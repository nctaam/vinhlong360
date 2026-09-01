# -*- coding: utf-8 -*-
"""Miền ENTITY — mặt công khai. Bóc khỏi `public_api.py` (2026-08-28, bước 1b).

Lát thứ ba sau `chat/` và `llmops/`, theo khuôn `agent/cases/`: gói theo MIỀN,
phát `APIRouter` riêng, nơi gắn chỉ `include_router`.

RANH GIỚI TÍNH BẰNG BAO ĐÓNG BẮC CẦU, và có HAI quyết định chủ đích:

1. Bước 1a tách trước `agent/entity_read.py` — 10 helper đọc-entity bị KẸT GIỮA
   (cả gói này lẫn phần còn lại của `public_api` đều gọi). Không tách trước thì
   gói này phải import ngược `public_api` — vòng.

2. LOẠI hai route tuy URL nằm dưới `/entities/` nhưng thuộc miền KHÁC:
       /entities/{id}/report-stale   -> đính chính (kéo theo cả cụm REPORTS_FILE,
                                        _jsonl_lock, _file_legacy_correction…)
       /entities/{id}/view-contact   -> ghi nhận tiếp xúc (dùng JSONL logger)
   Giữ chúng lại thì bao đóng nuốt cả tầng báo-lỗi. URL không phải ranh giới
   miền; NGƯỜI GỌI và DỮ LIỆU mới là.

Sau hai quyết định đó: 60 ký hiệu / 1.413 dòng / 0 rò rỉ, và chỉ còn 3 tên phải
xử (`router` — gói này có router riêng; `logger`; `_rollout_enabled`).
"""
from __future__ import annotations

import asyncio
import json
import math
import re
import time as _time
from collections import Counter, OrderedDict
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Optional

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field

from auth_middleware import (
    get_current_user,
    require_csrf,
    require_pg,
    require_user,
    validate_path_id,
)
import knowledge
from data_quality import entity_quality
from database import canonical_verified_at, db
from control_plane.clock import system_clock
from features import HAS_AUTOCORRECT, HAS_RECOMMENDER, autocorrect, recommend
from middleware import get_client_ip

from api_schemas import (
    CollectionsResponse,
    CompareResponse,
    EntityDetailResponse,
    EntityListResponse,
    EntityMapResponse,
    EntityTypesResponse,
    FeaturedResponse,
    GalleryResponse,
    PopularResponse,
    TrendingResponse,
)

# Import KEP nhu public_api.py: `agent` duoc nap ca dang phang lan dang goi.
if __package__ and __package__ != "entities":
    from ..index_policy import (
        IndexPolicyDecision, decide_entity, decide_ward, public_ward_child_counts,
    )
    from ..launch_evidence import current_policy_evidence
    from ..trust_policy import build_explanation, derive_freshness, derive_source_tier
else:
    from index_policy import (
        IndexPolicyDecision, decide_entity, decide_ward, public_ward_child_counts,
    )
    from launch_evidence import current_policy_evidence
    from trust_policy import build_explanation, derive_freshness, derive_source_tier

from entity_read import (
    _FULL_SCAN_LIMIT,
    _warn_if_scan_truncated,
    _err,
    _is_public,
    _get_public_entity,
    _get_public_entities_batch,
    _filter_public_entities,
    _project_public_entity_media,
    _rollout_enabled,
    _public_entity_has_media,
    _gallery_editorial_images,
    _enrich_place,
    _get_place,
    _public_facilities_by_place,
)

logger = logging.getLogger(__name__)
# KHÔNG tự mang prefix: router này được mount qua public_api.router (prefix
# "/api") bằng include_router — tự mang /api nữa là /api/api/entities, đã đo.
router = APIRouter(tags=["entities"])


DEFAULT_RELATIONSHIP_LIMIT = 24


def _public_entities_by_place(place_id: str) -> list[dict]:
    return _filter_public_entities(db.entities_by_place(place_id))


def _public_index_policy_child_count(ward_id: object) -> int:
    """Count only strictly identified, policy-eligible content children."""
    if type(ward_id) is not str or not ward_id.strip():
        return 0
    return public_ward_child_counts(db.entities_by_place(ward_id)).get(ward_id, 0)


def _entity_detail_index_policy(entity: dict) -> IndexPolicyDecision:
    evidence = current_policy_evidence()
    if type(entity.get("type")) is str and entity["type"] == "place":
        return decide_ward(
            entity,
            public_child_count=_public_index_policy_child_count(entity.get("id")),
            evidence=evidence,
        )
    return decide_entity(entity, evidence)


def _filter_public_relationships(rels: list[dict]) -> list[dict]:
    other_ids = [r.get("other_id") for r in rels if r.get("other_id")]
    if not other_ids:
        return rels
    batch = _get_public_entities_batch(other_ids)
    return [r for r in rels if r.get("other_id") in batch]


def _days_since(iso: str | None) -> int | None:
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).days
    except (ValueError, TypeError, AttributeError):
        # naive date (no tz) → aware-minus-naive raises TypeError; treat as unknown
        return None


def _build_source_freshness(entity: dict) -> dict:
    """Source freshness for entity detail. P0-6: freshness_status phản ánh NGÀY
    KIỂM-CHỨNG-THỰC-ĐỊA thật (attributes.verifiedAt) — KHÔNG bao giờ dùng
    updatedAt (timestamp import) — nên re-import hàng loạt không thể giả badge
    "mới kiểm chứng"."""
    from data_quality import source_info
    src = source_info(entity)
    updated_at = entity.get("updatedAt")
    verified_at = canonical_verified_at(entity)
    days_since_update = _days_since(updated_at)
    days_since_verified = _days_since(verified_at)
    status = derive_freshness({"verified_at": verified_at})
    return {
        "source_title": src.get("title") or None,
        "source_url": src.get("url") or None,
        "source_tier": derive_source_tier(entity),
        "updated_at": updated_at,
        "verified_at": verified_at,
        "days_since_update": days_since_update,
        "days_since_verified": days_since_verified,
        "freshness_status": status,
    }


_PRACTICAL_FACTS_KEYS = [
    "hours", "admission_fee", "phone", "address", "website",
    "zalo", "parking", "best_time", "peak_hours", "tips",
    "price_range", "duration", "accessibility",
]


def _apply_practical_fact_fallbacks(facts: dict, attrs: dict) -> None:
    """U-07: fill standardized keys from alternate attribute names when missing."""
    if facts["hours"] is None:
        facts["hours"] = attrs.get("open_hours") or attrs.get("opening_hours")
    if facts["admission_fee"] is None:
        facts["admission_fee"] = attrs.get("admission") or attrs.get("ticket_price")
    if facts["price_range"] is None:
        facts["price_range"] = attrs.get("price") or attrs.get("gia")


