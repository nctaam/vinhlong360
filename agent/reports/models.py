"""Small, backend-neutral report value objects."""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ReportTargetType(str, Enum):
    ENTITY = "entity"
    FACILITY = "facility"
    POST = "post"
    COMMENT = "comment"
    USER = "user"
    STALE_FIELD = "stale_field"


class ReportStatus(str, Enum):
    PENDING = "pending"
    REVIEWED = "reviewed"
    DISMISSED = "dismissed"
    RESOLVED = "resolved"


class InvalidReportTargetType(ValueError):
    code = "invalid_target_type"


def _target_type(value: object) -> ReportTargetType:
    if isinstance(value, ReportTargetType):
        return value
    try:
        return ReportTargetType(str(value))
    except (TypeError, ValueError) as exc:
        raise InvalidReportTargetType(f"unsupported report target type: {value!r}") from exc


@dataclass(frozen=True)
class ReportActor:
    """The stable scope used for idempotency and audit, never a raw IP/token."""

    actor_scope: str
    reporter_id: str | None = None
    reporter_hash: str | None = None
    source_channel: str = "web"

    def __post_init__(self) -> None:
        if type(self.actor_scope) is not str or not self.actor_scope.strip():
            raise ValueError("invalid_actor_scope")
        if self.reporter_id is not None and type(self.reporter_id) is not str:
            raise ValueError("invalid_reporter_id")
        if self.reporter_hash is not None and type(self.reporter_hash) is not str:
            raise ValueError("invalid_reporter_hash")
        if type(self.source_channel) is not str or not self.source_channel.strip():
            raise ValueError("invalid_source_channel")


@dataclass(frozen=True)
class ReportCreate:
    target_id: str
    target_type: ReportTargetType | str
    reason: str
    detail: str = ""
    contact: str = ""
    field: str | None = None
    legacy_locator: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "target_type", _target_type(self.target_type))
        if type(self.target_id) is not str or not self.target_id.strip():
            raise ValueError("invalid_target_id")
        if type(self.reason) is not str or not self.reason.strip():
            raise ValueError("invalid_reason")
        if type(self.detail) is not str or type(self.contact) is not str:
            raise ValueError("invalid_report_text")
        if self.field is not None and type(self.field) is not str:
            raise ValueError("invalid_report_field")


@dataclass(frozen=True)
class ReportRecord:
    report_id: str
    target_id: str
    target_type: ReportTargetType
    reason: str
    status: ReportStatus
    actor_scope: str
    reporter_id: str | None = None
    reporter_hash: str | None = None
    detail: str = ""
    contact_ciphertext: str | None = None
    field: str | None = None
    revision: int = 1
    idempotency_key: str | None = None
    created_at: datetime = dc_field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = dc_field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_by: str | None = None
    resolved_at: datetime | None = None
    correlation_id: str | None = None
    source_channel: str = "web"
    legacy_locator: str | None = None
    replayed: bool = False

    @property
    def id(self) -> str:
        return self.report_id

    def to_dict(self, *, redact_contact: bool = True) -> dict[str, Any]:
        result = {
            "report_id": self.report_id,
            "target_id": self.target_id,
            "target_type": self.target_type.value,
            "reason": self.reason,
            "status": self.status.value,
            "actor_scope": self.actor_scope,
            "reporter_id": self.reporter_id,
            "reporter_hash": self.reporter_hash,
            "detail": self.detail,
            "field": self.field,
            "revision": self.revision,
            "idempotency_key": self.idempotency_key,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "resolved_by": self.resolved_by,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "correlation_id": self.correlation_id,
            "source_channel": self.source_channel,
            "legacy_locator": self.legacy_locator,
            "replayed": self.replayed,
        }
        if not redact_contact:
            result["contact_ciphertext"] = self.contact_ciphertext
        return result
