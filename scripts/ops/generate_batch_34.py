import json

batch_34_data = [
    # 40 Products / OCOP & Local Terroir Specialties (Batch 34)
    {
        "entity_id": "keo-dua-thu-cong-ben-tre",
        "image": "web-nuxt/public/img/entities/keo-dua-thu-cong-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Những mẻ kẹo dừa nấu mạch nha thủ công được người thợ đổ khuôn, cắt viên và gói trong lớp giấy bánh tráng mỏng ăn được tại phường Bến Tre.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "mat-ong-hoa-dua-ben-tre",
        "image": "web-nuxt/public/img/entities/mat-ong-hoa-dua-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Mật ong hoa dừa đóng chai đạt chuẩn OCOP 4 sao với sắc vàng óng ánh tự nhiên, chắt lọc tinh túy từ các vườn dừa bạt ngàn xứ cù lao.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "dua-troc-le-phuong",
        "image": "web-nuxt/public/img/entities/dua-troc-le-phuong.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Sản phẩm dừa xiêm gọt trọc Lê Phương tại xã An Định đạt chứng nhận OCOP 3 sao, giữ trọn vị nước dừa tươi ngọt thanh phục vụ tiêu dùng và xuất khẩu.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "dong-trung-ha-thao-say-thang-hoa-drc",
        "image": "web-nuxt/public/img/entities/dong-trung-ha-thao-say-thang-hoa-drc.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Hộp đông trùng hạ thảo sấy thăng hoa DRC tại xã Hương Mỹ, sản phẩm nông nghiệp công nghệ cao đạt chứng nhận OCOP 3 sao với sợi nấm vàng cam đồng đều.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "keo-dau-phong-du-tan-loi",
        "image": "web-nuxt/public/img/entities/keo-dau-phong-du-tan-loi.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Kẹo đậu phộng Dư Tấn Lợi tại phường Tiểu Cần đạt OCOP 3 sao, giòn rụm với hạt đậu rang thơm bùi quyện lớp mạch nha và mè trắng thơm lừng.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "chieu-ca-hom",
        "image": "web-nuxt/public/img/entities/chieu-ca-hom.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Chiếu hoa Cà Hom dệt thủ công từ sợi lác nhuộm 5 sắc màu rực rỡ tại xã Hàm Giang, di sản văn hóa phi vật thể quốc gia lưu giữ tay nghề dệt chiếu Khmer.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "san-pham-ocop-thu-cong-my-nghe-tra-cu",
        "image": "web-nuxt/public/img/entities/san-pham-ocop-thu-cong-my-nghe-tra-cu.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Các sản phẩm thủ công mỹ nghệ từ tre và gỗ của đồng bào Khmer tại Trà Cú đạt chứng nhận OCOP, tinh xảo với mô hình nông cụ và mặt nạ dân gian.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "bot-nua-bot-khoai-mon-an-quang-huu",
        "image": "web-nuxt/public/img/entities/bot-nua-bot-khoai-mon-an-quang-huu.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Bột nưa nguyên chất An Quảng Hữu màu trắng tinh khiết, đặc sản truyền thống dùng nấu chè mát giải nhiệt giàu dinh dưỡng của bà con nông dân.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "banh-trang-ngot-le-hang",
        "image": "web-nuxt/public/img/entities/banh-trang-ngot-le-hang.webp",
        "author": "Ngọc Trảng",
        "source": "Báo Vĩnh Long",
        "caption": "Bánh tráng ngọt Lệ Hằng tại cù lao Mây phơi đều trên liếp tre, sản phẩm OCOP tiêu biểu với hương vị nước cốt dừa béo ngậy và vị ngọt thanh truyền thống.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "hop-tac-xa-cam-phuong-thuy",
        "image": "web-nuxt/public/img/entities/hop-tac-xa-cam-phuong-thuy.webp",
        "author": "Ngọc Trảng",
        "source": "Báo Vĩnh Long",
        "caption": "Trái cam sành vỏ mỏng mọng nước của HTX cam Phương Thúy tại phường Trà Ôn, canh tác theo tiêu chuẩn VietGAP đạt chứng nhận OCOP 3 sao chất lượng cao.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "tau-hu-ky-my-hoa-binh-minh",
        "image": "web-nuxt/public/img/entities/tau-hu-ky-my-hoa-binh-minh.webp",
        "author": "Thanh Đức",
        "source": "Báo Vĩnh Long",
        "caption": "Tàu hủ ky Mỹ Hòa phơi giòn từng lá vàng óng bên bờ sông, đặc sản truyền thống hơn một thế kỷ được công nhận di sản văn hóa phi vật thể quốc gia.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "tau-hu-ky-cai-von",
        "image": "web-nuxt/public/img/entities/tau-hu-ky-cai-von.webp",
        "author": "Thanh Đức",
        "source": "Báo Vĩnh Long",
        "caption": "Những xấp váng đậu tàu hủ ky Cái Vồn làm từ hạt đậu nành thuần khiết, thơm béo đặc trưng dùng chế biến các món chay thanh đạm và tiệc truyền thống.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "tra-kho-qua-rung-cai-von",
        "image": "web-nuxt/public/img/entities/tra-kho-qua-rung-cai-von.webp",
        "author": "Ngọc Trảng",
        "source": "Báo Vĩnh Long",
        "caption": "Trà khổ qua rừng Cái Vồn dạng túi lọc và xắt lát sấy khô, sản phẩm OCOP 4 sao tốt cho sức khỏe với vị đắng thanh hậu ngọt sâu lắng.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "tra-gung-mat-ong-dong-binh",
        "image": "web-nuxt/public/img/entities/tra-gung-mat-ong-dong-binh.webp",
        "author": "Thanh Đức",
        "source": "Báo Vĩnh Long",
        "caption": "Trà gừng mật ong Đông Bình đạt chuẩn OCOP 4 sao, sự kết hợp hài hòa giữa vị cay ấm nồng của củ gừng sẻ và vị ngọt thanh dịu của mật ong rừng nguyên chất.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "tra-gung-mat-ong-nguyen-chat-gingo",
        "image": "web-nuxt/public/img/entities/tra-gung-mat-ong-nguyen-chat-gingo.webp",
        "author": "Thanh Đức",
        "source": "Báo Vĩnh Long",
        "caption": "Hộp trà gừng mật ong nguyên chất thương hiệu Gingo tại Đông Bình, quy trình chế biến khép kín hiện đại giữ trọn dược tính quý và hương thơm nồng ấm.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khoai-lang-say-binh-tan",
        "image": "web-nuxt/public/img/entities/khoai-lang-say-binh-tan.webp",
        "author": "Ngọc Trảng",
        "source": "Báo Vĩnh Long",
        "caption": "Sản phẩm khoai lang tím và vàng sấy giòn Bình Tân, tinh hoa nông sản từ vùng chuyên canh khoai lớn nhất vùng đạt chuẩn OCOP chất lượng cao.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "man-an-phuoc-ocop",
        "image": "web-nuxt/public/img/entities/man-an-phuoc-ocop.webp",
        "author": "Ngọc Trảng",
        "source": "Báo Vĩnh Long",
        "caption": "Mận An Phước quả đỏ au căng bóng mọng nước của HTX Cây ăn trái An Thới, sản phẩm OCOP 4 sao giòn ngọt đậm đà danh tiếng miệt vườn cù lao.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khoai-lang-say-dong-phat",
        "image": "web-nuxt/public/img/entities/khoai-lang-say-dong-phat.webp",
        "author": "Ngọc Trảng",
        "source": "Báo Vĩnh Long",
        "caption": "Gói khoai lang sấy Đông Phát Food đạt chứng nhận OCOP 4 sao, công nghệ sấy chân không hiện đại xuất khẩu sang nhiều thị trường quốc tế khó tính.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khoai-lang-say-gion-mien-tay",
        "image": "web-nuxt/public/img/entities/khoai-lang-say-gion-mien-tay.webp",
        "author": "Ngọc Trảng",
        "source": "Báo Vĩnh Long",
        "caption": "Khoai lang sấy giòn Miền Tây màu tím tự nhiên không chất bảo quản, bao bì chỉn chu đạt chứng nhận OCOP phục vụ khách du lịch làm quà biếu.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "dua-hau-tan-hung-ocop",
        "image": "web-nuxt/public/img/entities/dua-hau-tan-hung-ocop.webp",
        "author": "Thanh Đức",
        "source": "Báo Vĩnh Long",
        "caption": "Những quả dưa hấu Tân Hưng vỏ mỏng ruột đỏ au ngọt lịm của HTX Tân Hưng, sản phẩm nông sản OCOP được người tiêu dùng ưa chuộng quanh năm.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "vu-sua-hoang-kim-thanh-binh-ocop",
        "image": "web-nuxt/public/img/entities/vu-sua-hoang-kim-thanh-binh-ocop.webp",
        "author": "Ngọc Trảng",
        "source": "Báo Vĩnh Long",
        "caption": "Vú sữa hoàng kim Thanh Bình vỏ vàng ươm mướt mắt, thịt dày mềm ngọt và hạt lép đạt chuẩn OCOP từ nhà vườn chuyên canh giống trái cây độc đáo.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khoai-lang-tan-thanh-ocop",
        "image": "web-nuxt/public/img/entities/khoai-lang-tan-thanh-ocop.webp",
        "author": "Thanh Đức",
        "source": "Báo Vĩnh Long",
        "caption": "Củ khoai lang tươi vỏ tím ruột vàng dẻo bùi của HTX Tân Thành, nông sản OCOP chủ lực của đất phù sa màu mỡ thu hoạch chính vụ.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "rau-cau-vinh-quang",
        "image": "web-nuxt/public/img/entities/rau-cau-vinh-quang.webp",
        "author": "Ngọc Trảng",
        "source": "Báo Vĩnh Long",
        "caption": "Khay rau câu tráng miệng Vinh Quang nhiều màu sắc tự nhiên từ lá dứa và nước cốt dừa, đặc sản OCOP 3 sao quen thuộc tại trung tâm thành phố.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "banh-phong-khoai-lang-nhat-ngoc",
        "image": "web-nuxt/public/img/entities/banh-phong-khoai-lang-nhat-ngoc.webp",
        "author": "Ngọc Trảng",
        "source": "Báo Vĩnh Long",
        "caption": "Bánh phồng khoai lang Nhật Ngọc nướng phồng xốp giòn tan, sự kết hợp độc đáo giữa khoai lang tươi và bột nếp đạt chứng nhận OCOP 4 sao.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "cha-lua-pate-thit-banh-pho-banh-canh-gao-phuong-truong-an",
        "image": "web-nuxt/public/img/entities/cha-lua-pate-thit-banh-pho-banh-canh-gao-phuong-truong-an.webp",
        "author": "Thanh Đức",
        "source": "Báo Vĩnh Long",
        "caption": "Bộ sản phẩm thực phẩm chế biến chả lụa và bánh phở gạo tươi tại phường Trường An, đạt chứng nhận OCOP 4 sao với quy chuẩn an toàn vệ sinh nghiêm ngặt.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "dua-ngo-luc-binh-thanh-quoi",
        "image": "web-nuxt/public/img/entities/dua-ngo-luc-binh-thanh-quoi.webp",
        "author": "Ngọc Trảng",
        "source": "Báo Vĩnh Long",
        "caption": "Hũ dưa ngó lục bình Thạnh Quới muối chua giòn rụm, món đặc sản dân dã đậm chất bản địa sông nước đạt chuẩn OCOP 3 sao.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "rau-thom-ocop-hop-tac-xa-phuoc-hau",
        "image": "web-nuxt/public/img/entities/rau-thom-ocop-hop-tac-xa-phuoc-hau.webp",
        "author": "Thanh Đức",
        "source": "Báo Vĩnh Long",
        "caption": "Vườn rau thơm và ngò gai xanh mướt của HTX rau an toàn Phước Hậu, sản phẩm rau gia vị OCOP thu hoạch tươi mới cung ứng cho siêu thị và chợ đầu mối.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "thanh-long-vang-thanh-duc-ocop-3-sao",
        "image": "web-nuxt/public/img/entities/thanh-long-vang-thanh-duc-ocop-3-sao.webp",
        "author": "Ngọc Trảng",
        "source": "Báo Vĩnh Long",
        "caption": "Trái thanh long vàng vỏ vàng ruột trắng trong của cơ sở Thiên An 3 tại xã Thanh Đức, sản phẩm OCOP 3 sao thơm dịu và giàu khoáng chất.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "mat-ong-hai-nuong",
        "image": "web-nuxt/public/img/entities/mat-ong-hai-nuong.webp",
        "author": "Ngọc Trảng",
        "source": "Báo Vĩnh Long",
        "caption": "Chai mật ong hoa nhãn nguyên chất cơ sở Hai Nương tại xã cù lao Hòa Ninh, sản phẩm sinh thái đặc trưng phục vụ du khách trải nghiệm làng du lịch.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "gach-nung-do-va-gom-khong-men-mang-thit",
        "image": "web-nuxt/public/img/entities/gach-nung-do-va-gom-khong-men-mang-thit.webp",
        "author": "Thanh Đức",
        "source": "Báo Vĩnh Long",
        "caption": "Sản phẩm gạch gốm đỏ không men Mang Thít với lớp men phấn trắng tự nhiên độc bản, tinh hoa làng nghề gốm trăm năm bên dòng kênh Thầy Cai.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "gach-do-truyen-thong-mang-thit",
        "image": "web-nuxt/public/img/entities/gach-do-truyen-thong-mang-thit.webp",
        "author": "Thanh Đức",
        "source": "Báo Vĩnh Long",
        "caption": "Từng viên gạch đỏ son đanh chắc được dỡ ra sau mẻ nung trấu truyền thống tại các lò gạch Mang Thít, cung ứng cho các công trình kiến trúc bền vững.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "gao-huu-co-tan-dat",
        "image": "web-nuxt/public/img/entities/gao-huu-co-tan-dat.webp",
        "author": "Ngọc Trảng",
        "source": "Báo Vĩnh Long",
        "caption": "Túi gạo hữu cơ ST25 Tấn Đạt tại xã Trung Ngãi đạt chuẩn OCOP, hạt thon dài trắng đều khi nấu tỏa hương dứa thơm nồng cơm dẻo ngọt.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "mut-dua-la-dua-duc-dat",
        "image": "web-nuxt/public/img/entities/mut-dua-la-dua-duc-dat.webp",
        "author": "Ngọc Trảng",
        "source": "Báo Vĩnh Long",
        "caption": "Hộp mứt dừa non lá dứa Đức Đạt màu xanh cốm tự nhiên đạt OCOP 4 sao, từng sợi dừa dẻo mềm béo ngậy mùi nước cốt dừa và thoảng hương lá dứa thơm.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "lap-xuong-hiep-ky",
        "image": "web-nuxt/public/img/entities/lap-xuong-hiep-ky.webp",
        "author": "Ngọc Trảng",
        "source": "Báo Vĩnh Long",
        "caption": "Lạp xưởng tươi Hiệp Ký đạt chứng nhận OCOP, ướp rượu mai quế lộ gia truyền thơm phức và thịt nạc heo tươi ngon chắc thịt.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "mut-xoai-cat-num-foodo-ocop",
        "image": "web-nuxt/public/img/entities/mut-xoai-cat-num-foodo-ocop.webp",
        "author": "Ngọc Trảng",
        "source": "Báo Vĩnh Long",
        "caption": "Mứt xoài sấy dẻo Foodo làm từ xoài cát núm bản địa, sản phẩm khởi nghiệp OCOP đặc sắc giữ trọn vị chua ngọt tự nhiên và màu vàng ươm hấp dẫn.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "bot-rau-ma-hoang-gia",
        "image": "web-nuxt/public/img/entities/bot-rau-ma-hoang-gia.webp",
        "author": "Ngọc Trảng",
        "source": "Báo Vĩnh Long",
        "caption": "Hộp bột rau má sấy lạnh Hoàng Gia tại xã Hiếu Nghĩa đạt chuẩn OCOP, nguyên liệu canh tác hữu cơ giữ nguyên chất xơ và vitamin tươi mát.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "san-pham-ocop-chao-thuan-duyen",
        "image": "web-nuxt/public/img/entities/san-pham-ocop-chao-thuan-duyen.webp",
        "author": "Thanh Đức",
        "source": "Báo Vĩnh Long",
        "caption": "Các hũ chao gia vị Thuận Duyên tại xã Tân Phú đạt OCOP 4 sao, lên men tự nhiên với miếng chao béo ngậy đậm đà hương vị ẩm thực miệt vườn.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "bun-tuoi-sau-thanh",
        "image": "web-nuxt/public/img/entities/bun-tuoi-sau-thanh.webp",
        "author": "Thanh Đức",
        "source": "Báo Vĩnh Long",
        "caption": "Bún tươi và bánh hủ tiếu sạch Sáu Thạnh đạt chuẩn OCOP 4 sao, làm từ gạo nàng thơm nguyên chất sợi trắng trong dai ngon không hàn the.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "san-pham-chao-dua-chao-chanh-day-thuan-duyen-ocop-4-sao",
        "image": "web-nuxt/public/img/entities/san-pham-chao-dua-chao-chanh-day-thuan-duyen-ocop-4-sao.webp",
        "author": "Thanh Đức",
        "source": "Báo Vĩnh Long",
        "caption": "Bộ đôi sản phẩm chao dừa và chao chanh dây Thuận Duyên OCOP 4 sao sáng tạo độc đáo, mang đến trải nghiệm hương vị chua ngọt béo ngậy mới lạ.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "cam-sanh-tra-on",
        "image": "web-nuxt/public/img/entities/cam-sanh-tra-on.webp",
        "author": "Ngọc Trảng",
        "source": "Báo Vĩnh Long",
        "caption": "Những trái cam sành Trà Ôn trĩu cành ven dòng sông Hậu, tép cam vàng tươi mọng nước ngọt thanh là sản phẩm nông sản OCOP nức tiếng gần xa.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    }
]

assert len(batch_34_data) == 40

with open("outputs/batch_34_products_photos.json", "w", encoding="utf-8") as f:
    json.dump(batch_34_data, f, ensure_ascii=False, indent=2)
    f.write("\n")

print("Generated outputs/batch_34_products_photos.json with 40 entries!")
