"""Tests for public_api source-freshness (P0-6).

Freshness must be computed from the real, human-set verification date in
``attributes.verifiedAt`` only — never from a legacy top-level field or
``updatedAt`` (an import timestamp), so a bulk re-import can't make pages look
"freshly verified".
"""
from datetime import datetime, timedelta, timezone

from public_api import _build_source_freshness


def _days_ago(n: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=n)).isoformat()


def test_fresh_from_recent_verifiedAt():
    e = {"attributes": {"verifiedAt": _days_ago(10)}, "updatedAt": _days_ago(500)}
    assert _build_source_freshness(e)["freshness_status"] == "fresh"


def test_unknown_when_no_verifiedAt_even_if_updated_recently():
    # An import timestamp must NOT make a page look "fresh".
    e = {"updatedAt": _days_ago(1)}
    assert _build_source_freshness(e)["freshness_status"] == "unknown"


def test_status_reflects_verifiedAt_not_updatedAt():
    # Old verification + brand-new import → status reflects the OLD verification.
    e = {"attributes": {"verifiedAt": _days_ago(400)}, "updatedAt": _days_ago(1)}
    assert _build_source_freshness(e)["freshness_status"] == "stale"


def test_no_dates_is_unknown():
    assert _build_source_freshness({})["freshness_status"] == "unknown"


def test_detail_source_freshness_projects_canonical_source_tier():
    result = _build_source_freshness(
        {
            "official": True,
            "source": {"title": "Cổng thông tin tỉnh Vĩnh Long"},
            "attributes": {"verifiedAt": _days_ago(10)},
        }
    )

    assert result["source_tier"] == "official"
    assert result["freshness_status"] == "fresh"


def test_top_level_verified_at_is_never_verification_authority() -> None:
    result = _build_source_freshness(
        {"verifiedAt": _days_ago(1), "updatedAt": _days_ago(1)}
    )
    assert result["verified_at"] is None
    assert result["days_since_verified"] is None
    assert result["freshness_status"] == "unknown"


def test_attribute_wins_when_top_level_value_conflicts() -> None:
    result = _build_source_freshness(
        {
            "verifiedAt": _days_ago(1),
            "updatedAt": _days_ago(1),
            "attributes": {"verifiedAt": _days_ago(400)},
        }
    )
    assert result["freshness_status"] == "stale"


def test_public_projection_removes_legacy_verified_at() -> None:
    from public_api import _project_public_entity_media

    projected = _project_public_entity_media(
        {"id": "entity-1", "verifiedAt": "2026-07-27T00:00:00Z"}
    )
    assert "verifiedAt" not in projected


# ── The revision the projection is serving (publication verification reads it) ──

def test_the_projection_states_the_revision_it_is_serving():
    from public_api import _public_entity_revision

    assert _public_entity_revision({"revision": 8}) == 8


def test_a_missing_or_unusable_revision_reads_as_the_first_one():
    from public_api import _public_entity_revision

    # Never None and never zero: verification compares this number, and a blank
    # would compare equal to nothing and quietly pass.
    for entity in ({}, {"revision": None}, {"revision": "x"}, {"revision": 0}):
        assert _public_entity_revision(entity) == 1
