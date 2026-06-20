#!/usr/bin/env python3
"""MEGA Deep Dive — Nghiên cứu CỰC SÂU mỗi entity với 5-10 web searches.

Bổ sung cho mega_research.py — chạy SONG SONG, đốt token tối đa.

Modes:
  --mode history-deep    : Nghiên cứu sâu lịch sử mỗi di tích (5 web queries/entity)
  --mode food-deep       : Phân tích sâu ẩm thực (công thức, video, review, so sánh)
  --mode person          : Tất cả nhân vật lịch sử 3 tỉnh
  --mode accommodation   : Tất cả khách sạn/homestay (giá, review, tiện nghi)
  --mode place-deep      : Tất cả địa điểm (chi tiết visitor info)
  --mode product-deep    : Tất cả sản phẩm đặc sản
  --mode culture         : Văn hóa phi vật thể (đờn ca tài tử, nhạc ngũ âm, Rô Băm...)
  --mode transport       : Giao thông, đường đi, phương tiện
  --mode photo-spots     : Điểm chụp ảnh đẹp, golden hour
  --mode hidden-gems     : Phát hiện điểm ẩn, off-the-beaten-path
  --mode seasonal        : Phân tích theo mùa chi tiết
  --mode compare         : So sánh 3 tỉnh trên nhiều chiều
  --mode all             : TẤT CẢ modes trên

Usage:
  python -u agent/scripts/mega_deep_dive.py --mode all --workers 8
  python -u agent/scripts/mega_deep_dive.py --mode food-deep --workers 6
"""
from __future__ import annotations
import argparse, json, os, re, sys, time, threading, warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

warnings.filterwarnings("ignore", message=".*renamed.*ddgs.*")

AGENT_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = AGENT_DIR.parent
OUTPUT_DIR = AGENT_DIR / "data" / "mega_research" / "deep_dive"
DATA_JSON = PROJECT_DIR / "web" / "data.json"

sys.path.insert(0, str(AGENT_DIR))
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_DIR / ".env")
except Exception:
    pass

# Reuse from mega_research
sys.path.insert(0, str(AGENT_DIR / "scripts"))
from mega_research import (LLM, web_research, src_list, read_jsonl, append_jsonl,
                           load_entities, log, utc, SYS_ACCURACY, PROVINCE, _cfg_io)

DEFAULT_MODEL = os.environ.get("LLM_MODEL") or "cx/gpt-5.5"


# ═══════════════════════════════════════════════════════════════════════════════
# MODE: history-deep — 5 web queries per heritage site
# ═══════════════════════════════════════════════════════════════════════════════

def history_deep(llm: LLM, workers: int = 6):
    log("═══ DEEP DIVE: HISTORY ═══")
    f = OUTPUT_DIR / "history_deep.jsonl"
    done = {r.get("entity_id") for r in read_jsonl(f)}
    ents = [e for e in load_entities() if e.get("type") == "history" and e["id"] not in done]
    log(f"  {len(ents)} history entities for deep dive")

    def do(e):
        prov = PROVINCE.get(e.get("area", ""), "ĐBSCL")
        n = e["name"]
        wr, ctx = web_research([
            f'"{n}" {prov} lịch sử chi tiết',
            f'"{n}" kiến trúc đặc điểm nghệ thuật',
            f'"{n}" lễ hội sự kiện hàng năm',
            f'"{n}" trùng tu bảo tồn hiện trạng',
            f'"{n}" du lịch review đánh giá du khách',
        ], max_per=6, max_fetch=15)
        r = llm.ask_json(sys=SYS_ACCURACY, user=f"""NGHIÊN CỨU SÂU: "{n}" ({prov})
Summary hiện có: {e.get('summary','')[:500]}

[NGUỒN WEB — 5 góc nghiên cứu]:
{ctx}

JSON chi tiết (null nếu không có nguồn):
{{
  "name": "{n}",
  "deep_history": {{"founding": null, "key_periods": [], "notable_events": [], "historical_figures": [], "confidence": 0.0}},
  "architecture_detail": {{"style": null, "materials": [], "dimensions": null, "unique_features": [], "restorations": [], "confidence": 0.0}},
  "cultural_practices": {{"annual_events": [], "rituals": [], "offerings": null, "music": null, "confidence": 0.0}},
  "conservation": {{"status": null, "threats": [], "projects": [], "funding": null, "confidence": 0.0}},
  "visitor_experience": {{"reviews_summary": null, "best_photo_spots": [], "hidden_details": [], "local_tips": [], "nearby_food": [], "confidence": 0.0}},
  "emotional_narrative": "200-300 từ kể câu chuyện cảm xúc về nơi này (chỉ dựa trên nguồn)",
  "seo_long_content": "500+ từ mô tả SEO-friendly đầy đủ",
  "overall_confidence": 0.0
}}""", temp=0.2, max_tok=6000)
        if r:
            r["entity_id"] = e["id"]; r["entity_name"] = n; r["area"] = e.get("area", "")
            r["sources"] = src_list(wr); r["n_sources"] = len(wr); r["ts"] = utc()
            append_jsonl(f, r)
            log(f"  ✓ {n} [{len(wr)} src]")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for i, fut in enumerate(as_completed([pool.submit(do, e) for e in ents])):
            try: fut.result()
            except Exception as ex: log(f"  ERR: {ex}")


