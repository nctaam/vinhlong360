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
_SAGA_RECEIPT_HASHES: dict[str, str] = {}
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
    normalized_key = str(key).strip()
    with _SAGA_LOCK:
        cached = _SAGA_RECEIPTS.get(normalized_key)
        cached_hash = _SAGA_RECEIPT_HASHES.get(normalized_key)
    # Validate the request hash before replaying any process-local receipt.
    if cached is not None and cached_hash == request_hash:
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
    return _receipt_from_data(meta.get("receipt")) or SagaReceipt("in_progress", normalized_key, error="idempotency_in_progress")


def _store_receipt(key: str, receipt: SagaReceipt, claim: ClaimResult | None = None) -> SagaReceipt:
    with _SAGA_LOCK:
        _SAGA_RECEIPTS[key] = receipt
        if claim is not None and claim.request_hash:
            _SAGA_RECEIPT_HASHES[key] = claim.request_hash
    if claim is not None and claim.claimed:
        try:
            with db._conn() as conn:
                record_idempotency_receipt(SimpleNamespace(_db=db, _conn=conn), claim, _receipt_data(receipt))
        except Exception as exc:
            logger.error("saga receipt persistence failed for %s: %s", key, exc)
            receipt = SagaReceipt(receipt.status, receipt.idempotency_key, receipt.steps,
                                  receipt.error, receipt.orphan_cleanup_pending,
                                  type(exc).__name__, receipt.post_commit_effects)
            # Keep the receipt durable even when the shared helper is
            # unavailable (for example, a transient worker-local failure).
            # A second worker can then replay the exact outcome instead of
            # being stuck at an indistinguishable in-progress claim.
            try:
                with db._conn() as conn:
                    ph = db._ph
                    meta = json.dumps({"request_hash": claim.request_hash, "receipt": _receipt_data(receipt)})
                    cast = "::jsonb" if getattr(db, "_use_pg", False) else ""
                    db._execute(conn, f"UPDATE request_idempotency_keys SET meta={ph}{cast} WHERE key={ph}", (meta, claim.key))
            except Exception:
                logger.error("saga receipt fallback persistence failed for %s", key, exc_info=True)
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


def _uploaded_values(uploaded: Any) -> list[Any]:
    """Extract candidate object keys without trusting a provider response shape."""
    if isinstance(uploaded, Mapping):
        values: list[Any] = []
        for value in uploaded.values():
            if isinstance(value, Mapping):
                for field in ("url", "key", "path"):
                    nested = value.get(field)
                    if nested:
                        values.append(nested)
            else:
                values.append(value)
        return values
    if isinstance(uploaded, (list, tuple, set, frozenset)):
        return list(uploaded)
    if isinstance(uploaded, str):
        return [uploaded]
    urls = getattr(uploaded, "urls", None)
    if isinstance(urls, Mapping):
        return list(urls.values())
    if isinstance(urls, (list, tuple, set, frozenset)):
        return list(urls)
    values = getattr(uploaded, "values", None)
    if callable(values):
        try:
            return list(values())
        except Exception:
            return []
    return []


def _cleanup_uploaded(storage_obj, suggestion_id: str, uploaded: Any = None) -> bool:
    failed = False
    values = _uploaded_values(uploaded)
    try:
        existing = list(getattr(storage_obj, "objects", ()))
    except Exception:
        existing = []
        failed = True
    values.extend(v for v in existing if suggestion_id in str(v))
    for value in dict.fromkeys(str(v) for v in values if v):
        try:
            storage_obj.delete(value)
        except Exception:
            failed = True
    return failed


def cleanup_uploaded_media(storage_obj, uploaded: Any = None) -> bool:
    """Compensate provider objects before an entity mutation has committed."""
    failed = False
    for value in dict.fromkeys(str(v) for v in _uploaded_values(uploaded) if v):
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


