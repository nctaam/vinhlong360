import json

batch_26_data = [
    # 40 Accommodations (Khách sạn sinh thái, homestay miệt vườn, resort ven sông)
    {
        "entity_id": "khach-san-phuoc-hung",
        "image": "web-nuxt/public/img/entities/khach-san-phuoc-hung.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Mặt tiền khách sạn Phước Hưng khang trang trên đường Nguyễn Huệ, phường 2, với phòng ốc tiện nghi cho khách thương vụ.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khach-san-an-khang",
        "image": "web-nuxt/public/img/entities/khach-san-an-khang.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Khuôn viên lưu trú tại khách sạn An Khang trên đường Đinh Tiên Hoàng, phường 8, không gian sạch sẽ và bãi đậu xe rộng rãi.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khach-san-ba-duc",
        "image": "web-nuxt/public/img/entities/khach-san-ba-duc.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Không gian nhà vườn truyền thống kết hợp phòng nghỉ tiện nghi tại khách sạn Ba Đức trên cù lao An Bình rợp bóng cây ăn trái.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khach-san-ngoc-yen",
        "image": "web-nuxt/public/img/entities/khach-san-ngoc-yen.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Khách sạn Ngọc Yến trên đường Phó Cơ Điều, phường 3, cung cấp dịch vụ phòng nghỉ lịch sự và thuận tiện cho khách lữ hành.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khach-san-vinh-sang",
        "image": "web-nuxt/public/img/entities/khach-san-vinh-sang.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Dãy phòng nghỉ sinh thái hướng nhìn ra mé sông Cổ Chiên tại khu du lịch Vinh Sang, cù lao An Bình, lộng gió phù sa.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khach-san-nhat-phuong",
        "image": "web-nuxt/public/img/entities/khach-san-nhat-phuong.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Khách sạn Nhật Phương tại phường 4 với phòng ốc thiết kế trang nhã, cách cầu Lộ chỉ vài trăm mét di chuyển.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khach-san-thanh-xuan",
        "image": "web-nuxt/public/img/entities/khach-san-thanh-xuan.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Mặt tiền khách sạn Thanh Xuân trên đường Trần Phú, phường 4, địa chỉ lưu trú bình dân quen thuộc của khách thập phương.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "le-thi-thuy-an-homestay",
        "image": "web-nuxt/public/img/entities/le-thi-thuy-an-homestay.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Ngôi nhà chòi lá đơn sơ soi bóng bên rạch nước tại Lê Thị Thúy An Homestay, xã An Bình, nơi du khách cùng trải nghiệm nấu ăn dân dã.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khach-san-bich-ngoan",
        "image": "web-nuxt/public/img/entities/khach-san-bich-ngoan.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Khách sạn Bích Ngoan tại phường 2, không gian phòng ốc ngăn nắp và phục vụ nước giải khát tận tình cho khách đường xa.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "nha-khach-vinh-tra",
        "image": "web-nuxt/public/img/entities/nha-khach-vinh-tra.webp",
        "author": "Thanh Sang",
        "source": "Trung tâm Xúc tiến Du lịch Vĩnh Long",
        "caption": "Khuôn viên xanh rợp mát bóng cây dầu cổ thụ tại Nhà khách Vĩnh Trà, phường Trà Vinh, phục vụ khách hội nghị và tham quan.",
        "license": "Bản quyền thuộc tác giả và Trung tâm Xúc tiến Du lịch Vĩnh Long"
    },
    {
        "entity_id": "khach-san-sanh-phuc",
        "image": "web-nuxt/public/img/entities/khach-san-sanh-phuc.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Khách sạn Sanh Phúc trên đường Trưng Nữ Vương, phường 1, gần kề chợ truyền thống và bến đò qua các xã cù lao.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khach-san-hai-duong-2",
        "image": "web-nuxt/public/img/entities/khach-san-hai-duong-2.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Khách sạn Hải Dương 2 tại phường 8 với lối kiến trúc hiện đại, cung cấp hệ thống điều hòa và nước nóng tiện nghi.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khach-san-tuong-vy",
        "image": "web-nuxt/public/img/entities/khach-san-tuong-vy.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Phòng nghỉ thoáng đãng ngập tràn ánh nắng ban mai tại khách sạn Tường Vy, phường 3, mang lại giấc ngủ thư thái.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "farmstay-dat-cu-lao",
        "image": "web-nuxt/public/img/entities/farmstay-dat-cu-lao.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Không gian sinh thái miệt vườn tại Farmstay Đất Cù Lao, xã Bình Hòa Phước, nơi du khách tự tay hái nhãn xuồng và chèo xuồng câu cá.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khach-san-huynh-thao",
        "image": "web-nuxt/public/img/entities/khach-san-huynh-thao.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Khách sạn Huỳnh Thảo tại phường 1 với sảnh đón tiếp gọn gàng, cách công viên bờ kè sông Long Hồ chỉ vài bước chân.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khach-san-dai-an",
        "image": "web-nuxt/public/img/entities/khach-san-dai-an.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Khách sạn Đại An trên đường Lê Thái Tổ, phường 2, cung cấp dịch vụ phòng đơn và phòng gia đình sạch sẽ, chu đáo.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "coco-riverside-lodge",
        "image": "web-nuxt/public/img/entities/coco-riverside-lodge.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Khu nghỉ dưỡng Coco Riverside Lodge bằng gỗ dừa độc đáo bên bờ rạch Hàm Luông, điểm đến nghỉ ngơi yêu thích của du khách quốc tế.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "cocohut-homestay",
        "image": "web-nuxt/public/img/entities/cocohut-homestay.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Những mái nhà tranh tre mộc mạc ẩn hiện dưới tán dừa rợp mát tại Cocohut Homestay, mang đến trải nghiệm sống chậm hòa hợp thiên nhiên.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "ks-nha-co-cau-ke",
        "image": "web-nuxt/public/img/entities/ks-nha-co-cau-ke.webp",
        "author": "Thanh Sang",
        "source": "Trung tâm Xúc tiến Du lịch Vĩnh Long",
        "caption": "Khu lưu trú kiến trúc Pháp cổ kết hợp nhà rường Nam Bộ tại Khách sạn Nhà cổ Cầu Kè, điểm hẹn văn hóa di sản độc đáo.",
        "license": "Bản quyền thuộc tác giả và Trung tâm Xúc tiến Du lịch Vĩnh Long"
    },
    {
        "entity_id": "nh-ks-sy-dien",
        "image": "web-nuxt/public/img/entities/nh-ks-sy-dien.webp",
        "author": "Thanh Sang",
        "source": "Trung tâm Xúc tiến Du lịch Vĩnh Long",
        "caption": "Tổ hợp nhà hàng và khách sạn Sỹ Điền tại phường Trà Vinh, chuyên phục vụ các món ăn Nam Bộ và phòng nghỉ khang trang.",
        "license": "Bản quyền thuộc tác giả và Trung tâm Xúc tiến Du lịch Vĩnh Long"
    },
    {
        "entity_id": "homestay-ut-trinh-con-tam-hiep",
        "image": "web-nuxt/public/img/entities/homestay-ut-trinh-con-tam-hiep.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Homestay Út Trinh trên Cồn Tam Hiệp giữa bốn bề sóng nước phù sa sông Cổ Chiên, với các gian phòng lợp lá dừa nước ngát hương đồng gió nội.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "coconut-homestay",
        "image": "web-nuxt/public/img/entities/coconut-homestay.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Không gian mộc mạc đậm chất xứ dừa tại Coconut Homestay với hồ sen trước ngõ và những giàn hoa khoe sắc rực rỡ dưới nắng mai.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "one-hotel",
        "image": "web-nuxt/public/img/entities/one-hotel.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Mặt tiền khách sạn ONE HOTEL phong cách tối giản hiện đại trên đường 2 Tháng 9, phường 1, được nhiều bạn trẻ lựa chọn khi lưu trú.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "the-grand-hotel-vinh-long",
        "image": "web-nuxt/public/img/entities/the-grand-hotel-vinh-long.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Toàn cảnh khách sạn The Grand Hotel Vĩnh Long trên đường Phó Cơ Điều với sảnh đón sang trọng và các dịch vụ lưu trú cao cấp.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "nha-thuyen-nam-cao-homestay",
        "image": "web-nuxt/public/img/entities/nha-thuyen-nam-cao-homestay.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Nhà thuyền Năm Cao neo đậu bên bến sông An Bình, nơi du khách bồng bềnh say giấc theo từng nhịp sóng nước và đón bình minh trên sông Tiền.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khach-san-phu-gia",
        "image": "web-nuxt/public/img/entities/khach-san-phu-gia.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Khách sạn Phú Gia tại phường 4 với trang thiết bị tiện nghi, nằm gần các trục đường mua sắm và nhà hàng ẩm thực địa phương.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "coco-home",
        "image": "web-nuxt/public/img/entities/coco-home.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Ngôi nhà dừa độc đáo Coco Home được dựng từ hàng ngàn cây dừa cổ thụ tại cù lao An Bình, vừa là điểm tham quan vừa là nơi lưu trú đặc sắc.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khach-san-tan-xuan",
        "image": "web-nuxt/public/img/entities/khach-san-tan-xuan.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Khách sạn Tân Xuân tại phường 2 với không gian phòng nghỉ yên bình, giá cả phải chăng, thích hợp cho các chuyến công tác dài ngày.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "nha-nghi-dl-sinh-thai-hoang-hao",
        "image": "web-nuxt/public/img/entities/nha-nghi-dl-sinh-thai-hoang-hao.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Nhà nghỉ sinh thái Hoàng Hảo tại xã Thanh Đức với các bungalow hướng ra mặt hồ sen mát rượi và vườn cây xanh rợp bóng.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khach-san-xuan-huong",
        "image": "web-nuxt/public/img/entities/khach-san-xuan-huong.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Khách sạn Xuân Hương trên đường Đoàn Thị Điểm, phường 1, sở hữu vị trí trung tâm tiếp giáp nhiều di tích lịch sử và danh lam thắng cảnh.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khach-san-tan-sang",
        "image": "web-nuxt/public/img/entities/khach-san-tan-sang.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Khách sạn Tấn Sang tại phường 9 với các phòng ốc thoáng mát, cung cấp nơi nghỉ chân thư thái cho du khách qua cầu Mỹ Thuận.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "can-tho-hotel-transit",
        "image": "web-nuxt/public/img/entities/can-tho-hotel-transit.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Không gian sảnh lễ tân tại khách sạn Sài Gòn - Vĩnh Long trên đường Trưng Nữ Vương, điểm lưu trú 4 sao chuẩn mực bên bờ sông Cổ Chiên.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khach-san-paris-vinh-long",
        "image": "web-nuxt/public/img/entities/khach-san-paris-vinh-long.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Khách sạn Paris Vĩnh Long tại phường 4 mang phong cách kiến trúc Pháp tân cổ điển lãng mạn cùng hệ thống phòng ngủ cao cấp.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "resort-ben-tre-riverside",
        "image": "web-nuxt/public/img/entities/resort-ben-tre-riverside.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Toàn cảnh hồ bơi vô cực và dãy phòng nghỉ sang trọng tại Bến Tre Riverside Resort hướng ra dòng sông Hàm Luông thơ mộng.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "vin-hotel-vinh-long",
        "image": "web-nuxt/public/img/entities/vin-hotel-vinh-long.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Tòa nhà Vin Hotel Vĩnh Long trong quần thể shophouse thương mại Vincom Plaza trên đường Phạm Thái Bường tấp nập.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "saigon-vinh-long-hotel",
        "image": "web-nuxt/public/img/entities/saigon-vinh-long-hotel.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Toàn cảnh khách sạn quốc tế Saigon Vinh Long Hotel bên dòng sông Cổ Chiên, trung tâm hội nghị và nghỉ dưỡng hàng đầu của tỉnh.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khach-san-ngoi-sao",
        "image": "web-nuxt/public/img/entities/khach-san-ngoi-sao.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Khách sạn Ngôi Sao tại phường 3 với không gian yên tĩnh, an ninh đảm bảo và phong cách đón tiếp niềm nở của đội ngũ nhân viên.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khach-san-tan-an-loc",
        "image": "web-nuxt/public/img/entities/khach-san-tan-an-loc.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Khách sạn Tân An Lộc tại phường 9 với các tiện nghi lưu trú chuẩn mực và dịch vụ thuê xe máy tham quan miệt vườn tiện lợi.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "muoi-quynh-homestay",
        "image": "web-nuxt/public/img/entities/muoi-quynh-homestay.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Mười Quỳnh Homestay trên cù lao An Bình với những liếp vườn bưởi trĩu quả, nơi du khách thưởng thức đờn ca tài tử bên chén trà nóng.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "homestay-hoa-thanh",
        "image": "web-nuxt/public/img/entities/homestay-hoa-thanh.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Khuôn viên nhà vườn rực rỡ sắc hoa và giàn bầu trĩu quả tại Homestay Hòa Thạnh, xã An Bình, điểm hẹn bình yên của lữ khách phương xa.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    }
]

assert len(batch_26_data) == 40

with open("outputs/batch_accommodations_photos.json", "w", encoding="utf-8") as f:
    json.dump(batch_26_data, f, ensure_ascii=False, indent=2)
    f.write("\n")

print("Generated outputs/batch_accommodations_photos.json with 40 entries!")
