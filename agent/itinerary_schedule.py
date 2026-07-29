"""Dependency-free time contracts and local travel-time estimation."""

from __future__ import annotations

from dataclasses import dataclass
import math
import re
import time
from typing import Sequence

from itinerary_optimizer import (
    Coordinates,
    NoFeasibleRouteError,
    RouteStop,
    haversine_km,
    project_onto_corridor,
)


_MODE_SPEED_KMH = {
    "driving": 40.0,
    "cycling": 15.0,
    "foot": 5.0,
}

_TYPE_DEFAULT_MINUTES = {
    "attraction": 90,
    "experience": 120,
    "craft village": 60,
    "dish": 45,
    "product": 30,
    "history": 60,
    "nature": 90,
    "person": 30,
    "event": 120,
    "economy": 30,
    "accommodation": 0,
}

_TIME_RANGE_PATTERN = re.compile(
    r"(?<!\d)"
    r"(?P<start_hour>\d{1,2})"
    r"(?:(?::(?P<start_colon_minute>\d{2}))|(?:[hH](?P<start_h_minute>\d{2}|)))"
    r"\s*-\s*"
    r"(?P<end_hour>\d{1,2})"
    r"(?:(?::(?P<end_colon_minute>\d{2}))|(?:[hH](?P<end_h_minute>\d{2}|)))"
    r"(?!\d)"
)

_WEEKDAY_PREFIX_PATTERN = re.compile(
    r"\b(?:t(?:hứ)?\s*[2-7]|cn)"
    r"(?:\s*-\s*(?:t(?:hứ)?\s*[2-7]|cn))?"
    r"(?=\s*:|\s|$)\s*:?\s*",
    re.IGNORECASE,
)

_HOURS_PATTERN = re.compile(
    r"(?P<value>\d+(?:[.,]\d+)?)\s*(?:giờ|gio|hours?|hrs?|h)\b",
    re.IGNORECASE,
)

_MINUTES_PATTERN = re.compile(
    r"(?P<value>\d+(?:[.,]\d+)?)\s*(?:phút|phut|minutes?|mins?)\b",
    re.IGNORECASE,
)


class NoFeasibleScheduleError(ValueError):
    """Raised when no schedule satisfies the requested constraints."""


@dataclass(frozen=True)
class TimeWindow:
    start_minute: int
    end_minute: int

    def __post_init__(self) -> None:
        if not _is_int(self.start_minute) or not _is_int(self.end_minute):
            raise ValueError("Mốc thời gian phải là số phút nguyên")
        if not 0 <= self.start_minute <= self.end_minute <= 1440:
            raise ValueError("Khung giờ phải nằm trong một ngày")


@dataclass(frozen=True)
class ScheduleStop:
    id: str
    coordinates: Coordinates
    visit_minutes: int
    opening_windows: tuple[TimeWindow, ...] = ()
    required: bool = True

    def __post_init__(self) -> None:
        try:
            coordinates = tuple(self.coordinates)
        except TypeError as exc:
            raise ValueError("Tọa độ phải gồm vĩ độ và kinh độ") from exc
        try:
            RouteStop(self.id, coordinates)
        except TypeError as exc:
            raise ValueError("Tọa độ phải là số hữu hạn") from exc
        if not _is_int(self.visit_minutes) or not 0 <= self.visit_minutes <= 720:
            raise ValueError("Thời lượng tham quan phải nằm trong khoảng 0-720 phút")
        windows = tuple(self.opening_windows)
        if any(not isinstance(window, TimeWindow) for window in windows):
            raise ValueError("Giờ mở cửa phải là các TimeWindow")
        if not isinstance(self.required, bool):
            raise ValueError("Trạng thái bắt buộc phải là boolean")
        object.__setattr__(self, "coordinates", coordinates)
        object.__setattr__(self, "opening_windows", windows)


