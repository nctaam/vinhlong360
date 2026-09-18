import json

batch_45_data = [
    {
        "entity_id": "p-long-duc",
        "image": "web-nuxt/public/img/entities/p-long-duc.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Khu di tích Đền thờ Bác Hồ rợp bóng cây xanh và các tuyến đường nhựa liên khóm khang trang tại Phường Long Đức.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "p-long-ho",
        "image": "web-nuxt/public/img/entities/p-long-ho.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Trung tâm hành chính và phố thị ven sông Long Hồ với những vườn cây ăn trái sum suê tại Phường Long Hồ.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "p-mo-cay",
        "image": "web-nuxt/public/img/entities/p-mo-cay.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Nhịp sống giao thương nhộn nhịp trên bến dưới thuyền của làng nghề sản xuất chỉ xơ dừa tại Phường Mỏ Cày.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "p-nguyet-hoa",
        "image": "web-nuxt/public/img/entities/p-nguyet-hoa.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Quần thể danh thắng Ao Bà Om thanh tịnh và các trường học, khu dân cư sầm uất tại Phường Nguyệt Hóa.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "p-phu-khuong",
        "image": "web-nuxt/public/img/entities/p-phu-khuong.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Đại lộ Đồng Khởi khang trang với các cơ quan hành chính, ngân hàng và khu thương mại tại Phường Phú Khương.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "p-phu-tan",
        "image": "web-nuxt/public/img/entities/p-phu-tan.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Khu đô thị mới mở rộng với các trục đường giao thông liên vùng thông thoáng tại Phường Phú Tân.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "p-phu-tuc",
        "image": "web-nuxt/public/img/entities/p-phu-tuc.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Cầu Rạch Miễu bắc qua sông Tiền kết nối giao thông cửa ngõ miệt vườn rợp bóng dừa tại Phường Phú Túc.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "p-phuoc-hau",
        "image": "web-nuxt/public/img/entities/p-phuoc-hau.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Khu dân cư hiện đại kết hợp không gian sinh thái ven kênh rạch phù sa tại Phường Phước Hậu thành phố Vĩnh Long.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "p-son-dong",
        "image": "web-nuxt/public/img/entities/p-son-dong.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Những vườn dừa xanh tốt xen kẽ cơ sở tiểu thủ công nghiệp và khu dân cư phát triển tại Phường Sơn Đông.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "p-tam-binh",
        "image": "web-nuxt/public/img/entities/p-tam-binh.webp",
        "author": "Thanh Đức",
        "source": "Báo Vĩnh Long",
        "caption": "Vựa cam sành Tam Bình mọng nước nức tiếng dọc theo dòng sông Măng Thít tại trung tâm Phường Tam Bình.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "p-tan-hanh",
        "image": "web-nuxt/public/img/entities/p-tan-hanh.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Các tuyến đường giao thông kết nối Khu công nghiệp Hòa Phú và vùng nông thôn mới ngoại thành tại Phường Tân Hạnh.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "p-tan-hoa",
        "image": "web-nuxt/public/img/entities/p-tan-hoa.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Bến phà Cầu Quan và các cơ sở đóng tàu gỗ truyền thống ven sông Hậu tại Phường Tân Hòa.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "p-tan-ngai",
        "image": "web-nuxt/public/img/entities/p-tan-ngai.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Khu du lịch Trường An và cầu Mỹ Thuận sừng sững bắc qua sông Tiền tại cửa ngõ Phường Tân Ngãi.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "p-tan-quoi",
        "image": "web-nuxt/public/img/entities/p-tan-quoi.webp",
        "author": "Thanh Đức",
        "source": "Báo Vĩnh Long",
        "caption": "Thủ phủ khoai lang Bình Tân trù phú với những cánh đồng xanh mướt ngút ngàn tại Phường Tân Quới.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "p-tan-thuy",
        "image": "web-nuxt/public/img/entities/p-tan-thuy.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Cảng cá Tiệm Tôm sầm uất và các cánh đồng làm muối trắng tinh khiết ven biển tại Phường Tân Thủy.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "p-tap-ngai",
        "image": "web-nuxt/public/img/entities/p-tap-ngai.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Những ngôi chùa Khmer rực rỡ sắc vàng soi bóng bên cánh đồng lúa hai vụ trĩu hạt tại Phường Tập Ngãi.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "p-thanh-duc",
        "image": "web-nuxt/public/img/entities/p-thanh-duc.webp",
        "author": "Ngọc Trảng",
        "source": "Báo Vĩnh Long",
        "caption": "Vương quốc gốm đỏ nung nức tiếng với hàng trăm lò gạch cổ kính dọc kênh Thầy Cai tại Phường Thanh Đức.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "p-tien-thuy",
        "image": "web-nuxt/public/img/entities/p-tien-thuy.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Vùng chuyên canh sầu riêng và măng cụt Cái Mơn xanh ngút ngàn dọc theo sông Ba Lai tại Phường Tiên Thủy.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "p-tieu-can",
        "image": "web-nuxt/public/img/entities/p-tieu-can.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Khu trung tâm thương mại huyện lỵ sầm uất trên tuyến Quốc lộ 60 kết nối liên tỉnh tại Phường Tiểu Cần.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "p-tra-on",
        "image": "web-nuxt/public/img/entities/p-tra-on.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Bến sông tấp nập chợ nổi và công viên bờ kè lộng gió ven sông Hậu tại trung tâm Phường Trà Ôn.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "p-tra-vinh",
        "image": "web-nuxt/public/img/entities/p-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Đô thị xanh cổ thụ rợp bóng mát cây sao, dầu hàng trăm năm tuổi tại trung tâm Phường Trà Vinh.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "p-truong-long-hoa",
        "image": "web-nuxt/public/img/entities/p-truong-long-hoa.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Bãi biển Ba Động cát mịn thoai thoải và rừng phi lao chắn sóng ngút ngàn tại Phường Trường Long Hòa.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "p-vung-liem",
        "image": "web-nuxt/public/img/entities/p-vung-liem.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Khu tưởng niệm cố Thủ tướng Võ Văn Kiệt và công viên tượng đài trang nghiêm tại Phường Vũng Liêm.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "vinh-long",
        "image": "web-nuxt/public/img/entities/vinh-long.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Bản đồ không gian địa lý và hệ thống sông ngòi kênh rạch trù phú của tỉnh Vĩnh Long mới theo mô hình 2 cấp.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "xa-an-binh",
        "image": "web-nuxt/public/img/entities/xa-an-binh.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Cù lao bốn mùa trĩu quả chôm chôm, sầu riêng và hệ thống homestay miệt vườn nổi tiếng tại Xã An Bình.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "xa-an-dinh",
        "image": "web-nuxt/public/img/entities/xa-an-dinh.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Cánh đồng dừa bạt ngàn và cơ sở chế biến đặc sản kẹo dừa thủ công truyền thống tại Xã An Định.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "xa-an-hiep",
        "image": "web-nuxt/public/img/entities/xa-an-hiep.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Vùng nuôi bò thịt chất lượng cao Ba Tri và đồng lúa trĩu bông phù sa tại Xã An Hiệp.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "xa-an-ngai-trung",
        "image": "web-nuxt/public/img/entities/xa-an-ngai-trung.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Làng nghề đan đan lát mây tre truyền thống và những rặng dừa xanh mát rợp bóng tại Xã An Ngãi Trung.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "xa-an-phu-tan",
        "image": "web-nuxt/public/img/entities/xa-an-phu-tan.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Cồn Tân Quy phù sa màu mỡ nổi tiếng với mùa trái cây sầu riêng, chôm chôm trĩu cành tại Xã An Phú Tân.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "xa-an-qui",
        "image": "web-nuxt/public/img/entities/xa-an-qui.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Khu nuôi tôm sú sinh thái công nghệ cao và rừng ngập mặn ven biển Thạnh Phú tại Xã An Qui.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "xa-an-truong",
        "image": "web-nuxt/public/img/entities/xa-an-truong.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Làng nghề dệt chiếu cói Cà Hôn nức tiếng lưu giữ hoa văn cổ truyền độc đáo tại Xã An Trường.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "xa-bao-thanh",
        "image": "web-nuxt/public/img/entities/xa-bao-thanh.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Cồn cát ven biển đón gió Đông và nghề làm muối truyền thống của ngư dân tại Xã Bảo Thạnh.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "xa-binh-phu",
        "image": "web-nuxt/public/img/entities/xa-binh-phu.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Các xưởng thủ công mỹ nghệ chạm khắc gỗ và đan lục bình xuất khẩu tại Xã Bình Phú huyện Càng Long.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "xa-binh-phuoc",
        "image": "web-nuxt/public/img/entities/xa-binh-phuoc.webp",
        "author": "Ngọc Trảng",
        "source": "Báo Vĩnh Long",
        "caption": "Hàng nghìn lò gạch nung đỏ rực soi bóng xuống dòng sông Măng Thít tại Xã Bình Phước.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "xa-cai-nhum",
        "image": "web-nuxt/public/img/entities/xa-cai-nhum.webp",
        "author": "Ngọc Trảng",
        "source": "Báo Vĩnh Long",
        "caption": "Thị trấn lò gạch Mang Thít cổ kính bên bờ kênh Thầy Cai thuộc vùng di sản đương đại tại Xã Cái Nhum.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "xa-cau-ke",
        "image": "web-nuxt/public/img/entities/xa-cau-ke.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Vương quốc dừa sáp Cầu Kè trĩu quả và văn hóa lễ hội Vu Lan Thắng Hội đặc sắc tại Xã Cầu Kè.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "xa-cau-ngang",
        "image": "web-nuxt/public/img/entities/xa-cau-ngang.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Đặc sản bánh tét Trà Cuôn gia truyền thơm nức nổi danh khắp ba miền tại Xã Cầu Ngang.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "xa-chau-hoa",
        "image": "web-nuxt/public/img/entities/xa-chau-hoa.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Vùng quê cách mạng Giồng Trôm với những rặng dừa xiêm xanh tốt và làng bánh tráng Mỹ Lồng tại Xã Châu Hòa.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "xa-chau-hung",
        "image": "web-nuxt/public/img/entities/xa-chau-hung.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Mô hình tôm lúa xen canh bền vững và vườn cây ăn trái sum suê tại Xã Châu Hưng.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "xa-chau-thanh",
        "image": "web-nuxt/public/img/entities/xa-chau-thanh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Những cánh đồng lúa chất lượng cao và ngôi chùa Hang cổ kính rợp bóng cây xanh tại Xã Châu Thành.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    }
]

assert len(batch_45_data) == 40

with open('outputs/batch_45_photos.json', 'w', encoding='utf-8') as f:
    json.dump(batch_45_data, f, ensure_ascii=False, indent=2)
    f.write('\n')

print('Generated outputs/batch_45_photos.json with 40 entries!')
