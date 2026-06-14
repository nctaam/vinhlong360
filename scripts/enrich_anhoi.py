#!/usr/bin/env python3
"""Bổ sung & sửa chữa dữ liệu Phường An Hội, TP Bến Tre."""
import json, sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "web" / "data.json"
sys.stdout.reconfigure(encoding="utf-8")

data = json.load(DATA.open("r", encoding="utf-8-sig"))
entities = data["entities"]
rels = data["relationships"]
by_id = {e["id"]: e for e in entities}
NOW = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ═══ 1. FIX: Cồn Tiên — thuộc Châu Thành, KHÔNG phải An Hội ═══
print("═══ 1. Fix Cồn Tiên placeId ═══")
ct = by_id.get("con-tien")
if ct and ct.get("placeId") == "p-an-hoi":
    ct["placeId"] = "xa-chau-thanh"  # or nearest place entity
    print(f"  Cồn Tiên: placeId p-an-hoi → xa-chau-thanh (Tiên Long, Châu Thành)")

# ═══ 2. FIX: Merge Diamond Stars duplicate ═══
print("\n═══ 2. Merge Diamond Stars duplicate ═══")
keep = by_id.get("diamond-stars-ben-tre-hotel")
remove = by_id.get("khach-san-diamond-stars")
if keep and remove:
    # Transfer address from remove → keep
    r_attrs = remove.get("attributes") or {}
    k_attrs = keep.get("attributes") or {}
    if isinstance(r_attrs, dict) and r_attrs.get("address") and isinstance(k_attrs, dict):
        if not k_attrs.get("address"):
            k_attrs["address"] = r_attrs["address"]
            keep["attributes"] = k_attrs
            print(f"  Transferred address: {r_attrs['address']}")
    # Redirect rels
    redirected = 0
    for r in rels:
        if r.get("from") == "khach-san-diamond-stars":
            r["from"] = "diamond-stars-ben-tre-hotel"
            redirected += 1
        if r.get("to") == "khach-san-diamond-stars":
            r["to"] = "diamond-stars-ben-tre-hotel"
            redirected += 1
    data["entities"] = [e for e in data["entities"] if e["id"] != "khach-san-diamond-stars"]
    del by_id["khach-san-diamond-stars"]
    print(f"  Merged khach-san-diamond-stars → diamond-stars-ben-tre-hotel ({redirected} rels)")

# ═══ 3. FIX: Link entities to p-an-hoi (confirmed addresses) ═══
print("\n═══ 3. Link entities to p-an-hoi ═══")
# P.1, P.2, P.3 đã sáp nhập thành P. An Hội (01/2020)
TO_LINK = {
    "tt-thuong-mai-sense-city-ben-tre": "26A Trần Quốc Tuấn, An Hội",
    "cho-dem-ben-tre": "136 Đại Lộ Đồng Khởi, An Hội",
    "ks-nh-hung-vuong": "148 Hùng Vương, An Hội",
    "co-so-keo-dua-thanh-long-ben-tre": "73 Nguyễn Đình Chiểu, P.1 → An Hội",
    "cua-hang-dac-san-dua-ben-tre-cong-ty-tnhh-dong-a-ben-tre": "61 Đồng Khởi, P.3 → An Hội",
    "buu-dien-trung-tam-tp-ben-tre-ben-tre": "3 Đại lộ Đồng Khởi, P.2 → An Hội",
    "hu-tieu-chu-hien-ben-tre": "near chợ BT, Nguyễn Đình Chiểu → An Hội",
    "quan-pho-sang-duong-tran-quoc-tuan-ben-tre": "Trần Quốc Tuấn → An Hội",
    "banh-canh-cho-ben-tre-hang-goc-cho-ben-tre-ben-tre": "gần chợ BT → An Hội",
}
linked = 0
for eid, reason in TO_LINK.items():
    e = by_id.get(eid)
    if e:
        old_pid = e.get("placeId", "")
        e["placeId"] = "p-an-hoi"
        if not e.get("area"):
            e["area"] = "ben-tre"
        linked += 1
        print(f"  {e['name']}: placeId={old_pid} → p-an-hoi ({reason})")
print(f"  Total linked: {linked}")

