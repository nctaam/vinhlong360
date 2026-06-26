"""
geocode_missing.py — Geocode entities missing coordinates using Nominatim.

Usage:
  python scripts/geocode_missing.py              # dry-run
  python scripts/geocode_missing.py --apply      # apply to data.json

Nominatim usage policy: max 1 req/s, with User-Agent.
"""

import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent.parent / "web" / "data.json"
DRY_RUN = "--apply" not in sys.argv
USER_AGENT = "vinhlong360-geocoder/1.0 (data-normalization)"

LAT_MIN, LAT_MAX = 9.4, 10.7
LNG_MIN, LNG_MAX = 105.5, 107.0


def geocode(query: str) -> tuple[float, float] | None:
    """Query Nominatim for coordinates. Returns (lat, lng) or None."""
    params = urllib.parse.urlencode({
        "q": query,
        "format": "json",
        "limit": 1,
        "countrycodes": "vn",
    })
    url = f"https://nominatim.openstreetmap.org/search?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data:
                lat = float(data[0]["lat"])
                lng = float(data[0]["lon"])
                if LAT_MIN <= lat <= LAT_MAX and LNG_MIN <= lng <= LNG_MAX:
                    return (lat, lng)
    except Exception as e:
        print(f"    Error: {e}")
    return None


def clean_address(addr: str) -> str:
    """Simplify address for better geocoding."""
    addr = re.sub(r"\s*,\s*Vĩnh Long$", ", Vinh Long, Vietnam", addr)
    addr = re.sub(r"\s*,\s*Bến Tre$", ", Ben Tre, Vietnam", addr)
    addr = re.sub(r"\s*,\s*Trà Vinh$", ", Tra Vinh, Vietnam", addr)
    addr = re.sub(r"Phường\s*", "P. ", addr)
    addr = re.sub(r"Thành phố\s*", "TP. ", addr)
    addr = re.sub(r"\s+", " ", addr).strip()
    return addr


def main():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    entities = data["entities"]

    missing = []
    for e in entities:
        c = e.get("coordinates")
        if isinstance(c, list) and len(c) >= 2:
            continue
        addr = (e.get("attributes") or {}).get("address", "")
        if addr:
            missing.append(e)

    print(f"{'DRY RUN' if DRY_RUN else 'APPLYING'}: {len(missing)} entities to geocode\n")

    results = []
    for i, e in enumerate(missing):
        addr = (e.get("attributes") or {}).get("address", "")
        name = e.get("name", "")
        clean = clean_address(addr)

        # Try full address first
        coords = geocode(clean)

        # If that fails, try name + area
        if not coords:
            area_name = {"vinh-long": "Vinh Long", "ben-tre": "Ben Tre", "tra-vinh": "Tra Vinh"}.get(e.get("area", ""), "")
            if area_name:
                coords = geocode(f"{name}, {area_name}, Vietnam")
                time.sleep(1.1)

        status = "FOUND" if coords else "MISS"
        results.append((e["id"], name, coords))
        if coords:
            print(f"  [{i+1:3d}/{len(missing)}] {status} {name[:40]:40s} → [{coords[0]:.6f}, {coords[1]:.6f}]")
        else:
            print(f"  [{i+1:3d}/{len(missing)}] {status} {name[:40]:40s} | {addr[:50]}")

        time.sleep(1.1)

    found = [r for r in results if r[2]]
    print(f"\n{'=' * 50}")
    print(f"Found: {len(found)}/{len(missing)}")
    print(f"Miss:  {len(missing) - len(found)}/{len(missing)}")

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

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\nSaved {len(found)} coordinates to data.json")


if __name__ == "__main__":
    main()
