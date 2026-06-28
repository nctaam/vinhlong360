"""
vinhlong360 — LLM Response Cache.

Cache câu trả lời LLM để:
  - Giảm token cost cho câu hỏi phổ biến
  - Tăng tốc response time
  - Giảm load lên API

Strategy: semantic key = normalized query → cached response
TTL: 1 giờ (dữ liệu có thể thay đổi sau auto-learn)
Max size: 500 entries (LRU eviction)

Backend: Redis (if REDIS_URL is set and redis is installed) or in-memory OrderedDict.
"""

import hashlib
import json
import logging
import os
import time
from collections import OrderedDict
from threading import Lock

logger = logging.getLogger(__name__)

try:
    import redis as _redis_lib
except ImportError:
    _redis_lib = None

MAX_SIZE = int(os.environ.get("CACHE_MAX_SIZE", "500"))
DEFAULT_TTL = int(os.environ.get("CACHE_DEFAULT_TTL", "3600"))
_KEY_PREFIX = "vl360:cache:"

# --- Redis connection (lazy, optional) ---
_redis_client = None
_use_redis = False

def _init_redis():
    """Try to connect to Redis if REDIS_URL is set and redis is importable."""
    global _redis_client, _use_redis
    redis_url = os.environ.get("REDIS_URL")
    if redis_url and _redis_lib is not None:
        try:
            _redis_client = _redis_lib.from_url(redis_url, decode_responses=True)
            _redis_client.ping()
            _use_redis = True
        except Exception as e:
            logger.warning("Redis unavailable (%s), falling back to in-memory", e)
            _redis_client = None
            _use_redis = False

_redis_initialized = False

def _ensure_redis():
    global _redis_initialized
    if _redis_initialized:
        return
    _redis_initialized = True
    _init_redis()

# --- In-memory fallback ---
_cache: OrderedDict = OrderedDict()
_lock = Lock()
_stats = {"hits": 0, "misses": 0, "evictions": 0}


def _track_cache_metric(operation: str) -> None:
    """Feed cache operation into Prometheus metrics (best-effort)."""
    try:
        from agent.metrics import track_cache
        track_cache(operation)
    except Exception:
        pass


def _normalize_key(message: str, session_id: str = "") -> str:
    """Chuẩn hóa query thành cache key (isolated by session)."""
    text = message.lower().strip()
    # Bỏ dấu câu cuối
    text = text.rstrip("?!.").strip()
    # Include session_id for isolation (empty = shared cache for common queries)
    key_input = text if not session_id else f"{session_id}:{text}"
    return hashlib.md5(key_input.encode("utf-8")).hexdigest()


def get(message: str) -> dict | None:
    """Lấy cached response. Trả về None nếu miss."""
    _ensure_redis()
    key = _normalize_key(message)

    if _use_redis:
        return _redis_get(key)

    with _lock:
        if key in _cache:
            entry = _cache[key]
            # Check TTL
            if time.time() - entry["timestamp"] < entry.get("ttl", DEFAULT_TTL):
                _stats["hits"] += 1
                _cache.move_to_end(key)
                _track_cache_metric("hit")
                return entry["response"]
            else:
                del _cache[key]
        _stats["misses"] += 1
        _track_cache_metric("miss")
        return None


def put(message: str, response: dict, ttl: int = DEFAULT_TTL):
    """Lưu response vào cache."""
    _ensure_redis()
    key = _normalize_key(message)

    if _use_redis:
        _redis_put(key, response, message, ttl)
        return

    with _lock:
        while len(_cache) >= MAX_SIZE:
            _cache.popitem(last=False)
            _stats["evictions"] += 1
            _track_cache_metric("eviction")

        _cache[key] = {
            "response": response,
            "timestamp": time.time(),
            "ttl": ttl,
            "query": message[:200],
        }


def invalidate_all():
    """Xóa toàn bộ cache (gọi sau khi reload data)."""
    if _use_redis:
        _redis_invalidate_all()
        return

    with _lock:
        _cache.clear()


