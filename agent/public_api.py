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
    if q:
        results = db.search_entities(q=q, entity_type=type, area=area, limit=limit)
    else:
        results = db.list_entities(entity_type=type, area=area, limit=limit, offset=offset)

    if month:
        results = [
            e for e in results
            if month in (e.get("season", {}) or {}).get("months", [])
        ]
        total = len(results)
    else:
        total = db.count_entities_filtered(entity_type=type, area=area, q=q)

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
                  "level": place.get("level"), "summary": place.get("summary")},
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
