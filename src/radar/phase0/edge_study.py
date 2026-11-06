"""Détecteur v2 : prédire l'avantage d'un signal sur le prix, et le valider honnêtement.

Population : les signaux d'accumulation (≥ 500 $ à ≤ 50 ¢) des marchés tirés au hasard.
Cible : l'issue achetée gagne-t-elle ? Référence : le prix qu'aurait payé un suiveur 5 min
après le signal, frais compris. Le modèle n'a d'intérêt que s'il fait mieux que ce prix hors
échantillon :
- validation croisée groupée par événement ;
- test chronologique : entraînement sur les marchés résolus avant une date, test après.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from radar.analysis import detector, edge_model, features
from radar.analysis.fees import taker_fee_per_share
from radar.analysis.stats import cluster_bootstrap_mean
from radar.phase0.analyze import MarketResult, iter_results, load_wallet_context, simulate_all
from radar.storage.repository import Conn

log = logging.getLogger(__name__)

RULE = detector.Rule(max_price=0.5, min_usdc=500)
FOLLOW_DELAY = timedelta(minutes=5)
FEATURES = [
    "logit_price",
    "log_usdc",
    "log_age_days",
    "age_unknown",
    "is_new",
    "log_hours_since_deposit",
    "log_hours_to_end",
    "n_signals_6h",
    "n_new_signals_6h",
    "mom_1h",
    "mom_24h",
    "log_vol_24h",
    "share_24h",
    "prior_n_log",
    "prior_excess",
    "q_military",
    "q_leader_out",
    "q_award",
    "q_date_ladder",
    "q_exact_day",
    "funder_known",
    "funder_is_hub",
    "cluster_size_log",
    "cluster_signals_24h",
]


@dataclass(frozen=True)
class EdgeStudy:
    table: pd.DataFrame  # une ligne par signal (échantillon et cas), caractéristiques et cible
    report: Path


def build_table(
    results: list[MarketResult],
    profiles: pd.DataFrame,
    deposits: pd.DataFrame,
    funders: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Signaux + caractéristiques + prix du suiveur à 5 min + cible."""
    sim = simulate_all(results, profiles, deposits, RULE, delays=(FOLLOW_DELAY,))
    sim = sim[sim["filled"]].copy()
    by_cond = {r.market.condition_id: r for r in results}
    parts = []
    for (cond, token), block in sim.groupby(["condition_id", "token_id"], sort=False):
        res = by_cond[str(cond)]
        flow = features.flow_features(block, res.views[str(token)])
        flags = features.question_flags(res.market.question)
        end = res.market.end_date
        extra = block.assign(**flow, **flags)
        extra["hours_to_end"] = (
            (pd.Timestamp(end) - extra["signal_ts"]).dt.total_seconds() / 3600
            if end is not None
            else np.nan
        )
        extra["closed_time"] = (
            pd.Timestamp(res.market.closed_time) if res.market.closed_time else pd.NaT
        )
        extra["question"] = res.market.question
        extra["fee_rate"] = res.market.fee_rate
        parts.append(extra)
    table = pd.concat(parts, ignore_index=True)
    track = features.wallet_track_record(table, table["closed_time"])
    table = table.join(track)
    if funders is not None and not funders.empty:
        first = features.first_funders(funders)
        hubs = features.hub_set(first, min_wallets=20)
        table = table.join(features.funding_features(table, first, hubs))
    else:
        for column in ("funder_known", "funder_is_hub", "cluster_size", "cluster_signals_24h"):
            table[column] = 0.0
    table["cluster_size_log"] = np.log1p(table["cluster_size"])

    days = table["wallet_age"].dt.total_seconds() / 86400
    table["log_age_days"] = np.log1p(days.clip(lower=0))
    table["age_unknown"] = days.isna().astype(float)
    table["is_new"] = (days <= 7).astype(float)
    since = table["since_deposit"].dt.total_seconds() / 3600
    table["log_hours_since_deposit"] = np.log1p(since.clip(lower=0))
    table["log_hours_to_end"] = np.log1p(table["hours_to_end"].clip(lower=0))
    table["log_usdc"] = np.log(table["signal_usdc"].astype(float))
    table["log_vol_24h"] = np.log1p(table["vol_24h"])
    table["prior_n_log"] = np.log1p(table["prior_n"])
    # Prix réellement payé par le suiveur, frais compris : c'est la référence à battre.
    fee = [
        taker_fee_per_share(p, r)
        for p, r in zip(table["entry_price"], table["fee_rate"], strict=True)
    ]
    table["follow_cost"] = (table["entry_price"] + np.array(fee)).clip(0.001, 0.999)
    table["logit_price"] = edge_model.logit(table["follow_cost"].to_numpy(dtype=float))
    table["won"] = table["won"].astype(float)
    return table


def _strategy_rows(data: pd.DataFrame, pred_col: str) -> list[str]:
    lines = [
        "| Règle de suivi | Signaux suivis | Événements | Gagnants | Coût moyen | "
        "Rendement moyen par $ |",
        "|---|---|---|---|---|---|",
    ]
    for threshold in (None, 0.0, 0.03, 0.05, 0.10):
        if threshold is None:
            chosen = data
            label = "Tout suivre"
        else:
            chosen = data[data[pred_col] - data["follow_cost"] > threshold]
            label = f"Avantage prédit > {threshold:.0%}"
        if chosen.empty:
            lines.append(f"| {label} | 0 | — | — | — | — |")
            continue
        ret = chosen["won"] / chosen["follow_cost"] - 1.0
        est = cluster_bootstrap_mean(ret, chosen["event_id"])
        lines.append(
            f"| {label} | {len(chosen)} | {chosen['event_id'].nunique()} | "
            f"{chosen['won'].mean():.0%} | {chosen['follow_cost'].mean():.0%} | {est.fmt()} |"
        )
    return lines


