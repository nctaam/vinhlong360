#!/usr/bin/env python3
"""Phase 6 atomic polish: replace final 25 R10.6 entities with AI art & expand 3 street-only market addresses.

Supports both local SQLite (`--sqlite`) and VPS PostgreSQL (`--postgres-env`).
All functions stay modular and within cyclomatic complexity <= 10 for R20.8.
"""
from __future__ import annotations

import argparse
import json
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
from apply_phase5_polish import (  # noqa: E402
    _apply_sqlite_updates,
    _sync_address_field,
)

STALE_PRESS_KEYS = (
    "image_author",
    "image_source",
    "image_license",
    "image_source_url",
    "image_url",
    "image_credit",
    "permission_evidence",
    "license_scope",
)

AI_IMAGE_CAPTIONS: dict[str, str] = {
    "chua-phat-ngoc-xa-loi": (
        "Minh họa tòa Bảo Tháp chín tầng uy nghiêm cùng mái ngói cong và khuôn viên xanh mát "
        "của Chùa Phật Ngọc Xá Lợi tại Vĩnh Long."
    ),
    "lau-tai-co": (
        "Minh họa nồi lẩu cù lao than hồng bày tôm tươi, chả cá, cà rốt tỉa hoa và rau xanh "
        "dùng nóng bên bàn gỗ mộc."
    ),
    "lau-mam-ben-tre": (
        "Minh họa nồi lẩu mắm đất nung sôi nghi ngút khói kèm mẹt bông súng tím, bông điên điển, "
        "cà tím, đậu bắp và tôm tươi."
    ),
    "banh-trang-my-long": (
        "Minh họa xấp bánh tráng nướng cốt dừa Mỹ Lồng vàng giòn xếp trên mẹt tre bên những "
        "gáo dừa tươi bổ đôi."
    ),
    "mam-tom-cha-vinh-long": (
        "Minh họa tô mắm tôm chà đỏ au sóng sánh bày cùng thịt luộc, bánh hỏi, khế chua và "
        "rau thơm trên tàu lá chuối."
    ),
    "chuoi-nuong-gia-truyen": (
        "Minh họa những khoanh chuối nếp nướng vỏ xém thơm rưới nước cốt dừa béo ngậy và "
        "mè rang vàng trong chén gốm."
    ),
    "ca-tai-tuong-chien-xu": (
        "Minh họa món cá tai tượng chiên xù dựng nguyên con vảy giòn rụm kèm bánh tráng, bún tươi, "
        "rau cải xanh và chén mắm me."
    ),
    "banh-xeo-mien-tay": (
        "Minh họa bánh xèo vỏ nghệ giòn rụm gấp nhân tôm thịt và giá đỗ trên mẹt tre lót lá chuối "
        "cùng cải xanh và nước mắm chua ngọt."
    ),
    "goi-cuon-tom-thit": (
        "Minh họa đĩa gỏi cuốn tôm thịt trong suốt thấy rõ tôm luộc, thịt ba rọi, hẹ xanh "
        "chấm cùng tương đậu phộng giã nhỏ."
    ),
    "cha-gio-chay": (
        "Minh họa đĩa chả giò chay chiên vàng giòn cắt xéo bày kèm rau sống, đồ chua bào sợi "
        "và chén nước tương tỏi ớt."
    ),
    "chao-ca-loc-rau-dang": (
        "Minh họa tô cháo cá lóc nóng hổi đầy phi lê cá ngọt thịt, gừng sợi và hành ngò dùng "
        "kèm rổ rau đắng đất tươi xanh."
    ),
    "tom-cang-xanh-nuong": (
        "Minh họa tôm càng xanh xẻ lưng nướng than hồng gạch son óng ả trên lá chuối kèm "
        "muối ớt xanh và chanh tươi."
    ),
    "banh-canh-ben-tre": (
        "Minh họa tô bánh canh bột xắt nấu nước cốt dừa sánh béo với thịt nạc, hành phi thơm "
        "và hành lá thái nhỏ."
    ),
    "bo-nuong-la-lot": (
        "Minh họa những xiên bò cuộn lá lốt nướng thơm phủ đậu phộng rang và mỡ hành bày "
        "bên bánh hỏi cùng khế chua."
    ),
    "xoi-vi-mien-tay": (
        "Minh họa từng miếng xôi vị nhiều tầng màu xanh lá dứa và tím lá cẩm rắc mè rang "
        "xếp ngay ngắn trên lá chuối."
    ),
    "tom-rang-muoi-ot": (
        "Minh họa đĩa tôm rang muối ớt áo lớp tỏi phi giòn và ớt đỏ cay nồng bày trên đĩa "
        "sứ thô trang trí ngò rí."
    ),
    "duong-dua": (
        "Minh họa thức quà đặc trưng vùng xứ dừa bài trí mộc mạc trong gáo dừa cùng lá chuối "
        "gói gọn và chén nước mắm ớt."
    ),
    "tep-rang-dua": (
        "Minh họa bát tép đồng rang nước cốt dừa sánh kẹo vàng óng điểm hành lá xanh trên "
        "bàn ăn gỗ giản dị."
    ),
    "cua-com-duyen-hai": (
        "Minh họa đĩa cua cốm vùng biển Duyên Hải hấp chín đỏ gạch son béo ngậy bày cạnh "
        "muối tiêu chanh và rau răm."
    ),
    "tom-cang-xanh-song-tien": (
        "Minh họa sọt tre đầy tôm càng xanh sông Tiền tươi rói ướp đá lạnh trên khoang ghe "
        "lúc nắng sớm ban mai."
    ),
    "bun-bo-co-tam-cho-ben-tre-ben-tre": (
        "Minh họa tô bún bò nóng hổi nhiều nạm thịt, chả cua và nước dùng đậm đà ăn kèm "
        "mẹt bắp chuối, giá sống."
    ),
    "com-ga-xoi-mo-5-vi-ben-tre": (
        "Minh họa đĩa cơm gà xối mỡ da giòn màu cánh gián đặt trên cơm đỏ thơm lừng kèm "
        "dưa leo, đồ chua và chén canh."
    ),
    "tinh-binh-chay-vinh-long": (
        "Minh họa mâm cơm chay thanh đạm gồm nấm kho tộ, đậu hũ chiên sả, gỏi ngó sen "
        "và chén cơm trắng dẻo thơm."
    ),
    "com-chay-au-lac-vinh-long": (
        "Minh họa phần cơm chay truyền thống với cà tím kho tiêu, rau xào xanh mướt, canh "
        "nấm đậu hũ và chén cơm đầy đặn."
    ),
    "nem-nuong-thanh-binh-ben-tre": (
        "Minh họa mẹt nem nướng xiên que xém vàng thơm lừng dùng kèm bánh tráng, xoài xanh, "
        "rau thơm và tương chấm đậu phộng."
    ),
}

