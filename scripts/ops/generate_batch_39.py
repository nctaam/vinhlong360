import json

batch_39_data = [
    # 21 History Entities (Completing 100% History: 195/195)
    {
        "entity_id": "den-tho-chu-tich-ho-chi-minh-long-duc",
        "image": "web-nuxt/public/img/entities/den-tho-chu-tich-ho-chi-minh-long-duc.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Khuôn viên Đền thờ Chủ tịch Hồ Chí Minh tại ấp Vĩnh Hội xã Long Đức, di tích lịch sử quốc gia trang nghiêm được đồng bào kiên cường bảo vệ trong kháng chiến.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "di-tich-duong-ho-chi-minh-tren-bien-ben-thanh-phong",
        "image": "web-nuxt/public/img/entities/di-tich-duong-ho-chi-minh-tren-bien-ben-thanh-phong.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Bia tưởng niệm di tích lịch sử quốc gia Bến Thạnh Phong bên bờ biển Đông, nơi mở đầu tuyến đường Hồ Chí Minh trên biển tiếp nhận vũ khí chi viện miền Nam.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "di-tich-chien-thang-gia-the",
        "image": "web-nuxt/public/img/entities/di-tich-chien-thang-gia-the.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Bia chiến thắng Giá Thẻ tại xã An Nhơn, di tích lịch sử cấp tỉnh khắc ghi chiến công oanh liệt của quân và dân địa phương trong kháng chiến chống Mỹ.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "khu-di-tich-dong-khoi-ben-tre",
        "image": "web-nuxt/public/img/entities/khu-di-tich-dong-khoi-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Tháp đuốc Đồng Khởi cao 24 mét vươn lên giữa bầu trời tại xã Định Thủy, biểu tượng bất diệt của phong trào Đồng Khởi năm 1960.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "dinh-long-thanh-w3",
        "image": "web-nuxt/public/img/entities/dinh-long-thanh-w3.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Bộ vì kèo gỗ chạm trổ hoa văn tinh xảo và các cặp long trụ tại Đình Long Thạnh xã Long Định, di tích kiến trúc nghệ thuật quốc gia đầu thế kỷ 20.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "dinh-long-phung",
        "image": "web-nuxt/public/img/entities/dinh-long-phung.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Hệ thống rường cột căm xe vững chãi và mái ngói âm dương tại Đình Long Phụng ấp Long Hòa 2, ngôi đình cổ lưu giữ sắc phong vua Tự Đức ban năm 1852.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "lang-mo-va-dinh-phan-thanh-gian",
        "image": "web-nuxt/public/img/entities/lang-mo-va-dinh-phan-thanh-gian.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Khu lăng mộ hình voi phục và đền thờ danh nhân Phan Thanh Giản tại xã Bảo Thạnh, di tích lịch sử quốc gia tôn vinh vị tiến sĩ đầu tiên của đất Nam Kỳ.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "bao-tang-tong-hop-tinh-tra-vinh",
        "image": "web-nuxt/public/img/entities/bao-tang-tong-hop-tinh-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Gian trưng bày cổ vật Óc Eo và hiện vật văn hóa Kinh - Khmer - Hoa tại Bảo tàng Tổng hợp, không gian lưu giữ chiều sâu lịch sử của vùng đất phương Nam.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "den-that-phu-vo-mieu",
        "image": "web-nuxt/public/img/entities/den-that-phu-vo-mieu.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Mái ngói cong vút đắp nổi lưỡng long chầu nguyệt tại Đền Thất Phủ Võ Miếu trên đường Trần Hưng Đạo, di tích kiến trúc nghệ thuật của cộng đồng người Hoa tại Ba Tri.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "nha-tho-giao-xu-cai-nhum",
        "image": "web-nuxt/public/img/entities/nha-tho-giao-xu-cai-nhum.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Tháp chuông cao 33 mét mang phong cách kiến trúc La Mã cổ kính của Nhà thờ Giáo xứ Cái Nhum xã Long Thới, một trong những họ đạo lâu đời nhất miền Tây.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "khu-mo-phan-thanh-gian",
        "image": "web-nuxt/public/img/entities/khu-mo-phan-thanh-gian.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Bình phong và bia đá rêu phong tại khu mộ tiến sĩ Phan Thanh Giản ấp Thạnh Nghĩa xã Bảo Thạnh, công trình kiến trúc lăng mộ triều Nguyễn thế kỷ 19.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "nha-ong-nguyen-van-cung-dia-diem-thanh-lap-chi-bo-dang-dau-tien-ben-tre",
        "image": "web-nuxt/public/img/entities/nha-ong-nguyen-van-cung-dia-diem-thanh-lap-chi-bo-dang-dau-tien-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Ngôi nhà gỗ ba gian của ông Nguyễn Văn Cung tại ấp Tân Hòa xã Tân Xuân, địa điểm lịch sử ghi dấu ngày thành lập chi bộ Đảng đầu tiên cuối tháng 4 năm 1930.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "chua-phi-rum-soc-bhiramyaraja",
        "image": "web-nuxt/public/img/entities/chua-phi-rum-soc-bhiramyaraja.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Chánh điện uy nghi với hàng cột đắp nổi tượng nữ thần Kayno tại chùa Phi Rùm Sóc ấp Rùm Sóc xã Châu Điền, ngôi cổ tự Khmer khởi dựng thế kỷ 11.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "di-tich-lich-su-luu-cu",
        "image": "web-nuxt/public/img/entities/di-tich-lich-su-luu-cu.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Nền móng gạch cổ và bệ thờ đền Bà La Môn thuộc văn hóa Óc Eo tại di tích Lưu Cừ II ấp Lưu Cừ II xã Lưu Nghiệp Anh, di tích quốc gia thế kỷ đầu Công nguyên.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "dinh-an-qui",
        "image": "web-nuxt/public/img/entities/dinh-an-qui.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Mặt tiền trang nghiêm của Đình thần An Qui tại vùng đất ven biển Thạnh Phú, di tích lịch sử cấp tỉnh từng là căn cứ nuôi giấu cán bộ cách mạng.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "den-tho-lanh-binh-nguyen-ngoc-thang",
        "image": "web-nuxt/public/img/entities/den-tho-lanh-binh-nguyen-ngoc-thang.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Gian thờ chính Lãnh binh Nguyễn Ngọc Thăng trên tỉnh lộ 885 xã Mỹ Thạnh, di tích lịch sử cấp quốc gia thờ phụng người anh hùng đánh giặc giữ nước.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "thien-hau-cung",
        "image": "web-nuxt/public/img/entities/thien-hau-cung.webp",
        "author": "Ngọc Trảng",
        "source": "Báo Vĩnh Long",
        "caption": "Mái ngói âm dương tráng men xanh ngọc và bia đá lập năm 1898 tại Thiên Hậu Cung đường 30 Tháng 4, cơ sở tín ngưỡng người Hoa tiêu biểu tại thành phố Vĩnh Long.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "di-tich-dau-cau-tiep-nhan-vu-khi-thanh-phong",
        "image": "web-nuxt/public/img/entities/di-tich-dau-cau-tiep-nhan-vu-khi-thanh-phong.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Bia chứng tích Đường Hồ Chí Minh trên biển tại bến Cồn Bửng xã Thạnh Phong, nơi những con tàu không số cập bến an toàn tiếp tế vũ khí cho chiến trường miền Nam.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "dinh-than-an-ngai-trung",
        "image": "web-nuxt/public/img/entities/dinh-than-an-ngai-trung.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Bộ khung gỗ căm xe nguyên khối và mái ngói vảy rêu phong tại Đình thần An Ngãi Trung ấp An Thạnh, ngôi đình làng lưu giữ sắc phong bổn cảnh Thành hoàng thời Nguyễn.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "khu-can-cu-tinh-uy-ben-tre-chau-hoa",
        "image": "web-nuxt/public/img/entities/khu-can-cu-tinh-uy-ben-tre-chau-hoa.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Hệ thống hầm bí mật và lán trại phục dựng tại Khu căn cứ Tỉnh ủy tại ấp Thới Hòa xã Châu Hòa, địa chỉ đỏ cách mạng giữa rặng dừa chở che cán bộ qua hai cuộc kháng chiến.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "dinh-lang-hieu-phung",
        "image": "web-nuxt/public/img/entities/dinh-lang-hieu-phung.webp",
        "author": "Thanh Đức",
        "source": "Báo Vĩnh Long",
        "caption": "Kiến trúc gian võ ca và chính điện lợp ngói âm dương cổ kính của Đình làng Hiếu Phụng tại ấp Quang Trạch, trung tâm tín ngưỡng gắn kết cư dân nông nghiệp huyện Vũng Liêm.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },

    # 1 Drink Entity (Completing 100% Drink: 1/1)
    {
        "entity_id": "dua-sap-sinh-to",
        "image": "web-nuxt/public/img/entities/dua-sap-sinh-to.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Ly sinh tố dừa sáp Cầu Kè béo ngậy xay cùng sữa đặc và đá nhuyễn rắc đậu phộng rang thơm lừng, thức uống giải khát trứ danh mang vị ngon đặc sản tự nhiên.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },

    # 1 Organization Entity (Completing 100% Organization: 1/1)
    {
        "entity_id": "cong-ty-tnhh-du-lich-sinh-thai-bao-duyen",
        "image": "web-nuxt/public/img/entities/cong-ty-tnhh-du-lich-sinh-thai-bao-duyen.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Đội thuyền du lịch sinh thái đón khách trải nghiệm ngắm cảnh miệt vườn cù lao của Công ty Du lịch Sinh thái Bảo Duyên tại bến thuyền trung tâm.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },

    # 17 Attraction Entities (Advancing Attraction: 88 -> 105 / 220)
    {
        "entity_id": "cua-hang-dac-san-mien-tay-tra-vinh-tra-vinh",
        "image": "web-nuxt/public/img/entities/cua-hang-dac-san-mien-tay-tra-vinh-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Gian trưng bày các đặc sản OCOP địa phương như dừa sáp, bánh tét Trà Cuôn và mật hoa dừa tại Cửa hàng Đặc sản Miền Tây trên đường Nguyễn Đáng.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "thien-vien-truc-lam-tra-vinh",
        "image": "web-nuxt/public/img/entities/thien-vien-truc-lam-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Chánh điện lợp ngói đỏ thanh tịnh giữa khuôn viên rợp bóng phi lao tại Thiền viện Trúc Lâm ấp Khoán Tiều xã Trường Long Hòa, điểm chiêm bái hướng mặt ra biển Đông.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "cho-dau-moi-nong-thuy-san-ben-tre",
        "image": "web-nuxt/public/img/entities/cho-dau-moi-nong-thuy-san-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Khung cảnh nhộn nhịp sáng sớm tại Chợ đầu mối nông thủy sản phường Phú Khương với hàng trăm chủng loại tôm cá tươi sống và trái cây nhiệt đới.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "cua-hang-thuc-pham-an-toan-hoa-sao",
        "image": "web-nuxt/public/img/entities/cua-hang-thuc-pham-an-toan-hoa-sao.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Kệ trưng bày rau củ hữu cơ và nông sản đạt tiêu chuẩn VietGAP tại Cửa hàng thực phẩm an toàn Hoa Sao số 72A đường Nguyễn Huệ thành phố Vĩnh Long.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khu-du-lich-sinh-thai-anh-ba-khia",
        "image": "web-nuxt/public/img/entities/khu-du-lich-sinh-thai-anh-ba-khia.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Khung cảnh sinh thái rừng ngập mặn với cầu khỉ và rặng đước xanh tươi tại Khu du lịch sinh thái Anh Ba Khía vùng ven biển Bình Đại.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "pho-an-vat-bo-ke",
        "image": "web-nuxt/public/img/entities/pho-an-vat-bo-ke.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Dãy hàng quán ẩm thực đường phố tấp nập khách dạo bộ vào buổi chiều tại Phố Ăn Vặt Bờ Kè dọc bờ kè sông Cổ Chiên phường Long Châu.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "sokfarm-tieu-can",
        "image": "web-nuxt/public/img/entities/sokfarm-tieu-can.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Kỹ thuật thu mật hoa dừa truyền thống và vườn dừa sinh thái đạt chuẩn hữu cơ quốc tế tại Sokfarm ấp Cây Hẹ thị trấn Cầu Quan.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "chua-vam-ray-wat-samrong",
        "image": "web-nuxt/public/img/entities/chua-vam-ray-wat-samrong.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Tượng Phật Thích Ca nhập niết bàn dài 54 mét mạ vàng uy nghiêm trong khuôn viên rực rỡ của Chùa Vàm Ray xã Hàm Giang.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "canh-dong-dien-gio-duyen-hai",
        "image": "web-nuxt/public/img/entities/canh-dong-dien-gio-duyen-hai.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Hàng trụ turbine gió khổng lồ màu trắng vươn cao trên nền trời xanh bên bờ biển Đông tại Cánh đồng Điện Gió Duyên Hải ấp Định An xã Đông Hải.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "nha-co-cai-cuong",
        "image": "web-nuxt/public/img/entities/nha-co-cai-cuong.webp",
        "author": "Thanh Đức",
        "source": "Báo Vĩnh Long",
        "caption": "Kiến trúc ba gian hai chái kết hợp phong cách phương Tây với bao lam chạm trổ tinh mỹ tại Nhà cổ Cai Cường trên cù lao An Bình.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "cho-dem-tra-vinh-pho-di-bo-hung-vuong-tra-vinh",
        "image": "web-nuxt/public/img/entities/cho-dem-tra-vinh-pho-di-bo-hung-vuong-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Đèn hoa rực rỡ và các gian hàng ẩm thực dân gian Khmer tấp nập người qua lại tại Chợ đêm và Phố đi bộ Hùng Vương trên đường Lý Tự Trọng.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "cho-giong-trom",
        "image": "web-nuxt/public/img/entities/cho-giong-trom.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Khu chợ truyền thống sầm uất tại thị trấn Giồng Trôm với đầy ắp các loại bánh phồng Sơn Đốc, kẹo dừa và rau củ quả tươi miệt vườn.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "cho-mo-cay",
        "image": "web-nuxt/public/img/entities/cho-mo-cay.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Nhịp mua bán rộn rã bên bờ rạch tại Chợ Mỏ Cày, trung tâm đầu mối giao thương nông sản và sản phẩm dừa truyền thống lâu đời.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "cho-ba-vat",
        "image": "web-nuxt/public/img/entities/cho-ba-vat.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Khung cảnh chợ quê Ba Vát xã Phước Mỹ Trung với những sạp hàng bày bán trái cây miệt vườn và các món bánh dân dã truyền thống.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "cong-vien-my-hoa",
        "image": "web-nuxt/public/img/entities/cong-vien-my-hoa.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Hàng cây xanh mát và thảm cỏ rộng thoáng bên bờ sông tại Công viên Mỹ Hóa trên đường Hùng Vương, không gian sinh hoạt cộng đồng thư thái của người dân.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "du-lich-sinh-thai-sala",
        "image": "web-nuxt/public/img/entities/du-lich-sinh-thai-sala.webp",
        "author": "Thanh Đức",
        "source": "Báo Vĩnh Long",
        "caption": "Hồ nước trong lành rợp bóng dừa nước và các chòi lá nghỉ ngơi tại Khu du lịch sinh thái Sala rộng 20 hecta trên đất cù lao An Bình.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khu-du-lich-s-mo-farm-cuu-long",
        "image": "web-nuxt/public/img/entities/khu-du-lich-s-mo-farm-cuu-long.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Không gian kiến trúc đất nung lấy cảm hứng từ vòm lò gạch cổ Mang Thít giữa vườn cây trái tại Khu du lịch Somo Farm Cửu Long thị trấn Cái Nhum.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    }
]

assert len(batch_39_data) == 40

with open("outputs/batch_39_history_photos.json", "w", encoding="utf-8") as f:
    json.dump(batch_39_data, f, ensure_ascii=False, indent=2)
    f.write("\n")

print("Generated outputs/batch_39_history_photos.json with 40 entries!")
