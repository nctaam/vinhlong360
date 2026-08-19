"""Evidence, risk decisions and immutable change sets.

Three rules shape this module.

A level is a claim about where something came from, not a verdict. `E3` means
"an authoritative source said so", not "this is true": evidence still has to be
in scope, unexpired, observed before the decision, and free of conflict before
it can carry anything.

`accepted` is an item decision, never a case terminal state and never a
publication. Accepting produces a change set with `apply_status='pending'`; this
module never touches a live entity.

A change set is bound to exactly one entity at exactly one revision, and every
patch carries its own inverse so a rollback needs no guesswork.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from .audit import CaseAuditDraft, safe_case_projection
from .domain import (
    CaseProblem,
    CasePhase,
    Channel,
    CorrectionOutcome,
    EvidenceLevel,
    PromiseHealth,
    RiskClass,
)
from .queue_policy import WorkItemDraft
from .service import CORRECTABLE_FIELD_PATHS
from .store import CorrectionEvidenceDraft, OutboxDraft
from .transitions import TransitionDraft

DECIDE_SCOPE = "cases:decide"
MAX_REASON_LENGTH = 200
INDEPENDENT_SOURCES_REQUIRED = 2
AUTHORITATIVE_LEVELS = frozenset({EvidenceLevel.E3, EvidenceLevel.E4})
CORROBORATING_LEVELS = frozenset({EvidenceLevel.E2, EvidenceLevel.E3, EvidenceLevel.E4})
HIGH_RISK = frozenset({RiskClass.R2, RiskClass.R3})
MAKER_CHECKER_RISK = frozenset({RiskClass.R3})

TERMINAL_OUTCOMES = frozenset(
    {
        CorrectionOutcome.CORRECTED,
        CorrectionOutcome.CONFIRMED_CURRENT,
        CorrectionOutcome.INSUFFICIENT_EVIDENCE,
        CorrectionOutcome.OUT_OF_SCOPE,
        CorrectionOutcome.DUPLICATE_LINKED,
        CorrectionOutcome.UNABLE_TO_VERIFY,
        CorrectionOutcome.WITHDRAWN_BY_REQUESTER,
    }
)


class CorrectionRejected(ValueError):
    def __init__(self, problem: CaseProblem) -> None:
        super().__init__(problem.code)
        self.problem = problem


def _reject(code: str, detail: str, status: int = 409) -> CorrectionRejected:
    return CorrectionRejected(CaseProblem(code=code, detail=detail, status=status))


# ── Evidence ──

@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    case_id: str
    item_id: str | None
    level: EvidenceLevel
    source_scope: str
    author_ref: str
    observed_at: datetime
    effective_at: datetime
    expires_at: datetime | None = None
    source_ref: str | None = None
    asserted_value: str | None = None


def usable_evidence(
    records: tuple[EvidenceRecord, ...], *, now: datetime, required_scope: str
) -> tuple[EvidenceRecord, ...]:
    """In scope, unexpired, and observed before the decision — nothing about level."""
    return tuple(
        record
        for record in records
        if record.source_scope == required_scope
        and record.observed_at <= now
        and (record.expires_at is None or record.expires_at > now)
    )


def conflicting_sources(records: tuple[EvidenceRecord, ...]) -> bool:
    """Two sources asserting different values is a conflict, not a ranking problem."""
    asserted = {record.asserted_value for record in records if record.asserted_value is not None}
    return len(asserted) > 1


def _independent_sources(records: tuple[EvidenceRecord, ...]) -> int:
    return len({
        record.source_ref
        for record in records
        if record.level in CORROBORATING_LEVELS and record.source_ref
    })


@dataclass(frozen=True)
class CorrectionRuling:
    supported: bool
    reason_code: str | None = None

    @classmethod
    def for_risk(
        cls,
        records: tuple[EvidenceRecord, ...],
        risk: RiskClass,
        *,
        decision_maker_ref: str,
    ) -> "CorrectionRuling":
        if conflicting_sources(records):
            return cls(False, "evidence_conflict")
        if risk not in HIGH_RISK:
            return cls(bool(records), None if records else "insufficient_evidence_level")
        # Somebody other than the decision maker must have put a usable piece on
        # the record, so a decision cannot rest only on its author's own filing.
        if not any(
            record.author_ref != decision_maker_ref and record.level in CORROBORATING_LEVELS
            for record in records
        ):
            return cls(False, "author_recusal_required")
        if any(record.level in AUTHORITATIVE_LEVELS for record in records):
            return cls(True, None)
        if _independent_sources(records) >= INDEPENDENT_SOURCES_REQUIRED:
            return cls(True, None)
        if not any(record.level in CORROBORATING_LEVELS for record in records):
            return cls(False, "insufficient_evidence_level")
        return cls(False, "independent_source_required")


def supports_risk(
    records: tuple[EvidenceRecord, ...], risk: RiskClass, *, decision_maker_ref: str
) -> bool:
    return CorrectionRuling.for_risk(records, risk, decision_maker_ref=decision_maker_ref).supported


# ── Decisions ──

@dataclass(frozen=True)
class DecideItemCommand:
    case_id: str
    item_id: str
    outcome_code: CorrectionOutcome
    reason_code: str
    evidence: tuple[EvidenceRecord, ...]
    risk_class: RiskClass
    actor: object
    reviewer_ref: str | None = None
    duplicate_of: str | None = None


@dataclass(frozen=True)
class DecisionOutcome:
    case_id: str
    item_id: str
    outcome_code: CorrectionOutcome
    reason_code: str
    evidence_refs: tuple[str, ...]
    decision_maker_ref: str
    reviewer_ref: str | None
    duplicate_of: str | None


_EVIDENCE_BEARING = frozenset({CorrectionOutcome.CORRECTED, CorrectionOutcome.CONFIRMED_CURRENT})


def requires_public_change(decision: DecisionOutcome) -> bool:
    """Accepted means a public change is owed, not that anything was published."""
    return decision.outcome_code is CorrectionOutcome.CORRECTED


def validate_decision(command: DecideItemCommand, *, now: datetime) -> DecisionOutcome:
    if command.outcome_code not in TERMINAL_OUTCOMES:
        raise _reject("unknown_correction_outcome", "That outcome is not offered.")
    scopes = set(getattr(command.actor, "scopes", ()) or ())
    if DECIDE_SCOPE not in scopes:
        raise _reject("decide_scope_required", "You cannot decide correction items.", status=403)
    reason = command.reason_code
    if type(reason) is not str or not reason.strip() or len(reason) > MAX_REASON_LENGTH:
        raise _reject("decision_reason_required", "A bounded reason code is required.", status=400)
    if command.outcome_code is CorrectionOutcome.DUPLICATE_LINKED and not command.duplicate_of:
        raise _reject("duplicate_link_required", "Name the case this duplicates.", status=400)

    maker = getattr(command.actor, "actor_ref", "unknown")
    if command.outcome_code in _EVIDENCE_BEARING:
        if not command.evidence:
            raise _reject("evidence_lineage_required", "A decision needs its evidence.", status=400)
        if command.risk_class in MAKER_CHECKER_RISK and (
            not command.reviewer_ref or command.reviewer_ref == maker
        ):
            raise _reject("maker_checker_required", "This risk class needs a second person.")
        ruling = CorrectionRuling.for_risk(
            command.evidence, command.risk_class, decision_maker_ref=maker
        )
        if not ruling.supported:
            raise _reject(ruling.reason_code or "insufficient_evidence_level",
                          "The evidence does not carry this decision.")
    elif command.risk_class in MAKER_CHECKER_RISK and command.reviewer_ref == maker:
        raise _reject("maker_checker_required", "This risk class needs a second person.")

    return DecisionOutcome(
        case_id=command.case_id,
        item_id=command.item_id,
        outcome_code=command.outcome_code,
        reason_code=reason.strip(),
        evidence_refs=tuple(record.evidence_id for record in command.evidence),
        decision_maker_ref=maker,
        reviewer_ref=command.reviewer_ref,
        duplicate_of=command.duplicate_of,
    )


# ── Change sets ──

@dataclass(frozen=True)
class ProposedChange:
    item_id: str
    entity_id: str
    field_path: str
    before_value: object
    after_value: object


@dataclass(frozen=True)
class ChangeSetDraft:
    case_id: str
    entity_id: str
    base_entity_revision: int
    changes: tuple[ProposedChange, ...]
    risk_class: str
    decision_maker_ref: str
    evidence_refs: tuple[str, ...]
    reviewer_ref: str | None = None
    apply_status: str = "pending"


# The plan's locked type name for an immutable change bundle.
CorrectionChangeSet = ChangeSetDraft


def build_patches(draft: ChangeSetDraft) -> tuple[dict, dict, dict]:
    """Before, after, and the inverse that undoes after without recomputation."""
    before = {change.field_path: change.before_value for change in draft.changes}
    after = {change.field_path: change.after_value for change in draft.changes}
    return before, after, dict(before)


def validate_change_set(
    draft: ChangeSetDraft, *, current_entity_revision: int, now: datetime
) -> ChangeSetDraft:
    if not draft.changes:
        raise _reject("change_set_is_empty", "A change set needs at least one change.")
    if not draft.evidence_refs:
        raise _reject("evidence_lineage_required", "A change set needs its evidence.", status=400)
    if draft.base_entity_revision != current_entity_revision:
        # The captured before-state is stale; re-reading is the caller's job.
        raise _reject("entity_revision_moved", "That entry changed since the decision.")
    if draft.risk_class in {"R3"} and (
        not draft.reviewer_ref or draft.reviewer_ref == draft.decision_maker_ref
    ):
        raise _reject("maker_checker_required", "This risk class needs a second person.")

    seen: set[str] = set()
    for change in draft.changes:
        if change.entity_id != draft.entity_id:
            raise _reject("change_set_spans_entities", "One change set, one entry.")
        if change.field_path not in CORRECTABLE_FIELD_PATHS:
            raise _reject("field_path_not_correctable", "That field cannot be corrected.")
        if change.field_path in seen:
            raise _reject("duplicate_change_field", "That field appears twice.")
        seen.add(change.field_path)

    if all(change.before_value == change.after_value for change in draft.changes):
        raise _reject("change_set_is_a_no_op", "This change set would change nothing.")
    return draft


# ── Persistence ──
#
# Every command below validates first and only then opens a transaction, so a
# refusal never leaves a partial write behind. None of them touches an entity.

_DATABASE = None
_CRYPTO = None
_POLICY = None


def configure_case_correction(*, database=None, crypto=None, policy=None) -> None:
    global _DATABASE, _CRYPTO, _POLICY
    _DATABASE = database
    _CRYPTO = crypto
    _POLICY = policy


def _store():
    from .store import PostgresCaseStore

    return PostgresCaseStore(_DATABASE) if _DATABASE is not None else PostgresCaseStore()


def _crypto():
    if _CRYPTO is None:
        raise RuntimeError("case_correction_not_configured")
    return _CRYPTO


def _policy_revision() -> str:
    return getattr(_POLICY, "revision", "correction-pilot-v1")


def _require_lease(transaction, case_id: str, actor, *, now: datetime) -> str:
    """An action is only allowed while its author is holding the work."""
    actor_ref = getattr(actor, "actor_ref", "unknown")
    if not transaction.actor_holds_lease(case_id, actor_ref, now=now):
        raise _reject(
            "active_lease_required",
            "Claim the work item before recording anything on this case.",
            status=403,
        )
    return actor_ref


@dataclass(frozen=True)
class AddEvidenceCommand:
    case_id: str
    item_id: str | None
    level: EvidenceLevel
    source_scope: str
    source_ref: str | None
    descriptor: dict
    content: str | None
    actor: object
    observed_at: datetime
    effective_at: datetime
    expires_at: datetime | None = None
    asserted_value: str | None = None


def _evidence_descriptor(command: AddEvidenceCommand) -> dict:
    """Everything a later decision needs to judge this evidence, kept with it.

    The table has columns for the level and the source reference only. Scope and
    the three timestamps decide whether evidence is in scope, observed before the
    ruling and still unexpired -- so leaving them in memory meant a decision could
    never be re-checked, or made at all, from what was written down.

    Content stays out. It is private and lives encrypted in its own column; this
    is the descriptor, and descriptors are readable.
    """
    descriptor = dict(command.descriptor or {})
    descriptor.update({
        "source_scope": command.source_scope,
        "observed_at": command.observed_at.isoformat(),
        "effective_at": command.effective_at.isoformat(),
        "expires_at": command.expires_at.isoformat() if command.expires_at else None,
        "asserted_value": command.asserted_value,
    })
    return descriptor


def load_evidence_records(case_id: str, item_id: str | None = None) -> tuple[EvidenceRecord, ...]:
    """Rebuild what was written down, so a ruling can be judged on it later."""
    store = _store()
    with store.transaction() as transaction:
        rows = transaction.load_correction_evidence(case_id, item_id)
    return tuple(
        EvidenceRecord(
            evidence_id=str(row["evidence_id"]),
            case_id=str(row["case_id"]),
            item_id=str(row["item_id"]) if row["item_id"] else None,
            level=EvidenceLevel(row["evidence_level"]),
            source_scope=str((row["descriptor"] or {}).get("source_scope") or ""),
            author_ref=str(row["created_by_ref"]),
            observed_at=_moment((row["descriptor"] or {}).get("observed_at")),
            effective_at=_moment((row["descriptor"] or {}).get("effective_at")),
            expires_at=_moment((row["descriptor"] or {}).get("expires_at")),
            source_ref=row["source_ref"],
            asserted_value=(row["descriptor"] or {}).get("asserted_value"),
        )
        for row in rows
    )


def _moment(value) -> datetime | None:
    if not value:
        return None
    return value if type(value) is datetime else datetime.fromisoformat(str(value))


def add_evidence(command: AddEvidenceCommand, *, now: datetime) -> EvidenceRecord:
    if type(command.level) is not EvidenceLevel:
        raise _reject("invalid_evidence_level", "That evidence level is not offered.")
    if type(command.source_scope) is not str or not command.source_scope.strip():
        raise _reject("evidence_scope_required", "Evidence needs a source scope.", status=400)
    if command.observed_at > now:
        raise _reject("evidence_not_yet_observed", "Evidence cannot come from the future.")

    crypto = _crypto()
    store = _store()
    with store.transaction() as transaction:
        actor_ref = _require_lease(transaction, command.case_id, command.actor, now=now)
        evidence_ids = transaction.insert_correction_evidence(
            (
                CorrectionEvidenceDraft(
                    case_id=command.case_id,
                    item_id=command.item_id,
                    evidence_level=command.level,
                    source_ref=command.source_ref,
                    descriptor=_evidence_descriptor(command),
                    # The payload is a private artifact, never a public descriptor.
                    content_enc=(
                        crypto.encrypt_private_payload({"content": command.content})
                        if command.content is not None
                        else None
                    ),
                    created_by_ref=actor_ref,
                    created_at=now,
                ),
            )
        )
    return EvidenceRecord(
        evidence_id=evidence_ids[0],
        case_id=command.case_id,
        item_id=command.item_id,
        level=command.level,
        source_scope=command.source_scope,
        author_ref=actor_ref,
        observed_at=command.observed_at,
        effective_at=command.effective_at,
        expires_at=command.expires_at,
        source_ref=command.source_ref,
        asserted_value=command.asserted_value,
    )


def decide_item(command: DecideItemCommand, *, now: datetime) -> DecisionOutcome:
    """Validate the ruling first; a refused decision writes nothing at all."""
    decision = validate_decision(command, now=now)
    store = _store()
    with store.transaction() as transaction:
        _require_lease(transaction, command.case_id, command.actor, now=now)
        transaction.insert_decision(
            case_id=decision.case_id,
            item_id=decision.item_id,
            outcome_code=decision.outcome_code.value,
            reason_code=decision.reason_code,
            evidence_refs=decision.evidence_refs,
            decision_maker_ref=decision.decision_maker_ref,
            reviewer_ref=decision.reviewer_ref,
            policy_revision=_policy_revision(),
            decided_at=now,
        )
    return decision


def build_change_set(
    case_id: str,
    accepted_item_ids: tuple[str, ...],
    actor,
    expected_revision: int,
    *,
    evidence_refs: tuple[str, ...],
    now: datetime,
) -> ChangeSetDraft:
    """Accepting owes a public change; this records that debt, it does not pay it.

    The change set, its item linkage, the move to fulfilment, the publication
    work, the audit and the notification intent all commit together. The live
    entity is not touched here — publication is Task 12's decision, behind its
    own kill switch.
    """
    crypto = _crypto()
    store = _store()
    with store.transaction() as transaction:
        actor_ref = _require_lease(transaction, case_id, actor, now=now)
        snapshot = transaction.load_case(case_id, for_update=True)
        if snapshot.current_revision != expected_revision:
            raise _reject("case_revision_conflict", "This case changed; reload it.")

        payloads = transaction.load_correction_item_payloads(case_id, tuple(accepted_item_ids))
        if len(payloads) != len(set(accepted_item_ids)):
            raise _reject("correction_item_not_found", "One of those items is not on this case.")

        entity_ids = {str(row["entity_id"]) for row in payloads}
        if len(entity_ids) != 1:
            raise _reject("change_set_spans_entities", "One change set, one entry.")
        entity_id = entity_ids.pop()

        changes = tuple(
            ProposedChange(
                item_id=str(row["item_id"]),
                entity_id=entity_id,
                field_path=str(row["field_path"]),
                before_value=crypto.decrypt_private_payload(str(row["reported_value_enc"]))["value"],
                after_value=crypto.decrypt_private_payload(str(row["proposed_value_enc"]))["value"],
            )
            for row in payloads
        )
        risk = max((str(row["risk_class"]) for row in payloads), default="R0")
        draft = ChangeSetDraft(
            case_id=case_id,
            entity_id=entity_id,
            base_entity_revision=int(payloads[0]["base_entity_revision"]),
            changes=changes,
            risk_class=risk,
            decision_maker_ref=actor_ref,
            reviewer_ref=getattr(actor, "reviewer_ref", None),
            evidence_refs=tuple(evidence_refs),
        )
        live_revision = transaction.entity_revision(entity_id)
        if live_revision is None:
            raise _reject("correction_entity_unknown", "That entry is not published here.",
                          status=404)
        validate_change_set(draft, current_entity_revision=live_revision, now=now)

        before, after, inverse = build_patches(draft)
        change_set_id = transaction.insert_change_set(
            case_id=case_id,
            base_entity_revision=draft.base_entity_revision,
            before_patch=before,
            after_patch=after,
            inverse_patch=inverse,
            evidence_refs=draft.evidence_refs,
            policy_revision=_policy_revision(),
            risk_class=risk,
            decision_maker_ref=actor_ref,
            reviewer_ref=draft.reviewer_ref,
            created_at=now,
        )
        transaction.link_change_set_items(change_set_id, tuple(accepted_item_ids))

        updated = transaction.update_case(
            snapshot.current_revision,
            replace(
                snapshot,
                phase=CasePhase.FULFILLMENT,
                current_revision=snapshot.current_revision + 1,
                updated_at=now,
            ),
        )
        transaction.append_transition(
            TransitionDraft(
                case_id=case_id,
                from_phase=snapshot.phase,
                to_phase=CasePhase.FULFILLMENT,
                from_revision=snapshot.current_revision,
                to_revision=updated.current_revision,
                actor_ref=actor_ref,
                reason_code="change_set_built",
                policy_revision=_policy_revision(),
                correlation_id=getattr(actor, "correlation_id", "correction"),
                occurred_at=now,
                waiting=None,
            )
        )
        transaction.insert_work_items(
            (
                WorkItemDraft(
                    case_id=case_id, kind="publication", required_role="case_operator",
                    risk_class=RiskClass(risk), ready_at=now, received_at=now,
                    promise_health=PromiseHealth.ON_TRACK,
                ),
            )
        )
        transaction.append_audit(
            CaseAuditDraft(
                case_id=case_id,
                actor_ref=actor_ref,
                actor_scopes=tuple(sorted(set(getattr(actor, "scopes", ()) or ()))),
                channel=getattr(actor, "channel", Channel.WEB),
                reason_code="change_set_built",
                policy_revision=_policy_revision(),
                correlation_id=getattr(actor, "correlation_id", "correction"),
                before_snapshot=safe_case_projection(snapshot),
                after_snapshot=safe_case_projection(updated),
                occurred_at=now,
            )
        )
        transaction.enqueue_outbox(
            OutboxDraft(
                case_id=case_id,
                idempotency_key=f"notify:{change_set_id}:decided",
                topic="correction.updated",
                descriptor={"reason": "decided", "policy_revision": _policy_revision()},
                available_at=now,
            )
        )
    return replace(draft, apply_status="pending")
