"""Small, database-backed concurrency primitives for community state.

The helpers deliberately accept the existing ``CaseTransaction`` shape (``_db``
and ``_conn``) as well as the light-weight transaction objects used by tests.
They keep state changes in the caller's transaction so an audit or notification
can be registered only after the compare-and-set has committed.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException


_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class StateConflict(HTTPException):
    """Deterministic HTTP 409 raised when a state CAS loses the race."""

    def __init__(self, detail: str = "state_conflict") -> None:
        super().__init__(status_code=409, detail=detail)
        self.code = detail


@dataclass(frozen=True)
class IdempotencyKey:
    command: str
    actor_id: str
    key: str

    def __post_init__(self) -> None:
        if not all(isinstance(value, str) and value.strip() for value in (self.command, self.actor_id, self.key)):
            raise ValueError("invalid_idempotency_key")

    @property
    def storage_key(self) -> str:
        return f"{self.command.strip()}:{self.actor_id.strip()}:{self.key.strip()}"


@dataclass(frozen=True)
class ClaimResult:
    key: str
    claimed: bool
    replayed: bool = False
    conflict: bool = False
    request_hash: str | None = None
    receipt: Any = None

    @property
    def is_replay(self) -> bool:
        return self.replayed

    @property
    def is_conflict(self) -> bool:
        return self.conflict


@dataclass(frozen=True)
class TransitionResult:
    table: str
    row_id: str
    old_status: str
    new_status: str
    revision: int
    actor_id: str
    reason: str
    correlation_id: str

    @property
    def status(self) -> str:
        return self.new_status


@dataclass(frozen=True)
class Lease:
    table: str
    row_id: str
    worker_id: str
    claim_expires_at: datetime
    revision: int
    status: str | None = None

    @property
    def id(self) -> str:
        return self.row_id

    @property
    def expires_at(self) -> datetime:
        return self.claim_expires_at


def _ctx(transaction):
    db = getattr(transaction, "_db", None)
    conn = getattr(transaction, "_conn", None)
    if db is None or conn is None:
        raise ValueError("invalid_transaction")
    return db, conn


def _table_name(table: str) -> str:
    if not isinstance(table, str) or not _IDENTIFIER.fullmatch(table):
        raise ValueError("invalid_table")
    return table


def _row_value(row, name: str, index: int = 0):
    if row is None:
        return None
    if isinstance(row, dict):
        return row.get(name)
    try:
        return row[name]
    except (IndexError, KeyError, TypeError):
        return row[index]


def _column_names(db, conn, table: str) -> set[str]:
    if getattr(db, "_use_pg", False):
        rows = db._fetchall(conn, "SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name=%s", (table,))
        return {str(_row_value(row, "column_name")) for row in rows}
    rows = db._fetchall(conn, f"PRAGMA table_info({table})", ())
    return {str(_row_value(row, "name", 1)) for row in rows}


def ensure_state_schema(transaction, table: str = "posts") -> None:
    """Add lease/revision fields without requiring a destructive migration."""
    table = _table_name(table)
    db, conn = _ctx(transaction)
    columns = _column_names(db, conn, table)
    additions = {
        "revision": "BIGINT NOT NULL DEFAULT 1" if getattr(db, "_use_pg", False) else "INTEGER NOT NULL DEFAULT 1",
        "claimed_by": "TEXT",
        "claim_expires_at": "TIMESTAMPTZ" if getattr(db, "_use_pg", False) else "TEXT",
        "publish_attempts": "INTEGER NOT NULL DEFAULT 0",
        "last_error_code": "TEXT",
    }
    for name, definition in additions.items():
        if name not in columns:
            ddl = f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {name} {definition}" if getattr(db, "_use_pg", False) else f"ALTER TABLE {table} ADD COLUMN {name} {definition}"
            try:
                db._execute(conn, ddl, ())
            except Exception:
                # Another worker may have added the same column between the
                # information-schema read and this DDL statement.
                if not getattr(db, "_use_pg", False):
                    raise
    if getattr(db, "_use_pg", False) and table == "posts":
        # Older deployments constrain moderation_status to the original four states.
        # Extend that check additively so a visible publish_failed state is durable.
        rows = db._fetchall(conn, "SELECT conname FROM pg_constraint WHERE conrelid='posts'::regclass AND contype='c' AND pg_get_constraintdef(oid) ILIKE %s", ("%moderation_status%",))
        for row in rows:
            name = _row_value(row, "conname")
            if name:
                db._execute(conn, f"ALTER TABLE posts DROP CONSTRAINT IF EXISTS {_table_name(str(name))}", ())
        exists = db._fetchone(conn, "SELECT 1 FROM pg_constraint WHERE conname='posts_moderation_status_check' AND conrelid='posts'::regclass", ())
        if exists is None:
            db._execute(conn, "ALTER TABLE posts ADD CONSTRAINT posts_moderation_status_check CHECK (moderation_status IN ('pending','approved','rejected','flagged','publish_failed'))", ())


def _idempotency_storage_key(key: IdempotencyKey | str) -> str:
    if isinstance(key, IdempotencyKey):
        return key.storage_key
    if not isinstance(key, str) or not key.strip():
        raise ValueError("invalid_idempotency_key")
    return key.strip()


def _decode_meta(value) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
            return decoded if isinstance(decoded, dict) else {}
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}
    return {}


def claim_idempotency(transaction, key: IdempotencyKey | str, request_hash: str) -> ClaimResult:
    """Atomically claim a command key, replaying exact retries and rejecting reuse."""
    if not isinstance(request_hash, str) or not request_hash.strip():
        raise ValueError("invalid_request_hash")
    db, conn = _ctx(transaction)
    storage_key = _idempotency_storage_key(key)
    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=24)
    if getattr(db, "_use_pg", False):
        row = db._fetchone(conn, "INSERT INTO request_idempotency_keys(key, expires_at, meta) VALUES (%s,%s,%s::jsonb) ON CONFLICT (key) DO NOTHING RETURNING key", (storage_key, expires, json.dumps({"request_hash": request_hash})))
        if row is not None:
            return ClaimResult(storage_key, claimed=True, request_hash=request_hash)
        row = db._fetchone(conn, "SELECT expires_at, meta FROM request_idempotency_keys WHERE key=%s FOR UPDATE", (storage_key,))
    else:
        row = db._fetchone(conn, "SELECT expires_at, meta FROM request_idempotency_keys WHERE key=?", (storage_key,))
        if row is None:
            db._execute(conn, "INSERT INTO request_idempotency_keys(key, first_seen_at, expires_at, meta) VALUES (?,?,?,?)", (storage_key, now.isoformat(), expires.isoformat(), json.dumps({"request_hash": request_hash})))
            return ClaimResult(storage_key, claimed=True, request_hash=request_hash)
    if row is None:
        return ClaimResult(storage_key, claimed=True, request_hash=request_hash)
    expiry = _row_value(row, "expires_at")
    if isinstance(expiry, str):
        try:
            expiry = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
        except ValueError:
            expiry = now
    if expiry is not None and getattr(expiry, "tzinfo", None) is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    if expiry is not None and expiry <= now:
        meta = json.dumps({"request_hash": request_hash})
        values = (expires, meta, storage_key) if getattr(db, "_use_pg", False) else (expires.isoformat(), meta, storage_key)
        db._execute(conn, "UPDATE request_idempotency_keys SET expires_at=%s, meta=%s::jsonb WHERE key=%s" if getattr(db, "_use_pg", False) else "UPDATE request_idempotency_keys SET expires_at=?, meta=? WHERE key=?", values)
        return ClaimResult(storage_key, claimed=True, request_hash=request_hash)
    meta = _decode_meta(_row_value(row, "meta"))
    previous = meta.get("request_hash")
    receipt = meta.get("receipt")
    if previous == request_hash:
        return ClaimResult(storage_key, claimed=False, replayed=True, request_hash=previous, receipt=receipt)
    return ClaimResult(storage_key, claimed=False, conflict=True, request_hash=previous, receipt=receipt)


def record_idempotency_receipt(transaction, claim: ClaimResult, receipt: Any) -> None:
    """Attach a JSON-serialisable response so an exact retry can replay it."""
    if not isinstance(claim, ClaimResult) or not claim.claimed:
        raise ValueError("invalid_idempotency_claim")
    db, conn = _ctx(transaction)
    meta = json.dumps({"request_hash": claim.request_hash, "receipt": receipt})
    sql = "UPDATE request_idempotency_keys SET meta=%s::jsonb WHERE key=%s" if getattr(db, "_use_pg", False) else "UPDATE request_idempotency_keys SET meta=? WHERE key=?"
    db._execute(conn, sql, (meta, claim.key))


def _status_column(db, conn, table: str) -> str:
    columns = _column_names(db, conn, table)
    if "moderation_status" in columns:
        return "moderation_status"
    if "status" in columns:
        return "status"
    raise ValueError("state_status_column_missing")


def cas_transition(transaction, table: str, row_id: str, *, expected_status: str,
                   new_status: str, actor_id: str, reason: str,
                   correlation_id: str) -> TransitionResult:
    """Transition one row with a status + revision compare-and-set."""
    table = _table_name(table)
    if not all(isinstance(value, str) and value for value in (row_id, expected_status, new_status, actor_id, reason, correlation_id)):
        raise ValueError("invalid_transition")
    db, conn = _ctx(transaction)
    ensure_state_schema(transaction, table)
    status_col = _status_column(db, conn, table)
    id_col = "id"
    if "case_id" in _column_names(db, conn, table):
        id_col = "case_id"
    lock = " FOR UPDATE" if getattr(db, "_use_pg", False) else ""
    id_expr = f"{id_col}::text" if getattr(db, "_use_pg", False) else id_col
    row = db._fetchone(conn, f"SELECT {status_col} AS state_status, revision FROM {table} WHERE {id_expr} = {db._ph}{lock}", (row_id,))
    if row is None:
        raise StateConflict()
    old = str(_row_value(row, "state_status"))
    revision = int(_row_value(row, "revision") or 1)
    if old != expected_status:
        raise StateConflict()
    updated = db._fetchone(conn, f"UPDATE {table} SET {status_col}={db._ph}, revision=revision+1 WHERE {id_expr}={db._ph} AND {status_col}={db._ph} AND revision={db._ph} RETURNING {id_col} AS row_id, {status_col} AS state_status, revision", (new_status, row_id, expected_status, revision))
    if updated is None:
        raise StateConflict()
    return TransitionResult(table, str(_row_value(updated, "row_id")), old, new_status, int(_row_value(updated, "revision") or revision + 1), actor_id, reason, correlation_id)


def claim_due(transaction, table: str, *, due_before: datetime, worker_id: str,
              lease_seconds: int) -> Lease | None:
    """Claim one due row; PostgreSQL uses SKIP LOCKED for multi-worker safety."""
    table = _table_name(table)
    if not isinstance(due_before, datetime) or due_before.tzinfo is None or not isinstance(worker_id, str) or not worker_id or lease_seconds <= 0:
        raise ValueError("invalid_due_claim")
    db, conn = _ctx(transaction)
    ensure_state_schema(transaction, table)
    columns = _column_names(db, conn, table)
    if "scheduled_at" not in columns:
        raise ValueError("scheduled_at_column_missing")
    id_col = "id" if "id" in columns else "case_id"
    status_col = "moderation_status" if "moderation_status" in columns else ("status" if "status" in columns else None)
    status_expr = f", target.{status_col} AS state_status" if status_col else ""
    expires = due_before + timedelta(seconds=lease_seconds)
    ph = db._ph
    if getattr(db, "_use_pg", False):
        row = db._fetchone(conn, f"WITH candidate AS (SELECT {id_col} FROM {table} WHERE scheduled_at IS NOT NULL AND scheduled_at <= {ph} AND (claim_expires_at IS NULL OR claim_expires_at <= {ph}) ORDER BY scheduled_at, {id_col} LIMIT 1 FOR UPDATE SKIP LOCKED) UPDATE {table} AS target SET claimed_by={ph}, claim_expires_at={ph}, revision=target.revision+1 FROM candidate WHERE target.{id_col}=candidate.{id_col} RETURNING target.{id_col} AS row_id, target.revision{status_expr}", (due_before, due_before, worker_id, expires))
    else:
        sqlite_status_expr = f", {status_col} AS state_status" if status_col else ""
        row = db._fetchone(conn, f"UPDATE {table} SET claimed_by={ph}, claim_expires_at={ph}, revision=revision+1 WHERE {id_col} = (SELECT {id_col} FROM {table} WHERE scheduled_at IS NOT NULL AND scheduled_at <= {ph} AND (claim_expires_at IS NULL OR claim_expires_at <= {ph}) ORDER BY scheduled_at, {id_col} LIMIT 1) RETURNING {id_col} AS row_id, revision{sqlite_status_expr}", (worker_id, expires.isoformat(), due_before.isoformat(), due_before.isoformat()))
    if row is None:
        return None
    status = _row_value(row, status_col) if status_col else None
    return Lease(table, str(_row_value(row, "row_id")), worker_id, expires, int(_row_value(row, "revision") or 1), status)
