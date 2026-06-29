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
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request, Depends, UploadFile, File
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field, field_validator

import data_quality
import knowledge
import analytics

logger = logging.getLogger("admin")
import site_settings
from database import db, escape_like as _escape_like

try:
    from cost_tracker import get_cost_report as _get_cost_report
    _HAS_COST = True
except Exception:  # noqa: BLE001
    logger.warning("Cost tracker unavailable", exc_info=True)
    _HAS_COST = False
from auth_middleware import get_current_user, validate_path_id, require_csrf
from middleware import admin_limiter, verify_admin_key, get_client_ip


def _sync_kb():
    """GĐ3.6: write-through — sau khi ghi DB, nạp lại knowledge để chat/tool thấy ngay.

    Bọc try/except: lỗi reload không được làm hỏng thao tác admin đã commit.
    Also invalidates LLM response cache to prevent stale chat answers.
    """
    try:
        knowledge.reload()
    except Exception:
        logger.exception("Knowledge reload failed after admin write — chat may serve stale data")
    try:
        import cache
        cache.invalidate_all()
    except Exception:
        logger.warning("LLM cache invalidation failed after KB sync")


def _safe(fn, default):
    try:
        return fn()
    except Exception:
        logger.debug("_safe(%s) failed, returning default", getattr(fn, "__name__", fn), exc_info=True)
        return default

# ── Auth dependency ──

_AUDIT_FILE = Path(__file__).resolve().parent / "data" / "admin_audit.jsonl"
_audit_lock = threading.Lock()


from config import settings as _cfg
_AUDIT_MAX_LINES = _cfg.AUDIT_MAX_LINES


def _log_admin_audit(actor: str, method: str, path: str, ip: str) -> None:
    """P2-7: ghi nhật ký thao tác admin (ai/làm-gì/khi-nào) — JSONL nhẹ, không chặn request."""
    try:
        with _audit_lock:
            _AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
            rec = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "actor": actor,
                   "method": method, "path": path, "ip": ip}
            with open(_AUDIT_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            _audit_cache["mtime"] = 0.0
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
        archive = _AUDIT_FILE.with_suffix(f".{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.jsonl")
        archive.write_text("\n".join(lines[:-_AUDIT_MAX_LINES]) + "\n", encoding="utf-8")
        tmp = _AUDIT_FILE.with_suffix(".tmp")
        tmp.write_text("\n".join(lines[-_AUDIT_MAX_LINES:]) + "\n", encoding="utf-8")
        tmp.replace(_AUDIT_FILE)
    except Exception:
        logger.exception("Audit log rotation failed")


async def require_admin(request: Request):
    """FastAPI dependency: verify admin auth + rate limit (+ audit log mọi mutation)."""
    # Rate limit
    client_ip = get_client_ip(request)
    allowed, rate_info = admin_limiter.is_allowed(client_ip)
    if not allowed:
        raise HTTPException(429, detail="Quá nhiều yêu cầu. Vui lòng thử lại sau.", headers={"Retry-After": str(rate_info["retry_after"])})
    # Auth: allow server-side admin key or a logged-in admin user from the frontend.
    actor = None
    if verify_admin_key(request):
        actor = "admin-key"
    else:
        user = await get_current_user(request)
        if user and user.get("role") == "admin":
            actor = f"user:{user.get('id')}"
    if not actor:
        raise HTTPException(401, detail="Xác thực admin không hợp lệ. Sử dụng X-Admin-Key hoặc phiên làm việc admin.")
    # P2-7: audit các thao tác THAY ĐỔI (đọc/GET không log để tránh nhiễu)
    if request.method in ("POST", "PUT", "DELETE", "PATCH"):
        _log_admin_audit(actor, request.method, request.url.path, client_ip)

ROOT = Path(__file__).resolve().parent.parent

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin), Depends(require_csrf)])


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
    images: list[str] | None = Field(None, max_length=50)

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
    images: list[str] = Field(default=[], max_length=50)
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
    candidate_ids: list[str] | None = Field(None, max_length=500)
    dry_run: bool = True

@router.get("/entities")
async def list_entities(
    type: Optional[str] = Query(None, max_length=50),
    area: Optional[str] = Query(None, max_length=100),
    q: Optional[str] = Query(None, max_length=200),
    include_places: bool = False,
    orphans_only: bool = False,
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0, le=10000),
):
    """Danh sách entities với filter — đọc từ database."""
    def _query():
        if q or orphans_only:
            all_matches = db.search_entities(q=q, entity_type=type, area=area, limit=10000, offset=0) if q else db.list_entities(entity_type=type, area=area, limit=10000, offset=0)
        else:
            all_matches = None
            results = db.list_entities(entity_type=type, area=area, limit=limit, offset=offset)

        if include_places:
            with db._conn() as conn:
                place_rows = db._fetchall(conn, "SELECT * FROM entities WHERE type = 'place' ORDER BY name LIMIT 1000", ())
            places = [db._parse_entity(r) for r in place_rows]
            if all_matches is not None:
                all_matches = all_matches + places
            else:
                results = results + places

        if orphans_only:
            with db._conn() as conn:
                rows = db._fetchall(conn,
                    "SELECT from_id AS eid FROM relationships UNION SELECT to_id FROM relationships", ())
                rel_ids = {db._row_to_dict(r)["eid"] for r in rows}
            if all_matches is not None:
                all_matches = [e for e in all_matches if e.get("type") != "place" and e["id"] not in rel_ids]

        if all_matches is not None:
            total = len(all_matches)
            items = all_matches[offset:offset + limit]
        else:
            total = db.count_entities_filtered(entity_type=type, area=area)
            items = results

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
            rows = db._fetchall(conn, "SELECT id, name, area, level FROM entities WHERE type = 'place' ORDER BY name LIMIT 500")
        return [db._row_to_dict(r) for r in rows]
    return await asyncio.to_thread(_query)


@router.get("/entities/check-duplicate")
async def check_duplicate(name: str = Query(..., min_length=2)):
    """Kiểm tra entity trùng tên (substring match, case-insensitive)."""
    name_lower = name.lower().strip()
    if len(name_lower) < 2:
        return {"duplicates": []}
    pattern = f"%{db.escape_like(name_lower)}%"
    def _query():
        with db._conn() as conn:
            rows = db._fetchall(conn,
                "SELECT id, name, type FROM entities WHERE type != 'place' AND LOWER(name) LIKE ? ESCAPE '\\' LIMIT 5",
                (pattern,))
        dups = []
        for r in rows:
            d = db._row_to_dict(r)
            dups.append({"id": d["id"], "name": d["name"], "type": d.get("type", "")})
        return {"duplicates": dups}
    return await asyncio.to_thread(_query)


@router.get("/entities/{entity_id}")
async def get_entity(entity_id: str):
    """Chi tiết 1 entity."""
    entity_id = validate_path_id(entity_id, "entity_id")
    def _query():
        entity = db.get_entity(entity_id)
        if not entity:
            raise HTTPException(404, "Entity không tồn tại")
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
            raise HTTPException(404, "Entity không tồn tại")
        old_snapshot = {k: v for k, v in existing.items()}
        updates = update.model_dump(exclude_none=True)
        existing.update(updates)
        existing["updatedAt"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
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


@router.post("/entities", status_code=201)
async def create_entity(entity: EntityCreate):
    """Tạo entity mới."""
    def _query():
        if db.get_entity(entity.id):
            raise HTTPException(409, "Entity đã tồn tại")
        payload = entity.model_dump()
        src = payload.pop("source", None) or {"title": "admin", "method": "manual"}
        new_entity = {
            **payload,
            "source": src,
            "updatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
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
            raise HTTPException(404, "Entity không tồn tại")
        db.delete_entity(entity_id)
        _sync_kb()
        from public_api import invalidate_entity_cache, invalidate_place_cache
        invalidate_entity_cache(entity_id)
        if entity.get("type") == "place":
            invalidate_place_cache()
    await asyncio.to_thread(_query)
    return {"success": True, "entity_id": entity_id}


class _EntityImageURL(BaseModel):
    url: str = Field(..., max_length=600)


@router.post("/entities/{entity_id}/images")
async def add_entity_image_url(entity_id: str, body: _EntityImageURL):
    """GĐ8.4: thêm ảnh entity theo URL (chỉ nguồn cấp phép — B6)."""
    entity_id = validate_path_id(entity_id, "entity_id")
    url = (body.url or "").strip()
    if url.startswith("/"):
        pass
    else:
        _assert_public_url(url)
    def _query():
        entity = db.get_entity(entity_id)
        if not entity:
            raise HTTPException(404, "Entity không tồn tại")
        images = list(entity.get("images") or [])
        if len(images) >= 10:
            raise HTTPException(400, "Tối đa 10 ảnh mỗi entity")
        if url not in images:
            images.append(url)
        entity["images"] = images
        entity["updatedAt"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
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
        raise HTTPException(404, "Entity không tồn tại")
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
    entity["updatedAt"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
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
            raise HTTPException(404, "Entity không tồn tại")
        images = list(entity.get("images") or [])
        if not (0 <= idx < len(images)):
            raise HTTPException(400, f"Chỉ số ảnh không hợp lệ (0–{len(images) - 1})")
        images.pop(idx)
        entity["images"] = images
        entity["updatedAt"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        db.upsert_entity(entity)
        _sync_kb()
        return {"status": "removed", "images": images}
    return await asyncio.to_thread(_query)


@router.get("/unclassified")
async def list_unclassified(limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0, le=10000),
                            q: Optional[str] = Query(None, max_length=200)):
    """Entity nội dung CHƯA gán xã/phường (placeId rỗng) — để admin gán đúng (lấp nợ placeId)."""
    ql = (q or "").lower().strip()
    base = "FROM entities WHERE type != 'place' AND (placeId IS NULL OR placeId = '')"
    params: list = []
    if ql:
        base += " AND LOWER(name) LIKE ? ESCAPE '\\'"
        params.append(f"%{db.escape_like(ql)}%")
    def _query():
        with db._conn() as conn:
            cnt = db._fetchone(conn, f"SELECT COUNT(*) as c {base}", tuple(params))
            total = db._row_to_dict(cnt)["c"] if cnt else 0
            rows = db._fetchall(conn, f"SELECT id, name, type, area, summary {base} ORDER BY name LIMIT ? OFFSET ?",
                                tuple(params) + (limit, offset))
        out = []
        for r in rows:
            d = db._row_to_dict(r)
            out.append({"id": d["id"], "name": d.get("name"), "type": d.get("type"),
                         "area": d.get("area"), "summary": (d.get("summary") or "")[:100]})
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
            raise HTTPException(404, "Entity không tồn tại")
        pid = body.place_id or None
        if pid:
            p = db.get_entity(pid)
            if not p or p.get("type") != "place":
                raise HTTPException(400, "place_id không phải xã/phường hợp lệ")
            e["area"] = p.get("area") or e.get("area")
        e["placeId"] = pid
        e["updatedAt"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        db.upsert_entity(e)
        _sync_kb()
        return {"success": True, "id": entity_id, "placeId": pid}
    return await asyncio.to_thread(_query)


# ── Itinerary CRUD ──

@router.get("/itineraries")
async def list_itineraries_admin(area: Optional[str] = Query(None, max_length=100)):
    return await asyncio.to_thread(db.list_itineraries, area=area)

@router.get("/itineraries/{itin_id}")
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
    description: str | None = Field(None, max_length=2000)
    days: list | None = Field(None, max_length=30)
    area: str | None = Field(None, max_length=100)
    tags: list[str] | None = Field(None, max_length=50)

class ItineraryUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=300)
    description: str | None = Field(None, max_length=2000)
    days: list | None = Field(None, max_length=30)
    area: str | None = Field(None, max_length=100)
    tags: list[str] | None = Field(None, max_length=50)

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


@router.post("/itineraries", status_code=201)
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
            cur = db._execute(conn, f"DELETE FROM itineraries WHERE id = {ph}", (itin_id,))
            if cur.rowcount == 0:
                raise HTTPException(404, "Lộ trình không tồn tại")
    await asyncio.to_thread(_query)
    return {"success": True, "id": itin_id}


# ── Relationship CRUD ──

@router.post("/relationships")
async def add_relationship(body: RelationshipCreate):
    validate_path_id(body.from_id, "from_id")
    validate_path_id(body.to_id, "to_id")
    await asyncio.to_thread(db.add_relationship, body.from_id, body.to_id, body.type)
    return {"status": "created"}

@router.delete("/relationships")
async def delete_relationship(from_id: str, to_id: str, type: str = Query(..., max_length=100)):
    validate_path_id(from_id, "from_id")
    validate_path_id(to_id, "to_id")
    def _query():
        db.initialize()
        ph = db._ph
        with db._conn() as conn:
            cur = db._execute(conn, f"DELETE FROM relationships WHERE from_id={ph} AND to_id={ph} AND type={ph}",
                              (from_id, to_id, type))
            if cur.rowcount == 0:
                raise HTTPException(404, "Mối quan hệ không tồn tại")
    await asyncio.to_thread(_query)
    return {"success": True}


@router.post("/relationships/bulk")
async def add_relationships_bulk(body: RelationshipBulkCreate):
    """B7b: thêm nhiều quan hệ cùng lúc."""
    validate_path_id(body.from_id, "from_id")
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
                logger.warning("Bulk relationship add failed for %s→%s: %s", body.from_id, to_id, e)
                errors.append({"to_id": to_id, "error": "Không thể thêm quan hệ"})
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
    offset: int = Query(0, ge=0, le=10000),
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
    validate_path_id(batch_id, "batch_id")
    def _query():
        try:
            result = data_quality.rollback_apply(batch_id)
        except ValueError:
            raise HTTPException(400, detail="Batch ID không hợp lệ")
        except FileNotFoundError:
            raise HTTPException(404, detail="Không tìm thấy batch")
        _sync_kb()
        return result
    return await asyncio.to_thread(_query)

# ── Stale content queue (U-17) ──

_STALE_QUEUE_MISSING_FIELDS = {"source", "images", "coordinates", "phone", "summary"}
_STALE_THRESHOLD_DEFAULT = 180


@router.get("/stale-queue")
async def stale_queue(
    threshold_days: int = Query(_STALE_THRESHOLD_DEFAULT, ge=30, le=730),
    missing_field: Optional[str] = Query(None, pattern="^(source|images|coordinates|phone|summary)$"),
    entity_type: Optional[str] = Query(None, max_length=50),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0, le=10000),
):
    """Danh sách entity cũ/thiếu thông tin — admin review queue."""
    def _query():
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=threshold_days)
        entities = knowledge._entities if hasattr(knowledge, "_entities") else {}
        results = []
        for eid, e in entities.items():
            if e.get("type") == "place":
                continue
            if entity_type and e.get("type") != entity_type:
                continue
            updated = e.get("updatedAt") or e.get("created_at")
            days_since = None
            if updated:
                try:
                    dt = datetime.fromisoformat(str(updated).replace("Z", "+00:00"))
                    days_since = (now - dt).days
                except (ValueError, TypeError):
                    days_since = 9999
            else:
                days_since = 9999
            is_stale = days_since >= threshold_days
            attrs = e.get("attributes") or {}
            missing = []
            if not e.get("source"):
                missing.append("source")
            if not e.get("images"):
                missing.append("images")
            if not e.get("coordinates"):
                missing.append("coordinates")
            if not attrs.get("phone"):
                missing.append("phone")
            if not e.get("summary"):
                missing.append("summary")
            if missing_field and missing_field not in missing:
                continue
            if not is_stale and not missing:
                continue
            results.append({
                "id": eid,
                "name": e.get("name"),
                "type": e.get("type"),
                "area": e.get("area"),
                "days_since_update": days_since,
                "is_stale": is_stale,
                "missing_fields": missing,
                "stale_reviewed_at": attrs.get("stale_reviewed_at"),
            })
        results.sort(key=lambda x: -(x["days_since_update"] or 0))
        total = len(results)
        return {"items": results[offset:offset + limit], "total": total}
    return await asyncio.to_thread(_query)


@router.post("/stale-queue/{entity_id}/mark-reviewed")
async def stale_mark_reviewed(entity_id: str):
    """Đánh dấu entity đã được admin xem xét — ghi timestamp vào attributes."""
    validate_path_id(entity_id, "entity_id")
    def _query():
        e = db.get_entity(entity_id)
        if not e:
            raise HTTPException(404, detail="Entity không tồn tại")
        attrs = e.get("attributes") or {}
        attrs["stale_reviewed_at"] = datetime.now(timezone.utc).isoformat()
        db.update_entity(entity_id, {"attributes": attrs})
        return {"ok": True, "entity_id": entity_id, "stale_reviewed_at": attrs["stale_reviewed_at"]}
    return await asyncio.to_thread(_query)


# ── Completeness standalone (BE-10) ──


@router.get("/completeness")
async def completeness_overview():
    """Tổng quan hoàn thiện: % entities có source+images+placeId+summary."""
    def _query():
        entities = knowledge._entities if hasattr(knowledge, "_entities") else {}
        total = 0
        has_source = 0
        has_images = 0
        has_place = 0
        has_summary = 0
        for e in entities.values():
            if e.get("type") == "place":
                continue
            total += 1
            q = data_quality.entity_quality(e)
            if q["has_source"]:
                has_source += 1
            if e.get("images"):
                has_images += 1
            if q["has_place"]:
                has_place += 1
            if e.get("summary"):
                has_summary += 1
        pct = lambda n: round(n / total * 100, 1) if total else 0
        return {
            "total_entities": total,
            "source": {"count": has_source, "pct": pct(has_source)},
            "images": {"count": has_images, "pct": pct(has_images)},
            "place_id": {"count": has_place, "pct": pct(has_place)},
            "summary": {"count": has_summary, "pct": pct(has_summary)},
            "overall_pct": pct(has_source + has_images + has_place + has_summary) / 4 * total if total else 0,
        }
    return await asyncio.to_thread(_query)


@router.get("/completeness/details")
async def completeness_details(
    missing: Optional[str] = Query(None, pattern="^(source|images|place|summary)$"),
    entity_type: Optional[str] = Query(None, max_length=50),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0, le=10000),
):
    """Per-entity completeness scores with filter."""
    def _query():
        entities = knowledge._entities if hasattr(knowledge, "_entities") else {}
        results = []
        for eid, e in entities.items():
            if e.get("type") == "place":
                continue
            if entity_type and e.get("type") != entity_type:
                continue
            q = data_quality.entity_quality(e)
            has_imgs = bool(e.get("images"))
            has_summ = bool(e.get("summary"))
            if missing == "source" and q["has_source"]:
                continue
            elif missing == "images" and has_imgs:
                continue
            elif missing == "place" and q["has_place"]:
                continue
            elif missing == "summary" and has_summ:
                continue
            results.append({
                "id": eid,
                "name": e.get("name"),
                "type": e.get("type"),
                "score": q["score"],
                "has_source": q["has_source"],
                "has_images": has_imgs,
                "has_place": q["has_place"],
                "has_summary": has_summ,
                "missing": q["missing"] + ([] if has_imgs else ["images"]) + ([] if has_summ else ["summary"]),
            })
        results.sort(key=lambda x: x["score"])
        total = len(results)
        return {"items": results[offset:offset + limit], "total": total}
    return await asyncio.to_thread(_query)


# ── Q&A quality queue (U-24) ──


@router.get("/qa-queue")
async def qa_queue(
    filter: Optional[str] = Query(None, pattern="^(unanswered|no_best_answer)$"),
    entity_id: Optional[str] = Query(None, max_length=100),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0, le=10000),
):
    """Admin queue: questions chưa có best answer hoặc chưa có reply."""
    ph = db._ph
    def _query():
        conditions = [f"p.post_type = 'question'", f"p.moderation_status = 'approved'"]
        params: list = []
        if entity_id:
            conditions.append(f"p.entity_id::text = {ph}")
            params.append(entity_id)
        if filter == "unanswered":
            conditions.append("p.comment_count = 0")
        elif filter == "no_best_answer":
            conditions.append("p.best_answer_id IS NULL")
        where = " AND ".join(conditions)
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT p.id, p.title, p.content, p.entity_id, p.user_id,
                       p.comment_count, p.best_answer_id, p.created_at,
                       u.display_name
                FROM posts p
                JOIN users u ON u.id = p.user_id
                WHERE {where}
                ORDER BY p.created_at DESC
                LIMIT {ph} OFFSET {ph}
            """, (*params, limit, offset))
            total_row = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM posts p WHERE {where}
            """, (*params,))
        total = db._row_to_dict(total_row)["c"] if total_row else 0
        return {
            "questions": [db._row_to_dict(r) for r in rows],
            "total": total,
            "filter": filter,
        }
    return await asyncio.to_thread(_query)


