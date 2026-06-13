"""
Import dữ liệu Phường An Hội + Bến Tre mở rộng + Trà Vinh events vào KB.

Xử lý:
  1. Thêm entity mới (dedup + geocode)
  2. Cập nhật các entity đã có (update_existing)

Chạy: python agent/import_phuong_an_hoi.py [--apply]
"""

import json, os, sys, re, time, unicodedata
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
DATA_JSON = ROOT / "web" / "data.json"
CRAWLED = Path(__file__).resolve().parent / "crawled" / "phuong_an_hoi_raw.json"

PLACE_KEYWORDS = {
    "Phường An Hội": "xa-an-binh",
    "TP Bến Tre": "xa-an-binh",
    "Châu Thành": "xa-an-binh",
    "Ba Tri": "xa-an-binh",
    "Bình Đại": "xa-an-binh",
    "Thạnh Phú": "xa-an-binh",
    "Chợ Lách": "xa-an-binh",
    "Mỏ Cày": "xa-an-binh",
    "Giồng Trôm": "xa-an-binh",
    "Bến Tre": "xa-an-binh",
    "TP Trà Vinh": "xa-tra-on",
    "Trà Vinh": "xa-tra-on",
    "Cầu Kè": "xa-tra-on",
    "Duyên Hải": "xa-tra-on",
    "Tiểu Cần": "xa-tra-on",
}

PROVINCE_PLACE = {
    "Bến Tre": "xa-an-binh",
    "Trà Vinh": "xa-tra-on",
}

SOURCE_URLS = {
    "Bến Tre": "https://baodongkhoi.vn/",
    "Trà Vinh": "https://baovinhlong.com.vn/xa-hoi/du-lich/",
    "default": "https://mytour.vn/",
}

SECTIONS = [
    ("an_hoi_ward", None),
    ("ben_tre_new_attractions", "attraction"),
    ("ben_tre_products_new", "product"),
    ("tra_vinh_events", "event"),
]


def slugify(text):
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.lower().strip()
    text = re.sub(r"[đĐ]", "d", text)
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s-]+", "-", text).strip("-")
    return text[:80]


def guess_place_id(addr, province_old=None):
    # GĐ-audit (B2): bỏ map cả tỉnh → 1 xã "thùng chứa". Cần crosswalk chính thống để gán đúng;
    # trước đó để None (chưa phân loại) còn hơn sai. Xem scripts/fix_placeid_buckets.py.
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
    print("═══ Import Phường An Hội + BT expanded + TV events ═══\n")

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
        if not items:
            continue
        cat_new = 0
        cat_dup = 0

        for item in items:
            name = item.get("name", "")
            if not name:
                continue

            entity_type = item.get("type") or default_type or "attraction"

            dup = find_duplicate(name, existing_names, existing_list + new_entities, entity_type)
            if dup:
                duplicates.append((name, dup, section))
                cat_dup += 1
                continue

            eid = slugify(name)
            if eid in existing or any(e["id"] == eid for e in new_entities):
                eid = eid + "-pah"

            addr = item.get("addr", "")
            province_old = item.get("province_old", "Bến Tre")

            source_url = SOURCE_URLS.get(province_old, SOURCE_URLS["default"])

            entity = {
                "id": eid,
                "type": entity_type,
                "name": name,
                "placeId": guess_place_id(addr, province_old),
                "summary": item.get("desc", ""),
                "source": {"title": "mytour.vn / baodongkhoi.vn / mia.vn", "url": source_url},
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
            if item.get("heritage_level"):
                attrs["heritage_level"] = item["heritage_level"]
            if attrs:
                entity["attributes"] = attrs

            # Geocode — try full address first, then simplified
            geo_q1 = f"{name}, {addr}" if addr else f"{name}, {province_old}, Việt Nam"
            coords = geocode_osm(geo_q1)
            if coords:
                entity["coords"] = coords
                entity["confidence"] = 0.8
            else:
                geo_q2 = f"{name}, {province_old}, Việt Nam"
                coords2 = geocode_osm(geo_q2)
                if coords2:
                    entity["coords"] = coords2
                    entity["confidence"] = 0.75

            new_entities.append(entity)
            existing_names.add(name.lower())
            cat_new += 1
            time.sleep(0.5)

        stats[section] = {"new": cat_new, "dup": cat_dup}
        print(f"  {section}: {cat_new} new, {cat_dup} dup (of {len(items)})")

    # ── Update pass ──────────────────────────────────────────
    updates_done = []
    for upd in raw.get("update_existing", []):
        uid = upd["id"]
        if uid not in existing:
            # try fuzzy: check if any key contains uid
            matched = next((k for k in existing if uid in k), None)
            if matched:
                uid = matched
            else:
                print(f"  ! UPDATE SKIP (not found): {upd['id']}")
                continue
        fields = upd.get("fields_to_update", {})
        ent = existing[uid]
        if "summary" in fields:
            ent["summary"] = fields["summary"]
        if "attributes" in fields:
            ent.setdefault("attributes", {}).update(fields["attributes"])
        ent["updatedAt"] = time.strftime("%Y-%m-%d")
        updates_done.append(uid)
        print(f"  ✎ Updated: {uid}")

    # ── Report ───────────────────────────────────────────────
    print(f"\n═══ Kết quả ═══")
    total_new = sum(s["new"] for s in stats.values())
    total_dup = sum(s["dup"] for s in stats.values())
    with_coords = sum(1 for e in new_entities if e.get("coords"))
    print(f"  Mới:      {total_new}")
    print(f"  Trùng:    {total_dup}")
    print(f"  Có GPS:   {with_coords}/{total_new}")
    print(f"  Cập nhật: {len(updates_done)}")

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

        out_file = Path(__file__).resolve().parent / "crawled" / "_phuong_an_hoi_proposed.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(new_entities, f, ensure_ascii=False, indent=2)
        print(f"\nĐã lưu: {out_file}")

    if "--apply" in sys.argv:
        if new_entities:
            data["entities"].extend(new_entities)
        # write back updates
        data["entities"] = [existing[k] for k in existing] + new_entities
        with open(DATA_JSON, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        total_ents = len(data["entities"]) - len(new_entities) + len(new_entities)
        print(f"\n✓ Đã lưu data.json")
        print(f"  +{len(new_entities)} entity mới, {len(updates_done)} entity cập nhật")
        print(f"  Tổng entities: {len(data['entities'])}")
    else:
        print(f"\nChạy lại với --apply để import + cập nhật vào data.json")


if __name__ == "__main__":
    main()
