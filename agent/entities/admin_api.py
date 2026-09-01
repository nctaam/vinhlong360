# -*- coding: utf-8 -*-
"""Miền ENTITY — mặt QUẢN TRỊ. Bóc khỏi `admin.py` (2026-08-28, bước 2b).

Hoàn tất gói miền entity theo khuôn `agent/cases/` (public_api.py + admin_api.py
trong CÙNG một gói): mặt công khai đã sang `entities/api.py` ở bước 1b; đây là
39 route quản trị (CRUD entity, quan hệ, schema/kind, chất lượng, media, claims,
featured) — 87 ký hiệu, bao đóng bắc cầu, 1 rò rỉ duy nhất là dòng ĐĂNG KÝ
`_admin_volatile_caches.append(_media_cache)` đi cùng cache về đây.

Mount qua `admin.router.include_router(...)` TRƯỚC `_fix_admin_route_order()`:
- cổng R20.9 chỉ nhìn thấy mount qua lời gọi include_router (bài học 1b);
- router cha mang prefix "/admin" VÀ dependencies [require_admin, require_csrf]
  — router này KHÔNG tự mang cả hai, kế thừa từ cha khi include (đã kiểm bằng
  đo runtime, không tin trí nhớ API).
"""
from __future__ import annotations

import asyncio
import html as _html
import json
import re as _re
import uuid
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import File, HTTPException, Query, Request, UploadFile
from fastapi import Path as PathParam
from pydantic import BaseModel, Field, field_validator

import data_quality
import knowledge
import text_utils
from admin_common import _log_mod_action, _mask, _sync_kb, _admin_volatile_caches
from auth_middleware import require_pg, validate_path_id
from database import db, escape_like as _escape_like  # alias như admin.py
# Alias NGUYÊN VĂN như admin.py — các tên `_x` là bí danh nội bộ, không phải
# tên xuất của entity_schemas (đã vấp ImportError khi đoán tên).
from entity_schemas import (
    ENTITY_SCHEMAS as _ENTITY_SCHEMAS,
    KIND_META as _KIND_META,
    KIND_OF_TYPE as _KIND_OF_TYPE,
    all_schemas as _all_schemas,
    kind_of as _kind_of,
    valid_types as _valid_types,
    validate_attributes as _validate_attributes,
)
import image_suggestions as _imgq  # alias như admin.py
from media_policy import (
    AI_ONLY_MEDIA_DETAIL,
    entity_images_are_ai_only,
    is_canonical_legacy_entity_image,
)
from notifications import create_notification
from pinned_http import (
    DestinationPolicyError,
    EgressPolicy,
    InvalidDestinationError,
    PinnedBodyLimitError,
    PinnedContentEncodingError,
    PinnedDeadlineExceeded,
    PinnedHTTPClient,
    PinnedTransportError,
    RedirectPolicyError,
    ResolutionError,
    ResolverSaturatedError,
    validate_public_url,
)

import logging

from fastapi import APIRouter

logger = logging.getLogger("admin")   # giữ NGUYÊN kênh log admin
router = APIRouter(tags=["admin-entities"])


def _admin_image_egress_policy(max_image_size: int) -> EgressPolicy:
    return EgressPolicy(
        max_encoded_bytes=max_image_size,
        max_decoded_bytes=max_image_size,
        accepted_encodings=("identity",),
        inactivity_timeout_seconds=25.0,
        total_timeout_seconds=25.0,
        max_redirects=5,
    )


_PINNED_HTTP = PinnedHTTPClient()


def _reject_non_ai_media() -> None:
    raise HTTPException(status_code=400, detail=AI_ONLY_MEDIA_DETAIL)


def _require_ai_only_entity_images(images: list[str] | None) -> None:
    if images is not None and not entity_images_are_ai_only(images):
        _reject_non_ai_media()


def _sanitize(text: str) -> str:
    """Remove dangerous HTML/JS from user input."""
    text = _html.escape(text)
    text = _re.sub(r'<script[^>]*>.*?</script>', '', text, flags=_re.IGNORECASE | _re.DOTALL)
    return text.strip()


VALID_TYPES = _valid_types()


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
    id: str = Field(..., min_length=2, max_length=100, pattern=r'^[a-z0-9_\-]+$')  # allow underscore (align w/ FE + existing slugs)
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


@router.get("/entities",
            summary="List entities (admin)",
            description="Returns a paginated list of all entities for admin management. Supports filtering by type, area, search query, and orphan detection.")
async def list_entities(
    type: Optional[str] = Query(None, max_length=50),
    kind: Optional[str] = Query(None, max_length=30),
    area: Optional[str] = Query(None, max_length=100),
    q: Optional[str] = Query(None, max_length=200),
    include_places: bool = False,
    orphans_only: bool = False,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0, le=10000),
):
    """Danh sách entities với filter — đọc từ database."""
    def _query():
        # GĐ-A: `kind` mở rộng thành các type thành viên qua registry (type cụ thể vẫn ưu tiên).
        kind_types: list[str] | None = None
        if kind and not type:
            kind_types = sorted(t for t, k in _KIND_OF_TYPE.items() if k == kind)
            if not kind_types:
                return {"total": 0, "offset": offset, "limit": limit, "entities": []}
        all_matches, results = _list_entities_fetch(type, area, q, orphans_only, kind_types, limit, offset)
        all_matches, results = _list_entities_add_places(include_places, all_matches, results)
        all_matches = _list_entities_filter_orphans(orphans_only, all_matches)

        if all_matches is not None:
            total = len(all_matches)
            items = all_matches[offset:offset + limit]
        else:
            total = db.count_entities_filtered(entity_type=type, area=area)
            items = results

        _list_entities_attach_place_names(items)
        return {"total": total, "offset": offset, "limit": limit, "entities": items}
    return await asyncio.to_thread(_query)


def _list_entities_fetch_place_rows() -> list[dict]:
    with db._conn() as conn:
        place_rows = db._fetchall(conn, "SELECT * FROM entities WHERE type = 'place' ORDER BY name LIMIT 1000", ())
    return [db._parse_entity(r) for r in place_rows]


def _list_entities_fetch(type, area, q, orphans_only, kind_types, limit, offset):
    """Return (all_matches, results) per the filter combination; `results` only set when unfiltered."""
    results = None
    if q or orphans_only:
        all_matches = db.search_entities(q=q, entity_type=type, area=area, limit=2000, offset=0) if q else db.list_entities(entity_type=type, area=area, limit=2000, offset=0)
        if kind_types:
            _kt = set(kind_types)
            all_matches = [e for e in all_matches if e.get("type") in _kt]
    elif kind_types:
        merged: list[dict] = []
        for t in kind_types:
            if t == "place":
                # list_entities mặc định không trả place — lấy trực tiếp (giống nhánh include_places).
                merged.extend(_list_entities_fetch_place_rows())
            else:
                merged.extend(db.list_entities(entity_type=t, area=area, limit=2000, offset=0) or [])
        merged.sort(key=lambda e: (e.get("name") or ""))
        all_matches = merged
    else:
        all_matches = None
        results = db.list_entities(entity_type=type, area=area, limit=limit, offset=offset)
    return all_matches, results


def _list_entities_add_places(include_places, all_matches, results):
    if include_places:
        places = _list_entities_fetch_place_rows()
        if all_matches is not None:
            all_matches = all_matches + places
        else:
            results = results + places
    return all_matches, results


def _list_entities_filter_orphans(orphans_only, all_matches):
    if orphans_only:
        with db._conn() as conn:
            orphan_rows = db._fetchall(conn,
                "SELECT id FROM entities WHERE type != 'place' "
                "AND id NOT IN (SELECT from_id FROM relationships) "
                "AND id NOT IN (SELECT to_id FROM relationships)", ())
            orphan_ids = {db._row_to_dict(r)["id"] for r in orphan_rows}
        if all_matches is not None:
            all_matches = [e for e in all_matches if e["id"] in orphan_ids]
    return all_matches


