import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import user_preferences
from database import Database
from user_preferences import (
    PreferenceRevisionConflict,
    PreferenceValidationError,
    load_preferences,
    merge_preference_patch,
    normalize_preference_patch,
    patch_preferences,
    recommendation_cutoff,
    record_preference_consent,
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
                revision INTEGER NOT NULL DEFAULT 0,
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
        "revision": 0,
    }


def test_patch_preferences_persists_normalized_values_and_revision(preference_database):
    snapshot = patch_preferences(
        "user-1",
        {
            "region_id": "province-vl",
            "region_label": "  Vinh Long  ",
            "region_scope": "province",
            "location_source": "manual",
            "explicit_interests": ["food", "food", "culture"],
        },
        expected_revision=0,
    )

    assert snapshot["region_label"] == "Vinh Long"
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
