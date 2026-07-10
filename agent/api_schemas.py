# -*- coding: utf-8 -*-
"""Pydantic response models cho public_api (SP3 W6.3).

Chiến lược AN TOÀN chống field-strip (đã verify thực nghiệm FastAPI):
- `response_model=StrictModel` mặc định LỌC BỎ field không khai → thiếu = vỡ FE.
- Base `ApiModel` đặt `extra="allow"` → FastAPI GIỮ NGUYÊN mọi field trả về
  (kể cả field không khai) → KHÔNG bao giờ strip → FE luôn nhận đủ.
- Mảng dùng `list` (untyped) → không validate item → không 500 do item mismatch.
- Field top-level khai `| None`/mặc định → validate nhẹ + document, gần như không 500.

Giá trị: OpenAPI document shape + validate nhẹ contract, mà TUYỆT ĐỐI không rủi ro
strip/500. Item-shape chi tiết đi qua nhờ extra="allow" (FE nhận nguyên).
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ApiModel(BaseModel):
    """Base: extra='allow' → không strip field trả về (an toàn FE)."""
    model_config = ConfigDict(extra="allow")


# ── list / catalog endpoints ─────────────────────────────────────────
class EntityTypesResponse(ApiModel):
    types: list = []
    total: int | None = None


class AreasResponse(ApiModel):
    areas: list = []
    total_places: int | None = None


class EntityListResponse(ApiModel):
    entities: list = []
    total: int | None = None


class FeaturedResponse(ApiModel):
    featured: list = []


class EventsResponse(ApiModel):
    events: list = []
    total: int | None = None


class CollectionsResponse(ApiModel):
    collections: list = []


# ── map / discovery endpoints ────────────────────────────────────────
class EntityMapResponse(ApiModel):
    entities: list = []
    total: int | None = None
    bbox: dict | None = None


class TrendingResponse(ApiModel):
    entities: list = []
    total: int | None = None
    period_days: int | None = None


class CompareResponse(ApiModel):
    entities: list = []
    count: int | None = None


class PopularResponse(ApiModel):
    entities: list = []
    entity_type: str | None = None
    area: str | None = None


class AutocompleteResponse(ApiModel):
    suggestions: list = []


# ── search (đa mảng) ─────────────────────────────────────────────────
class SearchResponse(ApiModel):
    q: str | None = None
    entities: list = []
    posts: list = []
    users: list = []
    results: list = []
    suggestions: list = []
    total: int | None = None


# ── batch-2: endpoint shape phức tạp (đo bằng cách gọi endpoint thật) ──
class HomepageResponse(ApiModel):
    seasonal: list = []
    experiences: list = []
    products: list = []
    top_dishes: list = []
    trending: list = []
    itineraries: list = []
    upcoming_events: list = []
    stats: dict | None = None
    area_counts: dict | None = None
    month: int | None = None
    seasonal_tagline: str | None = None


class EntityDetailResponse(ApiModel):
    # CHỈ khai scalar chắc-chắn-kiểu (id/type/name/summary/description luôn str|None).
    # KHÔNG khai field container biến-kiểu theo entity-type (source có thể str/list/
    # dict; images/relationships/attributes/quality...) → để extra="allow" mang qua
    # NGUYÊN KIỂU, tránh 500 ResponseValidation. ~30 field còn lại đi qua an toàn.
    id: str | None = None
    type: str | None = None
    name: str | None = None
    summary: str | None = None
    description: str | None = None
    relationship_total: int | None = None


class StatsResponse(ApiModel):
    entities: int | None = None
    places: int | None = None
    relationships: int | None = None
    itineraries: int | None = None
    feedback_entries: int | None = None
    query_log_entries: int | None = None
    backend: str | None = None
    db_size_kb: float | None = None
    db_path: str | None = None


class SiteSettingsResponse(ApiModel):
    """Map key→value động — extra='allow' mang toàn bộ setting qua."""


class TransparencyResponse(ApiModel):
    platform: str | None = None
    legal_entity: str | None = None
    contact_email: str | None = None
    content_policy: dict | None = None
    data_practices: dict | None = None
    nd147_compliance: dict | None = None


class MapPin(ApiModel):
    """1 pin bản đồ — /map-pins trả list[MapPin]; extra='allow' mang id/lat/lng/..."""