def _list_entities_attach_place_names(items) -> None:
    place_ids = list({e["placeId"] for e in items if e.get("placeId")})
    if place_ids:
        place_map = db.get_entities_batch(place_ids)
        for e in items:
            pid = e.get("placeId")
            if pid and pid in place_map:
                e["place_name"] = place_map[pid]["name"]
                e["area"] = place_map[pid].get("area") or e.get("area")


@router.get("/entity-kinds",
            summary="Entity counts grouped by owner category (kind)",
            description="Returns the 7 owner-facing categories (kinds) as a derived view over the 17 raw "
                        "types, with per-kind totals and per-type breakdown. Phase 2 of the content-model — "
                        "a reporting/grouping layer; nothing is stored, `type` stays the storage discriminator.")
async def entity_kinds():
    """Đếm entity theo danh mục chủ (kind) — lớp gộp phái sinh trên 17 type."""
    def _query():
        by_type = db.count_entities()  # {type: count}, excludes 'place'
        # place (administrative) counted separately since count_entities excludes it
        with db._conn() as conn:
            row = db._fetchone(conn, "SELECT COUNT(*) c FROM entities WHERE type = 'place'", ())
        place_count = (db._row_to_dict(row) or {}).get("c", 0) if row else 0
        by_type = dict(by_type)
        if place_count:
            by_type["place"] = place_count

        # Group into kinds, preserving KIND_META order.
        buckets: dict[str, list] = {k: [] for k in _KIND_META}
        for t, cnt in by_type.items():
            k = _kind_of(t)
            meta = _ENTITY_SCHEMAS.get(t, {})
            buckets.setdefault(k, []).append({
                "type": t,
                "label": meta.get("label", t),
                "emoji": meta.get("emoji", "📍"),
                "count": cnt,
            })
        kinds = []
        for k, km in _KIND_META.items():
            items = sorted(buckets.get(k, []), key=lambda x: -x["count"])
            kinds.append({
                "kind": k,
                "label": km["label"],
                "emoji": km["emoji"],
                "total": sum(i["count"] for i in items),
                "types": items,
            })
        return {"kinds": kinds, "grand_total": sum(by_type.values())}
    return await asyncio.to_thread(_query)


@router.get("/entity-completeness",
            summary="Data completeness per kind",
            description="Per-kind field-fill percentages (universal + registry fields) plus the entities "
                        "missing the most data. Read-only reporting for the per-kind AdminCP views (GĐ-A).")
async def entity_completeness(kind: str = Query(..., max_length=30), worst: int = Query(20, ge=1, le=100)):
    """% điền từng trường + entity thiếu nhiều nhất — dashboard làm giàu dữ liệu theo nhóm."""
    def _query():
        kind_types = sorted(t for t, k in _KIND_OF_TYPE.items() if k == kind)
        if not kind_types:
            return {"kind": kind, "total": 0, "fields": [], "worst": []}
        ents = _completeness_fetch_ents(kind_types)
        if not ents:
            return {"kind": kind, "total": 0, "fields": [], "worst": []}

        fields: list[dict] = []
        missing_map: dict[str, list[str]] = {e["id"]: [] for e in ents}
        seen = _completeness_universal_fields(ents, fields, missing_map)
        _completeness_registry_fields(ents, kind_types, seen, fields, missing_map)
        by_id = {e["id"]: e for e in ents}
        worst_list = sorted(missing_map.items(), key=lambda kv: -len(kv[1]))[:worst]
        return {"kind": kind, "total": len(ents), "fields": fields,
                "worst": [{"id": i, "name": by_id[i]["name"], "type": by_id[i]["type"],
                           "missing": m, "missing_count": len(m)} for i, m in worst_list if m]}
    return await asyncio.to_thread(_query)


_COMPLETENESS_UNIVERSAL = [("address", "Địa chỉ"), ("phone", "Điện thoại"), ("website", "Website"),
                          ("hours", "Giờ mở cửa"), ("price_range", "Khoảng giá"),
                          ("sub_category", "Phân loại"), ("best_time", "Thời điểm đẹp"), ("highlight", "Điểm nhấn")]


def _completeness_has(e: dict, key: str) -> bool:
    a = e.get("attributes") or {}
    if key == "season":
        s = e.get("season") or {}
        return bool(s.get("months") or s.get("best"))
    if key == "images":
        return bool(e.get("images"))
    if key == "coords_real":
        return bool(e.get("coordinates")) and not a.get("coords_approximate")
    if key == "summary_100":
        return len(str(e.get("summary") or "")) >= 100
    return a.get(key) not in (None, "", [], {})


def _completeness_fetch_ents(kind_types: list[str]) -> list[dict]:
    with db._conn() as conn:
        placeholders = ", ".join(db._ph for _ in kind_types)  # ?/%s theo backend (PG dùng %s)
        rows = db._fetchall(conn,
            f"SELECT * FROM entities WHERE type IN ({placeholders}) ORDER BY name LIMIT 2000",
            tuple(kind_types))
        return [db._parse_entity(r) for r in rows]


def _completeness_universal_fields(ents, fields, missing_map) -> set[str]:
    """Append universal-field stats to `fields`, update `missing_map`, return the seen key set."""
    universal_keys = [k for k, _ in _COMPLETENESS_UNIVERSAL] + ["season", "images", "coords_real", "summary_100"]
    labels = dict(_COMPLETENESS_UNIVERSAL)
    labels.update({"season": "Mùa", "images": "Ảnh", "coords_real": "Tọa độ thật",
                   "summary_100": "Tóm tắt ≥100 ký tự"})
    filled_counts = {k: 0 for k in universal_keys}
    for e in ents:
        for key in universal_keys:
            if _completeness_has(e, key):
                filled_counts[key] += 1
            else:
                missing_map[e["id"]].append(key)
    for key in universal_keys:
        fields.append({"key": key, "label": labels[key], "scope": "chung",
                       "filled": filled_counts[key], "pct": round(100 * filled_counts[key] / len(ents), 1)})
    return set(universal_keys)


def _completeness_registry_fields(ents, kind_types, seen, fields, missing_map) -> None:
    for t in kind_types:
        schema = _ENTITY_SCHEMAS.get(t) or {}
        t_ents = [e for e in ents if e["type"] == t]
        if not t_ents:
            continue
        for f in schema.get("fields", []):
            key = f["key"]
            if key in seen:
                continue
            filled = sum(1 for e in t_ents if _completeness_has(e, key))
            fields.append({"key": key, "label": f["label"], "scope": schema.get("label", t),
                           "filled": filled, "pct": round(100 * filled / len(t_ents), 1)})
            for e in t_ents:
                if not _completeness_has(e, key):
                    missing_map[e["id"]].append(key)


@router.get("/entities/places",
            summary="List places for dropdown",
            description="Returns a list of place entities (xa/phuong) for use in admin dropdown selectors.")
async def list_places():
    """Danh sách xã/phường cho dropdown."""
    def _query():
        db.initialize()
        with db._conn() as conn:
            rows = db._fetchall(conn, "SELECT id, name, area, level FROM entities WHERE type = 'place' ORDER BY name LIMIT 500")
        return [db._row_to_dict(r) for r in rows]
    return await asyncio.to_thread(_query)


@router.get("/entities/check-duplicate",
            summary="Check entity name duplicate",
            description="Checks for existing entities with similar names using case-insensitive substring matching. Returns up to 5 matches.")
