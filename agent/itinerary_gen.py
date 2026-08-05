"""
vinhlong360 — Dynamic Itinerary Generator.

Tạo lịch trình tùy chỉnh dựa trên:
  - Số ngày (1-5)
  - Sở thích (ẩm thực, lịch sử, thiên nhiên, văn hóa, mua sắm)
  - Khu vực ưu tiên
  - Tháng đi (mùa vụ)
  - Ngân sách (thấp/trung bình/cao)

Output: lịch trình chi tiết với thời gian, điểm dừng, ghi chú, ăn uống.
"""

import logging
import math
from numbers import Real
import re

import knowledge
from itinerary_selection import (
    SelectionCandidate,
    SelectionOptions,
    prune_candidates,
    select_and_schedule_day,
)
from itinerary_schedule import (
    NoFeasibleScheduleError,
    ScheduleOptions,
    ScheduleStop,
    TimeWindow,
    build_fallback_matrix,
    infer_visit_minutes,
    parse_opening_hours,
    parse_time_range,
    schedule_stop_order,
)

logger = logging.getLogger(__name__)

# ── Interest → entity_type mapping ──

INTEREST_MAP = {
    "am_thuc": ["dish", "product"],
    "lich_su": ["history", "person", "attraction"],
    "thien_nhien": ["nature", "experience"],
    "van_hoa": ["craft_village", "event", "attraction"],
    "mua_sam": ["product", "craft_village"],
    "tham_quan": ["attraction", "experience"],
    "tong_hop": ["attraction", "experience", "dish", "product", "craft_village"],
}

# Thời gian tham quan trung bình theo loại (phút)
VISIT_DURATION = {
    "attraction": 90,
    "experience": 120,
    "craft_village": 60,
    "dish": 45,
    "product": 30,
    "history": 60,
    "nature": 90,
    "person": 30,
    "event": 120,
    "economy": 30,
    "accommodation": 0,
}

MEAL_SLOTS = {
    "sang": "07:00",
    "trua": "12:00",
    "chieu": "15:00",
    "toi": "18:30",
}

MEAL_NOTE = "🍜 Nghỉ trưa & thưởng thức đặc sản"
REST_NOTE = "🪑 Nghỉ/đệm thời gian"


def generate_itinerary(
    days: int = 1,
    interests: list[str] = None,
    areas: list[str] = None,
    month: int = None,
    budget: str = "trung_binh",
    meal_anchors: list[str] | None = None,
    rest_anchors: list[str] | None = None,
) -> dict:
    """
    Tạo lịch trình tùy chỉnh.

    Args:
        days: 1-5 ngày
        interests: ["am_thuc", "lich_su", "thien_nhien", "van_hoa", "mua_sam", "tham_quan"]
        areas: ["vinh-long", "ben-tre", "tra-vinh"]
        month: 1-12 (ưu tiên mùa vụ)
        budget: "thap" | "trung_binh" | "cao"
        meal_anchors: Mốc bữa ăn cố định; None dùng mặc định 12:00, [] để tắt
        rest_anchors: Mốc nghỉ cố định; None không thêm khoảng nghỉ

    Returns: {title, days: [{date, stops: [{time, entity, note}]}], tips}
    """
    knowledge._ensure()
    days = max(1, min(5, days))
    interests = interests or ["tong_hop"]
    areas = areas or ["vinh-long", "ben-tre", "tra-vinh"]
    meal_anchor_values = ["12:00"] if meal_anchors is None else list(meal_anchors)
    rest_anchor_values = [] if rest_anchors is None else list(rest_anchors)

    # 1. Thu thập candidates
    candidates = _collect_candidates(interests, areas, month, budget)

    # Sort by score
    candidates.sort(key=lambda c: c["score"], reverse=True)
    meal_candidates = _collect_candidates(["am_thuc"], areas, month, budget)
    meal_candidates.sort(key=lambda c: c["score"], reverse=True)

    # 2. Phân bổ stops theo ngày
    stops_per_day = 5 if days == 1 else 4
    total_stops = stops_per_day * days
    selected = _select_diverse(candidates, total_stops, areas, days)

    # 3. Xây dựng lịch trình
    day_plans = _build_joint_day_plans(
        days,
        stops_per_day,
        selected,
        candidates,
        meal_candidates,
        month,
        meal_anchor_values,
        rest_anchor_values,
        areas,
    )

    # 4. Tips
    tips = _gen_tips(interests, areas, month, budget)

    # Title
    title = _build_title(days, interests, areas)

    return {
        "title": title,
        "days": days,
        "areas": areas,
        "interests": interests,
        "month": month,
        "budget": budget,
        "day_plans": day_plans,
        "tips": tips,
        "total_stops": sum(len(d["stops"]) for d in day_plans),
    }


