#!/usr/bin/env python3
"""Pillar Article Generator — GPT-5.5 deep content creation.

Generates 30+ long-form SEO articles (2000+ words each):
  - Top lists per category per region
  - Ultimate guides per region
  - Seasonal guides
  - Thematic deep-dives (culture, food, nature, craft)
  - Comparison/versus articles

Each article goes through 3 passes:
  Pass 1: Research outline + key facts
  Pass 2: Full draft with storytelling, local knowledge, sensory details
  Pass 3: SEO optimization (headings, keywords, internal links, FAQ)

Output: agent/data/articles/ — Markdown files, review queue.
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
OUTPUT_DIR = AGENT_DIR / "data" / "articles"
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
_stats = {"done": 0, "fail": 0}
RUN_TS = datetime.now().strftime("%Y%m%d_%H%M%S")


def tprint(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def llm_call(prompt, system="", retries=2, max_tokens=4000):
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    for attempt in range(retries + 1):
        try:
            r = client.chat.completions.create(
                model=LLM_MODEL, messages=msgs,
                temperature=0.7, max_tokens=max_tokens
            )
            return r.choices[0].message.content.strip()
        except Exception as e:
            if attempt < retries:
                time.sleep(5 * (attempt + 1))
            else:
                raise


SYSTEM = """Bạn là nhà báo du lịch chuyên viết về miền Tây Nam Bộ (Vĩnh Long, Bến Tre, Trà Vinh).
Viết TIẾNG VIỆT, giọng ấm áp, sinh động, giàu cảm xúc nhưng chính xác.
Sử dụng hình ảnh ngũ quan (mùi, vị, âm, xúc giác), kể chuyện có chiều sâu văn hóa.
Bài viết phải có giá trị thực tế cho du khách: địa chỉ, mẹo, giá tham khảo, thời gian.
Tối ưu SEO: heading rõ ràng, keyword tự nhiên, internal link suggestions.
Website: vinhlong360.vn — MXH du lịch cộng đồng."""

ARTICLES = [
    # Top lists by region
    {"id": "top-mon-an-vinh-long", "title": "Top 25 Món Ăn Vĩnh Long Phải Thử — Từ Quán Vỉa Hè Đến Nhà Hàng", "type": "top-list", "region": "Vĩnh Long", "category": "ẩm thực", "target_words": 2500},
    {"id": "top-mon-an-ben-tre", "title": "Top 20 Món Ngon Bến Tre — Xứ Dừa Ẩm Thực Ký", "type": "top-list", "region": "Bến Tre", "category": "ẩm thực", "target_words": 2500},
    {"id": "top-mon-an-tra-vinh", "title": "Top 20 Món Ăn Trà Vinh — Bún Nước Lèo và Hơn Thế Nữa", "type": "top-list", "region": "Trà Vinh", "category": "ẩm thực", "target_words": 2500},
    {"id": "top-diem-den-vinh-long", "title": "15 Điểm Đến Vĩnh Long Không Thể Bỏ Lỡ 2025", "type": "top-list", "region": "Vĩnh Long", "category": "điểm đến", "target_words": 2000},
    {"id": "top-diem-den-ben-tre", "title": "15 Điểm Tham Quan Bến Tre — Từ Cồn Phụng Đến Sân Chim Vàm Hồ", "type": "top-list", "region": "Bến Tre", "category": "điểm đến", "target_words": 2000},
    {"id": "top-diem-den-tra-vinh", "title": "15 Điểm Du Lịch Trà Vinh — Chùa Khmer, Ao Bà Om và Cồn Hô", "type": "top-list", "region": "Trà Vinh", "category": "điểm đến", "target_words": 2000},

    # Ultimate guides
    {"id": "guide-vinh-long-2025", "title": "Cẩm Nang Du Lịch Vĩnh Long 2025 — Từ A Đến Z", "type": "guide", "region": "Vĩnh Long", "category": "tổng hợp", "target_words": 3000},
    {"id": "guide-ben-tre-2025", "title": "Cẩm Nang Du Lịch Bến Tre 2025 — Xứ Dừa Toàn Tập", "type": "guide", "region": "Bến Tre", "category": "tổng hợp", "target_words": 3000},
    {"id": "guide-tra-vinh-2025", "title": "Cẩm Nang Du Lịch Trà Vinh 2025 — Khmer, Dừa Sáp & Hơn Thế", "type": "guide", "region": "Trà Vinh", "category": "tổng hợp", "target_words": 3000},

    # Seasonal
    {"id": "mua-trai-cay-mien-tay", "title": "Lịch Mùa Trái Cây Miền Tây — Tháng Nào Ăn Gì?", "type": "seasonal", "region": "3 vùng", "category": "trái cây", "target_words": 2000},
    {"id": "le-hoi-mien-tay-theo-thang", "title": "Lịch Lễ Hội Miền Tây 2025-2026 — Đầy Đủ 12 Tháng", "type": "seasonal", "region": "3 vùng", "category": "lễ hội", "target_words": 2500},
    {"id": "du-lich-mien-tay-mua-nuoc-noi", "title": "Du Lịch Miền Tây Mùa Nước Nổi — Trải Nghiệm Độc Đáo", "type": "seasonal", "region": "3 vùng", "category": "mùa vụ", "target_words": 2000},
    {"id": "tet-mien-tay", "title": "Tết Miền Tây — Phong Tục, Ẩm Thực và Nơi Đi Chơi", "type": "seasonal", "region": "3 vùng", "category": "Tết", "target_words": 2500},

    # Thematic deep-dives
    {"id": "van-hoa-khmer-tra-vinh", "title": "Văn Hóa Khmer Trà Vinh — Chùa, Lễ Hội và Nghệ Thuật Ngàn Năm", "type": "deep-dive", "region": "Trà Vinh", "category": "văn hóa", "target_words": 3000},
    {"id": "lang-nghe-mien-tay", "title": "Làng Nghề Miền Tây — Gốm, Dệt, Kẹo Dừa và Câu Chuyện Nghệ Nhân", "type": "deep-dive", "region": "3 vùng", "category": "làng nghề", "target_words": 2500},
    {"id": "ocop-mien-tay", "title": "Sản Phẩm OCOP Miền Tây — Từ Mật Hoa Dừa Đến Khoai Lang Tím", "type": "deep-dive", "region": "3 vùng", "category": "OCOP", "target_words": 2500},
    {"id": "song-nuoc-mien-tay", "title": "Sống Nước Miền Tây — Cuộc Sống Trên Sông và Những Cù Lao", "type": "deep-dive", "region": "3 vùng", "category": "thiên nhiên", "target_words": 2500},
    {"id": "homestay-mien-tay", "title": "Homestay Miền Tây — Ngủ Nhà Vườn, Ăn Cơm Quê, Sống Chậm", "type": "deep-dive", "region": "3 vùng", "category": "lưu trú", "target_words": 2000},

    # Itinerary articles
    {"id": "lich-trinh-2n1d-vinh-long", "title": "Lịch Trình 2 Ngày 1 Đêm Vĩnh Long — Vườn Trái Cây & Gốm Mang Thít", "type": "itinerary", "region": "Vĩnh Long", "category": "lịch trình", "target_words": 2000},
    {"id": "lich-trinh-2n1d-ben-tre", "title": "Lịch Trình 2 Ngày 1 Đêm Bến Tre — Dừa, Cồn và Kẹo", "type": "itinerary", "region": "Bến Tre", "category": "lịch trình", "target_words": 2000},
    {"id": "lich-trinh-3n2d-3-vung", "title": "Lịch Trình 3 Ngày 2 Đêm Vĩnh Long–Bến Tre–Trà Vinh", "type": "itinerary", "region": "3 vùng", "category": "lịch trình", "target_words": 2500},
    {"id": "lich-trinh-trai-cay", "title": "Vòng Trái Cây Miền Tây — Lịch Trình 1 Ngày Ăn Sập Vườn", "type": "itinerary", "region": "3 vùng", "category": "lịch trình", "target_words": 1800},
    {"id": "lich-trinh-chua-khmer", "title": "Tour Chùa Khmer Trà Vinh — Hành Trình Tâm Linh 2 Ngày", "type": "itinerary", "region": "Trà Vinh", "category": "lịch trình", "target_words": 2000},

    # Comparison
    {"id": "vinh-long-vs-ben-tre", "title": "Vĩnh Long vs Bến Tre — Nên Đi Đâu Trước?", "type": "comparison", "region": "VL vs BT", "category": "so sánh", "target_words": 2000},
    {"id": "mien-tay-cho-gia-dinh", "title": "Du Lịch Miền Tây Cho Gia Đình Có Con Nhỏ — Mẹo Hay & Lịch Trình", "type": "guide", "region": "3 vùng", "category": "gia đình", "target_words": 2000},

    # Practical
    {"id": "di-chuyen-mien-tay", "title": "Cách Di Chuyển Ở Miền Tây — Xe, Thuyền, Grab & Mẹo Tiết Kiệm", "type": "practical", "region": "3 vùng", "category": "di chuyển", "target_words": 1800},
    {"id": "chi-phi-du-lich-mien-tay", "title": "Chi Phí Du Lịch Miền Tây 2025 — Budget Từ 500K Đến 5 Triệu", "type": "practical", "region": "3 vùng", "category": "chi phí", "target_words": 2000},
    {"id": "meo-du-lich-mien-tay", "title": "30 Mẹo Du Lịch Miền Tây Từ Dân Bản Địa", "type": "practical", "region": "3 vùng", "category": "mẹo", "target_words": 2000},
]


def generate_article(article):
    aid = article["id"]
    tprint(f"  📝 {aid} — Pass 1: outline...")

    # Pass 1: Research outline
    outline_prompt = f"""Tạo outline chi tiết cho bài viết SEO:
Tiêu đề: {article['title']}
Loại: {article['type']}
Vùng: {article['region']}
Chủ đề: {article['category']}
Độ dài mục tiêu: {article['target_words']} từ

Trả về outline dạng Markdown:
- H2 sections (5-8 mục chính)
- H3 sub-sections nếu cần
- Key facts/data points cho mỗi section
- Internal link opportunities (→ /route)
- Target keywords cho mỗi section
"""
    try:
        outline = llm_call(outline_prompt, SYSTEM, max_tokens=2000)
    except Exception as e:
        tprint(f"  ✗ {aid} — outline fail: {e}")
        _stats["fail"] += 1
        return None

    tprint(f"  📝 {aid} — Pass 2: full draft...")

    # Pass 2: Full article
    draft_prompt = f"""Viết bài viết đầy đủ theo outline sau. Bài cho website vinhlong360.vn.

Tiêu đề: {article['title']}
Độ dài: {article['target_words']}+ từ
Giọng văn: Ấm áp, sinh động, giàu hình ảnh ngũ quan, am hiểu bản địa
Format: Markdown (H2, H3, bullet points, bold cho key info)

OUTLINE:
{outline}

YÊU CẦU:
- Mở bài hook mạnh (1 đoạn gợi cảm xúc)
- Mỗi section có ít nhất 1 chi tiết cụ thể (địa chỉ, giá, mẹo)
- Xen kẽ câu chuyện/anecdote với thông tin thực tế
- Kết bài có CTA (gợi ý action tiếp theo)
- Thêm 3-5 FAQ ở cuối (cho schema markup)
- Không nhồi keyword, viết tự nhiên
"""
    try:
        draft = llm_call(draft_prompt, SYSTEM, max_tokens=4000)
    except Exception as e:
        tprint(f"  ✗ {aid} — draft fail: {e}")
        _stats["fail"] += 1
        return None

    tprint(f"  📝 {aid} — Pass 3: SEO polish...")

    # Pass 3: SEO optimization metadata
    seo_prompt = f"""Phân tích bài viết sau và tạo SEO metadata:

