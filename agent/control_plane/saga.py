"""Compensating media approval saga and immutable entity mutation envelopes.

The saga deliberately keeps provider calls outside the entity write itself.  A
successful upload is compensated when the database transaction cannot commit;
the idempotency ledger makes exact retries return the original receipt.
"""
from __future__ import annotations

import copy
import hashlib
import json
import logging
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Sequence
from types import SimpleNamespace

from database import db
import image_suggestions as _imgq
from storage import storage
from control_plane.snapshot import bump_generation, invalidate_entity
from control_plane.concurrency import claim_idempotency, record_idempotency_receipt, ClaimResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SagaStep:
    name: str
    run: Callable[[], Any]
    compensate: Callable[[Any], None]
    metadata: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class MutationAuditEnvelope:
    """Immutable metadata captured for every entity/media mutation."""
    event_id: str
    actor_id: str
    reason: str
    correlation_id: str
    resource_type: str
    resource_id: str
    revision: int
    before: Mapping[str, Any] | None
    after: Mapping[str, Any] | None
    occurred_at: datetime


AuditEnvelope = MutationAuditEnvelope


@dataclass(frozen=True)
class SagaReceipt:
    status: str
    idempotency_key: str
    steps: tuple[Mapping[str, Any], ...] = ()
    error: str | None = None
    orphan_cleanup_pending: bool = False
    durability_error: str | None = None
    post_commit_effects: tuple[Mapping[str, Any], ...] = ()


_SAGA_RECEIPTS: dict[str, SagaReceipt] = {}
_SAGA_LOCK = threading.RLock()
_ENTITY_APPROVAL_LOCKS: dict[str, threading.Lock] = {}
_ENTITY_APPROVAL_LOCKS_GUARD = threading.Lock()


def _entity_approval_lock(entity_id: str) -> threading.Lock:
    with _ENTITY_APPROVAL_LOCKS_GUARD:
        return _ENTITY_APPROVAL_LOCKS.setdefault(str(entity_id), threading.Lock())


