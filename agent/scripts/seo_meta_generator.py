#!/usr/bin/env python3
"""SEO Meta Content Generator — GPT-5.5 multi-layer SEO optimization.

Generates for every page route:
  Layer 1: Meta title + description (Google SERP optimized)
  Layer 2: Open Graph title/description/image-alt (social sharing)
  Layer 3: Schema.org structured data suggestions
  Layer 4: Internal linking keywords
  Layer 5: GEO (Generative Engine Optimization) — entity-rich snippets for AI search

Also generates per-category and per-region landing page SEO.

Output: agent/data/seo/ — JSON files for review + integration.
"""
from __future__ import annotations
import json
import os
import sys
import time
import threading
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = AGENT_DIR.parent
OUTPUT_DIR = AGENT_DIR / "data" / "seo"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(AGENT_DIR))
os.environ["PYTHONUNBUFFERED"] = "1"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_DIR / ".env")
except Exception:
    pass

from openai import OpenAI

LLM_BASE = os.environ.get("LLM_BASE_URL", "")
LLM_KEY = os.environ.get("LLM_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "cx/gpt-5.5")

client = OpenAI(base_url=LLM_BASE, api_key=LLM_KEY)
_lock = threading.Lock()
RUN_TS = datetime.now().strftime("%Y%m%d_%H%M%S")

PAGES = [
    {"route": "/", "name": "Trang chủ", "context": "Landing page du lịch Vĩnh Long, Bến Tre, Trà Vinh. Tìm kiếm điểm đến, lịch trình, đặc sản."},
    {"route": "/du-lich", "name": "Du lịch - Trải nghiệm", "context": "Catalog trải nghiệm du lịch: tham quan, vườn trái cây, chợ nổi, homestay."},
    {"route": "/san-pham", "name": "Đặc sản & OCOP", "context": "Sản phẩm OCOP, đặc sản 3 vùng: kẹo dừa, bánh tráng, trái cây, thủ công."},
    {"route": "/le-hoi", "name": "Lễ hội & Sự kiện", "context": "Lịch lễ hội truyền thống: Lễ Vu Lan, Ok Om Bok, Đua ghe ngo, Chợ hoa Tết."},
    {"route": "/luu-tru", "name": "Lưu trú", "context": "Homestay, khách sạn, resort ven sông, nhà vườn lưu trú."},
    {"route": "/danh-ba", "name": "Danh bạ hành chính", "context": "Số điện thoại, địa chỉ cơ quan hành chính 3 tỉnh — phục vụ dân & du khách."},
    {"route": "/ban-do", "name": "Bản đồ", "context": "Bản đồ tương tác điểm đến, ẩm thực, lưu trú 3 vùng."},
    {"route": "/theo-mua", "name": "Theo mùa", "context": "Du lịch theo mùa: trái cây mùa nào, lễ hội tháng nào, sản phẩm theo mùa."},
    {"route": "/cong-dong", "name": "Cộng đồng", "context": "Feed cộng đồng du khách: chia sẻ review, ảnh, tips."},
    {"route": "/tao-lich-trinh", "name": "Tạo lịch trình", "context": "Công cụ tạo lịch trình du lịch cá nhân hóa."},
    {"route": "/tuyen-duong", "name": "Tuyến đường", "context": "Các tuyến du lịch gợi ý: 2N1Đ, vòng trái cây, chùa Khmer."},
    {"route": "/tim-kiem", "name": "Tìm kiếm", "context": "Trang tìm kiếm toàn bộ nội dung: entity, bài viết, lịch trình."},
    {"route": "/lien-he", "name": "Liên hệ", "context": "Thông tin liên hệ vinhlong360, hợp tác, quảng cáo."},
    {"route": "/ocop", "name": "OCOP", "context": "Sản phẩm OCOP (Mỗi Xã Một Sản Phẩm) 3 tỉnh miền Tây."},
]

REGIONS = [
    {"area": "vinh-long", "name": "Vĩnh Long", "desc": "Miệt vườn cam sành, khoai lang, bưởi Năm Roi, làng gốm Mang Thít, cù lao An Bình"},
    {"area": "ben-tre", "name": "Bến Tre", "desc": "Xứ dừa: kẹo dừa, mật hoa dừa, bưởi da xanh, sân chim Vàm Hồ, Cồn Phụng"},
    {"area": "tra-vinh", "name": "Trà Vinh", "desc": "Văn hóa Khmer: ao Bà Om, chùa cổ, dừa sáp Cầu Kè, bún nước lèo"},
]

CATEGORIES = [
    {"type": "dish", "name": "Ẩm thực", "count": 241},
    {"type": "attraction", "name": "Điểm tham quan", "count": 194},
    {"type": "product", "name": "Đặc sản & OCOP", "count": 218},
    {"type": "history", "name": "Di tích lịch sử", "count": 205},
    {"type": "accommodation", "name": "Lưu trú", "count": 165},
    {"type": "nature", "name": "Thiên nhiên", "count": 130},
    {"type": "experience", "name": "Trải nghiệm", "count": 92},
    {"type": "craft_village", "name": "Làng nghề", "count": 91},
    {"type": "event", "name": "Lễ hội & Sự kiện", "count": 67},
    {"type": "place", "name": "Địa điểm", "count": 358},
]


def tprint(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def llm_call(prompt, system="", retries=2):
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    for attempt in range(retries + 1):
        try:
            r = client.chat.completions.create(
                model=LLM_MODEL, messages=msgs,
                temperature=0.6, max_tokens=3000
            )
            return r.choices[0].message.content.strip()
        except Exception as e:
            if attempt < retries:
                time.sleep(5 * (attempt + 1))
            else:
                raise


def parse_json(text):
    text = re.sub(r"^```(?:json)?|```$", "", (text or "").strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"(\{.*\})", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                pass
    return None


SYSTEM = """Bạn là chuyên gia SEO du lịch Việt Nam, am hiểu Google Search, Google Discover, GEO
(Generative Engine Optimization), Schema.org, Open Graph. Target: du khách Việt tìm du lịch miền
Tây Nam Bộ (Vĩnh Long, Bến Tre, Trà Vinh). Site: vinhlong360.vn — MXH du lịch & OCOP cộng đồng.
Viết meta bằng TIẾNG VIỆT, tự nhiên, kích thích click, chứa từ khóa chính nhưng không nhồi keyword."""


def generate_page_seo(page):
    prompt = f"""Tạo SEO meta content đa tầng cho trang web du lịch vinhlong360.vn:

Trang: {page['name']}
Route: {page['route']}
Bối cảnh: {page['context']}

Trả về JSON:
{{
  "meta_title": "Tiêu đề SEO (50-60 ký tự, chứa từ khóa chính + brand)",
  "meta_description": "Mô tả meta (150-160 ký tự, CTA + USP + từ khóa)",
  "og_title": "Tiêu đề Open Graph cho social sharing (có thể dài hơn meta)",
  "og_description": "Mô tả OG (tối đa 200 ký tự, gợi tò mò, emoji OK)",
  "og_image_alt": "Alt text cho ảnh OG — mô tả hình ảnh đại diện trang",
  "schema_type": "Schema.org type phù hợp (WebPage/CollectionPage/SearchResultsPage/...)",
  "schema_suggestions": "Gợi ý structured data markup cụ thể cho trang này",
  "primary_keywords": ["từ khóa chính 1", "từ khóa 2", "từ khóa 3"],
  "long_tail_keywords": ["cụm từ khóa dài 1 (3-5 từ)", "cụm 2", "cụm 3", "cụm 4", "cụm 5"],
  "geo_snippet": "Đoạn text 2-3 câu tối ưu cho AI search engines (entity-rich, factual, cụ thể)",
  "internal_link_anchors": ["anchor text gợi ý 1 → target", "anchor 2 → target"],
  "google_discover_hooks": ["Tiêu đề style Discover 1 (gợi tò mò)", "Tiêu đề 2"]
}}

CHỈ trả về JSON hợp lệ."""

    try:
        raw = llm_call(prompt, SYSTEM)
        data = parse_json(raw)
        if data:
            data["_route"] = page["route"]
            data["_page_name"] = page["name"]
            tprint(f"  ✓ Page: {page['name']}")
            return data
        tprint(f"  ✗ Page: {page['name']} — parse fail")
    except Exception as e:
        tprint(f"  ✗ Page: {page['name']} — {e}")
    return None


def generate_region_seo(region):
    prompt = f"""Tạo SEO meta content chuyên sâu cho LANDING PAGE vùng du lịch:

Vùng: {region['name']}
Slug: /khu-vuc/{region['area']}
Đặc trưng: {region['desc']}
Website: vinhlong360.vn

Trả về JSON:
{{
  "meta_title": "Tiêu đề SEO (50-60 ký tự)",
  "meta_description": "Mô tả meta (150-160 ký tự)",
  "og_title": "OG title",
  "og_description": "OG description",
  "h1_suggestion": "Tiêu đề H1 gợi ý cho landing page",
  "intro_paragraph": "Đoạn giới thiệu 3-4 câu, sinh động, chứa keywords tự nhiên",
  "primary_keywords": ["kw1", "kw2", "kw3"],
  "long_tail_keywords": ["cụm dài 1", "cụm 2", "cụm 3", "cụm 4", "cụm 5"],
  "geo_snippet": "2-3 câu cho AI search — factual, entity-rich",
  "faq_suggestions": [
    {{"q": "Câu hỏi thường gặp 1", "a": "Câu trả lời ngắn gọn"}},
    {{"q": "Câu 2", "a": "Trả lời"}},
    {{"q": "Câu 3", "a": "Trả lời"}}
  ],
  "competitor_gap_keywords": ["từ khóa đối thủ chưa phủ 1", "kw2", "kw3"]
}}

CHỈ trả về JSON hợp lệ."""

    try:
        raw = llm_call(prompt, SYSTEM)
        data = parse_json(raw)
        if data:
            data["_area"] = region["area"]
            data["_region_name"] = region["name"]
            tprint(f"  ✓ Region: {region['name']}")
            return data
        tprint(f"  ✗ Region: {region['name']} — parse fail")
    except Exception as e:
        tprint(f"  ✗ Region: {region['name']} — {e}")
    return None


def generate_category_seo(cat):
    prompt = f"""Tạo SEO meta content cho CATEGORY PAGE du lịch:

Danh mục: {cat['name']}
Type: {cat['type']}
Số lượng entity: {cat['count']}
Website: vinhlong360.vn (du lịch Vĩnh Long, Bến Tre, Trà Vinh)

Trả về JSON:
{{
  "meta_title": "Tiêu đề SEO (50-60 ký tự)",
  "meta_description": "Mô tả meta (150-160 ký tự)",
  "og_title": "OG title",
  "og_description": "OG description",
  "h1_suggestion": "H1 landing page",
  "intro_paragraph": "Đoạn giới thiệu 2-3 câu",
  "primary_keywords": ["kw1", "kw2", "kw3"],
  "long_tail_keywords": ["cụm dài 1", "cụm 2", "cụm 3"],
  "geo_snippet": "Đoạn text AI search",
  "content_suggestions": ["Ý tưởng bài viết/content 1", "Ý 2", "Ý 3"]
}}

CHỈ trả về JSON hợp lệ."""

    try:
        raw = llm_call(prompt, SYSTEM)
        data = parse_json(raw)
        if data:
            data["_type"] = cat["type"]
            data["_category_name"] = cat["name"]
            tprint(f"  ✓ Category: {cat['name']}")
            return data
        tprint(f"  ✗ Category: {cat['name']} — parse fail")
    except Exception as e:
        tprint(f"  ✗ Category: {cat['name']} — {e}")
    return None


def main():
    tprint("=== SEO Meta Content Generator ===")
    tprint(f"Model: {LLM_MODEL}")

    results = {"pages": [], "regions": [], "categories": [], "generated_at": RUN_TS}

    tprint(f"\n--- Phase 1: {len(PAGES)} Page Routes ---")
    with ThreadPoolExecutor(max_workers=4) as pool:
        futs = {pool.submit(generate_page_seo, p): p for p in PAGES}
        for f in as_completed(futs):
            r = f.result()
            if r:
                results["pages"].append(r)

    tprint(f"\n--- Phase 2: {len(REGIONS)} Region Landing Pages ---")
    with ThreadPoolExecutor(max_workers=3) as pool:
        futs = {pool.submit(generate_region_seo, r): r for r in REGIONS}
        for f in as_completed(futs):
            r = f.result()
            if r:
                results["regions"].append(r)

    tprint(f"\n--- Phase 3: {len(CATEGORIES)} Category Pages ---")
    with ThreadPoolExecutor(max_workers=4) as pool:
        futs = {pool.submit(generate_category_seo, c): c for c in CATEGORIES}
        for f in as_completed(futs):
            r = f.result()
            if r:
                results["categories"].append(r)

    out = OUTPUT_DIR / f"seo_meta_{RUN_TS}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    tprint("\n=== DONE ===")
    tprint(f"Pages: {len(results['pages'])}/{len(PAGES)}")
    tprint(f"Regions: {len(results['regions'])}/{len(REGIONS)}")
    tprint(f"Categories: {len(results['categories'])}/{len(CATEGORIES)}")
    tprint(f"Output: {out}")


if __name__ == "__main__":
    main()
