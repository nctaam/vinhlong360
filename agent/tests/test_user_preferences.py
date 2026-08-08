import base64
import json
import sqlite3
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import auth
import auth_middleware
import location_resolver
import personalization_events
import public_api
import user_preferences
from auth_middleware import generate_csrf_token, generate_user_bound_token
from database import Database, db as live_db
from user_preferences import (
    PreferenceRevisionConflict,
    PreferenceValidationError,
    load_preferences,
    load_preference_consents,
    merge_preference_patch,
    normalize_preference_patch,
    patch_preferences,
    patch_preferences_with_consents,
    recommendation_cutoff,
    record_preference_consent,
)


def test_manual_all_region_wins_over_valid_gps_confirmation():
    merged = merge_preference_patch(
        {
            "region_id": None,
            "region_label": None,
            "region_scope": "all",
            "location_source": "manual",
            "location_accuracy": "unknown",
            "revision": 4,
        },
        {
            "region_id": "province-vl",
            "region_label": "Vĩnh Long",
            "region_scope": "province",
            "location_source": "gps",
            "location_accuracy": "province",
            "location_enabled": True,
        },
        expected_revision=4,
    )
    assert merged["region_id"] is None
    assert merged["region_scope"] == "all"
    assert merged["location_source"] == "manual"


_MANUAL_ALL_REGION = {
    "region_id": None,
    "region_label": None,
    "region_scope": "all",
    "location_source": "manual",
    "location_accuracy": "unknown",
}
_VALID_RESOLVER_REGION = {
    "region_id": "province-vl",
    "region_label": "Vĩnh Long",
    "region_scope": "province",
    "location_source": "gps",
    "location_accuracy": "province",
    "location_enabled": True,
    "location_consent_state": "granted",
    "location_provenance_version": "resolver-v2",
}


@pytest.mark.parametrize(
    ("snapshot", "reason"),
    [
        (
            {
                "region_id": "203.0.113.9",
                "region_label": "Vĩnh Long",
                "region_scope": "province",
                "location_source": "manual",
                "location_accuracy": "province",
            },
            "raw_shape",
        ),
        (
            {
                "region_id": "district-x",
                "region_label": "Tự khai",
                "region_scope": "district",
                "location_source": "manual",
                "location_accuracy": "district",
            },
            "manual_tuple",
        ),
        (
            {
                "region_id": "province-vl",
                "region_label": "Vĩnh Long",
                "region_scope": "province",
                "location_source": "gps",
                "location_accuracy": "province",
                "location_enabled": True,
                "location_consent_state": "granted",
                "location_provenance_version": None,
            },
            "provenance",
        ),
        ({"location_source": []}, "default_tuple"),
        ({"location_source": {}}, "default_tuple"),
        ({"location_source": None}, "default_tuple"),
        ({**_MANUAL_ALL_REGION, "region_id": []}, "manual_tuple"),
        ({**_MANUAL_ALL_REGION, "region_id": {}}, "manual_tuple"),
        (
            {
                **_MANUAL_ALL_REGION,
                "region_label": "Vĩnh Long",
                "region_scope": "province",
                "location_accuracy": "province",
            },
            "manual_tuple",
        ),
        ({**_VALID_RESOLVER_REGION, "region_scope": []}, "resolver_tuple"),
        ({**_VALID_RESOLVER_REGION, "region_scope": {}}, "resolver_tuple"),
        ({**_VALID_RESOLVER_REGION, "region_scope": None}, "resolver_tuple"),
        ({**_VALID_RESOLVER_REGION, "location_accuracy": []}, "resolver_tuple"),
        ({**_VALID_RESOLVER_REGION, "location_accuracy": {}}, "resolver_tuple"),
        ({**_VALID_RESOLVER_REGION, "location_accuracy": None}, "resolver_tuple"),
        ({**_VALID_RESOLVER_REGION, "region_id": ""}, "resolver_tuple"),
        ({**_VALID_RESOLVER_REGION, "region_id": " province-vl"}, "resolver_tuple"),
        ({**_VALID_RESOLVER_REGION, "region_id": "province vl"}, "resolver_tuple"),
        ({**_VALID_RESOLVER_REGION, "region_id": "x" * 129}, "resolver_tuple"),
        ({**_VALID_RESOLVER_REGION, "region_label": ""}, "resolver_tuple"),
        ({**_VALID_RESOLVER_REGION, "region_label": " Vĩnh Long"}, "resolver_tuple"),
        ({**_VALID_RESOLVER_REGION, "region_label": "x" * 161}, "resolver_tuple"),
    ],
)
def test_invalid_region_reason_is_bounded(snapshot, reason):
    assert user_preferences.invalid_region_reason(
        {**user_preferences._default_persisted_snapshot(), **snapshot}
    ) == reason


def test_quarantine_location_snapshot_drops_location_and_preserves_preferences():
    snapshot = user_preferences.quarantine_location_snapshot(
        {
            **user_preferences._default_persisted_snapshot(),
            "region_id": "203.0.113.9",
            "region_label": "10.25, 105.97",
            "region_scope": "province",
            "location_source": "gps",
            "location_accuracy": "province",
            "location_consent_state": "granted",
            "location_enabled": True,
            "location_provenance_version": "resolver-v1",
            "personalization_enabled": True,
            "explicit_interests": ["food"],
            "consent_version": "privacy-v1",
            "revision": 7,
        }
    )

    assert snapshot == {
        "region_id": None,
        "region_label": None,
        "region_scope": "unknown",
        "location_source": "default",
        "location_accuracy": "unknown",
        "location_consent_state": "off",
        "location_enabled": False,
        "personalization_enabled": True,
        "explicit_interests": ["food"],
        "recommendation_reset_at": None,
        "consent_version": "privacy-v1",
        "location_reconfirm_required": True,
        "revision": 7,
        "location_provenance_version": None,
    }
    assert user_preferences.invalid_region_reason(snapshot) is None
    assert "203.0.113.9" not in repr(snapshot)
    assert "10.25" not in repr(snapshot)
    assert "105.97" not in repr(snapshot)


@pytest.mark.parametrize(
    "field",
    ["location_reconfirm_required", "location_provenance_version"],
)
def test_remediation_fields_are_not_client_patchable(field):
    with pytest.raises(PreferenceValidationError, match="Unknown preference fields"):
        normalize_preference_patch({field: True})


def test_revision_accepts_json_safe_bigint_boundary():
    assert normalize_preference_patch(
        {"revision": 9_007_199_254_740_991}
    )["revision"] == 9_007_199_254_740_991


def test_revision_rejects_value_above_json_safe_bigint_boundary():
    with pytest.raises(PreferenceValidationError):
        normalize_preference_patch({"revision": 9_007_199_254_740_992})


def _insert_unsafe_preference(database, user_id="user-1", revision=7):
    with database._conn() as conn:
        conn.execute(
            "INSERT INTO user_preferences "
            "(user_id, region_id, region_label, region_scope, location_source, "
            "location_accuracy, location_consent_state, location_enabled, "
            "personalization_enabled, explicit_interests, consent_version, revision) "
            "VALUES (?, ?, ?, 'province', 'manual', 'province', 'granted', 1, 1, ?, 'privacy-v1', ?)",
            (user_id, "203.0.113.9", "10.25,105.97", '["food"]', revision),
        )


