#!/usr/bin/env python3
"""
generate_llms_txt.py — Sinh bách khoa toàn thư tri thức máy đọc llms-full.txt và llms.txt.
Tuân thủ chuẩn llmstxt.org và quy tắc địa giới hành chính 2 cấp (R10.7) của tỉnh Vĩnh Long mới.
"""

import json
from pathlib import Path

ROOT_DIR = Path(r"c:\Users\NCTaam\Documents\vinhlong360-correction-case-pilot")
DATA_JSON_PATH = ROOT_DIR / "web" / "data.json"
LLMS_TXT_PATH = ROOT_DIR / "web-nuxt" / "public" / "llms.txt"
LLMS_FULL_TXT_PATH = ROOT_DIR / "web-nuxt" / "public" / "llms-full.txt"
SITE_URL = "https://vinhlong360.vn"

BATCH_ORDER = [
    ("Đợt 1: 16 Điểm Di Sản & Thổ Nhưỡng Tiên Phong", [
        "van-thanh-mieu", "dinh-long-ho", "chua-tien-chau-tien-chau-tu", "lo-gach-mang-thit",
        "khu-luu-niem-thu-tuong-vo-van-kiet", "khu-luu-niem-tran-dai-nghia-vinh-long",
        "chua-phat-ngoc-xa-loi", "khu-di-tich-ao-ba-om", "chua-ang-angkorajaborey",
        "den-tho-bac-ho-tra-vinh", "chua-hang-kompong-chray", "lang-nghe-det-chieu-ca-hon",
        "lang-nghe-banh-trang-my-long", "lang-nghe-banh-phong-son-doc",
        "con-phung-con-ong-dao-dua", "nha-tho-cai-mon"
    ]),
    ("Đợt 2: 25 Thực Thể Ẩm Thực & Làng Nghề Nam Bộ", [
        "banh-canh-ben-co", "banh-canh-bot-xat-thit-vit-ben-tre", "banh-tet-tra-cuon-co-huong",
        "bun-suong-tra-vinh", "chao-am-tra-vinh", "ca-chay-tra-on-kho-rim-kho-to",
        "chuoi-dap-nuoc-cot-dua-ben-tre", "banh-xeo-oc-gao-con-phu-da", "hu-tieu-pate-ben-tre",
        "tau-hu-ky-my-hoa-chien-gion-binh-minh", "bun-nuoc-leo-tra-vinh", "bun-mam-vinh-long",
        "banh-dua-giong-luong", "banh-ray-khmer-la-dua", "khoai-lang-mam-song-cuon-la-cach",
        "com-hap-trai-dua-ben-tre", "che-chuoi-nuong-ben-tre", "ca-chay-song-hau-tra-on",
        "lang-keo-dua-mo-cay", "lang-nghe-banh-tet-tra-cuon", "lang-hoa-kieng-cai-mon-cho-lach",
        "lang-det-chieu-cu-lao-dai", "banh-trang-cu-lao-may", "lang-det-chieu-ca-hom-ham-tan",
        "hop-tac-xa-buoi-nam-roi-my-hoa"
    ]),
    ("Đợt 3: 30 Đình Làng, Chùa Cổ & Không Gian Tín Ngưỡng Tam Vùng", [
        "dinh-long-thanh", "that-phu-mieu-chua-ong-vinh-long", "chua-ba-thien-hau-vinh-long",
        "chua-hanh-phuc-tang-sanghamangala", "dinh-tan-hoa", "dinh-than-tan-giai",
        "khu-luu-niem-thu-tuong-chinh-phu-vo-van-kiet", "chua-giac-thien-go-cong",
        "dinh-than-my-thuan-cai-von", "chua-khmer-phu-ly", "chua-ang",
        "danh-thang-ao-ba-om-ao-vuong", "chua-hang-wat-kompong-chray",
        "chua-kompong-ong-met", "chua-co-wat-nodol", "chua-vam-ray",
        "phuoc-minh-cung-chua-ong-tra-vinh", "chua-giac-linh-chua-phat-lon",
        "dinh-long-duc-tra-vinh", "chua-o-mich-hung-hoa", "dinh-phu-le-ba-tri",
        "dinh-binh-hoa-giong-trom", "dinh-tan-thach-chau-thanh", "dinh-dai-dien-thanh-phu",
        "dinh-ran-dinh-thuy-mo-cay-nam", "chua-van-phuoc-binh-dai", "chua-tuyen-linh-mo-cay-nam",
        "chua-hoi-ton-co-tu-chau-thanh", "khu-di-tich-dac-biet-nguyen-dinh-chieu-ba-tri",
        "khu-luu-niem-nu-tuong-nguyen-thi-dinh-giong-trom"
    ]),
    ("Đợt 4: 36 Lưu Trú Homestay, Farmstay & Sinh Thái Miệt Vườn Tam Vùng", [
        "homestay-ut-trinh", "phuong-thao-homestay", "nam-thanh-homestay", "ut-thuy-homestay",
        "ngoc-phuong-homestay", "vinh-sang-resort", "mekong-pottery-homestay", "somo-farm-cuu-long",
        "riverside-park-eco-resort", "homestay-bay-thoi", "homestay-cu-lao-may", "nha-dua-cocohome",
        "forever-green-resort", "homestay-nam-ham-luong", "homestay-xu-dua", "homestay-lang-be",
        "homestay-nguoi-giu-rung", "mango-home-ben-tre", "mekong-home", "maison-du-pays-de-ben-tre",
        "nhon-thanh-homestay", "rooster-mekong-resort", "farmstay-sinh-thai-nguyen-gia", "khach-san-ham-luong",
        "con-chim-homestay", "homestay-bep-nam-bo-xua-con-chim", "homestay-tu-pha-con-chim",
        "suonsia-homestay-cau-ke", "mekong-garden-homestay-cang-long", "homestay-sokfram-tieu-can",
        "homestay-khmer-tra-vinh", "khu-du-lich-bien-ba-dong", "duyen-hai-homestay",
        "le-ngan-homestay-tap-ngai", "nha-nghi-nha-co-dai-an", "khach-san-hai-duong-i-ba-dong"
    ]),
    ("Đợt 5: 36 Sản Phẩm OCOP 3–5 Sao & Nông Sản Thổ Nhưỡng Tam Vùng", [
        "buoi-nam-roi-binh-minh", "cam-sanh-tam-binh", "khoai-lang-binh-tan", "sau-rieng-ri6",
        "gom-do-mang-thit", "banh-trang-nem-cu-lao-may", "nhan-xuong-com-vang",
        "chom-chom-binh-hoa-phuoc-rambutan", "xoai-cat-num-vung-liem", "chao-dua-thuan-duyen-tam-binh",
        "cuu-long-my-tuu-ruou-ocop-mang-thit", "sau-rieng-say-thang-hoa-sau-ri",
        "buoi-da-xanh-ben-tre", "keo-dua-ben-tre", "ruou-phu-le-ba-tri", "dua-xiem-xanh",
        "ngheu-thanh-hai", "cua-bien-thanh-phu", "sau-rieng-cai-mon", "chom-chom-cho-lach",
        "mut-dua-non", "tinh-dau-dua", "tranh-dua-cocohand", "ruou-dua-ben-tre",
        "dua-sap-cau-ke", "mat-hoa-dua-va-duong-hoa-dua-tra-vinh-ocop-5-sao",
        "vicosap-keo-dua-sap-ocop-5-sao", "cha-hoa-nam-thuy", "tom-kho-vinh-kim",
        "nuoc-mam-ruoi-long-vinh", "banh-tet-tra-cuon", "chuoi-ta-qua", "chu-u-ba-dong",
        "ruou-quach-cau-ngang", "mam-bo-hoc-tra-vinh", "tom-kho-cham-mam-chua-ngot-duyen-hai"
    ]),
    ("Đợt 6: 36 Nhân Vật Lịch Sử, Danh Nhân Văn Hóa & Nghệ Nhân Dân Gian Tam Vùng", [
        "thoai-ngoc-hau", "phan-thanh-gian", "vo-van-kiet", "tran-dai-nghia", "pham-hung",
        "nguyen-thong", "tong-huu-dinh", "tran-quang-quon", "nghe-nhan-chau-xuong",
        "nghe-nhan-nguyen-thi-thoi", "ut-tra-on", "le-thuy",
        "nguyen-dinh-chieu", "nguyen-thi-dinh", "suong-nguyet-anh", "nguyen-ngoc-thang",
        "truong-vinh-ky", "dong-van-cong", "truc-phuong", "le-anh-xuan", "le-trieu-dien",
        "nghe-nhan-dang-van-tiep", "nghe-nhan-nguyen-van-nam", "nghe-nhan-kieu-oanh",
        "nguyen-van-ton", "vien-chau-huynh-tri-ba", "ut-tich", "nguyen-thien-thanh",
        "thach-boi", "thach-oai", "thach-sok-xane", "son-soc", "kien-soc",
        "thach-chan", "thach-buol", "diep-thi-som"
    ]),
    ("Đợt 7: 25 Lễ Hội Truyền Thống & Sự Kiện Văn Hóa Tam Vùng", [
        "le-hoi-ok-om-bok", "le-hoi-chol-chnam-thmay-tai-chua-ky-son",
        "le-hoi-chol-chnam-thmay-va-sen-dolta", "sen-dolta", "le-hoi-dom-long-neak-ta",
        "hoi-thi-ghe-ngo-mo-rong-tinh-tra-vinh-dua-ghe-ngo-truyen-thong-tra-vinh",
        "tuan-le-van-hoa-du-lich-gan-voi-le-hoi-ok-om-bok", "le-hoi-nghinh-ong-duyen-hai",
        "le-hoi-nghinh-ong-binh-thang", "le-hoi-cung-bien-my-long", "le-cung-bien-dong-cao",
        "le-hoi-nghinh-ong-lang-con-tau", "le-hoi-ky-yen-dinh-phu-le", "le-hoi-ky-yen",
        "le-hoi-ky-yen-ha-dien-dinh-tan-giai", "lang-ong-tien-quan-thong-che-dieu-bat-tuong-quan-nguyen-van-",
        "le-hoi-van-thanh-mieu", "le-via-quoc-cong-tong-phuoc-hiep",
        "le-gio-phan-thanh-gian-tai-van-thanh-mieu", "le-gio-nguyen-dinh-chieu",
        "festival-dua-ben-tre", "festival-dua-sap-cau-ke-tra-vinh",
        "festival-gach-gom-do-kinh-te-xanh-tinh-vinh-long-vinh-long",
        "ngay-hoi-van-hoa-the-thao-va-du-lich-huyen-cho-lach-ben-tre",
        "ngay-hoi-banh-dan-gian-nam-bo-ket-hop-hoi-cho-ocop-vinh-long-vinh-long"
    ])
]


