"""
enrich_segments_tips.py — Bổ sung phân khúc khách + tips du lịch có trách nhiệm + mô tả văn hóa sâu.

Đọc 3 file CSV nghiên cứu GPT 5.5:
  1. nghien_cuu_12_chieu_phan_khuc_khach.csv   (10 phân khúc khách)
  2. nghien_cuu_12_chieu_rui_ro_bao_ton_moi_truong.csv (12 rủi ro)
  3. danh_muc_chuyen_sau_dia_diem_le_hoi_van_hoa_vl_tv_bt.csv (21 hồ sơ chi tiết)

Khớp fuzzy với entity trong DB → cập nhật attributes JSON:
  - target_segments: ["SEG01: Khách TP.HCM cuối tuần", ...]
  - responsible_tips: ["Áo phao bắt buộc khi đi ghe", ...]
  - culture_note: "Không gian cư trú ven sông Tiền..."
  - experience_note: "Đi ghe/đò, đạp xe..."

Chạy:
    python scripts/enrich_segments_tips.py          # dry-run
    python scripts/enrich_segments_tips.py --apply  # ghi vào DB
"""

import argparse
import csv
import json
import sqlite3
import sys
from difflib import SequenceMatcher
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "agent" / "data" / "vinhlong360.db"

CSV_SEGMENTS = REPO_ROOT / "nghien_cuu_12_chieu_phan_khuc_khach.csv"
CSV_RISKS = REPO_ROOT / "nghien_cuu_12_chieu_rui_ro_bao_ton_moi_truong.csv"
CSV_DETAIL = REPO_ROOT / "danh_muc_chuyen_sau_dia_diem_le_hoi_van_hoa_vl_tv_bt.csv"

MATCH_THRESHOLD = 0.55


def read_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _normalize(s: str) -> str:
    s = s.lower().strip()
    for prefix in ("khu ", "làng ", "lễ hội ", "điểm du lịch ", "chùa ", "đình ",
                    "cù lao ", "cồn ", "bảo tàng "):
        if s.startswith(prefix):
            s = s[len(prefix):]
    return s


GENERIC_TERMS = {"sông", "gốm", "khmer", "di tích", "homestay", "lễ hội", "làng nghề",
                  "toàn vùng", "ẩm thực", "chùa", "đình", "cồn", "biển", "vườn",
                  "nghề", "ông", "chợ", "lăng", "bảo tàng"}

MIN_NAME_LEN = 4


def fuzzy_match(name: str, entities: list[dict], threshold: float = MATCH_THRESHOLD) -> dict | None:
    raw = name.lower().strip()
    norm_name = _normalize(name)
    if raw in GENERIC_TERMS or norm_name in GENERIC_TERMS or len(norm_name) < MIN_NAME_LEN:
        return None
    best_score = 0.0
    best_entity = None
    for ent in entities:
        ent_name = _normalize(ent["name"])
        score = SequenceMatcher(None, norm_name, ent_name).ratio()
        if len(norm_name) >= 5 and len(ent_name) >= 5 and (ent_name in norm_name or norm_name in ent_name):
            score = max(score, 0.75)
        if score > best_score:
            best_score = score
            best_entity = ent
    if best_score >= threshold and best_entity:
        return {**best_entity, "_match_score": best_score}
    return None


def load_entities(conn: sqlite3.Connection) -> list[dict]:
    cur = conn.execute("SELECT id, name, type, attributes FROM entities")
    result = []
    for row in cur:
        attrs = {}
        if row[3]:
            try:
                attrs = json.loads(row[3])
            except (json.JSONDecodeError, TypeError):
                pass
        result.append({"id": row[0], "name": row[1], "type": row[2], "attributes": attrs})
    return result


def build_segment_map(segments: list[dict]) -> dict[str, list[str]]:
    """Map asset name → list of segment labels."""
    asset_segments: dict[str, list[str]] = {}
    for seg in segments:
        seg_label = f"{seg['segment_id']}: {seg['segment']}"
        assets = [a.strip() for a in seg.get("best_assets", "").split(",") if a.strip()]
        for asset in assets:
            asset_segments.setdefault(asset, []).append(seg_label)
    return asset_segments


