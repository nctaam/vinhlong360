#!/usr/bin/env python3
"""MEGA EXPERT — Nghiên cứu CẤP CHUYÊN GIA ĐẦU NGÀNH.

Vượt xa guide du lịch thông thường. Đây là nghiên cứu ở cấp:
- Tiến sĩ văn hóa học / nhân học
- Chuyên gia địa lý học / sinh thái học
- Nhà sử học vùng ĐBSCL
- Kiến trúc sư di sản
- Nhà kinh tế du lịch
- Food scientist
- Ethnographer
- Urban planner

Modes:
  --mode anthropology       : Nhân học văn hóa 3 dân tộc (Việt-Khmer-Hoa)
  --mode ecology-science    : Sinh thái học khoa học (hệ sinh thái, biodiversity)
  --mode food-science       : Khoa học ẩm thực (vi sinh, lên men, maillard...)
  --mode architecture       : Kiến trúc di sản (phân tích chuyên sâu mỗi công trình)
  --mode economics          : Kinh tế du lịch (phân tích SWOT, value chain)
  --mode history-academic   : Sử học hàn lâm (thời kỳ, biến cố, primary sources)
  --mode geography-deep     : Địa lý tự nhiên (thủy văn, trầm tích, khí hậu vi mô)
  --mode sociology          : Xã hội học nông thôn (cộng đồng, di cư, đô thị hóa)
  --mode linguistics        : Ngôn ngữ học (phương ngữ, địa danh, etymology)
  --mode religion           : Tôn giáo tín ngưỡng (syncretism Phật-Khmer-Hoa-dân gian)
  --mode music              : Âm nhạc học (đờn ca tài tử, nhạc Khmer, cải lương)
  --mode agriculture        : Nông học (giống lúa, cây ăn trái, OCOP, GAP)
  --mode hydrology          : Thủy văn học (sông Mekong, triều, xâm nhập mặn)
  --mode tourism-strategy   : Chiến lược du lịch (market analysis, positioning)
  --mode photography        : Nhiếp ảnh (golden hour, composition, locations)
  --mode wellness           : Sức khỏe & wellness (spa, yoga, healing, detox)
  --mode nightlife          : Đời sống về đêm (chợ đêm, quán, hoạt động)
  --mode children           : Du lịch trẻ em (giáo dục, trải nghiệm, an toàn)
  --mode romance            : Du lịch tình yêu (honeymoon, proposal spots)
  --mode accessibility      : Du lịch tiếp cận (xe lăn, người cao tuổi, khiếm thị)
  --mode all                : TẤT CẢ

Usage:
  python -u agent/scripts/mega_expert.py --mode all --workers 3
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
OUTPUT_DIR = AGENT_DIR / "data" / "mega_research" / "expert"

sys.path.insert(0, str(AGENT_DIR))
sys.path.insert(0, str(AGENT_DIR / "scripts"))
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_DIR / ".env")
except Exception:
    pass

from mega_research import (LLM, read_jsonl, append_jsonl, log, utc, _cfg_io)

SYS_EXPERT = """Bạn là CHUYÊN GIA ĐẦU NGÀNH — cấp tiến sĩ, giáo sư — về lĩnh vực được hỏi.
Bạn am hiểu sâu sắc vùng ĐBSCL (Vĩnh Long, Bến Tre, Trà Vinh).
Viết ở trình độ học thuật NHƯNG dễ hiểu. Dùng thuật ngữ chuyên ngành kèm giải thích.
Đan xen kiến thức sách vở với thực địa. Trích dẫn nghiên cứu/tác giả khi phù hợp.
KHÔNG bịa dữ liệu. Nếu không chắc → nói rõ "cần kiểm chứng".
Mỗi phân tích phải có GÓC NHÌN MỚI mà du khách thông thường KHÔNG biết.

QUAN TRỌNG: Trả lời bằng JSON thuần túy (bắt đầu { kết thúc }).
Viết CỰC KỲ CHI TIẾT — ít nhất 3000 ký tự. Phân tích SÂU, không hời hợt."""


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
# ANTHROPOLOGY — Nhân học văn hóa
# ═══════════════════════════════════════════════════════════════════════

ANTHRO_TOPICS = [
    ("viet_khmer_coexistence", """Phân tích NHÂN HỌC VĂN HÓA về mối quan hệ cộng sinh Việt-Khmer ở Trà Vinh:
