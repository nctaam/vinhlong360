"""Deterministic, dependency-free optimization for forward itineraries."""

from __future__ import annotations

from dataclasses import dataclass
import math


EARTH_RADIUS_KM = 6371.0088
MIN_CORRIDOR_KM = 0.02

Coordinates = tuple[float, float]


class NoFeasibleRouteError(ValueError):
    """Raised when the requested directional route cannot be constructed."""


@dataclass(frozen=True)
class RouteStop:
    id: str
    coordinates: Coordinates

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("ID điểm dừng không được để trống")
        if len(self.coordinates) != 2:
            raise ValueError("Tọa độ phải gồm vĩ độ và kinh độ")
        lat, lng = self.coordinates
        if not math.isfinite(lat) or not math.isfinite(lng):
            raise ValueError("Tọa độ phải là số hữu hạn")
        if not -90 <= lat <= 90:
            raise ValueError("Vĩ độ phải nằm trong khoảng [-90, 90]")
        if not -180 <= lng <= 180:
            raise ValueError("Kinh độ phải nằm trong khoảng [-180, 180]")


@dataclass(frozen=True)
class OptimizeOptions:
    strict_direction: bool = True
    station_tolerance: float = 0.02
    exact_limit: int = 10
    beam_width: int = 64
    blocked_edges: frozenset[tuple[str, str]] = frozenset()

    def __post_init__(self) -> None:
        if not math.isfinite(self.station_tolerance) or self.station_tolerance < 0:
            raise ValueError("Sai số tiến tuyến phải là số hữu hạn không âm")
        if self.exact_limit < 0:
            raise ValueError("Ngưỡng giải chính xác không được âm")
        if self.beam_width < 1:
            raise ValueError("Độ rộng beam search phải lớn hơn 0")


@dataclass(frozen=True)
class OptimizeResult:
    ordered_ids: tuple[str, ...]
    distance_before_km: float
    distance_after_km: float
    backtrack_ratio: float
    solver: str
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class Projection:
    station: float
    lateral_km: float


@dataclass(frozen=True)
class _PreparedStop:
    stop: RouteStop
    original_index: int
    projection: Projection


_ExactState = tuple[float, tuple[int, ...]]
_BeamState = tuple[float, tuple[int, ...], int, int]


def haversine_km(a: Coordinates, b: Coordinates) -> float:
    """Return great-circle distance in kilometers."""
    lat1, lng1 = map(math.radians, a)
    lat2, lng2 = map(math.radians, b)
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    h = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    )
    return EARTH_RADIUS_KM * 2 * math.asin(min(1.0, math.sqrt(h)))


def _local_xy_km(origin: Coordinates, point: Coordinates, ref_lat_rad: float) -> tuple[float, float]:
    lat0, lng0 = map(math.radians, origin)
    lat, lng = map(math.radians, point)
    return (
        EARTH_RADIUS_KM * (lng - lng0) * math.cos(ref_lat_rad),
        EARTH_RADIUS_KM * (lat - lat0),
    )


def project_onto_corridor(
    origin: Coordinates,
    destination: Coordinates,
    point: Coordinates,
) -> Projection:
    """Project a point onto the directed origin-to-destination corridor."""
    ref_lat_rad = math.radians((origin[0] + destination[0]) / 2)
    corridor_x, corridor_y = _local_xy_km(origin, destination, ref_lat_rad)
    corridor_length_sq = corridor_x ** 2 + corridor_y ** 2
    if corridor_length_sq < MIN_CORRIDOR_KM ** 2:
        raise NoFeasibleRouteError(
            "Điểm đầu và điểm cuối quá gần, không xác định được hướng tuyến"
        )

    point_x, point_y = _local_xy_km(origin, point, ref_lat_rad)
    station = (point_x * corridor_x + point_y * corridor_y) / corridor_length_sq
    lateral_km = abs(point_x * corridor_y - point_y * corridor_x) / math.sqrt(corridor_length_sq)
    return Projection(station=station, lateral_km=lateral_km)


def _path_distance_km(stops: list[RouteStop]) -> float:
    return sum(
        haversine_km(source.coordinates, target.coordinates)
        for source, target in zip(stops, stops[1:])
    )


