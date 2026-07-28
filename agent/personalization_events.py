"""Privacy-safe PostgreSQL persistence for bounded personalization signals."""

from __future__ import annotations

import json
import os
import re
import tempfile
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from config import settings
from database import db
from user_preferences import PreferenceSnapshot, _row_snapshot
from versioned_json_store import fsync_directory, publication_lock


MAX_EVENT_LIMIT = 300
MAX_INTEREST_KEYS = 12
EVENT_TTL_DAYS = 90
PERSONALIZATION_EVENT_TYPES = frozenset(
    {
        "community_view",
        "entity_view",
        "itinerary_view",
        "map_focus",
        "post_view",
        "save_add",
        "save_remove",
        "search",
        "search_submit",
        "visit_mark",
    }
)
PERSONALIZATION_CONTEXTS = frozenset(
    {"community", "entity", "home", "itinerary", "map", "saved", "search", "unknown"}
)
PERSONALIZATION_ENTITY_TYPES = frozenset(
    {
        "accommodation",
        "attraction",
        "cafe",
        "craft_village",
        "dish",
        "drink",
        "event",
        "experience",
        "facility",
        "history",
        "itinerary",
        "nature",
        "organization",
        "person",
        "place",
        "product",
        "restaurant",
    }
)
PERSONALIZATION_INTEREST_KEYS = frozenset(
    {"craft", "culture", "food", "garden", "local_products", "stay"}
)
_NORMALIZED_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,199}$")
_LEGACY_EVENT_FIELDS = frozenset(
    {
        "ts",
        "occurred_at",
        "user_id",
        "event_type",
        "context",
        "entity_id",
        "entity_type",
        "entity_name",
        "area",
        "area_id",
        "interest_keys",
        "query",
        "metadata",
        "ip_hash",
    }
)
LEGACY_EVENTS_PATH = Path(__file__).resolve().parent / "data" / "user_events.jsonl"
LEGACY_EVENTS_LOCK_PATH = LEGACY_EVENTS_PATH.with_name(
    ".user_events.personalization.publication.lock"
)


class PersonalizationEventError(ValueError):
    """Raised when a required event identifier is invalid."""


def _owner_id(value: Any) -> str:
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError, AttributeError) as exc:
        raise PersonalizationEventError("Invalid user identifier") from exc


def _bounded_text(value: Any, maximum: int, *, lower: bool = False) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized:
        return None
    normalized = normalized.lower() if lower else normalized
    return normalized[:maximum]


def _controlled_key(value: Any, field: str, allowed: frozenset[str]) -> str:
    normalized = _bounded_text(value, 64, lower=True)
    if normalized is None or normalized not in allowed:
        raise PersonalizationEventError(f"Invalid {field}")
    return normalized


def _optional_identifier(value: Any, field: str) -> str | None:
    if value is not None and len(str(value).strip()) > 200:
        raise PersonalizationEventError(f"Invalid {field}")
    normalized = _bounded_text(value, 200, lower=True)
    if normalized is None:
        return None
    if not _NORMALIZED_ID_RE.fullmatch(normalized):
        raise PersonalizationEventError(f"Invalid {field}")
    return normalized


def _optional_controlled_key(
    value: Any, field: str, allowed: frozenset[str]
) -> str | None:
    if value is None:
        return None
    return _controlled_key(value, field, allowed)


def _timestamp(value: Any, default: datetime) -> datetime:
    if value is None:
        parsed = default
    elif isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and len(value) <= 64:
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError as exc:
            raise PersonalizationEventError("Invalid event timestamp") from exc
    else:
        raise PersonalizationEventError("Invalid event timestamp")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _interest_keys(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, (list, tuple)):
        raise PersonalizationEventError("Invalid interest_keys")
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in value:
        key = _bounded_text(raw, 64, lower=True)
        if key is None or key not in PERSONALIZATION_INTEREST_KEYS:
            raise PersonalizationEventError("Invalid interest_keys")
        if key in seen:
            continue
        seen.add(key)
        normalized.append(key)
        if len(normalized) == MAX_INTEREST_KEYS:
            break
    return normalized


