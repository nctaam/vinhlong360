"""
vinhlong360 — Public API.

Read-only endpoints for the frontend to consume entities, itineraries,
and search results from the database instead of static data.json.

Mount: app.include_router(public_router)
"""

import asyncio
import hashlib
import json
import logging
import math
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from database import db
from data_quality import entity_quality
from middleware import report_limiter, get_client_ip
from auth_middleware import validate_path_id, require_pg, require_user, require_csrf

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
_homepage_rebuilding = False
_homepage_lock = asyncio.Lock()

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


def _build_source_freshness(entity: dict) -> dict:
    """Compute source freshness metadata for entity detail response."""
    from data_quality import source_info
    src = source_info(entity)
    updated_at = entity.get("updatedAt")
    days_since = None
    if updated_at:
        try:
            updated_dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            days_since = (datetime.now(timezone.utc) - updated_dt).days
        except (ValueError, TypeError):
            pass
    if days_since is None:
        status = "unknown"
    elif days_since <= 90:
        status = "fresh"
    elif days_since <= 180:
        status = "aging"
    else:
        status = "stale"
    return {
        "source_title": src.get("title") or None,
        "source_url": src.get("url") or None,
        "updated_at": updated_at,
        "days_since_update": days_since,
        "freshness_status": status,
    }


_PRACTICAL_FACTS_KEYS = [
    "hours", "admission_fee", "phone", "address", "website",
    "zalo", "parking", "best_time", "peak_hours", "tips",
    "price_range", "duration", "accessibility",
]


def _build_practical_facts(entity: dict) -> dict:
    """U-07: Extract standardized practical info from entity attributes."""
    attrs = entity.get("attributes") or {}
    facts = {}
    for key in _PRACTICAL_FACTS_KEYS:
        facts[key] = attrs.get(key)
    if facts["hours"] is None:
        facts["hours"] = attrs.get("open_hours") or attrs.get("opening_hours")
    if facts["admission_fee"] is None:
        facts["admission_fee"] = attrs.get("admission") or attrs.get("ticket_price")
    if facts["price_range"] is None:
        facts["price_range"] = attrs.get("price") or attrs.get("gia")
    has_any = any(v is not None for v in facts.values())
    facts["_completeness"] = sum(1 for v in facts.values() if v is not None and v != "_completeness")
    return facts if has_any else facts


def invalidate_place_cache():
    """Xoá cache tên/khu-vực xã/phường — gọi sau /reload để tránh phục vụ tên cũ
    khi admin đổi/di chuyển place."""
    _place_cache.clear()
    _homepage_cache.update(month=None, data=None, ts=0.0)  # Perf-P0: refresh homepage sau reload

# GĐ13.6f: báo cáo thông tin sai / nội dung vi phạm — lưu JSONL nhẹ (free-tier),
# admin xem qua /admin/reports để xử lý (takedown/sửa). KHÔNG dùng DB/dịch vụ trả phí.
REPORTS_FILE = Path(__file__).resolve().parent / "data" / "reports.jsonl"
SEARCH_LOG_FILE = Path(__file__).resolve().parent / "data" / "search_queries.jsonl"
_VALID_TARGET_TYPES = {"facility", "entity", "post", "comment", "other"}

_JSONL_MAX_LINES = 5000
import threading as _threading
_jsonl_lock = _threading.Lock()


def _maybe_rotate_jsonl(filepath: Path) -> None:
    try:
        if not filepath.exists():
            return
        lines = filepath.read_text(encoding="utf-8").splitlines()
        if len(lines) <= _JSONL_MAX_LINES:
            return
        archive = filepath.with_suffix(f".{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.jsonl")
        archive.write_text("\n".join(lines[:-_JSONL_MAX_LINES]) + "\n", encoding="utf-8")
        tmp = filepath.with_suffix(".tmp")
        tmp.write_text("\n".join(lines[-_JSONL_MAX_LINES:]) + "\n", encoding="utf-8")
        tmp.replace(filepath)
    except Exception:
        logger.exception("JSONL rotation failed for %s", filepath)


def _log_search_query(q: str, entity_type: str | None, area: str | None, total: int) -> None:
    try:
        record = json.dumps({
            "ts": datetime.now(timezone.utc).isoformat(),
            "q": q[:200],
            "type": entity_type,
            "area": area,
            "results": total,
        }, ensure_ascii=False)
        with _jsonl_lock:
            SEARCH_LOG_FILE.parent.mkdir(exist_ok=True)
            with open(SEARCH_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(record + "\n")
            _maybe_rotate_jsonl(SEARCH_LOG_FILE)
    except Exception:
        pass


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


_MINIMAL_FIELDS = {"id", "name", "type", "summary", "images", "place_name",
                    "place_area", "coordinates", "attributes"}


def _to_minimal(entity: dict) -> dict:
    out = {k: entity[k] for k in _MINIMAL_FIELDS if k in entity}
    imgs = entity.get("images")
    if imgs and isinstance(imgs, list):
        out["images"] = imgs[:1]
    attrs = entity.get("attributes") or {}
    out["rating"] = attrs.get("rating")
    out["review_count"] = attrs.get("review_count", 0)
    return out


@router.get("/entities")
async def list_entities(
    type: Optional[str] = Query(None, max_length=100),
    area: Optional[str] = Query(None, max_length=50),
    q: Optional[str] = Query(None, max_length=200),
    month: Optional[int] = Query(None, ge=1, le=12),
    sort: Optional[str] = Query(None, pattern="^(rating|newest|name)$"),
    fields: Optional[str] = Query(None, pattern="^(minimal|full)$"),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0, le=10000),
):
    entity_types: list[str] | None = None
    single_type = type
    if type and "," in type:
        entity_types = [t.strip() for t in type.split(",") if t.strip()][:10]
        single_type = None

    db_sort = sort if sort in ("rating", "name", "newest") else None
    db_month = month if month else None

    if q:
        results = await asyncio.to_thread(db.search_entities, q=q, entity_type=single_type, area=area, limit=limit, offset=offset, entity_types=entity_types, public_only=True, month=db_month)
        total = await asyncio.to_thread(db.count_entities_filtered, entity_type=single_type, area=area, q=q, entity_types=entity_types, public_only=True, month=db_month)
    else:
        results = await asyncio.to_thread(db.list_entities, entity_type=single_type, area=area, limit=limit, offset=offset, entity_types=entity_types, public_only=True, sort=db_sort, month=db_month)
        total = await asyncio.to_thread(db.count_entities_filtered, entity_type=single_type, area=area, entity_types=entity_types, public_only=True, month=db_month)
    _enrich_place(results)
    if fields == "minimal":
        results = [_to_minimal(e) for e in results]
    return {"total": total, "entities": results}


