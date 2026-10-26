"""
vinhlong360 — Site Settings Module.

CRUD + in-memory cache for the site_settings table (Postgres-only).
Provides get/set operations for admin-configurable website elements:
branding, SEO, navigation, footer, homepage, contact, announcements,
chat widget, theme colors, category overrides.

Usage:
    from site_settings import settings_manager
    all_public = settings_manager.get_all_public()
    settings_manager.upsert("branding.site_name", "vinhlong360")
"""

import json
import time
import uuid
from threading import Lock
from database import db

_cache: dict[str, object] | None = None
_cache_ts: float = 0
_llm_cache: dict[str, object] | None = None
_llm_cache_ts: float = 0
_cache_lock = Lock()
_CACHE_TTL = 60  # seconds
# Key khớp các marker này (hoặc prefix llm.) KHÔNG bao giờ được trả qua public API.
_SENSITIVE_MARKERS = ("api_key", "secret", "token", "password")


def is_public_key(key: str) -> bool:
    """Key này có được phép trả qua GET /api/site-settings (public, không auth)?"""
    kl = str(key).lower()
    return not (kl.startswith("llm.") or any(m in kl for m in _SENSITIVE_MARKERS))


def _ensure_table():
    """Create the site_settings table if it doesn't exist (Postgres only)."""
    if not db._use_pg:
        return False
    try:
        with db._conn() as conn:
            db._execute(conn, """
                CREATE TABLE IF NOT EXISTS site_settings (
                    key         TEXT PRIMARY KEY,
                    value       JSONB NOT NULL,
                    category    TEXT NOT NULL,
                    label       TEXT NOT NULL DEFAULT '',
                    description TEXT DEFAULT '',
                    input_type  TEXT DEFAULT 'text',
                    updated_at  TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            db._execute(conn, """
                CREATE INDEX IF NOT EXISTS idx_site_settings_cat ON site_settings(category)
            """)
        return True
    except Exception:
        return False

def _ensure_history_table():
    if not db._use_pg:
        return False
    try:
        with db._conn() as conn:
            db._execute(conn, """
                CREATE TABLE IF NOT EXISTS site_settings_history (
                    id             TEXT PRIMARY KEY,
                    setting_key    TEXT NOT NULL,
                    category       TEXT NOT NULL,
                    previous_value JSONB,
                    next_value     JSONB,
                    action         TEXT NOT NULL,
                    actor          TEXT,
                    created_at     TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            db._execute(conn, """
                CREATE INDEX IF NOT EXISTS idx_site_settings_history_key
                ON site_settings_history(setting_key, created_at DESC)
            """)
            db._execute(conn, """
                CREATE INDEX IF NOT EXISTS idx_site_settings_history_cat
                ON site_settings_history(category, created_at DESC)
            """)
        return True
    except Exception:
        return False


_history_ensured_db_id: int | None = None


def _ensure_history_once() -> None:
    global _history_ensured_db_id
    cur_db_id = id(db)
    if _history_ensured_db_id == cur_db_id:
        return
    if _ensure_history_table():
        _history_ensured_db_id = cur_db_id


def _invalidate():
    global _cache, _cache_ts, _llm_cache, _llm_cache_ts, _history_ensured_db_id
    with _cache_lock:
        _cache = None
        _cache_ts = 0
        _llm_cache = None
        _llm_cache_ts = 0
        _history_ensured_db_id = None


def _parse_setting_value(val: object) -> object:
    if isinstance(val, str):
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return val
    return val


def _format_admin_setting_row(row) -> dict:
    r = db._row_to_dict(row)
    val = _parse_setting_value(r["value"])
    r["value"] = _mask_if_sensitive(str(r["key"]), val)
    if r.get("updated_at"):
        r["updated_at"] = str(r["updated_at"])
    return r


def get_all_public() -> dict[str, object]:
    """Return flat {key: value} dict of all settings. Cached for 60s."""
    global _cache, _cache_ts
    with _cache_lock:
        if _cache is not None and (time.time() - _cache_ts) < _CACHE_TTL:
            return _cache

    if not db._use_pg:
        return {}

    try:
        with db._conn() as conn:
            rows = db._fetchall(conn, "SELECT key, value FROM site_settings")
        result = {}
        for row in rows:
            r = db._row_to_dict(row)
            key = str(r["key"])
            if not is_public_key(key):
                continue
            result[key] = _parse_setting_value(r["value"])
        with _cache_lock:
            _cache = result
            _cache_ts = time.time()
        return result
    except Exception:
        return {}


def is_sensitive_key(key: str) -> bool:
    """Return True if key holds a secret/token/api_key/password."""
    kl = str(key).lower()
    return any(m in kl for m in _SENSITIVE_MARKERS)


def _mask_secret_value(val: object) -> str:
    if isinstance(val, str) and len(val) >= 2 and val[0] == '"' and val[-1] == '"':
        val = val[1:-1]
    s = str(val or "")
    if s.endswith("***"):
        return s
    return s[:4] + "***" if len(s) > 8 else "***"


def _mask_if_sensitive(key: str, val: object) -> object:
    return _mask_secret_value(val) if is_sensitive_key(key) and val is not None else val


def get_llm_settings() -> dict[str, object]:
    """Return internal llm.* settings from site_settings (for llm_config runtime, cached 60s)."""
    global _llm_cache, _llm_cache_ts
    with _cache_lock:
        if _llm_cache is not None and (time.time() - _llm_cache_ts) < _CACHE_TTL:
            return dict(_llm_cache)
    if not db._use_pg:
        return {}
    try:
        with db._conn() as conn:
            rows = db._fetchall(conn, "SELECT key, value FROM site_settings WHERE category = 'llm'")
        out: dict[str, object] = {}
        for row in rows:
            r = db._row_to_dict(row)
            key = str(r["key"])
            if key.startswith("llm."):
                out[key] = _parse_setting_value(r["value"])
        with _cache_lock:
            _llm_cache = dict(out)
            _llm_cache_ts = time.time()
        return out
    except Exception:
        return {}


def get_by_category(category: str) -> list[dict]:
    """Return all settings for a category with full metadata (for admin editor)."""
    if not db._use_pg:
        return []
    ph = db._ph
    with db._conn() as conn:
        rows = db._fetchall(conn, f"""
            SELECT key, value, category, label, description, input_type, updated_at
            FROM site_settings WHERE category = {ph}
            ORDER BY key
        """, (category,))
    return [_format_admin_setting_row(row) for row in rows]


def get_all_grouped() -> dict[str, list[dict]]:
    """Return all settings grouped by category (for admin overview)."""
    if not db._use_pg:
        return {}
    with db._conn() as conn:
        rows = db._fetchall(conn, """
            SELECT key, value, category, label, description, input_type, updated_at
            FROM site_settings ORDER BY category, key
        """)
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        r = _format_admin_setting_row(row)
        grouped.setdefault(r["category"], []).append(r)
    return grouped


_MAX_VALUE_SIZE = 100_000


def _json_value(value: object) -> str:
    val_json = json.dumps(value, ensure_ascii=False)
    if len(val_json) > _MAX_VALUE_SIZE:
        raise ValueError(f"Setting value too large ({len(val_json)} > {_MAX_VALUE_SIZE})")
    return val_json


def _record_history(conn, *, key: str, category: str, previous: object, next_value: object, action: str, actor: str | None = None) -> None:
    ph = db._ph
    db._execute(conn, f"""
        INSERT INTO site_settings_history (id, setting_key, category, previous_value, next_value, action, actor)
        VALUES ({ph}, {ph}, {ph}, {ph}::jsonb, {ph}::jsonb, {ph}, {ph})
    """, (
        str(uuid.uuid4()),
        key,
        category,
        json.dumps(_mask_if_sensitive(key, previous), ensure_ascii=False),
        json.dumps(_mask_if_sensitive(key, next_value), ensure_ascii=False),
        action,
        actor,
    ))


def _update_setting_with_history(
    conn,
    *,
    key: str,
    value: object,
    val_json: str,
    action: str,
    actor: str | None = None,
    category_override: str | None = None,
) -> bool:
    ph = db._ph
    current = db._fetchone(conn, f"SELECT key, value, category FROM site_settings WHERE key = {ph}", (key,))
    if not current:
        return False
    cur = db._row_to_dict(current)
    update_cur = db._execute(conn, f"""
        UPDATE site_settings SET value = {ph}::jsonb, updated_at = NOW()
        WHERE key = {ph}
    """, (val_json, key))
    if getattr(update_cur, "rowcount", 0) <= 0:
        return False
    resolved_cat = category_override or cur.get("category") or key.split(".")[0]
    _record_history(
        conn,
        key=key,
        category=resolved_cat,
        previous=cur.get("value"),
        next_value=value,
        action=action,
        actor=actor,
    )
    return True


def upsert(key: str, value: object, *, actor: str | None = None, action: str = "update") -> bool:
    """Update a single setting's value. Invalidates cache."""
    if not db._use_pg:
        return False
    _ensure_history_once()
    val_json = _json_value(value)
    with db._conn() as conn:
        if not _update_setting_with_history(conn, key=key, value=value, val_json=val_json, action=action, actor=actor):
            return False
    _invalidate()
    return True


def bulk_upsert(updates: dict[str, object], *, actor: str | None = None) -> int:
    """Update multiple settings atomically. Returns count of updated rows."""
    if not db._use_pg or not updates:
        return 0
    _ensure_history_once()
    count = 0
    with db._conn() as conn:
        for key, value in updates.items():
            val_json = _json_value(value)
            if _update_setting_with_history(conn, key=key, value=value, val_json=val_json, action="bulk_update", actor=actor):
                count += 1
    _invalidate()
    return count


def reset_category(category: str, defaults: dict[str, dict], *, actor: str | None = None) -> int:
    """Reset all settings in a category to their default values."""
    if not db._use_pg:
        return 0
    _ensure_history_once()
    count = 0
    with db._conn() as conn:
        for key, meta in defaults.items():
            if meta.get("category") != category:
                continue
            val_json = _json_value(meta["value"])
            if _update_setting_with_history(
                conn,
                key=key,
                value=meta["value"],
                val_json=val_json,
                action="reset",
                actor=actor,
                category_override=category,
            ):
                count += 1
    _invalidate()
    return count


def load_history(category: str | None = None, key: str | None = None, limit: int = 50) -> dict[str, object]:
    if not db._use_pg:
        return {"total": 0, "history": []}
    _ensure_history_once()
    ph = db._ph
    conditions = []
    params: list[object] = []
    if category:
        conditions.append(f"category = {ph}")
        params.append(category)
    if key:
        conditions.append(f"setting_key = {ph}")
        params.append(key)
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    limit = max(1, min(int(limit or 50), 200))
    with db._conn() as conn:
        rows = db._fetchall(conn, f"""
            SELECT id, setting_key, category, previous_value, next_value, action, actor, created_at
            FROM site_settings_history
            {where}
            ORDER BY created_at DESC
            LIMIT {ph}
        """, tuple(params + [limit]))
        total = db._fetchone(conn, f"SELECT COUNT(*) as c FROM site_settings_history {where}", tuple(params))
    out = []
    for row in rows:
        item = db._row_to_dict(row)
        skey = str(item.get("setting_key") or "")
        item["previous_value"] = _mask_if_sensitive(skey, item.get("previous_value"))
        item["next_value"] = _mask_if_sensitive(skey, item.get("next_value"))
        if item.get("created_at"):
            item["created_at"] = str(item["created_at"])
        out.append(item)
    return {"total": db._row_to_dict(total)["c"] if total else 0, "history": out}


def rollback_history(history_id: str, *, actor: str | None = None) -> bool:
    if not db._use_pg:
        return False
    _ensure_history_once()
    ph = db._ph
    with db._conn() as conn:
        row = db._fetchone(conn, f"""
            SELECT id, setting_key, category, previous_value
            FROM site_settings_history WHERE id = {ph}
        """, (history_id,))
        if not row:
            return False
        rec = db._row_to_dict(row)
        prev = rec.get("previous_value")
        if not _update_setting_with_history(
            conn,
            key=rec["setting_key"],
            value=prev,
            val_json=_json_value(prev),
            action="rollback",
            actor=actor,
            category_override=rec.get("category"),
        ):
            return False
    _invalidate()
    return True

def seed_defaults(defaults: dict[str, dict]) -> int:
    """Insert default settings (ON CONFLICT DO NOTHING). Returns count inserted."""
    if not db._use_pg:
        return 0
    _ensure_table()
    ph = db._ph
    count = 0
    with db._conn() as conn:
        for key, meta in defaults.items():
            val_json = _json_value(meta["value"])
            cur = db._execute(conn, f"""
                INSERT INTO site_settings (key, value, category, label, description, input_type)
                VALUES ({ph}, {ph}::jsonb, {ph}, {ph}, {ph}, {ph})
                ON CONFLICT (key) DO NOTHING
            """, (key, val_json, meta["category"], meta.get("label", ""),
                  meta.get("description", ""), meta.get("input_type", "text")))
            if hasattr(cur, 'rowcount') and cur.rowcount > 0:
                count += 1
    _invalidate()
    return count
