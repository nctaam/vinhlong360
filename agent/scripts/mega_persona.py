#!/usr/bin/env python3
"""MEGA PERSONA — Nghiên cứu HÀNH TRÌNH NGƯỜI DÙNG + SO SÁNH ĐA CHIỀU.

30+ personas x detailed journey mapping
50+ comparative analysis dimensions
20+ hidden gem reports
Province-level deep profiles

Usage:
  python -u agent/scripts/mega_persona.py --mode all --workers 3
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
OUTPUT_DIR = AGENT_DIR / "data" / "mega_research" / "persona"

sys.path.insert(0, str(AGENT_DIR))
sys.path.insert(0, str(AGENT_DIR / "scripts"))
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_DIR / ".env")
except Exception:
    pass

from mega_research import (LLM, read_jsonl, append_jsonl, log, utc, _cfg_io)


SYS_JOURNEY = """Bạn là UX RESEARCHER + TRAVEL CONSULTANT cấp cao.
Thiết kế chi tiết hành trình du khách cho vùng Vĩnh Long + Bến Tre + Trà Vinh (ĐBSCL, Việt Nam).
Mỗi persona cần: demographic, motivation, pain points, touchpoints, emotions at each stage,
micro-moments, decision triggers, content needs, budget breakdown.
Viết CHI TIẾT, CỤ THỂ — tên địa điểm thật, giá thật, thời gian thật.

QUAN TRỌNG: Trả lời bằng JSON thuần túy (bắt đầu { kết thúc }).
Viết CỰC KỲ CHI TIẾT — ít nhất 3000 ký tự."""

SYS_COMPARE = """Bạn là CHUYÊN GIA SO SÁNH VÀ PHÂN TÍCH đa chiều.
So sánh các tỉnh/vùng/địa điểm ở ĐBSCL với phương pháp luận rõ ràng.
Dùng ma trận, scoring, benchmarking. Trung lập, dựa trên dữ liệu.
Đan xen góc nhìn định lượng và định tính.

QUAN TRỌNG: Trả lời bằng JSON thuần túy (bắt đầu { kết thúc }).
Viết CỰC KỲ CHI TIẾT — ít nhất 3000 ký tự."""

SYS_GEM = """Bạn là TRAVEL INSIDER — người địa phương am hiểu mọi ngóc ngách.
Chia sẻ những GÓC KHUẤT, BÍ MẬT mà 99% du khách không biết.
Chi tiết cụ thể: tên quán (nếu biết), con đường, khung giờ, mẹo vặt.
KHÔNG bịa — nếu không chắc thì nói rõ "cần kiểm chứng".

