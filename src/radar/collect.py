"""Collecte : relie les clients d'API au stockage."""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from radar.chain.funding import PolygonRpc, extract_funder
from radar.polymarket.data_api import DataApi
from radar.polymarket.gamma import GammaApi
from radar.polymarket.http import ApiError
from radar.polymarket.models import Activity, Market, Trade
from radar.storage import repository
from radar.storage.repository import Conn, MarketCollection

log = logging.getLogger(__name__)


class Collector:
    def __init__(self, conn: Conn, data_api: DataApi, gamma: GammaApi) -> None:
        self.conn = conn
        self.data_api = data_api
        self.gamma = gamma

    def collect_markets(
        self, markets: Iterable[Market], *, skip_collected: bool = True, workers: int = 6
    ) -> int:
        """Enregistre les métadonnées puis tous les trades de chaque marché.

        Les marchés sont téléchargés en parallèle (le débit global reste plafonné par le client
        HTTP), puis écrits un par un dans la base, dans l'ordre où ils arrivent.
        """
        markets = list(markets)
        repository.upsert_markets(self.conn, markets)
        done = repository.collected_conditions(self.conn) if skip_collected else set()
        todo = [m for m in markets if m.condition_id not in done]
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(self.fetch_trades, m.condition_id): m for m in todo}
            for n, future in enumerate(as_completed(futures), start=1):
                market = futures[future]
                all_rows, taker_rows = future.result()
                result = repository.replace_market_trades(
                    self.conn, market.condition_id, all_rows, taker_rows
                )
                log.info(
                    "[%d/%d] %s : %d lignes (%d taker, %d non rapprochées) — %s",
                    n,
                    len(todo),
                    market.condition_id[:10],
                    result.n_rows,
                    result.n_taker_rows,
                    result.n_unmatched_taker_rows,
                    market.question[:60],
                )
        return len(todo)

    def fetch_trades(self, condition_id: str) -> tuple[list[Trade], list[Trade]]:
        """Les deux flux d'un marché : toutes les lignes, et les seules lignes taker."""
        all_rows = list(self.data_api.market_trades(condition_id, taker_only=False))
        taker_rows = list(self.data_api.market_trades(condition_id, taker_only=True))
        return all_rows, taker_rows

    def collect_trades(self, condition_id: str) -> MarketCollection:
        all_rows, taker_rows = self.fetch_trades(condition_id)
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


def trace_funders(conn: Conn, rpc: PolygonRpc, wallets: Iterable[str], *, workers: int = 6) -> int:
    """Cherche l'expéditeur réel de chaque dépôt pas encore tracé de ces wallets."""
    todo = repository.untraced_deposits(conn, wallets)
    log.info("%d dépôts à tracer", len(todo))

    def fetch(item: tuple[str, str, datetime]) -> str | None:
        receipt = rpc.receipt(item[1])
        return extract_funder(receipt, item[0]) if receipt else None

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fetch, item): item for item in todo}
        for n, future in enumerate(as_completed(futures), start=1):
            wallet, tx_hash, ts = futures[future]
            try:
                funder = future.result()
            except ApiError as exc:
                log.warning("Dépôt %s non tracé : %s", tx_hash[:12], exc)
                continue
            repository.save_funder(conn, wallet, tx_hash, funder, ts)
            if n % 500 == 0:
                log.info("… %d / %d dépôts tracés", n, len(todo))
    return len(todo)
