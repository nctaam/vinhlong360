# -*- coding: utf-8 -*-
"""SHIM tương thích — miền định danh sang `agent/identity/` (2026-08-28).

Phản chiếu ĐỘNG toàn bộ namespace `identity.api` (kể cả tên gạch-dưới) — bài
học từ shim community/: ba lớp truy cập cũ (from-import 15+ tên đo được, truy
cập thuộc tính kiểu `auth._hash_password`, `auth.router` cùng-object) đều phải
sống mà liệt kê tĩnh KHÔNG đủ. monkeypatch vào shim không ăn tới handler — mọi
đích vá test đã chuyển thẳng sang `identity.api` cùng đợt.
"""
from identity import api as _api

globals().update(
    {k: v for k, v in vars(_api).items() if not k.startswith("__")}
)
del _api
