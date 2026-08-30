# -*- coding: utf-8 -*-
"""Khoá admin mà TEST GỬI phải là khoá mà SERVER KIỂM — trong mọi tổ hợp chạy.

VÌ SAO CÓ FILE NÀY. Kho có hai thư mục test, mỗi thư mục một `conftest.py`, và cả
hai cùng đặt `ADMIN_API_KEY` bằng `os.environ.setdefault` — với HAI GIÁ TRỊ KHÁC
NHAU (`tests/conftest.py` → "test-admin-key", `agent/tests/conftest.py` →
"test-admin-key-12345"). `setdefault` nghĩa là AI LOAD TRƯỚC THÌ THẮNG:

  chạy `pytest tests/`                  → bản ngắn thắng  → header ghim cứng khớp
  chạy `pytest agent/tests/ tests/`     → bản dài thắng   → header ghim cứng SAI

Hậu quả đo được 2026-08-30: **11 test integration đỏ**, toàn 404 trên `/metrics`,
`/vectors/stats`, `/system/*`, `/analytics/*`, `/ab-testing/*` — vì
`gate_internal_endpoints` (`agent/server.py:751`) trả 404 khi `verify_admin_key`
thất bại. Đọc log thì tưởng endpoint bị gỡ; thật ra chỉ là sai khoá.

VÀ ĐÓ LÀ MÌN CI: `.github/workflows/ci.yml:124` chạy đúng tổ hợp gây vỡ —
`pytest tests/ agent/tests/ -m "not slow"`, chú thích ngay trên nó ghi rõ "bao gồm
integration". Chạy riêng từng thư mục thì KHÔNG BAO GIỜ thấy.

File này KHÔNG mang marker nào, nên nó chạy ở mọi lượt đo — kể cả lượt mặc định
vốn loại `integration`. Đó là điểm chính: bất biến này phải được canh ở nơi người
ta thật sự nhìn.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agent"))


def test_khoa_server_kiem_dung_bang_khoa_moi_truong():
    """Khoá `middleware` chốt lúc import phải khớp env — nếu lệch, mọi route bị
    canh trả 404 và không test nào nói cho bạn biết vì sao."""
    import middleware

    assert middleware.ADMIN_API_KEY, "ADMIN_API_KEY rỗng → verify_admin_key fail-closed, mọi route bị canh trả 404"
    assert middleware.ADMIN_API_KEY == os.environ.get("ADMIN_API_KEY"), (
        "khoá mà server kiểm KHÁC khoá trong môi trường — hai conftest đang tranh "
        "nhau bằng setdefault, hoặc có test đổi env sau khi middleware đã import"
    )


def test_khong_fixture_nao_ghim_cung_khoa_admin():
    """`admin_headers` phải ĐỌC TỪ ENV, không ghim chuỗi.

    Ghim cứng thì fixture chỉ đúng khi thư mục của nó thắng cuộc đua `setdefault`
    — tức đúng lúc chạy riêng, sai lúc chạy chung, và CI chạy chung.
    """
    goc = Path(__file__).resolve().parents[1]
    pham_vi = [goc / "tests" / "conftest.py",
               goc / "tests" / "test_integration.py",
               goc / "agent" / "tests" / "conftest.py"]

    vi_pham = []
    for duong in pham_vi:
        if not duong.exists():
            continue
        for so, dong in enumerate(duong.read_text(encoding="utf-8").splitlines(), 1):
            if "X-Admin-Key" not in dong:
                continue
            # Ghim cứng = có dấu nháy ngay sau dấu hai chấm của khoá header.
            sau = dong.split("X-Admin-Key", 1)[1]
            if "os.environ" in sau or "environ[" in sau:
                continue
            if '"' in sau.split(":", 1)[-1] or "'" in sau.split(":", 1)[-1]:
                vi_pham.append(f"{duong.relative_to(goc).as_posix()}:{so}")

    assert not vi_pham, (
        "fixture gửi khoá admin GHIM CỨNG — sẽ sai khi chạy chung hai thư mục test "
        "(đúng tổ hợp CI dùng):\n  " + "\n  ".join(vi_pham)
    )
