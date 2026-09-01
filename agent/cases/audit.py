from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Mapping

from .domain import ActorContext, CaseSnapshot, Channel


_ENUM_VALUES = {
    "phase": frozenset(("intake", "triage", "investigation", "decision", "fulfillment", "closed")),
    "activity": frozenset(("active", "waiting_on_requester", "waiting_on_external")),
    "disposition_family": frozenset(("undetermined", "action_taken", "no_action", "transferred", "withdrawn", "duplicate")),
    "promise_health": frozenset(("on_track", "at_risk", "breached", "recovery")),
}
_REQUIRED_TEXT_FIELDS = frozenset(("case_id", "promise_policy_ref"))
_OPTIONAL_TEXT_FIELDS = frozenset(("domain_outcome", "severity"))
_TIMESTAMP_FIELDS = frozenset(("created_at", "updated_at", "closed_at"))
_SAFE_CASE_FIELDS = frozenset(
    (*_ENUM_VALUES, *_REQUIRED_TEXT_FIELDS, *_OPTIONAL_TEXT_FIELDS,
     *_TIMESTAMP_FIELDS, "current_revision")
)


def _canonical_timestamp(value: object, *, optional: bool) -> str | None:
    if value is None and optional:
        return None
    if type(value) is not str:
        raise ValueError("unsafe_case_audit_snapshot")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise ValueError("unsafe_case_audit_snapshot") from None
    if parsed.tzinfo is None or parsed.isoformat() != value:
        raise ValueError("unsafe_case_audit_snapshot")
    return value


def _validated_text_item(field: str, item: object) -> object:
    if field in _ENUM_VALUES:
        if type(item) is not str or item not in _ENUM_VALUES[field]:
            raise ValueError("unsafe_case_audit_snapshot")
        return item
    if field in _REQUIRED_TEXT_FIELDS:
        if type(item) is not str or not item:
            raise ValueError("unsafe_case_audit_snapshot")
        return item
    if item is not None and (type(item) is not str or not item):
        raise ValueError("unsafe_case_audit_snapshot")
    return item


def _validated_projection_item(field: str, item: object) -> object:
    if field in _ENUM_VALUES or field in _REQUIRED_TEXT_FIELDS or field in _OPTIONAL_TEXT_FIELDS:
        return _validated_text_item(field, item)
    if field == "current_revision":
        if type(item) is not int or item < 1:
            raise ValueError("unsafe_case_audit_snapshot")
        return item
    return _canonical_timestamp(item, optional=field == "closed_at")


def canonical_case_projection(value: Mapping[str, object]) -> Mapping[str, object]:
    """Validate the exact scalar audit schema and return an immutable copy."""
    if type(value) not in (dict, MappingProxyType) or not set(value) <= _SAFE_CASE_FIELDS:
        raise ValueError("unsafe_case_audit_snapshot")
    canonical: dict[str, object] = {}
    for field, item in value.items():
        canonical[field] = _validated_projection_item(field, item)
    return MappingProxyType(canonical)


def serialize_case_projection(value: Mapping[str, object] | None) -> str | None:
    if value is None:
        return None
    canonical = canonical_case_projection(value)
    return json.dumps(dict(canonical), sort_keys=True, allow_nan=False)


def safe_case_projection(snapshot: CaseSnapshot) -> dict[str, object]:
    """Return the allowlisted state/revision projection used by canonical audit."""
    if type(snapshot) is not CaseSnapshot:
        raise ValueError("invalid_case_snapshot")
    projection = {
        "case_id": snapshot.case_id,
        "phase": snapshot.phase.value,
        "activity": snapshot.activity.value,
        "disposition_family": snapshot.disposition_family.value,
        "domain_outcome": (
            None
            if snapshot.domain_outcome is None
            else getattr(snapshot.domain_outcome, "value", snapshot.domain_outcome)
        ),
        "severity": snapshot.severity,
        "current_revision": snapshot.current_revision,
        "promise_policy_ref": snapshot.promise_policy_ref,
        "promise_health": snapshot.promise_health.value,
        "created_at": snapshot.created_at.isoformat(),
        "updated_at": snapshot.updated_at.isoformat(),
        "closed_at": None if snapshot.closed_at is None else snapshot.closed_at.isoformat(),
    }
    return dict(canonical_case_projection(projection))


