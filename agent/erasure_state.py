"""Durable account-erasure state and the request transaction boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from config import settings
from database import db


UTC = timezone.utc
ERASURE_ERROR_CODES = frozenset(
    {"STORE_UNAVAILABLE", "RESIDUAL_DATA", "DB_CONSTRAINT", "VERIFY_FAILED"}
)


def _utc_aware(value: datetime, *, label: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError(f"{label} must be UTC-aware")
    return value.astimezone(UTC)


def _coerce_timestamp(value, *, label: str) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return _utc_aware(value, label=label)


@dataclass(frozen=True)
class ErasureState:
    deleted_at: datetime | None
    erasure_due_at: datetime | None
    erasure_attempt_count: int
    erasure_last_attempt_at: datetime | None
    erasure_last_error_code: str | None

    def __post_init__(self) -> None:
        if self.erasure_attempt_count < 0:
            raise ValueError("erasure_attempt_count must be non-negative")
        if self.erasure_last_error_code not in (None, *ERASURE_ERROR_CODES):
            raise ValueError("invalid erasure error code")
        for field_name in ("deleted_at", "erasure_due_at", "erasure_last_attempt_at"):
            value = getattr(self, field_name)
            if value is not None and (not isinstance(value, datetime) or value.tzinfo is None):
                raise ValueError(f"{field_name} must be UTC-aware")


def _state_from_row(row: dict) -> ErasureState:
    return ErasureState(
        deleted_at=_coerce_timestamp(row.get("deleted_at"), label="deleted_at"),
        erasure_due_at=_coerce_timestamp(
            row.get("erasure_due_at"), label="erasure_due_at"
        ),
        erasure_attempt_count=int(row.get("erasure_attempt_count") or 0),
        erasure_last_attempt_at=_coerce_timestamp(
            row.get("erasure_last_attempt_at"), label="erasure_last_attempt_at"
        ),
        erasure_last_error_code=row.get("erasure_last_error_code"),
    )


def load_erasure_state(conn, user_id, *, for_update: bool = False) -> ErasureState:
    """Load durable state, optionally taking the user-row lock."""
    lock = " FOR UPDATE" if for_update else ""
    row = db._fetchone(
        conn,
        f"""
            SELECT deleted_at, erasure_due_at, erasure_attempt_count,
                   erasure_last_attempt_at, erasure_last_error_code
            FROM users
            WHERE id::text = {db._ph}{lock}
        """,
        (str(user_id),),
    )
    if not row:
        raise LookupError("account not found")
    return _state_from_row(db._row_to_dict(row))


def request_account_erasure(user_id, *, now: datetime) -> ErasureState:
    """Commit disablement, deadline, and credential revocation atomically."""
    requested_at = _utc_aware(now, label="now")
    due_at = requested_at + timedelta(days=settings.ACCOUNT_ERASURE_DEADLINE_DAYS)
    db.initialize()

    with db._conn() as conn:
        row = db._fetchone(
            conn,
            f"""
                SELECT id, phone, deleted_at, erasure_due_at,
                       erasure_attempt_count, erasure_last_attempt_at,
                       erasure_last_error_code
                FROM users
                WHERE id::text = {db._ph}
                FOR UPDATE
            """,
            (str(user_id),),
        )
        if not row:
            raise LookupError("account not found")
        row = db._row_to_dict(row)
        phone = row.get("phone")
        updated = db._fetchone(
            conn,
            f"""
                UPDATE users
                SET deleted_at = COALESCE(deleted_at, {db._ph}),
                    erasure_due_at = COALESCE(erasure_due_at, {db._ph}),
                    is_active = FALSE
                WHERE id::text = {db._ph}
                RETURNING deleted_at, erasure_due_at, erasure_attempt_count,
                          erasure_last_attempt_at, erasure_last_error_code
            """,
            (requested_at, due_at, str(user_id)),
        )
        db._execute(
            conn,
            f"DELETE FROM user_sessions WHERE user_id::text = {db._ph}",
            (str(user_id),),
        )
        db._execute(
            conn,
            f"DELETE FROM otp_sessions WHERE phone = {db._ph}",
            (phone,),
        )
        db._execute(
            conn,
            f"DELETE FROM trusted_devices WHERE user_id::text = {db._ph}",
            (str(user_id),),
        )
        db._execute(
            conn,
            f"DELETE FROM pending_2fa WHERE user_id::text = {db._ph}",
            (str(user_id),),
        )
        return _state_from_row(db._row_to_dict(updated))
