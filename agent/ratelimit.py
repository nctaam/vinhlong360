"""
Rate-limit sliding-window trong-bộ-nhớ (per-process). Đủ cho 1 instance, <10k user.
Nếu scale nhiều instance → thay bằng Redis. Dùng cho chống-spam UGC (tạo bài/bình
luận/upload ảnh). Login/OTP đã có limit riêng trong auth.py.

    from ratelimit import check_rate
    check_rate(f"post:{user_id}", limit=10, window=600)   # raise HTTPException(429) nếu vượt
"""
import logging
import threading
import time

from fastapi import HTTPException

logger = logging.getLogger(__name__)

_rl_lock = threading.Lock()

# key -> list[timestamp] (chỉ giữ trong cửa sổ hiện tại)
_buckets: dict[str, list[float]] = {}
_MAX_KEYS = 50_000  # chặn phình bộ nhớ vô hạn (đủ lớn cho <10k user × vài loại key)


def _now() -> float:
    return time.time()


def check_rate(key: str, limit: int, window: int,
               msg: str = "Bạn thao tác quá nhanh. Vui lòng thử lại sau.") -> None:
    """Ghi nhận 1 lượt cho `key`; raise HTTPException(429) nếu đã đạt `limit` trong `window` giây."""
    now = _now()
    with _rl_lock:
        hits = [t for t in _buckets.get(key, []) if now - t < window]
        if len(hits) >= limit:
            _buckets[key] = hits
            retry_after = int(window - (now - hits[0])) + 1
            raise HTTPException(
                429, msg,
                headers={
                    "Retry-After": str(max(1, retry_after)),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(hits[0] + window)),
                },
            )
        hits.append(now)
        _buckets[key] = hits
        if len(_buckets) > _MAX_KEYS:
            logger.warning("Rate-limit buckets at capacity (%d); running GC", len(_buckets))
            _gc(now)


