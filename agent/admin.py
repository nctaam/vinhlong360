"""
vinhlong360 — Admin API.

CRUD endpoints cho quản lý knowledge base:
  - Xem/sửa/xóa entities
  - Review entities auto-learned (pending review)
  - Trigger auto-learn
  - Xem analytics
  - Export/Import data

Mount vào FastAPI app chính qua router.
"""

import asyncio
import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request, Depends, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

import data_quality
import knowledge
import analytics

logger = logging.getLogger("admin")
import site_settings
from database import db

try:
    from cost_tracker import get_cost_report as _get_cost_report
    _HAS_COST = True
except Exception:  # noqa: BLE001
    _HAS_COST = False
from auth_middleware import get_current_user, validate_path_id
from middleware import admin_limiter, verify_admin_key, get_client_ip


def _sync_kb():
    """GĐ3.6: write-through — sau khi ghi DB, nạp lại knowledge để chat/tool thấy ngay.

    Bọc try/except: lỗi reload không được làm hỏng thao tác admin đã commit.
    """
    try:
        knowledge.reload()
    except Exception:
        logger.exception("Knowledge reload failed after admin write — chat may serve stale data")


def _safe(fn, default):
    try:
        return fn()
    except Exception:
        return default

# ── Auth dependency ──

_AUDIT_FILE = Path(__file__).resolve().parent / "data" / "admin_audit.jsonl"


from config import settings as _cfg
_AUDIT_MAX_LINES = _cfg.AUDIT_MAX_LINES


