"""Trích phone CHÔN trong text → attributes.phone — chỉ khi có NHÃN liên-hệ rõ ràng
(Điện thoại/ĐT/SĐT/Hotline/Tel/liên hệ) đứng ngay trước số → là contact THẬT của entity,
không bịa, không bắt số ngẫu nhiên. Bỏ qua entity đã có phone.
DRY-RUN mặc định; --apply để ghi. §B1 backup trước.
"""
import json, re, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
DATA=ROOT/"web/data.json"
APPLY="--apply" in sys.argv
d=json.load(open(DATA,encoding="utf-8"))
# phone có nhãn liên-hệ ngay trước (trong ~12 ký tự)
LABELED=re.compile(r"(?:điện thoại|đt|sđt|hotline|tel|liên hệ|phone)\s*[:.]?\s*((?:0|\+?84)(?:\d[\s.\-]?){8,10}\d)", re.I)
def norm_phone(s): return re.sub(r"[\s.\-]","",s)
found=[]
for e in d["entities"]:
    a=e.get("attributes")
    if not isinstance(a,dict): continue
    if a.get("phone"): continue
    blob=" ".join(str(a.get(k,"")) for k in ("booking_note","note","contact","lien_he"))+" "+str(e.get("summary",""))
    m=LABELED.search(blob)
    if m:
        ph=norm_phone(m.group(1))
        if 9<=len(ph)<=11:
            found.append((e["id"], ph, e.get("type")))
            if APPLY: a["phone"]=ph; e["attributes"]=a
print(f"=== EXTRACT labeled phone — {'APPLY' if APPLY else 'DRY-RUN'} ===")
print(f"  trích được (có nhãn liên-hệ): {len(found)}")
for x in found: print("   ✓",x)
if APPLY:
    json.dump(d,open(DATA,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
    print(f"  ✅ ĐÃ GHI {DATA}")
else:
    print("  (DRY-RUN — chưa ghi)")
