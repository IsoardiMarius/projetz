"""Caractéristiques d'un signal, calculées avec ce qui était connu à l'instant du signal.

Elles alimentent le modèle « avantage sur le prix » (`radar.analysis.edge_model`). Aucune
grandeur ne dépend de l'issue ou des prix postérieurs au signal.
"""

from __future__ import annotations

import re
from datetime import timedelta

import numpy as np
import pandas as pd

_MILITARY = re.compile(
    r"\b(strike|strikes|attack|invade|invasion|forces|military|troops|missile|bomb|war|"
    r"ceasefire|operation|airstrike|drone|capture|captured)\b",
    re.IGNORECASE,
)
_LEADER_OUT = re.compile(
    r"\b(out|resign|resigns|removed|ousted|fired|arrested|leave|leaves|step down)\b",
    re.IGNORECASE,
)
_AWARD = re.compile(r"\b(nobel|prize|award|oscar|person of the year|#1|most searched)\b", re.I)
_DATE_LADDER = re.compile(
    r"\b(on|by|before)\s+(january|february|march|april|may|june|july|august|september|"
    r"october|november|december)\s+\d{1,2}\b",
    re.IGNORECASE,
)
_EXACT_DAY = re.compile(
    r"\bon\s+(january|february|march|april|may|june|july|august|september|october|november|"
    r"december)\s+\d{1,2}\b",
    re.IGNORECASE,
)


def question_flags(question: str) -> dict[str, float]:
    """Indicateurs simples sur le libellé du marché (type d'événement)."""
    return {
        "q_military": float(bool(_MILITARY.search(question))),
        "q_leader_out": float(bool(_LEADER_OUT.search(question))),
        "q_award": float(bool(_AWARD.search(question))),
        "q_date_ladder": float(bool(_DATE_LADDER.search(question))),
        "q_exact_day": float(bool(_EXACT_DAY.search(question))),
    }


def flow_features(
    signals: pd.DataFrame,
    token_view: pd.DataFrame,
    *,
    window: timedelta = timedelta(hours=6),
    new_wallet_age: timedelta = timedelta(days=7),
) -> pd.DataFrame:
    """Contexte de marché des signaux d'un même jeton, à l'instant de chaque signal.

    `signals` doit contenir signal_ts, signal_usdc et wallet_age (contexte du wallet).
    Renvoie, aligné sur l'index de `signals` :
    - n_signals_6h / n_new_signals_6h : signaux (et signaux de wallets récents) émis sur le
      même jeton dans la fenêtre précédente, le signal courant exclu ;
    - mom_1h / mom_24h : variation du prix du jeton sur 1 h et 24 h avant le signal ;
    - vol_24h : volume taker du jeton sur 24 h avant le signal ;
    - share_24h : part du signal dans ce volume.
    """
    out = pd.DataFrame(index=signals.index)
    ts = pd.DatetimeIndex(pd.to_datetime(signals["signal_ts"], utc=True)).as_unit("ns")
    order = np.argsort(ts.asi8, kind="stable")
    sorted_ns = ts.asi8[order]
    is_new = (
        signals["wallet_age"].notna() & (signals["wallet_age"] <= pd.Timedelta(new_wallet_age))
    ).to_numpy()[order]
    cum_new = np.concatenate([[0], np.cumsum(is_new)])
    lo = np.searchsorted(sorted_ns, sorted_ns - int(window.total_seconds() * 1e9), side="left")
    pos = np.arange(len(sorted_ns))
    n_all = pos - lo
    n_new = cum_new[pos] - cum_new[lo]
    inverse = np.empty_like(order)
    inverse[order] = pos
    out["n_signals_6h"] = n_all[inverse]
    out["n_new_signals_6h"] = n_new[inverse]

    view_ns = pd.DatetimeIndex(pd.to_datetime(token_view["ts"], utc=True)).as_unit("ns").asi8
    prices = token_view["price"].to_numpy(dtype=float)
    usdc = token_view["usdc"].to_numpy(dtype=float)
    cum_usdc = np.concatenate([[0.0], np.cumsum(usdc)])
    t = ts.asi8

    def price_at(times: np.ndarray) -> np.ndarray:
        idx = np.searchsorted(view_ns, times, side="right") - 1
        valid = idx >= 0
        res = np.full(len(times), np.nan)
        res[valid] = prices[idx[valid]]
        return res

    now = price_at(t - 1)  # dernier prix strictement avant le signal
    out["mom_1h"] = now - price_at(t - int(3600e9))
    out["mom_24h"] = now - price_at(t - int(86400e9))
    end = np.searchsorted(view_ns, t, side="left")
    start = np.searchsorted(view_ns, t - int(86400e9), side="left")
    vol = cum_usdc[end] - cum_usdc[start]
    out["vol_24h"] = vol
    out["share_24h"] = signals["signal_usdc"].to_numpy(dtype=float) / np.maximum(vol, 1.0)
    return out


