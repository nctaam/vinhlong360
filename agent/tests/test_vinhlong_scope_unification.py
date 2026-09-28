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


def test_api_areas_exposes_one_current_province_with_124_direct_children(monkeypatch):
    places = [
        {"id": "province-vl", "name": "Vĩnh Long", "type": "place", "parentId": None, "status": "published", "verified": True},
        {"id": "old-ben-tre", "name": "Bến Tre", "type": "place", "area": "ben-tre", "parentId": None, "status": "published", "verified": True},
    ] + [
        {
            "id": f"xa-{index}",
            "name": f"Ward {index}",
            "type": "place",
            "area": "historical-area",
            "parentId": "vinh-long",
            "status": "published",
            "verified": True,
        }
        for index in range(124)
    ]
    monkeypatch.setattr(public_api.db, "all_entities", lambda: places)

    class Response:
        headers: dict[str, str] = {}

    result = asyncio.run(public_api.list_areas(Response()))

    assert result["total_places"] == 124
    assert result["areas"] == [
        {
            "id": "vinh-long",
            "name": "Vĩnh Long",
            "parentId": None,
            "children": [
                {"id": place["id"], "name": place["name"], "type": "xa", "parentId": "vinh-long"}
                for place in places[2:]
            ],
            "count": 124,
        }
    ]
