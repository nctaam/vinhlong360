"""Audit all event entities for classification."""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, ".")
from database import db
db.initialize()

events = db.list_entities(entity_type="event", limit=10000)
for e in sorted(events, key=lambda x: x["name"]):
    eid = e["id"]
    name = e["name"]
    attrs = e.get("attributes") or {}
    ds = attrs.get("date_start", "")
    de = attrs.get("date_end", "")
    area = e.get("area", "")
    print(f"{eid} | {name} | {ds}~{de} | {area}")

print(f"\nTotal: {len(events)}")
