"""
vinhlong360 — Public API.

Read-only endpoints for the frontend to consume entities, itineraries,
and search results from the database instead of static data.json.

Mount: app.include_router(public_router)
"""

import json
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from database import db
from data_quality import entity_quality

router = APIRouter(prefix="/api", tags=["public"])

_place_cache: dict[str, dict] = {}
DEFAULT_RELATIONSHIP_LIMIT = 24

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
