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
    # `current_revision` là con số người báo phải gửi lại khi xin xét lại
    # (`expectedRevision`). Nó vắng mặt ở đây suốt từ đầu, nên client không có
    # cách nào biết giá trị — và nút "xin xét lại" 422 mọi lượt. Đây là số phiên
    # bản hồ sơ CỦA CHÍNH NGƯỜI ĐÓ, không phải từ vựng hậu trường.
    public_reference: str; received_at: datetime; current_step: str; waiting_for: str | None; next_action: str; next_update_at: datetime; promise_health: PromiseHealth; item_decisions: tuple[PublicItemDecision, ...]; item_publication_states: tuple[PublicItemPublication, ...]; review_path: str; current_revision: int
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
    outcome_code: str | None = None


@dataclass(frozen=True)
class PromiseClock:
    kind: str; started_at: datetime; due_at: datetime
    risk_at: datetime | None = None; observed_at: datetime | None = None
    health: PromiseHealth = PromiseHealth.ON_TRACK; policy_revision: str | None = None


@dataclass(frozen=True)
class ReviewCaseLink:
    review_case_id: str; status: ReviewCaseStatus


# Every ruling an editor can record, and what it means to the person who
# reported the mistake. Collapsing the six non-accepting outcomes into
# UNDETERMINED told anyone who was told no that they were still being
# considered — and, because the review action is only offered on a settled
# answer, took away the one control they had to contest it.
_DISPOSITION_BY_OUTCOME = {
    CorrectionOutcome.CORRECTED: DispositionFamily.ACTION_TAKEN,
    CorrectionOutcome.CONFIRMED_CURRENT: DispositionFamily.NO_ACTION,
    CorrectionOutcome.INSUFFICIENT_EVIDENCE: DispositionFamily.NO_ACTION,
    CorrectionOutcome.OUT_OF_SCOPE: DispositionFamily.NO_ACTION,
    CorrectionOutcome.UNABLE_TO_VERIFY: DispositionFamily.NO_ACTION,
    CorrectionOutcome.DUPLICATE_LINKED: DispositionFamily.DUPLICATE,
    CorrectionOutcome.WITHDRAWN_BY_REQUESTER: DispositionFamily.WITHDRAWN,
}


# A promise clock is only a promise if somebody looks at it. AT_RISK and
# BREACHED were in the vocabulary from the start and nothing in the system ever
# wrote either one: health was stamped ON_TRACK at intake, moved to RECOVERY by
# the two publication failure paths, and left there. So a reporter saw "Đúng
# hạn" beside an update date that had passed weeks earlier, and the operator
# queue — which ranks BREACHED first — never saw a late case at all.
AT_RISK_FRACTION = 0.8
# The promises a case is still keeping. `receipt` is excluded on purpose: its
# target is five seconds and the receipt is written in the same transaction as
# the case, so it is satisfied by construction and can never be outstanding.
# Counting it made every case read BREACHED five seconds after intake — telling
# every reporter we were already late, and handing a supervisor an escalation
# for every case ever filed.
LIVE_PROMISE_KINDS = frozenset({"triage", "update", "resolution"})


_HEALTH_RANK = {
    PromiseHealth.ON_TRACK: 0, PromiseHealth.RECOVERY: 1,
    PromiseHealth.AT_RISK: 2, PromiseHealth.BREACHED: 3,
}


def recorded_health(clocks) -> 'PromiseHealth':
    """What the stored clock rows already say, worst-first.

    There is no cases.promise_health column — a case's health has always been
    the worst of its clocks. Reading it in two places with two copies of the
    rank map is how the two answers start disagreeing.
    """
    return max(
        (PromiseHealth.ON_TRACK, *(clock.health for clock in clocks or ())),
        key=_HEALTH_RANK.__getitem__,
    )


def promise_health_at(clocks, now: datetime, *, recorded=None) -> 'PromiseHealth':
    """The health the clocks actually justify at `now`.

    RECOVERY wins when it is recorded: somebody observed a real failure and said
    so, which is a stronger statement than any arithmetic on a due date.
    """
    if recorded is PromiseHealth.RECOVERY:
        return PromiseHealth.RECOVERY
    worst = PromiseHealth.ON_TRACK
    for clock in clocks or ():
        if clock.kind not in LIVE_PROMISE_KINDS:
            continue
        if now >= clock.due_at:
            return PromiseHealth.BREACHED
        elapsed = (now - clock.started_at).total_seconds()
        window = (clock.due_at - clock.started_at).total_seconds()
        if window > 0 and elapsed / window >= AT_RISK_FRACTION:
            worst = PromiseHealth.AT_RISK
    return worst


def disposition_for(outcome_code: str | None) -> DispositionFamily:
    """The public family for a recorded ruling; UNDETERMINED only when none is."""
    if not outcome_code:
        return DispositionFamily.UNDETERMINED
    try:
        return _DISPOSITION_BY_OUTCOME[CorrectionOutcome(outcome_code)]
    except (KeyError, ValueError):
        # An outcome nobody mapped is a programming error. Saying "still being
        # looked at" would be a lie; saying nothing settled is at least true.
        return DispositionFamily.UNDETERMINED


# The domain speaks one authority vocabulary; a real AdminCP session carries
# another. Nothing issues `cases:work`, `cases:high_risk` or `cases:decide` —
# agent/admin_permissions.py grants only the six case scopes and, to superadmin,
# the wildcard — so the guards below rejected every operator who ever reached
# them, and a plain `in` test failed the wildcard too. The names stay (internal
# callers and tests use them); what each one MEANS is written down here once.
_AUTHORITY_ALIASES: dict[str, tuple[str, ...]] = {
    'cases:work': ('service.operator', 'case.supervisor'),
    # NOT case.supervisor: taking work off somebody and being cleared to touch
    # R2/R3 are separate authorities on purpose, and a test says so. This one
    # had no AdminCP name at all, so one was added to the registry rather than
    # borrowed from a neighbour.
    'cases:high_risk': ('case.high_risk',),
    'cases:decide': ('correction.decide',),
    'case.supervisor': (),
}


def holds_authority(scopes, authority: str) -> bool:
    """Does this actor hold `authority`, in either vocabulary?

    Deliberately not a widening: each internal name maps to the AdminCP scope
    that already means the same thing, and nothing else. The wildcard is
    honoured because superadmin genuinely carries it and nothing else.
    """
    held = set(scopes or ())
    if '*' in held or authority in held:
        return True
    return any(alias in held for alias in _AUTHORITY_ALIASES.get(authority, ()))


def review_relation(links: tuple[ReviewCaseLink, ...]) -> str:
    if not links:
        return 'none'
    statuses = {link.status for link in links}
    if ReviewCaseStatus.IN_PROGRESS in statuses:
        return 'under_review'
    if ReviewCaseStatus.REQUESTED in statuses:
        return 'review_requested'
    return 'review_completed'
