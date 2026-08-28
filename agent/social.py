# -*- coding: utf-8 -*-
"""SHIM tương thích — miền cộng đồng sang `agent/community/` (2026-08-28).

PHẢN CHIẾU ĐỘNG toàn bộ namespace của `community.api` (kể cả tên gạch-dưới):
ba lớp truy cập cũ phải sống nguyên — (1) `from social import X` với 29 tên đo
được, trong đó 21 gạch-dưới mà `import *` không xuất; (2) truy cập THUỘC TÍNH
`social._enrich_post` / `inspect.getsource(social._notify_mentions)` mà scan
import không nhìn thấy — đã đo được 11 bài vỡ khi shim chỉ liệt kê tĩnh;
(3) `social.router` ở server + 72 chỗ test (CÙNG object).

monkeypatch vào shim KHÔNG ăn tới handler (globals của community.api) — mọi
đích vá của test đã chuyển thẳng sang `community.api` cùng đợt (kịch bản A).
"""
from community import api as _api

globals().update(
    {k: v for k, v in vars(_api).items() if not k.startswith("__")}
)
del _api
