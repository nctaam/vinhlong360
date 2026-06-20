"""
Import crawled Foody.vn data into vinhlong360.db.
Reads: scratch/foody_crawled.json
Maps Foody listings → entity type 'dish' (default for restaurants/cafes).

Usage:
  python scripts/import_foody.py              # dry-run (show what would be inserted)
  python scripts/import_foody.py --apply      # actually insert into DB
  python scripts/import_foody.py --min-rating 8.0  # only import 8.0+
"""
import argparse, json, re, sqlite3, unicodedata
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "agent" / "data" / "vinhlong360.db"
INPUT_PATH = ROOT / "scratch" / "foody_crawled.json"

AREA_PLACE_MAP = {
    "vinh-long": "p-vinh-long-city",
    "ben-tre": "p-ben-tre-city",
    "tra-vinh": "p-tra-vinh-city",
}


def slugify(name: str) -> str:
    s = unicodedata.normalize("NFD", name.lower())
    s = re.sub(r"[̀-ͯ]", "", s)
    s = s.replace("đ", "d").replace("Đ", "d")
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s).strip("-")
    return s[:80]


def guess_type(name: str, address: str) -> str:
    name_lower = name.lower()
    if any(k in name_lower for k in ["hotel", "khách sạn", "homestay", "resort", "nhà nghỉ", "motel"]):
        return "accommodation"
    if any(k in name_lower for k in ["coffee", "café", "cafe", "cà phê", "trà", "tea", "milk tea", "trà sữa"]):
        return "dish"
    if any(k in name_lower for k in ["spa", "karaoke", "bar", "pub", "club", "gym"]):
        return "experience"
    return "dish"


def extract_place_id(address: str, area: str) -> str:
    addr_lower = address.lower()
    if "thành phố vĩnh long" in addr_lower or "tp. vĩnh long" in addr_lower or "tp vĩnh long" in addr_lower:
        return "p-vinh-long-city"
    if "thành phố bến tre" in addr_lower or "tp. bến tre" in addr_lower or "tp bến tre" in addr_lower:
        return "p-ben-tre-city"
    if "thành phố trà vinh" in addr_lower or "tp. trà vinh" in addr_lower or "tp trà vinh" in addr_lower:
        return "p-tra-vinh-city"
    return AREA_PLACE_MAP.get(area, f"p-{area}-city")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Actually insert into DB")
    parser.add_argument("--min-rating", type=float, default=7.0)
    args = parser.parse_args()

    if not INPUT_PATH.exists():
        print(f"No input file: {INPUT_PATH}")
        print("Run crawl_foody.py first.")
        return

    items = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    print(f"Loaded {len(items)} crawled items")

    filtered = [i for i in items if i.get("rating", 0) >= args.min_rating]
    print(f"After rating >= {args.min_rating}: {len(filtered)}")

    conn = sqlite3.connect(str(DB_PATH))
    existing_ids = {r[0] for r in conn.execute("SELECT id FROM entities").fetchall()}
    existing_names = {
        unicodedata.normalize("NFC", r[0].strip().lower())
        for r in conn.execute("SELECT name FROM entities").fetchall()
    }

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    to_insert = []

    for item in filtered:
        entity_id = slugify(item["name"])
        if not entity_id:
            continue

        suffix = 0
        base_id = entity_id
        while entity_id in existing_ids:
            suffix += 1
            entity_id = f"{base_id}-{suffix}"

        norm_name = unicodedata.normalize("NFC", item["name"].strip().lower())
        if norm_name in existing_names:
            continue

        entity_type = guess_type(item["name"], item.get("address", ""))
        place_id = extract_place_id(item.get("address", ""), item.get("area", ""))

        attrs = {"address": item.get("address", ""), "foodyRating": item["rating"]}
        if item.get("comments", 0) > 0:
            attrs["foodyComments"] = item["comments"]

        source = json.dumps(["foody.vn"], ensure_ascii=False)
        attrs_json = json.dumps(attrs, ensure_ascii=False)

        to_insert.append({
            "id": entity_id,
            "type": entity_type,
            "name": item["name"],
            "summary": f"{item['name']} — {item.get('address', '')}",
            "placeId": place_id,
            "area": item.get("area", ""),
            "confidence": 0.6,
            "attributes": attrs_json,
            "source": source,
            "updatedAt": now,
            "created_at": now,
        })
        existing_ids.add(entity_id)
        existing_names.add(norm_name)

    print(f"New entities to insert: {len(to_insert)}")

    from collections import Counter
    type_counts = Counter(e["type"] for e in to_insert)
    area_counts = Counter(e["area"] for e in to_insert)
    print(f"  By type: {dict(type_counts)}")
    print(f"  By area: {dict(area_counts)}")

    if not args.apply:
        print("\nDRY RUN — pass --apply to insert")
        for e in to_insert[:10]:
            print(f"  {e['id']} | {e['type']} | {e['name']}")
        if len(to_insert) > 10:
            print(f"  ... and {len(to_insert) - 10} more")
        conn.close()
        return

    sql = """INSERT INTO entities (id, type, name, summary, "placeId", area, confidence, attributes, source, "updatedAt", created_at)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""

    inserted = 0
    for e in to_insert:
        try:
            conn.execute(sql, (
                e["id"], e["type"], e["name"], e["summary"],
                e["placeId"], e["area"], e["confidence"],
                e["attributes"], e["source"], e["updatedAt"], e["created_at"],
            ))
            inserted += 1
        except Exception as ex:
            print(f"  SKIP {e['id']}: {ex}")

    conn.commit()
    total = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
    conn.close()

    print(f"\nInserted {inserted} entities")
    print(f"Total entities in DB: {total}")


if __name__ == "__main__":
    main()
