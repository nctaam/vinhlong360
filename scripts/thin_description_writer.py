#!/usr/bin/env python3
"""Nâng mô tả quá mỏng, chỉ từ dữ kiện đã có trong chính bản ghi.

767 entity có mô tả dưới 200 ký tự, trong đó 765 có `attributes` chứa dữ kiện
thật: toppings, must_order, peak_event, travel_tip, giờ mở cửa, giá... Viết mô tả
từ những dữ kiện đó là làm giàu; viết thêm bất cứ điều gì khác là bịa.

Gác cổng ở đây khác gác cổng của admin_naming_rewrite: nó soi CHỐNG BỊA — mọi con
số và mọi tên riêng trong bản mới phải truy được về mô tả cũ, tên entity hoặc
attributes. Không truy được thì từ chối ghi.

  python scripts/thin_description_writer.py export --limit 20 --out lot.json
  python scripts/thin_description_writer.py apply --in lot.json --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):  # console Windows cp1252 không in nổi tiếng Việt
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(os.environ.get("VL360_ROOT") or Path(__file__).resolve().parent.parent)
sys.path.insert(0, str(ROOT / "agent"))

THIN_LIMIT = 200
NUMBER_RE = re.compile(r"\d[\d.,/]*")
WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)

# Câu độn: kể ra thứ hồ sơ KHÔNG có để lấp cho đủ độ dài. Nó không thêm thông tin
# nào cho người đọc, chỉ làm mọi trang giống nhau.
EMPTY_FILLER_RE = re.compile(
    r"(chưa có thông tin|chưa rõ (giá|giờ|số điện thoại)|không có thông tin|"
    r"hỏi (tại chỗ|trực tiếp) (để|cho) (biết|rõ)|liên hệ để biết thêm|"
    r"thông tin đang được (cập nhật|bổ sung))",
    re.IGNORECASE,
)


def proper_nouns(text: str) -> set[str]:
    """Cụm từ viết hoa liên tiếp.

    Không dùng dải regex kiểu [A-ZĐÀ-Ỹ]: trong Unicode, dải À-Ỹ bao luôn chữ
    THƯỜNG có dấu (ă, đ, ế...), nên 'ăn', 'đi', 'đến' bị nhận nhầm là tên riêng.
    """
    nouns: set[str] = set()
    for sentence in re.split(r"[.!?\n]", text or ""):
        run: list[str] = []
        start_index = 0
        for index, word in enumerate(WORD_RE.findall(sentence)):
            if word[:1].isupper():
                if not run:
                    start_index = index
                run.append(word)
                continue
            if run:
                _collect(nouns, run, start_index)
                run = []
        if run:
            _collect(nouns, run, start_index)
    return nouns


def _collect(nouns: set[str], run: list[str], start_index: int) -> None:
    """Tiếng Việt viết hoa đầu câu, nên một từ viết hoa đứng đầu câu chưa phải
    tên riêng — tính nó là tên riêng sẽ chặn oan mọi câu mở đầu bằng danh từ
    chung ("Hàng bún dọn sớm...")."""
    if start_index == 0 and len(run) == 1:
        return
    nouns.add(" ".join(run))

# Từ mở đầu câu hoặc danh từ chung viết hoa — không phải tên riêng cần truy nguồn.
COMMON_CAPITALIZED = {
    "Bún", "Bánh", "Cơm", "Chè", "Cháo", "Quán", "Nhà", "Khu", "Chợ", "Vườn", "Cầu",
    "Sông", "Chùa", "Đình", "Miếu", "Làng", "Bến", "Món", "Trong", "Ngoài", "Từ",
    "Đến", "Khi", "Nếu", "Mỗi", "Giờ", "Giá", "Ngày", "Buổi", "Sáng", "Chiều", "Tối",
    "Đây", "Đó", "Ở", "Tại", "Có", "Không", "Một", "Hai", "Ba", "Nơi", "Người", "Các",
    "Tết", "Lễ", "Mùa", "Đặc", "Sản", "Phần", "Với", "Theo", "Sau", "Trước", "Bên",
}

VAGUE_WORDS = ("nổi tiếng", "hấp dẫn", "thu hút", "tuyệt vời", "độc đáo", "ấn tượng",
               "thơ mộng", "hữu tình", "không thể bỏ qua", "điểm đến lý tưởng")

# Trường nội bộ: ghi chú vận hành/marketing của đội ngũ, KHÔNG phải sự thật về
# địa điểm. Đợt đầu có bản biến responsible_tips (đề xuất nội bộ) thành dịch vụ
# đang bán — khách đọc xong có thể tới đặt một workshop không tồn tại.
INTERNAL_ONLY_FIELDS = (
    "responsible_tips", "target_segments", "priority", "role", "tour", "where",
    "local_favorite", "instagram_worthy", "coords_approximate", "schema_type",
    "merge_note", "confidence", "internal_note", "todo",
)

# Khẳng định độ chính xác vị trí. coords_approximate=false chỉ nghĩa là toạ độ
# KHÔNG được đánh dấu gần đúng — không đủ để hứa "bấm bản đồ là ra tới cửa".
# §1.7 cấm mọi claim xác minh mà dữ liệu không đỡ được.
PRECISION_CLAIMS = (
    "toạ độ chính xác", "tọa độ chính xác", "toạ độ chấm đúng", "tọa độ chấm đúng",
    "ra tới cửa", "đúng tới cửa", "chính xác tuyệt đối", "đã được xác minh",
    "đã xác minh", "kiểm chứng thực địa",
)

# Ba nhóm chủ đề mà đợt viết 765 mô tả đã bịa ra, và gác cổng chuỗi thuần không
# nhận biết được vì chúng không nhắc tên trường nào:
#
# 1. Lời khuyên an toàn. Một bản khuyên "bơi tự do giữa dòng, không phao không
#    hàng rào" trên sông Cổ Chiên — chính DB ghi sông này có điểm sâu nhất ĐBSCL
#    và dòng chảy mạnh. Khuyên sai kiểu này có thể làm chết người.
# 2. Giải thích lý do phân loại hành chính ("có thị trấn cũ bên trong nên xếp là
#    phường") — luật bịa, chính bộ dữ liệu bác bỏ.
# 3. Nhóm khách mục tiêu — đó là target_segments, ghi chú marketing nội bộ.
UNSOURCEABLE_TOPICS = (
    (r"(bơi|tắm|lội)\s+(tự do|thoải mái)|không\s+(phao|hàng rào|cứu hộ)|"
     r"an toàn hơn|đừng xuống nước|nước cạn nên|có thể tắm được",
     "lời khuyên an toàn không có trong bản ghi"),
    (r"nên\s+(được\s+)?(xếp|gọi|coi) là (phường|xã)|không phải (là )?(phường|xã)|"
     r"vì có thị trấn cũ|nên đơn vị mới",
     "tự suy ra luật phân loại hành chính"),
    (r"nhóm khách (được )?nhắm|khách mục tiêu|phù hợp với (dân|nhóm|giới)|"
     r"đối tượng khách",
     "nhóm khách mục tiêu là ghi chú nội bộ"),
)


def _strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


KNOWN_FIELDS = ("name", "description", "summary", "address", "place_name", "placeId",
                "area", "hours", "price_range", "best_time", "highlight")


def _known_text(entity: dict) -> str:
    """Toàn bộ chữ nghĩa đã biết về entity — nguồn hợp lệ duy nhất để viết."""
    parts = [str(entity.get(field) or "") for field in KNOWN_FIELDS]
    attributes = entity.get("attributes")
    if attributes:
        parts.append(attributes if isinstance(attributes, str)
                     else json.dumps(attributes, ensure_ascii=False))
    return "\n".join(parts)


def _invented_numbers(new: str, known: str) -> list[str]:
    return sorted({
        n.rstrip(".,/") for n in NUMBER_RE.findall(new)
        if n.rstrip(".,/") and n.rstrip(".,/") not in known
    })


def _invented_nouns(new: str, known_flat: str) -> list[str]:
    def traceable(noun: str) -> bool:
        if _strip_accents(noun).lower() in known_flat:
            return True
        # Cụm mở đầu câu có thể chỉ là một từ thường viết hoa; nếu bỏ từ đầu mà
        # phần còn lại truy được thì không phải bịa.
        tail = " ".join(noun.split()[1:])
        return bool(tail) and _strip_accents(tail).lower() in known_flat

    return sorted({
        noun for noun in proper_nouns(new)
        if noun not in COMMON_CAPITALIZED and not traceable(noun)
    })


def check_no_invention(entity: dict, new: str) -> list[str]:
    """Từ chối bản mới nếu nó chứa dữ kiện không truy được về bản ghi."""
    if not (new or "").strip():
        return ["mô tả mới rỗng"]

    known = _known_text(entity)
    lowered = new.lower()
    checks = [
        (_invented_numbers(new, known), "số liệu không có trong bản ghi"),
        (_invented_nouns(new, _strip_accents(known).lower()), "tên riêng không có trong bản ghi"),
        ([w for w in VAGUE_WORDS if w in lowered], "từ sáo rỗng"),
        ([f for f in INTERNAL_ONLY_FIELDS if f in lowered], "lộ tên trường nội bộ"),
        ([c for c in PRECISION_CLAIMS if c in lowered], "khai khống độ chính xác (§1.7)"),
    ]
    problems = [f"{label}: {found[:6]}" for found, label in checks if found]

    for pattern, label in UNSOURCEABLE_TOPICS:
        match = re.search(pattern, lowered)
        if match:
            problems.append(f"{label}: '{match.group(0)}'")

    # Không ép độ dài tối thiểu. Ngưỡng cứng 200 ký tự ở bản đầu đã khiến 148 bản
    # đạt ngưỡng bằng cách LIỆT KÊ NHỮNG THỨ HỒ SƠ KHÔNG CÓ ("giá thì chưa có
    # thông tin, hỏi tại chỗ"). Với entity nghèo dữ kiện, mô tả ngắn mới là trung
    # thực; điều bắt buộc chỉ là dài hơn bản cũ và không độn.
    if len(new) <= len(entity.get("description") or ""):
        problems.append("không dài hơn mô tả cũ")
    if EMPTY_FILLER_RE.search(new):
        problems.append("độn chữ bằng thứ hồ sơ không có")
    return problems


def _load_db():
    from database import db
    return db


def cmd_export(args):
    db = _load_db()
    rows = []
    for entity in db.all_entities():
        description = entity.get("description") or ""
        if len(description) >= THIN_LIMIT:
            continue
        attributes = entity.get("attributes")
        if isinstance(attributes, str):
            try:
                attributes = json.loads(attributes)
            except Exception:
                attributes = {"_raw": attributes}
        if not attributes:
            continue
        rows.append({
            "id": entity.get("id"),
            "name": entity.get("name"),
            "type": entity.get("type"),
            "area": entity.get("area"),
            "address": entity.get("address"),
            "description_old": description,
            "attributes": attributes,
            "description_new": "",
        })
    rows.sort(key=lambda r: len(r["description_old"]))
    batch = rows[args.offset:args.offset + args.limit]
    Path(args.out).write_text(json.dumps(batch, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[export] {len(batch)}/{len(rows)} entity -> {args.out}")


def cmd_apply(args):
    db = _load_db()
    batch = json.loads(Path(args.infile).read_text(encoding="utf-8"))
    applied = skipped = 0
    for row in batch:
        new = (row.get("description_new") or "").strip()
        if not new:
            continue
        entity = db.get_entity(row["id"])
        if not entity:
            print(f"  [SKIP] {row['id']}: không có trong DB")
            skipped += 1
            continue
        problems = check_no_invention(entity, new)
        if problems:
            print(f"  [SKIP] {row['id']}: {'; '.join(problems)}")
            skipped += 1
            continue
        if args.dry_run:
            print(f"  [OK-DRY] {row['id']} ({len(new)} ký tự)")
            applied += 1
            continue
        entity["description"] = new
        db.upsert_entity(entity)
        print(f"  [OK] {row['id']} ({len(new)} ký tự)")
        applied += 1
    print(f"[apply] ghi={applied} bỏ_qua={skipped} dry_run={args.dry_run}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    ex = sub.add_parser("export")
    ex.add_argument("--limit", type=int, default=20)
    ex.add_argument("--offset", type=int, default=0)
    ex.add_argument("--out", required=True)
    ex.set_defaults(func=cmd_export)

    ap_apply = sub.add_parser("apply")
    ap_apply.add_argument("--in", dest="infile", required=True)
    ap_apply.add_argument("--dry-run", action="store_true")
    ap_apply.set_defaults(func=cmd_apply)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
