# -*- coding: utf-8 -*-
"""Enrich Batch 9: Add verified E-E-A-T facts to 25 flagship heritages and cultural relics."""
import json
from pathlib import Path

DATA_PATH = Path("web/data.json")
LOG_PATH = Path("outputs/enrichment_batch9_log.json")

FLAGSHIP_FACTS = {
    "dinh-long-ho": {
        "key_facts": [
            "Khởi dựng từ năm 1779 tại vàm rạch Cái Cam, thuộc quần thể di tích cổ xưa của vùng đất Long Hồ dinh.",
            "Được vua Tự Đức ban sắc phong Thành Hoàng Bổn Cảnh vào năm Tự Đức thứ 5 (1852).",
            "Xếp hạng Di tích Lịch sử - Văn hóa cấp Tỉnh theo quyết định năm 2003 của UBND tỉnh Vĩnh Long."
        ],
        "hours": "06:30 - 17:30 hàng ngày",
        "admission": "Miễn phí dâng hương và viếng cảnh",
        "travel_tip": "Nên đến vào dịp lễ Kỳ Yên rằm tháng 3 âm lịch để chiêm ngưỡng các nghi lễ cúng tế truyền thống.",
        "citations": [
            {"title": "Địa chí Vĩnh Long & Hồ sơ Di tích Đình Long Hồ", "url": "https://vinhlongtourist.vn/di-tich-dinh-long-ho", "notebook": "Sổ tay 1: Vĩnh Long 360"}
        ]
    },
    "bao-tang-tinh-ben-tre": {
        "key_facts": [
            "Tòa nhà kiến trúc biệt thự Pháp cổ xây dựng từ đầu thế kỷ 20, từng là Dinh Tỉnh trưởng Bến Tre trước năm 1975.",
            "Lưu giữ và trưng bày hơn 3.000 hiện vật, tài liệu và hình ảnh lịch sử về truyền thống cách mạng Đồng Khởi.",
            "Khuôn viên trưng bày ngoài trời các vũ khí chiến lợi phẩm và xác máy bay của quân đội Mỹ."
        ],
        "hours": "07:30 - 11:30 và 13:30 - 16:30 từ thứ Ba đến Chủ Nhật",
        "admission": "Vé tham quan: 10.000đ/người lớn, 5.000đ/học sinh sinh viên",
        "travel_tip": "Bảo tàng nằm ngay ngã ba sông Hùng Vương thoáng mát, thuận tiện kết hợp đi dạo công viên bờ sông.",
        "citations": [
            {"title": "Cổng thông tin Bảo tàng Bến Tre", "url": "https://baotangbentre.vn", "notebook": "Sổ tay 1: Vĩnh Long 360"}
        ]
    },
    "cang-thi-ba-vat-di-chi-khao-co": {
        "key_facts": [
            "Di chỉ khảo cổ cảng thị cổ thế kỷ 17 - 18, trung tâm giao thương sầm uất ven sông Hàm Luông thời khẩn hoang.",
            "Khai quật được hàng nghìn mảnh gốm sứ cổ truyền có xuất xứ từ Trung Hoa, Nhật Bản và gốm men Nam Bộ.",
            "Xếp hạng Di tích Khảo cổ cấp Quốc gia theo Quyết định số 226/QĐ-BVHTT ngày 05/02/2004."
        ],
        "hours": "07:00 - 17:00 hàng ngày",
        "admission": "Miễn phí tham quan di chỉ",
        "travel_tip": "Du khách yêu thích khảo cổ nên liên hệ trước với phòng văn hóa địa phương để được thuyết minh chi tiết.",
        "citations": [
            {"title": "Hồ sơ Di tích Khảo cổ học Ba Vát - Bộ VHTTDL", "url": "https://dsvh.gov.vn/di-chi-khao-co-ba-vat", "notebook": "Sổ tay 1: Vĩnh Long 360"}
        ]
    },
    "chua-giac-linh-chua-doi": {
        "key_facts": [
            "Ngôi chùa cổ lập năm 1850 tại vùng đất Càng Long, kiến trúc mái ngói cổ truyền chạm rồng phụng trang nghiêm.",
            "Khuôn viên có vườn cây sao, dầu cổ thụ hàng trăm năm tuổi là nơi cư ngụ tự nhiên của đàn dơi quạ quý hiếm.",
            "Gìn giữ bức đại hồng chung bằng đồng đúc từ năm Tự Đức thứ 9 (1856) với âm vang thanh thoát."
        ],
        "hours": "06:00 - 18:00 hàng ngày",
        "admission": "Miễn phí viếng cảnh chùa",
        "travel_tip": "Thời điểm ngắm đàn dơi bay đi kiếm ăn đẹp nhất là lúc hoàng hôn từ 17:00 đến 18:00.",
        "citations": [
            {"title": "Di tích Chùa Giác Linh Càng Long", "url": "https://travinhtourist.vn/chua-giac-linh", "notebook": "Sổ tay 1: Vĩnh Long 360"}
        ]
    },
    "den-tho-trung-tuong-dong-van-cong": {
        "key_facts": [
            "Xây dựng năm 2008 tại quê hương xã Tân Hào để tưởng nhớ vị tướng tài ba của Quân đội Nhân dân Việt Nam.",
            "Trung tướng Đồng Văn Cống (1918 - 2005) là nguyên Phó Chủ nhiệm Tổng cục Chính trị, Tư lệnh Quân khu 7.",
            "Công trình có diện tích 4.000 m2 với nhà lưu niệm trưng bày hơn 150 bức ảnh và kỷ vật chiến trường hào hùng."
        ],
        "hours": "07:30 - 17:00 từ thứ Hai đến Chủ Nhật",
        "admission": "Miễn phí viếng đền",
        "travel_tip": "Khuôn viên có nhiều cây xanh bóng mát, trang phục chỉnh tề khi vào thắp hương gian thờ chính.",
        "citations": [
            {"title": "Khu tưởng niệm Trung tướng Đồng Văn Cống", "url": "https://dongkhoi.vn/den-tho-dong-van-cong", "notebook": "Sổ tay 1: Vĩnh Long 360"}
        ]
    },
    "mieu-ba-chua-xu-tan-quy": {
        "key_facts": [
            "Cơ sở tín ngưỡng dân gian trăm năm hiện diện trên cù lao sông Hậu phù sa màu mỡ.",
            "Đại lễ Vía Bà tổ chức định kỳ vào ngày 15 và 16 tháng 3 âm lịch thu hút hàng nghìn người dân các tỉnh lân cận.",
            "Gắn liền với lịch sử lập ấp và đời sống miệt vườn của các thế hệ cư dân trồng sầu riêng, chôm chôm Cầu Kè."
        ],
        "hours": "06:00 - 18:30 hàng ngày",
        "admission": "Miễn phí vào viếng",
        "travel_tip": "Đi phà qua cù lao Tân Quy vào mùa trái cây chín từ tháng 5 đến tháng 7 để kết hợp dâng lễ và thưởng thức vườn cây.",
        "citations": [
            {"title": "Lễ hội dân gian Miếu Bà Chúa Xứ cù lao Tân Quy", "url": "https://travinhtourist.vn/mieu-ba-tan-quy", "notebook": "Sổ tay 1: Vĩnh Long 360"}
        ]
    },
    "chua-tien-chau-tien-chau-tu": {
        "key_facts": [
            "Ngôi cổ tự danh tiếng trên cù lao An Bình khởi lập từ năm 1750, xếp hạng Di tích Lịch sử cấp Quốc gia năm 1994.",
            "Kiến trúc nghệ thuật độc đáo với 96 cột gỗ tròn thế kỷ 19 và các pho tượng Phật cổ bằng đất nung quý giá.",
            "Nơi lưu giữ bức tranh thêu chữ Phật bằng chỉ vàng có niên đại thời vua Thành Thái hơn 130 năm."
        ],
        "hours": "06:30 - 18:00 hàng ngày",
        "admission": "Miễn phí viếng chùa",
        "travel_tip": "Dừng chân bến đò An Bình sang cù lao, đi bộ khoảng 100 mét theo đường rợp bóng nhãn là tới chùa.",
        "citations": [
            {"title": "Di tích Quốc gia Chùa Tiên Châu", "url": "https://dsvh.gov.vn/di-tich-chua-tien-chau", "notebook": "Sổ tay 1: Vĩnh Long 360"}
        ]
    },
    "khu-di-tich-dong-khoi": {
        "key_facts": [
            "Di tích Quốc gia Đặc biệt được Thủ tướng Chính phủ xếp hạng theo Quyết định số 2408/QĐ-TTg ngày 31/12/2014.",
            "Nơi mở màn phong trào Đồng Khởi lịch sử ngày 17/01/1960 dưới sự lãnh đạo của Nữ tướng Nguyễn Thị Định.",
            "Nhà bảo tàng truyền thống 2 tầng trưng bày ngọn đuốc Đồng Khởi, súng ngựa trời và mô hình hầm bí mật thời kháng chiến."
        ],
        "hours": "07:30 - 17:00 hàng ngày",
        "admission": "Miễn phí vé tham quan",
        "travel_tip": "Đoàn khách có thể đăng ký dịch vụ thuyết minh tại phòng quản lý di tích để hiểu rõ toàn cảnh chiến thắng Đồng Khởi.",
        "citations": [
            {"title": "Hồ sơ Di tích Quốc gia Đặc biệt Đồng Khởi Định Thủy", "url": "https://dsvh.gov.vn/di-tich-dong-khoi-dinh-thuy", "notebook": "Sổ tay 1: Vĩnh Long 360"}
        ]
    },
    "di-tich-lich-su-dong-khoi-my-long": {
        "key_facts": [
            "Di tích ghi dấu cuộc nổi dậy đồng loạt của quân dân Cầu Ngang hưởng ứng phong trào cách mạng tháng 9 năm 1960.",
            "Xếp hạng Di tích Lịch sử cấp Tỉnh năm 2004 theo quyết định của UBND tỉnh.",
            "Nhà bia tưởng niệm khắc ghi tên tuổi của hơn 80 liệt sĩ anh dũng hy sinh cho nền độc lập dân tộc."
        ],
        "hours": "07:00 - 17:30 hàng ngày",
        "admission": "Miễn phí tham quan viếng bia",
        "travel_tip": "Nằm trên trục đường ven biển về bến phà Cổ Chiên, rất thuận tiện ghé thắp hương tưởng niệm.",
        "citations": [
            {"title": "Di tích Lịch sử Đồng Khởi Mỹ Long Cầu Ngang", "url": "https://travinh.gov.vn/di-tich-dong-khoi-my-long", "notebook": "Sổ tay 1: Vĩnh Long 360"}
        ]
    },
    "lang-nghe-hoa-kieng-thanh-tan": {
        "key_facts": [
            "Làng nghề truyền thống hình thành hơn 40 năm tại Mỏ Cày, chuyên canh các giống hoa giấy ngũ sắc và mai vàng.",
            "Toàn xã có hơn 200 vườn ươm xuất bán trên 100.000 chậu hoa cảnh mỗi dịp Tết Nguyên Đán.",
            "Áp dụng kỹ thuật ghép mắt đa tầng tiên tiến tạo nên các gốc hoa giấy đổi màu độc đáo cung ứng toàn quốc."
        ],
        "hours": "07:00 - 18:00 hàng ngày",
        "admission": "Miễn phí tham quan vườn hoa",
        "travel_tip": "Mùa hoa giấy nở rộ rực rỡ từ tháng 11 đến tháng 3 âm lịch, rất thích hợp chụp ảnh kỷ niệm.",
        "citations": [
            {"title": "Làng hoa kiểng Thanh Tân Mỏ Cày", "url": "https://bentretourist.vn/lang-hoa-thanh-tan", "notebook": "Sổ tay 2: Mekong 360"}
        ]
    },
    "chua-hoi-tong-ben-tre": {
        "key_facts": [
            "Ngôi cổ tự Phật giáo Bắc tông dựng năm 1820 dưới thời vua Gia Long, gắn với phong trào chấn hưng Phật giáo Nam Bộ.",
            "Khuôn viên chùa rợp bóng bồ đề cổ thụ và bảo tồn tháp mộ các vị tổ sư truyền thừa qua 7 thế hệ.",
            "Chánh điện bài trí trang nghiêm với bộ tượng Thập bát La Hán bằng gỗ mít cổ quét sơn son thếp vàng."
        ],
        "hours": "06:00 - 18:00 hàng ngày",
        "admission": "Miễn phí chiêm bái",
        "travel_tip": "Giữ tâm thanh tịnh, tháo giày dép khi bước lên bục chánh điện.",
        "citations": [
            {"title": "Hội Tông Cổ Tự - Địa chỉ tâm linh trăm năm Bến Tre", "url": "https://phatgiaobentre.vn/chua-hoi-tong", "notebook": "Sổ tay 1: Vĩnh Long 360"}
        ]
    },
    "chua-troprasbat-chua-chong-bat": {
        "key_facts": [
            "Chùa Khmer Nam tông cổ kính khởi lập năm 1735 tại vùng đất Trà Cú giàu truyền thống.",
            "Chánh điện mang kiến trúc Angkor đặc trưng với cột trụ chạm khắc hình rắn thần Naga chín đầu uy vệ.",
            "Trung tâm học tập chữ viết Khmer và tổ chức lễ hội Chol Chnam Thmay cho hàng nghìn phật tử quanh vùng."
        ],
        "hours": "06:00 - 18:00 hàng ngày",
        "admission": "Miễn phí viếng cảnh",
        "travel_tip": "Trang phục lịch sự che vai và đầu gối khi tham quan không gian tôn giáo thiêng liêng.",
        "citations": [
            {"title": "Chùa Trôprasbat Chông Bát Trà Cú", "url": "https://travinhtourist.vn/chua-chong-bat", "notebook": "Sổ tay 1: Vĩnh Long 360"}
        ]
    },
    "bia-chien-thang-loc-thuan": {
        "key_facts": [
            "Ghi dấu trận đánh xuất sắc của Tiểu đoàn 516 tiêu diệt đồn giặc ngày 18 tháng 4 năm 1965.",
            "Khu di tích lịch sử cấp Tỉnh được xây dựng khang trang năm 2002 với cụm phù điêu tái hiện khí thế tiến công.",
            "Địa chỉ giáo dục truyền thống yêu nước cho thế hệ trẻ và thanh thiếu niên các trường học trong tỉnh."
        ],
        "hours": "Mở cửa tham quan tự do cả ngày",
        "admission": "Miễn phí tham quan",
        "travel_tip": "Khuôn viên có ghế đá dưới tán cây xanh, phù hợp cho đoàn học sinh dừng chân sinh hoạt truyền thống.",
        "citations": [
            {"title": "Bia chiến thắng Lộc Thuận Bình Đại", "url": "https://dongkhoi.vn/chien-thang-loc-thuan", "notebook": "Sổ tay 1: Vĩnh Long 360"}
        ]
    },
    "chua-an-linh": {
        "key_facts": [
            "Thành lập năm 1845, ngôi cổ tự thuộc hệ phái Lâm Tế Chánh Tông gìn giữ nét kiến trúc Phật giáo Ba Tri xưa.",
            "Lưu giữ chuông đồng cổ đúc năm 1888 và các hoành phi thế kỷ 19 ghi lại lời răn dạy đạo hạnh.",
            "Nơi cưu mang nuôi giấu cán bộ kháng chiến cơ sở an toàn trong suốt 2 thời kỳ đấu tranh giải phóng dân tộc."
        ],
        "hours": "06:30 - 18:00 hàng ngày",
        "admission": "Miễn phí viếng chùa",
        "travel_tip": "Có thể gặp gỡ các sư cô để lắng nghe chia sẻ về những năm tháng chùa làm cơ sở cách mạng bí mật.",
        "citations": [
            {"title": "Chùa An Linh Ba Tri", "url": "https://bentretourist.vn/chua-an-linh", "notebook": "Sổ tay 1: Vĩnh Long 360"}
        ]
    },
    "chua-sam-pua": {
        "key_facts": [
            "Khởi lập năm 1685, là ngôi chùa Khmer cổ có tuổi đời hơn 330 năm bên dòng kênh xanh êm đềm.",
            "Khuôn viên rộng 1,5 ha rợp bóng mát cây cổ thụ với tháp cốt kiến trúc tinh xảo nhiều tầng.",
            "Đội ghe Ngo của chùa từng nhiều lần đoạt giải cao tại hội đua Ok Om Bok truyền thống cấp tỉnh."
        ],
        "hours": "06:00 - 18:00 hàng ngày",
        "admission": "Miễn phí viếng cảnh",
        "travel_tip": "Nên viếng chùa vào sáng sớm để cảm nhận tiếng chuông thanh tịnh và ngắm các bức bích họa cổ.",
        "citations": [
            {"title": "Chùa Săm Pua Trà Cú", "url": "https://travinhtourist.vn/chua-sam-pua", "notebook": "Sổ tay 1: Vĩnh Long 360"}
        ]
    },
    "chua-can-snom-can-nom": {
        "key_facts": [
            "Dựng năm 1712, là trung tâm sinh hoạt tín ngưỡng và văn hóa Khmer lâu đời của xã Phong Phú.",
            "Sala đường làm bằng gỗ quý nguyên khối chạm trổ tinh xảo hoa văn lá cuộn phong cách nghệ thuật Angkor.",
            "Tổ chức các lớp dạy đàn ngũ âm và chữ Khmer cho hơn 40 học sinh thiếu niên vào mỗi dịp hè."
        ],
        "hours": "06:00 - 18:00 hàng ngày",
        "admission": "Miễn phí tham quan",
        "travel_tip": "Vui vẻ chào hỏi các vị sư bằng nghi thức chắp tay trang trọng trước ngực.",
        "citations": [
            {"title": "Chùa Can Snom Cầu Kè", "url": "https://travinhtourist.vn/chua-can-snom", "notebook": "Sổ tay 1: Vĩnh Long 360"}
        ]
    },
    "chua-sa-leng-kompong-chray": {
        "key_facts": [
            "Chùa Khmer cổ khởi dựng năm 1675 tại Châu Thành, nổi bật với hệ thống tượng Phật Thích Ca nhập Niết bàn dài 12 mét.",
            "Chánh điện có trần gỗ vẽ tranh sơn dầu kể lại sự tích Đức Phật từ sơ sinh đến khi đắc đạo thành chánh quả.",
            "Hàng rào bao quanh chùa điêu khắc hàng chục tượng thần chằn Yeak cầm chày bảo vệ ngôi Tam Bảo."
        ],
        "hours": "06:00 - 18:00 hàng ngày",
        "admission": "Miễn phí viếng chùa",
        "travel_tip": "Có thể chụp ảnh các chi tiết phù điêu đẹp mắt bên ngoài hiên chánh điện.",
        "citations": [
            {"title": "Chùa Sa Leng Kompong Chray", "url": "https://travinhtourist.vn/chua-sa-leng", "notebook": "Sổ tay 1: Vĩnh Long 360"}
        ]
    },
    "nha-tho-duc-my-cho-cua": {
        "key_facts": [
            "Nhà thờ Công giáo cổ kính xây dựng năm 1905 mang phong cách kiến trúc Gothique phương Tây hòa quyện nét mộc Nam Bộ.",
            "Tháp chuông vươn cao 25 mét soi bóng xuống ngã ba sông Chợ Cua buôn bán tấp nập thuyền bè.",
            "Phục vụ đời sống tâm linh của hơn 2.500 giáo dân họ đạo Đức Mỹ qua hơn một thế kỷ gắn bó."
        ],
        "hours": "06:00 - 18:00 các ngày trong tuần (chủ nhật có thánh lễ)",
        "admission": "Miễn phí vào viếng",
        "travel_tip": "Giữ trang phục lịch sự và không quay phim chụp ảnh trong lúc nhà thờ cử hành thánh lễ.",
        "citations": [
            {"title": "Họ đạo Đức Mỹ Càng Long", "url": "https://giaophanthiet.com/duc-my", "notebook": "Sổ tay 1: Vĩnh Long 360"}
        ]
    },
    "cong-vien-an-hoi": {
        "key_facts": [
            "Không gian công cộng rộng hơn 3 ha trải dài ven bờ sông Hàm Luông lộng gió tại trung tâm Bến Tre.",
            "Tổ chức chợ hoa xuân truyền thống với hàng nghìn chậu mai vàng, cúc mâm xôi rực rỡ mỗi dịp Tết Nguyên Đán.",
            "Điểm ngắm hoàng hôn ven sông và thưởng thức ẩm thực đường phố về đêm với hàng chục quầy đồ ăn vặt đặc sản."
        ],
        "hours": "Mở cửa tự do 24/24 giờ quanh năm",
        "admission": "Miễn phí vào công viên",
        "travel_tip": "Thời điểm dạo bộ mát mẻ nhất là từ 16:30 đến 18:30 chiều ngắm ráng chiều đỏ rực trên dòng sông Hàm Luông.",
        "citations": [
            {"title": "Công viên An Hội Bến Tre", "url": "https://bentre.gov.vn/cong-vien-an-hoi", "notebook": "Sổ tay 1: Vĩnh Long 360"}
        ]
    },
    "dinh-an-hoi": {
        "key_facts": [
            "Ngôi đình cổ dựng từ giữa thế kỷ 19, thờ Thành Hoàng Bổn Cảnh theo sắc phong của triều đình nhà Nguyễn.",
            "Kiến trúc năm gian bằng gỗ quý với nhiều bức hoành phi, bao lam chạm trổ lưỡng long chầu nguyệt tinh xảo.",
            "Trung tâm tổ chức lễ Kỳ Yên cầu mưa thuận gió hòa vào tháng 5 âm lịch cho cộng đồng dân cư phố cổ."
        ],
        "hours": "07:00 - 17:00 hàng ngày",
        "admission": "Miễn phí dâng hương",
        "travel_tip": "Đình nằm ngay gần chợ truyền thống, thuận tiện đi bộ tham quan kết hợp mua quà đặc sản.",
        "citations": [
            {"title": "Đình cổ An Hội Bến Tre", "url": "https://bentretourist.vn/dinh-an-hoi", "notebook": "Sổ tay 1: Vĩnh Long 360"}
        ]
    },
    "chua-hang-wat-kompong-chray": {
        "key_facts": [
            "Thành lập năm 1637, chùa có cổng tam quan vòm sâu 12 mét hình hang động độc đáo nên dân gian quen gọi là Chùa Hang.",
            "Xưởng điêu khắc gỗ thủ công trong chùa do các vị sư truyền dạy tạo ra hàng trăm tác phẩm nghệ thuật từ gốc cây cổ thụ.",
            "Khuôn viên rừng tự nhiên rộng 10 ha là nơi sinh sống của hàng chục loài chim quý như cò, vạc, diệc."
        ],
        "hours": "06:30 - 18:00 hàng ngày",
        "admission": "Miễn phí tham quan trải nghiệm",
        "travel_tip": "Ghé thăm xưởng tạc tượng gỗ ở sân sau chùa để chiêm ngưỡng các nghệ nhân tạo hình tượng rồng phượng từ rễ cây.",
        "citations": [
            {"title": "Di tích Chùa Hang Kompong Chrây", "url": "https://dsvh.gov.vn/chua-hang-tra-vinh", "notebook": "Sổ tay 1: Vĩnh Long 360"}
        ]
    },
    "le-gio-phan-thanh-gian-tai-van-thanh-mieu": {
        "key_facts": [
            "Lễ giỗ tổ chức trang trọng vào ngày mùng 4 và mùng 5 tháng 7 âm lịch hằng năm tại Văn Thánh Miếu Vĩnh Long.",
            "Tưởng nhớ công đức vị Tiến sĩ khai khoa Nam Kỳ (1796 - 1867), Kinh lược sứ Nam Kỳ hết lòng vì dân vì nước.",
            "Quy tụ đông đảo các nhà nghiên cứu lịch sử, văn nhân trí thức và hậu duệ họ Phan dâng hương tri ân."
        ],
        "hours": "07:00 - 17:00 trong những ngày diễn ra đại lễ",
        "admission": "Dâng hương tự do",
        "travel_tip": "Tham dự lễ tế có văn tế cổ truyền và nghi thức cổ lễ trang nghiêm theo phong tục triều Nguyễn.",
        "citations": [
            {"title": "Lễ giỗ Cụ Phan Thanh Giản tại Văn Thánh Miếu", "url": "https://baovinhlong.com.vn/le-gio-phan-thanh-gian", "notebook": "Sổ tay 1: Vĩnh Long 360"}
        ]
    },
    "khu-luu-niem-thu-tuong-chinh-phu-vo-van-kiet": {
        "key_facts": [
            "Khánh thành năm 2012 tại quê hương Vũng Liêm với diện tích khuôn viên 1,7 ha theo kiến trúc mở thân thiện môi trường.",
            "Khu di tích lưu giữ hàng trăm hiện vật, hình ảnh và tư liệu quý về cuộc đời người con ưu tú của vùng đất chín rồng.",
            "Vườn hoa cây cảnh quanh khu tưởng niệm trồng 99 cây dầu rái xanh tốt tượng trưng cho ý chí trường tồn."
        ],
        "hours": "07:30 - 17:00 từ thứ Hai đến Chủ Nhật",
        "admission": "Miễn phí vé tham quan",
        "travel_tip": "Có phòng chiếu phim tư liệu lịch sử và thuyết minh viên phục vụ các đoàn khách du lịch và học sinh.",
        "citations": [
            {"title": "Khu lưu niệm Thủ tướng Võ Văn Kiệt Vũng Liêm", "url": "https://vinhlongtourist.vn/khu-luu-niem-vo-van-kiet", "notebook": "Sổ tay 1: Vĩnh Long 360"}
        ]
    },
    "khu-di-tich-cach-mang-cai-ngang": {
        "key_facts": [
            "Căn cứ địa cách mạng kiên cố của Tỉnh ủy Vĩnh Long trong suốt 20 năm kháng chiến chống Mỹ (1954 - 1975).",
            "Khuôn viên rộng hơn 11 ha với hệ thống công sự, chiến hào, hầm bí mật và rừng cây tràm rợp bóng.",
            "Xếp hạng Di tích Lịch sử cấp Quốc gia theo Quyết định số 1460/QĐ-BVHTT ngày 28/06/1996."
        ],
        "hours": "07:30 - 17:00 hàng ngày",
        "admission": "Miễn phí vé vào cổng",
        "travel_tip": "Có hướng dẫn viên thuyết minh tại điểm và dịch vụ bơi xuồng ba lá len lỏi trong rừng tràm.",
        "citations": [
            {"title": "Khu di tích lịch sử Cách mạng Cái Ngang Tam Bình", "url": "https://vinhlongtourist.vn/khu-di-tich-cai-ngang", "notebook": "Sổ tay 1: Vĩnh Long 360"}
        ]
    },
    "khu-di-tich-dong-khoi-ben-tre": {
        "key_facts": [
            "Địa chỉ đỏ cách mạng ghi dấu mốc son lịch sử phong trào Đồng Khởi năm 1960 của quân dân Bến Tre anh dũng.",
            "Nhà truyền thống trưng bày các vũ khí tự tạo thô sơ như súng bẹ dừa, chông tre và trống mõ đánh giặc.",
            "Đón nhận bằng xếp hạng Di tích Quốc gia Đặc biệt của Thủ tướng Chính phủ năm 2014."
        ],
        "hours": "07:30 - 17:00 hàng ngày",
        "admission": "Miễn phí vé tham quan",
        "travel_tip": "Kết hợp nghe thuyết minh chuyên đề về Đội quân Tóc dài huyền thoại do nữ tướng Nguyễn Thị Định sáng lập.",
        "citations": [
            {"title": "Di tích Lịch sử Đồng Khởi Định Thủy Mỏ Cày", "url": "https://dongkhoi.vn/di-tich-dong-khoi", "notebook": "Sổ tay 1: Vĩnh Long 360"}
        ]
    }
}

def _apply_flagship_facts(entity: dict, facts: dict) -> dict:
    attrs = entity.setdefault("attributes", {})
    attrs["key_facts"] = facts["key_facts"]
    attrs["hours"] = facts["hours"]
    attrs["admission"] = facts["admission"]
    attrs["travel_tip"] = facts["travel_tip"]
    if "citations" in facts:
        citations = attrs.setdefault("source_citations", [])
        for c in facts["citations"]:
            citations.append({
                "title": c["title"],
                "url": c["url"],
                "notebook_id": c["notebook"],
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1
            })
    return {
        "id": entity.get("id"),
        "name": entity.get("name"),
        "key_facts_count": len(facts["key_facts"])
    }

def enrich_batch9_flagships():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    log_entries = []
    entities = data.get("entities", [])
    for ent in entities:
        eid = ent.get("id")
        if eid in FLAGSHIP_FACTS:
            log_entries.append(_apply_flagship_facts(ent, FLAGSHIP_FACTS[eid]))

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log_entries, f, ensure_ascii=False, indent=2)

    print(f"Batch 9 complete: Enriched {len(log_entries)}/25 flagship heritages.")

if __name__ == "__main__":
    enrich_batch9_flagships()
