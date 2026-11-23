#!/usr/bin/env python3
"""Phase 5 atomic polish: 16 replaced-image metadata updates, parity sync & 2-tier addresses.

Supports both local SQLite (`--sqlite`) and VPS PostgreSQL (`--postgres-env`).
All functions stay modular and within cyclomatic complexity <= 10 for R20.8.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

OPS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(OPS_DIR))
from apply_phase4_ground_truth_and_dedup import (  # noqa: E402
    _apply_pg_entity_updates,
    _load_snapshot,
    _open_conn,
)

STALE_PRESS_KEYS = (
    "image_author",
    "image_source",
    "image_license",
    "image_source_url",
    "image_url",
    "permission_evidence",
    "license_scope",
)

AI_IMAGE_CAPTIONS: dict[str, str] = {
    "banh-tet-tra-cuon": (
        "Minh họa Bánh tét Trà Cuôn cắt khoanh xếp trên lá chuối với lớp nếp xanh lá bồ ngót, "
        "nhân đậu xanh, thịt ba rọi và trứng muối."
    ),
    "cho-dai-an": (
        "Minh họa không gian Chợ Đại An ven kênh với ghe xuồng, sạp rau quả và nhịp buôn bán "
        "buổi sáng vùng sông nước."
    ),
    "linga-va-yoni-luu-cu-ii": (
        "Minh họa hiện vật đá sa thạch Linga và Yoni Lưu Cừ II trưng bày trên bệ bảo tàng, "
        "di vật tiêu biểu của văn hóa Óc Eo."
    ),
    "xa-vinh-kim": (
        "Minh họa cảnh quan nông thôn Xã Vĩnh Kim xanh mát rặng dừa, đồng lúa chín vàng "
        "và cây cầu gỗ bắc qua con rạch nhỏ."
    ),
    "xa-phu-thuan": (
        "Minh họa tuyến rạch Xã Phú Thuận rợp bóng dừa nước ven sông với chiếc xuồng ba lá "
        "nhẹ trôi trong nắng sớm."
    ),
    "xa-long-huu": (
        "Minh họa toàn cảnh Xã Long Hữu vùng ven biển với đầm nuôi thủy sản, dải rừng ngập mặn "
        "xanh và cánh đồng điện gió ngoài khơi."
    ),
    "xa-long-vinh": (
        "Minh họa vùng cửa sông ven biển Xã Long Vĩnh với rừng đước ngập mặn và những chiếc ghe "
        "đánh cá neo đậu lúc bình minh."
    ),
    "khu-du-lich-sinh-thai-sala": (
        "Minh họa cầu gỗ uốn lượn qua hồ sen hồng nở rộ và các chòi lá sinh thái tại "
        "Khu du lịch sinh thái Sala."
    ),
    "homestay-lang-be": (
        "Minh họa nhà chòi gỗ mái lá ven sông nước cù lao của Homestay Làng Bè ánh đèn ấm "
        "vào lúc hoàng hôn."
    ),
    "lo-lem-homestay": (
        "Minh họa sân vườn Lọ Lem Homestay lung linh ánh đèn lồng dưới mái hiên gỗ và lối đi "
        "gạch rợp cây xanh."
    ),
    "khach-san-hoang-khiem": (
        "Minh họa mặt tiền kiến trúc boutique ấm áp với hàng cọ xanh đón khách lúc chập tối "
        "của Khách sạn Hoàng Khiêm."
    ),
    "nam-thanh-homestay": (
        "Minh họa ngôi nhà gỗ ba gian Nam Bộ nằm giữa vườn chôm chôm, nhãn trĩu quả bên con rạch "
        "của Năm Thành Homestay."
    ),
    "banh-nhat-ngoc": (
        "Minh họa đĩa bánh khoai lang tím và bánh đậu xanh truyền thống xếp trên mẹt tre bên "
        "tách trà ấm tại Bánh Nhật Ngọc."
    ),
    "cua-hang-dac-san-mekong": (
        "Minh họa kệ gỗ trưng bày giỏ mây tre, hũ mật ong và đặc sản vùng đồng bằng tại "
        "Cửa hàng đặc sản Mekong."
    ),
    "cap-cuu-115-ben-tre-ben-tre": (
        "Minh họa trạm tiếp nhận cấp cứu y tế khang trang cùng xe cứu thương trực 24/7."
    ),
    "ho-truc-giang": (
        "Minh họa cảnh quan Hồ Trúc Giang tĩnh lặng bên hàng liễu rủ, phượng vĩ và lối dạo "
        "lát đá phản chiếu nắng chiều."
    ),
}

EXPLICIT_ADDRESS_FIXES: dict[str, str] = {
    "khu-luu-niem-nguyen-dinh-chieu": "Ấp Giồng Cụt, Phường Ba Tri, tỉnh Vĩnh Long",
    "nha-co-huynh-thuy-le": "255A đường Nguyễn Huệ, Phường Sa Đéc, tỉnh Đồng Tháp (điểm kết nối ngoại tỉnh)",
    "thoai-ngoc-hau": (
        "Làng An Hải, Điện Bàn, Quảng Nam (quê gốc); Sơn Lăng, núi Sam, Châu Đốc, An Giang (nơi an táng); "
        "Cù Lao Dài, Xã Quới Thiện, tỉnh Vĩnh Long (nơi phụng thờ thân mẫu và em gái)"
    ),
    "phan-thanh-gian": (
        "Làng Tân Thạnh, Xã Bảo Thạnh, tỉnh Vĩnh Long (quê hương); "
        "Văn Thánh Miếu, Phường Phước Hậu, tỉnh Vĩnh Long (nơi thờ tự và hoạt động)"
    ),
    "vo-van-kiet": (
        "Xã Trung Ngãi, tỉnh Vĩnh Long (quê hương); "
        "Khu lưu niệm tại số 102 đường Nam Kỳ Khởi Nghĩa, Phường Vũng Liêm, tỉnh Vĩnh Long"
    ),
    "san-chim-vam-ho": (
        "Ven sông Ba Lai, Xã Mỹ Chánh Hòa & Xã Tân Xuân, tỉnh Vĩnh Long "
        "(trước 07/2025: Tân Mỹ – Mỹ Hòa – Tân Xuân)"
    ),
    "cua-com-duyen-hai": "Phường Duyên Hải & Xã Long Hữu (vùng biển Ba Động), tỉnh Vĩnh Long",
    "buoi-nam-roi-binh-minh": (
        "Cù lao Mỹ Hòa, Phường Bình Minh, tỉnh Vĩnh Long "
        "(điểm bán: Nhà lồng chợ Mỹ Hòa, Phường Bình Minh)"
    ),
    "am-thuc-san-vuon-1985-vinh-long": "Phường Long Châu, tỉnh Vĩnh Long (Facebook: Ẩm Thực Sân Vườn 1985, Vĩnh Long)",
    "ben-xe-tra-on-tich-thien-vinh-long": "Khu vực Tích Thiện – Trà Ôn, Phường Trà Ôn, tỉnh Vĩnh Long",
    "chua-o-mich-ratanadiparamkoskeo": "Ấp Ô Mịch, xã Châu Điền, Phường Hùng Hoà, tỉnh Vĩnh Long",
    "chua-phi-rum-soc-bhiramyaraja": "Ấp Rùm Sóc, xã Châu Điền, Xã Cầu Kè, tỉnh Vĩnh Long",
    "le-hoi-nguyen-tieu-o-tra-cu": "Xã Đại An, tỉnh Vĩnh Long",
    "ben-pha-tran-phu-can-tho-vinh-long-vinh-long": (
        "Khu vực bờ Cái Vồn, Phường Cái Vồn, tỉnh Vĩnh Long (đối diện Cần Thơ qua sông Hậu)"
    ),
    "quan-tom-cang-xanh-hai-lua-cu-lao-an-binh-vinh-long": "Cù lao An Bình, Xã An Bình, tỉnh Vĩnh Long",
    "tuyen-song-co-chien-hoang-hon-bo-ke-vinh-long": "Bờ kè sông Cổ Chiên, Phường Long Châu, tỉnh Vĩnh Long",
    "tom-su-sinh-thai-tra-vinh": "Vùng ven biển Duyên Hải – Trà Cú, Phường Trà Vinh, tỉnh Vĩnh Long",
}

STRIP_PATTERNS = (
    r"\s*\((?:Phường\s+\d+|xã\s+[^)]+|thị trấn\s+[^)]+|huyện\s+[^)]+|TP\.?\s*[^)]+)\s*(?:cũ|,\s*TP\.?\s*[^)]+cũ)?\)",
    r"\b(?:nay là|nay thuộc)\s+(?:xã|phường)\s+[^,;()]+(?:,\s*tỉnh Vĩnh Long)?",
    r",?\s*\b(?:huyện|thị xã|TX\.?|TP\.?|thành phố)\s+(?:Vĩnh Long|Bến Tre|Trà Vinh|Bình Minh|Duyên Hải|Long Hồ|Mang Thít|Tam Bình|Trà Ôn|Vũng Liêm|Ba Tri|Giồng Trôm|Mỏ Cày Nam|Mỏ Cày Bắc|Châu Thành|Chợ Lách|Bình Đại|Thạnh Phú|Càng Long|Cầu Kè|Tiểu Cần|Cầu Ngang|Trà Cú)\b\.?",
    r"\bthị trấn\s+(Vũng Liêm|Trà Ôn|Cái Nhum|Cầu Kè|Duyên Hải|Ba Tri|Phước Mỹ Trung|Tân Quới|Mỹ Long|Tiểu Cần)\b",
)

LEGACY_ADDR_RE = re.compile(r"\b(huyện|thị xã|thị trấn|TP\.?\s+|TX\.?\s+|Thành phố)\b", re.I)


def _normalize_address_2tier(eid: str, pname: str, addr: str) -> str:
    if eid in EXPLICIT_ADDRESS_FIXES:
        return EXPLICIT_ADDRESS_FIXES[eid]
    s = re.sub(r"\bXã TT\s+", "Xã ", addr.strip())
    s = re.sub(r"\bTT\s+", "", s)
    for pat in STRIP_PATTERNS:
        s = re.sub(pat, "", s, flags=re.I)
    s = re.sub(r",?\s*(?:tỉnh\s+)?Vĩnh Long\.?$", "", s, flags=re.I).strip()
    s = re.sub(r"\(\s*\)", "", s)
    s = re.sub(r"\s*,\s*,+", ", ", s)
    s = re.sub(r"\s*–\s*$", "", s)
    s = re.sub(r"\s{2,}", " ", s).strip(" ,;-–")
    pname_norm = pname.lower().replace("hòa", "hoà")
    s_lower = s.lower().replace("hòa", "hoà")
    if pname and pname_norm not in s_lower:
        s = f"{s}, {pname}" if s else pname
    elif not s:
        s = pname or "tỉnh Vĩnh Long"
    return s if s.lower().endswith("tỉnh vĩnh long") else f"{s}, tỉnh Vĩnh Long"


def _sync_address_field(row: dict[str, Any], attrs: dict[str, Any], target_addr: str) -> tuple[dict[str, Any], bool]:
    up: dict[str, Any] = {}
    cleaned = target_addr.strip()
    dirty = False
    if row.get("address") != cleaned:
        row["address"] = cleaned
        up["address"] = cleaned
    if attrs.get("address") != cleaned:
        attrs["address"] = cleaned
        dirty = True
    return up, dirty


def _apply_ai_media_truth(attrs: dict[str, Any], caption: str) -> bool:
    dirty = False
    for key in STALE_PRESS_KEYS:
        if key in attrs:
            attrs.pop(key, None)
            dirty = True
    for k, val in (("image_type", "ai-generated"), ("is_verified_photo", False), ("image_caption", caption)):
        if attrs.get(k) != val:
            attrs[k] = val
            dirty = True
    return dirty


def _maybe_sync_address(
    eid: str, row: dict[str, Any], attrs: dict[str, Any], up: dict[str, Any], places: dict[str, str], stats: dict[str, int]
) -> bool:
    pid = row.get("placeId") or ""
    addr = row.get("address") or ""
    if eid == "gateway-hcm" or pid == "gateway-hcm":
        return False
    if eid not in EXPLICIT_ADDRESS_FIXES and not LEGACY_ADDR_RE.search(addr):
        return False
    new_addr = _normalize_address_2tier(eid, places.get(pid, ""), addr)
    addr_up, addr_attr_dirty = _sync_address_field(row, attrs, new_addr)
    up.update(addr_up)
    if addr_up:
        stats["addresses_updated"] += 1
    elif addr_attr_dirty:
        stats["parity_synced"] += 1
    return addr_attr_dirty


def _update_one_entity(
    eid: str, row: dict[str, Any], places: dict[str, str], stats: dict[str, int]
) -> dict[str, Any]:
    attrs = dict(row["attrs"])
    up: dict[str, Any] = {}
    attrs_dirty = eid in AI_IMAGE_CAPTIONS and _apply_ai_media_truth(attrs, AI_IMAGE_CAPTIONS[eid])
    if attrs_dirty:
        stats["ai_media_updated"] += 1
    if _maybe_sync_address(eid, row, attrs, up, places, stats):
        attrs_dirty = True
    if attrs_dirty:
        row["attrs"] = attrs
        up["attributes"] = attrs
    return up


def _build_updates(entities: dict[str, dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, int]]:
    places = {eid: r["name"] for eid, r in entities.items() if r["type"] == "place"}
    updates: dict[str, dict[str, Any]] = {}
    stats = {"ai_media_updated": 0, "addresses_updated": 0, "parity_synced": 0}
    for eid, row in entities.items():
        up = _update_one_entity(eid, row, places, stats)
        if up:
            updates[eid] = up
    return updates, stats


def _apply_sqlite_updates(conn: sqlite3.Connection, updates: dict[str, dict[str, Any]]) -> None:
    cur = conn.cursor()
    cur.execute("BEGIN IMMEDIATE")
    for eid, up in updates.items():
        cols, vals = [], []
        if "address" in up:
            cols.append('"address" = ?')
            vals.append(up["address"])
        if "attributes" in up:
            cols.append("attributes = ?")
            vals.append(json.dumps(up["attributes"], ensure_ascii=False))
        if cols:
            cur.execute(f"UPDATE entities SET {', '.join(cols)} WHERE id = ?", [*vals, eid])
    cur.execute("INSERT INTO entities_fts(entities_fts) VALUES('rebuild')")
    conn.commit()
    conn.execute("VACUUM")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    src_group = ap.add_mutually_exclusive_group(required=True)
    src_group.add_argument("--sqlite", type=Path)
    src_group.add_argument("--postgres-env", action="store_true")
    mode_group = ap.add_mutually_exclusive_group()
    mode_group.add_argument("--dry-run", action="store_true")
    mode_group.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)
    apply_changes = bool(args.apply)

    conn, cur, is_pg = _open_conn(args)
    try:
        entities, _, _ = _load_snapshot(cur, is_pg=is_pg)
        updates, stats = _build_updates(entities)
        if apply_changes:
            if is_pg:
                _apply_pg_entity_updates(conn.cursor(), updates)
                conn.commit()
            else:
                _apply_sqlite_updates(conn, updates)
        else:
            conn.rollback()
        summary = {"entities_touched": len(updates), **stats}
        print(f"[{'APPLIED' if apply_changes else 'DRY-RUN'}][{'postgres' if is_pg else 'sqlite'}] {json.dumps(summary, ensure_ascii=False)}")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
