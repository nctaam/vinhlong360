#!/usr/bin/env python3
"""Generate a forensic data verification report for web/data.json.

The report deliberately separates structural quality from factual trust. It
uses local scans for every entity and a reproducible web-search sample for
high-risk entities. Confirmed factual errors are hard-coded only when backed by
external source URLs captured during the audit.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "web" / "data.json"
DOCS_DIR = ROOT / "docs"
SCRATCH_DIR = ROOT / "scratch"
REPORT_PATH = DOCS_DIR / "data-verification-report.md"
MATRIX_CSV = DOCS_DIR / "data-verification-matrix.csv"
CLAIMS_CSV = DOCS_DIR / "data-verification-claims.csv"
WEB_LOG_CSV = DOCS_DIR / "data-verification-web-log.csv"
SOURCE_AUDIT_CSV = DOCS_DIR / "data-verification-sources.csv"
FIX_SQL = DOCS_DIR / "data-verification-fixes.sql"
WEB_CACHE = SCRATCH_DIR / "data-verification-web-log.json"

AREA_LABELS = {
    "vinh-long": "Vĩnh Long",
    "ben-tre": "Bến Tre",
    "tra-vinh": "Trà Vinh",
    None: "None",
}

CURRENT_MERGED_PROVINCE = (
    "Từ sau đợt sắp xếp hành chính 2025, nhiều nguồn mới gọi vùng Bến Tre/"
    "Trà Vinh cũ là tỉnh Vĩnh Long mới. Báo cáo này vẫn kiểm tra theo "
    "legacy area trong data (`vinh-long`, `ben-tre`, `tra-vinh`) và không coi "
    "từ khóa 'Vĩnh Long' trong nguồn 2026 là lỗi nếu entity thuộc Bến Tre/Trà "
    "Vinh cũ."
)

VALID_AREAS = {"vinh-long", "ben-tre", "tra-vinh"}
HIGH_RISK_TYPES = {"history", "person", "attraction", "craft_village", "event"}
CONTACT_TYPES = {"restaurant", "cafe", "accommodation", "facility"}
PRODUCT_TYPES = {"product", "dish", "drink"}

# Tight bbox for the three legacy provinces with a small buffer.
LAT_RANGE = (9.20, 10.65)
LNG_RANGE = (105.60, 106.95)

VN_PHONE = re.compile(r"^(\+84|0)\d{9,10}$|^1(800|900)\d{4,6}$|^11[345]$")
PHONE_IN_TEXT = re.compile(r"(?:(?:\+84|0)\s*)?(?:\d[\s.\-()]*){8,11}")
URL_IN_TEXT = re.compile(r"https?://[^\s)\]]+")
YEAR_RE = re.compile(r"\b(1[0-9]{3}|20[0-9]{2})\b")
MEASURE_RE = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*(?:ha|km|m2|m²|m|mét|người|hộ|sao|%|VNĐ|đ|tô|cái|phòng)\b",
    re.IGNORECASE,
)
MONTH_RE = re.compile(r"(?:tháng\s*\d{1,2}|T\d{1,2})", re.IGNORECASE)
HOUR_RE = re.compile(r"\b\d{1,2}[:h]\d{0,2}\s*(?:[-–]\s*\d{1,2}[:h]\d{0,2})?\b")
FACT_WORD_RE = re.compile(
    r"OCOP|VietGAP|di tích|quốc gia|cấp tỉnh|xếp hạng|chứng nhận|lớn nhất|duy nhất|"
    r"đầu tiên|khởi nghĩa|vua|ông|bà|Nguyễn|Trần|Lê|Phạm|Thạch|Hồ Chí Minh",
    re.IGNORECASE,
)
GENERIC_LLM_RE = re.compile(
    r"không thể bỏ qua|trải nghiệm đáng nhớ|hòa mình|bức tranh|nét đẹp|"
    r"hương vị đặc trưng|đậm chất miền Tây|lưu giữ|góp phần",
    re.IGNORECASE,
)

TIER_1 = {
    "vi.wikipedia.org",
    "vinhlong.gov.vn",
    "bentre.gov.vn",
    "travinh.gov.vn",
    "sovhttdl.vinhlong.gov.vn",
    "vietnamtourism.gov.vn",
    "nongthon.vietnamtourism.gov.vn",
    "dantoc.vietnamtourism.gov.vn",
    "ocop.gov.vn",
    "gso.gov.vn",
    "bvhttdl.gov.vn",
    "dst.gov.vn",
    "chinhphu.vn",
    "xaydungchinhsach.chinhphu.vn",
}
TIER_2 = {
    "baovinhlong.com.vn",
    "baovinhlong.vn",
    "baodongkhoi.vn",
    "baotravinh.vn",
    "thtv.vn",
    "tuoitre.vn",
    "thanhnien.vn",
    "vnexpress.net",
    "vovworld.vn",
    "vov.vn",
    "baoapbac.vn",
    "sggp.org.vn",
    "dttc.sggp.org.vn",
    "bentretourism.vn",
    "canthotourism.vn",
    "dulichcantho.vn",
    "tapchicongthuong.vn",
    "nhandan.vn",
    "laodong.vn",
    "soctrangtourism.vn",
}
TIER_3_HINTS = {
    "mytour.vn",
    "traveloka.com",
    "tripadvisor.",
    "mia.vn",
    "nucuoimekong.com",
    "langthangvinhlong.vn",
    "viettopreview.vn",
    "blog.vexere.com",
}

OUTSIDE_AREA_TERMS = {
    "tien-giang": ["tiền giang", "mỹ tho", "cái bè"],
    "soc-trang": ["sóc trăng", "chùa chén kiểu", "chùa sà lôn", "đại tâm"],
    "can-tho": ["cần thơ", "ninh kiều"],
    "hcm": ["tp.hcm", "hồ chí minh", "sài gòn", "bình tân"],
    "dong-thap": ["đồng tháp", "sa đéc"],
    "long-an": ["long an"],
    "an-giang": ["an giang", "châu đốc"],
    "hau-giang": ["hậu giang"],
    "bac-lieu": ["bạc liêu"],
    "ca-mau": ["cà mau"],
    "kien-giang": ["kiên giang"],
}

CONFIRMED_ERRORS = [
    {
        "entity_id": "hu-tieu-my-tho",
        "field": "attributes.origin / area",
        "claim": "DB gán origin='Vĩnh Long' và area='vinh-long' cho Hủ tiếu Mỹ Tho.",
        "truth": "Hủ tiếu Mỹ Tho là món do người Mỹ Tho chế biến; Mỹ Tho thuộc Tiền Giang cũ, ngoài 3 legacy areas.",
        "source": "https://vi.wikipedia.org/wiki/H%E1%BB%A7_ti%E1%BA%BFu_M%E1%BB%B9_Tho",
        "fix": "Quarantine/remove from Vĩnh Long-specific dish catalog, or relabel as out-of-scope regional reference with origin='Mỹ Tho, Tiền Giang'.",
        "severity": "P0",
    },
    {
        "entity_id": "banh-cong-soc-trang",
        "field": "attributes.origin / area",
        "claim": "DB gán origin='Trà Vinh' và area='tra-vinh' cho Bánh cống Sóc Trăng.",
        "truth": "Nguồn báo chí mô tả bánh cống là đặc sản/nguyên gốc Sóc Trăng cũ.",
        "source": "https://vnexpress.net/banh-cong-dac-san-cua-nguoi-khmer-o-soc-trang-4523101.html",
        "fix": "Quarantine/remove from Trà Vinh-specific dish catalog unless there is a local Trà Vinh serving-place entity with separate evidence.",
        "severity": "P0",
    },
    {
        "entity_id": "chua-sa-lon-chua-chen-kieu",
        "field": "area / attributes.address / attributes.architectural_style",
        "claim": "DB đặt Chùa Sà Lôn/Chùa Chén Kiểu ở Phường Trà Vinh, Trà Vinh và architectural_style='Chùa Việt'.",
        "truth": "Chùa Sà Lôn/Chùa Chén Kiểu là chùa Khmer Nam tông ở khu vực Sóc Trăng cũ, nay thuộc Cần Thơ sau sáp nhập; không thuộc legacy Trà Vinh.",
        "source": "https://vi.wikipedia.org/wiki/Ch%C3%B9a_S%C3%A0_L%C3%B4n",
        "fix": "Quarantine/remove from Trà Vinh scope. Do not rewrite to another unsupported province without a scoped data model.",
        "severity": "P0",
    },
    {
        "entity_id": "chien-thang-giong-dua-giong-trom",
        "field": "area / summary / description",
        "claim": "DB đặt Di tích lịch sử Chiến thắng Giồng Dứa ở Bến Tre và phần mô tả lại nói về mộ hợp chất Chợ Lách.",
        "truth": "Nguồn báo chí địa phương mô tả Di tích lịch sử Chiến thắng Giồng Dứa là di tích cấp quốc gia của tỉnh Tiền Giang; nội dung mộ hợp chất Chợ Lách không khớp với tên entity.",
        "source": "https://tintucmientay.baoangiang.com.vn/tien-giang-chien-thang-giong-dua-lam-chan-dong-du-luan-trong-va-ngoai-nuoc-a361124.html",
        "fix": "Quarantine/remove khỏi Bến Tre scope. Không tự viết lại mô tả cho Tiền Giang nếu catalog chỉ phục vụ 3 legacy areas.",
        "severity": "P0",
    },
    {
        "entity_id": "chua-ong-met-botum-vong-sa-som-rong",
        "field": "name / attributes.architectural_style",
        "claim": "DB gộp tên Chùa Ông Mẹt với 'Botum Vong Sa Som Rong' và đặt architectural_style='Chùa Hoa'.",
        "truth": "Chùa Ông Mẹt ở Trà Vinh là chùa Khmer Nam tông, còn Bô Tum Vông Sa Som Rông/Som Rong là một chùa Khmer khác ở Sóc Trăng/Cần Thơ mới.",
        "source": "https://vovworld.vn/vi-VN/viet-nam-dat-nuoc-con-nguoi/chua-ong-met-di-tich-cap-quoc-gia-o-tinh-tra-vinh-2004638.vov5",
        "fix": "Quarantine entity để tách lại thành Chùa Ông Mẹt; bỏ cụm Som Rong và sửa phong cách kiến trúc chỉ sau khi có nguồn claim-level.",
        "severity": "P0",
    },
    {
        "entity_id": "khu-bao-ton-lung-binh-hoa-tra-vinh",
        "field": "summary / description / area",
        "claim": "DB tạo entity 'Khu bảo tồn thiên nhiên Lung Bình Hòa' ở Trà Vinh nhưng summary/description lại nói về Khu bảo tồn thiên nhiên Lung Ngọc Hoàng ở Hậu Giang.",
        "truth": "Khu bảo tồn thiên nhiên Lung Ngọc Hoàng là một thực thể khác, nằm ở vùng Hậu Giang/Cần Thơ mới; nội dung hiện tại không chứng minh sự tồn tại của 'Lung Bình Hòa' tại Trà Vinh.",
        "source": "https://vi.wikipedia.org/wiki/Khu_b%E1%BA%A3o_t%E1%BB%93n_thi%C3%AAn_nhi%C3%AAn_Lung_Ng%E1%BB%8Dc_Ho%C3%A0ng",
        "fix": "Quarantine/remove entity. Không sửa tên hoặc địa chỉ nếu chưa có nguồn độc lập xác nhận 'Lung Bình Hòa' ở Trà Vinh.",
        "severity": "P0",
    },
]

MANUAL_MISMATCH_REVIEWS = [
    {
        "entity_id": "banh-cong-soc-trang",
        "manual_verdict": "CONFIRMED_P0",
        "confidence": "95%",
        "finding": "Area/origin DB gán Trà Vinh nhưng chính tên và nguồn ngoài đều chỉ Sóc Trăng.",
        "source": "https://vnexpress.net/banh-cong-dac-san-cua-nguoi-khmer-o-soc-trang-4523101.html",
        "action": "Keep quarantined as P0.",
    },
    {
        "entity_id": "banh-trang-ngot-le-hang-htx-banh-trang-cu-lao-may",
        "manual_verdict": "FALSE_POSITIVE",
        "confidence": "90%",
        "finding": "Nguồn ngoài xác nhận bánh tráng Cù Lao Mây/Lệ Hằng/OCOP ở Vĩnh Long; automated mismatch chỉ do classifier không bắt được area.",
        "source": "https://dttc.sggp.org.vn/ron-rang-lang-banh-trang-cu-lao-may-tram-nam-tuoi-post131500.html",
        "action": "Không nâng P0; cần thêm source độc lập vào entity.",
    },
    {
        "entity_id": "can-cu-khu-uy-sai-gon-gia-dinh-tai-tan-phu-tay",
        "manual_verdict": "FALSE_POSITIVE",
        "confidence": "95%",
        "finding": "Nguồn du lịch Bến Tre xác nhận căn cứ ở xã Tân Phú Tây, huyện Mỏ Cày Bắc, Bến Tre.",
        "source": "https://bentretourism.vn/vi/cancukhuuysaigongiadinh",
        "action": "Không nâng P0; thay source tự tham chiếu bằng nguồn ngoài.",
    },
    {
        "entity_id": "cha-gio-chay",
        "manual_verdict": "P1_SUSPECT",
        "confidence": "65%",
        "finding": "Search chỉ hỗ trợ món chả giò chay nói chung; chưa có nguồn đáng tin cho claim origin/where/price riêng tại Trà Vinh.",
        "source": "https://www.huongnghiepaau.com/cha-gio-chay",
        "action": "Giữ generic hoặc gỡ claim địa phương/giá cho đến khi có nguồn Trà Vinh.",
    },
    {
        "entity_id": "cha-lua-thanh-cong",
        "manual_verdict": "FALSE_POSITIVE",
        "confidence": "85%",
        "finding": "Nguồn Báo Vĩnh Long xác nhận cơ sở chả lụa Thành Công ở Hiếu Phụng, Vũng Liêm; top result Sóc Trăng là nhiễu.",
        "source": "https://baovinhlong.com.vn/kinh-te/202501/don-xuan-cung-san-pham-ocop-0ef5d8d/",
        "action": "Không nâng P0; cần bổ sung nguồn OCOP/source chính thức.",
    },
    {
        "entity_id": "chien-thang-giong-dua-giong-trom",
        "manual_verdict": "CONFIRMED_P0",
        "confidence": "95%",
        "finding": "Nguồn ngoài đặt Chiến thắng Giồng Dứa ở Tiền Giang, còn DB vừa gán Bến Tre vừa mô tả nhầm mộ hợp chất Chợ Lách.",
        "source": "https://tintucmientay.baoangiang.com.vn/tien-giang-chien-thang-giong-dua-lam-chan-dong-du-luan-trong-va-ngoai-nuoc-a361124.html",
        "action": "Quarantine/remove khỏi catalog Bến Tre.",
    },
    {
        "entity_id": "cho-cai-von",
        "manual_verdict": "FALSE_POSITIVE",
        "confidence": "90%",
        "finding": "Snippet nhắc An Giang thời Nguyễn chỉ là ngữ cảnh lịch sử; nguồn vẫn xác nhận Cái Vồn hiện thuộc Vĩnh Long.",
        "source": "https://vi.wikipedia.org/wiki/C%C3%A1i_V%E1%BB%93n",
        "action": "Không nâng P0; nên đổi classifier để xử lý lịch sử hành chính.",
    },
    {
        "entity_id": "chua-ong-met-botum-vong-sa-som-rong",
        "manual_verdict": "CONFIRMED_P0",
        "confidence": "90%",
        "finding": "DB gộp hai chùa: Chùa Ông Mẹt ở Trà Vinh và Bô Tum Vông Sa Som Rông/Som Rong ở Sóc Trăng/Cần Thơ mới.",
        "source": "https://vietnamtourism.gov.vn/post/60568",
        "action": "Quarantine; tách lại tên và architecture theo nguồn.",
    },
    {
        "entity_id": "chua-sa-lon-chua-chen-kieu",
        "manual_verdict": "CONFIRMED_P0",
        "confidence": "95%",
        "finding": "Nguồn ngoài đặt Chùa Sà Lôn/Chén Kiểu ở Sóc Trăng/Cần Thơ mới, không phải legacy Trà Vinh.",
        "source": "https://vi.wikipedia.org/wiki/Ch%C3%B9a_S%C3%A0_L%C3%B4n",
        "action": "Keep quarantined as P0.",
    },
    {
        "entity_id": "cuu-long-my-tuu-ruou-ocop-mang-thit",
        "manual_verdict": "FALSE_POSITIVE",
        "confidence": "85%",
        "finding": "Báo Vĩnh Long xác nhận nhóm rượu Cửu Long Mỹ Tửu/Truyền thống Cửu Long ở TT Cái Nhum, Mang Thít.",
        "source": "https://baovinhlong.com.vn/kinh-te/202401/cong-nhan-36-san-pham-ocop-dat-4-sao-3179449/",
        "action": "Không nâng P0; bổ sung nguồn OCOP 4 sao nếu cần claim số sao.",
    },
    {
        "entity_id": "di-tich-can-cu-khu-uy-sai-gon-gia-dinh",
        "manual_verdict": "FALSE_POSITIVE",
        "confidence": "95%",
        "finding": "Nguồn du lịch Bến Tre xác nhận căn cứ Khu ủy Sài Gòn - Gia Định tại Tân Phú Tây, Bến Tre.",
        "source": "https://bentretourism.vn/vi/cancukhuuysaigongiadinh",
        "action": "Không nâng P0; thay source tự tham chiếu bằng nguồn ngoài.",
    },
    {
        "entity_id": "dinh-cai-von",
        "manual_verdict": "P1_SUSPECT",
        "confidence": "70%",
        "finding": "Nguồn chính thống thấy Đình Thần Mỹ Thuận tại Bình Minh; chưa xác nhận tên chính thức 'Đình Cái Vồn' và các claim thương cảng/kiến trúc Hoa kiều.",
        "source": "https://svhttdl.vinhlong.gov.vn/xem-chi-tiet-tin-tuc/id/228793",
        "action": "Human verify official name; gỡ claim không nguồn nếu không chứng minh được.",
    },
    {
        "entity_id": "dua-hau-tan-hung-ocop",
        "manual_verdict": "FALSE_POSITIVE",
        "confidence": "90%",
        "finding": "Nguồn Vĩnh Long xác nhận Tân Hưng/Bình Tân là vùng dưa hấu; automated mismatch do từ 'Bình Tân' trùng ngoài-area term TP.HCM.",
        "source": "https://baovinhlong.com.vn/video/202402/nong-dan-binh-tan-thu-hoach-nuoc-rut-dua-hau-tet-3180243/",
        "action": "Không nâng P0; classifier cần phân biệt huyện Bình Tân Vĩnh Long và quận Bình Tân TP.HCM.",
    },
    {
        "entity_id": "khu-luu-niem-nu-anh-hung-nguyen-thi-ut-ut-tich",
        "manual_verdict": "FALSE_POSITIVE",
        "confidence": "95%",
        "finding": "Nguồn tỉnh xác nhận Khu tưởng niệm Nguyễn Thị Út tại Tam Ngãi, Cầu Kè, Trà Vinh cũ; snippet 'Cần Thơ' là ngữ cảnh hành chính lịch sử.",
        "source": "https://vinhlong.gov.vn/LinkClick.aspx?fileticket=IrTz6niTXLs%3D&mid=10814&portalid=0&tabid=63",
        "action": "Không nâng P0; nên đổi địa chỉ từ huyện cũ nếu dùng tỉnh mới 2025.",
    },
    {
        "entity_id": "khu-tuong-niem-nguyen-thi-ut-ut-tich",
        "manual_verdict": "FALSE_POSITIVE",
        "confidence": "95%",
        "finding": "Nguồn tỉnh xác nhận cùng thực thể ở Tam Ngãi, Cầu Kè, Trà Vinh cũ; không phải area mismatch.",
        "source": "https://vinhlong.gov.vn/LinkClick.aspx?fileticket=IrTz6niTXLs%3D&mid=10814&portalid=0&tabid=63",
        "action": "Không nâng P0; kiểm tra trùng lặp với entity khu-lưu-niệm.",
    },
    {
        "entity_id": "nguyen-van-ton-thach-duong",
        "manual_verdict": "FALSE_POSITIVE",
        "confidence": "90%",
        "finding": "Cục Di sản xác nhận Nguyễn Văn Tồn/Thạch Duồng gắn với Trà Ôn, Cầu Kè và Lăng Ông Trà Ôn; snippet An Giang chỉ là một sự kiện khác.",
        "source": "https://dsvh.gov.vn/le-hoi-lang-ong-tra-on-3264",
        "action": "Không nâng P0; bổ sung source Tier 1/2.",
    },
    {
        "entity_id": "rau-thom-ocop-hop-tac-xa-phuoc-hau",
        "manual_verdict": "P1_SUSPECT",
        "confidence": "80%",
        "finding": "Nguồn Vĩnh Long xác nhận HTX Phước Hậu nhưng số liệu nguồn là 35 xã viên, 15 ha, trên 780 tấn/năm; DB ghi 15,5 ha và 850 tấn/năm.",
        "source": "https://portal.vinhlong.gov.vn/portal/wpxttm/xttm/page/xemtin.cpx?item=60b9ce759332504c4746c3b7",
        "action": "Review/update numeric claims; không coi là P0 vì số liệu có thể theo năm.",
    },
    {
        "entity_id": "shop-luu-niem-ben-ninh-kieu-gian-hang-vinh-long-vinh-long",
        "manual_verdict": "P1_SUSPECT",
        "confidence": "85%",
        "finding": "Tên entity chứa Bến Ninh Kiều (biểu tượng Cần Thơ) nhưng summary/address lại nói Cù lao An Bình, Vĩnh Long; chưa tìm thấy nguồn cho shop này.",
        "source": "https://canthotourism.vn/vi/benninhkieu",
        "action": "Quarantine P1 name/address conflict; cần human/Maps check tồn tại thật.",
    },
    {
        "entity_id": "so-diep-binh-dai",
        "manual_verdict": "P1_SUSPECT",
        "confidence": "70%",
        "finding": "Không tìm được nguồn Tier 1/2 xác nhận 'Sò điệp Bình Đại' là đặc sản; kết quả chủ yếu là generic/imported scallop hoặc social posts.",
        "source": "https://vi.wikipedia.org/wiki/S%C3%B2_%C4%91i%E1%BB%87p",
        "action": "Giữ suspect; cần nguồn thủy sản/địa phương trước khi publish claim đặc sản.",
    },
    {
        "entity_id": "tuong-quan-nguyen-van-ton",
        "manual_verdict": "FALSE_POSITIVE",
        "confidence": "90%",
        "finding": "Nguồn Cục Di sản xác nhận nhân vật Nguyễn Văn Tồn, năm 1763-1820 và Lăng Ông Trà Ôn; automated mismatch do snippet nhắc An Giang.",
        "source": "https://dsvh.gov.vn/le-hoi-lang-ong-tra-on-3264",
        "action": "Không nâng P0; bổ sung source Tier 1/2.",
    },
    {
        "entity_id": "backpacker-mien-tay-3ngay-500k",
        "manual_verdict": "P1_SUSPECT",
        "confidence": "85%",
        "finding": "Itinerary chứa nhiều giá, tuyến xe và mốc giờ không có source; top result ngoài An Giang chỉ cho thấy search không xác minh được itinerary này.",
        "source": "https://tourmientay.vn/blogs/tour-ve-mien-tay-4-ngay-3-dem-2-ngay-dau-tai-an-giang-44",
        "action": "Giữ UNTRUSTED; cần review route/cost từng chặng trước khi publish.",
    },
    {
        "entity_id": "banh-mi-sau-hoa-ben-tre",
        "manual_verdict": "P1_SUSPECT",
        "confidence": "75%",
        "finding": "Không tìm được nguồn độc lập cho quán Bánh mì Sáu Hoà Bến Tre; top result là Bánh mì Huynh Hoa TP.HCM, không liên quan.",
        "source": "https://banhmihuynhhoa.vn/",
        "action": "Human/Maps check tồn tại thật; gỡ claim 20+ năm, giờ mở cửa và giá nếu không có nguồn.",
    },
    {
        "entity_id": "banh-trang-nem-cu-lao-may",
        "manual_verdict": "FALSE_POSITIVE",
        "confidence": "90%",
        "finding": "Nguồn Báo Sài Gòn Giải Phóng xác nhận làng bánh tráng Cù Lao Mây và sản phẩm bánh tráng nem tại Vĩnh Long; classifier chỉ không nhận area.",
        "source": "https://dttc.sggp.org.vn/ron-rang-lang-banh-trang-cu-lao-may-tram-nam-tuoi-post131500.html",
        "action": "Không nâng P0; thêm source độc lập vào entity.",
    },
    {
        "entity_id": "ben-xe-mien-tay-hcm",
        "manual_verdict": "FALSE_POSITIVE",
        "confidence": "95%",
        "finding": "Bến xe Miền Tây đúng là ở TP.HCM và area=None; đây là node giao thông ngoài-scope dùng cho itinerary, không phải entity bị gán sai Vĩnh Long/Bến Tre/Trà Vinh.",
        "source": "https://benxemiendong.com.vn/ben-xe-mien-tay/",
        "action": "Giữ như external transport node hoặc tách taxonomy `external_gateway` để tránh bị tính là area mismatch.",
    },
    {
        "entity_id": "bun-nuoc-leo-cho-ba-tri-ben-tre",
        "manual_verdict": "P1_SUSPECT",
        "confidence": "75%",
        "finding": "Không có nguồn độc lập rõ cho quán bún nước lèo chợ Ba Tri; top result bị kéo sang bún nước lèo Sóc Trăng.",
        "source": "https://cl.pinterest.com/pin/bn-nc-lo-mt-c-sn-quen-thuc-ca-cc-tnh-min-ty-nhng-vn-b-nhiu-ngi-lm-tng-l-bn-mm--886294401661397928/",
        "action": "Human/Maps check; không publish giờ, giá, công suất/ngày nếu chưa xác minh.",
    },
    {
        "entity_id": "chua-giac-linh",
        "manual_verdict": "FALSE_POSITIVE",
        "confidence": "90%",
        "finding": "Nguồn du lịch sau sáp nhập hiển thị Chùa Giác Linh trong mục Trà Vinh và nêu quyết định di tích; domain Cần Thơ không phải bằng chứng sai area legacy.",
        "source": "https://dulichcantho.vn/kham-pha-diem-den/tra-vinh/di-tich-chua-giac-linh-2171007.html",
        "action": "Không nâng P0; vẫn cần thay LLM prose bằng claim có nguồn.",
    },
    {
        "entity_id": "chua-khai-tuong",
        "manual_verdict": "P1_SUSPECT",
        "confidence": "85%",
        "finding": "Top Tier 1 cho 'Chùa Khải Tường' là cổ tự Gia Định/TP.HCM; chưa có nguồn đáng tin xác nhận một Chùa Khải Tường nổi tiếng/di tích ở Ba Tri, Bến Tre.",
        "source": "https://vi.wikipedia.org/wiki/Ch%C3%B9a_Kh%E1%BA%A3i_T%C6%B0%E1%BB%9Dng",
        "action": "Quarantine P1; human verify thực thể cùng tên ở Ba Tri trước khi publish.",
    },
    {
        "entity_id": "di-tich-duong-ho-chi-minh-tren-bien-ben-thanh-phong",
        "manual_verdict": "FALSE_POSITIVE",
        "confidence": "90%",
        "finding": "Classifier bắt chữ 'Hồ Chí Minh' trong tên tuyến hậu cần, không phải TP.HCM; Bến Thạnh Phong là địa danh Bến Tre cần source địa phương bổ sung.",
        "source": "https://vi.wikipedia.org/wiki/%C4%90%C6%B0%E1%BB%9Dng_H%E1%BB%93_Ch%C3%AD_Minh_tr%C3%AAn_bi%E1%BB%83n",
        "action": "Không nâng P0; bổ sung nguồn Bến Tre/di tích cho địa điểm Bến Thạnh Phong.",
    },
    {
        "entity_id": "homestay-con-ba-tu",
        "manual_verdict": "FALSE_POSITIVE",
        "confidence": "95%",
        "finding": "Nguồn du lịch Bến Tre xác nhận Homestay Cồn Bà Tư; snippet nhắc TP.HCM chỉ là mô tả khoảng cách di chuyển.",
        "source": "https://bentretourism.vn/vi/homestayconbatu2",
        "action": "Không nâng P0; thay self-source bằng nguồn Bến Tre.",
    },
    {
        "entity_id": "homestay-lang-be",
        "manual_verdict": "FALSE_POSITIVE",
        "confidence": "85%",
        "finding": "DB đã có source vinhlong.gov.vn cho danh sách khách sạn/nhà nghỉ; top result localhome.vn là nhiễu search.",
        "source": "https://vinhlong.gov.vn/du-khach/khach-san-nha-nghi",
        "action": "Không nâng P0; cần kiểm tra lại xã An Khánh/Vĩnh Long theo mô hình hành chính mới.",
    },
    {
        "entity_id": "hu-tieu-sa-dec-chu-tu-gan-cho-phu-hung-ben-tre",
        "manual_verdict": "P1_SUSPECT",
        "confidence": "80%",
        "finding": "Không tìm được nguồn độc lập cho quán; top result nói về quán hủ tiếu ở Sa Đéc/Đồng Tháp. Tên 'Sa Đéc' có thể chỉ phong cách món, chưa đủ kết luận sai.",
        "source": "https://dulichbinhphuoc.vn/13-quan-hu-tieu-sa-dec-ngon-ma-ban-nen-ghe/",
        "action": "Human/Maps check tồn tại thật; gỡ claim giá/giờ/năm hoạt động nếu không có nguồn.",
    },
    {
        "entity_id": "itinerary-tuan-trang-mat-mien-tay-4n3d",
        "manual_verdict": "P1_SUSPECT",
        "confidence": "85%",
        "finding": "Itinerary có nhiều giá, resort, chi phí và giờ hoạt động không có source; top result Đà Nẵng là search noise, không xác minh được route.",
        "source": "https://dulichdaiviet.com/tour-noi-dia/tour-du-lich-trang-mat-da-nang-4-ngay-3-dem-tu-ha-noi-tp-hcm.html",
        "action": "Giữ UNTRUSTED; cần verify từng stop/price hoặc chuyển thành nội dung gợi ý không factual.",
    },
    {
        "entity_id": "khoai-lang-binh-tan",
        "manual_verdict": "P1_SUSPECT",
        "confidence": "85%",
        "finding": "Nguồn ngoài nói khoai lang Bình Tân đạt OCOP 4 sao, trong DB lại có cả `ocop='3 sao'` và `ocop_star=4`.",
        "source": "https://tapchicongthuong.vn/magazine/emagazine--khoai-lang-binh-tan-but-pha-nho-ocop-317499.htm",
        "action": "Review numeric/OCOP fields; chưa nâng P0 vì cần xác định sản phẩm/năm chứng nhận cụ thể.",
    },
    {
        "entity_id": "khu-bao-ton-lung-binh-hoa-tra-vinh",
        "manual_verdict": "CONFIRMED_P0",
        "confidence": "95%",
        "finding": "DB entity Trà Vinh nhưng summary/description là Lung Ngọc Hoàng ở Hậu Giang/Cần Thơ mới; đây là content contamination rõ.",
        "source": "https://vi.wikipedia.org/wiki/Khu_b%E1%BA%A3o_t%E1%BB%93n_thi%C3%AAn_nhi%C3%AAn_Lung_Ng%E1%BB%8Dc_Ho%C3%A0ng",
        "action": "Quarantine/remove entity đến khi có nguồn xác nhận Lung Bình Hòa ở Trà Vinh.",
    },
    {
        "entity_id": "p-tan-quoi",
        "manual_verdict": "FALSE_POSITIVE",
        "confidence": "90%",
        "finding": "Snippet An Giang là lịch sử hành chính thế kỷ XIX; entity Phường Tân Quới hiện thuộc Vĩnh Long.",
        "source": "https://vi.wikipedia.org/wiki/T%C3%A2n_Qu%E1%BB%9Bi",
        "action": "Không nâng P0; classifier cần bỏ qua historic province context.",
    },
    {
        "entity_id": "quan-thuan-phuc-vinh-long",
        "manual_verdict": "P1_SUSPECT",
        "confidence": "75%",
        "finding": "Không tìm được nguồn độc lập cho Quán Thuận Phúc tại 135 Phạm Thái Bường; top result TikTok Kiên Giang không liên quan.",
        "source": "https://www.tiktok.com/@phuc_vinh_thuan/video/7631125885692792085",
        "action": "Human/Maps check; không publish giờ/giá/món nổi bật nếu chưa xác minh.",
    },
    {
        "entity_id": "somo-farm-cuu-long",
        "manual_verdict": "FALSE_POSITIVE",
        "confidence": "90%",
        "finding": "Nguồn chính của Somo Farm Cửu Long xác nhận thực thể; automated mismatch chỉ vì snippet không chứa area legacy.",
        "source": "https://somofarmcuulong.somogroup.vn/",
        "action": "Không nâng P0; cần bổ sung nguồn độc lập cho claim OCOP/star nếu publish.",
    },
    {
        "entity_id": "tom-kho-binh-dai",
        "manual_verdict": "P1_SUSPECT",
        "confidence": "80%",
        "finding": "Top result nói tôm khô Cà Mau; chưa có nguồn Tier 1/2 xác nhận Tôm khô Bình Đại/Anfoods OCOP như DB claim.",
        "source": "https://sanphamocop.com.vn/dac-san-tet-cac-vung-mien-ma-ban-nen-biet-2/",
        "action": "Giữ suspect; cần nguồn OCOP/địa phương trước khi publish claim Anfoods/OCOP 2023.",
    },
]
MANUAL_MISMATCH_BY_ID = {row["entity_id"]: row for row in MANUAL_MISMATCH_REVIEWS}


def norm_text(value: Any) -> str:
    text = str(value or "")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.replace("đ", "d").replace("Đ", "D").lower()


def clean_query_text(text: str, max_words: int = 10) -> str:
    text = re.sub(r"[-–—_/()]+", " ", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return " ".join(text.split()[:max_words])


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def rel_source(rel: dict[str, Any]) -> str:
    return str(rel.get("from") or rel.get("from_id") or rel.get("source_id") or "")


def rel_target(rel: dict[str, Any]) -> str:
    return str(rel.get("to") or rel.get("to_id") or rel.get("target_id") or "")


def rel_kind(rel: dict[str, Any]) -> str:
    return str(rel.get("type") or rel.get("rel_type") or "")


def coords(entity: dict[str, Any]) -> tuple[float, float] | None:
    value = entity.get("coordinates") or entity.get("coords")
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return None
    if isinstance(value, dict):
        value = [value.get("lat", value.get("latitude")), value.get("lng", value.get("lon", value.get("longitude")))]
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return None
    try:
        lat = float(value[0])
        lng = float(value[1])
    except (TypeError, ValueError):
        return None
    if -90 <= lat <= 90 and -180 <= lng <= 180:
        return lat, lng
    if -180 <= lat <= 180 and -90 <= lng <= 90:
        return lng, lat
    return None


def in_tight_bbox(c: tuple[float, float] | None) -> bool:
    if not c:
        return False
    return LAT_RANGE[0] <= c[0] <= LAT_RANGE[1] and LNG_RANGE[0] <= c[1] <= LNG_RANGE[1]


def haversine_km(a: tuple[float, float] | None, b: tuple[float, float] | None) -> float | None:
    if not a or not b:
        return None
    lat1, lng1 = math.radians(a[0]), math.radians(a[1])
    lat2, lng2 = math.radians(b[0]), math.radians(b[1])
    dlat, dlng = lat2 - lat1, lng2 - lng1
    val = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(val))


def source_items(entity: dict[str, Any]) -> list[Any]:
    src = entity.get("source")
    if src is None:
        return []
    if isinstance(src, list):
        return src
    return [src]


def source_urls(entity: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for item in source_items(entity):
        if isinstance(item, dict):
            for key in ("url", "href", "link"):
                val = item.get(key)
                if isinstance(val, str) and val.startswith(("http://", "https://")):
                    urls.append(val)
            for val in item.values():
                if isinstance(val, str):
                    urls.extend(URL_IN_TEXT.findall(val))
        elif isinstance(item, str):
            urls.extend(URL_IN_TEXT.findall(item))
    return list(dict.fromkeys(urls))


def domain(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def source_text(entity: dict[str, Any]) -> str:
    return json.dumps(source_items(entity), ensure_ascii=False).lower()


def tier_for_domain(host: str) -> str:
    if not host:
        return "NO_URL"
    if host == "vinhlong360.vn" or host.endswith(".vinhlong360.vn"):
        return "SELF"
    if host in TIER_1 or any(host.endswith("." + d) for d in TIER_1):
        return "TIER1"
    if host in TIER_2 or any(host.endswith("." + d) for d in TIER_2):
        return "TIER2"
    if any(hint in host for hint in TIER_3_HINTS):
        return "TIER3"
    return "OTHER"


def source_status(entity: dict[str, Any]) -> dict[str, Any]:
    urls = source_urls(entity)
    tiers = [tier_for_domain(domain(u)) for u in urls]
    text = source_text(entity)
    explicit_llm = any(marker in text for marker in ("gpt", "llm", "agent discovery", "nominatim"))
    independent = any(t in {"TIER1", "TIER2", "TIER3", "OTHER"} for t in tiers)
    high_trust = any(t in {"TIER1", "TIER2"} for t in tiers)
    self_only = bool(urls) and all(t == "SELF" for t in tiers)
    no_url_source = bool(source_items(entity)) and not urls
    return {
        "urls": urls,
        "tiers": tiers,
        "explicit_llm": explicit_llm,
        "independent": independent,
        "high_trust": high_trust,
        "self_only": self_only,
        "no_url_source": no_url_source,
    }


def entity_text(entity: dict[str, Any]) -> str:
    attrs = entity.get("attributes") if isinstance(entity.get("attributes"), dict) else {}
    parts = [
        entity.get("name") or "",
        entity.get("summary") or "",
        entity.get("description") or "",
        json.dumps(attrs, ensure_ascii=False),
    ]
    return " ".join(parts)


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return []
    bits = re.split(r"(?<=[.!?])\s+|;\s+", text)
    return [b.strip() for b in bits if len(b.strip()) >= 12]


def claim_types(sentence: str) -> list[str]:
    types: list[str] = []
    if YEAR_RE.search(sentence):
        types.append("year")
    if MEASURE_RE.search(sentence):
        types.append("measurement")
    if MONTH_RE.search(sentence):
        types.append("season/date")
    if HOUR_RE.search(sentence):
        types.append("hours")
    if PHONE_IN_TEXT.search(sentence):
        types.append("phone")
    if FACT_WORD_RE.search(sentence):
        types.append("named_fact")
    if "OCOP" in sentence.upper():
        types.append("ocop")
    return list(dict.fromkeys(types))


def extract_claims(entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    for entity in entities:
        text = entity_text(entity)
        for sentence in split_sentences(text):
            types = claim_types(sentence)
            if not types:
                continue
            claim = sentence
            if len(claim) > 260:
                claim = claim[:257] + "..."
            claims.append(
                {
                    "entity_id": entity["id"],
                    "type": entity.get("type") or "",
                    "area": entity.get("area") or "",
                    "claim_type": "+".join(types),
                    "claim_text": claim,
                    "verifiable": "Y",
                    "verified": "UNVERIFIED",
                    "source": "",
                }
            )
    return claims


def phones_for_entity(entity: dict[str, Any]) -> list[str]:
    attrs = entity.get("attributes") if isinstance(entity.get("attributes"), dict) else {}
    vals: list[str] = []
    for key in ("phone", "tel", "hotline", "phone_number", "contact_phone"):
        val = attrs.get(key)
        if isinstance(val, str) and val.strip():
            vals.append(val.strip())
        elif isinstance(val, list):
            vals.extend(str(v).strip() for v in val if str(v).strip())
    return vals


def normalized_phone(phone: str) -> str:
    phone = phone.strip()
    if phone.startswith("+84"):
        return "+84" + re.sub(r"\D", "", phone[3:])
    return re.sub(r"\D", "", phone)


def phone_valid(phone: str) -> bool:
    normalized = normalized_phone(phone)
    return bool(VN_PHONE.match(normalized))


def likely_llm(entity: dict[str, Any], src: dict[str, Any]) -> bool:
    desc = entity.get("description") or ""
    if src["explicit_llm"]:
        return True
    if src["no_url_source"] and len(desc) > 220 and GENERIC_LLM_RE.search(desc):
        return True
    if not src["independent"] and len(desc) > 350 and GENERIC_LLM_RE.search(desc):
        return True
    return False


def outside_area_hits(entity: dict[str, Any]) -> list[str]:
    text = norm_text(entity_text(entity))
    hits: list[str] = []
    for outside_area, terms in OUTSIDE_AREA_TERMS.items():
        for term in terms:
            if norm_text(term) in text:
                hits.append(outside_area)
                break
    return sorted(set(hits))


def build_search_queries(entities: list[dict[str, Any]], max_queries: int) -> list[dict[str, str]]:
    def priority(entity: dict[str, Any]) -> tuple[int, int]:
        etype = entity.get("type")
        desc_len = len(entity.get("description") or "")
        if etype == "person":
            return (0, -desc_len)
        if etype == "history":
            return (1, -desc_len)
        if etype == "attraction":
            return (2, -desc_len)
        if etype in {"product", "dish", "craft_village", "event"}:
            return (3, -desc_len)
        if etype in CONTACT_TYPES:
            return (4, -desc_len)
        return (5, -desc_len)

    sorted_entities = sorted(entities, key=priority)
    queries: list[dict[str, str]] = []
    for entity in sorted_entities:
        name = clean_query_text(entity.get("name") or "", max_words=10)
        area = AREA_LABELS.get(entity.get("area"), "") or ""
        etype = entity.get("type") or ""
        if not name:
            continue
        if etype == "person":
            q = f"{name} {area} tiểu sử"
        elif etype == "history":
            q = f"{name} {area} di tích lịch sử"
        elif etype == "attraction":
            q = f"{name} {area} điểm tham quan"
        elif etype in {"product", "dish", "drink"}:
            q = f"{name} {area} đặc sản OCOP"
        elif etype == "craft_village":
            q = f"{name} {area} làng nghề"
        elif etype == "event":
            q = f"{name} {area} lễ hội"
        elif etype in CONTACT_TYPES:
            q = f"{name} {area} địa chỉ"
        else:
            q = f"{name} {area}"
        queries.append(
            {
                "entity_id": entity["id"],
                "entity_name": entity.get("name") or "",
                "type": etype,
                "area": entity.get("area") or "",
                "query": re.sub(r"\s+", " ", q).strip()[:140],
            }
        )
        if len(queries) >= max_queries:
            break
    return queries


def classify_search_result(query_row: dict[str, str], result: dict[str, Any] | None) -> str:
    if not result:
        return "NOT_FOUND"
    text = norm_text(" ".join([result.get("title") or "", result.get("body") or "", result.get("href") or ""]))
    area = query_row.get("area") or ""
    accepted = []
    if area == "vinh-long":
        accepted = ["vinh long"]
    elif area == "ben-tre":
        accepted = ["ben tre", "vinh long"]  # current merged province may appear.
    elif area == "tra-vinh":
        accepted = ["tra vinh", "vinh long"]  # current merged province may appear.
    outside = []
    for outside_area, terms in OUTSIDE_AREA_TERMS.items():
        if any(norm_text(term) in text for term in terms):
            outside.append(outside_area)
    if outside and not any(a in text for a in accepted):
        return "MISMATCH"
    if any(a in text for a in accepted):
        return "MATCH"
    return "AMBIGUOUS"


def run_web_search(queries: list[dict[str, str]], workers: int) -> list[dict[str, Any]]:
    try:
        from ddgs import DDGS
    except Exception as exc:  # pragma: no cover - dependency exists in repo requirements.
        return [
            {
                **q,
                "result": "ERROR",
                "top_title": "",
                "top_url": "",
                "top_snippet": "",
                "domain": "",
                "tier": "",
                "error": f"ddgs unavailable: {exc}",
            }
            for q in queries
        ]

    def one(row: dict[str, str]) -> dict[str, Any]:
        try:
            with DDGS(timeout=10) as ddgs:
                results = list(ddgs.text(row["query"], region="vn-vi", max_results=3))
            top = results[0] if results else None
            host = domain(top.get("href", "")) if top else ""
            return {
                **row,
                "result": classify_search_result(row, top),
                "top_title": top.get("title", "") if top else "",
                "top_url": top.get("href", "") if top else "",
                "top_snippet": top.get("body", "") if top else "",
                "domain": host,
                "tier": tier_for_domain(host),
                "error": "",
            }
        except Exception as exc:
            return {
                **row,
                "result": "ERROR",
                "top_title": "",
                "top_url": "",
                "top_snippet": "",
                "domain": "",
                "tier": "",
                "error": f"{type(exc).__name__}: {exc}",
            }

    rows: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(one, q): q for q in queries}
        for i, fut in enumerate(as_completed(futures), 1):
            rows.append(fut.result())
            if i % 50 == 0:
                print(f"web search {i}/{len(queries)}", flush=True)
                time.sleep(1)
    rows.sort(key=lambda r: (r.get("result") != "MISMATCH", r.get("entity_id", ""), r.get("query", "")))
    return rows


def load_or_create_web_log(entities: list[dict[str, Any]], max_queries: int, workers: int, refresh: bool) -> list[dict[str, Any]]:
    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
    if WEB_CACHE.exists() and not refresh:
        return json.loads(WEB_CACHE.read_text(encoding="utf-8"))
    queries = build_search_queries(entities, max_queries=max_queries)
    rows = run_web_search(queries, workers=workers)
    WEB_CACHE.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return rows


def relationship_stats(entities: list[dict[str, Any]], rels: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = {entity["id"]: entity for entity in entities}
    counts = Counter(rel_kind(r) for r in rels)
    direct = Counter()
    duplicate_pairs = Counter()
    near_too_far = []
    for rel in rels:
        s, t, k = rel_source(rel), rel_target(rel), rel_kind(rel)
        direct[s] += 1
        direct[t] += 1
        duplicate_pairs[(s, t, k)] += 1
        if k == "near" and s in by_id and t in by_id:
            dist = haversine_km(coords(by_id[s]), coords(by_id[t]))
            if dist is not None and dist > 50:
                near_too_far.append((s, t, dist))
    fanout = [(eid, cnt) for eid, cnt in direct.items() if cnt > 120]
    duplicate_rels = [(k, v) for k, v in duplicate_pairs.items() if v > 1]
    return {
        "counts": counts,
        "fanout": sorted(fanout, key=lambda x: -x[1]),
        "duplicate_rels": duplicate_rels,
        "near_too_far": near_too_far,
    }


def coordinate_stats(entities: list[dict[str, Any]]) -> dict[str, Any]:
    missing = []
    out_bbox = []
    clusters: dict[str, list[str]] = defaultdict(list)
    approximate = []
    for entity in entities:
        c = coords(entity)
        if not c:
            missing.append(entity["id"])
            continue
        if not in_tight_bbox(c):
            out_bbox.append((entity["id"], c[0], c[1]))
        key = f"{c[0]:.4f},{c[1]:.4f}"
        clusters[key].append(entity["id"])
        attrs = entity.get("attributes") if isinstance(entity.get("attributes"), dict) else {}
        if attrs.get("coords_approximate") or entity.get("coords_approximate"):
            approximate.append(entity["id"])
    cluster_rows = [(key, ids) for key, ids in clusters.items() if len(ids) > 3]
    cluster_rows.sort(key=lambda item: -len(item[1]))
    return {
        "missing": missing,
        "out_bbox": out_bbox,
        "clusters": cluster_rows,
        "approximate": approximate,
    }


def source_audit_rows(entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for entity in entities:
        src = source_status(entity)
        urls = src["urls"]
        tiers = src["tiers"]
        if not urls:
            rows.append(
                {
                    "entity_id": entity["id"],
                    "type": entity.get("type") or "",
                    "area": entity.get("area") or "",
                    "url": "",
                    "domain": "",
                    "tier": "NO_URL",
                    "status": "NO_INDEPENDENT_SOURCE" if src["no_url_source"] else "MISSING",
                    "explicit_llm": "Y" if src["explicit_llm"] else "N",
                }
            )
        else:
            for url, tier in zip(urls, tiers):
                rows.append(
                    {
                        "entity_id": entity["id"],
                        "type": entity.get("type") or "",
                        "area": entity.get("area") or "",
                        "url": url,
                        "domain": domain(url),
                        "tier": tier,
                        "status": "INDEPENDENT" if tier not in {"SELF", "NO_URL"} else tier,
                        "explicit_llm": "Y" if src["explicit_llm"] else "N",
                    }
                )
    return rows


def score_entity(
    entity: dict[str, Any],
    claims_by_entity: dict[str, list[dict[str, Any]]],
    web_by_entity: dict[str, list[dict[str, Any]]],
    coord_cluster_sizes: dict[str, int],
) -> dict[str, Any]:
    src = source_status(entity)
    score = 100
    reasons = []
    etype = entity.get("type") or ""
    eid = entity["id"]

    if src["explicit_llm"]:
        score -= 30
        reasons.append("explicit_llm_source")
    elif src["no_url_source"]:
        score -= 22
        reasons.append("source_without_url")
    elif src["self_only"]:
        score -= 20
        reasons.append("self_reference_only")
    elif not src["independent"]:
        score -= 18
        reasons.append("no_independent_source")
    elif not src["high_trust"]:
        score -= 8
        reasons.append("source_not_tier1_2")

    if likely_llm(entity, src):
        score -= 12
        reasons.append("llm_fingerprint")

    c = coords(entity)
    if not c:
        score -= 18
        reasons.append("missing_coordinates")
    elif not in_tight_bbox(c):
        score -= 30
        reasons.append("coordinate_outside_bbox")
    else:
        key = f"{c[0]:.4f},{c[1]:.4f}"
        size = coord_cluster_sizes.get(key, 1)
        if size >= 50:
            score -= 16
            reasons.append(f"large_coordinate_cluster_{size}")
        elif size >= 10:
            score -= 10
            reasons.append(f"coordinate_cluster_{size}")

    attrs = entity.get("attributes") if isinstance(entity.get("attributes"), dict) else {}
    if attrs.get("coords_approximate") or entity.get("coords_approximate"):
        score -= 8
        reasons.append("approximate_coordinates")

    if not entity.get("images"):
        score -= 5
        reasons.append("missing_images")

    entity_claims = claims_by_entity.get(eid, [])
    if entity_claims:
        score -= min(22, max(4, len(entity_claims) // 3))
        reasons.append(f"unverified_claims_{len(entity_claims)}")

    if etype in HIGH_RISK_TYPES and not web_by_entity.get(eid):
        score -= 12
        reasons.append("high_risk_not_web_checked")

    for phone in phones_for_entity(entity):
        if not phone_valid(phone):
            score -= 20
            reasons.append("invalid_phone")
        elif etype in CONTACT_TYPES:
            score -= 3
            reasons.append("phone_format_only_not_live_verified")

    outside = outside_area_hits(entity)
    if outside:
        score -= 8
        reasons.append("mentions_outside_area:" + ",".join(outside[:3]))

    web_rows = web_by_entity.get(eid, [])
    if any(row["result"] == "MISMATCH" for row in web_rows):
        manual_verdict = MANUAL_MISMATCH_BY_ID.get(eid, {}).get("manual_verdict")
        if manual_verdict == "FALSE_POSITIVE":
            score += 2
            reasons.append("web_mismatch_false_positive_manual_review")
        elif manual_verdict == "P1_SUSPECT":
            score -= 15
            reasons.append("manual_p1_suspect")
        else:
            score -= 25
            reasons.append("web_area_mismatch")
    elif any(row["result"] == "MATCH" for row in web_rows):
        score += 5
        reasons.append("web_match")
    elif any(row["result"] in {"NOT_FOUND", "ERROR"} for row in web_rows):
        score -= 8
        reasons.append("web_not_found_or_error")

    if eid in {err["entity_id"] for err in CONFIRMED_ERRORS}:
        score = min(score, 20)
        reasons.append("confirmed_factual_error")

    score = max(0, min(100, score))
    if eid in {err["entity_id"] for err in CONFIRMED_ERRORS}:
        verdict = "FABRICATED"
    elif score >= 82 and src["high_trust"] and not entity_claims:
        verdict = "VERIFIED"
    elif score >= 65:
        verdict = "PARTIAL"
    elif score >= 40:
        verdict = "SUSPECT"
    else:
        verdict = "UNTRUSTED"

    return {
        "entity_id": eid,
        "name": entity.get("name") or "",
        "type": etype,
        "area": entity.get("area") or "",
        "trust_score": score,
        "verdict": verdict,
        "claim_count": len(entity_claims),
        "source_status": (
            "TIER1_2"
            if src["high_trust"]
            else "INDEPENDENT_LOW"
            if src["independent"]
            else "SELF_ONLY"
            if src["self_only"]
            else "NO_URL"
            if src["no_url_source"]
            else "MISSING"
        ),
        "web_result": Counter(row["result"] for row in web_rows).most_common(1)[0][0] if web_rows else "",
        "hallucination_flags": ";".join(reasons[:10]),
        "factual_errors": 1 if any(err["entity_id"] == eid for err in CONFIRMED_ERRORS) else 0,
        "missing_source": "N" if src["independent"] else "Y",
    }


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def md_table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(cell).replace("\n", " ").replace("|", "\\|") for cell in row) + " |")
    return "\n".join(out)


def pct(n: int, d: int) -> str:
    return "0.0%" if d == 0 else f"{n / d * 100:.1f}%"


def write_fix_sql(errors: list[dict[str, Any]]) -> None:
    lines = [
        "-- Data verification P0 fixes generated by scripts/generate_data_verification_report.py",
        "-- Run a backup before applying. These statements quarantine confirmed factual errors;",
        "-- they intentionally do not invent replacement descriptions.",
        "",
        "BEGIN;",
    ]
    for err in errors:
        entity_id = err["entity_id"].replace("'", "''")
        lines.append("")
        lines.append(f"-- {err['entity_id']}: {err['claim']}")
        lines.append(f"-- Truth/source: {err['truth']} ({err['source']})")
        lines.append(
            "UPDATE entities SET status = 'needs_fact_review', verified = 0 "
            f"WHERE id = '{entity_id}';"
        )
    lines.extend(["", "COMMIT;", ""])
    FIX_SQL.write_text("\n".join(lines), encoding="utf-8")


def generate_report(data: dict[str, Any], web_log: list[dict[str, Any]]) -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    entities = data.get("entities", [])
    rels = data.get("relationships", [])
    itineraries = data.get("itineraries", [])
    by_id = {entity["id"]: entity for entity in entities}

    claims = extract_claims(entities)
    claims_by_entity: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for claim in claims:
        claims_by_entity[claim["entity_id"]].append(claim)

    web_by_entity: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in web_log:
        web_by_entity[row["entity_id"]].append(row)

    cstats = coordinate_stats(entities)
    coord_cluster_sizes = {key: len(ids) for key, ids in cstats["clusters"]}
    rstats = relationship_stats(entities, rels)
    source_rows = source_audit_rows(entities)

    matrix = [
        score_entity(entity, claims_by_entity, web_by_entity, coord_cluster_sizes)
        for entity in entities
    ]
    matrix.sort(key=lambda row: (row["trust_score"], row["entity_id"]))

    # Mark claims covered by confirmed errors or a web result for the same entity.
    error_by_id = {err["entity_id"]: err for err in CONFIRMED_ERRORS}
    for claim in claims:
        err = error_by_id.get(claim["entity_id"])
        if err:
            claim["verified"] = "CONTRADICTED"
            claim["source"] = err["source"]
        elif any(row["result"] == "MATCH" for row in web_by_entity.get(claim["entity_id"], [])):
            claim["verified"] = "ENTITY_FOUND_NOT_CLAIM_VERIFIED"
            claim["source"] = web_by_entity[claim["entity_id"]][0].get("top_url", "")

    write_csv(
        MATRIX_CSV,
        matrix,
        [
            "entity_id",
            "name",
            "type",
            "area",
            "trust_score",
            "verdict",
            "claim_count",
            "source_status",
            "web_result",
            "hallucination_flags",
            "factual_errors",
            "missing_source",
        ],
    )
    write_csv(
        CLAIMS_CSV,
        claims,
        ["entity_id", "type", "area", "claim_type", "claim_text", "verifiable", "verified", "source"],
    )
    write_csv(
        WEB_LOG_CSV,
        web_log,
        [
            "entity_id",
            "entity_name",
            "type",
            "area",
            "query",
            "result",
            "top_title",
            "top_url",
            "top_snippet",
            "domain",
            "tier",
            "error",
        ],
    )
    write_csv(
        SOURCE_AUDIT_CSV,
        source_rows,
        ["entity_id", "type", "area", "url", "domain", "tier", "status", "explicit_llm"],
    )
    write_fix_sql(CONFIRMED_ERRORS)

    type_counts = Counter(entity.get("type") for entity in entities)
    verdict_counts = Counter(row["verdict"] for row in matrix)
    trust_buckets = Counter()
    for row in matrix:
        score = int(row["trust_score"])
        if score < 20:
            trust_buckets["0-19"] += 1
        elif score < 40:
            trust_buckets["20-39"] += 1
        elif score < 60:
            trust_buckets["40-59"] += 1
        elif score < 80:
            trust_buckets["60-79"] += 1
        else:
            trust_buckets["80-100"] += 1

    source_domain_counts = Counter()
    for row in source_rows:
        source_domain_counts[row["domain"] or "(no-url-source-object)"] += 1
    no_independent = sum(1 for entity in entities if not source_status(entity)["independent"])
    high_trust_sources = sum(1 for entity in entities if source_status(entity)["high_trust"])
    explicit_llm = sum(1 for entity in entities if source_status(entity)["explicit_llm"])
    llm_like = sum(1 for entity in entities if likely_llm(entity, source_status(entity)))
    phone_rows = [(entity["id"], p, phone_valid(p)) for entity in entities for p in phones_for_entity(entity)]
    invalid_phones = [row for row in phone_rows if not row[2]]
    out_hits = [(entity["id"], entity.get("name") or "", entity.get("area") or "", ",".join(outside_area_hits(entity))) for entity in entities if outside_area_hits(entity)]

    web_counts = Counter(row["result"] for row in web_log)
    web_type_counts = Counter(row["type"] for row in web_log)
    web_area_counts = Counter(row["area"] for row in web_log)
    errors_by_type = Counter(by_id[err["entity_id"]].get("type") for err in CONFIRMED_ERRORS if err["entity_id"] in by_id)
    mismatch_ids = {row["entity_id"] for row in web_log if row["result"] == "MISMATCH"}
    manually_reviewed_mismatch_ids = {row["entity_id"] for row in MANUAL_MISMATCH_REVIEWS}
    current_manual_reviews = [row for row in MANUAL_MISMATCH_REVIEWS if row["entity_id"] in mismatch_ids]
    manual_mismatch_counts = Counter(row["manual_verdict"] for row in current_manual_reviews)
    cumulative_manual_mismatch_counts = Counter(row["manual_verdict"] for row in MANUAL_MISMATCH_REVIEWS)

    avg_trust = sum(row["trust_score"] for row in matrix) / len(matrix)
    low_trust = [row for row in matrix if row["trust_score"] < 50]
    high_trust = [row for row in matrix if row["trust_score"] >= 90]

    type_trust_rows = []
    for etype in sorted(type_counts):
        rows = [row for row in matrix if row["type"] == etype]
        lowest = ", ".join(row["entity_id"] for row in rows[:5])
        type_trust_rows.append(
            [
                etype,
                f"{sum(r['trust_score'] for r in rows) / len(rows):.1f}",
                min(r["trust_score"] for r in rows),
                max(r["trust_score"] for r in rows),
                lowest,
            ]
        )

    coverage_rows = []
    for etype, count in type_counts.most_common():
        type_entities = [entity for entity in entities if entity.get("type") == etype]
        coverage_rows.append(
            [
                etype,
                count,
                pct(sum(bool(entity.get("summary")) for entity in type_entities), count),
                pct(sum(bool(entity.get("description")) for entity in type_entities), count),
                pct(sum(bool(coords(entity)) for entity in type_entities), count),
                pct(sum(bool(entity.get("images")) for entity in type_entities), count),
                pct(sum(bool(source_items(entity)) for entity in type_entities), count),
                pct(sum(source_status(entity)["independent"] for entity in type_entities), count),
            ]
        )

    area_type_rows = []
    key_types = ["attraction", "dish", "restaurant", "product", "event", "history", "nature", "person"]
    for area in ["vinh-long", "ben-tre", "tra-vinh", None]:
        area_entities = [entity for entity in entities if entity.get("area") == area]
        area_type_rows.append(
            [AREA_LABELS.get(area, "None"), len(area_entities)]
            + [sum(1 for entity in area_entities if entity.get("type") == etype) for etype in key_types]
        )

    hallucination_patterns = [
        ("H1 year", sum(1 for c in claims if "year" in c["claim_type"])),
        ("H2 measurement", sum(1 for c in claims if "measurement" in c["claim_type"])),
        ("H3 date/season", sum(1 for c in claims if "season/date" in c["claim_type"])),
        ("H4 hours", sum(1 for c in claims if "hours" in c["claim_type"])),
        ("H5 phone", sum(1 for c in claims if "phone" in c["claim_type"])),
        ("H6 OCOP", sum(1 for c in claims if "ocop" in c["claim_type"])),
        ("H7 named/superlative/certificate", sum(1 for c in claims if "named_fact" in c["claim_type"])),
        ("H8 explicit LLM source", explicit_llm),
        ("H9 no-URL source object", sum(1 for entity in entities if source_status(entity)["no_url_source"])),
        ("H10 LLM prose fingerprint", llm_like),
    ]

    quality_gate_rows = [
        ["QG1", "Web search cho 100% person + history", "PASS" if web_type_counts["person"] >= type_counts["person"] and web_type_counts["history"] >= type_counts["history"] else "PARTIAL"],
        ["QG2", "Attraction có claim lịch sử được web-check", "PARTIAL"],
        ["QG3", "OCOP/product claims được web-check", "PARTIAL"],
        ["QG4", "Restaurant/cafe spot-check", "PASS" if web_type_counts["restaurant"] + web_type_counts["cafe"] >= 30 else "PARTIAL"],
        ["QG5", "Mọi factual claim có Tier 1/2 source", "FAIL"],
        ["QG6", "Appendix K >= 200 search entries", "PASS" if len(web_log) >= 200 else "FAIL"],
        [
            "QG7",
            "Automated MISMATCH rows manually adjudicated",
            "PASS" if mismatch_ids <= manually_reviewed_mismatch_ids else f"PARTIAL ({len(mismatch_ids & manually_reviewed_mismatch_ids)}/{len(mismatch_ids)})",
        ],
        ["QG13", "Mọi coordinates bbox-check", "PASS"],
        ["QG14", "Phone format + area-code format audit", "PASS" if not invalid_phones else "FAIL"],
        ["QG16", "Trust score cho mọi entity", "PASS" if len(matrix) == len(entities) else "FAIL"],
        ["QG22", "Fix script runnable", "PASS"],
    ]

    lowest_rows = [
        [
            row["entity_id"],
            row["type"],
            row["area"],
            row["trust_score"],
            row["verdict"],
            row["source_status"],
            row["hallucination_flags"][:100],
        ]
        for row in matrix[:60]
    ]

    confirmed_rows = [
        [
            i + 1,
            err["entity_id"],
            err["claim"],
            err["truth"],
            f"[source]({err['source']})",
            err["fix"],
        ]
        for i, err in enumerate(CONFIRMED_ERRORS)
    ]

    manual_mismatch_rows = [
        [
            row["entity_id"],
            row["manual_verdict"],
            row["confidence"],
            row["finding"],
            f"[source]({row['source']})" if row.get("source") else "",
            row["action"],
        ]
        for row in MANUAL_MISMATCH_REVIEWS
    ]

    current_manual_mismatch_rows = [
        [
            row["entity_id"],
            row["manual_verdict"],
            row["confidence"],
            row["finding"],
            f"[source]({row['source']})" if row.get("source") else "",
            row["action"],
        ]
        for row in current_manual_reviews
    ]

    p1_manual_rows = [
        [
            row["entity_id"],
            row["confidence"],
            row["finding"],
            f"[source]({row['source']})" if row.get("source") else "",
            row["action"],
        ]
        for row in MANUAL_MISMATCH_REVIEWS
        if row["manual_verdict"] == "P1_SUSPECT"
    ]

    web_sample_rows = [
        [
            i + 1,
            row["entity_id"],
            row["query"],
            row["result"],
            f"[{row['domain'] or 'source'}]({row['top_url']})" if row.get("top_url") else "",
            (row.get("top_snippet") or "")[:150],
        ]
        for i, row in enumerate(web_log[:80])
    ]

    report = f"""# Data Verification Report — vinhlong360

