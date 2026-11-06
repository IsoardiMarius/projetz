"""Séries de prix reconstituées à partir des trades.

Dans un marché binaire, acheter YES au prix p équivaut à vendre NO au prix 1 − p. On combine
donc les deux jetons pour densifier la série d'un jeton. On n'utilise que les lignes taker,
pour compter chaque exécution une seule fois.

Côté « ask » d'un jeton k : un taker qui ACHÈTE k, ou qui VEND le jeton complémentaire.
C'est le prix qu'aurait payé un suiveur qui achète k au marché.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal

import numpy as np
import pandas as pd

TRADE_COLUMNS = ["ts", "wallet", "token_id", "side", "size", "price", "is_taker"]


def token_view(trades: pd.DataFrame, token_id: str) -> pd.DataFrame:
    """Exécutions taker exprimées dans le prix du jeton `token_id`.

    Colonnes : ts, price (prix du jeton), ask (True si l'exécution révèle le prix vendeur),
    usdc (montant en dollars de l'exécution). Les lignes sont triées par horodatage.
    """
    takers = trades[trades["is_taker"]]
    same = takers["token_id"] == token_id
    price = np.where(same, takers["price"], 1.0 - takers["price"])
    buys = takers["side"] == "BUY"
    ask = np.where(same, buys, ~buys)
    view = pd.DataFrame(
        {
            "ts": takers["ts"].to_numpy(),
            "price": price,
            "ask": ask,
            "usdc": (takers["size"] * takers["price"]).to_numpy(),
        }
    )
    return view.sort_values("ts", kind="stable").reset_index(drop=True)


def rolling_median(view: pd.DataFrame, window: str = "30min") -> pd.Series:
    """Médiane glissante du prix sur une fenêtre de temps (résiste aux exécutions isolées)."""
    series = pd.Series(view["price"].to_numpy(), index=pd.DatetimeIndex(view["ts"]))
    return series.rolling(window).median()


def information_time(
    winner_view: pd.DataFrame,
    *,
    surprise_below: float = 0.5,
    confirmed_above: float = 0.85,
    window: str = "30min",
) -> datetime | None:
    """Moment estimé où l'issue gagnante devient évidente pour le marché.

    C'est le premier instant où la médiane glissante du gagnant dépasse `confirmed_above`,
    après le dernier passage sous `surprise_below`. Renvoie None si le gagnant n'a jamais été
    incertain (toujours favori) ou ne s'est jamais imposé avant la clôture.

    Ce repère est calculé a posteriori. Il sert à mesurer l'avance d'un signal, jamais à le
    déclencher.
    """
    if winner_view.empty:
        return None
    med = rolling_median(winner_view, window).dropna()
    below = med[med <= surprise_below]
    if below.empty:
        return None
    after = med[med.index > below.index[-1]]
    confirmed = after[after >= confirmed_above]
    if confirmed.empty:
        return None
    return pd.Timestamp(confirmed.index[0]).to_pydatetime()


def ask_price_after(
    token_view_df: pd.DataFrame,
    when: datetime,
    *,
    max_wait: timedelta = timedelta(hours=2),
    strict: bool = False,
) -> tuple[datetime, float] | None:
    """Première exécution côté vendeur à partir de `when` : (horodatage, prix).

    Avec `strict=True`, seules les exécutions postérieures à `when` comptent. On exclut ainsi
    le bloc du trade observé : un suiveur ne peut pas entrer dans la même transaction.
    Renvoie None si aucune exécution n'a lieu dans le délai `max_wait`.
    """
    asks = token_view_df[token_view_df["ask"]]
    times = pd.DatetimeIndex(asks["ts"])
    side: Literal["left", "right"] = "right" if strict else "left"
    position = int(times.searchsorted(pd.Timestamp(when), side=side))
    if position >= len(asks):
        return None
    row = asks.iloc[position]
    ts = pd.Timestamp(row["ts"]).to_pydatetime()
    if ts - when > max_wait:
        return None
    return ts, float(row["price"])
