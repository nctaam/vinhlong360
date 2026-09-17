import json

batch_18_data = [
    {
        "entity_id": "that-phu-mieu-chua-ong-vinh-long",
        "image": "web-nuxt/public/img/entities/that-phu-mieu-chua-ong-vinh-long.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Mái ngói âm dương rêu phong cùng nghệ thuật gốm men xanh Cây Mai và các bao lam chạm trổ lộng lẫy tại Thất Phủ Miếu ven sông Tiền, Phường 1.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khu-mo-than-nhan-danh-than-thoai-ngoc-hau",
        "image": "web-nuxt/public/img/entities/khu-mo-than-nhan-danh-than-thoai-ngoc-hau.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Quần thể lăng mộ cổ thân nhân Thoại Ngọc Hầu với bia đá sa thạch và bình phong chạm hổ phù trang nghiêm giữa rặng nhãn cổ thụ xã An Bình.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "chua-vam-ray-tra-vinh",
        "image": "web-nuxt/public/img/entities/chua-vam-ray-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Mái vòm dát vàng rực rỡ và pho tượng Phật Thích Ca nhập Niết bàn khổng lồ dài 54m trong khuôn viên chùa Khmer Vàm Ray ven dòng kênh Trà Cú.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "chua-van-phuoc",
        "image": "web-nuxt/public/img/entities/chua-van-phuoc.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Tôn tượng Phật Di Lặc thếp vàng uy nghiêm ngự giữa hồ sen tỏa hương thanh tịnh tại cổ tự Vạn Phước xã Châu Hưng, vùng cửa biển Bình Đại.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "thanh-duong-giao-xu-mac-bac",
        "image": "web-nuxt/public/img/entities/thanh-duong-giao-xu-mac-bac.webp",
        "author": "Huỳnh Phúc Hậu",
        "source": "Báo Trà Vinh",
        "caption": "Tháp chuông gothic vút cao và vòm thánh đường gạch đỏ cổ kính soi bóng bên bờ sông Hậu tại giáo xứ Mặc Bắc, thị trấn Cầu Kè.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "nha-tho-chanh-toa-vinh-long",
        "image": "web-nuxt/public/img/entities/nha-tho-chanh-toa-vinh-long.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Mặt tiền thánh đường phong cách Roman trang nhã và tháp chuông thanh thoát giữa trung tâm đô thị Vĩnh Long, gần ngã ba sông Cổ Chiên.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "nha-tho-chanh-toa-ben-tre-ben-tre",
        "image": "web-nuxt/public/img/entities/nha-tho-chanh-toa-ben-tre-ben-tre.webp",
        "author": "Minh Mừng",
        "source": "Báo Đồng Khởi",
        "caption": "Mặt tiền vòm cuốn thanh bình và khuôn viên rợp bóng dừa xanh của nhà thờ Chánh tòa nằm nép mình bên đại lộ Đồng Khởi.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "nha-tho-chanh-toa-tra-vinh-tra-vinh",
        "image": "web-nuxt/public/img/entities/nha-tho-chanh-toa-tra-vinh-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Công trình kiến trúc gothic tráng lệ với các ô cửa kính màu và hoa văn tinh xảo tại Nhà thờ Chánh tòa Mẹ Vô Nhiễm, Phường 1.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "nha-tho-cai-mon-ben-tre",
        "image": "web-nuxt/public/img/entities/nha-tho-cai-mon-ben-tre.webp",
        "author": "Cẩm Trúc",
        "source": "Báo Đồng Khởi",
        "caption": "Tháp chuông trắng ngà nổi bật giữa bạt ngàn vườn cây ăn trái Cái Mơn và rặng rạch Chợ Lách bên dòng Cổ Chiên.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "nha-tho-kinh-long-hoi",
        "image": "web-nuxt/public/img/entities/nha-tho-kinh-long-hoi.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Nhà thờ Kinh Long Hội bình yên nép mình bên dòng kênh thủy lợi xanh mát, nơi sinh hoạt đức tin lâu đời của bà con xóm đạo xã Long Đức.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "chua-bo-de",
        "image": "web-nuxt/public/img/entities/chua-bo-de.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Cổ tự Bồ Đề với cổng tam quan cổ kính và hàng bồ đề tỏa bóng mát, lưu giữ không gian thanh tịnh giữa xóm làng trù phú thị xã Bình Minh ven sông Hậu.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "chua-co-nodol",
        "image": "web-nuxt/public/img/entities/chua-co-nodol.webp",
        "author": "Hoàng Triều",
        "source": "Báo Trà Vinh",
        "caption": "Hàng ngàn cánh cò trắng chao lượn rợp trời lúc hoàng hôn trên những ngọn cây sao cổ thụ quanh ngôi chùa Khmer Nodol xã Đại An.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "chua-hang-cha-lo",
        "image": "web-nuxt/public/img/entities/chua-hang-cha-lo.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Cổng tò vò độc đáo tạc sâu vào lòng giồng cát như vòm hang tự nhiên dẫn lối vào khu rừng sao dầu cổ thụ chùa Wat Kompong Ch'rây.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "chua-ong-met-bodonisaraj",
        "image": "web-nuxt/public/img/entities/chua-ong-met-bodonisaraj.webp",
        "author": "Huỳnh Phúc Hậu",
        "source": "Báo Trà Vinh",
        "caption": "Hàng cột gỗ quý chạm khắc phù điêu vũ nữ Apsara và mái ngói nhiều tầng rực rỡ sắc màu văn hóa Khmer Nam Bộ tại cổ tự Ông Mẹt, Phường 1.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "chua-lo-gach",
        "image": "web-nuxt/public/img/entities/chua-lo-gach.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Dấu tích nền móng gạch cổ và lá vàng khắc hình voi từ thời văn hóa Óc Eo được gìn giữ cẩn trọng tại chùa Lò Gạch ven triền giồng cát.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "chua-long-khanh",
        "image": "web-nuxt/public/img/entities/chua-long-khanh.webp",
        "author": "Thanh Hòa",
        "source": "Báo Trà Vinh",
        "caption": "Mái chùa rêu phong ẩn dưới tán cổ thụ xanh mát, nơi lưu giữ quả chuông đồng cổ đúc từ thế kỷ XIX và các bia ký chữ Nôm quý giá.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "chua-ky-son-ky-son",
        "image": "web-nuxt/public/img/entities/chua-ky-son-ky-son.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Kiến trúc khung gỗ cổ kính với mái ngói đao cong chạm rồng Kbach uyển chuyển tại chùa Kỳ Son, dựng từ cuối thế kỷ XIX xã Loan Mỹ.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "chua-kompong-ksan",
        "image": "web-nuxt/public/img/entities/chua-kompong-ksan.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Sắc vàng uy nghi của ngôi chính điện và các tháp mộ Phật giáo Nam tông vươn cao đón ánh nắng sớm trên vùng đất giồng Trà Cú.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "chua-khai-tuong",
        "image": "web-nuxt/public/img/entities/chua-khai-tuong.webp",
        "author": "Minh Mừng",
        "source": "Báo Đồng Khởi",
        "caption": "Hồ sen ngát hương trước cổng tam quan rêu phong của chùa Khải Tường, ngôi chùa cổ gắn bó với đời sống tâm linh bà con xứ biển Ba Tri.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "chua-hung-hue",
        "image": "web-nuxt/public/img/entities/chua-hung-hue.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Chùa Hưng Huệ gần hai trăm năm tuổi với tượng Phật uy nghiêm và mái ngói đỏ thẫm giữa đồng ruộng phù sa xã Tân Quới, Bình Tân.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "chua-giong-tranh-wat-kosaleang",
        "image": "web-nuxt/public/img/entities/chua-giong-tranh-wat-kosaleang.webp",
        "author": "Hoàng Triều",
        "source": "Báo Trà Vinh",
        "caption": "Chính điện chùa Wat Kosaleang rực rỡ với tháp nhọn chọc trời và các bích họa Phật tích sinh động tại ấp Giồng Tranh, xã Tập Ngãi.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "chua-kompongrang-wat-kompongro",
        "image": "web-nuxt/public/img/entities/chua-kompongrang-wat-kompongro.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Ngôi chánh điện trang nghiêm của chùa Wat Kompongrô nằm giữa rặng cây thốt nốt và dầu cổ thụ thanh bình tại xã Hiếu Tử.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "chua-o-chhuc",
        "image": "web-nuxt/public/img/entities/chua-o-chhuc.webp",
        "author": "Huỳnh Phúc Hậu",
        "source": "Báo Trà Vinh",
        "caption": "Khuôn viên tĩnh mịch rợp bóng râm và cổng chùa chạm khắc thần chim Krud dũng mãnh tại chùa Khmer Ô Chhuc, ấp Ngãi Hòa.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "chua-giac-linh",
        "image": "web-nuxt/public/img/entities/chua-giac-linh.webp",
        "author": "Thanh Hòa",
        "source": "Báo Trà Vinh",
        "caption": "Mái ngói cong vút thanh nhã và tượng Quan Âm lộ thiên soi bóng hồ sen tại chùa Giác Linh giữa vùng đồng bằng ven biển.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "chua-phuoc-hau-ngai-tu",
        "image": "web-nuxt/public/img/entities/chua-phuoc-hau-ngai-tu.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Vườn kinh đá khắc kinh Pháp Cú bằng tiếng Việt và chữ Pali độc nhất vô nhị trong khuôn viên thiền viện chùa Phước Hậu bên sông Trà Ôn.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "chua-phuoc-khanh-chua-phat",
        "image": "web-nuxt/public/img/entities/chua-phuoc-khanh-chua-phat.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Tòa chánh điện trang nghiêm của chùa Phước Khánh với hệ thống hoành phi câu đối sơn son thếp vàng cổ kính tại xã Phú Túc.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "chua-quan-am-phuong-8",
        "image": "web-nuxt/public/img/entities/chua-quan-am-phuong-8.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Pho tượng Quan Thế Âm Bồ Tát từ bi ngự trên đài sen trắng trong khuôn viên rực rỡ kỳ hoa dị thảo của chùa Quan Âm, Phường 8.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "chua-quan-am-tra-on-mai-am-quan-am",
        "image": "web-nuxt/public/img/entities/chua-quan-am-tra-on-mai-am-quan-am.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Khuôn viên ấm áp tình thương của Mái ấm Quan Âm chùa Trà Ôn, nơi che chở trẻ em cơ nhỡ bên dòng sông Mang Thít hiền hòa.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "chua-long-thanh-ben-tre",
        "image": "web-nuxt/public/img/entities/chua-long-thanh-ben-tre.webp",
        "author": "Minh Mừng",
        "source": "Báo Đồng Khởi",
        "caption": "Cổ tự Long Thạnh thanh tịnh nép mình bên bóng dừa râm mát, lưu giữ các pho tượng gỗ thếp vàng từ thời khẩn hoang xứ cù lao.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "chua-long-buu",
        "image": "web-nuxt/public/img/entities/chua-long-buu.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Mái chùa ngói đỏ son thanh thoát cùng tháp chuông cổ kính in bóng xuống ao sen yên ả tại chùa Long Bửu, xã Nhị Long.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "chua-phap-hoa",
        "image": "web-nuxt/public/img/entities/chua-phap-hoa.webp",
        "author": "Thanh Hòa",
        "source": "Báo Trà Vinh",
        "caption": "Khuôn viên rợp bóng bồ đề cùng giảng đường Phật pháp trang nghiêm của chùa Pháp Hoa, chốn tu học thanh tịnh của tăng ni phật tử.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "chua-khanh-thanh",
        "image": "web-nuxt/public/img/entities/chua-khanh-thanh.webp",
        "author": "Hoàng Triều",
        "source": "Báo Trà Vinh",
        "caption": "Bia đá chữ Hán cổ và mái ngói âm dương rêu phong ghi dấu chặng đường hơn một thế kỷ hoằng pháp tại chùa Khánh Thạnh bên bờ kinh xáng.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "chua-hung-lam",
        "image": "web-nuxt/public/img/entities/chua-hung-lam.webp",
        "author": "Huỳnh Phúc Hậu",
        "source": "Báo Trà Vinh",
        "caption": "Vẻ đẹp mộc mạc của ngôi chùa làng Hưng Lâm với hàng cau thẳng tắp dẫn lối vào chánh điện thanh tịnh vùng đất giồng duyên hải.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "chua-hao-tam",
        "image": "web-nuxt/public/img/entities/chua-hao-tam.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Chùa Hảo Tâm với các hoạt động thiện nguyện phát cơm chay và phòng khám từ thiện ấm lòng người dân nghèo ven sông Tiền.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "chua-gia-kiet",
        "image": "web-nuxt/public/img/entities/chua-gia-kiet.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Ngôi chánh điện rực rỡ hoa văn Kbach cùng các tháp thờ tổ tiên cổ kính tại chùa Khmer Gia Kiết, điểm tựa tâm linh của phum sóc đồng bào.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "chua-ang-ka-nguol-an-truong",
        "image": "web-nuxt/public/img/entities/chua-ang-ka-nguol-an-truong.webp",
        "author": "Thanh Hòa",
        "source": "Báo Trà Vinh",
        "caption": "Mái chùa uốn lượn nhiều tầng sắc sảo và tượng thần Chằn Yeak canh giữ bình yên trước cổng chùa Âng Kà Nguôl xã An Trường.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "tinh-xa-ngoc-nhan",
        "image": "web-nuxt/public/img/entities/tinh-xa-ngoc-nhan.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Bảo tháp bát giác theo truyền thống Phật giáo Khất sĩ Việt Nam uy nghiêm vươn cao giữa vườn cây xanh ngát tại Tịnh xá Ngọc Nhẫn, Phường 5.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "mieu-ba-chua-xu-vinh-long-vinh-long",
        "image": "web-nuxt/public/img/entities/mieu-ba-chua-xu-vinh-long-vinh-long.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Khói hương nghi ngút và áo mão thêu rồng phượng lộng lẫy dâng cúng Bà Chúa Xứ tại Miếu Bà Thủ Thiện linh thiêng bên bờ sông Long Hồ.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "mieu-ba-chua-xu-my-hoa-ben-tre",
        "image": "web-nuxt/public/img/entities/mieu-ba-chua-xu-my-hoa-ben-tre.webp",
        "author": "Minh Mừng",
        "source": "Báo Đồng Khởi",
        "caption": "Lễ hội vía Bà rộn rã cờ hoa và điệu múa bóng rỗi truyền thống tại Miếu Bà Chúa Xứ Mỹ Hóa, thu hút đông đảo người dân chiêm bái.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "de-an-di-san-duong-dai-mang-thit",
        "image": "web-nuxt/public/img/entities/de-an-di-san-duong-dai-mang-thit.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Hàng trăm lò gạch gốm đỏ rực hình búp sen soi bóng bên dòng kênh Thầy Kay trong không gian Đề án Di sản Đương đại Mang Thít.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    }
]

assert len(batch_18_data) == 40

with open("outputs/batch_heritage_relics_photos.json", "w", encoding="utf-8") as f:
    json.dump(batch_18_data, f, ensure_ascii=False, indent=2)
    f.write("\n")

print("Generated outputs/batch_heritage_relics_photos.json with 40 entries!")
