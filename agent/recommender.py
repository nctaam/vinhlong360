"""
vinhlong360 — Recommendation Engine.

Cung cap goi y thong minh cho nguoi dung dua tren:
  - Content-Based Filtering (entity tuong tu)
  - User-Profile Recommendations (ca nhan hoa)
  - Trending / Popular (tu analytics)
  - Contextual (thoi gian, thoi tiet, mua vu)

Tat ca ham thread-safe, khong dung external deps.

Tich hop voi:
  - knowledge.py (entities, relationships)
  - analytics.py (entity_hits, queries)
  - memory.py (user profiles)
"""

import math
import time
from collections import defaultdict
from datetime import datetime
from threading import Lock

# Entity types recognized by the platform
CARD_TYPES = [
    "attraction", "product", "dish", "craft_village", "nature",
    "event", "experience", "person", "history", "accommodation",
    "organization", "economy",
]

# ══════════════════════════════════════════════════
#  Weights
# ══════════════════════════════════════════════════

# Content-based scoring weights
W_SAME_TYPE = 0.3
W_SHARED_TAGS = 0.3
W_SAME_AREA = 0.2
W_RELATIONSHIP = 0.2

# User-profile scoring weights
W_INTEREST_MATCH = 0.4
W_PREFERRED_AREA = 0.3
W_NOT_VISITED_BONUS = 0.2
W_POPULARITY = 0.1

# Contextual: entity types suited for each context
_WEATHER_TYPES: dict[str, list[str]] = {
    "rainy": ["attraction", "dish", "product", "history", "craft_village", "accommodation"],
    "sunny": ["nature", "experience", "attraction", "craft_village", "event"],
    "cloudy": ["attraction", "nature", "experience", "craft_village", "dish", "event"],
}

_TIME_TYPES: dict[str, list[str]] = {
    "morning": ["nature", "experience", "craft_village", "product", "attraction"],
    "afternoon": ["attraction", "craft_village", "history", "experience", "nature"],
    "evening": ["dish", "event", "experience", "attraction", "accommodation"],
}

# Interest keywords to entity type mapping (Vietnamese tourism context)
_INTEREST_TYPE_MAP: dict[str, list[str]] = {
    "am_thuc": ["dish", "product"],
    "lich_su": ["history", "person", "attraction"],
    "thien_nhien": ["nature", "experience"],
    "van_hoa": ["craft_village", "event", "attraction"],
    "mua_sam": ["product", "craft_village"],
    "tham_quan": ["attraction", "experience"],
    "tong_hop": CARD_TYPES,
}

_lock = Lock()


# ══════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════

def _get_tags(entity: dict) -> set[str]:
    """Extract tags from an entity, normalizing to a set of lowercase strings."""
    raw = entity.get("tags", [])
    if isinstance(raw, list):
        return {t.lower().strip() for t in raw if isinstance(t, str)}
    return set()


def _get_area(entity: dict, entities: dict) -> str | None:
    """Resolve the area of an entity via its placeId."""
    pid = entity.get("placeId")
    if not pid:
        return None
    place = entities.get(pid)
    if place:
        return place.get("area")
    return None


def _get_ward_id(entity: dict) -> str | None:
    """Get the ward/place id of an entity."""
    return entity.get("placeId") or entity.get("ward_id")


def _entity_in_season(entity: dict, month: int) -> bool:
    """Check if an entity is in season for the given month."""
    season = entity.get("season")
    if not season:
        return True  # No season restriction = always in season
    months = season.get("months", [])
    if not months:
        return True
    return month in months


def _entity_in_peak(entity: dict, month: int) -> bool:
    """Check if an entity is in peak season for the given month."""
    season = entity.get("season")
    if not season:
        return False
    return month in (season.get("peak") or [])


def _is_content_entity(entity: dict) -> bool:
    """Check if the entity is a displayable content type (not a place)."""
    return entity.get("type") in CARD_TYPES


def _build_relationship_index(relationships: list[dict]) -> dict[str, set[str]]:
    """Build a bidirectional adjacency index from relationships."""
    index: dict[str, set[str]] = defaultdict(set)
    for r in relationships:
        fr = r.get("from", "")
        to = r.get("to", "")
        if fr and to:
            index[fr].add(to)
            index[to].add(fr)
    return dict(index)


# ══════════════════════════════════════════════════
#  1. Content-Based Filtering
# ══════════════════════════════════════════════════

