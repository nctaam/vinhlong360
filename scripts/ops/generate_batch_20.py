import json

batch_20_data = [
    {
        "entity_id": "cho-hoa-tet",
        "image": "web-nuxt/public/img/entities/cho-hoa-tet.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Bến đỗ ghe thuyền tấp nập hoa mai, cúc vạn thọ và quất cảnh khoe sắc rực rỡ bên bờ kè sông Cổ Chiên mỗi dịp xuân về.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "le-hoi-ba-chua-xu",
        "image": "web-nuxt/public/img/entities/le-hoi-ba-chua-xu.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Nghi thức tắm Bà và dâng lễ trang trọng thu hút đông đảo người dân thập phương về chiêm bái bên dòng kênh Long Hồ.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "chao-cua-dong-ben-tre",
        "image": "web-nuxt/public/img/entities/chao-cua-dong-ben-tre.webp",
        "author": "Minh Mừng",
        "source": "Báo Đồng Khởi",
        "caption": "Nồi cháo cua đồng sôi lục bục với riêu cua béo ngậy, ăn kèm đĩa rau đắng đất và hột vịt lộn ngọt đậm đà phong vị miệt vườn.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "mam-song-khoai-lang",
        "image": "web-nuxt/public/img/entities/mam-song-khoai-lang.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Mẹt mắm sống cá sặc trộn tỏi ớt cay nồng ăn kèm đĩa khoai lang tím Bình Tân luộc chín bùi ngọt, món ăn dân dã thấm đẫm tình quê.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "ca-loc-nuong-trui",
        "image": "web-nuxt/public/img/entities/ca-loc-nuong-trui.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Con cá lóc đồng vùi trong đống rơm vàng rực lửa, thịt cá trắng ngần thơm lừng cuốn bánh tráng rau rừng chấm mắm me chua ngọt.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "nuoc-dua-tuoi-ben-tre",
        "image": "web-nuxt/public/img/entities/nuoc-dua-tuoi-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Trái dừa xiêm xanh vừa chặt tại vườn, nước dừa trong vắt ngọt lịm giải nhiệt ngày nắng gió trên cù lao sông Hàm Luông.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "banh-canh-ben-co-tra-vinh",
        "image": "web-nuxt/public/img/entities/banh-canh-ben-co-tra-vinh.webp",
        "author": "Hoàng Triều",
        "source": "Báo Trà Vinh",
        "caption": "Tô bánh canh Bến Có nức tiếng với sợi bánh trắng trong dai mềm, lòng heo giòn béo ngậy và nước lèo hầm xương trong veo ngọt thanh.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "banh-xeo-oc-gao-phu-da",
        "image": "web-nuxt/public/img/entities/banh-xeo-oc-gao-phu-da.webp",
        "author": "Cẩm Trúc",
        "source": "Báo Đồng Khởi",
        "caption": "Chiếc bánh xèo giòn rụm màu vàng nghệ với nhân ốc gạo cồn Phú Đa béo giòn sần sật, ăn cùng rau rừng chấm nước mắm tỏi ớt.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "co-diem---banh-canh-vit-bot-xat",
        "image": "web-nuxt/public/img/entities/co-diem---banh-canh-vit-bot-xat.webp",
        "author": "Minh Mừng",
        "source": "Báo Đồng Khởi",
        "caption": "Tô bánh canh vịt bột xắt Cô Diễm với nước dùng sền sệt béo ngọt bột gạo, thịt vịt cỏ mềm chấm nước mắm gừng cay nồng.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "oc-lac-hap-la-gung",
        "image": "web-nuxt/public/img/entities/oc-lac-hap-la-gung.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Thố ốc lác đồng luộc chín tới ngát hương lá gừng và sả cây, thịt ốc giòn ngọt chấm muối tiêu chanh ớt bên bàn tiệc miệt vườn.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "mam-chung-chuoi-dap",
        "image": "web-nuxt/public/img/entities/mam-chung-chuoi-dap.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Đĩa chuối xiêm đập nướng than hoa nóng hổi quết nước cốt dừa béo ngậy, kết hợp mắm chưng cá lóc đồng đậm đà hương vị sông Tiền.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "chuot-dua-hap-com",
        "image": "web-nuxt/public/img/entities/chuot-dua-hap-com.webp",
        "author": "Cẩm Trúc",
        "source": "Báo Đồng Khởi",
        "caption": "Món thịt chuột dừa hấp cơm trắng dẻo thơm ngậy, thịt ngọt mềm săn chắc nức danh ẩm thực dân dã miệt vườn dừa Mỏ Cày.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "oc-gao-con-phu-da-hap-sa",
        "image": "web-nuxt/public/img/entities/oc-gao-con-phu-da-hap-sa.webp",
        "author": "Minh Mừng",
        "source": "Báo Đồng Khởi",
        "caption": "Nồi ốc gạo cồn Phú Đa hấp sả bốc khói thơm lừng, thịt ốc trắng nõn béo ngậy nhể bằng gai bưởi chấm nước mắm sả ớt.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "loi-choi-sa-ot-tra-vinh",
        "image": "web-nuxt/public/img/entities/loi-choi-sa-ot-tra-vinh.webp",
        "author": "Huỳnh Phúc Hậu",
        "source": "Báo Trà Vinh",
        "caption": "Đĩa loi choi sả ớt chiên vàng óng ánh ngậy béo đặc trưng vùng bãi bồi duyên hải ven biển Ba Động, món nhậu khoái khẩu của ngư dân.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "hu-tieu-vinh-long",
        "image": "web-nuxt/public/img/entities/hu-tieu-vinh-long.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Tô hủ tiếu ngọt thanh ninh từ tôm khô và mực nướng cùng xương ống, sợi hủ tiếu dai mềm chan nước lèo nóng hổi phố cổ sông Tiền.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "oc-gao-phu-da",
        "image": "web-nuxt/public/img/entities/oc-gao-phu-da.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Rổ ốc gạo Phú Đa vừa cào từ đáy sông Cổ Chiên, vỏ ốc láng bóng ruột mập mạp đón chờ du khách ghé cồn thưởng thức.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "oc-gao-vinh-binh",
        "image": "web-nuxt/public/img/entities/oc-gao-vinh-binh.webp",
        "author": "Cẩm Trúc",
        "source": "Báo Đồng Khởi",
        "caption": "Ốc gạo Vĩnh Bình luộc sả lá chanh giòn ngọt thịt, đặc sản sông nước Chợ Lách mùa tết Đoan Ngọ mùng năm tháng năm âm lịch.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "mut-me-cai-von",
        "image": "web-nuxt/public/img/entities/mut-me-cai-von.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Từng trái me chín dốt lột vỏ sên đường cát óng ả dẻo quánh, vị chua thanh ngọt đậm đà đặc sản truyền thống thị xã Bình Minh.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "chuot-dong-nuong",
        "image": "web-nuxt/public/img/entities/chuot-dong-nuong.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Món chuột đồng nướng lu da giòn rụm vàng óng, ướp đẫm ngũ vị hương và mật ong thơm nức mũi sau mùa gặt lúa phù sa.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "nam-moi-xao",
        "image": "web-nuxt/public/img/entities/nam-moi-xao.webp",
        "author": "Minh Mừng",
        "source": "Báo Đồng Khởi",
        "caption": "Đĩa nấm mối đầu mùa xào mướp hương ngọt lịm giòn sần sật, lộc trời ban tặng cho những khu vườn dừa rậm rạp sau cơn mưa đầu mùa.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "ga-hap-ruou",
        "image": "web-nuxt/public/img/entities/ga-hap-ruou.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Con gà thả vườn hấp rượu nếp men bắc Phú Lễ da vàng óng mỡ màng, thịt gà ngọt đậm thoang thoảng men rượu nồng nàn xứ biển.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "che-buoi-vinh-long",
        "image": "web-nuxt/public/img/entities/che-buoi-vinh-long.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Ly chè bưởi thơm lừng với cùi bưởi Năm Roi giòn sần sật, đậu xanh bùi bùi quyện trong nước cốt dừa béo ngậy thanh mát.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "canh-chua-ca-linh-bong-so-dua",
        "image": "web-nuxt/public/img/entities/canh-chua-ca-linh-bong-so-dua.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Nồi canh chua cá linh non nấu bông so đũa đầu mùa nước nổi, vị chua dịu của me chín hòa cùng vị ngọt mềm béo ngậy của cá sông Tiền.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "tom-su-nuong-than-binh-dai",
        "image": "web-nuxt/public/img/entities/tom-su-nuong-than-binh-dai.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Những con tôm sú biển tươi rói nướng than hoa đỏ rực, vỏ tôm giòn rụm thịt ngọt lịm chấm muối ớt xanh vùng biển Bình Đại.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "hau-sua-thanh-phu",
        "image": "web-nuxt/public/img/entities/hau-sua-thanh-phu.webp",
        "author": "Minh Mừng",
        "source": "Báo Đồng Khởi",
        "caption": "Đĩa hàu sữa nướng mỡ hành đậu phộng béo ngậy trên bếp than hồng, đặc sản nuôi tự nhiên ven cửa biển Thạnh Hải.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "nem-nuong-vinh-long",
        "image": "web-nuxt/public/img/entities/nem-nuong-vinh-long.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Xâu nem nướng thịt heo quết nhuyễn nướng xèo xèo trên than hồng, cuốn bánh tráng nem Cù lao Mây cùng khế chua và chuối chát.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "ve-sau-chien-gion",
        "image": "web-nuxt/public/img/entities/ve-sau-chien-gion.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Đĩa ve sầu non chiên giòn rụm béo bùi tẩm nước mắm tỏi ớt, món đặc sản miệt vườn độc đáo mỗi độ hè về râm ran góc phố.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "loi-choi-sa-ot",
        "image": "web-nuxt/public/img/entities/loi-choi-sa-ot.webp",
        "author": "Hoàng Triều",
        "source": "Báo Trà Vinh",
        "caption": "Loi choi thân tròn như chiếc đũa xào sả ớt cay nồng đậm đà, món ngon độc đáo chỉ có ở vùng bãi bồi phù sa sông Cung Hầu.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "xoi-man-69---hung-dao-vuong",
        "image": "web-nuxt/public/img/entities/xoi-man-69---hung-dao-vuong.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Hộp xôi mặn dẻo thơm nếp mới với lạp xưởng, chà bông, pate béo ngậy và hành phi giòn tan tại góc phố Hưng Đạo Vương, Phường 1.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "yogurt-dua---ba-muoi-thang-tu",
        "image": "web-nuxt/public/img/entities/yogurt-dua---ba-muoi-thang-tu.webp",
        "author": "Minh Mừng",
        "source": "Báo Đồng Khởi",
        "caption": "Hũ yaourt dừa lên men tự nhiên mát lạnh béo ngậy nước cốt dừa tươi, điểm hẹn ẩm thực quen thuộc trên đường Ba Mươi Tháng Tư.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "dang-ga---cac-mon-ga-ta",
        "image": "web-nuxt/public/img/entities/dang-ga---cac-mon-ga-ta.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Mẹt gà ta thả vườn nướng muối ớt và gỏi gà bắp chuối đượm vị giấm dừa truyền thống phục vụ thực khách tại quán Đáng Gà.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "banh-flan-14",
        "image": "web-nuxt/public/img/entities/banh-flan-14.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Đĩa bánh flan mềm mịn thơm lừng mùi trứng sữa chan cà phê đen đá và đá bào mát rượi, góc ăn vặt gắn liền tuổi thơ đô thị.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "pho-91",
        "image": "web-nuxt/public/img/entities/pho-91.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Tô phở bò tái nạm bốc khói nghi ngút ngào ngạt hương quế hồi, nước dùng ninh xương ngọt lịm phục vụ khách ăn sáng tại Phở 91.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "banh-xeo-long-binh-2",
        "image": "web-nuxt/public/img/entities/banh-xeo-long-binh-2.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Chảo bánh xèo Long Bình vàng ươm tráng mỏng giòn rụm với nhân tôm sông, thịt ba rọi và củ hũ dừa trắng giòn thanh ngọt.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "banh-cuon-nong---tran-quoc-tuan",
        "image": "web-nuxt/public/img/entities/banh-cuon-nong---tran-quoc-tuan.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Đĩa bánh cuốn nóng tráng mỏng ươm nhân thịt mộc nhĩ, rắc đầy chả lụa và hành phi thơm lừng trên phố ẩm thực Trần Quốc Tuấn.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "com-ga-bong-viet",
        "image": "web-nuxt/public/img/entities/com-ga-bong-viet.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Dĩa cơm gà Bông Việt hạt cơm vàng ươm nấu nước luộc gà béo ngậy, đùi gà luộc da giòn thịt ngọt ăn kèm dưa chua giòn rụm.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "bun-bo-hue-19",
        "image": "web-nuxt/public/img/entities/bun-bo-hue-19.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Tô bún bò Huế đầy ắp bắp bò hoa và chả cua thơm phức mùi sả ớt cay nồng đậm đà tại quán bún bò 19 bên dòng rạch nội thị.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "3-mien-tra-vinh---bun-dau-mam-tom",
        "image": "web-nuxt/public/img/entities/3-mien-tra-vinh---bun-dau-mam-tom.webp",
        "author": "Hoàng Triều",
        "source": "Báo Trà Vinh",
        "caption": "Mẹt bún đậu mắm tôm đầy đặn với đậu hũ mơ chiên giòn, chả cốm vàng ươm và mắm tôm đánh sủi bọt quất chua cay tại quán 3 Miền.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "keo-dua-mo-cay-dish",
        "image": "web-nuxt/public/img/entities/keo-dua-mo-cay-dish.webp",
        "author": "Cẩm Trúc",
        "source": "Báo Đồng Khởi",
        "caption": "Đĩa kẹo dừa Mỏ Cày dẻo bùi béo ngậy hương nước cốt dừa và mạch nha, món tráng miệng gắn liền văn hóa tiếp khách miệt vườn.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "lo-com-cuu-long",
        "image": "web-nuxt/public/img/entities/lo-com-cuu-long.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Khay cốm gạo nổ bung xốp giòn tan ngào gừng và đường thốt nốt thơm lừng, món quà quê mộc mạc tại lò cốm Cửu Long ven sông Tiền.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    }
]

assert len(batch_20_data) == 40

with open("outputs/batch_culinary_events_photos.json", "w", encoding="utf-8") as f:
    json.dump(batch_20_data, f, ensure_ascii=False, indent=2)
    f.write("\n")

print("Generated outputs/batch_culinary_events_photos.json with 40 entries!")
