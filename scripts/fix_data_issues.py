#!/usr/bin/env python3
"""Analyze and fix data quality issues in web/data.json.

Targets:
1. 9 broken relationships (reference missing entity IDs)
2. 110 produced_in relationships that cross conflicting entity areas

Run: python scripts/fix_data_issues.py --analyze   (dry run — just report)
Run: python scripts/fix_data_issues.py --fix        (apply fixes to data.json)
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "web" / "data.json"


def load_data() -> dict[str, Any]:
    with DATA_PATH.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def save_data(data: dict[str, Any]) -> None:
    with DATA_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Saved {DATA_PATH}")


def rel_source(rel: dict) -> str | None:
    v = rel.get("from") or rel.get("from_id") or rel.get("source_id")
    return str(v) if v else None


def rel_target(rel: dict) -> str | None:
    v = rel.get("to") or rel.get("to_id") or rel.get("target_id")
    return str(v) if v else None


def rel_type(rel: dict) -> str | None:
    v = rel.get("type") or rel.get("rel_type")
    return str(v) if v else None


def effective_area(entity: dict | None, entity_by_id: dict) -> str | None:
    if not isinstance(entity, dict):
        return None
    area = entity.get("area")
    if area:
        return str(area)
    place_id = entity.get("placeId")
    place = entity_by_id.get(str(place_id)) if place_id else None
    if isinstance(place, dict) and place.get("area"):
        return str(place["area"])
    return None


def analyze_broken_relationships(data: dict) -> list[dict]:
    """Find relationships that reference non-existent entity IDs."""
    entities = data.get("entities", [])
    relationships = data.get("relationships", [])
    id_set = {str(e["id"]) for e in entities if isinstance(e, dict) and e.get("id")}

    broken = []
    for idx, rel in enumerate(relationships):
        src = rel_source(rel)
        dst = rel_target(rel)
        kind = rel_type(rel)
        if not src or not dst or not kind:
            continue
        missing_src = src not in id_set
        missing_dst = dst not in id_set
        if missing_src or missing_dst:
            broken.append({
                "index": idx,
                "rel": rel,
                "src": src,
                "dst": dst,
                "type": kind,
                "missing_src": missing_src,
                "missing_dst": missing_dst,
            })
    return broken


def find_possible_replacement(missing_id: str, id_set: set[str], entity_by_id: dict) -> str | None:
    """Try to find a replacement for a missing ID.

    Common pattern: xa-* was renamed to p-* after sáp nhập migration.
    """
    # xa- -> p- migration
    if missing_id.startswith("xa-"):
        candidate = "p-" + missing_id[3:]
        if candidate in id_set:
            return candidate
    # p- -> xa- reverse (unlikely but check)
    if missing_id.startswith("p-"):
        candidate = "xa-" + missing_id[2:]
        if candidate in id_set:
            return candidate
    # Check for close matches (edit distance 1-2)
    # Simple: check if removing/adding a suffix works
    parts = missing_id.rsplit("-", 1)
    if len(parts) == 2:
        prefix = parts[0]
        matches = [eid for eid in id_set if eid.startswith(prefix + "-")]
        if len(matches) == 1:
            return matches[0]
    return None


def analyze_produced_in_conflicts(data: dict) -> list[dict]:
    """Find produced_in relationships where source and target have different areas."""
    entities = data.get("entities", [])
    relationships = data.get("relationships", [])
    entity_by_id = {
        str(e["id"]): e for e in entities
        if isinstance(e, dict) and e.get("id")
    }

    conflicts = []
    for idx, rel in enumerate(relationships):
        kind = rel_type(rel)
        if kind != "produced_in":
            continue
        src = rel_source(rel)
        dst = rel_target(rel)
        if not src or not dst:
            continue
        src_entity = entity_by_id.get(src)
        dst_entity = entity_by_id.get(dst)
        if not src_entity or not dst_entity:
            continue

        src_area = effective_area(src_entity, entity_by_id)
        dst_area = effective_area(dst_entity, entity_by_id)

        if src_area and dst_area and src_area != dst_area:
            # Determine the "correct" area based on the entity's own area vs placeId area
            src_own_area = src_entity.get("area")
            src_place_id = src_entity.get("placeId")
            src_place = entity_by_id.get(str(src_place_id)) if src_place_id else None
            src_place_area = src_place.get("area") if isinstance(src_place, dict) else None

            dst_own_area = dst_entity.get("area")
            dst_place_id = dst_entity.get("placeId")
            dst_place = entity_by_id.get(str(dst_place_id)) if dst_place_id else None
            dst_place_area = dst_place.get("area") if isinstance(dst_place, dict) else None

            conflicts.append({
                "index": idx,
                "rel": rel,
                "src_id": src,
                "dst_id": dst,
                "src_name": src_entity.get("name"),
                "dst_name": dst_entity.get("name"),
                "src_type": src_entity.get("type"),
                "dst_type": dst_entity.get("type"),
                "src_area": src_area,
                "dst_area": dst_area,
                "src_own_area": src_own_area,
                "src_place_id": src_place_id,
                "src_place_area": src_place_area,
                "dst_own_area": dst_own_area,
                "dst_place_id": dst_place_id,
                "dst_place_area": dst_place_area,
            })
    return conflicts


def fix_broken_relationships(data: dict) -> tuple[int, int, int]:
    """Fix broken relationships: remap fixable IDs, remove truly broken ones.

    Returns (fixed_count, removed_count, total_broken).
    """
    entities = data.get("entities", [])
    relationships = data.get("relationships", [])
    id_set = {str(e["id"]) for e in entities if isinstance(e, dict) and e.get("id")}
    entity_by_id = {
        str(e["id"]): e for e in entities
        if isinstance(e, dict) and e.get("id")
    }

    indices_to_remove = []
    fixed = 0
    remapped = 0

    for idx, rel in enumerate(relationships):
        src = rel_source(rel)
        dst = rel_target(rel)
        kind = rel_type(rel)
        if not src or not dst or not kind:
            continue

        missing_src = src not in id_set
        missing_dst = dst not in id_set

        if not missing_src and not missing_dst:
            continue

        # Try to fix
        new_src = src
        new_dst = dst
        src_fixed = False
        dst_fixed = False

        if missing_src:
            replacement = find_possible_replacement(src, id_set, entity_by_id)
            if replacement:
                new_src = replacement
                src_fixed = True

        if missing_dst:
            replacement = find_possible_replacement(dst, id_set, entity_by_id)
            if replacement:
                new_dst = replacement
                dst_fixed = True

        if (missing_src and not src_fixed) or (missing_dst and not dst_fixed):
            # Can't fix — mark for removal
            indices_to_remove.append(idx)
            still_missing = []
            if missing_src and not src_fixed:
                still_missing.append(f"src={src}")
            if missing_dst and not dst_fixed:
                still_missing.append(f"dst={dst}")
            print(f"  REMOVE rel[{idx}]: {src} --{kind}--> {dst} (missing: {', '.join(still_missing)})")
        else:
            # Apply fixes
            if src_fixed:
                # Update the source field
                if "from" in rel:
                    rel["from"] = new_src
                elif "from_id" in rel:
                    rel["from_id"] = new_src
                elif "source_id" in rel:
                    rel["source_id"] = new_src
                print(f"  REMAP rel[{idx}] src: {src} -> {new_src} ({kind})")
                remapped += 1

            if dst_fixed:
                if "to" in rel:
                    rel["to"] = new_dst
                elif "to_id" in rel:
                    rel["to_id"] = new_dst
                elif "target_id" in rel:
                    rel["target_id"] = new_dst
                print(f"  REMAP rel[{idx}] dst: {dst} -> {new_dst} ({kind})")
                remapped += 1

            fixed += 1

    # Remove broken relationships (reverse order to preserve indices)
    removed = len(indices_to_remove)
    for idx in sorted(indices_to_remove, reverse=True):
        relationships.pop(idx)

    return fixed, removed, fixed + removed


def fix_produced_in_area_conflicts(data: dict) -> int:
    """Fix produced_in area conflicts by removing cross-area relationships.

    Analysis shows that these 110 conflicts are bogus cross-province
    produced_in links, e.g. a Vinh Long product linked to a Ben Tre
    craft village. The entity areas are correct — the relationships
    are wrong. The correct fix is to remove these invalid relationships.

    "produced_in" means the product/dish is produced at a specific
    craft village or place. A product from province A cannot be
    "produced in" a craft village in province B.
    """
    entities = data.get("entities", [])
    relationships = data.get("relationships", [])
    entity_by_id = {
        str(e["id"]): e for e in entities
        if isinstance(e, dict) and e.get("id")
    }

    indices_to_remove = []

    for idx, rel in enumerate(relationships):
        kind = rel_type(rel)
        if kind != "produced_in":
            continue
        src_id = rel_source(rel)
        dst_id = rel_target(rel)
        if not src_id or not dst_id:
            continue
        src_entity = entity_by_id.get(src_id)
        dst_entity = entity_by_id.get(dst_id)
        if not src_entity or not dst_entity:
            continue

        src_area = effective_area(src_entity, entity_by_id)
        dst_area = effective_area(dst_entity, entity_by_id)

        if src_area and dst_area and src_area != dst_area:
            indices_to_remove.append(idx)
            print(f"  REMOVE rel[{idx}]: {src_id} ({src_entity.get('name')}, area={src_area})"
                  f" --produced_in--> {dst_id} ({dst_entity.get('name')}, area={dst_area})")

    # Remove in reverse order to preserve indices
    for idx in sorted(indices_to_remove, reverse=True):
        relationships.pop(idx)

    return len(indices_to_remove)


def main():
    # Fix encoding for Windows console
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    if len(sys.argv) < 2 or sys.argv[1] not in ("--analyze", "--fix"):
        print("Usage: python scripts/fix_data_issues.py [--analyze | --fix]")
        sys.exit(1)

    mode = sys.argv[1]
    data = load_data()

    print("=" * 70)
    print("ANALYSIS: Broken relationships")
    print("=" * 70)
    broken = analyze_broken_relationships(data)
    entities = data.get("entities", [])
    id_set = {str(e["id"]) for e in entities if isinstance(e, dict) and e.get("id")}
    entity_by_id = {
        str(e["id"]): e for e in entities
        if isinstance(e, dict) and e.get("id")
    }

    for b in broken:
        src = b["src"]
        dst = b["dst"]
        kind = b["type"]
        parts = []
        if b["missing_src"]:
            repl = find_possible_replacement(src, id_set, entity_by_id)
            parts.append(f"  MISSING src: {src}" + (f" -> candidate: {repl}" if repl else " -> NO CANDIDATE"))
        if b["missing_dst"]:
            repl = find_possible_replacement(dst, id_set, entity_by_id)
            parts.append(f"  MISSING dst: {dst}" + (f" -> candidate: {repl}" if repl else " -> NO CANDIDATE"))

        src_name = entity_by_id.get(src, {}).get("name", "???")
        dst_name = entity_by_id.get(dst, {}).get("name", "???")
        print(f"\nrel[{b['index']}]: {src} ({src_name}) --{kind}--> {dst} ({dst_name})")
        for p in parts:
            print(p)

    print(f"\nTotal broken: {len(broken)}")

    print("\n" + "=" * 70)
    print("ANALYSIS: produced_in area conflicts")
    print("=" * 70)
    conflicts = analyze_produced_in_conflicts(data)

    # Summarize the patterns
    pattern_counter: Counter[tuple[str, str]] = Counter()
    for c in conflicts:
        pattern_counter[(c["src_area"], c["dst_area"])] += 1

    print(f"\nTotal conflicts: {len(conflicts)}")
    print("\nArea mismatch patterns (src_area -> dst_area): count")
    for (sa, da), count in pattern_counter.most_common():
        print(f"  {sa} -> {da}: {count}")

    # Show first few examples of each pattern
    print("\nExamples of each pattern:")
    shown: Counter[tuple[str, str]] = Counter()
    for c in conflicts:
        key = (c["src_area"], c["dst_area"])
        if shown[key] < 3:
            print(f"\n  [{c['src_area']} -> {c['dst_area']}]")
            print(f"    src: {c['src_id']} ({c['src_name']}, type={c['src_type']})")
            print(f"      own area: {c['src_own_area']}, placeId: {c['src_place_id']}, place area: {c['src_place_area']}")
            print(f"    dst: {c['dst_id']} ({c['dst_name']}, type={c['dst_type']})")
            print(f"      own area: {c['dst_own_area']}, placeId: {c['dst_place_id']}, place area: {c['dst_place_area']}")
            shown[key] += 1

    if mode == "--fix":
        print("\n" + "=" * 70)
        print("FIXING: Broken relationships")
        print("=" * 70)
        fixed, removed, total = fix_broken_relationships(data)
        print(f"\nResult: {fixed} remapped, {removed} removed (total {total} broken)")

        print("\n" + "=" * 70)
        print("FIXING: produced_in area conflicts (removing cross-area rels)")
        print("=" * 70)
        area_fixed = fix_produced_in_area_conflicts(data)
        print(f"\nResult: {area_fixed} cross-area produced_in relationships removed")

        save_data(data)
        print("\nDone! Run 'python scripts/validate_data.py' to verify.")


if __name__ == "__main__":
    main()
