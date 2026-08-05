# -*- coding: utf-8 -*-
"""Sửa khung hành chính cũ trong các trường LỒNG mà cổng R10.7 chưa nhìn thấy.

Cổng chỉ quét `name`/`description`/`summary` và attributes kiểu chuỗi, nên 8
occurrence nằm trong `attributes.key_facts[]` (list) chưa bao giờ bị đếm. Nội
dung của chúng gọi Bến Tre / Trà Vinh như tỉnh đang tồn tại — trái CLAUDE.md
§1.6 — và một câu còn nói ngược sự thật hành chính hiện tại.

Nguyên tắc sửa: GIỮ NGUYÊN mọi số liệu và tên riêng, chỉ đính chính khung hành
chính (thêm "cũ (trước 7-2025)", bỏ cấp huyện đã bãi bỏ). Không thêm dữ kiện
mới — số liệu vốn được thống kê theo đơn vị cũ nên "vùng ... cũ" là cách mô tả
đúng, không phải cách nói tránh.

Chạy:
    python scripts/fix_tinh_cu_nested.py --dry-run
    python scripts/fix_tinh_cu_nested.py
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agent"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
DATA_JSON = ROOT / "web" / "data.json"

# (entity_id, chỉ số trong key_facts, đoạn cũ, đoạn mới)
FIXES: list[tuple[str, int, str, str]] = [
    (
        "buoi-da-xanh", 2,
        "Diện tích trồng toàn tỉnh Bến Tre khoảng 5.904 ha",
        "Diện tích trồng toàn vùng Bến Tre cũ (trước 7-2025) khoảng 5.904 ha",
    ),
    (
        "rung-duoc-long-khanh", 0,
        "tại xã Long Khánh, huyện Duyên Hải, tỉnh Trà Vinh — không thuộc Bến Tre",
        "tại xã Long Khánh, vùng Duyên Hải thuộc Trà Vinh cũ (trước 7-2025)",
    ),
    (
        "chua-co-chua-nodol-chua-phno-don", 1,
        "Sân chim lớn nhất tỉnh Trà Vinh",
        "Sân chim lớn nhất vùng Trà Vinh cũ (trước 7-2025)",
    ),
    (
        "muoi-ba-tri", 1,
        "Ba Tri có diện tích làm muối lớn nhất tỉnh Bến Tre",
        "Ba Tri có diện tích làm muối lớn nhất vùng Bến Tre cũ (trước 7-2025)",
    ),
    (
        "thien-vien-truc-lam-tra-vinh", 1,
        "Thiền phái Trúc Lâm duy nhất tại tỉnh Trà Vinh",
        "Thiền phái Trúc Lâm duy nhất tại vùng Trà Vinh cũ (trước 7-2025)",
    ),
    (
        "cu-lao-dai-vung-liem", 1,
        "huyện Vũng Liêm, cách TP. Vĩnh Long hơn 30 km, tiếp giáp tỉnh Bến Tre và Trà Vinh",
        "Vũng Liêm, cách trung tâm Vĩnh Long hơn 30 km, tiếp giáp vùng Bến Tre và Trà Vinh cũ",
    ),
    (
        "keo-dua-mo-cay-dish", 3,
        "Hiện tỉnh Bến Tre có hơn 180 cơ sở sản xuất kẹo dừa, tập trung ở huyện Mỏ Cày Nam, "
        "Mỏ Cày Bắc, Châu Thành và TP Bến Tre",
        "Vùng Bến Tre cũ (trước 7-2025) có hơn 180 cơ sở sản xuất kẹo dừa, tập trung ở "
        "Mỏ Cày Nam, Mỏ Cày Bắc, Châu Thành và khu vực thành phố Bến Tre cũ",
    ),
    (
        # Câu gốc nói ngược sự thật hiện tại: sau sáp nhập 7-2025, Cồn Quy THUỘC
        # tỉnh Vĩnh Long. Giữ ý phân biệt địa lý ban đầu nhưng đặt lại cho đúng.
        "con-quy", 2,
        "Lưu ý: Cồn Quy thuộc tỉnh Bến Tre, không phải Vĩnh Long",
        "Cồn Quy nằm bên phía Bến Tre cũ (trước 7-2025), nay cùng thuộc tỉnh Vĩnh Long",
    ),
]


def _patch_key_facts(entity: dict, index: int, old: str, new: str) -> str | None:
    """Trả trạng thái: 'fixed' | 'already' | None (không khớp)."""
    facts = (entity.get("attributes") or {}).get("key_facts")
    if not isinstance(facts, list) or index >= len(facts):
        return None
    text = facts[index]
    if not isinstance(text, str):
        return None
    if new in text:
        return "already"
    if old not in text:
        return None
    facts[index] = text.replace(old, new)
    return "fixed"


def _apply_to_db(dry_run: bool) -> tuple[int, list[str]]:
    from database import db

    changed, notes = 0, []
    by_id = {e["id"]: e for e in db.all_entities()}
    for eid, index, old, new in FIXES:
        entity = by_id.get(eid)
        if entity is None:
            notes.append(f"  [BỎ QUA] {eid} — không có trong DB")
            continue
        state = _patch_key_facts(entity, index, old, new)
        if state == "already":
            notes.append(f"  [ĐÃ SỬA] {eid}")
        elif state == "fixed":
            changed += 1
            notes.append(f"  [{'DRY' if dry_run else 'GHI'}] {eid}")
            if not dry_run:
                db.upsert_entity(entity)
        else:
            notes.append(f"  [KHÔNG KHỚP] {eid}:key_facts[{index}] — kiểm lại bằng tay")
    return changed, notes


def _apply_to_data_json(dry_run: bool) -> tuple[int, list[str]]:
    if not DATA_JSON.exists():
        return 0, ["  [BỎ QUA] web/data.json không tồn tại"]
    data = json.loads(DATA_JSON.read_text(encoding="utf-8"))
    by_id = {e["id"]: e for e in data.get("entities", [])}
    changed, notes = 0, []
    for eid, index, old, new in FIXES:
        entity = by_id.get(eid)
        if entity is None:
            notes.append(f"  [BỎ QUA] {eid} — không có trong data.json")
            continue
        state = _patch_key_facts(entity, index, old, new)
        if state == "fixed":
            changed += 1
        elif state is None:
            notes.append(f"  [KHÔNG KHỚP] {eid}:key_facts[{index}]")
    if changed and not dry_run:
        # data.json là MỘT dòng compact, không newline cuối. Đã kiểm round-trip
        # `json.dumps(..., ensure_ascii=False)` cho ra byte y hệt bản gốc, nên
        # diff chỉ gồm đúng phần chữ được sửa. Ghi kiểu indent sẽ tạo diff 4.2 MB.
        DATA_JSON.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return changed, notes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-db", action="store_true",
                    help="chỉ sửa web/data.json (khi DB không mở được)")
    args = ap.parse_args()

    print(f"=== data.json ({'thử' if args.dry_run else 'ghi'}) ===")
    json_changed, json_notes = _apply_to_data_json(args.dry_run)
    for note in json_notes:
        print(note)
    print(f"  {json_changed} bản ghi")

    db_changed = 0
    if not args.skip_db:
        print(f"=== DB ({'thử' if args.dry_run else 'ghi'}) ===")
        db_changed, db_notes = _apply_to_db(args.dry_run)
        for note in db_notes:
            print(note)
        print(f"  {db_changed} bản ghi")

    print(f"\nTổng: data.json {json_changed} · DB {db_changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
