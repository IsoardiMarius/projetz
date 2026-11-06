"""Écriture et lecture des données collectées."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime

import psycopg
from psycopg.types.json import Jsonb

from radar.polymarket.models import Activity, Market, Trade, TradeRow

Conn = psycopg.Connection[tuple[object, ...]]


def upsert_markets(conn: Conn, markets: Iterable[Market]) -> int:
    count = 0
    with conn.transaction(), conn.cursor() as cur:
        for m in markets:
            cur.execute(
                """
                INSERT INTO markets (condition_id, market_id, question, slug, group_item_title,
                    event_id, event_slug, tags, fee_type, neg_risk, start_date, end_date,
                    closed_time, closed, volume, resolution_status, outcomes, winning_token_id,
                    fetched_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    now())
                ON CONFLICT (condition_id) DO UPDATE SET
                    market_id = EXCLUDED.market_id, question = EXCLUDED.question,
                    slug = EXCLUDED.slug, group_item_title = EXCLUDED.group_item_title,
                    event_id = COALESCE(EXCLUDED.event_id, markets.event_id),
                    event_slug = COALESCE(EXCLUDED.event_slug, markets.event_slug),
                    tags = CASE WHEN cardinality(EXCLUDED.tags) > 0
                                THEN EXCLUDED.tags ELSE markets.tags END,
                    fee_type = EXCLUDED.fee_type, neg_risk = EXCLUDED.neg_risk,
                    start_date = EXCLUDED.start_date, end_date = EXCLUDED.end_date,
                    closed_time = EXCLUDED.closed_time, closed = EXCLUDED.closed,
                    volume = EXCLUDED.volume, resolution_status = EXCLUDED.resolution_status,
                    outcomes = EXCLUDED.outcomes, winning_token_id = EXCLUDED.winning_token_id,
                    fetched_at = now()
                """,
                (
                    m.condition_id,
                    m.market_id,
                    m.question,
                    m.slug,
                    m.group_item_title,
                    m.event_id,
                    m.event_slug,
                    list(m.tags),
                    m.fee_type,
                    m.neg_risk,
                    m.start_date,
                    m.end_date,
                    m.closed_time,
                    m.closed,
                    m.volume,
                    m.resolution_status,
                    Jsonb([o.model_dump() for o in m.outcomes]),
                    m.winning_token_id,
                ),
            )
            count += 1
    return count


@dataclass(frozen=True)
class MarketCollection:
    condition_id: str
    n_rows: int
    n_taker_rows: int
    n_unmatched_taker_rows: int


def flag_takers(all_rows: Sequence[Trade], taker_rows: Sequence[Trade]) -> tuple[list[bool], int]:
    """Marque les lignes du flux complet qui sont des lignes taker.

    Le rapprochement se fait par multiensemble sur (tx, wallet, token, côté, taille, prix), pour
    gérer les doublons exacts. Renvoie aussi le nombre de lignes taker introuvables, qui doit
    être nul ou presque (contrôle de cohérence entre les deux flux).
    """
    remaining = Counter(t.match_key() for t in taker_rows)
    flags: list[bool] = []
    for row in all_rows:
        key = row.match_key()
        if remaining[key] > 0:
            remaining[key] -= 1
            flags.append(True)
        else:
            flags.append(False)
    return flags, sum(remaining.values())


def stream_market_trades(
    conn: Conn,
    condition_id: str,
    all_rows: Iterable[TradeRow],
    taker_keys: Counter[tuple[str, str, str, str, float, float]],
) -> MarketCollection:
    """Remplace les trades d'un marché en écrivant les lignes au fil de l'eau.

    `all_rows` arrive dans l'ordre de l'API (du plus récent au plus ancien) et n'est jamais
    gardé en mémoire : les lignes passent par une table de transit, puis sont numérotées
    de la plus ancienne à la plus récente (à horodatage égal, l'ordre de l'API est conservé).
    `taker_keys` (multiensemble des lignes taker) est consommé.
    """
    n_taker = sum(taker_keys.values())
    n_rows = 0
    with conn.transaction(), conn.cursor() as cur:
        cur.execute(
            "CREATE TEMP TABLE staging_trades (api_order INTEGER, ts TIMESTAMPTZ, wallet TEXT,"
            " token_id TEXT, outcome_index SMALLINT, side TEXT, size DOUBLE PRECISION,"
            " price DOUBLE PRECISION, is_taker BOOLEAN, tx_hash TEXT) ON COMMIT DROP"
        )
        with cur.copy(
            "COPY staging_trades (api_order, ts, wallet, token_id, outcome_index, side, size,"
            " price, is_taker, tx_hash) FROM STDIN"
        ) as copy:
            for row in all_rows:
                key = row.match_key()
                is_taker = taker_keys[key] > 0
                if is_taker:
                    taker_keys[key] -= 1
                copy.write_row(
                    (
                        n_rows,
                        row.ts,
                        row.wallet,
                        row.token_id,
                        row.outcome_index,
                        row.side,
                        row.size,
                        row.price,
                        is_taker,
                        row.tx_hash,
                    )
                )
                n_rows += 1
        cur.execute("DELETE FROM trades WHERE condition_id = %s", (condition_id,))
        cur.execute(
            """
            INSERT INTO trades (condition_id, seq, ts, wallet, token_id, outcome_index, side,
                size, price, is_taker, tx_hash)
            SELECT %s, (row_number() OVER (ORDER BY ts, api_order DESC) - 1)::int, ts, wallet,
                token_id, outcome_index, side, size, price, is_taker, tx_hash
            FROM staging_trades
            """,
            (condition_id,),
        )
        unmatched = sum(v for v in taker_keys.values() if v > 0)
        cur.execute(
            """
            INSERT INTO market_collections
                (condition_id, collected_at, n_rows, n_taker_rows, n_unmatched_taker_rows)
            VALUES (%s, now(), %s, %s, %s)
            ON CONFLICT (condition_id) DO UPDATE SET collected_at = now(),
                n_rows = EXCLUDED.n_rows, n_taker_rows = EXCLUDED.n_taker_rows,
                n_unmatched_taker_rows = EXCLUDED.n_unmatched_taker_rows
            """,
            (condition_id, n_rows, n_taker, unmatched),
        )
    return MarketCollection(condition_id, n_rows, n_taker, unmatched)


def replace_market_trades(
    conn: Conn, condition_id: str, all_rows: Sequence[Trade], taker_rows: Sequence[Trade]
) -> MarketCollection:
    """Variante en mémoire de `stream_market_trades` (petits volumes, tests)."""
    keys = Counter(TradeRow.from_trade(t).match_key() for t in taker_rows)
    return stream_market_trades(
        conn, condition_id, (TradeRow.from_trade(t) for t in all_rows), keys
    )


def collected_conditions(conn: Conn) -> set[str]:
    return {str(r[0]) for r in conn.execute("SELECT condition_id FROM market_collections")}


def save_wallet_profile(
    conn: Conn, wallet: str, first_activity: datetime | None, deposits: Iterable[Activity]
) -> None:
    with conn.transaction(), conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO wallet_profiles (wallet, first_activity_ts, fetched_at)
            VALUES (%s, %s, now())
            ON CONFLICT (wallet) DO UPDATE SET first_activity_ts = EXCLUDED.first_activity_ts,
                fetched_at = now()
            """,
            (wallet, first_activity),
        )
        cur.execute("DELETE FROM wallet_deposits WHERE wallet = %s", (wallet,))
        for d in deposits:
            cur.execute(
                "INSERT INTO wallet_deposits (wallet, ts, usdc, tx_hash) VALUES (%s, %s, %s, %s)"
                " ON CONFLICT DO NOTHING",
                (wallet, d.timestamp, d.usdc_size, d.transaction_hash),
            )


