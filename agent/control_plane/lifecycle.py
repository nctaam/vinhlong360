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
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from database import db


_VERSION = "1"
_MAX_LIMIT = 1000
_EXPORT_STRATEGIES = {
    "postgres", "table-manifest", "row-keyset", "joined-row-keyset",
    "metadata-only", "jsonl-owner-scan", "bounded-memory", "instruction-only",
    "media-manifest", "excluded", "unavailable",
}
_ERASE_STRATEGIES = {
    "transactional", "hard-delete", "delete", "unlink-or-delete", "retain-hash",
    "cascade", "filter-rewrite", "evict-owner", "versioned-clear", "delete-receipt",
    "purge-receipt", "issued-only", "unavailable",
}
_PROOF_LEVELS = {"strong", "bounded", "instruction", "receipt", "hash-only", "unavailable"}
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
        if self.classification not in {"personal", "pseudonymous", "aggregate", "operational"}:
            raise ValueError(f"invalid sink classification: {self.name}")
        if self.retention_days is not None and int(self.retention_days) < 0:
            raise ValueError("retention_days must be non-negative or null")
        if self.export_strategy not in _EXPORT_STRATEGIES:
            raise ValueError(f"invalid export_strategy: {self.name}")
        if self.erase_strategy not in _ERASE_STRATEGIES:
            raise ValueError(f"invalid erase_strategy: {self.name}")
        if self.proof_level not in _PROOF_LEVELS:
            raise ValueError(f"invalid proof_level: {self.name}")


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
        unknown = set(item) - required
        if unknown:
            raise ValueError(f"unknown lifecycle sink keys: {sorted(unknown)}")
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

    @property
    def verified(self) -> bool:
        if self.dry_run:
            return False
        return all(status in {"deleted", "already_absent"} for status in self.statuses.values())

    @property
    def success(self) -> bool:
        return self.verified

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject_hash": self.subject_hash,
            "dry_run": self.dry_run,
            "sinks": self.sinks,
            "browser_instruction": self.browser_instruction,
        }


def _subject_hash(subject_id: str) -> str:
    return hashlib.sha256(str(subject_id).encode("utf-8")).hexdigest()


