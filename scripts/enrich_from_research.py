"""
enrich_from_research.py — Làm giàu entity từ CSV nghiên cứu GPT 5.5.

Đọc 3 file CSV nghiên cứu:
  - nghien_cuu_12_chieu_catalog_62_tai_nguyen.csv   (62 tài nguyên)
  - danh_muc_chuyen_sau_dia_diem_le_hoi_van_hoa_vl_tv_bt.csv  (21 hồ sơ chi tiết)
  - nghien_cuu_6_tang_diem_den_toa_do.csv           (17 tọa độ)

Khớp fuzzy với entity trong DB (difflib, ngưỡng 0.6).
Cập nhật: description, attributes JSON, coordinates, season — chỉ khi trường đang rỗng/quá ngắn.
Entity KHÔNG khớp → log ra stdout để con người xét duyệt, KHÔNG tự tạo mới.

Dùng --dry-run (mặc định) để xem những gì sẽ thay đổi.
Dùng --apply để thực sự ghi vào DB.

Chạy:
    python scripts/enrich_from_research.py
    python scripts/enrich_from_research.py --apply
"""

import argparse
import csv
import json
import sqlite3
import sys
from difflib import SequenceMatcher
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "agent" / "data" / "vinhlong360.db"

CSV_CATALOG = REPO_ROOT / "nghien_cuu_12_chieu_catalog_62_tai_nguyen.csv"
CSV_DETAIL  = REPO_ROOT / "danh_muc_chuyen_sau_dia_diem_le_hoi_van_hoa_vl_tv_bt.csv"
CSV_COORDS  = REPO_ROOT / "nghien_cuu_6_tang_diem_den_toa_do.csv"

# Ngưỡng tương đồng tên (0–1). Giá trị 0.6 = tối thiểu để tính là "khớp".
MATCH_THRESHOLD = 0.6

# Mô tả ngắn tối thiểu để coi là "đã có nội dung" — dưới ngưỡng này sẽ bị ghi đè.
MIN_DESCRIPTION_LEN = 30
MIN_SEASON_LEN = 5


# ── CSV helpers ─────────────────────────────────────────────────────────────────

