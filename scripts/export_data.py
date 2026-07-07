#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Export DB → data.json (MỘT CHIỀU, công cụ THỦ CÔNG — không auto-chạy).

Tái lập cơ chế export sau khi export_data.py cũ bị xoá trong cleanup 06/2026
(campaign tỉnh-mới T1, plan docs/superpowers/plans/2026-07-07-data-tinh-moi.md).

- Nguồn: database layer (backend theo DATABASE_URL — SQLite local / PG prod).
- Đích: file JSON shape {entities, relationships, itineraries} (khớp web/data.json).
- Ghi ATOMIC (.tmp cùng thư mục + os.replace) — không bao giờ để file dở.
- `--dry-run`: chỉ in diff summary so với file hiện có, KHÔNG ghi.

B1 (CLAUDE.md): backup file đích trước khi ghi đè thật — chạy
`python scripts/backup_data.py` trước, script này không tự backup.

Dùng:
  python scripts/export_data.py --dry-run                 # xem diff vs web/data.json
  python scripts/export_data.py --out web/data.json       # ghi thật (sau khi backup)
  DATABASE_URL=postgresql://... python scripts/export_data.py --out /tmp/prod.json
"""
import argparse
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "agent"))

DEFAULT_OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "web", "data.json")


def build_payload(db) -> dict:
    return {
        "entities": db.all_entities(),
        "relationships": db.all_relationships(),
        "itineraries": db.all_itineraries(),
    }


def _entity_index(items: list) -> dict:
    return {e.get("id"): e for e in items if isinstance(e, dict) and e.get("id")}


def diff_summary(payload: dict, out_path: str) -> dict:
    """So payload mới với file hiện có (nếu có) — đếm thêm/bớt/đổi entity."""
    if not os.path.exists(out_path):
        return {"existing": False}
    try:
        with open(out_path, encoding="utf-8") as f:
            old = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        return {"existing": True, "unreadable": str(e)}
    new_idx = _entity_index(payload.get("entities", []))
    old_idx = _entity_index(old.get("entities", []))
    added = [i for i in new_idx if i not in old_idx]
    removed = [i for i in old_idx if i not in new_idx]
    changed = []
    for i in new_idx:
        if i in old_idx and json.dumps(new_idx[i], sort_keys=True, ensure_ascii=False) != json.dumps(
            old_idx[i], sort_keys=True, ensure_ascii=False
        ):
            changed.append(i)
    return {
        "existing": True,
        "entities_added": len(added),
        "entities_removed": len(removed),
        "entities_changed": len(changed),
        "added_sample": added[:5],
        "removed_sample": removed[:5],
        "changed_sample": changed[:5],
        "relationships_old_new": [len(old.get("relationships", [])), len(payload.get("relationships", []))],
        "itineraries_old_new": [len(old.get("itineraries", [])), len(payload.get("itineraries", []))],
    }


def export(db, out_path: str, dry_run: bool = False) -> dict:
    payload = build_payload(db)
    counts = {k: len(v) for k, v in payload.items()}
    result = {"written": False, "counts": counts, "diff": diff_summary(payload, out_path)}
    if counts["entities"] == 0:
        raise RuntimeError("DB trả 0 entity — từ chối export (tránh ghi đè data.json bằng file rỗng).")
    if dry_run:
        return result
    out_dir = os.path.dirname(os.path.abspath(out_path)) or "."
    fd, tmp_path = tempfile.mkstemp(prefix=".export-", suffix=".json", dir=out_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
        os.replace(tmp_path, out_path)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
    result["written"] = True
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="Export DB → data.json (một chiều, thủ công)")
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    from database import db  # backend theo DATABASE_URL

    result = export(db, a.out, dry_run=a.dry_run)
    print(json.dumps(result, ensure_ascii=False, indent=1))
    if not a.dry_run:
        print(f"OK: wrote {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
