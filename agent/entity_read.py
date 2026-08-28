# -*- coding: utf-8 -*-
"""Tầng ĐỌC ENTITY dùng chung — tách khỏi `public_api.py` (2026-08-28).

Bước 1a của lát `entities/`. Đo trước cho thấy 10 helper đọc-entity bị KẸT: cả
gói `entities/` sắp bóc LẪN phần còn lại của `public_api` đều gọi chúng, nên để
nguyên chỗ cũ là buộc `entities/` import ngược `public_api` — vòng.

Đây KHÔNG phải phình việc: chúng vốn là một tầng có thật (đọc entity công khai +
lọc + chiếu media + cache place), chỉ chưa được đặt tên. Cùng loại với
`agent/features.py` và `agent/http_errors.py` ở hai lát trước — hạ tầng dùng
chung thì tách ra, KHÔNG chia theo miền (bản đồ module §5).

Kèm ba thứ hạ tầng quét-toàn-kho (`_FULL_SCAN_LIMIT`, `_EVENT_SCAN_LIMIT`,
`_warn_if_scan_truncated`) vì các hàm ở đây và bên `entities/` đều dùng — xem
ROADMAP về "năm truy vấn quét-toàn-kho cắt lặng lẽ".
"""
from __future__ import annotations

import threading as _threading
from collections import OrderedDict
from dataclasses import asdict
from typing import Optional

from fastapi import HTTPException
from fastapi.responses import JSONResponse

from data_quality import entity_quality
from config import settings
from database import db
import logging

# Logger CHUAN, khong phai `middleware.logger`. `StructuredLogger.warning()`
# chi nhan MOT doi so; ma o day goi kieu `warning(fmt, a, b)` nen import nham
# loai la TypeError luc chay. Test _warn_if_scan_truncated bat duoc ngay.
logger = logging.getLogger(__name__)


# Doi tu public_api cung dot boc entities/ (2026-08-28): ca public_api LAN
# entities/ deu doc co rollout, de nguyen mot ben la ben kia phai import
# nguoc — vong.
def _rollout_enabled(name: str) -> bool:
    """Co rollout co bat khong — TRA CUU MUON, khong ghim namespace.

    Ham nay gac MOI route co co (khong rieng mien entity), va bo test hien co va
    co qua `public_api.settings` (10 cho / 4 file). Doc thang `settings` cua
    module nay lam ban va do vo hieu — do duoc 70 bai do khi thu. Nen: uu tien
    `public_api.settings` neu module do da nap, roi moi den ban cua chinh minh.

    Import trong THAN ham chu khong o dau file: dau file la vong (public_api
    import nguoc entity_read). Trong than thi den luc goi moi tra, luc do ca hai
    module deu da nap xong.
    """
    import sys

    mod = sys.modules.get("public_api")
    nguon = getattr(mod, "settings", settings) if mod is not None else settings
    return getattr(nguon, name, False) is True


def _require_rollout(name: str) -> None:
    if not _rollout_enabled(name):
        raise HTTPException(404, "Not found")

# Import KÉP như public_api.py: gói `agent` được nạp cả dạng phẳng lẫn
# dạng gói tuỳ ngữ cảnh. Chỉ viết một lối là vỡ ở lối kia.
if __package__:
    from .ai_disclosure import load_ai_disclosure
    from .image_descriptor import describe_entity_images
    from .media_policy import is_renderable_entity_descriptor
else:
    from ai_disclosure import load_ai_disclosure
    from image_descriptor import describe_entity_images
    from media_policy import is_renderable_entity_descriptor


_GALLERY_DISCLOSURE = load_ai_disclosure()


def _err(status_code: int, detail: str, **extra) -> JSONResponse:
    """Error-shape chuẩn (SP3 W6.2): {detail, ...} — đồng nhất với
    server._error_response và HTTPException handler. Trước đây public_api trả
    {error: code} bypass handler; nay dùng detail (FE dựa HTTP status, không đọc
    error-code — đã verify grep web-nuxt)."""
    body: dict = {"detail": detail}
    body.update(extra)
    return JSONResponse(status_code=status_code, content=body)


_PLACE_CACHE_MAX = 500


_place_cache: OrderedDict[str, dict] = OrderedDict()


_place_cache_lock = _threading.Lock()


def _is_public(e: dict) -> bool:
    """Entity được hiển thị công khai (listing/homepage): loại entity provisional /
    chưa kiểm chứng (auto-learned). Quarantine cho public display — KB chat vẫn dùng,
    nhưng trang công khai KHÔNG show nội dung tự-học chưa duyệt (tránh cảm giác nghiệp dư)."""
    return e.get("status") != "provisional" and e.get("verified") not in (False, 0)


def _get_public_entity(entity_id: str) -> Optional[dict]:
    entity = db.get_entity(entity_id)
    if not entity or not _is_public(entity):
        return None
    return entity


