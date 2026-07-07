#!/usr/bin/env python3
"""MEGA LLM Burn — Pure GPT-5.5 content generation (NO web search).

Reads existing entities + mega_research data → feeds to GPT-5.5 → generates
rich content. NO DuckDuckGo dependency = no rate limiting = MAX token burn.

Modes:
  --mode seo-all       : SEO content 500+ từ cho MỌI entity
  --mode narratives    : Bài viết cảm xúc 800+ từ cho top entities
  --mode itineraries   : 50 lịch trình chi tiết (1-7 ngày)
  --mode qa            : 500+ câu hỏi-đáp du lịch
  --mode social        : Social media posts cho mọi entity
  --mode descriptions  : Mô tả chi tiết cho mọi entity thiếu
  --mode tips          : Mẹo du lịch theo chủ đề
  --mode stories       : Câu chuyện địa phương
  --mode all           : TẤT CẢ modes

Usage:
  python -u agent/scripts/mega_llm_burn.py --mode all --workers 8
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import time
import warnings
warnings.filterwarnings("ignore", message=".*renamed.*ddgs.*")
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = AGENT_DIR.parent
OUTPUT_DIR = AGENT_DIR / "data" / "mega_research" / "llm_burn"
DATA_JSON = PROJECT_DIR / "web" / "data.json"

sys.path.insert(0, str(AGENT_DIR))
sys.path.insert(0, str(AGENT_DIR / "scripts"))
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_DIR / ".env")
except Exception:
    pass

from mega_research import (LLM, read_jsonl, append_jsonl, load_entities,
                           log, utc, PROVINCE, _cfg_io)

SYS_WRITER = """Bạn là nhà văn du lịch chuyên nghiệp, am hiểu sâu về miền Tây Nam Bộ Việt Nam.
Viết nội dung SEO-friendly, giàu cảm xúc, chính xác về văn hóa.
Sử dụng tiếng Việt tự nhiên, không sáo rỗng. Đan xen chi tiết cụ thể.
KHÔNG bịa thông tin. Nếu không chắc, nói rõ."""

SYS_QA = """Bạn là hướng dẫn viên du lịch kỳ cựu ở miền Tây Nam Bộ.
Trả lời câu hỏi du lịch một cách thực tế, hữu ích, chi tiết.
Chỉ trả lời dựa trên kiến thức thực tế. Thêm mẹo cá nhân khi phù hợp."""

SYS_SOCIAL = """Bạn là social media content creator cho du lịch miền Tây.
Viết caption hấp dẫn, dùng emoji phù hợp, có hashtag.
Tone: thân thiện, gần gũi, gợi cảm xúc muốn đi du lịch."""


def _load_research_context(entity_id: str) -> str:
    """Load any existing research for an entity from mega_research JSONL files."""
    ctx_parts = []
    for jf in (AGENT_DIR / "data" / "mega_research").rglob("*.jsonl"):
        if "llm_burn" in str(jf) or "deep_dive" in str(jf):
            continue
        for rec in read_jsonl(jf):
            if rec.get("entity_id") == entity_id or rec.get("id") == entity_id:
                for k, v in rec.items():
                    if k in ("ts", "sources", "n_sources", "entity_id", "entity_name"):
                        continue
                    if isinstance(v, str) and len(v) > 50:
                        ctx_parts.append(f"{k}: {v[:800]}")
                    elif isinstance(v, dict):
                        ctx_parts.append(f"{k}: {json.dumps(v, ensure_ascii=False)[:600]}")
                break
    return "\n".join(ctx_parts[:10]) if ctx_parts else ""


# ═══════════════════════════════════════════════════════════════════════════════
# MODE: seo-all — SEO content cho mọi entity
# ═══════════════════════════════════════════════════════════════════════════════

def seo_all(llm: LLM, workers: int = 8):
    log("═══ LLM BURN: SEO CONTENT ═══")
    f = OUTPUT_DIR / "seo_content.jsonl"
    done = {r.get("entity_id") for r in read_jsonl(f)}
    ents = [e for e in load_entities() if e["id"] not in done]
    log(f"  {len(ents)} entities for SEO content")

    def do(e):
        prov = PROVINCE.get(e.get("area", ""), "ĐBSCL")
        n = e["name"]
        t = e.get("type", "place")
        ctx = _load_research_context(e["id"])
        extra = f"\n[Nghiên cứu có sẵn]:\n{ctx}" if ctx else ""
        r = llm.ask_json(sys=SYS_WRITER, user=f"""Viết nội dung SEO cho: "{n}" (loại: {t}, {prov})
Summary hiện có: {e.get('summary','')[:500]}
{extra}

