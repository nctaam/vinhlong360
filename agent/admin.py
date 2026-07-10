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

from fastapi import APIRouter, HTTPException, Query, Request, Depends, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

import data_quality
import knowledge
import analytics
import text_utils

logger = logging.getLogger("admin")
import site_settings
from database import db, escape_like as _escape_like

try:
    from cost_tracker import get_cost_report as _get_cost_report
    _HAS_COST = True
except Exception:  # noqa: BLE001
    logger.warning("Cost tracker unavailable", exc_info=True)
    _HAS_COST = False
from auth_middleware import get_current_user, validate_path_id, require_csrf, require_pg
from middleware import admin_limiter, verify_admin_key, get_client_ip


def _sync_kb():
    """GĐ3.6: write-through — sau khi ghi DB, nạp lại knowledge để chat/tool thấy ngay.

    Bọc try/except: lỗi reload không được làm hỏng thao tác admin đã commit.
    Also invalidates LLM response cache to prevent stale chat answers.
    """
    try:
        knowledge.reload()
    except Exception:
        logger.exception("Knowledge reload failed after admin write — chat may serve stale data")
    try:
        import cache
        cache.invalidate_all()
    except Exception:
        logger.warning("LLM cache invalidation failed after KB sync")
    _invalidate_admin_caches()


_admin_volatile_caches: list[dict] = []

def _invalidate_admin_caches():
    for c in _admin_volatile_caches:
        c["data"] = None


def _safe(fn, default):
    try:
        return fn()
    except Exception:
        logger.debug("_safe(%s) failed, returning default", getattr(fn, "__name__", fn), exc_info=True)
        return default

# ── Auth dependency ──

_AUDIT_FILE = Path(__file__).resolve().parent / "data" / "admin_audit.jsonl"
_audit_lock = threading.Lock()


from config import settings as _cfg
_AUDIT_MAX_LINES = _cfg.AUDIT_MAX_LINES
_AUDIT_MAX_BYTES = 10 * 1024 * 1024  # B5b: rotate cũng khi file > 10MB (không chỉ khi vượt số dòng)

ADMIN_ROLE_SCOPES: dict[str, set[str]] = {
    "moderator": {"moderation.manager"},
    "admin": {"content.editor", "moderation.manager", "ops.deploy", "settings.admin", "security.admin"},
    "superadmin": {"*"},
}

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
)

def _coerce_scope_list(value: Any) -> set[str]:
    if isinstance(value, str):
        return {part.strip() for part in value.split(",") if part.strip()}
    if isinstance(value, (list, tuple, set)):
        return {str(part).strip() for part in value if str(part).strip()}
    return set()

def admin_scopes_for_user(user: dict | None) -> list[str]:
    """Return RBAC scopes for an admin actor. admin-key/superadmin receive wildcard."""
    if user is None:
        return ["*"]
    scopes = set(ADMIN_ROLE_SCOPES.get(str(user.get("role") or "user"), set()))
    for field in ("admin_scopes", "scopes", "permissions"):
        scopes.update(_coerce_scope_list(user.get(field)))
    if "*" in scopes:
        return ["*"]
    return sorted(scopes)

def _ensure_admin_scope(request: Request | None, scope: str) -> None:
    scopes = set(getattr(getattr(request, "state", None), "admin_scopes", []) or [])
    if "*" in scopes or scope in scopes:
        return
    raise HTTPException(403, f"Thieu quyen admin: {scope}")

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

def _has_admin_entry_scope(user: dict | None) -> bool:
    scopes = set(admin_scopes_for_user(user))
    return "*" in scopes or bool(scopes & {"content.editor", "moderation.manager", "ops.deploy", "settings.admin", "security.admin"})

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
    if admin_user is not None:
        request.state.user = admin_user
    await _require_admin_mutation_side_effects(request, actor, admin_user, client_ip)

async def require_admin_scope(request: Request, scope: str):
    """Verify admin auth and require an explicit RBAC scope for non-admin routes."""
    await require_admin(request, required_scope_override=scope)

def _require_admin_actor_id(request: Request | None) -> str:
    """Return the authenticated admin user id for actions that need user attribution."""
    if request is None:
        raise HTTPException(403, "Thao tác này cần phiên admin")
    user = getattr(request.state, "admin_user", None) or getattr(request.state, "user", None)
    if not user or not user.get("id"):
        raise HTTPException(403, "Thao tác này cần phiên admin")
    return str(user["id"])

def _admin_actor_label(request: Request | None) -> str:
    if request is None:
        return "admin-key"
    user = getattr(request.state, "admin_user", None) or getattr(request.state, "user", None)
    return f"user:{user.get('id')}" if user and user.get("id") else "admin-key"

ROOT = Path(__file__).resolve().parent.parent

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin), Depends(require_csrf)])


# ── Models ──

import re as _re
import html as _html

def _sanitize(text: str) -> str:
    """Remove dangerous HTML/JS from user input."""
    text = _html.escape(text)
    text = _re.sub(r'<script[^>]*>.*?</script>', '', text, flags=_re.IGNORECASE | _re.DOTALL)
    return text.strip()

# Entity types + per-type attribute schemas come from the content-model registry
# (agent/entity_schemas.py) — single source of truth so adding a type touches one
# file, not many (DoD-7). This fixes the old TYPE_META(17) vs VALID_TYPES(13)
# mismatch where restaurant/cafe/drink/place/itinerary 422'd on save.
from entity_schemas import (
    valid_types as _valid_types,
    validate_attributes as _validate_attributes,
    all_schemas as _all_schemas,
    kind_of as _kind_of,
    KIND_META as _KIND_META,
    KIND_OF_TYPE as _KIND_OF_TYPE,
    ENTITY_SCHEMAS as _ENTITY_SCHEMAS,
)
VALID_TYPES = _valid_types()

class EntityUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    type: str | None = None
    summary: str | None = Field(None, max_length=2000)
    placeId: str | None = Field(None, max_length=100)
    season: dict | None = None
    attributes: dict | None = None
    images: list[str] | None = Field(None, max_length=50)

    @field_validator("name", mode="before")
    @classmethod
    def sanitize_name(cls, v):
        return _sanitize(v) if v else v

    @field_validator("summary", mode="before")
    @classmethod
    def sanitize_summary(cls, v):
        return _sanitize(v) if v else v

    @field_validator("type", mode="before")
    @classmethod
    def validate_type(cls, v):
        if v and v not in VALID_TYPES:
            raise ValueError(f"type must be one of: {', '.join(sorted(VALID_TYPES))}")
        return v

    @field_validator("season", mode="before")
    @classmethod
    def validate_season(cls, v):
        if v is not None:
            months = v.get("months", [])
            peak = v.get("peak", [])
            if not all(isinstance(m, int) and 1 <= m <= 12 for m in months):
                raise ValueError("season.months must be list of integers 1-12")
            if not all(isinstance(m, int) and 1 <= m <= 12 for m in peak):
                raise ValueError("season.peak must be list of integers 1-12")
            if peak and not all(m in months for m in peak):
                raise ValueError("season.peak must be subset of season.months")
        return v

    @field_validator("images", mode="before")
    @classmethod
    def validate_images(cls, v):
        if v is not None:
            if not isinstance(v, list):
                raise ValueError("images must be a list of URLs")
            if len(v) > 10:
                raise ValueError("Maximum 10 images per entity")
            for url in v:
                if not isinstance(url, str) or len(url) > 500:
                    raise ValueError("Each image must be a URL string under 500 chars")
        return v


class EntityCreate(BaseModel):
    id: str = Field(..., min_length=2, max_length=100, pattern=r'^[a-z0-9_\-]+$')  # allow underscore (align w/ FE + existing slugs)
    type: str
    name: str = Field(..., min_length=1, max_length=200)
    placeId: str | None = Field(None, max_length=100)
    summary: str = Field("", max_length=2000)
    season: dict | None = None
    attributes: dict = {}
    images: list[str] = Field(default=[], max_length=50)
    source: dict | None = None  # GĐ13: cho phép khai nguồn chính thống (vd danh bạ facility — KHÔNG bịa)

    @field_validator("name", mode="before")
    @classmethod
    def sanitize_name(cls, v):
        return _sanitize(v)

    @field_validator("summary", mode="before")
    @classmethod
    def sanitize_summary(cls, v):
        return _sanitize(v) if v else v

    @field_validator("type", mode="before")
    @classmethod
    def validate_type(cls, v):
        if v not in VALID_TYPES:
            raise ValueError(f"type must be one of: {', '.join(sorted(VALID_TYPES))}")
        return v

    @field_validator("season", mode="before")
    @classmethod
    def validate_season(cls, v):
        if v is not None:
            months = v.get("months", [])
            peak = v.get("peak", [])
            if not all(isinstance(m, int) and 1 <= m <= 12 for m in months):
                raise ValueError("season.months must be list of integers 1-12")
            if not all(isinstance(m, int) and 1 <= m <= 12 for m in peak):
                raise ValueError("season.peak must be list of integers 1-12")
        return v

    @field_validator("images", mode="before")
    @classmethod
    def validate_images(cls, v):
        if v is not None:
            if not isinstance(v, list):
                raise ValueError("images must be a list of URLs")
            if len(v) > 10:
                raise ValueError("Maximum 10 images per entity")
            for url in v:
                if not isinstance(url, str) or len(url) > 500:
                    raise ValueError("Each image must be a URL string under 500 chars")
        return v


# ── Entity CRUD ──

class DataQualityApplyRequest(BaseModel):
    candidate_ids: list[str] | None = Field(None, max_length=500)
    dry_run: bool = True

class DataQualityDecisionRequest(BaseModel):
    candidate_ids: list[str] = Field(..., min_length=1, max_length=200)
    decision: str = Field(..., pattern="^(approve|reject|defer)$")
    note: str = Field("", max_length=1000)
    apply: bool = False

@router.get("/entities",
            summary="List entities (admin)",
            description="Returns a paginated list of all entities for admin management. Supports filtering by type, area, search query, and orphan detection.")
async def list_entities(
    type: Optional[str] = Query(None, max_length=50),
    kind: Optional[str] = Query(None, max_length=30),
    area: Optional[str] = Query(None, max_length=100),
    q: Optional[str] = Query(None, max_length=200),
    include_places: bool = False,
    orphans_only: bool = False,
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0, le=10000),
):
    """Danh sách entities với filter — đọc từ database."""
    def _query():
        # GĐ-A: `kind` mở rộng thành các type thành viên qua registry (type cụ thể vẫn ưu tiên).
        kind_types: list[str] | None = None
        if kind and not type:
            kind_types = sorted(t for t, k in _KIND_OF_TYPE.items() if k == kind)
            if not kind_types:
                return {"total": 0, "offset": offset, "limit": limit, "entities": []}
        all_matches, results = _list_entities_fetch(type, area, q, orphans_only, kind_types, limit, offset)
        all_matches, results = _list_entities_add_places(include_places, all_matches, results)
        all_matches = _list_entities_filter_orphans(orphans_only, all_matches)

        if all_matches is not None:
            total = len(all_matches)
            items = all_matches[offset:offset + limit]
        else:
            total = db.count_entities_filtered(entity_type=type, area=area)
            items = results

        _list_entities_attach_place_names(items)
        return {"total": total, "offset": offset, "limit": limit, "entities": items}
    return await asyncio.to_thread(_query)


def _list_entities_fetch_place_rows() -> list[dict]:
    with db._conn() as conn:
        place_rows = db._fetchall(conn, "SELECT * FROM entities WHERE type = 'place' ORDER BY name LIMIT 1000", ())
    return [db._parse_entity(r) for r in place_rows]


def _list_entities_fetch(type, area, q, orphans_only, kind_types, limit, offset):
    """Return (all_matches, results) per the filter combination; `results` only set when unfiltered."""
    results = None
    if q or orphans_only:
        all_matches = db.search_entities(q=q, entity_type=type, area=area, limit=2000, offset=0) if q else db.list_entities(entity_type=type, area=area, limit=2000, offset=0)
        if kind_types:
            _kt = set(kind_types)
            all_matches = [e for e in all_matches if e.get("type") in _kt]
    elif kind_types:
        merged: list[dict] = []
        for t in kind_types:
            if t == "place":
                # list_entities mặc định không trả place — lấy trực tiếp (giống nhánh include_places).
                merged.extend(_list_entities_fetch_place_rows())
            else:
                merged.extend(db.list_entities(entity_type=t, area=area, limit=2000, offset=0) or [])
        merged.sort(key=lambda e: (e.get("name") or ""))
        all_matches = merged
    else:
        all_matches = None
        results = db.list_entities(entity_type=type, area=area, limit=limit, offset=offset)
    return all_matches, results


def _list_entities_add_places(include_places, all_matches, results):
    if include_places:
        places = _list_entities_fetch_place_rows()
        if all_matches is not None:
            all_matches = all_matches + places
        else:
            results = results + places
    return all_matches, results


def _list_entities_filter_orphans(orphans_only, all_matches):
    if orphans_only:
        with db._conn() as conn:
            orphan_rows = db._fetchall(conn,
                "SELECT id FROM entities WHERE type != 'place' "
                "AND id NOT IN (SELECT from_id FROM relationships) "
                "AND id NOT IN (SELECT to_id FROM relationships)", ())
            orphan_ids = {db._row_to_dict(r)["id"] for r in orphan_rows}
        if all_matches is not None:
            all_matches = [e for e in all_matches if e["id"] in orphan_ids]
    return all_matches


def _list_entities_attach_place_names(items) -> None:
    place_ids = list({e["placeId"] for e in items if e.get("placeId")})
    if place_ids:
        place_map = db.get_entities_batch(place_ids)
        for e in items:
            pid = e.get("placeId")
            if pid and pid in place_map:
                e["place_name"] = place_map[pid]["name"]
                e["area"] = place_map[pid].get("area") or e.get("area")


@router.get("/entity-kinds",
            summary="Entity counts grouped by owner category (kind)",
            description="Returns the 7 owner-facing categories (kinds) as a derived view over the 17 raw "
                        "types, with per-kind totals and per-type breakdown. Phase 2 of the content-model — "
                        "a reporting/grouping layer; nothing is stored, `type` stays the storage discriminator.")
async def entity_kinds():
    """Đếm entity theo danh mục chủ (kind) — lớp gộp phái sinh trên 17 type."""
    def _query():
        by_type = db.count_entities()  # {type: count}, excludes 'place'
        # place (administrative) counted separately since count_entities excludes it
        with db._conn() as conn:
            row = db._fetchone(conn, "SELECT COUNT(*) c FROM entities WHERE type = 'place'", ())
        place_count = (db._row_to_dict(row) or {}).get("c", 0) if row else 0
        by_type = dict(by_type)
        if place_count:
            by_type["place"] = place_count

        # Group into kinds, preserving KIND_META order.
        buckets: dict[str, list] = {k: [] for k in _KIND_META}
        for t, cnt in by_type.items():
            k = _kind_of(t)
            meta = _ENTITY_SCHEMAS.get(t, {})
            buckets.setdefault(k, []).append({
                "type": t,
                "label": meta.get("label", t),
                "emoji": meta.get("emoji", "📍"),
                "count": cnt,
            })
        kinds = []
        for k, km in _KIND_META.items():
            items = sorted(buckets.get(k, []), key=lambda x: -x["count"])
            kinds.append({
                "kind": k,
                "label": km["label"],
                "emoji": km["emoji"],
                "total": sum(i["count"] for i in items),
                "types": items,
            })
        return {"kinds": kinds, "grand_total": sum(by_type.values())}
    return await asyncio.to_thread(_query)


@router.get("/entity-completeness",
            summary="Data completeness per kind",
            description="Per-kind field-fill percentages (universal + registry fields) plus the entities "
                        "missing the most data. Read-only reporting for the per-kind AdminCP views (GĐ-A).")
async def entity_completeness(kind: str = Query(..., max_length=30), worst: int = Query(20, ge=1, le=100)):
    """% điền từng trường + entity thiếu nhiều nhất — dashboard làm giàu dữ liệu theo nhóm."""
    def _query():
        kind_types = sorted(t for t, k in _KIND_OF_TYPE.items() if k == kind)
        if not kind_types:
            return {"kind": kind, "total": 0, "fields": [], "worst": []}
        ents = _completeness_fetch_ents(kind_types)
        if not ents:
            return {"kind": kind, "total": 0, "fields": [], "worst": []}

        fields: list[dict] = []
        missing_map: dict[str, list[str]] = {e["id"]: [] for e in ents}
        seen = _completeness_universal_fields(ents, fields, missing_map)
        _completeness_registry_fields(ents, kind_types, seen, fields, missing_map)
        by_id = {e["id"]: e for e in ents}
        worst_list = sorted(missing_map.items(), key=lambda kv: -len(kv[1]))[:worst]
        return {"kind": kind, "total": len(ents), "fields": fields,
                "worst": [{"id": i, "name": by_id[i]["name"], "type": by_id[i]["type"],
                           "missing": m, "missing_count": len(m)} for i, m in worst_list if m]}
    return await asyncio.to_thread(_query)


_COMPLETENESS_UNIVERSAL = [("address", "Địa chỉ"), ("phone", "Điện thoại"), ("website", "Website"),
                          ("hours", "Giờ mở cửa"), ("price_range", "Khoảng giá"),
                          ("sub_category", "Phân loại"), ("best_time", "Thời điểm đẹp"), ("highlight", "Điểm nhấn")]


def _completeness_has(e: dict, key: str) -> bool:
    a = e.get("attributes") or {}
    if key == "season":
        s = e.get("season") or {}
        return bool(s.get("months") or s.get("best"))
    if key == "images":
        return bool(e.get("images"))
    if key == "coords_real":
        return bool(e.get("coordinates")) and not a.get("coords_approximate")
    if key == "summary_100":
        return len(str(e.get("summary") or "")) >= 100
    return a.get(key) not in (None, "", [], {})


def _completeness_fetch_ents(kind_types: list[str]) -> list[dict]:
    with db._conn() as conn:
        placeholders = ", ".join(db._ph for _ in kind_types)  # ?/%s theo backend (PG dùng %s)
        rows = db._fetchall(conn,
            f"SELECT * FROM entities WHERE type IN ({placeholders}) ORDER BY name LIMIT 2000",
            tuple(kind_types))
        return [db._parse_entity(r) for r in rows]


def _completeness_universal_fields(ents, fields, missing_map) -> set[str]:
    """Append universal-field stats to `fields`, update `missing_map`, return the seen key set."""
    universal_keys = [k for k, _ in _COMPLETENESS_UNIVERSAL] + ["season", "images", "coords_real", "summary_100"]
    labels = dict(_COMPLETENESS_UNIVERSAL)
    labels.update({"season": "Mùa", "images": "Ảnh", "coords_real": "Tọa độ thật",
                   "summary_100": "Tóm tắt ≥100 ký tự"})
    filled_counts = {k: 0 for k in universal_keys}
    for e in ents:
        for key in universal_keys:
            if _completeness_has(e, key):
                filled_counts[key] += 1
            else:
                missing_map[e["id"]].append(key)
    for key in universal_keys:
        fields.append({"key": key, "label": labels[key], "scope": "chung",
                       "filled": filled_counts[key], "pct": round(100 * filled_counts[key] / len(ents), 1)})
    return set(universal_keys)


def _completeness_registry_fields(ents, kind_types, seen, fields, missing_map) -> None:
    for t in kind_types:
        schema = _ENTITY_SCHEMAS.get(t) or {}
        t_ents = [e for e in ents if e["type"] == t]
        if not t_ents:
            continue
        for f in schema.get("fields", []):
            key = f["key"]
            if key in seen:
                continue
            filled = sum(1 for e in t_ents if _completeness_has(e, key))
            fields.append({"key": key, "label": f["label"], "scope": schema.get("label", t),
                           "filled": filled, "pct": round(100 * filled / len(t_ents), 1)})
            for e in t_ents:
                if not _completeness_has(e, key):
                    missing_map[e["id"]].append(key)


@router.get("/entities/places",
            summary="List places for dropdown",
            description="Returns a list of place entities (xa/phuong) for use in admin dropdown selectors.")
async def list_places():
    """Danh sách xã/phường cho dropdown."""
    def _query():
        db.initialize()
        with db._conn() as conn:
            rows = db._fetchall(conn, "SELECT id, name, area, level FROM entities WHERE type = 'place' ORDER BY name LIMIT 500")
        return [db._row_to_dict(r) for r in rows]
    return await asyncio.to_thread(_query)


@router.get("/entities/check-duplicate",
            summary="Check entity name duplicate",
            description="Checks for existing entities with similar names using case-insensitive substring matching. Returns up to 5 matches.")
async def check_duplicate(name: str = Query(..., min_length=2, max_length=200)):
    """Kiểm tra entity trùng tên (substring, case-insensitive + B2c: không phân biệt dấu)."""
    name_lower = name.lower().strip()
    if len(name_lower) < 2:
        return {"duplicates": []}
    pattern = f"%{_escape_like(name_lower)}%"
    norm_needle = text_utils.normalize_name(name)
    def _query():
        with db._conn() as conn:
            # db._ph: ? chỉ đúng SQLite — trên PG (psycopg2) phải %s (500 trên prod)
            if db._use_pg:
                # f_unaccent (migration 015) đã có index — OR thêm để bắt biến thể có/không dấu.
                sql = (f"SELECT id, name, type FROM entities WHERE type != 'place' AND "
                       f"(LOWER(name) LIKE {db._ph} ESCAPE '\\' OR f_unaccent(LOWER(name)) LIKE f_unaccent({db._ph}) ESCAPE '\\') LIMIT 20")
                rows = db._fetchall(conn, sql, (pattern, pattern))
            else:
                rows = db._fetchall(conn,
                    f"SELECT id, name, type FROM entities WHERE type != 'place' AND LOWER(name) LIKE {db._ph} ESCAPE '\\' LIMIT 20",
                    (pattern,))
        dups = []
        for r in rows:
            d = db._row_to_dict(r)
            dups.append({"id": d["id"], "name": d["name"], "type": d.get("type", "")})
        if not db._use_pg:
            # SQLite fallback: không có unaccent() — lọc bổ sung bằng normalize_name trong Python.
            dups = [d for d in dups if norm_needle in text_utils.normalize_name(d["name"])]
        return {"duplicates": dups[:5]}
    return await asyncio.to_thread(_query)


@router.get("/entities/{entity_id}",
            summary="Get entity details",
            description="Returns full details of a single entity including its relationships.")
