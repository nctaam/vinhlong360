#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SP6 T2: điền trường bắt buộc per-type còn thiếu (R10.3b 49 → 0).

Hai pha (R70.5 — mọi apply có dry-run):
  propose  : suy giá trị từ dữ liệu SẴN CÓ (name/description) theo luật có
             ngữ cảnh + thứ tự ưu tiên chống bẫy (ATM-tại-bệnh-viện → ngân
             hàng, KHÔNG y_te; 'mộc mạc'/'trường hợp'/'quảng trường' không
             phải nghề) → in bảng + ghi fixes JSON.
  apply    : đọc fixes JSON, áp vào 1 kho (--store data|sqlite|pg); CHỈ set
             key còn thiếu, không ghi đè giá trị đã có.

Dùng:
  python scripts/sp6_fill_required.py propose --data web/data.json --out <fixes.json>
  python scripts/sp6_fill_required.py apply --fixes <fixes.json> --store data --data web/data.json
  python scripts/sp6_fill_required.py apply --fixes <fixes.json> --store sqlite --db agent/data/vinhlong360.db
  DATABASE_URL=... python scripts/sp6_fill_required.py apply --fixes <fixes.json> --store pg
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "agent"))

TODAY = date.today().isoformat()

# (office_kind, [pattern]) — thứ tự = ưu tiên; match trên name thường-hoá.
OFFICE_RULES = [
    ("ngan_hang", [r"\batm\b", "ngân hàng", "vietcombank", "agribank", "bidv",
                   "vietinbank", "sacombank", "kienlongbank", "dongabank"]),
    ("giao_thong", ["bến xe", "bến phà", "bến tàu", "xe buýt", "trạm xe", "bến đò"]),
    ("vien_thong", ["viettel", "vinaphone", "vnpt", "mobifone", "fpt telecom", "điểm giao dịch"]),
    ("cua_hang", ["vinmart", "winmart", "bách hoá xanh", "bách hóa xanh", "cửa hàng tiện lợi", "siêu thị"]),
    ("y_te", ["bệnh viện", "nhà thuốc", "trạm y tế", "phòng khám"]),
]

# Nghề craft_village nhận từ name/description — (cụm khớp, giá trị specialty).
# Cụm ĐẦY ĐỦ, không từ đơn dễ bẫy ('tre' khớp lung tung, 'mộc' khớp 'mộc mạc').
CRAFT_PATTERNS = [
    ("dệt chiếu", "dệt chiếu"), ("gạch gốm", "gạch gốm"), ("gạch ngói", "gạch ngói"),
    ("làm gốm", "gốm"), ("đan lục bình", "đan lục bình"), ("đan lát", "đan lát"),
    ("bánh tráng", "bánh tráng"), ("bánh phồng", "bánh phồng"), ("kẹo dừa", "kẹo dừa"),
    ("mật hoa dừa", "mật hoa dừa"), ("ca cao", "ca cao"), ("hoa kiểng", "hoa kiểng"),
    ("cây giống", "cây giống"), ("chằm nón", "chằm nón"), ("đan nón lá", "đan nón lá"),
    ("đúc lư đồng", "đúc lư đồng"), ("làm muối", "muối"), ("khô cá", "khô cá"),
    ("tép khô", "tép khô"), ("tôm khô", "tôm khô"), ("mỹ nghệ dừa", "thủ công mỹ nghệ dừa"),
    ("chỉ xơ dừa", "chỉ xơ dừa"), ("đan đát", "đan đát"), ("lò cốm", "cốm"),
    ("đóng thuyền", "đóng thuyền"), ("cam sành", "cam sành"), ("mai vàng", "mai vàng"),
    ("công nghiệp tre", "tiểu thủ công nghiệp tre"),
]


def _norm(s: str) -> str:
    return (s or "").lower()


def _match_office(name: str) -> str:
    for k, pats in OFFICE_RULES:
        if any(re.search(p, name) if "\\" in p else p in name for p in pats):
            return k
    return "khac"  # wifi công cộng, ca lạ → khac (vẫn ghi căn cứ)


def _match_craft(name: str, desc: str):
    hit = next(((p, v) for p, v in CRAFT_PATTERNS if p in name), None) or \
          next(((p, v) for p, v in CRAFT_PATTERNS if p in desc), None)
    if not hit:
        return None
    where = "name" if hit[0] in name else "description"
    return hit[1], f"khớp cụm '{hit[0]}' trong {where}"


