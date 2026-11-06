"""Modèles des réponses des API Polymarket.

Minimisation des données : seuls les champs utiles à l'analyse sont conservés. Le nom
affiché, le pseudonyme, la bio et les images de profil renvoyés par l'API sont
volontairement ignorés.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Literal, NamedTuple

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _from_epoch(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromtimestamp(int(value), tz=UTC)


class _ApiModel(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True, populate_by_name=True)


class TradeRow(NamedTuple):
    """Ligne de trade légère, pour la collecte en masse (pas d'objet pydantic par ligne)."""

    ts: datetime
    wallet: str
    token_id: str
    outcome_index: int | None
    side: str
    size: float
    price: float
    tx_hash: str

    @classmethod
    def from_api(cls, row: dict[str, Any]) -> TradeRow:
        side = str(row["side"])
        if side not in ("BUY", "SELL"):
            raise ValueError(f"côté inconnu : {side!r}")
        index = row.get("outcome_index")
        return cls(
            ts=_from_epoch(row["timestamp"]),
            wallet=str(row["proxy_wallet"]).lower(),
            token_id=str(row["token_id"]),
            outcome_index=None if index is None else int(index),
            side=side,
            size=float(row["size"]),
            price=float(row["price"]),
            tx_hash=str(row["transaction_hash"]),
        )

    @classmethod
    def from_trade(cls, t: Trade) -> TradeRow:
        return cls(
            t.timestamp,
            t.wallet,
            t.token_id,
            t.outcome_index,
            t.side,
            t.size,
            t.price,
            t.transaction_hash,
        )

    def match_key(self) -> tuple[str, str, str, str, float, float]:
        return (self.tx_hash, self.wallet, self.token_id, self.side, self.size, self.price)


class Trade(_ApiModel):
    """Une exécution (fill) vue du côté d'un wallet, telle que renvoyée par `/v2/trades`."""

    wallet: str = Field(alias="proxy_wallet")
    side: Literal["BUY", "SELL"]
    token_id: str
    condition_id: str
    size: float
    price: float
    timestamp: datetime
    outcome_index: int | None = None
    transaction_hash: str

    _normalize_ts = field_validator("timestamp", mode="before")(_from_epoch)

    @field_validator("wallet")
    @classmethod
    def _lower_wallet(cls, value: str) -> str:
        return value.lower()

    def match_key(self) -> tuple[str, str, str, str, float, float]:
        """Clé qui identifie une ligne pour rapprocher les flux taker et taker+maker."""
        return (self.transaction_hash, self.wallet, self.token_id, self.side, self.size, self.price)


ActivityType = Literal[
    "TRADE",
    "SPLIT",
    "MERGE",
    "REDEEM",
    "REWARD",
    "CONVERSION",
    "MIGRATION",
    "YIELD",
    "MAKER_REBATE",
    "TAKER_REBATE",
    "REFERRAL_REWARD",
    "DEPOSIT",
    "WITHDRAWAL",
    "DIRECTIONAL_SPLIT",
    "DIRECTIONAL_MERGE",
    "THRESHOLD_COMPOSE",
    "THRESHOLD_DECOMPOSE",
    "TIP",
]


class Activity(_ApiModel):
    """Une ligne d'activité d'un wallet (`/v2/activity`)."""

    wallet: str = Field(alias="proxy_wallet")
    type: str
    timestamp: datetime
    condition_id: str = ""
    token_id: str = ""
    side: str = ""
    size: float | None = None
    usdc_size: float | None = None
    price: float | None = None
    transaction_hash: str = ""

    _normalize_ts = field_validator("timestamp", mode="before")(_from_epoch)

    @field_validator("wallet")
    @classmethod
    def _lower_wallet(cls, value: str) -> str:
        return value.lower()


class Outcome(_ApiModel):
    token_id: str
    label: str
    final_price: float | None = None


class Market(_ApiModel):
    """Métadonnées d'un marché (Gamma `/markets`)."""

    market_id: str = Field(alias="id")
    condition_id: str = Field(alias="conditionId")
    question: str
    slug: str | None = None
    group_item_title: str | None = Field(default=None, alias="groupItemTitle")
    event_id: str | None = None
    event_slug: str | None = None
    tags: tuple[str, ...] = ()
    fee_type: str | None = Field(default=None, alias="feeType")
    neg_risk: bool = Field(default=False, alias="negRisk")
    start_date: datetime | None = Field(default=None, alias="startDate")
    end_date: datetime | None = Field(default=None, alias="endDate")
    closed_time: datetime | None = Field(default=None, alias="closedTime")
    closed: bool = False
    volume: float | None = Field(default=None, alias="volumeNum")
    resolution_status: str | None = Field(default=None, alias="umaResolutionStatus")
    outcomes: tuple[Outcome, ...] = ()

    @field_validator("closed_time", mode="before")
    @classmethod
    def _parse_closed_time(cls, value: Any) -> Any:
        # Gamma renvoie parfois « 2026-04-01 07:13:31+00 », que pydantic ne lit pas tel quel.
        if isinstance(value, str) and value.endswith("+00") and "T" not in value:
            return value.replace(" ", "T") + ":00"
        return value

    @property
    def winning_token_id(self) -> str | None:
        """Token gagnant si le marché est résolu (prix final à 1), sinon None."""
        if not self.closed:
            return None
        winners = [o.token_id for o in self.outcomes if o.final_price == 1.0]
        return winners[0] if len(winners) == 1 else None

    @classmethod
    def from_gamma(cls, raw: dict[str, Any], *, event: dict[str, Any] | None = None) -> Market:
        """Construit un marché depuis une ligne Gamma (certains champs y sont des chaînes JSON)."""
        token_ids = _json_list(raw.get("clobTokenIds"))
        labels = _json_list(raw.get("outcomes"))
        prices = _json_list(raw.get("outcomePrices"))
        outcomes = tuple(
            Outcome(
                token_id=str(token),
                label=str(labels[i]) if i < len(labels) else str(i),
                final_price=float(prices[i]) if i < len(prices) and prices[i] != "" else None,
            )
            for i, token in enumerate(token_ids)
        )
        parent = event or (raw.get("events") or [None])[0] or {}
        tags = tuple(
            str(t.get("slug"))
            for t in (parent.get("tags") or raw.get("tags") or [])
            if t.get("slug")
        )
        data = dict(raw)
        data.update(
            outcomes=outcomes,
            event_id=str(parent["id"]) if parent.get("id") is not None else None,
            event_slug=parent.get("slug"),
            tags=tags,
        )
        if data.get("volumeNum") is None and data.get("volume") not in (None, ""):
            data["volumeNum"] = float(data["volume"])
        return cls.model_validate(data)


def _json_list(value: Any) -> list[Any]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return value
    parsed = json.loads(value)
    return parsed if isinstance(parsed, list) else []
