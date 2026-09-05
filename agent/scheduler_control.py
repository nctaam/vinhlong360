"""Durable scheduler lease and execution receipt primitives.

PostgreSQL owns production coordination. SQLite support is intentionally small
and deterministic for local tests; it is never treated as deployment evidence.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any


class SchedulerLeaseError(RuntimeError):
    """Base error for scheduler lease operations."""


class LeaseNotOwned(SchedulerLeaseError):
    """The lease was replaced or is no longer active."""


@dataclass(frozen=True)
class LeaseClaim:
    acquired: bool
    lease_id: str
    task_name: str
    slot_key: str
    owner_id: str
    lease_until: datetime
    status: str


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _text(value: datetime) -> str:
    return _utc(value).isoformat()


def _parse_time(value: Any) -> datetime:
    if isinstance(value, datetime):
        return _utc(value)
    raw = str(value).replace("Z", "+00:00")
    parsed = datetime.fromisoformat(raw)
    return _utc(parsed)


def _ensure_sqlite_schema(database) -> None:
    if getattr(database, "_use_pg", False):
        return
    with database._conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS scheduler_task_slots (
                task_name TEXT NOT NULL,
                slot_key TEXT NOT NULL,
                owner_id TEXT NOT NULL,
                lease_id TEXT NOT NULL UNIQUE,
                lease_until TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('leased', 'finished')),
                started_at TEXT NOT NULL,
                finished_at TEXT,
                outcome TEXT,
                receipt_json TEXT,
                PRIMARY KEY (task_name, slot_key)
            );
            CREATE INDEX IF NOT EXISTS idx_scheduler_task_slots_lease_until
                ON scheduler_task_slots(lease_until);
            """
        )


def _claim_from_row(database, row, *, acquired: bool) -> LeaseClaim:
    item = database._row_to_dict(row)
    return LeaseClaim(
        acquired=acquired,
        lease_id=str(item["lease_id"]),
        task_name=str(item["task_name"]),
        slot_key=str(item["slot_key"]),
        owner_id=str(item["owner_id"]),
        lease_until=_parse_time(item["lease_until"]),
        status=str(item["status"]),
    )


def claim_task_slot(
    database,
    *,
    task_name: str,
    slot_key: str,
    owner_id: str,
    now: datetime,
    lease_seconds: int,
) -> LeaseClaim:
    """Claim a slot, or return the current owner without running work."""
    if not all(isinstance(value, str) and value.strip() for value in (task_name, slot_key, owner_id)):
        raise ValueError("invalid_scheduler_slot")
    if type(lease_seconds) is not int or lease_seconds < 1:
        raise ValueError("invalid_lease_seconds")
    now = _utc(now)
    lease_until = now + timedelta(seconds=lease_seconds)
    lease_id = str(uuid.uuid4())
    _ensure_sqlite_schema(database)
    ph = database._ph
    with database._conn() as conn:
        if getattr(database, "_use_pg", False):
            sql = f"""
                INSERT INTO scheduler_task_slots
                    (task_name, slot_key, owner_id, lease_id, lease_until, status, started_at)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, 'leased', {ph})
                ON CONFLICT (task_name, slot_key) DO UPDATE
                SET owner_id = EXCLUDED.owner_id,
                    lease_id = EXCLUDED.lease_id,
                    lease_until = EXCLUDED.lease_until,
                    status = 'leased',
                    started_at = EXCLUDED.started_at,
                    finished_at = NULL,
                    outcome = NULL,
                    receipt_json = NULL
                WHERE scheduler_task_slots.status = 'leased'
                  AND scheduler_task_slots.lease_until <= EXCLUDED.started_at
                RETURNING task_name, slot_key, owner_id, lease_id, lease_until, status
            """
            row = database._fetchone(
                conn,
                sql,
                (task_name, slot_key, owner_id, lease_id, lease_until, now),
            )
            if row is not None:
                return _claim_from_row(database, row, acquired=True)
        else:
            insert_cur = database._execute(
                conn,
                f"""
                INSERT OR IGNORE INTO scheduler_task_slots
                    (task_name, slot_key, owner_id, lease_id, lease_until, status, started_at)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, 'leased', {ph})
                """,
                (task_name, slot_key, owner_id, lease_id, _text(lease_until), _text(now)),
            )
            if int(getattr(insert_cur, "rowcount", 0) or 0) != 1:
                database._execute(
                    conn,
                    f"""
                    UPDATE scheduler_task_slots
                    SET owner_id = {ph}, lease_id = {ph}, lease_until = {ph},
                        status = 'leased', started_at = {ph}, finished_at = NULL,
                        outcome = NULL, receipt_json = NULL
                    WHERE task_name = {ph} AND slot_key = {ph}
                      AND status = 'leased' AND lease_until <= {ph}
                    """,
                    (owner_id, lease_id, _text(lease_until), _text(now), task_name, slot_key, _text(now)),
                )
        row = database._fetchone(
            conn,
            f"""
            SELECT task_name, slot_key, owner_id, lease_id, lease_until, status
            FROM scheduler_task_slots
            WHERE task_name = {ph} AND slot_key = {ph}
            """,
            (task_name, slot_key),
        )
        if row is None:
            raise SchedulerLeaseError("scheduler_claim_missing")
        acquired = str(database._row_to_dict(row)["lease_id"]) == lease_id
        return _claim_from_row(database, row, acquired=acquired)


def finish_task_slot(
    database,
    *,
    lease_id: str,
    outcome: str,
    finished_at: datetime,
    receipt: dict[str, Any],
) -> None:
    """Finish only the currently-owned lease and persist its receipt."""
    if not isinstance(lease_id, str) or not lease_id.strip():
        raise ValueError("invalid_lease_id")
    if not isinstance(outcome, str) or not outcome.strip():
        raise ValueError("invalid_outcome")
    if not isinstance(receipt, dict):
        raise ValueError("invalid_receipt")
    _ensure_sqlite_schema(database)
    ph = database._ph
    finished_at = _utc(finished_at)
    receipt_json = json.dumps(receipt, ensure_ascii=True, sort_keys=True, default=str)
    with database._conn() as conn:
        cur = database._execute(
            conn,
            f"""
            UPDATE scheduler_task_slots
            SET status = 'finished', finished_at = {ph}, outcome = {ph}, receipt_json = {ph}
            WHERE lease_id = {ph} AND status = 'leased'
            """,
            (finished_at if getattr(database, "_use_pg", False) else _text(finished_at), outcome.strip(), receipt_json, lease_id),
        )
        if int(getattr(cur, "rowcount", 0) or 0) != 1:
            raise LeaseNotOwned("scheduler_lease_not_owned")


__all__ = [
    "LeaseClaim",
    "LeaseNotOwned",
    "SchedulerLeaseError",
    "claim_task_slot",
    "finish_task_slot",
]
