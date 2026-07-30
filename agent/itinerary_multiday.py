"""Dependency-free multi-day itinerary allocation contracts and evaluation."""

from __future__ import annotations

from dataclasses import dataclass, replace
import math
import time
from typing import Sequence

from itinerary_schedule import (
    NoFeasibleScheduleError,
    ScheduleOptions,
    ScheduleResult,
    ScheduleStop,
    build_fallback_matrix,
    schedule_stop_order,
)
from itinerary_selection import SelectionCandidate


Allocation = tuple[tuple[str, ...], ...]


class _CandidateMap(dict[str, SelectionCandidate]):
    """Candidate lookup that also carries globally reserved stop IDs."""

    reserved_ids: frozenset[str] = frozenset()


@dataclass(frozen=True)
class MultiDayDayInput:
    day_index: int
    candidates: tuple[SelectionCandidate, ...]
    fixed_stops: tuple[ScheduleStop, ...]
    baseline_order: tuple[str, ...]
    schedule_options: ScheduleOptions

    def __post_init__(self) -> None:
        object.__setattr__(self, "candidates", tuple(self.candidates))
        object.__setattr__(self, "fixed_stops", tuple(self.fixed_stops))
        object.__setattr__(self, "baseline_order", tuple(self.baseline_order))


@dataclass(frozen=True)
class MultiDayOptions:
    min_content_per_day: int = 2
    max_count_delta: int = 1
    max_iterations: int = 12
    deadline_seconds: float = 1.0
    max_labels_per_endpoint: int = 8

    def __post_init__(self) -> None:
        if not _is_int(self.min_content_per_day) or self.min_content_per_day < 2:
            raise ValueError("Minimum content per day must be at least 2")
        if not _is_int(self.max_count_delta) or self.max_count_delta < 0:
            raise ValueError("Maximum count delta must be non-negative")
        if not _is_int(self.max_iterations) or self.max_iterations < 0:
            raise ValueError("Maximum iterations must be non-negative")
        if (
            isinstance(self.deadline_seconds, bool)
            or not isinstance(self.deadline_seconds, (int, float))
            or not math.isfinite(self.deadline_seconds)
            or self.deadline_seconds <= 0
        ):
            raise ValueError("Deadline must be a finite positive number")
        if (
            not _is_int(self.max_labels_per_endpoint)
            or self.max_labels_per_endpoint < 1
        ):
            raise ValueError("Maximum labels per endpoint must be positive")


@dataclass(frozen=True)
class MultiDayDayResult:
    day_index: int
    content_ids: tuple[str, ...]
    ordered_ids: tuple[str, ...]
    schedule: ScheduleResult
    synthetic_origin_id: str | None
    load_minutes: float


