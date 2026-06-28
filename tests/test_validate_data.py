from __future__ import annotations

import importlib.util
import json
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


# ── normalized_coordinates() ──────────────────────────────────────────────


def test_normalized_coordinates_list() -> None:
    assert validate_data.normalized_coordinates([10.25, 106.0]) == [10.25, 106.0]


def test_normalized_coordinates_dict_lat_lng() -> None:
    assert validate_data.normalized_coordinates({"lat": 10.25, "lng": 106.0}) == [10.25, 106.0]


def test_normalized_coordinates_dict_latitude_longitude() -> None:
    assert validate_data.normalized_coordinates({"latitude": 10.25, "longitude": 106.0}) == [10.25, 106.0]


def test_normalized_coordinates_json_string() -> None:
    assert validate_data.normalized_coordinates("[10.25, 106.0]") == [10.25, 106.0]


def test_normalized_coordinates_double_encoded() -> None:
    assert validate_data.normalized_coordinates('"[10.25, 106.0]"') == [10.25, 106.0]


def test_normalized_coordinates_transposed() -> None:
    result = validate_data.normalized_coordinates([106.0, 10.25])
    assert result == [10.25, 106.0]


def test_normalized_coordinates_invalid() -> None:
    assert validate_data.normalized_coordinates(None) is None
    assert validate_data.normalized_coordinates("not json") is None
    assert validate_data.normalized_coordinates([1, 2, 3]) is None
    assert validate_data.normalized_coordinates(42) is None
    assert validate_data.normalized_coordinates(["a", "b"]) is None


# ── haversine_km() ────────────────────────────────────────────────────────


def test_haversine_km_same_point() -> None:
    result = validate_data.haversine_km([10.25, 106.0], [10.25, 106.0])
    assert result is not None
    assert abs(result) < 0.001


def test_haversine_km_known_distance() -> None:
    result = validate_data.haversine_km([10.25, 106.0], [10.35, 106.1])
    assert result is not None
    assert 10 < result < 20


def test_haversine_km_none_inputs() -> None:
    assert validate_data.haversine_km(None, [10.25, 106.0]) is None
    assert validate_data.haversine_km([10.25, 106.0], None) is None


# ── _parse_json_string() ─────────────────────────────────────────────────


def test_parse_json_string_passthrough() -> None:
    assert validate_data._parse_json_string([10, 20]) == [10, 20]
    assert validate_data._parse_json_string(42) == 42


def test_parse_json_string_single_encoded() -> None:
    assert validate_data._parse_json_string("[10, 20]") == [10, 20]


def test_parse_json_string_double_encoded() -> None:
    assert validate_data._parse_json_string('"[10, 20]"') == [10, 20]


def test_parse_json_string_empty() -> None:
    assert validate_data._parse_json_string("") is None
    assert validate_data._parse_json_string("   ") is None


def test_parse_json_string_non_json() -> None:
    assert validate_data._parse_json_string("hello world") == "hello world"


# ── Boilerplate summary detection ─────────────────────────────────────────


def test_validate_flags_boilerplate_summary(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "a", "type": "attraction", "name": "A", "summary": "Không có đủ thông tin để mô tả", "area": "vinh-long"},
            {"id": "b", "type": "attraction", "name": "B", "summary": "404 Not Found", "area": "vinh-long"},
        ],
        "relationships": [],
        "itineraries": [],
    }

    issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["boilerplate_summary"] == 2
    assert "boilerplate_summary" in {issue.code for issue in issues}


# ── Season integrity ─────────────────────────────────────────────────────


def test_validate_flags_bad_season_months(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "a", "type": "product", "name": "A", "summary": "A", "area": "vinh-long",
             "season": {"months": [1, 13], "peak": [1]}},
        ],
        "relationships": [],
        "itineraries": [],
    }

    issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["season_integrity_errors"] == 1
    assert "season_integrity" in {issue.code for issue in issues}


def test_validate_flags_peak_not_subset_of_months(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "a", "type": "product", "name": "A", "summary": "A", "area": "vinh-long",
             "season": {"months": [1, 2, 3], "peak": [5]}},
        ],
        "relationships": [],
        "itineraries": [],
    }

    issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["season_integrity_errors"] == 1


def test_validate_valid_season_passes(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "a", "type": "product", "name": "A", "summary": "A", "area": "vinh-long",
             "season": {"months": [10, 11, 12], "peak": [11]}},
        ],
        "relationships": [],
        "itineraries": [],
    }

    issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["season_integrity_errors"] == 0


# ── source_not_list ──────────────────────────────────────────────────────


def test_validate_flags_source_not_list(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "a", "type": "attraction", "name": "A", "summary": "A", "area": "vinh-long",
             "source": "just-a-string"},
        ],
        "relationships": [],
        "itineraries": [],
    }

    issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["source_not_list"] == 1
    assert "source_not_list" in {issue.code for issue in issues}


# ── Level name/id mismatch ────────────────────────────────────────────────


def test_validate_flags_level_name_mismatch(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "p-test", "type": "place", "name": "Phường Test", "summary": "T", "level": "xa",
             "area": "vinh-long", "coordinates": [10.25, 106.0]},
        ],
        "relationships": [],
        "itineraries": [],
    }

    issues, _stats = validate_data.validate(data, tmp_path / "data.json")
    codes = {issue.code for issue in issues}

    assert "level_name_mismatch" in codes


def test_validate_flags_near_asymmetric(tmp_path: Path) -> None:
    """One-way near relationships should be flagged."""
    data = {
        "entities": [
            {"id": "a", "type": "attraction", "name": "A", "summary": "A", "area": "vinh-long", "coordinates": [10.25, 106.0]},
            {"id": "b", "type": "attraction", "name": "B", "summary": "B", "area": "vinh-long", "coordinates": [10.26, 106.01]},
        ],
        "relationships": [
            {"from": "a", "to": "b", "type": "near"},
        ],
        "itineraries": [],
    }

    issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["near_asymmetric"] == 1
    assert "near_asymmetric" in {issue.code for issue in issues}


def test_validate_no_near_asymmetric_when_reciprocal(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "a", "type": "attraction", "name": "A", "summary": "A", "area": "vinh-long", "coordinates": [10.25, 106.0]},
            {"id": "b", "type": "attraction", "name": "B", "summary": "B", "area": "vinh-long", "coordinates": [10.26, 106.01]},
        ],
        "relationships": [
            {"from": "a", "to": "b", "type": "near"},
            {"from": "b", "to": "a", "type": "near"},
        ],
        "itineraries": [],
    }

    issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["near_asymmetric"] == 0


