"""Show all events with details for review."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, ".")
from database import db
db.initialize()

events = db.list_entities(entity_type="event", limit=10000)

for cat_label, cat_key in [("LE-HOI", "le-hoi"), ("SU-KIEN", "su-kien"), ("MUA", "mua")]:
    group = [e for e in events if (e.get("attributes") or {}).get("category", "su-kien") == cat_key]
    group.sort(key=lambda x: (x.get("attributes") or {}).get("date_start", ""))
    print(f"\n{'='*60}")
    print(f"  {cat_label} ({len(group)})")
    print(f"{'='*60}")
    for e in group:
        attrs = e.get("attributes") or {}
        ds = attrs.get("date_start", "?")
        de = attrs.get("date_end", "?")
        lunar = attrs.get("lunar_date", "")
        area = e.get("area", "")
        summary = (e.get("summary") or "")[:80]
        print(f"\n  {e['id']}")
        print(f"    {e['name']}")
        print(f"    dates: {ds} ~ {de}  |  area: {area}")
        if lunar:
            print(f"    lunar: {lunar}")
        print(f"    summary: {summary}")