def _ensure_idempotency_schema() -> None:
    db.initialize()
    if db._use_pg:
        return
    with db._conn() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS request_idempotency_keys (
            key TEXT PRIMARY KEY, first_seen_at TEXT NOT NULL,
            expires_at TEXT NOT NULL, meta TEXT NOT NULL DEFAULT '{}'
        )""")


def _receipt_data(receipt: SagaReceipt) -> dict[str, Any]:
    return {
        "status": receipt.status, "idempotency_key": receipt.idempotency_key,
        "steps": [dict(item) for item in receipt.steps], "error": receipt.error,
        "orphan_cleanup_pending": receipt.orphan_cleanup_pending,
        "durability_error": receipt.durability_error,
        "post_commit_effects": [dict(item) for item in receipt.post_commit_effects],
    }


def _receipt_from_data(value: Any) -> SagaReceipt | None:
    if not isinstance(value, dict) or not value.get("status"):
        return None
    return SagaReceipt(
        str(value["status"]), str(value.get("idempotency_key") or ""),
        tuple(value.get("steps") or ()), value.get("error"),
        bool(value.get("orphan_cleanup_pending")), value.get("durability_error"),
        tuple(value.get("post_commit_effects") or ()),
    )


def _claim_command(key: str, suggestion_id: str, actor_id: str) -> tuple[ClaimResult, SagaReceipt | None]:
    _ensure_idempotency_schema()
    request_hash = hashlib.sha256(f"image-approval:{suggestion_id}:{actor_id}".encode()).hexdigest()
    with db._conn() as conn:
        claim = claim_idempotency(SimpleNamespace(_db=db, _conn=conn), key, request_hash)
    if claim.replayed:
        receipt = _receipt_from_data(claim.receipt)
        return claim, receipt or SagaReceipt("in_progress", key, error="idempotency_in_progress")
    if claim.conflict:
        return claim, SagaReceipt("idempotency_conflict", key, error="idempotency_key_reused")
    return claim, None


def peek_approval_receipt(key: str, suggestion_id: str, actor_id: str) -> SagaReceipt | None:
    """Read a durable approval receipt without claiming or running providers."""
    _ensure_idempotency_schema()
    request_hash = hashlib.sha256(f"image-approval:{suggestion_id}:{actor_id}".encode()).hexdigest()
    with _SAGA_LOCK:
        cached = _SAGA_RECEIPTS.get(str(key).strip())
    if cached is not None:
        return cached
    with db._conn() as conn:
        ph = db._ph
        row = db._fetchone(conn, f"SELECT meta FROM request_idempotency_keys WHERE key={ph}", (str(key).strip(),))
    if not row:
        return None
    raw = db._row_to_dict(row).get("meta")
    meta = raw if isinstance(raw, dict) else json.loads(raw or "{}")
    if meta.get("request_hash") != request_hash:
        return SagaReceipt("idempotency_conflict", str(key).strip(), error="idempotency_key_reused")
    return _receipt_from_data(meta.get("receipt")) or SagaReceipt("in_progress", str(key).strip(), error="idempotency_in_progress")


def _store_receipt(key: str, receipt: SagaReceipt, claim: ClaimResult | None = None) -> SagaReceipt:
    with _SAGA_LOCK:
        _SAGA_RECEIPTS[key] = receipt
    if claim is not None and claim.claimed:
        try:
            with db._conn() as conn:
                record_idempotency_receipt(SimpleNamespace(_db=db, _conn=conn), claim, _receipt_data(receipt))
        except Exception as exc:
            logger.error("saga receipt persistence failed for %s: %s", key, exc)
            receipt = SagaReceipt(receipt.status, receipt.idempotency_key, receipt.steps,
                                  receipt.error, receipt.orphan_cleanup_pending,
                                  type(exc).__name__, receipt.post_commit_effects)
            with _SAGA_LOCK:
                _SAGA_RECEIPTS[key] = receipt
    return receipt


def run_saga(steps: Sequence[SagaStep], *, idempotency_key: str,
             request_hash: str | None = None) -> SagaReceipt:
    """Run steps in order; compensate completed steps in reverse on failure."""
    if not isinstance(idempotency_key, str) or not idempotency_key.strip():
        raise ValueError("invalid_idempotency_key")
    key = idempotency_key.strip()
    command_hash = request_hash or hashlib.sha256(
        json.dumps({
            "idempotency_key": key,
            "steps": [{"name": step.name, "metadata": step.metadata or {}} for step in steps],
        }, separators=(",", ":"), sort_keys=True, ensure_ascii=True, default=str).encode()
    ).hexdigest()
    claim, durable_replay = _claim_generic_command(key, command_hash)
    if durable_replay is not None:
        return durable_replay
    completed: list[tuple[SagaStep, Any]] = []
    receipts: list[Mapping[str, Any]] = []
    try:
        for step in steps:
            receipt = step.run()
            completed.append((step, receipt))
            receipts.append({"name": step.name, "receipt": copy.deepcopy(receipt)})
    except Exception as exc:
        orphan = False
        for step, receipt in reversed(completed):
            try:
                step.compensate(receipt)
            except Exception:
                orphan = True
        result = SagaReceipt(
            "failed_orphaned" if orphan else "failed_compensated",
            key,
            tuple(receipts),
            type(exc).__name__,
            orphan,
        )
        return _store_receipt(key, result, claim)
    result = SagaReceipt("committed", key, tuple(receipts))
    return _store_receipt(key, result, claim)


def _claim_generic_command(key: str, request_hash: str) -> tuple[ClaimResult | None, SagaReceipt | None]:
    """Claim a generic saga command in the same durable ledger as API sagas."""
    try:
        _ensure_idempotency_schema()
        with db._conn() as conn:
            claim = claim_idempotency(SimpleNamespace(_db=db, _conn=conn), key, request_hash)
        if claim.replayed:
            receipt = _receipt_from_data(claim.receipt)
            return claim, receipt or SagaReceipt("in_progress", key, error="idempotency_in_progress")
        if claim.conflict:
            return claim, SagaReceipt("idempotency_conflict", key, error="idempotency_key_reused")
        return claim, None
    except Exception as exc:
        # A saga cannot safely claim durable idempotency if its ledger is down.
        logger.error("generic saga idempotency unavailable for %s: %s", key, exc)
        return None, SagaReceipt("failed", key, error="idempotency_unavailable")


def _json(value: Any) -> str | None:
    return None if value is None else json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def record_entity_mutation(
    resource_id: str,
    *,
    actor_id: str,
    reason: str,
    correlation_id: str,
    before: Mapping[str, Any] | None,
    after: Mapping[str, Any] | None,
    revision: int,
    resource_type: str = "entity",
    conn=None,
    event_id: str | None = None,
    database=None,
) -> dict[str, Any]:
    """Persist one immutable audit envelope before the caller commits."""
    if not all(isinstance(v, str) and v for v in (resource_id, actor_id, reason, correlation_id, resource_type)):
        raise ValueError("invalid_entity_audit")
    if type(revision) is not int or revision < 1:
        raise ValueError("invalid_entity_audit")
    event_id = event_id or uuid.uuid4().hex
    occurred = datetime.now(timezone.utc)
    immutable = MutationAuditEnvelope(
        event_id=event_id, resource_id=resource_id, resource_type=resource_type,
        actor_id=actor_id, reason=reason, correlation_id=correlation_id,
        revision=revision, before=copy.deepcopy(before), after=copy.deepcopy(after),
        occurred_at=occurred,
    )
    envelope = {**immutable.__dict__, "occurred_at": occurred.isoformat()}
    writer = getattr(database or db, "record_entity_mutation_audit", None)
    if writer is None:
        raise RuntimeError("entity_audit_writer_missing")
    writer(conn=conn, **envelope)
    return envelope


def fetch_image_data(suggestion: Mapping[str, Any]) -> bytes:
    """Return candidate bytes; network adapters may replace this hook."""
    value = suggestion.get("data") or suggestion.get("image_data") or b""
    return value if isinstance(value, bytes) else bytes(value)


def _suggestion_receipt(suggestion_id: str, actor_id: str, key: str, status: str, **extra) -> SagaReceipt:
    orphan = bool(extra.pop("orphan_cleanup_pending", False))
    post_commit_effects = tuple(extra.pop("post_commit_effects", ()) or ())
    payload = {"suggestion_id": suggestion_id, "actor_id": actor_id, **extra}
    return SagaReceipt(status, key, (payload,), extra.get("error"), orphan,
                       post_commit_effects=post_commit_effects)


def _cleanup_uploaded(storage_obj, suggestion_id: str, uploaded: Mapping[str, Any] | None = None) -> bool:
    failed = False
    values = list((uploaded or {}).values())
    values.extend(v for v in list(getattr(storage_obj, "objects", ())) if suggestion_id in str(v))
    for value in dict.fromkeys(str(v) for v in values if v):
        try:
            storage_obj.delete(value)
        except Exception:
            failed = True
    return failed


def cleanup_uploaded_media(storage_obj, uploaded: Mapping[str, Any] | None = None) -> bool:
    """Compensate provider objects before an entity mutation has committed."""
    failed = False
    for value in dict.fromkeys(str(v) for v in (uploaded or {}).values() if v):
        try:
            storage_obj.delete(value)
        except Exception:
            failed = True
    return failed


def _claim_suggestion(suggestion_id: str, actor_id: str, key: str) -> tuple[bool, str | None]:
    """Durable pending-row claim using the existing approved_by column."""
    marker = f"__claim__:{key}:{actor_id}"
    with db._conn() as conn:
        ph = db._ph
        row = db._fetchone(conn, f"SELECT status, approved_by FROM image_suggestions WHERE id={ph}", (suggestion_id,))
        if not row:
            return False, "not_found"
        item = db._row_to_dict(row)
        if item.get("status") != "pending":
            return False, "not_pending"
        claimed_by = item.get("approved_by") or ""
        if claimed_by and claimed_by != marker:
            return False, "in_progress"
        cur = db._execute(conn, f"UPDATE image_suggestions SET approved_by={ph} WHERE id={ph} AND status='pending' AND (approved_by='' OR approved_by IS NULL OR approved_by={ph})", (marker, suggestion_id, marker))
        if getattr(cur, "rowcount", 0) == 0:
            return False, "in_progress"
    return True, marker


def _release_suggestion_claim(suggestion_id: str, marker: str | None) -> None:
    if not marker:
        return
    try:
        with db._conn() as conn:
            ph = db._ph
            db._execute(conn, f"UPDATE image_suggestions SET approved_by='' WHERE id={ph} AND status='pending' AND approved_by={ph}", (suggestion_id, marker))
    except Exception:
        pass


def approve_image_suggestion(suggestion_id: str, actor_id: str, *, idempotency_key: str,
                             _image_data: bytes | None = None) -> SagaReceipt:
    """Approve a pending suggestion with upload compensation and exact retries."""
    key = str(idempotency_key).strip()
    claim, replay = _claim_command(key, suggestion_id, actor_id)
    if replay is not None:
        return replay
    if claim.conflict:
        return _store_receipt(key, SagaReceipt("idempotency_conflict", key, error="idempotency_key_reused"), None)
    with _SAGA_LOCK:
        previous = _SAGA_RECEIPTS.get(key)
        if previous is not None:
            return previous
    suggestion = _imgq.get_suggestion(suggestion_id)
    if not suggestion:
        return _store_receipt(key, _suggestion_receipt(suggestion_id, actor_id, key, "not_found"), claim)
    if suggestion.get("status") != "pending":
        return _store_receipt(key, _suggestion_receipt(suggestion_id, actor_id, key, "not_pending", current_status=suggestion.get("status")), claim)
    claimed, claim_error = _claim_suggestion(suggestion_id, actor_id, key)
    if not claimed:
        return _store_receipt(key, _suggestion_receipt(suggestion_id, actor_id, key, claim_error or "in_progress"), claim)
    claim_marker = f"__claim__:{key}:{actor_id}"

    uploaded: dict[str, Any] = {}
    try:
        entity = db.get_entity(suggestion["entity_id"])
        if not entity:
            result = _suggestion_receipt(suggestion_id, actor_id, key, "not_found")
            _release_suggestion_claim(suggestion_id, claim_marker)
            return _store_receipt(key, result, claim)
        try:
            uploaded = storage.upload_image_set(
                _image_data if _image_data is not None else fetch_image_data(suggestion),
                "entities", f"{suggestion['entity_id']}-{suggestion_id}"
            )
        except Exception as exc:
            # Providers can fail after creating objects; clean up any URLs they
            # exposed on the exception or partial return path.
            orphan = _cleanup_uploaded(storage, suggestion_id, getattr(exc, "urls", {}))
            result = _suggestion_receipt(suggestion_id, actor_id, key,
                                         "failed_orphaned" if orphan else "failed_compensated",
                                         error=type(exc).__name__, orphan_cleanup_pending=orphan)
            _release_suggestion_claim(suggestion_id, claim_marker)
            return _store_receipt(key, result, claim)
        cover = uploaded.get("md") or uploaded.get("lg") or uploaded.get("sm")
        with _entity_approval_lock(suggestion["entity_id"]):
            with db._conn() as conn:
                ph = db._ph
                lock_clause = " FOR UPDATE" if getattr(db, "_use_pg", False) else ""
                current_row = db._fetchone(
                    conn, f"SELECT * FROM entities WHERE id = {ph}{lock_clause}",
                    (suggestion["entity_id"],),
                )
                if not current_row:
                    raise RuntimeError("entity_not_found")
                before = db._parse_entity(current_row) if hasattr(db, "_parse_entity") else copy.deepcopy(entity)
                images = list(before.get("images") or [])
                if len(images) >= 10:
                    raise RuntimeError("image_limit")
                entity = copy.deepcopy(before)
                if cover and cover not in images:
                    images.append(cover)
                entity["images"] = images
                attrs = entity.get("attributes") if isinstance(entity.get("attributes"), dict) else {}
                credits = list(attrs.get("image_credits") or [])
                credits.append({"url": cover, "license": suggestion.get("license") or "", "author": suggestion.get("author") or "", "source": suggestion.get("source") or "", "source_url": suggestion.get("candidate_url") or "", "wp_title": suggestion.get("wp_title") or ""})
                attrs["image_credits"] = credits
                entity["attributes"] = attrs
                entity["updatedAt"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                if hasattr(db, "_entity_writer"):
                    db._entity_writer().upsert(conn, entity)
                if hasattr(db, "_bump_sqlite_entity_revision"):
                    db._bump_sqlite_entity_revision(conn, before, entity)
                revision_row = db._fetchone(conn, f"SELECT revision FROM entities WHERE id = {db._ph}", (suggestion["entity_id"],))
                revision = int((db._row_to_dict(revision_row) or {}).get("revision") or 1)
                record_entity_mutation(suggestion["entity_id"], actor_id=actor_id, reason="image_approval", correlation_id=key, before=before, after=entity, revision=revision, conn=conn, database=db)
                if not _imgq.mark_status(suggestion_id, "approved", approved_by=actor_id, conn=conn):
                    raise RuntimeError("suggestion_not_pending")
                snapshot = bump_generation(conn, suggestion["entity_id"], "image_approval", key)
        try:
            invalidate_entity(suggestion["entity_id"], reason="image_approval", generation=snapshot.generation)
            post_commit_effects = ({"effect": "invalidation", "status": "applied"},)
        except Exception as invalidation_error:
            # The entity transaction is already committed; cache invalidation is
            # retryable observation and must never delete committed media.
            logger.error("entity invalidation failed after image approval: %s", invalidation_error)
            post_commit_effects = ({"effect": "invalidation", "status": "failed",
                                    "error": type(invalidation_error).__name__},)
        result = _suggestion_receipt(suggestion_id, actor_id, key, "committed", url=cover, sizes=uploaded,
                                     post_commit_effects=post_commit_effects)
        return _store_receipt(key, result, claim)
    except Exception as exc:
        orphan = _cleanup_uploaded(storage, suggestion_id, uploaded)
        result = _suggestion_receipt(suggestion_id, actor_id, key,
                                     "failed_orphaned" if orphan else "failed_compensated",
                                     error=type(exc).__name__, orphan_cleanup_pending=orphan)
        _release_suggestion_claim(suggestion_id, claim_marker)
        return _store_receipt(key, result, claim)
__all__ = ["SagaStep", "SagaReceipt", "MutationAuditEnvelope", "AuditEnvelope",
           "run_saga", "approve_image_suggestion", "peek_approval_receipt", "cleanup_uploaded_media",
           "record_entity_mutation"]
