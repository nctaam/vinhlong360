"""Sửa placeId cho entity ở PHƯỜNG-SỐ của 3 TP cũ → phường mới (NQ1687).
Crosswalk lấy NGUYÊN VĂN từ NQ 1687/NQ-UBTVQH15, cross-check 2 lần độc lập KHỚP 100%
(mỗi phường-số đi TRỌN 'Sắp xếp toàn bộ diện tích...' vào 1 phường mới → map sạch).
AN-TOÀN §1.4: chỉ map khi address GHI RÕ 'thành phố/TP <tỉnh>' khớp area entity
(chặn nhầm TX Duyên Hải/TX Bình Minh cũng có phường-số). Phường-số KHÔNG có trong
NQ1687 (P2 VL; P1-5 BT; P2,P6 TV) → KHÔNG đụng. DRY-RUN mặc định; --apply để ghi.
"""
import json, re, sys, unicodedata, collections
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT/"web/data.json"
APPLY = "--apply" in sys.argv
with open(DATA, encoding="utf-8") as f:
    d = json.load(f)
ents = d["entities"]; byid = {e["id"]: e for e in ents}

XW = {  # (area, phường-số) -> ward_id  [verbatim NQ1687, verified 2x]
 ("vinh-long","1"):"p-long-chau", ("vinh-long","9"):"p-long-chau",
 ("vinh-long","3"):"p-phuoc-hau", ("vinh-long","4"):"p-phuoc-hau",
 ("vinh-long","5"):"p-thanh-duc", ("vinh-long","8"):"p-tan-hanh",
 ("ben-tre","8"):"p-phu-khuong", ("ben-tre","7"):"p-ben-tre", ("ben-tre","6"):"p-son-dong",
 ("tra-vinh","1"):"p-tra-vinh", ("tra-vinh","3"):"p-tra-vinh", ("tra-vinh","9"):"p-tra-vinh",
 ("tra-vinh","4"):"p-long-duc", ("tra-vinh","7"):"p-nguyet-hoa", ("tra-vinh","8"):"p-nguyet-hoa",
 ("tra-vinh","5"):"p-hoa-thuan",
}
CITY = {  # area -> regex 'thành phố/TP <tỉnh>' (NFC, đã lower)
 "vinh-long": re.compile(r"(?:thành phố|tp\.?)\s*vĩnh\s*long"),
 "ben-tre":   re.compile(r"(?:thành phố|tp\.?)\s*bến\s*tre"),
 "tra-vinh":  re.compile(r"(?:thành phố|tp\.?)\s*trà\s*vinh"),
}
NUMW = re.compile(r"(?:phường|p\.?)\s*0*(\d{1,2})\b", re.I)

def A(e):
    a=e.get("attributes")
    if isinstance(a,str):
        try:a=json.loads(a)
        except (ValueError, json.JSONDecodeError): a = {}
    return a if isinstance(a,dict) else {}

fixed=[]; skip_nocity=[]; skip_nomap=[]
for e in ents:
    if e.get("type")=="place": continue
    a=A(e); addr=a.get("address") or ""; area=e.get("area"); pid=e.get("placeId")
    if not addr or area not in CITY: continue
    m=NUMW.search(addr)
    if not m: continue
    num=m.group(1)
    low=unicodedata.normalize("NFC",addr).lower()
    key=(area,num)
    if key not in XW:
        skip_nomap.append((e["id"], f"P{num}", area)); continue
    if not CITY[area].search(low):
        skip_nocity.append((e["id"], f"P{num}", byid.get(pid,{}).get("name"))); continue
    tgt=XW[key]
    if pid==tgt: continue
    if APPLY: e["placeId"]=tgt
    fixed.append((e["id"], f"P{num}", byid.get(pid,{}).get("name"), tgt))

print(f"=== FIX numbered wards — {'APPLY' if APPLY else 'DRY-RUN'} ===")
print(f"  SỬA: {len(fixed)}")
for x in fixed: print("   ✓", x)
print(f"\n  BỎ — phường-số không có trong NQ1687 (P2 VL/P1-5 BT/P2,6 TV): {len(skip_nomap)}")
print(f"  BỎ — address không ghi rõ 'TP <tỉnh>' (nghi TX Duyên Hải...): {len(skip_nocity)}")
for x in skip_nocity[:12]: print("     ?", x)
src=collections.Counter(x[2] for x in fixed)
print("\n  placeId-cũ hay gặp:", src.most_common(8))
if APPLY:
    json.dump(d, open(DATA,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n  ✅ ĐÃ GHI {DATA}")
else:
    print("\n  (DRY-RUN — chưa ghi)")