@router.get("/entities/{entity_id}/relationships")
async def get_entity_relationships(
    entity_id: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0, le=10000),
    type: Optional[str] = Query(None, max_length=50),
    include_near: bool = True,
):
    validate_path_id(entity_id, "entity_id")
    def _query():
        e = db.get_entity(entity_id)
        if not e:
            return None
        rels, t = db.get_relationships(
            entity_id, limit=limit, offset=offset,
            rel_type=type, include_near=include_near, return_total=True,
        )
        return {"entity_id": entity_id, "total": t, "limit": limit,
                "offset": offset, "relationships": rels}
    result = await asyncio.to_thread(_query)
    if not result:
        return JSONResponse(status_code=404, content={"error": "not_found"})
    return result


@router.get("/entity-types")
async def entity_types():
    def _query():
        all_ents = db.list_entities(limit=10000, offset=0, public_only=True)
        counts: dict[str, int] = {}
        for e in all_ents:
            t = e.get("type", "unknown")
            counts[t] = counts.get(t, 0) + 1
        return sorted([{"type": k, "count": v} for k, v in counts.items()], key=lambda x: -x["count"])
    result = await asyncio.to_thread(_query)
    return {"types": result, "total": sum(t["count"] for t in result)}


@router.get("/areas")
async def list_areas():
    def _query():
        places = db.list_entities(entity_type="place", limit=1000, offset=0, public_only=True)
        areas: dict[str, list] = {}
        for p in places:
            area = p.get("area", "")
            if area not in areas:
                areas[area] = []
            areas[area].append({"id": p["id"], "name": p["name"]})
        return [{"area": k, "places": v, "count": len(v)} for k, v in sorted(areas.items())]
    result = await asyncio.to_thread(_query)
    return {"areas": result, "total_places": sum(a["count"] for a in result)}


@router.get("/entities/{entity_id}")
async def get_entity(
    entity_id: str,
    response: Response,
    relationship_limit: int = Query(DEFAULT_RELATIONSHIP_LIMIT, ge=0, le=100),
):
    validate_path_id(entity_id, "entity_id")
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=120"
    cache_key = f"{entity_id}:{relationship_limit}"
    now = _time.time()
    cached = _entity_cache.get(cache_key)
    if cached and now - cached[0] < _ENTITY_TTL:
        _entity_cache.move_to_end(cache_key)
        return cached[1]

    def _query():
        e = db.get_entity(entity_id)
        if not e:
            return None
        rels, rel_total = db.get_relationships(entity_id, limit=relationship_limit, return_total=True)
        e["relationship_total"] = rel_total
        e["relationships"] = rels
        _enrich_entity_place(e)
        e["quality"] = entity_quality(e)
        e["source_freshness"] = _build_source_freshness(e)
        e["practical_facts"] = _build_practical_facts(e)
        return e
    entity = await asyncio.to_thread(_query)
    if not entity:
        return JSONResponse(status_code=404, content={"error": "not_found"})

    _entity_cache[cache_key] = (now, entity)
    while len(_entity_cache) > _ENTITY_CACHE_MAX:
        _entity_cache.popitem(last=False)

    return entity


@router.get("/entities/{entity_id}/stats")
async def get_entity_stats(entity_id: str, response: Response):
    validate_path_id(entity_id, "entity_id")
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=120"
    ph = db._ph
    def _query():
        e = db.get_entity(entity_id)
        if not e:
            return None
        with db._conn() as conn:
            review_row = db._fetchone(conn, f"""
                SELECT COUNT(*) as review_count,
                       COALESCE(AVG(rating), 0) as avg_rating
                FROM posts
                WHERE entity_id = {ph} AND post_type = 'review'
                  AND moderation_status = 'approved' AND rating IS NOT NULL
            """, (entity_id,))
            post_row = db._fetchone(conn, f"""
                SELECT COUNT(*) as post_count FROM posts
                WHERE entity_id = {ph} AND moderation_status = 'approved'
            """, (entity_id,))
            bookmark_row = db._fetchone(conn, f"""
                SELECT COUNT(*) as bookmark_count FROM saved_entities
                WHERE entity_id = {ph}
            """, (entity_id,))
            follow_row = db._fetchone(conn, f"""
                SELECT COUNT(*) as follower_count FROM follows
                WHERE target_id = {ph} AND target_type = 'entity'
            """, (entity_id,))
        rd = db._row_to_dict(review_row) if review_row else {}
        pd = db._row_to_dict(post_row) if post_row else {}
        bd = db._row_to_dict(bookmark_row) if bookmark_row else {}
        fd = db._row_to_dict(follow_row) if follow_row else {}
        return {
            "entity_id": entity_id,
            "review_count": rd.get("review_count", 0),
            "avg_rating": round(float(rd.get("avg_rating", 0)), 1),
            "post_count": pd.get("post_count", 0),
            "bookmark_count": bd.get("bookmark_count", 0),
            "follower_count": fd.get("follower_count", 0),
        }
    result = await asyncio.to_thread(_query)
    if not result:
        return JSONResponse(status_code=404, content={"error": "not_found"})
    return result


