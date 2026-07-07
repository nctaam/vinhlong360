#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SP6 T3: thêm nguồn kiểm chứng (URL ngoài) vào entity.source — 3 kho.

CHỈ THÊM, không ghi đè/xoá nguồn cũ; bỏ qua nếu url đã có trong source.
Additions JSON: [{id, url, title, basis}] (đã qua verify workflow).

  python scripts/sp6_add_sources.py --additions <f.json> --store data [--execute]
  python scripts/sp6_add_sources.py --additions <f.json> --store sqlite [--execute]
  DATABASE_URL=... python scripts/sp6_add_sources.py --additions <f.json> --store pg [--execute]
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
from datetime import date

TODAY = date.today().isoformat()


def _merge(source, adds: list[dict]) -> tuple[list, int]:
    """Trả (source mới, số mục thêm). source có thể là list/None."""
    out = list(source) if isinstance(source, list) else []
    have = {s.get("url") for s in out if isinstance(s, dict) and s.get("url")}
    n = 0
    for a in adds:
        if a["url"] in have:
            continue
        out.append({"title": a["title"], "url": a["url"], "added": TODAY, "via": "sp6-corpus-map"})
        have.add(a["url"])
        n += 1
    return out, n


def _loads(raw) -> list:
    try:
        return json.loads(raw) if raw else []
    except (json.JSONDecodeError, TypeError):
        return []


def _run_data(by_id: dict, data_path: str, execute: bool) -> tuple[int, int, int]:
    d = json.load(io.open(data_path, encoding="utf-8"))
    ok = ent = 0
    for e in d["entities"]:
        if e["id"] not in by_id:
            continue
        merged, n = _merge(e.get("source"), by_id[e["id"]])
        if n:
            e["source"] = merged
            ok += n; ent += 1
    skip = len(set(by_id) - {e["id"] for e in d["entities"]})
    if execute:
        tmp = data_path + ".tmp"
        io.open(tmp, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False))
        os.replace(tmp, data_path)
    return ok, ent, skip


def _run_sqlite(by_id: dict, db_path: str, execute: bool) -> tuple[int, int, int]:
    import sqlite3
    conn = sqlite3.connect(db_path); conn.row_factory = sqlite3.Row
    ok = ent = skip = 0
    for eid, items in by_id.items():
        row = conn.execute("SELECT source FROM entities WHERE id=?", (eid,)).fetchone()
        if row is None:
            skip += 1; continue
        merged, n = _merge(_loads(row["source"]), items)
        if n:
            ok += n; ent += 1
            if execute:
                conn.execute("UPDATE entities SET source=?, updatedAt=? WHERE id=?",
                             (json.dumps(merged, ensure_ascii=False), TODAY, eid))
    if execute:
        conn.commit()
    return ok, ent, skip


def _run_pg(by_id: dict, execute: bool) -> tuple[int, int, int]:
    import psycopg2
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    ok = ent = skip = 0
    for eid, items in by_id.items():
        cur.execute("SELECT source::text FROM entities WHERE id=%s", (eid,))
        row = cur.fetchone()
        if row is None:
            skip += 1; continue
        merged, n = _merge(_loads(row[0]), items)
        if n:
            ok += n; ent += 1
            if execute:
                cur.execute('UPDATE entities SET source=%s::jsonb, "updatedAt"=%s WHERE id=%s',
                            (json.dumps(merged, ensure_ascii=False), TODAY, eid))
    conn.commit() if execute else conn.rollback()
    return ok, ent, skip


def run(additions_path: str, store: str, data_path: str, db_path: str, execute: bool) -> None:
    adds = json.load(io.open(additions_path, encoding="utf-8"))
    by_id: dict[str, list] = {}
    for a in adds:
        by_id.setdefault(a["id"], []).append(a)
    if store == "data":
        ok, ent, skip = _run_data(by_id, data_path, execute)
    elif store == "sqlite":
        ok, ent, skip = _run_sqlite(by_id, db_path, execute)
    else:
        ok, ent, skip = _run_pg(by_id, execute)
    print(f"{store}: +{ok} nguồn trên {ent} entity, {skip} id không thấy {'ĐÃ GHI' if execute else '(dry-run)'}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--additions", required=True)
    ap.add_argument("--store", choices=["data", "sqlite", "pg"], required=True)
    ap.add_argument("--data", default="web/data.json")
    ap.add_argument("--db", default="agent/data/vinhlong360.db")
    ap.add_argument("--execute", action="store_true")
    a = ap.parse_args()
    run(a.additions, a.store, a.data, a.db, a.execute)
    return 0


if __name__ == "__main__":
    sys.exit(main())
