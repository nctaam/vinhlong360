#!/usr/bin/env python3
"""
Deep geographic data normalization analysis for vinhlong360.
Analyzes: coordinate clustering, quality, placeId consistency,
area distribution, and ward coverage.
"""

import json
import sys
import os
from collections import Counter, defaultdict
from pathlib import Path

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

DATA_PATH = Path(__file__).resolve().parent.parent / "web" / "data.json"

def load_data():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def sep(title):
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

def subsep(title):
    print(f"\n--- {title} ---\n")

# ─────────────────────────────────────────────────
# PART 1: Coordinate clustering
# ─────────────────────────────────────────────────
def part1_coordinate_clustering(data):
    sep("PART 1: COORDINATE CLUSTERING")

    entities = data["entities"]
    entity_map = {e["id"]: e for e in entities}

    # 1a. All unique coordinate points
    coord_to_entities = defaultdict(list)
    no_coords = []
    invalid_coords = []

    for e in entities:
        c = e.get("coordinates")
        if c is None or c == []:
            no_coords.append(e)
            continue
        if not isinstance(c, list) or len(c) != 2:
            invalid_coords.append((e["id"], c))
            continue
        key = (round(c[0], 7), round(c[1], 7))
        coord_to_entities[key].append(e)

    print(f"Total entities: {len(entities)}")
    print(f"Entities with valid coordinates: {sum(len(v) for v in coord_to_entities.values())}")
    print(f"Entities with no/empty coordinates: {len(no_coords)}")
    print(f"Entities with invalid coordinate format: {len(invalid_coords)}")
    print(f"Unique coordinate points: {len(coord_to_entities)}")

    # 1b. Top 20 most-shared coordinates
    subsep("Top 20 most-shared coordinate points")
    shared = sorted(coord_to_entities.items(), key=lambda x: -len(x[1]))
    for i, (coord, ents) in enumerate(shared[:20]):
        names = [e["name"] for e in ents[:5]]
        extra = f" (+{len(ents)-5} more)" if len(ents) > 5 else ""
        types = Counter(e["type"] for e in ents)
        print(f"  {i+1:2d}. [{coord[0]}, {coord[1]}] — {len(ents)} entities")
        print(f"      Types: {dict(types)}")
        print(f"      Sample: {', '.join(names)}{extra}")

    # 1c. Ward coordinates
    subsep("Ward (xã/phường) coordinates")
    wards = [e for e in entities if e.get("type") == "place" and e.get("level") in ("xa", "phuong")]
    print(f"Total wards: {len(wards)}")

    # Group wards by their coordinates
    ward_coords = defaultdict(list)
    for w in wards:
        c = w.get("coordinates")
        if c and len(c) == 2:
            key = (round(c[0], 7), round(c[1], 7))
            ward_coords[key].append(w)

    print(f"Unique ward coordinate points: {len(ward_coords)}")

    # Show wards sharing coordinates
    shared_ward_coords = {k: v for k, v in ward_coords.items() if len(v) > 1}
    if shared_ward_coords:
        print(f"\nWards sharing the SAME coordinates ({len(shared_ward_coords)} clusters):")
        for coord, ws in sorted(shared_ward_coords.items(), key=lambda x: -len(x[1])):
            names = [f"{w['name']} ({w['id']})" for w in ws]
            print(f"  [{coord[0]}, {coord[1]}] — {len(ws)} wards: {', '.join(names)}")

    # 1d. Shared-coordinate clusters that are ward centroids
    subsep("Shared-coordinate clusters matching ward centroids")
    ward_coord_set = set(ward_coords.keys())

    matched = 0
    for coord, ents in shared[:50]:
        if len(ents) < 2:
            break
        if coord in ward_coord_set:
            ward_names = [w["name"] for w in ward_coords[coord]]
            non_ward_count = len(ents) - len(ward_coords[coord])
            if non_ward_count > 0:
                matched += 1
                print(f"  [{coord[0]}, {coord[1]}]: ward(s)={', '.join(ward_names)}, "
                      f"{non_ward_count} other entities share this coord")

    if matched == 0:
        # Check if entities share coords with ANY ward
        for coord, ents in shared[:50]:
            if len(ents) < 2:
                break
            if coord in ward_coord_set:
                ward_names = [w["name"] for w in ward_coords[coord]]
                print(f"  [{coord[0]}, {coord[1]}]: ward(s)={', '.join(ward_names)}, "
                      f"total entities at this point: {len(ents)}")
                matched += 1
        if matched == 0:
            print("  (No shared-coordinate clusters found at exact ward coordinate points)")

    return coord_to_entities, ward_coords


