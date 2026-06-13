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

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request, Depends
from pydantic import BaseModel, Field, field_validator

import data_quality
import knowledge
import analytics
from database import db

try:
    from cost_tracker import get_cost_report as _get_cost_report
    _HAS_COST = True
except Exception:  # noqa: BLE001
    _HAS_COST = False
from auth_middleware import get_current_user
from middleware import admin_limiter, verify_admin_key, get_client_ip


def _sync_kb():
    """GĐ3.6: write-through — sau khi ghi DB, nạp lại knowledge để chat/tool thấy ngay.

    Bọc try/except: lỗi reload không được làm hỏng thao tác admin đã commit.
    """
    try:
        knowledge.reload()
    except Exception:
        pass


def _safe(fn, default):
    try:
        return fn()
    except Exception:
        return default

# ── Auth dependency ──

async def require_admin(request: Request):
    """FastAPI dependency: verify admin auth + rate limit."""
    # Rate limit
    client_ip = get_client_ip(request)
    allowed, rate_info = admin_limiter.is_allowed(client_ip)
    if not allowed:
        raise HTTPException(429, detail="Rate limit exceeded", headers={"Retry-After": str(rate_info["retry_after"])})
    # Auth: allow server-side admin key or a logged-in admin user from the frontend.
    if verify_admin_key(request):
        return
    user = await get_current_user(request)
    if user and user.get("role") == "admin":
        return
    raise HTTPException(401, detail="Invalid admin credentials. Use X-Admin-Key or an admin session.")

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
               "accommodation", "person", "event", "history", "nature", "economy"}

class EntityUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    type: str | None = None
    summary: str | None = Field(None, max_length=2000)
    placeId: str | None = Field(None, max_length=100)
    confidence: float | None = Field(None, ge=0, le=1)
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
    confidence: float = Field(0.7, ge=0, le=1)
    season: dict | None = None
    attributes: dict = {}
    images: list[str] = []

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
    confidence_below: Optional[float] = None,
    limit: int = Query(50, le=500),
    offset: int = 0,
):
    """Danh sách entities với filter — đọc từ database."""
    if q:
        results = db.search_entities(q=q, entity_type=type, area=area, limit=limit)
    elif type:
        results = db.list_entities(entity_type=type, area=area, limit=limit, offset=offset)
    else:
        results = db.list_entities(area=area, limit=limit, offset=offset)

    if include_places:
        places = db.list_entities(entity_type=None, limit=1000, offset=0)
        results = [e for e in (results + [p for p in places if p["type"] == "place"])]

    if confidence_below is not None:
        results = [e for e in results if e.get("confidence", 1) < confidence_below]

    total = len(results)
    items = results[:limit] if q else results
    for e in items:
        if e.get("placeId"):
            place = db.get_entity(e["placeId"])
            e["place_name"] = place["name"] if place else None
            e["area"] = place.get("area") if place else e.get("area")

    return {"total": total, "offset": offset, "limit": limit, "entities": items}


@router.get("/entities/places")
async def list_places():
    """Danh sách xã/phường cho dropdown."""
    db.initialize()
    ph = db._ph
    with db._conn() as conn:
        rows = db._fetchall(conn, "SELECT id, name, area, level FROM entities WHERE type = 'place' ORDER BY name")
    return [db._row_to_dict(r) for r in rows]


@router.get("/entities/{entity_id}")
async def get_entity(entity_id: str):
    """Chi tiết 1 entity."""
    entity = db.get_entity(entity_id)
    if not entity:
        raise HTTPException(404, f"Entity '{entity_id}' not found")
    entity["relationships"] = db.get_relationships(entity_id)
    return entity


@router.put("/entities/{entity_id}")
async def update_entity(entity_id: str, update: EntityUpdate):
    """Cập nhật entity."""
    existing = db.get_entity(entity_id)
    if not existing:
        raise HTTPException(404, f"Entity '{entity_id}' not found")

    updates = update.model_dump(exclude_none=True)
    existing.update(updates)
    existing["updatedAt"] = datetime.now().strftime("%Y-%m-%d")
    db.upsert_entity(existing)
    _sync_kb()
    return {"status": "updated", "entity": existing}


