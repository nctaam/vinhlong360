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

@dataclass(frozen=True)
class ItemDecision:
    item_id: str; outcome: str | None; disposition_family: DispositionFamily
@dataclass(frozen=True)
class ItemPublication:
    item_id: str; state: PublicationState

@dataclass(frozen=True)
class ActorContext:
    actor_ref: str; channel: Channel; scopes: frozenset[str]; correlation_id: str
@dataclass(frozen=True)
class CommandEnvelope:
    idempotency_key: str; expected_revision: int | None; actor: ActorContext
@dataclass(frozen=True)
class CaseSnapshot:
    case_id: str; service_kind: ServiceKind; category: str; phase: CasePhase; activity: CaseActivity; disposition_family: DispositionFamily; domain_outcome: str | None; severity: str | None; reporter_privacy: str; owner_ref: str; current_revision: int; promise_policy_ref: str; created_at: datetime; updated_at: datetime; closed_at: datetime | None
@dataclass(frozen=True)
class PublicCaseStatus:
    public_reference: str; received_at: datetime; current_step: str; waiting_for: str | None; next_action: str; next_update_at: datetime; promise_health: PromiseHealth; item_decisions: tuple[ItemDecision, ...]; item_publication_states: tuple[ItemPublication, ...]; review_path: str
@dataclass(frozen=True)
class CaseProblem:
    code: str; detail: str; status: int = 400
