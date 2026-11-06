"""Connexion PostgreSQL et migrations versionnées (fichiers SQL numérotés)."""

from __future__ import annotations

import os
from importlib import resources

import psycopg

ENV_VAR = "RADAR_DATABASE_URL"


def database_url() -> str:
    url = os.environ.get(ENV_VAR)
    if not url:
        raise RuntimeError(
            f"La variable d'environnement {ENV_VAR} n'est pas définie (URL PostgreSQL)."
        )
    return url


def connect(url: str | None = None) -> psycopg.Connection[tuple[object, ...]]:
    """Connexion en autocommit : chaque bloc `conn.transaction()` est une vraie transaction.

    Sans autocommit, la première lecture ouvrirait une transaction implicite et tous les blocs
    suivants deviendraient de simples points de sauvegarde, validés seulement à la fermeture.
    """
    return psycopg.connect(url or database_url(), autocommit=True)


def _migration_files() -> list[tuple[str, str]]:
    folder = resources.files("radar.storage") / "migrations"
    files = sorted((p for p in folder.iterdir() if p.name.endswith(".sql")), key=lambda p: p.name)
    return [(p.name.removesuffix(".sql"), p.read_text(encoding="utf-8")) for p in files]


def migrate(conn: psycopg.Connection[tuple[object, ...]]) -> list[str]:
    """Applique les migrations manquantes, chacune dans sa transaction.

    Renvoie la liste des migrations appliquées.
    """
    with conn.transaction():
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            " version TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
        )
    done = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}
    applied: list[str] = []
    for version, sql in _migration_files():
        if version in done:
            continue
        with conn.transaction():
            conn.execute(sql.encode())
            conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (version,))
        applied.append(version)
    return applied
