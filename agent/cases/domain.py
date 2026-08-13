from dataclasses import dataclass
from enum import Enum

class _Values(str, Enum):
    def __str__(self): return self.value

class ServiceKind(_Values):
    CORRECTION='correction'; CLAIM='claim'; ACCOUNT_RECOVERY='account_recovery'; SAFETY_REPORT='safety_report'
class CasePhase(_Values):
    INTAKE='intake'; TRIAGE='triage'; INVESTIGATION='investigation'; DECISION='decision'; PUBLICATION='publication'; CLOSED='closed'
class CaseActivity(_Values):
    RECEIVED='received'; TRIAGED='triaged'; EVIDENCE_ADDED='evidence_added'; DECIDED='decided'; PUBLISHED='published'; VERIFIED='verified'; CLOSED='closed'
class DispositionFamily(_Values):
    CORRECTION='correction'; CONFIRMATION='confirmation'; INSUFFICIENT='insufficient'; OUT_OF_SCOPE='out_of_scope'; DUPLICATE='duplicate'; UNABLE_TO_VERIFY='unable_to_verify'; WITHDRAWN='withdrawn'
class PromiseHealth(_Values):
    ON_TRACK='on_track'; AT_RISK='at_risk'; BREACHED='breached'; RECOVERY='recovery'
class RiskClass(_Values):
    R0='R0'; R1='R1'; R2='R2'; R3='R3'
class EvidenceLevel(_Values):
    E0='E0'; E1='E1'; E2='E2'; E3='E3'; E4='E4'
class CorrectionOutcome(_Values):
    CORRECTED='corrected'; CONFIRMED_CURRENT='confirmed_current'; INSUFFICIENT_EVIDENCE='insufficient_evidence'; OUT_OF_SCOPE='out_of_scope'; DUPLICATE_LINKED='duplicate_linked'; UNABLE_TO_VERIFY='unable_to_verify'; WITHDRAWN_BY_REQUESTER='withdrawn_by_requester'
class PublicationState(_Values):
    NOT_REQUIRED='not_required'; PENDING='pending'; APPLIED='applied'; VERIFIED='verified'; ROLLED_BACK='rolled_back'

@dataclass(frozen=True)
class ActorContext:
    actor_ref: str; channel: str; scopes: frozenset[str]; correlation_id: str
@dataclass(frozen=True)
class CommandEnvelope:
    idempotency_key: str; expected_revision: int | None; actor: ActorContext
@dataclass(frozen=True)
class CaseSnapshot: public_reference: str; phase: CasePhase; revision: int = 0
@dataclass(frozen=True)
class PublicCaseStatus: public_reference: str; current_step: str; promise_health: PromiseHealth
@dataclass(frozen=True)
class CaseProblem: code: str; detail: str
