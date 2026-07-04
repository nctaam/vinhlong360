#!/usr/bin/env python3
"""Deep data audit — tìm mọi sai lệch trong dữ liệu vinhlong360.

Chạy: python scripts/deep_audit.py [--fix]
  --fix: tự động sửa các vấn đề an toàn (xoá rel vô nghĩa, fix type lạ, etc.)
"""
import json, math, sys, argparse, unicodedata, re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "web" / "data.json"
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from validate_data import (  # noqa: E402
    VALID_ENTITY_TYPES,
    has_approximate_coordinates,
    is_external_gateway,
    itinerary_stop_ref,
    normalized_coordinates,
    rel_source,
    rel_target,
    rel_type,
)

# Bbox chặt cho 3 tỉnh (VL + BT + TV)
LAT_MIN, LAT_MAX = 9.2, 10.65
LNG_MIN, LNG_MAX = 105.6, 106.95

VALID_TYPES = set(VALID_ENTITY_TYPES)

# Types lạ cần gộp
TYPE_REMAP = {}

VALID_AREAS = {"vinh-long", "ben-tre", "tra-vinh"}

VALID_REL_TYPES = {
    "near", "produced_in", "related_to", "associated_with",
    "hosts", "offered_by", "supplies_to",
}


def load():
    with DATA_PATH.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def save(data):
    with DATA_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=None, separators=(",", ":"))


def norm_coords(val):
    return normalized_coordinates(val)


def haversine(a, b):
    lat1, lng1 = math.radians(a[0]), math.radians(a[1])
    lat2, lng2 = math.radians(b[0]), math.radians(b[1])
    dlat, dlng = lat2 - lat1, lng2 - lng1
    h = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlng/2)**2
    return 6371 * 2 * math.asin(math.sqrt(h))


def strip_accents(s):
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


