import json

batch_19_data = [
    {
        "entity_id": "lang-nghe-cham-non-la-long-ho",
        "image": "web-nuxt/public/img/entities/lang-nghe-cham-non-la-long-ho.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Đôi bàn tay khéo léo của nghệ nhân thoăn thoắt từng mũi kim chằm nón lá dừa truyền thống tại ấp Long Hưng, xã Long An ven sông Long Hồ.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "lang-nghe-det-chieu-vung-liem",
        "image": "web-nuxt/public/img/entities/lang-nghe-det-chieu-vung-liem.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Khung dệt chiếu thủ công rộn rã tiếng thoi đưa, dệt nên những manh chiếu lác in hoa văn sắc nét tại vùng nguyên liệu lác xã Trung Thành Đông.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "lang-se-loi-lac-va-dan-lat-vung-liem",
        "image": "web-nuxt/public/img/entities/lang-se-loi-lac-va-dan-lat-vung-liem.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Người thợ lành nghề se từng sợi lõi lác óng ả làm nguyên liệu đan thảm thủ công mỹ nghệ xuất khẩu bên dòng sông Mang Thít.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "lang-nghe-trong-lac-trung-thanh-dong",
        "image": "web-nuxt/public/img/entities/lang-nghe-trong-lac-trung-thanh-dong.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Cánh đồng lác xanh mướt trải dài ven triền đê, nông dân tất bật thu hoạch và phơi những bó lác thẳng tắp dưới nắng vàng sông Cổ Chiên.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "lang-nghe-dan-chieu-va-lam-banh-xe-may-tre",
        "image": "web-nuxt/public/img/entities/lang-nghe-dan-chieu-va-lam-banh-xe-may-tre.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Nghề chẻ nan, uốn vành mây tre đan bánh xe ngựa kéo cổ truyền được các bậc cao niên bảo tồn nguyên vẹn tại làng nghề xã Tân An Luông.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "lang-nghe-banh-trang-tam-binh",
        "image": "web-nuxt/public/img/entities/lang-nghe-banh-trang-tam-binh.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Lò tráng bánh bốc khói nghi ngút từ tờ mờ sáng, những phên bánh tráng mè sữa tròn xoe phơi đều tăm tắp dọc triền rạch Cái Ngang.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "lang-nghe-dan-luc-binh-ngai-tu-binh-ninh",
        "image": "web-nuxt/public/img/entities/lang-nghe-dan-luc-binh-ngai-tu-binh-ninh.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Những cọng lục bình phơi khô dẻo dai qua bàn tay phụ nữ nông thôn biến thành các mẫu giỏ xách, đôn ngồi mỹ nghệ tinh xảo xã Ngãi Tứ.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "lang-nghe-dan-lat-may-tre-phu-le",
        "image": "web-nuxt/public/img/entities/lang-nghe-dan-lat-may-tre-phu-le.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Nghệ nhân làng Phú Lễ vót từng thanh tre bánh tẻ, tỉ mẩn đan bồ lúa, thúng mủng phục vụ đời sống nông nghiệp xứ cù lao Ba Tri.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "lang-nghe-dan-lat-an-duc",
        "image": "web-nuxt/public/img/entities/lang-nghe-dan-lat-an-duc.webp",
        "author": "Minh Mừng",
        "source": "Báo Đồng Khởi",
        "caption": "Không khí lao động khẩn trương tại làng đan lát An Đức với những nong, nia, rổ rá bằng tre trúc bền chắc nức tiếng miệt giồng cát.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "lang-nghe-dan-chapay-phu-can",
        "image": "web-nuxt/public/img/entities/lang-nghe-dan-chapay-phu-can.webp",
        "author": "Huỳnh Phúc Hậu",
        "source": "Báo Trà Vinh",
        "caption": "Nghệ nhân Khmer miệt mài đục đẽo thân gỗ mít, so từng phím đàn Chà-pây Đơng-veng cổ truyền tại sóc Phú Cần, thị trấn Tiểu Cần.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "lang-tau-hu-ky-my-hoa",
        "image": "web-nuxt/public/img/entities/lang-tau-hu-ky-my-hoa.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Hàng trăm chảo gang đun sữa đậu nành sôi sùng sục, người thợ nhẹ nhàng vớt từng tấm váng đậu vàng ươm phơi trên sào tại xã Mỹ Hòa bên bờ sông Hậu.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "htx-cam-sanh-tra-on",
        "image": "web-nuxt/public/img/entities/htx-cam-sanh-tra-on.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Những chùm cam sành vỏ mỏng mọng nước, tép vàng cam ngọt đậm đà được thu hoạch tại vườn chuyên canh trù phú huyện Trà Ôn ven sông Hậu.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "co-so-keo-dua-mo-cay",
        "image": "web-nuxt/public/img/entities/co-so-keo-dua-mo-cay.webp",
        "author": "Cẩm Trúc",
        "source": "Báo Đồng Khởi",
        "caption": "Chảo kẹo dừa sên mạch nha nghi ngút hương thơm béo ngậy, bàn tay công nhân thoăn thoắt cắt và gói từng viên kẹo dừa Mỏ Cày trứ danh.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "lang-gach-gom-long-ho",
        "image": "web-nuxt/public/img/entities/lang-gach-gom-long-ho.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Dãy lò gạch tròn truyền thống bằng đất sét nung đỏ au nằm san sát nhau bên triền kinh rạch nối liền dòng Cổ Chiên hiền hòa.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "lang-nghe-com-dep-ba-so",
        "image": "web-nuxt/public/img/entities/lang-nghe-com-dep-ba-so.webp",
        "author": "Hoàng Triều",
        "source": "Báo Trà Vinh",
        "caption": "Tiếng chày giã cốm nhịp nhàng vang vọng sóc Ba So, từng hạt nếp non rang vừa chín tới được giã dẹp, sàng sảy thơm lừng mùa lễ Ok Om Bok.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "vung-khoai-lang-binh-tan",
        "image": "web-nuxt/public/img/entities/vung-khoai-lang-binh-tan.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Cánh đồng khoai lang tím Nhật bạt ngàn tại Bình Tân vào vụ thu hoạch rộn rã củ to mây mẩy, khẳng định thương hiệu nông sản xuất khẩu chủ lực.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "lang-nghe-che-bien-hai-san-kho-thanh-phong",
        "image": "web-nuxt/public/img/entities/lang-nghe-che-bien-hai-san-kho-thanh-phong.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Những giàn phơi cá khô đù, cá khoai tươi rói ướp muối biển phơi dưới nắng giòn cửa biển Thạnh Phong, huyện Thạnh Phú.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "lang-nghe-thu-cong-my-nghe-tu-dua-quoi-son",
        "image": "web-nuxt/public/img/entities/lang-nghe-thu-cong-my-nghe-tu-dua-quoi-son.webp",
        "author": "Cẩm Trúc",
        "source": "Báo Đồng Khởi",
        "caption": "Gỗ dừa và gáo dừa già được bàn tay nghệ nhân Quới Sơn tiện gọt thành chén dĩa, đũa mun và các mô hình ghe xuồng mỹ nghệ độc đáo.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "lang-hoa-kieng-va-cay-giong-cho-lach",
        "image": "web-nuxt/public/img/entities/lang-hoa-kieng-va-cay-giong-cho-lach.webp",
        "author": "Minh Mừng",
        "source": "Báo Đồng Khởi",
        "caption": "Bạt ngàn gốc mai vàng, cúc mâm xôi và cây giống sầu riêng, măng cụt Cái Mơn khoe sắc rực rỡ dọc tuyến quốc lộ 57, huyện Chợ Lách.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "lang-nghe-nau-ruou-phu-le",
        "image": "web-nuxt/public/img/entities/lang-nghe-nau-ruou-phu-le.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Nồi chưng cất rượu thủ công bằng đất nung và men thuốc bắc cổ truyền tạo nên giọt rượu nếp Phú Lễ cay nồng thơm ngát xứ dừa Ba Tri.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "cong-ty-co-phan-xuat-nhap-khau-ben-tre-betrimex",
        "image": "web-nuxt/public/img/entities/cong-ty-co-phan-xuat-nhap-khau-ben-tre-betrimex.webp",
        "author": "Minh Mừng",
        "source": "Báo Đồng Khởi",
        "caption": "Dây chuyền tiệt trùng UHT hiện đại đóng hộp nước dừa tươi nguyên chất xuất khẩu toàn cầu tại nhà máy chế biến dừa vùng hạ lưu sông Hàm Luông.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "cong-ty-tnhh-che-bien-dua-luong-quoi",
        "image": "web-nuxt/public/img/entities/cong-ty-tnhh-che-bien-dua-luong-quoi.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Quy trình ép dầu dừa tinh khiết và sản xuất nước cốt dừa Vietcoco đạt chuẩn hữu cơ quốc tế tại cụm công nghiệp An Hiệp, Châu Thành.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "lang-nghe-dan-non-la-an-hiep",
        "image": "web-nuxt/public/img/entities/lang-nghe-dan-non-la-an-hiep.webp",
        "author": "Cẩm Trúc",
        "source": "Báo Đồng Khởi",
        "caption": "Những vành nón lá dừa nước trắng muốt, đường kim mũi chỉ đều đặn làm tôn thêm nét duyên dáng người phụ nữ miệt vườn Ba Tri.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "lang-nghe-cay-giong-uon-kieng-hung-khanh-trung",
        "image": "web-nuxt/public/img/entities/lang-nghe-cay-giong-uon-kieng-hung-khanh-trung.webp",
        "author": "Minh Mừng",
        "source": "Báo Đồng Khởi",
        "caption": "Nghệ nhân làng nghề Hưng Khánh Trung khéo léo uốn tỉa cây si, cây sung thành hình các linh vật rồng phượng sống động đón xuân.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "lang-nghe-dan-trang-gio-cong-dua-luong-phu",
        "image": "web-nuxt/public/img/entities/lang-nghe-dan-trang-gio-cong-dua-luong-phu.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Cọng lá dừa dẻo dai được bà con làng Lương Phú chuốt nhẵn, đan thành những chiếc giỏ đựng hoa quả thân thiện với môi trường.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "lang-nghe-banh-trang-nem-cu-lao-may",
        "image": "web-nuxt/public/img/entities/lang-nghe-banh-trang-nem-cu-lao-may.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Những phên bánh tráng nem mềm dẻo không cần nhúng nước, phơi đón gió sông Hậu lồng lộng trên bờ cù lao Mây xã Lục Sĩ Thành.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "ca-phi-sa-ot-thanh-phuoc",
        "image": "web-nuxt/public/img/entities/ca-phi-sa-ot-thanh-phuoc.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Cá phi tươi ướp đẫm sả ớt cay nồng chiên giòn rụm hoặc nướng than hoa, đặc sản dân dã đậm đà hương vị bãi bồi Thạnh Phước, Bình Đại.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "htx-thuy-san-sinh-thai-thanh-phuoc",
        "image": "web-nuxt/public/img/entities/htx-thuy-san-sinh-thai-thanh-phuoc.webp",
        "author": "Minh Mừng",
        "source": "Báo Đồng Khởi",
        "caption": "Mô hình nuôi nghêu, cua biển sinh thái tự nhiên dưới tán rừng ngập mặn tại Hợp tác xã thủy sản Thạnh Phước ven cửa sông Ba Lai.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "cua-hang-ocop-vung-liem",
        "image": "web-nuxt/public/img/entities/cua-hang-ocop-vung-liem.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Không gian trưng bày các sản phẩm OCOP đạt chuẩn 3 sao, 4 sao của vùng đất Vũng Liêm từ gạo tiến vua đến chiếu lác và bánh kẹo đặc sản.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "diem-trung-bay-va-ban-san-pham-ocop-vinh-long-tai-ben-cang",
        "image": "web-nuxt/public/img/entities/diem-trung-bay-va-ban-san-pham-ocop-vinh-long-tai-ben-cang.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Điểm giới thiệu và bán sản phẩm OCOP tỉnh Vĩnh Long đặt tại Bến Cảng Hành Khách sông Cổ Chiên, phục vụ chu đáo du khách thập phương.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "ca-doi-kho-mot-nang-binh-dai",
        "image": "web-nuxt/public/img/entities/ca-doi-kho-mot-nang-binh-dai.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Từng con cá đối biển béo ngậy được xẻ thịt ướp muối ớt vừa vị, phơi đúng một mẻ nắng to trên giàn phơi xã biển Bình Thắng.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "dua-kho-tra-vinh",
        "image": "web-nuxt/public/img/entities/dua-kho-tra-vinh.webp",
        "author": "Hoàng Triều",
        "source": "Báo Trà Vinh",
        "caption": "Những đống dừa khô già vỏ sẫm chất cao như núi tại các vựa dừa ven sông Cổ Chiên, sẵn sàng cung ứng chế biến dầu dừa và cơm dừa nạo sấy.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "dua-sap-cau-ke-dac-san-ben-tre",
        "image": "web-nuxt/public/img/entities/dua-sap-cau-ke-dac-san-ben-tre.webp",
        "author": "Minh Mừng",
        "source": "Báo Đồng Khởi",
        "caption": "Những trái dừa giống dứa và dừa xiêm xanh Ba Tri vỏ mỏng nước ngọt lịm, cơm dừa dẻo bùi nức tiếng vùng đồng bằng hạ lưu sông Hàm Luông.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "dua-sap-tra-vinh",
        "image": "web-nuxt/public/img/entities/dua-sap-tra-vinh.webp",
        "author": "Huỳnh Phúc Hậu",
        "source": "Báo Trà Vinh",
        "caption": "Trái dừa sáp Cầu Kè bổ đôi lộ lớp cơm dừa dày xốp béo ngậy quánh như kem, món quà trời ban độc nhất vô nhị của xứ dừa giồng cát.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "gao-sach-lua-tom-thanh-phu",
        "image": "web-nuxt/public/img/entities/gao-sach-lua-tom-thanh-phu.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Hạt gạo lúa - tôm Thạnh Phú thon dài trắng trong, cơm nấu dẻo thơm tự nhiên được canh tác hữu cơ hoàn toàn trên nền đất nuôi tôm sạch.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "gao-sach-tom-lua-thanh-phu-ocop",
        "image": "web-nuxt/public/img/entities/gao-sach-tom-lua-thanh-phu-ocop.webp",
        "author": "Minh Mừng",
        "source": "Báo Đồng Khởi",
        "caption": "Bao bì sản phẩm gạo sạch Tôm - Lúa Thạnh Phú đạt chứng nhận OCOP 4 sao, khẳng định mô hình nông nghiệp thích ứng biến đổi khí hậu bền vững.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "hop-tac-xa-thuy-san-thanh-loi-ngheu-thanh-hai-ocop",
        "image": "web-nuxt/public/img/entities/hop-tac-xa-thuy-san-thanh-loi-ngheu-thanh-hai-ocop.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Bãi nghêu Thạnh Hải rộng lớn ven bờ Biển Đông, xã viên HTX Thạnh Lợi cần mẫn cào từng mẻ nghêu thịt trắng nõn, ngọt đậm vị biển khơi.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "keo-dua-mo-cay-co-so-tuyet-phung",
        "image": "web-nuxt/public/img/entities/keo-dua-mo-cay-co-so-tuyet-phung.webp",
        "author": "Cẩm Trúc",
        "source": "Báo Đồng Khởi",
        "caption": "Hộp kẹo dừa dẻo sầu riêng, lá dứa Tuyết Phụng danh tiếng tại thị trấn Mỏ Cày, món quà quê hương ngọt ngào đậm đà tình đất tình người.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "kho-ca-bien-thanh-phu",
        "image": "web-nuxt/public/img/entities/kho-ca-bien-thanh-phu.webp",
        "author": "Minh Mừng",
        "source": "Báo Đồng Khởi",
        "caption": "Các loại khô cá lưỡi trâu, cá mối, cá chỉ vàng phơi khô tự nhiên thơm phức mùi nắng biển tại làng hải sản Thạnh Hải, huyện Thạnh Phú.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "kho-ca-bong-lau-ca-du-do-ca-bong-cat-mot-nang-thanh-phong",
        "image": "web-nuxt/public/img/entities/kho-ca-bong-lau-ca-du-do-ca-bong-cat-mot-nang-thanh-phong.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Mẻ khô cá bông lau và cá đù đỏ một nắng béo ngậy được ngư dân Thạnh Phong chế biến ngay khi tàu cập bến, giữ trọn độ tươi ngọt tự nhiên.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    }
]

assert len(batch_19_data) == 40

with open("outputs/batch_craft_products_photos.json", "w", encoding="utf-8") as f:
    json.dump(batch_19_data, f, ensure_ascii=False, indent=2)
    f.write("\n")

print("Generated outputs/batch_craft_products_photos.json with 40 entries!")
