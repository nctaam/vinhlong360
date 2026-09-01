"""Publishing a decided correction onto the live entry, and proving it landed.

Three separations carry this module.

`applied` and `verified` are different facts. Applying writes the entry inside
one transaction; verifying goes and looks at what the public actually gets back
and compares it to what was written. Only the second can close a case as
corrected, because only the second is evidence rather than intent.

Every participant of an apply — the entity row and its revision, the entity
change audit, the change set's state, the case transition, the case audit and
the notification intent — commits on one connection. A half-published
correction is a public claim nobody decided to make, and it would be discovered
by a reader rather than by us.

Failure is never terminal. A projection that does not match keeps the case in
fulfilment, marks the promise, raises an escalation and schedules the next
update. Rollback replays the stored inverse patch, and only while the revision
it applied is still the revision on the entry; anything else fails closed rather
than guessing which of two changes to undo.

`attributes.verifiedAt` is not publishable. It says a person checked the entry
on the ground, and it moves only through the separate verification command that
carries that authority — never as a side effect of correcting a phone number.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from .audit import CaseAuditDraft, safe_case_projection
from .domain import (
    CaseProblem,
    CasePhase,
    CorrectionOutcome,
    DispositionFamily,
    PromiseHealth,
    PublicationState,
)
from .transitions import TransitionDraft

APPLY_SCOPE = "publication.apply"
VERIFY_SCOPE = "publication.verify"
REVIEW_SCOPE = "truth.review"
INDEPENDENT_REVIEW_RISK = frozenset({"R3"})
VERIFICATION_MARKER = "verifiedAt"
# How long the reporter waits for the next word after a projection check fails.
RECOVERY_NEXT_UPDATE = timedelta(hours=24)


class PublicationRejected(ValueError):
    def __init__(self, problem: CaseProblem) -> None:
        super().__init__(problem.code)
        self.problem = problem


def _reject(code: str, detail: str, status: int = 409) -> PublicationRejected:
    return PublicationRejected(CaseProblem(code=code, detail=detail, status=status))


_DATABASE = None
_CRYPTO = None
_POLICY = None


def configure_case_publication(*, database=None, crypto=None, policy=None) -> None:
    global _DATABASE, _CRYPTO, _POLICY
    _DATABASE = database
    _CRYPTO = crypto
    _POLICY = policy


def _store():
    from .store import PostgresCaseStore

    return PostgresCaseStore(_DATABASE) if _DATABASE is not None else PostgresCaseStore()


def _policy_revision() -> str:
    return getattr(_POLICY, "revision", "correction-pilot-v1")


def _require_enabled() -> None:
    """The kill switch stops the site changing. It does not stop the promise.

    Intake, receipts, decisions and the audit trail all keep working with this
    off; only the step that edits what the public reads is withheld.
    """
    from config import settings

    if not getattr(settings, "CORRECTION_PUBLICATION_ENABLED", False):
        raise _reject(
            "publication_disabled", "Publishing corrections is currently switched off.",
            status=503,
        )


def _require_scope(actor, scope: str, code: str, detail: str) -> None:
    if scope not in set(getattr(actor, "scopes", ()) or ()):
        raise _reject(code, detail, status=403)


def _require_lease(transaction, case_id: str, actor, *, now: datetime) -> str:
    actor_ref = getattr(actor, "actor_ref", "unknown")
    if not transaction.actor_holds_lease(case_id, actor_ref, now=now):
        raise _reject(
            "active_lease_required", "Claim the publication work before applying it.",
            status=403,
        )
    return actor_ref


# ── Apply ──

@dataclass(frozen=True)
class ApplyChangeSetCommand:
    case_id: str
    change_set_id: str
    actor: object
    expected_case_revision: int
    expected_entity_revision: int


@dataclass(frozen=True)
class PublicationResult:
    change_set_id: str
    case_id: str
    entity_id: str
    entity_revision: int
    state: PublicationState
    applied_fields: tuple[str, ...]
    revision: int | None = None
    outbox_event_id: str | None = None


def _entity_patch(after_patch: dict, stored_attributes) -> dict:
    """Turn field paths into a patch the entity write boundary accepts.

    A nested path merges into the stored map rather than replacing it, so
    correcting a phone number cannot silently drop an address. The verification
    marker is restored from storage afterwards: it is not this command's to move,
    and merging is exactly where it could be carried along unnoticed.
    """
    stored = dict(stored_attributes or {})
    patch: dict = {}
    attributes: dict | None = None
    for path, value in sorted(after_patch.items()):
        if path.startswith("attributes."):
            key = path.split(".", 1)[1]
            if attributes is None:
                attributes = dict(stored)
            attributes[key] = value
        else:
            patch[path] = value
    if attributes is not None:
        if VERIFICATION_MARKER in stored:
            attributes[VERIFICATION_MARKER] = stored[VERIFICATION_MARKER]
        else:
            attributes.pop(VERIFICATION_MARKER, None)
        patch["attributes"] = attributes
    return patch


def _require_independent_review(transaction, row: dict, case_id: str,
                                actor_ref: str) -> None:
    """R3 changes the name of a place. One person is not enough to do that.

    Two proofs, both required: the change set names a reviewer who is not its
    maker, and somebody other than the maker has actually FINISHED the
    truth_review work the queue derived for this risk class. A name on the row
    is intent; a completed work item is the review having happened.
    """
    if str(row["risk_class"]) not in INDEPENDENT_REVIEW_RISK:
        return
    reviewer = row["reviewer_ref"]
    maker = row["decision_maker_ref"]
    if not reviewer or reviewer == maker or actor_ref == maker:
        raise _reject(
            "independent_review_required",
            "This risk class needs a second person to have reviewed it.",
            status=403,
        )
    finished_by = transaction.completed_work_assignees(case_id, "truth_review")
    if not any(assignee != maker for assignee in finished_by):
        raise _reject(
            "truth_review_required",
            "This risk class needs the truth review completed before publishing.",
            status=403,
        )


def apply_change_set(command: ApplyChangeSetCommand, *, now: datetime) -> PublicationResult:
    _require_enabled()
    _require_scope(command.actor, APPLY_SCOPE, "publication_scope_required",
                   "Applying a correction needs the publication scope.")
    store = _store()
    with store.transaction() as transaction:
        row = transaction.load_change_set(command.change_set_id, for_update=True)
        if str(row["case_id"]) != command.case_id:
            raise _reject("change_set_not_on_case", "That change set belongs to another case.")
        snapshot = transaction.load_case(command.case_id, for_update=True)
        if str(row["apply_status"]) == "applied":
            return _replay_apply(transaction, command, row, snapshot)
        if str(row["apply_status"]) != "pending":
            raise _reject("change_set_not_pending", "That change set was already decided.")
        actor_ref = _require_lease(transaction, command.case_id, command.actor, now=now)
        _require_independent_review(transaction, row, command.case_id, actor_ref)

        if snapshot.current_revision != command.expected_case_revision:
            raise _reject("case_revision_conflict", "This case changed; reload it.")

        entity_id, item_ids = transaction.load_change_set_target(command.change_set_id)
        entity = transaction.load_entity_for_update(entity_id)
        if (
            entity.revision != command.expected_entity_revision
            or entity.revision != int(row["base_entity_revision"])
        ):
            # The wording this correction was written against is already gone.
            raise _reject("entity_revision_moved", "That entry changed since the decision.")

        after_patch = dict(row["after_patch"] or {})
        write = transaction.apply_entity_patch(
            entity_id,
            _entity_patch(after_patch, entity.values.get("attributes")),
            expected_revision=entity.revision,
            actor=actor_ref,
            provenance="correction-apply",
        )
        transaction.set_change_set_apply_status(
            command.change_set_id, expected_status="pending", status="applied",
        )
        updated = transaction.update_case(
            snapshot.current_revision,
            replace(snapshot, current_revision=snapshot.current_revision + 1, updated_at=now),
        )
        transaction.append_transition(
            TransitionDraft(
                case_id=command.case_id,
                from_phase=snapshot.phase,
                to_phase=CasePhase.FULFILLMENT,
                from_revision=snapshot.current_revision,
                to_revision=updated.current_revision,
                actor_ref=actor_ref,
                reason_code="change_set_applied",
                policy_revision=_policy_revision(),
                correlation_id=getattr(command.actor, "correlation_id", "publication"),
                occurred_at=now,
                waiting=None,
            )
        )
        _write_audit_outbox(
            transaction, command, snapshot, updated, actor_ref,
            reason_code="change_set_applied",
            event_id=f"notify:{command.change_set_id}:applied",
            topic="correction.updated", now=now,
            descriptor={
                "entity_revision": write.revision,
                "applied_fields": list(sorted(after_patch)),
            },
        )
    from . import metrics as _metrics

    _metrics.observe("applied", channel="web", risk_class=str(row["risk_class"]),
                     case_id=command.case_id, now=now)
    return PublicationResult(
        change_set_id=command.change_set_id,
        case_id=command.case_id,
        entity_id=entity_id,
        entity_revision=write.revision,
        state=PublicationState.APPLIED,
        applied_fields=tuple(sorted(after_patch)),
        revision=updated.current_revision,
        outbox_event_id=f"notify:{command.change_set_id}:applied",
    )


def _replay_apply(transaction, command, row: dict, snapshot) -> PublicationResult:
    event_id = f"notify:{command.change_set_id}:applied"
    existing = transaction.load_outbox_by_idempotency_key(event_id)
    payload = _replay_payload(
        existing,
        event_id,
        required=("revision", "entity_revision", "applied_fields"),
    )
    entity_id, _ = transaction.load_change_set_target(command.change_set_id)
    return PublicationResult(
        change_set_id=command.change_set_id,
        case_id=command.case_id,
        entity_id=entity_id,
        entity_revision=int(payload["entity_revision"]),
        state=PublicationState.APPLIED,
        applied_fields=tuple(payload["applied_fields"]),
        revision=int(payload["revision"]),
        outbox_event_id=event_id,
    )


# ── Verification ──

@dataclass(frozen=True)
class VerifyProjectionCommand:
    case_id: str
    change_set_id: str
    actor: object


@dataclass(frozen=True)
class VerificationResult:
    change_set_id: str
    state: PublicationState
    verified: bool
    mismatches: tuple[str, ...]
    next_update_at: datetime | None = None
    revision: int | None = None
    outbox_event_id: str | None = None


def _read_path(projection: dict, path: str):
    node = projection
    for part in path.split("."):
        if not isinstance(node, dict):
            return None
        node = node.get(part)
    return node


def _compare_projection(projection, entity_id: str, after_patch: dict,
                        expected_revision: int) -> tuple[str, ...]:
    """What the reader is served, against what was written."""
    if not isinstance(projection, dict) or not projection:
        # No answer is not a pass. It tells us nothing about the page.
        return ("unreachable",)
    mismatches = []
    if str(projection.get("id") or "") != entity_id:
        mismatches.append("id")
    try:
        served_revision = int(projection.get("revision"))
    except (TypeError, ValueError):
        served_revision = None
    if served_revision != expected_revision:
        # The strongest signal available: a cache or prerender serving the copy
        # from before the apply fails here even when every value looks familiar.
        mismatches.append("revision")
    for path, value in sorted(after_patch.items()):
        if _read_path(projection, path) != value:
            mismatches.append(path)
    if not projection.get("source"):
        # A corrected entry that no longer says where it came from is not fixed.
        mismatches.append("source")
    return tuple(mismatches)


def _replay_verification_failure(transaction, command, snapshot, existing) -> VerificationResult:
    event_id = f"notify:{command.change_set_id}:verification_failed"
    payload = _replay_payload(existing, event_id, required=("revision", "mismatched"))
    raw_mismatches = payload["mismatched"]
    available_at = _verification_retry_at(existing)
    if available_at is None:
        raise _reject(
            "publication_receipt_invalid",
            "The persisted verification failure has no recovery deadline.",
        )
    return VerificationResult(
        change_set_id=command.change_set_id,
        state=PublicationState.APPLIED,
        verified=False,
        mismatches=tuple(str(item) for item in raw_mismatches),
        next_update_at=available_at,
        revision=int(payload["revision"]),
        outbox_event_id=event_id,
    )


def _verification_retry_at(existing: dict | None) -> datetime | None:
    if existing is None:
        return None
    payload = existing.get("payload")
    if isinstance(payload, dict) and payload.get("next_update_at"):
        return datetime.fromisoformat(str(payload["next_update_at"]))
    return existing.get("available_at")


def _replay_payload(existing: dict | None, event_id: str, *, required: tuple[str, ...]) -> dict:
    """Replay only a complete committed receipt; never fabricate response metadata."""
    if existing is None:
        raise _reject(
            "publication_receipt_missing",
            f"The committed publication receipt {event_id} is missing.",
        )
    payload = existing.get("payload")
    if not isinstance(payload, dict) or any(key not in payload for key in required):
        raise _reject(
            "publication_receipt_invalid",
            f"The committed publication receipt {event_id} is incomplete.",
        )
    return dict(payload)


def verify_public_projection(command: VerifyProjectionCommand, fetcher, *,
                             now: datetime) -> VerificationResult:
    _require_enabled()
    _require_scope(command.actor, VERIFY_SCOPE, "verification_scope_required",
                   "Checking the public copy needs the verification scope.")
    store = _store()
    with store.transaction() as transaction:
        row = transaction.load_change_set(command.change_set_id, for_update=True)
        if str(row["case_id"]) != command.case_id:
            raise _reject("change_set_not_on_case", "That change set belongs to another case.")
        if str(row["apply_status"]) != "applied":
            raise _reject("change_set_not_applied", "That change set has not been applied.")

        snapshot = transaction.load_case(command.case_id, for_update=True)
        if row.get("public_projection_verified_at") is not None:
            event_id = f"notify:{command.change_set_id}:verified"
            existing = transaction.load_outbox_by_idempotency_key(event_id)
            payload = _replay_payload(existing, event_id, required=("revision",))
            revision = int(payload["revision"])
            return VerificationResult(
                change_set_id=command.change_set_id,
                state=PublicationState.VERIFIED,
                verified=True,
                mismatches=(),
                revision=revision,
                outbox_event_id=event_id,
            )

        failure_event_id = f"notify:{command.change_set_id}:verification_failed"
        existing_failure = transaction.load_outbox_by_idempotency_key(failure_event_id)
        retry_at = _verification_retry_at(existing_failure)
        if existing_failure is not None and (retry_at is None or now < retry_at):
            return _replay_verification_failure(
                transaction, command, snapshot, existing_failure,
            )

        actor_ref = _require_lease(transaction, command.case_id, command.actor, now=now)

        entity_id, _items = transaction.load_change_set_target(command.change_set_id)
        after_patch = dict(row["after_patch"] or {})
        # Apply held the row locked and wrote base + 1, so that is the revision a
        # reader must be seeing if they are seeing this correction at all.
        expected_revision = int(row["base_entity_revision"]) + 1
        try:
            projection = fetcher(entity_id)
        except Exception:
            projection = None
        mismatches = _compare_projection(projection, entity_id, after_patch, expected_revision)

        if mismatches:
            if existing_failure is not None:
                # The stable failure receipt already owns this idempotency key;
                # preserve it rather than emitting a duplicate side effect.
                return _replay_verification_failure(
                    transaction, command, snapshot, existing_failure,
                )
            return _record_verification_failure(
                transaction, command, snapshot, actor_ref, mismatches, now=now
            )
        return _record_verification_success(
            transaction, command, snapshot, actor_ref, now=now
        )


def _record_verification_success(transaction, command, snapshot, actor_ref: str, *,
                                 now: datetime) -> VerificationResult:
    transaction.set_change_set_apply_status(
        command.change_set_id, expected_status="applied", status="applied", verified_at=now,
    )
    updated = transaction.update_case(
        snapshot.current_revision,
        replace(
            snapshot,
            phase=CasePhase.CLOSED,
            disposition_family=DispositionFamily.ACTION_TAKEN,
            domain_outcome=CorrectionOutcome.CORRECTED.value,
            current_revision=snapshot.current_revision + 1,
            updated_at=now,
            closed_at=now,
        ),
    )
    transaction.append_transition(
        TransitionDraft(
            case_id=command.case_id,
            from_phase=snapshot.phase,
            to_phase=CasePhase.CLOSED,
            from_revision=snapshot.current_revision,
            to_revision=updated.current_revision,
            actor_ref=actor_ref,
            reason_code="projection_verified",
            policy_revision=_policy_revision(),
            correlation_id=getattr(command.actor, "correlation_id", "publication"),
            occurred_at=now,
            waiting=None,
        )
    )
    _write_audit_outbox(
        transaction, command, snapshot, updated, actor_ref,
        reason_code="projection_verified",
        event_id=f"notify:{command.change_set_id}:verified",
        topic="correction.updated", now=now,
    )
    transaction.complete_work_item_of_kind(command.case_id, "publication", now=now)
    from . import metrics as _metrics

    # Two facts on purpose: the projection checked out, and the case finished.
    # On the caller's transaction: a second connection would block on the very
    # `cases` row this one has locked, and hang until the statement timeout.
    _metrics.observe_on(transaction, "verified", channel="web",
                        case_id=command.case_id, now=now)
    _metrics.observe_on(transaction, "completed", channel="web",
                        case_id=command.case_id, now=now)
    return VerificationResult(
        change_set_id=command.change_set_id,
        state=PublicationState.VERIFIED,
        verified=True,
        mismatches=(),
        revision=updated.current_revision,
        outbox_event_id=f"notify:{command.change_set_id}:verified",
    )


def _record_verification_failure(transaction, command, snapshot, actor_ref: str,
                                 mismatches: tuple[str, ...], *,
                                 now: datetime) -> VerificationResult:
    """Nothing terminal. The case keeps its promise and someone is told."""
    next_update_at = now + RECOVERY_NEXT_UPDATE
    transaction.set_promise_health(
        command.case_id, PromiseHealth.RECOVERY.value, observed_at=now
    )
    _write_audit_outbox(
        transaction, command, snapshot, snapshot, actor_ref,
        reason_code="projection_verification_failed",
        event_id=f"notify:{command.change_set_id}:verification_failed",
        topic="correction.updated", now=now, available_at=next_update_at,
        descriptor={
            "mismatched": list(mismatches),
            "next_update_at": next_update_at.isoformat(),
        },
    )
    from . import metrics as _metrics

    _metrics.observe_on(transaction, "recovery", channel="web",
                        case_id=command.case_id, now=now)
    return VerificationResult(
        change_set_id=command.change_set_id,
        state=PublicationState.APPLIED,
        verified=False,
        mismatches=mismatches,
        next_update_at=next_update_at,
        revision=snapshot.current_revision,
        outbox_event_id=f"notify:{command.change_set_id}:verification_failed",
    )


# ── Rollback ──

@dataclass(frozen=True)
class RollbackChangeSetCommand:
    case_id: str
    change_set_id: str
    actor: object
    reason_code: str


@dataclass(frozen=True)
class RollbackResult:
    change_set_id: str
    entity_id: str
    entity_revision: int
    state: PublicationState
    revision: int | None = None
    outbox_event_id: str | None = None


def rollback_change_set(command: RollbackChangeSetCommand, *,
                        now: datetime) -> RollbackResult:
    _require_enabled()
    _require_scope(command.actor, APPLY_SCOPE, "publication_scope_required",
                   "Undoing a correction needs the publication scope.")
    store = _store()
    drifted = False
    with store.transaction() as transaction:
        row = transaction.load_change_set(command.change_set_id, for_update=True)
        if str(row["case_id"]) != command.case_id:
            raise _reject("change_set_not_on_case", "That change set belongs to another case.")
        snapshot = transaction.load_case(command.case_id, for_update=True)
        if str(row["apply_status"]) == "rolled_back":
            return _replay_rollback(transaction, command, row, snapshot)
        if str(row["apply_status"]) != "applied":
            raise _reject("change_set_not_applied", "That change set is not on the entry.")
        actor_ref = _require_lease(transaction, command.case_id, command.actor, now=now)

        entity_id, _items = transaction.load_change_set_target(command.change_set_id)
        entity = transaction.load_entity_for_update(entity_id)
        applied_revision = int(row["base_entity_revision"]) + 1

        if entity.revision != applied_revision:
            # Somebody edited the entry after this correction landed. Replaying
            # the inverse now would discard their edit too, so this stops --
            # loudly, because a correction nobody can undo and nobody knows
            # about is worse than one that is merely stuck.
            _record_rollback_refusal(transaction, command, snapshot, actor_ref, now=now)
            drifted = True
        else:
            result = _undo(transaction, command, row, snapshot, entity, entity_id,
                           actor_ref, now=now)
    if drifted:
        raise _reject(
            "entity_drifted_after_apply",
            "That entry changed after this correction was published; undo it by hand.",
        )
    return result


def _undo(transaction, command, row, snapshot, entity, entity_id: str, actor_ref: str, *,
          now: datetime) -> RollbackResult:
    inverse = dict(row["inverse_patch"] or {})
    write = transaction.apply_entity_patch(
        entity_id,
        _entity_patch(inverse, entity.values.get("attributes")),
        expected_revision=entity.revision,
        actor=actor_ref,
        provenance="correction-rollback",
    )
    transaction.set_change_set_apply_status(
        command.change_set_id, expected_status="applied", status="rolled_back",
    )
    # The case cannot stay closed as corrected on a change that no longer exists.
    reopened = transaction.update_case(
        snapshot.current_revision,
        replace(
            snapshot,
            phase=CasePhase.FULFILLMENT,
            disposition_family=DispositionFamily.UNDETERMINED,
            domain_outcome=None,
            current_revision=snapshot.current_revision + 1,
            updated_at=now,
            closed_at=None,
        ),
    )
    transaction.append_transition(
        TransitionDraft(
            case_id=command.case_id,
            from_phase=snapshot.phase,
            to_phase=CasePhase.FULFILLMENT,
            from_revision=snapshot.current_revision,
            to_revision=reopened.current_revision,
            actor_ref=actor_ref,
            reason_code="change_set_rolled_back",
            policy_revision=_policy_revision(),
            correlation_id=getattr(command.actor, "correlation_id", "publication"),
            occurred_at=now,
            waiting=None,
        )
    )
    _write_audit_outbox(
        transaction, command, snapshot, reopened, actor_ref,
        reason_code=command.reason_code,
        action="change_set_rolled_back",
        event_id=f"notify:{command.change_set_id}:rolled_back",
        topic="correction.updated", now=now,
        descriptor={"entity_revision": write.revision},
    )
    return RollbackResult(
        change_set_id=command.change_set_id,
        entity_id=entity_id,
        entity_revision=write.revision,
        state=PublicationState.ROLLED_BACK,
        revision=reopened.current_revision,
        outbox_event_id=f"notify:{command.change_set_id}:rolled_back",
    )


def _replay_rollback(transaction, command, row: dict, snapshot) -> RollbackResult:
    event_id = f"notify:{command.change_set_id}:rolled_back"
    existing = transaction.load_outbox_by_idempotency_key(event_id)
    payload = _replay_payload(existing, event_id, required=("revision", "entity_revision"))
    entity_id, _ = transaction.load_change_set_target(command.change_set_id)
    return RollbackResult(
        change_set_id=command.change_set_id,
        entity_id=entity_id,
        entity_revision=int(payload["entity_revision"]),
        state=PublicationState.ROLLED_BACK,
        revision=int(payload["revision"]),
        outbox_event_id=event_id,
    )


def _record_rollback_refusal(transaction, command, snapshot, actor_ref: str, *,
                             now: datetime) -> None:
    transaction.set_promise_health(
        command.case_id, PromiseHealth.RECOVERY.value, observed_at=now
    )
    _write_audit_outbox(
        transaction, command, snapshot, snapshot, actor_ref,
        reason_code="rollback_refused_entity_drift",
        event_id=f"escalate:{command.change_set_id}:drift:{now.isoformat()}",
        topic="correction.escalated", now=now,
    )


def _audit(command, before, after, actor_ref: str, *, reason_code: str,
           now: datetime) -> CaseAuditDraft:
    return CaseAuditDraft(
        case_id=command.case_id,
        actor_ref=actor_ref,
        actor_scopes=tuple(sorted(set(getattr(command.actor, "scopes", ()) or ()))),
        channel=getattr(command.actor, "channel", None),
        reason_code=reason_code,
        policy_revision=_policy_revision(),
        correlation_id=getattr(command.actor, "correlation_id", "publication"),
        before_snapshot=safe_case_projection(before),
        after_snapshot=safe_case_projection(after),
        occurred_at=now,
    )


def _write_audit_outbox(transaction, command, before, after, actor_ref: str, *,
                        reason_code: str, event_id: str, topic: str,
                        action: str | None = None,
                        now: datetime, available_at: datetime | None = None,
                        descriptor: dict | None = None) -> None:
    try:
        from control_plane.audit import AuditEvent, write_audit_and_outbox
    except ModuleNotFoundError:
        from agent.control_plane.audit import AuditEvent, write_audit_and_outbox

    revision = int(after.current_revision)
    write_audit_and_outbox(
        transaction,
        AuditEvent(
            event_id=event_id,
            actor_id=actor_ref,
            action=action or reason_code,
            resource_type="case",
            resource_id=command.case_id,
            reason=reason_code,
            before=safe_case_projection(before),
            after=safe_case_projection(after),
            correlation_id=getattr(command.actor, "correlation_id", "publication"),
            revision=revision,
            generation=str(revision),
            occurred_at=now,
            actor_scopes=tuple(sorted(set(getattr(command.actor, "scopes", ()) or ()))),
            channel=getattr(command.actor, "channel", None),
            policy_revision=_policy_revision(),
        ),
        {
            "topic": topic,
            "idempotency_key": event_id,
            "available_at": available_at or now,
            "reason": reason_code,
            "policy_revision": _policy_revision(),
            **(descriptor or {}),
        },
    )