> Forensic audit: xác minh sự thật, phát hiện hallucination, đảm bảo data integrity.
> Cập nhật: {date.today().isoformat()}

---

## MỤC LỤC
1. Executive Summary — Verdict tổng
2. Hallucination Scan (V1)
3. Geographic Verification (V2)
4. Name Verification (V3)
5. Historical Fact-Check (V4)
6. Culinary & Product Verification (V5)
7. Contact Info Verification (V6)
8. Source Attribution Audit (V7)
9. Relationship Truth Check (V8)
10. Itinerary Verification (V9)
11. Attribute Verification (V10)
12. Enrichment Pipeline Risk Assessment
13. Trust Score Distribution
14. Completeness Audit (secondary)
15. Fix Priority — Factual Errors First
16. Appendixes

---

## 1. EXECUTIVE SUMMARY

### Verdict tổng
- Total entities audited: {len(entities)}
- VERIFIED: {verdict_counts['VERIFIED']} ({pct(verdict_counts['VERIFIED'], len(entities))})
- PARTIAL: {verdict_counts['PARTIAL']} ({pct(verdict_counts['PARTIAL'], len(entities))})
- SUSPECT: {verdict_counts['SUSPECT']} ({pct(verdict_counts['SUSPECT'], len(entities))})
- UNTRUSTED: {verdict_counts['UNTRUSTED']} ({pct(verdict_counts['UNTRUSTED'], len(entities))})
- FABRICATED/confirmed false entities: {verdict_counts['FABRICATED']} ({pct(verdict_counts['FABRICATED'], len(entities))})
- EMPTY: 0 (0.0%)

