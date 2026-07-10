#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Áp edit-record (mientay-rephrase + coord-fix) vào 1 kho. Dry-run mặc định (R70.5).

SURGICAL — chỉ đụng field/string liên quan (KHÔNG --replace) để giữ tối đa edit
AdminCP write-through trên prod (B7). Edit-record tự chứa (không cần data.json).

Loại edit:
  - field-set (top_level + formula_R50.3): entity[field] = new_text theo entity_id
    (entity qua get/upsert_entity; itinerary qua get/upsert_itinerary).
  - string-replace (nested + content_surgical): old→new trong MỌI string value.
  - coord_fixes: delete_entity · set attributes.coords_approximate=true · add coordinates.

  python scripts/apply_edit_record.py --record <f.json> --store sqlite [--execute]
  DATABASE_URL=postgresql://… python scripts/apply_edit_record.py --record <f.json> --store pg [--execute]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date

TODAY = date.today().isoformat()


def _load_db(store: str):
    if store == "sqlite":
        os.environ.pop("DATABASE_URL", None)  # ép SQLite bất kể env
    elif store == "pg" and not os.environ.get("DATABASE_URL", "").startswith("postgresql"):
        print("ERROR: --store pg cần DATABASE_URL=postgresql://…", file=sys.stderr)
        sys.exit(2)
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
    from database import db  # noqa: E402
    return db


def _walk_replace(value, pairs):
    """Đệ quy replace old→new trong mọi string. Trả (value_mới, có_đổi)."""
    if isinstance(value, str):
        nv = value
        for old, new in pairs:
            if old in nv:
                nv = nv.replace(old, new)
        return nv, (nv != value)
    if isinstance(value, dict):
        changed = False
        out = {}
        for k, v in value.items():
            out[k], ch = _walk_replace(v, pairs)
            changed = changed or ch
        return out, changed
    if isinstance(value, list):
        changed = False
        out = []
        for v in value:
            nv, ch = _walk_replace(v, pairs)
            out.append(nv)
            changed = changed or ch
        return out, changed
    return value, False


def _apply_field_sets(db, edits, execute, stats):
    for ed in edits:
        eid, field, new_text = ed.get("entity_id"), ed.get("field"), ed.get("new_text")
        if not (eid and field and (new_text or "").strip()):
            stats["field_skip"] += 1
            continue
        e = db.get_entity(eid)
        if e is not None:
            e[field] = new_text
            e["updatedAt"] = TODAY
            if execute:
                db.upsert_entity(e)
            stats["field_set"] += 1
            continue
        it = db.get_itinerary(eid)
        if it is not None:
            it[field] = new_text
            if execute:
                db.upsert_itinerary(it)
            stats["field_set"] += 1
            continue
        stats["field_skip"] += 1


def _collect_pairs(record):
    pairs = []
    for ed in record.get("nested", []):
        o, n = ed.get("old_string"), ed.get("new_string")
        if o and n is not None:
            pairs.append((o, n))
    for ed in record.get("content_surgical", []):
        o, n = ed.get("old"), ed.get("new")
        if o and n is not None:
            pairs.append((o, n))
    return pairs


_KEY_TEXT_FIELDS = ("summary", "description", "title", "name")


def _reconcile(original, replaced, ref, stats):
    """Chỉ giữ thay đổi string-replace ở key-text-field mà kết quả KHỚP data.json (ref).

    Chống over-match: pair bare (vd 'miền Tây'→'Vĩnh Long') có thể hỏng region-name
    ('miền Tây Nam Bộ'→'Vĩnh Long Nam Bộ') ở record data.json GIỮ nguyên. Nếu kết quả
    replace ≠ giá trị data.json → BỎ thay đổi field đó (giữ original). Trả (final, n_kept).
    """
    final = dict(original)
    kept = 0
    for f in _KEY_TEXT_FIELDS:
        if replaced.get(f) == original.get(f):
            continue  # field này không bị replace đụng
        if ref is not None and replaced.get(f) == ref.get(f):
            final[f] = replaced[f]
            kept += 1
        else:
            stats["str_skip_overmatch"] += 1  # replace đổi nhưng KHÔNG khớp data.json → bỏ
    return final, kept


