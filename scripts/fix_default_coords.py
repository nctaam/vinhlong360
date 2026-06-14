#!/usr/bin/env python3
"""Null hóa toạ độ mặc định tỉnh — những entity chung 1 điểm với >3 entity khác
là toạ độ trung tâm tỉnh/TP, không phải vị trí thật."""
import json, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "web" / "data.json"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

data = json.load(DATA.open("r", encoding="utf-8-sig"))
entities = data["entities"]

def norm_coords(val):
    if isinstance(val, str):
        try: val = json.loads(val)
        except: return None
    if isinstance(val, dict):
        lat = val.get("lat", val.get("latitude"))
        lng = val.get("lng", val.get("lon", val.get("longitude")))
        val = [lat, lng]
    if not isinstance(val, (list, tuple)) or len(val) != 2:
        return None
    try:
        return [float(val[0]), float(val[1])]
    except (TypeError, ValueError):
        return None

# Find clusters of entities at exact same coordinates
coord_map = defaultdict(list)
for e in entities:
    c = norm_coords(e.get("coordinates") or e.get("coords"))
    if not c:
        continue
    key = f"{c[0]:.4f},{c[1]:.4f}"
    coord_map[key].append(e)

# Clusters >3 at same point = likely province/city center default
THRESHOLD = 4
nulled = 0
# But protect places (type=place) which legitimately might share coords (e.g. ward center)
for key, group in coord_map.items():
    if len(group) < THRESHOLD:
        continue
    # Check if these are all different types of entities (not just places)
    non_place = [e for e in group if e.get("type") != "place"]
    if len(non_place) < THRESHOLD:
        continue
    print(f"\nCluster {key} ({len(group)} entities):")
    for e in group:
        typ = e.get("type", "?")
        name = e.get("name", "?")
        if typ == "place":
            print(f"  KEEP (place): {name}")
        else:
            e["coordinates"] = None
            if "coords" in e:
                e["coords"] = None
            nulled += 1
            print(f"  NULL: {name} ({typ})")

print(f"\n{'='*60}")
print(f"Nulled {nulled} default-coords entities")

# Also remove near rels involving newly-nulled entities (they're now meaningless)
nulled_ids = set()
for e in entities:
    if e.get("coordinates") is None and e.get("coords") is None and e.get("type") != "place":
        pass  # Already handled by deep_audit's near-without-coords cleanup

with DATA.open("w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=None, separators=(",", ":"))
print(f"✅ Saved: {len(entities)} entities")
