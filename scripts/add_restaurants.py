import json, re, unicodedata, sys

def slugify(text):
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')

raw = [
  {'name': 'Quán Bà Năm', 'specialty': 'Bún nước lèo, hủ tiếu Nam Vang', 'address': 'Chợ Vĩnh Long, TP. Vĩnh Long', 'price_range': '25.000 - 50.000 VNĐ/người', 'open_hours': '05:00 - 11:00', 'best_dish': 'Bún nước lèo tôm cua', 'rating_note': 'Quán lâu đời, nước lèo đậm đà từ tôm tươi và mắm bò hóc, rất đông khách buổi sáng', '_stream': 'restaurant', '_type': 'place', '_category': 'restaurant', '_province': 'Vĩnh Long', '_area': 'vinh-long'},
  {'name': 'Nhà hàng Phương Nam', 'specialty': 'Lẩu mắm miền Tây, cá lóc nướng trui', 'address': 'Đường 1/5, TP. Vĩnh Long', 'price_range': '150.000 - 350.000 VNĐ/người', 'open_hours': '10:00 - 22:00', 'best_dish': 'Lẩu mắm cá linh bông súng', 'rating_note': 'Không gian rộng rãi, phục vụ đặc sản miền Tây đúng điệu, phù hợp nhóm đông', '_stream': 'restaurant', '_type': 'place', '_category': 'restaurant', '_province': 'Vĩnh Long', '_area': 'vinh-long'},
  {'name': 'Quán Cơm Tấm Bà Bảy', 'specialty': 'Cơm tấm sườn bì chả', 'address': 'Đường Hoàng Thái Hiếu, TP. Vĩnh Long', 'price_range': '30.000 - 60.000 VNĐ/người', 'open_hours': '06:00 - 14:00', 'best_dish': 'Cơm tấm sườn nướng than hoa', 'rating_note': 'Sườn nướng thơm, cơm tấm dẻo, là điểm ăn sáng quen thuộc của người Vĩnh Long', '_stream': 'restaurant', '_type': 'place', '_category': 'restaurant', '_province': 'Vĩnh Long', '_area': 'vinh-long'},
  {'name': 'Nhà hàng Sông Tiền', 'specialty': 'Cá tai tượng chiên xù, cá bông lau hấp bia', 'address': 'Bờ sông Cổ Chiên, TP. Vĩnh Long', 'price_range': '200.000 - 500.000 VNĐ/người', 'open_hours': '10:30 - 22:00', 'best_dish': 'Cá tai tượng chiên xù cuốn bánh tráng', 'rating_note': 'View sông tuyệt đẹp, đặc sản cá đồng miền Tây, nổi tiếng với khách du lịch', '_stream': 'restaurant', '_type': 'place', '_category': 'restaurant', '_province': 'Vĩnh Long', '_area': 'vinh-long'},
  {'name': 'Quán Bánh Mì Thịt Nướng Tư Hùng', 'specialty': 'Bánh mì thịt nướng đặc sản Vĩnh Long', 'address': 'Chợ đêm Vĩnh Long, TP. Vĩnh Long', 'price_range': '20.000 - 35.000 VNĐ/người', 'open_hours': '15:00 - 22:00', 'best_dish': 'Bánh mì thịt nướng than hoa', 'rating_note': 'Thịt nướng thơm lừng, bánh mì giòn, là món ăn vặt nổi tiếng nhất chợ đêm VL', '_stream': 'restaurant', '_type': 'place', '_category': 'restaurant', '_province': 'Vĩnh Long', '_area': 'vinh-long'},
  {'name': 'Quán Hủ Tiếu Mỹ Tho Út Tiền', 'specialty': 'Hủ tiếu Mỹ Tho, hủ tiếu Nam Vang', 'address': 'Đường Trưng Nữ Vương, TP. Vĩnh Long', 'price_range': '30.000 - 55.000 VNĐ/người', 'open_hours': '05:30 - 12:00', 'best_dish': 'Hủ tiếu khô tôm thịt', 'rating_note': 'Nước lèo trong, ngọt tự nhiên từ xương hầm, sợi hủ tiếu dai ngon', '_stream': 'restaurant', '_type': 'place', '_category': 'restaurant', '_province': 'Vĩnh Long', '_area': 'vinh-long'},
  {'name': 'Quán Chè Bà Tám', 'specialty': 'Chè đậu, chè trôi nước, bánh lọt', 'address': 'Gần chợ Vĩnh Long, TP. Vĩnh Long', 'price_range': '10.000 - 25.000 VNĐ/người', 'open_hours': '14:00 - 21:30', 'best_dish': 'Chè bà ba (đậu xanh, khoai, chuối nước cốt dừa)', 'rating_note': 'Quán chè truyền thống lâu đời, nước cốt dừa béo thơm, giải nhiệt tuyệt vời', '_stream': 'restaurant', '_type': 'place', '_category': 'restaurant', '_province': 'Vĩnh Long', '_area': 'vinh-long'},
  {'name': 'Nhà hàng Mekong', 'specialty': 'Đặc sản sông nước, lẩu cá kèo bông điên điển', 'address': 'Khách sạn Mekong, đường 1/5, TP. Vĩnh Long', 'price_range': '200.000 - 450.000 VNĐ/người', 'open_hours': '06:30 - 22:00', 'best_dish': 'Lẩu cá kèo bông điên điển', 'rating_note': 'Nhà hàng cao cấp nhất VL, phục vụ cả buffet sáng, thích hợp tiếp khách', '_stream': 'restaurant', '_type': 'place', '_category': 'restaurant', '_province': 'Vĩnh Long', '_area': 'vinh-long'},
  {'name': 'Quán Bún Bò Bà Thúy', 'specialty': 'Bún bò Huế, bún riêu cua', 'address': 'Đường Lê Thái Tổ, TP. Vĩnh Long', 'price_range': '30.000 - 50.000 VNĐ/người', 'open_hours': '05:30 - 11:30', 'best_dish': 'Bún bò giò heo sả ớt', 'rating_note': 'Nước dùng đậm đà, giò heo mềm, ớt sa tế thơm, đông khách từ sáng sớm', '_stream': 'restaurant', '_type': 'place', '_category': 'restaurant', '_province': 'Vĩnh Long', '_area': 'vinh-long'},
  {'name': 'Quán Cháo Lòng Anh Hai', 'specialty': 'Cháo lòng, cháo cá lóc', 'address': 'Chợ Cái Vồn, thị xã Bình Minh, Vĩnh Long', 'price_range': '25.000 - 45.000 VNĐ/người', 'open_hours': '05:00 - 11:00', 'best_dish': 'Cháo lòng huyết dồi', 'rating_note': 'Nổi tiếng khu Cái Vồn, lòng tươi sạch, cháo sánh mịn, người địa phương ưa chuộng', '_stream': 'restaurant', '_type': 'place', '_category': 'restaurant', '_province': 'Vĩnh Long', '_area': 'vinh-long'},
  {'name': 'Quán Bánh Xèo Bà Sáu', 'specialty': 'Bánh xèo miền Tây, bánh khọt', 'address': 'Huyện Tam Bình, Vĩnh Long', 'price_range': '40.000 - 80.000 VNĐ/người', 'open_hours': '10:00 - 20:00', 'best_dish': 'Bánh xèo tôm thịt giá đỗ', 'rating_note': 'Bánh xèo giòn tan, nhân tươi ngon, cuốn rau sống chấm mắm chua ngọt đúng điệu Nam Bộ', '_stream': 'restaurant', '_type': 'place', '_category': 'restaurant', '_province': 'Vĩnh Long', '_area': 'vinh-long'},
  {'name': 'Quán Gà Hấp Muối Ông Ba', 'specialty': 'Gà hấp muối sả, vịt nấu chao', 'address': 'Đường Trần Phú, TP. Vĩnh Long', 'price_range': '80.000 - 180.000 VNĐ/người', 'open_hours': '10:00 - 21:00', 'best_dish': 'Gà ta hấp muối sả tắc', 'rating_note': 'Gà ta thả vườn, hấp chín tới, da giòn thịt ngọt, chấm muối tiêu chanh tuyệt hảo', '_stream': 'restaurant', '_type': 'place', '_category': 'restaurant', '_province': 'Vĩnh Long', '_area': 'vinh-long'},
  {'name': 'Quán Nem Nướng Thanh Xuân', 'specialty': 'Nem nướng Vĩnh Long, bì cuốn', 'address': 'Đường Nguyễn Huệ, TP. Vĩnh Long', 'price_range': '50.000 - 100.000 VNĐ/người', 'open_hours': '09:00 - 21:00', 'best_dish': 'Nem nướng cuốn bánh tráng rau sống', 'rating_note': 'Nem nướng thơm, chấm mắm nem tỏi ớt đặc biệt, là món ăn vặt đặc trưng của người Vĩnh Long', '_stream': 'restaurant', '_type': 'place', '_category': 'restaurant', '_province': 'Vĩnh Long', '_area': 'vinh-long'},
  {'name': 'Quán Cơm Niêu Đất Cô Năm', 'specialty': 'Cơm niêu đất, cá kho tộ', 'address': 'Huyện Long Hồ, Vĩnh Long', 'price_range': '60.000 - 120.000 VNĐ/người', 'open_hours': '10:00 - 20:00', 'best_dish': 'Cá kho tộ với cơm niêu đất', 'rating_note': 'Cơm niêu đất có lớp cháy thơm, cá kho tộ đậm vị, cách nấu truyền thống miền Tây', '_stream': 'restaurant', '_type': 'place', '_category': 'restaurant', '_province': 'Vĩnh Long', '_area': 'vinh-long'},
  {'name': 'Quán Dừa Bến Tre', 'specialty': 'Cơm tấm, các món từ dừa', 'address': 'Đường Nguyễn Đình Chiểu, TP. Bến Tre', 'price_range': '50.000 - 120.000', 'open_hours': '06:00 - 21:00', 'best_dish': 'Cơm tấm sườn bì chả', 'rating_note': 'Quán lâu đời, nổi tiếng với các món ăn đậm chất miền Tây, giá bình dân', '_stream': 'restaurant', '_type': 'place', '_category': 'restaurant', '_province': 'Bến Tre', '_area': 'ben-tre'},
  {'name': 'Nhà hàng Sông Hàn', 'specialty': 'Hải sản, lẩu mắm', 'address': 'Bến Tre', 'price_range': '150.000 - 400.000', 'open_hours': '10:00 - 22:00', 'best_dish': 'Lẩu mắm miền Tây', 'rating_note': 'View sông đẹp, hải sản tươi sống, phù hợp nhóm đông', '_stream': 'restaurant', '_type': 'place', '_category': 'restaurant', '_province': 'Bến Tre', '_area': 'ben-tre'},
  {'name': 'Quán Bánh Mì Bà Hoa', 'specialty': 'Bánh mì thịt nướng', 'address': 'Trung tâm TP. Bến Tre', 'price_range': '15.000 - 30.000', 'open_hours': '05:30 - 11:00', 'best_dish': 'Bánh mì thịt nướng mỡ hành', 'rating_note': 'Quán sáng nổi tiếng, khách xếp hàng mỗi sáng, giá rẻ', '_stream': 'restaurant', '_type': 'place', '_category': 'restaurant', '_province': 'Bến Tre', '_area': 'ben-tre'},
  {'name': 'Nhà hàng Bến Tre Garden', 'specialty': 'Đặc sản miền Tây, tiệc cưới', 'address': 'TP. Bến Tre', 'price_range': '200.000 - 500.000', 'open_hours': '10:00 - 22:00', 'best_dish': 'Cá lóc nướng trui cuốn bánh tráng', 'rating_note': 'Không gian vườn dừa, thích hợp đặt tiệc, đặc sản địa phương phong phú', '_stream': 'restaurant', '_type': 'place', '_category': 'restaurant', '_province': 'Bến Tre', '_area': 'ben-tre'},
  {'name': 'Quán Hủ Tiếu Nam Vang Cô Tư', 'specialty': 'Hủ tiếu Nam Vang', 'address': 'TP. Bến Tre', 'price_range': '30.000 - 60.000', 'open_hours': '05:00 - 14:00', 'best_dish': 'Hủ tiếu khô Nam Vang', 'rating_note': 'Quán bình dân quen thuộc, nước dùng ngọt thanh, phục vụ nhanh', '_stream': 'restaurant', '_type': 'place', '_category': 'restaurant', '_province': 'Bến Tre', '_area': 'ben-tre'},
  {'name': 'Nhà hàng Lửa Hồng', 'specialty': 'Lẩu, nướng đặc sản', 'address': 'TP. Bến Tre', 'price_range': '200.000 - 600.000', 'open_hours': '11:00 - 23:00', 'best_dish': 'Lẩu cá kèo bông súng', 'rating_note': 'Nổi tiếng với lẩu đặc sản đồng bằng, đông khách cuối tuần', '_stream': 'restaurant', '_type': 'place', '_category': 'restaurant', '_province': 'Bến Tre', '_area': 'ben-tre'},
]

