#!/usr/bin/env python3
"""Re-geocode entities đang dùng toạ độ trung tâm thành phố.

Dùng Nominatim (OpenStreetMap) — miễn phí, rate limit 1 req/s.
Chỉ update nếu kết quả nằm trong vùng VL+BT+TV.

Usage:
  python scripts/geocode_clusters.py                    # dry-run, show stats
  python scripts/geocode_clusters.py --apply            # geocode + update DB
  python scripts/geocode_clusters.py --apply --limit 50 # giới hạn 50 entities
  python scripts/geocode_clusters.py --city vinh-long   # chỉ 1 thành phố
"""

import argparse
import json
import sys
import time
import urllib.request
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENT_DIR = ROOT / "agent"
SCRATCH = ROOT / "scratch"
sys.path.insert(0, str(AGENT_DIR))

CITY_CENTERS = {
    "vinh-long": (10.254177, 105.962769),
    "ben-tre":   (10.227225, 106.407197),
    "tra-vinh":  (9.951624,  106.332233),
}
CLUSTER_RADIUS = 0.0005

REGION_BOUNDS = {
    "lat_min": 9.4, "lat_max": 10.5,
    "lon_min": 105.5, "lon_max": 107.0,
}

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "vinhlong360-geocoder/1.0 (data-quality-fix)"


def is_city_center(coords):
    if not coords or len(coords) != 2:
        return None
    for city, (clat, clon) in CITY_CENTERS.items():
        if abs(coords[0] - clat) < CLUSTER_RADIUS and abs(coords[1] - clon) < CLUSTER_RADIUS:
            return city
    return None


def in_region(lat, lon):
    return (REGION_BOUNDS["lat_min"] <= lat <= REGION_BOUNDS["lat_max"] and
            REGION_BOUNDS["lon_min"] <= lon <= REGION_BOUNDS["lon_max"])


def geocode_address(address, area_hint=""):
    query = address
    if area_hint:
        area_name = {"vinh-long": "Vĩnh Long", "ben-tre": "Bến Tre",
                     "tra-vinh": "Trà Vinh"}.get(area_hint, "")
        if area_name and area_name.lower() not in address.lower():
            query = f"{address}, {area_name}"

    params = urllib.parse.urlencode({
        "q": query,
        "format": "json",
        "limit": 1,
        "countrycodes": "vn",
    })
    url = f"{NOMINATIM_URL}?{params}"

    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return None, str(e)

    if not data:
        return None, "no results"

    result = data[0]
    lat = float(result["lat"])
    lon = float(result["lon"])

    if not in_region(lat, lon):
        return None, f"out of region: [{lat}, {lon}]"

    old_city = is_city_center([lat, lon])
    if old_city:
        return None, f"still at city center: {old_city}"

    return [lat, lon], result.get("display_name", "")


def _collect_targets(entities, args):
    targets = []
    for e in entities:
        if e.get("type") == "place":
            continue
        city = is_city_center(e.get("coordinates"))
        if not city:
            continue
        if args.city and city != args.city:
            continue
        addr = (e.get("attributes") or {}).get("address", "")
        if not addr or len(addr) < 10:
            continue
        targets.append({"entity": e, "city": city, "address": addr})
    return targets


def _print_dry_run(targets):
    print("\nDRY-RUN — samples:")
    for t in targets[:15]:
        e = t["entity"]
        print(f"  {e['id']:45s} {t['city']:10s} {t['address'][:60]}")
    if len(targets) > 15:
        print(f"  ... and {len(targets)-15} more")
    print(f"\nRun with --apply to geocode (rate: ~1/sec, est. {len(targets)} seconds)")


def _apply_one(log, db, i, t, total):
    e = t["entity"]
    eid = e["id"]
    addr = t["address"]
    city = t["city"]

    new_coords, detail = geocode_address(addr, city)

    entry = {
        "id": eid, "address": addr, "city": city,
        "old_coords": e.get("coordinates"),
        "new_coords": new_coords, "detail": detail,
    }
    log.write(json.dumps(entry, ensure_ascii=False) + "\n")

    if new_coords:
        e["coordinates"] = new_coords
        db.upsert_entity(e)
        print(f"  [{i+1}/{total}] OK  {eid[:40]} -> {new_coords}")
        return True
    print(f"  [{i+1}/{total}] SKIP {eid[:40]} ({detail})")
    return False


def _apply_geocode(targets, db):
    SCRATCH.mkdir(parents=True, exist_ok=True)
    log_path = SCRATCH / "geocode-log.jsonl"

    success = 0
    fail = 0

    with open(log_path, "a", encoding="utf-8") as log:
        for i, t in enumerate(targets):
            if _apply_one(log, db, i, t, len(targets)):
                success += 1
            else:
                fail += 1
            time.sleep(1.1)

    print(f"\nDone: {success} updated, {fail} skipped")
    print(f"Log: {log_path}")


def main():
    ap = argparse.ArgumentParser(description="Re-geocode city-center entities")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="Max entities to geocode")
    ap.add_argument("--city", choices=list(CITY_CENTERS.keys()))
    args = ap.parse_args()

    from database import db

    targets = _collect_targets(db.all_entities(), args)

    print(f"Entities at city center with address: {len(targets)}")
    if args.limit:
        targets = targets[:args.limit]
        print(f"Limited to: {args.limit}")

    if not args.apply:
        _print_dry_run(targets)
        return

    _apply_geocode(targets, db)


if __name__ == "__main__":
    main()
