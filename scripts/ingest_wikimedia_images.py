"""Ingest images from Vietnamese Wikipedia for entities without images.

B6 compliant: Wikipedia images are CC-BY-SA / CC0 / public domain.
Stores: entity.images = ["url1", ...]
Also stores attribution in entity.attributes.image_credits.

Strategy: Search Vietnamese Wikipedia for articles matching entity name,
then extract the article's lead image. Works best for dishes, well-known
landmarks, and cultural sites. Category fallback images in /img/cat/
cover entities without specific images.

Usage:
    python scripts/ingest_wikimedia_images.py           # all types
    python scripts/ingest_wikimedia_images.py dish       # specific type
    python scripts/ingest_wikimedia_images.py --dry-run  # preview only
"""

import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
os.chdir(os.path.join(os.path.dirname(__file__), ".."))

import httpx

DATA_FILE = "web/data.json"
VI_WIKI_API = "https://vi.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "vinhlong360/1.0 (https://vinhlong360.vn; contact@vinhlong360.vn)"}

PRIORITY_TYPES = ["dish", "attraction", "nature", "experience", "craft_village",
                  "accommodation", "product"]

AREA_KEYWORDS = {
    "vinh-long": ["vĩnh long", "cửu long", "mang thít", "long hồ", "trà ôn",
                  "bình tân", "tam bình", "vũng liêm", "bình minh"],
    "ben-tre": ["bến tre", "giồng trôm", "mỏ cày", "châu thành", "chợ lách",
                "ba tri", "bình đại", "thạnh phú"],
    "tra-vinh": ["trà vinh", "cầu kè", "tiểu cần", "châu thành", "trà cú",
                 "duyên hải", "cầu ngang"],
}

DISH_KEYWORDS = ["món", "ẩm thực", "nấu", "thực phẩm", "bánh", "bún", "phở",
                 "cơm", "lẩu", "chả", "gỏi", "canh", "cá", "thịt", "mắm",
                 "food", "cuisine", "dish", "soup", "noodle"]

NATURE_KEYWORDS = ["sông", "rừng", "biển", "hồ", "cồn", "cù lao", "đảo",
                   "thiên nhiên", "sinh thái", "ngập mặn"]

ATTRACTION_KEYWORDS = ["chùa", "đình", "miếu", "nhà thờ", "cầu", "chợ",
                       "bảo tàng", "di tích", "đền", "lăng", "kiến trúc",
                       "tượng đài", "công viên"]


def is_relevant(entity: dict, wiki_title: str) -> bool:
    """Check if a Wikipedia article title is likely relevant to the entity."""
    name_lower = entity["name"].lower()
    title_lower = wiki_title.lower()
    etype = entity.get("type", "")
    area = entity.get("area", "")

    # Direct name match (best case)
    name_words = set(name_lower.split())
    title_words = set(title_lower.split())
    overlap = name_words & title_words
    if len(overlap) >= 2:
        return True

    # For dishes: check if Wikipedia title contains food-related keywords
    if etype == "dish":
        if any(kw in title_lower for kw in DISH_KEYWORDS):
            return True
        if any(kw in title_lower for kw in name_lower.split() if len(kw) > 2):
            return True

    # For nature: check nature keywords
    if etype == "nature":
        if any(kw in title_lower for kw in NATURE_KEYWORDS):
            if any(w in title_lower for w in name_lower.split() if len(w) > 2):
                return True

    # For attractions: check cultural keywords
    if etype == "attraction":
        if any(kw in title_lower for kw in ATTRACTION_KEYWORDS):
            if any(w in title_lower for w in name_lower.split() if len(w) > 2):
                return True

    # Area match as bonus signal
    if area in AREA_KEYWORDS:
        if any(kw in title_lower for kw in AREA_KEYWORDS[area]):
            if any(w in title_lower for w in name_lower.split() if len(w) > 2):
                return True

    return False


def search_wikipedia_image(name: str, entity: dict) -> dict | None:
    """Search Vietnamese Wikipedia for an article and get its lead image."""
    params = {
        "action": "query", "format": "json",
        "generator": "search",
        "gsrsearch": name,
        "gsrlimit": "5",
        "prop": "pageimages|info",
        "piprop": "thumbnail",
        "pithumbsize": "800",
    }
    try:
        resp = httpx.get(VI_WIKI_API, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        pages = data.get("query", {}).get("pages", {})
        for page in sorted(pages.values(), key=lambda p: p.get("index", 999)):
            thumb = page.get("thumbnail", {})
            title = page.get("title", "")
            if not thumb or not thumb.get("source"):
                continue
            url = thumb["source"]
            # Skip non-photo images (logos, maps, flags, SVGs)
            if any(skip in url.lower() for skip in [".svg", "flag_of", "coat_of", "logo", "emblem", "location_map"]):
                continue
            if is_relevant(entity, title):
                return {
                    "url": url,
                    "title": title,
                    "source": "Wikipedia vi",
                    "license": "CC-BY-SA",
                }
    except Exception as e:
        print(f"  API error: {e}")
    return None


def main():
    dry_run = "--dry-run" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    target_type = args[0] if args else None

    data = json.load(open(DATA_FILE, encoding="utf-8"))
    entities = data["entities"]

    need_images = []
    for e in entities:
        if target_type and e.get("type") != target_type:
            continue
        if e.get("type") not in PRIORITY_TYPES:
            continue
        if e.get("images") and len(e["images"]) > 0:
            continue
        need_images.append(e)

    print(f"Found {len(need_images)} entities needing images")
    if target_type:
        print(f"  (filtered to type: {target_type})")
    if dry_run:
        print("  [DRY RUN — no changes will be saved]")

    updated = 0
    skipped = 0

    for i, entity in enumerate(need_images):
        name = entity["name"]
        eid = entity["id"]
        print(f"[{i+1}/{len(need_images)}] {eid}: {name}")

        result = search_wikipedia_image(name, entity)

        if not result:
            skipped += 1
            print(f"  (no relevant image)")
            continue

        if dry_run:
            updated += 1
            print(f"  WOULD ADD: {result['title']} → {result['url'][:70]}...")
            continue

        entity["images"] = [result["url"]]

        attrs = entity.get("attributes", {}) or {}
        attrs["image_credits"] = f"Wikipedia ({result['license']})"
        entity["attributes"] = attrs

        updated += 1
        print(f"  + {result['title']}")

        time.sleep(0.3)

        if updated % 50 == 0:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"  [saved {updated} so far]")

    if not dry_run and updated > 0:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\nUpdated {updated} entities with images ({skipped} skipped)")

        try:
            from database import db
            for e in need_images:
                if e.get("images") and len(e["images"]) > 0:
                    db.upsert_entity(e)
            print("Updated DB")
        except Exception as ex:
            print(f"DB update skipped: {ex}")
    else:
        print(f"\n{'Would update' if dry_run else 'Updated'}: {updated} ({skipped} skipped)")


if __name__ == "__main__":
    main()
