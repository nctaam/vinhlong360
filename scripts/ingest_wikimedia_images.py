"""Ingest images from Vietnamese Wikipedia for entities without images.

B6 compliant: Wikipedia images are CC-BY-SA / CC0 / public domain.
Stores: entity.images = ["url1", ...]
Also stores attribution in entity.attributes.image_credits.

Strategy: Search Vietnamese Wikipedia for articles matching entity name,
then extract the article's lead image. Works best for dishes, well-known
landmarks, and cultural sites. Category fallback images in /img/cat/
cover entities without specific images.

Usage:
    python scripts/ingest_wikimedia_images.py --mode=queue          # RECOMMENDED: queue candidates for admin review at /admin/duyet-anh (NO publish — B6)
    python scripts/ingest_wikimedia_images.py --mode=queue dish     # queue, specific type only
    python scripts/ingest_wikimedia_images.py --mode=queue --dry-run  # collect + preview, don't post
    python scripts/ingest_wikimedia_images.py           # direct-publish (legacy, bypasses review)
    python scripts/ingest_wikimedia_images.py dish       # direct-publish, specific type
    python scripts/ingest_wikimedia_images.py --dry-run  # preview only

Queue mode needs: ADMIN_API_KEY env (X-Admin-Key) + optionally VL_API_BASE (default http://127.0.0.1:8360).
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
                  "accommodation", "product", "history", "event", "landmark", "culture"]

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


# §1.4: chặn match SAI rõ ràng. Wikipedia fuzzy-search hay trả bài phổ-biến nhưng KHÁC nơi
# (Hội An/Văn Miếu Hà Nội...) hoặc bài CHỦ-ĐỀ chung (Du lịch/Ẩm thực/Siêu thị) → KHÔNG phải
# ảnh của entity. Loại trước khi đưa vào hàng đợi để admin không phải lọc rác + tránh duyệt nhầm.
OUT_OF_AREA = ["hội an", "hà nội", "cần thơ", "sài gòn", "hồ chí minh", "thừa thiên",
               "huế", "đà nẵng", "quốc tử giám", "phú quốc", "đà lạt", "nha trang",
               "hạ long", "sa pa", "đồng tháp", "an giang", "kiên giang", "sóc trăng",
               "bạc liêu", "cà mau", "tiền giang", "long an", "hậu giang", "vũng tàu",
               "bến thành", "chứng tích chiến tranh", "củ chi", "mỹ tho"]
# Bài CHỦ-ĐỀ chung — KHÔNG phải ảnh của một entity cụ thể. Chặn TUYỆT ĐỐI (kể cả khi tên
# entity tình cờ chứa từ này: vd "Du lịch sinh thái Sala" KHÔNG nên lấy ảnh bài "Du lịch").
GENERIC_BLOCK = ["du lịch", "ẩm thực", "siêu thị", "năm du lịch", "việt nam",
                 "đông nam á", "châu á", "thế giới", "danh sách",
                 "triều tiên", "hàn quốc", "trung quốc", "nhật bản", "ki-tô", "công giáo",
                 "phật giáo", "giáo phận", "tôn giáo"]


def _obviously_wrong(entity: dict, wiki_title: str) -> bool:
    """True nếu title rõ ràng KHÔNG phải entity (ngoài-vùng / chủ-đề chung)."""
    t = wiki_title.lower()
    name = entity["name"].lower()
    for bad in OUT_OF_AREA:
        if bad in t and bad not in name:
            return True
    for g in GENERIC_BLOCK:  # chặn tuyệt đối bài chủ-đề chung
        if g in t:
            return True
    return False


def is_relevant(entity: dict, wiki_title: str) -> bool:
    """Check if a Wikipedia article title is likely relevant to the entity."""
    if _obviously_wrong(entity, wiki_title):
        return False
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


API_BASE = os.environ.get("VL_API_BASE", "http://127.0.0.1:8360")
ADMIN_KEY = os.environ.get("ADMIN_API_KEY", "")


def _match_confidence(entity: dict, title: str) -> float:
    """Heuristic 0..1 that `title` matches the entity — a hint for the human reviewer.
    Name-match is the only reliable signal (Wikipedia fuzzy hits are ~50% wrong)."""
    nw = set(entity["name"].lower().split())
    tw = set(title.lower().split())
    overlap = len(nw & tw)
    if overlap >= 2:
        return 0.85
    if overlap == 1:
        return 0.6
    return 0.45


def post_suggestions(suggestions: list[dict]) -> None:
    """POST candidates to the admin review queue. NO publish — items sit pending at
    /admin/duyet-anh until a human approves (B6 + accuracy: Wikipedia name-match is
    ~50% wrong on fuzzy hits, so a review gate is mandatory)."""
    if not ADMIN_KEY:
        print("ERROR: set ADMIN_API_KEY (and optionally VL_API_BASE) to queue suggestions.")
        sys.exit(1)
    url = f"{API_BASE}/admin/image-suggestions/create-batch"
    headers = {**HEADERS, "X-Admin-Key": ADMIN_KEY, "Content-Type": "application/json"}
    sent = 0
    for i in range(0, len(suggestions), 100):
        chunk = suggestions[i:i + 100]
        try:
            r = httpx.post(url, json={"suggestions": chunk}, headers=headers, timeout=30)
            r.raise_for_status()
            res = r.json()
            sent += int(res.get("created", res.get("inserted", len(chunk))) or 0)
            print(f"  queued batch {i // 100 + 1}: {res}")
        except Exception as e:
            print(f"  batch POST failed: {e}")
    print(f"\nQueued {sent} suggestion(s) -> review/approve at /admin/duyet-anh (NOT published).")


def main():
    dry_run = "--dry-run" in sys.argv
    queue_mode = "--mode=queue" in sys.argv or "--queue" in sys.argv
    limit_arg = next((a for a in sys.argv if a.startswith("--limit=")), None)
    limit = int(limit_arg.split("=", 1)[1]) if limit_arg else None
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    target_type = args[0] if args else None

    with open(DATA_FILE, encoding="utf-8") as f:
        data = json.load(f)
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

    if limit:
        need_images = need_images[:limit]
    print(f"Found {len(need_images)} entities needing images")
    if target_type:
        print(f"  (filtered to type: {target_type})")
    if dry_run:
        print("  [DRY RUN — no changes will be saved]")

    # ── Review-queue mode (B6-safe): collect candidates → POST to admin queue, NO publish ──
    if queue_mode:
        suggestions = []
        skipped = 0
        for i, entity in enumerate(need_images):
            print(f"[{i+1}/{len(need_images)}] {entity['id']}: {entity['name']}")
            result = search_wikipedia_image(entity["name"], entity)
            if not result:
                skipped += 1
                print("  (no relevant image)")
                continue
            conf = _match_confidence(entity, result["title"])
            suggestions.append({
                "entity_id": entity["id"],
                "candidate_url": result["url"],
                "wp_title": result["title"],
                "license": result.get("license", ""),
                "author": result.get("author", ""),
                "source": "wikipedia-vi",
                "match_confidence": conf,
            })
            print(f"  candidate: {result['title']} (conf {conf})")
            time.sleep(0.3)
        print(f"\nCollected {len(suggestions)} candidate(s) ({skipped} no-match).")
        if not suggestions or dry_run:
            if dry_run:
                print("[DRY RUN] not posting to queue.")
            return
        post_suggestions(suggestions)
        return

    # ── Direct-publish mode (legacy): writes entity.images immediately. ──
    # WARNING: bypasses human review. Prefer --mode=queue (B6 + ~50% fuzzy-match error).
    print("  [direct-publish mode — bypasses review; use --mode=queue for the B6-safe path]")
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