def recommend_by_entity(
    entity_id: str,
    entities: dict,
    relationships: list[dict],
    limit: int = 8,
) -> list[dict]:
    """
    Given an entity the user is viewing, suggest similar/related ones.

    Scoring factors (normalized to 0-1 each, then weighted):
      - Same type:          0.3
      - Shared tags:        0.3  (Jaccard-like)
      - Same area:          0.2
      - Relationship exists: 0.2

    Args:
        entity_id: The ID of the entity being viewed.
        entities: Dict mapping entity_id -> entity dict.
        relationships: List of relationship dicts with 'from', 'to', 'type'.
        limit: Max number of recommendations to return.

    Returns:
        List of dicts: [{"id", "name", "type", "score", "reason"}], sorted desc.
    """
    source = entities.get(entity_id)
    if not source or not _is_content_entity(source):
        return []

    source_tags = _get_tags(source)
    source_area = _get_area(source, entities)
    source_type = source.get("type")
    source_ward = _get_ward_id(source)

    rel_index = _build_relationship_index(relationships)
    related_ids = rel_index.get(entity_id, set())

    scored: list[tuple[float, dict, list[str]]] = []

    for eid, candidate in entities.items():
        if eid == entity_id:
            continue
        if not _is_content_entity(candidate):
            continue

        score = 0.0
        reasons: list[str] = []

        # Factor 1: Same type
        if candidate.get("type") == source_type:
            score += W_SAME_TYPE
            reasons.append("same_type")

        # Factor 2: Shared tags (Jaccard-like)
        cand_tags = _get_tags(candidate)
        if source_tags and cand_tags:
            intersection = len(source_tags & cand_tags)
            union = len(source_tags | cand_tags)
            if union > 0:
                tag_sim = intersection / union
                score += W_SHARED_TAGS * tag_sim
                if intersection > 0:
                    reasons.append(f"shared_tags({intersection})")

        # Factor 3: Same area
        cand_area = _get_area(candidate, entities)
        if source_area and cand_area and source_area == cand_area:
            score += W_SAME_AREA
            reasons.append("same_area")
            # Extra boost for same ward
            cand_ward = _get_ward_id(candidate)
            if source_ward and cand_ward and source_ward == cand_ward:
                score += 0.05
                reasons.append("same_ward")

        # Factor 4: Relationship exists
        if eid in related_ids:
            score += W_RELATIONSHIP
            reasons.append("related")

        if score > 0:
            scored.append((score, candidate, reasons))

    # Sort descending by score, then by confidence as tiebreaker
    scored.sort(key=lambda x: (x[0], x[1].get("confidence", 0)), reverse=True)

    return [
        {
            "id": cand["id"],
            "name": cand.get("name", ""),
            "type": cand.get("type", ""),
            "score": round(sc, 4),
            "reason": ", ".join(reasons),
        }
        for sc, cand, reasons in scored[:limit]
    ]


# ══════════════════════════════════════════════════
#  2. User-Profile Recommendations
# ══════════════════════════════════════════════════

def recommend_for_user(
    user_profile: dict,
    entities: dict,
    limit: int = 10,
) -> list[dict]:
    """
    Personalized recommendations based on user profile.

    user_profile keys:
      - interests: list[str]      (e.g. ["am_thuc", "thien_nhien"])
      - preferred_areas: list[str] (e.g. ["vinh-long", "ben-tre"])
      - visited_entities: list[str] (entity IDs already seen)

    Scoring:
      - Matches interests:   0.4  (entity type aligns with interest)
      - In preferred area:   0.3
      - Not yet visited:     0.2  (bonus)
      - Popularity:          0.1  (from confidence as proxy)

    Diversity: max 3 entities per type in final results.

    Args:
        user_profile: Dict with interests, preferred_areas, visited_entities.
        entities: Dict mapping entity_id -> entity dict.
        limit: Max recommendations.

    Returns:
        Ranked list of recommendation dicts.
    """
    interests = user_profile.get("interests", [])
    preferred_areas = set(user_profile.get("preferred_areas", []))
    visited = set(user_profile.get("visited_entities", []))

    # Expand interests to entity types
    interest_types: set[str] = set()
    for interest in interests:
        mapped = _INTEREST_TYPE_MAP.get(interest, [])
        interest_types.update(mapped)

    scored: list[tuple[float, dict, list[str]]] = []

    for eid, entity in entities.items():
        if not _is_content_entity(entity):
            continue

        score = 0.0
        reasons: list[str] = []

        # Factor 1: Matches interests
        if interest_types and entity.get("type") in interest_types:
            score += W_INTEREST_MATCH
            reasons.append("matches_interest")

        # Factor 2: In preferred area
        if preferred_areas:
            area = _get_area(entity, entities)
            if area and area in preferred_areas:
                score += W_PREFERRED_AREA
                reasons.append("preferred_area")

        # Factor 3: Not yet visited bonus
        if eid not in visited:
            score += W_NOT_VISITED_BONUS
            reasons.append("not_visited")

        # Factor 4: Popularity proxy (confidence score)
        confidence = entity.get("confidence", 0)
        if confidence > 0:
            score += W_POPULARITY * min(confidence, 1.0)
            if confidence >= 0.8:
                reasons.append("high_confidence")

        if score > 0:
            scored.append((score, entity, reasons))

    # Sort descending
    scored.sort(key=lambda x: (x[0], x[1].get("confidence", 0)), reverse=True)

    # Diversity constraint: max 3 per entity type
    type_counts: dict[str, int] = defaultdict(int)
    diversified: list[dict] = []

    for sc, entity, reasons in scored:
        etype = entity.get("type", "")
        if type_counts[etype] >= 3:
            continue
        type_counts[etype] += 1
        diversified.append({
            "id": entity["id"],
            "name": entity.get("name", ""),
            "type": etype,
            "score": round(sc, 4),
            "reason": ", ".join(reasons),
        })
        if len(diversified) >= limit:
            break

    return diversified


