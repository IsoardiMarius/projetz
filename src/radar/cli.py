"""Interface en ligne de commande : `uv run radar --help`."""

from __future__ import annotations

import argparse
import logging
import sys

from radar.collect import Collector
from radar.polymarket.data_api import DataApi
from radar.polymarket.gamma import GammaApi
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
        collector = Collector(conn, DataApi(), GammaApi())
        if args.command == "collect-market":
            collector.collect_conditions(args.condition)
        elif args.command == "collect-event":
            collector.collect_event(args.slug, question_pattern=args.question)
        elif args.command == "profile-wallet":
            for wallet in args.wallet:
                collector.profile_wallet(wallet.lower())
    return 0


if __name__ == "__main__":
    sys.exit(main())
