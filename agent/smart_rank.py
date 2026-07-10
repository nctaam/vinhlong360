"""
vinhlong360 — Smart Ranking Engine.

Tích hợp dữ liệu analytics (popularity) vào scoring khi search.
Entities được hỏi nhiều → xếp hạng cao hơn.
"""

import json
import logging
import time
from pathlib import Path
from threading import Lock

logger = logging.getLogger(__name__)

ANALYTICS_FILE = Path(__file__).resolve().parent / "data" / "analytics.json"

_popularity: dict[str, int] = {}
_last_load: float = 0
_lock = Lock()
RELOAD_INTERVAL = 300  # 5 phút


def _load_popularity():
    """Load entity popularity from analytics data."""
    global _popularity, _last_load
    try:
        if ANALYTICS_FILE.exists():
            data = json.loads(ANALYTICS_FILE.read_text(encoding="utf-8"))
            _popularity = data.get("entity_hits", {})
            _last_load = time.time()
    except Exception as exc:
        logger.warning("Failed to load popularity data: %s", exc)


def get_popularity(entity_id: str) -> int:
    """Get hit count for an entity."""
    with _lock:
        if time.time() - _last_load > RELOAD_INTERVAL:
            _load_popularity()
        return _popularity.get(entity_id, 0)


def popularity_score(entity_id: str, max_boost: float = 3.0) -> float:
    """
    Tính popularity bonus (0 → max_boost).
    Dùng logarithmic scale để tránh entities quá popular chi phối.
    """
    import math
    hits = get_popularity(entity_id)
    if hits <= 0:
        return 0
    # log2(hits + 1) capped at max_boost
    return min(math.log2(hits + 1), max_boost)


def _season_bonus(entity: dict, month: int) -> float:
    """Season match bonus (+5 peak, +2 in-season)."""
    if not month:
        return 0.0
    season = entity.get("season")
    if season and isinstance(season, dict):
        peak = season.get("peak", [])
        months = season.get("months", [])
        if month in peak:
            return 5.0
        elif month in months:
            return 2.0
    return 0.0


def _richness_bonus(summary_len: int, attrs: dict) -> float:
    """Content richness (+0-2) from summary length and attribute count."""
    bonus = 0.0
    if summary_len > 50:
        bonus += 0.5
    if summary_len > 100:
        bonus += 0.5
    if summary_len > 200:
        bonus += 0.5
    if len(attrs) > 2:
        bonus += 0.5
    return bonus


def _query_match_bonus(q_match_level: str) -> float:
    """Query match level (+3 exact, +1 fuzzy)."""
    if q_match_level == "exact":
        return 3.0
    elif q_match_level == "fuzzy":
        return 1.0
    return 0.0


_TYPE_BONUS = {
    "attraction": 1.0,
    "experience": 1.0,
    "dish": 0.8,
    "nature": 0.8,
    "craft_village": 0.7,
    "product": 0.5,
    "history": 0.6,
    "person": 0.3,
    "event": 0.5,
    "accommodation": 0.3,
    "economy": 0.2,
}


def _verification_bonus(entity: dict) -> float:
    """Verification bonus (+2 verified, -2 provisional/unverified)."""
    if entity.get("verified") is True:
        return 2.0
    elif entity.get("status") == "provisional" or entity.get("verified") is False:
        return -2.0
    return 0.0


def _gps_bonus(entity: dict) -> float:
    """GPS completeness bonus."""
    if entity.get("coords") or entity.get("coordinates"):
        return 0.5
    return 0.0


def smart_score(entity: dict, month: int = None, q_match_level: str = "exact") -> float:
    """
    Tính tổng điểm xếp hạng thông minh.

    Factors:
      1. Season match bonus (+5 peak, +2 in-season)
      2. Popularity bonus (0-3, log scale)
      3. Content richness (+0-2)
      4. Query match level (+3 exact, +1 fuzzy)
      5. OCOP bonus (+1.5)
      6. Type bonus (attraction/experience slightly higher)
    """
    score = 0.0

    # 1. Season
    score += _season_bonus(entity, month)

    # 2. Popularity
    score += popularity_score(entity["id"])

    # 3. Content richness
    summary_len = len(entity.get("summary", ""))
    attrs = entity.get("attributes", {})
    score += _richness_bonus(summary_len, attrs)

    # 4. Query match
    score += _query_match_bonus(q_match_level)

    # 5. OCOP
    if attrs.get("ocop"):
        score += 1.5

    # 6. Type bonus (popular types slightly higher)
    score += _TYPE_BONUS.get(entity["type"], 0)

    # 7. Verification bonus
    score += _verification_bonus(entity)

    # 8. GPS completeness bonus
    score += _gps_bonus(entity)

    return round(score, 2)


def rank_entities(entities: list[dict], month: int = None, query: str = None) -> list[dict]:
    """
    Re-rank a list of entities using smart scoring.
    Returns entities sorted by smart_score descending.
    """
    scored = []
    for e in entities:
        match_level = "exact"  # Assume they passed through search filter
        s = smart_score(e, month=month, q_match_level=match_level)
        scored.append((s, e))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [e for _, e in scored]
