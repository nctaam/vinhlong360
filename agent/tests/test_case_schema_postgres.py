"""Real PostgreSQL contract checks for migration 080.

The test target is intentionally opt-in and loopback-only.  No ambient or
production DSN is accepted; absent target means explicit pytest skips.
"""
from __future__ import annotations

import os
import sys
import asyncio
import json
import subprocess
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agent"))
sys.path.insert(0, str(ROOT))

import database  # noqa: E402
from agent import database as database_readiness  # noqa: E402 - staged pairing guard
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
    "correction_change_sets", "correction_change_set_items", "legacy_intake_records", "case_capacity_events",
)


@pg_only
def test_migration_080_tables_columns_constraints_and_owners(pg_db):
    with pg_db._conn() as conn:
        rows = pg_db._fetchall(conn, "SELECT table_name FROM information_schema.tables WHERE table_schema='public'", ())
        tables = {pg_db._row_to_dict(r)["table_name"] for r in rows}
        assert set(CASE_TABLES) <= tables

        columns = {}
        for table in (*CASE_TABLES, "entities"):
            rows = pg_db._fetchall(conn, "SELECT column_name, data_type FROM information_schema.columns WHERE table_schema='public' AND table_name=%s", (table,))
            columns[table] = {pg_db._row_to_dict(r)["column_name"]: pg_db._row_to_dict(r)["data_type"] for r in rows}
        assert columns["cases"]["case_id"] == "uuid"
        assert columns["cases"]["current_revision"] == "integer"
        assert columns["case_receipts"]["capability_digest"] in {"text", "bytea"}
        assert columns["case_receipts"]["receipt_revision"] == "integer"
        assert columns["case_receipts"]["subject_user_id"] == "text"
        assert columns["case_access_sessions"]["session_key_version"] == "text"
        assert columns["case_idempotency"]["response_key_version"] == "text"
        assert "capability" not in columns["case_receipts"]
        assert not ({"contact", "phone", "email"} & set(columns["case_contact_challenges"]))
        assert "content_enc" in columns["correction_evidence"]
        assert "severity" in columns["cases"]
        assert "payload_enc" in columns["case_interactions"]
        for table, required in database.CASE_KERNEL_REQUIRED_COLUMNS.items():
            assert required <= set(columns[table]), f"readiness map drift for {table}"

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
        assert "confirmed_current" in definitions["case_decisions_outcome_code_check"]
        assert "unable_to_verify" in definitions["case_decisions_outcome_code_check"]
        assert "fulfillment" in definitions["case_transitions_from_phase_check"]
        assert "fulfillment" in definitions["case_transitions_to_phase_check"]
        assert "receipt_revision >= 1" in definitions["case_receipts_receipt_revision_positive"]

        owners = pg_db._fetchall(conn, "SELECT tablename, tableowner FROM pg_tables WHERE schemaname='public' AND tablename = ANY(%s)", (list(CASE_TABLES),))
        assert {pg_db._row_to_dict(r)["tableowner"] for r in owners} == {"vl360"}


@pg_only
def test_migration_080_foreign_keys_and_indexes_are_present(pg_db):
    with pg_db._conn() as conn:
        fks = pg_db._fetchall(conn, "SELECT conname FROM pg_constraint WHERE contype='f' AND connamespace='public'::regnamespace", ())
        fk_names = {pg_db._row_to_dict(r)["conname"] for r in fks}
        assert {"case_interactions_case_id_fkey", "case_work_items_case_id_fkey", "correction_change_sets_case_id_fkey", "correction_change_set_items_change_set_id_fkey", "correction_change_set_items_item_id_fkey"} <= fk_names
        indexes = pg_db._fetchall(conn, "SELECT indexname FROM pg_indexes WHERE schemaname='public'", ())
        names = {pg_db._row_to_dict(r)["indexname"] for r in indexes}
        assert {"uq_case_work_items_active_lease", "idx_case_work_items_queue_priority", "idx_case_promise_clocks_due", "idx_case_outbox_retry", "idx_case_access_sessions_expiry", "idx_legacy_intake_reconcile"} <= names


