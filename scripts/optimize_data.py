#!/usr/bin/env python3
"""Tối ưu dữ liệu: fill area từ placeId, sửa tên HTML, dọn summary,
auto-link placeId cho entity có area, kết nối orphan non-place."""
import json, sys, re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "web" / "data.json"
APPLY = "--apply" in sys.argv  # ETL-01: mặc định DRY-RUN, --apply mới ghi (+ backup B1)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

data = json.load(DATA.open("r", encoding="utf-8-sig"))
entities = data["entities"]
rels = data["relationships"]
by_id = {e["id"]: e for e in entities}

fixes = Counter()

# ── 1. Fill area from placeId ──
print("── 1. Fill area from placeId ──")
for e in entities:
    if e.get("area") or e["type"] == "place":
        continue
    pid = e.get("placeId")
    if not pid:
        continue
    place = by_id.get(pid)
    if place and place.get("area"):
        e["area"] = place["area"]
        fixes["area_from_placeId"] += 1
        print(f"  {e['name']}: area={place['area']} (from {pid})")
print(f"  Total: {fixes['area_from_placeId']}")

# ── 2. Fix HTML entities in names ──
print("\n── 2. Fix HTML & in names ──")
for e in entities:
    n = e.get("name", "")
    if "&amp;" in n:
        e["name"] = n.replace("&amp;", "&")
        fixes["name_html_fix"] += 1
        print(f"  {e['id']}: {n} → {e['name']}")

# ── 3. Clean summary: remove Google snippet date prefixes ──
print("\n── 3. Clean summary date prefixes ──")
date_prefix_re = re.compile(
    r'^(?:'
    r'\d{1,2}\s+thg\s+\d{1,2},?\s+\d{4}\s*[·\-–—]\s*'  # "26 thg 7, 2021 · "
    r'|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2},?\s+\d{4}\s*[·\-–—]\s*'  # "April 26, 2026 - "
    r'|\d{4}[-/]\d{1,2}[-/]\d{1,2}\s*[·\-–—]\s*'  # "2024-01-15 - "
    r')',
    re.IGNORECASE
)
for e in entities:
    s = e.get("summary") or ""
    if not s:
        continue
    m = date_prefix_re.match(s)
    if m:
        cleaned = s[m.end():]
        if len(cleaned) > 20:
            # Capitalize first letter
            cleaned = cleaned[0].upper() + cleaned[1:] if cleaned else cleaned
            e["summary"] = cleaned
            fixes["summary_date_prefix"] += 1
            print(f"  {e['id']}: removed \"{s[:m.end()].strip()}\"")

# ── 4. Fix truncated summaries (ending with "...") ──
print("\n── 4. Truncated summaries ──")
truncated = []
for e in entities:
    s = e.get("summary") or ""
    if s.endswith("...") or s.endswith("…"):
        truncated.append(e)
        # Remove trailing dots — better to have a clean incomplete sentence
        e["summary"] = re.sub(r'[.…]{2,}$', '.', s)
        fixes["summary_truncated_clean"] += 1
print(f"  Cleaned trailing '...': {fixes['summary_truncated_clean']}")
if truncated:
    for e in truncated[:5]:
        print(f"    {e['id']}: ...{(e.get('summary','') or '')[-60:]}")

# ── 5. Strip null/empty fields that add no value ──
print("\n── 5. Strip null/empty fields ──")
STRIP_FIELDS = ["legacyArea", "parentId", "level"]
for e in entities:
    for f in STRIP_FIELDS:
        if f in e and (e[f] is None or e[f] == "" or e[f] == 0):
            del e[f]
            fixes[f"strip_{f}"] += 1
print(f"  legacyArea: {fixes.get('strip_legacyArea', 0)}")
print(f"  parentId: {fixes.get('strip_parentId', 0)}")
print(f"  level: {fixes.get('strip_level', 0)}")