@router.post("/entities")
async def create_entity(entity: EntityCreate):
    """Tạo entity mới."""
    if db.get_entity(entity.id):
        raise HTTPException(409, f"Entity '{entity.id}' already exists")

    new_entity = {
        **entity.model_dump(),
        "source": {"title": "admin", "method": "manual"},
        "updatedAt": datetime.now().strftime("%Y-%m-%d"),
    }
    db.upsert_entity(new_entity)
    _sync_kb()
    return {"status": "created", "entity": new_entity}


@router.delete("/entities/{entity_id}")
async def delete_entity(entity_id: str):
    """Xóa entity."""
    if not db.delete_entity(entity_id):
        raise HTTPException(404, f"Entity '{entity_id}' not found")
    _sync_kb()
    return {"status": "deleted", "entity_id": entity_id}


# ── Itinerary CRUD ──

@router.get("/itineraries")
async def list_itineraries_admin(area: Optional[str] = None):
    return db.list_itineraries(area=area)

@router.get("/itineraries/{itin_id}")
async def get_itinerary_admin(itin_id: str):
    it = db.get_itinerary(itin_id)
    if not it:
        raise HTTPException(404, "Itinerary not found")
    return it

@router.post("/itineraries")
async def create_itinerary(body: dict):
    if not body.get("id") or not body.get("title"):
        raise HTTPException(400, "id and title required")
    db.upsert_itinerary(body)
    return {"status": "created", "id": body["id"]}

@router.put("/itineraries/{itin_id}")
async def update_itinerary(itin_id: str, body: dict):
    body["id"] = itin_id
    db.upsert_itinerary(body)
    return {"status": "updated", "id": itin_id}

@router.delete("/itineraries/{itin_id}")
async def delete_itinerary(itin_id: str):
    db.initialize()
    ph = db._ph
    with db._conn() as conn:
        db._execute(conn, f"DELETE FROM itineraries WHERE id = {ph}", (itin_id,))
    return {"status": "deleted", "id": itin_id}


# ── Relationship CRUD ──

@router.post("/relationships")
async def add_relationship(body: dict):
    db.add_relationship(body["from_id"], body["to_id"], body["type"])
    return {"status": "created"}

@router.delete("/relationships")
async def delete_relationship(from_id: str, to_id: str, type: str):
    db.initialize()
    ph = db._ph
    with db._conn() as conn:
        db._execute(conn, f"DELETE FROM relationships WHERE from_id={ph} AND to_id={ph} AND type={ph}",
                    (from_id, to_id, type))
    return {"status": "deleted"}


# ── Bulk operations ──

# Data quality review queue

@router.get("/data-quality/summary")
async def data_quality_summary(refresh: bool = Query(False)):
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

