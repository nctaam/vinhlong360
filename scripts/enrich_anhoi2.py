#!/usr/bin/env python3
"""Bổ sung quán ăn địa phương, homestay, điểm du lịch cho P. An Hội & TP Bến Tre."""
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

existing = set()
for r in rels:
    existing.add((r.get("from",""), r.get("to",""), r.get("type","")))

def add_entity(e):
    if e["id"] in by_id:
        print(f"  SKIP (exists): {e['name']}")
        return False
    data["entities"].append(e)
    by_id[e["id"]] = e
    print(f"  ADD: {e['name']} [{e['type']}]")
    return True

def add_rel(src, dst, rtype):
    if (src, dst, rtype) not in existing and (dst, src, rtype) not in existing:
        if src == dst:
            return
        data["relationships"].append({"from": src, "to": dst, "type": rtype})
        existing.add((src, dst, rtype))

# ═══ QUÁN ĂN ĐỊA PHƯƠNG (trong P. An Hội) ═══
print("═══ QUÁN ĂN ĐỊA PHƯƠNG ═══")

add_entity({
    "id": "bi-bun-di-hai-thoi-ben-tre",
    "type": "dish",
    "name": "Bì bún Dì Hai Thới",
    "summary": (
        "Bì bún Dì Hai Thới là quán ăn bình dân lâu đời tại 59 Lê Lợi, phường An Hội "
        "(P.2 cũ), TP Bến Tre. Món bì bún đặc trưng với gạo rang thơm, thịt ba chỉ, "
        "nem cuốn, rau sống tươi. Giá chỉ 15.000–23.000đ/phần, là điểm ăn sáng quen thuộc "
        "của dân địa phương."
    ),
    "area": "ben-tre",
    "placeId": "p-an-hoi",
    "coordinates": [10.2371, 106.3753],
    "source": {"title": "luhanhvietnam.com.vn", "url": "https://luhanhvietnam.com.vn/du-lich/top-10-quan-an-ngon-o-ben-tre-noi-danh.html"},
    "attributes": {
        "address": "59 Lê Lợi, Phường An Hội (P.2 cũ), TP Bến Tre",
        "price_range": "15.000–23.000đ",
        "specialty": "Bì bún, nem cuốn"
    },
    "confidence": 0.75,
    "created_at": NOW, "updatedAt": NOW
})

add_entity({
    "id": "banh-xeo-nguyen-hue-ben-tre",
    "type": "dish",
    "name": "Bánh xèo Nguyễn Huệ",
    "summary": (
        "Quán bánh xèo bình dân tại 266B Nguyễn Huệ, phường An Hội (P.1 cũ), TP Bến Tre. "
        "Bánh xèo miền Tây giòn rụm, nhân tôm thịt, giá mồng, ăn kèm rau sống cuốn bánh tráng. "
        "Giá chỉ 15.000đ/cái, là quán ăn sáng quen thuộc của người dân."
    ),
    "area": "ben-tre",
    "placeId": "p-an-hoi",
    "coordinates": [10.2355, 106.3740],
    "source": {"title": "hoclaixetphcm.com", "url": "https://www.hoclaixetphcm.com/an-sang-ben-tre/"},
    "attributes": {
        "address": "266B Nguyễn Huệ, Phường An Hội (P.1 cũ), TP Bến Tre",
        "price_range": "15.000đ/cái",
        "specialty": "Bánh xèo miền Tây"
    },
    "confidence": 0.7,
    "created_at": NOW, "updatedAt": NOW
})

add_entity({
    "id": "bun-bo-hue-chi-hang-ben-tre",
    "type": "dish",
    "name": "Bún bò Huế Chị Hằng",
    "summary": (
        "Quán bún bò Huế Chị Hằng tại 76C Đại Lộ Đồng Khởi, phường An Hội, TP Bến Tre. "
        "Nước dùng đậm đà cay nồng từ sả ớt, bò gân mềm, chả cua, "
        "kèm rau sống và mắm ruốc. Quán đông khách vào buổi sáng."
    ),
    "area": "ben-tre",
    "placeId": "p-an-hoi",
    "coordinates": [10.2405, 106.3755],
    "source": {"title": "toplist.vn + search", "url": "https://toplist.vn/top-list/quan-an-ngon-nhat-tai-ben-tre-34280.htm"},
    "attributes": {
        "address": "76C Đại Lộ Đồng Khởi, Phường An Hội, TP Bến Tre",
        "specialty": "Bún bò Huế"
    },
    "confidence": 0.7,
    "created_at": NOW, "updatedAt": NOW
})

