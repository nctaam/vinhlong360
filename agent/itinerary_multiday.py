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


@dataclass(frozen=True)
class _AllocationLabel:
    day_results: tuple[MultiDayDayResult, ...]
    current_end_id: str
    loads: tuple[float, ...]
    total_travel_minutes: float
    total_backtrack_ratio: float
    area_switches: int


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


def _load_objective(loads: tuple[float, ...]) -> tuple[float, float, float]:
    maximum = max(loads)
    minimum = min(loads)
    average = sum(loads) / len(loads)
    return (
        maximum,
        maximum - minimum,
        sum(abs(load - average) for load in loads),
    )


def _area_switch_count(
    day_results: tuple[MultiDayDayResult, ...],
    candidate_by_id: dict[str, SelectionCandidate],
) -> int:
    content_order = tuple(
        stop_id
        for day in day_results
        for stop_id in day.ordered_ids
        if stop_id in candidate_by_id
    )
    return sum(
        candidate_by_id[left].area != candidate_by_id[right].area
        for left, right in zip(content_order, content_order[1:])
    )


def _label_metrics(label: _AllocationLabel) -> tuple[float, ...]:
    max_load, load_range, absolute_deviation = _load_objective(label.loads)
    return (
        max_load,
        load_range,
        absolute_deviation,
        label.total_travel_minutes,
        label.total_backtrack_ratio,
        float(label.area_switches),
    )


def _label_objective(label: _AllocationLabel) -> tuple[object, ...]:
    return (
        *_label_metrics(label),
        tuple(day.ordered_ids for day in label.day_results),
        label.current_end_id,
    )


def _label_dominates(left: _AllocationLabel, right: _AllocationLabel) -> bool:
    """Compare labels that finish on the same endpoint."""
    if left.current_end_id != right.current_end_id:
        return False
    left_metrics = _label_metrics(left)
    right_metrics = _label_metrics(right)
    return all(
        left_value <= right_value
        for left_value, right_value in zip(left_metrics, right_metrics)
    ) and any(
        left_value < right_value
        for left_value, right_value in zip(left_metrics, right_metrics)
    )


def _cache_key(
    day: MultiDayDayInput,
    content_ids: tuple[str, ...],
    previous_end_id: str | None,
    current_end_id: str,
) -> tuple[object, ...]:
    return (
        day.day_index,
        tuple(sorted(content_ids)),
        tuple(stop.id for stop in day.fixed_stops),
        previous_end_id,
        current_end_id,
    )


def _cached_schedule_day(
    day: MultiDayDayInput,
    content_ids: tuple[str, ...],
    candidate_by_id: dict[str, SelectionCandidate],
    global_start_id: str,
    previous_end_id: str | None,
    current_end_id: str,
    deadline: float,
    cache: dict[tuple[object, ...], MultiDayDayResult | None],
) -> MultiDayDayResult | None:
    key = _cache_key(day, content_ids, previous_end_id, current_end_id)
    if key in cache:
        return cache[key]
    remaining_seconds = deadline - time.perf_counter()
    if remaining_seconds <= 0:
        cache[key] = None
        return None
    try:
        result = _schedule_day(
            day,
            content_ids,
            candidate_by_id,
            first_content_id=global_start_id if day.day_index == 1 else None,
            previous_end_id=previous_end_id,
            current_end_id=current_end_id,
            remaining_seconds=remaining_seconds,
        )
    except NoFeasibleScheduleError:
        result = None
    cache[key] = result
    return result


def _endpoint_choices(
    day_index: int,
    day_count: int,
    content_ids: tuple[str, ...],
    global_start_id: str,
    global_end_id: str,
) -> tuple[str, ...]:
    if day_index == day_count:
        return (global_end_id,)
    if day_index == 1:
        return tuple(stop_id for stop_id in content_ids if stop_id != global_start_id)
    return content_ids


def _prune_labels(
    labels: list[_AllocationLabel],
    max_labels_per_endpoint: int,
) -> tuple[_AllocationLabel, ...]:
    by_endpoint: dict[str, list[_AllocationLabel]] = {}
    for label in labels:
        by_endpoint.setdefault(label.current_end_id, []).append(label)

    kept: list[_AllocationLabel] = []
    for endpoint in sorted(by_endpoint):
        ordered = sorted(by_endpoint[endpoint], key=_label_objective)
        nondominated = [
            label
            for label in ordered
            if not any(
                _label_dominates(other, label)
                for other in ordered
                if other is not label
            )
        ]
        kept.extend(nondominated[:max_labels_per_endpoint])
    return tuple(sorted(kept, key=_label_objective))


