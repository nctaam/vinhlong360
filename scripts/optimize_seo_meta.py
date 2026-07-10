#!/usr/bin/env python3
"""Phân tích SEO metadata cho tất cả entities.

Xuất report: entity nào thiếu/yếu title, description, summary.
Suggest cải thiện (KHÔNG tự sửa — chỉ xuất CSV).

Usage:
  python scripts/optimize_seo_meta.py
  python scripts/optimize_seo_meta.py --type dish
  python scripts/optimize_seo_meta.py --min-score 50

Output: scratch/seo-audit-{date}.csv
"""

import argparse
import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENT_DIR = ROOT / "agent"
SCRATCH = ROOT / "scratch"

sys.path.insert(0, str(AGENT_DIR))

LOCATION_KEYWORDS = [
    "vĩnh long", "bến tre", "trà vinh", "vinh long", "ben tre", "tra vinh",
    "mekong", "miền tây", "đồng bằng", "sông nước",
]

TOPIC_KEYWORDS = {
    "dish": ["ẩm thực", "món ăn", "đặc sản", "hương vị", "thưởng thức", "nấu", "chế biến"],
    "drink": ["nước", "thức uống", "sinh tố", "rượu", "bia", "cà phê", "trà"],
    "experience": ["trải nghiệm", "du lịch", "tham quan", "khám phá", "tour"],
    "product": ["ocop", "sản phẩm", "đặc sản", "thủ công", "nông sản", "chất lượng"],
    "accommodation": ["khách sạn", "homestay", "nghỉ dưỡng", "phòng", "lưu trú"],
    "nature": ["thiên nhiên", "cảnh quan", "sinh thái", "vườn", "sông", "cù lao"],
    "history": ["lịch sử", "di tích", "văn hóa", "di sản", "truyền thống", "đền", "chùa"],
    "attraction": ["tham quan", "du lịch", "điểm đến", "nổi bật", "thu hút"],
    "craft_village": ["làng nghề", "thủ công", "truyền thống", "nghệ nhân", "tay nghề"],
    "event": ["lễ hội", "sự kiện", "festival", "mùa", "kỷ niệm", "hội"],
    "person": ["nhân vật", "nhà thơ", "anh hùng", "danh nhân", "nghệ sĩ", "tướng", "liệt sĩ"],
    "facility": ["bệnh viện", "trường", "chợ", "bến xe", "bưu điện", "ngân hàng"],
    "organization": ["hiệp hội", "hội", "tổ chức", "đoàn", "hợp tác xã"],
    "economy": ["kinh tế", "sản xuất", "nông nghiệp", "công nghiệp", "thương mại"],
    "cafe": ["cà phê", "quán", "không gian", "thư giãn"],
    "restaurant": ["nhà hàng", "quán ăn", "đặc sản", "ẩm thực", "buffet"],
}

BOILERPLATE_PATTERNS = [
    r"^.{0,30}$",
    r"chưa có thông tin",
    r"không có thông tin",
    r"đang cập nhật",
    r"^\s*$",
]


def load_entities(entity_type=None):
    try:
        from database import db
        entities = db.all_entities()
    except Exception:
        data_path = ROOT / "web" / "data.json"
        with open(data_path, encoding="utf-8") as f:
            data = json.load(f)
        entities = data.get("entities", [])

    entities = [e for e in entities if e.get("type") != "place"]

    if entity_type:
        entities = [e for e in entities if e.get("type") == entity_type]

    return entities


def is_boilerplate(text: str) -> bool:
    if not text:
        return True
    for pat in BOILERPLATE_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            return True
    return False


# Types exempt from certain criteria (inherently don't have this data)
CONTACT_EXEMPT = {"person", "nature", "history", "event", "itinerary", "economy"}
SEASON_EXEMPT = {"facility", "organization", "person", "itinerary",
                 "cafe", "restaurant", "history", "economy"}
LOCATION_KW_EXEMPT = {"person", "event", "itinerary"}
COORDS_EXEMPT = {"itinerary"}


def _score_summary_quality(summary: str, issues: list[str]) -> int:
    # Summary quality (max 30)
    if not summary or is_boilerplate(summary):
        issues.append("summary_missing")
        return 0
    if len(summary) < 50:
        issues.append("summary_too_short")
        return 5
    if len(summary) < 120:
        issues.append("summary_short")
        return 15
    score = 20
    if len(summary) >= 200:
        score += 10
    return score


def _score_location_kw(etype: str, summary_lower: str, issues: list[str]) -> int:
    # Location keywords in summary (+10)
    if etype in LOCATION_KW_EXEMPT:
        return 10
    if any(kw in summary_lower for kw in LOCATION_KEYWORDS):
        return 10
    issues.append("no_location_keyword")
    return 0


def _score_topic_kw(etype: str, summary_lower: str, issues: list[str]) -> int:
    # Topic keywords in summary (+10)
    type_keywords = TOPIC_KEYWORDS.get(etype, [])
    if type_keywords and any(kw in summary_lower for kw in type_keywords):
        return 10
    if type_keywords:
        issues.append("no_topic_keyword")
        return 0
    return 10


def _score_images(images, issues: list[str]) -> int:
    # Images (+15)
    if images and len(images) > 0:
        return 15
    issues.append("no_images")
    return 0


def _score_contact(etype: str, attrs: dict, issues: list[str]) -> int:
    # Contact info (+10)
    if etype in CONTACT_EXEMPT:
        return 10
    if attrs.get("phone") or attrs.get("zalo") or attrs.get("email"):
        return 10
    issues.append("no_contact")
    return 0