add_entity({
    "id": "lo-banh-mi-tan-thanh-ben-tre",
    "type": "dish",
    "name": "Lò Bánh Mì Tân Thành",
    "summary": (
        "Lò Bánh Mì Tân Thành tại 193A1 Đại Lộ Đồng Khởi, TP Bến Tre, nổi tiếng với ổ bánh mì "
        "giòn rụm nhân xíu mại thơm béo đặc trưng. Giá bình dân, là điểm ăn sáng "
        "quen thuộc từ đời cha ông của người dân Bến Tre."
    ),
    "area": "ben-tre",
    "placeId": "p-an-hoi",
    "coordinates": [10.2410, 106.3748],
    "source": {"title": "hoclaixetphcm.com", "url": "https://www.hoclaixetphcm.com/an-sang-ben-tre/"},
    "attributes": {
        "address": "193A1 Đại Lộ Đồng Khởi, TP Bến Tre",
        "specialty": "Bánh mì xíu mại"
    },
    "confidence": 0.7,
    "created_at": NOW, "updatedAt": NOW
})

add_entity({
    "id": "banh-canh-bot-xat-cho-ben-tre",
    "type": "dish",
    "name": "Bánh canh bột xắt chợ Bến Tre",
    "summary": (
        "Quán bánh canh bột xắt nằm tại 10 Chi Lăng (khu vực chợ Bến Tre), phường An Hội "
        "(P.2 cũ). Sợi bột xắt thủ công mềm dai, nước dùng sánh béo hầm từ xương heo và vịt, "
        "ăn kèm chả và rau. Giá bình dân ~25.000đ. Đặc sản dân dã xứ dừa."
    ),
    "area": "ben-tre",
    "placeId": "p-an-hoi",
    "coordinates": [10.2380, 106.3762],
    "source": {"title": "bentretoplist.com", "url": "https://bentretoplist.com/top-10-quan-banh-canh-bot-xat-o-ben-tre-ngon-re/"},
    "attributes": {
        "address": "10 Chi Lăng, Phường An Hội (P.2 cũ), TP Bến Tre",
        "price_range": "~25.000đ",
        "specialty": "Bánh canh bột xắt vịt"
    },
    "confidence": 0.75,
    "created_at": NOW, "updatedAt": NOW
})

add_entity({
    "id": "lau-mam-truc-giang-ben-tre",
    "type": "dish",
    "name": "Lẩu Mắm Trúc Giang",
    "summary": (
        "Quán lẩu mắm Trúc Giang tại 293D Nguyễn Thị Định, TP Bến Tre, chuyên lẩu mắm "
        "và lẩu chua đặc sản miền Tây. Nước lẩu mắm cá linh đậm đà, rau đồng xanh mướt, "
        "cá lóc phi lê tươi. Giờ: 9h–20h30."
    ),
    "area": "ben-tre",
    "placeId": "p-ben-tre",
    "coordinates": [10.2315, 106.3810],
    "source": {"title": "toplist.vn", "url": "https://toplist.vn/top-list/quan-an-ngon-nhat-tai-ben-tre-34280.htm"},
    "attributes": {
        "address": "293D Nguyễn Thị Định, TP Bến Tre",
        "opening_hours": "09:00–20:30",
        "specialty": "Lẩu mắm, lẩu chua miền Tây"
    },
    "confidence": 0.7,
    "created_at": NOW, "updatedAt": NOW
})

add_entity({
    "id": "hu-tieu-pate-ben-tre",
    "type": "dish",
    "name": "Hủ tiếu pate Bến Tre",
    "summary": (
        "Hủ tiếu pate là món ăn đặc trưng chỉ có ở Bến Tre, tại quán 226/1A đường 30/4, "
        "Phường 4, TP Bến Tre. Tô hủ tiếu nước dùng trong ngọt, sợi mềm dai, kèm thịt nguội, "
        "gan, tôm và pate béo bùi — sự pha trộn Pháp-Việt độc đáo. Giá 25.000–41.000đ. "
        "Giờ: 15h–22h."
    ),
    "area": "ben-tre",
    "placeId": "p-ben-tre",
    "coordinates": [10.2430, 106.3780],
    "source": {"title": "toplist.vn + luhanhvietnam", "url": "https://toplist.vn/top-list/quan-an-ngon-nhat-tai-ben-tre-34280.htm"},
    "attributes": {
        "address": "226/1A đường 30/4, Phường 4, TP Bến Tre",
        "price_range": "25.000–41.000đ",
        "opening_hours": "15:00–22:00",
        "specialty": "Hủ tiếu pate Bến Tre"
    },
    "confidence": 0.75,
    "created_at": NOW, "updatedAt": NOW
})

