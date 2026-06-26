"""
Merge enriched entities from backup with new entities in current data.json.

Used when two agents modify data.json concurrently:
- Agent A: enriches existing 202 entities (coords, attrs, longer summary)
- Agent B: adds 81 new entities + 15 itineraries + 83 relationships

This script merges both: takes enriched versions of originals + adds new ones.
"""
import json
import sys
import shutil
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

DATA_FILE = Path(__file__).resolve().parent.parent / "web" / "data.json"
BACKUP_DIR = Path(__file__).resolve().parent / "data" / "merge_backup"


def merge_enriched_into_current(enriched_path: str):
    """
    Merge enriched entity data into the current data.json.

    Takes the richer summary/attrs/coords from enriched version
    for original entities, keeps new entities as-is.
    """
    current = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    enriched = json.loads(Path(enriched_path).read_text(encoding="utf-8"))

    # Build lookup of enriched entities by ID
    enriched_by_id = {e["id"]: e for e in enriched["entities"]}

    # Build set of original entity IDs (from enriched, which has only original entities)
    original_ids = set(enriched_by_id.keys())

    # Current entities include both original + new
    current_by_id = {e["id"]: e for e in current["entities"]}
    new_entity_ids = set(current_by_id.keys()) - original_ids

    print(f"Original entities (enriched): {len(original_ids)}")
    print(f"New entities (to keep): {len(new_entity_ids)}")

    # Merge: for each entity
    merged_entities = []

    # First, add all enriched originals
    for eid, enriched_entity in enriched_by_id.items():
        current_entity = current_by_id.get(eid, enriched_entity)

        # Take the RICHER version of each field
        merged = {**current_entity}

        # Summary: take longer one
        if len(enriched_entity.get("summary", "")) > len(merged.get("summary", "")):
            merged["summary"] = enriched_entity["summary"]

        # Coords: take enriched if current doesn't have
        if enriched_entity.get("coords") and not merged.get("coords"):
            merged["coords"] = enriched_entity["coords"]

        # Attributes: merge (enriched wins for overlapping keys)
        if enriched_entity.get("attributes"):
            if not merged.get("attributes"):
                merged["attributes"] = {}
            merged["attributes"] = {**merged.get("attributes", {}), **enriched_entity["attributes"]}

        # Season: take enriched if current is empty
        if enriched_entity.get("season") and not merged.get("season"):
            merged["season"] = enriched_entity["season"]

        merged_entities.append(merged)

    # Then add all new entities
    for eid in new_entity_ids:
        merged_entities.append(current_by_id[eid])

    print(f"Merged total: {len(merged_entities)} entities")

    # Keep current relationships + itineraries (agent B's version has more)
    result = {
        "entities": merged_entities,
        "relationships": current.get("relationships", enriched.get("relationships", [])),
        "itineraries": current.get("itineraries", enriched.get("itineraries", [])),
        "ALL_MONTHS": current.get("ALL_MONTHS", enriched.get("ALL_MONTHS", [])),
    }

    # Backup current
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_path = BACKUP_DIR / "data_pre_merge.json"
    shutil.copy2(DATA_FILE, backup_path)
    print(f"Backup: {backup_path}")

    # Write merged (atomic: tmp + replace)
    tmp = DATA_FILE.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    tmp.replace(DATA_FILE)

    # Verify
    verify = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    types = {}
    for e in verify["entities"]:
        t = e.get("type", "?")
        types[t] = types.get(t, 0) + 1

    has_coords = sum(1 for e in verify["entities"] if e.get("coords"))
    has_attrs = sum(1 for e in verify["entities"] if e.get("attributes") and len(e["attributes"]) > 0)
    long_summary = sum(1 for e in verify["entities"] if len(e.get("summary", "")) > 100)

    print(f"\nFinal data.json:")
    print(f"  Total entities: {len(verify['entities'])}")
    for t, c in sorted(types.items(), key=lambda x: -x[1]):
        print(f"    {t}: {c}")
    print(f"  Relationships: {len(verify.get('relationships', []))}")
    print(f"  Itineraries: {len(verify.get('itineraries', []))}")
    print(f"  Has coords: {has_coords}")
    print(f"  Has attributes: {has_attrs}")
    print(f"  Summary >100 chars: {long_summary}")

    return len(verify["entities"])


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python merge_data.py <enriched_data.json>")
        sys.exit(1)
    merge_enriched_into_current(sys.argv[1])
