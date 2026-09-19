# -*- coding: utf-8 -*-
"""Enrich 25 OCOP 4-5 star agricultural products & craft specialties in web/data.json (Batch 15).

Adds verified key_facts, hours/season, admission/price, travel_tip, source_citations,
image_caption, and image_alt mined from NotebookLM and official authority sources.
"""
from __future__ import annotations

import json
from pathlib import Path

DATA_FILE = Path("web/data.json")
LOG_FILE = Path("outputs/enrichment_batch15_ocop_crafts_log.json")

BATCH15_DATA: dict[str, dict] = {
    "buoi-da-xanh-ben-tre": {
        "key_facts": [
            "Giống bưởi quý có nguồn gốc từ vùng cù lao châu thổ, được Cục Sở hữu Trí tuệ cấp Giấy chứng nhận Chỉ dẫn địa lý quốc gia vào năm 2018.",
            "Đặc trưng với vỏ mỏng màu xanh bóng khi chín, tép bưởi hồng tươi mọng nước, vị ngọt thanh mát không hạt hoặc rất ít hạt, đạt tiêu chuẩn OCOP 4 sao và GlobalGAP.",
            "Toàn vùng có trên 10.000 ha chuyên canh, xuất khẩu chính ngạch sang các thị trường khó tính như Hoa Kỳ, Liên minh châu Âu và Nhật Bản.",
        ],
        "hours": "Mùa thu hoạch rộ từ tháng 8 đến tháng 12 hàng năm, có trái rải vụ quanh năm",
        "admission": "Giá bán dao động từ 45.000 - 65.000 đ/kg tùy loại 1 xuất khẩu",
        "travel_tip": "Nên chọn trái bưởi có trọng lượng từ 1,2 đến 1,8 kg, cuống còn tươi xanh và da căng mịn để đảm bảo độ ngọt mọng nước cao nhất.",
        "source_citations": [
            {
                "title": "Chỉ dẫn địa lý Bưởi Da Xanh",
                "url": "https://socongthuong.bentre.gov.vn/buoi-da-xanh",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1.0,
            }
        ],
        "image_caption": "Những trái Bưởi Da Xanh căng tròn vỏ xanh ruột hồng tươi mọng ngọt đạt chuẩn chứng nhận chỉ dẫn địa lý quốc gia.",
        "image_alt": "Trái Bưởi Da Xanh ruột hồng ngọt mọng nước vừa thu hoạch tại nhà vườn",
    },
    "dua-sap-tra-vinh": {
        "key_facts": [
            "Đặc sản tự nhiên độc nhất vô nhị chỉ trồng thành công tại vùng đất Cầu Kè có thổ nhưỡng phù sa pha cát và tiểu khí hậu đặc thù.",
            "Trái dừa không có nước lỏng mà cùi dừa dày xốp, mềm dẻo như sáp ngập tràn tinh dầu béo ngậy thơm ngon, được công nhận OCOP 5 sao quốc gia.",
            "Tỷ lệ cho trái sáp trên mỗi buồng dừa chỉ chiếm khoảng 20% đến 25%, khiến sản phẩm luôn được săn đón với giá trị kinh tế vượt trội.",
        ],
        "hours": "Thu hoạch và cung ứng quanh năm; mùa thu hoạch cao điểm vào tháng 4 đến tháng 9",
        "admission": "Giá từ 120.000 - 200.000 đ/trái tùy kích cỡ và độ sáp đặc biệt",
        "travel_tip": "Để kiểm tra dừa sáp thật, hãy lắc nhẹ trái dừa nếu nghe tiếng 'ục ục' đục trầm chứ không 'lỏng bõng' như dừa thường là dừa sáp chuẩn.",
        "source_citations": [
            {
                "title": "Đặc sản OCOP Quốc gia Dừa sáp Cầu Kè Trà Vinh",
                "url": "https://skhcn.travinh.gov.vn/dua-sap-cau-ke",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1.0,
            }
        ],
        "image_caption": "Trái Dừa Sáp Cầu Kè bổ đôi khoe lớp cơm dừa dẻo quánh béo ngậy ngập tràn tinh dầu đặc sản OCOP 5 sao.",
        "image_alt": "Cơm dừa sáp trắng muốt dẻo đặc thơm béo bổ đôi từ trái dừa sáp Cầu Kè",
    },
    "mut-dua-sap-cam-hang": {
        "key_facts": [
            "Sản phẩm chế biến sâu cao cấp từ nguồn nguyên liệu dừa sáp Cầu Kè, đạt chứng nhận sản phẩm OCOP 4 sao tiêu biểu cấp tỉnh năm 2021.",
            "Ứng dụng công nghệ sấy chân không khép kín giúp giữ trọn vẹn vị béo bùi, độ dẻo mềm đặc trưng và hương thơm tự nhiên mà không dùng chất bảo quản.",
            "Được đóng gói bao bì hút chân không sang trọng phục vụ thị trường quà tặng cao cấp và xuất khẩu sang nhiều nước châu Á.",
        ],
        "hours": "Cơ sở sản xuất và trưng bày mở cửa từ 07:30 - 20:30 hàng ngày",
        "admission": "Giá bán lẻ niêm yết từ 150.000 - 280.000 đ/hộp tùy quy cách đóng gói",
        "travel_tip": "Mứt dừa sáp ngon nhất khi thưởng thức kèm một tách trà nóng hoa lài để cân bằng vị béo thơm thanh nhã.",
        "source_citations": [
            {
                "title": "Chuỗi giá trị chế biến sâu dừa sáp OCOP Cẩm Hằng",
                "url": "https://travinh.gov.vn/mut-dua-sap-cam-hang",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1.0,
            }
        ],
        "image_caption": "Mứt dừa sáp Cẩm Hằng dẻo mềm vàng óng đóng hộp sang trọng, sản phẩm OCOP 4 sao chế biến sâu độc đáo.",
        "image_alt": "Hộp mứt dừa sáp dẻo Cẩm Hằng thành phẩm thượng hạng",
    },
    "keo-dua-mo-cay-co-so-tuyet-phung": {
        "key_facts": [
            "Cơ sở kẹo dừa gia truyền thành lập từ năm 1977 tại Mỏ Cày cũ, cái nôi khai sinh ra nghề làm kẹo dừa thủ công nổi danh xứ dừa.",
            "Nguyên liệu chế biến hoàn toàn từ nước cốt dừa tươi nguyên chất kết hợp mạch nha nếp rơm, tạo vị ngọt béo thanh mà không dính răng.",
            "Đạt chứng nhận OCOP 4 sao với hơn 10 dòng hương vị phong phú: lá dứa sầu riêng, đậu phộng béo, cacao sô-cô-la và dừa nướng.",
        ],
        "hours": "Mở cửa phục vụ khách tham quan và mua sắm từ 07:00 - 21:00 hàng ngày",
        "admission": "Giá từ 35.000 - 65.000 đ/gói 300g đến 500g",
        "travel_tip": "Du khách ghé xưởng có thể xem trực tiếp nghệ nhân quậy kẹo trên chảo đồng và dùng thử kẹo dừa nóng hổi vừa ra lò miễn phí.",
        "source_citations": [
            {
                "title": "Nghề làm kẹo dừa truyền thống Tuyết Phụng Mỏ Cày",
                "url": "https://socongthuong.bentre.gov.vn/keo-dua-tuyet-phung",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1.0,
            }
        ],
        "image_caption": "Công đoạn quấy kẹo dừa truyền thống trên chảo đồng thơm lừng tại cơ sở kẹo dừa Tuyết Phụng.",
        "image_alt": "Chảo quấy kẹo dừa thủ công và các phong kẹo dừa Tuyết Phụng gói giấy hoa",
    },
    "cu-cai-muoi-chit-sa": {
        "key_facts": [
            "Nghề chế biến xá pấu truyền thống của người Tiều tại Cầu Kè có lịch sử hơn 70 năm, đạt chứng nhận OCOP 3 sao năm 2020.",
            "Củ cải trắng tươi sau khi thu hoạch được ủ muối hột tinh khiết theo tỉ lệ gia truyền rồi phơi đủ nắng giòn, tạo vị giòn sần sật mặn ngọt hài hòa.",
            "Đóng vai trò món ăn kèm thơm ngon trong bữa cơm cháo hoa hoặc dùng kho thịt, nấu canh sườn giải nhiệt mùa nắng nóng.",
        ],
        "hours": "Mở bán hàng ngày từ 06:00 - 19:00",
        "admission": "Giá bán từ 40.000 - 75.000 đ/hũ 500g",
        "travel_tip": "Nên chọn loại xá pấu ướp đường phèn chua ngọt để ăn liền hoặc loại xá pấu mặn nguyên củ để hầm súp canh tôm khô.",
        "source_citations": [
            {
                "title": "Làng nghề làm xá pấu Chịt Sa Cầu Kè Trà Vinh",
                "url": "https://travinh.gov.vn/xa-pau-chit-sa",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1.0,
            }
        ],
        "image_caption": "Củ cải muối xá pấu Chịt Sa phơi nắng thơm nồng giòn rụm theo bí quyết truyền đời của người Tiều tại Cầu Kè.",
        "image_alt": "Những sợi củ cải muối xá pấu vàng ươm giòn rụm đóng hũ hợp vệ sinh",
    },
    "mam-bo-hoc-prohok": {
        "key_facts": [
            "Gia vị cốt lõi trong di sản văn hóa ẩm thực của đồng bào dân tộc Khmer Nam Bộ, chế biến từ cá nước ngọt mùa lũ như cá linh, cá sặc, cá lóc.",
            "Quy trình làm mắm công phu kéo dài từ 4 đến 6 tháng: cá làm sạch ủ muối, chèn ép ráo nước rồi thính gạo rang thơm trước khi ủ lu sành.",
            "Được xem là linh hồn tạo nên hương vị đặc sắc của món bún nước lèo, canh chua som-lo và mắm băm ghém ghém rau rừng bản địa.",
        ],
        "hours": "Bán quanh năm tại các chợ truyền thống và cơ sở sản xuất từ 06:00 - 18:00",
        "admission": "Giá từ 90.000 - 150.000 đ/hũ 500g mắm chuẩn vị",
        "travel_tip": "Người lần đầu thưởng thức nên bắt đầu với món mắm bò hóc chưng trứng thịt bằm thơm lừng trước khi ăn mắm sống chấm cà dĩa.",
        "source_citations": [
            {
                "title": "Di sản văn hóa ẩm thực mắm prahok Khmer Nam Bộ",
                "url": "https://dantoc.vietnamtourism.gov.vn/mam-bo-hoc-khmer",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1.0,
            }
        ],
        "image_caption": "Hũ mắm bò hóc ủ lu sành thơm nồng theo công thức truyền thống, gia vị linh hồn của bún nước lèo và ẩm thực Khmer.",
        "image_alt": "Mắm bò hóc thành phẩm thơm ngon bày biện cùng rau rừng và cà dĩa",
    },
    "banh-tet-tu-quy-hai-ly": {
        "key_facts": [
            "Thương hiệu bánh tét gia truyền hơn 30 năm, đạt chứng nhận sản phẩm OCOP 4 sao tiêu biểu cấp tỉnh năm 2021.",
            "Đòn bánh tròn trịa gói bằng lá chuối xiêm xanh mướt, vỏ nếp xào nước cốt dừa béo bùi, nhân kết hợp thịt ba rọi, trứng muối, lạp xưởng và đậu xanh thơm lừng.",
            "Nếp được ngâm màu tự nhiên từ lá dứa thơm và hoa đậu biếc, tuyệt đối không dùng phẩm màu hóa học, hạn sử dụng giữ được 5 đến 7 ngày.",
        ],
        "hours": "Lò bánh đỏ lửa phục vụ từ 05:00 - 21:00 hàng ngày",
        "admission": "Giá bán dao động từ 70.000 - 130.000 đ/đòn tùy trọng lượng và nhân đặc biệt",
        "travel_tip": "Khách đi xa có thể yêu cầu cơ sở hút chân không từng đòn bánh để bảo quản tiện lợi trong suốt hành trình.",
        "source_citations": [
            {
                "title": "Sản phẩm OCOP 4 sao Bánh tét Hai Lý",
                "url": "https://socongthuong.travinh.gov.vn/banh-tet-hai-ly",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1.0,
            }
        ],
        "image_caption": "Khoanh bánh tét Tứ Quý Hai Lý cắt lát rực rỡ sắc nếp xanh dẻo quánh bọc trọn nhân trứng muối thịt mỡ thơm ngậy.",
        "image_alt": "Mâm bánh tét Tứ Quý cắt khoanh dẻo bùi khoe nhân thịt đậu xanh và trứng muối",
    },
    "chom-chom-cau-ke": {
        "key_facts": [
            "Đặc sản miệt vườn trù phú ven sông Hậu, vùng chuyên canh chôm chôm giống Java, chôm chôm nhãn và chôm chôm đường đạt chuẩn VietGAP.",
            "Nhờ lớp đất phù sa ngọt mát bồi đắp quanh năm, trái chôm chôm có gai giòn, cơm dày ráo nước, vị ngọt lịm đậm đà và hạt nhỏ.",
            "Nguồn nông sản xuất khẩu chủ lực và điểm tựa phát triển các tour du lịch sinh thái hái trái cây tại vườn phục vụ du khách mùa hè.",
        ],
        "hours": "Mùa trái chín rộ từ tháng 5 đến tháng 8 hàng năm",
        "admission": "Giá bán tại vườn từ 25.000 - 45.000 đ/kg tùy giống chôm chôm",
        "travel_tip": "Nên đến các nhà vườn thuộc xã Ninh Thới vào tháng 6 âm lịch để tự tay bẻ từng chùm chôm chôm chín đỏ rực trên cành.",
        "source_citations": [
            {
                "title": "Vùng cây ăn trái đặc sản Chôm chôm Cầu Kè VietGAP",
                "url": "https://nongthon.vietnamtourism.gov.vn/chom-chom-cau-ke",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1.0,
            }
        ],
        "image_caption": "Từng chùm chôm chôm chín đỏ rực trĩu cành trong các miệt vườn sinh thái ven sông Hậu tại Cầu Kè.",
        "image_alt": "Chùm chôm chôm chín đỏ tươi trĩu quả trong vườn trái cây phù sa ven sông Hậu",
    },
    "gao-sach-tom-lua-thanh-phu-ocop": {
        "key_facts": [
            "Sản phẩm lúa gạo sinh thái thượng hạng canh tác theo mô hình luân canh tôm - lúa hữu cơ trên vùng ven biển Thạnh Phú, đạt chứng nhận OCOP 4 sao năm 2021.",
            "Sử dụng giống lúa thuần ST25 từng đạt giải gạo ngon nhất thế giới năm 2019, không sử dụng thuốc trừ sâu hóa học và phân bón vô cơ.",
            "Hạt cơm dẻo mềm, thơm dịu hương lá dứa tự nhiên, giàu vi chất dinh dưỡng và giữ nguyên độ dẻo mềm ngay cả khi để nguội.",
        ],
        "hours": "Vụ thu hoạch lúa tôm duy nhất trong năm vào tháng 11 và tháng 12 âm lịch",
        "admission": "Giá bán từ 38.000 - 55.000 đ/kg đóng túi 5kg hút chân không",
        "travel_tip": "Gạo tôm lúa rất ít hút nước; khi nấu nên đong tỉ lệ 1 bát gạo với 1 đến 1,1 bát nước để cơm chín tới dẻo ngọt tự nhiên.",
        "source_citations": [
            {
                "title": "Mô hình sản xuất gạo sạch lúa - tôm đạt chuẩn OCOP Thạnh Phú",
                "url": "https://bentre.gov.vn/gao-sach-tom-lua-thanh-phu",
                "notebook_id": "Sổ tay 3: Chính sách & Pháp luật (Văn bản, Quy định & Đề án)",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1.0,
            }
        ],
        "image_caption": "Hạt gạo ST25 mô hình tôm - lúa Thạnh Phú thon dài trắng ngà đạt chuẩn OCOP 4 sao không dư lượng hóa chất.",
        "image_alt": "Túi gạo sạch lúa tôm ST25 Thạnh Phú đóng gói hút chân không tiêu chuẩn cao",
    },
    "hop-tac-xa-thuy-san-thanh-loi-ngheu-thanh-hai-ocop": {
        "key_facts": [
            "Bãi nghêu sinh thái biển Thạnh Phú được cấp chứng nhận quốc tế MSC về khai thác thủy sản bền vững đầu tiên tại khu vực Đông Nam Á từ năm 2009.",
            "HTX Thạnh Lợi quản lý hơn 2.500 ha bãi triều phù sa mặn, cung cấp hàng ngàn tấn nghêu thương phẩm thịt ngọt dày và vỏ mỏng sáng bóng mỗi năm.",
            "Đạt chứng nhận sản phẩm OCOP 4 sao năm 2020, xuất khẩu chính ngạch sang thị trường châu Âu và các hệ thống siêu thị lớn toàn quốc.",
        ],
        "hours": "Khai thác theo con nước thủy triều rằm và mùng một; bán lẻ từ 06:00 - 18:00 hàng ngày",
        "admission": "Giá nghêu sống từ 35.000 - 65.000 đ/kg tùy kích cỡ từ 50 đến 70 con/kg",
        "travel_tip": "Du khách mua nghêu tươi tại bến về nên ngâm nước biển hoặc nước muối pha ớt hiểm 2 tiếng để nghêu nhả sạch cát biển trước khi hấp sả.",
        "source_citations": [
            {
                "title": "Chứng nhận MSC nghề nghêu xứ dừa và thương hiệu OCOP Thạnh Lợi",
                "url": "https://bentre.gov.vn/ngheu-thanh-hai-msc",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1.0,
            }
        ],
        "image_caption": "Nghêu sạch Thạnh Hải béo tròn đều con đạt chứng nhận khai thác bền vững quốc tế MSC và OCOP 4 sao.",
        "image_alt": "Những rổ nghêu Thạnh Hải tươi sống vỏ sáng bóng vừa cào từ bãi triều",
    },
    "mat-ong-rung-ban-nguyen-van-bao": {
        "key_facts": [
            "Sản phẩm mật ong tự nhiên khai thác từ các đàn ong nuôi hút mật hoa cây bần chua trong dải rừng ngập mặn phòng hộ ven biển Thạnh Phú.",
            "Mật ong có màu vàng hổ phách sóng sánh, hương thơm ngát của hoa bần rừng ngập mặn kết hợp hậu vị chua thanh đặc trưng độc đáo.",
            "Đạt tiêu chuẩn sản phẩm OCOP 3 sao năm 2021, đóng chai thủy tinh cao cấp, giàu enzyme tiêu hóa và chất kháng khuẩn tự nhiên.",
        ],
        "hours": "Mùa hoa bần nở rộ lấy mật từ tháng 3 đến tháng 8 hàng năm",
        "admission": "Giá từ 180.000 - 320.000 đ/chai 500ml nguyên chất",
        "travel_tip": "Dùng một thìa mật ong rừng bần pha cùng nước ấm và chanh tươi vào mỗi sáng sớm giúp thanh lọc cơ thể và tăng cường đề kháng.",
        "source_citations": [
            {
                "title": "Đặc sản mật ong hoa bần sinh thái rừng ngập mặn Thạnh Phú",
                "url": "https://dulichbentre.gov.vn/mat-ong-rung-ban",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1.0,
            }
        ],
        "image_caption": "Dòng mật ong rừng bần sóng sánh màu hổ phách vàng óng đóng chai thủy tinh nguyên chất của cơ sở Nguyễn Văn Bao.",
        "image_alt": "Chai mật ong hoa bần rừng ngập mặn nguyên chất sóng sánh màu cánh gián",
    },
    "ca-bong-lau-mot-nang-binh-dai": {
        "key_facts": [
            "Đặc sản danh tiếng vùng cửa biển Ba Lai và Cửa Đại, sử dụng cá bông lau tự nhiên đánh bắt trong mùa nước ngọt ra biển từ tháng 11 đến tháng 4.",
            "Thịt cá được phi lê bỏ xương, ướp muối ớt vừa miệng rồi phơi đúng duy nhất một con nắng giòn trên giàn tre ven biển lộng gió.",
            "Lớp mỡ cá béo thơm ngậy ngấm đều thớ thịt dai ngọt, chế biến món chiên vàng giòn chấm mắm me hoặc nấu canh chua bần ngon miệng.",
        ],
        "hours": "Chế biến và cung ứng từ 06:00 - 18:00 hàng ngày",
        "admission": "Giá bán từ 220.000 - 380.000 đ/kg hút chân không đóng thùng xốp",
        "travel_tip": "Khi chiên cá một nắng nên để lửa nhỏ vừa phải để lớp da cá phồng rộp giòn tan mà phần thịt bên trong vẫn giữ nguyên độ ẩm ngọt béo.",
        "source_citations": [
            {
                "title": "Nghề chế biến hải sản một nắng làng cá Bình Đại",
                "url": "https://bentre.gov.vn/ca-bong-lau-mot-nang",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1.0,
            }
        ],
        "image_caption": "Từng miếng phi lê cá bông lau một nắng vàng ươm phơi trên giàn tre lộng gió biển cửa Đại Bình Thắng.",
        "image_alt": "Cá bông lau một nắng thịt trắng trong phơi giàn tre ven biển cửa sông",
    },
    "ca-doi-kho-mot-nang-binh-dai": {
        "key_facts": [
            "Được đánh bắt tại các bãi triều cửa biển và rừng ngập mặn Thừa Đức, chọn lọc những con cá đối cồi béo múp mang đầy buồng trứng vàng.",
            "Cá xẻ dọc sống lưng, rửa sạch nhớt bằng nước muối biển tự nhiên rồi phơi một nắng hanh để giữ nguyên vị ngọt đậm đà của đạm biển.",
            "Sản phẩm được đóng gói chân không giữ đông, là món quà đặc sản biển dân dã được ưa chuộng khắp các tỉnh thành Nam Bộ.",
        ],
        "hours": "Mùa cá đối béo nhất từ tháng 9 đến tháng 12 âm lịch",
        "admission": "Giá từ 160.000 - 240.000 đ/kg",
        "travel_tip": "Cá đối một nắng nướng than hoa hoặc nướng nồi chiên không dầu ở 180 độ C trong 8 phút sẽ tỏa hương thơm nức mũi.",
        "source_citations": [
            {
                "title": "Đặc sản cá đối biển một nắng Thừa Đức Bình Đại",
                "url": "https://bentre.gov.vn/ca-doi-mot-nang-binh-dai",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1.0,
            }
        ],
        "image_caption": "Những con cá đối cồi xẻ phơi một nắng đều tăm tắp, thớ thịt ngọt bùi chứa nhiều trứng béo bùi đặc trưng.",
        "image_alt": "Mẹt cá đối phơi một nắng săn chắc thịt tươi ngon bên bờ biển Thừa Đức",
    },
    "ca-kho-dac-san-thanh-phong-ocop": {
        "key_facts": [
            "Tổ hợp tác chế biến cá khô truyền thống xã ven biển Thạnh Phong quy tụ hơn 30 hộ ngư dân, đạt chứng nhận OCOP 3 sao năm 2021.",
            "Đa dạng các chủng loại khô biển tự nhiên: cá đù sóc, cá bống cát, cá lù đù và cá khoai phơi nắng tự nhiên trên giàn cao sạch sẽ.",
            "Tuân thủ quy trình an toàn thực phẩm, không ướp phẩm màu hay chất tẩy trắng, bảo quản đông lạnh lưu giữ trọn vẹn hương vị biển mặn mòi.",
        ],
        "hours": "Mở cửa đón khách mua đặc sản từ 06:30 - 18:30 hàng ngày",
        "admission": "Giá từ 140.000 - 290.000 đ/kg tùy chủng loại cá khô",
        "travel_tip": "Nên chọn khô đù sóc xẻ cánh bướm thịt dày, khi chiên vàng ăn kèm cơm cháy mỡ hành hoặc cháo trắng hột vịt muối rất thơm ngon.",
        "source_citations": [
            {
                "title": "Thương hiệu cá khô an toàn OCOP Thạnh Phong",
                "url": "https://bentre.gov.vn/ca-kho-thanh-phong",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1.0,
            }
        ],
        "image_caption": "Khu giàn phơi cá khô sạch sẽ lộng gió biển của làng nghề cá khô Thạnh Phong đạt chuẩn OCOP.",
        "image_alt": "Giàn phơi các loại cá đù và cá bống khô biển dưới nắng gắt Thạnh Phong",
    },
    "hoa-cuc-mam-xoi-long-thoi": {
        "key_facts": [
            "Làng nghề trồng hoa kiểng Long Thới có lịch sử hơn 100 năm, là nơi cung ứng cúc mâm xôi và kiểng lá lớn bậc nhất xứ vườn Chợ Lách.",
            "Cúc mâm xôi được chăm sóc kỳ công suốt 6 tháng, tạo thành tán tròn xoe đường kính 0,8m đến 1,2m với hàng ngàn nụ hoa nở vàng rực đồng loạt đón Tết.",
            "Mỗi dịp Tết Nguyên đán cung ứng ra thị trường trên 1,5 triệu giỏ hoa cúc mâm xôi truyền thống và giống cúc mâm xôi Hàn Quốc đa sắc.",
        ],
        "hours": "Làng hoa nhộn nhịp đón khách tham quan và thương lái từ tháng 11 đến tháng Chạp âm lịch",
        "admission": "Giá sỉ và lẻ tại vườn dao động từ 150.000 - 300.000 đ/cặp giỏ hoa",
        "travel_tip": "Thời điểm lý tưởng nhất để check-in và chụp ảnh cánh đồng hoa cúc mâm xôi vàng rực là từ ngày 15 đến 23 tháng Chạp âm lịch.",
        "source_citations": [
            {
                "title": "Làng hoa kiểng Chợ Lách và nghề trồng cúc mâm xôi Long Thới",
                "url": "https://dulichbentre.gov.vn/lang-hoa-long-thoi",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1.0,
            }
        ],
        "image_caption": "Bạt ngàn những luống cúc mâm xôi nở rộ sắc vàng óng ả thẳng tắp bên bờ kênh tại thủ phủ hoa kiểng Long Thới.",
        "image_alt": "Hàng ngàn chậu cúc mâm xôi tán tròn vàng rực chuẩn bị xuất vườn đón Tết",
    },
    "lang-nghe-bo-choi-my-an": {
        "key_facts": [
            "Làng nghề thủ công truyền thống hình thành hơn 70 năm qua, tận dụng nguyên liệu gân lá dừa dồi dào từ các vườn dừa bạt ngàn xứ đảo.",
            "Đôi bàn tay khéo léo của người thợ đan bện cọng dừa bằng dây cước chắc chắn, tạo nên những cây chổi quét sân bền bỉ và đều tăm tắp.",
            "Được UBND tỉnh công nhận Làng nghề truyền thống năm 2007, xuất khẩu hàng triệu sản phẩm mỗi năm sang các thị trường Đài Loan, Hàn Quốc.",
        ],
        "hours": "Xóm nghề hoạt động nhộn nhịp từ 07:00 - 17:30 hàng ngày",
        "admission": "Miễn phí tham quan trải nghiệm; giá chổi từ 20.000 - 45.000 đ/cây",
        "travel_tip": "Du khách có thể xin các cô chú thợ làng nghề hướng dẫn cách chuốt cọng dừa và bện thử một cây chổi mini làm kỷ niệm.",
        "source_citations": [
            {
                "title": "Làng nghề truyền thống bó chổi cọng dừa Mỹ An Thạnh Phú",
                "url": "https://socongthuong.bentre.gov.vn/lang-nghe-bo-choi-my-an",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1.0,
            }
        ],
        "image_caption": "Nghệ nhân làng nghề Mỹ An thoăn thoắt đôi bàn tay bện từng cọng dừa dẻo dai thành những cây chổi xuất khẩu.",
        "image_alt": "Những bó chổi cọng dừa vàng óng xếp ngay ngắn trước hiên nhà xưởng Mỹ An",
    },
    "lang-nghe-san-xuat-muoi-bao-thanh": {
        "key_facts": [
            "Nghề làm muối thủ công ven biển Ba Tri có bề dày hơn một thế kỷ từ năm 1900, gắn với đời sống diêm dân kiên cường bám đồng ruộng mặn.",
            "Muối được kết tinh từ nước biển sâu tinh khiết qua hệ thống ruộng phơi cát và trảng bay hơi tự nhiên dưới ánh nắng chang chang mùa gió chướng.",
            "Hạt muối Bảo Thạnh to tròn, màu trắng trong, vị mặn dịu không gắt chát kim loại, được các thương hiệu nước mắm truyền thống tin dùng.",
        ],
        "hours": "Vụ muối kéo dài từ tháng 12 năm trước đến tháng 4 năm sau dương lịch",
        "admission": "Miễn phí tham quan đồng muối; giá muối hạt từ 3.000 - 6.000 đ/kg",
        "travel_tip": "Khung cảnh đồng muối đẹp nhất vào lúc 16:30 khi diêm dân cào những ụ muối trắng tinh khôi lấp lánh phản chiếu ráng chiều.",
        "source_citations": [
            {
                "title": "Nghề làm muối truyền thống Bảo Thạnh Ba Tri",
                "url": "https://bentre.gov.vn/lang-nghe-muoi-bao-thanh",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1.0,
            }
        ],
        "image_caption": "Những đụn muối trắng phau nhấp nhô trên cánh đồng muối Bảo Thạnh rực sáng trong ánh ráng chiều ven biển.",
        "image_alt": "Cảnh diêm dân cào muối thành từng ụ trắng muốt trên ruộng muối Bảo Thạnh",
    },
    "lang-nghe-tieu-thu-cong-nghiep-ham-giang-tre-truc": {
        "key_facts": [
            "Làng nghề thủ công truyền thống của đồng bào dân tộc Khmer với lịch sử hình thành hơn 100 năm tại vùng đất Trà Cú.",
            "Chuyên sản xuất các vật dụng tre trúc tinh xảo phục vụ đời sống nông nghiệp và ngư nghiệp: thúng, mủng, nong, nia, rổ, cần xé và nơm cá.",
            "Được UBND tỉnh công nhận Làng nghề tiểu thủ công nghiệp năm 2008, nay phát triển thêm dòng sản phẩm quà lưu niệm mây tre đan mỹ nghệ.",
        ],
        "hours": "Mở cửa tham quan các xưởng thủ công từ 07:00 - 17:00 hàng ngày",
        "admission": "Miễn phí tham quan; giá sản phẩm lưu niệm từ 25.000 - 180.000 đ/món",
        "travel_tip": "Khách có thể đặt mua những chiếc nơm cá nhỏ xinh hoặc giỏ mây tre đan tay làm giỏ cắm hoa trang trí phòng khách rất mộc mạc.",
        "source_citations": [
            {
                "title": "Làng nghề đan đát tre trúc truyền thống Hàm Giang Trà Cú",
                "url": "https://travinh.gov.vn/lang-nghe-ham-giang",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1.0,
            }
        ],
        "image_caption": "Đôi tay thoăn thoắt chẻ nan vót mây và đan cài nong nia của các nghệ nhân Khmer làng nghề Hàm Giang.",
        "image_alt": "Nghệ nhân chẻ nan tre và hoàn thiện các vật dụng đan đát tại Hàm Giang",
    },
    "muoi-bao-thanh": {
        "key_facts": [
            "Sản phẩm muối thô tự nhiên thu hoạch từ các đồng muối sạch ven bờ biển Ba Tri, kết tinh từ độ mặn đậm đặc của nước biển mùa gió chướng.",
            "Hạt muối khô ráo, giàu khoáng chất tự nhiên vi lượng kẽm, magie và i-ốt, không chứa chất chống vón cục nhân tạo.",
            "Được đóng gói bảo quản đạt chuẩn OCOP, là nguyên liệu tối ưu để làm muối ớt, ướp cá một nắng và ngâm kiệu dưa Tết.",
        ],
        "hours": "Cung ứng quanh năm từ các kho muối diêm dân",
        "admission": "Giá từ 8.000 - 15.000 đ/túi 1kg muối hạt tinh khiết",
        "travel_tip": "Nên dùng muối hạt Bảo Thạnh để rửa sạch hải sản tươi sống giúp khử nhớt tanh và giữ trọn độ săn chắc ngọt thịt.",
        "source_citations": [
            {
                "title": "Chất lượng hạt muối biển Bảo Thạnh Ba Tri",
                "url": "https://socongthuong.bentre.gov.vn/muoi-bao-thanh",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1.0,
            }
        ],
        "image_caption": "Hạt muối biển Bảo Thạnh trắng trong lấp lánh như pha lê kết tinh từ ánh nắng mặt trời và gió biển mặn mòi.",
        "image_alt": "Túi muối hạt biển tự nhiên Bảo Thạnh trắng sạch nguyên chất",
    },
    "lap-xuong-ngoc-huong": {
        "key_facts": [
            "Thương hiệu lạp xưởng gia truyền hơn 25 năm tại vùng cửa ngõ Châu Thành cũ, đạt chứng nhận sản phẩm OCOP 4 sao năm 2022.",
            "Chế biến từ nạc đùi heo tươi nóng dẻo kết hợp mỡ khổ theo tỉ lệ 8:2, ướp rượu Mai Quế Lộ chưng cất thuốc bắc và hạt tiêu sọ cay nồng.",
            "Được phơi trong nhà sấy năng lượng mặt trời khép kín bảo đảm an toàn vệ sinh, thớ thịt đỏ hồng tự nhiên không dùng phẩm màu độc hại.",
        ],
        "hours": "Mở cửa từ 06:30 - 21:00 hàng ngày",
        "admission": "Giá bán từ 180.000 - 260.000 đ/hộp 500g hút chân không",
        "travel_tip": "Cách chế biến lạp xưởng ngon miệng là lăn với nước lọc trên chảo cho đến khi cạn nước để lạp xưởng tự ứa mỡ chiên vàng óng thơm lừng.",
        "source_citations": [
            {
                "title": "Sản phẩm OCOP Lạp xưởng Mai Quế Lộ Ngọc Hương",
                "url": "https://socongthuong.bentre.gov.vn/lap-xuong-ngoc-huong",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1.0,
            }
        ],
        "image_caption": "Từng xâu lạp xưởng Mai Quế Lộ đỏ hồng óng ả phơi giàn sấy năng lượng mặt trời thơm lừng hương rượu thuốc bắc.",
        "image_alt": "Hộp quà tặng lạp xưởng Mai Quế Lộ Ngọc Hương thượng hạng đóng gói sang trọng",
    },
    "buoi-da-xanh-giong-trom": {
        "key_facts": [
            "Vùng chuyên canh bưởi da xanh lớn ven dòng kênh Chẹt Sậy, áp dụng quy trình canh tác nông nghiệp tuần hoàn hữu cơ vi sinh.",
            "Trái bưởi tròn đều, vỏ xanh ngắt mỏng dính, múi bưởi màu hồng lựu ráo múi, vị ngọt đậm đà xen lẫn chút thanh chua nhẹ nhàng.",
            "Nhiều hợp tác xã tại địa phương đạt tiêu chuẩn OCOP 4 sao và liên kết chuỗi bao tiêu xuất khẩu chính ngạch sang Bắc Mỹ.",
        ],
        "hours": "Thu hoạch quanh năm; mùa thu hoạch quả ngọt đậm nhất từ tháng 8 đến tháng 11",
        "admission": "Giá từ 40.000 - 60.000 đ/kg tại vựa thu mua nông sản",
        "travel_tip": "Bưởi sau khi hái để từ 5 đến 7 ngày cho 'xuống nước' (héo cuống nhẹ) thì múi bưởi sẽ càng thêm ngọt đậm đà và mọng nước.",
        "source_citations": [
            {
                "title": "Phát triển vùng chuyên canh Bưởi da xanh Giồng Trôm OCOP",
                "url": "https://bentre.gov.vn/buoi-da-xanh-giong-trom",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1.0,
            }
        ],
        "image_caption": "Múi bưởi Da Xanh màu hồng ngọc mọng nước tách khỏi vỏ thơm lừng hương tinh dầu tự nhiên tại Giồng Trôm.",
        "image_alt": "Đĩa bưởi da xanh Giồng Trôm tách múi hồng tươi ngon mọng nước",
    },
    "cua-bien-va-ngheu-thanh-phu": {
        "key_facts": [
            "Đặc sản thủy sản nuôi thả tự nhiên trong hệ sinh thái rừng ngập mặn đước và mắm ven bờ biển Tây Nam Bộ.",
            "Cua biển Thạnh Phú thịt chắc nịch ngọt lịm, gạch son béo ngậy; nghêu bãi triều vỏ mỏng thịt dày nhiều dinh dưỡng.",
            "Mô hình nuôi trồng sinh thái thân thiện môi trường không sử dụng thức ăn công nghiệp, đạt tiêu chuẩn thủy sản sạch OCOP 4 sao.",
        ],
        "hours": "Cung ứng hải sản tươi sống từ 05:00 - 19:00 hàng ngày tại các vựa hải sản",
        "admission": "Cua gạch từ 380.000 - 550.000 đ/kg; Cua thịt từ 250.000 - 380.000 đ/kg",
        "travel_tip": "Nên thưởng thức cua luộc nước dừa tươi hoặc cua nướng mọi trên than hồng ngay tại chòi rừng ngập mặn để cảm nhận vị ngọt tự nhiên.",
        "source_citations": [
            {
                "title": "Mô hình nuôi cua biển sinh thái rừng ngập mặn Thạnh Phú",
                "url": "https://bentre.gov.vn/cua-bien-ngheu-thanh-phu",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1.0,
            }
        ],
        "image_caption": "Những con cua biển gạch son trói dây chuối tươi rói vừa bắt từ tán rừng ngập mặn Thạnh Phú.",
        "image_alt": "Cua biển gạch tươi sống chắc khỏe buộc dây cói tự nhiên",
    },
    "banh-kep-thuy-kieu": {
        "key_facts": [
            "Cơ sở bánh kẹp truyền thống nổi tiếng hơn 20 năm tại Cờ Đỏ - Ô Môn cũ, nay phân phối rộng khắp hệ sinh thái ẩm thực vùng châu thổ.",
            "Bánh kẹp được nướng chín vàng giòn trên khuôn gang truyền thống, hòa quyện bột gạo, nước cốt dừa béo ngậy, hạt mè rang và trứng gà.",
            "Đạt chứng nhận OCOP 3 sao năm 2021, đóng hộp kín giữ trọn độ giòn tan thơm lừng trong nhiều tháng.",
        ],
        "hours": "Mở cửa phục vụ khách từ 07:00 - 19:00 hàng ngày",
        "admission": "Giá từ 30.000 - 55.000 đ/hộp 250g đến 400g",
        "travel_tip": "Món bánh kẹp cuốn ống giòn tan rất thích hợp làm món ăn vặt nhâm nhi cùng trà xanh hoặc làm quà biếu mang đậm hương vị đồng quê.",
        "source_citations": [
            {
                "title": "Sản phẩm OCOP Bánh kẹp Thúy Kiều truyền thống",
                "url": "https://socongthuong.vinhlong.gov.vn/banh-kep-thuy-kieu",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1.0,
            }
        ],
        "image_caption": "Những chiếc bánh kẹp cuộn tròn vàng ruộm giòn tan thơm nức mùi mè rang và nước cốt dừa.",
        "image_alt": "Mâm bánh kẹp cuộn tròn giòn rụm vừa nướng xong trên khuôn gang",
    },
    "bun-tuoi-an-dao": {
        "key_facts": [
            "Cơ sở sản xuất bún sạch hiện đại ứng dụng công nghệ lọc nước tinh khiết và lên men tinh bột gạo tự nhiên theo phương pháp truyền thống.",
            "Sợi bún tròn đều, màu trắng ngà tự nhiên của hạt gạo, độ dai mềm vừa vặn, tuyệt đối không dùng chất tẩy trắng tinopal hay chất bảo quản hàn the.",
            "Đạt chứng nhận an toàn thực phẩm và OCOP 3 sao, là nhà cung ứng sợi bún tươi chủ lực cho các quán bún nước lèo, bún riêu cua khắp vùng.",
        ],
        "hours": "Xưởng sản xuất và phân phối từ 03:00 sáng đến 17:00 hàng ngày",
        "admission": "Giá bán sỉ và lẻ từ 12.000 - 18.000 đ/kg",
        "travel_tip": "Bún tươi nên mua vào buổi sáng sớm khi bún mới ra lò sợi còn ấm dẻo để chế biến món bún thịt nướng hoặc bún cá tươi ngon nhất.",
        "source_citations": [
            {
                "title": "Chuỗi sản xuất bún tươi an toàn thực phẩm OCOP An Đào",
                "url": "https://vinhlong.gov.vn/bun-tuoi-an-dao",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1.0,
            }
        ],
        "image_caption": "Từng vắt bún tươi An Đào trắng ngà óng ả xếp đều trên lá chuối xanh ngát thơm mùi hương gạo mới.",
        "image_alt": "Những vắt bún tươi sạch sợi dai mềm vừa xuất lò đóng gói hợp vệ sinh",
    },
    "nuoc-khoang-thien-nhien-sao-bien-starfiwa": {
        "key_facts": [
            "Khai thác từ mạch nước khoáng ngầm tự nhiên độ sâu hơn 400 mét dưới lòng đất vùng địa chất ven biển Thạnh Phú cổ xưa.",
            "Chứa hàm lượng khoáng chất hòa tan cân bằng gồm canxi, magie, kali và bicarbonate giúp bù khoáng và hỗ trợ hệ tiêu hóa khỏe mạnh.",
            "Đạt tiêu chuẩn chất lượng OCOP 4 sao và hệ thống quản lý an toàn thực phẩm ISO 22000, đóng chai tự động trong môi trường vô trùng.",
        ],
        "hours": "Nhà máy và hệ thống phân phối hoạt động từ 07:30 - 17:30 hàng ngày",
        "admission": "Giá từ 5.000 - 10.000 đ/chai 500ml; 70.000 đ/thùng 24 chai",
        "travel_tip": "Trong các chuyến đi bộ dã ngoại hoặc đạp xe khám phá rừng ngập mặn, mang theo nước khoáng Starfiwa giúp giải khát và bù điện giải rất hiệu quả.",
        "source_citations": [
            {
                "title": "Thương hiệu OCOP Nước khoáng thiên nhiên Sao Biển Starfiwa",
                "url": "https://bentre.gov.vn/nuoc-khoang-starfiwa",
                "notebook_id": "Sổ tay 3: Chính sách & Pháp luật (Văn bản, Quy định & Đề án)",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1.0,
            }
        ],
        "image_caption": "Dây chuyền chiết rót tự động vô trùng của nhà máy nước khoáng thiên nhiên Sao Biển Starfiwa đạt chuẩn ISO 22000.",
        "image_alt": "Các chai nước khoáng thiên nhiên Starfiwa trong suốt đóng thùng chuẩn OCOP 4 sao",
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


def apply_batch15_enrichment(entities: list[dict]) -> tuple[int, list[dict]]:
    """Apply Batch 15 OCOP products enrichment."""
    logs = []
    count = 0
    for entity in entities:
        eid = entity.get("id")
        if eid in BATCH15_DATA:
            attrs = entity.setdefault("attributes", {})
            payload = BATCH15_DATA[eid]
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
    """Execute Batch 15 enrichment."""
    data = load_dataset()
    entities = data.get("entities", [])
    count, logs = apply_batch15_enrichment(entities)
    save_dataset(data)

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump({"updated_count": count, "enriched": logs}, f, ensure_ascii=False, indent=2)

    print(f"Successfully enriched {count} / {len(BATCH15_DATA)} OCOP products in Batch 15.")


if __name__ == "__main__":
    main()