def _log_admin_audit(actor: str, method: str, path: str, ip: str) -> None:
    """P2-7: ghi nhật ký thao tác admin (ai/làm-gì/khi-nào) — JSONL nhẹ, không chặn request."""
    try:
        _AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
        rec = {"ts": datetime.now().isoformat(timespec="seconds"), "actor": actor,
               "method": method, "path": path, "ip": ip}
        with open(_AUDIT_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        _maybe_rotate_audit()
    except Exception:
        logger.exception("Failed to write admin audit log")


def _maybe_rotate_audit() -> None:
    try:
        if not _AUDIT_FILE.exists():
            return
        lines = _AUDIT_FILE.read_text(encoding="utf-8").splitlines()
        if len(lines) <= _AUDIT_MAX_LINES:
            return
        archive = _AUDIT_FILE.with_suffix(f".{datetime.now().strftime('%Y%m%d%H%M%S')}.jsonl")
        archive.write_text("\n".join(lines[:-_AUDIT_MAX_LINES]) + "\n", encoding="utf-8")
        _AUDIT_FILE.write_text("\n".join(lines[-_AUDIT_MAX_LINES:]) + "\n", encoding="utf-8")
    except Exception:
        logger.exception("Audit log rotation failed")


async def require_admin(request: Request):
    """FastAPI dependency: verify admin auth + rate limit (+ audit log mọi mutation)."""
    # Rate limit
    client_ip = get_client_ip(request)
    allowed, rate_info = admin_limiter.is_allowed(client_ip)
    if not allowed:
        raise HTTPException(429, detail="Rate limit exceeded", headers={"Retry-After": str(rate_info["retry_after"])})
    # Auth: allow server-side admin key or a logged-in admin user from the frontend.
    actor = None
    if verify_admin_key(request):
        actor = "admin-key"
    else:
        user = await get_current_user(request)
        if user and user.get("role") == "admin":
            actor = f"user:{user.get('id')}"
    if not actor:
        raise HTTPException(401, detail="Invalid admin credentials. Use X-Admin-Key or an admin session.")
    # P2-7: audit các thao tác THAY ĐỔI (đọc/GET không log để tránh nhiễu)
    if request.method in ("POST", "PUT", "DELETE", "PATCH"):
        _log_admin_audit(actor, request.method, request.url.path, client_ip)

ROOT = Path(__file__).resolve().parent.parent

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


# ── Models ──

import re as _re
import html as _html

def _sanitize(text: str) -> str:
    """Remove dangerous HTML/JS from user input."""
    text = _html.escape(text)
    text = _re.sub(r'<script[^>]*>.*?</script>', '', text, flags=_re.IGNORECASE | _re.DOTALL)
    return text.strip()

VALID_TYPES = {"experience", "product", "dish", "craft_village", "attraction",
               "accommodation", "person", "event", "history", "nature", "economy",
               "facility", "organization"}  # GĐ13: facility=cơ quan công vụ, organization=HTX/cơ sở

class EntityUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    type: str | None = None
    summary: str | None = Field(None, max_length=2000)
    placeId: str | None = Field(None, max_length=100)
    season: dict | None = None
    attributes: dict | None = None
    images: list[str] | None = None

    @field_validator("name", mode="before")
    @classmethod
    def sanitize_name(cls, v):
        return _sanitize(v) if v else v

    @field_validator("summary", mode="before")
    @classmethod
    def sanitize_summary(cls, v):
        return _sanitize(v) if v else v

    @field_validator("type", mode="before")
    @classmethod
    def validate_type(cls, v):
        if v and v not in VALID_TYPES:
            raise ValueError(f"type must be one of: {', '.join(sorted(VALID_TYPES))}")
        return v

    @field_validator("season", mode="before")
    @classmethod
    def validate_season(cls, v):
        if v is not None:
            months = v.get("months", [])
            peak = v.get("peak", [])
            if not all(isinstance(m, int) and 1 <= m <= 12 for m in months):
                raise ValueError("season.months must be list of integers 1-12")
            if not all(isinstance(m, int) and 1 <= m <= 12 for m in peak):
                raise ValueError("season.peak must be list of integers 1-12")
            if peak and not all(m in months for m in peak):
                raise ValueError("season.peak must be subset of season.months")
        return v

    @field_validator("images", mode="before")
    @classmethod
    def validate_images(cls, v):
        if v is not None:
            if not isinstance(v, list):
                raise ValueError("images must be a list of URLs")
            if len(v) > 10:
                raise ValueError("Maximum 10 images per entity")
            for url in v:
                if not isinstance(url, str) or len(url) > 500:
                    raise ValueError("Each image must be a URL string under 500 chars")
        return v


class EntityCreate(BaseModel):
    id: str = Field(..., min_length=2, max_length=100, pattern=r'^[a-z0-9\-]+$')
    type: str
    name: str = Field(..., min_length=1, max_length=200)
    placeId: str | None = Field(None, max_length=100)
    summary: str = Field("", max_length=2000)
    season: dict | None = None
    attributes: dict = {}
    images: list[str] = []
    source: dict | None = None  # GĐ13: cho phép khai nguồn chính thống (vd danh bạ facility — KHÔNG bịa)

    @field_validator("name", mode="before")
    @classmethod
    def sanitize_name(cls, v):
        return _sanitize(v)

    @field_validator("summary", mode="before")
    @classmethod
    def sanitize_summary(cls, v):
        return _sanitize(v) if v else v

    @field_validator("type", mode="before")
    @classmethod
    def validate_type(cls, v):
        if v not in VALID_TYPES:
            raise ValueError(f"type must be one of: {', '.join(sorted(VALID_TYPES))}")
        return v

    @field_validator("season", mode="before")
    @classmethod
    def validate_season(cls, v):
        if v is not None:
            months = v.get("months", [])
            peak = v.get("peak", [])
            if not all(isinstance(m, int) and 1 <= m <= 12 for m in months):
                raise ValueError("season.months must be list of integers 1-12")
            if not all(isinstance(m, int) and 1 <= m <= 12 for m in peak):
                raise ValueError("season.peak must be list of integers 1-12")
        return v

    @field_validator("images", mode="before")
    @classmethod
    def validate_images(cls, v):
        if v is not None:
            if not isinstance(v, list):
                raise ValueError("images must be a list of URLs")
            if len(v) > 10:
                raise ValueError("Maximum 10 images per entity")
            for url in v:
                if not isinstance(url, str) or len(url) > 500:
                    raise ValueError("Each image must be a URL string under 500 chars")
        return v


# ── Entity CRUD ──

class DataQualityApplyRequest(BaseModel):
    candidate_ids: list[str] | None = None
    dry_run: bool = True

@router.get("/entities")
async def list_entities(
    type: Optional[str] = None,
    area: Optional[str] = None,
    q: Optional[str] = None,
    include_places: bool = False,
    orphans_only: bool = False,
    limit: int = Query(50, le=500),
    offset: int = 0,
):
    """Danh sách entities với filter — đọc từ database."""
    def _query():
        if q:
            results = db.search_entities(q=q, entity_type=type, area=area, limit=limit)
        elif type:
            results = db.list_entities(entity_type=type, area=area, limit=limit, offset=offset)
        else:
            results = db.list_entities(area=area, limit=limit, offset=offset)

        if include_places:
            places = db.list_entities(entity_type=None, limit=1000, offset=0)
            results = [e for e in (results + [p for p in places if p["type"] == "place"])]

        if orphans_only:
            with db._conn() as conn:
                rows = db._fetchall(conn,
                    "SELECT from_id AS eid FROM relationships UNION SELECT to_id FROM relationships", ())
                rel_ids = {db._row_to_dict(r)["eid"] for r in rows}
            results = [e for e in results if e.get("type") != "place" and e["id"] not in rel_ids]

        total = len(results)
        items = results[:limit] if q else results

        place_ids = list({e["placeId"] for e in items if e.get("placeId")})
        if place_ids:
            place_map = db.get_entities_batch(place_ids)
            for e in items:
                pid = e.get("placeId")
                if pid and pid in place_map:
                    e["place_name"] = place_map[pid]["name"]
                    e["area"] = place_map[pid].get("area") or e.get("area")

        return {"total": total, "offset": offset, "limit": limit, "entities": items}
    return await asyncio.to_thread(_query)


@router.get("/entities/places")
async def list_places():
    """Danh sách xã/phường cho dropdown."""
    def _query():
        db.initialize()
        with db._conn() as conn:
            rows = db._fetchall(conn, "SELECT id, name, area, level FROM entities WHERE type = 'place' ORDER BY name")
        return [db._row_to_dict(r) for r in rows]
    return await asyncio.to_thread(_query)


@router.get("/entities/check-duplicate")
async def check_duplicate(name: str = Query(..., min_length=2)):
    """Kiểm tra entity trùng tên (substring match, case-insensitive)."""
    name_lower = name.lower().strip()
    if len(name_lower) < 2:
        return {"duplicates": []}
    pattern = f"%{name_lower}%"
    def _query():
        with db._conn() as conn:
            rows = db._fetchall(conn,
                "SELECT id, name, type FROM entities WHERE type != 'place' AND LOWER(name) LIKE ? LIMIT 5",
                (pattern,))
        return {"duplicates": [{"id": db._row_to_dict(r)["id"], "name": db._row_to_dict(r)["name"],
                                "type": db._row_to_dict(r).get("type", "")} for r in rows]}
    return await asyncio.to_thread(_query)


@router.get("/entities/{entity_id}")
async def get_entity(entity_id: str):
    """Chi tiết 1 entity."""
    entity_id = validate_path_id(entity_id, "entity_id")
    def _query():
        entity = db.get_entity(entity_id)
        if not entity:
            raise HTTPException(404, f"Entity '{entity_id}' not found")
        entity["relationships"] = db.get_relationships(entity_id)
        return entity
    return await asyncio.to_thread(_query)


@router.put("/entities/{entity_id}")
async def update_entity(entity_id: str, update: EntityUpdate):
    """Cập nhật entity."""
    entity_id = validate_path_id(entity_id, "entity_id")
    def _query():
        existing = db.get_entity(entity_id)
        if not existing:
            raise HTTPException(404, f"Entity '{entity_id}' not found")
        old_snapshot = {k: v for k, v in existing.items()}
        updates = update.model_dump(exclude_none=True)
        existing.update(updates)
        existing["updatedAt"] = datetime.now().strftime("%Y-%m-%d")
        db.upsert_entity(existing)
        db.log_entity_changes(entity_id, old_snapshot, existing)
        _sync_kb()
        from public_api import invalidate_entity_cache, invalidate_place_cache
        invalidate_entity_cache(entity_id)
        if existing.get("type") == "place":
            invalidate_place_cache()
        return {"status": "updated", "entity": existing}
    return await asyncio.to_thread(_query)


@router.get("/entities/{entity_id}/history")
async def get_entity_history(entity_id: str, limit: int = Query(50, ge=1, le=200)):
    """Lịch sử thay đổi entity."""
    entity_id = validate_path_id(entity_id, "entity_id")
    def _query():
        return {"history": db.get_entity_history(entity_id, limit)}
    return await asyncio.to_thread(_query)


@router.post("/entities")
async def create_entity(entity: EntityCreate):
    """Tạo entity mới."""
    def _query():
        if db.get_entity(entity.id):
            raise HTTPException(409, f"Entity '{entity.id}' already exists")
        payload = entity.model_dump()
        src = payload.pop("source", None) or {"title": "admin", "method": "manual"}
        new_entity = {
            **payload,
            "source": src,
            "updatedAt": datetime.now().strftime("%Y-%m-%d"),
        }
        db.upsert_entity(new_entity)
        _sync_kb()
        return {"status": "created", "entity": new_entity}
    return await asyncio.to_thread(_query)


@router.delete("/entities/{entity_id}")
async def delete_entity(entity_id: str):
    """Xóa entity."""
    entity_id = validate_path_id(entity_id, "entity_id")
    def _query():
        entity = db.get_entity(entity_id)
        if not entity:
            raise HTTPException(404, f"Entity '{entity_id}' not found")
        db.delete_entity(entity_id)
        _sync_kb()
        if entity.get("type") == "place":
            from public_api import invalidate_place_cache
            invalidate_place_cache()
    await asyncio.to_thread(_query)
    return {"status": "deleted", "entity_id": entity_id}


class _EntityImageURL(BaseModel):
    url: str


@router.post("/entities/{entity_id}/images")
async def add_entity_image_url(entity_id: str, body: _EntityImageURL):
    """GĐ8.4: thêm ảnh entity theo URL (chỉ nguồn cấp phép — B6)."""
    entity_id = validate_path_id(entity_id, "entity_id")
    url = (body.url or "").strip()
    if not (url.startswith("http://") or url.startswith("https://") or url.startswith("/")):
        raise HTTPException(400, "URL ảnh không hợp lệ")
    def _query():
        entity = db.get_entity(entity_id)
        if not entity:
            raise HTTPException(404, f"Entity '{entity_id}' not found")
        images = list(entity.get("images") or [])
        if len(images) >= 10:
            raise HTTPException(400, "Tối đa 10 ảnh mỗi entity")
        if url not in images:
            images.append(url)
        entity["images"] = images
        entity["updatedAt"] = datetime.now().strftime("%Y-%m-%d")
        db.upsert_entity(entity)
        _sync_kb()
        return {"status": "added", "images": images}
    return await asyncio.to_thread(_query)


@router.post("/entities/{entity_id}/images/upload")
async def upload_entity_image(entity_id: str, file: UploadFile = File(...)):
    """GĐ8.4: upload file ảnh → WebP 3 cỡ → R2 (fallback đĩa) → entity.images.
    Lưu URL cỡ md (800px) làm ảnh hiển thị; sm/lg cũng được upload để dùng srcset sau."""
    entity_id = validate_path_id(entity_id, "entity_id")
    from fastapi.concurrency import run_in_threadpool
    from storage import storage, MAX_IMAGE_SIZE

    entity = db.get_entity(entity_id)
    if not entity:
        raise HTTPException(404, f"Entity '{entity_id}' not found")
    data = await file.read()
    if len(data) > MAX_IMAGE_SIZE:
        raise HTTPException(400, f"Ảnh quá lớn (tối đa {MAX_IMAGE_SIZE // 1024 // 1024}MB)")
    # Không tin Content-Type client gửi — kiểm magic-byte thật.
    if not storage.sniff_image_type(data):
        raise HTTPException(400, "File không phải ảnh hợp lệ (JPEG/PNG/GIF/WebP)")
    if len(entity.get("images") or []) >= 10:
        raise HTTPException(400, "Tối đa 10 ảnh mỗi entity")
    try:
        urls = await run_in_threadpool(storage.upload_image_set, data, "entities", entity_id)
    except ValueError:
        raise HTTPException(400, "Ảnh không hợp lệ hoặc đã hỏng")
    except Exception:
        logger.exception("Entity image upload failed for %s", entity_id)
        raise HTTPException(500, "Không thể upload ảnh, vui lòng thử lại")

    cover = urls.get("md") or urls.get("lg")
    images = list(entity.get("images") or [])
    if cover and cover not in images:
        images.append(cover)
    entity["images"] = images
    entity["updatedAt"] = datetime.now().strftime("%Y-%m-%d")
    db.upsert_entity(entity)
    _sync_kb()
    return {"status": "uploaded", "url": cover, "sizes": urls, "images": images, "backend": storage.backend}


@router.delete("/entities/{entity_id}/images/{idx}")
async def remove_entity_image(entity_id: str, idx: int):
    """Gỡ ảnh thứ idx khỏi entity.images (không xoá file R2 — tránh mất ảnh dùng chung)."""
    entity_id = validate_path_id(entity_id, "entity_id")
    def _query():
        entity = db.get_entity(entity_id)
        if not entity:
            raise HTTPException(404, f"Entity '{entity_id}' not found")
        images = list(entity.get("images") or [])
        if 0 <= idx < len(images):
            images.pop(idx)
        entity["images"] = images
        entity["updatedAt"] = datetime.now().strftime("%Y-%m-%d")
        db.upsert_entity(entity)
        _sync_kb()
        return {"status": "removed", "images": images}
    return await asyncio.to_thread(_query)


@router.get("/unclassified")
async def list_unclassified(limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0),
                            q: Optional[str] = None):
    """Entity nội dung CHƯA gán xã/phường (placeId rỗng) — để admin gán đúng (lấp nợ placeId)."""
    ql = (q or "").lower().strip()
    base = "FROM entities WHERE type != 'place' AND (placeId IS NULL OR placeId = '')"
    params: list = []
    if ql:
        base += " AND LOWER(name) LIKE ?"
        params.append(f"%{ql}%")
    def _query():
        with db._conn() as conn:
            cnt = db._fetchone(conn, f"SELECT COUNT(*) as c {base}", tuple(params))
            total = db._row_to_dict(cnt)["c"] if cnt else 0
            rows = db._fetchall(conn, f"SELECT id, name, type, area, summary {base} ORDER BY name LIMIT ? OFFSET ?",
                                tuple(params) + (limit, offset))
        out = [{"id": db._row_to_dict(r)["id"], "name": db._row_to_dict(r).get("name"),
                "type": db._row_to_dict(r).get("type"), "area": db._row_to_dict(r).get("area"),
                "summary": (db._row_to_dict(r).get("summary") or "")[:100]} for r in rows]
        return {"total": total, "entities": out}
    return await asyncio.to_thread(_query)


