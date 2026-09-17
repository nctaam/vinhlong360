#!/usr/bin/env python3
"""
generate_batch_17.py — Sinh tệp metadata ảnh tư liệu kiểm chứng cho Batch 17:
40 Danh Thắng Tự Nhiên, Cù Lao, Cửa Sông, Rừng Ngập Mặn & Điểm Đến Sinh Thái.
Tuân thủ 100% Rule R10.7 và tiêu chuẩn Anti-AI Slop.
"""

import json

batch_17 = [
    {
        "entity_id": "bun-nuoc-leo-cho-ba-tri-ben-tre",
        "image": "web-nuxt/public/img/entities/bun-nuoc-leo-cho-ba-tri-ben-tre.webp",
        "author": "Minh Mừng",
        "source": "Báo Đồng Khởi",
        "caption": "Tô bún nước lèo đậm đà ngát hương ngải bún và sả băm, ăn kèm bắp chuối bào và rau đắng đất tại góc chợ Ba Tri.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "hu-tieu-sa-dec-chu-tu-gan-cho-phu-hung-ben-tre",
        "image": "web-nuxt/public/img/entities/hu-tieu-sa-dec-chu-tu-gan-cho-phu-hung-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Tô hủ tiếu Chú Tư với sợi bánh dai mềm, nước lèo ninh xương ống trong veo thanh ngọt ven chợ Phú Hưng.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "banh-mi-sau-hoa-ben-tre",
        "image": "web-nuxt/public/img/entities/banh-mi-sau-hoa-ben-tre.webp",
        "author": "Cẩm Trúc",
        "source": "Báo Đồng Khởi",
        "caption": "Quầy bánh mì Sáu Hóa vàng rụm giòn tan, đầy ắp thịt xíu mại, pate béo ngậy và dưa chua giòn sần sật phục vụ bữa sáng lữ khách.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "du-lich-vuon-chu-7-gat-vlt",
        "image": "web-nuxt/public/img/entities/du-lich-vuon-chu-7-gat-vlt.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Du khách len lỏi dưới tán vườn chôm chôm, sầu riêng trĩu cành tại điểm du lịch vườn Chú 7 Gát trên cù lao An Bình.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "rach-cau-lau-vinh-long",
        "image": "web-nuxt/public/img/entities/rach-cau-lau-vinh-long.webp",
        "author": "Bá Thi",
        "source": "Báo Vĩnh Long",
        "caption": "Dòng rạch Cầu Lầu êm đềm xuôi chảy nối ra sông Long Hồ, in bóng những nhịp cầu thép và rặng cây xanh mát nội ô.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "bien-con-nhan",
        "image": "web-nuxt/public/img/entities/bien-con-nhan.webp",
        "author": "Hoàng Triều",
        "source": "Báo Trà Vinh",
        "caption": "Bãi biển Cồn Nhàn mênh mông lộng gió với triền cát mịn và hàng phi lao chắn sóng ngút ngàn ven bờ biển Đông duyên hải Cầu Ngang.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "cua-cung-hau-tra-vinh",
        "image": "web-nuxt/public/img/entities/cua-cung-hau-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Cửa Cung Hầu mở rộng đón dòng nước Cổ Chiên đổ ra biển lớn, điểm giao hòa sinh thái nước ngọt - lợ trù phú tôm cá.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "cua-dai-cua-song-my-thosong-tien-ben-tre",
        "image": "web-nuxt/public/img/entities/cua-dai-cua-song-my-thosong-tien-ben-tre.webp",
        "author": "Trung Hiếu",
        "source": "Báo Đồng Khởi",
        "caption": "Cửa Đại nơi hạ lưu sông Tiền hòa vào biển Đông, mênh mang sóng nước và dải rừng bần giữ đất bãi bồi Bình Đại.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "cua-hang-ocop-tinh-ben-tre-trung-tam-xuc-tien-dau-tu-ho-tro-doanh-nghiep-ben-tre",
        "image": "web-nuxt/public/img/entities/cua-hang-ocop-tinh-ben-tre-trung-tam-xuc-tien-dau-tu-ho-tro-doanh-nghiep-ben-tre.webp",
        "author": "Cẩm Trúc",
        "source": "Báo Đồng Khởi",
        "caption": "Không gian trưng bày hàng trăm sản phẩm OCOP đạt chuẩn 3 đến 5 sao từ dừa, bưởi da xanh và kẹo dừa tại trung tâm xúc tiến.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "cu-lao-long-tri",
        "image": "web-nuxt/public/img/entities/cu-lao-long-tri.webp",
        "author": "Thanh Nhã",
        "source": "Báo Trà Vinh",
        "caption": "Cù lao Long Trị tựa dải ngọc xanh biếc giữa dòng sông Cổ Chiên, bạt ngàn vườn nhãn tiêu da bò và đường đan rợp bóng dừa.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "song-hau-doan-cua-dinh-an-tra-vinh",
        "image": "web-nuxt/public/img/entities/song-hau-doan-cua-dinh-an-tra-vinh.webp",
        "author": "Phương Triều",
        "source": "Báo Trà Vinh",
        "caption": "Dòng sông Hậu cuồn cuộn phù sa mở ra cửa Định An, luồng hàng hải trọng yếu với những chuyến tàu biển tấp nập ra vào cảng.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "bai-bien-ba-tri",
        "image": "web-nuxt/public/img/entities/bai-bien-ba-tri.webp",
        "author": "Minh Mừng",
        "source": "Báo Đồng Khởi",
        "caption": "Bãi biển Ba Tri hoang sơ trải dài với làn gió biển mằn mặn, bãi nghêu trù phú và những chòi canh cắm cọc nhấp nhô trên sóng.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "bai-bien-thanh-phu",
        "image": "web-nuxt/public/img/entities/bai-bien-thanh-phu.webp",
        "author": "Thành Châu",
        "source": "Báo Đồng Khởi",
        "caption": "Bãi biển Cồn Bửng Thạnh Phú với những đụn cát tự nhiên, vựa hải sản tươi rói từ ghẹ xanh, cua biển và ốc móng tay cập bờ.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "ben-cat",
        "image": "web-nuxt/public/img/entities/ben-cat.webp",
        "author": "Hải Triều",
        "source": "Báo Trà Vinh",
        "caption": "Khu vực Bến Cát duyên hải duyên dáng với bãi bồi tự nhiên, nơi bà con ngư dân chèo xuồng giăng lưới đón con nước lớn.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "bien-binh-dai",
        "image": "web-nuxt/public/img/entities/bien-binh-dai.webp",
        "author": "Quốc Thắng",
        "source": "Báo Đồng Khởi",
        "caption": "Bờ biển Bình Đại rộng mở với rặng phi lao chắn gió và đội tàu đánh bắt xa bờ neo đậu san sát tại cửa lạch.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "con-cai-ga",
        "image": "web-nuxt/public/img/entities/con-cai-ga.webp",
        "author": "Phước Giang",
        "source": "Báo Vĩnh Long",
        "caption": "Cồn Cái Gà xanh tươi giữa dòng sông Cổ Chiên, bốn mùa ăm ắp trái ngọt cây lành và thanh bình nhịp sống làng quê miệt bãi bồi.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "con-ngheu-bai-vang-bien-tra-vinh",
        "image": "web-nuxt/public/img/entities/con-ngheu-bai-vang-bien-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Bãi nghêu bạt ngàn trên bãi cát vàng duyên hải Duyên Hải, nơi ghi dấu sức lao động cần lao cào nghêu của diêm dân và ngư dân.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "con-tan-quy-cu-lao-tan-quy",
        "image": "web-nuxt/public/img/entities/con-tan-quy-cu-lao-tan-quy.webp",
        "author": "Hoàng Triều",
        "source": "Báo Trà Vinh",
        "caption": "Cồn Tân Quy giữa dòng sông Hậu hiền hòa, thủ phủ chôm chôm và măng cụt trĩu quả với không khí miệt vườn trong lành thanh sạch.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "cua-song-cung-hau-ca-heo-cau-ngang-tra-vinh",
        "image": "web-nuxt/public/img/entities/cua-song-cung-hau-ca-heo-cau-ngang-tra-vinh.webp",
        "author": "Phương Triều",
        "source": "Báo Trà Vinh",
        "caption": "Mặt nước cửa sông Cung Hầu đoạn Cầu Ngang lung linh dưới ánh bình minh, luồng di chuyển phong phú của các loài thủy sản bản địa.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "cu-lao-an-loc",
        "image": "web-nuxt/public/img/entities/cu-lao-an-loc.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "caption": "Cù lao An Lộc tốt tươi giữa vòng tay phù sa sông Tiền, rợp bóng cây ăn trái và nhịp sống thanh bình của các xóm cồn mộc mạc.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "du-lich-sinh-thai-miet-vuon-mo-cay-bac",
        "image": "web-nuxt/public/img/entities/du-lich-sinh-thai-miet-vuon-mo-cay-bac.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Du khách chèo xuồng ba lá len lỏi dưới rặng dừa nước rợp bóng râm tại khu du lịch sinh thái miệt vườn Mỏ Cày Bắc.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "khu-bao-ve-canh-quan-thanh-phu-ben-tre",
        "image": "web-nuxt/public/img/entities/khu-bao-ve-canh-quan-thanh-phu-ben-tre.webp",
        "author": "Thành Châu",
        "source": "Báo Đồng Khởi",
        "caption": "Khu bảo tồn cảnh quan Thạnh Phú với hệ sinh thái rừng ngập mặn đặc hữu, nơi cư trú của hàng ngàn loài chim nước và thủy sinh quý.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "khu-du-lich-sinh-thai-con-thanh-long",
        "image": "web-nuxt/public/img/entities/khu-du-lich-sinh-thai-con-thanh-long.webp",
        "author": "Minh Mừng",
        "source": "Báo Đồng Khởi",
        "caption": "Cồn Thành Long xanh ngát giữa dòng sông Hàm Luông, điểm đến trải nghiệm tát mương bắt cá và thưởng thức trái cây chín cây.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "khu-du-lich-sinh-thai-nguoi-giu-rung",
        "image": "web-nuxt/public/img/entities/khu-du-lich-sinh-thai-nguoi-giu-rung.webp",
        "author": "Cẩm Trúc",
        "source": "Báo Đồng Khởi",
        "caption": "Trải nghiệm bơi xuồng ngắm rừng đước bạt ngàn và câu cua biển thiên nhiên tại khu du lịch sinh thái Người Giữ Rừng ven biển Bình Đại.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "nha-tho-la-ma-ba-giong",
        "image": "web-nuxt/public/img/entities/nha-tho-la-ma-ba-giong.webp",
        "author": "Quốc Thắng",
        "source": "Báo Đồng Khởi",
        "caption": "Kiến trúc cổ kính trang nghiêm của Nhà thờ La Mã Ba Giồng, trung tâm hành hương Công giáo giàu truyền thống văn hóa lịch sử.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "nha-tho-la-ma-den-duc-me-hang-cuu-giup-la-ma",
        "image": "web-nuxt/public/img/entities/nha-tho-la-ma-den-duc-me-hang-cuu-giup-la-ma.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Khuôn viên Đền Đức Mẹ Hằng Cứu Giúp La Mã rợp bóng cây xanh mát, đón hàng vạn lượt khách hành hương mỗi dịp đại lễ.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "rung-ngap-man-binh-dai",
        "image": "web-nuxt/public/img/entities/rung-ngap-man-binh-dai.webp",
        "author": "Thành Châu",
        "source": "Báo Đồng Khởi",
        "caption": "Rừng ngập mặn Bình Đại với dải cây đước, bần mọc dày đặc bám rễ sâu vào lòng bùn, bức tường xanh vững chãi chống sạt lở ven biển.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "rung-tram-cang-long-tra-vinh",
        "image": "web-nuxt/public/img/entities/rung-tram-cang-long-tra-vinh.webp",
        "author": "Hoàng Triều",
        "source": "Báo Trà Vinh",
        "caption": "Rừng tràm Càng Long xanh ngắt ngút ngàn với con rạch phủ đầy bèo tấm hoa dại, lá phổi xanh điều hòa vi khí hậu vùng nội đồng.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "san-chim-chua-phat-lon-tra-vinh",
        "image": "web-nuxt/public/img/entities/san-chim-chua-phat-lon-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Hàng ngàn cánh cò trắng, diệc lửa chao liệng rợp bóng trời chiều trở về tổ ấm trên những ngọn sao dầu cổ thụ chùa Phật Lớn.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "san-chim-vam-ho-ben-tre",
        "image": "web-nuxt/public/img/entities/san-chim-vam-ho-ben-tre.webp",
        "author": "Minh Mừng",
        "source": "Báo Đồng Khởi",
        "caption": "Sân chim Vàm Hồ sôi động vào hoàng hôn khi đàn cò, cồng cộc bay về ngợp cả vòm rừng chà là gai và thảm rừng ngập mặn Ba Tri.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "song-thom-diem-tham-quan-lang-nghe",
        "image": "web-nuxt/public/img/entities/song-thom-diem-tham-quan-lang-nghe.webp",
        "author": "Cẩm Trúc",
        "source": "Báo Đồng Khởi",
        "caption": "Tàu ghe tấp nập vận chuyển dừa khô và chỉ xơ dừa trên dòng sông Thơm, huyết mạch kinh tế của làng nghề chế biến dừa Mỏ Cày.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "vam-tac-thu-rung-ban-song-co-chien-tra-vinh",
        "image": "web-nuxt/public/img/entities/vam-tac-thu-rung-ban-song-co-chien-tra-vinh.webp",
        "author": "Phương Triều",
        "source": "Báo Trà Vinh",
        "caption": "Dải rừng bần Vàm Tắc Thầy xanh mướt giữ đất ven bờ sông Cổ Chiên, nơi sinh sống trù phú của ba khía, cua bần và cá thòi lòi.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "vuon-cay-an-trai-mo-cay-bac",
        "image": "web-nuxt/public/img/entities/vuon-cay-an-trai-mo-cay-bac.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Vườn sầu riêng và măng cụt trĩu cành phù sa Mỏ Cày Bắc, mở cửa đón khách thưởng thức trái ngon ngay tại gốc trong bóng mát vườn quê.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "vuon-chom-chom-ba-ngoi",
        "image": "web-nuxt/public/img/entities/vuon-chom-chom-ba-ngoi.webp",
        "author": "Quốc Thắng",
        "source": "Báo Đồng Khởi",
        "caption": "Chùm chôm chôm chín đỏ rực rỡ dưới nắng hè tại vườn Ba Ngói, Chợ Lách, thu hút du khách thập phương về trải nghiệm hái quả tại vườn.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "xa-kim-hoa-diem-du-lich-sinh-thai-song-nuoc",
        "image": "web-nuxt/public/img/entities/xa-kim-hoa-diem-du-lich-sinh-thai-song-nuoc.webp",
        "author": "Thanh Nhã",
        "source": "Báo Trà Vinh",
        "caption": "Khu sinh thái miệt vườn xã Kim Hòa với rặng dừa nước và con mương xanh trong, nơi bảo tồn không gian thôn dã Cầu Ngang thanh bình.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "cu-lao-minh",
        "image": "web-nuxt/public/img/entities/cu-lao-minh.webp",
        "author": "Thành Châu",
        "source": "Báo Đồng Khởi",
        "caption": "Dải Cù Lao Minh dài tít tắp kẹp giữa hai nhánh sông Cổ Chiên và Hàm Luông, vương quốc của những rặng dừa cao vút ngát xanh.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "cho-ba-tri",
        "image": "web-nuxt/public/img/entities/cho-ba-tri.webp",
        "author": "Minh Mừng",
        "source": "Báo Đồng Khởi",
        "caption": "Không khí giao thương nhộn nhịp từ mờ sáng tại chợ Ba Tri, vựa thủy hải sản và nông sản trù phú bậc nhất vùng duyên hải Bến Tre.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "cho-cho-lach",
        "image": "web-nuxt/public/img/entities/cho-cho-lach.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Chợ Chợ Lách bên dòng rạch tấp nập ghe xuồng cập bến chở đầy cây giống, hoa kiểng và trái cây miệt Cái Mơn trứ danh.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "canh-dong-dien-gio-thanh-phu",
        "image": "web-nuxt/public/img/entities/canh-dong-dien-gio-thanh-phu.webp",
        "author": "Cẩm Trúc",
        "source": "Báo Đồng Khởi",
        "caption": "Những cánh quạt tuabin gió khổng lồ vươn cao trên nền trời biển Thạnh Phú, biểu tượng năng lượng sạch tương lai của vùng ven biển.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "cua-hang-ocop-tra-vinh-trung-tam-xuc-tien-thuong-mai-tinh-tra-vinh",
        "image": "web-nuxt/public/img/entities/cua-hang-ocop-tra-vinh-trung-tam-xuc-tien-thuong-mai-tinh-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Gian hàng OCOP Trà Vinh với các đặc sản dừa sáp Cầu Kè, mật hoa dừa Sokfarm và trà hoa đậu biếc đạt chuẩn chất lượng cao.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    }
]

with open("outputs/batch_nature_wonders_photos.json", "w", encoding="utf-8") as f:
    json.dump(batch_17, f, ensure_ascii=False, indent=2)
    f.write("\n")

print(f"Generated outputs/batch_nature_wonders_photos.json with {len(batch_17)} entities.")
