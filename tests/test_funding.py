"""Tests de l'extraction de l'origine des fonds, sur des reçus fictifs."""

from __future__ import annotations

import httpx
import pytest

from radar.chain.funding import TRANSFER_TOPIC, PolygonRpc, extract_funder
from radar.polymarket.http import ApiError, HttpClient

USDCE = "0x2791bca1f2de4661ed88a30c99a7a9449aa84174"
PUSD = "0xc011a7e12a19f7b1f670d46f03b03f3342e82dfb"
WALLET = "0x" + "aa" * 20
HUB = "0x" + "bb" * 20
OWNER = "0x" + "cc" * 20


def topic(addr: str) -> str:
    return "0x" + "0" * 24 + addr[2:]


def transfer(token: str, sender: str, receiver: str) -> dict[str, object]:
    return {"address": token, "topics": [TRANSFER_TOPIC, topic(sender), topic(receiver)]}


def test_old_scheme_direct_usdce_transfer_from_hub() -> None:
    receipt = {"logs": [transfer(USDCE, HUB, WALLET)]}
    assert extract_funder(receipt, WALLET) == HUB


def test_new_scheme_owner_usdc_wrapped_then_pusd_minted() -> None:
    receipt = {
        "logs": [
            {"address": "0x" + "88" * 20, "topics": ["0x7a27", topic(OWNER), topic(HUB)]},
            transfer(USDCE, OWNER, PUSD),  # l'USDC du propriétaire part vers le contrat pUSD
            transfer(PUSD, "0x" + "0" * 40, WALLET),  # frappe du pUSD vers le wallet
        ]
    }
    assert extract_funder(receipt, WALLET) == OWNER


def test_no_funder_when_only_mint() -> None:
    receipt = {"logs": [transfer(PUSD, "0x" + "0" * 40, WALLET)]}
    assert extract_funder(receipt, WALLET) is None


def test_rpc_client_posts_json_rpc_and_raises_on_error() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if b"0xbad" in request.content:
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "error": {"code": -1}})
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": {"logs": []}})

    http = HttpClient(
        "https://rpc.example.invalid",
        transport=httpx.MockTransport(handler),
        sleep=lambda s: None,
        rate_per_s=1000.0,
    )
    rpc = PolygonRpc("https://rpc.example.invalid", http=http)
    assert rpc.receipt("0x01") == {"logs": []}
    assert seen[0].method == "POST"
    assert b"eth_getTransactionReceipt" in seen[0].content
    with pytest.raises(ApiError, match="erreur RPC"):
        rpc.receipt("0xbad")