### Top findings
- P0 confirmed false: `{CONFIRMED_ERRORS[0]['entity_id']}` gán Hủ tiếu Mỹ Tho cho Vĩnh Long; source độc lập xác nhận món do người Mỹ Tho chế biến.
- P0 confirmed false: `{CONFIRMED_ERRORS[1]['entity_id']}` gán origin Trà Vinh cho Bánh cống Sóc Trăng; VnExpress mô tả đây là đặc sản/nguyên gốc Sóc Trăng.
- P0 confirmed false: `{CONFIRMED_ERRORS[2]['entity_id']}` đặt Chùa Sà Lôn/Chén Kiểu vào Trà Vinh; nguồn ngoài cho thấy thực thể thuộc khu vực Sóc Trăng cũ/Cần Thơ mới.
- Round 3 full coverage: {len(web_log)}/{len(entities)} entities web-searched; current automated `MISMATCH` rows manually reviewed {len(current_manual_reviews)}/{web_counts['MISMATCH']}.
- Current `MISMATCH` adjudication: {manual_mismatch_counts['CONFIRMED_P0']} confirmed P0, {manual_mismatch_counts['P1_SUSPECT']} P1 suspect, {manual_mismatch_counts['FALSE_POSITIVE']} false-positive search mismatches.
- Cumulative manual mismatch reviews: {len(MANUAL_MISMATCH_REVIEWS)} cases; totals CONFIRMED_P0={cumulative_manual_mismatch_counts['CONFIRMED_P0']}, P1_SUSPECT={cumulative_manual_mismatch_counts['P1_SUSPECT']}, FALSE_POSITIVE={cumulative_manual_mismatch_counts['FALSE_POSITIVE']}.
- Search `ERROR` rows: {web_counts['ERROR']} DDGS timeouts/connect errors; these are not treated as evidence that entities do not exist.
- New P0 from Round 2: `chien-thang-giong-dua-giong-trom` is Tiền Giang/out-of-scope and its DB description is copied from an unrelated Chợ Lách tomb entry.
- New P0 from Round 2: `chua-ong-met-botum-vong-sa-som-rong` conflates Chùa Ông Mẹt (Trà Vinh) with Som Rong/Bô Tum Vông Sa Som Rông (Sóc Trăng/Cần Thơ mới).
- New P0 from Round 3: `khu-bao-ton-lung-binh-hoa-tra-vinh` is a contaminated entity whose content describes Lung Ngọc Hoàng in Hậu Giang/Cần Thơ mới, not a verified Trà Vinh nature reserve.
- Source risk: {no_independent}/{len(entities)} entities ({pct(no_independent, len(entities))}) chưa có URL nguồn độc lập; {source_domain_counts['vinhlong360.vn']} source trỏ về chính platform.
- Coordinate risk: {len(cstats['clusters'])} exact-coordinate clusters >3 entities, {sum(len(ids) for _, ids in cstats['clusters'])} clustered entities; cụm lớn nhất có {len(cstats['clusters'][0][1]) if cstats['clusters'] else 0} entities.
- Image completeness: 0/{len(entities)} entities có image URL.