async def check_duplicate(name: str = Query(..., min_length=2, max_length=200)):
    """Kiểm tra entity trùng tên (substring, case-insensitive + B2c: không phân biệt dấu)."""
    name_lower = name.lower().strip()
    if len(name_lower) < 2:
        return {"duplicates": []}
    pattern = f"%{_escape_like(name_lower)}%"
    norm_needle = text_utils.normalize_name(name)
    def _query():
        with db._conn() as conn:
            # db._ph: ? chỉ đúng SQLite — trên PG (psycopg2) phải %s (500 trên prod)
            if db._use_pg:
                # f_unaccent (migration 015) đã có index — OR thêm để bắt biến thể có/không dấu.
                sql = (f"SELECT id, name, type FROM entities WHERE type != 'place' AND "
                       f"(LOWER(name) LIKE {db._ph} ESCAPE '\\' OR f_unaccent(LOWER(name)) LIKE f_unaccent({db._ph}) ESCAPE '\\') LIMIT 20")
                rows = db._fetchall(conn, sql, (pattern, pattern))
            else:
                rows = db._fetchall(conn,
                    f"SELECT id, name, type FROM entities WHERE type != 'place' AND LOWER(name) LIKE {db._ph} ESCAPE '\\' LIMIT 20",
                    (pattern,))
        dups = []
        for r in rows:
            d = db._row_to_dict(r)
            dups.append({"id": d["id"], "name": d["name"], "type": d.get("type", "")})
        if not db._use_pg:
            # SQLite fallback: không có unaccent() — lọc bổ sung bằng normalize_name trong Python.
            dups = [d for d in dups if norm_needle in text_utils.normalize_name(d["name"])]
        return {"duplicates": dups[:5]}
    return await asyncio.to_thread(_query)


@router.get("/entities/{entity_id}",
            summary="Get entity details",
            description="Returns full details of a single entity including its relationships.")
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


@router.put("/entities/{entity_id}",
            summary="Update entity",
            description="Updates an entity's fields. Logs changes to entity history and invalidates relevant caches.")