class SetBestAnswerBody(BaseModel):
    comment_id: str = Field(..., min_length=1, max_length=100)


@router.post("/qa-queue/{post_id}/set-best-answer")
async def qa_set_best_answer(post_id: str, body: SetBestAnswerBody):
    """Admin override: set best_answer_id cho 1 question."""
    post_id = validate_path_id(post_id, "post_id")
    ph = db._ph
    def _query():
        with db._conn() as conn:
            post = db._fetchone(conn, f"""
                SELECT id, post_type FROM posts WHERE id::text = {ph}
            """, (post_id,))
            if not post:
                raise HTTPException(404, "Bài hỏi không tồn tại")
            p = db._row_to_dict(post)
            if p.get("post_type") != "question":
                raise HTTPException(400, "Chỉ set best answer cho post_type=question")
            comment = db._fetchone(conn, f"""
                SELECT id FROM comments WHERE id::text = {ph} AND post_id::text = {ph}
            """, (body.comment_id, post_id))
            if not comment:
                raise HTTPException(404, "Comment không thuộc bài hỏi này")
            db._execute(conn, f"""
                UPDATE posts SET best_answer_id = {ph}::uuid WHERE id::text = {ph}
            """, (body.comment_id, post_id))
        return {"ok": True, "post_id": post_id, "best_answer_id": body.comment_id}
    return await asyncio.to_thread(_query)


# ── Contact funnel dashboard (U-22) ──

CONTACT_VIEWS_FILE = Path(__file__).resolve().parent / "data" / "contact_views.jsonl"


