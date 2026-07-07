#!/usr/bin/env python3
"""MEGA NARRATIVE RUNNER — Rich editorial storytelling content.

Long-form Vietnamese narratives: travel essays, food stories, cultural deep-dives,
seasonal guides, human interest pieces. Content for blog/magazine section.

SEQUENTIAL — one API call at a time (proxy constraint).
Resume-safe via JSONL done set.

Usage:
  python -u agent/scripts/mega_narrative_run.py 2>&1
"""
from __future__ import annotations
import json
import os
import sys
import time
import warnings
warnings.filterwarnings("ignore", message=".*renamed.*ddgs.*")
from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = AGENT_DIR.parent
OUTPUT_DIR = AGENT_DIR / "data" / "mega_research" / "narratives"

sys.path.insert(0, str(AGENT_DIR))
sys.path.insert(0, str(AGENT_DIR / "scripts"))
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_DIR / ".env")
except Exception:
    pass

from mega_research import (LLM, read_jsonl, append_jsonl,
                           log, utc, _cfg_io)

SYS = "Bạn là NHÀ VĂN DU LỊCH hàng đầu, kết hợp văn phong Paul Theroux + Nguyễn Ngọc Tư. Trả về JSON thuần túy. Viết tiếng Việt văn chương, sống động."

TOPICS = [
    # TRAVEL ESSAYS (15)
    ("essays", "dawn_mekong",
     'Viết essay 1500 từ: "Bình minh trên sông Mekong" — hành trình 5am từ bến phà, ánh sáng, mùi cà phê, tiếng máy ghe, con người. JSON: {"title":"...","essay":"...","word_count":0,"mood":"...","locations":[...],"photography_notes":"..."}'),
    ("essays", "coconut_kingdom",
     'Viết essay 1500 từ: "Vương quốc dừa" — 1 ngày ở Bến Tre, từ vườn dừa → xưởng kẹo → thương lái → kênh rạch. JSON: {"title":"...","essay":"...","word_count":0,"mood":"...","locations":[...],"photography_notes":"..."}'),
    ("essays", "khmer_pagoda_silence",
     'Viết essay 1500 từ: "Sự im lặng trong chùa Khmer" — meditation morning, sư sãi trẻ, kiến trúc, Naga, thời gian. JSON: {"title":"...","essay":"...","word_count":0,"mood":"...","locations":[...],"photography_notes":"..."}'),
    ("essays", "floating_market_economics",
     'Viết essay 1500 từ: "Kinh tế trên mặt nước" — 4am chợ nổi, xuồng treo cây bẹo, mặc cả, cà phê sóng. JSON: {"title":"...","essay":"...","word_count":0,"mood":"...","locations":[...],"photography_notes":"..."}'),
    ("essays", "rainy_season_magic",
     'Viết essay 1500 từ: "Khi mưa về miền Tây" — mùa nước nổi, cánh đồng ngập, bông điên điển, cá linh, sấm chớp. JSON: {"title":"...","essay":"...","word_count":0,"mood":"...","locations":[...],"photography_notes":"..."}'),
    ("essays", "night_ferry",
     'Viết essay 1500 từ: "Đêm phà Vĩnh Long" — phà đêm, sông tối, đèn cá, gió, con người trên phà, câu chuyện. JSON: {"title":"...","essay":"...","word_count":0,"mood":"...","locations":[...],"photography_notes":"..."}'),
    ("essays", "grandma_kitchen",
     'Viết essay 1500 từ: "Bếp bà ngoại" — học nấu ăn từ bà 75 tuổi, chợ sáng, gia vị, kỷ niệm, recipes trong stories. JSON: {"title":"...","essay":"...","word_count":0,"mood":"...","locations":[...],"recipes_mentioned":[...]}'),
    ("essays", "island_time",
     'Viết essay 1500 từ: "Thời gian trên cù lao" — sống chậm 3 ngày cù lao An Bình/Quy, rhythm, hammock, trái cây. JSON: {"title":"...","essay":"...","word_count":0,"mood":"...","locations":[...],"photography_notes":"..."}'),
    ("essays", "colonial_ghosts",
     'Viết essay 1500 từ: "Bóng ma thuộc địa" — dấu ấn Pháp còn sót: kiến trúc, cầu, nhà thờ, kênh đào, ký ức. JSON: {"title":"...","essay":"...","word_count":0,"mood":"...","locations":[...],"photography_notes":"..."}'),
    ("essays", "delta_cycling",
     'Viết essay 1500 từ: "Đạp xe qua châu thổ" — 3 ngày cycling, đường đê, cầu khỉ, chó, trẻ em vẫy tay. JSON: {"title":"...","essay":"...","word_count":0,"mood":"...","locations":[...],"route_notes":"..."}'),
    ("essays", "fisherman_dawn",
     'Viết essay 1500 từ: "Ngư dân bình minh" — theo thuyền đánh cá sông, kỹ thuật, câu chuyện, 30 năm trên sông. JSON: {"title":"...","essay":"...","word_count":0,"mood":"...","locations":[...],"human_story":"..."}'),
    ("essays", "fruit_season",
     'Viết essay 1500 từ: "Mùa trái chín" — tháng 5-7, sầu riêng-măng cụt-chôm chôm, vườn, thương lái, hương. JSON: {"title":"...","essay":"...","word_count":0,"mood":"...","locations":[...],"seasonal_calendar":"..."}'),
    ("essays", "craft_village_last",
     'Viết essay 1500 từ: "Người thợ cuối cùng" — nghệ nhân già giữ nghề (gốm/chiếu/đan lát), truyền nghề, lo lắng. JSON: {"title":"...","essay":"...","word_count":0,"mood":"...","locations":[...],"human_story":"..."}'),
    ("essays", "teen_delta",
     'Viết essay 1500 từ: "Gen Z miền Tây" — thanh niên 18-22, TikTok, dream, xuống HCMC, về quê Tết, identity. JSON: {"title":"...","essay":"...","word_count":0,"mood":"...","social_context":"..."}'),
    ("essays", "monsoon_resilience",
     'Viết essay 1500 từ: "Sống chung với nước" — cách người ĐBSCL thích ứng: nhà sàn, đê bao, nuôi cá mùa lũ. JSON: {"title":"...","essay":"...","word_count":0,"mood":"...","locations":[...],"adaptation_stories":"..."}'),

    # FOOD STORIES (10)
    ("food_stories", "pho_origin_delta",
     'Viết food story 1000 từ: câu chuyện phở/hủ tiếu miền Tây — khác Hà Nội/Sài Gòn thế nào, nước lèo, topping, 5am bowls. JSON: {"title":"...","story":"...","dishes":[...],"where_to_eat":[...],"history":"..."}'),
    ("food_stories", "banh_collection",
     'Viết food story 1000 từ: bộ sưu tập BÁNH miền Tây 3 tỉnh — 30+ loại bánh, nguyên liệu, dịp ăn, cách làm. JSON: {"title":"...","story":"...","banhs":[...],"seasonal":"...","recipes_hint":"..."}'),
    ("food_stories", "mam_universe",
     'Viết food story 1000 từ: vũ trụ MẮM — mắm cá linh, mắm tép, mắm ba khía, mắm ruốc, mắm kho, science of umami. JSON: {"title":"...","story":"...","types":[...],"making_process":"...","pairing":"..."}'),
    ("food_stories", "coconut_100ways",
     'Viết food story 1000 từ: "100 cách dùng dừa" — nước, cơm, sữa, dầu, đường, rượu, kẹo, nata, giấm, than. JSON: {"title":"...","story":"...","products":[...],"recipes":[...],"innovation":"..."}'),
    ("food_stories", "market_breakfast",
     'Viết food story 1000 từ: "Ăn sáng ở chợ" — 5:30am chợ 3 tỉnh, món sáng, quán quen, giá, ritual. JSON: {"title":"...","story":"...","markets":[...],"dishes":[...],"tips":"..."}'),
    ("food_stories", "khmer_cuisine",
     'Viết food story 1000 từ: ẩm thực Khmer Nam Bộ — bún nước lèo, cà ri, lẩu mắm, bánh tét, gia vị riêng. JSON: {"title":"...","story":"...","dishes":[...],"ingredients":"...","where":"..."}'),
    ("food_stories", "dessert_paradise",
     'Viết food story 1000 từ: "Thiên đường chè & bánh ngọt" — chè bưởi, chè đậu, bánh da lợn, bánh pía, trái cây dầm. JSON: {"title":"...","story":"...","desserts":[...],"seasonal":"...","where":"..."}'),
    ("food_stories", "fermentation_journey",
     'Viết food story 1000 từ: "Hành trình lên men" — tham quan xưởng mắm, kẹo dừa, rượu, giấm, nước cốt dừa. JSON: {"title":"...","story":"...","stops":[...],"science":"...","buy":"..."}'),
    ("food_stories", "street_food_map",
     'Viết food story 1000 từ: "Bản đồ ăn vặt" — top 50 món ăn vặt 3 tỉnh, giá <20k, locations, time. JSON: {"title":"...","story":"...","snacks":[...],"map_notes":"...","budget":"..."}'),
    ("food_stories", "farm_to_table",
     'Viết food story 1000 từ: "Từ ruộng đến bàn ăn" — 1 ngày: thu hoạch lúa/rau/cá → chế biến → bữa ăn. JSON: {"title":"...","story":"...","experiences":[...],"where":"...","booking":"..."}'),

    # SEASONAL GUIDES (4)
    ("seasonal", "tet_delta",
     'Hướng dẫn Tết miền Tây 3 tỉnh: chuẩn bị, mâm cỗ, chợ hoa, du xuân, chùa, kiêng kỵ, 7 ngày chi tiết. JSON: {"title":"...","guide":"...","preparation":"...","days":[...],"food":"...","customs":"...","tips":"..."}'),
    ("seasonal", "ok_om_bok",
     'Hướng dẫn lễ Ok Om Bok Trà Vinh: ý nghĩa, đua ghe ngo, cúng trăng, cốm dẹp, lịch trình, transport. JSON: {"title":"...","guide":"...","meaning":"...","events":[...],"food":"...","logistics":"...","tips":"..."}'),
    ("seasonal", "flood_season_travel",
     'Hướng dẫn du lịch mùa nước nổi (8-11): đồng ngập, bông điên điển, cá linh, xuồng, routes, safety. JSON: {"title":"...","guide":"...","months":"...","experiences":[...],"routes":[...],"safety":"...","packing":"..."}'),
    ("seasonal", "dry_season_best",
     'Hướng dẫn du lịch mùa khô (12-4): weather, fruit season, events, best activities, logistics. JSON: {"title":"...","guide":"...","months":"...","highlights":[...],"itineraries":[...],"tips":"..."}'),

    # HUMAN INTEREST (6)
    ("human", "artisan_profiles",
     'Profile 10 nghệ nhân 3 tỉnh: tên (pseudonym OK), nghề, tuổi nghề, câu chuyện, triết lý, legacy. JSON: {"title":"...","profiles":[...],"common_themes":"...","preservation":"..."}'),
    ("human", "homestay_hosts",
     'Profile 8 chủ homestay 3 tỉnh: câu chuyện chuyển đổi, khó khăn, niềm vui, lời khuyên, unique selling. JSON: {"title":"...","profiles":[...],"insights":"...","booking_tips":"..."}'),
    ("human", "young_returnees",
     'Profile 6 người trẻ bỏ phố về quê 3 tỉnh: startup, nông nghiệp, du lịch, creative, motivation. JSON: {"title":"...","profiles":[...],"trends":"...","opportunities":"..."}'),
    ("human", "elderly_memories",
     'Lịch sử qua lời kể 5 người già (75+) 3 tỉnh: trước 1975, Đổi Mới, thay đổi landscape, wisdom. JSON: {"title":"...","stories":[...],"historical_context":"...","lessons":"..."}'),
    ("human", "river_people",
     'Profile 5 "người sông" — ngư dân, lái đò, chợ nổi, thợ lặn, cứu hộ: đời sống trên nước. JSON: {"title":"...","profiles":[...],"river_culture":"...","challenges":"..."}'),
    ("human", "food_masters",
     'Profile 8 "bậc thầy ẩm thực" 3 tỉnh: đầu bếp quán, bà bán chè, thợ kẹo dừa, chủ lò bánh tráng. JSON: {"title":"...","profiles":[...],"recipes_hint":"...","where_to_find":"..."}'),
]


