#!/usr/bin/env python3
"""
find_duplicates.py — Tìm tất cả cặp entity trùng/gần trùng trong web/data.json.

Chiến lược phát hiện:
  1. Exact name match (case-insensitive)
  2. Near-match: normalize (lowercase, bỏ dấu, bỏ ngoặc alias) rồi so
  3. Same-address match: entities cùng address (sau normalize)
  4. Same name + different type

Mỗi cặp tính confidence score dựa trên:
  - Name similarity (Jaccard on words)
  - Same address
  - Same placeId
  - Same coordinates (within ~50m)
  - Same area

Output: danh sách cặp, sắp theo confidence giảm dần, kèm gợi ý giữ entity nào.
"""

import json
import sys
import os
import re
import unicodedata
from collections import Counter, defaultdict
from itertools import combinations
from math import radians, cos, sin, asin, sqrt

# ------------------------------------------------------------------
# Setup
# ------------------------------------------------------------------
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "web", "data.json")
with open(DATA_PATH, encoding="utf-8-sig") as f:
    data = json.load(f)

entities = data["entities"]
relationships = data["relationships"]
by_id = {e["id"]: e for e in entities}

# Pre-compute relationship counts per entity
rel_count = Counter()
for r in relationships:
    rel_count[r.get("from", "")] += 1
    rel_count[r.get("to", "")] += 1


# ------------------------------------------------------------------
# Normalization helpers
# ------------------------------------------------------------------
def remove_diacritics(s: str) -> str:
    """Remove Vietnamese diacritics: 'Vĩnh Long' -> 'Vinh Long'."""
    # Special Vietnamese chars that NFD doesn't fully handle
    s = s.replace("đ", "d").replace("Đ", "D")
    nfkd = unicodedata.normalize("NFD", s)
    return "".join(c for c in nfkd if unicodedata.category(c) != "Mn")


def remove_parenthetical(s: str) -> str:
    """Remove content in parentheses: 'Chùa Ông (Thất Phủ Miếu)' -> 'Chùa Ông'."""
    return re.sub(r"\s*\([^)]*\)", "", s).strip()


