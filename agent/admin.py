"""
vinhlong360 — Admin API.

CRUD endpoints cho quản lý knowledge base:
  - Xem/sửa/xóa entities
  - Review entities auto-learned (pending review)
  - Trigger auto-learn
  - Xem analytics
  - Export/Import data

Mount vào FastAPI app chính qua router.
"""

import asyncio
import json
import logging
import os
import re
import subprocess
import sys
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, Request, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field  # field_validator sang siteops/admin_api.py cung models announcements (lat 3)

import data_quality  # noqa: F401  (nguoi dung cuoi la siteops/admin_api.py — giu additive-first B2, go o task rieng)
import knowledge
import analytics

logger = logging.getLogger("admin")
import site_settings  # noqa: F401  (nguoi dung cuoi la siteops/admin_api.py — giu additive-first B2, go o task rieng)
from database import db, escape_like as _escape_like





try:
    from cost_tracker import get_cost_report as _get_cost_report
    _HAS_COST = True
except Exception:  # noqa: BLE001
    logger.warning("Cost tracker unavailable", exc_info=True)
    _HAS_COST = False
from auth_middleware import get_current_user, require_csrf  # require_pg sang siteops/admin_api.py cung announcements admin (lat 3); validate_path_id het nguoi dung truc tiep khi collections sang entities/ (lat 6)
from middleware import admin_limiter, verify_admin_key, get_client_ip








_admin_volatile_caches: list[dict] = []




# ── Auth dependency ──

_AUDIT_FILE = Path(__file__).resolve().parent / "data" / "admin_audit.jsonl"
_audit_lock = threading.Lock()


from config import settings as _cfg
from admin_permissions import (
    ADMIN_ROLE_SCOPES as ADMIN_ROLE_SCOPES,
    admin_scopes_for_user,
    filter_admin_badge_counts,
    filter_admin_dashboard_alerts,
    has_admin_entry_scope as _has_admin_entry_scope,
)
_AUDIT_MAX_LINES = _cfg.AUDIT_MAX_LINES
_AUDIT_MAX_BYTES = 10 * 1024 * 1024  # B5b: rotate cũng khi file > 10MB (không chỉ khi vượt số dòng)



ADMIN_SCOPE_RULES: tuple[tuple[str, str], ...] = (
    ("/admin/users", "security.admin"),
    ("/admin/audit-log", "security.admin"),
    ("/admin/activity-feed", "security.admin"),
    ("/admin/user-engagement", "security.admin"),
    ("/admin/user-growth", "security.admin"),
    ("/admin/site-settings", "settings.admin"),
    ("/admin/site-settings-history", "settings.admin"),
    ("/admin/llm-config", "settings.admin"),
    ("/admin/backup-trigger", "ops.deploy"),
    ("/admin/backup-status", "ops.deploy"),
    ("/admin/system-health", "ops.deploy"),
    ("/admin/ops-summary", "ops.deploy"),
    ("/admin/cost-overview", "ops.deploy"),
    ("/admin/analytics-overview", "ops.deploy"),
    ("/admin/search-analytics", "ops.deploy"),
    ("/admin/trigger-learn", "ops.deploy"),
    ("/admin/ai", "ops.deploy"),
    ("/admin/export", "ops.deploy"),
    ("/admin/notifications/cleanup", "ops.deploy"),
    ("/admin/cleanup-orphan-refs", "ops.deploy"),
    ("/admin/moderation", "moderation.manager"),
    ("/admin/reports", "moderation.manager"),
    ("/admin/info-reports", "moderation.manager"),
    ("/admin/appeals", "moderation.manager"),
    ("/admin/comments", "moderation.manager"),
    ("/admin/posts", "moderation.manager"),
    ("/admin/qa-queue", "moderation.manager"),
    ("/admin/content/search", "moderation.manager"),
    ("/admin/content-stats", "moderation.manager"),
    ("/admin/entities", "content.editor"),
    ("/admin/unclassified", "content.editor"),
    ("/admin/itineraries", "content.editor"),
    ("/admin/relationships", "content.editor"),
    ("/admin/data-quality", "content.editor"),
    ("/admin/stale-queue", "content.editor"),
    ("/admin/completeness", "content.editor"),
    ("/admin/contact-funnel", "content.editor"),
    ("/admin/collections", "content.editor"),
    ("/admin/image-suggestions", "content.editor"),
    ("/admin/featured", "content.editor"),
    ("/admin/media", "content.editor"),
    ("/admin/provisional", "content.editor"),
    ("/admin/sources", "content.editor"),
    ("/admin/claims", "content.editor"),
    ("/admin/announcements", "content.editor"),
    ("/admin/entity-completeness", "content.editor"),
    ("/admin/entity-kinds", "content.editor"),
    ("/admin/entity-schema", "content.editor"),
    ("/admin/stats", "ops.deploy"),
)

ADMIN_SCOPE_AWARE_READ_PATHS = frozenset({
    "/admin/badge-counts",
    "/admin/dashboard-alerts",
})

def _normalize_admin_path(path: str) -> str:
    normalized = "/" + (path or "").split("?", 1)[0].strip("/")
    if normalized.startswith("/admin-api/"):
        normalized = "/admin/" + normalized[len("/admin-api/"):]
    return normalized.rstrip("/") or "/admin"

def _admin_required_scope_for_path(path: str) -> str | None:
    normalized = _normalize_admin_path(path)
    for prefix, scope in ADMIN_SCOPE_RULES:
        if normalized == prefix or normalized.startswith(prefix + "/"):
            return scope
    return None


def _is_scope_aware_admin_read(request: Request) -> bool:
    return (
        request.method in ("GET", "HEAD", "OPTIONS")
        and _normalize_admin_path(request.url.path) in ADMIN_SCOPE_AWARE_READ_PATHS
    )

def _admin_actor_context(request: Request | None, actor: str) -> dict[str, Any]:
    user = getattr(getattr(request, "state", None), "admin_user", None) if request is not None else None
    scopes = getattr(getattr(request, "state", None), "admin_scopes", None) if request is not None else None
    request_id = ""
    if request is not None:
        request_id = request.headers.get("x-request-id") or request.headers.get("x-correlation-id") or ""
    return {
        "actor": actor,
        "actor_role": (user or {}).get("role") if user else ("admin-key" if actor == "admin-key" else ""),
        "actor_scopes": list(scopes or admin_scopes_for_user(user)),
        "request_id": request_id,
    }

def _ensure_admin_audit_events_table(conn) -> None:
    db._execute(conn, """
        CREATE TABLE IF NOT EXISTS admin_audit_events (
            id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            actor        TEXT NOT NULL,
            actor_role   TEXT,
            actor_scopes TEXT[] DEFAULT ARRAY[]::TEXT[],
            method       TEXT NOT NULL,
            path         TEXT NOT NULL,
            request_id   TEXT,
            ip           TEXT,
            reason       TEXT,
            before_json  JSONB,
            after_json   JSONB,
            meta         JSONB DEFAULT '{}'::JSONB
        )
    """, ())
    db._execute(conn, "CREATE INDEX IF NOT EXISTS idx_admin_audit_events_created_at ON admin_audit_events(created_at DESC)", ())

def _admin_audit_insert_params(record: dict[str, Any]) -> tuple:
    return (
        record.get("actor") or "unknown",
        record.get("actor_role") or None,
        record.get("actor_scopes") or [],
        record.get("method") or "",
        record.get("path") or "",
        record.get("request_id") or None,
        record.get("ip") or None,
        record.get("reason") or None,
        json.dumps(record.get("before"), ensure_ascii=False) if record.get("before") is not None else None,
        json.dumps(record.get("after"), ensure_ascii=False) if record.get("after") is not None else None,
        json.dumps(record.get("meta") or {}, ensure_ascii=False),
    )

def _log_admin_audit_db(record: dict[str, Any]) -> None:
    if not getattr(db, "_use_pg", False):
        return
    try:
        with db._conn() as conn:
            _ensure_admin_audit_events_table(conn)
            db._execute(conn, """
                INSERT INTO admin_audit_events
                    (actor, actor_role, actor_scopes, method, path, request_id, ip, reason, before_json, after_json, meta)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb)
            """, _admin_audit_insert_params(record))
    except Exception:
        logger.debug("Admin audit DB write skipped; JSONL fallback remains active", exc_info=True)

