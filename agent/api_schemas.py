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
