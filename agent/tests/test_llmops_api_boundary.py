"""Ranh giới của gói `agent/llmops/` — lát cắt thứ hai, sau `chat/` (2026-08-27).

Cùng khuôn với `test_chat_api_boundary.py`: khoá những tính chất mà mất thì cú
bóc thành vô nghĩa.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from llmops import api as llmops_api  # noqa: E402

SRC = Path(llmops_api.__file__).resolve()


def test_router_phat_du_43_route_dung_mien():
    # 42 route gốc + /search/enhanced về từ server.py (lát 4 đợt
    # hoàn-thiện-sâu 2026-08-29 — cùng loài chẩn đoán truy hồi /vectors/search).
    paths = sorted(r.path for r in llmops_api.router.routes)
    assert len(paths) == 43, len(paths)
    mien = {"/system", "/checkpoints", "/vectors", "/freshness", "/analytics",
            "/search/enhanced"}
    for p in paths:
        assert any(p == m or p.startswith(m + "/") for m in mien), f"route lạc miền: {p}"


def test_search_enhanced_len_app_tu_llmops():
    """/search/enhanced phải LÊN app và do llmops.api phục vụ — path y nguyên,
    handler đổi nhà; nếu server.py mọc lại bản sao thì test uniqueness đỏ trước."""
    import server

    matches = [r for r in server.app.routes if getattr(r, "path", None) == "/search/enhanced"]
    assert len(matches) == 1, f"kỳ vọng đúng 1 route /search/enhanced, có {len(matches)}"
    assert matches[0].endpoint.__module__ == "llmops.api", matches[0].endpoint.__module__


def test_KHONG_import_nguoc_server_va_chat():
    """`server` import `llmops.api`, nên chiều ngược là VÒNG. Và llmops không
    có việc gì với chat — import chéo giữa hai gói miền là rò rỉ ranh giới."""
    tree = ast.parse(SRC.read_text(encoding="utf-8"))
    xau = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            xau += [a.name for a in n.names if a.name.split(".")[0] in ("server", "chat")]
        elif isinstance(n, ast.ImportFrom) and n.module:
            if n.module.split(".")[0] in ("server", "chat"):
                xau.append(n.module)
    assert not xau, f"llmops/api.py import xấu: {xau}"


def test_khong_con_route_llmops_o_server():
    """Dời mà để lại bản sao là hai nguồn sự thật trôi khác nhau."""
    import re

    import server

    src = Path(server.__file__).resolve().read_text(encoding="utf-8")
    con = re.findall(
        r'@app\.(?:get|post|put|delete)\(\s*["\'](/(?:system|checkpoints|vectors|freshness|analytics|search/enhanced)[^"\']*)',
        src)
    assert not con, f"server.py vẫn còn route llmops: {con}"
