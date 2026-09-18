import json

batch_33_data = [
    # 46 Restaurants (Hoàn tất 100% Khối Nhà hàng & Quán ăn Truyền thống: 186/186)
    {
        "entity_id": "quan-com-binh-dan-cho-tra-vinh-tra-vinh",
        "image": "web-nuxt/public/img/entities/quan-com-binh-dan-cho-tra-vinh-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Quán cơm bình dân góc chợ trung tâm phường Trà Vinh, các khay cá kho tộ, thịt kho trứng và canh chua cá lóc thơm phức đãi khách lao động mỗi trưa.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "quan-com-tam-sau-tinh-tra-vinh",
        "image": "web-nuxt/public/img/entities/quan-com-tam-sau-tinh-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Quán cơm tấm Sáu Tịnh trên đường Nguyễn Thị Minh Khai, phường Trà Vinh, miếng sườn nướng mỡ hành đượm vị mật ong ăn kèm chả trứng và bì heo bùi béo.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "quan-nhau-ben-ca-tra-vinh-tra-vinh",
        "image": "web-nuxt/public/img/entities/quan-nhau-ben-ca-tra-vinh-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Quán ăn bình dân khu vực bến cá phường Trà Vinh, đón hải sản tươi rói từ ghe cào: cá khoai nấu ngót, tôm bạc luộc nước dừa và ốc cà na xào bơ tỏi.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "quan-di-bay-com-nieu-tra-vinh",
        "image": "web-nuxt/public/img/entities/quan-di-bay-com-nieu-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Quán Dì Bảy Cơm Niêu tại phường Long Đức, niêu cơm trắng dẻo thơm cháy giòn đáy nồi ăn cùng cá bống kho tiêu cay nồng và canh cua đồng mồng tơi.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "quan-com-binh-dan-ut-huong-tra-vinh",
        "image": "web-nuxt/public/img/entities/quan-com-binh-dan-ut-huong-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Quán cơm Út Hương trên đường Điện Biên Phủ, phường Trà Vinh, bữa trưa đượm vị gia đình với sườn ram mặn ngọt, tép xào bông điên điển và canh rau tập tàng.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "quan-nhau-vuon-dua-tieu-can-tra-vinh",
        "image": "web-nuxt/public/img/entities/quan-nhau-vuon-dua-tieu-can-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Quán ăn Vườn Dừa tại xã Nhị Long, chòi lá rợp bóng dừa mát rượi đãi khách món gà thả vườn nướng đất sét và lươn đồng xào sả ớt.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "quan-com-ba-hai-cho-cang-long-tra-vinh",
        "image": "web-nuxt/public/img/entities/quan-com-ba-hai-cho-cang-long-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Quán cơm Bà Hai bên lồng chợ Càng Long, xã Nhị Long, đĩa cơm thơm nóng sốt dẻo với cá rô kho tộ và đĩa rau luộc chấm kho quẹt đậm đà.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "quan-nhau-hai-san-bien-ba-dong-tra-vinh",
        "image": "web-nuxt/public/img/entities/quan-nhau-hai-san-bien-ba-dong-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Quán hải sản ven bãi biển Ba Động, phường Trường Long Hòa, phục vụ ghẹ hấp bia, tôm tít rang muối và mực một nắng nướng sa tế giòn ngọt.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "nha-hang-lang-be-ben-tre-ben-tre",
        "image": "web-nuxt/public/img/entities/nha-hang-lang-be-ben-tre-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Nhà hàng Làng Bè trên đường Đồng Văn Cống, xã Tân Phú, cụm bè nổi mặt nước đón gió mát phục vụ cá tai tượng chiên xù và tôm càng xanh nướng mọi.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "am-thuc-chay-hoa-sen-vinh-long",
        "image": "web-nuxt/public/img/entities/am-thuc-chay-hoa-sen-vinh-long.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Quán Ẩm Thực Chay Hoa Sen tại số 191/2 Đường Lò Rèn, phường 4, không gian thanh tịnh phục vụ bún huế chay, lẩu nấm và chả giò phù trúc vàng ươm giòn rụm.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "com-chay-thanh-dam-vinh-long",
        "image": "web-nuxt/public/img/entities/com-chay-thanh-dam-vinh-long.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Quán Cơm Chay Thanh Đạm tại số 101 Đường 2/9, phường 1, khay cơm tự chọn phong phú với đậu hũ kho nấm đông cô, sườn non chay rim mặn và canh rong biển.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "quan-chay-an-lac-vinh-long",
        "image": "web-nuxt/public/img/entities/quan-chay-an-lac-vinh-long.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Quán Chay An Lạc tại số 33/19B Phạm Thái Bường, phường 4, nổi tiếng với món cơm tấm sườn chả chay và hủ tiếu chay nấu từ củ quả ngọt thanh tự nhiên.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "quan-chay-chua-phat-hoc-tra-vinh",
        "image": "web-nuxt/public/img/entities/quan-chay-chua-phat-hoc-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Quán cơm chay cạnh chùa Phật Học trên đường Điện Biên Phủ, xã Nhị Long, đãi khách thập phương bữa cơm chay thanh đạm với nấm kho tiêu và canh chua bắp chuối.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "quan-chao-ca-ro-dong-cho-cau-ke-tra-vinh",
        "image": "web-nuxt/public/img/entities/quan-chao-ca-ro-dong-cho-cau-ke-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Quán cháo cá rô đồng khu chợ Cầu Kè, xã Cầu Kè, thịt cá rô đồng béo ngậy rỉa sạch xương xào thơm thả vào nồi cháo hoa ăn cùng rau đắng đất.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "quan-hu-tieu-nguoi-hoa-khu-phuong-1-tra-vinh",
        "image": "web-nuxt/public/img/entities/quan-hu-tieu-nguoi-hoa-khu-phuong-1-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Tiệm hủ tiếu truyền thống của người Hoa trên đường Lê Lợi, phường Trà Vinh, sợi bánh mềm dai nước dùng ngọt tủy xương heo ninh kỹ ăn cùng xá xíu thơm lừng.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "quan-banh-canh-ben-co-tra-vinh",
        "image": "web-nuxt/public/img/entities/quan-banh-canh-ben-co-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Quán bánh canh Bến Có trứ danh trên đường Trần Phú, xã Nhị Long, tô bánh canh bột gạo xắt tay nước dùng trong ngọt ngập tràn lòng heo tươi giòn.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "quan-com-chay-gan-chua-ang-angkor-rajaborei-tra-vinh",
        "image": "web-nuxt/public/img/entities/quan-com-chay-gan-chua-ang-angkor-rajaborei-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Quán cơm chay gần khuôn viên chùa Âng trên đường Ngô Quyền, phường Trà Vinh, thực đơn thanh tịnh từ rau củ quả miệt vườn đãi phật tử và du khách.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "quan-lau-mam-mien-tay-cho-tieu-can-tra-vinh",
        "image": "web-nuxt/public/img/entities/quan-lau-mam-mien-tay-cho-tieu-can-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Quán lẩu mắm đậm đà tại chợ Tiểu Cần, phường Tiểu Cần, nồi nước lẩu mắm cá linh sôi bùng khói ăn kèm bông so đũa, kèo nèo và rau nhút giòn sần sật.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "quan-chay-tinh-xa-ngoc-tra-vinh",
        "image": "web-nuxt/public/img/entities/quan-chay-tinh-xa-ngoc-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Quán chay Tịnh Xá Ngọc Quang trên đường Phạm Thái Bường, xã Nhị Long, phục vụ các món bún riêu chay, mì quảng chay và gỏi cuốn rau củ thanh khiết.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "khu-pho-am-thuc-bo-ho",
        "image": "web-nuxt/public/img/entities/khu-pho-am-thuc-bo-ho.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Khu phố ẩm thực bờ hồ Trúc Giang, phường An Hội, nhộn nhịp hàng quán về đêm với bánh tráng nướng mỡ hành, chè bưởi và ốc biển đủ món.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "lau-ca-linh-bong-dien-dien",
        "image": "web-nuxt/public/img/entities/lau-ca-linh-bong-dien-dien.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Quán lẩu cá linh bông điên điển tại phường 1, TP Vĩnh Long, mùa nước nổi đãi khách nồi lẩu cá linh non béo ngậy ngập tràn sắc vàng bông điên điển đầu mùa.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "nha-hang-noi-ben-tre",
        "image": "web-nuxt/public/img/entities/nha-hang-noi-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Nhà hàng nổi trên bến Hùng Vương, phường Bến Tre, không gian ẩm thực trên dòng sông mát rượi đón gió sông phục vụ cá chẽm sốt chua ngọt và tôm hấp nước dừa.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "quan-banh-uot-hai-nen",
        "image": "web-nuxt/public/img/entities/quan-banh-uot-hai-nen.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Quán Bánh Ướt Hai Nền tại số 43 Phan Ngọc Tòng, phường Bến Tre, lớp bánh tráng mỏng mềm mướt tráng tại chỗ rắc hành phi ăn kèm nem chua và chả lụa thơm lừng.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "lau-3-con-tep",
        "image": "web-nuxt/public/img/entities/lau-3-con-tep.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Quán Lẩu 3 Con Tép tại phường Bến Tre, chuyên các món lẩu hải sản tôm càng, mực ống và cá hồi tươi rói trong thố nước dùng chua cay đậm đà.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "mai-bingsu---vincom-plaza-vinh-long",
        "image": "web-nuxt/public/img/entities/mai-bingsu---vincom-plaza-vinh-long.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Quán Mai Bingsu tại tầng 4 Vincom Plaza Vĩnh Long, đường Phạm Thái Bường, món bingsu đá tuyết dưa lưới và xoài chín phủ kem sữa béo ngậy ngọt mát.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "kem-baskin-robbins---sense-city",
        "image": "web-nuxt/public/img/entities/kem-baskin-robbins---sense-city.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Cửa hàng kem Baskin Robbins tại trung tâm thương mại Sense City, đường Trần Quốc Tuấn, phường Bến Tre, phong phú vị kem ngoại nhập mát lạnh.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "lucid-dream---tea-cake",
        "image": "web-nuxt/public/img/entities/lucid-dream---tea-cake.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Tiệm trà bánh Lucid Dream tại số 130/4D Nguyễn Văn Nguyễn, phường Bến Tre, không gian ấm cúng phục vụ các set trà hoa thanh tao và bánh ngọt thủ công.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "banh-mi-co-lan-duong-hung-vuong-ben-tre",
        "image": "web-nuxt/public/img/entities/banh-mi-co-lan-duong-hung-vuong-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Tiệm bánh mì Cô Lan trên đường Hùng Vương, phường Phú Khương, ổ bánh mì giòn tan kẹp thịt xá xíu, chả lụa và pa-tê nhà làm thơm ngậy.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "com-tam-suon-bi-cha",
        "image": "web-nuxt/public/img/entities/com-tam-suon-bi-cha.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Quán cơm tấm sườn bì chả tại phường Long Châu, đĩa cơm hạt tấm nhuyễn thơm dẻo với miếng sườn ướp đậm đà nướng xém cạnh trên than hồng.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "nha-hang-lang-chai-ben-tre-ben-tre",
        "image": "web-nuxt/public/img/entities/nha-hang-lang-chai-ben-tre-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Nhà hàng Làng Chài tại số 17A10 Đồng Văn Cống, phường Bến Tre, hải sản tươi sống chọn trực tiếp từ bể: cua biển rang me, sò huyết cháy tỏi thơm nức.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "nha-hang-ham-luong-ben-tre",
        "image": "web-nuxt/public/img/entities/nha-hang-ham-luong-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Khách sạn nhà hàng Hàm Luông tại số 200C Hùng Vương, phường Bến Tre, hướng tầm nhìn ra ngã ba sông Hàm Luông phục vụ tiệc và ẩm thực Nam Bộ tinh túy.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "am-thuc-ngo-dong-ben-tre",
        "image": "web-nuxt/public/img/entities/am-thuc-ngo-dong-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Nhà hàng Ẩm Thực Ngô Đồng tại số 165B Đồng Khởi, phường Bến Tre, không gian ẩm thực gia đình ấm cúng với món lẩu gà nòi lá giang và cá lóc kho nghệ.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "com-tam-cay-sung",
        "image": "web-nuxt/public/img/entities/com-tam-cay-sung.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Quán Cơm Tấm Cây Sung tại số 249 Phạm Hùng, phường 9, nức tiếng với đĩa cơm sườn cọng nướng mềm ngọt ăn cùng trứng ốp-la lòng đào béo ngậy.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "meo-u-kitchen---mon-nhat",
        "image": "web-nuxt/public/img/entities/meo-u-kitchen---mon-nhat.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Quán Mèo Ú Kitchen trong hẻm 1 Hoàng Thái Hiếu, phường 1, chuyên ẩm thực Nhật Bản với các cuộn sushi cá hồi, cơm lươn nướng và mì ramen đậm đà.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "martini-cocktail-tea",
        "image": "web-nuxt/public/img/entities/martini-cocktail-tea.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Quán Martini Cocktail & Tea tại số 18 Trưng Nữ Vương, phường 1, không gian đồ uống pha chế sáng tạo bên bờ kè sông mát rượi.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "lau-mam-mien-tay",
        "image": "web-nuxt/public/img/entities/lau-mam-mien-tay.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Quán lẩu mắm miệt vườn tại xã An Bình, cù lao rợp bóng cây ăn trái đãi khách nồi lẩu mắm cá sặc đầy ắp cá đồng, mực tươi và đĩa rau vườn phong phú.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "lau-bo-bay-map",
        "image": "web-nuxt/public/img/entities/lau-bo-bay-map.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Quán Lẩu Bò Bảy Mập tại ấp Long Thuận A, xã Long Phước, nồi lẩu đuôi bò hầm củ sen thơm lừng nước dùng thảo mộc ăn kèm rau cải xanh tươi sạch.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "quan-vteen---pham-hung",
        "image": "web-nuxt/public/img/entities/quan-vteen---pham-hung.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Quán ăn vặt Vteen tại số 247A Phạm Hùng, phường 9, điểm hẹn quen thuộc của học sinh sinh viên với trà sữa trân châu, cá viên chiên và bánh tráng trộn.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "quan-com-chay-lac-vien-vinh-long",
        "image": "web-nuxt/public/img/entities/quan-com-chay-lac-vien-vinh-long.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Quán Cơm Chay Lạc Viên tại số 3 Phạm Hùng, phường 2, không gian thanh tịnh phục vụ cơm chay bình dân đủ món kho, xào, canh ngon miệng ấm lòng.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "quan-chi-yen---trai-cay-dia",
        "image": "web-nuxt/public/img/entities/quan-chi-yen---trai-cay-dia.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Quán Chị Yến trên đường Tỉnh 884, phường Sơn Đông, đĩa trái cây tươi cắt lát đủ loại xoài, mít, thanh long chan sữa chua và đá bào mát lạnh.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "pho-tien",
        "image": "web-nuxt/public/img/entities/pho-tien.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Quán Phở Tiên tại phường Mỏ Cày, tô phở bò tái nạm gầu giòn thơm phức nước dùng ninh xương hoa hồi truyền thống.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "tau-nha-hang-sai-gon-vinh-long",
        "image": "web-nuxt/public/img/entities/tau-nha-hang-sai-gon-vinh-long.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Tàu nhà hàng Sài Gòn Vĩnh Long tại số 04 Hưng Đạo Vương, phường Long Châu, du thuyền phục vụ ẩm thực trên sông Cổ Chiên ngắm cầu Mỹ Thuận về đêm.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "hai-san-ngoc-hiep-binh-dai-ben-tre",
        "image": "web-nuxt/public/img/entities/hai-san-ngoc-hiep-binh-dai-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Quán Hải Sản Ngọc Hiệp trên đường Lê Hoàng Chiếu, thị trấn Bình Đại, đặc sản cua biển gạch son luộc sả và sò huyết rang muối ớt đậm đà vị biển.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "nha-hang-hai-san-song-tra-binh-dai-ben-tre",
        "image": "web-nuxt/public/img/entities/nha-hang-hai-san-song-tra-binh-dai-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Nhà hàng Hải Sản Sông Trà tại xã Thạnh Ngãi ven bờ sông, thực đơn hải sản tươi sống đa dạng: tôm sú nướng, cá chẽm hấp nấm và lẩu nghêu chua cay.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "quan-nhau-dong-que-cau-ke-tra-vinh",
        "image": "web-nuxt/public/img/entities/quan-nhau-dong-que-cau-ke-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Quán Đồng Quê tại Cầu Kè, xã Nhị Long, phục vụ các món nhậu đồng dã: chim sẻ rô-ti, ếch đồng xào lăn và cá lóc đồng nướng trui trọn vị quê nhà.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "quan-an-ly-thong-ben-tre",
        "image": "web-nuxt/public/img/entities/quan-an-ly-thong-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Quán Ăn Lý Thông tại phường An Hội, điểm hẹn ẩm thực đêm quen thuộc với các món nướng than hoa, lẩu hải sản và cánh gà chiên nước mắm đậm đà.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    }
]

assert len(batch_33_data) == 46

with open("outputs/batch_restaurants_final_photos.json", "w", encoding="utf-8") as f:
    json.dump(batch_33_data, f, ensure_ascii=False, indent=2)
    f.write("\n")

print("Generated outputs/batch_restaurants_final_photos.json with 46 entries!")
