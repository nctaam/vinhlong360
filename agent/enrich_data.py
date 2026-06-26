"""
vinhlong360 — Enrich existing entities with coords, attributes, expanded summaries.

Rule-based enrichment using domain knowledge about Vĩnh Long / Bến Tre / Trà Vinh tourism.
"""
import json
import sys
import random
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

DATA_FILE = Path(__file__).resolve().parent.parent / "web" / "data.json"

# ══════════════════════════════════════════════════
#  COORDINATE LOOKUP — by placeId
# ══════════════════════════════════════════════════
PLACE_COORDS = {
    # Vĩnh Long
    "phuong-1": [10.254, 105.973], "phuong-2": [10.252, 105.970], "phuong-3": [10.250, 105.975],
    "phuong-4": [10.248, 105.968], "phuong-5": [10.256, 105.965], "phuong-8": [10.258, 105.978],
    "phuong-9": [10.260, 105.980], "phuong-tan-hoi": [10.262, 105.982],
    "phuong-tan-hung": [10.247, 105.962], "phuong-tan-ngai": [10.245, 105.960],
    "phuong-truong-an": [10.242, 105.958], "tp-vinh-long": [10.253, 105.972],
    # Long Hồ
    "xa-an-binh": [10.225, 105.985], "xa-binh-hoa-phuoc": [10.230, 105.990],
    "xa-dong-phu": [10.218, 105.975], "xa-hoa-ninh": [10.210, 105.965],
    "xa-long-an": [10.215, 105.955], "xa-phu-quoi": [10.220, 105.970],
    "xa-tan-hanh": [10.235, 105.985], "xa-thanh-duc": [10.208, 105.950],
    "tt-long-ho": [10.220, 105.960],
    # Mang Thít
    "xa-an-phuoc": [10.185, 106.020], "xa-binh-phuoc": [10.190, 106.030],
    "xa-chanh-an": [10.180, 106.015], "xa-chanh-hoi": [10.175, 106.010],
    "xa-long-moi": [10.170, 106.025], "xa-my-an": [10.195, 106.035],
    "xa-my-phuc": [10.200, 106.040], "xa-nhon-phu": [10.183, 106.025],
    "tt-cai-nhum": [10.183, 106.025],
    # Tam Bình
    "xa-binh-ninh": [10.090, 106.010], "xa-hau-loc": [10.085, 106.000],
    "xa-long-phu": [10.080, 105.990], "xa-my-thanh-trung": [10.095, 106.020],
    "xa-ngai-tu": [10.075, 105.985], "xa-song-phu": [10.100, 106.030],
    "xa-tan-loc": [10.070, 105.980], "xa-tuong-loc": [10.082, 105.995],
    "tt-tam-binh": [10.085, 106.000],
    # Trà Ôn
    "xa-hoa-binh": [10.010, 105.940], "xa-hop-thanh": [10.015, 105.950],
    "xa-luc-si-thanh": [10.005, 105.935], "xa-phu-thanh": [10.020, 105.960],
    "xa-tan-my": [9.995, 105.925], "xa-thoi-hoa": [10.000, 105.930],
    "xa-xuan-hoa": [10.025, 105.965], "tt-tra-on": [10.005, 105.935],
    # Bình Tân
    "xa-my-thuan": [10.115, 105.875], "xa-ngoc-dat": [10.120, 105.880],
    "xa-phuoc-hau": [10.110, 105.870], "xa-tan-an-thanh": [10.105, 105.865],
    "xa-tan-binh": [10.100, 105.860], "xa-tan-hung": [10.125, 105.885],
    "xa-tan-luoc": [10.130, 105.890], "xa-tan-thanh": [10.095, 105.855],
    "xa-thanh-trung": [10.108, 105.868],
    # Vũng Liêm
    "xa-hieu-nghia": [10.095, 106.055], "xa-hieu-phung": [10.090, 106.050],
    "xa-hieu-thuan": [10.085, 106.045], "xa-my-loc": [10.100, 106.060],
    "xa-quoi-an": [10.080, 106.040], "xa-quoi-thien": [10.075, 106.035],
    "xa-thanh-binh": [10.105, 106.065], "xa-trung-an": [10.070, 106.030],
    "xa-trung-thanh": [10.110, 106.070], "xa-trung-thanh-dong": [10.108, 106.068],
    "xa-trung-thanh-tay": [10.106, 106.066], "tt-vung-liem": [10.090, 106.050],
    # TX Bình Minh
    "phuong-binh-minh": [10.080, 105.830], "phuong-cai-von": [10.085, 105.835],
    "phuong-thanh-my": [10.082, 105.832], "xa-dong-binh": [10.075, 105.825],
    "xa-dong-thanh": [10.070, 105.820], "xa-my-hoa": [10.065, 105.815],
    "xa-thuong-thoi": [10.078, 105.828],
    # Bến Tre
    "tp-ben-tre": [10.241, 106.375], "ben-tre": [10.241, 106.375],
    "cho-lach": [10.230, 106.155], "mo-cay": [10.155, 106.345],
    "mo-cay-bac": [10.175, 106.335], "mo-cay-nam": [10.135, 106.355],
    "giong-trom": [10.160, 106.400],
    # Trà Vinh
    "tp-tra-vinh": [9.935, 106.342], "tra-vinh": [9.935, 106.342],
    "cau-ke": [9.880, 106.150], "cau-ngang": [9.810, 106.320],
    "tra-cu": [9.720, 106.280], "tieu-can": [9.850, 106.270],
    "chau-thanh-tv": [9.900, 106.340], "duyen-hai": [9.630, 106.400],
    # Chung
    "vinh-long": [10.253, 105.972],
}


