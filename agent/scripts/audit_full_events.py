"""Full audit of all 78 events — check duplicates, date issues, data quality."""
import sys, io, json
from collections import defaultdict
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, ".")
from database import db
db.initialize()

events = db.list_entities(entity_type="event", limit=10000)
print(f"Total: {len(events)}\n")

# 1. Check for near-duplicate names
print("=== POTENTIAL DUPLICATES (similar names) ===")
names = [(e["id"], e["name"]) for e in events]
seen = []
for i, (id1, n1) in enumerate(names):
    for id2, n2 in names[i+1:]:
        # simple word overlap check
        w1 = set(n1.lower().split())
        w2 = set(n2.lower().split())
        overlap = len(w1 & w2) / max(len(w1 | w2), 1)
        if overlap > 0.5:
            print(f"  ~{overlap:.0%} | {id1} ({n1})")
            print(f"       | {id2} ({n2})")

# 2. Date anomalies
print("\n=== DATE ANOMALIES ===")
for e in sorted(events, key=lambda x: (x.get("attributes") or {}).get("date_start", "")):
    attrs = e.get("attributes") or {}
    ds = attrs.get("date_start", "")
    de = attrs.get("date_end", "")
    if not ds:
        print(f"  NO DATE: {e['id']} | {e['name']}")
        continue
    if de and de < ds:
        print(f"  END<START: {e['id']} | {ds}~{de}")
    from datetime import datetime
    try:
        d1 = datetime.strptime(ds, "%Y-%m-%d")
        d2 = datetime.strptime(de, "%Y-%m-%d") if de else d1
        span = (d2 - d1).days
        if span > 60:
            print(f"  LONG SPAN ({span}d): {e['id']} | {e['name']} | {ds}~{de}")
        if d1.year != 2026:
            print(f"  WRONG YEAR: {e['id']} | {ds}")
    except (ValueError, TypeError):
        print(f"  BAD DATE: {e['id']} | {ds}~{de}")

# 3. Missing fields
print("\n=== MISSING AREA ===")
for e in events:
    if not e.get("area"):
        print(f"  {e['id']} | {e['name']}")

print("\n=== MISSING SUMMARY ===")
for e in events:
    s = e.get("summary") or ""
    if len(s) < 20:
        print(f"  {e['id']} | {e['name']} | summary={s[:50]}")

# 4. Category breakdown
print("\n=== CATEGORY BREAKDOWN ===")
cats = defaultdict(list)
for e in events:
    cat = (e.get("attributes") or {}).get("category", "?")
    cats[cat].append(e["name"])
for cat, names in sorted(cats.items()):
    print(f"  {cat}: {len(names)}")

# 5. Le-hoi without lunar_date
print("\n=== LE-HOI WITHOUT LUNAR_DATE ===")
for e in sorted(events, key=lambda x: x["name"]):
    attrs = e.get("attributes") or {}
    if attrs.get("category") == "le-hoi" and not attrs.get("lunar_date"):
        print(f"  {e['id']} | {e['name']} | {attrs.get('date_start','')}~{attrs.get('date_end','')}")

# 6. Su-kien with suspicious names (contains "lễ hội")
print("\n=== SU-KIEN WITH 'lễ hội' IN NAME ===")
for e in events:
    attrs = e.get("attributes") or {}
    if attrs.get("category") == "su-kien" and "lễ hội" in e["name"].lower():
        print(f"  {e['id']} | {e['name']}")

# 7. All events sorted by date for final review
print("\n=== FULL LIST BY DATE ===")
for e in sorted(events, key=lambda x: (x.get("attributes") or {}).get("date_start", "zzz")):
    attrs = e.get("attributes") or {}
    ds = attrs.get("date_start", "?")
    de = attrs.get("date_end", "?")
    cat = attrs.get("category", "?")
    lunar = attrs.get("lunar_date", "")
    area = e.get("area", "?")
    lunar_str = f" 🌙{lunar}" if lunar else ""
    print(f"  [{cat:7s}] {ds}~{de} | {e['name']} | {area}{lunar_str}")