def stats() -> dict:
    """Thống kê cache."""
    if _use_redis:
        return _redis_stats_summary()

    total = _stats["hits"] + _stats["misses"]
    hit_rate = (_stats["hits"] / total * 100) if total > 0 else 0
    return {
        "size": len(_cache),
        "max_size": MAX_SIZE,
        "hits": _stats["hits"],
        "misses": _stats["misses"],
        "hit_rate": f"{hit_rate:.1f}%",
        "evictions": _stats["evictions"],
        "backend": "in-memory",
    }


# ═══════════════════════════════════════════════
#  Redis backend helpers
# ═══════════════════════════════════════════════

def _redis_key(key: str) -> str:
    return f"{_KEY_PREFIX}{key}"


def _redis_get(key: str) -> dict | None:
    """Get from Redis. TTL is handled natively by Redis."""
    try:
        raw = _redis_client.get(_redis_key(key))
        if raw is not None:
            entry = json.loads(raw)
            _stats["hits"] += 1
            _track_cache_metric("hit")
            return entry["response"]
        _stats["misses"] += 1
        _track_cache_metric("miss")
        return None
    except Exception as exc:
        logger.warning("Redis GET failed: %s", exc)
        _stats["misses"] += 1
        _track_cache_metric("miss")
        return None


def _redis_put(key: str, response: dict, message: str, ttl: int):
    """Store in Redis with native TTL."""
    try:
        entry = {
            "response": response,
            "timestamp": time.time(),
            "query": message[:200],
        }
        _redis_client.set(_redis_key(key), json.dumps(entry, ensure_ascii=False), ex=ttl)
    except Exception as exc:
        logger.warning("Redis SET failed: %s", exc)


def _redis_invalidate_all():
    """Delete all vl360:cache:* keys."""
    try:
        cursor = 0
        while True:
            cursor, keys = _redis_client.scan(cursor, match=f"{_KEY_PREFIX}*", count=200)
            if keys:
                _redis_client.delete(*keys)
            if cursor == 0:
                break
    except Exception as exc:
        logger.warning("Redis invalidate failed: %s", exc)


def _redis_stats_summary() -> dict:
    """Stats when using Redis backend."""
    total = _stats["hits"] + _stats["misses"]
    hit_rate = (_stats["hits"] / total * 100) if total > 0 else 0
    key_count = 0
    try:
        cursor, keys = 0, []
        while True:
            cursor, batch = _redis_client.scan(cursor, match=f"{_KEY_PREFIX}*", count=500)
            keys.extend(batch)
            if cursor == 0:
                break
        key_count = len(keys)
    except Exception as exc:
        logger.debug("Redis stats scan failed: %s", exc)
    return {
        "size": key_count,
        "max_size": "unlimited (Redis)",
        "hits": _stats["hits"],
        "misses": _stats["misses"],
        "hit_rate": f"{hit_rate:.1f}%",
        "evictions": _stats["evictions"],
        "backend": "redis",
    }


def redis_stats() -> dict:
    """Return Redis-specific info. Empty dict if Redis is not active."""
    if not _use_redis:
        return {}
    try:
        info = _redis_client.info(section="memory")
        # Count cache keys
        cursor, keys = 0, []
        while True:
            cursor, batch = _redis_client.scan(cursor, match=f"{_KEY_PREFIX}*", count=500)
            keys.extend(batch)
            if cursor == 0:
                break
        return {
            "connected": True,
            "cache_keys": len(keys),
            "used_memory_human": info.get("used_memory_human", "N/A"),
            "used_memory_bytes": info.get("used_memory", 0),
        }
    except Exception as e:
        logger.warning("Redis health check failed: %s", e)
        return {"connected": False, "error": "Redis unavailable"}


def cache_health_check() -> dict:
    """Quick readiness probe for the cache subsystem."""
    with _lock:
        size = len(_cache)
    return {
        "status": "ok",
        "backend": "redis" if _use_redis else "memory",
        "redis_connected": _use_redis,
        "memory_cache_size": size,
        "memory_cache_max": MAX_SIZE,
        "hits": _stats["hits"],
        "misses": _stats["misses"],
    }
