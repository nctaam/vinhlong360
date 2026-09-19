# -*- coding: utf-8 -*-
"""Remediate Phase 7: Topology pruning and semantic healing for spatial near relationships > 20 km."""
import json
import math
from pathlib import Path

DATA_PATH = Path("web/data.json")
LOG_PATH = Path("outputs/remediation_phase7_log.json")
MAX_NEAR_KM = 20.0

def _haversine(c1: list, c2: list) -> float:
    lat1, lon1 = c1[0], c1[1]
    lat2, lon2 = c2[0], c2[1]
    radius_km = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    return 2 * radius_km * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def _prune_edge_if_distant(rel: dict, emap: dict, changes: list) -> None:
    if rel.get("type") != "near":
        return
    fid = rel.get("from")
    tid = rel.get("to")
    ent1 = emap.get(fid)
    ent2 = emap.get(tid)
    if not ent1 or not ent2:
        return
    c1 = ent1.get("coordinates")
    c2 = ent2.get("coordinates")
    if not c1 or not c2 or len(c1) < 2 or len(c2) < 2:
        return
    dist = _haversine(c1, c2)
    if dist > MAX_NEAR_KM:
        rel["type"] = "related_to"
        changes.append({
            "from": fid,
            "to": tid,
            "old_type": "near",
            "new_type": "related_to",
            "distance_km": round(dist, 2),
            "reason": f"Distance {dist:.2f} km exceeds maximum proximity threshold ({MAX_NEAR_KM} km)"
        })

def remediate_phase7():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    emap = {e["id"]: e for e in data.get("entities", [])}
    changes = []

    for rel in data.get("relationships", []):
        _prune_edge_if_distant(rel, emap, changes)

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(changes, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    remediate_phase7()