def test_validate_flags_coordinate_clusters(tmp_path: Path) -> None:
    """Multiple entities sharing exact same coordinates should be flagged."""
    data = {
        "entities": [
            {"id": "a", "type": "attraction", "name": "A", "summary": "A", "area": "vinh-long", "coordinates": [10.25, 106.0]},
            {"id": "b", "type": "restaurant", "name": "B", "summary": "B", "area": "vinh-long", "coordinates": [10.25, 106.0]},
            {"id": "c", "type": "dish", "name": "C", "summary": "C", "area": "vinh-long", "coordinates": [10.30, 106.1]},
        ],
        "relationships": [],
        "itineraries": [],
    }

    issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["coordinate_clusters"] == 1
    assert stats["coordinate_clustered_entities"] == 2
    assert "coordinate_clusters" in {issue.code for issue in issues}


def test_validate_no_coord_clusters_when_unique(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "a", "type": "attraction", "name": "A", "summary": "A", "area": "vinh-long", "coordinates": [10.25, 106.0]},
            {"id": "b", "type": "attraction", "name": "B", "summary": "B", "area": "vinh-long", "coordinates": [10.26, 106.01]},
        ],
        "relationships": [],
        "itineraries": [],
    }

    issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["coordinate_clusters"] == 0


def test_validate_flags_level_id_mismatch(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "xa-test", "type": "place", "name": "Phường Test", "summary": "T", "level": "phuong",
             "area": "vinh-long", "coordinates": [10.25, 106.0]},
        ],
        "relationships": [],
        "itineraries": [],
    }

    issues, _stats = validate_data.validate(data, tmp_path / "data.json")
    codes = {issue.code for issue in issues}

    assert "level_id_mismatch" in codes


# ── Timestamp inversions (DI-008) ────────────────────────────────────────


def test_validate_flags_timestamp_inversions(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "a", "type": "attraction", "name": "A", "summary": "A", "area": "vinh-long",
             "coordinates": [10.25, 106.0], "updatedAt": "2026-06-20", "created_at": "2026-06-22"},
        ],
        "relationships": [],
        "itineraries": [],
    }

    issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["timestamp_inversions"] == 1
    assert "timestamp_inversions" in {issue.code for issue in issues}


def test_validate_no_timestamp_inversion_when_correct(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "a", "type": "attraction", "name": "A", "summary": "A", "area": "vinh-long",
             "coordinates": [10.25, 106.0], "updatedAt": "2026-06-25", "created_at": "2026-06-20"},
        ],
        "relationships": [],
        "itineraries": [],
    }

    _issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["timestamp_inversions"] == 0


# ── Image coverage (DI-009) ──────────────────────────────────────────────


def test_validate_image_coverage_stat(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "a", "type": "attraction", "name": "A", "summary": "A", "area": "vinh-long",
             "coordinates": [10.25, 106.0], "images": ["https://example.com/a.jpg"]},
            {"id": "b", "type": "dish", "name": "B", "summary": "B", "area": "vinh-long",
             "coordinates": [10.26, 106.01]},
        ],
        "relationships": [],
        "itineraries": [],
    }

    _issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["image_coverage_pct"] == 50.0


def test_validate_image_coverage_zero(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "a", "type": "attraction", "name": "A", "summary": "A", "area": "vinh-long",
             "coordinates": [10.25, 106.0]},
        ],
        "relationships": [],
        "itineraries": [],
    }

    _issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["image_coverage_pct"] == 0.0


# ── Summary quality (DI-010) ─────────────────────────────────────────────


def test_validate_flags_summary_short(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "a", "type": "attraction", "name": "A", "summary": "Quá ngắn", "area": "vinh-long"},
        ],
        "relationships": [],
        "itineraries": [],
    }

    issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["summary_short"] == 1
    assert "summary_short" in {issue.code for issue in issues}


def test_validate_flags_summary_long(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "a", "type": "attraction", "name": "A", "summary": "x" * 501, "area": "vinh-long"},
        ],
        "relationships": [],
        "itineraries": [],
    }

    issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["summary_long"] == 1
    assert "summary_long" in {issue.code for issue in issues}


def test_validate_summary_optimal_not_flagged(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "a", "type": "attraction", "name": "A",
             "summary": "Mô tả đủ dài cho SEO, có nội dung hữu ích cho người đọc và tìm kiếm.", "area": "vinh-long"},
        ],
        "relationships": [],
        "itineraries": [],
    }

    _issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["summary_short"] == 0
    assert stats["summary_long"] == 0


# ── Itinerary-stop area mismatch (DI-012) ────────────────────────────────


def test_validate_flags_itinerary_area_mismatch(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "stop-bt", "type": "attraction", "name": "Stop BT", "summary": "S",
             "area": "ben-tre", "coordinates": [10.25, 106.0]},
        ],
        "relationships": [],
        "itineraries": [
            {"id": "it-vl", "area": "vinh-long", "stops": [{"entityId": "stop-bt"}]},
        ],
    }

    issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["itinerary_area_mismatches"] == 1
    assert "itinerary_area_mismatch" in {issue.code for issue in issues}


def test_validate_no_itinerary_area_mismatch_when_matching(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "stop-vl", "type": "attraction", "name": "Stop VL", "summary": "S",
             "area": "vinh-long", "coordinates": [10.25, 106.0]},
        ],
        "relationships": [],
        "itineraries": [
            {"id": "it-vl", "area": "vinh-long", "stops": [{"entityId": "stop-vl"}]},
        ],
    }

    _issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["itinerary_area_mismatches"] == 0


# ── Relationship type singletons (DI-013) ────────────────────────────────


def test_validate_flags_rel_type_singletons(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "a", "type": "product", "name": "A", "summary": "A", "area": "vinh-long", "coordinates": [10.25, 106.0]},
            {"id": "b", "type": "organization", "name": "B", "summary": "B", "area": "vinh-long", "coordinates": [10.26, 106.01]},
        ],
        "relationships": [
            {"from": "a", "to": "b", "type": "supplies_to"},
        ],
        "itineraries": [],
    }

    issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["rel_type_singletons"] >= 1
    assert "rel_type_singletons" in {issue.code for issue in issues}


def test_validate_no_rel_singletons_with_common_types(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "a", "type": "attraction", "name": "A", "summary": "A", "area": "vinh-long", "coordinates": [10.25, 106.0]},
            {"id": "b", "type": "attraction", "name": "B", "summary": "B", "area": "vinh-long", "coordinates": [10.26, 106.01]},
            {"id": "c", "type": "attraction", "name": "C", "summary": "C", "area": "vinh-long", "coordinates": [10.27, 106.02]},
            {"id": "d", "type": "attraction", "name": "D", "summary": "D", "area": "vinh-long", "coordinates": [10.28, 106.03]},
        ],
        "relationships": [
            {"from": "a", "to": "b", "type": "near"},
            {"from": "c", "to": "d", "type": "near"},
        ],
        "itineraries": [],
    }

    _issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["rel_type_singletons"] == 0


# ── _load_json error handling ────────────────────────────────────────────


def test_load_json_raises_on_non_object(tmp_path: Path) -> None:
    import pytest
    f = tmp_path / "bad.json"
    f.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(ValueError, match="must contain a JSON object"):
        validate_data._load_json(f)


# ── Duplicate relationships warning ──────────────────────────────────────


