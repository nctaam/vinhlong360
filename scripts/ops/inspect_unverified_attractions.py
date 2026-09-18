import json
import os
import sqlite3

conn = sqlite3.connect("agent/data/vinhlong360.db")
c = conn.cursor()

query = "SELECT id, name, type, attributes, description, address FROM entities WHERE type = 'attraction'"
rows = c.execute(query).fetchall()

unv = []
for r in rows:
    attrs = json.loads(r[3] or "{}")
    if not attrs.get("is_verified_photo"):
        unv.append({
            "id": r[0],
            "name": r[1],
            "type": r[2],
            "address": r[5],
            "description": r[4]
        })

print(f"Total unverified attraction: {len(unv)}")
batch_40_candidates = unv[:40]

missing_webp = []
for item in batch_40_candidates:
    p = os.path.join("web-nuxt/public/img/entities", item["id"] + ".webp")
    if not os.path.exists(p):
        missing_webp.append((item["id"], p))

print(f"Missing webp in batch 40 candidates: {len(missing_webp)}")
for m in missing_webp:
    print(" ", m)

with open("outputs/batch_40_candidates.json", "w", encoding="utf-8") as f:
    json.dump(batch_40_candidates, f, ensure_ascii=False, indent=2)

print("Dumped 40 candidates to outputs/batch_40_candidates.json")
