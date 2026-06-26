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
            # DI-001/005: bbox siết (9.0–11.0, 105.0–107.0) — điểm này lọt bbox cũ (11.5/107.5) nhưng nay phải bị bắt
            {"id": "edge", "type": "attraction", "name": "Edge", "summary": "Edge", "area": "tra-vinh", "coordinates": [11.3, 106.5]},
        ],
        "relationships": [],
        "itineraries": [],
    }

    issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["out_of_bounds_coordinates"] == 2
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

def test_validate_excludes_hierarchical_from_fanout(tmp_path: Path) -> None:
    # located_in (phân-cấp) KHÔNG tính vào ngưỡng fanout-120: một tỉnh chứa
    # >120 xã/phường là hợp lệ, không phải nhiễu "liên quan/gần đây".
    entities = [{"id": "tinh", "type": "place", "name": "Tinh", "summary": "T", "area": "vinh-long", "coordinates": [10.25, 106.0]}]
    relationships = []
    for index in range(validate_data.MAX_DIRECT_RELATIONSHIPS + 5):
        wid = f"w-{index}"
        entities.append({"id": wid, "type": "place", "name": wid, "summary": wid, "area": "vinh-long", "coordinates": [10.26, 106.01]})
        relationships.append({"from": wid, "to": "tinh", "type": "located_in"})
    data = {"entities": entities, "relationships": relationships, "itineraries": []}

    issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["relationship_fanout_over_limit"] == 0
    assert "relationship_fanout" not in {issue.code for issue in issues}


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


def test_validate_flags_produced_in_targeting_wrong_type(tmp_path: Path) -> None:
    """produced_in should target place or craft_village, not product."""
    data = {
        "entities": [
            {"id": "product-a", "type": "product", "name": "Product A", "summary": "A", "area": "vinh-long", "coordinates": [10.25, 106.0]},
            {"id": "product-b", "type": "product", "name": "Product B", "summary": "B", "area": "vinh-long", "coordinates": [10.26, 106.01]},
            {"id": "village-ok", "type": "craft_village", "name": "Village OK", "summary": "V", "area": "vinh-long", "coordinates": [10.27, 106.02]},
        ],
        "relationships": [
            {"from": "product-a", "to": "product-b", "type": "produced_in"},  # wrong target type
            {"from": "product-a", "to": "village-ok", "type": "produced_in"},  # correct
        ],
        "itineraries": [],
    }

    issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["produced_in_target_type_errors"] == 1
    assert "produced_in_target_type" in {issue.code for issue in issues}


def test_validate_produced_in_allows_place_and_craft_village(tmp_path: Path) -> None:
    """produced_in targeting place or craft_village should NOT flag errors."""
    data = {
        "entities": [
            {"id": "product-a", "type": "product", "name": "Product A", "summary": "A", "area": "vinh-long", "coordinates": [10.25, 106.0]},
            {"id": "place-1", "type": "place", "name": "Place 1", "summary": "P", "area": "vinh-long", "coordinates": [10.26, 106.01]},
            {"id": "village-1", "type": "craft_village", "name": "Village 1", "summary": "V", "area": "vinh-long", "coordinates": [10.27, 106.02]},
        ],
        "relationships": [
            {"from": "product-a", "to": "place-1", "type": "produced_in"},
            {"from": "product-a", "to": "village-1", "type": "produced_in"},
        ],
        "itineraries": [],
    }

    issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["produced_in_target_type_errors"] == 0
    assert "produced_in_target_type" not in {issue.code for issue in issues}


def test_validate_flags_place_level_none(tmp_path: Path) -> None:
    """Place entities with level=None should be flagged."""
    data = {
        "entities": [
            {"id": "place-ok", "type": "place", "name": "Place OK", "summary": "OK", "level": "xa", "area": "vinh-long", "coordinates": [10.25, 106.0]},
            {"id": "place-no-level", "type": "place", "name": "Place No Level", "summary": "No level", "area": "vinh-long", "coordinates": [10.26, 106.01]},
        ],
        "relationships": [],
        "itineraries": [],
    }

    issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["place_level_none"] == 1
    assert "place_level_none" in {issue.code for issue in issues}


def test_validate_flags_self_loop_relationships(tmp_path: Path) -> None:
    """Relationships where source==target are flagged as self-loops."""
    data = {
        "entities": [
            {"id": "a", "type": "attraction", "name": "A", "summary": "A", "area": "vinh-long", "coordinates": [10.25, 106.0]},
        ],
        "relationships": [
            {"from": "a", "to": "a", "type": "related_to"},
        ],
        "itineraries": [],
    }

    issues, _stats = validate_data.validate(data, tmp_path / "data.json")

    assert "self_loop_relationships" in {issue.code for issue in issues}


def test_validate_no_self_loop_when_distinct(tmp_path: Path) -> None:
    """Normal relationships (source!=target) should not trigger self-loop error."""
    data = {
        "entities": [
            {"id": "a", "type": "attraction", "name": "A", "summary": "A", "area": "vinh-long", "coordinates": [10.25, 106.0]},
            {"id": "b", "type": "attraction", "name": "B", "summary": "B", "area": "vinh-long", "coordinates": [10.26, 106.01]},
        ],
        "relationships": [
            {"from": "a", "to": "b", "type": "related_to"},
        ],
        "itineraries": [],
    }

    issues, _stats = validate_data.validate(data, tmp_path / "data.json")

    assert "self_loop_relationships" not in {issue.code for issue in issues}


def test_validate_flags_dangling_itinerary_stops(tmp_path: Path) -> None:
    """Itinerary stops referencing non-existent entities should be flagged."""
    data = {
        "entities": [
            {"id": "a", "type": "attraction", "name": "A", "summary": "A", "area": "vinh-long", "coordinates": [10.25, 106.0]},
        ],
        "relationships": [],
        "itineraries": [
            {"id": "it-1", "name": "Test", "stops": [
                {"entityId": "a"},
                {"entityId": "nonexistent-entity"},
            ]},
        ],
    }

    issues, _stats = validate_data.validate(data, tmp_path / "data.json")

    assert "dangling_itinerary_stops" in {issue.code for issue in issues}


def test_validate_no_dangling_when_stops_valid(tmp_path: Path) -> None:
    """Itinerary stops referencing existing entities should not be flagged."""
    data = {
        "entities": [
            {"id": "a", "type": "attraction", "name": "A", "summary": "A", "area": "vinh-long", "coordinates": [10.25, 106.0]},
        ],
        "relationships": [],
        "itineraries": [
            {"id": "it-1", "name": "Test", "stops": [{"entityId": "a"}]},
        ],
    }

    issues, _stats = validate_data.validate(data, tmp_path / "data.json")

    assert "dangling_itinerary_stops" not in {issue.code for issue in issues}


def test_validate_ignores_stops_without_entity_ref(tmp_path: Path) -> None:
    """Free-text stops (no entityId/id) should not trigger dangling error."""
    data = {
        "entities": [],
        "relationships": [],
        "itineraries": [
            {"id": "it-1", "name": "Test", "stops": [
                {"name": "Free text stop"},
            ]},
        ],
    }

    issues, _stats = validate_data.validate(data, tmp_path / "data.json")

    assert "dangling_itinerary_stops" not in {issue.code for issue in issues}
