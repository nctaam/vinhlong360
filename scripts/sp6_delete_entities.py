#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SP6: xoá entity (+ relationships dính) khỏi 1 kho. Dry-run mặc định (R70.5).

Danh sách id đọc từ file (1 id/dòng, bỏ dòng trống/#).
  python scripts/sp6_delete_entities.py --ids <f.txt> --store data [--execute]
  python scripts/sp6_delete_entities.py --ids <f.txt> --store sqlite [--execute]
  DATABASE_URL=... python scripts/sp6_delete_entities.py --ids <f.txt> --store pg [--execute]
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys


def load_ids(path: str) -> list[str]:
    out = []
    for ln in io.open(path, encoding="utf-8").read().splitlines():
        s = ln.strip()
        if s and not s.startswith("#"):
            out.append(s)
    return out


def del_data(ids: list[str], data_path: str, execute: bool) -> None:
    d = json.load(io.open(data_path, encoding="utf-8"))
    idset = set(ids)
    e0, r0 = len(d["entities"]), len(d["relationships"])
    present = [e["id"] for e in d["entities"] if e["id"] in idset]
    d["entities"] = [e for e in d["entities"] if e["id"] not in idset]
    d["relationships"] = [r for r in d["relationships"]
                          if r.get("from") not in idset and r.get("to") not in idset]
    print(f"  data: entity {e0}->{len(d['entities'])} ({len(present)} xoá), rels {r0}->{len(d['relationships'])}")
    missing = idset - set(present)
    if missing:
        print(f"  KHÔNG thấy trong data.json: {sorted(missing)}")
    if execute:
        tmp = data_path + ".tmp"
        io.open(tmp, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False))
        os.replace(tmp, data_path)


def del_sqlite(ids: list[str], db_path: str, execute: bool) -> None:
    import sqlite3
    conn = sqlite3.connect(db_path)
    fts = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%fts%'")]
    # local SQLite relationships dùng cột from_id/to_id (giống prod PG)
    ecnt = rcnt = 0
    for eid in ids:
        n = conn.execute("SELECT COUNT(*) FROM entities WHERE id=?", (eid,)).fetchone()[0]
        r = conn.execute("SELECT COUNT(*) FROM relationships WHERE from_id=? OR to_id=?", (eid, eid)).fetchone()[0]
        ecnt += n; rcnt += r
        if execute and n:
            conn.execute("DELETE FROM entities WHERE id=?", (eid,))
            conn.execute("DELETE FROM relationships WHERE from_id=? OR to_id=?", (eid, eid))
            for t in fts:
                try:
                    conn.execute(f"DELETE FROM {t} WHERE id=?", (eid,))
                except sqlite3.OperationalError:
                    pass
    if execute:
        conn.commit()
    print(f"  sqlite: {ecnt} entity, {rcnt} rels {'ĐÃ XOÁ' if execute else '(dry-run)'}")


def del_pg(ids: list[str], execute: bool) -> None:
    import psycopg2
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    ecnt = rcnt = 0
    for eid in ids:
        cur.execute("SELECT COUNT(*) FROM entities WHERE id=%s", (eid,))
        n = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM relationships WHERE from_id=%s OR to_id=%s", (eid, eid))
        r = cur.fetchone()[0]
        ecnt += n; rcnt += r
        if execute and n:
            cur.execute("DELETE FROM relationships WHERE from_id=%s OR to_id=%s", (eid, eid))
            cur.execute("DELETE FROM entities WHERE id=%s", (eid,))
    conn.commit() if execute else conn.rollback()
    print(f"  pg: {ecnt} entity, {rcnt} rels {'ĐÃ XOÁ' if execute else '(dry-run rollback)'}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", required=True)
    ap.add_argument("--store", choices=["data", "sqlite", "pg"], required=True)
    ap.add_argument("--data", default="web/data.json")
    ap.add_argument("--db", default="agent/data/vinhlong360.db")
    ap.add_argument("--execute", action="store_true")
    a = ap.parse_args()
    ids = load_ids(a.ids)
    print(f"{len(ids)} id, store={a.store}:")
    if a.store == "data":
        del_data(ids, a.data, a.execute)
    elif a.store == "sqlite":
        del_sqlite(ids, a.db, a.execute)
    else:
        del_pg(ids, a.execute)
    return 0


if __name__ == "__main__":
    sys.exit(main())