def _canonical_owner(subject_id: str) -> str:
    """Use one owner namespace across analytics, reports and erasure adapters."""
    value = str(subject_id)
    return value if value.startswith("user:") else f"user:{value}"


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
    "user_plans": ("user_id", "created_at", "id, user_id, title, stops, created_at"),
    "notifications": ("user_id", "created_at", "id, type, title, body, ref_type, ref_id, is_read, created_at"),
    # Export only the report metadata needed by the account owner. Contact is
    # intentionally excluded; bearer/IP material is never part of a bundle.
    "reports": ("reporter_id", "created_at", "id, target_type, target_id, reason, status, detail, field, revision, created_at, updated_at, correlation_id, source_channel, legacy_locator"),
    "login_history": ("user_id", "created_at", "id, method, success, ip, user_agent, created_at"),
    "user_privacy": ("user_id", "updated_at", "user_id, profile_visibility, show_activity, show_saved, updated_at"),
    "consent_log": ("user_id", "created_at", "id, user_id, version, ip, created_at"),
    "trusted_devices": ("user_id", "created_at", "id, user_id, device_name, ip, user_agent, last_used_at, expires_at, created_at"),
    "moderation_appeals": ("user_id", "created_at", "id, post_id, user_id, reason, status, reviewer_id, reviewer_note, reviewed_at, created_at"),
    "post_edit_history": ("editor_id", "created_at", "id, post_id, editor_id, old_content, old_rating, edit_reason, created_at"),
    "user_collections": ("user_id", "updated_at", "id, user_id, name, description, is_public, created_at, updated_at"),
    "collection_items": ("collection_id", "added_at", "id, collection_id, post_id, added_at"),
    "posts": ("user_id", "created_at", "id, user_id, entity_id, content, images, post_type, rating, moderation_status, is_draft, scheduled_at, deleted_at, created_at, updated_at"),
    "comments": ("user_id", "created_at", "id, post_id, user_id, content, parent_id, created_at"),
    "likes": ("user_id", "created_at", "post_id, created_at"),
    "saved_entities": ("user_id", "created_at", "id, entity_id, kind, snapshot, created_at"),
    "follows": ("follower_id", "created_at", "target_type, target_id, created_at"),
    "user_visits": ("user_id", "created_at", "entity_id, status, visited_at, created_at"),
    "post_reactions": ("user_id", "created_at", "post_id, reaction_type, created_at"),
    "blocks": ("blocker_id", "created_at", "blocked_id, created_at"),
    "user_mutes": ("user_id", "created_at", "muted_id, created_at"),
    "user_sessions": ("user_id", "created_at", "id, user_id, expires_at, created_at"),
    "user_2fa": ("user_id", "user_id", "user_id, enabled, created_at, updated_at"),
    "user_2fa_recovery_codes": ("user_id", "created_at", "id, user_id, used, created_at"),
    "pending_2fa": ("user_id", "created_at", "id, user_id, expires_at, created_at"),
    # Secondary account-owned tables from optional feature migrations. Keep
    # these explicit so export and erasure cannot silently diverge.
    "event_rsvp": ("user_id", "created_at", "user_id, entity_id, created_at"),
    "notification_preferences": ("user_id", "updated_at", "user_id, pref_like, pref_comment, pref_mention, pref_follow, pref_system, updated_at"),
    "comment_likes": ("user_id", "created_at", "user_id, comment_id, created_at"),
    "user_hidden_posts": ("user_id", "created_at", "user_id, post_id, created_at"),
    "user_achievements": ("user_id", "unlocked_at", "user_id, achievement_id, unlocked_at"),
    "profile_views": ("viewer_id", "created_at", "id, viewer_id, viewed_id, viewed_date, created_at"),
    "user_preferences": ("user_id", "updated_at", "user_id, region_id, region_label, region_scope, location_source, location_accuracy, location_consent_state, location_enabled, personalization_enabled, explicit_interests, recommendation_reset_at, consent_version, revision, location_reconfirm_required, location_provenance_version, created_at, updated_at"),
    "user_preference_consents": ("user_id", "created_at", "id, user_id, consent_type, state, version, created_at"),
    "user_personalization_events": ("user_id", "occurred_at", "id, user_id, event_type, context, entity_id, entity_type, area_id, interest_keys, occurred_at, expires_at"),
    "personalization_legacy_purge_queue": ("user_id", "created_at", "user_id, created_at, attempt_count, next_attempt_at, last_error"),
}
_TABLE_TIES = {
    "likes": ("post_id",), "follows": ("target_type", "target_id"),
    "user_visits": ("visited_at", "entity_id", "status"),
    "post_reactions": ("post_id", "reaction_type"), "user_2fa": ("enabled",),
    "blocks": ("blocked_id",), "user_mutes": ("muted_id",),
    "event_rsvp": ("entity_id",), "comment_likes": ("comment_id",),
    "user_hidden_posts": ("post_id",), "user_achievements": ("achievement_id",),
    "user_preference_consents": ("consent_type",),
    "user_personalization_events": ("event_type", "id"),
    "personalization_legacy_purge_queue": ("user_id",),
}


def _cursor_offset(cursor: Any, table: str) -> int:
    if isinstance(cursor, dict) and cursor.get("sink") in (None, table) and str(cursor.get("offset", "0")).isdigit():
        return int(cursor.get("offset", 0))
    return 0


def _query_page(sql: str, params: list[Any], limit: int) -> tuple[list[dict[str, Any]], str | None]:
    try:
        with db._conn() as conn:
            rows = db._fetchall(conn, sql, tuple(params))
        return [db._row_to_dict(row) for row in rows], None
    except Exception as exc:
        return [], type(exc).__name__


def _page_cursor(table: str, values: list[dict[str, Any]], order_col: str, offset: int, limit: int, truncated: bool) -> str | None:
    if not truncated or not values:
        return None
    last = values[-1]
    payload = {
        "sink": table,
        "offset": offset + limit,
        "value": str(last.get(order_col)),
        "id": str(last.get("id")) if last.get("id") is not None else None,
    }
    return _encode_cursor(json.dumps(payload, separators=(",", ":")))


