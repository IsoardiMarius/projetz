"""Trois stratégies testées sur l'historique, comme un paper trading rétrospectif.

Règles communes, fixées avant de regarder les résultats :
- l'achat se fait au marché, au prix de la première exécution côté vendeur 5 min après le
  déclencheur (jamais dans le même bloc), frais taker compris ;
- la position est gardée jusqu'à la résolution (1 $ par part si l'issue gagne, 0 sinon) ;
- mise fixe de 1 $ par position ; intervalles de confiance par bootstrap d'événements ;
- stabilité vérifiée sur deux périodes : avant et après le 1er mai 2026.

1. **Contre-pied de l'emballement** : quand au moins N comptes neufs (≤ 7 j) ont accumulé
   ≥ 500 $ sur la même issue à ≤ 50 ¢ en 6 h, on achète l'issue **opposée**.
2. **Quasi-certitudes** : on achète une issue dès qu'elle cote dans une tranche de prix élevée
   (90-95 ¢, 95-97 ¢, 97-99 ¢, ≥ 99 ¢).
3. **Comptes compétents** : on copie les positions (≥ 500 $, ≤ 95 ¢) des wallets dont
   l'historique, sur des marchés **déjà résolus** au moment du signal, bat nettement les prix
   payés (score z de Poisson-binomial).
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from radar.analysis import detector
from radar.analysis.copy_sim import ask_arrays, ask_entries
from radar.analysis.stats import cluster_bootstrap_mean
from radar.phase0.analyze import MarketResult, iter_results, load_wallet_context
from radar.storage.repository import Conn

log = logging.getLogger(__name__)

DELAY = timedelta(minutes=5)
MAX_WAIT = timedelta(hours=2)
SPLIT = pd.Timestamp(datetime(2026, 5, 1, tzinfo=UTC))
HYPE_RULE = detector.Rule(max_price=0.5, min_usdc=500)
SKILL_RULE = detector.Rule(max_price=0.95, min_usdc=500)
TRADE_COLUMNS = [
    "strategy",
    "variant",
    "condition_id",
    "event_id",
    "token_id",
    "entry_ts",
    "cost",
    "won",
    "ret",
    "days",
]


@dataclass
class Universe:
    results: list[MarketResult]
    by_cond: dict[str, MarketResult]
    token_market: dict[str, MarketResult]
    asks: dict[str, tuple[np.ndarray, np.ndarray]]

    @classmethod
    def build(cls, results: list[MarketResult]) -> Universe:
        by_cond = {r.market.condition_id: r for r in results}
        token_market = {t: r for r in results for t in r.market.token_ids}
        asks = {t: ask_arrays(v) for r in results for t, v in r.views.items()}
        return cls(results, by_cond, token_market, asks)


def buy(
    universe: Universe, token_ids: Iterable[str], trigger_ts: pd.Series, strategy: str, variant: str
) -> pd.DataFrame:
    """Achète chaque jeton au marché après son déclencheur ; une ligne par position remplie."""
    frame = pd.DataFrame(
        {"token_id": list(token_ids), "trigger": pd.to_datetime(trigger_ts, utc=True).to_numpy()}
    )
    rows = []
    for token, block in frame.groupby("token_id", sort=False):
        res = universe.token_market[str(token)]
        base = pd.DatetimeIndex(block["trigger"]).as_unit("ns").asi8
        in_time, entry_ns, price = ask_entries(universe.asks[str(token)], base, DELAY, MAX_WAIT)
        closed = res.market.closed_time or res.market.end_date
        closed_ns = pd.Timestamp(closed).value if closed else np.iinfo(np.int64).max
        ok = in_time & (entry_ns < closed_ns) & (price > 0) & (price < 1)
        if not ok.any():
            continue
        rate = res.market.fee_rate
        cost = price[ok] + rate * price[ok] * (1 - price[ok])
        won = res.market.winning_token_id == str(token)
        days = (closed_ns - entry_ns[ok]) / 86_400e9 if closed else np.full(ok.sum(), np.nan)
        rows.append(
            pd.DataFrame(
                {
                    "strategy": strategy,
                    "variant": variant,
                    "condition_id": res.market.condition_id,
                    "event_id": res.market.event_id or res.market.condition_id,
                    "token_id": str(token),
                    "entry_ts": pd.to_datetime(entry_ns[ok], utc=True, unit="ns"),
                    "cost": cost,
                    "won": float(won),
                    "ret": float(won) / cost - 1.0,
                    "days": days,
                }
            )
        )
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=TRADE_COLUMNS)


def _complement(res: MarketResult, token: str) -> str | None:
    others = [t for t in res.market.token_ids if t != token]
    return others[0] if len(res.market.token_ids) == 2 and len(others) == 1 else None


def _first_with_cooldown(times: np.ndarray, cooldown: timedelta) -> list[int]:
    """Indices des déclenchements espacés d'au moins `cooldown` du précédent retenu."""
    chosen: list[int] = []
    last = None
    gap = int(cooldown.total_seconds() * 1e9)
    for i, t in enumerate(times):
        if last is None or t - last >= gap:
            chosen.append(i)
            last = t
    return chosen


