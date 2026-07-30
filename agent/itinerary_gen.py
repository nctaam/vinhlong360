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

import knowledge
from itinerary_schedule import (
    NoFeasibleScheduleError,
    ScheduleOptions,
    ScheduleStop,
    build_fallback_matrix,
    infer_visit_minutes,
    parse_opening_hours,
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


def generate_itinerary(
    days: int = 1,
    interests: list[str] = None,
    areas: list[str] = None,
    month: int = None,
    budget: str = "trung_binh",
) -> dict:
    """
    Tạo lịch trình tùy chỉnh.

    Args:
        days: 1-5 ngày
        interests: ["am_thuc", "lich_su", "thien_nhien", "van_hoa", "mua_sam", "tham_quan"]
        areas: ["vinh-long", "ben-tre", "tra-vinh"]
        month: 1-12 (ưu tiên mùa vụ)
        budget: "thap" | "trung_binh" | "cao"

    Returns: {title, days: [{date, stops: [{time, entity, note}]}], tips}
    """
    knowledge._ensure()
    days = max(1, min(5, days))
    interests = interests or ["tong_hop"]
    areas = areas or ["vinh-long", "ben-tre", "tra-vinh"]

    # 1. Thu thập candidates
    candidates = _collect_candidates(interests, areas, month, budget)

    # Sort by score
    candidates.sort(key=lambda c: c["score"], reverse=True)

    # 2. Phân bổ stops theo ngày
    stops_per_day = 5 if days == 1 else 4
    total_stops = stops_per_day * days
    selected = _select_diverse(candidates, total_stops, areas, days)

    # 3. Xây dựng lịch trình
    day_plans = _build_day_plans(days, stops_per_day, selected, candidates, month)

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


def _build_day_plans(days: int, stops_per_day: int, selected: list, candidates: list, month: int) -> list:
    """Xây dựng day_plans từ danh sách entity đã chọn."""
    day_plans = []
    idx = 0
    for d in range(days):
        day_entities = selected[idx:idx + stops_per_day]
        idx += stops_per_day

        day_stops, schedule = _build_day_schedule(day_entities, candidates, month)

        day_plans.append({
            "day": d + 1,
            "area_focus": _day_area(day_entities),
            "stops": [{k: v for k, v in s.items() if k != "time_min"} for s in day_stops],
            "schedule": schedule,
        })

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
        "solver": "legacy",
        "matrix_source": "none",
        "total_travel_minutes": 0.0,
        "waiting_minutes": 0.0,
        "overtime_minutes": 0.0,
        "minimum_slack_minutes": 0.0,
        "backtrack_ratio": 0.0,
        "skipped": [],
        "warnings": warnings,
    }


def _build_day_schedule(day_entities: list[dict], candidates: list[dict], month: int) -> tuple[list[dict], dict]:
    legacy_stops = _build_day_stops(day_entities, candidates, month)
    if not day_entities:
        return legacy_stops, _legacy_schedule_diagnostics([])

    schedule_stops: list[ScheduleStop] = []
    warnings: list[str] = []
    for index, item in enumerate(day_entities):
        try:
            adapted = _candidate_schedule_stop(
                item,
                required=index in (0, len(day_entities) - 1),
            )
        except ValueError:
            return legacy_stops, _legacy_schedule_diagnostics(["schedule-fallback"])
        if adapted is None:
            return legacy_stops, _legacy_schedule_diagnostics(["coordinates-missing"])
        stop, stop_warnings = adapted
        schedule_stops.append(stop)
        warnings.extend(stop_warnings)

    if len(schedule_stops) < 2:
        return legacy_stops, _legacy_schedule_diagnostics(["schedule-fallback"])

    try:
        matrix = build_fallback_matrix(schedule_stops, "driving")
        result = schedule_stop_order(
            schedule_stops,
            matrix,
            ScheduleOptions(day_start_minute=480, day_end_minute=1080),
        )
    except (NoFeasibleScheduleError, ValueError):
        return legacy_stops, _legacy_schedule_diagnostics(["schedule-fallback"])

    items_by_id = {item["entity"]["id"]: item for item in day_entities}
    placements_by_id = {placement.stop_id: placement for placement in result.placements}
    scheduled_stops = []
    for entity_id in result.ordered_ids:
        item = items_by_id.get(entity_id)
        placement = placements_by_id.get(entity_id)
        if item is None or placement is None:
            continue
        entity = item["entity"]
        start_minute = int(round(placement.start_visit_minute))
        scheduled_stops.append({
            "time": _fmt_time(start_minute),
            "time_min": start_minute,
            "entity": _entity_summary(entity),
            "note": _gen_note(entity, month),
        })

    diagnostics = {
        "solver": result.solver,
        "matrix_source": result.matrix_source,
        "total_travel_minutes": result.total_travel_minutes,
        "waiting_minutes": result.waiting_minutes,
        "overtime_minutes": result.overtime_minutes,
        "minimum_slack_minutes": result.minimum_slack_minutes,
        "backtrack_ratio": result.backtrack_ratio,
        "skipped": [
            {"stop_id": skipped.stop_id, "reason": skipped.reason}
            for skipped in result.skipped
        ],
        "warnings": warnings + list(result.warnings),
    }
    return scheduled_stops, diagnostics


def _build_day_stops(day_entities: list, candidates: list, month: int) -> list:
    """Phân bổ thời gian & chèn bữa ăn cho 1 ngày."""
    day_stops = []
    # Phân bổ thời gian trong ngày
    current_time = 8 * 60  # 8:00 AM (in minutes)
    for i, item in enumerate(day_entities):
        e = item["entity"]
        etype = e["type"]

        # Thêm bữa ăn
        if current_time >= 11.5 * 60 and not any(s.get("is_meal") for s in day_stops if s.get("time_min", 0) > 11 * 60):
            meal = _find_meal(candidates, item["area"], [s["entity"]["id"] for s in day_stops])
            if meal:
                day_stops.append({
                    "time": _fmt_time(current_time),
                    "time_min": current_time,
                    "entity": _entity_summary(meal["entity"]),
                    "note": "🍜 Nghỉ trưa & thưởng thức đặc sản",
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
