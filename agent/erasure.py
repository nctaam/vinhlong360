"""Verified hard-erasure orchestration for deleted PostgreSQL accounts."""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from data_lifecycle import lifecycle_registry, validate_lifecycle_registry
from database import db
from erasure_state import ERASURE_ERROR_CODES
import metrics
from owner_write_gate import owner_key_for_user
from structured_references import scrub_user_references, validate_user_fk_actions


UTC = timezone.utc
_MAX_BATCH = 50
_DB_ERROR = "DB_CONSTRAINT"
_STORE_ERROR = "STORE_UNAVAILABLE"
_RESIDUAL_ERROR = "RESIDUAL_DATA"
_VERIFY_ERROR = "VERIFY_FAILED"
logger = logging.getLogger("erasure")


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


def _bounded_error(value: str | None, fallback: str) -> str:
    return value if value in ERASURE_ERROR_CODES else fallback


def _opaque_run_id(value: str | None) -> str:
    if value is None:
        return uuid4().hex
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:32]


@dataclass(frozen=True)
class ErasureResult:
    status: str
    stores: tuple[dict, ...] = ()
    error_code: str | None = None
    verified: bool = False
    run_id: str = field(default="", repr=False)

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "stores": [dict(store) for store in self.stores],
            "error_code": self.error_code,
            "verified": self.verified,
            "run_id": self.run_id,
        }


@dataclass(frozen=True)
class BatchErasureResult:
    selected_count: int = 0
    completed_count: int = 0
    failed_count: int = 0
    overdue_count: int = 0
    audit_only: bool = False
    error_code: str | None = None
    results: tuple[ErasureResult, ...] = field(default_factory=tuple, repr=False)

    def to_dict(self) -> dict:
        return {
            "selected_count": self.selected_count,
            "completed_count": self.completed_count,
            "failed_count": self.failed_count,
            "overdue_count": self.overdue_count,
            "audit_only": self.audit_only,
            "error_code": self.error_code,
        }


def _locked_user_row(conn, user_id: str) -> dict | None:
    row = db._fetchone(
        conn,
        f"""
            SELECT id, deleted_at, erasure_due_at, erasure_attempt_count,
                   erasure_last_attempt_at, erasure_last_error_code
            FROM users
            WHERE id::text = {db._ph}
            FOR UPDATE
        """,
        (str(user_id),),
    )
    if not row:
        return None
    return db._row_to_dict(row)


def _row_is_due(row: dict, now: datetime) -> bool:
    due_at = _timestamp(row.get("erasure_due_at"))
    return row.get("deleted_at") is not None and due_at is not None and due_at <= now


def _locked_due_row(conn, user_id: str, now: datetime) -> dict | None:
    row = _locked_user_row(conn, user_id)
    return row if row is not None and _row_is_due(row, now) else None


def _prepare_attempt(user_id: str, now: datetime):
    if not getattr(db, "_use_pg", True):
        return None, _DB_ERROR, "failed"
    try:
        db.initialize()
        with db._conn() as conn:
            row = _locked_user_row(conn, user_id)
            if row is None:
                return None, None, "already_erased"
            if not _row_is_due(row, now):
                return None, None, "not_due"
            db._fetchone(
                conn,
                f"""
                    UPDATE users
                    SET erasure_last_attempt_at = {db._ph}
                    WHERE id::text = {db._ph}
                    RETURNING erasure_last_attempt_at
                """,
                (now, str(user_id)),
            )
            return row, None, "prepared"
    except Exception:
        return None, _DB_ERROR, "failed"


def _subject_policies():
    return tuple(
        policy
        for policy in lifecycle_registry.policies
        if policy.subject_linked and policy.classification in {"personal", "pseudonymous"}
    )


def _validated_subject_policies():
    try:
        errors = validate_lifecycle_registry(lifecycle_registry.policies)
    except Exception:
        errors = ("INVALID_REGISTRY",)
    if errors:
        return (), _STORE_ERROR
    return _subject_policies(), None


def _store_entry(policy, purge, verify, error_code):
    return {
        "store_name": policy.name,
        "purged": bool(purge.complete),
        "removed_count": max(0, int(purge.removed_count)),
        "verified": bool(verify.verified),
        "residual_count": max(0, int(verify.residual_count)),
        "error_code": error_code,
    }


