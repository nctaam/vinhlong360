from __future__ import annotations

import hashlib
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse

import psycopg2
import psycopg2.extras
import pytest

import database as database_module
import feedback_policy
from owner_write_gate import OwnerWriteGate


ROOT = Path(__file__).resolve().parents[2]
MIGRATION_SQL = (
    ROOT / "agent" / "migrations" / "071_feedback_receipts.sql"
).read_text(encoding="utf-8")
NOW = datetime(2026, 7, 29, 12, 0, tzinfo=timezone.utc)
TURN_DIGEST = "b" * 64


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
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"} and not explicitly_allowed:
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


@pytest.fixture(scope="session", autouse=True)
def _postgres_schema():
    assert TEST_DATABASE_URL is not None
    with psycopg2.connect(TEST_DATABASE_URL) as conn:
        with conn.cursor() as cursor:
            cursor.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    phone TEXT UNIQUE NOT NULL,
                    deleted_at TIMESTAMPTZ
                )
                """
            )
            cursor.execute(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ"
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_version (
                    component TEXT PRIMARY KEY,
                    version INTEGER NOT NULL,
                    migration TEXT NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cursor.execute(MIGRATION_SQL)
    yield
    with psycopg2.connect(TEST_DATABASE_URL) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "TRUNCATE feedback_daily_rollups, feedback_receipts, users CASCADE"
            )


@pytest.fixture
def pg_store(monkeypatch):
    assert TEST_DATABASE_URL is not None
    database_module.psycopg2 = psycopg2
    database_module.psycopg2.extras = psycopg2.extras
    adapter = database_module.Database()
    adapter._use_pg = True
    adapter._dsn = TEST_DATABASE_URL
    monkeypatch.setattr(feedback_policy, "db", adapter)
    monkeypatch.setattr(feedback_policy, "_store", feedback_policy.PostgresFeedbackStore())

    def read_deleted_at(user_id: str):
        with adapter._conn(commit_on_success=False) as conn:
            row = adapter._fetchone(
                conn,
                "SELECT deleted_at FROM users WHERE id = %s::uuid",
                (user_id,),
            )
        return None if row is None else row["deleted_at"]

    monkeypatch.setattr(
        feedback_policy,
        "owner_write_gate",
        OwnerWriteGate(state_reader=read_deleted_at),
    )

    with psycopg2.connect(TEST_DATABASE_URL) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "TRUNCATE feedback_daily_rollups, feedback_receipts, users CASCADE"
            )
    return adapter


def _seed_user(pg_store) -> str:
    user_id = str(uuid.uuid4())
    with pg_store._conn() as conn:
        pg_store._execute(
            conn,
            "INSERT INTO users (id, phone) VALUES (%s::uuid, %s)",
            (user_id, f"test-{uuid.uuid4().hex}"),
        )
    return user_id


def _receipt_row(pg_store, token: str) -> dict:
    digest = hashlib.sha256(token.encode("ascii")).hexdigest()
    with pg_store._conn(commit_on_success=False) as conn:
        row = pg_store._fetchone(
            conn,
            "SELECT * FROM feedback_receipts WHERE token_digest = %s",
            (digest,),
        )
    return dict(row)


def test_authenticated_and_anonymous_issuance_store_only_digests(pg_store):
    user_id = _seed_user(pg_store)
    auth = feedback_policy.issue_feedback_receipt(
        f"user:{user_id}", TURN_DIGEST, "cx/gpt-5.4", "search", now=NOW
    )
    anon = feedback_policy.issue_feedback_receipt(
        f"anon:{'a' * 64}", TURN_DIGEST, "unknown", "unknown", now=NOW
    )

    assert auth is not None and anon is not None
    auth_row = _receipt_row(pg_store, auth.token)
    anon_row = _receipt_row(pg_store, anon.token)
    assert auth.token not in repr(auth_row)
    assert anon.token not in repr(anon_row)
    assert str(auth_row["user_id"]) == user_id
    assert auth_row["anonymous_owner_digest"] is None
    assert anon_row["user_id"] is None
    assert anon_row["anonymous_owner_digest"] == "a" * 64
    assert anon_row["model_variant"] == "other"
    assert anon_row["tool_bucket"] == "mixed"


def test_receipt_expires_at_twenty_four_hours(pg_store):
    receipt = feedback_policy.issue_feedback_receipt(
        f"anon:{'a' * 64}", TURN_DIGEST, "cx/gpt-5.4", "none", now=NOW
    )
    assert receipt is not None
    with pytest.raises(feedback_policy.FeedbackUnavailable):
        feedback_policy.consume_feedback_receipt(
            receipt.token,
            f"anon:{'a' * 64}",
            1,
            now=NOW + timedelta(hours=24),
        )


def test_concurrent_same_rating_replay_counts_once(pg_store):
    owner = f"anon:{'a' * 64}"
    receipt = feedback_policy.issue_feedback_receipt(
        owner, TURN_DIGEST, "cx/gpt-5.4", "search", now=NOW
    )
    assert receipt is not None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda _index: feedback_policy.consume_feedback_receipt(
                    receipt.token, owner, 1, now=NOW + timedelta(minutes=1)
                ),
                range(2),
            )
        )

    assert sorted(result.idempotent for result in results) == [False, True]
    with pg_store._conn(commit_on_success=False) as conn:
        row = pg_store._fetchone(
            conn,
            "SELECT positive_count, negative_count FROM feedback_daily_rollups",
            (),
        )
    assert dict(row) == {"positive_count": 1, "negative_count": 0}


def test_conflicting_replay_rejects_and_wrong_owner_is_unavailable(pg_store):
    owner = f"anon:{'a' * 64}"
    receipt = feedback_policy.issue_feedback_receipt(
        owner, TURN_DIGEST, "cx/gpt-5.4", "none", now=NOW
    )
    assert receipt is not None

    feedback_policy.consume_feedback_receipt(receipt.token, owner, 1, now=NOW)
    with pytest.raises(feedback_policy.FeedbackRejected):
        feedback_policy.consume_feedback_receipt(receipt.token, owner, 0, now=NOW)
    with pytest.raises(feedback_policy.FeedbackUnavailable):
        feedback_policy.consume_feedback_receipt(
            receipt.token, f"anon:{'c' * 64}", 1, now=NOW
        )


def test_consumed_row_clears_direct_owner_but_keeps_binding(pg_store):
    user_id = _seed_user(pg_store)
    owner = f"user:{user_id}"
    receipt = feedback_policy.issue_feedback_receipt(
        owner, TURN_DIGEST, "cx/gpt-5.4", "none", now=NOW
    )
    assert receipt is not None
    binding = _receipt_row(pg_store, receipt.token)["owner_binding_digest"]

    feedback_policy.consume_feedback_receipt(receipt.token, owner, 0, now=NOW)
    row = _receipt_row(pg_store, receipt.token)
    assert row["user_id"] is None
    assert row["anonymous_owner_digest"] is None
    assert row["owner_binding_digest"] == binding
    assert row["used_at"] is not None


def test_cleanup_is_bounded_and_idempotent(pg_store):
    owner = f"anon:{'a' * 64}"
    for index in range(3):
        receipt = feedback_policy.issue_feedback_receipt(
            owner,
            f"{index + 1:064x}",
            "cx/gpt-5.4",
            "none",
            now=NOW,
        )
        assert receipt is not None

    cleanup_now = NOW + timedelta(hours=25)
    assert feedback_policy.cleanup_expired_feedback_receipts(
        now=cleanup_now, limit=2
    ) == 2
    assert feedback_policy.cleanup_expired_feedback_receipts(
        now=cleanup_now, limit=2
    ) == 1
    assert feedback_policy.cleanup_expired_feedback_receipts(
        now=cleanup_now, limit=2
    ) == 0


def test_purge_removes_pending_and_consumed_owner_receipts(pg_store):
    owner = f"anon:{'a' * 64}"
    pending = feedback_policy.issue_feedback_receipt(
        owner, "1" * 64, "cx/gpt-5.4", "none", now=NOW
    )
    consumed = feedback_policy.issue_feedback_receipt(
        owner, "2" * 64, "cx/gpt-5.4", "none", now=NOW
    )
    assert pending is not None and consumed is not None
    feedback_policy.consume_feedback_receipt(consumed.token, owner, 1, now=NOW)

    assert feedback_policy.verify_feedback_owner_absent(owner) is False
    assert feedback_policy.purge_feedback_owner(owner) == 2
    assert feedback_policy.verify_feedback_owner_absent(owner) is True


def test_schema_contains_only_bounded_receipt_and_rollup_columns(pg_store):
    with pg_store._conn(commit_on_success=False) as conn:
        receipt_columns = pg_store._fetchall(
            conn,
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'feedback_receipts'
            """,
            (),
        )
        rollup_columns = pg_store._fetchall(
            conn,
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'feedback_daily_rollups'
            """,
            (),
        )

    receipt_names = {row["column_name"] for row in receipt_columns}
    assert not {"query", "reply", "entity_id", "session_id"} & receipt_names
    assert {row["column_name"] for row in rollup_columns} == {
        "day",
        "owner_kind",
        "model_variant",
        "tool_bucket",
        "positive_count",
        "negative_count",
    }
