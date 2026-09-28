from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import public_api
import user_preferences
from location_resolver import LocationResolution


def test_legacy_manual_regions_normalize_to_current_vinh_long():
    patch = {
        "region_id": "province-bt",
        "region_label": "Bến Tre",
        "region_scope": "province",
        "location_source": "manual",
        "location_accuracy": "province",
    }

    authorized = user_preferences._authorize_region_patch(patch, confirmed_location=None)

    assert authorized == {
        "region_id": "province-vl",
        "region_label": "Vĩnh Long",
        "region_scope": "province",
        "location_source": "manual",
        "location_accuracy": "province",
    }


def test_legacy_resolver_province_normalizes_without_accepting_raw_coordinates():
    resolution = LocationResolution(
        "province-tv", "Trà Vinh", "province", "gps", "province"
    )

    authorized = user_preferences._authorize_region_patch({}, confirmed_location=resolution)

    assert authorized["region_id"] == "province-vl"
    assert authorized["region_label"] == "Vĩnh Long"
    assert authorized["location_source"] == "gps"


def test_legacy_persisted_snapshot_is_projected_as_current_vinh_long():
    snapshot = user_preferences._snapshot_from_mapping(
        {
            "region_id": "province-bt",
            "region_label": "Bến Tre",
            "region_scope": "province",
            "location_source": "manual",
            "location_accuracy": "province",
        }
    )

    assert snapshot["region_id"] == "province-vl"
    assert snapshot["region_label"] == "Vĩnh Long"


def test_loading_legacy_manual_snapshot_writes_canonical_value_back(monkeypatch):
    raw = user_preferences._default_persisted_snapshot()
    raw.update(
        {
            "region_id": "province-bt",
            "region_label": "Bến Tre",
            "region_scope": "province",
            "location_source": "manual",
            "location_accuracy": "province",
            "revision": 7,
        }
    )
    written = []
    monkeypatch.setattr(user_preferences, "_select_preferences", lambda *args, **kwargs: raw)

    def write_back(conn, owner, snapshot, expected_revision):
        written.append((owner, snapshot.copy(), expected_revision))
        return snapshot

    monkeypatch.setattr(user_preferences, "_update_persisted_snapshot_in_connection", write_back)

    loaded = user_preferences._load_persisted_preferences_in_connection(
        object(), "owner-1", for_update=False, heal=True
    )

    assert loaded["region_id"] == "province-vl"
    assert written == [("owner-1", loaded, 7)]
    assert loaded["region_label"] == "Vĩnh Long"
    assert loaded["revision"] == 8


def test_api_areas_exposes_one_current_province_with_124_direct_children(monkeypatch):
    places = [
        {"id": "province-vl", "name": "Vĩnh Long", "type": "place", "parentId": None, "status": "published", "verified": True},
        {"id": "old-ben-tre", "name": "Bến Tre", "type": "place", "area": "ben-tre", "parentId": None, "status": "published", "verified": True},
        {"id": "bad-type", "name": "Not a place", "type": "event", "level": "xa", "parentId": "vinh-long", "status": "published", "verified": True},
        {"id": "bad-level", "name": "Bad level", "type": "place", "level": "huyen", "parentId": "vinh-long", "status": "published", "verified": True},
        {"id": "old-tv", "name": "Trà Vinh", "type": "place", "level": "phuong", "parentId": "tra-vinh", "status": "published", "verified": True},
    ] + [
        {
            "id": f"phuong-{index}",
            "name": f"Phường {index}",
            "type": "place",
            "level": "phuong",
            "parentId": "vinh-long",
            "status": "published",
            "verified": True,
        }
        for index in range(35)
    ] + [
        {
            "id": f"xa-{index}",
            "name": f"Xã {index}",
            "type": "place",
            "level": "xa",
            "parentId": "vinh-long",
            "status": "published",
            "verified": True,
        }
        for index in range(89)
    ]
    monkeypatch.setattr(public_api.db, "all_entities", lambda: places)

    class Response:
        headers: dict[str, str] = {}

    result = asyncio.run(public_api.list_areas(Response()))

    assert result["total_places"] == 124
    assert len(result["areas"]) == 1
    province = result["areas"][0]
    assert province["id"] == "vinh-long"
    assert province["name"] == "Vĩnh Long"
    assert province["parentId"] is None
    assert province["count"] == 124
    assert province["places"] == province["children"]
    assert {place["type"] for place in province["places"]} == {"xa", "phuong"}
    assert sum(place["type"] == "phuong" for place in province["places"]) == 35
    assert sum(place["type"] == "xa" for place in province["places"]) == 89


def test_api_areas_filters_before_cap_preserving_all_current_children(monkeypatch):
    unrelated = [
        {
            "id": f"old-{index}",
            "name": f"Old {index}",
            "type": "place",
            "level": "huyen",
            "parentId": "old-province",
            "status": "published",
            "verified": True,
        }
        for index in range(1100)
    ]
    current = [
        {
            "id": f"phuong-{index}",
            "name": f"Phuong {index}",
            "type": "place",
            "level": "phuong",
            "parentId": "vinh-long",
            "status": "published",
            "verified": True,
        }
        for index in range(35)
    ] + [
        {
            "id": f"xa-{index}",
            "name": f"Xa {index}",
            "type": "place",
            "level": "xa",
            "parentId": "vinh-long",
            "status": "published",
            "verified": True,
        }
        for index in range(89)
    ]
    monkeypatch.setattr(public_api.db, "all_entities", lambda: unrelated + current)

    class Response:
        headers: dict[str, str] = {}

    result = asyncio.run(public_api.list_areas(Response()))
    province = result["areas"][0]
    assert result["total_places"] == 124
    assert len(province["places"]) == 124
    assert sum(place["level"] == "phuong" for place in province["places"]) == 35
    assert sum(place["level"] == "xa" for place in province["places"]) == 89
