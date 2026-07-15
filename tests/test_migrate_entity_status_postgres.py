from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from scripts import migrate_entity_status as migration
from scripts.postgres_target import canonical_json_bytes, sha256_bytes


pytestmark = pytest.mark.entity_status_postgres
TEST_URL = os.environ.get("ENTITY_STATUS_TEST_DATABASE_URL")
TEST_CONFIRM = os.environ.get("ENTITY_STATUS_TEST_CONFIRM")
NOW = datetime(2026, 7, 15, 12, 10, tzinfo=UTC)
RESTORE_LISTING = (
    "; disposable PostgreSQL integration listing\n"
    "1; 1259 100 TABLE public entities owner\n"
    "2; 1259 101 TABLE public entity_changes owner\n"
)


def _quote_schema(schema: str) -> str:
    if not re.fullmatch(r"[a-z_][a-z0-9_]*", schema):
        raise AssertionError("fixture schema must be a safe generated identifier")
    return f'"{schema}"'


def _restore_listing_sha() -> str:
    return hashlib.sha256(RESTORE_LISTING.encode("utf-8")).hexdigest()


def _backup_evidence(
    tmp_path: Path, target: str, identity: dict[str, object]
) -> migration.BackupEvidence:
    root = tmp_path / "backup"
    root.mkdir()
    artifact = root / "postgres.dump"
    artifact.write_bytes(b"PGDMP-disposable-test")
    artifact_sha = hashlib.sha256(artifact.read_bytes()).hexdigest()
    manifest = {
        "schema": "vinhlong360-pg-backup-v1",
        "target": "pg",
        "target_fingerprint": target,
        "database_identity": dict(identity),
        "started_at": "2026-07-15T12:00:00Z",
        "completed_at": "2026-07-15T12:00:01Z",
        "max_age_seconds": migration.MAX_BACKUP_AGE_SECONDS,
        "tools": {
            "pg_dump": "pg_dump (PostgreSQL) 16.4",
            "pg_restore": "pg_restore (PostgreSQL) 16.4",
        },
        "artifact": {
            "path": artifact.name,
            "size": artifact.stat().st_size,
            "sha256": artifact_sha,
        },
        "validation": {
            "pg_restore_list": True,
            "required_tables": ["entities", "entity_changes"],
            "listing_sha256": _restore_listing_sha(),
        },
        "policy_revision": "published-v1",
    }
    return migration.BackupEvidence(
        manifest=manifest,
        manifest_sha256=sha256_bytes(canonical_json_bytes(manifest)),
        artifact_root=root,
    )


def _rows(cursor) -> list[dict[str, object]]:
    names = [item[0] for item in cursor.description]
    return [dict(zip(names, row, strict=True)) for row in cursor.fetchall()]


def _audit_rows(cursor, schema: str) -> list[tuple[object, ...]]:
    quoted_schema = _quote_schema(schema)
    cursor.execute(
        f"SELECT entity_id, field, old_value, new_value, actor "
        f"FROM {quoted_schema}.entity_changes "
        "ORDER BY entity_id, actor, old_value, new_value"
    )
    return cursor.fetchall()


@pytest.fixture
def pg_schema():
    if not TEST_URL or not TEST_URL.startswith("postgresql://"):
        pytest.skip(
            "set ENTITY_STATUS_TEST_DATABASE_URL to a disposable PostgreSQL database"
        )
    if TEST_CONFIRM != "disposable":
        pytest.skip(
            "set ENTITY_STATUS_TEST_CONFIRM=disposable for the disposable database"
        )
    psycopg2 = pytest.importorskip("psycopg2")
    schema = f"entity_status_{uuid.uuid4().hex}"
    quoted_schema = _quote_schema(schema)
    connection = psycopg2.connect(TEST_URL)
    created = False
    try:
        connection.autocommit = True
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE SCHEMA {quoted_schema}")
            created = True
            cursor.execute(f"SET search_path TO {quoted_schema}")
            cursor.execute(
                "CREATE TABLE entities ("
                "id TEXT PRIMARY KEY, type TEXT NOT NULL, status TEXT, "
                "verified INTEGER, attributes JSONB, source JSONB)"
            )
            cursor.execute(
                "CREATE TABLE entity_changes ("
                "id BIGSERIAL PRIMARY KEY, entity_id TEXT NOT NULL, "
                "field TEXT NOT NULL, old_value TEXT, new_value TEXT, "
                "actor TEXT, created_at TIMESTAMPTZ DEFAULT NOW())"
            )
            cursor.executemany(
                "INSERT INTO entities "
                "(id, type, status, verified, attributes, source) "
                "VALUES (%s, %s, NULL, 1, %s::jsonb, %s::jsonb)",
                [
                    (
                        entity_id,
                        "dish",
                        "{}",
                        json.dumps([{"url": source_url}]),
                    )
                    for entity_id, source_url in (
                        ("a", "https://example.org/a"),
                        ("b", "https://example.org/b"),
                    )
                ],
            )
            cursor.execute("RESET search_path")
        connection.autocommit = False
        yield connection, schema
    finally:
        try:
            connection.rollback()
            connection.autocommit = True
            if created:
                with connection.cursor() as cursor:
                    cursor.execute(f"DROP SCHEMA IF EXISTS {quoted_schema} CASCADE")
        finally:
            connection.close()


