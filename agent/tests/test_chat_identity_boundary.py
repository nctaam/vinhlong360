"""Khoá rewiring của `chat_identity` sau cú gỡ shim auth.py (2026-08-29).

`chat_identity._get_current_user_or_none` uỷ quyền LÚC GỌI cho miền định danh;
sau gỡ shim, đường resolve duy nhất là `identity.api`. Hai test này khoá đúng
hai thứ có thể trôi: nguồn hết tham chiếu đường phẳng cũ, và lời uỷ quyền
thật sự rơi vào hàm của identity.api (vá được bằng monkeypatch tại nhà thật).
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import chat_identity  # noqa: E402
from identity import api as identity_api  # noqa: E402


def test_nguon_het_duong_phang_cu():
    src = Path(chat_identity.__file__).read_text(encoding="utf-8")
    assert "from identity.api import" in src
    assert "from auth import" not in src


def test_uy_quyen_roi_vao_identity_api(monkeypatch):
    goi = {}

    async def stub(request):
        goi["request"] = request
        return {"id": "u-stub"}

    monkeypatch.setattr(identity_api, "_get_current_user_or_none", stub)
    req = SimpleNamespace(headers={}, cookies={})
    ket_qua = asyncio.run(chat_identity._get_current_user_or_none(req))
    assert ket_qua == {"id": "u-stub"}
    assert goi["request"] is req
