"""
vinhlong360 — Database Layer (PostgreSQL + SQLite fallback).

Supports PostgreSQL (production) via psycopg2 and SQLite (dev) as fallback.
Backend is selected by DATABASE_URL env var:
  - Set → PostgreSQL (postgresql://user:pass@host/db)
  - Not set → SQLite at agent/data/vinhlong360.db

Usage:
  from database import db
  db.search_entities(q="cam", area="vinh-long")
  db.upsert_entity({...})
"""

import json
import logging
import math
import os
import sqlite3
import time
from collections.abc import Mapping
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from config import is_postgresql_url

logger = logging.getLogger(__name__)


class PostCommitMutationError(RuntimeError):
    """A mutation committed, but a best-effort post-commit effect failed."""

    committed = True

    def __init__(self, effect: str, cause: Exception) -> None:
        super().__init__(f"post_commit_{effect}_failed")
        self.effect = effect
        self.cause = cause

# ── Config ──

DB_DIR = Path(__file__).resolve().parent / "data"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "vinhlong360.db"

DATABASE_URL = os.getenv("DATABASE_URL", "")
USE_PG = is_postgresql_url(DATABASE_URL)

RELATIONSHIP_TYPE_PRIORITY = {
    "hosts": 0,
    "offered_by": 1,
    "supplies_to": 2,
    "produced_in": 3,
    "associated_with": 4,
    "related_to": 5,
    "near": 9,
}

import entity_details as _entity_details
import entity_write as _entity_write
from control_plane.snapshot import bump_generation, invalidate_entity

PG_REQUIRED_TABLES = {
    "entities",
    "relationships",
    "itineraries",
    "users",
    "posts",
    "moderation_appeals",
    "comments",
    "saved_entities",
    "site_settings",
    "schema_version",
    "admin_audit_events",
    "shared_rate_limits",
    "request_idempotency_keys",
    "quality_metric_snapshots",
    "feedback_receipts",
    "feedback_daily_rollups",
    # NP-1 identity/location/trust (migration 076-078)
    "user_preferences",
    "user_preference_consents",
    "user_personalization_events",
    "personalization_legacy_purge_queue",
    # GĐ-B/C entity split (migration 059-062)
    "entity_changes",
    "site_settings_history",
    "entity_place_details",
    "entity_food_details",
    "entity_product_details",
    "entity_lodging_details",
    "entity_event_details",
    "entity_experience_details",
    "entity_facility_details",
    "entity_person_details",
    "entity_adminplace_details",
    # Tính năng tài khoản đã ship (migration 063-067). Thiếu nhóm này thì
    # health-check vẫn xanh nhưng 2FA/thiết bị tin cậy/huy hiệu vỡ ngay lần
    # gọi đầu — riêng 2FA là deploy gate, hỏng là khoá người dùng ra ngoài.
    "user_2fa",
    "pending_2fa",
    "user_2fa_recovery_codes",
    "trusted_devices",
    "achievements",
    "user_achievements",
    "profile_views",
    "entity_snapshot_generation",
    "media_delete_receipts",
    "browser_clear_instructions",
}

CASE_KERNEL_REQUIRED_TABLES = {
    "cases", "case_interactions", "case_party_authorities", "case_work_items",
    "case_decisions", "case_promise_clocks", "case_receipts", "case_access_sessions",
    "case_admin_access_sessions", "case_transitions", "case_audit_events", "case_outbox",
    "case_idempotency", "case_contact_challenges", "correction_items", "correction_evidence",
    "correction_change_sets", "correction_change_set_items", "legacy_intake_records", "case_capacity_events",
}
PG_REQUIRED_TABLES |= CASE_KERNEL_REQUIRED_TABLES
PG_CORE_REQUIRED_TABLES = PG_REQUIRED_TABLES - CASE_KERNEL_REQUIRED_TABLES

PG_REQUIRED_COLUMNS = {
    "entities": {"id", "type", "name", "status", "verified", "coordinates", "attributes", "images"},
    "itineraries": {"id", "title", "area", "areas", "stops"},
    "users": {"id", "phone", "password_hash", "username", "role", "is_active"},
    "posts": {"id", "user_id", "entity_id", "content", "moderation_status", "deleted_at", "is_draft", "revision", "claimed_by", "claim_expires_at", "publish_attempts", "last_error_code"},
    "moderation_appeals": {"id", "post_id", "user_id", "status", "revision", "claimed_by", "claim_expires_at", "last_error_code"},
    "saved_entities": {"id", "user_id", "entity_id", "kind", "snapshot", "created_at"},
    "admin_audit_events": {"actor", "actor_scopes", "request_id", "before_json", "after_json"},
    "shared_rate_limits": {"key", "hits", "expires_at", "updated_at"},
    "request_idempotency_keys": {"key", "first_seen_at", "expires_at", "meta"},
    "quality_metric_snapshots": {"metric_key", "metric_value", "created_at"},
    "feedback_receipts": {
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
    },
    "feedback_daily_rollups": {
        "day",
        "owner_kind",
        "model_variant",
        "tool_bucket",
        "positive_count",
        "negative_count",
    },
    "user_preferences": {
        "user_id", "region_id", "region_label", "region_scope",
        "location_source", "location_accuracy", "location_consent_state",
        "location_enabled", "personalization_enabled", "explicit_interests",
        "recommendation_reset_at", "consent_version", "revision",
        "location_reconfirm_required", "location_provenance_version",
        "created_at", "updated_at",
    },
    "user_preference_consents": {
        "id", "user_id", "consent_type", "state", "version", "created_at",
    },
    "user_personalization_events": {
        "id", "user_id", "event_type", "context", "entity_id",
        "entity_type", "area_id", "interest_keys", "occurred_at", "expires_at",
    },
    "personalization_legacy_purge_queue": {
        "user_id", "created_at", "attempt_count", "next_attempt_at", "last_error",
    },
    "schema_version": {"component", "version", "migration", "updated_at"},
    "entity_snapshot_generation": {"entity_id", "generation", "issued_at"},
    "media_delete_receipts": {"subject_id", "object_key", "generation", "status", "object_status", "cdn_status", "error", "updated_at"},
    "browser_clear_instructions": {"issuance_id", "subject_hash", "instruction_json", "issued_at"},
}

CASE_KERNEL_REQUIRED_COLUMNS = {
    "entities": {"revision"},
    "cases": {"case_id", "service_kind", "category", "phase", "activity", "disposition_family", "domain_outcome", "severity", "reporter_privacy", "owner_ref", "current_revision", "promise_policy_ref", "review_of_case_id", "created_at", "updated_at", "closed_at"},
    "case_interactions": {"interaction_id", "case_id", "channel", "actor_ref", "direction", "consent_ref", "identity_assurance", "payload_enc", "created_at"},
    "case_party_authorities": {"party_authority_id", "case_id", "party_ref", "authority_kind", "scope", "assurance_level", "granted_at", "expires_at", "revoked_at"},
    "case_work_items": {"work_item_id", "case_id", "kind", "required_role", "risk_class", "status", "assignee_ref", "lease_expires_at", "ready_at", "next_review_at", "priority", "revision"},
    "case_decisions": {"decision_id", "case_id", "item_id", "outcome_code", "reason_code", "evidence_refs", "decision_maker_ref", "reviewer_ref", "decided_at", "policy_revision"},
    "case_promise_clocks": {"clock_id", "case_id", "kind", "started_at", "due_at", "health", "policy_revision", "observed_at"},
    "case_receipts": {"receipt_id", "case_id", "public_reference", "capability_digest", "capability_key_version", "receipt_revision", "subject_user_id", "notification_consent_ref", "expires_at", "revoked_at", "created_at"},
    "case_access_sessions": {"access_session_id", "case_id", "receipt_id", "session_digest", "session_key_version", "expires_at", "revoked_at", "created_at"},
    "case_admin_access_sessions": {"admin_access_session_id", "case_id", "actor_ref", "scope", "session_digest", "expires_at", "revoked_at", "created_at"},
    "case_transitions": {"transition_id", "case_id", "from_phase", "to_phase", "from_revision", "to_revision", "actor_ref", "reason_code", "policy_revision", "correlation_id", "created_at"},
    "case_audit_events": {"audit_event_id", "case_id", "actor_ref", "actor_scopes", "channel", "reason_code", "policy_revision", "correlation_id", "before_snapshot", "after_snapshot", "created_at"},
    "case_outbox": {"outbox_id", "case_id", "idempotency_key", "topic", "payload", "status", "available_at", "attempts", "last_error_code", "created_at"},
    "case_idempotency": {"idempotency_id", "idempotency_key", "actor_ref", "request_digest", "response_enc", "response_key_version", "expires_at", "created_at"},
    "case_contact_challenges": {"challenge_id", "case_id", "contact_digest", "challenge_digest", "channel", "expires_at", "verified_at", "created_at"},
    "correction_items": {"item_id", "case_id", "entity_id", "field_path", "reported_value_enc", "proposed_value_enc", "base_entity_revision", "risk_class", "evidence_level", "created_at"},
    "correction_evidence": {"evidence_id", "case_id", "item_id", "evidence_level", "source_ref", "descriptor", "content_enc", "created_by_ref", "created_at"},
    "correction_change_sets": {"change_set_id", "case_id", "base_entity_revision", "before_patch", "after_patch", "inverse_patch", "evidence_refs", "policy_revision", "risk_class", "decision_maker_ref", "reviewer_ref", "apply_status", "public_projection_verified_at", "created_at"},
    "correction_change_set_items": {"change_set_id", "item_id", "created_at"},
    "legacy_intake_records": {"legacy_intake_id", "source_file", "source_line", "raw_record_digest", "imported_case_id", "legacy_status", "missing_data_flags", "mapping_decision", "import_result", "reconciliation_result", "imported_at"},
    "case_capacity_events": {"capacity_event_id", "case_id", "channel", "risk_class", "event_kind", "observed_at", "duration_seconds", "metadata"},
}
for _table, _columns in CASE_KERNEL_REQUIRED_COLUMNS.items():
    PG_REQUIRED_COLUMNS.setdefault(_table, set()).update(_columns)
PG_CORE_REQUIRED_COLUMNS = {
    table: columns - CASE_KERNEL_REQUIRED_COLUMNS.get(table, set())
    for table, columns in PG_REQUIRED_COLUMNS.items()
    if columns - CASE_KERNEL_REQUIRED_COLUMNS.get(table, set())
}

# 80 adds the PostgreSQL-only Correction Case Kernel and entity revision guard.
# 82 dạy vl360_region_text_is_safe nhận chữ số Unicode (§48.4) + quarantine tồn đọng.
# 83 adds the durable entity snapshot generation table used by cache consumers.
# 84 closes community moderation/scheduled state with durable CAS fields.
# Media/browser lifecycle receipts are part of the release readiness contract;
# older deployments must apply migration 085 before starting this release.
PG_REQUIRED_SCHEMA_VERSION = 85
PG_CORE_REQUIRED_SCHEMA_VERSION = 79
PG_REQUIRED_TRIGGERS = {
    "trg_entity_ratings": "posts",
    "trg_entity_ratings_del": "posts",
}
CASE_REQUIRED_INDEXES = {
    "case_receipts_case_revision_unique",
    "case_receipts_case_receipt_unique",
    "idx_case_access_sessions_expiry",
}
CASE_REQUIRED_FKS = {
    "case_access_sessions_case_receipt_fkey",
}
CASE_REQUIRED_TRIGGERS = {
    "case_access_sessions_same_case",
    "case_receipts_case_immutable",
}
CASE_REQUIRED_COLUMN_META = {
    ("case_receipts", "receipt_id"): ("uuid", "NO", "uuid_generate_v4"),
    ("case_receipts", "case_id"): ("uuid", "NO", None),
    ("case_receipts", "capability_digest"): ("text", "NO", None),
    ("case_receipts", "receipt_revision"): ("integer", "NO", "1"),
    ("case_access_sessions", "case_id"): ("uuid", "NO", None),
    ("case_access_sessions", "receipt_id"): ("uuid", "NO", None),
    ("case_access_sessions", "session_digest"): ("text", "NO", None),
    ("case_access_sessions", "session_key_version"): ("text", "NO", "v1"),
    ("case_idempotency", "response_key_version"): ("text", "NO", "v1"),
}

_CASE_REQUIRED_CONSTRAINT_DEFINITIONS = {
    "case_receipts_receipt_revision_positive": {
        "constraint_type": "c", "table_name": "case_receipts",
        "check_expression": "(receipt_revision>=1)",
    },
    "case_receipts_capability_digest_shape": {
        "constraint_type": "c", "table_name": "case_receipts",
        "check_expression": "(capability_digest~'^[0-9a-f]{64}$'::text)",
    },
    "case_receipts_expiry_order": {
        "constraint_type": "c", "table_name": "case_receipts",
        "check_expression": "(expires_at>created_at)",
    },
    "case_access_sessions_expiry_order": {
        "constraint_type": "c", "table_name": "case_access_sessions",
        "check_expression": "(expires_at>created_at)",
    },
    "case_idempotency_expiry_order": {
        "constraint_type": "c", "table_name": "case_idempotency",
        "check_expression": "(expires_at>created_at)",
    },
    "case_receipts_case_revision_unique": {
        "constraint_type": "u", "table_name": "case_receipts",
        "columns": ("case_id", "receipt_revision"),
    },
    "case_receipts_case_receipt_unique": {
        "constraint_type": "u", "table_name": "case_receipts",
        "columns": ("case_id", "receipt_id"),
    },
    "case_receipts_public_reference_key": {
        "constraint_type": "u", "table_name": "case_receipts",
        "columns": ("public_reference",),
    },
    "case_receipts_capability_digest_key": {
        "constraint_type": "u", "table_name": "case_receipts",
        "columns": ("capability_digest",),
    },
    "case_access_sessions_session_digest_key": {
        "constraint_type": "u", "table_name": "case_access_sessions",
        "columns": ("session_digest",),
    },
}
_CASE_REQUIRED_FK_DEFINITIONS = {
    "case_access_sessions_case_id_fkey": {
        "constraint_type": "f", "table_name": "case_access_sessions",
        "columns": ("case_id",), "target_table": "cases",
        "target_columns": ("case_id",), "delete_action": "c",
    },
    "case_access_sessions_receipt_id_fkey": {
        "constraint_type": "f", "table_name": "case_access_sessions",
        "columns": ("receipt_id",), "target_table": "case_receipts",
        "target_columns": ("receipt_id",), "delete_action": "c",
    },
    "case_access_sessions_case_receipt_fkey": {
        "constraint_type": "f", "table_name": "case_access_sessions",
        "columns": ("case_id", "receipt_id"), "target_table": "case_receipts",
        "target_columns": ("case_id", "receipt_id"), "delete_action": "c",
    },
}
# A same-named target in another namespace satisfies every other field, so the
# schema is part of the identity; NO ACTION on update keeps a case move from
# being propagated instead of rejected.
for _fk_definition in _CASE_REQUIRED_FK_DEFINITIONS.values():
    _fk_definition["target_schema"] = "public"
    _fk_definition["update_action"] = "a"