def _score_coords(etype: str, coords, issues: list[str]) -> int:
    # Coordinates (+10)
    if etype in COORDS_EXEMPT:
        return 10
    if coords and isinstance(coords, (list, tuple)) and len(coords) == 2:
        return 10
    issues.append("no_coords")
    return 0


def _score_season(etype: str, season, issues: list[str]) -> int:
    # Season data (+5)
    if etype in SEASON_EXEMPT:
        return 5
    if season and isinstance(season, dict) and season.get("peak"):
        return 5
    issues.append("no_season")
    return 0


def score_entity(entity: dict) -> tuple[int, list[str]]:
    score = 0
    issues = []

    summary = (entity.get("summary") or "").strip()
    description = (entity.get("description") or "").strip()
    images = entity.get("images") or []
    attrs = entity.get("attributes") or {}
    coords = entity.get("coordinates")
    season = entity.get("season")
    etype = entity.get("type", "")

    score += _score_summary_quality(summary, issues)

    summary_lower = summary.lower()

    score += _score_location_kw(etype, summary_lower, issues)
    score += _score_topic_kw(etype, summary_lower, issues)
    score += _score_images(images, issues)
    score += _score_contact(etype, attrs, issues)
    score += _score_coords(etype, coords, issues)
    score += _score_season(etype, season, issues)

    # Description bonus (+10)
    if description and len(description) > 100:
        score += 10

    return min(score, 100), issues


def suggest_title(entity: dict) -> str:
    name = entity.get("name", "")
    etype = entity.get("type", "")
    area = entity.get("area", "")
    area_label = {"vinh-long": "Vĩnh Long", "ben-tre": "Bến Tre",
                  "tra-vinh": "Trà Vinh"}.get(area, "")

    type_labels = {
        "dish": "Ẩm thực", "experience": "Trải nghiệm",
        "product": "Đặc sản", "accommodation": "Lưu trú",
        "nature": "Thiên nhiên", "history": "Di tích",
        "attraction": "Tham quan", "craft_village": "Làng nghề",
    }
    type_label = type_labels.get(etype, "")

    parts = [name]
    if type_label:
        parts.append(type_label)
    if area_label:
        parts.append(area_label)
    return " — ".join(parts)


def suggest_description(entity: dict) -> str:
    summary = (entity.get("summary") or "").strip()
    name = entity.get("name", "")
    if summary and len(summary) >= 80:
        return summary[:155]
    return f"Khám phá {name} — thông tin chi tiết, hình ảnh, đánh giá tại vinhlong360.vn"


def _build_rows(entities, min_score):
    rows = []
    for entity in entities:
        score, issues = score_entity(entity)
        if min_score and score >= min_score:
            continue
        rows.append({
            "id": entity.get("id", ""),
            "name": entity.get("name", ""),
            "type": entity.get("type", ""),
            "score": score,
            "issues": ", ".join(issues),
            "suggested_title": suggest_title(entity),
            "suggested_description": suggest_description(entity),
        })

    rows.sort(key=lambda r: r["score"])
    return rows


def _write_csv(csv_path, rows):
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "id", "name", "type", "score", "issues",
            "suggested_title", "suggested_description",
        ])
        writer.writeheader()
        writer.writerows(rows)


def _print_distribution(entities):
    # Score distribution
    brackets = {"0-30 (Kém)": 0, "31-60 (TB)": 0, "61-80 (Khá)": 0, "81-100 (Tốt)": 0}
    for entity in entities:
        s, _ = score_entity(entity)
        if s <= 30:
            brackets["0-30 (Kém)"] += 1
        elif s <= 60:
            brackets["31-60 (TB)"] += 1
        elif s <= 80:
            brackets["61-80 (Khá)"] += 1
        else:
            brackets["81-100 (Tốt)"] += 1

    total = len(entities)
    print(f"\n{'='*40}")
    print(f"SEO Score Distribution ({total} entities)")
    print(f"{'='*40}")
    for label, count in brackets.items():
        pct = count * 100 / total if total else 0
        bar = "█" * int(pct / 2)
        print(f"  {label:20s}  {count:5d}  ({pct:5.1f}%)  {bar}")


def _print_top_issues(entities):
    total = len(entities)
    # Top issues
    all_issues = {}
    for entity in entities:
        _, issues = score_entity(entity)
        for issue in issues:
            all_issues[issue] = all_issues.get(issue, 0) + 1

    print("\nTop issues:")
    for issue, count in sorted(all_issues.items(), key=lambda x: -x[1])[:10]:
        print(f"  {issue:25s}  {count:5d}  ({count*100/total:.1f}%)")


def main():
    ap = argparse.ArgumentParser(description="Phân tích SEO metadata")
    ap.add_argument("--type", dest="entity_type", help="Filter entity type")
    ap.add_argument("--min-score", type=int, default=0, help="Chỉ hiện entity dưới score này")
    args = ap.parse_args()

    entities = load_entities(args.entity_type)
    if not entities:
        print("[INFO] No entities found.")
        return

    SCRATCH.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    csv_path = SCRATCH / f"seo-audit-{date_str}.csv"

    rows = _build_rows(entities, args.min_score)

    _write_csv(csv_path, rows)

    print(f"[OK] Exported {len(rows)} entities to {csv_path}")

    _print_distribution(entities)
    _print_top_issues(entities)


if __name__ == "__main__":
    main()