async def get_entity(entity_id: str):
    """Chi tiết 1 entity."""
    entity_id = validate_path_id(entity_id, "entity_id")
    def _query():
        entity = db.get_entity(entity_id)
        if not entity:
            raise HTTPException(404, "Entity không tồn tại")
        entity["relationships"] = db.get_relationships(entity_id)
        return entity
    return await asyncio.to_thread(_query)


@router.put("/entities/{entity_id}",
            summary="Update entity",
            description="Updates an entity's fields. Logs changes to entity history and invalidates relevant caches.")
async def update_entity(entity_id: str, update: EntityUpdate):
    """Cập nhật entity."""
    entity_id = validate_path_id(entity_id, "entity_id")
    def _query():
        existing = db.get_entity(entity_id)
        if not existing:
            raise HTTPException(404, "Entity không tồn tại")
        old_snapshot = {k: v for k, v in existing.items()}
        updates = update.model_dump(exclude_none=True)
        existing.update(updates)
        # Typed, non-destructive validation against the type's content-model schema:
        # coerces known fields (number/bool/tags), preserves the bespoke tail, and
        # surfaces warnings (missing-required / bad-enum) without blocking the save.
        norm_attrs, warnings = _validate_attributes(existing.get("type", ""), existing.get("attributes"))
        existing["attributes"] = norm_attrs
        existing["updatedAt"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        db.upsert_entity(existing)
        db.log_entity_changes(entity_id, old_snapshot, existing)
        _sync_kb()
        from public_api import invalidate_entity_cache, invalidate_place_cache
        invalidate_entity_cache(entity_id)
        if existing.get("type") == "place":
            invalidate_place_cache()
        return {"status": "updated", "entity": existing, "warnings": warnings}
    return await asyncio.to_thread(_query)


@router.get("/entities/{entity_id}/history",
            summary="Get entity change history",
            description="Returns the change history (diffs) for a specific entity, ordered by most recent first.")
async def get_entity_history(entity_id: str, limit: int = Query(50, ge=1, le=200)):
    """Lịch sử thay đổi entity."""
    entity_id = validate_path_id(entity_id, "entity_id")
    def _query():
        return {"history": db.get_entity_history(entity_id, limit)}
    return await asyncio.to_thread(_query)


@router.get("/entity-schema",
            summary="Get entity content-model schema",
            description="Returns the per-type field schema registry that drives the AdminCP typed forms, "
                        "validation, and display. Single source of truth (agent/entity_schemas.py).")
async def get_entity_schema():
    """Content-model registry: per-type fields + owner-category (kind) mapping."""
    return _all_schemas()


@router.post("/entities", status_code=201,
             summary="Create entity",
             description="Creates a new entity. Returns 409 if an entity with the same ID already exists.")
async def create_entity(entity: EntityCreate):
    """Tạo entity mới."""
    def _query():
        if db.get_entity(entity.id):
            raise HTTPException(409, "Entity đã tồn tại")
        payload = entity.model_dump()
        src = payload.pop("source", None) or {"title": "admin", "method": "manual"}
        norm_attrs, warnings = _validate_attributes(payload.get("type", ""), payload.get("attributes"))
        payload["attributes"] = norm_attrs
        new_entity = {
            **payload,
            "source": src,
            "updatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        }
        db.upsert_entity(new_entity)
        _sync_kb()
        return {"status": "created", "entity": new_entity, "warnings": warnings}
    return await asyncio.to_thread(_query)


@router.delete("/entities/{entity_id}",
               summary="Delete entity",
               description="Deletes an entity and invalidates related caches. Does not remove associated files.")
async def delete_entity(entity_id: str):
    """Xóa entity."""
    entity_id = validate_path_id(entity_id, "entity_id")
    def _query():
        entity = db.get_entity(entity_id)
        if not entity:
            raise HTTPException(404, "Entity không tồn tại")
        db.delete_entity(entity_id)
        _sync_kb()
        from public_api import invalidate_entity_cache, invalidate_place_cache
        invalidate_entity_cache(entity_id)
        if entity.get("type") == "place":
            invalidate_place_cache()
    await asyncio.to_thread(_query)
    return {"success": True, "entity_id": entity_id}


class _EntityImageURL(BaseModel):
    url: str = Field(..., max_length=600)


@router.post("/entities/{entity_id}/images", status_code=201,
             summary="Add image URL to entity",
             description="Adds an image URL to an entity's image list. Validates URL accessibility. Maximum 10 images per entity.")
async def add_entity_image_url(entity_id: str, body: _EntityImageURL):
    """GĐ8.4: thêm ảnh entity theo URL (chỉ nguồn cấp phép — B6)."""
    entity_id = validate_path_id(entity_id, "entity_id")
    url = (body.url or "").strip()
    if url.startswith("/"):
        pass
    else:
        await asyncio.to_thread(_assert_public_url, url)
    def _query():
        entity = db.get_entity(entity_id)
        if not entity:
            raise HTTPException(404, "Entity không tồn tại")
        images = list(entity.get("images") or [])
        if len(images) >= 10:
            raise HTTPException(400, "Tối đa 10 ảnh mỗi entity")
        if url not in images:
            images.append(url)
        entity["images"] = images
        entity["updatedAt"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        db.upsert_entity(entity)
        _sync_kb()
        return {"status": "added", "images": images}
    return await asyncio.to_thread(_query)


@router.post("/entities/{entity_id}/images/upload",
             summary="Upload image file for entity",
             description="Uploads an image file, converts to WebP in 3 sizes (sm/md/lg), and adds to the entity. Maximum 10 images per entity.")
async def upload_entity_image(entity_id: str, file: UploadFile = File(...)):
    """GĐ8.4: upload file ảnh → WebP 3 cỡ → R2 (fallback đĩa) → entity.images.
    Lưu URL cỡ md (800px) làm ảnh hiển thị; sm/lg cũng được upload để dùng srcset sau."""
    entity_id = validate_path_id(entity_id, "entity_id")
    from fastapi.concurrency import run_in_threadpool
    from storage import storage, MAX_IMAGE_SIZE

    entity = db.get_entity(entity_id)
    if not entity:
        raise HTTPException(404, "Entity không tồn tại")
    data = await file.read(MAX_IMAGE_SIZE + 1)
    if len(data) > MAX_IMAGE_SIZE:
        del data
        raise HTTPException(413, f"Ảnh quá lớn (tối đa {MAX_IMAGE_SIZE // 1024 // 1024}MB)")
    if not storage.sniff_image_type(data):
        raise HTTPException(400, "File không phải ảnh hợp lệ (JPEG/PNG/GIF/WebP)")
    if len(entity.get("images") or []) >= 10:
        raise HTTPException(400, "Tối đa 10 ảnh mỗi entity")
    try:
        urls = await run_in_threadpool(storage.upload_image_set, data, "entities", entity_id)
    except ValueError:
        raise HTTPException(400, "Ảnh không hợp lệ hoặc đã hỏng")
    except Exception:
        logger.exception("Entity image upload failed for %s", entity_id)
        raise HTTPException(500, "Không thể upload ảnh, vui lòng thử lại")

    cover = urls.get("md") or urls.get("lg")
    images = list(entity.get("images") or [])
    if cover and cover not in images:
        images.append(cover)
    entity["images"] = images
    entity["updatedAt"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    db.upsert_entity(entity)
    _sync_kb()
    return {"status": "uploaded", "url": cover, "sizes": urls, "images": images, "backend": storage.backend}


@router.delete("/entities/{entity_id}/images/{idx}",
               summary="Remove image from entity",
               description="Removes an image at the given index from the entity's image list. Does not delete the actual file from storage.")
async def remove_entity_image(entity_id: str, idx: int):
    """Gỡ ảnh thứ idx khỏi entity.images (không xoá file R2 — tránh mất ảnh dùng chung)."""
    entity_id = validate_path_id(entity_id, "entity_id")
    def _query():
        entity = db.get_entity(entity_id)
        if not entity:
            raise HTTPException(404, "Entity không tồn tại")
        images = list(entity.get("images") or [])
        if not (0 <= idx < len(images)):
            raise HTTPException(400, f"Chỉ số ảnh không hợp lệ (0–{len(images) - 1})")
        images.pop(idx)
        entity["images"] = images
        entity["updatedAt"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        db.upsert_entity(entity)
        _sync_kb()
        return {"status": "removed", "images": images}
    return await asyncio.to_thread(_query)


@router.get("/unclassified",
            summary="List unclassified entities",
            description="Returns entities not yet assigned to a commune/ward (empty placeId). Supports search and pagination.")
async def list_unclassified(limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0, le=10000),
                            q: Optional[str] = Query(None, max_length=200)):
    """Entity nội dung CHƯA gán xã/phường (placeId rỗng) — để admin gán đúng (lấp nợ placeId)."""
    ql = (q or "").lower().strip()
    # PG folds identifier không nháy về lowercase → "placeid" not exist (cột tạo
    # là "placeId" quoted). Placeholder cũng phải theo db._ph (?/%s) — bug 500
    # trên prod PG, dev SQLite không thấy (case-insensitive + dùng ?).
    _pid = '"placeId"' if db._use_pg else "placeId"
    ph = db._ph
    base = f"FROM entities WHERE type != 'place' AND ({_pid} IS NULL OR {_pid} = '')"
    params: list = []
    if ql:
        base += f" AND LOWER(name) LIKE {ph} ESCAPE '\\'"
        params.append(f"%{_escape_like(ql)}%")
    def _query():
        with db._conn() as conn:
            cnt = db._fetchone(conn, f"SELECT COUNT(*) as c {base}", tuple(params))
            total = db._row_to_dict(cnt)["c"] if cnt else 0
            rows = db._fetchall(conn, f"SELECT id, name, type, area, summary {base} ORDER BY name LIMIT {ph} OFFSET {ph}",
                                tuple(params) + (limit, offset))
        out = []
        for r in rows:
            d = db._row_to_dict(r)
            out.append({"id": d["id"], "name": d.get("name"), "type": d.get("type"),
                         "area": d.get("area"), "summary": (d.get("summary") or "")[:100]})
        return {"total": total, "entities": out}
    return await asyncio.to_thread(_query)


class AssignPlaceRequest(BaseModel):
    place_id: Optional[str] = Field(None, max_length=100)

class BulkAssignPlaceRequest(BaseModel):
    entity_ids: list[str] = Field(..., min_length=1, max_length=200)
    place_id: Optional[str] = Field(None, max_length=100)


@router.post("/entities/{entity_id}/place",
             summary="Assign place to entity",
             description="Assigns or removes a commune/ward (placeId) for an entity. Validates the place exists.")
async def assign_place(entity_id: str, body: AssignPlaceRequest):
    """Gán (hoặc gỡ) xã/phường cho 1 entity. Validate place_id là place thật (chống gán bừa)."""
    entity_id = validate_path_id(entity_id, "entity_id")
    def _query():
        e = db.get_entity(entity_id)
        if not e:
            raise HTTPException(404, "Entity không tồn tại")
        pid = body.place_id or None
        if pid:
            p = db.get_entity(pid)
            if not p or p.get("type") != "place":
                raise HTTPException(400, "place_id không phải xã/phường hợp lệ")
            e["area"] = p.get("area") or e.get("area")
        e["placeId"] = pid
        e["updatedAt"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        db.upsert_entity(e)
        _sync_kb()
        return {"success": True, "id": entity_id, "placeId": pid}
    return await asyncio.to_thread(_query)


# ── Itinerary CRUD ──

@router.post("/entities/bulk-place",
             summary="Bulk assign place to entities",
             description="Assigns or removes a commune/ward placeId for many entities in one admin action.")
def _bulk_assign_entities(ids, pid, place):
    """Assign pid to each id in ids; return (assigned_ids, errors)."""
    assigned: list[str] = []
    errors: list[dict[str, str]] = []
    entities_map = db.get_entities_batch(ids) if ids else {}
    for entity_id in ids:
        entity = entities_map.get(entity_id)
        if not entity:
            errors.append({"id": entity_id, "error": "Entity không tồn tại"})
            continue
        if pid and place:
            entity["area"] = place.get("area") or entity.get("area")
        entity["placeId"] = pid
        entity["updatedAt"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        db.upsert_entity(entity)
        assigned.append(entity_id)
    return assigned, errors


async def bulk_assign_place(body: BulkAssignPlaceRequest):
    ids = [validate_path_id(entity_id, "entity_id") for entity_id in body.entity_ids]
    def _query():
        pid = body.place_id or None
        place = None
        if pid:
            place = db.get_entity(pid)
            if not place or place.get("type") != "place":
                raise HTTPException(400, "place_id không phải xã/phường hợp lệ")
        assigned, errors = _bulk_assign_entities(ids, pid, place)
        if assigned:
            _sync_kb()
        return {"success": True, "assigned": len(assigned), "assigned_ids": assigned, "errors": errors}
    return await asyncio.to_thread(_query)

@router.get("/itineraries",
            summary="List itineraries",
            description="Returns all itineraries, optionally filtered by area.")
async def list_itineraries_admin(area: Optional[str] = Query(None, max_length=100)):
    return await asyncio.to_thread(db.list_itineraries, area=area)

@router.get("/itineraries/{itin_id}",
            summary="Get itinerary by ID",
            description="Returns the full details of a single itinerary by its ID.")
async def get_itinerary_admin(itin_id: str):
    itin_id = validate_path_id(itin_id, "itin_id")
    def _query():
        it = db.get_itinerary(itin_id)
        if not it:
            raise HTTPException(404, "Lộ trình không tồn tại")
        return it
    return await asyncio.to_thread(_query)

class ItineraryCreate(BaseModel):
    id: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=300)
    summary: str | None = Field(None, max_length=2000)
    description: str | None = Field(None, max_length=2000)
    duration: str | None = Field(None, max_length=100)
    stops: list | None = Field(None, max_length=50)
    days: list | None = Field(None, max_length=30)
    area: str | None = Field(None, max_length=100)
    areas: list[str] | None = Field(None, max_length=10)
    tags: list[str] | None = Field(None, max_length=50)

class ItineraryUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=300)
    summary: str | None = Field(None, max_length=2000)
    description: str | None = Field(None, max_length=2000)
    duration: str | None = Field(None, max_length=100)
    stops: list | None = Field(None, max_length=50)
    days: list | None = Field(None, max_length=30)
    area: str | None = Field(None, max_length=100)
    areas: list[str] | None = Field(None, max_length=10)
    tags: list[str] | None = Field(None, max_length=50)

def _normalize_itinerary_payload(data: dict) -> dict:
    if data.get("description") and not data.get("summary"):
        data["summary"] = data["description"]
    return data

class RelationshipCreate(BaseModel):
    from_id: str = Field(..., min_length=1, max_length=100)
    to_id: str = Field(..., min_length=1, max_length=100)
    type: str = Field(..., min_length=1, max_length=100)

class RelationshipBulkPair(BaseModel):
    to_id: str = Field(..., min_length=1, max_length=100)
    type: str = Field("related_to", max_length=100)

class RelationshipBulkCreate(BaseModel):
    from_id: str = Field(..., min_length=1, max_length=100)
    pairs: list[RelationshipBulkPair] = Field(..., max_length=50)


@router.post("/itineraries", status_code=201,
             summary="Create itinerary",
             description="Creates a new itinerary with title, description, days, area, and tags.")
async def create_itinerary(body: ItineraryCreate):
    def _query():
        data = _normalize_itinerary_payload(body.model_dump(exclude_none=True))
        db.upsert_itinerary(data)
    await asyncio.to_thread(_query)
    return {"status": "created", "id": body.id}

@router.put("/itineraries/{itin_id}",
            summary="Update itinerary",
            description="Updates an existing itinerary. Only provided fields are changed.")
async def update_itinerary(itin_id: str, body: ItineraryUpdate):
    itin_id = validate_path_id(itin_id, "itin_id")
    def _query():
        data = _normalize_itinerary_payload(body.model_dump(exclude_none=True))
        existing = db.get_itinerary(itin_id)
        if not existing:
            raise HTTPException(404, "Lộ trình không tồn tại")
        data = {**existing, **data}
        data["id"] = itin_id
        db.upsert_itinerary(data)
    await asyncio.to_thread(_query)
    return {"status": "updated", "id": itin_id}

@router.delete("/itineraries/{itin_id}",
               summary="Delete itinerary",
               description="Permanently deletes an itinerary by its ID. Returns 404 if not found.")
async def delete_itinerary(itin_id: str):
    itin_id = validate_path_id(itin_id, "itin_id")
    def _query():
        db.initialize()
        ph = db._ph
        with db._conn() as conn:
            cur = db._execute(conn, f"DELETE FROM itineraries WHERE id = {ph}", (itin_id,))
            if cur.rowcount == 0:
                raise HTTPException(404, "Lộ trình không tồn tại")
    await asyncio.to_thread(_query)
    return {"success": True, "id": itin_id}


# ── Relationship CRUD ──

@router.post("/relationships", status_code=201,
             summary="Create entity relationship",
             description="Creates a directional relationship between two entities (e.g. related_to, belongs_to).")
async def add_relationship(body: RelationshipCreate):
    validate_path_id(body.from_id, "from_id")
    validate_path_id(body.to_id, "to_id")
    await asyncio.to_thread(db.add_relationship, body.from_id, body.to_id, body.type)
    return {"status": "created"}

@router.delete("/relationships",
               summary="Delete entity relationship",
               description="Removes a specific directional relationship between two entities. Returns 404 if not found.")
async def delete_relationship(from_id: str, to_id: str, type: str = Query(..., max_length=100)):
    validate_path_id(from_id, "from_id")
    validate_path_id(to_id, "to_id")
    def _query():
        db.initialize()
        ph = db._ph
        with db._conn() as conn:
            cur = db._execute(conn, f"DELETE FROM relationships WHERE from_id={ph} AND to_id={ph} AND type={ph}",
                              (from_id, to_id, type))
            if cur.rowcount == 0:
                raise HTTPException(404, "Mối quan hệ không tồn tại")
    await asyncio.to_thread(_query)
    return {"success": True}


@router.post("/relationships/bulk", status_code=201,
             summary="Bulk create relationships",
             description="Creates multiple relationships from one source entity at once. Reports individual errors without rolling back.")
async def add_relationships_bulk(body: RelationshipBulkCreate):
    """B7b: thêm nhiều quan hệ cùng lúc."""
    validate_path_id(body.from_id, "from_id")
    def _query():
        added = 0
        errors = []
        for p in body.pairs:
            to_id = p.to_id.strip()
            rel_type = p.type
            if not to_id:
                continue
            try:
                db.add_relationship(body.from_id, to_id, rel_type)
                added += 1
            except Exception as e:
                logger.warning("Bulk relationship add failed for %s→%s: %s", body.from_id, to_id, e)
                errors.append({"to_id": to_id, "error": "Không thể thêm quan hệ"})
        return {"added": added, "errors": errors}
    return await asyncio.to_thread(_query)


# ── Bulk operations ──

# Data quality review queue

@router.get("/data-quality/summary",
            summary="Get data quality summary",
            description="Returns an overview of data quality metrics including candidate counts, stream counts, and sitemap expectations.")
async def data_quality_summary(refresh: bool = Query(False)):
    def _query():
        data_summary = data_quality.summarize_data()
        queue = data_quality.load_candidate_queue(refresh=refresh)
        return {
            "data": data_summary,
            "candidates": queue.get("counts", {}),
            "stream_counts": queue.get("stream_counts", {}),
            "cache": queue.get("cache", {}),
            "sitemap": {
                "expected_public_detail_urls": data_summary["public_entities"],
                "expected_itinerary_urls": data_summary["itineraries"],
                "expected_public_content_urls": data_summary["public_entities"] + data_summary["itineraries"],
            },
            "policy": queue.get("policy", {}),
        }
    return await asyncio.to_thread(_query)

@router.get("/data-quality/review",
            summary="Review data quality candidates",
            description="Returns filterable data quality improvement candidates. Supports filtering by kind, bucket, and pagination.")
async def data_quality_review(
    kind: Optional[str] = Query(None, pattern="^(source|location|placeid|accuracy|relationship)$"),
    bucket: Optional[str] = Query(None, pattern="^(auto_apply|needs_review|reject)$"),
    refresh: bool = Query(False),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0, le=10000),
):
    def _query():
        queue = data_quality.load_candidate_queue(refresh=refresh)
        result = data_quality.filter_candidates(queue, kind=kind, bucket=bucket, limit=limit, offset=offset)
        result["cache"] = queue.get("cache", {})
        return result
    return await asyncio.to_thread(_query)

@router.post("/data-quality/apply",
             summary="Apply data quality improvements",
             description="Applies selected data quality candidates to entities. Supports dry-run mode for preview.")
async def data_quality_apply(body: DataQualityApplyRequest):
    def _query():
        result = data_quality.apply_candidates(body.candidate_ids, dry_run=body.dry_run)
        if result.get("applied_count") and not body.dry_run:
            _sync_kb()
        return result
    return await asyncio.to_thread(_query)

@router.get("/data-quality/history",
            summary="Get data quality apply history",
            description="Returns the history of applied data quality batches, ordered by most recent first.")
async def data_quality_history(limit: int = Query(20, ge=1, le=200)):
    result = await asyncio.to_thread(data_quality.load_apply_history, limit=limit)
    decisions = await asyncio.to_thread(data_quality.load_decision_history, limit=limit)
    result["decisions"] = decisions.get("decisions", [])
    result["decision_total"] = decisions.get("total", 0)
    return result

@router.post("/data-quality/decision",
             summary="Record data quality review decision",
             description="Records approve, reject, or defer decisions for data-quality candidates. Approved candidates can optionally be applied immediately.")
async def data_quality_decision(body: DataQualityDecisionRequest, request: Request):
    reviewer = _require_admin_actor_id(request)
    try:
        result = await asyncio.to_thread(
            data_quality.decide_candidates,
            body.candidate_ids,
            decision=body.decision,
            note=body.note,
            reviewer=reviewer,
            apply=body.apply,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    return result

@router.post("/data-quality/rollback/{batch_id}",
             summary="Rollback data quality batch",
             description="Reverts all changes from a previously applied data quality batch by restoring original entity data.")
async def data_quality_rollback(batch_id: str):
    validate_path_id(batch_id, "batch_id")
    def _query():
        try:
            result = data_quality.rollback_apply(batch_id)
        except ValueError:
            raise HTTPException(400, detail="Batch ID không hợp lệ")
        except FileNotFoundError:
            raise HTTPException(404, detail="Không tìm thấy batch")
        _sync_kb()
        return result
    return await asyncio.to_thread(_query)

# ── Stale content queue (U-17) ──

_STALE_QUEUE_MISSING_FIELDS = {"source", "images", "coordinates", "phone", "summary"}
_STALE_THRESHOLD_DEFAULT = 180


@router.get("/stale-queue",
            summary="List stale entities",
            description="Returns entities that are outdated or missing key fields, sorted by staleness. Supports filtering by missing field and entity type.")
async def stale_queue(
    threshold_days: int = Query(_STALE_THRESHOLD_DEFAULT, ge=30, le=730),
    missing_field: Optional[str] = Query(None, pattern="^(source|images|coordinates|phone|summary)$"),
    entity_type: Optional[str] = Query(None, max_length=50),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0, le=10000),
):
    """Danh sách entity cũ/thiếu thông tin — admin review queue."""
    def _query():
        now = datetime.now(timezone.utc)
        entities = knowledge._entities if getattr(knowledge, "_entities", None) else {}
        results = []
        for eid, e in entities.items():
            record = _stale_entity_record(eid, e, now, threshold_days, entity_type, missing_field)
            if record is not None:
                results.append(record)
        results.sort(key=lambda x: -(x["days_since_update"] or 0))
        total = len(results)
        return {"items": results[offset:offset + limit], "total": total}
    return await asyncio.to_thread(_query)


def _stale_days_since(updated, now) -> int:
    if updated:
        try:
            dt = datetime.fromisoformat(str(updated).replace("Z", "+00:00"))
            return (now - dt).days
        except (ValueError, TypeError):
            return 9999
    return 9999


def _stale_missing_fields(e, attrs) -> list[str]:
    missing = []
    if not e.get("source"):
        missing.append("source")
    if not e.get("images"):
        missing.append("images")
    if not e.get("coordinates"):
        missing.append("coordinates")
    if not attrs.get("phone"):
        missing.append("phone")
    if not e.get("summary"):
        missing.append("summary")
    return missing


def _stale_entity_record(eid, e, now, threshold_days, entity_type, missing_field):
    """Evaluate one entity for the stale queue; return its record dict or None to skip."""
    if e.get("type") == "place":
        return None
    if entity_type and e.get("type") != entity_type:
        return None
    updated = e.get("updatedAt") or e.get("created_at")
    days_since = _stale_days_since(updated, now)
    is_stale = days_since >= threshold_days
    attrs = e.get("attributes") or {}
    missing = _stale_missing_fields(e, attrs)
    if missing_field and missing_field not in missing:
        return None
    if not is_stale and not missing:
        return None
    return {
        "id": eid,
        "name": e.get("name"),
        "type": e.get("type"),
        "area": e.get("area"),
        "days_since_update": days_since,
        "is_stale": is_stale,
        "missing_fields": missing,
        "stale_reviewed_at": attrs.get("stale_reviewed_at"),
    }


@router.post("/stale-queue/{entity_id}/mark-reviewed",
             summary="Mark stale entity as reviewed",
             description="Records a review timestamp on the entity's attributes, indicating an admin has acknowledged its staleness.")
async def stale_mark_reviewed(entity_id: str):
    """Đánh dấu entity đã được admin xem xét — ghi timestamp vào attributes."""
    validate_path_id(entity_id, "entity_id")
    def _query():
        e = db.get_entity(entity_id)
        if not e:
            raise HTTPException(404, detail="Entity không tồn tại")
        attrs = e.get("attributes") or {}
        attrs["stale_reviewed_at"] = datetime.now(timezone.utc).isoformat()
        db.update_entity(entity_id, {"attributes": attrs})
        return {"ok": True, "entity_id": entity_id, "stale_reviewed_at": attrs["stale_reviewed_at"]}
    return await asyncio.to_thread(_query)


# ── Completeness standalone (BE-10) ──


@router.get("/completeness",
            summary="Entity completeness overview",
            description="Returns aggregate completeness statistics showing the percentage of entities that have source, images, place ID, and summary.")
async def completeness_overview():
    """Tổng quan hoàn thiện: % entities có source+images+placeId+summary."""
    def _query():
        entities = knowledge._entities if getattr(knowledge, "_entities", None) else {}
        total = 0
        has_source = 0
        has_images = 0
        has_place = 0
        has_summary = 0
        for e in entities.values():
            if e.get("type") == "place":
                continue
            total += 1
            q = data_quality.entity_quality(e)
            if q["has_source"]:
                has_source += 1
            if e.get("images"):
                has_images += 1
            if q["has_place"]:
                has_place += 1
            if e.get("summary"):
                has_summary += 1
        def pct(n):
            return round(n / total * 100, 1) if total else 0
        return {
            "total_entities": total,
            "source": {"count": has_source, "pct": pct(has_source)},
            "images": {"count": has_images, "pct": pct(has_images)},
            "place_id": {"count": has_place, "pct": pct(has_place)},
            "summary": {"count": has_summary, "pct": pct(has_summary)},
            "overall_pct": pct(has_source + has_images + has_place + has_summary) / 4 * total if total else 0,
        }
    return await asyncio.to_thread(_query)


@router.get("/completeness/details",
            summary="Entity completeness details",
            description="Returns per-entity completeness scores with missing field breakdown. Supports filtering by specific missing field and entity type.")
async def completeness_details(
    missing: Optional[str] = Query(None, pattern="^(source|images|place|summary)$"),
    entity_type: Optional[str] = Query(None, max_length=50),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0, le=10000),
):
    """Per-entity completeness scores with filter."""
    def _query():
        entities = knowledge._entities if getattr(knowledge, "_entities", None) else {}
        results = []
        for eid, e in entities.items():
            record = _completeness_detail_record(eid, e, missing, entity_type)
            if record is not None:
                results.append(record)
        results.sort(key=lambda x: x["score"])
        total = len(results)
        return {"items": results[offset:offset + limit], "total": total}
    return await asyncio.to_thread(_query)


def _completeness_detail_missing_hit(missing, q, has_imgs, has_summ) -> bool:
    """True when this entity should be skipped for the active `missing` filter."""
    if missing == "source" and q["has_source"]:
        return True
    elif missing == "images" and has_imgs:
        return True
    elif missing == "place" and q["has_place"]:
        return True
    elif missing == "summary" and has_summ:
        return True
    return False


def _completeness_detail_record(eid, e, missing, entity_type):
    if e.get("type") == "place":
        return None
    if entity_type and e.get("type") != entity_type:
        return None
    q = data_quality.entity_quality(e)
    has_imgs = bool(e.get("images"))
    has_summ = bool(e.get("summary"))
    if _completeness_detail_missing_hit(missing, q, has_imgs, has_summ):
        return None
    return {
        "id": eid,
        "name": e.get("name"),
        "type": e.get("type"),
        "score": q["score"],
        "has_source": q["has_source"],
        "has_images": has_imgs,
        "has_place": q["has_place"],
        "has_summary": has_summ,
        "missing": q["missing"] + ([] if has_imgs else ["images"]) + ([] if has_summ else ["summary"]),
    }


# ── Q&A quality queue (U-24) ──


@router.get("/qa-queue",
            summary="List Q&A posts needing attention",
            description="Returns Q&A questions that are unanswered or lack a best answer. Supports filtering by status and entity.")
async def qa_queue(
    filter: Optional[str] = Query(None, pattern="^(unanswered|no_best_answer)$"),
    entity_id: Optional[str] = Query(None, max_length=100),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0, le=10000),
):
    """Admin queue: questions chưa có best answer hoặc chưa có reply."""
    require_pg()
    ph = db._ph
    def _query():
        conditions = ["p.post_type = 'question'", "p.moderation_status = 'approved'"]
        params: list = []
        if entity_id:
            conditions.append(f"p.entity_id::text = {ph}")
            params.append(entity_id)
        if filter == "unanswered":
            conditions.append("p.comment_count = 0")
        elif filter == "no_best_answer":
            conditions.append("p.best_answer_id IS NULL")
        where = " AND ".join(conditions)
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT p.id, p.title, p.content, p.entity_id, p.user_id,
                       p.comment_count, p.best_answer_id, p.created_at,
                       u.display_name
                FROM posts p
                JOIN users u ON u.id = p.user_id
                WHERE {where}
                ORDER BY p.created_at DESC
                LIMIT {ph} OFFSET {ph}
            """, (*params, limit, offset))
            total_row = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM posts p WHERE {where}
            """, (*params,))
        total = db._row_to_dict(total_row)["c"] if total_row else 0
        return {
            "questions": [db._row_to_dict(r) for r in rows],
            "total": total,
            "filter": filter,
        }
    return await asyncio.to_thread(_query)