def test_validate_flags_duplicate_relationships(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "a", "type": "attraction", "name": "A", "summary": "A", "area": "vinh-long", "coordinates": [10.25, 106.0]},
            {"id": "b", "type": "attraction", "name": "B", "summary": "B", "area": "vinh-long", "coordinates": [10.26, 106.01]},
        ],
        "relationships": [
            {"from": "a", "to": "b", "type": "related_to"},
            {"from": "a", "to": "b", "type": "related_to"},
        ],
        "itineraries": [],
    }

    issues, _stats = validate_data.validate(data, tmp_path / "data.json")

    assert "duplicate_relationships" in {issue.code for issue in issues}


# ── Entity id=0 edge case (falsy but valid) ──────────────────────────────


def test_validate_entity_id_zero_not_counted_as_missing(tmp_path: Path) -> None:
    """id=0 is falsy but valid — should not be counted as missing."""
    data = {
        "entities": [
            {"id": 0, "type": "attraction", "name": "Zero", "summary": "Z", "area": "vinh-long"},
        ],
        "relationships": [],
        "itineraries": [],
    }

    issues, stats = validate_data.validate(data, tmp_path / "data.json")
    codes = {issue.code for issue in issues}

    assert "missing_entity_id" not in codes


# ── SEO attribute coverage (DI-014) ──────────────────────────────────────


def test_validate_seo_attr_coverage(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "r1", "type": "restaurant", "name": "R1", "summary": "R", "area": "vinh-long",
             "attributes": {"specialty": "Hải sản", "phone": "123"}},
            {"id": "r2", "type": "restaurant", "name": "R2", "summary": "R", "area": "vinh-long",
             "attributes": {}},
        ],
        "relationships": [],
        "itineraries": [],
    }

    _issues, stats = validate_data.validate(data, tmp_path / "data.json")

    cov = stats["seo_attr_coverage"]
    assert "restaurant" in cov
    assert cov["restaurant"]["total"] == 2
    assert cov["restaurant"]["has_any_seo_attr"] == 1


def test_validate_seo_attr_coverage_per_attr(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "r1", "type": "restaurant", "name": "R1", "summary": "R", "area": "vinh-long",
             "attributes": {"specialty": "Hải sản", "phone": "0909123456"}},
            {"id": "r2", "type": "restaurant", "name": "R2", "summary": "R", "area": "vinh-long",
             "attributes": {"phone": "0909123457"}},
        ],
        "relationships": [],
        "itineraries": [],
    }

    _issues, stats = validate_data.validate(data, tmp_path / "data.json")

    cov = stats["seo_attr_coverage"]["restaurant"]
    assert cov["per_attr"]["specialty"] == 1
    assert cov["per_attr"]["phone"] == 2


def test_validate_entities_by_area(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "a", "type": "attraction", "name": "A", "area": "vinh-long"},
            {"id": "b", "type": "dish", "name": "B", "area": "vinh-long"},
            {"id": "c", "type": "product", "name": "C", "area": "ben-tre"},
            {"id": "d", "type": "event", "name": "D"},
        ],
        "relationships": [],
        "itineraries": [],
    }

    _issues, stats = validate_data.validate(data, tmp_path / "data.json")

    by_area = stats["entities_by_area"]
    assert by_area["vinh-long"] == 2
    assert by_area["ben-tre"] == 1
    assert by_area["(none)"] == 1


def test_validate_seo_attr_coverage_skips_uncovered_types(tmp_path: Path) -> None:
    """Types not in the seo_required mapping should not appear in coverage."""
    data = {
        "entities": [
            {"id": "o1", "type": "organization", "name": "Org", "summary": "O", "area": "vinh-long"},
        ],
        "relationships": [],
        "itineraries": [],
    }

    _issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert "organization" not in stats["seo_attr_coverage"]


# ── Name length anomalies (DI-015) ───────────────────────────────────────


def test_validate_flags_name_too_short(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "a", "type": "attraction", "name": "X", "summary": "A", "area": "vinh-long"},
        ],
        "relationships": [],
        "itineraries": [],
    }

    issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["name_too_short"] == 1
    assert "name_too_short" in {issue.code for issue in issues}


def test_validate_flags_name_too_long(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "a", "type": "attraction", "name": "A" * 101, "summary": "A", "area": "vinh-long"},
        ],
        "relationships": [],
        "itineraries": [],
    }

    issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["name_too_long"] == 1
    assert "name_too_long" in {issue.code for issue in issues}


def test_validate_name_normal_length_not_flagged(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "a", "type": "attraction", "name": "Vườn trái cây Ba Vì", "summary": "A", "area": "vinh-long"},
        ],
        "relationships": [],
        "itineraries": [],
    }

    _issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["name_too_short"] == 0
    assert stats["name_too_long"] == 0


# ── Itinerary stops sanity (DI-016) ──────────────────────────────────────


def test_validate_flags_itinerary_empty_stops(tmp_path: Path) -> None:
    data = {
        "entities": [],
        "relationships": [],
        "itineraries": [
            {"id": "it-1", "title": "Empty", "stops": []},
        ],
    }

    issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["itinerary_empty_stops"] == 1
    assert "itinerary_empty_stops" in {issue.code for issue in issues}


def test_validate_flags_itinerary_excessive_stops(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": f"s-{i}", "type": "attraction", "name": f"S{i}", "summary": "S", "area": "vinh-long"}
            for i in range(25)
        ],
        "relationships": [],
        "itineraries": [
            {"id": "it-big", "title": "Big", "stops": [{"entityId": f"s-{i}"} for i in range(25)]},
        ],
    }

    issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["itinerary_excessive_stops"] == 1
    assert "itinerary_excessive_stops" in {issue.code for issue in issues}


# ── Entity quality score (DI-017) ───────────────────────────────────────


def test_quality_score_perfect_entity() -> None:
    entity = {
        "id": "a", "type": "restaurant", "name": "Nhà hàng Test",
        "summary": "Mô tả đủ dài cho SEO, có nội dung hữu ích cho người đọc.",
        "coordinates": [10.25, 106.0], "area": "vinh-long", "placeId": "xa-1",
        "source": [{"url": "https://example.com"}],
        "images": ["https://example.com/img.jpg"],
        "confidence": 0.9,
        "attributes": {"specialty": "Hải sản"},
    }
    score = validate_data.entity_quality_score(entity)
    assert score == 100


def test_quality_score_empty_entity() -> None:
    entity = {"id": "b", "type": "restaurant", "name": "Bad"}
    score = validate_data.entity_quality_score(entity)
    assert score <= 30


def test_quality_score_boilerplate_summary() -> None:
    entity = {
        "id": "c", "type": "attraction", "name": "C",
        "summary": "Không có đủ thông tin",
        "coordinates": [10.25, 106.0], "area": "vinh-long",
        "source": [{"url": "https://example.com"}],
        "images": ["https://example.com/img.jpg"],
    }
    score = validate_data.entity_quality_score(entity)
    assert score < 100
    full = {**entity, "summary": "Mô tả tốt đẹp cho SEO và nội dung hữu ích."}
    assert validate_data.entity_quality_score(full) > score


