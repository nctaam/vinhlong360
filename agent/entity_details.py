"""agent/entity_details.py — GĐ-C (C1): đồng bộ typed attributes ↔ cột phổ quát + bảng CTI.

Spec: docs/superpowers/specs/2026-07-02-entity-split-per-kind-design.md

Vai trò: NGUỒN SỰ THẬT về ánh xạ registry-key → cột vật lý (KEY_MAP, KIND_TABLE,
INT/JSONB columns) + logic dual-write. `scripts/backfill_entity_details.py` import
từ đây (không duplicate). database.py chỉ gọi 3 hook nhỏ:
  - ensure_schema_sqlite(conn)          — DDL parity cho dev SQLite
  - sync_entity_details(conn, is_pg, id, type, attrs)  — sau mỗi lần ghi entity
  - (delete: PG cascade qua FK; SQLite dọn trong sync khi det rỗng + delete hook)

Bất biến C1 (dual-write, CHƯA flip đọc): sau mỗi lần ghi, cột/bảng CTI PHẢN CHIẾU
đúng nội dung typed coerce-được trong attributes JSONB — parity script luôn 0 lệch.
JSONB vẫn là nguồn sự thật cho mọi đường đọc (flip đọc = C2, sau flag).
"""
from __future__ import annotations

import json
import os
from decimal import Decimal
from typing import Any

from entity_schemas import ENTITY_SCHEMAS, KIND_OF_TYPE, _coerce

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
INT_COLUMNS = {"founding_year", "scenic_rating", "review_count", "ocop_star",
               "households", "star_rating", "rooms", "month", "duration_days",
               "birth_year", "death_year", "population"}
JSONB_COLUMNS = {"ingredients", "amenities", "merged_from"}
NUMERIC_COLUMNS = {"rating"}
BOOL_COLUMNS = {"parking", "wifi", "ocop_certified"}


def _kind_columns() -> dict[str, list[str]]:
    """kind -> danh sách cột (ổn định, sorted) từ registry, trừ universal, áp KEY_MAP."""
    out: dict[str, set[str]] = {k: set() for k in KIND_TABLE}
    for etype, schema in ENTITY_SCHEMAS.items():
        kind = KIND_OF_TYPE.get(etype)
        if kind not in KIND_TABLE:
            continue
        for f in schema["fields"]:
            key = f["key"]
            if key in UNIVERSAL:
                continue
            out[kind].add(KEY_MAP.get(key, key))
    return {k: sorted(v) for k, v in out.items()}


KIND_COLUMNS: dict[str, list[str]] = _kind_columns()


def split_typed(etype: str, attrs: dict | None) -> tuple[dict, dict, list[str]]:
    """→ (universal {key: str}, detail {column: value}, skipped [key=value]).

    Cùng luật coercion với validate_attributes (widget-based); giá trị không
    coerce được (chữ trong cột số) bị bỏ qua — ở lại JSONB, không ép bừa.
    """
    attrs = attrs or {}
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


def _exec(conn, is_pg: bool, sql: str, params: list) -> None:
    if is_pg:
        cur = conn.cursor()
        cur.execute(sql, params)
    else:
        conn.execute(sql, params)


def _db_value(col: str, value: Any, is_pg: bool):
    if value is None:
        return None
    if col in JSONB_COLUMNS:
        if is_pg:
            from psycopg2.extras import Json
            return Json(value)
        return json.dumps(value, ensure_ascii=False)
    if col in BOOL_COLUMNS and not is_pg:
        return 1 if value else 0
    return value


