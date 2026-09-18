import sqlite3
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

conn = sqlite3.connect("agent/data/vinhlong360.db")
c = conn.cursor()
rows = c.execute("SELECT id, name, type, attributes, description, address FROM entities WHERE type = 'product'").fetchall()
unv_prod = [r for r in rows if not json.loads(r[3] or "{}").get("is_verified_photo")]

print(f"Total unverified products remaining: {len(unv_prod)}")

batch_35_candidates = []
for r in unv_prod[:40]:
    batch_35_candidates.append({
        "id": r[0],
        "name": r[1],
        "address": r[5],
        "description": r[4]
    })

with open("outputs/batch_35_candidates.json", "w", encoding="utf-8") as f:
    json.dump(batch_35_candidates, f, ensure_ascii=False, indent=2)

print("Dumped 40 candidates to outputs/batch_35_candidates.json")