class SetBestAnswerBody(BaseModel):
    comment_id: str = Field(..., min_length=1, max_length=100)


@router.post("/qa-queue/{post_id}/set-best-answer",
             summary="Set best answer on Q&A post",
             description="Admin override to designate a comment as the best answer for a question post. Validates both the post and comment exist.")
async def qa_set_best_answer(post_id: str, body: SetBestAnswerBody):
    """Admin override: set best_answer_id cho 1 question."""
    require_pg()
    post_id = validate_path_id(post_id, "post_id")
    ph = db._ph
    def _query():
        with db._conn() as conn:
            post = db._fetchone(conn, f"""
                SELECT id, post_type FROM posts WHERE id::text = {ph}
            """, (post_id,))
            if not post:
                raise HTTPException(404, "Bài hỏi không tồn tại")
            p = db._row_to_dict(post)
            if p.get("post_type") != "question":
                raise HTTPException(400, "Chỉ set best answer cho post_type=question")
            comment = db._fetchone(conn, f"""
                SELECT id FROM comments WHERE id::text = {ph} AND post_id::text = {ph}
            """, (body.comment_id, post_id))
            if not comment:
                raise HTTPException(404, "Comment không thuộc bài hỏi này")
            db._execute(conn, f"""
                UPDATE posts SET best_answer_id = {ph}::uuid WHERE id::text = {ph}
            """, (body.comment_id, post_id))
        return {"ok": True, "post_id": post_id, "best_answer_id": body.comment_id}
    return await asyncio.to_thread(_query)


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
        yield "entity_id,name,zalo,phone,website,map,total\n"
        for eid, c in sorted(counts.items(), key=lambda x: -x[1]["total"]):
            name = (ent_dict.get(eid, {}).get("name") or eid).replace(",", " ")
            yield f"{eid},{name},{c['zalo']},{c['phone']},{c['website']},{c['map']},{c['total']}\n"

    return StreamingResponse(_generate(), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=contact_funnel.csv"})


# ── Collections CRUD (U-28) ──


class CollectionCreate(BaseModel):
    slug: str = Field(..., min_length=2, max_length=100, pattern=r"^[a-z0-9\-]+$")
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field("", max_length=2000)
    cover_image: str | None = None
    entity_ids: list[str] = Field(default_factory=list, max_length=100)
    sort_order: int = Field(0, ge=0)
    is_published: bool = False


class CollectionUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=2000)
    cover_image: str | None = None
    entity_ids: list[str] | None = Field(None, max_length=100)
    sort_order: int | None = Field(None, ge=0)
    is_published: bool | None = None


@router.get("/collections",
            summary="List curated collections",
            description="Returns all curated entity collections ordered by sort_order. Supports pagination via limit and offset.")
