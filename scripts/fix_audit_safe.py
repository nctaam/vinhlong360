"""Gói tự-sửa-an-toàn từ audit (suy nội bộ, KHÔNG bịa). Mặc định DRY-RUN.
  1. con-phung → con-phung-con-ong-dao-dua trong itinerary stops
  2. p-vung-liem.parentId huyện-cũ → 'vinh-long'
  3. attributes.district (tên huyện cũ) → đổi key legacy_district (FE không render)
  4. address: bỏ token "Huyện X / Thị xã Y / Thị trấn Z / TX / TT" (giữ xã + tỉnh)
  5. sinh located_in: entity→ward (từ placeId) + ward→tỉnh (backbone graph)
Usage: python scripts/fix_audit_safe.py [--apply]
"""
import json, re, sys, collections
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT/"web/data.json"
APPLY = "--apply" in sys.argv
with open(DATA, encoding="utf-8") as f:
    d = json.load(f)
ents = d["entities"]; rels = d["relationships"]; itin = d["itineraries"]
byid = {e["id"]: e for e in ents}
wards = {e["id"] for e in ents if e.get("type")=="place" and e.get("level") in ("xa","phuong")}
stats = collections.Counter()

# 1. con-phung trong itinerary stops
GOOD = "con-phung-con-ong-dao-dua"
for it in itin:
    for key in ("stops","days"):
        for s in (it.get(key) or []):
            if isinstance(s, dict) and s.get("id") == "con-phung":
                s["id"] = GOOD; stats["1_con_phung_stop"] += 1
            # days có thể chứa stops lồng
            for s2 in (s.get("stops") or []) if isinstance(s, dict) else []:
                if isinstance(s2, dict) and s2.get("id") == "con-phung":
                    s2["id"] = GOOD; stats["1_con_phung_stop"] += 1

# 2. parentId p-vung-liem
pvl = byid.get("p-vung-liem")
if pvl and pvl.get("parentId") and pvl["parentId"] not in byid:
    pvl["parentId"] = "vinh-long"; stats["2_parentId_fixed"] += 1

# 3 + 4. district rename + address strip (per entity)
# CHỈ bỏ ", huyện X" (cấp huyện đã bãi bỏ), CHỪA "Huyện Lộ" (tên đường); GIỮ thị trấn/TX
# (đó là tên ward mới, xoá = mất địa danh); yêu cầu có dấu phẩy trước (đứng sau xã/locality).
DIST_SEG = re.compile(r"\s*,\s*huyện\s+(?!lộ\b|lô\b|lo\b)[^,]*", re.IGNORECASE)
TRIGGER = re.compile(r",\s*huyện\s+(?!lộ\b|lô\b|lo\b)", re.IGNORECASE)
def clean_addr(a):
    a2 = DIST_SEG.sub("", a)
    a2 = re.sub(r"\s*,\s*,+", ", ", a2)
    a2 = re.sub(r"\s{2,}", " ", a2)
    a2 = re.sub(r"\s+,", ",", a2).strip().strip(",").strip()
    return a2
addr_samples = []
for e in ents:
    a = e.get("attributes")
    if isinstance(a, str):
        try: a = json.loads(a)
        except Exception: a = {}
    if not isinstance(a, dict): continue
    changed = False
    # 3. district -> legacy_district
    if "district" in a:
        a["legacy_district"] = a.pop("district"); stats["3_district_renamed"] += 1; changed = True
    # 4. address strip
    for k in ("address","diaChi","dia_chi"):
        v = a.get(k)
        if isinstance(v, str) and TRIGGER.search(v):
            nv = clean_addr(v)
            if nv != v:
                if len(addr_samples) < 12: addr_samples.append((e["id"], v[:60], nv[:60]))
                a[k] = nv; stats["4_address_stripped"] += 1; changed = True
    if changed:
        e["attributes"] = a

# 5. located_in backbone (additive, dedup)
existing = {(r.get("from"), r.get("to"), r.get("type")) for r in rels}
new_rels = []
for e in ents:
    pid = e.get("placeId")
    if pid in wards and e.get("type") != "place":
        t = (e["id"], pid, "located_in")
        if t not in existing: new_rels.append({"from": e["id"], "to": pid, "type": "located_in"}); existing.add(t); stats["5a_entity_to_ward"] += 1
for w in wards:
    t = (w, "vinh-long", "located_in")
    if t not in existing and "vinh-long" in byid: new_rels.append({"from": w, "to": "vinh-long", "type": "located_in"}); existing.add(t); stats["5b_ward_to_tinh"] += 1

print(f"=== FIX AUDIT SAFE — {'APPLY' if APPLY else 'DRY-RUN'} ===")
for k,c in sorted(stats.items()): print(f"  {k}: {c}")
print(f"  located_in mới: {len(new_rels)} (rels {len(rels)} → {len(rels)+len(new_rels)})")
print("\n  Mẫu address trước→sau:")
for i,b,a in addr_samples: print(f"    {i}:\n      «{b}»\n      «{a}»")

if APPLY:
    rels.extend(new_rels)
    json.dump(d, open(DATA,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n  ✅ ĐÃ GHI {DATA}")
else:
    print("\n  (DRY-RUN — chưa ghi. Thêm --apply; nhớ B1 backup.)")