- Lịch sử giao thoa: từ Đế quốc Khmer → Nguyễn triều → hiện đại
- Identity negotiation: người Khmer duy trì bản sắc thế nào?
- Food exchange: món ăn nào là "creole" (lai Việt-Khmer)?
- Ritual syncretism: nghi lễ nào pha trộn Phật giáo Theravada + Đại thừa + dân gian?
- Marriage patterns: tỷ lệ hôn nhân liên sắc tộc?
- Language shift: Khmer đang mất dần? Trẻ em còn nói Khmer?
- Sacred spaces: pagoda Khmer vs đình/chùa Việt — ranh giới hay giao thoa?
- Economic niches: phân công lao động theo sắc tộc?
- Tourism impact: du lịch đang giúp hay làm mất bản sắc?"""),

    ("hoa_community_delta", """Phân tích NHÂN HỌC về cộng đồng người Hoa ở Vĩnh Long-Bến Tre-Trà Vinh:
- Di cư waves: Minh Hương, Triều Châu, Phúc Kiến, Quảng Đông — ai đến khi nào?
- Hội quán & miếu: vai trò xã hội ngoài tôn giáo
- Thương mại: từ tiệm thuốc Bắc, tiệm vàng → hiện đại hóa thế nào?
- Ẩm thực Hoa-Việt fusion: hủ tiếu, mì, bánh bao biến đổi ra sao?
- Assimilation patterns: thế hệ 3-4 còn giữ gì?
- Phong thủy trong kiến trúc dân gian
- Tết Nguyên Tiêu, Vu Lan, Thanh Minh — thực hành ở ĐBSCL khác TQ thế nào?"""),

    ("water_culture", """Phân tích NHÂN HỌC về VĂN HÓA SÔNG NƯỚC ĐBSCL:
- Ontology: sông nước là "nhà" — worldview khác với văn hóa đất liền thế nào?
- Habitus (Bourdieu): cơ thể, cử chỉ, kỹ năng từ sống trên nước
- Gender roles trên ghe xuồng: phụ nữ chèo, đàn ông kéo lưới?
- Market as social institution: chợ nổi không chỉ mua bán — courtship, gossip, politics
- Navigation knowledge: đọc sông, đọc triều — Indigenous Knowledge Systems
- Naming practices: tên sông, rạch, cù lao — toponymy phản ánh gì?
- Death & water: tang lễ sông nước, kiêng kỵ, ma sông
- Climate change adaptation: "sống chung với lũ" — resilience hay vulnerability?
- Modernization: cầu bê tông thay đò ngang — mất gì?"""),

    ("ritual_calendar", """Phân tích NHÂN HỌC TÔN GIÁO về LỊCH NGHI LỄ ở 3 tỉnh (12 tháng):
Với MỖI THÁNG liệt kê tất cả nghi lễ/lễ hội:
- Âm lịch: Tết, rằm, ngày vía, lễ cúng đình, giỗ tổ nghề...
- Phật lịch Theravada (Khmer): Chol Chnam Thmay, Pchum Ben, Ok Om Bok, Kathin...
- Phật lịch Đại thừa (Việt): Vu Lan, Phật Đản...
- Dương lịch: lễ hội hiện đại, sự kiện du lịch
- Agricultural cycle: cúng ruộng, cúng mùa, lễ đặt cây
- Overlap & fusion: khi nhiều truyền thống trùng ngày
Phân tích ý nghĩa COSMOLOGICAL, SOCIAL, ECONOMIC của mỗi nghi lễ."""),

    ("craft_anthropology", """Phân tích NHÂN HỌC KINH TẾ về LÀNG NGHỀ 3 tỉnh:
- Skill transmission: master-apprentice hay gia đình? Đang đứt gãy?
- Material culture: nguyên liệu → kỹ thuật → sản phẩm → meaning
- Gendered labor: nghề nào của phụ nữ, nam? Tại sao?
- Commodity chains: từ nghệ nhân → thương lái → thị trường → du khách
- Authenticity paradox: du lịch đòi "truyền thống" nhưng thị trường đòi "mới"
- Hàng nhái vs handmade: phân biệt thế nào? Giá trị ở đâu?
- UNESCO intangible heritage: ý nghĩa thực vs bureaucratic recognition
- Comparative: so sánh với làng nghề Nhật Bản/Thái Lan"""),
]


def anthropology(llm, workers=3):
    log("═══ EXPERT: ANTHROPOLOGY ═══")
    f = OUTPUT_DIR / "anthropology.jsonl"
    done = {r.get("key") for r in read_jsonl(f)}
    topics = [(k, p) for k, p in ANTHRO_TOPICS if k not in done]
    log(f"  {len(topics)} anthropology topics")
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(_gen, llm, f, k, SYS_EXPERT, p, 6000) for k, p in topics]
        for fut in as_completed(futs):
            try: fut.result()
            except Exception as e: log(f"  ERR: {e}")


# ═══════════════════════════════════════════════════════════════════════
# ECOLOGY-SCIENCE — Sinh thái học
# ═══════════════════════════════════════════════════════════════════════

ECO_TOPICS = [
    ("mekong_ecosystem", """Phân tích SINH THÁI HỌC hệ thống sông Mekong đoạn ĐBSCL:
- Trophic levels: từ phytoplankton → cá → chim → con người
- Seasonal flood pulse: Junk flood pulse concept áp dụng vào ĐBSCL
- Wetland services: water purification, carbon sequestration, flood attenuation — lượng hóa
- Biodiversity hotspots: vùng nào ở 3 tỉnh đa dạng nhất? Tại sao?
- Endangered species: loài nào Red List? Tình trạng bảo tồn?
- Invasive species: lục bình, cá rô phi, ốc bưu vàng — ecological impact
- Dam impact: đập thượng nguồn (TQ, Lào) → giảm phù sa → hậu quả gì?
- Mangrove loss: tỷ lệ mất rừng ngập mặn ven biển 3 tỉnh
- Ecosystem-based adaptation: giải pháp dựa vào hệ sinh thái"""),

    ("bird_ecology", """Phân tích ĐIỂU HỌC (ornithology) vùng 3 tỉnh:
- Species inventory: tất cả loài chim đã ghi nhận (resident + migratory)
- Breeding colonies: vườn cò, sân chim — nơi nào, bao nhiêu cá thể?
- Migration routes: East Asian-Australasian Flyway đi qua đâu?
- Important Bird Areas (IBAs): đã được BirdLife International công nhận?
- Flagship species: sếu đầu đỏ, cò lạo, diệc — conservation status
- Birding itinerary: lịch trình cho birder chuyên nghiệp (tháng, giờ, vị trí)
- Citizen science: eBird data cho vùng này?
- Threats: hunting, habitat loss, pesticides
- Eco-tourism potential: so sánh với Tràm Chim, U Minh"""),

    ("fruit_ecology", """Phân tích THỰC VẬT HỌC NÔNG NGHIỆP về CÂY ĂN TRÁI:
- Cultivar diversity: giống chôm chôm, sầu riêng, nhãn, bưởi ở VL-BT-TV
- Soil-climate interaction: tại sao bưởi Năm Roi ở Bình Minh ngon nhất?
- Pollination ecology: côn trùng thụ phấn cho vườn cây ăn trái
- Phenology: lịch ra hoa, đậu quả, chín — theo từng giống
- Post-harvest physiology: bảo quản trái cây nhiệt đới — ethylene, respiration
- Agroforestry systems: vườn dừa + cacao + chuối — polyculture ĐBSCL
- Climate change impact: nước mặn → stress → chất lượng quả thay đổi?
- Traditional ecological knowledge: nông dân biết gì mà khoa học chưa ghi nhận?"""),

    ("coastal_ecosystem", """Phân tích SINH THÁI BIỂN VEN BỜ Trà Vinh - Bến Tre:
- Mangrove zonation: Rhizophora, Avicennia, Sonneratia — phân bố thế nào?
- Mudflat ecology: sinh vật đáy, vi khuẩn, chuỗi thức ăn
- Fisheries ecology: tôm sú, cua, nghêu — lifecycle trong hệ sinh thái
- Seagrass beds: có không? Tầm quan trọng?
- Erosion & accretion: bờ biển nào đang lở, nào đang bồi? Tốc độ?
- Aquaculture impact: nuôi tôm → phá rừng → salinization → feedback loop
- Blue carbon: tiềm năng tín chỉ carbon rừng ngập mặn
- Community-based management: mô hình quản lý cộng đồng nào thành công?"""),
]


def ecology_science(llm, workers=3):
    log("═══ EXPERT: ECOLOGY SCIENCE ═══")
    f = OUTPUT_DIR / "ecology_science.jsonl"
    done = {r.get("key") for r in read_jsonl(f)}
    topics = [(k, p) for k, p in ECO_TOPICS if k not in done]
    log(f"  {len(topics)} ecology topics")
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(_gen, llm, f, k, SYS_EXPERT, p, 6000) for k, p in topics]
        for fut in as_completed(futs):
            try: fut.result()
            except Exception as e: log(f"  ERR: {e}")


# ═══════════════════════════════════════════════════════════════════════
# FOOD-SCIENCE — Khoa học ẩm thực
# ═══════════════════════════════════════════════════════════════════════

FOOD_TOPICS = [
    ("fermentation_science", """Phân tích KHOA HỌC LÊN MEN trong ẩm thực ĐBSCL:
- Nước mắm: proteolysis, amino acid profile, histamine risk
- Mắm cá: so sánh mắm cá linh, mắm cá lóc, mắm cá sặc — vi sinh khác nhau?
- Dưa cải: Lactobacillus fermentation, pH curve, probiotic benefits
- Rượu nếp: Saccharomyces + Amylomyces — co-culture fermentation
- Bánh tráng: rice starch gelatinization, retrogradation, texture
- Chuối ép: enzymatic browning, polyphenol oxidase
- Kẹo dừa: Maillard reaction, caramelization temperature
- Tương hột: koji fermentation ở climate nhiệt đới
- Food safety: mycotoxin risk trong sản phẩm lên men truyền thống"""),

    ("coconut_science", """Phân tích KHOA HỌC DỪA — từ botany đến food technology:
