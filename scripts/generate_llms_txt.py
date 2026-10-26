#!/usr/bin/env python3
"""
generate_llms_txt.py — Sinh bách khoa toàn thư tri thức máy đọc llms-full.txt và llms.txt.
Tuân thủ chuẩn llmstxt.org và quy tắc địa giới hành chính 2 cấp (R10.7) của tỉnh Vĩnh Long mới.
"""

import json
import sys
import argparse
from dataclasses import dataclass
from pathlib import Path

ROOT_DIR = Path(r"c:\Users\NCTaam\Documents\vinhlong360-correction-case-pilot")
DATA_JSON_PATH = ROOT_DIR / "web" / "data.json"
LLMS_TXT_PATH = ROOT_DIR / "web-nuxt" / "public" / "llms.txt"
LLMS_FULL_TXT_PATH = ROOT_DIR / "web-nuxt" / "public" / "llms-full.txt"
SITE_URL = "https://vinhlong360.vn"


def load_data(data_path: Path = DATA_JSON_PATH):
    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)


def sanitize_historical(text: str) -> str:
    return (
        text.replace("tỉnh Bến Tre", "tỉnh Bến Tre cũ")
        .replace("tỉnh Trà Vinh", "tỉnh Trà Vinh cũ")
    )


@dataclass(frozen=True)
class PhotoEvidence:
    credit: str
    source_url: str


def _nonempty_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _has_rights_bundle(attrs: dict) -> bool:
    if not all(_nonempty_text(attrs.get(name)) for name in ("image_author", "image_source", "image_license")):
        return False
    source_url = attrs.get("image_source_url")
    if not isinstance(source_url, str) or not source_url.strip().startswith(("http://", "https://")):
        return False
    permission = attrs.get("permission_evidence") or attrs.get("rights_evidence") or attrs.get("permission")
    return _nonempty_text(permission)


def sourced_photo_evidence(attrs: dict) -> PhotoEvidence | None:
    """Return evidence only when the candidate contains a complete rights bundle."""
    image_type = str(attrs.get("image_type") or "").strip().lower()
    if image_type not in {"documentary", "journalistic", "official", "press"}:
        return None
    if attrs.get("is_verified_photo") is not True:
        return None
    if not _has_rights_bundle(attrs):
        return None
    source_url = attrs.get("image_source_url")
    return PhotoEvidence(
        credit=f"{attrs['image_author'].strip()} · {attrs['image_source'].strip()}",
        source_url=source_url.strip(),
    )


def media_lines(entity: dict) -> list[str]:
    attrs = entity.get("attributes") or {}
    image_type = attrs.get("image_type")
    if image_type == "ai-generated":
        return ["- **Hình ảnh**: Minh họa AI — không phải ảnh chụp tại chỗ."]
    if image_type == "generated-placeholder":
        return ["- **Hình ảnh**: Minh họa đồ họa — chưa có ảnh riêng cho thực thể."]
    evidence = sourced_photo_evidence(attrs)
    if evidence is not None:
        return [
            f"- **Ảnh có nguồn**: {evidence.credit}",
            f"- **Nguồn truy vết**: {evidence.source_url}",
        ]
    return ["- **Hình ảnh**: Chưa có ảnh đã xác minh nguồn gốc."]


def format_entity_block(e: dict) -> list:
    eid = e["id"]
    summary = sanitize_historical(e.get("summary") or e.get("description") or "")
    coords = e.get("coordinates")
    coord_str = f"[{coords[0]:.4f}, {coords[1]:.4f}]" if coords and len(coords) >= 2 else "N/A"
    place = e.get("place_name") or e.get("placeId") or "Vĩnh Long"
    entity_type = e.get("type", "attraction")

    name = sanitize_historical(e.get('name') or '')
    return [
        f"#### [{name}]({SITE_URL}/dia-diem/{eid})",
        f"- **Mã ID**: `{eid}` | **Phân loại**: `{entity_type}` | **Địa bàn**: {place} | **Tọa độ**: {coord_str}",
        *media_lines(e),
        f"- **Tóm lược**: {summary}",
        ""
    ]


