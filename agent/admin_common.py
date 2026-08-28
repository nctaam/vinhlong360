# -*- coding: utf-8 -*-
"""Hạ tầng ADMIN dùng chung — tách khỏi `admin.py` (2026-08-28, bước 2a).

Cùng khuôn `entity_read.py` ở bước 1a: đo trước cho thấy ba helper bị KẸT GIỮA —
cả miền entity-admin sắp bóc LẪN phần còn lại của `admin.py` đều gọi:

    _sync_kb          12 nơi gọi — đồng bộ KB sau khi ghi
    _log_mod_action   20 nơi gọi — nhật ký kiểm duyệt
    _mask              6 nơi gọi — che số điện thoại trong log

Kèm registry cache biến động (`_admin_volatile_caches` + `_invalidate_admin_caches`)
vì `_sync_kb` xoá cache qua nó; các `append(...)` đăng ký vẫn ở lại nơi cache sống.

Logger giữ NGUYÊN kênh "admin" — đổi tên kênh là đổi nơi log được định tuyến.
"""
from __future__ import annotations

import logging

import knowledge

logger = logging.getLogger("admin")

_admin_volatile_caches: list[dict] = []


def _invalidate_admin_caches():
    for c in _admin_volatile_caches:
        c["data"] = None


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
    try:
        # The chat's KB catalogue, which has no TTL of its own. Without this a
        # takedown removes the row while every later /chat still names the
        # entity — the one guarantee the catalogue exists to provide.
        import kb_context
        kb_context.invalidate()
    except Exception:
        logger.warning("KB context invalidation failed after KB sync")
    _invalidate_admin_caches()


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
