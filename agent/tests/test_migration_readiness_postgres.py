"""Apply the real chain to a fresh disposable PostgreSQL schema and verify readiness."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import psycopg2
import psycopg2.extras
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import database as database_module  # noqa: E402
from scripts.apply_migrations import run as apply_migrations  # noqa: E402

LIBPQ_CONNECTION_TARGET_ENV_VARS = (
    "PGHOST",
    "PGHOSTADDR",
    "PGPORT",
    "PGDATABASE",
    "PGSERVICE",
    "PGSERVICEFILE",
)


def _validate_test_database_url(url: str) -> str:
    if any(os.environ.get(variable) for variable in LIBPQ_CONNECTION_TARGET_ENV_VARS):
        raise pytest.UsageError(
            "MIGRATION_APPLY_TEST_DATABASE_URL must not inherit libpq "
            "connection-target environment defaults"
        )
    parsed = urlparse(url)
    try:
        effective = psycopg2.extensions.parse_dsn(url)
    except psycopg2.ProgrammingError as exc:
        raise pytest.UsageError(
            "MIGRATION_APPLY_TEST_DATABASE_URL must be a valid PostgreSQL URL"
        ) from exc

    host = effective.get("host", "")
    hostaddr = effective.get("hostaddr", "")
    database_name = effective.get("dbname", "")
    loopback_hosts = {"127.0.0.1", "localhost", "::1"}
    if (
        parsed.scheme not in {"postgres", "postgresql"}
        or "service" in effective
        or "," in host
        or "," in hostaddr
        or host not in loopback_hosts
        or (hostaddr and hostaddr not in loopback_hosts)
        or "test" not in database_name.lower()
    ):
        raise pytest.UsageError(
            "MIGRATION_APPLY_TEST_DATABASE_URL must resolve to a single "
            "loopback PostgreSQL test database"
        )
    return url


def _test_database_url() -> str | None:
    url = os.environ.get("MIGRATION_APPLY_TEST_DATABASE_URL")
    return _validate_test_database_url(url) if url else None


def _connect_test_database():
    assert TEST_DATABASE_URL is not None
    return psycopg2.connect(_validate_test_database_url(TEST_DATABASE_URL))


TEST_DATABASE_URL = _test_database_url()
pg_only = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="set MIGRATION_APPLY_TEST_DATABASE_URL to a disposable PostgreSQL DB",
)


@pytest.mark.parametrize(
    "database_url",
    [
        "postgresql://user:password@localhost/my_test_db?host=prod.example.com",
        "postgresql://user:password@localhost/my_test_db?hostaddr=203.0.113.9",
        "postgresql://user:password@localhost/my_test_db?dbname=production",
        "postgresql://user:password@localhost/my_test_db?service=production",
        "postgresql://user:password@localhost/my_test_db?host=localhost%2Cprod.example.com",
    ],
    ids=["host-override", "hostaddr-override", "dbname-override", "service", "multi-host"],
)
def test_database_url_guard_rejects_libpq_effective_parameter_bypasses(
    monkeypatch, database_url
):
    monkeypatch.setenv("MIGRATION_APPLY_TEST_DATABASE_URL", database_url)

    with pytest.raises(pytest.UsageError, match="loopback PostgreSQL test database"):
        _test_database_url()


def test_database_url_guard_accepts_single_loopback_test_database(monkeypatch):
    database_url = "postgresql://user:password@127.0.0.1/migration_test"
    for variable in LIBPQ_CONNECTION_TARGET_ENV_VARS:
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv("MIGRATION_APPLY_TEST_DATABASE_URL", database_url)

    assert _test_database_url() == database_url


@pytest.mark.parametrize(
    ("variable", "value"),
    [
        ("PGHOST", "prod.example.com"),
        ("PGHOSTADDR", "203.0.113.9"),
        ("PGPORT", "6543"),
        ("PGDATABASE", "production"),
        ("PGSERVICE", "production"),
        ("PGSERVICEFILE", "unsafe-service.conf"),
    ],
)
def test_database_url_guard_rejects_libpq_environment_target_defaults(
    monkeypatch, variable, value
):
    database_url = "postgresql://user:password@127.0.0.1/migration_test"
    for environment_variable in LIBPQ_CONNECTION_TARGET_ENV_VARS:
        monkeypatch.delenv(environment_variable, raising=False)
    monkeypatch.setenv("MIGRATION_APPLY_TEST_DATABASE_URL", database_url)
    monkeypatch.setenv(variable, value)

    with pytest.raises(pytest.UsageError, match="libpq connection-target environment"):
        _test_database_url()


@pytest.fixture
def fresh_migrated_database():
    assert TEST_DATABASE_URL is not None
    with _connect_test_database() as conn:
        conn.autocommit = True
        with conn.cursor() as cursor:
            cursor.execute("DROP SCHEMA public CASCADE")
            cursor.execute("CREATE SCHEMA public")

    safe_database_url = _validate_test_database_url(TEST_DATABASE_URL)
    applied = apply_migrations(safe_database_url, init_baseline=True)
    adapter = database_module.Database()
    adapter._use_pg = True
    adapter._dsn = safe_database_url
    database_module.psycopg2 = psycopg2
    database_module.psycopg2.extras = psycopg2.extras
    return adapter, applied


@pg_only
def test_fresh_migration_chain_reaches_release_readiness(fresh_migrated_database):
    adapter, applied = fresh_migrated_database

    # Migration 081 chủ duyệt (commit 834a8d25); 082 unicode-digit CHECK (§48.4,
    # Migration 083 adds the shared entity snapshot generation table.
    assert [migration.version for migration in applied][-3:] == [81, 82, 83]
    adapter._dsn = _validate_test_database_url(adapter._dsn)
    with adapter._conn(commit_on_success=False) as conn:
        adapter._verify_pg_schema(conn)
    status = adapter.pg_schema_status()
    assert status["backend"] == "postgresql"
    assert status["ok"] is True
    assert status["schema_version"] == 83
    assert status["required_schema_version"] == 83
    assert status["missing_tables"] == []
    assert status["missing_columns"] == []
    assert status["missing_triggers"] == []
    assert status["issues"] == []


@pg_only
def test_case_readiness_reports_clean_for_an_untampered_schema(fresh_migrated_database):
    """Fail-closed is only half the contract: a correct schema must read ready.

    Every other drift probe asserts that an expected issue is present, which
    stays true even when the whole catalog is reported as drifted, so nothing
    covered the healthy direction.
    """
    adapter, _applied = fresh_migrated_database

    with adapter._conn(commit_on_success=False) as conn:
        snapshot = database_module._pg_schema_snapshot(conn)

    assert snapshot["case_missing_tables"] == []
    assert snapshot["case_missing_columns"] == []
    assert snapshot["case_issues"] == []

    status = database_module.case_kernel_schema_status(
        {**snapshot, "backend": "postgresql", "ok": not snapshot["issues"]},
        enabled=True,
    )
    assert status == {"ok": True, "state": "ready", "code": "case_kernel_ready"}


@pg_only
def test_case_readiness_fails_closed_for_catalog_definition_drift(
    fresh_migrated_database,
):
    adapter, _applied = fresh_migrated_database
    probes = (
        (
            (
                "ALTER TABLE case_receipts DROP CONSTRAINT "
                "case_receipts_receipt_revision_positive",
                "ALTER TABLE case_receipts ADD CONSTRAINT "
                "case_receipts_revision_positive_renamed "
                "CHECK (receipt_revision >= 1)",
            ),
            "constraint definition drift: case_receipts_receipt_revision_positive",
        ),
        (
            (
                "ALTER TABLE case_receipts DROP CONSTRAINT "
                "case_receipts_receipt_revision_positive",
                "ALTER TABLE case_receipts ADD CONSTRAINT "
                "case_receipts_receipt_revision_positive "
                "CHECK (receipt_revision >= 0)",
            ),
            "constraint definition drift: case_receipts_receipt_revision_positive",
        ),
        (
            (
                "ALTER TABLE case_receipts DROP CONSTRAINT "
                "case_receipts_case_revision_unique",
                "CREATE INDEX case_receipts_case_revision_unique "
                "ON case_receipts(receipt_revision, case_id)",
            ),
            "index definition drift: case_receipts_case_revision_unique",
        ),
        (
            (
                "ALTER TABLE case_access_sessions DROP CONSTRAINT "
                "case_access_sessions_case_receipt_fkey",
                "ALTER TABLE case_access_sessions ADD CONSTRAINT "
                "case_access_sessions_case_receipt_fkey "
                "FOREIGN KEY (case_id, receipt_id) "
                "REFERENCES case_receipts(case_id, receipt_id) ON DELETE RESTRICT",
            ),
            "foreign key definition drift: case_access_sessions_case_receipt_fkey",
        ),
        (
            (
                "DROP TRIGGER case_receipts_case_immutable ON case_receipts",
                "CREATE TRIGGER case_receipts_case_immutable "
                "AFTER UPDATE ON case_receipts FOR EACH ROW "
                "EXECUTE FUNCTION enforce_case_access_same_case()",
            ),
            "trigger definition drift: case_receipts_case_immutable",
        ),
        (
            # A same-named target in another namespace keeps every catalog field
            # the readiness query used to compare, while public.case_receipts is
            # no longer the referenced table.
            (
                "CREATE SCHEMA shadow",
                "CREATE TABLE shadow.case_receipts ("
                "case_id UUID NOT NULL, receipt_id UUID NOT NULL, "
                "PRIMARY KEY (case_id, receipt_id))",
                # PostgreSQL validates the new foreign key against existing
                # rows, so leave the probe self-contained rather than relying
                # on the table happening to be empty; the savepoint rolls the
                # delete back with everything else.
                "DELETE FROM case_access_sessions",
                "ALTER TABLE case_access_sessions DROP CONSTRAINT "
                "case_access_sessions_case_receipt_fkey",
                "ALTER TABLE case_access_sessions ADD CONSTRAINT "
                "case_access_sessions_case_receipt_fkey "
                "FOREIGN KEY (case_id, receipt_id) "
                "REFERENCES shadow.case_receipts(case_id, receipt_id) ON DELETE CASCADE",
            ),
            "foreign key definition drift: case_access_sessions_case_receipt_fkey",
        ),
        (
            # A restrictive WHEN predicate leaves table, function, event bitmask,
            # enabled state and UPDATE OF columns intact but never fires.
            (
                "DROP TRIGGER case_receipts_case_immutable ON case_receipts",
                "CREATE TRIGGER case_receipts_case_immutable "
                "BEFORE UPDATE OF case_id ON case_receipts FOR EACH ROW "
                "WHEN (false) EXECUTE FUNCTION reject_case_receipt_case_move()",
            ),
            "trigger definition drift: case_receipts_case_immutable",
        ),
        (
            # Replacing the body keeps the expected function name and every
            # trigger row field, yet the case-move guard becomes a no-op.
            (
                "CREATE OR REPLACE FUNCTION reject_case_receipt_case_move() "
                "RETURNS trigger LANGUAGE plpgsql AS $body$ BEGIN RETURN NEW; END; $body$",
            ),
            "trigger definition drift: case_receipts_case_immutable",
        ),
        (
            (
                "CREATE OR REPLACE FUNCTION enforce_case_access_same_case() "
                "RETURNS trigger LANGUAGE plpgsql AS $body$ BEGIN RETURN NEW; END; $body$",
            ),
            "trigger definition drift: case_access_sessions_same_case",
        ),
    )
    with adapter._conn(commit_on_success=False) as conn:
        for position, (statements, expected_issue) in enumerate(probes):
            savepoint = f"catalog_drift_{position}"
            adapter._execute(conn, f"SAVEPOINT {savepoint}", ())
            try:
                for statement in statements:
                    adapter._execute(conn, statement, ())
                snapshot = database_module._pg_schema_snapshot(conn)
                assert expected_issue in snapshot["case_issues"]
            finally:
                adapter._execute(conn, f"ROLLBACK TO SAVEPOINT {savepoint}", ())