@router.get("/contact-funnel")
async def contact_funnel(
    days: int = Query(30, ge=1, le=365),
    entity_id: Optional[str] = Query(None, max_length=100),
):
    """Thống kê click vào thông tin liên hệ — zalo/phone/website/map."""
    def _query():
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        counts: dict[str, dict[str, int]] = {}
        total = 0
        if not CONTACT_VIEWS_FILE.exists():
            return {"entities": [], "period_days": days, "total_contacts": 0}
        with open(CONTACT_VIEWS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                ts_str = rec.get("ts", "")
                try:
                    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    continue
                if ts < cutoff:
                    continue
                eid = rec.get("entity_id", "")
                if entity_id and eid != entity_id:
                    continue
                action = rec.get("action", "other")
                if eid not in counts:
                    counts[eid] = {"zalo": 0, "phone": 0, "website": 0, "map": 0, "total": 0}
                counts[eid][action] = counts[eid].get(action, 0) + 1
                counts[eid]["total"] += 1
                total += 1
        entities_list = []
        ent_dict = knowledge._entities if hasattr(knowledge, "_entities") else {}
        for eid, c in sorted(counts.items(), key=lambda x: -x[1]["total"]):
            e = ent_dict.get(eid, {})
            entities_list.append({
                "id": eid,
                "name": e.get("name", eid),
                "zalo": c["zalo"],
                "phone": c["phone"],
                "website": c["website"],
                "map": c["map"],
                "total": c["total"],
            })
        return {"entities": entities_list, "period_days": days, "total_contacts": total}
    return await asyncio.to_thread(_query)


@router.get("/contact-funnel/export")
async def contact_funnel_export(days: int = Query(30, ge=1, le=365)):
    """Export contact funnel dạng CSV."""
    import io

    def _generate():
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        counts: dict[str, dict[str, int]] = {}
        if CONTACT_VIEWS_FILE.exists():
            with open(CONTACT_VIEWS_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except (json.JSONDecodeError, ValueError):
                        continue
                    ts_str = rec.get("ts", "")
                    try:
                        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        continue
                    if ts < cutoff:
                        continue
                    eid = rec.get("entity_id", "")
                    action = rec.get("action", "other")
                    if eid not in counts:
                        counts[eid] = {"zalo": 0, "phone": 0, "website": 0, "map": 0, "total": 0}
                    counts[eid][action] = counts[eid].get(action, 0) + 1
                    counts[eid]["total"] += 1
        ent_dict = knowledge._entities if hasattr(knowledge, "_entities") else {}
        yield "entity_id,name,zalo,phone,website,map,total\n"
        for eid, c in sorted(counts.items(), key=lambda x: -x[1]["total"]):
            name = (ent_dict.get(eid, {}).get("name") or eid).replace(",", " ")
            yield f"{eid},{name},{c['zalo']},{c['phone']},{c['website']},{c['map']},{c['total']}\n"

    return StreamingResponse(_generate(), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=contact_funnel.csv"})


# ── Collections CRUD (U-28) ──


class CollectionCreate(BaseModel):
    slug: str = Field(..., min_length=2, max_length=100, pattern=r"^[a-z0-9\-]+$")
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field("", max_length=2000)
    cover_image: str | None = None
    entity_ids: list[str] = Field(default_factory=list, max_length=100)
    sort_order: int = Field(0, ge=0)
    is_published: bool = False


class CollectionUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=2000)
    cover_image: str | None = None
    entity_ids: list[str] | None = Field(None, max_length=100)
    sort_order: int | None = Field(None, ge=0)
    is_published: bool | None = None


@router.get("/collections")
async def list_collections(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    ph = db._ph
    def _query():
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT * FROM collections ORDER BY sort_order, created_at DESC
                LIMIT {ph} OFFSET {ph}
            """, (limit, offset))
            total_row = db._fetchone(conn, "SELECT COUNT(*) as c FROM collections", ())
        return {
            "collections": [db._row_to_dict(r) for r in rows],
            "total": db._row_to_dict(total_row)["c"] if total_row else 0,
        }
    return await asyncio.to_thread(_query)


@router.post("/collections", status_code=201)
async def create_collection(body: CollectionCreate, request: Request):
    ph = db._ph
    user = request.state.user if hasattr(request.state, "user") else None
    created_by = str(user["id"]) if user else None
    def _query():
        with db._conn() as conn:
            existing = db._fetchone(conn, f"SELECT id FROM collections WHERE slug = {ph}", (body.slug,))
            if existing:
                raise HTTPException(409, "Slug đã tồn tại")
            db._execute(conn, f"""
                INSERT INTO collections (slug, title, description, cover_image, entity_ids, sort_order, is_published, created_by)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph}::jsonb, {ph}, {ph}, {ph}::uuid)
            """, (body.slug, body.title, body.description, body.cover_image,
                  json.dumps(body.entity_ids), body.sort_order, body.is_published, created_by))
            row = db._fetchone(conn, f"SELECT * FROM collections WHERE slug = {ph}", (body.slug,))
        return db._row_to_dict(row)
    return await asyncio.to_thread(_query)


@router.put("/collections/{collection_id}")
async def update_collection(collection_id: str, body: CollectionUpdate):
    collection_id = validate_path_id(collection_id, "collection_id")
    ph = db._ph
    def _query():
        sets = []
        params: list = []
        if body.title is not None:
            sets.append(f"title = {ph}")
            params.append(body.title)
        if body.description is not None:
            sets.append(f"description = {ph}")
            params.append(body.description)
        if body.cover_image is not None:
            sets.append(f"cover_image = {ph}")
            params.append(body.cover_image)
        if body.entity_ids is not None:
            sets.append(f"entity_ids = {ph}::jsonb")
            params.append(json.dumps(body.entity_ids))
        if body.sort_order is not None:
            sets.append(f"sort_order = {ph}")
            params.append(body.sort_order)
        if body.is_published is not None:
            sets.append(f"is_published = {ph}")
            params.append(body.is_published)
        if not sets:
            raise HTTPException(400, "Không có trường nào để cập nhật")
        sets.append("updated_at = NOW()")
        params.append(collection_id)
        with db._conn() as conn:
            row = db._fetchone(conn, f"""
                UPDATE collections SET {', '.join(sets)} WHERE id::text = {ph} RETURNING *
            """, tuple(params))
        if not row:
            raise HTTPException(404, "Collection không tồn tại")
        return db._row_to_dict(row)
    return await asyncio.to_thread(_query)


@router.delete("/collections/{collection_id}")
async def delete_collection(collection_id: str):
    collection_id = validate_path_id(collection_id, "collection_id")
    ph = db._ph
    def _query():
        with db._conn() as conn:
            row = db._fetchone(conn, f"DELETE FROM collections WHERE id::text = {ph} RETURNING id", (collection_id,))
        if not row:
            raise HTTPException(404, "Collection không tồn tại")
        return {"ok": True, "deleted": collection_id}
    return await asyncio.to_thread(_query)


# ── Review responses (U-11) ──


class ReviewResponseBody(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


@router.post("/posts/{post_id}/response")
async def admin_review_response(post_id: str, body: ReviewResponseBody, request: Request):
    """Admin/business reply to a review — one response per review (UNIQUE)."""
    post_id = validate_path_id(post_id, "post_id")
    ph = db._ph
    user = request.state.user if hasattr(request.state, "user") else None
    responder_id = str(user["id"]) if user else None
    def _query():
        with db._conn() as conn:
            post = db._fetchone(conn, f"SELECT post_type FROM posts WHERE id::text = {ph}", (post_id,))
            if not post:
                raise HTTPException(404, "Bài viết không tồn tại")
            if db._row_to_dict(post).get("post_type") != "review":
                raise HTTPException(400, "Chỉ phản hồi cho bài đánh giá (review)")
            existing = db._fetchone(conn, f"SELECT id FROM review_responses WHERE post_id::text = {ph}", (post_id,))
            if existing:
                raise HTTPException(409, "Bài đánh giá đã có phản hồi")
            db._execute(conn, f"""
                INSERT INTO review_responses (post_id, responder_id, content)
                VALUES ({ph}::uuid, {ph}::uuid, {ph})
            """, (post_id, responder_id, body.content))
            row = db._fetchone(conn, f"SELECT * FROM review_responses WHERE post_id::text = {ph}", (post_id,))
        return db._row_to_dict(row) if row else {"ok": True}
    return await asyncio.to_thread(_query)


@router.get("/posts/{post_id}/response")
async def get_review_response(post_id: str):
    """Get the admin response for a review post."""
    post_id = validate_path_id(post_id, "post_id")
    ph = db._ph
    def _query():
        with db._conn() as conn:
            row = db._fetchone(conn, f"""
                SELECT rr.*, u.display_name as responder_name
                FROM review_responses rr
                JOIN users u ON u.id = rr.responder_id
                WHERE rr.post_id::text = {ph}
            """, (post_id,))
        if not row:
            return None
        return db._row_to_dict(row)
    result = await asyncio.to_thread(_query)
    if not result:
        return JSONResponse(status_code=404, content={"error": "no_response"})
    return result


class BulkDeleteRequest(BaseModel):
    entity_ids: list[str] = Field(..., min_length=1, max_length=200)

@router.post("/entities/bulk-delete")
async def bulk_delete(body: BulkDeleteRequest):
    """Xóa nhiều entities cùng lúc."""
    def _query():
        from public_api import invalidate_entity_cache
        deleted = 0
        for eid in body.entity_ids:
            if db.delete_entity(eid):
                invalidate_entity_cache(eid)
                deleted += 1
        if deleted:
            _sync_kb()
        return deleted
    deleted = await asyncio.to_thread(_query)
    return {"success": True, "count": deleted}


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
    offset: int = Query(0, ge=0, le=10000),
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
    validate_path_id(suggestion_id, "suggestion_id")
    def _query():
        s = _imgq.get_suggestion(suggestion_id)
        if not s:
            raise HTTPException(404, "Đề xuất không tồn tại")
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
    validate_path_id(suggestion_id, "suggestion_id")
    from fastapi.concurrency import run_in_threadpool
    from storage import storage, MAX_IMAGE_SIZE

    s = _imgq.get_suggestion(suggestion_id)
    if not s:
        raise HTTPException(404, "Đề xuất không tồn tại")
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
        logger.warning("Suggestion image fetch failed for %s: %s", candidate_url, e)
        raise HTTPException(502, "Không tải được ảnh nguồn, vui lòng thử lại sau")

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
        "added_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    })
    attrs["image_credits"] = credits
    entity["attributes"] = attrs
    entity["updatedAt"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    db.upsert_entity(entity)

    # require_admin already authenticated; record a generic approver marker for audit.
    _imgq.mark_status(suggestion_id, "approved", approved_by="admin")
    _sync_kb()
    return {"status": "approved", "url": cover, "sizes": urls, "images": images,
            "backend": storage.backend, "credits": credits[-1]}


@router.post("/image-suggestions/{suggestion_id}/reject")
async def reject_image_suggestion(suggestion_id: str, body: RejectSuggestionRequest = RejectSuggestionRequest()):
    """Từ chối 1 ứng viên (ghi lý do). Không tải/không upload gì."""
    validate_path_id(suggestion_id, "suggestion_id")
    def _query():
        s = _imgq.get_suggestion(suggestion_id)
        if not s:
            raise HTTPException(404, "Đề xuất không tồn tại")
        if s.get("status") != "pending":
            raise HTTPException(400, f"Suggestion đã ở trạng thái '{s.get('status')}' — không thể từ chối lại")
        _imgq.mark_status(suggestion_id, "rejected", rejection_reason=(body.reason or "").strip())
    await asyncio.to_thread(_query)
    return {"status": "rejected", "id": suggestion_id}


# ── Data management ──

_server_start_time = __import__("time").time()


@router.get("/system-health")
async def system_health():
    import os
    import time as _t
    def _query():
        result = {"sqlite": {}, "postgres": {}, "server": {}}
        result["server"]["uptime_seconds"] = int(_t.time() - _server_start_time)
        result["server"]["uptime_human"] = _format_uptime(int(_t.time() - _server_start_time))
        result["server"]["pid"] = os.getpid()
        try:
            import psutil
            proc = psutil.Process(os.getpid())
            result["server"]["memory_mb"] = round(proc.memory_info().rss / 1024 / 1024, 1)
        except (ImportError, Exception):
            result["server"]["memory_mb"] = -1

        db_path = os.path.join(os.path.dirname(__file__), "data", "knowledge.db")
        if os.path.exists(db_path):
            result["sqlite"]["size_mb"] = round(os.path.getsize(db_path) / 1024 / 1024, 2)
            result["sqlite"]["entities"] = len(db.list_entities(limit=100000, offset=0))
        if db._use_pg:
            with db._conn() as conn:
                tables = ["users", "posts", "comments", "likes", "follows",
                           "notifications", "blocks", "sessions", "user_visits",
                           "reports", "saved_entities", "announcements"]
                pg_tables = {}
                for t in tables:
                    try:
                        row = db._fetchone(conn, f"SELECT COUNT(*) as c FROM {t}", ())
                        pg_tables[t] = db._row_to_dict(row)["c"] if row else 0
                    except Exception:
                        pg_tables[t] = -1
                result["postgres"]["tables"] = pg_tables
                try:
                    size_row = db._fetchone(conn, """
                        SELECT pg_database_size(current_database()) as s
                    """, ())
                    result["postgres"]["size_mb"] = round(db._row_to_dict(size_row)["s"] / 1024 / 1024, 2) if size_row else 0
                except Exception:
                    result["postgres"]["size_mb"] = -1
                active_row = db._fetchone(conn, """
                    SELECT COUNT(*) as c FROM sessions WHERE expires_at > NOW()
                """, ())
                result["postgres"]["active_sessions"] = db._row_to_dict(active_row)["c"] if active_row else 0
                pending_row = db._fetchone(conn, """
                    SELECT COUNT(*) as c FROM posts WHERE moderation_status = 'pending'
                """, ())
                result["postgres"]["pending_moderation"] = db._row_to_dict(pending_row)["c"] if pending_row else 0
                open_reports = db._fetchone(conn, """
                    SELECT COUNT(*) as c FROM reports WHERE status = 'pending'
                """, ())
                result["postgres"]["open_reports"] = db._row_to_dict(open_reports)["c"] if open_reports else 0
        data_dir = Path(__file__).resolve().parent / "data"
        jsonl_files = list(data_dir.glob("*.jsonl"))
        result["storage"] = {
            "jsonl_files": len(jsonl_files),
            "jsonl_size_mb": round(sum(f.stat().st_size for f in jsonl_files) / 1024 / 1024, 2),
        }
        return result
    return await asyncio.to_thread(_query)


def _format_uptime(seconds: int) -> str:
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return " ".join(parts)


@router.get("/featured")
async def list_featured():
    ph = db._ph
    def _query():
        if not db._use_pg:
            return {"featured": []}
        with db._conn() as conn:
            rows = db._fetchall(conn, """
                SELECT entity_id, sort_order, created_at
                FROM featured_entities ORDER BY sort_order
            """, ())
        result = []
        for r in rows:
            rd = db._row_to_dict(r)
            entity = db.get_entity(rd["entity_id"])
            if entity:
                result.append({
                    "entity_id": rd["entity_id"],
                    "name": entity.get("name"),
                    "type": entity.get("type"),
                    "sort_order": rd["sort_order"],
                    "created_at": str(rd["created_at"]),
                })
        return {"featured": result}
    return await asyncio.to_thread(_query)


@router.post("/featured/{entity_id}")
async def toggle_featured(entity_id: str, request: Request):
    entity_id = validate_path_id(entity_id, "entity_id")
    entity = await asyncio.to_thread(db.get_entity, entity_id)
    if not entity:
        raise HTTPException(404, "Entity không tồn tại")
    admin_user = request.state.admin_user
    ph = db._ph
    def _query():
        if not db._use_pg:
            raise HTTPException(503, "Chức năng này yêu cầu Postgres")
        with db._conn() as conn:
            existing = db._fetchone(conn, f"""
                SELECT id FROM featured_entities WHERE entity_id = {ph}
            """, (entity_id,))
            if existing:
                db._execute(conn, f"DELETE FROM featured_entities WHERE entity_id = {ph}", (entity_id,))
                return False
            db._execute(conn, f"""
                INSERT INTO featured_entities (entity_id, added_by, sort_order)
                VALUES ({ph}, {ph}::uuid, (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM featured_entities))
            """, (entity_id, str(admin_user["id"])))
            return True
    is_featured = await asyncio.to_thread(_query)
    return {"entity_id": entity_id, "featured": is_featured}


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
                logger.debug("Stats PG deltas query failed", exc_info=True)

        entities_week = 0
        try:
            with db._conn() as c3:
                ew = db._fetchone(c3, "SELECT COUNT(*) as c FROM entities WHERE type != 'place' AND created_at >= datetime('now', '-7 days')", ())
                entities_week = db._row_to_dict(ew)["c"] if ew else 0
        except Exception:
            logger.debug("Stats entities_week query failed", exc_info=True)

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
            logger.debug("Stats backup info scan failed", exc_info=True)

        return {
            "total_entities": total_entities,
            "total_places": total_places,
            "total_relationships": db._row_to_dict(rel_count)["c"] if rel_count else 0,
            "total_itineraries": db._row_to_dict(itin_count)["c"] if itin_count else 0,
            "by_type": by_type,
            "completeness": completeness,
            "entities_week": entities_week,
            "backup": backup_info,
            **deltas,
        }
    return await asyncio.to_thread(_query)


@router.get("/user-engagement")
async def user_engagement_stats(days: int = Query(30, ge=1, le=365)):
    ph = db._ph
    def _query():
        if not db._use_pg:
            return {"error": "Chức năng này yêu cầu Postgres"}
        with db._conn() as conn:
            active_posters = db._fetchone(conn, f"""
                SELECT COUNT(DISTINCT user_id) as c FROM posts
                WHERE created_at > NOW() - INTERVAL '{days} days'
            """, ())
            active_commenters = db._fetchone(conn, f"""
                SELECT COUNT(DISTINCT user_id) as c FROM comments
                WHERE created_at > NOW() - INTERVAL '{days} days'
            """, ())
            active_likers = db._fetchone(conn, f"""
                SELECT COUNT(DISTINCT user_id) as c FROM likes
                WHERE created_at > NOW() - INTERVAL '{days} days'
            """, ())
            new_users = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM users
                WHERE created_at > NOW() - INTERVAL '{days} days'
            """, ())
            retained = db._fetchone(conn, f"""
                SELECT COUNT(DISTINCT p.user_id) as c FROM posts p
                JOIN users u ON u.id = p.user_id
                WHERE p.created_at > NOW() - INTERVAL '{days} days'
                  AND u.created_at < NOW() - INTERVAL '{days} days'
            """, ())
            total_users = db._fetchone(conn, f"SELECT COUNT(*) as c FROM users WHERE is_active = TRUE", ())
            daily = db._fetchall(conn, f"""
                SELECT DATE(created_at) as day, COUNT(DISTINCT user_id) as active_users
                FROM posts WHERE created_at > NOW() - INTERVAL '{days} days'
                GROUP BY DATE(created_at) ORDER BY day
            """, ())
        tu = db._row_to_dict(total_users)["c"] if total_users else 1
        ap = db._row_to_dict(active_posters)["c"] if active_posters else 0
        return {
            "period_days": days,
            "total_active_users": tu,
            "active_posters": ap,
            "active_commenters": db._row_to_dict(active_commenters)["c"] if active_commenters else 0,
            "active_likers": db._row_to_dict(active_likers)["c"] if active_likers else 0,
            "new_users": db._row_to_dict(new_users)["c"] if new_users else 0,
            "retained_users": db._row_to_dict(retained)["c"] if retained else 0,
            "engagement_rate": round(ap / tu * 100, 1) if tu else 0,
            "daily_active": [{"day": str(db._row_to_dict(r)["day"]), "users": db._row_to_dict(r)["active_users"]} for r in daily],
        }
    return await asyncio.to_thread(_query)