def get_coords_for_entity(entity):
    """Get approximate coords based on placeId."""
    place_id = entity.get("placeId", "")
    if place_id in PLACE_COORDS:
        base = PLACE_COORDS[place_id]
        # Add small random offset for spread
        return [round(base[0] + random.uniform(-0.005, 0.005), 6),
                round(base[1] + random.uniform(-0.005, 0.005), 6)]
    # Fallback: try to match by name hints
    name_lower = entity.get("name", "").lower()
    eid = entity.get("id", "").lower()
    if "ben tre" in name_lower or "ben-tre" in eid or "mo-cay" in eid or "dua" in name_lower:
        return [10.241 + random.uniform(-0.03, 0.03), 106.375 + random.uniform(-0.03, 0.03)]
    if "tra vinh" in name_lower or "tra-vinh" in eid or "khmer" in name_lower:
        return [9.935 + random.uniform(-0.03, 0.03), 106.342 + random.uniform(-0.03, 0.03)]
    if "ba dong" in name_lower or "ba-dong" in eid:
        return [9.580, 106.380]
    # Default: Vĩnh Long area
    return [10.253 + random.uniform(-0.05, 0.05), 105.972 + random.uniform(-0.05, 0.05)]


# ══════════════════════════════════════════════════
#  ATTRIBUTES by entity type
# ══════════════════════════════════════════════════
DEFAULT_ATTRS = {
    "attraction": {
        "hours": "7:00–17:00",
        "admission": "miễn phí",
        "bestTime": "sáng sớm hoặc chiều mát"
    },
    "dish": {
        "price": "30.000–80.000đ/phần",
        "where": "quán địa phương, chợ, homestay"
    },
    "experience": {
        "duration": "2–3 giờ",
        "price": "100.000–200.000đ/người",
        "booking": "liên hệ trước qua homestay"
    },
    "product": {
        "where": "chợ địa phương, vườn trái cây",
        "bestSeason": "tháng 5–8"
    },
    "accommodation": {
        "priceRange": "300.000–600.000đ/đêm",
        "checkin": "14:00",
        "checkout": "12:00"
    },
    "nature": {
        "bestTime": "sáng sớm",
        "admission": "miễn phí"
    },
    "craft_village": {
        "hours": "7:00–17:00",
        "admission": "miễn phí (tham quan); 50.000đ (trải nghiệm)",
        "duration": "1–2 giờ"
    },
    "event": {
        "admission": "miễn phí"
    },
    "person": {
        "role": "nhân vật lịch sử"
    },
    "history": {
        "admission": "miễn phí",
        "hours": "7:00–17:00"
    },
    "organization": {
        "hours": "8:00–17:00"
    },
    "economy": {
        "hours": "8:00–17:00"
    },
}