def sync_entity_details(conn, is_pg: bool, entity_id: str, etype: str,
                        attrs: dict | None) -> None:
    """Dual-write: phản chiếu typed attributes vào cột phổ quát + bảng CTI.

    Ghi-là-chính (mirror, KHÔNG COALESCE): cột = giá trị mới hoặc NULL — đảm bảo
    bất biến parity sau mọi lần ghi. Chạy trên CHÍNH connection/transaction của
    caller (upsert_entity/_bulk_load) — nguyên tử cùng lần ghi entity.
    """
    uni, det, _skipped = split_typed(etype, attrs)
    ph = "%s" if is_pg else "?"

    # 1) 8 cột phổ quát trên entities — luôn set đủ 8 (giá trị hoặc NULL).
    sets = ", ".join(f"{c} = {ph}" for c in UNIVERSAL)
    _exec(conn, is_pg, f"UPDATE entities SET {sets} WHERE id = {ph}",
          [uni.get(c) for c in UNIVERSAL] + [entity_id])

    # 2) Bảng CTI của kind (nếu có).
    kind = KIND_OF_TYPE.get(etype)
    table = KIND_TABLE.get(kind or "")
    if not table:
        return
    cols = KIND_COLUMNS[kind]
    if not det:
        _exec(conn, is_pg, f"DELETE FROM {table} WHERE entity_id = {ph}", [entity_id])
        _cache_put(entity_id, None)
        return
    values = [_db_value(c, det.get(c), is_pg) for c in cols]
    collist = ", ".join(cols)
    phs = ", ".join([ph] * (len(cols) + 1))
    if is_pg:
        updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in cols)
        sql = (f"INSERT INTO {table} (entity_id, {collist}) VALUES ({phs}) "
               f"ON CONFLICT (entity_id) DO UPDATE SET {updates}")
    else:
        sql = f"INSERT OR REPLACE INTO {table} (entity_id, {collist}) VALUES ({phs})"
    _exec(conn, is_pg, sql, [entity_id, *values])
    _cache_put(entity_id, det)


def delete_entity_details(conn, is_pg: bool, entity_id: str) -> None:
    """Dọn detail rows khi xoá entity. PG có FK CASCADE nhưng SQLite dev thường
    không bật PRAGMA foreign_keys — dọn tường minh cho chắc cả hai."""
    ph = "%s" if is_pg else "?"
    for table in KIND_TABLE.values():
        _exec(conn, is_pg, f"DELETE FROM {table} WHERE entity_id = {ph}", [entity_id])
    _cache_put(entity_id, None)


def _sqlite_type(col: str) -> str:
    if col in INT_COLUMNS:
        return "INTEGER"
    if col in NUMERIC_COLUMNS:
        return "REAL"
    if col in BOOL_COLUMNS:
        return "INTEGER"
    return "TEXT"  # JSONB_COLUMNS lưu JSON text trên SQLite


# ── C3: strip typed keys khỏi JSONB (cột là nguồn sự thật duy nhất) ─────────

def mapped_keys(etype: str, attrs: dict | None) -> set[str]:
    """Các key GỐC trong attrs đã được split_typed ánh xạ thành công vào cột
    (uni + det). Key uncoercible/tail KHÔNG nằm trong đây."""
    uni, det, _ = split_typed(etype, attrs or {})
    out = set(uni.keys())
    schema = ENTITY_SCHEMAS.get(etype) or {"fields": []}
    for f in schema["fields"]:
        key = f["key"]
        if key in (attrs or {}) and KEY_MAP.get(key, key) in det:
            out.add(key)
    return out


def strip_synced_keys(etype: str, attrs: dict | None) -> dict:
    """JSONB lưu trữ = attrs TRỪ các key đã sync vào cột (đường GHI, cùng
    transaction với sync nên cột chắc chắn khớp). Tail + uncoercible ở lại."""
    attrs = attrs or {}
    synced = mapped_keys(etype, attrs)
    return {k: v for k, v in attrs.items() if k not in synced}


def norm_value(v: Any) -> Any:
    """Chuẩn hoá để so sánh cột ↔ JSONB (cleanup so-sánh-trước-khi-xoá)."""
    if v is None:
        return None
    if isinstance(v, Decimal):
        v = float(v)
    if isinstance(v, float) and v.is_integer():
        return int(v)
    if isinstance(v, str):
        return v.strip()
    return v


# ── C2: flip ĐỌC sau flag ENTITY_DETAILS_TABLES ─────────────────────────────
# Cache detail-rows nạp 1 lần lúc initialize (9 bảng ~1.6k dòng, vài trăm KB);
# sync/delete giữ cache tươi khi ghi. Đổi flag = restart service (chuẩn env var).

_DETAIL_CACHE: dict[str, dict] | None = None

_SCHEMA_KEYS: dict[str, list[str]] = {
    etype: [f["key"] for f in schema["fields"]]
    for etype, schema in ENTITY_SCHEMAS.items()
}