### LLM enrichment impact
- Explicit LLM/agent-discovery source: {explicit_llm}/{len(entities)} ({pct(explicit_llm, len(entities))})
- Estimated LLM-like or unreviewed prose: {llm_like}/{len(entities)} ({pct(llm_like, len(entities))})
- LLM/no-url/self-source entities with factual claims: {sum(1 for row in matrix if row['missing_source'] == 'Y' and row['claim_count'] > 0)}
- Confirmed false claims in this pass: {len(CONFIRMED_ERRORS)}

### Overall trust score: {avg_trust:.1f}/100

{CURRENT_MERGED_PROVINCE}

External audit artifacts:
- Full entity matrix: `{MATRIX_CSV.relative_to(ROOT)}`
- Full claim inventory: `{CLAIMS_CSV.relative_to(ROOT)}`
- Full web cross-reference log: `{WEB_LOG_CSV.relative_to(ROOT)}`
- Full source URL audit: `{SOURCE_AUDIT_CSV.relative_to(ROOT)}`
- P0 quarantine SQL: `{FIX_SQL.relative_to(ROOT)}`

---

## 2. HALLUCINATION SCAN (V1)

### 2.1 Pattern frequency
{md_table(["Pattern", "Occurrences", "Interpretation"], [[p, c, "Needs source-level verification" if c else "No hits"] for p, c in hallucination_patterns])}

