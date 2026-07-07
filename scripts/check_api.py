import urllib.request
import json
import sys

r = urllib.request.urlopen("http://localhost:8360/api/homepage")
d = json.loads(r.read())

print("=== SEASONAL ===")
for e in d.get("seasonal", []):
    print(f"  {e['type']} | {e['name']}")

print("\n=== UPCOMING EVENTS ===")
for e in d.get("upcoming_events", []):
    a = e.get("attributes", {})
    print(f"  {e['name']} | ds={a.get('date_start')} | lunar={a.get('lunar_date','')}")
