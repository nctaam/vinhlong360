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

import json
from pathlib import Path
import re
import threading as _threading
from collections import OrderedDict
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
    from .publication_status import PUBLISHED_V1_EXCLUSIONS
else:
    from ai_disclosure import load_ai_disclosure
    from image_descriptor import describe_entity_images
    from media_policy import is_renderable_entity_descriptor
    from publication_status import PUBLISHED_V1_EXCLUSIONS


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


def _load_ground_truth_overlays() -> tuple[dict[str, dict], dict[str, dict]]:
    """Load verified summary/attribute overlays from outputs/ground-truth-9router-verification-2026-10-21.json
    in-memory without mutating web/data.json or agent/data/vinhlong360.db on disk."""
    summary_fixes: dict[str, dict] = {}
    dossier_fixes: dict[str, dict] = {}
    try:
        gt_path = Path(__file__).resolve().parent.parent / "outputs" / "ground-truth-9router-verification-2026-10-21.json"
        if not gt_path.exists():
            return summary_fixes, dossier_fixes
        payload = json.loads(gt_path.read_text(encoding="utf-8"))
        for item in payload.get("truncatedSummaryFixes", []):
            eid = item.get("entityId")
            if eid and item.get("verifiedSummary"):
                summary_fixes[eid] = item
        for item in payload.get("verifiedDossiers", []):
            eid = item.get("entityId")
            if eid and isinstance(item.get("verifiedGroundTruth"), dict):
                dossier_fixes[eid] = item
    except Exception:
        pass
    return summary_fixes, dossier_fixes


_SUMMARY_FIXES, _DOSSIER_FIXES = _load_ground_truth_overlays()


def _apply_summary_fix(e: dict, sfix: dict | None) -> dict:
    if not sfix or e.get("summary") != sfix.get("currentSummary"):
        return e
    out = dict(e)
    out["summary"] = sfix["verifiedSummary"]
    if sfix.get("verifiedDescription") or not out.get("description") or out.get("description") == sfix.get("currentSummary"):
        out["description"] = sfix.get("verifiedDescription") or sfix["verifiedSummary"]
    return out