def _collect_candidates(interests: list, areas: list, month: int, budget: str) -> list:
    """Thu thập & chấm điểm candidates khớp interests/areas."""
    target_types = set()
    for interest in interests:
        target_types.update(INTEREST_MAP.get(interest, INTEREST_MAP["tong_hop"]))

    candidates = []
    for e in knowledge._entities.values():
        if e["type"] not in target_types:
            continue
        p = knowledge.get_place(e["id"])
        if not p:
            continue
        area = p.get("area")
        if area not in areas:
            continue

        score = _score_entity(e, month, budget, area, areas)
        candidates.append({"entity": e, "place": p, "area": area, "score": score})

    return candidates


def _build_day_plans(
    days: int,
    stops_per_day: int,
    selected: list,
    meal_candidates: list,
    month: int,
    meal_anchors: list[str],
    rest_anchors: list[str],
) -> list:
    """Xây dựng day_plans từ danh sách entity đã chọn."""
    day_plans = []
    used_entity_ids = {item["entity"]["id"] for item in selected}
    idx = 0
    for d in range(days):
        day_entities = selected[idx:idx + stops_per_day]
        idx += stops_per_day

        day_stops, schedule = _build_day_schedule(
            day_entities,
            meal_candidates,
            month,
            meal_anchors,
            rest_anchors,
            d + 1,
            used_entity_ids,
        )
        used_entity_ids.update(item["entity"]["id"] for item in day_entities)
        used_entity_ids.update(
            stop["entity"]["id"]
            for stop in day_stops
            if stop.get("is_meal")
        )

        day_plans.append({
            "day": d + 1,
            "area_focus": _day_area(day_entities),
            "stops": [{k: v for k, v in s.items() if k != "time_min"} for s in day_stops],
            "schedule": schedule,
        })

    return day_plans


def _candidate_fee_value(item: dict) -> float | None:
    entity = item.get("entity") or {}
    attributes = entity.get("attributes") or {}
    value = entity.get("fee_value")
    if value is None:
        value = attributes.get("admission_fee")
    if value is None:
        value = attributes.get("gia")
    if isinstance(value, bool):
        return None
    if isinstance(value, Real):
        return float(value) if math.isfinite(float(value)) and value >= 0 else None
    if not isinstance(value, str):
        return None
    match = re.search(r"\d+(?:[.,]\d+)?", value)
    if match is None:
        return None
    try:
        parsed = float(match.group(0).replace(",", "."))
    except ValueError:
        return None
    return parsed if math.isfinite(parsed) and parsed >= 0 else None


def _ordered_kept_candidates(
    valid: list[tuple[dict, SelectionCandidate]],
    raw_items: list[dict],
    required_ids: frozenset[str],
    coordinate_drops: list[dict],
) -> tuple[list[SelectionCandidate], dict[str, dict], list[dict]]:
    """Prune pool rồi xếp thứ tự: required đầu, optional giữa, required cuối.

    Trả cả `raw_by_id` vì hàm gọi cần nó để dựng `kept_by_id` — nếu không thì
    shell phải tính lại y hệt.

    CỐ Ý giữ hai điểm dễ bị "dọn" nhầm:
    - `required_order` bám THỨ TỰ của `raw_items`, và khi có ≥2 required thì
      required ở GIỮA bị bỏ (chỉ lấy [0] và [-1] làm hai đầu mút). Đây là hành
      vi có test phủ, không phải lỗi.
    - Tên `kept_by_id` ở đây (id → SelectionCandidate) khác nghĩa với khoá
      `kept_by_id` trong dict trả về của hàm gọi (id → raw item).
    """
    valid_candidates = [candidate for _item, candidate in valid]
    required_valid_ids = frozenset(
        candidate.stop.id
        for candidate in valid_candidates
        if candidate.stop.id in required_ids
    )
    kept, pruned = prune_candidates(valid_candidates, required_valid_ids)
    kept_by_id = {candidate.stop.id: candidate for candidate in kept}
    raw_by_id = {item["entity"]["id"]: item for item in raw_items}
    required_order = [
        kept_by_id[item["entity"]["id"]]
        for item in raw_items
        if item["entity"]["id"] in kept_by_id
        and item["entity"]["id"] in required_ids
    ]
    optional_order = [
        candidate for candidate in kept if candidate.stop.id not in required_ids
    ]
    ordered_kept = (
        [required_order[0], *optional_order, required_order[-1]]
        if len(required_order) >= 2
        else [*required_order, *optional_order]
    )
    dropped = coordinate_drops + [
        {"stop_id": item.stop_id, "reason": item.reason} for item in pruned
    ]
    return ordered_kept, raw_by_id, dropped


