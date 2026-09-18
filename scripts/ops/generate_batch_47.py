import json

batch_47_data = [
    {
        "entity_id": "xa-thanh-phong",
        "image": "web-nuxt/public/img/entities/xa-thanh-phong.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Khu di tích lịch sử Đầu Cầu Tiếp Nhận Vũ Khí Bắc Nam đường Hồ Chí Minh trên biển tại Xã Thạnh Phong.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "xa-phu-phung",
        "image": "web-nuxt/public/img/entities/xa-phu-phung.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Vườn sầu riêng Ri6 và măng cụt trĩu quả bên bờ sông Cổ Chiên tại Xã Phú Phụng.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "xa-phu-quoi",
        "image": "web-nuxt/public/img/entities/xa-phu-quoi.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Cụm trường đại học và khu công nghiệp Hòa Phú hiện đại dọc tuyến Quốc lộ 1 tại Xã Phú Quới.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "xa-phu-thuan",
        "image": "web-nuxt/public/img/entities/xa-phu-thuan.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Vùng nuôi thủy sản nước lợ và các bãi nuôi nghêu ven cửa biển sông Tiền tại Xã Phú Thuận.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "xa-phuoc-long",
        "image": "web-nuxt/public/img/entities/xa-phuoc-long.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Vườn dừa xiêm xanh trĩu quả và cơ sở chế biến kẹo dừa truyền thống tại Xã Phước Long.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "xa-phuoc-my-trung",
        "image": "web-nuxt/public/img/entities/xa-phuoc-my-trung.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Trung tâm dịch vụ nông nghiệp và làng nghề chế biến chỉ xơ dừa xuất khẩu tại Xã Phước Mỹ Trung.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "xa-quoi-an",
        "image": "web-nuxt/public/img/entities/xa-quoi-an.webp",
        "author": "Thanh Dũng",
        "source": "Báo Vĩnh Long",
        "caption": "Vườn sầu riêng chuyên canh năng suất cao ven hệ thống kênh thủy lợi nội đồng tại Xã Quới An.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "xa-quoi-dien",
        "image": "web-nuxt/public/img/entities/xa-quoi-dien.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Mô hình cánh đồng lúa tôm sinh thái và rặng dừa hữu cơ trĩu quả tại Xã Quới Điền.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "xa-quoi-thien",
        "image": "web-nuxt/public/img/entities/xa-quoi-thien.webp",
        "author": "Huỳnh Biển",
        "source": "Báo Vĩnh Long",
        "caption": "Cù lao sông xanh biếc với bến phà vận chuyển chôm chôm và sầu riêng xuất bán tại Xã Quới Thiện.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "xa-song-loc",
        "image": "web-nuxt/public/img/entities/xa-song-loc.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Cánh đồng lúa chất lượng cao và giồng cát trồng rau màu luân canh tại Xã Song Lộc.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "xa-song-phu",
        "image": "web-nuxt/public/img/entities/xa-song-phu.webp",
        "author": "Nguyễn Thắng",
        "source": "Báo Vĩnh Long",
        "caption": "Chợ đầu mối nông sản Ba Càng và các vườn cam sành hữu cơ trĩu cành tại Xã Song Phú.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "xa-tam-ngai",
        "image": "web-nuxt/public/img/entities/xa-tam-ngai.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Khu tưởng niệm Nữ anh hùng lực lượng vũ trang nhân dân Nguyễn Thị Út tại Xã Tam Ngãi.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "xa-tan-an",
        "image": "web-nuxt/public/img/entities/xa-tan-an.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Cánh đồng nếp sáp truyền thống và làng nghề đòn bánh tét nức tiếng tại Xã Tân An.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "xa-tan-hao",
        "image": "web-nuxt/public/img/entities/xa-tan-hao.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Làng nghề tiểu thủ công nghiệp đan lát bồ cào và vườn dừa chuyên canh tại Xã Tân Hào.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "xa-tan-long-hoi",
        "image": "web-nuxt/public/img/entities/xa-tan-long-hoi.webp",
        "author": "Thanh Dũng",
        "source": "Báo Vĩnh Long",
        "caption": "Vườn thanh long ruột đỏ thắp đèn trái vụ và các tuyến mương vườn trù phú tại Xã Tân Long Hội.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "xa-tan-luoc",
        "image": "web-nuxt/public/img/entities/xa-tan-luoc.webp",
        "author": "Huỳnh Biển",
        "source": "Báo Vĩnh Long",
        "caption": "Cánh đồng chuyên canh khoai lang tím Nhật Bản xuất khẩu trải rộng ngút tầm mắt tại Xã Tân Lược.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "xa-tan-phu",
        "image": "web-nuxt/public/img/entities/xa-tan-phu.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Vườn chôm chôm chín đỏ cành thu hút khách tham quan trải nghiệm hái quả tại Xã Tân Phú.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "xa-tan-thanh-binh",
        "image": "web-nuxt/public/img/entities/xa-tan-thanh-binh.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Vườn dừa xiêm dứa thơm ngát và nhà máy sơ chế cơm dừa xuất khẩu tại Xã Tân Thành Bình.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "xa-tan-xuan",
        "image": "web-nuxt/public/img/entities/xa-tan-xuan.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Lò chưng cất rượu nếp men truyền thống Phú Lễ đạt chuẩn chỉ dẫn địa lý tại Xã Tân Xuân.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "xa-tap-son",
        "image": "web-nuxt/public/img/entities/xa-tap-son.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Ngôi chùa Khmer cổ kính với mái ngói nhiều tầng rực rỡ bên hàng cây sao rợp bóng tại Xã Tập Sơn.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "xa-thanh-hai",
        "image": "web-nuxt/public/img/entities/xa-thanh-hai.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Bãi biển Cồn Bửng trải dài cát mịn cùng hàng phi lao chắn gió ngút ngàn tại Xã Thạnh Hải.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "xa-thanh-phu",
        "image": "web-nuxt/public/img/entities/xa-thanh-phu.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Khu chợ trung tâm sầm uất đầu mối trao đổi thủy hải sản ven biển tại Xã Thạnh Phú.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "xa-thanh-phuoc",
        "image": "web-nuxt/public/img/entities/xa-thanh-phuoc.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Cảng cá Bình Đại nhộn nhịp tàu thuyền đánh bắt xa bờ cập cảng bán cá tươi tại Xã Thạnh Phước.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "xa-thanh-thoi",
        "image": "web-nuxt/public/img/entities/xa-thanh-thoi.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Làng nghề đóng ghe xuồng gỗ truyền thống và rặng dừa rợp bóng đôi bờ kênh tại Xã Thành Thới.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "xa-thanh-tri",
        "image": "web-nuxt/public/img/entities/xa-thanh-tri.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Trang trại nuôi tôm công nghệ cao và rừng phòng hộ sinh thái bạt ngàn tại Xã Thạnh Trị.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "xa-thoi-thuan",
        "image": "web-nuxt/public/img/entities/xa-thoi-thuan.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Bãi nghêu sạch đạt chứng nhận MSC quốc tế bên bờ biển lộng gió tại Xã Thới Thuận.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "xa-tra-con",
        "image": "web-nuxt/public/img/entities/xa-tra-con.webp",
        "author": "Nguyễn Thắng",
        "source": "Báo Vĩnh Long",
        "caption": "Cánh đồng lúa trĩu bông đón mùa gặt mới trong không khí thanh bình tại Xã Trà Côn.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "xa-tra-cu",
        "image": "web-nuxt/public/img/entities/xa-tra-cu.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Không gian sinh hoạt lễ hội Chôl Chnăm Thmây tưng bừng quanh ngôi chùa cổ tại Xã Trà Cú.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "xa-trung-hiep",
        "image": "web-nuxt/public/img/entities/xa-trung-hiep.webp",
        "author": "Thanh Dũng",
        "source": "Báo Vĩnh Long",
        "caption": "Khu lưu niệm Thủ tướng Chính phủ Võ Văn Kiệt ngập tràn sắc hoa và cây xanh tại Xã Trung Hiệp.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "xa-trung-ngai",
        "image": "web-nuxt/public/img/entities/xa-trung-ngai.webp",
        "author": "Thanh Dũng",
        "source": "Báo Vĩnh Long",
        "caption": "Chùa Hạnh Phúc Tăng với kiến trúc Phật giáo Nam tông trầm mặc niên đại nghìn năm tại Xã Trung Ngãi.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "xa-vinh-kim",
        "image": "web-nuxt/public/img/entities/xa-vinh-kim.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Cánh đồng dưa hấu giồng cát Ba Động mọng ngọt đạt chuẩn sản phẩm OCOP tại Xã Vinh Kim.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "xa-vinh-thanh",
        "image": "web-nuxt/public/img/entities/xa-vinh-thanh.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Làng nghề cây giống và hoa kiểng Cái Mơn nức tiếng với hàng triệu chậu hoa Tết tại Xã Vĩnh Thành.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "xa-vinh-xuan",
        "image": "web-nuxt/public/img/entities/xa-vinh-xuan.webp",
        "author": "Huỳnh Biển",
        "source": "Báo Vĩnh Long",
        "caption": "Vườn cam sành trĩu quả thẳng tắp dọc theo bờ kênh Thầy Cai tại Xã Vĩnh Xuân.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    }
]

with open("outputs/batch_47_photos.json", "w", encoding="utf-8") as f:
    json.dump(batch_47_data, f, ensure_ascii=False, indent=2)

print(f"Successfully generated outputs/batch_47_photos.json with {len(batch_47_data)} entries.")