@router.get("/user-growth")
async def user_growth(days: int = Query(30, ge=7, le=365)):
    ph = db._ph
    def _query():
        if not db._use_pg:
            return {"error": "Chức năng này yêu cầu Postgres"}
        with db._conn() as conn:
            daily_reg = db._fetchall(conn, f"""
                SELECT DATE(created_at) as day, COUNT(*) as signups
                FROM users
                WHERE created_at > NOW() - INTERVAL '{days} days'
                GROUP BY DATE(created_at) ORDER BY day
            """, ())
            total = db._fetchone(conn, "SELECT COUNT(*) as c FROM users WHERE is_active = TRUE", ())
            deactivated = db._fetchone(conn, "SELECT COUNT(*) as c FROM users WHERE is_active = FALSE", ())
            week_ago = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM users WHERE created_at > NOW() - INTERVAL '7 days'
            """, ())
            prev_week = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM users
                WHERE created_at > NOW() - INTERVAL '14 days'
                  AND created_at <= NOW() - INTERVAL '7 days'
            """, ())
        t = db._row_to_dict(total)["c"] if total else 0
        d = db._row_to_dict(deactivated)["c"] if deactivated else 0
        w = db._row_to_dict(week_ago)["c"] if week_ago else 0
        pw = db._row_to_dict(prev_week)["c"] if prev_week else 0
        growth_rate = round((w - pw) / pw * 100, 1) if pw > 0 else 0
        return {
            "total_users": t,
            "active_users": t,
            "deactivated_users": d,
            "signups_this_week": w,
            "signups_prev_week": pw,
            "growth_rate_pct": growth_rate,
            "daily_signups": [{"day": str(db._row_to_dict(r)["day"]), "signups": db._row_to_dict(r)["signups"]} for r in daily_reg],
        }
    return await asyncio.to_thread(_query)


_last_backup_time: float = 0
_BACKUP_COOLDOWN = _cfg.BACKUP_COOLDOWN