# ═══ 4. UPDATE: p-an-hoi place entity ═══
print("\n═══ 4. Update p-an-hoi place entity ═══")
anhoi = by_id.get("p-an-hoi")
if anhoi:
    anhoi["summary"] = (
        "Phường An Hội là phường trung tâm thành phố Bến Tre, được thành lập năm 2020 "
        "trên cơ sở hợp nhất 3 phường cũ (Phường 1, 2, 3). Nơi đây tập trung nhiều "
        "công trình quan trọng: Công viên An Hội, Hồ Trúc Giang, Bảo tàng Bến Tre, "
        "Đình An Hội (di tích cấp tỉnh), Chùa Viên Minh, chợ Bến Tre, Chợ đêm Bến Tre "
        "và trung tâm thương mại Sense City. Các tuyến đường chính: Đại lộ Đồng Khởi, "
        "Hùng Vương, Nguyễn Đình Chiểu, 3 Tháng 2, Nam Kỳ Khởi Nghĩa, Trần Quốc Tuấn."
    )
    anhoi["parentId"] = "thanh-pho-ben-tre-ben-tre"
    anhoi["level"] = "phuong"
    anhoi["legacyArea"] = "TP Bến Tre"
    anhoi["source"] = {
        "title": "UBND phường An Hội + Wikipedia TP Bến Tre",
        "url": "https://vi.wikipedia.org/wiki/B%E1%BA%BFn_Tre_(th%C3%A0nh_ph%E1%BB%91)"
    }
    print("  Updated summary, parentId, source")

# ═══ 5. ENRICH: Hồ Trúc Giang ═══
print("\n═══ 5. Enrich Hồ Trúc Giang ═══")
htg = by_id.get("ho-truc-giang")
if htg:
    htg["summary"] = (
        "Hồ Trúc Giang (còn gọi là Bờ Hồ hoặc Hồ Chung Thủy) nằm ở trung tâm TP Bến Tre, "
        "xây dựng năm 1930, diện tích khoảng 2 ha, hình thang, cải tạo hoàn thành năm 2006. "
        "Giữa hồ có nhà thủy tạ, bao quanh là hàng cây me tây và phượng vĩ cổ thụ. "
        "Đây là không gian xanh lý tưởng để đi dạo, tập thể dục, ngắm cảnh buổi sáng và chiều tối."
    )
    htg["source"] = {"title": "bazantravel.com", "url": "https://bazantravel.com/ho-truc-giang-ben-tre/"}
    if not htg.get("attributes") or not isinstance(htg.get("attributes"), dict):
        htg["attributes"] = {}
    htg["attributes"]["built_year"] = "1930"
    htg["attributes"]["area"] = "~2 ha"
    htg["attributes"]["renovated"] = "2006"
    htg["attributes"]["aliases"] = "Bờ Hồ, Hồ Chung Thủy"
    print("  Enriched: built_year, area, aliases, source")

# ═══ 6. ENRICH: Đình An Hội ═══
print("\n═══ 6. Enrich Đình An Hội ═══")
dah = by_id.get("dinh-an-hoi")
if dah:
    if not dah.get("attributes") or not isinstance(dah.get("attributes"), dict):
        dah["attributes"] = {}
    dah["attributes"]["heritage_level"] = "Di tích Lịch sử - Văn hóa cấp tỉnh"
    dah["attributes"]["founded"] = "trước 1846 (sắc phong năm Thiệu Trị)"
    dah["attributes"]["founder"] = "Huỳnh Văn Sắc"
    dah["attributes"]["ceremonies"] = "Lễ Kỳ Yên (12-13/3 ÂL), Lễ Lạp Miếu"
    print("  Enriched: heritage, ceremonies")

# ═══ 7. ADD: Phở Hồng Cúc ═══
print("\n═══ 7. Add Phở Hồng Cúc ═══")
if "pho-hong-cuc-ben-tre" not in by_id:
    new_entity = {
        "id": "pho-hong-cuc-ben-tre",
        "type": "dish",
        "name": "Phở Hồng Cúc",
        "summary": (
            "Phở Hồng Cúc là thương hiệu phở nổi tiếng nhất TP Bến Tre, tọa lạc tại "
            "106 đường 3/2, phường An Hội. Quán chuyên phở bò với đủ topping: bò viên, "
            "sườn bò, gan bò, gầu bò, cùng lẩu bò và lẩu xí quách. "
            "Giờ mở cửa: sáng 5h–12h, chiều 15h30–21h. Giá 30.000–70.000đ/phần."
        ),
        "area": "ben-tre",
        "placeId": "p-an-hoi",
        "coordinates": [10.2393, 106.3748],
        "source": {"title": "phohongcuc.com + foody.vn", "url": "https://phohongcuc.com/"},
        "attributes": {
            "address": "106 đường 3/2, khu phố 6, phường An Hội, TP Bến Tre",
            "phone": "0932 770 435",
            "opening_hours": "5:00–12:00, 15:30–21:00",
            "price_range": "30.000–70.000đ",
            "specialty": "Phở bò, lẩu bò, lẩu xí quách"
        },
        "confidence": 0.8,
        "created_at": NOW,
        "updatedAt": NOW
    }
    data["entities"].append(new_entity)
    by_id[new_entity["id"]] = new_entity
    print(f"  Added: {new_entity['name']}")