add_entity({
    "id": "bun-rieu-tu-dien-ben-tre",
    "type": "dish",
    "name": "Bún riêu Tú Điền",
    "summary": (
        "Quán bún riêu cua Tú Điền tại 10F Nguyễn Huệ, TP Bến Tre. "
        "Nước dùng chua thanh từ cà chua và riêu cua đồng, kèm tai heo, giò heo, "
        "chả cua, đậu hũ chiên. Giờ: 14h–21h."
    ),
    "area": "ben-tre",
    "placeId": "p-ben-tre",
    "coordinates": None,
    "source": {"title": "toplist.vn", "url": "https://toplist.vn/top-list/quan-an-ngon-nhat-tai-ben-tre-34280.htm"},
    "attributes": {
        "address": "10F Nguyễn Huệ, TP Bến Tre",
        "opening_hours": "14:00–21:00",
        "specialty": "Bún riêu cua đồng"
    },
    "confidence": 0.7,
    "created_at": NOW, "updatedAt": NOW
})

# ═══ HOMESTAY TP BẾN TRE ═══
print("\n═══ HOMESTAY ═══")

add_entity({
    "id": "ba-danh-homestay-ben-tre",
    "type": "accommodation",
    "name": "Ba Danh Homestay",
    "summary": (
        "Ba Danh Homestay tọa lạc tại Phường Phú Khương, TP Bến Tre, gần trung tâm thành phố. "
        "Thiết kế mộc mạc kiểu nhà vườn truyền thống Nam Bộ, mát tự nhiên nhờ bóng dừa, "
        "không cần máy lạnh. Giá 400.000–500.000đ/đêm."
    ),
    "area": "ben-tre",
    "placeId": "p-ben-tre",
    "coordinates": None,
    "source": {"title": "nucuoimekong.com", "url": "https://nucuoimekong.com/homestay-ben-tre"},
    "attributes": {
        "address": "Phường Phú Khương, TP Bến Tre",
        "price_range": "400.000–500.000đ/đêm",
        "style": "Nhà vườn truyền thống, không máy lạnh"
    },
    "confidence": 0.7,
    "created_at": NOW, "updatedAt": NOW
})

add_entity({
    "id": "hoa-dua-homestay-ben-tre",
    "type": "accommodation",
    "name": "Hoa Dừa Homestay",
    "summary": (
        "Hoa Dừa Homestay tại 22D Phường Phú Khương, TP Bến Tre. "
        "Phòng sạch sẽ, không gian thoáng mát yên tĩnh, chủ nhà thân thiện. "
        "Gần trung tâm, tiện di chuyển tham quan Hồ Trúc Giang, Bảo tàng Bến Tre. "
        "Giá 500.000đ/đêm."
    ),
    "area": "ben-tre",
    "placeId": "p-ben-tre",
    "coordinates": None,
    "source": {"title": "nucuoimekong.com", "url": "https://nucuoimekong.com/homestay-ben-tre"},
    "attributes": {
        "address": "22D Phường Phú Khương, TP Bến Tre",
        "price_range": "500.000đ/đêm"
    },
    "confidence": 0.7,
    "created_at": NOW, "updatedAt": NOW
})

add_entity({
    "id": "nhon-thanh-homestay-ben-tre",
    "type": "accommodation",
    "name": "Nhơn Thành Homestay",
    "summary": (
        "Nhơn Thành Homestay tại Phường Phú Khương, TP Bến Tre. "
        "Homestay giá rẻ, rộng rãi và yên tĩnh, tặng kèm xe đạp miễn phí "
        "để đạp quanh vườn dừa và các cù lao gần trung tâm. "
        "Giá 300.000–500.000đ/đêm."
    ),
    "area": "ben-tre",
    "placeId": "p-ben-tre",
    "coordinates": None,
    "source": {"title": "nucuoimekong.com", "url": "https://nucuoimekong.com/homestay-ben-tre"},
    "attributes": {
        "address": "Phường Phú Khương, TP Bến Tre",
        "price_range": "300.000–500.000đ/đêm",
        "amenities": "Xe đạp miễn phí"
    },
    "confidence": 0.7,
    "created_at": NOW, "updatedAt": NOW
})