def _prepare_stops(stops: list[RouteStop]) -> tuple[list[_PreparedStop], float]:
    origin = stops[0].coordinates
    destination = stops[-1].coordinates
    corridor_length_km = haversine_km(origin, destination)
    prepared = []
    for index, route_stop in enumerate(stops):
        projection = project_onto_corridor(origin, destination, route_stop.coordinates)
        if index == 0:
            projection = Projection(station=0.0, lateral_km=0.0)
        elif index == len(stops) - 1:
            projection = Projection(station=1.0, lateral_km=0.0)
        prepared.append(_PreparedStop(route_stop, index, projection))
    return prepared, corridor_length_km


def _edge_allowed(
    source: _PreparedStop,
    target: _PreparedStop,
    options: OptimizeOptions,
) -> bool:
    if (source.stop.id, target.stop.id) in options.blocked_edges:
        return False
    if (
        options.strict_direction
        and target.projection.station + options.station_tolerance
        < source.projection.station
    ):
        return False
    return True


def _edge_cost(
    source: _PreparedStop,
    target: _PreparedStop,
    corridor_length_km: float,
) -> float:
    distance = haversine_km(source.stop.coordinates, target.stop.coordinates)
    backward_progress_km = max(
        0.0,
        source.projection.station - target.projection.station,
    ) * corridor_length_km
    lateral_escape_km = abs(
        source.projection.lateral_km - target.projection.lateral_km
    )
    return distance + 2.0 * backward_progress_km + 0.15 * lateral_escape_km


def _path_cost(
    path: tuple[int, ...],
    prepared: list[_PreparedStop],
    corridor_length_km: float,
) -> float:
    return sum(
        _edge_cost(prepared[source], prepared[target], corridor_length_km)
        for source, target in zip(path, path[1:])
    )


def _path_is_allowed(
    path: tuple[int, ...],
    prepared: list[_PreparedStop],
    options: OptimizeOptions,
) -> bool:
    return all(
        _edge_allowed(prepared[source], prepared[target], options)
        for source, target in zip(path, path[1:])
    )


def _prefer_candidate(
    candidate_cost: float,
    candidate_path: tuple[int, ...],
    current: tuple[float, tuple[int, ...]] | None,
) -> bool:
    if current is None:
        return True
    current_cost, current_path = current
    if candidate_cost < current_cost - 1e-9:
        return True
    return abs(candidate_cost - current_cost) <= 1e-9 and candidate_path < current_path


def _initial_exact_states(
    prepared: list[_PreparedStop],
    middle: tuple[int, ...],
    options: OptimizeOptions,
    corridor_length_km: float,
) -> dict[tuple[int, int], _ExactState]:
    states: dict[tuple[int, int], _ExactState] = {}
    for middle_position, stop_index in enumerate(middle):
        if not _edge_allowed(prepared[0], prepared[stop_index], options):
            continue
        mask = 1 << middle_position
        path = (0, stop_index)
        states[(mask, middle_position)] = (
            _path_cost(path, prepared, corridor_length_km),
            path,
        )
    return states


def _expand_exact_state(
    states: dict[tuple[int, int], _ExactState],
    mask: int,
    last_position: int,
    last_index: int,
    middle: tuple[int, ...],
    prepared: list[_PreparedStop],
    options: OptimizeOptions,
    corridor_length_km: float,
) -> None:
    state = states.get((mask, last_position))
    if state is None:
        return
    state_cost, state_path = state
    for next_position, next_index in enumerate(middle):
        bit = 1 << next_position
        if mask & bit or not _edge_allowed(
            prepared[last_index], prepared[next_index], options
        ):
            continue
        next_mask = mask | bit
        next_path = state_path + (next_index,)
        next_cost = state_cost + _edge_cost(
            prepared[last_index],
            prepared[next_index],
            corridor_length_km,
        )
        key = (next_mask, next_position)
        if _prefer_candidate(next_cost, next_path, states.get(key)):
            states[key] = (next_cost, next_path)


def _expand_exact_states(
    states: dict[tuple[int, int], _ExactState],
    middle: tuple[int, ...],
    prepared: list[_PreparedStop],
    options: OptimizeOptions,
    corridor_length_km: float,
) -> None:
    full_mask = (1 << len(middle)) - 1
    for mask in range(1, full_mask + 1):
        for last_position, last_index in enumerate(middle):
            _expand_exact_state(
                states,
                mask,
                last_position,
                last_index,
                middle,
                prepared,
                options,
                corridor_length_km,
            )


