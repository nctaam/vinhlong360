"""Đợt 4 — migration-chain apply thật (B3). test_migration_chain cũ chỉ grep SQL file;
đây verify chain ĐÃ áp đúng lên PG (CI apply_migrations --init-baseline) qua
information_schema: core tables + trigger 070 (fire ON UPDATE) + schema_version tồn tại.
"""
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from urllib.parse import parse_qs, urlparse


_EXPLICIT_PG_TEST_ENV = {
    "VL360_TEST_DATABASE_URL": os.environ["VL360_TEST_DATABASE_URL"]
} if "VL360_TEST_DATABASE_URL" in os.environ else {}

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402
import database as database_module  # noqa: E402


def _pg_test_database_url(environ: Mapping[str, str]) -> str | None:
    url = environ.get("VL360_TEST_DATABASE_URL", "").strip()
    if not url:
        return None
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        parsed.port
    except ValueError:
        return None
    if parsed.scheme not in {"postgres", "postgresql"}:
        return None
    if hostname not in {"localhost", "127.0.0.1", "::1"}:
        return None
    if {"host", "hostaddr"} & parse_qs(parsed.query, keep_blank_values=True).keys():
        return None
    return url


def _pg_test_database(test_url: str | None):
    if test_url is not None:
        import psycopg2
        import psycopg2.extras

        database_module.psycopg2 = psycopg2
        database_module.psycopg2.extras = psycopg2.extras
    adapter = database_module.Database()
    adapter._use_pg = test_url is not None
    adapter._dsn = test_url
    return adapter


TEST_DATABASE_URL = _pg_test_database_url(_EXPLICIT_PG_TEST_ENV)
db = _pg_test_database(TEST_DATABASE_URL)
pg_only = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="set VL360_TEST_DATABASE_URL to a disposable loopback PostgreSQL database",
)

_CORE_TABLES = (
    "entities", "relationships", "itineraries", "users", "posts", "comments",
    "entity_ratings", "user_2fa", "user_2fa_recovery_codes", "pending_2fa",
    "trusted_devices", "shared_rate_limits", "request_idempotency_keys",
    "admin_audit_events", "schema_version",
)


def test_pg_integration_gate_ignores_generic_database_url():
    assert _pg_test_database_url({
        "DATABASE_URL": "postgresql://localhost/generic",
    }) is None


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://db.example.invalid/test_db",
        "postgresql://localhost.example/test_db",
        "postgresql://localhost/test_db?host=db.example.invalid",
        "postgresql://localhost/test_db?hostaddr=203.0.113.1",
        "sqlite://localhost/test_db",
    ],
)
def test_pg_integration_gate_rejects_non_loopback_or_non_postgresql_url(url):
    assert _pg_test_database_url({"VL360_TEST_DATABASE_URL": url}) is None


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://localhost/test_db",
        "postgresql://127.0.0.1/test_db",
        "postgresql://[::1]/test_db",
    ],
)
def test_pg_integration_gate_accepts_only_loopback_postgresql_urls(url):
    assert _pg_test_database_url({"VL360_TEST_DATABASE_URL": url}) == url


def test_pg_test_database_never_inherits_generic_database_config(monkeypatch):
    monkeypatch.setattr(database_module, "USE_PG", True)
    monkeypatch.setattr(
        database_module,
        "DATABASE_URL",
        "postgresql://db.example.invalid/generic",
    )

    adapter = _pg_test_database(None)

    assert adapter._use_pg is False
    assert adapter._dsn is None


def test_pg_test_database_uses_only_the_validated_test_url():
    url = "postgresql://localhost/test_db"

    adapter = _pg_test_database(url)

    assert adapter._use_pg is True
    assert adapter._dsn == url


@pg_only
def test_migration_chain_built_core_tables():
    with db._conn() as conn:
        rows = db._fetchall(conn, "SELECT table_name FROM information_schema.tables "
                                  "WHERE table_schema = 'public'", ())
        tables = {db._row_to_dict(r)["table_name"] for r in rows}
    missing = [t for t in _CORE_TABLES if t not in tables]
    assert not missing, f"Migration chain chưa tạo bảng: {missing}"


@pg_only
def test_migration_070_comment_trigger_fires_on_update():
    # Migration 070 đổi trigger comment_count fire ON INSERT/UPDATE/DELETE (soft-delete recount).
    with db._conn() as conn:
        rows = db._fetchall(conn, "SELECT event_manipulation FROM information_schema.triggers "
                                  "WHERE trigger_name = 'trg_comment_count'", ())
        events = {db._row_to_dict(r)["event_manipulation"] for r in rows}
    assert {"INSERT", "UPDATE", "DELETE"} <= events, f"trg_comment_count thiếu event: {events}"


@pg_only
def test_migration_071_rating_triggers_have_expected_events():
    with db._conn() as conn:
        rows = db._fetchall(
            conn,
            "SELECT trigger_name, event_manipulation FROM information_schema.triggers "
            "WHERE event_object_schema = 'public' "
            "AND trigger_name IN ('trg_entity_ratings', 'trg_entity_ratings_del')",
            (),
        )
    events = {}
    for row in rows:
        item = db._row_to_dict(row)
        events.setdefault(item["trigger_name"], set()).add(item["event_manipulation"])
    assert events == {
        "trg_entity_ratings": {"INSERT", "UPDATE"},
        "trg_entity_ratings_del": {"DELETE"},
    }


@pg_only
def test_schema_version_tracks_latest_migration():
    with db._conn() as conn:
        row = db._fetchone(conn, "SELECT version FROM schema_version WHERE component = 'agent'", ())
    assert row is not None
    assert int(db._row_to_dict(row)["version"]) >= 71  # đã áp tới 071
