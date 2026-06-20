#!/usr/bin/env python3
"""MEGA EXPERT RUNNER — Sequential expert research, ONE call at a time.

Key insight: 9router proxy works best with 1 concurrent call + short prompts.
Each call takes ~60s and produces ~7-10KB of expert-level content.

Usage:
  python -u agent/scripts/mega_expert_run.py 2>&1
"""
from __future__ import annotations
import json, os, sys, time, warnings
warnings.filterwarnings("ignore", message=".*renamed.*ddgs.*")
from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = AGENT_DIR.parent
OUTPUT_DIR = AGENT_DIR / "data" / "mega_research" / "expert"

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

SYS = "Bạn là CHUYÊN GIA ĐẦU NGÀNH. Trả về JSON thuần túy. Viết tiếng Việt, siêu chi tiết."

# All topics — short prompts with explicit JSON structure
TOPICS = [
    # ANTHROPOLOGY
    ("anthropology", "viet_khmer_coexistence",
     'Phân tích nhân học văn hóa cộng sinh Việt-Khmer ở Trà Vinh: lịch sử giao thoa, identity, food creole, ritual syncretism, hôn nhân, ngôn ngữ. JSON: {"topic":"...","analysis":"...","key_findings":[...],"modern_changes":"...","sources":[...]}'),
    ("anthropology", "hoa_community_delta",
     'Phân tích nhân học cộng đồng Hoa ở VL-BT-TV: các đợt di cư, hội quán, thương mại, ẩm thực fusion, đồng hóa. JSON: {"topic":"...","waves":[...],"practices":[...],"food":[...],"assimilation":"...","sources":[...]}'),
    ("anthropology", "ritual_calendar_h1",
     'Lịch nghi lễ tháng 1-6 ở 3 tỉnh VL-BT-TV: Tết, Rằm, Chôl Chnăm Thmây, lễ Phật, Thanh Minh. JSON: {"topic":"...","months":[{"month":1,"events":[...]}...],"analysis":"..."}'),
    ("anthropology", "ritual_calendar_h2",
     'Lịch nghi lễ tháng 7-12 ở 3 tỉnh VL-BT-TV: Vu Lan, Ok Om Bok, Sene Đôn Ta, Giáng Sinh, lễ cúng đất. JSON: {"topic":"...","months":[{"month":7,"events":[...]}...],"analysis":"..."}'),
    ("anthropology", "craft_anthropology",
     'Nhân học kinh tế làng nghề 3 tỉnh: truyền nghề, giới, chuỗi giá trị, du lịch. JSON: {"topic":"...","villages":[...],"transmission":"...","gender":"...","tourism_impact":"...","sources":[...]}'),

    # ECOLOGY
    ("ecology_science", "mekong_ecosystem",
     'Sinh thái học hệ thống sông Mekong đoạn ĐBSCL: trophic levels, flood pulse, wetland services, biodiversity, loài nguy cấp, invasive species, đập thượng nguồn. JSON: {"topic":"...","analysis":"...","species_list":[...],"threats":[...],"conservation":"...","sources":[...]}'),
    ("ecology_science", "bird_ecology",
     'Điểu học vùng VL-BT-TV: species inventory, vườn cò/sân chim, migration, IBA, birding itinerary. JSON: {"topic":"...","species":[...],"breeding_sites":[...],"best_seasons":"...","itinerary":"...","sources":[...]}'),
    ("ecology_science", "fruit_ecology",
     'Thực vật học nông nghiệp cây ăn trái ĐBSCL: cultivar, soil-climate, pollination, phenology, agroforestry. JSON: {"topic":"...","fruits":[...],"terroir":"...","traditional_knowledge":"...","climate_impact":"...","sources":[...]}'),
    ("ecology_science", "coastal_ecosystem",
     'Sinh thái biển ven bờ TV-BT: rừng ngập mặn, mudflat, thủy sản, xói lở, blue carbon. JSON: {"topic":"...","mangrove_zones":[...],"fisheries":[...],"erosion":"...","carbon_potential":"...","sources":[...]}'),

    # FOOD SCIENCE
    ("food_science", "fermentation",
     'Khoa học lên men ẩm thực ĐBSCL: nước mắm, mắm cá, dưa cải, rượu nếp, kẹo dừa. JSON: {"topic":"...","processes":[...],"microbiology":"...","flavor_chemistry":"...","safety":"...","sources":[...]}'),
    ("food_science", "coconut_science",
     'Khoa học dừa Bến Tre: cultivar, nước dừa, sữa dừa, dầu dừa, nata de coco. JSON: {"topic":"...","varieties":[...],"products":[...],"health_claims":"...","sustainability":"...","sources":[...]}'),
    ("food_science", "fish_gastronomy",
     'Ẩm thực cá sông Mekong: tasting profiles, cooking chemistry, umami, seasonal, parasitology. JSON: {"topic":"...","species_profiles":[...],"cooking_science":"...","safety":"...","sources":[...]}'),
    ("food_science", "rice_science",
     'Khoa học gạo ĐBSCL: giống lúa, terroir, bánh, bún/hủ tiếu/phở, cháo. JSON: {"topic":"...","varieties":[...],"starch_science":"...","products":[...],"nutrition":"...","sources":[...]}'),

    # ARCHITECTURE
    ("architecture", "khmer_pagoda",
     'Kiến trúc chùa Khmer TV: typology, structural system, Naga symbolism, polychrome, spatial organization. JSON: {"topic":"...","elements":[...],"symbolism":"...","notable_examples":[...],"restoration":"...","sources":[...]}'),
    ("architecture", "french_colonial",
     'Kiến trúc thuộc địa Pháp 3 tỉnh: inventory, style, material, tropical adaptation, conservation. JSON: {"topic":"...","buildings":[...],"styles":"...","adaptation":"...","heritage_route":"...","sources":[...]}'),
    ("architecture", "vernacular",
     'Kiến trúc dân gian ĐBSCL: nhà sàn, nhà 3 gian, floating architecture, garden integration. JSON: {"topic":"...","typologies":[...],"materials":"...","thermal_comfort":"...","evolution":"...","sources":[...]}'),

    # ECONOMICS
    ("economics", "swot_vinh_long",
     'SWOT chi tiết du lịch Vĩnh Long: 10+ điểm mỗi mục, so sánh Cần Thơ, market size, forecast 5 năm. JSON: {"province":"Vinh Long","strengths":[...],"weaknesses":[...],"opportunities":[...],"threats":[...],"market_analysis":"...","forecast":"..."}'),
    ("economics", "swot_ben_tre",
     'SWOT chi tiết du lịch Bến Tre: coconut positioning, value chain, USP, segmentation. JSON: {"province":"Ben Tre","strengths":[...],"weaknesses":[...],"opportunities":[...],"threats":[...],"positioning":"...","forecast":"..."}'),
    ("economics", "swot_tra_vinh",
     'SWOT chi tiết du lịch Trà Vinh: Khmer culture positioning, niche vs mass, heritage economics. JSON: {"province":"Tra Vinh","strengths":[...],"weaknesses":[...],"opportunities":[...],"threats":[...],"positioning":"...","forecast":"..."}'),
    ("economics", "value_chain",
     'Value chain du lịch ĐBSCL 3 tỉnh: marketing → booking → transport → accommodation → food → activities. JSON: {"topic":"...","chain_links":[...],"local_retention":"...","tour_vs_FIT":"...","recommendations":[...]}'),
    ("economics", "digital_tourism",
     'Kinh tế du lịch số 3 tỉnh: SEO, social media, OTA, review economy, Google Maps, AI. JSON: {"topic":"...","digital_landscape":"...","platforms":[...],"recommendations":[...],"sources":[...]}'),

    # HISTORY
    ("history_academic", "pre_colonial",
     'Sử học trước thuộc địa Pháp: Thủy Chân Lạp, nam tiến Nguyễn, khai phá kênh rạch, 3 dân tộc. JSON: {"topic":"...","periods":[...],"key_events":[...],"primary_sources":[...],"analysis":"..."}'),
    ("history_academic", "colonial_period",
     'Sử học thời Pháp ở 3 tỉnh: hạ tầng, rubber, rice export, missions, kháng chiến. JSON: {"topic":"...","periods":[...],"infrastructure":[...],"resistance":"...","legacy":"...","sources":[...]}'),
    ("history_academic", "war_period",
     'Sử học 3 tỉnh 1945-1975: chiến lược, căn cứ, Tết Mậu Thân, dân thường, herbicide, hậu 1975. JSON: {"topic":"...","key_events":[...],"impact":"...","reconciliation":"...","sources":[...]}'),
    ("history_academic", "economic_history",
     'Sử học kinh tế 3 tỉnh: tự cung → xuất khẩu gạo → tập thể → Đổi Mới → WTO. JSON: {"topic":"...","periods":[...],"land_patterns":"...","market_evolution":"...","sources":[...]}'),
    ("history_academic", "religious_history",
     'Sử học tôn giáo 3 tỉnh: Theravada, Đại thừa, Công giáo, Cao Đài, Hòa Hảo. JSON: {"topic":"...","traditions":[...],"syncretism":"...","state_relations":"...","sources":[...]}'),

    # GEOGRAPHY
    ("geography_deep", "hydrology",
     'Thủy văn học sông Tiền, Hậu, Cổ Chiên ở 3 tỉnh: lưu lượng, bồi lắng, xâm nhập mặn, triều. JSON: {"topic":"...","rivers":[...],"seasonal_patterns":"...","salt_intrusion":"...","projections":"...","sources":[...]}'),
    ("geography_deep", "geomorphology",
     'Địa mạo ĐBSCL 3 tỉnh: cù lao, giồng cát, bãi bồi, sụt lún, xói lở. JSON: {"topic":"...","landforms":[...],"processes":"...","subsidence":"...","coastal_retreat":"...","sources":[...]}'),
    ("geography_deep", "climate_micro",
     'Khí hậu vi mô 3 tỉnh: nội đồng vs ven biển, heat island, cực đoan, projections 2030-2050. JSON: {"topic":"...","zones":[...],"extremes":"...","projections":"...","adaptation":"...","sources":[...]}'),
    ("geography_deep", "soil_science",
     'Thổ nhưỡng 3 tỉnh Vĩnh Long, Bến Tre, Trà Vinh: phù sa sông Tiền/Hậu/Cổ Chiên, đất phèn, đất mặn ven biển, đất cát giồng, phân loại FAO/WRB, suitability cây ăn trái/lúa/thủy sản. JSON: {"topic":"...","soil_types":[...],"nutrient_profiles":"...","degradation":"...","sources":[...]}'),

    # MUSIC
    ("music", "don_ca_tai_tu",
     'Âm nhạc học đờn ca tài tử UNESCO: 20 bài bản tổ, điệu thức, nhạc cụ, tuning, improvisation. JSON: {"topic":"...","repertoire":[...],"instruments":[...],"theory":"...","performers_3tinh":[...],"sources":[...]}'),
    ("music", "khmer_music",
     'Âm nhạc Khmer Nam Bộ: nhạc ngũ âm, pinpeat, dù kê, rô băm, scale, instruments, revival. JSON: {"topic":"...","genres":[...],"instruments":[...],"sacred_vs_secular":"...","endangered":"...","sources":[...]}'),
    ("music", "cai_luong",
     'Âm nhạc học cải lương: từ tài tử → cải lương, vọng cổ, Western integration, troupes 3 tỉnh. JSON: {"topic":"...","evolution":"...","vocal_techniques":"...","famous_troupes":[...],"decline_revival":"...","sources":[...]}'),

    # SOCIOLOGY + LINGUISTICS + RELIGION
    ("sociology", "rural_transformation",
     'Xã hội học nông thôn 3 tỉnh: đô thị hóa, youth migration, remittance, aging, social media. JSON: {"topic":"...","trends":[...],"impact":"...","case_studies":[...],"sources":[...]}'),
    ("sociology", "tourism_sociology",
     'Xã hội học du lịch 3 tỉnh: host-guest, commodification, empowerment, pro-poor tourism. JSON: {"topic":"...","dynamics":"...","power_relations":"...","community_attitudes":"...","sources":[...]}'),
    ("linguistics", "dialect_study",
     'Ngôn ngữ học phương ngữ miền Tây: phonology, lexicon, Khmer đang mất, Hoa loanwords, toponymy. JSON: {"topic":"...","features":[...],"endangered":"...","etymology":[...],"sources":[...]}'),
    ("religion", "syncretism",
     'Tôn giáo học syncretism 3 tỉnh: Theravada + Mahayana + folk + Confucianism. JSON: {"topic":"...","case_studies":[...],"ritual_specialists":"...","sacred_geography":"...","sources":[...]}'),

    # AGRICULTURE + TOURISM STRATEGY
    ("agriculture", "ocop_deep",
     'Nông học & kinh tế OCOP 3 tỉnh: tiêu chí, sản phẩm nổi bật, GAP/GMP, so sánh OTOP. JSON: {"topic":"...","provinces":[...],"top_products":[...],"challenges":"...","comparison":"...","sources":[...]}'),
    ("agriculture", "aquaculture",
     'Thủy sản 3 tỉnh: tôm sú, cá tra, nghêu, technology, environmental impact, certification. JSON: {"topic":"...","species":[...],"production":"...","technology":"...","sustainability":"...","sources":[...]}'),
    ("tourism_strategy", "positioning",
     'Chiến lược định vị du lịch: Porter Five Forces, Blue Ocean cho 3 tỉnh, target segments. JSON: {"topic":"...","analysis":"...","segments":[...],"brand_architecture":"...","recommendations":[...]}'),
    ("tourism_strategy", "sustainable",
     'Du lịch bền vững 3 tỉnh: GSTC, carbon footprint, waste, community-based, eco-certification. JSON: {"topic":"...","current_state":"...","gaps":[...],"models":[...],"financing":"...","sources":[...]}'),

    # SPECIAL
    ("photography", "guide",
     'Nhiếp ảnh chuyên nghiệp 3 tỉnh: golden/blue hour, composition sông nước, portrait ethics, drone, gear. JSON: {"topic":"...","locations":[...],"timing":"...","techniques":"...","regulations":"..."}'),
    ("special", "wellness",
     'Du lịch sức khỏe 3 tỉnh: spa truyền thống, yoga, meditation chùa, forest bathing, digital detox. JSON: {"topic":"...","experiences":[...],"locations":[...],"potential":"...","recommendations":[...]}'),
    ("special", "nightlife",
     'Đời sống đêm 3 tỉnh: chợ đêm, quán, live music, karaoke, river cruise, street food. JSON: {"topic":"...","by_province":[...],"safety":"...","romantic_spots":[...],"recommendations":[...]}'),
    ("special", "children",
     'Du lịch trẻ em 3 tỉnh: educational, age-appropriate, safety, stroller, rainy day. JSON: {"topic":"...","by_age_group":[...],"activities":[...],"safety":"...","recommendations":[...]}'),
    ("special", "accessibility",
     'Du lịch tiếp cận 3 tỉnh: wheelchair, elderly, hearing/vision, medical, dietary. JSON: {"topic":"...","audit":[...],"itineraries":[...],"medical_facilities":[...],"recommendations":[...]}'),
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

    # Build done set across all files
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
        r = llm.ask_json(sys=SYS, user=prompt, temp=0.3, max_tok=6000)
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