- Cocos nucifera: cultivar ở Bến Tre (dừa xiêm, dừa ta, dừa dâu, dừa sáp)
- Coconut water: electrolyte composition, sterility, medical use
- Coconut milk: emulsion science, creaming, homogenization
- Virgin coconut oil: extraction methods, MCT content, health claims (evidence-based)
- Coconut sugar: glycemic index, sustainability vs cane sugar
- Nata de coco: bacterial cellulose from Komagataeibacter xylinus
- Copra processing: drying methods, aflatoxin risk
- Coconut fiber (coir): material science, construction applications
- Carbon footprint: coconut farming vs other tropical crops"""),

    ("mekong_fish_gastronomy", """Phân tích KHOA HỌC ẨM THỰC CÁ sông Mekong:
- Species tasting profiles: cá basa, cá tra, cá lóc, cá linh, cá chạch, cá cháy — flavor compounds
- Cooking chemistry: kho → Maillard; nướng → pyrolysis; hấp → steam distillation
- Texture science: protein denaturation temperature cho từng loài
- Umami: glutamate & nucleotide content — cá nào "ngon" nhất về mặt hóa học?
- Seasonal variation: mùa nước lên cá béo hơn? Fatty acid profile thay đổi?
- Smoking & drying: traditional preservation — water activity, shelf life
- Parasitology: Opisthorchis viverrini — risk khi ăn gỏi cá
- Aquaculture vs wild-caught: flavor & texture comparison
- Declining stocks: overfishing impact on culinary tradition"""),

    ("rice_science", """Phân tích KHOA HỌC GẠO ĐBSCL:
- Varieties: IR50404, OM5451, ST25, nếp — amylose/amylopectin ratio
- Terroir effect: phù sa → khoáng chất → flavor profile
- Milling degree: gạo lứt → gạo trắng — nutrient loss
- Cơm tấm science: broken rice — why different texture? Starch structure
- Bánh science: bột gạo + nước → viscosity, gel strength — chuẩn cho từng loại bánh
- Rice noodle: hủ tiếu, bún, phở — extrusion, retrogradation, texture
- Cháo: starch gelatinization kinetics, mouth-feel optimization
- Rice wine: amylolytic fermentation, flavor volatiles
- Nutrition: GI comparison, arsenic in rice, fortification potential"""),
]


def food_science(llm, workers=3):
    log("═══ EXPERT: FOOD SCIENCE ═══")
    f = OUTPUT_DIR / "food_science.jsonl"
    done = {r.get("key") for r in read_jsonl(f)}
    topics = [(k, p) for k, p in FOOD_TOPICS if k not in done]
    log(f"  {len(topics)} food science topics")
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(_gen, llm, f, k, SYS_EXPERT, p, 6000) for k, p in topics]
        for fut in as_completed(futs):
            try: fut.result()
            except Exception as e: log(f"  ERR: {e}")


# ═══════════════════════════════════════════════════════════════════════
# ARCHITECTURE — Kiến trúc di sản
# ═══════════════════════════════════════════════════════════════════════

ARCH_TOPICS = [
    ("khmer_pagoda_architecture", """Phân tích KIẾN TRÚC HỌC chùa Khmer ở Trà Vinh:
- Typology: chánh điện (vihara), sala, stupa, cổng (gopura) — plan, section
- Structural system: timber frame, masonry, modern RC — evolution
- Naga symbolism: rắn thần trên mái — Angkorian origin → ĐBSCL adaptation
- Polychrome decoration: sơn, vẽ, khảm — materials, techniques, iconography
- Spatial organization: sân, hồ sen, cây bồ đề, tháp cốt — cosmological meaning
- Restoration challenges: traditional vs modern materials — authenticity debate
- Climate adaptation: thông gió tự nhiên, mái dốc cho mưa nhiệt đới
- Comparative: so sánh với Angkor Wat, chùa Khmer Thái Lan/Campuchia
- Notable examples: Âng, Hang, Vàm Ray, Cò — phân tích chi tiết"""),

    ("french_colonial_architecture", """Phân tích KIẾN TRÚC THUỘC ĐỊA PHÁP ở 3 tỉnh:
- Inventory: nhà cổ, dinh thự, nhà thờ, trường học, chợ — còn bao nhiêu?
- Style classification: néo-classique, art déco, indochinois — đặc điểm
- Material technology: bê tông cốt thép đầu tiên, gạch Marseille, sắt đúc
- Adaptation tropicale: vérandah, jalousie, aération haute — tropical solution
- Social history: ai xây, ai ở, ai sử dụng hiện tại?
- Conservation status: đang được bảo vệ hay phá dỡ?
- Heritage tourism potential: route kiến trúc thuộc địa
- Notable: Nhà Long Hồ, Tòa hành chính cũ, nhà thờ Cái Mơn"""),

    ("vernacular_architecture", """Phân tích KIẾN TRÚC DÂN GIAN ĐBSCL:
- Nhà sàn: structural logic cho vùng ngập
- Nhà 3 gian: plan type, orientation (phong thủy vs practical)
- Materials: gỗ sao, gỗ dầu, lá dừa nước, đất — properties & availability
- Construction ritual: chọn ngày, dựng cột, cúng nhà
- Thermal comfort: passive cooling strategies — stack effect, cross ventilation
- Evolution: nhà trệt → nhà lầu → nhà phố → apartment — mất gì?
- Floating architecture: nhà bè, ghe ở — unique ĐBSCL typology
- Garden integration: cây ăn trái + nhà = living architecture
- Contemporary reinterpretation: homestay hiện đại vận dụng kiến trúc truyền thống"""),
]


def architecture(llm, workers=3):
    log("═══ EXPERT: ARCHITECTURE ═══")
    f = OUTPUT_DIR / "architecture.jsonl"
    done = {r.get("key") for r in read_jsonl(f)}
    topics = [(k, p) for k, p in ARCH_TOPICS if k not in done]
    log(f"  {len(topics)} architecture topics")
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(_gen, llm, f, k, SYS_EXPERT, p, 6000) for k, p in topics]
        for fut in as_completed(futs):
            try: fut.result()
            except Exception as e: log(f"  ERR: {e}")


# ═══════════════════════════════════════════════════════════════════════
# ECONOMICS — Kinh tế du lịch
# ═══════════════════════════════════════════════════════════════════════

ECON_TOPICS = [
    ("swot_vl", "Phân tích SWOT CỰC CHI TIẾT du lịch Vĩnh Long — 20+ điểm mỗi mục, so sánh với competitor (Cần Thơ, An Giang), market size estimation, growth forecast 5 năm, investment needed, ROI analysis"),
    ("swot_bt", "Phân tích SWOT CỰC CHI TIẾT du lịch Bến Tre — xứ dừa positioning, coconut tourism value chain, competitor analysis, unique selling proposition, market segmentation, pricing strategy"),
    ("swot_tv", "Phân tích SWOT CỰC CHI TIẾT du lịch Trà Vinh — Khmer culture positioning, niche vs mass market, heritage tourism economics, community benefit sharing, leakage analysis"),
    ("value_chain", "Phân tích VALUE CHAIN du lịch ĐBSCL 3 tỉnh: từ marketing → booking → transport → accommodation → food → activities → shopping → review. Tính giá trị tạo ra và % local retention ở mỗi mắt xích. So sánh tour group vs FIT vs digital nomad"),
    ("carrying_capacity", "Phân tích CARRYING CAPACITY du lịch: physical CC, ecological CC, social CC, economic CC cho top 10 điểm đến 3 tỉnh. Hiện tại so với ngưỡng? Seasonality adjustment? Management strategies?"),
    ("digital_tourism", "Phân tích kinh tế DU LỊCH SỐ cho 3 tỉnh: SEO landscape, social media ROI, OTA dependency (Booking/Agoda/Traveloka), review economy, influencer impact, Google Maps optimization, AI chatbot potential, VR/360° tourism"),
]


def economics(llm, workers=3):
    log("═══ EXPERT: ECONOMICS ═══")
    f = OUTPUT_DIR / "economics.jsonl"
    done = {r.get("key") for r in read_jsonl(f)}
    topics = [(k, p) for k, p in ECON_TOPICS if k not in done]
    log(f"  {len(topics)} economics topics")
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(_gen, llm, f, k, SYS_EXPERT, p, 6000) for k, p in topics]
        for fut in as_completed(futs):
            try: fut.result()
            except Exception as e: log(f"  ERR: {e}")


# ═══════════════════════════════════════════════════════════════════════
# HISTORY-ACADEMIC — Sử học hàn lâm
# ═══════════════════════════════════════════════════════════════════════

HIST_TOPICS = [
    ("pre_colonial", "Sử học hàn lâm: vùng đất 3 tỉnh TRƯỚC thuộc địa Pháp — Thủy Chân Lạp, Nguyễn triều nam tiến, khai phá kênh rạch, dân cư Việt-Khmer-Hoa, hành chính trấn Vĩnh Long. Primary sources: Gia Định thành thông chí, Đại Nam thực lục"),
    ("colonial_period", "Sử học: thời thuộc Pháp ở 3 tỉnh — hạ tầng (kênh, đường, chợ), rubber plantations, rice export, mission chrétienne, resistance movements, intellectual awakening, Cochinchine administrative system"),
    ("war_period", "Sử học: 3 tỉnh trong 2 cuộc kháng chiến — strategic hamlet, Mekong operations, Tet offensive, revolutionary base areas, civilian experience, POW, herbicide impact, post-1975 transformation"),
    ("economic_history", "Sử học kinh tế: 3 tỉnh qua các thời kỳ — từ tự cung tự cấp → rice export economy → collectivization → Đổi Mới → WTO → hiện đại. Landholding patterns, market formation, credit systems"),
    ("religious_history", "Sử học tôn giáo ở 3 tỉnh: Phật giáo Theravada (Khmer), Phật giáo Đại thừa (Việt), Công giáo (mission), Cao Đài, Hòa Hảo, Tin Lành — timeline, influence, syncretism, state-religion relations"),
]


def history_academic(llm, workers=3):
    log("═══ EXPERT: HISTORY ACADEMIC ═══")
    f = OUTPUT_DIR / "history_academic.jsonl"
    done = {r.get("key") for r in read_jsonl(f)}
    topics = [(k, p) for k, p in HIST_TOPICS if k not in done]
    log(f"  {len(topics)} history topics")
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(_gen, llm, f, k, SYS_EXPERT, p, 6000) for k, p in topics]
        for fut in as_completed(futs):
            try: fut.result()
            except Exception as e: log(f"  ERR: {e}")


# ═══════════════════════════════════════════════════════════════════════
# GEOGRAPHY-DEEP — Địa lý tự nhiên
# ═══════════════════════════════════════════════════════════════════════

GEO_TOPICS = [
    ("hydrology", "Phân tích THỦY VĂN HỌC: hệ thống sông Tiền, sông Hậu, sông Cổ Chiên, sông Hàm Luông ở 3 tỉnh — lưu lượng theo mùa, bồi lắng, xâm nhập mặn, triều bán nhật, quy luật lũ, sediment transport, delta progradation rate"),
    ("geomorphology", "Phân tích ĐỊA MẠO HỌC: cù lao hình thành thế nào? Giồng cát là gì? Bãi bồi ven sông — geomorphic processes. Sụt lún đất — nguyên nhân, tốc độ. Coastal erosion ở Trà Vinh, Bến Tre — retreat rate"),
    ("climate_micro", "Phân tích KHÍ HẬU HỌC VI MÔ: microclimate khác nhau ở 3 tỉnh — nội đồng vs ven biển vs thành phố. Heat island effect. Gió mùa chi tiết. Extreme events: bão, hạn, ngập. Climate change projections 2030-2050"),
    ("soil_science", "Phân tích THỔ NHƯỠNG HỌC: phân loại đất ở 3 tỉnh — phù sa mới, phù sa cũ, đất phèn, đất mặn, đất cát giồng. FAO classification. Nutrient profile. Suitability cho từng loại cây. Land degradation threats"),
]


def geography_deep(llm, workers=3):
    log("═══ EXPERT: GEOGRAPHY ═══")
    f = OUTPUT_DIR / "geography_deep.jsonl"
    done = {r.get("key") for r in read_jsonl(f)}
    topics = [(k, p) for k, p in GEO_TOPICS if k not in done]
    log(f"  {len(topics)} geography topics")
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(_gen, llm, f, k, SYS_EXPERT, p, 6000) for k, p in topics]
        for fut in as_completed(futs):
            try: fut.result()
            except Exception as e: log(f"  ERR: {e}")


# ═══════════════════════════════════════════════════════════════════════
# MUSIC — Âm nhạc học
# ═══════════════════════════════════════════════════════════════════════

MUSIC_TOPICS = [
    ("don_ca_tai_tu_deep", "Phân tích ÂM NHẠC HỌC đờn ca tài tử UNESCO: 20 bài bản tổ, hệ thống điệu (Bắc, Hạ, Nam, Oán), nhạc cụ (đàn kìm, đàn tranh, đàn cò, guitar phím lõm), tuning systems, improvisation rules, so sánh với gamelan/raga, truyền dạy, performers nổi tiếng 3 tỉnh, tourism performance format"),
    ("khmer_music_deep", "Phân tích ÂM NHẠC KHMER NAM BỘ: nhạc ngũ âm (pinpeat), dàn nhạc lễ, nhạc dù kê, nhạc rô băm — scale systems, instruments (skor, roneat, khong), rhythmic patterns, sacred vs secular, relationship to Cambodian court music, endangered status, revival efforts"),
    ("cai_luong_deep", "Phân tích ÂM NHẠC HỌC CẢI LƯƠNG: từ đờn ca tài tử → cải lương — harmonic evolution, vọng cổ 6 câu → 20 câu, Western instrument integration, vocal techniques, famous troupes from 3 tỉnh, decline & revival, comparison with Peking opera/kabuki"),
]


def music(llm, workers=3):
    log("═══ EXPERT: MUSIC ═══")
    f = OUTPUT_DIR / "music.jsonl"
    done = {r.get("key") for r in read_jsonl(f)}
    topics = [(k, p) for k, p in MUSIC_TOPICS if k not in done]
    log(f"  {len(topics)} music topics")
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(_gen, llm, f, k, SYS_EXPERT, p, 6000) for k, p in topics]
        for fut in as_completed(futs):
            try: fut.result()
            except Exception as e: log(f"  ERR: {e}")


# ═══════════════════════════════════════════════════════════════════════
# SOCIOLOGY, LINGUISTICS, RELIGION, AGRICULTURE, HYDROLOGY
# ═══════════════════════════════════════════════════════════════════════

SOCIO_TOPICS = [
    ("rural_transformation", "XÃ HỘI HỌC NÔNG THÔN: đô thị hóa 3 tỉnh — youth migration, aging villages, remittance economy, land consolidation, social stratification, marriage market squeeze, social media impact, COVID aftermath"),
    ("tourism_sociology", "XÃ HỘI HỌC DU LỊCH: host-guest interaction ở 3 tỉnh — commodification of culture, staged authenticity, empowerment vs exploitation, community attitudes, pro-poor tourism, volunteer tourism critique"),
    ("gender_mekong", "GIỚI & DU LỊCH ĐBSCL: phụ nữ trong du lịch (homestay hostess, market vendor, craft worker) — empowerment or double burden? Masculinity & fishing/farming. LGBTQ+ tourism potential. Safety for solo female travelers"),
]

LING_TOPICS = [
    ("dialect_study", "NGÔN NGỮ HỌC: phương ngữ miền Tây ở 3 tỉnh — phonological features (thanh điệu, âm đầu, vần), lexical differences, endangered Khmer dialects, Hoa loanwords, code-switching, diglossia, toponymy (tên sông, rạch, cù lao — origin stories)"),
    ("food_linguistics", "NGÔN NGỮ HỌC ẨM THỰC: etymology tên món ăn miền Tây — nguồn gốc Khmer (bún nước lèo, num bò chóc), Hoa (hủ tiếu, mì), Pháp (bánh mì, café), Sanskrit (cà ri). Onomatopoeia: bánh xèo, bánh tráng nướng"),
]

RELIG_TOPICS = [
    ("syncretism", "TÔN GIÁO HỌC: syncretism tôn giáo ở 3 tỉnh — Theravada + Mahayana + folk religion + Confucianism + Taoism. Case studies: chùa Khmer thờ Quan Âm, đình Việt có yếu tố Hoa, tín ngưỡng Bà Chúa Xứ. Ritual specialists: sư Khmer, thầy cúng, bà đồng"),
    ("death_rituals", "NHÂN HỌC TÔN GIÁO: nghi lễ tang ma ở 3 tỉnh — Việt (3 ngày, 49 ngày, giỗ), Khmer (hỏa táng, Pchum Ben), Hoa (Thanh Minh, đốt giấy). Funeral architecture: tháp cốt Khmer, mộ Việt, mộ Hoa. Death taboos & tourism sensitivity"),
]

AGRI_TOPICS = [
    ("ocop_deep", "NÔNG HỌC & KINH TẾ OCOP: chương trình OCOP ở 3 tỉnh — tiêu chí 3-5 sao, sản phẩm nào đạt cao nhất, quy trình đánh giá, GAP/GMP requirements, market access, e-commerce potential, success stories vs failures, so sánh với OTOP Thái Lan"),
    ("aquaculture_science", "THỦY SẢN HỌC: nuôi trồng thủy sản 3 tỉnh — tôm sú, tôm thẻ, cá tra, nghêu — production volume, technology (biofloc, RAS), environmental impact, certification (ASC, BAP), economic viability, climate vulnerability"),
]

TOURISM_STRAT = [
    ("positioning_strategy", "CHIẾN LƯỢC ĐỊNH VỊ du lịch: phân tích Porter's Five Forces, Blue Ocean Strategy cho 3 tỉnh. Target segments: domestic weekend, HCMC day-trip, international backpacker, luxury experiential, MICE, voluntourism. Brand architecture: umbrella brand vs individual province brands"),
    ("digital_marketing", "MARKETING SỐ DU LỊCH: content strategy (blog, video, podcast), SEO cho từng nhóm từ khóa, social media (TikTok, Instagram, YouTube, Zalo OA), KOL collaboration framework, Google Business Profile optimization, review management, email nurturing, retargeting"),
    ("sustainable_tourism", "DU LỊCH BỀN VỮNG: GSTC criteria áp dụng cho 3 tỉnh, carbon footprint per tourist, water usage, waste management, social license to operate, community-based tourism models, eco-certification feasibility, green financing options"),
]

PHOTO_TOPICS = [
    ("photography_guide", "HƯỚNG DẪN NHIẾP ẢNH chuyên nghiệp 3 tỉnh: golden hour timing theo mùa, blue hour spots, composition techniques cho landscape sông nước, portrait of locals (ethics!), food photography settings, drone regulations & best locations, astrophotography spots (light pollution map), recommended gear, post-processing style cho aesthetic miền Tây"),
]

SPECIAL_TOPICS = [
    ("wellness_tourism", "DU LỊCH SỨC KHỎE: spa truyền thống (xông hơi lá, massage dừa), yoga retreats potential, meditation at pagodas, forest bathing (shinrin-yoku) ở rừng tràm, thermal springs?, healthy food tours, digital detox programs, silence retreat concept"),
    ("nightlife_guide", "ĐỜI SỐNG VỀ ĐÊM chi tiết 3 tỉnh: chợ đêm (thời gian, vị trí, món ăn), quán cà phê đêm, karaoke, live music venues, river cruises, night markets, street food after 10pm, safety tips, romantic spots at night, photography at night"),
    ("children_tourism", "DU LỊCH TRẺ EM: educational experiences (farm visit, craft workshop, cooking class), age-appropriate activities (3-6, 7-12, 13-17), safety considerations, stroller-friendly routes, kid-friendly restaurants, rainy day alternatives, wildlife encounters, interactive museum/exhibition ideas"),
    ("romance_guide", "DU LỊCH TÌNH YÊU: best proposal spots, honeymoon itineraries, couple photography locations, romantic restaurants, sunset cruise, couples cooking class, matching couple outfit spots (áo bà ba), anniversary trip ideas, budget romantic options"),
    ("accessibility_guide", "DU LỊCH TIẾP CẬN: wheelchair accessibility audit (hotels, attractions, restaurants), elderly-friendly itineraries, hearing/vision impairment accommodations, medical facilities, pharmacy locations, dietary restrictions (halal, vegetarian, allergies), insurance recommendations"),
]


def _run_topics(llm, name, filename, topics, workers=3, max_tok=6000):
    log(f"═══ EXPERT: {name} ═══")
    f = OUTPUT_DIR / filename
    done = {r.get("key") for r in read_jsonl(f)}
    remaining = [(k, p) for k, p in topics if k not in done]
    log(f"  {len(remaining)} {name} topics")
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(_gen, llm, f, k, SYS_EXPERT, p, max_tok) for k, p in remaining]
        for fut in as_completed(futs):
            try: fut.result()
            except Exception as e: log(f"  ERR: {e}")


def sociology(llm, w=3): _run_topics(llm, "SOCIOLOGY", "sociology.jsonl", SOCIO_TOPICS, w)
def linguistics(llm, w=3): _run_topics(llm, "LINGUISTICS", "linguistics.jsonl", LING_TOPICS, w)
def religion(llm, w=3): _run_topics(llm, "RELIGION", "religion.jsonl", RELIG_TOPICS, w)
def agriculture(llm, w=3): _run_topics(llm, "AGRICULTURE", "agriculture.jsonl", AGRI_TOPICS, w)
def tourism_strategy(llm, w=3): _run_topics(llm, "TOURISM STRATEGY", "tourism_strategy.jsonl", TOURISM_STRAT, w)
def photography(llm, w=3): _run_topics(llm, "PHOTOGRAPHY", "photography.jsonl", PHOTO_TOPICS, w)
def wellness(llm, w=3): _run_topics(llm, "WELLNESS", "wellness.jsonl", SPECIAL_TOPICS[:1], w)
def nightlife(llm, w=3): _run_topics(llm, "NIGHTLIFE", "nightlife.jsonl", SPECIAL_TOPICS[1:2], w)
def children(llm, w=3): _run_topics(llm, "CHILDREN", "children.jsonl", SPECIAL_TOPICS[2:3], w)
def romance(llm, w=3): _run_topics(llm, "ROMANCE", "romance.jsonl", SPECIAL_TOPICS[3:4], w)
def accessibility(llm, w=3): _run_topics(llm, "ACCESSIBILITY", "accessibility.jsonl", SPECIAL_TOPICS[4:5], w)


MODES = {
    "anthropology": anthropology,
    "ecology-science": ecology_science,
    "food-science": food_science,
    "architecture": architecture,
    "economics": economics,
    "history-academic": history_academic,
    "geography-deep": geography_deep,
    "music": music,
    "sociology": sociology,
    "linguistics": linguistics,
    "religion": religion,
    "agriculture": agriculture,
    "tourism-strategy": tourism_strategy,
    "photography": photography,
    "wellness": wellness,
    "nightlife": nightlife,
    "children": children,
    "romance": romance,
    "accessibility": accessibility,
}


def main():
    _cfg_io()
    ap = argparse.ArgumentParser(description="Mega Expert — PhD-level research")
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
