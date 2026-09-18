import json

batch_35_data = [
    # 40 Products / OCOP & Local Terroir Specialties (Batch 35)
    {
        "entity_id": "banh-trang-ngot-le-hang-htx-banh-trang-cu-lao-may",
        "image": "web-nuxt/public/img/entities/banh-trang-ngot-le-hang-htx-banh-trang-cu-lao-may.webp",
        "author": "Ngọc Trảng",
        "source": "Báo Vĩnh Long",
        "caption": "Bánh tráng ngọt Lệ Hằng của HTX bánh tráng Cù Lao Mây phơi trên vỉ tre, sản phẩm OCOP đạt tiêu chuẩn xuất khẩu sang thị trường Nhật Bản và Hoa Kỳ.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "kho-ca-loc-phu-thanh",
        "image": "web-nuxt/public/img/entities/kho-ca-loc-phu-thanh.webp",
        "author": "Ngọc Trảng",
        "source": "Báo Vĩnh Long",
        "caption": "Những nong cá lóc xẻ thịt ướp muối ớt phơi dưới nắng giòn tại xã Phú Thành trên cù lao Mây, thớ thịt đỏ hồng đượm vị mặn ngọt tự nhiên.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "dua-xiem-xanh-giong-trom",
        "image": "web-nuxt/public/img/entities/dua-xiem-xanh-giong-trom.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Những buồng dừa xiêm xanh Giồng Trôm trĩu quả đạt chứng nhận OCOP, nước dừa ngọt thanh và cùi dừa mềm dẻo đặc trưng của đất cù lao.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "ca-chuon-kho-binh-dai",
        "image": "web-nuxt/public/img/entities/ca-chuon-kho-binh-dai.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Sản phẩm cá chuồn phơi khô Anfoods tại Bình Đại đạt chuẩn OCOP, cá chuồn biển tươi được sơ chế và phơi nắng tự nhiên giữ nguyên vị ngọt đậm của biển khơi.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "tom-kho-binh-dai",
        "image": "web-nuxt/public/img/entities/tom-kho-binh-dai.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Tôm khô sinh thái rừng ngập mặn Bình Đại màu đỏ tự nhiên, thịt tôm săn chắc và ngọt dẻo đạt chuẩn OCOP 4 sao không phẩm màu nhân tạo.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "mut-dua-huu-co-binh-dai",
        "image": "web-nuxt/public/img/entities/mut-dua-huu-co-binh-dai.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Hộp mứt dừa hữu cơ Bình Đại chế biến từ cơm dừa bánh tẻ canh tác hữu cơ, sợi mứt mềm béo nhẹ với đường mía thô tự nhiên.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "kho-ca-keo-duyen-hai",
        "image": "web-nuxt/public/img/entities/kho-ca-keo-duyen-hai.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Khô cá kèo Duyên Hải ướp tiêu ớt phơi nắng tự nhiên đạt chứng nhận OCOP 3 sao, thịt cá béo ngọt đặc trưng của vùng bãi bồi ven biển.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "cua-lot-vinacrab-long-toan",
        "image": "web-nuxt/public/img/entities/cua-lot-vinacrab-long-toan.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Sản phẩm cua lột Vinacrab Long Toàn đóng gói hút chân không đạt OCOP, lớp vỏ mềm giàu canxi và thịt cua ngọt thơm phục vụ ẩm thực cao cấp.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "tau-hu-ky-my-hoa",
        "image": "web-nuxt/public/img/entities/tau-hu-ky-my-hoa.webp",
        "author": "Thanh Đức",
        "source": "Báo Vĩnh Long",
        "caption": "Thợ làng nghề Mỹ Hòa khéo léo dùng dao vớt màng tàu hủ ky vàng óng trên chảo đun sữa đậu nành, nghề thủ công truyền thống đạt OCOP và di sản quốc gia.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "buoi-da-xanh-cho-lach",
        "image": "web-nuxt/public/img/entities/buoi-da-xanh-cho-lach.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Trái bưởi da xanh Chợ Lách tròn đều căng mọng, tép bưởi hồng tươi róc vỏ ngọt thanh không hạt được cấp chỉ dẫn địa lý và xuất khẩu chính ngạch.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "chom-chom-an-binh",
        "image": "web-nuxt/public/img/entities/chom-chom-an-binh.webp",
        "author": "Ngọc Trảng",
        "source": "Báo Vĩnh Long",
        "caption": "Chùm chôm chôm Java chín đỏ rực rỡ trĩu cành trên cù lao An Bình, cùi dày giòn tróc hạt ngọt đậm phù sa sông Tiền đãi khách du lịch.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "thanh-tra-binh-minh",
        "image": "web-nuxt/public/img/entities/thanh-tra-binh-minh.webp",
        "author": "Thanh Đức",
        "source": "Báo Vĩnh Long",
        "caption": "Chùm trái thanh trà ngọt vỏ mỏng vàng ươm mọng nước tại thị xã Bình Minh, quả đặc sản quý hiếm tỏa hương thơm thảo mộc khó quên.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "nem-vung-liem",
        "image": "web-nuxt/public/img/entities/nem-vung-liem.webp",
        "author": "Ngọc Trảng",
        "source": "Báo Vĩnh Long",
        "caption": "Đòn nem chua Vũng Liêm gói lá chuối truyền thống, lên men tự nhiên với thịt nạc heo tươi, tỏi ớt xắt lát và tiêu sọ thơm nồng.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "com-dep-khmer",
        "image": "web-nuxt/public/img/entities/com-dep-khmer.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Mẻ cốm dẹp nếp non vừa giã cối xong trộn cùng dừa nạo và đường cát trắng, phong vị ẩm thực lễ hội Ok Om Bok thiêng liêng của đồng bào Khmer.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "tom-duyen-hai",
        "image": "web-nuxt/public/img/entities/tom-duyen-hai.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Thu hoạch tôm sú nước lợ sinh thái tại thị xã Duyên Hải, tôm đạt kích cỡ lớn vỏ bóng xanh đen và cơ thịt chắc khỏe cung cấp cho các nhà máy chế biến.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "thanh-tra",
        "image": "web-nuxt/public/img/entities/thanh-tra.webp",
        "author": "Ngọc Trảng",
        "source": "Báo Vĩnh Long",
        "caption": "Những rổ trái thanh trà chín vàng tươi rói bày bán ven quốc lộ, hương vị chua thanh dịu mát làm nên nét ẩm thực hoa trái độc đáo của vùng.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "ca-da-tron-nuoi-nuoc-ngot",
        "image": "web-nuxt/public/img/entities/ca-da-tron-nuoi-nuoc-ngot.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Ao nuôi cá da trơn nước ngọt thâm canh ứng dụng công nghệ sinh học tại Mỏ Cày, cung ứng nguồn nguyên liệu cá tra cá basa sạch cho xuất khẩu.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "ca-tra-tra-vinh",
        "image": "web-nuxt/public/img/entities/ca-tra-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Kéo lưới thu hoạch cá tra thương phẩm tại các vùng nuôi chuyên canh ven sông Cổ Chiên, cá đồng đều kích cỡ đạt chuẩn GlobalGAP xuất khẩu.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "xa-lach-xoong-thuan-an",
        "image": "web-nuxt/public/img/entities/xa-lach-xoong-thuan-an.webp",
        "author": "Thanh Đức",
        "source": "Báo Vĩnh Long",
        "caption": "Liếp cải xà lách xoong Thuận An xanh mướt trải dài bên rạch nước trong, thương hiệu OCOP 4 sao nổi tiếng với cọng giòn rụm và vị the cay đặc trưng.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "ca-chay-tra-on",
        "image": "web-nuxt/public/img/entities/ca-chay-tra-on.webp",
        "author": "Ngọc Trảng",
        "source": "Báo Vĩnh Long",
        "caption": "Cá cháy Tích Thiện thân dẹp vảy bạc lấp lánh, sản vật quý hiếm mùa nước lợ sông Hậu dùng nấu canh chua bần hoặc kho rim rục xương.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "bo-da-xanh-ba-tri",
        "image": "web-nuxt/public/img/entities/bo-da-xanh-ba-tri.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Đàn bò thịt Ba Tri vạm vỡ gặm cỏ trên đồng cỏ ven biển, giống bò thịt chất lượng cao có chỉ dẫn nhãn hiệu tập thể uy tín của vùng duyên hải.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "ca-tra",
        "image": "web-nuxt/public/img/entities/ca-tra.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Cá tra nuôi bè nước ngọt trên dòng sông Hàm Luông đoạn qua Chợ Lách, dòng nước chảy liên tục giúp thịt cá săn chắc và trắng tinh khiết.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "nhan-tieu-da-bo",
        "image": "web-nuxt/public/img/entities/nhan-tieu-da-bo.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Chùm nhãn tiêu da bò trĩu quả vỏ nâu sậm, cơm dày hạt nhỏ như hạt tiêu và vị ngọt thơm đậm đà truyền thống của miệt vườn cây trái.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "nhan-ido-an-binh",
        "image": "web-nuxt/public/img/entities/nhan-ido-an-binh.webp",
        "author": "Ngọc Trảng",
        "source": "Báo Vĩnh Long",
        "caption": "Thu hoạch nhãn Ido cơm vàng hạt tiêu trên cù lao An Bình, giống nhãn năng suất cao kháng bệnh chổi rồng đạt tiêu chuẩn xuất khẩu chính ngạch.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "cam-xoan-tra-on",
        "image": "web-nuxt/public/img/entities/cam-xoan-tra-on.webp",
        "author": "Ngọc Trảng",
        "source": "Báo Vĩnh Long",
        "caption": "Trái cam xoàn Trà Ôn vỏ mỏng láng bóng với đít xoáy đồng tiền đặc trưng, tép cam vàng óng ngọt đậm thanh tao thu hoạch theo quy trình VietGAP.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "ca-dieu-hong-nuoi-be-long-ho",
        "image": "web-nuxt/public/img/entities/ca-dieu-hong-nuoi-be-long-ho.webp",
        "author": "Thanh Đức",
        "source": "Báo Vĩnh Long",
        "caption": "Làng bè nuôi cá điêu hồng san sát ven sông Cổ Chiên đoạn Long Hồ, cá quẫy bọt trắng xóa đón thức ăn tạo nên khung cảnh trù phú tấp nập.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "ca-tra-thuong-pham-vinh-long",
        "image": "web-nuxt/public/img/entities/ca-tra-thuong-pham-vinh-long.webp",
        "author": "Thanh Đức",
        "source": "Báo Vĩnh Long",
        "caption": "Cá tra thương phẩm chất lượng cao chuẩn bị xuất bán từ ao nuôi đạt chuẩn an toàn sinh học, phục vụ chuỗi cung ứng chế biến phi-lê xuất khẩu.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "cua-bien-ben-tre",
        "image": "web-nuxt/public/img/entities/cua-bien-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Cua biển nuôi quảng canh tự nhiên trong rừng ngập mặn Thạnh Phú, yếm chắc nịch và thịt ngọt đậm đà đạt chỉ dẫn địa lý quốc gia.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "tom-cang-xanh-ben-tre",
        "image": "web-nuxt/public/img/entities/tom-cang-xanh-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Tôm càng xanh toàn đực nuôi xen trong mương vườn dừa và ruộng lúa tại Thạnh Phú, tôm tươi sống càng xanh ngắt đạt chứng nhận OCOP.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "tom-the-chan-trang-ben-tre",
        "image": "web-nuxt/public/img/entities/tom-the-chan-trang-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Hệ thống ao lót bạt nuôi tôm thẻ chân trắng công nghệ cao ven biển Thạnh Phú, sản lượng thu hoạch lớn với tôm vỏ mỏng thịt giòn ngọt.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "ruou-phu-le",
        "image": "web-nuxt/public/img/entities/ruou-phu-le.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Chum sành ủ men thuốc Bắc 36 vị thảo mộc nấu rượu nếp Phú Lễ tại Ba Tri, danh tửu truyền thống nức tiếng với giọt rượu nồng êm dịu.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "banh-phong-son-doc",
        "image": "web-nuxt/public/img/entities/banh-phong-son-doc.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Bánh phồng nếp Sơn Đốc phơi trên liếp đan tại làng nghề Hưng Nhượng, nướng chín phồng to xốp thơm mùi nếp mới và nước cốt dừa béo bùi.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "chom-chom-con-tan-quy",
        "image": "web-nuxt/public/img/entities/chom-chom-con-tan-quy.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Vườn chôm chôm chín đỏ rực giữa cù lao Tân Quy bốn bề sông nước mênh mông, cùi trái giòn ngọt tróc hạt đặc sản mùa hè sông Hậu.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "quyt-duong-long-tri",
        "image": "web-nuxt/public/img/entities/quyt-duong-long-tri.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Trái quýt đường Long Trị chín vàng óng trên cành tại Càng Long, giống quýt cổ truyền đạt chứng nhận VietGAP với múi mọng ngọt thanh mát.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "dua-trai-tra-vinh",
        "image": "web-nuxt/public/img/entities/dua-trai-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Những buồng dừa hữu cơ trĩu quả thu hoạch từ vùng chuyên canh hơn hai mươi ngàn hecta, cung cấp nguyên liệu dừa tươi và dừa sáp giá trị cao.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "lua-gao-chat-luong-cao-tra-vinh",
        "image": "web-nuxt/public/img/entities/lua-gao-chat-luong-cao-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Cánh đồng mẫu lớn lúa chất lượng cao trĩu bông vàng rực mùa gặt, hạt gạo thon đều dẻo thơm phục vụ thị trường nội địa và xuất khẩu.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "tom-su-nuoc-lo-tra-vinh",
        "image": "web-nuxt/public/img/entities/tom-su-nuoc-lo-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Thu hoạch tôm sú tự nhiên dưới tán rừng ngập mặn ven biển, mô hình tôm-rừng sinh thái bền vững cho con tôm sạch thịt săn chắc ngọt lịm.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "so-huyet-tra-vinh",
        "image": "web-nuxt/public/img/entities/so-huyet-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Sò huyết tươi sống cào từ bãi bồi cửa biển Duyên Hải, con sò béo múp vỏ dày ruột đỏ au nhiều huyết giàu khoáng chất bồi bổ sức khỏe.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "nuoc-cot-dua-ben-tre",
        "image": "web-nuxt/public/img/entities/nuoc-cot-dua-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Nước cốt dừa đóng lon Delta Coco chế biến từ cơm dừa già tuyển chọn, sản phẩm OCOP đạt chuẩn quốc tế xuất khẩu đi hàng chục quốc gia.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "xoai-tu-quy",
        "image": "web-nuxt/public/img/entities/xoai-tu-quy.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Trái xoài tứ quý Thới Thuận to tròn nặng gần hai ký, thịt xoài dày giòn ngọt pha chút vị mặn khoáng chất tự nhiên của vùng đất giồng cát ven biển.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    }
]

assert len(batch_35_data) == 40

with open("outputs/batch_35_products_photos.json", "w", encoding="utf-8") as f:
    json.dump(batch_35_data, f, ensure_ascii=False, indent=2)
    f.write("\n")

print("Generated outputs/batch_35_products_photos.json with 40 entries!")