@pg_only
def test_rerunning_080_reconciles_provisional_receipt_security_columns(pg_db):
    old_080 = _git_file_at("0b125e21", "agent/migrations/080_correction_case_kernel.sql")
    old_init = _git_file_at("0b125e21", "init.sql")
    current_080 = (ROOT / "agent" / "migrations" / "080_correction_case_kernel.sql").read_text(encoding="utf-8")
    with pg_db._conn(commit_on_success=False) as conn:
        try:
            pg_db._execute(conn, "DROP SCHEMA public CASCADE", ())
            pg_db._execute(conn, "CREATE SCHEMA public", ())
            pg_db._execute(conn, old_init, ())
            pg_db._execute(conn, old_080, ())
            case_id = pg_db._row_to_dict(pg_db._fetchone(conn, "INSERT INTO cases(service_kind, category, phase, activity, disposition_family, reporter_privacy, owner_ref, promise_policy_ref) VALUES ('correction', 'receipt-replay', 'intake', 'active', 'undetermined', 'anonymous', 'person:test', 'policy:test') RETURNING case_id", ())) ["case_id"]
            for reference, digest in (("VL-COR-0000000000000", "a" * 64), ("VL-COR-0000000000011", "b" * 64)):
                pg_db._execute(conn, "INSERT INTO case_receipts(case_id, public_reference, capability_digest, capability_key_version, expires_at) VALUES (%s, %s, %s, 'v1', NOW() + INTERVAL '1 day')", (case_id, reference, digest))
            pg_db._execute(conn, current_080, ())
            rows = pg_db._fetchall(conn, "SELECT receipt_revision, subject_user_id FROM case_receipts WHERE case_id=%s ORDER BY receipt_revision", (case_id,))
            assert [(item["receipt_revision"], item["subject_user_id"]) for item in map(pg_db._row_to_dict, rows)] == [(1, None), (2, None)]
            columns = pg_db._fetchall(conn, "SELECT column_name FROM information_schema.columns WHERE table_name='case_access_sessions'", ())
            assert "session_key_version" in {item["column_name"] for item in map(pg_db._row_to_dict, columns)}
        finally:
            conn.rollback()


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
    assert database_readiness.CASE_KERNEL_REQUIRED_COLUMNS == database.CASE_KERNEL_REQUIRED_COLUMNS
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


def test_case_activation_status_codes_cover_owner_and_key_failures_without_secret_leaks():
    for code in ("case_encryption_key_required", "case_owner_individual_required"):
        status = database.case_kernel_schema_status(
            {"backend": "postgresql", "ok": True, "case_issues": [], "case_config_code": code},
            enabled=True,
        )
        assert status == {"ok": False, "state": "blocked", "code": code}
    assert "secret-value" not in repr(status)