_CASE_REQUIRED_INDEX_DEFINITIONS = {
    "case_receipts_case_revision_unique": {
        "table_name": "case_receipts", "columns": ("case_id", "receipt_revision"),
        "predicate": None, "unique": True,
    },
    "case_receipts_case_receipt_unique": {
        "table_name": "case_receipts", "columns": ("case_id", "receipt_id"),
        "predicate": None, "unique": True,
    },
    "idx_case_access_sessions_expiry": {
        "table_name": "case_access_sessions", "columns": ("expires_at", "access_session_id"),
        "predicate": "(revoked_atisnull)", "unique": False,
    },
}
# Trigger identity is not the trigger row alone: a matching name can be paired
# with a no-op body, so the body is pinned here. Whitespace is normalised before
# comparison, which is what lets migration 080 and init.sql keep their own
# formatting; test_database.py asserts both sources still agree with these.
_CASE_TRIGGER_FUNCTION_BODIES = {
    "reject_case_receipt_case_move": (
        "BEGIN IF OLD.case_id IS DISTINCT FROM NEW.case_id THEN "
        "RAISE EXCEPTION 'case_receipt_case_immutable'; END IF; RETURN NEW; END;"
    ),
    "enforce_case_access_same_case": (
        "BEGIN IF NOT EXISTS (SELECT 1 FROM case_receipts "
        "WHERE receipt_id = NEW.receipt_id AND case_id = NEW.case_id) THEN "
        "RAISE EXCEPTION 'case_access_receipt_case_mismatch'; END IF; RETURN NEW; END;"
    ),
}
_CASE_REQUIRED_TRIGGER_DEFINITIONS = {
    "case_receipts_case_immutable": {
        "table_name": "case_receipts", "function_schema": "public",
        "function_name": "reject_case_receipt_case_move", "trigger_type": 19,
        "enabled": "O", "update_columns": ("case_id",), "when_expression": None,
        "function_body": _CASE_TRIGGER_FUNCTION_BODIES["reject_case_receipt_case_move"],
    },
    "case_access_sessions_same_case": {
        "table_name": "case_access_sessions", "function_schema": "public",
        "function_name": "enforce_case_access_same_case", "trigger_type": 23,
        "enabled": "O", "update_columns": (), "when_expression": None,
        "function_body": _CASE_TRIGGER_FUNCTION_BODIES["enforce_case_access_same_case"],
    },
}

if USE_PG:
    import psycopg2
    import psycopg2.extras


def escape_like(s: str) -> str:
    """Escape SQL LIKE wildcards so user input is treated as literal text."""
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


# Bbox vùng phục vụ — guard validate toạ độ geocode (chống khớp nhầm tỉnh khác).
# Mặc định = tỉnh Vĩnh Long mới (gộp VL + Bến Tre + Trà Vinh cũ). Bản clone cho tỉnh
# khác (dongthap360/cantho360/...) PHẢI đặt env REGION_BBOX, nếu không guard sẽ null-hoá
# TOÀN BỘ toạ độ của tỉnh đó.
REGION_BBOX_ENV = "REGION_BBOX"
_DEFAULT_REGION_BBOX = (9.2, 10.65, 105.6, 106.95)  # lat_min, lat_max, lng_min, lng_max
_REGION_BBOX_CACHE: tuple[str, tuple[float, float, float, float]] | None = None


def _parse_region_bbox(raw: str) -> tuple[float, float, float, float] | None:
    """Parse "lat_min,lat_max,lng_min,lng_max". None nếu sai định dạng/vô lý."""
    parts = [p.strip() for p in str(raw).split(",")]
    if len(parts) != 4:
        return None
    try:
        lat_min, lat_max, lng_min, lng_max = (float(p) for p in parts)
    except ValueError:
        return None
    if lat_min > lat_max or lng_min > lng_max:
        return None
    if not (-90.0 <= lat_min and lat_max <= 90.0 and -180.0 <= lng_min and lng_max <= 180.0):
        return None
    return (lat_min, lat_max, lng_min, lng_max)


def region_bbox() -> tuple[float, float, float, float]:
    """Bbox đang áp dụng: env REGION_BBOX nếu hợp lệ, không thì mặc định Vĩnh Long.

    Đọc env mỗi lần gọi (có cache theo chuỗi thô) thay vì chốt lúc import: guard này
    chạy trong upsert nên test/ops đổi env phải ăn ngay, không cần reload module.
    """
    global _REGION_BBOX_CACHE
    raw = os.environ.get(REGION_BBOX_ENV, "").strip()
    if not raw:
        return _DEFAULT_REGION_BBOX
    if _REGION_BBOX_CACHE is not None and _REGION_BBOX_CACHE[0] == raw:
        return _REGION_BBOX_CACHE[1]
    parsed = _parse_region_bbox(raw)
    if parsed is None:
        logger.warning(
            "%s=%r sai định dạng (cần 'lat_min,lat_max,lng_min,lng_max') → dùng mặc định %s",
            REGION_BBOX_ENV, raw, _DEFAULT_REGION_BBOX,
        )
        parsed = _DEFAULT_REGION_BBOX
    _REGION_BBOX_CACHE = (raw, parsed)
    return parsed


def _validate_place_level(entity: dict):
    """Auto-fix level khi name prefix mâu thuẫn — phòng lỗi sáp nhập 2026-06-15."""
    if entity.get("type") != "place":
        return
    name = entity.get("name", "")
    level = entity.get("level")
    if name.startswith("Phường ") and level == "xa":
        entity["level"] = "phuong"
    elif name.startswith("Xã ") and level == "phuong":
        entity["level"] = "xa"
    eid = entity.get("id", "")
    if eid.startswith("p-") and entity.get("level") == "xa":
        entity["level"] = "phuong"
    elif eid.startswith("xa-") and entity.get("level") == "phuong":
        entity["level"] = "xa"


def _normalize_itinerary_areas(value) -> list[str]:
    if isinstance(value, list):
        return [str(area) for area in value if area]
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    return []


def _coords_in_region(c) -> bool:
    """True nếu [lat, lng] nằm trong bbox vùng phục vụ. Ngoài vùng = geocode sai → loại."""
    if isinstance(c, dict):
        c = [c.get("lat", c.get("latitude")), c.get("lng", c.get("lon", c.get("longitude")))]
    try:
        lat, lng = float(c[0]), float(c[1])
    except (TypeError, IndexError, ValueError):
        return False
    lat_min, lat_max, lng_min, lng_max = region_bbox()
    return lat_min <= lat <= lat_max and lng_min <= lng <= lng_max


def _warn_coords_dropped(entity_id, coords_val) -> None:
    """Cảnh báo khi guard bbox loại toạ độ.

    Trước đây việc loại là IM LẶNG (chỉ gán None): `ben-xe-mien-tay-hcm` còn toạ độ
    trong web/data.json nhưng DB trả None, không có dấu vết nào để lần ra. Với bản
    clone tỉnh khác, im lặng = mất sạch toạ độ. Log kèm id + toạ độ + bbox đang áp dụng.
    """
    logger.warning(
        "Loại toạ độ ngoài vùng: entity=%s coords=%r bbox=%s. "
        "Nếu vùng phục vụ khác Vĩnh Long, đặt %s='lat_min,lat_max,lng_min,lng_max'.",
        entity_id or "<no-id>", coords_val, region_bbox(), REGION_BBOX_ENV,
    )


def _env_truthy(name: str, default: str = "false") -> bool:
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes", "on")


# ── Shared WHERE-clause builders (extract-method từ search/list/count để giảm complexity;
#    di chuyển NGUYÊN VĂN từng khối, mutate conditions/params tại chỗ, giữ đúng thứ tự gọi) ──

def _pg_missing_columns(cur, tables: set, required_columns=None) -> list:
    """Quét cột thiếu theo PG_REQUIRED_COLUMNS (extract nguyên văn từ _verify_pg_schema)."""
    missing_columns: list[str] = []
    required_columns = required_columns or PG_REQUIRED_COLUMNS
    for table, columns in required_columns.items():
        if table not in tables:
            continue
        cur.execute(
            """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                """,
            (table,),
        )
        existing = {row["column_name"] for row in cur.fetchall()}
        for column in sorted(columns - existing):
            missing_columns.append(f"{table}.{column}")
    return missing_columns


def _pg_missing_triggers(cur) -> list[str]:
    cur.execute(
        """
        SELECT tg.tgname AS trigger_name, cls.relname AS table_name
        FROM pg_catalog.pg_trigger AS tg
        JOIN pg_catalog.pg_class AS cls ON cls.oid = tg.tgrelid
        JOIN pg_catalog.pg_namespace AS ns ON ns.oid = cls.relnamespace
        WHERE NOT tg.tgisinternal AND ns.nspname = 'public'
        """
    )
    existing = {
        (row["trigger_name"], row["table_name"])
        for row in cur.fetchall()
    }
    return [
        f"{trigger_name} on {table_name}"
        for trigger_name, table_name in sorted(PG_REQUIRED_TRIGGERS.items())
        if (trigger_name, table_name) not in existing
    ]


def _pg_schema_issues(
    missing_tables: list[str],
    missing_columns: list[str],
    missing_triggers: list[str],
    schema_version: int,
    *,
    required_schema_version: int = PG_REQUIRED_SCHEMA_VERSION,
) -> list[str]:
    """Dựng danh sách issue (extract nguyên văn từ _verify_pg_schema)."""
    issues: list[str] = []
    if missing_tables:
        issues.append("missing tables: " + ", ".join(missing_tables))
    if missing_columns:
        issues.append("missing columns: " + ", ".join(missing_columns))
    if missing_triggers:
        issues.append("missing triggers: " + ", ".join(missing_triggers))
    if schema_version < required_schema_version:
        issues.append(f"schema_version agent={schema_version}, expected >= {required_schema_version}")
    return issues


def _normalize_catalog_sql(value) -> str | None:
    if value is None:
        return None
    return "".join(str(value).lower().split())


def _catalog_definition_matches(row, expected: Mapping[str, object]) -> bool:
    if row is None:
        return False
    for key, value in expected.items():
        actual = row.get(key)
        if key in {"columns", "target_columns", "update_columns"}:
            actual = tuple(actual or ())
        elif key in {"check_expression", "predicate", "when_expression", "function_body"}:
            actual = _normalize_catalog_sql(actual)
            value = _normalize_catalog_sql(value)
        if actual != value:
            return False
    return all(
        row.get(key) is expected_value
        for key, expected_value in (
            ("validated", True),
            ("deferrable", False),
            ("deferred", False),
        )
        if key in row
    )


def _case_catalog_issues(constraint_rows, index_rows, trigger_rows) -> list[str]:
    issues: list[str] = []
    constraints = {row["constraint_name"]: row for row in constraint_rows}
    for name, expected in _CASE_REQUIRED_CONSTRAINT_DEFINITIONS.items():
        if not _catalog_definition_matches(constraints.get(name), expected):
            issues.append(f"constraint definition drift: {name}")
    for name, expected in _CASE_REQUIRED_FK_DEFINITIONS.items():
        if not _catalog_definition_matches(constraints.get(name), expected):
            issues.append(f"foreign key definition drift: {name}")

    indexes = {row["index_name"]: row for row in index_rows}
    index_health = {
        "valid": True, "ready": True, "live": True, "access_method": "btree",
    }
    for name, expected in _CASE_REQUIRED_INDEX_DEFINITIONS.items():
        definition = {**expected, **index_health}
        if not _catalog_definition_matches(indexes.get(name), definition):
            issues.append(f"index definition drift: {name}")

    triggers = {row["trigger_name"]: row for row in trigger_rows}
    for name, expected in _CASE_REQUIRED_TRIGGER_DEFINITIONS.items():
        if not _catalog_definition_matches(triggers.get(name), expected):
            issues.append(f"trigger definition drift: {name}")
    return issues


