"""Frais « taker » de Polymarket (barème en vigueur au 6/11/2026).

Frais par part = taux × p × (1 − p), où p est le prix. Les makers ne paient pas.
Le barème a évolué en 2026 : l'appliquer à des trades plus anciens donne une estimation prudente.
"""

from __future__ import annotations

from collections.abc import Iterable

# Ordre de priorité : la première étiquette reconnue fixe le taux.
_RATES: tuple[tuple[str, float], ...] = (
    ("geopolitics", 0.0),
    ("crypto", 0.07),
    ("sports", 0.05),
    ("economy", 0.05),
    ("culture", 0.05),
    ("pop-culture", 0.05),
    ("politics", 0.04),
    ("finance", 0.04),
    ("tech", 0.04),
    ("mentions", 0.04),
)
DEFAULT_RATE = 0.05


def taker_rate(tags: Iterable[str]) -> float:
    tag_set = set(tags)
    for tag, rate in _RATES:
        if tag in tag_set:
            return rate
    return DEFAULT_RATE


def taker_fee_per_share(price: float, rate: float) -> float:
    if not 0.0 <= price <= 1.0:
        raise ValueError(f"prix hors de [0, 1] : {price}")
    return rate * price * (1.0 - price)
