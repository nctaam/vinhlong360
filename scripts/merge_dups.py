#!/usr/bin/env python3
"""Merge confirmed duplicate entities and fix misleading names."""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "web" / "data.json"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

data = json.load(DATA.open("r", encoding="utf-8-sig"))
entities = data["entities"]
rels = data["relationships"]

by_id = {e["id"]: e for e in entities}

# ── 1. Rename Đình Long Thanh variants (3 khác nhau, cần phân biệt) ──
renames = {
    "dinh-long-thanh-vinh-long": "Đình Long Thanh (Vĩnh Long)",
    "dinh-long-thanh-w3": "Đình Long Thanh (Bình Đại, Bến Tre)",
    "dinh-long-thanh": "Đình Long Thanh (Thạnh Đức, Vĩnh Long)",
}
for eid, new_name in renames.items():
    if eid in by_id:
        old = by_id[eid]["name"]
        by_id[eid]["name"] = new_name
        print(f"RENAME: {old} → {new_name}")

# Fix summary sai (copy từ web khác) cho dinh-long-thanh-vinh-long
if "dinh-long-thanh-vinh-long" in by_id:
    e = by_id["dinh-long-thanh-vinh-long"]
    if "Vĩnh Phúc" in (e.get("summary") or ""):
        e["summary"] = "Đình Long Thanh tọa lạc tại Vĩnh Long, là ngôi đình cổ có giá trị lịch sử văn hóa."
        print("  Fixed wrong summary (was about Vĩnh Phúc, not Vĩnh Long)")

# ── 2. Merge duplicates: keep_id absorbs remove_id ──
merges = [
    # (keep, remove, reason)
    ("khu-luu-niem-tran-dai-nghia-vinh-long", "khu-luu-niem-giao-su-vien-si-tran-dai-nghia",
     "same place, keep the one with coords"),
    ("cu-lao-may-tra-on", "cu-lao-may-tra-on-vinh-long",
     "same place, keep the one with area+placeId+more rels"),
    ("du-lich-vuon-chu-7-gat", "du-lich-vuon-chu-7-gat-vlt",
     "same place, keep the one with more rels"),
    ("nha-gom-tu-buoi-w3", "nha-gom-tu-buoi",
     "same place, keep the one with good summary"),
    ("dinh-tan-hoa-w3", "dinh-tan-hoa",
     "same place, keep the one with good summary"),
]

removed_ids = set()
for keep_id, remove_id, reason in merges:
    keep = by_id.get(keep_id)
    remove = by_id.get(remove_id)
    if not keep or not remove:
        print(f"SKIP merge: {keep_id} or {remove_id} not found")
        continue

    # Transfer missing fields from remove → keep
    if not keep.get("coordinates") and remove.get("coordinates"):
        keep["coordinates"] = remove["coordinates"]
        print(f"  Transferred coords from {remove_id}")
    if not keep.get("placeId") and remove.get("placeId"):
        keep["placeId"] = remove["placeId"]
        print(f"  Transferred placeId from {remove_id}")
    if not keep.get("area") and remove.get("area"):
        keep["area"] = remove["area"]
        print(f"  Transferred area from {remove_id}")
    if not keep.get("source") and remove.get("source"):
        keep["source"] = remove["source"]
        print(f"  Transferred source from {remove_id}")

    # Redirect relationships from remove → keep
    redirected = 0
    for r in rels:
        src_key = "from" if "from" in r else ("from_id" if "from_id" in r else "source_id")
        dst_key = "to" if "to" in r else ("to_id" if "to_id" in r else "target_id")
        if r.get(src_key) == remove_id:
            r[src_key] = keep_id
            redirected += 1
        if r.get(dst_key) == remove_id:
            r[dst_key] = keep_id
            redirected += 1

    removed_ids.add(remove_id)
    print(f"MERGE: {remove_id} → {keep_id} ({reason}, {redirected} rels redirected)")

# For khu-luu-niem: also transfer placeId and source from the removed one
keep_tdn = by_id.get("khu-luu-niem-tran-dai-nghia-vinh-long")
if keep_tdn:
    if not keep_tdn.get("placeId"):
        keep_tdn["placeId"] = "xa-tam-binh"
        print("  Set placeId=xa-tam-binh for Khu LN Trần Đại Nghĩa")

# Remove merged entities
data["entities"] = [e for e in entities if e.get("id") not in removed_ids]
print(f"\nRemoved {len(removed_ids)} duplicate entities")

# Dedup relationships that now point same src→dst→type after merge
seen = set()
deduped = []
for r in rels:
    src = r.get("from") or r.get("from_id") or r.get("source_id") or ""
    dst = r.get("to") or r.get("to_id") or r.get("target_id") or ""
    kind = r.get("type") or r.get("rel_type") or ""
    key = (str(src), str(dst), str(kind))
    # Also skip self-refs created by merge
    if str(src) == str(dst):
        continue
    if key not in seen:
        seen.add(key)
        deduped.append(r)

removed_rels = len(rels) - len(deduped)
data["relationships"] = deduped
print(f"Deduped relationships: {len(rels)} → {len(deduped)} (removed {removed_rels})")

# Save
with DATA.open("w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=None, separators=(",", ":"))
print(f"\n✅ Saved: {len(data['entities'])} entities, {len(data['relationships'])} rels")
