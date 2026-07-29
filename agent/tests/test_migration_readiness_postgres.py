"""Apply the real chain to a fresh disposable PostgreSQL schema and verify readiness."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

import psycopg2
import psycopg2.extras
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import database as database_module  # noqa: E402
from scripts.apply_migrations import run as apply_migrations  # noqa: E402


def _test_database_url() -> str | None:
    url = os.environ.get("MIGRATION_APPLY_TEST_DATABASE_URL")
    if not url:
        return None
    parsed = urlparse(url)
    database_name = unquote(parsed.path.lstrip("/"))
    if (
        parsed.scheme not in {"postgres", "postgresql"}
        or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
        or "test" not in database_name.lower()
    ):
        raise pytest.UsageError(
            "MIGRATION_APPLY_TEST_DATABASE_URL must target a loopback "
            "PostgreSQL database whose name contains 'test'"
        )
    return url


TEST_DATABASE_URL = _test_database_url()
pytestmark = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="set MIGRATION_APPLY_TEST_DATABASE_URL to a disposable PostgreSQL DB",
)


@pytest.fixture
def fresh_migrated_database():
    assert TEST_DATABASE_URL is not None
    with psycopg2.connect(TEST_DATABASE_URL) as conn:
        conn.autocommit = True
        with conn.cursor() as cursor:
            cursor.execute("DROP SCHEMA public CASCADE")
            cursor.execute("CREATE SCHEMA public")

    applied = apply_migrations(TEST_DATABASE_URL, init_baseline=True)
    adapter = database_module.Database()
    adapter._use_pg = True
    adapter._dsn = TEST_DATABASE_URL
    database_module.psycopg2 = psycopg2
    database_module.psycopg2.extras = psycopg2.extras
    return adapter, applied


def test_fresh_migration_chain_reaches_release_readiness(fresh_migrated_database):
    adapter, applied = fresh_migrated_database

    assert [migration.version for migration in applied][-2:] == [71, 72]
    with adapter._conn(commit_on_success=False) as conn:
        adapter._verify_pg_schema(conn)
    status = adapter.pg_schema_status()
    assert status == {
        "backend": "postgresql",
        "ok": True,
        "schema_version": 72,
        "required_schema_version": 72,
    }
