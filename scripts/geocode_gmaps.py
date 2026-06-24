"""
geocode_gmaps.py — Upgrade approximate coordinates using Google Maps Geocoding API.

Requires GOOGLE_MAPS_API_KEY environment variable.
Free tier: $200/month credit = ~40,000 geocode calls/month.

Usage:
  $env:GOOGLE_MAPS_API_KEY='YOUR_KEY'
  python scripts/geocode_gmaps.py              # dry-run (first 10)
  python scripts/geocode_gmaps.py --apply      # apply all
  python scripts/geocode_gmaps.py --limit 50   # limit batch size

§B1: ALWAYS run scripts/backup_data.py BEFORE --apply.
"""

import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

DATA_PATH = Path(__file__).resolve().parent.parent / "web" / "data.json"
DRY_RUN = "--apply" not in sys.argv
API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")
LIMIT = 10

for i, arg in enumerate(sys.argv):
    if arg == "--limit" and i + 1 < len(sys.argv):
        LIMIT = int(sys.argv[i + 1])

LAT_MIN, LAT_MAX = 9.4, 10.7
LNG_MIN, LNG_MAX = 105.5, 107.0

AREA_NAMES = {
    "vinh-long": "Vĩnh Long",
    "ben-tre": "Bến Tre",
    "tra-vinh": "Trà Vinh",
}


def geocode_google(query):
    if not API_KEY:
        return None
    params = urllib.parse.urlencode({
        "address": query,
        "key": API_KEY,
        "region": "vn",
        "language": "vi",
    })
    url = f"https://maps.googleapis.com/maps/api/geocode/json?{params}"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("status") == "OK" and data.get("results"):
                loc = data["results"][0]["geometry"]["location"]
                lat, lng = loc["lat"], loc["lng"]
                if LAT_MIN <= lat <= LAT_MAX and LNG_MIN <= lng <= LNG_MAX:
                    return (round(lat, 7), round(lng, 7))
    except Exception as e:
        print(f"    Error: {e}")
    return None


def main():
    if not API_KEY:
        print("ERROR: Set GOOGLE_MAPS_API_KEY environment variable.")
        print("  PowerShell: $env:GOOGLE_MAPS_API_KEY='AIza...'")
        print("  Then re-run this script.")
        sys.exit(1)

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    entities = data["entities"]
    priority_types = {"restaurant", "cafe", "accommodation", "attraction", "facility", "market"}

    targets = []
    for e in entities:
        c = e.get("coordinates")
        if not (isinstance(c, list) and len(c) >= 2):
            continue
        if not (e.get("attributes") or {}).get("coords_approximate"):
            continue
        if e.get("type") not in priority_types:
            continue

        addr = (e.get("attributes") or {}).get("address", "")
        area = AREA_NAMES.get(e.get("area", ""), "")
        if addr:
            query = f"{addr}, {area}" if area else addr
        else:
            query = f"{e.get('name', '')}, {area}" if area else e.get("name", "")

        targets.append({"id": e["id"], "name": e.get("name", ""), "query": query, "area": e.get("area", "")})

    targets = targets[:LIMIT]
    print(f"{'DRY RUN' if DRY_RUN else 'APPLYING'}: {len(targets)} entities to geocode\n")

    results = []
    for i, t in enumerate(targets):
        coords = geocode_google(t["query"])
        status = f"[{coords[0]:.7f}, {coords[1]:.7f}]" if coords else "MISS"
        results.append((t["id"], t["name"], coords))
        print(f"  [{i+1:3d}/{len(targets)}] {status:30s} {t['name'][:40]}")
        time.sleep(0.05)

    found = [r for r in results if r[2]]
    print(f"\nFound: {len(found)}/{len(targets)}")

    if DRY_RUN:
        print("\n→ DRY RUN. Run with --apply to save.")
        return

    if not found:
        print("No coordinates to apply.")
        return

    emap = {e["id"]: e for e in entities}
    for eid, _, coords in found:
        if eid in emap and coords:
            emap[eid]["coordinates"] = [coords[0], coords[1]]
            attrs = emap[eid].get("attributes") or {}
            if "coords_approximate" in attrs:
                del attrs["coords_approximate"]
            emap[eid]["attributes"] = attrs

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\nUpgraded {len(found)} coordinates (removed coords_approximate flag).")


if __name__ == "__main__":
    main()