JSON (viết đầy đủ tiếng Việt, KHÔNG viết tắt):
{{
  "entity_id": "{e['id']}",
  "name": "{n}",
  "seo_title": "tiêu đề SEO 60-70 ký tự, có từ khóa chính",
  "meta_description": "mô tả SEO 150-160 ký tự, có CTA",
  "h1": "tiêu đề chính hấp dẫn",
  "intro": "đoạn mở đầu 100-150 từ, hook reader",
  "body_sections": [
    {{"h2": "tiêu đề mục", "content": "150-200 từ mỗi mục, chi tiết, có số liệu"}},
    {{"h2": "tiêu đề mục 2", "content": "150-200 từ"}},
    {{"h2": "tiêu đề mục 3", "content": "150-200 từ"}},
    {{"h2": "tiêu đề mục 4", "content": "150-200 từ"}}
  ],
  "conclusion": "đoạn kết 100 từ, có CTA nhẹ",
  "faq": [
    {{"q": "câu hỏi thường gặp 1", "a": "trả lời 50-80 từ"}},
    {{"q": "câu hỏi thường gặp 2", "a": "trả lời 50-80 từ"}},
    {{"q": "câu hỏi thường gặp 3", "a": "trả lời 50-80 từ"}}
  ],
  "keywords": ["từ khóa chính", "từ khóa phụ 1", "từ khóa phụ 2", "..."],
  "internal_links": ["entity liên quan 1", "entity liên quan 2"],
  "schema_type": "TouristAttraction|Restaurant|LocalBusiness|Event|Product"
}}""", temp=0.3, max_tok=6000)
        if r:
            r["entity_id"] = e["id"]; r["area"] = e.get("area", ""); r["type"] = t; r["ts"] = utc()
            append_jsonl(f, r)
            log(f"  ✓ SEO: {n}")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(do, e) for e in ents]
        for i, fut in enumerate(as_completed(futs)):
            try: fut.result()
            except Exception as ex: log(f"  ERR: {ex}")
            if (i+1) % 50 == 0:
                log(f"  ... SEO progress: {i+1}/{len(ents)} | {llm.info()}")


# ═══════════════════════════════════════════════════════════════════════════════
# MODE: narratives — Bài viết cảm xúc cho top entities
# ═══════════════════════════════════════════════════════════════════════════════

def narratives(llm: LLM, workers: int = 8):
    log("═══ LLM BURN: EMOTIONAL NARRATIVES ═══")
    f = OUTPUT_DIR / "narratives.jsonl"
    done = {r.get("entity_id") for r in read_jsonl(f)}
    ents = [e for e in load_entities()
            if e["id"] not in done and e.get("type") in
            ("history", "dish", "drink", "craft_village", "place", "attraction",
             "person", "event", "nature", "accommodation")]
    log(f"  {len(ents)} entities for narratives")

    def do(e):
        prov = PROVINCE.get(e.get("area", ""), "ĐBSCL")
        n = e["name"]
        ctx = _load_research_context(e["id"])
        extra = f"\n[Nghiên cứu]:\n{ctx}" if ctx else ""
        r = llm.ask_json(sys=SYS_WRITER, user=f"""Viết bài viết cảm xúc về "{n}" ({e.get('type','')}, {prov})
Summary: {e.get('summary','')[:500]}
{extra}

Viết bài 800-1200 từ, giàu cảm xúc, kể chuyện hấp dẫn, SEO-friendly.

