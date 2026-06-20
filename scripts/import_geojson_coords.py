"""
import_geojson_coords.py — GĐ3: Nhập tọa độ từ GeoJSON + CSV vào DB.

Nguồn:
  nghien_cuu_12_chieu_ban_do_diem_tuyen.geojson  (18 Point features)
  nghien_cuu_6_tang_diem_den_toa_do.csv           (cùng 18 điểm, dùng làm cross-check)

Logic:
  1. Đọc tất cả Point feature từ GeoJSON (bỏ qua LineString).
  2. Với mỗi điểm: fuzzy-match tên sang entity trong DB (ngưỡng 0.55).
  3. Nếu entity CHƯA có coordinates → đề xuất/ghi tọa độ.
  4. Nếu entity ĐÃ có coordinates → bỏ qua.
  5. Kiểm tra bbox vùng (lat 9.2–10.65, lon 105.6–106.95) trừ TP.HCM và Cần Thơ (ngoài vùng).

Chạy:
    python scripts/import_geojson_coords.py           # dry-run (mặc định)
    python scripts/import_geojson_coords.py --apply   # ghi vào DB
"""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
from difflib import SequenceMatcher
from pathlib import Path

# Force UTF-8 output on Windows (cp1252 cannot encode Vietnamese)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# ── Paths ──────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH   = REPO_ROOT / "agent" / "data" / "vinhlong360.db"
GEOJSON   = REPO_ROOT / "nghien_cuu_12_chieu_ban_do_diem_tuyen.geojson"
CSV_COORDS = REPO_ROOT / "nghien_cuu_6_tang_diem_den_toa_do.csv"

# Bbox cho vùng Vĩnh Long / Trà Vinh / Bến Tre (và phụ cận trong vùng)
LAT_MIN, LAT_MAX = 9.2, 10.65
LON_MIN, LON_MAX = 105.6, 106.95

# Ngưỡng fuzzy (0–1)
MATCH_THRESHOLD = 0.55

# ── Fuzzy matching ──────────────────────────────────────────────────────────────