_TRUNC_PRICE_END_RE = re.compile(
    r"(?:Giá(?: bình dân| tham khảo| rẻ)?(?::\s*Khoảng)?\s+\d{1,3}|"
    r"(?:Bình dân chợ|Bờ sông|Hiện đại bình dân|Cổ điển, dưới bóng cây lớn|Phố đêm sầm uất)\s+000)\.$"
)
_MOJIBAKE_FIXES: dict[str, str] = {
    "ho-truc-giang": (
        "Hồ Trúc Giang hình thành từ khoảng đầu thập niên 1930 ngay trung tâm thành phố Bến Tre, "
        "trên khu đất từng bị đào lấy đất rồi tích nước thành hồ. Tên Trúc Giang gắn với giai đoạn "
        "tỉnh lỵ Kiến Hòa, còn người dân quen gọi nơi này là Bờ Hồ. Đường dạo quanh hồ rợp bóng me tây "
        "và phượng vĩ lâu năm; mùa hè, sắc phượng phản chiếu xuống mặt nước tạo khung cảnh rất riêng của "
        "xứ dừa. Giữa hồ có nhà thủy tạ, ven bờ có ghế đá và lối đi bộ, buổi sáng thường có người tập thể dục, "
        "chiều tối là điểm hẹn hóng mát. Phía tây hồ đặt tượng đồng Trần Văn Ơn, gần Đình An Hội, Chợ Bến Tre, "
        "Bảo tàng Bến Tre và Chùa Viên Minh. Hồ mở cửa tự do, không thu phí; thời điểm dễ chịu nhất để dạo Bờ Hồ "
        "là mùa khô từ tháng 11 đến tháng 4."
    ),
    "nha-hang-noi-ttc-ben-tre-ben-tre": (
        "Nhà hàng nổi TTC Bến Tre phục vụ cá sông, tôm càng xanh và hải sản tươi sống trên bè nổi bên sông Hàm Luông. "
        "Giá tham khảo: 100.000–200.000 đ/người. Giờ mở cửa: 10:00–22:00."
    ),
    "nha-hang-lang-be-ben-tre-ben-tre": (
        "Nhà hàng Làng Bè Bến Tre phục vụ cá đồng, cá sông và tôm càng xanh trong không gian sông nước miệt vườn. "
        "Giá tham khảo: 100.000–200.000 đ/người. Giờ mở cửa: 09:00–21:00."
    ),
    "hai-san-ngoc-hiep-binh-dai-ben-tre": (
        "Hải Sản Ngọc Hiệp Bình Đại phục vụ cua biển, tôm biển, mực và bạch tuộc tươi sống từ vùng biển Bình Đại. "
        "Giá tham khảo: 150.000–300.000 đ/người. Giờ mở cửa: 09:00–20:00."
    ),
    "nha-hang-hai-san-song-tra-binh-dai-ben-tre": (
        "Nhà hàng Hải Sản Sông Trà ở Bình Đại phục vụ cá sông, tôm càng xanh, cua đồng và tép bạc từ sông Trà. "
        "Giá tham khảo: 100.000–250.000 đ/người. Giờ mở cửa: 10:00–21:00."
    ),
    "con-cu": (
        "Điểm tham quan nằm trong khu vực biển Ba Động thuộc xã Nhị Long, từng được quy hoạch phát triển du lịch sinh thái "
        "ven biển với dải cồn cát tự nhiên và thảm thực vật ngập mặn phong phú."
    ),
    "agribank-chi-nhanh-vinh-long-vinh-long": (
        "Cơ sở giao dịch chính của Agribank tại số 28 Hưng Đạo Vương, Phường Long Châu (Phường 1, TP. Vĩnh Long cũ), "
        "cung cấp dịch vụ ngân hàng, tài chính và hệ thống ATM hỗ trợ thẻ quốc tế cho người dân và du khách."
    ),
}
_PROSE_PATCHES: dict[str, tuple[str | None, str | None]] = {
    "xuong-thu-cong-cocohand-vuon-dua-huu-co": (
        "Cơ sở sản xuất tranh dừa thủ công mỹ nghệ Cocohand tại ấp Bình Đông 1, xã Hương Mỹ, kết hợp tham quan vườn dừa hữu cơ rộng hơn 11.000m².",
        "Cơ sở sản xuất tranh dừa thủ công mỹ nghệ Cocohand tại ấp Bình Đông 1, xã Hương Mỹ, kết hợp tham quan vườn dừa hữu cơ rộng hơn 11.000m². Khuôn viên có tổ ong lấy mật truyền thống và ao cá, tạo cảnh quan miệt vườn đặc trưng.",
    ),
    "khu-du-lich-sinh-thai-sala": (
        "Khu du lịch sinh thái rộng 20 ha tại xã Mỹ Thạnh Trung, tổng đầu tư hơn 40 tỷ đồng, cách trung tâm TP. Vĩnh Long khoảng 25 km.",
        None,
    ),
    "com-chay-au-lac-vinh-long": (
        "Quán cơm chay Âu Lạc bình dân trên đường Trần Văn Ơn, Phường Long Châu (Phường 1, TP. Vĩnh Long cũ).",
        None,
    ),
    "cong-vien-29": (
        None,
        "Công viên rộng rãi nằm ở trung tâm Tân Quới với không gian xanh mát, nhiều cây xanh và hoa kiểng. Thường xuyên tổ chức các hoạt động văn hóa, thể thao và sinh hoạt cộng đồng.",
    ),
    "hai-dang-ba-dong": (
        None,
        "Ngọn hải đăng ở ấp Nhà Mát, Phường Trường Long Hòa — một trong những điểm tham quan tại khu vực biển Ba Động. Công trình mang giá trị lịch sử, cảnh quan biển và là điểm ngắm bình minh, chụp ảnh.",
    ),
    "chua-van-phuoc": (
        None,
        "Ngôi chùa tại Bến Tre được mệnh danh là 'tiên cảnh chốn trần gian', là điểm du lịch tâm linh và chiêm bái nổi tiếng giữa rừng ngập mặn Bình Đại.",
    ),
    "kem-baskin-robbins---sense-city": (
        None,
        "Chi nhánh kem và tráng miệng quốc tế tại tầng trệt Trung tâm thương mại Sense City, số 26A Trần Quốc Tuấn, Phường Bến Tre.",
    ),
    "festival-gach-gom-do-kinh-te-xanh-tinh-vinh-long-vinh-long": (
        None,
        "Giữa rừng lò gạch đỏ trăm tuổi dọc kinh Thầy Cai, Festival Gạch Gốm Đỏ – Kinh tế Xanh tỉnh Vĩnh Long lần I (16–23/11/2024) thắp sáng 'vương quốc' Mang Thít. Sân khấu nổi trên chiếc sà lan 3.000 tấn neo giữa làng nghề, hội chợ 700–800 gian hàng công thương – nông nghiệp – du lịch mở rộng ra đường Võ Văn Kiệt. Phó Thủ tướng Hồ Đức Phớc dự khai mạc; kỷ lục Việt Nam 102 món từ tàu hủ ky ra đời ngay tại đây. Festival gắn với Đề án Di sản đương đại Mang Thít quy mô 3.060 ha.",
    ),
    "lang-van-coffee": (
        None,
        "Quán cà phê tại Quốc Lộ 60, TP. Bến Tre với không gian sân vườn rộng rãi, thoáng mát, phục vụ đa dạng cà phê và thức uống giải khát.",
    ),
}


