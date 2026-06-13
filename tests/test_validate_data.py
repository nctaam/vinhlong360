from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("validate_data", ROOT / "scripts" / "validate_data.py")
validate_data = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = validate_data
SPEC.loader.exec_module(validate_data)


def test_validate_reports_summary_quality_by_entity_kind(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "p-vinh-long", "type": "place", "name": "Phường Vĩnh Long"},
            {"id": "attraction-1", "type": "attraction", "name": "Điểm tham quan"},
        ],
        "relationships": [],
        "itineraries": [],
    }

    issues, stats = validate_data.validate(data, tmp_path / "data.json")
    codes = {issue.code for issue in issues}

    assert stats["missing_summary"] == 2
    assert stats["missing_summary_place"] == 1
    assert stats["missing_summary_non_place"] == 1
    assert "missing_summary_place" in codes
    assert "missing_summary_non_place" in codes


def test_validate_reports_location_quality_by_entity_kind(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "p-vinh-long", "type": "place", "name": "Phường Vĩnh Long", "summary": "Place"},
            {"id": "dish-1", "type": "dish", "name": "Món ăn", "summary": "Dish", "area": "vinh-long"},
        ],
        "relationships": [],
        "itineraries": [],
    }

    _issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["missing_location"] == 2
    assert stats["missing_location_place"] == 1
    assert stats["missing_location_non_place"] == 1

def test_validate_flags_coordinates_outside_mekong_bbox(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "p-vinh-long", "type": "place", "name": "Phuong Vinh Long", "summary": "Place", "coordinates": [10.25, 106.0]},
            {"id": "bad", "type": "attraction", "name": "Bad", "summary": "Bad", "area": "vinh-long", "coordinates": [21.0, 105.8]},
        ],
        "relationships": [],
        "itineraries": [],
    }

    issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["out_of_bounds_coordinates"] == 1
    assert "out_of_bounds_coordinates" in {issue.code for issue in issues}

def test_validate_flags_area_place_conflicts(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "xa-an-binh", "type": "place", "name": "Xa An Binh", "summary": "Place", "area": "vinh-long", "coordinates": [10.25, 106.0]},
            {"id": "ben-tre-item", "type": "product", "name": "Ben Tre item", "summary": "Item", "area": "ben-tre", "placeId": "xa-an-binh", "coordinates": [10.24, 106.02]},
        ],
        "relationships": [],
        "itineraries": [],
    }

    issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["area_place_conflicts"] == 1
    assert "area_place_conflicts" in {issue.code for issue in issues}

def test_validate_flags_bad_near_edges(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "a", "type": "attraction", "name": "A", "summary": "A", "area": "vinh-long", "coordinates": [10.25, 106.0]},
            {"id": "b", "type": "attraction", "name": "B", "summary": "B", "area": "vinh-long", "coordinates": [11.25, 107.0]},
            {"id": "c", "type": "attraction", "name": "C", "summary": "C", "area": "vinh-long"},
        ],
        "relationships": [
            {"from": "a", "to": "b", "type": "near"},
            {"from": "a", "to": "c", "type": "near"},
        ],
        "itineraries": [],
    }

    issues, stats = validate_data.validate(data, tmp_path / "data.json")
    codes = {issue.code for issue in issues}

    assert stats["far_near_relationships"] == 1
    assert stats["near_missing_location"] == 1
    assert "far_near_relationships" in codes
    assert "near_missing_location" in codes

def test_validate_flags_relationship_fanout(tmp_path: Path) -> None:
    entities = [
        {"id": "hub", "type": "attraction", "name": "Hub", "summary": "Hub", "area": "vinh-long", "coordinates": [10.25, 106.0]}
    ]
    relationships = []
    for index in range(validate_data.MAX_DIRECT_RELATIONSHIPS + 1):
        entity_id = f"e-{index}"
        entities.append({"id": entity_id, "type": "attraction", "name": entity_id, "summary": entity_id, "area": "vinh-long", "coordinates": [10.26, 106.01]})
        relationships.append({"from": "hub", "to": entity_id, "type": "related_to"})
    data = {"entities": entities, "relationships": relationships, "itineraries": []}

    issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["relationship_fanout_over_limit"] == 1
    assert "relationship_fanout" in {issue.code for issue in issues}

def test_validate_flags_produced_in_area_conflicts(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "product-vl", "type": "product", "name": "Product VL", "summary": "Product", "area": "vinh-long", "coordinates": [10.25, 106.0]},
            {"id": "village-bt", "type": "craft_village", "name": "Village BT", "summary": "Village", "area": "ben-tre", "coordinates": [10.26, 106.1]},
        ],
        "relationships": [
            {"from": "product-vl", "to": "village-bt", "type": "produced_in"},
        ],
        "itineraries": [],
    }

    issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["produced_in_area_conflicts"] == 1
    assert "produced_in_area_conflicts" in {issue.code for issue in issues}