def build_llms_txt(entities, itineraries, verified_entities, wards):
    count_verified = len(verified_entities)
    count_ai = sum((e.get("attributes") or {}).get("image_type") == "ai-generated" for e in entities)
    count_placeholder = sum((e.get("attributes") or {}).get("image_type") == "generated-placeholder" for e in entities)
    return f"""# vinhlong360.vn

> Cổng bách khoa tri thức du lịch, văn hóa bản địa, ẩm thực truyền thống, làng nghề và sản phẩm OCOP chính thức cho **tỉnh Vĩnh Long** — miền Tây Nam Bộ, Việt Nam.

## Giới thiệu & Địa giới Hành chính (Lưu ý Quan trọng)

Từ tháng 7-2025, ba địa bàn Vĩnh Long, Bến Tre và Trà Vinh đã **HỢP NHẤT thành MỘT tỉnh duy nhất mang tên Vĩnh Long**.
- Bến Tre và Trà Vinh **KHÔNG còn là đơn vị cấp tỉnh**, và cấp huyện cũng đã bãi bỏ hoàn toàn; tỉnh vận hành mô hình hành chính 2 cấp gồm **1 tỉnh và 124 xã/phường**.
- Mọi tên gọi "Bến Tre", "Trà Vinh" trong toàn bộ tài liệu chỉ dùng để chỉ **vùng đất/vùng văn hóa** theo địa giới cũ trước tháng 7-2025. Tuyệt đối không dùng "tỉnh Bến Tre" hay "tỉnh Trà Vinh" ngoài văn cảnh lịch sử.

## Toàn Văn Dữ Liệu Máy Đọc (Full Documentation)

- **Bách khoa toàn thư tri thức máy đọc chi tiết**: [llms-full.txt]({SITE_URL}/llms-full.txt)
  (Chứa toàn bộ {len(entities)} thực thể và trạng thái hình ảnh, 33 tuyến lộ trình, 124 xã/phường, lịch mùa vụ và lễ hội AEO).

## Thống Kê Nền Tảng

- **Tổng số thực thể dữ liệu**: {len(entities)} điểm đến, di tích, ẩm thực, làng nghề, nhân vật, sản phẩm.
- **Thực thể có bằng chứng ảnh tư liệu đầy đủ**: {count_verified} thực thể (chỉ tính bộ quyền và nguồn đã kiểm chứng).
- **Minh họa AI**: {count_ai} thực thể; **minh họa đồ họa**: {count_placeholder} thực thể.
- **Lộ trình du lịch liên vùng gợi ý**: {len(itineraries)} tuyến chuyên đề (1–3 ngày).
- **Đơn vị hành chính cấp cơ sở**: {len(wards)} xã/phường.

## Ba vùng Văn Hóa - Thổ Nhưỡng Tam Vùng (gọi theo địa giới tỉnh cũ, trước 7-2025)

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
- **Sổ tay hỏi đáp thực địa**: {SITE_URL}/chat

## Giao Tiếp Lập Trình (API Endpoints cho AI Agents)

- `GET /api/v1/entities`: Danh sách thực thể du lịch kèm phân trang và lọc danh mục.
- `GET /api/v1/search?q={{query}}`: Tìm kiếm thực thể theo từ khóa ngữ nghĩa.
- `GET /health`: Kiểm tra trạng thái hoạt động của hệ sinh thái.
"""


