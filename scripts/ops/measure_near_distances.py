# -*- coding: utf-8 -*-
import json
import math


def haversine(c1, c2):
    lat1, lon1 = c1
    lat2, lon2 = c2
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def compute_rel_distance(r, emap):
    s = emap.get(r.get("from"))
    t = emap.get(r.get("to"))
    if not s or not t:
        return None
    c1 = s.get("coordinates")
    c2 = t.get("coordinates")
    if not c1 or not c2 or len(c1) < 2 or len(c2) < 2:
        return None
    d = haversine(c1, c2)
    return (d, r, s["name"], t["name"])


def main():
    with open("web/data.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    emap = {e["id"]: e for e in data.get("entities", [])}
    near_rels = [r for r in data.get("relationships", []) if r.get("type") == "near"]
    print(f"Total near edges: {len(near_rels)}")

    distances = []
    for r in near_rels:
        item = compute_rel_distance(r, emap)
        if item:
            distances.append(item)

    distances.sort(key=lambda x: -x[0])
    gt_20 = [x for x in distances if x[0] > 20.0]
    gt_30 = [x for x in distances if x[0] > 30.0]
    gt_50 = [x for x in distances if x[0] > 50.0]

    print(f"Distances computed: {len(distances)}")
    print(f"> 20 km: {len(gt_20)}")
    print(f"> 30 km: {len(gt_30)}")
    print(f"> 50 km: {len(gt_50)}")
    print("Top 10 longest near edges:")
    for d, r, sn, tn in distances[:10]:
        print(f"  {d:.2f} km: {r['from']} ({sn}) <-> {r['to']} ({tn})")


if __name__ == "__main__":
    main()
