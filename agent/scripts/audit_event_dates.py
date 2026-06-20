"""Audit events: which have no dates, which have lunar dates."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, ".")
from database import db
db.initialize()

events = db.list_entities(entity_type="event", limit=10000)
print(f"Total events: {len(events)}")

print("\n=== NO DATE_START (candidates for removal) ===")
no_date = []
for e in sorted(events, key=lambda x: x["name"]):
    attrs = e.get("attributes") or {}
    ds = attrs.get("date_start", "")
    cat = attrs.get("category", "")
    lunar = attrs.get("lunar_date", "")
    if not ds:
        no_date.append(e)
        print(f"  {e['id']} | {e['name']} | cat={cat} | lunar={lunar}")
print(f"  Count: {len(no_date)}")

print("\n=== LE-HOI WITH LUNAR_DATE ===")
lunar_fests = []
for e in sorted(events, key=lambda x: x["name"]):
    attrs = e.get("attributes") or {}
    ds = attrs.get("date_start", "")
    cat = attrs.get("category", "")
    lunar = attrs.get("lunar_date", "")
    if cat == "le-hoi" and lunar:
        lunar_fests.append(e)
        print(f"  {e['id']} | {e['name']} | ds={ds} | lunar={lunar}")
print(f"  Count: {len(lunar_fests)}")

print("\n=== LE-HOI WITHOUT LUNAR AND WITHOUT DATE_START ===")
for e in sorted(events, key=lambda x: x["name"]):
    attrs = e.get("attributes") or {}
    ds = attrs.get("date_start", "")
    cat = attrs.get("category", "")
    lunar = attrs.get("lunar_date", "")
    if cat == "le-hoi" and not lunar and not ds:
        print(f"  {e['id']} | {e['name']}")