# ─────────────────────────────────────────────────
# PART 2: Coordinate quality
# ─────────────────────────────────────────────────
def part2_coordinate_quality(data, coord_to_entities):
    sep("PART 2: COORDINATE QUALITY")

    entities = data["entities"]

    # 2a. Format consistency
    subsep("Coordinate format check")
    format_issues = []
    for e in entities:
        c = e.get("coordinates")
        if c is None or c == []:
            continue
        if not isinstance(c, list):
            format_issues.append((e["id"], f"Not a list: {type(c).__name__}"))
        elif len(c) != 2:
            format_issues.append((e["id"], f"Length={len(c)}, expected 2"))
        elif not all(isinstance(v, (int, float)) for v in c):
            format_issues.append((e["id"], f"Non-numeric values: {c}"))

    print(f"Format issues found: {len(format_issues)}")
    for eid, issue in format_issues[:20]:
        print(f"  {eid}: {issue}")

    # 2b. Bounding box check: VL+BT+TV region
    LAT_MIN, LAT_MAX = 9.5, 10.8
    LNG_MIN, LNG_MAX = 105.5, 107.0

    subsep(f"Bounding box check (lat {LAT_MIN}-{LAT_MAX}, lng {LNG_MIN}-{LNG_MAX})")
    out_of_bbox = []
    lat_vals = []
    lng_vals = []

    for e in entities:
        c = e.get("coordinates")
        if c is None or c == [] or not isinstance(c, list) or len(c) != 2:
            continue
        lat, lng = c[0], c[1]
        lat_vals.append(lat)
        lng_vals.append(lng)

        if not (LAT_MIN <= lat <= LAT_MAX) or not (LNG_MIN <= lng <= LNG_MAX):
            out_of_bbox.append(e)

    if lat_vals:
        print(f"Latitude range:  min={min(lat_vals):.7f}, max={max(lat_vals):.7f}")
        print(f"Longitude range: min={min(lng_vals):.7f}, max={max(lng_vals):.7f}")

    print(f"\nEntities outside bounding box: {len(out_of_bbox)}")
    for e in out_of_bbox[:30]:
        c = e["coordinates"]
        print(f"  {e['id']} [{c[0]}, {c[1]}] area={e.get('area')} — {e['name'][:60]}")

    # 2c. coords_approximate flag
    subsep("Entities with coords_approximate flag")
    approx = [e for e in entities if e.get("attributes", {}).get("coords_approximate")]
    print(f"Total with coords_approximate=true: {len(approx)}")

    approx_by_area = Counter(e.get("area") for e in approx)
    print(f"\nBy area:")
    for area, count in approx_by_area.most_common():
        total_in_area = sum(1 for e in entities if e.get("area") == area)
        pct = count / total_in_area * 100 if total_in_area else 0
        print(f"  {area or '(none)':20s}: {count:4d} / {total_in_area:4d} ({pct:.1f}%)")

    approx_by_type = Counter(e.get("type") for e in approx)
    print(f"\nBy type:")
    for t, count in approx_by_type.most_common():
        total_of_type = sum(1 for e in entities if e.get("type") == t)
        pct = count / total_of_type * 100 if total_of_type else 0
        print(f"  {t or '(none)':20s}: {count:4d} / {total_of_type:4d} ({pct:.1f}%)")


