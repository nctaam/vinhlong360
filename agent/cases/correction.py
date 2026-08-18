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

from dataclasses import dataclass
from datetime import datetime

from .domain import CaseProblem, CorrectionOutcome, EvidenceLevel, RiskClass
from .service import CORRECTABLE_FIELD_PATHS

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
