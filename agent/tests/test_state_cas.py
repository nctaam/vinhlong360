from __future__ import annotations

import asyncio
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest


UTC = timezone.utc


class _SqliteDatabase:
    _use_pg = False
    _ph = "?"

    def __init__(self):
        self.conn = sqlite3.connect(":memory:", check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            "CREATE TABLE posts (id TEXT PRIMARY KEY, status TEXT, moderation_status TEXT, user_id TEXT, content TEXT, images TEXT, revision INTEGER NOT NULL DEFAULT 1, scheduled_at TEXT, claimed_by TEXT, claim_expires_at TEXT, publish_attempts INTEGER NOT NULL DEFAULT 0, last_error_code TEXT, updated_at TEXT)"
        )
        self.conn.execute(
            "CREATE TABLE request_idempotency_keys (key TEXT PRIMARY KEY, first_seen_at TEXT NOT NULL, expires_at TEXT NOT NULL, meta TEXT)"
        )

    def _conn(self, **_):
        class _Context:
            def __init__(self, outer):
                self.outer = outer

            def __enter__(self):
                return self.outer.conn

            def __exit__(self, *_):
                self.outer.conn.commit()

        return _Context(self)

    def _execute(self, conn, sql, params=()):
        return conn.execute(sql.replace("%s", "?"), params)

    def _fetchone(self, conn, sql, params=()):
        return self._execute(conn, sql, params).fetchone()

    def _fetchall(self, conn, sql, params=()):
        return self._execute(conn, sql, params).fetchall()

    def _row_to_dict(self, row):
        return dict(row) if row is not None else None


class _Tx:
    def __init__(self, db):
        self._db = db
        self._conn = db.conn


def test_idempotency_exact_retry_replays_and_hash_mismatch_conflicts():
    from control_plane.concurrency import IdempotencyKey, claim_idempotency

    db = _SqliteDatabase()
    tx = _Tx(db)
    key = IdempotencyKey("moderate", "actor-1", "request-1")
    first = claim_idempotency(tx, key, "hash-a")
    retry = claim_idempotency(tx, key, "hash-a")
    mismatch = claim_idempotency(tx, key, "hash-b")

    assert first.claimed is True
    assert retry.replayed is True
    assert retry.conflict is False
    assert mismatch.conflict is True


def test_cas_transition_is_single_winner_and_returns_deterministic_conflict():
    from control_plane.concurrency import StateConflict, cas_transition

    db = _SqliteDatabase()
    db.conn.execute("INSERT INTO posts(id, moderation_status) VALUES ('post-1', 'pending')")
    tx = _Tx(db)
    result = cas_transition(
        tx,
        "posts",
        "post-1",
        expected_status="pending",
        new_status="approved",
        actor_id="mod-1",
        reason="safe",
        correlation_id="corr-1",
    )
    assert result.new_status == "approved"
    with pytest.raises(StateConflict) as exc:
        cas_transition(
            tx,
            "posts",
            "post-1",
            expected_status="pending",
            new_status="rejected",
            actor_id="mod-2",
            reason="unsafe",
            correlation_id="corr-2",
        )
    assert exc.value.status_code == 409
    assert str(exc.value.detail) == "state_conflict"


def test_due_claim_is_leased_once_until_expiry():
    from control_plane.concurrency import claim_due

    db = _SqliteDatabase()
    due = datetime.now(UTC) - timedelta(minutes=1)
    db.conn.execute(
        "INSERT INTO posts(id, moderation_status, scheduled_at) VALUES ('post-1', 'pending', ?)",
        (due.isoformat(),),
    )
    tx = _Tx(db)
    first = claim_due(tx, "posts", due_before=datetime.now(UTC), worker_id="w1", lease_seconds=60)
    second = claim_due(tx, "posts", due_before=datetime.now(UTC), worker_id="w2", lease_seconds=60)

    assert first is not None
    assert second is None
    assert first.worker_id == "w1"


