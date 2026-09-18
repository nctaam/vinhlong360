import sqlite3
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

conn = sqlite3.connect("agent/data/vinhlong360.db")
c = conn.cursor()
rows = c.execute("SELECT id, name, type, attributes, description, address FROM entities WHERE type = 'product'").fetchall()
unv_prod = [r for r in rows if not json.loads(r[3] or "{}").get("is_verified_photo")]

batch_candidates = []
for r in unv_prod[:40]:
    batch_candidates.append({
        "id": r[0],
        "name": r[1],
        "address": r[5],
        "description": r[4]
    })

with open("outputs/batch_34_candidates.json", "w", encoding="utf-8") as f:
    json.dump(batch_candidates, f, ensure_ascii=False, indent=2)

print(f"Dumped 40 candidates to outputs/batch_34_candidates.json (total unverified products: {len(unv_prod)})")