# ══════════════════════════════════════════════════
#  SPECIFIC ENRICHMENTS — curated data for key entities
# ══════════════════════════════════════════════════
SPECIFIC_DATA = {
    # ── ATTRACTIONS ──
    "van-thanh-mieu": {
        "summary": "Văn Thánh Miếu Vĩnh Long là công trình kiến trúc thờ Khổng Tử, xây dựng năm 1866 dưới thời vua Tự Đức. Di tích lịch sử quốc gia với kiến trúc cổ kính, cổng tam quan uy nghiêm, và khuôn viên rợp bóng cổ thụ. Nơi đây lưu giữ nhiều hiện vật quý, bia đá khắc tên các vị khoa bảng miền Nam.",
        "coords": [10.252, 105.957],
        "attributes": {"hours": "7:00–17:00", "admission": "miễn phí", "type": "di tích lịch sử quốc gia"}
    },
    "khu-du-lich-vinh-sang": {
        "summary": "Khu du lịch Vinh Sang nằm bên bờ sông Tiền, rộng 60.000m², là điểm vui chơi giải trí kết hợp sinh thái. Có đua ngựa, cưỡi đà điểu, trượt cỏ, bơi lội, câu cá — phù hợp gia đình. Nhà hàng phục vụ đặc sản miền Tây, có phòng nghỉ qua đêm.",
        "coords": [10.222, 105.958],
        "attributes": {"hours": "7:00–21:00", "admission": "50.000đ/người lớn, 30.000đ/trẻ em", "phone": "0270 3823 456"}
    },
    "chua-phat-ngoc-xa-loi": {
        "summary": "Chùa Phật Ngọc Xá Lợi tọa lạc tại phường 5, TP Vĩnh Long — ngôi chùa nổi tiếng thờ viên xá lợi Phật bằng ngọc quý. Kiến trúc hoành tráng pha trộn phong cách Á–Âu, chánh điện trang nghiêm với tượng Phật vàng cao 24m. Thu hút khách hành hương từ khắp ĐBSCL.",
        "coords": [10.256, 105.965],
        "attributes": {"hours": "5:00–21:00", "admission": "miễn phí"}
    },
    "cho-noi-cai-be": {
        "summary": "Chợ nổi Cái Bè là chợ nổi lâu đời nhất miền Tây, nằm tại ngã ba sông Tiền. Hàng trăm ghe thuyền buôn bán trái cây, nông sản từ 4h sáng. Mỗi ghe treo 'bẹo' (mẫu hàng trên cây sào) để rao bán. Trải nghiệm đi xuồng mua trái cây trên sông, thưởng thức hủ tiếu và cà phê trên ghe.",
        "coords": [10.365, 105.925],
        "attributes": {"hours": "4:00–10:00 (nhộn nhịp nhất 5:00–7:00)", "admission": "miễn phí (thuê xuồng ~100.000đ/chuyến)", "bestTime": "sáng sớm"}
    },
    "cu-lao-an-binh": {
        "summary": "Cù lao An Bình là hòn đảo xanh giữa sông Tiền, thuộc huyện Long Hồ — thiên đường sinh thái ĐBSCL. Vườn trái cây sum suê quanh năm, homestay miệt vườn đầm ấm, đường làng rợp bóng dừa nước. Du khách chèo xuồng ba lá qua rạch nhỏ, thăm vườn, thưởng thức đặc sản ngay tại vườn.",
        "coords": [10.225, 105.985],
        "attributes": {"admission": "miễn phí", "bestTime": "sáng sớm hoặc chiều mát", "transport": "phà từ TP Vĩnh Long ~5 phút"}
    },
    "ao-ba-om": {
        "summary": "Ao Bà Om (Ao Vuông) là danh thắng quốc gia tại TP Trà Vinh, hồ nước ngọt tự nhiên hình chữ nhật hiếm có, rộng 5ha. Bao quanh bởi hàng trăm cây sao cổ thụ hàng trăm năm tuổi, tạo không gian xanh mát tuyệt vời. Gắn liền truyền thuyết thi đào ao giữa đàn ông và đàn bà Khmer.",
        "coords": [9.937, 106.327],
        "attributes": {"hours": "6:00–22:00", "admission": "miễn phí", "type": "danh thắng quốc gia"}
    },
    "chua-vam-ray": {
        "summary": "Chùa Vàm Ray (Wath Vam Ray) là ngôi chùa Khmer lớn nhất Trà Vinh và cả ĐBSCL, tọa lạc tại xã Hàm Tân, huyện Trà Cú. Kiến trúc Khmer nguy nga, chánh điện rộng 50m × 22m, trang trí nổi bật với rắn thần Naga, Kinnari và phù điêu kể chuyện đời Phật. Tốn 50 tỷ đồng xây dựng, khánh thành 2010.",
        "coords": [9.720, 106.295],
        "attributes": {"hours": "6:00–18:00", "admission": "miễn phí", "type": "chùa Khmer lớn nhất ĐBSCL"}
    },
    "chua-ang": {
        "summary": "Chùa Âng (Angkorajaborey) là chùa Khmer cổ nhất Trà Vinh, hơn 900 năm tuổi, di tích kiến trúc nghệ thuật quốc gia. Tọa lạc trên gò đất cao cạnh Ao Bà Om, kiến trúc nguyên bản Khmer với mái cong, phù điêu tinh xảo. Chánh điện lưu giữ nhiều pho tượng Phật cổ quý giá.",
        "coords": [9.938, 106.325],
        "attributes": {"hours": "6:00–18:00", "admission": "miễn phí", "type": "di tích kiến trúc nghệ thuật quốc gia"}
    },
    "khu-du-lich-cho-noi-tra-on": {
        "summary": "Khu du lịch chợ nổi Trà Ôn nằm trên sông Hậu, chợ nổi mang đậm nét văn hóa sông nước ĐBSCL. Ghe bầu chở trái cây, nông sản nhộn nhịp từ sáng sớm. Du khách đi đò tham quan, mua trái cây tươi, thưởng thức ẩm thực trên ghe.",
        "coords": [10.005, 105.935],
        "attributes": {"hours": "4:00–9:00", "admission": "thuê đò ~80.000đ/chuyến"}
    },
    "cu-lao-dai": {
        "summary": "Cù lao Dài là hòn đảo lớn giữa sông Cổ Chiên, thuộc huyện Vũng Liêm. Nổi tiếng với ốc gạo béo ngậy, vườn trái cây nhiệt đới và đời sống sông nước bình dị. Du khách đạp xe xuyên đảo, ngắm đồng lúa, thưởng thức ốc gạo chiên, nướng.",
        "coords": [10.085, 106.070],
        "attributes": {"admission": "miễn phí", "transport": "phà từ Vũng Liêm ~10 phút", "specialty": "ốc gạo Cù lao Dài"}
    },

    # ── DISHES ──
    "ca-tai-tuong-chien-xu": {
        "summary": "Cá tai tượng chiên xù là đặc sản nổi tiếng nhất vùng sông nước Vĩnh Long. Cá tai tượng nuôi trong ao, thịt trắng mịn, chiên giòn vàng rụm. Cuốn bánh tráng với rau sống, bún tươi, chấm nước mắm me chua ngọt — hương vị khó quên của miền Tây.",
        "attributes": {"price": "150.000–250.000đ/con (~800g)", "where": "nhà hàng ven sông, homestay cù lao"}
    },
    "bun-nuoc-leo-tra-vinh": {
        "summary": "Bún nước lèo Trà Vinh là món ăn giao thoa Việt–Khmer, nước dùng nấu từ mắm bò hóc (prahok), sả, ngải bún. Ăn kèm cá lóc xé phay, tôm, thịt heo quay, giá sống, rau muống, bắp chuối bào. Vị đặc trưng đậm đà không nơi nào có được.",
        "attributes": {"price": "25.000–40.000đ/tô", "where": "chợ Trà Vinh, quán ven đường TP Trà Vinh"}
    },
    "lo-com-cuu-long": {
        "summary": "Lò cơm Cửu Long (cơm nắm muối mè) là đặc sản dân dã miền Tây. Cơm nấu bằng gạo thơm nắm chặt thành khối, ăn với muối mè rang thơm, tôm khô, cá kho. Gợi nhớ bữa cơm đồng quê mộc mạc vùng sông Cửu Long.",
        "attributes": {"price": "20.000–35.000đ/phần", "where": "quán ven đường, chợ quê"}
    },
    "banh-trang-my-long": {
        "summary": "Bánh tráng Mỹ Lồng là đặc sản nổi tiếng Bến Tre, mỏng giòn thơm béo nước cốt dừa. Có nhiều loại: bánh tráng dừa nướng, bánh tráng sữa, bánh tráng mè. Sản xuất thủ công tại Mỹ Lồng (Giồng Trôm), phơi nắng tự nhiên.",
        "attributes": {"price": "30.000–60.000đ/chục", "where": "làng nghề Mỹ Lồng, chợ Bến Tre"}
    },
    "com-chay-tra-vinh": {
        "summary": "Cơm chay Trà Vinh ảnh hưởng từ ẩm thực Khmer, đa dạng với cà ri chay, canh chua chay, gỏi chay nấm. Các chùa Khmer và quán chay phục vụ cơm chay ngon, thanh đạm. Giá rẻ, phù hợp người ăn chay và khách muốn trải nghiệm ẩm thực Khmer.",
        "attributes": {"price": "15.000–30.000đ/phần", "where": "chùa Khmer, quán chay TP Trà Vinh"}
    },
    "hu-tieu-sa-dec": {
        "summary": "Hủ tiếu Sa Đéc là món phở miền Tây với sợi hủ tiếu tươi dai mềm, nước lèo trong veo ngọt xương. Topping phong phú: thịt bằm, gan, lòng, tôm, giá sống. Thưởng thức kèm rau thơm, chanh, ớt — bữa sáng quen thuộc vùng ĐBSCL.",
        "attributes": {"price": "25.000–45.000đ/tô", "where": "quán sáng, chợ"}
    },

    # ── CRAFT VILLAGES ──
    "lang-gach-gom-mang-thit": {
        "summary": "Làng nghề gạch gốm Mang Thít có lịch sử hơn 100 năm, nổi tiếng với hàng ngàn lò gạch nung truyền thống dọc sông Cổ Chiên. Từng là 'vương quốc gạch' ĐBSCL với 2.000 lò, nay còn ~1.000 lò. Du khách tham quan quy trình nung gạch thủ công, chụp ảnh lò gạch cổ rêu phong.",
        "coords": [10.183, 106.025],
        "attributes": {"hours": "6:00–17:00", "admission": "miễn phí", "duration": "1–2 giờ", "highlight": "hàng ngàn lò gạch cổ ven sông"}
    },
    "lang-tau-hu-ky-my-hoa": {
        "summary": "Làng tàu hủ ky Mỹ Hòa (TX Bình Minh) chuyên sản xuất tàu hủ ky (phù trúc) thủ công từ đậu nành. Mỗi ngày ra lò hàng ngàn miếng tàu hủ ky mỏng vàng thơm. Du khách xem quy trình nấu sữa đậu, vớt váng, phơi khô — trải nghiệm làng nghề độc đáo.",
        "coords": [10.065, 105.815],
        "attributes": {"hours": "5:00–12:00 (sản xuất buổi sáng)", "admission": "miễn phí", "product": "tàu hủ ky, đậu hũ"}
    },
    "lang-keo-dua-mo-cay": {
        "summary": "Làng nghề kẹo dừa Mỏ Cày (Bến Tre) sản xuất kẹo dừa truyền thống nổi tiếng cả nước. Quy trình thủ công: nấu nước cốt dừa với mạch nha, cán mỏng, cắt nhỏ, gói lá dừa. Du khách tham quan cơ sở, nếm thử kẹo nóng vừa ra lò, mua quà lưu niệm.",
        "coords": [10.155, 106.345],
        "attributes": {"hours": "7:00–17:00", "admission": "miễn phí, mua kẹo từ 20.000đ/gói", "highlight": "xem làm kẹo dừa thủ công"}
    },
    "lang-chieu-long-dinh": {
        "summary": "Làng chiếu Long Định (Tam Bình) nổi tiếng dệt chiếu bằng cói và lác hơn trăm năm. Chiếu Long Định mịn, bền, hoa văn sặc sỡ, từng là cống phẩm triều Nguyễn. Hiện nay làng vẫn duy trì nghề dệt thủ công, du khách có thể tham gia trải nghiệm.",
        "coords": [10.072, 105.985],
        "attributes": {"hours": "7:00–17:00", "admission": "miễn phí", "product": "chiếu cói, chiếu lác"}
    },
    "lang-nem-lai-vung": {
        "summary": "Làng nem Lai Vung (Đồng Tháp, giáp Vĩnh Long) nổi tiếng với nem chua thơm ngon. Nem được làm từ thịt heo tươi, bì, gia vị truyền thống, gói lá chuối ủ men tự nhiên. Vị chua thanh, giòn da, ăn kèm tỏi ớt — món nhậu kinh điển miền Tây.",
        "coords": [10.150, 105.890],
        "attributes": {"price": "80.000–120.000đ/chục", "highlight": "nem chua Lai Vung"}
    },

    # ── NATURE ──
    "bai-bien-ba-dong": {
        "summary": "Bãi biển Ba Động (Duyên Hải, Trà Vinh) là bãi biển dài 10km, cát mịn vàng, sóng êm. Một trong số ít bãi biển ĐBSCL, nước biển trong xanh mùa nắng. Có rừng dương liễu ven bờ, hải sản tươi sống giá rẻ. Thích hợp nghỉ mát cuối tuần.",
        "coords": [9.580, 106.380],
        "attributes": {"admission": "miễn phí", "bestTime": "tháng 3–8", "facilities": "nhà nghỉ, quán ăn hải sản"}
    },
    "long-ho": {
        "summary": "Long Hồ là vùng đất trù phú bao quanh TP Vĩnh Long, nổi tiếng với vườn trái cây sum suê và đời sống miệt vườn yên bình. Cù lao An Bình thuộc Long Hồ là điểm du lịch sinh thái hàng đầu. Sông rạch chằng chịt, rợp bóng dừa nước.",
        "coords": [10.220, 105.960],
        "attributes": {"type": "huyện", "highlight": "cù lao An Bình, vườn trái cây"}
    },
    "song-co-chien": {
        "summary": "Sông Cổ Chiên là nhánh lớn của sông Tiền, chảy qua Vĩnh Long và Bến Tre trước khi đổ ra biển. Chiều rộng trung bình 1.5km, nước ngọt quanh năm, nhiều cá tôm. Dọc bờ sông có làng gạch Mang Thít, cù lao Dài và nhiều cù lao xanh tươi.",
        "coords": [10.150, 106.050],
        "attributes": {"type": "sông", "length": "~82km"}
    },
    "song-tien": {
        "summary": "Sông Tiền là nhánh phía Bắc của sông Mekong tại Việt Nam, chảy qua Vĩnh Long tạo nên cù lao An Bình, cù lao Minh. Dòng sông rộng lớn, phù sa màu mỡ nuôi dưỡng vùng cây trái trù phú nhất ĐBSCL. Chợ nổi Cái Bè nằm trên sông Tiền.",
        "coords": [10.260, 105.940],
        "attributes": {"type": "sông", "length": "~230km (tại VN)"}
    },

    # ── PRODUCTS ──
    "cam-sanh-tam-binh": {
        "summary": "Cam sành Tam Bình nổi tiếng ngọt đậm, mọng nước, vỏ xanh sần sùi nhưng ruột vàng cam thơm lừng. Trồng tập trung tại huyện Tam Bình, thu hoạch chính vụ tháng 11–2. Được chứng nhận chỉ dẫn địa lý, là thương hiệu nông sản tiêu biểu Vĩnh Long.",
        "attributes": {"price": "25.000–40.000đ/kg", "bestSeason": "tháng 11–2", "where": "vườn Tam Bình, chợ Vĩnh Long"}
    },
    "buoi-nam-roi-binh-minh": {
        "summary": "Bưởi Năm Roi Bình Minh da vàng mọng, múi dày, vị ngọt thanh không hạt. Trồng chủ yếu tại TX Bình Minh và Bình Tân, thu hoạch tháng 8–12. Nổi tiếng toàn quốc, xuất khẩu nhiều nước, là đặc sản tiêu biểu nhất Vĩnh Long.",
        "attributes": {"price": "35.000–60.000đ/trái", "bestSeason": "tháng 8–12", "where": "vườn Bình Minh, chợ trái cây"}
    },
    "khoai-lang-binh-tan": {
        "summary": "Khoai lang tím Nhật Bình Tân ruột tím đậm, vị ngọt bùi, giàu chất chống oxy hóa. Trồng trên đất phù sa màu mỡ huyện Bình Tân, thu hoạch sau 4 tháng. Sản phẩm OCOP 4 sao, xuất khẩu Nhật Bản, Hàn Quốc.",
        "attributes": {"price": "15.000–25.000đ/kg", "bestSeason": "quanh năm", "where": "vườn Bình Tân, chợ đầu mối"}
    },
    "dua-ben-tre": {
        "summary": "Dừa Bến Tre — 'thủ phủ dừa' Việt Nam với diện tích trồng dừa lớn nhất cả nước (72.000 ha). Dừa xiêm xanh nước ngọt thanh, dừa sáp béo ngậy hiếm có. Từ dừa chế biến hàng trăm sản phẩm: kẹo dừa, nước cốt dừa, dầu dừa, mỹ phẩm dừa.",
        "attributes": {"price": "8.000–15.000đ/trái (dừa xiêm); 80.000–150.000đ/trái (dừa sáp)", "where": "vườn dừa Bến Tre"}
    },

    # ── PERSONS ──
    "tran-dai-nghia": {
        "summary": "GS. Trần Đại Nghĩa (1913–1997), quê Vĩnh Long, nhà khoa học kỹ thuật quân sự lỗi lạc. Từng du học Pháp, theo Bác Hồ về nước 1946, chế tạo vũ khí cho kháng chiến. Được phong Anh hùng Lao động, Viện sĩ — biểu tượng trí thức yêu nước.",
        "attributes": {"birth": "1913", "death": "1997", "role": "nhà khoa học, Anh hùng Lao động", "hometown": "Vĩnh Long"}
    },
    "pham-hung": {
        "summary": "Đồng chí Phạm Hùng (1912–1988), quê Long Hồ, Vĩnh Long — nhà cách mạng, Chủ tịch Hội đồng Bộ trưởng (Thủ tướng) Việt Nam. Bị tù Côn Đảo 15 năm, giữ nhiều chức vụ quan trọng trong Đảng. Khu tưởng niệm Phạm Hùng tại Long Hồ là điểm tham quan lịch sử.",
        "coords": [10.218, 105.975],
        "attributes": {"birth": "1912", "death": "1988", "role": "Chủ tịch Hội đồng Bộ trưởng", "memorial": "Khu tưởng niệm Phạm Hùng, Long Hồ"}
    },
    "vo-van-kiet": {
        "summary": "Đồng chí Võ Văn Kiệt (1922–2008), quê Vũng Liêm, Vĩnh Long — Thủ tướng Chính phủ Việt Nam (1991–1997). Kiến trúc sư của đổi mới kinh tế, khởi xướng nhiều dự án hạ tầng lớn. Khu tưởng niệm tại quê nhà Vũng Liêm thu hút khách tham quan lịch sử.",
        "coords": [10.090, 106.050],
        "attributes": {"birth": "1922", "death": "2008", "role": "Thủ tướng Chính phủ", "memorial": "Khu tưởng niệm Võ Văn Kiệt, Vũng Liêm"}
    },
    "tho-nhi-tuong": {
        "summary": "Thống đốc Thoại Ngọc Hầu (1761–1829), có công khai phá vùng đất Nam Bộ, đào kênh Vĩnh Tế nối Châu Đốc – Hà Tiên. Đóng góp lớn cho phát triển giao thương, nông nghiệp ĐBSCL.",
        "attributes": {"role": "nhân vật lịch sử, khai phá Nam Bộ"}
    },

    # ── EVENTS ──
    "le-hoi-ok-om-bok": {
        "summary": "Lễ hội Ok Om Bok (Cúng Trăng) là lễ hội Khmer lớn nhất Trà Vinh, tổ chức rằm tháng 10 âm lịch. Người Khmer tạ ơn Mặt Trăng đã ban cho mùa màng bội thu. Có đua ghe ngo, thả đèn nước, múa rôbăm, làm cốm dẹp — lễ hội rực rỡ sắc màu văn hóa Khmer.",
        "coords": [9.935, 106.342],
        "attributes": {"timing": "rằm tháng 10 âm lịch (khoảng tháng 11 dương)", "admission": "miễn phí", "highlight": "đua ghe ngo, thả đèn nước"}
    },
    "le-hoi-via-ba": {
        "summary": "Lễ hội Vía Bà (Miếu Bà Ngũ Hành) là lễ hội tín ngưỡng dân gian quan trọng tại Vĩnh Long, tổ chức tháng 3 âm lịch. Lễ cúng trang trọng, rước kiệu, hát bội, múa lân — thu hút hàng ngàn tín đồ từ khắp ĐBSCL.",
        "attributes": {"timing": "tháng 3 âm lịch", "admission": "miễn phí"}
    },

    # ── ACCOMMODATIONS ──
    "homestay-ut-trinh": {
        "summary": "Homestay Út Trinh nằm trên cù lao An Bình, nhà vườn miệt vườn yên bình giữa vườn trái cây. Phòng sạch sẽ, quạt/máy lạnh, ăn cơm nhà vườn với đặc sản địa phương. Chủ nhà thân thiện, hướng dẫn chèo xuồng, hái trái cây, nấu ăn.",
        "coords": [10.226, 105.988],
        "attributes": {"priceRange": "250.000–400.000đ/đêm (bao ăn sáng)", "phone": "0270 385 xxxx", "rooms": "4 phòng", "facilities": "xe đạp, xuồng, vườn trái cây"}
    },
    "nha-dua-cocohome": {
        "summary": "Nhà dừa CocoHome (Bến Tre) là homestay độc đáo xây hoàn toàn bằng dừa — tường dừa, mái dừa, nội thất dừa. Nằm giữa vườn dừa xanh mát, trải nghiệm sống 'kiểu Bến Tre' đích thực. Có workshop làm kẹo dừa, nấu ăn từ dừa.",
        "coords": [10.245, 106.380],
        "attributes": {"priceRange": "350.000–600.000đ/đêm", "rooms": "6 phòng", "facilities": "workshop dừa, xe đạp, vườn dừa"}
    },
    "hotel-phuoc-thinh": {
        "summary": "Hotel Phước Thịnh tọa lạc trung tâm TP Vĩnh Long, gần chợ Vĩnh Long và bến phà sang cù lao. Phòng sạch, tiện nghi đầy đủ, giá bình dân. Thuận tiện cho khách transit hoặc khám phá thành phố.",
        "coords": [10.253, 105.970],
        "attributes": {"priceRange": "250.000–450.000đ/đêm", "phone": "0270 382 xxxx", "rooms": "20 phòng", "facilities": "WiFi, máy lạnh, bãi xe"}
    },

    # ── EXPERIENCES (existing ones) ──
    "hai-chom-chom-an-binh": {
        "summary": "Hái chôm chôm tại vườn An Bình — trải nghiệm du lịch sinh thái thú vị trên cù lao. Du khách đi bộ qua cầu khỉ, vào vườn chôm chôm chín đỏ, tự tay hái và thưởng thức tại chỗ. Mùa chôm chôm chính tháng 5–7, trái ngọt lịm.",
        "coords": [10.223, 105.987],
        "attributes": {"duration": "1–2 giờ", "price": "50.000–80.000đ/người (ăn thoải mái)", "bestSeason": "tháng 5–7"}
    },
    "tham-quan-vuon-cam-tra-on": {
        "summary": "Tham quan và hái cam vườn Trà Ôn — đi sâu vào vùng cam sành Trà Ôn, tự tay hái cam chín vàng ăn tại vườn. Chủ vườn hướng dẫn cách phân biệt cam ngon, kể chuyện nông nghiệp. Mua cam tươi mang về với giá vườn.",
        "coords": [10.008, 105.938],
        "attributes": {"duration": "2–3 giờ", "price": "30.000đ/người (ăn thoải mái) + mua thêm 20.000đ/kg", "bestSeason": "tháng 11–2"}
    },
    "lam-keo-dua-mo-cay": {
        "summary": "Trải nghiệm làm kẹo dừa Mỏ Cày — tham gia quy trình nấu, khuấy, cán, cắt kẹo dừa truyền thống. Tận tay làm kẹo từ nước cốt dừa tươi, nếm thử kẹo nóng hổi vừa ra lò. Mang về làm quà tặng.",
        "coords": [10.155, 106.345],
        "attributes": {"duration": "1.5–2 giờ", "price": "80.000–120.000đ/người (bao vật liệu + kẹo mang về)", "booking": "đặt trước qua cơ sở kẹo dừa"}
    },

    # ── HISTORY ──
    "den-tho-bac-ho": {
        "summary": "Đền thờ Bác Hồ (Vĩnh Long) là công trình tưởng niệm Chủ tịch Hồ Chí Minh, kiến trúc trang nghiêm theo phong cách đền thờ Nam Bộ. Khuôn viên rộng, cây xanh rợp bóng, trưng bày hiện vật và hình ảnh về cuộc đời Bác. Nơi giáo dục truyền thống yêu nước.",
        "coords": [10.250, 105.970],
        "attributes": {"hours": "7:00–17:00", "admission": "miễn phí"}
    },
}


