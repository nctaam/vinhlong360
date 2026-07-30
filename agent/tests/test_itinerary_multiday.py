import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import itinerary_multiday
from itinerary_multiday import (
    MultiDayDayInput,
    MultiDayOptions,
    optimize_multi_day_allocation,
)
from itinerary_schedule import (
    NoFeasibleScheduleError,
    ScheduleOptions,
    ScheduleStop,
    TimeWindow,
)
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


def endpoint_choice_inputs() -> tuple[MultiDayDayInput, MultiDayDayInput]:
    return (
        day_input(
            1,
            [
                candidate("start", 10.00, visit=0),
                candidate("near-next-day", 11.00),
                candidate("baseline-end", 10.01),
            ],
        ),
        day_input(
            2,
            [
                candidate("day-2-first", 11.01),
                candidate("end", 11.02, visit=0),
            ],
        ),
    )


def test_dp_changes_internal_endpoint_to_reduce_next_day_origin_travel():
    result = optimize_multi_day_allocation(
        endpoint_choice_inputs(),
        global_start_id="start",
        global_end_id="end",
        options=MultiDayOptions(max_iterations=0),
    )

    assert result.days[0].ordered_ids[0] == "start"
    assert result.days[0].ordered_ids[-1] == "near-next-day"
    assert result.days[-1].ordered_ids[-1] == "end"
    assert max(result.final_load_minutes) <= max(result.initial_load_minutes)


def test_dp_keeps_fixed_anchor_in_the_original_day():
    first, second = endpoint_choice_inputs()
    meal = ScheduleStop(
        "meal",
        (11.015, 106.0),
        60,
        (TimeWindow(720, 780),),
        True,
    )
    second = MultiDayDayInput(
        day_index=second.day_index,
        candidates=second.candidates,
        fixed_stops=(meal,),
        baseline_order=second.baseline_order,
        schedule_options=second.schedule_options,
    )

    result = optimize_multi_day_allocation(
        (first, second),
        global_start_id="start",
        global_end_id="end",
        options=MultiDayOptions(max_iterations=0),
    )

    assert "meal" not in result.days[0].ordered_ids
    assert "meal" in result.days[1].ordered_ids
    assert result.days[1].schedule.skipped == ()


def test_endpoint_dp_is_deterministic():
    first = optimize_multi_day_allocation(
        endpoint_choice_inputs(),
        "start",
        "end",
        MultiDayOptions(max_iterations=0),
    )
    second = optimize_multi_day_allocation(
        endpoint_choice_inputs(),
        "start",
        "end",
        MultiDayOptions(max_iterations=0),
    )

    assert first == second


def test_dp_keeps_complete_baseline_when_dynamic_search_deadlines(monkeypatch):
    def deadline(*_args, **_kwargs):
        raise NoFeasibleScheduleError("deadline")

    monkeypatch.setattr(itinerary_multiday, "_solve_allocation", deadline)

    result = optimize_multi_day_allocation(
        simple_two_day_inputs(),
        "start",
        "end",
        MultiDayOptions(max_iterations=0),
    )

    assert tuple(day.content_ids for day in result.days) == (
        ("start", "day-1-end"),
        ("day-2-first", "end"),
    )
    assert result.initial_load_minutes == result.final_load_minutes
