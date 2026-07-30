"""Unit tests for Phase 3 selection contracts and pruning."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from itinerary_schedule import ScheduleOptions, ScheduleStop, build_fallback_matrix
from itinerary_selection import (
    DroppedCandidate,
    SelectionCandidate,
    SelectionOptions,
    prune_candidates,
    select_and_schedule_day,
)


def _latitude_for(stop_id: str) -> float:
    if stop_id == "start":
        return 10.0
    if stop_id == "end":
        return 10.2
    if stop_id.startswith("poi-"):
        return 10.02 + int(stop_id.removeprefix("poi-")) * 0.01
    return 10.1


def candidate(
    stop_id: str,
    reward: float,
    entity_type: str = "attraction",
    area: str = "vinh-long",
    visit: int = 60,
) -> SelectionCandidate:
    return SelectionCandidate(
        stop=ScheduleStop(stop_id, (_latitude_for(stop_id), 106.0), visit),
        reward=reward,
        entity_type=entity_type,
        area=area,
    )


def matrix_for(*stop_ids: str):
    stops = [
        ScheduleStop(stop_id, (_latitude_for(stop_id), 106.0), 0)
        for stop_id in stop_ids
    ]
    return build_fallback_matrix(stops, "driving")


def test_dominance_prune_keeps_higher_reward_shorter_candidate():
    kept, dropped = prune_candidates(
        [
            candidate("good", 10.0, visit=30),
            candidate("dominated", 8.0, visit=60),
        ],
        required_ids=frozenset(),
        max_candidates=20,
    )

    assert [item.stop.id for item in kept] == ["good"]
    assert dropped == (DroppedCandidate("dominated", "dominated"),)


def test_required_candidate_survives_dominance_and_cap():
    candidates = [candidate("required", 1.0, visit=120)] + [
        candidate(
            f"poi-{index}",
            20.0 - index,
            entity_type=f"type-{index}",
            visit=30,
        )
        for index in range(21)
    ]

    kept, dropped = prune_candidates(
        candidates,
        required_ids=frozenset({"required"}),
        max_candidates=20,
    )

    assert "required" in {item.stop.id for item in kept}
    assert any(item.reason == "candidate-cap" for item in dropped)


def test_selection_options_reject_invalid_bounds():
    with pytest.raises(ValueError):
        SelectionOptions(target_count=0)
    with pytest.raises(ValueError):
        SelectionOptions(target_count=4, exact_limit=-1)


def test_required_count_cannot_exceed_candidate_cap():
    candidates = [
        candidate(f"poi-{index}", 1.0, entity_type=f"type-{index}")
        for index in range(21)
    ]

    with pytest.raises(ValueError, match="Required"):
        prune_candidates(
            candidates,
            required_ids=frozenset(item.stop.id for item in candidates),
            max_candidates=20,
        )


def test_required_only_selection_schedules_without_optional_search():
    candidates = [
        candidate("start", 2.0, visit=0),
        candidate("end", 3.0, visit=0),
    ]

    result = select_and_schedule_day(
        candidates=candidates,
        required_ids=frozenset({"start", "end"}),
        fixed_stops=(),
        matrix=matrix_for("start", "end"),
        schedule_options=ScheduleOptions(),
        selection_options=SelectionOptions(target_count=2),
    )

    assert result.selected_ids == ("start", "end")
    assert result.selected_count == 2
    assert result.total_reward == 5.0
