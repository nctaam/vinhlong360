"""
merge_duplicates.py — Merge high-confidence duplicate entity pairs.

Strategy:
  - Only merges pairs with confidence >= 80 (very high certainty)
  - Keeps the entity with higher "richness" (more data/relationships)
  - Transfers all relationships from dropped entity to kept entity
  - Merges attributes (kept entity wins on conflicts)
  - Updates placeId references on other entities

Usage:
  python scripts/merge_duplicates.py              # dry-run
  python scripts/merge_duplicates.py --apply      # apply

§B1: ALWAYS run scripts/backup_data.py BEFORE --apply.
"""

import json
import re
import sys
import unicodedata
from collections import defaultdict
from itertools import combinations
from math import radians, cos, sin, asin, sqrt
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent.parent / "web" / "data.json"
DRY_RUN = "--apply" not in sys.argv
MIN_CONFIDENCE = 80


def load_data():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def strip_diacritics(s):
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalize_name(name):
    n = name.lower().strip()
    n = re.sub(r"\s*\([^)]*\)\s*", " ", n)
    n = strip_diacritics(n)
    n = re.sub(r"[^a-z0-9\s]", "", n)
    return re.sub(r"\s+", " ", n).strip()


def haversine_m(lat1, lng1, lat2, lng2):
    R = 6371000
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng/2)**2
    return R * 2 * asin(sqrt(a))


def jaccard_words(a, b):
    wa = set(a.lower().split())
    wb = set(b.lower().split())
    if not wa or not wb:
        return 0
    return len(wa & wb) / len(wa | wb)


def richness(e, rels):
    score = 0
    attrs = e.get("attributes") or {}
    score += len(attrs) * 2
    score += 10 if e.get("summary") and len(e.get("summary", "")) > 50 else 0
    score += 5 if isinstance(e.get("coordinates"), list) else 0
    score += 3 if e.get("area") else 0
    score += 3 if e.get("placeId") else 0
    score += sum(1 for r in rels if r.get("from") == e["id"] or r.get("to") == e["id"])
    return score


def find_pairs(entities, rels):
    """Find duplicate pairs with confidence >= MIN_CONFIDENCE."""
    emap = {e["id"]: e for e in entities}
    by_norm = defaultdict(list)
    by_addr = defaultdict(list)

    for e in entities:
        nn = normalize_name(e.get("name", ""))
        if nn:
            by_norm[nn].append(e["id"])
        addr = (e.get("attributes") or {}).get("address", "")
        if addr:
            na = normalize_name(addr)
            if na and len(na) > 10:
                by_addr[na].append(e["id"])

    candidates = set()
    for ids in by_norm.values():
        if len(ids) >= 2:
            for a, b in combinations(ids, 2):
                candidates.add((min(a, b), max(a, b)))
    for ids in by_addr.values():
        if 2 <= len(ids) <= 10:
            for a, b in combinations(ids, 2):
                candidates.add((min(a, b), max(a, b)))

    pairs = []
    for aid, bid in candidates:
        ea, eb = emap.get(aid), emap.get(bid)
        if not ea or not eb:
            continue

        score = 0
        name_jac = jaccard_words(ea.get("name", ""), eb.get("name", ""))
        score += name_jac * 30

        norm_a = normalize_name(ea.get("name", ""))
        norm_b = normalize_name(eb.get("name", ""))
        if norm_a == norm_b:
            score += 20

        addr_a = normalize_name((ea.get("attributes") or {}).get("address", ""))
        addr_b = normalize_name((eb.get("attributes") or {}).get("address", ""))
        if addr_a and addr_b and addr_a == addr_b:
            score += 20

        if ea.get("placeId") and ea.get("placeId") == eb.get("placeId"):
            score += 10

        ca = ea.get("coordinates")
        cb = eb.get("coordinates")
        if isinstance(ca, list) and isinstance(cb, list) and len(ca) >= 2 and len(cb) >= 2:
            dist = haversine_m(ca[0], ca[1], cb[0], cb[1])
            if dist < 50:
                score += 10
            elif dist < 500:
                score += 5

        if ea.get("area") and ea.get("area") == eb.get("area"):
            score += 10

        if score >= MIN_CONFIDENCE:
            ra = richness(ea, rels)
            rb = richness(eb, rels)
            keep = aid if ra >= rb else bid
            drop = bid if keep == aid else aid
            pairs.append((score, keep, drop))

    pairs.sort(key=lambda x: -x[0])
    return pairs