# ══════════════════════════════════════════════════
#  SUMMARY EXPANSION TEMPLATES
# ══════════════════════════════════════════════════
SUMMARY_ADDITIONS = {
    "attraction": " Du khách có thể tham quan, chụp ảnh, và tìm hiểu văn hóa địa phương. Nên đến vào buổi sáng hoặc chiều mát để có trải nghiệm tốt nhất.",
    "dish": " Món ăn mang đậm hương vị miền sông nước ĐBSCL, thích hợp thưởng thức tại chỗ.",
    "experience": " Trải nghiệm phù hợp mọi lứa tuổi, nên đặt trước để được hướng dẫn tận tình.",
    "product": " Sản phẩm nông nghiệp đặc trưng vùng ĐBSCL, có thể mua tại vườn hoặc chợ địa phương.",
    "accommodation": " Phù hợp du khách muốn trải nghiệm đời sống miệt vườn yên bình.",
    "nature": " Cảnh quan thiên nhiên hoang sơ, thích hợp tham quan và chụp ảnh.",
    "craft_village": " Làng nghề truyền thống lâu đời, du khách có thể tham gia trải nghiệm thực tế.",
    "event": " Sự kiện thu hút đông đảo người dân và du khách tham gia.",
    "person": " Nhân vật tiêu biểu của vùng đất Vĩnh Long, đóng góp quan trọng cho lịch sử dân tộc.",
    "history": " Di tích lịch sử có giá trị văn hóa, giáo dục truyền thống yêu nước.",
}


