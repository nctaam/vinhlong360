from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Mapping

from .domain import ActorContext, CaseSnapshot, Channel


_SAFE_CASE_FIELDS = (
    "case_id",
    "phase",
    "activity",
    "disposition_family",
    "domain_outcome",
    "severity",
    "current_revision",
    "promise_policy_ref",
    "promise_health",
    "created_at",
    "updated_at",
    "closed_at",
)


def _safe_value(value: object) -> object:
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def safe_case_projection(snapshot: CaseSnapshot) -> dict[str, object]:
    """Return the allowlisted state/revision projection used by canonical audit."""
    if type(snapshot) is not CaseSnapshot:
        raise ValueError("invalid_case_snapshot")
    return {
        field: _safe_value(getattr(snapshot, field))
        for field in _SAFE_CASE_FIELDS
    }


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
            if value is not None and not set(value) <= set(_SAFE_CASE_FIELDS):
                raise ValueError("unsafe_case_audit_snapshot")
            if value is not None and not isinstance(value, MappingProxyType):
                object.__setattr__(self, name, MappingProxyType(dict(value)))

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