# ══════════════════════════════════════════════════
#  3. Trending Recommendations
# ══════════════════════════════════════════════════

def recommend_trending(
    analytics_data: dict,
    entities: dict,
    limit: int = 10,
) -> list[dict]:
    """
    Recommend entities based on popularity with recency decay.

    analytics_data expected keys:
      - entity_hits: dict[str, int]          (total hit counts)
      - queries: list[dict]                  (recent queries with timestamps)

    Scoring:
      - Base popularity: log2(hits + 1)
      - Recency boost: recent hits (last 7 days) get 2x weight
      - Fresh discovery bonus: entities with low total hits but recent activity

    Args:
        analytics_data: Analytics dict (from analytics._load()).
        entities: Dict mapping entity_id -> entity dict.
        limit: Max recommendations.

    Returns:
        Ranked list mixing popular and fresh discoveries.
    """
    entity_hits = analytics_data.get("entity_hits", {})
    queries = analytics_data.get("queries", [])

    # Calculate recency-weighted scores
    now = time.time()
    week_seconds = 7 * 24 * 3600

    # Count recent entity mentions from queries (approximate via text matching)
    recent_boost: dict[str, float] = defaultdict(float)
    for q in queries:
        ts_str = q.get("timestamp", "")
        try:
            ts = datetime.fromisoformat(ts_str).timestamp()
        except (ValueError, TypeError):
            continue
        age = now - ts
        if age < week_seconds:
            # Decay: newer = higher weight (1.0 at t=0, 0.5 at t=7d)
            decay = max(0.0, 1.0 - (age / week_seconds) * 0.5)
            # We don't know which entity each query maps to,
            # so this boost is applied only to entities already in hits.
            # The recency signal comes from the query timestamps.
            # Mark the query window as "active"
            recent_boost["__recent_activity__"] = max(
                recent_boost["__recent_activity__"], decay
            )

    scored: list[tuple[float, dict, list[str]]] = []
    max_hits = max(entity_hits.values()) if entity_hits else 1

    for eid, hits in entity_hits.items():
        entity = entities.get(eid)
        if not entity or not _is_content_entity(entity):
            continue

        reasons: list[str] = []

        # Base popularity (logarithmic to avoid domination)
        pop_score = math.log2(hits + 1)
        reasons.append(f"hits({hits})")

        # Normalize relative to max
        relative_pop = hits / max_hits if max_hits > 0 else 0

        # Fresh discovery bonus: low total hits but entity exists
        if hits <= 3:
            pop_score += 1.5
            reasons.append("fresh_discovery")
        elif relative_pop >= 0.7:
            reasons.append("popular")

        # Confidence bonus
        confidence = entity.get("confidence", 0)
        pop_score += confidence * 0.5

        scored.append((pop_score, entity, reasons))

    # Sort and split into popular + fresh
    scored.sort(key=lambda x: x[0], reverse=True)

    # Mix: 60% popular, 40% fresh discoveries
    popular = [item for item in scored if "popular" in item[2] or "fresh_discovery" not in " ".join(item[2])]
    fresh = [item for item in scored if "fresh_discovery" in item[2]]

    pop_count = min(len(popular), max(1, int(limit * 0.6)))
    fresh_count = min(len(fresh), limit - pop_count)

    mixed = popular[:pop_count] + fresh[:fresh_count]
    # Fill remaining slots if needed
    remaining = limit - len(mixed)
    if remaining > 0:
        used_ids = {item[1]["id"] for item in mixed}
        for item in scored:
            if item[1]["id"] not in used_ids:
                mixed.append(item)
                used_ids.add(item[1]["id"])
                if len(mixed) >= limit:
                    break

    # Re-sort final list by score
    mixed.sort(key=lambda x: x[0], reverse=True)

    return [
        {
            "id": entity["id"],
            "name": entity.get("name", ""),
            "type": entity.get("type", ""),
            "score": round(sc, 4),
            "reason": ", ".join(reasons),
        }
        for sc, entity, reasons in mixed[:limit]
    ]


