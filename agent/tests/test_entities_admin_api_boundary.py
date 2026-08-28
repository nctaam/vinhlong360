"""Ranh giới mặt QUẢN TRỊ của gói `agent/entities/` (bước 2b, 2026-08-28).

Gói miền entity nay ĐỦ HAI MẶT theo khuôn `agent/cases/`: `api.py` (công khai,
bước 1b) + `admin_api.py` (quản trị, bước này).
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from entities import admin_api  # noqa: E402

SRC = Path(admin_api.__file__).resolve()


def test_router_khong_tu_mang_prefix_va_khong_tu_mang_auth():
    """Mount qua `admin.router.include_router(...)` — cha mang prefix "/admin"
    VÀ dependencies [require_admin, require_csrf]. Con tự mang nữa là
    /admin/admin hoặc auth chạy hai lần."""
    assert admin_api.router.prefix == ""
    assert admin_api.router.dependencies == []


def test_moi_route_len_app_duoi_admin_va_co_chot_auth():
    """AN NINH — kiểm bằng ĐO, không tin trí nhớ API: route con phải kế thừa
    require_admin + require_csrf từ router cha khi include."""
    import server

    app_routes = {r.path: r for r in server.app.routes if hasattr(r, "dependant")}
    thieu_route, thieu_auth = [], []
    for r in admin_api.router.routes:
        path = "/admin" + r.path
        if path not in app_routes:
            thieu_route.append(path)
            continue
        deps = {getattr(d.call, "__name__", "?")
                for d in app_routes[path].dependant.dependencies}
        if not {"require_admin", "require_csrf"} <= deps:
            thieu_auth.append((path, sorted(deps)))
    assert not thieu_route, f"route không lên app: {thieu_route[:5]}"
    assert not thieu_auth, f"route THIẾU chốt auth kế thừa: {thieu_auth[:5]}"


def test_KHONG_import_nguoc():
    tree = ast.parse(SRC.read_text(encoding="utf-8"))
    XAU = ("server", "admin", "public_api", "chat", "llmops")
    bad = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            bad += [a.name for a in n.names if a.name.split(".")[0] in XAU]
        elif isinstance(n, ast.ImportFrom) and n.module:
            if n.module.split(".")[0] in XAU:
                bad.append(n.module)
    assert not bad, f"admin_api.py import xấu: {bad}"


def test_khong_con_dinh_nghia_o_admin():
    import admin

    src = Path(admin.__file__).resolve().read_text(encoding="utf-8")
    tree = ast.parse(src)
    ten = {n.name for n in tree.body
           if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    for f in ("create_entity", "update_entity", "delete_entity", "admin_media"):
        assert f not in ten, f"admin.py vẫn còn định nghĩa {f}"