QUAN TRỌNG: Trả lời bằng JSON thuần túy (bắt đầu { kết thúc }).
Viết CỰC KỲ CHI TIẾT — ít nhất 3000 ký tự."""


def _gen(llm, f, key, sys_prompt, user_prompt, max_tok=8000):
    r = llm.ask_json(sys=sys_prompt, user=user_prompt, temp=0.3, max_tok=max_tok,
                     timeout=600)
    if r:
        r["key"] = key; r["ts"] = utc()
        append_jsonl(f, r)
        log(f"  ✓ {key} ({len(json.dumps(r, ensure_ascii=False))} chars)")
    else:
        log(f"  ✗ {key} — no valid JSON")
    return r


# ═══════════════════════════════════════════════════════════════════════
# PERSONAS — 30 hành trình chi tiết
# ═══════════════════════════════════════════════════════════════════════

PERSONAS = [
    ("solo_backpacker_25", "Backpacker 25 tuổi, ngân sách 500k/ngày, đi 5 ngày, muốn trải nghiệm local, ngủ homestay, ăn vỉa hè, thích chụp ảnh. Lịch trình CHI TIẾT từng giờ 5 ngày, budget breakdown, tips an toàn solo"),
    ("couple_honeymoon", "Cặp đôi tân hôn 28 tuổi, ngân sách 3tr/ngày, 4 ngày, muốn romantic + riêng tư + đẹp cho ảnh. Lịch trình từng giờ, nhà nghỉ/resort recommend, dinner spots, sunset spots, surprise ideas"),
    ("family_3gen", "Gia đình 3 thế hệ: ông bà 70+, bố mẹ 45, con 10+15. 3 ngày, ô tô riêng, ngân sách 5tr/ngày. Cân bằng nghỉ ngơi ông bà + vui chơi trẻ con + thú vị người lớn. Accessibility cho người cao tuổi"),
    ("korean_tourist", "Du khách Hàn Quốc 35 tuổi, 2 ngày from HCMC, quan tâm food + culture + photo. Không nói tiếng Việt. Cần: food recommendations phù hợp khẩu vị Hàn, communication tips, K-beauty/K-drama connections"),
    ("japanese_retiree", "Cặp đôi Nhật Bản đã nghỉ hưu, 65 tuổi, 3 ngày, quan tâm lịch sử + thủ công + vườn. Ngân sách thoải mái. Cần: quiet experiences, quality over quantity, WWII history connections, craft parallels with Japan"),
    ("french_historian", "Nhà sử học Pháp 50 tuổi, nghiên cứu dấu ấn thuộc địa Pháp ở ĐBSCL. 5 ngày, muốn thăm kiến trúc thuộc địa, nhà thờ, kênh đào Pháp xây, tài liệu lịch sử. Academic itinerary"),
    ("vegan_yogi", "Phụ nữ 32 tuổi, vegan, tập yoga, muốn wellness retreat 4 ngày. Cần: vegan restaurant options, meditation spots (chùa), natural spa, organic farm visit, peaceful accommodation"),
    ("photographer_pro", "Nhiếp ảnh gia chuyên nghiệp, 40 tuổi, 4 ngày, chuyên landscape + portrait. Cần: golden hour map, blue hour spots, local portrait subjects (xin phép), drone spots, equipment tips, seasonal light guide"),
    ("student_group_20", "Nhóm 20 sinh viên HCMC, fieldtrip 2 ngày, ngân sách 300k/người/ngày. Mục đích: học tập + team building. Cần: educational sites, group activities, cheap eat, transport for 20 people, safety protocol"),
    ("digital_nomad", "Digital nomad 30 tuổi, 2 tuần, cần WiFi tốt, quán cà phê để làm việc, co-working space, ngân sách 700k/ngày. Cần: WiFi map, power outlet cafés, monthly room deals, community, gym/running routes"),
    ("food_blogger", "Food blogger 500k followers, 3 ngày, cần quay video, thử tất cả món đặc sản. Cần: food map chi tiết, best time cho từng quán, photogenic dishes, origin stories, local chef connections"),
    ("birdwatcher", "Birder chuyên nghiệp từ Úc, 5 ngày, muốn xem sếu đầu đỏ + sân chim + vườn cò. Cần: species list, best hides, timing, local guide contacts, equipment, ethics, eBird hotspots"),
    ("cycling_enthusiast", "Nhóm 4 cyclist, 3 ngày, muốn đạp xe khám phá, 50-80km/ngày. Cần: route maps, road conditions, repair shops, water stops, flat/scenic routes, elevation, traffic safety"),
    ("muslim_traveler", "Du khách Mã Lai Muslim, 30 tuổi, 3 ngày. Cần: halal food options, prayer spaces/mosques, modest accommodation, alcohol-free activities, cultural sensitivity guide"),
    ("lgbtq_couple", "Cặp đôi đồng tính 30 tuổi từ Đài Loan, 3 ngày. Cần: safety assessment, LGBTQ-friendly accommodation, PDA advice, inclusive experiences, nightlife, local attitudes"),
    ("elderly_solo_woman", "Phụ nữ 68 tuổi, đi một mình, 3 ngày, từng sống Vĩnh Long hồi nhỏ (trước 1975). Nostalgia trip. Cần: accessible transport, safe accommodation, memory spots, gentle pace, health facilities"),
    ("motorbike_adventure", "Nhóm 2 tay lái Sài Gòn, 4 ngày, Honda Winner/Exciter, thích off-road + khám phá. Cần: route (bao gồm đường làng), petrol stations, mechanic shops, camping spots, river crossings"),
    ("art_collector", "Nhà sưu tập nghệ thuật 45 tuổi, quan tâm folk art, lacquer, ceramics. 3 ngày. Cần: galleries, workshops, master artisans, buying guide (giá hợp lý), shipping, authentication"),
    ("teacher_field_trip", "Giáo viên lịch sử, dẫn 35 học sinh lớp 10, 1 ngày. Cần: educational route, talking points at each stop, worksheet ideas, lunch spot cho 35 người, emergency plan, permission forms"),
    ("startup_team_retreat", "Team 8 người công ty tech HCMC, 2 ngày retreat. Cần: teambuilding activities, meeting room, WiFi, fun evening, cooking class, budget 10tr total, transport arrangement"),
    ("pregnant_couple", "Vợ mang thai 6 tháng + chồng, weekend getaway 2 ngày. Cần: safe food, comfortable accommodation, gentle activities, nearest hospital, no-risk experiences, relaxation focus"),
    ("disabled_veteran", "Cựu chiến binh Mỹ 75 tuổi, wheelchair, quay lại nơi từng đóng quân. 3 ngày. Cần: wheelchair access, Mekong war sites, emotional support, Vietnamese-American reconciliation sites, interpreter"),
    ("eco_volunteer", "Tình nguyện viên môi trường 25 tuổi, 1 tuần, muốn tham gia trồng rừng ngập mặn, clean-up, giáo dục cộng đồng. Cần: NGO contacts, volunteer programs, accommodation, meaningful projects"),
    ("culinary_student", "Sinh viên ẩm thực 22 tuổi, 5 ngày, muốn học nấu ăn miền Tây từ local cooks. Cần: cooking classes, market tours 5am, ingredient sourcing, recipe documentation, chef interviews"),
    ("buddhist_pilgrim", "Phật tử thuần thành 55 tuổi, 4 ngày, thăm chùa Khmer + chùa Việt. Cần: temple route, meditation schedule, monk etiquette, vegetarian food, religious calendar, offering guide"),
    ("real_estate_investor", "Nhà đầu tư BĐS HCMC, 2 ngày, khảo sát đất + resort potential + dự án. Cần: hot zones, price per m2, zoning info, infrastructure plans, ROI analysis, local contact"),
    ("journalist_investigative", "Nhà báo viết về biến đổi khí hậu ĐBSCL, 5 ngày. Cần: sụt lún, xâm nhập mặn, di cư, adaptation stories, expert interviews, photo opportunities, data sources"),
    ("music_researcher", "Nhà nghiên cứu âm nhạc (PhD), 4 ngày, nghiên cứu đờn ca tài tử + nhạc Khmer. Cần: performance venues, master musicians, recording opportunities, instrument makers, archives"),
    ("luxury_yacht", "Nhóm 6 người, thuê thuyền riêng, 3 ngày trên sông. Ngân sách không giới hạn. Cần: yacht/houseboat rental, riverside dining, VIP experiences, private tours, concierge recommendations"),
    ("teen_solo_first_trip", "Thiếu niên 18 tuổi, chuyến đi solo đầu tiên, 2 ngày, ngân sách 400k/ngày. Cần: safety tips, cheap accommodation, Instagram spots, street food, making friends, emergency contacts"),
]


def personas(llm, workers=3):
    log("═══ PERSONA JOURNEYS ═══")
    f = OUTPUT_DIR / "journeys.jsonl"
    done = {r.get("key") for r in read_jsonl(f)}
    remaining = [(k, p) for k, p in PERSONAS if k not in done]
    log(f"  {len(remaining)} personas to map")
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(_gen, llm, f, k, SYS_JOURNEY,
            f"Thiết kế HÀNH TRÌNH CHI TIẾT cho persona: {p}\n\n"
            "Trả về JSON với: persona_name, demographics, motivations, pain_points, "
            "day_by_day (mảng, mỗi ngày có schedule từng giờ, meals, transport, cost), "
            "budget_breakdown, tips, risks, alternatives, content_needs, "
            "emotional_journey (mảng cảm xúc qua từng touchpoint), "
            "booking_triggers, social_media_moments", 6000) for k, p in remaining]
        for fut in as_completed(futs):
            try: fut.result()
            except Exception as e: log(f"  ERR: {e}")


# ═══════════════════════════════════════════════════════════════════════
# COMPARISONS — So sánh đa chiều
# ═══════════════════════════════════════════════════════════════════════

COMPARISONS = [
    ("vl_vs_bt_vs_tv_overall", "So sánh TỔNG THỂ 3 tỉnh Vĩnh Long vs Bến Tre vs Trà Vinh: diện tích, dân số, GDP, du lịch, hạ tầng, giáo dục, y tế, văn hóa, ẩm thực, thiên nhiên — scoring matrix 1-10 cho 30+ tiêu chí"),
    ("vs_cantho", "So sánh 3 tỉnh (VL+BT+TV) vs CẦN THƠ về du lịch: lượng khách, doanh thu, hạ tầng, flight connections, nightlife, F&B variety, accommodation quality, digital presence, events — SWOT cho mỗi bên"),
    ("vs_dongthap_angiang", "So sánh cluster VL+BT+TV vs Đồng Tháp+An Giang: eco-tourism, heritage, food, accessibility from HCMC, homestay quality, community tourism, price level, seasonality"),
    ("vs_phuquoc", "So sánh du lịch 3 tỉnh vs PHÚ QUỐC: target audience overlap?, complementary positioning, beach vs river, budget comparison, international readiness, infrastructure gap"),
    ("vs_dalat_nhatrang", "So sánh du lịch ĐBSCL 3 tỉnh vs ĐÀ LẠT + NHA TRANG: market positioning, season overlap, transport, price, experience type, repeat visit rate, digital marketing presence"),
    ("district_ranking_vl", "RANKING tất cả huyện/thị Vĩnh Long theo du lịch: điểm đến, accommodation, food, accessibility, unique selling point, growth potential. Scoring + narrative cho từng huyện"),
    ("district_ranking_bt", "RANKING tất cả huyện/thị Bến Tre theo du lịch: coconut tourism density, homestay quality, craft variety, food scene, accessibility, river experience quality"),
    ("district_ranking_tv", "RANKING tất cả huyện/thị Trà Vinh theo du lịch: Khmer heritage density, pagoda quality, beach access, food diversity, accommodation, nightlife, cultural events"),
    ("food_compare_3province", "So sánh ẨM THỰC 3 tỉnh: signature dishes unique to each, shared dishes with local twist, ingredient availability, restaurant quality, street food scene, cooking class options, food tour potential"),
    ("accommodation_benchmark", "BENCHMARK chỗ ở 3 tỉnh: hotel count by star rating, homestay quality & price, resort options, unique stays (nhà vườn, nhà sàn, houseboat), Booking.com rating average, capacity vs demand"),
    ("heritage_density_map", "Phân tích MẬT ĐỘ DI SẢN trên bản đồ 3 tỉnh: di tích quốc gia, di tích tỉnh, chùa Khmer, nhà cổ, công trình Pháp, cây di sản — cluster analysis, heritage routes, conservation priority"),
    ("transport_benchmark", "BENCHMARK GIAO THÔNG 3 tỉnh: đường cao tốc, quốc lộ, tỉnh lộ km, cầu mới, bến xe, bến phà, airport access time, public transport, ride-hailing availability, river transport"),
    ("digital_readiness", "Đánh giá SỐ HÓA DU LỊCH 3 tỉnh: Google Maps listing quality, TripAdvisor presence, Booking/Agoda inventory, social media activity, QR payment adoption, WiFi coverage tourist areas, official website quality"),
    ("seasonality_matrix", "Ma trận MÙA VỤ du lịch 12 tháng x 3 tỉnh: weather score, event calendar, fruit season, price level, crowd level, photography conditions, recommended activities per month"),
    ("investment_opportunities", "Phân tích CƠ HỘI ĐẦU TƯ du lịch: top 10 gaps/opportunities mỗi tỉnh, estimated investment needed, expected ROI, risk factors, regulatory requirements, success probability"),
]


def comparisons(llm, workers=3):
    log("═══ COMPARISONS ═══")
    f = OUTPUT_DIR / "comparisons.jsonl"
    done = {r.get("key") for r in read_jsonl(f)}
    remaining = [(k, p) for k, p in COMPARISONS if k not in done]
    log(f"  {len(remaining)} comparisons")
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(_gen, llm, f, k, SYS_COMPARE, p, 6000) for k, p in remaining]
        for fut in as_completed(futs):
            try: fut.result()
            except Exception as e: log(f"  ERR: {e}")


# ═══════════════════════════════════════════════════════════════════════
# HIDDEN GEMS — Bí mật địa phương
# ═══════════════════════════════════════════════════════════════════════

GEM_TOPICS = [
    ("vl_hidden_food", "20 quán ăn BÍ MẬT ở Vĩnh Long mà chỉ dân local biết: tên quán/chủ, địa chỉ/khu vực, món đặc biệt, giá, giờ mở, mẹo gọi món, câu chuyện đằng sau"),
    ("bt_hidden_food", "20 quán ăn BÍ MẬT ở Bến Tre mà chỉ dân local biết: tên quán/chủ, địa chỉ/khu vực, món đặc biệt, giá, giờ mở, mẹo gọi món, câu chuyện đằng sau"),
    ("tv_hidden_food", "20 quán ăn BÍ MẬT ở Trà Vinh mà chỉ dân local biết: tên quán/chủ, địa chỉ/khu vực, món đặc biệt, giá, giờ mở, mẹo gọi món, câu chuyện đằng sau"),
    ("vl_secret_spots", "15 địa điểm BÍ MẬT ở Vĩnh Long: nơi locals picnic, góc sông đẹp ít người, cây cổ thụ, vườn trái cây tư nhân chào đón, con đường đẹp nhưng không có trên bản đồ du lịch"),
    ("bt_secret_spots", "15 địa điểm BÍ MẬT ở Bến Tre: bãi dừa vắng, cù lao nhỏ ít người, đường mòn xe đạp, ao sen bí mật, vườn ong, xưởng thủ công nhỏ"),
    ("tv_secret_spots", "15 địa điểm BÍ MẬT ở Trà Vinh: chùa Khmer nhỏ ít du khách nhưng đẹp, bãi biển vắng, rừng tràm hoang sơ, cánh đồng gió, sunset spots"),
    ("local_tips_transport", "30 MẸO GIAO THÔNG local: đò ngang nào vẫn chạy, phà nào miễn phí, xe buýt nào đi được cảnh đẹp, grab/be có không, thuê xe máy ở đâu, đường tắt, tránh kẹt"),
    ("local_tips_money", "MẸO TIỀN BẠC cho du khách: ATM ở đâu, quán nào nhận thẻ, chợ nào mặc cả được, giá local vs giá tourist, tip culture, đổi tiền, mobile payment"),
    ("local_tips_culture", "MẸO VĂN HÓA: cách chào hỏi, quà tặng khi đến nhà local, taboos, đi chùa Khmer nên biết gì, nghi thức uống trà, cách từ chối lịch sự, body language"),
    ("sunrise_sunset_map", "BẢN ĐỒ BÌNH MINH/HOÀNG HÔN: top 10 sunrise spots + top 10 sunset spots mỗi tỉnh, tọa độ GPS ước lượng, tháng đẹp nhất, composition tips, parking/access info"),
    ("rainy_day_guide", "HƯỚNG DẪN NGÀY MƯA: 20 hoạt động hay khi mưa ở 3 tỉnh — quán cà phê view mưa, bảo tàng, workshop, spa, cooking class, shopping, karaoke, đọc sách ở đâu"),
    ("market_guide_complete", "HƯỚNG DẪN CHỢ HOÀN CHỈNH: tất cả chợ lớn 3 tỉnh — giờ mở (chợ sáng/chiều/đêm), section map, món phải thử, mặc cả tips, vệ sinh, parking, seasonal items"),
    ("coffee_guide", "BẢN ĐỒ CÀ PHÊ chi tiết: tất cả quán cà phê đáng đến ở 3 tỉnh — WiFi quality, ổ cắm, atmosphere, specialty drinks, giá, giờ vàng, work-friendly, date-friendly, family-friendly rating"),
    ("after_dark", "AFTER DARK GUIDE: đời sống về đêm chi tiết 3 tỉnh — chợ đêm, quán nhậu, beer garden, live music, karaoke, riverside bars, late-night street food, safety tips, 24h spots"),
    ("free_experiences", "30 TRẢI NGHIỆM MIỄN PHÍ tuyệt vời ở 3 tỉnh: chùa, công viên, cầu view đẹp, lễ hội công cộng, sunset watching, river walk, market wandering, temple garden meditation"),
]


def hidden_gems(llm, workers=3):
    log("═══ HIDDEN GEMS ═══")
    f = OUTPUT_DIR / "hidden_gems.jsonl"
    done = {r.get("key") for r in read_jsonl(f)}
    remaining = [(k, p) for k, p in GEM_TOPICS if k not in done]
    log(f"  {len(remaining)} gem topics")
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(_gen, llm, f, k, SYS_GEM, p, 6000) for k, p in remaining]
        for fut in as_completed(futs):
            try: fut.result()
            except Exception as e: log(f"  ERR: {e}")


# ═══════════════════════════════════════════════════════════════════════
# PROVINCE PROFILES — Hồ sơ tỉnh siêu chi tiết
# ═══════════════════════════════════════════════════════════════════════

PROFILES = [
    ("vl_megaprofile", """Viết HỒ SƠ SIÊU CHI TIẾT tỉnh VĨNH LONG cho du khách thông minh:
- Tổng quan: diện tích, dân số, GDP, climate, geography
- Lịch sử: từ Thủy Chân Lạp → Nguyễn triều → Pháp → 1945-1975 → hiện đại
- Hành chính: tất cả huyện/thị + đặc điểm từng nơi
- Kinh tế: nông nghiệp, thủy sản, công nghiệp, du lịch — số liệu
- Văn hóa: nghệ thuật, lễ hội, tín ngưỡng, di sản
- Ẩm thực: top 30 món + nơi ăn ngon nhất
- Du lịch: top 20 điểm đến + lịch trình gợi ý 1-3-5 ngày
- Hạ tầng: đường, cầu, bến xe, y tế, giáo dục
- Người nổi tiếng: nhân vật lịch sử + hiện đại
- Tương lai: dự án đang triển khai, quy hoạch, triển vọng"""),

    ("bt_megaprofile", """Viết HỒ SƠ SIÊU CHI TIẾT tỉnh BẾN TRE — Xứ Dừa:
- Tổng quan: diện tích, dân số, GDP, climate, geography — đảo + cù lao
- Lịch sử: Đồng Khởi, anh hùng cách mạng, Nguyễn Đình Chiểu
- Hành chính: tất cả huyện/thị + đặc điểm
- Kinh tế: dừa value chain, thủy sản, cây ăn trái, du lịch
- Văn hóa: bản sắc "dừa", nghệ thuật, di sản
- Ẩm thực: 30 món + coconut-based specialties
- Du lịch: top 20 điểm đến + lịch trình
- Hạ tầng: cầu Rạch Miễu 2, đường ven biển, sân bay tương lai
- Nhân vật: Nguyễn Đình Chiểu, Phan Thanh Giản, Trương Vĩnh Ký...
- Tương lai: biến đổi khí hậu, kinh tế dừa 4.0, du lịch sinh thái"""),

    ("tv_megaprofile", """Viết HỒ SƠ SIÊU CHI TIẾT tỉnh TRÀ VINH — Vùng đất Khmer:
- Tổng quan: diện tích, dân số (Kinh-Khmer-Hoa %), climate, geography
- Lịch sử: từ Phù Nam/Chân Lạp → Nguyễn → hiện đại
- Hành chính: tất cả huyện/thị + đặc điểm + Khmer % mỗi huyện
- Kinh tế: nông nghiệp, thủy sản, công nghiệp, du lịch
- Văn hóa Khmer: 142 chùa, lễ hội, nghệ thuật, ngôn ngữ, nhạc ngũ âm
- Ẩm thực: 30 món (Việt + Khmer + fusion)
- Du lịch: top 20 điểm đến + temple route + beach route
- Hạ tầng: đường, cầu, cảng Định An, sân bay Long Toàn
- Nhân vật: nhân vật lịch sử + artists + monks
- Tương lai: khu kinh tế Định An, năng lượng tái tạo, climate adaptation"""),
]


def province_profiles(llm, workers=2):
    log("═══ PROVINCE PROFILES ═══")
    f = OUTPUT_DIR / "profiles.jsonl"
    done = {r.get("key") for r in read_jsonl(f)}
    remaining = [(k, p) for k, p in PROFILES if k not in done]
    log(f"  {len(remaining)} profiles")
    sys_p = "Bạn là CHUYÊN GIA ĐỊA PHƯƠNG CẤP CAO nhất. Viết hồ sơ tỉnh ở trình độ encyclopedia + Lonely Planet + academic. Siêu chi tiết, chính xác, cập nhật."
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(_gen, llm, f, k, sys_p, p, 6000) for k, p in remaining]
        for fut in as_completed(futs):
            try: fut.result()
            except Exception as e: log(f"  ERR: {e}")


MODES = {
    "personas": personas,
    "comparisons": comparisons,
    "hidden-gems": hidden_gems,
    "profiles": province_profiles,
}


def main():
    _cfg_io()
    ap = argparse.ArgumentParser(description="Mega Persona — Journey mapping & comparisons")
    ap.add_argument("--mode", required=True, choices=list(MODES.keys()) + ["all"])
    ap.add_argument("--workers", type=int, default=3)
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

    elapsed = (time.time() - t0) / 60
    log(f"\n═══ DONE ({elapsed:.1f}m) ═══")
    log(f"  FINAL LLM: {llm.info()}")

if __name__ == "__main__":
    main()
