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
