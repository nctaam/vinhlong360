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
import re
import time
import unicodedata
from pathlib import Path

logger = logging.getLogger(__name__)
from threading import Lock

try:
    import requests
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False

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
USER_AGENT = "vinhlong360-agent/1.0 (tourism knowledge-base geocoder)"
MIN_INTERVAL = 1.1  # seconds between requests (politeness)

_lock = Lock()
_last_request = [0.0]
_cache = None


def _load_cache() -> dict:
    global _cache
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
        tmp = CACHE_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(_cache, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(CACHE_FILE)
    except Exception as exc:
        logger.warning("Failed to save geocode cache: %s", exc)


def _norm(text: str) -> str:
    s = unicodedata.normalize("NFD", (text or "").lower())
    s = re.sub(r"[̀-ͯ]", "", s).replace("đ", "d")
    return re.sub(r"\s+", " ", s).strip()


def in_box(lat: float, lon: float) -> bool:
    return LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX


def _query_nominatim(query: str) -> list | None:
    """One rate-limited Nominatim call. Returns [lat, lon] in-box, or None."""
    if not _HAS_REQUESTS:
        return None
    with _lock:
        wait = MIN_INTERVAL - (time.time() - _last_request[0])
        if wait > 0:
            time.sleep(wait)
        _last_request[0] = time.time()
    try:
        resp = requests.get(
            NOMINATIM,
            params={"format": "jsonv2", "q": query, "limit": 1,
                    "viewbox": _VIEWBOX, "bounded": 1},
            headers={"User-Agent": USER_AGENT},
            timeout=15,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        if not data:
            return None
        lat, lon = float(data[0]["lat"]), float(data[0]["lon"])
        if in_box(lat, lon):
            return [round(lat, 7), round(lon, 7)]
    except Exception as exc:
        logger.debug("Geocode API failed for %s: %s", name, exc)
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
    if use_cache and key in cache:
        return cache[key]

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
        "available": _HAS_REQUESTS,
        "cached_queries": len(cache),
        "cached_hits": hits,
        "cached_misses": len(cache) - hits,
        "bbox": {"lat": [LAT_MIN, LAT_MAX], "lon": [LON_MIN, LON_MAX]},
    }


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    for q in ["Chùa Tuyên Linh", "Nhà cổ Huỳnh Phủ", "Biển Thừa Đức Bình Đại"]:
        print(f"{q!r:40} -> {geocode(q)}")
    print("stats:", stats())