# ═══════════════════════════════════════════════════════════════════════════════
# MODE: food-deep — Deep gastronomy analysis
# ═══════════════════════════════════════════════════════════════════════════════

def food_deep(llm: LLM, workers: int = 6):
    log("═══ DEEP DIVE: GASTRONOMY ═══")
    f = OUTPUT_DIR / "food_deep.jsonl"
    done = {r.get("entity_id") for r in read_jsonl(f)}
    ents = [e for e in load_entities() if e.get("type") in ("dish", "drink") and e["id"] not in done]
    log(f"  {len(ents)} dishes for deep dive")

    def do(e):
        prov = PROVINCE.get(e.get("area", ""), "ĐBSCL")
        n = e["name"]
        wr, ctx = web_research([
            f'"{n}" {prov} công thức nấu chi tiết',
            f'"{n}" nguồn gốc lịch sử ẩm thực',
            f'"{n}" review đánh giá quán ngon nhất',
            f'"{n}" giá bao nhiêu ở đâu ăn',
            f'"{n}" so sánh với món tương tự miền Tây',
            f'"{n}" video hướng dẫn nấu',
        ], max_per=5, max_fetch=15)
        r = llm.ask_json(sys=SYS_ACCURACY, user=f"""PHÂN TÍCH SÂU ẩm thực: "{n}" ({prov})
Summary: {e.get('summary','')[:400]}

[NGUỒN WEB — 6 góc]:
{ctx}

JSON:
{{
  "name": "{n}",
  "origin_story": {{"text": "300+ từ về nguồn gốc", "ethnic_roots": null, "century": null, "confidence": 0.0}},
  "recipe_detail": {{
    "ingredients": [{{"name": "...", "amount": "...", "substitute": null, "local_source": null}}],
    "steps": [{{"step": 1, "description": "...", "tips": "...", "duration": null}}],
    "total_time": null, "difficulty": "dễ|trung_bình|khó",
    "confidence": 0.0
  }},
  "sensory_profile": {{
    "taste": {{"sweet": 0, "sour": 0, "salty": 0, "bitter": 0, "umami": 0, "spicy": 0}},
    "texture": null, "aroma": null, "visual": null, "temperature": null
  }},
  "where_to_eat": [
    {{"name": "tên quán", "address": null, "price_range": null, "rating": null, "specialty": null, "source": null}}
  ],
  "food_pairing": ["món ăn kèm tốt nhất"],
  "health_notes": null,
  "seasonal_availability": null,
  "similar_dishes": [{{"name": "...", "region": "...", "difference": "..."}}],
  "instagram_worthiness": "mô tả visual appeal cho ảnh",
  "seo_content": "500+ từ SEO-friendly",
  "overall_confidence": 0.0
}}""", temp=0.2, max_tok=6000)
        if r:
            r["entity_id"] = e["id"]; r["entity_name"] = n; r["area"] = e.get("area", "")
            r["sources"] = src_list(wr); r["n_sources"] = len(wr); r["ts"] = utc()
            append_jsonl(f, r)
            log(f"  ✓ {n} [{len(wr)} src]")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for i, fut in enumerate(as_completed([pool.submit(do, e) for e in ents])):
            try: fut.result()
            except Exception as ex: log(f"  ERR: {ex}")


