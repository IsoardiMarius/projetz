"""Test de bout en bout du rapport de la Phase 0, sur deux marchés fictifs."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import psycopg
import pytest

from conftest import gamma_market
from radar.phase0.report import build_report
from radar.polymarket.models import Activity, Market, Trade
from radar.storage import repository

Conn = psycopg.Connection[tuple[object, ...]]
T0 = datetime(2026, 2, 20, tzinfo=UTC)


def _trade(
    cond: str, token: str, wallet: str, minutes: int, side: str, size: float, price: float, tx: int
) -> Trade:
    return Trade.model_validate(
        {
            "proxy_wallet": wallet,
            "side": side,
            "token_id": token,
            "condition_id": cond,
            "size": size,
            "price": price,
            "timestamp": int((T0 + timedelta(minutes=minutes)).timestamp()),
            "outcome_index": 0,
            "transaction_hash": f"0x{tx:064x}",
        }
    )


def _seed_market(conn: Conn, cond: str, grp: str, case_key: str | None, yes: str, no: str) -> None:
    market = Market.from_gamma(
        gamma_market(
            conditionId=cond,
            clobTokenIds=f'["{yes}", "{no}"]',
            outcomePrices='["1", "0"]',
            closedTime=None,
            events=[{"id": cond[-3:], "slug": cond, "tags": [{"slug": "geopolitics"}]}],
        )
    )
    repository.upsert_markets(conn, [market])
    conn.execute("INSERT INTO phase0_markets VALUES (%s, %s, %s)", (cond, grp, case_key))
    insider, crowd = "0x" + "aa" * 20, "0x" + "cc" * 20
    trades = []
    tx = 0
    # Le marché croit à « non » pendant 2 jours, un wallet neuf achète « oui » à bas prix,
    # puis l'information tombe et « oui » passe à 95 ¢.
    for m in range(0, 2 * 24 * 60, 30):
        tx += 1
        trades.append(_trade(cond, yes, crowd, m, "BUY", 50, 0.10, tx))
    tx += 1
    trades.append(_trade(cond, yes, insider, 2 * 24 * 60 + 5, "BUY", 20_000, 0.10, tx))
    for m in range(2 * 24 * 60 + 10, 2 * 24 * 60 + 600, 10):
        tx += 1
        trades.append(_trade(cond, yes, crowd, m, "BUY", 50, 0.95 if m > 3000 else 0.30, tx))
    newest_first = list(reversed(trades))
    repository.replace_market_trades(conn, cond, newest_first, newest_first)
    for wallet, age_days in ((insider, 1), (crowd, 400)):
        first = T0 + timedelta(days=2) - timedelta(days=age_days)
        dep = Activity.model_validate(
            {
                "proxy_wallet": wallet,
                "type": "DEPOSIT",
                "timestamp": int(first.timestamp()),
                "usdc_size": 1e4,
                "transaction_hash": f"0xd{wallet[-4:]}",
            }
        )
        repository.save_wallet_profile(conn, wallet, first, [dep])


@pytest.mark.db
def test_build_report_end_to_end(conn: Conn, tmp_path: Path) -> None:
    _seed_market(conn, "0x" + "01" * 32, "case", "iran_strikes_2026", "11", "12")
    _seed_market(conn, "0x" + "02" * 32, "sample", None, "21", "22")
    report = build_report(conn, tmp_path)
    text = report.read_text(encoding="utf-8")
    assert "## 1. Les cas connus" in text
    assert "Frappes américaines sur l'Iran" in text
    assert "## 2. Échantillon large" in text
    assert "## 3. Sensibilité" in text
    assert "alerte" in text  # le wallet neuf est repéré dans le tableau rétrospectif
    assert (tmp_path / "rendement_selon_retard.png").exists()