async def list_collections(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0, le=10000)):
    ph = db._ph
    def _query():
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT * FROM collections ORDER BY sort_order, created_at DESC
                LIMIT {ph} OFFSET {ph}
            """, (limit, offset))
            total_row = db._fetchone(conn, "SELECT COUNT(*) as c FROM collections", ())
        return {
            "collections": [db._row_to_dict(r) for r in rows],
            "total": db._row_to_dict(total_row)["c"] if total_row else 0,
        }
    return await asyncio.to_thread(_query)


@router.post("/collections", status_code=201,
             summary="Create a curated collection",
             description="Creates a new curated entity collection with a unique slug. Returns the created collection.")
async def create_collection(body: CollectionCreate, request: Request):
    ph = db._ph
    user = request.state.user if hasattr(request.state, "user") else None
    created_by = str(user["id"]) if user else None
    def _query():
        with db._conn() as conn:
            existing = db._fetchone(conn, f"SELECT id FROM collections WHERE slug = {ph}", (body.slug,))
            if existing:
                raise HTTPException(409, "Slug đã tồn tại")
            db._execute(conn, f"""
                INSERT INTO collections (slug, title, description, cover_image, entity_ids, sort_order, is_published, created_by)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph}::jsonb, {ph}, {ph}, {ph}::uuid)
            """, (body.slug, body.title, body.description, body.cover_image,
                  json.dumps(body.entity_ids), body.sort_order, body.is_published, created_by))
            row = db._fetchone(conn, f"SELECT * FROM collections WHERE slug = {ph}", (body.slug,))
        return db._row_to_dict(row)
    return await asyncio.to_thread(_query)


@router.put("/collections/{collection_id}",
            summary="Update a collection",
            description="Updates fields of an existing collection. Only provided fields are modified.")
async def update_collection(collection_id: str, body: CollectionUpdate):
    collection_id = validate_path_id(collection_id, "collection_id")
    ph = db._ph
    def _query():
        sets = []
        params: list = []
        if body.title is not None:
            sets.append(f"title = {ph}")
            params.append(body.title)
        if body.description is not None:
            sets.append(f"description = {ph}")
            params.append(body.description)
        if body.cover_image is not None:
            sets.append(f"cover_image = {ph}")
            params.append(body.cover_image)
        if body.entity_ids is not None:
            sets.append(f"entity_ids = {ph}::jsonb")
            params.append(json.dumps(body.entity_ids))
        if body.sort_order is not None:
            sets.append(f"sort_order = {ph}")
            params.append(body.sort_order)
        if body.is_published is not None:
            sets.append(f"is_published = {ph}")
            params.append(body.is_published)
        if not sets:
            raise HTTPException(400, "Không có trường nào để cập nhật")
        sets.append("updated_at = NOW()")
        params.append(collection_id)
        with db._conn() as conn:
            row = db._fetchone(conn, f"""
                UPDATE collections SET {', '.join(sets)} WHERE id::text = {ph} RETURNING *
            """, tuple(params))
        if not row:
            raise HTTPException(404, "Collection không tồn tại")
        return db._row_to_dict(row)
    return await asyncio.to_thread(_query)


@router.delete("/collections/{collection_id}",
               summary="Delete a collection",
               description="Permanently deletes a curated collection by its ID.")
async def delete_collection(collection_id: str):
    collection_id = validate_path_id(collection_id, "collection_id")
    ph = db._ph
    def _query():
        with db._conn() as conn:
            row = db._fetchone(conn, f"DELETE FROM collections WHERE id::text = {ph} RETURNING id", (collection_id,))
        if not row:
            raise HTTPException(404, "Collection không tồn tại")
        return {"ok": True, "deleted": collection_id}
    return await asyncio.to_thread(_query)


# ── Review responses (U-11) ──


class ReviewResponseBody(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


@router.post("/posts/{post_id}/response",
             summary="Respond to a review post",
             description="Creates an admin or business response to a review post. Only one response per review is allowed.")
async def admin_review_response(post_id: str, body: ReviewResponseBody, request: Request):
    """Admin/business reply to a review — one response per review (UNIQUE)."""
    require_pg()
    post_id = validate_path_id(post_id, "post_id")
    ph = db._ph
    responder_id = _require_admin_actor_id(request)
    def _query():
        with db._conn() as conn:
            post = db._fetchone(conn, f"SELECT user_id, post_type FROM posts WHERE id::text = {ph}", (post_id,))
            if not post:
                raise HTTPException(404, "Bài viết không tồn tại")
            pd = db._row_to_dict(post)
            if pd.get("post_type") != "review":
                raise HTTPException(400, "Chỉ phản hồi cho bài đánh giá (review)")
            db._execute(conn, f"SELECT pg_advisory_xact_lock(hashtext({ph}))", (f"review_resp:{post_id}",))
            existing = db._fetchone(conn, f"SELECT id FROM review_responses WHERE post_id::text = {ph}", (post_id,))
            if existing:
                raise HTTPException(409, "Bài đánh giá đã có phản hồi")
            db._execute(conn, f"""
                INSERT INTO review_responses (post_id, responder_id, content)
                VALUES ({ph}::uuid, {ph}::uuid, {ph})
            """, (post_id, responder_id, _html.escape(body.content.strip())))
            row = db._fetchone(conn, f"SELECT * FROM review_responses WHERE post_id::text = {ph}", (post_id,))
        _log_mod_action("review_response", post_id, "added")
        try:
            create_notification(str(pd["user_id"]), "social",
                                "Đánh giá của bạn đã nhận được phản hồi",
                                ref_type="post", ref_id=post_id)
        except Exception:
            logger.exception("Failed to notify review response %s", post_id)
        return db._row_to_dict(row) if row else {"ok": True}
    return await asyncio.to_thread(_query)


@router.get("/posts/{post_id}/response",
            summary="Get review response",
            description="Returns the admin response for a specific review post, if one exists.")
async def get_review_response(post_id: str):
    """Get the admin response for a review post."""
    require_pg()
    post_id = validate_path_id(post_id, "post_id")
    ph = db._ph
    def _query():
        with db._conn() as conn:
            row = db._fetchone(conn, f"""
                SELECT rr.*, u.display_name as responder_name
                FROM review_responses rr
                JOIN users u ON u.id = rr.responder_id
                WHERE rr.post_id::text = {ph}
            """, (post_id,))
        if not row:
            return None
        return db._row_to_dict(row)
    result = await asyncio.to_thread(_query)
    if not result:
        raise HTTPException(404, "Không tìm thấy phản hồi review")
    return result


class BulkDeleteRequest(BaseModel):
    entity_ids: list[str] = Field(..., min_length=1, max_length=200)

@router.post("/entities/bulk-delete",
             summary="Bulk delete entities",
             description="Deletes multiple entities by their IDs in a single operation. Returns the count of successfully deleted entities.")
async def bulk_delete(body: BulkDeleteRequest):
    """Xóa nhiều entities cùng lúc."""
    def _query():
        from public_api import invalidate_entity_cache
        deleted = 0
        for eid in body.entity_ids:
            if db.delete_entity(eid):
                invalidate_entity_cache(eid)
                deleted += 1
        if deleted:
            _sync_kb()
        return deleted
    deleted = await asyncio.to_thread(_query)
    return {"success": True, "count": deleted}


# ══════════════════════════════════════════════════
#  IMAGE INGEST REVIEW QUEUE (P2, review-gated — B6)
# ══════════════════════════════════════════════════
# Human-in-the-loop: ingest scripts queue licensed image CANDIDATES; nothing goes
# live until an admin approves here. On approve we re-encode + upload to R2 and
# carry license + author + source onto the entity (attributes.image_credits) per B6.

import image_suggestions as _imgq


class ImageSuggestionItem(BaseModel):
    entity_id: str = Field(..., min_length=1, max_length=100)
    candidate_url: str = Field(..., min_length=1, max_length=600)
    wp_title: str = Field("", max_length=200)
    license: str = Field("", max_length=80)
    author: str = Field("", max_length=120)
    source: str = Field("wikipedia-vi", max_length=40)
    match_confidence: float = Field(0.7, ge=0.0, le=1.0)


class ImageSuggestionBatch(BaseModel):
    suggestions: list[ImageSuggestionItem] = Field(..., max_length=500)


class RejectSuggestionRequest(BaseModel):
    reason: str | None = Field(None, max_length=300)


@router.get("/image-suggestions",
            summary="List image suggestions",
            description="Lists image candidates awaiting review. Filterable by status and entity_id with pagination.")
async def list_image_suggestions(
    status: Optional[str] = Query(None, pattern="^(pending|approved|rejected)$"),
    entity_id: Optional[str] = Query(None, max_length=100),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0, le=10000),
):
    """Liệt kê ứng viên ảnh chờ duyệt (mặc định: tất cả; lọc theo status/entity)."""
    def _query():
        result = _imgq.list_suggestions(status=status, entity_id=entity_id, limit=limit, offset=offset)
        result["counts"] = _imgq.status_counts()
        return result
    return await asyncio.to_thread(_query)


@router.get("/image-suggestions/{suggestion_id}",
            summary="Get image suggestion details",
            description="Returns full details of a single image suggestion including entity name for review.")
async def get_image_suggestion(suggestion_id: str):
    """Chi tiết 1 ứng viên ảnh (kèm tên entity để review)."""
    validate_path_id(suggestion_id, "suggestion_id")
    def _query():
        s = _imgq.get_suggestion(suggestion_id)
        if not s:
            raise HTTPException(404, "Đề xuất không tồn tại")
        return s
    return await asyncio.to_thread(_query)


@router.post("/image-suggestions/create-batch", status_code=201,
             summary="Create image suggestion batch",
             description="Queues a batch of image candidates from ingest scripts for admin review. Does not publish anything.")
async def create_image_suggestion_batch(body: ImageSuggestionBatch):
    """Nhận lô ứng viên từ script ingest (mode=queue). KHÔNG publish — chỉ xếp hàng chờ duyệt."""
    def _query():
        payload = [s.model_dump() for s in body.suggestions]
        return _imgq.create_batch(payload)
    return await asyncio.to_thread(_query)


def _is_blocked_ip(ip) -> bool:
    return (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
            or ip.is_multicast or ip.is_unspecified)


def _assert_public_url(url: str) -> None:
    """P0-13: chặn SSRF — chỉ http(s) tới host phân giải ra IP CÔNG KHAI
    (chặn 169.254.169.254, localhost, 10/172.16/192.168, link-local…)."""
    import ipaddress
    import socket
    from urllib.parse import urlparse
    p = urlparse(url or "")
    if p.scheme not in ("http", "https") or not p.hostname:
        raise HTTPException(400, "URL ảnh không hợp lệ (chỉ http/https)")
    try:
        infos = socket.getaddrinfo(p.hostname, p.port or (443 if p.scheme == "https" else 80))
    except Exception:
        raise HTTPException(400, "Không phân giải được host ảnh")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if _is_blocked_ip(ip):
            raise HTTPException(400, "Host ảnh trỏ địa chỉ nội bộ — từ chối (SSRF)")


def _fetch_public_url(url: str, headers: dict[str, str], timeout: int = 25, max_redirects: int = 5):
    """Fetch a public URL while re-validating every redirect target."""
    import httpx
    from urllib.parse import urljoin

    current_url = url
    for _ in range(max_redirects + 1):
        _assert_public_url(current_url)
        resp = httpx.get(current_url, headers=headers, timeout=timeout, follow_redirects=False)
        if 300 <= resp.status_code < 400 and resp.headers.get("location"):
            current_url = urljoin(str(resp.url), resp.headers["location"])
            continue
        _assert_public_url(str(resp.url))
        return resp
    raise HTTPException(400, "URL ảnh chuyển hướng quá nhiều lần")

async def _approve_fetch_image_data(candidate_url, run_in_threadpool, max_image_size):
    """Fetch + validate the candidate image bytes for approve_image_suggestion."""
    try:
        headers = {"User-Agent": "vinhlong360-image-review/1.0 (+https://vinhlong360.vn)"}
        resp = await run_in_threadpool(
            lambda: _fetch_public_url(candidate_url, headers=headers, timeout=25)
        )
        resp.raise_for_status()
        data = resp.content
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001 — network/404 → 502 with retry note
        logger.warning("Suggestion image fetch failed for %s: %s", candidate_url, e)
        raise HTTPException(502, "Không tải được ảnh nguồn, vui lòng thử lại sau")

    if not data or len(data) > max_image_size:
        raise HTTPException(400, f"Ảnh nguồn rỗng hoặc quá lớn (tối đa {max_image_size // 1024 // 1024}MB)")
    return data


def _approve_attach_credits(entity, cover, s, candidate_url):
    """Append the license/author/source credit for the uploaded cover URL; return credits list."""
    attrs = entity.get("attributes") or {}
    if not isinstance(attrs, dict):
        attrs = {}
    credits = attrs.get("image_credits")
    if not isinstance(credits, list):
        credits = []
    credits.append({
        "url": cover,
        "license": s.get("license") or "",
        "author": s.get("author") or "",
        "source": s.get("source") or "",
        "source_url": candidate_url,
        "wp_title": s.get("wp_title") or "",
        "added_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    })
    attrs["image_credits"] = credits
    entity["attributes"] = attrs
    return credits


@router.post("/image-suggestions/{suggestion_id}/approve",
             summary="Approve an image suggestion",
             description="Approves a pending image suggestion: downloads, re-encodes to WebP, uploads to storage, and attaches to the entity with license credits.")
async def approve_image_suggestion(suggestion_id: str):
    """Duyệt 1 ứng viên: tải ảnh → WebP 3 cỡ → R2 → gắn vào entity.images + lưu
    license/author/source vào attributes.image_credits (B6). Chỉ xử lý khi đang 'pending'."""
    validate_path_id(suggestion_id, "suggestion_id")
    from fastapi.concurrency import run_in_threadpool
    from storage import storage, MAX_IMAGE_SIZE

    s = _imgq.get_suggestion(suggestion_id)
    if not s:
        raise HTTPException(404, "Đề xuất không tồn tại")
    if s.get("status") != "pending":
        raise HTTPException(400, f"Suggestion đã ở trạng thái '{s.get('status')}' — không thể duyệt lại")

    entity = db.get_entity(s["entity_id"])
    if not entity:
        raise HTTPException(404, f"Entity '{s['entity_id']}' not found")

    images = list(entity.get("images") or [])
    if len(images) >= 10:
        raise HTTPException(400, "Tối đa 10 ảnh mỗi entity")

    # Fetch the candidate from its licensed source (Commons etc.). Bounded + guarded.
    candidate_url = s["candidate_url"]
    await asyncio.to_thread(_assert_public_url, candidate_url)  # P0-13: chặn SSRF tới host nội bộ
    data = await _approve_fetch_image_data(candidate_url, run_in_threadpool, MAX_IMAGE_SIZE)

    try:
        urls = await run_in_threadpool(storage.upload_image_set, data, "entities", s["entity_id"])
    except Exception:
        logger.exception("Suggestion image upload failed for %s", s.get("entity_id"))
        raise HTTPException(500, "Không thể upload ảnh, vui lòng thử lại")

    cover = urls.get("md") or urls.get("lg") or urls.get("sm")
    if cover and cover not in images:
        images.append(cover)
    entity["images"] = images

    # B6: persist license + author + source alongside the uploaded URL.
    credits = _approve_attach_credits(entity, cover, s, candidate_url)
    entity["updatedAt"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    db.upsert_entity(entity)

    # require_admin already authenticated; record a generic approver marker for audit.
    _imgq.mark_status(suggestion_id, "approved", approved_by="admin")
    _sync_kb()
    return {"status": "approved", "url": cover, "sizes": urls, "images": images,
            "backend": storage.backend, "credits": credits[-1]}


@router.post("/image-suggestions/{suggestion_id}/reject",
              summary="Reject image suggestion",
              description="Reject a pending image suggestion by ID, optionally recording a reason. No files are downloaded or uploaded.")
async def reject_image_suggestion(suggestion_id: str, body: RejectSuggestionRequest = RejectSuggestionRequest()):
    """Từ chối 1 ứng viên (ghi lý do). Không tải/không upload gì."""
    validate_path_id(suggestion_id, "suggestion_id")
    def _query():
        s = _imgq.get_suggestion(suggestion_id)
        if not s:
            raise HTTPException(404, "Đề xuất không tồn tại")
        if s.get("status") != "pending":
            raise HTTPException(400, f"Suggestion đã ở trạng thái '{s.get('status')}' — không thể từ chối lại")
        _imgq.mark_status(suggestion_id, "rejected", rejection_reason=(body.reason or "").strip())
    await asyncio.to_thread(_query)
    return {"status": "rejected", "id": suggestion_id}


# ── Data management ──

_server_start_time = __import__("time").time()


@router.get("/system-health",
            summary="Get system health status",
            description="Returns system health information including SQLite/Postgres status, server uptime, memory usage, and storage metrics.")
def _system_health_server(result, os, _t) -> None:
    result["server"]["uptime_seconds"] = int(_t.time() - _server_start_time)
    result["server"]["uptime_human"] = _format_uptime(int(_t.time() - _server_start_time))
    result["server"]["pid"] = os.getpid()
    try:
        import psutil
        proc = psutil.Process(os.getpid())
        result["server"]["memory_mb"] = round(proc.memory_info().rss / 1024 / 1024, 1)
    except (ImportError, Exception):
        result["server"]["memory_mb"] = -1


def _system_health_pg(result) -> None:
    with db._conn() as conn:
        tables = ["users", "posts", "comments", "likes", "follows",
                   "notifications", "blocks", "sessions", "user_visits",
                   "reports", "saved_entities", "announcements"]
        pg_tables = {}
        for t in tables:
            try:
                row = db._fetchone(conn, f"SELECT COUNT(*) as c FROM {t}", ())
                pg_tables[t] = db._row_to_dict(row)["c"] if row else 0
            except Exception:
                pg_tables[t] = -1
        result["postgres"]["tables"] = pg_tables
        try:
            size_row = db._fetchone(conn, """
                SELECT pg_database_size(current_database()) as s
            """, ())
            result["postgres"]["size_mb"] = round(db._row_to_dict(size_row)["s"] / 1024 / 1024, 2) if size_row else 0
        except Exception:
            result["postgres"]["size_mb"] = -1
        active_row = db._fetchone(conn, """
            SELECT COUNT(*) as c FROM sessions WHERE expires_at > NOW()
        """, ())
        result["postgres"]["active_sessions"] = db._row_to_dict(active_row)["c"] if active_row else 0
        pending_row = db._fetchone(conn, """
            SELECT COUNT(*) as c FROM posts WHERE moderation_status = 'pending'
        """, ())
        result["postgres"]["pending_moderation"] = db._row_to_dict(pending_row)["c"] if pending_row else 0
        open_reports = db._fetchone(conn, """
            SELECT COUNT(*) as c FROM reports WHERE status = 'pending'
        """, ())
        result["postgres"]["open_reports"] = db._row_to_dict(open_reports)["c"] if open_reports else 0


async def system_health():
    import os
    import time as _t
    def _query():
        result = {"sqlite": {}, "postgres": {}, "server": {}}
        _system_health_server(result, os, _t)
        db_path = os.path.join(os.path.dirname(__file__), "data", "knowledge.db")
        if os.path.exists(db_path):
            result["sqlite"]["size_mb"] = round(os.path.getsize(db_path) / 1024 / 1024, 2)
            result["sqlite"]["entities"] = sum(db.count_entities().values())
        if db._use_pg:
            _system_health_pg(result)
        data_dir = Path(__file__).resolve().parent / "data"
        jsonl_files = list(data_dir.glob("*.jsonl"))
        result["storage"] = {
            "jsonl_files": len(jsonl_files),
            "jsonl_size_mb": round(sum(f.stat().st_size for f in jsonl_files) / 1024 / 1024, 2),
        }
        return result
    return await asyncio.to_thread(_query)


def _format_uptime(seconds: int) -> str:
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return " ".join(parts)


@router.get("/featured",
            summary="List featured entities",
            description="Returns all currently featured entities with their sort order, name, and type.")
async def list_featured():
    def _query():
        if not db._use_pg:
            return {"featured": []}
        with db._conn() as conn:
            rows = db._fetchall(conn, """
                SELECT entity_id, sort_order, created_at
                FROM featured_entities ORDER BY sort_order
            """, ())
        items = [db._row_to_dict(r) for r in rows]
        batch = db.get_entities_batch([rd["entity_id"] for rd in items])
        result = []
        for rd in items:
            entity = batch.get(rd["entity_id"])
            if entity:
                result.append({
                    "entity_id": rd["entity_id"],
                    "name": entity.get("name"),
                    "type": entity.get("type"),
                    "sort_order": rd["sort_order"],
                    "created_at": str(rd["created_at"]),
                })
        return {"featured": result}
    return await asyncio.to_thread(_query)


@router.post("/featured/{entity_id}",
             summary="Toggle entity featured status",
             description="Add or remove an entity from the featured list. If already featured, it is removed; otherwise it is added.")
async def toggle_featured(entity_id: str, request: Request):
    entity_id = validate_path_id(entity_id, "entity_id")
    entity = await asyncio.to_thread(db.get_entity, entity_id)
    if not entity:
        raise HTTPException(404, "Entity không tồn tại")
    admin_user = getattr(request.state, "admin_user", None)
    ph = db._ph
    def _query():
        if not db._use_pg:
            raise HTTPException(503, "Chức năng này yêu cầu Postgres")
        with db._conn() as conn:
            existing = db._fetchone(conn, f"""
                SELECT id FROM featured_entities WHERE entity_id = {ph}
            """, (entity_id,))
            if existing:
                db._execute(conn, f"DELETE FROM featured_entities WHERE entity_id = {ph}", (entity_id,))
                return False
            added_by = str(admin_user["id"]) if admin_user else None
            db._execute(conn, f"""
                INSERT INTO featured_entities (entity_id, added_by, sort_order)
                VALUES ({ph}, {ph}::uuid, (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM featured_entities))
            """, (entity_id, added_by))
            return True
    is_featured = await asyncio.to_thread(_query)
    return {"entity_id": entity_id, "featured": is_featured}


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


def _latest_backup_info() -> dict:
    backup_dir = ROOT / "scratch" / "backups"
    if not backup_dir.exists():
        return {"ready": False, "latest": None, "count": 0, "size_mb": 0}
    dirs = sorted([p for p in backup_dir.iterdir() if p.is_dir()], key=lambda p: p.name, reverse=True)
    if not dirs:
        return {"ready": False, "latest": None, "count": 0, "size_mb": 0}
    latest = dirs[0]
    size_mb = round(sum(f.stat().st_size for f in latest.rglob("*") if f.is_file()) / 1048576, 1)
    return {"ready": True, "latest": latest.name, "count": len(dirs), "size_mb": size_mb}


@router.get("/backup-status",
            summary="Get latest backup status",
            description="Returns a thin snapshot of the latest local backup (readiness, name, count, size) — same info already surfaced inside /admin/stats and /admin/ops-summary, exposed standalone for lightweight polling.")
async def backup_status():
    """B5c: route mỏng bọc _latest_backup_info() — không thêm logic mới."""
    return {"backup": await asyncio.to_thread(_latest_backup_info)}


def _data_quality_ops_snapshot() -> dict:
    queue_path = data_quality.BURST_DIR / data_quality.QUEUE_FILE
    counts = {"auto_apply": 0, "needs_review": 0, "reject": 0}
    stream_counts = {}
    cache = {"exists": queue_path.exists(), "path": str(queue_path)}
    policy = {}
    if queue_path.exists():
        try:
            queue = json.loads(queue_path.read_text(encoding="utf-8-sig"))
            for bucket in counts:
                counts[bucket] = len(queue.get(bucket, []) or [])
            stream_counts = queue.get("stream_counts", {}) or {}
            policy = queue.get("policy", {}) or {}
            stat = queue_path.stat()
            cache.update({
                "size_bytes": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(timespec="seconds"),
            })
        except Exception:
            logger.debug("ops data-quality queue read failed", exc_info=True)
            cache["error"] = "read_failed"
    decisions = _safe(lambda: data_quality.load_decision_history(limit=20), {"total": 0, "decisions": []})
    return {
        "counts": counts,
        "total": sum(counts.values()),
        "stream_counts": stream_counts,
        "cache": cache,
        "policy": policy,
        "decision_total": decisions.get("total", 0),
        "recent_decisions": decisions.get("decisions", [])[:5],
    }

_QUALITY_TREND_KEYS = (
    "quality_score_avg",
    "image_coverage_pct",
    "place_coords_coverage_pct",
    "image_missing_credit",
    "image_missing_license",
    "image_missing_source",
    "duplicate_source_urls",
    "self_citation_pct",
)

def _quality_trend_meta(value):
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _quality_trend_fetch_rows():
    """Return (latest_rows, baseline_rows, count_row) or None on failure/no-pg."""
    with db._conn() as conn:
        latest_rows = db._fetchall(conn, """
            SELECT DISTINCT ON (metric_key)
                metric_key, metric_value, metric_unit, metadata, created_at
            FROM quality_metric_snapshots
            WHERE metric_key = ANY(%s)
            ORDER BY metric_key, created_at DESC
        """, (list(_QUALITY_TREND_KEYS),))
        baseline_rows = db._fetchall(conn, """
            SELECT DISTINCT ON (metric_key)
                metric_key, metric_value, created_at
            FROM quality_metric_snapshots
            WHERE metric_key = ANY(%s)
              AND created_at <= NOW() - INTERVAL '7 days'
            ORDER BY metric_key, created_at DESC
        """, (list(_QUALITY_TREND_KEYS),))
        count_row = db._fetchone(conn, """
            SELECT COUNT(*) AS c
            FROM quality_metric_snapshots
            WHERE created_at > NOW() - INTERVAL '30 days'
        """, ())
    return latest_rows, baseline_rows, count_row


def _quality_trend_budget_failure(meta, key, value):
    """Return a budget-failure dict for this metric, or None when the budget is met/absent."""
    budget = meta.get("budget") if isinstance(meta, dict) else None
    if isinstance(budget, dict) and budget.get("ok") is False:
        return {
            "metric_key": key,
            "value": round(value, 2),
            "expected": budget.get("expected"),
            "op": budget.get("op"),
            "severity": budget.get("severity") or "error",
        }
    return None


def _quality_trend_process_latest(latest_rows):
    """Return (latest, budget_failures, last_recorded_at) from the latest snapshot rows."""
    latest: dict[str, dict] = {}
    budget_failures: list[dict] = []
    last_recorded_at = None
    for row in latest_rows:
        item = db._row_to_dict(row)
        key = str(item.get("metric_key"))
        value = float(item.get("metric_value") or 0)
        created = item.get("created_at")
        created_iso = created.isoformat(timespec="seconds") if hasattr(created, "isoformat") else str(created or "")
        meta = _quality_trend_meta(item.get("metadata"))
        latest[key] = {
            "value": round(value, 2),
            "unit": item.get("metric_unit") or "count",
            "created_at": created_iso,
        }
        if created_iso and (not last_recorded_at or created_iso > last_recorded_at):
            last_recorded_at = created_iso
        failure = _quality_trend_budget_failure(meta, key, value)
        if failure is not None:
            budget_failures.append(failure)
    return latest, budget_failures, last_recorded_at


def _quality_trend_ops_snapshot() -> dict:
    empty = {
        "available": False,
        "latest": {},
        "delta_7d": {},
        "budget_failures": [],
        "sample_count": 0,
        "last_recorded_at": None,
    }
    if not db._use_pg:
        return empty

    try:
        latest_rows, baseline_rows, count_row = _quality_trend_fetch_rows()
    except Exception:
        logger.debug("ops quality trend read failed", exc_info=True)
        return empty

    latest, budget_failures, last_recorded_at = _quality_trend_process_latest(latest_rows)

    baseline = {str(db._row_to_dict(row).get("metric_key")): float(db._row_to_dict(row).get("metric_value") or 0) for row in baseline_rows}
    delta_7d = {
        key: round(item["value"] - baseline[key], 2)
        for key, item in latest.items()
        if key in baseline
    }
    return {
        "available": bool(latest),
        "latest": latest,
        "delta_7d": delta_7d,
        "budget_failures": budget_failures,
        "sample_count": int(db._row_to_dict(count_row).get("c") or 0) if count_row else 0,
        "last_recorded_at": last_recorded_at,
    }

def _ops_moderation_snapshot() -> dict:
    moderation = {"pending": 0, "flagged": 0, "reports": 0, "appeals": 0, "oldest_pending_hours": None}
    if db._use_pg:
        with db._conn() as conn:
            pending = db._fetchone(conn, "SELECT COUNT(*) as c FROM posts WHERE moderation_status IN ('pending','review')", ())
            flagged = db._fetchone(conn, "SELECT COUNT(*) as c FROM posts WHERE moderation_status = 'flagged'", ())
            reports = db._fetchone(conn, "SELECT COUNT(*) as c FROM reports WHERE status = 'pending'", ())
            appeals = db._fetchone(conn, "SELECT COUNT(*) as c FROM moderation_appeals WHERE status = 'pending'", ())
            oldest = db._fetchone(conn, """
                SELECT EXTRACT(EPOCH FROM (NOW() - MIN(created_at))) / 3600 as h
                FROM posts WHERE moderation_status IN ('pending','review','flagged')
            """, ())
        moderation.update({
            "pending": int(db._row_to_dict(pending)["c"] if pending else 0),
            "flagged": int(db._row_to_dict(flagged)["c"] if flagged else 0),
            "reports": int(db._row_to_dict(reports)["c"] if reports else 0),
            "appeals": int(db._row_to_dict(appeals)["c"] if appeals else 0),
            "oldest_pending_hours": round(float(db._row_to_dict(oldest).get("h") or 0), 1) if oldest else None,
        })
    return moderation


def _ops_audit_snapshot() -> dict:
    audit = {"jsonl_exists": _AUDIT_FILE.exists(), "db_available": False, "source": "jsonl", "recent_entries": 0, "last_ts": None}
    db_audit = _query_admin_audit_db(100)
    if db_audit is not None:
        audit["db_available"] = True
        audit["source"] = "db"
        audit["recent_entries"] = min(int(db_audit.get("total") or 0), 100)
        entries = db_audit.get("entries") or []
        if entries:
            audit["last_ts"] = entries[0].get("ts")
    if _AUDIT_FILE.exists():
        try:
            lines = [l for l in _AUDIT_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]
            if not audit["db_available"]:
                audit["recent_entries"] = min(len(lines), 100)
                if lines:
                    audit["last_ts"] = json.loads(lines[-1]).get("ts")
        except Exception:
            logger.debug("ops audit read failed", exc_info=True)
    return audit


@router.get("/ops-summary",
            summary="Get AdminCP operations summary",
            description="Returns release/deploy readiness, queue backlog, data-quality budgets, audit freshness, cost budget, and rollback readiness for the admin cockpit.")
async def ops_summary():
    """Ops cockpit snapshot: lightweight, read-only, no background jobs."""
    def _query():
        deploy_path = ROOT / "scripts" / "deploy.sh"
        gate_path = ROOT / "scripts" / "release_gate.ps1"
        deploy_text = deploy_path.read_text(encoding="utf-8", errors="ignore") if deploy_path.exists() else ""
        gate_text = gate_path.read_text(encoding="utf-8", errors="ignore") if gate_path.exists() else ""
        migrations = sorted((ROOT / "agent" / "migrations").glob("*.sql"))
        backup = _latest_backup_info()
        dq = _data_quality_ops_snapshot()
        quality_trend = _quality_trend_ops_snapshot()

        moderation = _ops_moderation_snapshot()
        audit = _ops_audit_snapshot()

        cost = _safe(lambda: _get_cost_report(), {}) if _HAS_COST else {}
        schema_status = db.pg_schema_status()
        shared_controls = {
            "rate_limit_enabled": os.environ.get("VL360_SHARED_RATE_LIMIT", "true").strip().lower() not in {"0", "false", "no", "off"},
            "idempotency_enabled": os.environ.get("VL360_SHARED_IDEMPOTENCY", "true").strip().lower() not in {"0", "false", "no", "off"},
            "tables_ready": bool(schema_status.get("ok")),
        }
        deploy_ready = all([
            "VL360_DEPLOY_HOST" in deploy_text,
            "/health/ready" in deploy_text,
            "exit 1" in deploy_text,
        ])
        gate_ready = all(token in gate_text for token in ("test_qa_fixes.py", "vue-tsc", "smoke_e2e_chrome.mjs", "check_migration_gate.py", "quality_budget.py"))
        release_state = {
            "gate_script": gate_path.exists(),
            "gate_covers_backend_frontend_e2e": gate_ready,
            "deploy_script": deploy_path.exists(),
            "deploy_host_env_configured": bool(os.environ.get("VL360_DEPLOY_HOST")),
            "deploy_health_blocking": deploy_ready,
            "latest_migration": migrations[-1].name if migrations else None,
            "migration_count": len(migrations),
            "schema_ok": bool(schema_status.get("ok")),
            "schema_version": schema_status.get("schema_version"),
            "required_schema_version": schema_status.get("required_schema_version"),
        }
        queue_backlog = {
            "moderation": moderation["pending"] + moderation["flagged"],
            "reports": moderation["reports"],
            "appeals": moderation["appeals"],
            "data_quality": dq["total"],
        }
        rollback = {
            "backup_ready": backup["ready"],
            "latest_backup": backup["latest"],
            "backup_count": backup["count"],
            "backup_size_mb": backup["size_mb"],
            "restore_drill_documented": (ROOT / "docs" / "deployment-guide.md").exists(),
            "restore_drill_script": (ROOT / "scripts" / "restore_drill.py").exists(),
        }
        quality_budget_ok = not quality_trend.get("budget_failures")
        status = "ok" if gate_ready and deploy_ready and backup["ready"] and schema_status.get("ok") and quality_budget_ok else "attention"
        return {
            "status": status,
            "release": release_state,
            "schema": schema_status,
            "shared_controls": shared_controls,
            "queues": queue_backlog,
            "moderation_sla": moderation,
            "data_quality": dq,
            "quality_trend": quality_trend,
            "audit": audit,
            "cost": cost,
            "rollback": rollback,
        }
    return await asyncio.to_thread(_query)

@router.get("/user-engagement",
            summary="Get user engagement metrics",
            description="Returns engagement metrics over a configurable period: active posters, commenters, likers, retention rate, and daily active users.")
async def user_engagement_stats(days: int = Query(30, ge=1, le=365)):
    require_pg()
    ph = db._ph
    def _query():
        interval_param = f"{days} days"
        with db._conn() as conn:
            active_posters = db._fetchone(conn, f"""
                SELECT COUNT(DISTINCT user_id) as c FROM posts
                WHERE created_at > NOW() - CAST({ph} AS INTERVAL)
            """, (interval_param,))
            active_commenters = db._fetchone(conn, f"""
                SELECT COUNT(DISTINCT user_id) as c FROM comments
                WHERE created_at > NOW() - CAST({ph} AS INTERVAL)
            """, (interval_param,))
            active_likers = db._fetchone(conn, f"""
                SELECT COUNT(DISTINCT user_id) as c FROM likes
                WHERE created_at > NOW() - CAST({ph} AS INTERVAL)
            """, (interval_param,))
            new_users = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM users
                WHERE created_at > NOW() - CAST({ph} AS INTERVAL)
            """, (interval_param,))
            retained = db._fetchone(conn, f"""
                SELECT COUNT(DISTINCT p.user_id) as c FROM posts p
                JOIN users u ON u.id = p.user_id
                WHERE p.created_at > NOW() - CAST({ph} AS INTERVAL)
                  AND u.created_at < NOW() - CAST({ph} AS INTERVAL)
            """, (interval_param, interval_param))
            total_users = db._fetchone(conn, "SELECT COUNT(*) as c FROM users WHERE is_active = TRUE", ())
            daily = db._fetchall(conn, f"""
                SELECT DATE(created_at) as day, COUNT(DISTINCT user_id) as active_users
                FROM posts WHERE created_at > NOW() - CAST({ph} AS INTERVAL)
                GROUP BY DATE(created_at) ORDER BY day
            """, (interval_param,))
        tu = db._row_to_dict(total_users)["c"] if total_users else 1
        ap = db._row_to_dict(active_posters)["c"] if active_posters else 0
        return {
            "period_days": days,
            "total_active_users": tu,
            "active_posters": ap,
            "active_commenters": db._row_to_dict(active_commenters)["c"] if active_commenters else 0,
            "active_likers": db._row_to_dict(active_likers)["c"] if active_likers else 0,
            "new_users": db._row_to_dict(new_users)["c"] if new_users else 0,
            "retained_users": db._row_to_dict(retained)["c"] if retained else 0,
            "engagement_rate": round(ap / tu * 100, 1) if tu else 0,
            "daily_active": [{"day": str(db._row_to_dict(r)["day"]), "users": db._row_to_dict(r)["active_users"]} for r in daily],
        }
    return await asyncio.to_thread(_query)