# ═══════════════════════════════════════════════════════════════════════════════
# MODE: person — Nhân vật lịch sử
# ═══════════════════════════════════════════════════════════════════════════════

def person_research(llm: LLM, workers: int = 6):
    log("═══ DEEP DIVE: PERSONS ═══")
    f = OUTPUT_DIR / "persons.jsonl"
    done = {r.get("entity_id") for r in read_jsonl(f)}
    ents = [e for e in load_entities() if e.get("type") == "person" and e["id"] not in done]
    log(f"  {len(ents)} persons for deep research")

    def do(e):
        prov = PROVINCE.get(e.get("area", ""), "ĐBSCL")
        n = e["name"]
        wr, ctx = web_research([
            f'"{n}" tiểu sử nhân vật lịch sử',
            f'"{n}" {prov} đóng góp di sản',
            f'"{n}" tượng đài đền thờ kỷ niệm',
        ], max_per=8, max_fetch=12)
        r = llm.ask_json(sys=SYS_ACCURACY, user=f"""Nhân vật: "{n}" ({prov})
Summary: {e.get('summary','')[:400]}
[NGUỒN WEB]: {ctx}
JSON:
{{
  "name": "{n}", "birth_year": null, "death_year": null,
  "biography": {{"text": "300+ từ", "confidence": 0.0}},
  "achievements": [{{"achievement": "...", "year": null, "confidence": 0.0}}],
  "legacy": {{"memorials": [], "streets_named": [], "schools": [], "confidence": 0.0}},
  "quotes": [],
  "related_sites": [{{"name": "...", "type": "đền_thờ|tượng|bảo_tàng", "confidence": 0.0}}],
  "seo_content": "400+ từ",
  "overall_confidence": 0.0
}}""", temp=0.15, max_tok=5000)
        if r:
            r["entity_id"] = e["id"]; r["entity_name"] = n; r["area"] = e.get("area", "")
            r["sources"] = src_list(wr); r["n_sources"] = len(wr); r["ts"] = utc()
            append_jsonl(f, r)
            log(f"  ✓ {n} [{len(wr)} src]")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for fut in as_completed([pool.submit(do, e) for e in ents]):
            try: fut.result()
            except Exception as ex: log(f"  ERR: {ex}")


# ═══════════════════════════════════════════════════════════════════════════════
# MODE: accommodation — Khách sạn/homestay deep
# ═══════════════════════════════════════════════════════════════════════════════

def accommodation_research(llm: LLM, workers: int = 6):
    log("═══ DEEP DIVE: ACCOMMODATION ═══")
    f = OUTPUT_DIR / "accommodation.jsonl"
    done = {r.get("entity_id") for r in read_jsonl(f)}
    ents = [e for e in load_entities() if e.get("type") == "accommodation" and e["id"] not in done]
    log(f"  {len(ents)} accommodations for deep research")

    def do(e):
        prov = PROVINCE.get(e.get("area", ""), "ĐBSCL")
        n = e["name"]
        wr, ctx = web_research([
            f'"{n}" {prov} review đánh giá',
            f'"{n}" giá phòng tiện nghi dịch vụ',
            f'"{n}" booking agoda traveloka',
            f'"{n}" hình ảnh phòng',
        ], max_per=6, max_fetch=12)
        r = llm.ask_json(sys=SYS_ACCURACY, user=f"""Lưu trú: "{n}" ({prov})
Summary: {e.get('summary','')[:400]}
[NGUỒN WEB]: {ctx}
JSON:
{{
  "name": "{n}", "type": "khách_sạn|homestay|farmstay|resort|nhà_nghỉ",
  "star_rating": null, "price_range": {{"min": null, "max": null, "currency": "VND", "confidence": 0.0}},
  "rooms": {{"total": null, "types": []}},
  "amenities": ["wifi", "..."],
  "highlights": ["điểm nổi bật"],
  "reviews_summary": {{"positive": ["..."], "negative": ["..."], "avg_rating": null, "confidence": 0.0}},
  "location": {{"address": null, "nearby_attractions": [], "transport": null}},
  "contact": {{"phone": null, "website": null, "booking_links": []}},
  "best_for": ["cặp đôi|gia đình|nhóm bạn|công tác"],
  "seo_content": "300+ từ",
  "overall_confidence": 0.0
}}""", temp=0.15, max_tok=4000)
        if r:
            r["entity_id"] = e["id"]; r["entity_name"] = n; r["area"] = e.get("area", "")
            r["sources"] = src_list(wr); r["n_sources"] = len(wr); r["ts"] = utc()
            append_jsonl(f, r)
            log(f"  ✓ {n} [{len(wr)} src]")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for fut in as_completed([pool.submit(do, e) for e in ents]):
            try: fut.result()
            except Exception as ex: log(f"  ERR: {ex}")


