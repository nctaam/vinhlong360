import json

batch_42_data = [
    {
        "entity_id": "khu-du-lich-dai-loc",
        "image": "web-nuxt/public/img/entities/khu-du-lich-dai-loc.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Khuôn viên vườn cây trái trĩu quả rợp mát và những chòi lá mộc mạc bên mương nước tại Khu du lịch Đại Lộc xã Sơn Định.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "vuon-xoai-tu-quy-thanh-son",
        "image": "web-nuxt/public/img/entities/vuon-xoai-tu-quy-thanh-son.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Những chùm xoài tứ quý trĩu nặng trên cành xanh mướt cho trái quanh năm tại Vườn xoài Thanh Sơn gần Cồn Phú Đa.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "diem-du-lich-ba-ngoi-con-phu-da",
        "image": "web-nuxt/public/img/entities/diem-du-lich-ba-ngoi-con-phu-da.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Du khách thưởng thức đặc sản ốc gạo và trái cây miệt vườn dưới bóng mát cây xanh tại Điểm du lịch Ba Ngói trên Cồn Phú Đa.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "chua-khmer-phuong-thanh-pisay",
        "image": "web-nuxt/public/img/entities/chua-khmer-phuong-thanh-pisay.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Ngôi chánh điện cổ kính với mái ngói nhiều tầng vút cong và tháp nhọn rực rỡ tại Chùa Khmer Phương Thạnh Pisay rợp bóng cây cổ thụ.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "thien-vien-truc-lam-duyen-hai",
        "image": "web-nuxt/public/img/entities/thien-vien-truc-lam-duyen-hai.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Quần thể kiến trúc Phật giáo bằng gỗ lim uy nghiêm hướng ra biển Đông lộng gió tại Thiền viện Trúc Lâm Duyên Hải xã Trường Long Hòa.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "khu-luu-niem-tran-dai-nghia",
        "image": "web-nuxt/public/img/entities/khu-luu-niem-tran-dai-nghia.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Khu nhà tưởng niệm trang nghiêm và các gian trưng bày hiện vật cuộc đời Giáo sư Viện sĩ Trần Đại Nghĩa tại xã Tường Lộc.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "vuon-chom-chom-ong-chin-hoan",
        "image": "web-nuxt/public/img/entities/vuon-chom-chom-ong-chin-hoan.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Những chùm chôm chôm chín đỏ trĩu cành bên lối đi rải đá miệt vườn tại Vườn chôm chôm ông Chín Hoán cù lao An Bình.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "nha-san-ong-muoi-day",
        "image": "web-nuxt/public/img/entities/nha-san-ong-muoi-day.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Căn nhà sàn gỗ truyền thống mộc mạc dựng bên rạch nước rợp bóng dừa mát rượi tại điểm dừng chân Nhà sàn ông Mười Đầy.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "vuon-trai-cay-be-sau",
        "image": "web-nuxt/public/img/entities/vuon-trai-cay-be-sau.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Vườn nhãn xuồng cơm vàng và chôm chôm bách thảo trĩu quả đón khách tham quan hái trái tại Vườn trái cây Bé Sáu trên cù lao An Bình.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "vuon-trai-cay-bi-bo",
        "image": "web-nuxt/public/img/entities/vuon-trai-cay-bi-bo.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Những lối đi rợp bóng mát rượi giữa các luống cây ăn trái nhiệt đới sum suê tại Vườn trái cây Bi Bo xã An Bình.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "nam-khanh",
        "image": "web-nuxt/public/img/entities/nam-khanh.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Mương nước phù sa và cầu khỉ lắt lẻo phục vụ các trò chơi dân gian vận động tại Điểm du lịch sinh thái Năm Khanh trên Cồn Công.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khu-du-lich-vinh-sang",
        "image": "web-nuxt/public/img/entities/khu-du-lich-vinh-sang.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Khu trải nghiệm câu cá sấu và trượt cỏ xanh mướt trải dài bên dòng sông Cổ Chiên tại Khu du lịch sinh thái Vinh Sang.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khu-du-lich-vuon-sinh-thai-ba-ngoi",
        "image": "web-nuxt/public/img/entities/khu-du-lich-vuon-sinh-thai-ba-ngoi.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Vườn sầu riêng và măng cụt cổ thụ xanh tốt ven bờ sông Cổ Chiên tại Khu du lịch Vườn sinh thái Ba Ngói ấp Phú Hiệp.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "vuon-trai-cay-6-tan",
        "image": "web-nuxt/public/img/entities/vuon-trai-cay-6-tan.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Không gian xanh ngát của vườn dâu da và bưởi da xanh ngọt lành tại Vườn trái cây 6 Tấn phục vụ du khách miệt vườn An Bình.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "vuon-trai-cay-tam-loc",
        "image": "web-nuxt/public/img/entities/vuon-trai-cay-tam-loc.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Các luống ổi ruột hồng và chôm chôm quả mọng trĩu cành bên mương nước trong lành tại Vườn trái cây Tám Lộc cù lao An Bình.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khu-du-lich-nha-xua-va-homestay-ut-trinh",
        "image": "web-nuxt/public/img/entities/khu-du-lich-nha-xua-va-homestay-ut-trinh.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Gian nhà rường cổ kính với hàng cột gỗ bóng loáng và hiên hoa lan rực rỡ tại Homestay Út Trinh xã An Bình bên bờ sông Tiền.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "lang-du-lich-cong-dong-cai-ngang",
        "image": "web-nuxt/public/img/entities/lang-du-lich-cong-dong-cai-ngang.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Cầu ván bắc qua rạch dừa nước và nếp sống mộc mạc thanh bình của người dân tại Làng du lịch cộng đồng Cái Ngang xã Phú Lộc.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "sieu-thi-thuy-tien",
        "image": "web-nuxt/public/img/entities/sieu-thi-thuy-tien.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Khu trưng bày các thiết bị gia dụng và đồ gỗ nội thất hiện đại phục vụ người dân tại Siêu thị Thủy Tiên trên trục lộ trung tâm.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "tt-xuc-tien-du-lich-tra-vinh",
        "image": "web-nuxt/public/img/entities/tt-xuc-tien-du-lich-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Gian trưng bày các ấn phẩm hướng dẫn du lịch và sản phẩm OCOP đặc trưng tại Trung tâm Xúc tiến Du lịch trên đường Nguyễn Thị Minh Khai.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "lo-gach-hung-loi",
        "image": "web-nuxt/public/img/entities/lo-gach-hung-loi.webp",
        "author": "Ngọc Trảng",
        "source": "Báo Vĩnh Long",
        "caption": "Những lò gạch hình chóp mái vòm cổ kính phủ rêu phong sừng sững soi bóng bên dòng kênh Thầy Cai tại Lò gạch Hưng Lợi Mang Thít.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "xa-chanh-an",
        "image": "web-nuxt/public/img/entities/xa-chanh-an.webp",
        "author": "Ngọc Trảng",
        "source": "Báo Vĩnh Long",
        "caption": "Đường liên ấp rợp bóng cây xanh và tháp chuông nhà thờ Công giáo xứ Mỹ Chánh thanh bình giữa đồng lúa xã Chánh An.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "vuon-sau-rieng-bay-thao",
        "image": "web-nuxt/public/img/entities/vuon-sau-rieng-bay-thao.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Hàng sầu riêng Ri6 trĩu quả trên diện tích 5 ha canh tác theo tiêu chuẩn VietGAP tại Vườn sầu riêng Bảy Thảo xã Vĩnh Thành.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "co-so-keo-dua-thanh-long-ben-tre",
        "image": "web-nuxt/public/img/entities/co-so-keo-dua-thanh-long-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Dây chuyền ngào đường nước cốt dừa và gói kẹo thủ công truyền thống bằng bánh tráng tại Cơ sở Kẹo Dừa Thanh Long đường Nguyễn Đình Chiểu.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "cua-hang-dac-san-dua-ben-tre-cong-ty-tnhh-dong-a-ben-tre",
        "image": "web-nuxt/public/img/entities/cua-hang-dac-san-dua-ben-tre-cong-ty-tnhh-dong-a-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Khu trưng bày các sản phẩm thủ công mỹ nghệ từ gỗ dừa và mỹ phẩm dừa tinh khiết tại Cửa hàng Đông Á trên đại lộ Đồng Khởi.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "cho-ben-tre-cho-trung-tam-ben-tre",
        "image": "web-nuxt/public/img/entities/cho-ben-tre-cho-trung-tam-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Khung cảnh buôn bán tấp nập của các sạp trái cây đặc sản và hải sản tươi sống tại Chợ trung tâm trên đường Trưng Trắc bên bờ sông Bến Tre.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "vuon-dua-sap-ba-thuy",
        "image": "web-nuxt/public/img/entities/vuon-dua-sap-ba-thuy.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Những buồng dừa sáp trĩu quả cơm dày dẻo đặc sản quý hiếm được chăm sóc kỹ lưỡng tại Vườn Dừa Sáp Ba Thúy vùng đất Cầu Kè.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "ao-ba-om-ao-vuong-tra-vinh",
        "image": "web-nuxt/public/img/entities/ao-ba-om-ao-vuong-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Mặt nước tĩnh lặng soi bóng những rễ cây sao, dầu cổ thụ kỳ thú hàng trăm năm tuổi tại Danh lam thắng cảnh quốc gia Ao Bà Om.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "di-san-lo-gach-mang-thit-kenh-thay-cai",
        "image": "web-nuxt/public/img/entities/di-san-lo-gach-mang-thit-kenh-thay-cai.webp",
        "author": "Ngọc Trảng",
        "source": "Báo Vĩnh Long",
        "caption": "Dãy tháp lò gạch đất sét nung đỏ rực trải dài dọc bờ kênh Thầy Cai thuộc Đề án Di sản đương đại Mang Thít quy mô hơn 3.000 ha.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "vuon-chom-chom-thay-ha",
        "image": "web-nuxt/public/img/entities/vuon-chom-chom-thay-ha.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Vườn chôm chôm trĩu quả chín đỏ rực đón các đoàn khách dừng chân thưởng thức trái ngọt tại Vườn chôm chôm thầy Hà xã Vĩnh Bình.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "nhom-don-ca-tai-tu-truong-an",
        "image": "web-nuxt/public/img/entities/nhom-don-ca-tai-tu-truong-an.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Các nghệ nhân say mê so dây đàn kìm và ca diễn những bản tài tử Nam Bộ truyền thống tại không gian văn hóa xã Trường An.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "clb-don-ca-tai-tu-du-lich-cuu-long",
        "image": "web-nuxt/public/img/entities/clb-don-ca-tai-tu-du-lich-cuu-long.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Buổi hòa tấu đờn ca tài tử phục vụ du khách trên tàu du lịch lướt êm đềm ngắm cảnh hoàng hôn sông Cổ Chiên của CLB Du lịch Cửu Long.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "clb-don-ca-tai-tu-tt-van-hoa-thong-tin-vinh-long",
        "image": "web-nuxt/public/img/entities/clb-don-ca-tai-tu-tt-van-hoa-thong-tin-vinh-long.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Tiết mục đờn ca tài tử Nam Bộ lưu giữ làn điệu cổ nhạc truyền thống do các nghệ nhân sinh hoạt tại Trung tâm Văn hóa Thông tin biểu diễn.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "bien-ba-dong",
        "image": "web-nuxt/public/img/entities/bien-ba-dong.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Bờ cát thoai thoải và hàng phi lao chắn gió rì rào trong làn gió biển mát lành tại Khu du lịch Biển Ba Động xã Trường Long Hòa.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "con-cu",
        "image": "web-nuxt/public/img/entities/con-cu.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Dải cồn cát tự nhiên xanh mát nhô lên giữa dòng phù sa ven biển với thảm thực vật ngập mặn phong phú tại Cồn Cù xã Nhị Long.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "nha-gom-do-tu-buoi",
        "image": "web-nuxt/public/img/entities/nha-gom-do-tu-buoi.webp",
        "author": "Ngọc Trảng",
        "source": "Báo Vĩnh Long",
        "caption": "Công trình nhà 3 gian 2 chái xây dựng hoàn toàn từ gốm đỏ nung không men đạt Kỷ lục Việt Nam của Nghệ nhân Nguyễn Văn Buôi tại Thanh Đức.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "agribank-chi-nhanh-vinh-long-vinh-long",
        "image": "web-nuxt/public/img/entities/agribank-chi-nhanh-vinh-long-vinh-long.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Trụ sở giao dịch khang trang của Agribank Chi nhánh Vĩnh Long tại số 28 đường Hưng Đạo Vương phục vụ nhu cầu tài chính của người dân.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "atm-vietcombank-benh-vien-da-khoa-tinh-vinh-long",
        "image": "web-nuxt/public/img/entities/atm-vietcombank-benh-vien-da-khoa-tinh-vinh-long.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Buồng máy ATM Vietcombank hoạt động 24/7 đặt tại khuôn viên Bệnh viện Đa khoa tỉnh trên đường Trần Phú phục vụ bệnh nhân và du khách.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "ben-pha-an-binh-vinh-long",
        "image": "web-nuxt/public/img/entities/ben-pha-an-binh-vinh-long.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Phà cập bến vận chuyển hành khách và xe cộ qua lại giữa trung tâm thành phố Vĩnh Long và các xã cù lao An Bình trên sông Cổ Chiên.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "ben-pha-dai-ngai-dau-cau-quan-tra-vinh-tra-vinh",
        "image": "web-nuxt/public/img/entities/ben-pha-dai-ngai-dau-cau-quan-tra-vinh-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Chuyến phà lớn vượt hai nhánh sông Hậu kết nối giao thương huyết mạch trên Quốc lộ 60 giữa bến phà Cầu Quan và Cù lao Dung.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "ben-pha-dinh-khao-vinh-long",
        "image": "web-nuxt/public/img/entities/ben-pha-dinh-khao-vinh-long.webp",
        "author": "Ngọc Trảng",
        "source": "Báo Vĩnh Long",
        "caption": "Bến phà Đình Khao tấp nập xe cộ qua lại trên tuyến Quốc lộ 57 vượt luồng sông Cổ Chiên kết nối vùng Long Hồ sang Chợ Lách.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    }
]

assert len(batch_42_data) == 40

with open('outputs/batch_42_attraction_photos.json', 'w', encoding='utf-8') as f:
    json.dump(batch_42_data, f, ensure_ascii=False, indent=2)
    f.write('\n')

print('Generated outputs/batch_42_attraction_photos.json with 40 entries!')
