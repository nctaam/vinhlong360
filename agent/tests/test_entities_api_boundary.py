"""Ranh giới của gói `agent/entities/` — lát thứ ba (2026-08-28).

Cùng khuôn `test_chat_api_boundary.py` / `test_llmops_api_boundary.py`, cộng một
điểm RIÊNG của lát này: gói được mount QUA `public_api.router` bằng
`include_router` thật (không phải include trực tiếp ở server) — vì 34 chỗ trong
bộ test soi `public_api.router` như "mặt công khai", và cổng R20.9 chỉ nhìn thấy
mount qua lời gọi `include_router`.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from entities import api as entities_api  # noqa: E402

SRC = Path(entities_api.__file__).resolve()


def test_router_khong_tu_mang_prefix():
    """Mount qua public_api.router (prefix /api). Tự mang /api nữa là
    /api/api/entities — đã đo được đúng lỗi đó trong lúc dựng."""
    assert entities_api.router.prefix == ""
    assert all(not r.path.startswith("/api/") for r in entities_api.router.routes)


def test_moi_route_deu_len_app_duoi_prefix_api():
    import server

    app_paths = {r.path for r in server.app.routes}
    thieu = ["/api" + r.path for r in entities_api.router.routes
             if "/api" + r.path not in app_paths]
    assert not thieu, f"route entity không lên app: {thieu[:5]}"


def test_KHONG_import_nguoc_public_api_server_chat_llmops():
    tree = ast.parse(SRC.read_text(encoding="utf-8"))
    XAU = ("server", "public_api", "chat", "llmops")
    bad = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            bad += [a.name for a in n.names if a.name.split(".")[0] in XAU]
        elif isinstance(n, ast.ImportFrom) and n.module:
            if n.module.split(".")[0] in XAU:
                bad.append(n.module)
    assert not bad, f"entities/api.py import xấu: {bad}"


def test_khong_con_dinh_nghia_o_public_api():
    """Dời mà để lại bản sao là hai nguồn sự thật trôi khác nhau."""
    import public_api

    src = Path(public_api.__file__).resolve().read_text(encoding="utf-8")
    tree = ast.parse(src)
    ten = {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    for f in ("get_entity", "entities_map_search", "popular_entities", "entities_trending"):
        assert f not in ten, f"public_api.py vẫn còn định nghĩa {f}"
