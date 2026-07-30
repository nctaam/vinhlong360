"""Integration tests for joint POI selection inside the generator."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import itinerary_gen
import knowledge


def _place(place_id, coordinates, area="vinh-long"):
    return {
        "id": place_id,
        "name": place_id,
        "type": "place",
        "area": area,
        "coordinates": coordinates,
    }


def _entity(entity_id, coordinates, **fields):
    entity = {
        "id": entity_id,
        "name": entity_id.upper(),
        "type": "attraction",
        "placeId": "p-vl",
        "confidence": 1.0,
        "summary": "phase 3 selection fixture",
        "coordinates": coordinates,
    }
    entity.update(fields)
    return entity


def _install(monkeypatch, entities):
    monkeypatch.setattr(knowledge, "_entities", entities)
    monkeypatch.setattr(knowledge, "_relationships", [])
    monkeypatch.setattr(knowledge, "_itineraries", {})
    return entities


@pytest.fixture
def generator_entities(monkeypatch):
    return _install(
        monkeypatch,
        {
            "p-vl": _place("p-vl", [10.0, 106.0]),
            "start": _entity("start", [10.0, 106.0], visit_minutes=0),
            "poi-a": _entity(
                "poi-a",
                [10.04, 106.0],
                confidence=1.0,
                visit_minutes=45,
            ),
            "poi-b": _entity(
                "poi-b",
                [10.08, 106.0],
                confidence=0.8,
                visit_minutes=120,
                type="experience",
            ),
            "poi-c": _entity(
                "poi-c",
                [10.12, 106.0],
                confidence=0.7,
                visit_minutes=30,
                type="craft_village",
            ),
            "poi-d": _entity(
                "poi-d",
                [10.14, 106.0],
                confidence=0.6,
                visit_minutes=180,
                type="product",
            ),
            "poi-e": _entity(
                "poi-e",
                [10.16, 106.0],
                confidence=0.5,
                visit_minutes=45,
                type="dish",
            ),
            "end": _entity("end", [10.18, 106.0], visit_minutes=0),
            "food": _entity(
                "food",
                [10.06, 106.0],
                type="dish",
                confidence=0.4,
            ),
        },
    )


@pytest.fixture
def two_day_entities(monkeypatch):
    entities = {
        "p-vl": _place("p-vl", [10.0, 106.0]),
        "food": _entity(
            "food",
            [10.09, 106.0],
            type="dish",
            confidence=0.2,
        ),
    }
    for index in range(8):
        entities[f"poi-{index}"] = _entity(
            f"poi-{index}",
            [10.01 + index * 0.02, 106.0],
            confidence=1.0 - index * 0.05,
            visit_minutes=45,
            type="attraction" if index % 2 == 0 else "experience",
        )
    return _install(monkeypatch, entities)


@pytest.fixture
def missing_coordinate_entities(monkeypatch):
    return _install(
        monkeypatch,
        {
            "p-vl": _place("p-vl", None),
            "missing-start": _entity(
                "missing-start",
                None,
                confidence=1.0,
                visit_minutes=0,
            ),
            "middle": _entity(
                "middle",
                [10.08, 106.0],
                confidence=0.9,
                visit_minutes=60,
            ),
            "end": _entity(
                "end",
                [10.16, 106.0],
                confidence=0.8,
                visit_minutes=0,
            ),
        },
    )


def test_generator_selects_feasible_high_reward_subset_and_reports_drops(
    generator_entities,
):
    result = itinerary_gen.generate_itinerary(
        days=1,
        interests=["tong_hop"],
        areas=["vinh-long"],
    )
    schedule = result["day_plans"][0]["schedule"]

    assert schedule["selection_solver"] in {"selection-exact", "selection-beam"}
    assert schedule["candidate_count"] >= schedule["selected_count"]
    assert (
        schedule["selected_count"] + len(schedule["dropped_reasons"])
        == schedule["candidate_count"]
    )
    assert all(item["reason"] for item in schedule["dropped_reasons"])


def test_generator_reserves_global_ids_before_meal_selection(two_day_entities):
    result = itinerary_gen.generate_itinerary(
        days=2,
        interests=["tong_hop"],
        areas=["vinh-long"],
        meal_anchors=["12:00"],
    )

    emitted_ids = [
        stop["entity"]["id"]
        for day in result["day_plans"]
        for stop in day["stops"]
    ]
    assert len(emitted_ids) == len(set(emitted_ids))


def test_generator_uses_phase2b_fallback_when_required_endpoint_lacks_coordinates(
    missing_coordinate_entities,
):
    result = itinerary_gen.generate_itinerary(
        days=1,
        interests=["tham_quan"],
        areas=["vinh-long"],
    )
    schedule = result["day_plans"][0]["schedule"]

    assert schedule["solver"] == "legacy-fixed-order"
    assert schedule["selection_solver"] == "phase2b-fallback"
    assert "coordinates-missing" in schedule["warnings"]
    assert "selection-fallback" in schedule["warnings"]
