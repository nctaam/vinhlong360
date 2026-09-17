import json
import sqlite3
import sys

def ingest_batch(batch_file_path: str, verified_at: str = "2026-09-17T21:00:00Z"):
    with open(batch_file_path, "r", encoding="utf-8") as f:
        batch = json.load(f)

    db_path = "agent/data/vinhlong360.db"
    json_path = "web/data.json"

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    json_entities = {e["id"]: e for e in data["entities"]}

    batch_map = {item["entity_id"]: item for item in batch}

    for eid, item in batch_map.items():
        # 1. Update SQLite DB
        row = cur.execute("SELECT attributes FROM entities WHERE id = ?", (eid,)).fetchone()
        if not row:
            raise ValueError(f"Entity {eid} not found in DB")

        attrs = json.loads(row[0] or "{}")
        attrs["image_author"] = item["author"]
        attrs["image_source"] = item["source"]
        attrs["image_type"] = "documentary"
        attrs["is_verified_photo"] = True
        attrs["image_caption"] = item["caption"]
        attrs["image_license"] = item["license"]
        attrs["verifiedAt"] = verified_at

        new_images = json.dumps([f"/img/entities/{eid}.webp"])
        new_attrs_str = json.dumps(attrs, ensure_ascii=False)
        cur.execute("UPDATE entities SET attributes = ?, images = ? WHERE id = ?", (new_attrs_str, new_images, eid))

        # 2. Update JSON
        if eid not in json_entities:
            raise ValueError(f"Entity {eid} not found in web/data.json")
        e = json_entities[eid]
        if "attributes" not in e or not isinstance(e["attributes"], dict):
            e["attributes"] = {}
        e["attributes"]["image_author"] = item["author"]
        e["attributes"]["image_source"] = item["source"]
        e["attributes"]["image_type"] = "documentary"
        e["attributes"]["is_verified_photo"] = True
        e["attributes"]["image_caption"] = item["caption"]
        e["attributes"]["image_license"] = item["license"]
        e["attributes"]["verifiedAt"] = verified_at
        e["images"] = [f"/img/entities/{eid}.webp"]

    conn.commit()
    conn.close()

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Successfully ingested {len(batch)} entities from {batch_file_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/ops/ingest_batch.py <batch_file_path> [verified_at]")
        sys.exit(1)
    verified_at = sys.argv[2] if len(sys.argv) > 2 else "2026-09-17T21:00:00Z"
    ingest_batch(sys.argv[1], verified_at)
