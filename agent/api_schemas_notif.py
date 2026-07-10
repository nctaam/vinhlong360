# -*- coding: utf-8 -*-
"""Pydantic response models cho notifications.py (SP3 W6.3 — UGC PG-only).

Chiến lược AN TOÀN (giống api_schemas.py, đã verify thực nghiệm FastAPI):
- Base `ApiModel` đặt `extra="allow"` → FastAPI GIỮ NGUYÊN mọi field trả về
  (kể cả field không khai) → KHÔNG bao giờ strip → FE luôn nhận đủ.
- CỰC KỲ BẢO THỦ: endpoint UGC trả 503 local (không PG) → KHÔNG verify được
  prod. Chỉ khai top-level field mà RETURN STATEMENT cho thấy kiểu RÕ RÀNG:
    * list literal `[...]`               → `list = []`
    * `len(x)` / COUNT(*) / `int(...)`   → `int | None = None`
    * `row is not None` / `bool(...)`    → `bool | None = None`
  Field mơ hồ / nested / biến-kiểu → KHÔNG khai (extra="allow" mang qua nguyên).
"""
from __future__ import annotations

from api_schemas import ApiModel


# ── GET /api/notifications ──
# return {"notifications": grouped (list), "unread_count": int}
class NotificationsResponse(ApiModel):
    notifications: list = []
    unread_count: int | None = None


# ── GET /api/notifications/unread-count ──
# return {"unread_count": count (int từ COUNT)}
class UnreadCountResponse(ApiModel):
    unread_count: int | None = None


# ── GET /api/notification-preferences ──
# return {"pref_like": bool, "pref_comment": bool, ...} (5 cờ bool)
class NotificationPreferencesResponse(ApiModel):
    pref_like: bool | None = None
    pref_comment: bool | None = None
    pref_mention: bool | None = None
    pref_follow: bool | None = None
    pref_system: bool | None = None


# ── GET /api/follow/check/{target_type}/{target_id} ──
# return {"following": row is not None (bool)}
class FollowCheckResponse(ApiModel):
    following: bool | None = None


# ── GET /api/following ──
# return {"following": items (list), "total": int, "has_more": bool}
class FollowingResponse(ApiModel):
    following: list = []
    total: int | None = None
    has_more: bool | None = None


# ── GET /api/followers/count/{target_type}/{target_id} ──
# return {"count": int (từ COUNT)}
class FollowerCountResponse(ApiModel):
    count: int | None = None


# ── GET /api/blocked-users ──
# return {"blocked": result (list), "total": int, "page": int, "has_more": bool}
class BlockedUsersResponse(ApiModel):
    blocked: list = []
    total: int | None = None
    page: int | None = None
    has_more: bool | None = None


# ── GET /api/muted-users ──
# return {"muted": result (list), "total": int, "page": int, "has_more": bool}
class MutedUsersResponse(ApiModel):
    muted: list = []
    total: int | None = None
    page: int | None = None
    has_more: bool | None = None


# ── GET /api/events/{entity_id}/rsvp ──
# return {"count": int (từ COUNT), "going": bool}
class RsvpStatusResponse(ApiModel):
    count: int | None = None
    going: bool | None = None