def test_quality_score_place_not_penalized_for_place_id() -> None:
    """Place entities should NOT be penalized for missing placeId or area."""
    entity = {
        "id": "p", "type": "place", "name": "Xã Test",
        "summary": "Mô tả đủ dài cho SEO và nội dung hữu ích cho người đọc.",
        "coordinates": [10.25, 106.0],
        "source": [{"url": "https://example.com"}],
        "images": ["https://example.com/img.jpg"],
    }
    score = validate_data.entity_quality_score(entity)
    assert score == 100


def test_quality_score_low_confidence_penalty() -> None:
    base = {
        "id": "d", "type": "attraction", "name": "D",
        "summary": "Mô tả đủ dài cho SEO và nội dung hữu ích cho người đọc.",
        "coordinates": [10.25, 106.0], "area": "vinh-long", "placeId": "xa-1",
        "source": [{"url": "https://example.com"}],
        "images": ["https://example.com/img.jpg"],
    }
    high = {**base, "confidence": 0.9}
    low = {**base, "confidence": 0.3}
    assert validate_data.entity_quality_score(high) > validate_data.entity_quality_score(low)


def test_quality_score_timestamp_inversion_penalty() -> None:
    base = {
        "id": "e", "type": "attraction", "name": "E",
        "summary": "Mô tả đủ dài cho SEO và nội dung hữu ích cho người đọc.",
        "coordinates": [10.25, 106.0], "area": "vinh-long", "placeId": "xa-1",
        "source": [{"url": "https://example.com"}],
        "images": ["https://example.com/img.jpg"],
    }
    ok = {**base, "updatedAt": "2026-06-25", "created_at": "2026-06-20"}
    bad = {**base, "updatedAt": "2026-06-20", "created_at": "2026-06-25"}
    assert validate_data.entity_quality_score(ok) > validate_data.entity_quality_score(bad)


def test_validate_reports_quality_score_distribution(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "good", "type": "attraction", "name": "Good",
             "summary": "Mô tả đủ dài cho SEO nội dung hữu ích cho người đọc tìm kiếm.",
             "coordinates": [10.25, 106.0], "area": "vinh-long", "placeId": "xa-1",
             "source": [{"url": "https://example.com"}],
             "images": ["https://example.com/img.jpg"]},
            {"id": "bad", "type": "restaurant", "name": "Bad"},
        ],
        "relationships": [],
        "itineraries": [],
    }

    _issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert "quality_score_avg" in stats
    assert isinstance(stats["quality_score_avg"], float)
    dist = stats["quality_score_distribution"]
    assert dist["good_80_100"] >= 1
    assert dist["critical_0_29"] + dist["needs_work_30_59"] >= 1


# ── Graph connectivity (DI-018) ────────────────────────────────────────


def test_graph_connectivity_single_component() -> None:
    entities = [
        {"id": "a", "type": "attraction"},
        {"id": "b", "type": "dish"},
        {"id": "c", "type": "product"},
    ]
    relationships = [
        {"from": "a", "to": "b", "type": "near"},
        {"from": "b", "to": "c", "type": "related_to"},
    ]
    gc = validate_data.graph_connectivity(entities, relationships)
    assert gc["total_components"] == 1
    assert gc["largest_component"] == 3
    assert gc["isolated_entities"] == 0


def test_graph_connectivity_isolated_nodes() -> None:
    entities = [
        {"id": "a", "type": "attraction"},
        {"id": "b", "type": "dish"},
        {"id": "c", "type": "product"},
    ]
    relationships = [
        {"from": "a", "to": "b", "type": "near"},
    ]
    gc = validate_data.graph_connectivity(entities, relationships)
    assert gc["total_components"] == 2
    assert gc["largest_component"] == 2
    assert gc["isolated_entities"] == 1


def test_graph_connectivity_all_isolated() -> None:
    entities = [
        {"id": "a", "type": "attraction"},
        {"id": "b", "type": "dish"},
    ]
    gc = validate_data.graph_connectivity(entities, [])
    assert gc["total_components"] == 2
    assert gc["isolated_entities"] == 2


def test_graph_connectivity_empty() -> None:
    gc = validate_data.graph_connectivity([], [])
    assert gc["total_components"] == 0
    assert gc["largest_component"] == 0
    assert gc["isolated_entities"] == 0


def test_graph_connectivity_ignores_broken_refs() -> None:
    entities = [{"id": "a", "type": "attraction"}]
    relationships = [{"from": "a", "to": "nonexistent", "type": "near"}]
    gc = validate_data.graph_connectivity(entities, relationships)
    assert gc["total_components"] == 1
    assert gc["isolated_entities"] == 1


def test_validate_includes_graph_connectivity(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "a", "type": "attraction", "name": "A", "summary": "A", "area": "vinh-long",
             "coordinates": [10.25, 106.0]},
            {"id": "b", "type": "dish", "name": "B", "summary": "B", "area": "vinh-long",
             "coordinates": [10.26, 106.01]},
        ],
        "relationships": [{"from": "a", "to": "b", "type": "near"}],
        "itineraries": [],
    }

    _issues, stats = validate_data.validate(data, tmp_path / "data.json")

    gc = stats["graph_connectivity"]
    assert gc["total_components"] >= 1
    assert gc["largest_component"] >= 2


def test_validate_itinerary_normal_stops_not_flagged(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "s-1", "type": "attraction", "name": "S1", "summary": "S", "area": "vinh-long"},
        ],
        "relationships": [],
        "itineraries": [
            {"id": "it-ok", "title": "OK", "stops": [{"entityId": "s-1"}]},
        ],
    }

    _issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["itinerary_empty_stops"] == 0
    assert stats["itinerary_excessive_stops"] == 0


# ── Source URL validation (DI-019) ──────────────────────────────────────


def test_validate_flags_invalid_source_urls(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "a", "type": "attraction", "name": "A", "summary": "A", "area": "vinh-long",
             "source": [{"url": "ftp://bad.com/file"}]},
        ],
        "relationships": [],
        "itineraries": [],
    }

    issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["invalid_source_urls"] == 1
    assert "invalid_source_urls" in {issue.code for issue in issues}


def test_validate_valid_source_urls_not_flagged(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "a", "type": "attraction", "name": "A", "summary": "A", "area": "vinh-long",
             "source": [{"url": "https://example.com/page"}]},
        ],
        "relationships": [],
        "itineraries": [],
    }

    _issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["invalid_source_urls"] == 0


def test_validate_source_url_string_in_list(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "a", "type": "attraction", "name": "A", "summary": "A", "area": "vinh-long",
             "source": ["javascript:alert(1)"]},
        ],
        "relationships": [],
        "itineraries": [],
    }

    issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["invalid_source_urls"] == 1


# ── Phone format validation (DI-020) ───────────────────────────────────