def _pg_schema_snapshot(conn) -> dict[str, object]:
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        """
    )
    tables = {row["table_name"] for row in cur.fetchall()}
    missing_tables = sorted(PG_CORE_REQUIRED_TABLES - tables)
    missing_columns = _pg_missing_columns(cur, tables, PG_CORE_REQUIRED_COLUMNS)
    case_missing_tables = sorted(CASE_KERNEL_REQUIRED_TABLES - tables)
    case_missing_columns = _pg_missing_columns(cur, tables, CASE_KERNEL_REQUIRED_COLUMNS)
    case_security_issues: list[str] = []
    # Lightweight readiness doubles expose a ``tables`` attribute; they only
    # model the legacy table/column/version contract, not PostgreSQL catalogs.
    if {"case_receipts", "case_access_sessions", "case_idempotency"} <= tables and not hasattr(cur, "tables"):
        case_security_issues.extend(_case_security_catalog_issues(cur))
    missing_triggers = _pg_missing_triggers(cur)
    return _pg_snapshot_result(
        cur, tables, missing_tables, missing_columns, missing_triggers,
        case_missing_tables, case_missing_columns, case_security_issues,
    )


def _case_security_catalog_issues(cur) -> list[str]:
        """Đối chiếu catalog bảo mật Case Kernel — SQL nguyên văn từ _pg_schema_snapshot."""
        case_security_issues: list[str] = []
        cur.execute("""
            SELECT con.conname AS constraint_name,
                   con.contype::text AS constraint_type,
                   source.relname AS table_name,
                   ARRAY(
                       SELECT attribute.attname
                       FROM unnest(con.conkey) WITH ORDINALITY AS source_key(attnum, position)
                       JOIN pg_attribute AS attribute
                         ON attribute.attrelid = con.conrelid
                        AND attribute.attnum = source_key.attnum
                       ORDER BY source_key.position
                   ) AS columns,
                   target.relname AS target_table,
                   target_ns.nspname AS target_schema,
                   ARRAY(
                       SELECT attribute.attname
                       FROM unnest(con.confkey) WITH ORDINALITY AS target_key(attnum, position)
                       JOIN pg_attribute AS attribute
                         ON attribute.attrelid = con.confrelid
                        AND attribute.attnum = target_key.attnum
                       ORDER BY target_key.position
                   ) AS target_columns,
                   con.confdeltype::text AS delete_action,
                   con.confupdtype::text AS update_action,
                   -- Canonical, not pretty: pretty-printing drops the outer
                   -- parentheses on PostgreSQL 16, so a correct CHECK read as
                   -- drift and readiness could never report ready.
                   pg_get_expr(con.conbin, con.conrelid, false) AS check_expression,
                   con.convalidated AS validated,
                   con.condeferrable AS deferrable,
                   con.condeferred AS deferred
            FROM pg_constraint AS con
            JOIN pg_class AS source ON source.oid = con.conrelid
            JOIN pg_namespace AS source_ns ON source_ns.oid = source.relnamespace
            LEFT JOIN pg_class AS target ON target.oid = con.confrelid
            LEFT JOIN pg_namespace AS target_ns ON target_ns.oid = target.relnamespace
            WHERE source_ns.nspname = 'public'
        """)
        constraint_rows = cur.fetchall()
        cur.execute("""
            SELECT index_class.relname AS index_name,
                   table_class.relname AS table_name,
                   ARRAY(
                       SELECT pg_get_indexdef(idx.indexrelid, position, true)
                       FROM generate_series(1, idx.indnkeyatts) AS key_position(position)
                       ORDER BY position
                   ) AS columns,
                   pg_get_expr(idx.indpred, idx.indrelid, false) AS predicate,
                   idx.indisunique AS unique,
                   idx.indisvalid AS valid,
                   idx.indisready AS ready,
                   idx.indislive AS live,
                   access_method.amname AS access_method
            FROM pg_index AS idx
            JOIN pg_class AS index_class ON index_class.oid = idx.indexrelid
            JOIN pg_class AS table_class ON table_class.oid = idx.indrelid
            JOIN pg_namespace AS table_ns ON table_ns.oid = table_class.relnamespace
            JOIN pg_am AS access_method ON access_method.oid = index_class.relam
            WHERE table_ns.nspname = 'public'
        """)
        index_rows = cur.fetchall()
        cur.execute("""
            SELECT tg.tgname AS trigger_name,
                   table_class.relname AS table_name,
                   function_ns.nspname AS function_schema,
                   function.proname AS function_name,
                   tg.tgtype::integer AS trigger_type,
                   tg.tgenabled AS enabled,
                   CASE WHEN tg.tgqual IS NULL THEN NULL
                        ELSE pg_get_triggerdef(tg.oid, true) END AS when_expression,
                   function.prosrc AS function_body,
                   ARRAY(
                       SELECT attribute.attname
                       FROM unnest(tg.tgattr::smallint[]) WITH ORDINALITY AS trigger_key(attnum, position)
                       JOIN pg_attribute AS attribute
                         ON attribute.attrelid = tg.tgrelid
                        AND attribute.attnum = trigger_key.attnum
                       ORDER BY trigger_key.position
                   ) AS update_columns
            FROM pg_trigger AS tg
            JOIN pg_class AS table_class ON table_class.oid = tg.tgrelid
            JOIN pg_namespace AS table_ns ON table_ns.oid = table_class.relnamespace
            JOIN pg_proc AS function ON function.oid = tg.tgfoid
            JOIN pg_namespace AS function_ns ON function_ns.oid = function.pronamespace
            WHERE NOT tg.tgisinternal AND table_ns.nspname = 'public'
        """)
        trigger_rows = cur.fetchall()
        case_security_issues.extend(
            _case_catalog_issues(constraint_rows, index_rows, trigger_rows)
        )
        cur.execute("SELECT table_name, column_name, data_type, is_nullable, column_default FROM information_schema.columns WHERE table_schema='public'")
        column_meta = {(row["table_name"], row["column_name"]): (row["data_type"], row["is_nullable"], row["column_default"]) for row in cur.fetchall()}
        for key, expected in CASE_REQUIRED_COLUMN_META.items():
            actual = column_meta.get(key)
            if actual is None or actual[:2] != expected[:2] or (expected[2] is not None and expected[2] not in str(actual[2])):
                case_security_issues.append(f"column definition drift: {key[0]}.{key[1]}")
        cur.execute("SELECT tablename, tableowner FROM pg_tables WHERE schemaname='public'")
        owners = {row["tablename"]: row["tableowner"] for row in cur.fetchall()}
        for table in CASE_KERNEL_REQUIRED_TABLES:
            if owners.get(table) != "vl360":
                case_security_issues.append(f"table owner drift: {table}")
        return case_security_issues


def _pg_snapshot_result(
    cur, tables, missing_tables, missing_columns, missing_triggers,
    case_missing_tables, case_missing_columns, case_security_issues,
) -> dict[str, object]:
    schema_version = 0
    if "schema_version" in tables:
        cur.execute(
            "SELECT COALESCE(MAX(version), 0) AS version FROM schema_version WHERE component = %s",
            ("agent",),
        )
        row = cur.fetchone() or {}
        schema_version = int(row.get("version") or 0)

    issues = _pg_schema_issues(
        missing_tables,
        missing_columns,
        missing_triggers,
        schema_version,
        required_schema_version=PG_CORE_REQUIRED_SCHEMA_VERSION,
    )
    case_issues = _pg_schema_issues(
        case_missing_tables,
        case_missing_columns,
        [],
        schema_version,
        required_schema_version=PG_REQUIRED_SCHEMA_VERSION,
    )
    return {
        "schema_version": schema_version,
        "missing_tables": missing_tables,
        "missing_columns": missing_columns,
        "missing_triggers": missing_triggers,
        "case_missing_tables": case_missing_tables,
        "case_missing_columns": case_missing_columns,
        "case_issues": case_issues + case_security_issues,
        "issues": issues,
    }


def case_kernel_schema_status(schema: Mapping[str, object], *, enabled: bool) -> dict[str, object]:
    """Project the global PostgreSQL schema result into the Case Kernel boundary."""
    if not enabled:
        return {"ok": True, "state": "dormant", "code": "case_kernel_dormant"}
    if schema.get("backend") != "postgresql":
        return {"ok": False, "state": "blocked", "code": "case_postgresql_required"}
    if schema.get("case_config_code") in {"case_encryption_key_required", "case_owner_individual_required"}:
        return {"ok": False, "state": "blocked", "code": schema["case_config_code"]}
    if schema.get("ok") and not schema.get("case_issues"):
        return {"ok": True, "state": "ready", "code": "case_kernel_ready"}
    return {"ok": False, "state": "blocked", "code": "case_schema_not_ready"}


_COORD_INVALID = object()  # sentinel: decode thất bại → _parse_coordinates trả None


def _coord_decode_str(value):
    """Giải tối đa 4 lớp JSON-string (extract nguyên văn từ _parse_coordinates).
    Trả _COORD_INVALID nếu gặp string rỗng / JSON hỏng (caller → None)."""
    current = value
    for _ in range(4):
        if not isinstance(current, str):
            break
        text = current.strip()
        if not text:
            return _COORD_INVALID
        try:
            current = json.loads(text)
        except Exception:
            return _COORD_INVALID
    return current


def _coord_normalize_latlng(lat: float, lng: float) -> list[float] | None:
    """Chuẩn hoá thứ tự lat/lng theo dải hợp lệ (extract nguyên văn)."""
    if -90 <= lat <= 90 and -180 <= lng <= 180:
        return [lat, lng]
    if -180 <= lat <= 180 and -90 <= lng <= 90:
        return [lng, lat]
    return None


def _append_public_only(conditions: list) -> None:
    conditions.append("(e.status IS NULL OR e.status != 'provisional')")
    conditions.append("(e.verified IS NULL OR e.verified != 0)")


def _append_type_filter(conditions: list, params: list, ph: str,
                        entity_types, entity_type) -> None:
    if entity_types:
        placeholders = ", ".join([ph] * len(entity_types))
        conditions.append(f"e.type IN ({placeholders})")
        params.extend(entity_types)
    elif entity_type:
        conditions.append(f"e.type = {ph}")
        params.append(entity_type)


def _append_area_filter(conditions: list, params: list, ph: str,
                        use_pg: bool, area) -> None:
    place_col = 'e."placeId"' if use_pg else "e.placeId"
    conditions.append(f"""
                (e.area = {ph} OR {place_col} IN (
                    SELECT id FROM entities WHERE type = 'place' AND area = {ph}
                ))
            """)
    params.extend([area, area])


def _append_q_filter(conditions: list, params: list, ph: str,
                     use_pg: bool, q: str) -> None:
    if use_pg:
        # không phân-biệt-dấu (f_unaccent + functional GIN trgm index, migration 015)
        conditions.append(f"(f_unaccent(lower(e.name)) LIKE f_unaccent({ph}) ESCAPE '\\' OR f_unaccent(lower(e.summary)) LIKE f_unaccent({ph}) ESCAPE '\\' OR f_unaccent(lower(e.source)) LIKE f_unaccent({ph}) ESCAPE '\\')")
        q_esc = escape_like(q.lower())
        params.extend([f"%{q_esc}%", f"%{q_esc}%", f"%{q_esc}%"])
    else:
        conditions.append(f"(f_unaccent(e.name) LIKE f_unaccent({ph}) ESCAPE '\\' OR f_unaccent(e.summary) LIKE f_unaccent({ph}) ESCAPE '\\' OR f_unaccent(e.source) LIKE f_unaccent({ph}) ESCAPE '\\')")
        q_esc = escape_like(q)
        params.extend([f"%{q_esc}%", f"%{q_esc}%", f"%{q_esc}%"])


_ATTR_ALIASES = {
    "open_hours": "hours", "opening_hours": "hours",
    "operating_hours": "hours", "open_on": "hours",
    "foodyRating": "rating", "foodyComments": "review_count",
    "bestTime": "best_time", "best_time_to_visit": "best_time",
    "priceRange": "price_range", "bestSeason": "season_note",
    "checkin": "check_in", "checkout": "check_out",
    "highlights": "highlight", "booking": "booking_note",
    "admission_fee": "admission", "location": "address",
}


def _extract_rel_triple(rel: dict):
    """Rút (from, to, type) từ 1 quan hệ, chấp nhận alias (extract nguyên văn)."""
    s = rel.get("from") or rel.get("from_id") or rel.get("source_id")
    t = rel.get("to") or rel.get("to_id") or rel.get("target_id")
    rt = rel.get("type") or rel.get("rel_type")
    return s, t, rt


def _build_bulk_entity_rows(entities, strip: bool, now: str):
    """Dựng (entity_rows, fts_rows) cho executemany (extract nguyên văn từ _bulk_load)."""
    entity_rows, fts_rows = [], []
    for entity in entities:
        season_val = entity.get("season")
        coords_val = entity.get("coordinates")
        attrs_raw = entity.get("attributes", {})
        attrs_store = (_entity_details.strip_synced_keys(entity["type"], attrs_raw)
                       if strip and isinstance(attrs_raw, dict) else attrs_raw)
        entity_rows.append((
            entity["id"], entity["type"], entity["name"],
            entity.get("summary", ""), entity.get("description", ""),
            entity.get("placeId"),
            entity.get("confidence", 1.0),
            json.dumps(season_val, ensure_ascii=False) if season_val else None,
            json.dumps(attrs_store, ensure_ascii=False),
            json.dumps(entity.get("source", {}), ensure_ascii=False),
            json.dumps(entity.get("images", []), ensure_ascii=False),
            entity.get("updatedAt", now),
            json.dumps(coords_val) if coords_val else None,
            entity.get("area"), entity.get("level"), entity.get("parentId"),
            entity.get("legacyArea"),
            entity.get("status"),
            _verified_column(entity.get("verified", True)),
        ))
        fts_rows.append((entity["id"], entity["name"], entity.get("summary", ""), entity["type"]))
    return entity_rows, fts_rows


def _build_bulk_rel_rows(rels):
    """Dựng rel_rows đã lọc (extract nguyên văn từ _bulk_load)."""
    rel_rows = []
    for rel in rels:
        s, t, rt = _extract_rel_triple(rel)
        if s and t and rt:
            rel_rows.append((s, t, rt))
    return rel_rows


def _build_bulk_itin_rows(itineraries):
    """Dựng itin_rows (extract nguyên văn từ _bulk_load)."""
    itin_rows = []
    for it in itineraries:
        itin_rows.append((
            it["id"], it["title"], it.get("area"),
            json.dumps(_normalize_itinerary_areas(it.get("areas")), ensure_ascii=False),
            it.get("duration"),
            it.get("summary", ""), json.dumps(it.get("stops", []), ensure_ascii=False),
        ))
    return itin_rows


def _normalize_source_val(source_val):
    """Normalize source to list[dict] on write (extract nguyên văn từ upsert_entity)."""
    if isinstance(source_val, str):
        return [{"url": source_val}] if source_val.startswith("http") else [{"name": source_val}] if source_val else []
    elif isinstance(source_val, dict):
        return [source_val] if source_val else []
    elif not isinstance(source_val, list):
        return []
    return source_val


def _normalize_upsert_fields(entity: dict):
    """Chuẩn hoá các field trước khi ghi entity (extract nguyên văn từ upsert_entity).
    Trả (season_val, attrs_val, source_val, images_val, coords_val, updated, attrs_store)."""
    season_val = entity.get("season")
    attrs_val = entity.get("attributes", {})
    source_val = entity.get("source", {})
    # Normalize attribute key aliases on write
    if isinstance(attrs_val, dict):
        attrs_val = {_ATTR_ALIASES.get(k, k): v for k, v in attrs_val.items()}
    # Normalize source to list[dict] on write
    source_val = _normalize_source_val(source_val)
    images_val = entity.get("images", [])
    # GĐ-audit: chấp nhận alias legacy "coords" để ETL/auto_learn không mất toạ độ
    # đã geocode (nhiều path ghi entity["coords"] thay vì "coordinates").
    coords_val = entity.get("coordinates") or entity.get("coords")
    # Guard geocode: bỏ toạ độ NGOÀI bbox vùng phục vụ (crawler/geocoder hay khớp nhầm
    # tên → pin sai tỉnh). Thà null còn hơn sai (xem fix data 2026-06-14). Bbox đổi được
    # qua env REGION_BBOX (mặc định = Vĩnh Long); việc loại KHÔNG còn im lặng.
    if coords_val and not _coords_in_region(coords_val):
        _warn_coords_dropped(entity.get("id"), coords_val)
        coords_val = None
    updated = entity.get("updatedAt", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    # GĐ-C3: khi flip đọc bật, JSONB lưu TAIL-ONLY (typed keys sống ở cột — sync
    # cùng transaction bên dưới đảm bảo cột khớp; uncoercible ở lại JSONB).
    attrs_store = (_entity_details.strip_synced_keys(entity["type"], attrs_val)
                   if _entity_details.reads_enabled() and isinstance(attrs_val, dict)
                   else attrs_val)
    return season_val, attrs_val, source_val, images_val, coords_val, updated, attrs_store


def _verified_column(value: object) -> object:
    """Ép bool sang 0/1 cho cột `entities.verified`.

    Cột đó là INTEGER (migration 057), nhưng code sinh giá trị Python `bool`.
    SQLite nuốt bool nên ở local không ai thấy; Postgres thì báo thẳng
    `DatatypeMismatch: column "verified" is of type integer but expression is of
    type boolean`, và `replace_from_json` vỡ hoàn toàn — 8 test dựng fixture qua
    đường đó chết ngay ở setup khi job PG lần đầu chạy hết (2026-08-06).

    Ép ở đây, không đổi kiểu cột: đổi schema `entities` trên prod là việc riêng,
    cần backup + migration + test theo §B4.
    """
    if isinstance(value, bool):
        return int(value)
    return value


def _publication_write_fields(entity: dict) -> tuple[object, object, bool, bool]:
    return (
        entity.get("status"),
        _verified_column(entity.get("verified", True)),
        "status" in entity,
        "verified" in entity,
    )


def _fts_unavailable_error(exc: sqlite3.OperationalError) -> bool:
    message = str(exc).lower()
    return "no such table: entities_fts" in message or "no such module: fts5" in message


def _delete_entity_fts_terms(conn, row) -> bool:
    if row is None:
        return True
    try:
        conn.execute(
            "INSERT INTO entities_fts(entities_fts, rowid, id, name, summary, type) "
            "VALUES ('delete', ?, ?, ?, ?, ?)",
            (row["rowid"], row["id"], row["name"], row["summary"], row["type"]),
        )
    except sqlite3.OperationalError as exc:
        if not _fts_unavailable_error(exc):
            raise
        logger.debug("FTS5 delete skipped for entity %s", row["id"])
        return False
    return True


def _insert_entity_fts_terms(conn, entity: dict) -> None:
    row = conn.execute(
        "SELECT rowid FROM entities WHERE id = ?", (entity["id"],)
    ).fetchone()
    try:
        conn.execute(
            "INSERT INTO entities_fts(rowid, id, name, summary, type) VALUES (?, ?, ?, ?, ?)",
            (row["rowid"], entity["id"], entity["name"], entity.get("summary", ""), entity["type"]),
        )
    except sqlite3.OperationalError as exc:
        if not _fts_unavailable_error(exc):
            raise
        logger.debug("FTS5 insert skipped for entity %s", entity["id"])


# ══════════════════════════════════════════════════
#  DATABASE CLASS
# ══════════════════════════════════════════════════

# Khoá phá hoà cho MỌI nhánh sắp xếp của `list_entities`. `id` là khoá chính nên
# nó biến thứ tự bộ phận thành thứ tự TOÀN PHẦN.
#
# Vì sao bắt buộc: truy vấn có `LIMIT ? OFFSET ?`, mà cả ba khoá sắp xếp đều đồng
# điểm hàng loạt trong dữ liệu thật — `name` (Vicosap ×2, dừa sáp ×2), `rating`
# (điểm thô), `updatedAt` (4 entity cùng mốc). SQL không hứa thứ tự nào giữa các
# hàng đồng điểm, và Postgres được phép chọn kế hoạch KHÁC cho mỗi OFFSET. Khi đó
# một entity hiện ở cả trang 1 lẫn trang 2, một entity khác không hiện ở trang nào.
# SQLite hay trả theo rowid nên TÌNH CỜ ổn định — đó là lý do lỗi này sống lâu mà
# test trên máy dev không bắt được.
_ENTITY_TIEBREAK = "e.id ASC"


def _entity_order_clause(sort: str | None, use_pg: bool) -> tuple[str, str]:
    """(join, order) cho `list_entities`. Mọi nhánh KẾT bằng khoá duy nhất."""
    updated_col = 'e."updatedAt"' if use_pg else "e.updatedAt"
    join = ""
    if sort == "name":
        order = "e.name ASC"
    elif sort == "rating":
        # GĐ-C3: rating giờ sống ở cột CTI; COALESCE với JSONB legacy để chạy
        # đúng mọi trạng thái (prod sau dọn, prod trước dọn, dev cột trống).
        join = "LEFT JOIN entity_food_details fd ON fd.entity_id = e.id"
        order = ("COALESCE(fd.rating, (e.attributes->>'rating')::float) DESC NULLS LAST"
                 if use_pg else
                 "COALESCE(fd.rating, json_extract(e.attributes, '$.rating')) DESC")
    else:
        order = f"{updated_col} DESC"
    return join, f"{order}, {_ENTITY_TIEBREAK}"


class Database:
    """Database with thread-safe connections. PostgreSQL or SQLite."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DB_PATH)
        self._lock = Lock()
        self._initialized = False
        self._use_pg = USE_PG
        self._dsn = DATABASE_URL if USE_PG else None
        # D02: connection pool cho PG (tái dùng connection thay vì connect/close mỗi request).
        # OPT-IN (OFF mặc định): bật bằng PG_USE_POOL=true. Mặc định connect-trực-tiếp.
        # LÝ DO: pool gây TREO agent lúc startup trên prod 2026-06-22 (ThreadedConnectionPool
        # getconn/init block) + code này untestable local (không có PG local, §B3). Pool chỉ là
        # tối ưu perf, <10k user connect-trực-tiếp dư sức. CHỈ bật lại sau khi test được với PG thật.
        self._pg_pool = None
        self._pg_pool_failed = False
        self._pg_pool_fail_ts = 0.0

    def _get_pg_pool(self):
        if os.environ.get("PG_USE_POOL", "false").strip().lower() not in ("1", "true", "yes", "on"):
            return None
        if self._pg_pool_failed:
            if time.time() - self._pg_pool_fail_ts < 60:
                return None
        if self._pg_pool is None:
            with self._lock:
                if self._pg_pool_failed:
                    self._pg_pool_failed = False
                if self._pg_pool is None:
                    try:
                        from psycopg2.pool import ThreadedConnectionPool
                        mx = max(2, int(os.environ.get("PG_POOL_MAX", "10")))
                        self._pg_pool = ThreadedConnectionPool(1, mx, self._dsn, connect_timeout=5)
                    except Exception as e:
                        logger.warning("PG pool creation failed: %s", e)
                        self._pg_pool_failed = True
                        self._pg_pool_fail_ts = time.time()
                        return None
        return self._pg_pool

    @staticmethod
    def _finalize_connection(conn, commit_on_success: bool):
        if commit_on_success:
            conn.commit()
        else:
            conn.rollback()

    @staticmethod
    def _rollback_connection_quietly(conn):
        try:
            conn.rollback()
        except BaseException:
            pass

    @staticmethod
    def _close_connection_preserving_error(
        conn, primary_error, *, committed_transaction: bool = False
    ):
        try:
            conn.close()
        except BaseException as cleanup_error:
            if primary_error is not None:
                return
            if committed_transaction and isinstance(cleanup_error, Exception):
                logger.warning(
                    "Database connection cleanup failed after commit: %s",
                    type(cleanup_error).__name__,
                )
                return
            raise

    @staticmethod
    def _return_connection_to_pool(
        pool, conn, *, reusable: bool, commit_on_success: bool, primary_error
    ):
        try:
            pool.putconn(conn, close=not reusable)
        except BaseException as cleanup_error:
            try:
                conn.close()
            except BaseException:
                pass
            if primary_error is None:
                committed_write = reusable and commit_on_success
                if not (committed_write and isinstance(cleanup_error, Exception)):
                    raise

    @contextmanager
    def _pg_conn(self, *, commit_on_success: bool):
        pool = self._get_pg_pool()
        conn = pool.getconn() if pool else psycopg2.connect(self._dsn, connect_timeout=5)
        reusable = False
        committed_transaction = False
        primary_error = None
        try:
            conn.autocommit = False
            yield conn
            self._finalize_connection(conn, commit_on_success)
            reusable = True
            committed_transaction = commit_on_success
        except BaseException as exc:
            primary_error = exc
            self._rollback_connection_quietly(conn)
            raise
        finally:
            if pool:
                self._return_connection_to_pool(
                    pool,
                    conn,
                    reusable=reusable,
                    commit_on_success=commit_on_success,
                    primary_error=primary_error,
                )
            else:
                self._close_connection_preserving_error(
                    conn,
                    primary_error,
                    committed_transaction=committed_transaction,
                )

    @contextmanager
    def _sqlite_conn(self, *, commit_on_success: bool):
        conn = sqlite3.connect(self.db_path, timeout=30)
        committed_transaction = False
        primary_error = None
        try:
            conn.row_factory = sqlite3.Row
            # Keep SQLite lexical search equivalent to PostgreSQL's f_unaccent
            # expression instead of relying on ASCII-only LIKE semantics.
            from search_contract import normalize_search_text
            create_function = getattr(conn, "create_function", None)
            if create_function is not None:
                create_function("f_unaccent", 1, normalize_search_text)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA busy_timeout=5000")
            yield conn
            self._finalize_connection(conn, commit_on_success)
            committed_transaction = commit_on_success
        except BaseException as exc:
            primary_error = exc
            self._rollback_connection_quietly(conn)
            raise
        finally:
            self._close_connection_preserving_error(
                conn,
                primary_error,
                committed_transaction=committed_transaction,
            )

    @contextmanager
    def _conn(self, *, commit_on_success: bool = True):
        """Own connection finalization and return only reusable pooled connections."""
        manager = self._pg_conn if self._use_pg else self._sqlite_conn
        with manager(commit_on_success=commit_on_success) as conn:
            yield conn

    def _cursor(self, conn):
        if self._use_pg:
            return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        return conn

    def _param(self, idx: int = 0) -> str:
        return "%s" if self._use_pg else "?"

    @property
    def _ph(self) -> str:
        return "%s" if self._use_pg else "?"

    def _execute(self, conn, sql: str, params=None):
        """Execute with param style conversion."""
        if self._use_pg:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute(sql, params or ())
            return cur
        else:
            return conn.execute(sql, params or ())

    def _fetchone(self, conn, sql: str, params=None):
        if self._use_pg:
            cur = self._execute(conn, sql, params)
            return cur.fetchone()
        else:
            return conn.execute(sql, params or ()).fetchone()

    def _fetchall(self, conn, sql: str, params=None):
        if self._use_pg:
            cur = self._execute(conn, sql, params)
            return cur.fetchall()
        else:
            return conn.execute(sql, params or ()).fetchall()

    def _row_to_dict(self, row) -> dict:
        if row is None:
            return None
        if isinstance(row, dict):
            return row
        return dict(row)

    def _verify_pg_schema(self, conn) -> None:
        """Verify PostgreSQL schema at startup without mutating it."""
        snapshot = _pg_schema_snapshot(conn)
        issues = snapshot["issues"]
        if not issues:
            return

        message = (
            "PostgreSQL schema is not ready for this release: "
            + "; ".join(issues)
            + ". Run scripts/apply_migrations.py before starting the agent."
        )
        if _env_truthy("VL360_ALLOW_PG_SCHEMA_DRIFT"):
            logger.warning("%s Continuing because VL360_ALLOW_PG_SCHEMA_DRIFT is enabled.", message)
            return
        raise RuntimeError(message)

    def pg_schema_status(self) -> dict:
        """Return a non-mutating schema readiness snapshot for health checks."""
        if not self._use_pg:
            return {
                "backend": "sqlite",
                "ok": True,
                "schema_version": None,
                "required_schema_version": PG_REQUIRED_SCHEMA_VERSION,
                "core_required_schema_version": PG_CORE_REQUIRED_SCHEMA_VERSION,
                "required_triggers": dict(PG_REQUIRED_TRIGGERS),
                "missing_triggers": [],
            }

        try:
            with self._conn() as conn:
                snapshot = _pg_schema_snapshot(conn)
            return {
                "backend": "postgresql",
                "ok": not snapshot["issues"],
                "required_schema_version": PG_REQUIRED_SCHEMA_VERSION,
                "core_required_schema_version": PG_CORE_REQUIRED_SCHEMA_VERSION,
                "required_triggers": dict(PG_REQUIRED_TRIGGERS),
                **snapshot,
            }
        except Exception as exc:  # noqa: BLE001 - health endpoint should report, not crash
            return {
                "backend": "postgresql",
                "ok": False,
                "schema_version": 0,
                "required_schema_version": PG_REQUIRED_SCHEMA_VERSION,
                "core_required_schema_version": PG_CORE_REQUIRED_SCHEMA_VERSION,
                "required_triggers": dict(PG_REQUIRED_TRIGGERS),
                "missing_triggers": [],
                "error": type(exc).__name__,
            }

    def initialize(self):
        """Create SQLite tables or verify PostgreSQL schema."""
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return

            with _entity_details.detail_cache_write_scope():
                if self._use_pg:
                    with self._conn() as conn:
                        self._verify_pg_schema(conn)
                        # GĐ-C C2: nạp cache detail khi flip đọc bật (đổi flag = restart)
                        if _entity_details.reads_enabled():
                            _entity_details.load_detail_cache(conn, True)
                        self._initialized = True
                        return

                with self._conn() as conn:
                    self._init_sqlite_schema(conn)

                self._initialized = True

    def _init_sqlite_schema(self, conn) -> None:
        """Tạo bảng/index SQLite + migration cột (extract nguyên văn từ initialize —
        nhánh SQLite duy nhất, KHÔNG chạy cho PostgreSQL). Không tự commit."""
        conn.executescript("""
                    CREATE TABLE IF NOT EXISTS entities (
                        id TEXT PRIMARY KEY,
                        type TEXT NOT NULL,
                        name TEXT NOT NULL,
                        summary TEXT DEFAULT '',
                        description TEXT DEFAULT '',
                        placeId TEXT,
                        confidence REAL DEFAULT 1.0,
                        season TEXT,
                        attributes TEXT DEFAULT '{}',
                        source TEXT DEFAULT '{}',
                        images TEXT DEFAULT '[]',
                        coordinates TEXT,
                        area TEXT,
                        level TEXT,
                        parentId TEXT,
                        legacyArea TEXT,
                        revision INTEGER NOT NULL DEFAULT 1,
                        updatedAt TEXT,
                        created_at TEXT DEFAULT (datetime('now'))
                    );

                    CREATE TABLE IF NOT EXISTS entity_snapshot_generation (
                        entity_id TEXT PRIMARY KEY,
                        generation INTEGER NOT NULL DEFAULT 0,
                        issued_at TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS entity_changes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        entity_id TEXT NOT NULL,
                        field TEXT NOT NULL,
                        old_value TEXT,
                        new_value TEXT,
                        actor TEXT DEFAULT 'admin',
                        created_at TEXT DEFAULT (datetime('now'))
                    );

                    CREATE TABLE IF NOT EXISTS entity_mutation_audit (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_id TEXT NOT NULL UNIQUE,
                        resource_id TEXT NOT NULL,
                        resource_type TEXT NOT NULL,
                        actor_id TEXT NOT NULL,
                        reason TEXT NOT NULL,
                        correlation_id TEXT NOT NULL,
                        revision INTEGER NOT NULL,
                        before_json TEXT,
                        after_json TEXT,
                        created_at TEXT NOT NULL DEFAULT (datetime('now'))
                    );
                    CREATE INDEX IF NOT EXISTS idx_entity_mutation_audit_resource
                        ON entity_mutation_audit(resource_id, id DESC);

                    CREATE TABLE IF NOT EXISTS media_delete_receipts (
                        subject_id TEXT NOT NULL,
                        object_key TEXT NOT NULL,
                        generation TEXT NOT NULL,
                        status TEXT NOT NULL,
                        object_status TEXT NOT NULL,
                        cdn_status TEXT NOT NULL,
                        error TEXT,
                        updated_at TEXT NOT NULL,
                        PRIMARY KEY (subject_id, object_key, generation)
                    );
                    CREATE TABLE IF NOT EXISTS browser_clear_instructions (
                        issuance_id TEXT PRIMARY KEY,
                        subject_hash TEXT NOT NULL,
                        instruction_json TEXT NOT NULL,
                        issued_at TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS relationships (
                        from_id TEXT NOT NULL,
                        to_id TEXT NOT NULL,
                        type TEXT NOT NULL,
                        PRIMARY KEY (from_id, to_id, type)
                    );

                    CREATE TABLE IF NOT EXISTS itineraries (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        area TEXT,
                        areas TEXT DEFAULT '[]',
                        duration TEXT,
                        summary TEXT DEFAULT '',
                        stops TEXT DEFAULT '[]',
                        created_at TEXT DEFAULT (datetime('now'))
                    );

                    CREATE TABLE IF NOT EXISTS feedback (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT,
                        query TEXT,
                        rating INTEGER,
                        entity_id TEXT,
                        created_at TEXT DEFAULT (datetime('now'))
                    );

                    CREATE TABLE IF NOT EXISTS query_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        query TEXT,
                        tools TEXT,
                        reply_length INTEGER,
                        score REAL,
                        session_id TEXT,
                        created_at TEXT DEFAULT (datetime('now'))
                    );

                    CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type);
                    CREATE INDEX IF NOT EXISTS idx_entities_placeId ON entities(placeId);
                    CREATE INDEX IF NOT EXISTS idx_entities_updated ON entities(updatedAt DESC);
                    CREATE INDEX IF NOT EXISTS idx_entities_area ON entities(area);
                    CREATE INDEX IF NOT EXISTS idx_itineraries_area ON itineraries(area);
                    CREATE INDEX IF NOT EXISTS idx_relationships_from ON relationships(from_id);
                    CREATE INDEX IF NOT EXISTS idx_relationships_to ON relationships(to_id);
                    CREATE INDEX IF NOT EXISTS idx_feedback_user ON feedback(user_id);
                    CREATE INDEX IF NOT EXISTS idx_query_log_session ON query_log(session_id);
                    CREATE INDEX IF NOT EXISTS idx_query_log_created ON query_log(created_at);
                """)

        try:
            conn.execute("""
                        CREATE VIRTUAL TABLE IF NOT EXISTS entities_fts USING fts5(
                            id, name, summary, type,
                            content=entities,
                            content_rowid=rowid
                        )
                    """)
        except sqlite3.OperationalError:
            logger.debug("FTS5 not available, full-text search disabled")

        if not self._use_pg:
            for col in ("status TEXT", "verified INTEGER DEFAULT 1", "revision INTEGER NOT NULL DEFAULT 1"):
                try:
                    conn.execute(f"ALTER TABLE entities ADD COLUMN {col}")
                except sqlite3.OperationalError:
                    pass
            try:
                conn.execute("ALTER TABLE itineraries ADD COLUMN areas TEXT DEFAULT '[]'")
            except sqlite3.OperationalError:
                pass
            for idx_sql in [
                "CREATE INDEX IF NOT EXISTS idx_entities_status ON entities(status)",
                "CREATE INDEX IF NOT EXISTS idx_entities_verified ON entities(verified)",
            ]:
                try:
                    conn.execute(idx_sql)
                except sqlite3.OperationalError:
                    pass

        # GĐ-C: DDL parity SQLite — 8 cột phổ quát + 9 bảng CTI (PG do migrations sở hữu)
        _entity_details.ensure_schema_sqlite(conn)
        # GĐ-C C2: nạp cache detail khi flip đọc bật (đổi flag = restart)
        if _entity_details.reads_enabled():
            _entity_details.load_detail_cache(conn, False)

    # ── Entity CRUD ──

    def _entity_writer(self):
        return _entity_write.EntityWriteService(self)

    def _bump_sqlite_entity_revision(self, conn, before: dict | None, entity: dict) -> None:
        """Mirror PostgreSQL content-diff revision semantics on SQLite."""
        if self._use_pg or before is None:
            return
        defaults = {"summary": "", "description": "", "placeId": None,
                    "confidence": 1.0, "season": None, "attributes": {},
                    "images": [], "coordinates": None, "area": None}
        tracked = ("name", "type", "summary", "description", "placeId",
                   "confidence", "season", "attributes", "images",
                   "coordinates", "area")
        def value(source, name):
            current = source.get(name, defaults.get(name))
            return defaults[name] if current is None and name in {"attributes", "images"} else current
        if any(value(before, name) != value(entity, name) for name in tracked):
            self._execute(conn, "UPDATE entities SET revision = revision + 1 WHERE id = ?", (entity["id"],))

    def upsert_entity(self, entity: dict, *, actor_id: str = "system",
                      reason: str = "entity_upsert", correlation_id: str | None = None):
        """Insert or update an entity. Owns one transaction, delegates the writing."""
        self.initialize()
        correlation_id = correlation_id or f"{reason}:{entity.get('id', '')}"
        with _entity_details.detail_cache_write_scope():
            with self._conn() as conn:
                existing_row = self._fetchone(conn, f"SELECT * FROM entities WHERE id = {self._ph}", (entity["id"],))
                old = self._parse_entity(existing_row) if existing_row else {}
                mutations = self._entity_writer().upsert(conn, entity)
                self._bump_sqlite_entity_revision(conn, old if existing_row else None, entity)
                revision_row = self._fetchone(conn, f"SELECT revision FROM entities WHERE id = {self._ph}", (entity["id"],))
                current_revision = int((self._row_to_dict(revision_row) or {}).get("revision") or 1)
                from control_plane.saga import record_entity_mutation
                record_entity_mutation(entity["id"], actor_id=actor_id, reason=reason,
                                       correlation_id=correlation_id,
                                       before=old, after=entity,
                                       revision=current_revision, conn=conn, database=self)
                snapshot = bump_generation(conn, entity["id"], "entity_upsert", "database.upsert_entity")
            # Only now: the transaction closed cleanly, so the change is real.
            try:
                _entity_details.apply_detail_cache_mutations(list(mutations))
            except Exception as exc:
                raise PostCommitMutationError("detail_cache", exc) from exc
        try:
            invalidate_entity(entity["id"], reason="entity_upsert", generation=snapshot.generation)
        except Exception as exc:
            raise PostCommitMutationError("invalidation", exc) from exc

    def upsert_entity_with_audit(self, entity: dict, old: dict | None = None, *,
                                 actor: str = "admin", provenance: str = "admin-editor",
                                 reason: str | None = None, correlation_id: str | None = None,
                                 conn=None):
        """Entity row, detail mirror and change audit under ONE transaction.

        Split across two, a failure between them leaves an edited entry with no
        record of who edited it, and that record is the only thing that makes the
        edit answerable afterwards.
        """
        self.initialize()
        if conn is not None:
            mutations = self._entity_writer().upsert(conn, entity)
            self._bump_sqlite_entity_revision(conn, old if old else None, entity)
            revision_row = self._fetchone(conn, f"SELECT revision FROM entities WHERE id = {self._ph}", (entity["id"],))
            current_revision = int((self._row_to_dict(revision_row) or {}).get("revision") or 1)
            self.log_entity_changes(entity.get("id", ""), old or {}, entity,
                                    f"{actor}|{provenance}", conn=conn)
            from control_plane.saga import record_entity_mutation
            record_entity_mutation(entity.get("id", ""), actor_id=actor,
                                   reason=reason or provenance,
                                   correlation_id=correlation_id or actor,
                                   before=old or {}, after=entity,
                                   revision=current_revision, conn=conn, database=self)
            return mutations
        with _entity_details.detail_cache_write_scope():
            with self._conn() as conn:
                mutations = self._entity_writer().upsert(conn, entity)
                self._bump_sqlite_entity_revision(conn, old if old else None, entity)
                revision_row = self._fetchone(conn, f"SELECT revision FROM entities WHERE id = {self._ph}", (entity["id"],))
                current_revision = int((self._row_to_dict(revision_row) or {}).get("revision") or 1)
                self.log_entity_changes(entity.get("id", ""), old or {}, entity,
                                        f"{actor}|{provenance}", conn=conn)
                from control_plane.saga import record_entity_mutation
                record_entity_mutation(entity.get("id", ""), actor_id=actor,
                                       reason=reason or provenance,
                                       correlation_id=correlation_id or actor,
                                       before=old or {}, after=entity,
                                       revision=current_revision, conn=conn, database=self)
                snapshot = bump_generation(conn, entity["id"], "entity_upsert", f"{actor}|{provenance}")
            try:
                _entity_details.apply_detail_cache_mutations(list(mutations))
            except Exception as exc:
                raise PostCommitMutationError("detail_cache", exc) from exc
        try:
            invalidate_entity(entity["id"], reason="entity_upsert", generation=snapshot.generation)
        except Exception as exc:
            raise PostCommitMutationError("invalidation", exc) from exc

    def _write_entity_row(self, conn, entity, season_val, attrs_store,
                          source_val, images_val, coords_val, updated) -> None:
        """Ghi 1 hàng entities (extract nguyên văn từ upsert_entity, per-backend SQL)."""
        status, verified, has_status, has_verified = _publication_write_fields(entity)
        values = (
            entity["id"],
            entity["type"],
            entity["name"],
            entity.get("summary", ""),
            entity.get("description", ""),
            entity.get("placeId"),
            entity.get("confidence", 1.0),
            json.dumps(season_val, ensure_ascii=False) if season_val else None,
            json.dumps(attrs_store, ensure_ascii=False),
            json.dumps(source_val, ensure_ascii=False),
            json.dumps(images_val, ensure_ascii=False),
            updated,
            json.dumps(coords_val) if coords_val else None,
            entity.get("area"),
            entity.get("level"),
            entity.get("parentId"),
            entity.get("legacyArea"),
            status,
            verified,
            has_status,
            has_verified,
        )
        if self._use_pg:
            self._execute(conn, """
                    INSERT INTO entities
                    (id, type, name, summary, description, "placeId", confidence, season,
                     attributes, source, images, "updatedAt", coordinates, area, level,
                     "parentId", "legacyArea", status, verified)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (id) DO UPDATE SET
                        type = EXCLUDED.type,
                        name = EXCLUDED.name,
                        summary = EXCLUDED.summary,
                        description = EXCLUDED.description,
                        "placeId" = EXCLUDED."placeId",
                        confidence = EXCLUDED.confidence,
                        season = EXCLUDED.season,
                        attributes = EXCLUDED.attributes,
                        source = EXCLUDED.source,
                        images = EXCLUDED.images,
                        "updatedAt" = EXCLUDED."updatedAt",
                        coordinates = EXCLUDED.coordinates,
                        area = EXCLUDED.area,
                        level = EXCLUDED.level,
                        "parentId" = EXCLUDED."parentId",
                        "legacyArea" = EXCLUDED."legacyArea",
                        status = CASE WHEN %s THEN EXCLUDED.status ELSE entities.status END,
                        verified = CASE WHEN %s THEN EXCLUDED.verified ELSE entities.verified END,
                        -- The number a pending correction was written against. It has
                        -- to move whenever the content moves, or the conflict check
                        -- waves through a correction aimed at wording already gone.
                        -- Only on a real difference: re-imports re-save identical rows
                        -- constantly, and bumping there would make every correction in
                        -- flight look stale over a change that never happened. The
                        -- compared set is exactly what this boundary calls writable;
                        -- "updatedAt" and source are bookkeeping, not content.
                        revision = entities.revision + CASE WHEN (
                            entities.type, entities.name, entities.summary,
                            entities.description, entities."placeId", entities.confidence,
                            entities.season, entities.attributes, entities.images,
                            entities.coordinates, entities.area
                        ) IS DISTINCT FROM (
                            EXCLUDED.type, EXCLUDED.name, EXCLUDED.summary,
                            EXCLUDED.description, EXCLUDED."placeId", EXCLUDED.confidence,
                            EXCLUDED.season, EXCLUDED.attributes, EXCLUDED.images,
                            EXCLUDED.coordinates, EXCLUDED.area
                        ) THEN 1 ELSE 0 END
                """, values)
        else:
            old_fts_row = conn.execute(
                "SELECT rowid, id, name, summary, type FROM entities WHERE id = ?",
                (entity["id"],),
            ).fetchone()
            fts_available = _delete_entity_fts_terms(conn, old_fts_row)
            conn.execute("""
                    INSERT INTO entities
                    (id, type, name, summary, description, placeId, confidence, season,
                     attributes, source, images, updatedAt, coordinates, area, level,
                     parentId, legacyArea, status, verified)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(id) DO UPDATE SET
                        type = excluded.type,
                        name = excluded.name,
                        summary = excluded.summary,
                        description = excluded.description,
                        placeId = excluded.placeId,
                        confidence = excluded.confidence,
                        season = excluded.season,
                        attributes = excluded.attributes,
                        source = excluded.source,
                        images = excluded.images,
                        updatedAt = excluded.updatedAt,
                        coordinates = excluded.coordinates,
                        area = excluded.area,
                        level = excluded.level,
                        parentId = excluded.parentId,
                        legacyArea = excluded.legacyArea,
                        status = CASE WHEN ? THEN excluded.status ELSE entities.status END,
                        verified = CASE WHEN ? THEN excluded.verified ELSE entities.verified END
                """, values)
            if fts_available:
                _insert_entity_fts_terms(conn, entity)

    def reload_entity_details_cache(self) -> int:
        """GĐ-C C2: nạp lại cache detail-rows (test + vận hành sau khi sửa DB tay)."""
        self.initialize()
        with _entity_details.detail_cache_write_scope():
            with self._conn() as conn:
                return _entity_details.load_detail_cache(conn, self._use_pg)

    def update_description(self, entity_id: str, description: str):
        """Update only the description field (won't be overwritten by upsert_entity)."""
        self.initialize()
        ph = self._ph
        with self._conn() as conn:
            self._execute(conn, f"UPDATE entities SET description = {ph} WHERE id = {ph}", (description, entity_id))
            snapshot = bump_generation(conn, entity_id, "description_update", "database.update_description")
        invalidate_entity(entity_id, reason="description_update", generation=snapshot.generation)

    def get_entity(self, entity_id: str) -> dict | None:
        """Get single entity by ID."""
        self.initialize()
        ph = self._ph
        with self._conn() as conn:
            row = self._fetchone(conn, f"SELECT * FROM entities WHERE id = {ph}", (entity_id,))
            return self._parse_entity(row) if row else None

    def get_entities_batch(self, entity_ids: list[str]) -> dict[str, dict]:
        """Get multiple entities by ID in one query. Returns {id: entity}."""
        if not entity_ids:
            return {}
        self.initialize()
        ph = self._ph
        unique_ids = list(dict.fromkeys(entity_ids))
        placeholders = ", ".join(ph for _ in unique_ids)
        with self._conn() as conn:
            rows = self._fetchall(conn, f"SELECT * FROM entities WHERE id IN ({placeholders})", tuple(unique_ids))
        return {e["id"]: e for row in rows if (e := self._parse_entity(row))}

    def delete_entity(self, entity_id: str, *, actor_id: str = "system",
                      reason: str = "entity_delete", correlation_id: str | None = None) -> bool:
        """Delete entity and its relationships."""
        self.initialize()
        ph = self._ph
        with _entity_details.detail_cache_write_scope():
            with self._conn() as conn:
                existing_row = self._fetchone(conn, f"SELECT * FROM entities WHERE id = {ph}", (entity_id,))
                old = self._parse_entity(existing_row) if existing_row else {}
                cur = self._execute(conn, f"DELETE FROM entities WHERE id = {ph}", (entity_id,))
                self._execute(conn, f"DELETE FROM relationships WHERE from_id = {ph} OR to_id = {ph}",
                              (entity_id, entity_id))
                # GĐ-C: dọn detail rows (PG có FK CASCADE; SQLite dev thường không bật pragma FK)
                mutation = _entity_details.delete_entity_details(conn, self._use_pg, entity_id)
                if not self._use_pg:
                    try:
                        conn.execute("DELETE FROM entities_fts WHERE id = ?", (entity_id,))
                    except sqlite3.OperationalError:
                        logger.debug("FTS5 delete skipped for entity %s", entity_id)
                deleted = cur.rowcount > 0
                if deleted:
                    from control_plane.saga import record_entity_mutation
                    record_entity_mutation(entity_id, actor_id=actor_id, reason=reason,
                                           correlation_id=correlation_id or f"{reason}:{entity_id}",
                                           before=old, after={}, revision=int(old.get("revision") or 0) + 1,
                                           conn=conn, database=self)
                snapshot = bump_generation(conn, entity_id, "entity_delete", "database.delete_entity") if deleted else None
            try:
                _entity_details.apply_detail_cache_mutations([mutation])
            except Exception as exc:
                if deleted:
                    raise PostCommitMutationError("detail_cache", exc) from exc
                raise
            if snapshot is not None:
                try:
                    invalidate_entity(entity_id, reason="entity_delete", generation=snapshot.generation)
                except Exception as exc:
                    raise PostCommitMutationError("invalidation", exc) from exc
            return deleted

    def record_entity_mutation_audit(self, *, event_id: str, resource_id: str,
                                     resource_type: str, actor_id: str, reason: str,
                                     correlation_id: str, revision: int,
                                     before: dict | None, after: dict | None,
                                     occurred_at: str | None = None, conn=None, **_kwargs):
        """Write an immutable envelope on the caller's transaction."""
        self.initialize()
        own = conn is None
        manager = self._conn() if own else None
        if own:
            with manager as local:
                return self.record_entity_mutation_audit(
                    event_id=event_id, resource_id=resource_id,
                    resource_type=resource_type, actor_id=actor_id,
                    reason=reason, correlation_id=correlation_id,
                    revision=revision, before=before, after=after,
                    occurred_at=occurred_at, conn=local)
        if not self._use_pg:
            self._execute(conn, """INSERT INTO entity_mutation_audit
                (event_id, resource_id, resource_type, actor_id, reason,
                 correlation_id, revision, before_json, after_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE(?, datetime('now')))""",
                (event_id, resource_id, resource_type, actor_id, reason,
                 correlation_id, revision,
                 json.dumps(before, ensure_ascii=False, sort_keys=True, default=str) if before is not None else None,
                 json.dumps(after, ensure_ascii=False, sort_keys=True, default=str) if after is not None else None,
                 occurred_at))
            return
        # PostgreSQL already has the append-only admin audit table in schema 84;
        # keep the envelope in its JSON metadata without runtime DDL.
        self._execute(conn, """INSERT INTO admin_audit_events
            (actor, method, path, request_id, reason, before_json, after_json, meta)
            VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb)""",
            (actor_id, "MUTATION", f"/{resource_type}/{resource_id}",
             correlation_id, reason,
             json.dumps(before, ensure_ascii=False, default=str) if before is not None else None,
             json.dumps(after, ensure_ascii=False, default=str) if after is not None else None,
             json.dumps({"event_id": event_id, "resource_id": resource_id,
                         "resource_type": resource_type, "revision": revision,
                         "correlation_id": correlation_id}, ensure_ascii=False)))

    def get_entity_audit(self, resource_id: str | None = None, limit: int = 200) -> list[dict]:
        self.initialize()
        if self._use_pg:
            ph = self._ph
            where = f"WHERE method = 'MUTATION' AND meta->>'resource_id' = {ph}" if resource_id else "WHERE method = 'MUTATION'"
            params = (resource_id, limit) if resource_id else (limit,)
            with self._conn() as conn:
                rows = self._fetchall(conn, f"SELECT actor AS actor_id, reason, request_id AS correlation_id, before_json, after_json, NULLIF(meta->>'revision', '')::integer AS revision, meta->>'event_id' AS event_id FROM admin_audit_events {where} ORDER BY created_at DESC LIMIT {ph}", params)
            return [self._row_to_dict(r) for r in rows]
        ph = self._ph
        where = f"WHERE resource_id = {ph}" if resource_id else ""
        params = (resource_id, limit) if resource_id else (limit,)
        with self._conn() as conn:
            rows = self._fetchall(conn, f"SELECT * FROM entity_mutation_audit {where} ORDER BY id DESC LIMIT {ph}", params)
        return [self._row_to_dict(r) for r in rows]

    def search_entities(self, q: str = None, entity_type: str = None,
                        area: str = None, limit: int = 20, offset: int = 0,
                        entity_types: list[str] | None = None,
                        public_only: bool = False,
                        month: int | None = None) -> list[dict]:
        """Search entities with filters (offset hỗ-trợ phân-trang — FIX bug search lặp)."""
        self.initialize()
        ph = self._ph
        conditions = ["e.type NOT IN ('place')"]
        params = []

        if public_only:
            _append_public_only(conditions)
        _append_type_filter(conditions, params, ph, entity_types, entity_type)

        if area:
            _append_area_filter(conditions, params, ph, self._use_pg, area)

        if month is not None:
            conditions.append(self._month_condition())
            params.append(self._month_param(month))

        if q:
            _append_q_filter(conditions, params, ph, self._use_pg, q)

        where = " AND ".join(conditions)
        params.append(limit)
        params.append(offset)

        with self._conn() as conn:
            rows = self._fetchall(conn, f"""
                SELECT e.* FROM entities e
                WHERE {where}
                ORDER BY e.confidence DESC, e.id
                LIMIT {ph} OFFSET {ph}
            """, params)
            return [self._parse_entity(r) for r in rows]

    _SORT_OPTIONS = {"newest", "name", "rating"}

    def _month_condition(self) -> str:
        if self._use_pg:
            return "e.season IS NOT NULL AND e.season::jsonb->'months' @> %s::jsonb"
        return "e.season IS NOT NULL AND EXISTS (SELECT 1 FROM json_each(json_extract(e.season, '$.months')) WHERE value = ?)"

    def _month_param(self, month: int):
        if self._use_pg:
            return json.dumps([month])
        return month

    def list_entities(self, entity_type: str = None, area: str = None,
                      limit: int = 500, offset: int = 0,
                      entity_types: list[str] | None = None,
                      public_only: bool = False,
                      sort: str | None = None,
                      month: int | None = None) -> list[dict]:
        """List entities with pagination."""
        self.initialize()
        ph = self._ph
        conditions = ["e.type != 'place'"]
        params = []
        if public_only:
            _append_public_only(conditions)
        _append_type_filter(conditions, params, ph, entity_types, entity_type)
        if area:
            _append_area_filter(conditions, params, ph, self._use_pg, area)
        if month is not None:
            conditions.append(self._month_condition())
            params.append(self._month_param(month))

        where = " AND ".join(conditions)
        params.extend([limit, offset])

        join, order = _entity_order_clause(sort, self._use_pg)

        with self._conn() as conn:
            rows = self._fetchall(conn, f"""
                SELECT e.* FROM entities e {join} WHERE {where}
                ORDER BY {order} LIMIT {ph} OFFSET {ph}
            """, params)
            return [self._parse_entity(r) for r in rows]

    def count_entities_filtered(self, entity_type: str = None, area: str = None,
                                q: str = None, entity_types: list[str] | None = None,
                                public_only: bool = False,
                                month: int | None = None) -> int:
        """Count non-place entities with the same public filters as list/search."""
        self.initialize()
        ph = self._ph
        conditions = ["e.type != 'place'"]
        params = []

        if public_only:
            _append_public_only(conditions)
        _append_type_filter(conditions, params, ph, entity_types, entity_type)
        if month is not None:
            conditions.append(self._month_condition())
            params.append(self._month_param(month))
        if area:
            _append_area_filter(conditions, params, ph, self._use_pg, area)
        if q:
            _append_q_filter(conditions, params, ph, self._use_pg, q)

        where = " AND ".join(conditions)
        with self._conn() as conn:
            row = self._fetchone(conn, f"SELECT COUNT(*) as c FROM entities e WHERE {where}", params)
            return int(row["c"] if row else 0)

    def count_entities(self) -> dict:
        """Count entities by type."""
        self.initialize()
        with self._conn() as conn:
            rows = self._fetchall(conn, """
                SELECT type, COUNT(*) as count FROM entities
                WHERE type != 'place'
                GROUP BY type
            """)
            return {r["type"]: r["count"] for r in rows}

    # ── Bulk load (GĐ3.4: nguồn cho knowledge in-memory; KHÔNG loại trừ place) ──

    def all_entities(self) -> list[dict]:
        """Toàn bộ entity (gồm cả place) — dùng để nạp knowledge in-memory."""
        self.initialize()
        with self._conn() as conn:
            rows = self._fetchall(conn, "SELECT * FROM entities")
            return [self._parse_entity(r) for r in rows]

    def all_relationships(self) -> list[dict]:
        """Toàn bộ quan hệ ở shape {from,to,type} (khớp data.json/knowledge)."""
        self.initialize()
        with self._conn() as conn:
            rows = self._fetchall(conn, "SELECT from_id, to_id, type FROM relationships")
            return [{"from": r["from_id"], "to": r["to_id"], "type": r["type"]} for r in rows]

    def all_itineraries(self) -> list[dict]:
        """Toàn bộ itinerary (stops đã parse)."""
        self.initialize()
        with self._conn() as conn:
            rows = self._fetchall(conn, "SELECT * FROM itineraries")
            return [self._parse_itinerary(r) for r in rows]

    def entities_by_place(self, place_id: str) -> list[dict]:
        """Tất cả entity nội dung thuộc 1 xã/phường (placeId), trừ chính các đơn vị place.
        Phục vụ trang hub per-xã/phường (du lịch/lưu trú/sản phẩm/...)."""
        self.initialize()
        ph = self._ph
        pcol = '"placeId"' if self._use_pg else "placeId"
        with self._conn() as conn:
            rows = self._fetchall(
                conn,
                f"SELECT * FROM entities WHERE {pcol} = {ph} AND type != {ph} ORDER BY type, name",
                (place_id, "place"))
            return [self._parse_entity(r) for r in rows]

    def facilities_by_place(self, place_id: str | None = None) -> list[dict]:
        """GĐ13.3: cơ quan hành chính (type=facility) theo xã/phường (placeId). Danh bạ hành chính."""
        self.initialize()
        ph = self._ph
        pcol = '"placeId"' if self._use_pg else "placeId"
        with self._conn() as conn:
            if place_id:
                rows = self._fetchall(
                    conn, f"SELECT * FROM entities WHERE type = {ph} AND {pcol} = {ph}",
                    ("facility", place_id))
            else:
                rows = self._fetchall(conn, f"SELECT * FROM entities WHERE type = {ph}", ("facility",))
            return [self._parse_entity(r) for r in rows]

    # ── Relationships ──

    def add_relationship(self, from_id: str, to_id: str, rel_type: str, *,
                         actor_id: str = "system", reason: str = "relationship_add",
                         correlation_id: str | None = None):
        self.initialize()
        ph = self._ph
        with self._conn() as conn:
            if self._use_pg:
                cur = self._execute(conn, f"""
                    INSERT INTO relationships (from_id, to_id, type) VALUES ({ph}, {ph}, {ph})
                    ON CONFLICT DO NOTHING
                """, (from_id, to_id, rel_type))
            else:
                cur = conn.execute(
                    "INSERT OR IGNORE INTO relationships (from_id, to_id, type) VALUES (?, ?, ?)",
                    (from_id, to_id, rel_type))
            if cur.rowcount:
                from control_plane.saga import record_entity_mutation
                record_entity_mutation(f"{from_id}:{to_id}:{rel_type}", actor_id=actor_id,
                                       reason=reason, correlation_id=correlation_id or f"relationship:{from_id}:{to_id}:{rel_type}",
                                       before={}, after={"from_id": from_id, "to_id": to_id, "type": rel_type},
                                       revision=1, resource_type="relationship", conn=conn, database=self)
        try:
            from public_api import invalidate_entity_cache
            invalidate_entity_cache(from_id)
            invalidate_entity_cache(to_id)
        except Exception:
            logger.warning("Cache invalidation failed for %s / %s", from_id, to_id, exc_info=True)

    def delete_relationship(self, from_id: str, to_id: str, rel_type: str, *,
                            actor_id: str = "system", reason: str = "relationship_delete",
                            correlation_id: str | None = None) -> bool:
        self.initialize()
        ph = self._ph
        with self._conn() as conn:
            cur = self._execute(conn, f"DELETE FROM relationships WHERE from_id={ph} AND to_id={ph} AND type={ph}", (from_id, to_id, rel_type))
            if not cur.rowcount:
                return False
            from control_plane.saga import record_entity_mutation
            record_entity_mutation(f"{from_id}:{to_id}:{rel_type}", actor_id=actor_id,
                                   reason=reason, correlation_id=correlation_id or f"relationship:{from_id}:{to_id}:{rel_type}",
                                   before={"from_id": from_id, "to_id": to_id, "type": rel_type}, after={},
                                   revision=1, resource_type="relationship", conn=conn, database=self)
        return True

    def _parse_coordinates(self, value) -> list[float] | None:
        current = _coord_decode_str(value)
        if current is _COORD_INVALID:
            return None
        if isinstance(current, dict):
            lat = current.get("lat", current.get("latitude"))
            lng = current.get("lng", current.get("lon", current.get("longitude")))
            current = [lat, lng]
        if not isinstance(current, (list, tuple)) or len(current) != 2:
            return None
        try:
            lat = float(current[0])
            lng = float(current[1])
        except (TypeError, ValueError):
            return None
        return _coord_normalize_latlng(lat, lng)

    def _haversine_km(self, left: list[float] | None, right: list[float] | None) -> float | None:
        if not left or not right:
            return None
        lat1, lng1 = math.radians(left[0]), math.radians(left[1])
        lat2, lng2 = math.radians(right[0]), math.radians(right[1])
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        val = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
        return 6371.0 * 2 * math.asin(math.sqrt(val))

    def _relationship_sort_key(self, rel: dict, entity_id: str, entity_area: str = ""):
        rel_type = rel.get("rel_type") or rel.get("type") or ""
        source_id = rel.get("source_id") or rel.get("from_id")
        other_name = rel.get("target_name") if source_id == entity_id else rel.get("source_name")
        other_area = rel.get("other_area") or ""
        distance = rel.get("distance_km") if isinstance(rel.get("distance_km"), (int, float)) else 999999
        same_area = 0 if (entity_area and other_area and entity_area == other_area) else 1
        return (
            same_area,
            1 if rel_type == "near" else 0,
            RELATIONSHIP_TYPE_PRIORITY.get(rel_type, 50),
            distance,
            str(other_name or ""),
        )

    def get_relationships(
        self,
        entity_id: str,
        *,
        limit: int | None = None,
        offset: int = 0,
        rel_type: str | None = None,
        include_near: bool = True,
        return_total: bool = False,
    ) -> list[dict] | tuple[list[dict], int]:
        self.initialize()
        ph = self._ph
        conditions = [f"(r.from_id = {ph} OR r.to_id = {ph})"]
        params: list = [entity_id, entity_id]
        if rel_type:
            conditions.append(f"r.type = {ph}")
            params.append(rel_type)
        if not include_near:
            conditions.append("r.type != 'near'")
        where = " AND ".join(conditions)
        _FETCH_CAP = 500
        with self._conn() as conn:
            rows = self._fetchall(conn, f"""
                SELECT
                    r.from_id,
                    r.to_id,
                    r.type,
                    src.name AS source_name,
                    src.type AS source_type,
                    src.area AS source_area,
                    src.coordinates AS source_coordinates,
                    dst.name AS target_name,
                    dst.type AS target_type,
                    dst.area AS target_area,
                    dst.coordinates AS target_coordinates
                FROM relationships r
                JOIN entities src ON src.id = r.from_id
                JOIN entities dst ON dst.id = r.to_id
                WHERE {where}
                LIMIT {_FETCH_CAP}
            """, tuple(params))

        relationships, entity_area = self._rows_to_relationships(rows, entity_id)

        relationships.sort(key=lambda rel: self._relationship_sort_key(rel, entity_id, entity_area))
        total = len(relationships)
        offset = max(int(offset or 0), 0)
        if offset:
            relationships = relationships[offset:]
        if limit is not None:
            relationships = relationships[:max(int(limit), 0)]
        if return_total:
            return relationships, total
        return relationships

    def _rows_to_relationships(self, rows, entity_id: str):
        """Chuyển hàng join thành list quan hệ chuẩn hoá (extract nguyên văn từ
        get_relationships). Trả (relationships, entity_area)."""
        entity_area = ""
        relationships = []
        for row in rows:
            rel = self._row_to_dict(row)
            source_id = rel.get("from_id")
            target_id = rel.get("to_id")
            kind = rel.get("type")

            source_coords = self._parse_coordinates(rel.pop("source_coordinates", None))
            target_coords = self._parse_coordinates(rel.pop("target_coordinates", None))
            distance = self._haversine_km(source_coords, target_coords)
            is_source = source_id == entity_id
            other_id = target_id if is_source else source_id
            other_name = rel.get("target_name") if is_source else rel.get("source_name")
            other_type = rel.get("target_type") if is_source else rel.get("source_type")
            other_area = rel.get("target_area") if is_source else rel.get("source_area")
            if not entity_area:
                entity_area = rel.get("source_area") if is_source else rel.get("target_area")

            item = {
                "source_id": source_id,
                "target_id": target_id,
                "rel_type": kind,
                "other_id": other_id,
                "other_name": other_name,
                "other_type": other_type,
                "other_area": other_area or "",
                "from_id": source_id,
                "to_id": target_id,
                "type": kind,
                "source_name": rel.get("source_name"),
                "target_name": rel.get("target_name"),
                "source_type": rel.get("source_type"),
                "target_type": rel.get("target_type"),
            }
            if distance is not None:
                item["distance_km"] = round(distance, 1)
            relationships.append(item)
        return relationships, entity_area

    def count_relationships(self, entity_id: str, *, rel_type: str | None = None, include_near: bool = True) -> int:
        self.initialize()
        ph = self._ph
        conditions = [f"(from_id = {ph} OR to_id = {ph})"]
        params: list = [entity_id, entity_id]
        if rel_type:
            conditions.append(f"type = {ph}")
            params.append(rel_type)
        if not include_near:
            conditions.append("type != 'near'")
        where = " AND ".join(conditions)
        with self._conn() as conn:
            row = self._fetchone(conn, f"SELECT COUNT(*) AS c FROM relationships WHERE {where}", tuple(params))
            return row["c"] if row else 0

    # ── Itineraries ──

    def upsert_itinerary(self, itinerary: dict):
        self.initialize()
        ph = self._ph
        stops = json.dumps(itinerary.get("stops", []), ensure_ascii=False)
        areas = json.dumps(_normalize_itinerary_areas(itinerary.get("areas")), ensure_ascii=False)
        with self._conn() as conn:
            if self._use_pg:
                self._execute(conn, f"""
                    INSERT INTO itineraries (id, title, area, areas, duration, summary, stops)
                    VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
                    ON CONFLICT (id) DO UPDATE SET
                        title = EXCLUDED.title, area = EXCLUDED.area, areas = EXCLUDED.areas,
                        duration = EXCLUDED.duration, summary = EXCLUDED.summary,
                        stops = EXCLUDED.stops
                """, (
                    itinerary["id"], itinerary["title"], itinerary.get("area"), areas,
                    itinerary.get("duration"), itinerary.get("summary", ""), stops))
            else:
                conn.execute("""
                    INSERT OR REPLACE INTO itineraries (id, title, area, areas, duration, summary, stops)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    itinerary["id"], itinerary["title"], itinerary.get("area"), areas,
                    itinerary.get("duration"), itinerary.get("summary", ""), stops))

    def get_itinerary(self, itin_id: str) -> dict | None:
        self.initialize()
        ph = self._ph
        with self._conn() as conn:
            row = self._fetchone(conn, f"SELECT * FROM itineraries WHERE id = {ph}", (itin_id,))
            return self._parse_itinerary(row) if row else None

    def list_itineraries(self, area: str = None, limit: int = 100, offset: int = 0) -> list[dict]:
        self.initialize()
        ph = self._ph
        with self._conn() as conn:
            if area:
                area_token = f'%"{area}"%'
                areas_expr = "areas::text" if self._use_pg else "areas"
                rows = self._fetchall(
                    conn,
                    f"SELECT * FROM itineraries WHERE area = {ph} OR {areas_expr} LIKE {ph} LIMIT {ph} OFFSET {ph}",
                    (area, area_token, limit, offset),
                )
            else:
                rows = self._fetchall(conn, f"SELECT * FROM itineraries LIMIT {ph} OFFSET {ph}", (limit, offset))
            return [self._parse_itinerary(r) for r in rows]

    def export_all(self) -> dict:
        """Export all entities, relationships, and itineraries for data dump."""
        self.initialize()
        with self._conn() as conn:
            entity_rows = self._fetchall(conn, "SELECT * FROM entities")
            rel_rows = self._fetchall(conn, "SELECT from_id, to_id, type FROM relationships")
            itin_rows = self._fetchall(conn, "SELECT * FROM itineraries")
        entities = [self._parse_entity(r) for r in entity_rows]
        relationships = []
        for r in rel_rows:
            d = self._row_to_dict(r)
            relationships.append({"from": d["from_id"], "to": d["to_id"], "type": d["type"]})
        itineraries = [self._parse_itinerary(r) for r in itin_rows]
        return {"entities": entities, "relationships": relationships, "itineraries": itineraries}

    # ── Feedback ──

    def save_feedback(self, user_id: str, query: str, rating: int, entity_id: str = None):
        self.initialize()
        ph = self._ph
        with self._conn() as conn:
            self._execute(conn, f"""
                INSERT INTO feedback (user_id, query, rating, entity_id)
                VALUES ({ph}, {ph}, {ph}, {ph})
            """, (user_id, query, rating, entity_id))

    def get_feedback_stats(self) -> dict:
        self.initialize()
        with self._conn() as conn:
            total = self._fetchone(conn, "SELECT COUNT(*) as c FROM feedback")["c"]
            positive = self._fetchone(conn, "SELECT COUNT(*) as c FROM feedback WHERE rating > 0")["c"]
            return {
                "total": total,
                "positive": positive,
                "negative": total - positive,
                "positive_rate": round(positive / max(total, 1) * 100, 1),
            }

    # ── Query Log ──

    def log_query(self, query: str, tools: list, reply_length: int, score: float = None, session_id: str = ""):
        self.initialize()
        ph = self._ph
        tools_val = json.dumps(tools)
        with self._conn() as conn:
            self._execute(conn, f"""
                INSERT INTO query_log (query, tools, reply_length, score, session_id)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph})
            """, (query, tools_val, reply_length, score, session_id))

    def get_query_stats(self, days: int = 7) -> dict:
        self.initialize()
        ph = self._ph
        with self._conn() as conn:
            if self._use_pg:
                interval_param = f"{days} days"
                total = self._fetchone(conn, f"""
                    SELECT COUNT(*) as c FROM query_log
                    WHERE created_at >= NOW() - CAST({ph} AS INTERVAL)
                """, (interval_param,))["c"]
                avg_score = self._fetchone(conn, f"""
                    SELECT AVG(score) as a FROM query_log
                    WHERE score IS NOT NULL AND created_at >= NOW() - CAST({ph} AS INTERVAL)
                """, (interval_param,))["a"]
            else:
                cutoff = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                total = conn.execute(
                    "SELECT COUNT(*) as c FROM query_log WHERE created_at >= date(?, ?)",
                    (cutoff, f"-{days} days")).fetchone()["c"]
                avg_score = conn.execute(
                    "SELECT AVG(score) as a FROM query_log WHERE score IS NOT NULL AND created_at >= date(?, ?)",
                    (cutoff, f"-{days} days")).fetchone()["a"]
            return {
                "total_queries": total,
                "avg_score": round(avg_score or 0, 2),
                "period_days": days,
            }

    # ── Migration ──

    def migrate_from_json(self, json_path: str) -> dict:
        """Import data from data.json. Works with both PG and SQLite."""
        self.initialize()

        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)

        entities_count = 0
        its_count = 0

        for e in data.get("entities", []):
            self.upsert_entity(e)
            entities_count += 1

        rels_count = self._migrate_relationships(data.get("relationships", []))

        for it in data.get("itineraries", []):
            self.upsert_itinerary(it)
            its_count += 1

        return {
            "status": "migrated",
            "entities": entities_count,
            "relationships": rels_count,
            "itineraries": its_count,
            "backend": "postgresql" if self._use_pg else "sqlite",
        }

    def _migrate_relationships(self, rels) -> int:
        """Import quan hệ (extract nguyên văn từ migrate_from_json). Trả số đã thêm."""
        rels_count = 0
        for r in rels:
            source_id, target_id, rel_type = _extract_rel_triple(r)
            if source_id and target_id and rel_type:
                self.add_relationship(source_id, target_id, rel_type)
                rels_count += 1
        return rels_count

    def replace_from_json(self, json_path: str) -> dict:
        """Replace knowledge tables from data.json, backing up SQLite first."""
        self.initialize()
        self._guard_destructive_replace()

        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)

        backup_path = None
        if not self._use_pg and os.path.exists(self.db_path):
            backup_path = self.backup()

        # F1 (atomic): DELETE + INSERT trong CÙNG 1 transaction cho CẢ PG lẫn SQLite.
        # Crash giữa chừng → rollback → data CŨ còn nguyên (KHÔNG để DB rỗng). Trước đây
        # PG xoá ở transaction này rồi nạp ở migrate_from_json (transaction KHÁC) → không atomic.
        with _entity_details.detail_cache_write_scope():
            with self._conn() as conn:
                self._clear_knowledge_tables(conn)
                result, mutations = self._bulk_load(conn, data)
                if result.get("relationships_dropped", 0) > 0:
                    logger.warning("replace_from_json: %d quan he trung (from,to,type) bi bo khi luu "
                                   "(input %d -> stored %d)",
                                   result['relationships_dropped'], result['relationships'], result['relationships_stored'])
            _entity_details.apply_detail_cache_mutations(mutations, reset=True)

        result["mode"] = "replace"
        if backup_path:
            result["backup"] = backup_path
        return result

    def _guard_destructive_replace(self) -> None:
        """Chặn replace khi khoá / thiếu cờ (extract nguyên văn từ replace_from_json)."""
        # GĐ0.5: khoá replace trong giai đoạn ổn định. Migrate có chủ đích (GĐ3.3) dùng
        # ALLOW_DESTRUCTIVE_DB_REPLACE=1 để vượt; mở khoá hẳn ở GĐ3.8.
        if os.environ.get("DESTRUCTIVE_OPS_LOCKED", "1") == "1" and os.environ.get("ALLOW_DESTRUCTIVE_DB_REPLACE") != "1":
            raise RuntimeError(
                "replace_from_json bị khoá (DESTRUCTIVE_OPS_LOCKED=1). "
                "Đặt ALLOW_DESTRUCTIVE_DB_REPLACE=1 cho migrate có chủ đích (GĐ3.3)."
            )

        if self._use_pg and os.environ.get("ALLOW_DESTRUCTIVE_DB_REPLACE") != "1":
            raise RuntimeError("Refusing to replace PostgreSQL data without ALLOW_DESTRUCTIVE_DB_REPLACE=1")

    def _clear_knowledge_tables(self, conn) -> None:
        """Xoá các bảng tri thức trong transaction hiện tại (extract nguyên văn)."""
        self._execute(conn, "DELETE FROM relationships")
        self._execute(conn, "DELETE FROM itineraries")
        if not self._use_pg:
            try:
                conn.execute("DELETE FROM entities_fts")
            except sqlite3.OperationalError:
                logger.debug("FTS5 clear skipped (table may not exist)")
        self._execute(conn, "DELETE FROM entities")

    def _bulk_load(
        self, conn, data: dict
    ) -> tuple[dict, list[_entity_details.DetailCacheMutation]]:
        """Nạp entities+relationships+itineraries vào DB trên CONNECTION đã cho (không tự
        commit) — để replace_from_json gói DELETE+INSERT trong 1 transaction (F1 atomic).
        SQLite + PostgreSQL dùng chung cấu trúc; SQL theo từng backend (copy từ upsert_*)."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        # GĐ-C3: flip đọc bật → JSONB lưu tail-only (sync bên dưới điền cột cùng transaction)
        _strip = _entity_details.reads_enabled()
        entity_rows, fts_rows = _build_bulk_entity_rows(data.get("entities", []), _strip, now)
        rel_rows = _build_bulk_rel_rows(data.get("relationships", []))
        itin_rows = _build_bulk_itin_rows(data.get("itineraries", []))

        stored = self._bulk_insert_rows(conn, entity_rows, fts_rows, rel_rows, itin_rows)

        # GĐ-C dual-write: phản chiếu typed attrs của TOÀN BỘ entities vừa nạp vào
        # cột phổ quát + bảng CTI — cùng transaction với DELETE+INSERT (F1 atomic).
        mutations = [
            _entity_details.sync_entity_details(
                conn, self._use_pg, entity["id"], entity["type"],
                entity.get("attributes") or {})
            for entity in data.get("entities", [])
        ]

        result = {
            "status": "migrated",
            "entities": len(entity_rows),
            "relationships": len(rel_rows),
            "relationships_stored": stored,
            "relationships_dropped": len(rel_rows) - stored,
            "itineraries": len(itin_rows),
            "backend": "postgresql" if self._use_pg else "sqlite",
        }
        return result, mutations

    def _bulk_insert_rows(self, conn, entity_rows, fts_rows, rel_rows, itin_rows) -> int:
        """executemany theo backend (extract nguyên văn từ _bulk_load). Trả số quan hệ đã lưu."""
        if self._use_pg:
            cur = conn.cursor()
            cur.executemany(
                'INSERT INTO entities (id, type, name, summary, description, "placeId", confidence, season, '
                'attributes, source, images, "updatedAt", coordinates, area, level, "parentId", "legacyArea", status, verified) '
                'VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) '
                'ON CONFLICT (id) DO NOTHING',
                entity_rows)
            cur.executemany(
                "INSERT INTO relationships (from_id, to_id, type) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
                rel_rows)
            cur.executemany(
                "INSERT INTO itineraries (id, title, area, areas, duration, summary, stops) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING",
                itin_rows)
            stored = self._fetchone(conn, "SELECT COUNT(*) as c FROM relationships")["c"]
        else:
            conn.executemany(
                "INSERT OR REPLACE INTO entities (id, type, name, summary, description, placeId, confidence, season, "
                "attributes, source, images, updatedAt, coordinates, area, level, parentId, legacyArea, status, verified) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", entity_rows)
            try:
                conn.executemany(
                    "INSERT OR REPLACE INTO entities_fts(id, name, summary, type) VALUES (?, ?, ?, ?)",
                    fts_rows)
            except sqlite3.OperationalError:
                logger.debug("FTS5 bulk insert skipped (%d rows)", len(fts_rows))
            conn.executemany(
                "INSERT OR IGNORE INTO relationships (from_id, to_id, type) VALUES (?, ?, ?)", rel_rows)
            conn.executemany(
                "INSERT OR REPLACE INTO itineraries (id, title, area, areas, duration, summary, stops) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)", itin_rows)
            stored = conn.execute("SELECT COUNT(*) as c FROM relationships").fetchone()["c"]
        return stored

    def backup(self, backup_path: str = None) -> str:
        """Create a backup (SQLite only; PG uses pg_dump)."""
        if self._use_pg:
            raise NotImplementedError("Use pg_dump for PostgreSQL backups")
        self.initialize()
        if not backup_path:
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            backup_path = str(Path(self.db_path).parent / f"vinhlong360_backup_{ts}.db")
        with self._conn() as conn:
            backup_conn = sqlite3.connect(backup_path)
            try:
                conn.backup(backup_conn)
            finally:
                backup_conn.close()
        return backup_path

    def stats(self) -> dict:
        """Database statistics."""
        self.initialize()
        with self._conn() as conn:
            entities = self._fetchone(conn, "SELECT COUNT(*) as c FROM entities WHERE type != 'place'")["c"]
            # "places" = SỐ XÃ/PHƯỜNG thật (level xa/phuong) = 124, KHÔNG đếm cả type=place thô
            # (162 — gồm 37 cơ-sở gán nhầm type=place + 1 tỉnh) để nhãn "Xã phường" đúng.
            places = self._fetchone(conn, "SELECT COUNT(*) as c FROM entities WHERE type = 'place' AND level IN ('xa','phuong')")["c"]
            rels = self._fetchone(conn, "SELECT COUNT(*) as c FROM relationships")["c"]
            its = self._fetchone(conn, "SELECT COUNT(*) as c FROM itineraries")["c"]
            feedback = self._fetchone(conn, "SELECT COUNT(*) as c FROM feedback")["c"]
            queries = self._fetchone(conn, "SELECT COUNT(*) as c FROM query_log")["c"]

            result = {
                "entities": entities,
                "places": places,
                "relationships": rels,
                "itineraries": its,
                "feedback_entries": feedback,
                "query_log_entries": queries,
                "backend": "postgresql" if self._use_pg else "sqlite",
            }

            if not self._use_pg:
                db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
                result["db_size_kb"] = round(db_size / 1024, 1)
                result["db_path"] = self.db_path

            return result

    # ── User methods (PG only, used by auth) ──

    def get_user_by_phone(self, phone: str) -> dict | None:
        self.initialize()
        ph = self._ph
        with self._conn() as conn:
            row = self._fetchone(conn, f"SELECT * FROM users WHERE phone = {ph}", (phone,))
            return self._row_to_dict(row)

    def get_user_by_id(self, user_id: str) -> dict | None:
        self.initialize()
        ph = self._ph
        with self._conn() as conn:
            row = self._fetchone(conn, f"SELECT * FROM users WHERE id::text = {ph}", (str(user_id),))
            return self._row_to_dict(row)

    def create_user(self, phone: str, display_name: str = None, consent_version: str = "1.0",
                    full_name: str = None, username: str = None, password_hash: str = None,
                    date_of_birth: str = None) -> dict:
        self.initialize()
        ph = self._ph
        extra_cols = []
        extra_phs = []
        extra_params = []
        if full_name:
            extra_cols.append("full_name"); extra_phs.append(ph); extra_params.append(full_name)
        if username:
            extra_cols.append("username"); extra_phs.append(ph); extra_params.append(username)
        if password_hash:
            extra_cols.append("password_hash"); extra_phs.append(ph); extra_params.append(password_hash)
        if date_of_birth:
            extra_cols.append("date_of_birth"); extra_phs.append(ph); extra_params.append(date_of_birth)
        cols_str = "phone, display_name, consent_at, consent_version"
        vals_str = f"{ph}, {ph}, NOW(), {ph}"
        params = [phone, display_name or full_name or f"User_{phone[-4:]}", consent_version]
        if extra_cols:
            cols_str += ", " + ", ".join(extra_cols)
            vals_str += ", " + ", ".join(extra_phs)
            params.extend(extra_params)
        with self._conn() as conn:
            row = self._fetchone(conn, f"""
                INSERT INTO users ({cols_str})
                VALUES ({vals_str})
                RETURNING *
            """, params)
            return self._row_to_dict(row)

    def update_user(self, user_id: str, **fields) -> dict | None:
        self.initialize()
        ph = self._ph
        sets = []
        params = []
        for k, v in fields.items():
            if k in ("display_name", "avatar_url", "cover_url", "bio", "role", "is_active", "password_hash", "username", "deleted_at", "full_name", "email", "contact_info"):
                sets.append(f"{k} = {ph}")
                params.append(v)
        if not sets:
            return self.get_user_by_id(user_id)
        params.append(str(user_id))
        with self._conn() as conn:
            row = self._fetchone(conn,
                f"UPDATE users SET {', '.join(sets)} WHERE id::text = {ph} RETURNING *", params)
            return self._row_to_dict(row)

    def delete_erased_user(self, conn, user_id: str, now):
        """Delete only a locked, deleted account whose exact deadline has passed."""
        ph = self._ph
        return self._fetchone(
            conn,
            f"""
                DELETE FROM users
                WHERE id::text = {ph}
                  AND deleted_at IS NOT NULL
                  AND erasure_due_at IS NOT NULL
                  AND erasure_due_at <= {ph}
                RETURNING id
            """,
            (str(user_id), now),
        )

    # ── Entity change history ──

    def log_entity_changes(self, entity_id: str, old: dict, new: dict,
                           actor: str = "admin", *, conn=None):
        tracked = ("name", "type", "summary", "placeId", "confidence", "season", "attributes", "images", "coordinates", "area")
        changes = []
        for field in tracked:
            old_val = str(old.get(field, "")) if old.get(field) is not None else ""
            new_val = str(new.get(field, "")) if new.get(field) is not None else ""
            if old_val != new_val:
                changes.append((entity_id, field, old_val[:2000], new_val[:2000], actor))
        if not changes:
            return
        if conn is not None:
            # Ride the caller's transaction: an audit that outlives a rollback of
            # the change it describes is a record of something that never happened.
            self._write_entity_change_rows(conn, changes)
            return
        with self._conn() as own_conn:
            self._write_entity_change_rows(own_conn, changes)

    def _write_entity_change_rows(self, conn, changes) -> None:
        ph = self._ph
        for c in changes:
            self._execute(conn, f"""
                INSERT INTO entity_changes (entity_id, field, old_value, new_value, actor)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph})
            """, c)

    def get_entity_history(self, entity_id: str, limit: int = 50) -> list[dict]:
        self.initialize()
        ph = self._ph
        with self._conn() as conn:
            rows = self._fetchall(conn, f"""
                SELECT id, entity_id, field, old_value, new_value, actor, created_at
                FROM entity_changes
                WHERE entity_id = {ph}
                ORDER BY created_at DESC, id DESC
                LIMIT {ph}
            """, (entity_id, limit))
        return [self._row_to_dict(r) for r in rows]

    # ── Helpers ──

    def _parse_entity(self, row) -> dict:
        if row is None:
            return None
        d = self._row_to_dict(row)
        json_fields = ("season", "attributes", "source", "images")
        if not self._use_pg:
            json_fields = (*json_fields, "coordinates")
        for field in json_fields:
            if d.get(field) and isinstance(d[field], str):
                try:
                    d[field] = json.loads(d[field])
                except (json.JSONDecodeError, ValueError, TypeError):
                    logger.warning("Corrupt JSON in entity %s field %s", d.get("id"), field)
        # GĐ-C C2: flag ON → attributes dựng lại từ cột (thắng) + fallback JSONB + tail
        if _entity_details.reads_enabled():
            d["attributes"] = _entity_details.rebuild_attributes(
                d.get("type") or "", d.get("attributes"), d)
        normalize_entity(d)
        return d

    def _parse_itinerary(self, row) -> dict:
        d = self._row_to_dict(row)
        for field in ("stops", "areas"):
            if d.get(field) and isinstance(d[field], str):
                try:
                    d[field] = json.loads(d[field])
                except (json.JSONDecodeError, ValueError, TypeError):
                    logger.warning("Corrupt JSON in itinerary %s %s", d.get("id"), field)
                    d[field] = []
        d["areas"] = _normalize_itinerary_areas(d.get("areas"))
        return d