def _admin_audit_db_filters(
    method: str | None,
    q: str | None,
    date_from: str | None,
    date_to: str | None,
) -> tuple[list[str], list[Any]]:
    conditions: list[str] = []
    params: list[Any] = []
    if method:
        conditions.append("method = %s")
        params.append(method.upper())
    if q:
        conditions.append("(LOWER(path) LIKE %s OR LOWER(actor) LIKE %s)")
        like = f"%{_escape_like(q.lower())}%"
        params.extend([like, like])
    if date_from:
        conditions.append("created_at::date >= %s::date")
        params.append(date_from)
    if date_to:
        conditions.append("created_at::date <= %s::date")
        params.append(date_to)
    return conditions, params

def _admin_audit_row_to_entry(row) -> dict[str, Any]:
    item = db._row_to_dict(row)
    ts = item.get("created_at")
    return {
        "ts": ts.isoformat(timespec="seconds") if hasattr(ts, "isoformat") else str(ts or ""),
        "actor": item.get("actor"),
        "actor_role": item.get("actor_role"),
        "actor_scopes": item.get("actor_scopes") or [],
        "method": item.get("method"),
        "path": item.get("path"),
        "request_id": item.get("request_id"),
        "ip": item.get("ip"),
        "reason": item.get("reason"),
        "meta": item.get("meta") or {},
    }

def _query_admin_audit_db(
    limit: int,
    method: str | None = None,
    q: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict[str, Any] | None:
    if not getattr(db, "_use_pg", False):
        return None
    try:
        conditions, params = _admin_audit_db_filters(method, q, date_from, date_to)
        where_sql = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        with db._conn() as conn:
            total_row = db._fetchone(conn, f"SELECT COUNT(*) as c FROM admin_audit_events{where_sql}", tuple(params))
            rows = db._fetchall(conn, f"""
                SELECT created_at, actor, actor_role, actor_scopes, method, path, request_id, ip, reason, meta
                FROM admin_audit_events
                {where_sql}
                ORDER BY created_at DESC
                LIMIT %s
            """, tuple(params + [limit]))
        entries = [_admin_audit_row_to_entry(row) for row in rows or []]
        total = int(db._row_to_dict(total_row).get("c") or 0) if total_row else len(entries)
        return {"entries": entries, "total": total, "source": "db"}
    except Exception:
        logger.debug("Admin audit DB read unavailable; falling back to JSONL", exc_info=True)
        return None


def _log_admin_audit(
    actor: str,
    method: str,
    path: str,
    ip: str,
    request: Request | None = None,
    *,
    before: Any = None,
    after: Any = None,
    reason: str | None = None,
    meta: dict[str, Any] | None = None,
) -> None:
    """P2-7: ghi nhật ký thao tác admin (ai/làm-gì/khi-nào) — JSONL nhẹ, không chặn request."""
    rec = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "method": method,
        "path": path,
        "ip": ip,
        "before": before,
        "after": after,
        "reason": reason,
        "meta": meta or {},
        **_admin_actor_context(request, actor),
    }
    try:
        with _audit_lock:
            _AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(_AUDIT_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            _audit_cache["mtime"] = 0.0
            _maybe_rotate_audit()
    except Exception:
        logger.exception("Failed to write admin audit log")
    _log_admin_audit_db(rec)


def _maybe_rotate_audit() -> None:
    # B5b: rotate khi dòng > _AUDIT_MAX_LINES HOẶC file > _AUDIT_MAX_BYTES (OR — giữ cap dòng cũ).
    try:
        if not _AUDIT_FILE.exists():
            return
        lines = _AUDIT_FILE.read_text(encoding="utf-8").splitlines()
        over_count = len(lines) > _AUDIT_MAX_LINES
        over_size = _AUDIT_FILE.stat().st_size > _AUDIT_MAX_BYTES
        if not (over_count or over_size):
            return
        # Giữ tối đa _AUDIT_MAX_LINES dòng (như cũ); nếu chỉ vượt vì dung lượng (dòng dài,
        # ít dòng) thì cắt còn một nửa để đảm bảo dung lượng thực sự giảm.
        keep = min(_AUDIT_MAX_LINES, len(lines))
        if over_size and not over_count:
            keep = min(keep, max(1, len(lines) // 2))
        if keep >= len(lines):
            return
        archive = _AUDIT_FILE.with_suffix(f".{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.jsonl")
        archive.write_text("\n".join(lines[:-keep]) + "\n", encoding="utf-8")
        tmp = _AUDIT_FILE.with_suffix(".tmp")
        tmp.write_text("\n".join(lines[-keep:]) + "\n", encoding="utf-8")
        tmp.replace(_AUDIT_FILE)
    except Exception:
        logger.exception("Audit log rotation failed")


def _require_admin_rate_limit(request: Request) -> str:
    """Enforce admin rate limit; return client_ip on success, else raise 429."""
    client_ip = get_client_ip(request)
    allowed, rate_info = admin_limiter.is_allowed(client_ip)
    if not allowed:
        raise HTTPException(429, detail="Quá nhiều yêu cầu. Vui lòng thử lại sau.", headers={"Retry-After": str(rate_info["retry_after"])})
    return client_ip

async def _require_admin_mutation_side_effects(request: Request, actor: str, admin_user, client_ip: str) -> None:
    """CSRF + audit for mutating admin methods (extracted from require_admin)."""
    if admin_user is not None and request.method in ("POST", "PUT", "DELETE", "PATCH"):
        await require_csrf(request)
    # P2-7: audit các thao tác THAY ĐỔI (đọc/GET không log để tránh nhiễu)
    if request.method in ("POST", "PUT", "DELETE", "PATCH"):
        _log_admin_audit(actor, request.method, request.url.path, client_ip, request=request)

async def require_admin(request: Request, required_scope_override: str | None = None):
    """FastAPI dependency: verify admin auth + rate limit (+ audit log mọi mutation)."""
    # Rate limit
    client_ip = _require_admin_rate_limit(request)
    # Auth: allow server-side admin key or a logged-in admin user from the frontend.
    actor = None
    user = None
    if verify_admin_key(request):
        actor = "admin-key"
    else:
        user = await get_current_user(request)
        if user and _has_admin_entry_scope(user):
            actor = f"user:{user.get('id')}"
    if not actor:
        raise HTTPException(401, detail="Xác thực admin không hợp lệ. Sử dụng X-Admin-Key hoặc phiên làm việc admin.")
    admin_user = user if actor != "admin-key" else None
    request.state.admin_user = admin_user
    request.state.admin_actor = actor
    request.state.admin_scopes = admin_scopes_for_user(admin_user)
    required_scope = required_scope_override or _admin_required_scope_for_path(request.url.path)
    request.state.admin_required_scope = required_scope
    if required_scope:
        _ensure_admin_scope(request, required_scope)
    elif admin_user is not None and not _is_scope_aware_admin_read(request):
        # Default-deny mọi route không có scope. Chỉ endpoint GET tự lọc response theo
        # workstream mới được khai trong ADMIN_SCOPE_AWARE_READ_PATHS.
        _ensure_admin_scope(request, "*")
    if admin_user is not None:
        request.state.user = admin_user
    await _require_admin_mutation_side_effects(request, actor, admin_user, client_ip)

async def require_admin_scope(request: Request, scope: str):
    """Verify admin auth and require an explicit RBAC scope for non-admin routes."""
    await require_admin(request, required_scope_override=scope)


ROOT = Path(__file__).resolve().parent.parent

# Ha tang admin dung chung — tach 2026-08-28 (buoc 2a cua lat entity-admin).
# Ca mien entity-admin sap boc LAN phan con lai cua file nay deu goi; de
# nguyen la mien moi phai import nguoc admin.py 5.900 dong. Tai xuat de bo
# test hien co van va duoc qua `admin.<ten>`.
from admin_common import (  # noqa: F401
    _CSV_FORMULA_PREFIXES,
    _admin_volatile_caches,
    _csv_cell,
    _csv_row,
    _ensure_admin_scope,
    _invalidate_admin_caches,
    _log_mod_action,
    _mask,
    _require_admin_actor_id,
    _safe,
    _sync_kb,
)

# Mien ENTITY mat quan tri sang agent/entities/admin_api.py (2026-08-28, buoc
# 2b) — hoan tat goi mien entity theo khuon cases/. Tai xuat de bo test hien
# co van va duoc qua `admin.<ten>`; router con duoc include TRUOC
# _fix_admin_route_order (cong R20.9 chi thay mount qua include_router).
from entities.admin_api import (  # noqa: F401
    AssignPlaceRequest,
    BulkAssignPlaceRequest,
    BulkDeleteRequest,
    ClaimDecisionBody,
    CollectionCreate,
    CollectionUpdate,
    EntityCreate,
    EntityUpdate,
    ImageSuggestionBatch,
    ImageSuggestionItem,
    ProvisionalDecisionBody,
    RejectSuggestionRequest,
    RelationshipBulkCreate,
    RelationshipBulkPair,
    RelationshipCreate,
    VALID_TYPES,
    _COMPLETENESS_UNIVERSAL,
    _EntityImageURL,
    _MEDIA_TTL,
    _PINNED_HTTP,
    _STALE_THRESHOLD_DEFAULT,
    _admin_image_egress_policy,
    _approve_attach_credits,
    _approve_fetch_image_data,
    _bulk_assign_entities,
    _completeness_detail_missing_hit,
    _completeness_detail_record,
    _completeness_fetch_ents,
    _completeness_has,
    _completeness_registry_fields,
    _completeness_universal_fields,
    _extract_media_items,
    _image_policy_http_error,
    _list_entities_add_places,
    _list_entities_attach_place_names,
    _list_entities_fetch,
    _list_entities_fetch_place_rows,
    _list_entities_filter_orphans,
    _media_cache,
    _media_credits_by_url,
    _media_item_from_image,
    _media_parse_json_field,
    _media_resolve_credit,
    _reject_non_ai_media,
    _require_ai_only_entity_images,
    _sanitize,
    _stale_days_since,
    _stale_entity_record,
    _stale_missing_fields,
    _validate_public_image_url,
    add_entity_image_url,
    add_relationship,
    add_relationships_bulk,
    approve_claim,
    approve_image_suggestion,
    approve_provisional,
    assign_place,
    bulk_assign_place,
    bulk_delete,
    check_duplicate,
    completeness_details,
    completeness_overview,
    create_collection,
    create_entity,
    create_image_suggestion_batch,
    delete_collection,
    delete_entity,
    delete_relationship,
    entity_completeness,
    entity_kinds,
    get_entity,
    get_entity_history,
    get_entity_schema,
    get_image_suggestion,
    list_claims,
    list_collections,
    list_entities,
    list_featured,
    list_image_suggestions,
    list_places,
    list_provisional_entities,
    list_unclassified,
    media_gallery,
    reject_claim,
    reject_image_suggestion,
    reject_provisional,
    remove_entity_image,
    stale_mark_reviewed,
    stale_queue,
    toggle_featured,
    update_collection,
    update_entity,
    upload_entity_image,
)

# Mien CONG DONG mat quan tri sang agent/community/admin_api.py (2026-08-29,
# lat 1 dot cat module) — goi mien cong dong du hai mat theo khuon cases/.
# Tai xuat de bo test hien co van va duoc qua `admin.<ten>`; router con duoc
# include TRUOC _fix_admin_route_order (cong R20.9 chi thay mount qua
# include_router).
from community.admin_api import (  # noqa: F401
    ADMIN_ROLE_RANKS,
    AdminUserNote,
    AppealDecisionBody,
    BatchModerationBody,
    BulkReportAction,
    BulkUserAction,
    ModNoteBody,
    RejectBody,
    ReviewResponseBody,
    SetBestAnswerBody,
    _admin_user_detail_stats,
    _admin_user_last_login,
    _apply_bulk_bans,
    _assert_actor_can_manage_target,
    _assert_not_last_admin,
    _assert_role_change_allowed,
    _batch_mod_collect,
    _batch_mod_notify,
    _batch_mod_query,
    _batch_mod_transition,
    _bulk_ban_query,
    _list_users_role_counts,
    _list_users_where,
    _mod_post,
    add_moderation_note,
    add_user_note,
    admin_content_search,
    admin_delete_comment,
    admin_list_comments,
    admin_post_detail,
    admin_review_response,
    admin_user_detail,
    admin_user_mutes,
    admin_user_reactions,
    approve_appeal,
    approve_post,
    ban_user,
    batch_moderation,
    bulk_ban_users,
    bulk_report_action,
    bulk_unban_users,
    content_stats,
    delete_review_response,
    delete_user_note,
    dismiss_report,
    export_posts_csv,
    export_users_csv,
    feature_post,
    get_moderation_notes,
    get_reports,
    get_review_response,
    get_user_notes,
    list_appeals,
    list_users,
    moderation_history,
    moderation_queue,
    moderation_stats,
    qa_queue,
    qa_set_best_answer,
    reject_appeal,
    reject_post,
    resolve_report,
    set_user_role,
    unban_user,
    user_engagement_stats,
    user_growth,
)

# Mien VAN HANH SITE (data-quality / system-health / backup / ops-summary /
# export toan-DB / site-settings / announcements admin) sang
# agent/siteops/admin_api.py (2026-08-29, lat 3 dot cat module). Tai xuat de bo
# test hien co van va duoc qua `admin.<ten>`; router con duoc include TRUOC
# _fix_admin_route_order (cong R20.9 chi thay mount qua include_router).
# KHONG tai xuat `_last_backup_time`: state module MUTABLE (global re-bind trong
# trigger_backup) — alias float chi la snapshot, tro thanh so cu ngay lan backup
# dau; ai can doc thi doc `siteops.admin_api._last_backup_time`.
from siteops.admin_api import (  # noqa: F401
    AnnouncementCreate,
    AnnouncementUpdate,
    BulkSettingUpdate,
    DataQualityApplyRequest,
    DataQualityDecisionRequest,
    SettingUpdate,
    _BACKUP_COOLDOWN,
    _QUALITY_TREND_KEYS,
    _SETTING_KEY_RE,
    _admin_actor_label,
    _data_quality_ops_snapshot,
    _format_uptime,
    _latest_backup_info,
    _ops_audit_snapshot,
    _ops_moderation_snapshot,
    _quality_trend_budget_failure,
    _quality_trend_fetch_rows,
    _quality_trend_meta,
    _quality_trend_ops_snapshot,
    _quality_trend_process_latest,
    _server_start_time,
    _system_health_pg,
    _system_health_server,
    admin_bulk_update_settings,
    admin_get_all_settings,
    admin_get_settings_by_category,
    admin_reset_category,
    admin_site_settings_history,
    admin_site_settings_rollback,
    admin_update_setting,
    backup_status,
    create_announcement,
    data_quality_apply,
    data_quality_decision,
    data_quality_history,
    data_quality_review,
    data_quality_rollback,
    data_quality_summary,
    delete_announcement,
    export_data,
    list_announcements,
    ops_summary,
    system_health,
    trigger_backup,
    update_announcement,
)

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin), Depends(require_csrf)])


