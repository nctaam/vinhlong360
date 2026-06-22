"""Gỡ near edge KHÔNG hợp lệ sau khi đổi coords — §1.4: quan hệ 'gần' sai → không công khai.
Sau re-align/null coords: near edge có thể (a) endpoint mất coords, (b) >50km (không còn 'gần').
Cả hai = near sai → gỡ (validate near_missing_location + far_near về 0).
DRY-RUN mặc định; --apply để ghi. §B1 backup trước.
"""
import json, sys, math
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
DATA=ROOT/"web/data.json"
APPLY="--apply" in sys.argv
def hav(a,b):
    if not a or not b or len(a)<2 or len(b)<2: return None
    la1,lo1,la2,lo2=map(math.radians,[a[0],a[1],b[0],b[1]])
    h=math.sin((la2-la1)/2)**2+math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2
    return 2*6371*math.asin(min(1,math.sqrt(h)))
d=json.load(open(DATA,encoding="utf-8"))
byid={e["id"]:e for e in d["entities"]}
rels=d["relationships"]
keep=[]; cut_missing=0; cut_far=0
for r in rels:
    if r.get("type")=="near":
        a=byid.get(r.get("from"),{}).get("coordinates"); b=byid.get(r.get("to"),{}).get("coordinates")
        if not a or not b: cut_missing+=1; continue
        km=hav(a,b)
        if km is not None and km>50: cut_far+=1; continue
    keep.append(r)
print(f"=== CLEAN near invalid — {'APPLY' if APPLY else 'DRY-RUN'} ===")
print(f"  gỡ near endpoint mất coords: {cut_missing}")
print(f"  gỡ near >50km: {cut_far}")
print(f"  relationships: {len(rels)} → {len(keep)}")
if APPLY:
    d["relationships"]=keep
    json.dump(d,open(DATA,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
    print(f"  ✅ ĐÃ GHI {DATA}")
else:
    print("  (DRY-RUN — chưa ghi)")
