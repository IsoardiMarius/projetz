"""Fixtures communes. Toutes les données de test sont fictives."""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import psycopg
import pytest

from radar.storage import db

TEST_DB_ENV = "RADAR_TEST_DATABASE_URL"

WALLET_A = "0x" + "a1" * 20
WALLET_B = "0x" + "b2" * 20
WALLET_C = "0x" + "c3" * 20
CONDITION = "0x" + "11" * 32
TOKEN_YES = "1001"
TOKEN_NO = "1002"


def ts(day: int, hour: int = 0, minute: int = 0) -> int:
    return int(datetime(2026, 2, day, hour, minute, tzinfo=UTC).timestamp())


def trade_row(**overrides: Any) -> dict[str, Any]:
    """Une ligne `/v2/trades` fictive, avec les champs de profil que l'on doit ignorer."""
    row: dict[str, Any] = {
        "proxy_wallet": WALLET_A.upper().replace("0X", "0x"),
        "side": "BUY",
        "token_id": TOKEN_YES,
        "condition_id": CONDITION,
        "size": 100.0,
        "price": 0.2,
        "timestamp": ts(1),
        "title": "Marché fictif ?",
        "slug": "marche-fictif",
        "event_slug": "evenement-fictif",
        "outcome": "Yes",
        "outcome_index": 0,
        "name": "pseudo-fictif",
        "pseudonym": "Generated-Name",
        "bio": "texte de profil à ne pas conserver",
        "profile_image": "https://example.invalid/img.png",
        "transaction_hash": "0x" + "ee" * 32,
    }
    row.update(overrides)
    return row


def gamma_market(**overrides: Any) -> dict[str, Any]:
    raw: dict[str, Any] = {
        "id": "42",
        "conditionId": CONDITION,
        "question": "Événement fictif avant le 28 février ?",
        "slug": "evenement-fictif-28-fevrier",
        "groupItemTitle": "28 février",
        "outcomes": '["Yes", "No"]',
        "outcomePrices": '["1", "0"]',
        "clobTokenIds": f'["{TOKEN_YES}", "{TOKEN_NO}"]',
        "closed": True,
        "closedTime": "2026-03-01 07:13:31+00",
        "startDate": "2026-01-15T00:00:00Z",
        "endDate": "2026-02-28T00:00:00Z",
        "negRisk": False,
        "volume": "123456.7",
        "umaResolutionStatus": "resolved",
        "events": [{"id": 7, "slug": "evenement-fictif", "tags": [{"slug": "geopolitics"}]}],
    }
    raw.update(overrides)
    return raw


@pytest.fixture
def conn() -> Iterator[psycopg.Connection[tuple[object, ...]]]:
    url = os.environ.get(TEST_DB_ENV)
    if not url:
        pytest.skip(f"{TEST_DB_ENV} non défini : tests de base de données ignorés")
    with psycopg.connect(url, autocommit=True) as c:
        c.execute("DROP SCHEMA public CASCADE")
        c.execute("CREATE SCHEMA public")
        db.migrate(c)
        yield c