# ══════════════════════════════════════════════════
#  P4 TRUST: timestamp normalization (no fabrication)
# ══════════════════════════════════════════════════

def _coerce_iso_date(value) -> str | None:
    """Trả ISO-8601 UTC (…Z) từ một giá trị ngày đã có sẵn trong DB/data.
    KHÔNG bịa ngày: chỉ chuẩn hoá định dạng. Trả None nếu không phân giải được.
    Track-H: không bao giờ thay bằng datetime.now(timezone.utc)."""
    if not value or not isinstance(value, str):
        return None
    s = value.strip()
    if not s:
        return None
    # Đã là ISO có Z → giữ nguyên
    if "T" in s and s.endswith("Z"):
        return s
    # Có 'T' nhưng thiếu Z (vd "2026-06-11T00:00:00") → thêm Z
    if "T" in s:
        return s.rstrip("Z") + "Z"
    # SQLite "datetime('now')" cho dạng "2026-06-13 04:00:38"
    candidate = s.replace(" ", "T", 1) if " " in s else s
    try:
        # Bỏ phần phân số giây nếu có (fromisoformat đời cũ kén)
        core = candidate.split(".")[0]
        parsed = datetime.fromisoformat(core)
        return parsed.strftime("%Y-%m-%dT%H:%M:%SZ")
    except (ValueError, AttributeError):
        # Date-only "2026-06-10" không qua được fromisoformat ở mọi runtime?
        # fromisoformat xử lý được date-only từ 3.11; fallback an toàn:
        return candidate + ("T00:00:00Z" if "T" not in candidate else "Z")


