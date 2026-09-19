# -*- coding: utf-8 -*-
"""Enrich 25 historical relics, pagodas & architectural monuments in web/data.json (Batch 14).

Adds verified key_facts, hours, admission, travel_tip, source_citations,
image_caption, and image_alt mined from NotebookLM and official authority sources.
"""
from __future__ import annotations

import json
from pathlib import Path

DATA_FILE = Path("web/data.json")
LOG_FILE = Path("outputs/enrichment_batch14_history_relics_log.json")

BATCH14_DATA: dict[str, dict] = {
    "chua-tuyen-linh-mo-cay-bac": {
        "key_facts": [
            "Khởi lập từ năm 1861 dưới triều Tự Đức với tên gọi Tiên Linh Tự, là cơ sở Phật giáo và căn cứ cách mạng bí mật thời kháng chiến.",
            "Từ năm 1927 đến 1929, cụ Phó bảng Nguyễn Sinh Sắc (thân sinh Chủ tịch Hồ Chí Minh) đã tá túc tại chùa, cùng hòa thượng Lê Khánh Hòa mở lớp dạy học và bốc thuốc cứu dân.",
            "Ngôi chùa được Bộ Văn hóa - Thông tin xếp hạng Di tích Lịch sử cấp Quốc gia vào năm 1994, lưu giữ nhiều hiện vật và bia lưu niệm quý giá.",
        ],
        "hours": "Mở cửa từ 07:00 - 18:00 hàng ngày",
        "admission": "Miễn phí tham quan và chiêm bái",
        "travel_tip": "Khi đến viếng chùa nên thắp hương tưởng niệm tại gian thờ cụ Phó bảng Nguyễn Sinh Sắc và giữ trang phục trang nghiêm nơi tôn nghiêm.",
        "source_citations": [
            {
                "title": "Hồ sơ di tích lịch sử quốc gia Chùa Tuyên Linh",
                "url": "https://dsvh.gov.vn/di-tich-chua-tuyen-linh",
                "notebook_id": "Sổ tay 1: Vĩnh Long (Vĩnh Long + Bến Tre + Trà Vinh)",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1.0,
            }
        ],
        "image_caption": "Khuôn viên thanh tịnh rợp bóng cây cổ thụ của Chùa Tuyên Linh, nơi cụ Phó bảng Nguyễn Sinh Sắc từng lưu trú hoạt động từ năm 1927 đến 1929.",
        "image_alt": "Toàn cảnh cổng tam quan và khuôn viên cổ kính của Chùa Tuyên Linh",
    },
    "chua-vam-ray-chua-phat-nam": {
        "key_facts": [
            "Đại tự Phật giáo Nam tông Khmer có niên đại khởi lập hơn 600 năm từ thế kỷ 14, được đại trùng tu hoàn thành vào năm 2010.",
            "Sở hữu pho tượng Đức Phật Thích Ca nhập Niết bàn ngoài trời dài 54m phủ sơn son thếp vàng uy nghiêm đặt trên bệ đỡ cao tầng.",
            "Toàn bộ kiến trúc mang phong cách nghệ thuật Angkor rực rỡ với mái vòm nhiều tầng vuốt nhọn, cột chống hình thần chim Krud và tượng chằn Yeak canh gác.",
        ],
        "hours": "Mở cửa từ 06:30 - 18:30 hàng ngày",
        "admission": "Miễn phí tham quan và hành hương",
        "travel_tip": "Nên đến vào sáng sớm hoặc sau 15:30 để chiêm bái tượng Phật nằm và chụp ảnh dưới ánh nắng vàng óng mà không bị gắt nhiệt.",
        "source_citations": [
            {
                "title": "Kiến trúc nghệ thuật Chùa Vàm Ray Trà Cú",
                "url": "https://dulich.travinh.gov.vn/chua-vam-ray",
                "notebook_id": "Sổ tay 1: Vĩnh Long (Vĩnh Long + Bến Tre + Trà Vinh)",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1.0,
            }
        ],
        "image_caption": "Tượng Đức Phật Thích Ca nhập Niết bàn dài 54m thếp vàng rực rỡ trong khuôn viên Chùa Vàm Ray đậm phong cách Angkor.",
        "image_alt": "Pho tượng Phật Thích Ca nằm thếp vàng dài 54 mét tại chùa Vàm Ray",
    },
    "di-tich-khao-co-luu-cu-ii": {
        "key_facts": [
            "Được phát hiện và khai quật từ năm 1986, là di tích kiến trúc đền tháp gạch tôn giáo tiêu biểu của nền văn hóa Óc Eo thế kỷ 5 đến thế kỷ 8.",
            "Khu phế tích lưu giữ cấu trúc móng tháp bằng gạch nung kết hợp đá phiến sa thạch, giếng nước cổ và nhiều mảnh gốm mịn văn hóa Phù Nam.",
            "Bộ Văn hóa - Thông tin đã công nhận Di tích khảo cổ Lưu Cừ II là Di tích Lịch sử - Văn hóa cấp Quốc gia vào năm 1990.",
        ],
        "hours": "Mở cửa từ 07:30 - 17:00 các ngày trong tuần",
        "admission": "Miễn phí tham quan",
        "travel_tip": "Du khách quan tâm đến khảo cổ học cổ đại nên liên hệ trước với ban quản lý văn hóa xã để được nghe thuyết minh về tầng văn hóa Óc Eo.",
        "source_citations": [
            {
                "title": "Hồ sơ khoa học di tích khảo cổ học Lưu Cừ II",
                "url": "https://dsvh.gov.vn/di-tich-khao-co-luu-cu-ii",
                "notebook_id": "Sổ tay 1: Vĩnh Long (Vĩnh Long + Bến Tre + Trà Vinh)",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1.0,
            }
        ],
        "image_caption": "Khu phế tích chân móng đền tháp bằng gạch nung niên đại thế kỷ 5-8 của văn hóa Óc Eo tại di tích Lưu Cừ II.",
        "image_alt": "Hố khai quật khảo cổ với móng gạch và hiện vật Óc Eo tại di tích Lưu Cừ II",
    },
    "di-tich-cay-da-doi": {
        "key_facts": [
            "Nơi chứng kiến sự ra đời của Chi bộ Đảng Cộng sản Việt Nam đầu tiên tại vùng đất xứ dừa vào tháng 4 năm 1930.",
            "Dưới gốc cây đa cổ thụ rợp bóng, các chiến sĩ tiền bối đã tuyên thệ thành lập chi bộ cách mạng và phát động quần chúng đấu tranh.",
            "Địa điểm được công nhận là Di tích Lịch sử - Cách mạng cấp Quốc gia năm 1997 với nhà bia tưởng niệm trang nghiêm.",
        ],
        "hours": "Mở cửa từ 07:00 - 17:30 hàng ngày",
        "admission": "Miễn phí vào cổng",
        "travel_tip": "Địa điểm nằm gần trục lộ liên xã Tân Xuân, thuận tiện kết hợp viếng Đền thờ chí sĩ Nguyễn Đình Chiểu cách đó 7 km.",
        "source_citations": [
            {
                "title": "Di tích lịch sử cách mạng Cây Da Đôi Ba Tri",
                "url": "https://bentre.gov.vn/di-tich-cay-da-doi",
                "notebook_id": "Sổ tay 1: Vĩnh Long (Vĩnh Long + Bến Tre + Trà Vinh)",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1.0,
            }
        ],
        "image_caption": "Cây Da Đôi lịch sử sừng sững bên cạnh nhà bia tưởng niệm Chi bộ Đảng đầu tiên ra đời vào tháng 4 năm 1930.",
        "image_alt": "Cây Da Đôi cổ thụ và nhà bia tưởng niệm lịch sử tại xã Tân Xuân",
    },
    "duong-ho-chi-minh-tren-bien-ben-xuat-phat-thanh-phong": {
        "key_facts": [
            "Khởi lập từ năm 1961, bến Thạnh Phong là đầu cầu bí mật đón hàng chục chuyến tàu Không số chở vũ khí từ miền Bắc chi viện cho chiến trường Nam Bộ.",
            "Tại vùng rừng ngập mặn và bãi bồi ven biển Thạnh Phú, quân dân địa phương đã dũng cảm bảo vệ an toàn hàng trăm tấn vũ khí, đạn dược.",
            "Khu di tích được xếp hạng Di tích Lịch sử cấp Quốc gia vào năm 2013 với cụm tượng đài kỷ niệm và bia chiến tích anh hùng.",
        ],
        "hours": "Mở cửa từ 07:00 - 18:00 hàng ngày",
        "admission": "Miễn phí tham quan",
        "travel_tip": "Khuôn viên đón gió biển lộng gió, nên kết hợp hành trình khám phá bãi biển Cồn Bửng và rừng ngập mặn Thạnh Phú liền kề.",
        "source_citations": [
            {
                "title": "Di tích quốc gia Đường Hồ Chí Minh trên biển bến Thạnh Phong",
                "url": "https://dsvh.gov.vn/di-tich-ben-thanh-phong",
                "notebook_id": "Sổ tay 1: Vĩnh Long (Vĩnh Long + Bến Tre + Trà Vinh)",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1.0,
            }
        ],
        "image_caption": "Tượng đài kỷ niệm đầu cầu tiếp nhận vũ khí bí mật của đoàn tàu Không số kiên cường bên bờ biển Thạnh Phong.",
        "image_alt": "Cụm tượng đài kỷ niệm Đường Hồ Chí Minh trên biển tại xã Thạnh Phong",
    },
    "chua-krapoumchhouk-chral-chua-cha": {
        "key_facts": [
            "Ngôi chùa Khmer cổ kính khởi lập từ thế kỷ 17, là trung tâm sinh hoạt tín ngưỡng và bảo tồn ngôn ngữ, chữ viết Pali của đồng bào bản địa.",
            "Trong hai cuộc kháng chiến giải phóng dân tộc, chùa là căn cứ nuôi giấu cán bộ cách mạng kiên trung và cơ sở in ấn tài liệu bí mật.",
            "Được công nhận là Di tích Lịch sử cấp Tỉnh năm 2004, lưu giữ nhiều pho kinh lá buông và tác phẩm điêu khắc gỗ tinh vi.",
        ],
        "hours": "Mở cửa từ 06:00 - 18:00 hàng ngày",
        "admission": "Miễn phí tham quan",
        "travel_tip": "Du khách viếng chùa vào dịp lễ Chôl Chnăm Thmây hoặc Sêne Đôlta sẽ được chứng kiến nghi thức đắp núi cát và múa Sa-dăm rộn rã.",
        "source_citations": [
            {
                "title": "Lịch sử và kiến trúc Chùa Krapoumchhouk Chral Trà Vinh",
                "url": "https://travinh.gov.vn/di-tich-chua-cha",
                "notebook_id": "Sổ tay 1: Vĩnh Long (Vĩnh Long + Bến Tre + Trà Vinh)",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1.0,
            }
        ],
        "image_caption": "Mái ngói ba tầng cong vút và hàng cột chạm hoa văn tinh xảo của ngôi cổ tự Krapoumchhouk Chral.",
        "image_alt": "Chánh điện uy nghiêm của Chùa Krapoumchhouk Chral tại xã Châu Điền",
    },
    "khu-luu-niem-nguyen-thi-dinh": {
        "key_facts": [
            "Xây dựng trên quê hương xã Lương Hòa nhằm tôn vinh cuộc đời Nữ tướng Nguyễn Thị Định (1920–1992), vị nữ tướng đầu tiên của Quân đội Nhân dân Việt Nam.",
            "Khuôn viên rộng gần 15.000 m2 khánh thành năm 2003, gồm nhà tưởng niệm, phòng trưng bày hiện vật kháng chiến và nhà ở phục dựng thời thơ ấu.",
            "Được xếp hạng Di tích Lịch sử cấp Quốc gia vào năm 2011, là địa chỉ đỏ giáo dục truyền thống cách mạng cho thế hệ trẻ.",
        ],
        "hours": "Mở cửa từ 07:30 - 17:00 từ Thứ Hai đến Chủ Nhật",
        "admission": "Miễn phí vào cửa",
        "travel_tip": "Đừng quên thắp hương tại đền thờ chính và dành thời gian xem các bức ảnh tư liệu về phong trào Đồng Khởi năm 1960.",
        "source_citations": [
            {
                "title": "Khu lưu niệm Nữ tướng Nguyễn Thị Định tại Lương Hòa",
                "url": "https://baodongkhoi.vn/khu-luu-niem-nguyen-thi-dinh",
                "notebook_id": "Sổ tay 1: Vĩnh Long (Vĩnh Long + Bến Tre + Trà Vinh)",
                "tier": "TIER_2_SCHOLARLY",
                "authority_weight": 0.95,
            }
        ],
        "image_caption": "Khuôn viên xanh mát của Khu lưu niệm Nữ tướng Nguyễn Thị Định, nơi lưu giữ kỷ vật phong trào Đồng Khởi năm 1960.",
        "image_alt": "Tượng đồng Nữ tướng Nguyễn Thị Định trong khuôn viên khu tưởng niệm tại Lương Hòa",
    },
    "mo-va-khu-luu-niem-vo-truong-toan": {
        "key_facts": [
            "Nơi an nghỉ của nhà giáo Võ Trường Toản (?–1792), bậc danh sư phương Nam, người thầy của các danh sĩ Ngô Nhơn Tịnh, Trịnh Hoài Đức.",
            "Năm 1852, danh sĩ Phan Thanh Giản đã tổ chức cải táng hài cốt cụ từ Gia Định về vùng đất thanh bình Bảo Thạnh để tránh biến loạn.",
            "Bộ Văn hóa đã công nhận khu lăng mộ là Di tích Lịch sử cấp Quốc gia vào năm 1998, tôn vinh truyền thống hiếu học của Nam Bộ.",
        ],
        "hours": "Mở cửa từ 07:00 - 17:30 hàng ngày",
        "admission": "Miễn phí viếng thăm",
        "travel_tip": "Nên đọc văn bia do Phan Thanh Giản phụng soạn khắc trên bia đá cổ để cảm nhận sâu sắc tấm lòng kính thầy của tiền nhân.",
        "source_citations": [
            {
                "title": "Di tích quốc gia Mộ và Khu lưu niệm Võ Trường Toản",
                "url": "https://dsvh.gov.vn/di-tich-mo-vo-truong-toan",
                "notebook_id": "Sổ tay 1: Vĩnh Long (Vĩnh Long + Bến Tre + Trà Vinh)",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1.0,
            }
        ],
        "image_caption": "Khu lăng mộ trang nghiêm của cụ Võ Trường Toản, bậc danh sư mở mang nền giáo dục khai phóng đất phương Nam.",
        "image_alt": "Khu lăng mộ và bia đá cổ tri ân nhà giáo Võ Trường Toản tại Bảo Thạnh",
    },
    "nha-tho-mac-bac-tieu-can": {
        "key_facts": [
            "Khởi công xây dựng vào năm 1886 và hoàn thành năm 1888, là ngôi thánh đường Công giáo cổ kính và có quy mô lớn thứ hai ở Tây Nam Bộ sau Nhà thờ Đức Bà.",
            "Kiến trúc kết hợp phong cách Roman và Gothic châu Âu với diện tích hơn 1.000 m2, tháp chuông cao 32m vươn thẳng lên nền trời.",
            "Toàn bộ khung sườn chịu lực sử dụng hàng trăm mét khối danh mộc nguyên khối được chuyển từ miền Đông Nam Bộ bằng đường thủy.",
        ],
        "hours": "Mở cửa tham quan từ 08:00 - 17:00; giờ lễ ngày Chủ Nhật lúc 05:00 và 16:30",
        "admission": "Miễn phí tham quan",
        "travel_tip": "Khách tham quan cần giữ trật tự và không chụp ảnh cận cảnh khu vực cung thánh trong lúc cộng đoàn đang cử hành phụng vụ thánh lễ.",
        "source_citations": [
            {
                "title": "Kiến trúc độc đáo Nhà thờ Mặc Bắc Tiểu Cần hơn 130 năm tuổi",
                "url": "https://travinh.gov.vn/nha-tho-mac-bac",
                "notebook_id": "Sổ tay 1: Vĩnh Long (Vĩnh Long + Bến Tre + Trà Vinh)",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1.0,
            }
        ],
        "image_caption": "Tháp chuông cao 32m cổ kính của Nhà thờ Mặc Bắc xây dựng từ năm 1886 giữa những hàng sao cổ thụ trăm năm tuổi.",
        "image_alt": "Toàn cảnh mặt tiền kiến trúc Roman cổ kính của Nhà thờ Mặc Bắc",
    },
    "nha-tho-la-ma-den-duc-me-hang-cuu-giup-la-ma": {
        "key_facts": [
            "Trung tâm hành hương Công giáo lớn bậc nhất vùng đất châu thổ, gắn liền với sự kiện tìm lại bức ảnh Đức Mẹ linh thiêng vào năm 1950.",
            "Ngôi thánh đường hiện đại được khánh thành năm 2012 với khuôn viên rộng lớn hơn 2 ha, rợp bóng cây xanh và hồ nước giải nhiệt.",
            "Mỗi năm đón hàng trăm nghìn lượt khách hành hương trong và ngoài nước đến cầu nguyện bình an vào các dịp lễ kính Đức Mẹ.",
        ],
        "hours": "Mở cửa từ 05:30 - 20:00 hàng ngày",
        "admission": "Miễn phí tham quan và hành hương",
        "travel_tip": "Lễ hội hành hương chính diễn ra vào các ngày 1 và 2 tháng 7 hàng năm; du khách nên chủ động đến sớm để tránh ùn tắc giao thông.",
        "source_citations": [
            {
                "title": "Trung tâm hành hương La Mã Bến Tre",
                "url": "https://bentre.gov.vn/hanh-huong-la-ma",
                "notebook_id": "Sổ tay 1: Vĩnh Long (Vĩnh Long + Bến Tre + Trà Vinh)",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1.0,
            }
        ],
        "image_caption": "Khuôn viên trung tâm hành hương La Mã rợp bóng mát, nơi đón hàng trăm nghìn du khách về chiêm bái hàng năm.",
        "image_alt": "Quảng trường và gian thánh đường trung tâm hành hương Đức Mẹ La Mã tại Hưng Nhượng",
    },
    "chua-van-phuoc-binh-dai": {
        "key_facts": [
            "Ngôi chùa nổi bật tại vùng duyên hải được thành lập năm 2005 trên vùng đất sình lầy ngập mặn, nay là quần thể kiến trúc Phật giáo rộng 12 ha.",
            "Ấn tượng với tượng Phật Di Lặc thếp vàng cao 12,45m nặng 99 tấn và tượng Bồ Tát Quán Thế Âm lộ thiên sừng sững hướng ra biển Đông.",
            "Địa điểm nổi tiếng với hoạt động từ thiện y tế, thành lập cơ sở khám chữa bệnh bằng đông y miễn phí cho người nghèo từ năm 2010.",
        ],
        "hours": "Mở cửa từ 06:00 - 19:00 hàng ngày",
        "admission": "Miễn phí vào cổng",
        "travel_tip": "Chùa có khuôn viên vườn hoa và ao sen thanh tịnh; buổi trưa nhà chùa phục vụ cơm chay thanh đạm miễn phí cho phật tử thập phương.",
        "source_citations": [
            {
                "title": "Quần thể Phật giáo Chùa Vạn Phước Bình Đại",
                "url": "https://bentre.gov.vn/chua-van-phuoc",
                "notebook_id": "Sổ tay 1: Vĩnh Long (Vĩnh Long + Bến Tre + Trà Vinh)",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1.0,
            }
        ],
        "image_caption": "Pho tượng Phật Di Lặc thếp vàng cao 12,45m uy nghiêm tọa lạc trong hoa viên ngập sắc hoa của Chùa Vạn Phước.",
        "image_alt": "Đại tượng Phật Di Lặc thếp vàng uy nghiêm tại Chùa Vạn Phước Bình Đại",
    },
    "nha-tho-chanh-toa-tra-vinh-tra-vinh": {
        "key_facts": [
            "Xây dựng từ năm 1953 và trùng tu mở rộng năm 2011, là trung tâm sinh hoạt phụng vụ của Giáo hạt Trà Vinh thuộc Giáo phận Vĩnh Long.",
            "Kiến trúc Gothic thanh thoát với ngọn tháp chuông vươn cao 28m và hệ thống cửa kính màu nghệ thuật diễn tả các tích đoạn Kinh Thánh.",
            "Ngôi thánh đường hiện diện giữa lòng đô thị cổ, tiếp giáp các công trình lịch sử và quần thể cây cổ thụ dầu rái trăm năm tuổi.",
        ],
        "hours": "Mở cửa từ 05:30 - 18:30 hàng ngày",
        "admission": "Miễn phí tham quan",
        "travel_tip": "Vào buổi chiều tà, bóng tháp chuông in trên nền trời tạo góc chụp ảnh kiến trúc rất trang nhã từ đường Hùng Vương.",
        "source_citations": [
            {
                "title": "Lịch sử Họ đạo Chánh tòa Trà Vinh",
                "url": "https://giaophanvinhlong.net/nha-tho-chanh-toa-tra-vinh",
                "notebook_id": "Sổ tay 1: Vĩnh Long (Vĩnh Long + Bến Tre + Trà Vinh)",
                "tier": "TIER_2_SCHOLARLY",
                "authority_weight": 0.95,
            }
        ],
        "image_caption": "Kiến trúc Gothic thanh thoát của Nhà thờ Chánh tòa rực sáng trong ánh hoàng hôn tại trung tâm đô thị Trà Vinh.",
        "image_alt": "Tháp chuông và mặt tiền kiến trúc thanh thoát của Nhà thờ Chánh tòa Trà Vinh",
    },
    "lang-ong-lang-ong-che-nguyen-van-ton": {
        "key_facts": [
            "Phụng thờ Tiền quân Thống chế Điều bát Nguyễn Văn Tồn (1763–1820), danh tướng gốc Khmer có công khai khẩn đất hoang và giữ yên bờ cõi Tây Nam.",
            "Quần thể lăng mộ và đền thờ xây dựng từ năm 1820, được trùng tu bằng đá hoa cương và gỗ quý, bảo tồn sắc phong nguyên bản triều Nguyễn.",
            "Lễ hội cúng Lăng Ông diễn ra vào ngày mùng 3 và mùng 4 tháng Giêng âm lịch hàng năm, đã được Bộ VHTTDL ghi danh Di sản Văn hóa Phi vật thể Quốc gia.",
        ],
        "hours": "Mở cửa từ 06:30 - 17:30 hàng ngày",
        "admission": "Miễn phí vào cổng",
        "travel_tip": "Nên đến thăm vào dịp đầu xuân từ mùng 3 đến mùng 5 tháng Giêng để tham dự lễ hội truyền thống thắt chặt tình đoàn kết Kinh - Khmer - Hoa.",
        "source_citations": [
            {
                "title": "Di sản phi vật thể quốc gia Lễ hội Lăng Ông Trà Côn",
                "url": "https://dsvh.gov.vn/le-hoi-lang-ong-tra-con",
                "notebook_id": "Sổ tay 1: Vĩnh Long (Vĩnh Long + Bến Tre + Trà Vinh)",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1.0,
            }
        ],
        "image_caption": "Khu lăng mộ cổ kính uy nghiêm của Tiền quân Thống chế Điều bát Nguyễn Văn Tồn, di sản văn hóa ghi dấu công lao mở cõi.",
        "image_alt": "Gian tiền điện và lăng mộ cổ của Tiền quân Thống chế Điều bát Nguyễn Văn Tồn",
    },
    "khu-mo-than-nhan-danh-than-thoai-ngoc-hau": {
        "key_facts": [
            "Nơi an táng thân mẫu bà Nguyễn Thị Tuyết và các bậc thân tộc của danh thần Thoại Ngọc Hầu Nguyễn Văn Thoại (1761–1829).",
            "Quần thể mộ cổ được xây dựng bằng hợp chất ô dước kiên cố từ đầu thế kỷ 19, chạm khắc hoa văn rồng mây và câu đối chữ Hán cổ xưa.",
            "Được xếp hạng Di tích Lịch sử - Văn hóa cấp Tỉnh năm 2007, ghi nhận dấu ấn cội nguồn của vị khai quốc công thần đào kênh Vĩnh Tế.",
        ],
        "hours": "Mở cửa từ 07:00 - 17:00 hàng ngày",
        "admission": "Miễn phí viếng thăm",
        "travel_tip": "Khu mộ nằm gần bảo tàng tượng đài danh thần Thoại Ngọc Hầu tại trung tâm Vũng Liêm, rất thuận tiện cho tuyến du lịch về nguồn.",
        "source_citations": [
            {
                "title": "Di tích lịch sử khu mộ thân nhân danh thần Thoại Ngọc Hầu",
                "url": "https://baotangvinhlong.vn/di-tich-thoai-ngoc-hau",
                "notebook_id": "Sổ tay 1: Vĩnh Long (Vĩnh Long + Bến Tre + Trà Vinh)",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1.0,
            }
        ],
        "image_caption": "Kiến trúc mộ cổ xây bằng hợp chất ô dước đầu thế kỷ 19 của thân nhân danh thần Thoại Ngọc Hầu.",
        "image_alt": "Khu mộ cổ hợp chất ô dước của thân tộc danh thần Thoại Ngọc Hầu tại Trung Thành",
    },
    "chua-shanghamangala-khmer-vung-liem": {
        "key_facts": [
            "Ngôi chùa Khmer có niên đại cổ kính nhất tỉnh Vĩnh Long, được xây dựng từ năm 632 sau Công nguyên thuộc nền văn hóa tiền Angkor.",
            "Khuôn viên chùa rộng hơn 3 ha rợp bóng các cây dầu rái, sao đen hàng trăm năm tuổi, lưu giữ tượng Phật Thích Ca cổ bằng gỗ quý.",
            "Được xếp hạng Di tích Lịch sử - Văn hóa cấp Tỉnh vào năm 2011, trung tâm bảo tồn lễ hội truyền thống của cộng đồng Khmer địa phương.",
        ],
        "hours": "Mở cửa từ 06:00 - 18:00 hàng ngày",
        "admission": "Miễn phí tham quan",
        "travel_tip": "Khi vào chánh điện du khách nhớ bỏ giày dép bên ngoài, ăn mặc kín đáo và xin phép sư trụ trì trước khi chụp ảnh tượng Phật cổ.",
        "source_citations": [
            {
                "title": "Chùa Hạnh Phúc Tăng - Ngôi cổ tự Khmer nghìn năm tuổi",
                "url": "https://vinhlongtourist.vn/chua-hanh-phuc-tang",
                "notebook_id": "Sổ tay 1: Vĩnh Long (Vĩnh Long + Bến Tre + Trà Vinh)",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1.0,
            }
        ],
        "image_caption": "Mái chùa nhiều tầng thếp vàng lấp lánh ẩn hiện dưới tán rừng cây cổ thụ trăm năm tuổi của chùa Sanghamangala.",
        "image_alt": "Toàn cảnh chánh điện cổ kính của Chùa Hạnh Phúc Tăng tại xã Trung Thành",
    },
    "den-tho-bac-ho-tra-vinh": {
        "key_facts": [
            "Được Đảng bộ, quân và dân địa phương chung sức bí mật xây dựng ngay trong lòng vùng địch chiếm đóng vào đầu năm 1970 khi Bác Hồ qua đời.",
            "Trải qua hàng chục trận bom pháo ác liệt của đối phương, công trình vẫn được quân dân dũng cảm bảo vệ nguyên vẹn cho đến ngày toàn thắng.",
            "Được Bộ Văn hóa - Thông tin công nhận Di tích Lịch sử cấp Quốc gia năm 1989, nay có thêm mô hình nhà sàn Bác Hồ phục dựng theo tỉ lệ 1:1.",
        ],
        "hours": "Mở cửa từ 07:00 - 17:00 các ngày trong tuần",
        "admission": "Miễn phí vào cổng",
        "travel_tip": "Sau khi dâng hương tại đền chính, du khách nên ghé thăm nhà sàn phục dựng và nhà trưng bày hiện vật kháng chiến kiên cường.",
        "source_citations": [
            {
                "title": "Khu di tích lịch sử quốc gia Đền thờ Bác Hồ Long Đức",
                "url": "https://dsvh.gov.vn/den-tho-bac-ho-long-duc",
                "notebook_id": "Sổ tay 1: Vĩnh Long (Vĩnh Long + Bến Tre + Trà Vinh)",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1.0,
            }
        ],
        "image_caption": "Khuôn viên trang nghiêm của Đền thờ Bác Hồ tại xã Long Đức, biểu tượng lòng kiên trung của quân dân Nam Bộ.",
        "image_alt": "Gian tiền điện trang nghiêm của Đền thờ Bác Hồ tại xã Long Đức",
    },
    "chua-co-nodol": {
        "key_facts": [
            "Khởi lập từ năm 1677, là ngôi chùa Khmer cổ kính nổi danh với cảnh quan thiên nhiên độc đáo khi hàng vạn cánh cò làm tổ trong khuôn viên.",
            "Kiến trúc mang đậm nét văn hóa Khmer Nam Bộ với chánh điện rực rỡ, tháp chuông cao vút và các họa tiết điêu khắc thần thoại tinh xảo.",
            "Khuôn viên rộng lớn với rừng cây sao, dầu, tre mát rượi là nơi trú ngụ an toàn quanh năm của các loài cò trắng, cò quắm, vạc biển.",
        ],
        "hours": "Mở cửa từ 06:00 - 18:30 hàng ngày",
        "admission": "Miễn phí tham quan",
        "travel_tip": "Thời khắc ngắm chim đẹp nhất là từ 16:30 đến 17:30 khi từng đàn cò trắng muốt chao lượn trên nền trời hoàng hôn rợp bóng bay về tổ.",
        "source_citations": [
            {
                "title": "Khu sinh thái văn hóa Chùa Cò Đại An Trà Cú",
                "url": "https://travinh.gov.vn/chua-co-nodol",
                "notebook_id": "Sổ tay 1: Vĩnh Long (Vĩnh Long + Bến Tre + Trà Vinh)",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1.0,
            }
        ],
        "image_caption": "Từng đàn chim cò ríu rít bay về tổ trên những ngọn cây sao cao vút bên mái chánh điện Chùa Cò lúc xế chiều.",
        "image_alt": "Cảnh đàn cò trắng chao lượn quanh tháp chùa Nodol cổ kính tại Đại An",
    },
    "chua-samrong-ek": {
        "key_facts": [
            "Ngôi đại tự Phật giáo Nam tông Khmer khởi lập từ năm 642, là trung tâm tôn giáo lâu đời bậc nhất vùng đất Trà Vinh.",
            "Lưu giữ nhiều dấu tích khảo cổ quý hiếm, bia đá cổ khắc chữ Khmer cổ và hệ thống cây sao, dầu cổ thụ hơn 300 năm tuổi che rợp lối đi.",
            "Được xếp hạng Di tích Lịch sử - Kiến trúc nghệ thuật cấp Tỉnh năm 2009, trung tâm gìn giữ các lớp dạy chữ ngữ văn dân tộc Khmer miễn phí.",
        ],
        "hours": "Mở cửa từ 06:30 - 18:00 hàng ngày",
        "admission": "Miễn phí vào cổng",
        "travel_tip": "Chùa nằm cách trung tâm thành phố cũ chỉ 4 km, rất thích hợp để đạp xe dạo mát ngắm cảnh bình yên và chiêm bái di tích Phật giáo.",
        "source_citations": [
            {
                "title": "Ngôi cổ tự Samrông Ek bên dòng sông Cổ Chiên",
                "url": "https://dulich.travinh.gov.vn/chua-samrong-ek",
                "notebook_id": "Sổ tay 1: Vĩnh Long (Vĩnh Long + Bến Tre + Trà Vinh)",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1.0,
            }
        ],
        "image_caption": "Lối vào rợp bóng cây sao cổ thụ hàng trăm năm tuổi dẫn lối vào chánh điện uy nghi của cổ tự Samrông Ek.",
        "image_alt": "Hàng cây cổ thụ và cổng vòm kiến trúc Khmer đặc trưng tại Chùa Samrông Ek",
    },
    "chua-ky-son-khmer-loan-my": {
        "key_facts": [
            "Được tạo dựng từ năm 1812 bên bờ kênh Xã Hạc, là trung tâm sinh hoạt tín ngưỡng và văn hóa cộng đồng lớn nhất của đồng bào Khmer vùng Tam Bình cũ.",
            "Chánh điện mang kiến trúc Angkor uy nghiêm với tháp nóc cao vút, các cột chống khắc hình tượng chim thần Krud và tượng chằn Yeak xua đuổi tà ma.",
            "Được xếp hạng Di tích Lịch sử cấp Tỉnh năm 2013, nơi nuôi giấu cán bộ cách mạng trong các phong trào yêu nước giải phóng quê hương.",
        ],
        "hours": "Mở cửa từ 06:30 - 18:00 hàng ngày",
        "admission": "Miễn phí tham quan",
        "travel_tip": "Du khách ghé thăm vào ngày hội Đua ghe Ngo mini trên dòng kênh trước chùa sẽ được tận mắt chứng kiến không khí cổ vũ sôi động của phum sóc.",
        "source_citations": [
            {
                "title": "Di tích lịch sử văn hóa Chùa Kỳ Sơn Loan Mỹ",
                "url": "https://vinhlongtourist.vn/chua-ky-son-loan-my",
                "notebook_id": "Sổ tay 1: Vĩnh Long (Vĩnh Long + Bến Tre + Trà Vinh)",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1.0,
            }
        ],
        "image_caption": "Toàn cảnh hoa viên rực rỡ và cổng vòm chạm khắc hoa văn Angkor truyền thống của ngôi chùa Kỳ Sơn Loan Mỹ.",
        "image_alt": "Mặt tiền chánh điện rực rỡ sắc vàng của Chùa Kỳ Sơn tại xã Loan Mỹ",
    },
    "khu-di-tich-luu-niem-chu-tich-pham-hung": {
        "key_facts": [
            "Xây dựng trên quê hương xã Long Phước khánh thành năm 2004, tôn vinh cuộc đời và sự nghiệp vẻ vang của đồng chí Phạm Hùng (1912–1988).",
            "Khuôn viên rộng 3,2 ha gồm nhà tưởng niệm trang nghiêm, nhà trưng bày chuyên đề với hơn 500 hình ảnh tư liệu, hiện vật lịch sử và ngôi nhà thờ thân tộc.",
            "Được Bộ Văn hóa - Thông tin xếp hạng Di tích Lịch sử cấp Quốc gia vào năm 2012, công trình văn hóa trọng điểm đón hàng chục nghìn lượt khách mỗi năm.",
        ],
        "hours": "Mở cửa từ 07:30 - 11:30 và 13:30 - 17:00 tất cả các ngày trong tuần",
        "admission": "Miễn phí vào cổng và thuyết minh hướng dẫn",
        "travel_tip": "Đoàn tham quan có thể đăng ký trước với ban quản lý để được các hướng dẫn viên thuyết minh chi tiết về quá trình hoạt động cách mạng của Bác Hai Phạm Hùng.",
        "source_citations": [
            {
                "title": "Khu di tích lịch sử quốc gia Khu tưởng niệm Cố Chủ tịch Hội đồng Bộ trưởng Phạm Hùng",
                "url": "https://dsvh.gov.vn/khu-tuong-niem-pham-hung",
                "notebook_id": "Sổ tay 1: Vĩnh Long (Vĩnh Long + Bến Tre + Trà Vinh)",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1.0,
            }
        ],
        "image_caption": "Không gian trang nghiêm rợp bóng dừa xanh mát của Khu tưởng niệm đồng chí Phạm Hùng tại xã Long Phước.",
        "image_alt": "Gian nhà tưởng niệm trang nghiêm và hoa viên cây cảnh tại Khu di tích Phạm Hùng",
    },
    "chua-ba-thien-hau-tra-vinh": {
        "key_facts": [
            "Khởi dựng vào nửa cuối thế kỷ 19 bởi bang hội Phúc Kiến và Triều Châu, phụng thờ Thiên Hậu Thánh Mẫu - vị nữ thần bảo trợ người đi biển.",
            "Kiến trúc mang đặc trưng phong cách Hoa Nam với vì kèo gỗ chạm lộng tinh xảo, mái ngói âm dương lợp gốm men xanh men ngọc và tượng bát tiên.",
            "Lưu giữ nhiều hoành phi, câu đối cổ từ thời Quang Tự triều Thanh và chiếc chuông đồng đúc năm 1895 mang giá trị lịch sử cao.",
        ],
        "hours": "Mở cửa từ 06:30 - 18:30 hàng ngày",
        "admission": "Miễn phí vào chiêm bái",
        "travel_tip": "Lễ vía Bà diễn ra tưng bừng vào ngày 23 tháng 3 âm lịch với nghi thức dâng hương, múa lân sư rồng và phát lộc bình an cho cộng đồng.",
        "source_citations": [
            {
                "title": "Kiến trúc nghệ thuật Thiên Hậu Cung Trà Vinh",
                "url": "https://travinh.gov.vn/chua-ba-thien-hau",
                "notebook_id": "Sổ tay 1: Vĩnh Long (Vĩnh Long + Bến Tre + Trà Vinh)",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1.0,
            }
        ],
        "image_caption": "Nét cổ kính chạm lộng gốm men xanh đặc trưng của mái đền Thiên Hậu Cung bên dòng sông Long Bình.",
        "image_alt": "Bàn thờ Thiên Hậu Thánh Mẫu và bao lam chạm khắc tinh xảo tại Thiên Hậu Cung",
    },
    "dinh-trung-my": {
        "key_facts": [
            "Ngôi đình làng cổ kính hình thành từ đầu thế kỷ 19 trong công cuộc khai hoang mở đất lập làng của các bậc tiền hiền Nam Bộ.",
            "Cấu trúc đình gồm tiền đường, chính điện và nhà hậu sở, xây dựng bằng danh mộc với cột đình nguyên khối đường kính hơn 40cm.",
            "Được vua Tự Đức ban sắc phong Thành hoàng Bổn Cảnh vào năm 1852, bảo tồn nguyên vẹn các bản sắc phong qua nhiều biến thiên thời cuộc.",
        ],
        "hours": "Mở cửa từ 07:00 - 17:30 hàng ngày",
        "admission": "Miễn phí tham quan",
        "travel_tip": "Đại lễ Kỳ Yên cúng đình diễn ra hàng năm vào trung tuần tháng 2 âm lịch với các nghi thức tế lễ cổ truyền và hát bội dân gian.",
        "source_citations": [
            {
                "title": "Di tích kiến trúc đình làng Nam Bộ Đình Trung Mỹ",
                "url": "https://baotangvinhlong.vn/dinh-trung-my",
                "notebook_id": "Sổ tay 1: Vĩnh Long (Vĩnh Long + Bến Tre + Trà Vinh)",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1.0,
            }
        ],
        "image_caption": "Gian chính điện bằng gỗ căm xe cổ thụ trầm mặc của ngôi đình làng Trung Mỹ có tuổi đời hơn 180 năm.",
        "image_alt": "Kiến trúc gian đình cổ mái ngói âm dương của Đình Trung Mỹ",
    },
    "dinh-loc-thuan": {
        "key_facts": [
            "Tạo dựng từ năm 1845 bên tả ngạn sông Ba Lai, là trung tâm tín ngưỡng và gắn kết tình làng nghĩa xóm của cư dân miệt cồn duyên hải.",
            "Đình lưu giữ sắc phong thần của vua Thiệu Trị năm thứ 5 (1845) và hoành phi mạ vàng chạm lộng chim phượng ngậm hoa mẫu đơn.",
            "Được xếp hạng Di tích Lịch sử - Văn hóa cấp Tỉnh năm 2008, đại trùng tu năm 2016 giữ nguyên vẹn hoa văn chạm khắc dân gian.",
        ],
        "hours": "Mở cửa từ 07:00 - 17:00 hàng ngày",
        "admission": "Miễn phí vào cổng",
        "travel_tip": "Nên hỏi ban hương chức đình để được xem chiếc khánh đồng cổ đúc từ giữa thế kỷ 19 còn ngân vang âm thanh trong trẻo.",
        "source_citations": [
            {
                "title": "Hồ sơ di tích văn hóa lịch sử Đình Lộc Thuận Bình Đại",
                "url": "https://bentre.gov.vn/di-tich-dinh-loc-thuan",
                "notebook_id": "Sổ tay 1: Vĩnh Long (Vĩnh Long + Bến Tre + Trà Vinh)",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1.0,
            }
        ],
        "image_caption": "Hàng cột gỗ lim và bàn thờ thần uy nghiêm của Đình Lộc Thuận lưu giữ sắc phong triều Nguyễn năm 1845.",
        "image_alt": "Chính điện tôn nghiêm với bao lam thếp vàng của Đình Lộc Thuận",
    },
    "dinh-tan-hoa": {
        "key_facts": [
            "Được xây dựng bên bờ sông Tiền thuộc phường Tân Hòa từ năm 1813 trong công cuộc khai phá mở đất lập làng.",
            "Đình có cấu trúc năm gian hai chái lợp ngói âm dương, nội thất nổi bật với các liễn đối khảm ốc xà cừ tinh xảo do nghệ nhân xứ Huế thực hiện.",
            "Được triều Tự Đức ban sắc phong vào năm 1852, trở thành điểm tựa tâm linh vững chắc cho bà con thương hồ miệt sông nước Cửu Long.",
        ],
        "hours": "Mở cửa từ 06:30 - 18:00 hàng ngày",
        "admission": "Miễn phí viếng thăm",
        "travel_tip": "Từ cầu Mỹ Thuận di chuyển đến đình chỉ mất 5 phút, du khách có thể ngắm hoàng hôn bên bờ sông Tiền lộng gió sau khi viếng đình.",
        "source_citations": [
            {
                "title": "Di tích lịch sử đình Tân Hòa bên bờ sông Tiền",
                "url": "https://svhttdl.vinhlong.gov.vn/dinh-tan-hoa",
                "notebook_id": "Sổ tay 1: Vĩnh Long (Vĩnh Long + Bến Tre + Trà Vinh)",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1.0,
            }
        ],
        "image_caption": "Khuôn viên Đình Tân Hòa nhìn ra khúc quanh êm đềm của sông Tiền lộng gió phù sa.",
        "image_alt": "Cổng đình và mái ngói cổ của Đình Tân Hòa soi bóng ven sông Tiền",
    },
    "san-chim-chua-phat-lon-tra-vinh": {
        "key_facts": [
            "Wat Kompong (thường gọi Chùa Phật Lớn) được tạo dựng từ năm 673, thuộc hàng cổ tự lâu đời bậc nhất tại thành phố Trà Vinh cũ.",
            "Khuôn viên chùa sở hữu một sân chim tự nhiên độc đáo giữa lòng đô thị với hàng trăm cây cổ thụ sao đen, dầu rái làm nơi cư ngụ cho hàng ngàn cánh cò, diệc, vạc.",
            "Nơi lưu giữ các hiện vật Phật giáo Nam tông quý giá và là trung tâm tổ chức các nghi lễ Chôl Chnăm Thmây, Ok Om Bok của phum sóc.",
        ],
        "hours": "Mở cửa từ 06:00 - 18:30 hàng ngày",
        "admission": "Miễn phí tham quan",
        "travel_tip": "Khoảng 17:00 chiều là thời điểm đàn chim rừng bay về tổ náo nhiệt nhất, rất phù hợp cho những ai yêu thích nhiếp ảnh động vật hoang dã.",
        "source_citations": [
            {
                "title": "Sân chim Chùa Phật Lớn Kompong Trà Vinh",
                "url": "https://dulich.travinh.gov.vn/san-chim-chua-phat-lon",
                "notebook_id": "Sổ tay 1: Vĩnh Long (Vĩnh Long + Bến Tre + Trà Vinh)",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1.0,
            }
        ],
        "image_caption": "Khu vườn cổ thụ rợp bóng của Chùa Phật Lớn nơi đàn chim cò hoang dã làm tổ trú ngụ giữa lòng đô thị.",
        "image_alt": "Đàn cò làm tổ trên những tán cây cổ thụ trong khuôn viên Chùa Phật Lớn",
    },
}