@dataclass(frozen=True)
class CaseAuditDraft:
    case_id: str
    actor_ref: str
    actor_scopes: tuple[str, ...]
    channel: Channel
    reason_code: str
    policy_revision: str
    correlation_id: str
    before_snapshot: Mapping[str, object] | None
    after_snapshot: Mapping[str, object] | None
    occurred_at: datetime
    # Optional envelope fields are additive for legacy callers. Transactional
    # correction events populate them so the audit row and outbox share one
    # durable identity without requiring a schema migration.
    event_id: str | None = None
    resource_id: str | None = None
    revision: int | None = None
    generation: str | None = None
    resource_type: str | None = None
    action: str | None = None

    def _identity_fields_valid(self) -> bool:
        return not (
            type(self.case_id) is not str
            or not self.case_id
            or type(self.actor_ref) is not str
            or not self.actor_ref
            or type(self.actor_scopes) is not tuple
            or tuple(sorted(set(self.actor_scopes))) != self.actor_scopes
            or not all(type(scope) is str and scope for scope in self.actor_scopes)
        )

    def _label_fields_valid(self) -> bool:
        return not (
            type(self.channel) is not Channel
            or type(self.reason_code) is not str
            or not self.reason_code
            or type(self.policy_revision) is not str
            or not self.policy_revision
            or type(self.correlation_id) is not str
            or not self.correlation_id
        )

    def _occurred_at_valid(self) -> bool:
        return type(self.occurred_at) is datetime and self.occurred_at.tzinfo is not None

    def __post_init__(self) -> None:
        if not self._base_fields_valid():
            raise ValueError("invalid_case_audit")
        self._normalize_event_fields()
        for name in ("before_snapshot", "after_snapshot"):
            value = getattr(self, name)
            if value is not None and not isinstance(value, Mapping):
                raise ValueError("invalid_case_audit")
            if value is not None:
                object.__setattr__(self, name, canonical_case_projection(value))

    def _base_fields_valid(self) -> bool:
        return self._identity_fields_valid() and self._label_fields_valid() and self._occurred_at_valid()

    def _normalize_event_fields(self) -> None:
        self._validate_event_identity()
        if self.event_id is None:
            return
        object.__setattr__(self, "resource_id", self.resource_id or self.case_id)
        object.__setattr__(self, "resource_type", self.resource_type or "case")
        object.__setattr__(self, "action", self.action or self.reason_code)
        if type(self.resource_type) is not str or not self.resource_type:
            raise ValueError("invalid_case_audit")
        if type(self.action) is not str or not self.action:
            raise ValueError("invalid_case_audit")
        revision = self._event_revision()
        object.__setattr__(self, "revision", revision)
        generation = self.generation or str(revision)
        if type(generation) is not str or not generation:
            raise ValueError("invalid_case_audit")
        object.__setattr__(self, "generation", generation)

    def _validate_event_identity(self) -> None:
        if self.resource_id is not None and (
            type(self.resource_id) is not str or not self.resource_id
        ):
            raise ValueError("invalid_case_audit")
        if self.event_id is None:
            if any(value is not None for value in (
                self.resource_id, self.revision, self.generation,
                self.resource_type, self.action,
            )):
                raise ValueError("invalid_case_audit")
            return
        if type(self.event_id) is not str or not self.event_id:
            raise ValueError("invalid_case_audit")

    def _event_revision(self) -> int:
        revision = self.revision
        if revision is None and self.after_snapshot is not None:
            revision = self.after_snapshot.get("current_revision")
        if type(revision) is not int or revision < 1:
            raise ValueError("invalid_case_audit")
        return revision

    @classmethod
    def from_snapshots(
        cls,
        *,
        actor: ActorContext,
        reason_code: str,
        policy_revision: str,
        before: CaseSnapshot | None,
        after: CaseSnapshot | None,
        occurred_at: datetime,
    ) -> CaseAuditDraft:
        if type(actor) is not ActorContext or before is None and after is None:
            raise ValueError("invalid_case_audit")
        case_id = after.case_id if after is not None else before.case_id
        if before is not None and before.case_id != case_id:
            raise ValueError("invalid_case_audit")
        return cls(
            case_id=case_id,
            actor_ref=actor.actor_ref,
            actor_scopes=tuple(sorted(actor.scopes)),
            channel=actor.channel,
            reason_code=reason_code,
            policy_revision=policy_revision,
            correlation_id=actor.correlation_id,
            before_snapshot=(
                None
                if before is None
                else MappingProxyType(safe_case_projection(before))
            ),
            after_snapshot=(
                None
                if after is None
                else MappingProxyType(safe_case_projection(after))
            ),
            occurred_at=occurred_at,
        )