def _propose_one(e: dict) -> tuple[dict | None, str | None]:
    """Trả (fix, unresolved-note). Chỉ 1 trong 2 khác None."""
    name, desc, etype = _norm(e.get("name")), _norm(e.get("description")), e.get("type")
    if etype == "facility":
        return {"id": e["id"], "field": "attr:office_kind", "value": _match_office(name),
                "basis": f"name='{e.get('name')}'"}, None
    if etype == "craft_village":
        m = _match_craft(name, desc)
        if m:
            return {"id": e["id"], "field": "attr:specialty", "value": m[0], "basis": m[1]}, None
        return None, e["id"]
    return None, f"{e['id']} ({etype})"


def propose(data_path: str, out_path: str) -> int:
    from entity_schemas import validate_attributes

    d = json.load(io.open(data_path, encoding="utf-8"))
    fixes, unresolved = [], []
    for e in d["entities"]:
        _, warns = validate_attributes(e.get("type") or "", e.get("attributes") or {})
        if not any("bắt buộc" in w for w in warns):
            continue
        fix, note = _propose_one(e)
        (fixes.append(fix) if fix else unresolved.append(note))
    for f in fixes:
        print(f"  {f['id']:<58} {f['field']:<22} = {f['value']:<14} | {f['basis'][:70]}")
    print(f"\npropose: {len(fixes)} fix | unresolved: {len(unresolved)} {unresolved[:5]}")
    io.open(out_path, "w", encoding="utf-8").write(json.dumps(fixes, ensure_ascii=False, indent=1))
    return 0 if not unresolved else 1


def _set_attr(attrs: dict, field: str, value: str) -> bool:
    """Set attr nếu CHƯA có (không ghi đè). Trả True nếu đã set."""
    key = field[5:]
    if attrs.get(key):
        return False
    attrs[key] = value
    return True


def _apply_data(fixes: list, data_path: str, execute: bool) -> tuple[int, int]:
    d = json.load(io.open(data_path, encoding="utf-8"))
    idx = {e["id"]: e for e in d["entities"]}
    ok = skip = 0
    for f in fixes:
        e = idx.get(f["id"])
        if e is None:
            skip += 1; continue
        if _set_attr(e.setdefault("attributes", {}), f["field"], f["value"]):
            ok += 1
    if execute:
        tmp = data_path + ".tmp"
        io.open(tmp, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False))
        os.replace(tmp, data_path)
    return ok, skip


def _apply_sqlite(fixes: list, db_path: str, execute: bool) -> tuple[int, int]:
    import sqlite3
    conn = sqlite3.connect(db_path); conn.row_factory = sqlite3.Row
    ok = skip = 0
    for f in fixes:
        row = conn.execute("SELECT attributes FROM entities WHERE id=?", (f["id"],)).fetchone()
        if row is None:
            skip += 1; continue
        attrs = json.loads(row["attributes"] or "{}")
        if _set_attr(attrs, f["field"], f["value"]):
            ok += 1
            if execute:
                conn.execute("UPDATE entities SET attributes=?, updatedAt=? WHERE id=?",
                             (json.dumps(attrs, ensure_ascii=False), TODAY, f["id"]))
    if execute:
        conn.commit()
    return ok, skip


def _apply_pg(fixes: list, execute: bool) -> tuple[int, int]:
    import psycopg2
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    ok = skip = 0
    for f in fixes:
        cur.execute("SELECT attributes::text FROM entities WHERE id=%s", (f["id"],))
        row = cur.fetchone()
        if row is None:
            skip += 1; continue
        attrs = json.loads(row[0]) if row[0] else {}
        if _set_attr(attrs, f["field"], f["value"]):
            ok += 1
            if execute:
                cur.execute('UPDATE entities SET attributes=%s::jsonb, "updatedAt"=%s WHERE id=%s',
                            (json.dumps(attrs, ensure_ascii=False), TODAY, f["id"]))
    conn.commit() if execute else conn.rollback()
    return ok, skip


def apply(fixes_path: str, store: str, data_path: str = "", db_path: str = "", execute: bool = False) -> None:
    fixes = json.load(io.open(fixes_path, encoding="utf-8"))
    if store == "data":
        ok, skip = _apply_data(fixes, data_path, execute)
    elif store == "sqlite":
        ok, skip = _apply_sqlite(fixes, db_path, execute)
    else:
        ok, skip = _apply_pg(fixes, execute)
    print(f"{store}: {ok} áp, {skip} skip {'ĐÃ GHI' if execute else '(dry-run)'}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["propose", "apply"])
    ap.add_argument("--data", default="web/data.json")
    ap.add_argument("--db", default="agent/data/vinhlong360.db")
    ap.add_argument("--fixes", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--store", choices=["data", "sqlite", "pg"], default="data")
    ap.add_argument("--execute", action="store_true")
    a = ap.parse_args()
    if a.mode == "propose":
        return propose(a.data, a.out)
    apply(a.fixes, a.store, data_path=a.data, db_path=a.db, execute=a.execute)
    return 0


if __name__ == "__main__":
    sys.exit(main())
