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


def test_rollout_enabled_ton_trong_ban_va_o_public_api(monkeypatch):
    """`_rollout_enabled` TRA CỨU MUỘN — ưu tiên `public_api.settings`.

    Bản đầu đọc thẳng `entity_read.settings` sau khi dời — làm 70 bài đỏ: 10 chỗ
    trong bộ test vá `public_api.settings`, mà hàm này gác MỌI route có cờ
    (không riêng miền entity), nên user_preferences / trust_policy /
    location_resolver đổ theo. Và KHÔNG lượt đo nhắm nào thấy được — nó phá
    những route NGOÀI miền đang bóc. Khoá lại ưu tiên đó.
    """
    import sys
    from types import SimpleNamespace

    import public_api  # noqa: F401 — bảo đảm module đã nạp trong sys.modules

    monkeypatch.setattr(sys.modules["public_api"], "settings",
                        SimpleNamespace(CO_THU_NGHIEM=True), raising=False)
    assert entity_read._rollout_enabled("CO_THU_NGHIEM") is True
    assert entity_read._rollout_enabled("CO_KHONG_TON_TAI") is False


def test_require_rollout_nem_404_khi_co_tat(monkeypatch):
    import sys
    from types import SimpleNamespace

    import pytest
    from fastapi import HTTPException

    import public_api  # noqa: F401

    monkeypatch.setattr(sys.modules["public_api"], "settings",
                        SimpleNamespace(), raising=False)
    with pytest.raises(HTTPException) as exc:
        entity_read._require_rollout("CO_TAT")
    assert exc.value.status_code == 404


def test_invalidate_place_cache_xoa_cache_va_phat_tin_hieu():
    """Cú dời invalidator (2026-08-28): hàm chạm HAI tầng — place-cache (sống ở
    đây) và homepage-cache (của public_api). Tách bằng LISTENER: đây xoá phần
    của mình rồi phát tín hiệu; public_api đăng ký việc-của-nó lúc import. Khoá
    cả hai vế để cú dời không âm thầm nuốt mất vế homepage."""
    entity_read._place_cache["x"] = {"name": "X", "area": None}
    goi = []
    entity_read._place_invalidation_listeners.append(lambda: goi.append(1))
    try:
        entity_read.invalidate_place_cache()
        assert "x" not in entity_read._place_cache, "place-cache chưa bị xoá"
        assert goi == [1], "listener không được phát tín hiệu"
    finally:
        entity_read._place_invalidation_listeners.pop()


def test_public_api_dang_ky_listener_homepage():
    """Vế homepage: import public_api phải đăng ký ĐÚNG MỘT listener — mất đăng
    ký là admin sửa place xong homepage vẫn phục vụ tên cũ (Perf-P0 cũ)."""
    import public_api  # noqa: F401 — kích hoạt đăng ký lúc import

    assert len(entity_read._place_invalidation_listeners) >= 1


def test_invalidate_entity_cache_la_hook_tuong_thich():
    entity_read.invalidate_entity_cache("bat-ky")  # không được ném
    entity_read.invalidate_entity_cache(None)
