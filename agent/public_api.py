"""
vinhlong360 — Public API.

Read-only endpoints for the frontend to consume entities, itineraries,
and search results from the database instead of static data.json.

Mount: app.include_router(public_router)
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from database import db
from data_quality import entity_quality
from middleware import report_limiter, get_client_ip

router = APIRouter(prefix="/api", tags=["public"])

_place_cache: dict[str, dict] = {}
DEFAULT_RELATIONSHIP_LIMIT = 24


def _is_public(e: dict) -> bool:
    """Entity được hiển thị công khai (listing/homepage): loại entity provisional /
    chưa kiểm chứng (auto-learned). Quarantine cho public display — KB chat vẫn dùng,
    nhưng trang công khai KHÔNG show nội dung tự-học chưa duyệt (tránh cảm giác nghiệp dư)."""
    return e.get("status") != "provisional" and e.get("verified") is not False


def invalidate_place_cache():
    """Xoá cache tên/khu-vực xã/phường — gọi sau /reload để tránh phục vụ tên cũ
    khi admin đổi/di chuyển place."""
    _place_cache.clear()

# GĐ13.6f: báo cáo thông tin sai / nội dung vi phạm — lưu JSONL nhẹ (free-tier),
# admin xem qua /admin/reports để xử lý (takedown/sửa). KHÔNG dùng DB/dịch vụ trả phí.
REPORTS_FILE = Path(__file__).resolve().parent / "data" / "reports.jsonl"
_VALID_TARGET_TYPES = {"facility", "entity", "post", "comment", "other"}

def _get_place(place_id: str) -> dict | None:
    if place_id in _place_cache:
        return _place_cache[place_id]
    place = db.get_entity(place_id)
    if place:
        _place_cache[place_id] = {"name": place["name"], "area": place.get("area")}
    return _place_cache.get(place_id)

def _enrich_place(entities: list[dict]):
    for e in entities:
        explicit_area = e.get("area")
        pid = e.get("placeId")
        if pid:
            p = _get_place(pid)
            if p:
                e["place_name"] = p["name"]
                e["place_area"] = explicit_area or p.get("area")
        elif explicit_area:
            e["place_area"] = explicit_area
        e["quality"] = entity_quality(e)

def _enrich_entity_place(entity: dict):
    pid = entity.get("placeId")
    explicit_area = entity.get("area")
    if pid:
        p = _get_place(pid)
        if p:
            entity["place_name"] = p["name"]
            entity["place_area"] = explicit_area or p.get("area")
    elif explicit_area:
        entity["place_area"] = explicit_area


@router.get("/entities")
async def list_entities(
    type: Optional[str] = None,
    area: Optional[str] = None,
    q: Optional[str] = None,
    month: Optional[int] = None,
    limit: int = Query(50, le=1000),
    offset: int = Query(0, ge=0),
):
    def _in_month(e):
        return month in ((e.get("season") or {}).get("months") or [])

    if q:
        results = db.search_entities(q=q, entity_type=type, area=area, limit=limit)
        if month:
            results = [e for e in results if _in_month(e)]
        total = len([e for e in results if _in_month(e)]) if month else db.count_entities_filtered(
            entity_type=type, area=area, q=q)
    elif month:
        # GĐ-audit fix: lọc month TRÊN TOÀN BỘ tập (không phân trang trước rồi mới lọc) →
        # total đúng + offset/limit đúng. Dataset nhỏ (<2k) nên nạp full an toàn.
        full = db.list_entities(entity_type=type, area=area, limit=100000, offset=0)
        filtered = [e for e in full if _in_month(e)]
        total = len(filtered)
        results = filtered[offset:offset + limit]
    else:
        results = db.list_entities(entity_type=type, area=area, limit=limit, offset=offset)
        total = db.count_entities_filtered(entity_type=type, area=area, q=q)

    # Quarantine: không hiển thị entity provisional/auto-learned chưa duyệt ở trang công khai.
    results = [e for e in results if _is_public(e)]
    _enrich_place(results)
    return {"total": total, "entities": results}


@router.get("/entities/{entity_id}/relationships")
async def get_entity_relationships(
    entity_id: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    type: Optional[str] = None,
    include_near: bool = True,
):
    entity = db.get_entity(entity_id)
    if not entity:
        return JSONResponse(status_code=404, content={"error": "not_found"})
    relationships = db.get_relationships(
        entity_id,
        limit=limit,
        offset=offset,
        rel_type=type,
        include_near=include_near,
    )
    total = db.count_relationships(entity_id, rel_type=type, include_near=include_near)
    return {
        "entity_id": entity_id,
        "total": total,
        "limit": limit,
        "offset": offset,
        "relationships": relationships,
    }

@router.get("/entities/{entity_id}")
async def get_entity(
    entity_id: str,
    relationship_limit: int = Query(DEFAULT_RELATIONSHIP_LIMIT, ge=0, le=100),
):
    entity = db.get_entity(entity_id)
    if not entity:
        return JSONResponse(status_code=404, content={"error": "not_found"})
    entity["relationship_total"] = db.count_relationships(entity_id)
    entity["relationships"] = db.get_relationships(entity_id, limit=relationship_limit)
    _enrich_entity_place(entity)
    entity["quality"] = entity_quality(entity)
    return entity


@router.get("/places")
async def list_places(area: Optional[str] = None):
    db.initialize()
    ph = db._ph
    with db._conn() as conn:
        if area:
            rows = db._fetchall(conn,
                f"SELECT id, name, area, level FROM entities WHERE type = 'place' AND area = {ph} ORDER BY name",
                (area,))
        else:
            rows = db._fetchall(conn,
                "SELECT id, name, area, level FROM entities WHERE type = 'place' ORDER BY name")
    return [db._row_to_dict(r) for r in rows]


@router.get("/facilities")
async def list_facilities(place: Optional[str] = None):
    """GĐ13.4: danh bạ hành chính — cơ quan công vụ (UBND/công an/...) theo xã/phường."""
    return {"facilities": db.facilities_by_place(place)}


# Nhóm loại entity cho trang hub xã/phường (theo 4 mục người dùng cần).
_WARD_GROUPS = {
    "tourism": {"attraction", "nature", "experience", "craft_village", "history", "event"},
    "lodging": {"accommodation"},
    "products": {"product", "dish", "drink"},
}


@router.get("/places/{place_id}/overview")
async def place_overview(place_id: str):
    """Trang hub 1 xã/phường: danh bạ hành chính + du lịch + lưu trú + sản phẩm.

    Gom theo placeId trong 1 lượt gọi. facilities rỗng đến khi có dữ liệu thật (Track-H 13.6).
    """
    place = db.get_entity(place_id)
    if not place or place.get("type") != "place":
        return JSONResponse(status_code=404, content={"error": "not_found", "detail": "Không phải xã/phường"})

    ents = db.entities_by_place(place_id)
    groups: dict[str, list] = {"tourism": [], "lodging": [], "products": [], "other": []}
    for e in ents:
        t = e.get("type")
        placed = False
        for g, types in _WARD_GROUPS.items():
            if t in types:
                groups[g].append(e)
                placed = True
                break
        if not placed:
            groups["other"].append(e)

    return {
        "place": {"id": place["id"], "name": place.get("name"), "area": place.get("area"),
                  "level": place.get("level"), "summary": place.get("summary"),
                  "attributes": place.get("attributes", {}),
                  "coordinates": place.get("coordinates")},
        "facilities": db.facilities_by_place(place_id),
        "counts": {g: len(v) for g, v in groups.items()},
        "tourism": groups["tourism"],
        "lodging": groups["lodging"],
        "products": groups["products"],
        "other": groups["other"],
    }


@router.get("/itineraries")
async def list_itineraries(area: Optional[str] = None):
    return db.list_itineraries(area=area)


@router.get("/itineraries/{itin_id}")
async def get_itinerary(itin_id: str):
    it = db.get_itinerary(itin_id)
    if not it:
        return JSONResponse(status_code=404, content={"error": "not_found"})
    for stop in it.get("stops", []):
        entity = db.get_entity(stop.get("id", ""))
        if entity:
            stop["name"] = entity["name"]
            if not stop.get("summary"):
                stop["summary"] = entity.get("summary", "")
            stop["type"] = entity["type"]
            if entity.get("coordinates"):
                stop["coordinates"] = entity["coordinates"]
    return it


@router.get("/search")
async def search(
    q: str = Query(..., min_length=1, max_length=200),
    type: Optional[str] = None,
    area: Optional[str] = None,
    limit: int = Query(20, le=100),
):
    results = db.search_entities(q=q, entity_type=type, area=area, limit=limit)
    _enrich_place(results)
    total = db.count_entities_filtered(entity_type=type, area=area, q=q)
    return {"q": q, "total": total, "results": results}


@router.get("/stats")
async def public_stats():
    return db.stats()


# ── Homepage curated feed ──────────────────────────────────────────

_TOURISM_TYPES = {"experience", "attraction", "dish", "nature", "craft_village",
                  "history", "accommodation", "event"}


def _event_is_past(e: dict) -> bool:
    """True if event has date_end and it's already passed."""
    attrs = e.get("attributes") or {}
    date_end = attrs.get("date_end")
    if not date_end:
        return False
    try:
        return datetime.strptime(date_end, "%Y-%m-%d").date() < datetime.now().date()
    except (ValueError, TypeError):
        return False