JSON:
{{
  "entity_id": "{e['id']}",
  "title": "tiêu đề bài viết hấp dẫn",
  "subtitle": "phụ đề gợi tò mò",
  "hero_caption": "mô tả ảnh đại diện lý tưởng",
  "paragraphs": [
    "Đoạn 1: mở đầu hook, 150-200 từ, kéo người đọc vào",
    "Đoạn 2: bối cảnh lịch sử/văn hóa, 150-200 từ",
    "Đoạn 3: trải nghiệm cá nhân/gợi ý chi tiết, 150-200 từ",
    "Đoạn 4: chi tiết đặc biệt ít ai biết, 150-200 từ",
    "Đoạn 5: kết nối cảm xúc + CTA, 100-150 từ"
  ],
  "pull_quote": "câu trích dẫn nổi bật từ bài",
  "tags": ["tag1", "tag2", "tag3"],
  "mood": "nostalgic|adventurous|peaceful|joyful|spiritual|romantic",
  "reading_time_min": 5,
  "related_entities": ["entity liên quan"]
}}""", temp=0.5, max_tok=8000)
        if r:
            r["entity_id"] = e["id"]; r["area"] = e.get("area", ""); r["ts"] = utc()
            append_jsonl(f, r)
            log(f"  ✓ Narrative: {n}")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(do, e) for e in ents]
        for i, fut in enumerate(as_completed(futs)):
            try: fut.result()
            except Exception as ex: log(f"  ERR: {ex}")
            if (i+1) % 50 == 0:
                log(f"  ... Narrative progress: {i+1}/{len(ents)} | {llm.info()}")


# ═══════════════════════════════════════════════════════════════════════════════
# MODE: itineraries — 50 lịch trình chi tiết
# ═══════════════════════════════════════════════════════════════════════════════

ITINERARY_SPECS = [
    ("vl_1day_classic", "1 ngày", "Vĩnh Long", "kinh điển", "mọi người"),
    ("vl_1day_food", "1 ngày", "Vĩnh Long", "ẩm thực", "foodie"),
    ("vl_1day_history", "1 ngày", "Vĩnh Long", "lịch sử văn hóa", "yêu lịch sử"),
    ("vl_2day_full", "2 ngày 1 đêm", "Vĩnh Long", "trọn vẹn", "cặp đôi"),
    ("vl_2day_family", "2 ngày 1 đêm", "Vĩnh Long", "gia đình vui", "gia đình có trẻ"),
    ("vl_3day_deep", "3 ngày 2 đêm", "Vĩnh Long", "khám phá sâu", "backpacker"),
    ("bt_1day_coconut", "1 ngày", "Bến Tre", "xứ dừa", "mọi người"),
    ("bt_1day_food", "1 ngày", "Bến Tre", "ẩm thực dừa", "foodie"),
    ("bt_2day_eco", "2 ngày 1 đêm", "Bến Tre", "sinh thái", "yêu thiên nhiên"),
    ("bt_2day_craft", "2 ngày 1 đêm", "Bến Tre", "làng nghề", "nghệ nhân"),
    ("bt_3day_full", "3 ngày 2 đêm", "Bến Tre", "trọn vẹn", "nhóm bạn"),
    ("tv_1day_khmer", "1 ngày", "Trà Vinh", "văn hóa Khmer", "yêu văn hóa"),
    ("tv_1day_temple", "1 ngày", "Trà Vinh", "chùa chiền", "tâm linh"),
    ("tv_2day_culture", "2 ngày 1 đêm", "Trà Vinh", "đa văn hóa", "nhiếp ảnh"),
    ("tv_2day_nature", "2 ngày 1 đêm", "Trà Vinh", "biển rừng", "phiêu lưu"),
    ("tv_3day_deep", "3 ngày 2 đêm", "Trà Vinh", "khám phá", "solo"),
    ("combo_vl_bt_2day", "2 ngày 1 đêm", "Vĩnh Long + Bến Tre", "kết hợp", "cặp đôi"),
    ("combo_vl_bt_3day", "3 ngày 2 đêm", "Vĩnh Long + Bến Tre", "trọn vẹn miền Tây", "gia đình"),
    ("combo_bt_tv_2day", "2 ngày 1 đêm", "Bến Tre + Trà Vinh", "dừa + Khmer", "backpacker"),
    ("combo_bt_tv_3day", "3 ngày 2 đêm", "Bến Tre + Trà Vinh", "đa dạng", "nhóm bạn"),
    ("combo_all_3day", "3 ngày 2 đêm", "3 tỉnh", "panorama miền Tây", "mọi người"),
    ("combo_all_5day", "5 ngày 4 đêm", "3 tỉnh", "deep dive", "du khách nước ngoài"),
    ("combo_all_7day", "7 ngày 6 đêm", "3 tỉnh", "trải nghiệm toàn diện", "digital nomad"),
    ("weekend_vl", "2 ngày (cuối tuần)", "Vĩnh Long", "getaway", "dân Sài Gòn"),
    ("weekend_bt", "2 ngày (cuối tuần)", "Bến Tre", "getaway", "dân Sài Gòn"),
    ("weekend_tv", "2 ngày (cuối tuần)", "Trà Vinh", "getaway", "dân Sài Gòn"),
    ("honeymoon_3day", "3 ngày 2 đêm", "Vĩnh Long + Bến Tre", "lãng mạn", "cặp đôi mới cưới"),
    ("budget_3day", "3 ngày 2 đêm", "3 tỉnh", "tiết kiệm <1tr", "sinh viên"),
    ("luxury_3day", "3 ngày 2 đêm", "Vĩnh Long + Bến Tre", "cao cấp", "thượng lưu"),
    ("photo_2day", "2 ngày 1 đêm", "3 tỉnh", "chụp ảnh", "nhiếp ảnh gia"),
    ("mua_nuoc_noi", "2 ngày 1 đêm", "Vĩnh Long", "mùa nước nổi", "trải nghiệm mùa"),
    ("tet_3day", "3 ngày", "3 tỉnh", "Tết Nguyên Đán", "về quê ăn Tết"),
    ("food_tour_3day", "3 ngày 2 đêm", "3 tỉnh", "food tour", "foodie chuyên nghiệp"),
    ("craft_2day", "2 ngày 1 đêm", "Vĩnh Long + Bến Tre", "làng nghề", "yêu handcraft"),
    ("spiritual_2day", "2 ngày 1 đêm", "Trà Vinh", "tâm linh thiền", "tìm bình yên"),
    ("kids_2day", "2 ngày 1 đêm", "Bến Tre", "thiếu nhi vui", "gia đình trẻ con 3-10"),
    ("senior_2day", "2 ngày 1 đêm", "Vĩnh Long", "thư thả", "người lớn tuổi"),
    ("adventure_3day", "3 ngày 2 đêm", "3 tỉnh", "mạo hiểm", "thích thử thách"),
    ("cycling_3day", "3 ngày 2 đêm", "Vĩnh Long + Bến Tre", "đạp xe", "yêu xe đạp"),
    ("cooking_class", "1 ngày", "Vĩnh Long", "học nấu ăn", "du khách nước ngoài"),
    ("market_tour", "1 ngày", "3 tỉnh", "chợ dân sinh", "foodie"),
    ("boat_tour_2day", "2 ngày 1 đêm", "Vĩnh Long + Bến Tre", "sông nước", "yêu sông"),
    ("night_life", "1 đêm", "Vĩnh Long", "đêm miền Tây", "trẻ năng động"),
    ("volunteer_3day", "3 ngày 2 đêm", "Trà Vinh", "tình nguyện Khmer", "sinh viên"),
    ("art_culture_2day", "2 ngày 1 đêm", "3 tỉnh", "nghệ thuật đờn ca tài tử", "yêu nghệ thuật"),
    ("rainy_season_2day", "2 ngày 1 đêm", "3 tỉnh", "mùa mưa", "du lịch mùa mưa"),
    ("sunrise_sunset", "1 ngày", "3 tỉnh", "bình minh hoàng hôn", "nhiếp ảnh"),
    ("fruit_season_2day", "2 ngày 1 đêm", "Vĩnh Long + Bến Tre", "mùa trái cây", "tháng 5-7"),
    ("heritage_walk", "1 ngày", "Trà Vinh", "di sản đi bộ", "yêu kiến trúc"),
    ("solo_female_3day", "3 ngày 2 đêm", "3 tỉnh", "an toàn", "phụ nữ đi một mình"),
]


def itineraries(llm: LLM, workers: int = 8):
    log("═══ LLM BURN: ITINERARIES ═══")
    f = OUTPUT_DIR / "itineraries.jsonl"
    done = {r.get("key") for r in read_jsonl(f)}
    specs = [(k, *rest) for k, *rest in ITINERARY_SPECS if k not in done]
    log(f"  {len(specs)} itineraries to generate")

    ents = load_entities()
    ent_summary = {}
    for e in ents:
        area = PROVINCE.get(e.get("area", ""), "")
        ent_summary.setdefault(area, []).append(f"{e['name']} ({e.get('type','')})")

    areas_text = "\n".join(f"[{a}]: {', '.join(es[:80])}" for a, es in ent_summary.items() if a)

    def do(spec):
        key, duration, region, theme, audience = spec
        r = llm.ask_json(sys=SYS_WRITER, user=f"""Tạo lịch trình du lịch CHI TIẾT:
- Thời gian: {duration}
- Khu vực: {region}
- Chủ đề: {theme}
- Đối tượng: {audience}

[ENTITIES CÓ SẴN — hãy sử dụng tên thật]:
{areas_text}

JSON (chi tiết từng giờ, có giá, có mẹo):
{{
  "key": "{key}",
  "title": "tên lịch trình hấp dẫn",
  "duration": "{duration}",
  "region": "{region}",
  "theme": "{theme}",
  "audience": "{audience}",
  "summary": "200 từ tóm tắt hấp dẫn",
  "budget": {{"min": null, "max": null, "currency": "VND", "includes": "ăn uống, di chuyển, vé"}},
  "best_season": "tháng nào tốt nhất",
  "packing_tips": ["mang gì"],
  "days": [
    {{
      "day": 1,
      "title": "tiêu đề ngày",
      "morning": {{
        "time": "06:00-11:30",
        "activities": [
          {{"time": "06:00", "place": "tên entity thật", "activity": "chi tiết", "duration_min": 60, "tips": "mẹo", "cost": null}}
        ]
      }},
      "lunch": {{"time": "11:30-13:00", "place": "quán/entity thật", "dishes": ["món nên thử"], "cost": null}},
      "afternoon": {{
        "time": "13:00-17:00",
        "activities": [...]
      }},
      "dinner": {{"time": "17:30-19:00", "place": "...", "dishes": [], "cost": null}},
      "evening": {{"time": "19:00-21:00", "activity": "hoạt động tối", "tips": "..."}},
      "accommodation": {{"name": "entity thật", "type": "homestay|khách sạn", "price_range": null}}
    }}
  ],
  "transport": {{"from_hcm": "cách đi từ SG", "local": "di chuyển nội vùng", "tips": "mẹo"}},
  "alternative_stops": ["nơi thay thế nếu hết thời gian"],
  "warnings": ["lưu ý quan trọng"],
  "seo_content": "400+ từ mô tả SEO cho trang lịch trình"
}}""", temp=0.4, max_tok=10000)
        if r:
            r["key"] = key; r["ts"] = utc()
            append_jsonl(f, r)
            log(f"  ✓ Itinerary: {key}")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for i, fut in enumerate(as_completed([pool.submit(do, s) for s in specs])):
            try: fut.result()
            except Exception as ex: log(f"  ERR: {ex}")


# ═══════════════════════════════════════════════════════════════════════════════
# MODE: qa — 500+ câu hỏi-đáp
# ═══════════════════════════════════════════════════════════════════════════════

QA_CATEGORIES = [
    ("general_vl", "Vĩnh Long tổng quan du lịch"),
    ("general_bt", "Bến Tre tổng quan du lịch"),
    ("general_tv", "Trà Vinh tổng quan du lịch"),
    ("transport_vl", "đi lại di chuyển Vĩnh Long"),
    ("transport_bt", "đi lại di chuyển Bến Tre"),
    ("transport_tv", "đi lại di chuyển Trà Vinh"),
    ("food_vl", "ẩm thực đặc sản Vĩnh Long"),
    ("food_bt", "ẩm thực đặc sản Bến Tre"),
    ("food_tv", "ẩm thực đặc sản Trà Vinh"),
    ("accommodation_vl", "khách sạn homestay Vĩnh Long"),
    ("accommodation_bt", "khách sạn homestay Bến Tre"),
    ("accommodation_tv", "khách sạn homestay Trà Vinh"),
    ("culture_khmer", "văn hóa Khmer Trà Vinh"),
    ("culture_mien_tay", "văn hóa miền Tây sông nước"),
    ("heritage", "di tích lịch sử 3 tỉnh"),
    ("nature", "thiên nhiên sinh thái"),
    ("shopping", "mua sắm quà tặng đặc sản"),
    ("budget", "chi phí ngân sách du lịch"),
    ("safety", "an toàn sức khỏe lưu ý"),
    ("best_time", "thời điểm tốt nhất đi du lịch"),
    ("family", "du lịch gia đình trẻ em"),
    ("couple", "du lịch cặp đôi lãng mạn"),
    ("solo", "du lịch một mình solo"),
    ("photo", "chụp ảnh đẹp check-in"),
    ("festival", "lễ hội sự kiện"),
    ("craft", "làng nghề truyền thống"),
    ("fruit", "vườn trái cây"),
    ("boat", "sông nước chợ nổi"),
    ("night", "hoạt động ban đêm"),
    ("foreigner", "du khách nước ngoài tips"),
]


def qa_generate(llm: LLM, workers: int = 8):
    log("═══ LLM BURN: Q&A GENERATION ═══")
    f = OUTPUT_DIR / "qa.jsonl"
    done = {r.get("category") for r in read_jsonl(f)}
    cats = [(k, q) for k, q in QA_CATEGORIES if k not in done]
    log(f"  {len(cats)} Q&A categories")

    def do(item):
        cat, topic = item
        r = llm.ask_json(sys=SYS_QA, user=f"""Tạo 20 câu hỏi-đáp về: "{topic}"
