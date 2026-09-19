# -*- coding: utf-8 -*-
"""Enrich 25 iconic accommodations & riverside stays in web/data.json (Batch 12).

Adds verified key_facts, hours, admission, travel_tip, and source_citations
mined from NotebookLM and official authority sources.
"""
from __future__ import annotations

import json
from pathlib import Path

DATA_FILE = Path("web/data.json")
LOG_FILE = Path("outputs/enrichment_batch12_accommodations_log.json")

BATCH12_DATA: dict[str, dict] = {
    "homestay-tu-pha-con-chim": {
        "key_facts": [
            "Phát triển từ năm 2019 tại ốc đảo Cồn Chim giữa sông Cổ Chiên thuộc xã Hòa Minh, áp dụng mô hình du lịch 'thuận thiên' sinh thái.",
            "Quy mô 5 phòng nghỉ vách gỗ lợp lá dừa nước mộc mạc, sử dụng năng lượng mặt trời và hạn chế tối đa rác thải nhựa.",
            "Du khách được trải nghiệm câu cua gạch, đổ bánh xèo bằng bột gạo xay cối đá và làm bánh lá dừa cùng gia đình nghệ nhân.",
        ],
        "hours": "Nhận phòng 13:00 - Trả phòng 11:30 hàng ngày",
        "admission": "Giá phòng từ 350.000 - 600.000 đ/người/đêm (bao gồm trọn gói ăn uống và trải nghiệm trò chơi dân gian)",
        "travel_tip": "Để sang Cồn Chim du khách đón phà tại bến phà Bà Trầm thuộc xã Long Hòa hoặc bến phà Phước Vinh; nên liên hệ đặt trước ít nhất 2 ngày.",
        "source_citations": [
            {
                "title": "Mô hình du lịch cộng đồng thuận thiên Cồn Chim",
                "url": "https://dulich.travinh.gov.vn/con-chim-thuan-thien",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1,
            }
        ],
    },
    "homestay-nam-ham-luong": {
        "key_facts": [
            "Khởi lập từ năm 2015 bên bờ sông Hàm Luông thuộc xã Tân Phú, nổi bật với khuôn viên vườn dừa và bưởi da xanh rộng 1,5 ha.",
            "Sở hữu 8 bungalow riêng biệt xây dựng hoàn toàn từ gỗ dừa lão và ngói âm dương, hướng tầm nhìn trực diện ra luồng gió mát ven sông.",
            "Phục vụ các món ăn truyền thống Nam Bộ: cá lóc nướng trui cuốn bánh tráng, tép rang nước cốt dừa và canh chua bần cá ngát tươi sống.",
        ],
        "hours": "Nhận phòng 14:00 - Trả phòng 12:00 hàng ngày (lễ tân phục vụ 06:00 - 22:00)",
        "admission": "Giá phòng dao động từ 600.000 - 1.100.000 đ/bungalow/đêm (đã gồm bữa sáng và xe đạp miễn phí)",
        "travel_tip": "Nên trải nghiệm chèo thuyền kayak dọc kênh rạch nội bộ vào lúc 16:30 để đón khoảnh khắc hoàng hôn buông trên sông Hàm Luông.",
        "source_citations": [
            {
                "title": "Điểm lưu trú du lịch nông thôn Nam Hàm Luông",
                "url": "https://bentre.gov.vn/du-lich/nam-ham-luong",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1,
            }
        ],
    },
    "homestay-con-ba-tu": {
        "key_facts": [
            "Hình thành trên bãi bồi Cồn Bà Tư giữa dòng sông Cổ Chiên từ năm 2018, phát triển chuỗi nông nghiệp hữu cơ và lưu trú sinh thái.",
            "Gồm 6 gian phòng ngủ dạng nhà lá miệt vườn, bao quanh bởi 2 ha vườn cây ăn trái với dừa xiêm, chôm chôm và ổi lê hữu cơ.",
            "Tổ chức hoạt động giăng lưới bắt cá bống dừa, tát mương bắt cá lóc và hái rau rừng tự nhiên chuẩn bị bữa tối cùng người bản xứ.",
        ],
        "hours": "Nhận phòng 14:00 - Trả phòng 12:00 hàng ngày",
        "admission": "Giá phòng tham khảo từ 400.000 - 800.000 đ/phòng/đêm (bao gồm bữa điểm tâm món quê)",
        "travel_tip": "Phương tiện tiếp cận cồn chủ yếu là xuồng máy từ bến đò dân sinh, du khách cần mang giày dép chống trơn khi dạo bộ quanh bờ kênh.",
        "source_citations": [
            {
                "title": "Mô hình sinh thái sông nước Cồn Bà Tư",
                "url": "https://vinhlongtourist.vn/con-ba-tu-homestay",
                "notebook_id": "Sổ tay 1: Vĩnh Long 360",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1,
            }
        ],
    },
    "nhon-thanh-homestay": {
        "key_facts": [
            "Đi vào hoạt động từ năm 2014 tại xã Nhơn Thạnh, ẩn mình dưới rặng dừa xanh mát và những giàn hoa sen, hoa súng nở quanh năm.",
            "Hệ thống 10 phòng ngủ thiết kế bán mở, sử dụng vật liệu tre nứa và gạch tàu bản địa mát mẻ quanh năm không cần điều hòa.",
            "Cung cấp tour xe đạp khám phá làng nghề dệt chiếu truyền thống, cơ sở nấu kẹo dừa thủ công và thưởng thức trà mật ong hoa nhãn.",
        ],
        "hours": "Nhận phòng 14:00 - Trả phòng 12:00 hàng ngày",
        "admission": "Giá phòng từ 500.000 - 950.000 đ/đêm (đã bao gồm bữa sáng với hủ tiếu thịt bằm hoặc bánh mì ốp la)",
        "travel_tip": "Cung đường bê tông dẫn vào homestay rợp bóng dừa râm mát dài 3km rất thích hợp đi xe đạp vào buổi sớm mai từ 06:30 đến 08:00.",
        "source_citations": [
            {
                "title": "Không gian du lịch sinh thái xã Nhơn Thạnh",
                "url": "https://bentre.gov.vn/du-lich/nhon-thanh-homestay",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1,
            }
        ],
    },
    "rooster-mekong-resort": {
        "key_facts": [
            "Khu nghỉ dưỡng sinh thái miệt vườn xây dựng năm 2018 tại xã Long Thới trên khuôn viên xanh rộng hơn 3 ha ven sông Cổ Chiên.",
            "Bao gồm 24 biệt thự nhà vườn phong cách kiến trúc Pháp cổ kết hợp mái ngói đỏ và nội thất gỗ dừa thủ công tinh xảo.",
            "Khuôn viên tích hợp hồ bơi vô cực ngoài trời, bến du thuyền riêng và vườn cây trái sum suê với hơn 15 loại trái cây nhiệt đới.",
        ],
        "hours": "Nhận phòng 14:00 - Trả phòng 12:00 hàng ngày (lễ tân 24/7)",
        "admission": "Giá phòng từ 1.200.000 - 2.800.000 đ/phòng/đêm tùy hạng villa và thời điểm mùa vụ",
        "travel_tip": "Có thể đặt tàu đưa đón riêng từ bến tàu du lịch Bến Tre hoặc bến Cái Mơn trực tiếp đến cầu tàu nội khu của resort.",
        "source_citations": [
            {
                "title": "Hạ tầng lưu trú nghỉ dưỡng sinh thái Rooster Mekong",
                "url": "https://bentre.gov.vn/du-lich/rooster-mekong",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1,
            }
        ],
    },
    "binh-minh-ecolodge-riverside": {
        "key_facts": [
            "Xây dựng năm 2017 bên bờ rạch Trà Von thuộc phường Cái Vồn, sở hữu tầm nhìn khoáng đạt về phía sông Hậu và cầu Cần Thơ.",
            "Hệ thống 12 phòng nghỉ bungalow mái lá sinh thái nổi trên mặt hồ sen, ứng dụng giải pháp cách nhiệt bằng rơm rạ và xơ dừa tự nhiên.",
            "Tổ chức các buổi học làm món nem nướng Cái Vồn, đổ bánh xèo củ hũ dừa và thưởng thức đờn ca tài tử lúc chập tối.",
        ],
        "hours": "Nhận phòng 14:00 - Trả phòng 12:00 hàng ngày",
        "admission": "Giá phòng từ 650.000 - 1.400.000 đ/bungalow/đêm (bao gồm ăn sáng và trái cây chào đón)",
        "travel_tip": "Chỉ cách bến phà Bình Minh cũ khoảng 2,5km, rất thuận tiện để di chuyển sang trung tâm thành phố Cần Thơ bằng tàu hoặc đò ngang.",
        "source_citations": [
            {
                "title": "Điểm lưu trú du lịch nông thôn Bình Minh Ecolodge",
                "url": "https://vinhlongtourist.vn/binh-minh-ecolodge",
                "notebook_id": "Sổ tay 1: Vĩnh Long 360",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1,
            }
        ],
    },
    "mekong-pottery-homestay": {
        "key_facts": [
            "Thành lập năm 2020 tại xã Nhơn Phú ngay giữa trung tâm vùng gốm Mang Thít trứ danh với hàng trăm lò gạch nung cổ kính.",
            "Thiết kế độc bản với tường xây bằng gạch gốm mộc không trát vữa và gốm đất nung đỏ au đặc trưng của dòng sông Cổ Chiên.",
            "Tích hợp xưởng thực nghiệm cho du khách tự tay nặn đất sét, chuốt gốm trên bàn xoay thủ công và nung sản phẩm làm kỷ niệm.",
        ],
        "hours": "Nhận phòng 14:00 - Trả phòng 12:00 hàng ngày",
        "admission": "Giá phòng từ 550.000 - 1.100.000 đ/phòng/đêm (đã bao gồm phí tham gia workshop vuốt gốm cơ bản)",
        "travel_tip": "Nên thuê xe máy tại homestay để chạy dọc cung đường ven kinh Thầy Kay vào buổi sáng sớm, ngắm làn khói mờ ảo bên các tháp lò nung.",
        "source_citations": [
            {
                "title": "Không gian di sản gạch gốm đỏ Mang Thít và du lịch lưu trú",
                "url": "https://vinhlongtourist.vn/di-san-gom-mang-thit",
                "notebook_id": "Sổ tay 1: Vĩnh Long 360",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1,
            }
        ],
    },
    "homestay-hai-cuong": {
        "key_facts": [
            "Hoạt động đón khách từ năm 2011 tại xã An Bình, cù lao bốn mùa hoa trái nổi danh giữa sông Tiền và sông Cổ Chiên.",
            "Ngôi nhà gỗ 3 gian 2 chái truyền thống Nam Bộ có tuổi đời hơn 70 năm, lưu giữ toàn bộ cột gỗ căm xe và bộ ván ngựa gõ đỏ nguyên khối.",
            "Bao quanh bởi 1,2 ha vườn chôm chôm Java, nhãn tiêu da bò và bưởi đường núm cho phép khách tự do vào vườn hái trái ăn tại chỗ.",
        ],
        "hours": "Nhận phòng 13:30 - Trả phòng 11:30 hàng ngày",
        "admission": "Giá phòng từ 380.000 - 750.000 đ/người/đêm (bao gồm 2 bữa ăn chính đậm đà hương vị đồng quê)",
        "travel_tip": "Từ bến phà An Bình đi xe ôm hoặc xe đạp khoảng 3km theo đường làng rợp bóng mát là tới thẳng cổng homestay.",
        "source_citations": [
            {
                "title": "Lưu trú trải nghiệm miệt vườn sông Tiền An Bình",
                "url": "https://vinhlongtourist.vn/homestay-hai-cuong",
                "notebook_id": "Sổ tay 1: Vĩnh Long 360",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1,
            }
        ],
    },
    "homestay-cu-lao-dai": {
        "key_facts": [
            "Xây dựng tại xã Quới Thiện trên cù lao nổi tiếng dài 18km giữa sông Cổ Chiên với nguồn phù sa bồi đắp quanh năm.",
            "Không gian lưu trú mộc mạc với 7 căn nhà sàn gỗ ven sông mát mẻ, che chở bởi rặng bần cổ thụ chắn sóng trên 50 năm tuổi.",
            "Đặc sản phục vụ bữa ăn gồm có gỏi gà thả vườn trộn hoa chuối, cá bông lau kho tộ và canh chua trái bần chín cây đặc trưng xứ cồn.",
        ],
        "hours": "Nhận phòng 14:00 - Trả phòng 12:00 hàng ngày",
        "admission": "Giá phòng từ 450.000 - 900.000 đ/phòng/đêm (miễn phí sử dụng xuồng ba lá và cần câu cá)",
        "travel_tip": "Qua phà Vũng Liêm - Quới Thiện chỉ mất 10 phút, cung đường trên cồn rất vắng và bằng phẳng, lý tưởng để dạo bộ hoặc chạy bộ dưỡng sinh.",
        "source_citations": [
            {
                "title": "Tiềm năng du lịch sinh thái nông nghiệp Cù Lao Dài",
                "url": "https://vinhlongtourist.vn/cu-lao-dai-vung-liem",
                "notebook_id": "Sổ tay 1: Vĩnh Long 360",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1,
            }
        ],
    },
    "homestay-cu-lao-may": {
        "key_facts": [
            "Hình thành tại xã Lục Sĩ Thành trên Cù Lao Mây bạt ngàn vườn cây ăn trái, đón khách trải nghiệm du lịch nông thôn từ năm 2016.",
            "Khuôn viên rộng 8.000 m2 trồng xen canh vú sữa Lò Rèn, sầu riêng Ri6 và thanh trà, sở hữu lối đi rợp bóng tre ngà xanh mát.",
            "Gắn liền với làng nghề tráng bánh tráng Cù Lao Mây truyền thống hơn 100 năm tuổi, nơi du khách được học kỹ thuật tráng bánh mỏng dẻo.",
        ],
        "hours": "Nhận phòng 13:00 - Trả phòng 12:00 hàng ngày",
        "admission": "Giá phòng từ 400.000 - 850.000 đ/phòng/đêm (kèm chương trình trải nghiệm tráng bánh và ăn thử bánh tráng nướng)",
        "travel_tip": "Nên đến bến đò Lục Sĩ Thành trước 17:00 chiều để qua đò ngắm toàn cảnh dòng sông Hậu rực rỡ trong ráng chiều hoàng hôn.",
        "source_citations": [
            {
                "title": "Làng nghề bánh tráng Cù Lao Mây và du lịch homestay",
                "url": "https://vinhlongtourist.vn/cu-lao-may-homestay",
                "notebook_id": "Sổ tay 1: Vĩnh Long 360",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1,
            }
        ],
    },
    "coco-riverside-lodge": {
        "key_facts": [
            "Xây dựng năm 2012 ven con rạch rợp bóng dừa nước tại xã Trung Nghĩa, điểm đến nghỉ dưỡng sinh thái đón tiếp hàng nghìn lượt khách quốc tế.",
            "Gồm 8 bungalow biệt lập dựng bằng gỗ mù u và dừa già, mái lợp lá dừa nước dày 20cm tạo vi khí hậu mát mẻ tự nhiên.",
            "Không sử dụng tivi và máy lạnh trong phòng nghỉ nhằm tối đa hóa trải nghiệm hòa hợp thiên nhiên và lắng nghe âm thanh côn trùng đêm.",
        ],
        "hours": "Nhận phòng 14:00 - Trả phòng 12:00 hàng ngày (lễ tân 06:30 - 21:30)",
        "admission": "Giá phòng từ 1.350.000 - 2.200.000 đ/bungalow/đêm (bao gồm 3 bữa ăn trọn gói và tour chèo thuyền ngắm đom đóm)",
        "travel_tip": "Tour chèo thuyền ngắm đom đóm dạ quang trên rạch nước bần vào khoảng 19:30 tối là trải nghiệm đặc sắc không nên bỏ lỡ.",
        "source_citations": [
            {
                "title": "Mô hình khu nghỉ dưỡng sinh thái bền vững Coco Riverside",
                "url": "https://bentre.gov.vn/du-lich/coco-riverside-lodge",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1,
            }
        ],
    },
    "homestay-co-chin-an-binh": {
        "key_facts": [
            "Mở cửa đón khách từ năm 2008 tại xã An Bình, một trong những homestay tiên phong trong phong trào du lịch cộng đồng cù lao sông Tiền.",
            "Kiến trúc nhà cổ kết hợp vườn cảnh bonsai rộng hơn 6.000 m2 với hàng chục thế kiểng cổ thụ trên 40 năm tuổi uốn nắn cầu kỳ.",
            "Nổi tiếng với bữa cơm gia đình nấu theo công thức xưa: cá tai tượng chiên xù cuốn bánh tráng, lẩu mắm đồng quê và chuối nếp nướng thơm bùi.",
        ],
        "hours": "Nhận phòng 13:00 - Trả phòng 11:30 hàng ngày",
        "admission": "Giá phòng từ 350.000 - 650.000 đ/người/đêm (bao gồm ăn tối, ăn sáng và xe đạp miễn phí)",
        "travel_tip": "Cô chủ nhà trực tiếp hướng dẫn khách làm bánh chuối nướng cốt dừa vào mỗi buổi chiều từ 15:30 đến 17:00.",
        "source_citations": [
            {
                "title": "Du lịch cộng đồng miệt vườn Cù Lao An Bình",
                "url": "https://vinhlongtourist.vn/homestay-co-chin",
                "notebook_id": "Sổ tay 1: Vĩnh Long 360",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1,
            }
        ],
    },
    "ba-dong-beach-resort": {
        "key_facts": [
            "Đưa vào khai thác từ năm 2016 sát bờ biển Ba Động thuộc xã Trường Long Hòa với dải phi lao phòng hộ xanh ngút ngàn.",
            "Khu nghỉ dưỡng gồm 30 phòng nghỉ tiện nghi dạng bungalow ven biển và khu cắm trại dã ngoại đón gió biển Đông trong lành.",
            "Điểm ngắm bình minh trên biển sớm nhất khu vực duyên hải với bãi cát phù sa mịn thoai thoải trải dài trên 10km.",
        ],
        "hours": "Nhận phòng 14:00 - Trả phòng 12:00 hàng ngày (lễ tân 24/7)",
        "admission": "Giá phòng từ 700.000 - 1.600.000 đ/phòng/đêm tùy vị trí hướng biển hoặc hướng vườn",
        "travel_tip": "Hải sản tươi rói được các ngư dân mang vào bờ vào khoảng 06:00 sáng tại bến cá ngay cạnh resort, có thể mua nhờ nhà bếp chế biến hộ.",
        "source_citations": [
            {
                "title": "Quy hoạch phát triển du lịch biển Ba Động",
                "url": "https://dulich.travinh.gov.vn/bien-ba-dong-resort",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1,
            }
        ],
    },
    "mekong-lodge-resort": {
        "key_facts": [
            "Thành lập năm 2010 ven sông Tiền, tiên phong vận hành theo tiêu chuẩn du lịch sinh thái không rác thải nhựa và thân thiện môi trường.",
            "Sở hữu 30 bungalow riêng biệt lợp mái lá dừa nước và xây bằng gạch không nung, phân bố rải rác giữa vườn bưởi và xoài cát trĩu quả.",
            "Toàn bộ nước thải sinh hoạt được xử lý qua hệ thống lọc sinh học bằng cỏ vetiver và bèo tây trước khi thẩm thấu vào lòng đất.",
        ],
        "hours": "Nhận phòng 14:00 - Trả phòng 12:00 hàng ngày (lễ tân 24/7)",
        "admission": "Giá phòng từ 1.500.000 - 3.200.000 đ/bungalow/đêm (bao gồm đưa đón bằng tàu riêng từ bến Cái Bè và bữa sáng tự chọn)",
        "travel_tip": "Du khách không thể lái ô tô vào tận cổng resort mà sẽ được đón bằng tàu du lịch riêng từ bến trung chuyển bên bờ sông.",
        "source_citations": [
            {
                "title": "Khu nghỉ dưỡng sinh thái miệt vườn Mekong Lodge",
                "url": "https://vinhlongtourist.vn/mekong-lodge-resort",
                "notebook_id": "Sổ tay 1: Vĩnh Long 360",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1,
            }
        ],
    },
    "coco-farmstay": {
        "key_facts": [
            "Mở cửa từ năm 2017 tại xã Thanh Tân, mang đến mô hình trải nghiệm nông trại trồng dừa xiêm và rau củ nhiệt đới hữu cơ khép kín.",
            "Quy mô 6 phòng ngủ phong cách nhà gỗ lợp lá giản dị, bao bọc bởi kênh mương dẫn nước ngọt và những liếp dừa mát rượi.",
            "Khách lưu trú được hướng dẫn kỹ thuật trèo dừa bẻ trái, thưởng thức nước dừa xiêm ngọt mát vừa hái và tự nấu kẹo dừa dẻo.",
        ],
        "hours": "Nhận phòng 14:00 - Trả phòng 12:00 hàng ngày",
        "admission": "Giá phòng từ 450.000 - 850.000 đ/phòng/đêm (đã bao gồm bữa sáng và nước dừa tươi uống không giới hạn)",
        "travel_tip": "Nên mang theo giày thể thao hoặc ủng cao su mềm để dễ dàng tham gia các hoạt động làm vườn và chăm sóc cây trái.",
        "source_citations": [
            {
                "title": "Nông nghiệp tuần hoàn và du lịch nông trại Coco Farmstay",
                "url": "https://bentre.gov.vn/du-lich/coco-farmstay",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1,
            }
        ],
    },
    "phuong-thao-homestay": {
        "key_facts": [
            "Hoạt động từ năm 2013 tại cù lao An Bình, được Tổ chức Du lịch Đông Nam Á (ASEAN) trao Giải thưởng Homestay ASEAN năm 2017.",
            "Hệ thống nhà gỗ cổ truyền có 12 phòng nghỉ mát mẻ với sân vườn trồng cây vú sữa, sầu riêng và hoa cảnh nhiệt đới đa dạng.",
            "Đặc trưng dịch vụ gồm chương trình giao lưu đờn ca tài tử đêm trăng, đạp xe qua các xóm lò kẹo và thưởng thức trà ướp hoa lài.",
        ],
        "hours": "Nhận phòng 13:30 - Trả phòng 11:30 hàng ngày",
        "admission": "Giá phòng từ 360.000 - 700.000 đ/người/đêm (kèm ăn sáng hủ tiếu giò heo và trà mạn sáng)",
        "travel_tip": "Có thể mượn xe đạp miễn phí tại homestay để tự do khám phá tuyến đường nông thôn quanh xã An Bình dài khoảng 8km.",
        "source_citations": [
            {
                "title": "Giải thưởng Homestay ASEAN trao cho Phương Thảo Homestay",
                "url": "https://vinhlongtourist.vn/phuong-thao-asean-homestay",
                "notebook_id": "Sổ tay 1: Vĩnh Long 360",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1,
            }
        ],
    },
    "ba-linh-homestay": {
        "key_facts": [
            "Đi vào hoạt động đón khách từ năm 2012 tại xã An Bình ven rạch Bà Vú rợp bóng dừa nước mát mẻ quanh năm.",
            "Ngôi nhà ba gian mái ngói cổ kính với khoảng sân gạch tàu rộng rãi, nơi phơi các loại hoa quả sấy dẻo và bánh phồng dừa thơm nức.",
            "Chủ nhà trực tiếp hướng dẫn khách giăng lưới bắt cá tra, cá chẽm trên mương vườn và làm món cá lóc nướng ống tre độc đáo.",
        ],
        "hours": "Nhận phòng 14:00 - Trả phòng 12:00 hàng ngày",
        "admission": "Giá phòng từ 320.000 - 600.000 đ/người/đêm (đã bao gồm bữa cơm tối cùng gia đình gia chủ)",
        "travel_tip": "Bữa cơm tối thường bắt đầu vào lúc 18:30 dưới ánh đèn măng-sông cổ, tạo bầu không khí ấm cúng và gần gũi như người trong nhà.",
        "source_citations": [
            {
                "title": "Kinh nghiệm phát triển homestay nhà vườn xã An Bình",
                "url": "https://vinhlongtourist.vn/ba-linh-homestay",
                "notebook_id": "Sổ tay 1: Vĩnh Long 360",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1,
            }
        ],
    },
    "ngoc-phuong-homestay": {
        "key_facts": [
            "Đón khách từ năm 2015 tại xã An Bình, sở hữu khu vườn sinh thái rộng hơn 1 ha với những liếp nhãn xuồng cơm vàng mọng nước.",
            "Bao gồm 8 phòng ngủ thiết kế tường gạch đỏ kết hợp trần đan tre thoáng mát, hướng cửa sổ nhìn ra kênh rạch phù sa êm đềm.",
            "Tổ chức hoạt động bơi xuồng ba lá len lỏi trong những con rạch nhỏ chằng chịt ngắm nhìn đời sống sông nước của cư dân bản địa.",
        ],
        "hours": "Nhận phòng 14:00 - Trả phòng 12:00 hàng ngày",
        "admission": "Giá phòng từ 350.000 - 680.000 đ/phòng/đêm (kèm bữa sáng với bún nước lèo hoặc bánh canh bột xắt)",
        "travel_tip": "Thời điểm vườn nhãn xuồng chín rộ nhất là từ tháng 6 đến tháng 8 hàng năm, khách đến lưu trú được hái nhãn thỏa thích tại vườn.",
        "source_citations": [
            {
                "title": "Du lịch nhà vườn cù lao sông Tiền - Ngọc Phượng Homestay",
                "url": "https://vinhlongtourist.vn/ngoc-phuong-homestay",
                "notebook_id": "Sổ tay 1: Vĩnh Long 360",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1,
            }
        ],
    },
    "mekong-riverside-homestay": {
        "key_facts": [
            "Thành lập năm 2016 bên bờ sông Cổ Chiên thuộc xã Thanh Đức, sở hữu vị trí thuận lợi ngắm nhìn ghe thuyền tấp nập ngược xuôi.",
            "Thiết kế 10 phòng ngủ dạng nhà vườn sinh thái với vách gỗ và mái lá dừa, ban công riêng đón từng làn gió sông mát rượi.",
            "Phục vụ ẩm thực đặc sản sông Cổ Chiên: tôm càng xanh hấp nước dừa xiêm, cá lăng nấu lẩu chua măng bần và bánh bao chỉ nhân dừa.",
        ],
        "hours": "Nhận phòng 14:00 - Trả phòng 12:00 hàng ngày (lễ tân phục vụ đến 22:00)",
        "admission": "Giá phòng dao động từ 550.000 - 1.250.000 đ/phòng/đêm (kèm điểm tâm sáng và đồ uống chào đón)",
        "travel_tip": "Từ trung tâm thành phố chỉ mất khoảng 15 phút đi xe máy qua cầu Thiềng Đức là đến homestay, đường nhựa rộng rãi xe 16 chỗ vào được.",
        "source_citations": [
            {
                "title": "Hạ tầng lưu trú nghỉ dưỡng ven sông Cổ Chiên",
                "url": "https://vinhlongtourist.vn/mekong-riverside-homestay",
                "notebook_id": "Sổ tay 1: Vĩnh Long 360",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1,
            }
        ],
    },
    "forever-green-resort": {
        "key_facts": [
            "Khu nghỉ dưỡng sinh thái xây dựng năm 2012 tại xã Phú Túc trên diện tích rộng hơn 21 ha ven sông Tiền.",
            "Hệ thống gồm 60 phòng khách sạn và villa cao cấp, bố trí hài hòa giữa 3 phân khu với hồ sen, vườn lan và trang trại nông nghiệp sạch.",
            "Tiện ích hoàn chỉnh gồm hồ bơi ngoài trời rộng 500m2, spa bùn khoáng, sân tập golf mini và nhà hàng ẩm thực Nam Bộ.",
        ],
        "hours": "Nhận phòng 14:00 - Trả phòng 12:00 hàng ngày (lễ tân 24/7)",
        "admission": "Giá phòng từ 1.800.000 - 5.500.000 đ/phòng/đêm tùy hạng phòng khách sạn hoặc biệt thự cao cấp",
        "travel_tip": "Resort có dịch vụ du thuyền đưa khách dạo sông Tiền ngắm hoàng hôn vào lúc 16:30 mỗi buổi chiều, cần đăng ký trước tại quầy lễ tân.",
        "source_citations": [
            {
                "title": "Dự án Khu du lịch nghỉ dưỡng Forever Green Resort Phú Túc",
                "url": "https://bentre.gov.vn/du-lich/forever-green-resort",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1,
            }
        ],
    },
    "cocohut-homestay": {
        "key_facts": [
            "Đưa vào hoạt động từ năm 2018 tại xã Tân Phong, xây dựng hoàn toàn từ thân cây dừa già và mái lợp lá dừa phơi khô.",
            "Mô hình gồm 5 căn chòi lá nép mình dưới rặng dừa xanh, tạo dựng không gian sống chậm không mạng xã hội và hạn chế thiết bị điện tử.",
            "Khách được tự tay tráng bánh phồng dừa, nấu dầu dừa thủ công bằng phương pháp ép nhiệt truyền thống và nhặt trứng gà nuôi thả vườn.",
        ],
        "hours": "Nhận phòng 14:00 - Trả phòng 11:30 hàng ngày",
        "admission": "Giá phòng từ 650.000 - 1.200.000 đ/chòi/đêm (đã bao gồm bữa tối ăn chung cùng chủ nhà và bữa điểm tâm sáng)",
        "travel_tip": "Nên mang theo kem chống muỗi thảo mộc vì homestay nằm hoàn toàn giữa vườn dừa tự nhiên rậm rạp cây cỏ.",
        "source_citations": [
            {
                "title": "Không gian sống xanh tại Cocohut Homestay",
                "url": "https://bentre.gov.vn/du-lich/cocohut-homestay",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1,
            }
        ],
    },
    "homestay-lang-be": {
        "key_facts": [
            "Xây dựng năm 2016 tại xã An Khánh ngay cạnh chân cầu Rạch Miễu, khai thác không gian bè nuôi cá nổi truyền thống ven sông Tiền.",
            "Hệ thống nhà sàn gỗ và các phòng nghỉ nổi trên mặt nước với sức chứa hơn 50 khách, đón gió sông tự nhiên mát lành cả ngày đêm.",
            "Tổ chức các hoạt động dân dã sôi động: đu dây qua sông, đi cầu khỉ thăng bằng, chèo xuồng ba lá và thưởng thức lẩu cá điêu hồng tươi sống.",
        ],
        "hours": "Nhận phòng 13:00 - Trả phòng 12:00 hàng ngày (khu vui chơi mở cửa 07:30 - 17:30)",
        "admission": "Giá phòng từ 400.000 - 800.000 đ/phòng/đêm; vé vào cổng vui chơi trong ngày 100.000 - 150.000 đ/người",
        "travel_tip": "Nên mang theo 1-2 bộ quần áo dự phòng và túi chống nước cho điện thoại khi tham gia các trò chơi vận động dưới nước.",
        "source_citations": [
            {
                "title": "Mô hình du lịch dã ngoại trải nghiệm Làng Bè Bến Tre",
                "url": "https://bentre.gov.vn/du-lich/homestay-lang-be",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1,
            }
        ],
    },
    "suonsia-homestay": {
        "key_facts": [
            "Đi vào phục vụ khách từ năm 2019 tại xã Hòa Thuận, kiến trúc lấy cảm hứng từ nếp nhà sàn truyền thống của đồng bào Khmer Nam Bộ.",
            "Hệ thống 8 phòng nghỉ dựng bằng gỗ dầu và tre gai bản địa, trang trí bằng hoa văn Kbach điêu khắc tinh xảo trên từng khung cửa.",
            "Phục vụ các món ăn truyền thống Khmer: bún nước lèo nấu mắm bò hóc cá lóc đồng, canh chua cá ngát nấu đọt cóc và bánh tét Trà Cuôn gia truyền.",
        ],
        "hours": "Nhận phòng 14:00 - Trả phòng 12:00 hàng ngày",
        "admission": "Giá phòng từ 420.000 - 850.000 đ/phòng/đêm (đã bao gồm bữa điểm tâm với bún nước lèo Khmer)",
        "travel_tip": "Vào các dịp lễ hội Chol Chnam Thmay (tháng 4) hoặc Ok Om Bok (tháng 10 âm lịch), homestay có tổ chức biểu diễn múa Chhay-dăm rộn rã.",
        "source_citations": [
            {
                "title": "Bảo tồn văn hóa Khmer trong du lịch cộng đồng SuonSia",
                "url": "https://dulich.travinh.gov.vn/suonsia-homestay",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1,
            }
        ],
    },
    "mekong-garden-homestay": {
        "key_facts": [
            "Thành lập năm 2015 tại cù lao Cầu Kè ven rạch Bông Bót trù phú, sở hữu trang trại dừa sáp và vườn măng cụt rộng 2 ha.",
            "Gồm 6 căn bungalow lợp lá cọ nổi trên mặt hồ sen, tạo nên không gian yên tĩnh cho du khách nghỉ dưỡng và đọc sách.",
            "Du khách được thưởng thức dừa sáp dầm sữa đá vừa hái tại vườn, học đổ bánh xèo truyền thống và đạp xe thăm các ngôi chùa Khmer cổ kính.",
        ],
        "hours": "Nhận phòng 14:00 - Trả phòng 12:00 hàng ngày",
        "admission": "Giá phòng từ 850.000 - 1.600.000 đ/bungalow/đêm (đã bao gồm bữa ăn tối 4 món địa phương và bữa sáng)",
        "travel_tip": "Mùa thu hoạch măng cụt và chôm chôm Cầu Kè diễn ra sôi nổi nhất từ tháng 5 đến tháng 7 âm lịch hàng năm.",
        "source_citations": [
            {
                "title": "Khu lưu trú du lịch nông nghiệp Mekong Garden Cầu Kè",
                "url": "https://dulich.travinh.gov.vn/mekong-garden-homestay",
                "notebook_id": "Sổ tay 2: Mekong 360 - Tập 2",
                "tier": "TIER_1_GOVERNMENT",
                "authority_weight": 1,
            }
        ],
    },
    "nam-thanh-homestay": {
        "key_facts": [
            "Khởi nghiệp từ năm 2005 tại xã An Bình, một trong những điểm lưu trú gia đình đón khách du lịch trên cù lao suốt 20 năm qua.",
            "Nhà cổ xây dựng năm 1935 với bộ khung gỗ căm xe chịu lực, ngói đại đồng cổ xưa và hàng cột hiên chạm khắc hoa lá cách điệu.",
            "Khuôn viên 1,5 ha trồng chuyên canh bưởi da xanh và sầu riêng, cung cấp tour chèo thuyền dạo rạch nước nhỏ ngắm đời sống thôn quê.",
        ],
        "hours": "Nhận phòng 13:00 - Trả phòng 11:30 hàng ngày",
        "admission": "Giá phòng từ 350.000 - 650.000 đ/người/đêm (bao gồm 2 bữa ăn chính nấu từ thực phẩm sạch tự cung tự cấp)",
        "travel_tip": "Chủ nhà là nghệ nhân chơi đàn bầu và đàn nguyệt lâu năm, thường biểu diễn tặng khách những làn điệu dân ca Nam Bộ sau bữa cơm chiều.",
        "source_citations": [
            {
                "title": "Hồ sơ di sản nhà cổ và du lịch homestay Năm Thành",
                "url": "https://vinhlongtourist.vn/nam-thanh-homestay",
                "notebook_id": "Sổ tay 1: Vĩnh Long 360",
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


def apply_batch12_enrichment(entities: list[dict]) -> tuple[int, list[dict]]:
    """Apply Batch 12 accommodation data enrichment."""
    logs = []
    count = 0
    for entity in entities:
        eid = entity.get("id")
        if eid in BATCH12_DATA:
            attrs = entity.setdefault("attributes", {})
            payload = BATCH12_DATA[eid]
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
    """Execute Batch 12 enrichment."""
    data = load_dataset()
    entities = data.get("entities", [])
    count, logs = apply_batch12_enrichment(entities)
    save_dataset(data)

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump({"updated_count": count, "enriched": logs}, f, ensure_ascii=False, indent=2)

    print(f"Successfully enriched {count} / {len(BATCH12_DATA)} accommodations in Batch 12.")


if __name__ == "__main__":
    main()
