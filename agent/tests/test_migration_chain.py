"""Tests GĐ-B bước 0: sửa chuỗi migration (audit 2026-07-02 top-risk #3).

Bảo vệ 3 chỗ đứt đã sửa:
  (1) init.sql tự bootstrap được: cột posts.deleted_at phải nằm TRONG CREATE TABLE
      vì index idx_posts_review_entity_recent_public cùng file tham chiếu nó.
  (2) migration 059 heal entity_claims (037 bị 029 che khi replay).
  (3) migration 059 sở hữu entity_changes + site_settings_history (trước đó chỉ
      được tạo runtime trong code — vô hình với replay).
Replay thật trên PG trắng là verify chính (chạy thủ công/CI); test này là guard rẻ.
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
INIT_SQL = (ROOT / "init.sql").read_text(encoding="utf-8")
MIG_059 = (ROOT / "agent" / "migrations" / "059_repair_migration_chain.sql").read_text(encoding="utf-8")


def _create_block(sql: str, table: str) -> str:
    m = re.search(rf"CREATE TABLE IF NOT EXISTS {table}\s*\((.*?)\n\);", sql, re.S)
    assert m, f"Không tìm thấy CREATE TABLE {table}"
    return m.group(1)


def test_init_sql_posts_has_deleted_at_in_create():
    block = _create_block(INIT_SQL, "posts")
    assert "deleted_at" in block, (
        "posts.deleted_at phải nằm trong CREATE TABLE của init.sql — index "
        "idx_posts_review_entity_recent_public tham chiếu nó ngay trong file"
    )


def test_init_sql_posts_index_dependency_satisfied():
    # Index dùng cột nào trong WHERE thì cột đó phải có trong CREATE block.
    idx = re.search(r"idx_posts_review_entity_recent_public.*?;", INIT_SQL, re.S)
    assert idx, "Thiếu index idx_posts_review_entity_recent_public"
    block = _create_block(INIT_SQL, "posts")
    for col in ("post_type", "moderation_status", "deleted_at", "entity_id", "created_at"):
        assert col in block, f"Cột {col} được index tham chiếu nhưng thiếu trong CREATE posts"


def test_059_heals_entity_claims():
    assert "ALTER TABLE entity_claims ADD COLUMN IF NOT EXISTS reviewer_note" in MIG_059
    assert "idx_entity_claims_entity_claimant" in MIG_059
    assert "entity_id, claimant_id" in MIG_059


def test_059_owns_code_created_tables():
    assert "CREATE TABLE IF NOT EXISTS entity_changes" in MIG_059
    assert "CREATE TABLE IF NOT EXISTS site_settings_history" in MIG_059
    # PG dialect — không lọt DDL SQLite
    assert "AUTOINCREMENT" not in MIG_059
    assert "BIGSERIAL" in MIG_059
    # Bài học ownership (deploy gotcha): bảng mới phải ALTER OWNER TO vl360
    assert MIG_059.count("OWNER TO vl360") >= 2


def test_059_records_schema_version_59_monotonic():
    assert "VALUES ('agent', 59," in MIG_059
    assert "GREATEST(schema_version.version, EXCLUDED.version)" in MIG_059


# ── GĐ-B: 060 cột phổ quát + 061 bảng CTI ──────────────────────────────────
MIG_060 = (ROOT / "agent" / "migrations" / "060_entity_universal_columns.sql").read_text(encoding="utf-8")
MIG_061 = (ROOT / "agent" / "migrations" / "061_entity_detail_tables.sql").read_text(encoding="utf-8")

UNIVERSAL = ["address", "phone", "website", "hours", "price_range", "sub_category", "best_time", "highlight"]
CTI_TABLES = [
    "entity_place_details", "entity_food_details", "entity_product_details",
    "entity_lodging_details", "entity_event_details", "entity_experience_details",
    "entity_facility_details", "entity_person_details", "entity_adminplace_details",
]
# Ánh xạ khóa registry -> tên cột khác (phải khớp comment trong 061 + backfill script)
KEY_TO_COLUMN = {"view": "view_note", "architectural_style": "architecture_style"}


def test_060_adds_all_universal_columns():
    for col in UNIVERSAL:
        assert f"ADD COLUMN IF NOT EXISTS {col}" in MIG_060, f"060 thiếu cột {col}"
    assert "VALUES ('agent', 60," in MIG_060


def test_061_has_9_cti_tables_with_fk_and_owner():
    for t in CTI_TABLES:
        assert f"CREATE TABLE IF NOT EXISTS {t}" in MIG_061, f"061 thiếu bảng {t}"
        assert f"ALTER TABLE {t} OWNER TO vl360" in MIG_061, f"061 thiếu OWNER cho {t}"
    assert MIG_061.count("REFERENCES entities(id) ON DELETE CASCADE") == len(CTI_TABLES)
    assert "VALUES ('agent', 61," in MIG_061


def test_registry_typed_fields_have_column_in_right_table():
    """Mọi trường typed trong registry (trừ 8 cột phổ quát) phải có cột trong
    ĐÚNG bảng CTI của kind — kiểm per-table (containment toàn file từng che mất
    việc entity_experience_details thiếu `admission` vì bảng place cũng có nó).
    Nguồn schema = 061 + các migration vá sau (062+)."""
    import sys
    sys.path.insert(0, str(ROOT / "agent"))
    from entity_schemas import ENTITY_SCHEMAS, KIND_OF_TYPE
    kind_to_table = {
        "place": "entity_place_details", "food": "entity_food_details",
        "product": "entity_product_details", "lodging": "entity_lodging_details",
        "event": "entity_event_details", "experience": "entity_experience_details",
        "facility": "entity_facility_details", "person": "entity_person_details",
        "admin_place": "entity_adminplace_details",
    }
    # Gom schema hiệu lực của từng bảng: CREATE block trong 061 + mọi
    # "ALTER TABLE <t> ADD COLUMN" trong các migration >= 062.
    later = "".join(
        p.read_text(encoding="utf-8")
        for p in sorted((ROOT / "agent" / "migrations").glob("*.sql"))
        if p.name[:3].isdigit() and int(p.name[:3]) >= 62
    )
    table_cols: dict[str, str] = {}
    for t in kind_to_table.values():
        block = re.search(rf"CREATE TABLE IF NOT EXISTS {t}\s*\((.*?)\n\);", MIG_061, re.S)
        assert block, f"061 thiếu bảng {t}"
        alters = "".join(re.findall(rf"ALTER TABLE {t} ADD COLUMN IF NOT EXISTS (\w+)", later))
        table_cols[t] = block.group(1) + " " + alters
    universal = set(UNIVERSAL)
    for etype, schema in ENTITY_SCHEMAS.items():
        kind = KIND_OF_TYPE.get(etype)
        if kind not in kind_to_table:
            continue  # itinerary có bảng riêng; other (organization/economy) chỉ dùng bộ chung
        for f in schema["fields"]:
            key = f["key"]
            if key in universal:
                continue
            col = KEY_TO_COLUMN.get(key, key)
            assert re.search(rf"\b{col}\b", table_cols[kind_to_table[kind]]), \
                f"Bảng {kind_to_table[kind]} thiếu cột {col} (registry {etype}.{key})"
