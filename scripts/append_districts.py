import sys, re, json
sys.stdout.reconfigure(encoding="utf-8")

VN_MAP = {
    "à":"a","á":"a","ả":"a","ã":"a","ạ":"a",
    "à":"a","á":"a","ả":"a","ã":"a","ạ":"a",
    "ă":"a","ắ":"a","ằ":"a","ẳ":"a","ẵ":"a","ặ":"a",
    "â":"a","ấ":"a","ầ":"a","ẩ":"a","ẫ":"a","ậ":"a",
    "è":"e","é":"e","ẻ":"e","ẽ":"e","ẹ":"e",
    "ê":"e","ế":"e","ề":"e","ể":"e","ễ":"e","ệ":"e",
    "ì":"i","í":"i","ỉ":"i","ĩ":"i","ị":"i",
    "ò":"o","ó":"o","ỏ":"o","õ":"o","ọ":"o",
    "ô":"o","ố":"o","ồ":"o","ổ":"o","ỗ":"o","ộ":"o",
    "ơ":"o","ớ":"o","ờ":"o","ở":"o","ỡ":"o","ợ":"o",
    "ù":"u","ú":"u","ủ":"u","ũ":"u","ụ":"u",
    "ư":"u","ứ":"u","ừ":"u","ử":"u","ữ":"u","ự":"u",
    "ỳ":"y","ý":"y","ỷ":"y","ỹ":"y","ỵ":"y",
    "đ":"d",
    "À":"a","Á":"a","Ả":"a","Ã":"a","Ạ":"a",
    "Ă":"a","Ắ":"a","Ằ":"a","Ẳ":"a","Ẵ":"a","Ặ":"a",
    "Â":"a","Ấ":"a","Ầ":"a","Ẩ":"a","Ẫ":"a","Ậ":"a",
    "È":"e","É":"e","Ẻ":"e","Ẽ":"e","Ẹ":"e",
    "Ê":"e","Ế":"e","Ề":"e","Ể":"e","Ễ":"e","Ệ":"e",
    "Ì":"i","Í":"i","Ỉ":"i","Ĩ":"i","Ị":"i",
    "Ò":"o","Ó":"o","Ỏ":"o","Õ":"o","Ọ":"o",
    "Ô":"o","Ố":"o","Ồ":"o","Ổ":"o","Ỗ":"o","Ộ":"o",
    "Ơ":"o","Ớ":"o","Ờ":"o","Ở":"o","Ỡ":"o","Ợ":"o",
    "Ù":"u","Ú":"u","Ủ":"u","Ũ":"u","Ụ":"u",
    "Ư":"u","Ứ":"u","Ừ":"u","Ử":"u","Ữ":"u","Ự":"u",
    "Ỳ":"y","Ý":"y","Ỷ":"y","Ỹ":"y","Ỵ":"y",
    "Đ":"d",
}

def slugify(text):
    result = ""
    for c in text:
        result += VN_MAP.get(c, c)
    result = result.lower()
    result = re.sub(r"[^a-z0-9]+", "-", result)
    result = result.strip("-")
    return result