def _finish_exact_path(
    states: dict[tuple[int, int], _ExactState],
    middle: tuple[int, ...],
    destination_index: int,
    prepared: list[_PreparedStop],
    options: OptimizeOptions,
    corridor_length_km: float,
) -> tuple[int, ...]:
    full_mask = (1 << len(middle)) - 1
    best: _ExactState | None = None
    for last_position, last_index in enumerate(middle):
        state = states.get((full_mask, last_position))
        if state is None:
            continue
        if not _edge_allowed(
            prepared[last_index], prepared[destination_index], options
        ):
            continue
        state_cost, state_path = state
        final_path = state_path + (destination_index,)
        final_cost = state_cost + _edge_cost(
            prepared[last_index],
            prepared[destination_index],
            corridor_length_km,
        )
        if _prefer_candidate(final_cost, final_path, best):
            best = (final_cost, final_path)

    if best is None:
        raise NoFeasibleRouteError("Không tìm thấy thứ tự điểm dừng hợp lệ")
    return best[1]


def _solve_exact(
    prepared: list[_PreparedStop],
    options: OptimizeOptions,
    corridor_length_km: float,
) -> tuple[int, ...]:
    destination_index = len(prepared) - 1
    middle = tuple(range(1, destination_index))
    if not middle:
        direct = (0, destination_index)
        if _path_is_allowed(direct, prepared, options):
            return direct
        raise NoFeasibleRouteError("Không tìm thấy thứ tự điểm dừng hợp lệ")

    states = _initial_exact_states(
        prepared, middle, options, corridor_length_km
    )
    _expand_exact_states(
        states, middle, prepared, options, corridor_length_km
    )
    return _finish_exact_path(
        states,
        middle,
        destination_index,
        prepared,
        options,
        corridor_length_km,
    )


def _leaves_unreachable_stop(
    next_index: int,
    remaining: tuple[int, ...],
    prepared: list[_PreparedStop],
    options: OptimizeOptions,
) -> bool:
    if not options.strict_direction:
        return False
    next_station = prepared[next_index].projection.station
    return any(
        prepared[index].projection.station + options.station_tolerance < next_station
        for index in remaining
    )


def _expand_beam_state(
    state: _BeamState,
    middle: tuple[int, ...],
    prepared: list[_PreparedStop],
    options: OptimizeOptions,
    corridor_length_km: float,
) -> list[_BeamState]:
    state_cost, state_path, mask, last_index = state
    expanded: list[_BeamState] = []
    for next_position, next_index in enumerate(middle):
        bit = 1 << next_position
        if mask & bit or not _edge_allowed(
            prepared[last_index], prepared[next_index], options
        ):
            continue
        next_mask = mask | bit
        remaining = tuple(
            index
            for position, index in enumerate(middle)
            if not next_mask & (1 << position)
        )
        if _leaves_unreachable_stop(next_index, remaining, prepared, options):
            continue
        next_cost = state_cost + _edge_cost(
            prepared[last_index],
            prepared[next_index],
            corridor_length_km,
        )
        expanded.append((
            next_cost,
            state_path + (next_index,),
            next_mask,
            next_index,
        ))
    return expanded


def _expand_beam_states(
    states: list[_BeamState],
    middle: tuple[int, ...],
    prepared: list[_PreparedStop],
    options: OptimizeOptions,
    corridor_length_km: float,
) -> list[_BeamState]:
    return [
        candidate
        for state in states
        for candidate in _expand_beam_state(
            state, middle, prepared, options, corridor_length_km
        )
    ]


def _beam_state_priority(
    state: _BeamState,
    prepared: list[_PreparedStop],
    destination_index: int,
) -> tuple[float, float, tuple[int, ...]]:
    state_cost, state_path, _mask, last_index = state
    remaining_distance = haversine_km(
        prepared[last_index].stop.coordinates,
        prepared[destination_index].stop.coordinates,
    )
    return state_cost + remaining_distance, state_cost, state_path


def _finish_beam_path(
    states: list[_BeamState],
    full_mask: int,
    destination_index: int,
    prepared: list[_PreparedStop],
    options: OptimizeOptions,
    corridor_length_km: float,
) -> tuple[int, ...]:
    best: _ExactState | None = None
    for state_cost, state_path, mask, last_index in states:
        if mask != full_mask:
            continue
        if not _edge_allowed(
            prepared[last_index], prepared[destination_index], options
        ):
            continue
        final_path = state_path + (destination_index,)
        final_cost = state_cost + _edge_cost(
            prepared[last_index],
            prepared[destination_index],
            corridor_length_km,
        )
        if _prefer_candidate(final_cost, final_path, best):
            best = (final_cost, final_path)

    if best is None:
        raise NoFeasibleRouteError("Không tìm thấy thứ tự điểm dừng hợp lệ")
    return best[1]


