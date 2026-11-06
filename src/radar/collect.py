"""Collecte : relie les clients d'API au stockage."""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed

from radar.polymarket.data_api import DataApi
from radar.polymarket.gamma import GammaApi
from radar.polymarket.models import Activity, Market
from radar.storage import repository
from radar.storage.repository import Conn, MarketCollection

log = logging.getLogger(__name__)


class Collector:
    def __init__(self, conn: Conn, data_api: DataApi, gamma: GammaApi) -> None:
        self.conn = conn
        self.data_api = data_api
        self.gamma = gamma

    def collect_markets(self, markets: Iterable[Market], *, skip_collected: bool = True) -> int:
        """Enregistre les métadonnées puis tous les trades de chaque marché."""
        markets = list(markets)
        repository.upsert_markets(self.conn, markets)
        done = repository.collected_conditions(self.conn) if skip_collected else set()
        n = 0
        for market in markets:
            if market.condition_id in done:
                continue
            result = self.collect_trades(market.condition_id)
            log.info(
                "%s : %d lignes (%d taker, %d non rapprochées) — %s",
                market.condition_id[:10],
                result.n_rows,
                result.n_taker_rows,
                result.n_unmatched_taker_rows,
                market.question[:70],
            )
            n += 1
        return n

    def collect_trades(self, condition_id: str) -> MarketCollection:
        all_rows = list(self.data_api.market_trades(condition_id, taker_only=False))
        taker_rows = list(self.data_api.market_trades(condition_id, taker_only=True))
        return repository.replace_market_trades(self.conn, condition_id, all_rows, taker_rows)

    def collect_conditions(self, condition_ids: list[str]) -> int:
        return self.collect_markets(self.gamma.markets(condition_ids))

    def collect_event(self, slug: str, *, question_pattern: str | None = None) -> int:
        markets = self.gamma.event_markets(slug)
        if question_pattern:
            regex = re.compile(question_pattern, re.IGNORECASE)
            markets = [m for m in markets if regex.search(m.question)]
        if not markets:
            log.warning("Aucun marché pour l'événement %s (filtre : %s)", slug, question_pattern)
        return self.collect_markets(markets)

    def fetch_profile(self, wallet: str, *, max_rows: int = 300) -> list[Activity]:
        """Les `max_rows` premières lignes d'activité du wallet, dépôts compris.

        La première ligne date la création du compte. Les dépôts plus tardifs ne sont pas vus,
        ce qui suffit pour juger un compte récent.
        """
        return list(
            self.data_api.wallet_activity(
                wallet, include_deposits_withdrawals=True, ascending=True, limit=max_rows
            )
        )

    def save_profile(self, wallet: str, rows: list[Activity]) -> None:
        first = rows[0].timestamp if rows else None
        deposits = [r for r in rows if r.type == "DEPOSIT"]
        repository.save_wallet_profile(self.conn, wallet, first, deposits)

    def profile_wallet(self, wallet: str) -> None:
        self.save_profile(wallet, self.fetch_profile(wallet))

    def profile_wallets(self, wallets: list[str], *, workers: int = 8) -> int:
        """Profile plusieurs wallets : requêtes en parallèle (débit limité), écritures en série."""
        done = 0
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(self.fetch_profile, w): w for w in wallets}
            for future in as_completed(futures):
                self.save_profile(futures[future], future.result())
                done += 1
                if done % 250 == 0:
                    log.info("… %d / %d wallets profilés", done, len(wallets))
        return done