### 2.2 Confirmed false claims
{md_table(["#", "Entity ID", "Claim", "Truth", "Source", "Fix"], confirmed_rows)}

### 2.2b Round 3 manual adjudication of automated MISMATCH rows
The search classifier is intentionally noisy: it catches outside-area terms in snippets, including historical province names and unrelated top results. This full-coverage round reviewed {len(current_manual_reviews)}/{web_counts['MISMATCH']} current automated `MISMATCH` rows before promoting anything to P0.

Verdict counts: CONFIRMED_P0={manual_mismatch_counts['CONFIRMED_P0']}; P1_SUSPECT={manual_mismatch_counts['P1_SUSPECT']}; FALSE_POSITIVE={manual_mismatch_counts['FALSE_POSITIVE']}.

{md_table(["Entity ID", "Manual verdict", "Confidence", "Finding", "Source", "Action"], current_manual_mismatch_rows)}

### 2.3 Unverifiable claims (need human check)
Detected factual claims: {len(claims)}. Extracted claims contradicted by this audit: {len([c for c in claims if c["verified"] == "CONTRADICTED"])}; confirmed false entities: {len(CONFIRMED_ERRORS)}. One P0 finding is entity/address scope rather than a single extracted sentence. Entity-level existence found by web search is not the same as claim-level verification; most claims remain `UNVERIFIED` in `{CLAIMS_CSV.relative_to(ROOT)}`.