def _build_practical_facts(entity: dict) -> dict:
    """U-07: Extract standardized practical info from entity attributes."""
    attrs = entity.get("attributes") or {}
    facts = {}
    for key in _PRACTICAL_FACTS_KEYS:
        facts[key] = attrs.get(key)
    _apply_practical_fact_fallbacks(facts, attrs)
    has_any = any(v is not None for v in facts.values())
    facts["_completeness"] = sum(1 for v in facts.values() if v is not None and v != "_completeness")
    return facts if has_any else facts


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


_MINIMAL_FIELDS = {"id", "name", "type", "summary", "image_descriptors", "place_name",
                    "place_area", "coordinates", "attributes"}


def _public_entity_revision(entity: dict) -> int:
    """The revision a reader is actually being served.

    Publication verification compares this against the revision it wrote, which
    is how a stale cache or prerender gets caught. That makes it a declared part
    of the projection rather than something surviving by accident of a
    permissive response model.
    """
    try:
        return max(1, int(entity.get("revision")))
    except (TypeError, ValueError):
        return 1


def _to_minimal(entity: dict) -> dict:
    out = {k: entity[k] for k in _MINIMAL_FIELDS if k in entity}
    descriptors = entity.get("image_descriptors")
    if isinstance(descriptors, list):
        out["image_descriptors"] = descriptors[:1]
    attrs = entity.get("attributes") or {}
    out["rating"] = attrs.get("rating")
    out["review_count"] = attrs.get("review_count", 0)
    return out


def _entity_card_shape(entity: dict, *, score: float | None = None, reason_vi: str = "") -> dict:
    projected = _project_public_entity_media(entity, limit=2)
    area = projected.get("place_area") or projected.get("area") or projected.get("legacyArea") or ""
    place = projected.get("place") or projected.get("place_name") or ""
    card = {
        "id": projected.get("id"),
        "name": projected.get("name", ""),
        "type": projected.get("type", ""),
        "summary": projected.get("summary", ""),
        "image_descriptors": projected["image_descriptors"],
        "place": place,
        "place_name": projected.get("place_name") or place,
        "place_area": area,
        "area": area,
        "score": round(float(score or 0), 4),
        "reason_vi": reason_vi,
    }
    if _rollout_enabled("RECOMMENDATION_EXPLANATIONS_V1"):
        card["explanation"] = build_explanation(
            entity, [reason_vi] if reason_vi else [], None
        )
    if _rollout_enabled("TRUST_DRAWER_V1"):
        card["source_tier"] = derive_source_tier(entity)
        card["freshness_status"] = derive_freshness(entity)
    return card


def _similar_reason_vi(reason: str) -> str:
    raw = str(reason or "")
    if "related" in raw:
        return "Lien quan trong ban do tri thuc"
    if "same_ward" in raw:
        return "Gan nhau trong cung xa phuong"
    if "same_area" in raw:
        return "Cung khu vuc kham pha"
    if "shared_tags" in raw:
        return "Co chu de trai nghiem gan nhau"
    if "same_type" in raw:
        return "Cung nhom noi dung"
    return "Phu hop de kham pha tiep"


@router.get("/entities", response_model=EntityListResponse,
            summary="List entities",
            description="Returns a paginated list of public entities. Supports filtering by type, area, search query, month, and sorting by rating/name/newest.")
async def list_entities(
    response: Response,
    type: Optional[str] = Query(None, max_length=100),
    area: Optional[str] = Query(None, max_length=50),
    q: Optional[str] = Query(None, max_length=200),
    month: Optional[int] = Query(None, ge=1, le=12),
    sort: Optional[str] = Query(None, pattern="^(rating|newest|name)$"),
    fields: Optional[str] = Query(None, pattern="^(minimal|full)$"),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0, le=10000),
):
    """Trả danh sách entity công khai đã phân trang kèm tổng số, lọc theo type/area/q/month và sort.

    type nhận nhiều giá trị phân tách bằng dấu phẩy (tối đa 10). Có q thì tìm bằng
    db.search_entities, không có thì liệt kê bằng db.list_entities. fields=minimal rút
    mỗi entity về tập trường tối thiểu.

    Hai điểm dễ hiểu nhầm: `sort` CHỈ có tác dụng ở nhánh không có q (db.search_entities
    không nhận tham số sort), và `type=place` không bao giờ khớp vì db.list_entities loại
    cứng `e.type != 'place'`.
    """
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=120"
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
    await asyncio.to_thread(_enrich_place, results)
    results = [_project_public_entity_media(entity) for entity in results]
    if fields == "minimal":
        results = [_to_minimal(e) for e in results]
    return {"total": total, "entities": results}


@router.get("/entities/{entity_id}/relationships",
            summary="Get entity relationships",
            description="Returns paginated relationships for a given entity. Supports filtering by relationship type and including nearby entities.")
async def get_entity_relationships(
    entity_id: str,
    response: Response,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0, le=10000),
    type: Optional[str] = Query(None, max_length=50),
    include_near: bool = True,
):
    """Trả quan hệ của một entity theo trang, đã loại quan hệ trỏ tới entity không công khai.

    total giữ tổng thật từ DB (đếm trước khi lọc) để phân trang không hụt.
    Entity không tồn tại hoặc không công khai → 404.
    """
    response.headers["Cache-Control"] = "public, max-age=120, stale-while-revalidate=300"
    validate_path_id(entity_id, "entity_id")
    def _query():
        e = _get_public_entity(entity_id)
        if not e:
            return None
        rels, t = db.get_relationships(
            entity_id, limit=limit, offset=offset,
            rel_type=type, include_near=include_near, return_total=True,
        )
        rels = _filter_public_relationships(rels)
        # `t` giữ tổng thật từ DB (return_total=True) cho pagination — KHÔNG ghi đè
        # bằng len(trang đã lọc) (sẽ đếm thiếu, client dừng phân trang sớm).
        return {"entity_id": entity_id, "total": t, "limit": limit,
                "offset": offset, "relationships": rels}
    result = await asyncio.to_thread(_query)
    if not result:
        return _err(404, "not_found")
    return result


@router.get("/featured", response_model=FeaturedResponse,
            summary="Get featured entities",
            description="Returns up to 20 editorially featured entities sorted by display order. Includes basic entity info and images.")
async def get_featured_entities(response: Response):
    """Trả tối đa 20 entity công khai được ghim trong bảng featured_entities, sắp theo sort_order.

    Chế độ không dùng Postgres trả về danh sách rỗng. Mỗi mục gồm id, name, type, summary,
    mô tả ảnh (1 ảnh), rating và toạ độ.
    """
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=600"
    def _query():
        if not db._use_pg:
            return {"featured": []}
        with db._conn() as conn:
            rows = db._fetchall(conn, """
                SELECT entity_id, sort_order FROM featured_entities
                ORDER BY sort_order LIMIT 20
            """, ())
        entity_ids = [db._row_to_dict(r)["entity_id"] for r in rows]
        batch = _get_public_entities_batch(entity_ids)
        result = []
        for eid in entity_ids:
            entity = batch.get(eid)
            if entity:
                projected = _project_public_entity_media(entity, limit=1)
                attrs = entity.get("attributes") or {}
                result.append({
                    "id": projected["id"],
                    "name": projected["name"],
                    "type": projected.get("type"),
                    "summary": projected.get("summary", ""),
                    "image_descriptors": projected["image_descriptors"],
                    "rating": attrs.get("rating"),
                    "coordinates": projected.get("coordinates"),
                })
        return {"featured": result}
    return await asyncio.to_thread(_query)