RAW = [
  {
    "name": "Thành phố Vĩnh Long",
    "admin_type": "thành phố",
    "population": 171000,
    "area_km2": 47.9,
    "known_for": "Trung tâm hành chính tỉnh lỵ, cảng sông Cổ Chiên, chợ nổi Vĩnh Long, di tích văn hóa Khmer và Pháp",
    "top_attraction": "Bến Ninh Kiều nhỏ (bờ kè sông Long Hồ) và tour miệt vườn cù lao An Bình",
    "specialty_product": "Bánh tráng nem Vĩnh Long, hủ tiếu Vĩnh Long",
    "distance_from_capital": 0,
    "_stream": "districts",
    "_type": "place",
    "_category": "district",
    "_province": "Vĩnh Long",
    "_area": "vinh-long"
  },
  {
    "name": "Huyện Long Hồ",
    "admin_type": "huyện",
    "population": 155000,
    "area_km2": 190.5,
    "known_for": "Vườn cây ăn trái miệt vườn, cù lao sông Tiền, homestay sinh thái, đi thuyền chèo kênh rạch",
    "top_attraction": "Cù lao An Bình (làng du lịch sinh thái sông nước nổi tiếng nhất Vĩnh Long)",
    "specialty_product": "Chôm chôm, nhãn, sầu riêng cù lao An Bình",
    "distance_from_capital": 7,
    "_stream": "districts",
    "_type": "place",
    "_category": "district",
    "_province": "Vĩnh Long",
    "_area": "vinh-long"
  },
  {
    "name": "Huyện Mang Thít",
    "admin_type": "huyện",
    "population": 120000,
    "area_km2": 161.6,
    "known_for": "Vương quốc lò gạch gốm đỏ (hàng trăm lò gạch thủ công ven sông Mang Thít), làng nghề truyền thống",
    "top_attraction": "Làng lò gạch Mang Thít - di sản công nghiệp lò nung gạch truyền thống độc đáo nhất ĐBSCL",
    "specialty_product": "Gạch thẻ, gốm đỏ Mang Thít",
    "distance_from_capital": 15,
    "_stream": "districts",
    "_type": "place",
    "_category": "district",
    "_province": "Vĩnh Long",
    "_area": "vinh-long"
  },
  {
    "name": "Huyện Vũng Liêm",
    "admin_type": "huyện",
    "population": 175000,
    "area_km2": 295.5,
    "known_for": "Đình thần Tân Giai, chùa cổ Phật giáo Nam tông Khmer, vùng lúa và dừa, kênh rạch chằng chịt",
    "top_attraction": "Chùa Phước Hậu (trung tâm Phật học Nam tông lớn của miền Tây)",
    "specialty_product": "Dừa uống, mắm cá lóc Vũng Liêm",
    "distance_from_capital": 35,
    "_stream": "districts",
    "_type": "place",
    "_category": "district",
    "_province": "Vĩnh Long",
    "_area": "vinh-long"
  },
  {
    "name": "Huyện Trà Ôn",
    "admin_type": "huyện",
    "population": 162000,
    "area_km2": 247.7,
    "known_for": "Chợ nổi Trà Ôn (một trong những chợ nổi lớn còn hoạt động ở ĐBSCL), vườn cây ăn trái, đờn ca tài tử",
    "top_attraction": "Chợ nổi Trà Ôn trên sông Hậu",
    "specialty_product": "Bưởi Năm Roi Trà Ôn (bưởi nổi tiếng nhất Việt Nam xuất khẩu)",
    "distance_from_capital": 55,
    "_stream": "districts",
    "_type": "place",
    "_category": "district",
    "_province": "Vĩnh Long",
    "_area": "vinh-long"
  },
  {
    "name": "Huyện Bình Tân",
    "admin_type": "huyện",
    "population": 100000,
    "area_km2": 158.2,
    "known_for": "Vùng khoai lang tím Bình Tân nổi tiếng nhất Việt Nam, nông nghiệp OCOP xuất khẩu",
    "top_attraction": "Cánh đồng khoai lang và mô hình nông nghiệp OCOP Bình Tân",
    "specialty_product": "Khoai lang tím Bình Tân (OCOP 4 sao, xuất khẩu Nhật, Hàn)",
    "distance_from_capital": 40,
    "_stream": "districts",
    "_type": "place",
    "_category": "district",
    "_province": "Vĩnh Long",
    "_area": "vinh-long"
  },
  {
    "name": "Thị xã Bình Minh",
    "admin_type": "thị xã",
    "population": 95000,
    "area_km2": 94.5,
    "known_for": "Cầu Mỹ Thuận 2, cửa ngõ vùng ĐBSCL phía tây, vùng bưởi Năm Roi gốc, thương mại dịch vụ",
    "top_attraction": "Cầu Mỹ Thuận và cầu Mỹ Thuận 2 - biểu tượng kết nối ĐBSCL",
    "specialty_product": "Bưởi Năm Roi Bình Minh (vùng trồng gốc nguyên bản)",
    "distance_from_capital": 45,
    "_stream": "districts",
    "_type": "place",
    "_category": "district",
    "_province": "Vĩnh Long",
    "_area": "vinh-long"
  },
  {
    "name": "Thành phố Bến Tre",
    "admin_type": "thành phố",
    "population": 180000,
    "area_km2": 67.61,
    "known_for": "Trung tâm hành chính tỉnh Bến Tre, cầu Rạch Miễu nối Tiền Giang, chợ Bến Tre, dừa sáp",
    "top_attraction": "Cồn Phụng (Đạo Dừa) - di tích lịch sử trên cồn giữa sông Tiền",
    "specialty_product": "Kữo dừa Bến Tre, mứt dừa",
    "distance_from_capital": 0,
    "_stream": "districts",
    "_type": "place",
    "_category": "district",
    "_province": "Bến Tre",
    "_area": "ben-tre"
  },
  {
    "name": "Huyện Châu Thành",
    "admin_type": "huyện",
    "population": 175000,
    "area_km2": 231.26,
    "known_for": "Vườn trái cây miệt vườn, du lịch homestay sông nước, cây cầu Hàm Luông",
    "top_attraction": "Cồn Tiên - cồn sông Hàm Luông với vườn trái cây và homestay sinh thái",
    "specialty_product": "Dừa xiêm xanh, bưới da xanh Châu Thành",
    "distance_from_capital": 15,
    "_stream": "districts",
    "_type": "place",
    "_category": "district",
    "_province": "Bến Tre",
    "_area": "ben-tre"
  },
  {
    "name": "Huyện Chợ Lách",
    "admin_type": "huyện",
    "population": 130000,
    "area_km2": 186.7,
    "known_for": "Vương quốc trái cây và hoa kiếng miền Tây, làng nghề ghép cây giống, Làng hoa Sa Đéc của Bến Tre",
    "top_attraction": "Làng hoa kiếng Cái Mơn - làng nghề trồng hoa cây cảnh nổi tiếng nhất Bến Tre",
    "specialty_product": "Chôm chôm, sầu riêng, bưới da xanh, cây giống hoa kiếng Cái Mơn",
    "distance_from_capital": 45,
    "_stream": "districts",
    "_type": "place",
    "_category": "district",
    "_province": "Bến Tre",
    "_area": "ben-tre"
  },
  {
    "name": "Huyện Mỏ Cày Nam",
    "admin_type": "huyện",
    "population": 200000,
    "area_km2": 247.8,
    "known_for": "Quê hương đồng khởi Bến Tre, di tích lịch sử cách mạng, vườn dừa bạt ngàn",
    "top_attraction": "Di tích Đồng Khởi Bến Tre tại xã Định Thủy - nơi phát súng khởi nghĩa 1960",
    "specialty_product": "Dừa khô, cơm dừa nạo sấy, mật hoa dừa",
    "distance_from_capital": 30,
    "_stream": "districts",
    "_type": "place",
    "_category": "district",
    "_province": "Bến Tre",
    "_area": "ben-tre"
  },
  {
    "name": "Huyện Mỏ Cày Bắc",
    "admin_type": "huyện",
    "population": 155000,
    "area_km2": 217.4,
    "known_for": "Vườn cây ăn trái, sông Hàm Luông, di tích lịch sử kháng chiến",
    "top_attraction": "Cù lao Minh - vùng cồn đất phù sa màu mỡ với vườn cây ăn trái xanh tốt",
    "specialty_product": "Sầu riêng Mỏ Cày, ca cao Bến Tre",
    "distance_from_capital": 25,
    "_stream": "districts",
    "_type": "place",
    "_category": "district",
    "_province": "Bến Tre",
    "_area": "ben-tre"
  },
  {
    "name": "Huyện Giồng Trôm",
    "admin_type": "huyện",
    "population": 210000,
    "area_km2": 313.3,
    "known_for": "Huyện đông dân nhất Bến Tre, vườn dừa, sông Ba Lai, tượng đài Đồng Khởi",
    "top_attraction": "Khu tưởng niệm Nữ tướng Nguyễn Thị Định tại xã Lương Hòa",
    "specialty_product": "Dừa sáp Giồng Trôm - dừa đặc sản hiếm có cùi dày giàu dầu",
    "distance_from_capital": 18,
    "_stream": "districts",
    "_type": "place",
    "_category": "district",
    "_province": "Bến Tre",
    "_area": "ben-tre"
  },
  {
    "name": "Huyện Bình Đại",
    "admin_type": "huyện",
    "population": 145000,
    "area_km2": 425.3,
    "known_for": "Cửa biển Đại, nuôi nghêu và thủy sản biển, rừng phòng hộ ven biển",
    "top_attraction": "Biển Thừa Đức - bãi biển hoang sơ và khu nuôi nghêu ven biển duy nhất Bến Tre",
    "specialty_product": "Nghêu Bình Đại, tôm khô, mắm tôm chà Bình Đại",
    "distance_from_capital": 50,
    "_stream": "districts",
    "_type": "place",
    "_category": "district",
    "_province": "Bến Tre",
    "_area": "ben-tre"
  },
  {
    "name": "Huyện Ba Tri",
    "admin_type": "huyện",
    "population": 195000,
    "area_km2": 355,
    "known_for": "Quê hương nhà thơ Nguyễn Đình Chiểu, muối Ba Tri, biển Ba Tri",
    "top_attraction": "Mộ và khu tưởng niệm Nguyễn Đình Chiểu tại thị trấn Ba Tri",
    "specialty_product": "Muối Ba Tri, khô cá, bánh tráng Ba Tri",
    "distance_from_capital": 55,
    "_stream": "districts",
    "_type": "place",
    "_category": "district",
    "_province": "Bến Tre",
    "_area": "ben-tre"
  },
  {
    "name": "Huyện Thạnh Phú",
    "admin_type": "huyện",
    "population": 145000,
    "area_km2": 428.8,
    "known_for": "Biển Thạnh Phú, rừng ngập mặn, khu sinh thái biển, tôm cua biển",
    "top_attraction": "Khu du lịch sinh thái biển Thạnh Phú - rừng ngập mặn và bãi biển hoang sơ cửa Cổ Chiên",
    "specialty_product": "Tôm càng xanh Thạnh Phú, cua biển, sò huyết",
    "distance_from_capital": 70,
    "_stream": "districts",
    "_type": "place",
    "_category": "district",
    "_province": "Bến Tre",
    "_area": "ben-tre"
  },
  {
    "name": "Thành phố Trà Vinh",
    "admin_type": "thành phố",
    "population": 131000,
    "area_km2": 68,
    "known_for": "Trung tâm tỉnh lỵ, chùa Khmer cổ kính, kiến trúc Pháp-Khmer độc đáo",
    "top_attraction": "Chùa Âng (Angkor Reach Borey) - chùa Khmer cổ nhất tỉnh",
    "specialty_product": "Bánh tét lá cẩm, bánh ống lá dứa",
    "distance_from_capital": 0,
    "_stream": "districts",
    "_type": "place",
    "_category": "district",
    "_province": "Trà Vinh",
    "_area": "tra-vinh"
  },
  {
    "name": "Thị xã Duyên Hải",
    "admin_type": "thị xã",
    "population": 95000,
    "area_km2": 531,
    "known_for": "Vùng biển, nuôi tôm công nghiệp, khu công nghiệp điện lực Duyên Hải",
    "top_attraction": "Bãi biển Hiệp Thạnh - bãi biển duy nhất của tỉnh Trà Vinh",
    "specialty_product": "Tôm sú, cua biển, nghêu Trà Vinh",
    "distance_from_capital": 55,
    "_stream": "districts",
    "_type": "place",
    "_category": "district",
    "_province": "Trà Vinh",
    "_area": "tra-vinh"
  },
  {
    "name": "Huyện Càng Long",
    "admin_type": "huyện",
    "population": 170000,
    "area_km2": 308,
    "known_for": "Vùng trồng lúa, vườn cây ăn trái, làng nghề đan lát truyền thống",
    "top_attraction": "Vườn cây ăn trái Huyền Đức, chùa Long Phước",
    "specialty_product": "Bưới da xanh Càng Long, mật ong rừng",
    "distance_from_capital": 26,
    "_stream": "districts",
    "_type": "place",
    "_category": "district",
    "_province": "Trà Vinh",
    "_area": "tra-vinh"
  },
  {
    "name": "Huyện Cầu Kè",
    "admin_type": "huyện",
    "population": 130000,
    "area_km2": 245,
    "known_for": "Cộng đồng Khmer đông đảo, vườn dừa, chùa chiền Khmer cổ",
    "top_attraction": "Chùa Nôdol (chùa Hang) - kiến trúc Khmer đặc sắc",
    "specialty_product": "Dừa khô Cầu Kè, hủ tiếu Cầu Kè nổi tiếng khắp miền Tây",
    "distance_from_capital": 52,
    "_stream": "districts",
    "_type": "place",
    "_category": "district",
    "_province": "Trà Vinh",
    "_area": "tra-vinh"
  },
  {
    "name": "Huyện Tiểu Cần",
    "admin_type": "huyện",
    "population": 115000,
    "area_km2": 226,
    "known_for": "Đình làng cổ, lễ hội truyền thống người Kinh-Khmer, sản xuất lúa",
    "top_attraction": "Đình Tiểu Cần - di tích lịch sử văn hóa cấp tỉnh",
    "specialty_product": "Gạo nàng thơm Tiểu Cần, rượu nếp",
    "distance_from_capital": 45,
    "_stream": "districts",
    "_type": "place",
    "_category": "district",
    "_province": "Trà Vinh",
    "_area": "tra-vinh"
  },
  {
    "name": "Huyện Cầu Ngang",
    "admin_type": "huyện",
    "population": 155000,
    "area_km2": 308,
    "known_for": "Rừng phòng hộ ven biển, nuôi thủy sản nước lợ, lúa hai vụ",
    "top_attraction": "Khu bảo tồn thiên nhiên Bắc Cầu Ngang - rừng ngập mặn ven biển",
    "specialty_product": "Cá bống kèo, tôm đất Cầu Ngang",
    "distance_from_capital": 35,
    "_stream": "districts",
    "_type": "place",
    "_category": "district",
    "_province": "Trà Vinh",
    "_area": "tra-vinh"
  },
  {
    "name": "Huyện Trà Cú",
    "admin_type": "huyện",
    "population": 185000,
    "area_km2": 367,
    "known_for": "Huyện Khmer đông nhất tỉnh, chùa Khmer cổ Hang, lễ hội Ok Om Bok",
    "top_attraction": "Chùa Hang (Kompong Chrây) - chùa cổ trong hang đá Khmer độc đáo",
    "specialty_product": "Mắm bồ hóc Trà Cú, dưa hấu Trà Cú",
    "distance_from_capital": 42,
    "_stream": "districts",
    "_type": "place",
    "_category": "district",
    "_province": "Trà Vinh",
    "_area": "tra-vinh"
  },
  {
    "name": "Huyện Duyên Hải",
    "admin_type": "huyện",
    "population": 80000,
    "area_km2": 427,
    "known_for": "Rừng ngập mặn Cồn Cò, đánh bắt thủy sản, cảnh quan cửa sông biển",
    "top_attraction": "Cồn Cò - cù lao giữa sông với rừng dừa nước và sinh thái cửa sông",
    "specialty_product": "Cua biển, mực một nắng Duyên Hải",
    "distance_from_capital": 60,
    "_stream": "districts",
    "_type": "place",
    "_category": "district",
    "_province": "Trà Vinh",
    "_area": "tra-vinh"
  }
]

