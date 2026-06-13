from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("normalize_data", ROOT / "scripts" / "normalize_data.py")
normalize_data = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(normalize_data)


def test_infer_area_from_place_uses_place_when_entity_has_no_conflict() -> None:
    places = {
        "xa-tra-cu": {"id": "xa-tra-cu", "type": "place", "area": "tra-vinh"},
    }
    entity = {
        "id": "chua-co-nodol",
        "type": "history",
        "name": "Chua Co Nodol",
        "placeId": "xa-tra-cu",
    }

    area, conflict = normalize_data.infer_area_from_place(entity, places)

    assert area == "tra-vinh"
    assert conflict is False


def test_infer_area_from_place_rejects_conflicting_entity_text() -> None:
    places = {
        "xa-tra-on": {"id": "xa-tra-on", "type": "place", "area": "vinh-long"},
    }
    entity = {
        "id": "khach-san-tra-vinh",
        "type": "accommodation",
        "name": "Khach san Tra Vinh",
        "placeId": "xa-tra-on",
        "attributes": {"address": "Thanh pho Tra Vinh"},
    }

    area, conflict = normalize_data.infer_area_from_place(entity, places)

    assert area is None
    assert conflict is True


def test_generate_place_summary_uses_existing_administrative_fields() -> None:
    entity = {
        "id": "p-tra-vinh",
        "type": "place",
        "name": "Ph\u01b0\u1eddng Tr\u00e0 Vinh",
        "level": "phuong",
        "area": "tra-vinh",
        "legacyArea": "TP Tr\u00e0 Vinh",
    }

    summary = normalize_data.generate_place_summary(entity)

    assert summary is not None
    assert "Ph\u01b0\u1eddng Tr\u00e0 Vinh" in summary
    assert "Tr\u00e0 Vinh" in summary
    assert "TP Tr\u00e0 Vinh" in summary


def test_write_data_js_reports_unchanged_content(tmp_path: Path) -> None:
    data = {
        "entities": [
            {"id": "p-tra-vinh", "type": "place", "name": "Ph\u01b0\u1eddng Tr\u00e0 Vinh"},
            {"id": "ao-ba-om", "type": "attraction", "name": "Ao B\u00e0 Om"},
        ],
        "relationships": [],
        "itineraries": [],
    }
    path = tmp_path / "data.js"

    assert normalize_data.write_data_js(data, path) is True
    first = path.read_text(encoding="utf-8")
    assert normalize_data.write_data_js(data, path) is False
    assert path.read_text(encoding="utf-8") == first

def test_regenerate_near_relationships_uses_in_bounds_same_area_and_fanout() -> None:
    places = {
        "p-a": {"id": "p-a", "type": "place", "area": "vinh-long"},
        "p-b": {"id": "p-b", "type": "place", "area": "ben-tre"},
    }
    entities = [
        {"id": "p-a", "type": "place", "area": "vinh-long"},
        {"id": "p-b", "type": "place", "area": "ben-tre"},
        {"id": "a", "type": "attraction", "area": "vinh-long", "placeId": "p-a", "coordinates": [10.25, 106.0]},
        {"id": "b", "type": "dish", "area": "vinh-long", "placeId": "p-a", "coordinates": [10.251, 106.001]},
        {"id": "c", "type": "product", "area": "ben-tre", "placeId": "p-b", "coordinates": [10.252, 106.002]},
        {"id": "d", "type": "product", "area": "vinh-long", "placeId": "p-a", "coordinates": [21.0, 105.8]},
    ]
    relationships = [
        {"from": "a", "to": "c", "type": "near"},
        {"from": "a", "to": "b", "type": "related_to"},
    ]

    rebuilt, previous_near, new_near = normalize_data.regenerate_near_relationships(
        entities,
        relationships,
        places,
        max_per_entity=1,
    )

    near_edges = [rel for rel in rebuilt if normalize_data.rel_type(rel) == "near"]
    assert previous_near == 1
    assert new_near == 1
    assert near_edges == [{"from": "a", "to": "b", "type": "near", "distance_km": near_edges[0]["distance_km"]}]
    assert any(normalize_data.rel_type(rel) == "related_to" for rel in rebuilt)

def test_drop_produced_in_area_conflicts_keeps_same_area_edges() -> None:
    places = {
        "p-vl": {"id": "p-vl", "type": "place", "area": "vinh-long"},
        "p-bt": {"id": "p-bt", "type": "place", "area": "ben-tre"},
    }
    entities = {
        "product-vl": {"id": "product-vl", "type": "product", "placeId": "p-vl"},
        "village-vl": {"id": "village-vl", "type": "craft_village", "area": "vinh-long"},
        "village-bt": {"id": "village-bt", "type": "craft_village", "area": "ben-tre"},
    }
    relationships = [
        {"from": "product-vl", "to": "village-vl", "type": "produced_in"},
        {"from": "product-vl", "to": "village-bt", "type": "produced_in"},
        {"from": "product-vl", "to": "village-bt", "type": "related_to"},
    ]

    kept, dropped = normalize_data.drop_produced_in_area_conflicts(relationships, entities, places)

    assert dropped == 1
    assert {normalize_data.rel_type(rel) for rel in kept} == {"produced_in", "related_to"}
    assert {rel["to"] for rel in kept if normalize_data.rel_type(rel) == "produced_in"} == {"village-vl"}
