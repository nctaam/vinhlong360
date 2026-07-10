# -*- coding: utf-8 -*-
"""Pydantic response models cho visits.py (UGC PG-only — "Đã đi / Muốn đi").

Chiến lược AN TOÀN (giống api_schemas.py, đã verify thực nghiệm FastAPI):
- Base `ApiModel` đặt `extra="allow"` → FastAPI GIỮ NGUYÊN field không khai
  → KHÔNG strip → FE luôn nhận đủ.
- CHỈ khai top-level field mà return-statement cho thấy kiểu RÕ RÀNG chắc chắn.
- Mảng dùng `list` (untyped) → không validate item → không 500 do item mismatch.
- Scalar dùng `| None` → validate nhẹ + document, gần như không 500.

Vì endpoint UGC trả 503 ở SQLite (không verify được prod) → CỰC KỲ BẢO THỦ:
field mơ hồ/nested/biến-kiểu → KHÔNG khai, để extra="allow" mang qua nguyên kiểu.
"""
from __future__ import annotations

from api_schemas import ApiModel


class VisitListResponse(ApiModel):
    """GET "" → {"visits": [{"entity_id","status"}, ...]}."""
    visits: list = []


class VisitCheckResponse(ApiModel):
    """GET /check/{entity_id} → {"status": "want"|"visited"|None}."""
    status: str | None = None


class ReviewPromptsResponse(ApiModel):
    """GET /review-prompts → {"prompts": [row, ...]}."""
    prompts: list = []


class VisitStatsResponse(ApiModel):
    """GET /stats → {"total","visited","want": COUNT ints, "by_type": dict}."""
    total: int | None = None
    visited: int | None = None
    want: int | None = None
    by_type: dict | None = None
