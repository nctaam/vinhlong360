"""Gộp entity TRÙNG (cùng thực thể) — DF-01/05. §1.4: cặp xác-minh TAY (không heuristic).
Mỗi cặp: dup → canonical. Repoint rel + itinerary-stop về canonical, dedupe, gộp field
(summary dài hơn, fill coords/images/attrs thiếu), xoá dup. DRY-RUN mặc định; --apply ghi.
"""
import json, sys, collections
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent; DATA=ROOT/"web/data.json"
APPLY="--apply" in sys.argv
# dup_id -> canonical_id (đã verify tay: cùng thực thể, khác id). Canonical = bản giàu
# summary nhất + placeId đúng. Landmark tên-riêng rõ ràng (KHÔNG gộp 'chợ'/'khách sạn'
# generic — chúng là nơi KHÁC nhau).
MERGE = {
    # đợt 1 (đã chạy — id cũ đã mất, script tự bỏ qua)
    "khu-luu-niem-giao-su-vien-si-tran-dai-nghia": "khu-luu-niem-tran-dai-nghia-vinh-long",
    "cu-lao-may-tra-on-vinh-long": "cu-lao-may-tra-on",
    # đợt 2 — name-variant dups (chùa/đình/cồn/cửa hàng — cùng 1 nơi, gộp vào bản giàu nhất)
    "chua-phuoc-hau": "chua-phuoc-hau-ngai-tu",                 # 0c → 536c (vườn kinh đá, Ngãi Tứ)
    "chua-phuoc-hau-vinh-long": "chua-phuoc-hau-ngai-tu",       # 164c → 536c
    "chua-tien-chau": "chua-tien-chau-tien-chau-tu",            # 0c → 296c (cù lao An Bình)
    "chua-tien-chau-di-da-tu": "chua-tien-chau-tien-chau-tu",   # 167c → 296c
    "chua-tien-chau-vinh-long": "chua-tien-chau-tien-chau-tu",  # 178c → 296c
    "dinh-long-thanh-vinh-long": "dinh-long-thanh-long-thanh-vo-mieu",  # 115c → 266c
    "con-nhan": "con-nhan-bien-ba-tri-ben-tre",                 # 70c → 191c
    "cua-hang-ocop-tra-vinh": "cua-hang-ocop-tra-vinh-trung-tam-xuc-tien-thuong-mai-tinh-tra-vinh",  # 45c → 276c
    # đợt 3 — cùng 1 chùa Ông Mẹt (Wat Kompong) TP Trà Vinh; bản kompong giàu hơn (di tích QG 2009)
    "chua-ong-met": "chua-kompong-ong-met",                    # boilerplate → di tích QG, Bodhisàlaràja
    # đợt 4 — cùng 1 đình Long Thanh (Long Thanh Miếu Vũ) P5 Vĩnh Long; bản đủ là -long-thanh-vo-mieu
    "dinh-long-thanh": "dinh-long-thanh-long-thanh-vo-mieu",   # rỗng → di tích QG 1991
}
d=json.load(open(DATA,encoding="utf-8")); ents=d["entities"]; byid={e["id"]:e for e in ents}
# 1. gộp field từ dup vào canonical (giữ canonical, lấy summary DÀI hơn, fill thiếu)
for dup,can in MERGE.items():
    if dup not in byid or can not in byid:
        print(f"  ⚠ bỏ qua {dup}→{can} (thiếu)"); continue
    de,ce=byid[dup],byid[can]
    if len(de.get("summary") or "")>len(ce.get("summary") or ""): ce["summary"]=de["summary"]
    for f in ("coordinates","placeId","images","source"):
        if not ce.get(f) and de.get(f): ce[f]=de[f]
    da,ca=de.get("attributes") or {},ce.get("attributes") or {}
    if isinstance(da,dict) and isinstance(ca,dict):
        for k,v in da.items(): ca.setdefault(k,v)
        ce["attributes"]=ca
# 2. repoint relationships dup→canonical, dedupe + bỏ self-loop
seen=set(); newrels=[]; rep=0
for r in d["relationships"]:
    f=MERGE.get(r.get("from"),r.get("from")); t=MERGE.get(r.get("to"),r.get("to"))
    if f!=r.get("from") or t!=r.get("to"): rep+=1
    if f==t: continue  # self-loop sau gộp
    key=(f,t,r.get("type"))
    if key in seen: continue
    seen.add(key); r["from"]=f; r["to"]=t; newrels.append(r)
d["relationships"]=newrels
# 3. repoint itinerary stops
istops=0
for it in d.get("itineraries",[]):
    for s in (it.get("stops") or []):
        for k in ("entityId","id","placeId"):
            if s.get(k) in MERGE: s[k]=MERGE[s[k]]; istops+=1
# 4. xoá dup entity
before=len(ents); d["entities"]=[e for e in ents if e["id"] not in MERGE]
print(f"=== MERGE DUP — {'APPLY' if APPLY else 'DRY-RUN'} ===")
print(f"  cặp gộp: {len([x for x in MERGE if x in byid])} | rel repoint: {rep} | itin-stop repoint: {istops}")
print(f"  entities {before}→{len(d['entities'])} | relationships → {len(d['relationships'])}")
if APPLY:
    json.dump(d,open(DATA,"w",encoding="utf-8"),ensure_ascii=False,indent=2); print("  ✅ ĐÃ GHI")
else: print("  (DRY-RUN)")