def _solve_beam(
    prepared: list[_PreparedStop],
    options: OptimizeOptions,
    corridor_length_km: float,
) -> tuple[int, ...]:
    destination_index = len(prepared) - 1
    middle = tuple(range(1, destination_index))
    full_mask = (1 << len(middle)) - 1
    states: list[_BeamState] = [(0.0, (0,), 0, 0)]

    for _ in middle:
        expanded = _expand_beam_states(
            states, middle, prepared, options, corridor_length_km
        )
        if not expanded:
            raise NoFeasibleRouteError("Không tìm thấy thứ tự điểm dừng hợp lệ")
        expanded.sort(
            key=lambda state: _beam_state_priority(
                state, prepared, destination_index
            )
        )
        states = expanded[:options.beam_width]

    return _finish_beam_path(
        states,
        full_mask,
        destination_index,
        prepared,
        options,
        corridor_length_km,
    )


def _local_candidates(path: tuple[int, ...]):
    for index in range(1, len(path) - 2):
        candidate = list(path)
        candidate[index], candidate[index + 1] = candidate[index + 1], candidate[index]
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
        segment = path[source:source + 2]
        remainder = path[:source] + path[source + 2:]
        for destination in range(1, len(remainder)):
            yield remainder[:destination] + segment + remainder[destination:]


def _improve_path(
    path: tuple[int, ...],
    prepared: list[_PreparedStop],
    options: OptimizeOptions,
    corridor_length_km: float,
) -> tuple[int, ...]:
    best_path = path
    best_cost = _path_cost(path, prepared, corridor_length_km)
    for _ in range(4):
        improved_path = best_path
        improved_cost = best_cost
        for candidate in _local_candidates(best_path):
            if not _path_is_allowed(candidate, prepared, options):
                continue
            candidate_cost = _path_cost(candidate, prepared, corridor_length_km)
            if candidate_cost < improved_cost - 1e-9:
                improved_path = candidate
                improved_cost = candidate_cost
        if improved_path == best_path:
            break
        best_path = improved_path
        best_cost = improved_cost
    return best_path


def _backtrack_ratio(
    path: tuple[int, ...],
    prepared: list[_PreparedStop],
    corridor_length_km: float,
    route_distance_km: float,
) -> float:
    backward_progress_km = sum(
        max(
            0.0,
            prepared[source].projection.station
            - prepared[target].projection.station,
        ) * corridor_length_km
        for source, target in zip(path, path[1:])
    )
    if backward_progress_km < 1e-12:
        return 0.0
    return backward_progress_km / max(route_distance_km, 1e-12)


def optimize_stop_order(
    stops: list[RouteStop],
    options: OptimizeOptions = OptimizeOptions(),
) -> OptimizeResult:
    """Validate stops and optimize their order along a directed corridor."""
    if not 2 <= len(stops) <= 20:
        raise ValueError("Lịch trình phải có từ 2 đến 20 điểm dừng")

    stop_ids = [stop.id for stop in stops]
    if len(stop_ids) != len(set(stop_ids)):
        raise ValueError("ID điểm dừng không được trùng")

    known_ids = set(stop_ids)
    if any(
        source not in known_ids or target not in known_ids
        for source, target in options.blocked_edges
    ):
        raise ValueError("Cạnh bị cấm phải tham chiếu điểm dừng có trong lịch trình")

    prepared, corridor_length_km = _prepare_stops(stops)
    middle_count = len(stops) - 2
    if middle_count <= options.exact_limit:
        path = _solve_exact(prepared, options, corridor_length_km)
        solver = "exact-dp"
    else:
        path = _solve_beam(prepared, options, corridor_length_km)
        solver = "beam-search"
    path = _improve_path(path, prepared, options, corridor_length_km)

    ordered_stops = [prepared[index].stop for index in path]
    distance_before_km = _path_distance_km(stops)
    distance_after_km = _path_distance_km(ordered_stops)

    return OptimizeResult(
        ordered_ids=tuple(stop.id for stop in ordered_stops),
        distance_before_km=distance_before_km,
        distance_after_km=distance_after_km,
        backtrack_ratio=_backtrack_ratio(
            path,
            prepared,
            corridor_length_km,
            distance_after_km,
        ),
        solver=solver,
        warnings=(),
    )