def test_enabled_readiness_reports_stable_key_and_owner_codes(monkeypatch):
    import config
    import data_lifecycle
    import privacy_policy

    @contextmanager
    def fake_conn():
        yield object()

    monkeypatch.setattr(server.knowledge, "_entities", {"sentinel": {}})
    monkeypatch.setattr(server.knowledge, "_data_source", "db")
    monkeypatch.setattr(server, "privacy_boundary_readiness", lambda: True)
    monkeypatch.setattr(server, "scheduler_status", lambda: {"erasure": {"audit_only": True}})
    monkeypatch.setattr(data_lifecycle, "lifecycle_registry_readiness", lambda: {"ok": True})
    monkeypatch.setattr(privacy_policy, "privacy_policy_readiness", lambda _settings: True)
    monkeypatch.setattr(database.db, "_conn", fake_conn)
    monkeypatch.setattr(database.db, "_fetchone", lambda *_args, **_kwargs: (1,))
    monkeypatch.setattr(database.db, "pg_schema_status", lambda: {"backend": "postgresql", "ok": True, "case_issues": []})
    monkeypatch.setattr(config.settings, "CASE_KERNEL_ENABLED", True)
    for flag in ("CORRECTION_INTAKE_ENABLED", "CORRECTION_ADMIN_ENABLED", "CORRECTION_ASSISTED_ENABLED", "CORRECTION_PUBLICATION_ENABLED"):
        monkeypatch.setattr(config.settings, flag, False)

    monkeypatch.setattr(config.settings, "CASE_KERNEL_ENCRYPTION_KEY", "")
    monkeypatch.setattr(config.settings, "CASE_SERVICE_OWNER_REF", "person:owner")
    response = asyncio.run(server.readiness_probe())
    payload = json.loads(response.body)
    assert response.status_code == 503
    assert payload["checks"]["case_kernel_schema"] == {"ok": True, "state": "ready", "code": "case_kernel_ready"}
    assert payload["checks"]["case_kernel_key"] == {"ok": False, "state": "blocked", "code": "case_encryption_key_required"}
    assert payload["checks"]["case_owner"] == {"ok": True, "state": "ready", "code": "case_owner_ready"}

    import base64
    monkeypatch.setattr(config.settings, "CASE_KERNEL_ENCRYPTION_KEY", base64.urlsafe_b64encode(b"r" * 32).decode("ascii"))
    monkeypatch.setattr(config.settings, "CASE_SERVICE_OWNER_REF", "team:operators")
    response = asyncio.run(server.readiness_probe())
    payload = json.loads(response.body)
    assert response.status_code == 503
    assert payload["checks"]["case_kernel_schema"] == {"ok": True, "state": "ready", "code": "case_kernel_ready"}
    assert payload["checks"]["case_kernel_key"] == {"ok": True, "state": "ready", "code": "case_kernel_key_ready"}
    assert payload["checks"]["case_owner"] == {"ok": False, "state": "blocked", "code": "case_owner_individual_required"}
    assert "adequate-secret-material" not in repr(payload)


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
def test_change_set_item_linkage_is_relational_and_immutable(pg_db):
    with pg_db._conn(commit_on_success=False) as conn:
        case_rows = pg_db._fetchall(
            conn,
            "INSERT INTO cases(service_kind, category, phase, activity, disposition_family, reporter_privacy, owner_ref, promise_policy_ref) VALUES ('correction', 'linkage-test', 'intake', 'active', 'undetermined', 'anonymous', 'person:test', 'policy:test') RETURNING case_id",
            (),
        )
        case_id = pg_db._row_to_dict(case_rows[0])["case_id"]
        item_row = pg_db._fetchone(
            conn,
            "INSERT INTO correction_items(case_id, field_path, base_entity_revision, risk_class, evidence_level) VALUES (%s, 'name', 1, 'R0', 'E0') RETURNING item_id",
            (case_id,),
        )
        item_id = pg_db._row_to_dict(item_row)["item_id"]
        other_case = pg_db._fetchone(
            conn,
            "INSERT INTO cases(service_kind, category, phase, activity, disposition_family, reporter_privacy, owner_ref, promise_policy_ref) VALUES ('correction', 'other-case', 'intake', 'active', 'undetermined', 'anonymous', 'person:test', 'policy:test') RETURNING case_id",
            (),
        )
        other_case_id = pg_db._row_to_dict(other_case)["case_id"]
        other_item = pg_db._fetchone(
            conn,
            "INSERT INTO correction_items(case_id, field_path, base_entity_revision, risk_class, evidence_level) VALUES (%s, 'name', 1, 'R0', 'E0') RETURNING item_id",
            (other_case_id,),
        )
        other_item_id = pg_db._row_to_dict(other_item)["item_id"]
        change_row = pg_db._fetchone(
            conn,
            "INSERT INTO correction_change_sets(case_id, base_entity_revision, before_patch, after_patch, inverse_patch, policy_revision, risk_class, decision_maker_ref) VALUES (%s, 1, '{}'::jsonb, '{}'::jsonb, '{}'::jsonb, 'policy:test', 'R0', 'person:test') RETURNING change_set_id",
            (case_id,),
        )
        change_id = pg_db._row_to_dict(change_row)["change_set_id"]
        pg_db._execute(conn, "INSERT INTO correction_change_set_items(change_set_id, item_id) VALUES (%s, %s)", (change_id, item_id))
        pg_db._execute(conn, "SAVEPOINT invalid_item", ())
        with pytest.raises(Exception):
            pg_db._execute(conn, "INSERT INTO correction_change_set_items(change_set_id, item_id) VALUES (%s, %s)", (change_id, "00000000-0000-0000-0000-000000000000"))
        pg_db._execute(conn, "ROLLBACK TO SAVEPOINT invalid_item", ())
        pg_db._execute(conn, "SAVEPOINT cross_case_item", ())
        with pytest.raises(Exception, match="change_set_item_case_mismatch"):
            pg_db._execute(conn, "INSERT INTO correction_change_set_items(change_set_id, item_id) VALUES (%s, %s)", (change_id, other_item_id))
        pg_db._execute(conn, "ROLLBACK TO SAVEPOINT cross_case_item", ())
        pg_db._execute(conn, "SAVEPOINT linked_item_case_move", ())
        with pytest.raises(Exception, match="change_set_item_case_mismatch"):
            pg_db._execute(conn, "UPDATE correction_items SET case_id=%s WHERE item_id=%s", (other_case_id, item_id))
        pg_db._execute(conn, "ROLLBACK TO SAVEPOINT linked_item_case_move", ())
        pg_db._execute(conn, "SAVEPOINT immutable_link", ())
        with pytest.raises(Exception, match="immutable_case_ledger"):
            pg_db._execute(conn, "DELETE FROM correction_change_set_items WHERE change_set_id=%s AND item_id=%s", (change_id, item_id))
        pg_db._execute(conn, "ROLLBACK TO SAVEPOINT immutable_link", ())
        with pytest.raises(Exception, match="immutable_case_ledger"):
            pg_db._fetchone(conn, "DELETE FROM correction_change_sets WHERE change_set_id=%s", (change_id,))
        conn.rollback()