def _solve_allocation(
    days: tuple[MultiDayDayInput, ...],
    allocation: Allocation,
    candidate_by_id: dict[str, SelectionCandidate],
    global_start_id: str,
    global_end_id: str,
    options: MultiDayOptions,
    deadline: float,
    cache: dict[tuple[object, ...], MultiDayDayResult | None],
) -> tuple[MultiDayDayResult, ...]:
    """Return the best complete route chain for one ownership allocation."""
    labels: tuple[_AllocationLabel, ...] = ()
    for day_position, (day, content_ids) in enumerate(zip(days, allocation)):
        if time.perf_counter() >= deadline:
            raise NoFeasibleScheduleError("Multi-day allocation deadline reached")
        endpoint_choices = _endpoint_choices(
            day.day_index,
            len(days),
            content_ids,
            global_start_id,
            global_end_id,
        )
        previous_labels: tuple[_AllocationLabel | None, ...] = labels or (None,)
        next_labels: list[_AllocationLabel] = []
        for previous_label in previous_labels:
            previous_end_id = (
                previous_label.current_end_id if previous_label is not None else None
            )
            for current_end_id in endpoint_choices:
                if time.perf_counter() >= deadline:
                    break
                day_result = _cached_schedule_day(
                    day,
                    content_ids,
                    candidate_by_id,
                    global_start_id,
                    previous_end_id,
                    current_end_id,
                    deadline,
                    cache,
                )
                if day_result is None:
                    continue
                day_results = (
                    (previous_label.day_results if previous_label is not None else ())
                    + (day_result,)
                )
                loads = (
                    (previous_label.loads if previous_label is not None else ())
                    + (day_result.load_minutes,)
                )
                next_labels.append(
                    _AllocationLabel(
                        day_results=day_results,
                        current_end_id=current_end_id,
                        loads=loads,
                        total_travel_minutes=(
                            previous_label.total_travel_minutes
                            if previous_label is not None
                            else 0.0
                        )
                        + day_result.schedule.total_travel_minutes,
                        total_backtrack_ratio=(
                            previous_label.total_backtrack_ratio
                            if previous_label is not None
                            else 0.0
                        )
                        + day_result.schedule.backtrack_ratio,
                        area_switches=_area_switch_count(
                            day_results,
                            candidate_by_id,
                        ),
                    )
                )
        if not next_labels:
            raise NoFeasibleScheduleError(
                f"No feasible endpoint label for day {day_position + 1}"
            )
        labels = _prune_labels(next_labels, options.max_labels_per_endpoint)

    return min(labels, key=_label_objective).day_results


def _solve_fixed_baseline(
    days: tuple[MultiDayDayInput, ...],
    allocation: Allocation,
    candidate_by_id: dict[str, SelectionCandidate],
    global_start_id: str,
    deadline: float,
    cache: dict[tuple[object, ...], MultiDayDayResult | None],
) -> tuple[MultiDayDayResult, ...] | None:
    result_days: list[MultiDayDayResult] = []
    previous_end_id: str | None = None
    for day, content_ids in zip(days, allocation):
        current_end_id = content_ids[-1]
        result = _cached_schedule_day(
            day,
            content_ids,
            candidate_by_id,
            global_start_id,
            previous_end_id,
            current_end_id,
            deadline,
            cache,
        )
        if result is None:
            return None
        result_days.append(result)
        previous_end_id = current_end_id
    return tuple(result_days)


def _result_days_objective(
    result_days: tuple[MultiDayDayResult, ...],
    candidate_by_id: dict[str, SelectionCandidate],
) -> tuple[object, ...]:
    label = _AllocationLabel(
        day_results=result_days,
        current_end_id=result_days[-1].schedule.ordered_ids[-1],
        loads=tuple(day.load_minutes for day in result_days),
        total_travel_minutes=sum(
            day.schedule.total_travel_minutes for day in result_days
        ),
        total_backtrack_ratio=sum(
            day.schedule.backtrack_ratio for day in result_days
        ),
        area_switches=_area_switch_count(result_days, candidate_by_id),
    )
    return _label_objective(label)


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
    cache: dict[tuple[object, ...], MultiDayDayResult | None] = {}
    baseline_days = _solve_fixed_baseline(
        day_inputs,
        allocation,
        candidate_by_id,
        global_start_id,
        deadline,
        cache,
    )
    try:
        final_days = _solve_allocation(
            day_inputs,
            allocation,
            candidate_by_id,
            global_start_id,
            global_end_id,
            options,
            deadline,
            cache,
        )
    except NoFeasibleScheduleError:
        if baseline_days is None:
            raise
        final_days = baseline_days
    if baseline_days is not None and _result_days_objective(
        baseline_days,
        candidate_by_id,
    ) < _result_days_objective(final_days, candidate_by_id):
        final_days = baseline_days
    final_loads = tuple(day.load_minutes for day in final_days)
    initial_loads = (
        tuple(day.load_minutes for day in baseline_days)
        if baseline_days is not None
        else final_loads
    )
    empty_moves = tuple(() for _ in final_days)
    warnings = (
        ("overnight-origin-approximated",)
        if any(day.synthetic_origin_id is not None for day in final_days)
        else ()
    )
    return MultiDayResult(
        days=final_days,
        solver="multiday-dp-local-search",
        initial_load_minutes=initial_loads,
        final_load_minutes=final_loads,
        max_imbalance_minutes=max(final_loads) - min(final_loads),
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