def build_risk_map(risks: list[dict]) -> dict[str, list[str]]:
    """Map location name → list of mitigation tips."""
    location_tips: dict[str, list[str]] = {}
    for risk in risks:
        scope_items = [s.strip() for s in risk.get("scope", "").split(",") if s.strip()]
        mitigation = risk.get("mitigation", "").strip()
        if not mitigation:
            continue
        tip = f"{risk['risk']}: {mitigation}"
        for loc in scope_items:
            location_tips.setdefault(loc, []).append(tip)
    return location_tips


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Ghi vào DB (mặc định: dry-run)")
    args = parser.parse_args()

    conn = sqlite3.connect(str(DB_PATH))
    entities = load_entities(conn)
    print(f"[db] {len(entities)} entities loaded")

    segments = read_csv(CSV_SEGMENTS)
    risks = read_csv(CSV_RISKS)
    details = read_csv(CSV_DETAIL)

    print(f"[csv] {len(segments)} segments, {len(risks)} risks, {len(details)} detail records")

    # ── 1. Segment tagging ──
    segment_map = build_segment_map(segments)
    segment_updates = []
    for asset_name, seg_labels in segment_map.items():
        match = fuzzy_match(asset_name, entities)
        if match:
            existing = match["attributes"].get("target_segments", [])
            if not existing:
                segment_updates.append({
                    "id": match["id"],
                    "name": match["name"],
                    "asset_name": asset_name,
                    "score": match["_match_score"],
                    "target_segments": seg_labels,
                })

    print(f"\n── Segment tagging: {len(segment_updates)} entities ──")
    for u in segment_updates:
        print(f"  {u['name']} (matched '{u['asset_name']}', score={u['score']:.2f})")
        for s in u["target_segments"]:
            print(f"    + {s}")

    # ── 2. Responsible travel tips ──
    risk_map = build_risk_map(risks)
    tip_updates = []
    for loc_name, tips in risk_map.items():
        match = fuzzy_match(loc_name, entities)
        if match:
            existing = match["attributes"].get("responsible_tips", [])
            if not existing:
                tip_updates.append({
                    "id": match["id"],
                    "name": match["name"],
                    "loc_name": loc_name,
                    "score": match["_match_score"],
                    "responsible_tips": tips,
                })

    print(f"\n── Responsible tips: {len(tip_updates)} entities ──")
    for u in tip_updates:
        print(f"  {u['name']} (matched '{u['loc_name']}', score={u['score']:.2f})")
        for t in u["responsible_tips"]:
            print(f"    + {t[:80]}...")

    # ── 3. Culture/experience notes from detail catalog ──
    detail_updates = []
    for detail in details:
        detail_name = detail.get("name", "").strip()
        if not detail_name:
            continue
        match = fuzzy_match(detail_name, entities)
        if match:
            culture = detail.get("culture", "").strip()
            experience = detail.get("experience", "").strip()
            tour_note = detail.get("tour", "").strip()
            risk_note = detail.get("risk", "").strip()

            existing_culture = match["attributes"].get("culture_note", "")
            existing_experience = match["attributes"].get("experience_note", "")

            if (culture or experience) and not (existing_culture and existing_experience):
                detail_updates.append({
                    "id": match["id"],
                    "name": match["name"],
                    "detail_name": detail_name,
                    "score": match["_match_score"],
                    "culture_note": culture,
                    "experience_note": experience,
                    "tour_note": tour_note,
                    "risk_note": risk_note,
                })

    print(f"\n── Culture/experience notes: {len(detail_updates)} entities ──")
    for u in detail_updates:
        print(f"  {u['name']} (matched '{u['detail_name']}', score={u['score']:.2f})")
        if u["culture_note"]:
            print(f"    culture: {u['culture_note'][:80]}...")
        if u["experience_note"]:
            print(f"    experience: {u['experience_note'][:80]}...")
        if u["tour_note"]:
            print(f"    tour: {u['tour_note'][:80]}...")

    # ── Apply ──
    total = len(segment_updates) + len(tip_updates) + len(detail_updates)
    if not args.apply:
        print(f"\n[dry-run] {total} updates would be applied. Run with --apply to write.")
        conn.close()
        return

    print(f"\n[apply] Writing {total} updates to DB...")

    def update_attrs(entity_id: str, new_fields: dict):
        cur = conn.execute("SELECT attributes FROM entities WHERE id = ?", (entity_id,))
        row = cur.fetchone()
        attrs = {}
        if row and row[0]:
            try:
                attrs = json.loads(row[0])
            except (json.JSONDecodeError, TypeError):
                pass
        attrs.update(new_fields)
        conn.execute("UPDATE entities SET attributes = ? WHERE id = ?",
                      (json.dumps(attrs, ensure_ascii=False), entity_id))

    for u in segment_updates:
        update_attrs(u["id"], {"target_segments": u["target_segments"]})

    for u in tip_updates:
        update_attrs(u["id"], {"responsible_tips": u["responsible_tips"]})

    for u in detail_updates:
        fields = {}
        if u["culture_note"]:
            fields["culture_note"] = u["culture_note"]
        if u["experience_note"]:
            fields["experience_note"] = u["experience_note"]
        if u["tour_note"]:
            fields["tour_note"] = u["tour_note"]
        if u["risk_note"]:
            fields["risk_note"] = u["risk_note"]
        if fields:
            update_attrs(u["id"], fields)

    conn.commit()
    conn.close()
    print(f"[done] {total} entities enriched.")


if __name__ == "__main__":
    main()
