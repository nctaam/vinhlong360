from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest


UTC = timezone.utc


class _SqliteDatabase:
    _use_pg = False
    _ph = "?"

    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
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
        return {"status": "approved"}

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
