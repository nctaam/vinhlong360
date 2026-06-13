"""
Import đợt crawl sâu: Trà Vinh (~27 entities), Bến Tre (~25), Vĩnh Long (~22).

Chạy: python agent/import_deep_crawl.py [--apply]
"""

import json, os, sys, re, time, unicodedata
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
DATA_JSON = ROOT / "web" / "data.json"
CRAWLED_DIR = Path(__file__).resolve().parent / "crawled"

FILES = [
    (CRAWLED_DIR / "crawl_deep_travinh_raw.json", "Trà Vinh", "xa-tra-on"),
    (CRAWLED_DIR / "crawl_deep_bentre_raw.json",  "Bến Tre",  "xa-an-binh"),
    (CRAWLED_DIR / "crawl_deep_vinhlong_raw.json", "Vĩnh Long", None),
]

PLACE_KEYWORDS = {
    # BT districts
    "Thạnh Phú": "xa-an-binh",
    "Mỏ Cày Nam": "xa-an-binh",
    "Mỏ Cày Bắc": "xa-an-binh",
    "Mỏ Cày": "xa-an-binh",
    "Chợ Lách": "xa-an-binh",
    "Ba Tri": "xa-an-binh",
    "Bình Đại": "xa-an-binh",
    "Giồng Trôm": "xa-an-binh",
    "Châu Thành": "xa-an-binh",
    "TP Bến Tre": "xa-an-binh",
    "Bến Tre": "xa-an-binh",
    # TV districts
    "Duyên Hải": "xa-tra-on",
    "Trà Cú": "xa-tra-on",
    "Cầu Kè": "xa-tra-on",
    "Cầu Ngang": "xa-tra-on",
    "Tiểu Cần": "xa-tra-on",
    "Càng Long": "xa-tra-on",
    "Châu Thành TV": "xa-tra-on",
    "TP Trà Vinh": "xa-tra-on",
    "Trà Vinh": "xa-tra-on",
    # VL districts
    "Trà Ôn": "xa-tra-on",
    "Tam Bình": "p-phuoc-hau",
    "Vũng Liêm": "p-phuoc-hau",
    "Bình Minh": "xa-an-binh",
    "Long Hồ": "p-long-chau",
    "Mang Thít": "p-phuoc-hau",
}


def slugify(text):
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.lower().strip()
    text = re.sub(r"[đĐ]", "d", text)
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s-]+", "-", text).strip("-")
    return text[:80]


def guess_place_id(addr, province_old, default_pid):
    # GĐ-audit (B2): bỏ default_pid + province fallback (dồn cả tỉnh vào 1 xã "thùng chứa").
    # Cần crosswalk chính thống để gán xã đúng; trước đó để None còn hơn sai.
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
    apply = "--apply" in sys.argv

    print("═══ Import Deep Crawl: TV + BT + VL ═══\n")

    with open(DATA_JSON, encoding="utf-8") as f:
        data = json.load(f)
    existing = {e["id"]: e for e in data.get("entities", [])}
    existing_names = {e["name"].lower() for e in existing.values()}
    existing_list = list(existing.values())

    all_new = []
    all_dups = []
    file_stats = {}

    for fpath, province, default_pid in FILES:
        if not fpath.exists():
            print(f"  ! Không tìm thấy: {fpath.name}")
            continue

        with open(fpath, encoding="utf-8") as f:
            items = json.load(f)

        cat_new = 0
        cat_dup = 0

        for item in items:
            name = item.get("name", "")
            if not name:
                continue

            entity_type = item.get("type", "attraction")

            dup = find_duplicate(name, existing_names, existing_list + all_new, entity_type)
            if dup:
                all_dups.append((name, dup, province))
                cat_dup += 1
                continue

            eid = slugify(name)
            if eid in existing or any(e["id"] == eid for e in all_new):
                eid = eid + "-dc"

            addr = item.get("addr", "")
            prov_old = item.get("province_old", province)
            pid = guess_place_id(addr, prov_old, default_pid)

            entity = {
                "id": eid,
                "type": entity_type,
                "name": name,
                "placeId": pid,
                "summary": item.get("desc", ""),
                "source": {
                    "title": f"mytour.vn / mia.vn ({prov_old})",
                    "url": "https://mytour.vn/",
                },
                "status": "provisional",
                "verified": False,
                "confidence": 0.75,
                "updatedAt": time.strftime("%Y-%m-%d"),
            }

            attrs = {}
            if addr:
                attrs["address"] = addr
            if prov_old:
                attrs["province_old"] = prov_old
            if attrs:
                entity["attributes"] = attrs

            # Geocode — full address first, then simplified
            geo_q1 = f"{name}, {addr}" if addr else f"{name}, {prov_old}, Việt Nam"
            coords = geocode_osm(geo_q1)
            if coords:
                entity["coords"] = coords
                entity["confidence"] = 0.8
            else:
                coords2 = geocode_osm(f"{name}, {prov_old}, Việt Nam")
                if coords2:
                    entity["coords"] = coords2
                    entity["confidence"] = 0.75

            all_new.append(entity)
            existing_names.add(name.lower())
            cat_new += 1
            time.sleep(0.5)

        file_stats[fpath.name] = {"new": cat_new, "dup": cat_dup, "total": len(items)}
        print(f"  {province}: {cat_new} new, {cat_dup} dup (of {len(items)})")

    # ── Summary ──────────────────────────────────────────────
    total_new = sum(s["new"] for s in file_stats.values())
    total_dup = sum(s["dup"] for s in file_stats.values())
    with_coords = sum(1 for e in all_new if e.get("coords"))

    print(f"\n═══ Kết quả tổng ═══")
    print(f"  Mới:    {total_new}")
    print(f"  Trùng:  {total_dup}")
    print(f"  Có GPS: {with_coords}/{total_new}")

    if all_dups:
        print(f"\n── Trùng lắp ({total_dup}) ──")
        for name, dup_of, prov in all_dups:
            print(f"  ✗ [{prov}] {name} ≈ {dup_of}")

    if all_new:
        print(f"\n── Entity mới ({total_new}) ──")
        by_type = {}
        for e in all_new:
            gps = "📍" if e.get("coords") else "  "
            prov = e.get("attributes", {}).get("province_old", "")
            print(f"  {gps} [{e['type']:14}] {e['name']} ({prov})")
            by_type[e["type"]] = by_type.get(e["type"], 0) + 1
        print(f"\n  Phân loại: {dict(sorted(by_type.items(), key=lambda x: -x[1]))}")

        out = CRAWLED_DIR / "_deep_crawl_proposed.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(all_new, f, ensure_ascii=False, indent=2)
        print(f"\nĐã lưu proposed: {out}")

    if apply and all_new:
        data["entities"].extend(all_new)
        with open(DATA_JSON, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n✓ Đã lưu data.json — tổng {len(data['entities'])} entities")
    elif all_new and not apply:
        print(f"\nChạy lại với --apply để import vào data.json")


if __name__ == "__main__":
    main()
