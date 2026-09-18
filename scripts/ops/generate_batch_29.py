import json

batch_29_data = [
    # 27 Cafes (Hoàn tất 100% Khối Cà Phê Văn Hóa & Trà Toàn Tỉnh: 56/56)
    {
        "entity_id": "gazebo-cafe",
        "image": "web-nuxt/public/img/entities/gazebo-cafe.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Gazebo Cafe trên đường Nguyễn Thị Minh Khai, phường 7, sở hữu không gian sân vườn thoáng đãng rợp bóng cây xanh và hồ cá thư giãn.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "che-ba-cam-khu-vuc-cho-ben-tre-ben-tre",
        "image": "web-nuxt/public/img/entities/che-ba-cam-khu-vuc-cho-ben-tre-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Quán chè bà Cẩm góc chợ trung tâm phường Phú Khương nức tiếng với chè thưng, chè đậu trắng nước cốt dừa béo ngậy nấu theo lối xưa.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "ca-phe-xua-tra-vinh",
        "image": "web-nuxt/public/img/entities/ca-phe-xua-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Cà phê Xưa trên đường Nguyễn Đáng tái hiện nét sinh hoạt Nam Bộ xưa với bàn ghế gỗ mộc, đèn dầu và giai điệu trữ tình lắng đọng.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "ca-phe-song-tien-ben-ninh-kieu-vinh-long-vinh-long",
        "image": "web-nuxt/public/img/entities/ca-phe-song-tien-ben-ninh-kieu-vinh-long-vinh-long.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Quán cà phê ven bờ kè sông Cổ Chiên trên đường Trưng Nữ Vương, phường 1, nơi đón gió sông lồng lộng và ngắm ghe đò xuôi ngược.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "ca-phe-vuon-cau-khu-con-phung-con-phuoc-vinh-long",
        "image": "web-nuxt/public/img/entities/ca-phe-vuon-cau-khu-con-phung-con-phuoc-vinh-long.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Cà phê Vườn Cau trên cồn Phước rợp bóng hàng cau thẳng tắp, không khí miệt vườn trong lành đãi khách ngụm trà mật ong phấn hoa thơm ngát.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "ca-phe-highland-vincom-vinh-long-vinh-long",
        "image": "web-nuxt/public/img/entities/ca-phe-highland-vincom-vinh-long-vinh-long.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Không gian hiện đại tại cà phê Highland tầng trệt Vincom Plaza, đường Phạm Thái Bường, phường 4, điểm dừng chân quen thuộc của người dân phố thị.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "quan-che-ba-tu-cho-vinh-long-vinh-long",
        "image": "web-nuxt/public/img/entities/quan-che-ba-tu-cho-vinh-long-vinh-long.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Quầy chè Bà Tư trong lồng chợ Vĩnh Long đường Hùng Vương, phường 1, với đủ nồi chè bưởi, chè khoai môn, sương sáo hột é ngọt mát lành.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "kem-dat-vinh-long-khu-cau-lau-vinh-long",
        "image": "web-nuxt/public/img/entities/kem-dat-vinh-long-khu-cau-lau-vinh-long.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Quán kem xôi dừa và kem đất truyền thống khu Cầu Lầu trên đường Nguyễn Huệ, phường 2, gắn liền với ký ức bao thế hệ học trò.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "sinh-to-ha-tien-duong-pham-thai-buong-vinh-long",
        "image": "web-nuxt/public/img/entities/sinh-to-ha-tien-duong-pham-thai-buong-vinh-long.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Tiệm sinh tố Hà Tiên trên đường Phạm Thái Bường, phường 4, chuyên các món dầm trái cây tươi ngon như bơ, mãng cầu, dâu tây miệt vườn.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "che-khuc-bach-khu-dem-vinh-long-cho-dem-phuong-1-vinh-long",
        "image": "web-nuxt/public/img/entities/che-khuc-bach-khu-dem-vinh-long-cho-dem-phuong-1-vinh-long.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Quán chè khúc bạch thanh mát tại chợ đêm đường 2 Tháng 9, phường 1, điểm dạo mát về đêm nhộn nhịp của các bạn trẻ.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "quan-che-ba-hai-cho-tra-vinh",
        "image": "web-nuxt/public/img/entities/quan-che-ba-hai-cho-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Gánh chè bà Hai góc đường Trần Phú tại chợ trung tâm bày biện hàng chục vị chè truyền thống, đậm đà nước cốt dừa thắng sánh mịn.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "ca-phe-bo-song-tra-vinh",
        "image": "web-nuxt/public/img/entities/ca-phe-bo-song-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Cà phê Bờ Sông trên đường Lê Lợi chạy dọc rạch Long Bình, không gian đón gió tự nhiên và ngắm hàng bần nở hoa rủ bóng ven bờ.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "quan-che-banh-lot-khmer-gan-ao-ba-om-tra-vinh",
        "image": "web-nuxt/public/img/entities/quan-che-banh-lot-khmer-gan-ao-ba-om-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Quán chè bánh lọt nước cốt dừa và đường thốt nốt Khmer nép mình dưới rặng sao cổ thụ Ao Bà Om, vị ngọt thanh mát dịu.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "ca-phe-vuon-dua-tra-vinh",
        "image": "web-nuxt/public/img/entities/ca-phe-vuon-dua-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Cà phê Vườn Dừa tại phường Hòa Thuận với những chòi lá mộc mạc dựng giữa liếp dừa xiêm, đón gió đồng mát rượi.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "quan-kem-sinh-to-thanh-binh-tra-vinh",
        "image": "web-nuxt/public/img/entities/quan-kem-sinh-to-thanh-binh-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Quán kem và sinh tố Thanh Bình trên đường Đinh Tiên Hoàng, phục vụ các món kem dừa và nước ép trái cây giải nhiệt tươi ngon.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "tiem-banh-che-gan-chua-ang-angkor-borei-tra-vinh",
        "image": "web-nuxt/public/img/entities/tiem-banh-che-gan-chua-ang-angkor-borei-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Tiệm bánh chè Khmer gần cổng chùa Âng bán bánh cúng, bánh tét lá cẩm và chè thốt nốt thơm lừng phục vụ du khách trẩy hội Ok Om Bok.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "ca-phe-cay-bang-phuong-4-tra-vinh",
        "image": "web-nuxt/public/img/entities/ca-phe-cay-bang-phuong-4-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Quán cà phê Cây Bàng rợp bóng mát trên đường Phạm Thái Bường, phường Long Đức, điểm ngồi hàn huyên chuyện đồng áng quen thuộc.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "quan-sinh-to-nuoc-ep-cho-dem-tra-vinh",
        "image": "web-nuxt/public/img/entities/quan-sinh-to-nuoc-ep-cho-dem-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Xe sinh tố nước ép chợ đêm đường Trần Phú đầy ắp quả tươi từ các nhà vườn, xay nhuyễn tại chỗ giữ nguyên vitamin bổ dưỡng.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "ca-phe-ho-sen-tra-vinh",
        "image": "web-nuxt/public/img/entities/ca-phe-ho-sen-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Cà phê Hồ Sen ven hồ trung tâm trên đường Lý Thường Kiệt, nơi ngắm hoa sen nở rộ thơm ngát vào mỗi buổi sớm mai trong lành.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "zen-coffee",
        "image": "web-nuxt/public/img/entities/zen-coffee.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Zen Coffee trên đường Trần Đại Nghĩa, phường 4, thiết kế theo phong cách thiền tĩnh lặng với sỏi trắng và tiếng nước chảy róc rách.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khoi-nguyen-coffee---hung-dao-vuong",
        "image": "web-nuxt/public/img/entities/khoi-nguyen-coffee---hung-dao-vuong.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Khởi Nguyên Coffee đường Hưng Đạo Vương nối dài, không gian rộng rãi thích hợp cho các buổi gặp gỡ công việc và đọc sách.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "henry-coffee",
        "image": "web-nuxt/public/img/entities/henry-coffee.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Henry Coffee trên đường Trưng Nữ Vương, phường 1, phong cách kiến trúc hiện đại nhìn thẳng ra công viên bờ sông Cổ Chiên thơ mộng.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "brownie-coffee-and-tea",
        "image": "web-nuxt/public/img/entities/brownie-coffee-and-tea.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Brownie Coffee And Tea trên đường Nguyễn Thị Minh Khai, phường 1, ghi điểm với các món bánh nướng mềm thơm và trà ủ lạnh thanh vị.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "bin-coffee",
        "image": "web-nuxt/public/img/entities/bin-coffee.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Bin Coffee số 152 Trưng Nữ Vương, phường 1, địa điểm dừng chân nhỏ xinh với tách cà phê phin đậm đà hương thơm nồng nàn.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "tra-sua-tapi---trung-nu-vuong",
        "image": "web-nuxt/public/img/entities/tra-sua-tapi---trung-nu-vuong.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Trà Sữa Tapi trên đường Trưng Nữ Vương, phường 1, quán trà sữa trẻ trung với nhiều loại thạch củ năng giòn ngọt tự làm khéo léo.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "tra-sua-family---dong-khoi",
        "image": "web-nuxt/public/img/entities/tra-sua-family---dong-khoi.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Trà Sữa Family trên đường Đồng Khởi, phường Phú Khương, quán ăn vặt và trà sữa thơm ngon phục vụ đông đảo thực khách trẻ.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "full-house-coffee",
        "image": "web-nuxt/public/img/entities/full-house-coffee.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Full House Coffee hẻm đường Nguyễn Huệ, phường 2, không gian ấm cúng yên tĩnh tách biệt khỏi sự hối hả của nhịp sống phố thị.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },

    # 13 Traditional Specialty Restaurants (Quán ăn & Nhà hàng đặc sản bản địa)
    {
        "entity_id": "ut-an---vuon-am-thuc",
        "image": "web-nuxt/public/img/entities/ut-an---vuon-am-thuc.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Vườn Ẩm Thực Út An tại khu phố Bình Khởi, phường Sơn Đông, phục vụ các món cá tai tượng chiên xù cuốn bánh tráng miệt vườn thơm giòn.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "am-thuc-chay-ta-on---duong-so-2",
        "image": "web-nuxt/public/img/entities/am-thuc-chay-ta-on---duong-so-2.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Nhà hàng Ẩm Thực Chay Tạ Ơn trên Đường Số 2, phường Bến Tre, nổi tiếng với thực đơn thanh tịnh chế biến từ nấm và rau củ tươi sạch.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "lang-be---am-thuc-du-lich-sinh-thai",
        "image": "web-nuxt/public/img/entities/lang-be---am-thuc-du-lich-sinh-thai.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Khu ẩm thực sinh thái Làng Bè bên sông Tiền, phường Phú Túc, nơi du khách thưởng thức cá lăng nấu ngót và tôm càng nướng mọi trên bè nổi.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "quan-71---am-thuc-chay-xoi-che",
        "image": "web-nuxt/public/img/entities/quan-71---am-thuc-chay-xoi-che.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Quán 71 trên đường 30 Tháng 4, phường Bến Tre, chuyên xôi vò, chè hoa cau và các món ăn chay truyền thống đậm đà phong vị xứ dừa.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "nha-hang-lang-chai",
        "image": "web-nuxt/public/img/entities/nha-hang-lang-chai.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Nhà Hàng Làng Chài trên đường Đồng Văn Cống, phường Sơn Đông, cung cấp hải sản bến biển tươi rói và cá bống dừa kho tộ cay nồng.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "song-nuoc-mien-tay-restaurant---am-thuc-mien-tay",
        "image": "web-nuxt/public/img/entities/song-nuoc-mien-tay-restaurant---am-thuc-mien-tay.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Nhà hàng Sông Nước Miền Tây tại phường Phú Túc với không gian nhà mái lá ven sông, nổi danh món lẩu mắm cá linh bông điên điển mùa nước nổi.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "hu-tieu-xi-quach-a-linh---le-loi",
        "image": "web-nuxt/public/img/entities/hu-tieu-xi-quach-a-linh---le-loi.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Quán hủ tiếu xí quách A Linh trên đường Lê Lợi, phường 1, nồi nước dùng hầm xương ống ngọt lịm ăn cùng cọng hủ tiếu dai mềm trứ danh.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "bun-nuoc-leo---ly-thuong-kiet",
        "image": "web-nuxt/public/img/entities/bun-nuoc-leo---ly-thuong-kiet.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Quán bún nước lèo góc đường Lý Thường Kiệt, phường 1, đậm đà mắm bò hóc truyền thống ăn kèm thịt heo quay da giòn và bắp chuối bào tươi.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "bun-nuoc-leo-huong-tra---pham-ngu-lao",
        "image": "web-nuxt/public/img/entities/bun-nuoc-leo-huong-tra---pham-ngu-lao.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Bún Nước Lèo Hương Trà trên đường Phạm Ngũ Lão, tô bún thơm phức mùi ngải bún và tép bạc tươi luộc ngọt nước.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "quan-tuyet---com-ca-ri-ga",
        "image": "web-nuxt/public/img/entities/quan-tuyet---com-ca-ri-ga.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Quán Tuyết trên đường Trần Phú với món cơm cà ri gà nấu theo công thức gia truyền, nước sốt sánh vàng béo ngậy vị nước cốt dừa tươi.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "de-nhat-lau-ca-keo---quan-an-gia-dinh",
        "image": "web-nuxt/public/img/entities/de-nhat-lau-ca-keo---quan-an-gia-dinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Quán Đệ Nhất Lẩu Cá Kèo trên đường Phạm Ngũ Lão, cá kèo sống quẫy đuôi thả vào nồi lẩu lá giang chua cay nghi ngút khói thơm lừng.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "chau-dong-quan---am-thuc-viet",
        "image": "web-nuxt/public/img/entities/chau-dong-quan---am-thuc-viet.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Châu Đồng Quán trên đường Đồng Khởi, khóm 9, phục vụ các món ốc bươu hấp tiêu xanh và cá lóc đồng kho quéo niêu đất đậm đà bản sắc.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "quan-tom-cang-xanh-hai-lua-cu-lao-an-binh-vinh-long",
        "image": "web-nuxt/public/img/entities/quan-tom-cang-xanh-hai-lua-cu-lao-an-binh-vinh-long.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Quán Hai Lúa trên cù lao An Bình đón khách bằng đĩa tôm càng xanh nướng muối ớt gạch son béo ngậy vừa bắt lên từ vèo sông mát rượi.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    }
]

assert len(batch_29_data) == 40

with open("outputs/batch_cafes_restaurants_part1_photos.json", "w", encoding="utf-8") as f:
    json.dump(batch_29_data, f, ensure_ascii=False, indent=2)
    f.write("\n")

print("Generated outputs/batch_cafes_restaurants_part1_photos.json with 40 entries!")