# ═══════════════════════════════════════════════════════════════════════════════
# MODE: culture — Văn hóa phi vật thể
# ═══════════════════════════════════════════════════════════════════════════════

CULTURE_TOPICS = [
    ("don_ca_tai_tu", "Đờn ca tài tử Nam Bộ UNESCO Vĩnh Long Bến Tre Trà Vinh"),
    ("nhac_ngu_am", "Nhạc ngũ âm Khmer Trà Vinh truyền thống"),
    ("ro_bam", "Sân khấu Rô Băm Khmer nghệ thuật biểu diễn"),
    ("du_ke", "Dù kê nghệ thuật Khmer Nam Bộ Trà Vinh"),
    ("hat_boi", "Hát bội miền Tây Vĩnh Long Bến Tre"),
    ("le_hoi_ok_om_bok", "Lễ hội Ok Om Bok Trà Vinh Khmer chi tiết nghi thức"),
    ("tet_chol_chnam_thmay", "Tết Chôl Chnăm Thmây Khmer Trà Vinh"),
    ("dua_ghe_ngo", "Đua ghe ngo Khmer Trà Vinh Sóc Trăng truyền thống"),
    ("nghe_det_chieu", "Nghề dệt chiếu Vĩnh Long Bến Tre truyền thống"),
    ("nghe_lam_banh_trang", "Nghề làm bánh tráng Mỹ Lồng Bến Tre"),
    ("nghe_lam_keo_dua", "Nghề làm kẹo dừa Bến Tre làng nghề truyền thống"),
    ("van_hoa_song_nuoc", "Văn hóa sông nước ĐBSCL chợ nổi ghe xuồng"),
    ("tin_nguong_ba_chua_xu", "Tín ngưỡng Bà Chúa Xứ miền Tây Nam Bộ"),
    ("nghe_thuat_cai_luong", "Nghệ thuật cải lương miền Tây Vĩnh Long"),
    ("phong_tuc_cuoi_hoi", "Phong tục cưới hỏi miền Tây Khmer Việt"),
    ("am_thuc_le_tet", "Ẩm thực lễ tết miền Tây truyền thống"),
    ("nghe_dan_lat", "Nghề đan lát tre lá miền Tây ĐBSCL"),
    ("van_hoa_miet_vuon", "Văn hóa miệt vườn sông nước miền Tây"),
]