def make_summary(r):
    parts = [r["name"] + " (" + r["admin_type"] + ")."]
    parts.append("Nổi bật: " + r["known_for"] + ".")
    parts.append("Điểm tham quan: " + r["top_attraction"] + ".")
    parts.append("Đặc sản: " + r["specialty_product"] + ".")
    if r["distance_from_capital"] > 0:
        parts.append(f"Cách trung tâm tỉnh {r['distance_from_capital']} km.")
    return " ".join(parts)

def make_entity(r):
    area = r["_area"]
    entity_type = r["_type"]
    name = r["name"]
    entity_id = slugify(name) + "-" + area

    summary = make_summary(r)

    attrs = {
        "admin_type": r["admin_type"],
        "population": r["population"],
        "area_km2": r["area_km2"],
        "known_for": r["known_for"],
        "top_attraction": r["top_attraction"],
        "specialty_product": r["specialty_product"],
        "distance_from_capital": r["distance_from_capital"],
        "province_old": r["_province"],
        "area": area,
        "category": r["_category"],
    }

    return {
        "id": entity_id,
        "type": entity_type,
        "name": name,
        "summary": summary,
        "source": "curated",
        "status": "provisional",
        "verified": False,
        "confidence": 0.7,
        "updatedAt": "2026-06-11T00:00:00Z",
        "coords": None,
        "attributes": attrs,
    }

