#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Đồng bộ `attributes.admin_code` từ web/data.json → DB (nguồn sự thật, CLAUDE.md §1.1).

VÌ SAO CÓ SCRIPT NÀY
--------------------
Mã hành chính 5 chữ số (`Mã PX`, NQ 1687/NQ-UBTVQH15) mới chỉ được ghi vào
`web/data.json`. Nhưng data.json chỉ là bản EXPORT — `scripts/export_data.py`
chạy MỘT CHIỀU DB→data.json, nên lần export kế tiếp sẽ xoá sạch các mã đó.
Script này đẩy giá trị về đúng nguồn sự thật để vòng export không làm mất dữ liệu.

ĐƯỜNG GHI
---------
Dùng `database.db.upsert_entity()` — đường ghi chính thức, KHÔNG phải SQL thô.
Lý do: upsert_entity còn (a) dựng lại FTS5 terms cho hàng vừa ghi, (b) dual-write
bảng CTI `entity_*_details` trong CÙNG transaction (agent/entity_details.py),
(c) chạy chung một chỗ cho cả SQLite lẫn Postgres. SQL `UPDATE` thô sẽ bỏ qua
cả ba và để index/CTI lệch âm thầm.

Entity được ĐỌC TỪ DB rồi chỉ vá đúng một khoá `attributes.admin_code`; mọi field
khác giữ nguyên giá trị DB. KHÔNG lấy nguyên entity trong data.json ghi đè DB —
data.json đã phân kỳ với DB, làm vậy là kéo lùi dữ liệu.

AN TOÀN
-------
- Idempotent: chạy lại lần 2 → 0 dòng thay đổi.
- `--dry-run` (mặc định): chỉ in kế hoạch, KHÔNG ghi. Ghi thật cần `--apply`.
- Từ chối ghi khi `DESTRUCTIVE_OPS_LOCKED=1` (mặc định của agent/config.py).
  Mở khoá hẹp bằng `ALLOW_ADMIN_CODE_SYNC=1` — cố ý KHÔNG bắt phải đặt
  `DESTRUCTIVE_OPS_LOCKED=0`, vì biến đó còn mở khoá `replace_from_json`
  (§B7) trong cùng shell.
- Từ chối ghi khi DB đã có admin_code KHÁC giá trị duyệt (ca xung đột phải do
  người quyết, không để script đè).
- §B1: chạy `python scripts/backup_data.py` TRƯỚC. Script này không tự backup.

DÙNG
----
  python scripts/sync_admin_code_to_db.py --dry-run
  ALLOW_ADMIN_CODE_SYNC=1 python scripts/sync_admin_code_to_db.py --apply
  # prod (chỉ khi chủ dự án duyệt — §4):
  DATABASE_URL=postgresql://... ALLOW_ADMIN_CODE_SYNC=1 \
      python scripts/sync_admin_code_to_db.py --apply
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "agent"))

DEFAULT_DATA_JSON = os.path.join(ROOT, "web", "data.json")
ADMIN_CODE_RE = re.compile(r"^\d{5}$")
WARD_LEVELS = frozenset({"phuong", "xa"})
# Khoá con số: tỉnh Vĩnh Long mới có đúng 124 xã/phường (35 phường + 89 xã).
# Đơn vị cấp tỉnh `vinh-long` KHÔNG mang mã 5 chữ số (mã tỉnh là `86`, 2 chữ số).
EXPECTED_CODED = 124


class SyncRefused(RuntimeError):
    """Điều kiện an toàn không đạt — không ghi gì cả."""


def load_approved_codes(data_json: str) -> dict[str, str]:
    """Đọc {entity_id: admin_code} từ data.json + tự kiểm tính toàn vẹn.

    data.json ở đây là nguồn giá trị ĐÃ DUYỆT (khoá bằng
    tests/test_place_admin_code.py). Script KHÔNG đọc lại file .xls gốc —
    thêm một nguồn thứ ba là thêm một chỗ để lệch.
    """
    with open(data_json, encoding="utf-8") as stream:
        entities = json.load(stream)["entities"]

    codes: dict[str, str] = {}
    seen: dict[str, str] = {}
    for entity in entities:
        attributes = entity.get("attributes")
        if not isinstance(attributes, dict):
            continue
        code = attributes.get("admin_code")
        if code is None:
            continue
        eid = entity["id"]
        if entity.get("type") != "place":
            raise SyncRefused(f"{eid}: admin_code trên type={entity.get('type')!r}, chỉ place mới được mang mã")
        if entity.get("level") not in WARD_LEVELS:
            raise SyncRefused(f"{eid}: level={entity.get('level')!r} không phải cấp xã/phường")
        if not isinstance(code, str) or not ADMIN_CODE_RE.fullmatch(code):
            raise SyncRefused(f"{eid}: admin_code không đúng 5 chữ số: {code!r}")
        if code in seen:
            raise SyncRefused(f"admin_code {code} trùng giữa {seen[code]} và {eid}")
        seen[code] = eid
        codes[eid] = code

    if len(codes) != EXPECTED_CODED:
        raise SyncRefused(
            f"data.json có {len(codes)} place mang admin_code, kỳ vọng {EXPECTED_CODED}. "
            "Nếu số đơn vị hành chính thật sự đổi, cập nhật EXPECTED_CODED + "
            "tests/test_place_admin_code.py trong cùng commit."
        )
    return codes