@router.get("/user-growth",
            summary="Get user growth over time",
            description="Returns daily signup counts, total/deactivated user counts, and week-over-week growth rate.")
async def user_growth(days: int = Query(30, ge=7, le=365)):
    require_pg()
    ph = db._ph
    def _query():
        interval_param = f"{days} days"
        with db._conn() as conn:
            daily_reg = db._fetchall(conn, f"""
                SELECT DATE(created_at) as day, COUNT(*) as signups
                FROM users
                WHERE created_at > NOW() - CAST({ph} AS INTERVAL)
                GROUP BY DATE(created_at) ORDER BY day
            """, (interval_param,))
            total = db._fetchone(conn, "SELECT COUNT(*) as c FROM users WHERE is_active = TRUE", ())
            deactivated = db._fetchone(conn, "SELECT COUNT(*) as c FROM users WHERE is_active = FALSE", ())
            week_ago = db._fetchone(conn, """
                SELECT COUNT(*) as c FROM users WHERE created_at > NOW() - INTERVAL '7 days'
            """, ())
            prev_week = db._fetchone(conn, """
                SELECT COUNT(*) as c FROM users
                WHERE created_at > NOW() - INTERVAL '14 days'
                  AND created_at <= NOW() - INTERVAL '7 days'
            """, ())
        t = db._row_to_dict(total)["c"] if total else 0
        d = db._row_to_dict(deactivated)["c"] if deactivated else 0
        w = db._row_to_dict(week_ago)["c"] if week_ago else 0
        pw = db._row_to_dict(prev_week)["c"] if prev_week else 0
        growth_rate = round((w - pw) / pw * 100, 1) if pw > 0 else 0
        return {
            "total_users": t,
            "active_users": t,
            "deactivated_users": d,
            "signups_this_week": w,
            "signups_prev_week": pw,
            "growth_rate_pct": growth_rate,
            "daily_signups": [{"day": str(db._row_to_dict(r)["day"]), "signups": db._row_to_dict(r)["signups"]} for r in daily_reg],
        }
    return await asyncio.to_thread(_query)


_last_backup_time: float = 0
_BACKUP_COOLDOWN = _cfg.BACKUP_COOLDOWN

@router.post("/backup-trigger",
             summary="Trigger data backup",
             description="Initiates a manual backup of the database. Returns the backup file path, size, and status. Rate-limited by a cooldown period.")
async def trigger_backup():
    """B5c: trigger manual backup from admin UI."""
    import time as _time
    global _last_backup_time
    now = _time.monotonic()
    if now - _last_backup_time < _BACKUP_COOLDOWN:
        remaining = int(_BACKUP_COOLDOWN - (now - _last_backup_time))
        raise HTTPException(429, f"Backup đã chạy gần đây. Thử lại sau {remaining} giây.")
    _last_backup_time = now
    script = Path(__file__).resolve().parent.parent / "scripts" / "backup_data.py"  # noqa: ASYNC240 (dựng path rẻ; I/O thật bọc asyncio.to_thread bên dưới)
    if not script.exists():
        raise HTTPException(500, "Không tìm thấy script backup_data.py")
    def _run():
        try:
            result = subprocess.run(
                [sys.executable, str(script), "--label", "admin-manual"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                logger.error("Backup script failed: %s", result.stderr)
                raise HTTPException(500, "Backup thất bại. Kiểm tra log server.")
            backup_dir = Path(__file__).resolve().parent.parent / "scratch" / "backups"
            dirs = sorted(backup_dir.iterdir(), key=lambda p: p.name, reverse=True)
            latest = dirs[0] if dirs else None
            size_mb = round(sum(f.stat().st_size for f in latest.rglob("*") if f.is_file()) / 1048576, 1) if latest else 0
            return {
                "success": True,
                "backup_name": latest.name if latest else None,
                "size_mb": size_mb,
                "output": result.stdout.strip(),
            }
        except subprocess.TimeoutExpired:
            raise HTTPException(504, "Backup timed out")
        except HTTPException:
            raise
        except Exception:
            logger.exception("Backup failed")
            raise HTTPException(500, "Backup thất bại. Kiểm tra log server.")
    return await asyncio.to_thread(_run)


@router.get("/media",
            summary="List uploaded media files",
            description="Returns a paginated gallery of all images across entities with credit and duplicate detection stats.")
async def media_gallery(
    page: int = Query(1, ge=1, le=1000),
    limit: int = Query(50, ge=1, le=200),
    filter: str = Query("all", pattern="^(all|missing_credit|duplicate)$"),
):
    """B6a: Central media gallery — cached extraction, avoids re-scanning all entities per page."""
    def _query():
        import time as _time
        now = _time.time()
        if _media_cache["data"] is None or (now - _media_cache["ts"]) > _MEDIA_TTL:
            entities = db.all_entities()
            _media_cache["data"] = _extract_media_items(entities)
            _media_cache["ts"] = now
        cached = _media_cache["data"]
        media_items = list(cached["items"])
        url_usage = cached["url_usage"]
        total_images = cached["total_images"]
        no_credit_count = cached["no_credit_count"]
        dup_count = cached["dup_count"]

        if filter == "missing_credit":
            media_items = [m for m in media_items if not m["credit"]]
        elif filter == "duplicate":
            dup_urls = {u for u, ids in url_usage.items() if len(ids) > 1}
            media_items = [m for m in media_items if m["url"] in dup_urls]

        total = len(media_items)
        offset = (page - 1) * limit
        page_items = media_items[offset:offset + limit]

        for item in page_items:
            usage = url_usage.get(item["url"], [])
            item["usage_count"] = len(usage)

        return {
            "items": page_items,
            "total": total,
            "page": page,
            "stats": {
                "total_images": total_images,
                "duplicates": dup_count,
                "missing_credit": no_credit_count,
            },
        }
    return await asyncio.to_thread(_query)

_media_cache: dict = {"ts": 0.0, "data": None}
_admin_volatile_caches.append(_media_cache)
_MEDIA_TTL = 120.0


def _media_parse_json_field(value, default):
    """Coerce a possibly-JSON-string field to a Python value; fall back to `default`."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return default
    return value


def _media_credits_by_url(image_credits) -> dict[str, dict]:
    credits_by_url: dict[str, dict] = {}
    if isinstance(image_credits, list):
        for credit_meta in image_credits:
            if not isinstance(credit_meta, dict):
                continue
            credit_url = credit_meta.get("url")
            if credit_url:
                credits_by_url[str(credit_url)] = credit_meta
    return credits_by_url


def _media_resolve_credit(img, credit_meta):
    """Resolve (credit, license_info) for one image from inline + registry metadata."""
    credit = ""
    license_info = ""
    if isinstance(img, dict):
        credit = img.get("credit") or img.get("author") or ""
        license_info = img.get("license", "")
    if not credit:
        credit = credit_meta.get("author") or credit_meta.get("credit") or ""
    if not license_info:
        license_info = credit_meta.get("license") or ""
    return credit, license_info


def _media_item_from_image(img, e, credits_by_url):
    """Build one media-gallery item from an image + its credit metadata; None if no URL."""
    url = img if isinstance(img, str) else img.get("url", "")
    if not url:
        return None
    credit_meta = credits_by_url.get(url, {})
    credit, license_info = _media_resolve_credit(img, credit_meta)
    return {
        "url": url,
        "entity_id": e.get("id", ""),
        "entity_name": e.get("name", ""),
        "entity_type": e.get("type", ""),
        "credit": credit,
        "license": license_info,
        "source": credit_meta.get("source") or "",
        "source_url": credit_meta.get("source_url") or "",
    }


def _extract_media_items(entities: list) -> dict:
    media_items = []
    url_usage: dict[str, list[str]] = {}
    for e in entities:
        images = _media_parse_json_field(e.get("images") or [], [])
        attrs = _media_parse_json_field(e.get("attributes") or {}, {})
        image_credits = attrs.get("image_credits") if isinstance(attrs, dict) else []
        credits_by_url = _media_credits_by_url(image_credits)
        for img in images:
            item = _media_item_from_image(img, e, credits_by_url)
            if item is None:
                continue
            media_items.append(item)
            url_usage.setdefault(item["url"], []).append(e.get("id", ""))
    return {
        "items": media_items,
        "url_usage": url_usage,
        "total_images": len(media_items),
        "no_credit_count": sum(1 for m in media_items if not m["credit"]),
        "dup_count": sum(1 for u, ids in url_usage.items() if len(ids) > 1),
    }


@router.get("/badge-counts",
            summary="Get admin dashboard badge counts",
            description="Returns lightweight counts for sidebar badges including moderation, images, unclassified entities, provisional items, and reports.")
async def badge_counts():
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
            s = kb_curation.stats()
            counts["provisional"] = s.get("pending", 0)
        except Exception:
            logger.debug("Badge kb_curation stats failed", exc_info=True)
        counts["reports"] += _count_open_info_reports()
        _badge_cache["data"] = counts
        _badge_cache["ts"] = now
        return counts
    return await asyncio.to_thread(_query)


@router.get("/dashboard-alerts",
            summary="Get dashboard alert notifications",
            description="Returns priority-sorted alerts for the admin dashboard. Scans moderation, reports, images, unclassified entities, provisional items, and appeals queues.")
async def dashboard_alerts():
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
        return {"alerts": alerts[:5]}
    return await asyncio.to_thread(_query)


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
        s = kb_curation.stats()
        prov = s.get("pending", 0)
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

@router.get("/provisional",
            summary="List provisional entities",
            description="Returns auto-learned entities pending verification, along with queue statistics.")
async def list_provisional_entities():
    """Liệt kê các entity tự học CHƯA kiểm chứng (chờ duyệt)."""
    def _query():
        import kb_curation
        return {"provisional": kb_curation.list_provisional(), **kb_curation.stats()}
    return await asyncio.to_thread(_query)


@router.post("/provisional/{entity_id}/approve",
             summary="Approve provisional entity",
             description="Promotes a provisional auto-learned entity to verified status in the knowledge base.")
async def approve_provisional(entity_id: str):
    """Duyệt 1 entity provisional → verified (tin cậy)."""
    validate_path_id(entity_id, "entity_id")
    def _query():
        import kb_curation
        result = kb_curation.promote(entity_id)
        if not result.get("ok"):
            raise HTTPException(404 if result.get("error") == "not found" else 400, result.get("error", "failed"))
        return result
    return await asyncio.to_thread(_query)


@router.post("/provisional/{entity_id}/reject",
             summary="Reject provisional entity",
             description="Rejects and removes a provisional auto-learned entity from the knowledge base.")
async def reject_provisional(entity_id: str):
    """Từ chối + xóa 1 entity provisional khỏi KB."""
    validate_path_id(entity_id, "entity_id")
    def _query():
        import kb_curation
        result = kb_curation.reject(entity_id)
        if not result.get("ok"):
            raise HTTPException(404 if result.get("error") == "not found" else 400, result.get("error", "failed"))
        return result
    return await asyncio.to_thread(_query)


@router.post("/export",
             summary="Export entity data",
             description="Exports all entities, relationships, and itineraries as a streaming JSON file to avoid memory issues.")
async def export_data():
    """Export toàn bộ entities từ DB — streaming JSON để không OOM."""

    def _generate():
        yield '{"entities":['
        entities = db.all_entities()
        for i, e in enumerate(entities):
            if i:
                yield ","
            yield json.dumps(e, ensure_ascii=False, default=str)
        yield '],"relationships":['
        with db._conn() as conn:
            rels = db._fetchall(conn, "SELECT from_id, to_id, type FROM relationships", ())
        for i, r in enumerate(rels):
            if i:
                yield ","
            yield json.dumps(db._row_to_dict(r), ensure_ascii=False, default=str)
        yield '],"itineraries":['
        with db._conn() as conn:
            itins = db._fetchall(conn, "SELECT * FROM itineraries", ())
        for i, it in enumerate(itins):
            if i:
                yield ","
            yield json.dumps(db._row_to_dict(it), ensure_ascii=False, default=str)  # default=str: TIMESTAMPTZ (datetime) trên PG
        yield ']}'

    return StreamingResponse(_generate(), media_type="application/json",
                             headers={"Content-Disposition": "attachment; filename=vinhlong360-export.json"})


@router.get("/export/users",
            summary="Export user data as CSV",
            description="Exports all users with stats (post count, follower count, reputation) as a downloadable CSV file. Phone numbers are masked.")
async def export_users_csv():
    """CSV export of all users with stats."""
    require_pg()

    def _generate():
        with db._conn() as conn:
            rows = db._fetchall(conn, """
                SELECT u.id, u.phone, u.display_name, u.role, u.is_active,
                       u.reputation, u.created_at,
                       COALESCE(pc.post_count, 0) AS post_count,
                       COALESCE(fc.follower_count, 0) AS follower_count
                FROM users u
                LEFT JOIN (
                    SELECT user_id, COUNT(*) AS post_count FROM posts
                    WHERE moderation_status != 'rejected'
                    GROUP BY user_id
                ) pc ON pc.user_id = u.id
                LEFT JOIN (
                    SELECT target_id, COUNT(*) AS follower_count FROM follows
                    WHERE target_type = 'user'
                    GROUP BY target_id
                ) fc ON fc.target_id = u.id::text
                ORDER BY u.created_at DESC
                LIMIT 50000
            """, ())
        yield "id,phone,display_name,role,is_active,reputation,created_at,post_count,follower_count\n"
        for r in rows:
            d = db._row_to_dict(r)
            phone = _mask(d.get("phone") or "")
            name = (d.get("display_name") or "").replace(",", " ").replace('"', "'")
            yield (f'{d["id"]},{phone},"{name}",{d.get("role","user")},'
                   f'{d.get("is_active",True)},{d.get("reputation",0)},'
                   f'{d.get("created_at","")},{d["post_count"]},{d["follower_count"]}\n')

    return StreamingResponse(_generate(), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=users.csv"})


@router.get("/export/posts",
            summary="Export post data as CSV",
            description="Exports posts with author and entity info as a downloadable CSV. Supports filtering by moderation status and date range.")
async def export_posts_csv(
    status: str = Query("all", max_length=20),
    days: int = Query(90, ge=1, le=365),
):
    """CSV export of posts with author/entity info."""
    require_pg()
    ph = db._ph

    def _generate():
        where_parts = []
        params = []
        if status != "all":
            where_parts.append(f"p.moderation_status = {ph}")
            params.append(status)
        where_parts.append(f"p.created_at > NOW() - CAST({ph} AS INTERVAL)")
        params.append(f"{days} days")
        where_clause = " AND ".join(where_parts) if where_parts else "TRUE"
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT p.id, p.user_id, p.post_type, p.rating,
                       p.like_count, p.comment_count, p.share_count,
                       p.moderation_status, p.entity_id, p.created_at,
                       u.display_name AS author_name
                FROM posts p
                LEFT JOIN users u ON u.id = p.user_id
                WHERE {where_clause}
                ORDER BY p.created_at DESC
                LIMIT 50000
            """, tuple(params))
        yield "id,user_id,author_name,post_type,rating,like_count,comment_count,share_count,status,entity_id,created_at\n"
        for r in rows:
            d = db._row_to_dict(r)
            name = (d.get("author_name") or "").replace(",", " ").replace('"', "'")
            yield (f'{d["id"]},{d.get("user_id","")},"{name}",'
                   f'{d.get("post_type","")},{d.get("rating","")},{d.get("like_count",0)},'
                   f'{d.get("comment_count",0)},{d.get("share_count",0)},'
                   f'{d.get("moderation_status","")},{d.get("entity_id","")},{d.get("created_at","")}\n')

    return StreamingResponse(_generate(), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=posts.csv"})


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


# ═══════════════════════════════════════════════════════
# Moderation & Community Admin
# ═══════════════════════════════════════════════════════


@router.get("/moderation/queue",
            summary="Get moderation queue",
            description="Returns posts pending moderation review. Supports filtering by status and pagination.")
async def moderation_queue(
    status: str = Query("review", pattern="^(review|pending|flagged|approved|rejected)$"),
    page: int = Query(1, ge=1, le=1000),
    limit: int = Query(20, ge=1, le=100),
):
    require_pg()
    ph = db._ph
    offset = (page - 1) * limit
    statuses = ["pending", "flagged"] if status == "review" else [status]
    placeholders = ", ".join([ph] * len(statuses))
    def _query():
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT p.*, u.display_name,
                       e.name as entity_name
                FROM posts p
                JOIN users u ON u.id = p.user_id
                LEFT JOIN entities e ON e.id = p.entity_id
                WHERE p.moderation_status IN ({placeholders})
                ORDER BY p.created_at DESC
                LIMIT {ph} OFFSET {ph}
            """, (*statuses, limit, offset))
            total = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM posts WHERE moderation_status IN ({placeholders})
            """, (*statuses,))
        return {
            "posts": [_mod_post(db._row_to_dict(r)) for r in rows],
            "total": db._row_to_dict(total)["c"] if total else 0,
            "page": page,
        }
    return await asyncio.to_thread(_query)


@router.post("/moderation/{post_id}/approve",
             summary="Approve moderated post",
             description="Approves a post pending moderation and notifies the author.")
async def approve_post(post_id: str):
    require_pg()
    post_id = validate_path_id(post_id, "post_id")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            row = db._fetchone(conn, f"""
                UPDATE posts SET moderation_status = 'approved' WHERE id::text = {ph}
                RETURNING user_id
            """, (post_id,))
            if not row:
                raise HTTPException(404, "Bài viết không tồn tại")
            author_id = str(db._row_to_dict(row)["user_id"])
        _log_mod_action("post", post_id, "approved")
        try:
            create_notification(author_id, "moderation",
                                "Bài viết của bạn đã được duyệt",
                                ref_type="post", ref_id=post_id)
        except Exception:
            logger.exception("Failed to notify post approval %s", post_id)
    await asyncio.to_thread(_query)
    return {"success": True}


class RejectBody(BaseModel):
    reason: str | None = Field(None, max_length=500)


@router.post("/moderation/{post_id}/reject",
             summary="Reject moderated post",
             description="Rejects a post pending moderation with an optional reason. Notifies the author.")
async def reject_post(post_id: str, body: RejectBody = RejectBody()):
    require_pg()
    post_id = validate_path_id(post_id, "post_id")
    reason = (body.reason or "").strip() or None
    def _query():
        ph = db._ph
        with db._conn() as conn:
            row = db._fetchone(conn, f"""
                UPDATE posts SET moderation_status = 'rejected' WHERE id::text = {ph}
                RETURNING user_id
            """, (post_id,))
            if not row:
                raise HTTPException(404, "Bài viết không tồn tại")
            author_id = str(db._row_to_dict(row)["user_id"])
        _log_mod_action("post", post_id, "rejected", reason)
        try:
            notif_body = f"Lý do: {reason}" if reason else None
            create_notification(author_id, "moderation",
                                "Bài viết của bạn đã bị từ chối",
                                body=notif_body,
                                ref_type="post", ref_id=post_id)
        except Exception:
            logger.exception("Failed to notify post rejection %s", post_id)
    await asyncio.to_thread(_query)
    return {"success": True}


class BatchModerationBody(BaseModel):
    post_ids: list[str] = Field(..., min_length=1, max_length=100)
    action: str = Field(..., max_length=20)  # 'approve' or 'reject'
    reason: str = Field("", max_length=500)


@router.post("/moderation/batch",
             summary="Batch moderate multiple posts",
             description="Approve or reject multiple posts at once. Notifies each author and logs moderation actions.")
def _batch_mod_notify(rows, status, reason) -> None:
    """Notify each affected post author of the batch moderation result."""
    if status == "approved":
        title = "Bài viết của bạn đã được duyệt"
        notif_body = None
    else:
        title = "Bài viết của bạn đã bị từ chối"
        notif_body = f"Lý do: {reason}" if reason else None
    for r in rows:
        rd = db._row_to_dict(r)
        try:
            create_notification(str(rd["user_id"]), "moderation", title,
                                body=notif_body,
                                ref_type="post", ref_id=str(rd["id"]))
        except Exception:
            logger.exception("Failed to notify batch moderation %s", rd["id"])


async def batch_moderation(body: BatchModerationBody, request: Request):
    require_pg()
    from ratelimit import check_rate
    admin_user = getattr(request.state, "admin_user", None)
    rl_key = f"admin:batch-mod:{admin_user['id']}" if admin_user else "admin:batch-mod:key"
    check_rate(rl_key, 10, 60, "Thao tác quá nhanh")
    if body.action not in ("approve", "reject"):
        raise HTTPException(400, "action must be 'approve' or 'reject'")
    if body.action == "reject" and not body.reason.strip():
        raise HTTPException(400, "reason is required when rejecting posts")
    if not body.post_ids or len(body.post_ids) > 100:
        raise HTTPException(400, "post_ids: 1-100 items")
    status = "approved" if body.action == "approve" else "rejected"
    reason = body.reason.strip() or None
    def _query():
        ph = db._ph
        placeholders = ", ".join(ph for _ in body.post_ids)
        params = [status] + list(body.post_ids)
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                UPDATE posts SET moderation_status = {ph}
                WHERE id::text IN ({placeholders})
                RETURNING id, user_id
            """, tuple(params))
            updated = len(rows)
        for pid in body.post_ids:
            _log_mod_action("post", pid, status, reason)
        _batch_mod_notify(rows, status, reason)
        return updated
    updated = await asyncio.to_thread(_query)
    return {"success": True, "updated": updated, "requested": len(body.post_ids)}


@router.get("/moderation/{post_id}/history",
            summary="Get post moderation history",
            description="Returns the full moderation action timeline for a specific post, including moderator names and scores.")
async def moderation_history(post_id: str):
    """Admin: view full moderation action timeline for a specific post."""
    require_pg()
    post_id = validate_path_id(post_id, "post_id")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            post = db._fetchone(conn, f"""
                SELECT id, moderation_status, created_at FROM posts WHERE id::text = {ph}
            """, (post_id,))
            if not post:
                raise HTTPException(404, "Bài viết không tồn tại")
            rows = db._fetchall(conn, f"""
                SELECT ml.action, ml.reason, ml.auto, ml.scores, ml.created_at,
                       u.display_name AS moderator_name
                FROM moderation_log ml
                LEFT JOIN users u ON u.id = ml.moderator_id
                WHERE ml.target_type = 'post' AND ml.target_id = {ph}
                ORDER BY ml.created_at DESC
                LIMIT 50
            """, (post_id,))
        pd = db._row_to_dict(post)
        actions = []
        for r in rows:
            d = db._row_to_dict(r)
            scores = d.get("scores")
            if isinstance(scores, str):
                try:
                    scores = json.loads(scores)
                except (json.JSONDecodeError, ValueError, TypeError):
                    scores = {}
            actions.append({
                "action": d["action"],
                "reason": d.get("reason"),
                "auto": bool(d.get("auto")),
                "moderator": d.get("moderator_name"),
                "scores": scores or {},
                "created_at": str(d.get("created_at", "")),
            })
        return {
            "post_id": post_id,
            "current_status": pd.get("moderation_status"),
            "post_created_at": str(pd.get("created_at", "")),
            "actions": actions,
            "total": len(actions),
        }
    return await asyncio.to_thread(_query)


@router.post("/posts/{post_id}/feature",
             summary="Toggle post featured status",
             description="Toggles whether a post is featured at the top of its entity page. Logs the action.")
async def feature_post(post_id: str, request: Request):
    """Admin: toggle feature a post at the top of its entity page."""
    require_pg()
    post_id = validate_path_id(post_id, "post_id")
    admin_id = _require_admin_actor_id(request)

    def _query():
        ph = db._ph
        with db._conn() as conn:
            row = db._fetchone(conn, f"SELECT id, entity_id, is_featured FROM posts WHERE id::text = {ph}", (post_id,))
            if not row:
                raise HTTPException(404, "Bài viết không tồn tại")
            rd = db._row_to_dict(row)
            if not rd.get("entity_id"):
                raise HTTPException(400, "Bài viết không thuộc entity nào")
            if rd.get("is_featured"):
                db._execute(conn, f"""
                    UPDATE posts SET is_featured = FALSE, featured_by = NULL, featured_at = NULL
                    WHERE id::text = {ph}
                """, (post_id,))
                return False
            db._execute(conn, f"""
                UPDATE posts SET is_featured = TRUE, featured_by = {ph}::uuid, featured_at = NOW()
                WHERE id::text = {ph}
            """, (admin_id, post_id))
            return True

    featured = await asyncio.to_thread(_query)
    _log_mod_action("post", post_id, "featured" if featured else "unfeatured", None)
    return {"featured": featured}



@router.delete("/posts/{post_id}/response",
               summary="Delete admin response",
               description="Deletes the admin review response for a post. Logs the deletion.")
async def delete_review_response(post_id: str):
    post_id = validate_path_id(post_id, "post_id")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            row = db._fetchone(conn, f"""
                DELETE FROM review_responses WHERE post_id::text = {ph} RETURNING id
            """, (post_id,))
            if not row:
                raise HTTPException(404, "Không có phản hồi để xoá")
    await asyncio.to_thread(_query)
    _log_mod_action("review_response", post_id, "deleted")
    return {"success": True}


class ModNoteBody(BaseModel):
    note: str = Field(..., min_length=1, max_length=500)


@router.post("/moderation/{post_id}/note",
             summary="Add moderation note",
             description="Adds an internal admin note to a post. Notes are not visible to the post author.")
async def add_moderation_note(post_id: str, body: ModNoteBody):
    """B3d: Add internal admin note (not visible to poster)."""
    require_pg()
    post_id = validate_path_id(post_id, "post_id")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            post = db._fetchone(conn, f"SELECT id FROM posts WHERE id::text = {ph}", (post_id,))
            if not post:
                raise HTTPException(404, "Bài viết không tồn tại")
            db._execute(conn, f"""
                UPDATE posts SET moderation_notes = COALESCE(moderation_notes, '[]'::jsonb) || {ph}::jsonb
                WHERE id::text = {ph}
            """, (json.dumps({"text": body.note, "at": datetime.now(timezone.utc).isoformat()}), post_id))
    await asyncio.to_thread(_query)
    _log_mod_action("post", post_id, "note_added")
    return {"success": True}


@router.get("/moderation/{post_id}/notes",
            summary="Get moderation notes",
            description="Returns all internal admin notes for a specific post.")
async def get_moderation_notes(post_id: str):
    require_pg()
    post_id = validate_path_id(post_id, "post_id")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            row = db._fetchone(conn, f"SELECT moderation_notes FROM posts WHERE id::text = {ph}", (post_id,))
        if not row:
            raise HTTPException(404, "Bài viết không tồn tại")
        notes = db._row_to_dict(row).get("moderation_notes") or []
        return {"notes": notes}
    return await asyncio.to_thread(_query)


@router.get("/moderation/stats",
            summary="Get moderation statistics",
            description="Returns post counts grouped by moderation status, plus totals for today and this week.")
async def moderation_stats():
    require_pg()
    def _query():
        with db._conn() as conn:
            rows = db._fetchall(conn, """
                SELECT moderation_status, COUNT(*) as c FROM posts GROUP BY moderation_status
            """, ())
            today = db._fetchone(conn, """
                SELECT COUNT(*) as c FROM posts WHERE created_at > NOW() - INTERVAL '24 hours'
            """, ())
            week = db._fetchone(conn, """
                SELECT COUNT(*) as c FROM posts WHERE created_at > NOW() - INTERVAL '7 days'
            """, ())
        return {
            "counts": {db._row_to_dict(row)["moderation_status"]: db._row_to_dict(row)["c"] for row in rows},
            "today": db._row_to_dict(today)["c"] if today else 0,
            "week": db._row_to_dict(week)["c"] if week else 0,
        }
    return await asyncio.to_thread(_query)


# ── Admin Content Search ──────────────────────────────────────────────────

@router.get("/content/search",
            summary="Search across all content",
            description="Admin keyword search across posts and comments. Supports filtering by content type, moderation status, and post type.")
async def admin_content_search(
    q: str = Query(..., min_length=1, max_length=200),
    content_type: str = Query("post", pattern="^(post|comment|all)$"),
    status: str = Query("all", pattern="^(all|approved|pending|rejected|flagged)$"),
    post_type: str = Query(None, pattern="^(review|question|tip|photo|general)$"),
    page: int = Query(1, ge=1, le=1000),
    limit: int = Query(20, ge=1, le=100),
):
    """Admin search across posts and comments by keyword."""
    require_pg()
    ph = db._ph
    offset = (page - 1) * limit
    search_esc = _escape_like(q)

    def _query():
        results = []
        total = 0
        with db._conn() as conn:
            if content_type in ("post", "all"):
                conditions = [f"(p.content ILIKE {ph} ESCAPE '\\' OR p.title ILIKE {ph} ESCAPE '\\')"]
                params = [f"%{search_esc}%", f"%{search_esc}%"]
                if status != "all":
                    conditions.append(f"p.moderation_status = {ph}")
                    params.append(status)
                if post_type:
                    conditions.append(f"p.post_type = {ph}")
                    params.append(post_type)
                where = " AND ".join(conditions)
                post_rows = db._fetchall(conn, f"""
                    SELECT p.id, p.title, p.content, p.post_type, p.moderation_status,
                           p.entity_id, p.created_at, p.like_count,
                           u.display_name as author_name
                    FROM posts p JOIN users u ON u.id = p.user_id
                    WHERE {where}
                    ORDER BY p.created_at DESC
                    LIMIT {ph} OFFSET {ph}
                """, tuple(params + [limit, offset]))
                post_count = db._fetchone(conn, f"SELECT COUNT(*) as c FROM posts p WHERE {where}", tuple(params))
                for r in post_rows:
                    d = db._row_to_dict(r)
                    d["_type"] = "post"
                    if d.get("content"):
                        d["content"] = d["content"][:300]
                    results.append(d)
                total += db._row_to_dict(post_count)["c"] if post_count else 0

            if content_type in ("comment", "all"):
                c_conditions = [f"c.content ILIKE {ph} ESCAPE '\\'"]
                c_params = [f"%{search_esc}%"]
                c_where = " AND ".join(c_conditions)
                comment_rows = db._fetchall(conn, f"""
                    SELECT c.id, c.content, c.post_id, c.created_at,
                           u.display_name as author_name
                    FROM comments c JOIN users u ON u.id = c.user_id
                    WHERE {c_where}
                    ORDER BY c.created_at DESC
                    LIMIT {ph} OFFSET {ph}
                """, tuple(c_params + [limit, offset]))
                comment_count = db._fetchone(conn, f"SELECT COUNT(*) as c FROM comments c WHERE {c_where}", tuple(c_params))
                for r in comment_rows:
                    d = db._row_to_dict(r)
                    d["_type"] = "comment"
                    if d.get("content"):
                        d["content"] = d["content"][:300]
                    results.append(d)
                total += db._row_to_dict(comment_count)["c"] if comment_count else 0
        return {"results": results, "total": total, "query": q, "page": page}

    return await asyncio.to_thread(_query)


# ── Admin Post Detail ────────────────────────────────────────────────────

@router.get("/posts/{post_id}",
            summary="Get post details (admin view)",
            description="Returns full post details including comments, author info, and moderation data for admin review.")
async def admin_post_detail(post_id: str):
    """Full post detail with comments for admin review."""
    require_pg()
    post_id = validate_path_id(post_id, "post_id")
    ph = db._ph

    def _query():
        with db._conn() as conn:
            post = db._fetchone(conn, f"""
                SELECT p.*, u.display_name as author_name, u.phone as author_phone,
                       u.avatar_url as author_avatar, u.role as author_role
                FROM posts p JOIN users u ON u.id = p.user_id
                WHERE p.id::text = {ph}
            """, (post_id,))
            if not post:
                raise HTTPException(404, "Bài viết không tồn tại")
            pd = db._row_to_dict(post)
            pd["author_phone"] = _mask(pd.get("author_phone", ""))

            comments = db._fetchall(conn, f"""
                SELECT c.id, c.content, c.created_at, c.parent_id,
                       u.display_name as author_name, u.id as user_id
                FROM comments c JOIN users u ON u.id = c.user_id
                WHERE c.post_id::text = {ph}
                ORDER BY c.created_at ASC
                LIMIT 100
            """, (post_id,))

            likes = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM likes WHERE post_id::text = {ph}
            """, (post_id,))

            reports = db._fetchall(conn, f"""
                SELECT r.id, r.reason, r.created_at, u.display_name as reporter_name
                FROM reports r JOIN users u ON u.id = r.reporter_id
                WHERE r.target_type = 'post' AND r.target_id = {ph}
                ORDER BY r.created_at DESC
            """, (post_id,))

        pd["comments"] = [db._row_to_dict(c) for c in comments]
        pd["comment_count"] = len(pd["comments"])
        pd["like_count_verified"] = db._row_to_dict(likes)["c"] if likes else 0
        pd["reports"] = [db._row_to_dict(r) for r in reports]
        pd["report_count"] = len(pd["reports"])
        return pd

    return await asyncio.to_thread(_query)


