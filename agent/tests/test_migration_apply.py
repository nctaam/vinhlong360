"""Đợt 4 — migration-chain apply thật (B3). test_migration_chain cũ chỉ grep SQL file;
đây verify chain ĐÃ áp đúng lên PG (CI apply_migrations --init-baseline) qua
information_schema: core tables + trigger 070 (fire ON UPDATE) + schema_version tồn tại.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402
from database import db  # noqa: E402

pg_only = pytest.mark.skipif(not db._use_pg, reason="Migration chain apply là PG-only.")

_CORE_TABLES = (
    "entities", "relationships", "itineraries", "users", "posts", "comments",
    "entity_ratings", "user_2fa", "user_2fa_recovery_codes", "pending_2fa",
    "trusted_devices", "shared_rate_limits", "request_idempotency_keys",
    "admin_audit_events", "schema_version",
    "feedback_receipts", "feedback_daily_rollups",
)


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
def test_schema_version_tracks_latest_migration():
    with db._conn() as conn:
        row = db._fetchone(conn, "SELECT version FROM schema_version WHERE component = 'agent'", ())
    assert row is not None
    assert int(db._row_to_dict(row)["version"]) >= 71  # đã áp tới 071


@pg_only
def test_feedback_tables_are_owned_by_runtime_role():
    with db._conn() as conn:
        rows = db._fetchall(
            conn,
            """
            SELECT tablename, tableowner
            FROM pg_tables
            WHERE schemaname = 'public'
              AND tablename IN ('feedback_receipts', 'feedback_daily_rollups')
            """,
            (),
        )

    owners = {
        db._row_to_dict(row)["tablename"]: db._row_to_dict(row)["tableowner"]
        for row in rows
    }
    assert owners == {
        "feedback_receipts": "vl360",
        "feedback_daily_rollups": "vl360",
    }


@pg_only
def test_feedback_receipt_schema_forbids_raw_content_columns():
    with db._conn() as conn:
        rows = db._fetchall(
            conn,
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'feedback_receipts'
            """,
            (),
        )
    columns = {db._row_to_dict(row)["column_name"] for row in rows}
    assert not {"query", "reply", "entity_id", "session_id"} & columns