@pg_only
def test_case_decision_outcome_constraint_matches_the_locked_contract(pg_db):
    permitted = (
        "corrected", "confirmed_current", "insufficient_evidence", "out_of_scope",
        "duplicate_linked", "unable_to_verify", "withdrawn_by_requester",
    )
    rejected = ("accepted", "rejected", "pending", "")
    with pg_db._conn(commit_on_success=False) as conn:
        pg_db._execute(conn, (ROOT / "agent" / "migrations" / "080_correction_case_kernel.sql").read_text(encoding="utf-8"), ())
        case_id = pg_db._row_to_dict(pg_db._fetchone(
            conn,
            "INSERT INTO cases(service_kind, category, phase, activity, disposition_family, reporter_privacy, owner_ref, promise_policy_ref) VALUES ('correction', 'outcome-test', 'intake', 'active', 'undetermined', 'anonymous', 'person:test', 'policy:test') RETURNING case_id",
            (),
        ))["case_id"]
        for outcome in permitted:
            pg_db._execute(
                conn,
                "INSERT INTO case_decisions(case_id, outcome_code, reason_code, decision_maker_ref, policy_revision) VALUES (%s, %s, 'schema-test', 'person:test', 'policy:test')",
                (case_id, outcome),
            )
        for outcome in rejected:
            pg_db._execute(conn, "SAVEPOINT invalid_outcome", ())
            with pytest.raises(Exception):
                pg_db._execute(
                    conn,
                    "INSERT INTO case_decisions(case_id, outcome_code, reason_code, decision_maker_ref, policy_revision) VALUES (%s, %s, 'schema-test', 'person:test', 'policy:test')",
                    (case_id, outcome),
                )
            pg_db._execute(conn, "ROLLBACK TO SAVEPOINT invalid_outcome", ())
        conn.rollback()


