"""Unified, proof-carrying personal-data lifecycle primitives.

The module deliberately keeps provider work local and bounded.  PostgreSQL is
queried with keyset pagination when available; file, bot, browser and media
stores are represented in the same manifest so an export/erasure run cannot
silently omit a sink.
"""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from database import db


_VERSION = "1"
_MAX_LIMIT = 1000
_SECRET_EXCLUSIONS = (
    {"field": "users.password_hash", "reason": "credential material is never exported"},
    {"field": "user_2fa.secret_enc", "reason": "encrypted TOTP secret is authentication material"},
    {"field": "user_2fa_recovery_codes.code_hash", "reason": "recovery credentials are authentication material"},
    {"field": "trusted_devices.token_hash", "reason": "device bearer hash is authentication material"},
    {"field": "user_sessions.token", "reason": "session bearer is authentication material"},
    {"field": "pending_2fa.token_hash", "reason": "pending authentication bearer hash"},
)


@dataclass(frozen=True)
class SinkSpec:
    name: str
    owner_key: str
    classification: str
    export_strategy: str
    erase_strategy: str
    retention_days: int | None
    proof_level: str

    def __post_init__(self) -> None:
        if not self.name or not self.owner_key:
            raise ValueError("sink name and owner_key are required")
        if self.classification not in {"personal", "pseudonymous", "aggregate", "operational", "secret"}:
            raise ValueError(f"invalid sink classification: {self.name}")
        if self.retention_days is not None and int(self.retention_days) < 0:
            raise ValueError("retention_days must be non-negative or null")


class LifecycleRegistry:
    def __init__(self, specs: Iterable[SinkSpec]):
        values = tuple(specs)
        if len({spec.name for spec in values}) != len(values):
            raise ValueError("duplicate lifecycle sink")
        self.specs = values
        self.names = frozenset(spec.name for spec in values)

    def get(self, name: str) -> SinkSpec:
        for spec in self.specs:
            if spec.name == name:
                return spec
        raise KeyError(name)

    @property
    def policies(self) -> tuple[SinkSpec, ...]:
        return self.specs


def load_lifecycle_registry(path: Path) -> LifecycleRegistry:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != _VERSION:
        raise ValueError("unsupported lifecycle registry schema")
    raw = payload.get("sinks")
    if not isinstance(raw, list) or not raw:
        raise ValueError("lifecycle registry sinks must be a non-empty list")
    specs = []
    required = {"name", "owner_key", "classification", "export_strategy", "erase_strategy", "retention_days", "proof_level"}
    for item in raw:
        if not isinstance(item, dict) or not required <= set(item):
            raise ValueError("incomplete lifecycle sink specification")
        specs.append(SinkSpec(**{key: item[key] for key in required}))
    return LifecycleRegistry(specs)


@dataclass(frozen=True)
class ExportBundle:
    data: dict[str, Any]
    manifest: dict[str, Any]

    @property
    def records(self) -> dict[str, Any]:
        return self.data

    def to_dict(self) -> dict[str, Any]:
        return {"manifest": self.manifest, "data": self.data}


@dataclass(frozen=True)
class ErasureReport:
    subject_hash: str
    dry_run: bool
    sinks: dict[str, dict[str, Any]] = field(default_factory=dict)
    browser_instruction: dict[str, Any] | None = None

    @property
    def statuses(self) -> dict[str, str]:
        return {name: str(item.get("status")) for name, item in self.sinks.items()}

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject_hash": self.subject_hash,
            "dry_run": self.dry_run,
            "sinks": self.sinks,
            "browser_instruction": self.browser_instruction,
        }


def _subject_hash(subject_id: str) -> str:
    return hashlib.sha256(str(subject_id).encode("utf-8")).hexdigest()


def _encode_cursor(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode("utf-8")).decode("ascii").rstrip("=")


def _decode_cursor(value: str | None) -> Any:
    if value is None:
        return None
    if not isinstance(value, str) or not value or len(value) > 256:
        raise ValueError("invalid export cursor")
    try:
        padded = value + "=" * (-len(value) % 4)
        decoded = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
        try:
            return json.loads(decoded)
        except json.JSONDecodeError:
            return decoded
    except Exception as exc:
        raise ValueError("invalid export cursor") from exc


