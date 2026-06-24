"""
fix_data_quality.py — Comprehensive structural data quality fixes for data.json.

Fixes applied:
  1. Delete person-near relationships (semantically meaningless)
  2. Delete cross-area near relationships (violate same-area rule)
  3. Infer area from placeId for entities missing area
  4. Add located_in relationships for entities with placeId but no located_in
  5. Inherit coordinates from placeId for entities without coords
  6. Link orphan entities to nearest ward by address parsing

Usage:
  python scripts/fix_data_quality.py              # dry-run (report only)
  python scripts/fix_data_quality.py --apply       # apply fixes to data.json

§B1: ALWAYS run scripts/backup_data.py BEFORE --apply.
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent.parent / "web" / "data.json"
DRY_RUN = "--apply" not in sys.argv


def load_data():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def fix_1_delete_person_near(rels, entity_map):
    """Delete near relationships involving person entities."""
    to_delete = []
    for i, r in enumerate(rels):
        if r["type"] != "near":
            continue
        e1 = entity_map.get(r.get("from"))
        e2 = entity_map.get(r.get("to"))
        if (e1 and e1.get("type") == "person") or (e2 and e2.get("type") == "person"):
            to_delete.append(i)
    return to_delete


def fix_2_delete_cross_area_near(rels, entity_map, skip_indices):
    """Delete near relationships crossing area boundaries."""
    to_delete = []
    for i, r in enumerate(rels):
        if r["type"] != "near" or i in skip_indices:
            continue
        e1 = entity_map.get(r.get("from"))
        e2 = entity_map.get(r.get("to"))
        if e1 and e2 and e1.get("area") and e2.get("area") and e1["area"] != e2["area"]:
            to_delete.append(i)
    return to_delete


def _area_from_address(addr: str) -> str | None:
    """Parse province hint from address text.
    Post-merger: 'Vĩnh Long' is ambiguous (could be old VL or new merged province).
    Only 'TP. Vĩnh Long' / 'Thành Phố Vĩnh Long' strongly signals vinh-long area.
    'TP. Bến Tre' / 'Bến Tre' at end of address = ben-tre area.
    'Tp. Trà Vinh' / 'Trà Vinh' at end of address = tra-vinh area.
    """
    if not addr:
        return None
    # Strong signals: city-level mentions
    tp_patterns = [
        (r"(?:TP\.?|Thành Phố)\s*Vĩnh Long", "vinh-long"),
        (r"(?:TP\.?|Thành Phố)\s*Bến Tre", "ben-tre"),
        (r"(?:Tp\.?|Thành Phố)\s*Trà Vinh", "tra-vinh"),
    ]
    for pat, area in tp_patterns:
        if re.search(pat, addr, re.IGNORECASE):
            return area
    # Weaker: province name at the end of address (trailing comma-separated segment)
    last_segment = addr.rsplit(",", 1)[-1].strip().lower()
    if last_segment in ("bến tre", "ben tre"):
        return "ben-tre"
    if last_segment in ("trà vinh", "tra vinh"):
        return "tra-vinh"
    if last_segment in ("vĩnh long", "vinh long"):
        return "vinh-long"
    return None


def _placeid_area_is_consistent(entity, entity_map) -> bool:
    """Check that placeId area doesn't contradict address-based area.
    Conservative: only rejects if address clearly signals a DIFFERENT specific area."""
    pid = entity.get("placeId")
    if not pid:
        return False
    place = entity_map.get(pid)
    if not place or not place.get("area"):
        return False
    addr = (entity.get("attributes") or {}).get("address", "")
    addr_area = _area_from_address(addr)
    if addr_area and addr_area != place["area"]:
        return False  # placeId contradicts address
    return True


def fix_3_infer_area(entities, entity_map):
    """Set area from address or placeId for entities missing area."""
    fixes = []
    for e in entities:
        if e.get("area"):
            continue
        # Priority 1: parse area from address
        addr = (e.get("attributes") or {}).get("address", "")
        addr_area = _area_from_address(addr)
        if addr_area:
            fixes.append((e["id"], addr_area))
            continue
        # Priority 2: inherit from placeId (only if consistent)
        if _placeid_area_is_consistent(e, entity_map):
            pid = e.get("placeId")
            place = entity_map.get(pid)
            fixes.append((e["id"], place["area"]))
    return fixes


def fix_4_add_located_in(entities, rels, entity_map):
    """Add located_in for entities with placeId but no located_in relationship.
    Only adds if placeId is consistent with address-based area."""
    existing = {r.get("from") for r in rels if r["type"] == "located_in"}
    new_rels = []
    for e in entities:
        if e.get("type") == "place":
            continue
        if e["id"] in existing:
            continue
        pid = e.get("placeId")
        if pid and entity_map.get(pid) and _placeid_area_is_consistent(e, entity_map):
            new_rels.append({"from": e["id"], "to": pid, "type": "located_in"})
    return new_rels


def fix_5_inherit_coordinates(entities, entity_map):
    """Inherit coordinates from placeId for entities without coords.
    Only inherits if placeId is consistent with address."""
    fixes = []
    for e in entities:
        coords = e.get("coordinates")
        if isinstance(coords, list) and len(coords) >= 2:
            continue
        pid = e.get("placeId")
        if pid and _placeid_area_is_consistent(e, entity_map):
            place = entity_map.get(pid)
            if place and isinstance(place.get("coordinates"), list) and len(place.get("coordinates", [])) >= 2:
                fixes.append((e["id"], place["coordinates"]))
    return fixes


def fix_6_link_orphans_by_address(entities, rels, entity_map):
    """Link orphan entities to ward by parsing address for phường/xã name."""
    entities_in_rels = set()
    for r in rels:
        entities_in_rels.add(r.get("from"))
        entities_in_rels.add(r.get("to"))

    orphans = [e for e in entities if e["id"] not in entities_in_rels]

    places = {
        e["id"]: e
        for e in entities
        if e.get("type") == "place" and e.get("level") in ("xa", "phuong")
    }
    place_by_area_name = {}
    for p in places.values():
        key = (p.get("area", ""), p["name"].lower())
        place_by_area_name[key] = p

    new_rels = []
    for e in orphans:
        if not e.get("area"):
            continue
        addr = (e.get("attributes") or {}).get("address", "")
        if not addr:
            continue

        phuong_match = re.search(r"P\.\s*(\d+)", addr)
        xa_match = re.search(r"(?:Xã|TT\.?|Thị Trấn)\s+([^,]+)", addr, re.IGNORECASE)

        matched_place = None
        area = e["area"]

        if phuong_match:
            num = phuong_match.group(1).strip()
            for key, p in place_by_area_name.items():
                if key[0] == area and num in p["name"]:
                    pname = p["name"].lower()
                    if f"phường {num}" in pname or pname.endswith(num):
                        matched_place = p
                        break

        if not matched_place and xa_match:
            xa_name = xa_match.group(1).strip().lower()
            for key, p in place_by_area_name.items():
                if key[0] == area and xa_name in key[1]:
                    matched_place = p
                    break

        if matched_place:
            new_rels.append({
                "from": e["id"],
                "to": matched_place["id"],
                "type": "located_in",
            })
            if not e.get("placeId"):
                e["placeId"] = matched_place["id"]

    return new_rels


def main():
    data = load_data()
    entities = data["entities"]
    rels = data["relationships"]
    entity_map = {e["id"]: e for e in entities}

    print(f"{'DRY RUN' if DRY_RUN else 'APPLYING'} — data.json: {len(entities)} entities, {len(rels)} relationships\n")

    # Pre-check: report wrong placeIds (address contradicts placeId area)
    wrong_pids = []
    for e in entities:
        pid = e.get("placeId")
        if not pid:
            continue
        place = entity_map.get(pid)
        if not place or not place.get("area"):
            continue
        addr = (e.get("attributes") or {}).get("address", "")
        addr_area = _area_from_address(addr)
        if addr_area and addr_area != place["area"]:
            wrong_pids.append((e["id"], e.get("name", ""), pid, place["area"], addr_area))
    if wrong_pids:
        print(f"WARNING: {len(wrong_pids)} entities have placeId contradicting address:")
        for eid, name, pid, p_area, a_area in wrong_pids[:10]:
            print(f"  {name[:40]} — placeId points to {p_area}, address says {a_area}")
        print()

    # Fix 1
    f1_indices = fix_1_delete_person_near(rels, entity_map)
    print(f"Fix 1: Delete {len(f1_indices)} person-near relationships")

    # Fix 2
    f2_indices = fix_2_delete_cross_area_near(rels, entity_map, set(f1_indices))
    print(f"Fix 2: Delete {len(f2_indices)} cross-area near relationships")

    # Fix 3
    f3_fixes = fix_3_infer_area(entities, entity_map)
    print(f"Fix 3: Infer area for {len(f3_fixes)} entities")
    for eid, area in f3_fixes[:5]:
        print(f"  {eid} → area={area}")

    # Fix 4
    f4_new = fix_4_add_located_in(entities, rels, entity_map)
    print(f"Fix 4: Add {len(f4_new)} located_in relationships")

    # Fix 5
    f5_fixes = fix_5_inherit_coordinates(entities, entity_map)
    print(f"Fix 5: Inherit coordinates for {len(f5_fixes)} entities")

    # Fix 6
    f6_new = fix_6_link_orphans_by_address(entities, rels, entity_map)
    print(f"Fix 6: Link {len(f6_new)} orphans by address matching")
    for r in f6_new[:5]:
        e = entity_map.get(r["from"], {})
        print(f"  {e.get('name', r['from'])[:35]} → {r['to']}")

    # Summary
    all_delete = set(f1_indices) | set(f2_indices)
    all_add = f4_new + f6_new
    print(f"\n{'=' * 50}")
    print(f"SUMMARY:")
    print(f"  Relationships deleted: {len(all_delete)}")
    print(f"  Relationships added:   {len(all_add)}")
    print(f"  Areas inferred:        {len(f3_fixes)}")
    print(f"  Coords inherited:      {len(f5_fixes)}")
    print(f"  Net relationships:     {len(rels) - len(all_delete) + len(all_add)}")

    if DRY_RUN:
        print(f"\n  → DRY RUN. Run with --apply to save changes.")
        return

    # Apply fixes
    print("\nApplying...")

    # Delete rels (reverse order to preserve indices)
    for i in sorted(all_delete, reverse=True):
        del rels[i]

    # Add new rels
    rels.extend(all_add)

    # Apply area fixes
    eid_map = {e["id"]: e for e in entities}
    for eid, area in f3_fixes:
        if eid in eid_map:
            eid_map[eid]["area"] = area

    # Apply coordinate fixes
    for eid, coords in f5_fixes:
        if eid in eid_map:
            eid_map[eid]["coordinates"] = coords

    data["relationships"] = rels
    save_data(data)

    print(f"Saved: {len(entities)} entities, {len(rels)} relationships")
    print("Run: python scripts/validate_data.py to verify.")


if __name__ == "__main__":
    main()
