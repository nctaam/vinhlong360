#!/usr/bin/env python3
"""Sửa ba lỗi dữ liệu đã được kiểm chứng chỉ đích danh.

Cả ba đều là sai sự thật chứ không phải vấn đề văn phong, và đều idempotent —
chạy lại không đổi gì thêm.

1. `vinh-long` ghi "124 đơn vị hành chính cấp xã (19 phường, 105 xã)". Tổng 124
   đúng, nhưng phân tách là số TRƯỚC đợt 16 xã lên phường (19 + 16 = 35). Số
   hiện hành: 35 phường, 89 xã.
2. 19 entity ghi điểm đánh giá trên thang sai: "8.9/5", "10.0/5". Điểm lớn hơn
   5 trên thang 5 là bất khả, nguồn là thang 10.
3. `san-chim-chua-phat-lon-tra-vinh` (Sân chim Chùa Phật Lớn, Trà Vinh) mang mô
   tả của Sân chim Vàm Hồ — một địa điểm khác, ở Bến Tre. Bản ghi không có
   address lẫn attributes nào khác, nên chỉ được BỎ phần sai; viết thêm là bịa.

  python scripts/fix_known_data_errors.py --dry-run
  python scripts/fix_known_data_errors.py
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(os.environ.get("VL360_ROOT") or Path(__file__).resolve().parent.parent)
sys.path.insert(0, str(ROOT / "agent"))

WRONG_UNIT_SPLIT = "(19 phường, 105 xã)"
RIGHT_UNIT_SPLIT = "(35 phường, 89 xã)"

RATING_RE = re.compile(r"(\d+[.,]\d+)\s*/\s*5\b")

MISLABELED_SANCTUARY = "san-chim-chua-phat-lon-tra-vinh"
SANCTUARY_TEXT = "Sân chim ở khu vực Chùa Phật Lớn, Trà Vinh."

# Mô tả ghi "OCOP 4 sao", attributes ghi "3 sao". Tra nguồn ngoài không xác nhận
# được con số nào, nên bỏ hẳn số sao thay vì chọn bừa — giữ "OCOP" là phần chắc.
OCOP_STAR_CONFLICT = ("khoai-lang-binh-tan", "Sản phẩm OCOP 4 sao", "Sản phẩm OCOP")

# attributes ghi mùa "tháng 5–8" nhưng mô tả ghi "chỉ rộ sau Tết". Báo Vĩnh Long
# xác nhận thanh trà chín từ trước Tết tới hết tháng 4, chính vụ tháng 2 âm lịch
# — tức mô tả đúng, attributes sai.
SEASON_CONFLICT = ("thanh-tra-binh-minh", "tháng 5–8", "tháng 1–4, chính vụ sau Tết")

# address ghi rõ Sa Đéc, Đồng Tháp nhưng area=ben-tre. Entity nằm NGOÀI tỉnh
# Vĩnh Long mới; giữ hay bỏ là quyết định của chủ dự án, nhưng mô tả không được
# để người đọc tưởng nó ở trong tỉnh.
OUT_OF_PROVINCE = (
    "nha-co-huynh-thuy-le",
    "Ngôi nhà cổ kiến trúc Pháp – Hoa đầu thế kỷ XX",
    "Ngôi nhà cổ ở Sa Đéc, Đồng Tháp — ngoài địa bàn tỉnh Vĩnh Long — kiến trúc Pháp – Hoa đầu thế kỷ XX",
)

# Mô tả bị hỏng mã (mojibake): "?i?m tham quan n?m trong khu v?c bi?n Ba ??ng".
# Đọc ra được nên đây là khôi phục, không phải viết mới.
MOJIBAKE_FIX = (
    "con-cu",
    "Điểm tham quan nằm trong khu vực biển Ba Động, từng được phát triển thành "
    "sân golf trong giai đoạn khai thác du lịch ven biển.",
)


def fix_rating_scale(text: str) -> str:
    """Điểm > 5 mà ghi thang 5 thì thang thật là 10; điểm ≤ 5 giữ nguyên."""
    def repl(match: re.Match) -> str:
        value = float(match.group(1).replace(",", "."))
        return f"{match.group(1)}/10" if value > 5 else match.group(0)
    return RATING_RE.sub(repl, text or "")


def _load_db():
    from database import db
    return db


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    db = _load_db()
    changed = 0

    for entity in db.all_entities():
        description = entity.get("description") or ""
        if not description:
            continue
        eid = entity.get("id")
        new = description

        if eid == "vinh-long" and WRONG_UNIT_SPLIT in new:
            new = new.replace(WRONG_UNIT_SPLIT, RIGHT_UNIT_SPLIT)

        new = fix_rating_scale(new)

        if eid == MISLABELED_SANCTUARY and "Vàm Hồ" in new:
            # Bản ghi không có dữ kiện riêng nào, nên chỉ giữ đúng phần suy ra
            # được từ chính tên entity. Thà ngắn còn hơn mô tả nhầm địa điểm.
            new = SANCTUARY_TEXT

        for target_id, old_text, fixed_text in (OCOP_STAR_CONFLICT, OUT_OF_PROVINCE):
            if eid == target_id and old_text in new:
                new = new.replace(old_text, fixed_text)

        if eid == MOJIBAKE_FIX[0] and "?" in new:
            new = MOJIBAKE_FIX[1]

        attributes_changed = False
        if eid == SEASON_CONFLICT[0]:
            attributes = entity.get("attributes")
            if isinstance(attributes, dict) and attributes.get("season_note") == SEASON_CONFLICT[1]:
                attributes["season_note"] = SEASON_CONFLICT[2]
                attributes_changed = True

        if new == description and not attributes_changed:
            continue
        changed += 1
        print(f"  [{'DRY' if args.dry_run else 'OK'}] {eid}")
        if not args.dry_run:
            entity["description"] = new
            db.upsert_entity(entity)

    print(f"[fix] {'sẽ sửa' if args.dry_run else 'đã sửa'} {changed} bản ghi")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