# ── Collections (U-28, public read-only) — dời NGUYÊN VĂN từ public_api.py
# (lát 6 đợt cắt module 2026-08-29): cùng khuôn biên-tập-chọn-entity với
# /featured ngay trên. Decorator path giữ từng ký tự — cha public_api.router
# mang prefix "/api" qua include_router.


@router.get("/collections", response_model=CollectionsResponse,
            summary="List public collections",
            description="Returns published editorial collections sorted by display order. Each collection includes title, description, cover image, and entity IDs.")
async def list_public_collections(response: Response, limit: int = Query(20, ge=1, le=100)):
    """Trả các collection đã publish theo sort_order, entity_ids đã lọc còn entity công khai.

    Cần Postgres (không có → 503).
    """
    require_pg()
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=600"
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
        collections = [db._row_to_dict(r) for r in rows]
        entity_ids = []
        for collection in collections:
            collection_ids = collection.get("entity_ids") or []
            if isinstance(collection_ids, str):
                collection_ids = json.loads(collection_ids)
            collection["entity_ids"] = collection_ids
            entity_ids.extend(collection_ids)
        public_entities = _get_public_entities_batch(entity_ids) if entity_ids else {}
        for collection in collections:
            collection["entity_ids"] = [
                entity_id for entity_id in collection["entity_ids"]
                if entity_id in public_entities
            ]
        return {"collections": collections}
    return await asyncio.to_thread(_query)


@router.get("/collections/{slug}",
            summary="Get collection by slug",
            description="Returns a single published collection by its URL slug with entity IDs resolved to full entity summaries.")
async def get_collection_by_slug(slug: str, response: Response):
    """Trả một collection đã publish theo slug, kèm entities đã lọc theo quyền công khai.

    Cần Postgres (không có → 503); slug không khớp collection đã publish → 404.
    """
    require_pg()
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=600"
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
        entities = _get_public_entities_batch(entity_ids) if entity_ids else {}
        col["entities"] = [
            _project_public_entity_media(entities[entity_id])
            for entity_id in entity_ids
            if entity_id in entities
        ]
        return col
    result = await asyncio.to_thread(_query)
    if not result:
        return _err(404, "not_found")
    return result


@router.get("/entity-types", response_model=EntityTypesResponse,
            summary="List entity types",
            description="Returns all entity types with their counts, ordered by frequency. Cached for 1 hour.")
async def entity_types(response: Response):
    """Trả số lượng entity CÔNG KHAI theo từng giá trị cột type, sắp giảm dần theo count.

    Áp cùng luật công khai với các endpoint public khác (bỏ `provisional` và
    `verified = 0`). Trước 2026-08-06 câu đếm chạy trên toàn bảng nên con số
    hiển thị lớn hơn số entity người dùng thật sự xem được.
    """
    response.headers["Cache-Control"] = "public, max-age=3600, stale-while-revalidate=7200"
    def _query():
        with db._conn() as conn:
            rows = db._fetchall(conn,
                "SELECT type, COUNT(*) as count FROM entities e"
                " WHERE (e.status IS NULL OR e.status != 'provisional')"
                " AND (e.verified IS NULL OR e.verified != 0)"
                " GROUP BY type ORDER BY count DESC", ())
        return [{"type": d["type"], "count": d["count"]} for d in (db._row_to_dict(r) for r in rows)]
    result = await asyncio.to_thread(_query)
    return {"types": result, "total": sum(t["count"] for t in result)}


@router.get("/entities/{entity_id}", response_model=EntityDetailResponse,
            summary="Get entity detail",
            description="Returns full entity detail including relationships, quality score, source freshness, practical facts, and index policy.")
async def get_entity(
    entity_id: str,
    relationship_limit: int = Query(DEFAULT_RELATIONSHIP_LIMIT, ge=0, le=100),
):
    """Trả chi tiết một entity công khai kèm quan hệ, quality, source_freshness và practical_facts.

    relationship_total giữ tổng quan hệ thật từ DB (trước khi lọc công khai).
    Entity không tồn tại hoặc không công khai → 404.
    """
    validate_path_id(entity_id, "entity_id")

    def _query():
        e = _get_public_entity(entity_id)
        if not e:
            return None
        e["index_policy"] = asdict(_entity_detail_index_policy(e))
        rels, rel_total = db.get_relationships(entity_id, limit=relationship_limit, return_total=True)
        rels = _filter_public_relationships(rels)
        # rel_total giữ tổng thật từ DB (return_total=True) — KHÔNG ghi đè bằng
        # len(trang đã lọc) để pagination quan hệ không đếm thiếu.
        e["relationship_total"] = rel_total
        e["relationships"] = rels
        _enrich_entity_place(e)
        e["revision"] = _public_entity_revision(e)
        e["quality"] = entity_quality(e)
        if _rollout_enabled("TRUST_DRAWER_V1"):
            e["source_freshness"] = _build_source_freshness(e)
        e["practical_facts"] = _build_practical_facts(e)
        return _project_public_entity_media(e)
    entity = await asyncio.to_thread(_query)
    if not entity:
        return _err(404, "not_found")
    return entity


@router.get("/entities/{entity_id}/stats",
            summary="Get entity social stats",
            description="Returns aggregated social stats for an entity: review count, average rating, post count, bookmark count, and follower count.")