def _gc(now: float | None = None) -> None:
    """Dọn các bucket rỗng/hết hạn (gọi cơ hội khi dict phình to)."""
    now = now if now is not None else _now()
    dead = [k for k, ts in _buckets.items() if not ts or now - ts[-1] > 3600]
    for k in dead:
        _buckets.pop(k, None)
    if len(_buckets) > _MAX_KEYS:
        by_age = sorted(_buckets.items(), key=lambda kv: kv[1][-1] if kv[1] else 0)
        for k, _ in by_age[:len(_buckets) - _MAX_KEYS + _MAX_KEYS // 10]:
            _buckets.pop(k, None)


def check_rate_ip(ip: str, action: str, limit: int, window: int,
                   msg: str = "Quá nhiều yêu cầu. Vui lòng thử lại sau.") -> None:
    """Rate-limit by IP + action name. Convenience wrapper for IP-based limits."""
    check_rate(f"{action}:{ip}", limit, window, msg)


def is_rate_limited(key: str, limit: int, window: int) -> bool:
    """Non-throwing check: returns True if key has hit the limit (does NOT record a hit)."""
    now = _now()
    hits = [t for t in _buckets.get(key, []) if now - t < window]
    return len(hits) >= limit


# ── Pre-defined rate-limit profiles for common endpoint categories ──

RATE_PROFILES = {
    "phone_check": {"limit": 10, "window": 300},
    "search": {"limit": 30, "window": 60},
    "llm_trigger": {"limit": 5, "window": 300},
    "checkpoint": {"limit": 20, "window": 60},
    "public_write": {"limit": 10, "window": 60},
}


def check_rate_profile(key: str, profile: str,
                        msg: str = "Bạn thao tác quá nhanh. Vui lòng thử lại sau.") -> None:
    """Rate-limit using a named profile from RATE_PROFILES."""
    cfg = RATE_PROFILES.get(profile)
    if not cfg:
        return
    check_rate(key, cfg["limit"], cfg["window"], msg)


# ── Adaptive rate limiting with progressive penalties ──

_violations: dict[str, list[float]] = {}
_VIOLATION_DECAY = 3600  # 1 hour window for counting violations


def check_rate_adaptive(key: str, base_limit: int, base_window: int,
                         msg: str = "Bạn thao tác quá nhanh. Vui lòng thử lại sau.") -> None:
    """Rate-limit with progressive penalties on repeated violations.

    1st violation: normal 429
    2nd violation within 1h: limit halved
    3rd+ violations: limit quartered, window doubled
    """
    now = _now()
    with _rl_lock:
        violation_count = len([t for t in _violations.get(key, []) if now - t < _VIOLATION_DECAY])

        if violation_count >= 3:
            effective_limit = max(1, base_limit // 4)
            effective_window = base_window * 2
        elif violation_count >= 1:
            effective_limit = max(1, base_limit // 2)
            effective_window = base_window
        else:
            effective_limit = base_limit
            effective_window = base_window

        hits = [t for t in _buckets.get(key, []) if now - t < effective_window]
        if len(hits) >= effective_limit:
            _buckets[key] = hits
            if key not in _violations:
                _violations[key] = []
            _violations[key].append(now)
            _violations[key] = [t for t in _violations[key] if now - t < _VIOLATION_DECAY]
            raise HTTPException(429, msg)
        hits.append(now)
        _buckets[key] = hits
        if len(_buckets) > _MAX_KEYS:
            _gc(now)


# ── Global IP budget (total requests across all endpoints) ──

_ip_global: dict[str, list[float]] = {}
_IP_GLOBAL_LIMIT = 300   # max 300 requests/minute from any single IP
_IP_GLOBAL_WINDOW = 60


def check_global_ip_budget(ip: str,
                            msg: str = "Quá nhiều yêu cầu. Vui lòng chờ và thử lại.") -> None:
    """Enforce a global per-IP request budget across all endpoints.

    Catches scanners/fuzzers that spread requests across many endpoints
    to evade per-endpoint limits.
    """
    now = _now()
    with _rl_lock:
        hits = [t for t in _ip_global.get(ip, []) if now - t < _IP_GLOBAL_WINDOW]
        if len(hits) >= _IP_GLOBAL_LIMIT:
            _ip_global[ip] = hits
            raise HTTPException(429, msg)
        hits.append(now)
        _ip_global[ip] = hits
        if len(_ip_global) > _MAX_KEYS:
            dead = [k for k, ts in _ip_global.items() if not ts or now - ts[-1] > _IP_GLOBAL_WINDOW * 2]
            for k in dead:
                _ip_global.pop(k, None)


def get_violation_count(key: str) -> int:
    """Get current violation count for a key (for diagnostics/testing)."""
    now = _now()
    return len([t for t in _violations.get(key, []) if now - t < _VIOLATION_DECAY])


# ── Burst detection ──

def detect_burst(key: str, burst_limit: int = 10, burst_window: int = 2) -> bool:
    """Detect a burst of requests (many requests in a very short window).

    Returns True if burst detected. Does NOT block — caller decides action.
    """
    now = _now()
    hits = [t for t in _buckets.get(key, []) if now - t < burst_window]
    return len(hits) >= burst_limit


# ── Reputation-aware rate limiting ──

def check_rate_reputation_aware(
    key: str, ip: str, base_limit: int, base_window: int,
    msg: str = "Bạn thao tác quá nhanh. Vui lòng thử lại sau.",
) -> None:
    """Rate-limit with limits adjusted by IP reputation.

    Clean IPs get full limit. Suspicious: 75%. Elevated: 50%. Hostile: 25%.
    Integrates with middleware.IPReputationTracker.
    """
    try:
        from middleware import ip_reputation
        level = ip_reputation.threat_level(ip)
    except Exception:
        level = 0

    multiplier = {0: 1.0, 1: 0.75, 2: 0.5, 3: 0.25}.get(level, 1.0)
    effective_limit = max(1, int(base_limit * multiplier))
    check_rate(key, effective_limit, base_window, msg)


# ── Coordinated attack detection (multi-IP same target) ──

_resource_access: dict[str, list[tuple[float, str]]] = {}
_COORD_WINDOW = 120  # 2 minutes
_COORD_THRESHOLD = 10  # 10 different IPs hitting the same resource = coordinated
_resource_lock_flag = False  # simple reentrant guard


def check_coordinated_attack(resource: str, ip: str) -> dict:
    """Detect multiple IPs targeting the same resource within a short window.

    Returns {is_coordinated: bool, unique_ips: int, window: int}
    """
    now = _now()
    with _rl_lock:
        entries = _resource_access.get(resource, [])
        entries = [(t, addr) for t, addr in entries if now - t < _COORD_WINDOW]
        entries.append((now, ip))
        _resource_access[resource] = entries

        if len(_resource_access) > 10_000:
            cutoff = now - _COORD_WINDOW
            dead = [k for k, v in _resource_access.items()
                    if not v or v[-1][0] < cutoff]
            for k in dead:
                _resource_access.pop(k, None)

        unique_ips = len({addr for _, addr in entries})
    return {
        "is_coordinated": unique_ips >= _COORD_THRESHOLD,
        "unique_ips": unique_ips,
        "window": _COORD_WINDOW,
    }


# ── Slow-rate attack detection (L7 DoS) ──

_slow_rate_tracking: dict[str, list[float]] = {}
_SLOW_RATE_WINDOW = 300  # 5 minutes
_SLOW_RATE_THRESHOLD = 50  # steady 50+ requests over 5min from one IP
_SLOW_RATE_MIN_INTERVAL_MS = 3000  # requests spaced suspiciously evenly


def detect_slow_attack(ip: str) -> dict:
    """Detect slow-rate L7 attacks (e.g., Slowloris-style).

    Pattern: steady stream of requests at regular intervals, staying just
    under rate limits but consuming server resources.
    Returns {is_slow_attack: bool, request_count: int, regularity: float}
    """
    now = _now()
    with _rl_lock:
        hits = _slow_rate_tracking.get(ip, [])
        hits = [t for t in hits if now - t < _SLOW_RATE_WINDOW]
        hits.append(now)
        _slow_rate_tracking[ip] = hits

    if len(hits) < _SLOW_RATE_THRESHOLD:
        return {"is_slow_attack": False, "request_count": len(hits), "regularity": 0.0}

    if len(hits) >= 3:
        intervals = [hits[i+1] - hits[i] for i in range(len(hits)-1)]
        if intervals:
            avg = sum(intervals) / len(intervals)
            if avg > 0:
                variance = sum((x - avg) ** 2 for x in intervals) / len(intervals)
                std_dev = variance ** 0.5
                regularity = 1.0 - min(1.0, std_dev / avg) if avg > 0 else 0.0
            else:
                regularity = 0.0
        else:
            regularity = 0.0
    else:
        regularity = 0.0

    is_attack = len(hits) >= _SLOW_RATE_THRESHOLD and regularity > 0.7
    return {
        "is_slow_attack": is_attack,
        "request_count": len(hits),
        "regularity": round(regularity, 3),
    }


# ── Token bucket for smooth rate limiting ──

_token_buckets: dict[str, tuple[float, float]] = {}  # key -> (tokens, last_refill)


def check_rate_token_bucket(
    key: str, capacity: int, refill_rate: float,
    msg: str = "Bạn thao tác quá nhanh. Vui lòng thử lại sau.",
) -> None:
    """Token bucket rate limiter — smoother than sliding window.

    capacity: max tokens (burst capacity)
    refill_rate: tokens per second
    Raises HTTPException(429) when bucket is empty.
    """
    now = _now()
    with _rl_lock:
        tokens, last_refill = _token_buckets.get(key, (float(capacity), now))

        elapsed = now - last_refill
        tokens = min(capacity, tokens + elapsed * refill_rate)

        if tokens < 1.0:
            raise HTTPException(429, msg)

        tokens -= 1.0
        _token_buckets[key] = (tokens, now)

        if len(_token_buckets) > _MAX_KEYS:
            cutoff = now - 3600
            dead = [k for k, (_, t) in _token_buckets.items() if t < cutoff]
            for k in dead:
                _token_buckets.pop(k, None)


# ── Rate limit exemption list ──

_exempt_ips: set[str] = set()
_exempt_keys: set[str] = set()


def add_rate_limit_exemption(ip: str = "", key: str = ""):
    """Add an IP or key to the rate limit exemption list."""
    if ip:
        _exempt_ips.add(ip)
    if key:
        _exempt_keys.add(key)


def remove_rate_limit_exemption(ip: str = "", key: str = ""):
    """Remove an IP or key from the exemption list."""
    _exempt_ips.discard(ip)
    _exempt_keys.discard(key)


def is_exempt(ip: str = "", key: str = "") -> bool:
    """Check if an IP or key is exempt from rate limiting."""
    return ip in _exempt_ips or key in _exempt_keys


def check_rate_with_exemption(
    key: str, ip: str, limit: int, window: int,
    msg: str = "Bạn thao tác quá nhanh. Vui lòng thử lại sau.",
) -> None:
    """Rate-limit with exemption support. Exempt IPs/keys bypass limits."""
    if is_exempt(ip=ip, key=key):
        return
    check_rate(key, limit, window, msg)


# ── Dynamic rate limiting based on server load ──

_load_multiplier: float = 1.0


def set_load_multiplier(multiplier: float):
    """Set a load-based rate limit multiplier (0.1 to 2.0).

    Under heavy load (multiplier < 1.0), all rate limits tighten.
    Under light load (multiplier > 1.0, up to 2.0), limits relax.
    """
    global _load_multiplier
    _load_multiplier = max(0.1, min(2.0, multiplier))


def get_load_multiplier() -> float:
    return _load_multiplier


def check_rate_load_aware(
    key: str, base_limit: int, base_window: int,
    msg: str = "Hệ thống đang tải cao. Vui lòng thử lại sau.",
) -> None:
    """Rate-limit adjusted by server load multiplier."""
    effective_limit = max(1, int(base_limit * _load_multiplier))
    check_rate(key, effective_limit, base_window, msg)


def gc_all() -> dict:
    """Periodic GC for all in-memory rate-limit dicts. Call from scheduler."""
    now = _now()
    with _rl_lock:
        before = sum(len(d) for d in [_buckets, _violations, _ip_global, _resource_access,
                                        _slow_rate_tracking, _token_buckets, _penalty_box,
                                        _penalty_violations, _sliding_counters])
        _gc(now)
        cutoff_global = now - _IP_GLOBAL_WINDOW * 2
        for k in [k for k, ts in _ip_global.items() if not ts or now - ts[-1] > cutoff_global]:
            _ip_global.pop(k, None)
        for k in [k for k, ts in _violations.items() if not ts or now - ts[-1] > _VIOLATION_DECAY]:
            _violations.pop(k, None)
        for k in [k for k, v in _resource_access.items() if not v or v[-1][0] < now - _COORD_WINDOW]:
            _resource_access.pop(k, None)
        for k in [k for k, ts in _slow_rate_tracking.items() if not ts or now - ts[-1] > _SLOW_RATE_WINDOW]:
            _slow_rate_tracking.pop(k, None)
        for k in [k for k, (_, t) in _token_buckets.items() if t < now - 3600]:
            _token_buckets.pop(k, None)
        for ip in [ip for ip, t in _penalty_box.items() if now >= t]:
            _penalty_box.pop(ip, None)
        for ip in [ip for ip, cnt in _penalty_violations.items()
                   if cnt <= 0 or ip not in _penalty_box]:
            _penalty_violations.pop(ip, None)
        for k in [k for k, v in _sliding_counters.items() if not v or v[-1][0] < now - 3600]:
            _sliding_counters.pop(k, None)
        after = sum(len(d) for d in [_buckets, _violations, _ip_global, _resource_access,
                                       _slow_rate_tracking, _token_buckets, _penalty_box,
                                       _penalty_violations, _sliding_counters])
    return {"before": before, "after": after, "freed": before - after}


def _reset() -> None:
    """Chỉ dùng trong test."""
    global _load_multiplier
    _buckets.clear()
    _violations.clear()
    _ip_global.clear()
    _resource_access.clear()
    _slow_rate_tracking.clear()
    _token_buckets.clear()
    _exempt_ips.clear()
    _exempt_keys.clear()
    _load_multiplier = 1.0
    _penalty_box.clear()
    _penalty_violations.clear()
    _sliding_counters.clear()
    _rl_callbacks.clear()


# ── Penalty box (temporary IP ban after severe violations) ──

_penalty_box: dict[str, float] = {}  # ip -> unban_time
_PENALTY_DURATION = 600  # 10 minutes


def add_to_penalty_box(ip: str, duration: int = 0):
    """Put an IP in the penalty box (temporary ban)."""
    dur = duration if duration > 0 else _PENALTY_DURATION
    with _rl_lock:
        _penalty_box[ip] = _now() + dur


def is_in_penalty_box(ip: str) -> bool:
    """Check if an IP is currently in the penalty box."""
    with _rl_lock:
        expiry = _penalty_box.get(ip)
        if expiry is None:
            return False
        if _now() >= expiry:
            _penalty_box.pop(ip, None)
            return False
        return True


def remove_from_penalty_box(ip: str):
    """Manually remove an IP from the penalty box."""
    with _rl_lock:
        _penalty_box.pop(ip, None)


_penalty_violations: dict[str, int] = {}


def check_rate_with_penalty(
    key: str, ip: str, limit: int, window: int,
    penalty_after: int = 3,
    msg: str = "Bạn đã bị tạm khóa do vượt giới hạn.",
) -> None:
    """Rate-limit that auto-bans IPs after repeated violations.

    After `penalty_after` violations, IP goes into the penalty box.
    """
    if is_in_penalty_box(ip):
        raise HTTPException(429, msg)

    try:
        check_rate(key, limit, window)
    except HTTPException:
        with _rl_lock:
            _penalty_violations[ip] = _penalty_violations.get(ip, 0) + 1
            if _penalty_violations[ip] >= penalty_after:
                _penalty_box[ip] = _now() + _PENALTY_DURATION
        raise


# ── Sliding window counter (precise counting) ──

_sliding_counters: dict[str, list[tuple[float, int]]] = {}
_COUNTER_RESOLUTION = 1  # 1-second granularity


def get_sliding_window_count(key: str, window: int) -> int:
    """Get precise request count over a sliding window.

    Uses sub-second bucketing for more accurate counting than list-of-timestamps.
    """
    now = _now()
    buckets = _sliding_counters.get(key, [])
    cutoff = now - window
    total = sum(count for ts, count in buckets if ts > cutoff)
    return total


def increment_sliding_counter(key: str, window: int = 60) -> int:
    """Increment counter and return current count for the window."""
    now = _now()
    bucket_ts = int(now / _COUNTER_RESOLUTION) * _COUNTER_RESOLUTION

    if key not in _sliding_counters:
        _sliding_counters[key] = []
    buckets = _sliding_counters[key]

    # Add to current bucket or create new
    if buckets and int(buckets[-1][0] / _COUNTER_RESOLUTION) == int(bucket_ts / _COUNTER_RESOLUTION):
        buckets[-1] = (buckets[-1][0], buckets[-1][1] + 1)
    else:
        buckets.append((bucket_ts, 1))

    # Prune old buckets
    cutoff = now - window - _COUNTER_RESOLUTION
    _sliding_counters[key] = [(ts, c) for ts, c in buckets if ts > cutoff]

    # GC
    if len(_sliding_counters) > _MAX_KEYS:
        dead = [k for k, v in _sliding_counters.items()
                if not v or v[-1][0] < cutoff]
        for k in dead:
            _sliding_counters.pop(k, None)

    return get_sliding_window_count(key, window)


# ── Rate limit event callbacks ──

_rl_callbacks: list = []


def register_rate_limit_callback(callback):
    """Register a callback to be called when any rate limit is hit.

    Callback signature: callback(key: str, ip: str, limit: int)
    """
    _rl_callbacks.append(callback)


def _fire_callbacks(key: str, ip: str = "", limit: int = 0):
    """Fire registered callbacks on rate limit violation."""
    for cb in _rl_callbacks:
        try:
            cb(key, ip, limit)
        except Exception:
            pass


def check_rate_with_callback(
    key: str, ip: str, limit: int, window: int,
    msg: str = "Bạn thao tác quá nhanh. Vui lòng thử lại sau.",
) -> None:
    """Rate-limit that fires registered callbacks on violation."""
    try:
        check_rate(key, limit, window, msg)
    except HTTPException:
        _fire_callbacks(key, ip, limit)
        raise
