"""Collecte : relie les clients d'API au stockage."""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable

from radar.polymarket.data_api import DataApi
from radar.polymarket.gamma import GammaApi
from radar.polymarket.models import Market
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

    def profile_wallet(self, wallet: str) -> None:
        """Âge du wallet (première activité, dépôts compris) et liste de ses dépôts."""
        first = next(
            self.data_api.wallet_activity(
                wallet, include_deposits_withdrawals=True, ascending=True, limit=1
            ),
            None,
        )
        deposits = list(
            self.data_api.wallet_activity(
                wallet,
                types=["DEPOSIT"],
                include_deposits_withdrawals=True,
                ascending=True,
                limit=200,
            )
        )
        repository.save_wallet_profile(
            self.conn, wallet, first.timestamp if first else None, deposits
        )
