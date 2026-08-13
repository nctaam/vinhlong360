from dataclasses import dataclass, replace
from datetime import datetime

from .domain import (
    ActorContext, CaseActivity, CasePhase, CaseSnapshot, CorrectionItem,
    CorrectionOutcome, DispositionFamily, PromiseClock, PromiseHealth,
    PublicationState,
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
    correlation_id: str; occurred_at: datetime


@dataclass(frozen=True)
class TransitionResult:
    snapshot: CaseSnapshot; transition: TransitionDraft


def promise_health(clock: PromiseClock, *, now: datetime) -> PromiseHealth:
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


def _validate_waiting(command: CaseTransitionCommand) -> None:
    if command.activity is CaseActivity.WAITING_ON_REQUESTER and not (
        command.requester_request and command.safe_message and command.waiting_on_ref
        and command.waiting_evidence_ref
        and command.next_review_at
    ):
        raise TransitionRejected('waiting_request_incomplete')


def _validate_corrected_close(snapshot: CaseSnapshot, command: CaseTransitionCommand,
                              items: tuple[CorrectionItem, ...]) -> None:
    if command.phase is not CasePhase.CLOSED or command.domain_outcome is not CorrectionOutcome.CORRECTED:
        return
    if snapshot.phase is not CasePhase.FULFILLMENT:
        raise TransitionRejected('corrected_requires_fulfillment')
    if any(item.accepted and item.requires_public_change
           and item.publication_state is not PublicationState.VERIFIED for item in items):
        raise TransitionRejected('publication_not_verified')


def _validate(snapshot: CaseSnapshot, command: CaseTransitionCommand,
              policy: CasePolicy, correction_items: tuple[CorrectionItem, ...]) -> None:
    del policy
    _validate_audit(snapshot, command)
    _validate_waiting(command)
    _validate_corrected_close(snapshot, command, correction_items)
    if command.phase is CasePhase.CLOSED and command.domain_outcome is None:
        raise TransitionRejected('terminal_outcome_required')


def transition_case(snapshot: CaseSnapshot, command: CaseTransitionCommand,
                    policy: CasePolicy, *, now: datetime,
                    correction_items: tuple[CorrectionItem, ...] = ()) -> TransitionResult:
    _validate(snapshot, command, policy, correction_items)
    closed_at = now if command.phase is CasePhase.CLOSED else None
    next_snapshot = replace(
        snapshot, phase=command.phase, activity=command.activity,
        disposition_family=command.disposition_family, domain_outcome=command.domain_outcome,
        current_revision=snapshot.current_revision + 1, updated_at=now, closed_at=closed_at,
    )
    return TransitionResult(next_snapshot, TransitionDraft(
        snapshot.case_id, snapshot.phase, command.phase, snapshot.current_revision,
        next_snapshot.current_revision, command.actor.actor_ref, command.reason_code,
        policy.revision, command.actor.correlation_id, now,
    ))
