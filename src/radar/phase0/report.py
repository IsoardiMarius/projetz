"""Rapport de la Phase 0 : tableaux et graphiques en Markdown.

Le rapport contient des données réelles : il est écrit en local et n'est jamais versionné.
"""

from __future__ import annotations

import itertools
import logging
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

from radar.analysis import detector, prices
from radar.analysis.stats import cluster_bootstrap_mean, wilson_interval
from radar.phase0.analyze import MarketResult, iter_results, load_wallet_context, simulate_all
from radar.phase0.cases import CASES
from radar.storage.repository import Conn

log = logging.getLogger(__name__)

DELAY_LABELS = {
    0: "bloc suivant",
    60: "1 min",
    300: "5 min",
    900: "15 min",
    1800: "30 min",
    3600: "1 h",
    14400: "4 h",
}
KEY_DELAYS = (0, 300, 3600, 14400)


def _delay_table(sim: pd.DataFrame, populations: dict[str, pd.Series]) -> str:
    header = (
        "| Population | Signaux | Événements | "
        + " | ".join(f"Rendement à {DELAY_LABELS[d]}" for d in KEY_DELAYS)
        + " |"
    )
    lines = [header, "|" + "---|" * (3 + len(KEY_DELAYS))]
    for name, mask in populations.items():
        base = sim[mask & (sim["delay_s"] == 0)]
        cells = []
        for d in KEY_DELAYS:
            sub = sim[mask & (sim["delay_s"] == d) & sim["filled"]]
            cells.append(cluster_bootstrap_mean(sub["ret"], sub["event_id"]).fmt())
        lines.append(
            f"| {name} | {len(base)} | {base['event_id'].nunique()} | " + " | ".join(cells) + " |"
        )
    return "\n".join(lines)


def _hit_table(sim: pd.DataFrame, populations: dict[str, pd.Series]) -> str:
    lines = [
        "| Population | Signaux | Issue gagnante | Prix moyen payé (proba implicite) | Écart |",
        "|---|---|---|---|---|",
    ]
    for name, mask in populations.items():
        base = sim[mask & (sim["delay_s"] == 0)]
        n = len(base)
        if n == 0:
            continue
        wins = int(base["won"].sum())
        low, high = wilson_interval(wins, n)
        implied = float(base["signal_vwap"].mean())
        lines.append(
            f"| {name} | {n} | {wins / n:.0%} [{low:.0%} ; {high:.0%}] | {implied:.0%} | "
            f"{wins / n - implied:+.0%} |"
        )
    return "\n".join(lines)