async def get_entity_stats(entity_id: str, response: Response):
    """Trả số đếm cộng đồng của một entity: review, rating trung bình, post, bookmark, follower.

    Chỉ đếm post đã duyệt và chưa xoá mềm. Cần Postgres (không có → 503);
    entity không tồn tại hoặc không công khai → 404.
    """
    validate_path_id(entity_id, "entity_id")
    require_pg()
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=120"
    ph = db._ph
    def _query():
        e = _get_public_entity(entity_id)
        if not e:
            return None
        with db._conn() as conn:
            review_row = db._fetchone(conn, f"""
                SELECT COUNT(*) as review_count,
                       COALESCE(AVG(rating), 0) as avg_rating
                FROM posts
                WHERE entity_id = {ph} AND post_type = 'review'
                  AND moderation_status = 'approved' AND deleted_at IS NULL AND rating IS NOT NULL
            """, (entity_id,))
            post_row = db._fetchone(conn, f"""
                SELECT COUNT(*) as post_count FROM posts
                WHERE entity_id = {ph} AND moderation_status = 'approved' AND deleted_at IS NULL
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
        return _err(404, "not_found")
    return result


@router.get("/entities/{entity_id}/rating-breakdown",
            summary="Get entity rating breakdown",
            description="Returns 5-star rating distribution with counts, percentages, total reviews, and average rating for an entity. Requires Postgres.")
async def get_entity_rating_breakdown(entity_id: str, response: Response):
    """5-star rating distribution for an entity."""
    validate_path_id(entity_id, "entity_id")
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=120"
    require_pg()
    ph = db._ph

    def _query():
        e = _get_public_entity(entity_id)
        if not e:
            return None
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT rating, COUNT(*) as count
                FROM posts
                WHERE entity_id = {ph} AND post_type = 'review'
                  AND moderation_status = 'approved' AND deleted_at IS NULL AND rating IS NOT NULL
                GROUP BY rating ORDER BY rating DESC
            """, (entity_id,))
            total_row = db._fetchone(conn, f"""
                SELECT COUNT(*) as total, COALESCE(AVG(rating), 0) as avg
                FROM posts
                WHERE entity_id = {ph} AND post_type = 'review'
                  AND moderation_status = 'approved' AND deleted_at IS NULL AND rating IS NOT NULL
            """, (entity_id,))
        breakdown = {str(i): 0 for i in range(1, 6)}
        for r in rows:
            rd = db._row_to_dict(r)
            rating = rd.get("rating")
            count = rd.get("count", 0)
            if rating is not None:
                star = str(int(rating))
                if star in breakdown:
                    breakdown[star] = count
        td = db._row_to_dict(total_row) if total_row else {}
        total = td.get("total", 0)
        return {
            "entity_id": entity_id,
            "breakdown": breakdown,
            "total_reviews": total,
            "avg_rating": round(float(td.get("avg", 0)), 1),
            "percentages": {k: round(v / total * 100, 1) if total > 0 else 0 for k, v in breakdown.items()},
        }

    result = await asyncio.to_thread(_query)
    if not result:
        return _err(404, "not_found")
    return result


def _shape_review_row(rd: dict) -> dict:
    return {
        "id": str(rd["id"]),
        "content": rd["content"],
        "rating": rd.get("rating"),
        "like_count": rd.get("like_count", 0),
        "comment_count": rd.get("comment_count", 0),
        "created_at": str(rd.get("created_at", "")),
        "author": {
            "id": str(rd.get("user_id", "")),
            "display_name": rd.get("display_name", ""),
            "username": rd.get("username"),
            "avatar_url": rd.get("avatar_url"),
        },
    }


@router.get("/entities/{entity_id}/reviews",
            summary="Get entity reviews",
            description="Returns paginated user reviews for an entity with sorting, rating filter, distribution, and the current user's own review if logged in.")
