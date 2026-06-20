"""
Crawl Foody.vn listings for Vinh Long, Ben Tre, Tra Vinh.
Output: scratch/foody_crawled.json

Usage:
  python scripts/crawl_foody.py                        # all provinces, all pages
  python scripts/crawl_foody.py --province vinh-long   # single province
  python scripts/crawl_foody.py --page 5 --pages 10    # page range
  python scripts/crawl_foody.py --resume               # resume from checkpoint
"""
import argparse, json, re, time, sqlite3, unicodedata
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "agent" / "data" / "vinhlong360.db"
OUT_DIR = ROOT / "scratch"
OUT_PATH = OUT_DIR / "foody_crawled.json"
CHECKPOINT_PATH = OUT_DIR / "foody_checkpoint.json"

PROVINCES = [
    {"slug": "vinh-long", "area": "vinh-long", "name": "Vinh Long"},
    {"slug": "ben-tre", "area": "ben-tre", "name": "Ben Tre"},
    {"slug": "tra-vinh", "area": "tra-vinh", "name": "Tra Vinh"},
]

ITEMS_PER_PAGE = 12
MIN_RATING = 7.0
DELAY_BETWEEN_PAGES = 2.0
DELAY_BETWEEN_PROVINCES = 5.0

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
}

sess = requests.Session()
sess.headers.update(HEADERS)


def normalize(s: str) -> str:
    s = unicodedata.normalize("NFC", s.strip().lower())
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


def load_existing_names() -> set:
    if not DB_PATH.exists():
        return set()
    conn = sqlite3.connect(str(DB_PATH))
    rows = conn.execute(
        "SELECT name FROM entities WHERE type IN ('dish','accommodation','experience','attraction')"
    ).fetchall()
    conn.close()
    return {normalize(r[0]) for r in rows}


def parse_total(html: str) -> int:
    soup = BeautifulSoup(html, "html.parser")
    el = soup.select_one(".result-counts, .result-status-count")
    if el:
        m = re.search(r"([\d.]+)", el.get_text())
        if m:
            return int(m.group(1).replace(".", ""))
    return 0


def parse_listing(html: str, province_slug: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    items = []

    for card in soup.select(".row-item.filter-result-item"):
        name_el = card.select_one(".resname h2 a")
        if not name_el:
            continue

        name = name_el.get_text(strip=True)
        if not name or len(name) < 2:
            continue

        href = name_el.get("href", "")
        slug = href.rstrip("/").split("/")[-1] if href else ""

        point_el = card.select_one(".point.highlight-text, .point")
        try:
            rating = float(point_el.get_text(strip=True)) if point_el else 0.0
        except ValueError:
            rating = 0.0

        addr_el = card.select_one(".result-address .address")
        address = addr_el.get_text(" ", strip=True) if addr_el else ""
        address = re.sub(r"\s+", " ", address)

        comments = 0
        stats_links = card.select(".stats a")
        if stats_links:
            first_span = stats_links[0].select_one("span:last-child")
            if first_span:
                try:
                    comments = int(first_span.get_text(strip=True))
                except ValueError:
                    pass

        items.append({
            "name": name,
            "slug": slug,
            "rating": rating,
            "address": address,
            "comments": comments,
            "url": f"https://www.foody.vn{href}" if href.startswith("/") else href,
        })

    return items


def crawl_province(prov: dict, start_page: int, max_pages: int) -> list[dict]:
    slug = prov["slug"]
    area = prov["area"]
    all_items = []

    url = f"https://www.foody.vn/{slug}/dia-diem?page={start_page}"
    print(f"[{area}] page {start_page}: {url}")

    try:
        resp = sess.get(url, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"[{area}] ERROR page {start_page}: {e}")
        return all_items

    total = parse_total(resp.text)
    total_pages = max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    print(f"[{area}] {total} results, {total_pages} pages")

    items = parse_listing(resp.text, slug)
    for it in items:
        it["area"] = area
    all_items.extend(items)
    print(f"[{area}] page {start_page}: {len(items)} items")

    end_page = min(start_page + max_pages - 1, total_pages)
    for page in range(start_page + 1, end_page + 1):
        time.sleep(DELAY_BETWEEN_PAGES)
        url = f"https://www.foody.vn/{slug}/dia-diem?page={page}"

        try:
            resp = sess.get(url, timeout=15)
            resp.raise_for_status()
        except Exception as e:
            print(f"[{area}] ERROR page {page}: {e}")
            save_checkpoint(area, page, all_items)
            continue

        items = parse_listing(resp.text, slug)
        for it in items:
            it["area"] = area
        all_items.extend(items)

        if page % 5 == 0 or page == end_page:
            print(f"[{area}] page {page}/{end_page}: +{len(items)} (total {len(all_items)})")

        if page % 20 == 0:
            save_checkpoint(area, page, all_items)

    return all_items


def save_checkpoint(area: str, page: int, items: list):
    cp = {"area": area, "page": page, "count": len(items)}
    CHECKPOINT_PATH.write_text(json.dumps(cp), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--province", choices=["vinh-long", "ben-tre", "tra-vinh"])
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--pages", type=int, default=999)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    print("Loading existing entities for dedup...")
    existing = load_existing_names()
    print(f"  {len(existing)} existing names")

    all_crawled = []
    if args.resume and OUT_PATH.exists():
        all_crawled = json.loads(OUT_PATH.read_text(encoding="utf-8"))
        print(f"  Resumed {len(all_crawled)} previous items")

    provinces = PROVINCES
    if args.province:
        provinces = [p for p in PROVINCES if p["slug"] == args.province]

    for prov in provinces:
        print(f"\n{'='*50}")
        print(f"  {prov['name']} ({prov['slug']})")
        print(f"{'='*50}")

        items = crawl_province(prov, args.page, args.pages)
        all_crawled.extend(items)

        if prov != provinces[-1]:
            print(f"  Waiting {DELAY_BETWEEN_PROVINCES}s...")
            time.sleep(DELAY_BETWEEN_PROVINCES)

    # Post-process
    print(f"\n{'='*50}")
    print(f"Raw: {len(all_crawled)}")

    quality = [i for i in all_crawled if i.get("rating", 0) >= MIN_RATING]
    print(f"Rating >= {MIN_RATING}: {len(quality)}")

    seen = set()
    unique = []
    for item in quality:
        if item["slug"] not in seen:
            seen.add(item["slug"])
            unique.append(item)
    print(f"Dedup slug: {len(unique)}")

    new_items = [i for i in unique if normalize(i["name"]) not in existing]
    print(f"New (not in DB): {len(new_items)}")

    OUT_DIR.mkdir(exist_ok=True)
    OUT_PATH.write_text(json.dumps(new_items, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved to {OUT_PATH}")

    from collections import Counter
    for area, count in sorted(Counter(i["area"] for i in new_items).items()):
        print(f"  {area}: {count}")


if __name__ == "__main__":
    main()
