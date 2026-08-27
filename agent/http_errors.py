# -*- coding: utf-8 -*-
"""Định dạng phản hồi lỗi HTTP — dùng chung.

Tách khỏi `server.py` (2026-08-27) khi bóc `agent/chat/`. Đây là một trong ba ký
hiệu THẬT SỰ dùng chung giữa chat và phần còn lại: đo được 14 nơi ngoài chat gọi
nó (`_global_exception_handler`, `build_vectors`, `reload_data`, `metrics_endpoint`…).
Để nó ở server.py là buộc chat import ngược server — vòng.
"""
from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

def _error_response(status_code: int, detail: str, request: Request = None, **extra) -> JSONResponse:
    body = {"detail": detail}
    if request:
        rid = getattr(getattr(request, "state", None), "request_id", None)
        if rid:
            body["request_id"] = rid
    body.update(extra)
    return JSONResponse(status_code=status_code, content=body)