@router.post("/backup-trigger")
async def trigger_backup():
    """B5c: trigger manual backup from admin UI."""
    import time as _time
    global _last_backup_time
    now = _time.monotonic()
    if now - _last_backup_time < _BACKUP_COOLDOWN:
        remaining = int(_BACKUP_COOLDOWN - (now - _last_backup_time))
        raise HTTPException(429, f"Backup đã chạy gần đây. Thử lại sau {remaining} giây.")
    _last_backup_time = now
    script = Path(__file__).resolve().parent.parent / "scripts" / "backup_data.py"
    if not script.exists():
        raise HTTPException(500, "Không tìm thấy script backup_data.py")
    def _run():
        try:
            result = subprocess.run(
                [sys.executable, str(script), "--label", "admin-manual"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                logger.error("Backup script failed: %s", result.stderr)
                raise HTTPException(500, "Backup thất bại. Kiểm tra log server.")
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
    page: int = Query(1, ge=1, le=1000),
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

        total_images = len(media_items)
        no_credit_count = sum(1 for m in media_items if not m["credit"])
        dup_count = sum(1 for u, ids in url_usage.items() if len(ids) > 1)

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

        return {
            "items": page_items,
            "total": total,
            "page": page,
            "stats": {
                "total_images": total_images,
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
            logger.debug("Badge image queue count failed", exc_info=True)
        with db._conn() as conn2:
            unc_row = db._fetchone(conn2, "SELECT COUNT(*) as c FROM entities WHERE type != 'place' AND (placeId IS NULL OR placeId = '')", ())
            counts["unclassified"] = db._row_to_dict(unc_row)["c"] if unc_row else 0
        try:
            import kb_curation
            s = kb_curation.stats()
            counts["provisional"] = s.get("pending", 0)
        except Exception:
            logger.debug("Badge kb_curation stats failed", exc_info=True)
        if _INFO_REPORTS_FILE.exists():
            try:
                lines = _INFO_REPORTS_FILE.read_text(encoding="utf-8").strip().split("\n")
                counts["reports"] = sum(1 for l in lines if l.strip() and json.loads(l).get("status", "open") == "open")
            except Exception:
                logger.debug("Badge reports file parse failed", exc_info=True)
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
                logger.debug("Alert reports file parse failed", exc_info=True)
        try:
            img_pending = _imgq.status_counts().get("pending", 0)
            if img_pending:
                alerts.append({"type": "images", "count": img_pending, "label": f"{img_pending} ảnh chờ duyệt", "icon": "🖼️", "link": "/admin/duyet-anh", "priority": 4})
        except Exception:
            logger.debug("Alert image queue count failed", exc_info=True)
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
            logger.debug("Alert kb_curation stats failed", exc_info=True)
        try:
            appeal_row = db._fetchone(conn2, "SELECT COUNT(*) as c FROM moderation_appeals WHERE status = 'pending'", ())
            appeal_count = db._row_to_dict(appeal_row)["c"] if appeal_row else 0
            if appeal_count:
                alerts.append({"type": "appeals", "count": appeal_count, "label": f"{appeal_count} khiếu nại chờ xử lý", "icon": "📩", "link": "/admin/khieu-nai", "priority": 2})
        except Exception:
            logger.debug("Alert appeals count failed", exc_info=True)
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
            logger.debug("Activity feed read failed", exc_info=True)
            return {"actions": []}
    return await asyncio.to_thread(_query)


_learn_proc: Optional[subprocess.Popen] = None

@router.post("/trigger-learn")
async def trigger_learn(category: Optional[str] = Query(None, max_length=50), topics: int = 3):
    """Trigger 1 vòng auto-learn (chạy background)."""
    if topics < 1 or topics > 20:
        raise HTTPException(400, "Số chủ đề phải từ 1 đến 20")
    if category:
        if len(category) > 50 or not re.match(r'^[\w\s\-À-ɏḀ-ỿ]+$', category):
            raise HTTPException(400, "Danh mục không hợp lệ — chỉ chấp nhận chữ, số, dấu gạch (tối đa 50 ký tự)")
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
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
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
    validate_path_id(entity_id, "entity_id")
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
    validate_path_id(entity_id, "entity_id")
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
        entities = db.all_entities()
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


@router.get("/export/users")
async def export_users_csv():
    """CSV export of all users with stats."""
    ph = db._ph

    def _generate():
        with db._conn() as conn:
            rows = db._fetchall(conn, """
                SELECT u.id, u.phone, u.display_name, u.role, u.is_active,
                       u.reputation, u.created_at,
                       COALESCE(pc.post_count, 0) AS post_count,
                       COALESCE(fc.follower_count, 0) AS follower_count
                FROM users u
                LEFT JOIN (
                    SELECT user_id, COUNT(*) AS post_count FROM posts
                    WHERE moderation_status != 'rejected'
                    GROUP BY user_id
                ) pc ON pc.user_id = u.id
                LEFT JOIN (
                    SELECT target_id, COUNT(*) AS follower_count FROM follows
                    WHERE target_type = 'user'
                    GROUP BY target_id
                ) fc ON fc.target_id = u.id::text
                ORDER BY u.created_at DESC
            """, ())
        yield "id,phone,display_name,role,is_active,reputation,created_at,post_count,follower_count\n"
        for r in rows:
            d = db._row_to_dict(r)
            phone = _mask(d.get("phone") or "")
            name = (d.get("display_name") or "").replace(",", " ").replace('"', "'")
            yield (f'{d["id"]},{phone},"{name}",{d.get("role","user")},'
                   f'{d.get("is_active",True)},{d.get("reputation",0)},'
                   f'{d.get("created_at","")},{d["post_count"]},{d["follower_count"]}\n')

    return StreamingResponse(_generate(), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=users.csv"})


@router.get("/export/posts")
async def export_posts_csv(
    status: str = Query("all", max_length=20),
    days: int = Query(90, ge=1, le=365),
):
    """CSV export of posts with author/entity info."""
    ph = db._ph

    def _generate():
        where_parts = []
        params = []
        if status != "all":
            where_parts.append(f"p.moderation_status = {ph}")
            params.append(status)
        where_parts.append(f"p.created_at > NOW() - INTERVAL '{days} days'")
        where_clause = " AND ".join(where_parts) if where_parts else "TRUE"
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT p.id, p.user_id, p.post_type, p.rating,
                       p.like_count, p.comment_count, p.share_count,
                       p.moderation_status, p.entity_id, p.created_at,
                       u.display_name AS author_name
                FROM posts p
                LEFT JOIN users u ON u.id = p.user_id
                WHERE {where_clause}
                ORDER BY p.created_at DESC
            """, tuple(params))
        yield "id,user_id,author_name,post_type,rating,like_count,comment_count,share_count,status,entity_id,created_at\n"
        for r in rows:
            d = db._row_to_dict(r)
            name = (d.get("author_name") or "").replace(",", " ").replace('"', "'")
            yield (f'{d["id"]},{d.get("user_id","")},"{name}",'
                   f'{d.get("post_type","")},{d.get("rating","")},{d.get("like_count",0)},'
                   f'{d.get("comment_count",0)},{d.get("share_count",0)},'
                   f'{d.get("moderation_status","")},{d.get("entity_id","")},{d.get("created_at","")}\n')

    return StreamingResponse(_generate(), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=posts.csv"})


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
    page: int = Query(1, ge=1, le=1000),
    limit: int = Query(20, ge=1, le=100),
):
    ph = db._ph
    offset = (page - 1) * limit
    statuses = ["pending", "flagged"] if status == "review" else [status]
    placeholders = ", ".join([ph] * len(statuses))
    def _query():
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT p.*, u.display_name,
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
            "total": db._row_to_dict(total)["c"] if total else 0,
            "page": page,
        }
    return await asyncio.to_thread(_query)


@router.post("/moderation/{post_id}/approve")
async def approve_post(post_id: str):
    post_id = validate_path_id(post_id, "post_id")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            row = db._fetchone(conn, f"""
                UPDATE posts SET moderation_status = 'approved' WHERE id::text = {ph}
                RETURNING user_id
            """, (post_id,))
            if not row:
                raise HTTPException(404, "Bài viết không tồn tại")
            author_id = str(db._row_to_dict(row)["user_id"])
        _log_mod_action("post", post_id, "approved")
        try:
            create_notification(author_id, "moderation",
                                "Bài viết của bạn đã được duyệt",
                                ref_type="post", ref_id=post_id)
        except Exception:
            logger.exception("Failed to notify post approval %s", post_id)
    await asyncio.to_thread(_query)
    return {"success": True}


class RejectBody(BaseModel):
    reason: str | None = Field(None, max_length=500)


@router.post("/moderation/{post_id}/reject")
async def reject_post(post_id: str, body: RejectBody = RejectBody()):
    post_id = validate_path_id(post_id, "post_id")
    reason = (body.reason or "").strip() or None
    def _query():
        ph = db._ph
        with db._conn() as conn:
            row = db._fetchone(conn, f"""
                UPDATE posts SET moderation_status = 'rejected' WHERE id::text = {ph}
                RETURNING user_id
            """, (post_id,))
            if not row:
                raise HTTPException(404, "Bài viết không tồn tại")
            author_id = str(db._row_to_dict(row)["user_id"])
        _log_mod_action("post", post_id, "rejected", reason)
        try:
            notif_body = f"Lý do: {reason}" if reason else None
            create_notification(author_id, "moderation",
                                "Bài viết của bạn đã bị từ chối",
                                body=notif_body,
                                ref_type="post", ref_id=post_id)
        except Exception:
            logger.exception("Failed to notify post rejection %s", post_id)
    await asyncio.to_thread(_query)
    return {"success": True}


class BatchModerationBody(BaseModel):
    post_ids: list[str] = Field(..., min_length=1, max_length=100)
    action: str = Field(..., max_length=20)  # 'approve' or 'reject'
    reason: str = Field("", max_length=500)


@router.post("/moderation/batch")
async def batch_moderation(body: BatchModerationBody):
    from ratelimit import check_rate
    check_rate("admin:batch-mod", 10, 60, "Thao tác quá nhanh")
    if body.action not in ("approve", "reject"):
        raise HTTPException(400, "action must be 'approve' or 'reject'")
    if not body.post_ids or len(body.post_ids) > 100:
        raise HTTPException(400, "post_ids: 1-100 items")
    status = "approved" if body.action == "approve" else "rejected"
    reason = body.reason.strip() or None
    def _query():
        ph = db._ph
        placeholders = ", ".join(ph for _ in body.post_ids)
        params = [status] + list(body.post_ids)
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                UPDATE posts SET moderation_status = {ph}
                WHERE id::text IN ({placeholders})
                RETURNING id, user_id
            """, tuple(params))
            updated = len(rows)
        for pid in body.post_ids:
            _log_mod_action("post", pid, status, reason)
        if status == "approved":
            title = "Bài viết của bạn đã được duyệt"
            notif_body = None
        else:
            title = "Bài viết của bạn đã bị từ chối"
            notif_body = f"Lý do: {reason}" if reason else None
        for r in rows:
            rd = db._row_to_dict(r)
            try:
                create_notification(str(rd["user_id"]), "moderation", title,
                                    body=notif_body,
                                    ref_type="post", ref_id=str(rd["id"]))
            except Exception:
                logger.exception("Failed to notify batch moderation %s", rd["id"])
        return updated
    updated = await asyncio.to_thread(_query)
    return {"success": True, "updated": updated, "requested": len(body.post_ids)}


@router.get("/moderation/{post_id}/history")
async def moderation_history(post_id: str):
    """Admin: view full moderation action timeline for a specific post."""
    post_id = validate_path_id(post_id, "post_id")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            post = db._fetchone(conn, f"""
                SELECT id, moderation_status, created_at FROM posts WHERE id::text = {ph}
            """, (post_id,))
            if not post:
                raise HTTPException(404, "Bài viết không tồn tại")
            rows = db._fetchall(conn, f"""
                SELECT ml.action, ml.reason, ml.auto, ml.scores, ml.created_at,
                       u.display_name AS moderator_name
                FROM moderation_log ml
                LEFT JOIN users u ON u.id = ml.moderator_id
                WHERE ml.target_type = 'post' AND ml.target_id = {ph}
                ORDER BY ml.created_at DESC
                LIMIT 50
            """, (post_id,))
        pd = db._row_to_dict(post)
        actions = []
        for r in rows:
            d = db._row_to_dict(r)
            scores = d.get("scores")
            if isinstance(scores, str):
                try:
                    scores = json.loads(scores)
                except (json.JSONDecodeError, ValueError, TypeError):
                    scores = {}
            actions.append({
                "action": d["action"],
                "reason": d.get("reason"),
                "auto": bool(d.get("auto")),
                "moderator": d.get("moderator_name"),
                "scores": scores or {},
                "created_at": str(d.get("created_at", "")),
            })
        return {
            "post_id": post_id,
            "current_status": pd.get("moderation_status"),
            "post_created_at": str(pd.get("created_at", "")),
            "actions": actions,
            "total": len(actions),
        }
    return await asyncio.to_thread(_query)


@router.post("/posts/{post_id}/feature")
async def feature_post(post_id: str, request: Request):
    """Admin: toggle feature a post at the top of its entity page."""
    post_id = validate_path_id(post_id, "post_id")
    admin_id = str(request.state.user["id"]) if hasattr(request, "state") and hasattr(request.state, "user") else None

    def _query():
        ph = db._ph
        with db._conn() as conn:
            row = db._fetchone(conn, f"SELECT id, entity_id, is_featured FROM posts WHERE id::text = {ph}", (post_id,))
            if not row:
                raise HTTPException(404, "Bài viết không tồn tại")
            rd = db._row_to_dict(row)
            if not rd.get("entity_id"):
                raise HTTPException(400, "Bài viết không thuộc entity nào")
            if rd.get("is_featured"):
                db._execute(conn, f"""
                    UPDATE posts SET is_featured = FALSE, featured_by = NULL, featured_at = NULL
                    WHERE id::text = {ph}
                """, (post_id,))
                return False
            db._execute(conn, f"""
                UPDATE posts SET is_featured = TRUE, featured_by = {ph}::uuid, featured_at = NOW()
                WHERE id::text = {ph}
            """, (admin_id, post_id))
            return True

    featured = await asyncio.to_thread(_query)
    _log_mod_action("post", post_id, "featured" if featured else "unfeatured", None)
    return {"featured": featured}


class _ReviewResponseBody2(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


@router.post("/posts/{post_id}/response")
async def add_review_response(post_id: str, body: _ReviewResponseBody2, request: Request):
    post_id = validate_path_id(post_id, "post_id")
    admin_id = request.state.user["id"] if hasattr(request, "state") and hasattr(request.state, "user") else None
    def _query():
        ph = db._ph
        with db._conn() as conn:
            post = db._fetchone(conn, f"""
                SELECT user_id, post_type FROM posts WHERE id::text = {ph}
            """, (post_id,))
            if not post:
                raise HTTPException(404, "Bài viết không tồn tại")
            pd = db._row_to_dict(post)
            if pd["post_type"] != "review":
                raise HTTPException(400, "Chỉ trả lời đánh giá (review)")
            existing = db._fetchone(conn, f"""
                SELECT id FROM review_responses WHERE post_id::text = {ph}
            """, (post_id,))
            if existing:
                raise HTTPException(409, "Đánh giá đã có phản hồi")
            import html as _html
            db._execute(conn, f"""
                INSERT INTO review_responses (post_id, responder_id, content)
                VALUES ({ph}::uuid, {ph}::uuid, {ph})
            """, (post_id, str(admin_id) if admin_id else None, _html.escape(body.content.strip())))
        try:
            create_notification(str(pd["user_id"]), "social",
                                "Đánh giá của bạn đã nhận được phản hồi",
                                ref_type="post", ref_id=post_id)
        except Exception:
            logger.exception("Failed to notify review response %s", post_id)
    await asyncio.to_thread(_query)
    return {"success": True}


@router.delete("/posts/{post_id}/response")
async def delete_review_response(post_id: str):
    post_id = validate_path_id(post_id, "post_id")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            row = db._fetchone(conn, f"""
                DELETE FROM review_responses WHERE post_id::text = {ph} RETURNING id
            """, (post_id,))
            if not row:
                raise HTTPException(404, "Không có phản hồi để xoá")
    await asyncio.to_thread(_query)
    return {"success": True}


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
                raise HTTPException(404, "Bài viết không tồn tại")
            db._execute(conn, f"""
                UPDATE posts SET moderation_notes = COALESCE(moderation_notes, '[]'::jsonb) || {ph}::jsonb
                WHERE id::text = {ph}
            """, (json.dumps({"text": body.note, "at": datetime.now(timezone.utc).isoformat()}), post_id))
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
            raise HTTPException(404, "Bài viết không tồn tại")
        notes = db._row_to_dict(row).get("moderation_notes") or []
        return {"notes": notes}
    return await asyncio.to_thread(_query)


@router.get("/moderation/stats")
async def moderation_stats():
    def _query():
        ph = db._ph
        with db._conn() as conn:
            rows = db._fetchall(conn, """
                SELECT moderation_status, COUNT(*) as c FROM posts GROUP BY moderation_status
            """, ())
            today = db._fetchone(conn, """
                SELECT COUNT(*) as c FROM posts WHERE created_at > NOW() - INTERVAL '24 hours'
            """, ())
            week = db._fetchone(conn, """
                SELECT COUNT(*) as c FROM posts WHERE created_at > NOW() - INTERVAL '7 days'
            """, ())
        return {
            "counts": {db._row_to_dict(row)["moderation_status"]: db._row_to_dict(row)["c"] for row in rows},
            "today": db._row_to_dict(today)["c"] if today else 0,
            "week": db._row_to_dict(week)["c"] if week else 0,
        }
    return await asyncio.to_thread(_query)


# ── Admin Content Search ──────────────────────────────────────────────────

@router.get("/content/search")
async def admin_content_search(
    q: str = Query(..., min_length=1, max_length=200),
    content_type: str = Query("post", pattern="^(post|comment|all)$"),
    status: str = Query("all", pattern="^(all|approved|pending|rejected|flagged)$"),
    post_type: str = Query(None, pattern="^(review|question|tip|photo|general)$"),
    page: int = Query(1, ge=1, le=1000),
    limit: int = Query(20, ge=1, le=100),
):
    """Admin search across posts and comments by keyword."""
    ph = db._ph
    offset = (page - 1) * limit
    search_esc = _escape_like(q)

    def _query():
        results = []
        total = 0
        with db._conn() as conn:
            if content_type in ("post", "all"):
                conditions = [f"(p.content ILIKE {ph} ESCAPE '\\' OR p.title ILIKE {ph} ESCAPE '\\')"]
                params = [f"%{search_esc}%", f"%{search_esc}%"]
                if status != "all":
                    conditions.append(f"p.moderation_status = {ph}")
                    params.append(status)
                if post_type:
                    conditions.append(f"p.post_type = {ph}")
                    params.append(post_type)
                where = " AND ".join(conditions)
                post_rows = db._fetchall(conn, f"""
                    SELECT p.id, p.title, p.content, p.post_type, p.moderation_status,
                           p.entity_id, p.created_at, p.like_count,
                           u.display_name as author_name
                    FROM posts p JOIN users u ON u.id = p.user_id
                    WHERE {where}
                    ORDER BY p.created_at DESC
                    LIMIT {ph} OFFSET {ph}
                """, tuple(params + [limit, offset]))
                post_count = db._fetchone(conn, f"SELECT COUNT(*) as c FROM posts p WHERE {where}", tuple(params))
                for r in post_rows:
                    d = db._row_to_dict(r)
                    d["_type"] = "post"
                    if d.get("content"):
                        d["content"] = d["content"][:300]
                    results.append(d)
                total += db._row_to_dict(post_count)["c"] if post_count else 0

            if content_type in ("comment", "all"):
                c_conditions = [f"c.content ILIKE {ph} ESCAPE '\\'"]
                c_params = [f"%{search_esc}%"]
                c_where = " AND ".join(c_conditions)
                comment_rows = db._fetchall(conn, f"""
                    SELECT c.id, c.content, c.post_id, c.created_at,
                           u.display_name as author_name
                    FROM comments c JOIN users u ON u.id = c.user_id
                    WHERE {c_where}
                    ORDER BY c.created_at DESC
                    LIMIT {ph} OFFSET {ph}
                """, tuple(c_params + [limit, offset]))
                comment_count = db._fetchone(conn, f"SELECT COUNT(*) as c FROM comments c WHERE {c_where}", tuple(c_params))
                for r in comment_rows:
                    d = db._row_to_dict(r)
                    d["_type"] = "comment"
                    if d.get("content"):
                        d["content"] = d["content"][:300]
                    results.append(d)
                total += db._row_to_dict(comment_count)["c"] if comment_count else 0
        return {"results": results, "total": total, "query": q, "page": page}

    return await asyncio.to_thread(_query)


# ── Admin Post Detail ────────────────────────────────────────────────────

@router.get("/posts/{post_id}")
async def admin_post_detail(post_id: str):
    """Full post detail with comments for admin review."""
    post_id = validate_path_id(post_id, "post_id")
    ph = db._ph

    def _query():
        with db._conn() as conn:
            post = db._fetchone(conn, f"""
                SELECT p.*, u.display_name as author_name, u.phone as author_phone,
                       u.avatar_url as author_avatar, u.role as author_role
                FROM posts p JOIN users u ON u.id = p.user_id
                WHERE p.id::text = {ph}
            """, (post_id,))
            if not post:
                raise HTTPException(404, "Bài viết không tồn tại")
            pd = db._row_to_dict(post)
            pd["author_phone"] = _mask(pd.get("author_phone", ""))

            comments = db._fetchall(conn, f"""
                SELECT c.id, c.content, c.created_at, c.parent_id,
                       u.display_name as author_name, u.id as user_id
                FROM comments c JOIN users u ON u.id = c.user_id
                WHERE c.post_id::text = {ph}
                ORDER BY c.created_at ASC
                LIMIT 100
            """, (post_id,))

            likes = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM likes WHERE post_id::text = {ph}
            """, (post_id,))

            reports = db._fetchall(conn, f"""
                SELECT r.id, r.reason, r.created_at, u.display_name as reporter_name
                FROM reports r JOIN users u ON u.id = r.reporter_id
                WHERE r.target_type = 'post' AND r.target_id = {ph}
                ORDER BY r.created_at DESC
            """, (post_id,))

        pd["comments"] = [db._row_to_dict(c) for c in comments]
        pd["comment_count"] = len(pd["comments"])
        pd["like_count_verified"] = db._row_to_dict(likes)["c"] if likes else 0
        pd["reports"] = [db._row_to_dict(r) for r in reports]
        pd["report_count"] = len(pd["reports"])
        return pd

    return await asyncio.to_thread(_query)


# ── Appeal management (NĐ147 compliance) ──

@router.get("/appeals")
async def list_appeals(
    status: str = Query("pending", pattern="^(pending|approved|rejected|all)$"),
    page: int = Query(1, ge=1, le=1000),
    limit: int = Query(20, ge=1, le=100),
):
    ph = db._ph
    offset = (page - 1) * limit
    def _query():
        with db._conn() as conn:
            where = "" if status == "all" else f"WHERE a.status = {ph}"
            params = [] if status == "all" else [status]
            rows = db._fetchall(conn, f"""
                SELECT a.*, u.display_name, u.username,
                       p.content AS post_content, p.post_type
                FROM moderation_appeals a
                JOIN users u ON u.id = a.user_id
                JOIN posts p ON p.id = a.post_id
                {where}
                ORDER BY a.created_at DESC
                LIMIT {ph} OFFSET {ph}
            """, (*params, limit, offset))
            total = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM moderation_appeals a {where}
            """, tuple(params))
        return {
            "appeals": [{
                "id": str(db._row_to_dict(r)["id"]),
                "post_id": str(db._row_to_dict(r)["post_id"]),
                "post_content": db._row_to_dict(r).get("post_content", "")[:200],
                "post_type": db._row_to_dict(r).get("post_type"),
                "user": {"display_name": db._row_to_dict(r).get("display_name"),
                         "username": db._row_to_dict(r).get("username")},
                "reason": db._row_to_dict(r).get("reason"),
                "status": db._row_to_dict(r)["status"],
                "reviewer_note": db._row_to_dict(r).get("reviewer_note"),
                "reviewed_at": str(db._row_to_dict(r)["reviewed_at"]) if db._row_to_dict(r).get("reviewed_at") else None,
                "created_at": str(db._row_to_dict(r)["created_at"]),
            } for r in rows],
            "total": db._row_to_dict(total)["c"] if total else 0,
            "page": page,
        }
    return await asyncio.to_thread(_query)


class AppealDecisionBody(BaseModel):
    note: str = Field("", max_length=500)


@router.post("/appeals/{appeal_id}/approve")
async def approve_appeal(appeal_id: str, body: AppealDecisionBody = AppealDecisionBody(), request: Request = None):
    appeal_id = validate_path_id(appeal_id, "appeal_id")
    admin_id = request.state.user["id"] if hasattr(request, "state") and hasattr(request.state, "user") else None
    def _query():
        ph = db._ph
        with db._conn() as conn:
            row = db._fetchone(conn, f"""
                SELECT post_id, user_id, status FROM moderation_appeals WHERE id::text = {ph}
            """, (appeal_id,))
            if not row:
                raise HTTPException(404, "Khiếu nại không tồn tại")
            rd = db._row_to_dict(row)
            if rd["status"] != "pending":
                raise HTTPException(400, f"Khiếu nại đã {rd['status']}")
            db._execute(conn, f"""
                UPDATE moderation_appeals
                SET status = 'approved', reviewer_note = {ph},
                    reviewer_id = {ph}::uuid, reviewed_at = NOW()
                WHERE id::text = {ph}
            """, (body.note.strip() or None, str(admin_id) if admin_id else None, appeal_id))
            db._execute(conn, f"""
                UPDATE posts SET moderation_status = 'approved' WHERE id::text = {ph}
            """, (str(rd["post_id"]),))
        try:
            create_notification(str(rd["user_id"]), "moderation",
                                "Khiếu nại được chấp nhận — bài viết đã được duyệt lại",
                                ref_type="post", ref_id=str(rd["post_id"]))
        except Exception:
            logger.exception("Failed to notify appeal approval %s", appeal_id)
    await asyncio.to_thread(_query)
    return {"success": True}


@router.post("/appeals/{appeal_id}/reject")
async def reject_appeal(appeal_id: str, body: AppealDecisionBody = AppealDecisionBody()):
    appeal_id = validate_path_id(appeal_id, "appeal_id")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            row = db._fetchone(conn, f"""
                SELECT post_id, user_id, status FROM moderation_appeals WHERE id::text = {ph}
            """, (appeal_id,))
            if not row:
                raise HTTPException(404, "Khiếu nại không tồn tại")
            rd = db._row_to_dict(row)
            if rd["status"] != "pending":
                raise HTTPException(400, f"Khiếu nại đã {rd['status']}")
            db._execute(conn, f"""
                UPDATE moderation_appeals
                SET status = 'rejected', reviewer_note = {ph}, reviewed_at = NOW()
                WHERE id::text = {ph}
            """, (body.note.strip() or None, appeal_id))
        try:
            note_msg = f" Lý do: {body.note.strip()}" if body.note.strip() else ""
            create_notification(str(rd["user_id"]), "moderation",
                                f"Khiếu nại không được chấp nhận.{note_msg}",
                                ref_type="post", ref_id=str(rd["post_id"]))
        except Exception:
            logger.exception("Failed to notify appeal rejection %s", appeal_id)
    await asyncio.to_thread(_query)
    return {"success": True}


# ── Admin Comment List ────────────────────────────────────────────────────

@router.get("/comments")
async def admin_list_comments(
    search: str = Query("", max_length=200),
    post_id: str = Query(None, max_length=50),
    page: int = Query(1, ge=1, le=1000),
    limit: int = Query(20, ge=1, le=100),
):
    """List comments for admin review with optional search and post filter."""
    ph = db._ph
    offset = (page - 1) * limit

    def _query():
        conditions = []
        params = []
        if search:
            search_esc = _escape_like(search)
            conditions.append(f"c.content ILIKE {ph} ESCAPE '\\'")
            params.append(f"%{search_esc}%")
        if post_id:
            conditions.append(f"c.post_id::text = {ph}")
            params.append(post_id)
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        count_params = list(params)
        params.extend([limit, offset])
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT c.id, c.content, c.post_id, c.parent_id, c.created_at,
                       u.display_name as author_name, u.id as user_id,
                       p.title as post_title, p.post_type
                FROM comments c
                JOIN users u ON u.id = c.user_id
                JOIN posts p ON p.id = c.post_id
                {where}
                ORDER BY c.created_at DESC
                LIMIT {ph} OFFSET {ph}
            """, tuple(params))
            total = db._fetchone(conn, f"SELECT COUNT(*) as c FROM comments c {where}", tuple(count_params))
        return {
            "comments": [db._row_to_dict(r) for r in rows],
            "total": db._row_to_dict(total)["c"] if total else 0,
            "page": page,
        }

    return await asyncio.to_thread(_query)


@router.delete("/comments/{comment_id}")
async def admin_delete_comment(comment_id: str, request: Request):
    """Admin force-delete a comment."""
    comment_id = validate_path_id(comment_id, "comment_id")
    ph = db._ph

    def _query():
        with db._conn() as conn:
            row = db._fetchone(conn, f"""
                DELETE FROM comments WHERE id::text = {ph}
                RETURNING id, post_id, user_id
            """, (comment_id,))
            if not row:
                raise HTTPException(404, "Bình luận không tồn tại")
            rd = db._row_to_dict(row)
            db._execute(conn, f"""
                UPDATE posts SET comment_count = GREATEST(comment_count - 1, 0)
                WHERE id = {ph}::uuid
            """, (str(rd["post_id"]),))
        _log_mod_action("comment", comment_id, "deleted")
        return rd

    result = await asyncio.to_thread(_query)
    return {"success": True, "deleted_comment": str(result["id"])}


@router.get("/content-stats")
async def content_stats(days: int = Query(30, ge=1, le=365)):
    ph = db._ph
    def _query():
        if not db._use_pg:
            return {"error": "Chức năng này yêu cầu Postgres"}
        with db._conn() as conn:
            by_type = db._fetchall(conn, f"""
                SELECT post_type, COUNT(*) as cnt
                FROM posts
                WHERE created_at > NOW() - INTERVAL '{days} days'
                  AND moderation_status = 'approved'
                GROUP BY post_type ORDER BY cnt DESC
            """, ())
            by_status = db._fetchall(conn, f"""
                SELECT moderation_status, COUNT(*) as cnt
                FROM posts
                WHERE created_at > NOW() - INTERVAL '{days} days'
                GROUP BY moderation_status ORDER BY cnt DESC
            """, ())
            avg_rating = db._fetchone(conn, f"""
                SELECT AVG(rating) as avg_r, COUNT(*) as cnt
                FROM posts
                WHERE post_type = 'review' AND rating IS NOT NULL
                  AND created_at > NOW() - INTERVAL '{days} days'
                  AND moderation_status = 'approved'
            """, ())
            total_comments = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM comments
                WHERE created_at > NOW() - INTERVAL '{days} days'
            """, ())
            daily_posts = db._fetchall(conn, f"""
                SELECT DATE(created_at) as day, COUNT(*) as cnt
                FROM posts
                WHERE created_at > NOW() - INTERVAL '{days} days'
                  AND moderation_status = 'approved'
                GROUP BY DATE(created_at) ORDER BY day
            """, ())
        ar = db._row_to_dict(avg_rating) if avg_rating else {}
        return {
            "period_days": days,
            "posts_by_type": {db._row_to_dict(r)["post_type"]: db._row_to_dict(r)["cnt"] for r in by_type},
            "posts_by_status": {db._row_to_dict(r)["moderation_status"]: db._row_to_dict(r)["cnt"] for r in by_status},
            "avg_review_rating": round(float(ar["avg_r"]), 2) if ar.get("avg_r") else None,
            "total_reviews_with_rating": ar.get("cnt", 0),
            "total_comments": db._row_to_dict(total_comments)["c"] if total_comments else 0,
            "daily_posts": [{"day": str(db._row_to_dict(r)["day"]), "count": db._row_to_dict(r)["cnt"]} for r in daily_posts],
        }
    return await asyncio.to_thread(_query)


@router.get("/analytics-overview")
async def analytics_overview(days: int = Query(0, ge=0, le=365)):
    """GĐ9.6: gói số liệu cho trang admin Analytics (1 call, đã auth qua require_admin).

    - popular: user hỏi gì nhiều · gaps: câu bot bí (backlog nội dung) · costs: chi phí LLM.
    - days: 0 = tất cả, 7/30/90 = lọc theo khoảng thời gian.
    """
    since = None
    if days > 0:
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
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


# ── Search analytics ──

@router.get("/search-analytics")
async def search_analytics(days: int = Query(7, ge=1, le=90)):
    search_log = Path(__file__).resolve().parent / "data" / "search_queries.jsonl"
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    def _read():
        if not search_log.exists():
            return {"top_queries": [], "zero_results": [], "total_searches": 0, "period_days": days}
        queries = {}
        zero_result = {}
        total = 0
        for line in search_log.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            if r.get("ts", "") < cutoff:
                continue
            total += 1
            q = r.get("q", "").strip().lower()
            if not q:
                continue
            queries[q] = queries.get(q, 0) + 1
            if r.get("results", 0) == 0:
                zero_result[q] = zero_result.get(q, 0) + 1
        top = sorted(queries.items(), key=lambda x: x[1], reverse=True)[:30]
        zeros = sorted(zero_result.items(), key=lambda x: x[1], reverse=True)[:20]
        return {
            "top_queries": [{"query": q, "count": c} for q, c in top],
            "zero_results": [{"query": q, "count": c} for q, c in zeros],
            "total_searches": total,
            "period_days": days,
        }
    return await asyncio.to_thread(_read)


@router.get("/reports")
async def get_reports(
    status: str = Query("pending", pattern="^(pending|resolved|dismissed)$"),
    target_type: str = Query(None, pattern="^(post|comment|user|entity)$"),
    reporter_id: str = Query(None, max_length=64),
    target_user_id: str = Query(None, max_length=64),
    page: int = Query(1, ge=1, le=1000),
    limit: int = Query(20, ge=1, le=100),
):
    if reporter_id:
        reporter_id = validate_path_id(reporter_id, "reporter_id")
    if target_user_id:
        target_user_id = validate_path_id(target_user_id, "target_user_id")
    ph = db._ph
    offset = (page - 1) * limit
    def _query():
        with db._conn() as conn:
            where = f"r.status = {ph}"
            params = [status]
            if target_type:
                where += f" AND r.target_type = {ph}"
                params.append(target_type)
            if reporter_id:
                where += f" AND r.reporter_id::text = {ph}"
                params.append(reporter_id)
            if target_user_id:
                where += f" AND r.target_type = 'user' AND r.target_id = {ph}"
                params.append(target_user_id)
            params.extend([limit, offset])
            rows = db._fetchall(conn, f"""
                SELECT r.id, r.target_type, r.target_id, r.reason, r.details,
                       r.reporter_id, r.status, r.created_at, u.display_name as reporter_name
                FROM reports r
                JOIN users u ON u.id = r.reporter_id
                WHERE {where}
                ORDER BY r.created_at DESC
                LIMIT {ph} OFFSET {ph}
            """, tuple(params))
            total = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM reports r WHERE {where}
            """, tuple(params[:-2]))
        return {
            "reports": [db._row_to_dict(r) for r in rows],
            "total": db._row_to_dict(total)["c"] if total else 0,
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
            cur = db._execute(conn, f"UPDATE reports SET status = {ph} WHERE id::text IN ({placeholders})",
                              (status, *body.ids))
            return cur.rowcount
    updated = await asyncio.to_thread(_query)
    return {"success": True, "updated": updated, "requested": len(body.ids)}


@router.post("/reports/{report_id}/resolve")
async def resolve_report(report_id: str):
    report_id = validate_path_id(report_id, "report_id")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            cur = db._execute(conn, f"""
                UPDATE reports SET status = 'resolved' WHERE id::text = {ph}
            """, (report_id,))
            if cur.rowcount == 0:
                raise HTTPException(404, "Báo cáo không tồn tại")
    await asyncio.to_thread(_query)
    return {"success": True}


@router.post("/reports/{report_id}/dismiss")
async def dismiss_report(report_id: str):
    report_id = validate_path_id(report_id, "report_id")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            cur = db._execute(conn, f"""
                UPDATE reports SET status = 'dismissed' WHERE id::text = {ph}
            """, (report_id,))
            if cur.rowcount == 0:
                raise HTTPException(404, "Báo cáo không tồn tại")
    await asyncio.to_thread(_query)
    return {"success": True}


# GĐ13.6f: báo-sai thông tin (facility/entity) & báo nội dung ẩn danh — kênh nhẹ JSONL
# (KHÔNG cần đăng nhập, không DB), tách khỏi UGC `reports` (Postgres) ở trên.
_INFO_REPORTS_FILE = Path(__file__).resolve().parent / "data" / "reports.jsonl"
from notifications import create_notification
from public_api import _jsonl_lock as _info_reports_lock


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
    method: Optional[str] = Query(None, max_length=10),
    q: Optional[str] = Query(None, max_length=200),
    date_from: Optional[str] = Query(None, max_length=20),
    date_to: Optional[str] = Query(None, max_length=20),
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
        with _info_reports_lock:
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
    return {"success": True, "ts": body.ts, "new_status": body.status}


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
            logger.debug("Cost overview: autonomous_budget unavailable", exc_info=True)
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
            logger.debug("Cost overview: cost_tracker unavailable", exc_info=True)
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
            logger.warning("Failed to parse info reports file: %s", _INFO_REPORTS_FILE)
        ctx.append(f"- Báo cáo sai thông tin: {len(reports)}")
        for r in reports[-5:]:
            ctx.append(f"    · [{r.get('target_type')}] {r.get('target_id')}: {str(r.get('reason', ''))[:60]}")
        raw = "\n".join(ctx) or "(không có dữ liệu)"

        try:
            from llm_config import get_client, get_model_mini
            resp = get_client().chat.completions.create(
                model=get_model_mini(), temperature=0.3, max_tokens=400,
                messages=[
                    {"role": "system", "content": "Bạn là trợ lý quản trị của vinhlong360. Dựa trên tình hình, đề xuất TỐI ĐA 3 việc ưu tiên xử lý, ngắn gọn, tiếng Việt, có thứ tự."},
                    {"role": "user", "content": f"Tình hình hiện tại:\n{raw}\n\nĐề xuất việc ưu tiên:"},
                ])
            return {"ok": True, "suggestion": resp.choices[0].message.content, "context": raw}
        except Exception as e:  # noqa: BLE001 - LLM down/budget → vẫn trả context để admin tự xử
            return {"ok": False, "suggestion": None, "context": raw,
                    "note": "LLM không khả dụng — xem tình hình thô bên dưới."}
    return await asyncio.to_thread(_query)


@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1, le=1000),
    limit: int = Query(20, ge=1, le=100),
    search: str = Query("", max_length=100),
    role_filter: Optional[str] = Query(None, pattern="^(user|moderator|admin)$"),
):
    ph = db._ph
    offset = (page - 1) * limit
    conditions = ["1=1"]
    params = []
    if search:
        search_esc = _escape_like(search)
        conditions.append(f"(display_name ILIKE {ph} ESCAPE '\\' OR phone LIKE {ph} ESCAPE '\\')")
        params.extend([f"%{search_esc}%", f"%{search_esc}%"])
    if role_filter:
        conditions.append(f"COALESCE(role, 'user') = {ph}")
        params.append(role_filter)
    where = " AND ".join(conditions)
    count_params = list(params)
    params.extend([limit, offset])
    def _query():
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT u.id, u.phone, u.display_name, u.role, u.is_active, u.created_at,
                       (SELECT COUNT(*) FROM posts p WHERE p.user_id = u.id AND p.moderation_status = 'approved') as post_count
                FROM users u WHERE {where}
                ORDER BY u.created_at DESC
                LIMIT {ph} OFFSET {ph}
            """, params)
            total = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM users WHERE {where}
            """, count_params)
        role_counts = {}
        try:
            with db._conn() as conn2:
                rc_rows = db._fetchall(conn2, "SELECT COALESCE(role, 'user') as role, COUNT(*) as c FROM users GROUP BY COALESCE(role, 'user')", ())
            for rc in rc_rows:
                d = db._row_to_dict(rc)
                role_counts[d["role"]] = d["c"]
        except Exception:
            logger.debug("Role counts query failed", exc_info=True)
        return {
            "users": [{
                "id": str(r["id"]),
                "phone": _mask(r.get("phone", "")),
                "display_name": r.get("display_name", ""),
                "role": r.get("role", "user"),
                "is_active": r.get("is_active", True),
                "created_at": str(r.get("created_at", "")),
                "post_count": r.get("post_count", 0),
            } for r in [db._row_to_dict(row) for row in rows]],
            "total": db._row_to_dict(total)["c"] if total else 0,
            "role_counts": role_counts,
        }
    return await asyncio.to_thread(_query)


@router.get("/users/{user_id}")
async def admin_user_detail(user_id: str):
    """Comprehensive user detail for admin panel."""
    user_id = validate_path_id(user_id, "user_id")
    ph = db._ph

    def _query():
        with db._conn() as conn:
            user = db._fetchone(conn, f"""
                SELECT id, phone, display_name, avatar_url, cover_url, bio,
                       username, role, is_active, created_at
                FROM users WHERE id::text = {ph}
            """, (user_id,))
            if not user:
                raise HTTPException(404, "Người dùng không tồn tại")
            ud = db._row_to_dict(user)
            ud["phone"] = _mask(ud.get("phone", ""))

            post_stats = db._fetchone(conn, f"""
                SELECT COUNT(*) as total,
                       COUNT(*) FILTER (WHERE moderation_status = 'approved') as approved,
                       COUNT(*) FILTER (WHERE moderation_status = 'rejected') as rejected,
                       COUNT(*) FILTER (WHERE moderation_status = 'pending') as pending,
                       COUNT(*) FILTER (WHERE post_type = 'review') as reviews,
                       COUNT(*) FILTER (WHERE post_type = 'question') as questions
                FROM posts WHERE user_id::text = {ph}
            """, (user_id,))
            ps = db._row_to_dict(post_stats) if post_stats else {}

            comment_count = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM comments WHERE user_id::text = {ph}
            """, (user_id,))

            follow_stats = db._fetchone(conn, f"""
                SELECT
                    (SELECT COUNT(*) FROM follows WHERE follower_id::text = {ph} AND target_type = 'user') as following,
                    (SELECT COUNT(*) FROM follows WHERE target_id = {ph} AND target_type = 'user') as followers
            """, (user_id, user_id))
            fs = db._row_to_dict(follow_stats) if follow_stats else {}

            session_count = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM user_sessions WHERE user_id = {ph}::uuid
            """, (user_id,))

            report_count = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM reports WHERE reporter_id::text = {ph}
            """, (user_id,))

            reported_count = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM reports WHERE target_type = 'user' AND target_id = {ph}
            """, (user_id,))

            block_count = db._fetchone(conn, f"""
                SELECT
                    (SELECT COUNT(*) FROM blocks WHERE blocker_id::text = {ph}) as blocking,
                    (SELECT COUNT(*) FROM blocks WHERE blocked_id::text = {ph}) as blocked_by
            """, (user_id, user_id))
            blk = db._row_to_dict(block_count) if block_count else {}

            mute_count = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM user_mutes WHERE user_id::text = {ph}
            """, (user_id,))

            reputation = db._fetchone(conn, f"""
                SELECT reputation_score FROM users WHERE id::text = {ph}
            """, (user_id,))
            rep = db._row_to_dict(reputation).get("reputation_score", 0) if reputation else 0

            last_login = None
            try:
                ll = db._fetchone(conn, f"""
                    SELECT created_at FROM login_history
                    WHERE user_id = {ph}::uuid AND success = TRUE
                    ORDER BY created_at DESC LIMIT 1
                """, (user_id,))
                if ll:
                    last_login = str(db._row_to_dict(ll)["created_at"])
            except Exception:
                pass

            last_post = db._fetchone(conn, f"""
                SELECT created_at FROM posts
                WHERE user_id::text = {ph} AND moderation_status = 'approved'
                ORDER BY created_at DESC LIMIT 1
            """, (user_id,))

        return {
            "user": ud,
            "stats": {
                "posts": ps,
                "comments": db._row_to_dict(comment_count)["c"] if comment_count else 0,
                "following": fs.get("following", 0),
                "followers": fs.get("followers", 0),
                "active_sessions": db._row_to_dict(session_count)["c"] if session_count else 0,
                "reports_filed": db._row_to_dict(report_count)["c"] if report_count else 0,
                "reports_against": db._row_to_dict(reported_count)["c"] if reported_count else 0,
                "blocking": blk.get("blocking", 0),
                "blocked_by": blk.get("blocked_by", 0),
                "muted_users": db._row_to_dict(mute_count)["c"] if mute_count else 0,
                "reputation_score": rep,
                "last_login": last_login,
                "last_post_at": str(db._row_to_dict(last_post)["created_at"]) if last_post else None,
            },
        }

    return await asyncio.to_thread(_query)