def _collection_items_page(subject_id: str, cursor: Any, limit: int, offset: int, ph: str) -> tuple[list[dict[str, Any]], str | None, bool, str | None]:
    # Items are owned through the user's collection, not by collection_id.
    where = f"uc.user_id::text = {ph}"
    params: list[Any] = [str(subject_id)]
    if cursor and not (isinstance(cursor, dict) and "offset" in cursor) and not offset:
        where += f" AND (ci.added_at::text, ci.id::text) < ({ph}, {ph})"
        params.extend([str(cursor.get("value")), str(cursor.get("id"))])
    sql = (
        "SELECT ci.id, ci.collection_id, ci.post_id, ci.added_at "
        f"FROM collection_items ci JOIN user_collections uc ON uc.id = ci.collection_id WHERE {where} "
        f"ORDER BY ci.added_at DESC, ci.id DESC LIMIT {ph} OFFSET {ph}"
    )
    params.extend([limit + 1, offset])
    values, error = _query_page(sql, params, limit)
    truncated = len(values) > limit
    values = values[:limit]
    return values, _page_cursor("collection_items", values, "added_at", offset, limit, truncated), truncated, error


def _table_filter(table: str, subject_id: str, cursor: Any, owner: str, order_col: str, columns: str, ph: str) -> tuple[str, list[Any]]:
    if table == "profile_views":
        # A profile-view row is personal to both participants.
        where = f"(viewer_id::text = {ph} OR viewed_id::text = {ph})"
        params: list[Any] = [str(subject_id), str(subject_id)]
    else:
        where = f"{owner}::text = {ph}"
        params = [str(subject_id)]
    if not cursor or (isinstance(cursor, dict) and "offset" in cursor):
        return where, params
    if isinstance(cursor, dict) and cursor.get("sink") not in (None, table):
        cursor = None
    if isinstance(cursor, dict) and cursor.get("value") is not None:
        value = cursor["value"]
        tie_id = cursor.get("id")
        has_id = "id" in {part.strip() for part in columns.split(",")}
        if tie_id and has_id:
            where += f" AND ({order_col} < {ph} OR ({order_col} = {ph} AND id < {ph}))"
            params.extend([value, value, tie_id])
            return where, params
        where += f" AND {order_col}::text < {ph}"
        params.append(value)
        return where, params
    where += f" AND {order_col}::text < {ph}"
    params.append(str(cursor))
    return where, params


def _table_order(table: str, order_col: str, columns: str) -> str:
    if "id" in {part.strip() for part in columns.split(",")}:
        return f"{order_col} DESC, id DESC"
    ties = _TABLE_TIES.get(table, ())
    return ", ".join([f"{order_col} DESC", *[f"{col} DESC" for col in ties]])


def _rows_for_table(table: str, subject_id: str, cursor: str | None, limit: int) -> tuple[list[dict[str, Any]], str | None, bool, str | None]:
    if not getattr(db, "_use_pg", False):
        return [], None, False, None
    owner, order_col, columns = _TABLES[table]
    ph = getattr(db, "_ph", "%s")
    offset = _cursor_offset(cursor, table)
    if table == "collection_items":
        return _collection_items_page(subject_id, cursor, limit, offset, ph)
    where, params = _table_filter(table, subject_id, cursor, owner, order_col, columns, ph)
    sql = f"SELECT {columns} FROM {table} WHERE {where} ORDER BY {_table_order(table, order_col, columns)} LIMIT {ph} OFFSET {ph}"
    params.extend([limit + 1, offset])
    values, error = _query_page(sql, params, limit)
    truncated = len(values) > limit
    values = values[:limit]
    return values, _page_cursor(table, values, order_col, offset, limit, truncated), truncated, error


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


def _external_rows(name: str, owner: str) -> tuple[list[dict[str, Any]], str | None, str]:
    if name == "analytics-jsonl":
        import analytics
        return analytics.export_owner_records(owner), None, "analytics"
    if name == "bot-memory":
        import bot_gateway
        if not hasattr(bot_gateway, "export_subject_memory"):
            return [], "ADAPTER_UNAVAILABLE", "bot"
        return bot_gateway.export_subject_memory(owner), None, "bot"
    if name == "reports-jsonl":
        from admin import _INFO_REPORTS_FILE
        rows = []
        if _INFO_REPORTS_FILE.exists():
            for line in _INFO_REPORTS_FILE.read_text(encoding="utf-8").splitlines():
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if str(item.get("owner_key", item.get("user_id", item.get("reporter_id", "")))) == owner:
                    rows.append(item)
        return rows, None, "reports"
    return [], "ADAPTER_UNAVAILABLE", "unavailable"


