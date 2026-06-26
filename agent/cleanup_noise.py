"""
Dọn dẹp entities nhiễu trong data.json.
Dùng các filter giống auto_learn.py để phát hiện và xóa noise.

Chạy:
  python agent/cleanup_noise.py           # preview
  python agent/cleanup_noise.py --apply   # áp dụng
"""

import json
import logging
import os
import re
import sys
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
DATA_JSON = ROOT / "web" / "data.json"

# Tên chứa keyword ngoài VL
OUTSIDE_KEYWORDS = [
    "cần thơ", "ninh kiều", "tiền giang", "cái bè", "mỹ tho",
    "đồng tháp", "an giang", "sóc trăng", "hậu giang", "kiên giang",
    "bạc liêu", "cà mau", "long an", "hồ chí minh", "sài gòn",
    "hà nội", "đà nẵng", "huế", "nha trang", "đà lạt", "phú quốc",
    "vũng tàu", "bình dương", "đồng nai", "tây ninh",
]

TOO_GENERIC = [
    "vĩnh long", "bến tre", "trà vinh",
    "tỉnh vĩnh long", "tỉnh bến tre", "tỉnh trà vinh",
    "sông tiền", "sông hậu", "sông cổ chiên",
    "đồng bằng sông cửu long", "miền tây", "nam bộ",
    "du lịch", "ẩm thực", "văn hóa", "lịch sử",
]

LEGAL_PATTERNS = [
    r"nghị quyết", r"chỉ thị", r"quyết định", r"thông tư",
    r"số\s+\d+", r"NQ-", r"CT/TW", r"QĐ-",
    r"UBND", r"HĐND", r"vincom", r"plaza",
]


ENGLISH_MARKERS = [
    "hotel", "resort", "homestay", "hostel", "market", "floating",
    "temple", "pier", "park", "eco", "island", "beach", "village",
    "museum", "tower", "bridge", "center", "centre", "plaza",
    "garden", "farm", "river", "cruise", "tour", "airport",
]


def has_vietnamese_diacritics(text):
    return bool(re.search(r"[àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ]", text.lower()))


def is_english_name(name):
    has_vn = has_vietnamese_diacritics(name)
    name_lower = name.lower()
    for marker in ENGLISH_MARKERS:
        if marker in name_lower:
            return not has_vn
    alpha = re.sub(r"[^a-zA-ZÀ-ỹ]", "", name)
    if not alpha or len(alpha) < 6:
        return False
    if has_vn:
        return False
    return len(name.split()) >= 3


def check_noise(entity):
    """Trả về lý do nhiễu, hoặc None nếu ok."""
    name = entity.get("name", "")
    name_lower = name.lower()
    etype = entity.get("type", "")

    # Không check place entities (dữ liệu gốc)
    if etype == "place":
        return None

    # Chỉ check entities có source URL (auto-learned/crawled)
    source = entity.get("source")
    if not source or not isinstance(source, dict):
        return None
    src_url = source.get("url", "")
    if not src_url or not src_url.startswith("http"):
        return None

    # Skip vinhlongtourist (crawled, đã verified)
    if "vinhlongtourist" in src_url:
        return None

    # 1. Ngoài VL
    summary = (entity.get("summary") or "").lower()
    for kw in OUTSIDE_KEYWORDS:
        if kw in name_lower:
            if not any(vl in name_lower for vl in ["vĩnh long", "bến tre", "trà vinh"]):
                return f"ngoài VL ({kw})"
        if kw in summary and "vĩnh long" not in summary and "bến tre" not in summary and "trà vinh" not in summary:
            return f"ngoài VL trong mô tả ({kw})"

    # 2. Quá chung
    if name_lower in TOO_GENERIC:
        return "quá chung"

    # 3. Văn bản pháp luật
    for pat in LEGAL_PATTERNS:
        if re.search(pat, name_lower):
            return f"văn bản/thương mại ({pat.strip()})"

    # 4. Tiếng Anh
    if is_english_name(name):
        return "tên tiếng Anh"

    # 5. Summary quá ngắn
    if len(entity.get("summary", "")) < 10:
        return "mô tả quá ngắn"

    return None


def main():
    with open(DATA_JSON, encoding="utf-8") as f:
        data = json.load(f)

    entities = data["entities"]
    noisy = []
    clean = []

    for e in entities:
        reason = check_noise(e)
        if reason:
            noisy.append((e, reason))
        else:
            clean.append(e)

    logger.info("Cleanup Noise — total: %d, noisy: %d, clean: %d",
                len(entities), len(noisy), len(clean))

    if noisy:
        logger.info("Noisy entities:")
        for e, reason in noisy:
            logger.info("  [%s] %s (id=%s)", reason, e['name'], e['id'])

    if "--apply" in sys.argv and noisy:
        # GĐ-audit (B1-invariant): backup TRƯỚC khi xoá file dữ liệu không tái tạo được.
        try:
            import subprocess
            subprocess.run([sys.executable, str(ROOT / "scripts" / "backup_data.py")], check=False)
        except Exception as exc:
            logger.warning("Backup failed (%s) — continuing with --apply", exc)
        data["entities"] = clean
        tmp = DATA_JSON.with_suffix(".cleanup.tmp")  # ghi atomic (tránh hỏng file giữa chừng)
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(DATA_JSON)
        # GĐ-audit (B1): xoá khỏi DB (chat đọc DB) — không chỉ data.json.
        try:
            from database import db
            for e, _r in noisy:
                db.delete_entity(e["id"])  # cascade rels + FTS
        except Exception as exc:
            logger.error("DB deletion failed: %s", exc)
        logger.info("Removed %d noisy entities (DB + data.json), %d remaining",
                    len(noisy), len(clean))
    elif noisy:
        logger.info("Run with --apply to remove: python agent/cleanup_noise.py --apply")


if __name__ == "__main__":
    main()