def culture_research(llm: LLM, workers: int = 6):
    log("═══ DEEP DIVE: CULTURE ═══")
    f = OUTPUT_DIR / "culture.jsonl"
    done = {r.get("key") for r in read_jsonl(f)}
    topics = [(k, q) for k, q in CULTURE_TOPICS if k not in done]
    log(f"  {len(topics)} culture topics for deep research")

    def do(item):
        key, query = item
        wr, ctx = web_research([
            query,
            query.split()[0] + " " + " ".join(query.split()[1:3]) + " nghiên cứu",
            query.split()[0] + " " + " ".join(query.split()[1:3]) + " bảo tồn phát triển",
        ], max_per=8, max_fetch=15)
        r = llm.ask_json(sys=SYS_ACCURACY, user=f"""Nghiên cứu văn hóa phi vật thể: "{query}"

[NGUỒN WEB]:
{ctx}

JSON:
{{
  "topic": "{key}",
  "title": "tên chính xác",
  "category": "âm_nhạc|sân_khấu|lễ_hội|nghề|phong_tục|tín_ngưỡng|ẩm_thực",
  "ethnic_origin": "Việt|Khmer|Hoa|đa_dân_tộc",
  "provinces": ["Vĩnh Long", "Bến Tre", "Trà Vinh"],
  "history": {{"text": "300+ từ lịch sử chi tiết", "confidence": 0.0}},
  "description": {{"text": "500+ từ mô tả chi tiết", "confidence": 0.0}},
  "practitioners": {{"notable": [], "training": null, "current_state": null, "confidence": 0.0}},
  "unesco_status": null,
  "conservation": {{"status": null, "challenges": [], "initiatives": [], "confidence": 0.0}},
  "tourism_potential": {{"where_experience": [], "when": null, "tips": [], "confidence": 0.0}},
  "related_entities": [],
  "seo_content": "600+ từ SEO",
  "overall_confidence": 0.0
}}""", temp=0.2, max_tok=6000)
        if r:
            r["key"] = key; r["sources"] = src_list(wr); r["n_sources"] = len(wr); r["ts"] = utc()
            append_jsonl(f, r)
            log(f"  ✓ {key} [{len(wr)} src]")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for fut in as_completed([pool.submit(do, t) for t in topics]):
            try: fut.result()
            except Exception as ex: log(f"  ERR: {ex}")


# ═══════════════════════════════════════════════════════════════════════════════
# MODE: transport — Giao thông
# ═══════════════════════════════════════════════════════════════════════════════

TRANSPORT_QUERIES = [
    ("hcm_to_vl", "đường đi từ TP.HCM đến Vĩnh Long xe khách xe buýt"),
    ("hcm_to_bt", "đường đi từ TP.HCM đến Bến Tre xe khách"),
    ("hcm_to_tv", "đường đi từ TP.HCM đến Trà Vinh xe khách"),
    ("vl_to_bt", "đường đi từ Vĩnh Long đến Bến Tre phà xe"),
    ("vl_to_tv", "đường đi từ Vĩnh Long đến Trà Vinh"),
    ("bt_to_tv", "đường đi từ Bến Tre đến Trà Vinh"),
    ("local_vl", "di chuyển nội tỉnh Vĩnh Long xe buýt xe ôm grab"),
    ("local_bt", "di chuyển nội tỉnh Bến Tre phương tiện"),
    ("local_tv", "di chuyển nội tỉnh Trà Vinh phương tiện"),
    ("ferry_routes", "phà đò ngang Vĩnh Long Bến Tre Trà Vinh tuyến"),
    ("bike_rental", "thuê xe máy xe đạp Vĩnh Long Bến Tre Trà Vinh"),
    ("boat_tour", "tour thuyền sông Vĩnh Long Bến Tre"),
]


def transport_research(llm: LLM, workers: int = 6):
    log("═══ DEEP DIVE: TRANSPORT ═══")
    f = OUTPUT_DIR / "transport.jsonl"
    done = {r.get("key") for r in read_jsonl(f)}
    topics = [(k, q) for k, q in TRANSPORT_QUERIES if k not in done]
    log(f"  {len(topics)} transport topics")

    def do(item):
        key, query = item
        wr, ctx = web_research([query, query + " 2026 giá vé thời gian"], max_per=8, max_fetch=12)
        r = llm.ask_json(sys=SYS_ACCURACY, user=f"""Giao thông: "{query}"
[NGUỒN WEB]: {ctx}
JSON:
{{
  "route": "{key}",
  "options": [
    {{"mode": "xe_khách|xe_buýt|grab|phà|thuyền|xe_máy",
      "operator": null, "duration": null, "price": null,
      "frequency": null, "station": null, "tips": null, "confidence": 0.0, "source": null}}
  ],
  "best_option": null,
  "warnings": [],
  "overall_confidence": 0.0
}}""", temp=0.15, max_tok=4000)
        if r:
            r["key"] = key; r["sources"] = src_list(wr); r["n_sources"] = len(wr); r["ts"] = utc()
            append_jsonl(f, r)
            log(f"  ✓ {key} [{len(wr)} src]")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for fut in as_completed([pool.submit(do, t) for t in topics]):
            try: fut.result()
            except Exception as ex: log(f"  ERR: {ex}")


