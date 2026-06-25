#!/usr/bin/env python3
"""Import travel_tips and best_time from enrichment JSONL into entity attributes.

Merges new tips into existing attributes JSON without overwriting existing values.
"""
import json, sqlite3, sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT / "agent" / "data" / "vinhlong360.db"
ENRICHMENT_DIR = PROJECT / "agent" / "data" / "enrichment"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def load_enrichments():
    """Load enrichment data, deduplicate by entity_id (last wins)."""
    records = {}
    for f in sorted(ENRICHMENT_DIR.glob("enrich_*.jsonl")):
        for line in open(f, encoding="utf-8"):
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            eid = r.get("entity_id", "")
            enrichment = r.get("enrichment", {})
            if not eid:
                continue
            records[eid] = enrichment
    return records


def main():
    enrichments = load_enrichments()
    print(f"Loaded {len(enrichments)} enrichment records")

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    updated = 0
    tips_added = 0
    best_time_added = 0
    hook_added = 0

    for eid, enrichment in enrichments.items():
        cur.execute("SELECT id, attributes FROM entities WHERE id = ?", (eid,))
        row = cur.fetchone()
        if not row:
            continue

        attrs = {}
        try:
            attrs = json.loads(row["attributes"]) if row["attributes"] else {}
        except Exception:
            attrs = {}

        changed = False

        # Import travel_tips (as a list)
        tips = enrichment.get("travel_tips", [])
        if tips and isinstance(tips, list) and not attrs.get("travel_tips"):
            attrs["travel_tips"] = tips[:3]  # Keep top 3
            tips_added += 1
            changed = True

        # Import best_time
        best_time = enrichment.get("best_time", "")
        if best_time and not attrs.get("best_time"):
            attrs["best_time"] = best_time
            best_time_added += 1
            changed = True

        # Import emotional_hook as highlight
        hook = enrichment.get("emotional_hook", "")
        if hook and not attrs.get("highlight"):
            attrs["highlight"] = hook
            hook_added += 1
            changed = True

        if changed:
            cur.execute(
                "UPDATE entities SET attributes = ? WHERE id = ?",
                (json.dumps(attrs, ensure_ascii=False), eid),
            )
            updated += 1

    conn.commit()
    conn.close()

    print(f"\nResults:")
    print(f"  Entities updated: {updated}")
    print(f"  Travel tips added: {tips_added}")
    print(f"  Best time added: {best_time_added}")
    print(f"  Highlight/hook added: {hook_added}")


if __name__ == "__main__":
    main()
