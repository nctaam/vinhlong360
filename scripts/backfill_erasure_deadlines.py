#!/usr/bin/env python3
"""Report or explicitly backfill missing account-erasure deadlines."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGENT_DIR = ROOT / "agent"
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

from config import settings  # noqa: E402
from database import db  # noqa: E402


UTC = timezone.utc


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _as_utc(value):
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _rows(db_obj):
    with db_obj._conn(commit_on_success=False) as conn:
        return db_obj._fetchall(
            conn,
            """
            SELECT id::text AS id, deleted_at
            FROM users
            WHERE deleted_at IS NOT NULL AND erasure_due_at IS NULL
            ORDER BY deleted_at, id
            """,
            (),
        )


def build_backfill_report(*, now: datetime | None = None, db_obj=None) -> dict:
    """Compute impact from stored deletion timestamps without writing state."""
    del now  # The projection is based on stored deleted_at, not a rolling TTL.
    database = db_obj or db
    if not getattr(database, "_use_pg", True):
        return {
            "legacy_missing_deadline_count": 0,
            "earliest_due_at": None,
            "latest_due_at": None,
            "error_code": "DB_CONSTRAINT",
        }
    try:
        rows = [database._row_to_dict(row) for row in _rows(database)]
    except Exception:
        return {
            "legacy_missing_deadline_count": 0,
            "earliest_due_at": None,
            "latest_due_at": None,
            "error_code": "DB_CONSTRAINT",
        }
    deadlines = [
        _as_utc(row["deleted_at"])
        + timedelta(days=settings.ACCOUNT_ERASURE_DEADLINE_DAYS)
        for row in rows
    ]
    return {
        "legacy_missing_deadline_count": len(deadlines),
        "earliest_due_at": min(deadlines).isoformat() if deadlines else None,
        "latest_due_at": max(deadlines).isoformat() if deadlines else None,
    }


def _backup_evidence(path: str | None) -> bool:
    return bool(path) and Path(path).is_file()


def _apply_backfill(db_obj) -> int:
    rows = [db_obj._row_to_dict(row) for row in _rows(db_obj)]
    with db_obj._conn() as conn:
        for row in rows:
            deleted_at = _as_utc(row["deleted_at"])
            due_at = deleted_at + timedelta(
                days=settings.ACCOUNT_ERASURE_DEADLINE_DAYS
            )
            db_obj._execute(
                conn,
                """
                UPDATE users
                SET erasure_due_at = %s
                WHERE id::text = %s
                  AND deleted_at IS NOT NULL
                  AND erasure_due_at IS NULL
                """,
                (due_at, str(row["id"])),
            )
    return len(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--backup-evidence", help="path to a completed backup manifest")
    args = parser.parse_args(argv)

    if not args.apply:
        print(json.dumps(build_backfill_report(now=_utc_now()), sort_keys=True))
        return 0
    if not _backup_evidence(args.backup_evidence):
        print("[backfill] --apply requires --backup-evidence pointing to a file", file=sys.stderr)
        return 2
    if not getattr(db, "_use_pg", True):
        print("[backfill] PostgreSQL is required", file=sys.stderr)
        return 1
    if hasattr(db, "initialize"):
        db.initialize()
    try:
        changed = _apply_backfill(db)
    except Exception:
        print("[backfill] DB_CONSTRAINT", file=sys.stderr)
        return 1
    print(json.dumps({"applied_count": changed}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
