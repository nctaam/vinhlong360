"""Generate SQL to update police_phone in PostgreSQL."""
import json

with open("web/data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

updates = []
for e in data["entities"]:
    if e.get("type") == "place" and e.get("attributes", {}).get("police_phone"):
        updates.append((e["id"], e["attributes"]["police_phone"]))

print(f"-- {len(updates)} entities with police_phone")

with open("scratch/update_police_phones.sql", "w", encoding="utf-8") as f:
    f.write("BEGIN;\n")
    for eid, phone in updates:
        eid_esc = eid.replace("'", "''")
        phone_esc = phone.replace("'", "''")
        f.write(
            f"UPDATE entities SET attributes = jsonb_set("
            f"COALESCE(attributes, '{{}}'::jsonb), "
            f"'{{police_phone}}', '\"{phone_esc}\"') "
            f"WHERE id = '{eid_esc}';\n"
        )
    f.write("COMMIT;\n")

print(f"Wrote scratch/update_police_phones.sql ({len(updates)} updates)")
