"""
Rate-limit sliding-window trong-bộ-nhớ (per-process). Đủ cho 1 instance, <10k user.
Nếu scale nhiều instance → thay bằng Redis. Dùng cho chống-spam UGC (tạo bài/bình
luận/upload ảnh). Login/OTP đã có limit riêng trong auth.py.

    from ratelimit import check_rate
    check_rate(f"post:{user_id}", limit=10, window=600)   # raise HTTPException(429) nếu vượt
"""
import logging
import time

from fastapi import HTTPException

logger = logging.getLogger(__name__)

# key -> list[timestamp] (chỉ giữ trong cửa sổ hiện tại)
_buckets: dict[str, list[float]] = {}
_MAX_KEYS = 50_000  # chặn phình bộ nhớ vô hạn (đủ lớn cho <10k user × vài loại key)


def _now() -> float:
    return time.time()


def check_rate(key: str, limit: int, window: int,
               msg: str = "Bạn thao tác quá nhanh. Vui lòng thử lại sau.") -> None:
    """Ghi nhận 1 lượt cho `key`; raise HTTPException(429) nếu đã đạt `limit` trong `window` giây."""
    now = _now()
    hits = [t for t in _buckets.get(key, []) if now - t < window]
    if len(hits) >= limit:
        # cập nhật lại bucket đã lọc (không thêm lượt) rồi từ chối
        _buckets[key] = hits
        raise HTTPException(429, msg)
    hits.append(now)
    _buckets[key] = hits
    if len(_buckets) > _MAX_KEYS:
        logger.warning("Rate-limit buckets at capacity (%d); running GC", len(_buckets))
        _gc(now)


def _gc(now: float | None = None) -> None:
    """Dọn các bucket rỗng/hết hạn (gọi cơ hội khi dict phình to)."""
    now = now if now is not None else _now()
    # window lớn nhất đang dùng ~600s; bucket không có timestamp nào < 3600s coi như chết
    dead = [k for k, ts in _buckets.items() if not ts or now - ts[-1] > 3600]
    for k in dead:
        _buckets.pop(k, None)


def _reset() -> None:
    """Chỉ dùng trong test."""
    _buckets.clear()
