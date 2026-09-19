# -*- coding: utf-8 -*-
"""Enrich 25 natural wonders, river islands & mangrove terroirs in web/data.json (Batch 13).

Adds verified key_facts, hours, admission, travel_tip, and source_citations
mined from NotebookLM and official authority sources.
"""
from __future__ import annotations

import json
from pathlib import Path

DATA_FILE = Path("web/data.json")
LOG_FILE = Path("outputs/enrichment_batch13_nature_wonders_log.json")

BATCH13_DATA: dict[str, dict] = {
    "cu-lao-an-binh": {
        "key_facts": [
            "Cù lao rộng hơn 60 km2 hình thành từ phù sa sông Cổ Chiên và sông Tiền bồi đắp qua hàng trăm năm, bao gồm 4 xã: An Bình, Bình Hòa Phước, Đồng Phú và Hòa Ninh.",
            "Sở hữu mạng lưới kênh rạch chằng chịt dài hàng trăm cây số với hơn 1.500 ha chuyên canh chôm chôm Java, nhãn xuồng cơm vàng và sầu riêng Ri6 trĩu quả.",
            "Cái nôi của mô hình du lịch homestay miệt vườn Nam Bộ từ những năm 1990 với hàng chục ngôi nhà vườn cổ kính trên 80 năm tuổi.",
        ],
        "hours": "Mở cửa tự do quanh năm; các điểm tham quan đón khách 07:00 - 18:00 hàng ngày",
        "admission": "Miễn phí tham quan cù lao; vé phà An Bình 1.000 - 5.000 đ/lượt/người và xe máy",
        "travel_tip": "Từ bến phà An Bình ngay trung tâm thành phố qua sông chỉ mất 10 phút; nên thuê xe đạp dạo bộ đường làng rợp bóng mát vào sáng sớm.",
        "source_citations": [
            {
                "title": "Quy hoạch phát triển du lịch sinh thái Cù lao An Bình",
                "url": "https://vinhlongtourist.vn/cu-lao-an-binh",
                "notebook_id": "Sổ tay 1: Vĩnh Long 360",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1,
            }
        ],
    },
    "con-chim": {
        "key_facts": [
            "Ốc đảo sinh thái rộng 60 ha nằm giữa dòng sông Cổ Chiên thuộc xã Hòa Minh, phát triển mô hình du lịch cộng đồng 'thuận thiên' nổi tiếng từ năm 2019.",
            "Cư dân trên cồn tuân thủ nghiêm ngặt nhịp sinh học: mùa mặn (tháng 1 đến tháng 5) nuôi tôm cua sinh thái, mùa ngọt (tháng 6 đến tháng 12) trồng lúa hữu cơ.",
            "Nói không với túi nilon và rác thải nhựa dùng một lần, sử dụng 100% chén dĩa gốm sứ và vật liệu thân thiện môi trường.",
        ],
        "hours": "07:00 - 17:30 hàng ngày (cần đặt trước với ban quản lý du lịch cộng đồng)",
        "admission": "Vé tham quan trọn gói trải nghiệm cộng đồng 220.000 - 350.000 đ/người (bao gồm hướng dẫn viên bản địa và 5 món ăn dân dã)",
        "travel_tip": "Du khách đi phà Bà Trầm hoặc đò ngang từ bến Long Hòa mất khoảng 15 phút vượt sông Cổ Chiên để đặt chân lên đảo.",
        "source_citations": [
            {
                "title": "Khai thác du lịch sinh thái cộng đồng thuận thiên Cồn Chim",
                "url": "https://dulich.travinh.gov.vn/con-chim-sinh-thai",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1,
            }
        ],
    },
    "cu-lao-minh": {
        "key_facts": [
            "Một trong ba dải cù lao châu thổ lớn của xứ dừa, ôm trọn giữa hai nhánh đại giang Hàm Luông và Cổ Chiên với chiều dài hơn 60km.",
            "Diện tích dừa chuyên canh tập trung trên 45.000 ha, chiếm hơn 60% tổng sản lượng dừa công nghiệp toàn vùng duyên hải.",
            "Lưu giữ bề dày lịch sử phong trào Đồng Khởi năm 1960 cùng các di tích lịch sử và chuỗi làng nghề chế biến chỉ xơ dừa xuất khẩu.",
        ],
        "hours": "Mở cửa tự do quanh năm",
        "admission": "Miễn phí tham quan các trục đường nông thôn và cù lao",
        "travel_tip": "Cung đường dọc Tỉnh lộ 882 và Quốc lộ 57 chạy dọc sống lưng Cù lao Minh rất thoáng rộng, lý tưởng cho các chuyến phượt xe máy ngắm rừng dừa.",
        "source_citations": [
            {
                "title": "Địa chí địa phương - Địa lý và kinh tế Cù lao Minh",
                "url": "https://bentre.gov.vn/dia-chi/cu-lao-minh",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1,
            }
        ],
    },
    "cu-lao-long-tri": {
        "key_facts": [
            "Cù lao phù sa xanh mướt rộng hơn 330 ha nằm giữa dòng sông Cổ Chiên thuộc xã Long Đức, chỉ cách trung tâm thị xã khoảng 3km đường thủy.",
            "Vùng chuyên canh trái cây nhiệt đới màu mỡ với các loại đặc sản trứ danh: nhãn long, cam xoàn, bưởi da xanh và dưa hấu bãi bồi.",
            "Sở hữu hệ sinh thái rừng bần ngập nước tự nhiên bao bọc ven sông, là nơi trú ngụ của nhiều loài thủy sản nước ngọt và chim di cư.",
        ],
        "hours": "07:00 - 17:30 hàng ngày",
        "admission": "Miễn phí tham quan; vé đò ngang qua cù lao 5.000 - 10.000 đ/người",
        "travel_tip": "Nên ghé thăm vào khoảng từ tháng 6 đến tháng 9 âm lịch đúng dịp thu hoạch nhãn long và chôm chôm chín rộ khắp các nhà vườn.",
        "source_citations": [
            {
                "title": "Đề án phát triển du lịch sinh thái Cù lao Long Trị",
                "url": "https://dulich.travinh.gov.vn/cu-lao-long-tri",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1,
            }
        ],
    },
    "con-tan-qui": {
        "key_facts": [
            "Hình thành giữa dòng sông Hậu thuộc xã An Phú Tân với diện tích tự nhiên hơn 500 ha, đất đai màu mỡ nhờ lượng phù sa bồi đắp quanh năm.",
            "Thủ phủ măng cụt, chôm chôm và sầu riêng với những gốc măng cụt cổ thụ trên 60 năm tuổi cho quả ngọt thanh ráo múi.",
            "Hàng năm vào dịp Tết Đoan Ngọ (mùng 5 tháng 5 âm lịch), cồn thu hút hàng vạn lượt du khách tham gia Ngày hội Trái cây ven sông.",
        ],
        "hours": "06:30 - 18:00 hàng ngày",
        "admission": "Vé đò qua cồn 5.000 - 10.000 đ/lượt; vé vào vườn trái cây ăn bao bụng 50.000 - 80.000 đ/người",
        "travel_tip": "Có hai bến phà đưa khách qua cồn từ bờ An Phú Tân hoặc từ bờ Cù Lao Mây, đường sá trên cồn được bê tông hóa hoàn toàn rất dễ đi.",
        "source_citations": [
            {
                "title": "Quy hoạch phát triển vùng chuyên canh cây ăn trái Cồn Tân Qui",
                "url": "https://dulich.travinh.gov.vn/con-tan-qui",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1,
            }
        ],
    },
    "con-oc": {
        "key_facts": [
            "Cồn cát phù sa lớn trên sông Hàm Luông thuộc xã Hưng Phong, dài hơn 8,3km với diện tích tự nhiên trên 640 ha.",
            "Bạt ngàn rặng dừa dứa, dừa xiêm xanh và bưởi da xanh chất lượng cao được tưới tắm dòng nước ngọt quanh năm từ sông Cửu Long.",
            "Gắn liền với các cơ sở thủ công chế tác đồ gia dụng từ thân và gáo dừa già độc đáo với hơn 50 sản phẩm thủ công mỹ nghệ.",
        ],
        "hours": "07:00 - 18:00 hàng ngày",
        "admission": "Miễn phí tham quan cảnh quan cồn; vé phà Hưng Phong 3.000 - 5.000 đ/lượt",
        "travel_tip": "Nên thưởng thức nước dừa dứa Cồn Ốc tại vườn vì dừa trồng ở vùng nước lợ nhẹ pha phù sa nơi đây có mùi thơm lá dứa nồng nàn đặc trưng.",
        "source_citations": [
            {
                "title": "Tiềm năng du lịch sinh thái nông nghiệp Cồn Ốc Hưng Phong",
                "url": "https://bentre.gov.vn/du-lich/con-oc",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1,
            }
        ],
    },
    "con-ho": {
        "key_facts": [
            "Cồn đất tự nhiên rộng gần 30 ha nổi lên giữa dòng sông Cổ Chiên thuộc xã Đức Mỹ, bảo tồn nếp sinh hoạt nguyên sơ không điện lưới quốc gia.",
            "Người dân địa phương phát triển sản phẩm du lịch 'đèn dầu sông nước' độc đáo từ năm 2020, đón khách trải nghiệm không gian đêm hoài niệm.",
            "Đất đai màu mỡ thích hợp trồng bưởi da xanh hữu cơ, hoa đậu biếc và nuôi cá lăng, cá hô tự nhiên dưới các mương vườn.",
        ],
        "hours": "Đón khách tour trải nghiệm từ 15:00 đến 21:00 hàng ngày (cần đặt trước)",
        "admission": "Giá tour trải nghiệm trọn gói 250.000 - 400.000 đ/người (gồm chèo xuồng, ẩm thực đêm đèn dầu và ngắm đom đóm)",
        "travel_tip": "Du khách tập trung tại bến tàu Đức Mỹ để đi xuồng máy khoảng 10 phút sang cồn; nên sạc đầy pin điện thoại và máy ảnh trước khi qua cồn.",
        "source_citations": [
            {
                "title": "Mô hình du lịch tự thân về đêm tại Cồn Hô",
                "url": "https://dulich.travinh.gov.vn/con-ho-tu-than",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1,
            }
        ],
    },
    "con-phu-da": {
        "key_facts": [
            "Cồn bãi bồi rộng hơn 250 ha trên sông Cổ Chiên thuộc xã Vĩnh Bình, nổi danh khắp miệt vườn là 'thủ phủ ốc gạo' tự nhiên nước ngọt.",
            "Khu vực nước chảy xiết và đáy cát pha phù sa tạo môi trường sống lý tưởng cho loài ốc gạo vỏ trắng ruột béo ngậy sinh sôi.",
            "Nhiều vườn cây trái xanh tốt quanh năm: chôm chôm tiến vua, nhãn xuồng và sầu riêng hạt lép với sản lượng hàng trăm tấn mỗi năm.",
        ],
        "hours": "07:00 - 18:00 hàng ngày",
        "admission": "Miễn phí tham quan cù lao; vé đò ngang 5.000 đ/lượt",
        "travel_tip": "Mùa ốc gạo Cồn Phú Đa béo ngậy nhất từ tháng 4 đến tháng 7 âm lịch; món bánh xèo ốc gạo Phú Đa là đặc sản nhất định phải thử.",
        "source_citations": [
            {
                "title": "Bảo tồn nguồn lợi ốc gạo tự nhiên Cồn Phú Đa",
                "url": "https://bentre.gov.vn/thuy-san/oc-gao-con-phu-da",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1,
            }
        ],
    },
    "con-quy-song-tien-chau-thanh-ben-tre": {
        "key_facts": [
            "Hình thành từ đầu thế kỷ 20 giữa sông Tiền thuộc xã Tân Thạch, một trong cụm tứ linh cồn Long - Lân - Quy - Phụng trứ danh.",
            "Diện tích nguyên thủy khoảng 65 ha, được bồi đắp liên tục bởi phù sa sông Tiền tạo nên những liếp vườn bưởi, cam sành và nhãn sum suê.",
            "Phát triển các mô hình du lịch sinh thái nông nghiệp, câu cá giải trí và biểu diễn đờn ca tài tử phục vụ khách trong nước và quốc tế.",
        ],
        "hours": "07:30 - 17:30 hàng ngày",
        "admission": "Vé vào cổng các khu du lịch trên cồn 30.000 - 50.000 đ/người; tour tàu đưa đón từ 80.000 đ/người",
        "travel_tip": "Du khách thường kết hợp tham quan Cồn Quy cùng Cồn Phụng trong tour đường sông nửa ngày xuất phát từ bến tàu du lịch Mỹ Tho hoặc bến đò Rạch Miễu.",
        "source_citations": [
            {
                "title": "Cụm du lịch tứ linh Long Lân Quy Phụng sông Tiền",
                "url": "https://bentre.gov.vn/du-lich/con-quy",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1,
            }
        ],
    },
    "con-tam-hiep-dao-tam-hiep": {
        "key_facts": [
            "Cồn đảo phù sa xanh ngát rộng trên 1.100 ha nằm giữa bốn bề sông Ba Lai thuộc xã Tam Hiệp, được mệnh danh là vương quốc nhãn xuồng.",
            "Địa thế cô lập với đất liền giúp nơi đây giữ trọn không khí trong lành, cây trái ngọt lành nhờ tầng đất phù sa cổ màu mỡ.",
            "Vùng chuyên canh nhãn tiêu da bò và nhãn xuồng cơm vàng với diện tích hơn 500 ha cho năng suất vượt trội đạt tiêu chuẩn VietGAP.",
        ],
        "hours": "Mở cửa tự do phục vụ cư dân và du khách",
        "admission": "Miễn phí tham quan; vé phà Tam Hiệp 5.000 đ/xe máy/lượt",
        "travel_tip": "Nên thuê xe máy hoặc xe đạp chạy dọc con đường đê bao quanh cồn dài 12km rợp bóng dừa để tận hưởng luồng gió mát rượi từ sông Ba Lai.",
        "source_citations": [
            {
                "title": "Quy hoạch phát triển kinh tế sinh thái xã đảo Tam Hiệp",
                "url": "https://bentre.gov.vn/kinh-te/dao-tam-hiep",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1,
            }
        ],
    },
    "con-cai-ga": {
        "key_facts": [
            "Hình thành giữa dòng sông Cổ Chiên thuộc xã Long Thới, sở hữu diện tích tự nhiên hơn 100 ha với vi khí hậu quanh năm trong lành.",
            "Vùng đất trù phú chuyên ươm tạo cây giống ăn trái và hoa kiểng chất lượng cao phục vụ các tỉnh đồng bằng sông Cửu Long.",
            "Bao quanh bờ cồn là dải rừng bần nước lợ tự nhiên chắn sóng, nơi sinh sống của các loài cá bống cát, cá thòi lòi và tôm bạc.",
        ],
        "hours": "07:00 - 17:30 hàng ngày",
        "admission": "Miễn phí tham quan; vé đò ngang dân sinh 5.000 đ/lượt",
        "travel_tip": "Đường làng trên cồn uốn lượn dưới các tán bưởi da xanh và sầu riêng râm mát, rất phù hợp cho các chuyến dạo bộ khám phá nông thôn bản địa.",
        "source_citations": [
            {
                "title": "Tiềm năng du lịch miệt vườn sông nước Cồn Cái Gà",
                "url": "https://bentre.gov.vn/du-lich/con-cai-ga",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1,
            }
        ],
    },
    "bai-bien-con-bung-thanh-hai": {
        "key_facts": [
            "Bãi biển phù sa hoang sơ dài hơn 15km thuộc xã Thạnh Hải, tiếp giáp cửa sông Hàm Luông và Biển Đông mênh mông lộng gió.",
            "Địa hình bãi bồi thoải rộng với rừng phi lao chắn sóng xanh ngắt, nổi tiếng là vùng khai thác ốc viết, cua biển và nghêu sò tự nhiên dồi dào.",
            "Là điểm kết nối quan trọng của Tuyến đường Hồ Chí Minh trên biển với các đoàn tàu không số cập bến an toàn trong thời kỳ kháng chiến.",
        ],
        "hours": "Mở cửa tự do 24/7",
        "admission": "Miễn phí tham quan; tắm nước ngọt 10.000 - 20.000 đ/người",
        "travel_tip": "Vào mùa gió chướng từ tháng 10 đến tháng 2 âm lịch, bãi biển xuất hiện từng đụn ốc viết dài hàng cây số, du khách có thể tự tay nhặt ốc luộc sả ngay trên bờ cát.",
        "source_citations": [
            {
                "title": "Quy hoạch phát triển du lịch sinh thái biển Cồn Bửng Thạnh Hải",
                "url": "https://bentre.gov.vn/du-lich/bien-con-bung",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1,
            }
        ],
    },
    "bien-thua-duc": {
        "key_facts": [
            "Bãi biển tự nhiên dài hơn 8km thuộc xã Thừa Đức ven cửa Đại sông Tiền, sở hữu dải rừng dương phòng hộ chắn gió cát cổ thụ.",
            "Bãi cát phù sa mịn thoai thoải không có đá ngầm, nguồn lợi hải sản dồi dào với các bãi nghêu thương phẩm xuất khẩu rộng hàng trăm hecta.",
            "Khu vực tập trung nhiều quán hải sản tươi sống phục vụ nghêu hấp sả, cua biển rang me và sò huyết nướng mọi vừa đánh bắt từ biển.",
        ],
        "hours": "06:00 - 18:30 hàng ngày",
        "admission": "Miễn phí vào bãi biển; giữ xe máy 5.000 đ/lượt",
        "travel_tip": "Hải sản ở biển Thừa Đức tươi ngon và giá cả bình dân; nên ghé quán thưởng thức nghêu luộc ngay trên bãi cát lúc xế chiều mát mẻ.",
        "source_citations": [
            {
                "title": "Khai thác tài nguyên bãi nghêu và du lịch biển Thừa Đức",
                "url": "https://bentre.gov.vn/du-lich/bien-thua-duc",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1,
            }
        ],
    },
    "bien-con-nhan": {
        "key_facts": [
            "Dải cồn cát ven biển dài hơn 6km thuộc xã Đông Hải, giữ vị trí phên dậu sinh thái che chắn cửa sông Cổ Chiên trước sóng gió biển Đông.",
            "Môi trường sống tự nhiên lý tưởng của hàng nghìn cá thể chim nhạn biển, bồ nông chân xám và các loài chim di trú về làm tổ.",
            "Rừng phi lao và rừng ngập mặn bao bọc bãi bồi phù sa, nơi sinh sản tự nhiên của nghêu lụa, sò huyết và vọp rừng ngập mặn.",
        ],
        "hours": "Mở cửa tự do quanh năm",
        "admission": "Miễn phí tham quan cảnh quan thiên nhiên",
        "travel_tip": "Thời điểm lý tưởng nhất để ngắm các đàn nhạn biển chao lượn trên mặt sóng là từ 05:30 đến 07:00 sáng lúc mặt trời vừa nhô lên từ đường chân trời.",
        "source_citations": [
            {
                "title": "Hệ sinh thái bãi bồi ven biển Cồn Nhàn duyên hải",
                "url": "https://dulich.travinh.gov.vn/con-nhan-dong-hai",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1,
            }
        ],
    },
    "khu-bao-ton-thien-nhien-dat-ngap-nuoc-vam-ho": {
        "key_facts": [
            "Khu bảo tồn loài - sinh cảnh rộng hơn 67 ha nằm ven sông Ba Lai thuộc xã Mỹ Hòa, thành lập năm 2001 nhằm bảo tồn hệ sinh thái rừng ngập mặn.",
            "Nơi cư trú tự nhiên của hơn 84 loài chim hoang dã quý hiếm với ước tính khoảng 500.000 cá thể cò trắng, cồng cộc, quắm đen và vạc xám.",
            "Thảm thực vật đặc trưng với rừng chà là gai, bần chua, cóc kèn và dừa nước mọc ken dày tạo thành tổ ấm an toàn cho muôn loài chim sinh sản.",
        ],
        "hours": "06:30 - 17:30 hàng ngày",
        "admission": "Vé vào cổng tham quan 40.000 đ/người lớn, 20.000 đ/trẻ em; đi thuyền ngắm chim 80.000 đ/người",
        "travel_tip": "Khoảnh khắc kỳ thú nhất diễn ra từ 16:30 đến 17:30 khi hàng vạn cánh cò trắng rợp trời bay về tổ sau một ngày kiếm ăn dọc các cánh đồng châu thổ.",
        "source_citations": [
            {
                "title": "Đề án bảo tồn đa dạng sinh học Sân chim Vàm Hồ",
                "url": "https://bentre.gov.vn/moi-truong/san-chim-vam-ho",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1,
            }
        ],
    },
    "khu-bao-ve-canh-quan-thanh-phu-ben-tre": {
        "key_facts": [
            "Khu bảo tồn đất ngập nước ven biển rộng hơn 2.500 ha thuộc địa bàn các xã Thạnh Phong, Thạnh Hải và Giao Thạnh ven vịnh bờ biển Đông.",
            "Lưu giữ dải rừng đước, mắm nguyên sinh quý giá có chức năng phòng hộ bờ biển, chống xói lở và bảo vệ nguồn nước ngầm ngọt cho vùng bán đảo.",
            "Môi trường sống của hàng trăm loài động vật hoang dã, thủy hải sản nước lợ và các bãi đẻ quan trọng của rùa biển, vích quý hiếm.",
        ],
        "hours": "07:00 - 17:00 các ngày trong tuần (liên hệ ban quản lý rừng phòng hộ)",
        "admission": "Miễn phí cho nghiên cứu khoa học và tham quan tuyến sinh thái có hướng dẫn",
        "travel_tip": "Nên đi theo các tuyến đường ván gỗ xuyên rừng đước để quan sát hệ thống rễ thở chằng chịt và các loài cua biển, cá thòi lòi leo cây.",
        "source_citations": [
            {
                "title": "Bảo tồn cảnh quan rừng ngập mặn đất ngập nước Thạnh Phú",
                "url": "https://bentre.gov.vn/moi-truong/bao-ton-thanh-phu",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1,
            }
        ],
    },
    "rung-ngap-man-long-vinh-duyen-hai": {
        "key_facts": [
            "Quần thể rừng phòng hộ ngập mặn ven biển rộng hơn 1.200 ha tại xã Long Vĩnh, hình thành bức tường xanh kiên cố bảo vệ đê biển trước bão lũ.",
            "Cây đước đôi, bần chua và mắm trắng phát triển ngút ngàn với những bộ rễ cọc vươn sâu giữ đất bồi phù sa mỗi năm lấn biển từ 15 đến 25m.",
            "Là vựa thủy sản sinh thái nước lợ phong phú cung cấp giống tôm sú tự nhiên, cua biển gạch son và vọp rừng ngập mặn cho ngư dân quanh vùng.",
        ],
        "hours": "Mở cửa tự do tham quan cảnh quan ngoại vi 24/7",
        "admission": "Miễn phí tham quan",
        "travel_tip": "Đi cano hoặc vỏ lãi luồn lách qua các lạch nước ngập mặn vào buổi chiều mát là trải nghiệm kỳ thú để tìm hiểu sự sống rừng ven biển.",
        "source_citations": [
            {
                "title": "Hệ thống rừng phòng hộ ven biển Long Vĩnh Duyên Hải",
                "url": "https://dulich.travinh.gov.vn/rung-ngap-man-long-vinh",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1,
            }
        ],
    },
    "song-co-chien-doan-mang-thit": {
        "key_facts": [
            "Nhánh chính của sông Tiền đổ ra biển Đông, đoạn qua địa bàn Mang Thít mở rộng từ 1,2 đến 1,8km với lưu lượng dòng chảy phù sa dồi dào.",
            "Hai bên bờ sông là trung tâm di sản lò gạch gốm trăm năm với hàng trăm vòm lò gạch nung đất sét đỏ soi bóng cổ kính xuống mặt nước.",
            "Vùng nước ngọt sâu thuận lợi cho nghề nuôi cá lồng bè truyền thống với hàng trăm bè nuôi cá điêu hồng, cá tra cá lăng xuất khẩu chất lượng cao.",
        ],
        "hours": "Mở cửa tự do cảnh quan sông nước quanh năm",
        "admission": "Miễn phí ngắm cảnh từ bờ kè; thuê thuyền ngắm lò gạch từ 300.000 - 600.000 đ/chuyến",
        "travel_tip": "Khoảnh khắc ngắm hoàng hôn ráng vàng soi bóng lên các vòm lò gạch đỏ ven sông Cổ Chiên từ 17:00 đến 17:45 là tuyệt cảnh nhiếp ảnh.",
        "source_citations": [
            {
                "title": "Quy hoạch cảnh quan sông Cổ Chiên và Di sản Đương đại Mang Thít",
                "url": "https://vinhlongtourist.vn/song-co-chien-mang-thit",
                "notebook_id": "Sổ tay 1: Vĩnh Long 360",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1,
            }
        ],
    },
    "song-long-ho-vinh-long": {
        "key_facts": [
            "Dòng thủy lộ lịch sử dài hơn 16km bắt nguồn từ sông Tiền chảy qua trung tâm tỉnh lỵ và hợp lưu với các kênh rạch tỏa đi muôn phương.",
            "Nơi ghi dấu sự nghiệp khai hoang mở cõi và xây dựng Thành Long Hồ từ năm 1732 thời Chúa Nguyễn, trung tâm kinh tế chính trị phương Nam thuở xưa.",
            "Dọc hai bờ sông là quần thể di tích lịch sử - văn hóa đậm đặc: Văn Thánh Miếu, đình Long Hồ và các ngôi nhà cổ bằng gỗ căm xe hàng trăm năm tuổi.",
        ],
        "hours": "Mở cửa tự do cảnh quan công cộng 24/7",
        "admission": "Miễn phí tham quan bờ kè và công viên ven sông",
        "travel_tip": "Bờ kè sông Long Hồ được xây dựng công viên hoa rực rỡ, thích hợp đi dạo bộ ngắm nhìn thuyền ghe chở hoa trái xuôi ngược vào buổi sáng sớm.",
        "source_citations": [
            {
                "title": "Lịch sử Thành Long Hồ và lưu vực sông Long Hồ",
                "url": "https://vinhlongtourist.vn/song-long-ho",
                "notebook_id": "Sổ tay 1: Vĩnh Long 360",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1,
            }
        ],
    },
    "kenh-thay-cai-vinh-long": {
        "key_facts": [
            "Tuyến kênh đào chiến lược dài hơn 12km đào thủ công từ đầu thế kỷ 20 nối liền sông Long Hồ với sông Mang Thít và sông Măng Thít.",
            "Tạo trục giao thông thủy huyết mạch vận chuyển đất sét, củi trấu và thành phẩm gạch ngói cho hàng nghìn miệng lò nung đỏ lửa dọc hai bờ.",
            "Đóng vai trò quan trọng trong việc tháo chua rửa mặn, cung cấp nguồn phù sa dồi dào cho hàng nghìn hecta vườn cây ăn trái quanh lưu vực.",
        ],
        "hours": "Mở cửa tự do cảnh quan 24/7",
        "admission": "Miễn phí tham quan",
        "travel_tip": "Nên chọn cung đường bộ chạy dọc theo bờ kênh Thầy Cai để chiêm ngưỡng cận cảnh nhịp sống lao động nhộn nhịp của các phu bốc vác gạch ngói.",
        "source_citations": [
            {
                "title": "Hệ thống kênh đào thủy lợi và vận tải gạch gốm Vĩnh Long",
                "url": "https://vinhlongtourist.vn/kenh-thay-cai",
                "notebook_id": "Sổ tay 1: Vĩnh Long 360",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1,
            }
        ],
    },
    "kenh-tra-on-vinh-long": {
        "key_facts": [
            "Tuyến đường thủy huyết mạch dài hơn 15km đào từ năm 1905 kết nối trực tiếp sông Tiền qua sông Măng Thít với sông Hậu.",
            "Mỗi ngày đón nhận hàng trăm lượt sà lan tải trọng lớn vận chuyển lúa gạo, cát sỏi phù sa và nông sản tỏa đi khắp các tỉnh thành Nam Bộ.",
            "Gắn liền với địa danh Chợ nổi Trà Ôn nổi tiếng nhóm họp từ rạng sáng ngay khúc quanh giao nhau giữa kênh Trà Ôn và dòng sông Hậu.",
        ],
        "hours": "Mở cửa tự do 24/7",
        "admission": "Miễn phí ngắm cảnh từ bờ kè xã Trà Côn",
        "travel_tip": "Để ngắm khung cảnh chợ nổi và ghe thuyền buôn bán sầm uất trên kênh Trà Ôn, du khách nên có mặt tại bến đò lúc 05:30 sáng.",
        "source_citations": [
            {
                "title": "Lịch sử thủy lộ kênh Trà Ôn và chợ nổi sông Hậu",
                "url": "https://vinhlongtourist.vn/kenh-tra-on",
                "notebook_id": "Sổ tay 1: Vĩnh Long 360",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1,
            }
        ],
    },
    "song-ham-luong-ben-tre": {
        "key_facts": [
            "Phân lưu quan trọng của sông Tiền dài hơn 70km, chảy uốn lượn qua các vùng dừa bạt ngàn rồi đổ ra Biển Đông qua cửa Hàm Luông rộng 3km.",
            "Độ sâu trung bình từ 12 đến 15m với lưu lượng nước ngọt khổng lồ, là nguồn sống cung cấp tưới tiêu cho hơn 70.000 ha dừa và cây ăn trái nhiệt đới.",
            "Chứng nhân lịch sử kiên cường trong phong trào cách mạng, nơi in dấu những chiến công huyền thoại của Đội quân Tóc dài năm 1960.",
        ],
        "hours": "Mở cửa tự do ngắm cảnh 24/7",
        "admission": "Miễn phí",
        "travel_tip": "Tại công viên bờ kè sông Hàm Luông lộng gió, du khách có thể thuê tàu du lịch ngắm cảnh hoàng hôn buông xuống mặt sông mênh mông.",
        "source_citations": [
            {
                "title": "Hệ thống thủy văn sông Hàm Luông và lưu vực kinh tế",
                "url": "https://bentre.gov.vn/thuy-van/song-ham-luong",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1,
            }
        ],
    },
    "song-ba-lai-ben-tre": {
        "key_facts": [
            "Dòng sông dài hơn 55km tách ra từ sông Mỹ Tho chảy giữa hai cù lao An Hóa và Bảo, nổi tiếng với công trình cống đập Ba Lai xây dựng năm 2002.",
            "Đập ngăn mặn Ba Lai dài 544m tạo nên hồ chứa nước ngọt nội địa rộng lớn phục vụ sản xuất nông nghiệp và sinh hoạt cho hàng vạn hộ dân.",
            "Hệ sinh thái chuyển tiếp độc đáo giữa vùng ngọt hóa thượng lưu và vùng sinh thái cửa biển mặn lợ hạ lưu với nhiều loài chim nước cư ngụ.",
        ],
        "hours": "Mở cửa tự do ngắm cảnh 24/7",
        "admission": "Miễn phí tham quan mặt đập và bờ sông",
        "travel_tip": "Khu vực cống đập Ba Lai là điểm ngắm toàn cảnh dòng sông và cửa biển rất khoáng đạt, có thể kết hợp ghé thăm các vườn dừa dứa kế bên.",
        "source_citations": [
            {
                "title": "Công trình thủy lợi cống đập Ba Lai ngọt hóa bán đảo",
                "url": "https://bentre.gov.vn/thuy-loi/dap-ba-lai",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1,
            }
        ],
    },
    "song-thom-diem-tham-quan-lang-nghe": {
        "key_facts": [
            "Thủy lộ tự nhiên dài hơn 15km nối sông Tiền và sông Hàm Luông, được mệnh danh là 'thung lũng chế biến dừa' sôi động nhất xứ dừa.",
            "Dọc hai bờ sông quy tụ hơn 400 cơ sở và doanh nghiệp chế biến xơ dừa, ép dầu dừa, sản xuất than gáo dừa và dệt thảm xuất khẩu sang hơn 30 quốc gia.",
            "Cảnh tượng hàng trăm sà lan và ghe bầu tải trọng hàng trăm tấn chở đầy ắp dừa khô vàng ươm tấp nập cập bến bốc dỡ ngày đêm.",
        ],
        "hours": "06:30 - 18:00 hàng ngày (các xưởng hoạt động từ 07:00 - 17:00)",
        "admission": "Miễn phí tham quan ngắm cảnh sông và các làng nghề",
        "travel_tip": "Có thể đứng trên cầu Mỏ Cày hoặc đi xuồng dọc sông Thom để chụp lại những bức ảnh chân thực về trung tâm giao thương dừa nhộn nhịp.",
        "source_citations": [
            {
                "title": "Cụm công nghiệp làng nghề sông Thom Mỏ Cày",
                "url": "https://bentre.gov.vn/kinh-te/lang-nghe-song-thom",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1,
            }
        ],
    },
    "kenh-bong-bot-tra-vinh": {
        "key_facts": [
            "Kênh thủy lợi quan trọng dài hơn 18km nối dòng sông Hậu với hệ thống sông nhánh nội đồng vùng đất Cầu Kè màu mỡ.",
            "Đưa nguồn nước ngọt phù sa vô tận thau chua rửa phèn cho vùng chuyên canh dừa sáp, măng cụt và chuối tá quạ đạt năng suất cao.",
            "Hai bên bờ kênh là nơi sinh sống đan xen hòa thuận của ba dân tộc Kinh, Khmer và Hoa với những nét văn hóa ẩm thực phong phú.",
        ],
        "hours": "Mở cửa tự do cảnh quan 24/7",
        "admission": "Miễn phí tham quan",
        "travel_tip": "Cung đường bê tông nông thôn dọc bờ kênh Bông Bót rợp bóng dừa xiêm và hoa quỳnh anh vàng rực, rất thích hợp đạp xe dạo cảnh thôn quê.",
        "source_citations": [
            {
                "title": "Hạ tầng thủy lợi và phát triển cây ăn trái kênh Bông Bót",
                "url": "https://dulich.travinh.gov.vn/kenh-bong-bot",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1,
            }
        ],
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


def apply_batch13_enrichment(entities: list[dict]) -> tuple[int, list[dict]]:
    """Apply Batch 13 natural wonders data enrichment."""
    logs = []
    count = 0
    for entity in entities:
        eid = entity.get("id")
        if eid in BATCH13_DATA:
            attrs = entity.setdefault("attributes", {})
            payload = BATCH13_DATA[eid]
            attrs["key_facts"] = payload["key_facts"]
            attrs["hours"] = payload["hours"]
            attrs["admission"] = payload["admission"]
            attrs["travel_tip"] = payload["travel_tip"]
            attrs["source_citations"] = payload["source_citations"]
            attrs["verified"] = True
            attrs["verifiedAt"] = "2026-09-19"
            count += 1
            logs.append({"id": eid, "name": entity.get("name"), "status": "enriched"})
    return count, logs


def main() -> None:
    """Execute Batch 13 enrichment."""
    data = load_dataset()
    entities = data.get("entities", [])
    count, logs = apply_batch13_enrichment(entities)
    save_dataset(data)

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump({"updated_count": count, "enriched": logs}, f, ensure_ascii=False, indent=2)

    print(f"Successfully enriched {count} / {len(BATCH13_DATA)} natural wonders in Batch 13.")


if __name__ == "__main__":
    main()