# --- 1. Contre-pied de l'emballement -------------------------------------------------------


def contrarian(
    universe: Universe,
    profiles: pd.DataFrame,
    deposits: pd.DataFrame,
    thresholds: tuple[int, ...] = (3, 5, 10),
) -> pd.DataFrame:
    parts = [r.signals for r in universe.results if not r.signals.empty]
    signals = detector.add_wallet_context(pd.concat(parts, ignore_index=True), profiles, deposits)
    signals["is_new"] = signals["wallet_age"].notna() & (
        signals["wallet_age"] <= pd.Timedelta(days=7)
    )
    signals["signal_ts"] = pd.to_datetime(signals["signal_ts"], utc=True)
    window = int(timedelta(hours=6).total_seconds() * 1e9)
    trades = []
    for variant_n in (0, *thresholds):
        tokens, triggers = [], []
        for token, block in signals.groupby("token_id", sort=False):
            res = universe.token_market.get(str(token))
            other = _complement(res, str(token)) if res else None
            if other is None:
                continue
            if variant_n == 0:  # référence : contre-pied de n'importe quel signal
                times = np.sort(pd.DatetimeIndex(block["signal_ts"]).as_unit("ns").asi8)
                fire = times[_first_with_cooldown(times, timedelta(hours=24))]
            else:
                new = np.sort(
                    pd.DatetimeIndex(block.loc[block["is_new"], "signal_ts"]).as_unit("ns").asi8
                )
                if len(new) < variant_n:
                    continue
                count = np.arange(len(new)) - np.searchsorted(new, new - window, side="left") + 1
                hot = new[count >= variant_n]
                fire = hot[_first_with_cooldown(hot, timedelta(hours=24))]
            tokens += [other] * len(fire)
            triggers += list(fire)
        label = (
            "contre-pied de tout signal (référence)"
            if variant_n == 0
            else (f"≥ {variant_n} comptes neufs en 6 h")
        )
        trades.append(
            buy(
                universe,
                tokens,
                pd.Series(pd.to_datetime(triggers, utc=True)),
                "contre-pied",
                label,
            )
        )
    return pd.concat(trades, ignore_index=True)


# --- 2. Quasi-certitudes -------------------------------------------------------------------


BANDS = ((0.90, 0.95), (0.95, 0.97), (0.97, 0.99), (0.99, 1.0))


def near_certain(universe: Universe) -> pd.DataFrame:
    trades = []
    for low, high in BANDS:
        tokens, triggers = [], []
        for token, (ask_ns, price) in universe.asks.items():
            inside = np.flatnonzero((price >= low) & (price < high))
            if len(inside):
                tokens.append(token)
                triggers.append(ask_ns[inside[0]])
        bought = buy(
            universe,
            tokens,
            pd.Series(pd.to_datetime(triggers, utc=True)),
            "quasi-certitude",
            f"{low:.2f}-{high:.2f} $",
        )
        # Le prix a pu bouger en 5 min : on ne garde que les entrées restées dans la zone.
        trades.append(bought[bought["cost"] >= low - 0.02])
    return pd.concat(trades, ignore_index=True)


# --- 3. Comptes compétents -----------------------------------------------------------------


def wallet_history(signals: pd.DataFrame) -> pd.DataFrame:
    """Bilan de chaque wallet sur ses positions déjà résolues au moment de chaque signal.

    prior_n, prior_wins, prior_sum_p (somme des prix payés), prior_var (Σ p(1−p)) et
    prior_z = (gains − Σp) / √Σp(1−p), le score de compétence au-delà du prix payé.
    """
    df = signals[["wallet", "signal_ts", "closed_time", "won", "signal_vwap"]].copy()
    df["wallet"] = df["wallet"].astype(str)
    df["p"] = df["signal_vwap"].astype(float).clip(0.001, 0.999)
    res = df.dropna(subset=["closed_time"]).sort_values("closed_time", kind="stable")
    grouped = res.groupby("wallet")
    res = res.assign(
        c_n=grouped.cumcount() + 1,
        c_w=grouped["won"].cumsum(),
        c_p=grouped["p"].cumsum(),
        c_v=(res["p"] * (1 - res["p"])).groupby(res["wallet"]).cumsum(),
    )[["wallet", "closed_time", "c_n", "c_w", "c_p", "c_v"]]
    query = df[["wallet", "signal_ts"]].reset_index().sort_values("signal_ts", kind="stable")
    merged = pd.merge_asof(
        query,
        res,
        left_on="signal_ts",
        right_on="closed_time",
        by="wallet",
        direction="backward",
        allow_exact_matches=False,
    ).set_index("index")
    out = pd.DataFrame(index=signals.index)
    out["prior_n"] = merged["c_n"].reindex(signals.index).fillna(0.0)
    out["prior_wins"] = merged["c_w"].reindex(signals.index).fillna(0.0)
    out["prior_sum_p"] = merged["c_p"].reindex(signals.index).fillna(0.0)
    var = merged["c_v"].reindex(signals.index).fillna(0.0)
    out["prior_z"] = np.where(
        var > 0, (out["prior_wins"] - out["prior_sum_p"]) / np.sqrt(var.where(var > 0, 1.0)), 0.0
    )
    return out