def _purge_and_verify(owner_key: str, policies):
    stores: list[dict] = []
    first_error = None
    for policy in policies:
        purge = policy.purge_owner(owner_key)
        verify = policy.verify_owner_absent(owner_key)
        error_code = None
        if not purge.complete or purge.error_code is not None:
            error_code = _bounded_error(purge.error_code, _STORE_ERROR)
        elif not verify.verified:
            fallback = _RESIDUAL_ERROR if verify.residual_count else _VERIFY_ERROR
            error_code = _bounded_error(verify.error_code, fallback)
        stores.append(_store_entry(policy, purge, verify, error_code))
        first_error = first_error or error_code
    return tuple(stores), first_error


def _record_failure(user_id: str, now: datetime, error_code: str) -> None:
    try:
        with db._conn() as conn:
            db._fetchone(
                conn,
                f"""
                    UPDATE users
                    SET erasure_attempt_count = LEAST(erasure_attempt_count + 1, 2147483647),
                        erasure_last_attempt_at = {db._ph},
                        erasure_last_error_code = {db._ph}
                    WHERE id::text = {db._ph} AND deleted_at IS NOT NULL
                    RETURNING erasure_attempt_count
                """,
                (now, error_code, str(user_id)),
            )
    except Exception:
        return


def _count_row(row) -> int:
    if row is None:
        return 0
    if isinstance(row, Mapping):
        return int(next(iter(row.values())) or 0)
    return int(row[0] or 0)


def _structured_checks(user_id: str):
    owner_key = f"user:{user_id}"
    sentinel = json.dumps([{"type": "user", "id": user_id}], separators=(",", ":"))
    return (
        ("SELECT COUNT(*) FROM feedback WHERE user_id = %s OR user_id = %s", (user_id, owner_key)),
        ("SELECT COUNT(*) FROM follows WHERE follower_id::text = %s OR (target_type = 'user' AND target_id = %s)", (user_id, user_id)),
        ("SELECT COUNT(*) FROM notifications WHERE ref_type = 'user' AND ref_id = %s", (user_id,)),
        ("SELECT COUNT(*) FROM reports WHERE reporter_id::text = %s OR (target_type = 'user' AND target_id = %s)", (user_id, user_id)),
        ("SELECT COUNT(*) FROM moderation_log WHERE target_type = 'user' AND target_id = %s", (user_id,)),
        ("SELECT COUNT(*) FROM posts WHERE mentions @> %s::jsonb", (sentinel,)),
        ("SELECT COUNT(*) FROM comments WHERE mentions @> %s::jsonb", (sentinel,)),
        ("SELECT COUNT(*) FROM entity_claims WHERE claimant_id::text = %s OR reviewer_id::text = %s", (user_id, user_id)),
        ("SELECT COUNT(*) FROM moderation_appeals WHERE user_id::text = %s OR reviewer_id::text = %s", (user_id, user_id)),
        ("SELECT COUNT(*) FROM admin_audit_events WHERE actor = %s OR actor = %s", (user_id, owner_key)),
        ("SELECT COUNT(*) FROM entity_changes WHERE actor = %s OR actor = %s", (user_id, owner_key)),
        ("SELECT COUNT(*) FROM site_settings_history WHERE actor = %s OR actor = %s", (user_id, owner_key)),
    )


def _assert_structured_absent(conn, user_id: str) -> None:
    with conn.cursor() as cursor:
        for sql, params in _structured_checks(user_id):
            cursor.execute(sql, params)
            if _count_row(cursor.fetchone()) > 0:
                raise RuntimeError("structured reference residue")


def _finalize_database(user_id: str, now: datetime) -> str:
    with db._conn() as conn:
        if _locked_due_row(conn, user_id, now) is None:
            row = db._fetchone(
                conn,
                f"SELECT id, deleted_at FROM users WHERE id::text = {db._ph}",
                (str(user_id),),
            )
            return "already_erased" if not row else "not_due"
        scrub_user_references(conn, user_id, actor_policy="set_null")
        validate_user_fk_actions(conn)
        _assert_structured_absent(conn, user_id)
        if not db.delete_erased_user(conn, user_id, now):
            raise RuntimeError("final delete predicate did not match")
        if db._fetchone(
            conn,
            f"SELECT id FROM users WHERE id::text = {db._ph}",
            (str(user_id),),
        ):
            raise RuntimeError("user residue after final delete")
    return "completed"


def _failed_result(run_id: str, code: str, stores=()) -> ErasureResult:
    return ErasureResult(
        status="failed",
        stores=tuple(stores),
        error_code=code,
        verified=False,
        run_id=run_id,
    )