def canonical_verified_at(entity: Mapping[str, object]) -> str | None:
    """Return normalized field-verification time from attributes only."""
    attributes = entity.get("attributes")
    if not isinstance(attributes, Mapping):
        return None
    raw = attributes.get("verifiedAt")
    if not isinstance(raw, str) or not raw.strip():
        return None
    candidate = raw.strip()
    try:
        parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    else:
        parsed = parsed.astimezone(timezone.utc)
    return parsed.isoformat(timespec="seconds").replace("+00:00", "Z")


def normalize_entity(entity: Mapping[str, object]) -> dict:
    """Normalize an entity row and keep verification under its canonical namespace.

    Older imports may contain a top-level ``verifiedAt``. It is migrated only when
    the nested value is absent/empty; an existing nested value always wins. The
    legacy top-level key is never exposed to callers.
    """
    d = dict(entity) if isinstance(entity, Mapping) else entity
    if not isinstance(d, dict):
        return d
    attrs = d.get("attributes")
    attrs = dict(attrs) if isinstance(attrs, Mapping) else {}
    nested = attrs.get("verifiedAt")
    legacy = d.get("verifiedAt")
    if (not isinstance(nested, str) or not nested.strip()) and isinstance(legacy, str) and legacy.strip():
        attrs["verifiedAt"] = legacy.strip()
    d["attributes"] = attrs
    _normalize_entity_timestamps(d)
    return d


