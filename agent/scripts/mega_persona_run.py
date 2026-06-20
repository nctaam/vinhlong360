#!/usr/bin/env python3
"""MEGA PERSONA RUNNER — Sequential persona research, ONE call at a time.

Usage:
  python -u agent/scripts/mega_persona_run.py 2>&1
"""
from __future__ import annotations
import json, os, sys, time, warnings
warnings.filterwarnings("ignore", message=".*renamed.*ddgs.*")
from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = AGENT_DIR.parent
OUTPUT_DIR = AGENT_DIR / "data" / "mega_research" / "persona"

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

SYS_J = "Bạn là UX RESEARCHER + TRAVEL CONSULTANT. Trả về JSON thuần túy. Viết tiếng Việt, siêu chi tiết."
SYS_C = "Bạn là CHUYÊN GIA SO SÁNH ĐA CHIỀU. Trả về JSON thuần túy. Trung lập, dựa trên dữ liệu."
SYS_G = "Bạn là TRAVEL INSIDER địa phương. Trả về JSON thuần túy. Chi tiết cụ thể, không bịa."
SYS_P = "Bạn là CHUYÊN GIA ĐỊA PHƯƠNG CẤP CAO. Trả về JSON thuần túy. Siêu chi tiết encyclopedia."

TOPICS = [
    # PERSONAS (30)
    ("journeys", SYS_J, "solo_backpacker", 'Hành trình backpacker 25 tuổi, 500k/ngày, 5 ngày VL-BT-TV: lịch trình từng giờ, homestay, vỉa hè, tips. JSON: {"persona":"...","days":[...],"budget":"...","tips":[...],"emotional_journey":[...]}'),
    ("journeys", SYS_J, "couple_honeymoon", 'Hành trình honeymoon 28 tuổi, 3tr/ngày, 4 ngày: romantic, riêng tư, ảnh đẹp. JSON: {"persona":"...","days":[...],"budget":"...","romantic_spots":[...],"surprise_ideas":[...]}'),
    ("journeys", SYS_J, "family_3gen", 'Gia đình 3 thế hệ (ông bà 70+, bố mẹ 45, con 10+15), 3 ngày ô tô, 5tr/ngày. JSON: {"persona":"...","days":[...],"accessibility":"...","tips":[...],"budget":"..."}'),
    ("journeys", SYS_J, "korean_tourist", 'Du khách Hàn 35 tuổi, 2 ngày from HCMC, food+culture+photo, không tiếng Việt. JSON: {"persona":"...","days":[...],"food_tips":"...","communication":"...","kpop_connections":"..."}'),
    ("journeys", SYS_J, "japanese_retiree", 'Cặp Nhật đã nghỉ hưu 65, 3 ngày, lịch sử+thủ công+vườn, quality. JSON: {"persona":"...","days":[...],"craft_parallels":"...","history_connections":"...","tips":[...]}'),
    ("journeys", SYS_J, "french_historian", 'Nhà sử học Pháp 50, 5 ngày, dấu ấn thuộc địa, kiến trúc, kênh đào, tài liệu. JSON: {"persona":"...","days":[...],"colonial_sites":[...],"archives":"...","tips":[...]}'),
    ("journeys", SYS_J, "photographer_pro", 'Nhiếp ảnh gia 40, 4 ngày, landscape+portrait: golden hour, drone, local subjects. JSON: {"persona":"...","days":[...],"golden_hour_map":"...","gear":"...","locations":[...]}'),
    ("journeys", SYS_J, "digital_nomad", 'Digital nomad 30, 2 tuần, WiFi, cafe, co-working, 700k/ngày. JSON: {"persona":"...","accommodation":"...","work_spots":[...],"community":"...","monthly_costs":"..."}'),
    ("journeys", SYS_J, "food_blogger", 'Food blogger 500k followers, 3 ngày, quay video, tất cả đặc sản. JSON: {"persona":"...","days":[...],"food_map":[...],"filming_tips":"...","stories":[...]}'),
    ("journeys", SYS_J, "birdwatcher", 'Birder Úc chuyên nghiệp, 5 ngày, sếu đầu đỏ, sân chim, vườn cò. JSON: {"persona":"...","days":[...],"species_list":[...],"best_hides":"...","ethics":"..."}'),
    ("journeys", SYS_J, "cycling_group", 'Nhóm 4 cyclist, 3 ngày, 50-80km/ngày, scenic routes. JSON: {"persona":"...","routes":[...],"road_conditions":"...","repair_shops":"...","safety":"..."}'),
    ("journeys", SYS_J, "muslim_traveler", 'Du khách Muslim Malaysia 30, 3 ngày: halal, prayer, modest. JSON: {"persona":"...","days":[...],"halal_food":[...],"prayer_spaces":"...","cultural_tips":"..."}'),
    ("journeys", SYS_J, "elderly_nostalgia", 'Phụ nữ 68, đi một mình, 3 ngày, từng sống VL trước 1975. JSON: {"persona":"...","days":[...],"memory_spots":"...","accessible_transport":"...","health_facilities":"..."}'),
    ("journeys", SYS_J, "motorbike_adventure", 'Nhóm 2 tay lái Sài Gòn, 4 ngày, Honda Winner, off-road. JSON: {"persona":"...","routes":[...],"petrol":"...","camping":"...","mechanic_shops":"..."}'),
    ("journeys", SYS_J, "student_group", 'Nhóm 20 SV HCMC, fieldtrip 2 ngày, 300k/người/ngày. JSON: {"persona":"...","days":[...],"educational":[...],"team_building":"...","logistics":"..."}'),
    ("journeys", SYS_J, "eco_volunteer", 'Tình nguyện viên môi trường 25, 1 tuần, trồng rừng, clean-up. JSON: {"persona":"...","days":[...],"programs":[...],"ngo_contacts":"...","impact":"..."}'),
    ("journeys", SYS_J, "culinary_student", 'SV ẩm thực 22, 5 ngày, học nấu từ local cooks, market tour 5am. JSON: {"persona":"...","days":[...],"classes":[...],"ingredients":"...","recipes":"..."}'),
    ("journeys", SYS_J, "buddhist_pilgrim", 'Phật tử 55, 4 ngày, chùa Khmer + chùa Việt, meditation. JSON: {"persona":"...","days":[...],"temple_route":"...","etiquette":"...","vegetarian_food":"..."}'),
    ("journeys", SYS_J, "luxury_yacht", 'Nhóm 6, thuê thuyền riêng, 3 ngày sông, budget không giới hạn. JSON: {"persona":"...","days":[...],"yacht_options":"...","vip_experiences":[...],"concierge":"..."}'),
    ("journeys", SYS_J, "teen_first_trip", 'Thiếu niên 18, solo đầu tiên, 2 ngày, 400k/ngày, Instagram. JSON: {"persona":"...","days":[...],"safety":"...","social_media_spots":[...],"making_friends":"..."}'),

    # COMPARISONS (15)
    ("comparisons", SYS_C, "vl_vs_bt_vs_tv", 'So sánh tổng thể VL vs BT vs TV: 30 tiêu chí, scoring 1-10. JSON: {"comparison":"...","criteria":[...],"scores":{"VL":{},"BT":{},"TV":{}},"summary":"..."}'),
    ("comparisons", SYS_C, "vs_cantho", 'So sánh cluster VL+BT+TV vs Cần Thơ du lịch: khách, doanh thu, nightlife, F&B. JSON: {"comparison":"...","dimensions":[...],"swot_each":"...","summary":"..."}'),
    ("comparisons", SYS_C, "vs_dongthap_angiang", 'So sánh VL+BT+TV vs Đồng Tháp+An Giang: eco, heritage, food, homestay. JSON: {"comparison":"...","dimensions":[...],"scores":"...","summary":"..."}'),
    ("comparisons", SYS_C, "district_ranking_vl", 'Ranking huyện/thị Vĩnh Long theo du lịch: điểm đến, food, accommodation, USP. JSON: {"province":"VL","districts":[...],"methodology":"...","recommendations":"..."}'),
    ("comparisons", SYS_C, "district_ranking_bt", 'Ranking huyện/thị Bến Tre theo du lịch: dừa, homestay, craft, food. JSON: {"province":"BT","districts":[...],"methodology":"...","recommendations":"..."}'),
    ("comparisons", SYS_C, "district_ranking_tv", 'Ranking huyện/thị Trà Vinh theo du lịch: Khmer, pagoda, beach, food. JSON: {"province":"TV","districts":[...],"methodology":"...","recommendations":"..."}'),
    ("comparisons", SYS_C, "food_compare", 'So sánh ẩm thực 3 tỉnh: signature dishes, shared dishes, street food, cooking class. JSON: {"comparison":"...","by_province":[...],"shared_dishes":[...],"unique_dishes":[...],"food_tour":"..."}'),
    ("comparisons", SYS_C, "accommodation_benchmark", 'Benchmark chỗ ở 3 tỉnh: hotel, homestay, resort, unique stays, Booking rating. JSON: {"comparison":"...","by_province":[...],"unique_stays":[...],"capacity":"..."}'),
    ("comparisons", SYS_C, "seasonality_matrix", 'Ma trận mùa vụ 12 tháng x 3 tỉnh: weather, events, fruit, price, crowd. JSON: {"comparison":"...","matrix":[...],"best_months":"...","avoid":"..."}'),
    ("comparisons", SYS_C, "digital_readiness", 'Đánh giá số hóa du lịch 3 tỉnh: Maps, TripAdvisor, Booking, social, QR, WiFi. JSON: {"comparison":"...","by_province":[...],"gaps":"...","recommendations":"..."}'),

    # HIDDEN GEMS (15)
    ("hidden_gems", SYS_G, "vl_hidden_food", '20 quán ăn bí mật Vĩnh Long chỉ local biết: tên, khu vực, món, giá, giờ. JSON: {"province":"VL","gems":[...],"tips":"..."}'),
    ("hidden_gems", SYS_G, "bt_hidden_food", '20 quán ăn bí mật Bến Tre chỉ local biết: tên, khu vực, món, giá, giờ. JSON: {"province":"BT","gems":[...],"tips":"..."}'),
    ("hidden_gems", SYS_G, "tv_hidden_food", '20 quán ăn bí mật Trà Vinh chỉ local biết: tên, khu vực, món, giá, giờ. JSON: {"province":"TV","gems":[...],"tips":"..."}'),
    ("hidden_gems", SYS_G, "vl_secret_spots", '15 địa điểm bí mật Vĩnh Long: locals picnic, góc sông, cây cổ thụ. JSON: {"province":"VL","spots":[...],"access":"..."}'),
    ("hidden_gems", SYS_G, "bt_secret_spots", '15 địa điểm bí mật Bến Tre: bãi dừa vắng, cù lao nhỏ, đường mòn. JSON: {"province":"BT","spots":[...],"access":"..."}'),
    ("hidden_gems", SYS_G, "tv_secret_spots", '15 địa điểm bí mật Trà Vinh: chùa Khmer nhỏ, bãi biển vắng, rừng tràm. JSON: {"province":"TV","spots":[...],"access":"..."}'),
    ("hidden_gems", SYS_G, "local_tips_transport", '30 mẹo giao thông local 3 tỉnh: đò ngang, phà, xe buýt, grab, thuê xe, tránh kẹt. JSON: {"tips":[...],"by_province":"..."}'),
    ("hidden_gems", SYS_G, "local_tips_money", 'Mẹo tiền bạc du khách: ATM, thẻ, mặc cả, giá local, tip culture, mobile pay. JSON: {"tips":[...],"by_province":"..."}'),
    ("hidden_gems", SYS_G, "market_guide", 'Hướng dẫn chợ hoàn chỉnh 3 tỉnh: giờ, section, món, mặc cả, vệ sinh, parking. JSON: {"markets":[...],"tips":"...","seasonal":"..."}'),
    ("hidden_gems", SYS_G, "coffee_guide", 'Bản đồ cà phê 3 tỉnh: WiFi, ổ cắm, atmosphere, specialty, giá, work-friendly. JSON: {"cafes":[...],"by_province":"...","best_for":"..."}'),
    ("hidden_gems", SYS_G, "free_experiences", '30 trải nghiệm miễn phí tuyệt vời 3 tỉnh: chùa, công viên, sunset, market. JSON: {"experiences":[...],"by_province":"..."}'),

    # PROVINCE PROFILES (3)
    ("profiles", SYS_P, "vl_megaprofile", 'Hồ sơ siêu chi tiết VĨNH LONG: tổng quan, lịch sử, hành chính, kinh tế, văn hóa, ẩm thực top 30, du lịch top 20, hạ tầng, nhân vật, tương lai. JSON: {"province":"Vinh Long","overview":"...","history":"...","districts":[...],"economy":"...","culture":"...","food":[...],"tourism":[...],"infrastructure":"...","famous_people":[...],"future":"..."}'),
    ("profiles", SYS_P, "bt_megaprofile", 'Hồ sơ siêu chi tiết BẾN TRE xứ dừa: tổng quan, Đồng Khởi, coconut value chain, ẩm thực dừa, du lịch, cầu Rạch Miễu 2, biến đổi khí hậu. JSON: {"province":"Ben Tre","overview":"...","history":"...","coconut":"...","food":[...],"tourism":[...],"infrastructure":"...","climate_change":"...","future":"..."}'),
    ("profiles", SYS_P, "tv_megaprofile", 'Hồ sơ siêu chi tiết TRÀ VINH vùng Khmer: Kinh-Khmer-Hoa %, 142 chùa, lễ hội, nhạc ngũ âm, ẩm thực fusion, khu kinh tế Định An. JSON: {"province":"Tra Vinh","overview":"...","demographics":"...","khmer_culture":"...","food":[...],"tourism":[...],"economic_zone":"...","future":"..."}'),
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

    remaining = [(cat, sys_p, key, prompt) for cat, sys_p, key, prompt in TOPICS if key not in done]
    log(f"Remaining: {len(remaining)} (done: {len(done)})")

    for i, (cat, sys_p, key, prompt) in enumerate(remaining):
        f = OUTPUT_DIR / f"{cat}.jsonl"
        t1 = time.time()
        log(f"[{i+1}/{len(remaining)}] {cat}/{key}...")
        r = llm.ask_json(sys=sys_p, user=prompt, temp=0.3, max_tok=6000)
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