@dataclass(frozen=True)
class TravelMatrix:
    stop_ids: tuple[str, ...]
    duration_minutes: tuple[tuple[float | None, ...], ...]
    source: str

    def __post_init__(self) -> None:
        try:
            stop_ids = tuple(self.stop_ids)
        except TypeError as exc:
            raise ValueError("ID ma trận phải là một dãy") from exc
        if any(
            not isinstance(stop_id, str) or not stop_id.strip() for stop_id in stop_ids
        ):
            raise ValueError("ID ma trận không được để trống")
        if len(stop_ids) != len(set(stop_ids)):
            raise ValueError("ID ma trận không được trùng")
        try:
            rows = tuple(tuple(row) for row in self.duration_minutes)
        except TypeError as exc:
            raise ValueError("Ma trận thời gian phải là một dãy hai chiều") from exc
        size = len(rows)
        if len(stop_ids) != size:
            raise ValueError("Số ID phải khớp kích thước ma trận thời gian")
        if any(len(row) != size for row in rows):
            raise ValueError("Ma trận thời gian phải là ma trận vuông")
        for row_index, row in enumerate(rows):
            for column_index, value in enumerate(row):
                if value is None:
                    if row_index == column_index:
                        raise ValueError("Đường chéo ma trận thời gian phải bằng 0")
                    continue
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise ValueError("Thời gian di chuyển phải là số hoặc None")
                if not math.isfinite(value) or value < 0:
                    raise ValueError("Thời gian di chuyển phải hữu hạn và không âm")
                if row_index == column_index and value != 0:
                    raise ValueError("Đường chéo ma trận thời gian phải bằng 0")
        if not isinstance(self.source, str) or not self.source.strip():
            raise ValueError("Nguồn ma trận không được để trống")
        object.__setattr__(self, "stop_ids", stop_ids)
        object.__setattr__(self, "duration_minutes", rows)


@dataclass(frozen=True)
class ScheduleOptions:
    day_start_minute: int = 480
    day_end_minute: int = 1080
    exact_limit: int = 10
    beam_width: int = 64
    station_tolerance: float = 0.02
    deadline_seconds: float = 2.0
    blocked_edges: frozenset[tuple[str, str]] = frozenset()

    def __post_init__(self) -> None:
        TimeWindow(self.day_start_minute, self.day_end_minute)
        if not _is_int(self.exact_limit) or self.exact_limit < 0:
            raise ValueError("Ngưỡng giải chính xác không được âm")
        if not _is_int(self.beam_width) or self.beam_width < 1:
            raise ValueError("Độ rộng beam search phải lớn hơn 0")
        if (
            isinstance(self.station_tolerance, bool)
            or not isinstance(self.station_tolerance, (int, float))
            or not math.isfinite(self.station_tolerance)
            or self.station_tolerance < 0
        ):
            raise ValueError("Sai số tiến tuyến phải là số hữu hạn không âm")
        if (
            isinstance(self.deadline_seconds, bool)
            or not isinstance(self.deadline_seconds, (int, float))
            or not math.isfinite(self.deadline_seconds)
            or self.deadline_seconds <= 0
        ):
            raise ValueError("Thời hạn giải phải là số hữu hạn dương")
        try:
            raw_edges = tuple(self.blocked_edges)
        except TypeError as exc:
            raise ValueError("Cạnh bị cấm phải là cặp ID điểm dừng") from exc
        if any(
            not isinstance(edge, (tuple, list))
            or len(edge) != 2
            or any(not isinstance(stop_id, str) or not stop_id for stop_id in edge)
            for edge in raw_edges
        ):
            raise ValueError("Cạnh bị cấm phải là cặp ID điểm dừng")
        blocked_edges = frozenset(tuple(edge) for edge in raw_edges)
        object.__setattr__(self, "blocked_edges", blocked_edges)


@dataclass(frozen=True)
class SchedulePlacement:
    stop_id: str
    arrival_minute: float
    start_visit_minute: float
    finish_visit_minute: float


@dataclass(frozen=True)
class SkippedStop:
    stop_id: str
    reason: str


@dataclass(frozen=True)
class ScheduleResult:
    ordered_ids: tuple[str, ...]
    placements: tuple[SchedulePlacement, ...]
    skipped: tuple[SkippedStop, ...]
    total_travel_minutes: float
    waiting_minutes: float
    overtime_minutes: float
    minimum_slack_minutes: float
    geometric_distance_km: float
    backtrack_ratio: float
    solver: str
    matrix_source: str
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class _PreparedStop:
    stop: ScheduleStop
    original_index: int
    matrix_index: int
    station: float


@dataclass(frozen=True)
class _Label:
    path: tuple[int, ...]
    placements: tuple[SchedulePlacement, ...]
    finish_minute: float
    travel_minutes: float
    waiting_minutes: float
    minimum_slack_minutes: float


