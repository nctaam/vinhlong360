import sqlite3
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

conn = sqlite3.connect("agent/data/vinhlong360.db")
c = conn.cursor()
rows = c.execute("SELECT id, name, type, attributes, description, address FROM entities WHERE type = 'history'").fetchall()
unv = [r for r in rows if not json.loads(r[3] or "{}").get("is_verified_photo")]

print(f"Total unverified history remaining: {len(unv)}")

batch_37_candidates = []
for r in unv[:40]:
    batch_37_candidates.append({
        "id": r[0],
        "name": r[1],
        "address": r[5],
        "description": r[4]
    })

with open("outputs/batch_37_candidates.json", "w", encoding="utf-8") as f:
    json.dump(batch_37_candidates, f, ensure_ascii=False, indent=2)

print("Dumped 40 candidates to outputs/batch_37_candidates.json")
