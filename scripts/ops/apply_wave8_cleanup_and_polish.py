#!/usr/bin/env python3
"""Wave 8 deterministic deep cleanup: addresses, descriptions, geos, types, 0 CTI debt, 20 merges & 40 prunes.

Supports both local SQLite (`--sqlite`) and VPS PostgreSQL (`--postgres-env`).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sqlite3
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "agent"))

from entity_details import (  # noqa: E402
    DETAIL_TABLES,
    KIND_TABLE,
    UNIVERSAL,
    _sync_cti_detail_row,
    delete_entity_details,
    split_typed,
)
from entity_schemas import KIND_OF_TYPE  # noqa: E402

BBOX_LAT = (9.0, 10.6)
BBOX_LNG = (105.6, 107.1)
OLD_CITY_CENTROIDS: tuple[tuple[float, float, str], ...] = (
    (10.2537, 105.9722, "VL"),
    (10.2433, 106.3755, "BT"),
    (9.9347, 106.3453, "TV"),
)

# Nhóm C: Deep pruning of retail shops, budget 2-star hotels, generic markets/blobs & micro single-brand items (40).
WAVE8_HARD_DELETES: tuple[str, ...] = (
    # Retail shops & OCOP showrooms mistyped as attractions (7)
    "cua-hang-dac-san-mekong",
    "cua-hang-dac-san-mien-tay-ba-bay-nem-vinh-long",
    "cua-hang-dac-san-mien-tay-tra-vinh-tra-vinh",
    "cua-hang-dac-san-que-hai-ung",
    "cua-hang-ocop-tinh-ben-tre-trung-tam-xuc-tien-dau-tu-ho-tro-doanh-nghiep-ben-tre",
    "cua-hang-ocop-tra-vinh-trung-tam-xuc-tien-thuong-mai-tinh-tra-vinh",
    "cua-hang-ocop-vinh-long-trung-tam-xuc-tien-thuong-mai-vinh-long",
    # Remaining plain 2-star / budget motels (5)
    "khach-san-ham-luong",
    "khach-san-phuoc-thanh-iv",
    "one-hotel",
    "khach-san-hoang-khiem",
    "farmstay-sinh-thai-nguyen-gia",
    # Local wholesale/district markets, flood canal & generic district orchard blobs (6)
    "cho-dau-moi-nong-san-ba-cang-song-phu",
    "cho-dai-an",
    "cho-cho-lach",
    "kenh-tra-on-vinh-long",
    "vuon-cay-an-trai-miet-vuon-long-ho",
    "vuon-cay-an-trai-mo-cay-bac",
    # Minor single-brand / household OCOP products overlapping regional staples (12)
    "banh-trang-ngot-le-hang",
    "cha-lua-thanh-cong",
    "gao-tan-tien",
    "mat-ong-hai-nuong",
    "mut-dua-la-dua-duc-dat",
    "mut-dua-sap-cam-hang",
    "mut-xoai-cat-num-foodo-ocop",
    "tom-xe-hiep-my-dong",
    "tra-gung-mat-ong-nguyen-chat-gingo",
    "tra-kho-qua-rung-cai-von",
    "ca-phi-sa-ot-thanh-phuoc",
    "cua-lot-vinacrab-long-toan",
    # Generic / stub eateries & nationwide holiday (10)
    "tet-nguyen-dan-mien-tay",
    "hu-tieu-chay",
    "banh-bao-tai-co",
    "com-ga-bong-viet",
    "ca-phe-cay-bang-phuong-4-tra-vinh",
    "sinh-to-ha-tien-duong-pham-thai-buong-vinh-long",
    "che-khuc-bach-khu-dem-vinh-long-cho-dem-phuong-1-vinh-long",
    "hu-tieu-nam-vang-99-vinh-long",
    "quan-hu-tieu-nam-vang-chu-teo-tra-vinh",
    "com-chay-au-lac-vinh-long",
)

# Nhóm B: Shadow-duplicate & overlapping entity merges with 301 redirects (20).
WAVE8_MERGES_BY_DST: dict[str, list[str]] = {
    "khu-luu-niem-truong-vinh-ky": ["nha-bia-tuong-niem-truong-vinh-ky"],
    "san-chim-vam-ho": ["du-lich-sinh-thai-san-chim-vam-ho-trai-nghiem-thuyen-rung"],
    "somo-farm-cuu-long": ["somo-farm-cuu-long-mang-thit"],
    "du-lich-sinh-thai-cu-lao-may-nam-khanh": ["nam-khanh"],
    "tham-lo-gach-mang-thit": [
        "tour-vuong-quoc-gach-ngoi-mang-thit",
        "tour-dap-xe-kham-pha-lo-gach-mang-thit",
    ],
    "tat-muong-bat-ca": ["tour-nha-gom-tat-muong-bat-ca"],
    "vuon-dua-sap-cau-ke-phong-thanh": ["vuon-dua-sinh-thai-cau-ke-tra-vinh"],
    "coco-home": ["coco-homestay"],
    "khoai-lang-binh-tan": ["vung-khoai-lang-binh-tan"],
    "buoi-da-xanh": ["vung-buoi-da-xanh-chau-thanh"],
    "buoi-nam-roi-binh-minh": ["hop-tac-xa-buoi-nam-roi-my-hoa"],
    "dua-sap-cau-ke": ["htx-nong-nghiep-thong-hoa-dua-sap", "dua-sap-hoa-tan"],
    "mat-hoa-dua-va-duong-hoa-dua-tra-vinh-ocop-5-sao": ["cong-ty-tnhh-tra-vinh-farm-sokfarm"],
    "sau-rieng-cai-mon": ["sau-rieng-cho-lach"],
    "banh-tet-tra-cuon": ["banh-tet-tra-cuon-co-huong"],
    "lau-mam-mien-tay": ["lau-mam-ben-tre"],
    "keo-dua-ben-tre": ["keo-dua-tuyet-phung", "keo-dua-tan-thach"],
}

# Nhóm A3: Explicit placeId corrections (6 entities).
WAVE8_PLACE_FIXES: dict[str, str] = {
    "cocohut-homestay": "p-phu-tuc",
    "homestay-lang-be": "xa-giao-long",
    "muoi-quynh-homestay": "xa-hoa-minh",
    "homestay-nam-ham-luong": "xa-phuoc-my-trung",
    "song-thom-rach-thom-ben-tre": "p-mo-cay",
    "cho-dem-ben-tre": "p-phu-khuong",
}

# Nhóm A3: Corrected coordinates for mis-pinned type='place' ward centroids (4 wards).
WAVE8_WARD_COORD_FIXES: dict[str, list[float]] = {
    "xa-luc-si-thanh": [10.0040, 105.9440],
    "p-tan-quoi": [10.0885, 105.7860],
    "xa-long-hoa": [9.7820, 106.4890],
    "xa-hoa-minh": [9.9167, 106.4274],
}

# Nhóm A4: Type fixes (7 entities).
WAVE8_TYPE_FIXES: dict[str, str] = {
    "quyt-duong-cau-ke": "product",
    "khu-du-lich-sinh-thai-hoang-hao": "attraction",
    "khu-sinh-thai-gio-duoc-thanh-phu-ben-tre": "attraction",
    "du-lich-sinh-thai-nam-son": "attraction",
    "khu-am-thuc-pho-cho-phu-khuong": "attraction",
    "kem-xoi-dua---khu-sao-mai": "cafe",
    "yogurt-dua---ba-muoi-thang-tu": "cafe",
}

# Nhóm A4: Clear all 30 surviving typed_uncoercible CTI attributes (None = pop key).
WAVE8_ATTR_COERCION_FIXES: dict[str, dict[str, Any]] = {
    "homestay-ut-trinh": {"rooms": 4},
    "nha-dua-cocohome": {"rooms": 6},
    "nha-tho-chanh-toa-ben-tre-ben-tre": {"founding_year": 1928},
    "thanh-that-cao-dai-ben-tre-ben-tre": {"founding_year": 1930},
    "chua-long-thanh-ben-tre": {"founding_year": None},
    "mieu-ba-chua-xu-my-hoa-ben-tre": {"founding_year": None},
    "mieu-ba-chua-xu-vinh-long-vinh-long": {"founding_year": None},
    "lo-com-cuu-long-vlt": {"households": None},
    "dong-muoi-bao-thanh": {"households": 350},
    "lang-dan-luc-binh-ngai-tu": {"households": 800},
    "lang-nghe-banh-phong-son-doc": {"households": 60},
    "lang-nghe-chi-xo-dua-khanh-thanh-tan": {"households": 60},
    "lang-nghe-dan-dat-ba-tri": {"households": 300},
    "lang-nghe-dan-dat-dai-an": {"households": 120},
    "lang-nghe-dan-dat-phuoc-tuy": {"households": 180},
    "lang-nghe-dan-gio-cong-dua-hung-phong": {"households": 500},
    "lang-nghe-dan-non-la-tt-long-ho": {"households": 120},
    "lang-nghe-det-chieu-ca-hom-ben-ba": {"households": 450},
    "lang-nghe-hoa-kieng-thanh-tan": {"households": 280},
    "lang-nghe-keo-dua-ba-tri": {"households": 30},
    "lang-nghe-san-xuat-chi-xo-dua-an-thanh": {"households": 50},
    "lang-nghe-thach-dua-hung-phong": {"households": 120},
    "lang-nghe-thu-cong-dua-phuoc-long": {"households": 90},
    "lang-nghe-thu-cong-my-nghe-dua-mo-cay-nam": {"households": 150},
    "lang-nghe-thu-cong-my-nghe-tu-dua-tai-tan-thach": {"households": 85},
    "lang-nghe-tieu-thu-cong-nghiep-duc-my": {"households": 200},
    "lang-nghe-tieu-thu-cong-nghiep-tre-ham-giang-co-so-tri-canh": {"households": 45},
    "lang-nghe-tom-kho-vinh-kim": {"households": 50},
    "lang-nghe-tre-truc-ba-tri": {"households": 100},
    "vung-cam-sanh-tra-on": {"households": 6500},
}

# Nhóm A2: Explicit clean rewrites for structured raw templates & legacy phrasing in description (24).
WAVE8_DESC_OVERRIDES: dict[str, str] = {
    "chua-giac-thien-vinh-long": (
        "Ngôi cổ tự Phật giáo Bắc tông (còn gọi Chùa Gò Công) tại số 70 Trần Phú, phường Phước Hậu, tỉnh Vĩnh Long. "
        "Chùa mang kiến trúc Phật giáo cải cách hài hòa với vườn tượng Phật ngoài trời, tháp mộ tổ sư và ao sen thanh tịnh; "
        "thờ Phật Thích Ca, Phật A Di Đà, Quán Thế Âm Bồ Tát và Địa Tạng Bồ Tát, tổ chức trang nghiêm lễ Phật Đản và Vu Lan hằng năm."
    ),
    "mieu-ba-chua-xu-vinh-long-vinh-long": (
        "Ngôi miếu tín ngưỡng dân gian hình thành từ thế kỷ 19 thờ Bà Chúa Xứ và Ngũ Hành Nương Nương theo kiến trúc Nam Bộ cổ truyền. "
        "Mái cong lợp ngói ống đắp nổi rồng phượng trang nghiêm, sân rộng thoáng đãng; hằng năm tổ chức lễ Vía Bà Chúa Xứ dịp 23–27/4 âm lịch với múa bóng rỗi và thả hoa đăng."
    ),
    "nha-tho-chanh-toa-ben-tre-ben-tre": (
        "Ngôi thánh đường Công giáo xây dựng từ năm 1928 tại phường An Hội, kết hợp đường nét kiến trúc Gothic với không gian nhiệt đới Nam Bộ. "
        "Tháp chuông cao, hệ cửa kính màu nghệ thuật cùng nội thất rộng thoáng tạo điểm nhấn kiến trúc đô thị, đón giáo dân và khách tham quan vào các dịp Giáng Sinh, Phục Sinh và Lễ Đức Mẹ Vô Nhiễm (8/12)."
    ),
    "thanh-that-cao-dai-ben-tre-ben-tre": (
        "Thánh thất đạo Cao Đài dựng từ thập niên 1930 tại phường Phú Khương, mang diện mạo nền trắng, cột tròn vàng xanh, tháp trụ hai bên cổng chính và biểu tượng Thiên Nhãn trên mặt tiền. "
        "Các mảng phù điêu Long – Lân – Quy – Phụng được chạm trổ công phu; hằng năm tổ chức lễ Vía Đức Cao Đài (9/1 âm lịch) và Hội Yến Diêu Trì Cung (15/8 âm lịch)."
    ),
    "chua-long-thanh-ben-tre": (
        "Ngôi cổ tự Phật giáo hình thành từ thế kỷ 19 tại khu vực Giồng Trôm, gây ấn tượng với tôn tượng Phật Di Lặc ngoài trời kích thước lớn giữa vườn cây và ao sen yên tĩnh. "
        "Tháp thờ xây theo lối Nam Bộ truyền thống, đón đông đảo phật tử hành hương vào dịp Thượng Nguyên (15/1 âm lịch), Phật Đản và Vu Lan."
    ),
    "mieu-ba-chua-xu-my-hoa-ben-tre": (
        "Ngôi miếu dân gian cổ từ thế kỷ 19 tại khu vực Mỹ Hóa, phường Phú Khương, giữ nét kiến trúc Nam Bộ truyền thống với mái đao cong, tường vàng, hoa văn rồng phượng đắp nổi và bình hương lớn giữa sân. "
        "Hằng năm miếu tổ chức lễ Vía Bà Chúa Xứ vào ngày 23–27/4 âm lịch."
    ),
    "banh-canh-cho-ben-tre-hang-goc-cho-ben-tre-ben-tre": (
        "Hàng bánh canh lâu năm ngay góc cổng chợ trên đường Nguyễn Đình Chiểu, phường Phú Khương, bán buổi sáng cho người dân địa phương. "
        "Nước lèo ninh từ xương hầm lâu cho vị ngọt tự nhiên, kết hợp bánh canh sợi tươi mềm dai và giò heo béo vừa; giá tham khảo khoảng 25.000–35.000đ/tô."
    ),
    "bun-thit-nuong-co-hanh-ben-tre": (
        "Quán bún thịt nướng bình dân trên đường Đồng Khởi (gần công viên Đồng Khởi), phường Phú Khương, phục vụ từ trưa đến tối. "
        "Thịt nướng than hoa thơm lừng dọn cùng bì, chả giò giòn và nước mắm pha chua ngọt kiểu Nam Bộ; giá tham khảo khoảng 25.000–30.000đ/phần."
    ),
    "che-ba-cam-khu-vuc-cho-ben-tre-ben-tre": (
        "Gánh chè truyền thống gần cổng sau khu vực chợ tại phường Phú Khương, mở bán từ 13:00 đến 20:00. "
        "Quán bán chè thập cẩm, chè đậu xanh nước dừa và chè bắp nấu từ nước cốt dừa tươi béo ngậy, mát lạnh buổi chiều; giá tham khảo khoảng 10.000–20.000đ/ly."
    ),
    "banh-xeo-muoi-xinh-ben-tre": (
        "Quán bánh xèo buổi chiều tối trên đường Nguyễn Thị Định, phường Phú Khương, chuyên bánh xèo tôm thịt và bánh xèo mực. "
        "Bánh đổ chảo lớn giòn rụm, nhân tôm sú tươi ngọt thịt, dọn kèm rổ rau vườn nhà và nước mắm chua ngọt; giá tham khảo khoảng 20.000–30.000đ/cái."
    ),
    "chao-long-ba-nam-cho-phuong-4-ben-tre": (
        "Quán cháo sáng quen thuộc tại khu vực chợ ở phường Phú Khương, chuyên cháo lòng heo tươi chế biến trong ngày. "
        "Lòng được làm sạch kỹ, giòn ngọt không tanh, ăn cùng tô cháo sánh vừa nóng hổi; giá tham khảo khoảng 20.000–30.000đ/tô."
    ),
    "goi-cuon-tom-thit-ba-hai-chau-thanh-ben-tre": (
        "Quán ăn vặt bình dân chuyên gỏi cuốn tôm thịt và cuốn diếp cá tại khu vực Châu Thành, mở cửa từ 8:00 đến 17:00. "
        "Tôm luộc tươi ngọt cuốn chắc tay cùng bún và rau thơm, chấm tương đen đậu phộng giã thô béo bùi; giá tham khảo khoảng 5.000–7.000đ/cuốn."
    ),
    "hang-banh-uot-co-lan-cho-ba-tri-ben-tre": (
        "Hàng điểm tâm sáng bên trong chợ Ba Tri, phường Ba Tri, chuyên bánh ướt lòng gà và bánh ướt cuốn gọn nhẹ. "
        "Bánh ướt tráng mỏng mềm mướt kết hợp lòng gà xào sả ớt thơm cay và hành phi giòn rắc đều trên mặt; giá tham khảo khoảng 20.000–30.000đ/phần."
    ),
    "vuon-am-thuc-truc-giang-ben-tre": (
        "Quán ăn sân vườn tại 76A Võ Nguyên Giáp, phường Phú Khương với không gian chòi lá thoáng mát rợp bóng cây xanh. "
        "Thực đơn chuyên các món ếch đồng theo mùa, đặc biệt là lẩu ếch nấu nước dừa béo thanh; giá tham khảo khoảng 150.000–350.000đ/người."
    ),
    "vuon-am-thuc-mai-an-tiem-ben-tre": (
        "Quán ẩm thực sân vườn tại 108E An Thuận B, phường Phú Khương với khuôn viên rộng thoáng phù hợp họp mặt gia đình. "
        "Món nổi bật gồm cá lóc nướng trui ăn kèm bún, rau rừng và ếch um dừa đậm vị quê; giá tham khảo khoảng 150.000–400.000đ/người."
    ),
    "am-thuc-ngo-dong-ben-tre": (
        "Nhà hàng ẩm thực sân vườn kết hợp chòi thủy tạ tại 165B Đồng Khởi, phường Bến Tre với không gian đồng quê rộng rãi. "
        "Thực đơn chuyên heo rừng quay da giòn chấm mắm me, heo rừng nướng sả và gà trống thiến; giá tham khảo khoảng 200.000–500.000đ/người."
    ),
    "nem-nuong-thanh-binh-ben-tre": (
        "Quán nem nướng lâu năm gần khu vực bến phà Hàm Luông cũ, phường An Hội, chuyên nem nướng than hồng và nem lụi cuốn bánh tráng. "
        "Thịt nem thơm mùi than hoa, cuốn bánh tráng mỏng cùng đồ chua và đậu phộng rang béo bùi; giá tham khảo khoảng 30.000–50.000đ/phần."
    ),
    "bun-suong-du-van-tra-vinh": (
        "Quán bún suông gia truyền từ năm 1986 tại 644 Võ Nguyên Giáp, phường Nguyệt Hóa, bán từ sáng cho khách địa phương và du khách. "
        "Chả tôm quết tay nhồi thành cọng suông dai ngọt hòa cùng nước dùng me chua thanh và tương xay đậm đà; giá tham khảo khoảng 30.000đ/tô."
    ),
    "bun-suong-ut-tam-tra-vinh": (
        "Quán bún suông sáng lâu năm tại 28 Nguyễn Thị Minh Khai, phường Trà Vinh, thường hết khách trước 10:00. "
        "Chả tôm quết theo vị truyền thống ăn cùng nước dùng me thanh dịu, giá bình dân tham khảo khoảng 25.000–40.000đ/tô."
    ),
    "quan-bun-nuoc-leo-duong-dong-khoi-tra-vinh": (
        "Quán bún nước lèo bán chuyên buổi xế chiều tại 94A Đồng Khởi, phường Trà Vinh, rất đông khách địa phương. "
        "Nước dùng mắm bò hóc hầm kỹ tạo vị sâu đậm, dùng kèm cá lóc đồng và thịt heo quay giòn; giá tham khảo khoảng 25.000–40.000đ/tô."
    ),
    "quan-di-bay-com-nieu-tra-vinh": (
        "Quán cơm niêu phong cách sân vườn gần khu du lịch Long Đức, phường Long Đức, chuyên bữa cơm gia đình Nam Bộ. "
        "Nổi bật với cơm niêu đất nung giòn đáy ăn cùng kho quẹt, mắm chưng và rau đồng; giá tham khảo khoảng 50.000–100.000đ."
    ),
    "banh-trang-nem-cu-lao-may": (
        "Làng nghề bánh tráng Cù Lao Mây tại xã Lục Sĩ Thành lưu giữ truyền thống hơn 100 năm với hàng chục hộ sản xuất thường xuyên. "
        "Bột gạo pha cùng nước cốt dừa và gia vị được tráng trên vải mùng căng miệng nồi hơi khoảng 10–15 giây để cho ra tấm bánh dẻo mỏng, không gãy khi cuốn, phơi nắng tự nhiên ngoài sân; giá tham khảo 30.000–60.000đ/xấp."
    ),
    "du-lich-sinh-thai-cu-lao-may-nam-khanh": (
        "Homestay và điểm du lịch sinh thái miệt vườn tại ấp Phú Xuân, xã Lục Sĩ Thành với nếp nhà gỗ truyền thống giữa vườn bưởi, sầu riêng và mít Thái. "
        "Du khách có thể câu cá, chèo xuồng thăm vườn trái cây và thưởng thức bữa cơm dân dã Nam Bộ ngay bên dòng sông Hậu."
    ),
    "kenh-tra-on-vinh-long": "Kênh Trà Ôn dài 35 km nối sông Hậu với vùng nội địa Trà Ôn.",  # removed in Wave 8 C anyway
}

DESC_PAREN_RIVER_RE = re.compile(r"\s*\((?:cửa biển|sông|rạch|kênh),\s*(\d+\s*km)\)\.")
DESC_SCENIC_RE = re.compile(r"\s*Đánh giá cảnh quan:\s*\d+/5\.?")
DESC_TRUNC_PRICE_RE = re.compile(r"\bGiá\s+(\d{1,3})\.(?!\d)")
ADDR_GARBLED_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\s*\(\.\s*\)"), ""),
    (re.compile(r"\s+\.,"), ","),
    (re.compile(r"\s+[–—],"), ","),
    (re.compile(r",\s*,"), ","),
    (re.compile(r",\s+Phường\s+[1-9],\s+(Phường\s+)"), r", \1"),
    (re.compile(r"^\s*,\s*|\s*,\s*$"), ""),
)


def _norm(s: str | None) -> str:
    txt = unicodedata.normalize("NFKD", (s or "").lower())
    txt = "".join(ch for ch in txt if not unicodedata.combining(ch)).replace("đ", "d")
    return re.sub(r"[^a-z0-9\s]", " ", txt).strip()


def _non_empty(val: Any) -> bool:
    return bool(val.strip()) if isinstance(val, str) else bool(val)


def _parse_attrs(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            return dict(parsed) if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _parse_coords(raw: Any) -> list[float] | None:
    if isinstance(raw, dict) and raw.get("lat") is not None and raw.get("lng") is not None:
        return [float(raw["lat"]), float(raw["lng"])]
    if isinstance(raw, (list, tuple)) and len(raw) == 2:
        return [float(raw[0]), float(raw[1])]
    if isinstance(raw, str) and raw.strip():
        try:
            return _parse_coords(json.loads(raw))
        except (json.JSONDecodeError, TypeError, ValueError):
            return None
    return None


def _dist_km(a: list[float], b: list[float]) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, [a[0], a[1], b[0], b[1]])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371.0 * 2.0 * math.asin(math.sqrt(h))


def _in_bbox(pt: list[float]) -> bool:
    return BBOX_LAT[0] <= pt[0] <= BBOX_LAT[1] and BBOX_LNG[0] <= pt[1] <= BBOX_LNG[1]


def _near_old_city(pt: list[float]) -> bool:
    return any(_dist_km(pt, [clat, clng]) < 3.0 for clat, clng, _ in OLD_CITY_CENTROIDS)


def _load_dotenv(env_path: Path) -> None:
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _open_conn(args: argparse.Namespace) -> tuple[Any, Any, bool]:
    if args.sqlite is not None:
        conn = sqlite3.connect(str(args.sqlite))
        conn.row_factory = sqlite3.Row
        return conn, conn.cursor(), False
    _load_dotenv(REPO_ROOT / ".env")
    _load_dotenv(Path("/opt/vinhlong360/.env"))
    dsn = os.environ.get("DATABASE_URL", "")
    if not dsn.startswith(("postgres://", "postgresql://")):
        raise SystemExit("DATABASE_URL not configured for --postgres-env")
    import psycopg2  # type: ignore
    import psycopg2.extras  # type: ignore

    conn = psycopg2.connect(dsn)
    return conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor), True


def _load_snapshot(
    cur: Any, is_pg: bool
) -> tuple[dict[str, dict[str, Any]], list[tuple[str, str, str]], list[dict[str, Any]]]:
    cols = (
        'id, type, name, summary, description, "placeId", coordinates, address, phone, website, hours, '
        'price_range, sub_category, best_time, highlight, attributes'
        if is_pg
        else "id, type, name, summary, description, placeId, coordinates, address, phone, website, hours, "
        "price_range, sub_category, best_time, highlight, attributes"
    )
    cur.execute(f"SELECT {cols} FROM entities")
    entities = {}
    for row in cur.fetchall():
        d = dict(row)
        d["attrs"] = _parse_attrs(row["attributes"])
        d["coords_pair"] = _parse_coords(row["coordinates"])
        entities[d["id"]] = d
    cur.execute("SELECT from_id, to_id, type FROM relationships")
    rels = [(r["from_id"], r["to_id"], r["type"]) for r in cur.fetchall()]
    cur.execute("SELECT id, title, stops FROM itineraries")
    return entities, rels, [dict(r) for r in cur.fetchall()]


def _ward_index(entities: dict[str, dict[str, Any]]) -> tuple[set[str], dict[str, set[str]], set[str]]:
    places = {eid for eid, r in entities.items() if r["type"] == "place" and eid != "vinh-long"}
    members: dict[str, set[str]] = defaultdict(set)
    for eid, r in entities.items():
        if r["type"] != "place" and r.get("placeId") in places:
            members[r["placeId"]].add(eid)
    return places, members, {w for w, s in members.items() if s}


def _build_raw_merge_pairs(entities: dict[str, dict[str, Any]], hard_set: set[str]) -> list[tuple[str, str]]:
    all_ids = set(entities)
    return [
        (src, dst)
        for dst, srcs in WAVE8_MERGES_BY_DST.items()
        if dst in all_ids and dst not in hard_set
        for src in srcs
        if src in all_ids and src != dst and src not in hard_set and entities[src]["type"] != "place"
    ]


def _needs_ward_rescue(
    sw: str | None,
    dst: str,
    dw: str | None,
    covered_wards: set[str],
    sim: dict[str, set[str]],
    all_srcs: set[str],
) -> tuple[bool, bool]:
    if sw not in covered_wards or (sim[sw] - all_srcs):
        return False, False
    conflict = dw in covered_wards and len(sim[dw] - all_srcs - {dst}) == 0
    return True, conflict


def _compute_merges(
    entities: dict[str, dict[str, Any]],
    ward_members: dict[str, set[str]],
    covered_wards: set[str],
    hard_set: set[str],
) -> tuple[dict[str, str], dict[str, str], list[dict[str, str]]]:
    sim = {w: set(m) - hard_set for w, m in ward_members.items()}
    merge_map: dict[str, str] = {}
    transfers: dict[str, str] = {}
    exempted: list[dict[str, str]] = []

    raw_pairs = _build_raw_merge_pairs(entities, hard_set)
    all_srcs = {s for s, _ in raw_pairs}
    for src, dst in raw_pairs:
        sw = entities[src].get("placeId")
        dw = transfers.get(dst, entities[dst].get("placeId"))
        rescue, conflict = _needs_ward_rescue(sw, dst, dw, covered_wards, sim, all_srcs)
        if rescue and conflict:
            exempted.append({"id": src, "ward": str(sw), "reason": "merge_would_create_white_zone"})
            continue
        if rescue and sw is not None:
            sim.get(dw or "", set()).discard(dst)
            sim.setdefault(sw, set()).add(dst)
            transfers[dst] = sw
        merge_map[src] = dst
        sim.get(sw or "", set()).discard(src)

    exempted.extend({"id": w, "ward": w, "reason": "ward_became_empty"} for w in covered_wards if len(sim[w]) == 0)
    return merge_map, transfers, exempted


def _apply_merge_utilities(
    entities: dict[str, dict[str, Any]], updates: dict[str, dict[str, Any]], merge_map: dict[str, str]
) -> None:
    for src, dst in sorted(merge_map.items()):
        for field in ("phone", "website", "hours"):
            cur_val = entities[dst]["attrs"].get(field) or entities[dst].get(field)
            src_val = entities[src]["attrs"].get(field) or entities[src].get(field)
            if not _non_empty(cur_val) and _non_empty(src_val):
                cleaned = str(src_val).strip()
                entities[dst]["attrs"][field] = cleaned
                entities[dst][field] = cleaned
                up = updates.setdefault(dst, {})
                up[field] = cleaned
                up["save_attrs"] = True
                up["sync_cti"] = True


def _apply_scalar_map(
    entities: dict[str, dict[str, Any]],
    updates: dict[str, dict[str, Any]],
    removed: set[str],
    field: str,
    mapping: dict[str, str],
    *,
    sync_cti: bool = False,
) -> None:
    for eid, new_val in mapping.items():
        if eid in entities and eid not in removed and entities[eid].get(field) != new_val:
            entities[eid][field] = new_val
            up = updates.setdefault(eid, {})
            up[field] = new_val
            if sync_cti:
                up["sync_cti"] = True


def _apply_ward_coord_fixes(entities: dict[str, dict[str, Any]], updates: dict[str, dict[str, Any]]) -> int:
    fixed = 0
    for wid, pt in WAVE8_WARD_COORD_FIXES.items():
        if wid in entities and entities[wid].get("coords_pair") != pt:
            entities[wid]["coords_pair"] = list(pt)
            updates.setdefault(wid, {})["coordinates"] = list(pt)
            fixed += 1
    return fixed


def _apply_centroid_coord_snaps(
    entities: dict[str, dict[str, Any]], updates: dict[str, dict[str, Any]], removed: set[str]
) -> int:
    snapped = 0
    for eid, row in entities.items():
        if eid in removed or row["type"] == "place":
            continue
        cur_pt = row.get("coords_pair")
        ward = entities.get(row.get("placeId") or "")
        ward_pt = ward.get("coords_pair") if ward else None
        if not cur_pt or not ward_pt or _near_old_city(ward_pt) or not _in_bbox(ward_pt):
            continue
        if _near_old_city(cur_pt) and _dist_km(cur_pt, ward_pt) > 8.0:
            row["coords_pair"] = list(ward_pt)
            updates.setdefault(eid, {})["coordinates"] = list(ward_pt)
            snapped += 1
    return snapped


def _replace_wrong_ward_in_addr(
    addr: str, ward_name: str, known_wards: dict[str, str]
) -> str:
    if ";" in addr or not ward_name:
        return addr
    wnorm = _norm(ward_name)
    found = re.findall(r"(?:Phường|Xã)\s+[A-ZĐÀ-Ỹ][a-zà-ỹđ]+(?:\s+[A-ZĐÀ-Ỹ][a-zà-ỹđ]+){0,3}", addr)
    for tok in found:
        tnorm = _norm(tok)
        if tnorm in known_wards and tnorm != wnorm and wnorm not in _norm(addr):
            addr = addr.replace(tok, ward_name, 1)
            break
    parts = [p.strip() for p in addr.split(",") if p.strip()]
    deduped: list[str] = []
    for part in parts:
        if deduped and _norm(deduped[-1]) == _norm(part):
            continue
        deduped.append(part)
    return ", ".join(deduped)


def _clean_single_address(addr: str, ward_name: str, known_wards: dict[str, str]) -> str:
    out = addr.strip()
    for pat, repl in ADDR_GARBLED_RULES:
        out = pat.sub(repl, out)
    out = _replace_wrong_ward_in_addr(out, ward_name, known_wards)
    return re.sub(r"\s{2,}", " ", out).strip()


def _apply_address_cleanups(
    entities: dict[str, dict[str, Any]], updates: dict[str, dict[str, Any]], removed: set[str]
) -> int:
    places = {eid: r["name"] for eid, r in entities.items() if r["type"] == "place" and eid != "vinh-long"}
    known_wards = {_norm(wname): wname for wname in places.values()}
    fixed = 0
    for eid, row in entities.items():
        if eid in removed or row["type"] == "place":
            continue
        old_addr = (row.get("address") or "").strip()
        if not old_addr:
            continue
        ward_name = places.get(row.get("placeId") or "", "")
        new_addr = _clean_single_address(old_addr, ward_name, known_wards)
        if new_addr != old_addr:
            row["address"] = new_addr
            up = updates.setdefault(eid, {})
            up["address"] = new_addr
            if "address" in row["attrs"]:
                row["attrs"]["address"] = new_addr
                up["save_attrs"] = True
            up["sync_cti"] = True
            fixed += 1
    return fixed


def _clean_single_description(eid: str, desc: str) -> str:
    if eid in WAVE8_DESC_OVERRIDES:
        return WAVE8_DESC_OVERRIDES[eid]
    out = DESC_PAREN_RIVER_RE.sub(r", dài khoảng \1.", desc)
    out = DESC_SCENIC_RE.sub("", out)
    out = DESC_TRUNC_PRICE_RE.sub(r"Giá tham khảo khoảng \1.000đ.", out)
    return re.sub(r"\s{2,}", " ", out).strip()


def _apply_description_cleanups(
    entities: dict[str, dict[str, Any]], updates: dict[str, dict[str, Any]], removed: set[str]
) -> int:
    fixed = 0
    for eid, row in entities.items():
        if eid in removed or row["type"] == "place":
            continue
        old_desc = (row.get("description") or "").strip()
        new_desc = _clean_single_description(eid, old_desc)
        if new_desc and new_desc != old_desc:
            row["description"] = new_desc
            updates.setdefault(eid, {})["description"] = new_desc
            fixed += 1
    return fixed


def _apply_attr_coercion_fixes(
    entities: dict[str, dict[str, Any]], updates: dict[str, dict[str, Any]], removed: set[str]
) -> int:
    fixed = 0
    for eid, patch in WAVE8_ATTR_COERCION_FIXES.items():
        if eid not in entities or eid in removed:
            continue
        attrs = entities[eid]["attrs"]
        for k, v in patch.items():
            if v is None:
                attrs.pop(k, None)
            else:
                attrs[k] = v
        up = updates.setdefault(eid, {})
        up["save_attrs"] = True
        up["sync_cti"] = True
        fixed += 1
    return fixed


def _validate_all_surviving_cti(
    entities: dict[str, dict[str, Any]], updates: dict[str, dict[str, Any]], removed: set[str]
) -> None:
    for eid, row in entities.items():
        if eid in removed:
            continue
        _, _, all_sk = split_typed(row["type"], row["attrs"])
        assert not all_sk, f"{eid} still has uncoercible attrs: {all_sk}"
    for eid, up in updates.items():
        if not up.get("sync_cti"):
            continue
        row = entities[eid]
        effective = {c: row[c] for c in UNIVERSAL if _non_empty(row.get(c))}
        effective.update(row["attrs"])
        uni, det, skipped = split_typed(row["type"], effective)
        assert not skipped, f"{eid} uncoercible after effective merge: {skipped}"
        up["_uni_cols"] = {k: v for k, v in uni.items() if row.get(k) != v}
        up["_det_row"] = det


def _apply_entity_updates(
    entities: dict[str, dict[str, Any]],
    merge_map: dict[str, str],
    transfers: dict[str, str],
    removed: set[str],
) -> tuple[dict[str, dict[str, Any]], dict[str, int]]:
    updates: dict[str, dict[str, Any]] = {}
    for dst, pid in transfers.items():
        if entities[dst].get("placeId") != pid:
            entities[dst]["placeId"] = pid
            updates[dst] = {"placeId": pid}
    _apply_merge_utilities(entities, updates, merge_map)
    _apply_scalar_map(entities, updates, removed, "placeId", WAVE8_PLACE_FIXES)
    _apply_scalar_map(entities, updates, removed, "type", WAVE8_TYPE_FIXES, sync_cti=True)
    ward_coords_fixed = _apply_ward_coord_fixes(entities, updates)
    coord_snaps = _apply_centroid_coord_snaps(entities, updates, removed)
    addr_fixed = _apply_address_cleanups(entities, updates, removed)
    desc_fixed = _apply_description_cleanups(entities, updates, removed)
    cti_fixed = _apply_attr_coercion_fixes(entities, updates, removed)
    _validate_all_surviving_cti(entities, updates, removed)
    stats = {
        "place_fixes": sum(1 for u in updates.values() if "placeId" in u),
        "type_fixes": sum(1 for u in updates.values() if "type" in u),
        "ward_coord_fixes": ward_coords_fixed,
        "coord_snaps": coord_snaps,
        "address_fixes": addr_fixed,
        "description_fixes": desc_fixed,
        "cti_coercion_fixes": cti_fixed,
    }
    return updates, stats


def _rewrite_relationships(
    rels: list[tuple[str, str, str]], merge_map: dict[str, str], surviving_ids: set[str]
) -> list[tuple[str, str, str]]:
    out: set[tuple[str, str, str]] = set()
    for f_id, t_id, rtype in rels:
        nf, nt = merge_map.get(f_id, f_id), merge_map.get(t_id, t_id)
        if nf in surviving_ids and nt in surviving_ids and nf != nt:
            out.add((nf, nt, rtype))
    return sorted(out)


def _remap_stop(stop: Any, merge_map: dict[str, str], surviving_ids: set[str]) -> tuple[str, Any] | None:
    sid = stop.get("id", "") if isinstance(stop, dict) else stop
    mapped = merge_map.get(sid, sid)
    if mapped not in surviving_ids:
        return None
    cur_stop = dict(stop, id=mapped) if isinstance(stop, dict) else mapped
    return mapped, cur_stop


def _rewrite_itineraries(
    itineraries: list[dict[str, Any]], merge_map: dict[str, str], surviving_ids: set[str]
) -> list[dict[str, Any]]:
    updates: list[dict[str, Any]] = []
    for it in itineraries:
        raw = it.get("stops")
        old_stops = json.loads(raw) if isinstance(raw, str) else list(raw or [])
        new_stops: list[Any] = []
        last_sid: str | None = None
        for stop in old_stops:
            remapped = _remap_stop(stop, merge_map, surviving_ids)
            if remapped is None:
                continue
            mapped, cur_stop = remapped
            if mapped != last_sid:
                last_sid = mapped
                new_stops.append(cur_stop)
        assert new_stops, f"Itinerary {it['id']} became empty after cleanup"
        if json.dumps(old_stops, sort_keys=True) != json.dumps(new_stops, sort_keys=True):
            updates.append({"id": it["id"], "stops": new_stops})
    return updates


def _resolve_chain(src: str, dst: str, combined: dict[str, str]) -> str:
    seen = {src}
    cur = dst
    while cur in combined and cur not in seen:
        seen.add(cur)
        cur = combined[cur]
    return cur


def _merge_redirects(
    redirects_path: Path | None, merge_map: dict[str, str], surviving_ids: set[str]
) -> dict[str, str]:
    existing: dict[str, str] = {}
    if redirects_path and redirects_path.exists():
        existing = json.loads(redirects_path.read_text(encoding="utf-8"))
    combined = {**existing, **merge_map}
    flattened: dict[str, str] = {}
    for src, dst in combined.items():
        cur = _resolve_chain(src, dst, combined)
        if cur != src and cur in surviving_ids and src not in surviving_ids:
            flattened[src] = cur
    for k, v in flattened.items():
        assert k != v and v not in flattened and v in surviving_ids
    return dict(sorted(flattened.items()))


def _build_plan(
    entities: dict[str, dict[str, Any]],
    rels: list[tuple[str, str, str]],
    itineraries: list[dict[str, Any]],
    redirects_path: Path | None,
) -> dict[str, Any]:
    places, ward_members, covered_wards = _ward_index(entities)
    hard_set = {eid for eid in WAVE8_HARD_DELETES if eid in entities and eid not in places}
    merge_map, transfers, exempted = _compute_merges(entities, ward_members, covered_wards, hard_set)
    assert not exempted, f"Exempted guardrails triggered: {exempted}"

    removed = hard_set | set(merge_map)
    surviving_ids = set(entities) - removed
    updates, fix_stats = _apply_entity_updates(entities, merge_map, transfers, removed)
    remapped_rels = _rewrite_relationships(rels, merge_map, surviving_ids)
    itin_updates = _rewrite_itineraries(itineraries, merge_map, surviving_ids)
    redirects = _merge_redirects(redirects_path, merge_map, surviving_ids)

    return {
        "counts": {
            "before_entities": len(entities),
            "after_entities": len(surviving_ids),
            "catalog_before": sum(1 for r in entities.values() if r["type"] != "place"),
            "catalog_after": sum(1 for eid in surviving_ids if entities[eid]["type"] != "place"),
            "merged": len(merge_map),
            "hard_deleted": len(hard_set),
            **fix_stats,
            "covered_wards": len(covered_wards),
            "redirects_total": len(redirects),
            "itineraries_updated": len(itin_updates),
            "before_relationships": len(rels),
            "after_relationships": len(remapped_rels),
        },
        "hard_deletes": sorted(hard_set),
        "merge_map": dict(sorted(merge_map.items())),
        "entity_updates": updates,
        "entities_state": entities,
        "remapped_rels": remapped_rels,
        "itinerary_updates": itin_updates,
        "redirects": redirects,
    }


def _sync_changed_cti(conn: Any, is_pg: bool, eid: str, etype: str, det: dict[str, Any]) -> None:
    ph = "%s" if is_pg else "?"
    kind = KIND_OF_TYPE.get(etype)
    table = KIND_TABLE.get(kind or "")
    cur = conn.cursor()
    for stale_table in DETAIL_TABLES:
        if stale_table != table:
            cur.execute(f"DELETE FROM {stale_table} WHERE entity_id = {ph}", [eid])
    _sync_cti_detail_row(conn, is_pg, ph, eid, kind, table, det)


def _encode_json_field(val: Any, is_pg: bool) -> Any:
    if is_pg:
        import psycopg2.extras  # type: ignore

        return psycopg2.extras.Json(val)
    return json.dumps(val, ensure_ascii=False)


def _write_entity_update(conn: Any, is_pg: bool, eid: str, up: dict[str, Any], row: dict[str, Any]) -> None:
    ph = "%s" if is_pg else "?"
    scalar_fields = ("type", "name", "summary", "description", "placeId", "address", "phone", "website", "hours")
    col_map: dict[str, Any] = {c: up[c] for c in scalar_fields if c in up}
    col_map.update(up.get("_uni_cols") or {})
    cols = [f'"{k}" = {ph}' for k in col_map]
    vals: list[Any] = list(col_map.values())
    if "coordinates" in up:
        cols.append(f"coordinates = {ph}")
        vals.append(_encode_json_field(up["coordinates"], is_pg))
    if up.get("save_attrs"):
        cols.append(f"attributes = {ph}")
        vals.append(_encode_json_field(row["attrs"], is_pg))
    if cols:
        conn.cursor().execute(f"UPDATE entities SET {', '.join(cols)} WHERE id = {ph}", [*vals, eid])
    if up.get("sync_cti"):
        _sync_changed_cti(conn, is_pg, eid, row["type"], up.get("_det_row") or {})


def _apply_sqlite(conn: sqlite3.Connection, plan: dict[str, Any]) -> None:
    cur = conn.cursor()
    cur.execute("BEGIN IMMEDIATE")
    removed = sorted(set(plan["merge_map"]) | set(plan["hard_deletes"]))

    for item in plan["itinerary_updates"]:
        cur.execute("UPDATE itineraries SET stops = ? WHERE id = ?", (json.dumps(item["stops"], ensure_ascii=False), item["id"]))
    for eid, up in plan["entity_updates"].items():
        _write_entity_update(conn, False, eid, up, plan["entities_state"][eid])

    cur.execute("DELETE FROM relationships")
    cur.executemany("INSERT OR IGNORE INTO relationships (from_id, to_id, type) VALUES (?, ?, ?)", plan["remapped_rels"])
    if removed:
        for eid in removed:
            delete_entity_details(conn, False, eid)
        ph = ",".join("?" for _ in removed)
        for tbl in ("image_suggestions", "entity_snapshot_generation", "entity_changes"):
            cur.execute(f"DELETE FROM {tbl} WHERE entity_id IN ({ph})", removed)
        cur.execute(f"DELETE FROM reports WHERE target_type = 'entity' AND target_id IN ({ph})", removed)
        cur.execute(f"DELETE FROM entities WHERE id IN ({ph})", removed)

    cur.execute("INSERT INTO entities_fts(entities_fts) VALUES('rebuild')")
    conn.commit()
    conn.execute("VACUUM")


def _remap_pg_refs(cur: Any, merge_map: dict[str, str]) -> None:
    for src, dst in merge_map.items():
        cur.execute("UPDATE posts SET entity_id = %s WHERE entity_id = %s", (dst, src))
        cur.execute("UPDATE correction_items SET entity_id = %s WHERE entity_id = %s", (dst, src))
        cur.execute("UPDATE follows SET target_id = %s WHERE target_type = 'entity' AND target_id = %s", (dst, src))
        cur.execute("UPDATE featured_entities SET entity_id = %s WHERE entity_id = %s", (dst, src))
        for tbl in ("user_visits", "saved_entities", "event_rsvp"):
            cur.execute(
                f"DELETE FROM {tbl} a WHERE entity_id = %s AND EXISTS "
                f"(SELECT 1 FROM {tbl} b WHERE b.user_id = a.user_id AND b.entity_id = %s)",
                (src, dst),
            )
            cur.execute(f"UPDATE {tbl} SET entity_id = %s WHERE entity_id = %s", (dst, src))
        cur.execute(
            "DELETE FROM entity_ratings WHERE entity_id = %s AND EXISTS "
            "(SELECT 1 FROM entity_ratings b WHERE b.entity_id = %s)",
            (src, dst),
        )
        cur.execute("UPDATE entity_ratings SET entity_id = %s WHERE entity_id = %s", (dst, src))


def _apply_postgres(conn: Any, plan: dict[str, Any]) -> None:
    import psycopg2.extras  # type: ignore

    cur = conn.cursor()
    for item in plan["itinerary_updates"]:
        cur.execute("UPDATE itineraries SET stops = %s WHERE id = %s", (psycopg2.extras.Json(item["stops"]), item["id"]))
    for eid, up in plan["entity_updates"].items():
        _write_entity_update(conn, True, eid, up, plan["entities_state"][eid])

    cur.execute("DELETE FROM relationships")
    if plan["remapped_rels"]:
        psycopg2.extras.execute_values(
            cur, "INSERT INTO relationships (from_id, to_id, type) VALUES %s ON CONFLICT DO NOTHING", plan["remapped_rels"], page_size=500
        )

    _remap_pg_refs(cur, plan["merge_map"])
    removed = sorted(set(plan["merge_map"]) | set(plan["hard_deletes"]))
    if removed:
        for tbl in (
            "user_visits", "saved_entities", "event_rsvp", "featured_entities",
            "user_personalization_events", "correction_items", "entity_claims",
            "entity_snapshot_generation", "entity_changes", "entity_ratings", *DETAIL_TABLES,
        ):
            cur.execute(f"DELETE FROM {tbl} WHERE entity_id = ANY(%s)", (removed,))
        cur.execute("DELETE FROM follows WHERE target_type = 'entity' AND target_id = ANY(%s)", (removed,))
        cur.execute("DELETE FROM reports WHERE target_type = 'entity' AND target_id = ANY(%s)", (removed,))
        cur.execute("UPDATE posts SET entity_id = NULL WHERE entity_id = ANY(%s)", (removed,))
        cur.execute("DELETE FROM entities WHERE id = ANY(%s)", (removed,))
    conn.commit()


def _write_report(
    report_out: Path | None,
    plan: dict[str, Any],
    *,
    apply_changes: bool,
    is_pg: bool,
) -> None:
    if report_out is None:
        return
    updates = plan["entity_updates"]
    out = {
        "mode": "apply" if apply_changes else "dry-run",
        "backend": "postgres" if is_pg else "sqlite",
        "counts": plan["counts"],
        "hard_deletes": plan["hard_deletes"],
        "merge_map": plan["merge_map"],
        "place_fixes": {k: v for k, v in WAVE8_PLACE_FIXES.items() if k in updates},
        "type_fixes": {k: v for k, v in WAVE8_TYPE_FIXES.items() if k in updates},
        "ward_coord_fixes": sorted(k for k in WAVE8_WARD_COORD_FIXES if k in updates),
        "address_fixes": sorted(k for k, u in updates.items() if "address" in u),
        "description_fixes": sorted(k for k, u in updates.items() if "description" in u),
        "cti_coercion_fixes": sorted(k for k in WAVE8_ATTR_COERCION_FIXES if k in updates),
        "coord_snapped": sorted(k for k, u in updates.items() if "coordinates" in u and k not in WAVE8_WARD_COORD_FIXES),
    }
    report_out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    src_group = ap.add_mutually_exclusive_group(required=True)
    src_group.add_argument("--sqlite", type=Path)
    src_group.add_argument("--postgres-env", action="store_true")
    mode_group = ap.add_mutually_exclusive_group()
    mode_group.add_argument("--dry-run", action="store_true")
    mode_group.add_argument("--apply", action="store_true")
    ap.add_argument("--redirects-file", type=Path)
    ap.add_argument("--report-out", type=Path)
    args = ap.parse_args(argv)
    apply_changes = bool(args.apply)

    conn, cur, is_pg = _open_conn(args)
    try:
        entities, rels, itineraries = _load_snapshot(cur, is_pg=is_pg)
        plan = _build_plan(entities, rels, itineraries, args.redirects_file)
        if apply_changes:
            (_apply_postgres if is_pg else _apply_sqlite)(conn, plan)
        else:
            conn.rollback()
        if args.redirects_file is not None and apply_changes:
            args.redirects_file.write_text(json.dumps(plan["redirects"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        _write_report(args.report_out, plan, apply_changes=apply_changes, is_pg=is_pg)
        print(f"[{'APPLIED' if apply_changes else 'DRY-RUN'}][{'postgres' if is_pg else 'sqlite'}] {json.dumps(plan['counts'], ensure_ascii=False)}")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