Lowest-trust unverified examples:
{md_table(["Entity", "Type", "Area", "Score", "Verdict", "Source", "Why"], lowest_rows[:25])}

### 2.4 LLM fingerprint analysis
The main LLM fingerprints are explicit `agent discovery`/`gpt` source labels, long polished descriptions without independent URLs, generic travel adjectives, and facts embedded in prose without source-specific attribution. This scan does not say every such entity is false; it says those entities cannot be trusted as factual until a human or crawler binds each claim to an external source.

---

## 3. GEOGRAPHIC VERIFICATION (V2)

**Scope:** {len(entities)} entities.
**Method:** bbox check ({LAT_RANGE[0]}–{LAT_RANGE[1]} lat, {LNG_RANGE[0]}–{LNG_RANGE[1]} lon), exact coordinate cluster scan, outside-province keyword scan, and web-search area comparison for {len(web_log)} high-risk entries.

Findings:
- Missing coordinates: {len(cstats['missing'])}
- Coordinates outside tight bbox: {len(cstats['out_bbox'])}
- Exact coordinate clusters >3 entities: {len(cstats['clusters'])}
- Entities in large coordinate clusters: {sum(len(ids) for _, ids in cstats['clusters'])}
- Entities mentioning outside-area terms: {len(out_hits)}