def _git_file_at(revision: str, path: str) -> str:
    return subprocess.run(
        ["git", "show", f"{revision}:{path}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout.decode("utf-8")


@pg_only
def test_rerunning_080_upgrades_the_provisional_dac9960b_shape(pg_db):
    """080 must reconcile its provisional shape when replayed directly."""
    old_init = _git_file_at("dac9960b", "init.sql")
    old_080 = _git_file_at("dac9960b", "agent/migrations/080_correction_case_kernel.sql")
    current_080 = (ROOT / "agent" / "migrations" / "080_correction_case_kernel.sql").read_text(encoding="utf-8")
    with pg_db._conn(commit_on_success=False) as conn:
        try:
            pg_db._execute(conn, "DROP SCHEMA public CASCADE", ())
            pg_db._execute(conn, "CREATE SCHEMA public", ())
            pg_db._execute(conn, old_init, ())
            pg_db._execute(conn, old_080, ())
            case_id = pg_db._row_to_dict(pg_db._fetchone(
                conn,
                "INSERT INTO cases(service_kind, category, phase, activity, disposition_family, reporter_privacy, owner_ref, promise_policy_ref) VALUES ('correction', 'replay-test', 'intake', 'active', 'undetermined', 'anonymous', 'person:test', 'policy:test') RETURNING case_id",
                (),
            ))["case_id"]
            item_id = pg_db._row_to_dict(pg_db._fetchone(
                conn,
                "INSERT INTO correction_items(case_id, field_path, base_entity_revision, risk_class, evidence_level) VALUES (%s, 'name', 1, 'R0', 'E0') RETURNING item_id",
                (case_id,),
            ))["item_id"]
            pg_db._execute(
                conn,
                "INSERT INTO correction_change_sets(case_id, item_ids, base_entity_revision, before_patch, after_patch, inverse_patch, policy_revision, risk_class, decision_maker_ref) VALUES (%s, %s::jsonb, 1, '{}'::jsonb, '{}'::jsonb, '{}'::jsonb, 'policy:test', 'R0', 'person:test')",
                (case_id, json.dumps([str(item_id)])),
            )
            pg_db._execute(conn, current_080, ())
            columns = pg_db._fetchall(
                conn,
                "SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='correction_change_sets'",
                (),
            )
            assert "item_ids" not in {pg_db._row_to_dict(row)["column_name"] for row in columns}
            constraints = pg_db._fetchall(
                conn,
                "SELECT pg_get_constraintdef(oid) AS definition FROM pg_constraint WHERE conname='case_decisions_outcome_code_check'",
                (),
            )
            assert "accepted" not in pg_db._row_to_dict(constraints[0])["definition"]
            links = pg_db._fetchall(conn, "SELECT item_id FROM correction_change_set_items", ())
            assert {str(pg_db._row_to_dict(row)["item_id"]) for row in links} == {str(item_id)}
        finally:
            conn.rollback()


@pg_only
def test_rerunning_080_fails_closed_for_unmigratable_provisional_item_ids(pg_db):
    old_init = _git_file_at("dac9960b", "init.sql")
    old_080 = _git_file_at("dac9960b", "agent/migrations/080_correction_case_kernel.sql")
    current_080 = (ROOT / "agent" / "migrations" / "080_correction_case_kernel.sql").read_text(encoding="utf-8")
    with pg_db._conn(commit_on_success=False) as conn:
        try:
            pg_db._execute(conn, "DROP SCHEMA public CASCADE", ())
            pg_db._execute(conn, "CREATE SCHEMA public", ())
            pg_db._execute(conn, old_init, ())
            pg_db._execute(conn, old_080, ())
            case_id = pg_db._row_to_dict(pg_db._fetchone(
                conn,
                "INSERT INTO cases(service_kind, category, phase, activity, disposition_family, reporter_privacy, owner_ref, promise_policy_ref) VALUES ('correction', 'replay-invalid', 'intake', 'active', 'undetermined', 'anonymous', 'person:test', 'policy:test') RETURNING case_id",
                (),
            ))["case_id"]
            pg_db._execute(
                conn,
                "INSERT INTO correction_change_sets(case_id, item_ids, base_entity_revision, before_patch, after_patch, inverse_patch, policy_revision, risk_class, decision_maker_ref) VALUES (%s, '{\"not\": \"an array\"}'::jsonb, 1, '{}'::jsonb, '{}'::jsonb, '{}'::jsonb, 'policy:test', 'R0', 'person:test')",
                (case_id,),
            )
            with pytest.raises(Exception, match="correction_change_set_item_ids_unmigratable"):
                pg_db._execute(conn, current_080, ())
        finally:
            conn.rollback()


@pg_only
def test_migration_080_schema_version_is_registered(pg_db):
    with pg_db._conn() as conn:
        row = pg_db._fetchone(conn, "SELECT version, migration FROM schema_version WHERE component='agent'", ())
    assert row is not None
    item = pg_db._row_to_dict(row)
    assert int(item["version"]) >= 80
    assert item["migration"] == "080_correction_case_kernel.sql"
