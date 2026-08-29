# -*- coding: utf-8 -*-
"""Miền LỊCH TRÌNH — mặt công khai. Bóc khỏi `public_api.py` (2026-08-29, lát 2
đợt cắt module; hồ sơ đo: journal wf_3f293d24-0a1, kết quả itineraries-routes).

Gói `agent/itineraries/` đã chứa tầng service (5 module itinerary_*, gom cơ học
6ee7f2e4); lát này đưa nốt TẦNG ROUTE về cùng mái theo khuôn hai-mặt
`agent/entities/`: 3 route public (optimize-order, list, get) + cụm validation/
serialize/schedule đi kèm — bao đóng bắc cầu, di chuyển NGUYÊN VĂN.

Mount qua `public_api.router.include_router(...)` TRƯỚC `_fix_route_order()`:
- cổng R20.9 chỉ nhìn thấy mount qua lời gọi include_router;
- router cha mang prefix "/api" — router này KHÔNG tự mang (tự mang nữa là
  /api/api/itineraries, bài đo của entities/api.py).

Hai helper stop dùng chung với homepage của public_api
(`_itinerary_stop_entity_id`, `_public_itinerary_stops`) đã về `entity_read.py`
ở bước 1a — gói này KHÔNG import ngược public_api (test_itineraries_boundary.py
cấm mọi import server/admin/public_api/entities/... trong gói).
"""
from __future__ import annotations

import asyncio
import logging
import math
from collections import Counter
from dataclasses import asdict
from typing import Literal, Optional

from fastapi import APIRouter, Query, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator, model_validator

from auth_middleware import validate_path_id
from database import db
from entity_read import (
    _err,
    _get_public_entities_batch,
    _itinerary_stop_entity_id,
    _public_itinerary_stops,
)

# Import TƯƠNG ĐỐI trong cùng gói — an toàn cả hai chế độ nạp (`itineraries.api`
# lẫn `agent.itineraries.api`); leaf hạ tầng thì import phẳng như entities/api.py.
from .itinerary_optimizer import (
    haversine_km,
    NoFeasibleRouteError,
    OptimizeOptions,
    RouteStop,
    optimize_stop_order,
)
from .itinerary_schedule import (
    NoFeasibleScheduleError,
    ScheduleOptions,
    ScheduleStop,
    TimeWindow,
    TravelMatrix,
    build_fallback_matrix,
    parse_opening_hours,
    parse_time_range,
    schedule_stop_order,
)

logger = logging.getLogger(__name__)
# KHÔNG tự mang prefix: mount qua public_api.router (prefix "/api").
router = APIRouter(tags=["itineraries"])


