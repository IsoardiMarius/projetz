from __future__ import annotations

import httpx

from conftest import CONDITION, WALLET_A, trade_row
from radar.polymarket.data_api import DataApi
from radar.polymarket.http import HttpClient


def paged_handler(pages: list[list[dict[str, object]]], seen: list[httpx.Request]):  # type: ignore[no-untyped-def]
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        cursor = request.url.params.get("cursor")
        index = 0 if cursor is None else int(cursor)
        next_cursor = str(index + 1) if index + 1 < len(pages) else None
        return httpx.Response(
            200,
            json={
                "data": pages[index],
                "pagination": {"has_more": next_cursor is not None, "next_cursor": next_cursor},
            },
        )

    return handler


def make_api(handler) -> DataApi:  # type: ignore[no-untyped-def]
    http = HttpClient(
        "https://data.example.invalid",
        transport=httpx.MockTransport(handler),
        sleep=lambda s: None,
        rate_per_s=1000.0,
    )
    return DataApi(http)


def test_market_trades_walks_all_pages_with_same_filters() -> None:
    seen: list[httpx.Request] = []
    pages = [[trade_row(size=1.0), trade_row(size=2.0)], [trade_row(size=3.0)]]
    api = make_api(paged_handler(pages, seen))
    trades = list(api.market_trades(CONDITION, taker_only=False))
    assert [t.size for t in trades] == [1.0, 2.0, 3.0]
    assert len(seen) == 2
    for request in seen:  # la doc exige de renvoyer les mêmes filtres à chaque page
        assert request.url.params["condition"] == CONDITION
        assert request.url.params["taker_only"] == "false"
    assert seen[1].url.params["cursor"] == "1"


def test_wallet_activity_limit_caps_total_rows() -> None:
    seen: list[httpx.Request] = []
    row = {
        "proxy_wallet": WALLET_A,
        "type": "DEPOSIT",
        "timestamp": 1770000000,
        "usdc_size": 50.0,
        "transaction_hash": "0x01",
    }
    api = make_api(paged_handler([[row, row], [row, row]], seen))
    rows = list(
        api.wallet_activity(
            WALLET_A, types=["DEPOSIT"], include_deposits_withdrawals=True, ascending=True, limit=3
        )
    )
    assert len(rows) == 3
    first = seen[0].url.params
    assert first["exclude_deposits_withdrawals"] == "false"
    assert first["sort_direction"] == "ASC"
    assert first["type"] == "DEPOSIT"
    assert first["start"] == "1"