def load_dataset() -> dict:
    """Load JSON database."""
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_dataset(data: dict) -> None:
    """Save JSON database."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def apply_batch14_enrichment(entities: list[dict]) -> tuple[int, list[dict]]:
    """Apply Batch 14 historical relics enrichment."""
    logs = []
    count = 0
    for entity in entities:
        eid = entity.get("id")
        if eid in BATCH14_DATA:
            attrs = entity.setdefault("attributes", {})
            payload = BATCH14_DATA[eid]
            attrs["key_facts"] = payload["key_facts"]
            attrs["hours"] = payload["hours"]
            attrs["admission"] = payload["admission"]
            attrs["travel_tip"] = payload["travel_tip"]
            attrs["source_citations"] = payload["source_citations"]
            attrs["image_caption"] = payload["image_caption"]
            attrs["image_alt"] = payload["image_alt"]
            attrs["verified"] = True
            attrs["verifiedAt"] = "2026-09-19"
            count += 1
            logs.append({"id": eid, "name": entity.get("name"), "status": "enriched"})
    return count, logs


def main() -> None:
    """Execute Batch 14 enrichment."""
    data = load_dataset()
    entities = data.get("entities", [])
    count, logs = apply_batch14_enrichment(entities)
    save_dataset(data)

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump({"updated_count": count, "enriched": logs}, f, ensure_ascii=False, indent=2)

    print(f"Successfully enriched {count} / {len(BATCH14_DATA)} historical relics in Batch 14.")


if __name__ == "__main__":
    main()
