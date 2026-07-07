#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Campaign tỉnh-mới: sửa CÓ NGỮ CẢNH text "tỉnh Bến Tre/Trà Vinh" (đơn vị đã giải thể 7/2025).

Plan: docs/superpowers/plans/2026-07-07-data-tinh-moi.md. KHÔNG batch-replace mù (bài học DF-02).

Subcommands:
  extract  --in prod_affected.json --out occurrences.json
           Tách per-FIELD record + gán loại theo rule-engine:
             cat1-address  : attr:address → auto-patch (chỉ đổi tên tỉnh)
             cat4-ten-rieng: name / attr:name / attr:organizer → GIỮ (đổi tên cơ quan cần nguồn)
             cat23-context : description/summary/attr khác → cần phân loại ngữ cảnh (agent)
  apply    --patches patches.json (--json PATH | --sqlite PATH | --pg) [--dry-run]
           Áp patch match-old-value-thì-mới-ghi (an toàn cho kho phân kỳ); bump updatedAt.
           --pg đọc DATABASE_URL (chạy trên VPS). Standalone: stdlib + psycopg2 (chỉ khi --pg).
  verify   (--json PATH | --sqlite PATH | --pg)
           Đếm occurrence còn lại theo field-group.

An toàn: apply mặc định --dry-run=False phải đi sau backup (B1); mọi lệnh in báo cáo applied/skipped.
"""
import argparse
import json
import io
import os
import re
import sys
from datetime import date

PAT = re.compile(r"tỉnh (Bến Tre|Trà Vinh)")
NAME_FIELDS = {"name", "attr:name", "attr:organizer"}
TODAY = date.today().isoformat()


# ---------------- extract ----------------

def iter_fields(e: dict):
    for f in ("name", "description", "summary"):
        v = e.get(f)
        if isinstance(v, str) and PAT.search(v):
            yield f, v
    attrs = e.get("attributes")
    if isinstance(attrs, str):
        try:
            attrs = json.loads(attrs)
        except json.JSONDecodeError:
            attrs = None
    if isinstance(attrs, dict):
        for k, v in attrs.items():
            if isinstance(v, str) and PAT.search(v):
                yield f"attr:{k}", v


def classify(field: str) -> str:
    if field in NAME_FIELDS:
        return "cat4-ten-rieng"
    if field == "attr:address":
        return "cat1-address"
    return "cat23-context"


def cmd_extract(args) -> int:
    ents = json.load(io.open(args.infile, encoding="utf-8-sig"))
    records = []
    for e in ents:
        for field, value in iter_fields(e):
            records.append({
                "entity_id": e["id"],
                "entity_name": e.get("name"),
                "field": field,
                "category": classify(field),
                "match_count": len(PAT.findall(value)),
                "value": value,
            })
    out = {"generated": TODAY, "records": records}
    io.open(args.out, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
    from collections import Counter
    c = Counter(r["category"] for r in records)
    occ = Counter()
    for r in records:
        occ[r["category"]] += r["match_count"]
    print(f"records={len(records)} | fields: {dict(c)} | occurrences: {dict(occ)}")
    return 0


# ---------------- apply ----------------

def _apply_to_entity_dict(e: dict, field: str, old: str, new: str) -> bool:
    """Áp 1 patch lên entity dạng dict (data.json). True nếu ghi."""
    if field.startswith("attr:"):
        key = field[5:]
        attrs = e.get("attributes")
        if not isinstance(attrs, dict) or attrs.get(key) != old:
            return False
        attrs[key] = new
    else:
        if e.get(field) != old:
            return False
        e[field] = new
    e["updatedAt"] = TODAY
    return True


def apply_json(path: str, patches: list, dry_run: bool) -> dict:
    data = json.load(io.open(path, encoding="utf-8"))
    idx = {e["id"]: e for e in data["entities"]}
    applied, skipped = [], []
    for p in patches:
        e = idx.get(p["entity_id"])
        ok = bool(e) and _apply_to_entity_dict(e, p["field"], p["old_value"], p["new_value"]) if e else False
        (applied if ok else skipped).append(f'{p["entity_id"]}:{p["field"]}')
    if not dry_run and applied:
        tmp = path + ".fixtmp"
        io.open(tmp, "w", encoding="utf-8").write(json.dumps(data, ensure_ascii=False))
        os.replace(tmp, path)
    return {"store": "json", "applied": len(applied), "skipped": len(skipped), "skipped_list": skipped[:20], "dry_run": dry_run}


def _apply_row(get_val, set_val, patch) -> bool:
    field, old, new = patch["field"], patch["old_value"], patch["new_value"]
    if field.startswith("attr:"):
        key = field[5:]
        raw = get_val("attributes")
        try:
            attrs = json.loads(raw) if isinstance(raw, str) else (raw or {})
        except json.JSONDecodeError:
            return False
        if not isinstance(attrs, dict) or attrs.get(key) != old:
            return False
        attrs[key] = new
        set_val("attributes", json.dumps(attrs, ensure_ascii=False))
    else:
        if get_val(field) != old:
            return False
        set_val(field, new)
    return True


def apply_sqlite(path: str, patches: list, dry_run: bool) -> dict:
    import sqlite3
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    applied, skipped = [], []
    try:
        for p in patches:
            row = conn.execute(
                "SELECT name, description, summary, attributes, updatedAt FROM entities WHERE id=?",
                (p["entity_id"],),
            ).fetchone()
            if row is None:
                skipped.append(f'{p["entity_id"]}:{p["field"]}:no-row')
                continue
            pend = {}
            ok = _apply_row(lambda c: row[c], lambda c, v: pend.__setitem__(c, v), p)
            if not ok:
                skipped.append(f'{p["entity_id"]}:{p["field"]}')
                continue
            applied.append(f'{p["entity_id"]}:{p["field"]}')
            if not dry_run:
                sets = ", ".join(f"{c}=?" for c in pend) + ", updatedAt=?"
                conn.execute(f"UPDATE entities SET {sets} WHERE id=?", (*pend.values(), TODAY, p["entity_id"]))
        if not dry_run:
            conn.commit()
    finally:
        conn.close()
    return {"store": "sqlite", "applied": len(applied), "skipped": len(skipped), "skipped_list": skipped[:20], "dry_run": dry_run}


def apply_pg(patches: list, dry_run: bool) -> dict:
    import psycopg2
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL chưa đặt")
    conn = psycopg2.connect(dsn)
    applied, skipped = [], []
    try:
        with conn:
            with conn.cursor() as cur:
                for p in patches:
                    cur.execute("SELECT name, description, summary, attributes::text FROM entities WHERE id=%s", (p["entity_id"],))
                    row = cur.fetchone()
                    if row is None:
                        skipped.append(f'{p["entity_id"]}:{p["field"]}:no-row')
                        continue
                    cols = {"name": row[0], "description": row[1], "summary": row[2], "attributes": row[3]}
                    pend = {}
                    ok = _apply_row(cols.get, pend.__setitem__, p)
                    if not ok:
                        skipped.append(f'{p["entity_id"]}:{p["field"]}')
                        continue
                    applied.append(f'{p["entity_id"]}:{p["field"]}')
                    if not dry_run:
                        for c, v in pend.items():
                            if c == "attributes":
                                cur.execute("UPDATE entities SET attributes=%s::jsonb, \"updatedAt\"=%s WHERE id=%s", (v, TODAY, p["entity_id"]))
                            else:
                                cur.execute(f'UPDATE entities SET {c}=%s, "updatedAt"=%s WHERE id=%s', (v, TODAY, p["entity_id"]))
            if dry_run:
                conn.rollback()
    finally:
        conn.close()
    return {"store": "pg", "applied": len(applied), "skipped": len(skipped), "skipped_list": skipped[:20], "dry_run": dry_run}


def cmd_apply(args) -> int:
    patches = json.load(io.open(args.patches, encoding="utf-8"))
    if isinstance(patches, dict):
        patches = patches["patches"]
    for p in patches:  # sanity từng patch
        assert p["old_value"] != p["new_value"], f'patch no-op: {p["entity_id"]}:{p["field"]}'
    if args.json_path:
        r = apply_json(args.json_path, patches, args.dry_run)
    elif args.sqlite_path:
        r = apply_sqlite(args.sqlite_path, patches, args.dry_run)
    elif args.pg:
        r = apply_pg(patches, args.dry_run)
    else:
        print("Cần --json | --sqlite | --pg"); return 2
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0


# ---------------- verify ----------------

def cmd_verify(args) -> int:
    from collections import Counter
    c = Counter()
    if args.json_path:
        data = json.load(io.open(args.json_path, encoding="utf-8"))
        ents = data["entities"]
    elif args.sqlite_path:
        import sqlite3
        conn = sqlite3.connect(args.sqlite_path); conn.row_factory = sqlite3.Row
        ents = [dict(r) for r in conn.execute("SELECT id, name, description, summary, attributes FROM entities")]
        conn.close()
    elif args.pg:
        import psycopg2
        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, description, summary, attributes::text FROM entities")
            ents = [dict(zip(("id", "name", "description", "summary", "attributes"), r)) for r in cur.fetchall()]
        conn.close()
    else:
        print("Cần --json | --sqlite | --pg"); return 2
    total = 0
    for e in ents:
        for field, value in iter_fields(e):
            n = len(PAT.findall(value))
            c[classify(field)] += n
            total += n
    print(json.dumps({"total": total, "by_category": dict(c)}, ensure_ascii=False))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p1 = sub.add_parser("extract"); p1.add_argument("--in", dest="infile", required=True); p1.add_argument("--out", required=True)
    p2 = sub.add_parser("apply"); p2.add_argument("--patches", required=True)
    p2.add_argument("--json", dest="json_path"); p2.add_argument("--sqlite", dest="sqlite_path"); p2.add_argument("--pg", action="store_true")
    p2.add_argument("--dry-run", action="store_true")
    p3 = sub.add_parser("verify")
    p3.add_argument("--json", dest="json_path"); p3.add_argument("--sqlite", dest="sqlite_path"); p3.add_argument("--pg", action="store_true")
    a = ap.parse_args()
    return {"extract": cmd_extract, "apply": cmd_apply, "verify": cmd_verify}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
