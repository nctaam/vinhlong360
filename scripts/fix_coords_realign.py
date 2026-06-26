"""Re-align toạ độ placeholder + gắn cờ gần-đúng — §1.4: không trình bày ước-lượng như thật.
'Placeholder coord' = toạ độ TRÙNG KHÍT centroid của MỘT xã/phường (không phải vị trí scrape thật).
  - placeId là ward hợp lệ  → coords = centroid-ward-CỦA-placeId (sửa pin sai ward) + cờ coords_approximate=true
  - placeId None/non-ward    → coords = None (gỡ pin giả-chính-xác; chưa phân loại thì không cắm pin)
Toạ độ KHÔNG trùng centroid nào (vị trí thật) → GIỮ NGUYÊN, không gắn cờ.
DRY-RUN mặc định; --apply để ghi. §B1 backup trước.
"""
import json, sys, collections
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT/"web/data.json"
APPLY = "--apply" in sys.argv
with open(DATA, encoding="utf-8") as f:
    d = json.load(f)
ents = d["entities"]; byid = {e["id"]: e for e in ents}
wards = {e["id"]: e for e in ents if e.get("type")=="place" and e.get("level") in ("xa","phuong")}
ward_centroid = {wid: tuple(w["coordinates"]) for wid,w in wards.items() if w.get("coordinates")}
# placeholder = centroid ward HOẶC toạ độ bị ≥10 entity dùng chung (chắc chắn không phải vị trí thật)
_cc = collections.Counter(tuple(e["coordinates"]) for e in ents
                          if e.get("type")!="place" and e.get("coordinates"))
centroid_set = set(ward_centroid.values()) | {c for c,n in _cc.items() if n >= 10}

def A(e):
    a=e.get("attributes")
    if isinstance(a,str):
        try:a=json.loads(a)
        except:a={}
    return a if isinstance(a,dict) else {}

realign=[]; nulled=[]; flagged_only=0
for e in ents:
    if e.get("type")=="place": continue
    c=e.get("coordinates")
    if not c or tuple(c) not in centroid_set: continue   # vị trí thật (không trùng centroid) → bỏ qua
    pid=e.get("placeId")
    if pid in ward_centroid:
        want=ward_centroid[pid]
        a=A(e)
        if tuple(c)!=want:
            if APPLY: e["coordinates"]=list(want)
            realign.append((e["id"], byid.get(pid,{}).get("name")))
        else:
            flagged_only+=1
        if APPLY:
            a["coords_approximate"]=True; e["attributes"]=a
    else:  # placeId None / non-ward → gỡ pin giả
        if APPLY:
            e["coordinates"]=None
            a=A(e); a.pop("coords_approximate",None); e["attributes"]=a
        nulled.append((e["id"], pid))

print(f"=== RE-ALIGN COORDS — {'APPLY' if APPLY else 'DRY-RUN'} ===")
print(f"  re-align về centroid-placeId (sửa pin sai ward): {len(realign)}")
print(f"  gắn cờ approximate (đã đúng centroid): {flagged_only}")
print(f"  null coords (placeId None/non-ward, gỡ pin giả): {len(nulled)}")
print(f"  → tổng gắn cờ coords_approximate: {len(realign)+flagged_only}")
print("\n  mẫu re-align:");  [print("   ↻",x) for x in realign[:10]]
print("  mẫu null:");       [print("   ∅",x) for x in nulled[:10]]
if APPLY:
    json.dump(d, open(DATA,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n  ✅ ĐÃ GHI {DATA}")
else:
    print("\n  (DRY-RUN — chưa ghi)")