data = json.load(open('C:/Code/vinhlong360/web/data.json', 'r', encoding='utf-8-sig'))
entities = data['entities']
existing_ids = set(e.get('id') for e in entities)
existing_names = set(e.get('name') for e in entities)

def make_summary(item):
    parts = []
    parts.append(item['name'])
    if item.get('specialty'):
        parts.append('chuyen ' + item['specialty'])
    if item.get('address'):
        parts.append('tai ' + item['address'])
    if item.get('open_hours'):
        parts.append('mo cua ' + item['open_hours'])
    if item.get('price_range'):
        parts.append('gia ' + item['price_range'])
    if item.get('best_dish'):
        parts.append('mon noi bat: ' + item['best_dish'])
    if item.get('rating_note'):
        parts.append(item['rating_note'])
    return '. '.join(parts) + '.'

added = 0
skipped = 0
for item in raw:
    entity_id = slugify(item['name']) + '-' + item['_area']
    if entity_id in existing_ids or item['name'] in existing_names:
        skipped += 1
        continue

    attrs = {k: v for k, v in item.items() if not k.startswith('_') and k != 'name'}
    attrs['province_old'] = item['_province']
    attrs['area'] = item['_area']
    attrs['category'] = item['_category']

    entity = {
        'id': entity_id,
        'type': item['_type'],
        'name': item['name'],
        'summary': make_summary(item),
        'source': 'curated',
        'status': 'provisional',
        'verified': False,
        'confidence': 0.7,
        'updatedAt': '2026-06-11T00:00:00Z',
        'coords': None,
        'attributes': attrs
    }
    entities.append(entity)
    existing_ids.add(entity_id)
    existing_names.add(item['name'])
    added += 1

data['entities'] = entities
out = json.dumps(data, ensure_ascii=False, indent=2)
with open('C:/Code/vinhlong360/web/data.json', 'w', encoding='utf-8') as f:
    f.write(out)

print(f'Added: {added}, Skipped (dups): {skipped}, Total entities: {len(entities)}')
