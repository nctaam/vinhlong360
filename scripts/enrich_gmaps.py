#!/usr/bin/env python3
"""Bổ sung + cập nhật dữ liệu từ Google Maps: toạ độ chính xác, entity mới."""
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

existing_rels = set()
for r in rels:
    existing_rels.add((r.get("from",""), r.get("to",""), r.get("type","")))

def add_rel(src, dst, rtype):
    if src == dst:
        return
    if (src, dst, rtype) not in existing_rels and (dst, src, rtype) not in existing_rels:
        data["relationships"].append({"from": src, "to": dst, "type": rtype})
        existing_rels.add((src, dst, rtype))

def add_entity(e):
    if e["id"] in by_id:
        return False
    data["entities"].append(e)
    by_id[e["id"]] = e
    return True

# ═══ 1. CẬP NHẬT TOẠ ĐỘ CHÍNH XÁC TỪ GOOGLE MAPS ═══
print("═══ 1. CẬP NHẬT TOẠ ĐỘ GOOGLE MAPS ═══")

COORD_UPDATES = {
    "nha-hang-lang-chai-ben-tre-ben-tre": [10.2410712, 106.3563649],
    "com-tam-co-muoi-ben-tre": [10.242411, 106.373712],
    "khu-du-lich-lan-vuong": [10.2085801, 106.3706958],
    "ben-tau-du-lich-tp-ben-tre-ben-tre": [10.2328447, 106.373955],
    "vuon-am-thuc-mai-an-tiem-ben-tre": [10.2295826, 106.377349],
    "nha-hang-noi-ttc-ben-tre-ben-tre": [10.2326579, 106.367582],
    "ba-danh-homestay-ben-tre": [10.2209397, 106.3938674],
    "nha-mo-homestay-ben-tre": [10.26369, 106.3453674],
    "cong-vien-hoang-lam-ben-tre": [10.2368545, 106.3761081],
    "hu-tieu-pate-ben-tre": [10.2429529, 106.3737592],
}

for eid, coords in COORD_UPDATES.items():
    e = by_id.get(eid)
    if not e:
        print(f"  SKIP (not found): {eid}")
        continue
    old = e.get("coordinates")
    e["coordinates"] = coords
    tag = "NEW" if not old else "UPD"
    print(f"  {tag}: {e['name']} → [{coords[0]:.4f}, {coords[1]:.4f}]")

# Also update area/placeId for entities that were missing them
AREA_FIX = {
    "nha-hang-lang-chai-ben-tre-ben-tre": ("ben-tre", "p-ben-tre"),
    "com-tam-co-muoi-ben-tre": ("ben-tre", "p-an-hoi"),
    "ben-tau-du-lich-tp-ben-tre-ben-tre": ("ben-tre", "p-an-hoi"),
    "vuon-am-thuc-mai-an-tiem-ben-tre": ("ben-tre", "p-ben-tre"),
}
for eid, (area, pid) in AREA_FIX.items():
    e = by_id.get(eid)
    if e:
        changed = []
        if not e.get("area"):
            e["area"] = area
            changed.append(f"area={area}")
        if not e.get("placeId"):
            e["placeId"] = pid
            changed.append(f"placeId={pid}")
        if changed:
            print(f"  FIX: {e['name']}: {', '.join(changed)}")

# ═══ 2. THÊM ENTITY MỚI TỪ GOOGLE MAPS ═══
print("\n═══ 2. ENTITY MỚI ═══")