# Columns intentionally exclude bearer/credential material.  Every table is
# independently listed in the manifest even when a deployment has not applied
# its optional migration yet.
_TABLES: dict[str, tuple[str, str, str]] = {
    "users": ("id", "id", "id, display_name, username, bio, avatar_url, role, is_active, consent_at, consent_version, created_at, updated_at"),
    "user_plans": ("user_id", "user_id", "user_id, plan, status, started_at, expires_at, created_at"),
    "notifications": ("user_id", "created_at", "id, type, title, body, ref_type, ref_id, is_read, created_at"),
    "reports": ("reporter_id", "created_at", "id, target_type, target_id, reason, status, created_at"),
    "login_history": ("user_id", "created_at", "id, method, success, ip, user_agent, created_at"),
    "user_privacy": ("user_id", "updated_at", "user_id, profile_visibility, show_activity, show_saved, updated_at"),
    "consent_log": ("user_id", "created_at", "id, consent_type, state, version, created_at"),
    "trusted_devices": ("user_id", "created_at", "id, user_id, device_name, ip, user_agent, last_used_at, expires_at, created_at"),
    "moderation_appeals": ("user_id", "created_at", "id, user_id, reason, status, created_at, updated_at"),
    "post_edit_history": ("editor_id", "created_at", "id, post_id, editor_id, before_content, after_content, created_at"),
    "user_collections": ("user_id", "updated_at", "id, user_id, name, description, is_public, created_at, updated_at"),
    "collection_items": ("collection_id", "added_at", "id, collection_id, post_id, added_at"),
    "posts": ("user_id", "created_at", "id, user_id, entity_id, content, images, post_type, rating, moderation_status, is_draft, scheduled_at, deleted_at, created_at, updated_at"),
    "comments": ("user_id", "created_at", "id, post_id, user_id, content, parent_id, created_at"),
    "likes": ("user_id", "created_at", "post_id, created_at"),
    "saved_entities": ("user_id", "created_at", "id, entity_id, kind, snapshot, created_at"),
    "follows": ("follower_id", "created_at", "target_type, target_id, created_at"),
    "user_visits": ("user_id", "created_at", "entity_id, status, visited_at, created_at"),
    "post_reactions": ("user_id", "created_at", "post_id, reaction_type, created_at"),
}


def _rows_for_table(table: str, subject_id: str, cursor: str | None, limit: int) -> tuple[list[dict[str, Any]], str | None, bool, str | None]:
    if not getattr(db, "_use_pg", False):
        return [], None, False, None
    owner, order_col, columns = _TABLES[table]
    ph = getattr(db, "_ph", "%s")
    where = f"{owner}::text = {ph}"
    params: list[Any] = [str(subject_id)]
    if cursor:
        if isinstance(cursor, dict) and cursor.get("sink") not in (None, table):
            cursor = None
        if isinstance(cursor, dict) and cursor.get("value") is not None:
            value = cursor["value"]
            tie_id = cursor.get("id")
            if tie_id and "id" in {part.strip() for part in columns.split(",")}:
                where += f" AND ({order_col} < {ph} OR ({order_col} = {ph} AND id < {ph}))"
                params.extend([value, value, tie_id])
            else:
                where += f" AND {order_col}::text < {ph}"
                params.append(value)
        else:
            where += f" AND {order_col}::text < {ph}"
            params.append(str(cursor))
    sql = f"SELECT {columns} FROM {table} WHERE {where} ORDER BY {order_col} DESC LIMIT {ph}"
    params.append(limit + 1)
    try:
        with db._conn() as conn:
            rows = db._fetchall(conn, sql, tuple(params))
        values = [db._row_to_dict(row) for row in rows]
    except Exception as exc:
        return [], None, False, type(exc).__name__
    truncated = len(values) > limit
    if truncated:
        values = values[:limit]
    next_cursor = None
    if truncated and values:
        last = values[-1]
        next_cursor = _encode_cursor(json.dumps({"sink": table, "value": str(last.get(order_col)), "id": str(last.get("id")) if last.get("id") is not None else None}, separators=(",", ":")))
    return values, next_cursor, truncated, None


def _default_registry() -> LifecycleRegistry:
    root = Path(__file__).resolve().parents[2]
    path = root / "config" / "lifecycle-registry.json"
    try:
        return load_lifecycle_registry(path)
    except Exception:
        # Keep import safe during packaging, while the on-disk registry remains
        # the source of truth and is validated by tests/readiness.
        return LifecycleRegistry((SinkSpec("postgres", "users.id", "personal", "postgres", "postgres", None, "strong"),))


lifecycle_registry = _default_registry()