def _normalized_event(event: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(event, Mapping):
        raise PersonalizationEventError("Event must be an object")
    occurred_at = _timestamp(event.get("occurred_at"), datetime.now(timezone.utc))
    expires_at = _timestamp(
        event.get("expires_at"), occurred_at + timedelta(days=EVENT_TTL_DAYS)
    )
    return {
        "event_type": _controlled_key(
            event.get("event_type"), "event_type", PERSONALIZATION_EVENT_TYPES
        ),
        "context": _controlled_key(
            event.get("context") or "unknown", "context", PERSONALIZATION_CONTEXTS
        ),
        "entity_id": _optional_identifier(event.get("entity_id"), "entity_id"),
        "entity_type": _optional_controlled_key(
            event.get("entity_type"), "entity_type", PERSONALIZATION_ENTITY_TYPES
        ),
        "area_id": _optional_identifier(event.get("area_id"), "area_id"),
        "interest_keys": _interest_keys(event.get("interest_keys")),
        "occurred_at": occurred_at,
        "expires_at": expires_at,
    }


def write_personalization_event(user_id: str, event: Mapping[str, Any]) -> None:
    """Persist only the allowlisted normalized event shape."""
    owner = _owner_id(user_id)
    normalized = _normalized_event(event)
    with db._conn() as conn:
        db._execute(
            conn,
            """
            INSERT INTO user_personalization_events
                (id, user_id, event_type, context, entity_id, entity_type,
                 area_id, interest_keys, occurred_at, expires_at)
            VALUES (%s, %s::uuid, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
            """,
            (
                str(uuid4()),
                owner,
                normalized["event_type"],
                normalized["context"],
                normalized["entity_id"],
                normalized["entity_type"],
                normalized["area_id"],
                json.dumps(normalized["interest_keys"], ensure_ascii=True),
                normalized["occurred_at"],
                normalized["expires_at"],
            ),
        )


def read_personalization_events(
    user_id: str, cutoff: datetime | str | None, limit: int = MAX_EVENT_LIMIT
) -> list[dict]:
    """Read current events after the strict reset boundary."""
    owner = _owner_id(user_id)
    bounded_limit = max(1, min(int(limit), MAX_EVENT_LIMIT))
    conditions = ["user_id = %s::uuid", "expires_at > NOW()"]
    params: list[Any] = [owner]
    if cutoff is not None:
        conditions.append("occurred_at > %s")
        params.append(_timestamp(cutoff, datetime.now(timezone.utc)))
    params.append(bounded_limit)
    with db._conn(commit_on_success=False) as conn:
        rows = db._fetchall(
            conn,
            "SELECT event_type, context, entity_id, entity_type, area_id, "
            "interest_keys, occurred_at, expires_at "
            "FROM user_personalization_events WHERE "
            + " AND ".join(conditions)
            + " ORDER BY occurred_at DESC, id DESC LIMIT %s",
            params,
        )
    return [db._row_to_dict(row) for row in rows]


def purge_personalization_events(
    user_id: str | None = None, before: datetime | str | None = None
) -> int:
    """Delete one user's events or events whose TTL ended by a boundary."""
    conditions: list[str] = []
    params: list[Any] = []
    if user_id is not None:
        conditions.append("user_id = %s::uuid")
        params.append(_owner_id(user_id))
    if before is not None:
        conditions.append("expires_at <= %s")
        params.append(_timestamp(before, datetime.now(timezone.utc)))
    if not conditions:
        conditions.append("expires_at <= NOW()")
    with db._conn() as conn:
        result = db._execute(
            conn,
            "DELETE FROM user_personalization_events WHERE " + " AND ".join(conditions),
            params,
        )
        return max(0, int(result.rowcount or 0))


def legacy_cutover_deadline() -> datetime | None:
    """Return Task 10's rollout boundary; absent configuration keeps reads off."""
    raw = getattr(settings, "PERSONALIZATION_LEGACY_READ_DEADLINE", None)
    if raw is None:
        raw = os.environ.get("PERSONALIZATION_LEGACY_READ_DEADLINE")
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return None
    try:
        return _timestamp(raw, datetime.now(timezone.utc))
    except PersonalizationEventError:
        return None


def _legacy_timestamp(row: Mapping[str, Any]) -> datetime | None:
    raw = row.get("occurred_at", row.get("ts"))
    try:
        return _timestamp(raw, datetime.now(timezone.utc)) if raw is not None else None
    except PersonalizationEventError:
        return None


def _legacy_projection(row: Mapping[str, Any]) -> dict[str, Any] | None:
    if set(row) - _LEGACY_EVENT_FIELDS:
        return None
    occurred_at = _legacy_timestamp(row)
    if occurred_at is None:
        return None
    try:
        event_type = _controlled_key(
            row.get("event_type"), "event_type", PERSONALIZATION_EVENT_TYPES
        )
        context = _controlled_key(
            row.get("context") or "unknown", "context", PERSONALIZATION_CONTEXTS
        )
    except PersonalizationEventError:
        return None
    try:
        entity_id = _optional_identifier(row.get("entity_id"), "entity_id")
    except PersonalizationEventError:
        entity_id = None
    try:
        entity_type = _optional_controlled_key(
            row.get("entity_type"), "entity_type", PERSONALIZATION_ENTITY_TYPES
        )
    except PersonalizationEventError:
        entity_type = None
    try:
        area_id = _optional_identifier(
            row.get("area_id", row.get("area")), "area_id"
        )
    except PersonalizationEventError:
        area_id = None
    try:
        interest_keys = _interest_keys(row.get("interest_keys"))
    except PersonalizationEventError:
        interest_keys = []
    return {
        "event_type": event_type,
        "context": context,
        "entity_id": entity_id,
        "entity_type": entity_type,
        "area_id": area_id,
        "interest_keys": interest_keys,
        "occurred_at": occurred_at,
    }


def _read_legacy_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def read_legacy_events_if_allowed(
    user_id: str, cutoff: datetime | str | None, now: datetime | str
) -> list[dict]:
    """Project legacy JSONL into the safe shape only during configured cutover."""
    owner = _owner_id(user_id)
    current = _timestamp(now, datetime.now(timezone.utc))
    deadline = legacy_cutover_deadline()
    if deadline is None or current > deadline:
        return []
    reset_at = _timestamp(cutoff, current) if cutoff is not None else None
    projected: list[dict] = []
    for row in reversed(_read_legacy_rows(LEGACY_EVENTS_PATH)):
        if str(row.get("user_id")) != owner:
            continue
        event = _legacy_projection(row)
        if event is None or (reset_at is not None and event["occurred_at"] <= reset_at):
            continue
        projected.append(event)
        if len(projected) == MAX_EVENT_LIMIT:
            break
    return projected


def _legacy_row_matches(
    row: Mapping[str, Any], owner: str | None, boundary: datetime | None
) -> bool:
    if _legacy_projection(row) is None:
        return False
    try:
        row_owner = _owner_id(row.get("user_id"))
    except PersonalizationEventError:
        return False
    if owner is not None and row_owner != owner:
        return False
    if boundary is None:
        return owner is not None
    occurred_at = _legacy_timestamp(row)
    return occurred_at is not None and occurred_at <= boundary


def purge_legacy_events(
    user_id: str | None = None, before: datetime | str | None = None
) -> int:
    """Atomically remove matching legacy rows under a cross-process lock."""
    owner = _owner_id(user_id) if user_id is not None else None
    boundary = (
        _timestamp(before, datetime.now(timezone.utc)) if before is not None else None
    )
    if owner is None and boundary is None:
        return 0
    path = LEGACY_EVENTS_PATH
    lock_path = LEGACY_EVENTS_LOCK_PATH
    with publication_lock(lock_path):
        if not path.exists():
            return 0
        kept_lines: list[str] = []
        removed = 0
        for line in path.read_text(encoding="utf-8").splitlines(keepends=True):
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                kept_lines.append(line)
                continue
            if not isinstance(row, dict) or not _legacy_row_matches(
                row, owner, boundary
            ):
                kept_lines.append(line)
            else:
                removed += 1
        if removed == 0:
            return 0
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                newline="\n",
                dir=path.parent,
                prefix=f".{path.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temp_path = Path(handle.name)
                handle.writelines(kept_lines)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, path)
            temp_path = None
            fsync_directory(path.parent)
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
        return removed


