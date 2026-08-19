"""At-least-once notification dispatch for correction cases.

A committed receipt is never undone by a notification outage: dispatch reads its
own queue, and every outcome — delivered, retried, suppressed or dead-lettered —
stays inside the outbox row. Authority is re-checked immediately before each
side effect, so consent withdrawn after enqueue means the message is never sent.

Messages carry a public reference and generic copy only. No evidence, no
proposed value, no phone echoed back, and never a bearer secret.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta

MAX_ATTEMPTS = 5
# Long enough to outlast a slow provider round trip, short enough that a
# dead worker's items come due again the same hour.
LEASE_SECONDS = 900
_BACKOFF_SECONDS = (60, 300, 1800, 7200)
_SUPPRESSED = "suppressed_at_delivery"

# One line per topic. An unknown topic is a programming error, not a licence to
# improvise copy at a reporter.
_TOPIC_COPY = {
    "correction.received": (
        "vinhlong360: da nhan yeu cau dinh chinh {reference}. "
        "Tra cuu tien do bang ma nay tren trang tra cuu. Khong chia se ma voi ai."
    ),
    "correction.updated": (
        "vinhlong360: yeu cau {reference} co cap nhat moi. "
        "Tra cuu tien do bang ma nay tren trang tra cuu. Khong chia se ma voi ai."
    ),
    "correction.closed": (
        "vinhlong360: yeu cau {reference} da khep lai. "
        "Tra cuu ket qua bang ma nay tren trang tra cuu. Khong chia se ma voi ai."
    ),
}

_DATABASE = None
_CRYPTO = None
_PROVIDER = None
_CONTACT_LOOKUP = None


@dataclass(frozen=True)
class DeliveryResult:
    delivered: bool
    error_code: str | None = None
    retryable: bool = False


@dataclass(frozen=True)
class DispatchSummary:
    claimed: int = 0
    sent: int = 0
    retried: int = 0
    suppressed: int = 0
    dead_lettered: int = 0


def configure_case_outbox(*, database=None, crypto=None, provider=None, contact_lookup=None) -> None:
    global _DATABASE, _CRYPTO, _PROVIDER, _CONTACT_LOOKUP
    _DATABASE = database
    _CRYPTO = crypto
    _PROVIDER = provider
    _CONTACT_LOOKUP = contact_lookup


def notification_message(*, public_reference: str, topic: str) -> str:
    if type(public_reference) is not str or not public_reference:
        raise ValueError("invalid_public_reference")
    template = _TOPIC_COPY.get(topic)
    if template is None:
        raise ValueError("unknown_outbox_topic")
    return template.format(reference=public_reference)


def _observe_provider_failure(case_id: str, now) -> None:
    from . import metrics as _metrics

    _metrics.observe("provider_failure", channel="sms", case_id=case_id, now=now)


def delivery_key(outbox_id: str) -> str:
    """A stable identifier for one logical send, for our own records and logs.

    It is deliberately NOT called an idempotency token: the eSMS payload has no
    field to carry one, so nothing on the provider side deduplicates for us.
    At-most-once therefore has to come from this module committing each outcome
    before it moves on — see dispatch_case_outbox.
    """
    return hashlib.sha256(f"vl360-case-outbox:{outbox_id}".encode("ascii")).hexdigest()[:32]


def _database():
    if _DATABASE is not None:
        return _DATABASE
    from database import db

    return db


def _contact_for(case_id: str, *, now: datetime) -> str | None:
    if _CONTACT_LOOKUP is not None:
        return _CONTACT_LOOKUP(case_id, now=now)
    from .contact import deliverable_contact_for

    return deliverable_contact_for(case_id, now=now, crypto=_CRYPTO)


def _claim(database, conn, now: datetime, limit: int) -> list[dict]:
    """Take a lease on due items and commit it before a single message is sent.

    'processing' has been in the schema since 080 and nothing used it. It is the
    difference between owning work and merely having read it: the lease is
    committed here, so a worker that dies mid-batch strands nothing — the lease
    lapses and the items come due again — while a concurrent dispatcher sees
    them as taken rather than sending them a second time.
    """
    rows = database._fetchall(
        conn,
        """
        SELECT outbox_id, case_id, topic, attempts
        FROM case_outbox
        WHERE status IN ('pending', 'processing') AND available_at <= %s
        ORDER BY available_at
        LIMIT %s
        FOR UPDATE SKIP LOCKED
        """,
        (now, limit),
    )
    claimed = [dict(database._row_to_dict(row)) for row in rows]
    if claimed:
        database._execute(
            conn,
            """
            UPDATE case_outbox
            SET status = 'processing', available_at = %s
            WHERE outbox_id = ANY(%s::uuid[])
            """,
            (now + timedelta(seconds=LEASE_SECONDS),
             [str(item["outbox_id"]) for item in claimed]),
        )
    return claimed


def _public_reference(database, conn, case_id: str) -> str | None:
    row = database._fetchone(
        conn,
        """
        SELECT public_reference FROM case_receipts
        WHERE case_id = %s AND revoked_at IS NULL
        ORDER BY receipt_revision DESC LIMIT 1
        """,
        (case_id,),
    )
    return None if row is None else str(database._row_to_dict(row)["public_reference"])


def _settle(database, conn, outbox_id: str, *, status: str, attempts: int,
            error_code: str | None, available_at: datetime) -> None:
    database._execute(
        conn,
        """
        UPDATE case_outbox
        SET status = %s, attempts = %s, last_error_code = %s, available_at = %s
        WHERE outbox_id = %s
        """,
        (status, attempts, error_code, available_at, outbox_id),
    )


def dispatch_case_outbox(*, now: datetime, limit: int = 100) -> DispatchSummary:
    """Claim due items, re-check authority, deliver, and record the outcome."""
    if type(now) is not datetime or now.tzinfo is None:
        raise ValueError("invalid_dispatch_clock")
    if type(limit) is not int or limit < 1:
        raise ValueError("invalid_dispatch_limit")
    database = _database()
    if not database._use_pg:
        raise RuntimeError("case_postgresql_required")

    claimed = sent = retried = suppressed = dead = 0
    # The lease is taken and committed first. Everything after it sends real
    # messages to real people, and each outcome is committed on its own: one
    # transaction spanning a whole batch means a failure on item fifty rolls
    # back the records of the forty-nine messages already delivered, and the
    # next run sends every one of them again.
    with database._conn(commit_on_success=False) as conn:
        due = _claim(database, conn, now, limit)
        conn.commit()

    with database._conn(commit_on_success=False) as conn:
        for item in due:
            claimed += 1
            outbox_id = str(item["outbox_id"])
            attempts = int(item["attempts"]) + 1

            # Authority is re-read here, not trusted from enqueue time.
            contact = _contact_for(str(item["case_id"]), now=now)
            reference = _public_reference(database, conn, str(item["case_id"]))
            if not contact or not reference:
                suppressed += 1
                _settle(database, conn, outbox_id, status="failed", attempts=attempts,
                        error_code=_SUPPRESSED, available_at=now)
                conn.commit()
                continue

            message = notification_message(public_reference=reference, topic=str(item["topic"]))
            result = _PROVIDER.send(contact, message, delivery_key=delivery_key(outbox_id))

            if result.delivered:
                sent += 1
                from . import metrics as _metrics

                _metrics.observe("updated", channel="sms",
                                 case_id=str(item["case_id"]), now=now)
                _settle(database, conn, outbox_id, status="sent", attempts=attempts,
                        error_code=None, available_at=now)
                conn.commit()
            elif result.retryable and attempts < MAX_ATTEMPTS:
                retried += 1
                _observe_provider_failure(str(item["case_id"]), now)
                backoff = _BACKOFF_SECONDS[min(attempts, len(_BACKOFF_SECONDS)) - 1]
                _settle(database, conn, outbox_id, status="pending", attempts=attempts,
                        error_code=result.error_code,
                        available_at=now + timedelta(seconds=backoff))
                conn.commit()
            else:
                dead += 1
                _observe_provider_failure(str(item["case_id"]), now)
                _settle(database, conn, outbox_id, status="failed", attempts=attempts,
                        error_code=result.error_code, available_at=now)
                conn.commit()

    return DispatchSummary(
        claimed=claimed, sent=sent, retried=retried,
        suppressed=suppressed, dead_lettered=dead,
    )
