#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SP2 reconcile — hợp nhất 3 kho (plan docs/superpowers/plans/2026-07-07-sp2-data.md).

Các bước (mặc định DRY-RUN — thêm --execute để ghi thật; R70.5):
  local-fix   : áp FIX đã verify (review-54) vào local SQLite
  local-clean : xoá khỏi local các id rác kỹ thuật/ngoài-địa-bàn (quyết định chủ 2026-07-07)
  prod        : (chạy TRÊN VPS) DELETE 3 entity ngoài tỉnh + relationships; áp 8 patch itinerary;
                INSERT danh sách push (39 entity từ file push_payload.json)
  Sau đó export prod → data.json + đồng bộ text local (bước riêng ngoài script này).

An toàn: mọi bước in báo cáo; prod yêu cầu pg_dump tồn tại cùng ngày (kiểm tên file backups/pre_sp2_*).
"""
from __future__ import annotations

import argparse
import json
import io
import os
import sqlite3
import sys
from datetime import date

TODAY = date.today().isoformat()


def apply_local_fixes(db_path: str, final_path: str, execute: bool) -> None:
    final = json.load(io.open(final_path, encoding="utf-8"))
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    applied = 0
    for eid, r in final.items():
        if r["action"] != "FIX":
            continue
        row = conn.execute("SELECT attributes, coordinates FROM entities WHERE id=?", (eid,)).fetchone()
        if row is None:
            print(f"  SKIP {eid}: không có trong local")
            continue
        for f in r["fixes"]:
            field, new = f["field"], f["new_value"]
            if field.startswith("attributes."):  # normalize dạng agent trả
                field = "attr:" + field[len("attributes."):]
            if field == "attributes":  # nguyên cột → MERGE vào attrs cũ (không drop tail)
                attrs = json.loads(row["attributes"] or "{}")
                attrs.update(json.loads(new))
                if execute:
                    conn.execute("UPDATE entities SET attributes=?, updatedAt=? WHERE id=?",
                                 (json.dumps(attrs, ensure_ascii=False), TODAY, eid))
                applied += 1
                continue
            if field == "coordinates":
                val = None if new in ("null", "None", "") else new
                if execute:
                    conn.execute("UPDATE entities SET coordinates=?, updatedAt=? WHERE id=?", (val, TODAY, eid))
            elif field.startswith("attr:"):
                attrs = json.loads(row["attributes"] or "{}")
                attrs[field[5:]] = new
                if execute:
                    conn.execute("UPDATE entities SET attributes=?, updatedAt=? WHERE id=?",
                                 (json.dumps(attrs, ensure_ascii=False), TODAY, eid))
            else:
                if execute:
                    conn.execute(f"UPDATE entities SET {field}=?, updatedAt=? WHERE id=?", (new, TODAY, eid))
            applied += 1
    if execute:
        conn.commit()
    print(f"local-fix: {applied} field {'ĐÃ GHI' if execute else '(dry-run)'}")


def clean_local(db_path: str, ids: list[str], execute: bool) -> None:
    conn = sqlite3.connect(db_path)
    for eid in ids:
        n = conn.execute("SELECT COUNT(*) FROM entities WHERE id=?", (eid,)).fetchone()[0]
        print(f"  local-clean {eid}: {'có' if n else 'KHÔNG có'}")
        if execute and n:
            conn.execute("DELETE FROM entities WHERE id=?", (eid,))
            conn.execute("DELETE FROM relationships WHERE \"from\"=? OR \"to\"=?", (eid, eid))
    if execute:
        conn.commit()
    print(f"local-clean: {len(ids)} id {'ĐÃ XOÁ' if execute else '(dry-run)'}")


def build_push_payload(db_path: str, final_path: str, out_path: str) -> None:
    """Xuất 39 entity (PUSH + FIX-đã-áp) từ local ra JSON để chở lên VPS."""
    final = json.load(io.open(final_path, encoding="utf-8"))
    ids = [i for i, r in final.items() if r["action"] in ("PUSH", "FIX")]
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = []
    for eid in ids:
        r = conn.execute("SELECT * FROM entities WHERE id=?", (eid,)).fetchone()
        if r:
            rows.append(dict(r))
    io.open(out_path, "w", encoding="utf-8").write(json.dumps(rows, ensure_ascii=False))
    print(f"push_payload: {len(rows)} entity → {out_path}")


def apply_prod(changes_path: str, payload_path: str, execute: bool) -> None:
    """Chạy TRÊN VPS: DELETE + itinerary patches + INSERT payload."""
    import psycopg2
    ch = json.load(io.open(changes_path, encoding="utf-8"))
    payload = json.load(io.open(payload_path, encoding="utf-8"))
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    # 1) DELETE
    for eid in ch["delete_ids"]:
        cur.execute("SELECT COUNT(*) FROM entities WHERE id=%s", (eid,))
        print(f"  DELETE {eid}: {'có' if cur.fetchone()[0] else 'KHÔNG'}")
        if execute:
            # PG dùng from_id/to_id (khác data.json from/to)
            cur.execute("DELETE FROM relationships WHERE from_id=%s OR to_id=%s", (eid, eid))
            cur.execute("DELETE FROM entities WHERE id=%s", (eid,))
    # 2) itinerary patches (match old_value)
    ok = skip = 0
    for p in ch["patches"]:
        field = p["field"]
        if field.startswith("attr:"):
            cur.execute("SELECT attributes::text FROM entities WHERE id=%s", (p["entity_id"],))
            row = cur.fetchone()
            attrs = json.loads(row[0]) if row and row[0] else {}
            if attrs.get(field[5:]) != p["old_value"]:
                skip += 1; print(f"  PATCH-SKIP {p['entity_id']}:{field}"); continue
            attrs[field[5:]] = p["new_value"]
            if execute:
                cur.execute('UPDATE entities SET attributes=%s::jsonb, "updatedAt"=%s WHERE id=%s',
                            (json.dumps(attrs, ensure_ascii=False), TODAY, p["entity_id"]))
        else:
            cur.execute(f"SELECT {field} FROM entities WHERE id=%s", (p["entity_id"],))
            row = cur.fetchone()
            if not row or row[0] != p["old_value"]:
                skip += 1; print(f"  PATCH-SKIP {p['entity_id']}:{field}"); continue
            if execute:
                cur.execute(f'UPDATE entities SET {field}=%s, "updatedAt"=%s WHERE id=%s',
                            (p["new_value"], TODAY, p["entity_id"]))
        ok += 1
    print(f"  patches: {ok} áp, {skip} skip")
    # 3) INSERT payload — theo cột giao nhau giữa payload và bảng prod
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='entities'")
    prod_cols = {r[0] for r in cur.fetchall()}
    inserted = existed = 0
    for e in payload:
        cur.execute("SELECT COUNT(*) FROM entities WHERE id=%s", (e["id"],))
        if cur.fetchone()[0]:
            existed += 1
            continue
        cols = [c for c in e.keys() if c in prod_cols and e[c] is not None]
        vals = [e[c] for c in cols]
        if execute:
            ph = ", ".join(["%s"] * len(cols))
            col_sql = ", ".join(f'"{c}"' for c in cols)
            cur.execute(f"INSERT INTO entities ({col_sql}) VALUES ({ph})", vals)
        inserted += 1
    print(f"  INSERT: {inserted} mới, {existed} đã tồn tại")
    if execute:
        conn.commit()
        print("PROD: ĐÃ GHI.")
    else:
        conn.rollback()
        print("PROD: dry-run (rollback).")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["local-fix", "local-clean", "push-payload", "prod"])
    ap.add_argument("--db", default="agent/data/vinhlong360.db")
    ap.add_argument("--final", default="")
    ap.add_argument("--changes", default="")
    ap.add_argument("--payload", default="")
    ap.add_argument("--ids", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--execute", action="store_true")
    a = ap.parse_args()
    if a.step == "local-fix":
        apply_local_fixes(a.db, a.final, a.execute)
    elif a.step == "local-clean":
        clean_local(a.db, [x for x in a.ids.split(",") if x], a.execute)
    elif a.step == "push-payload":
        build_push_payload(a.db, a.final, a.out)
    elif a.step == "prod":
        apply_prod(a.changes, a.payload, a.execute)
    return 0


if __name__ == "__main__":
    sys.exit(main())