async def update_entity(entity_id: str, update: EntityUpdate):
    """Cập nhật entity."""
    _require_ai_only_entity_images(update.images)
    entity_id = validate_path_id(entity_id, "entity_id")
    def _query():
        existing = db.get_entity(entity_id)
        if not existing:
            raise HTTPException(404, "Entity không tồn tại")
        old_snapshot = {k: v for k, v in existing.items()}
        updates = update.model_dump(exclude_none=True)
        existing.update(updates)
        # Typed, non-destructive validation against the type's content-model schema:
        # coerces known fields (number/bool/tags), preserves the bespoke tail, and
        # surfaces warnings (missing-required / bad-enum) without blocking the save.
        norm_attrs, warnings = _validate_attributes(existing.get("type", ""), existing.get("attributes"))
        existing["attributes"] = norm_attrs
        existing["updatedAt"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        # One transaction for the row and its audit: an edit that cannot be
        # recorded must not land, or nobody can answer for it later.
        db.upsert_entity_with_audit(existing, old_snapshot,
                                    actor="admin", provenance="admin-editor",
                                    reason="entity_update", correlation_id=f"entity-update:{entity_id}")
        _sync_kb()
        from entity_read import invalidate_entity_cache, invalidate_place_cache
        invalidate_entity_cache(entity_id)
        if existing.get("type") == "place":
            invalidate_place_cache()
        return {"status": "updated", "entity": existing, "warnings": warnings}
    return await asyncio.to_thread(_query)


@router.get("/entities/{entity_id}/history",
            summary="Get entity change history",
            description="Returns the change history (diffs) for a specific entity, ordered by most recent first.")
async def get_entity_history(entity_id: str, limit: int = Query(50, ge=1, le=200)):
    """Lịch sử thay đổi entity."""
    entity_id = validate_path_id(entity_id, "entity_id")
    def _query():
        return {"history": db.get_entity_history(entity_id, limit)}
    return await asyncio.to_thread(_query)


@router.get("/entity-schema",
            summary="Get entity content-model schema",
            description="Returns the per-type field schema registry that drives the AdminCP typed forms, "
                        "validation, and display. Single source of truth (agent/entity_schemas.py).")
async def get_entity_schema():
    """Content-model registry: per-type fields + owner-category (kind) mapping."""
    return _all_schemas()


@router.post("/entities", status_code=201,
             summary="Create entity",
             description="Creates a new entity. Returns 409 if an entity with the same ID already exists.")
async def create_entity(entity: EntityCreate):
    """Tạo entity mới."""
    _require_ai_only_entity_images(entity.images)
    def _query():
        if db.get_entity(entity.id):
            raise HTTPException(409, "Entity đã tồn tại")
        payload = entity.model_dump()
        src = payload.pop("source", None) or {"title": "admin", "method": "manual"}
        norm_attrs, warnings = _validate_attributes(payload.get("type", ""), payload.get("attributes"))
        payload["attributes"] = norm_attrs
        new_entity = {
            **payload,
            "source": src,
            "updatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        }
        db.upsert_entity(new_entity, actor_id="admin", reason="entity_create",
                          correlation_id=f"entity-create:{new_entity['id']}")
        _sync_kb()
        return {"status": "created", "entity": new_entity, "warnings": warnings}
    return await asyncio.to_thread(_query)


@router.delete("/entities/{entity_id}",
               summary="Delete entity",
               description="Deletes an entity and invalidates related caches. Does not remove associated files.")
async def delete_entity(entity_id: str):
    """Xóa entity."""
    entity_id = validate_path_id(entity_id, "entity_id")
    def _query():
        entity = db.get_entity(entity_id)
        if not entity:
            raise HTTPException(404, "Entity không tồn tại")
        db.delete_entity(entity_id, actor_id="admin", reason="entity_delete",
                         correlation_id=f"entity-delete:{entity_id}")
        _sync_kb()
        from entity_read import invalidate_entity_cache, invalidate_place_cache
        invalidate_entity_cache(entity_id)
        if entity.get("type") == "place":
            invalidate_place_cache()
    await asyncio.to_thread(_query)
    return {"success": True, "entity_id": entity_id}


class _EntityImageURL(BaseModel):
    url: str = Field(..., max_length=600)


@router.post("/entities/{entity_id}/images", status_code=201,
             summary="Add image URL to entity",
             description="Adds an image URL to an entity's image list. Validates URL accessibility. Maximum 10 images per entity.")
async def add_entity_image_url(entity_id: str, body: _EntityImageURL):
    """GĐ8.4: thêm ảnh entity theo URL (chỉ nguồn cấp phép — B6)."""
    entity_id = validate_path_id(entity_id, "entity_id")
    url = (body.url or "").strip()
    if not is_canonical_legacy_entity_image(url):
        _reject_non_ai_media()
    if url.startswith("/"):
        pass
    else:
        await asyncio.to_thread(_validate_public_image_url, url)
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
        db.upsert_entity(entity, actor_id="admin", reason="image_add",
                          correlation_id=f"image-add:{entity_id}")
        _sync_kb()
        return {"status": "added", "images": images}
    return await asyncio.to_thread(_query)


@router.post("/entities/{entity_id}/images/upload",
             summary="Upload image file for entity",
             description="Uploads an image file, converts to WebP in 3 sizes (sm/md/lg), and adds to the entity. Maximum 10 images per entity.")
async def upload_entity_image(entity_id: str, file: UploadFile = File(...)):
    """GĐ8.4: upload file ảnh → WebP 3 cỡ → R2 (fallback đĩa) → entity.images.
    Lưu URL cỡ md (800px) làm ảnh hiển thị; sm/lg cũng được upload để dùng srcset sau."""
    entity_id = validate_path_id(entity_id, "entity_id")
    _reject_non_ai_media()
    from fastapi.concurrency import run_in_threadpool
    from storage import storage, MAX_IMAGE_SIZE

    entity = db.get_entity(entity_id)
    if not entity:
        raise HTTPException(404, "Entity không tồn tại")
    data = await file.read(MAX_IMAGE_SIZE + 1)
    if len(data) > MAX_IMAGE_SIZE:
        del data
        raise HTTPException(413, f"Ảnh quá lớn (tối đa {MAX_IMAGE_SIZE // 1024 // 1024}MB)")
    if not storage.sniff_image_type(data):
        raise HTTPException(400, "File không phải ảnh hợp lệ (JPEG/PNG/GIF/WebP)")
    if len(entity.get("images") or []) >= 10:
        raise HTTPException(400, "Tối đa 10 ảnh mỗi entity")
    try:
        urls = await run_in_threadpool(storage.upload_image_set, data, "entities", entity_id)
    except ValueError:
        raise HTTPException(400, "Ảnh không hợp lệ hoặc đã hỏng")
    except Exception as exc:
        # upload_image_set attaches partial URLs when a provider fails after
        # writing one or more variants; remove those objects before returning.
        partial_urls = getattr(exc, "urls", {})
        if isinstance(partial_urls, dict) and partial_urls:
            from control_plane.saga import cleanup_uploaded_media
            orphan_cleanup = cleanup_uploaded_media(storage, partial_urls)
            if orphan_cleanup:
                logger.error("Entity image upload compensation incomplete for %s", entity_id)
        logger.exception("Entity image upload failed for %s", entity_id)
        raise HTTPException(500, "Không thể upload ảnh, vui lòng thử lại")

    cover = urls.get("md") or urls.get("lg")
    images = list(entity.get("images") or [])
    if cover and cover not in images:
        images.append(cover)
    entity["images"] = images
    entity["updatedAt"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    post_commit_effects = ()
    try:
        db.upsert_entity(entity, actor_id="admin", reason="image_upload",
                         correlation_id=f"image-upload:{entity_id}")
    except Exception as exc:
        if getattr(exc, "committed", False):
            post_commit_effects = ({"effect": getattr(exc, "effect", "unknown"),
                                    "status": "failed"},)
        else:
            from control_plane.saga import cleanup_uploaded_media
            orphan_cleanup = cleanup_uploaded_media(storage, urls)
            if orphan_cleanup:
                logger.error("Entity image upload compensation incomplete for %s", entity_id)
            raise
    if post_commit_effects:
        logger.error("Entity image upload committed but post-commit effect failed for %s", entity_id)
    try:
        _sync_kb()
    except Exception:
        # The entity commit is authoritative; a cache/KB refresh can be retried
        # without deleting the now-referenced media.
        logger.exception("Entity image post-commit sync failed for %s", entity_id)
        post_commit_effects = (*post_commit_effects,
                               {"effect": "kb_sync", "status": "failed"})
    return {"status": "uploaded_degraded" if post_commit_effects else "uploaded",
            "url": cover, "sizes": urls, "images": images, "backend": storage.backend,
            "post_commit_effects": post_commit_effects}


@router.delete("/entities/{entity_id}/images/{idx}",
               summary="Remove image from entity",
               description="Removes an image at the given index from the entity's image list. Does not delete the actual file from storage.")
async def remove_entity_image(entity_id: str, idx: int = PathParam(..., ge=0)):
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
        db.upsert_entity(entity, actor_id="admin", reason="image_remove",
                          correlation_id=f"image-remove:{entity_id}:{idx}")
        _sync_kb()
        return {"status": "removed", "images": images}
    return await asyncio.to_thread(_query)


@router.get("/unclassified",
            summary="List unclassified entities",
            description="Returns entities not yet assigned to a commune/ward (empty placeId). Supports search and pagination.")
async def list_unclassified(limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0, le=10000),
                            q: Optional[str] = Query(None, max_length=200)):
    """Entity nội dung CHƯA gán xã/phường (placeId rỗng) — để admin gán đúng (lấp nợ placeId)."""
    ql = (q or "").lower().strip()
    # PG folds identifier không nháy về lowercase → "placeid" not exist (cột tạo
    # là "placeId" quoted). Placeholder cũng phải theo db._ph (?/%s) — bug 500
    # trên prod PG, dev SQLite không thấy (case-insensitive + dùng ?).
    _pid = '"placeId"' if db._use_pg else "placeId"
    ph = db._ph
    base = f"FROM entities WHERE type != 'place' AND ({_pid} IS NULL OR {_pid} = '')"
    params: list = []
    if ql:
        base += f" AND LOWER(name) LIKE {ph} ESCAPE '\\'"
        params.append(f"%{_escape_like(ql)}%")
    def _query():
        with db._conn() as conn:
            cnt = db._fetchone(conn, f"SELECT COUNT(*) as c {base}", tuple(params))
            total = db._row_to_dict(cnt)["c"] if cnt else 0
            rows = db._fetchall(conn, f"SELECT id, name, type, area, summary {base} ORDER BY name LIMIT {ph} OFFSET {ph}",
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


class BulkAssignPlaceRequest(BaseModel):
    entity_ids: list[str] = Field(..., min_length=1, max_length=200)
    place_id: Optional[str] = Field(None, max_length=100)


@router.post("/entities/{entity_id}/place",
             summary="Assign place to entity",
             description="Assigns or removes a commune/ward (placeId) for an entity. Validates the place exists.")
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
        db.upsert_entity(e, actor_id="admin", reason="place_assign",
                          correlation_id=f"place-assign:{entity_id}")
        _sync_kb()
        return {"success": True, "id": entity_id, "placeId": pid}
    return await asyncio.to_thread(_query)


def _bulk_assign_entities(ids, pid, place, *, actor_id: str = "admin", reason: str = "bulk_place_assign"):
    """Assign pid to each id in ids; return (assigned_ids, errors)."""
    assigned: list[str] = []
    errors: list[dict[str, str]] = []
    outcomes: list[dict[str, object]] = []
    entities_map = db.get_entities_batch(ids) if ids else {}
    for entity_id in ids:
        entity = entities_map.get(entity_id)
        if not entity:
            errors.append({"id": entity_id, "error": "Entity không tồn tại"})
            outcomes.append({"id": entity_id, "ok": False, "error": "Entity không tồn tại"})
            continue
        if pid and place:
            entity["area"] = place.get("area") or entity.get("area")
        entity["placeId"] = pid
        entity["updatedAt"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        try:
            db.upsert_entity(entity, actor_id=actor_id, reason=reason,
                             correlation_id=f"{reason}:{entity_id}")
        except Exception:
            errors.append({"id": entity_id, "error": "Không thể cập nhật entity"})
            outcomes.append({"id": entity_id, "ok": False, "error": "Không thể cập nhật entity"})
            continue
        assigned.append(entity_id)
        outcomes.append({"id": entity_id, "ok": True})
    return assigned, errors, outcomes


@router.post("/entities/bulk-place",
             summary="Bulk assign place to entities",
             description="Assigns or removes a commune/ward placeId for many entities in one admin action.")
async def bulk_assign_place(body: BulkAssignPlaceRequest):
    raw_ids = list(body.entity_ids)
    def _query():
        ids = []
        invalid: dict[str, dict[str, object]] = {}
        for raw_id in raw_ids:
            try:
                ids.append(validate_path_id(raw_id, "entity_id"))
            except HTTPException:
                invalid[raw_id] = {"id": raw_id, "ok": False, "error": "Entity không hợp lệ"}
        pid = body.place_id or None
        place = None
        if pid:
            place = db.get_entity(pid)
            if not place or place.get("type") != "place":
                raise HTTPException(400, "place_id không phải xã/phường hợp lệ")
        assigned, errors, outcomes = _bulk_assign_entities(ids, pid, place,
                                                           actor_id="admin", reason="bulk_place_assign")
        if assigned:
            _sync_kb()
        by_id: dict[str, list[dict[str, object]]] = {}
        for outcome in outcomes:
            by_id.setdefault(str(outcome["id"]), []).append(outcome)
        ordered_outcomes = []
        for raw_id in raw_ids:
            if raw_id in invalid:
                ordered_outcomes.append(invalid[raw_id])
            elif by_id.get(raw_id):
                ordered_outcomes.append(by_id[raw_id].pop(0))
        errors = list(errors) + [{"id": raw_id, "error": item["error"]} for raw_id, item in invalid.items()]
        return {"success": True, "assigned": len(assigned), "assigned_ids": assigned,
                "errors": errors, "outcomes": ordered_outcomes}
    return await asyncio.to_thread(_query)


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


@router.post("/relationships", status_code=201,
             summary="Create entity relationship",
             description="Creates a directional relationship between two entities (e.g. related_to, belongs_to).")
async def add_relationship(body: RelationshipCreate):
    validate_path_id(body.from_id, "from_id")
    validate_path_id(body.to_id, "to_id")
    await asyncio.to_thread(db.add_relationship, body.from_id, body.to_id, body.type,
                            actor_id="admin", reason="relationship_add",
                            correlation_id=f"relationship-add:{body.from_id}:{body.to_id}:{body.type}")
    return {"status": "created"}


@router.delete("/relationships",
               summary="Delete entity relationship",
               description="Removes a specific directional relationship between two entities. Returns 404 if not found.")
async def delete_relationship(from_id: str, to_id: str, type: str = Query(..., max_length=100)):
    validate_path_id(from_id, "from_id")
    validate_path_id(to_id, "to_id")
    def _query():
        if not db.delete_relationship(from_id, to_id, type, actor_id="admin",
                                      reason="relationship_delete",
                                      correlation_id=f"relationship-delete:{from_id}:{to_id}:{type}"):
            raise HTTPException(404, "Mối quan hệ không tồn tại")
    await asyncio.to_thread(_query)
    return {"success": True}


@router.post("/relationships/bulk", status_code=201,
             summary="Bulk create relationships",
             description="Creates multiple relationships from one source entity at once. Reports individual errors without rolling back.")
async def add_relationships_bulk(body: RelationshipBulkCreate):
    """B7b: thêm nhiều quan hệ cùng lúc."""
    validate_path_id(body.from_id, "from_id")
    def _query():
        added = 0
        errors = []
        outcomes = []
        for p in body.pairs:
            to_id = p.to_id.strip()
            rel_type = p.type
            if not to_id:
                errors.append({"to_id": to_id, "error": "ID đích trống"})
                outcomes.append({"to_id": to_id, "type": rel_type, "ok": False, "error": "ID đích trống"})
                continue
            try:
                db.add_relationship(body.from_id, to_id, rel_type,
                                    actor_id="admin", reason="bulk_relationship_add",
                                    correlation_id=f"bulk-relationship:{body.from_id}:{to_id}:{rel_type}")
                added += 1
                outcomes.append({"to_id": to_id, "type": rel_type, "ok": True})
            except Exception as e:
                logger.warning("Bulk relationship add failed for %s→%s: %s", body.from_id, to_id, e)
                errors.append({"to_id": to_id, "error": "Không thể thêm quan hệ"})
                outcomes.append({"to_id": to_id, "type": rel_type, "ok": False,
                                 "error": "Không thể thêm quan hệ"})
        return {"added": added, "errors": errors, "outcomes": outcomes}
    return await asyncio.to_thread(_query)


_STALE_THRESHOLD_DEFAULT = 180


@router.get("/stale-queue",
            summary="List stale entities",
            description="Returns entities that are outdated or missing key fields, sorted by staleness. Supports filtering by missing field and entity type.")
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
        entities = knowledge._entities if getattr(knowledge, "_entities", None) else {}
        results = []
        for eid, e in entities.items():
            record = _stale_entity_record(eid, e, now, threshold_days, entity_type, missing_field)
            if record is not None:
                results.append(record)
        results.sort(key=lambda x: -(x["days_since_update"] or 0))
        total = len(results)
        return {"items": results[offset:offset + limit], "total": total}
    return await asyncio.to_thread(_query)


def _stale_days_since(updated, now) -> int:
    if updated:
        try:
            dt = datetime.fromisoformat(str(updated).replace("Z", "+00:00"))
            return (now - dt).days
        except (ValueError, TypeError):
            return 9999
    return 9999


def _stale_missing_fields(e, attrs) -> list[str]:
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
    return missing


def _stale_entity_record(eid, e, now, threshold_days, entity_type, missing_field):
    """Evaluate one entity for the stale queue; return its record dict or None to skip."""
    if e.get("type") == "place":
        return None
    if entity_type and e.get("type") != entity_type:
        return None
    updated = e.get("updatedAt") or e.get("created_at")
    days_since = _stale_days_since(updated, now)
    is_stale = days_since >= threshold_days
    attrs = e.get("attributes") or {}
    missing = _stale_missing_fields(e, attrs)
    if missing_field and missing_field not in missing:
        return None
    if not is_stale and not missing:
        return None
    return {
        "id": eid,
        "name": e.get("name"),
        "type": e.get("type"),
        "area": e.get("area"),
        "days_since_update": days_since,
        "is_stale": is_stale,
        "missing_fields": missing,
        "stale_reviewed_at": attrs.get("stale_reviewed_at"),
    }


@router.post("/stale-queue/{entity_id}/mark-reviewed",
             summary="Mark stale entity as reviewed",
             description="Records a review timestamp on the entity's attributes, indicating an admin has acknowledged its staleness.")
async def stale_mark_reviewed(entity_id: str):
    """Đánh dấu entity đã được admin xem xét — ghi timestamp vào attributes."""
    validate_path_id(entity_id, "entity_id")
    def _query():
        e = db.get_entity(entity_id)
        if not e:
            raise HTTPException(404, detail="Entity không tồn tại")
        attrs = e.get("attributes") or {}
        e["attributes"] = attrs
        attrs["stale_reviewed_at"] = datetime.now(timezone.utc).isoformat()
        # Route all entity writes through the audited canonical writer; Database
        # intentionally has no ad-hoc ``update_entity`` method.
        db.upsert_entity(
            e,
            actor_id="admin",
            reason="stale_reviewed",
            correlation_id=f"stale-review:{entity_id}",
        )
        _sync_kb()
        return {"ok": True, "entity_id": entity_id, "stale_reviewed_at": attrs["stale_reviewed_at"]}
    return await asyncio.to_thread(_query)


@router.get("/completeness",
            summary="Entity completeness overview",
            description="Returns aggregate completeness statistics showing the percentage of entities that have source, images, place ID, and summary.")
async def completeness_overview():
    """Tổng quan hoàn thiện: % entities có source+images+placeId+summary."""
    def _query():
        entities = knowledge._entities if getattr(knowledge, "_entities", None) else {}
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
        def metric(count):
            if not total:
                return {"count": count, "pct": None, "status": "not_applicable"}
            return {"count": count, "pct": round(count / total * 100, 1), "status": "measured"}

        overall = (
            {"pct": None, "status": "not_applicable"}
            if not total
            else {"pct": round((has_source + has_images + has_place + has_summary) / (4 * total) * 100, 1),
                  "status": "measured"}
        )
        return {
            "total_entities": total,
            "source": metric(has_source),
            "images": metric(has_images),
            "place_id": metric(has_place),
            "summary": metric(has_summary),
            "overall_pct": overall["pct"],
            "overall_status": overall["status"],
        }
    return await asyncio.to_thread(_query)


@router.get("/completeness/details",
            summary="Entity completeness details",
            description="Returns per-entity completeness scores with missing field breakdown. Supports filtering by specific missing field and entity type.")
async def completeness_details(
    missing: Optional[str] = Query(None, pattern="^(source|images|place|summary)$"),
    entity_type: Optional[str] = Query(None, max_length=50),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0, le=10000),
):
    """Per-entity completeness scores with filter."""
    def _query():
        entities = knowledge._entities if getattr(knowledge, "_entities", None) else {}
        results = []
        for eid, e in entities.items():
            record = _completeness_detail_record(eid, e, missing, entity_type)
            if record is not None:
                results.append(record)
        results.sort(key=lambda x: x["score"])
        total = len(results)
        return {"items": results[offset:offset + limit], "total": total}
    return await asyncio.to_thread(_query)


def _completeness_detail_missing_hit(missing, q, has_imgs, has_summ) -> bool:
    """True when this entity should be skipped for the active `missing` filter."""
    if missing == "source" and q["has_source"]:
        return True
    elif missing == "images" and has_imgs:
        return True
    elif missing == "place" and q["has_place"]:
        return True
    elif missing == "summary" and has_summ:
        return True
    return False


def _completeness_detail_record(eid, e, missing, entity_type):
    if e.get("type") == "place":
        return None
    if entity_type and e.get("type") != entity_type:
        return None
    q = data_quality.entity_quality(e)
    has_imgs = bool(e.get("images"))
    has_summ = bool(e.get("summary"))
    if _completeness_detail_missing_hit(missing, q, has_imgs, has_summ):
        return None
    return {
        "id": eid,
        "name": e.get("name"),
        "type": e.get("type"),
        "score": q["score"],
        "has_source": q["has_source"],
        "has_images": has_imgs,
        "has_place": q["has_place"],
        "has_summary": has_summ,
        "missing": q["missing"] + ([] if has_imgs else ["images"]) + ([] if has_summ else ["summary"]),
    }


class BulkDeleteRequest(BaseModel):
    entity_ids: list[str] = Field(..., min_length=1, max_length=200)


@router.post("/entities/bulk-delete",
             summary="Bulk delete entities",
             description="Deletes multiple entities by their IDs in a single operation. Returns the count of successfully deleted entities.")
async def bulk_delete(body: BulkDeleteRequest):
    """Xóa nhiều entities cùng lúc."""
    def _query():
        from entity_read import invalidate_entity_cache
        deleted = 0
        outcomes = []
        for eid in body.entity_ids:
            try:
                eid = validate_path_id(eid, "entity_id")
                removed = db.delete_entity(eid, actor_id="admin", reason="bulk_entity_delete",
                                            correlation_id=f"bulk-delete:{eid}")
            except Exception:
                outcomes.append({"id": eid, "ok": False, "error": "Không thể xóa entity"})
                continue
            if removed:
                invalidate_entity_cache(eid)
                deleted += 1
                outcomes.append({"id": eid, "ok": True})
            else:
                outcomes.append({"id": eid, "ok": False, "error": "Entity không tồn tại"})
        if deleted:
            _sync_kb()
        return deleted, outcomes
    deleted, outcomes = await asyncio.to_thread(_query)
    return {"success": True, "count": deleted, "outcomes": outcomes}


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


@router.get("/image-suggestions",
            summary="List image suggestions",
            description="Lists image candidates awaiting review. Filterable by status and entity_id with pagination.")
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


@router.get("/image-suggestions/{suggestion_id}",
            summary="Get image suggestion details",
            description="Returns full details of a single image suggestion including entity name for review.")
async def get_image_suggestion(suggestion_id: str):
    """Chi tiết 1 ứng viên ảnh (kèm tên entity để review)."""
    validate_path_id(suggestion_id, "suggestion_id")
    def _query():
        s = _imgq.get_suggestion(suggestion_id)
        if not s:
            raise HTTPException(404, "Đề xuất không tồn tại")
        return s
    return await asyncio.to_thread(_query)


@router.post("/image-suggestions/create-batch", status_code=201,
             summary="Create image suggestion batch",
             description="Queues a batch of image candidates from ingest scripts for admin review. Does not publish anything.")
async def create_image_suggestion_batch(body: ImageSuggestionBatch):
    """Nhận lô ứng viên từ script ingest (mode=queue). KHÔNG publish — chỉ xếp hàng chờ duyệt."""
    def _query():
        payload = [s.model_dump() for s in body.suggestions]
        return _imgq.create_batch(payload)
    return await asyncio.to_thread(_query)


def _image_policy_http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, InvalidDestinationError):
        return HTTPException(400, "URL ảnh không hợp lệ (chỉ http/https)")
    if isinstance(exc, ResolutionError):
        return HTTPException(400, "Không phân giải được host ảnh")
    if isinstance(exc, RedirectPolicyError):
        return HTTPException(400, "URL ảnh chuyển hướng quá nhiều lần")
    return HTTPException(400, "Host ảnh trỏ địa chỉ nội bộ — từ chối (SSRF)")


def _validate_public_image_url(url: str) -> None:
    """P0-13: chặn SSRF — chỉ http(s) tới host phân giải ra IP CÔNG KHAI
    (chặn 169.254.169.254, localhost, 10/172.16/192.168, link-local…)."""
    try:
        validate_public_url(url)
    except DestinationPolicyError as exc:
        raise _image_policy_http_error(exc) from exc


async def _approve_fetch_image_data(candidate_url, run_in_threadpool, max_image_size):
    """Fetch + validate the candidate image bytes for approve_image_suggestion."""
    try:
        result = await run_in_threadpool(
            lambda: _PINNED_HTTP.get(
                candidate_url,
                user_agent="vinhlong360-image-review/1.0 (+https://vinhlong360.vn)",
                policy=_admin_image_egress_policy(max_image_size),
                audit_context="admin_image_review",
            )
        )
        status_response = httpx.Response(
            result.status_code,
            headers=result.headers,
            request=httpx.Request("GET", result.url),
        )
        status_response.raise_for_status()
        data = result.content
    except (DestinationPolicyError, RedirectPolicyError) as exc:
        raise _image_policy_http_error(exc) from exc
    except (PinnedBodyLimitError, PinnedContentEncodingError) as exc:
        raise HTTPException(
            400,
            f"Ảnh nguồn rỗng hoặc quá lớn (tối đa {max_image_size // 1024 // 1024}MB)",
        ) from exc
    except (
        PinnedDeadlineExceeded,
        ResolverSaturatedError,
        PinnedTransportError,
        httpx.HTTPStatusError,
    ) as exc:
        logger.warning("Suggestion image fetch failed for %s: %s", candidate_url, exc)
        raise HTTPException(502, "Không tải được ảnh nguồn, vui lòng thử lại sau") from exc

    if not data or len(data) > max_image_size:
        raise HTTPException(
            400,
            f"Ảnh nguồn rỗng hoặc quá lớn (tối đa {max_image_size // 1024 // 1024}MB)",
        )
    return data


def _approve_attach_credits(entity, cover, s, candidate_url):
    """Append the license/author/source credit for the uploaded cover URL; return credits list."""
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
    return credits


@router.post("/image-suggestions/{suggestion_id}/approve",
             summary="Approve an image suggestion",
             description="Approves a pending image suggestion: downloads, re-encodes to WebP, uploads to storage, and attaches to the entity with license credits.")
async def approve_image_suggestion(suggestion_id: str, request: Request):
    """Duyệt 1 ứng viên: tải ảnh → WebP 3 cỡ → R2 → gắn vào entity.images + lưu
    license/author/source vào attributes.image_credits (B6). Chỉ xử lý khi đang 'pending'."""
    validate_path_id(suggestion_id, "suggestion_id")
    _reject_non_ai_media()
    from fastapi.concurrency import run_in_threadpool
    from storage import MAX_IMAGE_SIZE
    from control_plane import saga as media_saga
    key = request.headers.get("Idempotency-Key") or request.headers.get("X-Request-ID") or uuid.uuid4().hex

    s = _imgq.get_suggestion(suggestion_id)
    if not s:
        raise HTTPException(404, "Đề xuất không tồn tại")
    prior = media_saga.peek_approval_receipt(key, suggestion_id, "admin")
    if prior is not None:
        payload = dict(prior.steps[0].get("receipt", {})) if prior.steps else {}
        return {"status": prior.status, "url": payload.get("url"),
                "sizes": payload.get("sizes") or {}, "error": prior.error,
                "orphan_cleanup_pending": prior.orphan_cleanup_pending,
                "durability_error": prior.durability_error}
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
    data = await _approve_fetch_image_data(
        candidate_url,
        run_in_threadpool,
        MAX_IMAGE_SIZE,
    )

    receipt = await run_in_threadpool(
        media_saga.approve_image_suggestion,
        suggestion_id,
        "admin",
        idempotency_key=key,
        _image_data=data,
    )
    if receipt.status == "committed":
        payload = dict(receipt.steps[0].get("receipt", {})) if receipt.steps else {}
        sizes = payload.get("sizes") or {}
        cover = payload.get("url")
        saved = db.get_entity(s["entity_id"]) or entity
        credits = ((saved.get("attributes") or {}).get("image_credits") or [])
        return {"status": "approved", "url": cover, "sizes": sizes,
                "images": saved.get("images") or [], "backend": getattr(media_saga.storage, "backend", ""),
                "credits": credits[-1] if credits else {}}
    return {"status": receipt.status, "error": receipt.error,
            "orphan_cleanup_pending": receipt.orphan_cleanup_pending}


@router.post("/image-suggestions/{suggestion_id}/reject",
              summary="Reject image suggestion",
              description="Reject a pending image suggestion by ID, optionally recording a reason. No files are downloaded or uploaded.")
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


@router.get("/featured",
            summary="List featured entities",
            description="Returns all currently featured entities with their sort order, name, and type.")
async def list_featured():
    def _query():
        if not db._use_pg:
            return {"featured": []}
        with db._conn() as conn:
            rows = db._fetchall(conn, """
                SELECT entity_id, sort_order, created_at
                FROM featured_entities ORDER BY sort_order
            """, ())
        items = [db._row_to_dict(r) for r in rows]
        batch = db.get_entities_batch([rd["entity_id"] for rd in items])
        result = []
        for rd in items:
            entity = batch.get(rd["entity_id"])
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


@router.post("/featured/{entity_id}",
             summary="Toggle entity featured status",
             description="Add or remove an entity from the featured list. If already featured, it is removed; otherwise it is added.")
async def toggle_featured(entity_id: str, request: Request):
    entity_id = validate_path_id(entity_id, "entity_id")
    entity = await asyncio.to_thread(db.get_entity, entity_id)
    if not entity:
        raise HTTPException(404, "Entity không tồn tại")
    admin_user = getattr(request.state, "admin_user", None)
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
                from control_plane.saga import record_entity_mutation
                record_entity_mutation(entity_id, actor_id=str(admin_user["id"]) if admin_user else "admin",
                                       reason="featured_toggle", correlation_id=f"featured:{entity_id}",
                                       before={"featured": True}, after={"featured": False}, revision=1,
                                       resource_type="featured", conn=conn)
                return False
            added_by = str(admin_user["id"]) if admin_user else None
            db._execute(conn, f"""
                INSERT INTO featured_entities (entity_id, added_by, sort_order)
                VALUES ({ph}, {ph}::uuid, (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM featured_entities))
            """, (entity_id, added_by))
            from control_plane.saga import record_entity_mutation
            record_entity_mutation(entity_id, actor_id=added_by or "admin",
                                   reason="featured_toggle", correlation_id=f"featured:{entity_id}",
                                   before={"featured": False}, after={"featured": True}, revision=1,
                                   resource_type="featured", conn=conn)
            return True
    is_featured = await asyncio.to_thread(_query)
    return {"entity_id": entity_id, "featured": is_featured}


# ── Collections CRUD (U-28) — dời NGUYÊN VĂN từ admin.py (lát 6 đợt cắt
# module 2026-08-29): cùng khuôn biên-tập-chọn-entity + scope content.editor
# với cụm /featured ngay trên (scope map ở lại admin.py — khớp theo path).
# Decorator path giữ từng ký tự — cha admin.router mang prefix "/admin" +
# dependencies require_admin/require_csrf qua include_router.


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


@router.get("/collections",
            summary="List curated collections",
            description="Returns all curated entity collections ordered by sort_order. Supports pagination via limit and offset.")
async def list_collections(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0, le=10000)):
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


@router.post("/collections", status_code=201,
             summary="Create a curated collection",
             description="Creates a new curated entity collection with a unique slug. Returns the created collection.")
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


@router.put("/collections/{collection_id}",
            summary="Update a collection",
            description="Updates fields of an existing collection. Only provided fields are modified.")
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


@router.delete("/collections/{collection_id}",
               summary="Delete a collection",
               description="Permanently deletes a curated collection by its ID.")
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


@router.get("/media",
            summary="List uploaded media files",
            description="Returns a paginated gallery of all images across entities with credit and duplicate detection stats.")
async def media_gallery(
    page: int = Query(1, ge=1, le=1000),
    limit: int = Query(50, ge=1, le=200),
    filter: str = Query("all", pattern="^(all|missing_credit|duplicate)$"),
):
    """B6a: Central media gallery — cached extraction, avoids re-scanning all entities per page."""
    def _query():
        import time as _time
        now = _time.time()
        if _media_cache["data"] is None or (now - _media_cache["ts"]) > _MEDIA_TTL:
            entities = db.all_entities()
            _media_cache["data"] = _extract_media_items(entities)
            _media_cache["ts"] = now
        cached = _media_cache["data"]
        media_items = list(cached["items"])
        url_usage = cached["url_usage"]
        total_images = cached["total_images"]
        no_credit_count = cached["no_credit_count"]
        dup_count = cached["dup_count"]

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


_media_cache: dict = {"ts": 0.0, "data": None}


_MEDIA_TTL = 120.0


def _media_parse_json_field(value, default):
    """Coerce a possibly-JSON-string field to a Python value; fall back to `default`."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return default
    return value


def _media_credits_by_url(image_credits) -> dict[str, dict]:
    credits_by_url: dict[str, dict] = {}
    if isinstance(image_credits, list):
        for credit_meta in image_credits:
            if not isinstance(credit_meta, dict):
                continue
            credit_url = credit_meta.get("url")
            if credit_url:
                credits_by_url[str(credit_url)] = credit_meta
    return credits_by_url


def _media_resolve_credit(img, credit_meta):
    """Resolve (credit, license_info) for one image from inline + registry metadata."""
    credit = ""
    license_info = ""
    if isinstance(img, dict):
        credit = img.get("credit") or img.get("author") or ""
        license_info = img.get("license", "")
    if not credit:
        credit = credit_meta.get("author") or credit_meta.get("credit") or ""
    if not license_info:
        license_info = credit_meta.get("license") or ""
    return credit, license_info


def _media_item_from_image(img, e, credits_by_url):
    """Build one media-gallery item from an image + its credit metadata; None if no URL."""
    if isinstance(img, str):
        url = img
    elif isinstance(img, dict):
        url = img.get("url", "")
    else:
        return None
    if not isinstance(url, str) or not url:
        return None
    credit_meta = credits_by_url.get(url, {})
    credit, license_info = _media_resolve_credit(img, credit_meta)
    return {
        "url": url,
        "entity_id": e.get("id", ""),
        "entity_name": e.get("name", ""),
        "entity_type": e.get("type", ""),
        "credit": credit,
        "license": license_info,
        "source": credit_meta.get("source") or "",
        "source_url": credit_meta.get("source_url") or "",
    }


def _extract_media_items(entities: list) -> dict:
    media_items = []
    url_usage: dict[str, list[str]] = {}
    for e in entities:
        images = _media_parse_json_field(e.get("images") or [], [])
        attrs = _media_parse_json_field(e.get("attributes") or {}, {})
        image_credits = attrs.get("image_credits") if isinstance(attrs, dict) else []
        credits_by_url = _media_credits_by_url(image_credits)
        for img in images:
            item = _media_item_from_image(img, e, credits_by_url)
            if item is None:
                continue
            media_items.append(item)
            url_usage.setdefault(item["url"], []).append(e.get("id", ""))
    return {
        "items": media_items,
        "url_usage": url_usage,
        "total_images": len(media_items),
        "no_credit_count": sum(1 for m in media_items if not m["credit"]),
        "dup_count": sum(1 for u, ids in url_usage.items() if len(ids) > 1),
    }


class ProvisionalDecisionBody(BaseModel):
    review_token: str = Field(..., min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")


def _record_provisional_decision(entity_id: str, actor_id: str, decision: str,
                                 before: dict, after: dict) -> None:
    from control_plane.saga import record_entity_mutation
    record_entity_mutation(
        entity_id, actor_id=actor_id, reason=f"provisional_{decision}",
        correlation_id=f"provisional:{decision}:{entity_id}",
        before=before, after=after,
        revision=int(before.get("revision") or 1) + 1,
        resource_type="entity", database=db,
    )


@router.get("/provisional",
            summary="List provisional entities",
            description="Returns auto-learned entities pending verification, along with queue statistics.")
async def list_provisional_entities():
    """Liệt kê các entity tự học CHƯA kiểm chứng (chờ duyệt)."""
    def _query():
        import kb_curation
        return {"provisional": kb_curation.list_provisional(), **kb_curation.stats()}
    return await asyncio.to_thread(_query)


@router.post("/provisional/{entity_id}/approve",
             summary="Approve provisional entity",
             description="Promotes a provisional auto-learned entity to verified status in the knowledge base.")
async def approve_provisional(entity_id: str, body: ProvisionalDecisionBody):
    """Duyệt 1 entity provisional → verified (tin cậy)."""
    validate_path_id(entity_id, "entity_id")
    def _query():
        import kb_curation
        result = kb_curation.promote(entity_id, body.review_token)
        if not result.get("ok"):
            error = result.get("error")
            status_code = 409 if error == "stale_review" else 404 if error == "not found" else 400
            raise HTTPException(status_code, error or "failed")
        return result
    return await asyncio.to_thread(_query)


@router.post("/provisional/{entity_id}/reject",
             summary="Reject provisional entity",
             description="Rejects and removes a provisional auto-learned entity from the knowledge base.")
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


@router.get("/claims",
            summary="List entity ownership claims",
            description="List entity ownership claims filtered by status for admin review. Supports pagination.")
async def list_claims(
    status: str = Query("pending", max_length=20),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0, le=10000),
):
    """U-30: List entity claims for admin review."""
    require_pg()
    valid_statuses = ("pending", "approved", "rejected", "all")
    if status not in valid_statuses:
        raise HTTPException(422, f"Status không hợp lệ. Cho phép: {', '.join(valid_statuses)}")

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
        def _claim_row(row):
            # Every other endpoint masks; this one did not, and it is the only
            # place in the API that returned a registered user's raw phone.
            item = dict(db._row_to_dict(row))
            if item.get("claimant_phone"):
                item["claimant_phone"] = _mask(str(item["claimant_phone"]))
            return item

        return {
            "claims": [_claim_row(r) for r in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    return await asyncio.to_thread(_query)


class ClaimDecisionBody(BaseModel):
    reason: str = Field("", max_length=1000)


def _apply_claim_decision(conn, claim_id: str, status: str, actor_id: str, reason: str,
                          *, reviewer_id: str | None = None) -> dict:
    """CAS a pending claim and append its immutable audit on the same connection."""
    if status not in {"approved", "rejected"}:
        raise ValueError("invalid_claim_status")
    ph = db._ph
    lock = " FOR UPDATE" if db._use_pg else ""
    cast = "::uuid" if db._use_pg else ""
    row = db._fetchone(conn, f"SELECT * FROM entity_claims WHERE id = {ph}{cast}{lock}", (claim_id,))
    if not row:
        return {"error": "not_found"}
    before = dict(db._row_to_dict(row))
    if before.get("status") != "pending":
        return {"error": "not_pending", "current_status": before.get("status")}
    persisted_reviewer = actor_id if reviewer_id is None and db._use_pg is False else reviewer_id
    after = {**before, "status": status, "reviewer_id": persisted_reviewer,
             "rejection_reason": reason if status == "rejected" else ""}
    if status == "approved":
        sql = f"UPDATE entity_claims SET status='approved', reviewer_id={ph}{cast}, reviewed_at=NOW() WHERE id={ph}{cast} AND status='pending'"
        params = (persisted_reviewer, claim_id)
    else:
        sql = f"UPDATE entity_claims SET status='rejected', reviewer_id={ph}{cast}, reviewed_at=NOW(), rejection_reason={ph} WHERE id={ph}{cast} AND status='pending'"
        params = (persisted_reviewer, reason, claim_id)
    updated = db._execute(conn, sql, params)
    if getattr(updated, "rowcount", 1) == 0:
        return {"error": "not_pending", "current_status": "pending"}
    from control_plane.saga import record_entity_mutation
    record_entity_mutation(
        claim_id, actor_id=actor_id, reason=reason or f"claim_{status}",
        correlation_id=f"claim:{claim_id}", before=before, after=after,
        revision=int(before.get("revision") or 1) + 1,
        resource_type="entity_claim", conn=conn, database=db,
    )
    return {"ok": True, "claimant_id": str(before.get("claimant_id")), "entity_id": before.get("entity_id")}


@router.post("/claims/{claim_id}/approve",
             summary="Approve an entity ownership claim",
             description="Approve a pending entity ownership claim. Notifies the claimant upon approval.")
async def approve_claim(claim_id: str, request: Request):
    """U-30: Approve an entity claim."""
    require_pg()
    claim_id = validate_path_id(claim_id, "claim_id")
    admin_user = getattr(request.state, "admin_user", None)

    def _approve():
        with db._conn() as conn:
            reviewer_id = str(admin_user["id"]) if admin_user else None
            return _apply_claim_decision(conn, claim_id, "approved", reviewer_id or "api-key-admin", "claim_approved",
                                         reviewer_id=reviewer_id)

    result = await asyncio.to_thread(_approve)
    if "error" in result:
        code = 404 if result["error"] == "not_found" else 409
        detail = "Không tìm thấy claim" if result["error"] == "not_found" else f"Claim đã xử lý ({result.get('current_status', '')})"
        raise HTTPException(code, detail)
    _log_mod_action("claim", claim_id, "approved")
    if result.get("claimant_id"):
        def _notify():
            create_notification(
                result["claimant_id"], "claim_approved",
                "Yêu cầu xác nhận doanh nghiệp của bạn đã được duyệt!",
                ref_type="entity", ref_id=result.get("entity_id", ""),
            )
        await asyncio.to_thread(_notify)
    return {"ok": True}


@router.post("/claims/{claim_id}/reject",
             summary="Reject an entity ownership claim",
             description="Reject a pending entity ownership claim with an optional reason. Notifies the claimant.")
async def reject_claim(claim_id: str, body: ClaimDecisionBody, request: Request):
    """U-30: Reject an entity claim with optional reason."""
    require_pg()
    claim_id = validate_path_id(claim_id, "claim_id")
    admin_user = getattr(request.state, "admin_user", None)

    def _reject():
        with db._conn() as conn:
            reviewer_id = str(admin_user["id"]) if admin_user else None
            return _apply_claim_decision(conn, claim_id, "rejected", reviewer_id or "api-key-admin", body.reason or "claim_rejected",
                                         reviewer_id=reviewer_id)

    result = await asyncio.to_thread(_reject)
    if "error" in result:
        code = 404 if result["error"] == "not_found" else 409
        detail = "Không tìm thấy claim" if result["error"] == "not_found" else f"Claim đã xử lý ({result.get('current_status', '')})"
        raise HTTPException(code, detail)
    _log_mod_action("claim", claim_id, "rejected", body.reason or None)
    if result.get("claimant_id"):
        def _notify():
            create_notification(
                result["claimant_id"], "claim_rejected",
                "Yêu cầu xác nhận doanh nghiệp của bạn chưa được duyệt.",
                ref_type="entity", ref_id=result.get("entity_id", ""),
            )
        await asyncio.to_thread(_notify)
    return {"ok": True}

_admin_volatile_caches.append(_media_cache)
