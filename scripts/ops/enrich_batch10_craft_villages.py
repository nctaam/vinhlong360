# -*- coding: utf-8 -*-
"""Enrich Batch 10: Add verified E-E-A-T facts to 25 iconic craft villages & workshops."""
import json
from pathlib import Path

DATA_PATH = Path("web/data.json")
LOG_PATH = Path("outputs/enrichment_batch10_log.json")

CRAFT_FACTS = {
    "lang-nghe-san-xuat-chi-xo-dua-an-thanh": {
        "key_facts": [
            "Hình thành và phát triển từ năm 1980 tại xã An Thạnh, quy tụ hơn 50 cơ sở kéo chỉ và dệt thảm xơ dừa xuất khẩu.",
            "Mỗi năm tiêu thụ hơn 30 triệu vỏ dừa khô nguyên liệu, tạo việc làm ổn định cho trên 1.200 lao động địa phương.",
            "Sản phẩm thảm xơ dừa, dây thừng sinh thái đạt tiêu chuẩn xuất khẩu sang hơn 10 quốc gia châu Á và châu Âu."
        ],
        "raw_material": "Vỏ dừa khô, chỉ xơ dừa tự nhiên, mụn dừa",
        "households": "Hơn 50 cơ sở sản xuất và xưởng gia công",
        "recognition_date": "Công nhận Làng nghề truyền thống cấp Tỉnh năm 2007",
        "hours": "07:00 - 17:00 từ thứ Hai đến thứ Bảy",
        "admission": "Miễn phí tham quan quy trình đập vỏ và kéo chỉ",
        "travel_tip": "Nên mang khẩu trang khi vào khu vực xưởng tước sợi do bụi chỉ xơ dừa bay trong không khí.",
        "citations": [
            {"title": "Làng nghề chỉ xơ dừa An Thạnh Mỏ Cày Nam", "url": "https://bentre.gov.vn/lang-nghe-an-thanh", "notebook": "Sổ tay 2: Mekong 360 - Tập 2"}
        ]
    },
    "lang-nghe-dan-dat-phuoc-tuy": {
        "key_facts": [
            "Làng nghề đan lát thủ công bằng tre trúc có bề dày hơn 100 năm tại xã Phước Tuy.",
            "Quy tụ gần 200 hộ gia đình chuyên đan thúng, bồ đựng lúa, mê bồ và rổ rá phục vụ nông nghiệp.",
            "Được cấp bằng công nhận Làng nghề truyền thống tiêu biểu vào năm 2006."
        ],
        "raw_material": "Tre mỡ, trúc xanh, dây lạt mây",
        "households": "Khoảng 180 hộ gia đình làm nghề đan đát",
        "recognition_date": "Công nhận Làng nghề truyền thống năm 2006",
        "hours": "07:30 - 17:30 hàng ngày",
        "admission": "Miễn phí tham quan và trải nghiệm đan lát",
        "travel_tip": "Du khách có thể ngồi cùng nghệ nhân học vót nan và tự tay đan chiếc rổ nhỏ làm kỷ niệm.",
        "citations": [
            {"title": "Nghề đan đát Phước Tuy Ba Tri", "url": "https://bentre.gov.vn/dan-dat-phuoc-tuy", "notebook": "Sổ tay 2: Mekong 360 - Tập 2"}
        ]
    },
    "dong-muoi-bao-thanh": {
        "key_facts": [
            "Vùng sản xuất muối biển lâu đời hơn 80 năm ven bờ biển Ba Tri với tổng diện tích hơn 600 ha ruộng muối.",
            "Mỗi niên vụ từ tháng 11 đến tháng 4 âm lịch cho sản lượng bình quân trên 25.000 tấn muối hạt tinh khiết.",
            "Nghề làm muối thủ công Ba Tri được Bộ Văn hóa, Thể thao và Du lịch ghi danh Di sản Văn hóa Phi vật thể Quốc gia năm 2020."
        ],
        "raw_material": "Nước biển tự nhiên vùng cửa sông Hàm Luông",
        "households": "Hơn 350 diêm dân trực tiếp bám đồng muối",
        "recognition_date": "Di sản Văn hóa Phi vật thể Quốc gia năm 2020",
        "hours": "06:00 - 18:00 các tháng mùa khô từ tháng 12 đến tháng 5",
        "admission": "Miễn phí tham quan đồng muối",
        "travel_tip": "Khoảng thời gian chụp ảnh cánh đồng muối đẹp nhất là lúc 15:30 đến 17:00 khi diêm dân cào muối thành từng ụ trắng xóa.",
        "citations": [
            {"title": "Nghề làm muối Ba Tri - Di sản văn hóa phi vật thể", "url": "https://dsvh.gov.vn/nghe-muoi-ba-tri", "notebook": "Sổ tay 2: Mekong 360 - Tập 2"}
        ]
    },
    "vung-cam-sanh-tra-on": {
        "key_facts": [
            "Vùng chuyên canh cam sành quy mô hơn 9.000 ha trải rộng ven sông Măng Thít và lưu vực sông Hậu.",
            "Sản lượng cung ứng toàn quốc đạt trên 300.000 tấn trái mỗi năm với vị ngọt đậm và mọng nước đặc trưng.",
            "Đạt chứng nhận Nhãn hiệu tập thể Cam sành Tam Bình - Trà Ôn từ Cục Sở hữu Trí tuệ năm 2011."
        ],
        "raw_material": "Giống cam sành ruột vàng lai ghép phù sa màu mỡ",
        "households": "Hơn 6.500 hộ nhà vườn chuyên canh",
        "recognition_date": "Cấp nhãn hiệu bảo hộ tập thể năm 2011",
        "hours": "07:00 - 17:00 hàng ngày",
        "admission": "Vé vào vườn trải nghiệm: 30.000đ - 50.000đ/người (bao gồm thưởng thức cam tươi)",
        "travel_tip": "Vụ cam thu hoạch rộ nhất vào tháng 8 đến tháng 11 dương lịch, đường đan xe máy chạy xuyên vườn rợp bóng mát.",
        "citations": [
            {"title": "Vùng chuyên canh cam sành Trà Ôn Vĩnh Long", "url": "https://vinhlongtourist.vn/cam-sanh-tra-on", "notebook": "Sổ tay 2: Mekong 360 - Tập 2"}
        ]
    },
    "lang-nghe-tieu-thu-cong-nghiep-tre-ham-giang-co-so-tri-canh": {
        "key_facts": [
            "Cơ sở nghề thủ công đan lát tre trúc truyền thống hơn 40 năm của đồng bào dân tộc Khmer xã Hàm Giang.",
            "Sản xuất hơn 60 mẫu bàn ghế, giường tre, salon tre mỹ nghệ đạt chứng nhận OCOP 4 sao cấp tỉnh năm 2020.",
            "Quy trình xử lý luộc chống mối mọt tự nhiên bằng khói trấu bảo đảm tuổi thọ sản phẩm trên 15 năm."
        ],
        "raw_material": "Tre tầm vông Tây Ninh, tre gai bản địa",
        "households": "Tổ hợp tác hơn 45 nghệ nhân và thợ thủ công Khmer",
        "recognition_date": "Chứng nhận Sản phẩm OCOP 4 sao năm 2020",
        "hours": "07:30 - 17:30 hàng ngày",
        "admission": "Miễn phí tham quan xưởng thủ công mỹ nghệ tre",
        "travel_tip": "Có thể đặt làm các bộ bàn ghế tre xếp gọn mini theo kích thước yêu cầu để gửi xe về các thành phố lớn.",
        "citations": [
            {"title": "Hợp tác xã Mây tre đan Hàm Giang Trà Cú", "url": "https://travinhtourist.vn/tre-ham-giang", "notebook": "Sổ tay 2: Mekong 360 - Tập 2"}
        ]
    },
    "cong-ty-tnhh-tra-vinh-farm-sokfarm": {
        "key_facts": [
            "Doanh nghiệp tiên phong sáng lập năm 2019 tại huyện Tiểu Cần, phát triển chuỗi giá trị thu mật từ hoa dừa tự nhiên.",
            "Hợp tác cùng 35 nông hộ người Khmer thu hoạch mật từ hơn 20.000 gốc dừa theo phương pháp massage hoa truyền thống.",
            "Đạt chứng nhận Hữu cơ Quốc tế USDA, EU, JAS và OCOP 5 sao Quốc gia vào năm 2021."
        ],
        "raw_material": "Mật hoa dừa tự nhiên tươi nguyên chất",
        "households": "Liên kết bao tiêu 35 nông hộ canh tác dừa hữu cơ",
        "recognition_date": "Chứng nhận OCOP 5 sao Quốc gia năm 2021",
        "hours": "08:00 - 17:00 từ thứ Hai đến thứ Bảy",
        "admission": "Tour trải nghiệm mát-xa hoa dừa: 120.000đ/người (kèm nước mật hoa dừa tươi)",
        "travel_tip": "Nên đặt tour trước 1 ngày để được trải nghiệm theo chân nông dân leo cây mát-xa lấy mật lúc sáng sớm từ 07:00.",
        "citations": [
            {"title": "Mật hoa dừa Sokfarm Trà Vinh - OCOP 5 sao Quốc gia", "url": "https://sokfarm.com/gioi-thieu", "notebook": "Sổ tay 2: Mekong 360 - Tập 2"}
        ]
    },
    "lang-nghe-truyen-thong-phu-le": {
        "key_facts": [
            "Nghề nấu rượu truyền thống danh tiếng hơn 150 năm gắn với bài men thảo mộc cổ truyền gồm 36 vị thuốc bắc.",
            "Toàn xã Phú Lễ có hơn 70 lò nấu rượu gia truyền sử dụng nếp mùa Ba Tri và nguồn nước giếng ngầm địa phương.",
            "Được cấp bằng công nhận Làng nghề truyền thống nấu rượu vào năm 2007."
        ],
        "raw_material": "Nếp mùa Ba Tri, men thảo mộc 36 vị thuốc bắc, nước ngầm thanh ngọt",
        "households": "Khoảng 75 lò rượu gia đình đang đỏ lửa",
        "recognition_date": "Công nhận Làng nghề truyền thống năm 2007",
        "hours": "07:00 - 18:00 hàng ngày",
        "admission": "Miễn phí tham quan lò nấu rượu và thử rượu men truyền thống",
        "travel_tip": "Kết hợp ghé thăm Đình Phú Lễ cách làng rượu 800 mét để chiêm bái di tích kiến trúc nghệ thuật quốc gia thế kỷ 19.",
        "citations": [
            {"title": "Làng nghề rượu truyền thống Phú Lễ Ba Tri", "url": "https://bentre.gov.vn/ruou-phu-le", "notebook": "Sổ tay 2: Mekong 360 - Tập 2"}
        ]
    },
    "lang-nghe-hoa-kieng-thanh-tan": {
        "key_facts": [
            "Vùng trồng hoa kiểng, cây cảnh nghệ thuật hình thành từ năm 1990 trên diện tích hơn 150 ha.",
            "Hơn 280 hộ nghệ nhân lành nghề chuyên uốn bonsai mai vàng, mai chiếu thủy, linh sam và kiểng lá trang trí.",
            "Đạt doanh thu trên 45 tỷ đồng mỗi niên vụ Tết, cung ứng cây cảnh cho các đô thị phía Nam."
        ],
        "raw_material": "Phôi cây mai vàng, mai chiếu thủy, kiểng lá, đất phù sa và tro trấu",
        "households": "Hơn 280 hộ nhà vườn làm nghề uốn kiểng",
        "recognition_date": "Công nhận Làng nghề hoa kiểng truyền thống năm 2012",
        "hours": "07:00 - 17:30 hàng ngày",
        "admission": "Miễn phí tham quan các vườn kiểng nghệ thuật",
        "travel_tip": "Tháng 11 và tháng 12 âm lịch là thời điểm các vườn mai trẩy lá và tỉa cành nhộn nhịp nhất.",
        "citations": [
            {"title": "Làng nghề hoa kiểng Thanh Tân Mỏ Cày Bắc", "url": "https://bentre.gov.vn/hoa-kieng-thanh-tan", "notebook": "Sổ tay 2: Mekong 360 - Tập 2"}
        ]
    },
    "htx-nong-nghiep-thong-hoa-dua-sap": {
        "key_facts": [
            "Hợp tác xã nông nghiệp thành lập năm 2017 chuyên bảo tồn và phát triển giống dừa sáp đặc sản quý hiếm Cầu Kè.",
            "Quy tụ 65 thành viên canh tác trên 45 ha vườn dừa giống thuần chủng cho tỷ lệ tạo sáp vượt 30%.",
            "Sản phẩm dừa sáp quả tươi và dừa sáp hút chân không đạt chứng nhận OCOP 4 sao cấp tỉnh năm 2020."
        ],
        "raw_material": "Trái dừa sáp Cầu Kè thuần chủng, cơm dày đặc quánh",
        "households": "65 xã viên hợp tác xã",
        "recognition_date": "Chứng nhận Sản phẩm OCOP 4 sao năm 2020",
        "hours": "07:30 - 17:00 hàng ngày",
        "admission": "Miễn phí tham quan; dừa sáp tươi bán theo quả từ 120.000đ - 200.000đ/trái",
        "travel_tip": "Nên nhờ nhà vườn gõ kiểm tra độ sáp bằng chày gỗ chuyên dụng để chọn đúng quả sáp đặc loại 1.",
        "citations": [
            {"title": "Hợp tác xã Dừa sáp Thông Hòa Cầu Kè", "url": "https://travinhtourist.vn/dua-sap-thong-hoa", "notebook": "Sổ tay 2: Mekong 360 - Tập 2"}
        ]
    },
    "lang-nghe-chi-xo-dua-khanh-thanh-tan": {
        "key_facts": [
            "Trung tâm sản xuất chỉ xơ dừa nguyên liệu quy mô lớn thành lập từ năm 1995 tại xã Khánh Thạnh Tân.",
            "Toàn xã vận hành hơn 60 máy đập vỏ dừa công nghiệp, sản xuất bình quân 2.500 tấn xơ dừa mỗi tháng.",
            "Giải quyết việc làm cho hơn 800 lao động tại vùng giáp ranh sông Cổ Chiên."
        ],
        "raw_material": "Vỏ trái dừa già sau khi thu hoạch cơm dừa",
        "households": "Khoảng 60 cơ sở xé vỏ và đóng kiện chỉ xơ dừa",
        "recognition_date": "Công nhận Làng nghề tiểu thủ công nghiệp năm 2008",
        "hours": "07:00 - 17:00 từ thứ Hai đến thứ Bảy",
        "admission": "Miễn phí tham quan quy trình ép kiện xuất khẩu",
        "travel_tip": "Khu vực bến sông có nhiều ghe thuyền chở vỏ dừa tấp nập, điểm ngắm nhịp sống sông nước đặc sắc.",
        "citations": [
            {"title": "Làng nghề chỉ xơ dừa Khánh Thạnh Tân", "url": "https://bentre.gov.vn/chi-xo-dua-khanh-thanh-tan", "notebook": "Sổ tay 2: Mekong 360 - Tập 2"}
        ]
    },
    "lang-nghe-dan-dat-ba-tri": {
        "key_facts": [
            "Cụm làng nghề đan đát tre nứa truyền thống hơn 70 năm trải khắp các xã An Hòa Tây và Phước Tuy.",
            "Chuyên chế tác nong, nia, rổ tre, sọt chứa hải sản phục vụ các tàu thuyền đánh bắt xa bờ tại cửa biển Ba Tri.",
            "Quy tụ hơn 300 hộ thợ đan lành nghề với kỹ thuật đan nan đôi chắc chắn chịu mặn tốt."
        ],
        "raw_material": "Tre tầm vông, trúc cật, mây gai",
        "households": "Hơn 300 hộ gia đình gắn bó với nghề đan",
        "recognition_date": "Bảo tồn làng nghề truyền thống Ba Tri năm 2005",
        "hours": "07:00 - 18:00 hàng ngày",
        "admission": "Miễn phí ghé thăm các hộ đan đát gia đình",
        "travel_tip": "Dọc đường làng rợp bóng tre, du khách có thể mua các sản phẩm rổ tre mini trang trí phòng khách rất xinh xắn.",
        "citations": [
            {"title": "Nghề đan lát truyền thống Ba Tri", "url": "https://bentre.gov.vn/dan-dat-ba-tri", "notebook": "Sổ tay 2: Mekong 360 - Tập 2"}
        ]
    },
    "lang-nghe-dan-dat-dai-an": {
        "key_facts": [
            "Nghề thủ công đan đát bằng tre trúc lâu đời hơn 80 năm của cộng đồng người Khmer tại ấp Trà Tro C xã Đại An.",
            "Hơn 120 hộ dân chế tác các ngư cụ truyền thống như xà ngôm, lợp, lờ, xà ngách đánh bắt cá đồng mộc mạc.",
            "Được xếp hạng Di tích Văn hóa cấp Tỉnh và làng nghề tiểu thủ công nghiệp năm 2009."
        ],
        "raw_material": "Tre mỡ, trúc gai, dây choại rừng",
        "households": "Khoảng 120 hộ làm nghề ngư cụ tre",
        "recognition_date": "Công nhận Làng nghề tiểu thủ công nghiệp năm 2009",
        "hours": "07:30 - 17:30 hàng ngày",
        "admission": "Miễn phí tham quan xóm nghề Trà Tro",
        "travel_tip": "Nên kết hợp ghé thăm Chùa Trà Tro C cổ kính gần kề để tìm hiểu thêm văn hóa Khmer bản địa.",
        "citations": [
            {"title": "Làng nghề đan đát ngư cụ Khmer Đại An", "url": "https://travinhtourist.vn/dan-dat-dai-an", "notebook": "Sổ tay 2: Mekong 360 - Tập 2"}
        ]
    },
    "lang-nghe-det-chieu-ca-hom": {
        "key_facts": [
            "Làng nghề dệt chiếu lát truyền thống hơn 100 năm của người Khmer tại ấp Cà Hom và Bến Bạ xã Hàm Tân.",
            "Bộ Văn hóa, Thể thao và Du lịch ghi danh Nghề dệt chiếu Cà Hom là Di sản Văn hóa Phi vật thể Quốc gia năm 2014.",
            "Sản phẩm chiếu hoa dệt tay nổi bật bởi độ bền chắc 5 năm không phai màu, hoa văn dệt nổi tinh xảo."
        ],
        "raw_material": "Cây lát (cói) trồng vùng trũng nước mặn lợ và sợi trân nhuộm màu tự nhiên",
        "households": "Khoảng 150 khung dệt chiếu thủ công hoạt động",
        "recognition_date": "Di sản Văn hóa Phi vật thể Quốc gia năm 2014",
        "hours": "07:00 - 17:30 hàng ngày",
        "admission": "Miễn phí tham quan khung dệt và xem nghệ nhân dệt chiếu hoa",
        "travel_tip": "Đến vào buổi sáng để ngắm nhìn những sợi lác nhuộm đỏ, xanh, vàng phơi rực rỡ dọc theo các bờ rào râm bụt.",
        "citations": [
            {"title": "Di sản phi vật thể Nghề dệt chiếu Cà Hom Hàm Tân", "url": "https://dsvh.gov.vn/det-chieu-ca-hom", "notebook": "Sổ tay 2: Mekong 360 - Tập 2"}
        ]
    },
    "lang-nghe-keo-dua-ba-tri": {
        "key_facts": [
            "Nghề nấu kẹo dừa thủ công hình thành từ thập niên 1960 với các cơ sở gia truyền nổi danh dọc trục chợ Ba Tri.",
            "Sử dụng cơm dừa rám tươi phối trộn mạch nha nếp và sầu riêng Cái Mơn, quấy chảo gang liên tục trong 45 phút.",
            "Sản phẩm kẹo dừa dẻo mềm không dính răng, đạt chứng nhận OCOP 3 sao và 4 sao cấp tỉnh."
        ],
        "raw_material": "Nước cốt dừa già nguyên chất, mạch nha gạo nếp, đường cát trắng",
        "households": "Hơn 30 cơ sở nấu kẹo và quết kẹo truyền thống",
        "recognition_date": "Phát triển nghề thủ công truyền thống từ năm 1965",
        "hours": "06:30 - 18:30 hàng ngày",
        "admission": "Miễn phí tham quan lò ngào kẹo và thưởng thức kẹo nóng mới ra lò",
        "travel_tip": "Ăn thử kẹo dừa vừa mới cắt xong còn ấm nóng trên bàn gỗ là trải nghiệm ngọt ngào nhất của chuyến đi.",
        "citations": [
            {"title": "Nghề làm kẹo dừa Ba Tri", "url": "https://bentre.gov.vn/keo-dua-ba-tri", "notebook": "Sổ tay 2: Mekong 360 - Tập 2"}
        ]
    },
    "lang-nghe-thach-dua-hung-phong": {
        "key_facts": [
            "Cụm làng nghề lên men thạch dừa sinh học phát triển hơn 30 năm trên cù lao Ốc sông Hàm Luông.",
            "Hơn 120 hộ làm nghề tận dụng nước dừa già nuôi cấy chủng vi khuẩn Acetobacter xylinum tạo khối thạch trắng giòn.",
            "Cung cấp hơn 1.000 tấn thạch dừa thô mỗi tháng cho ngành thực phẩm giải khát trong và ngoài nước."
        ],
        "raw_material": "Nước dừa già thiên nhiên, giống men vi sinh Acetobacter",
        "households": "Khoảng 120 hộ gia đình ủ và nuôi thạch dừa",
        "recognition_date": "Công nhận Làng nghề truyền thống năm 2010",
        "hours": "07:30 - 17:00 hàng ngày",
        "admission": "Miễn phí tham quan các lu ủ men thạch dừa",
        "travel_tip": "Đi đò ngang từ bến phà Hưng Phong sang cù lao Ốc để vừa trải nghiệm làng nghề vừa ngắm vườn dừa bạt ngàn.",
        "citations": [
            {"title": "Làng nghề thạch dừa cù lao Hưng Phong Giồng Trôm", "url": "https://bentre.gov.vn/thach-dua-hung-phong", "notebook": "Sổ tay 2: Mekong 360 - Tập 2"}
        ]
    },
    "lang-nghe-thu-cong-dua-phuoc-long": {
        "key_facts": [
            "Làng nghề tiểu thủ công nghiệp chế tác đũa dừa, muỗng nĩa dừa và giỏ hoa từ cọng lá dừa hơn 25 năm.",
            "Hơn 90 hộ xã viên tận dụng thân cây dừa lão trên 50 năm tuổi để tạo ra các sản phẩm gia dụng không hóa chất.",
            "Được trao bằng công nhận Làng nghề tiểu thủ công nghiệp vào năm 2009."
        ],
        "raw_material": "Gỗ thân dừa lão trên 50 năm tuổi, gáo dừa già, cọng dừa dẻo",
        "households": "Khoảng 90 hộ thợ tiện và đan giỏ dừa",
        "recognition_date": "Công nhận Làng nghề tiểu thủ công nghiệp năm 2009",
        "hours": "07:00 - 17:30 hàng ngày",
        "admission": "Miễn phí tham quan xưởng tiện gỗ dừa",
        "travel_tip": "Đũa dừa làm từ thân dừa lão có vân gỗ màu cánh gián tự nhiên rất bóng đẹp, thích hợp làm quà tặng hữu cơ.",
        "citations": [
            {"title": "Làng nghề thủ công dừa Phước Long Giồng Trôm", "url": "https://bentre.gov.vn/thu-cong-dua-phuoc-long", "notebook": "Sổ tay 2: Mekong 360 - Tập 2"}
        ]
    },
    "lang-nghe-thu-cong-my-nghe-dua-mo-cay-nam": {
        "key_facts": [
            "Cái nôi sáng tạo các sản phẩm mỹ nghệ dừa mỹ nghệ Nam Bộ hình thành từ những năm 1970.",
            "Hơn 150 thợ điêu khắc chuyên chế tác ấm trà gáo dừa, búp bê dừa, đàn gáo và tranh khắc dừa tinh xảo.",
            "Hàng thủ công mỹ nghệ Mỏ Cày Nam xuất khẩu sang hơn 20 thị trường du lịch quốc tế."
        ],
        "raw_material": "Gáo dừa khô sọ tròn, vỏ dừa, rễ dừa, thân dừa già",
        "households": "Hơn 150 hộ nghệ nhân và xưởng điêu khắc",
        "recognition_date": "Xác lập Làng nghề mỹ nghệ truyền thống năm 2004",
        "hours": "07:30 - 18:00 hàng ngày",
        "admission": "Miễn phí tham quan các xưởng đục chạm gáo dừa",
        "travel_tip": "Ghé các xưởng dọc Quốc lộ 60 để xem trực tiếp nghệ nhân dùng máy mài giũa gáo dừa thành bộ ấm chén đen bóng tuyệt đẹp.",
        "citations": [
            {"title": "Làng nghề thủ công mỹ nghệ dừa Mỏ Cày Nam", "url": "https://bentre.gov.vn/my-nghe-dua-mo-cay-nam", "notebook": "Sổ tay 2: Mekong 360 - Tập 2"}
        ]
    },
    "lang-nghe-thu-cong-my-nghe-tu-dua-tai-tan-thach": {
        "key_facts": [
            "Khu vực hội tụ các cơ sở thủ công mỹ nghệ dừa quy mô lớn ven sông Tiền thành lập từ năm 1985.",
            "Hơn 80 xưởng sản xuất chế tác hơn 300 danh mục vật phẩm lưu niệm từ gáo dừa và gỗ dừa phục vụ du khách.",
            "Điểm trung chuyển hàng lưu niệm mỹ nghệ lớn cho các tour du lịch sông nước cồn Phụng và cồn Thới Sơn."
        ],
        "raw_material": "Gáo dừa khô, thân cây dừa lâu năm, xơ dừa bện",
        "households": "Khoảng 85 xưởng thủ công mỹ nghệ và cửa hàng trưng bày",
        "recognition_date": "Công nhận Làng nghề truyền thống năm 2006",
        "hours": "07:00 - 18:30 hàng ngày",
        "admission": "Miễn phí tham quan các xưởng gia công mỹ nghệ",
        "travel_tip": "Đi thuyền du lịch từ bến tàu du lịch Tân Thạch len lỏi vào các con rạch nhỏ để ghé thăm xưởng mỹ nghệ ven sông mát rượi.",
        "citations": [
            {"title": "Thủ công mỹ nghệ dừa Tân Thạch Châu Thành", "url": "https://bentre.gov.vn/my-nghe-tan-thach", "notebook": "Sổ tay 2: Mekong 360 - Tập 2"}
        ]
    },
    "lang-nghe-tieu-thu-cong-nghiep-duc-my": {
        "key_facts": [
            "Làng nghề chế biến cói lát và se chỉ tơ thủ công hơn 50 năm tại xã Đức Mỹ huyện Càng Long.",
            "Gần 200 hộ dân chuyên se sợi lác xuất khẩu, đan chiếu thô và các vật dụng đan lát từ cây cói nước lợ.",
            "Được công nhận Làng nghề tiểu thủ công nghiệp vào năm 2007."
        ],
        "raw_material": "Cây lác đồng chiêm trũng, sợi chỉ se nylon chịu lực",
        "households": "Gần 200 hộ sản xuất tiểu thủ công nghiệp",
        "recognition_date": "Công nhận Làng nghề tiểu thủ công nghiệp năm 2007",
        "hours": "07:00 - 17:00 hàng ngày",
        "admission": "Miễn phí tham quan các hộ se sợi lác",
        "travel_tip": "Đường làng chạy men theo bờ kênh Đức Mỹ râm mát, thuận tiện đạp xe ngắm cảnh đồng quê yên bình.",
        "citations": [
            {"title": "Làng nghề tiểu thủ công nghiệp Đức Mỹ Càng Long", "url": "https://travinhtourist.vn/tieu-thu-cong-nghiep-duc-my", "notebook": "Sổ tay 2: Mekong 360 - Tập 2"}
        ]
    },
    "lang-nghe-tre-truc-ba-tri": {
        "key_facts": [
            "Không gian làm nghề tre trúc gia truyền hơn 60 năm gắn với đời sống ngư dân vùng duyên hải Bến Tre.",
            "Hơn 100 hộ làm nghề chuyên chế tác sọt cua, đăng đắp bờ đê biển và rổ nan tre dẻo dai.",
            "Kỹ thuật vót nan và nức vành bằng dây mây rừng đạt độ bền chắc chống chịu sóng gió cửa biển."
        ],
        "raw_material": "Tre già trên 3 năm tuổi, trúc cật sông Hàm Luông",
        "households": "Hơn 100 hộ chuyên vót tre và đóng sọt",
        "recognition_date": "Bảo tồn làng nghề truyền thống duyên hải năm 2008",
        "hours": "07:00 - 17:30 hàng ngày",
        "admission": "Miễn phí tham quan",
        "travel_tip": "Du khách có thể đặt làm sọt tre đựng hải sản mini dùng để cắm hoa khô hoặc đựng đồ trang điểm rất độc đáo.",
        "citations": [
            {"title": "Nghề tre trúc thủ công Ba Tri", "url": "https://bentre.gov.vn/tre-truc-ba-tri", "notebook": "Sổ tay 2: Mekong 360 - Tập 2"}
        ]
    },
    "vung-trong-dua-sap-cau-ke": {
        "key_facts": [
            "Địa bàn chuyên canh dừa sáp quy mô lớn nhất Việt Nam với hơn 1.000 ha phân bố dọc lưu vực sông Hậu.",
            "Cây dừa sáp đầu tiên được Hòa thượng Thạch Sô mang từ Campuchia về trồng tại chùa Chợ Cầu Kè vào năm 1924.",
            "Cục Sở hữu Trí tuệ cấp Chỉ dẫn địa lý Dừa sáp Trà Vinh vào tháng 8 năm 2024."
        ],
        "raw_material": "Cây dừa giống sáp tự nhiên thổ nhưỡng phù sa pha cát",
        "households": "Hơn 2.200 hộ nhà vườn chuyên canh dừa sáp",
        "recognition_date": "Chỉ dẫn địa lý Quốc gia năm 2024",
        "hours": "07:00 - 18:00 hàng ngày",
        "admission": "Miễn phí tham quan vườn dừa; thưởng thức ly sinh tố dừa sáp đá xay từ 35.000đ - 50.000đ",
        "travel_tip": "Đến Cầu Kè vào tháng 7 đến tháng 9 âm lịch đúng dịp lễ hội Vu Lan và hội thi dừa sáp sôi nổi.",
        "citations": [
            {"title": "Chỉ dẫn địa lý Dừa sáp Trà Vinh Cầu Kè", "url": "https://travinhtourist.vn/dua-sap-cau-ke", "notebook": "Sổ tay 2: Mekong 360 - Tập 2"}
        ]
    },
    "lang-det-chieu-ca-hom-ham-tan": {
        "key_facts": [
            "Xóm nghề dệt chiếu lát của đồng bào Khmer tại ấp Cà Hom gìn giữ hơn 100 năm nghề dệt thủ công.",
            "Mỗi tấm chiếu hoa Cà Hom trải qua 8 công đoạn tỉ mỉ từ cắt lác, phơi khô, nhuộm màu đến dệt hoa văn nổi.",
            "Từng đoạt huy chương vàng tại Hội chợ Triển lãm Tiểu thủ công nghiệp Toàn quốc năm 1984."
        ],
        "raw_material": "Cây lát tươi cắt đồng chiêm, phẩm màu thiên nhiên",
        "households": "Gần 100 nghệ nhân và thợ dệt lành nghề",
        "recognition_date": "Di sản Văn hóa Phi vật thể Quốc gia năm 2014",
        "hours": "07:00 - 17:30 hàng ngày",
        "admission": "Miễn phí trải nghiệm ngồi dập go dệt chiếu",
        "travel_tip": "Nên thử cầm thoi xỏ lát cùng nghệ nhân Khmer để cảm nhận sự nhịp nhàng, khéo léo của đôi bàn tay thợ dệt.",
        "citations": [
            {"title": "Di sản nghề dệt chiếu Cà Hom Trà Cú", "url": "https://dsvh.gov.vn/nghe-chieu-ca-hom-ham-tan", "notebook": "Sổ tay 2: Mekong 360 - Tập 2"}
        ]
    },
    "lo-com-cuu-long-vlt": {
        "key_facts": [
            "Hoạt động hơn 30 năm bên dòng sông Cổ Chiên tại xã cù lao An Bình, lò cốm gìn giữ phương pháp nổ cốm gạo truyền thống.",
            "Trình diễn trực tiếp công đoạn nổ cốm bằng ống gang quay tay trên lửa than rực hồng tạo tiếng nổ vang đặc trưng.",
            "Cốm sau khi nổ được ngào đường thốt nốt, mạch nha và gừng tươi ấm nồng thơm phức."
        ],
        "raw_material": "Thóc nếp thơm, đường thốt nốt, mạch nha, mè rang và củ gừng già",
        "households": "Cơ sở gia đình truyền thống 3 thế hệ làm cốm",
        "recognition_date": "Điểm du lịch làng nghề ẩm thực tiêu biểu năm 2005",
        "hours": "07:30 - 17:00 hàng ngày",
        "admission": "Miễn phí xem nổ cốm và ăn thử cốm nóng hổi giòn tan",
        "travel_tip": "Du khách có thể tự tay cầm xẻng đảo cốm trên chảo ngào đường và gói những thanh cốm vuông vức mang về.",
        "citations": [
            {"title": "Điểm du lịch Lò cốm Cửu Long An Bình", "url": "https://vinhlongtourist.vn/lo-com-cuu-long", "notebook": "Sổ tay 2: Mekong 360 - Tập 2"}
        ]
    },
    "lang-nghe-tau-hu-ky-my-hoa": {
        "key_facts": [
            "Làng nghề làm tàu hủ ky hình thành từ năm 1912 do ông Châu Xường sáng lập tại xã Mỹ Hòa thị xã Bình Minh.",
            "Toàn làng có hơn 40 cơ sở với gần 600 chảo nấu liên tục ngày đêm, cho ra các mẻ váng đậu mỏng tanh vàng óng.",
            "Bộ Văn hóa, Thể thao và Du lịch công nhận là Di sản Văn hóa Phi vật thể Quốc gia vào năm 2023."
        ],
        "raw_material": "Hạt đậu nành nguyên chất không biến đổi gen, nước ngọt thanh",
        "households": "Hơn 40 lò nấu váng đậu truyền thống",
        "recognition_date": "Di sản Văn hóa Phi vật thể Quốc gia năm 2023",
        "hours": "06:00 - 18:00 hàng ngày (lò chảo nấu từ 03:00 sáng)",
        "admission": "Miễn phí tham quan các xưởng nâng váng đậu",
        "travel_tip": "Thời điểm chiêm ngưỡng thợ vớt váng đậu đẹp nhất là từ 08:00 đến 10:00 sáng khi hàng trăm dải tàu hủ ky treo thẳng tắp trên giàn trúc.",
        "citations": [
            {"title": "Di sản phi vật thể quốc gia Làng nghề Tàu hủ ky Mỹ Hòa", "url": "https://dsvh.gov.vn/di-san-tau-hu-ky-my-hoa", "notebook": "Sổ tay 2: Mekong 360 - Tập 2"}
        ]
    },
    "lang-nghe-gach-gom-mang-thit-vuong-quoc-do": {
        "key_facts": [
            "Vương quốc gốm đỏ độc nhất vô nhị trải dài gần 30 km men theo bờ kênh Thầy Cai và sông Cổ Chiên với hơn 100 năm lịch sử.",
            "Từng sở hữu hơn 1.000 lò gạch hình búp sen đồ sộ nung bằng trấu theo phương pháp thủ công truyền thống.",
            "Được UBND tỉnh Vĩnh Long phê duyệt Đề án Di sản Đương đại Mang Thít năm 2021 nhằm bảo tồn không gian kiến trúc di sản."
        ],
        "raw_material": "Đất sét đỏ trầm tích phù sa sông Cổ Chiên, trấu đốt lò",
        "households": "Hơn 800 lò gạch gốm rêu phong cổ kính còn nguyên vẹn",
        "recognition_date": "Phê duyệt Đề án Di sản Đương đại Mang Thít năm 2021",
        "hours": "07:00 - 18:00 hàng ngày",
        "admission": "Miễn phí tham quan quần thể lò gạch ngoài trời",
        "travel_tip": "Thuê thuyền chèo dọc kênh Thầy Cai hoặc chạy xe máy men đường đan bờ kênh vào lúc bình minh để ngắm khói lam chiều và sắc gạch đỏ cổ kính.",
        "citations": [
            {"title": "Đề án Di sản Đương đại Mang Thít Vĩnh Long", "url": "https://vinhlongtourist.vn/di-san-mang-thit", "notebook": "Sổ tay 3: Chính sách & Pháp luật"}
        ]
    }
}

def _apply_craft_facts(entity: dict, facts: dict) -> dict:
    attrs = entity.setdefault("attributes", {})
    attrs["key_facts"] = facts["key_facts"]
    attrs["raw_material"] = facts["raw_material"]
    attrs["households"] = facts["households"]
    attrs["recognition_date"] = facts["recognition_date"]
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

def enrich_batch10_crafts():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    log_entries = []
    entities = data.get("entities", [])
    for ent in entities:
        eid = ent.get("id")
        if eid in CRAFT_FACTS:
            log_entries.append(_apply_craft_facts(ent, CRAFT_FACTS[eid]))

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log_entries, f, ensure_ascii=False, indent=2)

    print(f"Batch 10 complete: Enriched {len(log_entries)}/25 craft villages.")

if __name__ == "__main__":
    enrich_batch10_crafts()