def _selection_pool_state(
    raw_items: list[dict],
    required_ids: frozenset[str],
) -> dict:
    """Adapt one raw pool and retain deterministic diagnostics for its drops."""
    raw_items = list(raw_items)
    candidate_count = len(raw_items)
    warnings: list[str] = []
    coordinate_drops: list[dict] = []
    valid: list[tuple[dict, SelectionCandidate]] = []
    missing_required = False

    for item in raw_items:
        stop_id = item["entity"]["id"]
        required = stop_id in required_ids
        try:
            adapted = _candidate_schedule_stop(item, required=required)
        except ValueError:
            raise
        if adapted is None:
            coordinate_drops.append(
                {"stop_id": stop_id, "reason": "coordinates-missing"}
            )
            missing_required = missing_required or required
            continue
        stop, stop_warnings = adapted
        warnings.extend(stop_warnings)
        valid.append(
            (
                item,
                SelectionCandidate(
                    stop=stop,
                    reward=float(item.get("score", 0.0)),
                    entity_type=item["entity"].get("type", "unknown"),
                    area=item.get("area", ""),
                    fee_value=_candidate_fee_value(item),
                ),
            )
        )

    if missing_required:
        return {
            "candidate_count": candidate_count,
            "warnings": warnings,
            "raw_items": raw_items,
            "valid": valid,
            "kept": [],
            "kept_by_id": {},
            "dropped": coordinate_drops,
            "required_missing": True,
        }

    ordered_kept, raw_by_id, dropped = _ordered_kept_candidates(
        valid, raw_items, required_ids, coordinate_drops
    )
    return {
        "candidate_count": candidate_count,
        "warnings": warnings,
        "raw_items": raw_items,
        "valid": valid,
        "kept": ordered_kept,
        "kept_by_id": {candidate.stop.id: raw_by_id[candidate.stop.id] for candidate in ordered_kept},
        "dropped": dropped,
        "required_missing": False,
    }


def _build_joint_candidate_pools(
    seed_days: list[list[dict]],
    candidates: list[dict],
    areas: list[str],
) -> list[list[dict]]:
    """Partition non-seed extras while reserving every seed ID for its own day."""
    pools = [list(day) for day in seed_days]
    seed_ids = {
        item["entity"]["id"] for day in seed_days for item in day
    }
    extras = [
        item for item in candidates if item["entity"]["id"] not in seed_ids
    ]
    for item in extras:
        matching = [
            index
            for index, day in enumerate(seed_days)
            if _day_area(day) == item.get("area")
        ]
        eligible = matching or list(range(len(pools)))
        target_index = min(eligible, key=lambda index: (len(pools[index]), index))
        pools[target_index].append(item)

    normalized: list[list[dict]] = []
    for day, pool in zip(seed_days, pools):
        if len(day) >= 2:
            first_id = day[0]["entity"]["id"]
            last_id = day[-1]["entity"]["id"]
            middle = [
                item
                for item in pool
                if item["entity"]["id"] not in {first_id, last_id}
            ]
            normalized.append([day[0], *middle, day[-1]])
        else:
            normalized.append(pool)
    return normalized


def _selection_anchor_stops(anchor_items: list[dict]) -> list[ScheduleStop]:
    return [
        ScheduleStop(
            id=item["entity"]["id"],
            coordinates=_candidate_coordinates(item),
            visit_minutes=60 if item["_anchor_kind"] == "meal" else 30,
            opening_windows=(item["_anchor_window"],),
            required=True,
        )
        for item in anchor_items
    ]


def _project_placements(schedule, items_by_id: dict[str, dict], month: int) -> list[dict]:
    """Dựng danh sách stop người dùng nhìn thấy từ một ScheduleResult.

    Gộp bản trùng giữa `_build_day_schedule` (truyền thẳng ScheduleResult) và
    `_project_selection_schedule` (truyền `result.schedule`). Nhận CHÍNH đối
    tượng schedule chứ không nhận SelectionResult, để hai chỗ gọi giữ nguyên
    nguồn dữ liệu của mình.
    """
    placements_by_id = {placement.stop_id: placement for placement in schedule.placements}
    scheduled_stops: list[dict] = []
    for entity_id in schedule.ordered_ids:
        item = items_by_id.get(entity_id)
        placement = placements_by_id.get(entity_id)
        if item is None or placement is None:
            continue
        entity = item["entity"]
        start_minute = int(round(placement.start_visit_minute))
        scheduled_stop = {
            "time": _fmt_time(start_minute),
            "time_min": start_minute,
            "entity": _entity_summary(entity),
            "note": _gen_note(entity, month),
        }
        if item.get("_anchor_kind") == "meal":
            scheduled_stop["note"] = MEAL_NOTE
            scheduled_stop["is_meal"] = True
        elif item.get("_anchor_kind") == "rest":
            scheduled_stop["note"] = REST_NOTE
            scheduled_stop["is_rest"] = True
        scheduled_stops.append(scheduled_stop)
    return scheduled_stops


