"""
enrich_data.py — Enrich data with place descriptions + near relationships.

Pass 1: Generate descriptions for 125 place entities based on their children.
Pass 2: Add near relationships for entities with coords but no near rel.

Usage:
  python scripts/enrich_data.py              # dry-run
  python scripts/enrich_data.py --apply      # apply to data.json

§B1: ALWAYS run scripts/backup_data.py BEFORE --apply.
"""

import io
import json
import sys
from collections import Counter, defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from math import radians, cos, sin, asin, sqrt
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent.parent / "web" / "data.json"
DRY_RUN = "--apply" not in sys.argv

AREA_NAMES = {
    "vinh-long": "Vĩnh Long",
    "ben-tre": "Bến Tre",
    "tra-vinh": "Trà Vinh",
}

TYPE_LABELS_VI = {
    "restaurant": "quán ăn/nhà hàng",
    "cafe": "quán cà phê",
    "accommodation": "nơi lưu trú",
    "attraction": "điểm tham quan",
    "history": "di tích lịch sử",
    "nature": "cảnh quan thiên nhiên",
    "craft_village": "làng nghề",
    "product": "đặc sản/sản phẩm",
    "dish": "món ăn",
    "experience": "trải nghiệm",
    "event": "sự kiện/lễ hội",
    "facility": "tiện ích",
    "economy": "kinh tế",
    "person": "nhân vật",
    "drink": "thức uống",
    "organization": "tổ chức",
    "market": "chợ",
}


def haversine_m(lat1, lng1, lat2, lng2):
    R = 6371000
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return R * 2 * asin(sqrt(a))


def generate_place_description(place, children, emap):
    child_entities = [emap[cid] for cid in children if cid in emap]
    if not child_entities:
        return None

    type_counts = Counter(e.get("type", "?") for e in child_entities)
    area_name = AREA_NAMES.get(place.get("area", ""), "")
    name = place.get("name", "")

    parts = []
    for t, label in TYPE_LABELS_VI.items():
        count = type_counts.get(t, 0)
        if count > 0:
            parts.append(f"{count} {label}")

    if not parts:
        return None

    highlights_str = ", ".join(parts[:5])
    if len(parts) > 5:
        highlights_str += f" và {sum(type_counts.get(t, 0) for t in list(TYPE_LABELS_VI.keys())[5:] if type_counts.get(t, 0) > 0)} địa điểm khác"

    notable = []
    for e in child_entities:
        if e.get("type") in ("attraction", "history", "nature", "craft_village"):
            notable.append(e.get("name", ""))
    notable = notable[:3]

    if notable:
        notable_str = f" Nổi bật có {', '.join(notable)}."
    else:
        notable_str = ""

    if area_name:
        desc = f"{name} thuộc {area_name}, tập trung {highlights_str}.{notable_str}"
    else:
        desc = f"{name} tập trung {highlights_str}.{notable_str}"

    return desc


def pass1_place_descriptions(data):
    entities = data["entities"]
    rels = data["relationships"]
    emap = {e["id"]: e for e in entities}

    located_in = defaultdict(list)
    for r in rels:
        if r["type"] == "located_in":
            located_in[r["to"]].append(r["from"])

    results = []
    for e in entities:
        if e.get("type") != "place":
            continue
        if e.get("description"):
            continue

        children = located_in.get(e["id"], [])
        desc = generate_place_description(e, children, emap)
        if desc:
            results.append((e["id"], e.get("name", ""), desc))

    return results


def pass2_near_relationships(data, max_new=500):
    entities = data["entities"]
    rels = data["relationships"]

    existing_near = set()
    for r in rels:
        if r["type"] == "near":
            existing_near.add((r["from"], r["to"]))
            existing_near.add((r["to"], r["from"]))

    in_near = set()
    for r in rels:
        if r["type"] == "near":
            in_near.add(r["from"])
            in_near.add(r["to"])

    skip_types = {"place", "itinerary", "person", "event", "organization"}
    candidates = []
    for e in entities:
        c = e.get("coordinates")
        if not (isinstance(c, list) and len(c) >= 2):
            continue
        if e.get("type") in skip_types:
            continue
        if e["id"] in in_near:
            continue
        candidates.append(e)

    by_area = defaultdict(list)
    for e in candidates:
        by_area[e.get("area", "unknown")].append(e)

    all_with_coords = []
    for e in entities:
        c = e.get("coordinates")
        if isinstance(c, list) and len(c) >= 2 and e.get("type") not in skip_types:
            all_with_coords.append(e)

    new_rels = []
    for area, area_candidates in by_area.items():
        area_entities = [e for e in all_with_coords if e.get("area") == area]

        for cand in area_candidates:
            if len(new_rels) >= max_new:
                break

            clat, clng = cand["coordinates"][0], cand["coordinates"][1]
            nearest = []

            for other in area_entities:
                if other["id"] == cand["id"]:
                    continue
                pair = (cand["id"], other["id"])
                rev_pair = (other["id"], cand["id"])
                if pair in existing_near or rev_pair in existing_near:
                    continue

                olat, olng = other["coordinates"][0], other["coordinates"][1]
                dist = haversine_m(clat, clng, olat, olng)
                if dist <= 3000:
                    nearest.append((dist, other["id"]))

            nearest.sort()
            for dist, other_id in nearest[:2]:
                pair_key = (min(cand["id"], other_id), max(cand["id"], other_id))
                if pair_key not in existing_near:
                    new_rels.append({
                        "from": cand["id"],
                        "to": other_id,
                        "type": "near",
                    })
                    existing_near.add(pair_key)
                    existing_near.add((pair_key[1], pair_key[0]))

    return new_rels


def main():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"{'DRY RUN' if DRY_RUN else 'APPLYING'}\n")

    # Pass 1: Place descriptions
    desc_results = pass1_place_descriptions(data)
    print(f"Pass 1 — Place descriptions: {len(desc_results)} to generate")
    for eid, name, desc in desc_results[:5]:
        print(f"  {name[:35]:35s} → {desc[:80]}...")
    if len(desc_results) > 5:
        print(f"  ... +{len(desc_results) - 5} more")

    # Pass 2: Near relationships
    near_results = pass2_near_relationships(data)
    print(f"\nPass 2 — Near relationships: {len(near_results)} new")

    if DRY_RUN:
        print(f"\n→ DRY RUN. Run with --apply to save.")
        return

    # Apply Pass 1
    emap = {e["id"]: e for e in data["entities"]}
    for eid, _, desc in desc_results:
        if eid in emap:
            emap[eid]["description"] = desc

    # Apply Pass 2
    data["relationships"].extend(near_results)

    # Deduplicate relationships
    seen = set()
    deduped = []
    for r in data["relationships"]:
        key = (r.get("from"), r.get("to"), r["type"])
        if key not in seen:
            seen.add(key)
            deduped.append(r)
    data["relationships"] = deduped

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\nSaved. Entities: {len(data['entities'])}, Relationships: {len(data['relationships'])}")
    print("Run: python scripts/validate_data.py to verify.")


if __name__ == "__main__":
    main()