async def get_entity_reviews(
    entity_id: str,
    response: Response,
    page: int = Query(1, ge=1, le=1000),
    limit: int = Query(20, ge=1, le=50),
    sort: str = Query("newest", pattern="^(newest|helpful|highest|lowest)$"),
    min_rating: int = Query(None, ge=1, le=5),
    user=Depends(get_current_user),
):
    """Trả review của một entity theo trang kèm tổng, rating trung bình và phân bố sao.

    Hỗ trợ sort newest/helpful/highest/lowest và lọc min_rating; user đăng nhập được kèm
    my_review (review mới nhất của chính họ, nội dung cắt 100 ký tự). Cần Postgres
    (không có → 503); entity không tồn tại hoặc không công khai → 404.
    """
    validate_path_id(entity_id, "entity_id")
    require_pg()
    response.headers["Cache-Control"] = "public, max-age=30, stale-while-revalidate=60"
    if not await asyncio.to_thread(_get_public_entity, entity_id):
        return _err(404, "not_found")
    ph = db._ph
    offset = (page - 1) * limit
    uid = str(user["id"]) if user else None
    _REVIEW_SORT = {"newest": "p.created_at DESC", "helpful": "p.like_count DESC, p.created_at DESC",
                     "highest": "p.rating DESC, p.created_at DESC", "lowest": "p.rating ASC, p.created_at DESC"}
    order = _REVIEW_SORT.get(sort, "p.created_at DESC")
    def _query():
        conditions = [f"p.entity_id = {ph}", "p.post_type = 'review'", "p.moderation_status = 'approved'", "p.deleted_at IS NULL"]
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
                  AND p.moderation_status = 'approved' AND p.deleted_at IS NULL AND p.rating IS NOT NULL
                GROUP BY p.rating ORDER BY p.rating DESC
            """, (entity_id,))
            my_review = None
            if uid:
                my_row = db._fetchone(conn, f"""
                    SELECT p.id, p.rating, p.content, p.created_at FROM posts p
                    WHERE p.entity_id = {ph} AND p.user_id = {ph}::uuid
                      AND p.post_type = 'review' AND p.moderation_status = 'approved' AND p.deleted_at IS NULL
                    ORDER BY p.created_at DESC LIMIT 1
                """, (entity_id, uid))
                if my_row:
                    mr = db._row_to_dict(my_row)
                    my_review = {"id": str(mr["id"]), "rating": mr["rating"],
                                 "content": mr["content"][:100], "created_at": str(mr.get("created_at", ""))}
        return rows, total_row, dist_rows, my_review
    rows, total_row, dist_rows, my_review = await asyncio.to_thread(_query)
    td = db._row_to_dict(total_row) if total_row else {}
    total = td.get("c", 0)
    distribution = {str(db._row_to_dict(r).get("rating", 0)): db._row_to_dict(r).get("cnt", 0) for r in dist_rows}
    reviews = [_shape_review_row(db._row_to_dict(r)) for r in rows]
    result = {
        "reviews": reviews,
        "total": total,
        "avg_rating": round(float(td.get("avg_rating", 0)), 1),
        "distribution": distribution,
        "page": page,
        "has_more": offset + limit < total,
    }
    if my_review is not None:
        result["my_review"] = my_review
    return result


@router.get("/places",
            summary="List places",
            description="Returns all place entities (wards/communes) with id, name, area, and level. Optionally filtered by area. Cached for 1 hour.")
async def list_places(response: Response, area: Optional[str] = Query(None, max_length=100)):
    """Trả entity type=place công khai (id, name, area, level), lọc tuỳ chọn theo area.

    Khi không truyền area, câu truy vấn giới hạn 500 bản ghi đầu sắp theo tên.
    """
    response.headers["Cache-Control"] = "public, max-age=3600, stale-while-revalidate=7200"
    db.initialize()
    def _query():
        ph = db._ph
        with db._conn() as conn:
            if area:
                rows = db._fetchall(conn,
                    f"SELECT id, name, area, level, status, verified FROM entities WHERE type = 'place' AND area = {ph} ORDER BY name",
                    (area,))
            else:
                rows = db._fetchall(conn,
                    "SELECT id, name, area, level, status, verified FROM entities WHERE type = 'place' ORDER BY name LIMIT 500")
        public_places = _filter_public_entities([db._row_to_dict(r) for r in rows])
        return [
            {"id": place["id"], "name": place["name"],
             "area": place.get("area"), "level": place.get("level")}
            for place in public_places
        ]
    return await asyncio.to_thread(_query)


_WARD_GROUPS = {
    "tourism": {"attraction", "nature", "experience", "craft_village", "history", "event"},
    "lodging": {"accommodation"},
    "products": {"product", "dish", "drink"},
}


@router.get("/places/{place_id}/overview",
            summary="Get place overview",
            description="Returns a ward/commune hub page with facilities, tourism, lodging, and product entities grouped by category with counts.")
async def place_overview(place_id: str, response: Response):
    """Trang hub 1 xã/phường: danh bạ hành chính + du lịch + lưu trú + sản phẩm.

    Gom theo placeId trong 1 lượt gọi. facilities rỗng đến khi có dữ liệu thật (Track-H 13.6).
    """
    validate_path_id(place_id, "place_id")
    def _query():
        p = _get_public_entity(place_id)
        if not p or p.get("type") != "place":
            return None
        ents = _public_entities_by_place(place_id)
        groups: dict[str, list] = {"tourism": [], "lodging": [], "products": [], "other": []}
        for e in ents:
            t = e.get("type")
            placed = False
            projected = _project_public_entity_media(e)
            for g, types in _WARD_GROUPS.items():
                if t in types:
                    groups[g].append(projected)
                    placed = True
                    break
            if not placed:
                groups["other"].append(projected)
        return {
            "place": {"id": p["id"], "name": p.get("name"), "area": p.get("area"),
                      "level": p.get("level"), "summary": p.get("summary"),
                      "attributes": p.get("attributes", {}),
                      "coordinates": p.get("coordinates")},
            "facilities": _public_facilities_by_place(place_id),
            "counts": {g: len(v) for g, v in groups.items()},
            "tourism": groups["tourism"],
            "lodging": groups["lodging"],
            "products": groups["products"],
            "other": groups["other"],
        }
    result = await asyncio.to_thread(_query)
    if not result:
        return _err(404, "Không phải xã/phường")
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=60"
    return result


_DAY_PLAN_SLOTS = [
    {"label": "sáng", "start": "08:00", "duration_min": 60},
    {"label": "sáng", "start": "09:30", "duration_min": 45},
    {"label": "trưa", "start": "11:00", "duration_min": 60},
    {"label": "chiều", "start": "13:30", "duration_min": 60},
    {"label": "chiều", "start": "15:00", "duration_min": 45},
    {"label": "chiều", "start": "16:30", "duration_min": 45},
]


def _haversine_km(a: list | None, b: list | None) -> float:
    if not a or not b or len(a) < 2 or len(b) < 2:
        return 999.0
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(h))


def _select_day_plan_candidates(ents: list[dict], center) -> list[dict]:
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
    return candidates


def _build_day_plan_stops(candidates: list[dict]) -> list[dict]:
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
    return stops


@router.get("/places/{place_id}/day-plan",
            summary="Get place day plan",
            description="Returns a suggested one-day itinerary for a ward/commune with diverse entity types ordered by proximity. Includes time slots and durations.")
async def place_day_plan(place_id: str, response: Response):
    """Gợi ý lịch trình 1 ngày cho xã/phường — đa dạng loại hình, sắp theo khoảng cách."""
    validate_path_id(place_id, "place_id")

    def _query():
        p = _get_public_entity(place_id)
        if not p or p.get("type") != "place":
            return None
        ents = _public_entities_by_place(place_id)
        center = p.get("coordinates")
        candidates = _select_day_plan_candidates(ents, center)
        stops = _build_day_plan_stops(candidates)
        total_min = sum(s["visit_duration_min"] for s in stops)
        return {
            "place": {"id": p["id"], "name": p.get("name"), "area": p.get("area")},
            "stops": stops,
            "total_stops": len(stops),
            "total_duration_min": total_min,
        }

    result = await asyncio.to_thread(_query)
    if not result:
        return _err(404, "Không phải xã/phường")
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=60"
    return result


@router.get("/entities/{entity_id}/gallery",
            response_model=GalleryResponse,
            summary="Get entity image gallery",
            description="Returns all images for an entity including editorial images and user review photos with credits and alt text.")
async def get_entity_gallery(entity_id: str, response: Response):
    """Trả danh sách mô tả ảnh biên tập có thể render của một entity công khai.

    Chỉ lấy ảnh của entity qua describe_entity_images (không kèm ảnh từ review người dùng);
    entity không tồn tại hoặc không công khai → 404.
    """
    validate_path_id(entity_id, "entity_id")
    response.headers["Cache-Control"] = "public, max-age=120, stale-while-revalidate=300"

    entity = await asyncio.to_thread(_get_public_entity, entity_id)
    if not entity:
        return _err(404, "not_found")

    images = _gallery_editorial_images(entity)

    return {"images": images}


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


def _int0(v) -> int:
    """int() null-safe: NULL/None/'' → 0 (dùng cho review stats từ DB)."""
    return int(v or 0)


@router.get("/entities/{entity_id}/review-stats",
            summary="Get entity review stats",
            description="Returns review statistics for an entity: average rating, distribution by star, and frequently mentioned keywords extracted from review text.")
async def get_review_stats(entity_id: str, response: Response):
    """Trả thống kê review của entity: điểm trung bình, số lượng, phân bố sao và từ khoá hay nhắc.

    Từ khoá lấy từ 200 review mới nhất (unigram/bigram xuất hiện >= 2 lần, đã bỏ stopword).
    Cache tiến trình 300 giây; chế độ không dùng Postgres hoặc truy vấn lỗi → kết quả rỗng;
    entity không tồn tại hoặc không công khai → 404.
    """
    validate_path_id(entity_id, "entity_id")
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=600"

    entity = await asyncio.to_thread(_get_public_entity, entity_id)
    if not entity:
        return _err(404, "not_found")

    now = _time.time()
    cached = _REVIEW_STATS_CACHE.get(entity_id)
    if cached and now - cached[0] < _REVIEW_STATS_TTL:
        return cached[1]

    _empty = {"avg": 0, "count": 0, "distribution": {}, "mentions": []}

    if not db._use_pg:
        return _empty

    ph = db._ph

    def _query():
        with db._conn() as conn:
            dist_rows = db._fetchall(conn, f"""
                SELECT rating, COUNT(*) as cnt
                FROM posts
                WHERE entity_id = {ph} AND post_type = 'review'
                    AND moderation_status = 'approved' AND deleted_at IS NULL AND rating IS NOT NULL
                GROUP BY rating
            """, (entity_id,))
            content_rows = db._fetchall(conn, f"""
                SELECT content FROM posts
                WHERE entity_id = {ph} AND post_type = 'review'
                    AND moderation_status = 'approved' AND deleted_at IS NULL AND content IS NOT NULL
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
        rating = _int0(r.get("rating"))
        cnt = _int0(r.get("cnt"))
        distribution[str(rating)] = cnt
        total += cnt
        weighted_sum += rating * cnt

    avg = round(weighted_sum / total, 1) if total > 0 else 0

    texts = [db._row_to_dict(r)["content"] for r in content_rows]
    mentions = _extract_mentions(texts)

    result = {"avg": avg, "count": total, "distribution": distribution, "mentions": mentions}
    _REVIEW_STATS_CACHE[entity_id] = (now, result)
    if len(_REVIEW_STATS_CACHE) > 500:
        oldest = min(_REVIEW_STATS_CACHE, key=lambda k: _REVIEW_STATS_CACHE[k][0])
        _REVIEW_STATS_CACHE.pop(oldest, None)
    return result


