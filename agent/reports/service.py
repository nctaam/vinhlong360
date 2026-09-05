"""Application service for canonical report intake and transitions."""

from __future__ import annotations

from database import db as default_database

from .models import (
    InvalidReportTargetType,
    ReportActor,
    ReportCreate,
    ReportRecord,
    ReportStatus,
)
from .repository import ReportRepository


class ReportError(RuntimeError):
    code = "report_error"
    status = 400


class ReportTargetNotFound(ReportError):
    code = "target_not_found"
    status = 404


class ReportNotFound(ReportError):
    code = "report_not_found"
    status = 404


class ReportConflict(ReportError):
    code = "revision_conflict"
    status = 409


class ReportIdempotencyConflict(ReportError):
    code = "idempotency_conflict"
    status = 409


class ReportService:
    def __init__(self, *, database=default_database, repository: ReportRepository | None = None):
        self.database = database
        self.repository = repository or ReportRepository(database)

    def _normalize_request(self, request: ReportCreate) -> ReportCreate:
        if not isinstance(request, ReportCreate):
            try:
                request = ReportCreate(**request)
            except InvalidReportTargetType:
                raise
            except Exception as exc:
                raise ReportError("invalid_report_request") from exc
        # ReportCreate performs strict target-type validation and never maps
        # unknown values to the historical `other` bucket.
        return request

    def create(self, request: ReportCreate, *, actor: ReportActor, idempotency_key: str, correlation_id: str) -> ReportRecord:
        request = self._normalize_request(request)
        if type(actor) is not ReportActor:
            raise ReportError("invalid_report_actor")
        if type(idempotency_key) is not str or not idempotency_key.strip() or len(idempotency_key) > 200:
            raise ReportError("invalid_idempotency_key")
        if type(correlation_id) is not str or not correlation_id.strip() or len(correlation_id) > 200:
            raise ReportError("invalid_correlation_id")
        if not self.repository.target_exists(request.target_type, request.target_id.strip()):
            raise ReportTargetNotFound("target_not_found")
        try:
            return self.repository.create(
                request,
                actor=actor,
                idempotency_key=idempotency_key.strip(),
                correlation_id=correlation_id.strip(),
            )
        except Exception as exc:
            # A unique-key race is resolved by the repository's select-after-
            # insert path. Preserve driver failures as service errors instead
            # of leaking SQL details to HTTP callers.
            if getattr(exc, "code", None):
                raise
            raise ReportError("report_store_failed") from exc

    def transition(self, report_id: str, *, expected_revision: int, status: ReportStatus | str, actor: ReportActor, reason: str) -> ReportRecord:
        if type(report_id) is not str or not report_id.strip():
            raise ReportNotFound("report_not_found")
        try:
            status = status if isinstance(status, ReportStatus) else ReportStatus(str(status))
        except (TypeError, ValueError) as exc:
            raise ReportError("invalid_report_status") from exc
        if type(expected_revision) is not int or expected_revision < 1:
            raise ReportConflict("revision_conflict")
        try:
            return self.repository.transition(
                report_id.strip(), expected_revision=expected_revision,
                status=status, actor=actor, reason=str(reason or "").strip(),
            )
        except LookupError as exc:
            raise ReportNotFound("report_not_found") from exc
        except RuntimeError as exc:
            if str(exc) == "report_revision_conflict":
                raise ReportConflict("revision_conflict") from exc
            raise ReportError("report_store_failed") from exc


__all__ = [
    "InvalidReportTargetType",
    "ReportConflict",
    "ReportError",
    "ReportIdempotencyConflict",
    "ReportNotFound",
    "ReportService",
    "ReportTargetNotFound",
]
