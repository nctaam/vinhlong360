"""Ranh giới của gói `agent/chat/` sau khi bóc khỏi server.py (2026-08-27).

Bóc chat ra chỉ có nghĩa nếu ranh giới GIỮ ĐƯỢC. Bộ này khoá bốn tính chất mà
nếu mất thì cú bóc thành vô nghĩa — hoặc tệ hơn, thành một vòng import chờ nổ.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chat import api as chat_api  # noqa: E402

CHAT_SRC = Path(chat_api.__file__).resolve()


def test_router_phat_dung_hai_route_chat():
    paths = {r.path for r in chat_api.router.routes}
    assert paths == {"/chat", "/chat/stream"}, paths


def test_KHONG_import_nguoc_server():
    """Điều kiện sống còn: `server` import `chat.api`, nên chiều ngược là VÒNG.

    Cả import mức module lẫn import lười trong thân hàm đều tính — import lười
    không nổ lúc khởi động nên nó nguy hiểm hơn, chỉ sập khi chạy đúng nhánh đó.
    """
    tree = ast.parse(CHAT_SRC.read_text(encoding="utf-8"))
    xau = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            xau += [a.name for a in n.names if a.name.split(".")[0] == "server"]
        elif isinstance(n, ast.ImportFrom) and n.module:
            if n.module.split(".")[0] == "server":
                xau.append(n.module)
    assert not xau, f"chat/api.py import ngược server: {xau}"


def test_giu_bo_loc_rieng_tu_va_cong_owner():
    """Hai thứ KHÔNG được rơi rụng trong lúc dời: mốc biên giới riêng tư và
    cổng ghi theo chủ sở hữu. Mất chúng thì cú dời đã đổi hành vi."""
    src = CHAT_SRC.read_text(encoding="utf-8")
    assert src.count("_privacy_input_boundary_marker = True") >= 2, "thiếu mốc biên giới riêng tư"
    assert "owner_write_gate.assert_writable(" in src, "thiếu cổng ghi theo chủ sở hữu"


def test_khong_con_ma_chat_o_server():
    """Dời mà để lại bản sao là tệ hơn không dời: hai bản trôi khác nhau."""
    import server

    server_src = Path(server.__file__).resolve().read_text(encoding="utf-8")
    tree = ast.parse(server_src)
    ten = {
        n.name for n in tree.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert "chat_stream" not in ten, "server.py vẫn còn định nghĩa chat_stream"
    assert "_event_stream_body" not in ten
