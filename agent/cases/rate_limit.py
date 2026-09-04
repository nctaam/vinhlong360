"""Durable rate buckets for case commands.

Local memory is not authoritative: a process restart or a second worker must not
reset abuse controls, so the sliding window lives in ``shared_rate_limits`` and
every decision is taken under a per-key advisory lock. Subjects are stored as
keyed digests, never as a raw IP, contact, or actor reference.
"""
from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timedelta

CASE_RATE_BUCKETS = frozenset(
    {
        "correction_create",
        "receipt_exchange",
        "contact_otp",
        "contact_otp_requester",
        "contact_otp_verify",
        "contact_otp_withdraw",
        "case_review",
        "receipt_rotation",
    }
)


def rate_subject_digest(subject: str, *, master_key: str | bytes) -> str:
    if type(subject) is not str or not subject.strip():
        raise ValueError("invalid_rate_subject")
    key = master_key.encode("utf-8") if isinstance(master_key, str) else master_key
    return hmac.new(key, subject.strip().encode("utf-8"), hashlib.sha256).hexdigest()


def _validate(bucket: object, subject_digest: object, limit: object, window: object, now: object) -> None:
    if type(bucket) is not str or not bucket:
        raise ValueError("invalid_rate_bucket")
    if type(subject_digest) is not str or not subject_digest:
        raise ValueError("invalid_rate_subject")
    if type(limit) is not int or limit < 1 or type(window) is not int or window < 1:
        raise ValueError("invalid_rate_window")
    if type(now) is not datetime or now.tzinfo is None:
        raise ValueError("invalid_rate_clock")


def check_case_rate_limit(
    bucket: str,
    subject_digest: str,
    *,
    limit: int,
    window: int,
    now: datetime,
    database=None,
) -> bool:
    """Record one attempt and report whether it is allowed.

    Returns ``False`` once the window is full without recording the attempt, so a
    blocked caller cannot extend its own penalty by retrying.
    """
    _validate(bucket, subject_digest, limit, window, now)
    if database is None:
        from database import db as database
    if not database._use_pg:
        raise RuntimeError("case_postgresql_required")

    key = f"case:{bucket}:{subject_digest}"
    stamp = now.timestamp()
    cutoff = stamp - window
    expires_at = now + timedelta(seconds=window)
    with database._conn(commit_on_success=False) as conn:
        database._fetchone(
            conn, "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (key,)
        )
        row = database._fetchone(
            conn, "SELECT hits FROM shared_rate_limits WHERE key=%s FOR UPDATE", (key,)
        )
        recorded = row["hits"] if row is not None and row["hits"] is not None else []
        hits = [float(value) for value in recorded if float(value) > cutoff]
        allowed = len(hits) < limit
        if allowed:
            hits.append(stamp)
        database._execute(
            conn,
            """
            INSERT INTO shared_rate_limits(key, hits, expires_at, updated_at)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (key) DO UPDATE SET
                hits = EXCLUDED.hits,
                expires_at = EXCLUDED.expires_at,
                updated_at = EXCLUDED.updated_at
            """,
            (key, hits, expires_at, now),
        )
        conn.commit()
    return allowed