@dataclass(frozen=True)
class _SearchOutcome:
    label: _Label | None
    solver: str
    deadline_reached: bool


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _prepare_schedule(
    stops: Sequence[ScheduleStop],
    matrix: TravelMatrix,
    options: ScheduleOptions,
) -> tuple[tuple[_PreparedStop, ...], float]:
    schedule_stops = tuple(stops)
    matrix_indexes = _validate_schedule_inputs(schedule_stops, matrix, options)
    origin = schedule_stops[0].coordinates
    destination = schedule_stops[-1].coordinates
    corridor_length_km = haversine_km(origin, destination)
    return (
        _project_schedule_stops(
            schedule_stops,
            matrix_indexes,
            origin,
            destination,
        ),
        corridor_length_km,
    )


def _validate_schedule_inputs(
    schedule_stops: tuple[ScheduleStop, ...],
    matrix: TravelMatrix,
    options: ScheduleOptions,
) -> dict[str, int]:
    if not 2 <= len(schedule_stops) <= 20:
        raise ValueError("Lịch trình phải có từ 2 đến 20 điểm dừng")
    if any(not isinstance(stop, ScheduleStop) for stop in schedule_stops):
        raise ValueError("Lịch trình phải gồm các ScheduleStop")

    stop_ids = tuple(stop.id for stop in schedule_stops)
    if len(stop_ids) != len(set(stop_ids)):
        raise ValueError("ID điểm dừng không được trùng")
    if set(stop_ids) != set(matrix.stop_ids):
        raise ValueError("ID ma trận phải khớp chính xác các điểm dừng")

    known_ids = set(stop_ids)
    if any(
        source not in known_ids or target not in known_ids
        for source, target in options.blocked_edges
    ):
        raise ValueError("Cạnh bị cấm phải tham chiếu điểm dừng trong lịch trình")
    return {
        stop_id: matrix_index for matrix_index, stop_id in enumerate(matrix.stop_ids)
    }


def _project_schedule_stops(
    schedule_stops: tuple[ScheduleStop, ...],
    matrix_indexes: dict[str, int],
    origin: Coordinates,
    destination: Coordinates,
) -> tuple[_PreparedStop, ...]:
    prepared = []
    try:
        for original_index, stop in enumerate(schedule_stops):
            station = project_onto_corridor(
                origin,
                destination,
                stop.coordinates,
            ).station
            if original_index == 0:
                station = 0.0
            elif original_index == len(schedule_stops) - 1:
                station = 1.0
            prepared.append(
                _PreparedStop(
                    stop=stop,
                    original_index=original_index,
                    matrix_index=matrix_indexes[stop.id],
                    station=station,
                )
            )
    except NoFeasibleRouteError as exc:
        raise NoFeasibleScheduleError(str(exc)) from exc
    return tuple(prepared)


def _candidate_windows(
    stop: ScheduleStop,
    options: ScheduleOptions,
) -> tuple[TimeWindow, ...]:
    if stop.opening_windows:
        return tuple(
            sorted(
                stop.opening_windows,
                key=lambda window: (window.start_minute, window.end_minute),
            )
        )
    return (TimeWindow(options.day_start_minute, options.day_end_minute),)


def _place_stop(
    stop: ScheduleStop,
    arrival_minute: float,
    options: ScheduleOptions,
) -> tuple[SchedulePlacement, float, float] | None:
    for window in _candidate_windows(stop, options):
        start_visit = max(
            arrival_minute,
            options.day_start_minute,
            window.start_minute,
        )
        finish_visit = start_visit + stop.visit_minutes
        latest_finish = min(window.end_minute, options.day_end_minute)
        if finish_visit <= latest_finish:
            return (
                SchedulePlacement(
                    stop_id=stop.id,
                    arrival_minute=arrival_minute,
                    start_visit_minute=start_visit,
                    finish_visit_minute=finish_visit,
                ),
                start_visit - arrival_minute,
                latest_finish - finish_visit,
            )
    return None


