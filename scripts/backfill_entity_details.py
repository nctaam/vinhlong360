"""Backfill entity typed attributes (JSONB) → cột phổ quát + bảng CTI (GĐ-B bước 3).

Spec: docs/superpowers/specs/2026-07-02-entity-split-per-kind-design.md

Nguyên tắc:
- PG-only (SQLite dev chưa có bảng CTI — database.py parity thuộc GĐ-C).
- `attributes` JSONB KHÔNG bị sửa — nguồn sự thật chưa đổi cho tới GĐ-C.
- Idempotent: cột chỉ được điền khi đang NULL (COALESCE — cột-đã-có luôn thắng).
- Ánh xạ cột + widget lấy TRỰC TIẾP từ registry agent/entity_schemas.py; 2 ngoại lệ
  tên cột trong KEY_MAP phải khớp comment migration 061.
- Giá trị không coerce được (vd chữ trong cột số) → BỎ QUA (ở lại JSONB), có đếm log.

Chạy trên VPS (từ /opt/vinhlong360, sau `set -a; . ./.env; set +a`):
  ./venv/bin/python scripts/backfill_entity_details.py --dry-run
  ./venv/bin/python scripts/backfill_entity_details.py --apply
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agent"))
from entity_schemas import KIND_OF_TYPE  # noqa: E402
# Nguồn sự thật ánh xạ + coercion: agent/entity_details.py (GĐ-C dual-write dùng chung).
from entity_details import (  # noqa: E402,F401  (INT_COLUMNS/KEY_MAP/UNIVERSAL re-export cho test_backfill_entity_details)
    INT_COLUMNS, JSONB_COLUMNS, KEY_MAP, KIND_TABLE, UNIVERSAL, split_typed,
)

typed_values = split_typed  # alias giữ tương thích parity script/test


def _apply_universal(cur, r, uni, stats, apply):
    """Cập nhật cột phổ quát (COALESCE — cột-đã-có thắng) + đếm stats."""
    if uni:
        stats["uni_updates"] += 1
        if apply:
            sets = ", ".join(f"{k} = COALESCE({k}, %s)" for k in uni)
            cur.execute(f"UPDATE entities SET {sets} WHERE id = %s", [*uni.values(), r["id"]])


def _apply_detail(cur, r, det, stats, per_table, apply):
    """Upsert bảng CTI (ON CONFLICT COALESCE) + đếm stats/per_table."""
    import psycopg2.extras
    kind = KIND_OF_TYPE.get(r["type"])
    table = KIND_TABLE.get(kind or "")
    if table and det:
        stats["detail_rows"] += 1
        per_table[table] += 1
        if apply:
            cols = list(det.keys())
            vals = [psycopg2.extras.Json(v) if c in JSONB_COLUMNS else v
                    for c, v in det.items()]
            collist = ", ".join(cols)
            ph = ", ".join(["%s"] * len(cols))
            updates = ", ".join(f"{c} = COALESCE({table}.{c}, EXCLUDED.{c})" for c in cols)
            cur.execute(
                f"INSERT INTO {table} (entity_id, {collist}) VALUES (%s, {ph}) "
                f"ON CONFLICT (entity_id) DO UPDATE SET {updates}",
                [r["id"], *vals])


def _process_row(cur, r, stats, per_table, skipped_log, apply):
    """Xử lý 1 entity: parse attrs → split → apply universal + detail."""
    attrs = r["attributes"] or {}
    if isinstance(attrs, str):
        attrs = json.loads(attrs or "{}")
    uni, det, skipped = typed_values(r["type"], attrs)
    if skipped:
        stats["skipped_vals"] += len(skipped)
        skipped_log.extend(f"{r['id']}: {s}" for s in skipped)
    _apply_universal(cur, r, uni, stats, apply)
    _apply_detail(cur, r, det, stats, per_table, apply)


def _print_report(mode, stats, per_table, skipped_log):
    """In báo cáo tổng + per-table + danh sách skipped (tối đa 15 dòng)."""
    print(f"[{mode}] entities={stats['entities']} | uni_updates={stats['uni_updates']} "
          f"| detail_rows={stats['detail_rows']} | skipped_vals={stats['skipped_vals']}")
    for t, n in sorted(per_table.items(), key=lambda kv: -kv[1]):
        if n:
            print(f"  {t}: {n}")
    if skipped_log:
        print("-- skipped (ở lại JSONB, tối đa 15 dòng):")
        for line in skipped_log[:15]:
            print("  ", line)


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    dsn = os.environ.get("DATABASE_URL", "")
    if not dsn.startswith(("postgres://", "postgresql://")):
        print("DATABASE_URL không phải Postgres — backfill là PG-only. Dừng.")
        return 2
    import psycopg2
    import psycopg2.extras

    conn = psycopg2.connect(dsn)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT id, type, attributes FROM entities")
    rows = cur.fetchall()

    stats = {"entities": len(rows), "uni_updates": 0, "detail_rows": 0, "skipped_vals": 0}
    per_table: dict[str, int] = {t: 0 for t in KIND_TABLE.values()}
    skipped_log: list[str] = []

    for r in rows:
        _process_row(cur, r, stats, per_table, skipped_log, args.apply)

    if args.apply:
        conn.commit()
        mode = "APPLIED"
    else:
        conn.rollback()
        mode = "DRY-RUN"
    conn.close()

    _print_report(mode, stats, per_table, skipped_log)
    return 0


if __name__ == "__main__":
    sys.exit(main())
