"""Behavior tests for the generator's local time-aware schedule adapter."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import itinerary_gen as ig
import knowledge
from itinerary_schedule import NoFeasibleScheduleError


def _place(place_id: str, coordinates=None) -> dict:
    return {
        "id": place_id,
        "name": place_id,
        "type": "place",
        "area": "vinh-long",
        "coordinates": coordinates,
    }


def _entity(entity_id: str, coordinates=None, **fields) -> dict:
    entity = {
        "id": entity_id,
        "name": entity_id.upper(),
        "type": "attraction",
        "placeId": "p-vl",
        "confidence": 1.0,
        "summary": "fixture summary",
        "coordinates": coordinates,
    }
    entity.update(fields)
    return entity


@pytest.fixture
def generator_entities(monkeypatch):
    entities = {
        "p-vl": _place("p-vl"),
        "start": _entity(
            "start",
            [10.0, 106.0],
            visit_minutes=0,
            attributes={"hours": "08:00-18:00"},
        ),
        "near": _entity(
            "near",
            [10.09, 106.0],
            duration_minutes=90,
            attributes={"open_hours": "08:00-18:00"},
        ),
        "end": _entity("end", [10.18, 106.0], visit_minutes=0),
    }
    monkeypatch.setattr(knowledge, "_entities", entities)
    monkeypatch.setattr(knowledge, "_relationships", [])
    monkeypatch.setattr(knowledge, "_itineraries", {})
    return entities


def test_generator_uses_real_leg_durations_instead_of_fixed_thirty_minutes(generator_entities):
    result = ig.generate_itinerary(
        days=1,
        interests=["tham_quan"],
        areas=["vinh-long"],
    )

    day = result["day_plans"][0]
    stops = day["stops"]
    assert [stop["entity"]["id"] for stop in stops if not stop.get("is_meal")] == [
        "start",
        "near",
        "end",
    ]
    assert stops[1]["time"] == "08:15"
    assert day["schedule"]["matrix_source"] == "haversine-fallback"
    assert day["schedule"]["total_travel_minutes"] > 20
    assert set(day["schedule"]) == {
        "solver",
        "matrix_source",
        "total_travel_minutes",
        "waiting_minutes",
        "overtime_minutes",
        "minimum_slack_minutes",
        "backtrack_ratio",
        "skipped",
        "warnings",
    }


def test_generator_uses_parent_place_coordinates_before_falling_back(monkeypatch):
    entities = {
        "p-start": _place("p-start", [10.0, 106.0]),
        "p-near": _place("p-near", [10.09, 106.0]),
        "p-end": _place("p-end", [10.18, 106.0]),
        "start": _entity("start", None, placeId="p-start", visit_minutes=0),
        "near": _entity("near", None, placeId="p-near", duration_minutes=90),
        "end": _entity("end", None, placeId="p-end", visit_minutes=0),
    }
    monkeypatch.setattr(knowledge, "_entities", entities)
    monkeypatch.setattr(knowledge, "_relationships", [])
    monkeypatch.setattr(knowledge, "_itineraries", {})

    day = ig.generate_itinerary(days=1, interests=["tham_quan"], areas=["vinh-long"])[
        "day_plans"
    ][0]

    assert day["stops"][1]["time"] == "08:15"
    assert "coordinates-missing" not in day["schedule"]["warnings"]


def test_generator_keeps_legacy_timeline_when_coordinates_are_missing(generator_entities):
    generator_entities["near"]["coordinates"] = None

    day = ig.generate_itinerary(days=1, interests=["tham_quan"], areas=["vinh-long"])[
        "day_plans"
    ][0]
    stops = [stop for stop in day["stops"] if not stop.get("is_meal")]

    assert [stop["entity"]["id"] for stop in stops] == ["start", "near", "end"]
    assert stops[1]["time"] == "10:00"
    assert day["schedule"]["warnings"] == [
        "meal-anchor-unavailable",
        "coordinates-missing",
    ]


def test_generator_keeps_legacy_timeline_when_schedule_is_infeasible(
    generator_entities, monkeypatch,
):
    def fail_schedule(*_args, **_kwargs):
        raise NoFeasibleScheduleError("middle")

    monkeypatch.setattr(ig, "schedule_stop_order", fail_schedule, raising=False)

    day = ig.generate_itinerary(days=1, interests=["tham_quan"], areas=["vinh-long"])[
        "day_plans"
    ][0]

    assert [stop["time"] for stop in day["stops"] if not stop.get("is_meal")] == [
        "08:00",
        "10:00",
        "12:00",
    ]
    assert day["schedule"]["warnings"] == [
        "meal-anchor-unavailable",
        "schedule-fallback",
    ]
    assert day["schedule"]["skipped"] == []


def test_generator_reports_optional_middle_stop_when_day_window_overflows(generator_entities):
    generator_entities["near"]["duration_minutes"] = 720

    day = ig.generate_itinerary(days=1, interests=["tham_quan"], areas=["vinh-long"])[
        "day_plans"
    ][0]

    assert [stop["entity"]["id"] for stop in day["stops"] if not stop.get("is_meal")] == [
        "start",
        "end",
    ]
    assert day["schedule"]["skipped"] == [
        {"stop_id": "near", "reason": "day-window-overflow"},
    ]


def test_generator_falls_back_for_invalid_schedule_duration(generator_entities):
    generator_entities["near"]["duration_minutes"] = 999

    day = ig.generate_itinerary(days=1, interests=["tham_quan"], areas=["vinh-long"])[
        "day_plans"
    ][0]

    assert day["schedule"]["warnings"] == [
        "meal-anchor-unavailable",
        "schedule-fallback",
    ]


@pytest.fixture
def generator_entities_with_food(generator_entities):
    generator_entities["food"] = _entity(
        "food",
        [10.12, 106.0],
        type="dish",
        summary="Local specialty dish",
    )
    return generator_entities


def test_explicit_meal_anchor_uses_real_food_candidate(generator_entities_with_food):
    result = ig.generate_itinerary(
        days=1,
        interests=["tham_quan"],
        areas=["vinh-long"],
        meal_anchors=["12h00"],
    )

    meals = [stop for stop in result["day_plans"][0]["stops"] if stop.get("is_meal")]
    assert len(meals) == 1
    assert meals[0]["time"] == "12:00"
    assert meals[0]["entity"]["type"] in {"dish", "product"}
    assert meals[0]["entity"]["id"] == "food"


def test_rest_anchor_emits_synthetic_fixed_window_stop(generator_entities):
    result = ig.generate_itinerary(
        days=1,
        interests=["tham_quan"],
        areas=["vinh-long"],
        rest_anchors=["15h00"],
    )

    rests = [stop for stop in result["day_plans"][0]["stops"] if stop.get("is_rest")]
    assert len(rests) == 1
    assert rests[0]["time"] == "15:00"
    assert rests[0]["entity"] == {
        "id": rests[0]["entity"]["id"],
        "name": "Nghỉ",
        "type": "rest",
        "summary": "Khoảng nghỉ",
    }
    assert rests[0]["note"] == "🪑 Nghỉ/đệm thời gian"


def test_explicit_empty_meal_anchors_disable_meal_insertion(generator_entities_with_food):
    result = ig.generate_itinerary(
        days=1,
        interests=["tham_quan"],
        areas=["vinh-long"],
        meal_anchors=[],
    )

    assert not any(stop.get("is_meal") for stop in result["day_plans"][0]["stops"])


def test_invalid_anchor_is_nonfatal_and_reported(generator_entities):
    result = ig.generate_itinerary(
        days=1,
        interests=["tham_quan"],
        areas=["vinh-long"],
        meal_anchors=["not-a-time"],
        rest_anchors=["25:00"],
    )

    warnings = result["day_plans"][0]["schedule"]["warnings"]
    assert warnings.count("invalid-anchor") == 2


def test_meal_anchor_without_food_candidate_is_omitted_with_diagnostic(generator_entities):
    result = ig.generate_itinerary(
        days=1,
        interests=["tham_quan"],
        areas=["vinh-long"],
        meal_anchors=["12:00"],
    )

    day = result["day_plans"][0]
    assert not any(stop.get("is_meal") for stop in day["stops"])
    assert "meal-anchor-unavailable" in day["schedule"]["warnings"]


def test_coordinate_invalid_meal_is_not_reintroduced_by_legacy_fallback(
    generator_entities_with_food,
):
    generator_entities_with_food["food"]["coordinates"] = None
    generator_entities_with_food["near"]["coordinates"] = None

    result = ig.generate_itinerary(
        days=1,
        interests=["tham_quan"],
        areas=["vinh-long"],
        meal_anchors=["12:00"],
    )

    day = result["day_plans"][0]
    assert not any(stop.get("is_meal") for stop in day["stops"])
    assert "meal-anchor-unavailable" in day["schedule"]["warnings"]
    assert "coordinates-missing" in day["schedule"]["warnings"]


@pytest.fixture
def two_day_generator_entities(monkeypatch):
    entities = {
        "p-vl": _place("p-vl"),
        "food": _entity("food", [10.11, 106.0], type="dish"),
    }
    for index in range(8):
        entity_id = f"stop-{index}"
        entities[entity_id] = _entity(
            entity_id,
            [10.0 + index * 0.02, 106.0],
            visit_minutes=60,
        )
    monkeypatch.setattr(knowledge, "_entities", entities)
    monkeypatch.setattr(knowledge, "_relationships", [])
    monkeypatch.setattr(knowledge, "_itineraries", {})
    return entities


def test_meal_anchor_consumes_candidates_across_days(two_day_generator_entities):
    result = ig.generate_itinerary(
        days=2,
        interests=["tham_quan"],
        areas=["vinh-long"],
        meal_anchors=["12:00"],
    )

    meals = [
        stop
        for day in result["day_plans"]
        for stop in day["stops"]
        if stop.get("is_meal")
    ]
    assert [meal["entity"]["id"] for meal in meals] == ["food"]
    assert "meal-anchor-unavailable" in result["day_plans"][1]["schedule"]["warnings"]


@pytest.fixture
def regular_food_on_first_day_entities(monkeypatch):
    entities = {
        "p-vl": _place("p-vl"),
        "food": _entity(
            "food",
            [10.01, 106.0],
            type="dish",
            confidence=1.0,
        ),
    }
    for index in range(7):
        entity_id = f"visit-{index}"
        entities[entity_id] = _entity(
            entity_id,
            [10.03 + index * 0.02, 106.0],
            confidence=0.5,
            visit_minutes=60,
        )
    monkeypatch.setattr(knowledge, "_entities", entities)
    monkeypatch.setattr(knowledge, "_relationships", [])
    monkeypatch.setattr(knowledge, "_itineraries", {})
    return entities


def test_regular_food_on_day_one_is_not_reused_as_day_two_meal(
    regular_food_on_first_day_entities,
):
    result = ig.generate_itinerary(
        days=2,
        interests=["tong_hop"],
        areas=["vinh-long"],
        meal_anchors=["12:00"],
    )

    food_stops = [
        (day["day"], stop)
        for day in result["day_plans"]
        for stop in day["stops"]
        if stop["entity"]["id"] == "food"
    ]
    assert len(food_stops) == 1
    assert food_stops[0][0] == 1
    assert not food_stops[0][1].get("is_meal")
    assert "meal-anchor-unavailable" in result["day_plans"][1]["schedule"]["warnings"]
