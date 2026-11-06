"""Détecteur de « flux informé », version Phase 0 : des règles simples, fixées a priori.

Un **signal** naît quand un wallet a accumulé au moins `min_usdc` d'achats d'une issue à un
prix inférieur ou égal à `max_price`. Le signal est daté du trade qui franchit le seuil.
L'**alerte** est un signal émis par un wallet récent (âge ≤ `max_wallet_age` à ce moment).

Toutes les grandeurs sont calculées avec ce qui était connu à l'instant du signal : aucune
information future (issue, prix ultérieurs) n'intervient.

Les seuils par défaut viennent de l'étude préalable et ne sont pas ajustés sur les résultats :
- prix ≤ 0,35 (outsider) ;
- au moins 1 000 $ (seuil utilisé par des détecteurs publics) ;
- wallet de 7 jours au plus (la moitié des comptes du rapport ACDC pariaient moins de 2 jours
  après leur création).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

import pandas as pd


@dataclass(frozen=True)
class Rule:
    max_price: float = 0.35
    min_usdc: float = 1_000.0
    max_wallet_age: timedelta = timedelta(days=7)

    def label(self) -> str:
        days = self.max_wallet_age.total_seconds() / 86400
        return f"prix ≤ {self.max_price:.2f}, ≥ {self.min_usdc:,.0f} $, âge ≤ {days:g} j"


def accumulation_signals(trades: pd.DataFrame, rule: Rule) -> pd.DataFrame:
    """Un signal par (wallet, jeton) qui franchit le seuil d'achats à bas prix.

    `trades` contient les colonnes : condition_id, ts, wallet, token_id, side, size, price.
    Renvoie : condition_id, wallet, token_id, signal_ts, signal_usdc, signal_vwap,
    first_buy_ts.
    """
    buys = trades[(trades["side"] == "BUY") & (trades["price"] <= rule.max_price)].copy()
    columns = [
        "condition_id",
        "wallet",
        "token_id",
        "signal_ts",
        "signal_usdc",
        "signal_vwap",
        "first_buy_ts",
    ]
    if buys.empty:
        return pd.DataFrame(columns=columns)
    buys["usdc"] = buys["size"] * buys["price"]
    buys = buys.sort_values(["wallet", "token_id", "ts"], kind="stable")
    keys = ["condition_id", "wallet", "token_id"]
    grouped = buys.groupby(keys, sort=False)
    buys["cum_usdc"] = grouped["usdc"].cumsum()
    buys["cum_size"] = grouped["size"].cumsum()
    buys["first_buy_ts"] = grouped["ts"].transform("min")
    crossing = buys[buys["cum_usdc"] >= rule.min_usdc]
    first = crossing.groupby(keys, sort=False).head(1)
    return pd.DataFrame(
        {
            "condition_id": first["condition_id"].to_numpy(),
            "wallet": first["wallet"].to_numpy(),
            "token_id": first["token_id"].to_numpy(),
            "signal_ts": first["ts"].to_numpy(),
            "signal_usdc": first["cum_usdc"].to_numpy(),
            "signal_vwap": (first["cum_usdc"] / first["cum_size"]).to_numpy(),
            "first_buy_ts": first["first_buy_ts"].to_numpy(),
        },
        columns=columns,
    )


def add_wallet_context(
    signals: pd.DataFrame, profiles: pd.DataFrame, deposits: pd.DataFrame
) -> pd.DataFrame:
    """Ajoute l'âge du wallet et l'ancienneté de son dernier dépôt, au moment du signal.

    `profiles` : wallet, first_activity_ts. `deposits` : wallet, ts (dépôts individuels ; les
    distributions groupées doivent avoir été retirées en amont).
    Un wallet sans profil a un âge inconnu (NaT) et ne déclenche jamais d'alerte.
    """
    out = signals.merge(profiles[["wallet", "first_activity_ts"]], on="wallet", how="left")
    out["wallet_age"] = out["signal_ts"] - out["first_activity_ts"]
    out = out.sort_values("signal_ts", kind="stable").reset_index(drop=True)
    if deposits.empty:
        out["last_deposit_ts"] = pd.NaT
    else:
        dep = deposits[["wallet", "ts"]].rename(columns={"ts": "last_deposit_ts"})
        dep = dep.sort_values("last_deposit_ts", kind="stable")
        out = pd.merge_asof(
            out,
            dep,
            left_on="signal_ts",
            right_on="last_deposit_ts",
            by="wallet",
            direction="backward",
        )
    out["since_deposit"] = out["signal_ts"] - out["last_deposit_ts"]
    return out


def is_alert(signals_with_context: pd.DataFrame, rule: Rule) -> pd.Series:
    age = signals_with_context["wallet_age"]
    return age.notna() & (age <= pd.Timedelta(rule.max_wallet_age))
