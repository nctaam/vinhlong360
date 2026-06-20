"""
import_tour_products.py — GĐ4: Nhập tour sản phẩm + ma trận tuyến đường.

Nguồn:
  nghien_cuu_12_chieu_ma_tran_san_pham.csv   → itineraries mới trong DB
  nghien_cuu_6_tang_ma_tran_tuyen_khong_gian.csv → agent/data/route_matrix.json

Cột CSV sản phẩm: product_id, product, itinerary, segments, geography, readiness, note
Cột CSV tuyến:    from, to, from_key, to_key, distance_km, duration_min, status

Logic tour:
  1. Tạo itinerary record (id sinh từ product_id, title = product).
  2. Parse cột `itinerary` (phân cách " - "): từng phần = tên điểm dừng.
  3. Fuzzy-match tên điểm dừng sang entity trong DB (ngưỡng 0.5).
  4. stops JSON = [{entityId, name, note}] (note = "" nếu không có).
  5. area = geography (chuẩn hoá sang slug nếu đơn vùng), duration suy từ readiness.
  6. summary = ghép segments + readiness + note từ CSV.
  7. Bỏ qua nếu id đã tồn tại trong DB.

Logic tuyến đường:
  Ghi toàn bộ CSV vào agent/data/route_matrix.json (không lưu DB).

Chạy:
    python scripts/import_tour_products.py           # dry-run (mặc định)
    python scripts/import_tour_products.py --apply   # ghi vào DB + JSON
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

# Force UTF-8 output on Windows (cp1252 cannot encode Vietnamese)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# ── Paths ──────────────────────────────────────────────────────────────────────

REPO_ROOT     = Path(__file__).resolve().parent.parent
DB_PATH       = REPO_ROOT / "agent" / "data" / "vinhlong360.db"
CSV_PRODUCTS  = REPO_ROOT / "nghien_cuu_12_chieu_ma_tran_san_pham.csv"
CSV_ROUTES    = REPO_ROOT / "nghien_cuu_6_tang_ma_tran_tuyen_khong_gian.csv"
ROUTE_JSON    = REPO_ROOT / "agent" / "data" / "route_matrix.json"

# Ngưỡng fuzzy khớp điểm dừng
MATCH_THRESHOLD = 0.50

# Map geography → area slug đơn vùng
AREA_MAP: dict[str, str] = {
    "Bến Tre":        "ben-tre",
    "Vĩnh Long":      "vinh-long",
    "Trà Vinh":       "tra-vinh",
    "Liên vùng":      "lien-vung",
    "Vĩnh Long; Bến Tre": "lien-vung",
    "Bến Tre; Vĩnh Long": "lien-vung",
    "Vĩnh Long; Trà Vinh": "lien-vung",
    "Trà Vinh; Vĩnh Long": "lien-vung",
}


# ── Fuzzy matching ──────────────────────────────────────────────────────────────

_STRIP_PREFIXES = (
    "trung tâm ", "khu ", "làng ", "lễ hội ", "điểm du lịch ",
    "chùa ", "đình ", "lăng ", "biển ", "cù lao ", "cồn ",
)


def _normalize(s: str) -> str:
    s = s.lower().strip()
    for prefix in _STRIP_PREFIXES:
        if s.startswith(prefix):
            s = s[len(prefix):]
            break
    return s


def fuzzy_score(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()


def best_match(
    name: str, entities: list[dict]
) -> tuple[dict | None, float]:
    best_ent, best_score = None, 0.0
    for ent in entities:
        score = fuzzy_score(name, ent["name"])
        if score > best_score:
            best_score = score
            best_ent = ent
    return best_ent, best_score


# ── DB helpers ──────────────────────────────────────────────────────────────────

def load_entities(db_path: Path) -> list[dict]:
    if not db_path.exists():
        sys.exit(f"[ERROR] DB không tồn tại: {db_path}")
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT id, name, type, area FROM entities").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def load_existing_itinerary_ids(db_path: Path) -> set[str]:
    conn = sqlite3.connect(str(db_path))
    rows = conn.execute("SELECT id FROM itineraries").fetchall()
    conn.close()
    return {r[0] for r in rows}


def insert_itineraries(db_path: Path, records: list[dict]) -> None:
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executemany(
        """INSERT OR IGNORE INTO itineraries (id, title, area, duration, summary, stops, created_at)
           VALUES (:id, :title, :area, :duration, :summary, :stops, :created_at)""",
        records,
    )
    conn.commit()
    conn.close()


# ── CSV loaders ─────────────────────────────────────────────────────────────────

def read_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


# ── Tour product processing ──────────────────────────────────────────────────────

def make_itinerary_id(product_id: str) -> str:
    """Chuyển 'P01' → 'tour-p01' v.v."""
    return "tour-" + product_id.strip().lower()


def geo_to_area(geography: str) -> str:
    """Chuyển geography thành area slug."""
    geo = geography.strip()
    if geo in AREA_MAP:
        return AREA_MAP[geo]
    # Nếu chứa ';' → liên vùng
    if ";" in geo:
        return "lien-vung"
    # Thử match đơn
    for key, slug in AREA_MAP.items():
        if geo.lower() in key.lower():
            return slug
    return "lien-vung"


def duration_from_readiness(readiness: str, itinerary_text: str) -> str:
    """Ước tính duration từ tên sản phẩm hoặc readiness."""
    text = itinerary_text.lower()
    # Ưu tiên tìm trong tên tuyến
    m = re.search(r"(\d+)[nN](\d+)[đĐdD]", text)
    if m:
        return f"{m.group(1)} ngày {m.group(2)} đêm"
    m = re.search(r"(\d+)\s*ngày", text)
    if m:
        n = int(m.group(1))
        nights = n - 1
        return f"{n} ngày{' ' + str(nights) + ' đêm' if nights > 0 else ''}"
    # Seasonal/Pilot thường là 1-2 ngày
    r = readiness.strip().lower()
    if r in ("market-ready", "seasonal"):
        return "1 ngày"
    return "1–2 ngày"


def parse_stops(
    itinerary_text: str,
    entities: list[dict],
) -> tuple[list[dict], list[str]]:
    """
    Parse chuỗi itinerary, tách thành danh sách stop.
    Trả về (stops_list, unmatched_names).
    stops_list = [{entityId, name, note}]
    """
    # Tách bởi " - " (dấu gạch giữa có khoảng trắng)
    raw_parts = re.split(r"\s*[-–]\s*", itinerary_text)

    stops: list[dict] = []
    unmatched: list[str] = []

    for part in raw_parts:
        part = part.strip()
        if not part:
            continue

        # Bỏ qua chuỗi chỉ là mô tả hoạt động (chứa toàn động từ thông thường)
        # → chỉ skip nếu là cụm rất ngắn và không có danh từ riêng
        entity, score = best_match(part, entities)

        if entity is not None and score >= MATCH_THRESHOLD:
            stops.append(
                {
                    "entityId": entity["id"],
                    "name":     entity["name"],
                    "note":     "",
                }
            )
        else:
            # Lưu tên thô nếu không khớp, không có entityId
            stops.append(
                {
                    "entityId": None,
                    "name":     part,
                    "note":     "",
                }
            )
            unmatched.append(f"    [{score:.2f}] '{part}'")

    return stops, unmatched


def build_summary(row: dict) -> str:
    """Ghép các trường thành summary."""
    parts = []
    if row.get("segments"):
        parts.append(f"Đoạn đường: {row['segments']}")
    if row.get("readiness"):
        parts.append(f"Mức sẵn sàng: {row['readiness']}")
    if row.get("note"):
        parts.append(row["note"].strip())
    return " | ".join(parts) if parts else ""


# ── Route matrix ────────────────────────────────────────────────────────────────

def build_route_matrix(rows: list[dict]) -> list[dict]:
    result = []
    for row in rows:
        try:
            distance_km  = float(row["distance_km"])
            duration_min = float(row["duration_min"])
        except (ValueError, KeyError):
            distance_km  = None
            duration_min = None
        result.append(
            {
                "from":         row.get("from", "").strip(),
                "to":           row.get("to", "").strip(),
                "from_key":     row.get("from_key", "").strip(),
                "to_key":       row.get("to_key", "").strip(),
                "distance_km":  distance_km,
                "duration_min": duration_min,
            }
        )
    return result


# ── Main ────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Nhập tour sản phẩm vào DB và route matrix vào JSON"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Ghi vào DB + route_matrix.json (mặc định: dry-run)",
    )
    args = parser.parse_args()
    dry_run = not args.apply

    if dry_run:
        print("[DRY-RUN] Không ghi gì. Dùng --apply để thực sự ghi.\n")

    # Load sources
    product_rows = read_csv(CSV_PRODUCTS)
    route_rows   = read_csv(CSV_ROUTES)
    db_entities  = load_entities(DB_PATH)
    existing_ids = load_existing_itinerary_ids(DB_PATH)

    print(f"CSV sản phẩm : {len(product_rows)} dòng")
    print(f"CSV tuyến    : {len(route_rows)} dòng")
    print(f"DB entities  : {len(db_entities)}")
    print(f"Itineraries hiện có: {len(existing_ids)}\n")

    # ── Tour products ──────────────────────────────────────────────────────────

    records_to_insert: list[dict] = []
    skip_existing: list[str] = []
    all_unmatched_stops: list[str] = []
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for row in product_rows:
        product_id   = row.get("product_id", "").strip()
        product_name = row.get("product", "").strip()
        itinerary_text = row.get("itinerary", "").strip()
        segments     = row.get("segments", "").strip()
        geography    = row.get("geography", "").strip()
        readiness    = row.get("readiness", "").strip()
        note         = row.get("note", "").strip()

        itin_id = make_itinerary_id(product_id)

        if itin_id in existing_ids:
            skip_existing.append(f"  {itin_id} ({product_name}) — đã tồn tại")
            continue

        area     = geo_to_area(geography)
        duration = duration_from_readiness(readiness, product_name + " " + itinerary_text)
        summary  = build_summary({"segments": segments, "readiness": readiness, "note": note})

        stops, unmatched = parse_stops(itinerary_text, db_entities)
        if unmatched:
            all_unmatched_stops.append(f"  {product_id} ({product_name}):")
            all_unmatched_stops.extend(unmatched)

        records_to_insert.append(
            {
                "id":         itin_id,
                "title":      product_name,
                "area":       area,
                "duration":   duration,
                "summary":    summary,
                "stops":      json.dumps(stops, ensure_ascii=False),
                "created_at": created_at,
            }
        )

    # ── Route matrix ───────────────────────────────────────────────────────────

    route_matrix = build_route_matrix(route_rows)

    # ── Reporting ──────────────────────────────────────────────────────────────

    print("=== ITINERARIES SẼ TẠO ===")
    for rec in records_to_insert:
        stops_list = json.loads(rec["stops"])
        matched = sum(1 for s in stops_list if s.get("entityId"))
        total   = len(stops_list)
        action  = "[sẽ ghi]" if dry_run else "→ GHI"
        print(
            f"  {action} {rec['id']}: {rec['title']}"
            f" | area={rec['area']} | duration={rec['duration']}"
            f" | stops={total} ({matched} khớp entity)"
        )

    if skip_existing:
        print(f"\n=== BỎ QUA (đã tồn tại) [{len(skip_existing)}] ===")
        for s in skip_existing:
            print(s)

    if all_unmatched_stops:
        print(f"\n=== ĐIỂM DỪNG KHÔNG KHỚP ENTITY ===")
        for s in all_unmatched_stops:
            print(s)

    print(f"\n=== ROUTE MATRIX ({len(route_matrix)} tuyến) ===")
    for r in route_matrix:
        print(
            f"  {r['from_key']} → {r['to_key']}"
            f" | {r['distance_km']} km / {r['duration_min']} phút"
        )

    print(
        f"\nTổng kết: {len(records_to_insert)} itinerary sẽ tạo | "
        f"{len(skip_existing)} bỏ qua | "
        f"{len(route_matrix)} tuyến cho route_matrix.json"
    )

    if not dry_run:
        if records_to_insert:
            insert_itineraries(DB_PATH, records_to_insert)
            print(f"\n[OK] Đã ghi {len(records_to_insert)} itinerary vào DB.")
        ROUTE_JSON.parent.mkdir(parents=True, exist_ok=True)
        with open(ROUTE_JSON, "w", encoding="utf-8") as f:
            json.dump(route_matrix, f, ensure_ascii=False, indent=2)
        print(f"[OK] Đã ghi route_matrix.json ({len(route_matrix)} tuyến) → {ROUTE_JSON}")
    elif dry_run:
        print("\n[DRY-RUN] Dùng --apply để thực sự ghi.")


if __name__ == "__main__":
    main()
