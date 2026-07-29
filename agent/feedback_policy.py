"""One-time, owner-bound aggregate feedback receipts."""

from __future__ import annotations

import hashlib
import hmac
import logging
import re
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from chat_identity import owner_binding_digest
from config import settings
from database import db


logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{43}$")
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_MODEL_VARIANTS = {
    "cx/gpt-5.4": "cx-gpt-5-4",
    "cx-gpt-5.4-mini": "cx-gpt-5-4-mini",
    "cx/gpt-5.5": "cx-gpt-5-5",
    "cx/gpt-5.5-mini": "cx-gpt-5-5-mini",
    "cx-gpt-5-4": "cx-gpt-5-4",
    "cx-gpt-5-4-mini": "cx-gpt-5-4-mini",
    "cx-gpt-5-5": "cx-gpt-5-5",
    "cx-gpt-5-5-mini": "cx-gpt-5-5-mini",
}
_TOOL_BUCKETS = frozenset({"none", "search", "weather", "knowledge", "mixed"})


class FeedbackUnavailable(RuntimeError):
    pass


class FeedbackRejected(RuntimeError):
    pass


@dataclass(frozen=True)
class FeedbackReceipt:
    token: str
    expires_at: datetime


@dataclass(frozen=True)
class FeedbackConsumeResult:
    rating: int
    idempotent: bool


@dataclass(frozen=True)
class _OwnerRef:
    owner_kind: str
    user_id: str | None
    anonymous_owner_digest: str | None
    owner_binding: str


@dataclass(frozen=True)
class _ReceiptRecord:
    token_digest: str
    owner_kind: str
    user_id: str | None
    anonymous_owner_digest: str | None
    owner_binding_digest: str
    assistant_turn_digest: str
    model_variant: str
    tool_bucket: str
    created_at: datetime
    expires_at: datetime


def _now(value: datetime | None) -> datetime:
    current = datetime.now(timezone.utc) if value is None else value
    if not isinstance(current, datetime) or current.tzinfo is None:
        raise FeedbackRejected("INVALID_FEEDBACK_TIME")
    return current.astimezone(timezone.utc)


def _owner_ref(owner_key: str) -> _OwnerRef:
    if not isinstance(owner_key, str):
        raise FeedbackRejected("INVALID_FEEDBACK_OWNER")
    if owner_key.startswith("user:"):
        raw_user_id = owner_key.removeprefix("user:")
        try:
            user_id = str(uuid.UUID(raw_user_id))
        except (ValueError, AttributeError) as exc:
            raise FeedbackRejected("INVALID_FEEDBACK_OWNER") from exc
        return _OwnerRef(
            owner_kind="authenticated",
            user_id=user_id,
            anonymous_owner_digest=None,
            owner_binding=owner_binding_digest(f"user:{user_id}"),
        )
    if owner_key.startswith("anon:"):
        anonymous_digest = owner_key.removeprefix("anon:")
        if not _DIGEST_RE.fullmatch(anonymous_digest):
            raise FeedbackRejected("INVALID_FEEDBACK_OWNER")
        return _OwnerRef(
            owner_kind="anonymous",
            user_id=None,
            anonymous_owner_digest=anonymous_digest,
            owner_binding=owner_binding_digest(owner_key),
        )
    raise FeedbackRejected("INVALID_FEEDBACK_OWNER")


def _token_digest(token: str) -> str:
    if not isinstance(token, str) or not _TOKEN_RE.fullmatch(token):
        raise FeedbackRejected("INVALID_FEEDBACK_RECEIPT")
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def _turn_digest(value: str) -> str:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise FeedbackRejected("INVALID_ASSISTANT_TURN_DIGEST")
    return value


def _rating(value: int) -> int:
    if type(value) is not int or value not in (0, 1):
        raise FeedbackRejected("INVALID_FEEDBACK_RATING")
    return value


def _model_variant(value: str) -> str:
    return _MODEL_VARIANTS.get(value, "other") if isinstance(value, str) else "other"


def _tool_bucket(value: str) -> str:
    return value if isinstance(value, str) and value in _TOOL_BUCKETS else "mixed"