@router.get("/entities/{entity_id}/reviews")
async def get_entity_reviews(
    entity_id: str,
    response: Response,
    page: int = Query(1, ge=1, le=1000),
    limit: int = Query(20, ge=1, le=50),
    sort: str = Query("newest", max_length=20),
    min_rating: int = Query(None, ge=1, le=5),
):
    validate_path_id(entity_id, "entity_id")
    response.headers["Cache-Control"] = "public, max-age=30, stale-while-revalidate=60"
    ph = db._ph
    offset = (page - 1) * limit
    _REVIEW_SORT = {"newest": "p.created_at DESC", "helpful": "p.like_count DESC, p.created_at DESC",
                     "highest": "p.rating DESC, p.created_at DESC", "lowest": "p.rating ASC, p.created_at DESC"}
    order = _REVIEW_SORT.get(sort, "p.created_at DESC")
    def _query():
        conditions = [f"p.entity_id = {ph}", "p.post_type = 'review'", "p.moderation_status = 'approved'"]
        params = [entity_id]
        if min_rating is not None:
            conditions.append(f"p.rating >= {ph}")
            params.append(min_rating)
        where = " AND ".join(conditions)
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT p.id, p.user_id, p.content, p.rating, p.images, p.like_count,
                       p.comment_count, p.created_at, u.display_name, u.avatar_url, u.username
                FROM posts p JOIN users u ON u.id = p.user_id
                WHERE {where}
                ORDER BY {order}
                LIMIT {ph} OFFSET {ph}
            """, (*params, limit, offset))
            total_row = db._fetchone(conn, f"""
                SELECT COUNT(*) as c, COALESCE(AVG(p.rating), 0) as avg_rating
                FROM posts p WHERE {where}
            """, tuple(params))
            dist_rows = db._fetchall(conn, f"""
                SELECT p.rating, COUNT(*) as cnt FROM posts p
                WHERE p.entity_id = {ph} AND p.post_type = 'review'
                  AND p.moderation_status = 'approved' AND p.rating IS NOT NULL
                GROUP BY p.rating ORDER BY p.rating DESC
            """, (entity_id,))
        return rows, total_row, dist_rows
    rows, total_row, dist_rows = await asyncio.to_thread(_query)
    td = db._row_to_dict(total_row) if total_row else {}
    total = td.get("c", 0)
    distribution = {str(db._row_to_dict(r)["rating"]): db._row_to_dict(r)["cnt"] for r in dist_rows}
    reviews = []
    for r in rows:
        rd = db._row_to_dict(r)
        images = rd.get("images", [])
        if isinstance(images, str):
            try:
                images = json.loads(images)
            except (json.JSONDecodeError, ValueError, TypeError):
                images = []
        reviews.append({
            "id": str(rd["id"]),
            "content": rd["content"],
            "rating": rd.get("rating"),
            "images": images,
            "like_count": rd.get("like_count", 0),
            "comment_count": rd.get("comment_count", 0),
            "created_at": str(rd.get("created_at", "")),
            "author": {
                "id": str(rd.get("user_id", "")),
                "display_name": rd.get("display_name", ""),
                "username": rd.get("username"),
                "avatar_url": rd.get("avatar_url"),
            },
        })
    return {
        "reviews": reviews,
        "total": total,
        "avg_rating": round(float(td.get("avg_rating", 0)), 1),
        "distribution": distribution,
        "page": page,
        "has_more": offset + limit < total,
    }


@router.get("/places")
async def list_places(response: Response, area: Optional[str] = Query(None, max_length=100)):
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
                    "SELECT id, name, area, level FROM entities WHERE type = 'place' ORDER BY name LIMIT 500")
        return [db._row_to_dict(r) for r in rows]
    return await asyncio.to_thread(_query)


@router.get("/facilities")
async def list_facilities(place: Optional[str] = Query(None, max_length=100)):
    """GĐ13.4: danh bạ hành chính — cơ quan công vụ (UBND/công an/...) theo xã/phường."""
    facilities = await asyncio.to_thread(db.facilities_by_place, place)
    return {"facilities": facilities}


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
    validate_path_id(place_id, "place_id")
    def _query():
        p = db.get_entity(place_id)
        if not p or p.get("type") != "place":
            return None
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
            "place": {"id": p["id"], "name": p.get("name"), "area": p.get("area"),
                      "level": p.get("level"), "summary": p.get("summary"),
                      "attributes": p.get("attributes", {}),
                      "coordinates": p.get("coordinates")},
            "facilities": db.facilities_by_place(place_id),
            "counts": {g: len(v) for g, v in groups.items()},
            "tourism": groups["tourism"],
            "lodging": groups["lodging"],
            "products": groups["products"],
            "other": groups["other"],
        }
    result = await asyncio.to_thread(_query)
    if not result:
        return JSONResponse(status_code=404, content={"error": "not_found", "detail": "Không phải xã/phường"})
    return result


_DAY_PLAN_TYPE_PRIORITY = [
    "attraction", "nature", "history", "experience", "craft_village",
    "dish", "drink", "product", "market", "accommodation", "event",
]
_DAY_PLAN_SLOTS = [
    {"label": "sáng", "start": "08:00", "duration_min": 60},
    {"label": "sáng", "start": "09:30", "duration_min": 45},
    {"label": "trưa", "start": "11:00", "duration_min": 60},
    {"label": "chiều", "start": "13:30", "duration_min": 60},
    {"label": "chiều", "start": "15:00", "duration_min": 45},
    {"label": "chiều", "start": "16:30", "duration_min": 45},
]


def _haversine_km(a: list | None, b: list | None) -> float:
    if not a or not b:
        return 999.0
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(h))


@router.get("/places/{place_id}/day-plan")
async def place_day_plan(place_id: str):
    """Gợi ý lịch trình 1 ngày cho xã/phường — đa dạng loại hình, sắp theo khoảng cách."""
    validate_path_id(place_id, "place_id")

    def _query():
        p = db.get_entity(place_id)
        if not p or p.get("type") != "place":
            return None
        ents = db.entities_by_place(place_id)
        center = p.get("coordinates")
        seen_types: set = set()
        candidates = []
        for e in sorted(ents, key=lambda x: _haversine_km(center, x.get("coordinates"))):
            t = e.get("type")
            if t in seen_types or t == "place":
                continue
            seen_types.add(t)
            candidates.append(e)
            if len(candidates) >= len(_DAY_PLAN_SLOTS):
                break
        if not candidates and ents:
            candidates = ents[:len(_DAY_PLAN_SLOTS)]
        stops = []
        for i, e in enumerate(candidates):
            slot = _DAY_PLAN_SLOTS[i] if i < len(_DAY_PLAN_SLOTS) else _DAY_PLAN_SLOTS[-1]
            stops.append({
                "entity_id": e["id"],
                "name": e.get("name"),
                "type": e.get("type"),
                "suggested_time": slot["start"],
                "time_of_day": slot["label"],
                "visit_duration_min": slot["duration_min"],
                "coordinates": e.get("coordinates"),
            })
        total_min = sum(s["visit_duration_min"] for s in stops)
        return {
            "place": {"id": p["id"], "name": p.get("name"), "area": p.get("area")},
            "stops": stops,
            "total_stops": len(stops),
            "total_duration_min": total_min,
        }

    result = await asyncio.to_thread(_query)
    if not result:
        return JSONResponse(status_code=404, content={"error": "not_found", "detail": "Không phải xã/phường"})
    return result


@router.get("/itineraries")
async def list_itineraries(
    area: Optional[str] = Query(None, max_length=100),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0, le=10000),
):
    return await asyncio.to_thread(db.list_itineraries, area=area, limit=limit, offset=offset)


@router.get("/itineraries/{itin_id}")
async def get_itinerary(itin_id: str):
    validate_path_id(itin_id, "itin_id")
    def _query():
        it = db.get_itinerary(itin_id)
        if not it:
            return None
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
    result = await asyncio.to_thread(_query)
    if not result:
        return JSONResponse(status_code=404, content={"error": "not_found"})
    return result


@router.get("/search")
async def search(
    request: Request,
    q: str = Query(..., min_length=1, max_length=200),
    type: Optional[str] = Query(None, max_length=50),
    area: Optional[str] = Query(None, max_length=100),
    limit: int = Query(20, ge=1, le=100),
):
    from ratelimit import check_rate
    check_rate(f"search:{get_client_ip(request)}", 30, 60, "Tìm kiếm quá nhanh. Vui lòng thử lại sau.")
    results = await asyncio.to_thread(db.search_entities, q=q, entity_type=type, area=area, limit=limit)
    _enrich_place(results)
    total = await asyncio.to_thread(db.count_entities_filtered, entity_type=type, area=area, q=q)
    safe_q = re.sub(r"<[^>]+>", "", q)
    _log_search_query(safe_q, type, area, total)
    return {"q": safe_q, "total": total, "results": results}


@router.get("/autocomplete")
async def autocomplete(
    request: Request,
    response: Response,
    q: str = Query(..., min_length=1, max_length=100),
    type: Optional[str] = Query(None, max_length=50),
    limit: int = Query(8, ge=1, le=20),
):
    """Lightweight typeahead for entity name search."""
    from ratelimit import check_rate
    check_rate(f"autocomplete:{get_client_ip(request)}", 60, 60, "Quá nhiều yêu cầu. Vui lòng thử lại sau.")
    response.headers["Cache-Control"] = "public, max-age=30, stale-while-revalidate=60"
    results = await asyncio.to_thread(db.search_entities, q=q, entity_type=type, limit=limit)
    return {
        "suggestions": [
            {"id": e["id"], "name": e["name"], "type": e.get("type", ""),
             "place": e.get("place", "")}
            for e in results
        ],
    }


@router.get("/me/activity")
async def user_activity(
    request: Request,
    page: int = Query(1, ge=1, le=1000),
    limit: int = Query(20, ge=1, le=50),
    user=Depends(require_user),
):
    from ratelimit import check_rate
    check_rate(f"activity:{user['id']}", 20, 60, "Quá nhiều yêu cầu. Vui lòng thử lại sau.")
    ph = db._ph
    offset = (page - 1) * limit
    uid = str(user["id"])
    def _query():
        with db._conn() as conn:
            posts = db._fetchall(conn, f"""
                SELECT id, content, post_type, entity_id, created_at, like_count, comment_count
                FROM posts WHERE user_id = {ph}::uuid AND moderation_status != 'rejected'
                ORDER BY created_at DESC LIMIT {ph} OFFSET {ph}
            """, (uid, limit, offset))
            comments = db._fetchall(conn, f"""
                SELECT c.id, c.content, c.post_id, c.created_at, p.entity_id
                FROM comments c JOIN posts p ON p.id = c.post_id
                WHERE c.user_id = {ph}::uuid
                ORDER BY c.created_at DESC LIMIT {ph} OFFSET {ph}
            """, (uid, limit, offset))
            likes = db._fetchall(conn, f"""
                SELECT l.post_id, l.created_at, p.content, p.entity_id
                FROM likes l JOIN posts p ON p.id = l.post_id
                WHERE l.user_id = {ph}::uuid
                ORDER BY l.created_at DESC LIMIT {ph} OFFSET {ph}
            """, (uid, limit, offset))
        return (
            [db._row_to_dict(r) for r in posts],
            [db._row_to_dict(r) for r in comments],
            [db._row_to_dict(r) for r in likes],
        )
    posts, comments, likes = await asyncio.to_thread(_query)
    for p in posts:
        p["id"] = str(p["id"])
        p["type"] = "post"
    for c in comments:
        c["id"] = str(c["id"])
        c["post_id"] = str(c["post_id"])
        c["type"] = "comment"
    for lk in likes:
        lk["post_id"] = str(lk["post_id"])
        lk["type"] = "like"
    items = sorted(posts + comments + likes, key=lambda x: str(x.get("created_at", "")), reverse=True)[:limit]
    return {"activity": items, "page": page, "has_more": len(items) == limit}


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
        return datetime.strptime(date_end, "%Y-%m-%d").date() < datetime.now(timezone.utc).date()
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
    month = datetime.now(timezone.utc).month

    global _homepage_rebuilding
    _now = _time.time()
    cache_fresh = (_homepage_cache["data"] is not None and _homepage_cache["month"] == month
                   and _now - _homepage_cache["ts"] < _HOMEPAGE_TTL)
    if cache_fresh:
        return _homepage_cache["data"]
    if _homepage_lock.locked() and _homepage_cache["data"] is not None:
        return _homepage_cache["data"]
    async with _homepage_lock:
        cache_fresh = (_homepage_cache["data"] is not None and _homepage_cache["month"] == month
                       and _time.time() - _homepage_cache["ts"] < _HOMEPAGE_TTL)
        if cache_fresh:
            return _homepage_cache["data"]
        _homepage_rebuilding = True

    all_ents = await asyncio.to_thread(db.list_entities, limit=5000, offset=0, public_only=True)
    public = [e for e in all_ents if not _event_is_past(e)]
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
    today = datetime.now(timezone.utc).date()
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
    all_itineraries = await asyncio.to_thread(db.list_itineraries)
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

    stats = await asyncio.to_thread(db.stats)

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
        logger.warning("Failed to load seasonal taglines override", exc_info=True)
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
    _homepage_cache.update(month=month, data=result, ts=_time.time())
    _homepage_rebuilding = False
    return result


# ── Map pins (lightweight endpoint for MapListView) ──────────────────

_TYPE_META = {
    "attraction": {"emoji": "\U0001f3de️", "color": "#2E86AB"},
    "nature": {"emoji": "\U0001f333", "color": "#4CAF50"},
    "experience": {"emoji": "\U0001f3ad", "color": "#FF6B35"},
    "dish": {"emoji": "\U0001f35c", "color": "#D94F3D"},
    "drink": {"emoji": "\U0001f964", "color": "#E57373"},
    "product": {"emoji": "\U0001f381", "color": "#FF9800"},
    "craft_village": {"emoji": "\U0001f3e1", "color": "#8D6E63"},
    "accommodation": {"emoji": "\U0001f3e8", "color": "#7E57C2"},
    "event": {"emoji": "\U0001f389", "color": "#EC407A"},
    "history": {"emoji": "\U0001f3db️", "color": "#795548"},
    "person": {"emoji": "\U0001f9d1", "color": "#607D8B"},
    "economy": {"emoji": "\U0001f4b0", "color": "#43A047"},
    "organization": {"emoji": "\U0001f3e2", "color": "#546E7A"},
    "facility": {"emoji": "\U0001f3e5", "color": "#1976D2"},
}

_map_pins_cache: dict = {"data": None, "filters": None, "ts": 0.0}
_MAP_PINS_TTL = 120


@router.get("/map-pins")
async def get_map_pins(
    response: Response,
    type: Optional[str] = Query(None, max_length=50),
    area: Optional[str] = Query(None, max_length=50),
):
    response.headers["Cache-Control"] = "public, max-age=120, stale-while-revalidate=300"
    cache_key = f"{type}:{area}"
    _now = _time.time()
    if (_map_pins_cache["data"] is not None
            and _map_pins_cache["filters"] == cache_key
            and _now - _map_pins_cache["ts"] < _MAP_PINS_TTL):
        return _map_pins_cache["data"]

    type_filters: list[str] | None = None
    if type:
        type_filters = [t.strip() for t in type.split(",") if t.strip()]

    def _query():
        all_ents = db.list_entities(limit=5000, offset=0, area=area, public_only=True, entity_types=type_filters)
        pins = []
        for e in all_ents:
            coords = e.get("coordinates")
            if not coords or not isinstance(coords, (list, tuple)) or len(coords) < 2:
                continue
            try:
                lat, lng = float(coords[0]), float(coords[1])
            except (TypeError, ValueError, IndexError):
                continue
            etype = e.get("type", "")
            meta = _TYPE_META.get(etype, {"emoji": "\U0001f4cd", "color": "#9E9E9E"})
            attrs = e.get("attributes") or {}
            pin = {
                "id": e["id"],
                "name": e["name"],
                "type": etype,
                "lat": lat,
                "lng": lng,
                "emoji": meta["emoji"],
                "category_color": meta["color"],
                "rating": attrs.get("rating"),
                "review_count": attrs.get("review_count", 0),
            }
            pid = e.get("placeId")
            if pid:
                p = _get_place(pid)
                if p:
                    pin["place_name"] = p["name"]
            pins.append(pin)
        return pins

    result = await asyncio.to_thread(_query)
    _map_pins_cache.update(data=result, filters=cache_key, ts=_now)
    return result


@router.get("/events")
async def list_events(
    response: Response,
    area: Optional[str] = Query(None, max_length=100),
    include_past: bool = False,
    limit: int = Query(50, ge=1, le=200),
):
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=600"
    """Sự kiện: sắp xếp theo date_start, mặc định ẩn sự kiện đã qua."""
    today = datetime.now(timezone.utc).date()
    all_ents = await asyncio.to_thread(db.list_entities, entity_type="event", limit=2000, offset=0, public_only=True)
    events = list(all_ents)
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


_REPORT_FIELD_OPTIONS = {"phone", "hours", "address", "source", "name", "price", "images", "other"}


class ReportIn(BaseModel):
    target_id: str = Field(..., min_length=1, max_length=200)
    target_type: str = Field("entity", max_length=20)
    reason: str = Field(..., min_length=1, max_length=60)
    detail: str = Field("", max_length=2000)
    contact: str = Field("", max_length=120)
    field: Optional[str] = Field(None, max_length=20)


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
    report_field = payload.field if payload.field and payload.field in _REPORT_FIELD_OPTIONS else None
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "target_id": payload.target_id.strip(),
        "target_type": target_type,
        "reason": payload.reason.strip(),
        "detail": payload.detail.strip(),
        "contact": payload.contact.strip(),
        "field": report_field,
        "ip_hash": hashlib.sha256(ip.encode()).hexdigest()[:16],
        "status": "open",
    }
    def _write():
        with _jsonl_lock:
            REPORTS_FILE.parent.mkdir(exist_ok=True)
            with open(REPORTS_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            _maybe_rotate_jsonl(REPORTS_FILE)
    try:
        await asyncio.to_thread(_write)
    except OSError:
        logger.exception("Failed to write report to %s", REPORTS_FILE)
        return JSONResponse(status_code=500, content={"error": "store_failed"})
    return {"ok": True, "message": "Đã ghi nhận. Cảm ơn bạn đã góp ý — chúng tôi sẽ kiểm tra."}


# ── Report stale field (U-02: field-level freshness reports) ─────────

_STALE_FIELDS = {"phone", "hours", "address", "source", "name", "price", "images", "other"}


class ReportStaleIn(BaseModel):
    field: str = Field(..., min_length=1, max_length=20)
    detail: str = Field("", max_length=2000)


@router.post("/entities/{entity_id}/report-stale")
async def report_stale_field(entity_id: str, payload: ReportStaleIn, request: Request):
    """U-02: Report a specific field as stale/incorrect on an entity."""
    validate_path_id(entity_id, "entity_id")
    if payload.field not in _STALE_FIELDS:
        return JSONResponse(status_code=422, content={
            "error": "invalid_field",
            "valid_fields": sorted(_STALE_FIELDS),
        })
    ip = get_client_ip(request)
    allowed, info = report_limiter.is_allowed(ip)
    if not allowed:
        return JSONResponse(
            status_code=429,
            content={"error": "rate_limited", "retry_after": info.get("retry_after", 60)},
        )
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "target_id": entity_id,
        "target_type": "stale_field",
        "field": payload.field,
        "detail": payload.detail.strip(),
        "ip_hash": hashlib.sha256(ip.encode()).hexdigest()[:16],
        "status": "open",
    }
    def _write():
        with _jsonl_lock:
            REPORTS_FILE.parent.mkdir(exist_ok=True)
            with open(REPORTS_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            _maybe_rotate_jsonl(REPORTS_FILE)
    try:
        await asyncio.to_thread(_write)
    except OSError:
        logger.exception("Failed to write stale report")
        return JSONResponse(status_code=500, content={"error": "store_failed"})
    return {"ok": True, "message": "Đã ghi nhận — chúng tôi sẽ kiểm tra và cập nhật."}


# ── Entity gallery (entity images + review images) ───────────────────

@router.get("/entities/{entity_id}/gallery")
async def get_entity_gallery(entity_id: str, response: Response):
    validate_path_id(entity_id, "entity_id")
    response.headers["Cache-Control"] = "public, max-age=120, stale-while-revalidate=300"

    entity = await asyncio.to_thread(db.get_entity, entity_id)
    if not entity:
        return JSONResponse(status_code=404, content={"error": "not_found"})

    images: list[dict] = []
    attrs = entity.get("attributes") or {}
    default_credit = attrs.get("image_credit", "AI-generated")
    for url in (entity.get("images") or []):
        if isinstance(url, str) and url:
            images.append({
                "url": url,
                "alt": f"{entity['name']} — ảnh {len(images) + 1}",
                "credit": default_credit,
                "width": None,
                "height": None,
            })

    if db._use_pg:
        ph = db._ph
        def _review_images():
            with db._conn() as conn:
                rows = db._fetchall(conn, f"""
                    SELECT p.images, u.display_name
                    FROM posts p
                    JOIN users u ON u.id = p.user_id
                    WHERE p.entity_id = {ph} AND p.post_type = 'review'
                        AND p.moderation_status = 'approved'
                        AND p.images IS NOT NULL
                    ORDER BY p.created_at DESC
                    LIMIT 50
                """, (entity_id,))
            return [db._row_to_dict(r) for r in rows]

        try:
            review_rows = await asyncio.to_thread(_review_images)
            for row in review_rows:
                review_imgs = row.get("images") or []
                if isinstance(review_imgs, str):
                    try:
                        review_imgs = json.loads(review_imgs)
                    except (json.JSONDecodeError, ValueError):
                        continue
                credit = row.get("display_name", "Người dùng")
                for url in review_imgs:
                    if isinstance(url, str) and url:
                        images.append({
                            "url": url,
                            "alt": f"{entity['name']} — ảnh đánh giá",
                            "credit": credit,
                            "width": None,
                            "height": None,
                        })
        except Exception:
            logger.exception("gallery review-images query failed for %s", entity_id)

    return {"images": images, "total": len(images)}


# ── Review stats (rating distribution + mention extraction) ──────────

_REVIEW_STATS_CACHE: dict[str, tuple[float, dict]] = {}
_REVIEW_STATS_TTL = 300

_VN_STOPWORDS = frozenset(
    "và của là này đó có không được cho với từ tại ở về để bị do theo "
    "đã sẽ đang rất rồi nhưng hay hoặc nếu thì mà cũng các những một nhiều "
    "khi nên ra vào lên xuống đi lại còn quá nào ai gì sao thế nữa đây".split()
)
_PUNCT_RE = re.compile(r"[.,!?;:\"'()\[\]{}<>/\\@#$%^&*+=~`|…–—]")


def _extract_mentions(texts: list[str], top_n: int = 8) -> list[dict]:
    unigrams: Counter = Counter()
    bigrams: Counter = Counter()
    for text in texts:
        clean = _PUNCT_RE.sub(" ", text.lower())
        words = [w for w in clean.split() if w and w not in _VN_STOPWORDS and len(w) > 1]
        unigrams.update(words)
        for i in range(len(words) - 1):
            bigrams[f"{words[i]} {words[i+1]}"] += 1
    combined: Counter = Counter()
    for w, c in unigrams.items():
        if c >= 2:
            combined[w] = c
    for bg, c in bigrams.items():
        if c >= 2:
            combined[bg] = c
    return [{"keyword": kw, "count": cnt} for kw, cnt in combined.most_common(top_n)]


@router.get("/entities/{entity_id}/review-stats")
async def get_review_stats(entity_id: str, response: Response):
    validate_path_id(entity_id, "entity_id")
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=600"

    now = _time.time()
    cached = _REVIEW_STATS_CACHE.get(entity_id)
    if cached and now - cached[0] < _REVIEW_STATS_TTL:
        return cached[1]

    _empty = {"avg": 0, "count": 0, "distribution": {}, "mentions": []}

    entity = await asyncio.to_thread(db.get_entity, entity_id)
    if not entity:
        return JSONResponse(status_code=404, content={"error": "not_found"})

    if not db._use_pg:
        return _empty

    ph = db._ph

    def _query():
        with db._conn() as conn:
            dist_rows = db._fetchall(conn, f"""
                SELECT rating, COUNT(*) as cnt
                FROM posts
                WHERE entity_id = {ph} AND post_type = 'review'
                    AND moderation_status = 'approved' AND rating IS NOT NULL
                GROUP BY rating
            """, (entity_id,))
            content_rows = db._fetchall(conn, f"""
                SELECT content FROM posts
                WHERE entity_id = {ph} AND post_type = 'review'
                    AND moderation_status = 'approved' AND content IS NOT NULL
                    AND content != ''
                ORDER BY created_at DESC LIMIT 200
            """, (entity_id,))
        return dist_rows, content_rows

    try:
        dist_rows, content_rows = await asyncio.to_thread(_query)
    except Exception:
        logger.exception("review-stats query failed for %s", entity_id)
        return _empty

    distribution = {}
    total = 0
    weighted_sum = 0
    for row in dist_rows:
        r = db._row_to_dict(row)
        rating = int(r["rating"])
        cnt = int(r["cnt"])
        distribution[str(rating)] = cnt
        total += cnt
        weighted_sum += rating * cnt

    avg = round(weighted_sum / total, 1) if total > 0 else 0

    texts = [db._row_to_dict(r)["content"] for r in content_rows]
    mentions = _extract_mentions(texts)

    result = {"avg": avg, "count": total, "distribution": distribution, "mentions": mentions}
    _REVIEW_STATS_CACHE[entity_id] = (now, result)
    return result


# ── Similar entity recommendations (U-29: rule-based) ────────────────

_similar_cache: OrderedDict[str, tuple[float, list]] = OrderedDict()
_SIMILAR_TTL = 300  # 5 min cache


@router.get("/entities/{entity_id}/similar")
async def get_similar_entities(
    entity_id: str,
    response: Response,
    limit: int = Query(6, ge=1, le=20),
):
    """U-29: Rule-based similar entity recommendations (no ML)."""
    validate_path_id(entity_id, "entity_id")
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=600"

    now = _time.time()
    cache_key = f"{entity_id}:{limit}"
    cached = _similar_cache.get(cache_key)
    if cached and now - cached[0] < _SIMILAR_TTL:
        _similar_cache.move_to_end(cache_key)
        return {"entity_id": entity_id, "similar": cached[1]}

    def _compute():
        try:
            import knowledge
            knowledge._ensure()
            entities_map = knowledge._entities
            rels = knowledge._relationships if hasattr(knowledge, "_relationships") else []
        except Exception:
            return None
        if entity_id not in entities_map:
            return None
        from recommender import recommend_by_entity
        return recommend_by_entity(entity_id, entities_map, rels, limit=limit)

    result = await asyncio.to_thread(_compute)
    if result is None:
        entity = await asyncio.to_thread(db.get_entity, entity_id)
        if not entity:
            return JSONResponse(status_code=404, content={"error": "not_found"})
        return {"entity_id": entity_id, "similar": []}

    _similar_cache[cache_key] = (now, result)
    while len(_similar_cache) > 200:
        _similar_cache.popitem(last=False)

    return {"entity_id": entity_id, "similar": result}


@router.get("/entities/{entity_id}/nearby")
async def get_nearby_entities(
    entity_id: str,
    limit: int = Query(10, ge=1, le=30),
    radius_km: float = Query(10.0, ge=0.5, le=50.0),
    type: str = Query(None, max_length=50),
):
    validate_path_id(entity_id, "entity_id")
    entity = await asyncio.to_thread(db.get_entity, entity_id)
    if not entity:
        raise HTTPException(404, "Entity không tồn tại")
    center = entity.get("coordinates")
    if not center or not isinstance(center, (list, tuple)) or len(center) < 2:
        return {"entity_id": entity_id, "nearby": [], "message": "Entity không có tọa độ"}
    def _query():
        type_filters = [type] if type else None
        all_ents = db.list_entities(limit=3000, offset=0, public_only=True, entity_types=type_filters)
        nearby = []
        for e in all_ents:
            if e["id"] == entity_id:
                continue
            dist = _haversine_km(center, e.get("coordinates"))
            if dist <= radius_km:
                nearby.append({
                    "id": e["id"],
                    "name": e["name"],
                    "type": e.get("type"),
                    "distance_km": round(dist, 2),
                    "coordinates": e.get("coordinates"),
                })
        nearby.sort(key=lambda x: x["distance_km"])
        return nearby[:limit]
    result = await asyncio.to_thread(_query)
    return {"entity_id": entity_id, "nearby": result, "radius_km": radius_km}


# ── Entity Q&A (U-09: questions with best answer resolution) ─────────

from fastapi import Depends

@router.get("/entities/{entity_id}/qa", dependencies=[Depends(require_pg)])
async def get_entity_qa(
    entity_id: str,
    response: Response,
    page: int = Query(1, ge=1, le=100),
    limit: int = Query(10, ge=1, le=50),
):
    """U-09: Surface Q&A posts for an entity with accepted answer resolution."""
    validate_path_id(entity_id, "entity_id")
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=120"

    entity = await asyncio.to_thread(db.get_entity, entity_id)
    if not entity:
        return JSONResponse(status_code=404, content={"error": "not_found"})

    ph = db._ph
    offset = (page - 1) * limit

    def _qa_query():
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT p.id, p.content, p.created_at, p.user_id, p.best_answer_id,
                       p.comment_count, p.like_count,
                       u.display_name, u.avatar_url, u.username
                FROM posts p
                JOIN users u ON u.id = p.user_id
                WHERE p.entity_id = {ph}
                  AND p.post_type = 'question'
                  AND p.moderation_status = 'approved'
                ORDER BY (CASE WHEN p.best_answer_id IS NOT NULL THEN 0 ELSE 1 END),
                         p.like_count DESC, p.created_at DESC
                LIMIT {ph} OFFSET {ph}
            """, (entity_id, limit, offset))

            total_row = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM posts
                WHERE entity_id = {ph} AND post_type = 'question'
                  AND moderation_status = 'approved'
            """, (entity_id,))

            questions = []
            for r in rows:
                d = db._row_to_dict(r)
                q = {
                    "id": d["id"],
                    "content": d["content"],
                    "created_at": d["created_at"],
                    "user": {
                        "id": d["user_id"],
                        "display_name": d.get("display_name"),
                        "avatar_url": d.get("avatar_url"),
                        "username": d.get("username"),
                    },
                    "comment_count": d.get("comment_count", 0),
                    "like_count": d.get("like_count", 0),
                    "best_answer_id": d.get("best_answer_id"),
                    "best_answer": None,
                }
                if d.get("best_answer_id"):
                    answer = db._fetchone(conn, f"""
                        SELECT c.id, c.content, c.created_at, c.user_id,
                               u2.display_name, u2.avatar_url, u2.username
                        FROM comments c
                        JOIN users u2 ON u2.id = c.user_id
                        WHERE c.id = {ph}
                    """, (d["best_answer_id"],))
                    if answer:
                        a = db._row_to_dict(answer)
                        q["best_answer"] = {
                            "id": a["id"],
                            "content": a["content"],
                            "created_at": a["created_at"],
                            "user": {
                                "id": a["user_id"],
                                "display_name": a.get("display_name"),
                                "avatar_url": a.get("avatar_url"),
                                "username": a.get("username"),
                            },
                        }
                questions.append(q)
            return questions, db._row_to_dict(total_row) if total_row else {}

    questions, total_d = await asyncio.to_thread(_qa_query)
    total = total_d.get("c", 0)
    return {
        "entity_id": entity_id,
        "questions": questions,
        "total": total,
        "has_more": (page * limit) < total,
    }


# ── Contact view tracking (CTA analytics) ───────────────────────────

CONTACT_VIEWS_FILE = Path(__file__).resolve().parent / "data" / "contact_views.jsonl"
_VALID_CONTACT_ACTIONS = {"zalo", "phone", "website", "map"}


@router.post("/entities/{entity_id}/view-contact")
async def track_contact_view(
    entity_id: str,
    request: Request,
    action: str = Query(..., pattern="^(zalo|phone|website|map)$"),
):
    validate_path_id(entity_id, "entity_id")
    ip = get_client_ip(request)
    from ratelimit import check_rate
    check_rate(f"contact-view:{ip}", 10, 60,
               "Quá nhiều yêu cầu. Vui lòng thử lại sau.")

    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "entity_id": entity_id,
        "action": action,
        "ip_hash": hashlib.sha256(ip.encode()).hexdigest()[:16],
    }

    def _write():
        with _jsonl_lock:
            CONTACT_VIEWS_FILE.parent.mkdir(exist_ok=True)
            with open(CONTACT_VIEWS_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            _maybe_rotate_jsonl(CONTACT_VIEWS_FILE)

    try:
        await asyncio.to_thread(_write)
    except OSError:
        logger.exception("Failed to write contact view log")
        return JSONResponse(status_code=500, content={"error": "store_failed"})
    return {"ok": True}


# ── Entity claims (U-30) ────────────────────────────────────────────

class EntityClaimIn(BaseModel):
    business_name: str = Field(..., min_length=2, max_length=200)
    contact_phone: str = Field(..., min_length=10, max_length=15)
    contact_email: str = Field("", max_length=200)
    evidence: str = Field("", max_length=2000)


@router.post("/entities/{entity_id}/claim", dependencies=[Depends(require_pg)])
async def submit_entity_claim(entity_id: str, payload: EntityClaimIn, request: Request, user=Depends(require_user), _csrf=Depends(require_csrf)):
    validate_path_id(entity_id, "entity_id")
    from ratelimit import check_rate
    check_rate(f"claim:{user['id']}", 3, 86400, "Chỉ được gửi 3 yêu cầu xác nhận/ngày.")
    uid = str(user["id"])
    entity = await asyncio.to_thread(db.get_entity, entity_id)
    if not entity:
        raise HTTPException(404, "Entity không tồn tại")
    ph = db._ph
    def _query():
        with db._conn() as conn:
            existing = db._fetchone(conn, f"""
                SELECT id, status FROM entity_claims
                WHERE entity_id = {ph} AND claimant_id::text = {ph}
            """, (entity_id, uid))
            if existing:
                st = db._row_to_dict(existing)["status"]
                if st == "pending":
                    raise HTTPException(409, "Bạn đã gửi yêu cầu xác nhận cho entity này")
                if st == "approved":
                    raise HTTPException(409, "Entity này đã được xác nhận cho bạn")
            import html as _html
            db._execute(conn, f"""
                INSERT INTO entity_claims (entity_id, claimant_id, business_name, contact_phone, contact_email, evidence)
                VALUES ({ph}, {ph}::uuid, {ph}, {ph}, {ph}, {ph})
            """, (entity_id, uid, _html.escape(payload.business_name.strip()),
                  payload.contact_phone.strip(), payload.contact_email.strip(),
                  _html.escape(payload.evidence.strip()) if payload.evidence else ""))
    await asyncio.to_thread(_query)
    return {"success": True, "message": "Yêu cầu xác nhận đã được gửi. Chúng tôi sẽ xem xét."}


# ── What's-new feed (U-15) ────────────────────────────────────────────


@router.get("/feed/new-since")
async def feed_new_since(
    since: str = Query(..., min_length=10, max_length=30),
    limit: int = Query(50, ge=1, le=100),
):
    """Mới cập nhật/tạo từ `since` — entities + posts (public only)."""
    from database import db as _db
    ph = _db._ph
    try:
        since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return JSONResponse(status_code=400, content={"error": "invalid_date", "detail": "since phải là ISO datetime"})

    def _query():
        import knowledge
        new_entities = []
        entities = knowledge._entities if hasattr(knowledge, "_entities") else {}
        for eid, e in entities.items():
            if e.get("type") == "place":
                continue
            updated = e.get("updatedAt") or e.get("created_at")
            if not updated:
                continue
            try:
                dt = datetime.fromisoformat(str(updated).replace("Z", "+00:00"))
            except (ValueError, TypeError):
                continue
            if dt >= since_dt:
                new_entities.append({
                    "id": eid, "name": e.get("name"), "type": e.get("type"),
                    "area": e.get("area"), "updated_at": str(updated),
                })
        new_entities.sort(key=lambda x: x["updated_at"], reverse=True)
        new_entities = new_entities[:limit]
        new_posts = []
        if _db._use_pg:
            with _db._conn() as conn:
                rows = _db._fetchall(conn, f"""
                    SELECT p.id, p.title, p.post_type, p.entity_id, p.created_at,
                           u.display_name
                    FROM posts p JOIN users u ON u.id = p.user_id
                    WHERE p.moderation_status = 'approved'
                    AND p.created_at >= {ph}
                    ORDER BY p.created_at DESC
                    LIMIT {ph}
                """, (since_dt.isoformat(), limit))
                new_posts = [_db._row_to_dict(r) for r in rows]
        return {
            "entities": new_entities,
            "posts": new_posts,
            "counts": {"entities": len(new_entities), "posts": len(new_posts)},
            "since": since,
        }
    return await asyncio.to_thread(_query)


# ── Collections (U-28, public read-only) ──────────────────────────────


@router.get("/collections")
async def list_public_collections(limit: int = Query(20, ge=1, le=100)):
    """Published collections — sorted by sort_order."""
    ph = db._ph
    def _query():
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT id, slug, title, description, cover_image, entity_ids, sort_order
                FROM collections
                WHERE is_published = TRUE
                ORDER BY sort_order, created_at DESC
                LIMIT {ph}
            """, (limit,))
        return {"collections": [db._row_to_dict(r) for r in rows]}
    return await asyncio.to_thread(_query)


@router.get("/collections/{slug}")
async def get_collection_by_slug(slug: str):
    """Public collection detail by slug — resolve entity_ids to summaries."""
    validate_path_id(slug, "slug")
    ph = db._ph
    def _query():
        with db._conn() as conn:
            row = db._fetchone(conn, f"""
                SELECT * FROM collections WHERE slug = {ph} AND is_published = TRUE
            """, (slug,))
        if not row:
            return None
        col = db._row_to_dict(row)
        entity_ids = col.get("entity_ids") or []
        if isinstance(entity_ids, str):
            entity_ids = json.loads(entity_ids)
        entities = db.get_entities_batch(entity_ids) if entity_ids else []
        col["entities"] = entities
        return col
    result = await asyncio.to_thread(_query)
    if not result:
        return JSONResponse(status_code=404, content={"error": "not_found"})
    return result


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
