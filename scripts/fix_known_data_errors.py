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

        if new == description:
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