def levenshtein(a, b):
    if len(a) < len(b): a, b = b, a
    prev = list(range(len(b)+1))
    for i, ca in enumerate(a):
        curr = [i+1]
        for j, cb in enumerate(b):
            curr.append(min(prev[j+1]+1, curr[j]+1, prev[j]+(ca != cb)))
        prev = curr
    return prev[-1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fix", action="store_true")
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    data = load()
    entities = data.get("entities", [])
    rels = data.get("relationships", [])
    itineraries = data.get("itineraries", [])

    by_id = {str(e["id"]): e for e in entities if isinstance(e, dict) and e.get("id")}
    issues = []
    fixes = []

    print(f"=== DEEP AUDIT: {len(entities)} entities, {len(rels)} rels, {len(itineraries)} itineraries ===\n")

    # ── 1. TYPE VALIDATION ──
    print("── 1. Entity types ──")
    type_counts = Counter(e.get("type") for e in entities)
    invalid_types = {t: c for t, c in type_counts.items() if t not in VALID_TYPES and t not in TYPE_REMAP}
    remap_types = {t: c for t, c in type_counts.items() if t in TYPE_REMAP}
    for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
        marker = " ❌ INVALID" if t in invalid_types else (" → "+TYPE_REMAP[t] if t in remap_types else "")
        print(f"  {t}: {c}{marker}")
    # ── 2. AREA VALIDATION ──
    print("\n── 2. Area validation ──")
    bad_area = []
    missing_area = []
    for e in entities:
        if e.get("type") == "place":
            area = e.get("area")
            if not area:
                missing_area.append(e["id"])
            elif area not in VALID_AREAS:
                bad_area.append((e["id"], e["name"], area))
        else:
            area = e.get("area")
            if area and area not in VALID_AREAS:
                bad_area.append((e["id"], e["name"], area))
    print(f"  Places missing area: {len(missing_area)}")
    print(f"  Invalid area values: {len(bad_area)}")
    for eid, name, area in bad_area[:10]:
        print(f"    {eid}: '{name}' has area='{area}'")

    # ── 3. COORDINATES DEEP CHECK ──
    print("\n── 3. Coordinates ──")
    no_coords = []
    out_bbox = []
    coord_buckets = defaultdict(list)
    for e in entities:
        if e.get("type") == "itinerary" or is_external_gateway(e):
            continue
        c = norm_coords(e.get("coordinates") or e.get("coords"))
        if not c:
            no_coords.append(e["id"])
            continue
        lat, lng = c
        if not (LAT_MIN <= lat <= LAT_MAX and LNG_MIN <= lng <= LNG_MAX):
            out_bbox.append((e["id"], e["name"], lat, lng))
        key = f"{lat:.4f},{lng:.4f}"
        coord_buckets[key].append((e["id"], has_approximate_coordinates(e)))

    dup_coords_approx = {k: v for k, v in coord_buckets.items() if len(v) > 3 and all(is_approx for _eid, is_approx in v)}
    dup_coords_precise = {
        k: [eid for eid, is_approx in v if not is_approx]
        for k, v in coord_buckets.items()
        if len([eid for eid, is_approx in v if not is_approx]) > 3
    }
    print(f"  Missing coordinates: {len(no_coords)}")
    print(f"  Out of tight bbox: {len(out_bbox)}")
    print(f"  Approx same-coord clusters (>3 entities): {len(dup_coords_approx)}")
    print(f"  Precise same-coord clusters (>3 entities): {len(dup_coords_precise)}")
    for coord, eids in sorted(dup_coords_precise.items(), key=lambda x: -len(x[1]))[:5]:
        names = [by_id[eid]["name"] for eid in eids[:4] if eid in by_id]
        print(f"    {coord} ({len(eids)} entities): {', '.join(names)}...")

    # ── 4. NEAR RELATIONSHIP AUDIT ──
    print("\n── 4. Near relationships ──")
    near_rels = [r for r in rels if rel_type(r) == "near"]
    near_no_coords = []
    near_too_far = []
    near_self = []
    near_directed = Counter()
    near_edges = set()

    for r in near_rels:
        src = str(rel_source(r) or "")
        dst = str(rel_target(r) or "")
        if src == dst:
            near_self.append(r)
            continue
        near_directed[(src, dst)] += 1
        near_edges.add((src, dst))
        se = by_id.get(src)
        de = by_id.get(dst)
        if not se or not de:
            continue
        sc = norm_coords(se.get("coordinates") or se.get("coords"))
        dc = norm_coords(de.get("coordinates") or de.get("coords"))
        if not sc or not dc:
            near_no_coords.append(r)
            continue
        dist = haversine(sc, dc)
        if dist > 50:
            near_too_far.append((r, dist, se["name"], de["name"]))

    near_dups_found = sum(c - 1 for c in near_directed.values() if c > 1)
    near_reciprocal_pairs = sum(1 for s, d in near_edges if s < d and (d, s) in near_edges)
    print(f"  Total near: {len(near_rels)}")
    print(f"  Missing coords (either side): {len(near_no_coords)} → SHOULD DELETE")
    print(f"  Too far (>50km): {len(near_too_far)} → SHOULD DELETE")
    print(f"  Self-referencing: {len(near_self)} → SHOULD DELETE")
    print(f"  Duplicate directed edges: {near_dups_found} -> SHOULD DELETE")
    print(f"  Reciprocal near pairs: {near_reciprocal_pairs} -> runtime-safe")
    for r, dist, sn, dn in near_too_far[:5]:
        print(f"    {sn} ↔ {dn}: {dist:.1f}km")

    # ── 5. PRODUCED_IN CROSS-AREA ──
    print("\n── 5. produced_in relationships ──")
    pi_rels = [r for r in rels if rel_type(r) == "produced_in"]
    pi_cross = []
    for r in pi_rels:
        src = str(rel_source(r) or "")
        dst = str(rel_target(r) or "")
        se, de = by_id.get(src), by_id.get(dst)
        if not se or not de: continue
        sa = se.get("area") or ""
        da = de.get("area") or ""
        if sa and da and sa != da:
            pi_cross.append((r, se["name"], de["name"], sa, da))
    print(f"  Total produced_in: {len(pi_rels)}")
    print(f"  Cross-area conflicts: {len(pi_cross)} → SHOULD DELETE")
    for r, sn, dn, sa, da in pi_cross:
        print(f"    {sn} ({sa}) → {dn} ({da})")

    # ── 6. DUPLICATE RELATIONSHIPS ──
    print("\n── 6. Duplicate relationships ──")
    rel_keys = Counter()
    for r in rels:
        src = str(rel_source(r) or "")
        dst = str(rel_target(r) or "")
        kind = str(rel_type(r) or "")
        rel_keys[(src, dst, kind)] += 1
    dup_rels = {k: v for k, v in rel_keys.items() if v > 1}
    print(f"  Duplicate rel triples: {len(dup_rels)}")
    if dup_rels:
        for (s, d, k), cnt in sorted(dup_rels.items(), key=lambda x: -x[1])[:5]:
            sn = by_id.get(s, {}).get("name", s)
            dn = by_id.get(d, {}).get("name", d)
            print(f"    {sn} --{k}--> {dn}: {cnt}x")

    # ── 7. BROKEN REFS IN RELATIONSHIPS ──
    print("\n── 7. Broken references ──")
    broken = []
    for r in rels:
        src = str(rel_source(r) or "")
        dst = str(rel_target(r) or "")
        if src not in by_id or dst not in by_id:
            broken.append((src, dst))
    print(f"  Broken references: {len(broken)}")

    # ── 8. FUZZY DUPLICATE NAMES ──
    print("\n── 8. Fuzzy duplicate names ──")
    name_norm = {}
    for e in entities:
        name = e.get("name", "").strip()
        if not name: continue
        key = strip_accents(name)
        key = re.sub(r"[^a-z0-9 ]", "", key)
        key = re.sub(r"\s+", " ", key).strip()
        if key not in name_norm:
            name_norm[key] = []
        name_norm[key].append((e["id"], name, e.get("type")))

    fuzzy_dups = {k: v for k, v in name_norm.items() if len(v) > 1}
    # Also check levenshtein between different normalized keys
    keys = list(name_norm.keys())
    close_pairs = []
    for i in range(len(keys)):
        for j in range(i+1, min(i+50, len(keys))):
            if abs(len(keys[i]) - len(keys[j])) > 3:
                continue
            dist = levenshtein(keys[i], keys[j])
            if dist <= 2 and dist > 0:
                close_pairs.append((keys[i], keys[j], dist))

    print(f"  Exact-normalized duplicates: {len(fuzzy_dups)}")
    for k, entries in sorted(fuzzy_dups.items(), key=lambda x: -len(x[1]))[:10]:
        items = [f"{eid}({t})" for eid, n, t in entries]
        orig_name = entries[0][1]
        print(f"    '{orig_name}': {', '.join(items)}")

    print(f"  Near-duplicate pairs (Levenshtein ≤ 2): {len(close_pairs)}")
    for k1, k2, d in close_pairs[:10]:
        n1 = name_norm[k1][0][1]
        n2 = name_norm[k2][0][1]
        print(f"    '{n1}' ↔ '{n2}' (dist={d})")

    # ── 9. ITINERARY INTEGRITY ──
    print("\n── 9. Itinerary integrity ──")
    itin_broken_stops = 0
    for it in itineraries:
        stops = it.get("stops", [])
        for stop in stops:
            eid = itinerary_stop_ref(stop)
            if eid and str(eid) not in by_id:
                itin_broken_stops += 1
                print(f"  Itinerary '{it.get('title',it.get('name','?'))}': stop '{eid}' not found")
    if not itin_broken_stops:
        print(f"  All {len(itineraries)} itineraries OK")

    # ── 10. ENTITY PLACEAREA CONSISTENCY ──
    print("\n── 10. placeId ↔ area consistency ──")
    pid_area_conflict = 0
    for e in entities:
        if e.get("type") == "place": continue
        pid = e.get("placeId")
        if not pid: continue
        place = by_id.get(str(pid))
        if not place: continue
        ea = e.get("area", "")
        pa = place.get("area", "")
        if ea and pa and ea != pa:
            pid_area_conflict += 1
            print(f"  {e['id']}: area={ea} but placeId={pid} has area={pa}")
    if not pid_area_conflict:
        print(f"  All consistent")

    # ── SUMMARY ──
    print("\n" + "="*60)
    to_delete = len(near_no_coords) + len(near_too_far) + len(near_self) + len(pi_cross) + sum(v-1 for v in dup_rels.values())
    print(f"TOTAL ISSUES FOUND:")
    print(f"  Near rels without coords: {len(near_no_coords)}")
    print(f"  Near rels too far: {len(near_too_far)}")
    print(f"  Near self-ref: {len(near_self)}")
    print(f"  produced_in cross-area: {len(pi_cross)}")
    print(f"  Duplicate rels: {sum(v-1 for v in dup_rels.values())}")
    print(f"  Types to remap: {sum(remap_types.values())}")
    print(f"  Fuzzy name dups: {len(fuzzy_dups)}")
    print(f"  TOTAL RELS TO DELETE: {to_delete}")

    if args.fix and (to_delete > 0 or remap_types):
        print(f"\n── APPLYING FIXES ──")
        # Build set of rels to remove
        remove_set = set()
        for r in near_no_coords + near_self:
            remove_set.add(id(r))
        for r, *_ in near_too_far:
            remove_set.add(id(r))
        for r, *_ in pi_cross:
            remove_set.add(id(r))

        # Remove duplicates (keep first occurrence)
        seen_keys = set()
        for r in rels:
            src = str(rel_source(r) or "")
            dst = str(rel_target(r) or "")
            kind = str(rel_type(r) or "")
            key = (src, dst, kind)
            if key in seen_keys:
                remove_set.add(id(r))
            else:
                seen_keys.add(key)

        before = len(rels)
        data["relationships"] = [r for r in rels if id(r) not in remove_set]
        after = len(data["relationships"])
        print(f"  Relationships: {before} → {after} (removed {before - after})")

        if remap_types:
            for e in entities:
                if e.get("type") in TYPE_REMAP:
                    old = e["type"]
                    e["type"] = TYPE_REMAP[old]
                    fixes.append(f"type {e['id']}: {old} -> {e['type']}")
            print(f"  Types remapped: {sum(remap_types.values())}")

        save(data)
        print(f"\n  ✅ Saved to {DATA_PATH}")
    elif args.fix:
        print("\n  No fixes needed.")


if __name__ == "__main__":
    main()
