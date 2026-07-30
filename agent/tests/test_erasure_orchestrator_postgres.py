"""Disposable PostgreSQL evidence for the hard-erasure orchestrator."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from threading import Event, Thread
from urllib.parse import unquote, urlparse

import psycopg2
import psycopg2.extras
import pytest

import data_lifecycle
import database as database_module
import erasure
import quarantine


UTC = timezone.utc
NOW = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)
THREAD_TIMEOUT = 10


def _test_database_url() -> str | None:
    url = os.environ.get("TRUST_ERASURE_TEST_DATABASE_URL")
    if not url:
        return None
    parsed = urlparse(url)
    database_name = unquote(parsed.path.lstrip("/"))
    explicitly_allowed = os.environ.get(
        "TRUST_ERASURE_ALLOW_PG_TESTS", ""
    ).lower() in {"1", "true", "yes", "on"}
    if parsed.scheme not in {"postgres", "postgresql"} or not database_name:
        raise pytest.UsageError(
            "TRUST_ERASURE_TEST_DATABASE_URL must be a PostgreSQL URL"
        )
    if "test" not in database_name.lower() and not explicitly_allowed:
        raise pytest.UsageError(
            "PostgreSQL trust-erasure tests require a database name containing "
            "'test' or TRUST_ERASURE_ALLOW_PG_TESTS=true"
        )
    if (
        parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
        and not explicitly_allowed
    ):
        raise pytest.UsageError(
            "Non-loopback PostgreSQL trust-erasure tests require "
            "TRUST_ERASURE_ALLOW_PG_TESTS=true"
        )
    return url


TEST_DATABASE_URL = _test_database_url()
pytestmark = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="set TRUST_ERASURE_TEST_DATABASE_URL to a disposable PostgreSQL DB",
)


class Metric:
    def __init__(self):
        self.calls = []

    def inc(self, labels=None, amount=1):
        self.calls.append((labels, amount))


class Gate:
    def __init__(self):
        self.unblocked = []

    def unblock_owner(self, owner_key):
        self.unblocked.append(owner_key)


@pytest.fixture
def pg_erasure_db(monkeypatch):
    assert TEST_DATABASE_URL is not None
    schema = f"erasure_orchestrator_{uuid.uuid4().hex}"
    with psycopg2.connect(TEST_DATABASE_URL) as conn:
        with conn.cursor() as cursor:
            cursor.execute(f'CREATE SCHEMA "{schema}"')
            cursor.execute(f'SET search_path TO "{schema}"')
            cursor.execute(
                """
                CREATE TABLE users (
                    id UUID PRIMARY KEY,
                    phone TEXT NOT NULL,
                    is_active BOOLEAN NOT NULL DEFAULT FALSE,
                    deleted_at TIMESTAMPTZ,
                    erasure_due_at TIMESTAMPTZ,
                    erasure_attempt_count INTEGER NOT NULL DEFAULT 0,
                    erasure_last_attempt_at TIMESTAMPTZ,
                    erasure_last_error_code TEXT
                )
                """
            )

    database_module.psycopg2 = psycopg2
    database_module.psycopg2.extras = psycopg2.extras
    adapter = database_module.Database()
    adapter._use_pg = True
    adapter._dsn = psycopg2.extensions.make_dsn(
        TEST_DATABASE_URL,
        options=f"-c search_path={schema}",
    )
    adapter.initialize = lambda: None
    cleanup_events = []
    monkeypatch.setattr(erasure, "db", adapter)
    monkeypatch.setattr(quarantine, "db", adapter)
    monkeypatch.setattr(erasure, "validate_lifecycle_registry", lambda _policies: ())
    monkeypatch.setattr(
        erasure,
        "scrub_user_references",
        lambda *_args, **_kwargs: cleanup_events.append("scrub"),
    )
    monkeypatch.setattr(
        erasure,
        "validate_user_fk_actions",
        lambda _conn: cleanup_events.append("validate") or (),
    )
    monkeypatch.setattr(
        erasure,
        "_assert_structured_absent",
        lambda _conn, _user_id: cleanup_events.append("verify_structured"),
    )
    monkeypatch.setattr(quarantine, "owner_write_gate", Gate())
    for name in (
        "erasure_due_total",
        "erasure_completed_total",
        "erasure_failed_total",
        "erasure_overdue_total",
    ):
        monkeypatch.setattr(erasure.metrics, name, Metric())

    try:
        yield adapter, cleanup_events
    finally:
        with psycopg2.connect(TEST_DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                cursor.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')


def _seed_due_user(pg_db, *, due_at=NOW - timedelta(seconds=1)) -> str:
    user_id = str(uuid.uuid4())
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            """
            INSERT INTO users (
                id, phone, is_active, deleted_at, erasure_due_at
            ) VALUES (%s::uuid, %s, FALSE, %s, %s)
            """,
            (
                user_id,
                f"test-{uuid.uuid4().hex}",
                NOW - timedelta(days=30),
                due_at,
            ),
        )
    return user_id


def _user_row(pg_db, user_id: str):
    with pg_db._conn(commit_on_success=False) as conn:
        row = pg_db._fetchone(
            conn,
            """
            SELECT id::text AS id, phone, is_active, deleted_at,
                   erasure_due_at, erasure_attempt_count,
                   erasure_last_attempt_at, erasure_last_error_code
            FROM users WHERE id::text = %s
            """,
            (user_id,),
        )
    return pg_db._row_to_dict(row) if row else None


def _registry(purge, verify):
    return data_lifecycle.LifecycleRegistry(
        [
            data_lifecycle.DataStorePolicy(
                name="postgres_test_store",
                classification="personal",
                purge=purge,
                verify=verify,
                description="Disposable PostgreSQL test store",
            )
        ]
    )


def test_orchestrator_commits_attempt_before_external_purge(pg_erasure_db, monkeypatch):
    pg_db, cleanup_events = pg_erasure_db
    user_id = _seed_due_user(pg_db)
    owner_key = f"user:{user_id}"
    store = {owner_key: "personal"}
    observed_markers = []

    def purge(selected_owner):
        observed_markers.append(_user_row(pg_db, user_id)["erasure_last_attempt_at"])
        store.pop(selected_owner, None)
        return data_lifecycle.PurgeResult("postgres_test_store", removed_count=1)

    def verify(selected_owner):
        return data_lifecycle.VerificationResult(
            "postgres_test_store",
            absent=selected_owner not in store,
        )

    monkeypatch.setattr(erasure, "lifecycle_registry", _registry(purge, verify))

    result = erasure.erase_account(user_id, now=NOW, run_id="postgres-run")

    assert result.status == "completed"
    assert result.verified is True
    assert observed_markers == [NOW]
    assert _user_row(pg_db, user_id) is None
    assert cleanup_events == ["scrub", "validate", "verify_structured"]


def test_final_transaction_rolls_back_and_retains_due_user(
    pg_erasure_db,
    monkeypatch,
):
    pg_db, _cleanup_events = pg_erasure_db
    user_id = _seed_due_user(pg_db)
    owner_key = f"user:{user_id}"
    store = {owner_key: "personal"}
    original_phone = _user_row(pg_db, user_id)["phone"]

    def purge(selected_owner):
        store.pop(selected_owner, None)
        return data_lifecycle.PurgeResult("postgres_test_store", removed_count=1)

    def verify(selected_owner):
        return data_lifecycle.VerificationResult(
            "postgres_test_store",
            absent=selected_owner not in store,
        )

    def scrub_then_fail(conn, selected_user_id, **_kwargs):
        pg_db._execute(
            conn,
            "UPDATE users SET phone = %s WHERE id::text = %s",
            ("rolled-back", selected_user_id),
        )
        raise RuntimeError("injected structured cleanup failure")

    monkeypatch.setattr(erasure, "lifecycle_registry", _registry(purge, verify))
    monkeypatch.setattr(erasure, "scrub_user_references", scrub_then_fail)

    result = erasure.erase_account(user_id, now=NOW)

    row = _user_row(pg_db, user_id)
    assert result.status == "failed"
    assert result.error_code == "DB_CONSTRAINT"
    assert row["phone"] == original_phone
    assert row["deleted_at"] is not None
    assert row["erasure_attempt_count"] == 1
    assert row["erasure_last_error_code"] == "DB_CONSTRAINT"


def test_recovery_cannot_reactivate_during_external_purge(
    pg_erasure_db,
    monkeypatch,
):
    pg_db, _cleanup_events = pg_erasure_db
    user_id = _seed_due_user(pg_db, due_at=NOW)
    owner_key = f"user:{user_id}"
    store = {owner_key: "personal"}
    purge_started = Event()
    release_purge = Event()

    def purge(selected_owner):
        purge_started.set()
        assert release_purge.wait(timeout=THREAD_TIMEOUT)
        store.pop(selected_owner, None)
        return data_lifecycle.PurgeResult("postgres_test_store", removed_count=1)

    def verify(selected_owner):
        return data_lifecycle.VerificationResult(
            "postgres_test_store",
            absent=selected_owner not in store,
        )

    monkeypatch.setattr(erasure, "lifecycle_registry", _registry(purge, verify))
    results = []
    worker = Thread(
        target=lambda: results.append(erasure.erase_account(user_id, now=NOW))
    )
    worker.start()
    assert purge_started.wait(timeout=THREAD_TIMEOUT)

    recovery = quarantine.recover_account(
        user_id,
        now=NOW - timedelta(microseconds=1),
    )

    release_purge.set()
    worker.join(timeout=THREAD_TIMEOUT)
    assert not worker.is_alive()
    assert recovery.recovered is False
    assert results[0].status == "completed"
    assert _user_row(pg_db, user_id) is None
