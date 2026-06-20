"""
Check duplicate/suspicious coordinates among 124 ward entities in data.json.
"""
import json
from collections import defaultdict

DATA_PATH = r"C:\Code\vinhlong360\web\data.json"

# Expected coordinate ranges per area
AREA_RANGES = {
    "vinh-long": {"lat": (9.9, 10.3), "lon": (105.7, 106.2)},
    "ben-tre":   {"lat": (9.8, 10.35), "lon": (106.0, 106.8)},
    "tra-vinh":  {"lat": (9.5, 10.1),  "lon": (106.0, 106.6)},
}

with open(DATA_PATH, encoding="utf-8") as f:
    data = json.load(f)

# Extract ward/phuong entities
wards = []
for e in data["entities"]:
    eid = e.get("id", "")
    level = e.get("level", "")
    if level in ("xa", "phuong") and (eid.startswith("xa-") or eid.startswith("p-")):
        wards.append(e)

print(f"Total ward entities found: {len(wards)}\n")

# ── Part 1: Duplicate coordinates (rounded to 4 decimal places) ──
coord_groups = defaultdict(list)
for w in wards:
    coords = w.get("coordinates")
    if coords and len(coords) == 2:
        key = (round(coords[0], 4), round(coords[1], 4))
        coord_groups[key].append(w)

duplicates = {k: v for k, v in coord_groups.items() if len(v) >= 2}

print("=" * 80)
print("PART 1: DUPLICATE COORDINATES (rounded to 4 decimal places)")
print("=" * 80)

if not duplicates:
    print("No duplicate coordinates found.")
else:
    print(f"Found {len(duplicates)} groups with shared coordinates:\n")
    for i, (coord, entities) in enumerate(sorted(duplicates.items()), 1):
        print(f"--- Group {i}: coordinates ({coord[0]}, {coord[1]}) — {len(entities)} entities ---")
        for e in entities:
            raw = e.get("coordinates", [None, None])
            print(f"  ID:    {e['id']}")
            print(f"  Name:  {e['name']}")
            print(f"  Area:  {e.get('area', e.get('parentId', 'N/A'))}")
            print(f"  Level: {e.get('level')}")
            print(f"  Raw:   ({raw[0]}, {raw[1]})")
            print()

# Also check exact duplicates (no rounding)
exact_groups = defaultdict(list)
for w in wards:
    coords = w.get("coordinates")
    if coords and len(coords) == 2:
        key = (coords[0], coords[1])
        exact_groups[key].append(w)

exact_dups = {k: v for k, v in exact_groups.items() if len(v) >= 2}

print()
print("=" * 80)
print("PART 1b: EXACT DUPLICATE COORDINATES (no rounding)")
print("=" * 80)
if not exact_dups:
    print("No exact duplicate coordinates found.")
else:
    print(f"Found {len(exact_dups)} groups with exactly identical coordinates:\n")
    for i, (coord, entities) in enumerate(sorted(exact_dups.items()), 1):
        print(f"--- Group {i}: exact ({coord[0]}, {coord[1]}) — {len(entities)} entities ---")
        for e in entities:
            print(f"  ID:   {e['id']}")
            print(f"  Name: {e['name']}")
            print(f"  Area: {e.get('area', e.get('parentId', 'N/A'))}")
        print()

# ── Part 2: Out-of-range coordinates ──
print()
print("=" * 80)
print("PART 2: COORDINATES OUTSIDE EXPECTED RANGE FOR AREA")
print("=" * 80)

out_of_range = []
no_area = []
missing_coords = []

for w in wards:
    coords = w.get("coordinates")
    area = w.get("area") or w.get("parentId")

    if not coords or len(coords) != 2:
        missing_coords.append(w)
        continue

    lat, lon = coords[0], coords[1]

    if area not in AREA_RANGES:
        no_area.append((w, area))
        continue

    r = AREA_RANGES[area]
    issues = []
    if lat < r["lat"][0] or lat > r["lat"][1]:
        issues.append(f"lat {lat} outside [{r['lat'][0]}, {r['lat'][1]}]")
    if lon < r["lon"][0] or lon > r["lon"][1]:
        issues.append(f"lon {lon} outside [{r['lon'][0]}, {r['lon'][1]}]")

    if issues:
        out_of_range.append((w, area, issues))

if missing_coords:
    print(f"\nEntities with MISSING coordinates: {len(missing_coords)}")
    for w in missing_coords:
        print(f"  {w['id']} — {w['name']}")

if no_area:
    print(f"\nEntities with UNKNOWN area (not in expected ranges): {len(no_area)}")
    for w, area in no_area:
        print(f"  {w['id']} — area={area}")

if out_of_range:
    print(f"\nEntities with OUT-OF-RANGE coordinates: {len(out_of_range)}")
    for w, area, issues in out_of_range:
        coords = w["coordinates"]
        print(f"\n  ID:     {w['id']}")
        print(f"  Name:   {w['name']}")
        print(f"  Area:   {area}")
        print(f"  Coords: ({coords[0]}, {coords[1]})")
        for issue in issues:
            print(f"  ISSUE:  {issue}")
else:
    print("\nNo out-of-range coordinates found.")

# ── Part 3: Summary statistics ──
print()
print("=" * 80)
print("PART 3: SUMMARY STATISTICS")
print("=" * 80)

area_counts = defaultdict(int)
for w in wards:
    area = w.get("area") or w.get("parentId", "unknown")
    area_counts[area] += 1

print(f"\nTotal wards: {len(wards)}")
print("By area:")
for area, count in sorted(area_counts.items()):
    print(f"  {area}: {count}")

# Distance check: find closest pairs
print()
print("=" * 80)
print("PART 4: VERY CLOSE PAIRS (< 500m apart, ~0.005 degrees)")
print("=" * 80)

import math

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

close_pairs = []
for i in range(len(wards)):
    c1 = wards[i].get("coordinates")
    if not c1 or len(c1) != 2:
        continue
    for j in range(i + 1, len(wards)):
        c2 = wards[j].get("coordinates")
        if not c2 or len(c2) != 2:
            continue
        dist = haversine_km(c1[0], c1[1], c2[0], c2[1])
        if dist < 0.5 and dist > 0:  # < 500m but not exact same
            close_pairs.append((wards[i], wards[j], dist))

close_pairs.sort(key=lambda x: x[2])

if close_pairs:
    print(f"\nFound {len(close_pairs)} pairs closer than 500m:\n")
    for w1, w2, dist in close_pairs:
        c1 = w1["coordinates"]
        c2 = w2["coordinates"]
        print(f"  {dist*1000:.0f}m apart:")
        print(f"    {w1['id']:30s} ({c1[0]:.6f}, {c1[1]:.6f}) — {w1['name']}")
        print(f"    {w2['id']:30s} ({c2[0]:.6f}, {c2[1]:.6f}) — {w2['name']}")
        a1 = w1.get('area') or w1.get('parentId', '?')
        a2 = w2.get('area') or w2.get('parentId', '?')
        if a1 != a2:
            print(f"    ⚠ DIFFERENT AREAS: {a1} vs {a2}")
        print()
else:
    print("\nNo pairs closer than 500m found (besides exact duplicates).")
