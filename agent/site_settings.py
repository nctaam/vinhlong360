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
from threading import Lock
from database import db

_cache: dict[str, object] | None = None
_cache_ts: float = 0
_cache_lock = Lock()
_CACHE_TTL = 60  # seconds


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


def _invalidate():
    global _cache, _cache_ts
    with _cache_lock:
        _cache = None
        _cache_ts = 0


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
            val = r["value"]
            if isinstance(val, str):
                try:
                    val = json.loads(val)
                except (json.JSONDecodeError, TypeError):
                    pass
            result[r["key"]] = val
        with _cache_lock:
            _cache = result
            _cache_ts = time.time()
        return result
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
    result = []
    for row in rows:
        r = db._row_to_dict(row)
        val = r["value"]
        if isinstance(val, str):
            try:
                val = json.loads(val)
            except (json.JSONDecodeError, TypeError):
                pass
        r["value"] = val
        if r.get("updated_at"):
            r["updated_at"] = str(r["updated_at"])
        result.append(r)
    return result


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
        r = db._row_to_dict(row)
        val = r["value"]
        if isinstance(val, str):
            try:
                val = json.loads(val)
            except (json.JSONDecodeError, TypeError):
                pass
        r["value"] = val
        if r.get("updated_at"):
            r["updated_at"] = str(r["updated_at"])
        grouped.setdefault(r["category"], []).append(r)
    return grouped


def upsert(key: str, value: object) -> bool:
    """Update a single setting's value. Invalidates cache."""
    if not db._use_pg:
        return False
    ph = db._ph
    val_json = json.dumps(value, ensure_ascii=False)
    with db._conn() as conn:
        db._execute(conn, f"""
            UPDATE site_settings SET value = {ph}::jsonb, updated_at = NOW()
            WHERE key = {ph}
        """, (val_json, key))
    _invalidate()
    return True


def bulk_upsert(updates: dict[str, object]) -> int:
    """Update multiple settings atomically. Returns count of updated rows."""
    if not db._use_pg or not updates:
        return 0
    ph = db._ph
    count = 0
    with db._conn() as conn:
        for key, value in updates.items():
            val_json = json.dumps(value, ensure_ascii=False)
            db._execute(conn, f"""
                UPDATE site_settings SET value = {ph}::jsonb, updated_at = NOW()
                WHERE key = {ph}
            """, (val_json, key))
            count += 1
    _invalidate()
    return count


def reset_category(category: str, defaults: dict[str, dict]) -> int:
    """Reset all settings in a category to their default values."""
    if not db._use_pg:
        return 0
    ph = db._ph
    count = 0
    with db._conn() as conn:
        for key, meta in defaults.items():
            if meta.get("category") != category:
                continue
            val_json = json.dumps(meta["value"], ensure_ascii=False)
            db._execute(conn, f"""
                UPDATE site_settings SET value = {ph}::jsonb, updated_at = NOW()
                WHERE key = {ph}
            """, (val_json, key))
            count += 1
    _invalidate()
    return count


def seed_defaults(defaults: dict[str, dict]) -> int:
    """Insert default settings (ON CONFLICT DO NOTHING). Returns count inserted."""
    if not db._use_pg:
        return 0
    _ensure_table()
    ph = db._ph
    count = 0
    with db._conn() as conn:
        for key, meta in defaults.items():
            val_json = json.dumps(meta["value"], ensure_ascii=False)
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