def test_postgres_apply_recovery_and_rollback_audits(
    pg_schema, tmp_path: Path
) -> None:
    connection, schema = pg_schema
    quoted_schema = _quote_schema(schema)

    with connection.cursor() as cursor:
        store = migration.PostgresPublicationStore(cursor, schema=schema)
        cursor.execute(f"SELECT * FROM {quoted_schema}.entities ORDER BY id")
        rows = _rows(cursor)
        identity = store.target_identity()
        plan = migration.build_plan(
            rows=rows,
            identity=identity,
            schema_columns=store.schema_columns(),
            created_at="2026-07-15T12:00:00Z",
            tool_source_revision="postgres-integration-test",
        )
        plan_sha = sha256_bytes(canonical_json_bytes(plan))
        backup = _backup_evidence(tmp_path, plan["target_fingerprint"], identity)
        applied = migration.apply_plan(
            store,
            plan,
            plan_sha256=plan_sha,
            backup=backup,
            confirm_target=plan["target_fingerprint"],
            now=NOW,
            restore_validator=lambda _artifact: _restore_listing_sha(),
            clock=lambda: NOW,
        )
    connection.commit()

    assert applied["result"] == "applied"
    assert applied["updated_ids"] == ["a", "b"]

    with connection.cursor() as cursor:
        store = migration.PostgresPublicationStore(cursor, schema=schema)
        assert store.status_counts() == {"published": 2, "null": 0}
        apply_actor = migration.audit_actor("apply", plan_sha)
        assert _audit_rows(cursor, schema) == [
            ("a", "status", "null", "published", apply_actor),
            ("b", "status", "null", "published", apply_actor),
        ]
        repeated = migration.apply_plan(
            store,
            plan,
            plan_sha256=plan_sha,
            backup=backup,
            confirm_target=plan["target_fingerprint"],
            now=NOW,
            restore_validator=lambda _artifact: _restore_listing_sha(),
            clock=lambda: NOW,
        )
    connection.commit()

    assert repeated["result"] == "already-applied"
    assert repeated["recovery_ready"] is True
    assert repeated["recovery_contract"] == "apply-audit-exact-v1"
    assert repeated["updated_ids"] == ["a", "b"]

    with connection.cursor() as cursor:
        assert _audit_rows(cursor, schema) == [
            ("a", "status", "null", "published", apply_actor),
            ("b", "status", "null", "published", apply_actor),
        ]

    rollback_now = NOW + timedelta(minutes=10)
    repeated_sha = sha256_bytes(canonical_json_bytes(repeated))
    with connection.cursor() as cursor:
        store = migration.PostgresPublicationStore(cursor, schema=schema)
        rolled_back = migration.rollback_apply(
            store,
            repeated,
            apply_report_sha256=repeated_sha,
            backup=backup,
            confirm_target=plan["target_fingerprint"],
            now=rollback_now,
            restore_validator=lambda _artifact: _restore_listing_sha(),
            clock=lambda: rollback_now,
        )
    connection.commit()

    assert rolled_back["result"] == "rolled-back"
    assert rolled_back["restored_ids"] == ["a", "b"]

    with connection.cursor() as cursor:
        store = migration.PostgresPublicationStore(cursor, schema=schema)
        assert store.status_counts() == {"published": 0, "null": 2}
        rollback_actor = migration.audit_actor("rollback", plan_sha)
        assert _audit_rows(cursor, schema) == [
            ("a", "status", "null", "published", apply_actor),
            ("a", "status", "published", "null", rollback_actor),
            ("b", "status", "null", "published", apply_actor),
            ("b", "status", "published", "null", rollback_actor),
        ]
        repeated_rollback = migration.rollback_apply(
            store,
            repeated,
            apply_report_sha256=repeated_sha,
            backup=backup,
            confirm_target=plan["target_fingerprint"],
            now=rollback_now,
            restore_validator=lambda _artifact: _restore_listing_sha(),
            clock=lambda: rollback_now,
        )
    connection.commit()

    assert repeated_rollback["result"] == "already-rolled-back"
    assert repeated_rollback["recovery_ready"] is True
    assert repeated_rollback["recovery_contract"] == "rollback-audit-exact-v1"
    assert repeated_rollback["restored_ids"] == []

    with connection.cursor() as cursor:
        store = migration.PostgresPublicationStore(cursor, schema=schema)
        assert store.status_counts() == {"published": 0, "null": 2}
        assert _audit_rows(cursor, schema) == [
            ("a", "status", "null", "published", apply_actor),
            ("a", "status", "published", "null", rollback_actor),
            ("b", "status", "null", "published", apply_actor),
            ("b", "status", "published", "null", rollback_actor),
        ]


def test_postgres_advisory_lock_excludes_second_transaction(pg_schema) -> None:
    _fixture_connection, schema = pg_schema
    psycopg2 = pytest.importorskip("psycopg2")
    first = psycopg2.connect(TEST_URL)
    second = psycopg2.connect(TEST_URL)
    try:
        with first.cursor() as first_cursor, second.cursor() as second_cursor:
            migration.PostgresPublicationStore(
                first_cursor, schema=schema
            ).acquire_lock(migration.LOCK_NAME)
            second_cursor.execute(
                "SELECT pg_try_advisory_xact_lock(hashtext(%s))",
                (migration.LOCK_NAME,),
            )
            assert second_cursor.fetchone()[0] is False
            first.rollback()
            second_cursor.execute(
                "SELECT pg_try_advisory_xact_lock(hashtext(%s))",
                (migration.LOCK_NAME,),
            )
            assert second_cursor.fetchone()[0] is True
    finally:
        first.rollback()
        second.rollback()
        first.close()
        second.close()