# ── Models ──


# Entity types + per-type attribute schemas come from the content-model registry
# (agent/entity_schemas.py) — single source of truth so adding a type touches one
# file, not many (DoD-7). This fixes the old TYPE_META(17) vs VALID_TYPES(13)
# mismatch where restaurant/cafe/drink/place/itinerary 422'd on save.





# ── Entity CRUD ──



























































# ── Itinerary CRUD: sang itineraries/admin_api.py (2026-08-29, lát 2 đợt cắt
# module) — mount lại vào router này ở cuối file, TRƯỚC _fix_admin_route_order(),
# như miền entity/community. ──


# ── Relationship CRUD ──






# ── Bulk operations ──

# Data-quality review queue (6 route, co B7 apply/rollback): sang
# siteops/admin_api.py (2026-08-29, lat 3).

# ── Stale content queue (U-17) ──

_STALE_QUEUE_MISSING_FIELDS = {"source", "images", "coordinates", "phone", "summary"}












# ── Completeness standalone (BE-10) ──












# ── Contact funnel dashboard (U-22) ──

CONTACT_VIEWS_FILE = Path(__file__).resolve().parent / "data" / "contact_views.jsonl"


@router.get("/contact-funnel",
            summary="Contact funnel analytics",
            description="Returns contact interaction statistics (zalo, phone, website, map clicks) per entity for a given time period.")
