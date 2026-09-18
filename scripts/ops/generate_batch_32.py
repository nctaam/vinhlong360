import json

batch_32_data = [
    # 40 Restaurants (Chuẩn hóa Khối Quán ăn Truyền thống & Đặc sản Sông Nước: 40/86)
    {
        "entity_id": "nha-hang-binh-an-khu-cong-nghiep-hoa-phu-vinh-long",
        "image": "web-nuxt/public/img/entities/nha-hang-binh-an-khu-cong-nghiep-hoa-phu-vinh-long.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Nhà hàng Bình An ven trục đường Ba Tháng Hai, phường Tân Ngãi, không gian tiệc thoáng đãng phục vụ thực đơn mâm cỗ Nam Bộ và hải sản tươi sống.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "quan-oc-co-ba-gan-cau-my-thuan-phia-vinh-long",
        "image": "web-nuxt/public/img/entities/quan-oc-co-ba-gan-cau-my-thuan-phia-vinh-long.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Quán ốc Cô Ba cạnh chân cầu Mỹ Thuận trên quốc lộ 1A, xã Tân Hòa, các thau ốc bươu, ốc lác luộc sả ớt chấm nước mắm gừng cay nồng ấm bụng.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "quan-lau-ca-keo-chu-tam-huyen-vung-liem-vinh-long",
        "image": "web-nuxt/public/img/entities/quan-lau-ca-keo-chu-tam-huyen-vung-liem-vinh-long.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Quán Chú Tám tại thị trấn Vũng Liêm, thố lẩu cá kèo lá giang sôi sùng sục ăn kèm rau đắng đất, bắp chuối bào và bún tươi trắng muốt.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "nha-hang-phuong-nam-ven-song-long-ho-vinh-long",
        "image": "web-nuxt/public/img/entities/nha-hang-phuong-nam-ven-song-long-ho-vinh-long.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Nhà hàng Phương Nam bên bờ sông Long Hồ, bàn ăn lộng gió đón khách thưởng thức cá tai tượng chiên xù cuốn bánh tráng rau vườn An Bình.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "bun-thit-nuong-co-hanh-ben-tre",
        "image": "web-nuxt/public/img/entities/bun-thit-nuong-co-hanh-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Quán bún thịt nướng Cô Hạnh trên đường Đồng Khởi, phường Phú Khương, xiên thịt nạc dăm ướp sả mật ong nướng than hoa vàng ruộm thơm phức.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "banh-xeo-muoi-xinh-ben-tre",
        "image": "web-nuxt/public/img/entities/banh-xeo-muoi-xinh-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Quán bánh xèo Mười Xinh trên đường Nguyễn Thị Định, phường Phú Khương, chảo bánh xèo xèo vàng giòn nhân tôm đất, thịt ba rọi và củ hũ dừa giòn ngọt.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "chao-long-ba-nam-cho-phuong-4-ben-tre",
        "image": "web-nuxt/public/img/entities/chao-long-ba-nam-cho-phuong-4-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Quán cháo lòng Bà Năm góc chợ truyền thống phường Phú Khương, tô cháo gạo rang thơm phức dồi huyết chiên giòn và đĩa lòng heo tươi xắt miếng dày.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "bun-nuoc-leo-co-tu-mo-cay-ben-tre",
        "image": "web-nuxt/public/img/entities/bun-nuoc-leo-co-tu-mo-cay-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Quán bún nước lèo Cô Tư Mỏ Cày, nước lèo nấu từ cá đồng và mắm sặc thanh dịu, ăn kèm bắp chuối thái mỏng, giá sống và rau muống chẻ non mềm.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "banh-tam-ben-tre-hang-xe-day-khu-vuc-truong-hoc-ben-tre",
        "image": "web-nuxt/public/img/entities/banh-tam-ben-tre-hang-xe-day-khu-vuc-truong-hoc-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Gánh bánh tằm bì xe đẩy gần trường THPT Nguyễn Đình Chiểu, phường Phú Khương, cọng bánh tằm se tay mềm dẻo chan nước cốt dừa béo và nước mắm ớt chua ngọt.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "hang-banh-uot-co-lan-cho-ba-tri-ben-tre",
        "image": "web-nuxt/public/img/entities/hang-banh-uot-co-lan-cho-ba-tri-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Hàng bánh ướt Cô Lan bên lồng chợ Ba Tri, lớp bánh tráng mỏng mềm mướt tráng tại chỗ rắc hành phi thơm lừng ăn kèm chả lụa lá chuối tươi ngon.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "com-tam-co-muoi-ben-tre",
        "image": "web-nuxt/public/img/entities/com-tam-co-muoi-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Quán cơm tấm Cô Mười tại số 136/1 Nguyễn Ngọc Nhựt, phường Phú Khương, miếng sườn cốt lết nướng than đượm vị mật ong ăn cùng chả trứng hấp bùi béo.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "com-tam-kim-ngan-ben-tre",
        "image": "web-nuxt/public/img/entities/com-tam-kim-ngan-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Cơm tấm Kim Ngân tại số 325 Trương Định, phường Phú Khương, hạt tấm nhuyễn dẻo thơm chan mỡ hành óng ánh, bì thịt xắt nhuyễn và đồ chua giòn rụm.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "com-tam-9-trieu-ben-tre",
        "image": "web-nuxt/public/img/entities/com-tam-9-trieu-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Quán cơm tấm 9 Triệu trên tuyến Lộ Hàng Keo, phường Phú Khương, sườn nướng than xém cạnh thấm đượm gia vị truyền thống phục vụ bữa trưa dân dã.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "vuon-am-thuc-truc-giang-ben-tre",
        "image": "web-nuxt/public/img/entities/vuon-am-thuc-truc-giang-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Vườn ẩm thực Trúc Giang tại số 76A Võ Nguyên Giáp, phường Phú Khương, không gian sân vườn rợp bóng cây phục vụ lẩu tôm càng xanh và gà tre nướng muối ớt.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "vuon-am-thuc-mai-an-tiem-ben-tre",
        "image": "web-nuxt/public/img/entities/vuon-am-thuc-mai-an-tiem-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Vườn ẩm thực Mai An Tiêm tại số 108E An Thuận B, phường Phú Khương, khuôn viên chòi lá mộc mạc chuyên các món đồng quê: lươn xào sả ớt và cá lóc hấp bầu.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "quan-com-tam-chu-tu-tra-cu-tra-vinh",
        "image": "web-nuxt/public/img/entities/quan-com-tam-chu-tu-tra-cu-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Quán cơm tấm Chú Tư bên chợ Trà Cú, đĩa cơm tấm sườn nướng mỡ hành thơm phức kèm chén nước mắm kẹo ớt hiểm tỏi băm cay nồng đưa vị.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "quan-hu-tieu-nam-vang-chu-teo-tra-vinh",
        "image": "web-nuxt/public/img/entities/quan-hu-tieu-nam-vang-chu-teo-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Quán hủ tiếu Chú Tèo trên đường Nguyễn Thị Minh Khai, phường Trà Vinh, tô hủ tiếu khô trộn tỏi phi, thịt bằm, tim gan heo và trứng cút lòng đào thanh ngọt.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "quan-bun-nuoc-leo-cho-tra-vinh-tra-vinh",
        "image": "web-nuxt/public/img/entities/quan-bun-nuoc-leo-cho-tra-vinh-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Quầy bún nước lèo góc chợ trung tâm đường Trần Phú, phường Trà Vinh, hương vị mắm prohoc truyền thống hòa quyện thịt heo quay giòn bì và cá lóc đồng.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "hu-tieu-ba-tam-cau-ke-tra-vinh",
        "image": "web-nuxt/public/img/entities/hu-tieu-ba-tam-cau-ke-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Tiệm hủ tiếu Bà Tám tại thị trấn Cầu Kè, nước lèo ninh từ xương ống heo ngọt thanh tự nhiên, sợi bánh hủ tiếu gạo Cầu Kè mềm dai đặc trưng.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "quan-bun-bo-hue-hai-lua-tra-vinh",
        "image": "web-nuxt/public/img/entities/quan-bun-bo-hue-hai-lua-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Quán bún bò Hai Lúa trên đường Lê Lợi, phường Trà Vinh, tô bún bò bắp hoa nạm giòn thơm lừng mùi sả ớt phi và mắm ruốc chưng theo khẩu vị miền Trung Nam Bộ.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "quan-pho-bac-nam-hung-tra-vinh",
        "image": "web-nuxt/public/img/entities/quan-pho-bac-nam-hung-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Quán phở Bắc Năm Hùng trên đường Điện Biên Phủ, phường Trà Vinh, nồi nước dùng bò hầm thảo mộc trong vắt và bánh phở tươi mềm mịn chuẩn vị Bắc xưa.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "quan-hu-tieu-tieu-can-hu-tieu-muc-tra-vinh",
        "image": "web-nuxt/public/img/entities/quan-hu-tieu-tieu-can-hu-tieu-muc-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Quán hủ tiếu mực tại phường Tiểu Cần, mực ống tươi rói xắt khoanh dày giòn ngọt hòa cùng nước lèo nấu mực khô tôm khô thơm nức mũi.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "banh-mi-co-sau-gan-truong-ai-hoc-tra-vinh-tra-vinh",
        "image": "web-nuxt/public/img/entities/banh-mi-co-sau-gan-truong-ai-hoc-tra-vinh-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Xe bánh mì Cô Sáu gần cổng trường Đại học trên đường Nguyễn Đáng, ổ bánh mì vỏ giòn rụm nhồi đầy pa-tê gan béo ngậy, thịt xá xíu và dưa chua ngò rí.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "quan-bun-rieu-cua-cho-cu-tra-vinh-tra-vinh",
        "image": "web-nuxt/public/img/entities/quan-bun-rieu-cua-cho-cu-tra-vinh-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Quán bún riêu cua khu Chợ Cũ đường Nguyễn Thái Học, phường Long Đức, thảng thốt vị ngọt thanh riêu cua đồng xốp mềm, đậu hũ chiên vàng và cà chua đỏ au.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "hu-tieu-go-duyen-hai-tra-vinh",
        "image": "web-nuxt/public/img/entities/hu-tieu-go-duyen-hai-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Xe hủ tiếu gõ đêm trung tâm phường Duyên Hải, tô hủ tiếu nóng bốc khói ấm lòng người dân vùng biển với thịt xắt mỏng, tóp mỡ giòn và hành lá thanh tao.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "nha-hang-song-que-tra-vinh-tra-vinh",
        "image": "web-nuxt/public/img/entities/nha-hang-song-que-tra-vinh-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Nhà hàng Sông Quê trên đường Nguyễn Đáng, không gian ẩm thực ấm cúng đãi khách các món cá chép giòn om dưa và gà hấp lá chúc thơm ngát.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "quan-ca-ong-bo-song-co-chien-khu-vuc-ben-pha-co-chien-tra-vinh",
        "image": "web-nuxt/public/img/entities/quan-ca-ong-bo-song-co-chien-khu-vuc-ben-pha-co-chien-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Quán cá đồng ven bến phà Cổ Chiên cũ, đĩa cá bống kho tiêu cay nồng niêu đất và cá kèo nướng muối ớt đón gió mát rượi từ dòng sông lớn.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "nha-hang-bien-nho-ba-ong-tra-vinh",
        "image": "web-nuxt/public/img/entities/nha-hang-bien-nho-ba-ong-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Nhà hàng Biển Nhớ tại khu du lịch Ba Động, phường Trường Long Hòa, bàn ăn hướng ra sóng biển phục vụ tôm biển nướng mọi và chù ụ rang me chua ngọt.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "nha-hang-phu-sa-bo-song-tra-vinh-tra-vinh",
        "image": "web-nuxt/public/img/entities/nha-hang-phu-sa-bo-song-tra-vinh-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Nhà hàng Phù Sa bên bờ sông Long Bình, đường Lê Lợi, ẩm thực miệt vườn tinh tế với món lẩu cá linh bông điên điển và ốc bươu nhồi thịt hấp gừng.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "quan-ca-song-hai-bo-khu-vuc-cau-tra-vinh-tra-vinh",
        "image": "web-nuxt/public/img/entities/quan-ca-song-hai-bo-khu-vuc-cau-tra-vinh-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Quán cá sông Hai Bờ gần chân cầu trung tâm, các món cá mè vinh kho lạt ăn kèm xoài băm và cá chạch lấu nướng muối ớt than hồng đượm vị.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "nha-hang-thien-huong-tp-tra-vinh-tra-vinh",
        "image": "web-nuxt/public/img/entities/nha-hang-thien-huong-tp-tra-vinh-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Nhà hàng Thiên Hương trên đường Đinh Tiên Hoàng, không gian sang trọng chuyên phục vụ tiệc cưới và các món lẩu cua đồng hải sản đầy đặn.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "quan-nhau-bo-song-ba-ke-tieu-can-tra-vinh",
        "image": "web-nuxt/public/img/entities/quan-nhau-bo-song-ba-ke-tieu-can-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Quán ăn bình dân bờ sông Ba Kè, phường Tiểu Cần, không gian thoáng đãng bên rặng dừa nước phục vụ ếch đồng nướng mọi và cá lóc nướng trui giòn rụm.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "nha-hang-hai-san-lung-cot-cau-gan-cot-cau-co-chien-tra-vinh",
        "image": "web-nuxt/public/img/entities/nha-hang-hai-san-lung-cot-cau-gan-cot-cau-co-chien-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Nhà hàng hải sản Lung Cột Cầu dưới chân cầu Cổ Chiên, hải sản tươi sống đánh bắt từ cửa sông bồi đắp phù sa như tôm sú, cá chẽm và sò huyết mập mạp.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "quan-hai-san-my-long-bai-bien-my-long-tra-vinh",
        "image": "web-nuxt/public/img/entities/quan-hai-san-my-long-bai-bien-my-long-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Quán hải sản bên bờ biển Mỹ Long, mâm nghêu hấp lá quế thơm phức, cua biển gạch son luộc và mực trứng nướng mắm nhĩ đậm đà vị biển.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "chao-am-ba-nam-tra-vinh",
        "image": "web-nuxt/public/img/entities/chao-am-ba-nam-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Quán Cháo Ám Bà Năm tại số 56 Lê Lợi, phường Trà Vinh, món cháo cá lóc đồng nấu trứng cá vàng ươm, thì là và hành hoa bốc khói ngạt ngào trứ danh.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "bun-nuoc-leo-huong-tra-tra-vinh",
        "image": "web-nuxt/public/img/entities/bun-nuoc-leo-huong-tra-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Quán bún nước lèo Hương Trà tại số 260 Phạm Ngũ Lão, phường Trà Vinh, nước dùng mắm prohoc nguyên chất đậm đà, chả giò chiên vàng giòn và huyết heo tươi mềm.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "hu-tieu-xi-quach-a-linh-tra-vinh",
        "image": "web-nuxt/public/img/entities/hu-tieu-xi-quach-a-linh-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Quán Hủ Tiếu A Linh trên đường Lê Lợi, tô xí quách sườn heo hầm róc thịt chấm tương đen ớt sa tế cay nồng đi kèm bánh hủ tiếu dai ngọt.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "ha-cao-chi-tu-tra-vinh",
        "image": "web-nuxt/public/img/entities/ha-cao-chi-tu-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Quầy Há Cảo Chị Tư trên đường Nguyễn Thị Minh Khai, xửng hấp bốc khói nghi ngút với những viên há cảo tôm thịt vỏ trong veo rắc hành phi và sốt tương đậm vị.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "chao-am-cho-chau-thanh-tra-vinh",
        "image": "web-nuxt/public/img/entities/chao-am-cho-chau-thanh-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Gánh cháo ám truyền thống góc chợ Châu Thành, thịt cá lóc rỉa sạch xào hành thơm phức thả vào nồi cháo hoa nhừ mịn rắc tiêu sọ cay nồng.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "quan-bun-nuoc-leo-duong-dong-khoi-tra-vinh",
        "image": "web-nuxt/public/img/entities/quan-bun-nuoc-leo-duong-dong-khoi-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Quán bún nước lèo tại số 94A Đồng Khởi, tô bún đầy đặn cá lóc luộc, thịt heo quay da giòn và rổ rau ghém hoa chuối, hẹ lá xanh mướt.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    }
]

assert len(batch_32_data) == 40

with open("outputs/batch_restaurants_part3_photos.json", "w", encoding="utf-8") as f:
    json.dump(batch_32_data, f, ensure_ascii=False, indent=2)
    f.write("\n")

print("Generated outputs/batch_restaurants_part3_photos.json with 40 entries!")
