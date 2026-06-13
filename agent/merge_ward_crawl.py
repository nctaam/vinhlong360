"""
Gộp các file ward_chunk_*.json thành ward_crawl_130_raw.json
Chạy sau khi workflow hoàn tất:
  python agent/merge_ward_crawl.py [--apply]
"""
import json, os, sys, re, time, unicodedata, glob
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
DATA_JSON = ROOT / "web" / "data.json"
CRAWLED = Path(__file__).resolve().parent / "crawled"
OUT_RAW = CRAWLED / "ward_crawl_130_raw.json"

PLACE_KEYWORDS = {
    # BT
    "TP Bến Tre": "xa-an-binh", "An Hội": "xa-an-binh", "Châu Thành": "xa-an-binh",
    "Chợ Lách": "xa-an-binh", "Mỏ Cày": "xa-an-binh", "Ba Tri": "xa-an-binh",
    "Bình Đại": "xa-an-binh", "Thạnh Phú": "xa-an-binh", "Giồng Trôm": "xa-an-binh",
    "Bến Tre": "xa-an-binh",
    # TV
    "TP Trà Vinh": "xa-tra-on", "Càng Long": "xa-tra-on", "Cầu Kè": "xa-tra-on",
    "Tiểu Cần": "xa-tra-on", "Cầu Ngang": "xa-tra-on", "Trà Cú": "xa-tra-on",
    "Duyên Hải": "xa-tra-on", "Trà Vinh": "xa-tra-on",
    # VL
    "TP Vĩnh Long": "p-long-chau", "Long Hồ": "p-long-chau",
    "Mang Thít": "p-phuoc-hau", "Vũng Liêm": "p-phuoc-hau",
    "Tam Bình": "p-phuoc-hau", "Bình Tân": "xa-an-binh",
    "Trà Ôn": "xa-tra-on", "TX Bình Minh": "xa-an-binh",
}
PROVINCE_PLACE = {"Bến Tre": "xa-an-binh", "Trà Vinh": "xa-tra-on", "Vĩnh Long": "p-long-chau"}

def slugify(text):
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.lower().strip()
    text = re.sub(r"[đĐ]", "d", text)
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s-]+", "-", text).strip("-")
    return text[:80]

def guess_place_id(addr, province_old, district=""):
    combined = f"{addr} {district}"
    for kw, pid in PLACE_KEYWORDS.items():
        if kw.lower() in combined.lower():
            return pid
    return PROVINCE_PLACE.get(province_old, "p-long-chau")

def find_duplicate(name, existing_names_lower, existing_list, entity_type=None):
    nl = name.lower()
    if nl in existing_names_lower:
        return nl
    nl_tokens = set(nl.split())
    if len(nl_tokens) < 3:
        return None
    # Tính signature: sorted tokens — dùng để phát hiện cùng từ khác thứ tự (anagram)
    # VD "Thạnh Phong" vs "Phong Thạnh" sẽ có SAME sorted signature → bắt buộc kiểm tra thêm
    nl_sorted = tuple(sorted(nl_tokens))
    for ex in existing_list:
        ex_name = ex.get("name", "").lower()
        ex_tokens = set(ex_name.split())
        if len(ex_tokens) < 3:
            continue
        if entity_type and ex.get("type") and entity_type != ex["type"]:
            continue
        inter = nl_tokens & ex_tokens
        union = nl_tokens | ex_tokens
        jaccard = len(inter) / len(union) if union else 0
        if jaccard <= 0.7:
            continue
        # Loại false positive: nếu tên place ngắn (≤ 4 tokens) mà chỉ khác thứ tự từ
        # VD "Xã Phong Thạnh" ≠ "Xã Thạnh Phong" — cần ít nhất 1 token phân biệt
        ex_sorted = tuple(sorted(ex_tokens))
        if nl_sorted == ex_sorted and nl != ex_name:
            # Tên cùng từ nhưng khác thứ tự: chỉ coi là dup nếu ≥ 5 tokens (tránh "Phong Thạnh" ≠ "Thạnh Phong")
            if len(nl_tokens) < 5:
                continue
        return ex_name
    return None