Khu vực: Vĩnh Long, Bến Tre, Trà Vinh

Câu hỏi phải là câu hỏi THẬT mà du khách hay hỏi (Google, TripAdvisor, forum...).
Trả lời phải chi tiết 80-150 từ mỗi câu, có số liệu cụ thể.

JSON:
{{
  "category": "{cat}",
  "topic": "{topic}",
  "qa_pairs": [
    {{
      "q": "câu hỏi tự nhiên, cụ thể",
      "a": "câu trả lời chi tiết 80-150 từ, có số liệu, có mẹo thực tế",
      "tags": ["tag1", "tag2"],
      "difficulty": "basic|intermediate|expert",
      "related_entities": ["entity name liên quan"]
    }}
  ]
}}""", temp=0.4, max_tok=12000)
        if r:
            r["category"] = cat; r["ts"] = utc()
            n_qa = len(r.get("qa_pairs", []))
            append_jsonl(f, r)
            log(f"  ✓ Q&A: {cat} ({n_qa} pairs)")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for fut in as_completed([pool.submit(do, c) for c in cats]):
            try: fut.result()
            except Exception as ex: log(f"  ERR: {ex}")


# ═══════════════════════════════════════════════════════════════════════════════
# MODE: social — Social media content
# ═══════════════════════════════════════════════════════════════════════════════

def social_content(llm: LLM, workers: int = 8):
    log("═══ LLM BURN: SOCIAL MEDIA CONTENT ═══")
    f = OUTPUT_DIR / "social.jsonl"
    done = {r.get("entity_id") for r in read_jsonl(f)}
    ents = [e for e in load_entities() if e["id"] not in done
            and e.get("type") in ("dish", "drink", "history", "place", "attraction",
                                  "craft_village", "event", "nature", "accommodation")]
    log(f"  {len(ents)} entities for social content")

    def do(e):
        prov = PROVINCE.get(e.get("area", ""), "ĐBSCL")
        n = e["name"]
        r = llm.ask_json(sys=SYS_SOCIAL, user=f"""Tạo social media content cho: "{n}" ({e.get('type','')}, {prov})