def test_publish_due_posts_rechecks_moderation_and_clears_lease(monkeypatch):
    import database
    import scheduler

    db = _SqliteDatabase()
    due = datetime.now(UTC) - timedelta(minutes=1)
    db.conn.execute(
        "INSERT INTO posts(id, user_id, content, images, moderation_status, scheduled_at) VALUES ('post-1', 'user-1', 'A scheduled post', '[]', 'pending', ?)",
        (due.isoformat(),),
    )
    monkeypatch.setattr(database, "db", db)

    async def approve(*_args, **_kwargs):
        return {"status": "approved", "moderation_available": True}

    monkeypatch.setattr("moderation.moderate_content_enhanced", approve)
    monkeypatch.setattr("admin_common._log_mod_action", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("notifications.create_notification", lambda *_args, **_kwargs: None)

    result = scheduler.task_publish_due_posts(now=datetime.now(UTC), worker_id="worker-1", limit=1)
    row = db.conn.execute("SELECT moderation_status, scheduled_at, claimed_by, publish_attempts FROM posts WHERE id='post-1'").fetchone()

    assert result.published == 1
    assert row["moderation_status"] == "approved"
    assert row["scheduled_at"] is None
    assert row["claimed_by"] is None


def test_publish_failure_remains_visible_with_retry_metadata(monkeypatch):
    import database
    import scheduler

    db = _SqliteDatabase()
    due = datetime.now(UTC) - timedelta(minutes=1)
    db.conn.execute(
        "INSERT INTO posts(id, user_id, content, images, moderation_status, scheduled_at) VALUES ('post-2', 'user-2', 'Another scheduled post', '[]', 'pending', ?)",
        (due.isoformat(),),
    )
    monkeypatch.setattr(database, "db", db)

    async def fail(*_args, **_kwargs):
        raise RuntimeError("provider_down")

    monkeypatch.setattr("moderation.moderate_content_enhanced", fail)
    result = scheduler.task_publish_due_posts(now=datetime.now(UTC), worker_id="worker-2", limit=1)
    row = db.conn.execute("SELECT moderation_status, scheduled_at, publish_attempts, last_error_code FROM posts WHERE id='post-2'").fetchone()

    assert result.failed == 1
    assert row["moderation_status"] == "publish_failed"
    assert row["scheduled_at"] is not None
    assert row["publish_attempts"] == 1
    assert row["last_error_code"] == "RuntimeError"


def test_pending_unavailable_moderation_does_not_reject(monkeypatch):
    import database
    import scheduler
    db = _SqliteDatabase()
    due = datetime.now(UTC) - timedelta(minutes=1)
    db.conn.execute("INSERT INTO posts(id, user_id, content, images, moderation_status, scheduled_at) VALUES ('post-3','user-3','Pending provider','[]','pending',?)", (due.isoformat(),))
    monkeypatch.setattr(database, "db", db)
    async def unavailable(*_args, **_kwargs):
        return {"status": "pending", "moderation_available": False}
    monkeypatch.setattr("moderation.moderate_content_enhanced", unavailable)
    result = scheduler.task_publish_due_posts(now=datetime.now(UTC), worker_id="worker-3", limit=1)
    row = db.conn.execute("SELECT moderation_status, scheduled_at, publish_attempts FROM posts WHERE id='post-3'").fetchone()
    assert result.failed == 1
    assert row["moderation_status"] == "publish_failed"
    assert row["scheduled_at"] is not None


def test_due_claim_skips_draft_and_non_pending_rows():
    from control_plane.concurrency import claim_due
    db = _SqliteDatabase()
    due = datetime.now(UTC) - timedelta(minutes=1)
    db.conn.execute("INSERT INTO posts(id, moderation_status, scheduled_at) VALUES ('draft','approved',?)", (due.isoformat(),))
    db.conn.execute("INSERT INTO posts(id, moderation_status, scheduled_at) VALUES ('pending','pending',?)", (due.isoformat(),))
    tx = _Tx(db)
    lease = claim_due(tx, "posts", due_before=datetime.now(UTC), worker_id="w", lease_seconds=60)
    assert lease is not None and lease.row_id == "pending"


def test_production_alias_prd_fails_closed(monkeypatch):
    import ratelimit
    monkeypatch.setenv("ENVIRONMENT", "prd")
    monkeypatch.setattr(ratelimit, "_check_rate_pg", lambda *_args, **_kwargs: False)
    with pytest.raises(Exception) as exc:
        ratelimit.check_rate("prd-key", 10, 60)
    assert getattr(exc.value, "status_code", None) == 503


def test_community_create_post_uses_shared_idempotency_claim():
    from pathlib import Path
    source = (Path(__file__).parents[1] / "community" / "api.py").read_text(encoding="utf-8")
    block = source[source.index("async def create_post"):source.index("# ── Draft Posts ──")]
    assert "_community_idempotency(" in block
    assert "_community_idempotency_record" in block
    assert "require_idempotency" not in block


def test_pg_schema_verification_never_runs_hot_path_ddl():
    from control_plane.concurrency import ensure_state_schema

    class PgProbe:
        _use_pg = True
        _ph = "%s"

        def __init__(self):
            self.statements = []

        def _fetchall(self, _conn, sql, _params=()):
            self.statements.append(sql)
            if "information_schema.columns" in sql:
                return [{"column_name": name} for name in (
                    "revision", "claimed_by", "claim_expires_at",
                    "publish_attempts", "last_error_code",
                )]
            return [{"conname": "posts_moderation_status_check"}]

        def _fetchone(self, _conn, sql, _params=()):
            self.statements.append(sql)
            return {"definition": "CHECK (moderation_status IN ('pending','approved','rejected','flagged','publish_failed'))"}

        def _execute(self, _conn, sql, _params=()):
            self.statements.append(sql)
            raise AssertionError("schema verification attempted DDL")

    db = PgProbe()
    tx = type("Tx", (), {"_db": db, "_conn": object()})()
    ensure_state_schema(tx, "posts")
    assert not any("ALTER TABLE" in sql for sql in db.statements)


def test_pg_appeal_schema_verification_requires_only_appeal_columns():
    from control_plane.concurrency import ensure_state_schema

    class PgAppealProbe:
        _use_pg = True

        def _fetchall(self, _conn, _sql, _params=()):
            return [{"column_name": name} for name in (
                "revision", "claimed_by", "claim_expires_at", "last_error_code",
            )]

        def _execute(self, _conn, _sql, _params=()):
            raise AssertionError("schema verification attempted DDL")

    db = PgAppealProbe()
    tx = type("Tx", (), {"_db": db, "_conn": object()})()
    ensure_state_schema(tx, "moderation_appeals")


def test_sqlite_schema_adds_only_missing_compatibility_columns():
    from control_plane.concurrency import ensure_state_schema

    db = _SqliteDatabase()
    db.conn.execute("ALTER TABLE posts DROP COLUMN publish_attempts")
    tx = _Tx(db)
    ensure_state_schema(tx, "posts")
    columns = {row[1] for row in db.conn.execute("PRAGMA table_info(posts)")}
    assert "publish_attempts" in columns


def test_due_claim_without_status_column_returns_lease_with_no_status():
    from control_plane.concurrency import claim_due

    db = _SqliteDatabase()
    db.conn.execute("CREATE TABLE queue (id TEXT PRIMARY KEY, scheduled_at TEXT, claimed_by TEXT, claim_expires_at TEXT, revision INTEGER NOT NULL DEFAULT 1)")
    db.conn.execute("INSERT INTO queue(id, scheduled_at) VALUES ('q-1', ?)", ((datetime.now(UTC) - timedelta(minutes=1)).isoformat(),))
    lease = claim_due(_Tx(db), "queue", due_before=datetime.now(UTC), worker_id="w", lease_seconds=60)
    assert lease is not None and lease.status is None


def test_idempotency_pending_retry_returns_in_progress_without_duplicate(monkeypatch):
    from fastapi import HTTPException, Request
    from community import api as community_api

    db = _SqliteDatabase()
    monkeypatch.setattr(community_api, "db", db)
    request = Request({"type": "http", "headers": [(b"idempotency-key", b"retry-1")]})
    user = {"id": "user-1"}
    claim, replay = community_api._community_idempotency(request, user, "create_post", {"content": "atomic"})
    assert claim.claimed is True and replay is None
    db.conn.execute("INSERT INTO posts(id, moderation_status) VALUES ('post-atomic', 'pending')")
    with pytest.raises(HTTPException) as exc:
        community_api._community_idempotency(request, user, "create_post", {"content": "atomic"})
    assert exc.value.status_code == 409
    assert exc.value.detail == "idempotency_in_progress"
    assert db.conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0] == 1