_similar_cache: OrderedDict[str, tuple[float, list]] = OrderedDict()


_SIMILAR_TTL = 300  # 5 min cache


def _build_similar_cards(raw_items: list[dict], full_entities: dict, entities_map: dict) -> list[dict]:
    cards: list[dict] = []
    for item in raw_items:
        candidate = full_entities.get(str(item.get("id"))) or entities_map.get(str(item.get("id"))) or item
        reason_vi = _similar_reason_vi(str(item.get("reason") or ""))
        card = _entity_card_shape(candidate, score=float(item.get("score") or 0), reason_vi=reason_vi)
        card["reason"] = item.get("reason", "")
        cards.append(card)
    return cards


def _compute_similar_entities(entity_id: str, limit: int) -> list[dict] | None:
    try:
        import knowledge
        knowledge._ensure()
        entities_map = {eid: e for eid, e in knowledge._entities.items() if _is_public(e)}
        rels = knowledge._relationships if hasattr(knowledge, "_relationships") else []
    except Exception:
        logger.warning("Knowledge load failed for recommendations", exc_info=True)
        return None
    if entity_id not in entities_map:
        return None
    from recommender import recommend_by_entity
    raw_items = recommend_by_entity(entity_id, entities_map, rels, limit=limit)
    entity_ids = [str(item.get("id")) for item in raw_items if item.get("id")]
    full_entities = db.get_entities_batch(entity_ids) if entity_ids else {}
    if full_entities:
        _enrich_place(list(full_entities.values()))
    return _build_similar_cards(raw_items, full_entities, entities_map)


@router.get("/entities/{entity_id}/similar",
            summary="Get similar entities",
            description="Returns rule-based similar entity recommendations based on type, area, and relationship graph. No ML required. Cached for 5 minutes.")
async def get_similar_entities(
    entity_id: str,
    response: Response,
    limit: int = Query(6, ge=1, le=20),
):
    """U-29: Rule-based similar entity recommendations (no ML)."""
    validate_path_id(entity_id, "entity_id")
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=600"
    if not await asyncio.to_thread(_get_public_entity, entity_id):
        return _err(404, "not_found")

    now = _time.time()
    cache_key = f"{entity_id}:{limit}"
    cached = _similar_cache.get(cache_key)
    if cached and now - cached[0] < _SIMILAR_TTL:
        _similar_cache.move_to_end(cache_key)
        return {"entity_id": entity_id, "similar": cached[1]}

    result = await asyncio.to_thread(_compute_similar_entities, entity_id, limit)
    if result is None:
        entity = await asyncio.to_thread(_get_public_entity, entity_id)
        if not entity:
            return _err(404, "not_found")
        return {"entity_id": entity_id, "similar": []}

    _similar_cache[cache_key] = (now, result)
    while len(_similar_cache) > 200:
        _similar_cache.popitem(last=False)

    return {"entity_id": entity_id, "similar": result}


@router.get("/entities/{entity_id}/nearby",
            summary="Get nearby entities",
            description="Returns entities within a given radius (km) of the specified entity, sorted by distance. Optionally filtered by entity type.")
async def get_nearby_entities(
    entity_id: str,
    response: Response,
    limit: int = Query(10, ge=1, le=30),
    radius_km: float = Query(10.0, ge=0.5, le=50.0),
    type: str = Query(None, max_length=50),
):
    """Trả entity công khai nằm trong bán kính radius_km quanh một entity, sắp theo khoảng cách.

    Quét tối đa 3000 entity và tính khoảng cách haversine, lọc tuỳ chọn theo type.
    Entity gốc không tồn tại/không công khai → 404; entity gốc thiếu toạ độ hợp lệ →
    trả danh sách rỗng kèm message.
    """
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=600"
    validate_path_id(entity_id, "entity_id")
    entity = await asyncio.to_thread(_get_public_entity, entity_id)
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


@router.get("/entities/{entity_id}/qa",
            dependencies=[Depends(require_pg)],
            summary="Get entity Q&A",
            description="Returns paginated Q&A posts for an entity with accepted answer resolution. Questions with best answers are shown first. Requires Postgres.")