_STRIP_PREFIXES = (
    "trung tâm ", "khu ", "làng ", "lễ hội ", "điểm du lịch ",
    "chùa ", "đình ", "lăng ", "biển ", "cù lao ",
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
    rows = conn.execute("SELECT id, name, type, coordinates, area FROM entities").fetchall()
    conn.close()
    result = []
    for row in rows:
        d = dict(row)
        if d.get("coordinates") and isinstance(d["coordinates"], str):
            try:
                d["coordinates"] = json.loads(d["coordinates"])
            except Exception:
                d["coordinates"] = None
        result.append(d)
    return result


def apply_coord_updates(db_path: Path, updates: list[dict]) -> None:
    """Ghi tọa độ mới vào DB. updates = [{id, lat, lon, name}]"""
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    for upd in updates:
        coords_json = json.dumps([upd["lat"], upd["lon"]])
        conn.execute(
            "UPDATE entities SET coordinates = ? WHERE id = ?",
            (coords_json, upd["id"]),
        )
    conn.commit()
    conn.close()


# ── GeoJSON loader ──────────────────────────────────────────────────────────────

def load_geojson_points(path: Path) -> list[dict]:
    """Chỉ lấy Point features."""
    with open(path, encoding="utf-8-sig") as f:
        data = json.load(f)
    points = []
    for feat in data.get("features", []):
        geom = feat.get("geometry", {})
        if geom.get("type") != "Point":
            continue
        props = feat.get("properties", {})
        lon, lat = geom["coordinates"]
        points.append(
            {
                "key":        props.get("key", ""),
                "name":       props.get("name", ""),
                "coord_note": props.get("coord_note", ""),
                "lat":        lat,
                "lon":        lon,
            }
        )
    return points


# ── CSV loader (cross-check) ────────────────────────────────────────────────────

def load_csv_coords(path: Path) -> list[dict]:
    """Đọc CSV tọa độ. Cột: key, name, q, lat, lon, coord_note, display_name"""
    result = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            try:
                lat = float(row["lat"])
                lon = float(row["lon"])
            except (ValueError, KeyError):
                continue
            result.append(
                {
                    "key":  row.get("key", "").strip(),
                    "name": row.get("name", "").strip(),
                    "lat":  lat,
                    "lon":  lon,
                }
            )
    return result


# ── Bbox guard ──────────────────────────────────────────────────────────────────

def in_region_bbox(lat: float, lon: float) -> bool:
    return LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX


# ── Main ────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Nhập tọa độ từ GeoJSON vào entities DB"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Ghi vào DB (mặc định: dry-run)",
    )
    args = parser.parse_args()
    dry_run = not args.apply

    if dry_run:
        print("[DRY-RUN] Không ghi gì vào DB. Dùng --apply để thực sự ghi.\n")

    # Load sources
    geojson_points = load_geojson_points(GEOJSON)
    csv_points     = load_csv_coords(CSV_COORDS)
    db_entities    = load_entities(DB_PATH)

    print(f"GeoJSON Point features : {len(geojson_points)}")
    print(f"CSV coord rows         : {len(csv_points)}")
    print(f"DB entities            : {len(db_entities)}")

    # Merge: geojson is primary; add any CSV key not already in geojson
    geojson_keys = {p["key"] for p in geojson_points}
    extra_csv = [p for p in csv_points if p["key"] not in geojson_keys]
    all_points = geojson_points + extra_csv
    print(f"Điểm để xử lý (sau merge): {len(all_points)}\n")

    updates: list[dict] = []
    skipped_bbox: list[str] = []
    skipped_has_coords: list[str] = []
    no_match: list[str] = []

    for pt in all_points:
        lat, lon = pt["lat"], pt["lon"]

        # Bbox guard (skip nếu ngoài vùng)
        if not in_region_bbox(lat, lon):
            skipped_bbox.append(f"  {pt['name']} ({lat:.4f}, {lon:.4f}) — NGOÀI VÙNG BBOX")
            continue

        # Fuzzy match
        entity, score = best_match(pt["name"], db_entities)

        if entity is None or score < MATCH_THRESHOLD:
            no_match.append(
                f"  [{score:.2f}] '{pt['name']}' — không khớp entity nào (ngưỡng {MATCH_THRESHOLD})"
            )
            continue

        # Kiểm tra đã có tọa độ chưa
        existing_coords = entity.get("coordinates")
        has_coords = (
            existing_coords is not None
            and existing_coords != ""
            and existing_coords != []
        )

        if has_coords:
            skipped_has_coords.append(
                f"  [{score:.2f}] '{pt['name']}' → {entity['id']} ĐÃ có coords {existing_coords}"
            )
            continue

        # Đề xuất ghi
        updates.append(
            {
                "id":         entity["id"],
                "name":       entity["name"],
                "source_name": pt["name"],
                "lat":        lat,
                "lon":        lon,
                "score":      score,
            }
        )

    # Report
    print("=== ĐỀ XUẤT GHI TỌA ĐỘ ===")
    if updates:
        for u in updates:
            action = "→ GHI" if not dry_run else "→ [sẽ ghi]"
            print(
                f"  [{u['score']:.2f}] '{u['source_name']}'"
                f" → {u['id']} ({u['name']}) "
                f"{action} [{u['lat']}, {u['lon']}]"
            )
    else:
        print("  (không có điểm nào cần ghi)")

    if skipped_has_coords:
        print(f"\n=== BỎ QUA (đã có tọa độ) [{len(skipped_has_coords)}] ===")
        for s in skipped_has_coords:
            print(s)

    if skipped_bbox:
        print(f"\n=== BỎ QUA (ngoài bbox vùng) [{len(skipped_bbox)}] ===")
        for s in skipped_bbox:
            print(s)

    if no_match:
        print(f"\n=== KHÔNG KHỚP DB [{len(no_match)}] ===")
        for s in no_match:
            print(s)

    print(f"\nTổng kết: {len(updates)} sẽ ghi | {len(skipped_has_coords)} bỏ qua (đã có) | "
          f"{len(skipped_bbox)} ngoài bbox | {len(no_match)} không khớp")

    if not dry_run and updates:
        apply_coord_updates(DB_PATH, updates)
        print(f"\n[OK] Đã ghi {len(updates)} tọa độ vào DB.")
    elif dry_run and updates:
        print("\n[DRY-RUN] Dùng --apply để thực sự ghi.")


if __name__ == "__main__":
    main()
