"""U1.1 — Normalize attribute key aliases to canonical names.

Reads all entities from DB, renames alias keys → canonical,
writes back via db.upsert_entity(), then exports data.json.

Run backup_data.py BEFORE this script (B1).
"""
import sys, os, subprocess
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ALIAS_MAP = {
    "operating_hours": "hours",
    "open_on": "hours",          # 14 entities, all overlap with hours → drop
    "open_hours": "hours",
    "opening_hours": "hours",
    "admission_fee": "admission",
    "best_time_to_visit": "best_time",
    "priceRange": "price_range",
    "bestSeason": "season_note",
    "bestTime": "best_time",
    "checkin": "check_in",
    "checkout": "check_out",
    "highlights": "highlight",
    "booking": "booking_note",
    "location": "address",
    "foodyRating": "rating",
    "foodyComments": "review_count",
}

def normalize(attrs: dict) -> tuple[dict, list[str]]:
    """Return (normalized_attrs, list_of_changes)."""
    result = {}
    changes = []
    for k, v in attrs.items():
        canonical = ALIAS_MAP.get(k, k)
        if canonical != k:
            if canonical in attrs or canonical in result:
                changes.append(f"  dropped {k} (canonical {canonical} already exists)")
                continue
            changes.append(f"  {k} -> {canonical}")
        result[canonical] = v
    return result, changes

def main():
    from agent.database import Database
    db = Database()
    db.initialize()
    entities = db.all_entities()

    total_changed = 0
    total_renames = 0
    for e in entities:
        attrs = e.get("attributes", {})
        if not isinstance(attrs, dict):
            continue
        new_attrs, changes = normalize(attrs)
        if changes:
            total_changed += 1
            total_renames += len(changes)
            print(f"[{e['id']}] {e['name']}")
            for c in changes:
                print(c)
            e["attributes"] = new_attrs
            db.upsert_entity(e)

    print(f"\nDone: {total_changed} entities updated, {total_renames} attribute renames")

    # Export data.json
    import json
    print("Exporting data.json...")
    entities = db.all_entities()
    relationships = db.all_relationships()
    itineraries = db.all_itineraries()
    data = {"entities": entities, "relationships": relationships, "itineraries": itineraries}
    with open("web/data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Exported {len(entities)} entities, {len(relationships)} rels, {len(itineraries)} itineraries")

if __name__ == "__main__":
    main()