def read_csv(path: Path) -> list[dict]:
    """Đọc CSV UTF-8-BOM, trả về list of dict."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


# ── Fuzzy matching ──────────────────────────────────────────────────────────────

def _normalize(s: str) -> str:
    """Chuẩn hóa nhẹ để so sánh: lower, bỏ dấu gạch, bỏ tiền tố phổ biến."""
    s = s.lower().strip()
    # Bỏ một số từ bổ trợ không ảnh hưởng nhận dạng
    for prefix in ("khu ", "làng ", "lễ hội ", "điểm du lịch ", "chùa ", "đình "):
        if s.startswith(prefix):
            s = s[len(prefix):]
            break
    return s


def fuzzy_score(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()


def best_match(research_name: str, db_entities: list[dict]) -> tuple[dict | None, float]:
    """Tìm entity DB khớp nhất với tên nghiên cứu. Trả (entity, score)."""
    best_entity = None
    best_score = 0.0
    for ent in db_entities:
        score = fuzzy_score(research_name, ent["name"])
        if score > best_score:
            best_score = score
            best_entity = ent
    return best_entity, best_score


# ── DB helpers ──────────────────────────────────────────────────────────────────

def load_db_entities(db_path: Path) -> list[dict]:
    """Nạp tất cả entity (kể cả place) từ SQLite, parse JSON fields."""
    if not db_path.exists():
        print(f"[WARN] DB không tồn tại tại {db_path}", file=sys.stderr)
        return []
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM entities").fetchall()
    conn.close()

    entities = []
    for row in rows:
        d = dict(row)
        for field in ("season", "attributes", "source", "images", "coordinates"):
            if d.get(field) and isinstance(d[field], str):
                try:
                    d[field] = json.loads(d[field])
                except Exception:
                    pass
        entities.append(d)
    return entities


def apply_updates(db_path: Path, updates: list[dict]):
    """Ghi các bản cập nhật vào DB. Mỗi update có dạng:
       { 'id': ..., 'description'?: ..., 'attributes'?: {...}, 'coordinates'?: [...], 'season'?: ... }
    """
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    for upd in updates:
        eid = upd["id"]
        sets = []
        params = []

        if "description" in upd:
            sets.append("description = ?")
            params.append(upd["description"])

        if "attributes" in upd:
            sets.append("attributes = ?")
            params.append(json.dumps(upd["attributes"], ensure_ascii=False))

        if "coordinates" in upd:
            sets.append("coordinates = ?")
            params.append(json.dumps(upd["coordinates"], ensure_ascii=False))

        if "season" in upd:
            sets.append("season = ?")
            val = upd["season"]
            params.append(json.dumps(val, ensure_ascii=False) if not isinstance(val, str) else val)

        if not sets:
            continue

        params.append(eid)
        conn.execute(f"UPDATE entities SET {', '.join(sets)} WHERE id = ?", params)

    conn.commit()
    conn.close()


# ── Build enrichment data from CSVs ────────────────────────────────────────────

def build_catalog_map(rows: list[dict]) -> dict[str, dict]:
    """Tạo dict name -> catalog row (từ 62-tài-nguyên CSV)."""
    return {r["name"].strip(): r for r in rows}


def build_detail_map(rows: list[dict]) -> dict[str, dict]:
    """Tạo dict name -> detail row (từ 21-hồ-sơ CSV)."""
    return {r["name"].strip(): r for r in rows}


def build_coord_map(rows: list[dict]) -> dict[str, dict]:
    """Tạo dict name -> coord row (từ tọa-độ CSV)."""
    return {r["name"].strip(): r for r in rows}


# ── Region bbox guard (khớp với database.py) ────────────────────────────────────
_REGION_BBOX = (9.2, 10.65, 105.6, 106.95)  # lat_min, lat_max, lng_min, lng_max


def coords_in_region(lat: float, lon: float) -> bool:
    return _REGION_BBOX[0] <= lat <= _REGION_BBOX[1] and _REGION_BBOX[2] <= lon <= _REGION_BBOX[3]


# ── Core enrichment logic ───────────────────────────────────────────────────────

def compute_enrichment(
    db_entity: dict,
    catalog_row: dict | None,
    detail_row: dict | None,
    coord_row: dict | None,
) -> dict | None:
    """
    Tính bộ thay đổi cần áp dụng cho entity DB.
    Trả None nếu không có gì cần cập nhật.
    """
    changes = {}
    eid = db_entity["id"]

    # ── description ──────────────────────────────────────────────────────────
    existing_desc = (db_entity.get("description") or "").strip()
    if len(existing_desc) < MIN_DESCRIPTION_LEN:
        parts = []
        if detail_row:
            culture = (detail_row.get("culture") or "").strip()
            experience = (detail_row.get("experience") or "").strip()
            if culture:
                parts.append(culture)
            if experience:
                parts.append(experience)
        if catalog_row:
            cultural_value = (catalog_row.get("cultural_value") or "").strip()
            if cultural_value and cultural_value not in " ".join(parts):
                parts.append(cultural_value)
        new_desc = " ".join(p for p in parts if p)
        if new_desc and len(new_desc) > len(existing_desc):
            changes["description"] = new_desc

    # ── attributes (merge, không ghi đè) ─────────────────────────────────────
    existing_attrs = db_entity.get("attributes") or {}
    if isinstance(existing_attrs, str):
        try:
            existing_attrs = json.loads(existing_attrs)
        except Exception:
            existing_attrs = {}
    new_attrs = dict(existing_attrs)

    def _set_if_missing(key: str, value):
        """Chỉ thêm nếu key chưa có hoặc rỗng."""
        if key not in new_attrs or not new_attrs[key]:
            if value:
                new_attrs[key] = value

    if catalog_row:
        _set_if_missing("priority",          (catalog_row.get("priority") or "").strip() or None)
        _set_if_missing("target_segments",   (catalog_row.get("target_segments") or "").strip() or None)
        _set_if_missing("suggested_duration",(catalog_row.get("suggested_duration") or "").strip() or None)
        _set_if_missing("role",              (catalog_row.get("role") or "").strip() or None)

    if detail_row:
        _set_if_missing("risk",   (detail_row.get("risk") or "").strip() or None)
        _set_if_missing("tour",   (detail_row.get("tour") or "").strip() or None)
        # source links (corpus + official) — lưu riêng để dễ dùng
        corpus = (detail_row.get("corpus") or "").strip()
        official = (detail_row.get("official") or "").strip()
        if corpus:
            _set_if_missing("source_corpus", corpus)
        if official:
            _set_if_missing("source_official", official)

    # Ghi attributes chỉ khi thực sự có thay đổi
    if new_attrs != existing_attrs:
        changes["attributes"] = new_attrs

    # ── coordinates ─────────────────────────────────────────────────────────
    existing_coords = db_entity.get("coordinates")
    if not existing_coords and coord_row:
        try:
            lat = float(coord_row["lat"])
            lon = float(coord_row["lon"])
            if coords_in_region(lat, lon):
                changes["coordinates"] = [lat, lon]
        except (ValueError, KeyError, TypeError):
            pass

    # ── season ───────────────────────────────────────────────────────────────
    existing_season = db_entity.get("season")
    # season trong DB có thể là str hoặc list/dict
    existing_season_str = ""
    if isinstance(existing_season, str):
        existing_season_str = existing_season
    elif existing_season:
        existing_season_str = json.dumps(existing_season, ensure_ascii=False)

    if len(existing_season_str) < MIN_SEASON_LEN:
        new_season = ""
        if detail_row:
            new_season = (detail_row.get("season") or "").strip()
        if not new_season and catalog_row:
            new_season = (catalog_row.get("season") or "").strip()
        if new_season and len(new_season) > len(existing_season_str):
            changes["season"] = new_season

    if not changes:
        return None
    changes["id"] = eid
    return changes


# ── Main ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Làm giàu entity DB từ CSV nghiên cứu. Mặc định: dry-run."
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="Thực sự ghi thay đổi vào DB (mặc định chỉ xem trước / dry-run)."
    )
    parser.add_argument(
        "--threshold", type=float, default=MATCH_THRESHOLD,
        help=f"Ngưỡng fuzzy match (0–1, mặc định {MATCH_THRESHOLD})."
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="In chi tiết từng match."
    )
    args = parser.parse_args()

    dry_run = not args.apply
    threshold = args.threshold

    print("=" * 70)
    print(f"  enrich_from_research.py  {'(DRY-RUN — không ghi)' if dry_run else '(APPLY — GHI VÀO DB)'}")
    print("=" * 70)

    # ── Load CSVs ──────────────────────────────────────────────────────────
    for p in (CSV_CATALOG, CSV_DETAIL, CSV_COORDS):
        if not p.exists():
            print(f"[ERROR] Không tìm thấy file: {p}", file=sys.stderr)
            sys.exit(1)

    catalog_rows = read_csv(CSV_CATALOG)
    detail_rows  = read_csv(CSV_DETAIL)
    coord_rows   = read_csv(CSV_COORDS)

    print(f"\nĐã đọc CSV:")
    print(f"  catalog  : {len(catalog_rows)} dòng  ({CSV_CATALOG.name})")
    print(f"  detail   : {len(detail_rows)} dòng  ({CSV_DETAIL.name})")
    print(f"  coords   : {len(coord_rows)} dòng  ({CSV_COORDS.name})")

    catalog_map = build_catalog_map(catalog_rows)
    detail_map  = build_detail_map(detail_rows)
    coord_map   = build_coord_map(coord_rows)

    # ── Load DB entities ───────────────────────────────────────────────────
    db_entities = load_db_entities(DB_PATH)
    if not db_entities:
        print("[ERROR] Không có entity nào trong DB hoặc DB chưa tồn tại.", file=sys.stderr)
        sys.exit(1)
    print(f"\nEntity trong DB: {len(db_entities)}")

    # ── Collect tất cả tên nghiên cứu cần xét ─────────────────────────────
    # Ưu tiên detail (21 hồ sơ chi tiết), sau đó catalog (62 tài nguyên),
    # sau đó coords (17 tọa độ). Gộp tên unique.
    research_names: list[str] = []
    seen: set[str] = set()

    def _add(name: str):
        n = name.strip()
        if n and n not in seen:
            seen.add(n)
            research_names.append(n)

    for r in detail_rows:
        _add(r.get("name", ""))
    for r in catalog_rows:
        _add(r.get("name", ""))
    for r in coord_rows:
        _add(r.get("name", ""))

    print(f"Tên nghiên cứu unique cần khớp: {len(research_names)}")

    # ── Fuzzy match + compute enrichment ──────────────────────────────────
    matched_count   = 0
    enriched_count  = 0
    unmatched_count = 0
    skipped_count   = 0  # matched nhưng không có gì mới để bổ sung

    updates_to_apply: list[dict] = []
    unmatched_names: list[str]   = []

    for rname in research_names:
        entity, score = best_match(rname, db_entities)

        if score < threshold:
            unmatched_count += 1
            unmatched_names.append(rname)
            if args.verbose:
                best_name = entity["name"] if entity else "N/A"
                print(f"  [UNMATCHED] '{rname}'  best_score={score:.2f}  (best_db='{best_name}')")
            continue

        matched_count += 1
        if args.verbose:
            print(f"  [MATCH] '{rname}' → '{entity['name']}'  score={score:.2f}")

        # Lấy data từ cả 3 nguồn
        c_row = catalog_map.get(rname)
        d_row = detail_map.get(rname)
        coord_row = coord_map.get(rname)

        # Nếu không khớp trực tiếp với tên, thử lại bằng fuzzy trên từng map
        def _fuzzy_lookup(mapping: dict) -> dict | None:
            best_v, best_s = None, 0.0
            for k, v in mapping.items():
                s = fuzzy_score(rname, k)
                if s > best_s:
                    best_s, best_v = s, v
            return best_v if best_s >= threshold else None

        if not c_row:
            c_row = _fuzzy_lookup(catalog_map)
        if not d_row:
            d_row = _fuzzy_lookup(detail_map)
        if not coord_row:
            coord_row = _fuzzy_lookup(coord_map)

        changes = compute_enrichment(entity, c_row, d_row, coord_row)

        if changes is None:
            skipped_count += 1
            if args.verbose:
                print(f"    → Bỏ qua (không có trường nào cần bổ sung)")
            continue

        enriched_count += 1
        updates_to_apply.append(changes)

        # In preview
        field_names = [k for k in changes if k != "id"]
        print(f"\n  [{entity['id']}] '{entity['name']}'  (score={score:.2f})")
        for k in field_names:
            v = changes[k]
            if isinstance(v, str):
                preview = v[:120] + ("…" if len(v) > 120 else "")
            else:
                preview = str(v)
            print(f"    {k}: {preview}")

    # ── In danh sách UNMATCHED ────────────────────────────────────────────
    if unmatched_names:
        print("\n" + "─" * 70)
        print(f"KHÔNG KHỚP ({unmatched_count}) — cần xét duyệt thủ công (KHÔNG tự tạo mới):")
        for n in unmatched_names:
            print(f"  • {n}")

    # ── Summary ───────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  TỔNG KẾT")
    print("=" * 70)
    print(f"  Tên nghiên cứu đã xét  : {len(research_names)}")
    print(f"  Khớp DB                : {matched_count}")
    print(f"  Sẽ làm giàu            : {enriched_count}")
    print(f"  Bỏ qua (đã đủ dữ liệu): {skipped_count}")
    print(f"  Không khớp             : {unmatched_count}")

    if dry_run:
        print("\n  [DRY-RUN] Không có thay đổi nào được ghi.")
        print("  Chạy lại với --apply để ghi thực sự.")
    else:
        if updates_to_apply:
            apply_updates(DB_PATH, updates_to_apply)
            print(f"\n  [APPLY] Đã ghi {len(updates_to_apply)} bản cập nhật vào {DB_PATH}")
        else:
            print("\n  [APPLY] Không có gì để ghi.")

    print("=" * 70)


if __name__ == "__main__":
    main()
