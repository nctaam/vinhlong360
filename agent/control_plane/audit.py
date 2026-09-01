"""Transactional audit and outbox intent envelope for case mutations."""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Mapping


@dataclass(frozen=True)
class AuditEvent:
    event_id: str
    actor_id: str
    action: str
    resource_type: str
    resource_id: str
    reason: str
    before: Mapping[str, object] | None
    after: Mapping[str, object] | None
    correlation_id: str
    revision: int
    occurred_at: datetime
    generation: str | None = field(default=None, compare=True)
    actor_scopes: tuple[str, ...] = ()
    channel: object | None = None
    policy_revision: str = "correction-pilot-v1"

    def __post_init__(self) -> None:
        self._validate_identity()
        self._validate_revision()
        self._validate_time()
        self._validate_generation()
        self._validate_actor_metadata()

    def _validate_identity(self) -> None:
        if not all(type(value) is str and value for value in (
            self.event_id, self.actor_id, self.action, self.resource_type,
            self.resource_id, self.reason, self.correlation_id,
        )):
            raise ValueError("invalid_audit_event")

    def _validate_revision(self) -> None:
        if type(self.revision) is not int or self.revision < 1:
            raise ValueError("invalid_audit_event")

    def _validate_time(self) -> None:
        if type(self.occurred_at) is not datetime or self.occurred_at.tzinfo is None:
            raise ValueError("invalid_audit_event")

    def _validate_generation(self) -> None:
        if self.generation is not None and (type(self.generation) is not str or not self.generation):
            raise ValueError("invalid_audit_event")
        if self.generation is None:
            object.__setattr__(self, "generation", str(self.revision))

    def _validate_actor_metadata(self) -> None:
        if type(self.actor_scopes) is not tuple or tuple(sorted(set(self.actor_scopes))) != self.actor_scopes:
            raise ValueError("invalid_audit_event")
        if not all(type(scope) is str and scope for scope in self.actor_scopes):
            raise ValueError("invalid_audit_event")
        try:
            from cases.domain import Channel
        except ModuleNotFoundError:
            from agent.cases.domain import Channel
        if type(self.channel) is not Channel:
            raise ValueError("invalid_audit_event")
        if type(self.policy_revision) is not str or not self.policy_revision:
            raise ValueError("invalid_audit_event")


def _envelope(event: AuditEvent, payload: Mapping[str, object]) -> dict[str, object]:
    result = dict(payload)
    result.update({
        "event_id": event.event_id,
        "action": event.action,
        "reason": event.reason,
        "resource_type": event.resource_type,
        "case_id": event.resource_id,
        "resource_id": event.resource_id,
        "revision": event.revision,
        "generation": event.generation or result.get("generation", str(event.revision)),
        "correlation_id": event.correlation_id,
        "actor_scopes": list(event.actor_scopes),
        "channel": event.channel.value,
        "policy_revision": event.policy_revision,
    })
    return result


def write_audit_and_outbox(transaction, event: AuditEvent, payload: Mapping[str, object], *,
                           update_existing: bool = False) -> None:
    """Write audit intent and outbox intent on the caller's open transaction."""
    if not isinstance(event, AuditEvent) or not isinstance(payload, Mapping):
        raise TypeError("invalid_audit_envelope")
    requested_generation = payload.get("generation")
    if requested_generation is not None and requested_generation != event.generation:
        event = replace(event, generation=str(requested_generation))
    envelope = _envelope(event, payload)

    _write_audit(transaction, event)
    _write_outbox(transaction, event, envelope, update_existing=update_existing)


def _write_audit(transaction, event: AuditEvent) -> None:
    if hasattr(transaction, "append_audit_event"):
        transaction.append_audit_event(event)
        return
    if hasattr(transaction, "write_audit_event"):
        transaction.write_audit_event(event)
        return
    try:
        from cases.audit import CaseAuditDraft
    except ModuleNotFoundError:
        from agent.cases.audit import CaseAuditDraft
    transaction.append_audit(CaseAuditDraft(
        case_id=event.resource_id, actor_ref=event.actor_id,
        actor_scopes=event.actor_scopes,
        channel=event.channel,
        reason_code=event.reason,
        policy_revision=event.policy_revision, correlation_id=event.correlation_id,
        before_snapshot=event.before, after_snapshot=event.after,
        occurred_at=event.occurred_at, event_id=event.event_id,
        resource_id=event.resource_id, revision=event.revision,
        generation=event.generation, resource_type=event.resource_type,
        action=event.action,
    ))


def _write_outbox(transaction, event: AuditEvent, envelope: Mapping[str, object], *,
                  update_existing: bool = False) -> None:
    if update_existing:
        if not hasattr(transaction, "update_outbox_event"):
            raise ValueError("publication_receipt_update_unsupported")
        transaction.update_outbox_event(envelope)
        return
    if hasattr(transaction, "enqueue_outbox_event"):
        transaction.enqueue_outbox_event(envelope)
        return
    if hasattr(transaction, "write_outbox_event"):
        transaction.write_outbox_event(envelope)
        return
    try:
        from cases.store import OutboxDraft
    except ModuleNotFoundError:
        from agent.cases.store import OutboxDraft
    topic = str(envelope.get("topic") or event.action)
    key = str(envelope.get("idempotency_key") or event.event_id)
    available_at = envelope.get("available_at", event.occurred_at)
    descriptor = dict(envelope)
    for key_name in ("topic", "idempotency_key", "available_at"):
        descriptor.pop(key_name, None)
    transaction.enqueue_outbox(OutboxDraft(
        case_id=event.resource_id, idempotency_key=key, topic=topic,
        descriptor=descriptor, available_at=available_at,
    ))


__all__ = ["AuditEvent", "write_audit_and_outbox"]
