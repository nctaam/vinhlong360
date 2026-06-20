"""
Import dữ liệu Bến Tre và Trà Vinh từ baovinhlong.com.vn vào KB.
Source: bài viết du lịch, điểm đến, đặc sản 3 tỉnh

Chạy: python agent/import_baovinhlong.py [--apply]
"""

import json, os, sys, re, time, unicodedata
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
DATA_JSON = ROOT / "web" / "data.json"
CRAWLED = Path(__file__).resolve().parent / "crawled" / "baovinhlong_raw.json"

# placeId mapping — BT districts → xa-an-binh, TV districts → xa-tra-on
PLACE_KEYWORDS = {
    # Bến Tre (province old) → phường/xã thuộc VL mới
    "Phường Bến Tre": "xa-an-binh",
    "Phường An Hội": "xa-an-binh",
    "Phường Phú Khương": "xa-an-binh",
    "TP Bến Tre": "xa-an-binh",
    "Châu Thành": "xa-an-binh",
    "Ba Tri": "xa-an-binh",
    "Bình Đại": "xa-an-binh",
    "Thạnh Phú": "xa-an-binh",
    "Chợ Lách": "xa-an-binh",
    "Mỏ Cày": "xa-an-binh",
    "Giồng Trôm": "xa-an-binh",
    "Bến Tre": "xa-an-binh",
    # Trà Vinh (province old) → xa-tra-on
    "TP Trà Vinh": "xa-tra-on",
    "Cầu Kè": "xa-tra-on",
    "Duyên Hải": "xa-tra-on",
    "Càng Long": "xa-tra-on",
    "Tiểu Cần": "xa-tra-on",
    "Cầu Ngang": "xa-tra-on",
    "Trà Cú": "xa-tra-on",
    "Châu Thành": "xa-tra-on",   # override below if BT first matched
    "Trà Vinh": "xa-tra-on",
    "Trường Long Hòa": "xa-tra-on",
    "Nguyệt Hóa": "xa-tra-on",
    # VL mới central
    "Long Châu": "p-long-chau",
    "Phước Hậu": "p-phuoc-hau",
    "An Bình": "xa-an-binh",
    "Mỹ Tân": "xa-an-binh",
}

# Province → default placeId fallback
PROVINCE_PLACE = {
    "Bến Tre": "xa-an-binh",
    "Trà Vinh": "xa-tra-on",
}

SOURCE_URL = "https://baovinhlong.com.vn/xa-hoi/du-lich/"

SECTIONS = [
    ("ben_tre_attractions", "attraction"),
    ("ben_tre_products", "product"),
    ("tra_vinh_attractions", "attraction"),
    ("tra_vinh_products", "product"),
]

ITEM_TYPE_OVERRIDE = {
    "history": "history",
    "nature": "nature",
    "craft_village": "craft_village",
    "attraction": "attraction",
    "product": "product",
    "experience": "experience",
}


def slugify(text):
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.lower().strip()
    text = re.sub(r"[đĐ]", "d", text)
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s-]+", "-", text).strip("-")
    return text[:80]


def guess_place_id(addr, province_old=None):
    # GĐ-audit (B2): KHÔNG còn map cả tỉnh cũ → 1 xã "thùng chứa" (gây bug placeId dồn
    # Bến Tre→xa-an-binh, Trà Vinh→xa-tra-on). Gán xã đúng cần crosswalk "đơn vị cũ→xã mới"
    # chính thống (Track-H). Trước khi có → để None (chưa phân loại) còn hơn sai.
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


def main():
    print("═══ Import baovinhlong.com.vn (BT + TV) ═══\n")

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

    for section, default_type in SECTIONS:
        items = raw.get(section, [])
        cat_new = 0
        cat_dup = 0

        for item in items:
            name = item.get("name", "")
            if not name:
                continue

            # Use item type if specified
            entity_type = ITEM_TYPE_OVERRIDE.get(item.get("type", ""), default_type)

            dup = find_duplicate(name, existing_names, existing_list + new_entities, entity_type)
            if dup:
                duplicates.append((name, dup, section))
                cat_dup += 1
                continue

            eid = slugify(name)
            if eid in existing or any(e["id"] == eid for e in new_entities):
                eid = eid + "-bvl"

            addr = item.get("addr", "")
            province_old = item.get("province_old", "")

            entity = {
                "id": eid,
                "type": entity_type,
                "name": name,
                "placeId": guess_place_id(addr, province_old),
                "summary": (item.get("desc", "") or "")[:200],
                "source": {"title": "baovinhlong.com.vn", "url": SOURCE_URL},
                "status": "provisional",
                "verified": False,
                "confidence": 0.75,
                "updatedAt": time.strftime("%Y-%m-%d"),
            }

            attrs = {}
            if addr:
                attrs["address"] = addr
            if province_old:
                attrs["province_old"] = province_old
            if attrs:
                entity["attributes"] = attrs

            # Geocode
            geo_query = f"{name}, {addr}" if addr else f"{name}, {province_old}, Vĩnh Long"
            coords = geocode_osm(geo_query)
            if coords:
                entity["coords"] = coords
                entity["confidence"] = 0.8
            else:
                simple = f"{name}, {province_old}, Việt Nam" if province_old else f"{name}, Vĩnh Long"
                coords2 = geocode_osm(simple)
                if coords2:
                    entity["coords"] = coords2
                    entity["confidence"] = 0.75

            new_entities.append(entity)
            existing_names.add(name.lower())
            cat_new += 1
            time.sleep(0.5)

        stats[section] = {"new": cat_new, "dup": cat_dup, "total": len(items)}
        print(f"  {section}: {cat_new} new, {cat_dup} dup (of {len(items)})")

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
            prov = e.get("attributes", {}).get("province_old", "")
            print(f"  {gps} [{e['type']}] {e['name']} ({prov})")

        out_file = Path(__file__).resolve().parent / "crawled" / "_baovinhlong_proposed.json"
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