@router.post("/users/{user_id}/ban")
async def ban_user(user_id: str, request: Request):
    user_id = validate_path_id(user_id, "user_id")
    admin_user = await get_current_user(request)
    if admin_user and str(admin_user["id"]) == user_id:
        raise HTTPException(400, "Không thể tự ban chính mình")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            target = db._fetchone(conn, f"SELECT is_active FROM users WHERE id::text = {ph}", (user_id,))
            if not target:
                raise HTTPException(404, "Không tìm thấy người dùng")
            db._execute(conn, f"""
                UPDATE users SET is_active = FALSE WHERE id::text = {ph}
            """, (user_id,))
            db._execute(conn, f"""
                DELETE FROM user_sessions WHERE user_id = {ph}::uuid
            """, (user_id,))
    await asyncio.to_thread(_query)
    _log_mod_action("user", user_id, "ban")
    return {"success": True}


@router.post("/users/{user_id}/unban")
async def unban_user(user_id: str):
    user_id = validate_path_id(user_id, "user_id")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            target = db._fetchone(conn, f"SELECT is_active FROM users WHERE id::text = {ph}", (user_id,))
            if not target:
                raise HTTPException(404, "Không tìm thấy người dùng")
            td = db._row_to_dict(target)
            if td["is_active"]:
                raise HTTPException(400, "Người dùng không bị ban")
            db._execute(conn, f"""
                UPDATE users SET is_active = TRUE WHERE id::text = {ph}
            """, (user_id,))
    await asyncio.to_thread(_query)
    _log_mod_action("user", user_id, "unban")
    return {"success": True}


