"""Refuse modified applied migrations; serialize migration runners with an advisory lock."""

import hashlib
from pathlib import Path

from gtmdq.config import PROJECT_ROOT
from gtmdq.database.connection import connect


def migrate(directory: Path | None = None) -> list[str]:
    directory = directory or PROJECT_ROOT / "sql"
    paths = sorted(directory.glob("[0-9][0-9][0-9]_*.sql"))
    if not paths:
        raise ValueError(f"No migration files found in {directory}")
    applied = []
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(%s)", (714202642,))
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS public.gtmdq_schema_migration (
                filename TEXT PRIMARY KEY,
                sha256 TEXT NOT NULL,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)
        for path in paths:
            sql = path.read_text(encoding="utf-8")
            checksum = hashlib.sha256(sql.encode()).hexdigest()
            cursor.execute(
                "SELECT sha256 FROM public.gtmdq_schema_migration WHERE filename = %s", (path.name,)
            )
            existing = cursor.fetchone()
            if existing:
                if existing[0] != checksum:
                    raise ValueError(f"Applied migration changed: {path.name}; add a new migration")
                continue
            cursor.execute(sql)
            cursor.execute(
                "INSERT INTO public.gtmdq_schema_migration (filename, sha256) VALUES (%s, %s)",
                (path.name, checksum),
            )
            applied.append(path.name)
    return applied
