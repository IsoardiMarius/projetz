"""Simulation d'un suiveur : il achète la même issue que le signal, avec un retard donné.

Hypothèses (prudentes) :
- le suiveur achète « au marché » : il paie le prix de la première exécution côté vendeur
  observée après son retard, et jamais dans le bloc du signal lui-même ;
- il paie les frais taker du barème actuel ;
- il garde la position jusqu'à la résolution : 1 $ par part si l'issue gagne, 0 sinon ;
- petite mise (100 $) : on néglige l'impact de son propre ordre sur le carnet, qui n'est pas
  historisé.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from radar.analysis.fees import taker_fee_per_share

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
    """Une ligne par (signal, retard), calculée en bloc par jeton (recherche dichotomique).

    Colonnes ajoutées : delay_s, filled, entry_ts, entry_price, won, ret. `filled` vaut False
    si aucune exécution n'a eu lieu dans le délai `max_wait`, ou si le marché était déjà
    clôturé à l'heure d'entrée. L'entrée a toujours lieu strictement après l'instant visé :
    jamais dans le bloc du signal.
    """
    if signals.empty:
        return pd.DataFrame()
    frames: list[pd.DataFrame] = []
    signal_ts = pd.to_datetime(signals["signal_ts"], utc=True)
    for token_id, idx in signals.groupby("token_id", sort=False).groups.items():
        view = token_views[str(token_id)]
        asks = view[view["ask"]]
        ask_ns = pd.DatetimeIndex(pd.to_datetime(asks["ts"], utc=True)).as_unit("ns").asi8
        ask_price = asks["price"].to_numpy(dtype=float)
        block = signals.loc[idx]
        base_ns = pd.DatetimeIndex(signal_ts.loc[idx]).as_unit("ns").asi8
        info = [markets[str(c)] for c in block["condition_id"]]
        won = np.array([m.winning_token_id == str(token_id) for m in info])
        rates = np.array([m.fee_rate for m in info])
        closed_ns = np.array(
            [
                pd.Timestamp(m.closed_time).value
                if m.closed_time is not None
                else np.iinfo(np.int64).max
                for m in info
            ]
        )
        for delay in delays:
            target = base_ns + int(delay.total_seconds() * 1e9)
            pos = np.searchsorted(ask_ns, target, side="right")
            has = pos < len(ask_ns)
            safe = np.minimum(pos, max(len(ask_ns) - 1, 0))
            entry_ns = np.where(has, ask_ns[safe] if len(ask_ns) else 0, 0)
            entry_px = np.where(has, ask_price[safe] if len(ask_ns) else np.nan, np.nan)
            in_time = has & (entry_ns - target <= int(max_wait.total_seconds() * 1e9))
            filled = in_time & (entry_ns < closed_ns) & (entry_px > 0)
            cost = entry_px + rates * entry_px * (1.0 - entry_px)
            ret = np.where(
                filled, np.where(won, 1.0, 0.0) / np.where(filled, cost, 1.0) - 1.0, np.nan
            )
            out = block.copy()
            out["delay_s"] = int(delay.total_seconds())
            out["filled"] = filled
            out["entry_ts"] = pd.to_datetime(np.where(in_time, entry_ns, 0), utc=True, unit="ns")
            out.loc[~in_time, "entry_ts"] = pd.NaT
            out["entry_price"] = np.where(in_time, entry_px, np.nan)
            out["won"] = won
            out["ret"] = ret
            frames.append(out)
    result = pd.concat(frames, ignore_index=True)
    order = {int(d.total_seconds()): i for i, d in enumerate(delays)}
    result["_d"] = result["delay_s"].map(order)
    return result.sort_values(["_d"], kind="stable").drop(columns="_d").reset_index(drop=True)