NEW_ENTITIES = [
    {
        "id": "an-hoi-quan-ben-tre",
        "type": "dish",
        "name": "An Hội Quán",
        "summary": (
            "An Hội Quán tại khu vực trung tâm phường An Hội, TP Bến Tre, "
            "là quán ăn uống kết hợp không gian thư giãn. Phục vụ các món ăn "
            "bình dân và thức uống, phù hợp cho cả gia đình và bạn bè."
        ),
        "area": "ben-tre",
        "placeId": "p-an-hoi",
        "coordinates": [10.2409615, 106.3753189],
        "attributes": {"address": "Phường An Hội, TP Bến Tre"},
        "confidence": 0.7,
    },
    {
        "id": "hu-tieu-hai-san-ben-tre",
        "type": "dish",
        "name": "Hủ Tiếu Hải Sản Bến Tre",
        "summary": (
            "Quán hủ tiếu hải sản tại 36-38 Phan Ngọc Tòng, TP Bến Tre. "
            "Nổi tiếng với hủ tiếu nước dùng ngọt thanh, thêm tôm, mực, cua "
            "và hải sản tươi sống. 4.2★ trên Google Maps với hơn 300 đánh giá. "
            "Bánh ướt ngon, phục vụ nhanh."
        ),
        "area": "ben-tre",
        "placeId": "p-ben-tre",
        "coordinates": [10.2360388, 106.3784242],
        "attributes": {
            "address": "36-38 Phan Ngọc Tòng, TP Bến Tre",
            "price_range": "1-100.000đ",
            "rating": "4.2★ (303 đánh giá)"
        },
        "confidence": 0.8,
    },
    {
        "id": "banh-canh-cua-sg-an-hoi-ben-tre",
        "type": "dish",
        "name": "Bánh Canh Cua Bến Tre Sài Gòn - An Hội",
        "summary": (
            "Quán bánh canh cua tại 12 Phan Ngọc Tòng, khu vực phường An Hội, TP Bến Tre. "
            "Bánh canh cua chắc thịt, nước dùng ngọt béo, topping đầy đặn (riêu cua, chả, "
            "giò heo), giá khoảng 60.000đ. 4.9★ trên Google Maps — quán nhỏ nhưng chất lượng cao."
        ),
        "area": "ben-tre",
        "placeId": "p-an-hoi",
        "coordinates": [10.235012, 106.3787533],
        "attributes": {
            "address": "12 Phan Ngọc Tòng, Phường An Hội, TP Bến Tre",
            "price_range": "~60.000đ",
            "rating": "4.9★ (28 đánh giá)"
        },
        "confidence": 0.8,
    },
    {
        "id": "owa-sushi-ben-tre",
        "type": "dish",
        "name": "OWA SUSHI Bến Tre",
        "summary": (
            "Quán sushi và món Nhật tại Số 41 Đường 30 Tháng 4, phường An Hội, TP Bến Tre. "
            "Phục vụ sushi, sashimi, lẩu Nhật. Giá 100.000–600.000đ. "
            "4.8★ trên Google Maps với hơn 500 đánh giá — quán Nhật hiếm hoi tại Bến Tre."
        ),
        "area": "ben-tre",
        "placeId": "p-an-hoi",
        "coordinates": [10.2378225, 106.3754383],
        "attributes": {
            "address": "Số 41 Đường 30/4, Phường An Hội, TP Bến Tre",
            "price_range": "100.000–600.000đ",
            "rating": "4.8★ (514 đánh giá)",
            "specialty": "Sushi, sashimi, món Nhật"
        },
        "confidence": 0.8,
    },
    {
        "id": "bo-dun-muoi-hoa-ben-tre",
        "type": "dish",
        "name": "Bò đun Mười Hoa",
        "summary": (
            "Quán bò đun (lẩu bò) Mười Hoa tại khu vực gần sông Bến Tre, "
            "chuyên bò nhúng me, bò đun nước mắm, lẩu bò — phong cách miền Tây. "
            "Thịt bò tươi, nước lèo đậm đà."
        ),
        "area": "ben-tre",
        "placeId": "p-ben-tre",
        "coordinates": [10.2363289, 106.3793926],
        "attributes": {
            "address": "TP Bến Tre (gần sông)",
            "specialty": "Bò đun, lẩu bò miền Tây"
        },
        "confidence": 0.7,
    },
    {
        "id": "tiem-ca-phe-bac-xiu-ben-tre",
        "type": "attraction",
        "name": "Tiệm cà phê bạc xỉu",
        "summary": (
            "Tiệm cà phê bạc xỉu tại phường An Hội, TP Bến Tre. "
            "Quán nhỏ xinh chuyên bạc xỉu (cà phê sữa đá kiểu miền Nam), "
            "không gian ấm cúng, phù hợp check-in và thư giãn."
        ),
        "area": "ben-tre",
        "placeId": "p-an-hoi",
        "coordinates": [10.2394385, 106.3773479],
        "attributes": {
            "address": "Phường An Hội, TP Bến Tre",
            "specialty": "Bạc xỉu, cà phê"
        },
        "confidence": 0.65,
    },
    {
        "id": "tiem-ca-phe-nam-ky-ben-tre",
        "type": "attraction",
        "name": "Tiệm Cà Phê Nam Kỳ - Năm Mười",
        "summary": (
            "Tiệm Cà Phê Nam Kỳ (Năm Mười) tại phường An Hội, TP Bến Tre. "
            "Quán cà phê mang phong cách Nam Kỳ xưa, trang trí vintage, "
            "phục vụ cà phê phin truyền thống và các thức uống sáng tạo."
        ),
        "area": "ben-tre",
        "placeId": "p-an-hoi",
        "coordinates": [10.2399436, 106.3788277],
        "attributes": {
            "address": "Phường An Hội, TP Bến Tre",
            "style": "Vintage, phong cách Nam Kỳ xưa"
        },
        "confidence": 0.65,
    },
    {
        "id": "lamera-homestay-coffee-ben-tre",
        "type": "accommodation",
        "name": "Lamera Homestay Coffee",
        "summary": (
            "Lamera Homestay Coffee nằm gần trung tâm TP Bến Tre, "
            "kết hợp lưu trú và quán cà phê. Phòng studio tiện nghi, "
            "phù hợp cho du khách cá nhân hoặc cặp đôi muốn ở gần trung tâm."
        ),
        "area": "ben-tre",
        "placeId": "p-ben-tre",
        "coordinates": [10.2399902, 106.3674393],
        "attributes": {
            "address": "TP Bến Tre",
            "style": "Homestay kết hợp quán cà phê"
        },
        "confidence": 0.7,
    },
    {
        "id": "tron-homestay-ben-tre",
        "type": "accommodation",
        "name": "Trốn Homestay Bến Tre",
        "summary": (
            "Trốn Homestay tại TP Bến Tre, mang ý nghĩa 'trốn' khỏi đô thị "
            "để hòa mình vào thiên nhiên xứ dừa. Không gian yên tĩnh, xanh mát, "
            "phù hợp nghỉ dưỡng cuối tuần."
        ),
        "area": "ben-tre",
        "placeId": "p-ben-tre",
        "coordinates": [10.2556, 106.3896408],
        "attributes": {
            "address": "TP Bến Tre"
        },
        "confidence": 0.65,
    },
]