def test_validate_flags_invalid_phone_format(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "a", "type": "restaurant", "name": "A", "summary": "A", "area": "vinh-long",
             "attributes": {"phone": "abc-not-a-phone"}},
        ],
        "relationships": [],
        "itineraries": [],
    }

    issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["invalid_phone_format"] == 1
    assert "invalid_phone_format" in {issue.code for issue in issues}


def test_validate_valid_vn_phone_not_flagged(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "a", "type": "restaurant", "name": "A", "summary": "A", "area": "vinh-long",
             "attributes": {"phone": "0270 3822 456"}},
            {"id": "b", "type": "restaurant", "name": "B", "summary": "B", "area": "vinh-long",
             "attributes": {"phone": "+84 909 123 456"}},
        ],
        "relationships": [],
        "itineraries": [],
    }

    _issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["invalid_phone_format"] == 0


def test_vn_phone_regex_patterns() -> None:
    """Direct test of the VN phone regex."""
    assert validate_data.VN_PHONE.match("0909123456")
    assert validate_data.VN_PHONE.match("+84909123456")
    assert validate_data.VN_PHONE.match("02703822456")
    assert validate_data.VN_PHONE.match("18006821")
    assert validate_data.VN_PHONE.match("1800545413")
    assert validate_data.VN_PHONE.match("19009247")
    assert validate_data.VN_PHONE.match("115")
    assert validate_data.VN_PHONE.match("113")
    assert not validate_data.VN_PHONE.match("12345")
    assert not validate_data.VN_PHONE.match("abc")


# ── CLI main() ──────────────────────────────────────────────────────────


def test_main_returns_zero_on_clean_data(tmp_path: Path, monkeypatch: "pytest.MonkeyPatch") -> None:
    import pytest  # noqa: F811
    data = {"entities": [], "relationships": [], "itineraries": []}
    f = tmp_path / "data.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["validate_data", "--data", str(f)])
    assert validate_data.main() == 0


def test_main_returns_one_on_errors(tmp_path: Path, monkeypatch: "pytest.MonkeyPatch") -> None:
    import pytest  # noqa: F811
    data = {
        "entities": [{"type": "attraction", "name": "Test"}],
        "relationships": [],
        "itineraries": [],
    }
    f = tmp_path / "data.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["validate_data", "--data", str(f)])
    assert validate_data.main() == 1


def test_main_json_output(tmp_path: Path, monkeypatch: "pytest.MonkeyPatch", capsys: "pytest.CaptureFixture[str]") -> None:
    import pytest  # noqa: F811
    data = {"entities": [], "relationships": [], "itineraries": []}
    f = tmp_path / "data.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["validate_data", "--data", str(f), "--json"])
    validate_data.main()
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert "stats" in parsed
    assert "issues" in parsed


def test_main_warnings_as_errors(tmp_path: Path, monkeypatch: "pytest.MonkeyPatch") -> None:
    import pytest  # noqa: F811
    data = {
        "entities": [
            {"id": "a", "type": "attraction", "name": "A"},
        ],
        "relationships": [],
        "itineraries": [],
    }
    f = tmp_path / "data.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["validate_data", "--data", str(f), "--warnings-as-errors"])
    assert validate_data.main() == 1


# ── print_report coverage ──────────────────────────────────────────────


def test_print_report_runs_without_error(tmp_path: Path, capsys: "pytest.CaptureFixture[str]") -> None:
    import pytest  # noqa: F811
    data = {
        "entities": [
            {"id": "a", "type": "restaurant", "name": "A", "summary": "A test restaurant",
             "area": "vinh-long", "coordinates": [10.25, 106.0],
             "attributes": {"specialty": "Hải sản"}},
        ],
        "relationships": [],
        "itineraries": [],
    }
    issues, stats = validate_data.validate(data, tmp_path / "data.json")
    validate_data.print_report(issues, stats)
    out = capsys.readouterr().out
    assert "VinhLong360 data validation" in out
    assert "Entity quality score" in out
    assert "Graph connectivity" in out


# ── SEO_REQUIRED constant ──────────────────────────────────────────────


def test_seo_required_covers_main_types() -> None:
    """SEO_REQUIRED should cover the most important entity types."""
    assert "restaurant" in validate_data.SEO_REQUIRED
    assert "product" in validate_data.SEO_REQUIRED
    assert "event" in validate_data.SEO_REQUIRED
    assert "accommodation" in validate_data.SEO_REQUIRED
    assert "place" not in validate_data.SEO_REQUIRED


# ── Orphan entities (DI-021) ───────────────────────────────────────────


def test_validate_flags_orphan_entities(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "connected", "type": "attraction", "name": "C", "summary": "C", "area": "vinh-long",
             "coordinates": [10.25, 106.0]},
            {"id": "orphan", "type": "dish", "name": "O", "summary": "O", "area": "vinh-long",
             "coordinates": [10.26, 106.01]},
        ],
        "relationships": [{"from": "connected", "to": "connected", "type": "near"}],
        "itineraries": [],
    }

    issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["orphan_entities"] >= 1
    assert "orphan_entities" in {issue.code for issue in issues}


def test_validate_no_orphans_when_all_connected(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "a", "type": "attraction", "name": "A", "summary": "A", "area": "vinh-long",
             "coordinates": [10.25, 106.0]},
            {"id": "b", "type": "dish", "name": "B", "summary": "B", "area": "vinh-long",
             "coordinates": [10.26, 106.01]},
        ],
        "relationships": [{"from": "a", "to": "b", "type": "near"}],
        "itineraries": [],
    }

    _issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["orphan_entities"] == 0


def test_validate_itinerary_stop_counts_as_reference(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "stop-ref", "type": "attraction", "name": "S", "summary": "S", "area": "vinh-long",
             "coordinates": [10.25, 106.0]},
        ],
        "relationships": [],
        "itineraries": [
            {"id": "it-1", "title": "Trip", "stops": [{"entityId": "stop-ref"}]},
        ],
    }

    _issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["orphan_entities"] == 0


def test_validate_places_excluded_from_orphan_count(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "xa-1", "type": "place", "name": "Xã 1", "summary": "P", "area": "vinh-long",
             "coordinates": [10.25, 106.0]},
        ],
        "relationships": [],
        "itineraries": [],
    }

    _issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["orphan_entities"] == 0


# ── Website URL validation (DI-022) ────────────────────────────────────


def test_validate_flags_invalid_website_url(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "a", "type": "restaurant", "name": "A", "summary": "A", "area": "vinh-long",
             "attributes": {"website": "not-a-url"}},
        ],
        "relationships": [],
        "itineraries": [],
    }

    issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["invalid_website_urls"] == 1
    assert "invalid_website_urls" in {issue.code for issue in issues}


def test_validate_valid_website_not_flagged(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "a", "type": "restaurant", "name": "A", "summary": "A", "area": "vinh-long",
             "attributes": {"website": "https://example.com"}},
        ],
        "relationships": [],
        "itineraries": [],
    }

    _issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["invalid_website_urls"] == 0


# ── Unknown relationship types (DI-023) ────────────────────────────────