class PostgresFeedbackStore:
    def _require_postgres(self) -> None:
        if not db._use_pg:
            raise FeedbackUnavailable("FEEDBACK_UNAVAILABLE")

    def issue(self, record: _ReceiptRecord) -> None:
        self._require_postgres()
        with db._conn() as conn:
            db._execute(
                conn,
                """
                INSERT INTO feedback_receipts (
                    token_digest, owner_kind, user_id, anonymous_owner_digest,
                    owner_binding_digest, assistant_turn_digest, model_variant,
                    tool_bucket, created_at, expires_at
                ) VALUES (
                    %s, %s, %s::uuid, %s, %s, %s, %s, %s, %s, %s
                )
                """,
                (
                    record.token_digest,
                    record.owner_kind,
                    record.user_id,
                    record.anonymous_owner_digest,
                    record.owner_binding_digest,
                    record.assistant_turn_digest,
                    record.model_variant,
                    record.tool_bucket,
                    record.created_at,
                    record.expires_at,
                ),
            )

    @staticmethod
    def _locked_receipt(conn, token_digest: str) -> dict:
        row = db._fetchone(
            conn,
            """
            SELECT id::text AS id, owner_kind, user_id::text AS user_id,
                   anonymous_owner_digest, owner_binding_digest,
                   model_variant, tool_bucket, rating, expires_at, used_at
            FROM feedback_receipts
            WHERE token_digest = %s
            FOR UPDATE
            """,
            (token_digest,),
        )
        if row is None:
            raise FeedbackUnavailable("FEEDBACK_UNAVAILABLE")
        return dict(row)

    @staticmethod
    def _authorize_receipt(
        stored: dict,
        *,
        owner_kind: str,
        owner_binding: str,
        now: datetime,
    ) -> None:
        if stored["expires_at"] <= now:
            raise FeedbackUnavailable("FEEDBACK_UNAVAILABLE")
        if stored["owner_kind"] != owner_kind or not hmac.compare_digest(
            stored["owner_binding_digest"], owner_binding
        ):
            raise FeedbackUnavailable("FEEDBACK_UNAVAILABLE")

    @staticmethod
    def _replay_result(stored: dict, rating: int) -> FeedbackConsumeResult | None:
        if stored["used_at"] is None:
            return None
        if stored["rating"] == rating:
            return FeedbackConsumeResult(rating=rating, idempotent=True)
        raise FeedbackRejected("CONFLICTING_FEEDBACK_REPLAY")

    @staticmethod
    def _require_direct_owner(
        stored: dict,
        *,
        owner_kind: str,
        user_id: str | None,
        anonymous_owner_digest: str | None,
    ) -> None:
        authenticated = (
            owner_kind == "authenticated"
            and stored["user_id"] == user_id
            and stored["anonymous_owner_digest"] is None
        )
        anonymous = (
            owner_kind == "anonymous"
            and stored["user_id"] is None
            and stored["anonymous_owner_digest"] == anonymous_owner_digest
        )
        if not (authenticated or anonymous):
            raise FeedbackUnavailable("FEEDBACK_UNAVAILABLE")

    @staticmethod
    def _increment_rollup(conn, stored: dict, *, owner_kind: str, rating: int, now: datetime) -> None:
        positive = 1 if rating == 1 else 0
        negative = 1 if rating == 0 else 0
        db._execute(
            conn,
            """
            INSERT INTO feedback_daily_rollups (
                day, owner_kind, model_variant, tool_bucket,
                positive_count, negative_count
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (day, owner_kind, model_variant, tool_bucket)
            DO UPDATE SET
                positive_count = feedback_daily_rollups.positive_count
                    + EXCLUDED.positive_count,
                negative_count = feedback_daily_rollups.negative_count
                    + EXCLUDED.negative_count
            """,
            (
                now.date(),
                owner_kind,
                stored["model_variant"],
                stored["tool_bucket"],
                positive,
                negative,
            ),
        )

    @staticmethod
    def _mark_used(conn, receipt_id: str, *, rating: int, now: datetime) -> None:
        db._execute(
            conn,
            """
            UPDATE feedback_receipts
            SET rating = %s, used_at = %s,
                user_id = NULL, anonymous_owner_digest = NULL
            WHERE id = %s::uuid
            """,
            (rating, now, receipt_id),
        )

    def consume(
        self,
        *,
        token_digest: str,
        owner_kind: str,
        user_id: str | None,
        anonymous_owner_digest: str | None,
        owner_binding: str,
        rating: int,
        now: datetime,
    ) -> FeedbackConsumeResult:
        self._require_postgres()
        with db._conn() as conn:
            stored = self._locked_receipt(conn, token_digest)
            self._authorize_receipt(
                stored,
                owner_kind=owner_kind,
                owner_binding=owner_binding,
                now=now,
            )
            replay = self._replay_result(stored, rating)
            if replay is not None:
                return replay
            self._require_direct_owner(
                stored,
                owner_kind=owner_kind,
                user_id=user_id,
                anonymous_owner_digest=anonymous_owner_digest,
            )
            self._increment_rollup(
                conn,
                stored,
                owner_kind=owner_kind,
                rating=rating,
                now=now,
            )
            self._mark_used(conn, stored["id"], rating=rating, now=now)
            return FeedbackConsumeResult(rating=rating, idempotent=False)

    def cleanup(self, *, now: datetime, limit: int) -> int:
        self._require_postgres()
        with db._conn() as conn:
            cursor = db._execute(
                conn,
                """
                WITH expired AS (
                    SELECT id
                    FROM feedback_receipts
                    WHERE expires_at <= %s
                    ORDER BY expires_at, id
                    LIMIT %s
                    FOR UPDATE SKIP LOCKED
                )
                DELETE FROM feedback_receipts AS receipt
                USING expired
                WHERE receipt.id = expired.id
                """,
                (now, limit),
            )
            return max(0, cursor.rowcount)

    def purge(self, *, owner_binding: str) -> int:
        self._require_postgres()
        with db._conn() as conn:
            cursor = db._execute(
                conn,
                "DELETE FROM feedback_receipts WHERE owner_binding_digest = %s",
                (owner_binding,),
            )
            return max(0, cursor.rowcount)

    def owner_absent(self, *, owner_binding: str) -> bool:
        self._require_postgres()
        with db._conn(commit_on_success=False) as conn:
            row = db._fetchone(
                conn,
                """
                SELECT 1 FROM feedback_receipts
                WHERE owner_binding_digest = %s
                LIMIT 1
                """,
                (owner_binding,),
            )
            return row is None


