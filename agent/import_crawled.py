"""
Import dữ liệu crawled → đề xuất entity mới.

Bước:
1. Đọc crawled data + data hiện có
2. Dùng LLM map placeId cho các entity thiếu
3. Loại bỏ trùng lắp
4. Xuất file đề xuất để review

Chạy: python agent/import_crawled.py
"""

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

client = OpenAI(
    api_key=os.environ["LLM_API_KEY"],
    base_url=os.environ["LLM_BASE_URL"],
)
MODEL = os.environ.get("LLM_MODEL_MINI", "cx/gpt-5.4-mini")

ROOT = Path(__file__).resolve().parent.parent
CRAWLED_DIR = Path(__file__).resolve().parent / "crawled"
DATA_JSON = ROOT / "web" / "data.json"

# Mapping thủ công cho các địa điểm nổi tiếng
KNOWN_PLACES = {
    "khu-du-lich-vinh-sang": ("xa-an-binh", "DUPLICATE:khu-du-lich-vinh-sang"),
    "ut-trinh": ("xa-an-binh", "DUPLICATE:homestay-ut-trinh"),
    "bao-tang-vinh-long": ("p-long-chau", "DUPLICATE:bao-tang-vinh-long"),
    "nha-dua-cocohome": ("xa-an-binh", None),
    "peace-farm": ("xa-an-binh", None),
    "du-lich-sinh-thai-sala": ("xa-an-binh", None),
    "du-lich-vuon-chu-7-gat": ("xa-an-binh", None),
    "khu-du-lich-cho-noi-tra-on": ("xa-luc-si-thanh", None),
    "khu-du-lich-s-mo-farm-cuu-long": ("xa-an-binh", None),
    "bao-tang-dua-sap-tra-vinh": ("xa-cau-ke", None),
    "khu-mo-than-nhan-danh-than-thoai-ngoc-hau": ("p-long-chau", None),
    "lo-com-cuu-long": ("p-long-chau", None),
    "nha-gom-tu-buoi": ("xa-nhon-phu", None),
    "chua-khmer-vinh-long": ("xa-tra-on", None),
    "chua-phuoc-hau": ("p-phuoc-hau", None),
    "chua-tien-chau": ("p-long-chau", None),
    "dinh-long-thanh": ("p-thanh-duc", None),
    "dinh-tan-hoa": ("p-tan-hanh", None),
}


def load_existing():
    """Load data.json hiện có."""
    with open(DATA_JSON, encoding="utf-8") as f:
        data = json.load(f)
    return {e["id"]: e for e in data.get("entities", [])}


def load_crawled():
    """Load tất cả file crawled."""
    all_file = CRAWLED_DIR / "_all_crawled.json"
    if all_file.exists():
        with open(all_file, encoding="utf-8") as f:
            return json.load(f)
    return []


def main():
    print("═══ Import Crawled Data ═══\n")

    existing = load_existing()
    crawled = load_crawled()
    print(f"Existing entities: {len(existing)}")
    print(f"Crawled entities: {len(crawled)}\n")

    new_entities = []
    duplicates = []
    unmapped = []

    try:
        import kb_curation
        has_curation = True
    except ImportError:
        has_curation = False

    try:
        import geocode as geo
        has_geocode = True
    except ImportError:
        has_geocode = False

    all_entities_list = list(existing.values())

    for entity in crawled:
        eid = entity["id"]

        # Map placeId
        if eid in KNOWN_PLACES:
            place_id, dup_of = KNOWN_PLACES[eid]
            entity["placeId"] = place_id
            if dup_of and dup_of.startswith("DUPLICATE:"):
                duplicates.append((entity["name"], dup_of.split(":")[1]))
                continue
        elif not entity.get("placeId"):
            unmapped.append(entity)
            continue

        # Check trùng tên
        is_dup = False
        for ex in existing.values():
            if ex.get("name", "").lower() == entity["name"].lower():
                duplicates.append((entity["name"], ex["id"]))
                is_dup = True
                break
        if is_dup:
            continue

        # Near-duplicate detection (token overlap + cross-type)
        if has_curation:
            dup_id = kb_curation.find_near_duplicate(
                entity["name"], entity.get("type", "attraction"),
                all_entities_list + new_entities,
            )
            if dup_id:
                duplicates.append((entity["name"], dup_id))
                continue

        # Check trùng ID
        if eid in existing:
            entity["id"] = eid + "-vlt"

        # Geocode via OSM (coordinates NEVER from LLM)
        if has_geocode and not entity.get("coords"):
            addr = entity.get("_address_raw", "")
            q = entity["name"] if not addr else f"{entity['name']}, {addr}"
            coords = geo.geocode(q, region="Vĩnh Long")
            if coords:
                entity["coords"] = coords

        # Mark as provisional (official source → higher confidence than LLM)
        entity["status"] = "provisional"
        entity["verified"] = False
        entity["confidence"] = 0.7 if entity.get("coords") else 0.6
        entity["learned_at"] = __import__("time").strftime("%Y-%m-%d")

        # Cleanup
        entity.pop("_crawled_from", None)
        entity.pop("_address_raw", None)

        new_entities.append(entity)

    # Report
    print(f"── Kết quả ──")
    print(f"Mới (thêm được): {len(new_entities)}")
    print(f"Trùng lắp (bỏ):  {len(duplicates)}")
    print(f"Chưa map placeId: {len(unmapped)}")

    if duplicates:
        print(f"\n── Trùng lắp ──")
        for name, existing_id in duplicates:
            print(f"  ✗ {name} ≈ {existing_id}")

    if unmapped:
        print(f"\n── Chưa map ──")
        for e in unmapped:
            print(f"  ? {e['name']} (address: {e.get('_address_raw', '?')})")

    if new_entities:
        print(f"\n── Entity mới ──")
        for e in new_entities:
            print(f"  ✓ {e['name']} → {e['type']} → {e.get('placeId', '?')}")

        # Save
        out_file = CRAWLED_DIR / "_proposed_new.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(new_entities, f, ensure_ascii=False, indent=2)
        print(f"\nĐã lưu: {out_file}")
        print("Review file này rồi chạy: python agent/import_crawled.py --apply")

    if "--apply" in sys.argv and new_entities:
        apply_to_data(new_entities)


def apply_to_data(new_entities):
    """Thêm entities mới vào data.json."""
    with open(DATA_JSON, encoding="utf-8") as f:
        data = json.load(f)

    data["entities"].extend(new_entities)

    with open(DATA_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Đã thêm {len(new_entities)} entity vào data.json")
    print(f"  Tổng entities: {len(data['entities'])}")


if __name__ == "__main__":
    main()
