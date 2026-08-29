# -*- coding: utf-8 -*-
"""Miền LỊCH TRÌNH — mặt QUẢN TRỊ. Bóc khỏi `admin.py` (2026-08-29, lát 2 đợt
cắt module; hồ sơ đo: journal wf_3f293d24-0a1, kết quả itineraries-routes).

Hoàn tất khuôn hai-mặt cho gói `agent/itineraries/` (như `agent/entities/`,
`agent/community/`): mặt công khai ở `itineraries/api.py`, đây là 5 route CRUD
quản trị (list/get/create/update/delete) + 2 model + 1 helper normalize —
bao đóng bắc cầu, di chuyển NGUYÊN VĂN.

Mount qua `admin.router.include_router(...)` TRƯỚC `_fix_admin_route_order()`:
- cổng R20.9 chỉ nhìn thấy mount qua lời gọi include_router;
- router cha mang prefix "/admin" VÀ dependencies [require_admin, require_csrf]
  — router này KHÔNG tự mang cả hai, kế thừa từ cha khi include (kiểm bằng
  đo runtime trong test ranh giới, không tin trí nhớ API).
"""
from __future__ import annotations

import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from auth_middleware import validate_path_id
from database import db

router = APIRouter(tags=["admin-itineraries"])


# ── Itinerary CRUD ──


@router.get("/itineraries",
            summary="List itineraries",
            description="Returns all itineraries, optionally filtered by area.")
async def list_itineraries_admin(area: Optional[str] = Query(None, max_length=100)):
    return await asyncio.to_thread(db.list_itineraries, area=area)

@router.get("/itineraries/{itin_id}",
            summary="Get itinerary by ID",
            description="Returns the full details of a single itinerary by its ID.")
async def get_itinerary_admin(itin_id: str):
    itin_id = validate_path_id(itin_id, "itin_id")
    def _query():
        it = db.get_itinerary(itin_id)
        if not it:
            raise HTTPException(404, "Lộ trình không tồn tại")
        return it
    return await asyncio.to_thread(_query)

class ItineraryCreate(BaseModel):
    id: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=300)
    summary: str | None = Field(None, max_length=2000)
    description: str | None = Field(None, max_length=2000)
    duration: str | None = Field(None, max_length=100)
    stops: list | None = Field(None, max_length=50)
    days: list | None = Field(None, max_length=30)
    area: str | None = Field(None, max_length=100)
    areas: list[str] | None = Field(None, max_length=10)
    tags: list[str] | None = Field(None, max_length=50)

class ItineraryUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=300)
    summary: str | None = Field(None, max_length=2000)
    description: str | None = Field(None, max_length=2000)
    duration: str | None = Field(None, max_length=100)
    stops: list | None = Field(None, max_length=50)
    days: list | None = Field(None, max_length=30)
    area: str | None = Field(None, max_length=100)
    areas: list[str] | None = Field(None, max_length=10)
    tags: list[str] | None = Field(None, max_length=50)

def _normalize_itinerary_payload(data: dict) -> dict:
    if data.get("description") and not data.get("summary"):
        data["summary"] = data["description"]
    return data


@router.post("/itineraries", status_code=201,
             summary="Create itinerary",
             description="Creates a new itinerary with title, description, days, area, and tags.")
async def create_itinerary(body: ItineraryCreate):
    def _query():
        data = _normalize_itinerary_payload(body.model_dump(exclude_none=True))
        db.upsert_itinerary(data)
    await asyncio.to_thread(_query)
    return {"status": "created", "id": body.id}

@router.put("/itineraries/{itin_id}",
            summary="Update itinerary",
            description="Updates an existing itinerary. Only provided fields are changed.")
async def update_itinerary(itin_id: str, body: ItineraryUpdate):
    itin_id = validate_path_id(itin_id, "itin_id")
    def _query():
        data = _normalize_itinerary_payload(body.model_dump(exclude_none=True))
        existing = db.get_itinerary(itin_id)
        if not existing:
            raise HTTPException(404, "Lộ trình không tồn tại")
        data = {**existing, **data}
        data["id"] = itin_id
        db.upsert_itinerary(data)
    await asyncio.to_thread(_query)
    return {"status": "updated", "id": itin_id}

@router.delete("/itineraries/{itin_id}",
               summary="Delete itinerary",
               description="Permanently deletes an itinerary by its ID. Returns 404 if not found.")
async def delete_itinerary(itin_id: str):
    itin_id = validate_path_id(itin_id, "itin_id")
    def _query():
        db.initialize()
        ph = db._ph
        with db._conn() as conn:
            cur = db._execute(conn, f"DELETE FROM itineraries WHERE id = {ph}", (itin_id,))
            if cur.rowcount == 0:
                raise HTTPException(404, "Lộ trình không tồn tại")
    await asyncio.to_thread(_query)
    return {"success": True, "id": itin_id}