_store = PostgresFeedbackStore()


def issue_feedback_receipt(
    owner_key: str,
    assistant_turn_digest: str,
    model_variant: str,
    tool_bucket: str,
    *,
    now: datetime | None = None,
) -> FeedbackReceipt | None:
    owner = _owner_ref(owner_key)
    created_at = _now(now)
    expires_at = created_at + timedelta(hours=settings.FEEDBACK_RECEIPT_TTL_HOURS)
    token = secrets.token_urlsafe(32)
    record = _ReceiptRecord(
        token_digest=hashlib.sha256(token.encode("ascii")).hexdigest(),
        owner_kind=owner.owner_kind,
        user_id=owner.user_id,
        anonymous_owner_digest=owner.anonymous_owner_digest,
        owner_binding_digest=owner.owner_binding,
        assistant_turn_digest=_turn_digest(assistant_turn_digest),
        model_variant=_model_variant(model_variant),
        tool_bucket=_tool_bucket(tool_bucket),
        created_at=created_at,
        expires_at=expires_at,
    )
    try:
        _store.issue(record)
    except FeedbackRejected:
        raise
    except Exception:
        logger.warning("FEEDBACK_RECEIPT_ISSUE_UNAVAILABLE")
        return None
    return FeedbackReceipt(token=token, expires_at=expires_at)


def consume_feedback_receipt(
    token: str,
    owner_key: str,
    rating: int,
    *,
    now: datetime | None = None,
) -> FeedbackConsumeResult:
    token_hash = _token_digest(token)
    owner = _owner_ref(owner_key)
    safe_rating = _rating(rating)
    current = _now(now)
    try:
        return _store.consume(
            token_digest=token_hash,
            owner_kind=owner.owner_kind,
            user_id=owner.user_id,
            anonymous_owner_digest=owner.anonymous_owner_digest,
            owner_binding=owner.owner_binding,
            rating=safe_rating,
            now=current,
        )
    except (FeedbackRejected, FeedbackUnavailable):
        raise
    except Exception:
        logger.warning("FEEDBACK_RECEIPT_CONSUME_UNAVAILABLE")
        raise FeedbackUnavailable("FEEDBACK_UNAVAILABLE") from None


def cleanup_expired_feedback_receipts(
    *,
    now: datetime | None = None,
    limit: int = 500,
) -> int:
    if type(limit) is not int or not 1 <= limit <= 500:
        raise FeedbackRejected("INVALID_FEEDBACK_CLEANUP_LIMIT")
    try:
        return _store.cleanup(now=_now(now), limit=limit)
    except (FeedbackRejected, FeedbackUnavailable):
        raise
    except Exception:
        raise FeedbackUnavailable("FEEDBACK_UNAVAILABLE") from None


def purge_feedback_owner(owner_key: str) -> int:
    owner = _owner_ref(owner_key)
    try:
        return _store.purge(owner_binding=owner.owner_binding)
    except (FeedbackRejected, FeedbackUnavailable):
        raise
    except Exception:
        raise FeedbackUnavailable("FEEDBACK_UNAVAILABLE") from None


def verify_feedback_owner_absent(owner_key: str) -> bool:
    owner = _owner_ref(owner_key)
    try:
        return _store.owner_absent(owner_binding=owner.owner_binding)
    except (FeedbackRejected, FeedbackUnavailable):
        raise
    except Exception:
        raise FeedbackUnavailable("FEEDBACK_UNAVAILABLE") from None