def _initial_label(
    prepared: tuple[_PreparedStop, ...],
    options: ScheduleOptions,
) -> _Label | None:
    placed = _place_stop(
        prepared[0].stop,
        float(options.day_start_minute),
        options,
    )
    if placed is None:
        return None
    placement, waiting_minutes, slack_minutes = placed
    return _Label(
        path=(0,),
        placements=(placement,),
        finish_minute=placement.finish_visit_minute,
        travel_minutes=0.0,
        waiting_minutes=waiting_minutes,
        minimum_slack_minutes=slack_minutes,
    )


def _edge_allowed(
    source: _PreparedStop,
    target: _PreparedStop,
    options: ScheduleOptions,
) -> bool:
    if (source.stop.id, target.stop.id) in options.blocked_edges:
        return False
    return target.station + options.station_tolerance >= source.station


def _travel_minutes(
    source: _PreparedStop,
    target: _PreparedStop,
    matrix: TravelMatrix,
) -> float | None:
    duration = matrix.duration_minutes[source.matrix_index][target.matrix_index]
    return None if duration is None else float(duration)


def _extend_label(
    label: _Label,
    target_index: int,
    prepared: tuple[_PreparedStop, ...],
    matrix: TravelMatrix,
    options: ScheduleOptions,
) -> _Label | None:
    source = prepared[label.path[-1]]
    target = prepared[target_index]
    if not _edge_allowed(source, target, options):
        return None
    travel_minutes = _travel_minutes(source, target, matrix)
    if travel_minutes is None:
        return None

    arrival_minute = (
        float(options.day_start_minute)
        if label.path == (0,)
        else label.finish_minute + travel_minutes
    )
    placed = _place_stop(target.stop, arrival_minute, options)
    if placed is None:
        return None
    placement, waiting_minutes, slack_minutes = placed
    return _Label(
        path=label.path + (target_index,),
        placements=label.placements + (placement,),
        finish_minute=placement.finish_visit_minute,
        travel_minutes=label.travel_minutes + travel_minutes,
        waiting_minutes=label.waiting_minutes + waiting_minutes,
        minimum_slack_minutes=min(label.minimum_slack_minutes, slack_minutes),
    )


def _label_objective(label: _Label) -> tuple[float, float, float, tuple[int, ...]]:
    return (
        label.finish_minute,
        label.travel_minutes,
        -label.minimum_slack_minutes,
        label.path,
    )


def _dominates(left: _Label, right: _Label) -> bool:
    no_worse = (
        left.finish_minute <= right.finish_minute
        and left.travel_minutes <= right.travel_minutes
    )
    if not no_worse:
        return False
    strictly_better = (
        left.finish_minute < right.finish_minute
        or left.travel_minutes < right.travel_minutes
    )
    return strictly_better or _label_objective(left) <= _label_objective(right)


def _insert_nondominated(bucket: list[_Label], candidate: _Label) -> None:
    if any(_dominates(current, candidate) for current in bucket):
        return
    bucket[:] = [current for current in bucket if not _dominates(candidate, current)]
    bucket.append(candidate)
    bucket.sort(key=_label_objective)


def _deadline_reached(deadline: float) -> bool:
    return time.perf_counter() >= deadline


def _best_complete(labels: Sequence[_Label]) -> _Label | None:
    return min(labels, key=_label_objective) if labels else None


def _exact_initial_states(
    start_label: _Label,
    middle: tuple[int, ...],
    prepared: tuple[_PreparedStop, ...],
    matrix: TravelMatrix,
    options: ScheduleOptions,
    deadline: float,
) -> tuple[dict[tuple[int, int], list[_Label]], bool]:
    states: dict[tuple[int, int], list[_Label]] = {}
    for middle_position, stop_index in enumerate(middle):
        if _deadline_reached(deadline):
            return states, True
        candidate = _extend_label(
            start_label,
            stop_index,
            prepared,
            matrix,
            options,
        )
        if candidate is not None:
            states[(1 << middle_position, stop_index)] = [candidate]
    return states, False


def _expand_exact_label(
    label: _Label,
    mask: int,
    middle: tuple[int, ...],
    states: dict[tuple[int, int], list[_Label]],
    prepared: tuple[_PreparedStop, ...],
    matrix: TravelMatrix,
    options: ScheduleOptions,
) -> None:
    for next_position, next_index in enumerate(middle):
        bit = 1 << next_position
        if mask & bit:
            continue
        candidate = _extend_label(
            label,
            next_index,
            prepared,
            matrix,
            options,
        )
        if candidate is None:
            continue
        bucket = states.setdefault((mask | bit, next_index), [])
        _insert_nondominated(bucket, candidate)


