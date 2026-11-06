"""Accès à la Data API v2 de Polymarket (publique, sans clé, pagination par curseur)."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any

from radar.polymarket.http import HttpClient, QueryValue
from radar.polymarket.models import Activity, Trade

DATA_API_URL = "https://data-api.polymarket.com/v2"
MAX_PAGE_SIZE = 1000


class DataApi:
    def __init__(self, http: HttpClient | None = None) -> None:
        self._http = http or HttpClient(DATA_API_URL, rate_per_s=8.0)

    def close(self) -> None:
        self._http.close()

    def iter_rows(self, path: str, params: Mapping[str, QueryValue]) -> Iterator[dict[str, Any]]:
        """Parcourt toutes les pages d'une route paginée.

        Les mêmes filtres sont renvoyés à chaque page : la doc l'exige sur les flux, car le
        curseur ne porte que sa position.
        """
        cursor: str | None = None
        while True:
            query: dict[str, QueryValue] = dict(params)
            if cursor is not None:
                query["cursor"] = cursor
            payload = self._http.get_json(path, query)
            rows = payload.get("data") or []
            yield from rows
            pagination = payload.get("pagination") or {}
            cursor = pagination.get("next_cursor")
            if not cursor:
                return

    def market_trades(self, condition_id: str, *, taker_only: bool) -> Iterator[Trade]:
        """Tous les trades d'un marché, des plus récents aux plus anciens.

        Avec `taker_only=False`, chaque exécution apparaît aussi du côté de chaque maker.
        Dans ce mode, `start`/`end` sont ignorés par l'API : on parcourt donc tout le marché.
        """
        params: dict[str, QueryValue] = {
            "condition": condition_id,
            "limit": MAX_PAGE_SIZE,
            "taker_only": taker_only,
            "filter_type": "TOKENS",
            "filter_amount": 0,
        }
        for row in self.iter_rows("/trades", params):
            yield Trade.model_validate(row)

    def wallet_activity(
        self,
        wallet: str,
        *,
        types: list[str] | None = None,
        include_deposits_withdrawals: bool = False,
        start: int = 1,
        end: int | None = None,
        ascending: bool = False,
        limit: int | None = None,
    ) -> Iterator[Activity]:
        """Activité d'un wallet.

        `start=1` couvre tout l'historique (par défaut, l'API ne remonte qu'à 3 ans).

        `limit` borne le nombre total de lignes renvoyées (et pas seulement la taille de page).
        """
        page = MAX_PAGE_SIZE if limit is None else max(1, min(limit, MAX_PAGE_SIZE))
        params: dict[str, QueryValue] = {
            "user": wallet,
            "limit": page,
            "start": start,
            "sort_direction": "ASC" if ascending else "DESC",
            "exclude_deposits_withdrawals": not include_deposits_withdrawals,
        }
        if end is not None:
            params["end"] = end
        if types:
            params["type"] = ",".join(types)
        for count, row in enumerate(self.iter_rows("/activity", params), start=1):
            yield Activity.model_validate(row)
            if limit is not None and count >= limit:
                return
