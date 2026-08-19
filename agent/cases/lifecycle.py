"""Retention: everything private has an end date; the answerable minimum stays.

The order of the shelves, from shortest to longest:

  promptly       expired access sessions, idempotency rows, contact challenges
  90 days        the optional contact after a case reaches a terminal close —
                 a reply address kept longer than the reply is surveillance
  365 days       encrypted private evidence and reported/proposed payloads,
                 unless a hold has been explicitly audited for that case
  730 days       the minimal case/decision/publication/audit lineage stays put;
                 after that, capacity events lose their case linkage

Nothing here ever deletes the audit or decision lineage early. A service that
edits public facts must be able to answer for an edit for as long as the edit
can matter, and 730 days is that promise, not this module's to shorten.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

CONTACT_RETENTION = timedelta(days=90)
PRIVATE_EVIDENCE_RETENTION = timedelta(days=365)
LINEAGE_RETENTION = timedelta(days=730)


@dataclass(frozen=True)
class CleanupSummary:
    expired_access_sessions: int = 0
    expired_idempotency: int = 0
    expired_challenges: int = 0
    contacts_redacted: int = 0
    private_payloads_redacted: int = 0
    capacity_links_removed: int = 0
    held_cases_skipped: tuple[str, ...] = field(default_factory=tuple)


def cleanup_case_data(transaction, *, now: datetime | None = None,
                      audited_holds: frozenset[str] = frozenset()) -> CleanupSummary:
    """One pass over every shelf, on the caller's transaction.

    `audited_holds` is the explicit, already-audited list of case ids under a
    legal or security hold. It is an argument, not a config flag: a hold is a
    decision somebody recorded, and passing it in keeps the record next to the
    person who made it.
    """
    now = now or datetime.now(timezone.utc)

    expired_access = transaction.purge_expired_access_sessions(now=now)
    expired_idempotency = transaction.purge_expired_idempotency(now=now)
    expired_challenges = transaction.purge_expired_contact_challenges(now=now)

    contacts = transaction.redact_closed_case_contacts(
        closed_before=now - CONTACT_RETENTION
    )
    payloads, held = transaction.redact_private_payloads(
        closed_before=now - PRIVATE_EVIDENCE_RETENTION,
        excluded_case_ids=tuple(sorted(audited_holds)),
    )
    delinked = transaction.deidentify_capacity_events(
        observed_before=now - LINEAGE_RETENTION
    )

    return CleanupSummary(
        expired_access_sessions=expired_access,
        expired_idempotency=expired_idempotency,
        expired_challenges=expired_challenges,
        contacts_redacted=contacts,
        private_payloads_redacted=payloads,
        capacity_links_removed=delinked,
        held_cases_skipped=tuple(held),
    )