# ─────────────────────────────────────────────────
# PART 3: PlaceId consistency
# ─────────────────────────────────────────────────
def part3_placeid_consistency(data):
    sep("PART 3: PLACEID CONSISTENCY")

    entities = data["entities"]
    entity_map = {e["id"]: e for e in entities}

    # 3a. All unique placeId values
    subsep("Unique placeId values")
    placeid_map = defaultdict(list)
    no_placeid = []

    for e in entities:
        pid = e.get("placeId")
        if pid:
            placeid_map[pid].append(e)
        else:
            no_placeid.append(e)

    print(f"Entities with placeId: {len(entities) - len(no_placeid)}")
    print(f"Entities without placeId: {len(no_placeid)}")
    print(f"Unique placeId values: {len(placeid_map)}")

    print(f"\nTop 30 placeIds by entity count:")
    for pid, ents in sorted(placeid_map.items(), key=lambda x: -len(x[1]))[:30]:
        ref = entity_map.get(pid)
        ref_name = ref["name"] if ref else "(NOT FOUND)"
        print(f"  {pid:35s}: {len(ents):4d} entities → {ref_name}")

    # 3b. placeId doesn't match area
    subsep("PlaceId vs area mismatch")
    mismatches = []
    for e in entities:
        pid = e.get("placeId")
        if not pid:
            continue
        ref = entity_map.get(pid)
        if not ref:
            continue
        e_area = e.get("area")
        ref_area = ref.get("area")
        if e_area and ref_area and e_area != ref_area:
            mismatches.append((e, ref))

    print(f"Entities whose placeId points to a place in a different area: {len(mismatches)}")
    for e, ref in mismatches[:20]:
        print(f"  {e['id']}: area={e.get('area')}, placeId={e['placeId']} (area={ref.get('area')})")

    # 3c. placeId pointing to non-existent entities
    subsep("PlaceId pointing to non-existent entities")
    dangling = []
    for pid, ents in placeid_map.items():
        if pid not in entity_map:
            dangling.append((pid, ents))

    print(f"PlaceIds referencing non-existent entities: {len(dangling)}")
    for pid, ents in dangling[:30]:
        sample = [e["id"] for e in ents[:3]]
        print(f"  {pid}: {len(ents)} entities reference it (e.g. {', '.join(sample)})")

    # 3d. Entities without placeId but address mentions known ward
    subsep("Entities without placeId whose address mentions a known ward")

    # Build ward name lookup
    wards = [e for e in entities if e.get("type") == "place" and e.get("level") in ("xa", "phuong")]
    ward_names = {}
    for w in wards:
        # Extract short name (without Xã/Phường prefix)
        name = w["name"]
        for prefix in ["Phường ", "Xã ", "Thị trấn "]:
            if name.startswith(prefix):
                name = name[len(prefix):]
                break
        ward_names[name.lower()] = w

    candidates = []
    for e in no_placeid:
        addr = e.get("attributes", {}).get("address", "")
        if not addr:
            continue
        addr_lower = addr.lower()
        for wname, ward in ward_names.items():
            if wname in addr_lower and len(wname) > 2:  # skip very short names
                candidates.append((e, ward, wname))
                break

    print(f"Entities without placeId that mention a ward name in address: {len(candidates)}")
    for e, ward, matched in candidates[:20]:
        addr = e.get("attributes", {}).get("address", "")[:80]
        print(f"  {e['id']}: matched '{matched}' → {ward['id']}")
        print(f"    address: {addr}")
    if len(candidates) > 20:
        print(f"  ... and {len(candidates)-20} more")

    return placeid_map, no_placeid