def test_create_post_crash_after_insert_returns_in_progress_without_second_insert(monkeypatch):
    from fastapi import HTTPException, Request
    from community import api as community_api

    db = _SqliteDatabase()
    monkeypatch.setattr(community_api, "db", db)
    monkeypatch.setattr(community_api, "check_rate", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(community_api, "_post_dup_exists", lambda *_args, **_kwargs: False)
    request = Request({"type": "http", "headers": [(b"idempotency-key", b"crash-after-insert")]})
    user = {"id": "user-atomic", "display_name": "Atomic"}
    inserts = []

    async def approve(*_args, **_kwargs):
        return {"status": "approved", "moderation_available": True}

    def insert_then_crash(*_args, **_kwargs):
        db.conn.execute("INSERT INTO posts(id, moderation_status) VALUES ('post-crash', 'approved')")
        inserts.append("post-crash")
        raise RuntimeError("crash_after_insert_before_receipt")

    monkeypatch.setattr(community_api, "moderate_content_enhanced", approve)
    monkeypatch.setattr(community_api, "_post_insert", insert_then_crash)
    body = community_api.CreatePost(content="An atomicity regression post")

    with pytest.raises(RuntimeError, match="crash_after_insert_before_receipt"):
        asyncio.run(community_api.create_post(body, request=request, user=user))
    with pytest.raises(HTTPException) as exc:
        asyncio.run(community_api.create_post(body, request=request, user=user))

    assert exc.value.status_code == 409
    assert exc.value.detail == "idempotency_in_progress"
    assert inserts == ["post-crash"]
    assert db.conn.execute("SELECT COUNT(*) FROM posts WHERE id='post-crash'").fetchone()[0] == 1


def test_scheduler_missing_moderation_availability_fails_closed(monkeypatch):
    import database
    import scheduler

    db = _SqliteDatabase()
    due = datetime.now(UTC) - timedelta(minutes=1)
    db.conn.execute(
        "INSERT INTO posts(id, user_id, content, images, moderation_status, scheduled_at) VALUES ('post-missing-availability','user-4','Missing flag','[]','pending',?)",
        (due.isoformat(),),
    )
    monkeypatch.setattr(database, "db", db)

    async def malformed(*_args, **_kwargs):
        return {"status": "approved"}

    monkeypatch.setattr("moderation.moderate_content_enhanced", malformed)
    result = scheduler.task_publish_due_posts(now=datetime.now(UTC), worker_id="worker-missing", limit=1)
    row = db.conn.execute("SELECT moderation_status, scheduled_at FROM posts WHERE id='post-missing-availability'").fetchone()
    assert result.failed == 1
    assert row["moderation_status"] == "publish_failed"
    assert row["scheduled_at"] is not None


def test_due_claim_lease_expiry_uses_current_time_not_due_cutoff():
    from control_plane.concurrency import claim_due

    db = _SqliteDatabase()
    due = datetime(2020, 1, 1, tzinfo=UTC)
    db.conn.execute(
        "INSERT INTO posts(id, moderation_status, scheduled_at) VALUES ('post-now', 'pending', ?)",
        (due.isoformat(),),
    )
    lease = claim_due(_Tx(db), "posts", due_before=due, worker_id="w-now", lease_seconds=60)
    assert lease is not None
    assert lease.claim_expires_at > datetime.now(UTC) - timedelta(seconds=5)


def test_due_claim_reclaims_expired_lease_using_actual_now():
    from control_plane.concurrency import claim_due

    db = _SqliteDatabase()
    stale_schedule = datetime(2020, 1, 1, tzinfo=UTC)
    expired_lease = datetime.now(UTC) - timedelta(minutes=1)
    db.conn.execute(
        "INSERT INTO posts(id, moderation_status, scheduled_at, claimed_by, claim_expires_at) VALUES ('post-expired', 'pending', ?, 'old-worker', ?)",
        (stale_schedule.isoformat(), expired_lease.isoformat()),
    )
    worker_now = datetime.now(UTC)
    lease = claim_due(
        _Tx(db), "posts", due_before=stale_schedule,
        worker_id="new-worker", lease_seconds=60, now=worker_now,
    )
    assert lease is not None
    assert lease.worker_id == "new-worker"
    assert lease.claim_expires_at == worker_now + timedelta(seconds=60)


def test_publish_failed_post_is_automatically_retryable(monkeypatch):
    import database
    import scheduler

    db = _SqliteDatabase()
    due = datetime.now(UTC) - timedelta(minutes=1)
    db.conn.execute(
        "INSERT INTO posts(id, user_id, content, images, moderation_status, scheduled_at) VALUES ('post-retry','user-5','Retry me','[]','publish_failed',?)",
        (due.isoformat(),),
    )
    monkeypatch.setattr(database, "db", db)

    async def approve(*_args, **_kwargs):
        return {"status": "approved", "moderation_available": True}

    monkeypatch.setattr("moderation.moderate_content_enhanced", approve)
    monkeypatch.setattr("admin_common._log_mod_action", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("notifications.create_notification", lambda *_args, **_kwargs: None)
    result = scheduler.task_publish_due_posts(now=datetime.now(UTC), worker_id="worker-retry", limit=1)
    row = db.conn.execute("SELECT moderation_status, scheduled_at FROM posts WHERE id='post-retry'").fetchone()
    assert result.published == 1
    assert row["moderation_status"] == "approved"
    assert row["scheduled_at"] is None


def test_failed_due_rows_back_off_so_batch_does_not_starve_other_posts(monkeypatch):
    import database
    import scheduler

    db = _SqliteDatabase()
    due = datetime.now(UTC) - timedelta(minutes=1)
    for post_id in ("post-fail-first", "post-fail-second"):
        db.conn.execute(
            "INSERT INTO posts(id, user_id, content, images, moderation_status, scheduled_at) VALUES (?, 'user-batch', 'Retry batch', '[]', 'pending', ?)",
            (post_id, due.isoformat()),
        )
    monkeypatch.setattr(database, "db", db)

    async def unavailable(*_args, **_kwargs):
        return {"status": "pending", "moderation_available": False}

    monkeypatch.setattr("moderation.moderate_content_enhanced", unavailable)
    result = scheduler.task_publish_due_posts(now=datetime.now(UTC), worker_id="worker-batch", limit=2)
    rows = db.conn.execute("SELECT id, moderation_status, scheduled_at, publish_attempts FROM posts ORDER BY id").fetchall()
    assert result.claimed == 2
    assert result.failed == 2
    assert [row["moderation_status"] for row in rows] == ["publish_failed", "publish_failed"]
    assert all(row["scheduled_at"] is not None for row in rows)
    assert all(row["publish_attempts"] == 1 for row in rows)