class AssignPlaceRequest(BaseModel):
    place_id: Optional[str] = Field(None, max_length=100)


@router.post("/entities/{entity_id}/place")
async def assign_place(entity_id: str, body: AssignPlaceRequest):
    """Gán (hoặc gỡ) xã/phường cho 1 entity. Validate place_id là place thật (chống gán bừa)."""
    entity_id = validate_path_id(entity_id, "entity_id")
    def _query():
        e = db.get_entity(entity_id)
        if not e:
            raise HTTPException(404, f"Entity '{entity_id}' not found")
        pid = body.place_id or None
        if pid:
            p = db.get_entity(pid)
            if not p or p.get("type") != "place":
                raise HTTPException(400, f"'{pid}' không phải xã/phường hợp lệ")
            e["area"] = p.get("area") or e.get("area")
        e["placeId"] = pid
        e["updatedAt"] = datetime.now().strftime("%Y-%m-%d")
        db.upsert_entity(e)
        _sync_kb()
        return {"status": "ok", "id": entity_id, "placeId": pid}
    return await asyncio.to_thread(_query)


# ── Itinerary CRUD ──

@router.get("/itineraries")
async def list_itineraries_admin(area: Optional[str] = None):
    return await asyncio.to_thread(db.list_itineraries, area=area)

@router.get("/itineraries/{itin_id}")
async def get_itinerary_admin(itin_id: str):
    itin_id = validate_path_id(itin_id, "itin_id")
    def _query():
        it = db.get_itinerary(itin_id)
        if not it:
            raise HTTPException(404, "Itinerary not found")
        return it
    return await asyncio.to_thread(_query)

class ItineraryCreate(BaseModel):
    id: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=300)
    description: str | None = Field(None, max_length=2000)
    days: list | None = None
    area: str | None = Field(None, max_length=100)
    tags: list[str] | None = None

class ItineraryUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=300)
    description: str | None = Field(None, max_length=2000)
    days: list | None = None
    area: str | None = Field(None, max_length=100)
    tags: list[str] | None = None

class RelationshipCreate(BaseModel):
    from_id: str = Field(..., min_length=1, max_length=100)
    to_id: str = Field(..., min_length=1, max_length=100)
    type: str = Field(..., min_length=1, max_length=100)

class RelationshipBulkPair(BaseModel):
    to_id: str = Field(..., min_length=1, max_length=100)
    type: str = Field("related_to", max_length=100)

class RelationshipBulkCreate(BaseModel):
    from_id: str = Field(..., min_length=1, max_length=100)
    pairs: list[RelationshipBulkPair] = Field(..., max_length=50)


@router.post("/itineraries")
async def create_itinerary(body: ItineraryCreate):
    def _query():
        data = body.model_dump(exclude_none=True)
        db.upsert_itinerary(data)
    await asyncio.to_thread(_query)
    return {"status": "created", "id": body.id}

@router.put("/itineraries/{itin_id}")
async def update_itinerary(itin_id: str, body: ItineraryUpdate):
    itin_id = validate_path_id(itin_id, "itin_id")
    def _query():
        data = body.model_dump(exclude_none=True)
        data["id"] = itin_id
        db.upsert_itinerary(data)
    await asyncio.to_thread(_query)
    return {"status": "updated", "id": itin_id}

@router.delete("/itineraries/{itin_id}")
async def delete_itinerary(itin_id: str):
    itin_id = validate_path_id(itin_id, "itin_id")
    def _query():
        db.initialize()
        ph = db._ph
        with db._conn() as conn:
            db._execute(conn, f"DELETE FROM itineraries WHERE id = {ph}", (itin_id,))
    await asyncio.to_thread(_query)
    return {"status": "deleted", "id": itin_id}


# ── Relationship CRUD ──

@router.post("/relationships")
async def add_relationship(body: RelationshipCreate):
    await asyncio.to_thread(db.add_relationship, body.from_id, body.to_id, body.type)
    return {"status": "created"}

@router.delete("/relationships")
async def delete_relationship(from_id: str, to_id: str, type: str):
    validate_path_id(from_id, "from_id")
    validate_path_id(to_id, "to_id")
    def _query():
        db.initialize()
        ph = db._ph
        with db._conn() as conn:
            db._execute(conn, f"DELETE FROM relationships WHERE from_id={ph} AND to_id={ph} AND type={ph}",
                        (from_id, to_id, type))
    await asyncio.to_thread(_query)
    return {"status": "deleted"}


@router.post("/relationships/bulk")
async def add_relationships_bulk(body: RelationshipBulkCreate):
    """B7b: thêm nhiều quan hệ cùng lúc."""
    def _query():
        added = 0
        errors = []
        for p in body.pairs:
            to_id = p.to_id.strip()
            rel_type = p.type
            if not to_id:
                continue
            try:
                db.add_relationship(body.from_id, to_id, rel_type)
                added += 1
            except Exception as e:
                errors.append({"to_id": to_id, "error": str(e)})
        return {"added": added, "errors": errors}
    return await asyncio.to_thread(_query)


# ── Bulk operations ──

# Data quality review queue

@router.get("/data-quality/summary")
async def data_quality_summary(refresh: bool = Query(False)):
    def _query():
        data_summary = data_quality.summarize_data()
        queue = data_quality.load_candidate_queue(refresh=refresh)
        return {
            "data": data_summary,
            "candidates": queue.get("counts", {}),
            "stream_counts": queue.get("stream_counts", {}),
            "cache": queue.get("cache", {}),
            "sitemap": {
                "expected_public_detail_urls": data_summary["public_entities"],
                "expected_itinerary_urls": data_summary["itineraries"],
                "expected_public_content_urls": data_summary["public_entities"] + data_summary["itineraries"],
            },
            "policy": queue.get("policy", {}),
        }
    return await asyncio.to_thread(_query)