class BulkUserAction(BaseModel):
    user_ids: list[str] = Field(..., min_length=1, max_length=50)
    reason: str = Field("", max_length=500)


@router.post("/users/bulk-ban")
async def bulk_ban_users(body: BulkUserAction, request: Request):
    from ratelimit import check_rate
    check_rate("admin:bulk-ban", 5, 60, "Thao tác quá nhanh")
    admin_user = await get_current_user(request)
    admin_id = str(admin_user["id"]) if admin_user else None
    ids = [validate_path_id(uid, "user_id") for uid in body.user_ids]
    if admin_id and admin_id in ids:
        raise HTTPException(400, "Không thể tự ban chính mình")
    def _query():
        ph = db._ph
        banned = []
        with db._conn() as conn:
            for uid in ids:
                target = db._fetchone(conn, f"SELECT is_active FROM users WHERE id::text = {ph}", (uid,))
                if not target:
                    continue
                db._execute(conn, f"UPDATE users SET is_active = FALSE WHERE id::text = {ph}", (uid,))
                db._execute(conn, f"DELETE FROM user_sessions WHERE user_id = {ph}::uuid", (uid,))
                banned.append(uid)
        return banned
    banned = await asyncio.to_thread(_query)
    for uid in banned:
        _log_mod_action("user", uid, "ban", body.reason or None)
    return {"success": True, "banned_count": len(banned), "banned_ids": banned}


@router.post("/users/bulk-unban")
async def bulk_unban_users(body: BulkUserAction):
    from ratelimit import check_rate
    check_rate("admin:bulk-unban", 5, 60, "Thao tác quá nhanh")
    ids = [validate_path_id(uid, "user_id") for uid in body.user_ids]
    def _query():
        ph = db._ph
        unbanned = []
        with db._conn() as conn:
            for uid in ids:
                target = db._fetchone(conn, f"SELECT is_active FROM users WHERE id::text = {ph}", (uid,))
                if not target:
                    continue
                td = db._row_to_dict(target)
                if td["is_active"]:
                    continue
                db._execute(conn, f"UPDATE users SET is_active = TRUE WHERE id::text = {ph}", (uid,))
                unbanned.append(uid)
        return unbanned
    unbanned = await asyncio.to_thread(_query)
    for uid in unbanned:
        _log_mod_action("user", uid, "unban", body.reason or None)
    return {"success": True, "unbanned_count": len(unbanned), "unbanned_ids": unbanned}


@router.post("/users/{user_id}/role")
async def set_user_role(user_id: str, role: str = Query(..., pattern="^(user|moderator|admin)$")):
    user_id = validate_path_id(user_id, "user_id")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            target = db._fetchone(conn, f"SELECT is_active FROM users WHERE id::text = {ph}", (user_id,))
            if not target:
                raise HTTPException(404, "Không tìm thấy người dùng")
            td = db._row_to_dict(target)
            if not td["is_active"]:
                raise HTTPException(400, "Không thể gán quyền cho tài khoản đã bị ban")
            db._execute(conn, f"""
                UPDATE users SET role = {ph} WHERE id::text = {ph}
            """, (role, user_id))
    await asyncio.to_thread(_query)
    _log_mod_action("user", user_id, f"set_role:{role}")
    return {"success": True}


class AdminUserNote(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


@router.post("/users/{user_id}/notes")
async def add_user_note(user_id: str, body: AdminUserNote, request: Request):
    """Admin: add internal note to a user profile."""
    user_id = validate_path_id(user_id, "user_id")
    admin_id = str(request.state.user["id"]) if hasattr(request, "state") and hasattr(request.state, "user") else None

    def _query():
        ph = db._ph
        with db._conn() as conn:
            row = db._fetchone(conn, f"SELECT id FROM users WHERE id::text = {ph}", (user_id,))
            if not row:
                raise HTTPException(404, "Người dùng không tồn tại")
            note = db._fetchone(conn, f"""
                INSERT INTO admin_user_notes (user_id, admin_id, content)
                VALUES ({ph}::uuid, {ph}::uuid, {ph}) RETURNING id, created_at
            """, (user_id, admin_id, body.content.strip()))
            return db._row_to_dict(note)

    result = await asyncio.to_thread(_query)
    return {"note": {"id": str(result["id"]), "created_at": str(result["created_at"])}}


@router.get("/users/{user_id}/notes")
async def get_user_notes(user_id: str, limit: int = Query(50, ge=1, le=200)):
    """Admin: list internal notes for a user."""
    user_id = validate_path_id(user_id, "user_id")

    def _query():
        ph = db._ph
        with db._conn() as conn:
            return db._fetchall(conn, f"""
                SELECT n.id, n.content, n.created_at, u.display_name as admin_name
                FROM admin_user_notes n JOIN users u ON u.id = n.admin_id
                WHERE n.user_id = {ph}::uuid ORDER BY n.created_at DESC LIMIT {ph}
            """, (user_id, limit))

    rows = await asyncio.to_thread(_query)
    notes = []
    for r in rows:
        d = db._row_to_dict(r)
        notes.append({"id": str(d["id"]), "content": d["content"],
                       "admin_name": d.get("admin_name"), "created_at": str(d["created_at"])})
    return {"notes": notes}


@router.delete("/users/{user_id}/notes/{note_id}")
async def delete_user_note(user_id: str, note_id: str):
    """Admin: delete an internal note."""
    user_id = validate_path_id(user_id, "user_id")
    note_id = validate_path_id(note_id, "note_id")

    def _query():
        ph = db._ph
        with db._conn() as conn:
            row = db._fetchone(conn, f"DELETE FROM admin_user_notes WHERE id = {ph}::uuid AND user_id = {ph}::uuid RETURNING 1",
                               (note_id, user_id))
            if not row:
                raise HTTPException(404, "Ghi chú không tồn tại")

    await asyncio.to_thread(_query)
    return {"success": True}


# ── Admin: user mutes + reactions visibility ────────────────────────

@router.get("/users/{user_id}/mutes")
async def admin_user_mutes(user_id: str, limit: int = Query(50, ge=1, le=200)):
    user_id = validate_path_id(user_id, "user_id")
    ph = db._ph
    def _query():
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT m.muted_id, u.display_name, u.username, m.created_at
                FROM user_mutes m JOIN users u ON u.id = m.muted_id
                WHERE m.user_id = {ph}::uuid
                ORDER BY m.created_at DESC LIMIT {ph}
            """, (user_id, limit))
            return [db._row_to_dict(r) for r in rows]
    mutes = await asyncio.to_thread(_query)
    return {"mutes": [{"muted_id": str(m["muted_id"]), "display_name": m.get("display_name"),
                        "username": m.get("username"), "created_at": str(m["created_at"])} for m in mutes],
            "total": len(mutes)}


@router.get("/users/{user_id}/reactions")
async def admin_user_reactions(user_id: str, limit: int = Query(100, ge=1, le=500)):
    user_id = validate_path_id(user_id, "user_id")
    ph = db._ph
    def _query():
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT r.reaction_type, COUNT(*) as count
                FROM post_reactions r WHERE r.user_id = {ph}::uuid
                GROUP BY r.reaction_type
            """, (user_id,))
            summary = {db._row_to_dict(r)["reaction_type"]: int(db._row_to_dict(r)["count"]) for r in rows}
            recent = db._fetchall(conn, f"""
                SELECT r.post_id, r.reaction_type, r.created_at, p.content
                FROM post_reactions r LEFT JOIN posts p ON p.id = r.post_id
                WHERE r.user_id = {ph}::uuid
                ORDER BY r.created_at DESC LIMIT {ph}
            """, (user_id, limit))
            return summary, [db._row_to_dict(r) for r in recent]
    summary, recent = await asyncio.to_thread(_query)
    return {"summary": summary, "total": sum(summary.values()),
            "recent": [{"post_id": str(r["post_id"]), "reaction_type": r["reaction_type"],
                        "created_at": str(r["created_at"]),
                        "content_preview": (r.get("content") or "")[:100]} for r in recent]}


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
        logger.debug("Moderation log write failed", exc_info=True)


# ══════════════════════════════════════════════════
#  SITE SETTINGS — CMS admin endpoints
# ══════════════════════════════════════════════════

@router.get("/site-settings")
async def admin_get_all_settings():
    """All settings grouped by category (for admin overview)."""
    if not db._use_pg:
        raise HTTPException(503, detail="Cài đặt site yêu cầu PostgreSQL")
    return await asyncio.to_thread(site_settings.get_all_grouped)


_SETTING_KEY_RE = re.compile(r"^[a-zA-Z0-9_./:-]{1,200}$")

@router.get("/site-settings/{category}")
async def admin_get_settings_by_category(category: str):
    """Settings for a specific category (for admin editor page)."""
    if not _SETTING_KEY_RE.match(category):
        raise HTTPException(400, detail="Tên danh mục không hợp lệ")
    if not db._use_pg:
        raise HTTPException(503, detail="Cài đặt site yêu cầu PostgreSQL")
    def _query():
        items = site_settings.get_by_category(category)
        if not items:
            raise HTTPException(404, detail=f"Không tìm thấy cài đặt cho danh mục '{category}'")
        return {"category": category, "settings": items}
    return await asyncio.to_thread(_query)


