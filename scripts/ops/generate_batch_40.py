import json

batch_40_data = [
    # 40 Attraction Entities (Batch 40)
    {
        "entity_id": "nha-co-tran-dai-nghia",
        "image": "web-nuxt/public/img/entities/nha-co-tran-dai-nghia.webp",
        "author": "Thanh Đức",
        "source": "Báo Vĩnh Long",
        "caption": "Ngôi nhà cổ nơi Giáo sư Viện sĩ Trần Đại Nghĩa chào đời tại xã Tường Lộc, công trình lưu giữ những ký vật thời niên thiếu của nhà khoa học quân giới lỗi lạc.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "diem-du-lich-sinh-thai-tu-do",
        "image": "web-nuxt/public/img/entities/diem-du-lich-sinh-thai-tu-do.webp",
        "author": "Ngọc Trảng",
        "source": "Báo Vĩnh Long",
        "caption": "Vườn chôm chôm chín đỏ trĩu cành trên đất cồn Công tại Điểm du lịch sinh thái Tư Dô, điểm ghé thăm miệt vườn trải nghiệm hái trái cây ngọt lành.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "diem-du-lich-sinh-thai-tam-trong",
        "image": "web-nuxt/public/img/entities/diem-du-lich-sinh-thai-tam-trong.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Những rặng cây ăn trái sum suê rợp mát bao quanh ao cá dân dã tại Điểm du lịch sinh thái Tám Trong đầu cồn Công, nét thanh bình đặc trưng miệt vườn cù lao.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khu-du-lich-sinh-thai-miet-vuon-vinh-sang",
        "image": "web-nuxt/public/img/entities/khu-du-lich-sinh-thai-miet-vuon-vinh-sang.webp",
        "author": "Ngọc Trảng",
        "source": "Báo Vĩnh Long",
        "caption": "Khung cảnh vườn cây ăn trái rộng 2,2 hecta và hồ chèo xuồng giải trí bên dòng sông Cổ Chiên tại Khu du lịch sinh thái Vinh Sang xã An Bình.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "canh-dong-dien-gio-ngoai-khoi-ba-dong",
        "image": "web-nuxt/public/img/entities/canh-dong-dien-gio-ngoai-khoi-ba-dong.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Cụm turbine điện gió ngoài khơi Ba Động sừng sững trên nền sóng biển xanh ngắt, biểu tượng năng lượng sạch hiện đại của vùng duyên hải.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "cau-lang-chim",
        "image": "web-nuxt/public/img/entities/cau-lang-chim.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Cầu Láng Chim vắt ngang qua nhánh kênh rợp bóng rặng bần xanh rì tại xã Long Hữu, nơi ngắm nhìn những đàn chim trời chao lượn mỗi buổi chiều tà.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "cau-truong-long-hoa",
        "image": "web-nuxt/public/img/entities/cau-truong-long-hoa.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Cầu Trường Long Hòa nối liền dải đất ven biển với những rặng phi lao chắn sóng xanh ngát, tuyến giao thông huyết mạch đưa du khách ra bãi biển Ba Động.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "nha-co-huynh-thuy-le",
        "image": "web-nuxt/public/img/entities/nha-co-huynh-thuy-le.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Mặt tiền chạm khắc hoa văn phong cách kiến trúc Pháp - Hoa đầu thế kỷ 20 của Nhà cổ Huỳnh Thủy Lê, công trình kiến trúc nghệ thuật độc đáo bên dòng Sa Giang.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khu-van-hoa-du-lich-ao-ba-om",
        "image": "web-nuxt/public/img/entities/khu-van-hoa-du-lich-ao-ba-om.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Mặt hồ tĩnh lặng rợp bóng hàng sao dầu cổ thụ trăm năm tại Khu văn hóa du lịch Ao Bà Om phường Nguyệt Hóa, trung tâm tổ chức lễ hội Ok Om Bok rực rỡ.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "ao-ba-om",
        "image": "web-nuxt/public/img/entities/ao-ba-om.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Rễ cây sao dầu cổ thụ trồi lên mặt đất tạo nên những hình thù kỳ thú bao quanh bờ danh thắng quốc gia Ao Bà Om, điểm chiêm bái di sản thiên nhiên và văn hóa.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "bao-tang-dua-sap-tra-vinh",
        "image": "web-nuxt/public/img/entities/bao-tang-dua-sap-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Không gian trưng bày hình ảnh và hiện vật về nguồn gốc cây dừa sáp trăm năm tại Bảo tàng dừa sáp Cầu Kè, bảo tàng trái cây đầu tiên của vùng châu thổ.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "con-thanh-long-mo-cay-nam",
        "image": "web-nuxt/public/img/entities/con-thanh-long-mo-cay-nam.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Vườn dừa xanh bạt ngàn và mạng lưới kênh rạch tự nhiên trên dải cồn Thành Long rộng 111 hecta giữa dòng Cổ Chiên, điểm du lịch sinh thái miệt vườn hoang sơ.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "cho-dem-ben-tre",
        "image": "web-nuxt/public/img/entities/cho-dem-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Dãy hàng quán ẩm thực đêm rực rỡ ánh đèn tại Chợ đêm phường An Hội, nơi phục vụ các món chè dừa, bánh xèo và quà lưu niệm thủ công mỹ nghệ xứ dừa.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "lang-van-hoa-du-lich-khmer-tra-vinh",
        "image": "web-nuxt/public/img/entities/lang-van-hoa-du-lich-khmer-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Các gian nhà truyền thống và đường bích họa rực rỡ sắc màu tái hiện nếp sống cổ truyền tại Làng Văn hóa Du lịch Khmer bao quanh bờ Ao Bà Om.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "cho-thanh-phu",
        "image": "web-nuxt/public/img/entities/cho-thanh-phu.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Khu chợ truyền thống Thạnh Phú tấp nập thuyền ghe cập bến với tôm cua biển và nghêu sò tươi sống từ cửa sông Hàm Luông đưa về mỗi sáng.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "lang-nghe-tau-hu-ky-my-hoa",
        "image": "web-nuxt/public/img/entities/lang-nghe-tau-hu-ky-my-hoa.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Người thợ khéo léo vớt từng lớp váng đậu nành óng vàng trên chảo gang đỏ lửa tại Làng nghề tàu hũ ky Mỹ Hòa bên sông Cái Vồn, Di sản văn hóa phi vật thể quốc gia.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "bao-tang-van-hoa-dan-toc-khmer",
        "image": "web-nuxt/public/img/entities/bao-tang-van-hoa-dan-toc-khmer.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Kiến trúc mái cong truyền thống và hiện vật trang phục, nhạc cụ ngũ âm tại Bảo tàng Văn hóa dân tộc Khmer khánh thành năm 1997 tại khóm 4 phường Nguyệt Hóa.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "cang-ca-binh-thang",
        "image": "web-nuxt/public/img/entities/cang-ca-binh-thang.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Hàng chục tàu đánh bắt xa bờ cập bến tại Cảng cá Bình Thắng trong ánh bình minh, mang về những mẻ hải sản tươi rói cho thị trường đầu mối duyên hải.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "cong-vien-giong-trom",
        "image": "web-nuxt/public/img/entities/cong-vien-giong-trom.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Không gian cây xanh rợp bóng mát và đường dạo bộ thảnh thơi tại Công viên Giồng Trôm, lá phổi xanh giữa lòng thị trấn.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "rung-ngap-man-long-khanh",
        "image": "web-nuxt/public/img/entities/rung-ngap-man-long-khanh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Lối cầu ván gỗ len lỏi xuyên qua thảm rừng đước ngập mặn xanh thẫm tại xã Long Khánh, khu bảo tồn sinh thái ven biển giữ đất bồi phù sa.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "cho-cai-von",
        "image": "web-nuxt/public/img/entities/cho-cai-von.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Khung cảnh buôn bán nông sản và các loại rau củ miệt vườn tấp nập từ sớm mai tại Chợ Cái Vồn bên bờ sông Hậu thuộc thị xã Bình Minh.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "cau-can-tho",
        "image": "web-nuxt/public/img/entities/cau-can-tho.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Tháp cầu dây văng Cầu Cần Thơ cao 171 mét vươn mình hùng vĩ bắc qua dòng sông Hậu, công trình giao thông trọng điểm nối liền đôi bờ phương Nam.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khu-du-lich-lan-vuong",
        "image": "web-nuxt/public/img/entities/khu-du-lich-lan-vuong.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Trải nghiệm chèo xuồng ba lá len lỏi dưới rặng dừa nước rợp bóng tại Khu du lịch sinh thái Lan Vương, điểm sinh hoạt dã ngoại đậm nét thôn quê.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "khu-du-lich-lang-be",
        "image": "web-nuxt/public/img/entities/khu-du-lich-lang-be.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Hệ thống nhà bè nổi và rặng bần soi bóng tại Khu du lịch Làng Bè ấp An Thới, nơi phục vụ các món cá tai tượng chiên xù và trò chơi dân gian miệt vườn.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "don-ca-tai-tu-nam-bo-tai-vinh-long",
        "image": "web-nuxt/public/img/entities/don-ca-tai-tu-nam-bo-tai-vinh-long.webp",
        "author": "Ngọc Trảng",
        "source": "Báo Vĩnh Long",
        "caption": "Nghệ nhân gảy đàn kìm và ca nương hòa giọng những điệu lý tài tử Nam Bộ mộc mạc bên bờ sông Cổ Chiên, di sản văn hóa phi vật thể đại diện của nhân loại.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "nhom-don-ca-tai-tu-bong-hong-vang",
        "image": "web-nuxt/public/img/entities/nhom-don-ca-tai-tu-bong-hong-vang.webp",
        "author": "Thanh Đức",
        "source": "Báo Vĩnh Long",
        "caption": "Buổi biểu diễn hòa tấu đàn tranh, đàn cò và guitar phím lõm của Nhóm đờn ca tài tử Bông Hồng Vàng phục vụ du khách tại homestay miệt vườn cù lao.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "trang-trai-vinh-sang",
        "image": "web-nuxt/public/img/entities/trang-trai-vinh-sang.webp",
        "author": "Ngọc Trảng",
        "source": "Báo Vĩnh Long",
        "caption": "Khu chuồng trại nuôi đà điểu và các loài động vật bản địa tại Trang trại Vinh Sang xã An Bình, điểm trải nghiệm sinh thái thu hút nhiều gia đình và trẻ nhỏ.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "chua-kompongnigrodha",
        "image": "web-nuxt/public/img/entities/chua-kompongnigrodha.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Chánh điện rực rỡ sắc vàng và những cây cổ thụ di sản hàng trăm năm tuổi trong khuôn viên Chùa KompongNigrodha cổ kính khởi dựng từ năm 1637 tại Trà Ôn.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "sieu-thi-coop-mart-vinh-long",
        "image": "web-nuxt/public/img/entities/sieu-thi-coop-mart-vinh-long.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Mặt tiền và khu quầy kệ mua sắm hiện đại tại Siêu thị Co.opmart Vĩnh Long số 26 đường Ba Tháng Hai phường Long Châu, trung tâm thương mại phục vụ người dân.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "trung-tam-thuong-mai-vincom-vinh-long",
        "image": "web-nuxt/public/img/entities/trung-tam-thuong-mai-vincom-vinh-long.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Trung tâm thương mại Vincom Plaza Vĩnh Long trên đường Phạm Thái Bường phường Phước Hậu với hệ thống mua sắm, ẩm thực và rạp chiếu phim hiện đại.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "sieu-thi-dien-may-cho-lon-vinh-long",
        "image": "web-nuxt/public/img/entities/sieu-thi-dien-may-cho-lon-vinh-long.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Khu vực trưng bày thiết bị gia dụng và điện tử tại Siêu thị Điện máy Chợ Lớn số 39 đường Trần Đại Nghĩa phường Phước Hậu thành phố Vĩnh Long.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "cua-hang-dac-san-que-hai-ung",
        "image": "web-nuxt/public/img/entities/cua-hang-dac-san-que-hai-ung.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Quầy trưng bày các sản phẩm mắm tôm chua ngọt và bánh mứt thủ công dân dã tại Cửa hàng Đặc sản quê Hai Ửng trên cồn Chim xã Hòa Minh.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "sieu-thi-go-tra-vinh",
        "image": "web-nuxt/public/img/entities/sieu-thi-go-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Khu mua sắm hàng tiêu dùng và thực phẩm tươi sống tại Siêu thị GO! trên đường Võ Nguyên Giáp phường Nguyệt Hóa, điểm mua sắm quy mô lớn của người dân.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "cua-hang-ocop-bien-ba-dong",
        "image": "web-nuxt/public/img/entities/cua-hang-ocop-bien-ba-dong.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Kệ hàng giới thiệu hải sản khô đạt chứng nhận OCOP 3 đến 4 sao tại Cửa hàng OCOP biển Ba Động xã Trường Long Hòa, điểm dừng chân mua quà cho du khách.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "cua-hang-ocop-ao-ba-om",
        "image": "web-nuxt/public/img/entities/cua-hang-ocop-ao-ba-om.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Cửa hàng OCOP và đặc sản lưu niệm thủ công mỹ nghệ Khmer nằm ngay cổng di tích danh thắng Ao Bà Om, phục vụ khách tham quan mua sắm.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "sieu-thi-go-ben-tre",
        "image": "web-nuxt/public/img/entities/sieu-thi-go-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Khu trưng bày đặc sản kẹo dừa và hàng tiêu dùng phong phú tại Siêu thị GO! phường Sơn Đông, trung tâm bán lẻ nhộn nhịp phục vụ người tiêu dùng.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "tt-thuong-mai-sense-city-ben-tre",
        "image": "web-nuxt/public/img/entities/tt-thuong-mai-sense-city-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Mặt tiền hiện đại và sảnh mua sắm tích hợp ẩm thực tại Trung tâm thương mại Sense City số 26A đường Trần Quốc Tuấn phường An Hội.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "cua-hang-ocop-vinh-long-trung-tam-xuc-tien-thuong-mai-vinh-long",
        "image": "web-nuxt/public/img/entities/cua-hang-ocop-vinh-long-trung-tam-xuc-tien-thuong-mai-vinh-long.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Khu trưng bày các sản phẩm OCOP tiêu biểu của tỉnh tại Cửa hàng Trung tâm Xúc tiến Thương mại số 31 đường Phạm Thái Bường thành phố Vĩnh Long.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "nha-thuc-pham-sach-khoai-lang-tim-binh-tan-vinh-long",
        "image": "web-nuxt/public/img/entities/nha-thuc-pham-sach-khoai-lang-tim-binh-tan-vinh-long.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Gian hàng phân phối khoai lang tím Bình Tân và nông sản sạch đạt tiêu chuẩn an toàn tại cửa hàng nông sản sạch trên trục Quốc lộ 53.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "cua-hang-dac-san-mien-tay-ba-bay-nem-vinh-long",
        "image": "web-nuxt/public/img/entities/cua-hang-dac-san-mien-tay-ba-bay-nem-vinh-long.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Quầy nem truyền thống trứ danh và các sản phẩm bánh tráng đặc sản đóng gói tại Cửa hàng Đặc sản Miền Tây - Bà Bảy Nem trên đường Nguyễn Huệ.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    }
]

assert len(batch_40_data) == 40

with open("outputs/batch_40_attraction_photos.json", "w", encoding="utf-8") as f:
    json.dump(batch_40_data, f, ensure_ascii=False, indent=2)
    f.write("\n")

print("Generated outputs/batch_40_attraction_photos.json with 40 entries!")
