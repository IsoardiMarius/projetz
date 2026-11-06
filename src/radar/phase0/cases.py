"""Cas d'étude de la Phase 0 : marchés où une information privilégiée a été alléguée ou établie.

Seuls les marchés sont listés ici, jamais les wallets : les comptes concernés sont retrouvés
par l'analyse. Le moment où l'information devient publique est estimé automatiquement à
partir des prix (voir `radar.analysis.prices`), pour ne pas dépendre d'horaires non vérifiés.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Case:
    key: str
    title: str
    event_slug: str
    question_pattern: str | None
    context: str


CASES: tuple[Case, ...] = (
    Case(
        key="nobel_2025",
        title="Prix Nobel de la paix 2025",
        event_slug="nobel-peace-prize-winner-2025",
        question_pattern=r"Machado",
        context="La cote de la lauréate est passée d'environ 4 % à plus de 70 % dans la nuit "
        "précédant l'annonce. Une enquête pour fuite a été ouverte.",
    ),
    Case(
        key="google_2025",
        title="Personne la plus recherchée sur Google en 2025",
        event_slug="1-searched-person-on-google-this-year",
        question_pattern=r"d4vd",
        context="Un compte qui a gagné 22 paris sur 23 sur le classement Google a été inculpé "
        "par le DOJ et la CFTC (mai 2026).",
    ),
    Case(
        key="maduro_2026",
        title="Capture de Nicolás Maduro (3 janvier 2026)",
        event_slug="maduro-out-in-2025",
        question_pattern=r"by (January 31|March 31), 2026",
        context="Un militaire américain a été inculpé pour avoir parié avec des informations "
        "classifiées sur l'opération.",
    ),
    Case(
        key="iran_strikes_2026",
        title="Frappes américaines sur l'Iran (28 février 2026)",
        event_slug="us-strikes-iran-by",
        question_pattern=r"by (February 28|March 1|March 15), 2026",
        context="Des wallets créés et financés moins de 24 h avant ont acheté à 10-20 ¢. "
        "Aucune poursuite connue.",
    ),
    Case(
        key="khamenei_2026",
        title="Départ de Khamenei (mars 2026)",
        event_slug="khamenei-out-as-supreme-leader-of-iran-by-march-31",
        question_pattern=None,
        context="Marché lié aux frappes de fin février 2026 ; gains importants rapportés par "
        "des comptes très actifs sur ces événements.",
    ),
    Case(
        key="ceasefire_2026",
        title="Cessez-le-feu États-Unis–Iran (avril 2026)",
        event_slug="us-x-iran-ceasefire-by",
        question_pattern=r"April 7",
        context="Environ 600 k$ de gains rapportés sur 3 comptes avant l'annonce.",
    ),
)
