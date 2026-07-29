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

    project_onto_corridor(stops[0].coordinates, stops[-1].coordinates, stops[0].coordinates)
    distance = _path_distance_km(stops)
    if len(stops) > 2:
        raise NoFeasibleRouteError("Chưa có bộ giải cho các điểm trung gian")

    if (stops[0].id, stops[1].id) in options.blocked_edges:
        raise NoFeasibleRouteError("Không tìm thấy thứ tự điểm dừng hợp lệ")

    return OptimizeResult(
        ordered_ids=tuple(stop_ids),
        distance_before_km=distance,
        distance_after_km=distance,
        backtrack_ratio=0.0,
        solver="exact-dp",
        warnings=(),
    )
