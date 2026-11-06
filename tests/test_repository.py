from __future__ import annotations

import psycopg
import pytest
from hypothesis import given
from hypothesis import strategies as st

from conftest import CONDITION, TOKEN_NO, WALLET_A, WALLET_B, WALLET_C, gamma_market, trade_row, ts
from radar.polymarket.models import Activity, Market, Trade
from radar.storage import db, repository

Conn = psycopg.Connection[tuple[object, ...]]


def make_trade(**kw: object) -> Trade:
    return Trade.model_validate(trade_row(**kw))


# --- Rapprochement taker / flux complet (logique pure) ------------------------------------


def test_flag_takers_handles_exact_duplicates() -> None:
    a = make_trade(proxy_wallet=WALLET_A)
    b = make_trade(proxy_wallet=WALLET_B, side="SELL")
    flags, unmatched = repository.flag_takers([a, b, a], [a, a])
    assert flags == [True, False, True]
    assert unmatched == 0


def test_flag_takers_reports_unmatched_taker_rows() -> None:
    a = make_trade(proxy_wallet=WALLET_A)
    c = make_trade(proxy_wallet=WALLET_C)
    flags, unmatched = repository.flag_takers([a], [a, c])
    assert flags == [True]
    assert unmatched == 1


@given(st.lists(st.sampled_from([WALLET_A, WALLET_B, WALLET_C]), max_size=30), st.data())
def test_flag_takers_counts_are_consistent(wallets: list[str], data: st.DataObject) -> None:
    rows = [make_trade(proxy_wallet=w) for w in wallets]
    takers = data.draw(st.lists(st.sampled_from(rows), max_size=len(rows))) if rows else []
    flags, unmatched = repository.flag_takers(rows, takers)
    assert sum(flags) + unmatched == len(takers)
    assert len(flags) == len(rows)


# --- Base de données -------------------------------------------------------------------------


@pytest.mark.db
def test_migrate_is_idempotent(conn: Conn) -> None:
    assert db.migrate(conn) == []


@pytest.mark.db
def test_upsert_market_then_update(conn: Conn) -> None:
    repository.upsert_markets(conn, [Market.from_gamma(gamma_market(closed=False))])
    repository.upsert_markets(conn, [Market.from_gamma(gamma_market())])
    row = conn.execute(
        "SELECT closed, winning_token_id, tags FROM markets WHERE condition_id = %s", (CONDITION,)
    ).fetchone()
    assert row == (True, "1001", ["geopolitics"])


@pytest.mark.db
def test_replace_market_trades_is_idempotent_and_ordered(conn: Conn) -> None:
    repository.upsert_markets(conn, [Market.from_gamma(gamma_market())])
    # Ordre de l'API : du plus récent au plus ancien.
    newest = make_trade(proxy_wallet=WALLET_B, timestamp=ts(3), price=0.9)
    maker = make_trade(proxy_wallet=WALLET_C, timestamp=ts(2), token_id=TOKEN_NO, price=0.7)
    taker = make_trade(proxy_wallet=WALLET_A, timestamp=ts(2), price=0.3)
    oldest = make_trade(proxy_wallet=WALLET_A, timestamp=ts(1), price=0.1)
    api_order = [newest, maker, taker, oldest]
    takers = [newest, taker, oldest]

    for _ in range(2):  # deux collectes successives donnent le même résultat
        result = repository.replace_market_trades(conn, CONDITION, api_order, takers)
    assert result.n_rows == 4
    assert result.n_unmatched_taker_rows == 0

    rows = conn.execute(
        "SELECT seq, wallet, price, is_taker FROM trades WHERE condition_id = %s ORDER BY seq",
        (CONDITION,),
    ).fetchall()
    assert [(r[1], r[2], r[3]) for r in rows] == [
        (WALLET_A, 0.1, True),
        (WALLET_A, 0.3, True),  # à horodatage égal, l'ordre chronologique de l'API est rétabli
        (WALLET_C, 0.7, False),
        (WALLET_B, 0.9, True),
    ]
    assert repository.collected_conditions(conn) == {CONDITION}


@pytest.mark.db
def test_save_wallet_profile_replaces_deposits(conn: Conn) -> None:
    deposit = Activity.model_validate(
        {
            "proxy_wallet": WALLET_A,
            "type": "DEPOSIT",
            "timestamp": ts(1),
            "usdc_size": 500.0,
            "transaction_hash": "0x01",
        }
    )
    repository.save_wallet_profile(conn, WALLET_A, deposit.timestamp, [deposit])
    repository.save_wallet_profile(conn, WALLET_A, deposit.timestamp, [deposit])
    count = conn.execute("SELECT count(*) FROM wallet_deposits").fetchone()
    assert count == (1,)
    assert repository.profiled_wallets(conn) == {WALLET_A}