# ── Appeal management (NĐ147 compliance) ──

@router.get("/appeals",
            summary="List user appeals",
            description="Returns a paginated list of user appeals against moderation decisions. Supports filtering by status.")
async def list_appeals(
    status: str = Query("pending", pattern="^(pending|approved|rejected|all)$"),
    page: int = Query(1, ge=1, le=1000),
    limit: int = Query(20, ge=1, le=100),
):
    require_pg()
    ph = db._ph
    offset = (page - 1) * limit
    def _query():
        with db._conn() as conn:
            where = "" if status == "all" else f"WHERE a.status = {ph}"
            params = [] if status == "all" else [status]
            rows = db._fetchall(conn, f"""
                SELECT a.*, u.display_name, u.username,
                       p.content AS post_content, p.post_type
                FROM moderation_appeals a
                JOIN users u ON u.id = a.user_id
                JOIN posts p ON p.id = a.post_id
                {where}
                ORDER BY a.created_at DESC
                LIMIT {ph} OFFSET {ph}
            """, (*params, limit, offset))
            total = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM moderation_appeals a {where}
            """, tuple(params))
        return {
            "appeals": [{
                "id": str(db._row_to_dict(r)["id"]),
                "post_id": str(db._row_to_dict(r)["post_id"]),
                "post_content": db._row_to_dict(r).get("post_content", "")[:200],
                "post_type": db._row_to_dict(r).get("post_type"),
                "user": {"display_name": db._row_to_dict(r).get("display_name"),
                         "username": db._row_to_dict(r).get("username")},
                "reason": db._row_to_dict(r).get("reason"),
                "status": db._row_to_dict(r)["status"],
                "reviewer_note": db._row_to_dict(r).get("reviewer_note"),
                "reviewed_at": str(db._row_to_dict(r)["reviewed_at"]) if db._row_to_dict(r).get("reviewed_at") else None,
                "created_at": str(db._row_to_dict(r)["created_at"]),
            } for r in rows],
            "total": db._row_to_dict(total)["c"] if total else 0,
            "page": page,
        }
    return await asyncio.to_thread(_query)


class AppealDecisionBody(BaseModel):
    note: str = Field("", max_length=500)


@router.post("/appeals/{appeal_id}/approve",
              summary="Approve a user appeal",
              description="Approves a moderation appeal, restoring the post and notifying the user.")
async def approve_appeal(appeal_id: str, body: AppealDecisionBody = AppealDecisionBody(), request: Request = None):
    require_pg()
    appeal_id = validate_path_id(appeal_id, "appeal_id")
    admin_id = _require_admin_actor_id(request)
    def _query():
        ph = db._ph
        with db._conn() as conn:
            row = db._fetchone(conn, f"""
                SELECT post_id, user_id, status FROM moderation_appeals WHERE id::text = {ph}
            """, (appeal_id,))
            if not row:
                raise HTTPException(404, "Khiếu nại không tồn tại")
            rd = db._row_to_dict(row)
            if rd["status"] != "pending":
                raise HTTPException(400, f"Khiếu nại đã {rd['status']}")
            db._execute(conn, f"""
                UPDATE moderation_appeals
                SET status = 'approved', reviewer_note = {ph},
                    reviewer_id = {ph}::uuid, reviewed_at = NOW()
                WHERE id::text = {ph}
            """, (body.note.strip() or None, admin_id, appeal_id))
            db._execute(conn, f"""
                UPDATE posts SET moderation_status = 'approved' WHERE id::text = {ph}
            """, (str(rd["post_id"]),))
        _log_mod_action("appeal", appeal_id, "approved", body.note.strip() or None)
        try:
            create_notification(str(rd["user_id"]), "moderation",
                                "Khiếu nại được chấp nhận — bài viết đã được duyệt lại",
                                ref_type="post", ref_id=str(rd["post_id"]))
        except Exception:
            logger.exception("Failed to notify appeal approval %s", appeal_id)
    await asyncio.to_thread(_query)
    return {"success": True}


@router.post("/appeals/{appeal_id}/reject",
              summary="Reject a user appeal",
              description="Rejects a moderation appeal and notifies the user with an optional reason.")
async def reject_appeal(appeal_id: str, body: AppealDecisionBody = AppealDecisionBody(), request: Request = None):
    require_pg()
    appeal_id = validate_path_id(appeal_id, "appeal_id")
    admin_id = _require_admin_actor_id(request)
    def _query():
        ph = db._ph
        with db._conn() as conn:
            row = db._fetchone(conn, f"""
                SELECT post_id, user_id, status FROM moderation_appeals WHERE id::text = {ph}
            """, (appeal_id,))
            if not row:
                raise HTTPException(404, "Khiếu nại không tồn tại")
            rd = db._row_to_dict(row)
            if rd["status"] != "pending":
                raise HTTPException(400, f"Khiếu nại đã {rd['status']}")
            db._execute(conn, f"""
                UPDATE moderation_appeals
                SET status = 'rejected', reviewer_note = {ph},
                    reviewer_id = {ph}::uuid, reviewed_at = NOW()
                WHERE id::text = {ph}
            """, (body.note.strip() or None, admin_id, appeal_id))
        _log_mod_action("appeal", appeal_id, "rejected", body.note.strip() or None)
        try:
            note_msg = f" Lý do: {body.note.strip()}" if body.note.strip() else ""
            create_notification(str(rd["user_id"]), "moderation",
                                f"Khiếu nại không được chấp nhận.{note_msg}",
                                ref_type="post", ref_id=str(rd["post_id"]))
        except Exception:
            logger.exception("Failed to notify appeal rejection %s", appeal_id)
    await asyncio.to_thread(_query)
    return {"success": True}


# ── Admin Comment List ────────────────────────────────────────────────────

@router.get("/comments",
            summary="List comments for admin review",
            description="Returns a paginated list of comments with optional search and post filter.")
async def admin_list_comments(
    search: str = Query("", max_length=200),
    post_id: str = Query(None, max_length=50),
    page: int = Query(1, ge=1, le=1000),
    limit: int = Query(20, ge=1, le=100),
):
    """List comments for admin review with optional search and post filter."""
    ph = db._ph
    offset = (page - 1) * limit

    def _query():
        conditions = []
        params = []
        if search:
            search_esc = _escape_like(search)
            conditions.append(f"c.content ILIKE {ph} ESCAPE '\\'")
            params.append(f"%{search_esc}%")
        if post_id:
            conditions.append(f"c.post_id::text = {ph}")
            params.append(post_id)
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        count_params = list(params)
        params.extend([limit, offset])
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT c.id, c.content, c.post_id, c.parent_id, c.created_at,
                       u.display_name as author_name, u.id as user_id,
                       p.title as post_title, p.post_type
                FROM comments c
                JOIN users u ON u.id = c.user_id
                JOIN posts p ON p.id = c.post_id
                {where}
                ORDER BY c.created_at DESC
                LIMIT {ph} OFFSET {ph}
            """, tuple(params))
            total = db._fetchone(conn, f"SELECT COUNT(*) as c FROM comments c {where}", tuple(count_params))
        return {
            "comments": [db._row_to_dict(r) for r in rows],
            "total": db._row_to_dict(total)["c"] if total else 0,
            "page": page,
        }

    return await asyncio.to_thread(_query)


@router.delete("/comments/{comment_id}",
               summary="Delete a comment",
               description="Force-deletes a comment by ID and recalculates the parent post comment count.")
async def admin_delete_comment(comment_id: str, request: Request):
    """Admin force-delete a comment."""
    comment_id = validate_path_id(comment_id, "comment_id")
    ph = db._ph

    def _query():
        with db._conn() as conn:
            row = db._fetchone(conn, f"""
                DELETE FROM comments WHERE id::text = {ph}
                RETURNING id, post_id, user_id
            """, (comment_id,))
            if not row:
                raise HTTPException(404, "Bình luận không tồn tại")
            rd = db._row_to_dict(row)
            db._execute(conn, f"""
                UPDATE posts
                SET comment_count = (
                    SELECT COUNT(*) FROM comments WHERE post_id = {ph}::uuid
                )
                WHERE id = {ph}::uuid
            """, (str(rd["post_id"]), str(rd["post_id"])))
        _log_mod_action("comment", comment_id, "deleted")
        return rd

    result = await asyncio.to_thread(_query)
    return {"success": True, "deleted_comment": str(result["id"])}


@router.get("/content-stats",
            summary="Get content statistics",
            description="Returns content statistics including posts by type/status, average ratings, and daily post counts for a given period.")