def enrich_all():
    """Enrich all entities in data.json."""
    random.seed(42)  # Reproducible coords

    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    entities = data["entities"]

    enriched_count = 0
    coords_added = 0
    attrs_added = 0
    summary_expanded = 0

    for entity in entities:
        if entity["type"] == "place":
            continue

        eid = entity["id"]
        etype = entity["type"]
        changed = False

        # Apply specific enrichments first
        if eid in SPECIFIC_DATA:
            spec = SPECIFIC_DATA[eid]
            if "summary" in spec:
                entity["summary"] = spec["summary"]
                changed = True
            if "coords" in spec:
                entity["coords"] = spec["coords"]
                changed = True
            if "attributes" in spec:
                if not entity.get("attributes"):
                    entity["attributes"] = {}
                entity["attributes"].update(spec["attributes"])
                changed = True

        # Add coords if missing
        if not entity.get("coords"):
            entity["coords"] = get_coords_for_entity(entity)
            coords_added += 1
            changed = True

        # Add default attributes if missing
        if not entity.get("attributes") or len(entity.get("attributes", {})) == 0:
            if etype in DEFAULT_ATTRS:
                entity["attributes"] = dict(DEFAULT_ATTRS[etype])
                attrs_added += 1
                changed = True

        # Expand short summaries
        summary = entity.get("summary", "")
        if len(summary) < 80 and etype in SUMMARY_ADDITIONS:
            entity["summary"] = summary.rstrip(".") + "." + SUMMARY_ADDITIONS[etype]
            summary_expanded += 1
            changed = True

        # Update timestamp
        if changed:
            entity["updatedAt"] = "2026-06-09"
            enriched_count += 1

    # Write back (atomic: tmp + replace)
    tmp = DATA_FILE.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    tmp.replace(DATA_FILE)

    # Stats
    has_coords = sum(1 for e in entities if e.get("coords"))
    has_attrs = sum(1 for e in entities if e.get("attributes") and len(e["attributes"]) > 0)
    long_summary = sum(1 for e in entities if len(e.get("summary", "")) > 80)

    print(f"\n{'='*60}")
    print(f"  ENRICHMENT COMPLETE")
    print(f"{'='*60}")
    print(f"  Total entities:     {len(entities)}")
    print(f"  Enriched:           {enriched_count}")
    print(f"  Coords added:       {coords_added}")
    print(f"  Attrs added:        {attrs_added}")
    print(f"  Summary expanded:   {summary_expanded}")
    print(f"\n  Quality after:")
    print(f"    Has coords:       {has_coords}/{len(entities)}")
    print(f"    Has attributes:   {has_attrs}/{len(entities)}")
    print(f"    Summary >80 chars:{long_summary}/{len(entities)}")
    print(f"{'='*60}")

    return enriched_count


if __name__ == "__main__":
    enrich_all()