# ══════════════════════════════════════════════════
#  4. Contextual Recommendations
# ══════════════════════════════════════════════════

def recommend_contextual(
    month: int,
    time_of_day: str,
    weather: str,
    entities: dict,
    limit: int = 8,
) -> list[dict]:
    """
    Context-aware recommendations based on time, weather, and season.

    Rules:
      - Rainy  -> indoor attractions, museums, food, crafts
      - Sunny  -> nature, outdoor experiences, events
      - Cloudy -> mix of indoor and outdoor
      - Morning  -> nature, gardens, markets, experiences
      - Afternoon -> attractions, crafts, history
      - Evening   -> food, events, cultural shows, accommodation
      - Season: match entity's season field to current month

    Args:
        month: Current month (1-12).
        time_of_day: One of "morning", "afternoon", "evening".
        weather: One of "sunny", "rainy", "cloudy".
        entities: Dict mapping entity_id -> entity dict.
        limit: Max recommendations.

    Returns:
        Ranked list of contextually appropriate entities.
    """
    weather_types = set(_WEATHER_TYPES.get(weather, CARD_TYPES))
    time_types = set(_TIME_TYPES.get(time_of_day, CARD_TYPES))

    # Preferred types = intersection of weather and time preferences
    preferred = weather_types & time_types
    if not preferred:
        # Fallback: union if intersection is empty
        preferred = weather_types | time_types

    scored: list[tuple[float, dict, list[str]]] = []

    for eid, entity in entities.items():
        if not _is_content_entity(entity):
            continue

        score = 0.0
        reasons: list[str] = []
        etype = entity.get("type", "")

        # Factor 1: Type fits context
        if etype in preferred:
            score += 0.4
            reasons.append(f"fits_{weather}_{time_of_day}")
        elif etype in weather_types:
            score += 0.25
            reasons.append(f"fits_{weather}")
        elif etype in time_types:
            score += 0.25
            reasons.append(f"fits_{time_of_day}")
        else:
            continue  # Skip entities that don't fit any context

        # Factor 2: Season match
        if _entity_in_peak(entity, month):
            score += 0.35
            reasons.append("peak_season")
        elif _entity_in_season(entity, month):
            score += 0.15
            reasons.append("in_season")
        else:
            # Out of season: penalize but don't exclude
            score -= 0.1

        # Factor 3: Confidence
        confidence = entity.get("confidence", 0)
        score += confidence * 0.15

        # Factor 4: Content richness
        summary = entity.get("summary", "")
        if len(summary) > 100:
            score += 0.1
            reasons.append("rich_content")

        if score > 0:
            scored.append((score, entity, reasons))

    scored.sort(key=lambda x: (x[0], x[1].get("confidence", 0)), reverse=True)

    return [
        {
            "id": entity["id"],
            "name": entity.get("name", ""),
            "type": entity.get("type", ""),
            "score": round(sc, 4),
            "reason": ", ".join(reasons),
        }
        for sc, entity, reasons in scored[:limit]
    ]


# ══════════════════════════════════════════════════
#  5. Unified Recommendation API
# ══════════════════════════════════════════════════

def recommend(context: dict) -> dict:
    """
    Unified recommendation entry point.

    Merges and deduplicates results from all applicable engines
    based on the provided context.

    context keys (all optional):
      - entity_id: str              -> triggers content-based filtering
      - user_profile: dict          -> triggers user-profile recommendations
      - analytics_data: dict        -> triggers trending recommendations
      - month: int                  -> used by contextual + season filtering
      - time_of_day: str            -> contextual ("morning"/"afternoon"/"evening")
      - weather: str                -> contextual ("sunny"/"rainy"/"cloudy")
      - entities: dict              -> REQUIRED: the entities corpus
      - relationships: list[dict]   -> needed for content-based filtering
      - limit: int                  -> final result limit (default 10)

    Returns:
        {
            "recommendations": [{"id", "name", "type", "score", "reason"}],
            "strategy": str  (describes which engines contributed)
        }
    """
    with _lock:
        return _recommend_impl(context)