def _prepare_image_approval(
    suggestion_id: str, actor_id: str, key: str
) -> tuple[ClaimResult, SagaReceipt | None, Mapping[str, Any] | None]:
    """Resolve durable replay/conflict and load a still-pending suggestion."""
    claim, replay = _claim_command(key, suggestion_id, actor_id)
    if replay is not None:
        return claim, replay, None
    if claim.conflict:
        result = SagaReceipt("idempotency_conflict", key, error="idempotency_key_reused")
        return claim, _store_receipt(key, result, None), None
    with _SAGA_LOCK:
        previous = _SAGA_RECEIPTS.get(key)
    if previous is not None:
        return claim, previous, None
    suggestion = _imgq.get_suggestion(suggestion_id)
    if not suggestion:
        result = _suggestion_receipt(suggestion_id, actor_id, key, "not_found")
        return claim, _store_receipt(key, result, claim), None
    if suggestion.get("status") != "pending":
        result = _suggestion_receipt(
            suggestion_id, actor_id, key, "not_pending",
            current_status=suggestion.get("status"),
        )
        return claim, _store_receipt(key, result, claim), None
    return claim, None, suggestion


def _normalize_approval_upload(uploaded: Any) -> dict[str, str]:
    """Validate provider output before any entity mutation."""
    if not isinstance(uploaded, Mapping):
        raise RuntimeError("provider_invalid_response")
    normalized: dict[str, str] = {}
    for size in ("sm", "md", "lg"):
        if size not in uploaded:
            continue
        value = uploaded.get(size)
        if not isinstance(value, str) or not value.strip() or not (
            value.strip().startswith("/")
            or value.strip().startswith(("http://", "https://"))
        ):
            raise RuntimeError("provider_malformed_cover")
        normalized[size] = value.strip()
    if not normalized:
        raise RuntimeError("provider_missing_cover")
    if "credit" in uploaded:
        credit = uploaded.get("credit")
        if not isinstance(credit, str) or not credit.strip():
            raise RuntimeError("provider_malformed_credit")
    return normalized


def _approval_cover(uploaded: Mapping[str, str]) -> str:
    return uploaded.get("md") or uploaded.get("lg") or uploaded.get("sm") or ""


def _upload_approval_media(
    suggestion: Mapping[str, Any], actor_id: str, key: str, image_data: bytes | None
) -> tuple[dict[str, str] | None, SagaReceipt | None]:
    """Upload media and compensate provider objects on an exposed failure."""
    try:
        uploaded = storage.upload_image_set(
            image_data if image_data is not None else fetch_image_data(suggestion),
            "entities", f"{suggestion['entity_id']}-{suggestion['id']}",
        )
        return _normalize_approval_upload(uploaded), None
    except Exception as exc:
        try:
            orphan = _cleanup_uploaded(storage, str(suggestion["id"]), getattr(exc, "urls", {}))
        except Exception:
            logger.error("media compensation failed for %s", suggestion["id"], exc_info=True)
            orphan = True
        result = _suggestion_receipt(
            str(suggestion["id"]), actor_id, key,
            "failed_orphaned" if orphan else "failed_compensated",
            error=type(exc).__name__, orphan_cleanup_pending=orphan,
        )
        return None, result


