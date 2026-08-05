#!/usr/bin/env python3
"""Soi toàn bộ mô tả đang phục vụ người dùng, tìm dấu hiệu nội dung không đáng tin.

Khác `thin_description_writer` (gác cổng lúc GHI), script này soi thứ ĐÃ nằm
trong DB — chạy định kỳ, không gắn vào pre-commit vì phải đọc cả bảng entities.

Sáu nhóm dưới đây đều đến từ lỗi thật đã xảy ra, không phải giả định:
  - trường nội bộ lộ ra văn công khai (responsible_tips thành "workshop" đang bán)
  - khai khống độ chính xác vị trí (coords_approximate=false thành "ra tới cửa")
  - lời khuyên an toàn bịa (khuyên bơi giữa sông Cổ Chiên)
  - tự suy luật hành chính ("có thị trấn cũ bên trong nên xếp là phường")
  - đơn vị hành chính đã bãi bỏ ở ngữ cảnh hiện tại
  - câu độn kể ra thứ hồ sơ không có

  python scripts/audit_content_integrity.py            # tóm tắt
  python scripts/audit_content_integrity.py --list     # kèm id vi phạm
  python scripts/audit_content_integrity.py --max 0    # exit≠0 nếu còn vi phạm
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(os.environ.get("VL360_ROOT") or Path(__file__).resolve().parent.parent)
sys.path.insert(0, str(ROOT / "agent"))
sys.path.insert(0, str(ROOT / "scripts"))

# Câu có mốc lịch sử thì cách gọi cũ là ĐÚNG — không tính là vi phạm.
HISTORICAL = ("cũ", "trước 7-2025", "trước tháng 7", "trước năm", "sáp nhập",
              "hợp nhất", "sinh tại", "sinh năm", "quê ở", "thời", "xưa",
              "nguyên là", "từng là", "triều")

RULES: list[tuple[str, str, str]] = [
    ("truong_noi_bo",
     r"responsible_tips|target_segments|local_favorite|instagram_worthy|"
     r"coords_approximate|schema_type|merge_note|priority\s*[:=]",
     "lộ tên trường nội bộ ra văn công khai"),
    ("khai_khong_vi_tri",
     r"to[aạ] độ (chính xác|chấm đúng)|ra tới cửa|đúng tới cửa|"
     r"đã (được )?xác minh|kiểm chứng thực địa",
     "khai khống độ chính xác vị trí hoặc mức xác minh (§1.7)"),
    ("khuyen_an_toan",
     r"(bơi|tắm|lội)\s+(tự do|thoải mái)|không\s+(phao|hàng rào|cứu hộ)|"
     r"đừng xuống nước|nước cạn nên|an toàn hơn",
     "lời khuyên an toàn không truy được nguồn"),
    ("tu_suy_luat_hc",
     r"nên\s+(được\s+)?(xếp|gọi|coi) là (phường|xã)|vì có thị trấn|nên đơn vị mới",
     "tự suy ra luật phân loại hành chính"),
    ("don_chu",
     r"chưa có thông tin|chưa rõ (giá|giờ|số điện thoại)|hỏi (tại chỗ|trực tiếp) (để|cho)|"
     r"thông tin đang được (cập nhật|bổ sung)",
     "độn chữ bằng thứ hồ sơ không có"),
]

STALE_ADMIN = [
    re.compile(r"\b[Hh]uyện\s+[A-ZĐÀ-ÞĂĐĨŨƠƯẠ-Ỹ]"),
    re.compile(r"\b[Tt]hành\s+[Pp]hố\s+(Bến Tre|Trà Vinh|Vĩnh Long)\b"),
    re.compile(r"\bTP\.?\s*(Bến Tre|Trà Vinh|Vĩnh Long)\b"),
    re.compile(r"\b[Tt]hị\s+[Tt]rấn\s+[A-ZĐÀ-ÞĂĐĨŨƠƯẠ-Ỹ]"),
    re.compile(r"\b[Tt]ỉnh\s+(Bến Tre|Trà Vinh)\b"),
]


def stale_admin_sentences(text: str) -> list[str]:
    out = []
    for sentence in re.split(r"(?<=[.!?])\s+", text or ""):
        if not any(p.search(sentence) for p in STALE_ADMIN):
            continue
        if any(marker in sentence.lower() for marker in HISTORICAL):
            continue
        out.append(sentence.strip())
    return out


# "cua, còng, vọp bơi lội tự do" là tả động vật, không phải khuyên người xuống
# nước. Chỉ tính vi phạm khi câu đang nói về người.
FAUNA = ("cua", "còng", "vọp", "cá", "tôm", "chim", "cò", "vạc", "ốc", "ba khía", "đàn")
HUMAN = ("bạn", "khách", "du khách", "người", "trẻ", "nhóm", "mình", "ta")


def _is_about_people(sentence: str, match_start: int = -1) -> bool:
    """Chủ thể của hành động mới quyết định, không phải cả câu.

    "bạn sẽ chứng kiến cua, còng, vọp bơi lội tự do" có cả 'bạn' lẫn tên con vật;
    thứ đang bơi là con vật, nên xét đoạn NGAY TRƯỚC cụm khớp.
    """
    lowered = sentence.lower()
    if match_start >= 0:
        preceding = lowered[max(0, match_start - 45):match_start]
        if any(word in preceding for word in FAUNA):
            return False
    if any(word in lowered for word in HUMAN):
        return True
    return not any(word in lowered for word in FAUNA)


def audit(entities) -> dict[str, list[tuple[str, str]]]:
    findings: dict[str, list[tuple[str, str]]] = {key: [] for key, _, _ in RULES}
    findings["don_vi_hanh_chinh_cu"] = []
    for entity in entities:
        description = entity.get("description") or ""
        if not description:
            continue
        eid = entity.get("id") or "?"
        lowered = description.lower()
        for key, pattern, _ in RULES:
            match = re.search(pattern, lowered)
            if not match:
                continue
            if key == "khuyen_an_toan":
                sentence = next(
                    (s for s in re.split(r"(?<=[.!?])\s+|—", description)
                     if re.search(pattern, s.lower())), description)
                local = re.search(pattern, sentence.lower())
                if not _is_about_people(sentence, local.start() if local else -1):
                    continue
            findings[key].append((eid, match.group(0)[:60]))
        bad = stale_admin_sentences(description)
        if bad:
            findings["don_vi_hanh_chinh_cu"].append((eid, bad[0][:70]))
    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--list", action="store_true", help="in id vi phạm")
    ap.add_argument("--max", type=int, default=None,
                    help="số vi phạm tối đa chấp nhận; vượt thì exit≠0")
    args = ap.parse_args()

    from database import db
    entities = db.all_entities()
    findings = audit(entities)

    labels = {key: label for key, _, label in RULES}
    labels["don_vi_hanh_chinh_cu"] = "đơn vị hành chính đã bãi bỏ ở ngữ cảnh hiện tại"

    total = 0
    print(f"Soi {len(entities)} entity:")
    for key, items in findings.items():
        total += len(items)
        status = "OK" if not items else "!!"
        print(f"  [{status}] {labels[key]}: {len(items)}")
        if args.list:
            for eid, sample in items[:10]:
                print(f"        {eid} — {sample}")
    print(f"Tổng vi phạm: {total}")

    if args.max is not None and total > args.max:
        print(f"VƯỢT NGƯỠNG ({total} > {args.max})")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