# ─────────────────────────────────────────────────
# PART 4: Area distribution
# ─────────────────────────────────────────────────
def part4_area_distribution(data):
    sep("PART 4: AREA DISTRIBUTION")

    entities = data["entities"]

    # 4a. Count per area
    subsep("Entity count per area")
    area_counts = Counter(e.get("area") for e in entities)
    for area, count in area_counts.most_common():
        pct = count / len(entities) * 100
        print(f"  {area or '(none)':25s}: {count:4d} ({pct:.1f}%)")

    # 4b. Entities without area
    subsep("Entities without area")
    no_area = [e for e in entities if not e.get("area")]
    print(f"Entities without area: {len(no_area)}")

    for e in no_area[:30]:
        addr = e.get("attributes", {}).get("address", "")[:60]
        pid = e.get("placeId", "")
        print(f"  {e['id']:40s} type={e.get('type'):15s} placeId={pid} addr={addr}")

    if len(no_area) > 30:
        print(f"  ... and {len(no_area)-30} more")

    # Check if area can be inferred from placeId or address
    entity_map = {e["id"]: e for e in entities}
    inferable = 0
    for e in no_area:
        pid = e.get("placeId")
        if pid and pid in entity_map:
            ref = entity_map[pid]
            if ref.get("area"):
                inferable += 1
                continue
        addr = e.get("attributes", {}).get("address", "")
        addr_lower = addr.lower()
        for keyword, area in [("vĩnh long", "vinh-long"), ("bến tre", "ben-tre"),
                               ("trà vinh", "tra-vinh"), ("vinh long", "vinh-long"),
                               ("ben tre", "ben-tre"), ("tra vinh", "tra-vinh")]:
            if keyword in addr_lower:
                inferable += 1
                break

    print(f"\nOf {len(no_area)} without area, {inferable} could potentially be inferred from placeId or address")

    # 4c. Cross-check: area=vinh-long but address mentions Bến Tre / Trà Vinh
    subsep("Cross-check: area vs address mismatch")

    cross_checks = [
        ("vinh-long", ["bến tre", "ben tre", "bến tre"], "Bến Tre"),
        ("vinh-long", ["trà vinh", "tra vinh"], "Trà Vinh"),
        ("ben-tre", ["vĩnh long", "vinh long"], "Vĩnh Long"),
        ("ben-tre", ["trà vinh", "tra vinh"], "Trà Vinh"),
        ("tra-vinh", ["vĩnh long", "vinh long"], "Vĩnh Long"),
        ("tra-vinh", ["bến tre", "ben tre"], "Bến Tre"),
    ]

    total_mismatches = 0
    for area_val, keywords, label in cross_checks:
        mismatched = []
        for e in entities:
            if e.get("area") != area_val:
                continue
            addr = e.get("attributes", {}).get("address", "")
            addr_lower = addr.lower()
            for kw in keywords:
                if kw in addr_lower:
                    mismatched.append(e)
                    break
        if mismatched:
            print(f"area='{area_val}' but address mentions '{label}': {len(mismatched)}")
            for e in mismatched[:5]:
                addr = e.get("attributes", {}).get("address", "")[:80]
                print(f"    {e['id']}: {addr}")
            if len(mismatched) > 5:
                print(f"    ... and {len(mismatched)-5} more")
            total_mismatches += len(mismatched)

    if total_mismatches == 0:
        print("  No area/address cross-check mismatches found.")


