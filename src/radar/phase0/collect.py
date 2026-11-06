"""Collecte des données de la Phase 0 (cas connus et échantillon large)."""

from __future__ import annotations

import logging
import re

from radar.collect import Collector
from radar.phase0.cases import CASES
from radar.phase0.sample import SampleSpec, draw_sample, fetch_candidates
from radar.polymarket.models import Market
from radar.storage import repository
from radar.storage.repository import Conn

log = logging.getLogger(__name__)


def _tag(conn: Conn, markets: list[Market], grp: str, case_key: str | None) -> None:
    with conn.transaction():
        for m in markets:
            conn.execute(
                "INSERT INTO phase0_markets (condition_id, grp, case_key) VALUES (%s, %s, %s)"
                " ON CONFLICT (condition_id) DO UPDATE SET grp = EXCLUDED.grp,"
                " case_key = EXCLUDED.case_key",
                (m.condition_id, grp, case_key),
            )


def collect_cases(collector: Collector) -> None:
    for case in CASES:
        markets = collector.gamma.event_markets(case.event_slug)
        if case.question_pattern:
            regex = re.compile(case.question_pattern, re.IGNORECASE)
            markets = [m for m in markets if regex.search(m.question)]
        if not markets:
            raise RuntimeError(f"Aucun marché trouvé pour le cas {case.key}")
        log.info("Cas %s : %d marché(s)", case.key, len(markets))
        repository.upsert_markets(collector.conn, markets)
        _tag(collector.conn, markets, "case", case.key)
        collector.collect_markets(markets)


def collect_sample(collector: Collector, spec: SampleSpec) -> None:
    candidates = fetch_candidates(collector.gamma, spec)
    case_ids = {
        str(r[0])
        for r in collector.conn.execute(
            "SELECT condition_id FROM phase0_markets WHERE grp = 'case'"
        )
    }
    sample = draw_sample(candidates, spec, exclude=case_ids)
    log.info("Échantillon : %d marchés tirés parmi %d candidats", len(sample), len(candidates))
    repository.upsert_markets(collector.conn, sample)
    _tag(collector.conn, sample, "sample", None)
    collector.collect_markets(sample)