def _schedule_core_diagnostics(schedule) -> dict:
    """8 khoá chẩn đoán chung của một ScheduleResult.

    CỐ Ý KHÔNG có khoá `warnings`: hai chỗ gọi tính nó từ NGUỒN KHÁC NHAU —
    `_build_day_schedule` gộp warnings của chính lịch, còn `_selection_diagnostics`
    cố tình BỎ `result.schedule.warnings`. Helper mà tự đọc `schedule.warnings`
    sẽ âm thầm thêm warning lịch vào đường selection (đã có test ghim).
    """
    return {
        "solver": schedule.solver,
        "matrix_source": schedule.matrix_source,
        "total_travel_minutes": schedule.total_travel_minutes,
        "waiting_minutes": schedule.waiting_minutes,
        "overtime_minutes": schedule.overtime_minutes,
        "minimum_slack_minutes": schedule.minimum_slack_minutes,
        "backtrack_ratio": schedule.backtrack_ratio,
        "skipped": [
            {"stop_id": skipped.stop_id, "reason": skipped.reason}
            for skipped in schedule.skipped
        ],
    }


def _project_selection_schedule(
    result,
    items_by_id: dict[str, dict],
    anchor_items: list[dict],
    month: int,
) -> list[dict]:
    items_by_id = dict(items_by_id)
    items_by_id.update(
        {item["entity"]["id"]: item for item in anchor_items}
    )
    return _project_placements(result.schedule, items_by_id, month)


def _selection_diagnostics(result, state: dict, anchor_warnings: list[str]) -> dict:
    dropped = list(state["dropped"])
    dropped.extend(
        {"stop_id": item.stop_id, "reason": item.reason}
        for item in result.dropped
    )
    dropped.sort(key=lambda item: item["stop_id"])
    # KHÔNG lấy result.schedule.warnings — xem docstring _schedule_core_diagnostics
    warnings = list(state["warnings"]) + list(anchor_warnings) + list(result.warnings)
    return {
        **_schedule_core_diagnostics(result.schedule),
        "warnings": warnings,
        "selection_solver": result.solver,
        "candidate_count": state["candidate_count"],
        "selected_count": result.selected_count,
        "total_reward": result.total_reward,
        "dropped_reasons": dropped,
    }


def _fallback_selection_diagnostics(
    schedule: dict,
    raw_items: list[dict],
    day_stops: list[dict],
) -> dict:
    emitted_ids = {
        stop["entity"]["id"]
        for stop in day_stops
        if not stop.get("is_meal") and not stop.get("is_rest")
    }
    raw_by_id = {item["entity"]["id"]: item for item in raw_items}
    dropped = []
    for item in raw_items:
        stop_id = item["entity"]["id"]
        if stop_id in emitted_ids:
            continue
        reason = (
            "coordinates-missing"
            if _candidate_coordinates(item) is None
            else "lower-reward-alternative"
        )
        dropped.append({"stop_id": stop_id, "reason": reason})
    schedule = dict(schedule)
    schedule.update(
        {
            "selection_solver": "phase2b-fallback",
            "candidate_count": len(raw_items),
            "selected_count": len(emitted_ids),
            "total_reward": sum(
                raw_by_id[stop_id].get("score", 0.0)
                for stop_id in emitted_ids
                if stop_id in raw_by_id
            ),
            "dropped_reasons": sorted(dropped, key=lambda item: item["stop_id"]),
        }
    )
    return schedule


