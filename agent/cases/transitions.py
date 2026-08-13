from dataclasses import dataclass, replace
from datetime import datetime

from .domain import (
    ActorContext, CaseActivity, CasePhase, CaseSnapshot, CorrectionItem, EvidenceLevel,
    CorrectionOutcome, DispositionFamily, PromiseClock, PromiseHealth,
    Channel, PublicationState, RiskClass, ServiceKind, WaitingContext,
)
from .policy import CasePolicy


class TransitionRejected(ValueError):
    pass


@dataclass(frozen=True)
class CaseTransitionCommand:
    phase: CasePhase; activity: CaseActivity; disposition_family: DispositionFamily
    domain_outcome: CorrectionOutcome | None; actor: ActorContext; reason_code: str
    expected_revision: int | None; requester_request: str | None = None
    safe_message: str | None = None; waiting_on_ref: str | None = None
    waiting_evidence_ref: str | None = None
    next_review_at: datetime | None = None


@dataclass(frozen=True)
class TransitionDraft:
    case_id: str; from_phase: CasePhase; to_phase: CasePhase; from_revision: int
    to_revision: int; actor_ref: str; reason_code: str; policy_revision: str
    correlation_id: str; occurred_at: datetime; waiting: WaitingContext | None


@dataclass(frozen=True)
class TransitionResult:
    snapshot: CaseSnapshot; transition: TransitionDraft


def promise_health(clock: PromiseClock, *, now: datetime) -> PromiseHealth:
    _validate_clock(clock, now)
    if now >= clock.due_at:
        return PromiseHealth.BREACHED
    if clock.risk_at is not None and now >= clock.risk_at:
        return PromiseHealth.AT_RISK
    return clock.health


def _validate_audit(snapshot: CaseSnapshot, command: CaseTransitionCommand) -> None:
    if snapshot.phase is CasePhase.CLOSED:
        raise TransitionRejected('closed_case_immutable')
    if command.expected_revision != snapshot.current_revision:
        raise TransitionRejected('revision_conflict')
    if not command.actor.actor_ref or not command.actor.correlation_id or not command.reason_code:
        raise TransitionRejected('transition_audit_incomplete')


def _aware(value: object) -> bool:
    return isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None


def _validate_clock(clock: PromiseClock, now: datetime) -> None:
    if (not isinstance(clock, PromiseClock) or not isinstance(clock.health, PromiseHealth)
            or not _aware(now) or not _aware(clock.started_at) or not _aware(clock.due_at)
            or clock.started_at > clock.due_at
            or clock.risk_at is not None and (not _aware(clock.risk_at)
                                             or not clock.started_at <= clock.risk_at <= clock.due_at)
            or clock.observed_at is not None and not _aware(clock.observed_at)):
        raise TransitionRejected('invalid_case_time')


def _validate_contract(snapshot: CaseSnapshot, command: CaseTransitionCommand,
                       correction_items: tuple[CorrectionItem, ...], now: datetime) -> None:
    snapshot_values = (
        (snapshot.service_kind, ServiceKind), (snapshot.phase, CasePhase),
        (snapshot.activity, CaseActivity), (snapshot.disposition_family, DispositionFamily),
        (snapshot.promise_health, PromiseHealth),
    )
    command_values = (
        (command.phase, CasePhase), (command.activity, CaseActivity),
        (command.disposition_family, DispositionFamily),
    )
    outcomes = (snapshot.domain_outcome, command.domain_outcome)
    if (not all(isinstance(value, expected) for value, expected in snapshot_values + command_values)
            or any(outcome is not None and not isinstance(outcome, CorrectionOutcome) for outcome in outcomes)
            or not isinstance(command.actor, ActorContext)
            or not isinstance(command.actor.channel, Channel)
            or not _aware(now) or not _aware(snapshot.created_at) or not _aware(snapshot.updated_at)
            or snapshot.created_at > snapshot.updated_at or snapshot.updated_at > now
            or snapshot.closed_at is not None and (not _aware(snapshot.closed_at) or snapshot.closed_at > now)
            or not all(_valid_item(item) for item in correction_items)):
        raise TransitionRejected('invalid_case_contract')
    for clock in snapshot.promise_clocks:
        _validate_clock(clock, now)


