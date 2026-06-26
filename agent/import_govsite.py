"""
Import dữ liệu từ vinhlong.gov.vn vào KB.
Source: 6 trang du khách (di tích, lễ hội, đờn ca tài tử, điểm DL, khách sạn, mua sắm)

Chạy: python agent/import_govsite.py [--apply]
"""

import json, os, sys, re, time, unicodedata
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
DATA_JSON = ROOT / "web" / "data.json"
CRAWLED = Path(__file__).resolve().parent / "crawled" / "govsite_raw.json"

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
    "Đông Thành": "p-dong-thanh",
    "An Bình": "xa-an-binh",
    "Long Hồ": "xa-long-ho",
    "Cái Nhum": "xa-cai-nhum",
    "Nhơn Phú": "xa-nhon-phu",
    "Bình Phước": "xa-binh-phuoc",
    "Tam Bình": "xa-tam-binh",
    "Trà Ôn": "xa-tra-on",
    "Trà Côn": "xa-tra-con",
    "Lục Sĩ Thành": "xa-luc-si-thanh",
    "Trung Thành": "xa-trung-thanh",
    "Trung Ngãi": "xa-trung-ngai",
    "Trung Hiệp": "xa-trung-hiep",
    "Quới An": "xa-quoi-an",
    "Hòa Ninh": "xa-hoa-binh",
    "Tân Long Hội": "xa-tan-long-hoi",
    "Phú Đức": "xa-long-ho",
    "Long Phước": "xa-long-ho",
    "Phú Lộc": "xa-tam-binh",
    "Loan Mỹ": "xa-tam-binh",
    "Ngãi Tứ": "xa-tam-binh",
    "Bình Ninh": "xa-tam-binh",
    "Mỹ Thạnh Trung": "xa-tam-binh",
    "Bình Hòa Phước": "xa-long-ho",
    "Vũng Liêm": "xa-trung-hiep",
    "Hưng Mỹ": "xa-trung-thanh",
    "Mỹ Long": "xa-tra-on",
    "Cầu Kè": "xa-tra-on",
    "Trà Vinh": "xa-tra-on",
    "Nguyệt Hóa": "xa-tra-on",
    "Duyên Hải": "xa-tra-on",
    "Trường Long Hòa": "xa-tra-on",
    "Bến Tre": "xa-an-binh",
    "An Hội": "xa-an-binh",
    "Phú Khương": "xa-an-binh",
    "Sơn Đông": "xa-an-binh",
    "Ba Tri": "xa-an-binh",
    "Giồng Trôm": "xa-an-binh",
    "Bình Đại": "xa-an-binh",
    "Chợ Lách": "xa-an-binh",
    "Mỏ Cày": "xa-an-binh",
    "Châu Thành": "xa-an-binh",
    "Phú Túc": "xa-an-binh",
    "An Khánh": "xa-an-binh",
    "Thạnh Phú": "xa-an-binh",
    "Long Đức": "xa-tra-on",
    "Tiểu Cần": "xa-tra-on",
    "Nhị Long": "xa-tra-on",
    "Hòa Minh": "xa-tra-on",
}

TYPE_MAP = {
    "heritage": "history",
    "festivals": "event",
    "culture": "attraction",
    "attractions": "attraction",
    "hotels": "accommodation",
    "shopping": "attraction",
}

SOURCE_URLS = {
    "heritage": "https://vinhlong.gov.vn/du-khach/di-tich-lich-su",
    "festivals": "https://vinhlong.gov.vn/du-khach/le-hoi-truyen-thong",
    "culture": "https://vinhlong.gov.vn/du-khach/%C4%91on-ca-tai-tu",
    "attractions": "https://vinhlong.gov.vn/du-khach/%C4%91iem-du-lich",
    "hotels": "https://vinhlong.gov.vn/du-khach/khach-san-nha-nghi",
    "shopping": "https://vinhlong.gov.vn/du-khach/%C4%91ia-%C4%91iem-mua-sam",
}


def guess_place_id(addr):
    # GĐ-audit (B2): PLACE_KEYWORDS map district cũ → xã "thùng chứa" (Bến Tre→xa-an-binh,
    # Trà Vinh→xa-tra-on). Bỏ — cần crosswalk chính thống; để None còn hơn gán sai.
    return None


def name_similarity(a, b):
    a_tokens = set(a.lower().split())
    b_tokens = set(b.lower().split())
    if not a_tokens or not b_tokens:
        return 0
    intersection = a_tokens & b_tokens
    return len(intersection) / min(len(a_tokens), len(b_tokens))


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
    print("═══ Import vinhlong.gov.vn ═══\n")

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

    for category in ["heritage", "festivals", "culture", "attractions", "hotels", "shopping"]:
        items = raw.get(category, [])
        entity_type = TYPE_MAP[category]
        source_url = SOURCE_URLS[category]
        cat_new = 0
        cat_dup = 0

        for item in items:
            name = item.get("name", "")
            desc = item.get("desc", item.get("description", ""))
            addr = item.get("addr", item.get("address", ""))

            dup = find_duplicate(name, existing_names, existing_list + new_entities, entity_type)
            if dup:
                duplicates.append((name, dup, category))
                cat_dup += 1
                continue

            eid = slugify(name)
            if eid in existing or any(e["id"] == eid for e in new_entities):
                eid = eid + "-gov"

            entity = {
                "id": eid,
                "type": entity_type,
                "name": name,
                "placeId": guess_place_id(addr),
                "summary": desc,
                "source": {"title": "vinhlong.gov.vn", "url": source_url},
                "status": "provisional",
                "verified": False,
                "confidence": 0.75,
                "updatedAt": time.strftime("%Y-%m-%d"),
            }

            if category == "hotels":
                rating = item.get("rating", "")
                phone = item.get("phone", "")
                attrs = {}
                if rating:
                    attrs["hạng"] = rating
                if phone:
                    attrs["phone"] = phone
                if addr:
                    attrs["address"] = addr
                entity["attributes"] = attrs
                entity["summary"] = f"{name} ({rating})" if rating else name
                if addr:
                    entity["summary"] += f", {addr}"

            if category == "shopping":
                if addr:
                    entity["attributes"] = {"address": addr}

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

            if cat_new % 10 == 0:
                print(f"  [{category}] {cat_new} new so far...")
                time.sleep(0.3)

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
        for name, dup_of, cat in duplicates[:30]:
            print(f"  ✗ [{cat}] {name} ≈ {dup_of}")
        if len(duplicates) > 30:
            print(f"  ... và {len(duplicates) - 30} trùng lắp khác")

    if new_entities:
        print(f"\n── Entity mới ({total_new}) ──")
        for e in new_entities[:20]:
            gps = "📍" if e.get("coords") else "  "
            print(f"  {gps} [{e['type']}] {e['name']}")
        if len(new_entities) > 20:
            print(f"  ... và {len(new_entities) - 20} entity khác")

        out_file = Path(__file__).resolve().parent / "crawled" / "_govsite_proposed.json"
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