def _solve_exact(
    prepared: tuple[_PreparedStop, ...],
    active_middle: tuple[int, ...],
    matrix: TravelMatrix,
    options: ScheduleOptions,
    deadline: float,
) -> _SearchOutcome:
    solver = "schedule-exact"
    start_label = _initial_label(prepared, options)
    if start_label is None:
        return _SearchOutcome(None, solver, False)
    destination_index = len(prepared) - 1
    if not active_middle:
        if _deadline_reached(deadline):
            return _SearchOutcome(None, solver, True)
        direct = _extend_label(
            start_label,
            destination_index,
            prepared,
            matrix,
            options,
        )
        return _SearchOutcome(direct, solver, False)

    states, timed_out = _exact_initial_states(
        start_label,
        active_middle,
        prepared,
        matrix,
        options,
        deadline,
    )
    if timed_out:
        return _SearchOutcome(None, solver, True)
    label, timed_out = _traverse_exact_states(
        states,
        active_middle,
        destination_index,
        prepared,
        matrix,
        options,
        deadline,
    )
    return _SearchOutcome(label, solver, timed_out)


def _traverse_exact_states(
    states: dict[tuple[int, int], list[_Label]],
    middle: tuple[int, ...],
    destination_index: int,
    prepared: tuple[_PreparedStop, ...],
    matrix: TravelMatrix,
    options: ScheduleOptions,
    deadline: float,
) -> tuple[_Label | None, bool]:
    completed: list[_Label] = []
    full_mask = (1 << len(middle)) - 1
    for mask in range(1, full_mask + 1):
        for last_index in middle:
            for label in tuple(states.get((mask, last_index), ())):
                if _deadline_reached(deadline):
                    return _best_complete(completed), True
                if mask == full_mask:
                    complete = _extend_label(
                        label,
                        destination_index,
                        prepared,
                        matrix,
                        options,
                    )
                    if complete is not None:
                        completed.append(complete)
                else:
                    _expand_exact_label(
                        label,
                        mask,
                        middle,
                        states,
                        prepared,
                        matrix,
                        options,
                    )
    return _best_complete(completed), False


def _beam_rank(label: _Label) -> tuple[int, float, float, float, tuple[int, ...]]:
    return (
        0,
        label.finish_minute,
        label.travel_minutes,
        -label.minimum_slack_minutes,
        label.path,
    )


def _expand_beam_level(
    frontier: Sequence[tuple[_Label, int]],
    middle: tuple[int, ...],
    prepared: tuple[_PreparedStop, ...],
    matrix: TravelMatrix,
    options: ScheduleOptions,
) -> list[tuple[_Label, int]]:
    expanded: list[tuple[_Label, int]] = []
    for label, mask in frontier:
        for next_position, next_index in enumerate(middle):
            bit = 1 << next_position
            if mask & bit:
                continue
            next_mask = mask | bit
            if _leaves_directionally_unreachable(
                next_index,
                next_mask,
                middle,
                prepared,
                options,
            ):
                continue
            candidate = _extend_label(
                label,
                next_index,
                prepared,
                matrix,
                options,
            )
            if candidate is not None:
                expanded.append((candidate, next_mask))
    expanded.sort(key=lambda state: _beam_rank(state[0]))
    return expanded[: options.beam_width]


def _leaves_directionally_unreachable(
    next_index: int,
    next_mask: int,
    middle: tuple[int, ...],
    prepared: tuple[_PreparedStop, ...],
    options: ScheduleOptions,
) -> bool:
    next_station = prepared[next_index].station
    return any(
        not next_mask & (1 << position)
        and prepared[index].station + options.station_tolerance < next_station
        for position, index in enumerate(middle)
    )


