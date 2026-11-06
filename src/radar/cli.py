"""Interface en ligne de commande : `uv run radar --help`."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from radar.analysis import detector
from radar.chain.funding import DEFAULT_RPC, PolygonRpc
from radar.collect import Collector, trace_funders
from radar.phase0 import analyze as phase0_analyze
from radar.phase0 import collect as phase0_collect
from radar.phase0 import edge_study as phase0_edge
from radar.phase0 import report as phase0_report
from radar.phase0.sample import SampleSpec
from radar.polymarket.data_api import DATA_API_URL, DataApi
from radar.polymarket.gamma import GammaApi
from radar.polymarket.http import HttpClient
from radar.storage import db


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="radar", description="Analyse personnelle de Polymarket")
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("migrate", help="crée ou met à jour le schéma de la base")

    p_market = sub.add_parser("collect-market", help="collecte tous les trades de marchés")
    p_market.add_argument("--condition", action="append", required=True)

    p_event = sub.add_parser("collect-event", help="collecte les marchés d'un événement")
    p_event.add_argument("--slug", required=True)
    p_event.add_argument("--question", help="expression régulière pour filtrer les marchés")

    p_wallet = sub.add_parser("profile-wallet", help="âge et dépôts de wallets")
    p_wallet.add_argument("--wallet", action="append", required=True)

    p_phase0 = sub.add_parser("phase0-collect", help="collecte les données de la Phase 0")
    p_phase0.add_argument("--cases", action="store_true", help="marchés des cas connus")
    p_phase0.add_argument("--sample", type=int, metavar="N", help="échantillon de N marchés")

    sub.add_parser(
        "phase0-profile", help="âge et dépôts des wallets ayant émis un signal (Phase 0)"
    )
    p_report = sub.add_parser("phase0-report", help="rapport de la Phase 0 (local)")
    p_report.add_argument("--out", type=Path, default=Path("reports/phase0"))

    p_edge = sub.add_parser("phase0-edge", help="étude du détecteur v2 (local)")
    p_edge.add_argument("--out", type=Path, default=Path("reports/phase0"))

    p_fund = sub.add_parser("trace-funders", help="origine des fonds des wallets à signal")
    p_fund.add_argument("--rpc", default=DEFAULT_RPC, help="nœud RPC Polygon (lecture seule)")
    p_fund.add_argument("--young-only", action="store_true", help="seulement les wallets ≤ 30 j")

    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.DEBUG if args.verbose else logging.WARNING)

    with db.connect() as conn:
        if args.command == "migrate":
            applied = db.migrate(conn)
            print("Migrations appliquées :", ", ".join(applied) or "aucune")
            return 0
        collector = Collector(
            conn,
            DataApi(HttpClient(DATA_API_URL, rate_per_s=25.0)),
            GammaApi(),
            connect=db.connect,
        )
        if args.command == "collect-market":
            collector.collect_conditions(args.condition)
        elif args.command == "collect-event":
            collector.collect_event(args.slug, question_pattern=args.question)
        elif args.command == "phase0-collect":
            if args.cases:
                phase0_collect.collect_cases(collector)
            if args.sample:
                phase0_collect.collect_sample(collector, SampleSpec(size=args.sample))
        elif args.command == "phase0-profile":
            # Règle la plus large de l'analyse de sensibilité : couvre tous les réglages testés.
            loosest = detector.Rule(max_price=0.5, min_usdc=500)
            phase0_analyze.profile_signal_wallets(collector, loosest)
        elif args.command == "phase0-report":
            report = phase0_report.build_report(conn, args.out)
            print(f"Rapport : {report}")
        elif args.command == "phase0-edge":
            study = phase0_edge.run(conn, args.out)
            print(f"Rapport : {study.report}")
        elif args.command == "trace-funders":
            wallets = phase0_analyze.signal_wallets(
                conn, young_days=30 if args.young_only else None
            )
            trace_funders(conn, PolygonRpc(args.rpc), wallets)
        elif args.command == "profile-wallet":
            for wallet in args.wallet:
                collector.profile_wallet(wallet.lower())
    return 0


if __name__ == "__main__":
    sys.exit(main())
