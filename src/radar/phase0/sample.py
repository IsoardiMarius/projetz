"""Échantillon large de marchés résolus, pour ne pas juger le détecteur sur les seuls cas connus."""

from __future__ import annotations

import random
from collections.abc import Iterable
from dataclasses import dataclass

from radar.polymarket.gamma import GammaApi
from radar.polymarket.models import Market


@dataclass(frozen=True)
class SampleSpec:
    tag_slug: str = "geopolitics"
    end_date_min: str = "2025-10-01T00:00:00Z"
    end_date_max: str = "2026-10-31T00:00:00Z"
    min_volume: float = 50_000
    max_volume: float = 30_000_000
    size: int = 250
    seed: int = 20261106


def eligible(market: Market, spec: SampleSpec) -> bool:
    """Marché fermé, avec un gagnant net, et un volume dans les bornes."""
    return (
        market.closed
        and market.winning_token_id is not None
        and market.volume is not None
        and spec.min_volume <= market.volume <= spec.max_volume
    )


def draw_sample(candidates: Iterable[Market], spec: SampleSpec, exclude: set[str]) -> list[Market]:
    """Tirage aléatoire reproductible (graine fixe), sans les marchés exclus."""
    pool = sorted(
        (m for m in candidates if eligible(m, spec) and m.condition_id not in exclude),
        key=lambda m: m.condition_id,
    )
    rng = random.Random(spec.seed)  # noqa: S311 (tirage statistique reproductible, pas de sécurité)
    return rng.sample(pool, min(spec.size, len(pool)))


def fetch_candidates(gamma: GammaApi, spec: SampleSpec) -> list[Market]:
    markets: list[Market] = []
    for event in gamma.iter_closed_events(
        tag_slug=spec.tag_slug, end_date_min=spec.end_date_min, end_date_max=spec.end_date_max
    ):
        markets.extend(Market.from_gamma(m, event=event) for m in event.get("markets") or [])
    return markets