def test_validate_flags_unknown_rel_types(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "a", "type": "attraction", "name": "A", "summary": "A", "area": "vinh-long",
             "coordinates": [10.25, 106.0]},
            {"id": "b", "type": "dish", "name": "B", "summary": "B", "area": "vinh-long",
             "coordinates": [10.26, 106.01]},
        ],
        "relationships": [
            {"from": "a", "to": "b", "type": "invented_type"},
        ],
        "itineraries": [],
    }

    issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["unknown_rel_types"] >= 1
    assert "unknown_rel_types" in {issue.code for issue in issues}


def test_validate_known_rel_types_not_flagged(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "a", "type": "attraction", "name": "A", "summary": "A", "area": "vinh-long",
             "coordinates": [10.25, 106.0]},
            {"id": "b", "type": "dish", "name": "B", "summary": "B", "area": "vinh-long",
             "coordinates": [10.26, 106.01]},
        ],
        "relationships": [
            {"from": "a", "to": "b", "type": "near"},
        ],
        "itineraries": [],
    }

    _issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["unknown_rel_types"] == 0


def test_known_rel_types_constant() -> None:
    """KNOWN_REL_TYPES should include all hierarchical types."""
    for t in validate_data.HIERARCHICAL_REL_TYPES:
        assert t in validate_data.KNOWN_REL_TYPES


# ── Entity ID format (DI-024) ────────────────────────────────────────


def test_validate_flags_entity_id_with_spaces(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "has space", "type": "attraction", "name": "A", "summary": "A", "area": "vinh-long"},
        ],
        "relationships": [],
        "itineraries": [],
    }

    issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["invalid_entity_ids"] == 1
    assert "invalid_entity_ids" in {issue.code for issue in issues}


def test_validate_flags_entity_id_with_control_chars(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "tab\there", "type": "attraction", "name": "A", "summary": "A", "area": "vinh-long"},
        ],
        "relationships": [],
        "itineraries": [],
    }

    issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["invalid_entity_ids"] == 1


def test_validate_flags_entity_id_too_long(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "x" * 201, "type": "attraction", "name": "A", "summary": "A", "area": "vinh-long"},
        ],
        "relationships": [],
        "itineraries": [],
    }

    issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["invalid_entity_ids"] == 1


def test_validate_valid_entity_id_not_flagged(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "cam-sanh-vinh-long", "type": "attraction", "name": "A", "summary": "A", "area": "vinh-long"},
        ],
        "relationships": [],
        "itineraries": [],
    }

    _issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["invalid_entity_ids"] == 0


# ── produced_in source type (DI-025) ─────────────────────────────────


def test_validate_flags_produced_in_source_type_error(tmp_path: Path) -> None:
    """produced_in source should be product/dish/drink/craft_village."""
    data = {
        "entities": [
            {"id": "att-src", "type": "attraction", "name": "A", "summary": "A", "area": "vinh-long",
             "coordinates": [10.25, 106.0]},
            {"id": "place-dst", "type": "place", "name": "P", "summary": "P", "area": "vinh-long",
             "coordinates": [10.26, 106.01]},
        ],
        "relationships": [
            {"from": "att-src", "to": "place-dst", "type": "produced_in"},
        ],
        "itineraries": [],
    }

    issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["produced_in_source_type_errors"] == 1
    assert "produced_in_source_type" in {issue.code for issue in issues}


def test_validate_produced_in_source_product_ok(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "prod-src", "type": "product", "name": "P", "summary": "P", "area": "vinh-long",
             "coordinates": [10.25, 106.0]},
            {"id": "place-dst", "type": "place", "name": "PL", "summary": "PL", "area": "vinh-long",
             "coordinates": [10.26, 106.01]},
        ],
        "relationships": [
            {"from": "prod-src", "to": "place-dst", "type": "produced_in"},
        ],
        "itineraries": [],
    }

    _issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["produced_in_source_type_errors"] == 0


# ── Confidence distribution ──────────────────────────────────────────


def test_validate_confidence_distribution(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "a", "type": "attraction", "name": "A", "summary": "A", "area": "vinh-long",
             "confidence": 0.3},
            {"id": "b", "type": "dish", "name": "B", "summary": "B", "area": "vinh-long",
             "confidence": 0.7},
            {"id": "c", "type": "product", "name": "C", "summary": "C", "area": "vinh-long",
             "confidence": 0.9},
        ],
        "relationships": [],
        "itineraries": [],
    }

    _issues, stats = validate_data.validate(data, tmp_path / "data.json")

    cd = stats["confidence_distribution"]
    assert cd["min"] == 0.3
    assert cd["max"] == 0.9
    assert cd["median"] == 0.7
    assert cd["count"] == 3


def test_validate_confidence_distribution_even_count(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "a", "type": "attraction", "name": "A", "summary": "A", "confidence": 0.4},
            {"id": "b", "type": "dish", "name": "B", "summary": "B", "confidence": 0.8},
        ],
        "relationships": [],
        "itineraries": [],
    }

    _issues, stats = validate_data.validate(data, tmp_path / "data.json")

    cd = stats["confidence_distribution"]
    assert cd["median"] == 0.6


def test_validate_no_confidence_distribution_without_values(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "a", "type": "attraction", "name": "A", "summary": "A"},
        ],
        "relationships": [],
        "itineraries": [],
    }

    _issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert "confidence_distribution" not in stats


# ── print_report with all new keys ───────────────────────────────────


def test_print_report_includes_new_keys(tmp_path: Path, capsys: "pytest.CaptureFixture[str]") -> None:
    import pytest  # noqa: F811
    data = {
        "entities": [
            {"id": "a", "type": "restaurant", "name": "A", "summary": "A test restaurant",
             "area": "vinh-long", "coordinates": [10.25, 106.0],
             "attributes": {"specialty": "Hải sản"}, "confidence": 0.8},
        ],
        "relationships": [],
        "itineraries": [],
    }
    issues, stats = validate_data.validate(data, tmp_path / "data.json")
    validate_data.print_report(issues, stats)
    out = capsys.readouterr().out
    assert "invalid_website_urls" in out
    assert "orphan_entities" in out
    assert "coords_without_address" in out
    assert "Confidence distribution" in out


# ── Duplicate name+type (DI-026) ─────────────────────────────────────


def test_validate_flags_duplicate_name_type(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "a1", "type": "attraction", "name": "Vườn trái cây", "summary": "A"},
            {"id": "a2", "type": "attraction", "name": "Vườn trái cây", "summary": "B"},
        ],
        "relationships": [],
        "itineraries": [],
    }

    issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["duplicate_name_type"] == 1
    assert "duplicate_name_type" in {issue.code for issue in issues}


def test_validate_same_name_different_type_ok(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "a1", "type": "attraction", "name": "Cam sành", "summary": "A"},
            {"id": "a2", "type": "product", "name": "Cam sành", "summary": "B"},
        ],
        "relationships": [],
        "itineraries": [],
    }

    _issues, stats = validate_data.validate(data, tmp_path / "data.json")

    assert stats["duplicate_name_type"] == 0