def _normalize_entity_timestamps(d: dict) -> dict:
    """Đảm bảo entity luôn phơi ra mốc thời gian ổn định, KHÔNG bịa.

    - updatedAt: chuẩn hoá ISO-8601 UTC. Nếu thiếu → suy từ created_at (DB luôn có).
    - createdAt: phơi created_at của DB (audit) nếu chưa có.
    Tất cả nguồn đều là field DB/data sẵn có — không dùng ngày hiện tại.
    """
    if not isinstance(d, dict):
        return d

    updated = d.get("updatedAt")
    iso_updated = _coerce_iso_date(updated) if updated else None
    if not iso_updated:
        # Fallback an toàn: dùng created_at của hàng DB (không bao giờ là "now")
        iso_updated = _coerce_iso_date(d.get("created_at"))
    if iso_updated:
        d["updatedAt"] = iso_updated

    # createdAt (audit) — chỉ phơi nếu DB có created_at
    if d.get("created_at") and not d.get("createdAt"):
        iso_created = _coerce_iso_date(d.get("created_at"))
        if iso_created:
            d["createdAt"] = iso_created

    d.pop("verifiedAt", None)
    return d


# Singleton
db = Database()


# ══════════════════════════════════════════════════
#  CLI: Migration tool
# ══════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    ROOT = Path(__file__).resolve().parent.parent
    JSON_PATH = ROOT / "web" / "data.json"

    if "--migrate" in sys.argv:
        print(f"Migrating {JSON_PATH} → {'PostgreSQL' if USE_PG else 'SQLite'}")
        result = db.migrate_from_json(str(JSON_PATH))
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif "--replace" in sys.argv:
        print(f"Replacing {'PostgreSQL' if USE_PG else 'SQLite'} knowledge data from {JSON_PATH}")
        result = db.replace_from_json(str(JSON_PATH))
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif "--backup" in sys.argv:
        path = db.backup()
        print(f"Backup created: {path}")

    elif "--stats" in sys.argv:
        print(json.dumps(db.stats(), indent=2, ensure_ascii=False))

    else:
        print("Usage:")
        print("  python database.py --migrate   # Import data.json")
        print("  python database.py --replace   # Replace knowledge tables from data.json")
        print("  python database.py --backup    # Create database backup (SQLite only)")
        print("  python database.py --stats     # Show database statistics")
