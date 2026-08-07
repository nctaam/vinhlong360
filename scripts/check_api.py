import urllib.request
import json
import os

# Mặc định 8360 = y hệt trước; đặt AGENT_PORT khi backend chạy cổng khác.
BASE_URL = f"http://localhost:{os.environ.get('AGENT_PORT', '8360').strip() or '8360'}"

r = urllib.request.urlopen(f"{BASE_URL}/api/homepage")
d = json.loads(r.read())

print("=== SEASONAL ===")
for e in d.get("seasonal", []):
    print(f"  {e['type']} | {e['name']}")

print("\n=== UPCOMING EVENTS ===")
for e in d.get("upcoming_events", []):
    a = e.get("attributes", {})
    print(f"  {e['name']} | ds={a.get('date_start')} | lunar={a.get('lunar_date','')}")