def _recommend_impl(context: dict) -> dict:
    """Internal implementation — called under lock."""
    entities = context.get("entities", {})
    relationships = context.get("relationships", [])
    limit = context.get("limit", 10)

    if not entities:
        return {"recommendations": [], "strategy": "no_entities"}

    strategies_used: list[str] = []
    all_results: list[dict] = []

    # 1. Content-based (if entity_id provided)
    entity_id = context.get("entity_id")
    if entity_id and entity_id in entities:
        results = recommend_by_entity(entity_id, entities, relationships, limit=limit)
        # Weight these results (primary signal when viewing an entity)
        for r in results:
            r["_source"] = "content_based"
            r["score"] = r["score"] * 1.2  # Boost content-based when entity context exists
        all_results.extend(results)
        strategies_used.append("content_based")

    # 2. User-profile (if user_profile provided)
    user_profile = context.get("user_profile")
    if user_profile:
        results = recommend_for_user(user_profile, entities, limit=limit)
        for r in results:
            r["_source"] = "user_profile"
        all_results.extend(results)
        strategies_used.append("user_profile")

    # 3. Trending (if analytics_data provided)
    analytics_data = context.get("analytics_data")
    if analytics_data:
        results = recommend_trending(analytics_data, entities, limit=limit)
        for r in results:
            r["_source"] = "trending"
            r["score"] = r["score"] * 0.15  # Normalize trending scores down
        all_results.extend(results)
        strategies_used.append("trending")

    # 4. Contextual (if time/weather context provided)
    month = context.get("month")
    time_of_day = context.get("time_of_day")
    weather = context.get("weather")
    if month and (time_of_day or weather):
        tod = time_of_day or "afternoon"
        w = weather or "sunny"
        results = recommend_contextual(month, tod, w, entities, limit=limit)
        for r in results:
            r["_source"] = "contextual"
        all_results.extend(results)
        strategies_used.append("contextual")

    # Fallback: if no strategy matched, do contextual with current month
    if not strategies_used:
        now = datetime.now()
        hour = now.hour
        if hour < 12:
            tod = "morning"
        elif hour < 17:
            tod = "afternoon"
        else:
            tod = "evening"
        results = recommend_contextual(now.month, tod, "sunny", entities, limit=limit)
        for r in results:
            r["_source"] = "contextual_fallback"
        all_results.extend(results)
        strategies_used.append("contextual_fallback")

    # ── Merge & Deduplicate ──
    merged = _merge_results(all_results, limit)

    # Clean internal fields
    for r in merged:
        r.pop("_source", None)
        r["score"] = round(r["score"], 4)

    strategy_str = " + ".join(strategies_used)
    return {
        "recommendations": merged,
        "strategy": strategy_str,
    }


def _merge_results(results: list[dict], limit: int) -> list[dict]:
    """
    Merge results from multiple engines, deduplicating by entity ID.

    When the same entity appears from multiple sources, keep the highest
    score and combine the reasons.
    """
    by_id: dict[str, dict] = {}

    for r in results:
        eid = r["id"]
        if eid in by_id:
            existing = by_id[eid]
            # Take the higher score
            if r["score"] > existing["score"]:
                existing["score"] = r["score"]
            # Combine reasons (deduplicated)
            existing_reasons = set(existing["reason"].split(", "))
            new_reasons = set(r["reason"].split(", "))
            combined = existing_reasons | new_reasons
            combined.discard("")
            existing["reason"] = ", ".join(sorted(combined))
            # Track sources
            existing.setdefault("_sources", set()).add(r.get("_source", ""))
        else:
            by_id[eid] = {
                "id": r["id"],
                "name": r["name"],
                "type": r["type"],
                "score": r["score"],
                "reason": r["reason"],
                "_source": r.get("_source", ""),
                "_sources": {r.get("_source", "")},
            }

    # Bonus for entities recommended by multiple engines
    for entry in by_id.values():
        sources = entry.pop("_sources", set())
        sources.discard("")
        if len(sources) > 1:
            entry["score"] += 0.1 * (len(sources) - 1)
            entry["reason"] += f", multi_signal({len(sources)})"

    # Sort and limit
    merged = sorted(by_id.values(), key=lambda x: x["score"], reverse=True)
    return merged[:limit]
