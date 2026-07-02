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