def _external_page(rows: list[dict[str, Any]], limit: int, cursor: Any) -> tuple[list[dict[str, Any]], str | None, bool]:
    offset = int(cursor) if isinstance(cursor, str) and cursor.isdigit() else 0
    page = rows[offset:offset + limit]
    truncated = offset + limit < len(rows)
    next_cursor = _encode_cursor(str(offset + limit)) if truncated else None
    return page, next_cursor, truncated


def _external_export(name: str, subject_id: str, limit: int, cursor: Any = None) -> tuple[list[dict[str, Any]], str | None, bool, str | None, str]:
    """Enumerate local adapters; unavailable providers are explicit, never empty-success."""
    owner = _canonical_owner(subject_id)
    try:
        rows, error, adapter = _external_rows(name, owner)
        page, next_cursor, truncated = _external_page(rows, limit, cursor)
        return page, next_cursor, truncated, error, adapter
    except Exception as exc:
        return [], None, False, type(exc).__name__, "local"


def _digest_rows(payload: Any) -> str:
    canonical = json.dumps(payload, ensure_ascii=True, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _table_export_entry(table: str, subject_id: str, decoded: Any, limit: int) -> tuple[list[dict[str, Any]], dict[str, Any], str, bool, str | None]:
    rows, next_cursor, truncated, error = _rows_for_table(table, subject_id, decoded, limit)
    digest = _digest_rows(rows)
    columns = _TABLES[table][2]
    has_id = "id" in {part.strip() for part in columns.split(",")}
    manifest = {
        "count": len(rows),
        "next_cursor": next_cursor,
        "truncated": truncated,
        "checksum": digest,
        "pagination": "stable-offset" if table in _TABLE_TIES or not has_id else "keyset",
        "consistency": "snapshot-at-request; concurrent mutations may shift offset pages",
    }
    return rows, manifest, digest, truncated, error


def _external_cursor(decoded: Any, name: str) -> Any:
    if isinstance(decoded, dict) and decoded.get("sink") == name:
        return str(decoded.get("offset", 0))
    return decoded if isinstance(decoded, str) else None


def _external_sink_entry(name: str, subject_id: str, decoded: Any, limit: int) -> tuple[list[dict[str, Any]], dict[str, Any], str, bool, str | None]:
    adapters = {"reports-jsonl", "analytics-jsonl", "bot-memory"}
    if name in adapters:
        rows, next_cursor, truncated, error, adapter = _external_export(name, subject_id, limit, _external_cursor(decoded, name))
    else:
        rows, next_cursor, truncated, error, adapter = [], None, False, "ADAPTER_UNAVAILABLE", "unavailable"
    digest = _digest_rows(rows)
    manifest = {"count": len(rows), "next_cursor": next_cursor, "truncated": truncated, "checksum": digest, "adapter": adapter, "status": "error" if error else "available"}
    return rows, manifest, digest, truncated, error


def _postgres_manifest(data: dict[str, Any], sink_manifest: dict[str, Any], checksums: dict[str, str], truncated: bool, errors: list[dict[str, str]]) -> None:
    payload = {name: data[name] for name in _TABLES}
    digest = _digest_rows(payload)
    checksums["postgres"] = digest
    sink_manifest["postgres"] = {
        "count": sum(item["count"] for name, item in sink_manifest.items() if name in _TABLES),
        "next_cursor": None,
        "truncated": truncated,
        "degraded": bool(errors),
        "checksum": digest,
    }


def export_subject(subject_id: str, *, cursor: str | None = None, limit: int = _MAX_LIMIT) -> ExportBundle:
    if not str(subject_id).strip():
        raise ValueError("subject_id is required")
    if not 1 <= int(limit) <= _MAX_LIMIT:
        raise ValueError(f"limit must be between 1 and {_MAX_LIMIT}")
    subject = str(subject_id)
    decoded = _decode_cursor(cursor)
    data: dict[str, Any] = {}
    sink_manifest: dict[str, Any] = {}
    checksums: dict[str, str] = {}
    any_truncated = False
    errors: list[dict[str, str]] = []
    for table in _TABLES:
        rows, entry, digest, truncated, error = _table_export_entry(table, subject, decoded, int(limit))
        data[table], sink_manifest[table], checksums[table] = rows, entry, digest
        any_truncated = any_truncated or truncated
        if error:
            errors.append({"sink": table, "error": error})
    for name in ("reports-jsonl", "analytics-jsonl", "bot-memory", "browser-storage", "object-store", "cdn"):
        rows, entry, digest, truncated, error = _external_sink_entry(name, subject, decoded, int(limit))
        data[name], sink_manifest[name], checksums[name] = rows, entry, digest
        any_truncated = any_truncated or truncated
        if error:
            errors.append({"sink": name, "error": error})
    _postgres_manifest(data, sink_manifest, checksums, any_truncated, errors)
    manifest = {
        "schema_version": _VERSION,
        "version": _VERSION,
        "subject_hash": _subject_hash(subject),
        "sinks": sink_manifest,
        "truncated": any_truncated,
        "degraded": bool(errors) or any(bool(item.get("degraded")) for item in sink_manifest.values()),
        "excluded_secrets": list(_SECRET_EXCLUSIONS),
        "checksums": checksums,
        "errors": errors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    return ExportBundle(data=data, manifest=manifest)


_BROWSER_CLEAR_KEYS = (
    "vl360_favorites", "vl360_recent", "vl360_post_draft", "vl360_recent_searches",
    "vinhlong360:public-search-entries:v2", "chat_sid", "vl360_plans", "vl360_planner_draft",
    "vl360:journey-thread:v1",
)
_BROWSER_PROOFS: dict[str, dict[str, Any]] = {}


def _browser_db_table() -> bool:
    """Create the durable browser-proof table on local/test databases."""
    try:
        db.initialize()
        if getattr(db, "_use_pg", False):
            with db._conn(commit_on_success=False) as conn:
                db._fetchone(conn, "SELECT 1 FROM browser_clear_instructions LIMIT 1", ())
            return True
        with db._conn() as conn:
            db._execute(conn, """
                CREATE TABLE IF NOT EXISTS browser_clear_instructions (
                    issuance_id TEXT PRIMARY KEY,
                    subject_hash TEXT NOT NULL,
                    instruction_json TEXT NOT NULL,
                    issued_at TEXT NOT NULL
                )
            """, ())
        return True
    except Exception:
        return False


def issue_browser_clear_instruction(subject_id: str) -> dict[str, Any]:
    token = _subject_hash(str(subject_id))
    issuance_id = uuid.uuid4().hex
    instruction = {"version": "v1", "action": "clear", "keys": list(_BROWSER_CLEAR_KEYS), "issued": True, "subject_hash": token, "issuance_id": issuance_id}
    _BROWSER_PROOFS[issuance_id] = dict(instruction)
    if _browser_db_table():
        try:
            with db._conn() as conn:
                db._execute(conn, "INSERT INTO browser_clear_instructions (issuance_id, subject_hash, instruction_json, issued_at) VALUES ({0}, {0}, {0}, {0})".format(db._ph), (issuance_id, token, json.dumps(instruction, sort_keys=True), datetime.now(timezone.utc).isoformat()))
        except Exception:
            pass
    return instruction


def get_browser_clear_instruction(issuance_id: str) -> dict[str, Any] | None:
    """Retrieve an issuance proof from durable storage after a restart."""
    cached = _BROWSER_PROOFS.get(str(issuance_id))
    if cached is not None:
        return dict(cached)
    if not _browser_db_table():
        return None
    try:
        with db._conn(commit_on_success=False) as conn:
            row = db._fetchone(conn, "SELECT instruction_json FROM browser_clear_instructions WHERE issuance_id = " + db._ph, (str(issuance_id),))
        if row:
            value = db._row_to_dict(row).get("instruction_json")
            proof = json.loads(value) if isinstance(value, str) else value
            if isinstance(proof, dict):
                _BROWSER_PROOFS[str(issuance_id)] = dict(proof)
                return dict(proof)
    except Exception:
        return None
    return None


def _erase_analytics(owner: str) -> dict[str, Any]:
    import analytics
    removed = analytics.purge_owner_records(owner)
    return {"status": "deleted" if removed else "already_absent", "count": removed}


def _erase_bot(owner: str) -> dict[str, Any]:
    import bot_gateway
    if not hasattr(bot_gateway, "purge_subject_memory"):
        return {"status": "unavailable", "count": 0, "error_code": "ADAPTER_UNAVAILABLE"}
    removed = bot_gateway.purge_subject_memory(owner)
    verified = bot_gateway.verify_subject_memory_absent(owner)
    status = "deleted" if removed and verified else "already_absent" if verified else "failed"
    return {"status": status, "count": removed}


def _erase_reports(owner: str) -> dict[str, Any]:
    from admin import _INFO_REPORTS_FILE, _info_reports_lock
    with _info_reports_lock:
        if not _INFO_REPORTS_FILE.exists():
            return {"status": "already_absent", "count": 0}
        lines = _INFO_REPORTS_FILE.read_text(encoding="utf-8").splitlines()
        kept, removed = [], 0
        for line in lines:
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                kept.append(line)
                continue
            owner_value = item.get("owner_key", item.get("user_id", item.get("reporter_id", "")))
            if str(owner_value) == owner:
                removed += 1
            else:
                kept.append(line)
        if removed:
            tmp = _INFO_REPORTS_FILE.with_suffix(".tmp")
            tmp.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
            tmp.replace(_INFO_REPORTS_FILE)
        return {"status": "deleted" if removed else "already_absent", "count": removed}


def _named_external_erase(name: str, owner: str) -> dict[str, Any] | None:
    handlers = {
        "analytics-jsonl": _erase_analytics,
        "bot-memory": _erase_bot,
        "reports-jsonl": _erase_reports,
    }
    handler = handlers.get(name)
    return handler(owner) if handler else None


def _external_erase(name: str, subject_id: str, *, dry_run: bool) -> dict[str, Any]:
    if dry_run:
        return {"status": "retained", "count": 0, "dry_run": True}
    owner = _canonical_owner(subject_id)
    try:
        result = _named_external_erase(name, owner)
        if result is not None:
            return result
    except Exception as exc:
        return {"status": "failed", "count": 0, "error_code": type(exc).__name__}
    if name == "browser-storage":
        return {"status": "issued", "count": 0, "error_code": "BROWSER_CLIENT_ACTION_REQUIRED"}
    return {"status": "retained", "count": 0, "error_code": "ADAPTER_UNAVAILABLE"}


_POSTGRES_EXTRA_OWNERS = {
    "blocks": "blocker_id", "user_mutes": "user_id", "user_sessions": "user_id",
    "user_2fa": "user_id", "user_2fa_recovery_codes": "user_id", "pending_2fa": "user_id",
    "event_rsvp": "user_id", "notification_preferences": "user_id",
    "comment_likes": "user_id", "user_hidden_posts": "user_id",
    "user_achievements": "user_id", "user_preferences": "user_id",
    "user_preference_consents": "user_id", "user_personalization_events": "user_id",
    "personalization_legacy_purge_queue": "user_id",
    "profile_views": "viewer_id",
}


def _erase_postgres_extra(name: str, subject_id: str, *, dry_run: bool) -> dict[str, Any]:
    if dry_run:
        return {"status": "retained", "count": 0, "dry_run": True}
    if not getattr(db, "_use_pg", False):
        return {"status": "unavailable", "count": 0, "error_code": "DB_UNAVAILABLE"}
    column = _POSTGRES_EXTRA_OWNERS[name]
    ph = getattr(db, "_ph", "%s")
    try:
        with db._conn() as conn:
            if name == "profile_views":
                result = db._execute(conn, f"DELETE FROM {name} WHERE viewer_id::text = {ph} OR viewed_id::text = {ph}", (str(subject_id), str(subject_id)))
            else:
                result = db._execute(conn, f"DELETE FROM {name} WHERE {column}::text = {ph}", (str(subject_id),))
            removed = int(getattr(result, "rowcount", 0) or 0)
        return {"status": "deleted" if removed else "already_absent", "count": removed}
    except Exception as exc:
        return {"status": "failed", "count": 0, "error_code": type(exc).__name__}


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
    for name in ("reports-jsonl", "analytics-jsonl", "bot-memory", "object-store", "cdn"):
        outcomes[name] = _external_erase(name, subject, dry_run=dry_run)
    outcomes["browser-storage"] = _external_erase("browser-storage", subject, dry_run=dry_run)
    for name in _POSTGRES_EXTRA_OWNERS:
        outcomes[name] = _erase_postgres_extra(name, str(subject_id), dry_run=dry_run)
    return ErasureReport(_subject_hash(str(subject_id)), bool(dry_run), outcomes, instruction)


__all__ = [
    "ErasureReport", "ExportBundle", "LifecycleRegistry", "SinkSpec",
    "erase_subject", "export_subject", "issue_browser_clear_instruction",
    "get_browser_clear_instruction",
    "lifecycle_registry", "load_lifecycle_registry",
]
