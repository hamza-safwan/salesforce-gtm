import os

import psycopg
import pytest

from gtmdq.database.connection import connect
from gtmdq.database.migrations import migrate

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("GTMDQ_RUN_DB_TESTS") != "1",
        reason="Set GTMDQ_RUN_DB_TESTS=1 to use the configured local database",
    ),
]


def test_migration_rerun_is_a_noop_and_drift_fails(tmp_path):
    migrate()
    assert migrate() == []
    with connect() as connection:
        count = connection.execute("SELECT count(*) FROM public.gtmdq_schema_migration").fetchone()[
            0
        ]
        assert count >= 1
        for name in (
            "raw.snapshot",
            "raw.salesforce_account",
            "dq.rule_result",
            "dq.remediation_queue",
        ):
            assert connection.execute("SELECT to_regclass(%s)", (name,)).fetchone()[0] == name
    (tmp_path / "001_schema.sql").write_text("SELECT 1;", encoding="utf-8")
    with pytest.raises(ValueError, match="Applied migration changed"):
        migrate(tmp_path)
    assert migrate() == []


def test_failed_migration_rolls_back_all_statements(tmp_path):
    (tmp_path / "999_transaction_probe.sql").write_text(
        "CREATE TABLE public.gtmdq_rollback_probe (id INTEGER); SELECT 1 / 0;", encoding="utf-8"
    )
    with pytest.raises(psycopg.errors.DivisionByZero):
        migrate(tmp_path)
    with connect() as connection:
        assert (
            connection.execute("SELECT to_regclass('public.gtmdq_rollback_probe')").fetchone()[0]
            is None
        )
        assert (
            connection.execute(
                "SELECT count(*) FROM public.gtmdq_schema_migration WHERE filename = %s",
                ("999_transaction_probe.sql",),
            ).fetchone()[0]
            == 0
        )