def _build_joint_day_plans(
    days: int,
    stops_per_day: int,
    selected: list,
    candidates: list,
    meal_candidates: list,
    month: int,
    meal_anchors: list[str],
    rest_anchors: list[str],
    areas: list[str],
) -> list:
    seed_days = [
        selected[index * stops_per_day : (index + 1) * stops_per_day]
        for index in range(days)
    ]
    raw_pools = _build_joint_candidate_pools(seed_days, candidates, areas)
    states = []
    reserved_content_ids: set[str] = set()
    for raw_pool, seed_day in zip(raw_pools, seed_days):
        required_ids = frozenset(
            item["entity"]["id"] for item in (seed_day[:1] + seed_day[-1:])
        ) if len(seed_day) >= 2 else frozenset()
        try:
            state = _selection_pool_state(raw_pool, required_ids)
        except ValueError:
            state = {
                "candidate_count": len(raw_pool),
                "warnings": ["schedule-fallback"],
                "raw_items": raw_pool,
                "valid": [],
                "kept": [],
                "kept_by_id": {},
                "dropped": [],
                "required_missing": True,
                "preparation_error": True,
            }
        if state.get("required_missing") or state.get("preparation_error"):
            reserved_content_ids.update(
                item["entity"]["id"] for item in raw_pool
            )
        else:
            reserved_content_ids.update(
                candidate.stop.id for candidate in state["kept"]
            )
        states.append((state, required_ids, seed_day, raw_pool))

    used_content_ids: set[str] = set()
    used_anchor_ids: set[str] = set()
    day_plans = []
    for day_index, (state, required_ids, seed_day, raw_pool) in enumerate(states):
        anchor_items, anchor_warnings = _build_anchor_items(
            seed_day,
            meal_candidates,
            meal_anchors,
            rest_anchors,
            day_index + 1,
            reserved_content_ids | used_anchor_ids | used_content_ids,
        )
        current_anchor_ids = {
            item["entity"]["id"]
            for item in anchor_items
            if item.get("_anchor_kind") == "meal"
        }
        used_anchor_ids.update(current_anchor_ids)

        fallback_used_ids = (
            reserved_content_ids | used_anchor_ids | used_content_ids
        ) - current_anchor_ids
        if (
            len(seed_day) < 2
            or state.get("required_missing")
            or state.get("preparation_error")
        ):
            day_stops, schedule = _build_day_schedule(
                seed_day,
                meal_candidates,
                month,
                meal_anchors,
                rest_anchors,
                day_index + 1,
                fallback_used_ids,
            )
            schedule = _fallback_selection_diagnostics(
                schedule,
                raw_pool,
                day_stops,
            )
            schedule["warnings"] = list(schedule["warnings"])
            if "selection-fallback" not in schedule["warnings"]:
                schedule["warnings"].append("selection-fallback")
        else:
            selection_items = state["kept"]
            fixed_stops = _selection_anchor_stops(anchor_items)
            matrix_stops = [candidate.stop for candidate in selection_items]
            matrix_stops.extend(fixed_stops)
            try:
                matrix = build_fallback_matrix(matrix_stops, "driving")
                result = select_and_schedule_day(
                    candidates=selection_items,
                    required_ids=required_ids,
                    fixed_stops=fixed_stops,
                    matrix=matrix,
                    schedule_options=ScheduleOptions(
                        day_start_minute=480,
                        day_end_minute=1080,
                    ),
                    selection_options=SelectionOptions(
                        target_count=stops_per_day,
                        exact_limit=8,
                        beam_width=32,
                        repair_iterations=32,
                    ),
                )
            except (NoFeasibleScheduleError, ValueError):
                day_stops, schedule = _build_day_schedule(
                    seed_day,
                    meal_candidates,
                    month,
                    meal_anchors,
                    rest_anchors,
                    day_index + 1,
                    fallback_used_ids,
                )
                schedule = _fallback_selection_diagnostics(
                    schedule,
                    raw_pool,
                    day_stops,
                )
                schedule["warnings"] = list(schedule["warnings"])
                if "selection-fallback" not in schedule["warnings"]:
                    schedule["warnings"].append("selection-fallback")
            else:
                day_stops = _project_selection_schedule(
                    result,
                    state["kept_by_id"],
                    anchor_items,
                    month,
                )
                schedule = _selection_diagnostics(
                    result,
                    state,
                    anchor_warnings,
                )
                used_content_ids.update(result.selected_ids)

        used_content_ids.update(
            stop["entity"]["id"]
            for stop in day_stops
            if not stop.get("is_meal") and not stop.get("is_rest")
        )
        used_anchor_ids.update(
            stop["entity"]["id"]
            for stop in day_stops
            if stop.get("is_meal")
        )
        day_plans.append(
            {
                "day": day_index + 1,
                "area_focus": _day_area(seed_day),
                "stops": [
                    {key: value for key, value in stop.items() if key != "time_min"}
                    for stop in day_stops
                ],
                "schedule": schedule,
            }
        )
    return day_plans


def _finite_coordinates(value) -> tuple[float, float] | None:
    if isinstance(value, dict):
        value = (
            value.get("lat", value.get("latitude")),
            value.get("lng", value.get("lon", value.get("longitude"))),
        )
    if not isinstance(value, (list, tuple)) or len(value) < 2:
        return None
    lat, lng = value[:2]
    if (
        isinstance(lat, bool)
        or isinstance(lng, bool)
        or not isinstance(lat, Real)
        or not isinstance(lng, Real)
        or not math.isfinite(float(lat))
        or not math.isfinite(float(lng))
    ):
        return None
    return float(lat), float(lng)


def _candidate_coordinates(item: dict) -> tuple[float, float] | None:
    entity = item.get("entity") or {}
    coordinates = _finite_coordinates(entity.get("coordinates"))
    if coordinates is not None:
        return coordinates
    return _finite_coordinates((item.get("place") or {}).get("coordinates"))


def _candidate_visit_minutes(item: dict) -> int | None:
    entity = item.get("entity") or {}
    attributes = entity.get("attributes") or {}
    for key in ("visit_minutes", "duration_minutes"):
        value = entity.get(key)
        if value is None:
            value = attributes.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    return None


def _candidate_suggested_duration(item: dict) -> str | None:
    entity = item.get("entity") or {}
    attributes = entity.get("attributes") or {}
    for key in ("suggested_duration", "duration"):
        value = entity.get(key)
        if value is None:
            value = attributes.get(key)
        if isinstance(value, str):
            return value
    return None


