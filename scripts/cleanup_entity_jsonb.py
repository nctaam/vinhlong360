"""GĐ-C3: dọn typed keys khỏi attributes JSONB — cột/bảng CTI thành nguồn sự thật duy nhất.

AN TOÀN THIẾT KẾ (so-sánh-trước-khi-xoá): một key CHỈ bị xoá khỏi JSONB khi giá
trị cột tương ứng THẬT SỰ khớp (sau chuẩn hoá kiểu). Hệ quả:
  - Giá trị uncoercible ("Thế kỷ 19", "20 phòng") → cột NULL → KHÔNG xoá.
  - Môi trường cột trống (dev SQLite chưa backfill) → KHÔNG xoá gì (no-op).
  - Tail (bespoke + KBYG) không thuộc schema → không bao giờ đụng.
Idempotent. KHÔNG gọi sync (cột giữ nguyên). Đọc JSONB THÔ (không qua rebuild).

BẮT BUỘC trước khi --apply trên prod: pg_dump backup (§B1).
Chạy: set -a; . ./.env; set +a
  ./venv/bin/python scripts/cleanup_entity_jsonb.py --dry-run | --apply
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agent"))
from database import db  # noqa: E402
from entity_details import (  # noqa: E402
    KEY_MAP, KIND_TABLE, UNIVERSAL, norm_value, split_typed,
)
from entity_schemas import ENTITY_SCHEMAS, KIND_OF_TYPE  # noqa: E402


def strippable_keys(etype: str, attrs: dict, entity_row: dict, detail_row: dict) -> list[str]:
    """Các key trong attrs có giá trị cột KHỚP (sau coercion + chuẩn hoá) → xoá được."""
    uni, det, _ = split_typed(etype, attrs)
    out: list[str] = []
    schema = ENTITY_SCHEMAS.get(etype) or {"fields": []}
    for f in schema["fields"]:
        key = f["key"]
        if key not in attrs:
            continue
        if key in UNIVERSAL:
            expected = uni.get(key)
            actual = entity_row.get(key)
        else:
            col = KEY_MAP.get(key, key)
            expected = det.get(col)
            actual = detail_row.get(col)
        if expected is None:
            continue  # uncoercible/rỗng — ở lại JSONB
        if isinstance(expected, list) or isinstance(actual, list):
            if (actual or []) == (expected or []):
                out.append(key)
        elif norm_value(actual) == norm_value(expected):
            out.append(key)
    return out


def run(apply: bool) -> dict:
    db.initialize()
    ph = db._ph
    with db._conn() as conn:
        rows = db._fetchall(conn, "SELECT * FROM entities", ())
        raw_entities = [db._row_to_dict(r) for r in rows]
        details: dict[str, dict[str, dict]] = {}
        for table in set(KIND_TABLE.values()):
            drows = db._fetchall(conn, f"SELECT * FROM {table}", ())
            details[table] = {}
            for dr in drows:
                dd = db._row_to_dict(dr)
                eid = dd.pop("entity_id")
                # chuẩn hoá kiểu như cache đọc (bool/json/decimal)
                from entity_details import _norm_col_value
                details[table][eid] = {c: _norm_col_value(c, v) for c, v in dd.items()}

        stats = {"entities": len(raw_entities), "touched": 0, "keys_removed": 0, "kept_uncoercible": 0}
        for e in raw_entities:
            attrs = e.get("attributes")
            if isinstance(attrs, str):
                try:
                    attrs = json.loads(attrs or "{}")
                except (json.JSONDecodeError, ValueError):
                    continue
            if not isinstance(attrs, dict) or not attrs:
                continue
            kind = KIND_OF_TYPE.get(e["type"])
            table = KIND_TABLE.get(kind or "")
            drow = details.get(table, {}).get(e["id"], {}) if table else {}
            strip = strippable_keys(e["type"], attrs, e, drow)
            if not strip:
                continue
            new_attrs = {k: v for k, v in attrs.items() if k not in strip}
            # đếm key schema còn lại vì uncoercible (thống kê minh bạch)
            schema_keys = {f["key"] for f in (ENTITY_SCHEMAS.get(e["type"]) or {"fields": []})["fields"]}
            stats["kept_uncoercible"] += sum(1 for k in new_attrs if k in schema_keys)
            stats["touched"] += 1
            stats["keys_removed"] += len(strip)
            if apply:
                db._execute(conn, f"UPDATE entities SET attributes = {ph} WHERE id = {ph}",
                            (json.dumps(new_attrs, ensure_ascii=False), e["id"]))
        if not apply and db._use_pg:
            conn.rollback()
    return stats


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    stats = run(apply=args.apply)
    mode = "APPLIED" if args.apply else "DRY-RUN"
    print(f"[{mode}] entities={stats['entities']} | touched={stats['touched']} "
          f"| keys_removed={stats['keys_removed']} | schema-keys giữ lại (uncoercible)={stats['kept_uncoercible']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