def geocode_osm(query, retries=2):
    try:
        import httpx
    except ImportError:
        return None
    for _ in range(retries):
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
    apply = "--apply" in sys.argv
    print("═══ Merge + Import Ward Crawl 130 ═══\n")

    # Step 1: Merge all chunk files
    chunk_files = sorted(CRAWLED.glob("ward_chunk_*.json"))
    print(f"Tìm thấy {len(chunk_files)} chunk files:")
    raw_all = []
    for cf in chunk_files:
        try:
            items = json.loads(cf.read_text(encoding="utf-8"))
            if isinstance(items, list):
                raw_all.extend(items)
                print(f"  {cf.name}: {len(items)} items")
            else:
                print(f"  {cf.name}: SKIP (not array)")
        except Exception as e:
            print(f"  {cf.name}: ERROR — {e}")

    print(f"\nTổng raw: {len(raw_all)} items")

    # Step 2: Write merged raw
    with open(OUT_RAW, "w", encoding="utf-8") as f:
        json.dump(raw_all, f, ensure_ascii=False, indent=2)
    print(f"Đã ghi: {OUT_RAW}")

    if not apply:
        print("\nChạy với --apply để dedup + geocode + import vào data.json")
        return

    # Step 3: Dedup + geocode + import
    with open(DATA_JSON, encoding="utf-8") as f:
        data = json.load(f)
    existing = {e["id"]: e for e in data.get("entities", [])}
    existing_names = {e["name"].lower() for e in existing.values()}
    existing_list = list(existing.values())

    new_entities = []
    duplicates = []

    valid_types = {
        "attraction", "product", "dish", "craft_village", "nature",
        "history", "accommodation", "experience", "event", "person", "place"
    }

    for item in raw_all:
        name = (item.get("name") or "").strip()
        if not name or len(name) < 3:
            continue
        entity_type = item.get("type", "attraction")
        if entity_type not in valid_types:
            entity_type = "attraction"

        dup = find_duplicate(name, existing_names, existing_list + new_entities, entity_type)
        if dup:
            duplicates.append((name, dup))
            continue

        eid = slugify(name)
        if eid in existing or any(e["id"] == eid for e in new_entities):
            eid = eid + "-wc"

        addr = item.get("addr", "")
        province_old = item.get("province_old", "Vĩnh Long")
        district = item.get("district", "")

        entity = {
            "id": eid,
            "type": entity_type,
            "name": name,
            "placeId": guess_place_id(addr, province_old, district),
            "summary": (item.get("desc") or "").strip(),
            "source": {"title": "Ward Crawl 130 — vinhlong360", "url": "https://vinhlong360.vn/"},
            "status": "provisional",
            "verified": False,
            "confidence": 0.7,
            "updatedAt": time.strftime("%Y-%m-%d"),
        }

        attrs = {}
        if addr:
            attrs["address"] = addr
        if province_old:
            attrs["province_old"] = province_old
        if district:
            attrs["district"] = district
        if item.get("ward"):
            attrs["ward"] = item["ward"]
        if attrs:
            entity["attributes"] = attrs

        # Geocode
        geo_q = f"{name}, {addr}" if addr else f"{name}, {district}, {province_old}, Việt Nam"
        coords = geocode_osm(geo_q)
        if coords:
            entity["coords"] = coords
            entity["confidence"] = 0.78
        else:
            coords2 = geocode_osm(f"{name}, {province_old}, Việt Nam")
            if coords2:
                entity["coords"] = coords2

        new_entities.append(entity)
        existing_names.add(name.lower())
        time.sleep(0.5)

    print(f"\n═══ Kết quả ═══")
    print(f"  Mới:    {len(new_entities)}")
    print(f"  Trùng:  {len(duplicates)}")
    print(f"  Có GPS: {sum(1 for e in new_entities if e.get('coords'))}/{len(new_entities)}")

    # By type
    by_type = {}
    for e in new_entities:
        by_type[e["type"]] = by_type.get(e["type"], 0) + 1
    print(f"  Loại: {dict(sorted(by_type.items(), key=lambda x:-x[1]))}")

    # By province
    by_prov = {}
    for e in new_entities:
        p = e.get("attributes", {}).get("province_old", "?")
        by_prov[p] = by_prov.get(p, 0) + 1
    print(f"  Tỉnh: {by_prov}")

    if new_entities:
        data["entities"].extend(new_entities)
        with open(DATA_JSON, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n✓ Đã lưu data.json — tổng {len(data['entities'])} entities")

if __name__ == "__main__":
    main()