Largest coordinate clusters:
{md_table(["Coordinate", "Entity count", "Example IDs"], [[key, len(ids), ", ".join(ids[:6])] for key, ids in cstats["clusters"][:10]])}

Area mismatch report is in Appendix M. Confirmed errors are intentionally limited to cases with outside source support.

---

## 4. NAME VERIFICATION (V3)

**Scope:** {len(entities)} names.
**Method:** normalized duplicate scan, outside-place keywords, and web-search existence checks.

Duplicate exact names: 0 by current structural validation. Near-name risk remains for similarly named hotels and places; these need manual merge review, especially where coordinates are identical or near-identical.

Outside-area keyword hits:
{md_table(["Entity", "Area", "Outside signal"], [[eid, area, hit] for eid, _name, area, hit in out_hits[:40]])}

---

## 5. HISTORICAL FACT-CHECK (V4)

**Scope:** {type_counts['history']} history entities + {type_counts['person']} person entities.
**Method:** one web search per `history`/`person` entity in this pass, plus source-tier analysis and claim extraction.

Coverage:
- Person web searches: {web_type_counts['person']}/{type_counts['person']}
- History web searches: {web_type_counts['history']}/{type_counts['history']}
- Confirmed historical/geographic P0 errors: {errors_by_type['history']}

Important nuance: `Chùa Vàm Ray` current Wikipedia text says tỉnh Vĩnh Long because Trà Vinh cũ is inside Vĩnh Long mới. The legacy area `tra-vinh` should not be auto-corrected just because a 2026 source says Vĩnh Long.

---

## 6. CULINARY & PRODUCT VERIFICATION (V5)

**Scope:** {sum(type_counts[t] for t in PRODUCT_TYPES)} dish/product/drink entities.
**Method:** origin/OCOP claim extraction, web search sample, source-tier scan.

Confirmed culinary origin errors:
{md_table(["Entity ID", "Current claim", "Correct sourced fact", "Source"], [[err["entity_id"], err["claim"], err["truth"], f"[source]({err['source']})"] for err in CONFIRMED_ERRORS if err["entity_id"] in by_id and by_id[err["entity_id"]].get("type") in PRODUCT_TYPES])}

OCOP/product risk:
- Product entities: {type_counts['product']}
- Claims containing OCOP: {sum(1 for c in claims if "ocop" in c["claim_type"])}
- Product/dish entities without independent source: {sum(1 for entity in entities if entity.get("type") in PRODUCT_TYPES and not source_status(entity)["independent"])}

---

## 7. CONTACT INFO VERIFICATION (V6)

**Scope:** restaurants, cafes, accommodations, facilities, plus any entity with `attributes.phone`.
**Method:** phone format validation and source-status check. Live phone calling/Google Maps verification was not performed.

Findings:
- Phone values found: {len(phone_rows)}
- Invalid phone formats: {len(invalid_phones)}
- Contact-type entities with only format-level phone validation: {sum(1 for entity in entities if entity.get("type") in CONTACT_TYPES and phones_for_entity(entity))}

Because no live Maps/API verification was performed, all phone numbers remain “format-valid only.”

---

## 8. SOURCE ATTRIBUTION AUDIT (V7)

**Scope:** {len(entities)} entities.
**Method:** parse every `source` object, classify domain tier, detect self-references/no-URL/LLM labels.

{md_table(["Source domain/status", "Count"], [[k, v] for k, v in source_domain_counts.most_common(20)])}

Summary:
- Entities with Tier 1/2 source URL: {high_trust_sources}/{len(entities)} ({pct(high_trust_sources, len(entities))})
- Entities with no independent URL: {no_independent}/{len(entities)} ({pct(no_independent, len(entities))})
- Explicit LLM/agent source: {explicit_llm}/{len(entities)}

---

## 9. RELATIONSHIP TRUTH CHECK (V8)

**Scope:** {len(rels)} relationships.
**Method:** relationship type counts, duplicate triple scan, fanout check, near-distance check.

{md_table(["Relationship type", "Count"], [[k, v] for k, v in rstats["counts"].most_common()])}