def _purge_user_personalization_in_connection(conn, owner: str) -> None:
    db._execute(
        conn,
        "DELETE FROM user_personalization_events WHERE user_id = %s::uuid",
        (owner,),
    )
    db._execute(
        conn,
        "DELETE FROM user_preference_consents WHERE user_id = %s::uuid",
        (owner,),
    )
    db._execute(
        conn,
        "DELETE FROM user_preferences WHERE user_id = %s::uuid",
        (owner,),
    )


def purge_user_personalization(user_id: str, *, conn=None) -> None:
    """Delete preference, consent, and event rows for final account purge."""
    owner = _owner_id(user_id)
    if conn is not None:
        _purge_user_personalization_in_connection(conn, owner)
        return
    with db._conn() as conn:
        _purge_user_personalization_in_connection(conn, owner)


def record_recommendation_reset(user_id: str) -> PreferenceSnapshot:
    """Advance the single effective reset cutoff atomically."""
    owner = _owner_id(user_id)
    reset_at = datetime.now(timezone.utc)
    with db._conn() as conn:
        row = db._fetchone(
            conn,
            """
            INSERT INTO user_preferences
                (user_id, recommendation_reset_at, revision, updated_at)
            VALUES (%s::uuid, %s, 1, NOW())
            ON CONFLICT (user_id) DO UPDATE SET
                recommendation_reset_at = GREATEST(
                    user_preferences.recommendation_reset_at,
                    EXCLUDED.recommendation_reset_at
                ),
                revision = user_preferences.revision + 1,
                updated_at = NOW()
            RETURNING region_id, region_label, region_scope, location_source,
                      location_accuracy, location_consent_state, location_enabled,
                      personalization_enabled, explicit_interests,
                      recommendation_reset_at, consent_version, revision
            """,
            (owner, reset_at),
        )
    return _row_snapshot(row)