# ═══ 8. ADD: Đền thờ Ân sư tiền vãng ═══
print("\n═══ 8. Add Đền thờ Ân sư tiền vãng ═══")
if "den-tho-an-su-tien-vang-ben-tre" not in by_id:
    new_entity = {
        "id": "den-tho-an-su-tien-vang-ben-tre",
        "type": "history",
        "name": "Đền thờ Ân sư tiền vãng",
        "summary": (
            "Đền thờ Ân sư tiền vãng (miếu Tiên sư) nằm trong khuôn viên Trường Tiểu học Phú Thọ, "
            "đường Nam Kỳ Khởi Nghĩa, phường An Hội, TP Bến Tre. Đền xây dựng năm 1969, "
            "do Thầy Nguyễn Văn Trinh (1901–1975), hiệu trưởng đầu tiên của trường Trung học Kiến Hòa, "
            "sáng lập để tôn vinh các bậc thầy đi trước."
        ),
        "area": "ben-tre",
        "placeId": "p-an-hoi",
        "coordinates": None,
        "source": {
            "title": "Báo Đồng Khởi Online",
            "url": "https://dongkhoi.baovinhlong.vn/den-tho-an-su-tien-vang-o-ben-tre-16112020-a80176.html"
        },
        "attributes": {
            "address": "Trường TH Phú Thọ, đường Nam Kỳ Khởi Nghĩa, phường An Hội, TP Bến Tre",
            "built_year": "1969",
            "founder": "Thầy Nguyễn Văn Trinh (1901–1975)"
        },
        "confidence": 0.7,
        "created_at": NOW,
        "updatedAt": NOW
    }
    data["entities"].append(new_entity)
    by_id[new_entity["id"]] = new_entity
    print(f"  Added: {new_entity['name']}")

# ═══ 9. ADD: Công viên Hoàng Lam ═══
print("\n═══ 9. Add Công viên Hoàng Lam ═══")
if "cong-vien-hoang-lam-ben-tre" not in by_id:
    new_entity = {
        "id": "cong-vien-hoang-lam-ben-tre",
        "type": "attraction",
        "name": "Công viên Hoàng Lam",
        "summary": (
            "Công viên Hoàng Lam là một trong những công viên nhỏ nằm trong phường An Hội, "
            "TP Bến Tre, phục vụ nhu cầu giải trí và thư giãn của cư dân địa phương."
        ),
        "area": "ben-tre",
        "placeId": "p-an-hoi",
        "coordinates": None,
        "source": {"title": "Wikipedia TP Bến Tre", "url": "https://vi.wikipedia.org/wiki/B%E1%BA%BFn_Tre_(th%C3%A0nh_ph%E1%BB%91)"},
        "confidence": 0.6,
        "created_at": NOW,
        "updatedAt": NOW
    }
    data["entities"].append(new_entity)
    by_id[new_entity["id"]] = new_entity
    print(f"  Added: {new_entity['name']}")

# ═══ 10. ADD: Nhà hàng Khách sạn Hùng Vương — enrich existing ═══
print("\n═══ 10. Enrich KS-NH Hùng Vương ═══")
hv = by_id.get("ks-nh-hung-vuong")
if hv:
    hv["summary"] = (
        "Khách sạn nhà hàng Hùng Vương tọa lạc tại 148 Hùng Vương, phường An Hội, TP Bến Tre. "
        "Không gian rộng rãi, hiện đại với khu VIP riêng phục vụ tiệc lớn, tiệc cưới, sinh nhật. "
        "Đội ngũ đầu bếp mang đến set menu đa dạng từ buffet sáng đến cơm nhà đậm hương vị Nam Bộ."
    )
    if not hv.get("attributes") or not isinstance(hv.get("attributes"), dict):
        hv["attributes"] = {}
    hv["attributes"]["phone"] = "0275 3822 408"
    print("  Enriched: summary, phone")

# ═══ 11. ADD RELATIONSHIPS ═══
print("\n═══ 11. Add relationships for p-an-hoi ═══")
# Build existing rel set
existing = set()
for r in rels:
    existing.add((r.get("from",""), r.get("to",""), r.get("type","")))