async def content_stats(days: int = Query(30, ge=1, le=365)):
    require_pg()
    ph = db._ph
    def _query():
        interval_param = f"{days} days"
        with db._conn() as conn:
            by_type = db._fetchall(conn, f"""
                SELECT post_type, COUNT(*) as cnt
                FROM posts
                WHERE created_at > NOW() - CAST({ph} AS INTERVAL)
                  AND moderation_status = 'approved'
                GROUP BY post_type ORDER BY cnt DESC
            """, (interval_param,))
            by_status = db._fetchall(conn, f"""
                SELECT moderation_status, COUNT(*) as cnt
                FROM posts
                WHERE created_at > NOW() - CAST({ph} AS INTERVAL)
                GROUP BY moderation_status ORDER BY cnt DESC
            """, (interval_param,))
            avg_rating = db._fetchone(conn, f"""
                SELECT AVG(rating) as avg_r, COUNT(*) as cnt
                FROM posts
                WHERE post_type = 'review' AND rating IS NOT NULL
                  AND created_at > NOW() - CAST({ph} AS INTERVAL)
                  AND moderation_status = 'approved'
            """, (interval_param,))
            total_comments = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM comments
                WHERE created_at > NOW() - CAST({ph} AS INTERVAL)
            """, (interval_param,))
            daily_posts = db._fetchall(conn, f"""
                SELECT DATE(created_at) as day, COUNT(*) as cnt
                FROM posts
                WHERE created_at > NOW() - CAST({ph} AS INTERVAL)
                  AND moderation_status = 'approved'
                GROUP BY DATE(created_at) ORDER BY day
            """, (interval_param,))
        ar = db._row_to_dict(avg_rating) if avg_rating else {}
        return {
            "period_days": days,
            "posts_by_type": {db._row_to_dict(r)["post_type"]: db._row_to_dict(r)["cnt"] for r in by_type},
            "posts_by_status": {db._row_to_dict(r)["moderation_status"]: db._row_to_dict(r)["cnt"] for r in by_status},
            "avg_review_rating": round(float(ar["avg_r"]), 2) if ar.get("avg_r") else None,
            "total_reviews_with_rating": ar.get("cnt", 0),
            "total_comments": db._row_to_dict(total_comments)["c"] if total_comments else 0,
            "daily_posts": [{"day": str(db._row_to_dict(r)["day"]), "count": db._row_to_dict(r)["cnt"]} for r in daily_posts],
        }
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


@router.get("/reports",
            summary="List user reports",
            description="Returns a paginated list of user reports with filtering by status, target type, reporter, and target user.")
async def get_reports(
    status: str = Query("pending", pattern="^(all|pending|resolved|dismissed)$"),
    target_type: str = Query(None, pattern="^(post|comment|user|entity)$"),
    reporter_id: str = Query(None, max_length=64),
    target_user_id: str = Query(None, max_length=64),
    page: int = Query(1, ge=1, le=1000),
    limit: int = Query(20, ge=1, le=500),
):
    require_pg()
    if reporter_id:
        reporter_id = validate_path_id(reporter_id, "reporter_id")
    if target_user_id:
        target_user_id = validate_path_id(target_user_id, "target_user_id")
    ph = db._ph
    offset = (page - 1) * limit
    def _query():
        with db._conn() as conn:
            conditions = []
            params = []
            if status != "all":
                conditions.append(f"r.status = {ph}")
                params.append(status)
            if target_type:
                conditions.append(f"r.target_type = {ph}")
                params.append(target_type)
            if reporter_id:
                conditions.append(f"r.reporter_id::text = {ph}")
                params.append(reporter_id)
            if target_user_id:
                conditions.append("r.target_type = 'user'")
                conditions.append(f"r.target_id = {ph}")
                params.append(target_user_id)
            where = " AND ".join(conditions) if conditions else "1=1"
            params.extend([limit, offset])
            rows = db._fetchall(conn, f"""
                SELECT r.id, r.target_type, r.target_id, r.reason, to_jsonb(r)->>'details' AS details,
                       r.reporter_id, r.status, r.created_at, u.display_name as reporter_name
                FROM reports r
                LEFT JOIN users u ON u.id = r.reporter_id
                WHERE {where}
                ORDER BY r.created_at DESC
                LIMIT {ph} OFFSET {ph}
            """, tuple(params))
            total = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM reports r WHERE {where}
            """, tuple(params[:-2]))
        return {
            "reports": [db._row_to_dict(r) for r in rows],
            "total": db._row_to_dict(total)["c"] if total else 0,
        }
    return await asyncio.to_thread(_query)


class BulkReportAction(BaseModel):
    ids: list[str] = Field(..., min_length=1, max_length=100)
    action: str = Field(..., pattern="^(resolve|dismiss)$")


@router.post("/reports/bulk",
              summary="Bulk action on reports",
              description="Applies a resolve or dismiss action to multiple reports at once.")
async def bulk_report_action(body: BulkReportAction):
    status = "resolved" if body.action == "resolve" else "dismissed"
    def _query():
        ph = db._ph
        placeholders = ",".join([ph] * len(body.ids))
        with db._conn() as conn:
            cur = db._execute(conn, f"UPDATE reports SET status = {ph} WHERE id::text IN ({placeholders})",
                              (status, *body.ids))
            return cur.rowcount
    updated = await asyncio.to_thread(_query)
    for rid in body.ids:
        _log_mod_action("report", rid, status)
    return {"success": True, "updated": updated, "requested": len(body.ids)}


@router.post("/reports/{report_id}/resolve",
              summary="Resolve a report",
              description="Marks a user report as resolved after admin review.")
async def resolve_report(report_id: str):
    report_id = validate_path_id(report_id, "report_id")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            cur = db._execute(conn, f"""
                UPDATE reports SET status = 'resolved' WHERE id::text = {ph}
            """, (report_id,))
            if cur.rowcount == 0:
                raise HTTPException(404, "Báo cáo không tồn tại")
    await asyncio.to_thread(_query)
    _log_mod_action("report", report_id, "resolved")
    return {"success": True}


@router.post("/reports/{report_id}/dismiss",
              summary="Dismiss a report",
              description="Marks a user report as dismissed, indicating no action is needed.")
async def dismiss_report(report_id: str):
    report_id = validate_path_id(report_id, "report_id")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            cur = db._execute(conn, f"""
                UPDATE reports SET status = 'dismissed' WHERE id::text = {ph}
            """, (report_id,))
            if cur.rowcount == 0:
                raise HTTPException(404, "Báo cáo không tồn tại")
    await asyncio.to_thread(_query)
    _log_mod_action("report", report_id, "dismissed")
    return {"success": True}


# GĐ13.6f: báo-sai thông tin (facility/entity) & báo nội dung ẩn danh — kênh nhẹ JSONL
# (KHÔNG cần đăng nhập, không DB), tách khỏi UGC `reports` (Postgres) ở trên.
_INFO_REPORTS_FILE = Path(__file__).resolve().parent / "data" / "reports.jsonl"
from notifications import create_notification
from public_api import _jsonl_lock as _info_reports_lock

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
    """Liệt kê báo-sai/báo cáo ẩn danh (reports.jsonl), mới nhất trước. Admin tự xử lý
    (sửa entity qua editor / takedown thủ công)."""
    def _query():
        if not _INFO_REPORTS_FILE.exists():
            return {"reports": [], "total": 0}
        items = []
        with open(_INFO_REPORTS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        items.reverse()
        open_count = sum(1 for r in items if r.get("status", "open") == "open")
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
    ts: str = Field(..., min_length=1, max_length=64)   # khóa theo timestamp ISO (ổn định)
    status: str = Field(..., pattern="^(open|resolved|dismissed)$")


@router.post("/info-reports/action",
             summary="Update information report status",
             description="Change the status of an info-correction report to open, resolved, or dismissed. Writes atomically to the JSONL store.")
async def info_report_action(body: ReportActionRequest):
    """Đổi trạng thái 1 báo-sai (resolve/dismiss/open) — ghi lại reports.jsonl atomic."""
    def _query():
        with _info_reports_lock:
            if not _INFO_REPORTS_FILE.exists():
                raise HTTPException(404, "Không có báo cáo")
            records, found = [], False
            for line in _INFO_REPORTS_FILE.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if r.get("ts") == body.ts:
                    r["status"] = body.status
                    found = True
                records.append(r)
            if not found:
                raise HTTPException(404, f"Không tìm thấy báo cáo ts={body.ts}")
            tmp = _INFO_REPORTS_FILE.with_suffix(".tmp")
            tmp.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n", encoding="utf-8")
            tmp.replace(_INFO_REPORTS_FILE)
    await asyncio.to_thread(_query)
    return {"success": True, "ts": body.ts, "new_status": body.status}


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


def _list_users_where(ph, search, role_filter):
    """Build the users WHERE clause + params for the admin list, honoring search/role filters."""
    conditions = ["1=1"]
    params = []
    if search:
        search_esc = _escape_like(search)
        conditions.append(f"(display_name ILIKE {ph} ESCAPE '\\' OR phone LIKE {ph} ESCAPE '\\')")
        params.extend([f"%{search_esc}%", f"%{search_esc}%"])
    if role_filter:
        conditions.append(f"COALESCE(role, 'user') = {ph}")
        params.append(role_filter)
    return " AND ".join(conditions), params


def _list_users_role_counts() -> dict:
    role_counts = {}
    try:
        with db._conn() as conn2:
            rc_rows = db._fetchall(conn2, "SELECT COALESCE(role, 'user') as role, COUNT(*) as c FROM users GROUP BY COALESCE(role, 'user')", ())
        for rc in rc_rows:
            d = db._row_to_dict(rc)
            role_counts[d["role"]] = d["c"]
    except Exception:
        logger.debug("Role counts query failed", exc_info=True)
    return role_counts


@router.get("/users",
            summary="List all users",
            description="Returns a paginated list of users with post counts. Supports search by name or phone, and filtering by role.")
async def list_users(
    page: int = Query(1, ge=1, le=1000),
    limit: int = Query(20, ge=1, le=100),
    search: str = Query("", max_length=100),
    role_filter: Optional[str] = Query(None, pattern="^(user|moderator|admin)$"),
    q: Optional[str] = Query(None, max_length=100),
    offset: Optional[int] = Query(None, ge=0, le=100000),
):
    require_pg()
    ph = db._ph
    if q and not search:
        search = q
    actual_offset = offset if offset is not None else (page - 1) * limit
    where, params = _list_users_where(ph, search, role_filter)
    count_params = list(params)
    params.extend([limit, actual_offset])
    def _query():
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT u.id, u.phone, u.display_name, u.role, u.is_active, u.created_at,
                       (SELECT COUNT(*) FROM posts p WHERE p.user_id = u.id AND p.moderation_status = 'approved') as post_count
                FROM users u WHERE {where}
                ORDER BY u.created_at DESC
                LIMIT {ph} OFFSET {ph}
            """, params)
            total = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM users WHERE {where}
            """, count_params)
        role_counts = _list_users_role_counts()
        return {
            "users": [{
                "id": str(r["id"]),
                "phone": _mask(r.get("phone", "")),
                "display_name": r.get("display_name", ""),
                "role": r.get("role", "user"),
                "is_active": r.get("is_active", True),
                "created_at": str(r.get("created_at", "")),
                "post_count": r.get("post_count", 0),
            } for r in [db._row_to_dict(row) for row in rows]],
            "total": db._row_to_dict(total)["c"] if total else 0,
            "page": page if offset is None else (actual_offset // limit) + 1,
            "limit": limit,
            "role_counts": role_counts,
        }
    return await asyncio.to_thread(_query)


@router.get("/users/{user_id}",
            summary="Get user details",
            description="Returns comprehensive user profile and activity statistics for the admin panel, including post counts, follow stats, reports, blocks, and reputation.")
async def admin_user_detail(user_id: str):
    """Comprehensive user detail for admin panel."""
    require_pg()
    user_id = validate_path_id(user_id, "user_id")
    ph = db._ph

    def _query():
        with db._conn() as conn:
            user = db._fetchone(conn, f"""
                SELECT id, phone, display_name, avatar_url, cover_url, bio,
                       username, role, is_active, created_at
                FROM users WHERE id::text = {ph}
            """, (user_id,))
            if not user:
                raise HTTPException(404, "Người dùng không tồn tại")
            ud = db._row_to_dict(user)
            ud["phone"] = _mask(ud.get("phone", ""))

            post_stats = db._fetchone(conn, f"""
                SELECT COUNT(*) as total,
                       COUNT(*) FILTER (WHERE moderation_status = 'approved') as approved,
                       COUNT(*) FILTER (WHERE moderation_status = 'rejected') as rejected,
                       COUNT(*) FILTER (WHERE moderation_status = 'pending') as pending,
                       COUNT(*) FILTER (WHERE post_type = 'review') as reviews,
                       COUNT(*) FILTER (WHERE post_type = 'question') as questions
                FROM posts WHERE user_id::text = {ph}
            """, (user_id,))
            ps = db._row_to_dict(post_stats) if post_stats else {}

            comment_count = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM comments WHERE user_id::text = {ph}
            """, (user_id,))

            follow_stats = db._fetchone(conn, f"""
                SELECT
                    (SELECT COUNT(*) FROM follows WHERE follower_id::text = {ph} AND target_type = 'user') as following,
                    (SELECT COUNT(*) FROM follows WHERE target_id = {ph} AND target_type = 'user') as followers
            """, (user_id, user_id))
            fs = db._row_to_dict(follow_stats) if follow_stats else {}

            session_count = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM user_sessions WHERE user_id = {ph}::uuid
            """, (user_id,))

            report_count = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM reports WHERE reporter_id::text = {ph}
            """, (user_id,))

            reported_count = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM reports WHERE target_type = 'user' AND target_id = {ph}
            """, (user_id,))

            block_count = db._fetchone(conn, f"""
                SELECT
                    (SELECT COUNT(*) FROM blocks WHERE blocker_id::text = {ph}) as blocking,
                    (SELECT COUNT(*) FROM blocks WHERE blocked_id::text = {ph}) as blocked_by
            """, (user_id, user_id))
            blk = db._row_to_dict(block_count) if block_count else {}

            mute_count = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM user_mutes WHERE user_id::text = {ph}
            """, (user_id,))

            reputation = db._fetchone(conn, f"""
                SELECT reputation_score FROM users WHERE id::text = {ph}
            """, (user_id,))
            rep = db._row_to_dict(reputation).get("reputation_score", 0) if reputation else 0

            last_login = _admin_user_last_login(conn, ph, user_id)

            last_post = db._fetchone(conn, f"""
                SELECT created_at FROM posts
                WHERE user_id::text = {ph} AND moderation_status = 'approved'
                ORDER BY created_at DESC LIMIT 1
            """, (user_id,))

        stats = _admin_user_detail_stats(
            ps, comment_count, fs, session_count, report_count, reported_count,
            blk, mute_count, rep, last_login, last_post)
        return {"user": ud, "stats": stats}

    return await asyncio.to_thread(_query)


def _admin_user_last_login(conn, ph, user_id):
    last_login = None
    try:
        ll = db._fetchone(conn, f"""
            SELECT created_at FROM login_history
            WHERE user_id = {ph}::uuid AND success = TRUE
            ORDER BY created_at DESC LIMIT 1
        """, (user_id,))
        if ll:
            last_login = str(db._row_to_dict(ll)["created_at"])
    except Exception:
        logger.debug("login_history query failed for user %s", user_id, exc_info=True)
    return last_login


def _admin_user_detail_stats(ps, comment_count, fs, session_count, report_count,
                             reported_count, blk, mute_count, rep, last_login, last_post):
    return {
        "posts": ps,
        "comments": db._row_to_dict(comment_count)["c"] if comment_count else 0,
        "following": fs.get("following", 0),
        "followers": fs.get("followers", 0),
        "active_sessions": db._row_to_dict(session_count)["c"] if session_count else 0,
        "reports_filed": db._row_to_dict(report_count)["c"] if report_count else 0,
        "reports_against": db._row_to_dict(reported_count)["c"] if reported_count else 0,
        "blocking": blk.get("blocking", 0),
        "blocked_by": blk.get("blocked_by", 0),
        "muted_users": db._row_to_dict(mute_count)["c"] if mute_count else 0,
        "reputation_score": rep,
        "last_login": last_login,
        "last_post_at": str(db._row_to_dict(last_post)["created_at"]) if last_post else None,
    }


@router.post("/users/{user_id}/ban",
             summary="Ban a user",
             description="Deactivate a user account and revoke all active sessions. Admins cannot ban themselves.")
async def ban_user(user_id: str, request: Request):
    require_pg()
    user_id = validate_path_id(user_id, "user_id")
    admin_user = await get_current_user(request)
    if admin_user and str(admin_user["id"]) == user_id:
        raise HTTPException(400, "Không thể tự ban chính mình")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            target = db._fetchone(conn, f"SELECT is_active FROM users WHERE id::text = {ph}", (user_id,))
            if not target:
                raise HTTPException(404, "Không tìm thấy người dùng")
            db._execute(conn, f"""
                UPDATE users SET is_active = FALSE WHERE id::text = {ph}
            """, (user_id,))
            db._execute(conn, f"""
                DELETE FROM user_sessions WHERE user_id = {ph}::uuid
            """, (user_id,))
    await asyncio.to_thread(_query)
    _log_mod_action("user", user_id, "ban")
    return {"success": True}


@router.post("/users/{user_id}/unban",
             summary="Unban a user",
             description="Reactivate a previously banned user account. Returns an error if the user is not currently banned.")
async def unban_user(user_id: str):
    require_pg()
    user_id = validate_path_id(user_id, "user_id")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            target = db._fetchone(conn, f"SELECT is_active FROM users WHERE id::text = {ph}", (user_id,))
            if not target:
                raise HTTPException(404, "Không tìm thấy người dùng")
            td = db._row_to_dict(target)
            if td["is_active"]:
                raise HTTPException(400, "Người dùng không bị ban")
            db._execute(conn, f"""
                UPDATE users SET is_active = TRUE WHERE id::text = {ph}
            """, (user_id,))
    await asyncio.to_thread(_query)
    _log_mod_action("user", user_id, "unban")
    return {"success": True}


class BulkUserAction(BaseModel):
    user_ids: list[str] = Field(..., min_length=1, max_length=50)
    reason: str = Field("", max_length=500)


@router.post("/users/bulk-ban",
             summary="Bulk ban users",
             description="Ban multiple users at once. Accepts a list of user IDs and an optional reason; skips non-existent users.")
async def bulk_ban_users(body: BulkUserAction, request: Request):
    require_pg()
    from ratelimit import check_rate
    check_rate("admin:bulk-ban", 5, 60, "Thao tác quá nhanh")
    admin_user = await get_current_user(request)
    admin_id = str(admin_user["id"]) if admin_user else None
    ids = [validate_path_id(uid, "user_id") for uid in body.user_ids]
    if admin_id and admin_id in ids:
        raise HTTPException(400, "Không thể tự ban chính mình")
    def _query():
        ph = db._ph
        banned = []
        with db._conn() as conn:
            for uid in ids:
                target = db._fetchone(conn, f"SELECT is_active FROM users WHERE id::text = {ph}", (uid,))
                if not target:
                    continue
                db._execute(conn, f"UPDATE users SET is_active = FALSE WHERE id::text = {ph}", (uid,))
                db._execute(conn, f"DELETE FROM user_sessions WHERE user_id = {ph}::uuid", (uid,))
                banned.append(uid)
        return banned
    banned = await asyncio.to_thread(_query)
    for uid in banned:
        _log_mod_action("user", uid, "ban", body.reason or None)
    return {"success": True, "banned_count": len(banned), "banned_ids": banned}


@router.post("/users/bulk-unban",
             summary="Bulk unban users",
             description="Unban multiple users at once. Accepts a list of user IDs and an optional reason; skips non-existent or active users.")
async def bulk_unban_users(body: BulkUserAction):
    require_pg()
    from ratelimit import check_rate
    check_rate("admin:bulk-unban", 5, 60, "Thao tác quá nhanh")
    ids = [validate_path_id(uid, "user_id") for uid in body.user_ids]
    def _query():
        ph = db._ph
        unbanned = []
        with db._conn() as conn:
            for uid in ids:
                target = db._fetchone(conn, f"SELECT is_active FROM users WHERE id::text = {ph}", (uid,))
                if not target:
                    continue
                td = db._row_to_dict(target)
                if td["is_active"]:
                    continue
                db._execute(conn, f"UPDATE users SET is_active = TRUE WHERE id::text = {ph}", (uid,))
                unbanned.append(uid)
        return unbanned
    unbanned = await asyncio.to_thread(_query)
    for uid in unbanned:
        _log_mod_action("user", uid, "unban", body.reason or None)
    return {"success": True, "unbanned_count": len(unbanned), "unbanned_ids": unbanned}


def _assert_role_change_allowed(admin_user, admin_role, role, target_role) -> None:
    """Privilege-boundary guard: only superadmin/admin-key may grant/change the admin role."""
    if admin_user and admin_role != "superadmin":
        if role == "admin" and target_role != "admin":
            raise HTTPException(403, "Chỉ superadmin hoặc admin key mới được cấp quyền admin")
        if target_role == "admin" and role != "admin":
            raise HTTPException(403, "Chỉ superadmin hoặc admin key mới được đổi quyền admin khác")


def _assert_not_last_admin(conn, ph, user_id, role, target_role) -> None:
    """Prevent demoting the last remaining active admin."""
    if target_role == "admin" and role != "admin":
        remaining = db._fetchone(conn, f"""
            SELECT COUNT(*) as c FROM users
            WHERE COALESCE(role, 'user') = 'admin'
              AND is_active = TRUE
              AND id::text <> {ph}
        """, (user_id,))
        remaining_count = db._row_to_dict(remaining)["c"] if remaining else 0
        if remaining_count <= 0:
            raise HTTPException(400, "Không thể hạ quyền admin cuối cùng")


@router.post("/users/{user_id}/role",
             summary="Set user role",
             description="Assign a role (user, moderator, or admin) to a user. Banned users cannot be assigned roles.")
async def set_user_role(request: Request, user_id: str, role: str = Query(..., pattern="^(user|moderator|admin)$")):
    require_pg()
    _ensure_admin_scope(request, "security.admin")
    user_id = validate_path_id(user_id, "user_id")
    admin_user = getattr(request.state, "admin_user", None)
    if admin_user and str(admin_user.get("id")) == user_id:
        raise HTTPException(400, "Không thể tự đổi role chính mình")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            target = db._fetchone(conn, f"SELECT id, is_active, role FROM users WHERE id::text = {ph}", (user_id,))
            if not target:
                raise HTTPException(404, "Không tìm thấy người dùng")
            td = db._row_to_dict(target)
            if not td["is_active"]:
                raise HTTPException(400, "Không thể gán quyền cho tài khoản đã bị ban")
            target_role = td.get("role") or "user"
            admin_role = (admin_user or {}).get("role") if admin_user else "admin-key"
            _assert_role_change_allowed(admin_user, admin_role, role, target_role)
            _assert_not_last_admin(conn, ph, user_id, role, target_role)
            db._execute(conn, f"""
                UPDATE users SET role = {ph} WHERE id::text = {ph}
            """, (role, user_id))
    await asyncio.to_thread(_query)
    _log_mod_action("user", user_id, f"set_role:{role}")
    return {"success": True}


class AdminUserNote(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


@router.post("/users/{user_id}/notes", status_code=201,
             summary="Add admin note to user",
             description="Create an internal admin note attached to a user profile. Notes are only visible to admins.")
async def add_user_note(user_id: str, body: AdminUserNote, request: Request):
    """Admin: add internal note to a user profile."""
    user_id = validate_path_id(user_id, "user_id")
    admin_id = _require_admin_actor_id(request)

    def _query():
        ph = db._ph
        with db._conn() as conn:
            row = db._fetchone(conn, f"SELECT id FROM users WHERE id::text = {ph}", (user_id,))
            if not row:
                raise HTTPException(404, "Người dùng không tồn tại")
            note = db._fetchone(conn, f"""
                INSERT INTO admin_user_notes (user_id, admin_id, content)
                VALUES ({ph}::uuid, {ph}::uuid, {ph}) RETURNING id, created_at
            """, (user_id, admin_id, body.content.strip()))
            return db._row_to_dict(note)

    result = await asyncio.to_thread(_query)
    return {"note": {"id": str(result["id"]), "created_at": str(result["created_at"])}}


@router.get("/users/{user_id}/notes",
            summary="List admin notes for user",
            description="Retrieve all internal admin notes for a user, ordered by most recent first.")
async def get_user_notes(user_id: str, limit: int = Query(50, ge=1, le=200)):
    """Admin: list internal notes for a user."""
    user_id = validate_path_id(user_id, "user_id")

    def _query():
        ph = db._ph
        with db._conn() as conn:
            return db._fetchall(conn, f"""
                SELECT n.id, n.content, n.created_at, u.display_name as admin_name
                FROM admin_user_notes n JOIN users u ON u.id = n.admin_id
                WHERE n.user_id = {ph}::uuid ORDER BY n.created_at DESC LIMIT {ph}
            """, (user_id, limit))

    rows = await asyncio.to_thread(_query)
    notes = []
    for r in rows:
        d = db._row_to_dict(r)
        notes.append({"id": str(d["id"]), "content": d["content"],
                       "admin_name": d.get("admin_name"), "created_at": str(d["created_at"])})
    return {"notes": notes}


@router.delete("/users/{user_id}/notes/{note_id}",
               summary="Delete admin note",
               description="Delete a specific internal admin note from a user profile.")
async def delete_user_note(user_id: str, note_id: str):
    """Admin: delete an internal note."""
    user_id = validate_path_id(user_id, "user_id")
    note_id = validate_path_id(note_id, "note_id")

    def _query():
        ph = db._ph
        with db._conn() as conn:
            row = db._fetchone(conn, f"DELETE FROM admin_user_notes WHERE id = {ph}::uuid AND user_id = {ph}::uuid RETURNING 1",
                               (note_id, user_id))
            if not row:
                raise HTTPException(404, "Ghi chú không tồn tại")

    await asyncio.to_thread(_query)
    return {"success": True}


# ── Admin: user mutes + reactions visibility ────────────────────────

@router.get("/users/{user_id}/mutes",
            summary="Get user mute list",
            description="List all users muted by a specific user, with display names and timestamps.")
async def admin_user_mutes(user_id: str, limit: int = Query(50, ge=1, le=200)):
    user_id = validate_path_id(user_id, "user_id")
    ph = db._ph
    def _query():
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT m.muted_id, u.display_name, u.username, m.created_at
                FROM user_mutes m JOIN users u ON u.id = m.muted_id
                WHERE m.user_id = {ph}::uuid
                ORDER BY m.created_at DESC LIMIT {ph}
            """, (user_id, limit))
            return [db._row_to_dict(r) for r in rows]
    mutes = await asyncio.to_thread(_query)
    return {"mutes": [{"muted_id": str(m["muted_id"]), "display_name": m.get("display_name"),
                        "username": m.get("username"), "created_at": str(m["created_at"])} for m in mutes],
            "total": len(mutes)}


