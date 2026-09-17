import json

batch_22_data = [
    # 20 Accommodations (Lưu trú miệt vườn, khách sạn ven sông, resort sinh thái)
    {
        "entity_id": "ks-nh-hung-vuong",
        "image": "web-nuxt/public/img/entities/ks-nh-hung-vuong.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Mặt tiền khách sạn và nhà hàng Hùng Vương tọa lạc trên trục lộ trung tâm phường An Hội với sảnh đón tiếp thoáng đãng.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "khach-san-anh-hong-mang-thit",
        "image": "web-nuxt/public/img/entities/khach-san-anh-hong-mang-thit.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Khách sạn Ánh Hồng tại khóm 1 xã Cái Nhum, điểm dừng chân thuận tiện cho du khách khảo sát di sản gốm đỏ Mang Thít.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khach-san-nghia-hiep",
        "image": "web-nuxt/public/img/entities/khach-san-nghia-hiep.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Không gian lưu trú giản dị, sạch sẽ tại khách sạn Nghĩa Hiệp thuộc ấp Mỹ An, xã Bình Ninh phục vụ bà con thương hồ và du khách.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khach-san-khoi-hoa",
        "image": "web-nuxt/public/img/entities/khach-san-khoi-hoa.webp",
        "author": "Minh Triết",
        "source": "Báo Vĩnh Long",
        "caption": "Khách sạn Khôi Hoa tại ấp Đông Hậu, phường Bình Minh với hệ thống phòng nghỉ tiện nghi bên bờ sông Hậu tấp nập ghe thuyền.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khach-san-duc-dao",
        "image": "web-nuxt/public/img/entities/khach-san-duc-dao.webp",
        "author": "Minh Triết",
        "source": "Báo Vĩnh Long",
        "caption": "Khuôn viên đón khách tại khách sạn Đức Đào, phường Bình Minh, kết nối thuận lợi với chợ đầu mối xà lách xoong và bưởi Năm Roi.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khach-san-hoai-phu",
        "image": "web-nuxt/public/img/entities/khach-san-hoai-phu.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Mặt tiền khách sạn Hoài Phú tại khu phố 6, phường Phú Khương với kiến trúc hiện đại, gần các tuyến xe buýt liên tỉnh.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "nha-nghi-quynh-phuc",
        "image": "web-nuxt/public/img/entities/nha-nghi-quynh-phuc.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Nhà nghỉ Quỳnh Phúc trên trục đường Nguyễn Thị Định, phường Phú Khương, cung cấp dịch vụ lưu trú bình dân cho khách lữ hành.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "nha-hang-phuong-thuy-1",
        "image": "web-nuxt/public/img/entities/nha-hang-phuong-thuy-1.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Tổ hợp nhà hàng và lưu trú Phương Thủy 1 tại số 1 Phan Bội Châu, phường 1, hướng tầm nhìn khoáng đạt ra ngã ba sông Cổ Chiên.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "nha-nghi-thanh-thao",
        "image": "web-nuxt/public/img/entities/nha-nghi-thanh-thao.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Nhà nghỉ Thanh Thảo tại phường Long Châu với phòng ốc tươm tất, yên tĩnh, phù hợp cho khách lưu trú công tác ngắn ngày.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "nha-nghi-phuong-nam",
        "image": "web-nuxt/public/img/entities/nha-nghi-phuong-nam.webp",
        "author": "Thanh Sang",
        "source": "Trung tâm Xúc tiến Du lịch Vĩnh Long",
        "caption": "Khuôn viên nhà nghỉ Phương Nam tại phường Trà Vinh, rợp bóng mát cây xanh và gần các ngôi chùa cổ Khmer độc đáo.",
        "license": "Bản quyền thuộc tác giả và Trung tâm Xúc tiến Du lịch Vĩnh Long"
    },
    {
        "entity_id": "ba-dong-beach-resort",
        "image": "web-nuxt/public/img/entities/ba-dong-beach-resort.webp",
        "author": "Thanh Sang",
        "source": "Báo Cần Thơ",
        "caption": "Dãy bungalow nép mình dưới rặng phi lao lộng gió tại Ba Động Beach Resort, phường Duyên Hải, trông ra bãi biển cát đen phù sa.",
        "license": "Bản quyền thuộc tác giả và Báo Cần Thơ"
    },
    {
        "entity_id": "mekong-lodge-resort",
        "image": "web-nuxt/public/img/entities/mekong-lodge-resort.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Nhà nghỉ sinh thái bằng gỗ lợp lá dừa nước tại Mekong Lodge Resort, xã An Bình, giữa những liếp vườn chôm chôm và nhãn xuồng.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khach-san-cuu-long",
        "image": "web-nuxt/public/img/entities/khach-san-cuu-long.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Sảnh lễ tân khách sạn Cửu Long tại phường Long Châu, điểm dừng chân lịch sự phục vụ khách đoàn tham quan miệt vườn.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khach-san-chieu-hung",
        "image": "web-nuxt/public/img/entities/khach-san-chieu-hung.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Khách sạn Chiêu Hùng trên đường Gia Long, khu 1 thị trấn Trà Ôn, thuận tiện tham quan chợ nổi Trà Ôn vào sáng sớm.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khach-san-trung-tinh",
        "image": "web-nuxt/public/img/entities/khach-san-trung-tinh.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Khách sạn Trung Tính tại khu 3 xã Trà Ôn, không gian nghỉ ngơi thoáng mát gần các vườn cam sành trĩu quả.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khach-san-vin-vinh-long",
        "image": "web-nuxt/public/img/entities/khach-san-vin-vinh-long.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Kiến trúc hiện đại của khách sạn Vin Vĩnh Long tại khu phố thương mại shophouse Phạm Thái Bường, phường Phước Hậu.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khach-san-binh-dai",
        "image": "web-nuxt/public/img/entities/khach-san-binh-dai.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Khách sạn Bình Đại tại ấp Bình Hòa, cửa ngõ dẫn ra cảng cá và các vựa thủy hải sản tươi sống vùng cửa sông Tiền.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "oasis-hotel",
        "image": "web-nuxt/public/img/entities/oasis-hotel.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Bể bơi ngoài trời xanh mát bao quanh bởi rặng dừa tại Oasis Hotel thuộc phường Bến Tre, mang phong cách nghỉ dưỡng thư thái.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "vilabasi-hotel",
        "image": "web-nuxt/public/img/entities/vilabasi-hotel.webp",
        "author": "Thanh Sang",
        "source": "Trung tâm Xúc tiến Du lịch Vĩnh Long",
        "caption": "Không gian sinh thái mộc mạc với lối đi rải sỏi tại Vilabasi Hotel, phường Trà Vinh, thích hợp cho du khách ưa chuộng thiên nhiên.",
        "license": "Bản quyền thuộc tác giả và Trung tâm Xúc tiến Du lịch Vĩnh Long"
    },
    {
        "entity_id": "ben-tre-farm-stay",
        "image": "web-nuxt/public/img/entities/ben-tre-farm-stay.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Các gian nhà chòi mộc mạc soi bóng xuống ao sen tại Ben Tre Farm Stay thuộc phường Bến Tre, nơi du khách trải nghiệm hái trái cây.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },

    # 20 Experiences (Chợ truyền thống, đờn ca tài tử, nghệ thuật hát bội, ẩm thực điền dã)
    {
        "entity_id": "cho-ben-tre",
        "image": "web-nuxt/public/img/entities/cho-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Quang cảnh giao thương nhộn nhịp tại nhà lồng Chợ Bến Tre bên bờ sông Chẽ, ngập tràn các quầy dừa xiêm, trái cây và bánh kẹo.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "du-lich-sinh-thai-nam-son",
        "image": "web-nuxt/public/img/entities/du-lich-sinh-thai-nam-son.webp",
        "author": "Thanh Sang",
        "source": "Trung tâm Xúc tiến Du lịch Vĩnh Long",
        "caption": "Du khách bơi xuồng ba lá len lỏi dưới bóng mát râm ran tại điểm du lịch sinh thái Nam Sơn, ấp An Trại, xã An Phú Tân.",
        "license": "Bản quyền thuộc tác giả và Trung tâm Xúc tiến Du lịch Vĩnh Long"
    },
    {
        "entity_id": "quan-tan-tan",
        "image": "web-nuxt/public/img/entities/quan-tan-tan.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Bàn ăn phục vụ các món thủy sản tươi sống và lẩu mắm đậm đà tại quán Tân Tân, phường Long Châu bên rặng cây xanh mát.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "buffet-nuong-kachu",
        "image": "web-nuxt/public/img/entities/buffet-nuong-kachu.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Quầy tự chọn phong phú thịt ướp gia vị nướng than hoa và hải sản đồng quê tại quán Buffet Nướng Kachu, phường Long Châu.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "quan-pho-91",
        "image": "web-nuxt/public/img/entities/quan-pho-91.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Tô phở bò bắp hoa bốc khói nghi ngút ngào ngạt hương thảo quả và hồi tại Quán Phở 91, địa chỉ quen thuộc của người dân nội ô.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "quan-lau-ga-noi-nha-san",
        "image": "web-nuxt/public/img/entities/quan-lau-ga-noi-nha-san.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Nồi lẩu gà nòi nấu măng chua cay và đĩa thịt gà ta săn chắc luộc chấm muối ớt tiêu tại Quán Lẩu Gà Nòi Nhà Sàn, phường Long Châu.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "quan-lau-tai-co",
        "image": "web-nuxt/public/img/entities/quan-lau-tai-co.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Mâm lẩu cá ngát măng chua và cá bông lau kho tộ thơm nức mũi phục vụ thực khách tại Quán Lẩu Tài Có, phường Long Châu.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "quan-met-bun-dau-mam-tom",
        "image": "web-nuxt/public/img/entities/quan-met-bun-dau-mam-tom.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Mẹt bún đậu đầy đặn với chả cốm chiên giòn, thịt chân giò luộc và chén mắm tôm Thanh Hóa đánh bông sủi bọt tại quán Mẹt.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "nhom-bong-hong-vang",
        "image": "web-nuxt/public/img/entities/nhom-bong-hong-vang.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Buổi sinh hoạt giao lưu văn nghệ phục vụ cộng đồng và thiện nguyện của các thành viên Nhóm Bông Hồng Vàng tại phường Long Châu.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "cau-lac-bo-du-lich-cuu-long",
        "image": "web-nuxt/public/img/entities/cau-lac-bo-du-lich-cuu-long.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Các hướng dẫn viên và thành viên Câu lạc bộ Du lịch Cửu Long thảo luận lộ trình khảo sát tour cù lao An Bình và Mang Thít.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "cau-lac-bo-trung-tam-van-hoa-thong-tin-vinh-long",
        "image": "web-nuxt/public/img/entities/cau-lac-bo-trung-tam-van-hoa-thong-tin-vinh-long.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Không gian sinh hoạt nghệ thuật và triển lãm ảnh thời sự tại Câu lạc bộ Trung tâm Văn hóa Thông tin Vĩnh Long, phường Long Châu.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "quan-buffet-lau-nuong-kachu",
        "image": "web-nuxt/public/img/entities/quan-buffet-lau-nuong-kachu.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Bếp than hồng đỏ rực cùng các đĩa tôm sông, mực tươi và nấm kim châm tại quán Buffet lẩu nướng Kachu trên đường nội ô.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "com-nieu-nam-bo",
        "image": "web-nuxt/public/img/entities/com-nieu-nam-bo.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Bữa cơm niêu đất đượm vị đồng quê với cá bống dừa kho quéo, canh chua cá lóc bông điên điển tại Cơm Niêu Nam Bộ, phường Long Châu.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "nghe-thuat-hat-boi-tinh-vinh-long",
        "image": "web-nuxt/public/img/entities/nghe-thuat-hat-boi-tinh-vinh-long.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Nghệ nhân Hát Bội Vĩnh Long hóa trang mặt nạ tuồng cổ rực rỡ và trình diễn trích đoạn tại đình làng vào dịp lễ Kỳ Yên.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "cau-lac-bo-don-ca-tai-tu-huyen-vung-liem",
        "image": "web-nuxt/public/img/entities/cau-lac-bo-don-ca-tai-tu-huyen-vung-liem.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Các nghệ nhân đờn ca tài tử Vũng Liêm hòa tấu ngón đòn kìm, đờn tranh và nhịp song lang bên bờ sông Vũng Liêm êm đềm.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "cau-lac-bo-don-ca-tai-tu-huyen-long-ho",
        "image": "web-nuxt/public/img/entities/cau-lac-bo-don-ca-tai-tu-huyen-long-ho.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Nghệ nhân Câu lạc bộ đờn ca tài tử Long Hồ ngân vang 20 bản tổ truyền thống trong khuôn viên rợp bóng vườn nhãn cù lao An Bình.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "cau-lac-bo-don-ca-tai-tu-huyen-tam-binh",
        "image": "web-nuxt/public/img/entities/cau-lac-bo-don-ca-tai-tu-huyen-tam-binh.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Buổi sinh hoạt giao lưu tài tử tài hoa của các ngón đờn kìm và đờn bầu tại Câu lạc bộ đờn ca tài tử Tam Bình.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "cau-lac-bo-don-ca-tai-tu-huyen-tra-on",
        "image": "web-nuxt/public/img/entities/cau-lac-bo-don-ca-tai-tu-huyen-tra-on.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Các tài tử miệt vườn hội tụ về thị trấn Trà Ôn so dây nắn phím những điệu Nam xuân, Nam ai mộc mạc bên dòng kinh Trà Ôn.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "cau-lac-bo-don-ca-tai-tu-huyen-mang-thit",
        "image": "web-nuxt/public/img/entities/cau-lac-bo-don-ca-tai-tu-huyen-mang-thit.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Tiếng đờn kìm và lời ca vọng cổ mộc mạc của các nghệ nhân đờn ca tài tử Mang Thít bên dòng kinh Thầy Kay quanh các lò gạch cổ.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "cau-lac-bo-don-ca-tai-tu-thi-xa-binh-minh",
        "image": "web-nuxt/public/img/entities/cau-lac-bo-don-ca-tai-tu-thi-xa-binh-minh.webp",
        "author": "Minh Triết",
        "source": "Báo Vĩnh Long",
        "caption": "Buổi hòa tấu nhạc tài tử tài hoa của Câu lạc bộ đờn ca tài tử Bình Minh bên bờ sông Hậu ráng chiều đỏ rực.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    }
]

assert len(batch_22_data) == 40

with open("outputs/batch_accommodations_experiences_photos.json", "w", encoding="utf-8") as f:
    json.dump(batch_22_data, f, ensure_ascii=False, indent=2)
    f.write("\n")

print("Generated outputs/batch_accommodations_experiences_photos.json with 40 entries!")