class SettingUpdate(BaseModel):
    value: object = Field(..., description="New value for the setting")


@router.put("/site-settings/{key:path}")
async def admin_update_setting(key: str, body: SettingUpdate):
    """Update a single setting value."""
    if not _SETTING_KEY_RE.match(key):
        raise HTTPException(400, detail="Tên cài đặt không hợp lệ")
    if not db._use_pg:
        raise HTTPException(503, detail="Cài đặt site yêu cầu PostgreSQL")
    def _query():
        ok = site_settings.upsert(key, body.value)
        if not ok:
            raise HTTPException(500, detail="Không thể cập nhật cài đặt")
    await asyncio.to_thread(_query)
    return {"success": True, "key": key}


class BulkSettingUpdate(BaseModel):
    updates: dict[str, object] = Field(..., description="Map of key→value to update")


@router.post("/site-settings/bulk")
async def admin_bulk_update_settings(body: BulkSettingUpdate):
    """Batch update multiple settings at once."""
    if not db._use_pg:
        raise HTTPException(503, detail="Cài đặt site yêu cầu PostgreSQL")
    count = await asyncio.to_thread(site_settings.bulk_upsert, body.updates)
    return {"success": True, "updated": count}


@router.post("/site-settings/reset/{category}")
async def admin_reset_category(category: str):
    """Reset all settings in a category to their defaults."""
    if not _SETTING_KEY_RE.match(category):
        raise HTTPException(400, detail="Tên danh mục không hợp lệ")
    if not db._use_pg:
        raise HTTPException(503, detail="Cài đặt site yêu cầu PostgreSQL")
    def _query():
        from seed_site_settings import DEFAULTS
        return site_settings.reset_category(category, DEFAULTS)
    count = await asyncio.to_thread(_query)
    return {"success": True, "reset": count}


# ══════════════════════════════════════════════════
#  LLM CONFIG — runtime AI configuration
# ══════════════════════════════════════════════════

@router.get("/llm-config")
async def admin_get_llm_config():
    """Current LLM configuration (API key masked)."""
    import llm_config
    return await asyncio.to_thread(llm_config.get_status)


class LLMConfigUpdate(BaseModel):
    base_url: str = Field(..., min_length=1, max_length=500)
    api_key: str = Field(..., min_length=1, max_length=500)
    model: str = Field(..., min_length=1, max_length=100)
    model_mini: str = Field(..., min_length=1, max_length=100)


@router.put("/llm-config")
async def admin_update_llm_config(body: LLMConfigUpdate):
    """Update LLM config. Validates with a test API call before applying."""
    import llm_config
    try:
        result = await asyncio.to_thread(
            llm_config.update_config,
            body.base_url, body.api_key, body.model, body.model_mini,
        )
    except ValueError as e:
        logger.warning("LLM config update rejected: %s", e)
        raise HTTPException(400, detail="Cấu hình LLM không hợp lệ")
    return {"success": True, "config": result}


@router.post("/llm-config/reset")
async def admin_reset_llm_config():
    """Reset LLM config to environment variables."""
    import llm_config
    result = await asyncio.to_thread(llm_config.reset_to_env)
    return {"success": True, "config": result}


@router.post("/notifications/cleanup")
async def admin_cleanup_notifications(days: int = Query(90, ge=7, le=365)):
    """Delete read notifications older than N days."""
    if not db._use_pg:
        raise HTTPException(503, detail="Thông báo yêu cầu PostgreSQL")
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


@router.post("/cleanup-orphan-refs")
async def admin_cleanup_orphan_entity_refs():
    """Remove UGC records referencing entity IDs that no longer exist in knowledge base."""
    if not db._use_pg:
        raise HTTPException(503, detail="Chức năng này yêu cầu PostgreSQL")
    valid_ids = {e["id"] for e in db.list_entities(limit=10000, offset=0)}
    if not valid_ids:
        return {"success": True, "cleaned": {}}

    ph = db._ph
    tables = ["saved_entities", "user_visits", "event_rsvp"]
    cleaned = {}

    def _cleanup():
        with db._conn() as conn:
            for table in tables:
                try:
                    rows = db._fetchall(conn, f"SELECT DISTINCT entity_id FROM {table}", ())
                    orphan_ids = [r[0] if not hasattr(r, 'keys') else db._row_to_dict(r)["entity_id"]
                                  for r in rows
                                  if (r[0] if not hasattr(r, 'keys') else db._row_to_dict(r)["entity_id"]) not in valid_ids]
                    if orphan_ids:
                        placeholders = ",".join(ph for _ in orphan_ids)
                        cur = db._execute(conn, f"DELETE FROM {table} WHERE entity_id IN ({placeholders})", tuple(orphan_ids))
                        cleaned[table] = cur.rowcount if cur else 0
                    else:
                        cleaned[table] = 0
                except Exception:
                    cleaned[table] = -1

    await asyncio.to_thread(_cleanup)
    return {"success": True, "cleaned": cleaned}


# ── Entity claims admin (U-30: approve/reject business claims) ────────

@router.get("/claims")
async def list_claims(
    status: str = Query("pending", max_length=20),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0, le=10000),
):
    """U-30: List entity claims for admin review."""
    valid_statuses = ("pending", "approved", "rejected", "all")
    if status not in valid_statuses:
        return JSONResponse(status_code=422, content={"error": "invalid_status", "valid": list(valid_statuses)})

    ph = db._ph

    def _query():
        where = "" if status == "all" else f"WHERE c.status = {ph}"
        params = [] if status == "all" else [status]
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT c.id, c.entity_id, c.business_name, c.contact_phone,
                       c.contact_email, c.evidence, c.status, c.created_at,
                       c.reviewed_at, c.rejection_reason,
                       u.display_name as claimant_name, u.phone as claimant_phone
                FROM entity_claims c
                JOIN users u ON u.id = c.claimant_id
                {where}
                ORDER BY c.created_at DESC
                LIMIT {ph} OFFSET {ph}
            """, tuple(params + [limit, offset]))
            total_row = db._fetchone(conn, f"""
                SELECT COUNT(*) as cnt FROM entity_claims c {where}
            """, tuple(params))
        total = db._row_to_dict(total_row)["cnt"] if total_row else 0
        return {
            "claims": [db._row_to_dict(r) for r in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    return await asyncio.to_thread(_query)


class ClaimDecisionBody(BaseModel):
    reason: str = Field("", max_length=1000)


@router.post("/claims/{claim_id}/approve")
async def approve_claim(claim_id: str, request: Request):
    """U-30: Approve an entity claim."""
    claim_id = validate_path_id(claim_id, "claim_id")
    ph = db._ph
    admin_user = request.state.admin_user

    def _approve():
        with db._conn() as conn:
            row = db._fetchone(conn, f"SELECT id, status, claimant_id, entity_id FROM entity_claims WHERE id = {ph}::uuid", (claim_id,))
            if not row:
                return {"error": "not_found"}
            claim = db._row_to_dict(row)
            if claim["status"] != "pending":
                return {"error": "not_pending", "current_status": claim["status"]}
            db._execute(conn, f"""
                UPDATE entity_claims SET status = 'approved', reviewer_id = {ph}::uuid, reviewed_at = NOW()
                WHERE id = {ph}::uuid
            """, (str(admin_user["id"]), claim_id))
        return {"ok": True, "claimant_id": str(claim["claimant_id"]), "entity_id": claim.get("entity_id")}

    result = await asyncio.to_thread(_approve)
    if "error" in result:
        code = 404 if result["error"] == "not_found" else 409
        return JSONResponse(status_code=code, content=result)
    if result.get("claimant_id"):
        def _notify():
            create_notification(
                result["claimant_id"], "claim_approved",
                "Yêu cầu xác nhận doanh nghiệp của bạn đã được duyệt!",
                ref_type="entity", ref_id=result.get("entity_id", ""),
            )
        await asyncio.to_thread(_notify)
    return {"ok": True}


@router.post("/claims/{claim_id}/reject")
async def reject_claim(claim_id: str, body: ClaimDecisionBody, request: Request):
    """U-30: Reject an entity claim with optional reason."""
    claim_id = validate_path_id(claim_id, "claim_id")
    ph = db._ph
    admin_user = request.state.admin_user

    def _reject():
        with db._conn() as conn:
            row = db._fetchone(conn, f"SELECT id, status, claimant_id, entity_id FROM entity_claims WHERE id = {ph}::uuid", (claim_id,))
            if not row:
                return {"error": "not_found"}
            claim = db._row_to_dict(row)
            if claim["status"] != "pending":
                return {"error": "not_pending", "current_status": claim["status"]}
            db._execute(conn, f"""
                UPDATE entity_claims SET status = 'rejected', reviewer_id = {ph}::uuid,
                    reviewed_at = NOW(), rejection_reason = {ph}
                WHERE id = {ph}::uuid
            """, (str(admin_user["id"]), body.reason, claim_id))
        return {"ok": True, "claimant_id": str(claim["claimant_id"]), "entity_id": claim.get("entity_id")}

    result = await asyncio.to_thread(_reject)
    if "error" in result:
        code = 404 if result["error"] == "not_found" else 409
        return JSONResponse(status_code=code, content=result)
    if result.get("claimant_id"):
        def _notify():
            create_notification(
                result["claimant_id"], "claim_rejected",
                "Yêu cầu xác nhận doanh nghiệp của bạn chưa được duyệt.",
                ref_type="entity", ref_id=result.get("entity_id", ""),
            )
        await asyncio.to_thread(_notify)
    return {"ok": True}


# ── Announcements (system notices for users) ────────────────────────────

class AnnouncementCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field("", max_length=5000)
    type: str = Field("info", max_length=20)
    priority: int = Field(0, ge=0, le=100)
    starts_at: Optional[str] = None
    expires_at: Optional[str] = None

    @field_validator("type")
    @classmethod
    def _validate_type(cls, v):
        allowed = ("info", "warning", "maintenance", "update")
        if v not in allowed:
            raise ValueError(f"type must be one of {allowed}")
        return v


class AnnouncementUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, max_length=5000)
    type: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=0, le=100)
    starts_at: Optional[str] = None
    expires_at: Optional[str] = None

    @field_validator("type")
    @classmethod
    def _validate_type(cls, v):
        if v is None:
            return v
        allowed = ("info", "warning", "maintenance", "update")
        if v not in allowed:
            raise ValueError(f"type must be one of {allowed}")
        return v


@router.get("/announcements")
async def list_announcements(
    is_active: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0, le=10000),
):
    ph = db._ph

    def _query():
        where_clauses = []
        params = []
        if is_active is not None:
            where_clauses.append(f"is_active = {ph}")
            params.append(is_active)
        where = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT id, title, content, type, is_active, priority,
                       starts_at, expires_at, created_by, created_at, updated_at
                FROM announcements
                {where}
                ORDER BY priority DESC, created_at DESC
                LIMIT {ph} OFFSET {ph}
            """, tuple(params + [limit, offset]))
            total_row = db._fetchone(conn, f"SELECT COUNT(*) as cnt FROM announcements {where}", tuple(params))
        total = db._row_to_dict(total_row)["cnt"] if total_row else 0
        return {
            "announcements": [db._row_to_dict(r) for r in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    return await asyncio.to_thread(_query)


@router.post("/announcements")
async def create_announcement(body: AnnouncementCreate, request: Request):
    ph = db._ph
    admin_user = request.state.admin_user

    def _query():
        with db._conn() as conn:
            row = db._fetchone(conn, f"""
                INSERT INTO announcements (title, content, type, priority, starts_at, expires_at, created_by)
                VALUES ({ph}, {ph}, {ph}, {ph},
                        COALESCE({ph}::timestamptz, NOW()),
                        {ph}::timestamptz,
                        {ph}::uuid)
                RETURNING id, title, type, is_active, priority, starts_at, expires_at, created_at
            """, (
                body.title.strip(), body.content.strip(), body.type,
                body.priority, body.starts_at, body.expires_at,
                str(admin_user["id"]),
            ))
        return db._row_to_dict(row) if row else None

    result = await asyncio.to_thread(_query)
    return {"success": True, "announcement": result}


@router.put("/announcements/{announcement_id}")
async def update_announcement(announcement_id: str, body: AnnouncementUpdate):
    announcement_id = validate_path_id(announcement_id, "announcement_id")
    ph = db._ph

    def _query():
        sets = []
        params = []
        if body.title is not None:
            sets.append(f"title = {ph}")
            params.append(body.title.strip())
        if body.content is not None:
            sets.append(f"content = {ph}")
            params.append(body.content.strip())
        if body.type is not None:
            sets.append(f"type = {ph}")
            params.append(body.type)
        if body.is_active is not None:
            sets.append(f"is_active = {ph}")
            params.append(body.is_active)
        if body.priority is not None:
            sets.append(f"priority = {ph}")
            params.append(body.priority)
        if body.starts_at is not None:
            sets.append(f"starts_at = {ph}::timestamptz")
            params.append(body.starts_at)
        if body.expires_at is not None:
            sets.append(f"expires_at = {ph}::timestamptz")
            params.append(body.expires_at)
        if not sets:
            raise HTTPException(400, "Không có thay đổi")
        sets.append("updated_at = NOW()")
        params.append(announcement_id)
        with db._conn() as conn:
            row = db._fetchone(conn, f"""
                UPDATE announcements SET {", ".join(sets)}
                WHERE id::text = {ph}
                RETURNING id, title, content, type, is_active, priority, starts_at, expires_at, updated_at
            """, tuple(params))
        if not row:
            raise HTTPException(404, "Thông báo không tồn tại")
        return db._row_to_dict(row)

    result = await asyncio.to_thread(_query)
    return {"success": True, "announcement": result}


@router.delete("/announcements/{announcement_id}")
async def delete_announcement(announcement_id: str):
    announcement_id = validate_path_id(announcement_id, "announcement_id")
    ph = db._ph

    def _query():
        with db._conn() as conn:
            row = db._fetchone(conn, f"""
                DELETE FROM announcements WHERE id::text = {ph} RETURNING id
            """, (announcement_id,))
        if not row:
            raise HTTPException(404, "Thông báo không tồn tại")
        return True

    await asyncio.to_thread(_query)
    return {"success": True}