def _valid_item(item: CorrectionItem) -> bool:
    return (isinstance(item, CorrectionItem) and isinstance(item.risk_class, RiskClass)
            and isinstance(item.evidence_level, EvidenceLevel)
            and isinstance(item.publication_state, PublicationState)
            and type(item.base_entity_revision) is int and item.base_entity_revision >= 1)


def _validate_phase_move(snapshot: CaseSnapshot, command: CaseTransitionCommand) -> None:
    allowed = {
        CasePhase.INTAKE: frozenset((CasePhase.INTAKE, CasePhase.TRIAGE)),
        CasePhase.TRIAGE: frozenset((CasePhase.TRIAGE, CasePhase.INVESTIGATION)),
        CasePhase.INVESTIGATION: frozenset((CasePhase.INVESTIGATION, CasePhase.DECISION)),
        CasePhase.DECISION: frozenset((CasePhase.DECISION, CasePhase.FULFILLMENT)),
        CasePhase.FULFILLMENT: frozenset((CasePhase.FULFILLMENT, CasePhase.CLOSED)),
    }
    if command.phase not in allowed[snapshot.phase]:
        raise TransitionRejected('illegal_phase_transition')


def _validate_waiting(command: CaseTransitionCommand, now: datetime) -> None:
    if command.phase is not CasePhase.CLOSED and command.activity is CaseActivity.WAITING_ON_REQUESTER and not (
        command.requester_request and command.safe_message and command.waiting_on_ref
        and command.waiting_evidence_ref
        and _aware(command.next_review_at) and command.next_review_at > now
    ):
        raise TransitionRejected('waiting_request_incomplete')


def _validate_terminal_close(snapshot: CaseSnapshot, command: CaseTransitionCommand,
                             items: tuple[CorrectionItem, ...]) -> None:
    if command.phase is not CasePhase.CLOSED:
        return
    if command.domain_outcome is CorrectionOutcome.CORRECTED and snapshot.phase is not CasePhase.FULFILLMENT:
        raise TransitionRejected('corrected_requires_fulfillment')
    if any(item.accepted and item.requires_public_change
           and (item.publication_failed or item.rollback_failed
                or item.publication_state is not PublicationState.VERIFIED) for item in items):
        code = 'publication_not_verified' if command.domain_outcome is CorrectionOutcome.CORRECTED else 'publication_recovery_required'
        raise TransitionRejected(code)


def _validate(snapshot: CaseSnapshot, command: CaseTransitionCommand,
              policy: CasePolicy, correction_items: tuple[CorrectionItem, ...], now: datetime) -> None:
    del policy
    _validate_contract(snapshot, command, correction_items, now)
    _validate_audit(snapshot, command)
    _validate_waiting(command, now)
    _validate_terminal_close(snapshot, command, correction_items)
    _validate_phase_move(snapshot, command)
    if command.phase is CasePhase.CLOSED and command.domain_outcome is None:
        raise TransitionRejected('terminal_outcome_required')


def transition_case(snapshot: CaseSnapshot, command: CaseTransitionCommand,
                    policy: CasePolicy, *, now: datetime,
                    correction_items: tuple[CorrectionItem, ...] = ()) -> TransitionResult:
    _validate(snapshot, command, policy, correction_items, now)
    closed_at = now if command.phase is CasePhase.CLOSED else None
    activity = CaseActivity.ACTIVE if command.phase is CasePhase.CLOSED else command.activity
    waiting = (WaitingContext(command.requester_request, command.safe_message, command.waiting_on_ref,
                              command.waiting_evidence_ref, command.next_review_at, now)
               if activity is CaseActivity.WAITING_ON_REQUESTER else None)
    next_snapshot = replace(
        snapshot, phase=command.phase, activity=activity,
        disposition_family=command.disposition_family, domain_outcome=command.domain_outcome,
        current_revision=snapshot.current_revision + 1, updated_at=now, closed_at=closed_at, waiting=waiting,
    )
    return TransitionResult(next_snapshot, TransitionDraft(
        snapshot.case_id, snapshot.phase, command.phase, snapshot.current_revision,
        next_snapshot.current_revision, command.actor.actor_ref, command.reason_code,
        policy.revision, command.actor.correlation_id, now, waiting,
    ))
