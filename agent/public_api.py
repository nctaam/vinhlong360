"""
vinhlong360 — Public API.

Read-only endpoints for the frontend to consume entities, itineraries,
and search results from the database instead of static data.json.

Mount: app.include_router(public_router)
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Query, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from database import db
from data_quality import entity_quality
from middleware import report_limiter, get_client_ip

router = APIRouter(prefix="/api", tags=["public"])

from collections import OrderedDict

_PLACE_CACHE_MAX = 500
_place_cache: OrderedDict[str, dict] = OrderedDict()
DEFAULT_RELATIONSHIP_LIMIT = 24

# Perf-P0: cache payload /homepage (endpoint nóng nhất) — trước đây scan toàn bảng entity
# + 6×COUNT mỗi request. Curation tất định theo tháng → cache TTL ngắn, theo tháng.
import time as _time
_homepage_cache: dict = {"month": None, "data": None, "ts": 0.0}
_HOMEPAGE_TTL = 120  # giây

_ENTITY_CACHE_MAX = 1000
_entity_cache: OrderedDict[str, tuple[float, dict]] = OrderedDict()
_ENTITY_TTL = 60  # 60s cache per entity

def invalidate_entity_cache(entity_id: str | None = None):
    """Clear entity cache entry or all entries."""
    if entity_id:
        to_del = [k for k in _entity_cache if k.startswith(f"{entity_id}:")]
        for k in to_del:
            del _entity_cache[k]
    else:
        _entity_cache.clear()


def _is_public(e: dict) -> bool:
    """Entity được hiển thị công khai (listing/homepage): loại entity provisional /
    chưa kiểm chứng (auto-learned). Quarantine cho public display — KB chat vẫn dùng,
    nhưng trang công khai KHÔNG show nội dung tự-học chưa duyệt (tránh cảm giác nghiệp dư)."""
    return e.get("status") != "provisional" and e.get("verified") is not False


def invalidate_place_cache():
    """Xoá cache tên/khu-vực xã/phường — gọi sau /reload để tránh phục vụ tên cũ
    khi admin đổi/di chuyển place."""
    _place_cache.clear()
    _homepage_cache.update(month=None, data=None, ts=0.0)  # Perf-P0: refresh homepage sau reload

# GĐ13.6f: báo cáo thông tin sai / nội dung vi phạm — lưu JSONL nhẹ (free-tier),
# admin xem qua /admin/reports để xử lý (takedown/sửa). KHÔNG dùng DB/dịch vụ trả phí.
REPORTS_FILE = Path(__file__).resolve().parent / "data" / "reports.jsonl"
_VALID_TARGET_TYPES = {"facility", "entity", "post", "comment", "other"}

import site_settings


@router.get("/site-settings")
async def get_site_settings(response: Response):
    """Public flat {key: value} dict of all site settings (cached 60s)."""
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=120"
    return site_settings.get_all_public()

def _get_place(place_id: str) -> dict | None:
    if place_id in _place_cache:
        _place_cache.move_to_end(place_id)
        return _place_cache[place_id]
    place = db.get_entity(place_id)
    if place:
        _place_cache[place_id] = {"name": place["name"], "area": place.get("area")}
        if len(_place_cache) > _PLACE_CACHE_MAX:
            _place_cache.popitem(last=False)
    return _place_cache.get(place_id)

def _enrich_place(entities: list[dict]):
    uncached = {e["placeId"] for e in entities if e.get("placeId") and e["placeId"] not in _place_cache}
    if uncached:
        batch = db.get_entities_batch(list(uncached))
        for pid, place in batch.items():
            _place_cache[pid] = {"name": place["name"], "area": place.get("area")}
    for e in entities:
        explicit_area = e.get("area")
        pid = e.get("placeId")
        if pid:
            p = _place_cache.get(pid)
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
    # Support comma-separated types: ?type=experience,attraction,dish
    entity_types: list[str] | None = None
    single_type = type
    if type and "," in type:
        entity_types = [t.strip() for t in type.split(",") if t.strip()]
        single_type = None

    def _in_month(e):
        return month in ((e.get("season") or {}).get("months") or [])

    if q:
        if month:
            full = db.search_entities(q=q, entity_type=single_type, area=area, limit=100000, entity_types=entity_types, public_only=True)
            filtered = [e for e in full if _in_month(e)]
            total = len(filtered)
            results = filtered[offset:offset + limit]
        else:
            results = db.search_entities(q=q, entity_type=single_type, area=area, limit=limit, offset=offset, entity_types=entity_types, public_only=True)
            total = db.count_entities_filtered(entity_type=single_type, area=area, q=q, entity_types=entity_types, public_only=True)
    elif month:
        full = db.list_entities(entity_type=single_type, area=area, limit=100000, offset=0, entity_types=entity_types, public_only=True)
        filtered = [e for e in full if _in_month(e)]
        total = len(filtered)
        results = filtered[offset:offset + limit]
    else:
        results = db.list_entities(entity_type=single_type, area=area, limit=limit, offset=offset, entity_types=entity_types, public_only=True)
        total = db.count_entities_filtered(entity_type=single_type, area=area, q=q, entity_types=entity_types, public_only=True)
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
    relationships, total = db.get_relationships(
        entity_id,
        limit=limit,
        offset=offset,
        rel_type=type,
        include_near=include_near,
        return_total=True,
    )
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
    response: Response,
    relationship_limit: int = Query(DEFAULT_RELATIONSHIP_LIMIT, ge=0, le=100),
):
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=120"
    cache_key = f"{entity_id}:{relationship_limit}"
    now = _time.time()
    cached = _entity_cache.get(cache_key)
    if cached and now - cached[0] < _ENTITY_TTL:
        _entity_cache.move_to_end(cache_key)
        return cached[1]

    entity = db.get_entity(entity_id)
    if not entity:
        return JSONResponse(status_code=404, content={"error": "not_found"})
    rels, rel_total = db.get_relationships(entity_id, limit=relationship_limit, return_total=True)
    entity["relationship_total"] = rel_total
    entity["relationships"] = rels
    _enrich_entity_place(entity)
    entity["quality"] = entity_quality(entity)

    _entity_cache[cache_key] = (now, entity)
    while len(_entity_cache) > _ENTITY_CACHE_MAX:
        _entity_cache.popitem(last=False)

    return entity


@router.get("/places")
async def list_places(response: Response, area: Optional[str] = None):
    response.headers["Cache-Control"] = "public, max-age=3600, stale-while-revalidate=7200"
    db.initialize()
    def _query():
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
    return await asyncio.to_thread(_query)


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
    stop_ids = [s.get("id", "") for s in it.get("stops", []) if s.get("id")]
    entities = db.get_entities_batch(stop_ids)
    for stop in it.get("stops", []):
        entity = entities.get(stop.get("id", ""))
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
    request: Request,
    q: str = Query(..., min_length=1, max_length=200),
    type: Optional[str] = None,
    area: Optional[str] = None,
    limit: int = Query(20, le=100),
):
    from ratelimit import check_rate
    check_rate(f"search:{get_client_ip(request)}", 30, 60, "Tìm kiếm quá nhanh. Vui lòng thử lại sau.")
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


_GENERIC_NAMES = {"tắm sông", "đi ghe", "đi đò", "tham quan", "du lịch",
                   "ăn uống", "mua sắm", "chụp ảnh", "câu cá", "dạo phố"}


def _homepage_score(e: dict, month: int) -> float:
    from smart_rank import smart_score
    s = smart_score(e, month=month, q_match_level="none")
    if e.get("images"):
        s += 2.0
    if len(e.get("summary", "") or "") > 80:
        s += 1.0
    if e["name"].lower().strip() in _GENERIC_NAMES:
        s -= 5.0
    return s


def _name_key(name: str) -> str:
    """Normalize name for dedup: lowercase, strip common prefixes/suffixes."""
    import re
    n = name.lower().strip()
    n = re.sub(r"^(hái|mùa|tham quan|khu du lịch|làng nghề)\s+", "", n)
    n = re.sub(r"\s+(tại|ở|cù lao|cồn)\s+.*$", "", n)
    return n


def _dedup_by_name(entities: list[dict], limit: int) -> list[dict]:
    """Pick top entities, skipping near-duplicate names and same placeId."""
    result = []
    seen_keys: set[str] = set()
    seen_place_ids: set[str] = set()
    for e in entities:
        nk = _name_key(e["name"])
        pid = e.get("placeId") or ""
        if any(nk in sk or sk in nk for sk in seen_keys if len(nk) > 3 and len(sk) > 3):
            continue
        if pid and pid in seen_place_ids:
            continue
        result.append(e)
        seen_keys.add(nk)
        if pid:
            seen_place_ids.add(pid)
        if len(result) >= limit:
            break
    return result


def _diverse_pick(entities: list[dict], max_per_type: int = 2,
                  max_per_area: int = 4, limit: int = 8,
                  exclude_ids: set | None = None) -> list[dict]:
    result = []
    type_counts: dict[str, int] = {}
    area_counts: dict[str, int] = {}
    seen_keys: set[str] = set()
    seen_place_ids: set[str] = set()
    for e in entities:
        if exclude_ids and e["id"] in exclude_ids:
            continue
        t = e["type"]
        a = e.get("place_area") or "unknown"
        if type_counts.get(t, 0) >= max_per_type:
            continue
        if area_counts.get(a, 0) >= max_per_area:
            continue
        nk = _name_key(e["name"])
        pid = e.get("placeId") or ""
        if any(nk in sk or sk in nk for sk in seen_keys if len(nk) > 3 and len(sk) > 3):
            continue
        if pid and pid in seen_place_ids:
            continue
        result.append(e)
        type_counts[t] = type_counts.get(t, 0) + 1
        area_counts[a] = area_counts.get(a, 0) + 1
        seen_keys.add(nk)
        if pid:
            seen_place_ids.add(pid)
        if len(result) >= limit:
            break
    return result


@router.get("/homepage")
async def homepage_curated(response: Response):
    """Curated homepage: smart-scored, type/area diverse, seasonal-aware, deduped."""
    response.headers["Cache-Control"] = "public, max-age=120, stale-while-revalidate=300"
    month = datetime.now().month

    # Perf-P0: trả cache nếu còn hạn + cùng tháng (tránh scan toàn bảng mỗi request)
    _now = _time.time()
    if (_homepage_cache["data"] is not None and _homepage_cache["month"] == month
            and _now - _homepage_cache["ts"] < _HOMEPAGE_TTL):
        return _homepage_cache["data"]

    all_ents = db.list_entities(limit=100000, offset=0)
    public = [e for e in all_ents if _is_public(e) and not _event_is_past(e)]
    _enrich_place(public)

    for e in public:
        e["_score"] = _homepage_score(e, month)

    # Seasonal: entities actually in season this month (not year-round)
    def _in_season(e):
        s = e.get("season")
        if not s or not isinstance(s, dict):
            return False
        months = s.get("months") or []
        if len(months) >= 11:
            return False
        return month in months or month in (s.get("peak") or [])

    seasonal_pool = [e for e in public
                     if e["type"] in ("product", "experience", "dish")
                     and _in_season(e)]
    seasonal_pool.sort(key=lambda e: e["_score"], reverse=True)
    seasonal = _dedup_by_name(seasonal_pool, limit=4)

    seasonal_ids = {e["id"] for e in seasonal}

    # Upcoming events (next 30 days, sorted by date_start)
    # Only show events with reliable dates: must have lunar_date OR
    # consistent month field. Exclude cat=mua (seasonal, not event).
    today = datetime.now().date()
    from datetime import timedelta
    cutoff = today + timedelta(days=30)
    upcoming_pool = []
    for e in public:
        if e["type"] != "event":
            continue
        attrs = e.get("attributes") or {}
        cat = attrs.get("category", "")
        if cat == "mua":
            continue
        ds = attrs.get("date_start")
        if not ds:
            continue
        try:
            d = datetime.strptime(ds, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue
        # Skip if month field set but conflicts with date_start (fabricated date)
        attr_month = attrs.get("month")
        if attr_month and isinstance(attr_month, (int, float)) and int(attr_month) != d.month:
            continue
        if today <= d <= cutoff:
            e["_days_until"] = (d - today).days
            upcoming_pool.append(e)
    upcoming_pool.sort(key=lambda x: x.get("_days_until", 999))
    upcoming_events = upcoming_pool[:3]

    upcoming_ids = {e["id"] for e in upcoming_events}
    exclude_from_exp = seasonal_ids | upcoming_ids

    # Experiences: tourism types, diverse, excluding seasonal + upcoming event dupes
    tourism = [e for e in public if e["type"] in _TOURISM_TYPES]
    tourism.sort(key=lambda e: e.get("_score", 0), reverse=True)
    experiences = _diverse_pick(tourism, max_per_type=2, max_per_area=4, limit=8,
                                exclude_ids=exclude_from_exp)

    # Products fallback (when seasonal is empty)
    products_pool = [e for e in public if e["type"] == "product"]
    products_pool.sort(key=lambda e: e.get("_score", 0), reverse=True)
    products = _dedup_by_name(products_pool, limit=8)

    # Itineraries: score by seasonal relevance + area diversity
    all_itineraries = db.list_itineraries()
    for it in all_itineraries:
        it_score = 0.0
        stops = it.get("stops") or []
        for stop in stops:
            if isinstance(stop, str):
                eid = stop
            else:
                eid = stop.get("entity_id") or stop.get("id", "")
            matched = next((e for e in public if e["id"] == eid), None)
            if matched:
                if _in_season(matched):
                    it_score += 2.0
                if matched.get("images"):
                    it_score += 0.5
        dur = it.get("duration") or ""
        if dur:
            import re
            m = re.search(r"(\d+)", str(dur))
            if m:
                try:
                    d = int(m.group(1))
                    if 1 <= d <= 3:
                        it_score += 1.0
                except (ValueError, TypeError):
                    pass
        it["_score"] = it_score
    all_itineraries.sort(key=lambda x: x.get("_score", 0), reverse=True)
    seen_areas: set[str] = set()
    itineraries = []
    for it in all_itineraries:
        a = it.get("area", "")
        if a and a in seen_areas and len(itineraries) < 3:
            continue
        itineraries.append(it)
        if a:
            seen_areas.add(a)
        if len(itineraries) >= 4:
            break
    for it in itineraries:
        it.pop("_score", None)

    stats = db.stats()

    # Area counts for region tiles
    card_types = {"product", "dish", "drink", "experience", "attraction", "nature",
                  "craft_village", "history", "accommodation", "event"}
    area_counts: dict[str, int] = {}
    for e in public:
        a = e.get("place_area") or e.get("area")
        if e["type"] in card_types and a:
            area_counts[a] = area_counts.get(a, 0) + 1

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
    # A7: admin can override taglines via site_settings (homepage.seasonal_taglines:
    # a {"<month>": "<text>"} object). Falls back to defaults; {} on SQLite.
    seasonal_tagline = ""
    try:
        _ov = site_settings.get_all_public().get("homepage.seasonal_taglines")
        if isinstance(_ov, dict):
            seasonal_tagline = _ov.get(str(month)) or _ov.get(month) or ""
    except Exception:
        seasonal_tagline = ""
    if not seasonal_tagline:
        seasonal_tagline = _TAGLINES.get(month, "Khám phá miệt vườn theo cách của người bản địa")

    # Top dishes by rating (social proof for "Tinh hoa" section)
    dishes_pool = [e for e in public
                   if e["type"] == "dish"
                   and isinstance((e.get("attributes") or {}).get("rating"), (int, float))
                   and (e.get("attributes") or {}).get("review_count", 0) >= 3]
    dishes_pool.sort(key=lambda e: (
        (e.get("attributes") or {}).get("rating", 0),
        (e.get("attributes") or {}).get("review_count", 0),
    ), reverse=True)
    top_dishes = _dedup_by_name(dishes_pool, limit=6)

    for section in [seasonal, experiences, products, top_dishes]:
        for e in section:
            e.pop("_score", None)

    for e in upcoming_events:
        e.pop("_score", None)
        e["days_until"] = e.pop("_days_until", None)

    # Trending: entities with highest chat/search hit counts
    from proactive import get_trending_entities
    trending_raw = get_trending_entities(limit=6)
    trending = []
    for t in trending_raw:
        ent = next((e for e in public if e["id"] == t["id"]), None)
        if ent:
            item = {k: ent[k] for k in ("id", "name", "type", "summary", "images", "place_name", "place_area") if k in ent}
            item["hit_count"] = t["hit_count"]
            trending.append(item)

    result = {
        "seasonal": seasonal,
        "experiences": experiences,
        "products": products,
        "top_dishes": top_dishes,
        "trending": trending,
        "itineraries": itineraries,
        "stats": stats,
        "area_counts": area_counts,
        "month": month,
        "upcoming_events": upcoming_events,
        "seasonal_tagline": seasonal_tagline,
    }
    _homepage_cache.update(month=month, data=result, ts=_now)
    return result


@router.get("/events")
async def list_events(
    response: Response,
    area: Optional[str] = None,
    include_past: bool = False,
    limit: int = Query(50, le=200),
):
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=600"
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

    # Exclude seasonal items (cat=mua) and events with unreliable dates
    def _date_reliable(e):
        attrs = e.get("attributes") or {}
        if attrs.get("category") == "mua":
            return False
        ds = attrs.get("date_start")
        attr_month = attrs.get("month")
        if ds and attr_month and isinstance(attr_month, (int, float)):
            try:
                d = datetime.strptime(ds, "%Y-%m-%d").date()
                if int(attr_month) != d.month:
                    return False
            except (ValueError, TypeError):
                pass
        return True

    events = [e for e in events if _date_reliable(e)]

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


# ── ND 147/2024 Compliance & Transparency ──────────────────────────────

@router.get("/transparency")
async def transparency_report():
    """ND 147/2024 transparency: moderation policy, contact, takedown SLA."""
    return {
        "platform": "VinhLong360",
        "legal_entity": "Cá nhân vận hành — vinhlong360.vn",
        "contact_email": "lienhe@vinhlong360.vn",
        "content_policy": {
            "moderation": "Tất cả nội dung người dùng được kiểm duyệt tự động trước khi hiển thị.",
            "takedown_sla_hours": 24,
            "appeal_process": "Gửi email đến lienhe@vinhlong360.vn trong 7 ngày.",
            "prohibited_content": [
                "Vi phạm pháp luật Việt Nam",
                "Thông tin sai sự thật gây hoang mang",
                "Xúc phạm, phân biệt đối xử",
                "Spam, quảng cáo trái phép",
                "Nội dung khiêu dâm, bạo lực",
            ],
        },
        "data_practices": {
            "storage_location": "Việt Nam",
            "data_retention": "Dữ liệu cá nhân được lưu khi tài khoản hoạt động. Xóa khi deactivate.",
            "third_party_sharing": "Không chia sẻ dữ liệu với bên thứ ba ngoài mục đích vận hành.",
        },
        "nd147_compliance": {
            "regulation": "Nghị định 147/2024/NĐ-CP",
            "content_removal_within_24h": True,
            "user_data_on_request": True,
            "cooperation_with_authorities": True,
        },
    }