@dataclass(frozen=True)
class MultiDayResult:
    days: tuple[MultiDayDayResult, ...]
    solver: str
    initial_load_minutes: tuple[float, ...]
    final_load_minutes: tuple[float, ...]
    max_imbalance_minutes: float
    move_count: int
    moved_in_by_day: tuple[tuple[str, ...], ...]
    moved_out_by_day: tuple[tuple[str, ...], ...]
    warnings: tuple[str, ...]


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_inputs(
    days: tuple[MultiDayDayInput, ...],
    global_start_id: str,
    global_end_id: str,
    options: MultiDayOptions,
) -> dict[str, SelectionCandidate]:
    """Return the unique global candidate map after validating the problem."""
    if not isinstance(options, MultiDayOptions):
        raise ValueError("Multi-day options are invalid")
    if not days:
        raise ValueError("At least one itinerary day is required")
    if not isinstance(global_start_id, str) or not global_start_id.strip():
        raise ValueError("global start ID must not be empty")
    if not isinstance(global_end_id, str) or not global_end_id.strip():
        raise ValueError("global end ID must not be empty")
    if global_start_id == global_end_id:
        raise ValueError("global start and end IDs must differ")

    expected_indices = tuple(range(1, len(days) + 1))
    actual_indices = tuple(day.day_index for day in days)
    if actual_indices != expected_indices:
        raise ValueError("Day indices must be positive, sequential, and start at 1")

    candidate_by_id = _CandidateMap()
    all_fixed_ids: set[str] = set()
    owner_by_id: dict[str, int] = {}

    for day in days:
        if not isinstance(day, MultiDayDayInput):
            raise ValueError("Every day must be a MultiDayDayInput")
        if len(day.candidates) < 2:
            raise ValueError("Each day must contain at least two content candidates")
        if not isinstance(day.schedule_options, ScheduleOptions):
            raise ValueError("Every day must contain valid schedule options")
        if any(not isinstance(item, SelectionCandidate) for item in day.candidates):
            raise ValueError("Day candidates must be SelectionCandidate values")
        if any(not isinstance(stop, ScheduleStop) for stop in day.fixed_stops):
            raise ValueError("Fixed stops must be ScheduleStop values")

        candidate_ids = tuple(item.stop.id for item in day.candidates)
        fixed_ids = tuple(stop.id for stop in day.fixed_stops)
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("duplicate content ID within a day")
        if len(fixed_ids) != len(set(fixed_ids)):
            raise ValueError("duplicate fixed-stop ID within a day")
        if set(candidate_ids) & set(fixed_ids):
            raise ValueError("duplicate ID across content and fixed stops")
        if len(day.baseline_order) != len(set(day.baseline_order)):
            raise ValueError("Baseline order must not contain duplicate IDs")
        if set(day.baseline_order) != set(candidate_ids):
            raise ValueError("Baseline order must contain every content ID exactly once")
        if set(day.baseline_order) & set(fixed_ids):
            raise ValueError("Baseline order must not contain fixed-stop IDs")

        for candidate in day.candidates:
            stop_id = candidate.stop.id
            if stop_id in candidate_by_id or stop_id in all_fixed_ids:
                raise ValueError(f"duplicate content ID across days: {stop_id}")
            candidate_by_id[stop_id] = candidate
            owner_by_id[stop_id] = day.day_index
        for stop_id in fixed_ids:
            if stop_id in candidate_by_id or stop_id in all_fixed_ids:
                raise ValueError(f"duplicate fixed-stop ID across days: {stop_id}")
            all_fixed_ids.add(stop_id)

    if owner_by_id.get(global_start_id) != 1:
        raise ValueError("global start ID must belong to day 1")
    if owner_by_id.get(global_end_id) != len(days):
        raise ValueError("global end ID must belong to the final day")
    if days[0].baseline_order[0] != global_start_id:
        raise ValueError("global start ID must be first in the baseline order")
    if days[-1].baseline_order[-1] != global_end_id:
        raise ValueError("global end ID must be last in the baseline order")

    candidate_by_id.reserved_ids = frozenset(candidate_by_id) | frozenset(
        all_fixed_ids
    )
    return candidate_by_id


def _synthetic_origin_id(
    day: MultiDayDayInput,
    previous_end_id: str,
    candidate_by_id: dict[str, SelectionCandidate],
) -> str:
    base_id = f"__multiday_origin_{day.day_index}_{previous_end_id}"
    used_ids = getattr(candidate_by_id, "reserved_ids", frozenset(candidate_by_id))
    origin_id = base_id
    suffix = 1
    while origin_id in used_ids:
        origin_id = f"{base_id}_{suffix}"
        suffix += 1
    return origin_id


