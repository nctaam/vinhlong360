"""
vinhlong360 — Runtime LLM Configuration.

Admin có thể đổi LLM endpoint/model/key từ AdminCP mà không cần restart.
Ưu tiên: site_settings (DB) > env vars > defaults.

Thread-safe: OpenAI client được tạo lại khi config thay đổi.
"""

import json
import logging
import os
from threading import Lock
from openai import OpenAI

logger = logging.getLogger(__name__)

_lock = Lock()
_client: OpenAI | None = None
_config: dict = {}
_config_source: str = "env"

_ENV_DEFAULTS = {
    "base_url": os.environ.get("LLM_BASE_URL", ""),
    "api_key": os.environ.get("LLM_API_KEY", ""),
    "model": os.environ.get("LLM_MODEL", "cx/gpt-5.4"),
    "model_mini": os.environ.get("LLM_MODEL_MINI", "cx/gpt-5.4-mini"),
}


def _load_from_db() -> dict | None:
    try:
        from site_settings import get_all_public
        settings = get_all_public()
        base_url = settings.get("llm.base_url")
        api_key = settings.get("llm.api_key")
        if base_url and api_key:
            return {
                "base_url": base_url,
                "api_key": api_key,
                "model": settings.get("llm.model") or _ENV_DEFAULTS["model"],
                "model_mini": settings.get("llm.model_mini") or _ENV_DEFAULTS["model_mini"],
            }
    except Exception:
        logger.debug("Failed to load LLM config from DB", exc_info=True)
    return None


def _build_client(cfg: dict) -> OpenAI:
    return OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"], timeout=120.0)


def _resolve_config() -> tuple[dict, str]:
    db_cfg = _load_from_db()
    if db_cfg:
        return db_cfg, "database"
    return dict(_ENV_DEFAULTS), "env"


def get_client() -> OpenAI:
    global _client, _config, _config_source
    with _lock:
        cfg, source = _resolve_config()
        if _client is None or cfg != _config:
            _client = _build_client(cfg)
            _config = cfg
            _config_source = source
            logger.info("LLM client (re)created, source=%s, base_url=%s, model=%s",
                        source, cfg["base_url"], cfg["model"])
        return _client


def get_model() -> str:
    cfg, _ = _resolve_config()
    return cfg["model"]


def get_model_mini() -> str:
    cfg, _ = _resolve_config()
    return cfg["model_mini"]


def get_status() -> dict:
    cfg, source = _resolve_config()
    return {
        "source": source,
        "base_url": cfg["base_url"],
        "api_key_set": bool(cfg["api_key"]),
        "api_key_preview": cfg["api_key"][:8] + "..." if len(cfg["api_key"]) > 8 else "***",
        "model": cfg["model"],
        "model_mini": cfg["model_mini"],
    }


def update_config(base_url: str, api_key: str, model: str, model_mini: str) -> dict:
    """Validate new config with a test call, then save to site_settings."""
    test_client = OpenAI(api_key=api_key, base_url=base_url)
    try:
        resp = test_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "test"}],
            max_tokens=5,
            timeout=15,
        )
        if not resp.choices:
            raise ValueError("LLM returned empty response")
    except Exception as e:
        raise ValueError(f"LLM test call failed: {e}")

    from site_settings import upsert, _ensure_table
    _ensure_table()
    _seed_llm_keys()
    upsert("llm.base_url", base_url)
    upsert("llm.api_key", api_key)
    upsert("llm.model", model)
    upsert("llm.model_mini", model_mini)

    global _client, _config, _config_source
    with _lock:
        _client = None
        _config = {}
        _config_source = ""
    logger.info("LLM config updated via admin, base_url=%s, model=%s", base_url, model)
    return get_status()


def reset_to_env() -> dict:
    """Remove DB overrides, revert to environment variables."""
    try:
        from database import db
        if db._use_pg:
            ph = db._ph
            with db._conn() as conn:
                for key in ("llm.base_url", "llm.api_key", "llm.model", "llm.model_mini"):
                    db._execute(conn, f"DELETE FROM site_settings WHERE key = {ph}", (key,))
            from site_settings import _invalidate
            _invalidate()
    except Exception:
        logger.debug("Failed to clear LLM config from DB", exc_info=True)

    global _client, _config, _config_source
    with _lock:
        _client = None
        _config = {}
        _config_source = ""
    logger.info("LLM config reset to environment variables")
    return get_status()


def _seed_llm_keys():
    """Ensure llm.* keys exist in site_settings table."""
    from database import db
    if not db._use_pg:
        return
    ph = db._ph
    keys = [
        ("llm.base_url", "LLM Base URL", "URL gốc của API (vd: https://api.openai.com/v1)"),
        ("llm.api_key", "LLM API Key", "API key xác thực"),
        ("llm.model", "Model chính", "Model dùng cho chat (vd: gpt-4o, cx/gpt-5.4)"),
        ("llm.model_mini", "Model phụ", "Model nhỏ cho tác vụ đơn giản (vd: gpt-4o-mini)"),
    ]
    with db._conn() as conn:
        for key, label, desc in keys:
            db._execute(conn, f"""
                INSERT INTO site_settings (key, value, category, label, description, input_type)
                VALUES ({ph}, {ph}::jsonb, 'llm', {ph}, {ph}, 'text')
                ON CONFLICT (key) DO NOTHING
            """, (key, json.dumps(""), label, desc))