def _filter_public_entities(entities: list[dict]) -> list[dict]:
    """Keep only entities eligible for anonymous public projections."""
    return [entity for entity in entities if _is_public(entity)]


def _get_public_entities_batch(entity_ids: list[str]) -> dict[str, dict]:
    """Batch lookup that cannot return provisional or explicitly unverified rows."""
    return {
        entity_id: entity
        for entity_id, entity in db.get_entities_batch(entity_ids).items()
        if _is_public(entity)
    }


def _public_facilities_by_place(place_id: str | None = None) -> list[dict]:
    return [
        _project_public_entity_media(entity)
        for entity in _filter_public_entities(db.facilities_by_place(place_id))
    ]


def _get_place(place_id: str) -> dict | None:
    with _place_cache_lock:
        if place_id in _place_cache:
            _place_cache.move_to_end(place_id)
            return _place_cache[place_id]
    place = db.get_entity(place_id)
    if place:
        with _place_cache_lock:
            _place_cache[place_id] = {"name": place["name"], "area": place.get("area")}
            if len(_place_cache) > _PLACE_CACHE_MAX:
                _place_cache.popitem(last=False)
    with _place_cache_lock:
        return _place_cache.get(place_id)


def _apply_cached_place(e: dict) -> None:
    explicit_area = e.get("area")
    pid = e.get("placeId")
    if pid:
        with _place_cache_lock:
            p = _place_cache.get(pid)
        if p:
            e["place_name"] = p["name"]
            e["place_area"] = explicit_area or p.get("area")
    elif explicit_area:
        e["place_area"] = explicit_area
    e["quality"] = entity_quality(e)


def _enrich_place(entities: list[dict]):
    with _place_cache_lock:
        uncached = {e["placeId"] for e in entities if e.get("placeId") and e["placeId"] not in _place_cache}
    if uncached:
        batch = db.get_entities_batch(list(uncached))
        with _place_cache_lock:
            for pid, place in batch.items():
                _place_cache[pid] = {"name": place["name"], "area": place.get("area")}
    for e in entities:
        _apply_cached_place(e)


def _project_public_entity_media(entity: dict, *, limit: int | None = None) -> dict:
    """Return an owned public projection with descriptor-only entity media."""
    projected = dict(entity)
    for key in ("image", "images", "image_url", "image_urls", "image_descriptor", "image_descriptors"):
        projected.pop(key, None)
    projected.pop("verifiedAt", None)
    descriptors = _gallery_editorial_images(entity)
    projected["image_descriptors"] = descriptors[:limit] if limit is not None else descriptors
    return projected


def _public_entity_has_media(entity: dict) -> bool:
    """Return whether the public projection contains renderable entity media."""
    return bool(_project_public_entity_media(entity, limit=1)["image_descriptors"])


_FULL_SCAN_LIMIT = 5000


_EVENT_SCAN_LIMIT = 2000


def _warn_if_scan_truncated(rows, limit: int, where: str) -> bool:
    """True khi lát cắt đã CHẠM trần — tức có thể đã mất dữ liệu.

    `>=` chứ không `>`: khi trả về đúng `limit` hàng thì không phân biệt được
    "vừa đủ" với "đã bị cắt", và ở ranh giới đó phải coi như đã cắt.
    """
    if len(rows) < limit:
        return False
    logger.warning(
        "%s: quét toàn kho CHẠM TRẦN %d hàng — dữ liệu vượt trần bị bỏ im lặng. "
        "Nâng trần hoặc chuyển sang phân trang trước khi tin kết quả.",
        where, limit,
    )
    return True


def _gallery_editorial_images(entity: dict) -> list[dict]:
    images = []
    for descriptor in describe_entity_images(
        entity,
        disclosure=_GALLERY_DISCLOSURE,
    ):
        serialized = asdict(descriptor)
        if is_renderable_entity_descriptor(serialized):
            images.append(serialized)
    return images


def invalidate_entity_cache(entity_id: str | None = None):
    """Compatibility hook retained after removing policy-bearing response memoization."""
    del entity_id


# Nghe-ngong khi place-cache bi xoa. `invalidate_place_cache` cham HAI tang:
# place-cache (song o day) va homepage-cache (song o public_api). Doi ca khoi
# sang day la keo nham tang; de nguyen ben public_api thi entity-admin phai
# import facade cong khai chi de xoa cache — mui ranh gioi ma boundary-test
# cua goi entities/ bat duoc. Listener giu dung hanh vi: public_api dang ky
# viec-cua-no luc import; khi public_api chua duoc nap thi homepage-cache
# cung chua ton tai nen khong co gi de xoa — van dung.
_place_invalidation_listeners: list = []


def invalidate_place_cache():
    """Xoá cache tên/khu-vực xã/phường — gọi sau /reload hoặc admin sửa place."""
    with _place_cache_lock:
        _place_cache.clear()
    for _fn in list(_place_invalidation_listeners):
        _fn()
