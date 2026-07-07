#!/usr/bin/env python3
"""MEGA ITINERARY RUNNER — Chi tiết lịch trình du lịch mọi kiểu, mọi thời lượng.

50+ lịch trình siêu chi tiết: từng giờ, từng bữa ăn, từng điểm dừng,
budget, transport, tips insider.

SEQUENTIAL — one API call at a time.
Resume-safe via JSONL done set.

Usage:
  python -u agent/scripts/mega_itinerary_run.py 2>&1
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
OUTPUT_DIR = AGENT_DIR / "data" / "mega_research" / "itineraries"

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

SYS = "Bạn là TRAVEL PLANNER chuyên nghiệp hàng đầu Việt Nam. Trả về JSON thuần túy. Viết tiếng Việt, siêu chi tiết từng giờ."

TOPICS = [
    # === VĨNH LONG ===
    ("vinh_long", "vl_1day_classic",
     'Lịch trình 1 NGÀY Vĩnh Long classic: 6am-9pm, từng giờ, ăn sáng-trưa-chiều-tối, di chuyển, giá. JSON: {"title":"...","duration":"1 ngày","province":"Vĩnh Long","schedule":[{"time":"06:00","activity":"...","location":"...","cost":"...","tips":"..."}...],"total_budget":"...","transport":"...","packing":"..."}'),
    ("vinh_long", "vl_2day_deep",
     'Lịch trình 2 NGÀY Vĩnh Long deep: cù lao, vườn trái cây, chợ, làng nghề, homestay. Từng giờ. JSON: {"title":"...","duration":"2 ngày","days":[{"day":1,"schedule":[...]},{"day":2,"schedule":[...]}],"accommodation":"...","total_budget":"..."}'),
    ("vinh_long", "vl_food_tour",
     'Lịch trình FOOD TOUR 1 ngày Vĩnh Long: 10+ quán, từ 5am phở → 10pm chè. Từng món, giá, địa chỉ. JSON: {"title":"...","type":"food_tour","stops":[{"time":"...","place":"...","dish":"...","price":"...","tips":"..."}...],"total_food_cost":"..."}'),

    # === BẾN TRE ===
    ("ben_tre", "bt_1day_coconut",
     'Lịch trình 1 NGÀY Bến Tre dừa: xưởng kẹo, vườn dừa, xuồng kênh rạch, ẩm thực dừa. Từng giờ. JSON: {"title":"...","duration":"1 ngày","province":"Bến Tre","schedule":[...],"total_budget":"...","transport":"..."}'),
    ("ben_tre", "bt_2day_islands",
     'Lịch trình 2 NGÀY Bến Tre cù lao: Phụng, Quy, Ốc, Cồn Tiên. Xuồng, xe đạp, homestay. JSON: {"title":"...","duration":"2 ngày","days":[...],"accommodation":"...","total_budget":"..."}'),
    ("ben_tre", "bt_food_tour",
     'Lịch trình FOOD TOUR 1 ngày Bến Tre: đặc sản dừa, hải sản Bình Đại, bánh, mắm. 10+ điểm. JSON: {"title":"...","type":"food_tour","stops":[...],"total_food_cost":"..."}'),
    ("ben_tre", "bt_3day_coast",
     'Lịch trình 3 NGÀY Bến Tre ven biển: Bình Đại, Ba Tri, Thạnh Phú, biển, rừng ngập mặn, hải sản. JSON: {"title":"...","duration":"3 ngày","days":[...],"accommodation":"...","total_budget":"..."}'),

    # === TRÀ VINH ===
    ("tra_vinh", "tv_1day_khmer",
     'Lịch trình 1 NGÀY Trà Vinh Khmer: 5 chùa Khmer, bún nước lèo, ao bà Om, nhạc ngũ âm. Từng giờ. JSON: {"title":"...","duration":"1 ngày","province":"Trà Vinh","schedule":[...],"total_budget":"..."}'),
    ("tra_vinh", "tv_2day_culture",
     'Lịch trình 2 NGÀY Trà Vinh văn hóa: chùa Khmer, nhà cổ, chợ, biển Ba Động, làng Khmer. JSON: {"title":"...","duration":"2 ngày","days":[...],"accommodation":"...","total_budget":"..."}'),
    ("tra_vinh", "tv_food_tour",
     'Lịch trình FOOD TOUR 1 ngày Trà Vinh: bún nước lèo, bánh canh Bến Có, cà ri Khmer, chè. 10+ điểm. JSON: {"title":"...","type":"food_tour","stops":[...],"total_food_cost":"..."}'),
    ("tra_vinh", "tv_3day_complete",
     'Lịch trình 3 NGÀY Trà Vinh toàn diện: TP TV, Cầu Kè, Trà Cú, Duyên Hải. Khmer + biển + rừng. JSON: {"title":"...","duration":"3 ngày","days":[...],"accommodation":"...","total_budget":"..."}'),

    # === LIÊN TỈNH ===
    ("combined", "3tinh_3day",
     'Lịch trình 3 NGÀY 3 tỉnh VL-BT-TV: 1 ngày mỗi tỉnh, highlights, di chuyển liên tỉnh. Từng giờ. JSON: {"title":"...","duration":"3 ngày","days":[{"day":1,"province":"VL","schedule":[...]},{"day":2,"province":"BT","schedule":[...]},{"day":3,"province":"TV","schedule":[...]}],"transport":"...","total_budget":"..."}'),
    ("combined", "3tinh_5day",
     'Lịch trình 5 NGÀY 3 tỉnh VL-BT-TV: deep, VL 2 ngày + BT 2 ngày + TV 1 ngày. Homestay, food tour. JSON: {"title":"...","duration":"5 ngày","days":[...],"accommodation":[...],"total_budget":"..."}'),
    ("combined", "3tinh_7day",
     'Lịch trình 7 NGÀY 3 tỉnh VL-BT-TV: ultra-deep, mỗi tỉnh 2+ ngày, off-beaten-path. JSON: {"title":"...","duration":"7 ngày","days":[...],"accommodation":[...],"total_budget":"...","insider_tips":[...]}'),
    ("combined", "food_grand_tour",
     'Lịch trình FOOD GRAND TOUR 5 ngày 3 tỉnh: 50+ món, từng bữa, markets, street food, fine dining. JSON: {"title":"...","duration":"5 ngày","days":[...],"total_dishes":0,"total_food_cost":"..."}'),
    ("combined", "heritage_trail",
     'Lịch trình DI SẢN 4 ngày 3 tỉnh: chùa, nhà cổ, kiến trúc Pháp, đình, miếu, làng nghề. JSON: {"title":"...","duration":"4 ngày","days":[...],"heritage_sites":[...],"total_budget":"..."}'),
    ("combined", "nature_eco",
     'Lịch trình ECO 4 ngày: sân chim, rừng ngập mặn, vườn trái cây, đồng lúa, sông, biển. JSON: {"title":"...","duration":"4 ngày","days":[...],"wildlife_checklist":[...],"eco_tips":"..."}'),
    ("combined", "photo_expedition",
     'Lịch trình NHIẾP ẢNH 5 ngày: golden hour, blue hour, drone spots, portrait, landscape. JSON: {"title":"...","duration":"5 ngày","days":[...],"gear_checklist":"...","best_shots":[...]}'),

    # === THEO ĐỐI TƯỢNG ===
    ("themed", "budget_3day",
     'Lịch trình TIẾT KIỆM 3 ngày 3 tỉnh: <500k/ngày, xe buýt, homestay rẻ, ăn chợ. Từng giờ + giá. JSON: {"title":"...","budget_cap":"500k/ngày","days":[...],"money_tips":[...],"total":"..."}'),
    ("themed", "luxury_3day",
     'Lịch trình SANG TRỌNG 3 ngày: resort, thuyền riêng, fine dining, spa, 5tr+/ngày. JSON: {"title":"...","budget":"5tr+/ngày","days":[...],"vip_experiences":[...],"concierge":"..."}'),
    ("themed", "family_kids_3day",
     'Lịch trình GIA ĐÌNH + TRẺ EM 3 ngày: safe, fun, educational, stroller-friendly, nap time. JSON: {"title":"...","ages":"3-12","days":[...],"kid_friendly":[...],"safety":"...","packing":"..."}'),
    ("themed", "elderly_2day",
     'Lịch trình NGƯỜI LỚN TUỔI 2 ngày: nhẹ nhàng, accessible, nghỉ nhiều, y tế gần, nostalgia. JSON: {"title":"...","pace":"slow","days":[...],"accessibility":"...","medical":"..."}'),
    ("themed", "couple_romantic_3day",
     'Lịch trình LÃNG MẠN 3 ngày: sunset, candlelight, private boat, garden, đẹp. JSON: {"title":"...","mood":"romantic","days":[...],"surprise_ideas":[...],"photography":"..."}'),
    ("themed", "solo_female_3day",
     'Lịch trình NỮ ĐI MỘT MÌNH 3 ngày: an toàn, social, empowering, community, tips. JSON: {"title":"...","safety_focus":true,"days":[...],"safety_tips":[...],"social_spots":[...]}'),
    ("themed", "student_weekend",
     'Lịch trình SINH VIÊN cuối tuần 2 ngày: <300k/ngày, vui, Instagram, nhóm 4-6 người. JSON: {"title":"...","budget":"<300k/ngày","days":[...],"group_tips":"...","instagram_spots":[...]}'),
    ("themed", "cycling_3day",
     'Lịch trình XE ĐẠP 3 ngày: routes 40-60km/ngày, flat terrain, scenic, repair, accommodation. JSON: {"title":"...","total_km":0,"days":[{"day":1,"route":"...","distance":"...","elevation":"...","stops":[...]}...],"gear":"...","safety":"..."}'),
    ("themed", "motorbike_4day",
     'Lịch trình XE MÁY 4 ngày 3 tỉnh: routes, petrol, scenic detours, mechanic, camping option. JSON: {"title":"...","total_km":0,"days":[...],"road_conditions":"...","petrol_stations":[...],"safety":"..."}'),
    ("themed", "fishing_2day",
     'Lịch trình CÂU CÁ 2 ngày: spots, mùa, loại cá, gear, guide, cook-your-catch. JSON: {"title":"...","days":[...],"species":[...],"gear":"...","guides":[...],"cooking":"..."}'),

    # === THEO MÙA ===
    ("seasonal_itin", "tet_5day",
     'Lịch trình TẾT 5 ngày (late Jan/Feb): chợ hoa, đình chùa, mâm cỗ, du xuân, kiêng kỵ. JSON: {"title":"...","season":"Tết","days":[...],"customs":"...","food":"...","tips":"..."}'),
    ("seasonal_itin", "summer_7day",
     'Lịch trình HÈ 7 ngày (Jun-Aug): trái cây, mưa chiều, activities indoor/outdoor, trẻ em. JSON: {"title":"...","season":"hè","days":[...],"fruit_calendar":"...","rain_plan":"..."}'),
    ("seasonal_itin", "flood_season_3day",
     'Lịch trình MÙA NƯỚC NỔI 3 ngày (Sep-Nov): đồng ngập, xuồng, bông điên điển, cá linh. JSON: {"title":"...","season":"mùa nước nổi","days":[...],"unique_experiences":[...],"safety":"..."}'),
    ("seasonal_itin", "dry_weekend",
     'Lịch trình MÙA KHÔ cuối tuần (Dec-Apr): weather perfect, outdoor, camping, stargazing. JSON: {"title":"...","season":"mùa khô","days":[...],"outdoor_activities":[...],"camping":"..."}'),
    ("seasonal_itin", "ok_om_bok_3day",
     'Lịch trình LỄ OK OM BOK 3 ngày TV (Oct/Nov): đua ghe ngo, cúng trăng, lễ hội, ẩm thực. JSON: {"title":"...","festival":"Ok Om Bok","days":[...],"events":[...],"food":"...","logistics":"..."}'),

    # === TỪ SÀI GÒN ===
    ("from_hcmc", "hcmc_vl_daytrip",
     'Day trip Sài Gòn → Vĩnh Long: xe 6am, về 9pm, tối ưu thời gian, highlights. JSON: {"title":"...","from":"HCMC","to":"VL","transport":[...],"schedule":[...],"total_budget":"..."}'),
    ("from_hcmc", "hcmc_bt_daytrip",
     'Day trip Sài Gòn → Bến Tre: Mỹ Thuận bridge, coconut tour, về tối. JSON: {"title":"...","from":"HCMC","to":"BT","transport":[...],"schedule":[...],"total_budget":"..."}'),
    ("from_hcmc", "hcmc_3tinh_3day",
     'Sài Gòn → 3 tỉnh 3 ngày: thuê xe 7 chỗ, 4 người, tối ưu route, về HCMC. JSON: {"title":"...","from":"HCMC","transport":"xe thuê","people":4,"days":[...],"total_budget":"..."}'),
    ("from_hcmc", "hcmc_weekend_escape",
     'Weekend escape Sài Gòn → VL hoặc BT: Thứ 6 tối đi, CN tối về, relax, disconnect. JSON: {"title":"...","duration":"2 ngày 1 đêm","options":[{"dest":"VL","plan":"..."},{"dest":"BT","plan":"..."}],"transport":"..."}'),

    # === NICHE ===
    ("niche", "birdwatching_5day",
     'Lịch trình BIRDING 5 ngày 3 tỉnh: sân chim, vườn cò, sếu đầu đỏ, checklist, hides, guide. JSON: {"title":"...","days":[...],"species_target":[...],"gear":"...","guides":[...],"best_time":"..."}'),
    ("niche", "temple_hopping_3day",
     'Lịch trình CHÙA KHMER 3 ngày TV: 20+ chùa, kiến trúc, lịch sử, etiquette, ảnh. JSON: {"title":"...","days":[...],"temples":[...],"etiquette":"...","photography":"..."}'),
    ("niche", "craft_workshop_3day",
     'Lịch trình HỌC NGHỀ 3 ngày: làm kẹo dừa, đan chiếu, gốm, nấu ăn, hands-on. JSON: {"title":"...","days":[...],"workshops":[...],"booking":"...","what_to_bring":"..."}'),
    ("niche", "wellness_retreat_5day",
     'Lịch trình WELLNESS 5 ngày: yoga, meditation chùa, spa, đi bộ, ăn chay, digital detox. JSON: {"title":"...","days":[...],"wellness_activities":[...],"diet":"...","disconnect":"..."}'),
    ("niche", "volunteer_7day",
     'Lịch trình TÌNH NGUYỆN 7 ngày: dạy tiếng Anh, trồng rừng, clean-up, community, impact. JSON: {"title":"...","days":[...],"programs":[...],"requirements":"...","impact":"...","contacts":"..."}'),
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