def _compose_approved_entity(
    before: Mapping[str, Any], suggestion: Mapping[str, Any], cover: str
) -> dict[str, Any]:
    """Merge the approved cover and attribution into the latest entity row."""
    images = list(before.get("images") or [])
    if len(images) >= 10:
        raise RuntimeError("image_limit")
    if cover and cover not in images:
        images.append(cover)
    entity = copy.deepcopy(before)
    entity["images"] = images
    attrs = entity.get("attributes") if isinstance(entity.get("attributes"), dict) else {}
    credits = list(attrs.get("image_credits") or [])
    credits.append({
        "url": cover,
        "license": suggestion.get("license") or "",
        "author": suggestion.get("author") or "",
        "source": suggestion.get("source") or "",
        "source_url": suggestion.get("candidate_url") or "",
        "wp_title": suggestion.get("wp_title") or "",
    })
    attrs["image_credits"] = credits
    entity["attributes"] = attrs
    entity["updatedAt"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return entity


def _commit_image_approval(
    suggestion: Mapping[str, Any], actor_id: str, key: str,
    uploaded: Mapping[str, str], fallback_entity: Mapping[str, Any],
) -> Any:
    """Commit entity, audit, suggestion status, and generation atomically."""
    cover = _approval_cover(uploaded)
    with _entity_approval_lock(str(suggestion["entity_id"])):
        with db._conn() as conn:
            ph = db._ph
            lock_clause = " FOR UPDATE" if getattr(db, "_use_pg", False) else ""
            current_row = db._fetchone(
                conn, f"SELECT * FROM entities WHERE id = {ph}{lock_clause}",
                (suggestion["entity_id"],),
            )
            if not current_row:
                raise RuntimeError("entity_not_found")
            before = db._parse_entity(current_row) if hasattr(db, "_parse_entity") else copy.deepcopy(fallback_entity)
            entity = _compose_approved_entity(before, suggestion, cover)
            if hasattr(db, "_entity_writer"):
                db._entity_writer().upsert(conn, entity)
            if hasattr(db, "_bump_sqlite_entity_revision"):
                db._bump_sqlite_entity_revision(conn, before, entity)
            revision_row = db._fetchone(
                conn, f"SELECT revision FROM entities WHERE id = {db._ph}",
                (suggestion["entity_id"],),
            )
            revision = int((db._row_to_dict(revision_row) or {}).get("revision") or 1)
            record_entity_mutation(
                suggestion["entity_id"], actor_id=actor_id, reason="image_approval",
                correlation_id=key, before=before, after=entity, revision=revision,
                conn=conn, database=db,
            )
            if not _imgq.mark_status(suggestion["id"], "approved", approved_by=actor_id, conn=conn):
                raise RuntimeError("suggestion_not_pending")
            return bump_generation(conn, suggestion["entity_id"], "image_approval", key)


def _invalidate_approved_entity(entity_id: str, generation: Any) -> tuple[Mapping[str, Any], ...]:
    """Invalidate caches after commit without turning a committed write into failure."""
    try:
        invalidate_entity(entity_id, reason="image_approval", generation=generation.generation)
        return ({"effect": "invalidation", "status": "applied"},)
    except Exception as exc:
        logger.error("entity invalidation failed after image approval: %s", exc)
        return ({"effect": "invalidation", "status": "failed", "error": type(exc).__name__},)


def _approval_failure(
    suggestion_id: str, actor_id: str, key: str, marker: str,
    uploaded: Any, exc: Exception, claim: ClaimResult,
) -> SagaReceipt:
    """Turn a pre-commit failure into a receipt and release the pending claim."""
    if getattr(exc, "commit_outcome_unknown", False):
        result = _suggestion_receipt(
            suggestion_id, actor_id, key, "commit_unknown",
            error=type(exc).__name__, reconciliation_required=True,
        )
        return _store_receipt(key, result, claim)
    try:
        orphan = _cleanup_uploaded(storage, suggestion_id, uploaded)
    except Exception:
        logger.error("media compensation failed for %s", suggestion_id, exc_info=True)
        orphan = True
    result = _suggestion_receipt(
        suggestion_id, actor_id, key,
        "failed_orphaned" if orphan else "failed_compensated",
        error=type(exc).__name__, orphan_cleanup_pending=orphan,
    )
    _release_suggestion_claim(suggestion_id, marker)
    return _store_receipt(key, result, claim)


def approve_image_suggestion(suggestion_id: str, actor_id: str, *, idempotency_key: str,
                             _image_data: bytes | None = None) -> SagaReceipt:
    """Approve a pending suggestion with upload compensation and exact retries."""
    key = str(idempotency_key).strip()
    claim, immediate, suggestion = _prepare_image_approval(suggestion_id, actor_id, key)
    if immediate is not None:
        return immediate
    assert suggestion is not None
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
        uploaded, upload_failure = _upload_approval_media(suggestion, actor_id, key, _image_data)
        if upload_failure is not None:
            _release_suggestion_claim(suggestion_id, claim_marker)
            return _store_receipt(key, upload_failure, claim)
        assert uploaded is not None
        snapshot = _commit_image_approval(suggestion, actor_id, key, uploaded, entity)
        post_commit_effects = _invalidate_approved_entity(suggestion["entity_id"], snapshot)
        cover = _approval_cover(uploaded)
        result = _suggestion_receipt(suggestion_id, actor_id, key, "committed", url=cover, sizes=uploaded,
                                     post_commit_effects=post_commit_effects)
        return _store_receipt(key, result, claim)
    except Exception as exc:
        return _approval_failure(suggestion_id, actor_id, key, claim_marker, uploaded, exc, claim)
__all__ = ["SagaStep", "SagaReceipt", "MutationAuditEnvelope", "AuditEnvelope",
           "run_saga", "approve_image_suggestion", "peek_approval_receipt", "cleanup_uploaded_media",
           "record_entity_mutation"]
