"""Hợp đồng của `_error_response` — hàm dùng chung giữa server và chat.

Tách ra module riêng khi bóc `agent/chat/` (2026-08-27): đo được 14 nơi ngoài
chat gọi nó, nên để ở server.py là buộc chat import ngược server — vòng.
Vì cả hai bên cùng dùng, đổi hình dạng phản hồi ở đây là đổi cho CẢ HAI.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from http_errors import _error_response  # noqa: E402


def _body(resp) -> dict:
    return json.loads(bytes(resp.body).decode("utf-8"))


def test_tra_dung_ma_va_thong_diep():
    r = _error_response(404, "Không tìm thấy.")
    assert r.status_code == 404
    assert _body(r)["detail"] == "Không tìm thấy."


def test_khong_ro_ri_khi_khong_co_request():
    """Gọi không kèm request phải chạy được — 14 nơi gọi, không phải nơi nào
    cũng có object request trong tay."""
    r = _error_response(500, "Lỗi hệ thống.")
    assert r.status_code == 500
    assert "request_id" not in _body(r)


def test_extra_duoc_gop_vao_than():
    r = _error_response(429, "Quá nhiều yêu cầu.", retry_after=30)
    assert _body(r)["retry_after"] == 30