def _schedule_day(
    day: MultiDayDayInput,
    content_ids: tuple[str, ...],
    candidate_by_id: dict[str, SelectionCandidate],
    first_content_id: str | None,
    previous_end_id: str | None,
    current_end_id: str,
    remaining_seconds: float,
) -> MultiDayDayResult:
    """Schedule one fully required day with a fixed first/origin and end."""
    if current_end_id not in content_ids:
        raise NoFeasibleScheduleError("Current endpoint is absent from its day")
    if first_content_id is not None and first_content_id not in content_ids:
        raise NoFeasibleScheduleError("First content stop is absent from its day")
    if (first_content_id is None) == (previous_end_id is None):
        raise ValueError("A day needs exactly one first-stop source")
    if not math.isfinite(remaining_seconds) or remaining_seconds <= 0:
        raise NoFeasibleScheduleError("Multi-day scheduling deadline reached")

    required_content = {
        stop_id: replace(candidate_by_id[stop_id].stop, required=True)
        for stop_id in content_ids
    }
    required_fixed = tuple(replace(stop, required=True) for stop in day.fixed_stops)

    synthetic_origin_id: str | None = None
    if first_content_id is not None:
        first_stop = required_content[first_content_id]
        excluded_content = {first_content_id, current_end_id}
    else:
        assert previous_end_id is not None
        synthetic_origin_id = _synthetic_origin_id(
            day,
            previous_end_id,
            candidate_by_id,
        )
        first_stop = ScheduleStop(
            id=synthetic_origin_id,
            coordinates=candidate_by_id[previous_end_id].stop.coordinates,
            visit_minutes=0,
            required=True,
        )
        excluded_content = {current_end_id}

    middle_stops = tuple(
        required_content[stop_id]
        for stop_id in content_ids
        if stop_id not in excluded_content
    ) + required_fixed
    stops = (first_stop, *middle_stops, required_content[current_end_id])
    schedule_options = replace(
        day.schedule_options,
        deadline_seconds=min(day.schedule_options.deadline_seconds, remaining_seconds),
    )
    schedule = schedule_stop_order(
        stops,
        build_fallback_matrix(stops, "driving"),
        schedule_options,
    )

    expected_ids = tuple(stop.id for stop in stops)
    if schedule.skipped:
        raise NoFeasibleScheduleError("Multi-day schedule skipped a required stop")
    if schedule.overtime_minutes > 0:
        raise NoFeasibleScheduleError("Multi-day schedule exceeds the day window")
    if len(schedule.ordered_ids) != len(expected_ids) or set(
        schedule.ordered_ids
    ) != set(expected_ids):
        raise NoFeasibleScheduleError("Multi-day schedule omitted an input stop")
    if schedule.ordered_ids[0] != first_stop.id:
        raise NoFeasibleScheduleError("Multi-day schedule changed the first stop")
    if schedule.ordered_ids[-1] != current_end_id:
        raise NoFeasibleScheduleError("Multi-day schedule changed the final stop")

    load_minutes = (
        max(placement.finish_visit_minute for placement in schedule.placements)
        - day.schedule_options.day_start_minute
    )
    ordered_ids = tuple(
        stop_id
        for stop_id in schedule.ordered_ids
        if stop_id != synthetic_origin_id
    )
    return MultiDayDayResult(
        day_index=day.day_index,
        content_ids=content_ids,
        ordered_ids=ordered_ids,
        schedule=schedule,
        synthetic_origin_id=synthetic_origin_id,
        load_minutes=load_minutes,
    )


def optimize_multi_day_allocation(
    days: Sequence[MultiDayDayInput],
    global_start_id: str,
    global_end_id: str,
    options: MultiDayOptions,
) -> MultiDayResult:
    """Evaluate the Phase 3 allocation with fixed baseline endpoints."""
    day_inputs = tuple(days)
    candidate_by_id = _validate_inputs(
        day_inputs,
        global_start_id,
        global_end_id,
        options,
    )
    allocation: Allocation = tuple(day.baseline_order for day in day_inputs)
    deadline = time.perf_counter() + options.deadline_seconds

    result_days: list[MultiDayDayResult] = []
    previous_end_id: str | None = None
    for index, (day, content_ids) in enumerate(zip(day_inputs, allocation)):
        current_end_id = content_ids[-1]
        result_days.append(
            _schedule_day(
                day,
                content_ids,
                candidate_by_id,
                first_content_id=global_start_id if index == 0 else None,
                previous_end_id=previous_end_id,
                current_end_id=current_end_id,
                remaining_seconds=deadline - time.perf_counter(),
            )
        )
        previous_end_id = current_end_id

    final_days = tuple(result_days)
    loads = tuple(day.load_minutes for day in final_days)
    empty_moves = tuple(() for _ in final_days)
    warnings = (
        ("overnight-origin-approximated",)
        if any(day.synthetic_origin_id is not None for day in final_days)
        else ()
    )
    return MultiDayResult(
        days=final_days,
        solver="multiday-dp-local-search",
        initial_load_minutes=loads,
        final_load_minutes=loads,
        max_imbalance_minutes=max(loads) - min(loads),
        move_count=0,
        moved_in_by_day=empty_moves,
        moved_out_by_day=empty_moves,
        warnings=warnings,
    )


__all__ = [
    "MultiDayDayInput",
    "MultiDayDayResult",
    "MultiDayOptions",
    "MultiDayResult",
    "optimize_multi_day_allocation",
]
