"""Real PostgreSQL contract checks for migration 080.

The test target is intentionally opt-in and loopback-only.  No ambient or
production DSN is accepted; absent target means explicit pytest skips.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agent"))
sys.path.insert(0, str(ROOT))

import database  # noqa: E402
import server  # noqa: E402, F401 - pairs readiness wiring with agent/server.py


def _validated_url() -> str | None:
    raw = os.environ.get("VL360_TEST_DATABASE_URL", "").strip()
    if not raw:
        return None
    parsed = urlparse(raw)
    if parsed.scheme not in {"postgres", "postgresql"} or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        return None
    if {"host", "hostaddr"} & parse_qs(parsed.query, keep_blank_values=True).keys():
        return None
    return raw


TEST_DATABASE_URL = _validated_url()
pg_only = pytest.mark.skipif(TEST_DATABASE_URL is None, reason="set VL360_TEST_DATABASE_URL to a disposable loopback PostgreSQL database")


@pytest.fixture(scope="module")
def pg_db():
    if TEST_DATABASE_URL is None:
        pytest.skip("set VL360_TEST_DATABASE_URL to a disposable loopback PostgreSQL database")
    import psycopg2
    import psycopg2.extras
    database.psycopg2 = psycopg2
    database.psycopg2.extras = psycopg2.extras
    adapter = database.Database()
    adapter._use_pg = True
    adapter._dsn = TEST_DATABASE_URL
    return adapter


CASE_TABLES = (
    "cases", "case_interactions", "case_party_authorities", "case_work_items",
    "case_decisions", "case_promise_clocks", "case_receipts", "case_access_sessions",
    "case_admin_access_sessions", "case_transitions", "case_audit_events", "case_outbox",
    "case_idempotency", "case_contact_challenges", "correction_items", "correction_evidence",
    "correction_change_sets", "legacy_intake_records", "case_capacity_events",
)


@pg_only
def test_migration_080_tables_columns_constraints_and_owners(pg_db):
    with pg_db._conn() as conn:
        rows = pg_db._fetchall(conn, "SELECT table_name FROM information_schema.tables WHERE table_schema='public'", ())
        tables = {pg_db._row_to_dict(r)["table_name"] for r in rows}
        assert set(CASE_TABLES) <= tables

        columns = {}
        for table in CASE_TABLES:
            rows = pg_db._fetchall(conn, "SELECT column_name, data_type FROM information_schema.columns WHERE table_schema='public' AND table_name=%s", (table,))
            columns[table] = {pg_db._row_to_dict(r)["column_name"]: pg_db._row_to_dict(r)["data_type"] for r in rows}
        assert columns["cases"]["case_id"] == "uuid"
        assert columns["cases"]["current_revision"] == "integer"
        assert columns["case_receipts"]["capability_digest"] in {"text", "bytea"}
        assert "capability" not in columns["case_receipts"]
        assert not ({"contact", "phone", "email"} & set(columns["case_contact_challenges"]))
        assert "content_enc" in columns["correction_evidence"]
        assert "payload_enc" in columns["case_interactions"]

        constraints = pg_db._fetchall(
            conn,
            "SELECT conname, pg_get_constraintdef(oid) AS definition FROM pg_constraint WHERE connamespace='public'::regnamespace",
            (),
        )
        definitions = {
            pg_db._row_to_dict(row)["conname"]: pg_db._row_to_dict(row)["definition"]
            for row in constraints
        }
        expected = {
            "entities_revision_positive", "case_receipts_capability_digest_shape",
            "case_work_items_active_lease", "case_idempotency_expiry_order",
            "correction_change_sets_base_revision_positive", "legacy_intake_locator_unique",
        }
        assert expected <= set(definitions)
        assert "revision >= 1" in definitions["entities_revision_positive"]
        assert "^[0-9a-f]{64}$" in definitions["case_receipts_capability_digest_shape"]

        owners = pg_db._fetchall(conn, "SELECT tablename, tableowner FROM pg_tables WHERE schemaname='public' AND tablename = ANY(%s)", (list(CASE_TABLES),))
        assert {pg_db._row_to_dict(r)["tableowner"] for r in owners} == {"vl360"}


@pg_only
def test_migration_080_foreign_keys_and_indexes_are_present(pg_db):
    with pg_db._conn() as conn:
        fks = pg_db._fetchall(conn, "SELECT conname FROM pg_constraint WHERE contype='f' AND connamespace='public'::regnamespace", ())
        fk_names = {pg_db._row_to_dict(r)["conname"] for r in fks}
        assert {"case_interactions_case_id_fkey", "case_work_items_case_id_fkey", "correction_change_sets_case_id_fkey"} <= fk_names
        indexes = pg_db._fetchall(conn, "SELECT indexname FROM pg_indexes WHERE schemaname='public'", ())
        names = {pg_db._row_to_dict(r)["indexname"] for r in indexes}
        assert {"uq_case_work_items_active_lease", "idx_case_work_items_queue_priority", "idx_case_promise_clocks_due", "idx_case_outbox_retry", "idx_case_access_sessions_expiry", "idx_legacy_intake_reconcile"} <= names


@pg_only
def test_case_transition_and_audit_ledgers_are_database_immutable(pg_db):
    with pg_db._conn(commit_on_success=False) as conn:
        case_row = pg_db._fetchone(
            conn,
            "INSERT INTO cases(service_kind, category, phase, activity, disposition_family, reporter_privacy, owner_ref, promise_policy_ref) VALUES ('correction', 'schema-test', 'intake', 'active', 'undetermined', 'anonymous', 'person:test', 'policy:test') RETURNING case_id",
            (),
        )
        case_id = pg_db._row_to_dict(case_row)["case_id"]
        transition = pg_db._fetchone(
            conn,
            "INSERT INTO case_transitions(case_id, to_phase, to_revision, actor_ref, reason_code, policy_revision, correlation_id) VALUES (%s, 'intake', 1, 'person:test', 'created', 'policy:test', 'schema-test') RETURNING transition_id",
            (case_id,),
        )
        transition_id = pg_db._row_to_dict(transition)["transition_id"]
        with pytest.raises(Exception, match="immutable_case_ledger"):
            pg_db._fetchone(conn, "DELETE FROM case_transitions WHERE transition_id=%s", (transition_id,))
        conn.rollback()


def test_case_kernel_schema_status_is_dormant_or_fail_closed_without_details():
    dormant = database.case_kernel_schema_status({"backend": "sqlite", "ok": True}, enabled=False)
    assert dormant == {"ok": True, "state": "dormant", "code": "case_kernel_dormant"}

    postgresql_required = database.case_kernel_schema_status({"backend": "sqlite", "ok": True}, enabled=True)
    assert postgresql_required == {"ok": False, "state": "blocked", "code": "case_postgresql_required"}

    schema_blocked = database.case_kernel_schema_status(
        {"backend": "postgresql", "ok": True, "case_issues": ["dsn-canary schema-canary"]},
        enabled=True,
    )
    assert schema_blocked == {"ok": False, "state": "blocked", "code": "case_schema_not_ready"}
    assert "canary" not in repr(schema_blocked)


def test_core_schema_can_remain_ready_while_case_kernel_is_dormant():
    schema = {
        "backend": "postgresql",
        "ok": True,
        "schema_version": 79,
        "case_issues": ["missing tables: cases", "schema_version agent=79, expected >= 80"],
    }
    assert database.case_kernel_schema_status(schema, enabled=False)["ok"] is True
    assert database.case_kernel_schema_status(schema, enabled=True) == {
        "ok": False,
        "state": "blocked",
        "code": "case_schema_not_ready",
    }


@pg_only
def test_migration_080_schema_version_is_registered(pg_db):
    with pg_db._conn() as conn:
        row = pg_db._fetchone(conn, "SELECT version, migration FROM schema_version WHERE component='agent'", ())
    assert row is not None
    item = pg_db._row_to_dict(row)
    assert int(item["version"]) >= 80
    assert item["migration"] == "080_correction_case_kernel.sql"