def normalize_name(name: str) -> str:
    """Lowercase, remove diacritics, remove parenthetical aliases, collapse whitespace."""
    s = name.lower().strip()
    s = remove_parenthetical(s)
    s = remove_diacritics(s)
    # Remove punctuation (hyphens, quotes, etc.)
    s = re.sub(r"[''\"''\-–—]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def normalize_address(addr: str) -> str:
    """Normalize address for comparison: lowercase, remove diacritics, strip common noise."""
    if not addr:
        return ""
    s = addr.lower().strip()
    s = remove_diacritics(s)
    # Remove common prefixes/noise
    for noise in ["tinh ", "huyen ", "thanh pho ", "tp ", "xa ", "phuong ", "thi tran ",
                   "khom ", "ap ", "duong ", "quoc lo "]:
        s = s.replace(noise, "")
    s = re.sub(r"[,.\-–—()]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def jaccard_words(a: str, b: str) -> float:
    """Jaccard similarity on word sets."""
    wa = set(a.split())
    wb = set(b.split())
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def haversine_m(lat1, lon1, lat2, lon2):
    """Distance in meters between two lat/lon points."""
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * 6371000 * asin(sqrt(a))


def get_coords(e):
    """Return (lat, lon) or None."""
    c = e.get("coordinates")
    if c and isinstance(c, list) and len(c) == 2:
        lat, lon = c
        # Filter out default/zero coords
        if lat and lon and abs(lat) > 0.1 and abs(lon) > 0.1:
            return (lat, lon)
    return None


def get_address(e):
    return (e.get("attributes") or {}).get("address", "") or ""


def entity_richness(e):
    """Score how 'rich' an entity is — more data = prefer to keep."""
    score = 0
    score += rel_count.get(e["id"], 0) * 3  # relationships are very valuable
    if e.get("summary"):
        score += min(len(e["summary"]), 200) / 20  # summary length, capped
    if e.get("description"):
        score += min(len(e["description"]), 200) / 20
    if get_coords(e):
        score += 5
    if get_address(e):
        score += 3
    if e.get("placeId"):
        score += 2
    if e.get("images"):
        score += len(e["images"]) * 2
    if e.get("source"):
        score += len(e["source"])
    attrs = e.get("attributes") or {}
    score += len([v for v in attrs.values() if v]) * 0.5
    if e.get("verifiedAt"):
        score += 1
    return score


# ------------------------------------------------------------------
# Build indexes for candidate generation
# ------------------------------------------------------------------
print("Building indexes...\n")

# Skip itinerary entities (they are content, not places)
non_itinerary = [e for e in entities if e.get("type") != "itinerary"]

# Index: normalized name -> list of entities
by_norm_name = defaultdict(list)
# Index: exact lowercase name -> list of entities
by_exact_lower = defaultdict(list)
# Index: normalized address -> list of entities
by_norm_addr = defaultdict(list)

for e in non_itinerary:
    name = e.get("name", "")
    by_exact_lower[name.lower().strip()].append(e)
    by_norm_name[normalize_name(name)].append(e)

    addr = normalize_address(get_address(e))
    if addr and len(addr) > 5:  # only meaningful addresses
        by_norm_addr[addr].append(e)


# ------------------------------------------------------------------
# Candidate pair generation
# ------------------------------------------------------------------
candidate_pairs = {}  # (id_a, id_b) -> reason


def add_pair(a, b, reason):
    key = tuple(sorted([a["id"], b["id"]]))
    if key not in candidate_pairs:
        candidate_pairs[key] = set()
    candidate_pairs[key].add(reason)


# 1. Exact name match (case-insensitive)
for name_lower, group in by_exact_lower.items():
    if len(group) > 1:
        for a, b in combinations(group, 2):
            add_pair(a, b, "exact_name")

# 2. Near-match on normalized name
for norm, group in by_norm_name.items():
    if len(group) > 1:
        for a, b in combinations(group, 2):
            add_pair(a, b, "normalized_name")

# 3. Same normalized address
for addr, group in by_norm_addr.items():
    if len(group) > 1:
        for a, b in combinations(group, 2):
            # Only pair if names are at least somewhat similar
            name_sim = jaccard_words(normalize_name(a["name"]), normalize_name(b["name"]))
            if name_sim > 0.15:  # at least some word overlap
                add_pair(a, b, "same_address")

# 4. Fuzzy: compare entities with high Jaccard on normalized name words
# We only compare within same area to limit N^2 explosion
by_area = defaultdict(list)
for e in non_itinerary:
    area = e.get("area", "unknown")
    by_area[area].append(e)

for area, group in by_area.items():
    if len(group) > 500:
        continue  # skip huge groups for performance
    for i, a in enumerate(group):
        norm_a = normalize_name(a["name"])
        for b in group[i + 1:]:
            norm_b = normalize_name(b["name"])
            sim = jaccard_words(norm_a, norm_b)
            if sim >= 0.55:  # high word overlap
                add_pair(a, b, "fuzzy_name")

# 5. Cross-type: same or very similar name but different types
# Already covered by strategies above, but let's explicitly flag them
for norm, group in by_norm_name.items():
    types_in_group = set(e["type"] for e in group)
    if len(group) > 1 and len(types_in_group) > 1:
        for a, b in combinations(group, 2):
            if a["type"] != b["type"]:
                add_pair(a, b, "cross_type")


# ------------------------------------------------------------------
# Score each candidate pair
# ------------------------------------------------------------------
results = []

for (id_a, id_b), reasons in candidate_pairs.items():
    a = by_id[id_a]
    b = by_id[id_b]

    score = 0.0
    details = []

    # --- Name similarity ---
    norm_a = normalize_name(a["name"])
    norm_b = normalize_name(b["name"])
    name_jaccard = jaccard_words(norm_a, norm_b)

    # Exact name match (case-insensitive)
    if a["name"].lower().strip() == b["name"].lower().strip():
        score += 40
        details.append("exact_name_match")
    # Normalized name match (no diacritics, no parens)
    elif norm_a == norm_b:
        score += 35
        details.append(f"normalized_name_match")
    elif name_jaccard >= 0.7:
        score += name_jaccard * 30
        details.append(f"name_jaccard={name_jaccard:.2f}")
    elif name_jaccard >= 0.55:
        score += name_jaccard * 20
        details.append(f"name_jaccard={name_jaccard:.2f}")
    else:
        score += name_jaccard * 10
        details.append(f"name_jaccard={name_jaccard:.2f}")

    # --- Same address ---
    addr_a = normalize_address(get_address(a))
    addr_b = normalize_address(get_address(b))
    if addr_a and addr_b:
        if addr_a == addr_b:
            score += 25
            details.append("same_address")
        else:
            addr_jaccard = jaccard_words(addr_a, addr_b)
            if addr_jaccard > 0.5:
                score += addr_jaccard * 15
                details.append(f"addr_jaccard={addr_jaccard:.2f}")

    # --- Same placeId ---
    pid_a = a.get("placeId") or ""
    pid_b = b.get("placeId") or ""
    if pid_a and pid_b and pid_a == pid_b:
        score += 15
        details.append("same_placeId")

    # --- Same/close coordinates ---
    ca = get_coords(a)
    cb = get_coords(b)
    if ca and cb:
        dist = haversine_m(ca[0], ca[1], cb[0], cb[1])
        if dist < 50:
            score += 20
            details.append(f"coords_within_50m ({dist:.0f}m)")
        elif dist < 200:
            score += 12
            details.append(f"coords_within_200m ({dist:.0f}m)")
        elif dist < 500:
            score += 5
            details.append(f"coords_within_500m ({dist:.0f}m)")

    # --- Same area ---
    area_a = a.get("area", "")
    area_b = b.get("area", "")
    if area_a and area_b and area_a == area_b:
        score += 5
        details.append("same_area")

    # --- Cross-type bonus (suspicious: same place in two categories) ---
    if a["type"] != b["type"]:
        details.append(f"CROSS_TYPE: {a['type']} vs {b['type']}")

    # --- Same type (stronger signal if names match) ---
    if a["type"] == b["type"]:
        score += 3
        details.append(f"same_type: {a['type']}")

    # Filter out low-confidence pairs
    if score < 20:
        continue

    # --- Decide which to keep ---
    rich_a = entity_richness(a)
    rich_b = entity_richness(b)
    if rich_a >= rich_b:
        keep, drop = a, b
        keep_score, drop_score = rich_a, rich_b
    else:
        keep, drop = b, a
        keep_score, drop_score = rich_b, rich_a

    results.append({
        "confidence": round(score, 1),
        "a_id": a["id"],
        "a_name": a["name"],
        "a_type": a["type"],
        "b_id": b["id"],
        "b_name": b["name"],
        "b_type": b["type"],
        "details": details,
        "keep_id": keep["id"],
        "keep_name": keep["name"],
        "keep_richness": round(keep_score, 1),
        "drop_id": drop["id"],
        "drop_name": drop["name"],
        "drop_richness": round(drop_score, 1),
        "reasons": sorted(reasons),
    })

# Sort by confidence descending
results.sort(key=lambda r: -r["confidence"])

# ------------------------------------------------------------------
# Classify: TRUE duplicates vs merely related cross-type
# ------------------------------------------------------------------
# A "true duplicate" means the same real-world thing entered twice.
# Cross-type pairs with low name similarity are likely separate entities
# that merely share a location name (e.g., "Bãi biển Thạnh Phú" vs "Khô cá biển Thạnh Phú").

true_dups = []
maybe_related = []

for r in results:
    is_cross = any("CROSS_TYPE" in d for d in r["details"])
    name_j = 0
    for d in r["details"]:
        if d.startswith("name_jaccard="):
            name_j = float(d.split("=")[1])
        elif d in ("exact_name_match",):
            name_j = 1.0
        elif d == "normalized_name_match":
            name_j = 0.95

    if is_cross and name_j < 0.5:
        maybe_related.append(r)
    else:
        true_dups.append(r)


def print_pair(i, r):
    print(f"{'─' * 80}")
    print(f"  #{i}  Confidence: {r['confidence']}  |  Detection: {', '.join(r['reasons'])}")
    print(f"{'─' * 80}")
    print(f"  A: {r['a_name']}")
    print(f"     id={r['a_id']}  type={r['a_type']}")
    print(f"  B: {r['b_name']}")
    print(f"     id={r['b_id']}  type={r['b_type']}")
    print()
    print(f"  Signals: {' | '.join(r['details'])}")
    print()
    print(f"  >>> KEEP: {r['keep_name']} (richness={r['keep_richness']})")
    print(f"      DROP: {r['drop_name']} (richness={r['drop_richness']})")
    print()


# ------------------------------------------------------------------
# Output
# ------------------------------------------------------------------
print(f"{'=' * 90}")
print(f"  DUPLICATE ENTITY REPORT")
print(f"  Source: web/data.json ({len(entities)} entities, {len(relationships)} relationships)")
print(f"{'=' * 90}")
print()

# Section 1: TRUE DUPLICATES
print(f"{'#' * 90}")
print(f"  SECTION 1: TRUE DUPLICATES — {len(true_dups)} pairs")
print(f"  (same real-world entity entered multiple times)")
print(f"{'#' * 90}\n")

for i, r in enumerate(true_dups, 1):
    print_pair(i, r)

# Section 2: MAYBE RELATED (cross-type, low name similarity)
print(f"\n{'#' * 90}")
print(f"  SECTION 2: MAYBE RELATED (cross-type, different entities) — {len(maybe_related)} pairs")
print(f"  (likely separate entities at same location, NOT true duplicates)")
print(f"{'#' * 90}\n")

for i, r in enumerate(maybe_related, 1):
    print_pair(i, r)

# Summary
print(f"\n{'=' * 90}")
print(f"  SUMMARY")
print(f"{'=' * 90}")
print(f"  Total candidate pairs: {len(results)}")
print(f"  TRUE DUPLICATES (merge candidates): {len(true_dups)}")
td_high = [r for r in true_dups if r["confidence"] >= 50]
td_med = [r for r in true_dups if 30 <= r["confidence"] < 50]
td_low = [r for r in true_dups if r["confidence"] < 30]
print(f"    High confidence (>=50): {len(td_high)}")
print(f"    Medium confidence (30-49): {len(td_med)}")
print(f"    Low confidence (<30): {len(td_low)}")
print(f"  MAYBE RELATED (not true dups): {len(maybe_related)}")
print()

# Cross-type true dups (these are actionable)
cross_true = [r for r in true_dups if any("CROSS_TYPE" in d for d in r["details"])]
print(f"  Cross-type TRUE dups (same place, different type): {len(cross_true)}")
for r in cross_true:
    ct = [d for d in r["details"] if "CROSS_TYPE" in d][0]
    print(f"    [{r['confidence']}] {r['a_name']} vs {r['b_name']} — {ct}")