@router.get("/users/{user_id}/reactions",
            summary="Get user reaction history",
            description="Retrieve a summary of reaction types and recent reactions made by a user.")
async def admin_user_reactions(user_id: str, limit: int = Query(100, ge=1, le=500)):
    user_id = validate_path_id(user_id, "user_id")
    ph = db._ph
    def _query():
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT r.reaction_type, COUNT(*) as count
                FROM post_reactions r WHERE r.user_id = {ph}::uuid
                GROUP BY r.reaction_type
            """, (user_id,))
            summary = {db._row_to_dict(r)["reaction_type"]: int(db._row_to_dict(r)["count"]) for r in rows}
            recent = db._fetchall(conn, f"""
                SELECT r.post_id, r.reaction_type, r.created_at, p.content
                FROM post_reactions r LEFT JOIN posts p ON p.id = r.post_id
                WHERE r.user_id = {ph}::uuid
                ORDER BY r.created_at DESC LIMIT {ph}
            """, (user_id, limit))
            return summary, [db._row_to_dict(r) for r in recent]
    summary, recent = await asyncio.to_thread(_query)
    return {"summary": summary, "total": sum(summary.values()),
            "recent": [{"post_id": str(r["post_id"]), "reaction_type": r["reaction_type"],
                        "created_at": str(r["created_at"]),
                        "content_preview": (r.get("content") or "")[:100]} for r in recent]}


def _mod_post(row: dict) -> dict:
    images = row.get("images", [])
    if isinstance(images, str):
        try:
            images = json.loads(images)
        except Exception:
            images = []
    return {
        "id": str(row["id"]),
        "content": row.get("content", "")[:2000],
        "post_type": row.get("post_type", "share"),
        "moderation_status": row.get("moderation_status", "pending"),
        "images": images,
        "author": row.get("display_name", ""),
        "display_name": row.get("display_name", ""),
        "phone": _mask(row.get("phone", "")),
        "entity_name": row.get("entity_name"),
        "created_at": str(row.get("created_at", "")),
        "moderation_notes": row.get("moderation_notes") or [],
    }


def _mask(phone: str) -> str:
    if not phone or len(phone) < 6:
        return phone or ""
    return phone[:3] + "****" + phone[-3:]


def _log_mod_action(target_type, target_id, action, reason=None):
    try:
        from moderation import log_moderation
        log_moderation(target_type, target_id, action, {"reason": reason} if reason else {}, auto=False)
    except Exception:
        logger.debug("Moderation log write failed", exc_info=True)


# ══════════════════════════════════════════════════
#  SITE SETTINGS — CMS admin endpoints
# ══════════════════════════════════════════════════

@router.get("/site-settings",
            summary="Get all site settings",
            description="Retrieve all site settings grouped by category for the admin overview panel.")
async def admin_get_all_settings():
    """All settings grouped by category (for admin overview)."""
    if not db._use_pg:
        raise HTTPException(503, detail="Cài đặt site yêu cầu PostgreSQL")
    return await asyncio.to_thread(site_settings.get_all_grouped)


_SETTING_KEY_RE = re.compile(r"^[a-zA-Z0-9_./:-]{1,200}$")

@router.get("/site-settings/{category}",
            summary="Get settings by category",
            description="Retrieve all site settings for a specific category, for the admin editor page.")
async def admin_get_settings_by_category(category: str):
    """Settings for a specific category (for admin editor page)."""
    if not _SETTING_KEY_RE.match(category):
        raise HTTPException(400, detail="Tên danh mục không hợp lệ")
    if not db._use_pg:
        raise HTTPException(503, detail="Cài đặt site yêu cầu PostgreSQL")
    def _query():
        items = site_settings.get_by_category(category)
        if not items:
            raise HTTPException(404, detail=f"Không tìm thấy cài đặt cho danh mục '{category}'")
        return {"category": category, "settings": items}
    return await asyncio.to_thread(_query)


class SettingUpdate(BaseModel):
    value: object = Field(..., description="New value for the setting")


@router.put("/site-settings/{key:path}",
            summary="Update a site setting",
            description="Update the value of a single site setting by its key path.")
async def admin_update_setting(key: str, body: SettingUpdate, request: Request):
    """Update a single setting value."""
    if not _SETTING_KEY_RE.match(key):
        raise HTTPException(400, detail="Tên cài đặt không hợp lệ")
    if not db._use_pg:
        raise HTTPException(503, detail="Cài đặt site yêu cầu PostgreSQL")
    actor = _admin_actor_label(request)
    def _query():
        ok = site_settings.upsert(key, body.value, actor=actor)
        if not ok:
            raise HTTPException(404, detail="Không tìm thấy cài đặt")
    await asyncio.to_thread(_query)
    return {"success": True, "key": key}


class BulkSettingUpdate(BaseModel):
    updates: dict[str, object] = Field(..., description="Map of key→value to update")


@router.post("/site-settings/bulk",
             summary="Bulk update site settings",
             description="Update multiple site settings at once. Accepts a map of key-value pairs.")
async def admin_bulk_update_settings(body: BulkSettingUpdate, request: Request):
    """Batch update multiple settings at once."""
    if not db._use_pg:
        raise HTTPException(503, detail="Cài đặt site yêu cầu PostgreSQL")
    count = await asyncio.to_thread(site_settings.bulk_upsert, body.updates, actor=_admin_actor_label(request))
    return {"success": True, "updated": count}


@router.post("/site-settings/reset/{category}",
             summary="Reset category settings to defaults",
             description="Reset all site settings in a category back to their default values.")
async def admin_reset_category(category: str, request: Request):
    """Reset all settings in a category to their defaults."""
    if not _SETTING_KEY_RE.match(category):
        raise HTTPException(400, detail="Tên danh mục không hợp lệ")
    if not db._use_pg:
        raise HTTPException(503, detail="Cài đặt site yêu cầu PostgreSQL")
    def _query():
        from seed_site_settings import DEFAULTS
        return site_settings.reset_category(category, DEFAULTS, actor=_admin_actor_label(request))
    count = await asyncio.to_thread(_query)
    return {"success": True, "reset": count}

@router.get("/site-settings-history",
            summary="Get site settings change history",
            description="Returns recent setting changes, optionally filtered by category or key.")
async def admin_site_settings_history(
    category: Optional[str] = Query(None, max_length=100),
    key: Optional[str] = Query(None, max_length=200),
    limit: int = Query(50, ge=1, le=200),
):
    if category and not _SETTING_KEY_RE.match(category):
        raise HTTPException(400, detail="Tên danh mục không hợp lệ")
    if key and not _SETTING_KEY_RE.match(key):
        raise HTTPException(400, detail="Tên cài đặt không hợp lệ")
    if not db._use_pg:
        raise HTTPException(503, detail="Cài đặt site yêu cầu PostgreSQL")
    return await asyncio.to_thread(site_settings.load_history, category=category, key=key, limit=limit)

@router.post("/site-settings-history/{history_id}/rollback",
             summary="Rollback a site setting change",
             description="Restores a setting value from a previous history snapshot.")
async def admin_site_settings_rollback(history_id: str, request: Request):
    history_id = validate_path_id(history_id, "history_id")
    if not db._use_pg:
        raise HTTPException(503, detail="Cài đặt site yêu cầu PostgreSQL")
    ok = await asyncio.to_thread(site_settings.rollback_history, history_id, actor=_admin_actor_label(request))
    if not ok:
        raise HTTPException(404, detail="Không tìm thấy snapshot")
    return {"success": True, "rolled_back": history_id}


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


@router.post("/notifications/cleanup",
             summary="Clean up old notifications",
             description="Delete read notifications older than N days. Returns the count of deleted records.")
async def admin_cleanup_notifications(days: int = Query(90, ge=7, le=365)):
    """Delete read notifications older than N days."""
    if not db._use_pg:
        raise HTTPException(503, detail="Thông báo yêu cầu PostgreSQL")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            cur = db._execute(conn, f"""
                DELETE FROM notifications
                WHERE is_read = TRUE
                  AND created_at < NOW() - MAKE_INTERVAL(days => {ph})
            """, (days,))
            return cur.rowcount if cur else 0
    deleted = await asyncio.to_thread(_query)
    return {"success": True, "deleted": deleted, "days": days}


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

@router.get("/claims",
            summary="List entity ownership claims",
            description="List entity ownership claims filtered by status for admin review. Supports pagination.")
async def list_claims(
    status: str = Query("pending", max_length=20),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0, le=10000),
):
    """U-30: List entity claims for admin review."""
    require_pg()
    valid_statuses = ("pending", "approved", "rejected", "all")
    if status not in valid_statuses:
        raise HTTPException(422, f"Status không hợp lệ. Cho phép: {', '.join(valid_statuses)}")

    ph = db._ph

    def _query():
        where = "" if status == "all" else f"WHERE c.status = {ph}"
        params = [] if status == "all" else [status]
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT c.id, c.entity_id, c.business_name, c.contact_phone,
                       c.contact_email, c.evidence, c.status, c.created_at,
                       c.reviewed_at, c.rejection_reason,
                       u.display_name as claimant_name, u.phone as claimant_phone
                FROM entity_claims c
                JOIN users u ON u.id = c.claimant_id
                {where}
                ORDER BY c.created_at DESC
                LIMIT {ph} OFFSET {ph}
            """, tuple(params + [limit, offset]))
            total_row = db._fetchone(conn, f"""
                SELECT COUNT(*) as cnt FROM entity_claims c {where}
            """, tuple(params))
        total = db._row_to_dict(total_row)["cnt"] if total_row else 0
        return {
            "claims": [db._row_to_dict(r) for r in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    return await asyncio.to_thread(_query)


class ClaimDecisionBody(BaseModel):
    reason: str = Field("", max_length=1000)


@router.post("/claims/{claim_id}/approve",
             summary="Approve an entity ownership claim",
             description="Approve a pending entity ownership claim. Notifies the claimant upon approval.")
async def approve_claim(claim_id: str, request: Request):
    """U-30: Approve an entity claim."""
    require_pg()
    claim_id = validate_path_id(claim_id, "claim_id")
    ph = db._ph
    admin_user = getattr(request.state, "admin_user", None)

    def _approve():
        with db._conn() as conn:
            row = db._fetchone(conn, f"SELECT id, status, claimant_id, entity_id FROM entity_claims WHERE id = {ph}::uuid", (claim_id,))
            if not row:
                return {"error": "not_found"}
            claim = db._row_to_dict(row)
            if claim["status"] != "pending":
                return {"error": "not_pending", "current_status": claim["status"]}
            reviewer_id = str(admin_user["id"]) if admin_user else None
            db._execute(conn, f"""
                UPDATE entity_claims SET status = 'approved', reviewer_id = {ph}::uuid, reviewed_at = NOW()
                WHERE id = {ph}::uuid
            """, (reviewer_id, claim_id))
        return {"ok": True, "claimant_id": str(claim["claimant_id"]), "entity_id": claim.get("entity_id")}

    result = await asyncio.to_thread(_approve)
    if "error" in result:
        code = 404 if result["error"] == "not_found" else 409
        detail = "Không tìm thấy claim" if result["error"] == "not_found" else f"Claim đã xử lý ({result.get('current_status', '')})"
        raise HTTPException(code, detail)
    _log_mod_action("claim", claim_id, "approved")
    if result.get("claimant_id"):
        def _notify():
            create_notification(
                result["claimant_id"], "claim_approved",
                "Yêu cầu xác nhận doanh nghiệp của bạn đã được duyệt!",
                ref_type="entity", ref_id=result.get("entity_id", ""),
            )
        await asyncio.to_thread(_notify)
    return {"ok": True}


@router.post("/claims/{claim_id}/reject",
             summary="Reject an entity ownership claim",
             description="Reject a pending entity ownership claim with an optional reason. Notifies the claimant.")
async def reject_claim(claim_id: str, body: ClaimDecisionBody, request: Request):
    """U-30: Reject an entity claim with optional reason."""
    require_pg()
    claim_id = validate_path_id(claim_id, "claim_id")
    ph = db._ph
    admin_user = getattr(request.state, "admin_user", None)

    def _reject():
        with db._conn() as conn:
            row = db._fetchone(conn, f"SELECT id, status, claimant_id, entity_id FROM entity_claims WHERE id = {ph}::uuid", (claim_id,))
            if not row:
                return {"error": "not_found"}
            claim = db._row_to_dict(row)
            if claim["status"] != "pending":
                return {"error": "not_pending", "current_status": claim["status"]}
            reviewer_id = str(admin_user["id"]) if admin_user else None
            db._execute(conn, f"""
                UPDATE entity_claims SET status = 'rejected', reviewer_id = {ph}::uuid,
                    reviewed_at = NOW(), rejection_reason = {ph}
                WHERE id = {ph}::uuid
            """, (reviewer_id, body.reason, claim_id))
        return {"ok": True, "claimant_id": str(claim["claimant_id"]), "entity_id": claim.get("entity_id")}

    result = await asyncio.to_thread(_reject)
    if "error" in result:
        code = 404 if result["error"] == "not_found" else 409
        detail = "Không tìm thấy claim" if result["error"] == "not_found" else f"Claim đã xử lý ({result.get('current_status', '')})"
        raise HTTPException(code, detail)
    _log_mod_action("claim", claim_id, "rejected", body.reason or None)
    if result.get("claimant_id"):
        def _notify():
            create_notification(
                result["claimant_id"], "claim_rejected",
                "Yêu cầu xác nhận doanh nghiệp của bạn chưa được duyệt.",
                ref_type="entity", ref_id=result.get("entity_id", ""),
            )
        await asyncio.to_thread(_notify)
    return {"ok": True}


# ── Announcements (system notices for users) ────────────────────────────

class AnnouncementCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field("", max_length=5000)
    type: str = Field("info", max_length=20)
    priority: int = Field(0, ge=0, le=100)
    starts_at: Optional[str] = None
    expires_at: Optional[str] = None

    @field_validator("type")
    @classmethod
    def _validate_type(cls, v):
        allowed = ("info", "warning", "maintenance", "update")
        if v not in allowed:
            raise ValueError(f"type must be one of {allowed}")
        return v


class AnnouncementUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, max_length=5000)
    type: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=0, le=100)
    starts_at: Optional[str] = None
    expires_at: Optional[str] = None

    @field_validator("type")
    @classmethod
    def _validate_type(cls, v):
        if v is None:
            return v
        allowed = ("info", "warning", "maintenance", "update")
        if v not in allowed:
            raise ValueError(f"type must be one of {allowed}")
        return v


@router.get("/announcements",
            summary="List announcements",
            description="List system announcements with optional active-status filter. Supports pagination.")
async def list_announcements(
    is_active: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0, le=10000),
):
    require_pg()
    ph = db._ph

    def _query():
        where_clauses = []
        params = []
        if is_active is not None:
            where_clauses.append(f"is_active = {ph}")
            params.append(is_active)
        where = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT id, title, content, type, is_active, priority,
                       starts_at, expires_at, created_by, created_at, updated_at
                FROM announcements
                {where}
                ORDER BY priority DESC, created_at DESC
                LIMIT {ph} OFFSET {ph}
            """, tuple(params + [limit, offset]))
            total_row = db._fetchone(conn, f"SELECT COUNT(*) as cnt FROM announcements {where}", tuple(params))
        total = db._row_to_dict(total_row)["cnt"] if total_row else 0
        return {
            "announcements": [db._row_to_dict(r) for r in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    return await asyncio.to_thread(_query)


@router.post("/announcements", status_code=201,
             summary="Create an announcement",
             description="Create a new system announcement with title, content, type, priority, and optional schedule.")
async def create_announcement(body: AnnouncementCreate, request: Request):
    require_pg()
    ph = db._ph
    admin_user = getattr(request.state, "admin_user", None)

    def _query():
        created_by = str(admin_user["id"]) if admin_user else None
        with db._conn() as conn:
            row = db._fetchone(conn, f"""
                INSERT INTO announcements (title, content, type, priority, starts_at, expires_at, created_by)
                VALUES ({ph}, {ph}, {ph}, {ph},
                        COALESCE({ph}::timestamptz, NOW()),
                        {ph}::timestamptz,
                        {ph}::uuid)
                RETURNING id, title, type, is_active, priority, starts_at, expires_at, created_at
            """, (
                body.title.strip(), body.content.strip(), body.type,
                body.priority, body.starts_at, body.expires_at,
                created_by,
            ))
        return db._row_to_dict(row) if row else None

    result = await asyncio.to_thread(_query)
    return {"success": True, "announcement": result}


@router.put("/announcements/{announcement_id}",
            summary="Update an announcement",
            description="Update fields of an existing announcement. Only provided fields are changed.")
async def update_announcement(announcement_id: str, body: AnnouncementUpdate):
    require_pg()
    announcement_id = validate_path_id(announcement_id, "announcement_id")
    ph = db._ph

    def _query():
        sets = []
        params = []
        if body.title is not None:
            sets.append(f"title = {ph}")
            params.append(body.title.strip())
        if body.content is not None:
            sets.append(f"content = {ph}")
            params.append(body.content.strip())
        if body.type is not None:
            sets.append(f"type = {ph}")
            params.append(body.type)
        if body.is_active is not None:
            sets.append(f"is_active = {ph}")
            params.append(body.is_active)
        if body.priority is not None:
            sets.append(f"priority = {ph}")
            params.append(body.priority)
        if body.starts_at is not None:
            sets.append(f"starts_at = {ph}::timestamptz")
            params.append(body.starts_at)
        if body.expires_at is not None:
            sets.append(f"expires_at = {ph}::timestamptz")
            params.append(body.expires_at)
        if not sets:
            raise HTTPException(400, "Không có thay đổi")
        sets.append("updated_at = NOW()")
        params.append(announcement_id)
        with db._conn() as conn:
            row = db._fetchone(conn, f"""
                UPDATE announcements SET {", ".join(sets)}
                WHERE id::text = {ph}
                RETURNING id, title, content, type, is_active, priority, starts_at, expires_at, updated_at
            """, tuple(params))
        if not row:
            raise HTTPException(404, "Thông báo không tồn tại")
        return db._row_to_dict(row)

    result = await asyncio.to_thread(_query)
    return {"success": True, "announcement": result}


@router.delete("/announcements/{announcement_id}",
               summary="Delete an announcement",
               description="Permanently delete an announcement by ID.")
async def delete_announcement(announcement_id: str):
    require_pg()
    announcement_id = validate_path_id(announcement_id, "announcement_id")
    ph = db._ph

    def _query():
        with db._conn() as conn:
            row = db._fetchone(conn, f"""
                DELETE FROM announcements WHERE id::text = {ph} RETURNING id
            """, (announcement_id,))
        if not row:
            raise HTTPException(404, "Thông báo không tồn tại")
        return True

    await asyncio.to_thread(_query)
    return {"success": True}


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
    # An toàn: CHỈ áp reorder khi không mất route. Nếu _reorder_static_routes bỏ sót
    # static (spath không khớp param nào trong other_routes) → other_routes ngắn hơn →
    # router.routes[:] sẽ LÀM RỖNG/MẤT route (đã thấy admin.router trống trên CI-Linux).
    if len(other_routes) == len(router.routes):
        router.routes[:] = other_routes

_fix_admin_route_order()