def _candidate_schedule_stop(item: dict, required: bool) -> tuple[ScheduleStop, tuple[str, ...]] | None:
    entity = item.get("entity") or {}
    coordinates = _candidate_coordinates(item)
    if coordinates is None:
        return None
    attributes = entity.get("attributes") or {}
    hours = (
        entity.get("hours")
        or entity.get("open_hours")
        or attributes.get("hours")
        or attributes.get("open_hours")
    )
    opening_windows, warnings = parse_opening_hours(hours)
    visit_minutes = infer_visit_minutes(
        entity.get("type"),
        _candidate_visit_minutes(item),
        _candidate_suggested_duration(item),
    )
    return (
        ScheduleStop(
            id=entity["id"],
            coordinates=coordinates,
            visit_minutes=visit_minutes,
            opening_windows=opening_windows,
            required=required,
        ),
        warnings,
    )


def _legacy_schedule_diagnostics(warnings: list[str]) -> dict:
    return {
        "solver": "legacy-fixed-order",
        "matrix_source": "none",
        "total_travel_minutes": 0.0,
        "waiting_minutes": 0.0,
        "overtime_minutes": 0.0,
        "minimum_slack_minutes": 0.0,
        "backtrack_ratio": 0.0,
        "skipped": [],
        "warnings": warnings,
    }


def _fixed_anchor_window(anchor: str, visit_minutes: int) -> TimeWindow | None:
    if not isinstance(anchor, str):
        return None
    anchor = anchor.strip()
    parsed = parse_time_range(f"{anchor}-{anchor}")
    if parsed is None:
        return None
    try:
        return TimeWindow(parsed.start_minute, parsed.start_minute + visit_minutes)
    except ValueError:
        return None


def _find_meal_anchor_candidate(candidates: list, area: str, exclude_ids: set[str]) -> dict | None:
    for candidate in candidates:
        entity = candidate.get("entity") or {}
        if (
            entity.get("type") in ("dish", "product")
            and candidate.get("area") == area
            and entity.get("id") not in exclude_ids
            and _candidate_coordinates(candidate) is not None
        ):
            return candidate
    return None


def _build_anchor_items(
    day_entities: list[dict],
    meal_candidates: list[dict],
    meal_anchors: list[str],
    rest_anchors: list[str],
    day_number: int,
    used_entity_ids: set[str],
) -> tuple[list[dict], list[str]]:
    items: list[dict] = []
    warnings: list[str] = []
    area = _day_area(day_entities)
    used_ids = set(used_entity_ids)
    used_ids.update(item["entity"]["id"] for item in day_entities)

    for anchor_index, anchor in enumerate(meal_anchors):
        window = _fixed_anchor_window(anchor, 60)
        if window is None:
            warnings.append("invalid-anchor")
            continue
        meal = _find_meal_anchor_candidate(meal_candidates, area, used_ids)
        if meal is None:
            warnings.append("meal-anchor-unavailable")
            continue
        meal_id = meal["entity"]["id"]
        used_ids.add(meal_id)
        items.append({
            **meal,
            "_anchor_kind": "meal",
            "_anchor_window": window,
            "_anchor_index": anchor_index,
        })

    route_coordinates = [
        coordinates
        for item in day_entities
        if (coordinates := _candidate_coordinates(item)) is not None
    ]
    for anchor_index, anchor in enumerate(rest_anchors):
        window = _fixed_anchor_window(anchor, 30)
        if window is None:
            warnings.append("invalid-anchor")
            continue
        if not route_coordinates:
            warnings.append("rest-anchor-unavailable")
            continue
        coordinates = route_coordinates[min(anchor_index, len(route_coordinates) - 1)]
        items.append({
            "entity": {
                "id": f"rest-anchor-{day_number}-{anchor_index}",
                "name": "Nghỉ",
                "type": "rest",
                "summary": "Khoảng nghỉ",
                "coordinates": coordinates,
            },
            "area": area,
            "_anchor_kind": "rest",
            "_anchor_window": window,
            "_anchor_index": anchor_index,
        })

    return items, warnings


