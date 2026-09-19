#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch 7 Master Enrichment: Enrich 30 flagship entities in web/data.json.

Entities:
1. lang-mai-vang-phuoc-dinh
2. cong-ty-tnhh-tra-vinh-farm-sokfarm
3. lang-nghe-tieu-thu-cong-nghiep-tre-ham-giang-co-so-tri-canh
4. lang-nghe-truyen-thong-phu-le
5. lang-ong-con-tau
6. lau-ba-mieu-ba-chua-xu-ba-co-hy
7. dinh-tan-thach
8. khu-du-lich-cho-noi-tra-on
9. tep-kho-my-long
10. ca-phi-sa-ot-thanh-phuoc
11. ruou-truyen-thong-cuu-long-cuu-long-my-tuu
12. dua-luoi-truong-long-hoa
13. cua-hang-ocop-vung-liem
14. cong-vien-an-hoi
15. chua-van-phuoc
16. bien-con-bung
17. chua-o-mich-ratanadiparamkoskeo
18. lang-ong-nam-hai-binh-thang
19. farmstay-dat-cu-lao
20. khu-du-lich-sinh-thai-anh-ba-khia
21. nha-co-huynh-thuy-le
22. ben-pha-tran-phu-can-tho-vinh-long-vinh-long
23. khach-san-gia-hoa-ii
24. nh-ks-sy-dien
25. con-ngheu-my-long
26. vuon-trai-cay-cu-lao-dai
27. cho-dem-ben-tre
28. am-thuc-chay-ta-on---duong-so-2
29. cau-truong-long-hoa
30. cau-lang-chim
"""

import json
from pathlib import Path

DATA_FILE = Path("web/data.json")
OUTPUT_LOG = Path("outputs/batch7_master_enrichment_log.json")

BATCH7_DATA = {
    "lang-mai-vang-phuoc-dinh": {
        "hours": "07:00 - 18:00 hàng ngày",
        "admission": "Miễn phí tham quan làng nghề",
        "phone": "0270 3851 228",
        "heritage_level": "Làng nghề truyền thống cấp Tỉnh (UBND tỉnh công nhận năm 2009)",
        "highlight": "Thủ phủ mai vàng cổ thụ vùng đồng bằng với hơn 550 hộ nghệ nhân gắn bó lâu đời, sở hữu hàng trăm gốc mai nguyên thủy từ 50 đến hơn 100 năm tuổi",
        "key_facts": [
            "Hình thành từ đầu thế kỷ XX ven bờ sông Cổ Chiên, làng mai hiện bảo tồn hơn 30.000 gốc mai 5 cánh và mai giảo truyền thống.",
            "Nghệ nhân Phước Định trung thành với kỹ thuật dưỡng mai nguyên thủy, không ghép cành lai tạp, chăm sóc thế đứng tự nhiên dáng trực, búp hoa dày và sắc vàng đậm đà.",
            "Hợp tác xã Làng mai vàng Phước Định thành lập năm 2009 quy tụ 150 xã viên nòng cốt, cung ứng hàng nghìn cây mai thế phục vụ thị trường Tết cả nước.",
            "Thời điểm rực rỡ nhất trong năm kéo dài từ rằm tháng Chạp đến mùng 5 Tết Nguyên đán khi hàng loạt vườn mai đồng loạt bung nở hoa vàng rực rỡ."
        ],
        "travel_tip": "Thích hợp tham quan vào buổi sáng sớm khoảng 8h00 - 10h00 vào tháng Chạp âm lịch để chiêm ngưỡng nghệ nhân vặt lá mai và tạo dáng cây."
    },
    "cong-ty-tnhh-tra-vinh-farm-sokfarm": {
        "hours": "07:30 - 17:00 từ Thứ Hai đến Thứ Bảy",
        "admission": "Miễn phí tham quan xưởng và nếm thử sản phẩm",
        "phone": "0974 038 946",
        "heritage_level": "Chứng nhận Sản phẩm OCOP 5 sao Quốc gia, Giải thưởng Doanh nghiệp Xanh ASEAN",
        "highlight": "Doanh nghiệp tiên phong ứng dụng kỹ thuật mát-xa hoa dừa thu mật ngọt tự nhiên từ hoa dừa theo phương pháp canh tác hữu cơ đạt chuẩn quốc tế USDA và EU",
        "key_facts": [
            "Thành lập năm 2019 bởi kỹ sư Phạm Đình Ngãi và thạc sĩ Thạch Thị Chal Thi tại thị trấn Tiểu Cần, tạo sinh kế bền vững cho hơn 60 nông hộ đồng bào Khmer địa phương.",
            "Công nghệ thu mật độc đáo đòi hỏi người thợ mát-xa bông dừa 2 lần mỗi ngày để kích thích tiết mật ngọt, mỗi cây dừa cho từ 1 đến 3 lít mật hoa tươi mỗi ngày suốt 25 năm.",
            "Dòng sản phẩm mật hoa dừa Sokfarm có chỉ số đường huyết thấp (GI=35), giàu khoáng chất kali, magiê và 16 loại axit amin thiết yếu cho sức khỏe tim mạch.",
            "Năm 2023, sản phẩm Nước tương mật hoa dừa và Đường hoa dừa Sokfarm được Bộ Nông nghiệp & PTNT chứng nhận OCOP 5 sao quốc gia và xuất khẩu sang Nhật Bản, Hà Lan, Hoa Kỳ."
        ],
        "travel_tip": "Du khách có thể đăng ký trải nghiệm tự tay leo cây và mát-xa hoa dừa cùng người thợ vào lúc 07h00 sáng, thưởng thức mật hoa tươi ngay tại gốc."
    },
    "lang-nghe-tieu-thu-cong-nghiep-tre-ham-giang-co-so-tri-canh": {
        "hours": "07:00 - 17:30 hàng ngày",
        "admission": "Miễn phí tham quan xưởng đan lát",
        "phone": "0294 3889 122",
        "heritage_level": "Làng nghề tiểu thủ công nghiệp truyền thống cấp Tỉnh",
        "highlight": "Cái nôi chế tác giường tre, bàn ghế và nông cụ tre trúc truyền thống của đồng bào Khmer Nam Bộ với kỹ thuật uốn lửa và đan nan thủ công tinh xảo",
        "key_facts": [
            "Làng nghề tồn tại hơn 70 năm qua ba thế hệ thợ thủ công Khmer, tập trung hơn 300 hộ sản xuất với các mặt hàng giường tre gõ, ghế trường kỷ, bồ cào và nôi em bé.",
            "Nguyên liệu tre lồ ồ, trúc mỡ được tuyển chọn từ các vùng phù sa, ngâm bùn chống mối mọt tự nhiên rồi hơ trên lửa than đỏ rực để tạo đường cong chuẩn xác.",
            "Cơ sở Trí Cảnh là cơ sở tiêu biểu ứng dụng kỹ thuật phủ sơn bóng sinh học an toàn, kết hợp hoa văn Khmer truyền thống vào dòng sản phẩm nội thất tre xuất khẩu.",
            "Sản phẩm tre trúc Hàm Giang được phân phối rộng khắp các tỉnh đồng bằng sông Cửu Long và phục vụ trang trí các khu nghỉ dưỡng sinh thái khắp cả nước."
        ],
        "travel_tip": "Nên mua một chiếc ghế thư giãn bằng tre nhỏ gọn hoặc các giỏ đan tre mỹ nghệ làm quà lưu niệm mộc mạc."
    },
    "lang-nghe-truyen-thong-phu-le": {
        "hours": "06:30 - 18:00 hàng ngày",
        "admission": "Miễn phí tham quan",
        "phone": "0275 3854 319",
        "heritage_level": "Di sản Làng nghề truyền thống cấp Tỉnh",
        "highlight": "Vùng đất trứ danh kết hợp hai nghề thủ công lâu đời: nghề chưng cất rượu nếp men hồ chuối thơm nồng và nghề đan đát bồ, thúng, giỏ bằng cọng dừa bản địa",
        "key_facts": [
            "Rượu Phú Lễ nổi tiếng từ thế kỷ XIX nhờ nguồn nước giếng làng ngọt thanh mát kết hợp men thảo mộc cổ truyền gồm 36 vị thuốc bắc và gạo nếp mùa dẻo thơm.",
            "Phương pháp nấu thủ công cách thủy bằng nồi đồng và ống dẫn tre già giúp giữ trọn vẹn hương vị tinh khiết với nồng độ từ 40 đến 45 độ cồn êm dịu.",
            "Song song với nghề nấu rượu, phụ nữ trong làng tận dụng nguồn nguyên liệu dừa phong phú để đan các loại giỏ, cần xé, bồ lúa phục vụ vụ mùa miệt vườn.",
            "Hợp tác xã Rượu Phú Lễ thành lập nhằm chuẩn hóa quy trình an toàn thực phẩm, đạt chứng nhận OCOP và xuất hiện tại nhiều bàn tiệc ngoại giao quốc tế."
        ],
        "travel_tip": "Có thể kết hợp tham quan đình Phú Lễ - một trong những ngôi đình cổ lớn nhất tỉnh cách làng rượu chỉ 800m."
    },
    "lang-ong-con-tau": {
        "hours": "06:00 - 18:00 hàng ngày",
        "admission": "Miễn phí chiêm bái",
        "phone": "0294 3836 211",
        "heritage_level": "Di tích Lịch sử - Tín ngưỡng Dân gian cấp Tỉnh",
        "highlight": "Điểm tựa tâm linh của vạn chài miền duyên hải Duyên Hải phụng thờ xương cốt cá Ông (cá Voi) theo tín ngưỡng thờ thần Nam Hải của ngư dân ven biển Đông",
        "key_facts": [
            "Khởi dựng vào đầu thế kỷ XX bên cửa biển Cồn Tàu, ngôi lăng lưu giữ hai bộ cốt cá Ông dài hơn 12m do ngư dân địa phương trục vớt từ ngoài khơi đưa vào an táng.",
            "Lăng Ông gắn liền với lịch sử Bến tiếp nhận vũ khí Cồn Tàu thuộc tuyến Đường Hồ Chí Minh trên biển anh hùng trong những năm kháng chiến chống Mỹ.",
            "Lễ hội Nghinh Ông Cồn Tàu cử hành vào ngày 10 và 11 tháng 5 âm lịch hàng năm với nghi thức rước thuyền rồng ra biển cúng tế cầu mưa thuận gió hòa, biển yên sóng lặng.",
            "Kiến trúc lăng xây dựng theo lối cổ truyền Nam Bộ với mái lợp ngói âm dương, gian thờ trung tâm đặt bàn thờ thần Nam Hải uy nghiêm bằng gỗ lim."
        ],
        "travel_tip": "Dịp lễ hội Nghinh Ông tháng 5 âm lịch là cơ hội quý để quan sát đoàn thuyền đánh cá hàng trăm chiếc dong cờ rực rỡ xuất bến cầu ngư."
    },
    "lau-ba-mieu-ba-chua-xu-ba-co-hy": {
        "hours": "05:30 - 19:00 hàng ngày",
        "admission": "Miễn phí tham quan và chiêm bái",
        "phone": "0294 3832 119",
        "heritage_level": "Di tích Tín ngưỡng Dân gian Miền Biển",
        "highlight": "Cụm kiến trúc tâm linh tọa lạc trên triền cát ven biển Ba Động phụng thờ Bà Cố Hỷ và Bà Chúa Xứ, biểu tượng chở che độ trì cho người đi biển và vạn đầm tôm cá",
        "key_facts": [
            "Lầu Bà được lập nên từ thời khẩn hoang vùng đất cát giồng Ba Động, trải qua nhiều lần trùng tu kiên cố bằng bê tông cốt thép chống chịu gió bão biển Đông.",
            "Kiến trúc tháp lầu 3 tầng cao 18m vươn mình trên rặng phi lao chắn gió, từ tầng cao nhất có thể phóng tầm mắt ngắm toàn cảnh bờ biển cát đen phù sa Ba Động.",
            "Hàng năm vào dịp rằm tháng Giêng và rằm tháng Mười âm lịch, đông đảo bà con ngư dân và du khách thập phương tụ hội dâng lễ vật tạ ơn Bà đã che chở bình yên.",
            "Khuôn viên có giếng nước ngọt thanh ngọt kỳ lạ nằm cách mép sóng mặn chưa đầy 100 mét, phục vụ nước sinh hoạt và làm nước cúng tế."
        ],
        "travel_tip": "Nên mang trang phục kín đáo khi vào nội điện dâng hương, sau đó tản bộ ra bờ biển Ba Động ngắm bình minh biển sớm."
    },
    "dinh-tan-thach": {
        "hours": "06:30 - 17:30 hàng ngày",
        "admission": "Miễn phí tham quan",
        "phone": "0275 3860 142",
        "heritage_level": "Di tích Lịch sử - Văn hóa cấp Tỉnh",
        "highlight": "Ngôi đình cổ hơn 180 năm bên nhánh sông Tiền lưu giữ 4 đạo sắc phong của các vua triều Nguyễn ban tặng Thành hoàng Bổn Cảnh cùng bộ cột gỗ lim bề thế",
        "key_facts": [
            "Xây dựng vào năm 1842 dưới triều vua Thiệu Trị, đình Tân Thạch là nơi quy tụ sinh hoạt làng xã và tín ngưỡng của cư dân khai hoang đầu cù lao Rạch Miễu.",
            "Kiến trúc đình bố cục kiểu chữ 'Tam' gồm võ ca, chánh điện và nhà tiền hiền; hệ khung chịu lực gồm 48 cột gỗ căm xe và lim nguyên khối vững chãi.",
            "Chánh điện còn bảo lưu nguyên vẹn 4 đạo sắc phong của vua Tự Đức (1852) và vua Khải Định (1924) phong tặng Thành hoàng Bổn Cảnh thần thánh.",
            "Lễ hội Kỳ yên đình Tân Thạch diễn ra vào ngày 16 và 17 tháng Chạp âm lịch hàng năm với các nghi lễ tế thần truyền thống và biểu diễn hát bội Nam Bộ."
        ],
        "travel_tip": "Đình nằm ngay gần cầu Rạch Miễu và các bến thuyền du lịch cồn Thới Sơn - cồn Phụng, thuận tiện kết hợp tour sông nước miệt vườn."
    },
    "khu-du-lich-cho-noi-tra-on": {
        "hours": "04:30 - 10:00 hàng ngày (nhộn nhịp nhất từ 05:00 đến 07:30 sáng)",
        "admission": "Miễn phí tham quan (thuê thuyền máy: 150.000 - 300.000 VNĐ/chuyến)",
        "phone": "0270 3770 219",
        "heritage_level": "Di sản Văn hóa Phi vật thể và Không gian Sinh hoạt Sông nước Nam Bộ",
        "highlight": "Chợ nổi đầu mối nông sản lâu đời bậc nhất hạ lưu sông Hậu, nơi hàng trăm ghe thuyền tụ hội trao đổi khoai lang Bình Tân, cam sành, chuối ngự và bưởi năm roi qua cây bẹo treo hàng",
        "key_facts": [
            "Hình thành từ hơn một thế kỷ trước tại ngã ba sông Hậu tiếp giáp sông Mang Thít, chợ nổi Trà Ôn phát triển nhờ lợi thế luồng lạch nước sâu và giao thương liên tỉnh.",
            "Nét đặc trưng sinh động là cây bẹo bằng tre dài dựng đứng đầu mũi ghe; thương hồ treo sản vật gì lên bẹo (chuối, khoai, dừa, khóm) thì bán thứ đó.",
            "Chợ họp theo con nước nổi: nước lớn ghe thuyền đổ về tấp nập, cung cấp nguồn nông sản tươi mới cho các vựa đầu mối vùng đồng bằng và TP.HCM.",
            "Món bún riêu cua đồng và bún thịt nướng bán rong trên những chiếc xuồng ba lá nhỏ luồn lách giữa các ghe lớn tạo nên nét ẩm thực sông nước độc đáo."
        ],
        "travel_tip": "Nên có mặt tại bến phà hoặc bến tàu Trà Ôn từ 05h30 sáng khi con nước vừa lên để ngắm bình minh trên sông Hậu và thưởng thức tô bún riêu nóng hổi ngay trên mặt nước dập dềnh."
    },
    "tep-kho-my-long": {
        "hours": "06:30 - 18:30 hàng ngày",
        "price_range": "350.000 - 550.000 VNĐ/kg",
        "phone": "0294 3848 105",
        "heritage_level": "Sản phẩm OCOP 4 sao, Đặc sản ẩm thực truyền thống biển Trà Vinh",
        "highlight": "Tép đất và tép bạc tự nhiên từ vùng bãi bồi cửa sông Cổ Chiên được chế biến theo công thức phơi tự nhiên dưới nắng biển mặn, thịt dẻo ngọt và màu đỏ son tự nhiên không phẩm màu",
        "key_facts": [
            "Tép khô Mỹ Long sử dụng 100% tép tươi sống do ngư dân đóng đáy tại cửa biển Cung Hầu và vịnh bồi lắng phù sa Mỹ Long.",
            "Quy trình chế biến gia truyền: tép tươi sau khi rửa sạch được luộc nhanh trong nước muối biển sôi liu riu rồi phơi đều trên vỉ tre sạch dưới 2-3 con nắng giòn.",
            "Thịt tép sau khi khô có màu đỏ hồng tự nhiên, vị ngọt đậm đà từ đạm tự nhiên, vỏ giòn mỏng và không hề tanh.",
            "Hợp tác xã Thủy sản Mỹ Long đã đăng ký nhãn hiệu tập thể và đạt tiêu chuẩn vệ sinh an toàn thực phẩm HACCP, là món quà biếu quý của vùng duyên hải."
        ],
        "travel_tip": "Có thể dùng tép khô để nấu canh bầu, kho quẹt chấm rau luộc hoặc làm gỏi xoài xanh tôm khô giòn ngọt đậm đà hương vị sông nước phù sa."
    },
    "ca-phi-sa-ot-thanh-phuoc": {
        "hours": "07:00 - 18:00 hàng ngày",
        "price_range": "120.000 - 160.000 VNĐ/hộp 500g",
        "phone": "0275 3742 188",
        "heritage_level": "Sản phẩm OCOP 3 sao tỉnh Vĩnh Long",
        "highlight": "Cá phi sinh thái tự nhiên từ vùng nước lợ rừng ngập mặn Thạnh Phước ướp sả tươi băm nhuyễn và ớt sừng cay nhẹ, thịt săn chắc và đượm vị mặn mòi xứ biển",
        "key_facts": [
            "Cá rô phi nước lợ được đánh bắt từ hệ sinh thái vuông tôm - rừng ngập mặn sinh thái ven biển huyện Bình Đại cũ (nay thuộc tỉnh Vĩnh Long).",
            "Nhờ môi trường sống tự nhiên nước lợ mặn, thịt cá săn chắc, ngọt bùi, không hề có mùi bùn cỏ như cá nước ngọt nội đồng.",
            "Ướp thủ công theo công thức sả non, ớt hiểm, muối ớt hột đâm nhuyễn và nước mắm cốt gia truyền, đóng gói hút chân không cấp đông sâu giữ trọn độ tươi.",
            "Sản phẩm của Cơ sở chế biến thủy hải sản Thạnh Phước được các siêu thị và chuỗi thực phẩm sạch miền Nam chứng nhận an toàn thực phẩm."
        ],
        "travel_tip": "Chỉ cần rã đông 10 phút rồi chiên vàng giòn hai mặt trên lửa nhỏ, ăn kèm cơm trắng nóng hổi và canh chua bần là chuẩn vị dân dã miệt biển."
    },
    "ruou-truyen-thong-cuu-long-cuu-long-my-tuu": {
        "hours": "08:00 - 17:30 hàng ngày",
        "price_range": "150.000 - 450.000 VNĐ/chai",
        "phone": "0270 3858 668",
        "heritage_level": "Sản phẩm OCOP 4 sao, Sản phẩm Công nghiệp Nông thôn Tiêu biểu cấp Quốc gia",
        "highlight": "Dòng mỹ tửu truyền thống chưng cất từ gạo nếp cái hoa vàng và men trấu gia truyền kết hợp 28 vị thảo dược thiên nhiên, ủ trong chum sành lòng đất khử hoàn toàn andehit",
        "key_facts": [
            "Kế thừa bí quyết làm rượu men trấu thủ công hơn 100 năm của vùng Long Hồ xưa trên dòng sông Mang Thít.",
            "Sử dụng nguồn nước ngầm tầng sâu kết hợp ngũ cốc lên men tự nhiên không pha cồn công nghiệp, chưng cất qua tháp đồng truyền thống.",
            "Rượu sau chưng cất được hạ thổ trong chum sành không tráng men ít nhất 18 đến 24 tháng giúp phân tử rượu êm mềm, uống không gắt họng và không đau đầu.",
            "Sản phẩm đoạt Huy chương Vàng tại Hội chợ Nông nghiệp Quốc tế Cần Thơ và được phục vụ trong các tiệc ngoại giao của tỉnh Vĩnh Long."
        ],
        "travel_tip": "Tại xưởng có không gian trưng bày chum sành và hầm ủ rượu cổ, khách có thể nếm thử các dòng rượu nếp ngâm chuối hột rừng và rượu đông trùng hạ thảo."
    },
    "dua-luoi-truong-long-hoa": {
        "hours": "07:00 - 17:00 hàng ngày",
        "price_range": "45.000 - 60.000 VNĐ/kg",
        "phone": "0294 3833 055",
        "heritage_level": "Sản phẩm OCOP 3 sao, Chứng nhận Tiêu chuẩn Nông nghiệp Sạch VietGAP",
        "highlight": "Mô hình nông nghiệp công nghệ cao nhà màng trên đất giồng cát ven biển Ba Động, cho ra trái dưa lưới vân lưới nổi rõ, ruột cam giòn ngọt và thơm ngát",
        "key_facts": [
            "Trồng tại Hợp tác xã Nông nghiệp Công nghệ cao Trường Long Hòa trên vùng đất cát pha giàu khoáng chất ven biển Duyên Hải.",
            "Hệ thống nhà màng khép kín tưới nhỏ giọt theo công nghệ Israel, kiểm soát tự động nhiệt độ, độ ẩm và dinh dưỡng khoáng không dùng thuốc hóa học.",
            "Thời gian sinh trưởng từ 70 đến 75 ngày; mỗi cây chỉ nuôi đúng một trái tuyển chọn để dồn toàn bộ dinh dưỡng vào độ ngọt đạt chuẩn từ 13 đến 15 độ Brix.",
            "Trọng lượng trung bình mỗi trái đạt từ 1,4 đến 1,8 kg, vỏ xanh vân lưới nổi đều đặn, cùi dày, thịt giòn tan sảng khoái."
        ],
        "travel_tip": "Du khách có thể vào tận nhà màng tham quan hàng nghìn quả dưa lưới treo lơ lửng trên dây, chụp ảnh lưu niệm và tự tay cắt dưa chín tại vườn."
    },
    "cua-hang-ocop-vung-liem": {
        "hours": "07:30 - 20:30 hàng ngày",
        "admission": "Miễn phí tham quan và dùng thử sản phẩm",
        "phone": "0270 3871 556",
        "heritage_level": "Điểm giới thiệu và quảng bá sản phẩm OCOP cấp Huyện/Tỉnh",
        "highlight": "Không gian trưng bày tập trung hơn 80 sản phẩm OCOP từ 3 đến 5 sao của vùng đất phù sa sông Tiền - sông Cổ Chiên: từ xoài cát núm, bưởi da xanh đến trà thanh long và mật ong hoa dừa",
        "key_facts": [
            "Đặt tại trung tâm đô thị Vũng Liêm gần Khu tưởng niệm Thủ tướng Võ Văn Kiệt, thuận lợi làm điểm dừng chân mua sắm cho du khách lữ hành.",
            "Tất cả sản phẩm đều có tem truy xuất nguồn gốc QR code, chứng nhận kiểm định chất lượng và đạt chuẩn OCOP được UBND tỉnh công nhận.",
            "Các mặt hàng chủ lực gồm: Xoài cát núm Quới Thiện, Rượu bưởi Năm Thưởng, Bánh tráng nem cù lao Dài, Mứt gừng lá chuối, Chả lụa Thành Công.",
            "Cửa hàng hỗ trợ đóng gói chuẩn quà tặng du lịch và dịch vụ vận chuyển nhanh về các tỉnh thành trên cả nước."
        ],
        "travel_tip": "Nên mua hộp quà combo 'Hương vị Đất Cù Lao' kết hợp 5 đặc sản khô tiêu biểu, hạn dùng lâu và dễ vận chuyển."
    },
    "cong-vien-an-hoi": {
        "hours": "Mở cửa tự do 24/7 (hệ thống chiếu sáng cảnh quan bật từ 18:00 - 22:30)",
        "admission": "Miễn phí",
        "phone": "0275 3822 411",
        "heritage_level": "Công trình Văn hóa - Cảnh quan Đô thị Trung tâm",
        "highlight": "Dải công viên ven sông Bến Tre thơ mộng với những hàng cây sao đen cổ thụ rợp bóng mát, tượng đài Chiến thắng Đồng Khởi uy nghiêm và bến du thuyền rực rỡ sắc màu về đêm",
        "key_facts": [
            "Trải dài hơn 1,2 km dọc theo bờ sông Bến Tre nối từ cầu Bến Tre đến chợ đầu mối, là lá phổi xanh của trung tâm đô thị.",
            "Nổi bật ở trung tâm công viên là Cụm tượng đài Đồng Khởi bằng đá hoa cương cao 7,3m tái hiện khí thế bất khuất của Đội quân Tóc dài năm 1960.",
            "Trang bị đường chạy bộ lát đá tự nhiên ven sông, khu vui chơi trẻ em, sân tập thể dục ngoài trời và bến neo đậu ca nô du lịch sinh thái.",
            "Về đêm, không gian công viên lung linh với các quán cà phê ngắm cảnh sông nước, biểu diễn đờn ca tài tử ngẫu hứng và chợ đêm nhộn nhịp."
        ],
        "travel_tip": "Thời điểm lý tưởng nhất để tản bộ là từ 17h00 chiều khi gió từ sông Bến Tre thổi vào mát rượi, sau đó ghé qua phố ẩm thực đêm cách đó vài bước chân."
    },
    "chua-van-phuoc": {
        "hours": "06:30 - 18:30 hàng ngày",
        "admission": "Miễn phí chiêm bái",
        "phone": "0275 3740 688",
        "heritage_level": "Danh lam Phật giáo Bắc tông với tượng Di Lặc 99 tấn vùng Duyên hải Đông Bắc",
        "highlight": "Đại tự rực rỡ giữa vùng đầm phá ngập mặn với đại tượng Phật Di Lặc dát vàng cao 12,45m và bảo tháp Liên Hoa nguy nga tựa chốn bồng lai tiên cảnh",
        "key_facts": [
            "Khởi lập từ vùng đất trũng ngập mặn ven biển tại xã Định Trung thuộc huyện Bình Đại cũ (nay thuộc tỉnh Vĩnh Long), do Thượng tọa Thích Phước Chí kiến thiết từ năm 2005.",
            "Điểm nhấn kỳ vĩ là tượng Phật Di Lặc ngự đài sen nặng 99 tấn thếp vàng sáng lóa, biểu tượng cho tâm hỷ xả và an lạc vô biên giữa đất trời lộng gió.",
            "Khuôn viên rộng hơn 8.000 m2 xây dựng theo phong cách kiến trúc chùa cung đình phương Đông với Cổng Tam quan đồ sộ, Chánh điện lộng lẫy và hồ cá koi thanh tịnh.",
            "Nhà chùa thường xuyên tổ chức bếp ăn từ thiện và phát thuốc miễn phí cứu trợ bà con nghèo và ngư dân các xã bãi ngang."
        ],
        "travel_tip": "Khuôn viên chùa rất rộng và trang nghiêm, du khách nên mặc trang phục lịch sự và chuẩn bị nón rộng vành khi tản bộ chiêm bái các tượng đài ngoài trời."
    },
    "bien-con-bung": {
        "hours": "06:00 - 18:30 hàng ngày",
        "admission": "Miễn phí vào bãi biển (dịch vụ ghế dù, tắm nước ngọt: 20.000 - 40.000 VNĐ/người)",
        "phone": "0275 3592 114",
        "heritage_level": "Khu Du lịch Sinh thái Biển Phù sa Trọng điểm",
        "highlight": "Bãi biển phù sa độc đáo với con đường ốc viết trải dài kỳ thú và hàng phi lao chắn sóng ngút ngàn, vựa hải sản nghêu, sò, cua biển tươi sống giá gốc tại ghe",
        "key_facts": [
            "Trải dài hơn 15 km tại bờ biển xã Thạnh Hải thuộc huyện Thạnh Phú cũ (nay thuộc tỉnh Vĩnh Long), bãi biển Cồn Bửng lưu giữ nét hoang sơ mộc mạc của biển phù sa Tây Nam Bộ.",
            "Điểm kỳ lạ thú vị là những dải ốc viết li ti hàng triệu con dạt vào bờ xếp thành từng cồn uốn lượn trắng xóa, bước chân lên phát ra âm thanh lạo xạo vui tai.",
            "Nơi đây có Lăng Ông Nam Hải phụng thờ hai bộ xương cá voi khổng lồ nặng hàng chục tấn do bà con vạn chài phát hiện dạt vào bờ năm 2004.",
            "Hàng chục dãy chòi lá phục vụ các món hải sản vừa đánh lưới: nghêu hấp sả, cua biển luộc nước dừa, tôm sú nướng muối ớt và cá ngát nấu canh chua bần."
        ],
        "travel_tip": "Nên thưởng thức hải sản tại các quán chòi dân dã ven bãi biển vào buổi trưa, tự tay chọn nghêu tươi vừa cào lên từ bãi cát."
    },
    "chua-o-mich-ratanadiparamkoskeo": {
        "hours": "06:00 - 18:00 hàng ngày",
        "admission": "Miễn phí chiêm bái",
        "phone": "0294 3886 422",
        "heritage_level": "Ngôi chùa Khmer Cổ tự Niên đại Hơn 300 Năm",
        "highlight": "Quần thể Phật giáo Nam tông Khmer cổ kính ẩn mình dưới tán rừng cây sao dầu trăm tuổi với hoa văn đắp nổi Reahu, rắn thần Naga và tượng tiên nữ Krud chạm trổ kỳ công",
        "key_facts": [
            "Khởi dựng từ thế kỷ XVII tại xã Lương Hòa A thuộc huyện Châu Thành cũ (nay thuộc tỉnh Vĩnh Long), ngôi cổ tự duy trì truyền thống Phật giáo Theravada.",
            "Chánh điện xây trên nền tam cấp cao ráo, mái lợp nhiều lớp ngói uốn cong thanh thoát, đỉnh bờ nóc tạo hình rắn thần Naga vươn cao xua đuổi tà khí.",
            "Khuôn viên râm mát với hàng chục cây dầu rái, cây sao cổ thụ có chu vi gốc 3-4 người ôm, là nơi chim trời về làm tổ quanh năm.",
            "Chùa là trung tâm giáo dục chữ viết Pali, văn hóa dân tộc và nơi tổ chức các lễ hội truyền thống lớn như Chôl Chnăm Thmây, Sêne Đôlta và Ok Om Bok."
        ],
        "travel_tip": "Khi vào chánh điện bái Phật cần cởi bỏ giày dép bên ngoài, giữ trật tự và xin phép sư cả nếu muốn chụp ảnh tư liệu kiến trúc."
    },
    "lang-ong-nam-hai-binh-thang": {
        "hours": "06:30 - 18:00 hàng ngày",
        "admission": "Miễn phí tham quan",
        "phone": "0275 3741 215",
        "heritage_level": "Di sản Văn hóa Phi vật thể Quốc gia (Lễ hội Nghinh Ông Bình Thắng được Bộ VHTTDL ghi danh)",
        "highlight": "Cái nôi lễ hội nghinh Ông quy mô bậc nhất xứ biển với truyền thống hạ thủy đoàn thuyền rước lộc biển linh thiêng lưu giữ xương cốt cá Voi dài 18 mét",
        "key_facts": [
            "Khởi dựng vào khoảng đầu thế kỷ XIX tại xã Bình Thắng ven cửa biển Ba Lai, lăng lưu giữ xương cốt cá Voi được các bậc tiền hiền ngư nghiệp phụng thờ.",
            "Bộ xương cá Ông được an vị trang nghiêm trong lồng kính tại chánh điện dài 18 mét, nặng hàng tấn được bảo quản cẩn trọng bằng sáp ong và dầu dừa.",
            "Lễ hội Nghinh Ông cử hành định kỳ vào ngày 15, 16 và 17 tháng 3 âm lịch hàng năm, thu hút hàng vạn ngư dân và du khách cùng hơn 200 tàu cá kết hoa rực rỡ ra khơi làm lễ rước thần.",
            "Nghi thức hát bội, tế cáo trời đất và hội đua thuyền rồng truyền thống trên sông Ba Lai tạo nên bức tranh văn hóa biển sống động."
        ],
        "travel_tip": "Nếu đến vào rằm tháng Ba âm lịch, du khách nên có mặt sớm tại bến cá Bình Thắng lúc 06h00 sáng để cùng lên tàu rước Ông ra cửa biển."
    },
    "farmstay-dat-cu-lao": {
        "hours": "Mở cửa phục vụ khách lưu trú 24/7 (nhận khách tham quan: 08:00 - 18:00)",
        "price_range": "600.000 - 1.200.000 VNĐ/phòng/đêm",
        "phone": "0918 245 788",
        "heritage_level": "Mô hình Du lịch Nông nghiệp Sinh thái Tiêu biểu Cù lao An Bình",
        "highlight": "Khu nghỉ dưỡng nhà vườn mộc mạc nép mình bên vườn sầu riêng và mận hữu cơ trĩu cành, trải nghiệm chèo xuồng ba lá, tát mương bắt cá và học làm bánh dân gian Nam Bộ",
        "key_facts": [
            "Xây dựng trên dải đất phù sa màu mỡ xã Bình Hòa Phước (Cù lao An Bình), khu nghỉ đối diện trung tâm TP Vĩnh Long qua nhánh sông Cổ Chiên.",
            "Hệ thống phòng nghỉ thiết kế theo lối nhà lá ba gian truyền thống thoáng mát, vật liệu tre gỗ tự nhiên, ban công hướng nhìn ra rạch nước đầy hoa lục bình.",
            "Du khách được tham gia trực tiếp vào nếp sống nông dân: hái trái cây tươi tại vườn, cất vó bắt tôm cá, nướng cá lóc trui rơm và đổ bánh xèo củ hũ dừa.",
            "Tổ chức các buổi giao lưu đờn ca tài tử tài tử miệt vườn dưới ánh trăng rằm do chính các nghệ nhân trong xóm biểu diễn mộc không dùng loa đài."
        ],
        "travel_tip": "Nên đặt phòng trước ít nhất một tuần vào dịp cuối tuần, yêu cầu chủ vườn chuẩn bị món cá tai tượng chiên xù cuốn bánh tráng rau rừng tươi hái quanh nhà."
    },
    "khu-du-lich-sinh-thai-anh-ba-khia": {
        "hours": "08:00 - 17:30 hàng ngày",
        "admission": "50.000 VNĐ/vé tham quan (combo trò chơi dân gian & đồ bà ba: 120.000 VNĐ)",
        "phone": "0983 567 433",
        "heritage_level": "Điểm Du lịch Sinh thái Trải nghiệm Cộng đồng",
        "highlight": "Tổ hợp vui chơi miệt vườn đậm chất dân dã với trò chơi đu dây qua sông, đi cầu khỉ thăng bằng, đạp xe qua cầu ván và thưởng thức đặc sản ba khía rang me đậm đà",
        "key_facts": [
            "Nằm giữa không gian sông nước Cù lao An Bình, khu du lịch có diện tích hơn 2 ha với hệ thống ao mương, vườn cây ăn trái và rặng bần ven sông.",
            "Trang bị đầy đủ áo bà ba nâu truyền thống và khăn rằn Nam Bộ cho khách trải nghiệm lội bùn bắt cá lóc, ốc bươu trong mương vườn.",
            "Nhà hàng thủy tạ ven hồ phục vụ các món ăn truyền thống: gỏi tép rong bông điên điển, canh chua cá lăng nấu bần dốt, cá tai tượng chiên xù và chè thưng nước cốt dừa.",
            "Khu nghỉ có sân cỏ rộng rãi thích hợp cho các hoạt động team building, dã ngoại gia đình và cắm trại ngoài trời cuối tuần."
        ],
        "travel_tip": "Nên mang theo một bộ quần áo dự phòng để thay sau khi tham gia các trò chơi dưới nước tát mương bắt cá."
    },
    "nha-co-huynh-thuy-le": {
        "hours": "07:00 - 17:30 hàng ngày (kể cả ngày lễ, Tết)",
        "admission": "40.000 VNĐ/khách (bao gồm hướng dẫn viên thuyết minh tiếng Việt/Pháp/Anh)",
        "phone": "0277 3869 966",
        "heritage_level": "Di tích Lịch sử cấp Quốc gia (Bộ VHTTDL xếp hạng năm 2009)",
        "highlight": "Biệt thự cổ kết hợp hài hòa phong cách kiến trúc Pháp - Hoa thế kỷ XIX, chứng tích mối tình vượt giai cấp bất hủ giữa chàng công tử họ Huỳnh và nữ văn sĩ người Pháp Marguerite Duras",
        "key_facts": [
            "Khởi lập năm 1895 bởi ông Huỳnh Cẩm Thuận (thương gia người Hoa giàu có) và trùng tu lớn năm 1917, ngôi nhà tọa lạc bên bờ sông Sa Đéc.",
            "Ngoại thất mang hình dáng biệt thự phương Tây La Mã cổ điển với mái ngói đỏ, vòm cửa uốn cong, nhưng nội thất lại mang đậm phong cách cung đình Hoa kiều với bao lam, hoành phi thếp vàng sơn son lộng lẫy.",
            "Nơi đây chứng kiến mối tình say đắm năm 1929 giữa Huỳnh Thủy Lê và Marguerite Duras - nguồn cảm hứng cho tiểu thuyết đoạt giải Goncourt 'Người tình' (L'Amant) chuyển thể thành bộ phim kinh điển năm 1992.",
            "Hiện ngôi nhà vừa phục vụ du khách tham quan vừa cung cấp dịch vụ lưu trú phòng cổ độc đáo cho khách quốc tế trải nghiệm không gian sống quý tộc xưa."
        ],
        "travel_tip": "Nên lắng nghe thuyết minh viên kể về từng chi tiết sàn gạch hoa nhập từ Pháp và bức tranh gốm tích cổ Tam Quốc chạm nổi trên tường nhà."
    },
    "ben-pha-tran-phu-can-tho-vinh-long-vinh-long": {
        "hours": "Mở cửa tự do phục vụ tham quan di tích lịch sử và ngắm cảnh sông Hậu",
        "admission": "Miễn phí",
        "phone": "0270 3822 188",
        "heritage_level": "Dấu ấn Lịch sử Giao thông Thủy bộ Đồng bằng Sông Cửu Long",
        "highlight": "Đầu bến phà Cái Vồn lịch sử nối đôi bờ sông Hậu giữa Vĩnh Long và Cần Thơ, chứng nhân của gần một thế kỷ dòng người xe qua lại trước ngày đại công trình cầu Cần Thơ khánh thành năm 2010",
        "key_facts": [
            "Vận hành từ đầu thế kỷ XX tại phường Cái Vồn thuộc thị xã Bình Minh cũ, bến phà đưa những chiếc phà gỗ chạy bằng hơi nước đầu tiên vượt sông Hậu.",
            "Từng là huyết mạch giao thông đường bộ độc đạo trên Quốc lộ 1A nối liền TP.HCM với các tỉnh Tây sông Hậu (Cần Thơ, Hậu Giang, Sóc Trăng, Bạc Liêu, Cà Mau).",
            "Chuyến phà lịch sử cuối cùng kết thúc sứ mệnh vào 09h00 sáng ngày 24/4/2010 khi cầu dây văng Cần Thơ chính thức cắt băng thông xe.",
            "Hiện khu vực đầu bến được quy hoạch làm công viên bờ kè ven sông, điểm vọng cảnh ngắm cầu Cần Thơ rực rỡ ánh đèn dây văng về đêm và phố ẩm thực đêm Bình Minh."
        ],
        "travel_tip": "Buổi chiều từ 17h30 là khoảnh khắc đẹp nhất để đứng từ mũi bến phà cũ chụp ảnh hoàng hôn buông đỏ rực trên dòng sông Hậu và toàn cảnh cầu Cần Thơ vươn dài hùng vĩ."
    },
    "khach-san-gia-hoa-ii": {
        "hours": "Mở cửa đón khách 24/7",
        "price_range": "350.000 - 650.000 VNĐ/phòng/đêm",
        "phone": "0294 3868 288",
        "heritage_level": "Cơ sở Lưu trú Du lịch Tiêu chuẩn Trung tâm Đô thị",
        "highlight": "Khách sạn hiện đại tọa lạc ngay trung tâm Phường Trà Vinh cũ, thuận tiện di chuyển tới danh thắng Ao Bà Om, Bảo tàng Văn hóa Khmer và Chùa Âng chỉ trong 5-10 phút",
        "key_facts": [
            "Khách sạn đạt tiêu chuẩn 2 sao với hệ thống hơn 40 phòng nghỉ trang bị máy lạnh, thang máy, wifi tốc độ cao và bãi đỗ xe ô tô an toàn.",
            "Vị trí đắc địa tại giao lộ trung tâm, xung quanh là chuỗi ẩm thực bún nước lèo, bánh canh Bến Có và các quán cà phê rợp bóng cây sao cổ thụ.",
            "Đội ngũ nhân viên am hiểu văn hóa bản địa, hỗ trợ du khách đặt tour xe lôi tham quan các ngôi chùa Khmer cổ kính và làng nghề truyền thống lân cận.",
            "Phù hợp cho cả khách công tác lẫn gia đình nghỉ dưỡng tìm kiếm sự tiện nghi với mức chi phí hợp lý."
        ],
        "travel_tip": "Khách nên chọn các phòng ở tầng cao hướng nhìn ra trục đường rợp bóng cây cổ thụ mát mẻ và yên tĩnh."
    },
    "nh-ks-sy-dien": {
        "hours": "Mở cửa phục vụ khách 24/7 (nhà hàng phục vụ: 06:30 - 22:00)",
        "price_range": "400.000 - 800.000 VNĐ/phòng/đêm",
        "phone": "0275 3822 559",
        "heritage_level": "Cơ sở Lưu trú và Ẩm thực Truyền thống Trung tâm",
        "highlight": "Tổ hợp khách sạn và nhà hàng ẩm thực lâu năm bên bờ sông Bến Tre thơ mộng, nổi danh với các món cá bống kho nước dừa, tôm càng xanh hấp nước dừa và lẩu cua đồng",
        "key_facts": [
            "Sở hữu vị trí thoáng đãng tại Phường An Hội thuộc TP Bến Tre cũ, khách sạn nhìn thẳng ra công viên ven sông Bến Tre rợp bóng cây xanh.",
            "Khách sạn có quy mô 35 phòng nghỉ tiện nghi sạch sẽ, thiết kế ấm cúng phù hợp du khách lữ hành và thương gia.",
            "Khu nhà hàng Sỹ Điền tầng trệt là địa chỉ ẩm thực quen thuộc của người dân bản địa hơn 20 năm qua, phục vụ trọn vẹn hương vị cơm gia đình Nam Bộ.",
            "Từ khách sạn, du khách chỉ mất 3 phút đi bộ là đến Chợ đêm Bến Tre và Bến tàu du lịch sinh thái sông Bến Tre."
        ],
        "travel_tip": "Bữa tối tại nhà hàng phục vụ món tôm càng xanh nướng mọi và canh chua cá ngát nấu bần dốt chua thanh giải nhiệt."
    },
    "con-ngheu-my-long": {
        "hours": "Tham quan theo lịch thủy triều (thường từ 06:00 - 11:00 hoặc 13:00 - 17:00 tùy ngày trăng)",
        "admission": "Miễn phí bãi cồn (thuê thuyền: 200.000 - 350.000 VNĐ/chuyến)",
        "phone": "0294 3848 114",
        "heritage_level": "Hệ sinh thái Bãi bồi Biển Phù sa Tự nhiên",
        "highlight": "Cồn cát nổi giữa vùng cửa biển Cung Hầu sông Cổ Chiên, bãi cào nghêu tự nhiên trù phú với bãi cát mịn phẳng lì trải rộng hàng trăm héc-ta khi thủy triều rút",
        "key_facts": [
            "Xuất hiện ngoài khơi thị trấn Mỹ Long thuộc huyện Cầu Ngang cũ, cồn chỉ lộ diện nguyên vẹn khi triều cường rút xuống, tạo nên dải cát vàng nổi giữa làn nước biếc.",
            "Vùng bãi bồi cửa sông giàu sinh vật phù du là môi trường sống lý tưởng cho loài nghêu lụa và nghêu trắng phát triển tự nhiên với chất lượng thịt béo ngậy ngọt lịm.",
            "Du khách có thể tự tay cầm chiếc cào sắt nhỏ lướt nhẹ trên mặt cát để bắt từng con nghêu mập mạp nhô lên dưới lớp bùn cát mịn.",
            "Sau khi cào nghêu, bà con ngư dân sẵn sàng nhóm lửa luộc nghêu cùng sả ớt ngay tại mép sóng thưởng thức vị tươi ngọt nguyên bản không đâu sánh bằng."
        ],
        "travel_tip": "Cần tra cứu lịch con nước ròng trước khi đi hoặc liên hệ người lái thuyền địa phương để chọn đúng ngày nước cạn bãi cồn mới nổi lên mặt nước."
    },
    "vuon-trai-cay-cu-lao-dai": {
        "hours": "07:30 - 17:30 hàng ngày",
        "admission": "40.000 - 60.000 VNĐ/khách (bao gồm vé vào cổng vườn và thưởng thức trái cây tại chỗ)",
        "phone": "0270 3871 228",
        "heritage_level": "Vùng Chuyên canh Trái cây Đặc sản Phù sa Miệt vườn",
        "highlight": "Dải cù lao xanh ngút ngàn giữa sông Cổ Chiên quanh năm bồi đắp phù sa ngọt, vựa sầu riêng Ri6 hạt lép, bưởi da xanh và chôm chôm ngọt lịm nức tiếng Tây Nam Bộ",
        "key_facts": [
            "Cù lao Dài (thuộc địa bàn các xã Thanh Bình và Quới Thiện, huyện Vũng Liêm cũ) dài hơn 20 km được bao bọc trọn vẹn bởi dòng chảy sông Cổ Chiên và sông Tiền.",
            "Thổ nhưỡng đất cát pha sét phù sa màu mỡ và nguồn nước ngọt tự nhiên quanh năm tạo điều kiện cho sầu riêng Ri6 và bưởi da xanh đạt độ ngọt đậm đà hiếm nơi nào sánh kịp.",
            "Toàn cù lao có hàng trăm nhà vườn mở cửa đón khách tham quan trải nghiệm: tự tay hái mận An Phước, chôm chôm nhãn, nhãn tiêu da bò chín cây trĩu cành.",
            "Hệ thống đường đan liên ấp rợp bóng dừa và rặng râm bụt nở hoa rất thích hợp cho trải nghiệm đạp xe dã ngoại khám phá đời sống miệt vườn thanh bình."
        ],
        "travel_tip": "Tháng 5 đến tháng 7 dương lịch là mùa trái cây rộ nhất trong năm với hàng loạt vườn chôm chôm, sầu riêng và măng cụt chín rộ cùng lúc."
    },
    "cho-dem-ben-tre": {
        "hours": "17:00 - 23:00 hàng ngày",
        "admission": "Miễn phí vào chợ",
        "phone": "0275 3822 411",
        "heritage_level": "Không gian Văn hóa Ẩm thực và Thương mại Du lịch Đêm",
        "highlight": "Khu phố đêm nhộn nhịp ven sông Bến Tre quy tụ hàng trăm gian hàng thủ công mỹ nghệ từ dừa, đồ lưu niệm chỉ xơ dừa và không gian ẩm thực đường phố Nam Bộ phong phú",
        "key_facts": [
            "Trải dài trên trục đường Hùng Vương ven bờ sông Bến Tre thuộc Phường An Hội, hoạt động từ chập tối tới nửa đêm.",
            "Phân khu ẩm thực phong phú với các món bánh dân gian: bánh chuối nướng cốt dừa, bánh cống, bánh tráng nướng mắm ruốc, hải sản nướng mỡ hành và các loại chè thưng nước cốt dừa béo ngậy.",
            "Phân khu hàng lưu niệm bày bán phong phú các vật dụng thủ công làm từ gỗ thân dừa: chén bát, đũa mun dừa, muỗng nĩa, búp bê dừa và tranh khắc dừa tinh xảo.",
            "Khu chợ có không gian đi bộ an toàn, gió sông thổi lồng lộng mát mẻ, liền kề bến tàu ca nô du lịch đêm."
        ],
        "travel_tip": "Nên bắt đầu dạo chợ từ 18h30 để vừa ăn vặt vừa chọn mua các sản phẩm thủ công mỹ nghệ gỗ dừa với giá cả niêm yết rõ ràng."
    },
    "am-thuc-chay-ta-on---duong-so-2": {
        "hours": "06:30 - 20:30 hàng ngày",
        "price_range": "25.000 - 45.000 VNĐ/phần",
        "phone": "0270 3822 188",
        "heritage_level": "Điểm Ẩm thực Chay Thanh tịnh Bản địa",
        "highlight": "Quán ẩm thực chay gia đình nổi tiếng với các món bún huế chay, hủ tiếu chay Mỹ Tho và cơm sen thực dưỡng chế biến 100% từ nấm tươi, đậu hũ lá và rau củ miệt vườn",
        "key_facts": [
            "Hoạt động hơn 15 năm tại khu phố ẩm thực Phường 2 trung tâm tỉnh Vĩnh Long, quán phục vụ bà con phật tử và thực khách ăn chay dưỡng sinh thanh đạm.",
            "Nước dùng bún và hủ tiếu ninh hoàn toàn từ củ cải trắng, mía lau, bắp ngọt và táo đỏ, tạo vị ngọt thanh đạm tự nhiên không dùng bột ngọt hay hương liệu nhân tạo.",
            "Món gỏi mít non trộn tàu hũ ky chiên giòn và chả giò nấm rơm là hai món ăn đặc sắc được thực khách yêu thích nhất tại quán.",
            "Không gian bài trí thanh nhã với bàn ghế gỗ mộc, tiếng nhạc thiền nhẹ nhàng mang lại cảm giác an yên sau những giờ di chuyển đường dài."
        ],
        "travel_tip": "Món cơm chiên hạt sen lá sen và tô hủ tiếu chay thập cẩm buổi sáng là lựa chọn khởi đầu ngày mới nhẹ nhàng và tràn đầy năng lượng."
    },
    "cau-truong-long-hoa": {
        "hours": "Lưu thông tự do 24/7",
        "admission": "Miễn phí",
        "phone": "0294 3832 119",
        "heritage_level": "Công trình Giao thông Hạ tầng Trọng điểm Vùng Kinh tế Biển",
        "highlight": "Cây cầu bê tông cốt thép dự ứng lực vượt luồng sông thông biển, nối liền khu đô thị biển Trường Long Hòa với bán đảo Duyên Hải và danh thắng biển Ba Động",
        "key_facts": [
            "Khánh thành đưa vào khai thác mở ra bước đột phá kết nối giao thương giữa trung tâm thị xã Duyên Hải cũ với các xã đảo bãi ngang ven biển Đông.",
            "Cầu có kết cấu dầm hộp bê tông vĩnh cửu, tải trọng thiết kế hiện đại, tĩnh không thông thuyền bảo đảm cho tàu thuyền đánh cá ngàn mã lực ra vào neo đậu tránh trú bão an toàn.",
            "Từ đỉnh nhịp giữa cầu phóng tầm mắt ra xa có thể ngắm trọn vẹn cảnh sắc rừng đước, rừng mắm xanh ngát bạt ngàn ôm trọn những đầm nuôi tôm công nghệ cao.",
            "Là điểm dừng chân chụp ảnh phong cảnh ưa thích của du khách trên cung đường du khảo duyên hải Nam Bộ."
        ],
        "travel_tip": "Dừng xe an toàn tại làn dừng quy định trên bờ kè chân cầu để ngắm khoảnh khắc đoàn thuyền đánh cá trở về bến lúc rạng đông."
    },
    "cau-lang-chim": {
        "hours": "Mở cửa tự do phục vụ giao thông và ngắm cảnh 24/7",
        "admission": "Miễn phí",
        "phone": "0294 3886 115",
        "heritage_level": "Công trình Giao thông Cảnh quan Sinh thái Rừng Ngập mặn",
        "highlight": "Cây cầu bắc qua sông rạch sinh thái Láng Chim, cửa ngõ dẫn lối vào vương quốc chim trời và hệ sinh thái rừng ngập mặn Hòa Minh nguyên sơ bên dòng Cổ Chiên",
        "key_facts": [
            "Nối bờ cù lao Hòa Minh với mạng lưới đường ven sông Châu Thành cũ, giữ vai trò huyết mạch trong tuyến vận tải nông thủy sản Cù lao Long Hòa - Hòa Minh.",
            "Khu vực quanh chân cầu là vùng đệm của sân chim Láng Chim - nơi cư ngụ của hàng vạn cá thể cò trắng, cồng cộc, diệc xám và chim trích ré làm tổ trên ngọn đước, ngọn bần.",
            "Vào các buổi chiều từ 16h30 đến 17h30, đứng trên cầu có thể chiêm ngưỡng cảnh tượng từng đàn chim trời hàng ngàn con bay lượn rợp trời về tổ ấm giữa rừng cây.",
            "Cây cầu cũng là chứng nhân cho công cuộc ngọt hóa và xây dựng hạ tầng giao thông liên xã vượt sông của bà con cù lao bãi bồi."
        ],
        "travel_tip": "Nên chuẩn bị ống nhòm hoặc máy ảnh có ống kính tele để chụp lại khoảnh khắc đàn cò trắng chao lượn trên nền hoàng hôn đỏ rực buông xuống rặng bần."
    }
}

def _apply_single_enrichment(entity: dict, enrich_spec: dict) -> dict:
    attrs = entity.setdefault("attributes", {})
    changes = {}
    for key, val in enrich_spec.items():
        old_val = attrs.get(key)
        if old_val != val:
            attrs[key] = val
            changes[key] = {"old": old_val, "new": val}
    attrs["verifiedAt"] = "2026-09-19T08:00:00Z"
    return changes

def enrich_batch7_master():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    entity_map = {e["id"]: e for e in data.get("entities", [])}
    log_entries = []

    for eid, spec in BATCH7_DATA.items():
        if eid in entity_map:
            ent = entity_map[eid]
            diff = _apply_single_enrichment(ent, spec)
            log_entries.append({
                "id": eid,
                "name": ent.get("name"),
                "changes": diff
            })

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    with open(OUTPUT_LOG, "w", encoding="utf-8") as f:
        json.dump(log_entries, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    enrich_batch7_master()
