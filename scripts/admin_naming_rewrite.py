#!/usr/bin/env python3
"""Sửa cách gọi đơn vị hành chính trong mô tả entity, theo lô, có kiểm chứng.

Từ 7/2025 chỉ còn một tỉnh Vĩnh Long, hành chính hai cấp. Mô tả cũ vẫn viết
"huyện Vũng Liêm", "thành phố Bến Tre", "tỉnh Trà Vinh" như đơn vị đang tồn tại.
Không thể sửa bằng regex: câu tiểu sử ("sinh tại huyện Giồng Trôm, 1918") thì
cách gọi cũ mới là đúng, còn câu mô tả vị trí hiện tại thì phải đổi.

Nên luồng là: export lô -> người/LLM viết lại từng câu -> apply có gác cổng.

  python scripts/admin_naming_rewrite.py export --limit 25 --out lot.json
  python scripts/admin_naming_rewrite.py apply --in lot.json --dry-run
  python scripts/admin_naming_rewrite.py apply --in lot.json

Gác cổng khi apply (mọi bản ghi phải qua, nếu không thì bỏ qua bản ghi đó):
  - không rỗng, không ngắn đi quá 25% so với bản cũ
  - giữ nguyên mọi số liệu (năm, diện tích, số lượng) có trong bản cũ
  - giữ nguyên mọi tên riêng viết hoa có trong bản cũ
  - không còn cách gọi đơn vị hành chính đã bỏ, trừ khi câu đó có ngữ cảnh lịch sử
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

# Console Windows mặc định cp1252 không in được tiếng Việt: script chết giữa
# chừng bằng UnicodeEncodeError sau khi đã ghi một phần — nguy hiểm cho lệnh apply.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# DB là tài sản chung của repo chính, không thuộc worktree nào. VL360_ROOT cho
# phép chạy script từ worktree đang phát triển mà vẫn đọc/ghi đúng DB thật.
ROOT = Path(os.environ.get("VL360_ROOT") or Path(__file__).resolve().parent.parent)
sys.path.insert(0, str(ROOT / "agent"))

# Cách gọi đơn vị hành chính đã bị bãi bỏ.
#
# Nhãn cấp phải bắt cả dạng VIẾT HOA ("Huyện Trà Cú", "Thành Phố Vĩnh Long").
# Bản đầu chỉ bắt chữ thường, nên trong đợt sửa 457 mô tả, hai bến xe đang hoạt
# động giữ nguyên "Thị trấn/Huyện/Tỉnh" rồi bị dán thêm "cũ" — đọc thành đã ngưng
# chạy. Dùng lớp chữ hoa tường minh thay vì dải [A-ZĐÀ-Ỹ], vì dải đó trong Unicode
# trùm luôn chữ THƯỜNG có dấu (đ, ế, ă...).
_UPPER = r"[A-ZĐÀ-ÞĂĐĨŨƠƯẠ-Ỹ]"
STALE_PATTERNS = [
    (re.compile(rf"\b[Hh]uyện\s+{_UPPER}"), "huyện + tên riêng"),
    (re.compile(r"\b[Tt]hành\s+[Pp]hố\s+(Bến Tre|Trà Vinh|Vĩnh Long)\b"), "thành phố trực thuộc tỉnh"),
    (re.compile(r"\bTP\.?\s*(Bến Tre|Trà Vinh|Vĩnh Long)\b"), "TP viết tắt"),
    (re.compile(rf"\b[Tt]hị\s+[Tt]rấn\s+{_UPPER}"), "thị trấn"),
    (re.compile(r"\b[Tt]ỉnh\s+(Bến Tre|Trà Vinh)\b"), "tỉnh đã sáp nhập"),
]

# Nhãn cấp bị gộp vào cụm tên riêng ("Huyện Cầu Ngang" thành một token), nên xoá
# nhãn lại bị chặn là "mất tên riêng" — chính điều buộc người sửa giữ nhãn rồi dán
# "cũ". Vì vậy phải bóc nhãn ra trước khi so tên riêng.
ADMIN_LABELS = {"Huyện", "Thị", "Trấn", "Thành", "Phố", "Tỉnh", "TP", "TT", "H",
                "Xã", "Phường", "Ấp", "Khóm", "Khu"}

# Dấu hiệu câu đang kể chuyện quá khứ — cách gọi cũ ở đây là đúng, không sửa.
HISTORICAL_MARKERS = (
    "cũ", "trước 7-2025", "trước tháng 7", "trước năm", "sáp nhập", "hợp nhất",
    "sinh tại", "sinh năm", "quê ở", "thời", "xưa", "nguyên là", "từng là",
)

NUMBER_RE = re.compile(r"\d[\d.,]*")
PROPER_NOUN_RE = re.compile(r"\b[A-ZĐÀ-Ỹ][a-zà-ỹ]+(?:\s+[A-ZĐÀ-Ỹ][a-zà-ỹ]+)*")


def stale_hits(text: str) -> list[str]:
    return [label for pattern, label in STALE_PATTERNS if pattern.search(text or "")]


def sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text or "") if s.strip()]


def stale_sentences(text: str) -> list[str]:
    """Chỉ những câu vừa dùng cách gọi cũ, vừa KHÔNG có ngữ cảnh lịch sử."""
    out = []
    for sentence in sentences(text):
        if not stale_hits(sentence):
            continue
        if any(marker in sentence.lower() for marker in HISTORICAL_MARKERS):
            continue
        out.append(sentence)
    return out


def _numbers(text: str) -> set[str]:
    return {n.rstrip(".,") for n in NUMBER_RE.findall(text or "")}


def _proper_nouns(text: str) -> set[str]:
    """Các TỪ viết hoa, đã bỏ nhãn cấp hành chính.

    Hai điều bản đầu làm sai, đều đã cho lọt lỗi thật:
    - dùng dải [A-ZĐÀ-Ỹ], mà trong Unicode dải đó trùm luôn chữ THƯỜNG có dấu,
      nên "đến", "đi" bị tính là tên riêng;
    - so theo CỤM viết hoa liên tiếp. Bỏ nhãn cấp ở giữa làm hai tên dính lại
      thành cụm khác ("Cầu Ngang Cầu Ngang Trà Vinh" so với "Cầu Ngang Trà
      Vinh"), nên bản sửa đúng vẫn bị chặn là "mất tên riêng" — chính điều buộc
      người sửa giữ nhãn rồi dán "cũ".
    So theo từ thì mất tên là mất thật, không phụ thuộc cách ghép cụm.
    """
    words = re.findall(r"[^\W\d_]+", text or "", re.UNICODE)
    return {w for w in words if w[:1].isupper() and w not in ADMIN_LABELS}


def check(old: str, new: str) -> list[str]:
    """Trả về danh sách lý do từ chối. Rỗng = an toàn để ghi."""
    problems = []
    if not (new or "").strip():
        problems.append("mô tả mới rỗng")
        return problems

    if len(new) < len(old) * 0.75:
        problems.append(f"ngắn hơn 25% so với bản cũ ({len(new)} < {len(old)})")

    lost_numbers = _numbers(old) - _numbers(new)
    if lost_numbers:
        problems.append(f"mất số liệu: {sorted(lost_numbers)[:6]}")

    lost_nouns = _proper_nouns(old) - _proper_nouns(new)
    # Tên đơn vị hành chính cũ được phép biến mất — đó chính là mục đích sửa.
    lost_nouns = {n for n in lost_nouns if n not in {"Bến Tre", "Trà Vinh", "Vĩnh Long"}}
    if lost_nouns:
        problems.append(f"mất tên riêng: {sorted(lost_nouns)[:6]}")

    remaining = stale_sentences(new)
    if remaining:
        problems.append(f"vẫn còn cách gọi cũ ở {len(remaining)} câu: {remaining[0][:70]}")

    return problems


# Phép biến đổi hẹp, chỉ áp cho câu KHÔNG có ngữ cảnh lịch sử. Mục tiêu là bỏ
# cấp hành chính đã bãi bỏ mà giữ nguyên địa danh — không diễn đạt lại câu.
AUTO_RULES = [
    # "cách thành phố Bến Tre 70 km" -> "cách trung tâm Bến Tre 70 km"
    (re.compile(r"\b([Cc]ách)\s+(?:[Tt]hành\s+[Pp]hố|TP\.?)\s*(Bến Tre|Trà Vinh|Vĩnh Long)\b"),
     r"\1 trung tâm \2"),
    # "tại TP Vĩnh Long" / "ở Thành Phố Bến Tre" -> giữ tên, bỏ cấp
    (re.compile(r"\b(?:[Tt]hành\s+[Pp]hố|TP\.?)\s*(Bến Tre|Trà Vinh|Vĩnh Long)\b"), r"\1"),
    # "xã A, huyện B" -> "xã A, B" (địa danh giữ nguyên, chỉ bỏ nhãn cấp).
    # Phải nhận cả dạng viết hoa: 40 bản ghi lọt qua đợt đầu đều viết "Huyện X",
    # "Thị trấn Y", "Thành Phố Z".
    (re.compile(rf"\b[Hh]uyện\s+(?={_UPPER})"), ""),
    (re.compile(rf"\bH\.\s*(?={_UPPER})"), ""),
    (re.compile(rf"\b[Tt]hị\s+[Tt]rấn\s+(?={_UPPER})"), ""),
    (re.compile(rf"\bTT\.?\s+(?={_UPPER})"), ""),
    # "tỉnh Bến Tre" ở ngữ cảnh hiện tại -> địa danh vùng
    (re.compile(r"\b[Tt]ỉnh\s+(Bến Tre|Trà Vinh)\b"), r"\1"),
]


def suggest(text: str) -> str:
    """Bản nháp: chỉ đụng vào câu đang dùng cách gọi cũ ở ngữ cảnh hiện tại."""
    bad = set(stale_sentences(text))
    if not bad:
        return text
    out = text
    for sentence in bad:
        fixed = sentence
        for pattern, repl in AUTO_RULES:
            fixed = pattern.sub(repl, fixed)
        fixed = re.sub(r"\s{2,}", " ", fixed).replace(" ,", ",")
        out = out.replace(sentence, fixed)
    return out


def _load_db():
    from database import db
    return db


def cmd_export(args):
    db = _load_db()
    rows = []
    for entity in db.all_entities():
        description = entity.get("description") or ""
        bad = stale_sentences(description)
        if not bad:
            continue
        draft = suggest(description) if args.suggest else ""
        # Bản nháp không qua nổi gác cổng thì để trống, buộc phải viết tay.
        if draft and check(description, draft):
            draft = ""
        rows.append({
            "id": entity.get("id"),
            "name": entity.get("name"),
            "type": entity.get("type"),
            "area": entity.get("area"),
            "stale_sentences": bad,
            "description_old": description,
            "description_new": draft,
        })
    rows.sort(key=lambda r: (-len(r["stale_sentences"]), r["id"] or ""))
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
        problems = check(entity.get("description") or "", new)
        if problems:
            print(f"  [SKIP] {row['id']}: {'; '.join(problems)}")
            skipped += 1
            continue
        if args.dry_run:
            print(f"  [OK-DRY] {row['id']}")
            applied += 1
            continue
        entity["description"] = new
        db.upsert_entity(entity)
        print(f"  [OK] {row['id']}")
        applied += 1
    print(f"[apply] ghi={applied} bỏ_qua={skipped} dry_run={args.dry_run}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    ex = sub.add_parser("export")
    ex.add_argument("--limit", type=int, default=25)
    ex.add_argument("--offset", type=int, default=0)
    ex.add_argument("--out", required=True)
    ex.add_argument("--suggest", action="store_true",
                    help="điền sẵn bản nháp cho các câu đổi được bằng luật hẹp; "
                         "nháp không qua gác cổng thì để trống để viết tay")
    ex.set_defaults(func=cmd_export)

    ap_apply = sub.add_parser("apply")
    ap_apply.add_argument("--in", dest="infile", required=True)
    ap_apply.add_argument("--dry-run", action="store_true")
    ap_apply.set_defaults(func=cmd_apply)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
