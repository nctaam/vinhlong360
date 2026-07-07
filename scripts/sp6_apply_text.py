#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SP6: áp summary/description viết lại vào 1 kho. Dry-run mặc định (R70.5).

Payload JSON: [{id, summary, description}]. CHỈ cập nhật entity có id khớp;
bỏ qua nếu text mới rỗng (an toàn). updatedAt = hôm nay.

  python scripts/sp6_apply_text.py --payload <f.json> --store data [--execute]
  python scripts/sp6_apply_text.py --payload <f.json> --store sqlite [--execute]
  DATABASE_URL=... python scripts/sp6_apply_text.py --payload <f.json> --store pg [--execute]
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
from datetime import date

TODAY = date.today().isoformat()


def _valid(p: dict) -> bool:
    return bool(p.get("id") and (p.get("summary") or "").strip() and (p.get("description") or "").strip())


def apply_data(payload: list, data_path: str, execute: bool) -> None:
    d = json.load(io.open(data_path, encoding="utf-8"))
    idx = {e["id"]: e for e in d["entities"]}
    ok = skip = 0
    for p in payload:
        e = idx.get(p["id"])
        if e is None or not _valid(p):
            skip += 1; continue
        e["summary"] = p["summary"].strip()
        e["description"] = p["description"].strip()
        e["updatedAt"] = TODAY
        ok += 1
    if execute:
        tmp = data_path + ".tmp"
        io.open(tmp, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False))
        os.replace(tmp, data_path)
    print(f"  data: {ok} áp, {skip} skip {'ĐÃ GHI' if execute else '(dry-run)'}")


def apply_sqlite(payload: list, db_path: str, execute: bool) -> None:
    import sqlite3
    conn = sqlite3.connect(db_path)
    ok = skip = 0
    for p in payload:
        if not _valid(p):
            skip += 1; continue
        n = conn.execute("SELECT COUNT(*) FROM entities WHERE id=?", (p["id"],)).fetchone()[0]
        if not n:
            skip += 1; continue
        if execute:
            conn.execute("UPDATE entities SET summary=?, description=?, updatedAt=? WHERE id=?",
                         (p["summary"].strip(), p["description"].strip(), TODAY, p["id"]))
        ok += 1
    if execute:
        conn.commit()
    print(f"  sqlite: {ok} áp, {skip} skip {'ĐÃ GHI' if execute else '(dry-run)'}")


def apply_pg(payload: list, execute: bool) -> None:
    import psycopg2
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    ok = skip = 0
    for p in payload:
        if not _valid(p):
            skip += 1; continue
        cur.execute("SELECT COUNT(*) FROM entities WHERE id=%s", (p["id"],))
        if not cur.fetchone()[0]:
            skip += 1; continue
        if execute:
            cur.execute('UPDATE entities SET summary=%s, description=%s, "updatedAt"=%s WHERE id=%s',
                        (p["summary"].strip(), p["description"].strip(), TODAY, p["id"]))
        ok += 1
    conn.commit() if execute else conn.rollback()
    print(f"  pg: {ok} áp, {skip} skip {'ĐÃ GHI' if execute else '(dry-run)'}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--payload", required=True)
    ap.add_argument("--store", choices=["data", "sqlite", "pg"], required=True)
    ap.add_argument("--data", default="web/data.json")
    ap.add_argument("--db", default="agent/data/vinhlong360.db")
    ap.add_argument("--execute", action="store_true")
    a = ap.parse_args()
    payload = json.load(io.open(a.payload, encoding="utf-8"))
    print(f"{len(payload)} entity, store={a.store}:")
    if a.store == "data":
        apply_data(payload, a.data, a.execute)
    elif a.store == "sqlite":
        apply_sqlite(payload, a.db, a.execute)
    else:
        apply_pg(payload, a.execute)
    return 0


if __name__ == "__main__":
    sys.exit(main())
