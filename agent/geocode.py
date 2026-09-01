"""
vinhlong360 — Geocoder (OpenStreetMap / Nominatim), scoped to the province.

Gives the self-learning pipeline precise map coordinates for auto-found places.
CRITICAL DESIGN: coordinates come from a geocoding API, NEVER from the LLM —
LLMs hallucinate plausible-but-wrong lat/lon (a documented "misevolution" risk).

Safety / politeness:
  - Restricted to the merged Vĩnh Long province bounding box (viewbox + bounded),
    and every result is re-validated to be inside the box.
  - Rate-limited to ~1 req/sec with a proper User-Agent (Nominatim usage policy).
  - Results (hits AND misses) are cached to disk to avoid repeat lookups.
  - Fully offline-safe: any network/API error returns None (no coords, no crash).
"""

import json
import logging
from contextlib import contextmanager
import os
import time
from pathlib import Path
from threading import Lock
from urllib.parse import urlencode

from pinned_http import EgressPolicy, PinnedHTTPClient

logger = logging.getLogger(__name__)

AGENT_DIR = Path(__file__).resolve().parent
DATA_DIR = AGENT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
CACHE_FILE = DATA_DIR / "geocode_cache.json"

# Bounding box of merged Vĩnh Long (Vĩnh Long + Bến Tre + Trà Vinh).
LAT_MIN, LAT_MAX = 9.40, 10.55
LON_MIN, LON_MAX = 105.70, 106.85
# Nominatim viewbox = left,top,right,bottom = lon_min,lat_max,lon_max,lat_min
_VIEWBOX = f"{LON_MIN},{LAT_MAX},{LON_MAX},{LAT_MIN}"

NOMINATIM = "https://nominatim.openstreetmap.org/search"
NOMINATIM_ORIGIN = "https://nominatim.openstreetmap.org"
USER_AGENT = "vinhlong360-agent/1.0 (tourism knowledge-base geocoder)"
MIN_INTERVAL = 1.1  # seconds between requests (politeness)

_NOMINATIM_EGRESS_POLICY = EgressPolicy(
    max_encoded_bytes=64 * 1024,
    max_decoded_bytes=256 * 1024,
    accepted_encodings=("gzip", "identity"),
    inactivity_timeout_seconds=15.0,
    total_timeout_seconds=15.0,
    max_redirects=2,
    allowed_origins=(NOMINATIM_ORIGIN,),
)
_PINNED_HTTP = PinnedHTTPClient()

_lock = Lock()
_last_request = [0.0]
_cache = None


_cache_lock = Lock()
_cache_stats = {"cache_hits": 0, "duplicate_writes": 0, "lost_update_prevented": 0}


@contextmanager
def _interprocess_file_lock(path: Path):
    """Serialize geocode manifest updates across worker processes."""
    lock_path = path.with_suffix(path.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as handle:
        if os.name == "nt":
            import msvcrt
            handle.seek(0)
            handle.write(b"0")
            handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _load_cache() -> dict:
    global _cache
    if _cache is not None:
        return _cache
    with _cache_lock:
        if _cache is not None:
            return _cache
        if CACHE_FILE.exists():
            try:
                _cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            except Exception as exc:
                logger.warning("Failed to load geocode cache: %s", exc)
                _cache = {}
        else:
            _cache = {}
        return _cache


def _save_cache():
    try:
        with _interprocess_file_lock(CACHE_FILE):
            disk_cache = {}
            if CACHE_FILE.exists():
                try:
                    raw = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
                    if isinstance(raw, dict):
                        disk_cache = raw
                except Exception:
                    disk_cache = {}
            missing_from_memory = set(disk_cache) - set(_cache or {})
            if missing_from_memory:
                _cache_stats["lost_update_prevented"] += len(missing_from_memory)
            merged = {**disk_cache, **(_cache or {})}
            _cache.clear()
            _cache.update(merged)
            tmp = CACHE_FILE.with_suffix(".tmp")
            tmp.write_text(json.dumps(_cache, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(CACHE_FILE)
    except Exception as exc:
        logger.warning("Failed to save geocode cache: %s", exc)


def _norm(text: str) -> str:
    from search_contract import normalize_search_text
    return normalize_search_text(text)


def in_box(lat: float, lon: float) -> bool:
    return LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX


def _query_nominatim(query: str) -> list | None:
    """One rate-limited Nominatim call. Returns [lat, lon] in-box, or None."""
    with _lock:
        wait = MIN_INTERVAL - (time.time() - _last_request[0])
        if wait > 0:
            time.sleep(wait)
        _last_request[0] = time.time()
    try:
        params = urlencode({
            "format": "jsonv2",
            "q": query,
            "limit": 1,
            "viewbox": _VIEWBOX,
            "bounded": 1,
        })
        resp = _PINNED_HTTP.get(
            f"{NOMINATIM}?{params}",
            user_agent=USER_AGENT,
            policy=_NOMINATIM_EGRESS_POLICY,
            audit_context="geocode",
        )
        if resp.status_code != 200:
            return None
        data = json.loads(resp.content)
        if not isinstance(data, list) or not data or not isinstance(data[0], dict):
            return None
        lat, lon = float(data[0]["lat"]), float(data[0]["lon"])
        if in_box(lat, lon):
            return [round(lat, 7), round(lon, 7)]
    except Exception as exc:
        logger.debug("Nominatim query failed for %r: %s", query, exc)
    return None


def geocode(name: str, region: str = "Vĩnh Long", use_cache: bool = True) -> list | None:
    """Return [lat, lon] for a place name within the province, or None.

    Tries "<name>, <region>" first, then "<name>" alone (viewbox keeps it local).
    Caches both hits and misses.
    """
    if not name or len(name.strip()) < 3:
        return None
    cache = _load_cache()
    key = _norm(f"{name}|{region}")
    if key in cache:
        if use_cache:
            _cache_stats["cache_hits"] += 1
            return cache[key]
        _cache_stats["duplicate_writes"] += 1

    coords = _query_nominatim(f"{name}, {region}, Việt Nam")
    if coords is None:
        coords = _query_nominatim(name)

    cache[key] = coords  # cache hits AND misses
    _save_cache()
    return coords


def stats() -> dict:
    cache = _load_cache()
    hits = sum(1 for v in cache.values() if v)
    return {
        "available": True,
        "cached_queries": len(cache),
        "cached_hits": hits,
        "cached_misses": len(cache) - hits,
        "cache_hits": _cache_stats["cache_hits"],
        "duplicate_writes": _cache_stats["duplicate_writes"],
        "lost_update_prevented": _cache_stats["lost_update_prevented"],
        "bbox": {"lat": [LAT_MIN, LAT_MAX], "lon": [LON_MIN, LON_MAX]},
    }


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    for q in ["Chùa Tuyên Linh", "Nhà cổ Huỳnh Phủ", "Biển Thừa Đức Bình Đại"]:
        print(f"{q!r:40} -> {geocode(q)}")
    print("stats:", stats())
