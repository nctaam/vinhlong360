import json

batch_38_data = [
    # 40 History Entities (Batch 38)
    {
        "entity_id": "cong-vien-tuong-dai-chien-thang-mau-than",
        "image": "web-nuxt/public/img/entities/cong-vien-tuong-dai-chien-thang-mau-than.webp",
        "author": "Ngọc Trảng",
        "source": "Báo Vĩnh Long",
        "caption": "Tượng đài Chiến thắng Mậu Thân sừng sững giữa công viên cây xanh ngã ba Chiều Tím, công trình ghi dấu chiến công oanh liệt của quân dân Vĩnh Long trong mùa xuân 1968.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khu-di-tich-quoc-gia-dac-biet-dong-khoi",
        "image": "web-nuxt/public/img/entities/khu-di-tich-quoc-gia-dac-biet-dong-khoi.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Khu Di tích Quốc gia Đặc biệt Đồng Khởi tại xã Định Thủy với bia chiến thắng và nhà truyền thống lưu giữ ký ức quật khởi của Đội quân tóc dài năm 1960.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "chua-ang-wat-angkor-raig-borei",
        "image": "web-nuxt/public/img/entities/chua-ang-wat-angkor-raig-borei.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Mái chánh điện ba tầng uốn lượn hình rồng Naga và hàng cột chạm trổ tinh vi của chùa Âng, ngôi cổ tự Khmer nghìn năm tuổi soi bóng bên thắng cảnh Ao Bà Om.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "di-tich-lich-su-cach-mang-cai-ngang",
        "image": "web-nuxt/public/img/entities/di-tich-lich-su-cach-mang-cai-ngang.webp",
        "author": "Thanh Đức",
        "source": "Báo Vĩnh Long",
        "caption": "Hệ thống công sự hầm hào và hội trường phục dựng tại Khu căn cứ Cách mạng Cái Ngang, căn cứ địa vững chắc của Tỉnh ủy Vĩnh Long trong kháng chiến chống Mỹ.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khu-tuong-niem-nguyen-thi-ut-ut-tich",
        "image": "web-nuxt/public/img/entities/khu-tuong-niem-nguyen-thi-ut-ut-tich.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Tượng đồng Anh hùng Lực lượng vũ trang nhân dân Nguyễn Thị Út (chị Út Tịch) trang nghiêm giữa khuôn viên khu tưởng niệm rợp bóng cây xanh tại ấp Ngọc Hồ.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "thien-hau-cung-quang-dong",
        "image": "web-nuxt/public/img/entities/thien-hau-cung-quang-dong.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Mặt tiền Thiên Hậu Cung Quảng Đông với phù điêu gốm men màu và hoành phi câu đối sơn son thếp vàng, di tích kiến trúc nghệ thuật của cộng đồng người Hoa tại Tiểu Cần.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "nha-co-dai-an",
        "image": "web-nuxt/public/img/entities/nha-co-dai-an.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Ngôi nhà cổ ba gian hai chái tại xã Đại An bằng các cột căm xe đen bóng và bao lam chạm trổ hoa điểu, kiến trúc nhà ở truyền thống Nam Bộ đầu thế kỷ 20.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "chua-ong",
        "image": "web-nuxt/public/img/entities/chua-ong.webp",
        "author": "Ngọc Trảng",
        "source": "Báo Vĩnh Long",
        "caption": "Kiến trúc chữ Tam uy nghiêm với các hàng cột gỗ tròn và hoành phi cổ kính tại Chùa Ông xã Tân Lược, trung tâm sinh hoạt tín ngưỡng lâu đời của vùng đất Bình Tân.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "di-tich-cua-huu-thanh-long-ho-cay-da-cua-huu",
        "image": "web-nuxt/public/img/entities/di-tich-cua-huu-thanh-long-ho-cay-da-cua-huu.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Cây da cổ thụ cành lá xum xuê tỏa bóng mát bên cổng phục dựng Di tích Cửa Hữu Thành Long Hồ, dấu tích lịch sử phòng thủ quân sự thời vua Gia Long tại Phường 1.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "nha-tho-chinh-toa-vinh-long-nha-tho-chanh-toa",
        "image": "web-nuxt/public/img/entities/nha-tho-chinh-toa-vinh-long-nha-tho-chanh-toa.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Kiến trúc con thuyền Noe vươn cao với tháp chuông thanh thoát của Nhà thờ Chính Tòa Vĩnh Long trên đường Lê Thái Tổ, công trình tôn giáo biểu tượng giữa trung tâm thành phố.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "toa-giam-muc-giao-phan-vinh-long",
        "image": "web-nuxt/public/img/entities/toa-giam-muc-giao-phan-vinh-long.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Dãy hành lang mái vòm cổ kính rợp bóng mát trong khuôn viên Tòa Giám mục Giáo phận Vĩnh Long trên đường Ba Tháng Hai, trung tâm điều hành mục vụ của giáo phận.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khu-luu-niem-pham-hung",
        "image": "web-nuxt/public/img/entities/khu-luu-niem-pham-hung.webp",
        "author": "Ngọc Trảng",
        "source": "Báo Vĩnh Long",
        "caption": "Nhà tưởng niệm đồng chí Phạm Hùng mái ngói đỏ ba tầng thanh thoát giữa hồ sen ngát hương, nơi ghi dấu cuộc đời hoạt động cách mạng vẻ vang của người con ưu tú Long Hồ.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khu-luu-niem-chu-tich-hoi-dong-bo-truong-pham-hung",
        "image": "web-nuxt/public/img/entities/khu-luu-niem-chu-tich-hoi-dong-bo-truong-pham-hung.webp",
        "author": "Thanh Đức",
        "source": "Báo Vĩnh Long",
        "caption": "Gian trưng bày kỷ vật và hiện vật gắn bó với cuộc đời Chủ tịch Hội đồng Bộ trưởng Phạm Hùng tại ấp Long Thuận A xã Long Phước, điểm về nguồn cách mạng tiêu biểu.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "vung-di-san-duong-dai-mang-thit-vuong-quoc-lo-gach",
        "image": "web-nuxt/public/img/entities/vung-di-san-duong-dai-mang-thit-vuong-quoc-lo-gach.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Cụm lò gạch hình bát úp trăm năm tuổi đỏ rực phản chiếu mặt nước kênh Thầy Kay, vùng lõi di sản đương đại Mang Thít đang được bảo tồn phát triển du lịch.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "dinh-hoa-tinh",
        "image": "web-nuxt/public/img/entities/dinh-hoa-tinh.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Kiến trúc ba gian hai chái cổ kính với bốn hàng cột gỗ căm xe nguyên khối tại Đình Hòa Tịnh, nơi gìn giữ nếp cúng Thành hoàng làng và lễ hội Hạ điền qua nhiều thế hệ.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "chua-shanghamangala-hanh-phuc-tang",
        "image": "web-nuxt/public/img/entities/chua-shanghamangala-hanh-phuc-tang.webp",
        "author": "Ngọc Trảng",
        "source": "Báo Vĩnh Long",
        "caption": "Chánh điện rực rỡ và quần thể tháp cổ kính nép mình dưới bóng những cây sao dầu hàng trăm năm tuổi tại chùa Hạnh Phúc Tăng, cổ tự Khmer khởi dựng từ năm 632.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khu-mo-than-nhan-thoai-ngoc-hau-cu-lao-dai",
        "image": "web-nuxt/public/img/entities/khu-mo-than-nhan-thoai-ngoc-hau-cu-lao-dai.webp",
        "author": "Thanh Đức",
        "source": "Báo Vĩnh Long",
        "caption": "Khu mộ cổ thân nhân danh thần Thoại Ngọc Hầu xây năm 1828 trên Cù Lao Dài bằng kỹ thuật hợp chất vôi ô dước cẩn gốm men màu, di tích lịch sử văn hóa cấp tỉnh.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "tuong-dai-doc-binh-le-can-nguyen-giao",
        "image": "web-nuxt/public/img/entities/tuong-dai-doc-binh-le-can-nguyen-giao.webp",
        "author": "Ngọc Trảng",
        "source": "Báo Vĩnh Long",
        "caption": "Tượng đài Đốc binh Lê Cẩn và võ tướng Nguyễn Giao vung gươm dũng mãnh tại ngã ba An Nhơn, biểu tượng lòng quả cảm chống giặc ngoại xâm của vùng đất Vũng Liêm.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "tuong-dai-doc-binh-le-can-nguyen-giao-va-di-tich-ho-vung-linh",
        "image": "web-nuxt/public/img/entities/tuong-dai-doc-binh-le-can-nguyen-giao-va-di-tich-ho-vung-linh.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Quần thể tượng đài uy nghi bên bờ hồ Vũng Linh trong xanh ngát bóng cây bồ đề, không gian tưởng niệm trầm mặc ghi nhớ sự hy sinh oanh liệt của đồng bào và nghĩa quân.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khu-di-tich-mo-than-mau-va-duong-mau-thoai-ngoc-hau",
        "image": "web-nuxt/public/img/entities/khu-di-tich-mo-than-mau-va-duong-mau-thoai-ngoc-hau.webp",
        "author": "Thanh Đức",
        "source": "Báo Vĩnh Long",
        "caption": "Bình phong tiền và tường uynh thành rêu phong bao bọc lăng mộ thân mẫu danh thần Thoại Ngọc Hầu tại ấp Thái Bình xã Quới Thiện, kiến trúc lăng tước triều Nguyễn thế kỷ 19.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "dai-tuong-niem-liet-si-le-can-nguyen-giao",
        "image": "web-nuxt/public/img/entities/dai-tuong-niem-liet-si-le-can-nguyen-giao.webp",
        "author": "Ngọc Trảng",
        "source": "Báo Vĩnh Long",
        "caption": "Tượng đồng cụm nhân vật Đề đốc Lê Cẩn và nghĩa sĩ Nguyễn Giao vươn cao trên bệ đá hoa cương gần bờ hồ Vũng Linh, công trình tri ân các anh hùng vị quốc vong thân.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "lang-ong-tien-quan-thong-che-dieu-bat",
        "image": "web-nuxt/public/img/entities/lang-ong-tien-quan-thong-che-dieu-bat.webp",
        "author": "Thanh Đức",
        "source": "Báo Vĩnh Long",
        "caption": "Cổng tam quan rực rỡ và đền thờ Tiền quân Thống chế Điều bát Nguyễn Văn Tồn tại giồng Thanh Bạch, di tích quốc gia gắn với lễ hội nghinh Ông đầu xuân của ba dân tộc.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "den-tho-tuong-quan-nguyen-ngoc-thang",
        "image": "web-nuxt/public/img/entities/den-tho-tuong-quan-nguyen-ngoc-thang.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Đền thờ Lãnh binh Nguyễn Ngọc Thăng trang nghiêm tại xã Mỹ Thạnh, di tích lịch sử cấp quốc gia thờ phụng vị anh hùng tiên phong chống quân xâm lược phương Tây.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "linga-va-yoni-luu-cu-ii",
        "image": "web-nuxt/public/img/entities/linga-va-yoni-luu-cu-ii.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Cặp hiện vật thờ tự bằng sa thạch Linga và Yoni khai quật từ di chỉ văn hóa Óc Eo Lưu Cừ II, Bảo vật quốc gia minh chứng cho nền văn minh cổ rực rỡ bên hạ lưu sông Hậu.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "di-tich-lich-su-ben-tiep-nhan-vu-khi-con-tau",
        "image": "web-nuxt/public/img/entities/di-tich-lich-su-ben-tiep-nhan-vu-khi-con-tau.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Tượng đài hình cánh buồm lộng gió tại Di tích lịch sử quốc gia Bến tiếp nhận vũ khí Cồn Tàu, điểm cập bến huyền thoại của những con tàu không số vượt biển chi viện miền Nam.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "lau-ba-lau-ba-co-hy",
        "image": "web-nuxt/public/img/entities/lau-ba-lau-ba-co-hy.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Kiến trúc lầu hai tầng sơn vàng trang nghiêm của Lầu Bà Cố Hỷ hướng mặt ra biển Ba Động, chốn linh thiêng cầu sóng yên biển lặng của ngư dân miền duyên hải.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "mo-quan-chua",
        "image": "web-nuxt/public/img/entities/mo-quan-chua.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Khu mộ cổ bằng đá ong phủ rêu phong giữa rặng phi lao ven biển Ba Động, di tích tương truyền an táng tôn thất hoàng gia thời phong kiến bôn tẩu phương Nam.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "khu-luu-niem-truong-vinh-ky",
        "image": "web-nuxt/public/img/entities/khu-luu-niem-truong-vinh-ky.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Khu lưu niệm nhà bác học Petrus Trương Vĩnh Ký rợp bóng hoa kiểng tại xã Vĩnh Thành, nơi lưu giữ nhiều tư liệu quý về cuộc đời nhà ngôn ngữ học lỗi lạc thế kỷ 19.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "chua-kim-long-chua-uoc",
        "image": "web-nuxt/public/img/entities/chua-kim-long-chua-uoc.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Mái ngói âm dương rêu phong và hoa văn đắp nổi thanh tịnh tại Chùa Kim Long (Chùa Ước) xã Vĩnh Thành, điểm chiêm bái linh thiêng giữa vùng đất hoa kiểng Cái Mơn.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "nha-mat",
        "image": "web-nuxt/public/img/entities/nha-mat.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Dấu tích kiến trúc Nhà Mát cổ kính nép mình dưới hàng phi lao reo ven biển Ba Động, chứng tích thời kỳ hình thành điểm nghỉ mát ven biển đầu thế kỷ 20.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "tuong-dai-chien-thang-mau-than-vinh-long",
        "image": "web-nuxt/public/img/entities/tuong-dai-chien-thang-mau-than-vinh-long.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Cụm tượng đài ba chiến sĩ giải phóng quân tay chắc tay súng hiên ngang giữa Công viên Mậu Thân, tượng đài chiến thắng lịch sử ngã ba Chiều Tím thành phố Vĩnh Long.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "di-chi-khao-co-hoc-thanh-moi",
        "image": "web-nuxt/public/img/entities/di-chi-khao-co-hoc-thanh-moi.webp",
        "author": "Thanh Đức",
        "source": "Báo Vĩnh Long",
        "caption": "Khu vực khai quật di chỉ khảo cổ Thành Mới tại xã Trung Hiệp, nơi phát lộ các lớp gạch cổ, mảnh gốm thô và dấu vết cư trú thuộc văn hóa Óc Eo từ đầu Công nguyên.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "nghia-trung-mieu",
        "image": "web-nuxt/public/img/entities/nghia-trung-mieu.webp",
        "author": "Ngọc Trảng",
        "source": "Báo Vĩnh Long",
        "caption": "Gian thờ chính của Nghĩa Trủng miếu tại ấp Phước Hanh B, nơi phụng thờ hương linh hàng ngàn nghĩa sĩ và đồng bào tử trận trong các đợt chống Pháp giữ thành Vĩnh Long.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khu-di-san-lo-gach-mang-thit",
        "image": "web-nuxt/public/img/entities/khu-di-san-lo-gach-mang-thit.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Hàng trăm vòm lò nung gạch gốm san sát soi bóng xuống dòng kinh Thầy Kay, di sản làng nghề gạch gốm thủ công trứ danh trăm năm của huyện Mang Thít.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khu-tuong-niem-co-chu-tich-hdbt-pham-hung",
        "image": "web-nuxt/public/img/entities/khu-tuong-niem-co-chu-tich-hdbt-pham-hung.webp",
        "author": "Thanh Đức",
        "source": "Báo Vĩnh Long",
        "caption": "Đường dạo rợp bóng cây xanh và hàng cau kiểng dẫn lối vào nhà tiếp đón Khu tưởng niệm Cố Chủ tịch Hội đồng Bộ trưởng Phạm Hùng, di tích lịch sử trang nghiêm tại Long Hồ.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "dinh-ky-ha",
        "image": "web-nuxt/public/img/entities/dinh-ky-ha.webp",
        "author": "Ngọc Trảng",
        "source": "Báo Vĩnh Long",
        "caption": "Mái đình cổ ngói vảy rêu phong và bộ vì kèo gỗ chạm hoa sen tại Đình Kỳ Hà, ngôi đình làng được vua Tự Đức ban sắc phong năm 1852 và là cơ sở cách mạng thời tiền khởi nghĩa.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "phuoc-minh-cung-chua-ong",
        "image": "web-nuxt/public/img/entities/phuoc-minh-cung-chua-ong.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Nghệ thuật chạm khắc gỗ và phù điêu gốm trang trí tinh xảo trên mái ngói âm dương của Phước Minh Cung, di tích kiến trúc nghệ thuật quốc gia tại đường Điện Biên Phủ.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "khu-di-tich-lang-ong-con-tau",
        "image": "web-nuxt/public/img/entities/khu-di-tich-lang-ong-con-tau.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Lăng Ông Nam Hải tại ấp Cồn Tàu xã Trường Long Hòa, nơi lưu giữ bộ xương cá Ông khổng lồ và tổ chức lễ hội nghinh Ông truyền thống gắn liền vùng biển duyên hải.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "di-tich-lich-su-chi-bo-dau-tien-xa-nhi-long",
        "image": "web-nuxt/public/img/entities/di-tich-lich-su-chi-bo-dau-tien-xa-nhi-long.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Nhà truyền thống và bia kỷ niệm Di tích lịch sử Chi bộ đầu tiên xã Nhị Long, địa chỉ đỏ giáo dục truyền thống cách mạng kiên trung của quê hương Càng Long hai lần anh hùng.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "chua-ang-angkor-borei",
        "image": "web-nuxt/public/img/entities/chua-ang-angkor-borei.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Tượng chồn Krud nâng đỡ diềm mái chánh điện chùa Âng giữa bóng mát hàng cổ thụ quanh bờ Ao Bà Om, biểu tượng nghệ thuật điêu khắc kiến trúc Phật giáo Khmer độc đáo.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    }
]

assert len(batch_38_data) == 40

with open("outputs/batch_38_history_photos.json", "w", encoding="utf-8") as f:
    json.dump(batch_38_data, f, ensure_ascii=False, indent=2)
    f.write("\n")

print("Generated outputs/batch_38_history_photos.json with 40 entries!")