def _insert_noncanonical_resolver_preference(database, user_id="user-1", revision=7):
    with database._conn() as conn:
        conn.execute(
            "INSERT INTO user_preferences "
            "(user_id, region_id, region_label, region_scope, location_source, "
            "location_accuracy, location_consent_state, location_enabled, "
            "personalization_enabled, explicit_interests, consent_version, "
            "location_provenance_version, revision) "
            "VALUES (?, ?, ?, 'province', 'gps', 'province', 'granted', 1, 1, ?, "
            "'privacy-v1', 'resolver-v2', ?)",
            (user_id, "x" * 129, "Vĩnh Long", '["food"]', revision),
        )


def test_load_preferences_quarantines_unsafe_region_without_losing_non_location_state(
    preference_database,
):
    _insert_unsafe_preference(preference_database)

    snapshot = load_preferences("user-1")

    assert snapshot["region_id"] is None
    assert snapshot["location_source"] == "default"
    assert snapshot["location_consent_state"] == "off"
    assert snapshot["location_reconfirm_required"] is True
    assert snapshot["explicit_interests"] == ["food"]
    assert snapshot["personalization_enabled"] is True
    assert snapshot["consent_version"] == "privacy-v1"
    assert snapshot["revision"] == 8


def test_load_preferences_quarantines_overlong_resolver_region_id(
    preference_database,
):
    _insert_noncanonical_resolver_preference(preference_database)

    snapshot = load_preferences("user-1")

    assert snapshot["region_id"] is None
    assert snapshot["region_label"] is None
    assert snapshot["location_source"] == "default"
    assert snapshot["location_consent_state"] == "off"
    assert snapshot["location_reconfirm_required"] is True
    assert snapshot["explicit_interests"] == ["food"]
    assert snapshot["revision"] == 8


def test_second_load_after_quarantine_is_idempotent(preference_database):
    _insert_unsafe_preference(preference_database)

    assert load_preferences("user-1")["revision"] == 8
    assert load_preferences("user-1")["revision"] == 8


def test_unrelated_patch_sanitizes_once_without_synthetic_location_consent(
    preference_database,
):
    _insert_unsafe_preference(preference_database)

    snapshot = patch_preferences_with_consents(
        "user-1",
        {"explicit_interests": ["culture"]},
        expected_revision=7,
    )

    assert snapshot["revision"] == 8
    assert snapshot["region_id"] is None
    assert snapshot["location_reconfirm_required"] is True
    assert snapshot["explicit_interests"] == ["culture"]
    assert load_preference_consents("user-1") == []


def test_manual_patch_completes_reconfirm_in_the_same_write(preference_database):
    _insert_unsafe_preference(preference_database)

    snapshot = patch_preferences(
        "user-1",
        {
            "region_id": None,
            "region_label": None,
            "region_scope": "all",
            "location_source": "manual",
            "location_accuracy": "unknown",
        },
        expected_revision=7,
    )

    assert snapshot["revision"] == 8
    assert snapshot["location_source"] == "manual"
    assert snapshot["region_scope"] == "all"
    assert snapshot["location_reconfirm_required"] is False


def test_recommendation_reset_uses_sanitized_preference_boundary(
    preference_database, monkeypatch
):
    _insert_unsafe_preference(preference_database)
    monkeypatch.setattr(personalization_events, "db", preference_database)

    snapshot = personalization_events.record_recommendation_reset("user-1")

    assert snapshot["region_id"] is None
    assert snapshot["location_reconfirm_required"] is True
    assert snapshot["explicit_interests"] == ["food"]
    assert snapshot["recommendation_reset_at"] is not None
    assert "location_provenance_version" not in snapshot


def test_recommendation_reset_rejects_json_unsafe_revision_ceiling(
    preference_database, monkeypatch
):
    with preference_database._conn() as conn:
        conn.execute(
            "INSERT INTO user_preferences (user_id, revision) VALUES (?, ?)",
            ("user-1", 9_007_199_254_740_991),
        )
    monkeypatch.setattr(personalization_events, "db", preference_database)

    with pytest.raises(PreferenceValidationError, match="revision limit"):
        personalization_events.record_recommendation_reset("user-1")

    with preference_database._conn(commit_on_success=False) as conn:
        row = conn.execute(
            "SELECT recommendation_reset_at, revision FROM user_preferences "
            "WHERE user_id = ?",
            ("user-1",),
        ).fetchone()
    assert tuple(row) == (None, 9_007_199_254_740_991)


def test_concurrent_first_recommendation_resets_are_atomic(
    preference_database, monkeypatch
):
    original_loader_select = user_preferences._select_preferences
    original_reset_select = personalization_events._select_preferences
    loader_barrier = threading.Barrier(2)
    reset_barrier = threading.Barrier(2)

    def synchronized_loader_select(conn, owner, *, for_update=False):
        row = original_loader_select(conn, owner, for_update=for_update)
        if for_update and row is None:
            loader_barrier.wait(timeout=5)
        return row

    def synchronized_reset_select(conn, owner, *, for_update=False):
        row = original_reset_select(conn, owner, for_update=for_update)
        if for_update and row is None:
            reset_barrier.wait(timeout=5)
        return row

    monkeypatch.setattr(
        user_preferences, "_select_preferences", synchronized_loader_select
    )
    monkeypatch.setattr(
        personalization_events, "_select_preferences", synchronized_reset_select
    )
    monkeypatch.setattr(personalization_events, "db", preference_database)
    results = []

    def reset_in_thread(index):
        try:
            snapshot = personalization_events.record_recommendation_reset("user-1")
            results.append((index, "ok", snapshot["revision"]))
        except Exception as exc:  # pragma: no cover - asserted below
            results.append((index, type(exc).__name__, str(exc)))

    threads = [
        threading.Thread(target=reset_in_thread, args=(index,))
        for index in (1, 2)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert all(not thread.is_alive() for thread in threads)
    assert sorted((status, revision) for _, status, revision in results) == [
        ("ok", 1),
        ("ok", 2),
    ]
    assert load_preferences("user-1")["revision"] == 2

pg_only = pytest.mark.skipif(
    not live_db._use_pg, reason="PostgreSQL preference contract requires DATABASE_URL."
)


def test_manual_region_wins_over_lower_quality_sources():
    merged = merge_preference_patch(
        current={"region_id": "province-vl", "location_source": "manual", "revision": 2},
        patch={"region_id": "province-bt", "location_source": "ip"},
        expected_revision=2,
    )

    assert merged["region_id"] == "province-vl"
    assert merged["location_source"] == "manual"


@pytest.mark.parametrize(
    ("current_source", "patch_source", "expected_region"),
    [
        ("default", "ip", "province-bt"),
        ("ip", "gps", "province-bt"),
        ("gps", "manual", "province-bt"),
        ("gps", "ip", "province-vl"),
    ],
)
def test_region_source_precedence_is_manual_gps_ip_default(
    current_source, patch_source, expected_region
):
    merged = merge_preference_patch(
        current={
            "region_id": "province-vl",
            "location_source": current_source,
            "location_enabled": True,
            "revision": 0,
        },
        patch={"region_id": "province-bt", "location_source": patch_source},
        expected_revision=0,
    )

    assert merged["region_id"] == expected_region


def test_explicit_interests_are_unique_and_bounded():
    patch = normalize_preference_patch(
        {"explicit_interests": ["food", "food", "x" * 200]}
    )

    assert patch["explicit_interests"] == ["food"]


def test_explicit_interests_keep_at_most_twelve_non_blank_labels():
    interests = ["  "] + [f"interest-{index}" for index in range(14)]

    patch = normalize_preference_patch({"explicit_interests": interests})

    assert patch["explicit_interests"] == [
        f"interest-{index}" for index in range(12)
    ]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("region_scope", "city"),
        ("location_source", "wifi"),
        ("location_accuracy", "exact"),
        ("location_consent_state", "accepted"),
    ],
)
def test_unknown_enum_values_are_rejected(field, value):
    with pytest.raises(PreferenceValidationError):
        normalize_preference_patch({field: value})