# Build new entities - dedup within batch
new_entities = []
seen_ids = set()
seen_names = set()

for r in RAW:
    eid = slugify(r["name"]) + "-" + r["_area"]
    if eid in seen_ids or r["name"] in seen_names:
        print(f"SKIP BATCH DUP: {eid}")
        continue
    seen_ids.add(eid)
    seen_names.add(r["name"])
    new_entities.append(make_entity(r))

print(f"Entities built from batch: {len(new_entities)}")

# Read existing data and check for duplicates
with open("C:/Code/vinhlong360/web/data.json", "r", encoding="utf-8") as f:
    content = f.read()

existing_ids = set(re.findall(r'^\s*"id":\s*"([^"]+)"', content, re.MULTILINE))
existing_names = set(re.findall(r'^\s*"name":\s*"([^"]+)"', content, re.MULTILINE))

print(f"Existing IDs in file: {len(existing_ids)}")

to_append = []
skipped = []
for e in new_entities:
    if e["id"] in existing_ids:
        skipped.append(f"id-dup:{e['id']}")
    elif e["name"] in existing_names:
        skipped.append(f"name-dup:{e['name']}")
    else:
        to_append.append(e)

if skipped:
    print(f"Skipped (already exist): {skipped}")

print(f"Will append: {len(to_append)}")