Summary: {e.get('summary','')[:400]}

JSON:
{{
  "entity_id": "{e['id']}",
  "name": "{n}",
  "instagram": {{
    "caption": "caption 150-300 từ, storytelling, có emoji phù hợp",
    "hashtags": ["#vinhlong360", "#mienTay", "...thêm 15-20 hashtag"],
    "best_time_post": "giờ tốt nhất đăng",
    "photo_suggestion": "mô tả ảnh lý tưởng đi kèm"
  }},
  "facebook": {{
    "post": "bài post 200-400 từ, engaging, có CTA",
    "audience": "đối tượng mục tiêu"
  }},
  "tiktok": {{
    "script": "kịch bản video 30-60 giây",
    "hook": "câu mở đầu hook 3 giây đầu",
    "music_mood": "nhạc nền gợi ý",
    "trending_sounds": ["âm thanh trending phù hợp"]
  }},
  "zalo": {{
    "oa_post": "bài viết OA 100-200 từ",
    "community_post": "bài đăng cộng đồng 50-100 từ"
  }},
  "google_review": {{
    "sample_review": "mẫu review 5 sao 50-100 từ",
    "key_points": ["điểm nổi bật nên nhắc"]
  }}
}}""", temp=0.5, max_tok=6000)
        if r:
            r["entity_id"] = e["id"]; r["area"] = e.get("area", ""); r["ts"] = utc()
            append_jsonl(f, r)
            log(f"  ✓ Social: {n}")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(do, e) for e in ents]
        for i, fut in enumerate(as_completed(futs)):
            try: fut.result()
            except Exception as ex: log(f"  ERR: {ex}")
            if (i+1) % 50 == 0:
                log(f"  ... Social progress: {i+1}/{len(ents)} | {llm.info()}")


# ═══════════════════════════════════════════════════════════════════════════════
# MODE: descriptions — Mô tả chi tiết
# ═══════════════════════════════════════════════════════════════════════════════

def descriptions(llm: LLM, workers: int = 8):
    log("═══ LLM BURN: DETAILED DESCRIPTIONS ═══")
    f = OUTPUT_DIR / "descriptions.jsonl"
    done = {r.get("entity_id") for r in read_jsonl(f)}
    ents = [e for e in load_entities() if e["id"] not in done]
    log(f"  {len(ents)} entities for descriptions")

    def do(e):
        prov = PROVINCE.get(e.get("area", ""), "ĐBSCL")
        n = e["name"]
        t = e.get("type", "place")
        ctx = _load_research_context(e["id"])
        extra = f"\n[Nghiên cứu]:\n{ctx}" if ctx else ""
        r = llm.ask_json(sys=SYS_WRITER, user=f"""Viết mô tả CHI TIẾT cho "{n}" (loại: {t}, {prov})
Summary: {e.get('summary','')[:500]}
{extra}

