#!/usr/bin/env python3
"""Wave 7 deterministic data polish, shadow-duplicate merges & deep catalog pruning.

Supports both local SQLite (`--sqlite`) and VPS PostgreSQL (`--postgres-env`).
Applies:
- Nhóm A1: clear copied/placeholder phone numbers across columns, JSONB & CTI
- Nhóm A2: rewrite 34 malformed / raw-scraped / truncated / outdated summaries
- Nhóm A3: fix 5 mismatched placeIds (+ clean address) & snap old-city centroid coords
- Nhóm B: consolidate 14 shadow-duplicate entities with flattened 301 redirects
- Nhóm C: hard-delete 64 generic/low-value entities while preserving 124/124 wards
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sqlite3
import sys
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
FAKE_PHONE_DIGITS: frozenset[str] = frozenset({
    "02703822188",
    "02703823456",
    "02703771188",
    "02943889122",
})

# Nhóm C: Deep pruning of generic / low-value entities (64).
WAVE7_HARD_DELETES: tuple[str, ...] = (
    # Generic district & wholesale markets (10)
    "cho-ba-tri",
    "cho-ba-vat",
    "cho-binh-dai",
    "cho-giong-trom",
    "cho-mo-cay",
    "cho-tan-quoi",
    "cho-tan-thanh",
    "cho-thanh-phu",
    "cho-dau-moi-nong-thuy-san-ben-tre",
    "cho-cau-ke",
    # Small canals / rivers without unique cultural highlight (6; keep song-ba-lai-ben-tre for xa-chau-hung)
    "rach-cau-lau-vinh-long",
    "rach-cai-ca-vinh-long",
    "rach-tra-ngoa-vinh-long",
    "rach-gam-ben-tre",
    "kenh-bong-bot-tra-vinh",
    "kenh-thay-cai-vinh-long",
    # Generic nationwide dishes (9)
    "bo-nuong-la-lot",
    "goi-cuon-tom-thit",
    "cha-gio-chay",
    "tom-rang-muoi-ot",
    "ca-keo-kho-to",
    "chao-ca-loc-rau-dang",
    "bo-to-vinh-long",
    "banh-phu-the-vinh-long",
    "nem-nuong-vinh-long",
    # Out-of-province / generic / skeleton restaurants (12)
    "hu-tieu-my-tho-anh-tuan-ben-tre",
    "hu-tieu-sa-dec-chu-tu-gan-cho-phu-hung-ben-tre",
    "quan-pho-sang-duong-tran-quoc-tuan-ben-tre",
    "bun-bo-co-tam-cho-ben-tre-ben-tre",
    "chao-ech-tran-nam",
    "com-nieu-nam-bo",
    "quan-lau-mam-mien-tay-cho-tieu-can-tra-vinh",
    "quan-chao-ca-ro-dong-cho-cau-ke-tra-vinh",
    "nha-hang-ngan-vinh",
    "quan-chay-an-lac-vinh-long",
    "com-ga-xoi-mo-5-vi-ben-tre",
    "banh-flan-14",
    # Micro-OCOP single household products (17)
    "cu-cai-non-muoi-chua-bui-thi-thanh-thao-ocop",
    "bun-tuoi-an-dao",
    "keo-dau-phong-du-tan-loi",
    "rau-cau-vinh-quang",
    "rau-thom-ocop-hop-tac-xa-phuoc-hau",
    "dong-trung-ha-thao-say-thang-hoa-drc",
    "banh-kep-thuy-kieu",
    "mam-tep-du-du-thuy-nguyen",
    "tom-kho-hai-kham",
    "lap-xuong-co-ba-loan",
    "lap-xuong-hiep-ky",
    "ruou-gia-bao",
    "dua-troc-le-phuong",
    "thanh-long-vang-thanh-duc-ocop-3-sao",
    "vu-sua-hoang-kim-thanh-binh-ocop",
    "dua-hau-tan-hung-ocop",
    "man-an-phuoc-ocop",
    # Plain 2-star roadside hotels (10)
    "khach-san-binh-dai",
    "khach-san-binh-minh",
    "khach-san-dong-quan",
    "khach-san-hoan-my-2",
    "khach-san-hoang-hao",
    "khach-san-khoi-hoa",
    "khach-san-minh-khue",
    "khach-san-ngoc-hung",
    "khach-san-phuong-thao",
    "khach-san-xuan-huong",
)

# Nhóm B: Shadow-duplicate consolidation (dst -> [src...], 14 merges).
WAVE7_MERGES_BY_DST: dict[str, list[str]] = {
    "cho-noi-tra-on": ["cho-noi-tra-on-dc"],
    "vung-cam-sanh-tra-on": ["htx-cam-sanh-tra-on"],
    "keo-dua-ben-tre": ["keo-dua-mo-cay-dish"],
    "cu-lao-dai": ["vuon-trai-cay-cu-lao-dai"],
    "cua-song-cung-hau-ca-heo-cau-ngang-tra-vinh": ["cua-cung-hau-tra-vinh"],
    "khu-du-lich-sinh-thai-nguoi-giu-rung": ["homestay-nguoi-giu-rung"],
    "con-chim": ["con-chim-homestay"],
    "dua-sap-cau-ke": ["vung-trong-dua-sap-cau-ke"],
    "banh-phong-son-doc": ["banh-phong-mi-giong-trom"],
    "lang-banh-trang-my-long": ["banh-trang-my-long"],
    "banh-canh-ben-co": ["quan-banh-canh-ben-co-tra-vinh"],
    "vuon-trai-cay-6-tan": [
        "vuon-trai-cay-be-sau",
        "vuon-trai-cay-bi-bo",
        "vuon-trai-cay-tam-loc",
    ],
}

# Nhóm A3: Explicit placeId & clean address fixes (5 entities).
WAVE7_PLACE_FIXES: dict[str, str] = {
    "khoai-lang-say-binh-tan": "p-tan-quoi",
    "khoai-lang-say-dong-phat": "p-tan-quoi",
    "chua-khmer-phu-ly": "p-dong-thanh",
    "dinh-lang-thien-my": "p-tra-on",
    "phan-thanh-gian": "xa-bao-thanh",
}

WAVE7_ADDRESS_FIXES: dict[str, str] = {
    "khoai-lang-say-binh-tan": "Khoai lang sấy Bình Tân, Phường Tân Quới, tỉnh Vĩnh Long",
    "khoai-lang-say-dong-phat": "Khoai lang sấy Đông Phát, Phường Tân Quới, tỉnh Vĩnh Long",
    "chua-khmer-phu-ly": "Phường Đông Thành, tỉnh Vĩnh Long",
    "dinh-lang-thien-my": "Đình làng Thiện Mỹ, Phường Trà Ôn, tỉnh Vĩnh Long",
}

# Nhóm A2: Malformed / raw-scraped / truncated / outdated summaries (34 entities).
WAVE7_SUMMARY_FIXES: dict[str, str] = {
    "cua-dai-cua-song-my-thosong-tien-ben-tre": (
        "Cửa biển dài khoảng 6 km ở phía bắc tỉnh Vĩnh Long, nơi sông Tiền đổ ra Biển Đông. "
        "Vùng cửa sông ngập mặn rộng lớn này là bãi đẻ tự nhiên của nhiều loài thủy sản và điểm xuất phát các tuyến tham quan ven biển, "
        "nổi bật với góc nhìn tàu thuyền ra vào từ mũi Cửa Đại."
    ),
    "song-hau-doan-cua-dinh-an-tra-vinh": (
        "Cửa biển lớn dài khoảng 25 km nơi sông Hậu đổ ra Biển Đông, từng là tuyến đường thủy xuất khẩu gạo sầm uất từ thời Pháp thuộc. "
        "Hệ sinh thái cửa sông bồi tụ bãi đẻ cho cá tôm, với điểm ngắm cảnh tiêu biểu tại mũi Cồn Cát ven vùng ngập mặn."
    ),
    "den-tho-trung-tuong-dong-van-cong": (
        "Đền thờ tưởng niệm Trung tướng Đồng Văn Cống (1918–2005), vị chỉ huy gắn bó với chiến khu bưng biền Nam Bộ. "
        "Là di tích lịch sử văn hóa địa phương tại xã Tân Hào, công trình mang kiến trúc nhà làng Nam Bộ trang nghiêm và gần gũi."
    ),
    "song-long-ho-vinh-long": (
        "Dòng sông dài khoảng 28 km chảy qua khu vực Long Hồ và tiếp giáp trung tâm Vĩnh Long, "
        "gắn liền với tên gọi Long Hồ Dinh – thủ phủ hành chính đàng Trong thế kỷ 18. "
        "Trục giao thông thủy này kết nối các xã cù lao vườn cây ăn trái, đẹp nhất khi nhìn từ bến đò Long Hồ."
    ),
    "song-ham-luong-ben-tre": (
        "Một trong bốn nhánh lớn của sông Cửu Long dài khoảng 70 km, phân chia cù lao Bảo và cù lao Minh giữa những rặng dừa bạt ngàn. "
        "Tuyến sông gắn liền với lịch sử Đồng Khởi và giao thương miệt vườn, có tầm nhìn khoáng đạt từ cầu Hàm Luông."
    ),
    "song-ba-lai-ben-tre": (
        "Nhánh sông cổ dài khoảng 55 km của hệ thống sông Tiền, nay được điều tiết bởi cống đập Ba Lai hoàn thành năm 2002 để ngăn mặn giữ ngọt. "
        "Thượng lưu đập trở thành hồ trữ nước ngọt lớn phục vụ sinh hoạt và vườn cây, đồng thời là điểm tham quan công trình thủy lợi tiêu biểu."
    ),
    "song-thom-rach-thom-ben-tre": (
        "Tuyến thủy nội địa dài khoảng 22 km chảy qua vùng vườn dừa lâu năm của Mỏ Cày Bắc và Mỏ Cày Nam. "
        "Hai bên bờ rạch quy tụ nhiều hộ làm kẹo dừa và chỉ xơ dừa truyền thống, tạo nên khung cảnh làng nghề sông nước sống động."
    ),
    "hu-tieu-chu-hien-ben-tre": (
        "Quán hủ tiếu sáng quen thuộc gần khu vực chợ trên đường Nguyễn Đình Chiểu, phường Phú Khương. "
        "Quán phục vụ hủ tiếu đặc biệt đầy đủ thịt, topping và trứng cút với nước dùng ninh từ xương heo trong vắt, ngọt thanh tự nhiên."
    ),
    "nha-hang-phuong-thuy": (
        "Nhà hàng tại số 2 Phan Bội Châu, phường Long Châu, tỉnh Vĩnh Long, "
        "phục vụ ẩm thực truyền thống Nam Bộ và tiếp đón khách đoàn, tiệc gia đình ngay trung tâm đô thị ven sông."
    ),
    "hu-tieu-nam-vang-ba-nam-ben-tre": (
        "Quán ăn sáng trên đường Nguyễn Thị Định, phường Phú Khương, chuyên hủ tiếu Nam Vang khô dùng kèm chén nước súp riêng. "
        "Nước dùng ninh từ xương heo và tôm khô tạo vị ngọt thanh đậm đà theo khẩu vị Nam Bộ."
    ),
    "nha-hang-hai-san-song-tien-vinh-long": (
        "Nhà hàng ven bờ sông Tiền gần khu vực phà Đình Khao, phường Long Châu, có không gian thoáng rộng hướng sông và bãi đậu xe thuận tiện. "
        "Thực đơn nổi bật với hải sản, thủy sản tươi sống như cá lóc nướng trui cuốn bánh tráng, cá trê và lẩu tôm càng xanh (tham khảo từ 150.000đ/người)."
    ),
    "banh-canh-cho-ben-tre-hang-goc-cho-ben-tre-ben-tre": (
        "Hàng bánh canh lâu năm ngay góc cổng chợ trên đường Nguyễn Đình Chiểu, phường Phú Khương, bán buổi sáng cho người dân địa phương. "
        "Bánh canh sợi tươi mềm dai chan nước lèo xương hầm ngọt dịu ăn cùng giò heo béo mềm, giá tham khảo khoảng 25.000–35.000đ/tô."
    ),
    "bun-thit-nuong-co-hanh-ben-tre": (
        "Quán bún thịt nướng bình dân trên đường Đồng Khởi, phường Phú Khương, phục vụ từ trưa đến tối. "
        "Bún thịt nướng than hoa ăn cùng bì, chả giò giòn và nước mắm chua ngọt pha theo khẩu vị Nam Bộ, giá tham khảo khoảng 25.000–30.000đ/phần."
    ),
    "che-ba-cam-khu-vuc-cho-ben-tre-ben-tre": (
        "Gánh chè truyền thống gần cổng sau khu vực chợ tại phường Phú Khương, mở bán từ trưa đến tối. "
        "Thực đơn gồm chè thập cẩm, chè đậu xanh nước dừa và chè bắp nấu từ nước cốt dừa tươi béo thơm, giá tham khảo khoảng 10.000–20.000đ/ly."
    ),
    "banh-xeo-muoi-xinh-ben-tre": (
        "Quán bánh xèo buổi chiều tối trên đường Nguyễn Thị Định, phường Phú Khương, chuyên bánh xèo nhân tôm thịt và mực tươi. "
        "Bánh đổ chảo lớn giòn rụm, nhân tôm sú ngọt thịt, dọn kèm rổ rau vườn nhà, giá tham khảo khoảng 20.000–30.000đ/cái."
    ),
    "chao-long-ba-nam-cho-phuong-4-ben-tre": (
        "Quán cháo sáng quen thuộc tại khu vực chợ ở phường Phú Khương, chuyên cháo lòng heo tươi làm sạch trong ngày. "
        "Cháo nấu sánh vừa, lòng giòn không tanh, phục vụ sớm cho người đi chợ với giá tham khảo khoảng 20.000–30.000đ/tô."
    ),
    "goi-cuon-tom-thit-ba-hai-chau-thanh-ben-tre": (
        "Quán ăn vặt bình dân chuyên gỏi cuốn tôm thịt và cuốn diếp cá tại khu vực Châu Thành, mở bán từ sáng đến chiều. "
        "Tôm luộc tươi ngọt, cuốn chắc tay, chấm tương đen đậu phộng giã thô béo bùi, giá tham khảo khoảng 5.000–7.000đ/cuốn."
    ),
    "hang-banh-uot-co-lan-cho-ba-tri-ben-tre": (
        "Hàng điểm tâm sáng bên trong khu vực chợ Ba Tri, chuyên bánh ướt lòng gà và bánh ướt cuốn ăn gọn nhẹ. "
        "Bánh tráng mỏng mềm mướt kết hợp lòng gà xào sả ớt thơm cay và hành phi giòn, giá tham khảo khoảng 20.000–30.000đ/phần."
    ),
    "vuon-am-thuc-truc-giang-ben-tre": (
        "Quán ăn sân vườn tại 76A Võ Nguyên Giáp, phường Phú Khương với không gian chòi lá thoáng mát nhiều cây xanh. "
        "Chuyên các món ếch đồng theo mùa, đặc biệt là lẩu ếch nấu nước dừa béo thanh, giá tham khảo khoảng 150.000–350.000đ/người."
    ),
    "vuon-am-thuc-mai-an-tiem-ben-tre": (
        "Quán ẩm thực sân vườn tại 108E An Thuận B, phường Phú Khương với khuôn viên rộng rợp bóng cây phù hợp tiệc gia đình. "
        "Thực đơn thiên về đặc sản đồng quê và thủy sản như cá lóc nướng trui cuốn rau rừng, ếch um dừa, giá tham khảo từ 150.000đ/người."
    ),
    "bun-suong-ut-tam-tra-vinh": (
        "Quán bún suông sáng lâu năm tại 28 Nguyễn Thị Minh Khai, phường Trà Vinh, thường hết khách trước trưa. "
        "Chả tôm quết thành con suông dai ngọt hòa cùng nước lèo chua thanh đậm vị me và tương xay, giá tham khảo khoảng 25.000–40.000đ/tô."
    ),
    "quan-bun-nuoc-leo-duong-dong-khoi-tra-vinh": (
        "Quán bún nước lèo bán chuyên buổi xế chiều tại 94A Đồng Khởi, phường Trà Vinh, rất đông khách địa phương. "
        "Nước dùng mắm bò hóc hầm kỹ cho vị sâu đậm đà, ăn kèm cá lóc đồng và thịt heo quay giòn, giá tham khảo khoảng 25.000–40.000đ/tô."
    ),
    "quan-di-bay-com-nieu-tra-vinh": (
        "Quán cơm niêu phong cách sân vườn gần khu du lịch Long Đức, phường Long Đức, chuyên bữa cơm gia đình Nam Bộ. "
        "Nổi bật với cơm niêu đất nung giòn đáy ăn cùng kho quẹt, mắm chưng và rau đồng, giá tham khảo khoảng 50.000–100.000đ."
    ),
    "mieu-ba-chua-xu-vinh-long-vinh-long": (
        "Ngôi miếu tín ngưỡng dân gian hình thành từ thế kỷ 19 thờ Bà Chúa Xứ và Ngũ Hành Nương Nương theo kiến trúc Nam Bộ cổ truyền. "
        "Mái cong lợp ngói ống đắp nổi rồng phượng trang nghiêm, hằng năm tổ chức lễ Vía Bà dịp 23–27/4 âm lịch với múa bóng rỗi và thả hoa đăng."
    ),
    "nha-tho-chanh-toa-ben-tre-ben-tre": (
        "Ngôi thánh đường Công giáo xây dựng từ năm 1928 tại phường An Hội, mang kiến trúc Gothic kết hợp hài hòa nét nhiệt đới. "
        "Tháp chuông cao, hệ cửa kính màu nghệ thuật và không gian nội thất rộng thoáng tạo nên điểm nhấn di sản giữa lòng đô thị."
    ),
    "thanh-that-cao-dai-ben-tre-ben-tre": (
        "Thánh thất đạo Cao Đài dựng từ thập niên 1930 tại phường Phú Khương, nổi bật với kiến trúc nền trắng, cột tròn vàng xanh và biểu tượng Thiên Nhãn. "
        "Công trình chạm trổ hoa văn tứ linh Long – Lân – Quy – Phụng công phu, thu hút tín đồ hành lễ và du khách dịp Vía Đức Cao Đài, Hội Yến Diêu Trì."
    ),
    "chua-long-thanh-ben-tre": (
        "Ngôi cổ tự Phật giáo hình thành từ thế kỷ 19 gắn với vùng Giồng Trôm xưa, nổi bật với tôn tượng Phật Di Lặc ngoài trời kích thước lớn. "
        "Khuôn viên chùa rợp bóng cây xanh, có ao sen và tháp thờ truyền thống thanh tịnh, đón đông đảo phật tử vào dịp Phật Đản và Vu Lan."
    ),
    "mieu-ba-chua-xu-my-hoa-ben-tre": (
        "Ngôi miếu dân gian cổ từ thế kỷ 19 tại khu vực Mỹ Hóa, phường Phú Khương, lưu giữ nét kiến trúc thờ Mẫu truyền thống Nam Bộ. "
        "Mái đao cong, tường vàng đắp nổi rồng phượng cùng khoảng sân rộng nơi diễn ra lễ Vía Bà Chúa Xứ hằng năm vào 23–27/4 âm lịch."
    ),
    "lang-keo-dua-mo-cay": (
        "Cái nôi của nghề làm kẹo dừa thủ công truyền thống tại Mỏ Cày, gắn liền với quy trình nấu nước cốt dừa cùng mạch nha trên bếp lửa. "
        "Du khách có thể tham quan xưởng nấu kẹo, tận mắt xem công đoạn cán cắt gói lá dừa thủ công và thưởng thức mẻ kẹo nóng vừa ra lò."
    ),
    "am-thuc-ngo-dong-ben-tre": (
        "Nhà hàng ẩm thực sân vườn kết hợp chòi thủy tạ tại 165B Đồng Khởi, phường Bến Tre với không gian đồng quê thoáng đãng. "
        "Thực đơn chuyên các món đặc sản như heo rừng quay da giòn chấm mắm me, heo rừng nướng sả và gà trống thiến, giá tham khảo từ 200.000đ/người."
    ),
    "quan-com-chay-lac-vien-vinh-long": (
        "Quán cơm chay bình dân tại số 3 Phạm Hùng, phường Long Châu, tỉnh Vĩnh Long, mở cửa phục vụ từ sáng đến tối. "
        "Quán chuyên các món cơm chay phần đậm vị Nam Bộ như canh chua chay, cá kho tộ chay với giá tham khảo từ 25.000–60.000đ."
    ),
    "song-lang-the-tra-vinh": (
        "Dòng sông nội địa dài khoảng 30 km kết nối trung tâm Trà Vinh với vùng Châu Thành, đôi bờ rợp bóng vườn dừa và nhiều phum sóc Khmer cổ. "
        "Trước khi có mạng lưới đường bộ, đây là trục giao thương thủy chủ lực, nay vẫn lưu giữ cảnh sắc thuyền gỗ mộc mạc qua đoạn xã Nhị Long."
    ),
    "nem-nuong-thanh-binh-ben-tre": (
        "Quán nem nướng lâu năm gần khu vực bến phà Hàm Luông cũ, phường An Hội, chuyên nem nướng than hồng và nem lụi cuốn bánh tráng. "
        "Thịt nem thơm mùi khói than, cuốn bánh tráng mỏng cùng đồ chua và đậu phộng rang béo bùi, giá tham khảo khoảng 30.000–50.000đ/phần."
    ),
    "chua-quan-am-phuong-8": (
        "Ngôi chùa Phật giáo tại 168 Nguyễn Văn Lâu, khóm 5, phường Tân Hạnh, tỉnh Vĩnh Long, "
        "nổi bật với công trình tôn tượng Quán Thế Âm Bồ Tát lộ thiên quy mô lớn đang được kiến tạo, là điểm chiêm bái thanh tịnh của phật tử địa phương."
    ),
}


def _non_empty(val: Any) -> bool:
    return bool(val.strip()) if isinstance(val, str) else bool(val)


def _digits_only(val: Any) -> str:
    return "".join(ch for ch in str(val or "") if ch.isdigit())


def _is_fake_phone(val: Any) -> bool:
    return _digits_only(val) in FAKE_PHONE_DIGITS


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
        'id, type, name, summary, "placeId", coordinates, address, phone, website, hours, '
        'price_range, sub_category, best_time, highlight, attributes'
        if is_pg
        else "id, type, name, summary, placeId, coordinates, address, phone, website, hours, "
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
        for dst, srcs in WAVE7_MERGES_BY_DST.items()
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
            if field == "phone" and _is_fake_phone(src_val):
                continue
            if not _non_empty(cur_val) and _non_empty(src_val):
                cleaned = str(src_val).strip()
                entities[dst]["attrs"][field] = cleaned
                entities[dst][field] = cleaned
                up = updates.setdefault(dst, {})
                up[field] = cleaned
                up["save_attrs"] = True
                up["sync_cti"] = True


def _clear_fake_phones(
    entities: dict[str, dict[str, Any]], updates: dict[str, dict[str, Any]], removed: set[str]
) -> int:
    cleared = 0
    for eid, row in entities.items():
        if eid in removed:
            continue
        col_fake = _is_fake_phone(row.get("phone"))
        attr_fake = _is_fake_phone(row["attrs"].get("phone"))
        if not (col_fake or attr_fake):
            continue
        cleared += 1
        row["phone"] = None
        row["attrs"].pop("phone", None)
        up = updates.setdefault(eid, {})
        up["phone"] = None
        up["save_attrs"] = True
        up["sync_cti"] = True
    return cleared


def _apply_scalar_map(
    entities: dict[str, dict[str, Any]],
    updates: dict[str, dict[str, Any]],
    removed: set[str],
    field: str,
    mapping: dict[str, str],
) -> None:
    for eid, new_val in mapping.items():
        if eid in entities and eid not in removed and entities[eid].get(field) != new_val:
            entities[eid][field] = new_val
            updates.setdefault(eid, {})[field] = new_val


def _apply_address_fixes(
    entities: dict[str, dict[str, Any]], updates: dict[str, dict[str, Any]], removed: set[str]
) -> None:
    for eid, new_addr in WAVE7_ADDRESS_FIXES.items():
        if eid not in entities or eid in removed:
            continue
        row = entities[eid]
        if row.get("address") == new_addr and row["attrs"].get("address") == new_addr:
            continue
        row["address"] = new_addr
        up = updates.setdefault(eid, {})
        up["address"] = new_addr
        if "address" in row["attrs"]:
            row["attrs"]["address"] = new_addr
            up["save_attrs"] = True
        up["sync_cti"] = True


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
        if _near_old_city(cur_pt) and _dist_km(cur_pt, ward_pt) > 20.0:
            row["coords_pair"] = list(ward_pt)
            updates.setdefault(eid, {})["coordinates"] = list(ward_pt)
            snapped += 1
    return snapped


def _validate_cti_updates(entities: dict[str, dict[str, Any]], updates: dict[str, dict[str, Any]]) -> None:
    for eid, up in updates.items():
        if not up.get("sync_cti"):
            continue
        row = entities[eid]
        effective = {c: row[c] for c in UNIVERSAL if _non_empty(row.get(c))}
        effective.update(row["attrs"])
        if "phone" in up and up["phone"] is None:
            effective.pop("phone", None)
        uni, det, _skipped = split_typed(row["type"], effective)
        up["_uni_cols"] = {k: v for k, v in uni.items() if row.get(k) != v}
        up["_det_row"] = det


def _apply_entity_updates(
    entities: dict[str, dict[str, Any]],
    merge_map: dict[str, str],
    transfers: dict[str, str],
    removed: set[str],
) -> tuple[dict[str, dict[str, Any]], int, int]:
    updates: dict[str, dict[str, Any]] = {}
    for dst, pid in transfers.items():
        if entities[dst].get("placeId") != pid:
            entities[dst]["placeId"] = pid
            updates[dst] = {"placeId": pid}
    _apply_merge_utilities(entities, updates, merge_map)
    fake_phones_cleared = _clear_fake_phones(entities, updates, removed)
    _apply_scalar_map(entities, updates, removed, "placeId", WAVE7_PLACE_FIXES)
    _apply_address_fixes(entities, updates, removed)
    _apply_scalar_map(entities, updates, removed, "summary", WAVE7_SUMMARY_FIXES)
    coord_snaps = _apply_centroid_coord_snaps(entities, updates, removed)
    _validate_cti_updates(entities, updates)
    return updates, fake_phones_cleared, coord_snaps


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
    hard_set = {eid for eid in WAVE7_HARD_DELETES if eid in entities and eid not in places}
    merge_map, transfers, exempted = _compute_merges(entities, ward_members, covered_wards, hard_set)
    assert not exempted, f"Exempted guardrails triggered: {exempted}"

    removed = hard_set | set(merge_map)
    surviving_ids = set(entities) - removed
    updates, fake_phones_cleared, coord_snaps = _apply_entity_updates(entities, merge_map, transfers, removed)
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
            "fake_phones_cleared": fake_phones_cleared,
            "summary_fixes": sum(1 for u in updates.values() if "summary" in u),
            "place_fixes": sum(1 for u in updates.values() if "placeId" in u),
            "address_fixes": sum(1 for u in updates.values() if "address" in u),
            "coord_snaps": coord_snaps,
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
    scalar_fields = ("type", "name", "summary", "placeId", "address", "phone", "website", "hours")
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
        "place_fixes": {k: v for k, v in WAVE7_PLACE_FIXES.items() if k in updates},
        "address_fixes": sorted(k for k in WAVE7_ADDRESS_FIXES if k in updates),
        "summary_fixes": sorted(k for k in WAVE7_SUMMARY_FIXES if k in updates),
        "fake_phones_cleared": sorted(k for k, u in updates.items() if u.get("phone") is None and "phone" in u),
        "coord_snapped": sorted(k for k, u in updates.items() if "coordinates" in u),
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
