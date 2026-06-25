#!/usr/bin/env python3
"""Import enrichment descriptions into the entities table.

Reads JSONL files from agent/data/enrichment/, deduplicates by entity_id
(latest record wins), and updates the `description` column in the DB.
Only updates entities that currently have an empty description.
"""
import json, sqlite3, sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT / "agent" / "data" / "vinhlong360.db"
ENRICHMENT_DIR = PROJECT / "agent" / "data" / "enrichment"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def load_enrichments():
    """Load all enrichment JSONL files, deduplicate by entity_id (last wins)."""
    records = {}
    files = sorted(ENRICHMENT_DIR.glob("enrich_*.jsonl"))
    for f in files:
        for line in open(f, encoding="utf-8"):
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            eid = r.get("entity_id", "")
            enrichment = r.get("enrichment", {})
            desc = enrichment.get("description", "")
            if eid and desc and len(desc) > 50:
                records[eid] = desc
    return records


def main():
    enrichments = load_enrichments()
    print(f"Loaded {len(enrichments)} unique entity descriptions from enrichment files")

    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    # Count entities with empty description
    cur.execute("SELECT COUNT(*) FROM entities WHERE description IS NULL OR description = ''")
    empty_count = cur.fetchone()[0]
    print(f"Entities with empty description: {empty_count}")

    updated = 0
    skipped = 0
    not_found = 0

    for eid, desc in enrichments.items():
        # Only update if entity exists and has empty description
        cur.execute(
            "UPDATE entities SET description = ? WHERE id = ? AND (description IS NULL OR description = '')",
            (desc, eid),
        )
        if cur.rowcount > 0:
            updated += 1
        else:
            # Check if entity exists at all
            cur.execute("SELECT id, description FROM entities WHERE id = ?", (eid,))
            row = cur.fetchone()
            if row is None:
                not_found += 1
            else:
                skipped += 1  # already has description

    conn.commit()

    # Verify
    cur.execute("SELECT COUNT(*) FROM entities WHERE description IS NOT NULL AND description != ''")
    total_with_desc = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM entities")
    total = cur.fetchone()[0]

    conn.close()

    print(f"\nResults:")
    print(f"  Updated:   {updated}")
    print(f"  Skipped:   {skipped} (already had description)")
    print(f"  Not found: {not_found} (entity ID not in DB)")
    print(f"\nDB state: {total_with_desc}/{total} entities now have descriptions")


if __name__ == "__main__":
    main()