def _build_day_schedule(
    day_entities: list[dict],
    meal_candidates: list[dict],
    month: int,
    meal_anchors: list[str],
    rest_anchors: list[str],
    day_number: int,
    used_entity_ids: set[str],
) -> tuple[list[dict], dict]:
    anchor_items, anchor_warnings = _build_anchor_items(
        day_entities,
        meal_candidates,
        meal_anchors,
        rest_anchors,
        day_number,
        used_entity_ids,
    )
    legacy_meal_candidates = [
        item for item in anchor_items if item.get("_anchor_kind") == "meal"
    ]
    legacy_stops = _build_day_stops(
        day_entities,
        legacy_meal_candidates,
        month,
        insert_meal=bool(legacy_meal_candidates),
    )
    if not day_entities:
        return legacy_stops, _legacy_schedule_diagnostics(anchor_warnings)

    original_entries: list[tuple[dict, ScheduleStop]] = []
    warnings = list(anchor_warnings)
    for index, item in enumerate(day_entities):
        try:
            adapted = _candidate_schedule_stop(
                item,
                required=index in (0, len(day_entities) - 1),
            )
        except ValueError:
            return legacy_stops, _legacy_schedule_diagnostics(anchor_warnings + ["schedule-fallback"])
        if adapted is None:
            return legacy_stops, _legacy_schedule_diagnostics(anchor_warnings + ["coordinates-missing"])
        stop, stop_warnings = adapted
        original_entries.append((item, stop))
        warnings.extend(stop_warnings)

    if len(original_entries) < 2:
        return legacy_stops, _legacy_schedule_diagnostics(anchor_warnings + ["schedule-fallback"])

    anchor_entries = [
        (
            item,
            ScheduleStop(
                id=item["entity"]["id"],
                coordinates=_candidate_coordinates(item),
                visit_minutes=60 if item["_anchor_kind"] == "meal" else 30,
                opening_windows=(item["_anchor_window"],),
                required=True,
            ),
        )
        for item in anchor_items
    ]
    schedule_entries = [
        original_entries[0],
        *anchor_entries,
        *original_entries[1:-1],
        original_entries[-1],
    ]
    schedule_stops = [stop for _item, stop in schedule_entries]

    try:
        matrix = build_fallback_matrix(schedule_stops, "driving")
        result = schedule_stop_order(
            schedule_stops,
            matrix,
            ScheduleOptions(day_start_minute=480, day_end_minute=1080),
        )
    except (NoFeasibleScheduleError, ValueError):
        return legacy_stops, _legacy_schedule_diagnostics(anchor_warnings + ["schedule-fallback"])

    items_by_id = {item["entity"]["id"]: item for item, _stop in schedule_entries}
    scheduled_stops = _project_placements(result, items_by_id, month)
    diagnostics = {
        **_schedule_core_diagnostics(result),
        # Đường legacy CÓ gộp warnings của chính lịch — khác đường selection.
        "warnings": warnings + list(result.warnings),
    }
    return scheduled_stops, diagnostics


def _build_day_stops(
    day_entities: list,
    candidates: list,
    month: int,
    insert_meal: bool = True,
) -> list:
    """Phân bổ thời gian & chèn bữa ăn cho 1 ngày."""
    day_stops = []
    # Phân bổ thời gian trong ngày
    current_time = 8 * 60  # 8:00 AM (in minutes)
    for i, item in enumerate(day_entities):
        e = item["entity"]
        etype = e["type"]

        # Thêm bữa ăn
        if insert_meal and current_time >= 11.5 * 60 and not any(s.get("is_meal") for s in day_stops if s.get("time_min", 0) > 11 * 60):
            meal = _find_meal(candidates, item["area"], [s["entity"]["id"] for s in day_stops])
            if meal:
                day_stops.append({
                    "time": _fmt_time(current_time),
                    "time_min": current_time,
                    "entity": _entity_summary(meal["entity"]),
                    "note": MEAL_NOTE,
                    "is_meal": True,
                })
                current_time += 60

        day_stops.append({
            "time": _fmt_time(current_time),
            "time_min": current_time,
            "entity": _entity_summary(e),
            "note": _gen_note(e, month),
        })
        current_time += VISIT_DURATION.get(etype, 60) + 30  # + di chuyển

    return day_stops


def _build_title(days: int, interests: list, areas: list) -> str:
    """Tạo tiêu đề lịch trình."""
    area_names = [knowledge.AREA_META.get(a, {}).get("name", a) for a in areas]
    interest_labels = {"am_thuc": "ẩm thực", "lich_su": "lịch sử", "thien_nhien": "thiên nhiên",
                       "van_hoa": "văn hóa", "mua_sam": "mua sắm", "tham_quan": "tham quan", "tong_hop": "tổng hợp"}
    interest_text = " & ".join(interest_labels.get(i, i) for i in interests[:2])
    return f"Lịch trình {days} ngày {interest_text} — {', '.join(area_names[:2])}"


def _score_entity(e: dict, month: int, budget: str, area: str, preferred_areas: list) -> float:
    """Chấm điểm entity cho việc chọn vào lịch trình."""
    score = e.get("confidence", 0.5) * 10

    # Mùa vụ bonus
    if month:
        season = e.get("season")
        if season:
            if month in (season.get("peak") or []):
                score += 5
            elif month in season.get("months", []):
                score += 2

    # Khu vực ưu tiên
    if area in preferred_areas[:1]:
        score += 2

    # Loại entity
    type_bonus = {"attraction": 3, "experience": 3, "dish": 2, "craft_village": 2,
                  "product": 1, "history": 2, "nature": 3, "person": 1}
    score += type_bonus.get(e["type"], 0)

    # OCOP bonus
    if e.get("attributes", {}).get("ocop"):
        score += 2

    # Summary length (content richness)
    summary_len = len(e.get("summary", ""))
    if summary_len > 50:
        score += 1
    if summary_len > 100:
        score += 1

    return score