def _solve_beam(
    prepared: tuple[_PreparedStop, ...],
    active_middle: tuple[int, ...],
    matrix: TravelMatrix,
    options: ScheduleOptions,
    deadline: float,
) -> _SearchOutcome:
    solver = "schedule-beam"
    start_label = _initial_label(prepared, options)
    if start_label is None:
        return _SearchOutcome(None, solver, False)
    destination_index = len(prepared) - 1
    frontier: list[tuple[_Label, int]] = [(start_label, 0)]

    for _ in active_middle:
        if _deadline_reached(deadline):
            return _SearchOutcome(None, solver, True)
        frontier = _expand_beam_level(
            frontier,
            active_middle,
            prepared,
            matrix,
            options,
        )
        if not frontier:
            return _SearchOutcome(None, solver, False)

    completed: list[_Label] = []
    for label, _ in frontier:
        if _deadline_reached(deadline):
            return _SearchOutcome(_best_complete(completed), solver, True)
        complete = _extend_label(
            label,
            destination_index,
            prepared,
            matrix,
            options,
        )
        if complete is not None:
            completed.append(complete)
    return _SearchOutcome(_best_complete(completed), solver, False)


def _solve_route(
    prepared: tuple[_PreparedStop, ...],
    active_middle: tuple[int, ...],
    matrix: TravelMatrix,
    options: ScheduleOptions,
    deadline: float,
) -> _SearchOutcome:
    if len(active_middle) <= options.exact_limit:
        return _solve_exact(prepared, active_middle, matrix, options, deadline)
    return _solve_beam(prepared, active_middle, matrix, options, deadline)


def _local_candidates(path: tuple[int, ...]):
    for index in range(1, len(path) - 2):
        candidate = list(path)
        candidate[index], candidate[index + 1] = (
            candidate[index + 1],
            candidate[index],
        )
        yield tuple(candidate)

    for source in range(1, len(path) - 1):
        for destination in range(1, len(path) - 1):
            if source == destination:
                continue
            candidate = list(path)
            moved = candidate.pop(source)
            candidate.insert(destination, moved)
            yield tuple(candidate)

    for source in range(1, len(path) - 2):
        segment = path[source : source + 2]
        remainder = path[:source] + path[source + 2 :]
        for destination in range(1, len(remainder)):
            yield remainder[:destination] + segment + remainder[destination:]


def _evaluate_path(
    path: tuple[int, ...],
    prepared: tuple[_PreparedStop, ...],
    matrix: TravelMatrix,
    options: ScheduleOptions,
) -> _Label | None:
    label = _initial_label(prepared, options)
    if label is None or path[0] != 0 or path[-1] != len(prepared) - 1:
        return None
    for target_index in path[1:]:
        label = _extend_label(label, target_index, prepared, matrix, options)
        if label is None:
            return None
    return label


def _repair_route(
    initial: _Label,
    prepared: tuple[_PreparedStop, ...],
    matrix: TravelMatrix,
    options: ScheduleOptions,
    deadline: float,
) -> tuple[_Label, bool]:
    best = initial
    for _ in range(4):
        improved = best
        for path in _local_candidates(best.path):
            if _deadline_reached(deadline):
                return best, True
            candidate = _evaluate_path(path, prepared, matrix, options)
            if candidate is not None and _label_objective(candidate) < _label_objective(
                improved
            ):
                improved = candidate
        if improved.path == best.path:
            break
        best = improved
    return best, False


def _optional_burden(
    stop_index: int,
    prepared: tuple[_PreparedStop, ...],
    matrix: TravelMatrix,
) -> float:
    matrix_index = prepared[stop_index].matrix_index
    incident = []
    for other_index in range(len(matrix.stop_ids)):
        if other_index == matrix_index:
            continue
        outbound = matrix.duration_minutes[matrix_index][other_index]
        inbound = matrix.duration_minutes[other_index][matrix_index]
        if outbound is not None:
            incident.append(float(outbound))
        if inbound is not None:
            incident.append(float(inbound))
    shortest_incident = min(incident) if incident else math.inf
    return prepared[stop_index].stop.visit_minutes + shortest_incident


def _optional_drop_order(
    prepared: tuple[_PreparedStop, ...],
    matrix: TravelMatrix,
) -> tuple[int, ...]:
    optional = [
        index
        for index in range(1, len(prepared) - 1)
        if not prepared[index].stop.required
    ]
    return tuple(
        sorted(
            optional,
            key=lambda index: (
                -_optional_burden(index, prepared, matrix),
                prepared[index].original_index,
            ),
        )
    )