def _apply_prose_patch(e: dict, eid: str) -> dict:
    if eid not in _PROSE_PATCHES:
        return e
    s_patch, d_patch = _PROSE_PATCHES[eid]
    out = dict(e)
    if s_patch:
        out["summary"] = s_patch
    if d_patch:
        out["description"] = d_patch
    if eid == "kem-baskin-robbins---sense-city":
        attrs = dict(out.get("attributes") or {})
        if attrs.get("specialty") == "Ốc":
            attrs["specialty"] = "Kem tươi, tráng miệng lạnh"
            out["attributes"] = attrs
    return out


def _repair_corrupted_prose(e: dict) -> dict:
    eid = str(e.get("id") or "")
    if eid in _MOJIBAKE_FIXES and "?" in str(e.get("description") or ""):
        e = {**e, "description": _MOJIBAKE_FIXES[eid]}
    e = _apply_prose_patch(e, eid)
    desc = str(e.get("description") or "").strip()
    if desc and _TRUNC_PRICE_END_RE.search(desc):
        attrs = e.get("attributes") or {}
        price = attrs.get("price_range") or attrs.get("price") if isinstance(attrs, dict) else None
        suffix = f" Giá tham khảo: {price}." if price else ""
        e = {**e, "description": _TRUNC_PRICE_END_RE.sub("", desc).rstrip() + suffix}
    return e


def _apply_dossier_fix(e: dict, dfix: dict | None) -> dict:
    if not dfix or len(str(e.get("summary") or "")) <= 25:
        return e
    gt = dfix["verifiedGroundTruth"]
    curr = dfix.get("currentInDataJson") or {}
    out = dict(e)
    if gt.get("summary") and out.get("summary") == curr.get("summary"):
        out["summary"] = gt["summary"]
    attrs = dict(out.get("attributes") or {})
    for k in ("address", "phone", "hours"):
        if gt.get(k) and not attrs.get(k):
            attrs[k] = gt[k]
    out["attributes"] = attrs
    return out


def _apply_ground_truth_overlay(e: dict) -> dict:
    eid = e.get("id")
    if not eid:
        return e
    e = _apply_summary_fix(e, _SUMMARY_FIXES.get(eid))
    e = _apply_dossier_fix(e, _DOSSIER_FIXES.get(eid))
    return _repair_corrupted_prose(e)


def _is_public(e: dict) -> bool:
    """Entity được hiển thị công khai (listing/homepage): loại entity provisional /
    chưa kiểm chứng (auto-learned) và các ID nằm trong PUBLISHED_V1_EXCLUSIONS."""
    return (
        e.get("status") != "provisional"
        and e.get("verified") not in (False, 0)
        and e.get("id") not in PUBLISHED_V1_EXCLUSIONS
    )


def _get_public_entity(entity_id: str) -> Optional[dict]:
    entity = db.get_entity(entity_id)
    if not entity or not _is_public(entity):
        return None
    return _apply_ground_truth_overlay(entity)


def _filter_public_entities(entities: list[dict]) -> list[dict]:
    """Keep only entities eligible for anonymous public projections."""
    return [_apply_ground_truth_overlay(entity) for entity in entities if _is_public(entity)]


def _get_public_entities_batch(entity_ids: list[str]) -> dict[str, dict]:
    """Batch lookup that cannot return provisional or explicitly unverified rows."""
    return {
        entity_id: _apply_ground_truth_overlay(entity)
        for entity_id, entity in db.get_entities_batch(entity_ids).items()
        if _is_public(entity)
    }


# Dời từ public_api.py cùng đợt bóc itineraries/ (2026-08-29, bước 1a lát 2):
# cả route itinerary (sang itineraries/api.py) LẪN homepage của public_api đều
# gọi hai helper này — để nguyên chỗ cũ là gói mới phải import ngược public_api
# (test_itineraries_boundary.py cấm). Nhà tự nhiên: chúng lọc stop theo
# _get_public_entities_batch ngay trên đây.
def _itinerary_stop_entity_id(stop) -> str:
    if isinstance(stop, str):
        return stop
    if isinstance(stop, dict):
        return str(stop.get("entityId") or stop.get("entity_id") or stop.get("id") or "")
    return ""