JSON:
{{
  "entity_id": "{e['id']}",
  "name": "{n}",
  "short_desc": "1 câu, 30 từ, bản chất",
  "medium_desc": "3-5 câu, 80-120 từ, đủ thông tin chính",
  "long_desc": "300-500 từ, chi tiết toàn diện, hấp dẫn",
  "emotional_desc": "100-150 từ, gợi cảm xúc, kể chuyện",
  "practical_desc": "100-150 từ, thông tin thực tế (giờ, giá, cách đi)",
  "unique_selling_point": "1 câu, điểm khác biệt duy nhất",
  "visitor_persona_match": ["cặp đôi", "gia đình", "..."],
  "time_needed": "thời gian khuyến nghị",
  "best_combined_with": ["entity khác nên kết hợp"],
  "avoid_if": "không phù hợp nếu..."
}}""", temp=0.3, max_tok=5000)
        if r:
            r["entity_id"] = e["id"]; r["area"] = e.get("area", ""); r["type"] = t; r["ts"] = utc()
            append_jsonl(f, r)
            log(f"  ✓ Desc: {n}")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(do, e) for e in ents]
        for i, fut in enumerate(as_completed(futs)):
            try: fut.result()
            except Exception as ex: log(f"  ERR: {ex}")
            if (i+1) % 50 == 0:
                log(f"  ... Desc progress: {i+1}/{len(ents)} | {llm.info()}")


# ═══════════════════════════════════════════════════════════════════════════════
# MODE: tips — Mẹo du lịch
# ═══════════════════════════════════════════════════════════════════════════════

TIPS_TOPICS = [
    "mẹo tiết kiệm chi phí du lịch miền Tây",
    "mẹo chụp ảnh đẹp miền Tây sông nước",
    "mẹo an toàn đi du lịch miền Tây",
    "mẹo ăn uống miền Tây tránh đau bụng",
    "mẹo di chuyển miền Tây cho người lần đầu",
    "mẹo du lịch mùa mưa miền Tây",
    "mẹo du lịch mùa nước nổi",
    "mẹo homestay miền Tây chọn ở đâu",
    "mẹo mua quà đặc sản miền Tây",
    "mẹo du lịch bằng xe máy miền Tây",
    "mẹo du lịch với trẻ em miền Tây",
    "mẹo du lịch cho người lớn tuổi miền Tây",
    "mẹo du lịch solo nữ miền Tây an toàn",
    "mẹo du lịch Tết miền Tây",
    "mẹo giao tiếp với người dân địa phương miền Tây",
    "mẹo tham quan chùa Khmer Trà Vinh",
    "mẹo trải nghiệm chợ nổi miền Tây",
    "mẹo du lịch Bến Tre xứ dừa",
    "mẹo du lịch Vĩnh Long lần đầu",
    "mẹo du lịch Trà Vinh khám phá Khmer",
    "mẹo du lịch bền vững miền Tây",
    "mẹo du lịch mùa trái cây miền Tây",
    "mẹo check-in Instagram miền Tây",
    "mẹo du lịch nhóm bạn miền Tây vui",
    "mẹo du lịch cặp đôi miền Tây lãng mạn",
    "lỗi thường gặp khi du lịch miền Tây",
    "mẹo đi ghe thuyền miền Tây không say sóng",
    "mẹo chọn tour miền Tây giá tốt",
    "mẹo wifi internet miền Tây cho digital nomad",
    "mẹo du lịch miền Tây dịp lễ 30/4 2/9",
]


def tips_generate(llm: LLM, workers: int = 8):
    log("═══ LLM BURN: TRAVEL TIPS ═══")
    f = OUTPUT_DIR / "tips.jsonl"
    done = {r.get("topic") for r in read_jsonl(f)}
    topics = [t for t in TIPS_TOPICS if t not in done]
    log(f"  {len(topics)} tips topics")

    def do(topic):
        r = llm.ask_json(sys=SYS_QA, user=f"""Viết bài mẹo du lịch chi tiết: "{topic}"

JSON:
{{
  "topic": "{topic}",
  "title": "tiêu đề hấp dẫn",
  "intro": "100 từ giới thiệu",
  "tips": [
    {{
      "number": 1,
      "title": "tiêu đề mẹo",
      "content": "100-150 từ chi tiết mẹo, có ví dụ cụ thể",
      "pro_tip": "mẹo nâng cao từ người địa phương",
      "related_entities": ["entity liên quan"]
    }}
  ],
  "common_mistakes": ["sai lầm thường gặp 1", "sai lầm 2", "sai lầm 3"],
  "summary": "50 từ tóm tắt",
  "tags": ["tag1", "tag2"],
  "audience": "đối tượng phù hợp nhất"
}}""", temp=0.4, max_tok=8000)
        if r:
            r["topic"] = topic; r["ts"] = utc()
            n_tips = len(r.get("tips", []))
            append_jsonl(f, r)
            log(f"  ✓ Tips: {topic[:40]}... ({n_tips} tips)")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for fut in as_completed([pool.submit(do, t) for t in topics]):
            try: fut.result()
            except Exception as ex: log(f"  ERR: {ex}")


# ═══════════════════════════════════════════════════════════════════════════════
# MODE: stories — Câu chuyện địa phương
# ═══════════════════════════════════════════════════════════════════════════════

STORY_PROMPTS = [
    ("co_gai_dua", "Cô gái Bến Tre và cây dừa — truyền thuyết xứ dừa"),
    ("cau_my_thuan", "Câu chuyện cầu Mỹ Thuận — giấc mơ bắc qua sông Tiền"),
    ("cho_noi_binh_minh", "Bình minh trên chợ nổi — một ngày ở sông nước miền Tây"),
    ("nghe_nhan_chieu", "Nghệ nhân dệt chiếu cuối cùng — câu chuyện giữ nghề"),
    ("co_chi_lam_keo_dua", "Bí quyết kẹo dừa Mỏ Cày — câu chuyện 3 thế hệ"),
    ("chua_khmer_binh_minh", "Bình minh ở chùa Khmer — khi ánh nắng chạm mái cong"),
    ("don_ca_tai_tu_dem", "Đêm đờn ca tài tử bên sông — thanh âm miền Tây"),
    ("mua_nuoc_noi_story", "Mùa nước nổi — khi miền Tây sống chung với lũ"),
    ("o_cua", "Ông già và ô cửa — câu chuyện làm bánh tráng Mỹ Lồng"),
    ("con_doi_tra_vinh", "Cồn Dơi Trà Vinh — khi dơi bay trong hoàng hôn"),
    ("vuon_trai_cay", "Một ngày ở vườn trái cây Vĩnh Long — mùa chôm chôm chín rộ"),
    ("pha_vinh_long", "Phà qua sông — chuyện cũ người xưa Vĩnh Long"),
    ("nghe_nhan_gom", "Nghệ nhân gốm Vĩnh Long — lửa và đất"),
    ("cot_co_tra_vinh", "Cột cờ Trà Vinh và câu chuyện độc lập"),
    ("song_co_chien", "Sông Cổ Chiên — dòng chảy lịch sử và đời thường"),
    ("cho_dem_vinh_long", "Chợ đêm Vĩnh Long — thanh âm và mùi vị miền sông nước"),
    ("lang_nghe_an_binh", "Cù lao An Bình — hòn đảo xanh giữa sông"),
    ("tet_khmer", "Tết Khmer ở Trà Vinh — lễ hội sắc màu"),
    ("con_phung", "Cồn Phụng — di sản của ông Đạo Dừa"),
    ("ba_chua_xu", "Tín ngưỡng Bà Chúa Xứ — tâm linh miền Tây"),
    ("ghe_ngo", "Đua ghe ngo — tốc độ trên sông Trà Vinh"),
    ("hai_san_tra_vinh", "Biển Trà Vinh — hải sản và bình minh"),
    ("thanh_pho_vinh_long", "Thành phố Vĩnh Long — đô thị nhỏ bên sông"),
    ("cam_sanh_tra_vinh", "Cam sành Trà Vinh — vàng ruộm miệt vườn"),
    ("banh_xeo_mien_tay", "Bánh xèo miền Tây — tiếng xèo đầy cảm xúc"),
]


def stories(llm: LLM, workers: int = 8):
    log("═══ LLM BURN: LOCAL STORIES ═══")
    f = OUTPUT_DIR / "stories.jsonl"
    done = {r.get("key") for r in read_jsonl(f)}
    prompts = [(k, p) for k, p in STORY_PROMPTS if k not in done]
    log(f"  {len(prompts)} stories to write")

    def do(item):
        key, prompt = item
        r = llm.ask_json(sys=SYS_WRITER, user=f"""Viết câu chuyện du lịch: "{prompt}"

