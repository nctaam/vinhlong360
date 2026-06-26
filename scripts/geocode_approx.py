"""Nâng cấp toạ độ gần-đúng → THẬT qua Nominatim (OSM, miễn phí) — §1.4 CÓ GATE.
Chỉ nhận geocode khi: (a) có kết quả, (b) trong VN, (c) cách centroid-ward-của-placeId <=5km
(loại match sai trùng-tên-đường tỉnh khác). Nhận → set coords + bỏ cờ coords_approximate.
Loại → giữ nguyên (gần-đúng). KHÔNG bịa: toạ độ là từ OSM cho địa chỉ thật + khớp ward.
Usage: python scripts/geocode_approx.py [--limit N] [--apply]   (§B1 backup trước --apply)
"""
import json, re, sys, time, math, urllib.parse, urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
DATA=ROOT/"web/data.json"
APPLY="--apply" in sys.argv
LIMIT=next((int(a.split("=")[1]) for a in sys.argv if a.startswith("--limit=")), None)
UA="vinhlong360-geocode/1.0 (phamhoctriet8882@gmail.com)"
CITY={"vinh-long":"Vĩnh Long","ben-tre":"Bến Tre","tra-vinh":"Trà Vinh"}
def hav(a,b):
    la1,lo1,la2,lo2=map(math.radians,[a[0],a[1],b[0],b[1]])
    h=math.sin((la2-la1)/2)**2+math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2
    return 2*6371*math.asin(min(1,math.sqrt(h)))
def A(e):
    a=e.get("attributes"); return a if isinstance(a,dict) else {}
def street_of(addr):
    # lấy phần đường trước marker ward; bỏ số nhà đầu cho Nominatim VN
    s=re.split(r",\s*(?:P\.|Phường|Xã|TT\.|Thị trấn|Thành Phố|TP|Khóm|Ấp)", addr, flags=re.I)[0]
    s=re.sub(r"^\s*(?:số\s*)?\d+[A-Za-z]?(?:/\d+[A-Za-z]?)?\s*", "", s, flags=re.I)  # bỏ số nhà
    return s.strip(" ,")
def geocode(q):
    url="https://nominatim.openstreetmap.org/search?"+urllib.parse.urlencode({"format":"json","limit":1,"countrycodes":"vn","q":q})
    req=urllib.request.Request(url, headers={"User-Agent":UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            d=json.load(r)
        return (float(d[0]["lat"]), float(d[0]["lon"])) if d else None
    except Exception as ex:
        return ("ERR", str(ex)[:40])

with open(DATA, encoding="utf-8") as f:
    d = json.load(f)
ents=d["entities"]; byid={e["id"]:e for e in ents}
wards={e["id"]:e for e in ents if e.get("type")=="place" and e.get("level") in ("xa","phuong")}
cand=[]
for e in ents:
    if e.get("type")=="place": continue
    a=A(e); addr=a.get("address") or ""; pid=e.get("placeId")
    if not (a.get("coords_approximate") or not e.get("coordinates")): continue
    if pid not in wards or not wards[pid].get("coordinates"): continue
    st=street_of(addr)
    if not st or not re.search(r"[A-Za-zÀ-ỹ]{3}", st): continue   # cần tên đường thật
    cand.append(e)
if LIMIT: cand=cand[:LIMIT]
print(f"=== GEOCODE approx — {'APPLY' if APPLY else 'DRY-RUN'} | ứng viên: {len(cand)} ===")
acc=rej=err=0; updates={}
for i,e in enumerate(cand):
    a=A(e); st=street_of(a.get("address") or ""); prov=CITY.get(e.get("area"),"")
    addr=a.get("address") or ""
    wname=re.sub(r"^(xã|phường)\s+","",wards[e["placeId"]].get("name",""),flags=re.I).strip()
    # neo locality để OSM không khớp nhầm 'tỉnh': TP nếu là thành-phố, else tên ward
    if re.search(r"thành phố|tp\b", addr, re.I): loc=f"thành phố {prov}"
    else: loc=f"{wname}, {prov}"
    q=f"{st}, {loc}, Việt Nam"
    res=geocode(q)
    wc=tuple(wards[e["placeId"]]["coordinates"])
    if isinstance(res,tuple) and res[0]=="ERR": err+=1; tag=f"ERR {res[1]}"
    elif res is None: rej+=1; tag="rỗng"
    else:
        km=hav(res, wc)
        if 0.2<km<=5: acc+=1; updates[e["id"]]=res; tag=f"✓ NHẬN ({km:.1f}km) {res}"
        elif km<=0.2: rej+=1; tag=f"✗ echo centroid ({km*1000:.0f}m)"
        else: rej+=1; tag=f"✗ loại ({km:.1f}km lệch ward)"
    if i<30 or isinstance(res,tuple) and res[0]=="ERR":
        print(f"  [{i+1}] {e['id'][:34]:34s} '{q[:38]}' → {tag}")
    time.sleep(1.1)
print(f"\n  NHẬN {acc} | LOẠI {rej} | ERR {err}  (tỉ lệ nhận {acc/max(1,len(cand))*100:.0f}%)")
if APPLY and updates:
    for e in ents:
        if e["id"] in updates:
            e["coordinates"]=list(updates[e["id"]])
            a=A(e); a.pop("coords_approximate",None); e["attributes"]=a
    json.dump(d,open(DATA,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
    print(f"  ✅ ĐÃ GHI {DATA} ({len(updates)} coords thật)")
elif not APPLY:
    print("  (DRY-RUN — chưa ghi)")