async def get_entity_qa(
    entity_id: str,
    response: Response,
    page: int = Query(1, ge=1, le=100),
    limit: int = Query(10, ge=1, le=50),
):
    """U-09: Surface Q&A posts for an entity with accepted answer resolution."""
    validate_path_id(entity_id, "entity_id")
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=120"

    entity = await asyncio.to_thread(_get_public_entity, entity_id)
    if not entity:
        return _err(404, "not_found")

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
                  AND p.moderation_status = 'approved' AND p.deleted_at IS NULL
                ORDER BY (CASE WHEN p.best_answer_id IS NOT NULL THEN 0 ELSE 1 END),
                         p.like_count DESC, p.created_at DESC
                LIMIT {ph} OFFSET {ph}
            """, (entity_id, limit, offset))

            total_row = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM posts
                WHERE entity_id = {ph} AND post_type = 'question'
                  AND moderation_status = 'approved' AND deleted_at IS NULL
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


class EntityClaimIn(BaseModel):
    business_name: str = Field(..., min_length=2, max_length=200)
    contact_phone: str = Field(..., min_length=10, max_length=15)
    contact_email: str = Field("", max_length=200)
    evidence: str = Field("", max_length=2000)


@router.post("/entities/{entity_id}/claim",
             dependencies=[Depends(require_pg)],
             summary="Submit entity ownership claim",
             description="Submits a business ownership claim for an entity. Requires authentication and CSRF. Limited to 3 claims per day per user. Requires Postgres.")
async def submit_entity_claim(entity_id: str, payload: EntityClaimIn, request: Request, user=Depends(require_user), _csrf=Depends(require_csrf)):
    """Nhận yêu cầu xác nhận quyền sở hữu một entity từ user đăng nhập, ghi vào bảng entity_claims.

    Giới hạn 3 yêu cầu/ngày mỗi user; entity không tồn tại/không công khai → 404; user đã có
    yêu cầu ở trạng thái pending hoặc approved cho entity đó → 409. Tên doanh nghiệp và
    evidence được HTML-escape trước khi lưu. Cần Postgres và CSRF hợp lệ.
    """
    validate_path_id(entity_id, "entity_id")
    from ratelimit import check_rate
    check_rate(f"claim:{user['id']}", 3, 86400, "Chỉ được gửi 3 yêu cầu xác nhận/ngày.")
    uid = str(user["id"])
    entity = await asyncio.to_thread(_get_public_entity, entity_id)
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


def _coords_in_bbox(lat, lng, north, south, east, west) -> bool:
    if not (south <= lat <= north):
        return False
    if west <= east:
        return west <= lng <= east
    return lng >= west or lng <= east


def _map_search_shape(e: dict, coords: list) -> dict:
    projected = _project_public_entity_media(e, limit=1)
    return {
        "id": projected.get("id"),
        "name": projected.get("name"),
        "type": projected.get("type"),
        "coordinates": coords,
        "place": projected.get("place"),
        "summary": (projected.get("summary") or "")[:150],
        "image_descriptors": projected["image_descriptors"],
    }


@router.get("/entities/map", response_model=EntityMapResponse,
            summary="Search entities by bounding box",
            description="Returns entities within a geographic bounding box for map display. Supports entity type filter. Returns coordinates, summary, and first image.")
async def entities_map_search(
    response: Response,
    north: float = Query(..., ge=-90, le=90),
    south: float = Query(..., ge=-90, le=90),
    east: float = Query(..., ge=-180, le=180),
    west: float = Query(..., ge=-180, le=180),
    entity_type: str = Query(None, max_length=50),
    limit: int = Query(100, ge=1, le=500),
):
    """Entities within a bounding box for map display."""
    response.headers["Cache-Control"] = "public, max-age=120, stale-while-revalidate=300"
    if north <= south:
        raise HTTPException(400, "Giá trị north phải lớn hơn south")
    def _query():
        entities = db.list_entities(limit=_FULL_SCAN_LIMIT, public_only=True)
        _warn_if_scan_truncated(entities, _FULL_SCAN_LIMIT, "entity trong khung bản đồ")
        results = []
        for e in entities:
            coords = e.get("coordinates")
            if not coords or not isinstance(coords, list) or len(coords) < 2:
                continue
            if not _coords_in_bbox(coords[0], coords[1], north, south, east, west):
                continue
            if entity_type and e.get("type") != entity_type:
                continue
            results.append(_map_search_shape(e, coords))
            if len(results) >= limit:
                break
        return results
    results = await asyncio.to_thread(_query)
    return {"entities": results, "total": len(results), "bbox": {"north": north, "south": south, "east": east, "west": west}}


@router.get("/entities/trending", response_model=TrendingResponse,
            summary="Get trending entities",
            description="Returns entities with the most activity (posts, reviews, bookmarks) in a recent time period. Filterable by entity type. Requires Postgres.")
async def entities_trending(
    days: int = Query(7, ge=1, le=90),
    entity_type: str = Query(None, max_length=50),
    limit: int = Query(10, ge=1, le=50),
    response: Response = None,
):
    """Entities with most activity (posts+reviews+bookmarks) in recent days."""
    require_pg()
    ph = db._ph
    if response:
        response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=600"

    def _query():
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT entity_id,
                       COUNT(*) as activity_count,
                       COUNT(*) FILTER (WHERE post_type = 'review') as review_count,
                       COALESCE(AVG(rating) FILTER (WHERE rating IS NOT NULL), 0) as avg_rating
                FROM posts
                WHERE entity_id IS NOT NULL
                  AND moderation_status = 'approved' AND deleted_at IS NULL
                  AND created_at >= NOW() - INTERVAL '1 day' * {ph}
                GROUP BY entity_id
                ORDER BY activity_count DESC, review_count DESC
                LIMIT {ph}
            """, (days, limit * 3))
        candidates = [db._row_to_dict(r) for r in rows]
        batch = _get_public_entities_batch([c["entity_id"] for c in candidates])
        results = []
        for c in candidates:
            e = batch.get(c["entity_id"])
            if not e:
                continue
            if entity_type and e.get("type") != entity_type:
                continue
            projected = _project_public_entity_media(e, limit=1)
            results.append({
                "entity_id": c["entity_id"],
                "name": projected.get("name"),
                "type": projected.get("type"),
                "place": projected.get("place"),
                "coordinates": projected.get("coordinates"),
                "image_descriptors": projected["image_descriptors"],
                "activity_count": c["activity_count"],
                "review_count": c["review_count"],
                "avg_rating": round(float(c["avg_rating"]), 1),
            })
            if len(results) >= limit:
                break
        return {"entities": results, "total": len(results), "period_days": days}

    return await asyncio.to_thread(_query)


@router.get("/entities/compare", response_model=CompareResponse,
            summary="Compare entities side by side",
            description="Returns side-by-side comparison data for 2-5 entities. Includes practical attributes (hours, phone, address) and quality scores.")
async def compare_entities(
    request: Request,
    response: Response,
    ids: str = Query(..., min_length=1, max_length=500),
):
    """Side-by-side entity comparison. Pass comma-separated IDs (max 5)."""
    response.headers["Cache-Control"] = "public, max-age=120, stale-while-revalidate=300"
    from ratelimit import check_rate
    check_rate(f"compare:{get_client_ip(request)}", 20, 60,
               "Quá nhiều yêu cầu. Vui lòng thử lại sau.")
    id_list = [validate_path_id(i.strip(), "entity_id") for i in ids.split(",") if i.strip()][:5]
    if len(id_list) < 2:
        raise HTTPException(400, "Cần ít nhất 2 entity để so sánh")

    def _query():
        batch = _get_public_entities_batch(id_list)
        results = []
        for eid in id_list:
            e = batch.get(eid)
            if not e:
                continue
            projected = _project_public_entity_media(e, limit=3)
            attrs = e.get("attributes", {})
            if isinstance(attrs, str):
                try:
                    attrs = json.loads(attrs)
                except (json.JSONDecodeError, ValueError):
                    attrs = {}
            results.append({
                "id": projected["id"], "name": projected.get("name", ""),
                "type": projected.get("type", ""),
                "place": projected.get("place", ""),
                "summary": (projected.get("summary") or "")[:300],
                "image_descriptors": projected["image_descriptors"],
                "coordinates": projected.get("coordinates"),
                "attributes": {
                    "hours": attrs.get("hours"),
                    "phone": attrs.get("phone"),
                    "address": attrs.get("address"),
                    "admission_fee": attrs.get("admission_fee"),
                    "parking": attrs.get("parking"),
                },
                "quality_score": entity_quality(e),
            })
        return results

    entities = await asyncio.to_thread(_query)
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=120"
    return {"entities": entities, "count": len(entities)}


