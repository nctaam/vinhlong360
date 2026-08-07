import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import itinerary_gen
import knowledge
from itinerary_schedule import NoFeasibleScheduleError


def _place(place_id: str, coordinates=(10.0, 106.0)) -> dict:
    return {
        "id": place_id,
        "name": place_id,
        "type": "place",
        "area": "vinh-long",
        "coordinates": coordinates,
    }


def _entity(
    entity_id: str,
    coordinates: list[float],
    entity_type: str,
    visit_minutes: int,
    confidence: float,
) -> dict:
    return {
        "id": entity_id,
        "name": entity_id.upper(),
        "type": entity_type,
        "placeId": "p-vl",
        "confidence": confidence,
        "summary": "phase 4 generator fixture",
        "coordinates": coordinates,
        "visit_minutes": visit_minutes,
    }


@pytest.fixture
def imbalanced_generator_entities(monkeypatch):
    ordered_ids = [
        "start",
        "heavy-fixed",
        "move-me",
        "day-1-end",
        "day-2-a",
        "day-2-b",
        "day-2-c",
        "end",
    ]
    entities = {
        "p-vl": _place("p-vl"),
        "start": _entity("start", [10.00, 106.0], "attraction", 0, 1.00),
        "heavy-fixed": _entity("heavy-fixed", [10.02, 106.0], "experience", 200, 0.99),
        "move-me": _entity("move-me", [10.061, 106.0], "craft_village", 100, 0.98),
        "day-1-end": _entity("day-1-end", [10.06, 106.0], "product", 0, 0.97),
        "day-2-a": _entity("day-2-a", [10.08, 106.0], "attraction", 0, 0.96),
        "day-2-b": _entity("day-2-b", [10.10, 106.0], "experience", 30, 0.95),
        "day-2-c": _entity("day-2-c", [10.12, 106.0], "craft_village", 30, 0.94),
        "end": _entity("end", [10.14, 106.0], "product", 0, 0.93),
    }
    monkeypatch.setattr(knowledge, "_entities", entities)
    monkeypatch.setattr(knowledge, "_relationships", [])
    monkeypatch.setattr(knowledge, "_itineraries", {})

    def forced_select(candidates, total, areas, days):
        by_id = {item["entity"]["id"]: item for item in candidates}
        return [by_id[stop_id] for stop_id in ordered_ids]

    monkeypatch.setattr(itinerary_gen, "_select_diverse", forced_select)
    return entities


def _content_ids(day: dict) -> list[str]:
    return [
        stop["entity"]["id"]
        for stop in day["stops"]
        if not stop.get("is_meal") and not stop.get("is_rest")
    ]


def test_generator_balances_days_and_preserves_global_endpoints(
    imbalanced_generator_entities,
):
    result = itinerary_gen.generate_itinerary(
        days=2,
        interests=["tong_hop"],
        areas=["vinh-long"],
        meal_anchors=[],
    )
    first, second = result["day_plans"]
    allocation = first["schedule"]["allocation"]

    assert _content_ids(first)[0] == "start"
    assert _content_ids(second)[-1] == "end"
    assert "move-me" not in _content_ids(first)
    assert "move-me" in _content_ids(second)
    assert allocation["solver"] in {
        "multiday-dp-local-search",
        "multiday-deadline",
    }
    assert allocation["final_load_minutes"] < allocation["initial_load_minutes"]
    assert first["schedule"]["selected_count"] == 4
    assert second["schedule"]["selected_count"] == 4


def test_generator_multiday_keeps_entity_uniqueness_and_total_stops(
    imbalanced_generator_entities,
):
    result = itinerary_gen.generate_itinerary(
        days=2,
        interests=["tong_hop"],
        areas=["vinh-long"],
        meal_anchors=[],
    )
    emitted = [
        stop["entity"]["id"]
        for day in result["day_plans"]
        for stop in day["stops"]
    ]

    assert len(emitted) == len(set(emitted))
    assert result["total_stops"] == len(emitted)
    assert all("allocation" in day["schedule"] for day in result["day_plans"])


def test_generator_keeps_phase3_output_when_multiday_solver_fails(
    imbalanced_generator_entities,
    monkeypatch,
):
    def fail_multiday(*_args, **_kwargs):
        raise NoFeasibleScheduleError("phase 4 unavailable")

    monkeypatch.setattr(
        itinerary_gen,
        "optimize_multi_day_allocation",
        fail_multiday,
    )
    result = itinerary_gen.generate_itinerary(
        days=2,
        interests=["tong_hop"],
        areas=["vinh-long"],
        meal_anchors=[],
    )

    assert all(
        day["schedule"]["allocation"] == {
            "solver": "multiday-fallback",
            "move_count": 0,
            "moved_in_ids": [],
            "moved_out_ids": [],
            "warnings": ["multiday-fallback"],
        }
        for day in result["day_plans"]
    )


def test_one_day_generator_does_not_add_allocation_diagnostics(
    imbalanced_generator_entities,
):
    result = itinerary_gen.generate_itinerary(
        days=1,
        interests=["tong_hop"],
        areas=["vinh-long"],
        meal_anchors=[],
    )

    assert "allocation" not in result["day_plans"][0]["schedule"]
