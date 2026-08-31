"""Transactional audit and outbox intent envelope for case mutations."""
from __future__ import annotations

from dataclasses import dataclass, field
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

    def __post_init__(self) -> None:
        if not all(type(value) is str and value for value in (
            self.event_id, self.actor_id, self.action, self.resource_type,
            self.resource_id, self.reason, self.correlation_id,
        )):
            raise ValueError("invalid_audit_event")
        if type(self.revision) is not int or self.revision < 1:
            raise ValueError("invalid_audit_event")
        if type(self.occurred_at) is not datetime or self.occurred_at.tzinfo is None:
            raise ValueError("invalid_audit_event")
        if self.generation is not None and (type(self.generation) is not str or not self.generation):
            raise ValueError("invalid_audit_event")


def _envelope(event: AuditEvent, payload: Mapping[str, object]) -> dict[str, object]:
    result = dict(payload)
    result.update({
        "event_id": event.event_id,
        "case_id": event.resource_id,
        "revision": event.revision,
        "generation": event.generation or result.get("generation", str(event.revision)),
        "correlation_id": event.correlation_id,
    })
    return result


def write_audit_and_outbox(transaction, event: AuditEvent, payload: Mapping[str, object]) -> None:
    """Write audit intent and outbox intent on the caller's open transaction."""
    if not isinstance(event, AuditEvent) or not isinstance(payload, Mapping):
        raise TypeError("invalid_audit_envelope")
    envelope = _envelope(event, payload)

    if hasattr(transaction, "append_audit_event"):
        transaction.append_audit_event(event)
    elif hasattr(transaction, "write_audit_event"):
        transaction.write_audit_event(event)
    else:
        try:
            from cases.audit import CaseAuditDraft
            from cases.domain import Channel
        except ModuleNotFoundError:
            from agent.cases.audit import CaseAuditDraft
            from agent.cases.domain import Channel

        transaction.append_audit(
            CaseAuditDraft(
                case_id=event.resource_id,
                actor_ref=event.actor_id,
                actor_scopes=(),
                channel=Channel.WEB,
                reason_code=event.action,
                policy_revision="correction-pilot-v1",
                correlation_id=event.correlation_id,
                before_snapshot=event.before,
                after_snapshot=event.after,
                occurred_at=event.occurred_at,
            )
        )

    if hasattr(transaction, "enqueue_outbox_event"):
        transaction.enqueue_outbox_event(envelope)
    elif hasattr(transaction, "write_outbox_event"):
        transaction.write_outbox_event(envelope)
    else:
        try:
            from cases.store import OutboxDraft
        except ModuleNotFoundError:
            from agent.cases.store import OutboxDraft

        topic = str(envelope.get("topic") or event.action)
        key = str(envelope.get("idempotency_key") or event.event_id)
        available_at = envelope.get("available_at", event.occurred_at)
        descriptor = dict(envelope)
        descriptor.pop("topic", None)
        descriptor.pop("idempotency_key", None)
        descriptor.pop("available_at", None)
        transaction.enqueue_outbox(
            OutboxDraft(
                case_id=event.resource_id,
                idempotency_key=key,
                topic=topic,
                descriptor=descriptor,
                available_at=available_at,
            )
        )


__all__ = ["AuditEvent", "write_audit_and_outbox"]
