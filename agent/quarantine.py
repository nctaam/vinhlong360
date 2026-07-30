"""Immediate account quarantine and grace-period recovery boundaries."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from config import settings
from data_lifecycle import lifecycle_registry
from database import db
from erasure_state import ERASURE_ERROR_CODES
from owner_write_gate import owner_key_for_user, owner_write_gate


UTC = timezone.utc
_MAX_RETRY_BATCH = 50
_DB_ERROR = "DB_CONSTRAINT"
_STORE_ERROR = "STORE_UNAVAILABLE"


def _utc_aware(value: datetime, *, label: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError(f"{label} must be UTC-aware")
    return value.astimezone(UTC)


def _timestamp(value):
    if value is None:
        return None
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _error_code(value: str | None, *, fallback: str = _STORE_ERROR) -> str:
    return value if value in ERASURE_ERROR_CODES else fallback


@dataclass(frozen=True)
class QuarantineResult:
    """Subject-free diagnostic result for one immediate quarantine attempt."""

    run_id: str
    attempted_store_names: tuple[str, ...] = ()
    failed_store_names: tuple[str, ...] = ()
    error_code: str | None = None
    status: str = "completed"

    @property
    def success(self) -> bool:
        return self.status == "completed" and self.error_code is None

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "attempted_store_names": list(self.attempted_store_names),
            "failed_store_names": list(self.failed_store_names),
            "error_code": self.error_code,
            "status": self.status,
            "success": self.success,
        }


@dataclass(frozen=True)
class QuarantineBatchResult:
    """Subject-free bounded retry summary."""

    selected_count: int = 0
    completed_count: int = 0
    failed_count: int = 0
    audit_only: bool = False
    error_code: str | None = None
    results: tuple[QuarantineResult, ...] = field(default_factory=tuple, repr=False)

    def to_dict(self) -> dict:
        return {
            "selected_count": self.selected_count,
            "completed_count": self.completed_count,
            "failed_count": self.failed_count,
            "audit_only": self.audit_only,
            "error_code": self.error_code,
        }


@dataclass(frozen=True)
class RecoveryResult:
    """Recovery result; the returned user is intentionally hidden from repr."""

    recovered: bool
    user: dict | None = field(default=None, repr=False, compare=False)


def _locked_user(conn, user_id: str) -> dict | None:
    row = db._fetchone(
        conn,
        f"""
            SELECT u.* FROM users u
            WHERE u.id::text = {db._ph}
            FOR UPDATE
        """,
        (str(user_id),),
    )
    return db._row_to_dict(row) if row else None


def _immediate_policies():
    return tuple(policy for policy in lifecycle_registry.policies if policy.quarantine_on_request)


def _record_quarantine_success(conn, user_id: str, now: datetime) -> None:
    db._fetchone(
        conn,
        f"""
            UPDATE users
            SET erasure_last_attempt_at = {db._ph},
                erasure_last_error_code = NULL
            WHERE id::text = {db._ph}
            RETURNING erasure_last_attempt_at, erasure_last_error_code
        """,
        (now, str(user_id)),
    )


def _record_quarantine_failure(
    conn, user_id: str, now: datetime, error_code: str
) -> None:
    db._fetchone(
        conn,
        f"""
            UPDATE users
            SET erasure_attempt_count = LEAST(erasure_attempt_count + 1, 2147483647),
                erasure_last_attempt_at = {db._ph},
                erasure_last_error_code = {db._ph}
            WHERE id::text = {db._ph}
            RETURNING erasure_attempt_count, erasure_last_attempt_at,
                      erasure_last_error_code
        """,
        (now, error_code, str(user_id)),
    )


def _quarantine_is_not_pending(row: dict, requested_at: datetime) -> bool:
    if row.get("deleted_at") is None or row.get("is_active", True):
        return True
    due_at = _timestamp(row.get("erasure_due_at"))
    return due_at is not None and requested_at >= due_at


def _purge_immediate_policies(policies, owner_key: str):
    failed: list[str] = []
    error_code = None
    for policy in policies:
        result = policy.purge_owner(owner_key)
        if not result.complete or result.error_code is not None:
            failed.append(policy.name)
            error_code = error_code or _error_code(result.error_code)
    return failed, error_code


def _quarantine_locked(
    conn,
    user_id: str,
    requested_at: datetime,
    run_id: str,
    owner_key: str,
    policies,
    attempted: tuple[str, ...],
) -> QuarantineResult:
    row = _locked_user(conn, user_id)
    if not row:
        return QuarantineResult(
            run_id=run_id,
            attempted_store_names=attempted,
            error_code=_DB_ERROR,
            status="unavailable",
        )
    if _quarantine_is_not_pending(row, requested_at):
        return QuarantineResult(
            run_id=run_id,
            attempted_store_names=attempted,
            status="not_pending",
        )

    # The durable deleted_at check remains authoritative; this hook only
    # shortens the local blocked-owner cache for retries and restarts.
    owner_write_gate.block_owner(owner_key)
    failed, error_code = _purge_immediate_policies(policies, owner_key)
    if failed:
        bounded_error = error_code or _STORE_ERROR
        _record_quarantine_failure(
            conn, user_id, requested_at, bounded_error
        )
        return QuarantineResult(
            run_id=run_id,
            attempted_store_names=attempted,
            failed_store_names=tuple(failed),
            error_code=bounded_error,
            status="failed",
        )
    _record_quarantine_success(conn, user_id, requested_at)
    return QuarantineResult(
        run_id=run_id,
        attempted_store_names=attempted,
    )


def quarantine_account(user_id, *, now: datetime) -> QuarantineResult:
    """Purge bounded ephemeral stores while holding the durable user lock."""
    requested_at = _utc_aware(now, label="now")
    run_id = uuid4().hex
    owner_key = owner_key_for_user(user_id)
    policies = _immediate_policies()
    attempted = tuple(policy.name for policy in policies)

    try:
        db.initialize()
        with db._conn() as conn:
            return _quarantine_locked(
                conn,
                str(user_id),
                requested_at,
                run_id,
                owner_key,
                policies,
                attempted,
            )
    except Exception:
        return QuarantineResult(
            run_id=run_id,
            attempted_store_names=attempted,
            error_code=_DB_ERROR,
            status="unavailable",
        )


def retry_pending_quarantines(
    *, now: datetime, limit: int = 50, audit_only: bool = False
) -> QuarantineBatchResult:
    """Retry incomplete pre-deadline quarantine attempts independently."""
    requested_at = _utc_aware(now, label="now")
    if not 1 <= int(limit) <= _MAX_RETRY_BATCH:
        raise ValueError("limit must be between 1 and 50")
    selected_ids: list[str] = []
    try:
        db.initialize()
        with db._conn(commit_on_success=False) as conn:
            rows = db._fetchall(
                conn,
                f"""
                    SELECT id::text AS id
                    FROM users
                    WHERE deleted_at IS NOT NULL
                      AND erasure_due_at IS NOT NULL
                      AND erasure_due_at > {db._ph}
                      AND (
                          erasure_last_attempt_at IS NULL
                          OR erasure_last_error_code IS NOT NULL
                      )
                    ORDER BY deleted_at, id
                    LIMIT {db._ph}
                """,
                (requested_at, int(limit)),
            )
            selected_ids = [str(db._row_to_dict(row)["id"]) for row in rows]
    except Exception:
        return QuarantineBatchResult(
            audit_only=audit_only,
            error_code=_DB_ERROR,
        )

    if audit_only:
        return QuarantineBatchResult(
            selected_count=len(selected_ids),
            audit_only=True,
        )

    results: list[QuarantineResult] = []
    completed = 0
    failed = 0
    for selected_id in selected_ids:
        result = quarantine_account(selected_id, now=requested_at)
        results.append(result)
        if result.success or result.status == "not_pending":
            completed += 1
        else:
            failed += 1
    return QuarantineBatchResult(
        selected_count=len(selected_ids),
        completed_count=completed,
        failed_count=failed,
        results=tuple(results),
    )


def recover_account(user_id, *, now: datetime) -> RecoveryResult:
    """Recover only before the exact deadline, then unblock after commit."""
    requested_at = _utc_aware(now, label="now")
    owner_key = owner_key_for_user(user_id)
    recovered_user = None
    try:
        db.initialize()
        with db._conn() as conn:
            row = _locked_user(conn, str(user_id))
            if not row or not settings.RECOVERY_ENABLED_DURING_GRACE_PERIOD:
                return RecoveryResult(recovered=False)
            due_at = _timestamp(row.get("erasure_due_at"))
            last_attempt_at = _timestamp(row.get("erasure_last_attempt_at"))
            if (
                row.get("deleted_at") is None
                or row.get("is_active", True)
                or due_at is None
                or requested_at >= due_at
                or (
                    last_attempt_at is not None
                    and last_attempt_at >= due_at
                )
            ):
                return RecoveryResult(recovered=False)
            updated = db._fetchone(
                conn,
                f"""
                    UPDATE users
                    SET deleted_at = NULL,
                        erasure_due_at = NULL,
                        erasure_attempt_count = 0,
                        erasure_last_attempt_at = NULL,
                        erasure_last_error_code = NULL,
                        is_active = TRUE
                    WHERE id::text = {db._ph}
                    RETURNING *
                """,
                (str(user_id),),
            )
            recovered_user = db._row_to_dict(updated)
    except Exception:
        return RecoveryResult(recovered=False)

    owner_write_gate.unblock_owner(owner_key)
    return RecoveryResult(recovered=True, user=recovered_user)