def test_labels_are_trimmed_and_blank_labels_are_removed():
    patch = normalize_preference_patch(
        {"region_label": "  Vinh Long  ", "explicit_interests": [" food ", ""]}
    )

    assert patch == {"region_label": "Vinh Long", "explicit_interests": ["food"]}


def test_revision_is_normalized_to_an_integer():
    patch = normalize_preference_patch({"revision": "7"})

    assert patch["revision"] == 7
    assert isinstance(patch["revision"], int)


def test_revision_rejects_values_above_json_safe_integer_range():
    with pytest.raises(PreferenceValidationError):
        normalize_preference_patch({"revision": 9_007_199_254_740_992})


def test_merge_rejects_revision_increment_past_json_safe_integer_range():
    with pytest.raises(PreferenceValidationError):
        merge_preference_patch(
            {"revision": 9_007_199_254_740_991},
            {"explicit_interests": ["food"]},
            expected_revision=9_007_199_254_740_991,
        )


def test_recommendation_reset_rejects_oversized_iso_input():
    oversized = "2026-07-28T03:04:05." + ("1" * 39) + "+00:00"
    assert len(oversized) == 65

    with pytest.raises(PreferenceValidationError):
        normalize_preference_patch({"recommendation_reset_at": oversized})


def test_revision_mismatch_is_rejected():
    with pytest.raises(PreferenceRevisionConflict):
        merge_preference_patch({"revision": 4}, {"location_enabled": False}, 3)


def test_merge_increments_revision_without_mutating_inputs():
    current = {"revision": 4, "location_enabled": True}
    patch = {"location_enabled": False}

    merged = merge_preference_patch(current, patch, expected_revision=4)

    assert merged["revision"] == 5
    assert merged["location_enabled"] is False
    assert current == {"revision": 4, "location_enabled": True}
    assert patch == {"location_enabled": False}


@pytest.mark.parametrize("location_source", ["gps", "ip"])
def test_disabled_location_does_not_accept_resolver_regions(location_source):
    merged = merge_preference_patch(
        current={"revision": 0, "location_enabled": False},
        patch={
            "region_id": "province-bt",
            "region_scope": "province",
            "location_source": location_source,
        },
        expected_revision=0,
    )

    assert merged["region_id"] is None
    assert merged["location_source"] == "default"


@pytest.mark.parametrize("location_source", ["gps", "ip"])
def test_disabling_location_clears_only_resolver_derived_region(location_source):
    merged = merge_preference_patch(
        current={
            "region_id": "province-vl",
            "region_label": "Vinh Long",
            "region_scope": "province",
            "location_source": location_source,
            "location_accuracy": "province",
            "location_consent_state": "granted",
            "location_enabled": True,
            "personalization_enabled": True,
            "explicit_interests": ["food"],
            "consent_version": "v1",
            "revision": 4,
        },
        patch={"location_enabled": False},
        expected_revision=4,
    )

    assert merged == {
        "region_id": None,
        "region_label": None,
        "region_scope": "unknown",
        "location_source": "default",
        "location_accuracy": "unknown",
        "location_consent_state": "granted",
        "location_enabled": False,
        "personalization_enabled": True,
        "explicit_interests": ["food"],
        "recommendation_reset_at": None,
        "consent_version": "v1",
        "location_reconfirm_required": False,
        "revision": 5,
        "location_provenance_version": None,
    }


@pytest.mark.parametrize("location_source", ["gps", "ip"])
def test_disabling_location_with_explicit_default_clears_resolver_region(
    location_source,
):
    merged = merge_preference_patch(
        current={
            "region_id": "province-vl",
            "region_label": "Vinh Long",
            "region_scope": "province",
            "location_source": location_source,
            "location_accuracy": "province",
            "location_enabled": True,
            "revision": 4,
        },
        patch={"location_enabled": False, "location_source": "default"},
        expected_revision=4,
    )

    assert merged["region_id"] is None
    assert merged["region_label"] is None
    assert merged["region_scope"] == "unknown"
    assert merged["location_source"] == "default"
    assert merged["location_accuracy"] == "unknown"
    assert merged["location_enabled"] is False


@pytest.mark.parametrize("location_source", ["gps", "ip"])
def test_disabling_location_cannot_launder_resolver_region_as_manual(
    location_source,
):
    merged = merge_preference_patch(
        current={
            "region_id": "province-vl",
            "region_label": "Vinh Long",
            "region_scope": "province",
            "location_source": location_source,
            "location_accuracy": "province",
            "location_enabled": True,
            "revision": 4,
        },
        patch={"location_enabled": False, "location_source": "manual"},
        expected_revision=4,
    )

    assert merged["region_id"] is None
    assert merged["region_label"] is None
    assert merged["region_scope"] == "unknown"
    assert merged["location_source"] == "default"
    assert merged["location_accuracy"] == "unknown"
    assert merged["location_enabled"] is False


def test_disabling_location_accepts_an_explicit_manual_region():
    merged = merge_preference_patch(
        current={
            "region_id": "province-vl",
            "region_label": "Vinh Long",
            "region_scope": "province",
            "location_source": "gps",
            "location_accuracy": "province",
            "location_enabled": True,
            "revision": 4,
        },
        patch={
            "region_id": "province-bt",
            "region_label": "Ben Tre",
            "region_scope": "province",
            "location_source": "manual",
            "location_accuracy": "province",
            "location_enabled": False,
        },
        expected_revision=4,
    )

    assert merged["region_id"] == "province-bt"
    assert merged["region_label"] == "Ben Tre"
    assert merged["region_scope"] == "province"
    assert merged["location_source"] == "manual"
    assert merged["location_accuracy"] == "province"
    assert merged["location_enabled"] is False


@pytest.mark.parametrize("location_source", ["gps", "ip"])
def test_disabling_location_accepts_explicit_manual_all_region(location_source):
    merged = merge_preference_patch(
        current={
            "region_id": "province-vl",
            "region_label": "Vĩnh Long",
            "region_scope": "province",
            "location_source": location_source,
            "location_accuracy": "province",
            "location_enabled": True,
            "revision": 4,
        },
        patch={
            "region_id": None,
            "region_label": None,
            "region_scope": "all",
            "location_source": "manual",
            "location_accuracy": "unknown",
            "location_enabled": False,
        },
        expected_revision=4,
    )

    assert merged["region_id"] is None
    assert merged["region_label"] is None
    assert merged["region_scope"] == "all"
    assert merged["location_source"] == "manual"
    assert merged["location_accuracy"] == "unknown"
    assert merged["location_enabled"] is False


def test_disabling_location_preserves_manual_region():
    merged = merge_preference_patch(
        current={
            "region_id": "province-vl",
            "region_label": "Vinh Long",
            "region_scope": "province",
            "location_source": "manual",
            "location_accuracy": "province",
            "location_enabled": True,
            "revision": 4,
        },
        patch={"location_enabled": False},
        expected_revision=4,
    )

    assert merged["region_id"] == "province-vl"
    assert merged["region_label"] == "Vinh Long"
    assert merged["region_scope"] == "province"
    assert merged["location_source"] == "manual"
    assert merged["location_accuracy"] == "province"
    assert merged["location_enabled"] is False


