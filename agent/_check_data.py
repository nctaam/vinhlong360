"""DEPRECATED: This module is dead code (zero references in codebase).
One-time data diagnostic script. Use scripts/validate_data.py instead.
See docs/DEAD-CODE-AUDIT.md."""

import sys, json
sys.path.insert(0, "agent")
from database import Database
db = Database()
entities = db.list_entities(limit=9999)
print(f"Total entities: {len(entities)}")

types = {}
no_summary = 0
short_summary = 0
no_coords = 0
empty_attrs = 0

for e in entities:
    t = e["type"]
    types[t] = types.get(t, 0) + 1
    s = e.get("summary", "") or ""
    a = e.get("attributes") or {}
    if not s or len(s) < 10:
        no_summary += 1
    elif len(s) < 50:
        short_summary += 1
    if not e.get("coordinates"):
        no_coords += 1
    if not a or a == {} or a == "{}":
        empty_attrs += 1

print(f"Types: {json.dumps(types, ensure_ascii=False)}")
print(f"No summary: {no_summary}")
print(f"Short summary (<50): {short_summary}")
print(f"No coordinates: {no_coords}")
print(f"No/empty attrs: {empty_attrs}")

itins = db.list_itineraries()
print(f"Itineraries: {len(itins)}")
areas = set()
for it in itins:
    areas.add(it.get("area", ""))
print(f"Itinerary areas: {areas}")

# Sample entity
if entities:
    e = entities[0]
    print(f"\nSample entity keys: {list(e.keys())}")
    print(f"Sample: {json.dumps(e, ensure_ascii=False, default=str)[:500]}")