def _pick_best_candidate(areas: list, area_pools: dict, used_ids: set, used_day_types: set):
    """Chọn candidate tốt nhất (chưa dùng) qua các area, phạt loại đã có trong ngày."""
    best = None
    for area in areas:
        pool = area_pools.get(area, [])
        for c in pool:
            eid = c["entity"]["id"]
            etype = c["entity"]["type"]
            if eid in used_ids:
                continue
            # Đa dạng loại trong cùng ngày
            type_penalty = -3 if etype in used_day_types else 0
            adjusted = c["score"] + type_penalty
            if not best or adjusted > best[1]:
                best = (c, adjusted)
    return best


def _select_diverse(candidates: list, total: int, areas: list, days: int) -> list:
    """Chọn entities đa dạng (khu vực, loại)."""
    selected = []
    used_ids = set()
    used_types_per_day = {}

    # Round-robin qua areas
    area_pools = {a: [c for c in candidates if c["area"] == a] for a in areas}

    for i in range(total):
        day_num = i // (total // days) if days > 1 else 0
        if day_num not in used_types_per_day:
            used_types_per_day[day_num] = set()

        # Ưu tiên khu vực chưa đủ
        best = _pick_best_candidate(areas, area_pools, used_ids, used_types_per_day.get(day_num, set()))

        if best:
            selected.append(best[0])
            used_ids.add(best[0]["entity"]["id"])
            used_types_per_day.setdefault(day_num, set()).add(best[0]["entity"]["type"])

    return selected


def _find_meal(candidates: list, area: str, exclude_ids: list) -> dict | None:
    """Tìm món ăn/đặc sản cho bữa trưa."""
    for c in candidates:
        if c["entity"]["type"] in ("dish", "product") and c["area"] == area:
            if c["entity"]["id"] not in exclude_ids:
                return c
    return None


def _entity_summary(e: dict) -> dict:
    attrs = e.get("attributes") or {}
    d = {
        "id": e["id"],
        "name": e["name"],
        "type": e["type"],
        "summary": e.get("summary", "")[:120],
    }
    hours = attrs.get("hours") or attrs.get("open_hours")
    if hours:
        d["hours"] = hours
    if attrs.get("admission_fee"):
        d["admission_fee"] = attrs["admission_fee"]
    if attrs.get("address"):
        d["address"] = attrs["address"]
    return d


def _fmt_time(minutes: int) -> str:
    h = minutes // 60
    m = minutes % 60
    return f"{h:02d}:{m:02d}"


def _day_area(entities: list) -> str:
    areas = [e["area"] for e in entities if "area" in e]
    if not areas:
        return ""
    from collections import Counter
    return Counter(areas).most_common(1)[0][0]


def _gen_note(e: dict, month: int) -> str:
    notes = []
    if e.get("season") and month:
        peak = e["season"].get("peak", [])
        if month in peak:
            notes.append("⭐ Đang vào mùa cao điểm!")
    attrs = e.get("attributes", {})
    if attrs.get("ocop"):
        notes.append(f"🏅 OCOP {attrs['ocop']}")
    fee = attrs.get("admission_fee") or attrs.get("gia")
    if fee:
        notes.append(f"💰 {fee}")
    hours = attrs.get("hours") or attrs.get("open_hours")
    if hours:
        notes.append(f"🕐 {hours}")
    return " | ".join(notes) if notes else ""


def _gen_tips(interests: list, areas: list, month: int, budget: str) -> list[str]:
    tips = []
    if month and month in [6, 7, 8, 9, 10]:
        tips.append("☔ Tháng mùa mưa — nên mang áo mưa và giày chống trượt")
    if month and month in [12, 1, 2, 3]:
        tips.append("☀️ Mùa khô — thời tiết lý tưởng cho tham quan ngoài trời")
    if "ben-tre" in areas:
        tips.append("🥥 Bến Tre: nên thử dừa tươi và kẹo dừa tại xưởng")
    if "tra-vinh" in areas:
        tips.append("🛕 Trà Vinh: tôn trọng phong tục chùa Khmer (cởi giày, trang phục lịch sự)")
    if budget == "thap":
        tips.append("💡 Ăn quán bình dân và di chuyển xe máy để tiết kiệm")
    if budget == "cao":
        tips.append("🏨 Nên đặt resort/homestay cao cấp trước, đặc biệt cuối tuần")
    if "am_thuc" in interests:
        tips.append("🍴 Hỏi dân địa phương quán nào ngon — thường ngon hơn quán du lịch")
    tips.append("📱 Lưu số hotline du lịch Vĩnh Long: 1900.xxxx")
    return tips
