#!/usr/bin/env python3
import json, sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

with open("web/data.json", encoding="utf-8-sig") as f:
    data = json.load(f)
by_id = {e["id"]: e for e in data["entities"]}
rels = data["relationships"]

dups = [
    ("dinh-long-thanh-vinh-long", "dinh-long-thanh-w3", "dinh-long-thanh"),
    ("khu-luu-niem-tran-dai-nghia-vinh-long", "khu-luu-niem-giao-su-vien-si-tran-dai-nghia"),
    ("cu-lao-may-tra-on-vinh-long", "cu-lao-may-tra-on"),
    ("du-lich-vuon-chu-7-gat-vlt", "du-lich-vuon-chu-7-gat"),
    ("lo-com-cuu-long-vlt", "lo-com-cuu-long"),
    ("nha-gom-tu-buoi-w3", "nha-gom-tu-buoi"),
    ("dinh-tan-hoa-w3", "dinh-tan-hoa"),
]

for group in dups:
    print("---")
    for eid in group:
        e = by_id.get(eid)
        if not e:
            print(f"  {eid}: NOT FOUND")
            continue
        coords = e.get("coordinates") or e.get("coords")
        pid = e.get("placeId", "")
        src = e.get("source", "")
        typ = e["type"]
        area = e.get("area", "")
        rc = sum(1 for r in rels
                 if (r.get("from") or r.get("from_id") or "") == eid
                 or (r.get("to") or r.get("to_id") or "") == eid)
        summary = (e.get("summary") or "")[:80]
        print(f"  {eid}")
        print(f"    type={typ} area={area} placeId={pid}")
        print(f"    coords={'YES' if coords else 'NO'} source={'YES' if src else 'NO'} rels={rc}")
        print(f"    summary: {summary}")
