"""Preference normalization and persistence boundary for identity personalization."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any, TypedDict
from uuid import uuid4

from database import db
from location_resolver import LocationResolution, contains_raw_location_value


REGION_SCOPES = frozenset({"ward", "district", "province", "all", "unknown"})
LOCATION_SOURCES = frozenset({"manual", "gps", "ip", "default"})
LOCATION_ACCURACIES = frozenset({"ward", "district", "province", "unknown"})
LOCATION_CONSENT_STATES = frozenset({"unknown", "granted", "denied", "off", "expired"})
CONSENT_TYPES = frozenset({"location", "personalization"})
CONSENT_EVENT_STATES = frozenset({"granted", "denied", "off", "expired"})

MAX_INTERESTS = 12
MAX_INTEREST_LENGTH = 64
MAX_REGION_ID_LENGTH = 128
MAX_REGION_LABEL_LENGTH = 160
MAX_CONSENT_VERSION_LENGTH = 64
MAX_RECOMMENDATION_RESET_AT_LENGTH = 64
MAX_PREFERENCE_REVISION = 9_007_199_254_740_991
LOCATION_PROVENANCE_RESOLVER_V2 = "resolver-v2"

_SOURCE_PRIORITY = {"default": 0, "ip": 1, "gps": 2, "manual": 3}
_REGION_FIELDS = frozenset(
    {"region_id", "region_label", "region_scope", "location_source", "location_accuracy"}
)
_CANONICAL_MANUAL_REGIONS = {
    "province-vl": {
        "region_id": "province-vl",
        "region_label": "Vĩnh Long",
        "region_scope": "province",
        "location_source": "manual",
        "location_accuracy": "province",
    },
    "province-bt": {
        "region_id": "province-bt",
        "region_label": "Bến Tre",
        "region_scope": "province",
        "location_source": "manual",
        "location_accuracy": "province",
    },
    "province-tv": {
        "region_id": "province-tv",
        "region_label": "Trà Vinh",
        "region_scope": "province",
        "location_source": "manual",
        "location_accuracy": "province",
    },
    None: {
        "region_id": None,
        "region_label": None,
        "region_scope": "all",
        "location_source": "manual",
        "location_accuracy": "unknown",
    },
}
_PUBLIC_SNAPSHOT_FIELDS = (
    "region_id",
    "region_label",
    "region_scope",
    "location_source",
    "location_accuracy",
    "location_consent_state",
    "location_enabled",
    "personalization_enabled",
    "explicit_interests",
    "recommendation_reset_at",
    "consent_version",
    "location_reconfirm_required",
    "revision",
)
_PERSISTED_FIELDS = (*_PUBLIC_SNAPSHOT_FIELDS, "location_provenance_version")
_PATCH_FIELDS = frozenset(
    field
    for field in _PUBLIC_SNAPSHOT_FIELDS
    if field not in {"location_reconfirm_required"}
)


class PreferenceSnapshot(TypedDict):
    region_id: str | None
    region_label: str | None
    region_scope: str
    location_source: str
    location_accuracy: str
    location_consent_state: str
    location_enabled: bool
    personalization_enabled: bool
    explicit_interests: list[str]
    recommendation_reset_at: datetime | str | None
    consent_version: str | None
    location_reconfirm_required: bool
    revision: int


class PersistedPreferenceSnapshot(PreferenceSnapshot):
    location_provenance_version: str | None


class PreferencePatch(TypedDict, total=False):
    region_id: str | None
    region_label: str | None
    region_scope: str
    location_source: str
    location_accuracy: str
    location_consent_state: str
    location_enabled: bool
    personalization_enabled: bool
    explicit_interests: list[str]
    recommendation_reset_at: datetime | str | None
    consent_version: str | None
    revision: int


class PreferenceConsentEntry(TypedDict):
    consent_type: str
    state: str
    version: str
    created_at: datetime | str


class PreferenceError(ValueError):
    """Base error for invalid or conflicting preference mutations."""


class PreferenceValidationError(PreferenceError):
    """Raised when preference input is outside the bounded contract."""


class PreferenceRevisionConflict(PreferenceError):
    """Raised when optimistic preference revision does not match current state."""

    def __init__(self, expected_revision: int, current_revision: int):
        self.expected_revision = expected_revision
        self.current_revision = current_revision
        super().__init__(
            f"Preference revision conflict: expected {expected_revision}, current {current_revision}"
        )


def _default_persisted_snapshot() -> PersistedPreferenceSnapshot:
    return {
        "region_id": None,
        "region_label": None,
        "region_scope": "unknown",
        "location_source": "default",
        "location_accuracy": "unknown",
        "location_consent_state": "unknown",
        "location_enabled": False,
        "personalization_enabled": False,
        "explicit_interests": [],
        "recommendation_reset_at": None,
        "consent_version": None,
        "location_reconfirm_required": False,
        "revision": 0,
        "location_provenance_version": None,
    }


def _default_snapshot() -> PreferenceSnapshot:
    return _public_snapshot(_default_persisted_snapshot())


def _public_snapshot(snapshot: Mapping[str, Any]) -> PreferenceSnapshot:
    return {field: snapshot[field] for field in _PUBLIC_SNAPSHOT_FIELDS}


def _bounded_optional_text(value: Any, field: str, maximum: int) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise PreferenceValidationError(f"{field} must be text or null")
    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > maximum:
        raise PreferenceValidationError(f"{field} exceeds {maximum} characters")
    return normalized


def _enum_value(value: Any, field: str, allowed: frozenset[str]) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise PreferenceValidationError(f"Unknown {field}: {value!r}")
    return value


def _boolean_value(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise PreferenceValidationError(f"{field} must be a boolean")
    return value


def _revision_value(value: Any) -> int:
    if isinstance(value, bool):
        raise PreferenceValidationError("revision must be a non-negative integer")
    try:
        revision = int(value)
    except (TypeError, ValueError) as exc:
        raise PreferenceValidationError("revision must be a non-negative integer") from exc
    if isinstance(value, float) and not value.is_integer():
        raise PreferenceValidationError("revision must be a non-negative integer")
    if isinstance(value, str) and str(revision) != value.strip():
        raise PreferenceValidationError("revision must be a non-negative integer")
    if revision < 0 or revision > MAX_PREFERENCE_REVISION:
        raise PreferenceValidationError("revision must be a non-negative integer")
    return revision


def _normalize_interests(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        raise PreferenceValidationError("explicit_interests must be an array")
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in value:
        if not isinstance(raw, str):
            raise PreferenceValidationError("explicit_interests must contain only text labels")
        label = raw.strip()
        if not label or len(label) > MAX_INTEREST_LENGTH or label in seen:
            continue
        seen.add(label)
        normalized.append(label)
        if len(normalized) == MAX_INTERESTS:
            break
    return normalized


def parse_utc_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        if len(value) > MAX_RECOMMENDATION_RESET_AT_LENGTH:
            raise PreferenceValidationError("Invalid UTC timestamp")
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError as exc:
            raise PreferenceValidationError("Invalid UTC timestamp") from exc
    else:
        raise PreferenceValidationError("Invalid UTC timestamp")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def normalize_preference_patch(patch: Mapping[str, Any]) -> PreferencePatch:
    if not isinstance(patch, Mapping):
        raise PreferenceValidationError("Preference patch must be an object")
    unknown = set(patch) - _PATCH_FIELDS
    if unknown:
        raise PreferenceValidationError(f"Unknown preference fields: {', '.join(sorted(unknown))}")

    normalized: PreferencePatch = {}
    for field, value in patch.items():
        if field == "region_id":
            normalized[field] = _bounded_optional_text(value, field, MAX_REGION_ID_LENGTH)
            if contains_raw_location_value(normalized[field]):
                raise PreferenceValidationError("Invalid region value")
        elif field == "region_label":
            normalized[field] = _bounded_optional_text(value, field, MAX_REGION_LABEL_LENGTH)
            if contains_raw_location_value(normalized[field]):
                raise PreferenceValidationError("Invalid region value")
        elif field == "region_scope":
            normalized[field] = _enum_value(value, field, REGION_SCOPES)
        elif field == "location_source":
            normalized[field] = _enum_value(value, field, LOCATION_SOURCES)
        elif field == "location_accuracy":
            normalized[field] = _enum_value(value, field, LOCATION_ACCURACIES)
        elif field == "location_consent_state":
            normalized[field] = _enum_value(value, field, LOCATION_CONSENT_STATES)
        elif field in {"location_enabled", "personalization_enabled"}:
            normalized[field] = _boolean_value(value, field)
        elif field == "explicit_interests":
            normalized[field] = _normalize_interests(value)
        elif field == "recommendation_reset_at":
            normalized[field] = None if value is None else parse_utc_timestamp(value)
        elif field == "consent_version":
            normalized[field] = _bounded_optional_text(value, field, MAX_CONSENT_VERSION_LENGTH)
        elif field == "revision":
            normalized[field] = _revision_value(value)
    return normalized


def _authorize_region_patch(
    patch: Mapping[str, Any],
    *,
    confirmed_location: LocationResolution | None,
) -> dict[str, Any]:
    authorized = dict(patch)
    client_region_fields = _REGION_FIELDS.intersection(authorized)
    if confirmed_location is not None:
        if client_region_fields:
            raise PreferenceValidationError(
                "Resolver confirmation cannot include client region fields"
            )
        authorized.update(
            {
                "region_id": confirmed_location.region_id,
                "region_label": confirmed_location.region_label,
                "region_scope": confirmed_location.region_scope,
                "location_source": confirmed_location.location_source,
                "location_accuracy": confirmed_location.location_accuracy,
            }
        )
        return authorized
    if not client_region_fields:
        return authorized

    source = authorized.get("location_source")
    if source == "manual":
        canonical = _CANONICAL_MANUAL_REGIONS.get(authorized.get("region_id"))
        if canonical is None or any(
            authorized.get(field) != value for field, value in canonical.items()
        ):
            raise PreferenceValidationError("Invalid manual region selection")
        return authorized
    if source == "default":
        allowed = {
            "region_id": None,
            "region_label": None,
            "region_scope": "unknown",
            "location_source": "default",
            "location_accuracy": "unknown",
        }
        if any(
            field != "location_source" and authorized.get(field) != allowed[field]
            for field in client_region_fields
        ):
            raise PreferenceValidationError("Invalid default region selection")
        return authorized
    raise PreferenceValidationError("Resolver region confirmation is required")


def _snapshot_from_mapping(value: Mapping[str, Any]) -> PersistedPreferenceSnapshot:
    snapshot = _default_persisted_snapshot()
    for field in _PERSISTED_FIELDS:
        if field in value:
            snapshot[field] = value[field]
    snapshot["revision"] = _revision_value(snapshot["revision"])
    snapshot["location_enabled"] = bool(snapshot["location_enabled"])
    snapshot["personalization_enabled"] = bool(snapshot["personalization_enabled"])
    snapshot["location_reconfirm_required"] = bool(
        snapshot["location_reconfirm_required"]
    )
    interests = snapshot["explicit_interests"]
    if isinstance(interests, str):
        try:
            interests = json.loads(interests)
        except json.JSONDecodeError:
            interests = []
    snapshot["explicit_interests"] = _normalize_interests(interests)
    reset_at = snapshot["recommendation_reset_at"]
    if reset_at is not None:
        snapshot["recommendation_reset_at"] = parse_utc_timestamp(reset_at)
    return snapshot


def _manual_region_tuple(snapshot: Mapping[str, Any]) -> bool:
    region_id = snapshot.get("region_id")
    canonical = _CANONICAL_MANUAL_REGIONS.get(region_id)
    return (
        snapshot.get("location_source") == "manual"
        and snapshot.get("location_provenance_version") is None
        and canonical is not None
        and all(snapshot.get(field) == value for field, value in canonical.items())
    )


def _default_region_tuple(snapshot: Mapping[str, Any]) -> bool:
    return (
        snapshot.get("location_source") == "default"
        and snapshot.get("region_id") is None
        and snapshot.get("region_label") is None
        and snapshot.get("region_scope") == "unknown"
        and snapshot.get("location_accuracy") == "unknown"
        and snapshot.get("location_provenance_version") is None
    )


def _quarantine_region_tuple(snapshot: Mapping[str, Any]) -> bool:
    return (
        _default_region_tuple(snapshot)
        and snapshot.get("location_consent_state") == "off"
        and snapshot.get("location_enabled") is False
        and snapshot.get("location_reconfirm_required") is True
    )


def _resolver_region_tuple(snapshot: Mapping[str, Any]) -> bool:
    return (
        snapshot.get("location_source") in {"gps", "ip"}
        and snapshot.get("region_id") is not None
        and snapshot.get("region_scope") in {"ward", "district", "province"}
        and snapshot.get("location_accuracy") in LOCATION_ACCURACIES
        and snapshot.get("location_enabled") is True
        and snapshot.get("location_consent_state") == "granted"
    )


def invalid_region_reason(snapshot: Mapping[str, Any]) -> str | None:
    """Return the bounded remediation reason for a persisted location tuple."""
    if contains_raw_location_value(
        snapshot.get("region_id")
    ) or contains_raw_location_value(snapshot.get("region_label")):
        return "raw_shape"

    source = snapshot.get("location_source")
    if source == "manual":
        if not _manual_region_tuple(snapshot):
            return "manual_tuple"
    elif source in {"gps", "ip"}:
        if not _resolver_region_tuple(snapshot):
            return "resolver_tuple"
        if (
            snapshot.get("location_provenance_version")
            != LOCATION_PROVENANCE_RESOLVER_V2
        ):
            return "provenance"
    elif source == "default":
        if not _default_region_tuple(snapshot):
            return "default_tuple"
    else:
        return "default_tuple"

    if snapshot.get("location_reconfirm_required") and not _quarantine_region_tuple(
        snapshot
    ):
        return "state_mismatch"
    return None


def quarantine_location_snapshot(
    snapshot: Mapping[str, Any],
) -> PersistedPreferenceSnapshot:
    """Drop all location fields while preserving non-location preferences."""
    current = _snapshot_from_mapping(snapshot)
    current.update(
        {
            "region_id": None,
            "region_label": None,
            "region_scope": "unknown",
            "location_source": "default",
            "location_accuracy": "unknown",
            "location_consent_state": "off",
            "location_enabled": False,
            "location_reconfirm_required": True,
            "location_provenance_version": None,
        }
    )
    return current


def merge_preference_patch(
    current: Mapping[str, Any], patch: Mapping[str, Any], expected_revision: int
) -> PersistedPreferenceSnapshot:
    expected = _revision_value(expected_revision)
    current_snapshot = _snapshot_from_mapping(current)
    if current_snapshot["revision"] != expected:
        raise PreferenceRevisionConflict(expected, current_snapshot["revision"])

    normalized = normalize_preference_patch(patch)
    normalized.pop("revision", None)
    patch_source = normalized.get("location_source", current_snapshot["location_source"])
    current_source = current_snapshot["location_source"]
    region_change = bool(_REGION_FIELDS.intersection(normalized))
    lower_quality = _SOURCE_PRIORITY[patch_source] < _SOURCE_PRIORITY[current_source]
    location_enabled = normalized.get(
        "location_enabled", current_snapshot["location_enabled"]
    )
    resolver_disabled = not location_enabled and patch_source in {"gps", "ip"}
    disabling_existing_resolver = (
        normalized.get("location_enabled") is False
        and current_source in {"gps", "ip"}
        and not (
            patch_source == "manual"
            and "region_id" in normalized
            and normalized["region_id"] is not None
        )
    )
    if disabling_existing_resolver:
        normalized.update(
            {
                "region_id": None,
                "region_label": None,
                "region_scope": "unknown",
                "location_source": "default",
                "location_accuracy": "unknown",
            }
        )
    elif region_change and (resolver_disabled or lower_quality):
        for field in _REGION_FIELDS:
            normalized.pop(field, None)

    merged = dict(current_snapshot)
    merged.update(normalized)
    if current_snapshot["revision"] == MAX_PREFERENCE_REVISION:
        raise PreferenceValidationError("Preference revision limit reached")
    merged["revision"] = current_snapshot["revision"] + 1
    return merged


def _apply_internal_location_metadata(
    merged: PersistedPreferenceSnapshot,
    *,
    authorized_patch: Mapping[str, Any],
    confirmed_location: LocationResolution | None,
) -> None:
    """Finalize remediation metadata after the public patch has been merged."""
    if merged["location_source"] == "manual":
        merged["location_provenance_version"] = None
        if authorized_patch.get("location_source") == "manual":
            merged["location_reconfirm_required"] = False
        return
    if merged["location_source"] in {"gps", "ip"} and confirmed_location is not None:
        merged["location_provenance_version"] = LOCATION_PROVENANCE_RESOLVER_V2
        merged["location_reconfirm_required"] = False
        return
    if merged["location_source"] == "default":
        merged["location_provenance_version"] = None


def recommendation_cutoff(snapshot: Mapping[str, Any]) -> datetime | None:
    raw = snapshot.get("recommendation_reset_at")
    return parse_utc_timestamp(raw) if raw else None


def _user_id(value: Any) -> str:
    normalized = _bounded_optional_text(value, "user_id", 128)
    if normalized is None:
        raise PreferenceValidationError("user_id is required")
    return normalized


def _user_param() -> str:
    return f"{db._ph}::uuid" if db._use_pg else db._ph


def _preference_columns() -> str:
    return ", ".join(_PERSISTED_FIELDS)


def _select_preferences(conn, user_id: str, *, for_update: bool = False):
    lock = " FOR UPDATE" if for_update and db._use_pg else ""
    return db._fetchone(
        conn,
        f"SELECT {_preference_columns()} FROM user_preferences "
        f"WHERE user_id = {_user_param()}{lock}",
        (user_id,),
    )


def _row_snapshot(row) -> PersistedPreferenceSnapshot:
    return _snapshot_from_mapping(db._row_to_dict(row))


def load_preferences(user_id: str) -> PreferenceSnapshot:
    owner = _user_id(user_id)
    with db._conn(commit_on_success=False) as conn:
        row = _select_preferences(conn, owner)
    return (
        _public_snapshot(_row_snapshot(row))
        if row is not None
        else _default_snapshot()
    )


def _write_values(snapshot: PersistedPreferenceSnapshot) -> tuple[list[Any], str]:
    values = []
    for field in _PERSISTED_FIELDS:
        value = snapshot[field]
        if field == "explicit_interests":
            value = json.dumps(value, ensure_ascii=True)
        elif field == "recommendation_reset_at" and isinstance(value, datetime):
            value = value.isoformat()
        values.append(value)
    placeholders = [db._ph] * len(values)
    if db._use_pg:
        placeholders[_PERSISTED_FIELDS.index("explicit_interests")] += "::jsonb"
    return values, ", ".join(placeholders)


def _consent_policy_version() -> str:
    # Lazy import keeps the persistence module independent during auth startup.
    from auth import CONSENT_VERSION

    version = _bounded_optional_text(
        CONSENT_VERSION, "consent version", MAX_CONSENT_VERSION_LENGTH
    )
    if version is None:
        raise PreferenceValidationError("consent version is required")
    return version


def _preference_consent_changes(
    current: PreferenceSnapshot, snapshot: PreferenceSnapshot
) -> list[tuple[str, str]]:
    changes: list[tuple[str, str]] = []
    if current["location_consent_state"] != snapshot["location_consent_state"]:
        changes.append(("location", snapshot["location_consent_state"]))
    if current["personalization_enabled"] != snapshot["personalization_enabled"]:
        changes.append(
            (
                "personalization",
                "granted" if snapshot["personalization_enabled"] else "off",
            )
        )
    return changes


def _patch_preferences_in_connection(
    conn,
    owner: str,
    patch: Mapping[str, Any],
    expected: int,
    *,
    consent_version_fallback: str | None = None,
    confirmed_location: LocationResolution | None = None,
) -> tuple[PersistedPreferenceSnapshot, PersistedPreferenceSnapshot]:
    if not patch:
        raise PreferenceValidationError("Preference patch must not be empty")

    authorized_patch = _authorize_region_patch(
        patch, confirmed_location=confirmed_location
    )
    row = _select_preferences(conn, owner, for_update=True)
    current = _row_snapshot(row) if row is not None else _default_persisted_snapshot()
    merged = merge_preference_patch(current, authorized_patch, expected)
    _apply_internal_location_metadata(
        merged,
        authorized_patch=authorized_patch,
        confirmed_location=confirmed_location,
    )
    if (
        consent_version_fallback is not None
        and _preference_consent_changes(current, merged)
        and merged["consent_version"] is None
    ):
        merged["consent_version"] = consent_version_fallback
    values, value_placeholders = _write_values(merged)
    if row is None:
        inserted = db._fetchone(
            conn,
            f"INSERT INTO user_preferences (user_id, {_preference_columns()}) "
            f"VALUES ({_user_param()}, {value_placeholders}) "
            f"ON CONFLICT (user_id) DO NOTHING RETURNING {_preference_columns()}",
            [owner, *values],
        )
        if inserted is None:
            latest = _select_preferences(conn, owner)
            current_revision = _row_snapshot(latest)["revision"] if latest else 0
            raise PreferenceRevisionConflict(expected, current_revision)
        return current, _row_snapshot(inserted)

    assignments = []
    for field in _PERSISTED_FIELDS:
        placeholder = db._ph
        if field == "explicit_interests" and db._use_pg:
            placeholder += "::jsonb"
        assignments.append(f"{field} = {placeholder}")
    assignments.append("updated_at = NOW()" if db._use_pg else "updated_at = CURRENT_TIMESTAMP")
    updated = db._fetchone(
        conn,
        f"UPDATE user_preferences SET {', '.join(assignments)} "
        f"WHERE user_id = {_user_param()} AND revision = {db._ph} "
        f"RETURNING {_preference_columns()}",
        [*values, owner, expected],
    )
    if updated is None:
        latest = _select_preferences(conn, owner)
        current_revision = _row_snapshot(latest)["revision"] if latest else 0
        raise PreferenceRevisionConflict(expected, current_revision)
    return current, _row_snapshot(updated)


def patch_preferences(
    user_id: str, patch: Mapping[str, Any], expected_revision: int
) -> PreferenceSnapshot:
    owner = _user_id(user_id)
    expected = _revision_value(expected_revision)
    with db._conn() as conn:
        _, snapshot = _patch_preferences_in_connection(conn, owner, patch, expected)
    return _public_snapshot(snapshot)


def _insert_preference_consent(
    conn, owner: str, consent_type: str, state: str, version: str
) -> None:
    normalized_type = _enum_value(consent_type, "consent_type", CONSENT_TYPES)
    normalized_state = _enum_value(state, "consent state", CONSENT_EVENT_STATES)
    normalized_version = _bounded_optional_text(
        version, "consent version", MAX_CONSENT_VERSION_LENGTH
    )
    if normalized_version is None:
        raise PreferenceValidationError("consent version is required")
    db._execute(
        conn,
        "INSERT INTO user_preference_consents "
        f"(id, user_id, consent_type, state, version) VALUES ({db._ph}, {_user_param()}, "
        f"{db._ph}, {db._ph}, {db._ph})",
        (str(uuid4()), owner, normalized_type, normalized_state, normalized_version),
    )


def patch_preferences_with_consents(
    user_id: str,
    patch: Mapping[str, Any],
    expected_revision: int,
    *,
    confirmed_location: LocationResolution | None = None,
) -> PreferenceSnapshot:
    owner = _user_id(user_id)
    expected = _revision_value(expected_revision)
    with db._conn() as conn:
        current, snapshot = _patch_preferences_in_connection(
            conn,
            owner,
            patch,
            expected,
            consent_version_fallback=_consent_policy_version(),
            confirmed_location=confirmed_location,
        )
        for consent_type, state in _preference_consent_changes(current, snapshot):
            _insert_preference_consent(
                conn,
                owner,
                consent_type,
                state,
                snapshot["consent_version"],
            )
    return _public_snapshot(snapshot)


def record_preference_consent(
    user_id: str, consent_type: str, state: str, version: str
) -> None:
    owner = _user_id(user_id)
    with db._conn() as conn:
        _insert_preference_consent(
            conn, owner, consent_type, state, version
        )


def load_preference_consents(user_id: str) -> list[PreferenceConsentEntry]:
    owner = _user_id(user_id)
    with db._conn(commit_on_success=False) as conn:
        rows = db._fetchall(
            conn,
            "SELECT consent_type, state, version, created_at "
            "FROM user_preference_consents "
            f"WHERE user_id = {_user_param()} "
            "ORDER BY created_at DESC, id DESC LIMIT 100",
            (owner,),
        )
    return [db._row_to_dict(row) for row in rows]
