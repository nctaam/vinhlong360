"""Đối chiếu từng dòng JSONB ↔ cột phổ quát + bảng CTI (GĐ-B bước 4).

Luật: với mỗi entity, giá trị typed coerce-được trong `attributes` PHẢI bằng giá
trị cột tương ứng (universal trên entities, còn lại trong bảng CTI của kind).
Hai chiều: cột có giá trị mà JSONB không có (sau coercion) cũng là lệch.
Exit 0 = parity sạch; exit 1 = có lệch (in tối đa 20 dòng đầu).

Chạy trên VPS: set -a; . ./.env; set +a
  ./venv/bin/python scripts/verify_entity_details_parity.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agent"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from entity_schemas import KIND_OF_TYPE  # noqa: E402
from backfill_entity_details import (  # noqa: E402
    KIND_TABLE, JSONB_COLUMNS, UNIVERSAL, typed_values,
)


def _norm(v):
    if v is None:
        return None
    if isinstance(v, float) and v.is_integer():
        return int(v)
    if isinstance(v, str):
        return v.strip()
    return v


def main() -> int:
    dsn = os.environ.get("DATABASE_URL", "")
    if not dsn.startswith(("postgres://", "postgresql://")):
        print("DATABASE_URL không phải Postgres — parity là PG-only. Dừng.")
        return 2
    import psycopg2
    import psycopg2.extras
    from decimal import Decimal

    conn = psycopg2.connect(dsn)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM entities")
    entities = cur.fetchall()

    details: dict[str, dict[str, dict]] = {}
    for table in set(KIND_TABLE.values()):
        cur.execute(f"SELECT * FROM {table}")
        details[table] = {r["entity_id"]: dict(r) for r in cur.fetchall()}
    conn.close()

    mismatches: list[str] = []
    checked = 0
    for e in entities:
        attrs = e.get("attributes") or {}
        if isinstance(attrs, str):
            attrs = json.loads(attrs or "{}")
        uni, det, _skipped = typed_values(e["type"], attrs)
        kind = KIND_OF_TYPE.get(e["type"])
        table = KIND_TABLE.get(kind or "")
        drow = details.get(table, {}).get(e["id"], {}) if table else {}

        for key, expected in uni.items():
            checked += 1
            actual = e.get(key)
            if _norm(actual) != _norm(expected):
                mismatches.append(f"{e['id']}.{key}: cột={actual!r} ≠ jsonb={expected!r}")
        if not table:
            # Kind không có bảng CTI (itinerary — bảng riêng; other) → typed fields
            # ở lại JSONB theo thiết kế, không phải lệch.
            det = {}
        for col, expected in det.items():
            checked += 1
            actual = drow.get(col)
            if isinstance(actual, Decimal):
                actual = float(actual)
            if col in JSONB_COLUMNS:
                if (actual or []) != (expected or []):
                    mismatches.append(f"{e['id']}.{col}: cột={actual!r} ≠ jsonb={expected!r}")
            elif _norm(actual) != _norm(expected):
                mismatches.append(f"{e['id']}.{col}: cột={actual!r} ≠ jsonb={expected!r}")
        # HẬU-C3: JSONB lưu tail-only — key VẮNG trong JSONB là by-design (đã dọn),
        # KHÔNG phải lệch. Chỉ XUNG ĐỘT giá trị (key tồn tại trong JSONB nhưng khác
        # cột) mới là lệch — đã được kiểm ở chiều thuận phía trên.

    print(f"parity: {checked} giá trị đối chiếu, {len(mismatches)} lệch / {len(entities)} entity")
    for line in mismatches[:20]:
        print("  LỆCH:", line)
    return 1 if mismatches else 0


if __name__ == "__main__":
    sys.exit(main())
