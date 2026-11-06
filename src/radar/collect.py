"""Collecte : relie les clients d'API au stockage."""

from __future__ import annotations

import logging
import re
from collections import Counter
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from radar.chain.funding import PolygonRpc, extract_funder
from radar.polymarket.data_api import DataApi
from radar.polymarket.gamma import GammaApi
from radar.polymarket.http import ApiError
from radar.polymarket.models import Activity, Market
from radar.storage import repository
from radar.storage.repository import Conn, MarketCollection

log = logging.getLogger(__name__)


class Collector:
    def __init__(
        self,
        conn: Conn,
        data_api: DataApi,
        gamma: GammaApi,
        connect: Callable[[], Conn] | None = None,
    ) -> None:
        self.conn = conn
        self.data_api = data_api
        self.gamma = gamma
        self.connect = connect  # fabrique de connexions pour les tâches parallèles

    def collect_markets(
        self, markets: Iterable[Market], *, skip_collected: bool = True, workers: int = 4
    ) -> int:
        """Enregistre les métadonnées puis tous les trades de chaque marché.

        Les marchés sont traités en parallèle, chacun sur sa propre connexion, et leurs lignes
        sont écrites au fil de l'eau (mémoire bornée). Le débit global reste plafonné par le
        client HTTP partagé.
        """
        markets = list(markets)
        repository.upsert_markets(self.conn, markets)
        done = repository.collected_conditions(self.conn) if skip_collected else set()
        todo = [m for m in markets if m.condition_id not in done]
        if self.connect is None or workers <= 1:
            for n, market in enumerate(todo, start=1):
                self._log(n, len(todo), market, self.collect_trades(market.condition_id))
            return len(todo)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(self._collect_isolated, m.condition_id): m for m in todo}
            for n, future in enumerate(as_completed(futures), start=1):
                self._log(n, len(todo), futures[future], future.result())
        return len(todo)

    def _collect_isolated(self, condition_id: str) -> MarketCollection:
        assert self.connect is not None
        with self.connect() as conn:
            return self.collect_trades(condition_id, conn=conn)

    @staticmethod
    def _log(n: int, total: int, market: Market, result: MarketCollection) -> None:
        log.info(
            "[%d/%d] %s : %d lignes (%d taker, %d non rapprochées) — %s",
            n,
            total,
            market.condition_id[:10],
            result.n_rows,
            result.n_taker_rows,
            result.n_unmatched_taker_rows,
            market.question[:60],
        )

    def collect_trades(self, condition_id: str, *, conn: Conn | None = None) -> MarketCollection:
        """Collecte en deux temps : clés des lignes taker, puis flux complet écrit en direct."""
        keys = Counter(
            r.match_key() for r in self.data_api.market_trade_rows(condition_id, taker_only=True)
        )
        rows = self.data_api.market_trade_rows(condition_id, taker_only=False)
        return repository.stream_market_trades(conn or self.conn, condition_id, rows, keys)

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
