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


def _validate_test_database_url(url: str) -> str:
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
    monkeypatch.setenv("MIGRATION_APPLY_TEST_DATABASE_URL", database_url)

    assert _test_database_url() == database_url


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

    assert [migration.version for migration in applied][-3:] == [71, 72, 73]
    adapter._dsn = _validate_test_database_url(adapter._dsn)
    with adapter._conn(commit_on_success=False) as conn:
        adapter._verify_pg_schema(conn)
    status = adapter.pg_schema_status()
    assert status == {
        "backend": "postgresql",
        "ok": True,
        "schema_version": 73,
        "required_schema_version": 73,
    }