@router.get("/data-quality/review")
async def data_quality_review(
    kind: Optional[str] = Query(None, pattern="^(source|location|placeid|accuracy|relationship)$"),
    bucket: Optional[str] = Query(None, pattern="^(auto_apply|needs_review|reject)$"),
    refresh: bool = Query(False),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    queue = data_quality.load_candidate_queue(refresh=refresh)
    result = data_quality.filter_candidates(queue, kind=kind, bucket=bucket, limit=limit, offset=offset)
    result["cache"] = queue.get("cache", {})
    return result

@router.post("/data-quality/apply")
async def data_quality_apply(body: DataQualityApplyRequest):
    # GĐ3.8: apply_candidates ghi THẲNG vào DB (DB-native, không DELETE-reload-json) -> an toàn, đã bỏ khoá.
    result = data_quality.apply_candidates(body.candidate_ids, dry_run=body.dry_run)
    if result.get("applied_count") and not body.dry_run:
        _sync_kb()
    return result

@router.get("/data-quality/history")
async def data_quality_history(limit: int = Query(20, ge=1, le=200)):
    return data_quality.load_apply_history(limit=limit)

@router.post("/data-quality/rollback/{batch_id}")
async def data_quality_rollback(batch_id: str):
    # GĐ3.8: rollback DB-native (đặt lại field về before trong history) -> an toàn, đã bỏ khoá.
    try:
        result = data_quality.rollback_apply(batch_id)
    except ValueError as exc:
        raise HTTPException(400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(404, detail=str(exc)) from exc
    _sync_kb()
    return result

@router.post("/entities/bulk-delete")
async def bulk_delete(entity_ids: list[str]):
    """Xóa nhiều entities cùng lúc."""
    deleted = 0
    for eid in entity_ids:
        if db.delete_entity(eid):
            deleted += 1
    return {"status": "deleted", "count": deleted}


@router.post("/entities/bulk-update-confidence")
async def bulk_update_confidence(entity_ids: list[str], confidence: float = Query(ge=0, le=1)):
    """Cập nhật confidence cho nhiều entities."""
    updated = 0
    for eid in entity_ids:
        entity = db.get_entity(eid)
        if entity:
            entity["confidence"] = confidence
            entity["updatedAt"] = datetime.now().strftime("%Y-%m-%d")
            db.upsert_entity(entity)
            updated += 1
    return {"status": "updated", "count": updated}


# ── Review queue ──

@router.get("/review")
async def review_queue(confidence_below: float = 0.7, limit: int = 50):
    """Entities cần review (confidence thấp)."""
    db.initialize()
    ph = db._ph
    with db._conn() as conn:
        rows = db._fetchall(conn, f"""
            SELECT id, type, name, summary, confidence, source, "updatedAt"
            FROM entities WHERE type != 'place' AND confidence < {ph}
            ORDER BY confidence ASC LIMIT {ph}
        """, (confidence_below, limit))
    results = []
    for r in rows:
        d = db._row_to_dict(r)
        d["summary"] = (d.get("summary") or "")[:150]
        results.append(d)
    return {"total": len(results), "entities": results}


# ── Image management ──

@router.post("/entities/{entity_id}/images")
async def add_entity_image(entity_id: str, request: Request):
    """Add image URL to entity."""
    body = await request.json()
    url = body.get("url", "")
    if not url or not isinstance(url, str) or len(url) > 500:
        raise HTTPException(400, "Invalid image URL")
    if not url.startswith(("https://", "http://")):
        raise HTTPException(400, "Image URL must start with http:// or https://")

    entity = db.get_entity(entity_id)
    if not entity:
        raise HTTPException(404, f"Entity '{entity_id}' not found")

    images = entity.get("images", []) or []
    if isinstance(images, str):
        images = json.loads(images)
    if len(images) >= 10:
        raise HTTPException(400, "Maximum 10 images per entity")
    images.append(url)
    entity["images"] = images
    entity["updatedAt"] = datetime.now().strftime("%Y-%m-%d")
    db.upsert_entity(entity)
    return {"status": "added", "images": images}


@router.delete("/entities/{entity_id}/images/{index}")
async def remove_entity_image(entity_id: str, index: int):
    """Remove image by index from entity."""
    entity = db.get_entity(entity_id)
    if not entity:
        raise HTTPException(404, f"Entity '{entity_id}' not found")

    images = entity.get("images", []) or []
    if isinstance(images, str):
        images = json.loads(images)
    if index < 0 or index >= len(images):
        raise HTTPException(400, f"Image index {index} out of range (0-{len(images)-1})")
    removed = images.pop(index)
    entity["images"] = images
    entity["updatedAt"] = datetime.now().strftime("%Y-%m-%d")
    db.upsert_entity(entity)
    return {"status": "removed", "removed_url": removed, "images": images}


# ── Data management ──

@router.get("/stats")
async def admin_stats():
    """Thống kê chi tiết cho admin."""
    db.initialize()
    ph = db._ph
    with db._conn() as conn:
        type_rows = db._fetchall(conn, "SELECT type, COUNT(*) as c FROM entities GROUP BY type", ())
        rel_count = db._fetchone(conn, "SELECT COUNT(*) as c FROM relationships", ())
        itin_count = db._fetchone(conn, "SELECT COUNT(*) as c FROM itineraries", ())
        low_conf = db._fetchone(conn, "SELECT COUNT(*) as c FROM entities WHERE type != 'place' AND confidence < 0.7", ())

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

    return {
        "total_entities": total_entities,
        "total_places": total_places,
        "total_relationships": rel_count["c"] if rel_count else 0,
        "total_itineraries": itin_count["c"] if itin_count else 0,
        "by_type": by_type,
        "low_confidence": low_conf["c"] if low_conf else 0,
    }


@router.post("/trigger-learn")
async def trigger_learn(category: Optional[str] = None, topics: int = 3):
    """Trigger 1 vòng auto-learn (chạy background)."""
    # Validate topics range
    if topics < 1 or topics > 20:
        raise HTTPException(400, "topics must be between 1 and 20")
    # Sanitize category — allow only alphanumeric, hyphens, underscores, Vietnamese chars
    if category:
        if len(category) > 50 or not re.match(r'^[\w\s\-À-ɏḀ-ỿ]+$', category):
            raise HTTPException(400, "Invalid category — only letters, numbers, hyphens, underscores allowed (max 50 chars)")
    cmd = [sys.executable, str(ROOT / "agent" / "auto_learn.py"), "--apply", "--topics", str(topics)]
    if category:
        cmd.extend(["--category", category])

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        return {
            "status": "started",
            "pid": proc.pid,
            "command": " ".join(cmd),
            "note": "Chạy background. Gọi POST /reload sau khi xong.",
        }
    except Exception as e:
        raise HTTPException(500, str(e))


# ── Quarantine review queue (provisional auto-learned entities) ──

@router.get("/provisional")
async def list_provisional_entities():
    """Liệt kê các entity tự học CHƯA kiểm chứng (chờ duyệt)."""
    import kb_curation
    return {"provisional": kb_curation.list_provisional(), **kb_curation.stats()}


@router.post("/provisional/{entity_id}/approve")
async def approve_provisional(entity_id: str):
    """Duyệt 1 entity provisional → verified (tin cậy)."""
    import kb_curation
    result = kb_curation.promote(entity_id)
    if not result.get("ok"):
        raise HTTPException(404 if result.get("error") == "not found" else 400, result.get("error", "failed"))
    return result


@router.post("/provisional/{entity_id}/reject")
async def reject_provisional(entity_id: str):
    """Từ chối + xóa 1 entity provisional khỏi KB."""
    import kb_curation
    result = kb_curation.reject(entity_id)
    if not result.get("ok"):
        raise HTTPException(404 if result.get("error") == "not found" else 400, result.get("error", "failed"))
    return result


@router.post("/export")
async def export_data():
    """Export toàn bộ entities từ DB."""
    entities = db.list_entities(limit=10000)
    db.initialize()
    with db._conn() as conn:
        rels = db._fetchall(conn, "SELECT from_id, to_id, type FROM relationships", ())
        itins = db._fetchall(conn, "SELECT * FROM itineraries", ())
    return {
        "entities": entities,
        "relationships": [db._row_to_dict(r) for r in rels],
        "itineraries": [db._row_to_dict(r) for r in itins],
    }


@router.get("/sources")
async def list_sources():
    """Liệt kê tất cả nguồn dữ liệu."""
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


# ═══════════════════════════════════════════════════════
# Moderation & Community Admin
# ═══════════════════════════════════════════════════════


@router.get("/moderation/queue")
async def moderation_queue(
    status: str = Query("pending", pattern="^(pending|flagged|approved|rejected)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    ph = db._ph
    offset = (page - 1) * limit
    with db._conn() as conn:
        rows = db._fetchall(conn, f"""
            SELECT p.*, u.display_name, u.phone,
                   e.name as entity_name
            FROM posts p
            JOIN users u ON u.id = p.user_id
            LEFT JOIN entities e ON e.id = p.entity_id
            WHERE p.moderation_status = {ph}
            ORDER BY p.created_at DESC
            LIMIT {ph} OFFSET {ph}
        """, (status, limit, offset))
        total = db._fetchone(conn, f"""
            SELECT COUNT(*) as c FROM posts WHERE moderation_status = {ph}
        """, (status,))
    return {
        "posts": [_mod_post(db._row_to_dict(r)) for r in rows],
        "total": total["c"] if total else 0,
        "page": page,
    }


@router.post("/moderation/{post_id}/approve")
async def approve_post(post_id: str):
    ph = db._ph
    with db._conn() as conn:
        db._execute(conn, f"""
            UPDATE posts SET moderation_status = 'approved' WHERE id::text = {ph}
        """, (post_id,))
    _log_mod_action("post", post_id, "approved")
    return {"success": True}


@router.post("/moderation/{post_id}/reject")
async def reject_post(post_id: str):
    ph = db._ph
    with db._conn() as conn:
        db._execute(conn, f"""
            UPDATE posts SET moderation_status = 'rejected' WHERE id::text = {ph}
        """, (post_id,))
    _log_mod_action("post", post_id, "rejected")
    return {"success": True}


@router.get("/moderation/stats")
async def moderation_stats():
    with db._conn() as conn:
        rows = db._fetchall(conn, """
            SELECT moderation_status, COUNT(*) as c FROM posts GROUP BY moderation_status
        """, ())
    counts = {r["moderation_status"]: r["c"] for r in [db._row_to_dict(row) for row in rows]}
    return {"counts": counts}


@router.get("/analytics-overview")
async def analytics_overview():
    """GĐ9.6: gói số liệu cho trang admin Analytics (1 call, đã auth qua require_admin).

    - popular: user hỏi gì nhiều · gaps: câu bot bí (backlog nội dung) · costs: chi phí LLM.
    """
    out = {
        "summary": _safe(lambda: analytics.get_summary(), {}),
        "popular": _safe(lambda: analytics.get_popular_queries(20), []),
        "gaps": _safe(lambda: analytics.get_knowledge_gaps(20), []),
        "top_entities": _safe(lambda: analytics.get_top_entities(15), []),
        "costs": _safe(_get_cost_report, {}) if _HAS_COST else {"available": False},
    }
    return out


@router.get("/reports")
async def get_reports(
    status: str = Query("pending", pattern="^(pending|resolved|dismissed)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    ph = db._ph
    offset = (page - 1) * limit
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


@router.post("/reports/{report_id}/resolve")
async def resolve_report(report_id: str):
    ph = db._ph
    with db._conn() as conn:
        db._execute(conn, f"""
            UPDATE reports SET status = 'resolved' WHERE id::text = {ph}
        """, (report_id,))
    return {"success": True}


@router.post("/reports/{report_id}/dismiss")
async def dismiss_report(report_id: str):
    ph = db._ph
    with db._conn() as conn:
        db._execute(conn, f"""
            UPDATE reports SET status = 'dismissed' WHERE id::text = {ph}
        """, (report_id,))
    return {"success": True}


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
    }


@router.post("/users/{user_id}/ban")
async def ban_user(user_id: str):
    ph = db._ph
    with db._conn() as conn:
        db._execute(conn, f"""
            UPDATE users SET is_active = FALSE WHERE id::text = {ph}
        """, (user_id,))
    return {"success": True}


@router.post("/users/{user_id}/unban")
async def unban_user(user_id: str):
    ph = db._ph
    with db._conn() as conn:
        db._execute(conn, f"""
            UPDATE users SET is_active = TRUE WHERE id::text = {ph}
        """, (user_id,))
    return {"success": True}


@router.post("/users/{user_id}/role")
async def set_user_role(user_id: str, role: str = Query(..., pattern="^(user|moderator|admin)$")):
    ph = db._ph
    with db._conn() as conn:
        db._execute(conn, f"""
            UPDATE users SET role = {ph} WHERE id::text = {ph}
        """, (role, user_id))
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
        "content": row.get("content", "")[:200],
        "post_type": row.get("post_type", "share"),
        "moderation_status": row.get("moderation_status", "pending"),
        "images": images,
        "author": row.get("display_name", ""),
        "entity_name": row.get("entity_name"),
        "created_at": str(row.get("created_at", "")),
    }


def _mask(phone: str) -> str:
    if not phone or len(phone) < 6:
        return phone or ""
    return phone[:3] + "****" + phone[-3:]


def _log_mod_action(target_type, target_id, action):
    try:
        from moderation import log_moderation
        log_moderation(target_type, target_id, action, {}, auto=False)
    except Exception:
        pass
