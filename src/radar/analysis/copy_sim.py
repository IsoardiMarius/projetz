"""Simulation d'un suiveur : il achète la même issue que le signal, avec un retard donné.

Hypothèses (prudentes) :
- le suiveur achète « au marché » : il paie le prix de la première exécution côté vendeur
  observée après son retard ;
- il paie les frais taker du barème actuel ;
- il garde la position jusqu'à la résolution : 1 $ par part si l'issue gagne, 0 sinon ;
- petite mise (100 $) : on néglige l'impact de son propre ordre sur le carnet, qui n'est pas
  historisé.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

import pandas as pd

from radar.analysis.fees import taker_fee_per_share
from radar.analysis.prices import ask_price_after

DEFAULT_DELAYS: tuple[timedelta, ...] = (
    timedelta(seconds=0),
    timedelta(minutes=1),
    timedelta(minutes=5),
    timedelta(minutes=15),
    timedelta(minutes=30),
    timedelta(hours=1),
    timedelta(hours=4),
)


@dataclass(frozen=True)
class MarketInfo:
    winning_token_id: str | None
    closed_time: datetime | None
    fee_rate: float


def follower_return(entry_price: float, won: bool, fee_rate: float) -> float:
    """Rendement par dollar investi, frais compris (−1 = mise perdue)."""
    cost = entry_price + taker_fee_per_share(entry_price, fee_rate)
    if cost <= 0:
        raise ValueError("coût d'entrée nul")
    return (1.0 if won else 0.0) / cost - 1.0


def simulate(
    signals: pd.DataFrame,
    token_views: Mapping[str, pd.DataFrame],
    markets: Mapping[str, MarketInfo],
    delays: Sequence[timedelta] = DEFAULT_DELAYS,
    *,
    max_wait: timedelta = timedelta(hours=2),
) -> pd.DataFrame:
    """Une ligne par (signal, retard).

    Colonnes ajoutées : delay_s, filled, entry_ts, entry_price, won, ret. `filled` vaut False
    si aucune exécution n'a eu lieu dans le délai `max_wait`, ou si le marché était déjà
    clôturé à l'heure d'entrée.
    """
    rows: list[dict[str, object]] = []
    for signal in signals.to_dict("records"):
        market = markets[str(signal["condition_id"])]
        token_id = str(signal["token_id"])
        view = token_views[token_id]
        won = market.winning_token_id == token_id
        signal_ts = pd.Timestamp(signal["signal_ts"]).to_pydatetime()
        for delay in delays:
            entry = ask_price_after(view, signal_ts + delay, max_wait=max_wait)
            filled = entry is not None and (
                market.closed_time is None or entry[0] < market.closed_time
            )
            row: dict[str, object] = {str(k): v for k, v in signal.items()}
            row.update(
                delay_s=int(delay.total_seconds()),
                filled=filled,
                entry_ts=entry[0] if entry else None,
                entry_price=entry[1] if entry else None,
                won=won,
                ret=None,
            )
            if filled and entry is not None and entry[1] > 0:
                row["ret"] = follower_return(entry[1], won, market.fee_rate)
            rows.append(row)
    return pd.DataFrame(rows)
