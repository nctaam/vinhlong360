#!/usr/bin/env python3
"""Tối ưu chất lượng dữ liệu — phát hiện và sửa các vấn đề phổ biến.

Chế độ mặc định: dry-run (chỉ báo cáo, không sửa).
Dùng --apply để thực sự sửa data (BẮT BUỘC backup trước).

Modules:
  1. near-symmetry    — thêm quan hệ "near" ngược cho các cặp 1 chiều
  2. timestamps       — sửa created_at > updatedAt (do import DB)
  3. phones           — chuẩn hoá SĐT về format VN (+84/0...)
  4. coord-clusters   — báo cáo entities dùng toạ độ trung tâm thành phố
  5. summaries        — báo cáo summary quá ngắn/bị cắt

Usage:
  python scripts/optimize_data.py                  # dry-run tất cả
  python scripts/optimize_data.py --apply           # sửa tất cả
  python scripts/optimize_data.py --module near     # chỉ chạy 1 module
  python scripts/optimize_data.py --module phones --apply
"""

import argparse
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENT_DIR = ROOT / "agent"
sys.path.insert(0, str(AGENT_DIR))

CITY_CENTERS = {
    "vinh-long": (10.254177, 105.962769),
    "ben-tre":   (10.227225, 106.407197),
    "tra-vinh":  (9.951624,  106.332233),
}
CLUSTER_RADIUS = 0.0005  # ~55m

VN_PHONE_RE = re.compile(r'(\+84|0)\d{9,10}')
VN_TOLLFREE_RE = re.compile(r'1[89]00\s?\d{4,6}')
PHONE_CLEAN_RE = re.compile(r'[\s.\-()]')


def _is_city_center(coords, threshold=CLUSTER_RADIUS):
    if not coords or not isinstance(coords, (list, tuple)) or len(coords) != 2:
        return None
    lat, lon = coords[0], coords[1]
    for city, (clat, clon) in CITY_CENTERS.items():
        if abs(lat - clat) < threshold and abs(lon - clon) < threshold:
            return city
    return None


# ──────────────────────────────────────────────
# Module 1: Near-relationship symmetry
# ──────────────────────────────────────────────

def fix_near_symmetry(db, apply=False):
    rels = db.all_relationships()
    near_set = set()
    for r in rels:
        if r["type"] == "near":
            near_set.add((r["from"], r["to"]))

    missing = []
    for (a, b) in list(near_set):
        if (b, a) not in near_set:
            missing.append((b, a))

    print(f"\n{'='*50}")
    print(f"[near-symmetry] {len(near_set)} near relationships")
    print(f"  Missing reverse: {len(missing)}")

    if not missing:
        print("  OK — all symmetric")
        return 0

    if apply:
        added = 0
        for from_id, to_id in missing:
            db.add_relationship(from_id, to_id, "near")
            added += 1
        print(f"  APPLIED: added {added} reverse relationships")
    else:
        print(f"  DRY-RUN: would add {len(missing)} reverse relationships")
        for a, b in missing[:5]:
            print(f"    {a} <-> {b}")
        if len(missing) > 5:
            print(f"    ... and {len(missing)-5} more")

    return len(missing)


# ──────────────────────────────────────────────
# Module 2: Timestamp inversions
# ──────────────────────────────────────────────

