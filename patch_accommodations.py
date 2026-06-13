import json

patches = [
  {"id": "khach-san-anh-hong-mang-thit", "price_range": "150–300k/đêm", "accommodation_type": "Khách sạn 1 sao", "check_in": "14:00", "check_out": "12:00", "booking_note": "Liên hệ trực tiếp khách sạn tại Khóm 1, xã Cái Nhum, huyện Mang Thít (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "khach-san-nghia-hiep", "price_range": "150–300k/đêm", "accommodation_type": "Khách sạn 1 sao", "check_in": "14:00", "check_out": "12:00", "booking_note": "Liên hệ trực tiếp khách sạn tại Ấp Mỹ An, xã Bình Ninh, huyện Tam Bình (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "khach-san-khoi-hoa", "price_range": "300–600k/đêm", "accommodation_type": "Khách sạn 2 sao", "check_in": "14:00", "check_out": "12:00", "booking_note": "Liên hệ trực tiếp khách sạn tại ấp Đông Hậu, phường Bình Minh, TX Bình Minh (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "khach-san-duc-dao", "price_range": "150–300k/đêm", "accommodation_type": "Khách sạn 1 sao", "check_in": "14:00", "check_out": "12:00", "booking_note": "Liên hệ trực tiếp khách sạn tại Phường Bình Minh, TX Bình Minh (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "khach-san-tan-thanh-2", "price_range": "150–300k/đêm", "accommodation_type": "Khách sạn 1 sao", "check_in": "14:00", "check_out": "12:00", "booking_note": "Liên hệ trực tiếp khách sạn tại Phường Bình Minh, TX Bình Minh (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "khach-san-chieu-hung", "price_range": "150–300k/đêm", "accommodation_type": "Khách sạn 1 sao", "check_in": "14:00", "check_out": "12:00", "booking_note": "Liên hệ trực tiếp khách sạn tại 20A Gia Long, Khu I, xã Trà Ôn (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "khach-san-trung-tinh", "price_range": "150–300k/đêm", "accommodation_type": "Khách sạn 1 sao", "check_in": "14:00", "check_out": "12:00", "booking_note": "Liên hệ trực tiếp khách sạn tại 100A1 Thống chế điều bát, khu 3, xã Trà Ôn (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "khach-san-tan-thanh-6", "price_range": "150–300k/đêm", "accommodation_type": "Khách sạn 1 sao", "check_in": "14:00", "check_out": "12:00", "booking_note": "Liên hệ trực tiếp khách sạn tại 162 Nam Kỳ Khởi Nghĩa, xã Trung Thành (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "coco-riverside-lodge", "price_range": "800k–2tr/đêm", "accommodation_type": "Lodge/Resort boutique", "check_in": "14:00", "check_out": "12:00", "booking_note": "Đặt phòng qua website hoặc liên hệ lodge tại Ấp Phú Ân, xã Trung Nghĩa, huyện Trà Ôn (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "khach-san-bich-ngoan", "price_range": "100–200k/đêm", "accommodation_type": "Nhà nghỉ", "check_in": "14:00", "check_out": "12:00", "booking_note": "Liên hệ trực tiếp tại 17/22 đường 19/5, phường Trà Vinh, TP Trà Vinh (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "nha-khach-vinh-tra", "price_range": "100–200k/đêm", "accommodation_type": "Nhà nghỉ", "check_in": "14:00", "check_out": "12:00", "booking_note": "Liên hệ trực tiếp tại 4A Nguyễn Thị Minh Khai, phường Trà Vinh, TP Trà Vinh (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "khach-san-sanh-phuc", "price_range": "100–200k/đêm", "accommodation_type": "Nhà nghỉ", "check_in": "14:00", "check_out": "12:00", "booking_note": "Liên hệ trực tiếp tại 419 Đồng Khởi, phường Trà Vinh, TP Trà Vinh (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "khach-san-gia-hoa-ii", "price_range": "100–200k/đêm", "accommodation_type": "Nhà nghỉ", "check_in": "14:00", "check_out": "12:00", "booking_note": "Liên hệ trực tiếp tại 50 Lê Lợi, phường 2, TP Trà Vinh (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "hoan-my-homestay", "price_range": "400–800k/phòng/đêm", "accommodation_type": "Homestay", "check_in": "14:00", "check_out": "11:00", "booking_note": "Liên hệ trực tiếp chủ nhà tại Ấp Phú Hòa, Phường Long Đức, TP Trà Vinh (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "khach-san-hoan-my-2", "price_range": "100–200k/đêm", "accommodation_type": "Nhà nghỉ", "check_in": "14:00", "check_out": "12:00", "booking_note": "Liên hệ trực tiếp tại 132B Nguyễn Đáng, phường Nguyệt Hóa, TP Trà Vinh (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "khach-san-an-khang", "price_range": "100.000–200.000 VND/đêm", "accommodation_type": "Nhà nghỉ", "check_in": "14:00", "check_out": "12:00", "booking_note": "Liên hệ trực tiếp: 69 Võ Văn Kiệt, P. Nguyệt Hóa, TP Trà Vinh (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "khach-san-ngoc-quy", "price_range": "100.000–200.000 VND/đêm", "accommodation_type": "Nhà nghỉ", "check_in": "14:00", "check_out": "12:00", "booking_note": "Liên hệ trực tiếp: 105 Võ Nguyên Giáp, P. Nguyệt Hóa, TP Trà Vinh (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "khach-san-thanh-binh-i", "price_range": "100.000–200.000 VND/đêm", "accommodation_type": "Nhà nghỉ", "check_in": "14:00", "check_out": "12:00", "booking_note": "Liên hệ trực tiếp: 109 Võ Nguyên Giáp, P. Nguyệt Hóa, TP Trà Vinh (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "khach-san-thanh-binh-ii", "price_range": "100.000–200.000 VND/đêm", "accommodation_type": "Nhà nghỉ", "check_in": "14:00", "check_out": "12:00", "booking_note": "Liên hệ trực tiếp: 199 Võ Nguyên Giáp, P. Nguyệt Hóa, TP Trà Vinh (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "khach-san-hai-duong-i", "price_range": "100.000–200.000 VND/đêm", "accommodation_type": "Nhà nghỉ", "check_in": "14:00", "check_out": "12:00", "booking_note": "Liên hệ trực tiếp: 14 đường 2/9, P. Duyên Hải, TP Trà Vinh (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "khach-san-hai-duong-2", "price_range": "100.000–200.000 VND/đêm", "accommodation_type": "Nhà nghỉ", "check_in": "14:00", "check_out": "12:00", "booking_note": "Liên hệ trực tiếp: 140A QL53, P. Duyên Hải, TP Trà Vinh (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "khach-san-tuong-vy", "price_range": "100.000–200.000 VND/đêm", "accommodation_type": "Nhà nghỉ", "check_in": "14:00", "check_out": "12:00", "booking_note": "Liên hệ trực tiếp: 135 đường 3/2, P. Duyên Hải, TP Trà Vinh (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "farmstay-dat-cu-lao", "price_range": "400.000–800.000 VND/phòng/đêm", "accommodation_type": "Farmstay", "check_in": "14:00", "check_out": "11:00", "booking_note": "Liên hệ trực tiếp: Cảng Cá Láng Chim, P. Trường Long Hòa, TP Trà Vinh – có thể yêu cầu đặt cọc trước (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "le-ngan-homestay", "price_range": "200.000–400.000 VND/người hoặc 400.000–800.000 VND/phòng", "accommodation_type": "Homestay", "check_in": "14:00", "check_out": "11:00", "booking_note": "Liên hệ trực tiếp: Ấp Lê Văn Quới, xã Tập Ngãi, huyện Tiểu Cần, Trà Vinh (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "ks-nha-co-cau-ke", "price_range": "100.000–200.000 VND/đêm", "accommodation_type": "Nhà nghỉ (nhà cổ)", "check_in": "14:00", "check_out": "12:00", "booking_note": "Liên hệ trực tiếp: Khóm 2, xã Cầu Kè, huyện Cầu Kè, Trà Vinh – trải nghiệm nhà cổ đặc trưng (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "suonsia-homestay", "price_range": "200.000–400.000 VND/người hoặc 400.000–800.000 VND/phòng", "accommodation_type": "Homestay", "check_in": "14:00", "check_out": "11:00", "booking_note": "Liên hệ trực tiếp: 22/2 ấp Bà My, xã Cầu Kè, huyện Cầu Kè, Trà Vinh (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "nh-ks-sy-dien", "price_range": "100.000–200.000 VND/đêm", "accommodation_type": "Nhà nghỉ", "check_in": "14:00", "check_out": "12:00", "booking_note": "Liên hệ trực tiếp: 19A Hương Lộ 32, ấp Bà My, xã Cầu Kè, huyện Cầu Kè, Trà Vinh (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "mekong-garden-homestay", "price_range": "200.000–400.000 VND/người hoặc 400.000–800.000 VND/phòng", "accommodation_type": "Homestay", "check_in": "14:00", "check_out": "11:00", "booking_note": "Liên hệ trực tiếp: Ấp Đon, xã Nhị Long, huyện Cầu Kè, Trà Vinh – gần vườn cây ăn trái (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "khach-san-huynh-thao", "price_range": "100.000–200.000 VND/đêm", "accommodation_type": "Nhà nghỉ", "check_in": "14:00", "check_out": "12:00", "booking_note": "Liên hệ trực tiếp: 69c Đồng Văn Cống, P. Bến Tre, TP Bến Tre (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "khach-san-dai-an", "price_range": "100.000–200.000 VND/đêm", "accommodation_type": "Nhà nghỉ", "check_in": "14:00", "check_out": "12:00", "booking_note": "Liên hệ trực tiếp: 234-D8 Hùng Vương, P. Bến Tre, TP Bến Tre (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "khach-san-diamond-stars", "price_range": "100.000–200.000 VND/đêm", "accommodation_type": "Nhà nghỉ", "check_in": "14:00", "check_out": "12:00", "booking_note": "Liên hệ trực tiếp: 140 Hùng Vương, P. An Hội, TP Bến Tre (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "ks-nh-hung-vuong", "price_range": "100.000–200.000 VND/đêm", "accommodation_type": "Nhà nghỉ", "check_in": "14:00", "check_out": "12:00", "booking_note": "Liên hệ trực tiếp: 148 Hùng Vương, P. An Hội, TP Bến Tre (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "khach-san-binh-dai", "price_range": "300.000–600.000 VND/đêm", "accommodation_type": "Khách sạn 2 sao", "check_in": "14:00", "check_out": "12:00", "booking_note": "Liên hệ trực tiếp: Nguyễn Thị Định, Ấp Bình Hòa, huyện Bình Đại, Bến Tre (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "homestay-ut-trinh-con-tam-hiep", "price_range": "200.000–400.000 VND/người hoặc 400.000–800.000 VND/phòng", "accommodation_type": "Homestay", "check_in": "14:00", "check_out": "11:00", "booking_note": "Đặt phòng qua điện thoại hoặc Zalo; nằm trên Cồn Tam Hiệp, xã Phú Thuận, huyện Bình Đại, Bến Tre (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "cocohut-homestay", "price_range": "200.000–400.000 VND/người hoặc 400.000–800.000 VND/phòng", "accommodation_type": "Homestay", "check_in": "14:00", "check_out": "11:00", "booking_note": "Liên hệ trực tiếp: Ấp Hòa Trung, xã Sơn Hòa, huyện Châu Thành, Bến Tre (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "homestay-lang-be", "price_range": "200.000–400.000 VND/người hoặc 400.000–800.000 VND/phòng", "accommodation_type": "Homestay", "check_in": "14:00", "check_out": "11:00", "booking_note": "Liên hệ trực tiếp: 81B/6B Ấp An Thới B, xã An Khánh, huyện Châu Thành, Bến Tre (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "homestay-nguoi-giu-rung", "price_range": "200.000–400.000 VND/người hoặc 400.000–800.000 VND/phòng", "accommodation_type": "Homestay", "check_in": "14:00", "check_out": "11:00", "booking_note": "Liên hệ trực tiếp: Ấp Tân An, xã Thạnh Phước, huyện Thạnh Phú, Bến Tre; phù hợp cho khách muốn trải nghiệm rừng ngập mặn (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "coconut-homestay", "price_range": "200.000–400.000 VND/người hoặc 400.000–800.000 VND/phòng", "accommodation_type": "Homestay", "check_in": "14:00", "check_out": "11:00", "booking_note": "Liên hệ trực tiếp: 66 Ấp Tân Phước, huyện Mỏ Cày, Bến Tre (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "homestay-ut-trinh", "price_range": "500.000–1.200.000 VND/đêm", "accommodation_type": "Nhà vườn có dịch vụ", "check_in": "14:00", "check_out": "11:00", "booking_note": "Nằm trên cù lao An Bình, Vĩnh Long; đặt phòng qua Zalo hoặc điện thoại trước ít nhất 1 ngày (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "nha-dua-cocohome", "price_range": "500.000–1.200.000 VND/đêm", "accommodation_type": "Nhà vườn có dịch vụ (Homestay đặc sắc)", "check_in": "14:00", "check_out": "11:00", "booking_note": "Kiến trúc dừa độc đáo tại Bến Tre; nên đặt trước qua điện thoại hoặc mạng xã hội (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "hotel-phuoc-thinh", "price_range": "300.000–600.000 VND/đêm", "accommodation_type": "Khách sạn 2 sao", "check_in": "14:00", "check_out": "12:00", "booking_note": "Trung tâm TP Vĩnh Long, gần chợ và bến phà; có thể đặt qua Booking.com hoặc liên hệ trực tiếp (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "van-trang-hotel", "price_range": "300.000–600.000 VND/đêm", "accommodation_type": "Khách sạn 2 sao", "check_in": "14:00", "check_out": "12:00", "booking_note": "Tại Vĩnh Long; có sân hiên và dịch vụ lưu trú cơ bản; liên hệ trực tiếp để đặt phòng (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "khach-san-hoang-khiem", "price_range": "300.000–600.000 VND/đêm", "accommodation_type": "Khách sạn 2 sao", "check_in": "14:00", "check_out": "12:00", "booking_note": "Ấp Mỹ Thới (5), Vĩnh Long; liên hệ trực tiếp để xác nhận phòng trống (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "lo-lem-homestay", "price_range": "200.000–400.000 VND/người hoặc 400.000–800.000 VND/phòng", "accommodation_type": "Homestay", "check_in": "14:00", "check_out": "11:00", "booking_note": "Tại Vĩnh Long; có ban công, sân hiên, chỗ đậu xe và Wi-Fi; liên hệ trực tiếp hoặc đặt qua OTA (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "test", "price_range": "300.000–600.000 VND/đêm", "accommodation_type": "Khách sạn 2 sao", "check_in": "14:00", "check_out": "12:00", "booking_note": "Ấp Mỹ Thới (5), Vĩnh Long; thông tin còn hạn chế, nên liên hệ trực tiếp để xác nhận (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "mekong-lodge-resort", "price_range": "800k–2tr/đêm", "accommodation_type": "Resort sinh thái", "check_in": "14:00", "check_out": "12:00", "booking_note": "Bungalow gỗ lợp lá, hồ bơi, đặt trước 1–2 tuần dịp lễ (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "homestay-bay-thoi", "price_range": "200–400k/người hoặc 400–800k/phòng", "accommodation_type": "Homestay bình dân", "check_in": "13:00", "check_out": "11:00", "booking_note": "Phòng đơn giản trong vườn cây ăn trái, nên liên hệ trước (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "khach-san-cuu-long", "price_range": "600k–1.2tr/đêm", "accommodation_type": "Khách sạn 3 sao", "check_in": "14:00", "check_out": "12:00", "booking_note": "View sông Cổ Chiên, đặt phòng qua website hoặc OTA (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "nha-nghi-thanh-thao", "price_range": "100–200k/đêm", "accommodation_type": "Nhà nghỉ bình dân", "check_in": "13:00", "check_out": "11:00", "booking_note": "Gần chợ Vĩnh Long, thường nhận khách walk-in (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "resort-ben-tre-riverside", "price_range": "800k–2tr/đêm", "accommodation_type": "Resort ven sông", "check_in": "14:00", "check_out": "12:00", "booking_note": "Hồ bơi vô cực, view sông, đặt trước qua OTA hoặc hotline (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "homestay-dua-ben-tre", "price_range": "200–400k/người hoặc 400–800k/phòng", "accommodation_type": "Homestay sinh thái", "check_in": "13:00", "check_out": "11:00", "booking_note": "Nhà sàn gỗ dừa, trải nghiệm làm kẹo dừa, nên đặt trước 3–5 ngày (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "khach-san-ham-luong", "price_range": "300–600k/đêm", "accommodation_type": "Khách sạn 2 sao", "check_in": "14:00", "check_out": "12:00", "booking_note": "Trung tâm TP Bến Tre, tiện nghi cơ bản, có thể đặt walk-in (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "tra-vinh-palace-hotel", "price_range": "600k–1.2tr/đêm", "accommodation_type": "Khách sạn 3 sao", "check_in": "14:00", "check_out": "12:00", "booking_note": "Gần ao Bà Om, khách sạn lớn nhất TP Trà Vinh, đặt qua OTA hoặc hotline (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "nha-nghi-phuong-nam", "price_range": "100–200k/đêm", "accommodation_type": "Nhà nghỉ bình dân", "check_in": "13:00", "check_out": "11:00", "booking_note": "Gần chợ Trà Vinh, phòng máy lạnh, nhận khách walk-in (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "homestay-khmer-tra-vinh", "price_range": "200–400k/người hoặc 400–800k/phòng", "accommodation_type": "Homestay văn hóa Khmer", "check_in": "13:00", "check_out": "11:00", "booking_note": "Nhà sàn gỗ truyền thống Khmer, trải nghiệm văn hóa địa phương, nên đặt trước (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "resort-vinh-sang", "price_range": "500k–1.2tr/đêm", "accommodation_type": "Khu nghỉ dưỡng sinh thái", "check_in": "14:00", "check_out": "12:00", "booking_note": "Nhà vườn ven sông cù lao An Bình, đặt trước dịp cuối tuần và lễ (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "can-tho-hotel-transit", "price_range": "300–600k/đêm", "accommodation_type": "Khách sạn 2 sao", "check_in": "14:00", "check_out": "12:00", "booking_note": "Gần cầu Mỹ Thuận, phù hợp khách quá cảnh, thường nhận walk-in (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "homestay-co-chin-an-binh", "price_range": "200–400k/người hoặc 400–800k/phòng", "accommodation_type": "Homestay gia đình", "check_in": "13:00", "check_out": "11:00", "booking_note": "Giữa vườn nhãn và chôm chôm cù lao An Bình, liên hệ trực tiếp để đặt chỗ (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "khach-san-binh-minh", "price_range": "300–600k/đêm", "accommodation_type": "Khách sạn nhỏ", "check_in": "14:00", "check_out": "12:00", "booking_note": "Tại TX Bình Minh gần vùng bưởi Năm Roi, phù hợp khách công tác và du lịch (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "mango-home-ben-tre", "price_range": "200–400k/người hoặc 400–800k/phòng", "accommodation_type": "Homestay hiện đại", "check_in": "14:00", "check_out": "12:00", "booking_note": "Phong cách decor đẹp giữa vườn xoài Châu Thành, đặt trước qua mạng xã hội hoặc OTA (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "ba-dong-beach-resort", "price_range": "800k–2tr/đêm", "accommodation_type": "Resort biển", "check_in": "14:00", "check_out": "12:00", "booking_note": "Liên hệ trực tiếp hoặc đặt qua Booking.com/Agoda. (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "one-hotel", "price_range": "300k–600k/đêm", "accommodation_type": "Khách sạn 2 sao", "check_in": "14:00", "check_out": "12:00", "booking_note": "Có phòng Deluxe, VIP và bungalow gia đình. (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "the-grand-hotel-vinh-long", "price_range": "600k–1.2tr/đêm", "accommodation_type": "Khách sạn boutique 3 sao", "check_in": "14:00", "check_out": "12:00", "booking_note": "Vị trí trung tâm, gần khu ẩm thực. (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "khach-san-paris-vinh-long", "price_range": "300k–600k/đêm", "accommodation_type": "Khách sạn 2 sao", "check_in": "14:00", "check_out": "12:00", "booking_note": "WiFi miễn phí, mini bar, thang máy. (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "khach-san-vin-vinh-long", "price_range": "300k–600k/đêm", "accommodation_type": "Khách sạn 2 sao", "check_in": "14:00", "check_out": "12:00", "booking_note": "Tiếp tân 24h, bãi xe riêng, ATM. (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "vinh-sang-resort", "price_range": "800k–2tr/đêm", "accommodation_type": "Resort sinh thái", "check_in": "14:00", "check_out": "12:00", "booking_note": "Nằm trên cù lao An Bình, cần đặt trước vào cuối tuần. (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "happy-family-guesthouse", "price_range": "200k–400k/đêm", "accommodation_type": "Nhà nghỉ / Guesthouse", "check_in": "13:00", "check_out": "11:00", "booking_note": "Phổ biến với khách bụi, nên đặt sớm. (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "coco-happy-farm", "price_range": "500k–1.2tr/đêm", "accommodation_type": "Nhà vườn / Farmstay", "check_in": "14:00", "check_out": "11:00", "booking_note": "Trải nghiệm nông trại, ẩm thực địa phương. (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "mekong-home", "price_range": "500k–1.2tr/đêm", "accommodation_type": "Nhà vườn / Bungalow", "check_in": "14:00", "check_out": "11:00", "booking_note": "Bungalow giữa vườn dừa, không khí yên tĩnh. (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "coco-farmstay", "price_range": "400k–800k/đêm", "accommodation_type": "Farmstay / Homestay", "check_in": "14:00", "check_out": "11:00", "booking_note": "Gắn với vườn dừa và sinh hoạt nông nghiệp. (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "my-cam-hotel", "price_range": "300k–600k/đêm", "accommodation_type": "Khách sạn 2 sao", "check_in": "14:00", "check_out": "12:00", "booking_note": "Tại trung tâm thành phố. (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "khach-san-hoai-phu", "price_range": "300k–600k/đêm", "accommodation_type": "Khách sạn 2 sao", "check_in": "14:00", "check_out": "12:00", "booking_note": "Tại TP Bến Tre, phù hợp khách công tác và du lịch. (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "nha-nghi-quynh-phuc", "price_range": "100k–200k/đêm", "accommodation_type": "Nhà nghỉ bình dân", "check_in": "13:00", "check_out": "11:00", "booking_note": "Phòng sạch sẽ, giá bình dân tại Bến Tre. (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "mekong-hotel-restaurant", "price_range": "600k–1.2tr/đêm", "accommodation_type": "Khách sạn 3 sao", "check_in": "14:00", "check_out": "12:00", "booking_note": "Tọa lạc trên đại lộ Đồng Khởi, có nhà hàng sang trọng. (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "rooster-mekong-resort", "price_range": "800k–2tr/đêm", "accommodation_type": "Resort sinh thái", "check_in": "14:00", "check_out": "12:00", "booking_note": "Khu nghỉ dưỡng 2ha bên sông Mê Kông, nên đặt trước. (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "farmstay-sinh-thai-nguyen-gia", "price_range": "500k–1.2tr/đêm", "accommodation_type": "Farmstay / Nhà vườn sinh thái", "check_in": "14:00", "check_out": "12:00", "booking_note": "Liên hệ trực tiếp chủ vườn để đặt chỗ. (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "khu-du-lich-sinh-thai-nam-son", "price_range": "500k–1.2tr/đêm", "accommodation_type": "Khu du lịch sinh thái / Nhà vườn có dịch vụ", "check_in": "14:00", "check_out": "12:00", "booking_note": "Có thể đặt theo nhóm hoặc theo phòng, nên liên hệ trước để xác nhận phòng trống. (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "homestay-sokfram", "price_range": "400–800k/phòng/đêm", "accommodation_type": "Homestay phổ thông", "check_in": "13:00", "check_out": "11:00", "booking_note": "Chỉ có 3 phòng, nên đặt trước ít nhất 1–2 ngày. (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "nha-nghi-nha-co-dai-an", "price_range": "100–200k/đêm", "accommodation_type": "Nhà nghỉ", "check_in": "14:00", "check_out": "12:00", "booking_note": "Nằm trong khuôn viên khu du lịch, liên hệ ban quản lý khu để đặt phòng. (Ước tính – liên hệ trực tiếp để xác nhận)"},
  {"id": "binh-minh-ecolodge-riverside", "price_range": "800k–2tr/đêm", "accommodation_type": "Ecolodge / Resort nhỏ boutique", "check_in": "14:00", "check_out": "12:00", "booking_note": "Vị trí ven sông Hậu, khuyến nghị đặt trước qua website hoặc điện thoại để chọn phòng view sông. (Ước tính – liên hệ trực tiếp để xác nhận)"},
]

patch_map = {p["id"]: p for p in patches}

DATA_PATH = r"C:\Code\vinhlong360\web\data.json"

with open(DATA_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

updated = 0
not_found = []

for entity in data["entities"]:
    eid = entity.get("id")
    if eid in patch_map:
        p = patch_map[eid]
        if "attributes" not in entity or entity["attributes"] is None:
            entity["attributes"] = {}
        attrs = entity["attributes"]
        attrs["price_range"] = p["price_range"]
        attrs["accommodation_type"] = p["accommodation_type"]
        if "check_in" not in attrs:
            attrs["check_in"] = p["check_in"]
        if "check_out" not in attrs:
            attrs["check_out"] = p["check_out"]
        if "booking_note" not in attrs:
            attrs["booking_note"] = p["booking_note"]
        updated += 1

found_ids = {e.get("id") for e in data["entities"]}
for pid in patch_map:
    if pid not in found_ids:
        not_found.append(pid)

with open(DATA_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Updated: {updated}")
print(f"Not found: {not_found}")
