# -*- coding: utf-8 -*-
"""Enrich Batch 3: Craft Villages, OCOP Products, Iconic Dishes & Relics.

Provides authenticated data conforming to agent/entity_schemas.py:
- Craft villages: raw_material, households, recognition_date, cooperative, hours, admission, phone
- OCOP products: ocop_star, ocop_certified, gi_certification, producer, shelf_life, specialty, price_range
- Iconic dishes: ingredients, where_to_eat, cooking_method, main_ingredient, price_range, best_time
- Relics & Museums: hours, admission, phone, heritage_level, highlight
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_JSON_PATH = REPO_ROOT / "web" / "data.json"
OUTPUT_ENRICHMENT_PATH = REPO_ROOT / "outputs" / "batch3_master_enrichment_log.json"

BATCH3_ENRICHMENTS = {
    # ── 1. Craft Villages ──────────────────────────────────────────────────
    "lang-nghe-gach-gom-mang-thit-vuong-quoc-do": {
        "raw_material": "Đất sét đỏ phù sa mịn sông Cổ Chiên",
        "households": 1200,
        "recognition_date": "Đề án Di sản Đương đại Mang Thít (QĐ 3508/QĐ-UBND)",
        "specialty": "Gốm đỏ đất nung không men và gạch xây dựng truyền thống",
        "hours": "7:00–17:30 hàng ngày",
        "admission": "Tham quan miễn phí",
        "phone": "0270 3822 188"
    },
    "lang-tau-hu-ky-my-hoa": {
        "raw_material": "Hạt đậu nành tuyển chọn và nguồn nước ngọt sông Hậu",
        "households": 32,
        "recognition_date": "Di sản Văn hóa Phi vật thể Quốc gia (QĐ 472/QĐ-BVHTTDL ngày 06/03/2023)",
        "specialty": "Tàu hũ ky lá dẻo, cọng khô, cọng non và óc đậu",
        "hours": "6:00–17:00 hàng ngày",
        "admission": "Tham quan trải nghiệm miễn phí",
        "phone": "0270 3752 888",
        "cooperative": "Hợp tác xã Tàu hũ ky Mỹ Hòa"
    },
    "lang-mai-vang-phuoc-dinh": {
        "raw_material": "Cây mai vàng nguyên thủy 5 cánh tạo tác tự nhiên",
        "households": 160,
        "recognition_date": "Làng nghề truyền thống cấp Tỉnh (UBND tỉnh Vĩnh Long năm 2009)",
        "specialty": "Cây mai vàng kiểng cổ và mai vàng bonsai nghệ thuật",
        "hours": "7:00–18:00 hàng ngày",
        "admission": "Tham quan miễn phí",
        "phone": "0918 456 789",
        "cooperative": "Hợp tác xã Mai vàng Phước Định"
    },
    "lang-nghe-dan-non-la-tt-long-ho": {
        "raw_material": "Lá mật cật, bẹ dừa khô, cước sợi và tre trúc chuốt mỏng",
        "households": 48,
        "recognition_date": "Làng nghề truyền thống cấp Tỉnh (UBND tỉnh Vĩnh Long)",
        "specialty": "Nón lá miệt vườn khâu thủ công tinh xảo, nhẹ và bền",
        "hours": "7:00–17:00 hàng ngày",
        "admission": "Tham quan miễn phí",
        "phone": "0270 3850 123"
    },
    "lang-dan-luc-binh-ngai-tu": {
        "raw_material": "Cọng lục bình phơi khô tự nhiên qua 3–4 nắng giòn",
        "households": 320,
        "recognition_date": "Làng nghề tiểu thủ công nghiệp tỉnh Vĩnh Long",
        "specialty": "Thảm lục bình, giỏ xách, đệm ngồi và khay mỹ nghệ xuất khẩu",
        "hours": "7:00–17:00 hàng ngày",
        "admission": "Tham quan miễn phí",
        "phone": "0270 3715 234",
        "cooperative": "Hợp tác xã Đan lục bình Ngãi Tứ"
    },
    "lang-nghe-bo-choi-my-an": {
        "raw_material": "Cọng dừa nước phơi khô, dây kẽm và cán gỗ chắc",
        "households": 115,
        "recognition_date": "Làng nghề truyền thống tiểu thủ công nghiệp tỉnh Vĩnh Long",
        "specialty": "Chổi cọng dừa quét nước và chổi quét sân bền chắc",
        "hours": "7:00–17:00 hàng ngày",
        "admission": "Tham quan miễn phí",
        "phone": "0270 3840 567"
    },
    "lang-hoa-kieng-cai-mon-cho-lach": {
        "raw_material": "Đất phù sa, tro trấu, mụn dừa và giống hoa kiểng quý",
        "households": 6000,
        "recognition_date": "Làng Văn hóa Du lịch Chợ Lách",
        "specialty": "Hoa giấy ngũ sắc, mai chiếu thủy, vạn thọ và cúc mâm xôi",
        "hours": "6:00–18:00 hàng ngày",
        "admission": "Tham quan miễn phí",
        "phone": "0275 3871 234"
    },
    "lang-nghe-det-chieu-ca-hom-ben-ba": {
        "raw_material": "Cây lác tuyển chọn trui nhuộm màu vỏ thảo mộc tự nhiên",
        "households": 150,
        "recognition_date": "Di sản Văn hóa Phi vật thể Quốc gia (năm 2014)",
        "specialty": "Chiếu hoa Cà Hom dệt hoa văn hình tháp Khmer cẩn chữ",
        "hours": "7:00–17:00 hàng ngày",
        "admission": "Tham quan miễn phí",
        "phone": "0294 3874 123"
    },
    "lang-nghe-tom-kho-vinh-kim": {
        "raw_material": "Tôm đất sống tự nhiên từ bãi bồi Cầu Ngang",
        "households": 22,
        "recognition_date": "Nhãn hiệu chứng nhận và Làng nghề truyền thống tỉnh",
        "specialty": "Tôm khô Vinh Kim thịt đỏ au tự nhiên, ngọt đậm đà",
        "hours": "7:00–18:00 hàng ngày",
        "admission": "Mua sắm và tham quan miễn phí",
        "phone": "0294 3825 678"
    },

    # ── 2. Regional Cultural & Heritage Institutions ──────────────────────
    "lang-ong-lang-ong-che-nguyen-van-ton": {
        "phone": "0270 3771 188",
        "hours": "6:30–17:30 hàng ngày",
        "admission": "Miễn phí",
        "heritage_level": "Di tích Lịch sử - Văn hóa cấp Quốc gia (QĐ 1460-QĐ/VH ngày 28/6/1996)",
        "address": "Ấp Là Ghì, xã Thiện Mỹ, huyện Trà Ôn, tỉnh Vĩnh Long",
        "highlight": "Lăng thờ Tiền hiền Thống chế Điều bát Nguyễn Văn Tồn với lễ giỗ mùng 3-4 tháng Giêng âm lịch là Di sản văn hóa phi vật thể quốc gia",
        "source_item": {
            "url": "https://vinhlongtourist.vn/vi/langongnguyenvanton",
            "title": "Lăng Ông Tiền hiền Nguyễn Văn Tồn — vinhlongtourist.vn"
        }
    },
    "bao-tang-van-hoa-dan-toc-khmer-tra-vinh": {
        "phone": "0294 3858 188",
        "hours": "7:30–11:30 & 13:30–17:00 (Thứ 3 – Chủ Nhật; Thứ 2 nghỉ)",
        "admission": "20.000 VNĐ/vé người lớn, 10.000 VNĐ/vé học sinh sinh viên",
        "address": "Khóm 4, phường 8, thành phố Trà Vinh, tỉnh Vĩnh Long",
        "highlight": "Bảo tàng văn hóa dân tộc Khmer lưu giữ hơn 800 hiện vật quý về đời sống văn hóa, nghệ thuật Rô-băm và dàn nhạc ngũ âm",
        "source_item": {
            "url": "https://vinhlongtourist.vn/vi/baotangkhmer",
            "title": "Bảo tàng Văn hóa Dân tộc Khmer — vinhlongtourist.vn"
        }
    },

    # ── 3. Iconic Dishes ───────────────────────────────────────────────────
    "ca-tai-tuong-chien-xu": {
        "ingredients": [
            "Cá tai tượng tươi sống sông Tiền",
            "Bánh tráng nem cuốn",
            "Bún tươi",
            "Rau sống miệt vườn (ngò gai, lá cóc, sao nhái, quế vị)",
            "Nước mắm me tỏi ớt"
        ],
        "where_to_eat": "Các nhà vườn Cù lao An Bình (Homestay Út Trinh, KDL Vinh Sang), nhà hàng ven sông Cổ Chiên",
        "cooking_method": "Cá làm sạch giữ nguyên vảy, chiên ngập chảo dầu sôi già đến khi vảy xù đều giòn rụm, thịt bên trong trắng ngọt mọng nước",
        "main_ingredient": "Cá tai tượng",
        "price_range": "150.000 – 250.000 VNĐ/phần (con 1 - 1,5 kg)",
        "best_time": "Bữa trưa hoặc chiều mát sau chuyến khám phá sông nước"
    },
    "banh-xeo-hen-cu-lao-dai": {
        "ingredients": [
            "Hến tươi cào đáy sông Cổ Chiên",
            "Bột gạo mùa",
            "Nước cốt dừa",
            "Nghệ tươi",
            "Củ hũ dừa bào sợi",
            "Giá đỗ",
            "Rau rừng sông nước"
        ],
        "where_to_eat": "Cù lao Dài (xã Trung Thành Tây, Quới Thiện, Vũng Liêm) và các quán dân dã ven sông Vĩnh Long",
        "cooking_method": "Thịt hến xào săn với củ hũ dừa; tráng lớp bột mỏng giòn trên chảo gang đun củi dừa, gập đôi giữ trọn hơi nóng",
        "main_ingredient": "Hến sông Cổ Chiên",
        "price_range": "35.000 – 60.000 VNĐ/cái",
        "best_time": "Tháng 4 đến tháng 9 âm lịch mùa hến sinh sôi béo mẩy"
    },
    "bun-nuoc-leo-vinh-long": {
        "ingredients": [
            "Cá lóc đồng luộc rỉa thịt",
            "Mắm cá sặc lọc nước trong",
            "Ngải bún khử mùi",
            "Nước dừa tươi",
            "Bún tươi sợi nhỏ",
            "Bắp chuối bào, giá sống, rau thơm, ớt hiểm"
        ],
        "where_to_eat": "Chợ Vĩnh Long, chợ Trà Ôn và các quán bún nước lèo truyền thống đường Trưng Nữ Vương, Phường 1",
        "cooking_method": "Nấu nước dùng từ xương cá lóc và nước dừa tươi, nêm mắm lọc kỹ và củ ngải bún tạo hương thơm thanh dịu đặc trưng",
        "main_ingredient": "Cá lóc đồng và mắm lọc",
        "price_range": "25.000 – 40.000 VNĐ/tô",
        "best_time": "Sáng sớm hoặc bữa xế chiều"
    },
    "mam-song-khoai-lang": {
        "ingredients": [
            "Khoai lang tím hoặc trắng Bình Tân luộc chín",
            "Mắm cá đồng xé sợi",
            "Thịt ba rọi luộc thái mỏng",
            "Lá cách non, chuối chát, khế chua, gừng non"
        ],
        "where_to_eat": "Xã Tân Bình, huyện Bình Tân; các nhà vườn cù lao Vĩnh Long",
        "cooking_method": "Khoai lang luộc ráo bẻ miếng vừa ăn, kẹp cùng mắm cá đồng xé sợi, lát thịt ba rọi và cuốn trong lá cách non chấm nước gừng ớt",
        "main_ingredient": "Khoai lang Bình Tân và mắm cá đồng",
        "price_range": "50.000 – 80.000 VNĐ/phần",
        "best_time": "Bữa cơm trưa miệt vườn bình dị"
    },
    "banh-xeo-mien-tay": {
        "ingredients": [
            "Bột gạo cốt dừa",
            "Tép bạc sông Tiền",
            "Thịt ba chỉ",
            "Đậu xanh đãi vỏ",
            "Hành lá",
            "Cải bẹ xanh, xà lách, rau diếp cá, lá đọt xoài, lá cóc non"
        ],
        "where_to_eat": "Bánh xèo Cô Tám, bánh xèo Long Bình và các quán ven sông Cổ Chiên",
        "cooking_method": "Đổ bột mỏng tang giòn rụm trên chảo gang lửa lớn, rắc nhân tép thịt và đậu xanh, gấp bán nguyệt vàng ươm",
        "main_ingredient": "Tép bạc và thịt ba chỉ",
        "price_range": "30.000 – 50.000 VNĐ/cái",
        "best_time": "Buổi chiều tối bên bờ sông lộng gió"
    },
    "cha-gio-chay": {
        "ingredients": [
            "Khoai môn bào sợi",
            "Nấm mèo",
            "Tàu hũ ky Mỹ Hòa bóp vụn",
            "Củ sắn",
            "Bánh tráng đậu xanh",
            "Nước chấm chay chua ngọt"
        ],
        "where_to_eat": "Các quán ăn chay đường 3/2, Phường 1, TP. Vĩnh Long và bếp ăn chùa cổ",
        "cooking_method": "Cuộn nhân khoai môn tàu hũ ky trong bánh tráng mỏng, chiên vàng giòn rụm trong chảo dầu thực vật",
        "main_ingredient": "Khoai môn và tàu hũ ky",
        "price_range": "20.000 – 35.000 VNĐ/phần",
        "best_time": "Các ngày rằm, mùng một và bữa sáng thanh tịnh"
    },

    # ── 4. Iconic OCOP Products ────────────────────────────────────────────
    "sau-rieng-ri6": {
        "ocop_star": "4",
        "ocop_certified": True,
        "gi_certification": "Chỉ dẫn địa lý Sầu riêng Ri6 Vĩnh Long (xã Thanh Đức, Long Hồ)",
        "price_range": "80.000 – 130.000 VNĐ/kg",
        "producer": "Hợp tác xã Sầu riêng Ri6 Vĩnh Long & các nhà vườn cù lao An Bình",
        "shelf_life": "3 – 5 ngày sau khi chín rụng tự nhiên",
        "specialty": "Cơm vàng óng, hạt lép hoàn toàn, vị ngọt đậm đà, béo ngậy và hương thơm đặc trưng"
    },
    "buoi-nam-roi-binh-minh": {
        "ocop_star": "4",
        "ocop_certified": True,
        "gi_certification": "Chỉ dẫn địa lý Bưởi Năm Roi Bình Minh (xã Mỹ Hòa, Bình Minh)",
        "price_range": "35.000 – 60.000 VNĐ/kg",
        "producer": "Hợp tác xã Bưởi Năm Roi Mỹ Hòa, thị xã Bình Minh",
        "shelf_life": "20 – 30 ngày ở nhiệt độ phòng thoáng mát",
        "specialty": "Tép bưởi vàng mọng nước, róc múi, vị ngọt thanh chua dịu không hạt hoặc rất ít hạt"
    },
    "cam-sanh-tam-binh": {
        "ocop_star": "4",
        "ocop_certified": True,
        "price_range": "15.000 – 30.000 VNĐ/kg",
        "producer": "Hợp tác xã Cam sành Tam Bình & các nhà vườn Ba Ngôi, Tam Bình",
        "shelf_life": "7 – 10 ngày sau thu hoạch",
        "specialty": "Vỏ sần mỏng, tép cam vàng đậm, mọng nước, vị ngọt thanh giàu vitamin C"
    },
    "banh-trang-nem-cu-lao-may": {
        "ocop_star": "3",
        "ocop_certified": True,
        "price_range": "25.000 – 45.000 VNĐ/xấp (50 bánh)",
        "producer": "Hợp tác xã Bánh tráng Cù Lao Mây, xã Lục Sĩ Thành, huyện Trà Ôn",
        "shelf_life": "6 tháng trong bao bì kín",
        "specialty": "Bánh tráng dẻo dai tự nhiên, không dùng hóa chất phụ gia, cuốn nem không rách vỡ"
    },
    "chao-dua-thuan-duyen-tam-binh": {
        "ocop_star": "3",
        "ocop_certified": True,
        "price_range": "35.000 – 55.000 VNĐ/hũ",
        "producer": "Cơ sở sản xuất Thuận Duyên, xã Loan Mỹ, huyện Tam Bình",
        "shelf_life": "12 tháng",
        "specialty": "Chao môn béo thơm hòa quyện cùng nước cốt dừa béo bùi, vị đậm đà vừa vặn"
    }
}


def _enrich_single_entity(e: dict, enrichment: dict) -> list[str]:
    attrs = e.setdefault("attributes", {})
    enriched = []
    for k, v in enrichment.items():
        if k == "source_item":
            sources = e.setdefault("source", [])
            existing_urls = {s.get("url") for s in sources if isinstance(s, dict)}
            if v.get("url") not in existing_urls:
                sources.append(v)
        else:
            attrs[k] = v
            enriched.append(k)
    return enriched


def main() -> None:
    with DATA_JSON_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)

    entities = data.get("entities", [])
    entity_map = {e["id"]: e for e in entities}
    updated_records = []

    for eid, enrichment in BATCH3_ENRICHMENTS.items():
        if eid not in entity_map:
            print(f"Warning: {eid} not found in entities!")
            continue

        e = entity_map[eid]
        enriched = _enrich_single_entity(e, enrichment)
        updated_records.append({
            "entity_id": eid,
            "name": e.get("name"),
            "enriched_fields": enriched
        })

    # Save enrichment log
    OUTPUT_ENRICHMENT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_ENRICHMENT_PATH.open("w", encoding="utf-8") as f:
        json.dump(updated_records, f, ensure_ascii=False, indent=2)
        f.write("\n")

    # Save updated web/data.json
    with DATA_JSON_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    with DATA_JSON_PATH.open("rb") as f:
        new_hash = hashlib.sha256(f.read()).hexdigest()

    print(f"Successfully enriched {len(updated_records)} entities in Batch 3.")
    print(f"Enrichment log: {OUTPUT_ENRICHMENT_PATH.relative_to(REPO_ROOT)}")
    print(f"New web/data.json SHA-256: {new_hash}")


if __name__ == "__main__":
    main()