def _first_required_blocker(
    prepared: tuple[_PreparedStop, ...],
    matrix: TravelMatrix,
    options: ScheduleOptions,
) -> str:
    if _initial_label(prepared, options) is None:
        return prepared[0].stop.id
    destination_index = len(prepared) - 1
    required_middle = tuple(
        index for index in range(1, destination_index) if prepared[index].stop.required
    )
    for index in required_middle:
        if (
            _evaluate_path(
                (0, index, destination_index),
                prepared,
                matrix,
                options,
            )
            is None
        ):
            return prepared[index].stop.id
    if required_middle:
        return prepared[required_middle[0]].stop.id
    return prepared[destination_index].stop.id


def _path_geometry(
    path: tuple[int, ...],
    prepared: tuple[_PreparedStop, ...],
    corridor_length_km: float,
) -> tuple[float, float]:
    geometric_distance_km = sum(
        haversine_km(
            prepared[source].stop.coordinates,
            prepared[target].stop.coordinates,
        )
        for source, target in zip(path, path[1:])
    )
    backward_progress_km = sum(
        max(0.0, prepared[source].station - prepared[target].station)
        * corridor_length_km
        for source, target in zip(path, path[1:])
    )
    if backward_progress_km < 1e-12:
        return geometric_distance_km, 0.0
    return (
        geometric_distance_km,
        backward_progress_km / max(geometric_distance_km, 1e-12),
    )


def _build_schedule_result(
    label: _Label,
    skipped: tuple[SkippedStop, ...],
    solver: str,
    matrix: TravelMatrix,
    prepared: tuple[_PreparedStop, ...],
    corridor_length_km: float,
    options: ScheduleOptions,
    deadline_reached: bool,
) -> ScheduleResult:
    geometric_distance_km, backtrack_ratio = _path_geometry(
        label.path,
        prepared,
        corridor_length_km,
    )
    warnings = ("schedule-deadline-reached",) if deadline_reached else ()
    return ScheduleResult(
        ordered_ids=tuple(prepared[index].stop.id for index in label.path),
        placements=label.placements,
        skipped=skipped,
        total_travel_minutes=label.travel_minutes,
        waiting_minutes=label.waiting_minutes,
        overtime_minutes=max(0.0, label.finish_minute - options.day_end_minute),
        minimum_slack_minutes=label.minimum_slack_minutes,
        geometric_distance_km=geometric_distance_km,
        backtrack_ratio=backtrack_ratio,
        solver=solver,
        matrix_source=matrix.source,
        warnings=warnings,
    )


def _solve_with_optional_drops(
    prepared: tuple[_PreparedStop, ...],
    matrix: TravelMatrix,
    options: ScheduleOptions,
    deadline: float,
) -> tuple[_SearchOutcome, tuple[SkippedStop, ...]]:
    active_middle = tuple(range(1, len(prepared) - 1))
    outcome = _solve_route(prepared, active_middle, matrix, options, deadline)
    skipped: list[SkippedStop] = []
    if outcome.label is not None or outcome.deadline_reached:
        return outcome, ()

    for optional_index in _optional_drop_order(prepared, matrix):
        active_middle = tuple(
            index for index in active_middle if index != optional_index
        )
        skipped.append(
            SkippedStop(
                prepared[optional_index].stop.id,
                "day-window-overflow",
            )
        )
        outcome = _solve_route(prepared, active_middle, matrix, options, deadline)
        if outcome.label is not None or outcome.deadline_reached:
            break
    return outcome, tuple(skipped)


def schedule_stop_order(
    stops: Sequence[ScheduleStop],
    matrix: TravelMatrix,
    options: ScheduleOptions = ScheduleOptions(),
) -> ScheduleResult:
    """Schedule fixed-endpoint stops within hard travel and opening windows."""
    prepared, corridor_length_km = _prepare_schedule(stops, matrix, options)
    deadline = time.perf_counter() + options.deadline_seconds
    outcome, skipped = _solve_with_optional_drops(prepared, matrix, options, deadline)

    if outcome.label is None:
        blocker = _first_required_blocker(prepared, matrix, options)
        raise NoFeasibleScheduleError(
            f"Không tìm thấy lịch trình khả thi; điểm chặn đầu tiên: {blocker}"
        )

    repaired, repair_timed_out = _repair_route(
        outcome.label,
        prepared,
        matrix,
        options,
        deadline,
    )
    return _build_schedule_result(
        repaired,
        skipped,
        outcome.solver,
        matrix,
        prepared,
        corridor_length_km,
        options,
        outcome.deadline_reached or repair_timed_out,
    )