def test_recommendation_cutoff_parses_utc_timestamp():
    cutoff = recommendation_cutoff(
        {"recommendation_reset_at": "2026-07-28T03:04:05Z"}
    )

    assert cutoff == datetime(2026, 7, 28, 3, 4, 5, tzinfo=timezone.utc)


def test_recommendation_cutoff_is_none_when_not_reset():
    assert recommendation_cutoff({"recommendation_reset_at": None}) is None


@pytest.fixture
def preference_database(tmp_path, monkeypatch):
    database = Database(str(tmp_path / "preferences.db"))
    database._use_pg = False
    database._dsn = None
    with database._conn() as conn:
        conn.executescript(
            """
            CREATE TABLE user_preferences (
                user_id TEXT PRIMARY KEY,
                region_id TEXT,
                region_label TEXT,
                region_scope TEXT NOT NULL DEFAULT 'unknown',
                location_source TEXT NOT NULL DEFAULT 'default',
                location_accuracy TEXT NOT NULL DEFAULT 'unknown',
                location_consent_state TEXT NOT NULL DEFAULT 'unknown',
                location_enabled INTEGER NOT NULL DEFAULT 0,
                personalization_enabled INTEGER NOT NULL DEFAULT 0,
                explicit_interests TEXT NOT NULL DEFAULT '[]',
                recommendation_reset_at TEXT,
                consent_version TEXT,
                location_reconfirm_required INTEGER NOT NULL DEFAULT 0,
                location_provenance_version TEXT,
                revision BIGINT NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE user_preference_consents (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                consent_type TEXT NOT NULL,
                state TEXT NOT NULL,
                version TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
    monkeypatch.setattr(user_preferences, "db", database)
    return database


@pytest.fixture
def logged_in_user(monkeypatch):
    session_token = "preference-route-session"
    other_session_token = "preference-route-session-other"
    user = {
        "id": "user-1",
        "display_name": "Preference owner",
        "date_of_birth": "1990-01-02",
        "ip": "203.0.113.9",
    }
    other_user = {**user, "id": "user-2", "display_name": "Other owner"}

    async def current_user(request):
        bearer = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        if bearer == session_token:
            return user
        if bearer == other_session_token:
            return other_user
        return None

    monkeypatch.setattr(auth_middleware, "_get_current_user_or_none", current_user)
    headers = {"Authorization": f"Bearer {session_token}"}
    return SimpleNamespace(
        user=user,
        headers=headers,
        csrf_headers={
            **headers,
            "X-CSRF-Token": generate_csrf_token(session_token),
        },
        other_csrf_headers={
            "Authorization": f"Bearer {other_session_token}",
            "X-CSRF-Token": generate_csrf_token(other_session_token),
        },
    )


@pytest.fixture
def client(preference_database, logged_in_user, monkeypatch):
    monkeypatch.setattr(
        public_api,
        "settings",
        SimpleNamespace(PREFERENCE_PROFILE_V1=True, LOCATION_RESOLVER_V1=True),
        raising=False,
    )
    app = FastAPI()
    app.include_router(public_api.router)
    # Vô hiệu hoá `require_pg` cho app dựng trong test.
    #
    # Năm route preference/location của NP-1 vốn KHÔNG khai `require_pg`; hợp vào main
    # thì test hợp đồng tests/test_api_surface_contract.py bắt được — route đòi đăng
    # nhập mà thiếu guard này sẽ nổ 500 trên SQLite thay vì trả 503 rõ ràng (§1.3).
    # Guard đã được thêm, nên bộ test này (chạy SQLite) phải override như các file
    # transport khác đang làm (xem agent/tests/test_account_deletion_transport.py).
    # KHÔNG gỡ guard để test xanh — guard mới là thứ đúng.
    app.dependency_overrides[public_api.require_pg] = lambda: None
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def postgres_preference_user():
    if not live_db._use_pg:
        pytest.skip("PostgreSQL preference contract requires DATABASE_URL.")
    user_id = str(uuid4())
    with live_db._conn() as conn:
        live_db._execute(
            conn,
            f"INSERT INTO users (id, phone, display_name) "
            f"VALUES ({live_db._ph}::uuid, {live_db._ph}, {live_db._ph})",
            (user_id, f"np1-{user_id}", "NP1 preference test"),
        )
    try:
        yield user_id
    finally:
        with live_db._conn() as conn:
            live_db._execute(
                conn,
                f"DELETE FROM users WHERE id = {live_db._ph}::uuid",
                (user_id,),
            )


@pg_only
def test_postgres_patch_round_trips_uuid_jsonb_and_returned_snapshot(
    postgres_preference_user,
):
    snapshot = patch_preferences(
        postgres_preference_user,
        {
            "region_id": "province-vl",
            "region_label": "Vĩnh Long",
            "region_scope": "province",
            "location_source": "manual",
            "location_accuracy": "province",
            "explicit_interests": ["food", "culture"],
        },
        expected_revision=0,
    )

    assert snapshot["region_id"] == "province-vl"
    assert snapshot["explicit_interests"] == ["food", "culture"]
    assert snapshot["revision"] == 1
    assert load_preferences(postgres_preference_user) == snapshot


@pg_only
def test_postgres_update_clears_resolver_region_and_rejects_stale_revision(
    postgres_preference_user,
):
    first = patch_preferences_with_consents(
        postgres_preference_user,
        {
            "location_consent_state": "granted",
            "location_enabled": True,
            "explicit_interests": ["food"],
        },
        expected_revision=0,
        confirmed_location=location_resolver.LocationResolution(
            region_id="province-vl",
            region_label="Vĩnh Long",
            region_scope="province",
            location_source="gps",
            location_accuracy="province",
        ),
    )

    disabled = patch_preferences(
        postgres_preference_user,
        {"location_enabled": False, "location_source": "default"},
        expected_revision=first["revision"],
    )

    assert disabled["region_id"] is None
    assert disabled["region_label"] is None
    assert disabled["region_scope"] == "unknown"
    assert disabled["location_source"] == "default"
    assert disabled["location_accuracy"] == "unknown"
    assert disabled["explicit_interests"] == ["food"]
    assert disabled["revision"] == 2
    with pytest.raises(PreferenceRevisionConflict) as conflict:
        patch_preferences(
            postgres_preference_user,
            {"personalization_enabled": True},
            expected_revision=1,
        )
    assert conflict.value.current_revision == 2
    assert load_preferences(postgres_preference_user) == disabled


@pg_only
def test_postgres_consent_patch_persists_snapshot_and_event_atomically(
    postgres_preference_user,
):
    snapshot = patch_preferences_with_consents(
        postgres_preference_user,
        {"personalization_enabled": True},
        expected_revision=0,
    )

    with live_db._conn(commit_on_success=False) as conn:
        rows = live_db._fetchall(
            conn,
            "SELECT consent_type, state, version FROM user_preference_consents "
            f"WHERE user_id = {live_db._ph}::uuid",
            (postgres_preference_user,),
        )

    assert snapshot["personalization_enabled"] is True
    assert snapshot["consent_version"] == auth.CONSENT_VERSION
    assert snapshot["revision"] == 1
    assert load_preferences(postgres_preference_user) == snapshot
    assert [
        (
            live_db._row_to_dict(row)["consent_type"],
            live_db._row_to_dict(row)["state"],
            live_db._row_to_dict(row)["version"],
        )
        for row in rows
    ] == [("personalization", "granted", auth.CONSENT_VERSION)]


@pg_only
def test_postgres_consent_failure_rolls_back_preference_snapshot(
    postgres_preference_user, monkeypatch
):
    real_execute = live_db._execute

    def fail_consent_insert(conn, sql, params=None):
        if "INSERT INTO user_preference_consents" in sql:
            raise RuntimeError("injected postgres consent failure")
        return real_execute(conn, sql, params)

    monkeypatch.setattr(live_db, "_execute", fail_consent_insert)
    with pytest.raises(RuntimeError, match="injected postgres consent failure"):
        patch_preferences_with_consents(
            postgres_preference_user,
            {
                "location_consent_state": "granted",
                "consent_version": "privacy-v1",
            },
            expected_revision=0,
        )

    assert load_preferences(postgres_preference_user)["revision"] == 0
    with live_db._conn(commit_on_success=False) as conn:
        row = live_db._fetchone(
            conn,
            "SELECT COUNT(*) AS count FROM user_preference_consents "
            f"WHERE user_id = {live_db._ph}::uuid",
            (postgres_preference_user,),
        )
    assert live_db._row_to_dict(row)["count"] == 0


def test_load_preferences_returns_privacy_safe_public_defaults(preference_database):
    snapshot = load_preferences("user-1")

    assert snapshot == {
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
    }


def test_patch_preferences_persists_normalized_values_and_revision(preference_database):
    snapshot = patch_preferences(
        "user-1",
        {
            "region_id": "province-vl",
            "region_label": "Vĩnh Long",
            "region_scope": "province",
            "location_source": "manual",
            "location_accuracy": "province",
            "explicit_interests": ["food", "food", "culture"],
        },
        expected_revision=0,
    )

    assert snapshot["region_label"] == "Vĩnh Long"
    assert snapshot["explicit_interests"] == ["food", "culture"]
    assert snapshot["revision"] == 1
    assert load_preferences("user-1") == snapshot


def test_patch_preferences_rejects_stale_revision_without_overwriting(
    preference_database,
):
    first = patch_preferences(
        "user-1", {"personalization_enabled": True}, expected_revision=0
    )

    with pytest.raises(PreferenceRevisionConflict):
        patch_preferences(
            "user-1", {"personalization_enabled": False}, expected_revision=0
        )

    assert load_preferences("user-1") == first


def test_recommendation_reset_timestamp_round_trips_as_utc(preference_database):
    snapshot = patch_preferences(
        "user-1",
        {"recommendation_reset_at": "2026-07-28T03:04:05+07:00"},
        expected_revision=0,
    )

    expected = datetime(2026, 7, 27, 20, 4, 5, tzinfo=timezone.utc)
    assert snapshot["recommendation_reset_at"] == expected
    assert load_preferences("user-1")["recommendation_reset_at"] == expected


def test_record_preference_consent_appends_bounded_decisions(preference_database):
    record_preference_consent("user-1", "location", "granted", "v1")
    record_preference_consent("user-1", "location", "off", "v2")

    with preference_database._conn(commit_on_success=False) as conn:
        rows = conn.execute(
            "SELECT consent_type, state, version FROM user_preference_consents "
            "WHERE user_id = ? ORDER BY created_at, rowid",
            ("user-1",),
        ).fetchall()

    assert [tuple(row) for row in rows] == [
        ("location", "granted", "v1"),
        ("location", "off", "v2"),
    ]


def test_record_preference_consent_rejects_unknown_state(preference_database):
    with pytest.raises(PreferenceValidationError):
        record_preference_consent("user-1", "location", "accepted", "v1")

    with sqlite3.connect(preference_database.db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM user_preference_consents").fetchone()[0]
    assert count == 0


def test_preferences_default_snapshot_is_safe(client, logged_in_user):
    response = client.get("/api/me/preferences", headers=logged_in_user.headers)

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert response.json()["location_enabled"] is False
    assert response.json()["region_id"] is None
    assert {
        "date_of_birth",
        "dob",
        "ip",
        "latitude",
        "longitude",
        "coordinates",
    }.isdisjoint(response.json())


def test_preference_profile_flag_blocks_mutations_without_changing_snapshot(
    client, logged_in_user, monkeypatch
):
    reset_calls = []
    monkeypatch.setattr(
        public_api,
        "settings",
        SimpleNamespace(PREFERENCE_PROFILE_V1=False),
    )
    monkeypatch.setattr(
        public_api,
        "record_recommendation_reset",
        lambda owner: reset_calls.append(owner) or {"revision": 1},
    )

    patch_response = client.patch(
        "/api/me/preferences",
        json={"revision": 0, "explicit_interests": ["food"]},
        headers=logged_in_user.csrf_headers,
    )
    reset_response = client.post(
        "/api/me/recommendations/reset",
        headers=logged_in_user.csrf_headers,
    )

    assert patch_response.status_code == 404
    assert reset_response.status_code == 404
    assert reset_calls == []
    assert load_preferences("user-1")["revision"] == 0


def test_preference_profile_flag_allows_enabled_mutation(client, logged_in_user):
    response = client.patch(
        "/api/me/preferences",
        json={"revision": 0, "explicit_interests": ["food"]},
        headers=logged_in_user.csrf_headers,
    )

    assert response.status_code == 200
    assert response.json()["explicit_interests"] == ["food"]


def test_recommendation_reset_projects_internal_location_metadata(
    client, logged_in_user, monkeypatch
):
    snapshot = {
        **user_preferences._default_persisted_snapshot(),
        "recommendation_reset_at": "2026-07-29T08:00:00+00:00",
        "location_provenance_version": "resolver-v2",
        "revision": 3,
    }
    monkeypatch.setattr(
        public_api,
        "record_recommendation_reset",
        lambda _owner: snapshot,
    )

    response = client.post(
        "/api/me/recommendations/reset",
        headers=logged_in_user.csrf_headers,
    )

    assert response.status_code == 200
    assert response.json()["location_reconfirm_required"] is False
    assert response.json()["revision"] == 3
    assert "location_provenance_version" not in response.json()


def test_preferences_patch_accepts_only_exact_canonical_manual_region(
    client, logged_in_user
):
    valid = client.patch(
        "/api/me/preferences",
        json={
            "revision": 0,
            "region_id": "province-vl",
            "region_label": "Vĩnh Long",
            "region_scope": "province",
            "location_source": "manual",
            "location_accuracy": "province",
        },
        headers=logged_in_user.csrf_headers,
    )

    assert valid.status_code == 200
    assert valid.json()["region_id"] == "province-vl"

    forged = client.patch(
        "/api/me/preferences",
        json={
            "revision": 1,
            "region_id": "province-vl",
            "region_label": "10.25, 105.97",
            "region_scope": "province",
            "location_source": "manual",
            "location_accuracy": "province",
        },
        headers=logged_in_user.csrf_headers,
    )

    assert forged.status_code == 422
    snapshot = load_preferences("user-1")
    assert snapshot["revision"] == 1
    assert snapshot["region_label"] == "Vĩnh Long"
    assert "10.25" not in repr(snapshot)
    assert "105.97" not in repr(snapshot)


@pytest.mark.parametrize("location_source", ["gps", "ip"])
def test_preferences_patch_rejects_incomplete_manual_all_region_from_resolver(
    client, preference_database, logged_in_user, location_source
):
    with preference_database._conn() as conn:
        conn.execute(
            "INSERT INTO user_preferences "
            "(user_id, region_id, region_label, region_scope, location_source, "
            "location_accuracy, location_consent_state, location_enabled, "
            "location_provenance_version, revision) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "user-1",
                "province-vl",
                "Vĩnh Long",
                "province",
                location_source,
                "province",
                "granted",
                True,
                "resolver-v2",
                4,
            ),
        )

    response = client.patch(
        "/api/me/preferences",
        json={
            "revision": 4,
            "region_scope": "all",
            "location_source": "manual",
            "location_accuracy": "unknown",
        },
        headers=logged_in_user.csrf_headers,
    )

    assert response.status_code == 422
    snapshot = load_preferences("user-1")
    assert snapshot["region_id"] == "province-vl"
    assert snapshot["region_label"] == "Vĩnh Long"
    assert snapshot["region_scope"] == "province"
    assert snapshot["location_source"] == location_source
    assert snapshot["location_accuracy"] == "province"
    assert snapshot["location_enabled"] is True
    assert snapshot["revision"] == 4
    with preference_database._conn(commit_on_success=False) as conn:
        row = conn.execute(
            "SELECT location_provenance_version FROM user_preferences "
            "WHERE user_id = ?",
            ("user-1",),
        ).fetchone()
    assert row["location_provenance_version"] == "resolver-v2"


@pytest.mark.parametrize("location_source", ["gps", "ip"])
def test_preferences_patch_rejects_forged_resolver_source_without_token(
    client, logged_in_user, location_source
):
    response = client.patch(
        "/api/me/preferences",
        json={
            "revision": 0,
            "region_id": "province-vl",
            "region_label": "Vĩnh Long",
            "region_scope": "province",
            "location_source": location_source,
            "location_accuracy": "province",
            "location_enabled": True,
        },
        headers=logged_in_user.csrf_headers,
    )

    assert response.status_code == 422
    assert load_preferences("user-1")["revision"] == 0


def _resolve_fixture_location(client, logged_in_user, monkeypatch):
    now = datetime(2026, 7, 29, 8, tzinfo=timezone.utc)
    monkeypatch.setattr(location_resolver, "_utc_now", lambda: now, raising=False)
    client.app.dependency_overrides[public_api.get_reverse_geocoder] = lambda: (
        lambda *_: {
            "region_id": "province-vl",
            "region_label": "Vĩnh Long",
            "region_scope": "province",
            "location_accuracy": "province",
        }
    )
    return client.post(
        "/api/me/location/resolve",
        json={"mode": "gps", "latitude": 10.25, "longitude": 105.97},
        headers=logged_in_user.csrf_headers,
    )


def test_location_confirmation_token_is_revision_bound_and_effectively_one_use(
    client, logged_in_user, monkeypatch
):
    resolution = _resolve_fixture_location(client, logged_in_user, monkeypatch)
    token = resolution.json()["confirmation_token"]

    first = client.patch(
        "/api/me/preferences",
        json={
            "revision": 0,
            "location_confirmation_token": token,
            "location_consent_state": "granted",
            "location_enabled": True,
        },
        headers=logged_in_user.csrf_headers,
    )
    assert first.status_code == 200
    assert first.headers["Cache-Control"] == "no-store"
    assert first.json()["revision"] == 1

    replay = client.patch(
        "/api/me/preferences",
        json={
            "revision": 1,
            "location_confirmation_token": token,
            "location_consent_state": "granted",
            "location_enabled": True,
        },
        headers=logged_in_user.csrf_headers,
    )
    assert replay.status_code == 409
    assert replay.headers["Cache-Control"] == "no-store"
    assert replay.json()["revision"] == 1


def test_confirmation_token_payload_has_revision_but_no_nonce_or_raw_coordinates(
    client, logged_in_user, monkeypatch
):
    response = _resolve_fixture_location(client, logged_in_user, monkeypatch)
    encoded = response.json()["confirmation_token"].split(".", 1)[0]
    envelope = json.loads(
        base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
    )
    payload = envelope["payload"]
    assert payload["preference_revision"] == 0
    assert "issued_at" in payload
    assert "nonce" not in payload
    serialized = json.dumps(payload)
    assert "10.25" not in serialized
    assert "105.97" not in serialized


def test_preference_mutation_after_token_issue_returns_409(
    client, logged_in_user, monkeypatch
):
    token = _resolve_fixture_location(
        client, logged_in_user, monkeypatch
    ).json()["confirmation_token"]
    changed = client.patch(
        "/api/me/preferences",
        json={"revision": 0, "explicit_interests": ["food"]},
        headers=logged_in_user.csrf_headers,
    )
    assert changed.status_code == 200
    stale = client.patch(
        "/api/me/preferences",
        json={
            "revision": 1,
            "location_confirmation_token": token,
            "location_consent_state": "granted",
            "location_enabled": True,
        },
        headers=logged_in_user.csrf_headers,
    )
    assert stale.status_code == 409
    assert stale.json()["revision"] == 1


def test_v1_confirmation_purpose_is_rejected(
    client, logged_in_user, monkeypatch
):
    now = datetime(2026, 7, 29, 8, tzinfo=timezone.utc)
    monkeypatch.setattr(location_resolver, "_utc_now", lambda: now, raising=False)
    old_token = generate_user_bound_token(
        "location-confirmation-v1",
        "user-1",
        {
            "issued_at": int(now.timestamp()),
            "preference_revision": 0,
            "region_id": "province-vl",
            "region_label": "Vĩnh Long",
            "region_scope": "province",
            "location_source": "gps",
            "location_accuracy": "province",
        },
        expires_at=int(now.timestamp()) + 300,
    )
    response = client.patch(
        "/api/me/preferences",
        json={
            "revision": 0,
            "location_confirmation_token": old_token,
            "location_consent_state": "granted",
            "location_enabled": True,
        },
        headers=logged_in_user.csrf_headers,
    )
    assert response.status_code == 422


def test_resolve_token_binds_post_quarantine_revision(
    client, preference_database, logged_in_user, monkeypatch
):
    _insert_unsafe_preference(preference_database)
    response = _resolve_fixture_location(client, logged_in_user, monkeypatch)
    encoded = response.json()["confirmation_token"].split(".", 1)[0]
    envelope = json.loads(
        base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
    )
    assert envelope["payload"]["preference_revision"] == 8
    assert load_preferences("user-1")["revision"] == 8


def test_resolver_confirmation_token_is_required_user_bound_and_transient(
    client, preference_database, logged_in_user, monkeypatch
):
    resolution = _resolve_fixture_location(client, logged_in_user, monkeypatch)

    assert resolution.status_code == 200
    assert resolution.headers["Cache-Control"] == "no-store"
    token = resolution.json()["confirmation_token"]
    assert isinstance(token, str) and token
    assert "10.25" not in token
    assert "105.97" not in token

    wrong_owner = client.patch(
        "/api/me/preferences",
        json={
            "revision": 0,
            "location_confirmation_token": token,
            "location_consent_state": "granted",
            "location_enabled": True,
        },
        headers=logged_in_user.other_csrf_headers,
    )
    assert wrong_owner.status_code == 422
    assert load_preferences("user-2")["revision"] == 0

    forged = client.patch(
        "/api/me/preferences",
        json={
            "revision": 0,
            "location_confirmation_token": token[:-1] + ("A" if token[-1] != "A" else "B"),
            "location_consent_state": "granted",
            "location_enabled": True,
        },
        headers=logged_in_user.csrf_headers,
    )
    assert forged.status_code == 422
    assert load_preferences("user-1")["revision"] == 0

    confirmed = client.patch(
        "/api/me/preferences",
        json={
            "revision": 0,
            "location_confirmation_token": token,
            "location_consent_state": "granted",
            "location_enabled": True,
        },
        headers=logged_in_user.csrf_headers,
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["region_id"] == "province-vl"
    assert confirmed.json()["location_source"] == "gps"
    assert confirmed.json()["location_reconfirm_required"] is False
    assert "location_provenance_version" not in confirmed.json()
    assert "confirmation_token" not in confirmed.json()
    public_snapshot = load_preferences("user-1")
    assert "location_provenance_version" not in public_snapshot
    assert "confirmation_token" not in repr(public_snapshot)
    with preference_database._conn(commit_on_success=False) as conn:
        row = conn.execute(
            "SELECT location_provenance_version FROM user_preferences "
            "WHERE user_id = ?",
            ("user-1",),
        ).fetchone()
    assert row["location_provenance_version"] == "resolver-v2"


def test_manual_all_region_route_wins_over_resolver_confirmation(
    client, preference_database, logged_in_user, monkeypatch
):
    selected = client.patch(
        "/api/me/preferences",
        json={
            "revision": 0,
            "region_id": None,
            "region_label": None,
            "region_scope": "all",
            "location_source": "manual",
            "location_accuracy": "unknown",
        },
        headers=logged_in_user.csrf_headers,
    )
    assert selected.status_code == 200

    now = datetime(2026, 7, 29, 8, tzinfo=timezone.utc)
    monkeypatch.setattr(location_resolver, "_utc_now", lambda: now, raising=False)
    client.app.dependency_overrides[public_api.get_reverse_geocoder] = lambda: (
        lambda *_: {
            "region_id": "province-vl",
            "region_label": "Vĩnh Long",
            "region_scope": "province",
            "location_accuracy": "province",
        }
    )
    resolution = client.post(
        "/api/me/location/resolve",
        json={"mode": "gps", "latitude": 10.25, "longitude": 105.97},
        headers=logged_in_user.csrf_headers,
    )
    token = resolution.json()["confirmation_token"]

    confirmed = client.patch(
        "/api/me/preferences",
        json={
            "revision": 1,
            "location_confirmation_token": token,
            "location_consent_state": "granted",
            "location_enabled": True,
        },
        headers=logged_in_user.csrf_headers,
    )

    assert confirmed.status_code == 200
    assert confirmed.json()["region_id"] is None
    assert confirmed.json()["region_scope"] == "all"
    assert confirmed.json()["location_source"] == "manual"
    with preference_database._conn(commit_on_success=False) as conn:
        row = conn.execute(
            "SELECT location_provenance_version FROM user_preferences "
            "WHERE user_id = ?",
            ("user-1",),
        ).fetchone()
    assert row["location_provenance_version"] is None


@pytest.mark.parametrize("location_source", ["gps", "ip"])
def test_preferences_patch_disables_location_with_manual_all_region(
    client, preference_database, logged_in_user, location_source
):
    with preference_database._conn() as conn:
        conn.execute(
            "INSERT INTO user_preferences "
            "(user_id, region_id, region_label, region_scope, location_source, "
            "location_accuracy, location_consent_state, location_enabled, "
            "location_provenance_version, revision) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "user-1",
                "province-vl",
                "Vĩnh Long",
                "province",
                location_source,
                "province",
                "granted",
                True,
                "resolver-v2",
                4,
            ),
        )

    response = client.patch(
        "/api/me/preferences",
        json={
            "revision": 4,
            "region_id": None,
            "region_label": None,
            "region_scope": "all",
            "location_source": "manual",
            "location_accuracy": "unknown",
            "location_enabled": False,
        },
        headers=logged_in_user.csrf_headers,
    )

    assert response.status_code == 200
    assert response.json()["region_id"] is None
    assert response.json()["region_label"] is None
    assert response.json()["region_scope"] == "all"
    assert response.json()["location_source"] == "manual"
    assert response.json()["location_accuracy"] == "unknown"
    assert response.json()["location_enabled"] is False
    assert "location_provenance_version" not in response.json()
    assert load_preferences("user-1") == response.json()


def test_resolver_confirmation_token_expires_at_the_short_lived_boundary(
    client, logged_in_user, monkeypatch
):
    issued_at = datetime(2026, 7, 29, 8, tzinfo=timezone.utc)
    monkeypatch.setattr(location_resolver, "_utc_now", lambda: issued_at, raising=False)
    monkeypatch.setattr(public_api, "get_client_ip", lambda _request: "203.0.113.8")
    client.app.dependency_overrides[public_api.get_ip_geocoder] = lambda: (
        lambda *_: {
            "region_id": "province-vl",
            "region_label": "Vĩnh Long",
            "region_scope": "province",
            "location_accuracy": "province",
        }
    )
    resolution = client.post(
        "/api/me/location/resolve",
        json={"mode": "ip"},
        headers=logged_in_user.csrf_headers,
    )
    token = resolution.json()["confirmation_token"]
    monkeypatch.setattr(
        location_resolver,
        "_utc_now",
        lambda: issued_at.replace(minute=6),
        raising=False,
    )

    response = client.patch(
        "/api/me/preferences",
        json={
            "revision": 0,
            "location_confirmation_token": token,
            "location_consent_state": "granted",
            "location_enabled": True,
        },
        headers=logged_in_user.csrf_headers,
    )

    assert response.status_code == 422
    assert load_preferences("user-1")["revision"] == 0


def test_preferences_get_requires_authenticated_owner(client):
    response = client.get("/api/me/preferences")

    assert response.status_code == 401


def test_preferences_patch_requires_revision_and_csrf(client, logged_in_user):
    response = client.patch(
        "/api/me/preferences",
        json={"location_enabled": True},
        headers=logged_in_user.headers,
    )

    assert response.status_code == 403


def test_preferences_patch_missing_revision_after_valid_csrf(client, logged_in_user):
    response = client.patch(
        "/api/me/preferences",
        json={"location_enabled": True},
        headers=logged_in_user.csrf_headers,
    )

    assert response.status_code == 422


def test_preferences_revision_conflict_returns_current_snapshot(
    client, logged_in_user
):
    first = client.patch(
        "/api/me/preferences",
        json={"revision": 0, "explicit_interests": ["food"]},
        headers=logged_in_user.csrf_headers,
    )
    assert first.status_code == 200

    response = client.patch(
        "/api/me/preferences",
        json={"revision": 0, "explicit_interests": ["culture"]},
        headers=logged_in_user.csrf_headers,
    )

    assert response.status_code == 409
    assert response.headers["Cache-Control"] == "no-store"
    assert response.json()["revision"] == 1
    assert response.json()["explicit_interests"] == ["food"]


def test_preferences_patch_uses_authenticated_owner_not_client_user_id(
    client, logged_in_user, preference_database
):
    response = client.patch(
        "/api/me/preferences",
        json={
            "revision": 0,
            "user_id": "user-2",
            "personalization_enabled": True,
        },
        headers=logged_in_user.csrf_headers,
    )

    assert response.status_code == 422
    assert load_preferences("user-1")["revision"] == 0
    assert load_preferences("user-2")["revision"] == 0


def test_preferences_patch_records_changed_consents_and_returns_safe_history(
    client, logged_in_user
):
    response = client.patch(
        "/api/me/preferences",
        json={
            "revision": 0,
            "location_consent_state": "granted",
            "location_enabled": True,
            "personalization_enabled": True,
            "consent_version": "privacy-v1",
        },
        headers=logged_in_user.csrf_headers,
    )

    assert response.status_code == 200
    assert response.json()["revision"] == 1
    history = client.get(
        "/api/me/preferences/consents", headers=logged_in_user.headers
    )
    assert history.status_code == 200
    assert history.headers["Cache-Control"] == "no-store"
    assert {
        (item["consent_type"], item["state"], item["version"])
        for item in history.json()["consents"]
    } == {
        ("location", "granted", "privacy-v1"),
        ("personalization", "granted", "privacy-v1"),
    }
    assert all(
        {"ip", "latitude", "longitude", "coordinates", "date_of_birth"}.isdisjoint(
            item
        )
        for item in history.json()["consents"]
    )


@pytest.mark.parametrize(
    ("preference_patch", "expected_type", "expected_state"),
    [
        ({"personalization_enabled": True}, "personalization", "granted"),
        ({"location_consent_state": "granted"}, "location", "granted"),
    ],
)
def test_preferences_initial_consent_toggle_uses_server_policy_version(
    client,
    logged_in_user,
    preference_patch,
    expected_type,
    expected_state,
):
    response = client.patch(
        "/api/me/preferences",
        json={"revision": 0, **preference_patch},
        headers=logged_in_user.csrf_headers,
    )

    assert response.status_code == 200
    assert response.json()["consent_version"] == auth.CONSENT_VERSION
    history = client.get(
        "/api/me/preferences/consents", headers=logged_in_user.headers
    )
    assert [
        (item["consent_type"], item["state"], item["version"])
        for item in history.json()["consents"]
    ] == [(expected_type, expected_state, auth.CONSENT_VERSION)]


@pytest.mark.parametrize("location_source", ["gps", "ip"])
def test_preferences_location_off_rejects_manual_source_laundering(
    client, logged_in_user, location_source, monkeypatch
):
    def provider(*_):
        return {
            "region_id": "province-vl",
            "region_label": "Vĩnh Long",
            "region_scope": "province",
            "location_accuracy": "province",
        }

    if location_source == "gps":
        client.app.dependency_overrides[public_api.get_reverse_geocoder] = lambda: provider
        resolution = client.post(
            "/api/me/location/resolve",
            json={"mode": "gps", "latitude": 10.25, "longitude": 105.97},
            headers=logged_in_user.csrf_headers,
        )
    else:
        monkeypatch.setattr(public_api, "get_client_ip", lambda _request: "203.0.113.8")
        client.app.dependency_overrides[public_api.get_ip_geocoder] = lambda: provider
        resolution = client.post(
            "/api/me/location/resolve",
            json={"mode": "ip"},
            headers=logged_in_user.csrf_headers,
        )
    first = client.patch(
        "/api/me/preferences",
        json={
            "revision": 0,
            "location_confirmation_token": resolution.json()["confirmation_token"],
            "location_consent_state": "granted",
            "location_enabled": True,
        },
        headers=logged_in_user.csrf_headers,
    )
    assert first.status_code == 200

    laundering = client.patch(
        "/api/me/preferences",
        json={
            "revision": 1,
            "location_enabled": False,
            "location_source": "manual",
        },
        headers=logged_in_user.csrf_headers,
    )
    assert laundering.status_code == 422

    response = client.patch(
        "/api/me/preferences",
        json={"revision": 1, "location_enabled": False},
        headers=logged_in_user.csrf_headers,
    )
    assert response.status_code == 200
    assert response.json()["region_id"] is None
    assert response.json()["region_label"] is None
    assert response.json()["region_scope"] == "unknown"
    assert response.json()["location_source"] == "default"
    assert response.json()["location_accuracy"] == "unknown"


@pytest.mark.parametrize(
    ("revision", "expected_status"),
    [
        (9_007_199_254_740_991, 409),
        (9_007_199_254_740_992, 422),
    ],
)
def test_preferences_revision_is_bounded_for_json_safe_integer(
    client, logged_in_user, revision, expected_status
):
    response = client.patch(
        "/api/me/preferences",
        json={"revision": revision, "explicit_interests": ["food"]},
        headers=logged_in_user.csrf_headers,
    )

    assert response.status_code == expected_status
    assert str(revision) not in response.text
    assert load_preferences("user-1")["revision"] == 0


@pytest.mark.parametrize(
    ("fraction_digits", "expected_status"),
    [
        (38, 200),
        (39, 422),
    ],
)
def test_preferences_recommendation_reset_iso_input_is_bounded(
    client, logged_in_user, fraction_digits, expected_status
):
    timestamp = "2026-07-28T03:04:05." + ("1" * fraction_digits) + "+00:00"
    assert len(timestamp) == (64 if fraction_digits == 38 else 65)

    response = client.patch(
        "/api/me/preferences",
        json={"revision": 0, "recommendation_reset_at": timestamp},
        headers=logged_in_user.csrf_headers,
    )

    assert response.status_code == expected_status
    if expected_status == 200:
        assert response.json()["revision"] == 1
    else:
        assert timestamp not in response.text
        assert load_preferences("user-1")["revision"] == 0


def test_preferences_patch_rejects_unbounded_or_sensitive_fields(
    client, logged_in_user
):
    response = client.patch(
        "/api/me/preferences",
        json={
            "revision": 0,
            "region_id": "x" * 129,
            "coordinates": {"latitude": 10.1, "longitude": 106.2},
            "date_of_birth": "1990-01-02",
        },
        headers=logged_in_user.csrf_headers,
    )

    assert response.status_code == 422
    assert "coordinates" not in response.text
    assert "10.1" not in response.text
    assert "106.2" not in response.text
    assert "1990-01-02" not in response.text
    assert load_preferences("user-1")["revision"] == 0


def test_preferences_patch_is_rate_limited(client, logged_in_user, monkeypatch):
    monkeypatch.setattr(public_api, "PREFERENCE_PATCH_RATE_LIMIT", 2, raising=False)
    for revision in range(2):
        response = client.patch(
            "/api/me/preferences",
            json={"revision": revision, "explicit_interests": [f"interest-{revision}"]},
            headers=logged_in_user.csrf_headers,
        )
        assert response.status_code == 200

    blocked = client.patch(
        "/api/me/preferences",
        json={"revision": 2, "explicit_interests": ["blocked"]},
        headers=logged_in_user.csrf_headers,
    )

    assert blocked.status_code == 429
    assert load_preferences("user-1")["explicit_interests"] == ["interest-1"]


def test_preferences_patch_rolls_back_snapshot_when_consent_insert_fails(
    client, logged_in_user, preference_database, monkeypatch
):
    real_execute = preference_database._execute

    def fail_consent_insert(conn, sql, params=None):
        if "INSERT INTO user_preference_consents" in sql:
            raise RuntimeError("injected consent failure")
        return real_execute(conn, sql, params)

    monkeypatch.setattr(preference_database, "_execute", fail_consent_insert)
    with TestClient(client.app, raise_server_exceptions=False) as response_client:
        response = response_client.patch(
            "/api/me/preferences",
            json={
                "revision": 0,
                "location_consent_state": "granted",
                "consent_version": "privacy-v1",
            },
            headers=logged_in_user.csrf_headers,
        )

    assert response.status_code == 500
    assert load_preferences("user-1")["revision"] == 0
    with sqlite3.connect(preference_database.db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM user_preference_consents").fetchone()[0]
    assert count == 0