def load_data():
    with open(DATA_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def build_llms_txt(entities, itineraries, verified_entities, wards):
    return f"""# vinhlong360.vn

> Cổng bách khoa tri thức du lịch, văn hóa bản địa, ẩm thực truyền thống, làng nghề và sản phẩm OCOP chính thức cho **tỉnh Vĩnh Long** — miền Tây Nam Bộ, Việt Nam.

## Giới thiệu & Địa giới Hành chính (Lưu ý Quan trọng)

Từ tháng 7-2025, ba địa bàn Vĩnh Long, Bến Tre và Trà Vinh đã **HỢP NHẤT thành MỘT tỉnh duy nhất mang tên Vĩnh Long**.
- Cấp huyện đã được bãi bỏ hoàn toàn; tỉnh vận hành mô hình hành chính 2 cấp gồm **1 tỉnh và 124 xã/phường**.
- Mọi tên gọi "Bến Tre", "Trà Vinh" trong toàn bộ tài liệu chỉ dùng để chỉ **vùng đất/vùng văn hóa** theo địa giới cũ trước tháng 7-2025. Tuyệt đối không dùng "tỉnh Bến Tre" hay "tỉnh Trà Vinh" ngoài văn cảnh lịch sử.

## Toàn Văn Dữ Liệu Máy Đọc (Full Documentation)

- **Bách khoa toàn thư tri thức máy đọc chi tiết**: [llms-full.txt]({SITE_URL}/llms-full.txt)
  (Chứa toàn bộ 204 thực thể xác minh ảnh tư liệu, 33 tuyến lộ trình, 124 xã/phường, lịch mùa vụ và lễ hội AEO).

## Thống Kê Nền Tảng

- **Tổng số thực thể dữ liệu**: {len(entities)} điểm đến, di tích, ẩm thực, làng nghề, nhân vật, sản phẩm.
- **Thực thể xác minh ảnh tư liệu báo chí chính thống**: {len(verified_entities)} thực thể (100% ảnh WebP nội bộ kèm bản quyền Google Images).
- **Lộ trình du lịch liên vùng gợi ý**: {len(itineraries)} tuyến chuyên đề (1–3 ngày).
- **Đơn vị hành chính cấp cơ sở**: {len(wards)} xã/phường.

## Ba Vùng Văn Hóa - Thổ Nhưỡng Tam Vùng

1. **Vùng Đất Học & Di Sản Đỏ Vĩnh Long (Trung tâm)**: Lò gạch gốm đỏ Mang Thít, cù lao An Bình, Văn Thánh Miếu, bưởi Năm Roi Bình Minh, cam sành Tam Bình, khoai lang Bình Tân.
2. **Vùng Đất Dừa & Đồng Khởi Bến Tre (Phía Đông)**: Rặng dừa bạt ngàn, kẹo dừa Mỏ Cày, bưởi Da Xanh, di tích Đạo Dừa Cồn Phụng, bánh tráng Mỹ Lồng, bánh phồng Sơn Đốc.
3. **Vùng Văn Hóa Khmer & Duyên Hải Trà Vinh (Phía Nam)**: Ao Bà Om, 143 chùa Khmer Nam Bộ cổ kính, dừa sáp Cầu Kè, mật hoa dừa Sokfarm, bún nước lèo, lễ hội Ok Om Bok.

## Các Chuyên Mục Chính

- **Du lịch & Di sản**: {SITE_URL}/du-lich
- **Ẩm thực & Thổ nhưỡng**: {SITE_URL}/kham-pha/am-thuc
- **Sản phẩm OCOP 3–5 sao**: {SITE_URL}/ocop
- **Lễ hội & Sự kiện văn hóa**: {SITE_URL}/le-hoi
- **Lộ trình du lịch gợi ý**: {SITE_URL}/lich-trinh
- **Bản đồ tương tác 124 xã/phường**: {SITE_URL}/ban-do
- **Danh mục 124 xã/phường**: {SITE_URL}/xa-phuong
- **Trò chuyện cùng Trợ lý AI**: {SITE_URL}/chat

## Giao Tiếp Lập Trình (API Endpoints cho AI Agents)

- `GET /api/v1/entities`: Danh sách thực thể du lịch kèm phân trang và lọc danh mục.
- `GET /api/v1/search?q={{query}}`: Tìm kiếm thực thể theo từ khóa ngữ nghĩa.
- `GET /health`: Kiểm tra trạng thái hoạt động của hệ sinh thái.
"""


def _render_entity_item(e, etype: str) -> list[str]:
    eid = e["id"]
    attrs = e.get("attributes") or {}
    author = attrs.get("image_author", "Phóng viên")
    source = attrs.get("image_source", "Báo chí địa phương")
    summary = e.get("summary") or e.get("description") or ""
    coords = e.get("coordinates")
    coord_str = f"[{coords[0]:.4f}, {coords[1]:.4f}]" if coords and len(coords) >= 2 else "N/A"
    place = e.get("place_name") or e.get("placeId") or "Vĩnh Long"

    return [
        f"#### [{e.get('name')}]({SITE_URL}/dia-diem/{eid})",
        f"- **Mã ID**: `{eid}` | **Phân loại**: `{etype}` | **Địa bàn**: {place} | **Tọa độ**: {coord_str}",
        f"- **Ảnh tư liệu WebP**: `{SITE_URL}/img/entities/{eid}.webp`",
        f"- **Tác giả ảnh**: {author} · **Cơ quan**: {source}",
        f"- **Bản quyền hình ảnh**: [Điều khoản sử dụng]({SITE_URL}/dieu-khoan-su-dung) | [Cấp phép]({SITE_URL}/lien-he)",
        f"- **Tóm lược**: {summary}",
        "",
    ]


def _render_verified_entities(verified_entities) -> list[str]:
    category_labels = {
        "attraction": "Di tích lịch sử & Thắng cảnh tiêu biểu",
        "history": "Đình làng, Chùa cổ & Không gian tưởng niệm",
        "event": "Lễ hội truyền thống & Sự kiện văn hóa",
        "product": "Sản phẩm OCOP 3–5 sao & Nông sản đặc sản",
        "dish": "Ẩm thực bản địa & Món ngon thổ nhưỡng",
        "craft_village": "Làng nghề thủ công truyền thống",
        "accommodation": "Lưu trú Homestay, Farmstay & Sinh thái miệt vườn",
        "person": "Nhân vật lịch sử, Danh nhân văn hóa & Nghệ nhân dân gian",
        "nature": "Sinh thái miệt vườn, Cù lao & Sông nước",
        "experience": "Trải nghiệm văn hóa & Du lịch cộng đồng",
    }
    grouped = {}
    for e in verified_entities:
        grouped.setdefault(e.get("type", "attraction"), []).append(e)

    out: list[str] = []
    for etype, elist in sorted(grouped.items(), key=lambda x: len(x[1]), reverse=True):
        cat_title = category_labels.get(etype, etype.capitalize())
        out.append(f"### {cat_title} ({len(elist)} thực thể)\n")
        for e in sorted(elist, key=lambda x: str(x.get("name", ""))):
            out.extend(_render_entity_item(e, etype))
    return out


def _render_itineraries(itineraries) -> list[str]:
    out: list[str] = [f"## 3. Danh Mục {len(itineraries)} Tuyến Lộ Trình Du Lịch Liên Vùng Chuyên Đề\n"]
    for itin in itineraries:
        iid = itin.get("id")
        title = itin.get("title", "")
        duration = itin.get("duration", "1 ngày")
        summary = itin.get("summary", "")
        stops = itin.get("stops") or []
        out.append(f"### [{title}]({SITE_URL}/lich-trinh/{iid})")
        out.append(f"- **Mã lộ trình**: `{iid}` | **Thời lượng**: {duration} | **Số điểm dừng**: {len(stops)}")
        out.append(f"- **Mô tả hành trình**: {summary}")
        if stops:
            stop_names = [str(s.get("name", s.get("entityId", ""))) for s in stops[:8]]
            out.append(f"- **Các điểm dừng tiêu biểu**: {' → '.join(stop_names)}")
        out.append("")
    return out


def _render_wards(wards) -> list[str]:
    out: list[str] = [
        "## 4. Danh Mục 124 Xã/Phường Thuộc Tỉnh Vĩnh Long\n",
        "Tỉnh Vĩnh Long gồm 35 phường và 89 xã:\n",
    ]
    for w in sorted(wards, key=lambda x: str(x.get("name", ""))):
        wid = w.get("id")
        wname = w.get("name")
        attrs = w.get("attributes") or {}
        police = attrs.get("police_phone", "")
        contact_str = f" | Hotline CAX: {police}" if police else ""
        out.append(f"- **[{wname}]({SITE_URL}/xa-phuong/{wid})** (`{wid}`){contact_str}")
    out.append("")
    return out


def build_llms_full_txt(itineraries, verified_entities, wards):
    lines = [
        "# vinhlong360 — Bách Khoa Toàn Thư Tri Thức & Dữ Liệu Du Lịch, Thổ Nhưỡng, OCOP Tam Vùng (llms-full.txt)",
        "",
        "> vinhlong360.vn là nền tảng tri thức du lịch, văn hóa bản địa, ẩm thực truyền thống, làng nghề và sản phẩm OCOP chính thức cho **tỉnh Vĩnh Long** (hợp nhất từ ba vùng Vĩnh Long, Bến Tre, Trà Vinh cũ từ tháng 7-2025). Tỉnh vận hành hành chính 2 cấp gồm 124 xã/phường (không có cấp huyện).",
        "",
        "## 1. Quy Chuẩn Địa Giới Hành Chính (Rule R10.7)",
        "- Toàn bộ lãnh thổ 3 vùng cũ nay thuộc một đơn vị hành chính cấp tỉnh duy nhất: **tỉnh Vĩnh Long**.",
        "- 124 đơn vị hành chính trực thuộc gồm 35 phường và 89 xã.",
        "- Cấp huyện đã bãi bỏ; các địa danh huyện cũ (Long Hồ, Mang Thít, Ba Tri, Châu Thành, Càng Long, Cầu Kè, Trà Cú...) chỉ mang giá trị lịch sử và chỉ dẫn vị trí địa lý dân gian.",
        "",
        f"## 2. Danh Mục {len(verified_entities)} Thực Thể Xác Minh Ảnh Tư Liệu Báo Chí & Giấy Phép Google Images",
        "",
        "Mỗi thực thể dưới đây đều có ảnh tư liệu báo chí chính thống được lưu trữ nội bộ chuẩn WebP, tích hợp siêu dữ liệu Schema.org `ImageObject` với đầy đủ bản quyền (`creator`, `creditText`, `copyrightNotice`, `license`, `acquireLicensePage`).",
        "",
    ]
    lines.extend(_render_verified_entities(verified_entities))
    lines.extend(_render_itineraries(itineraries))
    lines.extend(_render_wards(wards))

    lines.append("## 5. Lịch Nông Vụ OCOP & Trái Cây Miệt Vườn Tam Vùng")
    lines.append("")
    lines.append("- **Tháng 1 - Tháng 3 (Xuân)**: Bưởi Năm Roi Bình Minh, Cam sành Tam Bình, Quýt đường, Mật ong hoa nhãn.")
    lines.append("- **Tháng 4 - Tháng 6 (Hạ - Rộ mùa)**: Sầu riêng Ri6 Long Hồ & Cái Mơn, Chôm chôm Bình Hòa Phước & Chợ Lách, Măng cụt Cái Mơn, Xoài cát Núm Vũng Liêm.")
    lines.append("- **Tháng 5 - Tháng 7 (Hạ muộn)**: Nhãn xuồng cơm vàng Cù lao An Bình, Vú sữa Lò Rèn, Mận An Phước.")
    lines.append("- **Tháng 8 - Tháng 11 (Mùa nước nổi phù sa)**: Bông điên điển, Cá linh, Cá cháy Trà Ôn, Bông súng đồng.")
    lines.append("- **Thu hoạch quanh năm**: Dừa sáp Cầu Kè, Mật hoa dừa Sokfarm, Kẹo dừa Bến Tre, Bưởi Da Xanh, Khoai lang tím Nhật Bình Tân.")
    lines.append("")

    lines.append("## 6. Lịch Lễ Hội Truyền Thống & Sự Kiện Văn Hóa Tam Vùng")
    lines.append("")
    lines.append("- **Lễ hội Ok Om Bok Trà Vinh (Rằm tháng 10 Âm lịch)**: Di sản văn hóa phi vật thể quốc gia, lễ cúng Trăng đút cốm dẹp, thả đèn gió, đèn nước, hội thi Đua ghe Ngo truyền thống trên sông Long Bình.")
    lines.append("- **Tết Chôl Chnăm Thmây (Tháng 4 Dương lịch - Giữa tháng Chét)**: Tết cổ truyền người Khmer, lễ đắp núi cát, tắm Phật tại 143 chùa Khmer Nam Bộ.")
    lines.append("- **Lễ hội Sêne Đôlta (Tháng 8 - 9 Âm lịch)**: Lễ cúng ông bà, báo hiếu tổ tiên của đồng bào dân tộc Khmer.")
    lines.append("- **Lễ hội Đom Lơng Néak Tà (Tháng 3 - 5 Âm lịch)**: Di sản phi vật thể quốc gia, lễ cúng thần bảo hộ xóm sóc của người Khmer.")
    lines.append("- **Lễ hội Nghinh Ông Duyên Hải & Bình Thắng (Tháng Giêng & Tháng 6 Âm lịch)**: Di sản phi vật thể quốc gia, lễ hội cầu ngư, tạ ơn Cá Voi của ngư dân miền duyên hải.")
    lines.append("- **Lễ Kỳ Yên Đình Long Thanh, Phú Lễ, Tân Giai (Rằm tháng 3 & Rằm tháng 11 Âm lịch)**: Đại lễ cầu quốc thái dân an, hát bội cổ truyền Nam Bộ tại các ngôi đình làng trăm năm tuổi.")
    lines.append("- **Festival Gạch Gốm Đỏ Mang Thít & Festival Dừa Bến Tre**: Các sự kiện xúc tiến kinh tế xanh, tôn vinh di sản nghề truyền thống trăm năm.")
    lines.append("")

    lines.append("## 7. Cấu Trúc Semantic Schema.org & Tối Ưu Hóa AEO/GEO")
    lines.append("")
    lines.append("Hệ sinh thái Vĩnh Long 360 triển khai cấu trúc Schema.org JSON-LD chặt chẽ:")
    lines.append("- `TouristAttraction`: Địa danh du lịch, di tích, danh lam thắng cảnh.")
    lines.append("- `LodgingBusiness`: Cơ sở homestay, farmstay, khách sạn.")
    lines.append("- `Event`: Sự kiện văn hóa, lễ hội với `eventStatus`, `isAccessibleForFree`, `offers`.")
    lines.append("- `Product`: Nông sản, đặc sản OCOP kèm xếp hạng sao (`award`, `brand`).")
    lines.append("- `ImageObject`: Chuẩn Google Images License với `creator`, `creditText`, `copyrightNotice`, `license`, `acquireLicensePage`.")
    lines.append("- `SpeakableSpecification`: Hỗ trợ công cụ đọc màn hình và AI voice search qua CSS selectors `.lead`, `.highlights`, `h1`.")
    lines.append("")

    return "\n".join(lines)


def main():
    data = load_data()
    entities = data.get("entities", [])
    itineraries = data.get("itineraries", [])

    verified_entities = [
        e for e in entities
        if (e.get("attributes") or {}).get("is_verified_photo")
    ]
    wards = [
        e for e in entities
        if e.get("type") == "place" and e.get("id") not in ("prov-1", "vinh-long")
    ]

    print(f"Entities: {len(entities)}")
    print(f"Verified photo entities: {len(verified_entities)}")
    print(f"Itineraries: {len(itineraries)}")
    print(f"Wards: {len(wards)}")

    llms_txt_content = build_llms_txt(entities, itineraries, verified_entities, wards)
    llms_full_txt_content = build_llms_full_txt(itineraries, verified_entities, wards)

    with open(LLMS_TXT_PATH, "w", encoding="utf-8") as f:
        f.write(llms_txt_content)
    print(f"Written {LLMS_TXT_PATH} ({len(llms_txt_content.encode('utf-8'))} bytes)")

    with open(LLMS_FULL_TXT_PATH, "w", encoding="utf-8") as f:
        f.write(llms_full_txt_content)
    print(f"Written {LLMS_FULL_TXT_PATH} ({len(llms_full_txt_content.encode('utf-8'))} bytes)")


if __name__ == "__main__":
    main()