def build_llms_full_txt(entities, itineraries, verified_entities, wards):
    lines = []

    lines.append("# vinhlong360 — Bách Khoa Toàn Thư Tri Thức & Dữ Liệu Du Lịch, Thổ Nhưỡng, OCOP Vĩnh Long (llms-full.txt)")
    lines.append("")
    lines.append("> vinhlong360.vn là nền tảng tri thức du lịch, văn hóa bản địa, ẩm thực truyền thống, làng nghề và sản phẩm OCOP chính thức cho **tỉnh Vĩnh Long** (hợp nhất từ ba vùng Vĩnh Long, Bến Tre, Trà Vinh cũ từ tháng 7-2025). Tỉnh vận hành hành chính 2 cấp gồm 124 xã/phường (không có cấp huyện).")
    lines.append("")
    lines.append("## 1. Quy Chuẩn Địa Giới Hành Chính (Rule R10.7)")
    lines.append("- Toàn bộ lãnh thổ 3 vùng cũ nay thuộc một đơn vị hành chính cấp tỉnh duy nhất: **tỉnh Vĩnh Long**.")
    lines.append("- 124 đơn vị hành chính trực thuộc gồm 35 phường và 89 xã.")
    lines.append("- Cấp huyện đã bãi bỏ; các địa danh huyện cũ (Long Hồ, Mang Thít, Ba Tri, Châu Thành, Càng Long, Cầu Kè, Trà Cú...) chỉ mang giá trị lịch sử và chỉ dẫn vị trí địa lý dân gian.")
    lines.append("")

    lines.append(f"## 2. Danh Mục {len(entities)} Thực Thể Và Trạng Thái Hình Ảnh")
    lines.append("")
    lines.append("Thông tin hình ảnh dưới đây chỉ nêu loại minh họa hoặc bằng chứng truy vết đã có trong dữ liệu ứng viên; không suy diễn nguồn, tác giả hay giấy phép còn thiếu.")
    lines.append("")

    for e in entities:
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

    lines.append("## 5. Lịch Nông Vụ OCOP & Trái Cây Miệt Vườn Vĩnh Long")
    lines.append("")
    lines.append("- **Tháng 1 - Tháng 3 (Xuân)**: Bưởi Năm Roi Bình Minh, Cam sành Tam Bình, Quýt đường, Mật ong hoa nhãn.")
    lines.append("- **Tháng 4 - Tháng 6 (Hạ - Rộ mùa)**: Sầu riêng Ri6 Long Hồ & Cái Mơn, Chôm chôm Bình Hòa Phước & Chợ Lách, Măng cụt Cái Mơn, Xoài cát Núm Vũng Liêm.")
    lines.append("- **Tháng 5 - Tháng 7 (Hạ muộn)**: Nhãn xuồng cơm vàng Cù lao An Bình, Vú sữa Lò Rèn, Mận An Phước.")
    lines.append("- **Tháng 8 - Tháng 11 (Mùa nước nổi phù sa)**: Bông điên điển, Cá linh, Cá cháy Trà Ôn, Bông súng đồng.")
    lines.append("- **Thu hoạch quanh năm**: Dừa sáp Cầu Kè, Mật hoa dừa Sokfarm, Kẹo dừa Bến Tre, Bưởi Da Xanh, Khoai lang tím Nhật Bình Tân.")
    lines.append("")

    lines.append("## 6. Lịch Lễ Hội Truyền Thống & Sự Kiện Văn Hóa Vĩnh Long")
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
    lines.append("- `ImageObject`: Chỉ công bố các trường quyền và nguồn khi dữ liệu có bằng chứng đầy đủ; thiếu bằng chứng sẽ được ghi rõ là chưa xác minh.")
    lines.append("- `SpeakableSpecification`: Hỗ trợ công cụ đọc màn hình và AI voice search qua CSS selectors `.lead`, `.highlights`, `h1`.")
    lines.append("")

    return "\n".join(lines)


def generate_llms(data_path: Path, output_dir: Path) -> dict[str, Path]:
    data = load_data(Path(data_path))
    entities = [e for e in data.get("entities", []) if e.get("id") != "prov-1"]
    itineraries = data.get("itineraries", [])

    verified_entities = [e for e in entities if sourced_photo_evidence(e.get("attributes") or {}) is not None]
    wards = [
        e for e in entities
        if e.get("type") == "place" and e.get("id") not in ("prov-1", "vinh-long")
    ]

    llms_txt_content = build_llms_txt(entities, itineraries, verified_entities, wards)
    llms_full_txt_content = build_llms_full_txt(entities, itineraries, verified_entities, wards)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    llms_path = output_dir / "llms.txt"
    full_path = output_dir / "llms-full.txt"
    with llms_path.open("w", encoding="utf-8") as f:
        f.write(llms_txt_content)
    with full_path.open("w", encoding="utf-8") as f:
        f.write(llms_full_txt_content)
    return {"llms": llms_path, "llms_full": full_path}


def main(argv: list[str] | None = None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--llms-output", type=Path, required=True)
    parser.add_argument("--llms-full-output", type=Path, required=True)
    args = parser.parse_args(argv)
    outputs = generate_llms(args.data, args.llms_output.parent)
    if outputs["llms"] != args.llms_output:
        args.llms_output.parent.mkdir(parents=True, exist_ok=True)
        args.llms_output.write_bytes(outputs["llms"].read_bytes())
    if outputs["llms_full"] != args.llms_full_output:
        args.llms_full_output.parent.mkdir(parents=True, exist_ok=True)
        args.llms_full_output.write_bytes(outputs["llms_full"].read_bytes())
    print(f"Written {args.llms_output}")
    print(f"Written {args.llms_full_output}")


if __name__ == "__main__":
    main()
