"""Gỡ produced_in Cartesian rác — §1.4: quan hệ KHÔNG có bằng chứng = không công khai.
Bằng chứng audit: product 'produced_in' fanout cao (6/10/13/22 — đúng số craft_village
trong vùng) = auto-sinh tích Descartes (vd 'Muối Ba Tri' produced_in 22 làng gồm cả làng
hoa/làng ghe/làng kẹo dừa = SAI). Product thật produced_in 1-5 nơi (fanout<=5, đều đúng:
'Tàu hủ ky Mỹ Hòa'→'Làng tàu hủ ky Mỹ Hòa').
LUẬT: gỡ produced_in nếu fanout-NGUỒN >= THRESH (mặc định 6). Giữ fanout<=5 (chủ ý/thật).
KHÔNG rescue khớp-tên (đã đo: nhiễu, khớp nhầm địa-danh → vi phạm §1.4).
DRY-RUN mặc định; --apply để ghi. §B1 backup trước.
"""
import json, sys, collections
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
DATA=ROOT/"web/data.json"
APPLY="--apply" in sys.argv
THRESH=6
with open(DATA,encoding="utf-8") as f:
    d=json.load(f)
byid={e["id"]:e for e in d["entities"]}
rels=d["relationships"]
pin=[r for r in rels if r.get("type")=="produced_in"]
src_fan=collections.Counter(r["from"] for r in pin)

keep=[]; cut=[]
for r in rels:
    if r.get("type")=="produced_in" and src_fan[r["from"]]>=THRESH:
        cut.append(r)
    else:
        keep.append(r)
# thống kê
cut_src=collections.Counter(byid.get(r["from"],{}).get("name") for r in cut)
print(f"=== CUT produced_in Cartesian — {'APPLY' if APPLY else 'DRY-RUN'} (thresh fanout>={THRESH}) ===")
print(f"  produced_in: {len(pin)} → giữ {len(pin)-len(cut)} (fanout<=5) | gỡ {len(cut)}")
print(f"  relationships: {len(rels)} → {len(keep)}")
print(f"  product bị gỡ hết produced_in (fanout cao): {len(cut_src)}")
print("  mẫu product gỡ:", [n for n,_ in cut_src.most_common(8)])
# kiểm: product nào còn produced_in sau gỡ
after=collections.Counter(r["from"] for r in keep if r.get("type")=="produced_in")
print(f"  product CÒN produced_in (link thật giữ lại): {len(after)}")
if APPLY:
    d["relationships"]=keep
    json.dump(d,open(DATA,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
    print(f"\n  ✅ ĐÃ GHI {DATA}")
else:
    print("\n  (DRY-RUN — chưa ghi)")