def fix_timestamps(db, apply=False):
    entities = db.all_entities()
    inversions = []
    for e in entities:
        ca = e.get("created_at", "")
        ua = e.get("updatedAt", "")
        if ca and ua and str(ua) < str(ca):
            inversions.append(e)

    print(f"\n{'='*50}")
    print(f"[timestamps] {len(entities)} entities")
    print(f"  Inversions (updatedAt < created_at): {len(inversions)}")

    if not inversions:
        print("  OK — no inversions")
        return 0

    if apply:
        conn_ctx = db._conn()
        conn = conn_ctx.__enter__()
        try:
            fixed = 0
            for e in inversions:
                ua = e.get("updatedAt", "")
                ua_clean = str(ua).replace("T", " ").replace("Z", "")[:19]
                if db._use_pg:
                    db._execute(conn,
                        "UPDATE entities SET created_at = %s WHERE id = %s",
                        (ua_clean, e["id"]))
                else:
                    conn.execute(
                        "UPDATE entities SET created_at = ? WHERE id = ?",
                        (ua_clean, e["id"]))
                fixed += 1
            conn_ctx.__exit__(None, None, None)
            print(f"  APPLIED: fixed {fixed} timestamp inversions")
        except Exception as ex:
            conn_ctx.__exit__(type(ex), ex, ex.__traceback__)
            print(f"  ERROR: {ex}")
            return -1
    else:
        print(f"  DRY-RUN: would fix {len(inversions)} inversions")
        for e in inversions[:3]:
            print(f"    {e['id']}: created={e.get('created_at')} updated={e.get('updatedAt')}")

    return len(inversions)


# ──────────────────────────────────────────────
# Module 3: Phone normalization
# ──────────────────────────────────────────────

def fix_phones(db, apply=False):
    entities = db.all_entities()
    issues = []

    for e in entities:
        attrs = e.get("attributes") or {}
        phone = attrs.get("phone", "")
        if not phone:
            continue

        cleaned = PHONE_CLEAN_RE.sub("", phone)

        if VN_PHONE_RE.fullmatch(cleaned) and cleaned == phone:
            continue
        tollfree_clean = re.sub(r'\s', '', phone.split("(")[0].split("|")[0].strip())
        if re.fullmatch(r'1[89]00\d{4,6}', tollfree_clean) and tollfree_clean == phone:
            continue

        if VN_PHONE_RE.fullmatch(cleaned):
            issues.append({
                "id": e["id"], "type": e.get("type", ""),
                "original": phone, "primary": cleaned,
                "is_note": False, "all_numbers": [cleaned],
            })
            continue
        if re.fullmatch(r'1[89]00\d{4,6}', tollfree_clean):
            issues.append({
                "id": e["id"], "type": e.get("type", ""),
                "original": phone, "primary": tollfree_clean,
                "is_note": False, "all_numbers": [tollfree_clean],
            })
            continue

        NOT_A_PHONE = ["chưa", "không", "chưa xác", "không tìm",
                       "đang cập nhật", "liên hệ", "xxxx", "xxx "]
        is_note = any(kw in phone.lower() for kw in NOT_A_PHONE)

        nums = [m.group() for m in VN_PHONE_RE.finditer(cleaned)]
        tollfree = [m.group().replace(" ", "")
                    for m in VN_TOLLFREE_RE.finditer(phone)]

        if is_note:
            primary = ""
        else:
            primary = nums[0] if nums else (tollfree[0] if tollfree else None)

        issues.append({
            "id": e["id"],
            "type": e.get("type", ""),
            "original": phone,
            "primary": primary,
            "is_note": is_note,
            "all_numbers": nums + tollfree,
        })

    print(f"\n{'='*50}")
    print(f"[phones] Non-standard phone formats: {len(issues)}")

    if not issues:
        print("  OK — all phones valid")
        return 0

    fixable = [i for i in issues if i["primary"] is not None]
    unfixable = [i for i in issues if i["primary"] is None]
    notes = [i for i in fixable if i.get("is_note")]
    phone_fixes = [i for i in fixable if not i.get("is_note")]

    print(f"  Phone normalization: {len(phone_fixes)}")
    print(f"  Note → clear phone: {len(notes)}")
    print(f"  Needs manual review: {len(unfixable)}")

    if apply and fixable:
        fixed = 0
        for issue in fixable:
            e = db.get_entity(issue["id"])
            if not e:
                continue
            attrs = dict(e.get("attributes") or {})
            old_phone = attrs.get("phone", "")
            attrs["phone"] = issue["primary"]
            if len(issue["all_numbers"]) > 1 or old_phone != issue["primary"]:
                attrs["phone_note"] = old_phone
            e["attributes"] = attrs
            db.upsert_entity(e)
            fixed += 1
        print(f"  APPLIED: normalized {fixed} phone numbers")
    else:
        print("\n  DRY-RUN samples:")
        for i in issues[:8]:
            arrow = f" -> {i['primary']}" if i["primary"] else " -> (needs manual)"
            print(f"    {i['id'][:45]:45s} {i['original'][:50]}{arrow}")

    if unfixable:
        print("\n  Manual review needed:")
        for i in unfixable[:5]:
            print(f"    {i['id'][:45]:45s} {i['original'][:60]}")

    return len(issues)