def _observe_failure(run_id: str, code: str, stores=()) -> None:
    metrics.erasure_failed_total.inc({"code": code})
    for store in stores:
        if store.get("error_code"):
            logger.warning(
                "Erasure store failed: run_id=%s store_name=%s error_code=%s",
                run_id,
                store["store_name"],
                store["error_code"],
            )


def erase_account(user_id, *, now: datetime, run_id: str | None = None) -> ErasureResult:
    requested_at = _utc_aware(now, label="now")
    stable_run_id = _opaque_run_id(run_id)
    row, prep_error, prep_status = _prepare_attempt(str(user_id), requested_at)
    if prep_error:
        _observe_failure(stable_run_id, prep_error)
        return _failed_result(stable_run_id, prep_error)
    if prep_status == "already_erased":
        return ErasureResult(
            status="already_erased",
            verified=True,
            run_id=stable_run_id,
        )
    if row is None:
        return ErasureResult(status="not_due", run_id=stable_run_id)

    owner_key = owner_key_for_user(user_id)
    policies, registry_error = _validated_subject_policies()
    if registry_error:
        _record_failure(str(user_id), requested_at, registry_error)
        _observe_failure(stable_run_id, registry_error)
        return _failed_result(stable_run_id, registry_error)
    stores, store_error = _purge_and_verify(owner_key, policies)
    if store_error:
        _record_failure(str(user_id), requested_at, store_error)
        _observe_failure(stable_run_id, store_error, stores)
        return _failed_result(stable_run_id, store_error, stores)

    try:
        final_status = _finalize_database(str(user_id), requested_at)
    except Exception:
        _record_failure(str(user_id), requested_at, _DB_ERROR)
        _observe_failure(stable_run_id, _DB_ERROR, stores)
        return _failed_result(stable_run_id, _DB_ERROR, stores)
    if final_status == "already_erased":
        metrics.erasure_completed_total.inc()
        return ErasureResult(
            status="completed",
            stores=stores,
            verified=True,
            run_id=stable_run_id,
        )
    if final_status != "completed":
        _record_failure(str(user_id), requested_at, _DB_ERROR)
        _observe_failure(stable_run_id, _DB_ERROR, stores)
        return _failed_result(stable_run_id, _DB_ERROR, stores)
    metrics.erasure_completed_total.inc()
    return ErasureResult(
        status="completed",
        stores=stores,
        verified=True,
        run_id=stable_run_id,
    )


def _select_due_ids(now: datetime, limit: int):
    with db._conn(commit_on_success=False) as conn:
        rows = db._fetchall(
            conn,
            f"""
                SELECT id::text AS id, erasure_due_at
                FROM users
                WHERE deleted_at IS NOT NULL
                  AND erasure_due_at IS NOT NULL
                  AND erasure_due_at <= {db._ph}
                ORDER BY erasure_due_at, id
                LIMIT {db._ph}
            """,
            (now, limit),
        )
        return [db._row_to_dict(row) for row in rows]


def _erase_selected(user_id: str, requested_at: datetime) -> ErasureResult:
    try:
        return erase_account(user_id, now=requested_at)
    except Exception:
        run_id = _opaque_run_id(None)
        _record_failure(user_id, requested_at, _DB_ERROR)
        _observe_failure(run_id, _DB_ERROR)
        return _failed_result(run_id, _DB_ERROR)


def erase_due_accounts(
    now: datetime, limit: int = 50, *, audit_only: bool = False
) -> BatchErasureResult:
    requested_at = _utc_aware(now, label="now")
    if not 1 <= int(limit) <= _MAX_BATCH:
        raise ValueError("limit must be between 1 and 50")
    try:
        if not getattr(db, "_use_pg", True):
            return BatchErasureResult(audit_only=audit_only, error_code=_DB_ERROR)
        selected = _select_due_ids(requested_at, int(limit))
    except Exception:
        return BatchErasureResult(audit_only=audit_only, error_code=_DB_ERROR)

    overdue = sum(
        1 for row in selected if _timestamp(row.get("erasure_due_at")) is not None
    )
    metrics.erasure_due_total.inc(amount=len(selected))
    metrics.erasure_overdue_total.inc(amount=overdue)
    if audit_only:
        return BatchErasureResult(
            selected_count=len(selected),
            overdue_count=overdue,
            audit_only=True,
        )

    results = tuple(
        _erase_selected(str(row["id"]), requested_at) for row in selected
    )
    completed = sum(result.verified for result in results)
    failed = sum(result.status == "failed" for result in results)
    return BatchErasureResult(
        selected_count=len(selected),
        completed_count=completed,
        failed_count=failed,
        overdue_count=overdue,
        results=results,
    )