for e in NEW_ENTITIES:
    e["created_at"] = NOW
    e["updatedAt"] = NOW
    e["source"] = {"title": "Google Maps", "url": "https://maps.google.com"}
    if add_entity(e):
        print(f"  ADD: {e['name']} [{e['type']}] @ [{e['coordinates'][0]:.4f}, {e['coordinates'][1]:.4f}]")
    else:
        print(f"  SKIP (exists): {e['name']}")

# ═══ 3. RELATIONSHIPS ═══
print("\n═══ 3. RELATIONSHIPS ═══")

# New dishes in An Hội
anhoi_new = ["an-hoi-quan-ben-tre", "banh-canh-cua-sg-an-hoi-ben-tre",
             "owa-sushi-ben-tre", "tiem-ca-phe-bac-xiu-ben-tre",
             "tiem-ca-phe-nam-ky-ben-tre"]
for eid in anhoi_new:
    add_rel(eid, "p-an-hoi", "produced_in")
    add_rel(eid, "cong-vien-an-hoi", "associated_with")

# Dishes near An Hội but in p-ben-tre
bt_new = ["hu-tieu-hai-san-ben-tre", "bo-dun-muoi-hoa-ben-tre"]
for eid in bt_new:
    add_rel(eid, "p-ben-tre", "produced_in")

# Homestays
hs_new = ["lamera-homestay-coffee-ben-tre", "tron-homestay-ben-tre"]
for eid in hs_new:
    add_rel(eid, "p-ben-tre", "produced_in")
    add_rel(eid, "ho-truc-giang", "associated_with")

# Cross-link quán ăn An Hội
all_anhoi_food = [
    "an-hoi-quan-ben-tre", "banh-canh-cua-sg-an-hoi-ben-tre",
    "owa-sushi-ben-tre", "bi-bun-di-hai-thoi-ben-tre",
    "banh-xeo-nguyen-hue-ben-tre", "bun-bo-hue-chi-hang-ben-tre",
    "lo-banh-mi-tan-thanh-ben-tre", "banh-canh-bot-xat-cho-ben-tre",
]
for i, a in enumerate(all_anhoi_food):
    for b in all_anhoi_food[i+1:i+3]:
        add_rel(a, b, "related_to")

# Cross-link cafés
add_rel("tiem-ca-phe-bac-xiu-ben-tre", "tiem-ca-phe-nam-ky-ben-tre", "related_to")

# Link homestays to restaurants
for h in hs_new + ["ba-danh-homestay-ben-tre", "hoa-dua-homestay-ben-tre",
                    "nhon-thanh-homestay-ben-tre", "duyen-que-homestay-ben-tre"]:
    add_rel(h, "vuon-am-thuc-mai-an-tiem-ben-tre", "associated_with")

# ═══ 4. DEDUP + SAVE ═══
seen = set()
deduped = []
for r in data["relationships"]:
    key = (r.get("from",""), r.get("to",""), r.get("type",""))
    if r.get("from") == r.get("to"):
        continue
    if key not in seen:
        seen.add(key)
        deduped.append(r)
data["relationships"] = deduped

# ═══ SUMMARY ═══
new_count = sum(1 for e in data["entities"] if e.get("created_at") == NOW)
coord_updated = sum(1 for eid in COORD_UPDATES if eid in by_id)
anhoi_total = sum(1 for e in data["entities"] if e.get("placeId") == "p-an-hoi")
bt_total = sum(1 for e in data["entities"] if e.get("area") == "ben-tre")

print(f"\n{'═'*60}")
print(f"Coordinates updated: {coord_updated}")
print(f"New entities added: {new_count}")
print(f"P. An Hội entities: {anhoi_total}")
print(f"Bến Tre area total: {bt_total}")

with DATA.open("w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=None, separators=(",", ":"))
print(f"\n✅ Saved: {len(data['entities'])} entities, {len(data['relationships'])} rels")