if not to_append:
    print("Nothing to append.")
    sys.exit(0)

# Build the JSON strings for each new entity (indented 8 spaces to match file style)
new_json_items = ",\n        ".join(
    json.dumps(e, ensure_ascii=False, indent=8).replace("\n", "\n        ")
    for e in to_append
)

# The entities array in the file ends before "    ]"
# We need to find the closing bracket of the entities array
# File structure: { "entities": [ ... LAST_ENTITY ] }
# or { "entities": [ ... LAST_ENTITY ], "relations": [ ... ] }

# Strategy: find the last "        }" that closes an entity object, then insert after it
# The insertion point is: after the last entity object, before the array-closing "]"

# Find the last "        }" in the entities section
# Since entities is the first (and only?) top-level array, we look for
# the pattern:  \n        }\n    ]  (the last entity closing before array close)

# The file ends with ...}\n    ]\n} so entities array close is "    ]"
# Let's find the second-to-last "    ]" or the first one

# Check what comes after entities array
# Look for "    ]" patterns
bracket_positions = [m.start() for m in re.finditer(r'\n    \]', content)]
print(f"\nFound {len(bracket_positions)} '\\n    ]' positions in file")
for pos in bracket_positions[:3]:
    ctx = content[pos-30:pos+50]
    print(f"  pos {pos}: {repr(ctx)}")

