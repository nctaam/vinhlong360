"""Dependency-free time contracts and local travel-time estimation."""

from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Sequence

from itinerary_optimizer import Coordinates, RouteStop, haversine_km


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
        object.__setattr__(self, "coordinates", coordinates)
        object.__setattr__(self, "opening_windows", windows)


@dataclass(frozen=True)
class TravelMatrix:
    duration_minutes: tuple[tuple[float | None, ...], ...]
    source: str

    def __post_init__(self) -> None:
        try:
            rows = tuple(tuple(row) for row in self.duration_minutes)
        except TypeError as exc:
            raise ValueError("Ma trận thời gian phải là một dãy hai chiều") from exc
        size = len(rows)
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
        object.__setattr__(self, "duration_minutes", rows)


@dataclass(frozen=True)
class ScheduleOptions:
    day_start_minute: int = 480
    day_end_minute: int = 1080
    exact_limit: int = 10
    beam_width: int = 64
    station_tolerance: float = 0.02
    deadline_seconds: float = 2.0

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


@dataclass(frozen=True)
class SchedulePlacement:
    stop_id: str
    arrival_minute: float
    start_minute: float
    end_minute: float


@dataclass(frozen=True)
class SkippedStop:
    stop_id: str
    reason: str


@dataclass(frozen=True)
class ScheduleResult:
    placements: tuple[SchedulePlacement, ...]
    skipped: tuple[SkippedStop, ...]
    total_travel_minutes: float
    solver: str
    matrix_source: str
    warnings: tuple[str, ...]


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


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

    normalized_type = entity_type.strip().lower() if isinstance(entity_type, str) else ""
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
                haversine_km(source.coordinates, target.coordinates)
                / speed_kmh
                * 60.0
            )
            durations[source_index][target_index] = duration
            durations[target_index][source_index] = duration
    return TravelMatrix(
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
]