def _clean_stop_note(stop: dict, stop_id: str, entity: dict) -> None:
    note = stop.get("note")
    if not stop_id or not isinstance(note, str) or stop_id not in note:
        return
    attrs = entity.get("attributes")
    tip = (attrs.get("travel_tip") or attrs.get("highlight")) if isinstance(attrs, dict) else None
    stop["note"] = str(tip).strip() if tip else note.replace(stop_id, entity["name"])


def _enrich_itinerary_stop(stop: dict, stop_id: str, entity: dict) -> None:
    stop.setdefault("id", stop_id)
    stop.setdefault("entityId", stop_id)
    stop["name"] = entity["name"]
    if not stop.get("summary"):
        stop["summary"] = entity.get("summary", "")
    stop["type"] = entity["type"]
    if entity.get("coordinates"):
        stop["coordinates"] = entity["coordinates"]


def _public_itinerary_stops(
    stops: list, public_entities: dict[str, dict] | None = None, *, enrich: bool = False,
) -> list:
    stop_ids = [sid for sid in (_itinerary_stop_entity_id(stop) for stop in stops) if sid]
    if public_entities is None:
        public_entities = _get_public_entities_batch(stop_ids)
    result = []
    for stop in stops:
        stop_id = _itinerary_stop_entity_id(stop)
        if stop_id and stop_id not in public_entities:
            continue
        entity = public_entities.get(stop_id) if isinstance(stop, dict) else None
        if entity:
            _clean_stop_note(stop, stop_id, entity)
            if enrich:
                _enrich_itinerary_stop(stop, stop_id, entity)
        result.append(stop)
    return result


def _public_facilities_by_place(place_id: str | None = None) -> list[dict]:
    return [
        _project_public_entity_media(entity)
        for entity in _filter_public_entities(db.facilities_by_place(place_id))
    ]


EXTERNAL_GATEWAY_PLACE_IDS: frozenset[str] = frozenset({"gateway-hcm"})


def _get_place(place_id: str) -> dict | None:
    if not place_id or place_id in EXTERNAL_GATEWAY_PLACE_IDS:
        return None
    with _place_cache_lock:
        if place_id in _place_cache:
            _place_cache.move_to_end(place_id)
            return _place_cache[place_id]
    place = db.get_entity(place_id)
    if not place:
        return None
    entry = {"name": place["name"], "area": place.get("area")}
    with _place_cache_lock:
        _place_cache[place_id] = entry
        _place_cache.move_to_end(place_id)
        if len(_place_cache) > _PLACE_CACHE_MAX:
            _place_cache.popitem(last=False)
    return entry


_PLACE_MISSING = object()


def _apply_cached_place(e: dict, *, cached_place: dict | object = _PLACE_MISSING) -> None:
    explicit_area = e.get("area")
    pid = e.get("placeId")
    if pid:
        if cached_place is _PLACE_MISSING:
            with _place_cache_lock:
                p = _place_cache.get(pid)
        else:
            p = cached_place
        if isinstance(p, dict):
            e["place_name"] = p["name"]
            e["place_area"] = explicit_area or p.get("area")
    elif explicit_area:
        e["place_area"] = explicit_area
    e["quality"] = entity_quality(e)


def _warm_and_snapshot_places(needed_ids: set[str]) -> dict[str, dict | None]:
    with _place_cache_lock:
        uncached = [pid for pid in needed_ids if pid not in _place_cache]
    if uncached:
        batch = db.get_entities_batch(uncached)
        with _place_cache_lock:
            for pid, place in batch.items():
                _place_cache[pid] = {"name": place["name"], "area": place.get("area")}
            while len(_place_cache) > _PLACE_CACHE_MAX:
                _place_cache.popitem(last=False)
    with _place_cache_lock:
        return {pid: _place_cache.get(pid) for pid in needed_ids}


def _enrich_place(entities: list[dict]):
    needed_ids = {e["placeId"] for e in entities if e.get("placeId")}
    place_snapshot = _warm_and_snapshot_places(needed_ids) if needed_ids else {}
    for e in entities:
        pid = e.get("placeId")
        _apply_cached_place(e, cached_place=place_snapshot.get(pid) if pid else None)


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
        serialized = dict(vars(descriptor))
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
