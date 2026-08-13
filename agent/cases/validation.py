from datetime import datetime

from .domain import (
    ActorContext, CaseActivity, CasePhase, CaseSnapshot, Channel, CorrectionItem,
    CorrectionOutcome, DispositionFamily, EvidenceLevel, PromiseClock, PromiseHealth,
    PublicationState, RiskClass,
)
from .policy import CasePolicy


class PolicyRejected(ValueError):
    pass


def aware(value: object) -> bool:
    return isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None


def valid_identifier(value: object) -> bool:
    return isinstance(value, str) and bool(value) and ':' not in value and '\n' not in value


def validate_clock(clock: object, now: object) -> None:
    if (not isinstance(clock, PromiseClock) or not isinstance(clock.health, PromiseHealth)
            or not aware(now) or not aware(clock.started_at) or not aware(clock.due_at)
            or clock.started_at > clock.due_at
            or clock.observed_at is not None and (not aware(clock.observed_at)
                                                  or not clock.started_at <= clock.observed_at <= now)
            or clock.risk_at is not None and (not aware(clock.risk_at)
                                               or not clock.started_at <= clock.risk_at <= clock.due_at)):
        raise PolicyRejected('invalid_case_time')


def validate_item(item: object) -> None:
    if (not isinstance(item, CorrectionItem) or not valid_identifier(item.item_id)
            or not isinstance(item.risk_class, RiskClass) or not isinstance(item.evidence_level, EvidenceLevel)
            or not isinstance(item.publication_state, PublicationState)
            or type(item.base_entity_revision) is not int or item.base_entity_revision < 1
            or any(type(flag) is not bool for flag in (
                item.accepted, item.requires_public_change, item.validated, item.evidence_conflict,
                item.publication_failed, item.rollback_failed, item.privacy_security_safety_signal))):
        raise PolicyRejected('invalid_case_contract')


def validate_snapshot(snapshot: object, now: object) -> None:
    if not isinstance(snapshot, CaseSnapshot) or not aware(now):
        raise PolicyRejected('invalid_case_contract')
    if (not valid_identifier(snapshot.case_id) or not isinstance(snapshot.phase, CasePhase)
            or not isinstance(snapshot.activity, CaseActivity)
            or not isinstance(snapshot.disposition_family, DispositionFamily)
            or not isinstance(snapshot.promise_health, PromiseHealth)
            or snapshot.domain_outcome is not None and not isinstance(snapshot.domain_outcome, CorrectionOutcome)
            or not aware(snapshot.created_at) or not aware(snapshot.updated_at)
            or not snapshot.created_at <= snapshot.updated_at <= now
            or (snapshot.phase is CasePhase.CLOSED) != (snapshot.closed_at is not None)
            or snapshot.closed_at is not None and (not aware(snapshot.closed_at)
                                                    or not snapshot.updated_at <= snapshot.closed_at <= now)
            or not isinstance(snapshot.promise_clocks, tuple)):
        raise PolicyRejected('invalid_case_contract')
    for clock in snapshot.promise_clocks:
        validate_clock(clock, now)


def validate_actor(actor: object) -> None:
    if (not isinstance(actor, ActorContext) or not isinstance(actor.channel, Channel)
            or not valid_identifier(actor.actor_ref) or not valid_identifier(actor.correlation_id)
            or not isinstance(actor.scopes, frozenset)):
        raise PolicyRejected('invalid_case_contract')


def validate_policy(policy: object) -> None:
    if (not isinstance(policy, CasePolicy) or not isinstance(policy.risk_registry, dict)
            or not isinstance(policy.risk_registry.get('R1'), dict)
            or type(policy.risk_registry['R1'].get('independent_review')) is not bool):
        raise PolicyRejected('invalid_case_policy')