def _validate_itinerary_stop_id(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("ID điểm dừng không được để trống")
    return value


def _validate_duration_matrix_values(value):
    if value is None:
        return value
    if not isinstance(value, list) or any(not isinstance(row, list) for row in value):
        raise ValueError("Ma trận thời gian phải là một dãy hai chiều")
    if any(
        cell is not None
        and (
            isinstance(cell, bool)
            or not isinstance(cell, (int, float))
            or not math.isfinite(cell)
            or cell < 0
        )
        for row in value
        for cell in row
    ):
        raise ValueError("Thời gian di chuyển phải hữu hạn, không âm hoặc null")
    return value


class ItineraryOptimizeStopIn(BaseModel):
    id: str = Field(min_length=1, max_length=200)
    coordinates: tuple[float, float]

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        return _validate_itinerary_stop_id(value)

    @field_validator("coordinates")
    @classmethod
    def validate_coordinates(cls, value: tuple[float, float]) -> tuple[float, float]:
        lat, lng = value
        if not math.isfinite(lat) or not math.isfinite(lng):
            raise ValueError("Tọa độ phải là số hữu hạn")
        if not -90 <= lat <= 90:
            raise ValueError("Vĩ độ phải nằm trong khoảng [-90, 90]")
        if not -180 <= lng <= 180:
            raise ValueError("Kinh độ phải nằm trong khoảng [-180, 180]")
        return value


class ItineraryScheduleStopIn(BaseModel):
    id: str = Field(min_length=1, max_length=200)
    visit_minutes: int = Field(default=60, ge=0, le=720)
    opening_hours: str | None = Field(default=None, max_length=200)
    requested_time: str | None = Field(default=None, max_length=80)
    required: bool = True

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        return _validate_itinerary_stop_id(value)

    @field_validator("requested_time")
    @classmethod
    def validate_requested_time(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if parse_time_range(value) is None:
            raise ValueError("Khung giờ yêu cầu không hợp lệ")
        return value.strip()


class ItineraryScheduleIn(BaseModel):
    day_start_minute: int = Field(default=480, ge=0, le=1440)
    day_end_minute: int = Field(default=1080, ge=0, le=1440)
    mode: Literal["driving", "cycling", "foot"] = "driving"
    stops: list[ItineraryScheduleStopIn] = Field(min_length=2, max_length=20)
    duration_matrix_minutes: list[list[float | None]] | None = None

    @field_validator("duration_matrix_minutes", mode="before")
    @classmethod
    def validate_matrix_values(cls, value):
        return _validate_duration_matrix_values(value)

    @model_validator(mode="after")
    def validate_time_bounds_and_matrix(self):
        if self.day_end_minute <= self.day_start_minute:
            raise ValueError("Giờ kết thúc ngày phải sau giờ bắt đầu")
        matrix = self.duration_matrix_minutes
        if matrix is None:
            return self
        size = len(self.stops)
        if len(matrix) != size or any(len(row) != size for row in matrix):
            raise ValueError("Ma trận thời gian phải vuông và khớp số điểm dừng")
        if any(matrix[index][index] != 0 for index in range(size)):
            raise ValueError("Đường chéo ma trận thời gian phải bằng 0")
        return self


def _validate_schedule_references(
    schedule: ItineraryScheduleIn,
    stop_ids: list[str],
) -> None:
    schedule_ids = [stop.id for stop in schedule.stops]
    if Counter(schedule_ids) != Counter(stop_ids):
        raise ValueError("ID lịch phải khớp chính xác các điểm dừng")
    if schedule_ids[0] != stop_ids[0] or schedule_ids[-1] != stop_ids[-1]:
        raise ValueError("Điểm đầu và điểm cuối phải khớp lịch trình gốc")
    if not schedule.stops[0].required or not schedule.stops[-1].required:
        raise ValueError("Điểm đầu và điểm cuối phải là điểm bắt buộc")


class ItineraryOptimizeIn(BaseModel):
    stops: list[ItineraryOptimizeStopIn] = Field(min_length=2, max_length=20)
    strict_direction: bool = True
    blocked_edges: list[tuple[str, str]] = Field(default_factory=list, max_length=80)
    schedule: ItineraryScheduleIn | None = None

    @model_validator(mode="after")
    def validate_route_references(self):
        stop_ids = [stop.id for stop in self.stops]
        known_ids = set(stop_ids)
        if len(stop_ids) != len(known_ids):
            raise ValueError("ID điểm dừng không được trùng")
        if any(
            source not in known_ids or target not in known_ids
            for source, target in self.blocked_edges
        ):
            raise ValueError("Cạnh bị cấm phải tham chiếu điểm dừng trong lịch trình")
        if self.schedule is not None:
            _validate_schedule_references(self.schedule, stop_ids)
        return self


def _schedule_windows(stop: ItineraryScheduleStopIn) -> tuple[TimeWindow, ...]:
    opening_windows = ()
    if stop.opening_hours is not None:
        opening_windows, _ = parse_opening_hours(stop.opening_hours)
    requested_window = parse_time_range(stop.requested_time)
    if requested_window is None:
        return opening_windows
    if not opening_windows:
        return (requested_window,)

    intersections = tuple(
        TimeWindow(
            max(window.start_minute, requested_window.start_minute),
            min(window.end_minute, requested_window.end_minute),
        )
        for window in opening_windows
        if max(window.start_minute, requested_window.start_minute)
        <= min(window.end_minute, requested_window.end_minute)
    )
    if not intersections:
        raise NoFeasibleScheduleError(
            f"Không tìm thấy lịch trình khả thi; điểm chặn đầu tiên: {stop.id}"
        )
    return intersections


def _build_schedule_stops(payload: ItineraryOptimizeIn) -> tuple[ScheduleStop, ...]:
    schedule = payload.schedule
    if schedule is None:
        raise ValueError("Thiếu cấu hình lịch trình")
    coordinates_by_id = {stop.id: stop.coordinates for stop in payload.stops}
    return tuple(
        ScheduleStop(
            stop.id,
            coordinates_by_id[stop.id],
            stop.visit_minutes,
            _schedule_windows(stop),
            stop.required,
        )
        for stop in schedule.stops
    )


def _build_schedule_matrix(
    schedule: ItineraryScheduleIn,
    stops: tuple[ScheduleStop, ...],
) -> TravelMatrix:
    if schedule.duration_matrix_minutes is None:
        return build_fallback_matrix(stops, schedule.mode)
    return TravelMatrix(
        tuple(stop.id for stop in schedule.stops),
        tuple(tuple(row) for row in schedule.duration_matrix_minutes),
        "request",
    )


def _path_distance_km(stops: list[ItineraryOptimizeStopIn]) -> float:
    return sum(
        haversine_km(source.coordinates, target.coordinates)
        for source, target in zip(stops, stops[1:])
    )


def _serialize_schedule_result(result, distance_before_km: float) -> dict:
    return {
        "ordered_ids": list(result.ordered_ids),
        "distance_before_km": distance_before_km,
        "distance_after_km": result.geometric_distance_km,
        "saved_distance_km": max(
            0.0,
            distance_before_km - result.geometric_distance_km,
        ),
        "backtrack_ratio": result.backtrack_ratio,
        "solver": result.solver,
        "warnings": list(result.warnings),
        "schedule": {
            "placements": [
                {
                    "stop_id": placement.stop_id,
                    "arrival_minute": placement.arrival_minute,
                    "start_visit_minute": placement.start_visit_minute,
                    "end_visit_minute": placement.finish_visit_minute,
                }
                for placement in result.placements
            ],
            "skipped": [asdict(stop) for stop in result.skipped],
            "matrix_source": result.matrix_source,
            "total_travel_minutes": result.total_travel_minutes,
            "waiting_minutes": result.waiting_minutes,
            "overtime_minutes": result.overtime_minutes,
            "minimum_slack_minutes": result.minimum_slack_minutes,
        },
    }


def _serialize_order_result(result, extra_warnings: tuple[str, ...] = ()) -> dict:
    return {
        "ordered_ids": list(result.ordered_ids),
        "distance_before_km": result.distance_before_km,
        "distance_after_km": result.distance_after_km,
        "saved_distance_km": max(
            0.0,
            result.distance_before_km - result.distance_after_km,
        ),
        "backtrack_ratio": result.backtrack_ratio,
        "solver": result.solver,
        "warnings": [*result.warnings, *extra_warnings],
    }


async def _optimize_itinerary_order_only(
    payload: ItineraryOptimizeIn,
    extra_warnings: tuple[str, ...] = (),
) -> dict | JSONResponse:
    stops = [RouteStop(stop.id, stop.coordinates) for stop in payload.stops]
    options = OptimizeOptions(
        strict_direction=payload.strict_direction,
        blocked_edges=frozenset(payload.blocked_edges),
    )
    try:
        result = await asyncio.to_thread(optimize_stop_order, stops, options)
    except NoFeasibleRouteError as exc:
        return _err(409, str(exc))
    return _serialize_order_result(result, extra_warnings)


async def _schedule_itinerary(payload: ItineraryOptimizeIn) -> dict | JSONResponse:
    schedule = payload.schedule
    if schedule is None:
        raise ValueError("Thiếu cấu hình lịch trình")
    try:
        stops = _build_schedule_stops(payload)
    except NoFeasibleScheduleError as exc:
        return _err(409, str(exc))
    options = ScheduleOptions(
        day_start_minute=schedule.day_start_minute,
        day_end_minute=schedule.day_end_minute,
        blocked_edges=frozenset(payload.blocked_edges),
    )
    try:
        matrix = _build_schedule_matrix(schedule, stops)
        result = await asyncio.to_thread(schedule_stop_order, stops, matrix, options)
    except NoFeasibleScheduleError as exc:
        return _err(409, str(exc))
    except Exception:
        logger.exception("Schedule optimization failed; using order-only fallback")
        return await _optimize_itinerary_order_only(
            payload,
            ("schedule-fallback-order-only",),
        )
    return _serialize_schedule_result(result, _path_distance_km(payload.stops))


@router.post(
    "/itineraries/optimize-order",
    summary="Optimize itinerary stop order",
    description="Reorders 2-20 stops along a fixed forward corridor without paid services.",
)
async def optimize_itinerary_order(payload: ItineraryOptimizeIn):
    """Sắp lại thứ tự điểm dừng của lịch trình; có trường schedule thì chạy nhánh xếp lịch theo giờ.

    Cả hai nhánh trả ordered_ids, quãng đường trước/sau, backtrack_ratio, solver và warnings.
    Không tìm được phương án khả thi → 409; nhánh xếp lịch lỗi bất ngờ sẽ lùi về nhánh
    chỉ-sắp-thứ-tự kèm cảnh báo schedule-fallback-order-only.
    """
    if payload.schedule is not None:
        return await _schedule_itinerary(payload)
    return await _optimize_itinerary_order_only(payload)


@router.get("/itineraries",
            summary="List itineraries",
            description="Returns paginated travel itineraries. Optionally filtered by area. Cached for 5 minutes.")
async def list_itineraries(
    response: Response,
    area: Optional[str] = Query(None, max_length=100),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0, le=10000),
):
    """Trả danh sách lịch trình theo trang, đã loại các stop trỏ tới entity không công khai.

    Lọc tuỳ chọn theo area; các entity của stop được nạp theo lô một lần cho cả trang.
    """
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=600"
    def _query():
        itineraries = db.list_itineraries(area=area, limit=limit, offset=offset)
        stop_ids = [
            stop_id
            for itinerary in itineraries
            for stop_id in (
                _itinerary_stop_entity_id(stop) for stop in itinerary.get("stops", [])
            )
            if stop_id
        ]
        public_entities = _get_public_entities_batch(stop_ids) if stop_ids else {}
        for itinerary in itineraries:
            itinerary["stops"] = _public_itinerary_stops(
                itinerary.get("stops", []), public_entities,
            )
        return itineraries
    return await asyncio.to_thread(_query)


@router.get("/itineraries/{itin_id}",
            summary="Get itinerary detail",
            description="Returns a single itinerary with stops enriched with entity names, summaries, types, and coordinates.")
async def get_itinerary(itin_id: str, response: Response):
    """Trả một lịch trình theo id, stop đã lọc theo entity công khai và bổ sung dữ liệu entity.

    Lịch trình không tồn tại → 404.
    """
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=600"
    validate_path_id(itin_id, "itin_id")
    def _query():
        it = db.get_itinerary(itin_id)
        if not it:
            return None
        it["stops"] = _public_itinerary_stops(it.get("stops", []), enrich=True)
        return it
    result = await asyncio.to_thread(_query)
    if not result:
        return _err(404, "not_found")
    return result