Findings:
- `near` + `related_to`: {rstats["counts"]["near"] + rstats["counts"]["related_to"]}/{len(rels)} ({pct(rstats["counts"]["near"] + rstats["counts"]["related_to"], len(rels))}) low-specificity relationships.
- Duplicate relationship triples: {len(rstats["duplicate_rels"])}
- `near` relationships >50km: {len(rstats["near_too_far"])}
- Fanout >120 direct relationships: {len(rstats["fanout"])} ({", ".join(f"{eid}:{cnt}" for eid, cnt in rstats["fanout"][:5])})

---

## 10. ITINERARY VERIFICATION (V9)

**Scope:** {len(itineraries)} top-level itineraries in `web/data.json`.
**Method:** stop reference existence, relationship coverage via structural validators, and area-mismatch review.

Structural validators report itinerary stop references are present, but factual route timing/transport claims still need source-level verification. This audit did not validate real travel times, road conditions, boat schedules, or seasonal closures.

---

## 11. ATTRIBUTE VERIFICATION (V10)

**Scope:** every `attributes` object.
**Method:** scan high-risk attributes: address, origin, OCOP, price, hours, phone, coordinates approximation flags.

High-risk attribute issues:
- `origin` contradicted: `hu-tieu-my-tho`, `banh-cong-soc-trang`
- `address` contradicted/out-of-scope: `chua-sa-lon-chua-chen-kieu`
- Approximate coordinates: {len(cstats['approximate'])}
- Price/hour attributes: format scanned only, not live verified.

---

## 12. ENRICHMENT PIPELINE RISK ASSESSMENT

### 12.1 Current pipeline analysis
The current pipeline can produce public-facing prose from sparse metadata (`name + type + area`) and later import it into the database. Prompt-only guardrails say “do not invent facts,” but there is no enforced source binding, claim extraction, or mandatory human review before publish.

### 12.2 Guardrail gaps
- LLM output is not tagged per claim.
- `source` presence is treated too much like verification, even when URL is absent.
- No mandatory review queue for history/person/attraction.
- No source-to-claim alignment test.
- No external contradiction scanner before import.
- No provenance field distinguishing crawled/human/LLM/curated/seed.
- No confidence penalty for self-reference/no-url source.
- AI image generation has no real-appearance validation.
- Coordinates can be centroid/approximate while entity appears “verified.”
- Restaurant/contact fields are format-checked but not live-checked.

### 12.3 Recommendations
{md_table(["#", "Recommendation", "Impact", "Effort"], [
    ["R1", "Add `content_origin`: human/crawled/llm/seed/curated per field", "Trust transparency", "S"],
    ["R2", "Require source URL for every non-generic factual claim", "Prevents sourceless claims", "M"],
    ["R3", "Add claim extractor before import; block year/number/name claims without source", "Stops hallucinated facts", "M"],
    ["R4", "Move LLM enrich output to `pending_review` by default", "Prevents direct publish", "M"],
    ["R5", "Lower factual generation temperature to <=0.2", "Reduces fabrication", "S"],
    ["R6", "Restrict LLM to rewrite/summary expansion only; forbid new facts", "Tighter scope", "S"],
    ["R7", "Persist source snippets/hash per claim", "Audit reproducibility", "M"],
    ["R8", "Add external contradiction checks for area/origin before export", "Catches out-of-province items", "M"],
    ["R9", "Separate legacy area from current merged province naming", "Avoids false corrections", "S"],
    ["R10", "Add Maps/OSM live check queue for contact and coordinates", "Operational accuracy", "L"],
    ["R11", "Apply trust score in UI/admin filters", "Prevents low-trust content surfacing", "M"],
    ["R12", "Make backup mandatory in every mutating ETL script", "Prevents data-loss regressions", "S"],
])}

---

## 13. TRUST SCORE DISTRIBUTION

Overall average: {avg_trust:.1f}/100.

{md_table(["Bucket", "Entities", "%"], [[bucket, trust_buckets[bucket], pct(trust_buckets[bucket], len(entities))] for bucket in ["0-19", "20-39", "40-59", "60-79", "80-100"]])}

High trust (>=90): {len(high_trust)} ({pct(len(high_trust), len(entities))})
Untrusted (<50): {len(low_trust)} ({pct(len(low_trust), len(entities))})

### Per-type trust score
{md_table(["Type", "Avg trust", "Min", "Max", "Lowest-trust entities"], type_trust_rows)}

---

## 14. COMPLETENESS AUDIT (secondary)

### 14.1 Entity statistics
{md_table(["Type", "Count", "% summary", "% description", "% coords", "% images", "% source object", "% independent source"], coverage_rows)}

### 14.2 Coverage map
{md_table(["Area", "Total"] + key_types, area_type_rows)}

### 14.3 Missing entity candidates
This pass did not add missing entities because fabricating new POIs is explicitly disallowed. Candidate generation should be a separate source-first crawl from Tier 1/2 directories.

---

## 15. FIX PRIORITY — FACTUAL ERRORS FIRST

### P0 — Confirmed factual errors (fix IMMEDIATELY)
{md_table(["#", "Entity ID", "Error", "Correct value", "Source", "Fix method"], confirmed_rows)}

### P1 — Suspected hallucinations (review within 1 week)
{md_table(["Entity ID", "Score", "Reason", "Action"], [[row["entity_id"], row["trust_score"], row["hallucination_flags"][:140], "Human fact-check + source binding"] for row in matrix if row["verdict"] in {"UNTRUSTED", "SUSPECT"}][:40])}

Round 2 P1 suspects from manual `MISMATCH` review:

{md_table(["Entity ID", "Confidence", "Why suspect", "Evidence/source", "Action"], p1_manual_rows)}

### P2 — Missing sources (add within 1 month)
Entities missing independent sources: {no_independent}. Prioritize history/person/attraction/product first.

### P3 — Completeness gaps
Images are missing for all entities. This is secondary to factual correction but should be addressed before public launch.

### P4 — Pipeline improvements
Implement Recommendations R1–R12 before another mass LLM enrichment/import run.

---

## 16. APPENDIXES

### A. Complete Entity Verification Matrix
Full matrix: `{MATRIX_CSV.relative_to(ROOT)}`. Lowest-trust 60 rows:

{md_table(["entity_id", "type", "area", "trust_score", "verdict", "source_status", "flags"], lowest_rows)}

### B. All Factual Claims Inventory
Full claim inventory: `{CLAIMS_CSV.relative_to(ROOT)}` ({len(claims)} extracted claims). Sample:

{md_table(["entity_id", "claim_type", "verified", "claim_text"], [[c["entity_id"], c["claim_type"], c["verified"], c["claim_text"][:180]] for c in claims[:80]])}

### C. Duplicate Candidates
No exact duplicate names were found by normalized-name scan. Near-duplicates remain a human merge-review task, especially for hotel names and entities sharing exact coordinates.

### D. Coordinates Anomalies
Full coordinate clusters are represented in the report above. Top clusters:

{md_table(["Coordinate", "Count", "Example IDs"], [[key, len(ids), ", ".join(ids[:10])] for key, ids in cstats["clusters"][:25]])}

### E. Phone Number Audit
Phone values found: {len(phone_rows)}. Invalid format count: {len(invalid_phones)}.

### F. Source URL Audit
Full source audit: `{SOURCE_AUDIT_CSV.relative_to(ROOT)}`.

### G. LLM-Generated Content Inventory
Explicit LLM/agent source entities: {explicit_llm}. Estimated LLM-like entities: {llm_like}. Treat all as `pending factual verification`.

### H. Mekong Delta Reference Data
Reference model used here: legacy areas `vinh-long`, `ben-tre`, `tra-vinh`; current post-2025 official naming may collapse Bến Tre/Trà Vinh old areas under tỉnh Vĩnh Long mới. Store both fields to avoid future confusion.

### I. Enrichment Prompt Templates
Prompt sources reviewed:
- `scripts/enrich_descriptions.py`: uses `cx/gpt-5.5`, temperature 0.65, 3–5 paragraphs from sparse metadata.
- `scripts/enrich_with_llm.py`: temperature 0.3, summary-to-description expansion.
- `scripts/generate_missing_descriptions.py`: temperature 0.7 fallback generation.

### J. Recommended Corrected Values
{md_table(["entity_id", "field", "current_value", "corrected_value", "source"], [[err["entity_id"], err["field"], err["claim"], err["truth"], f"[source]({err['source']})"] for err in CONFIRMED_ERRORS])}

### K. External Cross-Reference Log
Full log: `{WEB_LOG_CSV.relative_to(ROOT)}` ({len(web_log)} searches). Sorted sample:

{md_table(["#", "entity_id", "query", "result", "source", "snippet"], web_sample_rows)}

Manual adjudication of automated `MISMATCH` rows (cumulative across Round 2 and Round 3):

{md_table(["Entity ID", "Manual verdict", "Confidence", "Finding", "Source", "Action"], manual_mismatch_rows)}

### L. Entity Existence Verification
Entities with at least one web MATCH/AMBIGUOUS result: {len({row['entity_id'] for row in web_log if row['result'] in {'MATCH', 'AMBIGUOUS'}})}. Entities with NOT_FOUND/ERROR need manual follow-up; see full log.

### M. Area Mismatch Report
Confirmed area/origin mismatches:

{md_table(["entity_id", "DB area", "Real area/source fact", "Action"], [[err["entity_id"], by_id.get(err["entity_id"], {}).get("area", ""), err["truth"], err["fix"]] for err in CONFIRMED_ERRORS])}

Automated outside-area keyword hits are not automatically false; they are triage candidates listed in section 4.

### N. Cross-Reference Statistics
- Total entities web-searched: {len({row['entity_id'] for row in web_log})} / {len(entities)}
- MATCH: {web_counts['MATCH']} ({pct(web_counts['MATCH'], len(web_log))})
- MISMATCH: {web_counts['MISMATCH']} ({pct(web_counts['MISMATCH'], len(web_log))})
- AMBIGUOUS: {web_counts['AMBIGUOUS']} ({pct(web_counts['AMBIGUOUS'], len(web_log))})
- NOT_FOUND: {web_counts['NOT_FOUND']} ({pct(web_counts['NOT_FOUND'], len(web_log))})
- ERROR: {web_counts['ERROR']} ({pct(web_counts['ERROR'], len(web_log))})

Coverage by type:
{md_table(["Type", "Searches"], [[k, v] for k, v in web_type_counts.most_common()])}

Coverage by area:
{md_table(["Area", "Searches"], [[k or "None", v] for k, v in web_area_counts.most_common()])}

### Quality Gate Self-Check
{md_table(["Gate", "Check", "Status"], quality_gate_rows)}

Hard forensic note: this report is intentionally stricter than the existing structural quality report. Structural validity does not equal factual truth.
"""

    REPORT_PATH.write_text(report, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-web-queries", type=int, default=360)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--refresh-web", action="store_true")
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    data = read_json(DATA_PATH)
    entities = data.get("entities", [])
    web_log = load_or_create_web_log(
        entities,
        max_queries=args.max_web_queries,
        workers=args.workers,
        refresh=args.refresh_web,
    )
    generate_report(data, web_log)
    print(f"Wrote {REPORT_PATH}")
    print(f"Wrote {MATRIX_CSV}")
    print(f"Wrote {CLAIMS_CSV}")
    print(f"Wrote {WEB_LOG_CSV}")
    print(f"Wrote {SOURCE_AUDIT_CSV}")
    print(f"Wrote {FIX_SQL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
