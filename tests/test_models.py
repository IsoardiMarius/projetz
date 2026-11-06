from __future__ import annotations

from datetime import UTC, datetime

from conftest import CONDITION, TOKEN_NO, TOKEN_YES, WALLET_A, gamma_market, trade_row
from radar.polymarket.models import Market, Trade


def test_trade_keeps_only_needed_fields_and_normalizes() -> None:
    trade = Trade.model_validate(trade_row())
    assert trade.wallet == WALLET_A  # adresse en minuscules
    assert trade.timestamp == datetime(2026, 2, 1, tzinfo=UTC)
    dumped = trade.model_dump()
    for private_field in ("name", "pseudonym", "bio", "profile_image"):
        assert private_field not in dumped


def test_market_from_gamma_parses_json_strings_and_winner() -> None:
    market = Market.from_gamma(gamma_market())
    assert market.condition_id == CONDITION
    assert [o.token_id for o in market.outcomes] == [TOKEN_YES, TOKEN_NO]
    assert [o.label for o in market.outcomes] == ["Yes", "No"]
    assert market.winning_token_id == TOKEN_YES
    assert market.tags == ("geopolitics",)
    assert market.event_slug == "evenement-fictif"
    assert market.closed_time == datetime(2026, 3, 1, 7, 13, 31, tzinfo=UTC)
    assert market.volume == 123456.7


def test_market_without_clear_winner() -> None:
    open_market = Market.from_gamma(gamma_market(closed=False))
    assert open_market.winning_token_id is None
    ambiguous = Market.from_gamma(gamma_market(outcomePrices='["0.5", "0.5"]'))
    assert ambiguous.winning_token_id is None


def test_market_uses_explicit_event_over_embedded() -> None:
    event = {"id": 99, "slug": "autre-evenement", "tags": [{"slug": "politics"}]}
    market = Market.from_gamma(gamma_market(), event=event)
    assert market.event_id == "99"
    assert market.tags == ("politics",)