EXPLICIT_ADDRESS_FIXES: dict[str, str] = {
    "cho-binh-dai": "Chợ Bình Đại, QL57B, Phường Bình Đại, tỉnh Vĩnh Long",
    "cho-thanh-phu": "Chợ Thạnh Phú, Đường Thuỷ Sản, Xã Thạnh Phú, tỉnh Vĩnh Long",
    "cho-ba-tri": "Chợ Ba Tri, Đường Nguyễn Đình Chiểu, Phường Ba Tri, tỉnh Vĩnh Long",
}


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


def _update_one_entity(eid: str, row: dict[str, Any], stats: dict[str, int]) -> dict[str, Any]:
    attrs = dict(row["attrs"])
    up: dict[str, Any] = {}
    attrs_dirty = False
    if eid in AI_IMAGE_CAPTIONS and _apply_ai_media_truth(attrs, AI_IMAGE_CAPTIONS[eid]):
        attrs_dirty = True
        stats["ai_media_updated"] += 1
    if eid in EXPLICIT_ADDRESS_FIXES:
        addr_up, addr_attr_dirty = _sync_address_field(row, attrs, EXPLICIT_ADDRESS_FIXES[eid])
        up.update(addr_up)
        if addr_up:
            stats["addresses_updated"] += 1
        elif addr_attr_dirty:
            stats["parity_synced"] += 1
        if addr_attr_dirty:
            attrs_dirty = True
    if attrs_dirty:
        row["attrs"] = attrs
        up["attributes"] = attrs
    return up


def _build_updates(entities: dict[str, dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, int]]:
    updates: dict[str, dict[str, Any]] = {}
    stats = {"ai_media_updated": 0, "addresses_updated": 0, "parity_synced": 0}
    for eid, row in entities.items():
        up = _update_one_entity(eid, row, stats)
        if up:
            updates[eid] = up
    return updates, stats


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
