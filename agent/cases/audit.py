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


def canonical_case_projection(value: Mapping[str, object]) -> Mapping[str, object]:
    """Validate the exact scalar audit schema and return an immutable copy."""
    if type(value) not in (dict, MappingProxyType) or not set(value) <= _SAFE_CASE_FIELDS:
        raise ValueError("unsafe_case_audit_snapshot")
    canonical: dict[str, object] = {}
    for field, item in value.items():
        if field in _ENUM_VALUES:
            if type(item) is not str or item not in _ENUM_VALUES[field]:
                raise ValueError("unsafe_case_audit_snapshot")
        elif field in _REQUIRED_TEXT_FIELDS:
            if type(item) is not str or not item:
                raise ValueError("unsafe_case_audit_snapshot")
        elif field in _OPTIONAL_TEXT_FIELDS:
            if item is not None and (type(item) is not str or not item):
                raise ValueError("unsafe_case_audit_snapshot")
        elif field == "current_revision":
            if type(item) is not int or item < 1:
                raise ValueError("unsafe_case_audit_snapshot")
        else:
            item = _canonical_timestamp(item, optional=field == "closed_at")
        canonical[field] = item
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

    def __post_init__(self) -> None:
        if (
            type(self.case_id) is not str
            or not self.case_id
            or type(self.actor_ref) is not str
            or not self.actor_ref
            or type(self.actor_scopes) is not tuple
            or tuple(sorted(set(self.actor_scopes))) != self.actor_scopes
            or not all(type(scope) is str and scope for scope in self.actor_scopes)
            or type(self.channel) is not Channel
            or type(self.reason_code) is not str
            or not self.reason_code
            or type(self.policy_revision) is not str
            or not self.policy_revision
            or type(self.correlation_id) is not str
            or not self.correlation_id
            or type(self.occurred_at) is not datetime
            or self.occurred_at.tzinfo is None
        ):
            raise ValueError("invalid_case_audit")
        for name in ("before_snapshot", "after_snapshot"):
            value = getattr(self, name)
            if value is not None and not isinstance(value, Mapping):
                raise ValueError("invalid_case_audit")
            if value is not None:
                object.__setattr__(self, name, canonical_case_projection(value))

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