add_entity({
    "id": "duyen-que-homestay-ben-tre",
    "type": "accommodation",
    "name": "Duyên Quê Charming Countryside",
    "summary": (
        "Duyên Quê Charming Countryside tại Phường Phú Khương, TP Bến Tre, "
        "là homestay cao cấp với không gian yên tĩnh giữa vườn dừa. "
        "Phục vụ ẩm thực Âu-Á và chay, phù hợp khách quốc tế. "
        "Giá 600.000–1.700.000đ/đêm."
    ),
    "area": "ben-tre",
    "placeId": "p-ben-tre",
    "coordinates": None,
    "source": {"title": "nucuoimekong.com", "url": "https://nucuoimekong.com/homestay-ben-tre"},
    "attributes": {
        "address": "Phường Phú Khương, TP Bến Tre",
        "price_range": "600.000–1.700.000đ/đêm",
        "style": "Cao cấp, ẩm thực Âu-Á và chay"
    },
    "confidence": 0.7,
    "created_at": NOW, "updatedAt": NOW
})

add_entity({
    "id": "nha-mo-homestay-ben-tre",
    "type": "accommodation",
    "name": "Nhà Mơ Homestay",
    "summary": (
        "Nhà Mơ Homestay tại Ấp 2, xã Sơn Đông, TP Bến Tre, "
        "nằm giữa vườn trái cây miền Tây yên bình. Không gian mộc mạc, "
        "gần sông, thích hợp cho du khách muốn trải nghiệm cuộc sống miệt vườn."
    ),
    "area": "ben-tre",
    "placeId": "p-ben-tre",
    "coordinates": None,
    "source": {"title": "search results", "url": "https://luhanhvietnam.com.vn/du-lich/top-10-homestay-ben-tre-tuyet-dep.html"},
    "attributes": {
        "address": "Ấp 2, xã Sơn Đông, TP Bến Tre"
    },
    "confidence": 0.65,
    "created_at": NOW, "updatedAt": NOW
})

add_entity({
    "id": "nguyet-que-homestay-ben-tre",
    "type": "accommodation",
    "name": "Nguyệt Quê Homestay & Tours",
    "summary": (
        "Nguyệt Quê Homestay & Tours tại 75Đ, Ấp 4, xã Nhơn Thạnh, TP Bến Tre. "
        "Kết hợp lưu trú và tour trải nghiệm: chèo xuồng, thăm vườn trái cây, "
        "làm kẹo dừa, đạp xe miệt vườn. Phổ biến với khách quốc tế."
    ),
    "area": "ben-tre",
    "placeId": "p-ben-tre",
    "coordinates": None,
    "source": {"title": "search results", "url": "https://luhanhvietnam.com.vn/du-lich/top-10-homestay-ben-tre-tuyet-dep.html"},
    "attributes": {
        "address": "75Đ, Ấp 4, Xã Nhơn Thạnh, TP Bến Tre",
        "services": "Tour chèo xuồng, thăm vườn, làm kẹo dừa"
    },
    "confidence": 0.65,
    "created_at": NOW, "updatedAt": NOW
})

# ═══ ĐỊA ĐIỂM DU LỊCH ═══
print("\n═══ ĐỊA ĐIỂM DU LỊCH ═══")

add_entity({
    "id": "cocofarm-store-ben-tre",
    "type": "attraction",
    "name": "Cocofarm Store",
    "summary": (
        "Cocofarm Store là điểm check-in và mua sắm đặc sản dừa tại TP Bến Tre, "
        "thiết kế chủ yếu từ gỗ dừa, vừa mang nét xưa cũ vừa hiện đại. "
        "Nơi trưng bày và bán các sản phẩm thủ công mỹ nghệ, thực phẩm từ dừa "
        "(kẹo, tinh dầu, mỹ phẩm, đồ trang trí). Phổ biến với du khách trẻ."
    ),
    "area": "ben-tre",
    "placeId": "p-ben-tre",
    "coordinates": None,
    "source": {"title": "phanvantravel.com", "url": "https://phanvantravel.com/dia-diem-du-lich-ben-tre"},
    "attributes": {
        "style": "Thiết kế từ gỗ dừa, check-in + mua sắm"
    },
    "confidence": 0.65,
    "created_at": NOW, "updatedAt": NOW
})

