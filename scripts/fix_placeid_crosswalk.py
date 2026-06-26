"""Giải placeId còn nợ bằng CROSSWALK NQ1687 (nguồn) — §1.4: chính xác, không bịa, nghi→None.
Tái dùng CROSSWALK/OLD2NEW/NUMBERED/parser từ migrate_huyen_to_ward (import an toàn: xoá --apply
khỏi argv để module KHÔNG tự ghi).
  Round A — placeId trỏ NON-WARD (place nhưng không phải xã/phường): address+crosswalk hội tụ 1
            ward → SỬA; không → None (chưa phân loại, KHÔNG đoán).
  Round B — placeId là ward HỢP LỆ nhưng address+crosswalk hội tụ ward KHÁC → SỬA (NQ1687 ưu tiên).
DRY-RUN mặc định; --apply để ghi. §B1 backup trước.
"""
import sys, re, json, importlib.util
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT/"web/data.json"
APPLY = "--apply" in sys.argv

# import migrate module KHÔNG cho nó tự apply
_argv = sys.argv; sys.argv = ["x"]
spec = importlib.util.spec_from_file_location("mig", ROOT/"scripts/migrate_huyen_to_ward.py")
mig = importlib.util.module_from_spec(spec)
import io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    spec.loader.exec_module(mig)
sys.argv = _argv
norm, OLD2NEW, NUMBERED, ward_idx, ward_by_name = mig.norm, mig.OLD2NEW, mig.NUMBERED, mig.ward_idx, mig.ward_by_name
COMMUNE, CITY, attrs = mig.COMMUNE, mig.CITY, mig.attrs

with open(DATA, encoding="utf-8") as f:
    d = json.load(f)
ents = d["entities"]; byid = {e["id"]: e for e in ents}
ward_ids = {w["id"] for w in mig.wards}
place_ids = mig.place_ids

def resolve(e):
    a = attrs(e); addr = " ".join(str(a.get(k,"")) for k in ("address","diaChi","dia_chi")).strip()
    area = e.get("area"); wids=set()
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

A_fix=[]; A_none=[]; B_fix=[]
for e in ents:
    if e.get("type")=="place": continue
    pid=e.get("placeId")
    if not pid: continue                      # thiếu hẳn → việc của migrate, bỏ qua
    if pid in ward_ids:                        # Round B: ward hợp lệ
        r=resolve(e)
        if r and r!=pid:
            B_fix.append((e["id"], byid[pid].get("name"), byid[r].get("name"), r))
    elif pid in place_ids:                     # Round A: trỏ non-ward
        r=resolve(e)
        if r: A_fix.append((e["id"], byid[pid].get("name"), byid[r].get("name"), r))
        else: A_none.append((e["id"], byid[pid].get("name")))

print(f"=== FIX placeId crosswalk — {'APPLY' if APPLY else 'DRY-RUN'} ===")
print(f"\n[A] placeId trỏ non-ward: SỬA(crosswalk)={len(A_fix)} | →None(chưa phân loại)={len(A_none)}")
for x in A_fix: print("   ✓A", x)
for x in A_none: print("   ∅A", x)
print(f"\n[B] ward hợp lệ NHƯNG address+crosswalk → ward KHÁC: {len(B_fix)}")
for x in B_fix: print("   ✓B", x)

if APPLY:
    n=0
    for e in ents:
        if e.get("type")=="place": continue
        eid=e["id"]
        m={x[0]:x[3] for x in A_fix}|{x[0]:x[3] for x in B_fix}
        if eid in m: e["placeId"]=m[eid]; n+=1
        elif eid in {x[0] for x in A_none}: e["placeId"]=None; n+=1
    json.dump(d, open(DATA,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n  ✅ ĐÃ GHI {DATA} (A_fix {len(A_fix)} + A_none {len(A_none)} + B_fix {len(B_fix)} = {n})")
else:
    print("\n  (DRY-RUN — chưa ghi)")
