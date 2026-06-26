"""Tối ưu dữ liệu an-toàn từ audit (READ→ghi khi --apply). KHÔNG bịa.
  B. dish→craft_village produced_in → associated_with (sửa loại quan hệ, dedup)
  C. entity dồn ở centroid-VÙNG + placeId→ward → nâng coords = centroid-XÃ (chính xác hơn)
Usage: python scripts/optimize_audit_relgeo.py [--apply]   (B1 backup trước khi --apply)
"""
import json, sys, math, collections
from pathlib import Path

def haversine_km(a, b):
    if not a or not b or len(a) < 2 or len(b) < 2: return None
    la1, lo1, la2, lo2 = map(math.radians, [a[0], a[1], b[0], b[1]])
    h = math.sin((la2-la1)/2)**2 + math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2
    return 2 * 6371 * math.asin(min(1, math.sqrt(h)))
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT/"web/data.json"
APPLY = "--apply" in sys.argv
with open(DATA, encoding="utf-8") as f:
    d = json.load(f)
ents = d["entities"]; rels = d["relationships"]
byid = {e["id"]: e for e in ents}
wards = {e["id"]: e for e in ents if e.get("type")=="place" and e.get("level") in ("xa","phuong")}
stats = collections.Counter()

# B. re-type dish→craft produced_in → associated_with (dedup vs assoc đã có)
assoc_exist = {(r.get("from"), r.get("to")) for r in rels if r.get("type")=="associated_with"}
new_rels = []; removed = 0
for r in rels:
    if r.get("type")=="produced_in" and byid.get(r.get("from"),{}).get("type")=="dish" and byid.get(r.get("to"),{}).get("type")=="craft_village":
        key=(r.get("from"), r.get("to"))
        if key in assoc_exist:
            removed += 1; stats["B_dropped_dup"] += 1; continue
        r["type"]="associated_with"; assoc_exist.add(key); stats["B_retyped"] += 1
    new_rels.append(r)
d["relationships"] = new_rels

# C. coords placeholder → centroid-xã (deterministic 1-pass, hội tụ):
# entity ngồi trên 1 centroid (xã bất kỳ HOẶC điểm bị dồn ≥20) mà KHÔNG phải xã của
# mình (placeId) → đưa về centroid xã đúng. Sau move coord==centroid-xã-của-mình → skip.
ward_centroids = {tuple(w["coordinates"]) for w in wards.values() if w.get("coordinates")}
coord_count = collections.Counter(tuple(e["coordinates"]) for e in ents if e.get("coordinates"))
placeholder = ward_centroids | {c for c,n in coord_count.items() if n >= 20}
upg_samples=[]
for e in ents:
    c = e.get("coordinates")
    if not c: continue
    w = wards.get(e.get("placeId"))
    if not (w and w.get("coordinates")): continue
    wc = tuple(w["coordinates"])
    if tuple(c) != wc and tuple(c) in placeholder:
        if len(upg_samples) < 8: upg_samples.append((e["id"], tuple(c), wc, w.get("name")))
        if APPLY: e["coordinates"] = list(wc)
        stats["C_coords_to_ward_centroid"] += 1

# D. gỡ cạnh near >50km (rác lộ ra sau khi nâng coords; vi phạm near≤50km)
cur = d["relationships"]; kept = []
for r in cur:
    if r.get("type") == "near":
        a = byid.get(r.get("from"), {}).get("coordinates"); b = byid.get(r.get("to"), {}).get("coordinates")
        km = haversine_km(a, b)
        if km is not None and km > 50:
            stats["D_far_near_removed"] += 1; continue
    kept.append(r)
d["relationships"] = kept

print(f"=== OPTIMIZE — {'APPLY' if APPLY else 'DRY-RUN'} ===")
for k,c in sorted(stats.items()): print(f"  {k}: {c}")
print(f"  rels {len(rels)} → {len(d['relationships'])} (bỏ {removed} produced_in trùng assoc)")
print("\n  Mẫu nâng coords (vùng→xã):")
for i,old,new,nm in upg_samples: print(f"    {i}: {old} → {new} ({nm})")
if APPLY:
    json.dump(d, open(DATA,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n  ✅ ĐÃ GHI {DATA}")
else:
    print("\n  (DRY-RUN — chưa ghi.)")