# ──────────────────────────────────────────────
# Module 4: Coordinate clusters
# ──────────────────────────────────────────────

def audit_coord_clusters(db, apply=False):
    entities = db.all_entities()
    center_entities = {}

    for e in entities:
        city = _is_city_center(e.get("coordinates"))
        if city:
            center_entities.setdefault(city, []).append(e)

    total_affected = sum(len(v) for v in center_entities.values())
    print(f"\n{'='*50}")
    print(f"[coord-clusters] Entities using city-center coordinates: {total_affected}")

    for city, ents in sorted(center_entities.items(), key=lambda x: -len(x[1])):
        print(f"\n  {city}: {len(ents)} entities")
        by_type = Counter(e.get("type", "?") for e in ents)
        for t, c in by_type.most_common(5):
            print(f"    {t}: {c}")

    if apply:
        report_path = ROOT / "scratch" / "coord-clusters-report.txt"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"Coordinate Cluster Report — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            f.write(f"{'='*60}\n\n")
            f.write(f"Total entities with city-center coords: {total_affected}\n\n")
            for city, ents in sorted(center_entities.items(), key=lambda x: -len(x[1])):
                lat, lon = CITY_CENTERS[city]
                f.write(f"\n{city} [{lat}, {lon}] — {len(ents)} entities\n")
                f.write("-" * 60 + "\n")
                for e in sorted(ents, key=lambda x: x.get("type", "")):
                    name = e.get("name", "")[:40]
                    f.write(f"  {e['id']:50s} {e.get('type',''):15s} {name}\n")
        print(f"\n  EXPORTED: {report_path}")

    return total_affected


# ──────────────────────────────────────────────
# Module 5: Summary quality
# ──────────────────────────────────────────────

def audit_summaries(db, apply=False):
    entities = [e for e in db.all_entities() if e.get("type") != "place"]
    issues = {"short": [], "truncated": [], "long": []}

    for e in entities:
        summary = (e.get("summary") or "").strip()
        if not summary:
            continue
        if len(summary) < 50:
            issues["short"].append(e)
        elif summary.endswith("...") or summary.endswith("…"):
            issues["truncated"].append(e)
        elif len(summary) > 500:
            issues["long"].append(e)

    print(f"\n{'='*50}")
    print(f"[summaries] {len(entities)} content entities")
    print(f"  Short (<50 chars): {len(issues['short'])}")
    print(f"  Truncated (ends ...): {len(issues['truncated'])}")
    print(f"  Long (>500 chars): {len(issues['long'])}")

    if issues["short"]:
        print("\n  Short summaries:")
        for e in issues["short"][:5]:
            s = (e.get("summary") or "")[:60]
            print(f"    {e['id']:45s} ({len(e.get('summary',''))} chars) {s}")

    if issues["truncated"]:
        print("\n  Truncated summaries:")
        for e in issues["truncated"][:5]:
            s = (e.get("summary") or "")[-60:]
            print(f"    {e['id']:45s} ...{s}")

    return sum(len(v) for v in issues.values())


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def fix_truncated_summaries(db, apply=False):
    entities = [e for e in db.all_entities() if e.get("type") != "place"]
    truncated = []
    for e in entities:
        s = (e.get("summary") or "").strip()
        if s.endswith("...") or s.endswith("…"):
            truncated.append(e)

    print(f"\n{'='*50}")
    print(f"[truncated-summaries] Found: {len(truncated)}")

    if not truncated:
        print("  OK — no truncated summaries")
        return 0

    if apply:
        fixed = 0
        for e in truncated:
            s = (e.get("summary") or "").strip()
            s = s.rstrip(".…").rstrip(".")
            while s.endswith("..."):
                s = s[:-3]
            s = s.rstrip()
            if s and s[-1] not in ".!?。":
                last_period = max(s.rfind(". "), s.rfind("! "), s.rfind("? "))
                if last_period > len(s) * 0.6:
                    s = s[:last_period + 1]
                else:
                    s = s + "."
            e["summary"] = s
            db.upsert_entity(e)
            fixed += 1
        print(f"  APPLIED: cleaned {fixed} summaries")
    else:
        print("  DRY-RUN samples:")
        for e in truncated[:5]:
            s = (e.get("summary") or "")
            print(f"    {e['id']:40s} ...{s[-50:]}")

    return len(truncated)


