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
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agent"))

import database

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
MIG_072 = (ROOT / "agent" / "migrations" / "072_feedback_receipts.sql").read_text(encoding="utf-8")
MIG_073 = (ROOT / "agent" / "migrations" / "073_account_erasure_state.sql").read_text(encoding="utf-8")
MIG_074_PATH = ROOT / "agent" / "migrations" / "074_erasure_delete_actions.sql"
MIG_074 = MIG_074_PATH.read_text(encoding="utf-8") if MIG_074_PATH.exists() else ""
MIG_080_PATH = ROOT / "agent" / "migrations" / "080_correction_case_kernel.sql"
MIG_080 = MIG_080_PATH.read_text(encoding="utf-8") if MIG_080_PATH.exists() else ""

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


def test_072_feedback_receipts_are_digest_only_and_owner_clearable():
    block = _create_block(MIG_072, "feedback_receipts")
    normalized = " ".join(block.split())
    for column in (
        "token_digest",
        "owner_kind",
        "user_id",
        "anonymous_owner_digest",
        "owner_binding_digest",
        "assistant_turn_digest",
        "model_variant",
        "tool_bucket",
        "rating",
        "created_at",
        "expires_at",
        "used_at",
    ):
        assert column in block
    for forbidden in ("query", "reply", "entity_id", "session_id"):
        assert forbidden not in block
    assert "ON DELETE CASCADE" in block
    assert "used_at IS NOT NULL" in block
    assert "user_id IS NULL AND anonymous_owner_digest IS NULL" in normalized


def test_072_rollup_and_indexes_are_bounded():
    block = _create_block(MIG_072, "feedback_daily_rollups")
    assert "UNIQUE (day, owner_kind, model_variant, tool_bucket)" in block
    assert "positive_count" in block
    assert "negative_count" in block
    for index_name in (
        "idx_feedback_receipts_token_digest",
        "idx_feedback_receipts_expires",
        "idx_feedback_receipts_user",
        "idx_feedback_receipts_anonymous",
        "idx_feedback_receipts_owner_binding",
    ):
        assert index_name in MIG_072
    assert "VALUES ('agent', 72," in MIG_072


def test_init_sql_contains_final_feedback_schema():
    assert "CREATE TABLE IF NOT EXISTS feedback_receipts" in INIT_SQL
    assert "CREATE TABLE IF NOT EXISTS feedback_daily_rollups" in INIT_SQL


def test_database_readiness_requires_erasure_schema_version_74():
    # Tên hàm giữ nguyên (74 = mốc erasure) nhưng NGƯỠNG đã tiến: hợp NP-1 vào main
    # thêm migration 076-078, 079 planner revision, 080 Case Kernel, 081 vòng đời
    # change set và 082 CHECK vị-trí nhận chữ số Unicode.
    assert database.PG_REQUIRED_SCHEMA_VERSION == 84
    assert {"feedback_receipts", "feedback_daily_rollups"} <= database.PG_REQUIRED_TABLES
    assert {
        "token_digest",
        "owner_kind",
        "owner_binding_digest",
        "assistant_turn_digest",
        "expires_at",
    } <= database.PG_REQUIRED_COLUMNS["feedback_receipts"]
    assert {
        "day",
        "owner_kind",
        "model_variant",
        "tool_bucket",
        "positive_count",
        "negative_count",
    } <= database.PG_REQUIRED_COLUMNS["feedback_daily_rollups"]


def test_073_adds_bounded_erasure_metadata_without_backfill():
    """Migration replay must add lifecycle state without inventing legacy dates."""
    for column in (
        "erasure_due_at TIMESTAMPTZ",
        "erasure_attempt_count INTEGER NOT NULL DEFAULT 0",
        "erasure_last_attempt_at TIMESTAMPTZ",
        "erasure_last_error_code TEXT",
    ):
        assert f"ADD COLUMN IF NOT EXISTS {column}" in MIG_073
    assert "erasure_attempt_count >= 0" in MIG_073
    for code in (
        "STORE_UNAVAILABLE",
        "RESIDUAL_DATA",
        "DB_CONSTRAINT",
        "VERIFY_FAILED",
    ):
        assert code in MIG_073
    assert "idx_users_erasure_due" in MIG_073
    assert "WHERE deleted_at IS NOT NULL AND erasure_due_at IS NOT NULL" in MIG_073
    assert not re.search(r"\bUPDATE\s+users\b", MIG_073, re.I)
    assert "VALUES ('agent', 73," in MIG_073


def test_init_sql_contains_final_account_erasure_state():
    """A fresh schema must expose the same columns and bounds as migration 073."""
    block = _create_block(INIT_SQL, "users")
    for column in (
        "deleted_at",
        "erasure_due_at",
        "erasure_attempt_count",
        "erasure_last_attempt_at",
        "erasure_last_error_code",
    ):
        assert column in block
    assert "erasure_attempt_count >= 0" in block
    assert "idx_users_erasure_due" in INIT_SQL


def test_074_registers_replay_safe_erasure_fk_policy():
    assert "ALTER TABLE" in MIG_074
    assert "ON DELETE CASCADE" in MIG_074
    assert "ON DELETE SET NULL" in MIG_074
    assert "completed_claim_scrub" in MIG_074
    assert "VALUES ('agent', 74," in MIG_074
    assert "DROP TABLE" not in MIG_074.upper()
    assert "TRUNCATE" not in MIG_074.upper()
    assert "DELETE FROM" not in MIG_074.upper()


