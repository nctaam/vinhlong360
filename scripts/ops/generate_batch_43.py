import json

batch_43_data = [
    {
        "entity_id": "ben-pha-ham-luong-ben-tre",
        "image": "web-nuxt/public/img/entities/ben-pha-ham-luong-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Bến phà Hàm Luông vượt qua dòng sông rộng lớn đưa đón hành khách qua lại giữa đôi bờ thành phố Bến Tre và cù lao Mỏ Cày.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "ben-pha-tan-phu-chau-thanh-ben-tre",
        "image": "web-nuxt/public/img/entities/ben-pha-tan-phu-chau-thanh-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Chiếc phà sắt chở khách qua sông Ba Lai nối liền vùng đất Tân Phú sang vương quốc hoa kiểng Chợ Lách.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "ben-pha-tran-phu-can-tho-vinh-long-vinh-long",
        "image": "web-nuxt/public/img/entities/ben-pha-tran-phu-can-tho-vinh-long-vinh-long.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Bến đò khách dân sinh Trần Phú vận chuyển người dân vượt sông Hậu kết nối thị xã Bình Minh với bến Ninh Kiều.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "ben-tau-du-lich-tp-ben-tre-ben-tre",
        "image": "web-nuxt/public/img/entities/ben-tau-du-lich-tp-ben-tre-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Thuyền du lịch cập bến đón khách tham quan các cồn bãi và rạch dừa nước tại Bến tàu du lịch đường Hùng Vương.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "ben-xe-ba-tri-ben-tre",
        "image": "web-nuxt/public/img/entities/ben-xe-ba-tri-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Khu vực sân đỗ xe khách và nhà chờ khang trang phục vụ các tuyến xe liên tỉnh tại Bến xe Ba Tri ven Tỉnh lộ 885.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "ben-xe-ben-tre-trung-tam-ben-tre",
        "image": "web-nuxt/public/img/entities/ben-xe-ben-tre-trung-tam-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Hàng dài xe khách chất lượng cao xuất bến tỏa đi các tỉnh thành tại Bến xe trung tâm trên đường Đoàn Hoàng Minh.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "ben-xe-cau-ke-tra-vinh",
        "image": "web-nuxt/public/img/entities/ben-xe-cau-ke-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Phương tiện vận tải hành khách đón trả khách đi các xã miệt vườn dừa sáp tại Bến xe Cầu Kè ven Tỉnh lộ 911.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "ben-xe-cau-ngang-tra-vinh",
        "image": "web-nuxt/public/img/entities/ben-xe-cau-ngang-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Sân đón trả khách của tuyến xe buýt số 04 và các xe đò liên xã tại Bến xe Cầu Ngang trên trục đường 3 Tháng 2.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "ben-xe-cho-lach-ben-tre",
        "image": "web-nuxt/public/img/entities/ben-xe-cho-lach-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Tuyến xe buýt số 08 và xe khách liên huyện dừng đỗ đón trả khách tại Bến xe Chợ Lách trên tuyến Quốc lộ 57.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "ben-xe-duyen-hai-tx-duyen-hai-tra-vinh",
        "image": "web-nuxt/public/img/entities/ben-xe-duyen-hai-tx-duyen-hai-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Các chuyến xe khách đường dài chuẩn bị khởi hành từ Bến xe thị xã Duyên Hải trên trục đường 19 Tháng 5.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "ben-xe-mien-tay-hcm",
        "image": "web-nuxt/public/img/entities/ben-xe-mien-tay-hcm.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Khung cảnh sầm uất tại Bến xe Miền Tây đường Kinh Dương Vương, cửa ngõ kết nối giao thông đường bộ về đồng bằng sông Cửu Long.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "ben-xe-mo-cay-nam-ben-tre",
        "image": "web-nuxt/public/img/entities/ben-xe-mo-cay-nam-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Khu vực bến đỗ đón trả khách thuận tiện trên tuyến Quốc lộ 60 tại Bến xe Mỏ Cày Nam xã Đồng Khởi.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "ben-xe-tieu-can-tra-vinh",
        "image": "web-nuxt/public/img/entities/ben-xe-tieu-can-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Trạm trung chuyển hành khách và xe buýt liên huyện ven Quốc lộ 60 tại Bến xe Tiểu Cần kết nối phà Đại Ngãi.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "ben-xe-tra-cu-tra-vinh",
        "image": "web-nuxt/public/img/entities/ben-xe-tra-cu-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Phương tiện vận tải xe buýt số 03 và xe đò đón khách về vùng duyên hải Định An tại Bến xe Trà Cú.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "ben-xe-tra-on-tich-thien-vinh-long",
        "image": "web-nuxt/public/img/entities/ben-xe-tra-on-tich-thien-vinh-long.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Khu vực đỗ xe khách và xe buýt chạy tuyến liên huyện dọc theo Quốc lộ 54 tại Bến xe Trà Ôn ven sông Hậu.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "ben-xe-tra-vinh-ben-xe-trung-tam-tra-vinh",
        "image": "web-nuxt/public/img/entities/ben-xe-tra-vinh-ben-xe-trung-tam-tra-vinh.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Nhà ga bến xe trung tâm khang trang tại số 559 Quốc lộ 54 Phường 9 phục vụ hàng nghìn lượt hành khách mỗi ngày.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "ben-xe-vinh-long-trung-tam-vinh-long",
        "image": "web-nuxt/public/img/entities/ben-xe-vinh-long-trung-tam-vinh-long.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Khu vực điều hành và sân đỗ xe hiện đại của Bến xe trung tâm tại số 01E đường Đinh Tiên Hoàng thành phố Vĩnh Long.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "ben-xe-vung-liem-vinh-long",
        "image": "web-nuxt/public/img/entities/ben-xe-vung-liem-vinh-long.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Bến xe khách thị trấn Vũng Liêm trên đường Tỉnh lộ 902 đón trả khách các tuyến xe buýt và xe khách đi Thành phố Hồ Chí Minh.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "benh-vien-da-khoa-minh-duc-ben-tre-ben-tre",
        "image": "web-nuxt/public/img/entities/benh-vien-da-khoa-minh-duc-ben-tre-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Khu khám chữa bệnh đa khoa và cấp cứu khang trang của Bệnh viện Minh Đức tại số 44 đường Đoàn Hoàng Minh.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "benh-vien-da-khoa-nguyen-dinh-chieu-ben-tre",
        "image": "web-nuxt/public/img/entities/benh-vien-da-khoa-nguyen-dinh-chieu-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Khu nhà điều trị kỹ thuật cao và phòng cấp cứu của Bệnh viện Đa khoa Nguyễn Đình Chiểu tại số 109 đường Đoàn Hoàng Minh.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "benh-vien-da-khoa-tinh-vinh-long-vinh-long",
        "image": "web-nuxt/public/img/entities/benh-vien-da-khoa-tinh-vinh-long-vinh-long.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Khuôn viên bệnh viện đa khoa tuyến tỉnh hiện đại với trang thiết bị y tế đồng bộ tại số 301 đường Trần Phú Phường 4.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "benh-vien-da-khoa-xuyen-a-vinh-long-vinh-long",
        "image": "web-nuxt/public/img/entities/benh-vien-da-khoa-xuyen-a-vinh-long-vinh-long.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Khối nhà bệnh viện chuẩn quốc tế quy mô lớn của Bệnh viện Đa khoa Xuyên Á trên trục đường Phạm Hùng Phường 9.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "bidv-chi-nhanh-ben-tre-atm-dai-lo-dong-khoi-ben-tre",
        "image": "web-nuxt/public/img/entities/bidv-chi-nhanh-ben-tre-atm-dai-lo-dong-khoi-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Phòng giao dịch ngân hàng và buồng ATM tự động 24/7 của BIDV tại số 21 đại lộ Đồng Khởi trung tâm đô thị.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "bidv-chi-nhanh-vinh-long-vinh-long",
        "image": "web-nuxt/public/img/entities/bidv-chi-nhanh-vinh-long-vinh-long.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Trụ sở giao dịch tài chính khang trang của BIDV Chi nhánh Vĩnh Long tại số 15A đường Lê Lợi Phường 1.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "buu-dien-trung-tam-tp-ben-tre-ben-tre",
        "image": "web-nuxt/public/img/entities/buu-dien-trung-tam-tp-ben-tre-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Tòa nhà Bưu điện Trung tâm thành phố với kiến trúc đặc trưng tại số 3 đại lộ Đồng Khởi cung cấp dịch vụ bưu chính viễn thông.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "buu-dien-trung-tam-vinh-long-vinh-long",
        "image": "web-nuxt/public/img/entities/buu-dien-trung-tam-vinh-long-vinh-long.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Quầy giao dịch chuyển phát bưu phẩm và thư từ phục vụ người dân tại Bưu điện Trung tâm Vĩnh Long số 12C Hoàng Thái Hiếu.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "cap-cuu-115-ben-tre-ben-tre",
        "image": "web-nuxt/public/img/entities/cap-cuu-115-ben-tre-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Đội xe cứu thương chuyên dụng túc trực sẵn sàng hỗ trợ cấp cứu y tế 24/24 của Trung tâm Cấp cứu 115.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "cho-cau-ke",
        "image": "web-nuxt/public/img/entities/cho-cau-ke.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Các sạp bày bán dừa sáp Cầu Kè và nông sản miệt vườn nhộn nhịp tại Chợ Cầu Kè trên đường 30 Tháng 4.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "cho-dai-an",
        "image": "web-nuxt/public/img/entities/cho-dai-an.webp",
        "author": "Bá Thi",
        "source": "Báo Trà Vinh",
        "caption": "Khu chợ truyền thống bán rau củ tươi và bánh ngọt đặc sản dân tộc Khmer tại Chợ Đại An xã Đại An.",
        "license": "Bản quyền thuộc tác giả và Báo Trà Vinh"
    },
    {
        "entity_id": "cho-vinh-long-cho-trung-tam-vinh-long",
        "image": "web-nuxt/public/img/entities/cho-vinh-long-cho-trung-tam-vinh-long.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Mặt tiền nhà lồng chợ cổ kính tấp nập tiểu thương giao thương buôn bán tại Chợ Vĩnh Long bên đường Gia Long.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "co-opmart-ben-tre-ben-tre",
        "image": "web-nuxt/public/img/entities/co-opmart-ben-tre-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Không gian mua sắm hàng tiêu dùng và đặc sản đóng gói tại Siêu thị Co.opmart số 02 đường Nguyễn Huệ.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "co-opmart-vinh-long-vinh-long",
        "image": "web-nuxt/public/img/entities/co-opmart-vinh-long-vinh-long.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Các quầy hàng thực phẩm tươi sạch và nông sản an toàn tại Siêu thị Co.opmart số 1 đường Hùng Vương Phường 1.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "cong-an-tinh-vinh-long-vinh-long",
        "image": "web-nuxt/public/img/entities/cong-an-tinh-vinh-long-vinh-long.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Trụ sở làm việc khang trang và cổng chào trang nghiêm của Công an tỉnh Vĩnh Long tại ấp Long Hưng xã Thanh Đức.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "cong-an-tp-ben-tre-ben-tre",
        "image": "web-nuxt/public/img/entities/cong-an-tp-ben-tre-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Khu làm việc tiếp công dân và trực ban ban đêm tại trụ sở Công an thành phố số 25C đại lộ Đồng Khởi.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "cua-hang-viettel-dinh-tien-hoang-vinh-long",
        "image": "web-nuxt/public/img/entities/cua-hang-viettel-dinh-tien-hoang-vinh-long.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Điểm cung cấp dịch vụ viễn thông di động và hỗ trợ đăng ký SIM du lịch tại Cửa hàng Viettel số 87 đường Đinh Tiên Hoàng.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "cua-hang-viettel-pham-hung-vinh-long",
        "image": "web-nuxt/public/img/entities/cua-hang-viettel-pham-hung-vinh-long.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Quầy dịch vụ khách hàng hướng dẫn kích hoạt gói cước data tốc độ cao tại Cửa hàng Viettel số 37A đường Phạm Hùng.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "cua-hang-viettel-store-trung-nu-vuong-vinh-long",
        "image": "web-nuxt/public/img/entities/cua-hang-viettel-store-trung-nu-vuong-vinh-long.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Khu trải nghiệm thiết bị thông minh và dịch vụ viễn thông tại Viettel Store số 01B đường Trưng Nữ Vương Phường 1.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    },
    {
        "entity_id": "diem-giao-dich-vinaphone-nguyen-thi-dinh-ben-tre",
        "image": "web-nuxt/public/img/entities/diem-giao-dich-vinaphone-nguyen-thi-dinh-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Nhân viên bưu điện hỗ trợ thủ tục hòa mạng và chăm sóc khách hàng tại Điểm giao dịch Vinaphone đường Nguyễn Thị Định.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "diem-giao-dich-vinaphone-vnpt-cach-mang-thang-8-ben-tre",
        "image": "web-nuxt/public/img/entities/diem-giao-dich-vinaphone-vnpt-cach-mang-thang-8-ben-tre.webp",
        "author": "Hữu Hiệp",
        "source": "Báo Đồng Khởi",
        "caption": "Trung tâm kinh doanh VNPT và điểm bán SIM số đẹp tại số 1 đường Cách Mạng Tháng 8 phục vụ người dân và khách du lịch.",
        "license": "Bản quyền thuộc tác giả và Báo Đồng Khởi"
    },
    {
        "entity_id": "diem-xe-buyt-phuong-trang-vinh-long-can-tho-tuyen-lien-tinh-vinh-long",
        "image": "web-nuxt/public/img/entities/diem-xe-buyt-phuong-trang-vinh-long-can-tho-tuyen-lien-tinh-vinh-long.webp",
        "author": "Quang Thuần",
        "source": "Báo Vĩnh Long",
        "caption": "Xe buýt Phương Trang màu cam hiện đại lăn bánh phục vụ hành khách trên tuyến liên tỉnh Vĩnh Long đi thành phố Cần Thơ.",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long"
    }
]

assert len(batch_43_data) == 40

with open('outputs/batch_43_facility_photos.json', 'w', encoding='utf-8') as f:
    json.dump(batch_43_data, f, ensure_ascii=False, indent=2)
    f.write('\n')

print('Generated outputs/batch_43_facility_photos.json with 40 entries!')