# ─────────────────────────────────────────────────
# PART 5: Ward coverage map
# ─────────────────────────────────────────────────
def part5_ward_coverage(data, placeid_map):
    sep("PART 5: WARD COVERAGE MAP")

    entities = data["entities"]
    relationships = data["relationships"]
    entity_map = {e["id"]: e for e in entities}

    # All wards
    wards = [e for e in entities if e.get("type") == "place" and e.get("level") in ("xa", "phuong")]
    print(f"Total wards (xã + phường): {len(wards)}")

    # Build ward → entities via located_in relationships
    located_in = defaultdict(set)  # ward_id → set of entity_ids
    for r in relationships:
        if r["type"] == "located_in":
            # from=entity, to=ward (typically)
            located_in[r["to"]].add(r["from"])

    # Also count via placeId
    placeid_coverage = defaultdict(set)
    for e in entities:
        pid = e.get("placeId")
        if pid and pid in entity_map:
            ref = entity_map[pid]
            if ref.get("type") == "place" and ref.get("level") in ("xa", "phuong"):
                placeid_coverage[pid].add(e["id"])

    # Merge: entities per ward
    ward_entity_counts = {}
    for w in wards:
        wid = w["id"]
        combined = located_in.get(wid, set()) | placeid_coverage.get(wid, set())
        # Exclude the ward itself
        combined.discard(wid)
        ward_entity_counts[wid] = combined

    subsep("Ward entity counts (via located_in OR placeId)")

    counts = [(w, len(ward_entity_counts.get(w["id"], set()))) for w in wards]
    counts.sort(key=lambda x: -x[1])

    # Top 20 wards by entity count
    subsep("Top 20 wards by entity count")
    for i, (w, cnt) in enumerate(counts[:20]):
        print(f"  {i+1:2d}. {w['name']:40s} ({w['id']:35s}) area={w.get('area'):10s} — {cnt} entities")

    # Empty wards
    empty = [(w, cnt) for w, cnt in counts if cnt == 0]
    subsep(f"Empty wards (0 entities): {len(empty)}")
    for w, cnt in empty:
        print(f"  {w['name']:40s} ({w['id']:35s}) area={w.get('area')}")

    # Distribution summary
    subsep("Distribution statistics")
    all_counts = [cnt for _, cnt in counts]
    total = sum(all_counts)
    n = len(all_counts)
    mean = total / n if n else 0
    median = sorted(all_counts)[n // 2] if n else 0
    max_val = max(all_counts) if all_counts else 0
    min_val = min(all_counts) if all_counts else 0

    print(f"Wards: {n}")
    print(f"Total entities across wards: {total}")
    print(f"Mean entities/ward: {mean:.1f}")
    print(f"Median entities/ward: {median}")
    print(f"Max: {max_val}, Min: {min_val}")
    print(f"Wards with 0 entities: {len(empty)}")
    print(f"Wards with 1+ entities: {n - len(empty)}")
    print(f"Wards with 10+ entities: {sum(1 for c in all_counts if c >= 10)}")
    print(f"Wards with 20+ entities: {sum(1 for c in all_counts if c >= 20)}")

    # Gini coefficient
    subsep("Gini coefficient of entity distribution across wards")
    sorted_counts = sorted(all_counts)
    if n > 0 and total > 0:
        cumulative = 0
        gini_sum = 0
        for i, c in enumerate(sorted_counts):
            cumulative += c
            gini_sum += (2 * (i + 1) - n - 1) * c
        gini = gini_sum / (n * total)
        print(f"Gini coefficient: {gini:.4f}")
        print(f"  (0 = perfectly equal, 1 = maximally unequal)")
        if gini > 0.6:
            print(f"  → HIGH inequality: entities are very concentrated in a few wards")
        elif gini > 0.4:
            print(f"  → MODERATE inequality")
        else:
            print(f"  → RELATIVELY even distribution")
    else:
        print("Cannot compute Gini (no data)")

    # Coverage by area
    subsep("Ward coverage by area")
    area_ward_stats = defaultdict(lambda: {"total": 0, "empty": 0, "entities": 0})
    for w, cnt in counts:
        area = w.get("area", "(none)")
        area_ward_stats[area]["total"] += 1
        area_ward_stats[area]["entities"] += cnt
        if cnt == 0:
            area_ward_stats[area]["empty"] += 1

    for area, stats in sorted(area_ward_stats.items()):
        covered = stats["total"] - stats["empty"]
        pct = covered / stats["total"] * 100 if stats["total"] else 0
        print(f"  {area:20s}: {stats['total']:3d} wards, {covered:3d} covered ({pct:.0f}%), "
              f"{stats['empty']:3d} empty, {stats['entities']:4d} total entities")

    # Quintile distribution
    subsep("Distribution by quintile")
    if n >= 5:
        q_size = n // 5
        for qi in range(5):
            start = qi * q_size
            end = (qi + 1) * q_size if qi < 4 else n
            q_counts = sorted_counts[start:end]
            q_total = sum(q_counts)
            q_pct = q_total / total * 100 if total else 0
            print(f"  Q{qi+1} (wards {start+1}-{end}): {q_total} entities ({q_pct:.1f}%), "
                  f"range {min(q_counts)}-{max(q_counts)}")


# ─────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────
def main():
    print("Loading data from:", DATA_PATH)
    data = load_data()
    print(f"Loaded {len(data['entities'])} entities, {len(data['relationships'])} relationships")

    coord_to_entities, ward_coords = part1_coordinate_clustering(data)
    part2_coordinate_quality(data, coord_to_entities)
    placeid_map, no_placeid = part3_placeid_consistency(data)
    part4_area_distribution(data)
    part5_ward_coverage(data, placeid_map)

    sep("ANALYSIS COMPLETE")

if __name__ == "__main__":
    main()