TITLE: {article['title']}
ARTICLE (trích):
{draft[:2000]}...

Trả về JSON (CHỈ JSON):
{{
  "meta_title": "SEO title (50-60 chars)",
  "meta_description": "Meta desc (150-160 chars)",
  "primary_keyword": "từ khóa chính",
  "secondary_keywords": ["kw2", "kw3", "kw4"],
  "internal_links": ["{{'anchor': 'text', 'target': '/route'}}"],
  "faq_schema": [{{"q": "câu hỏi", "a": "trả lời ngắn"}}],
  "readability_score": "1-10",
  "word_count_estimate": 0,
  "improvement_suggestions": ["gợi ý 1", "gợi ý 2"]
}}"""
    try:
        seo_raw = llm_call(seo_prompt, SYSTEM, max_tokens=1500)
        seo_meta = json.loads(re.sub(r"^```(?:json)?|```$", "", seo_raw.strip(), flags=re.MULTILINE).strip()) if seo_raw else {}
    except Exception:
        seo_meta = {}

    # Save article
    slug = aid
    md_path = OUTPUT_DIR / f"{slug}.md"
    frontmatter = f"""---
title: "{article['title']}"
type: {article['type']}
region: {article['region']}
category: {article['category']}
generated: {datetime.now(timezone.utc).isoformat()}
model: {LLM_MODEL}
seo: {json.dumps(seo_meta, ensure_ascii=False)}
---

"""
    with _lock:
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(frontmatter + draft)

    _stats["done"] += 1
    tprint(f"  ✓ {aid} — saved ({md_path.name})")
    return {"id": aid, "file": str(md_path)}


def main():
    tprint("=== Pillar Article Generator ===")
    tprint(f"Total articles: {len(ARTICLES)}")
    tprint(f"Model: {LLM_MODEL}")
    tprint(f"Output: {OUTPUT_DIR}")
    tprint("")

    results = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(generate_article, a): a for a in ARTICLES}
        for fut in as_completed(futures):
            r = fut.result()
            if r:
                results.append(r)
            if (_stats["done"] + _stats["fail"]) % 5 == 0:
                tprint(f"  --- Progress: {_stats['done']} done, {_stats['fail']} fail / {len(ARTICLES)} ---")

    tprint(f"\n=== DONE: {_stats['done']} articles, {_stats['fail']} failed ===")

    manifest = OUTPUT_DIR / f"manifest_{RUN_TS}.json"
    with open(manifest, "w", encoding="utf-8") as f:
        json.dump({"articles": results, "total": len(ARTICLES), "done": _stats["done"], "fail": _stats["fail"]}, f, ensure_ascii=False, indent=2)
    tprint(f"Manifest: {manifest}")


if __name__ == "__main__":
    main()
