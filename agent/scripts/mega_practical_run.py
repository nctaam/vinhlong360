#!/usr/bin/env python3
"""MEGA PRACTICAL RUNNER — Thông tin thực tế siêu chi tiết cho du khách.

Giao thông, tiền bạc, an toàn, y tế, mua sắm, communication, etiquette,
emergency, packing, weather, phrasebook, accessibility — TẤT CẢ.

SEQUENTIAL — one API call at a time.
Resume-safe via JSONL done set.

Usage:
  python -u agent/scripts/mega_practical_run.py 2>&1
"""
from __future__ import annotations
import json, os, sys, time, warnings
warnings.filterwarnings("ignore", message=".*renamed.*ddgs.*")
from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = AGENT_DIR.parent
OUTPUT_DIR = AGENT_DIR / "data" / "mega_research" / "practical"

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

SYS = "Bạn là TRAVEL CONSULTANT chuyên sâu Việt Nam. Trả về JSON thuần túy. Viết tiếng Việt, siêu chi tiết thực tế."

TOPICS = [
    # === GIAO THÔNG ===
    ("transport", "hcmc_to_3tinh",
     'Hướng dẫn ĐI TỪ SÀI GÒN đến 3 tỉnh VL-BT-TV: xe khách (hãng, giờ, giá, bến), xe thuê, tự lái, grab. JSON: {"topic":"...","options":[...],"comparison":"...","tips":"...","booking":"..."}'),
    ("transport", "inter_province",
     'Hướng dẫn DI CHUYỂN GIỮA 3 TỈNH: xe buýt, xe ôm, phà, đò, thuê xe máy, grab, taxi. Giá + thời gian. JSON: {"topic":"...","routes":[...],"options":[...],"tips":"...","apps":"..."}'),
    ("transport", "local_transport_vl",
     'Giao thông NỘI TỈNH Vĩnh Long: xe buýt tuyến, xe ôm, phà Mỹ Thuận/An Bình, đò, grab, thuê xe. JSON: {"topic":"...","options":[...],"routes":[...],"prices":"...","tips":"..."}'),
    ("transport", "local_transport_bt",
     'Giao thông NỘI TỈNH Bến Tre: xe buýt, phà Rạch Miễu, đò kênh rạch, thuê xuồng, grab. JSON: {"topic":"...","options":[...],"ferry_schedule":"...","prices":"...","tips":"..."}'),
    ("transport", "local_transport_tv",
     'Giao thông NỘI TỈNH Trà Vinh: xe buýt, xe lôi, grab, thuê xe máy, đò. JSON: {"topic":"...","options":[...],"routes":[...],"prices":"...","tips":"..."}'),
    ("transport", "bike_rental",
     'Hướng dẫn THUÊ XE MÁY/ĐẠP 3 tỉnh: shops, giá, giấy tờ, bảo hiểm, đường, luật. JSON: {"topic":"...","rental_shops":[...],"prices":"...","requirements":"...","safety":"...","routes":"..."}'),

    # === TIỀN BẠC ===
    ("money", "atm_banking",
     'Hướng dẫn TIỀN BẠC & NGÂN HÀNG 3 tỉnh: ATM locations, phí rút, đổi tiền, thẻ quốc tế, MoMo/ZaloPay. JSON: {"topic":"...","atm_map":[...],"fees":"...","exchange":"...","mobile_pay":"...","tips":"..."}'),
    ("money", "budget_guide",
     'Hướng dẫn NGÂN SÁCH chi tiết: budget/mid/luxury per day, ăn uống, chỗ ở, transport, activities. JSON: {"topic":"...","tiers":[...],"daily_breakdown":"...","saving_tips":[...],"splurge_worthy":"..."}'),
    ("money", "tipping_bargaining",
     'Văn hóa TIP & MẶC CẢ 3 tỉnh: khi nào tip, bao nhiêu, mặc cả ở đâu, cách mặc cả lịch sự. JSON: {"topic":"...","tipping_guide":"...","bargaining_guide":"...","cultural_notes":"...","scam_awareness":"..."}'),

    # === AN TOÀN ===
    ("safety", "general_safety",
     'Hướng dẫn AN TOÀN du lịch 3 tỉnh: giao thông, trộm cắp, scam, thời tiết, động vật, đêm. JSON: {"topic":"...","risks":[...],"prevention":"...","by_province":"...","emergency_numbers":"..."}'),
    ("safety", "health_medical",
     'Hướng dẫn Y TẾ & SỨC KHỎE: bệnh viện, nhà thuốc, bảo hiểm, vaccinations, food safety, first aid. JSON: {"topic":"...","hospitals":[...],"pharmacies":"...","insurance":"...","common_issues":"...","first_aid":"..."}'),
    ("safety", "food_safety",
     'Hướng dẫn AN TOÀN THỰC PHẨM: ăn đường phố safely, nước uống, dị ứng, vegetarian/vegan, halal. JSON: {"topic":"...","street_food_rules":[...],"water":"...","allergies":"...","dietary":[...],"emergency":"..."}'),
    ("safety", "weather_disasters",
     'Hướng dẫn THỜI TIẾT & THIÊN TAI: mùa mưa, bão, lũ, nắng nóng, sấm sét, ứng phó. JSON: {"topic":"...","by_month":"...","hazards":[...],"preparation":"...","shelter":"...","apps":"..."}'),
    ("safety", "solo_female",
     'Hướng dẫn NỮ ĐI MỘT MÌNH 3 tỉnh: an toàn, dress code, đêm, transport, accommodation, social. JSON: {"topic":"...","safety_tips":[...],"accommodation":"...","transport":"...","social":"...","emergency":"..."}'),

    # === MUA SẮM ===
    ("shopping", "souvenirs_guide",
     'Hướng dẫn MUA SẮM QUÀ 3 tỉnh: quà đặc sản, thủ công, OCOP, giá, shops uy tín, mang máy bay. JSON: {"topic":"...","by_province":[...],"price_guide":"...","trusted_shops":[...],"packing_tips":"...","customs":"..."}'),
    ("shopping", "market_guide_detailed",
     'Hướng dẫn CHỢ chi tiết 3 tỉnh: tên chợ, giờ, section, món ăn, mua sắm, parking, toilet. JSON: {"topic":"...","markets":[...],"tips":"...","etiquette":"...","best_buys":"..."}'),

    # === COMMUNICATION ===
    ("communication", "sim_internet",
     'Hướng dẫn SIM & INTERNET 3 tỉnh: mua SIM, data plan, WiFi spots, coverage, eSIM. JSON: {"topic":"...","providers":[...],"plans":[...],"wifi_map":"...","coverage":"...","tips":"..."}'),
    ("communication", "phrasebook",
     'PHRASEBOOK du lịch: 100 câu tiếng Việt + 30 câu Khmer cơ bản, pronunciation, situations. JSON: {"topic":"...","vietnamese":[{"phrase":"...","pronunciation":"...","situation":"..."}...],"khmer":[...],"tips":"..."}'),
    ("communication", "apps_tools",
     'APPS & TOOLS du lịch 3 tỉnh: maps, transport, food, translate, payment, weather, emergency. JSON: {"topic":"...","essential_apps":[...],"useful_apps":[...],"offline_tools":"...","tips":"..."}'),

    # === VĂN HÓA & ETIQUETTE ===
    ("etiquette", "cultural_dos_donts",
     'VĂN HÓA ỨNG XỬ 3 tỉnh: chùa, nhà dân, ăn uống, chụp ảnh, mặc cả, cho tiền, Khmer customs. JSON: {"topic":"...","dos":[...],"donts":[...],"khmer_specific":"...","religious":"...","photography":"..."}'),
    ("etiquette", "temple_guide",
     'Hướng dẫn THĂM CHÙA: Phật giáo Việt, Theravada Khmer, Công giáo, Cao Đài — dress, behavior, offerings. JSON: {"topic":"...","by_religion":[...],"dress_code":"...","behavior":"...","photography":"...","donations":"..."}'),

    # === CHỖ Ở ===
    ("accommodation", "hotel_guide",
     'Hướng dẫn CHỖ Ở chi tiết 3 tỉnh: hotel, homestay, resort, unique stays, booking tips, areas. JSON: {"topic":"...","by_province":[...],"by_budget":[...],"booking_tips":"...","unique_stays":[...],"areas":"..."}'),
    ("accommodation", "homestay_deep",
     'Hướng dẫn HOMESTAY chi tiết: best homestays 3 tỉnh, phong cách, giá, book, etiquette, expectation. JSON: {"topic":"...","homestays":[...],"what_to_expect":"...","etiquette":"...","booking":"...","review_guide":"..."}'),

    # === PACKING & PREPARATION ===
    ("preparation", "packing_list",
     'PACKING LIST chi tiết theo mùa: mùa khô, mùa mưa, mùa nước nổi. Clothing, gear, medicine, docs. JSON: {"topic":"...","by_season":[...],"essentials":[...],"optional":[...],"dont_bring":"...","tips":"..."}'),
    ("preparation", "pre_trip_checklist",
     'CHECKLIST TRƯỚC CHUYẾN ĐI: booking, documents, insurance, money, apps, research, packing. JSON: {"topic":"...","timeline":[...],"documents":"...","booking":"...","money":"...","health":"...","apps":"..."}'),

    # === FOREIGN VISITORS ===
    ("foreign", "international_guide",
     'Hướng dẫn DU KHÁCH QUỐC TẾ: visa, airport transfer, SIM, money, culture shock, language barrier. JSON: {"topic":"...","visa":"...","arrival":"...","sim":"...","money":"...","culture":"...","communication":"...","safety":"..."}'),
    ("foreign", "korean_guide",
     'Hướng dẫn riêng DU KHÁCH HÀN: K-culture connections, food similarities, shopping, selfie spots. JSON: {"topic":"...","cultural_links":"...","food_guide":"...","shopping":"...","photo_spots":[...],"practical":"..."}'),
    ("foreign", "japanese_guide",
     'Hướng dẫn riêng DU KHÁCH NHẬT: craft parallels, food quality, cleanliness, onsen alternatives, history. JSON: {"topic":"...","cultural_parallels":"...","food_guide":"...","craft":"...","quality_finds":[...],"practical":"..."}'),
    ("foreign", "western_guide",
     'Hướng dẫn riêng DU KHÁCH PHƯƠNG TÂY: adventure, authentic, responsible tourism, volunteer, long-stay. JSON: {"topic":"...","adventure":[...],"authentic_experiences":"...","responsible":"...","long_stay":"...","practical":"..."}'),

    # === ACCESSIBILITY ===
    ("accessibility", "wheelchair_guide",
     'Hướng dẫn DU LỊCH XE LĂN 3 tỉnh: accessible sites, transport, accommodation, restaurants, assistance. JSON: {"topic":"...","accessible_sites":[...],"transport":"...","accommodation":"...","challenges":"...","tips":"..."}'),
    ("accessibility", "elderly_guide",
     'Hướng dẫn NGƯỜI LỚN TUỔI: nhịp chậm, y tế, accessible, shade, rest stops, medication. JSON: {"topic":"...","suitable_activities":[...],"medical":"...","rest_stops":"...","diet":"...","tips":"..."}'),
    ("accessibility", "dietary_guide",
     'Hướng dẫn CHẾ ĐỘ ĂN ĐẶC BIỆT: vegetarian, vegan, halal, gluten-free, allergies — ở đâu, nói sao. JSON: {"topic":"...","vegetarian":"...","vegan":"...","halal":"...","gluten_free":"...","allergies":"...","phrases":[...]}'),

    # === EMERGENCY ===
    ("emergency", "emergency_guide",
     'Hướng dẫn KHẨN CẤP toàn diện: số điện thoại, bệnh viện, công an, lãnh sự quán, mất hộ chiếu, tai nạn. JSON: {"topic":"...","numbers":[...],"hospitals":[...],"police":"...","embassy":"...","lost_passport":"...","insurance":"..."}'),
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
        r = llm.ask_json(sys=SYS, user=prompt, temp=0.2, max_tok=6000)
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
