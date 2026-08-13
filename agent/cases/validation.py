from datetime import datetime

from .domain import (
    ActorContext, CaseActivity, CasePhase, CaseSnapshot, Channel, CorrectionItem,
    CorrectionOutcome, DispositionFamily, EvidenceLevel, PromiseClock,
    PromiseHealth, PublicationState, RiskClass, ServiceKind, WaitingContext,
)
from .policy import CasePolicy


class PolicyRejected(ValueError):
    pass


def aware(value: object) -> bool:
    return isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip()) and value == value.strip()


def validate_text(value: object) -> None:
    if not _text(value):
        raise PolicyRejected('invalid_case_contract')


def valid_identifier(value: object) -> bool:
    return _text(value) and ':' not in value and not any(character.isspace() for character in value)


def validate_identifier(value: object) -> None:
    if not valid_identifier(value):
        raise PolicyRejected('invalid_case_contract')


def _optional_identifier(value: object) -> bool:
    return value is None or valid_identifier(value)


def _optional_text(value: object) -> bool:
    return value is None or _text(value)


def _valid_clock_observation(clock: PromiseClock, now: datetime) -> bool:
    if clock.observed_at is None:
        return True
    return (aware(clock.observed_at)
            and clock.started_at <= clock.observed_at <= now)


def _valid_clock_risk(clock: PromiseClock) -> bool:
    if clock.risk_at is None:
        return True
    return (aware(clock.risk_at)
            and clock.started_at <= clock.risk_at <= clock.due_at)


def validate_clock(clock: object, now: object) -> None:
    if type(clock) is not PromiseClock or not aware(now):
        raise PolicyRejected('invalid_case_time')
    if any((
        not _text(clock.kind), type(clock.health) is not PromiseHealth,
        not _optional_text(clock.policy_revision), not aware(clock.started_at),
        not aware(clock.due_at),
    )):
        raise PolicyRejected('invalid_case_time')
    if (clock.started_at > clock.due_at
            or not _valid_clock_observation(clock, now)
            or not _valid_clock_risk(clock)):
        raise PolicyRejected('invalid_case_time')


def _valid_item_core(item: CorrectionItem) -> bool:
    return not any((
        not valid_identifier(item.item_id), type(item.risk_class) is not RiskClass,
        type(item.evidence_level) is not EvidenceLevel,
        type(item.publication_state) is not PublicationState,
        type(item.base_entity_revision) is not int, item.base_entity_revision < 1,
    ))


def _valid_item_references(item: CorrectionItem) -> bool:
    return not any((
        not _optional_identifier(item.evidence_supplier_ref),
        not _optional_identifier(item.entity_id), not _optional_text(item.field_path),
        not _optional_identifier(item.decision_ref),
        not _optional_identifier(item.changeset_ref),
    ))


def _valid_item_flags(item: CorrectionItem) -> bool:
    return all(type(flag) is bool for flag in (
        item.accepted, item.requires_public_change, item.validated,
        item.evidence_conflict, item.publication_failed, item.rollback_failed,
        item.privacy_security_safety_signal,
    ))


def validate_item(item: object) -> None:
    if type(item) is not CorrectionItem:
        raise PolicyRejected('invalid_case_contract')
    if not _valid_item_core(item) or not _valid_item_references(item) or not _valid_item_flags(item):
        raise PolicyRejected('invalid_case_contract')
    if not isinstance(item.evidence_refs, tuple):
        raise PolicyRejected('invalid_case_contract')
    if any(not valid_identifier(reference) for reference in item.evidence_refs):
        raise PolicyRejected('invalid_case_contract')


def _validate_waiting(snapshot: CaseSnapshot, now: datetime) -> None:
    waiting = snapshot.waiting
    if snapshot.activity is not CaseActivity.WAITING_ON_REQUESTER:
        if waiting is not None:
            raise PolicyRejected('invalid_case_contract')
        return
    if type(waiting) is not WaitingContext:
        raise PolicyRejected('invalid_case_contract')
    if any((
        not _text(waiting.requester_request), not _text(waiting.safe_message),
        not valid_identifier(waiting.waiting_on_ref),
        not valid_identifier(waiting.evidence_ref),
    )):
        raise PolicyRejected('invalid_case_contract')
    if (not aware(waiting.started_at) or not aware(waiting.next_review_at)
            or waiting.started_at > now or waiting.next_review_at <= now):
        raise PolicyRejected('invalid_case_time')


def _valid_snapshot_fields(snapshot: CaseSnapshot) -> bool:
    return not any((
        not valid_identifier(snapshot.case_id), type(snapshot.service_kind) is not ServiceKind,
        not _text(snapshot.category), type(snapshot.phase) is not CasePhase,
        type(snapshot.activity) is not CaseActivity,
        type(snapshot.disposition_family) is not DispositionFamily,
        type(snapshot.promise_health) is not PromiseHealth,
        snapshot.domain_outcome is not None and type(snapshot.domain_outcome) is not CorrectionOutcome,
        not _optional_text(snapshot.severity), not _text(snapshot.reporter_privacy),
        not isinstance(snapshot.owner_ref, str),
        isinstance(snapshot.owner_ref, str) and snapshot.owner_ref != snapshot.owner_ref.strip(),
        type(snapshot.current_revision) is not int, not _text(snapshot.promise_policy_ref),
        not isinstance(snapshot.promise_clocks, tuple),
    ))


def _valid_snapshot_times(snapshot: CaseSnapshot, now: datetime) -> bool:
    if not aware(snapshot.created_at) or not aware(snapshot.updated_at):
        return False
    if not snapshot.created_at <= snapshot.updated_at <= now:
        return False
    if snapshot.closed_at is None:
        return snapshot.phase is not CasePhase.CLOSED
    return (snapshot.phase is CasePhase.CLOSED and aware(snapshot.closed_at)
            and snapshot.updated_at <= snapshot.closed_at <= now)


def validate_snapshot(snapshot: object, now: object) -> None:
    if type(snapshot) is not CaseSnapshot or not aware(now):
        raise PolicyRejected('invalid_case_contract')
    if not _valid_snapshot_fields(snapshot) or snapshot.current_revision < 1:
        raise PolicyRejected('invalid_case_contract')
    if not _valid_snapshot_times(snapshot, now):
        raise PolicyRejected('invalid_case_contract')
    if snapshot.phase is CasePhase.CLOSED and snapshot.activity is not CaseActivity.ACTIVE:
        raise PolicyRejected('invalid_case_contract')
    _validate_waiting(snapshot, now)
    for clock in snapshot.promise_clocks:
        validate_clock(clock, now)


def validate_actor(actor: object) -> None:
    if type(actor) is not ActorContext:
        raise PolicyRejected('invalid_case_contract')
    if any((
        type(actor.channel) is not Channel, not valid_identifier(actor.actor_ref),
        not valid_identifier(actor.correlation_id), not isinstance(actor.scopes, frozenset),
    )):
        raise PolicyRejected('invalid_case_contract')
    if any(not valid_identifier(scope) for scope in actor.scopes):
        raise PolicyRejected('invalid_case_contract')


def validate_policy(policy: object) -> None:
    if type(policy) is not CasePolicy:
        raise PolicyRejected('invalid_case_policy')
    if any((
        not _text(policy.revision), not isinstance(policy.risk_registry, dict),
        not isinstance(policy.risk_registry.get('R1'), dict),
    )):
        raise PolicyRejected('invalid_case_policy')
    if type(policy.risk_registry['R1'].get('independent_review')) is not bool:
        raise PolicyRejected('invalid_case_policy')