def merge_entity(keep_e, drop_e):
    """Merge drop_e data into keep_e (keep wins on conflicts)."""
    # Merge attributes
    keep_attrs = keep_e.get("attributes") or {}
    drop_attrs = drop_e.get("attributes") or {}
    for k, v in drop_attrs.items():
        if k not in keep_attrs and v:
            keep_attrs[k] = v
    keep_e["attributes"] = keep_attrs

    # Fill missing fields
    if not keep_e.get("coordinates") and drop_e.get("coordinates"):
        keep_e["coordinates"] = drop_e["coordinates"]
    if not keep_e.get("area") and drop_e.get("area"):
        keep_e["area"] = drop_e["area"]
    if not keep_e.get("placeId") and drop_e.get("placeId"):
        keep_e["placeId"] = drop_e["placeId"]
    if (not keep_e.get("summary") or len(keep_e.get("summary", "")) < 30) and drop_e.get("summary") and len(drop_e.get("summary", "")) > 30:
        keep_e["summary"] = drop_e["summary"]

    # Merge tags
    keep_tags = set(keep_e.get("tags") or [])
    drop_tags = set(drop_e.get("tags") or [])
    if keep_tags | drop_tags:
        keep_e["tags"] = sorted(keep_tags | drop_tags)

    # Cross-type: if one is history and other is attraction, keep both in aliases
    if keep_e.get("type") != drop_e.get("type"):
        aliases = keep_e.get("aliases") or []
        aliases.append(drop_e.get("name", ""))
        keep_e["aliases"] = aliases


def main():
    data = load_data()
    entities = data["entities"]
    rels = data["relationships"]
    emap = {e["id"]: e for e in entities}

    pairs = find_pairs(entities, rels)
    print(f"{'DRY RUN' if DRY_RUN else 'APPLYING'}: {len(pairs)} pairs with confidence >= {MIN_CONFIDENCE}\n")

    # Remove transitive: if A→B and B→C, only keep A→B
    already_dropped = set()
    final_pairs = []
    for score, keep, drop in pairs:
        if keep in already_dropped or drop in already_dropped:
            continue
        already_dropped.add(drop)
        final_pairs.append((score, keep, drop))

    print(f"After dedup: {len(final_pairs)} pairs to merge\n")

    for i, (score, keep, drop) in enumerate(final_pairs[:30]):
        kn = emap[keep].get("name", "")[:40]
        dn = emap[drop].get("name", "")[:40]
        kt = emap[keep].get("type", "")
        dt = emap[drop].get("type", "")
        print(f"  [{score:5.1f}] KEEP {kn:40s} ({kt}) ← DROP {dn:40s} ({dt})")

    if len(final_pairs) > 30:
        print(f"  ... +{len(final_pairs) - 30} more")

    if DRY_RUN:
        print(f"\n→ DRY RUN. Run with --apply to save.")
        return

    # Apply merges
    for score, keep_id, drop_id in final_pairs:
        keep_e = emap.get(keep_id)
        drop_e = emap.get(drop_id)
        if not keep_e or not drop_e:
            continue

        merge_entity(keep_e, drop_e)

        # Transfer relationships
        for r in rels:
            if r.get("from") == drop_id:
                r["from"] = keep_id
            if r.get("to") == drop_id:
                r["to"] = keep_id

        # Update placeId references
        for e in entities:
            if e.get("placeId") == drop_id:
                e["placeId"] = keep_id

    # Remove dropped entities
    drop_ids = {drop for _, _, drop in final_pairs}
    entities[:] = [e for e in entities if e["id"] not in drop_ids]

    # Remove self-referencing relationships
    rels[:] = [r for r in rels if r.get("from") != r.get("to")]

    # Remove duplicate relationships (same from+to+type)
    seen = set()
    deduped = []
    for r in rels:
        key = (r.get("from"), r.get("to"), r["type"])
        if key not in seen:
            seen.add(key)
            deduped.append(r)
    data["relationships"] = deduped

    save_data(data)
    print(f"\nMerged {len(final_pairs)} pairs.")
    print(f"Entities: {len(data['entities'])}")
    print(f"Relationships: {len(data['relationships'])}")
    print("Run: python scripts/validate_data.py to verify.")


if __name__ == "__main__":
    main()