# The entities array closing bracket is the first "    ]"
if bracket_positions:
    insert_before = bracket_positions[0]
    # The content before insert_before ends the last entity with "        }"
    # We need to add a comma after the last entity then add new entities
    # Check what is just before the closing bracket
    pre_close = content[insert_before-5:insert_before+5]
    print(f"\nContent around first bracket close: {repr(pre_close)}")

    # Build insertion: ,\n        {new entity 1},\n        {new entity 2},...
    insertion = ",\n        " + new_json_items

    # new content
    new_content = content[:insert_before] + insertion + content[insert_before:]

    with open("C:/Code/vinhlong360/web/data.json", "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"\nDone. Appended {len(to_append)} entities.")
    for e in to_append:
        print(f"  + {e['id']}")
else:
    print("No newline-based bracket found. File is likely minified (compact JSON).")
    # For minified file, find the entities array closing bracket
    # The file is: {"entities":[...LAST_ENTITY...]}
    # or {"entities":[...],"relations":[...]}
    # Strategy: find last "}" before "]}" or "]," that closes entities
    # The safest approach: find the last occurrence of "}]" or "}],"
    # that closes the entities array

    # Check file ending
    print(f"File ends with: {repr(content[-20:])}")

    # The entities array ends right before "]}" (if entities is last key)
    # or before "]," (if there are more keys after entities)
    # Find where entities array closes
    entities_start = content.index('"entities":[') + len('"entities":[')
    print(f"Entities array starts at position: {entities_start}")

    # Use regex to find the end of the entities array
    # Find "]" that is followed by either "}" or ","
    # But we need the one that closes the entities array specifically
    # Since entities is first, its closing ] is at the correct brace depth

    # Count brackets to find the matching ]
    depth = 0
    entities_close_pos = None
    for i in range(entities_start, len(content)):
        c = content[i]
        if c == '[' or c == '{':
            depth += 1
        elif c == ']' or c == '}':
            if c == ']' and depth == 0:
                entities_close_pos = i
                break
            depth -= 1

    if entities_close_pos is None:
        print("ERROR: Could not find entities array closing bracket via bracket counting")
        sys.exit(1)

    print(f"Entities array closes at position: {entities_close_pos}")
    print(f"Context: {repr(content[entities_close_pos-30:entities_close_pos+10])}")

    # Insert new entities before the closing bracket
    # Build compact JSON for each entity
    compact_items = ",".join(json.dumps(e, ensure_ascii=False, separators=(',', ':')) for e in to_append)
    insertion = "," + compact_items

    new_content = content[:entities_close_pos] + insertion + content[entities_close_pos:]

    with open("C:/Code/vinhlong360/web/data.json", "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"\nDone. Appended {len(to_append)} entities (compact format).")
    for e in to_append:
        print(f"  + {e['id']}")