def reads_enabled() -> bool:
    return os.environ.get("ENTITY_DETAILS_TABLES", "").strip().lower() in ("1", "true", "yes", "on")


def reset_detail_cache() -> None:
    global _DETAIL_CACHE
    _DETAIL_CACHE = None


def _norm_col_value(col: str, v: Any) -> Any:
    if v is None:
        return None
    if col in BOOL_COLUMNS:
        return bool(v)
    if col in JSONB_COLUMNS and isinstance(v, str):
        try:
            return json.loads(v)
        except (json.JSONDecodeError, ValueError):
            return None
    if isinstance(v, Decimal):
        f = float(v)
        return int(f) if f.is_integer() else f
    return v


def load_detail_cache(conn, is_pg: bool) -> int:
    """Nạp toàn bộ 9 bảng CTI vào cache {entity_id: {col: giá_trị_python}}."""
    global _DETAIL_CACHE
    cache: dict[str, dict] = {}
    for table in KIND_TABLE.values():
        if is_pg:
            cur = conn.cursor()
            cur.execute(f"SELECT * FROM {table}")
            raw_rows = cur.fetchall()
            cols = [c[0] for c in cur.description]
            rows = [r if isinstance(r, dict) else dict(zip(cols, r)) for r in raw_rows]
        else:
            fetched = conn.execute(f"SELECT * FROM {table}").fetchall()
            rows = [{k: r[k] for k in r.keys()} for r in fetched]
        for r in rows:
            eid = r.pop("entity_id")
            cache[eid] = {c: _norm_col_value(c, v) for c, v in r.items() if v is not None}
    _DETAIL_CACHE = cache
    return len(cache)


def _cache_put(entity_id: str, det: dict | None) -> None:
    """sync/delete gọi để giữ cache tươi (det = giá trị python từ split_typed)."""
    if _DETAIL_CACHE is None:
        return
    if det:
        _DETAIL_CACHE[entity_id] = dict(det)
    else:
        _DETAIL_CACHE.pop(entity_id, None)


def rebuild_attributes(etype: str, attrs: Any, entity_row: dict) -> Any:
    """Flag ON: dựng lại attributes — CỘT THẮNG khi có giá trị; fallback JSONB thô
    (bảo toàn giá trị uncoercible như 'Thế kỷ 19'); tail (bespoke + KBYG) nguyên
    vẹn; giữ đúng thứ tự key gốc. Legacy string-số ("4") được chuẩn hoá kiểu
    theo cột (4) — thay đổi chủ đích, ghi trong spec."""
    if not isinstance(attrs, dict):
        return attrs
    schema_keys = _SCHEMA_KEYS.get(etype)
    if not schema_keys:
        return attrs
    detail = (_DETAIL_CACHE or {}).get(entity_row.get("id") or "", {})

    def col_value(key: str) -> Any:
        if key in UNIVERSAL:
            return entity_row.get(key)
        return detail.get(KEY_MAP.get(key, key))

    key_set = set(schema_keys)
    out: dict = {}
    for k, v in attrs.items():
        if k in key_set:
            cv = col_value(k)
            out[k] = cv if cv is not None else v
        else:
            out[k] = v
    for k in schema_keys:  # key chỉ có ở cột (thế giới hậu-C3 sau khi dọn JSONB)
        if k not in out:
            cv = col_value(k)
            if cv is not None:
                out[k] = cv
    return out


def ensure_schema_sqlite(conn) -> None:
    """DDL parity cho dev SQLite: 8 cột phổ quát trên entities (ALTER nếu thiếu)
    + 9 bảng CTI (CREATE IF NOT EXISTS). PG KHÔNG đi qua đây — migrations sở hữu."""
    existing = {row[1] for row in conn.execute("PRAGMA table_info(entities)")}
    for col in UNIVERSAL:
        if col not in existing:
            conn.execute(f"ALTER TABLE entities ADD COLUMN {col} TEXT")
    for kind, table in KIND_TABLE.items():
        cols_ddl = ",\n    ".join(f"{c} {_sqlite_type(c)}" for c in KIND_COLUMNS[kind])
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {table} (
                entity_id TEXT PRIMARY KEY REFERENCES entities(id) ON DELETE CASCADE,
                {cols_ddl}
            )""")