def _decay_chart(sim: pd.DataFrame, populations: dict[str, pd.Series], path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    delays = sorted(sim["delay_s"].unique())
    xs = range(len(delays))
    for name, mask in populations.items():
        points, lows, highs = [], [], []
        for d in delays:
            sub = sim[mask & (sim["delay_s"] == d) & sim["filled"]]
            est = cluster_bootstrap_mean(sub["ret"], sub["event_id"])
            points.append(est.value)
            lows.append(est.low)
            highs.append(est.high)
        ax.plot(xs, points, marker="o", label=name)
        ax.fill_between(xs, lows, highs, alpha=0.15)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xticks(list(xs), [DELAY_LABELS.get(int(d), str(d)) for d in delays])
    ax.set_xlabel("Retard du suiveur après le signal")
    ax.set_ylabel("Rendement moyen par $ (frais compris)")
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.set_title("Ce qu'il reste à gagner en suivant, selon le retard")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def _case_chart(res: MarketResult, alerts: pd.DataFrame, path: Path) -> None:
    winner = res.market.winning_token_id
    if winner is None or winner not in res.views:
        return
    view = res.views[winner]
    med = prices.rolling_median(view, "30min").dropna()
    end = pd.Timestamp(res.t_info) + pd.Timedelta(days=1) if res.t_info else med.index.max()
    start = end - pd.Timedelta(days=10)
    med = med[(med.index >= start) & (med.index <= end)]
    if med.empty:
        return
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(
        med.index,
        med.to_numpy(),
        color="#3060a0",
        linewidth=1.2,
        label="Prix de l'issue gagnante (médiane 30 min)",
    )
    mine = alerts[
        (alerts["condition_id"] == res.market.condition_id) & (alerts["token_id"] == winner)
    ]
    mine = mine[
        (pd.to_datetime(mine["signal_ts"], utc=True) >= start)
        & (pd.to_datetime(mine["signal_ts"], utc=True) <= end)
    ]
    if not mine.empty:
        ax.scatter(
            pd.to_datetime(mine["signal_ts"], utc=True),
            mine["signal_vwap"],
            s=(mine["signal_usdc"].clip(upper=200_000) / 400) + 15,
            color="#d04020",
            alpha=0.7,
            label="Alertes (wallets récents), taille = mise",
        )
    if res.t_info:
        ax.axvline(
            float(mdates.date2num(res.t_info)),  # type: ignore[no-untyped-call]
            color="black",
            linestyle="--",
            linewidth=1,
            label="Information évidente (estimée)",
        )
    ax.set_ylim(0, 1)
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.set_title(res.market.question[:90], fontsize=9)
    ax.legend(fontsize=7, loc="upper left")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def _short(wallet: str) -> str:
    return f"{wallet[:6]}…{wallet[-4:]}"


def _top_informed_buyers(
    res: MarketResult, signals0: pd.DataFrame, profiles: pd.DataFrame, top: int = 5
) -> list[str]:
    """Plus gros gagnants ayant acheté l'issue gagnante à ≤ 50 ¢ avant l'information.

    Ce tableau est rétrospectif (il utilise l'issue) : il sert à vérifier si le détecteur,
    lui sans information future, aurait repéré ces comptes.
    """
    winner = res.market.winning_token_id
    if res.t_info is None or winner is None:
        return []
    t_info = pd.Timestamp(res.t_info)
    t = res.trades
    buys = t[
        (t["token_id"] == winner) & (t["side"] == "BUY") & (t["price"] <= 0.5) & (t["ts"] < t_info)
    ].copy()
    if buys.empty:
        return []
    buys["usdc"] = buys["size"] * buys["price"]
    agg = buys.groupby("wallet").agg(
        usdc=("usdc", "sum"), shares=("size", "sum"), first=("ts", "min"), last=("ts", "max")
    )
    agg["profit"] = agg["shares"] - agg["usdc"]
    agg = agg.sort_values("profit", ascending=False).head(top)
    first_seen = profiles.set_index("wallet")["first_activity_ts"]
    med = prices.rolling_median(res.views[winner], "30min").dropna()
    flagged = set(signals0["wallet"])
    alerted = set(signals0[signals0["alert"]]["wallet"])
    lines = [
        "",
        "Plus gros acheteurs gagnants avant l'information (rétrospectif) :",
        "",
        "| Wallet | Misé | Prix moyen | Gain | Âge au 1er achat | Avance du 1er achat | "
        "Prix 1 h après | Repéré ? |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for wallet, row in agg.iterrows():
        seen = first_seen.get(wallet)
        age = (
            f"{(row['first'] - seen).total_seconds() / 86400:.1f} j"
            if seen is not None and not pd.isna(seen)
            else "inconnu"
        )
        lead_h = (t_info - row["first"]).total_seconds() / 3600
        after = med[med.index >= row["first"] + pd.Timedelta(hours=1)]
        price_1h = f"{after.iloc[0]:.0%}" if len(after) else "—"
        status = "alerte" if wallet in alerted else ("signal" if wallet in flagged else "non")
        lines.append(
            f"| {_short(str(wallet))} | {row['usdc']:,.0f} $ | {row['usdc'] / row['shares']:.0%} | "
            f"{row['profit']:,.0f} $ | {age} | {lead_h:.1f} h | {price_1h} | {status} |"
        )
    return lines


def _case_section(
    results: list[MarketResult], sim: pd.DataFrame, out_dir: Path, profiles: pd.DataFrame
) -> list[str]:
    lines = ["## 1. Les cas connus", ""]
    by_key = {c.key: c for c in CASES}
    for key in sorted({r.market.case_key for r in results if r.market.case_key}):
        case = by_key[key]
        lines += [f"### {case.title}", "", f"_{case.context}_", ""]
        for res in [r for r in results if r.market.case_key == key]:
            s0 = sim[(sim["condition_id"] == res.market.condition_id) & (sim["delay_s"] == 0)]
            alerts = s0[s0["alert"]]
            before = alerts[alerts["lead"] > pd.Timedelta(0)] if res.t_info else alerts.iloc[0:0]
            on_winner = before[before["won"]]
            t_info = res.t_info.strftime("%d/%m/%Y %H:%M UTC") if res.t_info else "non déterminé"
            lines += [
                f"**{res.market.question}**",
                "",
                f"- Moment où l'issue devient évidente (estimé) : {t_info}",
                f"- Signaux (≥ 1 000 $ à ≤ 35 ¢) : {len(s0)} ; dont alertes (wallet ≤ 7 j) : "
                f"{len(alerts)}",
                f"- Alertes **avant** ce moment : {len(before)}, dont {len(on_winner)} sur "
                f"l'issue gagnante",
            ]
            if not on_winner.empty:
                lead_h = on_winner["lead"].dt.total_seconds() / 3600
                lines.append(
                    f"- Avance de ces alertes : médiane {lead_h.median():.1f} h "
                    f"(de {lead_h.min():.1f} h à {lead_h.max():.1f} h) ; mises cumulées "
                    f"{on_winner['signal_usdc'].sum():,.0f} $ au moment du signal ; prix "
                    f"moyen payé {on_winner['signal_vwap'].mean():.0%}"
                )
            # Le suiveur ne sait pas quelles alertes précèdent l'annonce : il les suit toutes.
            follow = sim[
                sim["filled"] & sim["alert"] & sim["condition_id"].eq(res.market.condition_id)
            ]
            parts = []
            for d in KEY_DELAYS:
                sub = follow[follow["delay_s"] == d]
                if len(sub):
                    parts.append(f"{DELAY_LABELS[d]} : {sub['ret'].mean():+.0%}")
            if parts:
                lines.append(
                    f"- Suiveur de **toutes** les alertes de ce marché "
                    f"({len(alerts)}), rendement moyen : " + " ; ".join(parts)
                )
            lines += _top_informed_buyers(res, s0, profiles)
            chart = out_dir / f"cas_{res.market.condition_id[:10]}.png"
            _case_chart(res, s0[s0["alert"]], chart)
            if chart.exists():
                lines += ["", f"![{res.market.question}]({chart.name})"]
            lines.append("")
    return lines


def _sensitivity(
    results: list[MarketResult],
    profiles: pd.DataFrame,
    deposits: pd.DataFrame,
    base_rule: detector.Rule,
) -> list[str]:
    lines = [
        "## 3. Sensibilité aux seuils (échantillon large)",
        "",
        "Tous les réglages sont montrés : aucun n'a été choisi en regardant les résultats.",
        "",
        "| Prix max | Mise min | Âge max | Alertes | Gagnantes | Prix payé | "
        "Rendement suiveur à 5 min |",
        "|---|---|---|---|---|---|---|",
    ]
    sample = [r for r in results if r.market.grp == "sample"]
    for max_price, min_usdc, age_days in itertools.product(
        (0.2, 0.35, 0.5), (500, 1000, 5000), (2, 7, 30)
    ):
        rule = replace(
            base_rule,
            max_price=max_price,
            min_usdc=min_usdc,
            max_wallet_age=timedelta(days=age_days),
        )
        rerun = [replace(r, signals=detector.accumulation_signals(r.trades, rule)) for r in sample]
        sim = simulate_all(
            rerun, profiles, deposits, rule, delays=(timedelta(0), timedelta(minutes=5))
        )
        if sim.empty:
            continue
        alerts0 = sim[sim["alert"] & (sim["delay_s"] == 0)]
        a5 = sim[sim["alert"] & (sim["delay_s"] == 300) & sim["filled"]]
        est = cluster_bootstrap_mean(a5["ret"], a5["event_id"])
        hit = alerts0["won"].mean() if len(alerts0) else float("nan")
        lines.append(
            f"| {max_price:.2f} | {min_usdc:,} $ | {age_days} j | {len(alerts0)} | "
            f"{hit:.0%} | {alerts0['signal_vwap'].mean():.0%} | {est.fmt()} |"
        )
    return lines


def build_report(conn: Conn, out_dir: Path, rule: detector.Rule | None = None) -> Path:
    rule = rule or detector.Rule()
    out_dir.mkdir(parents=True, exist_ok=True)
    results = list(iter_results(conn, rule))
    profiles, deposits = load_wallet_context(conn)
    sim = simulate_all(results, profiles, deposits, rule)

    is_case = sim["grp"] == "case"
    is_sample = sim["grp"] == "sample"
    populations = {
        "Cas connus : toutes les alertes": is_case & sim["alert"],
        "Échantillon : alertes (wallets ≤ 7 j)": is_sample & sim["alert"],
        "Échantillon : autres signaux (wallets anciens)": is_sample
        & ~sim["alert"]
        & sim["wallet_age"].notna(),
    }
    _decay_chart(sim, populations, out_dir / "rendement_selon_retard.png")

    n_sample = len({r.market.condition_id for r in results if r.market.grp == "sample"})
    n_events = len({r.market.event_id for r in results if r.market.grp == "sample"})
    profiled = sim["wallet_age"].notna().mean() if len(sim) else 0.0
    lines = [
        "# Phase 0 — Peut-on repérer les initiés à temps, et gagner en les suivant ?",
        "",
        f"Règle testée : **{rule.label()}**. Un *signal* est émis quand un wallet a acheté "
        "au moins le montant minimal d'une issue à bas prix ; c'est une *alerte* si le wallet "
        "est récent. Le suiveur achète la même issue au marché, avec retard, frais compris, et "
        "garde jusqu'à la résolution. Intervalles de confiance à 90 % par bootstrap "
        "d'événements.",
        "",
        f"Données : {len(results)} marchés résolus ({n_sample} tirés au hasard parmi les "
        f"marchés géopolitiques résolus entre oct. 2025 et oct. 2026, {n_events} événements ; "
        f"le reste = cas connus). Âge connu pour {profiled:.0%} des signaux.",
        "",
    ]
    lines += _case_section(results, sim, out_dir, profiles)
    lines += [
        "## 2. Échantillon large : les alertes battent-elles le hasard ?",
        "",
        _hit_table(sim, populations),
        "",
        "*Écart* = part d'issues gagnantes moins la probabilité implicite du prix payé. "
        "Un écart positif signifie que ces acheteurs savaient mieux que le marché.",
        "",
        _delay_table(sim, populations),
        "",
        "![Rendement selon le retard](rendement_selon_retard.png)",
        "",
    ]
    lines += _sensitivity(results, profiles, deposits, rule)
    report = out_dir / "rapport_phase0.md"
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log.info("Rapport écrit : %s", report)
    return report