def run(conn: Conn, out_dir: Path, *, split_date: datetime | None = None) -> EdgeStudy:
    out_dir.mkdir(parents=True, exist_ok=True)
    results = list(iter_results(conn, RULE))
    profiles, deposits = load_wallet_context(conn)
    funders = pd.DataFrame(
        conn.execute("SELECT wallet, funder, ts FROM wallet_funders").fetchall(),
        columns=["wallet", "funder", "ts"],
    )
    funders["ts"] = pd.to_datetime(funders["ts"], utc=True)
    table = build_table(results, profiles, deposits, funders)
    sample = table[table["grp"] == "sample"].copy()
    cases = table[table["grp"] == "case"].copy()
    log.info("Table : %d signaux (%d échantillon, %d cas)", len(table), len(sample), len(cases))

    cv = edge_model.cross_validate(sample, FEATURES, price_col="follow_cost")
    sample["pred_cv"] = cv.predictions
    skill = 1 - cv.loss_model / cv.loss_price
    gbm_pred, gbm_loss = edge_model.cross_validate_gbm(sample, FEATURES, price_col="follow_cost")
    sample["pred_gbm"] = gbm_pred
    gbm_skill = 1 - gbm_loss / cv.loss_price

    split = split_date or datetime(2026, 5, 1, tzinfo=UTC)
    train = sample[sample["closed_time"] < pd.Timestamp(split)]
    test = sample[sample["signal_ts"] >= pd.Timestamp(split)]
    lines_time: list[str] = []
    if len(train) > 200 and len(test) > 50:
        model = edge_model.OffsetLogit(c=0.5).fit(
            train[FEATURES].to_numpy(dtype=float),
            train["won"].to_numpy(dtype=float),
            train["logit_price"].to_numpy(dtype=float),
        )
        test = test.assign(
            pred_time=model.predict_proba(
                test[FEATURES].to_numpy(dtype=float), test["logit_price"].to_numpy(dtype=float)
            )
        )
        loss_m = edge_model.log_loss(test["won"].to_numpy(), test["pred_time"].to_numpy())
        loss_p = edge_model.log_loss(test["won"].to_numpy(), test["follow_cost"].to_numpy())
        lines_time = [
            f"Entraînement : {len(train)} signaux de marchés résolus avant le "
            f"{split:%d/%m/%Y} ; test : {len(test)} signaux émis après.",
            "",
            f"Amélioration de la log-loss sur le test : **{1 - loss_m / loss_p:+.2%}** "
            "(positif = le modèle bat le prix).",
            "",
            *_strategy_rows(test, "pred_time"),
        ]
        full = edge_model.OffsetLogit(c=0.5).fit(
            sample[FEATURES].to_numpy(dtype=float),
            sample["won"].to_numpy(dtype=float),
            sample["logit_price"].to_numpy(dtype=float),
        )
        cases["pred_full"] = full.predict_proba(
            cases[FEATURES].to_numpy(dtype=float), cases["logit_price"].to_numpy(dtype=float)
        )

    coef = cv.coefficients.sort_values(key=lambda s: -s.abs())
    lines = [
        "# Détecteur v2 — l'avantage sur le prix est-il prévisible ?",
        "",
        f"Population : {len(sample)} signaux (≥ 500 $ achetés à ≤ 50 ¢) sur "
        f"{sample['event_id'].nunique()} événements géopolitiques tirés au hasard. Référence : "
        "le prix payé par un suiveur 5 min après le signal, frais compris.",
        "",
        "## 1. Validation croisée (groupée par événement)",
        "",
        f"- Log-loss du prix seul : {cv.loss_price:.4f} ; du modèle : {cv.loss_model:.4f} → "
        f"amélioration **{skill:+.2%}**.",
        "",
        *_strategy_rows(sample, "pred_cv"),
        "",
        f"Modèle non linéaire (gradient boosting) : log-loss {gbm_loss:.4f} → amélioration "
        f"**{gbm_skill:+.2%}**.",
        "",
        *_strategy_rows(sample, "pred_gbm"),
        "",
        "Coefficients standardisés (moyenne des plis ; positif = augmente la probabilité "
        "de gain au-delà du prix) :",
        "",
        "| Caractéristique | Coefficient |",
        "|---|---|",
        *[f"| {name} | {value:+.3f} |" for name, value in coef.items()],
        "",
        "## 2. Test chronologique",
        "",
        *(lines_time or ["Pas assez de données de part et d'autre de la date de coupe."]),
        "",
    ]
    if "pred_full" in cases:
        lines += [
            "## 3. Les cas connus vus par le modèle (illustration, biais de sélection)",
            "",
            "| Cas | Signaux | Avantage prédit moyen | Gagnants | Coût moyen |",
            "|---|---|---|---|---|",
        ]
        for key, grp in cases.groupby("case_key"):
            edge = (grp["pred_full"] - grp["follow_cost"]).mean()
            lines.append(
                f"| {key} | {len(grp)} | {edge:+.1%} | {grp['won'].mean():.0%} | "
                f"{grp['follow_cost'].mean():.0%} |"
            )
    report = out_dir / "detecteur_v2.md"
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if not math.isnan(skill):
        log.info("Amélioration log-loss (CV) : %+.2f %%", 100 * skill)
    return EdgeStudy(table=table, report=report)