def profiled_wallets(conn: Conn) -> set[str]:
    return {str(r[0]) for r in conn.execute("SELECT wallet FROM wallet_profiles")}


def untraced_deposits(
    conn: Conn, wallets: Iterable[str], *, first_n: int = 3
) -> list[tuple[str, str, datetime]]:
    """Premiers dépôts (wallet, tx, date) de ces wallets dont l'origine n'est pas encore connue.

    Les `first_n` premiers dépôts suffisent pour identifier qui a financé le compte.
    """
    rows = conn.execute(
        """
        WITH ranked AS (
            SELECT wallet, tx_hash, ts,
                   row_number() OVER (PARTITION BY wallet ORDER BY ts) AS rank
            FROM wallet_deposits WHERE wallet = ANY(%s)
        )
        SELECT r.wallet, r.tx_hash, r.ts FROM ranked r
        LEFT JOIN wallet_funders f ON f.wallet = r.wallet AND f.tx_hash = r.tx_hash
        WHERE f.wallet IS NULL AND r.rank <= %s
        ORDER BY r.wallet, r.ts
        """,
        (list(wallets), first_n),
    ).fetchall()
    return [(str(r[0]), str(r[1]), r[2]) for r in rows if isinstance(r[2], datetime)]


def save_funder(conn: Conn, wallet: str, tx_hash: str, funder: str | None, ts: datetime) -> None:
    conn.execute(
        "INSERT INTO wallet_funders (wallet, tx_hash, funder, ts) VALUES (%s, %s, %s, %s)"
        " ON CONFLICT (wallet, tx_hash) DO UPDATE SET funder = EXCLUDED.funder",
        (wallet, tx_hash, funder, ts),
    )
