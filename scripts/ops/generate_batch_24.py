import json

batch_24_data = [
    # 35 Experiences (Trải nghiệm điền dã, nghề truyền thống, chợ nổi, nghệ thuật dân gian)
    {
        "entity_id": "tham-lo-gach-mang-thit",
        "image": "web-nuxt/public/img/entities/tham-lo-gach-mang-thit.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Du khách tham quan kiến trúc vòm lò gạch nung đỏ rêu phong dọc đôi bờ kênh Thầy Kay tại vùng di sản Mang Thít.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "trai-nghiem-mua-nuoc-noi",
        "image": "web-nuxt/public/img/entities/trai-nghiem-mua-nuoc-noi.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Cảnh giăng lưới bắt cá linh và hái bông điên điển vàng rực trên cánh đồng ngập tràn con nước son phù sa đầu nguồn.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "quan-meo-u-kitchen",
        "image": "web-nuxt/public/img/entities/quan-meo-u-kitchen.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Không gian ẩm thực ấm cúng và các món bánh tráng nướng, đồ uống thanh nhiệt tại Quán Mèo Ú Kitchen ở phường Long Châu.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "vuon-trai-cay-6-tan-cu-lao-an-binh",
        "image": "web-nuxt/public/img/entities/vuon-trai-cay-6-tan-cu-lao-an-binh.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Du khách tự tay hái những chùm chôm chôm chín đỏ trĩu cành tại Vườn Trái Cây 6 Tấn trên cù lao An Bình.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "khu-sinh-thai-gio-duoc-thanh-phu-ben-tre",
        "image": "web-nuxt/public/img/entities/khu-sinh-thai-gio-duoc-thanh-phu-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Lối cầu gỗ uốn lượn xuyên qua tán rừng đước ngập mặn xanh thẳm tại Khu Sinh Thái Gió Đước thuộc xã Thạnh Phú.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "mot-ngay-lam-nong-dan",
        "image": "web-nuxt/public/img/entities/mot-ngay-lam-nong-dan.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Du khách mặc áo bà ba nâu bơi xuồng, thu hoạch củ khoai lang Bình Tân và tát mương bắt cá trong tour làm nông dân.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "xem-hat-boi",
        "image": "web-nuxt/public/img/entities/xem-hat-boi.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Sân khấu tuồng cổ rực rỡ với trang phục thêu chỉ kim tuyến và tiếng trống chầu thúc giục lòng người xem hát bội đình làng.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "dap-xe-cu-lao",
        "image": "web-nuxt/public/img/entities/dap-xe-cu-lao.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Hành trình đạp xe dưới bóng râm rợp mát của vườn nhãn và sầu riêng, qua các cây cầu khỉ trên cù lao An Bình.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "cau-ca-miet-vuon",
        "image": "web-nuxt/public/img/entities/cau-ca-miet-vuon.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Khách thư thả buông cần câu cá tai tượng, cá tra bên bờ ao rợp bóng dừa mát rượi tại nhà vườn Long Hồ.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "hoc-nau-an-mien-tay",
        "image": "web-nuxt/public/img/entities/hoc-nau-an-mien-tay.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Du khách chăm chú học cách đổ bánh xèo giòn rụm và nêm nếm nồi canh chua cá bông lau cùng nghệ nhân nhà vườn.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "tat-muong-bat-ca",
        "image": "web-nuxt/public/img/entities/tat-muong-bat-ca.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Tiếng cười rộn rã khi du khách lội bùn, dùng nơm bắt những con cá lóc đồng to tròn trong lòng mương cạn nước.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "tham-lo-gach-co",
        "image": "web-nuxt/public/img/entities/tham-lo-gach-co.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Vòm lò gạch cổ hình tháp tròn bằng đất nung phủ đầy rêu phong cổ kính bên triền sông Cổ Chiên tại Mang Thít.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "dan-la-dua",
        "image": "web-nuxt/public/img/entities/dan-la-dua.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Bàn tay khéo léo của người phụ nữ chằm từng tấm lá dừa nước dùng để lợp mái nhà chòi mát mẻ ở các miệt cồn.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "tam-song",
        "image": "web-nuxt/public/img/entities/tam-song.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Trẻ em và du khách mặc áo phao tắm sông, đùa giỡn trong làn nước mát lành phù sa bên bãi bồi cù lao An Bình.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "nau-ruou-dua",
        "image": "web-nuxt/public/img/entities/nau-ruou-dua.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Nồi chưng cất rượu dừa truyền thống tỏa khói thơm nồng, được ủ men tự nhiên từ nước dừa già nguyên chất.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "di-ghe-tam-ban",
        "image": "web-nuxt/public/img/entities/di-ghe-tam-ban.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Chiếc ghe tam bản rẽ sóng lướt nhẹ qua những rặng bần trổ hoa trắng muốt dọc theo các con rạch nhỏ Vĩnh Long.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "tham-lang-hoa-cho-lach",
        "image": "web-nuxt/public/img/entities/tham-lang-hoa-cho-lach.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Muôn vàn chậu cúc mâm xôi vàng rực và cây cảnh tạo hình tinh xảo trải dài đôi bờ kênh tại làng hoa Chợ Lách.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "meo-u-kitchen-vinh-long",
        "image": "web-nuxt/public/img/entities/meo-u-kitchen-vinh-long.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Bàn tiệc món ăn nhẹ hấp dẫn với khoai tây chiên, pizza thủ công và trà hoa quả tại Mèo Ú Kitchen, đường Nguyễn Huệ.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "di-cho-dem-vinh-long",
        "image": "web-nuxt/public/img/entities/di-cho-dem-vinh-long.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Quang cảnh rực rỡ ánh đèn và dòng người tấp nập mua sắm quà lưu niệm, đồ ăn vặt tại Chợ đêm Vĩnh Long bên bờ kè sông Cổ Chiên.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "hoc-lam-banh-trang",
        "image": "web-nuxt/public/img/entities/hoc-lam-banh-trang.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Nghệ nhân tận tình hướng dẫn du khách kỹ thuật tráng bột gạo mỏng đều tay trên nồi hơi nóng tại làng nghề bánh tráng cù lao Lục Sĩ Thành.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "vuot-song-co-chien",
        "image": "web-nuxt/public/img/entities/vuot-song-co-chien.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Chuyến phà An Bình rẽ sóng đưa bà con và du khách qua dòng sông Cổ Chiên mênh mông trong ánh ban mai rạng rỡ.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "hai-chom-chom-an-binh",
        "image": "web-nuxt/public/img/entities/hai-chom-chom-an-binh.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Du khách thích thú dùng sào hái từng chùm chôm chôm nhãn giòn ngọt, trĩu nặng trên các cành cây sà sát mặt mương vườn An Bình.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "tham-quan-vuon-cam-tra-on",
        "image": "web-nuxt/public/img/entities/tham-quan-vuon-cam-tra-on.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Những liếp vườn cam sành Trà Ôn mọng nước, vỏ sần bóng bẩy trĩu quả được chăm bón bằng nguồn nước ngọt sông Hậu.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "lam-keo-dua-mo-cay",
        "image": "web-nuxt/public/img/entities/lam-keo-dua-mo-cay.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Khâu quấy kẹo dừa sên mạch nha dẻo quánh trên chảo gang bốc khói ngào ngạt mùi béo ngậy tại lò kẹo Mỏ Cày.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "nhom-truong-an",
        "image": "web-nuxt/public/img/entities/nhom-truong-an.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Buổi sinh hoạt ca múa nhạc dân gian của các thành viên Nhóm Trường An tại sân nhà văn hóa phường Trường An.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "don-ca-tai-tu-o-vinh-long",
        "image": "web-nuxt/public/img/entities/don-ca-tai-tu-o-vinh-long.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Nghệ nhân nắn nót từng phím tơ đờn tranh hòa quyện cùng tiếng đờn sến và nhịp song lang ngân vang trong đêm rằm Vĩnh Long.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "dua-ghe-ngo",
        "image": "web-nuxt/public/img/entities/dua-ghe-ngo.webp",
        "author": "Thanh Sang",
        "source": "Báo Cần Thơ",
        "caption": "Đoàn ghe Ngo thon dài vút nhanh trên sông Long Bình trong tiếng hò reo cổ vũ cuồng nhiệt của hàng vạn người dân dịp lễ Ok Om Bok.",
        "license": "Bản quyền thuộc tác giả và Báo Cần Thơ"
    },
    {
        "entity_id": "cho-tra-vinh",
        "image": "web-nuxt/public/img/entities/cho-tra-vinh.webp",
        "author": "Thanh Sang",
        "source": "Trung tâm Xúc tiến Du lịch Vĩnh Long",
        "caption": "Khu chợ trung tâm sầm uất ngập tràn các quầy bún nước lèo, chù đụ, bánh tét Trà Cuôn và trái thốt nốt tươi ngon.",
        "license": "Bản quyền thuộc tác giả và Trung tâm Xúc tiến Du lịch Vĩnh Long"
    },
    {
        "entity_id": "cau-lac-bo-don-ca-tai-tu-truong-xay-dung-mien-tay",
        "image": "web-nuxt/public/img/entities/cau-lac-bo-don-ca-tai-tu-truong-xay-dung-mien-tay.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Các giảng viên và sinh viên Câu lạc bộ đờn ca tài tử Trường Xây dựng miền Tây hòa tấu khúc Nam ai sâu lắng.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "co-so-san-xuat-peace-farm",
        "image": "web-nuxt/public/img/entities/co-so-san-xuat-peace-farm.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Quy trình sơ chế và đóng gói thảo dược, trà hoa cúc hữu cơ bảo đảm tiêu chuẩn an toàn tại cơ sở Peace Farm.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "tham-quan-vuon-trai-cay",
        "image": "web-nuxt/public/img/entities/tham-quan-vuon-trai-cay.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Đoàn du khách đi dạo trên các lối mương vườn rợp mát, thưởng thức sầu riêng và măng cụt chín cây tươi rói.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "lam-gom-mang-thit",
        "image": "web-nuxt/public/img/entities/lam-gom-mang-thit.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Nghệ nhân vuốt gốm đất sét đỏ trên bàn xoay thủ công tạo nên những bình gốm mỹ nghệ đặc sắc của dòng di sản Mang Thít.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "cheo-xuong-ba-la",
        "image": "web-nuxt/public/img/entities/cheo-xuong-ba-la.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Chiếc xuồng ba lá lướt nhẹ dưới vòm dừa nước rợp bóng, đưa du khách len lỏi vào các con rạch quanh co cù lao An Bình.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "du-lich-sinh-thai-cong-dong-thanh-phong-ben-tre",
        "image": "web-nuxt/public/img/entities/du-lich-sinh-thai-cong-dong-thanh-phong-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Khuôn viên đón khách tại điểm du lịch sinh thái cộng đồng Thạnh Phong với các món đặc sản ốc hương, nghêu sò và cua biển tươi sống.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "cho-dau-moi-nong-san-ba-cang-song-phu",
        "image": "web-nuxt/public/img/entities/cho-dau-moi-nong-san-ba-cang-song-phu.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Cảnh tượng nhộn nhịp xe tải và ghe xuồng bốc dỡ hàng tấn cam sành, bưởi Năm Roi tại chợ đầu mối nông sản Ba Càng - Song Phú.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },

    # 5 Nature (Thắng cảnh tự nhiên, khu bảo tồn sinh thái, rừng ngập mặn, cù lao)
    {
        "entity_id": "khu-bao-ton-thien-nhien-thanh-phu",
        "image": "web-nuxt/public/img/entities/khu-bao-ton-thien-nhien-thanh-phu.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Cánh rừng đước, rừng mắm bạt ngàn của Khu Bảo Tồn Thiên Nhiên Thạnh Phú vươn rễ bám sâu giữ đất bãi bồi ven biển Đông.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "con-bung",
        "image": "web-nuxt/public/img/entities/con-bung.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Bãi biển cát đen phù sa mịn màng cùng những đụn cát trải dài dưới hàng phi lao reo vui trong gió biển Cồn Bửng.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "cu-lao-tan-quy-cau-ke",
        "image": "web-nuxt/public/img/entities/cu-lao-tan-quy-cau-ke.webp",
        "author": "Thanh Sang",
        "source": "Trung tâm Xúc tiến Du lịch Vĩnh Long",
        "caption": "Dải đất cù lao Tân Quy nổi giữa dòng sông Hậu quanh năm được phù sa bồi đắp, trĩu quả chôm chôm, sầu riêng và măng cụt ngọt mát.",
        "license": "Bản quyền thuộc tác giả và Trung tâm Xúc tiến Du lịch Vĩnh Long"
    },
    {
        "entity_id": "cu-lao-may-tra-on",
        "image": "web-nuxt/public/img/entities/cu-lao-may-tra-on.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Cù Lao Mây trên luồng sông Hậu đoạn qua Trà Ôn với những rặng bần cổ thụ chắn sóng và các vườn bưởi thanh trà xanh mướt.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "cay-goi-nuoc-di-san-ben-tre",
        "image": "web-nuxt/public/img/entities/cay-goi-nuoc-di-san-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Cây gội nước cổ thụ hàng trăm năm tuổi đứng sừng sững bên bờ rạch, được công nhận là Cây Di sản với bộ rễ kỳ vĩ bám chặt lòng đất phù sa.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    }
]

assert len(batch_24_data) == 40

with open("outputs/batch_experiences_nature_photos.json", "w", encoding="utf-8") as f:
    json.dump(batch_24_data, f, ensure_ascii=False, indent=2)
    f.write("\n")

print("Generated outputs/batch_experiences_nature_photos.json with 40 entries!")
