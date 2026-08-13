from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class _Values(str, Enum):
    def __str__(self) -> str:
        return self.value


class Channel(_Values):
    WEB = 'web'; PHONE = 'phone'; ZALO_HUMAN = 'zalo_human'; ZALO_AI_HANDOFF = 'zalo_ai_handoff'; EMAIL_TRANSCRIBED = 'email_transcribed'
class ServiceKind(_Values):
    CORRECTION = 'correction'; CLAIM = 'claim'; ACCOUNT_RECOVERY = 'account_recovery'; SAFETY_REPORT = 'safety_report'
class CasePhase(_Values):
    INTAKE = 'intake'; TRIAGE = 'triage'; INVESTIGATION = 'investigation'; DECISION = 'decision'; FULFILLMENT = 'fulfillment'; CLOSED = 'closed'
class CaseActivity(_Values):
    ACTIVE = 'active'; WAITING_ON_REQUESTER = 'waiting_on_requester'; WAITING_ON_EXTERNAL = 'waiting_on_external'
class DispositionFamily(_Values):
    UNDETERMINED = 'undetermined'; ACTION_TAKEN = 'action_taken'; NO_ACTION = 'no_action'; TRANSFERRED = 'transferred'; WITHDRAWN = 'withdrawn'; DUPLICATE = 'duplicate'
class PromiseHealth(_Values):
    ON_TRACK = 'on_track'; AT_RISK = 'at_risk'; BREACHED = 'breached'; RECOVERY = 'recovery'
class RiskClass(_Values):
    R0 = 'R0'; R1 = 'R1'; R2 = 'R2'; R3 = 'R3'
class EvidenceLevel(_Values):
    E0 = 'E0'; E1 = 'E1'; E2 = 'E2'; E3 = 'E3'; E4 = 'E4'
class CorrectionOutcome(_Values):
    CORRECTED = 'corrected'; CONFIRMED_CURRENT = 'confirmed_current'; INSUFFICIENT_EVIDENCE = 'insufficient_evidence'; OUT_OF_SCOPE = 'out_of_scope'; DUPLICATE_LINKED = 'duplicate_linked'; UNABLE_TO_VERIFY = 'unable_to_verify'; WITHDRAWN_BY_REQUESTER = 'withdrawn_by_requester'
class PublicationState(_Values):
    NOT_REQUIRED = 'not_required'; PENDING = 'pending'; APPLIED = 'applied'; VERIFIED = 'verified'; ROLLED_BACK = 'rolled_back'
class ReviewCaseStatus(_Values):
    REQUESTED = 'requested'; IN_PROGRESS = 'in_progress'; COMPLETED = 'completed'

@dataclass(frozen=True)
class PublicItemDecision:
    item_id: str; outcome: str | None; disposition_family: DispositionFamily
@dataclass(frozen=True)
class PublicItemPublication:
    item_id: str; state: PublicationState

@dataclass(frozen=True)
class ActorContext:
    actor_ref: str; channel: Channel; scopes: frozenset[str]; correlation_id: str
@dataclass(frozen=True)
class CommandEnvelope:
    idempotency_key: str; expected_revision: int | None; actor: ActorContext
@dataclass(frozen=True)
class WaitingContext:
    requester_request: str; safe_message: str; waiting_on_ref: str
    evidence_ref: str; next_review_at: datetime; started_at: datetime
@dataclass(frozen=True)
class CaseSnapshot:
    case_id: str; service_kind: ServiceKind; category: str; phase: CasePhase; activity: CaseActivity; disposition_family: DispositionFamily; domain_outcome: str | None; severity: str | None; reporter_privacy: str; owner_ref: str; current_revision: int; promise_policy_ref: str; created_at: datetime; updated_at: datetime; closed_at: datetime | None; promise_health: PromiseHealth = PromiseHealth.ON_TRACK; waiting: WaitingContext | None = None; promise_clocks: tuple['PromiseClock', ...] = ()
@dataclass(frozen=True)
class PublicCaseStatus:
    public_reference: str; received_at: datetime; current_step: str; waiting_for: str | None; next_action: str; next_update_at: datetime; promise_health: PromiseHealth; item_decisions: tuple[PublicItemDecision, ...]; item_publication_states: tuple[PublicItemPublication, ...]; review_path: str
@dataclass(frozen=True)
class CaseProblem:
    code: str; detail: str; status: int = 400


@dataclass(frozen=True)
class CorrectionItem:
    item_id: str; risk_class: RiskClass; evidence_level: EvidenceLevel
    accepted: bool = False; requires_public_change: bool = False
    publication_state: PublicationState = PublicationState.NOT_REQUIRED
    validated: bool = False; evidence_supplier_ref: str | None = None
    evidence_conflict: bool = False; publication_failed: bool = False
    rollback_failed: bool = False; privacy_security_safety_signal: bool = False
    entity_id: str | None = None; field_path: str | None = None
    reported_value: object | None = None; proposed_value: object | None = None
    base_entity_revision: int = 1; evidence_refs: tuple[str, ...] = ()
    decision_ref: str | None = None; changeset_ref: str | None = None


@dataclass(frozen=True)
class PromiseClock:
    kind: str; started_at: datetime; due_at: datetime
    risk_at: datetime | None = None; observed_at: datetime | None = None
    health: PromiseHealth = PromiseHealth.ON_TRACK; policy_revision: str | None = None


@dataclass(frozen=True)
class ReviewCaseLink:
    review_case_id: str; status: ReviewCaseStatus


def review_relation(links: tuple[ReviewCaseLink, ...]) -> str:
    if not links:
        return 'none'
    statuses = {link.status for link in links}
    if ReviewCaseStatus.IN_PROGRESS in statuses:
        return 'under_review'
    if ReviewCaseStatus.REQUESTED in statuses:
        return 'review_requested'
    return 'review_completed'
