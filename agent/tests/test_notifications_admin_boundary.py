"""Ranh giới mặt QUẢN TRỊ của notifications — lát 5 hoàn-thiện-sâu (2026-08-29).

Một route dời (POST /admin/notifications/cleanup) nhưng khoá đủ khuôn: lên app
dưới /admin với chốt kế thừa THẬT (đo dependant runtime), router con sạch
prefix/deps-thừa, nhà cũ hết định nghĩa.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import admin  # noqa: E402
import notifications  # noqa: E402
import server  # noqa: E402


def test_route_len_app_va_ke_thua_chot_admin():
    route = next(r for r in server.app.routes
                 if getattr(r, "path", "") == "/admin/notifications/cleanup")
    ten_deps = {d.call.__name__ for d in route.dependant.dependencies if d.call}
    assert {"require_admin", "require_csrf", "require_pg"} <= ten_deps, ten_deps


def test_router_con_khong_prefix_khong_thua_chot():
    assert notifications.admin_router.prefix == ""
    ten = {d.dependency.__name__ for d in notifications.admin_router.dependencies}
    assert ten == {"require_pg"}, ten


def test_nha_cu_het_dinh_nghia():
    tree = ast.parse(Path(admin.__file__).read_text(encoding="utf-8"))
    ten = [n.name for n in ast.walk(tree)
           if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
           and n.name == "admin_cleanup_notifications"]
    assert ten == [], "admin.py vẫn còn định nghĩa handler đã dời"