add_entity({
    "id": "bo-ke-song-ben-tre",
    "type": "attraction",
    "name": "Bờ kè sông Bến Tre",
    "summary": (
        "Bờ kè dọc sông Bến Tre (sông Hàm Luông) chạy qua trung tâm thành phố, "
        "đoạn từ Công viên An Hội đến cầu Bến Tre. "
        "Buổi chiều tối, dân địa phương tập trung đi bộ, tập thể dục, ngắm hoàng hôn trên sông. "
        "Có nhiều quán nước, hàng rong, và là nơi check-in đẹp."
    ),
    "area": "ben-tre",
    "placeId": "p-an-hoi",
    "coordinates": [10.2395, 106.3730],
    "source": {"title": "tổng hợp du lịch Bến Tre"},
    "attributes": {
        "best_time": "chiều tối, sáng sớm",
        "activity": "đi bộ, tập thể dục, ngắm hoàng hôn"
    },
    "confidence": 0.65,
    "created_at": NOW, "updatedAt": NOW
})

# ═══ LINK EXISTING ENTITIES ═══
print("\n═══ LINK EXISTING PLACE-TYPE ENTITIES ═══")

# Reclassify place-type entities that are actually restaurants/shops
RECLASSIFY = {
    "banh-mi-co-lan-duong-hung-vuong-ben-tre": ("dish", "p-an-hoi"),
    "vuon-am-thuc-truc-giang-ben-tre": ("attraction", "p-an-hoi"),
    "nha-hang-noi-ttc-ben-tre-ben-tre": ("dish", "p-ben-tre"),
    "nha-hang-ham-luong-ben-tre": ("dish", "p-ben-tre"),
}
for eid, (new_type, pid) in RECLASSIFY.items():
    e = by_id.get(eid)
    if e and e.get("type") == "place":
        old_type = e["type"]
        e["type"] = new_type
        e["placeId"] = pid
        if not e.get("area"):
            e["area"] = "ben-tre"
        print(f"  RECLASSIFY: {e['name']}: {old_type} → {new_type}, placeId={pid}")

# ═══ RELATIONSHIPS ═══
print("\n═══ RELATIONSHIPS ═══")

# All new An Hội dishes → p-an-hoi
anhoi_dishes = ["bi-bun-di-hai-thoi-ben-tre", "banh-xeo-nguyen-hue-ben-tre",
                "bun-bo-hue-chi-hang-ben-tre", "lo-banh-mi-tan-thanh-ben-tre",
                "banh-canh-bot-xat-cho-ben-tre"]
for did in anhoi_dishes:
    add_rel(did, "p-an-hoi", "produced_in")
    # Link to Chợ Bến Tre (nearby)
    add_rel(did, "cho-dem-ben-tre", "associated_with")
    # Link to Công viên An Hội
    add_rel(did, "cong-vien-an-hoi", "associated_with")

# TP BT dishes → p-ben-tre
bt_dishes = ["lau-mam-truc-giang-ben-tre", "hu-tieu-pate-ben-tre", "bun-rieu-tu-dien-ben-tre"]
for did in bt_dishes:
    add_rel(did, "p-ben-tre", "produced_in")

# Homestays → nearby attractions
bt_homestays = ["ba-danh-homestay-ben-tre", "hoa-dua-homestay-ben-tre",
                "nhon-thanh-homestay-ben-tre", "duyen-que-homestay-ben-tre",
                "nha-mo-homestay-ben-tre", "nguyet-que-homestay-ben-tre"]
for hid in bt_homestays:
    add_rel(hid, "p-ben-tre", "produced_in")
    add_rel(hid, "ho-truc-giang", "associated_with")
    add_rel(hid, "cong-vien-an-hoi", "associated_with")

# New attractions
add_rel("cocofarm-store-ben-tre", "p-ben-tre", "produced_in")
add_rel("bo-ke-song-ben-tre", "p-an-hoi", "produced_in")
add_rel("bo-ke-song-ben-tre", "cong-vien-an-hoi", "related_to")
add_rel("bo-ke-song-ben-tre", "cho-dem-ben-tre", "related_to")

# Cross-link dishes
for d1 in anhoi_dishes:
    for d2 in anhoi_dishes:
        if d1 < d2:
            add_rel(d1, d2, "related_to")

# ═══ SUMMARY ═══
print(f"\n{'═'*60}")
new_count = sum(1 for e in data["entities"] if e.get("created_at") == NOW)
new_rel_count = len(data["relationships"]) - len(rels)
anhoi_total = sum(1 for e in data["entities"] if e.get("placeId") == "p-an-hoi")
print(f"Added: {new_count} new entities, {new_rel_count} new rels")
print(f"P. An Hội total entities: {anhoi_total}")

# Dedup
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

with DATA.open("w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=None, separators=(",", ":"))
print(f"\n✅ Saved: {len(data['entities'])} entities, {len(data['relationships'])} rels")