SKILL_VARIANTS: tuple[tuple[str, int, float, float], ...] = (
    # (libellé, historique minimal, z min, z max)
    ("tout copier (référence)", 0, -np.inf, np.inf),
    ("historique ≥ 10, mauvais (z < 0)", 10, -np.inf, 0.0),
    ("historique ≥ 5, z ≥ 1", 5, 1.0, np.inf),
    ("historique ≥ 10, z ≥ 2", 10, 2.0, np.inf),
    ("historique ≥ 20, z ≥ 2", 20, 2.0, np.inf),
    ("historique ≥ 20, z ≥ 3", 20, 3.0, np.inf),
)


def skilled(universe: Universe) -> pd.DataFrame:
    parts = []
    for r in universe.results:
        s = detector.accumulation_signals(r.trades, SKILL_RULE)
        if s.empty:
            continue
        s["won"] = (s["token_id"].astype(str) == (r.market.winning_token_id or "")).astype(float)
        s["closed_time"] = pd.Timestamp(r.market.closed_time) if r.market.closed_time else pd.NaT
        parts.append(s)
    signals = pd.concat(parts, ignore_index=True)
    signals["signal_ts"] = pd.to_datetime(signals["signal_ts"], utc=True)
    signals["closed_time"] = pd.to_datetime(signals["closed_time"], utc=True)
    signals = signals.join(wallet_history(signals))
    trades = []
    for label, min_n, z_lo, z_hi in SKILL_VARIANTS:
        chosen = signals[
            (signals["prior_n"] >= min_n)
            & (signals["prior_z"] >= z_lo)
            & (signals["prior_z"] < z_hi)
        ]
        trades.append(
            buy(
                universe,
                chosen["token_id"].astype(str),
                chosen["signal_ts"],
                "comptes compétents",
                label,
            )
        )
    return pd.concat(trades, ignore_index=True)


# --- Rapport -------------------------------------------------------------------------------


def _row(label: str, t: pd.DataFrame, annualize: bool) -> str:
    width = 9 if annualize else 8
    if t.empty:
        return f"| {label} | 0 |" + " — |" * (width - 2)
    est = cluster_bootstrap_mean(t["ret"], t["event_id"])
    early = t[t["entry_ts"] < SPLIT]
    late = t[t["entry_ts"] >= SPLIT]
    cells = [
        label,
        str(len(t)),
        str(t["event_id"].nunique()),
        f"{t['won'].mean():.1%}",
        f"{t['cost'].mean():.1%}",
        est.fmt(),
    ]
    if annualize:
        days = t["days"].clip(lower=1 / 24)
        rate = t["ret"].sum() / days.sum() * 365 if days.sum() > 0 else float("nan")
        cells.append(f"{rate:+.0%} ({int((t['won'] == 0).sum())} pertes)")
    cells += [
        cluster_bootstrap_mean(early["ret"], early["event_id"]).fmt(),
        cluster_bootstrap_mean(late["ret"], late["event_id"]).fmt(),
    ]
    return "| " + " | ".join(cells) + " |"


def report(trades: pd.DataFrame, out: Path) -> Path:
    lines = [
        "# Trois stratégies testées sur l'historique",
        "",
        "Mise de 1 $ par position, achat au marché 5 min après le déclencheur, frais "
        "compris, gardé jusqu'à la résolution. Entre crochets : intervalle de confiance à "
        "90 % (bootstrap d'événements). Les deux dernières colonnes séparent les positions "
        "prises avant et après le 1er mai 2026 : une stratégie solide doit gagner sur les "
        "deux.",
        "",
    ]
    titles = {
        "contre-pied": "## 1. Contre-pied de l'emballement des comptes neufs",
        "quasi-certitude": "## 2. Quasi-certitudes (90-99 ¢)",
        "comptes compétents": "## 3. Copier les comptes compétents",
    }
    for strategy, title in titles.items():
        sub = trades[trades["strategy"] == strategy]
        annual = strategy == "quasi-certitude"
        header = [
            "Variante",
            "Positions",
            "Événements",
            "Gagnantes",
            "Prix payé moyen",
            "Rendement par $",
        ]
        if annual:
            header.append("Rendement annualisé")
        header += ["Avant mai 2026", "Après mai 2026"]
        lines += [title, "", "| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
        for variant in dict.fromkeys(sub["variant"]):
            lines.append(_row(str(variant), sub[sub["variant"] == variant], annual))
        lines.append("")
    path = out / "strategies.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def run(conn: Conn, out: Path) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    results = [r for r in iter_results(conn, HYPE_RULE) if r.market.grp == "sample"]
    universe = Universe.build(results)
    profiles, deposits = load_wallet_context(conn)
    log.info("%d marchés chargés", len(results))
    trades = pd.concat(
        [contrarian(universe, profiles, deposits), near_certain(universe), skilled(universe)],
        ignore_index=True,
    )
    log.info("%d positions simulées", len(trades))
    return report(trades, out)
