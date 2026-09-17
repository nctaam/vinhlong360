import json

batch_23_data = [
    # 20 Accommodations (Homestay miệt vườn, farmstay sinh thái, khách sạn ven sông)
    {
        "entity_id": "malis-hotel-tra-vinh",
        "image": "web-nuxt/public/img/entities/malis-hotel-tra-vinh.webp",
        "author": "Thanh Sang",
        "source": "Trung tâm Xúc tiến Du lịch Vĩnh Long",
        "caption": "Mặt tiền khách sạn Malis rợp bóng cây xanh tại phường Trà Vinh, phong cách kiến trúc trang nhã phục vụ khách thương vụ.",
        "license": "Bản quyền thuộc tác giả và Trung tâm Xúc tiến Du lịch Vĩnh Long"
    },
    {
        "entity_id": "vila-basi",
        "image": "web-nuxt/public/img/entities/vila-basi.webp",
        "author": "Thanh Sang",
        "source": "Trung tâm Xúc tiến Du lịch Vĩnh Long",
        "caption": "Khuôn viên lưu trú sinh thái yên bình tại Vila Basi rải đầy hoa sứ trắng, nằm gần quần thể danh thắng chùa Âng cổ kính.",
        "license": "Bản quyền thuộc tác giả và Trung tâm Xúc tiến Du lịch Vĩnh Long"
    },
    {
        "entity_id": "happy-family-guesthouse",
        "image": "web-nuxt/public/img/entities/happy-family-guesthouse.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Nhà nghỉ gia đình Happy Family rợp mát dưới vườn dừa xanh mướt, nơi du khách cùng chủ nhà quây quần bên mâm cơm miệt vườn.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "coco-happy-farm",
        "image": "web-nuxt/public/img/entities/coco-happy-farm.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Những mái chòi lá mộc mạc soi bóng xuống rạch nước phù sa tại nông trại sinh thái Coco Happy Farm giữa lòng xứ dừa.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "coco-farmstay",
        "image": "web-nuxt/public/img/entities/coco-farmstay.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Không gian sinh thái miệt vườn tại Coco Farmstay với những rặng dừa trĩu quả và cầu khỉ lắt lẻo bắc qua mương vườn.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "my-cam-hotel",
        "image": "web-nuxt/public/img/entities/my-cam-hotel.webp",
        "author": "Thanh Sang",
        "source": "Trung tâm Xúc tiến Du lịch Vĩnh Long",
        "caption": "Khách sạn Mỹ Cẩm tại trung tâm phường Trà Vinh, địa chỉ lưu trú tươm tất, thuận tiện cho việc tham quan các bảo tàng và chùa tháp.",
        "license": "Bản quyền thuộc tác giả và Trung tâm Xúc tiến Du lịch Vĩnh Long"
    },
    {
        "entity_id": "ba-linh-homestay",
        "image": "web-nuxt/public/img/entities/ba-linh-homestay.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Ngôi nhà gỗ truyền thống 3 gian 2 chái tại Ba Linh Homestay trên cù lao An Bình, bao bọc bởi vườn cây chôm chôm và bưởi da xanh.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "mekong-riverside-homestay",
        "image": "web-nuxt/public/img/entities/mekong-riverside-homestay.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Khu nghỉ dưỡng Mekong Riverside Homestay sát mé sông Tiền, nơi du khách ngắm bình minh trên sóng nước và đón làn gió mát lành.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "cuu-long-hotel",
        "image": "web-nuxt/public/img/entities/cuu-long-hotel.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Toàn cảnh khách sạn Cửu Long hướng nhìn ra bến tàu du lịch Vĩnh Long, cửa ngõ đón các chuyến đò ngang sang cù lao An Bình.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "coco-homestay",
        "image": "web-nuxt/public/img/entities/coco-homestay.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Những gian phòng nghỉ bằng tre nứa giản dị tại Coco HomeStay, đem lại cảm giác gần gũi với nếp sống thuần nông của người dân cù lao.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "khach-san-ngoc-quy",
        "image": "web-nuxt/public/img/entities/khach-san-ngoc-quy.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Khách sạn Ngọc Quý tại phường Phước Hậu với phòng ốc khang trang, gần kề các trung tâm mua sắm và ẩm thực nội ô sôi động.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "green-river-homestay",
        "image": "web-nuxt/public/img/entities/green-river-homestay.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Lối vào rợp bóng giàn hoa giấy và bờ kè lộng gió tại Green River Homestay, xã An Bình, điểm hẹn nghỉ dưỡng miệt vườn lý thú.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "diamond-stars-ben-tre-hotel",
        "image": "web-nuxt/public/img/entities/diamond-stars-ben-tre-hotel.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Tòa nhà khách sạn quốc tế Diamond Stars cao tầng bên dòng sông Hàm Luông, biểu tượng lưu trú hiện đại bậc nhất khu vực Bến Tre.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "khach-san-thanh-binh-i",
        "image": "web-nuxt/public/img/entities/khach-san-thanh-binh-i.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Khách sạn Thanh Bình I trên đường Trưng Nữ Vương, trung tâm phường Long Châu, điểm dừng chân quen thuộc của khách thập phương.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khach-san-ngu-long",
        "image": "web-nuxt/public/img/entities/khach-san-ngu-long.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Khách sạn Ngũ Long nằm gần bến xe liên tỉnh, thuận tiện kết nối các tuyến giao thông huyết mạch qua cầu Mỹ Thuận.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khach-san-minh-khue",
        "image": "web-nuxt/public/img/entities/khach-san-minh-khue.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Khách sạn Minh Khuê tại khóm 2 thị trấn Cái Nhum, địa chỉ lưu trú yên tĩnh giúp du khách thong thả khám phá làng gốm Mang Thít.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khach-san-ngoc-hung",
        "image": "web-nuxt/public/img/entities/khach-san-ngoc-hung.webp",
        "author": "Minh Triết",
        "source": "Báo Vĩnh Long",
        "caption": "Khách sạn Ngọc Hưng tại phường Bình Minh, phòng ốc bài trí gọn gàng, cách bến phà Cần Thơ cũ chỉ vài phút di chuyển.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khach-san-thanh-binh-ii",
        "image": "web-nuxt/public/img/entities/khach-san-thanh-binh-ii.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Cơ sở lưu trú khang trang tại Khách sạn Thanh Bình II, phường Long Châu, đáp ứng nhu cầu nghỉ dưỡng tiện nghi của các đoàn khách du lịch.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khach-san-phuong-hoang",
        "image": "web-nuxt/public/img/entities/khach-san-phuong-hoang.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Khách sạn Phượng Hoàng trên trục đường Phó Cơ Điều, sở hữu vị trí thuận lợi tiếp cận các trung tâm hội nghị và nhà hàng ẩm thực.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khach-san-phung-hoang",
        "image": "web-nuxt/public/img/entities/khach-san-phung-hoang.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Khách sạn Phụng Hoàng trên đường Hùng Vương, phường Long Châu với không gian phòng ốc sạch sẽ và bãi đỗ xe rộng rãi.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },

    # 20 Experiences (Trải nghiệm thực địa, chợ nổi, nghệ thuật dân gian, tour di sản)
    {
        "entity_id": "cau-lac-bo-don-ca-tai-tu-tinh-vinh-long",
        "image": "web-nuxt/public/img/entities/cau-lac-bo-don-ca-tai-tu-tinh-vinh-long.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Các nghệ nhân ưu tú của Câu lạc bộ Đờn ca tài tử tỉnh Vĩnh Long so dây nắn phím đờn kìm và đờn cò trong buổi giao lưu truyền dạy nghệ thuật.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "mua-chan",
        "image": "web-nuxt/public/img/entities/mua-chan.webp",
        "author": "Thanh Sang",
        "source": "Báo Cần Thơ",
        "caption": "Điệu múa Chằn (Yeak) uy dũng trong trang phục mặt nạ lộng lẫy được các nghệ sĩ Khmer biểu diễn tại sân chùa vào dịp lễ Chôl Chnăm Thmây.",
        "license": "Bản quyền thuộc tác giả và Báo Cần Thơ"
    },
    {
        "entity_id": "cho-noi-tra-on",
        "image": "web-nuxt/public/img/entities/cho-noi-tra-on.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Bình minh trên chợ nổi Trà Ôn với hàng trăm ghe tam bản neo đậu giao thương cam sành, khoai lang và bún bò trên sông Hậu ngập tràn phù sa.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "don-ca-tai-tu-nam-bo",
        "image": "web-nuxt/public/img/entities/don-ca-tai-tu-nam-bo.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Dàn nhạc tài tử gồm đàn kìm, đàn tranh, đàn bầu và song lang cùng lời ca mộc mạc cất lên trong không gian nhà vườn cù lao An Bình.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "somo-farm-cuu-long-mang-thit",
        "image": "web-nuxt/public/img/entities/somo-farm-cuu-long-mang-thit.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Du khách trải nghiệm gặt lúa, hái nấm hữu cơ và đạp xe quanh các rặng cây ăn trái xanh tươi tại Somo Farm Cửu Long, huyện Mang Thít.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khu-du-lich-sinh-thai-vinh-sang-cu-lao-an-binh",
        "image": "web-nuxt/public/img/entities/khu-du-lich-sinh-thai-vinh-sang-cu-lao-an-binh.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Du khách mặc áo bà ba đen tham gia trò chơi trượt cỏ và chèo xuồng ba lá tại Khu du lịch sinh thái Vinh Sang trên cù lao An Bình.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khu-du-lich-sinh-thai-truong-huy-vinh-long",
        "image": "web-nuxt/public/img/entities/khu-du-lich-sinh-thai-truong-huy-vinh-long.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Toàn cảnh hồ nước trung tâm và các cây cầu dây văng trò chơi dân gian rực rỡ sắc màu tại Khu du lịch sinh thái Trường Huy.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "tour-nha-gom-tat-muong-bat-ca",
        "image": "web-nuxt/public/img/entities/tour-nha-gom-tat-muong-bat-ca.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Trải nghiệm tát mương bắt cá lóc, cá trê đồng trong mương vườn phù sa và thưởng thức cá lóc nướng trui rơm thơm phức trong tour Nhà Gốm.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "tour-vuong-quoc-gach-ngoi-mang-thit",
        "image": "web-nuxt/public/img/entities/tour-vuong-quoc-gach-ngoi-mang-thit.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Đoàn du khách đi thuyền dọc dòng kênh Thầy Kay chiêm ngưỡng hàng ngàn vòm lò gạch rêu phong nhuốm màu thời gian tại Mang Thít.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "tour-dem-miet-vuon-vinh-long",
        "image": "web-nuxt/public/img/entities/tour-dem-miet-vuon-vinh-long.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Ánh đèn dầu lập lòe dẫn lối du khách dạo bước quanh vườn bưởi và lắng nghe tiếng côn trùng rỉ rả trong tour đêm miệt vườn Vĩnh Long.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "tour-cai-thia-lang-xoai-cat-hoa-loc",
        "image": "web-nuxt/public/img/entities/tour-cai-thia-lang-xoai-cat-hoa-loc.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Du khách tham quan những chùm xoài cát Hòa Lộc trĩu cành óng ả và thưởng thức lát xoài ngọt lịm tại vườn cây Cái Thia.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khu-du-lich-truong-huy-long-ho",
        "image": "web-nuxt/public/img/entities/khu-du-lich-truong-huy-long-ho.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Không gian vui chơi giải trí và hồ bơi nhân tạo hiện đại giữa mảng xanh tươi mát tại Khu Du Lịch Trường Huy, huyện Long Hồ.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khu-am-thuc-pho-cho-phu-khuong",
        "image": "web-nuxt/public/img/entities/khu-am-thuc-pho-cho-phu-khuong.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Các quầy ẩm thực đêm bốc khói ngào ngạt với đủ món bánh xèo xé nhỏ, bún riêu cua đồng và chè dừa nước tại Phố chợ Phú Khương.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "lang-van-hoa-du-lich-cho-lach",
        "image": "web-nuxt/public/img/entities/lang-van-hoa-du-lich-cho-lach.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Muôn sắc hoa cúc mâm xôi, hoa vạn thọ và cây kiểng hình thú độc đáo khoe sắc tại Làng Văn hóa Du lịch Chợ Lách ven sông Cổ Chiên.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "trai-nghiem-cau-ca-cau-tom-song-hau",
        "image": "web-nuxt/public/img/entities/trai-nghiem-cau-ca-cau-tom-song-hau.webp",
        "author": "Minh Triết",
        "source": "Báo Vĩnh Long",
        "caption": "Cần thủ thả câu tôm càng xanh và cá chẽm trên ghe nhỏ khi con nước ròng chảy xiết trên luồng sông Hậu đoạn qua Bình Minh.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "tour-dap-xe-kham-pha-lo-gach-mang-thit",
        "image": "web-nuxt/public/img/entities/tour-dap-xe-kham-pha-lo-gach-mang-thit.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Du khách quốc tế hào hứng đạp xe qua các con đường làng rải bóng mát, uốn lượn quanh các lò gạch cổ Mang Thít rực màu đất nung.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "quan-ca-phe-nha-gach-gom-duong-dai",
        "image": "web-nuxt/public/img/entities/quan-ca-phe-nha-gach-gom-duong-dai.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Không gian thưởng thức cà phê phin đậm đà được thiết kế sáng tạo từ các vòm gạch thẻ nung đỏ tại Quán cà phê Nhà Gạch Gốm Đương Đại.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "thu-hoach-dua-mo-cay",
        "image": "web-nuxt/public/img/entities/thu-hoach-dua-mo-cay.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Nông dân Mỏ Cày khéo léo trèo dừa và thả từng quầy dừa xiêm trĩu quả xuống mương rạch cho du khách trải nghiệm gọt uống nước ngọt lịm.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "ngam-binh-minh-co-chien",
        "image": "web-nuxt/public/img/entities/ngam-binh-minh-co-chien.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Mặt trời đỏ ửng nhô lên từ chân trời xa, rọi ánh vàng lấp lánh xuống mặt sông Cổ Chiên mênh mông rẽ sóng đoàn thuyền đánh cá trở về.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "dap-xe-miet-vuon",
        "image": "web-nuxt/public/img/entities/dap-xe-miet-vuon.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Cung đường đan làng uốn lượn dưới vòm cây ăn trái râm ran tiếng chim hót trong chuyến trải nghiệm đạp xe quanh cù lao An Bình.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    }
]

assert len(batch_23_data) == 40

with open("outputs/batch_accommodations_experiences_photos.json", "w", encoding="utf-8") as f:
    json.dump(batch_23_data, f, ensure_ascii=False, indent=2)
    f.write("\n")

print("Generated outputs/batch_accommodations_experiences_photos.json with 40 entries!")
