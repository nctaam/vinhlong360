#!/usr/bin/env python3
"""MEGA ULTRA-DEEP RUNNER — Nghiên cứu CỰC SÂU vượt cả chuyên gia đầu ngành.

Các chủ đề chưa được cover bởi expert_run.py hay persona_run.py:
- Y học cổ truyền, dược liệu
- Văn hóa sông nước, ghe xuồng
- Kinh tế phi chính thức, chợ nổi
- Thích ứng khí hậu
- Chuyển đổi số nông thôn
- Ẩm thực phân tử (molecular)
- Dệt, gốm, thủ công mỹ nghệ
- Đóng ghe truyền thống
- Lịch sử truyền miệng
- Di cư lao động
- Hệ sinh thái đất ngập nước
- Dịch vụ hệ sinh thái rừng ngập mặn
- Chuỗi giá trị dừa chi tiết
- Vi sinh vật học nước mắm
- Nhiệt động học kiến trúc dân gian
- Hạ tầng thuộc địa Pháp mapping
- Khảo cổ học
- Nhân khẩu học chi tiết
- Hệ thống kênh rạch
- Du lịch tâm linh
- Ẩm thực đường phố từng quận/huyện
- Nghệ thuật biểu diễn
- Giáo dục & literacy
- Hệ thống y tế
- Thể thao & giải trí

Usage:
  python -u agent/scripts/mega_ultradeep_run.py 2>&1
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
OUTPUT_DIR = AGENT_DIR / "data" / "mega_research" / "ultradeep"

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

SYS = "Bạn là CHUYÊN GIA ĐẦU NGÀNH cấp giáo sư. Trả về JSON thuần túy. Viết tiếng Việt, siêu chi tiết học thuật."

TOPICS = [
    # === Y HỌC CỔ TRUYỀN & DƯỢC LIỆU ===
    ("medicine", "traditional_medicine",
     'Y học cổ truyền 3 tỉnh VL-BT-TV: thầy thuốc nam, bài thuốc dân gian, cây thuốc ĐBSCL, đông y Khmer, bà đỡ truyền thống, WHO integration. JSON: {"topic":"...","practitioners":[...],"remedies":[...],"medicinal_plants":[...],"khmer_medicine":"...","modern_integration":"...","sources":[...]}'),
    ("medicine", "medicinal_plants",
     'Dược liệu học cây thuốc vùng ĐBSCL 3 tỉnh: inventory 50+ loài, tên Latin, công dụng, bộ phận dùng, bào chế, evidence-based, conservation. JSON: {"topic":"...","plants":[{"name":"...","latin":"...","uses":"...","preparation":"...","evidence":"..."}...],"conservation":"...","sources":[...]}'),

    # === VĂN HÓA SÔNG NƯỚC ===
    ("waterway", "river_culture",
     'Văn hóa sông nước ĐBSCL 3 tỉnh: đời sống trên sông, nhà nổi, chợ nổi, nghề chài, ghe tam bản, ca dao sông nước, nghi lễ thủy thần. JSON: {"topic":"...","daily_life":"...","floating_markets":[...],"boat_types":[...],"folklore":[...],"rituals":"...","decline":"...","sources":[...]}'),
    ("waterway", "boat_building",
     'Nghề đóng ghe xuồng ĐBSCL: loại ghe (tam bản, chài, bầu, lường), gỗ sao/gõ, kỹ thuật, xưởng còn hoạt động, UNESCO potential. JSON: {"topic":"...","boat_types":[...],"materials":"...","techniques":"...","workshops":[...],"masters":"...","preservation":"...","sources":[...]}'),
    ("waterway", "canal_system",
     'Hệ thống kênh rạch 3 tỉnh: lịch sử đào kênh (Nguyễn, Pháp, sau 1975), thủy lợi, giao thông, sinh thái, bản đồ. JSON: {"topic":"...","history":[...],"major_canals":[...],"engineering":"...","ecological_function":"...","current_state":"...","sources":[...]}'),

    # === KINH TẾ PHI CHÍNH THỨC ===
    ("informal_economy", "floating_markets",
     'Kinh tế học chợ nổi ĐBSCL: cấu trúc thương mại, chuỗi cung ứng, pricing, seasonal, social networks, so sánh quốc tế. JSON: {"topic":"...","markets":[...],"economics":"...","supply_chain":"...","social_structure":"...","comparison":"...","future":"...","sources":[...]}'),
    ("informal_economy", "street_economy",
     'Kinh tế vỉa hè 3 tỉnh: xe đẩy, gánh hàng rong, quán cóc, thu nhập, quy định, spatial pattern, tourist interaction. JSON: {"topic":"...","types":[...],"income_analysis":"...","regulations":"...","spatial_patterns":"...","tourism_interface":"...","sources":[...]}'),

    # === KHÍ HẬU & THÍCH ỨNG ===
    ("climate", "adaptation",
     'Thích ứng biến đổi khí hậu 3 tỉnh: xâm nhập mặn, sụt lún, lũ, mô hình Dutch-style, nông nghiệp thông minh, tái định cư. JSON: {"topic":"...","vulnerabilities":[...],"adaptation_strategies":[...],"local_innovation":"...","financing":"...","projections_2050":"...","sources":[...]}'),
    ("climate", "disaster_risk",
     'Quản lý rủi ro thiên tai 3 tỉnh: bão, lũ, sạt lở, triều cường, hạn mặn, early warning, cộng đồng. JSON: {"topic":"...","hazards":[...],"historical_events":[...],"response_capacity":"...","community_resilience":"...","infrastructure":"...","sources":[...]}'),

    # === THỦ CÔNG MỸ NGHỆ CHI TIẾT ===
    ("crafts", "weaving_textiles",
     'Dệt & thủ công vải 3 tỉnh: dệt chiếu (Vĩnh Long), dệt khăn rằn, thổ cẩm Khmer, kỹ thuật nhuộm, raw materials, value chain. JSON: {"topic":"...","traditions":[...],"techniques":"...","materials":"...","artisans":[...],"market":"...","preservation":"...","sources":[...]}'),
    ("crafts", "pottery_ceramics",
     'Gốm sứ 3 tỉnh: lò gốm cổ, kỹ thuật nung, men, motif, gốm Khmer vs Hoa vs Việt, contemporary artists. JSON: {"topic":"...","history":"...","techniques":[...],"kilns":[...],"styles":"...","artists":[...],"sources":[...]}'),
    ("crafts", "coconut_craft",
     'Thủ công mỹ nghệ dừa Bến Tre: chạm khắc gáo dừa, sơ dừa, cọng dừa, product lines, export, artisan profiles. JSON: {"topic":"...","products":[...],"techniques":"...","artisans":[...],"value_chain":"...","innovation":"...","export":"...","sources":[...]}'),
    ("crafts", "food_processing",
     'Chế biến thực phẩm truyền thống 3 tỉnh: kẹo dừa, bánh tráng, bánh phồng, mắm, tương, process science. JSON: {"topic":"...","products":[...],"processes":[...],"science":"...","hygiene":"...","scale_up":"...","sources":[...]}'),

    # === KHẢO CỔ HỌC ===
    ("archaeology", "oc_eo_culture",
     'Khảo cổ học văn hóa Óc Eo liên hệ 3 tỉnh: di chỉ, hiện vật, thương mại biển, Hindu-Buddhist, carbon dating. JSON: {"topic":"...","sites":[...],"artifacts":[...],"trade_routes":"...","chronology":"...","significance":"...","sources":[...]}'),
    ("archaeology", "prehistoric",
     'Khảo cổ học tiền sử ĐBSCL: Holocene, hình thành châu thổ, cư dân đầu tiên, công cụ đá, di chỉ 3 tỉnh. JSON: {"topic":"...","geology":"...","early_settlements":[...],"artifacts":"...","dating":"...","interpretation":"...","sources":[...]}'),

    # === NHÂN KHẨU HỌC ===
    ("demographics", "ethnic_mosaic",
     'Nhân khẩu học chi tiết 3 tỉnh: Kinh/Khmer/Hoa/Chăm %, phân bố theo huyện, xu hướng, urbanization, fertility. JSON: {"topic":"...","by_province":[...],"by_district":[...],"trends":"...","urbanization":"...","projections":"...","sources":[...]}'),
    ("demographics", "migration",
     'Di cư lao động 3 tỉnh: push-pull, HCMC corridor, remittance, brain drain, return migration, social impact. JSON: {"topic":"...","patterns":[...],"economics":"...","social_impact":"...","remittance":"...","policy":"...","sources":[...]}'),

    # === DU LỊCH TÂM LINH ===
    ("spiritual", "pilgrimage_routes",
     'Du lịch tâm linh 3 tỉnh: hành hương chùa Khmer, Phật giáo Đại thừa, Công giáo, Cao Đài, miếu dân gian, map routes. JSON: {"topic":"...","routes":[...],"major_sites":[...],"festivals":[...],"etiquette":"...","accommodation":"...","sources":[...]}'),
    ("spiritual", "sacred_trees_water",
     'Cây thiêng & nước thiêng 3 tỉnh: cây bồ đề, đa, sao, giếng cổ, suối, sông thiêng, tín ngưỡng. JSON: {"topic":"...","sacred_trees":[...],"sacred_water":"...","beliefs":"...","protection":"...","tourism_potential":"...","sources":[...]}'),

    # === ẨM THỰC ĐƯỜNG PHỐ TỪNG HUYỆN ===
    ("street_food", "vl_districts",
     'Bản đồ ẩm thực đường phố TỪNG HUYỆN/THỊ Vĩnh Long: TP VL, Long Hồ, Mang Thít, Vũng Liêm, Tam Bình, Trà Ôn, Bình Tân, Bình Minh. JSON: {"topic":"...","districts":[{"name":"...","specialties":[...],"must_try":[...],"market":"..."}...],"sources":[...]}'),
    ("street_food", "bt_districts",
     'Bản đồ ẩm thực đường phố TỪNG HUYỆN/THỊ Bến Tre: TP BT, Châu Thành, Chợ Lách, Mỏ Cày Bắc/Nam, Giồng Trôm, Bình Đại, Ba Tri, Thạnh Phú. JSON: {"topic":"...","districts":[{"name":"...","specialties":[...],"must_try":[...],"market":"..."}...],"sources":[...]}'),
    ("street_food", "tv_districts",
     'Bản đồ ẩm thực đường phố TỪNG HUYỆN/THỊ Trà Vinh: TP TV, Càng Long, Cầu Kè, Tiểu Cần, Châu Thành, Trà Cú, Duyên Hải, Cầu Ngang, Huyện TV. JSON: {"topic":"...","districts":[{"name":"...","specialties":[...],"must_try":[...],"market":"..."}...],"sources":[...]}'),

    # === NGHỆ THUẬT BIỂU DIỄN ===
    ("performing_arts", "ro_bam",
     'Rô Băm (múa mặt nạ Khmer) Trà Vinh: lịch sử, kịch bản Reamker, mặt nạ, nhạc đệm, đoàn biểu diễn, UNESCO. JSON: {"topic":"...","history":"...","repertoire":[...],"mask_art":"...","music":"...","troupes":[...],"revival":"...","sources":[...]}'),
    ("performing_arts", "du_ke",
     'Dù Kê (opera Khmer) Nam Bộ: hình thành, ảnh hưởng cải lương, kịch bản, star system, đoàn 3 tỉnh. JSON: {"topic":"...","evolution":"...","repertoire":[...],"performers":[...],"influence":"...","current_state":"...","sources":[...]}'),
    ("performing_arts", "hat_boi",
     'Hát Bội & sân khấu truyền thống 3 tỉnh: đình diễn, lễ Kỳ Yên, tuồng tích, phục trang, decline. JSON: {"topic":"...","history":"...","repertoire":"...","costumes":"...","venues":[...],"rituals":"...","preservation":"...","sources":[...]}'),

    # === GIÁO DỤC & Y TẾ ===
    ("social_infra", "education",
     'Hệ thống giáo dục 3 tỉnh: trường học, đại học, literacy, Khmer bilingual ed, vocational, digital divide. JSON: {"topic":"...","by_province":[...],"higher_ed":[...],"bilingual":"...","vocational":"...","challenges":"...","sources":[...]}'),
    ("social_infra", "healthcare",
     'Hệ thống y tế 3 tỉnh: bệnh viện, trạm y tế, bác sĩ/vạn dân, bệnh đặc thù, y tế cộng đồng Khmer. JSON: {"topic":"...","by_province":[...],"facilities":[...],"health_indicators":"...","traditional_medicine":"...","challenges":"...","sources":[...]}'),

    # === HẠ TẦNG GIAO THÔNG ===
    ("infrastructure", "road_network",
     'Hạ tầng đường bộ 3 tỉnh: quốc lộ, tỉnh lộ, cầu lớn (Mỹ Thuận 2, Rạch Miễu 2, Cổ Chiên, Đại Ngãi), quy hoạch 2030. JSON: {"topic":"...","highways":[...],"bridges":[...],"projects":[...],"connectivity":"...","impact_tourism":"...","sources":[...]}'),
    ("infrastructure", "river_transport",
     'Giao thông đường thủy 3 tỉnh: bến phà, đò, tuyến vận tải, cảng, logistics, du lịch đường sông. JSON: {"topic":"...","routes":[...],"ferries":[...],"ports":[...],"river_tourism":"...","modernization":"...","sources":[...]}'),
    ("infrastructure", "digital_infra",
     'Hạ tầng số 3 tỉnh: 4G/5G, fiber, WiFi công cộng, chính quyền điện tử, fintech, e-commerce nông thôn. JSON: {"topic":"...","coverage":[...],"e_government":"...","fintech":"...","e_commerce":"...","challenges":"...","sources":[...]}'),

    # === CHUỖI GIÁ TRỊ NÔNG SẢN ===
    ("value_chain", "coconut_full",
     'Chuỗi giá trị dừa Bến Tre chi tiết: 72,000 ha, 200+ sản phẩm, coir/copra/VCO/nata/charcoal/cosmetics, export $200M+. JSON: {"topic":"...","production":"...","products":[...],"processing":[...],"export":"...","innovation":"...","sustainability":"...","sources":[...]}'),
    ("value_chain", "fruit_chain",
     'Chuỗi giá trị trái cây 3 tỉnh: bưởi Năm Roi, chôm chôm, nhãn, sầu riêng, GAP, cold chain, export. JSON: {"topic":"...","fruits":[...],"production":"...","quality":"...","logistics":"...","export":"...","challenges":"...","sources":[...]}'),
    ("value_chain", "rice_chain",
     'Chuỗi giá trị lúa gạo 3 tỉnh: giống, canh tác, xay xát, thương lái, export, ST25, organic. JSON: {"topic":"...","varieties":[...],"production":"...","milling":"...","trade":"...","quality":"...","sources":[...]}'),
    ("value_chain", "aquaculture_chain",
     'Chuỗi giá trị thủy sản 3 tỉnh: tôm sú/thẻ, cá tra, nghêu, cua, nuôi trồng, chế biến, ASC/BAP. JSON: {"topic":"...","species":[...],"farming":"...","processing":[...],"certification":"...","challenges":"...","sources":[...]}'),

    # === THỂ THAO & GIẢI TRÍ ===
    ("recreation", "traditional_games",
     'Trò chơi dân gian & thể thao truyền thống 3 tỉnh: đua ghe ngo, bơi xuồng, kéo co, đá cầu, cờ tướng, wrestling Khmer. JSON: {"topic":"...","games":[...],"festivals":[...],"events":[...],"preservation":"...","sources":[...]}'),
    ("recreation", "modern_leisure",
     'Giải trí hiện đại 3 tỉnh: karaoke, billiard, internet cafe, gym, swimming, soccer, parks. JSON: {"topic":"...","facilities":[...],"youth_culture":"...","nightlife":"...","trends":"...","sources":[...]}'),

    # === ĐỊA DANH HỌC ===
    ("toponymy", "place_names",
     'Địa danh học 3 tỉnh: nguồn gốc tên Khmer/Hoa/Việt, biến đổi qua thời gian, câu chuyện đằng sau tên. JSON: {"topic":"...","origins":[...],"khmer_roots":[...],"chinese_influence":[...],"transformations":"...","stories":[...],"sources":[...]}'),

    # === SINH THÁI CHI TIẾT ===
    ("ecology_deep", "wetland_services",
     'Dịch vụ hệ sinh thái đất ngập nước 3 tỉnh: lọc nước, chống lũ, đa dạng sinh học, carbon, valuation. JSON: {"topic":"...","services":[...],"biodiversity":[...],"carbon_stock":"...","economic_value":"...","threats":"...","sources":[...]}'),
    ("ecology_deep", "mangrove_detailed",
     'Rừng ngập mặn chi tiết BT-TV: loài cây, zonation, fauna, blue carbon, nuôi tôm-rừng, REDD+. JSON: {"topic":"...","species":[...],"zonation":"...","fauna":[...],"carbon":"...","shrimp_mangrove":"...","projects":[...],"sources":[...]}'),
    ("ecology_deep", "freshwater_fish",
     'Ngư loại học cá nước ngọt 3 tỉnh: inventory 100+ loài, endemic, invasive, IUCN status, fishing culture. JSON: {"topic":"...","species":[...],"endemic":"...","invasive":"...","conservation":"...","fishing_methods":"...","sources":[...]}'),

    # === VĂN HỌC & FOLKLORE ===
    ("literature", "folk_literature",
     'Văn học dân gian 3 tỉnh: ca dao, hò, vè, truyện cổ tích, truyền thuyết, thần thoại Khmer, Hoa. JSON: {"topic":"...","genres":[...],"examples":[...],"khmer_tales":[...],"themes":"...","preservation":"...","sources":[...]}'),
    ("literature", "modern_writers",
     'Văn học hiện đại 3 tỉnh: nhà văn, nhà thơ, tác phẩm, chủ đề ĐBSCL, Sơn Nam, Nguyễn Ngọc Tư. JSON: {"topic":"...","writers":[...],"works":[...],"themes":"...","influence":"...","sources":[...]}'),

    # === KIẾN TRÚC NÂNG CAO ===
    ("architecture_deep", "thermal_design",
     'Nhiệt động học kiến trúc dân gian ĐBSCL: thông gió tự nhiên, mái lá, vật liệu cách nhiệt, bioclimatic principles. JSON: {"topic":"...","principles":[...],"traditional_solutions":"...","materials":"...","modern_adaptation":"...","lessons":"...","sources":[...]}'),
    ("architecture_deep", "colonial_mapping",
     'Bản đồ hạ tầng thuộc địa Pháp 3 tỉnh: tòa hành chính, nhà thờ, trường, bệnh viện, chợ, cầu, kênh. JSON: {"topic":"...","inventory":[...],"architectural_styles":"...","condition":"...","heritage_value":"...","adaptive_reuse":"...","sources":[...]}'),

    # === TÔN GIÁO SÂU ===
    ("religion_deep", "khmer_theravada",
     'Phật giáo Theravada Khmer TV chi tiết: 142 chùa, hierarchy, bonze education, Pali manuscripts, role xã hội. JSON: {"topic":"...","monasteries":[...],"organization":"...","education":"...","manuscripts":"...","social_role":"...","challenges":"...","sources":[...]}'),
    ("religion_deep", "folk_beliefs",
     'Tín ngưỡng dân gian 3 tỉnh: thờ Bà, ông Tà (Neak Ta), thần Nông, cá Ông, miếu, medium, geomancy. JSON: {"topic":"...","deities":[...],"practices":[...],"mediums":"...","festivals":"...","spatial_pattern":"...","sources":[...]}'),

    # === CHUYỂN ĐỔI SỐ NÔNG THÔN ===
    ("digital", "agritech",
     'Agritech & smart farming 3 tỉnh: IoT, drone, precision agriculture, marketplace, case studies. JSON: {"topic":"...","technologies":[...],"adoption":"...","case_studies":[...],"barriers":"...","potential":"...","sources":[...]}'),
    ("digital", "social_media_local",
     'Social media & creator economy 3 tỉnh: TikTok/YouTube/Facebook local influencers, food bloggers, farm-to-table livestream. JSON: {"topic":"...","platforms":[...],"creators":[...],"content_types":"...","economic_impact":"...","tourism_promotion":"...","sources":[...]}'),
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