def _filter_popular_entities(all_entities: list[dict], entity_type: str | None, area: str | None) -> list[dict]:
    if entity_type:
        all_entities = [e for e in all_entities if e.get("type") == entity_type]
    if area:
        all_entities = [e for e in all_entities
                       if area.lower() in (e.get("place", "") or "").lower()
                       or area.lower() in (e.get("area", "") or "").lower()]
    return all_entities


def _score_popular_entity(e: dict) -> float:
    rc = e.get("rating_count", 0) or 0
    avg = e.get("rating_avg", 0) or 0
    has_img = 1 if _public_entity_has_media(e) else 0
    eq = entity_quality(e)
    eq_score = eq.get("score", 0) if isinstance(eq, dict) else eq
    return rc * 2 + avg * 3 + has_img * 5 + eq_score * 0.1


def _shape_popular_entity(e: dict) -> dict:
    projected = _project_public_entity_media(e, limit=2)
    return {
        "id": projected["id"], "name": projected.get("name", ""),
        "type": projected.get("type", ""),
        "place": projected.get("place", ""),
        "summary": (projected.get("summary") or "")[:200],
        "image_descriptors": projected["image_descriptors"],
        "rating_count": e.get("rating_count", 0) or 0,
        "rating_avg": round(float(e.get("rating_avg", 0) or 0), 1),
        "quality_score": entity_quality(e),
    }


@router.get("/entities/popular", response_model=PopularResponse,
            summary="Get popular entities",
            description="Returns entities ranked by a composite popularity score based on review count, rating, images, and quality. Filterable by type and area.")
async def popular_entities(
    request: Request,
    response: Response,
    entity_type: Optional[str] = Query(None, max_length=50),
    area: Optional[str] = Query(None, max_length=100),
    limit: int = Query(10, ge=1, le=50),
):
    """Popular entities by review count + rating. Filter by type and area."""
    from ratelimit import check_rate
    check_rate(f"popular:{get_client_ip(request)}", 20, 60,
               "Quá nhiều yêu cầu. Vui lòng thử lại sau.")

    def _query():
        all_entities = db.list_entities(limit=_FULL_SCAN_LIMIT, public_only=True)
        _warn_if_scan_truncated(all_entities, _FULL_SCAN_LIMIT, "bảng phổ biến")
        all_entities = _filter_popular_entities(all_entities, entity_type, area)
        scored = [(_score_popular_entity(e), e) for e in all_entities]
        scored.sort(key=lambda x: -x[0])
        return [_shape_popular_entity(e) for _, e in scored[:limit]]

    results = await asyncio.to_thread(_query)
    response.headers["Cache-Control"] = "public, max-age=120, stale-while-revalidate=300"
    return {"entities": results, "entity_type": entity_type, "area": area}


@router.get("/entities/search",
            summary="Advanced entity search",
            description="Entity search with advanced filters: type, area, image presence, and sort order. Returns paginated results with enriched place data.")
async def entity_search(
    request: Request,
    response: Response,
    q: str = Query("", max_length=200),
    entity_type: Optional[str] = Query(None, max_length=50),
    area: Optional[str] = Query(None, max_length=100),
    has_image: Optional[bool] = Query(None),
    sort: str = Query("relevance", max_length=20),
    page: int = Query(1, ge=1, le=200),
    limit: int = Query(20, ge=1, le=50),
):
    """Entity search with type, area, image, and sort filters."""
    from ratelimit import check_rate
    check_rate(f"esearch:{get_client_ip(request)}", 30, 60,
               "Tìm kiếm quá nhanh. Vui lòng thử lại sau.")
    offset = (page - 1) * limit
    all_entities = await asyncio.to_thread(
        db.search_entities, q=q or None, entity_type=entity_type, area=area,
        limit=500, public_only=True
    )
    if has_image is True:
        all_entities = [e for e in all_entities if _public_entity_has_media(e)]
    elif has_image is False:
        all_entities = [e for e in all_entities if not _public_entity_has_media(e)]
    if sort == "name":
        all_entities.sort(key=lambda e: e.get("name", "").lower())
    elif sort == "newest":
        all_entities.sort(key=lambda e: str(e.get("updatedAt", "")), reverse=True)
    total = len(all_entities)
    page_items = all_entities[offset:offset + limit]
    _enrich_place(page_items)
    page_items = [_project_public_entity_media(entity) for entity in page_items]
    response.headers["Cache-Control"] = "public, max-age=30, stale-while-revalidate=60"
    return {
        "entities": page_items, "total": total,
        "page": page, "has_more": offset + limit < total,
        "filters": {
            "entity_type": entity_type, "area": area,
            "has_image": has_image, "sort": sort,
        },
    }


# ── Mặt tri thức TOP-LEVEL (server.py về nhà 2026-08-29, lát 9) ──────────────
# /recommend /autocorrect /graph: truy hồi/gợi ý trên knowledge — miền entities,
# nhưng path là top-level (KHÔNG /api) nên KHÔNG được gộp vào `router` ở trên
# (router đó GỘP vào public_router prefix /api — test_entities_api_boundary ép
# mọi route của nó nằm dưới /api). Router PHỤ tên RIÊNG (mìn R20.9 tên-biến-
# router 2026-08-18: hai biến cùng tên `router` làm resolver coi module cũ là
# chưa mount), server.py mount 1 dòng: app.include_router(top_router).

top_router = APIRouter()


@top_router.get("/recommend")
async def recommend_endpoint(
    entity_id: str = Query(None, max_length=200), month: int = Query(None, ge=1, le=12),
    weather: str = Query(None, max_length=50), time_of_day: str = Query(None, max_length=50),
    limit: int = Query(10, ge=1, le=100),
):
    if not HAS_RECOMMENDER:
        raise HTTPException(503, detail="Recommender not available")
    def _rec():
        knowledge._ensure()
        ctx = {}
        if entity_id:
            ctx["entity_id"] = entity_id
        if month:
            ctx["month"] = month
        else:
            ctx["month"] = system_clock.now_vietnam().month
        if weather:
            ctx["weather"] = weather
        if time_of_day:
            ctx["time_of_day"] = time_of_day
        ctx["entities"] = knowledge._entities
        ctx["relationships"] = knowledge._relationships if hasattr(knowledge, '_relationships') else []
        ctx["limit"] = limit
        return recommend(ctx)
    return await asyncio.to_thread(_rec)


@top_router.get("/autocorrect")
async def autocorrect_endpoint(q: str):
    if not HAS_AUTOCORRECT:
        return {"original": q, "corrected": q, "was_corrected": False}
    return await asyncio.to_thread(autocorrect, q)


@top_router.get("/graph")
async def graph_endpoint(entity_id: str, hops: int = 2, max_nodes: int = 30):
    """Return subgraph data for knowledge graph visualization."""
    from agentic_rag import graph_expand
    return await asyncio.to_thread(lambda: graph_expand(entity_id, max_hops=min(hops, 4), max_nodes=min(max_nodes, 50)))
