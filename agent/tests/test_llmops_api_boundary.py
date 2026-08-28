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


def test_router_phat_du_42_route_dung_mien():
    paths = sorted(r.path for r in llmops_api.router.routes)
    assert len(paths) == 42, len(paths)
    mien = {"/system", "/checkpoints", "/vectors", "/freshness", "/analytics"}
    for p in paths:
        assert any(p == m or p.startswith(m + "/") for m in mien), f"route lạc miền: {p}"


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
        r'@app\.(?:get|post|put|delete)\(\s*["\'](/(?:system|checkpoints|vectors|freshness|analytics)[^"\']*)',
        src)
    assert not con, f"server.py vẫn còn route llmops: {con}"
