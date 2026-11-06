"""Origine des fonds d'un wallet Polymarket, lue dans les reçus de transaction Polygon.

Deux schémas de dépôt coexistent :
- avant le 28/04/2026 : un transfert d'USDC.e arrive directement sur le wallet. L'expéditeur
  est souvent un « hub » (relais d'exchange ou de bridge) partagé par des milliers de comptes ;
- après : l'USDC d'une adresse personnelle est converti en pUSD, frappé vers le wallet.
  L'expéditeur de l'USDC est alors le vrai financeur.

Règle unique : le financeur est l'expéditeur du premier transfert ERC-20 de la transaction qui
ne vient ni de l'adresse nulle, ni d'un contrat Polymarket connu. Les hubs sont repérés ensuite,
par le nombre de wallets qu'ils financent.
"""

from __future__ import annotations

from typing import Any

from radar.polymarket.http import ApiError, HttpClient

TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
ZERO = "0x" + "0" * 40
POLYMARKET_CONTRACTS = frozenset(
    a.lower()
    for a in (
        "0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB",  # pUSD
        "0x93070a847efEf7F70739046A929D47a521F5B8ee",  # CollateralOnramp
        "0xE111180000d2663C0091e4f400237545B87B996B",  # CTF Exchange
        "0xe2222d279d744050d28e00520010520000310F59",  # Neg Risk CTF Exchange
        "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045",  # CTF
        "0x4bfb41d5b3570defd03c39a9a4d8de6bd8b8982e",  # ancien CTF Exchange
    )
)
COLLATERAL_TOKENS = frozenset(
    a.lower()
    for a in (
        "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",  # USDC.e
        "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",  # USDC natif
        "0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB",  # pUSD
    )
)
DEFAULT_RPC = "https://polygon.drpc.org"


def _address(topic: str) -> str:
    return "0x" + topic[-40:].lower()


def extract_funder(receipt: dict[str, Any], wallet: str) -> str | None:
    """Expéditeur réel des fonds d'un dépôt (voir la règle en tête du module)."""
    wallet = wallet.lower()
    for entry in receipt.get("logs") or []:
        topics = entry.get("topics") or []
        if len(topics) < 3 or topics[0].lower() != TRANSFER_TOPIC:
            continue
        if str(entry.get("address", "")).lower() not in COLLATERAL_TOKENS:
            continue
        sender = _address(topics[1])
        if sender in (ZERO, wallet) or sender in POLYMARKET_CONTRACTS:
            continue
        return sender
    return None


class PolygonRpc:
    def __init__(self, url: str = DEFAULT_RPC, http: HttpClient | None = None) -> None:
        self._url = url
        self._http = http or HttpClient(url, rate_per_s=8.0)
        self._id = 0

    def receipt(self, tx_hash: str) -> dict[str, Any] | None:
        self._id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._id,
            "method": "eth_getTransactionReceipt",
            "params": [tx_hash],
        }
        answer = self._http.post_json("", payload)
        if not isinstance(answer, dict):
            raise ApiError("réponse RPC inattendue")
        if answer.get("error"):
            raise ApiError(f"erreur RPC : {answer['error']}")
        result = answer.get("result")
        return result if isinstance(result, dict) else None