def _minute_of_day(hour_text: str, minute_text: str | None) -> int | None:
    hour = int(hour_text)
    minute = int(minute_text or 0)
    if hour > 24 or minute > 59 or (hour == 24 and minute != 0):
        return None
    return hour * 60 + minute


def _window_from_match(match: re.Match[str]) -> TimeWindow | None:
    start = _minute_of_day(
        match.group("start_hour"),
        match.group("start_colon_minute") or match.group("start_h_minute"),
    )
    end = _minute_of_day(
        match.group("end_hour"),
        match.group("end_colon_minute") or match.group("end_h_minute"),
    )
    if start is None or end is None or start > end:
        return None
    return TimeWindow(start, end)


def parse_time_range(text: str | None) -> TimeWindow | None:
    """Parse one supported local time range, returning None when untrusted."""
    if not isinstance(text, str):
        return None
    match = _TIME_RANGE_PATTERN.fullmatch(text.strip())
    if match is None:
        return None
    return _window_from_match(match)


def parse_opening_hours(
    text: str | None,
) -> tuple[tuple[TimeWindow, ...], tuple[str, ...]]:
    """Extract trusted time ranges and nonfatal parsing warnings."""
    warnings: list[str] = []
    if not isinstance(text, str):
        return (), ("opening-hours-unknown",)

    if _WEEKDAY_PREFIX_PATTERN.search(text):
        warnings.append("weekday-specific-hours-ignored")
        text = _WEEKDAY_PREFIX_PATTERN.sub(" ", text)

    windows = tuple(
        window
        for match in _TIME_RANGE_PATTERN.finditer(text)
        if (window := _window_from_match(match)) is not None
    )
    if not windows:
        warnings.append("opening-hours-unknown")
    return windows, tuple(warnings)


def infer_visit_minutes(
    entity_type: str | None,
    explicit_minutes: int | None,
    suggested_duration: str | None,
) -> int:
    """Infer visit duration from explicit data, free text, then type defaults."""
    if explicit_minutes is not None:
        return explicit_minutes

    if isinstance(suggested_duration, str):
        hours_match = _HOURS_PATTERN.search(suggested_duration)
        minutes_match = _MINUTES_PATTERN.search(suggested_duration)
        if hours_match is not None or minutes_match is not None:
            hours = _duration_number(hours_match) if hours_match is not None else 0.0
            minutes = (
                _duration_number(minutes_match) if minutes_match is not None else 0.0
            )
            return int(round(hours * 60 + minutes))

    normalized_type = (
        entity_type.strip().lower() if isinstance(entity_type, str) else ""
    )
    return _TYPE_DEFAULT_MINUTES.get(normalized_type, 60)


def _duration_number(match: re.Match[str]) -> float:
    return float(match.group("value").replace(",", "."))


def build_fallback_matrix(
    stops: Sequence[ScheduleStop],
    mode: str,
) -> TravelMatrix:
    """Build a symmetric local travel-time matrix from Haversine distances."""
    try:
        speed_kmh = _MODE_SPEED_KMH[mode]
    except KeyError as exc:
        raise ValueError(f"Unsupported travel mode: {mode}") from exc

    size = len(stops)
    durations = [[0.0 for _ in range(size)] for _ in range(size)]
    for source_index, source in enumerate(stops):
        for target_index in range(source_index + 1, size):
            target = stops[target_index]
            duration = (
                haversine_km(source.coordinates, target.coordinates) / speed_kmh * 60.0
            )
            durations[source_index][target_index] = duration
            durations[target_index][source_index] = duration
    return TravelMatrix(
        tuple(stop.id for stop in stops),
        tuple(tuple(row) for row in durations),
        "haversine-fallback",
    )


__all__ = [
    "NoFeasibleScheduleError",
    "ScheduleOptions",
    "SchedulePlacement",
    "ScheduleResult",
    "ScheduleStop",
    "SkippedStop",
    "TimeWindow",
    "TravelMatrix",
    "build_fallback_matrix",
    "infer_visit_minutes",
    "parse_opening_hours",
    "parse_time_range",
    "schedule_stop_order",
]