def fix_place_ids(db, apply=False):
    import math

    entities = db.all_entities()
    places = [e for e in entities if e.get("type") == "place" and e.get("coordinates")]
    no_place = [e for e in entities if e.get("type") != "place" and not e.get("placeId")]

    def dist_km(c1, c2):
        return math.sqrt((c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2) * 111

    MAX_DIST = 5.0
    assignable = []
    for e in no_place:
        c = e.get("coordinates")
        if not c or not isinstance(c, (list, tuple)) or len(c) != 2:
            continue
        if _is_city_center(c):
            continue
        best = min(places, key=lambda p: dist_km(c, p["coordinates"]))
        d = dist_km(c, best["coordinates"])
        if d <= MAX_DIST:
            assignable.append((e, best, d))

    print(f"\n{'='*50}")
    print(f"[place-ids] Entities without placeId: {len(no_place)}")
    print(f"  Auto-assignable (< {MAX_DIST}km): {len(assignable)}")

    if not assignable:
        print("  OK — nothing to assign")
        return 0

    if apply:
        fixed = 0
        for e, place, d in assignable:
            e["placeId"] = place["id"]
            if not e.get("area") and place.get("area"):
                e["area"] = place["area"]
            db.upsert_entity(e)
            fixed += 1
        print(f"  APPLIED: assigned {fixed} placeIds")
    else:
        print("\n  DRY-RUN samples:")
        for e, place, d in assignable[:10]:
            print(f"    {e['id']:40s} -> {place['id']:25s} ({d:.1f}km)")
        if len(assignable) > 10:
            print(f"    ... and {len(assignable)-10} more")

    return len(assignable)


MODULES = {
    "near": fix_near_symmetry,
    "timestamps": fix_timestamps,
    "phones": fix_phones,
    "clusters": audit_coord_clusters,
    "summaries": audit_summaries,
    "truncated": fix_truncated_summaries,
    "placeids": fix_place_ids,
}


def main():
    ap = argparse.ArgumentParser(description="Tối ưu chất lượng dữ liệu")
    ap.add_argument("--apply", action="store_true",
                    help="Thực sự sửa data (mặc định: dry-run)")
    ap.add_argument("--module", choices=list(MODULES.keys()),
                    help="Chỉ chạy 1 module")
    args = ap.parse_args()

    if args.apply:
        print("[WARNING] APPLY mode — data sẽ được sửa!")
        print("[WARNING] Đảm bảo đã chạy: python scripts/backup_data.py")
        print()

    from database import db

    modules = {args.module: MODULES[args.module]} if args.module else MODULES
    results = {}

    for name, func in modules.items():
        count = func(db, apply=args.apply)
        results[name] = count

    print(f"\n{'='*50}")
    print(f"TỔNG KẾT {'(APPLIED)' if args.apply else '(DRY-RUN)'}")
    print(f"{'='*50}")
    for name, count in results.items():
        status = "fixed" if args.apply and count > 0 else "issues"
        print(f"  {name:20s}  {count:6d} {status}")


if __name__ == "__main__":
    main()
