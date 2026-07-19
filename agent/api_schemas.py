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

from typing import Literal

from pydantic import BaseModel, ConfigDict, StrictInt, StrictStr, field_validator, model_validator

if __package__:
    from .ai_disclosure import (
        CANONICAL_ENTITY_AI,
        CANONICAL_PLACEHOLDER,
        CANONICAL_UGC_PHOTO,
    )
    from .image_descriptor import normalize_renderable_image_url
else:
    from ai_disclosure import (
        CANONICAL_ENTITY_AI,
        CANONICAL_PLACEHOLDER,
        CANONICAL_UGC_PHOTO,
    )
    from image_descriptor import normalize_renderable_image_url


class ApiModel(BaseModel):
    """Base: extra='allow' → không strip field trả về (an toàn FE)."""
    model_config = ConfigDict(extra="allow")


_GALLERY_COMBINATIONS = {
    ("ai-generated", "entity-editorial", "entity-ai"),
    ("placeholder", "generated-placeholder", "entity-placeholder"),
    ("user-uploaded", "review-ugc", "ugc-photo"),
    ("user-uploaded", "post-ugc", "ugc-photo"),
}
_GALLERY_DISCLOSURES = {
    "entity-ai": CANONICAL_ENTITY_AI,
    "entity-placeholder": CANONICAL_PLACEHOLDER,
    "ugc-photo": CANONICAL_UGC_PHOTO,
}


class GalleryImageDescriptor(BaseModel):
    """Strict, disclosure-backed image descriptor returned by the gallery API."""

    model_config = ConfigDict(extra="forbid")

    url: StrictStr | None
    alt: StrictStr
    source_class: Literal["ai-generated", "placeholder", "user-uploaded"]
    source_kind: Literal[
        "entity-editorial",
        "generated-placeholder",
        "review-ugc",
        "post-ugc",
    ]
    disclosure_key: Literal["entity-ai", "entity-placeholder", "ugc-photo"]
    short_label: StrictStr | None
    full_disclosure: StrictStr
    credit: StrictStr | None
    width: StrictInt | None
    height: StrictInt | None

    @field_validator("url", mode="before")
    @classmethod
    def _validate_url(cls, value: object) -> object:
        if value is None:
            return None
        normalized = normalize_renderable_image_url(value)
        if normalized is None:
            raise ValueError("image URL is not renderable")
        return normalized

    @field_validator("alt", "full_disclosure", mode="after")
    @classmethod
    def _require_non_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("image text must be non-blank")
        return value

    @field_validator("short_label", "credit", mode="after")
    @classmethod
    def _require_non_blank_optional_text(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("image optional text must be non-blank")
        return value

    @model_validator(mode="after")
    def _validate_invariants(self) -> "GalleryImageDescriptor":
        combination = (self.source_class, self.source_kind, self.disclosure_key)
        if combination not in _GALLERY_COMBINATIONS:
            raise ValueError("image source combination is not allowed")

        canonical = _GALLERY_DISCLOSURES[self.disclosure_key]
        if (
            self.short_label != canonical.short_label
            or self.full_disclosure != canonical.full_disclosure
        ):
            raise ValueError("image disclosure copy is not canonical")

        if self.source_class != "placeholder" and self.url is None:
            raise ValueError("non-placeholder image must have a URL")
        if self.source_class != "user-uploaded" and self.credit is not None:
            raise ValueError("AI and placeholder images cannot have credit")

        dimensions = (self.width, self.height)
        if (dimensions[0] is None) != (dimensions[1] is None):
            raise ValueError("image dimensions must be null together")
        if any(dimension is not None and dimension <= 0 for dimension in dimensions):
            raise ValueError("image dimensions must be positive integers")
        return self


class GalleryResponse(BaseModel):
    """Exact gallery envelope; no legacy top-level fields are permitted."""

    model_config = ConfigDict(extra="forbid")

    images: list[GalleryImageDescriptor]


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


class IndexPolicyDecisionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["entity", "ward", "itinerary"]
    indexable: bool
    reasons: list[str]
    policy_fingerprint: str
    policy_revision: str


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
    index_policy: IndexPolicyDecisionResponse


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
