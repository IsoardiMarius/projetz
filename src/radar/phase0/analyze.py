"""Analyses de la Phase 0 : signaux, alertes et simulation d'un suiveur, marché par marché."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import pandas as pd

from radar.analysis import copy_sim, detector, fees, prices
from radar.collect import Collector
from radar.storage.repository import Conn

log = logging.getLogger(__name__)

BATCH_DEPOSIT_MIN_WALLETS = (
    5  # un même dépôt vers ≥ 5 wallets = distribution groupée, pas un financement
)


@dataclass(frozen=True)
class MarketRow:
    condition_id: str
    question: str
    grp: str
    case_key: str | None
    event_id: str | None
    tags: tuple[str, ...]
    winning_token_id: str | None
    token_ids: tuple[str, ...]
    closed_time: datetime | None
    end_date: datetime | None

    @property
    def fee_rate(self) -> float:
        return fees.taker_rate(self.tags)


@dataclass
class MarketResult:
    market: MarketRow
    t_info: datetime | None
    signals: pd.DataFrame
    trades: pd.DataFrame = field(repr=False)
    views: dict[str, pd.DataFrame] = field(repr=False)


def load_markets(conn: Conn) -> list[MarketRow]:
    rows = conn.execute(
        """
        SELECT m.condition_id, m.question, p.grp, p.case_key, m.event_id, m.tags,
               m.winning_token_id, m.outcomes, m.closed_time, m.end_date
        FROM phase0_markets p
        JOIN markets m USING (condition_id)
        JOIN market_collections c USING (condition_id)
        WHERE m.winning_token_id IS NOT NULL
        ORDER BY p.grp, p.case_key, m.condition_id
        """
    ).fetchall()
    result = []
    for r in rows:
        outcomes = r[7] if isinstance(r[7], list) else []
        result.append(
            MarketRow(
                condition_id=str(r[0]),
                question=str(r[1]),
                grp=str(r[2]),
                case_key=None if r[3] is None else str(r[3]),
                event_id=None if r[4] is None else str(r[4]),
                tags=tuple(r[5]) if isinstance(r[5], list) else (),
                winning_token_id=str(r[6]),
                token_ids=tuple(str(o["token_id"]) for o in outcomes),
                closed_time=r[8] if isinstance(r[8], datetime) else None,
                end_date=r[9] if isinstance(r[9], datetime) else None,
            )
        )
    return result


def load_trades(conn: Conn, condition_id: str) -> pd.DataFrame:
    cur = conn.execute(
        "SELECT condition_id, ts, wallet, token_id, side, size, price, is_taker"
        " FROM trades WHERE condition_id = %s ORDER BY seq",
        (condition_id,),
    )
    columns = ["condition_id", "ts", "wallet", "token_id", "side", "size", "price", "is_taker"]
    frame = pd.DataFrame(cur.fetchall(), columns=columns)
    frame["ts"] = pd.to_datetime(frame["ts"], utc=True)
    return frame


def analyze_market(conn: Conn, market: MarketRow, rule: detector.Rule) -> MarketResult:
    trades = load_trades(conn, market.condition_id)
    views = {token: prices.token_view(trades, token) for token in market.token_ids}
    winner_view = views.get(market.winning_token_id or "")
    t_info = None if winner_view is None else prices.information_time(winner_view)
    signals = detector.accumulation_signals(trades, rule)
    return MarketResult(market=market, t_info=t_info, signals=signals, trades=trades, views=views)


def iter_results(conn: Conn, rule: detector.Rule) -> Iterator[MarketResult]:
    for market in load_markets(conn):
        yield analyze_market(conn, market, rule)


def load_wallet_context(conn: Conn) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Profils et dépôts individuels (sans les distributions groupées)."""
    profiles = pd.DataFrame(
        conn.execute("SELECT wallet, first_activity_ts FROM wallet_profiles").fetchall(),
        columns=["wallet", "first_activity_ts"],
    )
    profiles["first_activity_ts"] = pd.to_datetime(profiles["first_activity_ts"], utc=True)
    deposits = pd.DataFrame(
        conn.execute(
            """
            SELECT d.wallet, d.ts FROM wallet_deposits d
            WHERE d.tx_hash NOT IN (
                SELECT tx_hash FROM wallet_deposits GROUP BY tx_hash
                HAVING count(DISTINCT wallet) >= %s)
            """,
            (BATCH_DEPOSIT_MIN_WALLETS,),
        ).fetchall(),
        columns=["wallet", "ts"],
    )
    deposits["ts"] = pd.to_datetime(deposits["ts"], utc=True)
    return profiles, deposits


def profile_signal_wallets(collector: Collector, rule: detector.Rule) -> int:
    """Récupère l'âge et les dépôts des wallets qui ont émis au moins un signal."""
    wallets: set[str] = set()
    for result in iter_results(collector.conn, rule):
        wallets.update(result.signals["wallet"].astype(str))
    known = {str(r[0]) for r in collector.conn.execute("SELECT wallet FROM wallet_profiles")}
    missing = sorted(wallets - known)
    log.info("%d wallets à profiler (%d déjà connus)", len(missing), len(wallets & known))
    return collector.profile_wallets(missing)


def simulate_all(
    results: list[MarketResult],
    profiles: pd.DataFrame,
    deposits: pd.DataFrame,
    rule: detector.Rule,
    delays: tuple[timedelta, ...] = copy_sim.DEFAULT_DELAYS,
) -> pd.DataFrame:
    """Signaux enrichis (contexte du wallet, alerte, avance sur l'information) et simulation."""
    frames = []
    for res in results:
        if res.signals.empty:
            continue
        ctx = detector.add_wallet_context(res.signals, profiles, deposits)
        ctx["alert"] = detector.is_alert(ctx, rule)
        ctx["grp"] = res.market.grp
        ctx["case_key"] = res.market.case_key
        ctx["event_id"] = res.market.event_id or res.market.condition_id
        ctx["t_info"] = pd.Timestamp(res.t_info) if res.t_info else pd.NaT
        info = copy_sim.MarketInfo(
            winning_token_id=res.market.winning_token_id,
            closed_time=res.market.closed_time,
            fee_rate=res.market.fee_rate,
        )
        sim = copy_sim.simulate(ctx, res.views, {res.market.condition_id: info}, delays)
        frames.append(sim)
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    out["lead"] = out["t_info"] - pd.to_datetime(out["signal_ts"], utc=True)
    return out
