"""Giải placeId cho entity THIẾU placeId (bị bỏ sót) qua CROSSWALK NQ1687 + parser cải tiến
bắt 'P.' viết tắt. §1.4: chỉ gán khi mọi đơn-vị address hội tụ DUY NHẤT 1 ward khớp area;
không hội tụ → để None (chưa phân loại). KHÔNG bịa.
DRY-RUN mặc định; --apply để ghi. §B1 backup.
"""
import sys, re, json, importlib.util, io, contextlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
DATA=ROOT/"web/data.json"
APPLY="--apply" in sys.argv
_argv=sys.argv; sys.argv=["x"]
spec=importlib.util.spec_from_file_location("mig", ROOT/"scripts/migrate_huyen_to_ward.py")
mig=importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()): spec.loader.exec_module(mig)
sys.argv=_argv
norm,OLD2NEW,NUMBERED,ward_idx,ward_by_name=mig.norm,mig.OLD2NEW,mig.NUMBERED,mig.ward_idx,mig.ward_by_name

d=json.load(open(DATA,encoding="utf-8")); ents=d["entities"]; byid={e["id"]:e for e in ents}
# parser cải tiến: bắt 'phường/xã/thị trấn/P.' + tên; tách số riêng
# Viết tắt p./tt./tx. phải có ranh-giới-từ phía trước (chặn 'Tp.' bị hiểu là 'p.')
COMMUNE=re.compile(r"(?:xã|phường|thị trấn|(?<![a-zà-ỹ])p\.|(?<![a-zà-ỹ])tt\.|(?<![a-zà-ỹ])tx\.)\s*([A-Za-zÀ-ỹ0-9][A-Za-zÀ-ỹ0-9\s]*?)(?:\s*[,–\-]|\s+và\b|$|\s+huyện|\s+tx\b|\s+thị xã|\s+thành phố|\s+tỉnh|\s+tp\b)", re.I)
CITY=re.compile(r"(?:thành phố|tp)\.?\s+([A-Za-zÀ-ỹ\s]+?)(?:,|$|\s+tỉnh)", re.I)
def A(e):
    a=e.get("attributes"); return a if isinstance(a,dict) else {}
def resolve(e):
    a=A(e); addr=" ".join(str(a.get(k,"")) for k in ("address","diaChi","dia_chi")).strip()
    area=e.get("area"); wids=set()
    if not addr or not area: return None
    for raw in COMMUNE.findall(addr):
        raw=raw.strip(); cn=norm(raw)
        if not cn: continue
        if re.fullmatch(r"\d+", raw):
            cm=CITY.search(addr); city=norm(cm.group(1)) if cm else ""
            nk=(city, norm("Phường "+raw))
            if nk in NUMBERED:
                w=ward_idx.get((norm(NUMBERED[nk]), area))
                if w: wids.add(w)
        else:
            names=OLD2NEW.get(cn,set()) | ({raw} if cn in ward_by_name else set())
            for nm in names:
                w=ward_idx.get((norm(re.sub(r"^(xã|phường)\s+","",nm,flags=re.I)), area))
                if w: wids.add(w)
    return next(iter(wids)) if len(wids)==1 else None

miss=[e for e in ents if e.get("type")!="place" and not e.get("placeId")]
fixed=[]; still=0
for e in miss:
    r=resolve(e)
    if r: fixed.append((e["id"], (A(e).get("address") or "")[:42], byid[r].get("name"), r))
    else: still+=1
print(f"=== RESOLVE missing placeId — {'APPLY' if APPLY else 'DRY-RUN'} ===")
print(f"  thiếu placeId: {len(miss)} | GIẢI được (crosswalk hội tụ): {len(fixed)} | còn None: {still}")
for x in fixed[:30]: print("   ✓",x)
if APPLY:
    m={x[0]:x[3] for x in fixed}
    for e in ents:
        if e["id"] in m: e["placeId"]=m[e["id"]]
    json.dump(d,open(DATA,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
    print(f"\n  ✅ ĐÃ GHI {DATA} ({len(fixed)})")
else:
    print("\n  (DRY-RUN — chưa ghi)")
