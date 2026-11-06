"""Client HTTP commun aux API publiques de Polymarket.

Il gère :
- la limitation de débit (au plus `rate_per_s` requêtes par seconde) ;
- les reprises sur 429 et 5xx, en respectant l'en-tête `Retry-After` ;
- un User-Agent explicite (Cloudflare rejette celui de Python par défaut) ;
- le contournement du cache CDN (CloudFront met en cache 5 min les URL identiques).
"""

from __future__ import annotations

import contextlib
import logging
import threading
import time
from collections.abc import Callable, Mapping
from typing import Any

import httpx

USER_AGENT = "radar/0.1 (outil de recherche personnel)"

log = logging.getLogger(__name__)

QueryValue = str | int | float | bool | list[str]


class ApiError(RuntimeError):
    """Erreur définitive renvoyée par une API (après épuisement des reprises)."""


class RateLimiter:
    """Espace les requêtes d'au moins `1 / rate_per_s` seconde. Utilisable par plusieurs threads."""

    def __init__(
        self,
        rate_per_s: float,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if rate_per_s <= 0:
            raise ValueError("rate_per_s doit être strictement positif")
        self._interval = 1.0 / rate_per_s
        self._clock = clock
        self._sleep = sleep
        self._next_slot = 0.0
        self._lock = threading.Lock()

    def wait(self) -> None:
        with self._lock:  # on réserve un créneau, puis on attend hors du verrou
            now = self._clock()
            slot = max(now, self._next_slot)
            self._next_slot = slot + self._interval
        if slot > now:
            self._sleep(slot - now)


class HttpClient:
    """Client JSON synchrone, poli envers l'API, avec reprises."""

    def __init__(
        self,
        base_url: str,
        *,
        rate_per_s: float = 5.0,
        timeout_s: float = 30.0,
        max_retries: int = 5,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url,
            timeout=timeout_s,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            transport=transport,
        )
        self._limiter = RateLimiter(rate_per_s, sleep=sleep)
        self._max_retries = max_retries
        self._sleep = sleep
        self._clock = clock

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> HttpClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def post_json(self, path: str, payload: Any) -> Any:
        """POST JSON avec les mêmes reprises que `get_json` (utilisé pour le JSON-RPC)."""
        return self._request("POST", path, payload=payload)

    def get_json(
        self,
        path: str,
        params: Mapping[str, QueryValue] | None = None,
        *,
        bust_cache: bool = False,
    ) -> Any:
        """GET `path` et renvoie le JSON décodé.

        `bust_cache=True` ajoute un paramètre variable pour obtenir une réponse fraîche.
        """
        query: dict[str, QueryValue] = dict(params or {})
        if bust_cache:
            query["_"] = str(int(self._clock() * 1000))
        return self._request("GET", path, params=_encode(query))

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: list[tuple[str, str | int | float | bool | None]] | None = None,
        payload: Any = None,
    ) -> Any:
        last_problem = ""
        for attempt in range(self._max_retries + 1):
            self._limiter.wait()
            try:
                response = self._client.request(method, path, params=params, json=payload)
            except httpx.TransportError as exc:
                last_problem = f"erreur réseau : {exc!r}"
                self._backoff(attempt, None)
                continue
            if response.status_code == 429 or response.status_code >= 500:
                last_problem = f"HTTP {response.status_code}"
                self._backoff(attempt, response.headers.get("Retry-After"))
                continue
            if response.status_code >= 400:
                raise ApiError(f"HTTP {response.status_code} sur {path} : {response.text[:300]}")
            return response.json()
        raise ApiError(
            f"échec après {self._max_retries + 1} tentatives sur {path} ({last_problem})"
        )

    def _backoff(self, attempt: int, retry_after: str | None) -> None:
        if attempt >= self._max_retries:
            return
        delay = min(2.0**attempt, 60.0)
        if retry_after is not None:
            with contextlib.suppress(ValueError):
                delay = max(delay, float(retry_after))
        log.warning("Nouvelle tentative dans %.1f s (tentative %d)", delay, attempt + 1)
        self._sleep(delay)


def _encode(query: Mapping[str, QueryValue]) -> list[tuple[str, str | int | float | bool | None]]:
    """Encode les paramètres : booléens en minuscules, listes en paramètres répétés."""
    items: list[tuple[str, str | int | float | bool | None]] = []
    for key, value in query.items():
        if isinstance(value, bool):
            items.append((key, "true" if value else "false"))
        elif isinstance(value, list):
            items.extend((key, str(v)) for v in value)
        else:
            items.append((key, str(value)))
    return items