# All entities linked to p-an-hoi
anhoi_entities = [e for e in data["entities"] if e.get("placeId") == "p-an-hoi"]
anhoi_ids = [e["id"] for e in anhoi_entities]

new_rels = []
def add_rel(src, dst, rtype):
    if (src, dst, rtype) not in existing and (dst, src, rtype) not in existing:
        new_rels.append({"from": src, "to": dst, "type": rtype})
        existing.add((src, dst, rtype))

# Link all An Hội entities to p-an-hoi via produced_in
for eid in anhoi_ids:
    if eid != "p-an-hoi":
        add_rel(eid, "p-an-hoi", "produced_in")

# Semantic relationships within An Hội
# Dishes ↔ restaurants/attractions
dishes = [e["id"] for e in anhoi_entities if e["type"] == "dish"]
attractions = [e["id"] for e in anhoi_entities if e["type"] == "attraction"]
accommodations = [e["id"] for e in anhoi_entities if e["type"] == "accommodation"]
history_sites = [e["id"] for e in anhoi_entities if e["type"] == "history"]
nature_sites = [e["id"] for e in anhoi_entities if e["type"] == "nature"]

# Hồ Trúc Giang ↔ Công viên An Hội (nearby)
add_rel("ho-truc-giang", "cong-vien-an-hoi", "related_to")
# Đình An Hội ↔ Chùa Viên Minh (history sites in same ward)
add_rel("dinh-an-hoi", "chua-vien-minh-ben-tre", "related_to")
# Bảo tàng ↔ Đình An Hội
add_rel("bao-tang-ben-tre", "dinh-an-hoi", "related_to")
# Chợ đêm ↔ Công viên An Hội
add_rel("cho-dem-ben-tre", "cong-vien-an-hoi", "related_to")
# Phở Hồng Cúc ↔ attractions
if "pho-hong-cuc-ben-tre" in by_id:
    add_rel("pho-hong-cuc-ben-tre", "cho-dem-ben-tre", "associated_with")
    add_rel("pho-hong-cuc-ben-tre", "cong-vien-an-hoi", "associated_with")
# KS-NH Hùng Vương ↔ Bảo tàng (same street)
add_rel("ks-nh-hung-vuong", "bao-tang-ben-tre", "associated_with")
# Diamond Stars ↔ attractions
add_rel("diamond-stars-ben-tre-hotel", "cong-vien-an-hoi", "associated_with")
add_rel("diamond-stars-ben-tre-hotel", "ho-truc-giang", "associated_with")
# Sense City ↔ Chợ đêm
add_rel("tt-thuong-mai-sense-city-ben-tre", "cho-dem-ben-tre", "related_to")
# Event ↔ Công viên
if "tuan-le-van-hoa-am-thuc-an-hoi-2026" in by_id:
    add_rel("tuan-le-van-hoa-am-thuc-an-hoi-2026", "cong-vien-an-hoi", "hosts")
# Đền thờ ↔ Đình An Hội
if "den-tho-an-su-tien-vang-ben-tre" in by_id:
    add_rel("den-tho-an-su-tien-vang-ben-tre", "dinh-an-hoi", "related_to")
# Công viên Hoàng Lam ↔ Công viên An Hội
if "cong-vien-hoang-lam-ben-tre" in by_id:
    add_rel("cong-vien-hoang-lam-ben-tre", "cong-vien-an-hoi", "related_to")

data["relationships"].extend(new_rels)
print(f"  Added {len(new_rels)} relationships")

# ═══ SUMMARY ═══
print(f"\n{'═'*60}")
anhoi_final = [e for e in data["entities"] if e.get("placeId") == "p-an-hoi"]
print(f"TỔNG KẾT P. An Hội:")
print(f"  Entities: {len(anhoi_final)}")
from collections import Counter
type_counts = Counter(e["type"] for e in anhoi_final)
for t, c in type_counts.most_common():
    print(f"    {t}: {c}")

# Dedup rels
seen = set()
deduped = []
for r in data["relationships"]:
    key = (r.get("from",""), r.get("to",""), r.get("type",""))
    rev = (r.get("to",""), r.get("from",""), r.get("type",""))
    if r.get("from") == r.get("to"):
        continue
    if key not in seen:
        seen.add(key)
        deduped.append(r)
removed_dup = len(data["relationships"]) - len(deduped)
data["relationships"] = deduped
if removed_dup:
    print(f"  Deduped rels: removed {removed_dup}")

# Save
with DATA.open("w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=None, separators=(",", ":"))
print(f"\n✅ Saved: {len(data['entities'])} entities, {len(data['relationships'])} rels")