def test_074_clears_non_nullable_actor_and_claim_fields_before_scrub():
    normalized = " ".join(MIG_074.split())
    for table, column in (
        ("post_edit_history", "editor_id"),
        ("admin_user_notes", "admin_id"),
        ("entity_claims", "claimant_id"),
        ("entity_claims", "business_name"),
        ("entity_claims", "contact_phone"),
        ("moderation_appeals", "user_id"),
        ("moderation_log", "target_id"),
        ("admin_audit_events", "actor"),
    ):
        assert f"ALTER COLUMN {column} DROP NOT NULL" in normalized, (
            f"074 must make {table}.{column} nullable for exact actor/claim scrubbing"
        )


CASE_TABLES = {
    "cases", "case_interactions", "case_party_authorities", "case_work_items",
    "case_decisions", "case_promise_clocks", "case_receipts", "case_access_sessions",
    "case_admin_access_sessions", "case_transitions", "case_audit_events", "case_outbox",
    "case_idempotency", "case_contact_challenges", "correction_items", "correction_evidence",
    "correction_change_sets", "correction_change_set_items", "legacy_intake_records", "case_capacity_events",
}


def test_080_is_additive_replay_safe_and_registers_schema_version():
    assert MIG_080_PATH.exists(), "migration 080 must exist"
    assert "DROP TABLE" not in MIG_080.upper()
    assert "TRUNCATE" not in MIG_080.upper()
    assert "DELETE FROM" not in MIG_080.upper()
    assert "VALUES ('agent', 80, '080_correction_case_kernel.sql'" in MIG_080
    assert "GREATEST(schema_version.version, EXCLUDED.version)" in MIG_080
    for table in CASE_TABLES:
        assert f"CREATE TABLE IF NOT EXISTS {table}" in MIG_080


def test_080_uses_digest_or_ciphertext_names_for_private_payloads():
    for forbidden in ("capability TEXT", "contact TEXT", "evidence TEXT", "capability_digest BYTEA"):
        assert forbidden not in MIG_080
    assert "capability_digest" in MIG_080
    assert "*_enc" not in MIG_080  # wildcard is documentation, concrete names are required
    assert "payload_enc" in MIG_080
    assert "content_enc" in MIG_080


def test_080_receipt_security_columns_have_replay_safe_contracts():
    for source in (MIG_080, INIT_SQL):
        assert "receipt_revision INTEGER NOT NULL" in source
        assert "subject_user_id TEXT" in source
        assert "session_key_version TEXT NOT NULL" in source
        assert "response_key_version TEXT NOT NULL" in source
        assert "UNIQUE (case_id, receipt_revision)" in source
        assert "case_receipts_receipt_revision_positive" in source


def test_init_sql_contains_case_kernel_parity_and_entity_revision():
    for table in CASE_TABLES:
        assert f"CREATE TABLE IF NOT EXISTS {table}" in INIT_SQL
    assert "ADD COLUMN IF NOT EXISTS revision" in MIG_080
    entities = _create_block(INIT_SQL, "entities")
    assert re.search(r"\brevision\s+INTEGER\s+NOT NULL\s+DEFAULT\s+1", entities, re.I)
    assert "entities_revision_positive" in INIT_SQL


def test_database_readiness_requires_case_schema_version_81():
    # 081 is part of the kernel contract, not an optional follow-up: without it
    # a published correction can never be marked as published. (Ngưỡng đã tiến
    # lên 82 — unicode-digit CHECK — nhưng hợp đồng kernel của test này giữ nguyên.)
    assert database.PG_REQUIRED_SCHEMA_VERSION == 84
    assert CASE_TABLES <= database.PG_REQUIRED_TABLES
    assert {"revision"} <= database.PG_REQUIRED_COLUMNS["entities"]
    assert {"case_id", "current_revision", "service_kind", "phase"} <= database.PG_REQUIRED_COLUMNS["cases"]


def test_dormant_core_contract_excludes_case_revision_but_enabled_contract_requires_it():
    assert "revision" not in database.PG_CORE_REQUIRED_COLUMNS["entities"]
    assert "revision" in database.CASE_KERNEL_REQUIRED_COLUMNS["entities"]
    assert "severity" in database.CASE_KERNEL_REQUIRED_COLUMNS["cases"]


def test_080_binds_case_vocabularies_and_relational_change_set_linkage():
    outcome = re.search(r"outcome_code TEXT NOT NULL CHECK \(outcome_code IN \(([^)]*)\)\)", MIG_080)
    assert outcome
    assert set(re.findall(r"'([^']+)'", outcome.group(1))) == {
        "corrected", "confirmed_current", "insufficient_evidence", "out_of_scope",
        "duplicate_linked", "unable_to_verify", "withdrawn_by_requester",
    }
    assert "resolved" not in MIG_080 and "dismissed" not in MIG_080
    assert "from_phase TEXT" in MIG_080 and "to_phase TEXT NOT NULL CHECK" in MIG_080
    assert "correction_change_set_items" in MIG_080
    assert "item_ids JSONB" not in MIG_080
    assert "correction_items_linked_case_immutable" in MIG_080


def test_073_owns_location_remediation_contract():
    migration = ROOT / "agent" / "migrations" / "078_location_preference_remediation.sql"
    sql = migration.read_text(encoding="utf-8")

    assert "location_reconfirm_required" in sql
    assert "location_provenance_version" in sql
    assert "location-confirmation" not in sql
    assert "resolver-v2" in sql
    # 73 -> 78: migration nay duoc danh so lai khi hop NP-1 vao main (071-073 da bi dung).
    assert "VALUES ('agent', 78," in sql
    assert "CREATE TABLE" not in sql
