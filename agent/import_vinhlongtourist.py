"""
Import dữ liệu từ vinhlongtourist.vn vào KB.
Source: điểm tham quan, lưu trú, nhà hàng, mua sắm, đặc sản, tour

Chạy: python agent/import_vinhlongtourist.py [--apply]
"""

import json, os, sys, re, time, unicodedata
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
DATA_JSON = ROOT / "web" / "data.json"
CRAWLED = Path(__file__).resolve().parent / "crawled" / "vinhlongtourist_raw.json"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from text_utils import slugify

PLACE_KEYWORDS = {
    "Long Châu": "p-long-chau",
    "Phước Hậu": "p-phuoc-hau",
    "Tân Ngãi": "p-tan-ngai",
    "Tân Hạnh": "p-tan-hanh",
    "Thanh Đức": "p-thanh-duc",
    "Bình Minh": "p-binh-minh",
    "Cái Vồn": "p-cai-von",
    "An Bình": "xa-an-binh",
    "Long Hồ": "xa-long-ho",
    "Cái Nhum": "xa-cai-nhum",
    "Mang Thít": "xa-cai-nhum",
    "Tam Bình": "xa-tam-binh",
    "Trà Ôn": "xa-tra-on",
    "Trà Côn": "xa-tra-con",
    "Vũng Liêm": "xa-trung-hiep",
    "Quới Thiện": "xa-trung-hiep",
    "Tam Ngãi": "xa-tra-on",
    "Cầu Kè": "xa-tra-on",
    "Trà Vinh": "xa-tra-on",
    "Nguyệt Hóa": "xa-tra-on",
    "Bến Tre": "xa-an-binh",
}

SOURCE_URL = "https://vinhlongtourist.vn"

TYPE_MAP = {
    "attractions": "attraction",
    "accommodation": "accommodation",
    "restaurants": "dish",
    "shopping": "attraction",
    "products": "product",
    "tours": "experience",
}

# Override per-item types when item has its own type field
ITEM_TYPE_OVERRIDE = {
    "history": "history",
    "craft_village": "craft_village",
    "experience": "experience",
    "product": "product",
    "shopping": "attraction",
    "attraction": "attraction",
}


def guess_place_id(addr):
    if not addr:
        return None
    for kw, pid in PLACE_KEYWORDS.items():
        if kw.lower() in addr.lower():
            return pid
    return None


def find_duplicate(name, existing_names_lower, existing_list, entity_type=None):
    nl = name.lower()
    if nl in existing_names_lower:
        return nl
    nl_tokens = set(nl.split())
    if len(nl_tokens) < 3:
        return None
    for ex in existing_list:
        ex_name = ex.get("name", "").lower()
        ex_tokens = set(ex_name.split())
        if len(ex_tokens) < 3:
            continue
        if entity_type and ex.get("type") and entity_type != ex["type"]:
            continue
        intersection = nl_tokens & ex_tokens
        union = nl_tokens | ex_tokens
        jaccard = len(intersection) / len(union) if union else 0
        if jaccard > 0.7:
            return ex_name
    return None


def geocode_osm(query, retries=2):
    try:
        import httpx
    except ImportError:
        return None
    for attempt in range(retries):
        try:
            r = httpx.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": query, "format": "json", "limit": 1, "countrycodes": "vn"},
                headers={"User-Agent": "vinhlong360-agent/1.0"},
                timeout=10,
            )
            if r.status_code == 200 and r.json():
                d = r.json()[0]
                return [float(d["lat"]), float(d["lon"])]
        except Exception:
            time.sleep(1)
    return None


def build_entity(item, entity_type, category):
    name = item.get("name", "")
    desc = item.get("desc", item.get("description", ""))
    addr = item.get("addr", item.get("address", ""))
    phone = item.get("phone", "")
    email = item.get("email", "")
    hours = item.get("hours", "")
    stars = item.get("stars", "")

    # Override type if item specifies it
    if "type" in item and item["type"] in ITEM_TYPE_OVERRIDE:
        entity_type = ITEM_TYPE_OVERRIDE[item["type"]]

    eid = slugify(name)

    entity = {
        "id": eid,
        "type": entity_type,
        "name": name,
        "placeId": guess_place_id(addr),
        "summary": desc,
        "source": {"title": "vinhlongtourist.vn", "url": SOURCE_URL},
        "status": "provisional",
        "verified": False,
        "confidence": 0.75,
        "updatedAt": time.strftime("%Y-%m-%d"),
    }

    attrs = {}
    if phone:
        attrs["phone"] = phone
    if email:
        attrs["email"] = email
    if addr:
        attrs["address"] = addr
    if hours:
        attrs["hours"] = hours
    if stars:
        attrs["stars"] = stars
    if item.get("company"):
        attrs["company"] = item["company"]
    if item.get("duration"):
        attrs["duration"] = item["duration"]
    if attrs:
        entity["attributes"] = attrs

    return entity