async def contact_funnel(
    days: int = Query(30, ge=1, le=365),
    entity_id: Optional[str] = Query(None, max_length=100),
):
    """Thống kê click vào thông tin liên hệ — zalo/phone/website/map."""
    def _query():
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        if not CONTACT_VIEWS_FILE.exists():
            return {"entities": [], "period_days": days, "total_contacts": 0}
        if CONTACT_VIEWS_FILE.stat().st_size > 20 * 1024 * 1024:
            return {"entities": [], "period_days": days, "total_contacts": 0, "warning": "Log quá lớn, cần rotation"}
        counts, total = _contact_funnel_tally(cutoff, entity_id)
        entities_list = _contact_funnel_entities(counts)
        return {"entities": entities_list, "period_days": days, "total_contacts": total}
    return await asyncio.to_thread(_query)


def _contact_funnel_accumulate(rec, cutoff, entity_id, counts) -> bool:
    """Fold one log record into `counts`; return True if it counted, False if skipped."""
    ts_str = rec.get("ts", "")
    try:
        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return False
    if ts < cutoff:
        return False
    eid = rec.get("entity_id", "")
    if entity_id and eid != entity_id:
        return False
    action = rec.get("action", "other")
    if eid not in counts:
        counts[eid] = {"zalo": 0, "phone": 0, "website": 0, "map": 0, "total": 0}
    counts[eid][action] = counts[eid].get(action, 0) + 1
    counts[eid]["total"] += 1
    return True