# ── Parameterized entity_quality_score ───────────────────────────────


import pytest


@pytest.mark.parametrize("entity,max_score", [
    ({"id": "a", "type": "attraction", "name": "A"}, 30),
    ({"id": "b", "type": "place", "name": "B", "summary": "Good summary for SEO",
      "coordinates": [10.25, 106.0], "source": [{"url": "https://x.com"}],
      "images": ["https://x.com/i.jpg"]}, 100),
    ({"id": "c", "type": "restaurant", "name": "C", "summary": "Không có đủ thông tin"}, 60),
])
def test_quality_score_parameterized(entity, max_score) -> None:
    score = validate_data.entity_quality_score(entity)
    assert score <= max_score


# ── Parameterized normalized_coordinates ─────────────────────────────


@pytest.mark.parametrize("input_val,expected", [
    ([10.25, 106.0], [10.25, 106.0]),
    ({"lat": 10.25, "lng": 106.0}, [10.25, 106.0]),
    ("[10.25, 106.0]", [10.25, 106.0]),
    ([106.0, 10.25], [10.25, 106.0]),
    (None, None),
    ("not json", None),
    ([1, 2, 3], None),
    (42, None),
])
def test_normalized_coordinates_parameterized(input_val, expected) -> None:
    assert validate_data.normalized_coordinates(input_val) == expected


@pytest.mark.parametrize("summary,expected_penalty", [
    ("", True),
    ("Quá ngắn", True),
    ("x" * 501, True),
    ("Mô tả đủ dài cho SEO và nội dung hữu ích cho người đọc.", False),
])
def test_quality_score_summary_penalties(summary, expected_penalty) -> None:
    base = {
        "id": "q", "type": "attraction", "name": "Q",
        "coordinates": [10.25, 106.0], "area": "vinh-long", "placeId": "xa-1",
        "source": [{"url": "https://x.com"}],
        "images": ["https://x.com/i.jpg"],
        "attributes": {"admission": "miễn phí"},
    }
    if summary:
        base["summary"] = summary
    score = validate_data.entity_quality_score(base)
    if expected_penalty:
        assert score < 100
    else:
        assert score == 100


def test_validate_flags_coords_without_address(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "no-addr", "type": "attraction", "name": "No Address",
             "coordinates": [10.25, 106.0], "attributes": {}},
        ],
        "relationships": [],
        "itineraries": [],
    }
    data_path = tmp_path / "data.json"
    data_path.write_text(json.dumps(data), encoding="utf-8")
    _, stats = validate_data.validate(data, data_path)
    assert stats["coords_without_address"] == 1


def test_validate_no_coords_without_address_when_has_address(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "has-addr", "type": "attraction", "name": "Has Address",
             "coordinates": [10.25, 106.0],
             "attributes": {"address": "123 Đường Trần Phú, Vĩnh Long"}},
        ],
        "relationships": [],
        "itineraries": [],
    }
    data_path = tmp_path / "data.json"
    data_path.write_text(json.dumps(data), encoding="utf-8")
    _, stats = validate_data.validate(data, data_path)
    assert stats["coords_without_address"] == 0


def test_validate_flags_duplicate_source_urls(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "a", "type": "attraction", "name": "A",
             "source": [{"url": "https://same.com/page"}]},
            {"id": "b", "type": "attraction", "name": "B",
             "source": [{"url": "https://same.com/page"}]},
        ],
        "relationships": [],
        "itineraries": [],
    }
    data_path = tmp_path / "data.json"
    data_path.write_text(json.dumps(data), encoding="utf-8")
    _, stats = validate_data.validate(data, data_path)
    assert stats["duplicate_source_urls"] == 1


def test_validate_no_duplicate_source_urls_when_unique(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "a", "type": "attraction", "name": "A",
             "source": [{"url": "https://a.com"}]},
            {"id": "b", "type": "attraction", "name": "B",
             "source": [{"url": "https://b.com"}]},
        ],
        "relationships": [],
        "itineraries": [],
    }
    data_path = tmp_path / "data.json"
    data_path.write_text(json.dumps(data), encoding="utf-8")
    _, stats = validate_data.validate(data, data_path)
    assert stats["duplicate_source_urls"] == 0


def test_seo_required_covers_craft_village_and_drink() -> None:
    assert "craft_village" in validate_data.SEO_REQUIRED
    assert "drink" in validate_data.SEO_REQUIRED
    assert "specialty" in validate_data.SEO_REQUIRED["craft_village"]
    assert "price_range" in validate_data.SEO_REQUIRED["drink"]


def test_validate_flags_truncated_summary(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "trunc", "type": "attraction", "name": "Trunc",
             "summary": "Beautiful place with many things to see and do in this area..."},
        ],
        "relationships": [],
        "itineraries": [],
    }
    data_path = tmp_path / "data.json"
    data_path.write_text(json.dumps(data), encoding="utf-8")
    _, stats = validate_data.validate(data, data_path)
    assert stats["summary_truncated"] == 1


def test_validate_no_truncated_summary_when_complete(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "full", "type": "attraction", "name": "Full",
             "summary": "Beautiful place with many things to see and do in this area, a complete sentence"},
        ],
        "relationships": [],
        "itineraries": [],
    }
    data_path = tmp_path / "data.json"
    data_path.write_text(json.dumps(data), encoding="utf-8")
    _, stats = validate_data.validate(data, data_path)
    assert stats["summary_truncated"] == 0


def test_validate_places_excluded_from_coords_without_address(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "p-test", "type": "place", "name": "Place",
             "coordinates": [10.25, 106.0], "attributes": {}},
        ],
        "relationships": [],
        "itineraries": [],
    }
    data_path = tmp_path / "data.json"
    data_path.write_text(json.dumps(data), encoding="utf-8")
    _, stats = validate_data.validate(data, data_path)
    assert stats["coords_without_address"] == 0


def test_validate_flags_unknown_entity_type(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "e1", "type": "totally_made_up", "name": "Bad", "summary": "x" * 60},
            {"id": "e2", "type": "attraction", "name": "Good", "summary": "x" * 60},
        ],
        "relationships": [],
        "itineraries": [],
    }
    issues, stats = validate_data.validate(data, tmp_path / "data.json")
    assert stats["unknown_entity_types"] == 1
    assert "unknown_entity_type" in {i.code for i in issues}


def test_validate_no_unknown_type_for_valid_types(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": f"e-{t}", "type": t, "name": t, "summary": "x" * 60}
            for t in ("attraction", "dish", "place", "person", "history", "cafe")
        ],
        "relationships": [],
        "itineraries": [],
    }
    issues, stats = validate_data.validate(data, tmp_path / "data.json")
    assert stats["unknown_entity_types"] == 0
    assert "unknown_entity_type" not in {i.code for i in issues}


