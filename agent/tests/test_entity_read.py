"""Hợp đồng của tầng ĐỌC ENTITY dùng chung (`agent/entity_read.py`).

Tách khỏi `public_api.py` 2026-08-28 (bước 1a của lát `entities/`): 10 helper
đọc-entity bị KẸT GIỮA — cả gói `entities/` sắp bóc lẫn phần còn lại của
`public_api` đều gọi. Vì CẢ HAI bên dùng, đổi hành vi ở đây là đổi cho cả hai.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import entity_read  # noqa: E402


def test_logger_la_loai_CHUAN_khong_phai_StructuredLogger():
    """Bản đầu tôi import `middleware.logger` — một `StructuredLogger` chỉ nhận
    MỘT đối số — trong khi mã ở đây gọi kiểu `warning(fmt, a, b, c)`. Đúng tên,
    SAI LỚP, chỉ nổ lúc chạy. Khoá lại để không ai lặp."""
    assert isinstance(entity_read.logger, logging.Logger)
    # gọi đúng kiểu mã trong module đang dùng — không được ném
    entity_read.logger.warning("thu %s %d %s", "a", 1, "b")


def test_canh_bao_cham_tran_quet_kho():
    """`>=` chứ không `>`: trả về ĐÚNG `limit` hàng thì không phân biệt được
    'vừa đủ' với 'đã bị cắt', nên ở ranh giới phải coi như đã cắt."""
    assert entity_read._warn_if_scan_truncated([1] * 4999, 5000, "x") is False
    assert entity_read._warn_if_scan_truncated([1] * 5000, 5000, "x") is True
    assert entity_read._warn_if_scan_truncated([1] * 5001, 5000, "x") is True


def test_tran_la_hang_co_ten():
    assert entity_read._FULL_SCAN_LIMIT == 5000
    assert entity_read._EVENT_SCAN_LIMIT == 2000


def test_err_dung_khoa_detail_khong_phai_error():
    """Hình dạng `{detail: ...}` là CÓ CHỦ ĐÍCH (SP3 W6.2): đồng nhất với
    `server._error_response` và handler HTTPException. Bản cũ của public_api trả
    `{error: code}` và đi vòng qua handler. Khoá lại để không ai lùi về hình
    dạng cũ — nay hàm này phục vụ CẢ hai bên nên lùi là lùi cho cả hai."""
    import json

    r = entity_read._err(404, "khong_thay", muc="entity")
    assert r.status_code == 404
    than = json.loads(bytes(r.body).decode("utf-8"))
    assert than["detail"] == "khong_thay"
    assert "error" not in than, "lùi về hình dạng {error:...} cũ"
    assert than["muc"] == "entity", "**extra phải được gộp vào thân"


def test_is_public_chi_nhan_entity_da_publish():
    assert entity_read._is_public({"id": "a", "verified": True}) is True
    assert entity_read._is_public({"id": "b", "verified": False}) is False


def test_cache_place_co_khoa_va_co_tran():
    """Cache dùng chung giữa hai tiến trình đọc — mất khoá là mất tính đúng."""
    assert entity_read._PLACE_CACHE_MAX > 0
    assert hasattr(entity_read._place_cache_lock, "acquire")