# ── 6. Clean empty arrays/objects ──
print("\n── 6. Clean empty arrays/objects ──")
for e in entities:
    if "images" in e and (e["images"] is None or e["images"] == [] or e["images"] == ""):
        del e["images"]
        fixes["strip_empty_images"] += 1
    if "attributes" in e and (e["attributes"] is None or e["attributes"] == {} or e["attributes"] == "" or e["attributes"] == []):
        del e["attributes"]
        fixes["strip_empty_attributes"] += 1
    if "season" in e and (e["season"] is None or e["season"] == "" or e["season"] == []):
        del e["season"]
        fixes["strip_empty_season"] += 1
    if "source" in e and (e["source"] is None or e["source"] == ""):
        del e["source"]
        fixes["strip_empty_source"] += 1
    if "coords" in e:
        del e["coords"]  # legacy field, coordinates is canonical
        fixes["strip_coords_legacy"] += 1
    if "confidence" in e and (e["confidence"] is None or e["confidence"] == "" or e["confidence"] == 0):
        del e["confidence"]
        fixes["strip_empty_confidence"] += 1
    if "created_at" in e and (e["created_at"] is None or e["created_at"] == ""):
        del e["created_at"]
        fixes["strip_empty_created_at"] += 1
    if "updatedAt" in e and (e["updatedAt"] is None or e["updatedAt"] == ""):
        del e["updatedAt"]
        fixes["strip_empty_updatedAt"] += 1
print(f"  images: {fixes.get('strip_empty_images', 0)}")
print(f"  attributes: {fixes.get('strip_empty_attributes', 0)}")
print(f"  season: {fixes.get('strip_empty_season', 0)}")
print(f"  source: {fixes.get('strip_empty_source', 0)}")
print(f"  coords (legacy): {fixes.get('strip_coords_legacy', 0)}")
print(f"  confidence: {fixes.get('strip_empty_confidence', 0)}")

# ── 7. Auto-link orphan non-place entities via produced_in/area ──
print("\n── 7. Auto-link orphans via area→place ──")
rel_ids = set()
for r in rels:
    rel_ids.add(r.get("from") or r.get("from_id") or "")
    rel_ids.add(r.get("to") or r.get("to_id") or "")

# Build area→place mapping
area_places = defaultdict(list)
for e in entities:
    if e["type"] == "place" and e.get("area"):
        area_places[e["area"]].append(e)

# ĐÃ VÔ HIỆU (ETL-02, §1.4): trước đây tự gán produced_in cho orphan về placeId hoặc
# "place đầu tiên theo area" — quan hệ BỊA không bằng chứng (món/sản phẩm KHÔNG thật sự
# 'produced_in' phường đầu danh sách). Orphan nên giải bằng crosswalk có bằng chứng
# (migrate_huyen_to_ward / fix_placeid_crosswalk), KHÔNG tự sinh produced_in.
orphans = [e for e in entities if e["id"] not in rel_ids and e["type"] != "place"]
print(f"  Orphan non-place: {len(orphans)} (KHÔNG tự gán produced_in — §1.4)")
fixes["orphan_linked"] = 0

# ── 8. Enrich short summaries ──
print("\n── 8. Very short summaries (<30 chars) ──")
short = [e for e in entities if e.get("summary") and len(e["summary"]) < 30]
print(f"  Count: {len(short)}")
for e in short:
    print(f"    [{e['type']}] {e['name']}: \"{e['summary']}\"")

# ── Summary ──
print(f"\n{'='*60}")
print("OPTIMIZATION SUMMARY:")
total_fixes = sum(fixes.values())
for k, v in fixes.most_common():
    print(f"  {k}: {v}")
print(f"  TOTAL CHANGES: {total_fixes}")

# Save — ETL-01: chỉ ghi khi --apply, BẮT BUỘC backup B1 trước (§B1)
if APPLY:
    import subprocess
    subprocess.run([sys.executable, str(ROOT / "scripts" / "backup_data.py")], check=False)
    with DATA.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Saved: {len(entities)} entities, {len(data['relationships'])} rels")
else:
    print(f"\n(DRY-RUN — chưa ghi. Thêm --apply để ghi, sẽ tự backup trước.)")

# File size
size_kb = DATA.stat().st_size / 1024
print(f"  File size: {size_kb:.0f} KB")