@router.get("/data-quality/review")
async def data_quality_review(
    kind: Optional[str] = Query(None, pattern="^(source|location|placeid|accuracy|relationship)$"),
    bucket: Optional[str] = Query(None, pattern="^(auto_apply|needs_review|reject)$"),
    refresh: bool = Query(False),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    def _query():
        queue = data_quality.load_candidate_queue(refresh=refresh)
        result = data_quality.filter_candidates(queue, kind=kind, bucket=bucket, limit=limit, offset=offset)
        result["cache"] = queue.get("cache", {})
        return result
    return await asyncio.to_thread(_query)

@router.post("/data-quality/apply")
async def data_quality_apply(body: DataQualityApplyRequest):
    def _query():
        result = data_quality.apply_candidates(body.candidate_ids, dry_run=body.dry_run)
        if result.get("applied_count") and not body.dry_run:
            _sync_kb()
        return result
    return await asyncio.to_thread(_query)

@router.get("/data-quality/history")
async def data_quality_history(limit: int = Query(20, ge=1, le=200)):
    return await asyncio.to_thread(data_quality.load_apply_history, limit=limit)

@router.post("/data-quality/rollback/{batch_id}")
async def data_quality_rollback(batch_id: str):
    validate_path_id(batch_id)
    def _query():
        try:
            result = data_quality.rollback_apply(batch_id)
        except ValueError as exc:
            raise HTTPException(400, detail=str(exc)) from exc
        except FileNotFoundError as exc:
            raise HTTPException(404, detail=str(exc)) from exc
        _sync_kb()
        return result
    return await asyncio.to_thread(_query)

@router.post("/entities/bulk-delete")
async def bulk_delete(entity_ids: list[str]):
    """Xóa nhiều entities cùng lúc."""
    def _query():
        deleted = 0
        for eid in entity_ids:
            if db.delete_entity(eid):
                deleted += 1
        return deleted
    deleted = await asyncio.to_thread(_query)
    return {"status": "deleted", "count": deleted}


# ══════════════════════════════════════════════════
#  IMAGE INGEST REVIEW QUEUE (P2, review-gated — B6)
# ══════════════════════════════════════════════════
# Human-in-the-loop: ingest scripts queue licensed image CANDIDATES; nothing goes
# live until an admin approves here. On approve we re-encode + upload to R2 and
# carry license + author + source onto the entity (attributes.image_credits) per B6.

import image_suggestions as _imgq


class ImageSuggestionItem(BaseModel):
    entity_id: str = Field(..., min_length=1, max_length=100)
    candidate_url: str = Field(..., min_length=1, max_length=600)
    wp_title: str = Field("", max_length=200)
    license: str = Field("", max_length=80)
    author: str = Field("", max_length=120)
    source: str = Field("wikipedia-vi", max_length=40)
    match_confidence: float = Field(0.7, ge=0.0, le=1.0)


class ImageSuggestionBatch(BaseModel):
    suggestions: list[ImageSuggestionItem] = Field(..., max_length=500)


class RejectSuggestionRequest(BaseModel):
    reason: str | None = Field(None, max_length=300)


@router.get("/image-suggestions")
async def list_image_suggestions(
    status: Optional[str] = Query(None, pattern="^(pending|approved|rejected)$"),
    entity_id: Optional[str] = Query(None, max_length=100),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Liệt kê ứng viên ảnh chờ duyệt (mặc định: tất cả; lọc theo status/entity)."""
    def _query():
        result = _imgq.list_suggestions(status=status, entity_id=entity_id, limit=limit, offset=offset)
        result["counts"] = _imgq.status_counts()
        return result
    return await asyncio.to_thread(_query)


@router.get("/image-suggestions/{suggestion_id}")
async def get_image_suggestion(suggestion_id: str):
    """Chi tiết 1 ứng viên ảnh (kèm tên entity để review)."""
    validate_path_id(suggestion_id)
    def _query():
        s = _imgq.get_suggestion(suggestion_id)
        if not s:
            raise HTTPException(404, f"Suggestion '{suggestion_id}' not found")
        return s
    return await asyncio.to_thread(_query)


@router.post("/image-suggestions/create-batch")
async def create_image_suggestion_batch(body: ImageSuggestionBatch):
    """Nhận lô ứng viên từ script ingest (mode=queue). KHÔNG publish — chỉ xếp hàng chờ duyệt."""
    def _query():
        payload = [s.model_dump() for s in body.suggestions]
        return _imgq.create_batch(payload)
    return await asyncio.to_thread(_query)


def _assert_public_url(url: str) -> None:
    """P0-13: chặn SSRF — chỉ http(s) tới host phân giải ra IP CÔNG KHAI
    (chặn 169.254.169.254, localhost, 10/172.16/192.168, link-local…)."""
    import ipaddress
    import socket
    from urllib.parse import urlparse
    p = urlparse(url or "")
    if p.scheme not in ("http", "https") or not p.hostname:
        raise HTTPException(400, "URL ảnh không hợp lệ (chỉ http/https)")
    try:
        infos = socket.getaddrinfo(p.hostname, p.port or (443 if p.scheme == "https" else 80))
    except Exception:
        raise HTTPException(400, "Không phân giải được host ảnh")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
                or ip.is_multicast or ip.is_unspecified):
            raise HTTPException(400, "Host ảnh trỏ địa chỉ nội bộ — từ chối (SSRF)")


@router.post("/image-suggestions/{suggestion_id}/approve")
async def approve_image_suggestion(suggestion_id: str):
    """Duyệt 1 ứng viên: tải ảnh → WebP 3 cỡ → R2 → gắn vào entity.images + lưu
    license/author/source vào attributes.image_credits (B6). Chỉ xử lý khi đang 'pending'."""
    validate_path_id(suggestion_id)
    from fastapi.concurrency import run_in_threadpool
    from storage import storage, MAX_IMAGE_SIZE

    s = _imgq.get_suggestion(suggestion_id)
    if not s:
        raise HTTPException(404, f"Suggestion '{suggestion_id}' not found")
    if s.get("status") != "pending":
        raise HTTPException(400, f"Suggestion đã ở trạng thái '{s.get('status')}' — không thể duyệt lại")

    entity = db.get_entity(s["entity_id"])
    if not entity:
        raise HTTPException(404, f"Entity '{s['entity_id']}' not found")

    images = list(entity.get("images") or [])
    if len(images) >= 10:
        raise HTTPException(400, "Tối đa 10 ảnh mỗi entity")

    # Fetch the candidate from its licensed source (Commons etc.). Bounded + guarded.
    candidate_url = s["candidate_url"]
    _assert_public_url(candidate_url)  # P0-13: chặn SSRF tới host nội bộ
    try:
        import httpx
        headers = {"User-Agent": "vinhlong360-image-review/1.0 (+https://vinhlong360.vn)"}
        resp = await run_in_threadpool(
            lambda: httpx.get(candidate_url, headers=headers, timeout=25, follow_redirects=True)
        )
        resp.raise_for_status()
        data = resp.content
    except Exception as e:  # noqa: BLE001 — network/404 → 502 with retry note
        raise HTTPException(502, f"Không tải được ảnh nguồn (thử lại sau): {str(e)[:120]}")

    if not data or len(data) > MAX_IMAGE_SIZE:
        raise HTTPException(400, f"Ảnh nguồn rỗng hoặc quá lớn (tối đa {MAX_IMAGE_SIZE // 1024 // 1024}MB)")

    try:
        urls = await run_in_threadpool(storage.upload_image_set, data, "entities", s["entity_id"])
    except Exception:
        logger.exception("Suggestion image upload failed for %s", s.get("entity_id"))
        raise HTTPException(500, "Không thể upload ảnh, vui lòng thử lại")

    cover = urls.get("md") or urls.get("lg") or urls.get("sm")
    if cover and cover not in images:
        images.append(cover)
    entity["images"] = images

    # B6: persist license + author + source alongside the uploaded URL.
    attrs = entity.get("attributes") or {}
    if not isinstance(attrs, dict):
        attrs = {}
    credits = attrs.get("image_credits")
    if not isinstance(credits, list):
        credits = []
    credits.append({
        "url": cover,
        "license": s.get("license") or "",
        "author": s.get("author") or "",
        "source": s.get("source") or "",
        "source_url": candidate_url,
        "wp_title": s.get("wp_title") or "",
        "added_at": datetime.now().strftime("%Y-%m-%d"),
    })
    attrs["image_credits"] = credits
    entity["attributes"] = attrs
    entity["updatedAt"] = datetime.now().strftime("%Y-%m-%d")
    db.upsert_entity(entity)

    # require_admin already authenticated; record a generic approver marker for audit.
    _imgq.mark_status(suggestion_id, "approved", approved_by="admin")
    _sync_kb()
    return {"status": "approved", "url": cover, "sizes": urls, "images": images,
            "backend": storage.backend, "credits": credits[-1]}


@router.post("/image-suggestions/{suggestion_id}/reject")
async def reject_image_suggestion(suggestion_id: str, body: RejectSuggestionRequest = RejectSuggestionRequest()):
    """Từ chối 1 ứng viên (ghi lý do). Không tải/không upload gì."""
    validate_path_id(suggestion_id)
    def _query():
        s = _imgq.get_suggestion(suggestion_id)
        if not s:
            raise HTTPException(404, f"Suggestion '{suggestion_id}' not found")
        if s.get("status") != "pending":
            raise HTTPException(400, f"Suggestion đã ở trạng thái '{s.get('status')}' — không thể từ chối lại")
        _imgq.mark_status(suggestion_id, "rejected", rejection_reason=(body.reason or "").strip())
    await asyncio.to_thread(_query)
    return {"status": "rejected", "id": suggestion_id}


# ── Data management ──

@router.get("/stats")
async def admin_stats():
    """Thống kê chi tiết cho admin."""
    def _query():
        db.initialize()
        ph = db._ph
        with db._conn() as conn:
            type_rows = db._fetchall(conn, "SELECT type, COUNT(*) as c FROM entities GROUP BY type", ())
            rel_count = db._fetchone(conn, "SELECT COUNT(*) as c FROM relationships", ())
            itin_count = db._fetchone(conn, "SELECT COUNT(*) as c FROM itineraries", ())

        by_type = {}
        total_entities = 0
        total_places = 0
        for r in type_rows:
            d = db._row_to_dict(r)
            if d["type"] == "place":
                total_places = d["c"]
            else:
                by_type[d["type"]] = d["c"]
                total_entities += d["c"]

        with db._conn() as c2:
            comp = db._fetchone(c2, """
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN summary IS NOT NULL AND summary != '' THEN 1 ELSE 0 END) as has_summary,
                       SUM(CASE WHEN images IS NOT NULL AND images != '' AND images != '[]' THEN 1 ELSE 0 END) as has_images,
                       SUM(CASE WHEN placeId IS NOT NULL AND placeId != '' THEN 1 ELSE 0 END) as has_place
                FROM entities WHERE type != 'place'
            """, ())
            cd = db._row_to_dict(comp) if comp else {}
            comp_total = cd.get("total", 0)
            has_summary = cd.get("has_summary", 0)
            has_images = cd.get("has_images", 0)
            has_place = cd.get("has_place", 0)
            orphan_row = db._fetchone(c2, """
                SELECT COUNT(*) as c FROM entities
                WHERE type != 'place'
                  AND id NOT IN (SELECT DISTINCT from_id FROM relationships UNION SELECT DISTINCT to_id FROM relationships)
            """, ())
            orphan_count = db._row_to_dict(orphan_row)["c"] if orphan_row else 0
        completeness = {
            "total": comp_total,
            "has_summary": has_summary,
            "has_images": has_images,
            "has_place": has_place,
            "orphans": orphan_count,
            "pct": round((has_summary + has_images + has_place) / (comp_total * 3) * 100, 1) if comp_total else 0,
        }

        deltas = {}
        if db._use_pg:
            try:
                with db._conn() as pg:
                    users_week = db._fetchone(pg, "SELECT COUNT(*) as c FROM users WHERE created_at > NOW() - INTERVAL '7 days'", ())
                    posts_week = db._fetchone(pg, "SELECT COUNT(*) as c FROM posts WHERE created_at > NOW() - INTERVAL '7 days'", ())
                    total_users = db._fetchone(pg, "SELECT COUNT(*) as c FROM users", ())
                    total_posts = db._fetchone(pg, "SELECT COUNT(*) as c FROM posts", ())
                deltas = {
                    "users_week": db._row_to_dict(users_week)["c"] if users_week else 0,
                    "posts_week": db._row_to_dict(posts_week)["c"] if posts_week else 0,
                    "total_users": db._row_to_dict(total_users)["c"] if total_users else 0,
                    "total_posts": db._row_to_dict(total_posts)["c"] if total_posts else 0,
                }
            except Exception:
                pass

        entities_week = 0
        try:
            with db._conn() as c3:
                ew = db._fetchone(c3, "SELECT COUNT(*) as c FROM entities WHERE type != 'place' AND created_at >= datetime('now', '-7 days')", ())
                entities_week = db._row_to_dict(ew)["c"] if ew else 0
        except Exception:
            pass

        backup_info = None
        try:
            backup_dir = Path(__file__).resolve().parent.parent / "scratch" / "backups"
            if backup_dir.exists():
                dirs = sorted(backup_dir.iterdir(), key=lambda p: p.name, reverse=True)
                if dirs:
                    latest = dirs[0]
                    size_mb = round(sum(f.stat().st_size for f in latest.rglob("*") if f.is_file()) / 1048576, 1)
                    backup_info = {"last": latest.name, "size_mb": size_mb, "count": len(dirs)}
        except Exception:
            pass

        return {
            "total_entities": total_entities,
            "total_places": total_places,
            "total_relationships": rel_count["c"] if rel_count else 0,
            "total_itineraries": itin_count["c"] if itin_count else 0,
            "by_type": by_type,
            "completeness": completeness,
            "entities_week": entities_week,
            "backup": backup_info,
            **deltas,
        }
    return await asyncio.to_thread(_query)


@router.post("/backup-trigger")
async def trigger_backup():
    """B5c: trigger manual backup from admin UI."""
    script = Path(__file__).resolve().parent.parent / "scripts" / "backup_data.py"
    if not script.exists():
        raise HTTPException(500, "backup_data.py not found")
    def _run():
        try:
            result = subprocess.run(
                [sys.executable, str(script), "--label", "admin-manual"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                raise HTTPException(500, result.stderr or "Backup failed")
            backup_dir = Path(__file__).resolve().parent.parent / "scratch" / "backups"
            dirs = sorted(backup_dir.iterdir(), key=lambda p: p.name, reverse=True)
            latest = dirs[0] if dirs else None
            size_mb = round(sum(f.stat().st_size for f in latest.rglob("*") if f.is_file()) / 1048576, 1) if latest else 0
            return {
                "success": True,
                "backup_name": latest.name if latest else None,
                "size_mb": size_mb,
                "output": result.stdout.strip(),
            }
        except subprocess.TimeoutExpired:
            raise HTTPException(504, "Backup timed out")
        except HTTPException:
            raise
        except Exception:
            logger.exception("Backup failed")
            raise HTTPException(500, "Backup thất bại. Kiểm tra log server.")
    return await asyncio.to_thread(_run)


@router.get("/media")
async def media_gallery(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    filter: str = Query("all", pattern="^(all|missing_credit|duplicate)$"),
):
    """B6a: Central media gallery — flat list of all images across entities."""
    def _query():
        entities = db.all_entities()
        media_items = []
        url_usage: dict[str, list[str]] = {}
        for e in entities:
            images = e.get("images") or []
            if isinstance(images, str):
                try:
                    images = json.loads(images)
                except Exception:
                    images = []
            for img in images:
                url = img.get("url") or img if isinstance(img, str) else img.get("url", "")
                if not url:
                    continue
                credit = img.get("credit") or img.get("author") or "" if isinstance(img, dict) else ""
                license_info = img.get("license", "") if isinstance(img, dict) else ""
                item = {
                    "url": url,
                    "entity_id": e.get("id", ""),
                    "entity_name": e.get("name", ""),
                    "entity_type": e.get("type", ""),
                    "credit": credit,
                    "license": license_info,
                }
                media_items.append(item)
                url_usage.setdefault(url, []).append(e.get("id", ""))

        if filter == "missing_credit":
            media_items = [m for m in media_items if not m["credit"]]
        elif filter == "duplicate":
            dup_urls = {u for u, ids in url_usage.items() if len(ids) > 1}
            media_items = [m for m in media_items if m["url"] in dup_urls]

        total = len(media_items)
        offset = (page - 1) * limit
        page_items = media_items[offset:offset + limit]

        for item in page_items:
            usage = url_usage.get(item["url"], [])
            item["usage_count"] = len(usage)

        dup_count = sum(1 for u, ids in url_usage.items() if len(ids) > 1)
        no_credit_count = sum(1 for m in media_items if not m["credit"]) if filter != "missing_credit" else total

        return {
            "items": page_items,
            "total": total,
            "page": page,
            "stats": {
                "total_images": len(media_items) if filter == "all" else sum(len(e.get("images") or []) for e in entities),
                "duplicates": dup_count,
                "missing_credit": no_credit_count,
            },
        }
    return await asyncio.to_thread(_query)


@router.get("/badge-counts")
async def badge_counts():
    """Lightweight counts cho sidebar badges — moderation/images/unclassified/provisional."""
    def _query():
        counts = {"moderation": 0, "images": 0, "unclassified": 0, "provisional": 0, "reports": 0}
        with db._conn() as conn:
            row = db._fetchone(conn, "SELECT COUNT(*) as c FROM posts WHERE moderation_status IN ('pending','review','flagged')", ())
            if row:
                counts["moderation"] = db._row_to_dict(row)["c"]
        try:
            counts["images"] = _imgq.status_counts().get("pending", 0)
        except Exception:
            pass
        with db._conn() as conn2:
            unc_row = db._fetchone(conn2, "SELECT COUNT(*) as c FROM entities WHERE type != 'place' AND (placeId IS NULL OR placeId = '')", ())
            counts["unclassified"] = db._row_to_dict(unc_row)["c"] if unc_row else 0
        try:
            import kb_curation
            s = kb_curation.stats()
            counts["provisional"] = s.get("pending", 0)
        except Exception:
            pass
        if _INFO_REPORTS_FILE.exists():
            try:
                lines = _INFO_REPORTS_FILE.read_text(encoding="utf-8").strip().split("\n")
                counts["reports"] = sum(1 for l in lines if l.strip() and json.loads(l).get("status", "open") == "open")
            except Exception:
                pass
        return counts
    return await asyncio.to_thread(_query)


@router.get("/dashboard-alerts")
async def dashboard_alerts():
    """Priority-sorted alerts cho admin dashboard."""
    def _query():
        alerts: list[dict] = []
        with db._conn() as conn:
            mod = db._fetchone(conn, "SELECT COUNT(*) as c FROM posts WHERE moderation_status IN ('flagged')", ())
            flagged = db._row_to_dict(mod)["c"] if mod else 0
            mod2 = db._fetchone(conn, "SELECT COUNT(*) as c FROM posts WHERE moderation_status IN ('pending','review')", ())
            pending_mod = db._row_to_dict(mod2)["c"] if mod2 else 0
        if flagged:
            alerts.append({"type": "flagged", "count": flagged, "label": f"{flagged} bài viết bị gắn cờ", "icon": "🚩", "link": "/admin/kiem-duyet?tab=flagged", "priority": 1})
        if pending_mod:
            alerts.append({"type": "moderation", "count": pending_mod, "label": f"{pending_mod} bài chờ duyệt", "icon": "📝", "link": "/admin/kiem-duyet", "priority": 2})
        if _INFO_REPORTS_FILE.exists():
            try:
                lines = _INFO_REPORTS_FILE.read_text(encoding="utf-8").strip().split("\n")
                open_reports = sum(1 for l in lines if l.strip() and json.loads(l).get("status", "open") == "open")
                if open_reports:
                    alerts.append({"type": "reports", "count": open_reports, "label": f"{open_reports} báo sai chưa xử lý", "icon": "⚠️", "link": "/admin/bao-cao", "priority": 3})
            except Exception:
                pass
        try:
            img_pending = _imgq.status_counts().get("pending", 0)
            if img_pending:
                alerts.append({"type": "images", "count": img_pending, "label": f"{img_pending} ảnh chờ duyệt", "icon": "🖼️", "link": "/admin/duyet-anh", "priority": 4})
        except Exception:
            pass
        with db._conn() as conn2:
            unc_row = db._fetchone(conn2, "SELECT COUNT(*) as c FROM entities WHERE type != 'place' AND (placeId IS NULL OR placeId = '')", ())
            unc_count = db._row_to_dict(unc_row)["c"] if unc_row else 0
        if unc_count:
            alerts.append({"type": "unclassified", "count": unc_count, "label": f"{unc_count} entity chưa phân loại", "icon": "📍", "link": "/admin/chua-phan-loai", "priority": 5})
        try:
            import kb_curation
            s = kb_curation.stats()
            prov = s.get("pending", 0)
            if prov:
                alerts.append({"type": "provisional", "count": prov, "label": f"{prov} entity chờ xét duyệt", "icon": "🔬", "link": "/admin/duyet-tu-hoc", "priority": 6})
        except Exception:
            pass
        alerts.sort(key=lambda a: a["priority"])
        return {"alerts": alerts[:5]}
    return await asyncio.to_thread(_query)


@router.get("/activity-feed")
async def activity_feed(limit: int = Query(10, ge=1, le=50)):
    """10 admin actions gần nhất từ audit JSONL."""
    def _query():
        if not _AUDIT_FILE.exists():
            return {"actions": []}
        try:
            lines = _AUDIT_FILE.read_text(encoding="utf-8").strip().split("\n")
            actions = []
            for line in reversed(lines):
                if not line.strip():
                    continue
                try:
                    actions.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
                if len(actions) >= limit:
                    break
            return {"actions": actions}
        except Exception:
            return {"actions": []}
    return await asyncio.to_thread(_query)


_learn_proc: Optional[subprocess.Popen] = None

@router.post("/trigger-learn")
async def trigger_learn(category: Optional[str] = None, topics: int = 3):
    """Trigger 1 vòng auto-learn (chạy background)."""
    if topics < 1 or topics > 20:
        raise HTTPException(400, "topics must be between 1 and 20")
    if category:
        if len(category) > 50 or not re.match(r'^[\w\s\-À-ɏḀ-ỿ]+$', category):
            raise HTTPException(400, "Invalid category — only letters, numbers, hyphens, underscores allowed (max 50 chars)")
    cmd = [sys.executable, str(ROOT / "agent" / "auto_learn.py"), "--apply", "--topics", str(topics)]
    if category:
        cmd.extend(["--category", category])

    def _start():
        global _learn_proc
        if _learn_proc is not None and _learn_proc.poll() is None:
            raise HTTPException(409, f"Auto-learn đang chạy (PID {_learn_proc.pid}). Vui lòng chờ xong.")
        try:
            _learn_proc = subprocess.Popen(
                cmd,
                cwd=str(ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
            return {
                "status": "started",
                "pid": _learn_proc.pid,
                "command": " ".join(cmd),
                "note": "Chạy background. Gọi POST /reload sau khi xong.",
            }
        except Exception:
            logger.exception("Auto-learn trigger failed")
            raise HTTPException(500, "Không thể khởi chạy auto-learn. Kiểm tra log server.")
    return await asyncio.to_thread(_start)


# ── Quarantine review queue (provisional auto-learned entities) ──

@router.get("/provisional")
async def list_provisional_entities():
    """Liệt kê các entity tự học CHƯA kiểm chứng (chờ duyệt)."""
    def _query():
        import kb_curation
        return {"provisional": kb_curation.list_provisional(), **kb_curation.stats()}
    return await asyncio.to_thread(_query)


@router.post("/provisional/{entity_id}/approve")
async def approve_provisional(entity_id: str):
    """Duyệt 1 entity provisional → verified (tin cậy)."""
    validate_path_id(entity_id)
    def _query():
        import kb_curation
        result = kb_curation.promote(entity_id)
        if not result.get("ok"):
            raise HTTPException(404 if result.get("error") == "not found" else 400, result.get("error", "failed"))
        return result
    return await asyncio.to_thread(_query)


@router.post("/provisional/{entity_id}/reject")
async def reject_provisional(entity_id: str):
    """Từ chối + xóa 1 entity provisional khỏi KB."""
    validate_path_id(entity_id)
    def _query():
        import kb_curation
        result = kb_curation.reject(entity_id)
        if not result.get("ok"):
            raise HTTPException(404 if result.get("error") == "not found" else 400, result.get("error", "failed"))
        return result
    return await asyncio.to_thread(_query)


@router.post("/export")
async def export_data():
    """Export toàn bộ entities từ DB — streaming JSON để không OOM."""
    import io

    def _generate():
        yield '{"entities":['
        entities = db.list_entities(limit=10000)
        for i, e in enumerate(entities):
            if i:
                yield ","
            yield json.dumps(e, ensure_ascii=False)
        yield '],"relationships":['
        with db._conn() as conn:
            rels = db._fetchall(conn, "SELECT from_id, to_id, type FROM relationships", ())
        for i, r in enumerate(rels):
            if i:
                yield ","
            yield json.dumps(db._row_to_dict(r), ensure_ascii=False)
        yield '],"itineraries":['
        with db._conn() as conn:
            itins = db._fetchall(conn, "SELECT * FROM itineraries", ())
        for i, it in enumerate(itins):
            if i:
                yield ","
            yield json.dumps(db._row_to_dict(it), ensure_ascii=False)
        yield ']}'

    return StreamingResponse(_generate(), media_type="application/json",
                             headers={"Content-Disposition": "attachment; filename=vinhlong360-export.json"})


@router.get("/sources")
async def list_sources():
    """Liệt kê tất cả nguồn dữ liệu."""
    def _query():
        all_entities = db.list_entities(limit=10000)
        sources = {}
        for e in all_entities:
            if e.get("type") == "place":
                continue
            src = e.get("source", {})
            if isinstance(src, str):
                try:
                    src = json.loads(src)
                except Exception:
                    src = {}
            if isinstance(src, dict):
                key = src.get("title", "unknown")
                if key not in sources:
                    sources[key] = {"count": 0, "sample_url": src.get("url", "")}
                sources[key]["count"] += 1
        return {"sources": sources}
    return await asyncio.to_thread(_query)


# ═══════════════════════════════════════════════════════
# Moderation & Community Admin
# ═══════════════════════════════════════════════════════


@router.get("/moderation/queue")
async def moderation_queue(
    status: str = Query("review", pattern="^(review|pending|flagged|approved|rejected)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    ph = db._ph
    offset = (page - 1) * limit
    statuses = ["pending", "flagged"] if status == "review" else [status]
    placeholders = ", ".join([ph] * len(statuses))
    def _query():
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT p.*, u.display_name, u.phone,
                       e.name as entity_name
                FROM posts p
                JOIN users u ON u.id = p.user_id
                LEFT JOIN entities e ON e.id = p.entity_id
                WHERE p.moderation_status IN ({placeholders})
                ORDER BY p.created_at DESC
                LIMIT {ph} OFFSET {ph}
            """, (*statuses, limit, offset))
            total = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM posts WHERE moderation_status IN ({placeholders})
            """, (*statuses,))
        return {
            "posts": [_mod_post(db._row_to_dict(r)) for r in rows],
            "total": total["c"] if total else 0,
            "page": page,
        }
    return await asyncio.to_thread(_query)


@router.post("/moderation/{post_id}/approve")
async def approve_post(post_id: str):
    post_id = validate_path_id(post_id, "post_id")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            db._execute(conn, f"""
                UPDATE posts SET moderation_status = 'approved' WHERE id::text = {ph}
            """, (post_id,))
        _log_mod_action("post", post_id, "approved")
    await asyncio.to_thread(_query)
    return {"success": True}


class RejectBody(BaseModel):
    reason: str | None = None


@router.post("/moderation/{post_id}/reject")
async def reject_post(post_id: str, body: RejectBody = RejectBody()):
    post_id = validate_path_id(post_id, "post_id")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            db._execute(conn, f"""
                UPDATE posts SET moderation_status = 'rejected' WHERE id::text = {ph}
            """, (post_id,))
        _log_mod_action("post", post_id, "rejected", (body.reason or "").strip() or None)
    await asyncio.to_thread(_query)
    return {"success": True}


class BatchModerationBody(BaseModel):
    post_ids: list[str] = Field(..., min_length=1, max_length=100)
    action: str  # 'approve' or 'reject'
    reason: str = Field("", max_length=500)


@router.post("/moderation/batch")
async def batch_moderation(body: BatchModerationBody):
    if body.action not in ("approve", "reject"):
        raise HTTPException(400, "action must be 'approve' or 'reject'")
    if not body.post_ids or len(body.post_ids) > 100:
        raise HTTPException(400, "post_ids: 1-100 items")
    status = "approved" if body.action == "approve" else "rejected"
    def _query():
        ph = db._ph
        placeholders = ", ".join(ph for _ in body.post_ids)
        params = [status] + list(body.post_ids)
        with db._conn() as conn:
            db._execute(conn, f"UPDATE posts SET moderation_status = {ph} WHERE id::text IN ({placeholders})", tuple(params))
        for pid in body.post_ids:
            _log_mod_action("post", pid, status, body.reason.strip() or None)
    await asyncio.to_thread(_query)
    return {"success": True, "updated": len(body.post_ids)}


class ModNoteBody(BaseModel):
    note: str = Field(..., min_length=1, max_length=500)


@router.post("/moderation/{post_id}/note")
async def add_moderation_note(post_id: str, body: ModNoteBody):
    """B3d: Add internal admin note (not visible to poster)."""
    post_id = validate_path_id(post_id, "post_id")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            post = db._fetchone(conn, f"SELECT id FROM posts WHERE id::text = {ph}", (post_id,))
            if not post:
                raise HTTPException(404, "Post not found")
            db._execute(conn, f"""
                UPDATE posts SET moderation_notes = COALESCE(moderation_notes, '[]'::jsonb) || {ph}::jsonb
                WHERE id::text = {ph}
            """, (json.dumps({"text": body.note, "at": datetime.now().isoformat()}), post_id))
    await asyncio.to_thread(_query)
    return {"success": True}


@router.get("/moderation/{post_id}/notes")
async def get_moderation_notes(post_id: str):
    post_id = validate_path_id(post_id, "post_id")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            row = db._fetchone(conn, f"SELECT moderation_notes FROM posts WHERE id::text = {ph}", (post_id,))
        if not row:
            raise HTTPException(404, "Post not found")
        notes = db._row_to_dict(row).get("moderation_notes") or []
        return {"notes": notes}
    return await asyncio.to_thread(_query)


@router.get("/moderation/stats")
async def moderation_stats():
    def _query():
        with db._conn() as conn:
            rows = db._fetchall(conn, """
                SELECT moderation_status, COUNT(*) as c FROM posts GROUP BY moderation_status
            """, ())
        return {"counts": {r["moderation_status"]: r["c"] for r in [db._row_to_dict(row) for row in rows]}}
    return await asyncio.to_thread(_query)


@router.get("/analytics-overview")
async def analytics_overview(days: int = Query(0, ge=0, le=365)):
    """GĐ9.6: gói số liệu cho trang admin Analytics (1 call, đã auth qua require_admin).

    - popular: user hỏi gì nhiều · gaps: câu bot bí (backlog nội dung) · costs: chi phí LLM.
    - days: 0 = tất cả, 7/30/90 = lọc theo khoảng thời gian.
    """
    since = None
    if days > 0:
        since = (datetime.now() - timedelta(days=days)).isoformat()
    def _query():
        return {
            "summary": _safe(lambda: analytics.get_summary(since=since), {}),
            "popular": _safe(lambda: analytics.get_popular_queries(20, since=since), []),
            "gaps": _safe(lambda: analytics.get_knowledge_gaps(20, since=since), []),
            "top_entities": _safe(lambda: analytics.get_top_entities(15), []),
            "costs": _safe(_get_cost_report, {}) if _HAS_COST else {"available": False},
            "daily": _safe(lambda: analytics.get_daily_stats(days or 30), []),
        }
    return await asyncio.to_thread(_query)


@router.get("/reports")
async def get_reports(
    status: str = Query("pending", pattern="^(pending|resolved|dismissed)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    ph = db._ph
    offset = (page - 1) * limit
    def _query():
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT r.*, u.display_name as reporter_name
                FROM reports r
                JOIN users u ON u.id = r.reporter_id
                WHERE r.status = {ph}
                ORDER BY r.created_at DESC
                LIMIT {ph} OFFSET {ph}
            """, (status, limit, offset))
            total = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM reports WHERE status = {ph}
            """, (status,))
        return {
            "reports": [db._row_to_dict(r) for r in rows],
            "total": total["c"] if total else 0,
        }
    return await asyncio.to_thread(_query)


class BulkReportAction(BaseModel):
    ids: list[str] = Field(..., min_length=1, max_length=100)
    action: str = Field(..., pattern="^(resolve|dismiss)$")


@router.post("/reports/bulk")
async def bulk_report_action(body: BulkReportAction):
    status = "resolved" if body.action == "resolve" else "dismissed"
    def _query():
        ph = db._ph
        placeholders = ",".join([ph] * len(body.ids))
        with db._conn() as conn:
            db._execute(conn, f"UPDATE reports SET status = {ph} WHERE id::text IN ({placeholders})",
                        (status, *body.ids))
    await asyncio.to_thread(_query)
    return {"success": True, "updated": len(body.ids)}


@router.post("/reports/{report_id}/resolve")
async def resolve_report(report_id: str):
    report_id = validate_path_id(report_id, "report_id")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            db._execute(conn, f"""
                UPDATE reports SET status = 'resolved' WHERE id::text = {ph}
            """, (report_id,))
    await asyncio.to_thread(_query)
    return {"success": True}


@router.post("/reports/{report_id}/dismiss")
async def dismiss_report(report_id: str):
    report_id = validate_path_id(report_id, "report_id")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            db._execute(conn, f"""
                UPDATE reports SET status = 'dismissed' WHERE id::text = {ph}
            """, (report_id,))
    await asyncio.to_thread(_query)
    return {"success": True}


# GĐ13.6f: báo-sai thông tin (facility/entity) & báo nội dung ẩn danh — kênh nhẹ JSONL
# (KHÔNG cần đăng nhập, không DB), tách khỏi UGC `reports` (Postgres) ở trên.
_INFO_REPORTS_FILE = Path(__file__).resolve().parent / "data" / "reports.jsonl"


@router.get("/info-reports")
async def get_info_reports(limit: int = Query(100, ge=1, le=500)):
    """Liệt kê báo-sai/báo cáo ẩn danh (reports.jsonl), mới nhất trước. Admin tự xử lý
    (sửa entity qua editor / takedown thủ công)."""
    def _query():
        if not _INFO_REPORTS_FILE.exists():
            return {"reports": [], "total": 0}
        items = []
        with open(_INFO_REPORTS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        items.reverse()
        open_count = sum(1 for r in items if r.get("status", "open") == "open")
        return {"reports": items[:limit], "total": len(items), "open": open_count}
    return await asyncio.to_thread(_query)


_audit_cache: dict = {"mtime": 0.0, "items": []}

@router.get("/audit-log")
async def get_audit_log(
    limit: int = Query(200, ge=1, le=5000),
    method: Optional[str] = None,
    q: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    """P2-7: nhật ký thao tác admin (mutation), mới nhất trước. Hỗ trợ filter server-side."""
    def _query():
        if not _AUDIT_FILE.exists():
            return {"entries": [], "total": 0}
        try:
            mtime = _AUDIT_FILE.stat().st_mtime
        except OSError:
            mtime = 0.0
        if mtime != _audit_cache["mtime"]:
            items = []
            with open(_AUDIT_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        items.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            _audit_cache["mtime"] = mtime
            _audit_cache["items"] = items
        items = _audit_cache["items"]
        filtered = items
        if method:
            filtered = [e for e in filtered if e.get("method") == method.upper()]
        if q:
            q_lower = q.lower()
            filtered = [e for e in filtered if q_lower in (e.get("path") or "").lower() or q_lower in (e.get("actor") or "").lower()]
        if date_from:
            filtered = [e for e in filtered if (e.get("ts") or "")[:10] >= date_from]
        if date_to:
            filtered = [e for e in filtered if (e.get("ts") or "")[:10] <= date_to]
        total = len(filtered)
        return {"entries": list(reversed(filtered[-limit:])), "total": total}
    return await asyncio.to_thread(_query)


class ReportActionRequest(BaseModel):
    ts: str = Field(..., min_length=1, max_length=64)   # khóa theo timestamp ISO (ổn định)
    status: str = Field(..., pattern="^(open|resolved|dismissed)$")


@router.post("/info-reports/action")
async def info_report_action(body: ReportActionRequest):
    """Đổi trạng thái 1 báo-sai (resolve/dismiss/open) — ghi lại reports.jsonl atomic."""
    def _query():
        if not _INFO_REPORTS_FILE.exists():
            raise HTTPException(404, "Không có báo cáo")
        records, found = [], False
        for line in _INFO_REPORTS_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("ts") == body.ts:
                r["status"] = body.status
                found = True
            records.append(r)
        if not found:
            raise HTTPException(404, f"Không tìm thấy báo cáo ts={body.ts}")
        tmp = _INFO_REPORTS_FILE.with_suffix(".tmp")
        tmp.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n", encoding="utf-8")
        tmp.replace(_INFO_REPORTS_FILE)
    await asyncio.to_thread(_query)
    return {"status": "ok", "ts": body.ts, "new_status": body.status}


@router.get("/cost-overview")
async def cost_overview():
    """Bảng chi phí: chi phí LLM (cost_tracker) + ngân sách agent tự động (cap/dùng/còn).
    Bảo vệ ngân sách <1tr/tháng khi autonomous-LLM được bật."""
    def _query():
        out: dict = {"llm": {"available": False}, "agent_budget": {"enabled": False}}
        try:
            import autonomous_budget as ab
            out["agent_budget"] = ab.status()
        except Exception:
            pass
        try:
            from cost_tracker import cost_attribution
            s = cost_attribution.get_summary()
            out["llm"] = {
                "available": True,
                "total_cost_usd": s.get("total_cost", 0),
                "total_calls": s.get("count", s.get("total_calls", 0)),
                "daily": cost_attribution.get_daily_costs(7),
            }
        except Exception:
            pass
        return out
    return await asyncio.to_thread(_query)


@router.post("/ai/triage")
async def ai_triage():
    """On-demand: trợ lý LLM gợi ý ≤3 việc quản trị ưu tiên từ tình hình hiện tại.
    Chỉ chạy KHI admin bấm (1 lần gọi LLM — KHÔNG vòng lặp nền, tôn trọng §B8).
    Trả context thô nếu LLM không khả dụng (degrade an toàn)."""
    def _query():
        ctx = []
        reports = []
        try:
            if _INFO_REPORTS_FILE.exists():
                for ln in _INFO_REPORTS_FILE.read_text(encoding="utf-8").splitlines():
                    if ln.strip():
                        reports.append(json.loads(ln))
        except Exception:
            pass
        ctx.append(f"- Báo cáo sai thông tin: {len(reports)}")
        for r in reports[-5:]:
            ctx.append(f"    · [{r.get('target_type')}] {r.get('target_id')}: {str(r.get('reason', ''))[:60]}")
        raw = "\n".join(ctx) or "(không có dữ liệu)"

        try:
            from server import client, MODEL_MINI
            resp = client.chat.completions.create(
                model=MODEL_MINI, temperature=0.3, max_tokens=400,
                messages=[
                    {"role": "system", "content": "Bạn là trợ lý quản trị của vinhlong360. Dựa trên tình hình, đề xuất TỐI ĐA 3 việc ưu tiên xử lý, ngắn gọn, tiếng Việt, có thứ tự."},
                    {"role": "user", "content": f"Tình hình hiện tại:\n{raw}\n\nĐề xuất việc ưu tiên:"},
                ])
            return {"ok": True, "suggestion": resp.choices[0].message.content, "context": raw}
        except Exception as e:  # noqa: BLE001 - LLM down/budget → vẫn trả context để admin tự xử
            return {"ok": False, "suggestion": None, "context": raw,
                    "note": "LLM không khả dụng — xem tình hình thô bên dưới.", "detail": str(e)[:120]}
    return await asyncio.to_thread(_query)


@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: str = Query("", max_length=100),
):
    ph = db._ph
    offset = (page - 1) * limit
    conditions = ["1=1"]
    params = []
    if search:
        conditions.append(f"(display_name ILIKE {ph} OR phone LIKE {ph})")
        params.extend([f"%{search}%", f"%{search}%"])
    where = " AND ".join(conditions)
    params.extend([limit, offset])
    def _query():
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT id, phone, display_name, role, is_active, created_at
                FROM users WHERE {where}
                ORDER BY created_at DESC
                LIMIT {ph} OFFSET {ph}
            """, params)
            total = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM users WHERE {where}
            """, params[:len(params) - 2])
        role_counts = {}
        try:
            with db._conn() as conn2:
                rc_rows = db._fetchall(conn2, "SELECT COALESCE(role, 'user') as role, COUNT(*) as c FROM users GROUP BY COALESCE(role, 'user')", ())
            for rc in rc_rows:
                d = db._row_to_dict(rc)
                role_counts[d["role"]] = d["c"]
        except Exception:
            pass
        return {
            "users": [{
                "id": str(r["id"]),
                "phone": _mask(r.get("phone", "")),
                "display_name": r.get("display_name", ""),
                "role": r.get("role", "user"),
                "is_active": r.get("is_active", True),
                "created_at": str(r.get("created_at", "")),
            } for r in [db._row_to_dict(row) for row in rows]],
            "total": total["c"] if total else 0,
            "role_counts": role_counts,
        }
    return await asyncio.to_thread(_query)


@router.post("/users/{user_id}/ban")
async def ban_user(user_id: str):
    user_id = validate_path_id(user_id, "user_id")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            db._execute(conn, f"""
                UPDATE users SET is_active = FALSE WHERE id::text = {ph}
            """, (user_id,))
    await asyncio.to_thread(_query)
    return {"success": True}


@router.post("/users/{user_id}/unban")
async def unban_user(user_id: str):
    user_id = validate_path_id(user_id, "user_id")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            db._execute(conn, f"""
                UPDATE users SET is_active = TRUE WHERE id::text = {ph}
            """, (user_id,))
    await asyncio.to_thread(_query)
    return {"success": True}


@router.post("/users/{user_id}/role")
async def set_user_role(user_id: str, role: str = Query(..., pattern="^(user|moderator|admin)$")):
    user_id = validate_path_id(user_id, "user_id")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            db._execute(conn, f"""
                UPDATE users SET role = {ph} WHERE id::text = {ph}
            """, (role, user_id))
    await asyncio.to_thread(_query)
    return {"success": True}


def _mod_post(row: dict) -> dict:
    images = row.get("images", [])
    if isinstance(images, str):
        try:
            images = json.loads(images)
        except Exception:
            images = []
    return {
        "id": str(row["id"]),
        "content": row.get("content", "")[:2000],
        "post_type": row.get("post_type", "share"),
        "moderation_status": row.get("moderation_status", "pending"),
        "images": images,
        "author": row.get("display_name", ""),
        "display_name": row.get("display_name", ""),
        "phone": _mask(row.get("phone", "")),
        "entity_name": row.get("entity_name"),
        "created_at": str(row.get("created_at", "")),
        "moderation_notes": row.get("moderation_notes") or [],
    }


def _mask(phone: str) -> str:
    if not phone or len(phone) < 6:
        return phone or ""
    return phone[:3] + "****" + phone[-3:]


def _log_mod_action(target_type, target_id, action, reason=None):
    try:
        from moderation import log_moderation
        log_moderation(target_type, target_id, action, {"reason": reason} if reason else {}, auto=False)
    except Exception:
        pass


# ══════════════════════════════════════════════════
#  SITE SETTINGS — CMS admin endpoints
# ══════════════════════════════════════════════════

@router.get("/site-settings")
async def admin_get_all_settings():
    """All settings grouped by category (for admin overview)."""
    if not db._use_pg:
        raise HTTPException(503, detail="Site settings require PostgreSQL")
    return await asyncio.to_thread(site_settings.get_all_grouped)


@router.get("/site-settings/{category}")
async def admin_get_settings_by_category(category: str):
    """Settings for a specific category (for admin editor page)."""
    if not db._use_pg:
        raise HTTPException(503, detail="Site settings require PostgreSQL")
    def _query():
        items = site_settings.get_by_category(category)
        if not items:
            raise HTTPException(404, detail=f"No settings found for category '{category}'")
        return {"category": category, "settings": items}
    return await asyncio.to_thread(_query)


class SettingUpdate(BaseModel):
    value: object = Field(..., description="New value for the setting")


@router.put("/site-settings/{key:path}")
async def admin_update_setting(key: str, body: SettingUpdate):
    """Update a single setting value."""
    if not db._use_pg:
        raise HTTPException(503, detail="Site settings require PostgreSQL")
    def _query():
        ok = site_settings.upsert(key, body.value)
        if not ok:
            raise HTTPException(500, detail="Failed to update setting")
    await asyncio.to_thread(_query)
    return {"success": True, "key": key}


class BulkSettingUpdate(BaseModel):
    updates: dict[str, object] = Field(..., description="Map of key→value to update")


@router.post("/site-settings/bulk")
async def admin_bulk_update_settings(body: BulkSettingUpdate):
    """Batch update multiple settings at once."""
    if not db._use_pg:
        raise HTTPException(503, detail="Site settings require PostgreSQL")
    count = await asyncio.to_thread(site_settings.bulk_upsert, body.updates)
    return {"success": True, "updated": count}


@router.post("/site-settings/reset/{category}")
async def admin_reset_category(category: str):
    """Reset all settings in a category to their defaults."""
    if not db._use_pg:
        raise HTTPException(503, detail="Site settings require PostgreSQL")
    def _query():
        from seed_site_settings import DEFAULTS
        return site_settings.reset_category(category, DEFAULTS)
    count = await asyncio.to_thread(_query)
    return {"success": True, "reset": count}


@router.post("/notifications/cleanup")
async def admin_cleanup_notifications(days: int = Query(90, ge=7, le=365)):
    """Delete read notifications older than N days."""
    if not db._use_pg:
        raise HTTPException(503, detail="Notifications require PostgreSQL")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            cur = db._execute(conn, f"""
                DELETE FROM notifications
                WHERE is_read = TRUE
                  AND created_at < NOW() - MAKE_INTERVAL(days => {ph})
            """, (days,))
            return cur.rowcount if cur else 0
    deleted = await asyncio.to_thread(_query)
    return {"success": True, "deleted": deleted, "days": days}