def _contact_funnel_tally(cutoff, entity_id):
    counts: dict[str, dict[str, int]] = {}
    total = 0
    with open(CONTACT_VIEWS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            if _contact_funnel_accumulate(rec, cutoff, entity_id, counts):
                total += 1
    return counts, total


def _contact_funnel_entities(counts):
    entities_list = []
    ent_dict = knowledge._entities if getattr(knowledge, "_entities", None) else {}
    for eid, c in sorted(counts.items(), key=lambda x: -x[1]["total"]):
        e = ent_dict.get(eid, {})
        entities_list.append({
            "id": eid,
            "name": e.get("name", eid),
            "zalo": c["zalo"],
            "phone": c["phone"],
            "website": c["website"],
            "map": c["map"],
            "total": c["total"],
        })
    return entities_list


@router.get("/contact-funnel/export",
            summary="Export contact funnel as CSV",
            description="Exports contact funnel data as a downloadable CSV file with per-entity interaction counts.")
async def contact_funnel_export(days: int = Query(30, ge=1, le=365)):
    """Export contact funnel dạng CSV."""

    def _generate():
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        counts: dict[str, dict[str, int]] = {}
        if CONTACT_VIEWS_FILE.exists():
            with open(CONTACT_VIEWS_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except (json.JSONDecodeError, ValueError):
                        continue
                    ts_str = rec.get("ts", "")
                    try:
                        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        continue
                    if ts < cutoff:
                        continue
                    eid = rec.get("entity_id", "")
                    action = rec.get("action", "other")
                    if eid not in counts:
                        counts[eid] = {"zalo": 0, "phone": 0, "website": 0, "map": 0, "total": 0}
                    counts[eid][action] = counts[eid].get(action, 0) + 1
                    counts[eid]["total"] += 1
        ent_dict = knowledge._entities if getattr(knowledge, "_entities", None) else {}
        yield _csv_row(["entity_id", "name", "zalo", "phone", "website", "map", "total"])
        for eid, c in sorted(counts.items(), key=lambda x: -x[1]["total"]):
            name = ent_dict.get(eid, {}).get("name") or eid
            yield _csv_row([
                eid, name, c["zalo"], c["phone"], c["website"], c["map"], c["total"],
            ])

    return StreamingResponse(_generate(), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=contact_funnel.csv"})


# ── Collections CRUD (U-28): sang entities/admin_api.py cạnh cụm /featured
# (lát 6 đợt cắt module 2026-08-29). Ký hiệu tái xuất ở block
# `from entities.admin_api import` đầu file; scope map "/admin/collections"
# ở lại ADMIN_SCOPE_RULES vì khớp theo path.







# ══════════════════════════════════════════════════
#  IMAGE INGEST REVIEW QUEUE (P2, review-gated — B6)
# ══════════════════════════════════════════════════
# Human-in-the-loop: ingest scripts queue licensed image CANDIDATES; nothing goes
# live until an admin approves here. On approve we re-encode + upload to R2 and
# carry license + author + source onto the entity (attributes.image_credits) per B6.

import image_suggestions as _imgq


























# ── Data management ──

# System-health + uptime: sang siteops/admin_api.py (2026-08-29, lat 3).






@router.get("/stats",
            summary="Get admin dashboard statistics",
            description="Returns detailed statistics including entity counts by type, completeness scores, weekly deltas, and backup info.")
async def admin_stats(compare_days: int = Query(7, ge=1, le=90)):
    """Thống kê chi tiết cho admin.

    B1d: compare_days cho phép đổi cửa sổ so-sánh (mặc định 7 → giữ nguyên output cũ).
    """
    def _query():
        db.initialize()
        ph = db._ph
        with db._conn() as conn:
            rel_count = db._fetchone(conn, "SELECT COUNT(*) as c FROM relationships", ())
            itin_count = db._fetchone(conn, "SELECT COUNT(*) as c FROM itineraries", ())

        by_type, total_entities, total_places = _admin_stats_entity_counts()
        completeness = _admin_stats_completeness()

        # B1d: cửa sổ so-sánh cấu hình được qua compare_days (mặc định 7 ngày — giữ nguyên hành vi cũ).
        interval_pg = f"{compare_days} days"

        deltas = {}
        if db._use_pg:
            try:
                with db._conn() as pg:
                    users_week = db._fetchone(pg, f"SELECT COUNT(*) as c FROM users WHERE created_at > NOW() - CAST({ph} AS INTERVAL)", (interval_pg,))
                    posts_week = db._fetchone(pg, f"SELECT COUNT(*) as c FROM posts WHERE created_at > NOW() - CAST({ph} AS INTERVAL)", (interval_pg,))
                    total_users = db._fetchone(pg, "SELECT COUNT(*) as c FROM users", ())
                    total_posts = db._fetchone(pg, "SELECT COUNT(*) as c FROM posts", ())
                deltas = {
                    "users_week": db._row_to_dict(users_week)["c"] if users_week else 0,
                    "posts_week": db._row_to_dict(posts_week)["c"] if posts_week else 0,
                    "total_users": db._row_to_dict(total_users)["c"] if total_users else 0,
                    "total_posts": db._row_to_dict(total_posts)["c"] if total_posts else 0,
                }
            except Exception:
                logger.debug("Stats PG deltas query failed", exc_info=True)

        entities_week = _admin_stats_entities_week(ph, interval_pg, compare_days)
        backup_info = _admin_stats_backup_info()

        return {
            "total_entities": total_entities,
            "total_places": total_places,
            "total_relationships": db._row_to_dict(rel_count)["c"] if rel_count else 0,
            "total_itineraries": db._row_to_dict(itin_count)["c"] if itin_count else 0,
            "by_type": by_type,
            "completeness": completeness,
            "entities_week": entities_week,
            "backup": backup_info,
            **deltas,
        }
    return await asyncio.to_thread(_query)


def _admin_stats_entity_counts():
    with db._conn() as conn:
        type_rows = db._fetchall(conn, "SELECT type, COUNT(*) as c FROM entities GROUP BY type", ())
    by_type = {}
    total_entities = 0
    total_places = 0
    for r in type_rows:
        d = db._row_to_dict(r)
        if d["type"] == "place":
            total_places = d["c"]
        else:
            by_type[d["type"]] = d["c"]
            total_entities += d["c"]
    return by_type, total_entities, total_places


def _admin_stats_completeness():
    with db._conn() as c2:
        # PG: images là JSONB (so sánh với '' bắt PG parse '' thành JSON → 500);
        # placeId phải quoted. SQLite: images là TEXT — giữ nguyên so sánh chuỗi.
        if db._use_pg:
            comp_sql = """
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN summary IS NOT NULL AND summary != '' THEN 1 ELSE 0 END) as has_summary,
                   SUM(CASE WHEN images IS NOT NULL AND jsonb_typeof(images) = 'array' AND jsonb_array_length(images) > 0 THEN 1 ELSE 0 END) as has_images,
                   SUM(CASE WHEN "placeId" IS NOT NULL AND "placeId" != '' THEN 1 ELSE 0 END) as has_place
            FROM entities WHERE type != 'place'
            """
        else:
            comp_sql = """
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN summary IS NOT NULL AND summary != '' THEN 1 ELSE 0 END) as has_summary,
                   SUM(CASE WHEN images IS NOT NULL AND images != '' AND images != '[]' THEN 1 ELSE 0 END) as has_images,
                   SUM(CASE WHEN placeId IS NOT NULL AND placeId != '' THEN 1 ELSE 0 END) as has_place
            FROM entities WHERE type != 'place'
            """
        comp = db._fetchone(c2, comp_sql, ())
        cd = db._row_to_dict(comp) if comp else {}
        comp_total = cd.get("total", 0)
        has_summary = cd.get("has_summary", 0)
        has_images = cd.get("has_images", 0)
        has_place = cd.get("has_place", 0)
        orphan_row = db._fetchone(c2, """
            SELECT COUNT(*) as c FROM entities
            WHERE type != 'place'
              AND id NOT IN (SELECT DISTINCT from_id FROM relationships UNION SELECT DISTINCT to_id FROM relationships)
        """, ())
        orphan_count = db._row_to_dict(orphan_row)["c"] if orphan_row else 0
    return {
        "total": comp_total,
        "has_summary": has_summary,
        "has_images": has_images,
        "has_place": has_place,
        "orphans": orphan_count,
        "pct": round((has_summary + has_images + has_place) / (comp_total * 3) * 100, 1) if comp_total else 0,
    }


def _admin_stats_entities_week(ph, interval_pg, compare_days) -> int:
    entities_week = 0
    try:
        if db._use_pg:
            week_sql = f"SELECT COUNT(*) as c FROM entities WHERE type != 'place' AND created_at >= NOW() - CAST({ph} AS INTERVAL)"
            week_params = (interval_pg,)
        else:
            week_sql = f"SELECT COUNT(*) as c FROM entities WHERE type != 'place' AND created_at >= datetime('now', {ph})"
            week_params = (f"-{compare_days} days",)
        with db._conn() as c3:
            ew = db._fetchone(c3, week_sql, week_params)
            entities_week = db._row_to_dict(ew)["c"] if ew else 0
    except Exception:
        logger.debug("Stats entities_week query failed", exc_info=True)
    return entities_week


def _admin_stats_backup_info():
    backup_info = None
    try:
        backup_dir = Path(__file__).resolve().parent.parent / "scratch" / "backups"
        if backup_dir.exists():
            dirs = sorted(backup_dir.iterdir(), key=lambda p: p.name, reverse=True)
            if dirs:
                latest = dirs[0]
                size_mb = round(sum(f.stat().st_size for f in latest.rglob("*") if f.is_file()) / 1048576, 1)
                backup_info = {"last": latest.name, "size_mb": size_mb, "count": len(dirs)}
    except Exception:
        logger.debug("Stats backup info scan failed", exc_info=True)
    return backup_info


# Backup-status + ops-summary + backup-trigger (B1) + cac snapshot van hanh:
# sang siteops/admin_api.py (2026-08-29, lat 3).

















@router.get("/badge-counts",
            summary="Get admin dashboard badge counts",
            description="Returns lightweight counts for sidebar badges including moderation, images, unclassified entities, provisional items, and reports.")
async def badge_counts(request: Request):
    """Lightweight counts cho sidebar badges — cached 60s to avoid repeated DB+JSONL parsing."""
    def _query():
        import time as _time
        now = _time.time()
        if _badge_cache["data"] is not None and (now - _badge_cache["ts"]) < _BADGE_TTL:
            return _badge_cache["data"]
        counts = {"moderation": 0, "images": 0, "unclassified": 0, "provisional": 0, "reports": 0}
        if db._use_pg:
            with db._conn() as conn:
                row = db._fetchone(conn, "SELECT COUNT(*) as c FROM posts WHERE moderation_status IN ('pending','review','flagged')", ())
                if row:
                    counts["moderation"] = db._row_to_dict(row)["c"]
                report_row = db._fetchone(conn, "SELECT COUNT(*) as c FROM reports WHERE status = 'pending'", ())
                if report_row:
                    counts["reports"] += db._row_to_dict(report_row)["c"]
        try:
            counts["images"] = _imgq.status_counts().get("pending", 0)
        except Exception:
            logger.debug("Badge image queue count failed", exc_info=True)
        with db._conn() as conn2:
            _pid = '"placeId"' if db._use_pg else "placeId"
            unc_row = db._fetchone(conn2, f"SELECT COUNT(*) as c FROM entities WHERE type != 'place' AND ({_pid} IS NULL OR {_pid} = '')", ())
            counts["unclassified"] = db._row_to_dict(unc_row)["c"] if unc_row else 0
        try:
            import kb_curation
            s = kb_curation.normalize_curation_summary(kb_curation.stats())
            counts["provisional"] = s["provisional_count"]
        except Exception:
            logger.debug("Badge kb_curation stats failed", exc_info=True)
        counts["reports"] += _count_open_info_reports()
        _badge_cache["data"] = counts
        _badge_cache["ts"] = now
        return counts
    counts = await asyncio.to_thread(_query)
    scopes = getattr(request.state, "admin_scopes", [])
    return filter_admin_badge_counts(counts, scopes)


@router.get("/dashboard-alerts",
            summary="Get dashboard alert notifications",
            description="Returns priority-sorted alerts for the admin dashboard. Scans moderation, reports, images, unclassified entities, provisional items, and appeals queues.")
async def dashboard_alerts(request: Request):
    """Priority-sorted alerts cho admin dashboard."""
    def _query():
        alerts: list[dict] = []
        flagged = 0
        pending_mod = 0
        open_reports = 0
        if db._use_pg:
            with db._conn() as conn:
                mod = db._fetchone(conn, "SELECT COUNT(*) as c FROM posts WHERE moderation_status IN ('flagged')", ())
                flagged = db._row_to_dict(mod)["c"] if mod else 0
                mod2 = db._fetchone(conn, "SELECT COUNT(*) as c FROM posts WHERE moderation_status IN ('pending','review')", ())
                pending_mod = db._row_to_dict(mod2)["c"] if mod2 else 0
                report_row = db._fetchone(conn, "SELECT COUNT(*) as c FROM reports WHERE status = 'pending'", ())
                open_reports += db._row_to_dict(report_row)["c"] if report_row else 0
        if flagged:
            alerts.append({"type": "flagged", "count": flagged, "label": f"{flagged} bài viết bị gắn cờ", "icon": "🚩", "link": "/admin/kiem-duyet?tab=flagged", "priority": 1})
        if pending_mod:
            alerts.append({"type": "moderation", "count": pending_mod, "label": f"{pending_mod} bài chờ duyệt", "icon": "📝", "link": "/admin/kiem-duyet", "priority": 2})
        open_reports += _count_open_info_reports()
        if open_reports:
            alerts.append({"type": "reports", "count": open_reports, "label": f"{open_reports} báo cáo chưa xử lý", "icon": "⚠️", "link": "/admin/bao-cao", "priority": 3})
        _dashboard_alerts_images(alerts)
        _dashboard_alerts_unclassified(alerts)
        _dashboard_alerts_provisional(alerts)
        _dashboard_alerts_appeals(alerts)
        alerts.sort(key=lambda a: a["priority"])
        return {"alerts": alerts}
    payload = await asyncio.to_thread(_query)
    scopes = getattr(request.state, "admin_scopes", [])
    visible_alerts = filter_admin_dashboard_alerts(payload["alerts"], scopes)
    return {"alerts": visible_alerts[:5]}


def _dashboard_alerts_images(alerts) -> None:
    try:
        img_pending = _imgq.status_counts().get("pending", 0)
        if img_pending:
            alerts.append({"type": "images", "count": img_pending, "label": f"{img_pending} ảnh chờ duyệt", "icon": "🖼️", "link": "/admin/duyet-anh", "priority": 4})
    except Exception:
        logger.debug("Alert image queue count failed", exc_info=True)


def _dashboard_alerts_unclassified(alerts) -> None:
    with db._conn() as conn2:
        _pid = '"placeId"' if db._use_pg else "placeId"
        unc_row = db._fetchone(conn2, f"SELECT COUNT(*) as c FROM entities WHERE type != 'place' AND ({_pid} IS NULL OR {_pid} = '')", ())
        unc_count = db._row_to_dict(unc_row)["c"] if unc_row else 0
    if unc_count:
        alerts.append({"type": "unclassified", "count": unc_count, "label": f"{unc_count} entity chưa phân loại", "icon": "📍", "link": "/admin/chua-phan-loai", "priority": 5})


def _dashboard_alerts_provisional(alerts) -> None:
    try:
        import kb_curation
        s = kb_curation.normalize_curation_summary(kb_curation.stats())
        prov = s["provisional_count"]
        if prov:
            alerts.append({"type": "provisional", "count": prov, "label": f"{prov} entity chờ xét duyệt", "icon": "🔬", "link": "/admin/duyet-tu-hoc", "priority": 6})
    except Exception:
        logger.debug("Alert kb_curation stats failed", exc_info=True)


def _dashboard_alerts_appeals(alerts) -> None:
    try:
        with db._conn() as conn3:
            appeal_row = db._fetchone(conn3, "SELECT COUNT(*) as c FROM moderation_appeals WHERE status = 'pending'", ())
        appeal_count = db._row_to_dict(appeal_row)["c"] if appeal_row else 0
        if appeal_count:
            alerts.append({"type": "appeals", "count": appeal_count, "label": f"{appeal_count} khiếu nại chờ xử lý", "icon": "📩", "link": "/admin/kiem-duyet", "priority": 2})
    except Exception:
        logger.debug("Alert appeals count failed", exc_info=True)


@router.get("/activity-feed",
            summary="Recent admin activity feed",
            description="Returns the most recent admin actions from the audit JSONL log file. Defaults to 10 entries.")
async def activity_feed(limit: int = Query(10, ge=1, le=50)):
    """10 admin actions gần nhất từ audit JSONL."""
    def _query():
        db_audit = _query_admin_audit_db(limit)
        if db_audit is not None:
            logger.debug("Activity feed served from admin audit DB")
            return {"actions": db_audit.get("entries", []), "source": "db"}
        if not _AUDIT_FILE.exists():
            return {"actions": []}
        try:
            lines = _AUDIT_FILE.read_text(encoding="utf-8").strip().split("\n")
            actions = []
            for line in reversed(lines):
                if not line.strip():
                    continue
                try:
                    actions.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
                if len(actions) >= limit:
                    break
            return {"actions": actions}
        except Exception:
            logger.debug("Activity feed read failed", exc_info=True)
            return {"actions": []}
    return await asyncio.to_thread(_query)


_learn_proc: Optional[subprocess.Popen] = None

@router.post("/trigger-learn",
             summary="Trigger knowledge learning",
             description="Starts a background auto-learn cycle that discovers and ingests new knowledge topics. Optionally filtered by category.")
async def trigger_learn(category: Optional[str] = Query(None, max_length=50), topics: int = 3):
    """Trigger 1 vòng auto-learn (chạy background)."""
    if topics < 1 or topics > 20:
        raise HTTPException(400, "Số chủ đề phải từ 1 đến 20")
    if category:
        if len(category) > 50 or not re.match(r'^[\w\s\-À-ɏḀ-ỿ]+$', category):
            raise HTTPException(400, "Danh mục không hợp lệ — chỉ chấp nhận chữ, số, dấu gạch (tối đa 50 ký tự)")
    cmd = [sys.executable, str(ROOT / "agent" / "auto_learn.py"), "--apply", "--topics", str(topics)]
    if category:
        cmd.extend(["--category", category])

    def _start():
        global _learn_proc
        if _learn_proc is not None and _learn_proc.poll() is None:
            raise HTTPException(409, f"Auto-learn đang chạy (PID {_learn_proc.pid}). Vui lòng chờ xong.")
        try:
            _learn_proc = subprocess.Popen(
                cmd,
                cwd=str(ROOT),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
            return {
                "status": "started",
                "pid": _learn_proc.pid,
                "command": " ".join(cmd),
                "note": "Chạy background. Gọi POST /reload sau khi xong.",
            }
        except Exception:
            logger.exception("Auto-learn trigger failed")
            raise HTTPException(500, "Không thể khởi chạy auto-learn. Kiểm tra log server.")
    return await asyncio.to_thread(_start)


# ── Quarantine review queue (provisional auto-learned entities) ──









# Export toan-DB (POST /export): sang siteops/admin_api.py (2026-08-29, lat 3).




@router.get("/sources",
            summary="List data sources",
            description="Returns all unique data sources across entities with entity counts and sample entity IDs per source.")
async def list_sources():
    """Liệt kê tất cả nguồn dữ liệu."""
    def _query():
        with db._conn() as conn:
            rows = db._fetchall(conn,
                "SELECT source FROM entities WHERE type != 'place' AND source IS NOT NULL",
                ())
        sources: dict = {}
        for r in rows:
            raw = db._row_to_dict(r).get("source", "")
            if not raw:
                continue
            src = raw
            if isinstance(src, str):
                try:
                    src = json.loads(src)
                except Exception:
                    continue
            if isinstance(src, dict):
                key = src.get("title", "unknown")
                if key not in sources:
                    sources[key] = {"count": 0, "sample_url": src.get("url", "")}
                sources[key]["count"] += 1
        return {"sources": sources}
    return await asyncio.to_thread(_query)




@router.get("/analytics-overview",
            summary="Analytics dashboard overview",
            description="Returns aggregated analytics for the admin dashboard including popular queries, knowledge gaps, top entities, and cost reports.")
async def analytics_overview(days: int = Query(0, ge=0, le=365)):
    """GĐ9.6: gói số liệu cho trang admin Analytics (1 call, đã auth qua require_admin).

    - popular: user hỏi gì nhiều · gaps: câu bot bí (backlog nội dung) · costs: chi phí LLM.
    - days: 0 = tất cả, 7/30/90 = lọc theo khoảng thời gian.
    """
    since = None
    if days > 0:
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    def _query():
        return {
            "summary": _safe(lambda: analytics.get_summary(since=since), {}),
            "popular": _safe(lambda: analytics.get_popular_queries(20, since=since), []),
            "gaps": _safe(lambda: analytics.get_knowledge_gaps(20, since=since), []),
            "top_entities": _safe(lambda: analytics.get_top_entities(15), []),
            "costs": _safe(_get_cost_report, {}) if _HAS_COST else {"available": False},
            "daily": _safe(lambda: analytics.get_daily_stats(days or 30), []),
        }
    return await asyncio.to_thread(_query)


# ── Search analytics ──

@router.get("/search-analytics",
            summary="Search term analytics",
            description="Analyzes search query logs and returns top queries, zero-result queries, and total search count for a given period.")
async def search_analytics(days: int = Query(7, ge=1, le=90)):
    search_log = Path(__file__).resolve().parent / "data" / "search_queries.jsonl"  # noqa: ASYNC240 (dựng path rẻ; đọc file bọc asyncio.to_thread)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    def _read():
        if not search_log.exists():
            return {"top_queries": [], "zero_results": [], "total_searches": 0, "period_days": days}
        if search_log.stat().st_size > 20 * 1024 * 1024:
            return {"top_queries": [], "zero_results": [], "total_searches": 0, "period_days": days, "warning": "Log quá lớn, cần rotation"}
        queries = {}
        zero_result = {}
        total = 0
        with open(search_log, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                if r.get("ts", "") < cutoff:
                    continue
                total += 1
                q = r.get("q", "").strip().lower()
                if not q:
                    continue
                queries[q] = queries.get(q, 0) + 1
                if r.get("results", 0) == 0:
                    zero_result[q] = zero_result.get(q, 0) + 1
        top = sorted(queries.items(), key=lambda x: x[1], reverse=True)[:30]
        zeros = sorted(zero_result.items(), key=lambda x: x[1], reverse=True)[:20]
        return {
            "top_queries": [{"query": q, "count": c} for q, c in top],
            "zero_results": [{"query": q, "count": c} for q, c in zeros],
            "total_searches": total,
            "period_days": days,
        }
    return await asyncio.to_thread(_read)




# GĐ13.6f: báo-sai thông tin (facility/entity) & báo nội dung ẩn danh — kênh nhẹ JSONL
# (KHÔNG cần đăng nhập, không DB), tách khỏi UGC `reports` (Postgres) ở trên.
_INFO_REPORTS_FILE = Path(__file__).resolve().parent / "data" / "reports.jsonl"
# Moi handler goi create_notification da sang community/admin_api.py (2026-08-29)
# — giu import nhu TAI XUAT vi test_phase16_coverage
# (test_admin_imports_create_notification) van soi hasattr(admin, ...).
from notifications import create_notification  # noqa: F401
# Kept as an exported lock for the legacy lifecycle erasure adapter; report
# status mutations no longer use the JSONL file.
from jsonl_store import jsonl_lock as _info_reports_lock  # noqa: F401

_info_reports_cache: dict = {"mtime": 0.0, "count": 0}

def _count_open_info_reports() -> int:
    if not _INFO_REPORTS_FILE.exists():
        return 0
    try:
        mtime = _INFO_REPORTS_FILE.stat().st_mtime
    except OSError:
        return 0
    if mtime == _info_reports_cache["mtime"]:
        return _info_reports_cache["count"]
    try:
        lines = _INFO_REPORTS_FILE.read_text(encoding="utf-8").strip().split("\n")
        count = sum(1 for l in lines if l.strip() and json.loads(l).get("status", "open") == "open")
    except Exception:
        logger.debug("Info reports count failed", exc_info=True)
        count = 0
    _info_reports_cache["mtime"] = mtime
    _info_reports_cache["count"] = count
    return count

_badge_cache: dict = {"ts": 0.0, "data": None}
_admin_volatile_caches.append(_badge_cache)
_BADGE_TTL = 60.0


@router.get("/info-reports",
            summary="List information reports",
            description="List anonymous info-correction and content reports from the JSONL store, newest first. Returns open count for badge display.")
async def get_info_reports(limit: int = Query(100, ge=1, le=500)):
    """List canonical reports plus read-only legacy JSONL history."""
    def _query():
        items = []
        try:
            from reports.repository import ReportRepository
            items.extend(record.to_dict() for record in ReportRepository(db).list(limit=limit))
        except Exception:
            logger.debug("Canonical report list unavailable", exc_info=True)
        if _INFO_REPORTS_FILE.exists():
            with open(_INFO_REPORTS_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        items.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        items.sort(key=lambda r: str(r.get("created_at") or r.get("ts") or ""), reverse=True)
        open_count = sum(1 for r in items if r.get("status", "open") in {"open", "pending"})
        return {"reports": items[:limit], "total": len(items), "open": open_count}
    return await asyncio.to_thread(_query)


_audit_cache: dict = {"mtime": 0.0, "items": []}

@router.get("/audit-log",
            summary="Get admin audit log",
            description="Returns paginated audit log entries of admin actions. Supports filtering by HTTP method, search query, and date range.")
async def get_audit_log(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0, le=100000),
    method: Optional[str] = Query(None, max_length=10),
    q: Optional[str] = Query(None, max_length=200),
    date_from: Optional[str] = Query(None, max_length=20),
    date_to: Optional[str] = Query(None, max_length=20),
):
    """P2-7: nhật ký thao tác admin (mutation), mới nhất trước. Hỗ trợ filter server-side."""
    def _query():
        db_audit = _query_admin_audit_db(limit, method=method, q=q, date_from=date_from, date_to=date_to)
        if db_audit is not None:
            return db_audit
        if not _AUDIT_FILE.exists():
            return {"entries": [], "total": 0}
        items = _audit_log_load_items()
        filtered = _audit_log_filter(items, method, q, date_from, date_to)
        filtered.reverse()
        total = len(filtered)
        return {"entries": filtered[offset:offset + limit], "total": total}
    return await asyncio.to_thread(_query)


def _audit_log_load_items() -> list:
    """Load audit JSONL entries via the mtime-keyed cache; return a fresh list copy."""
    try:
        mtime = _AUDIT_FILE.stat().st_mtime
    except OSError:
        mtime = 0.0
    with _audit_lock:
        if mtime != _audit_cache["mtime"]:
            raw_items = []
            with open(_AUDIT_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        raw_items.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            _audit_cache["mtime"] = mtime
            _audit_cache["items"] = raw_items
        return list(_audit_cache["items"])


def _audit_log_filter_q(items, q) -> list:
    q_lower = q.lower()
    return [e for e in items if q_lower in (e.get("path") or "").lower() or q_lower in (e.get("actor") or "").lower()]


def _audit_log_filter(items, method, q, date_from, date_to) -> list:
    filtered = items
    if method:
        filtered = [e for e in filtered if e.get("method") == method.upper()]
    if q:
        filtered = _audit_log_filter_q(filtered, q)
    if date_from:
        filtered = [e for e in filtered if (e.get("ts") or "")[:10] >= date_from]
    if date_to:
        filtered = [e for e in filtered if (e.get("ts") or "")[:10] <= date_to]
    return filtered


class ReportActionRequest(BaseModel):
    report_id: str | None = Field(None, min_length=1, max_length=128)
    expected_revision: int = Field(1, ge=1, le=2_147_483_647)
    ts: str | None = Field(None, min_length=1, max_length=64)   # legacy JSONL locator
    status: str = Field(..., pattern="^(open|resolved|dismissed)$")


async def _transition_canonical_report(body: ReportActionRequest):
    from reports.models import ReportActor
    from reports.service import ReportService, ReportError
    try:
        status = "pending" if body.status == "open" else body.status
        record = await asyncio.to_thread(
            ReportService(database=db).transition,
            body.report_id,
            expected_revision=body.expected_revision,
            status=status,
            actor=ReportActor(actor_scope="admin", source_channel="admin"),
            reason=f"admin:{body.status}",
        )
    except ReportError as exc:
        raise HTTPException(exc.status, exc.code) from exc
    return {
        "success": True,
        "report_id": record.report_id,
        "new_status": record.status.value,
        "revision": record.revision,
    }


@router.post("/info-reports/action",
             summary="Update information report status",
             description="Change the status of a canonical information report to open, resolved, or dismissed. Legacy JSONL rows are read/import-only.")
async def info_report_action(body: ReportActionRequest):
    """Transition a canonical report; legacy JSONL is not a mutable store."""
    if body.report_id:
        return await _transition_canonical_report(body)
    if not body.ts:
        raise HTTPException(422, "report_id or ts is required")
    raise HTTPException(
        410,
        "legacy_report_mutation_disabled",
        headers={"X-Report-Legacy-Mode": "read_import_only"},
    )


@router.get("/cost-overview",
            summary="Get LLM and API cost overview",
            description="Returns LLM usage costs from the cost tracker and autonomous agent budget status. Helps monitor the monthly budget cap.")
async def cost_overview():
    """Bảng chi phí: chi phí LLM (cost_tracker) + ngân sách agent tự động (cap/dùng/còn).
    Bảo vệ ngân sách <1tr/tháng khi autonomous-LLM được bật."""
    def _query():
        out: dict = {"llm": {"available": False}, "agent_budget": {"enabled": False}}
        try:
            import autonomous_budget as ab
            out["agent_budget"] = ab.status()
        except Exception:
            logger.debug("Cost overview: autonomous_budget unavailable", exc_info=True)
        try:
            from cost_tracker import cost_attribution
            s = cost_attribution.get_summary()
            out["llm"] = {
                "available": True,
                "total_cost_usd": s.get("total_cost", 0),
                "total_calls": s.get("count", s.get("total_calls", 0)),
                "daily": cost_attribution.get_daily_costs(7),
            }
        except Exception:
            logger.debug("Cost overview: cost_tracker unavailable", exc_info=True)
        return out
    return await asyncio.to_thread(_query)


@router.post("/ai/triage",
             summary="AI-assisted admin triage",
             description="On-demand LLM call that suggests up to 3 priority admin actions based on current system state. Degrades gracefully if LLM is unavailable.")
async def ai_triage():
    """On-demand: trợ lý LLM gợi ý ≤3 việc quản trị ưu tiên từ tình hình hiện tại.
    Chỉ chạy KHI admin bấm (1 lần gọi LLM — KHÔNG vòng lặp nền, tôn trọng §B8).
    Trả context thô nếu LLM không khả dụng (degrade an toàn)."""
    def _query():
        ctx = []
        reports = []
        try:
            if _INFO_REPORTS_FILE.exists():
                for ln in _INFO_REPORTS_FILE.read_text(encoding="utf-8").splitlines():
                    if ln.strip():
                        reports.append(json.loads(ln))
        except Exception:
            logger.warning("Failed to parse info reports file: %s", _INFO_REPORTS_FILE)
        ctx.append(f"- Báo cáo sai thông tin: {len(reports)}")
        for r in reports[-5:]:
            ctx.append(f"    · [{r.get('target_type')}] {r.get('target_id')}: {str(r.get('reason', ''))[:60]}")
        raw = "\n".join(ctx) or "(không có dữ liệu)"

        try:
            from llm_config import get_client, get_model_mini
            resp = get_client().chat.completions.create(
                model=get_model_mini(), temperature=0.3, max_tokens=400, timeout=30,
                messages=[
                    {"role": "system", "content": "Bạn là trợ lý quản trị của vinhlong360. Dựa trên tình hình, đề xuất TỐI ĐA 3 việc ưu tiên xử lý, ngắn gọn, tiếng Việt, có thứ tự."},
                    {"role": "user", "content": f"Tình hình hiện tại:\n{raw}\n\nĐề xuất việc ưu tiên:"},
                ])
            return {"ok": True, "suggestion": resp.choices[0].message.content, "context": raw}
        except Exception:  # noqa: BLE001 - LLM down/budget → vẫn trả context để admin tự xử
            return {"ok": False, "suggestion": None, "context": raw,
                    "note": "LLM không khả dụng — xem tình hình thô bên dưới."}
    return await asyncio.to_thread(_query)








# ── Site-settings admin: sang siteops/admin_api.py (2026-08-29, lat 3) ──


# ══════════════════════════════════════════════════
#  LLM CONFIG — runtime AI configuration
# ══════════════════════════════════════════════════

@router.get("/llm-config",
            summary="Get LLM configuration",
            description="Retrieve the current LLM configuration with the API key masked.")
async def admin_get_llm_config():
    """Current LLM configuration (API key masked)."""
    import llm_config
    return await asyncio.to_thread(llm_config.get_status)


class LLMConfigUpdate(BaseModel):
    base_url: str = Field(..., min_length=1, max_length=500)
    api_key: str = Field(..., min_length=1, max_length=500)
    model: str = Field(..., min_length=1, max_length=100)
    model_mini: str = Field(..., min_length=1, max_length=100)


@router.put("/llm-config",
            summary="Update LLM configuration",
            description="Update the LLM configuration. Validates settings with a test API call before applying.")
async def admin_update_llm_config(body: LLMConfigUpdate):
    """Update LLM config. Validates with a test API call before applying."""
    import llm_config
    try:
        result = await asyncio.to_thread(
            llm_config.update_config,
            body.base_url, body.api_key, body.model, body.model_mini,
        )
    except ValueError as e:
        logger.warning("LLM config update rejected: %s", e)
        raise HTTPException(400, detail="Cấu hình LLM không hợp lệ")
    return {"success": True, "config": result}


@router.post("/llm-config/reset",
             summary="Reset LLM config to defaults",
             description="Reset the LLM configuration back to values from environment variables.")
async def admin_reset_llm_config():
    """Reset LLM config to environment variables."""
    import llm_config
    result = await asyncio.to_thread(llm_config.reset_to_env)
    return {"success": True, "config": result}


# admin_cleanup_notifications → notifications.py admin_router (lát 5, 2026-08-29)


def _orphan_entity_ids(rows, valid_ids) -> list:
    """Return entity_ids from `rows` that are not present in `valid_ids` (dict/tuple-row safe)."""
    def _eid(r):
        return r[0] if not hasattr(r, 'keys') else db._row_to_dict(r)["entity_id"]
    return [_eid(r) for r in rows if _eid(r) not in valid_ids]


@router.post("/cleanup-orphan-refs",
             summary="Clean up orphaned entity references",
             description="Remove UGC records that reference entity IDs no longer present in the knowledge base.")
async def admin_cleanup_orphan_entity_refs():
    """Remove UGC records referencing entity IDs that no longer exist in knowledge base."""
    if not db._use_pg:
        raise HTTPException(503, detail="Chức năng này yêu cầu PostgreSQL")
    valid_ids = {e["id"] for e in db.list_entities(limit=10000, offset=0)}
    if not valid_ids:
        return {"success": True, "cleaned": {}}

    ph = db._ph
    tables = ["saved_entities", "user_visits", "event_rsvp"]
    cleaned = {}

    def _cleanup():
        with db._conn() as conn:
            for table in tables:
                try:
                    rows = db._fetchall(conn, f"SELECT DISTINCT entity_id FROM {table}", ())
                    orphan_ids = _orphan_entity_ids(rows, valid_ids)
                    if orphan_ids:
                        placeholders = ",".join(ph for _ in orphan_ids)
                        cur = db._execute(conn, f"DELETE FROM {table} WHERE entity_id IN ({placeholders})", tuple(orphan_ids))
                        cleaned[table] = cur.rowcount if cur else 0
                    else:
                        cleaned[table] = 0
                except Exception:
                    logger.debug("Orphan cleanup failed for table %s", table, exc_info=True)
                    cleaned[table] = -1

    await asyncio.to_thread(_cleanup)
    return {"success": True, "cleaned": cleaned}


# ── Entity claims admin (U-30: approve/reject business claims) ────────









# ── Announcements admin: sang siteops/admin_api.py (2026-08-29, lat 3) ──


# ── Route ordering fix ───────────────────────────────────────────────────
def _find_shadowed_routes() -> set:
    """Static paths that sit under a parameterized base and would be shadowed by it."""
    param_bases = {}
    shadowed = set()
    for r in router.routes:
        path = getattr(r, "path", "")
        if "{" in path:
            base = path.split("{")[0].rstrip("/")
            if base not in param_bases:
                param_bases[base] = True
        else:
            for base in param_bases:
                if path.startswith(base + "/"):
                    shadowed.add(path)
    return shadowed


def _reorder_static_routes(static_routes, other_routes) -> None:
    """Insert each static route just before the parameterized route that would shadow it."""
    for s in reversed(static_routes):
        spath = getattr(s, "path", "")
        for i, r in enumerate(other_routes):
            rpath = getattr(r, "path", "")
            if "{" in rpath:
                base = rpath.split("{")[0].rstrip("/")
                if spath.startswith(base + "/"):
                    other_routes.insert(i, s)
                    break


def _fix_admin_route_order():
    """Ensure static sub-paths match before parameterized catch-alls."""
    shadowed = _find_shadowed_routes()
    if not shadowed:
        return
    static_routes = []
    other_routes = []
    for r in router.routes:
        path = getattr(r, "path", "")
        if path in shadowed:
            static_routes.append(r)
        else:
            other_routes.append(r)
    _reorder_static_routes(static_routes, other_routes)
    # Defensive: chỉ áp reorder khi bảo toàn đủ route. Nếu _reorder_static_routes bỏ sót
    # static nào (spath không khớp param base trong other_routes) thì other_routes ngắn
    # hơn → bỏ qua để không mất route. Với route thật mọi static đều khớp nên luôn áp.
    if len(other_routes) == len(router.routes):
        router.routes[:] = other_routes

from entities.admin_api import router as _entities_admin_router  # noqa: E402
router.include_router(_entities_admin_router)

from community.admin_api import router as _community_admin_router  # noqa: E402
router.include_router(_community_admin_router)

# Mien LICH TRINH cung khuon (2026-08-29, lat 2): 5 route CRUD /itineraries* song
# o itineraries/admin_api.py, mount long TRUOC _fix_admin_route_order() — router
# con khong tu mang prefix/deps, ke thua /admin + require_admin + require_csrf.
from itineraries.admin_api import router as _itineraries_admin_router  # noqa: E402

router.include_router(_itineraries_admin_router)

# Mien VAN HANH SITE cung khuon (2026-08-29, lat 3): 22 route quan tri
# (data-quality/system-health/backup/ops-summary/export/site-settings/
# announcements) song o siteops/admin_api.py, mount long TRUOC
# _fix_admin_route_order() — router con khong tu mang prefix/deps, ke thua
# /admin + require_admin + require_csrf; reorder cha van phu static-truoc-param
# cho /site-settings/bulk dung truoc /site-settings/{key:path} (do runtime:
# index bulk < index {key:path}); /site-settings/reset/{category} mang tham so
# nen khong thuoc dien reorder — y nguyen thu tu dinh nghia nhu truoc cu doi,
# reachable nho match theo path+method (PUT vs POST).
from siteops.admin_api import router as _siteops_admin_router  # noqa: E402

router.include_router(_siteops_admin_router)

# Mặt admin của notifications (lát 5) — 1 route, kế thừa chốt từ router cha.
from notifications import admin_router as _notifications_admin_router  # noqa: E402
router.include_router(_notifications_admin_router)

_fix_admin_route_order()