def main():
    print("═══ Import vinhlongtourist.vn ═══\n")

    with open(DATA_JSON, encoding="utf-8") as f:
        data = json.load(f)
    existing = {e["id"]: e for e in data.get("entities", [])}
    existing_names = {e["name"].lower() for e in existing.values()}
    existing_list = list(existing.values())

    with open(CRAWLED, encoding="utf-8") as f:
        raw = json.load(f)

    new_entities = []
    duplicates = []
    stats = {}

    categories = ["attractions", "accommodation", "restaurants", "shopping", "products", "tours"]

    for category in categories:
        items = raw.get(category, [])
        entity_type = TYPE_MAP[category]
        cat_new = 0
        cat_dup = 0

        for item in items:
            name = item.get("name", "")
            if not name:
                continue

            # Determine actual entity type for dedup check
            actual_type = entity_type
            if "type" in item and item["type"] in ITEM_TYPE_OVERRIDE:
                actual_type = ITEM_TYPE_OVERRIDE[item["type"]]

            dup = find_duplicate(name, existing_names, existing_list + new_entities, actual_type)
            if dup:
                duplicates.append((name, dup, category))
                cat_dup += 1
                continue

            entity = build_entity(item, entity_type, category)
            eid = entity["id"]

            if eid in existing or any(e["id"] == eid for e in new_entities):
                entity["id"] = eid + "-vlt"

            addr = item.get("addr", item.get("address", ""))
            geo_query = f"{name}, {addr}, Vĩnh Long" if addr else f"{name}, Vĩnh Long"
            coords = geocode_osm(geo_query)
            if coords:
                entity["coords"] = coords
                entity["confidence"] = 0.8
            else:
                geo_query2 = f"{name}, Vĩnh Long"
                coords2 = geocode_osm(geo_query2)
                if coords2:
                    entity["coords"] = coords2
                    entity["confidence"] = 0.75

            new_entities.append(entity)
            existing_names.add(name.lower())
            cat_new += 1

            if cat_new % 5 == 0:
                print(f"  [{category}] {cat_new} new so far...")

            time.sleep(0.5)

        stats[category] = {"new": cat_new, "dup": cat_dup, "total": len(items)}
        print(f"  {category}: {cat_new} new, {cat_dup} dup (of {len(items)})")

    print(f"\n═══ Kết quả ═══")
    total_new = sum(s["new"] for s in stats.values())
    total_dup = sum(s["dup"] for s in stats.values())
    with_coords = sum(1 for e in new_entities if e.get("coords"))
    print(f"  Mới:      {total_new}")
    print(f"  Trùng:    {total_dup}")
    print(f"  Có GPS:   {with_coords}/{total_new}")

    if duplicates:
        print(f"\n── Trùng lắp ({total_dup}) ──")
        for name, dup_of, cat in duplicates:
            print(f"  ✗ [{cat}] {name} ≈ {dup_of}")

    if new_entities:
        print(f"\n── Entity mới ({total_new}) ──")
        for e in new_entities:
            gps = "📍" if e.get("coords") else "  "
            print(f"  {gps} [{e['type']}] {e['name']}")

        out_file = Path(__file__).resolve().parent / "crawled" / "_vinhlongtourist_proposed.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(new_entities, f, ensure_ascii=False, indent=2)
        print(f"\nĐã lưu: {out_file}")

    if "--apply" in sys.argv and new_entities:
        data["entities"].extend(new_entities)
        with open(DATA_JSON, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n✓ Đã thêm {len(new_entities)} entity vào data.json")
        print(f"  Tổng entities: {len(data['entities'])}")
    elif new_entities and "--apply" not in sys.argv:
        print(f"\nChạy lại với --apply để import vào data.json")


if __name__ == "__main__":
    main()