def build_plan(db, codes: dict[str, str]) -> dict:
    """So từng entity trong DB với giá trị duyệt. KHÔNG ghi gì ở bước này."""
    to_write: list[tuple[dict, str]] = []
    unchanged: list[str] = []
    conflicts: list[tuple[str, str, str]] = []
    missing: list[str] = []

    for eid, code in codes.items():
        entity = db.get_entity(eid)
        if entity is None:
            missing.append(eid)
            continue
        if entity.get("type") != "place" or entity.get("level") not in WARD_LEVELS:
            conflicts.append((eid, f"type={entity.get('type')!r} level={entity.get('level')!r}", code))
            continue
        attributes = entity.get("attributes")
        current = attributes.get("admin_code") if isinstance(attributes, dict) else None
        if current == code:
            unchanged.append(eid)
        elif current is None:
            to_write.append((entity, code))
        else:
            conflicts.append((eid, str(current), code))

    return {"to_write": to_write, "unchanged": unchanged, "conflicts": conflicts, "missing": missing}


def find_stray_codes(db, codes: dict[str, str]) -> list[str]:
    """Entity trong DB mang admin_code mà KHÔNG thuộc danh sách duyệt."""
    stray = []
    for entity in db.all_entities():
        attributes = entity.get("attributes")
        if not isinstance(attributes, dict) or attributes.get("admin_code") is None:
            continue
        if entity["id"] not in codes:
            stray.append(entity["id"])
    return sorted(stray)


def write_locked() -> str | None:
    """Trả lý do bị khoá, hoặc None nếu được phép ghi."""
    if os.environ.get("ALLOW_ADMIN_CODE_SYNC") == "1":
        return None
    if os.environ.get("DESTRUCTIVE_OPS_LOCKED", "1") == "1":
        return (
            "DESTRUCTIVE_OPS_LOCKED=1 (mặc định) — từ chối ghi. "
            "Mở khoá hẹp cho đúng thao tác này: ALLOW_ADMIN_CODE_SYNC=1"
        )
    return None


def apply_plan(db, to_write: list[tuple[dict, str]]) -> int:
    """Ghi qua upsert_entity — chỉ vá attributes.admin_code, giữ nguyên phần còn lại."""
    written = 0
    for entity, code in to_write:
        attributes = entity.get("attributes")
        entity["attributes"] = {**(attributes if isinstance(attributes, dict) else {}), "admin_code": code}
        db.upsert_entity(entity)
        written += 1
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description="Đồng bộ admin_code từ data.json vào DB")
    parser.add_argument("--data-json", default=DEFAULT_DATA_JSON)
    parser.add_argument("--dry-run", action="store_true", help="chỉ in kế hoạch (mặc định khi không có --apply)")
    parser.add_argument("--apply", action="store_true", help="ghi thật vào DB")
    args = parser.parse_args()

    from database import DATABASE_URL, db

    try:
        codes = load_approved_codes(args.data_json)
        plan = build_plan(db, codes)
    except SyncRefused as exc:
        print(f"TỪ CHỐI: {exc}", file=sys.stderr)
        return 2

    target = "postgres" if DATABASE_URL else f"sqlite:{db.db_path}"
    stray = find_stray_codes(db, codes)
    summary = {
        "target": target,
        "approved_in_data_json": len(codes),
        "already_correct_in_db": len(plan["unchanged"]),
        "will_write": len(plan["to_write"]),
        "conflicts": [{"id": i, "db": cur, "approved": new} for i, cur, new in plan["conflicts"]],
        "missing_in_db": plan["missing"],
        "stray_codes_in_db": stray,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=1))

    if plan["missing"]:
        print(f"TỪ CHỐI: {len(plan['missing'])} entity có mã duyệt nhưng không tồn tại trong DB.", file=sys.stderr)
        return 2
    if plan["conflicts"]:
        print(
            f"TỪ CHỐI: {len(plan['conflicts'])} entity đã có admin_code KHÁC trong DB — "
            "người phải quyết, script không đè.",
            file=sys.stderr,
        )
        return 2

    if not args.apply:
        print(f"DRY-RUN: sẽ ghi {len(plan['to_write'])} dòng. Thêm --apply để ghi thật.")
        return 0

    locked = write_locked()
    if locked:
        print(f"TỪ CHỐI: {locked}", file=sys.stderr)
        return 3

    written = apply_plan(db, plan["to_write"])
    print(f"OK: đã ghi {written} dòng vào {target}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
