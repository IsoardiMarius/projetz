"""Accès à l'API Gamma de Polymarket (métadonnées des marchés et des événements)."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from typing import Any

from radar.polymarket.http import HttpClient, QueryValue
from radar.polymarket.models import Market

GAMMA_URL = "https://gamma-api.polymarket.com"
_CONDITIONS_PER_REQUEST = 20


class GammaApi:
    def __init__(self, http: HttpClient | None = None) -> None:
        self._http = http or HttpClient(GAMMA_URL, rate_per_s=8.0)

    def close(self) -> None:
        self._http.close()

    def event(self, slug: str) -> dict[str, Any] | None:
        """Un événement et ses marchés, ou None s'il n'existe pas."""
        rows = self._http.get_json("/events", {"slug": slug})
        return rows[0] if rows else None

    def event_markets(self, slug: str) -> list[Market]:
        event = self.event(slug)
        if event is None:
            return []
        return [Market.from_gamma(m, event=event) for m in event.get("markets") or []]

    def markets(self, condition_ids: Sequence[str]) -> list[Market]:
        """Métadonnées de marchés, ouverts ou fermés, par identifiant de condition."""
        result: list[Market] = []
        for i in range(0, len(condition_ids), _CONDITIONS_PER_REQUEST):
            chunk = list(condition_ids[i : i + _CONDITIONS_PER_REQUEST])
            for closed in (True, False):
                params: dict[str, QueryValue] = {
                    "condition_ids": chunk,
                    "closed": closed,
                    "limit": len(chunk),
                }
                rows = self._http.get_json("/markets", params)
                result.extend(Market.from_gamma(r) for r in rows)
        return result

    def iter_closed_events(
        self,
        *,
        tag_slug: str,
        end_date_min: str,
        end_date_max: str,
        page_size: int = 100,
    ) -> Iterator[dict[str, Any]]:
        """Événements fermés d'un thème, dont la date de fin est dans l'intervalle (ISO 8601)."""
        offset = 0
        while True:
            params: dict[str, QueryValue] = {
                "closed": True,
                "tag_slug": tag_slug,
                "end_date_min": end_date_min,
                "end_date_max": end_date_max,
                "limit": page_size,
                "offset": offset,
                "order": "endDate",
                "ascending": True,
            }
            rows = self._http.get_json("/events", params)
            if not rows:
                return
            yield from rows
            if len(rows) < page_size:
                return
            offset += page_size