# ═══════════════════════════════════════════════════════════════════════════════
# MODE: seasonal — Phân tích theo mùa
# ═══════════════════════════════════════════════════════════════════════════════

def seasonal_research(llm: LLM, workers: int = 6):
    log("═══ DEEP DIVE: SEASONAL ═══")
    f = OUTPUT_DIR / "seasonal.jsonl"
    done = {r.get("key") for r in read_jsonl(f)}

    months = [(f"month_{m:02d}", f"du lịch miền Tây tháng {m} thời tiết trái cây lễ hội") for m in range(1, 13)]
    seasons = [
        ("mua_nuoc_noi", "mùa nước nổi ĐBSCL du lịch trải nghiệm tháng mấy"),
        ("mua_kho", "mùa khô ĐBSCL du lịch hoạt động"),
        ("tet_nguyen_dan", "Tết Nguyên Đán miền Tây du lịch chợ hoa"),
        ("he", "du lịch hè miền Tây gia đình tháng 6 7 8"),
    ]
    topics = [(k, q) for k, q in months + seasons if k not in done]
    log(f"  {len(topics)} seasonal topics")

    def do(item):
        key, query = item
        wr, ctx = web_research([query, query + " Vĩnh Long Bến Tre Trà Vinh"], max_per=6, max_fetch=10)
        r = llm.ask_json(sys=SYS_ACCURACY, user=f"""Phân tích mùa: "{query}"
[NGUỒN WEB]: {ctx}
JSON:
{{
  "period": "{key}",
  "weather": {{"temperature": null, "rainfall": null, "humidity": null, "confidence": 0.0}},
  "fruits_available": [{{"name": "...", "peak": null, "province": null}}],
  "events": [{{"name": "...", "date": null}}],
  "activities": ["hoạt động tốt nhất"],
  "pros": ["ưu điểm du lịch lúc này"],
  "cons": ["nhược điểm"],
  "crowd_level": "thấp|trung_bình|cao|rất_cao",
  "price_level": "thấp|trung_bình|cao",
  "recommended_entities": [],
  "packing_tips": [],
  "overall_confidence": 0.0
}}""", temp=0.15, max_tok=4000)
        if r:
            r["key"] = key; r["sources"] = src_list(wr); r["n_sources"] = len(wr); r["ts"] = utc()
            append_jsonl(f, r)
            log(f"  ✓ {key} [{len(wr)} src]")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for fut in as_completed([pool.submit(do, t) for t in topics]):
            try: fut.result()
            except Exception as ex: log(f"  ERR: {ex}")


# ═══════════════════════════════════════════════════════════════════════════════
# MODE: compare — So sánh 3 tỉnh
# ═══════════════════════════════════════════════════════════════════════════════

COMPARE_DIMS = [
    ("tourism_overview", "so sánh du lịch Vĩnh Long Bến Tre Trà Vinh điểm mạnh điểm yếu"),
    ("food_comparison", "so sánh ẩm thực Vĩnh Long Bến Tre Trà Vinh đặc sản khác biệt"),
    ("culture_comparison", "so sánh văn hóa Vĩnh Long Bến Tre Trà Vinh Khmer Việt"),
    ("nature_comparison", "so sánh thiên nhiên sinh thái Vĩnh Long Bến Tre Trà Vinh"),
    ("accommodation_comparison", "so sánh lưu trú Vĩnh Long Bến Tre Trà Vinh giá homestay"),
    ("accessibility", "so sánh giao thông tiếp cận Vĩnh Long Bến Tre Trà Vinh từ TPHCM"),
    ("budget_comparison", "chi phí du lịch Vĩnh Long Bến Tre Trà Vinh so sánh ngân sách"),
    ("family_friendliness", "du lịch gia đình Vĩnh Long Bến Tre Trà Vinh phù hợp trẻ em"),
    ("photography", "chụp ảnh đẹp Vĩnh Long Bến Tre Trà Vinh điểm đẹp nhất"),
    ("hidden_gems", "điểm ẩn ít người biết Vĩnh Long Bến Tre Trà Vinh off beaten path"),
]


