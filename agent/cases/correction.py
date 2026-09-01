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

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import datetime

from .audit import safe_case_projection
from .domain import (
    CaseProblem,
    CasePhase,
    CorrectionOutcome,
    EvidenceLevel,
    PromiseHealth,
    RiskClass,
    holds_authority,
)
from .queue_policy import WorkItemDraft
from .service import CORRECTABLE_FIELD_PATHS
from .store import CorrectionEvidenceDraft
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
    """In scope, effective, observed and unexpired at the decision boundary."""
    if type(now) is not datetime or now.tzinfo is None:
        raise ValueError("evidence_timestamp_timezone_required")

    def usable(record: EvidenceRecord) -> bool:
        try:
            return bool(
                record.source_scope == required_scope
                and record.observed_at.tzinfo is not None
                and record.effective_at.tzinfo is not None
                and record.observed_at <= now
                and record.effective_at <= now
                and (record.expires_at is None or (
                    record.expires_at.tzinfo is not None and record.expires_at > now
                ))
            )
        except (AttributeError, TypeError):
            return False

    return tuple(
        record
        for record in records
        if usable(record)
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
    required_scope: str | None = None


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
    revision: int | None = None
    outbox_event_id: str | None = None


_EVIDENCE_BEARING = frozenset({CorrectionOutcome.CORRECTED, CorrectionOutcome.CONFIRMED_CURRENT})


def requires_public_change(decision: DecisionOutcome) -> bool:
    """Accepted means a public change is owed, not that anything was published."""
    return decision.outcome_code is CorrectionOutcome.CORRECTED


def _require_decision_basics(command: DecideItemCommand) -> str:
    """Guard đầu vào theo ĐÚNG thứ tự reject cũ — mã lỗi đầu tiên là hợp đồng."""
    if command.outcome_code not in TERMINAL_OUTCOMES:
        raise _reject("unknown_correction_outcome", "That outcome is not offered.")
    scopes = set(getattr(command.actor, "scopes", ()) or ())
    if not holds_authority(scopes, DECIDE_SCOPE):
        raise _reject("decide_scope_required", "You cannot decide correction items.", status=403)
    reason = command.reason_code
    if type(reason) is not str or not reason.strip() or len(reason) > MAX_REASON_LENGTH:
        raise _reject("decision_reason_required", "A bounded reason code is required.", status=400)
    if command.outcome_code is CorrectionOutcome.DUPLICATE_LINKED and not command.duplicate_of:
        raise _reject("duplicate_link_required", "Name the case this duplicates.", status=400)
    return reason


def _require_decision_support(command: DecideItemCommand, maker: str) -> None:
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


def _normalize_decision_command(
    command: DecideItemCommand, *, now: datetime, required_scope: str | None = None,
) -> DecideItemCommand:
    _require_decision_basics(command)
    maker = getattr(command.actor, "actor_ref", "unknown")
    if command.evidence:
        scope = required_scope if required_scope is not None else command.required_scope
        if not scope:
            raise _reject("evidence_scope_required", "A decision needs an evidence scope.", status=400)
        usable = usable_evidence(tuple(command.evidence), now=now, required_scope=scope)
        if command.outcome_code in _EVIDENCE_BEARING and not usable:
            raise _reject(
                "evidence_not_usable",
                "No evidence matches the required scope and decision time window.",
                status=409,
            )
        command = replace(command, evidence=usable)
    _require_decision_support(command, maker)
    return command


def validate_decision(
    command: DecideItemCommand, *, now: datetime, required_scope: str | None = None
) -> DecisionOutcome:
    command = _normalize_decision_command(command, now=now, required_scope=required_scope)
    reason = command.reason_code
    maker = getattr(command.actor, "actor_ref", "unknown")

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
    revision: int | None = None
    outbox_event_id: str | None = None


# The plan's locked type name for an immutable change bundle.
CorrectionChangeSet = ChangeSetDraft


def live_value_at(values: dict, field_path: str):
    """What the entry actually says at `field_path`, traversing dotted paths.

    Same reading agent/public_api.py does for legacy reports. The inverse patch
    is an undo, and an undo built from anything but the observed value is a
    guess dressed as a record.
    """
    node = values
    for part in field_path.split("."):
        node = node.get(part) if isinstance(node, dict) else None
        if node is None:
            return None
    return node


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

    _require_coherent_changes(draft)

    if all(change.before_value == change.after_value for change in draft.changes):
        raise _reject("change_set_is_a_no_op", "This change set would change nothing.")
    return draft


def _require_coherent_changes(draft: ChangeSetDraft) -> None:
    seen: set[str] = set()
    for change in draft.changes:
        if change.entity_id != draft.entity_id:
            raise _reject("change_set_spans_entities", "One change set, one entry.")
        if change.field_path not in CORRECTABLE_FIELD_PATHS:
            raise _reject("field_path_not_correctable", "That field cannot be corrected.")
        if change.field_path in seen:
            raise _reject("duplicate_change_field", "That field appears twice.")
        seen.add(change.field_path)


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


def _decision_command_digest(command: DecideItemCommand) -> str:
    value = {
        "case_id": command.case_id,
        "item_id": command.item_id,
        "outcome_code": getattr(command.outcome_code, "value", command.outcome_code),
        "reason_code": command.reason_code,
        "evidence_ids": [record.evidence_id for record in command.evidence],
        "risk_class": getattr(command.risk_class, "value", command.risk_class),
        "actor_ref": getattr(command.actor, "actor_ref", "unknown"),
        "reviewer_ref": command.reviewer_ref,
        "duplicate_of": command.duplicate_of,
        "required_scope": command.required_scope,
    }
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _build_command_digest(
    case_id: str, item_ids: tuple[str, ...], actor, expected_revision: int,
    evidence_refs: tuple[str, ...],
) -> str:
    value = {
        "case_id": case_id,
        "item_ids": sorted(str(item_id) for item_id in item_ids),
        "actor_ref": getattr(actor, "actor_ref", "unknown"),
        "expected_revision": expected_revision,
        "evidence_refs": list(evidence_refs),
    }
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _replay_receipt_payload(
    existing: dict | None, event_id: str, *, required: tuple[str, ...]
) -> dict:
    """Read only a complete committed outbox receipt for a replay."""
    if existing is None:
        raise _reject(
            "publication_receipt_missing",
            f"The committed receipt {event_id} is missing.",
        )
    if not isinstance(existing, Mapping):
        raise _reject(
            "publication_receipt_invalid",
            f"The committed receipt {event_id} is malformed.",
        )
    try:
        receipt = dict(existing)
    except (TypeError, ValueError):
        raise _reject(
            "publication_receipt_invalid",
            f"The committed receipt {event_id} is malformed.",
        )
    payload = receipt.get("payload")
    if not isinstance(payload, Mapping):
        raise _reject(
            "publication_receipt_invalid",
            f"The committed receipt {event_id} is incomplete.",
        )
    try:
        payload = dict(payload)
    except (TypeError, ValueError):
        raise _reject(
            "publication_receipt_invalid",
            f"The committed receipt {event_id} is malformed.",
        )
    if any(key not in payload for key in required):
        raise _reject(
            "publication_receipt_invalid",
            f"The committed receipt {event_id} is incomplete.",
        )
    return dict(payload)


def _require_receipt_text(payload: dict, key: str, event_id: str) -> str:
    value = payload.get(key)
    if type(value) is not str or not value:
        raise _reject(
            "publication_receipt_invalid",
            f"The committed receipt {event_id} has an invalid {key}.",
        )
    return value


def _require_receipt_risk_class(payload: dict, key: str, event_id: str) -> str:
    raw = _require_receipt_text(payload, key, event_id)
    try:
        return RiskClass(raw).value
    except (TypeError, ValueError):
        raise _reject(
            "publication_receipt_invalid",
            f"The committed receipt {event_id} has an invalid {key}.",
        )


def _require_receipt_revision(payload: dict, event_id: str) -> int:
    revision = payload.get("revision")
    if type(revision) is not int or revision < 1:
        raise _reject(
            "publication_receipt_invalid",
            f"The committed receipt {event_id} has an invalid revision.",
        )
    return revision


def _require_replay_mapping(payload: dict, key: str, event_id: str) -> dict:
    value = payload.get(key)
    if type(value) is not dict:
        raise _reject(
            "publication_receipt_invalid",
            f"The committed receipt {event_id} has an invalid {key}.",
        )
    return value


def _require_replay_refs(payload: dict, key: str, event_id: str) -> tuple[str, ...]:
    value = payload.get(key)
    if type(value) not in (list, tuple) or not value:
        raise _reject(
            "publication_receipt_invalid",
            f"The committed receipt {event_id} has invalid {key}.",
        )
    if any(type(ref) is not str or not ref for ref in value):
        raise _reject(
            "publication_receipt_invalid",
            f"The committed receipt {event_id} has invalid {key}.",
        )
    return tuple(value)


def _require_decided_payloads(payloads: tuple[dict, ...]) -> None:
    unruled = tuple(
        str(row["item_id"]) for row in payloads
        if row.get("outcome_code") != CorrectionOutcome.CORRECTED.value
    )
    if unruled:
        raise _reject(
            "correction_item_not_decided",
            "Every item in a change set needs a recorded ruling of 'corrected'.",
        )


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
    required_scope: str | None = None


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
    _validate_evidence_command(command, now)

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
    # Normalize once before deriving the idempotency digest. The receipt and a
    # lost-response retry must bind to the same usable evidence set.
    command = _normalize_decision_command(command, now=now)
    store = _store()
    with store.transaction() as transaction:
        snapshot = transaction.load_case(command.case_id, for_update=True)
        event_id = f"decision:{command.case_id}:{command.item_id}"
        existing = transaction.load_outbox_by_idempotency_key(event_id)
        if existing is not None:
            payload = _replay_receipt_payload(
                existing,
                event_id,
                required=(
                    "event_id", "case_id", "revision", "generation",
                    "correlation_id", "decision_digest", "ruling",
                ),
            )
            if payload["event_id"] != event_id or payload["case_id"] != command.case_id:
                raise _reject(
                    "publication_receipt_invalid",
                    f"The committed receipt {event_id} identifies another decision.",
                )
            _require_receipt_text(payload, "generation", event_id)
            _require_receipt_text(payload, "correlation_id", event_id)
            revision = _require_receipt_revision(payload, event_id)
            decision_digest = _require_receipt_text(payload, "decision_digest", event_id)
            if decision_digest != _decision_command_digest(command):
                raise _reject(
                    "decision_idempotency_conflict",
                    "That item already has a different persisted ruling.",
                )
            ruling = payload["ruling"]
            if type(ruling) is not dict:
                raise _reject(
                    "publication_receipt_invalid",
                    f"The committed receipt {event_id} has an invalid ruling.",
                )
            ruling_required = (
                "case_id", "item_id", "outcome_code", "reason_code", "refs",
                "decision_maker_ref", "reviewer_ref", "duplicate_of",
            )
            if any(key not in ruling for key in ruling_required):
                raise _reject(
                    "publication_receipt_invalid",
                    f"The committed receipt {event_id} has an incomplete ruling.",
                )
            if (
                type(ruling["case_id"]) is not str
                or ruling["case_id"] != command.case_id
                or type(ruling["item_id"]) is not str
                or ruling["item_id"] != command.item_id
            ):
                raise _reject(
                    "publication_receipt_invalid",
                    f"The committed receipt {event_id} identifies another item.",
                )
            try:
                outcome_code = CorrectionOutcome(ruling["outcome_code"])
            except (TypeError, ValueError):
                raise _reject(
                    "publication_receipt_invalid",
                    f"The committed receipt {event_id} has an invalid outcome.",
                )
            if outcome_code is not command.outcome_code:
                raise _reject(
                    "publication_receipt_invalid",
                    f"The committed receipt {event_id} disagrees with the command.",
                )
            reason_code = ruling["reason_code"]
            refs = ruling["refs"]
            maker = ruling["decision_maker_ref"]
            reviewer = ruling["reviewer_ref"]
            duplicate_of = ruling["duplicate_of"]
            if (
                type(reason_code) is not str
                or not reason_code.strip()
                or len(reason_code) > MAX_REASON_LENGTH
                or type(refs) not in (list, tuple)
                or any(type(ref) is not str or not ref for ref in refs)
                or type(maker) is not str
                or not maker
                or (reviewer is not None and (type(reviewer) is not str or not reviewer))
                or (duplicate_of is not None and (type(duplicate_of) is not str or not duplicate_of))
            ):
                raise _reject(
                    "publication_receipt_invalid",
                    f"The committed receipt {event_id} has malformed ruling fields.",
                )
            command_actor = getattr(command.actor, "actor_ref", None)
            if (
                reason_code.strip() != command.reason_code.strip()
                or maker != command_actor
                or reviewer != command.reviewer_ref
                or duplicate_of != command.duplicate_of
            ):
                raise _reject(
                    "publication_receipt_invalid",
                    f"The committed receipt {event_id} disagrees with the command.",
                )
            command_refs = tuple(
                record.evidence_id for record in command.evidence
                if type(getattr(record, "evidence_id", None)) is str
            )
            if (
                outcome_code in _EVIDENCE_BEARING and not refs
                or tuple(refs) != command_refs
            ):
                raise _reject(
                    "publication_receipt_invalid",
                    f"The committed receipt {event_id} disagrees with command evidence.",
                )
            return DecisionOutcome(
                case_id=ruling["case_id"],
                item_id=ruling["item_id"],
                outcome_code=outcome_code,
                reason_code=reason_code.strip(),
                evidence_refs=tuple(refs),
                decision_maker_ref=maker,
                reviewer_ref=reviewer,
                duplicate_of=duplicate_of,
                revision=revision,
                outbox_event_id=event_id,
            )

        decision = validate_decision(command, now=now)
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
        # Decisions are item-level records; the case revision advances when a
        # case transition occurs (for example, building a change set).
        updated = snapshot
        try:
            from control_plane.audit import AuditEvent, write_audit_and_outbox
        except ModuleNotFoundError:
            from agent.control_plane.audit import AuditEvent, write_audit_and_outbox

        write_audit_and_outbox(
            transaction,
            AuditEvent(
                event_id=event_id,
                actor_id=decision.decision_maker_ref,
                action="item_decided",
                resource_type="case",
                resource_id=command.case_id,
                reason=decision.reason_code,
                before=safe_case_projection(snapshot),
                after=safe_case_projection(updated),
                correlation_id=getattr(command.actor, "correlation_id", "correction"),
                revision=updated.current_revision,
                generation=str(updated.current_revision),
                occurred_at=now,
                actor_scopes=tuple(sorted(set(getattr(command.actor, "scopes", ()) or ()))),
                channel=getattr(command.actor, "channel", None),
                policy_revision=_policy_revision(),
            ),
            {
                "topic": "correction.updated",
                "idempotency_key": event_id,
                "available_at": now,
                "reason": "decided",
                "policy_revision": _policy_revision(),
                "decision_digest": _decision_command_digest(command),
                "ruling": {
                    "case_id": decision.case_id,
                    "item_id": decision.item_id,
                    "outcome_code": decision.outcome_code.value,
                    "reason_code": decision.reason_code,
                    "refs": list(decision.evidence_refs),
                    "decision_maker_ref": decision.decision_maker_ref,
                    "reviewer_ref": decision.reviewer_ref,
                    "duplicate_of": decision.duplicate_of,
                },
            },
        )
    return replace(decision, revision=updated.current_revision, outbox_event_id=event_id)


def _replay_existing_change_set(transaction, case_id: str, item_ids: tuple[str, ...],
                                actor, expected_revision: int,
                                evidence_refs: tuple[str, ...], snapshot) -> ChangeSetDraft | None:
    existing = transaction.load_change_set_for_items(case_id, item_ids)
    if existing is not None:
        if not isinstance(existing, Mapping):
            raise _reject(
                "publication_receipt_invalid",
                "The persisted change set marker is malformed.",
            )
        try:
            existing = dict(existing)
        except (TypeError, ValueError):
            raise _reject(
                "publication_receipt_invalid",
                "The persisted change set marker is malformed.",
            )
    if not existing or str(existing.get("apply_status")) not in {"pending", "applied"}:
        return None
    change_set_id = existing.get("change_set_id")
    if type(change_set_id) is not str or not change_set_id:
        raise _reject(
            "publication_receipt_invalid",
            "The persisted change set marker is malformed.",
        )
    event_id = f"notify:{change_set_id}:decided"
    receipt = transaction.load_outbox_by_idempotency_key(event_id)
    payload = _replay_receipt_payload(
        receipt,
        event_id,
        required=(
            "event_id", "case_id", "revision", "generation", "correlation_id",
            "change_set_id", "item_ids", "build_digest", "risk_class",
        ),
    )
    if payload["event_id"] != event_id or payload["case_id"] != case_id:
        raise _reject(
            "publication_receipt_invalid",
            f"The committed receipt {event_id} identifies another case.",
        )
    _require_receipt_text(payload, "generation", event_id)
    _require_receipt_text(payload, "correlation_id", event_id)
    revision = _require_receipt_revision(payload, event_id)
    if payload["change_set_id"] != change_set_id:
        raise _reject(
            "publication_receipt_invalid",
            f"The committed receipt {event_id} identifies another change set.",
        )
    receipt_item_ids = payload["item_ids"]
    if (
        type(receipt_item_ids) not in (list, tuple)
        or any(type(item_id) is not str or not item_id for item_id in receipt_item_ids)
        or tuple(sorted(receipt_item_ids)) != tuple(sorted(item_ids))
    ):
        raise _reject(
            "publication_receipt_invalid",
            f"The committed receipt {event_id} has invalid item linkage.",
        )
    expected_digest = _build_command_digest(
        case_id, item_ids, actor, expected_revision, evidence_refs,
    )
    persisted_digest = _require_receipt_text(payload, "build_digest", event_id)
    if persisted_digest != expected_digest:
        raise _reject(
            "change_set_idempotency_conflict",
            "That item selection already has a different persisted change set.",
        )
    persisted_case_id = existing.get("case_id")
    if type(persisted_case_id) is not str or persisted_case_id != case_id:
        raise _reject(
            "publication_receipt_invalid",
            f"The persisted change set {change_set_id} identifies another case.",
        )
    base_entity_revision = existing.get("base_entity_revision")
    if type(base_entity_revision) is not int or base_entity_revision < 1:
        raise _reject(
            "publication_receipt_invalid",
            f"The persisted change set {change_set_id} has an invalid base revision.",
        )
    before_patch = _require_replay_mapping(existing, "before_patch", event_id)
    after_patch = _require_replay_mapping(existing, "after_patch", event_id)
    risk_class = _require_receipt_risk_class(existing, "risk_class", event_id)
    receipt_risk_class = _require_receipt_risk_class(payload, "risk_class", event_id)
    if receipt_risk_class != risk_class:
        raise _reject(
            "publication_receipt_invalid",
            f"The committed receipt {event_id} disagrees with the persisted risk class.",
        )
    decision_maker_ref = _require_receipt_text(existing, "decision_maker_ref", event_id)
    persisted_evidence_refs = _require_replay_refs(existing, "evidence_refs", event_id)
    if persisted_evidence_refs != tuple(evidence_refs):
        raise _reject(
            "publication_receipt_invalid",
            f"The persisted change set {change_set_id} has unrelated evidence.",
        )
    reviewer_ref = existing.get("reviewer_ref")
    if reviewer_ref is not None and (type(reviewer_ref) is not str or not reviewer_ref):
        raise _reject(
            "publication_receipt_invalid",
            f"The persisted change set {change_set_id} has an invalid reviewer.",
        )
    try:
        entity_id, linked_item_ids = transaction.load_change_set_target(change_set_id)
    except (KeyError, TypeError, ValueError):
        raise _reject(
            "publication_receipt_invalid",
            f"The persisted change set {change_set_id} target is malformed.",
        )
    if (
        type(entity_id) is not str or not entity_id
        or type(linked_item_ids) is not tuple
        or any(type(item_id) is not str or not item_id for item_id in linked_item_ids)
        or tuple(sorted(linked_item_ids)) != tuple(sorted(item_ids))
    ):
        raise _reject(
            "publication_receipt_invalid",
            f"The persisted change set {change_set_id} target is malformed.",
        )
    fields_by_item = {}
    item_risks = {}
    for item in transaction.load_correction_item_payloads(case_id, linked_item_ids):
        if type(item) is not dict:
            raise _reject(
                "publication_receipt_invalid",
                f"The persisted change set {change_set_id} item payload is malformed.",
            )
        item_id = item.get("item_id")
        field_path = item.get("field_path")
        if type(item_id) is not str or not item_id or type(field_path) is not str or not field_path:
            raise _reject(
                "publication_receipt_invalid",
                f"The persisted change set {change_set_id} item payload is malformed.",
            )
        fields_by_item[item_id] = field_path
        item_risks[item_id] = _require_receipt_risk_class(item, "risk_class", event_id)
    if set(fields_by_item) != set(linked_item_ids):
        raise _reject(
            "publication_receipt_invalid",
            f"The persisted change set {change_set_id} item linkage is incomplete.",
        )
    expected_risk_class = max(item_risks.values(), key=lambda value: value)
    if expected_risk_class != risk_class:
        raise _reject(
            "publication_receipt_invalid",
            f"The persisted change set {change_set_id} risk class is not item-bound.",
        )
    if set(before_patch) != set(fields_by_item.values()) or set(after_patch) != set(fields_by_item.values()):
        raise _reject(
            "publication_receipt_invalid",
            f"The persisted change set {change_set_id} patches are incomplete.",
        )
    changes = tuple(
        ProposedChange(
            item_id=item_id,
            entity_id=entity_id,
            field_path=fields_by_item[item_id],
            before_value=before_patch[field_path],
            after_value=after_patch[field_path],
        )
        for item_id in linked_item_ids
        for field_path in (fields_by_item[item_id],)
    )
    return ChangeSetDraft(
        case_id=case_id,
        entity_id=entity_id,
        base_entity_revision=base_entity_revision,
        changes=changes,
        risk_class=risk_class,
        decision_maker_ref=decision_maker_ref,
        evidence_refs=persisted_evidence_refs,
        reviewer_ref=reviewer_ref,
        apply_status=str(existing["apply_status"]),
        revision=revision,
        outbox_event_id=event_id,
    )


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
        snapshot = transaction.load_case(case_id, for_update=True)
        requested_item_ids = tuple(sorted(set(str(item_id) for item_id in accepted_item_ids)))
        replay = _replay_existing_change_set(
            transaction, case_id, requested_item_ids, actor, expected_revision,
            evidence_refs, snapshot,
        )
        if replay is not None:
            return replay
        actor_ref = _require_lease(transaction, case_id, actor, now=now)
        if snapshot.current_revision != expected_revision:
            raise _reject("case_revision_conflict", "This case changed; reload it.")

        payloads = transaction.load_correction_item_payloads(case_id, tuple(accepted_item_ids))
        if len(payloads) != len(set(accepted_item_ids)):
            raise _reject("correction_item_not_found", "One of those items is not on this case.")

        # Nothing reaches the public entry without a ruling that says so. The
        # decide path weighs evidence, risk and recusal; without this check the
        # build path simply walked around all of it, and verification then
        # closed the case as a properly answered correction.
        _require_decided_payloads(payloads)

        entity_ids = {str(row["entity_id"]) for row in payloads}
        if len(entity_ids) != 1:
            raise _reject("change_set_spans_entities", "One change set, one entry.")
        entity_id = entity_ids.pop()

        # What the entry says now is ours to read, never the reporter's to
        # assert. The before-state becomes the inverse patch, so trusting their
        # transcription would mean a rollback republishing a string nobody
        # authored and nobody ever reviewed — the reported value is seen at no
        # other point in the system.
        live = transaction.load_entity_for_update(entity_id)
        changes = tuple(
            ProposedChange(
                item_id=str(row["item_id"]),
                entity_id=entity_id,
                field_path=str(row["field_path"]),
                before_value=live_value_at(live.values, str(row["field_path"])),
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
        try:
            from control_plane.audit import AuditEvent, write_audit_and_outbox
        except ModuleNotFoundError:
            from agent.control_plane.audit import AuditEvent, write_audit_and_outbox

        event_id = f"notify:{change_set_id}:decided"
        write_audit_and_outbox(
            transaction,
            AuditEvent(
                event_id=event_id,
                actor_id=actor_ref,
                action="change_set_built",
                resource_type="case",
                resource_id=case_id,
                reason="change_set_built",
                before=safe_case_projection(snapshot),
                after=safe_case_projection(updated),
                correlation_id=getattr(actor, "correlation_id", "correction"),
                revision=updated.current_revision,
                generation=str(updated.current_revision),
                occurred_at=now,
                actor_scopes=tuple(sorted(set(getattr(actor, "scopes", ()) or ()))),
                channel=getattr(actor, "channel", None),
                policy_revision=_policy_revision(),
            ),
            {
                "topic": "correction.updated",
                "idempotency_key": event_id,
                "available_at": now,
                "reason": "decided",
                "policy_revision": _policy_revision(),
                "change_set_id": change_set_id,
                "item_ids": list(accepted_item_ids),
                "risk_class": risk,
                "build_digest": _build_command_digest(
                    case_id, tuple(sorted(set(accepted_item_ids))), actor,
                    expected_revision, evidence_refs,
                ),
            },
        )
    return replace(
        draft,
        apply_status="pending",
        revision=updated.current_revision,
        outbox_event_id=event_id,
    )


def _validate_evidence_command(command: AddEvidenceCommand, now: datetime) -> None:
    if type(command.level) is not EvidenceLevel:
        raise _reject("invalid_evidence_level", "That evidence level is not offered.")
    if type(command.source_scope) is not str or not command.source_scope.strip():
        raise _reject("evidence_scope_required", "Evidence needs a source scope.", status=400)
    if command.required_scope is not None and command.source_scope != command.required_scope:
        raise _reject("evidence_scope_mismatch", "Evidence is outside the required scope.", status=400)
    _validate_evidence_time_bounds(command, now)


def _evidence_timestamps_are_aware(command: AddEvidenceCommand, now: datetime) -> bool:
    values = (command.observed_at, command.effective_at, command.expires_at, now)
    return all(value is None or (type(value) is datetime and value.tzinfo is not None) for value in values)


def _validate_evidence_time_bounds(command: AddEvidenceCommand, now: datetime) -> None:
    if not _evidence_timestamps_are_aware(command, now):
        raise _reject("evidence_timestamp_timezone_required", "Evidence timestamps need a timezone.", status=400)
    if command.observed_at > now:
        raise _reject("evidence_not_yet_observed", "Evidence cannot come from the future.")
    if command.effective_at > now:
        raise _reject("evidence_effective_at_future", "Evidence cannot become effective in the future.")
    _validate_evidence_expiry(command, now)


def _validate_evidence_expiry(command: AddEvidenceCommand, now: datetime) -> None:
    if command.expires_at is not None and command.expires_at < command.effective_at:
        raise _reject("evidence_expiry_order_invalid", "Evidence expiry precedes effectiveness.", status=400)
    if command.expires_at is not None and command.expires_at <= now:
        raise _reject("evidence_expired", "Evidence has already expired.", status=400)