def wallet_track_record(signals: pd.DataFrame, closed_time: pd.Series) -> pd.DataFrame:
    """Historique de chaque wallet sur les marchés déjà résolus au moment du signal.

    `signals` contient wallet, signal_ts, won et signal_vwap ; `closed_time` (même index)
    donne la date de résolution du marché du signal. Pour chaque signal, on agrège les
    signaux antérieurs du même wallet dont le marché était **déjà résolu** :
    - prior_n : nombre de positions résolues ;
    - prior_excess : (gains − somme des prix payés) / (n + 5), un taux de réussite au-delà du
      prix, rétréci vers 0 pour les petits historiques.
    """
    df = pd.DataFrame(
        {
            "wallet": signals["wallet"].astype(str).to_numpy(),
            "t": pd.to_datetime(signals["signal_ts"], utc=True).to_numpy(),
            "closed": pd.to_datetime(closed_time, utc=True).to_numpy(),
            "won": signals["won"].astype(float).to_numpy(),
            "p": signals["signal_vwap"].astype(float).to_numpy(),
        },
        index=signals.index,
    )
    resolved = df.dropna(subset=["closed"]).sort_values("closed", kind="stable")
    resolved = resolved.assign(
        cum_n=resolved.groupby("wallet").cumcount() + 1,
        cum_excess=(resolved["won"] - resolved["p"]).groupby(resolved["wallet"]).cumsum(),
    )[["wallet", "closed", "cum_n", "cum_excess"]]
    query = df[["wallet", "t"]].reset_index().sort_values("t", kind="stable")
    query["t"] = pd.to_datetime(query["t"], utc=True)
    resolved["closed"] = pd.to_datetime(resolved["closed"], utc=True)
    merged = pd.merge_asof(
        query,
        resolved,
        left_on="t",
        right_on="closed",
        by="wallet",
        direction="backward",
        allow_exact_matches=False,
    ).set_index("index")
    out = pd.DataFrame(index=signals.index)
    out["prior_n"] = merged["cum_n"].reindex(signals.index).fillna(0.0)
    excess = merged["cum_excess"].reindex(signals.index).fillna(0.0)
    out["prior_excess"] = excess / (out["prior_n"] + 5.0)
    return out


def first_funders(funders: pd.DataFrame) -> pd.DataFrame:
    """Premier financeur connu de chaque wallet : wallet, funder, funded_ts.

    `funders` contient wallet, funder (éventuellement nul) et ts (date du dépôt).
    """
    known = funders.dropna(subset=["funder"]).sort_values("ts", kind="stable")
    first = known.groupby("wallet", as_index=False).first()
    return first.rename(columns={"ts": "funded_ts"})[["wallet", "funder", "funded_ts"]]


def hub_set(first: pd.DataFrame, min_wallets: int = 20) -> set[str]:
    """Financeurs partagés par au moins `min_wallets` wallets : exchanges, bridges, relais.

    Un financeur commun de ce type ne dit rien d'un lien entre comptes.
    """
    counts = first.groupby("funder")["wallet"].nunique()
    return set(counts[counts >= min_wallets].index.astype(str))


def funding_features(
    signals: pd.DataFrame,
    first: pd.DataFrame,
    hubs: set[str],
    *,
    window: timedelta = timedelta(hours=24),
) -> pd.DataFrame:
    """Liens de financement au moment de chaque signal (aligné sur l'index de `signals`).

    - funder_known / funder_is_hub : origine des fonds trouvée, et s'agit-il d'un hub ;
    - cluster_size : wallets financés par le même financeur personnel **avant** le signal ;
    - cluster_signals_24h : signaux, dans les 24 h précédentes et sur le même jeton, d'autres
      wallets ayant le même financeur personnel (comptes coordonnés).
    """
    df = signals[["wallet", "token_id", "signal_ts"]].copy()
    df["signal_ts"] = pd.to_datetime(df["signal_ts"], utc=True)
    df["wallet"] = df["wallet"].astype(str)
    df["token_id"] = df["token_id"].astype(str)
    df = df.merge(first, on="wallet", how="left")
    out = pd.DataFrame(index=signals.index)
    out["funder_known"] = df["funder"].notna().to_numpy(dtype=float)
    is_hub = df["funder"].isin(hubs).to_numpy()
    out["funder_is_hub"] = is_hub.astype(float)
    personal = df["funder"].where(~df["funder"].isin(hubs))

    # Taille du groupe connue à la date du signal.
    fund = first[~first["funder"].isin(hubs)].copy()
    fund["funded_ts"] = pd.to_datetime(fund["funded_ts"], utc=True)
    sizes = np.zeros(len(df))
    for funder, idx in df.groupby(personal.to_numpy(), sort=False).groups.items():
        times = np.sort(
            pd.DatetimeIndex(fund.loc[fund["funder"] == funder, "funded_ts"]).as_unit("ns").asi8
        )
        when = pd.DatetimeIndex(df.loc[idx, "signal_ts"]).as_unit("ns").asi8
        sizes[np.asarray(idx)] = np.searchsorted(times, when, side="right")
    out["cluster_size"] = sizes

    # Signaux coordonnés : même jeton, même financeur personnel, dans la fenêtre précédente.
    coordinated = np.zeros(len(df))
    keyed = df.assign(personal=personal).dropna(subset=["personal"])
    for _, block in keyed.groupby(["token_id", "personal"], sort=False):
        if len(block) < 2:
            continue
        t = np.sort(pd.DatetimeIndex(block["signal_ts"]).as_unit("ns").asi8)
        own = pd.DatetimeIndex(block["signal_ts"]).as_unit("ns").asi8
        lo = np.searchsorted(t, own - int(window.total_seconds() * 1e9), side="left")
        hi = np.searchsorted(t, own, side="left")  # strictement avant : pas soi-même
        coordinated[block.index.to_numpy()] = hi - lo
    out["cluster_signals_24h"] = coordinated
    return out
