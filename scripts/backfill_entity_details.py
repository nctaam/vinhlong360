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
from entity_schemas import ENTITY_SCHEMAS, KIND_OF_TYPE, _coerce  # noqa: E402

UNIVERSAL = ["address", "phone", "website", "hours", "price_range",
             "sub_category", "best_time", "highlight"]
KEY_MAP = {"view": "view_note", "architectural_style": "architecture_style"}
KIND_TABLE = {
    "place": "entity_place_details",
    "food": "entity_food_details",
    "product": "entity_product_details",
    "lodging": "entity_lodging_details",
    "event": "entity_event_details",
    "experience": "entity_experience_details",
    "facility": "entity_facility_details",
    "person": "entity_person_details",
    "admin_place": "entity_adminplace_details",
}
# Cột INTEGER trong 061 — float lẻ (4.5) vào đây là dữ liệu rác → bỏ qua.
INT_COLUMNS = {"founding_year", "scenic_rating", "review_count", "ocop_star",
               "households", "star_rating", "rooms", "month", "duration_days",
               "birth_year", "death_year", "population"}
# Cột JSONB trong 061 (widget tags).
JSONB_COLUMNS = {"ingredients", "amenities", "merged_from"}


def typed_values(etype: str, attrs: dict) -> tuple[dict, dict, list[str]]:
    """→ (universal {key: str}, detail {column: value}, skipped [key=value])."""
    schema = ENTITY_SCHEMAS.get(etype) or {"fields": []}
    uni: dict = {}
    det: dict = {}
    skipped: list[str] = []
    for f in schema["fields"]:
        key = f["key"]
        if key not in attrs:
            continue
        raw = attrs[key]
        if raw in (None, "", [], {}):
            continue
        coerced, ok = _coerce(raw, f["widget"])
        if not ok or coerced in (None, "", [], {}):
            skipped.append(f"{key}={raw!r}")
            continue
        if key in UNIVERSAL:
            uni[key] = coerced if isinstance(coerced, str) else str(coerced)
            continue
        col = KEY_MAP.get(key, key)
        if col in INT_COLUMNS:
            # Widget select trả string ("3" cho ocop_star) — nhận string số.
            if isinstance(coerced, bool):
                skipped.append(f"{key}={raw!r}")
                continue
            if isinstance(coerced, str):
                try:
                    coerced = float(coerced.strip().replace(",", "."))
                except ValueError:
                    skipped.append(f"{key}={raw!r}")
                    continue
            if isinstance(coerced, float):
                if not coerced.is_integer():
                    skipped.append(f"{key}={raw!r}")
                    continue
                coerced = int(coerced)
            if not isinstance(coerced, int):
                skipped.append(f"{key}={raw!r}")
                continue
        det[col] = coerced
    return uni, det, skipped


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
        attrs = r["attributes"] or {}
        if isinstance(attrs, str):
            attrs = json.loads(attrs or "{}")
        uni, det, skipped = typed_values(r["type"], attrs)
        if skipped:
            stats["skipped_vals"] += len(skipped)
            skipped_log.extend(f"{r['id']}: {s}" for s in skipped)
        if uni:
            stats["uni_updates"] += 1
            if args.apply:
                sets = ", ".join(f"{k} = COALESCE({k}, %s)" for k in uni)
                cur.execute(f"UPDATE entities SET {sets} WHERE id = %s", [*uni.values(), r["id"]])
        kind = KIND_OF_TYPE.get(r["type"])
        table = KIND_TABLE.get(kind or "")
        if table and det:
            stats["detail_rows"] += 1
            per_table[table] += 1
            if args.apply:
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

    if args.apply:
        conn.commit()
        mode = "APPLIED"
    else:
        conn.rollback()
        mode = "DRY-RUN"
    conn.close()

    print(f"[{mode}] entities={stats['entities']} | uni_updates={stats['uni_updates']} "
          f"| detail_rows={stats['detail_rows']} | skipped_vals={stats['skipped_vals']}")
    for t, n in sorted(per_table.items(), key=lambda kv: -kv[1]):
        if n:
            print(f"  {t}: {n}")
    if skipped_log:
        print("-- skipped (ở lại JSONB, tối đa 15 dòng):")
        for line in skipped_log[:15]:
            print("  ", line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