def _homepage_score(e: dict, month: int) -> float:
    from smart_rank import smart_score
    s = smart_score(e, month=month, q_match_level="none")
    if e.get("images"):
        s += 2.0
    if len(e.get("summary", "") or "") > 80:
        s += 1.0
    return s


def _diverse_pick(entities: list[dict], max_per_type: int = 2,
                  max_per_area: int = 4, limit: int = 8) -> list[dict]:
    result = []
    type_counts: dict[str, int] = {}
    area_counts: dict[str, int] = {}
    for e in entities:
        t = e["type"]
        a = e.get("place_area") or "unknown"
        if type_counts.get(t, 0) >= max_per_type:
            continue
        if area_counts.get(a, 0) >= max_per_area:
            continue
        result.append(e)
        type_counts[t] = type_counts.get(t, 0) + 1
        area_counts[a] = area_counts.get(a, 0) + 1
        if len(result) >= limit:
            break
    return result


@router.get("/homepage")
async def homepage_curated():
    """Curated homepage: smart-scored, type/area diverse, seasonal-aware."""
    month = datetime.now().month

    all_ents = db.list_entities(limit=100000, offset=0)
    public = [e for e in all_ents if _is_public(e) and not _event_is_past(e)]
    _enrich_place(public)

    for e in public:
        e["_score"] = _homepage_score(e, month)

    # Seasonal: entities actually in season this month (not year-round)
    def _in_season(e):
        s = e.get("season")
        if not s:
            return False
        months = s.get("months") or []
        if len(months) >= 11:
            return False
        return month in months or month in (s.get("peak") or [])

    seasonal_pool = [e for e in public
                     if e["type"] in ("product", "experience", "dish", "event")
                     and _in_season(e)]
    seasonal_pool.sort(key=lambda e: e["_score"], reverse=True)
    seasonal = seasonal_pool[:4]

    seasonal_ids = {e["id"] for e in seasonal}

    # Experiences: tourism types, diverse, excluding seasonal duplicates
    tourism = [e for e in public
               if e["type"] in _TOURISM_TYPES and e["id"] not in seasonal_ids]
    tourism.sort(key=lambda e: e["_score"], reverse=True)
    experiences = _diverse_pick(tourism, max_per_type=2, max_per_area=4, limit=8)

    # Products fallback (when seasonal is empty)
    products_pool = [e for e in public if e["type"] == "product"]
    products_pool.sort(key=lambda e: e["_score"], reverse=True)
    products = products_pool[:8]

    itineraries = db.list_itineraries()[:4]
    stats = db.stats()

    # Area counts for region tiles
    card_types = {"product", "dish", "drink", "experience", "attraction", "nature",
                  "craft_village", "history", "accommodation", "event"}
    area_counts: dict[str, int] = {}
    for e in public:
        a = e.get("place_area") or e.get("area")
        if e["type"] in card_types and a:
            area_counts[a] = area_counts.get(a, 0) + 1

    # Upcoming events (next 30 days, sorted by date_start)
    today = datetime.now().date()
    from datetime import timedelta
    cutoff = today + timedelta(days=30)
    upcoming_pool = []
    for e in public:
        if e["type"] != "event":
            continue
        attrs = e.get("attributes") or {}
        ds = attrs.get("date_start")
        if not ds:
            continue
        try:
            d = datetime.strptime(ds, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue
        if today <= d <= cutoff:
            e["_days_until"] = (d - today).days
            upcoming_pool.append(e)
    upcoming_pool.sort(key=lambda x: x.get("_days_until", 999))
    upcoming_events = upcoming_pool[:3]
    for e in upcoming_events:
        e.pop("_score", None)
        e["days_until"] = e.pop("_days_until", None)

    # Seasonal tagline
    _TAGLINES = {
        1: "Tết Nguyên đán — không khí miệt vườn ngập sắc xuân",
        2: "Mùa xuân miệt vườn — trái cây đầu mùa đang chín",
        3: "Tháng 3 lễ hội đình làng — khám phá văn hóa cổ truyền",
        4: "Mùa Chôl Chnăm Thmây — lễ hội Khmer sôi động",
        5: "Mùa trái cây bắt đầu — chôm chôm, sầu riêng, măng cụt",
        6: "Mùa trái cây đang chín rộ — miệt vườn ngọt lịm",
        7: "Giữa mùa trái cây — vườn trái cây mở cửa đón khách",
        8: "Mùa Vu Lan — lễ hội lồng đèn sắp đến",
        9: "Trung thu miệt vườn — lồng đèn và bánh dân gian",
        10: "Mùa Ok Om Bok — đua ghe ngo sôi động miền Tây",
        11: "Cuối năm — khám phá làng nghề và đặc sản Tết",
        12: "Mùa Tết đang đến — đặc sản và quà tặng miệt vườn",
    }
    seasonal_tagline = _TAGLINES.get(month, "Khám phá miệt vườn theo cách của người bản địa")

    for section in [seasonal, experiences, products]:
        for e in section:
            e.pop("_score", None)

    return {
        "seasonal": seasonal,
        "experiences": experiences,
        "products": products,
        "itineraries": itineraries,
        "stats": stats,
        "area_counts": area_counts,
        "month": month,
        "upcoming_events": upcoming_events,
        "seasonal_tagline": seasonal_tagline,
    }


@router.get("/events")
async def list_events(
    area: Optional[str] = None,
    include_past: bool = False,
    limit: int = Query(50, le=200),
):
    """Sự kiện: sắp xếp theo date_start, mặc định ẩn sự kiện đã qua."""
    today = datetime.now().date()
    all_ents = db.list_entities(entity_type="event", limit=100000, offset=0)
    events = [e for e in all_ents if _is_public(e)]
    _enrich_place(events)

    if area:
        events = [e for e in events
                  if (e.get("place_area") or e.get("area")) == area]

    if not include_past:
        events = [e for e in events if not _event_is_past(e)]

    def _sort_key(e):
        attrs = e.get("attributes") or {}
        ds = attrs.get("date_start")
        if ds:
            try:
                return (0, datetime.strptime(ds, "%Y-%m-%d").date())
            except (ValueError, TypeError):
                pass
        s = (e.get("season") or {}).get("months") or []
        if s:
            first = min(s)
            d = datetime(today.year, first, 1).date()
            if d < today:
                d = datetime(today.year + 1, first, 1).date()
            return (1, d)
        return (2, datetime(today.year, 12, 31).date())

    events.sort(key=_sort_key)
    return {"total": len(events), "events": events[:limit]}


class ReportIn(BaseModel):
    target_id: str = Field(..., min_length=1, max_length=200)
    target_type: str = Field("entity", max_length=20)
    reason: str = Field(..., min_length=1, max_length=60)
    detail: str = Field("", max_length=2000)
    contact: str = Field("", max_length=120)


@router.post("/report")
async def submit_report(payload: ReportIn, request: Request):
    """GĐ13.6f: tiếp nhận báo-sai (facility/entity) & báo cáo nội dung (post/comment).

    Lưu vào reports.jsonl cho admin xử lý — KHÔNG đăng/khoá tự động. Rate-limit theo IP.
    """
    ip = get_client_ip(request)
    allowed, info = report_limiter.is_allowed(ip)
    if not allowed:
        return JSONResponse(
            status_code=429,
            content={"error": "rate_limited", "retry_after": info.get("retry_after", 60),
                     "message": "Bạn gửi quá nhiều báo cáo. Vui lòng thử lại sau."},
        )
    target_type = payload.target_type if payload.target_type in _VALID_TARGET_TYPES else "other"
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "target_id": payload.target_id.strip(),
        "target_type": target_type,
        "reason": payload.reason.strip(),
        "detail": payload.detail.strip(),
        "contact": payload.contact.strip(),
        "ip": ip,
        "status": "open",
    }
    try:
        REPORTS_FILE.parent.mkdir(exist_ok=True)
        with open(REPORTS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        return JSONResponse(status_code=500, content={"error": "store_failed"})
    return {"ok": True, "message": "Đã ghi nhận. Cảm ơn bạn đã góp ý — chúng tôi sẽ kiểm tra."}