def compare_research(llm: LLM, workers: int = 6):
    log("═══ DEEP DIVE: COMPARE 3 PROVINCES ═══")
    f = OUTPUT_DIR / "compare.jsonl"
    done = {r.get("key") for r in read_jsonl(f)}
    topics = [(k, q) for k, q in COMPARE_DIMS if k not in done]
    log(f"  {len(topics)} comparison dimensions")

    def do(item):
        key, query = item
        wr, ctx = web_research([query], max_per=10, max_fetch=12)
        r = llm.ask_json(sys=SYS_ACCURACY, user=f"""So sánh 3 tỉnh: "{query}"
[NGUỒN WEB]: {ctx}
JSON:
{{
  "dimension": "{key}",
  "vinh_long": {{"strengths": ["..."], "weaknesses": ["..."], "highlights": ["..."], "score": null}},
  "ben_tre": {{"strengths": ["..."], "weaknesses": ["..."], "highlights": ["..."], "score": null}},
  "tra_vinh": {{"strengths": ["..."], "weaknesses": ["..."], "highlights": ["..."], "score": null}},
  "winner": null,
  "synergies": ["cách kết hợp 3 tỉnh tốt nhất"],
  "recommendation": "500+ từ phân tích chi tiết",
  "overall_confidence": 0.0
}}""", temp=0.2, max_tok=5000)
        if r:
            r["key"] = key; r["sources"] = src_list(wr); r["n_sources"] = len(wr); r["ts"] = utc()
            append_jsonl(f, r)
            log(f"  ✓ {key} [{len(wr)} src]")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for fut in as_completed([pool.submit(do, t) for t in topics]):
            try: fut.result()
            except Exception as ex: log(f"  ERR: {ex}")


# ═══════════════════════════════════════════════════════════════════════════════
# MODE: place-deep — Tất cả place entities
# ═══════════════════════════════════════════════════════════════════════════════

def place_deep(llm: LLM, workers: int = 6):
    log("═══ DEEP DIVE: PLACES ═══")
    f = OUTPUT_DIR / "places_deep.jsonl"
    done = {r.get("entity_id") for r in read_jsonl(f)}
    ents = [e for e in load_entities() if e.get("type") in ("place", "attraction") and e["id"] not in done]
    log(f"  {len(ents)} places for deep research")

    def do(e):
        prov = PROVINCE.get(e.get("area", ""), "ĐBSCL")
        n = e["name"]
        wr, ctx = web_research([
            f'"{n}" {prov} du lịch chi tiết',
            f'"{n}" review đánh giá kinh nghiệm',
            f'"{n}" giờ mở cửa giá vé địa chỉ',
            f'"{n}" ảnh đẹp điểm chụp hình',
        ], max_per=6, max_fetch=12)
        r = llm.ask_json(sys=SYS_ACCURACY, user=f"""Địa điểm: "{n}" ({prov})
Summary: {e.get('summary','')[:400]}
[NGUỒN WEB]: {ctx}
JSON:
{{
  "name": "{n}",
  "detailed_description": {{"text": "400+ từ", "confidence": 0.0}},
  "visitor_info": {{"hours": null, "fee": null, "duration_min": null, "best_time": null, "parking": null}},
  "highlights": ["điểm nổi bật"],
  "photo_spots": ["vị trí chụp ảnh đẹp"],
  "reviews": {{"summary": null, "avg_rating": null, "common_praise": [], "common_complaints": []}},
  "nearby": [{{"name": "...", "distance": null, "type": "..."}}],
  "local_tips": ["mẹo từ người địa phương"],
  "accessibility": null,
  "seo_content": "400+ từ SEO",
  "overall_confidence": 0.0
}}""", temp=0.15, max_tok=5000)
        if r:
            r["entity_id"] = e["id"]; r["entity_name"] = n; r["area"] = e.get("area", "")
            r["sources"] = src_list(wr); r["n_sources"] = len(wr); r["ts"] = utc()
            append_jsonl(f, r)
            log(f"  ✓ {n} [{len(wr)} src]")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for i, fut in enumerate(as_completed([pool.submit(do, e) for e in ents])):
            try: fut.result()
            except Exception as ex: log(f"  ERR: {ex}")


