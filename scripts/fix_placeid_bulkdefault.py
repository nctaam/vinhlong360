"""Sửa bug bulk-default placeId (entity bị gán nhầm vào phường mặc-định).
AN-TOÀN §1.4: chỉ sửa khi BẰNG CHỨNG 3 LỚP đồng thuận —
  (1) attributes.address ghi 'xã/phường/thị trấn <W>'
  (2) norm(W) = ĐÚNG 1 xã/phường hiện tại CÙNG vùng (area) với entity, ≠ placeId hiện tại
  (3) CORROBORATION: token-slug của W nằm trong entity.id HOẶC trong entity.name
Thiếu bất kỳ lớp nào → KHÔNG sửa, ghi vào danh sách flag (chờ NQ1687/soát tay).
DRY-RUN mặc định; --apply để ghi. §B1 backup trước.
"""
import json, re, sys, unicodedata, collections
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT/"web/data.json"
APPLY = "--apply" in sys.argv
with open(DATA, encoding="utf-8") as f:
    d = json.load(f)
ents = d["entities"]; byid = {e["id"]: e for e in ents}

def A(e):
    a=e.get("attributes")
    if isinstance(a,str):
        try:a=json.loads(a)
        except (ValueError, json.JSONDecodeError): a = {}
    return a if isinstance(a,dict) else {}
def norm(s):
    s=unicodedata.normalize("NFC",(s or "")).strip().lower()
    return re.sub(r"^(xã|phường|thị trấn|tt\.?|p\.?)\s+","",s).strip()
def slug(s):  # bỏ dấu → ascii token để so với id
    s=unicodedata.normalize("NFD",(s or "")).encode("ascii","ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+","-",s).strip("-")

wards=[e for e in ents if e.get("type")=="place" and e.get("level") in ("xa","phuong")]
# index: (area, norm_name) -> [ward]; chỉ nhận khi DUY NHẤT
ward_idx=collections.defaultdict(list)
for w in wards: ward_idx[(w.get("area"), norm(w.get("name")))].append(w)
CM=re.compile(r"(?:xã|phường|thị trấn)\s+([^,]+)",re.I)

fixed=[]; flagged=[]
for e in ents:
    if e.get("type")=="place": continue
    a=A(e); addr=a.get("address") or ""; pid=e.get("placeId"); earea=e.get("area")
    if not addr or not earea: continue
    m=CM.search(addr)
    if not m: continue
    aw=norm(m.group(1))
    if not aw: continue
    cands=ward_idx.get((earea, aw), [])
    cur_pn=norm(byid.get(pid,{}).get("name")) if pid in byid else None
    if aw==cur_pn: continue                       # đã đúng
    if len(cands)!=1:
        if aw and cur_pn and aw!=cur_pn: flagged.append((e["id"], m.group(1).strip(), byid.get(pid,{}).get("name"), f"cands={len(cands)}"))
        continue
    target=cands[0]
    tok=slug(aw)
    corrob = tok and (tok in slug(e["id"]) or tok in slug(e.get("name","")))
    rec=(e["id"], m.group(1).strip(), byid.get(pid,{}).get("name"), target["id"])
    if corrob:
        if APPLY: e["placeId"]=target["id"]
        fixed.append(rec)
    else:
        flagged.append(rec+("no-corrob",))

print(f"=== FIX placeId bulk-default — {'APPLY' if APPLY else 'DRY-RUN'} ===")
print(f"  SỬA (3-lớp khớp): {len(fixed)}")
for x in fixed: print("   ✓", x)
print(f"\n  FLAG (thiếu corrob / mơ hồ → chờ soát): {len(flagged)}")
for x in flagged[:25]: print("   ?", x)
# thống kê placeId nguồn bị sửa nhiều nhất (xác nhận bulk-default)
src=collections.Counter(x[2] for x in fixed)
print("\n  placeId-SAI hay gặp (bằng chứng bulk-default):", src.most_common(8))
if APPLY:
    json.dump(d, open(DATA,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n  ✅ ĐÃ GHI {DATA}")
else:
    print("\n  (DRY-RUN — chưa ghi)")
