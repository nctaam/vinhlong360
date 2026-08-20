"""Capacity evidence: what the service actually did, with nobody in it.

Events are append-only rows grouped by case, risk and channel — never by
person. A metric row that carried a phone number or a bearer would turn the
measurement system into a second copy of the private data it measures, so the
metadata gate here refuses those keys outright.

The 28-day window is computed from the database every time. Nothing about it
lives in process memory, so a deploy or restart cannot reset the denominator —
the failure mode where every incident conveniently starts a fresh, clean month.

Eligibility only ever produces an internal evidence object. Nothing here flips
a public SLA claim; that is a decision a person makes while holding this
evidence, not a side effect of a query coming back non-zero.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

WINDOW_DAYS = 28

EVENT_KINDS = frozenset({
    "received", "triaged", "waiting", "updated", "decided", "applied",
    "verified", "completed", "repeated_contact", "provider_failure",
    "lease_expired", "recovery",
})

# Keys that would make a metric row a copy of private data.
_FORBIDDEN_METADATA_TOKENS = (
    "contact", "phone", "email", "capability", "receipt", "secret",
    "bearer", "token", "evidence", "value", "name",
)


class CapacityEventRejected(ValueError):
    pass


@dataclass(frozen=True)
class CapacityWindow:
    """Twenty-eight complete UTC days, ending yesterday."""

    start_day: date
    end_day: date
    days: int
    covered_days: int
    missing_days: tuple[date, ...]
    arrivals: int
    completions: int
    by_risk: dict
    by_channel: dict


@dataclass(frozen=True)
class EligibilityEvidence:
    window: CapacityWindow
    coverage_named: str
    computed_at: datetime


def _validate_metadata(metadata: dict | None) -> dict:
    metadata = dict(metadata or {})
    for key in metadata:
        normalized = str(key).lower().replace("-", "_")
        if any(token in normalized for token in _FORBIDDEN_METADATA_TOKENS):
            raise CapacityEventRejected(f"unsafe_capacity_metadata:{key}")
        if not isinstance(metadata[key], (str, int, float, bool, type(None))):
            raise CapacityEventRejected(f"unsafe_capacity_metadata:{key}")
    return metadata


def record_capacity_event(transaction, *, kind: str, channel: str, risk_class: str | None,
                          case_id: str | None = None, duration_seconds: int | None = None,
                          metadata: dict | None = None,
                          now: datetime | None = None) -> None:
    """Append one operational fact. Unknown kinds are refused, not invented."""
    if kind not in EVENT_KINDS:
        raise CapacityEventRejected(f"unknown_capacity_event:{kind}")
    if duration_seconds is not None and duration_seconds < 0:
        raise CapacityEventRejected("negative_duration")
    transaction.record_capacity_event(
        kind=kind, channel=channel, risk_class=risk_class, case_id=case_id,
        duration_seconds=duration_seconds, metadata=_validate_metadata(metadata),
        observed_at=now or datetime.now(timezone.utc),
    )


def capacity_window(transaction, now: datetime) -> CapacityWindow:
    """The last 28 complete UTC days, straight from the database.

    Today is excluded: it is not finished, and a window that includes a partial
    day undercounts precisely when somebody is looking.
    """
    end_day = now.astimezone(timezone.utc).date() - timedelta(days=1)
    start_day = end_day - timedelta(days=WINDOW_DAYS - 1)
    daily = transaction.capacity_daily_counts(start_day, end_day)

    covered = {row["day"] for row in daily}
    expected = [start_day + timedelta(days=offset) for offset in range(WINDOW_DAYS)]
    missing = tuple(day for day in expected if day not in covered)

    arrivals = sum(row["arrivals"] for row in daily)
    completions = sum(row["completions"] for row in daily)
    by_risk: dict = {}
    by_channel: dict = {}
    for row in daily:
        for risk, count in (row.get("by_risk") or {}).items():
            by_risk[risk] = by_risk.get(risk, 0) + count
        for channel, count in (row.get("by_channel") or {}).items():
            by_channel[channel] = by_channel.get(channel, 0) + count

    return CapacityWindow(
        start_day=start_day, end_day=end_day, days=WINDOW_DAYS,
        covered_days=len(covered), missing_days=missing,
        arrivals=arrivals, completions=completions,
        by_risk=by_risk, by_channel=by_channel,
    )


def public_sla_eligible(window: CapacityWindow, *, coverage_named: str = "",
                        now: datetime | None = None):
    """False, or the evidence a person may act on. Never a switch.

    27 days is not 28. A gap is not coverage. Zero arrivals means the service
    was not exercised, and zero completions means it did not finish anything —
    neither is a record anyone may promise on.
    """
    if window.days != WINDOW_DAYS or window.covered_days != WINDOW_DAYS:
        return False
    if window.missing_days:
        return False
    if window.arrivals <= 0 or window.completions <= 0:
        return False
    if not coverage_named.strip():
        # Somebody has to be named as holding the duty the SLA describes.
        return False
    return EligibilityEvidence(
        window=window,
        coverage_named=coverage_named.strip(),
        computed_at=now or datetime.now(timezone.utc),
    )


# ── Instrumentation ──
#
# `observe` is what the transports call. It opens its own short transaction and
# never raises: a broken metrics pipe must never break the business action it
# is watching, so every failure lands in the log and nowhere else.

import logging

_DATABASE = None
_logger = logging.getLogger("cases.metrics")


def configure_case_metrics(*, database=None) -> None:
    global _DATABASE
    _DATABASE = database


def observe_on(transaction, kind: str, *, channel: str, risk_class: str | None = None,
               case_id: str | None = None, duration_seconds: int | None = None,
               metadata: dict | None = None, now: datetime | None = None) -> bool:
    """Record on the caller's OPEN transaction, never on a second connection.

    `observe` opens one of its own. Called from inside a transaction that holds
    FOR UPDATE on a `cases` row, that second connection blocks: the capacity
    insert carries a foreign key to `cases` and so needs FOR KEY SHARE on the
    very row the caller has locked, while the caller sits waiting for this
    function to return. PostgreSQL cannot see that cycle — one side is blocked
    in the application — so nothing raises a deadlock; the statement runs to its
    timeout and the connection is dropped as idle-in-transaction. Verification
    hung and then failed with an undecodable 409, every single time.
    """
    try:
        record_capacity_event(
            transaction, kind=kind, channel=channel, risk_class=risk_class,
            case_id=case_id, duration_seconds=duration_seconds,
            metadata=metadata, now=now,
        )
        return True
    except CapacityEventRejected:
        # A bad kind or duration is a programming error, not a database fault,
        # and swallowing it here would keep the caller's transaction usable.
        _logger.warning("capacity event refused: %s", kind, exc_info=True)
        return False


def observe(kind: str, *, channel: str, risk_class: str | None = None,
            case_id: str | None = None, duration_seconds: int | None = None,
            metadata: dict | None = None, now: datetime | None = None) -> bool:
    """Record one boundary event; True if it landed, False if it was dropped."""
    if _DATABASE is None:
        return False
    try:
        from .store import PostgresCaseStore

        with PostgresCaseStore(_DATABASE).transaction() as transaction:
            record_capacity_event(
                transaction, kind=kind, channel=channel, risk_class=risk_class,
                case_id=case_id, duration_seconds=duration_seconds,
                metadata=metadata, now=now,
            )
        return True
    except Exception:  # noqa: BLE001 - measurement must never break the action
        _logger.warning("capacity event dropped: %s", kind, exc_info=True)
        return False
