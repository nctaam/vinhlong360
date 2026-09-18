import json

batch_46_data = [
    {
        "entity_id": "xa-cho-lach",
        "image": "web-nuxt/public/img/entities/xa-cho-lach.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Vương quốc hoa kiểng và cây giống Cái Mơn rực rỡ sắc màu dọc tuyến Quốc lộ 57 tại Xã Chợ Lách.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "xa-dai-an",
        "image": "web-nuxt/public/img/entities/xa-dai-an.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Chùa Cò Nodol cổ kính với hàng nghìn cánh chim bay rợp trời trong rặng sao dầu thanh tịnh tại Xã Đại An.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "xa-dai-dien",
        "image": "web-nuxt/public/img/entities/xa-dai-dien.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Nhà cổ Huỳnh Phủ chạm trổ gỗ lim tinh xảo ghi dấu ấn văn hóa trăm năm của vùng đất Thạnh Phú tại Xã Đại Điền.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "xa-don-chau",
        "image": "web-nuxt/public/img/entities/xa-don-chau.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Cánh đồng màu dưa hấu và đậu phộng trĩu hạt trên giồng cát ven biển duyên hải tại Xã Đôn Châu.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "xa-dong-hai",
        "image": "web-nuxt/public/img/entities/xa-dong-hai.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Rừng đước ngập mặn xanh bạt ngàn ôm trọn các vuông tôm sinh thái bền vững tại Xã Đông Hải.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "xa-dong-khoi",
        "image": "web-nuxt/public/img/entities/xa-dong-khoi.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Khu di tích lịch sử Quốc gia đặc biệt Đồng Khởi ngọn cờ đầu phong trào cách mạng miền Nam tại Xã Đồng Khởi.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "xa-giao-long",
        "image": "web-nuxt/public/img/entities/xa-giao-long.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Khu công nghiệp Giao Long và cảng sông nhộn nhịp đón tàu thuyền vận chuyển dừa hàng hóa tại Xã Giao Long.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "xa-giong-trom",
        "image": "web-nuxt/public/img/entities/xa-giong-trom.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Phố thị trung tâm sầm uất với đền thờ nữ tướng Nguyễn Thị Định anh hùng tại Xã Giồng Trôm.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "xa-ham-giang",
        "image": "web-nuxt/public/img/entities/xa-ham-giang.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Làng nghề đan chiếu Cà Hôn truyền thống gìn giữ tinh hoa thủ công của đồng bào dân tộc tại Xã Hàm Giang.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "xa-hau-loc",
        "image": "web-nuxt/public/img/entities/xa-hau-loc.webp",
        "author": "Thanh Đức",
        "source": "Báo Vĩnh Long",
        "caption": "Cánh đồng màu xen canh rau sạch và các vườn cam sành sum suê trĩu quả tại Xã Hậu Lộc.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "xa-hiep-my",
        "image": "web-nuxt/public/img/entities/xa-hiep-my.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Vùng nuôi nghêu lụa và tôm càng xanh chất lượng cao đạt chuẩn xuất khẩu tại Xã Hiệp Mỹ ven biển Cầu Ngang.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "xa-hieu-phung",
        "image": "web-nuxt/public/img/entities/xa-hieu-phung.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Các tuyến đường nông thôn mới kiểu mẫu rợp bóng hoa mười giờ và bưởi da xanh tại Xã Hiếu Phụng.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "xa-hieu-thanh",
        "image": "web-nuxt/public/img/entities/xa-hieu-thanh.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Đồng lúa trĩu bông phù sa và các mô hình kinh tế vườn đồi trang trại tiêu biểu tại Xã Hiếu Thành.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "xa-hoa-binh",
        "image": "web-nuxt/public/img/entities/xa-hoa-binh.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Những luống cam sành hữu cơ chuẩn GlobalGAP mọng nước ven các kênh rạch tại Xã Hòa Bình huyện Trà Ôn.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "xa-hoa-hiep",
        "image": "web-nuxt/public/img/entities/xa-hoa-hiep.webp",
        "author": "Thanh Đức",
        "source": "Báo Vĩnh Long",
        "caption": "Làng nghề đan đan lát bèo tây lục bình xuất khẩu tạo việc làm ổn định cho hàng nghìn hộ dân tại Xã Hòa Hiệp.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "xa-hoa-minh",
        "image": "web-nuxt/public/img/entities/xa-hoa-minh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Ốc đảo Cồn Chim với mô hình du lịch sinh thái nông nghiệp thuận thiên tôm lúa độc đáo tại Xã Hòa Minh.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "xa-hung-khanh-trung",
        "image": "web-nuxt/public/img/entities/xa-hung-khanh-trung.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Vườn kiểng thú và cây cảnh uốn lượn nghệ thuật đạt tầm quốc gia của các nghệ nhân Chợ Lách tại Xã Hưng Khánh Trung.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "xa-hung-my",
        "image": "web-nuxt/public/img/entities/xa-hung-my.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Chùa Hang (Kompong Chray) với khuôn viên rừng cây cổ thụ hàng trăm năm tuổi tại Xã Hưng Mỹ.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "xa-hung-nhuong",
        "image": "web-nuxt/public/img/entities/xa-hung-nhuong.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Làng nghề bánh phồng Sơn Đốc trứ danh thơm nức hương nếp dừa nướng trên bếp than hồng tại Xã Hưng Nhượng.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "xa-huong-my",
        "image": "web-nuxt/public/img/entities/xa-huong-my.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Những rặng dừa xiêm trĩu quả soi bóng bờ kênh và cụm đền thờ anh hùng liệt sĩ tại Xã Hương Mỹ.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "xa-loc-thuan",
        "image": "web-nuxt/public/img/entities/xa-loc-thuan.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Cánh đồng màu và vùng nuôi trồng thủy sản nước lợ công nghệ cao dọc sông Ba Lai tại Xã Lộc Thuận.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "xa-long-hiep",
        "image": "web-nuxt/public/img/entities/xa-long-hiep.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Các ngôi chùa Nam tông Khmer lộng lẫy và ngày hội văn hóa truyền thống rộn ràng tại Xã Long Hiệp.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "xa-long-hoa",
        "image": "web-nuxt/public/img/entities/xa-long-hoa.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Khu du lịch cộng đồng Cồn Hô nơi du khách trải nghiệm bơi xuồng ngắm vườn bưởi da xanh tại Xã Long Hòa.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "xa-long-huu",
        "image": "web-nuxt/public/img/entities/xa-long-huu.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Cánh đồng muối Ba Động và các cơ sở chế biến muối tôm đậm đà hương vị biển tại Xã Long Hữu.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "xa-long-thanh",
        "image": "web-nuxt/public/img/entities/xa-long-thanh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Cảng trung chuyển hải sản và các cánh đồng điện gió vươn cao trên nền trời duyên hải tại Xã Long Thành.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "xa-long-vinh",
        "image": "web-nuxt/public/img/entities/xa-long-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Vùng rừng ngập mặn đước vẹt bảo vệ đê biển và các trang trại nuôi tôm thâm canh tại Xã Long Vĩnh.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "xa-luc-si-thanh",
        "image": "web-nuxt/public/img/entities/xa-luc-si-thanh.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Cù lao Mây xanh mát giữa lòng sông Hậu với đặc sản bánh tráng nem và trái cây ngọt lành tại Xã Lục Sĩ Thành.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "xa-luong-hoa",
        "image": "web-nuxt/public/img/entities/xa-luong-hoa.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Quê hương bà Định với đền thờ tưởng niệm trang nghiêm giữa bóng dừa xanh mát tại Xã Lương Hòa.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "xa-luong-phu",
        "image": "web-nuxt/public/img/entities/xa-luong-phu.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Đường làng liên ấp rợp bóng cây xanh và nghề thủ công thắt giỏ cọng dừa tại Xã Lương Phú.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "xa-luu-nghiep-anh",
        "image": "web-nuxt/public/img/entities/xa-luu-nghiep-anh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Làng nghề dệt chiếu cói truyền thống và các ngôi chùa Phật giáo Nam tông tại Xã Lưu Nghiệp Anh.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "xa-my-chanh-hoa",
        "image": "web-nuxt/public/img/entities/xa-my-chanh-hoa.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Đồng lúa phì nhiêu Ba Tri xen lẫn những rặng dừa xiêm và nghề làm nón lá truyền thống tại Xã Mỹ Chánh Hòa.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "xa-my-long",
        "image": "web-nuxt/public/img/entities/xa-my-long.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Lễ hội Nghinh Ông sôi nổi và bến cảng hải sản tấp nập thuyền bè ven sông Cung Hầu tại Xã Mỹ Long.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "xa-my-thuan",
        "image": "web-nuxt/public/img/entities/xa-my-thuan.webp",
        "author": "Thanh Đức",
        "source": "Báo Vĩnh Long",
        "caption": "Cánh đồng lúa chất lượng cao kết hợp trồng luân canh khoai lang và bắp ngọt tại Xã Mỹ Thuận huyện Bình Tân.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "xa-ngai-tu",
        "image": "web-nuxt/public/img/entities/xa-ngai-tu.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Vùng bưởi Năm Roi ngọt thanh và xóm làng bình yên ven nhánh sông Trà Ôn tại Xã Ngãi Tứ.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "xa-ngu-lac",
        "image": "web-nuxt/public/img/entities/xa-ngu-lac.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Những ngôi chùa tháp Khmer uy nghi trên giồng cát và các vuông tôm công nghiệp hiện đại tại Xã Ngũ Lạc.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "xa-nhi-long",
        "image": "web-nuxt/public/img/entities/xa-nhi-long.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Cồn cát tự nhiên Cồn Cù và làng nghề dệt chiếu dừa xanh mát tại Xã Nhị Long bên sông Cổ Chiên.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "xa-nhi-truong",
        "image": "web-nuxt/public/img/entities/xa-nhi-truong.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Cộng đồng Khmer gìn giữ nghề dệt thổ cẩm và các lễ hội văn hóa Phật giáo truyền thống tại Xã Nhị Trường.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "xa-nhon-phu",
        "image": "web-nuxt/public/img/entities/xa-nhon-phu.webp",
        "author": "Ngọc Trảng",
        "source": "Báo Vĩnh Long",
        "caption": "Cụm tháp lò gạch đỏ cổ kính sừng sững bên dòng sông Mang Thít hiền hòa tại Xã Nhơn Phú.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "xa-nhuan-phu-tan",
        "image": "web-nuxt/public/img/entities/xa-nhuan-phu-tan.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Vùng chuyên canh dừa hữu cơ đạt tiêu chuẩn xuất khẩu và cơ sở đóng tàu thuyền tại Xã Nhuận Phú Tân.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "xa-phong-thanh",
        "image": "web-nuxt/public/img/entities/xa-phong-thanh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Những rặng dừa sáp trĩu cành bên cánh đồng lúa hai vụ trù phú tại Xã Phong Thạnh huyện Cầu Kè.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    }
]

assert len(batch_46_data) == 40

with open('outputs/batch_46_photos.json', 'w', encoding='utf-8') as f:
    json.dump(batch_46_data, f, ensure_ascii=False, indent=2)
    f.write('\n')

print('Generated outputs/batch_46_photos.json with 40 entries!')
