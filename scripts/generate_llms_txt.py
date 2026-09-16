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


def load_data():
    with open(DATA_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def sanitize_historical(text: str) -> str:
    return (
        text.replace("tỉnh Bến Tre", "tỉnh Bến Tre cũ")
        .replace("tỉnh Trà Vinh", "tỉnh Trà Vinh cũ")
    )


def format_entity_block(e: dict) -> list:
    eid = e["id"]
    attrs = e.get("attributes") or {}
    author = attrs.get("image_author", "Phóng viên")
    source = attrs.get("image_source", "Báo chí địa phương")
    summary = sanitize_historical(e.get("summary") or e.get("description") or "")
    coords = e.get("coordinates")
    coord_str = f"[{coords[0]:.4f}, {coords[1]:.4f}]" if coords and len(coords) >= 2 else "N/A"
    place = e.get("place_name") or e.get("placeId") or "Vĩnh Long"
    entity_type = e.get("type", "attraction")

    return [
        f"#### [{e.get('name')}]({SITE_URL}/dia-diem/{eid})",
        f"- **Mã ID**: `{eid}` | **Phân loại**: `{entity_type}` | **Địa bàn**: {place} | **Tọa độ**: {coord_str}",
        f"- **Ảnh tư liệu WebP**: `{SITE_URL}/img/entities/{eid}.webp`",
        f"- **Tác giả ảnh**: {author} · **Cơ quan**: {source}",
        f"- **Bản quyền hình ảnh**: [Điều khoản sử dụng]({SITE_URL}/dieu-khoan-su-dung) | [Cấp phép]({SITE_URL}/lien-he)",
        f"- **Tóm lược**: {summary}",
        ""
    ]


def build_llms_txt(entities, itineraries, verified_entities, wards):
    count_verified = len(verified_entities)
    return f"""# vinhlong360.vn

> Cổng bách khoa tri thức du lịch, văn hóa bản địa, ẩm thực truyền thống, làng nghề và sản phẩm OCOP chính thức cho **tỉnh Vĩnh Long** — miền Tây Nam Bộ, Việt Nam.

## Giới thiệu & Địa giới Hành chính (Lưu ý Quan trọng)

Từ tháng 7-2025, ba địa bàn Vĩnh Long, Bến Tre và Trà Vinh đã **HỢP NHẤT thành MỘT tỉnh duy nhất mang tên Vĩnh Long**.
- Cấp huyện đã được bãi bỏ hoàn toàn; tỉnh vận hành mô hình hành chính 2 cấp gồm **1 tỉnh và 124 xã/phường**.
- Mọi tên gọi "Bến Tre", "Trà Vinh" trong toàn bộ tài liệu chỉ dùng để chỉ **vùng đất/vùng văn hóa** theo địa giới cũ trước tháng 7-2025. Tuyệt đối không dùng "tỉnh Bến Tre" hay "tỉnh Trà Vinh" ngoài văn cảnh lịch sử.

## Toàn Văn Dữ Liệu Máy Đọc (Full Documentation)

- **Bách khoa toàn thư tri thức máy đọc chi tiết**: [llms-full.txt]({SITE_URL}/llms-full.txt)
  (Chứa toàn bộ {count_verified} thực thể xác minh ảnh tư liệu, 33 tuyến lộ trình, 124 xã/phường, lịch mùa vụ và lễ hội AEO).

## Thống Kê Nền Tảng

- **Tổng số thực thể dữ liệu**: {len(entities)} điểm đến, di tích, ẩm thực, làng nghề, nhân vật, sản phẩm.
- **Thực thể xác minh ảnh tư liệu báo chí chính thống**: {count_verified} thực thể (100% ảnh WebP nội bộ kèm bản quyền Google Images).
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


def build_llms_full_txt(entities, itineraries, verified_entities, wards):
    lines = []

    lines.append("# vinhlong360 — Bách Khoa Toàn Thư Tri Thức & Dữ Liệu Du Lịch, Thổ Nhưỡng, OCOP Tam Vùng (llms-full.txt)")
    lines.append("")
    lines.append("> vinhlong360.vn là nền tảng tri thức du lịch, văn hóa bản địa, ẩm thực truyền thống, làng nghề và sản phẩm OCOP chính thức cho **tỉnh Vĩnh Long** (hợp nhất từ ba vùng Vĩnh Long, Bến Tre, Trà Vinh cũ từ tháng 7-2025). Tỉnh vận hành hành chính 2 cấp gồm 124 xã/phường (không có cấp huyện).")
    lines.append("")
    lines.append("## 1. Quy Chuẩn Địa Giới Hành Chính (Rule R10.7)")
    lines.append("- Toàn bộ lãnh thổ 3 vùng cũ nay thuộc một đơn vị hành chính cấp tỉnh duy nhất: **tỉnh Vĩnh Long**.")
    lines.append("- 124 đơn vị hành chính trực thuộc gồm 35 phường và 89 xã.")
    lines.append("- Cấp huyện đã bãi bỏ; các địa danh huyện cũ (Long Hồ, Mang Thít, Ba Tri, Châu Thành, Càng Long, Cầu Kè, Trà Cú...) chỉ mang giá trị lịch sử và chỉ dẫn vị trí địa lý dân gian.")
    lines.append("")

    lines.append(f"## 2. Danh Mục {len(verified_entities)} Thực Thể Xác Minh Ảnh Tư Liệu Báo Chí & Giấy Phép Google Images")
    lines.append("")
    lines.append("Mỗi thực thể dưới đây đều có ảnh tư liệu báo chí chính thống được lưu trữ nội bộ chuẩn WebP, tích hợp siêu dữ liệu Schema.org `ImageObject` với đầy đủ bản quyền (`creator`, `creditText`, `copyrightNotice`, `license`, `acquireLicensePage`).")
    lines.append("")

    for e in verified_entities:
        lines.extend(format_entity_block(e))

    lines.append(f"## 3. Danh Mục {len(itineraries)} Tuyến Lộ Trình Du Lịch Liên Vùng Chuyên Đề")
    lines.append("")
    for itin in itineraries:
        iid = itin.get("id")
        title = itin.get("title", "")
        duration = itin.get("duration", "1 ngày")
        summary = itin.get("summary", "")
        stops = itin.get("stops") or []
        lines.append(f"### [{title}]({SITE_URL}/lich-trinh/{iid})")
        lines.append(f"- **Mã lộ trình**: `{iid}` | **Thời lượng**: {duration} | **Số điểm dừng**: {len(stops)}")
        lines.append(f"- **Mô tả hành trình**: {summary}")
        if stops:
            stop_names = [str(s.get("name", s.get("entityId", ""))) for s in stops[:8]]
            lines.append(f"- **Các điểm dừng tiêu biểu**: {' → '.join(stop_names)}")
        lines.append("")

    lines.append("## 4. Danh Mục 124 Xã/Phường Thuộc Tỉnh Vĩnh Long")
    lines.append("")
    lines.append("Tỉnh Vĩnh Long gồm 35 phường và 89 xã:")
    lines.append("")
    for w in sorted(wards, key=lambda x: str(x.get("name", ""))):
        wid = w.get("id")
        wname = w.get("name")
        attrs = w.get("attributes") or {}
        police = attrs.get("police_phone", "")
        contact_str = f" | Hotline CAX: {police}" if police else ""
        lines.append(f"- **[{wname}]({SITE_URL}/xa-phuong/{wid})** (`{wid}`){contact_str}")
    lines.append("")

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
        if e.get("type") == "place" and e.get("id") != "prov-1"
    ]

    print(f"Entities: {len(entities)}")
    print(f"Verified photo entities: {len(verified_entities)}")
    print(f"Itineraries: {len(itineraries)}")
    print(f"Wards: {len(wards)}")

    llms_txt_content = build_llms_txt(entities, itineraries, verified_entities, wards)
    llms_full_txt_content = build_llms_full_txt(entities, itineraries, verified_entities, wards)

    with open(LLMS_TXT_PATH, "w", encoding="utf-8") as f:
        f.write(llms_txt_content)
    print(f"Written {LLMS_TXT_PATH} ({len(llms_txt_content.encode('utf-8'))} bytes)")

    with open(LLMS_FULL_TXT_PATH, "w", encoding="utf-8") as f:
        f.write(llms_full_txt_content)
    print(f"Written {LLMS_FULL_TXT_PATH} ({len(llms_full_txt_content.encode('utf-8'))} bytes)")


if __name__ == "__main__":
    main()