Viết 1000-1500 từ, phong cách travel writing chuyên nghiệp.
Đan xen mô tả cảnh, cảm xúc, lịch sử, ẩm thực, con người.
Giọng văn: chậm rãi, gợi hình, như đang kể cho bạn nghe.

JSON:
{{
  "key": "{key}",
  "title": "tiêu đề bài viết",
  "subtitle": "phụ đề",
  "estimated_reading_time": 7,
  "location": "khu vực cụ thể",
  "paragraphs": [
    "Đoạn 1 (mở đầu hook): 200-300 từ",
    "Đoạn 2 (thân bài): 200-300 từ",
    "Đoạn 3 (thân bài): 200-300 từ",
    "Đoạn 4 (cao trào/chi tiết đặc biệt): 200-300 từ",
    "Đoạn 5 (kết bài cảm xúc): 150-200 từ"
  ],
  "pull_quotes": ["câu trích dẫn hay nhất"],
  "photo_suggestions": ["mô tả ảnh nên đi kèm bài"],
  "related_entities": ["entity liên quan"],
  "mood_playlist": ["gợi ý nhạc đọc kèm"],
  "tags": ["travel", "miền Tây", "..."]
}}""", temp=0.6, max_tok=10000)
        if r:
            r["key"] = key; r["ts"] = utc()
            append_jsonl(f, r)
            log(f"  ✓ Story: {key}")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for fut in as_completed([pool.submit(do, p) for p in prompts]):
            try: fut.result()
            except Exception as ex: log(f"  ERR: {ex}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

MODES = {
    "seo-all": seo_all,
    "narratives": narratives,
    "itineraries": itineraries,
    "qa": qa_generate,
    "social": social_content,
    "descriptions": descriptions,
    "tips": tips_generate,
    "stories": stories,
}

def main():
    _cfg_io()
    ap = argparse.ArgumentParser(description="Mega LLM Burn — Pure GPT-5.5")
    ap.add_argument("--mode", required=True, choices=list(MODES.keys()) + ["all"])
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    llm = LLM()
    if not llm.ok:
        log("ERROR: LLM not configured"); return

    t0 = time.time()
    log(f"Model: {llm.model}  Workers: {a.workers}")
    log(f"Entities loaded: {len(load_entities())}")

    modes = list(MODES.keys()) if a.mode == "all" else [a.mode]
    for m in modes:
        log(f"\n{'='*60}")
        MODES[m](llm, workers=a.workers)
        log(f"  LLM after {m}: {llm.info()}")

    elapsed = (time.time() - t0) / 60
    log(f"\n{'='*60}")
    log(f"═══ DONE ({elapsed:.1f}m) ═══")
    log(f"  FINAL LLM: {llm.info()}")
    log(f"  Output: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