def test_validate_short_summary_examples(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "e1", "type": "dish", "name": "Short", "summary": "Hi"},
            {"id": "e2", "type": "dish", "name": "Long enough", "summary": "x" * 60},
        ],
        "relationships": [],
        "itineraries": [],
    }
    _, stats = validate_data.validate(data, tmp_path / "data.json")
    examples = stats.get("short_summary_examples", [])
    assert any("e1" in ex for ex in examples)
    assert not any("e2" in ex for ex in examples)


def test_validate_dangling_rel_entity_ids(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "e1", "type": "attraction", "name": "A", "summary": "x" * 60},
        ],
        "relationships": [
            {"source_id": "e1", "target_id": "ghost", "rel_type": "near"},
        ],
        "itineraries": [],
    }
    issues, stats = validate_data.validate(data, tmp_path / "data.json")
    ids = stats.get("dangling_rel_entity_ids", [])
    assert "ghost" in ids
    assert any("broken_relationships" == i.code for i in issues)


# ── SEO_REQUIRED expanded keys (validator update 2026-06-28) ────────


@pytest.mark.parametrize("attr_key", [
    "price", "price_range", "ocop", "ocop_star", "ocop_certified", "brand",
])
def test_product_seo_any_key_passes(attr_key, tmp_path: Path) -> None:
    """Product with ANY one of the expanded SEO keys should pass the SEO check."""
    data = {
        "entities": [
            {"id": "p1", "type": "product", "name": "Sản phẩm", "summary": "Sản phẩm test",
             "area": "vinh-long", "attributes": {attr_key: "test-value"}},
        ],
        "relationships": [],
        "itineraries": [],
    }

    _issues, stats = validate_data.validate(data, tmp_path / "data.json")

    cov = stats["seo_attr_coverage"]["product"]
    assert cov["has_any_seo_attr"] == 1


def test_product_seo_fails_without_any_key(tmp_path: Path) -> None:
    """Product with none of the required keys should fail the SEO check."""
    data = {
        "entities": [
            {"id": "p1", "type": "product", "name": "Sản phẩm", "summary": "Sản phẩm test",
             "area": "vinh-long", "attributes": {"schema_type": "Product"}},
        ],
        "relationships": [],
        "itineraries": [],
    }

    _issues, stats = validate_data.validate(data, tmp_path / "data.json")

    cov = stats["seo_attr_coverage"]["product"]
    assert cov["has_any_seo_attr"] == 0


@pytest.mark.parametrize("attr_key", ["date_start", "startDate"])
def test_event_seo_both_date_keys(attr_key, tmp_path: Path) -> None:
    """Event with either date_start or startDate should pass."""
    data = {
        "entities": [
            {"id": "ev1", "type": "event", "name": "Lễ hội", "summary": "Lễ hội test",
             "area": "vinh-long", "attributes": {attr_key: "2026-01-15"}},
        ],
        "relationships": [],
        "itineraries": [],
    }

    _issues, stats = validate_data.validate(data, tmp_path / "data.json")

    cov = stats["seo_attr_coverage"]["event"]
    assert cov["has_any_seo_attr"] == 1


def test_drink_seo_coverage(tmp_path: Path) -> None:
    """Drink type should be tracked in SEO coverage."""
    data = {
        "entities": [
            {"id": "d1", "type": "drink", "name": "Nước dừa", "summary": "Thức uống",
             "area": "vinh-long", "attributes": {"specialty": "Nước dừa tươi"}},
            {"id": "d2", "type": "drink", "name": "Trà", "summary": "Thức uống",
             "area": "vinh-long", "attributes": {}},
        ],
        "relationships": [],
        "itineraries": [],
    }

    _issues, stats = validate_data.validate(data, tmp_path / "data.json")

    cov = stats["seo_attr_coverage"]["drink"]
    assert cov["total"] == 2
    assert cov["has_any_seo_attr"] == 1
    assert cov["per_attr"]["specialty"] == 1


def test_quality_score_product_ocop_star_not_penalized() -> None:
    """Product with ocop_star should get full SEO score (no -10 penalty)."""
    entity = {
        "id": "p", "type": "product", "name": "Cam sành Vĩnh Long",
        "summary": "Mô tả đủ dài cho SEO, có nội dung hữu ích cho người đọc.",
        "coordinates": [10.25, 106.0], "area": "vinh-long", "placeId": "xa-1",
        "source": [{"url": "https://example.com"}],
        "images": ["https://example.com/img.jpg"],
        "confidence": 0.9,
        "attributes": {"ocop_star": 4},
    }
    score = validate_data.entity_quality_score(entity)
    assert score == 100


def test_quality_score_product_brand_not_penalized() -> None:
    """Product with only brand attr should still pass SEO check."""
    entity = {
        "id": "p", "type": "product", "name": "Kẹo dừa Bến Tre",
        "summary": "Mô tả đủ dài cho SEO, có nội dung hữu ích cho người đọc.",
        "coordinates": [10.25, 106.0], "area": "ben-tre", "placeId": "xa-1",
        "source": [{"url": "https://example.com"}],
        "images": ["https://example.com/img.jpg"],
        "confidence": 0.9,
        "attributes": {"brand": "Đặc sản Bến Tre"},
    }
    score = validate_data.entity_quality_score(entity)
    assert score == 100


def test_seo_required_product_has_all_expanded_keys() -> None:
    """Verify the product SEO_REQUIRED list includes all expanded key names."""
    product_keys = validate_data.SEO_REQUIRED["product"]
    for key in ("price", "price_range", "ocop", "ocop_star", "ocop_certified", "brand"):
        assert key in product_keys


def test_seo_required_event_has_both_date_keys() -> None:
    """Event should accept both date_start and startDate."""
    event_keys = validate_data.SEO_REQUIRED["event"]
    assert "date_start" in event_keys
    assert "startDate" in event_keys


def test_seo_required_attraction_has_expanded_keys() -> None:
    """Attraction should check admission, hours, specialty, price_range."""
    attr_keys = validate_data.SEO_REQUIRED["attraction"]
    for key in ("admission", "hours", "specialty", "price_range"):
        assert key in attr_keys


def test_quality_score_itinerary_not_penalized_for_coords_area() -> None:
    """Itinerary entities should NOT be penalized for missing coords/area/placeId."""
    entity = {
        "id": "it-test", "type": "itinerary", "name": "Lộ trình test",
        "summary": "Mô tả đủ dài cho SEO và nội dung hữu ích cho người đọc.",
        "placeId": "xa-1",
        "source": [{"url": "https://example.com"}],
        "images": ["https://example.com/img.jpg"],
        "confidence": 1.0,
    }
    score = validate_data.entity_quality_score(entity)
    assert score == 100


def test_quality_score_itinerary_without_placeId_or_area() -> None:
    """Itinerary without placeId and area should NOT lose points for those."""
    entity = {
        "id": "it-min", "type": "itinerary", "name": "Lộ trình",
        "summary": "Mô tả đủ dài cho SEO và nội dung hữu ích cho người đọc.",
        "source": [{"url": "https://example.com"}],
        "images": ["https://example.com/img.jpg"],
        "confidence": 1.0,
    }
    score = validate_data.entity_quality_score(entity)
    assert score == 100
