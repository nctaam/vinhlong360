# -*- coding: utf-8 -*-
"""Miền VẬN HÀNH SITE (siteops) — mặt CÔNG KHAI. Bóc khỏi `public_api.py`
(2026-08-29, lát 3 đợt hoàn-thiện-sâu; hồ sơ đo: journal wf_3f293d24-0a1,
kết quả siteops).

Hoàn tất khuôn hai-mặt cho gói `agent/siteops/` (như `entities/`,
`community/`, `itineraries/`): mặt quản trị ở `siteops/admin_api.py` (22 route),
đây là 2 route đọc công khai (site-settings + announcements active) —
di chuyển NGUYÊN VĂN.

LƯU Ý hợp đồng UGC_MODULES (tests/test_api_surface_contract.py): KHÔNG thêm
"siteops.api" vào frozenset đó — get_site_settings PHỤC VỤ SQLite dev (trả
dict, không 503), còn list_active_announcements gọi require_pg trong THÂN hàm
chứ không qua Depends — thêm vào là tự làm đỏ hợp đồng.

Mount qua `public_api.router.include_router(...)` TRƯỚC `_fix_route_order()`:
- cổng R20.9 chỉ nhìn thấy mount qua lời gọi include_router;
- router cha mang prefix "/api" — router này KHÔNG tự mang (tự mang nữa là
  /api/api/site-settings, bài đo của entities/api.py).
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Query, Response

import site_settings
from api_schemas import SiteSettingsResponse
from auth_middleware import require_pg
from database import db

router = APIRouter(tags=["siteops"])


@router.get("/site-settings", response_model=SiteSettingsResponse,
            summary="Get site settings",
            description="Returns all public site settings as a flat key-value dict. Cached for 60 seconds.")
async def get_site_settings(response: Response):
    """Public flat {key: value} dict of all site settings (cached 60s)."""
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=120"
    return site_settings.get_all_public()


# ── Public Announcements ─────────────────────────────────────────────────

@router.get("/announcements",
            summary="List active announcements",
            description="Returns currently active announcements sorted by priority. Only shows announcements within their active date range. Requires Postgres.")
async def list_active_announcements(response: Response, limit: int = Query(10, ge=1, le=50)):
    """Active announcements for display to users."""
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=120"
    require_pg()
    ph = db._ph

    def _query():
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT id, title, content, type, priority, starts_at, expires_at, created_at
                FROM announcements
                WHERE is_active = TRUE
                  AND starts_at <= NOW()
                  AND (expires_at IS NULL OR expires_at > NOW())
                ORDER BY priority DESC, created_at DESC
                LIMIT {ph}
            """, (limit,))
        return [db._row_to_dict(r) for r in rows]

    items = await asyncio.to_thread(_query)
    return {"announcements": items, "total": len(items)}