def _apply_string_replaces(db, pairs, ref_by_id, execute, stats):
    if not pairs:
        return
    for e in db.all_entities():
        replaced, changed = _walk_replace(e, pairs)
        if not changed:
            continue
        final, kept = _reconcile(e, replaced, ref_by_id.get(e["id"]), stats)
        if kept:
            final["updatedAt"] = TODAY
            if execute:
                db.upsert_entity(final)
            stats["str_replace_recs"] += 1
    for it in db.all_itineraries():
        replaced, changed = _walk_replace(it, pairs)
        if not changed:
            continue
        final, kept = _reconcile(it, replaced, ref_by_id.get(it["id"]), stats)
        if kept:
            if execute:
                db.upsert_itinerary(final)
            stats["str_replace_recs"] += 1


def _set_approx(entity):
    attrs = entity.get("attributes")
    if not isinstance(attrs, dict):
        attrs = {}
    attrs["coords_approximate"] = True
    entity["attributes"] = attrs
    entity["updatedAt"] = TODAY


def _apply_coord_fixes(db, cf, execute, stats):
    for raw in cf.get("delete_entity", []):
        eid = raw.split(" (")[0].strip()  # bỏ chú thích trong ngoặc
        if db.get_entity(eid) is not None:
            if execute:
                db.delete_entity(eid)
            stats["coord"] += 1
        else:
            stats["coord_skip"] += 1
    for eid in cf.get("set_coords_approximate_true", []):
        e = db.get_entity(eid)
        if e is None:
            stats["coord_skip"] += 1
            continue
        _set_approx(e)
        if execute:
            db.upsert_entity(e)
        stats["coord"] += 1
    for eid, coords in cf.get("add_coords", {}).items():
        if eid.startswith("_"):  # bỏ khóa _note
            continue
        e = db.get_entity(eid)
        if e is None:
            stats["coord_skip"] += 1
            continue
        e["coordinates"] = coords
        _set_approx(e)
        if execute:
            db.upsert_entity(e)
        stats["coord"] += 1


def _load_reference(path):
    """data.json {id: record} cho entities + itineraries (validate string-replace)."""
    with open(path, encoding="utf-8") as f:
        dj = json.load(f)
    ref = {e["id"]: e for e in dj.get("entities", [])}
    ref.update({i["id"]: i for i in dj.get("itineraries", [])})
    return ref


def apply_record(db, record, ref_by_id, execute):
    stats = {"field_set": 0, "field_skip": 0, "str_replace_recs": 0,
             "str_skip_overmatch": 0, "coord": 0, "coord_skip": 0}
    _apply_field_sets(db, record.get("top_level", []) + record.get("formula_R50.3", []), execute, stats)
    _apply_string_replaces(db, _collect_pairs(record), ref_by_id, execute, stats)
    _apply_coord_fixes(db, record.get("coord_fixes_R_deploygate", {}), execute, stats)
    return stats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--reference", default="web/data.json",
                    help="data.json làm chân lý validate string-replace (chống over-match)")
    ap.add_argument("--store", choices=["sqlite", "pg"], default="sqlite")
    ap.add_argument("--execute", action="store_true", help="Ghi thật (mặc định dry-run)")
    args = ap.parse_args()

    with open(args.record, encoding="utf-8") as f:
        record = json.load(f)
    ref_by_id = _load_reference(args.reference)
    db = _load_db(args.store)
    stats = apply_record(db, record, ref_by_id, args.execute)
    mode = "EXECUTE" if args.execute else "DRY-RUN"
    print(f"[{mode}] store={args.store} {json.dumps(stats, ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
