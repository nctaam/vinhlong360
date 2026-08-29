# -*- coding: utf-8 -*-
"""Hạ tầng ADMIN dùng chung — tách khỏi `admin.py` (2026-08-28, bước 2a).

Cùng khuôn `entity_read.py` ở bước 1a: đo trước cho thấy ba helper bị KẸT GIỮA —
cả miền entity-admin sắp bóc LẪN phần còn lại của `admin.py` đều gọi:

    _sync_kb          12 nơi gọi — đồng bộ KB sau khi ghi
    _log_mod_action   20 nơi gọi — nhật ký kiểm duyệt
    _mask              6 nơi gọi — che số điện thoại trong log

Kèm registry cache biến động (`_admin_volatile_caches` + `_invalidate_admin_caches`)
vì `_sync_kb` xoá cache qua nó; các `append(...)` đăng ký vẫn ở lại nơi cache sống.

Bổ sung 2026-08-29 (bước dọn nền lát community-admin): năm ký hiệu nữa cũng KẸT
GIỮA — cả miền community-admin sắp bóc lẫn phần ở lại của `admin.py` đều dùng:

    _csv_cell/_csv_row/_CSV_FORMULA_PREFIXES   export CSV (cả contact_funnel_export ở lại)
    _require_admin_actor_id                    lấy id admin cho hành động cần quy trách nhiệm
    _ensure_admin_scope                        chốt RBAC scope (require_admin ở lại cũng gọi)

Bổ sung 2026-08-29 (bước dọn nền lát 3 — siteops): thêm một ký hiệu KẸT GIỮA:

    _safe    bọc try/except trả default — analytics_overview Ở LẠI admin.py lẫn
             ops_summary/_data_quality_ops_snapshot sang siteops/ đều gọi

Logger giữ NGUYÊN kênh "admin" — đổi tên kênh là đổi nơi log được định tuyến.
"""
from __future__ import annotations

import csv
import io
import logging
from typing import Any

from fastapi import HTTPException, Request

import knowledge

logger = logging.getLogger("admin")


def _safe(fn, default):
    try:
        return fn()
    except Exception:
        logger.debug("_safe(%s) failed, returning default", getattr(fn, "__name__", fn), exc_info=True)
        return default


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


_CSV_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _csv_cell(value: Any) -> str:
    cell = "" if value is None else str(value)
    if cell.startswith(_CSV_FORMULA_PREFIXES):
        return "'" + cell
    return cell


def _csv_row(values) -> str:
    output = io.StringIO()
    csv.writer(output, lineterminator="\n").writerow([_csv_cell(value) for value in values])
    return output.getvalue()


def _ensure_admin_scope(request: Request | None, scope: str) -> None:
    scopes = set(getattr(getattr(request, "state", None), "admin_scopes", []) or [])
    if "*" in scopes or scope in scopes:
        return
    raise HTTPException(403, f"Thieu quyen admin: {scope}")


def _require_admin_actor_id(request: Request | None) -> str:
    """Return the authenticated admin user id for actions that need user attribution."""
    if request is None:
        raise HTTPException(403, "Thao tác này cần phiên admin")
    user = getattr(request.state, "admin_user", None) or getattr(request.state, "user", None)
    if not user or not user.get("id"):
        raise HTTPException(403, "Thao tác này cần phiên admin")
    return str(user["id"])
