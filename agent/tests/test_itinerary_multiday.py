import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from itinerary_multiday import (
    MultiDayDayInput,
    MultiDayOptions,
    optimize_multi_day_allocation,
)
from itinerary_schedule import ScheduleOptions, ScheduleStop
from itinerary_selection import SelectionCandidate


def candidate(
    stop_id: str,
    latitude: float,
    longitude: float = 106.0,
    visit: int = 30,
    reward: float = 1.0,
    entity_type: str | None = None,
    area: str = "vinh-long",
) -> SelectionCandidate:
    return SelectionCandidate(
        stop=ScheduleStop(stop_id, (latitude, longitude), visit),
        reward=reward,
        entity_type=entity_type or stop_id,
        area=area,
    )


def day_input(
    day_index: int,
    candidates: list[SelectionCandidate],
    fixed_stops: tuple[ScheduleStop, ...] = (),
) -> MultiDayDayInput:
    return MultiDayDayInput(
        day_index=day_index,
        candidates=tuple(candidates),
        fixed_stops=fixed_stops,
        baseline_order=tuple(item.stop.id for item in candidates),
        schedule_options=ScheduleOptions(
            day_start_minute=480,
            day_end_minute=1080,
        ),
    )


def simple_two_day_inputs() -> tuple[MultiDayDayInput, MultiDayDayInput]:
    return (
        day_input(
            1,
            [
                candidate("start", 10.00, visit=0),
                candidate("day-1-end", 10.10),
            ],
        ),
        day_input(
            2,
            [
                candidate("day-2-first", 10.20),
                candidate("end", 10.30, visit=0),
            ],
        ),
    )


def test_multiday_options_reject_invalid_bounds():
    with pytest.raises(ValueError):
        MultiDayOptions(min_content_per_day=1)
    with pytest.raises(ValueError):
        MultiDayOptions(max_count_delta=-1)
    with pytest.raises(ValueError):
        MultiDayOptions(deadline_seconds=0)
    with pytest.raises(ValueError):
        MultiDayOptions(max_labels_per_endpoint=0)


def test_optimizer_rejects_duplicate_content_ids_across_days():
    first, second = simple_two_day_inputs()
    duplicate = day_input(
        2,
        [candidate("day-1-end", 10.20), candidate("end", 10.30, visit=0)],
    )

    with pytest.raises(ValueError, match="duplicate"):
        optimize_multi_day_allocation(
            (first, duplicate),
            global_start_id="start",
            global_end_id="end",
            options=MultiDayOptions(max_iterations=0),
        )


def test_optimizer_rejects_unknown_global_anchor():
    days = simple_two_day_inputs()

    with pytest.raises(ValueError, match="global"):
        optimize_multi_day_allocation(
            days,
            global_start_id="missing",
            global_end_id="end",
            options=MultiDayOptions(max_iterations=0),
        )


def test_fixed_allocation_adds_internal_origin_without_emitting_it():
    days = simple_two_day_inputs()
    result = optimize_multi_day_allocation(
        days,
        global_start_id="start",
        global_end_id="end",
        options=MultiDayOptions(max_iterations=0),
    )

    second = result.days[1]
    assert result.move_count == 0
    assert second.synthetic_origin_id is not None
    assert second.synthetic_origin_id in second.schedule.ordered_ids
    assert second.synthetic_origin_id not in second.ordered_ids
    assert set(second.content_ids) == {"day-2-first", "end"}
    assert second.load_minutes > 30.0
    assert "overnight-origin-approximated" in result.warnings


def test_synthetic_origin_avoids_fixed_id_collision_across_days():
    first, second = simple_two_day_inputs()
    collision_id = "__multiday_origin_2_day-1-end"
    first = day_input(
        1,
        list(first.candidates),
        fixed_stops=(ScheduleStop(collision_id, (10.05, 106.0), 0),),
    )

    result = optimize_multi_day_allocation(
        (first, second),
        global_start_id="start",
        global_end_id="end",
        options=MultiDayOptions(max_iterations=0),
    )

    assert result.days[1].synthetic_origin_id == f"{collision_id}_1"