# ═══════════════════════════════════════════════════════════════════════════════
# MODE: product-deep
# ═══════════════════════════════════════════════════════════════════════════════

def product_deep(llm: LLM, workers: int = 6):
    log("═══ DEEP DIVE: PRODUCTS ═══")
    f = OUTPUT_DIR / "products_deep.jsonl"
    done = {r.get("entity_id") for r in read_jsonl(f)}
    ents = [e for e in load_entities() if e.get("type") == "product" and e["id"] not in done]
    log(f"  {len(ents)} products for deep research")

    def do(e):
        prov = PROVINCE.get(e.get("area", ""), "ĐBSCL")
        n = e["name"]
        wr, ctx = web_research([
            f'"{n}" {prov} sản phẩm đặc sản',
            f'"{n}" mua ở đâu giá bao nhiêu',
            f'"{n}" quy trình sản xuất nguyên liệu',
        ], max_per=6, max_fetch=10)
        r = llm.ask_json(sys=SYS_ACCURACY, user=f"""Sản phẩm: "{n}" ({prov})
Summary: {e.get('summary','')[:400]}
[NGUỒN WEB]: {ctx}
JSON:
{{
  "name": "{n}",
  "description": {{"text": "300+ từ", "confidence": 0.0}},
  "production": {{"process": null, "materials": [], "time": null, "confidence": 0.0}},
  "price": {{"range": null, "unit": null, "confidence": 0.0}},
  "where_buy": [{{"place": "...", "address": null, "online": null}}],
  "quality_markers": ["cách nhận biết hàng chất lượng"],
  "shelf_life": null,
  "gift_potential": "tốt cho quà tặng không",
  "seo_content": "300+ từ",
  "overall_confidence": 0.0
}}""", temp=0.15, max_tok=4000)
        if r:
            r["entity_id"] = e["id"]; r["entity_name"] = n; r["area"] = e.get("area", "")
            r["sources"] = src_list(wr); r["n_sources"] = len(wr); r["ts"] = utc()
            append_jsonl(f, r)
            log(f"  ✓ {n} [{len(wr)} src]")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for fut in as_completed([pool.submit(do, e) for e in ents]):
            try: fut.result()
            except Exception as ex: log(f"  ERR: {ex}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

MODES = {
    "history-deep": history_deep,
    "food-deep": food_deep,
    "person": person_research,
    "accommodation": accommodation_research,
    "culture": culture_research,
    "transport": transport_research,
    "seasonal": seasonal_research,
    "compare": compare_research,
    "place-deep": place_deep,
    "product-deep": product_deep,
}

def main():
    _cfg_io()
    ap = argparse.ArgumentParser(description="Mega Deep Dive")
    ap.add_argument("--mode", required=True, choices=list(MODES.keys()) + ["all"])
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    llm = LLM()
    if not llm.ok:
        log("ERROR: LLM not configured"); return

    t0 = time.time()
    log(f"Model: {llm.model}  Workers: {a.workers}")

    modes = list(MODES.keys()) if a.mode == "all" else [a.mode]
    for m in modes:
        MODES[m](llm, workers=a.workers)
        log(f"  LLM after {m}: {llm.info()}")

    log(f"\n═══ DONE ({(time.time()-t0)/60:.1f}m) ═══")
    log(f"  FINAL LLM: {llm.info()}")

if __name__ == "__main__":
    main()