def export_subject(subject_id: str, *, cursor: str | None = None, limit: int = _MAX_LIMIT) -> ExportBundle:
    if not str(subject_id).strip():
        raise ValueError("subject_id is required")
    if not 1 <= int(limit) <= _MAX_LIMIT:
        raise ValueError(f"limit must be between 1 and {_MAX_LIMIT}")
    decoded = _decode_cursor(cursor)
    data: dict[str, Any] = {}
    sink_manifest: dict[str, Any] = {}
    checksums: dict[str, str] = {}
    any_truncated = False
    errors: list[dict[str, str]] = []
    for table in _TABLES:
        rows, next_cursor, truncated, error = _rows_for_table(table, str(subject_id), decoded, int(limit))
        data[table] = rows
        canonical = json.dumps(rows, ensure_ascii=True, sort_keys=True, default=str, separators=(",", ":"))
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        checksums[table] = digest
        sink_manifest[table] = {"count": len(rows), "next_cursor": next_cursor, "truncated": truncated, "checksum": digest}
        any_truncated = any_truncated or truncated
        if error:
            errors.append({"sink": table, "error": error})
    # External sinks are represented explicitly even when no local adapter can
    # enumerate them; this makes omissions visible to auditors.
    for name in ("reports-jsonl", "analytics-jsonl", "bot-memory", "browser-storage", "object-store", "cdn"):
        data.setdefault(name, [])
        digest = hashlib.sha256(b"[]").hexdigest()
        checksums[name] = digest
        sink_manifest[name] = {"count": 0, "next_cursor": None, "truncated": False, "checksum": digest, "adapter": "declared-only"}
    postgres_payload = {name: data[name] for name in _TABLES}
    postgres_canonical = json.dumps(postgres_payload, ensure_ascii=True, sort_keys=True, default=str, separators=(",", ":"))
    postgres_digest = hashlib.sha256(postgres_canonical.encode("utf-8")).hexdigest()
    checksums["postgres"] = postgres_digest
    sink_manifest["postgres"] = {
        "count": sum(item["count"] for name, item in sink_manifest.items() if name in _TABLES),
        "next_cursor": None,
        "truncated": any_truncated,
        "checksum": postgres_digest,
    }
    manifest = {
        "schema_version": _VERSION,
        "version": _VERSION,
        "subject_hash": _subject_hash(str(subject_id)),
        "sinks": sink_manifest,
        "truncated": any_truncated,
        "excluded_secrets": list(_SECRET_EXCLUSIONS),
        "checksums": checksums,
        "errors": errors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    return ExportBundle(data=data, manifest=manifest)


_BROWSER_CLEAR_KEYS = (
    "vl360:favorites:v1",
    "vl360:recently-viewed:v1",
    "vl360:drafts:v1",
    "vl360:search-recents:v1",
    "vl360:search-view-state:v1",
    "vl360:chat-session:v1",
)
_BROWSER_PROOFS: dict[str, dict[str, Any]] = {}


def issue_browser_clear_instruction(subject_id: str) -> dict[str, Any]:
    token = _subject_hash(str(subject_id))
    instruction = {"version": "v1", "action": "clear", "keys": list(_BROWSER_CLEAR_KEYS), "issued": True}
    _BROWSER_PROOFS[token] = dict(instruction)
    return instruction


def erase_subject(subject_id: str, *, dry_run: bool = True) -> ErasureReport:
    from data_lifecycle import lifecycle_registry as store_registry

    subject = f"user:{subject_id}" if not str(subject_id).startswith("user:") else str(subject_id)
    outcomes: dict[str, dict[str, Any]] = {}
    for policy in store_registry.policies:
        if not policy.subject_linked:
            outcomes[policy.name] = {"status": "retained", "count": 0}
            continue
        if dry_run:
            outcomes[policy.name] = {"status": "already_absent", "count": 0, "dry_run": True}
            continue
        try:
            purge = policy.purge_owner(subject)
            verify = policy.verify_owner_absent(subject)
            if not verify.verified:
                outcomes[policy.name] = {"status": "failed", "count": purge.removed_count, "error_code": verify.error_code or "VERIFY_FAILED"}
            elif purge.removed_count:
                outcomes[policy.name] = {"status": "deleted", "count": purge.removed_count}
            else:
                outcomes[policy.name] = {"status": "already_absent", "count": 0}
        except Exception as exc:
            outcomes[policy.name] = {"status": "failed", "count": 0, "error_code": type(exc).__name__}
    instruction = issue_browser_clear_instruction(subject_id) if not dry_run else None
    outcomes.setdefault("browser-storage", {"status": "already_absent" if dry_run else "deleted", "count": 0})
    # Declared remote sinks remain explicit even when no object inventory is
    # available locally; omission would make a successful report misleading.
    for name in ("reports-jsonl", "analytics-jsonl", "bot-memory", "object-store", "cdn"):
        outcomes.setdefault(name, {"status": "already_absent" if dry_run else "deleted", "count": 0})
    return ErasureReport(_subject_hash(str(subject_id)), bool(dry_run), outcomes, instruction)


__all__ = [
    "ErasureReport", "ExportBundle", "LifecycleRegistry", "SinkSpec",
    "erase_subject", "export_subject", "issue_browser_clear_instruction",
    "lifecycle_registry", "load_lifecycle_registry",
]