def main():
    _cfg_io()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    llm = LLM()
    if not llm.ok:
        log("ERROR: LLM not configured"); return

    t0 = time.time()
    log(f"Model: {llm.model}")
    log(f"Total topics: {len(TOPICS)}")

    done = set()
    for fp in OUTPUT_DIR.glob("*.jsonl"):
        for r in read_jsonl(fp):
            done.add(r.get("key", ""))

    remaining = [(cat, key, prompt) for cat, key, prompt in TOPICS if key not in done]
    log(f"Remaining: {len(remaining)} (done: {len(done)})")

    for i, (cat, key, prompt) in enumerate(remaining):
        f = OUTPUT_DIR / f"{cat}.jsonl"
        t1 = time.time()
        log(f"[{i+1}/{len(remaining)}] {cat}/{key}...")
        r = llm.ask_json(sys=SYS, user=prompt, temp=0.4, max_tok=6000)
        elapsed = time.time() - t1
        if r:
            r["key"] = key; r["category"] = cat; r["ts"] = utc()
            append_jsonl(f, r)
            size = len(json.dumps(r, ensure_ascii=False))
            log(f"  ✓ {key} ({elapsed:.0f}s, {size} chars)")
        else:
            log(f"  ✗ {key} ({elapsed:.0f}s) — no valid JSON")
        log(f"  LLM: {llm.info()}")

    total_min = (time.time() - t0) / 60
    log(f"\n═══ DONE ({total_min:.1f}m) ═══")
    log(f"  FINAL: {llm.info()}")


if __name__ == "__main__":
    main()
