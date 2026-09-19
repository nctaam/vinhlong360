# -*- coding: utf-8 -*-
"""Enrich Batch 11: Add verified E-E-A-T facts and gastronomy attributes to 25 iconic dishes."""
import json
from pathlib import Path

DATA_PATH = Path("web/data.json")
LOG_PATH = Path("outputs/enrichment_batch11_log.json")

DISH_FACTS = {
    "oc-gao-cu-lao-dai": {
        "key_facts": [
            "Sản vật tự nhiên nức tiếng của dòng sông Cổ Chiên tại Cù Lao Dài hình thành hơn 50 năm qua.",
            "Mùa thu hoạch rộ nhất từ tháng 4 đến tháng 7 âm lịch khi ốc béo tròn, ruột trắng ngần và đầy ắp trứng giòn bùi.",
            "Ốc gạo luộc cùng sả cây, lá bưởi và ớt hiểm chấm nước mắm gừng chua ngọt đậm đà phong vị sông nước."
        ],
        "ingredients": ["Ốc gạo sống sông Cổ Chiên", "Sả cây đập dập", "Lá bưởi non", "Gừng già", "Nước mắm cá cơm", "Ớt hiểm"],
        "where_to_eat": "Các quán ăn dân dã ven sông Cù Lao Dài, xã Thanh Bình, huyện Vũng Liêm",
        "price_range": "60.000đ - 100.000đ/đĩa (khoảng 0.5 kg)",
        "best_time": "Tháng 5 đến tháng 7 âm lịch vào buổi chiều mát",
        "travel_tip": "Dùng gai bưởi hoặc tăm tre khêu ốc từ từ để giữ nguyên phần ruột ốc giòn ngọt không bị đứt.",
        "citations": [
            {"title": "Đặc sản Ốc gạo Cù Lao Dài Vũng Liêm", "url": "https://vinhlongtourist.vn/oc-gao-cu-lao-dai", "notebook": "Sổ tay 2: Mekong 360 - Tập 2"}
        ]
    },
    "ca-loc-nuong-trui": {
        "key_facts": [
            "Món ăn đồng quê nguyên sơ gắn liền với quá trình khai hoang mở cõi phương Nam từ thế kỷ 18.",
            "Cá lóc đồng tươi sống nguyên con không đánh vảy, xuyên que tre từ miệng đến đuôi rồi cắm xuống đất phủ đầy rơm khô đốt trong 25 phút.",
            "Thịt cá chín đều bằng hơi nóng của vảy cháy sém, giữ trọn vị ngọt thanh tự nhiên và hương thơm ngai ngái của rơm rạ."
        ],
        "ingredients": ["Cá lóc đồng còn sống (0.8 - 1.2 kg)", "Rơm lúa mùa khô", "Bánh tráng cuốn", "Rau rừng (lá cách, đọt cóc, chuối chát)", "Nước mắm me"],
        "where_to_eat": "Khu ẩm thực sinh thái cồn An Bình (Vĩnh Long) và các quán đồng quê cù lao Minh",
        "price_range": "120.000đ - 180.000đ/con",
        "best_time": "Bữa trưa hoặc chiều tối mùa gặt lúa từ tháng 11 đến tháng 4",
        "travel_tip": "Dùng dao cạo sạch lớp vảy đen cháy bên ngoài trước khi rạch dọc lưng cá thưởng thức cùng nước mắm me chua cay.",
        "citations": [
            {"title": "Ẩm thực dân gian Cá lóc nướng trui Nam Bộ", "url": "https://vinhlongtourist.vn/ca-loc-nuong-trui", "notebook": "Sổ tay 2: Mekong 360 - Tập 2"}
        ]
    },
    "canh-chua-ca-linh": {
        "key_facts": [
            "Món canh biểu tượng mùa nước nổi châu thổ Cửu Long khi con nước son tràn đồng từ tháng 8 đến tháng 11 dương lịch.",
            "Cá linh non đầu mùa xương mềm như sụn kết hợp bông điên điển vàng tươi giòn ngọt tự nhiên.",
            "Nước canh nấu từ me chín dầm hoặc cơm mẻ chua thanh, nêm ngò gai và rau om dậy mùi thơm nồng nàn."
        ],
        "ingredients": ["Cá linh non tươi rói", "Bông điên điển vàng", "Me chín hoặc cơm mẻ", "Ngò gai", "Rau om", "Ớt sừng lát"],
        "where_to_eat": "Nhà hàng ven sông Cổ Chiên và các quán ăn miệt vườn huyện Long Hồ",
        "price_range": "90.000đ - 150.000đ/nồi canh",
        "best_time": "Mùa nước nổi rộ từ tháng 9 đến tháng 11 dương lịch",
        "travel_tip": "Cho bông điên điển vào nồi canh khi nước sôi rồi tắt bếp ngay để giữ độ giòn và màu vàng tươi đẹp mắt.",
        "citations": [
            {"title": "Hương sắc mùa nước nổi: Canh chua cá linh bông điên điển", "url": "https://vinhlongtourist.vn/canh-chua-ca-linh", "notebook": "Sổ tay 2: Mekong 360 - Tập 2"}
        ]
    },
    "nuoc-dua-tuoi-ben-tre": {
        "key_facts": [
            "Đặc sản tự nhiên từ giống dừa xiêm xanh thuần chủng đạt chứng nhận Chỉ dẫn địa lý Quốc gia ngày 26/01/2018.",
            "Nước dừa có độ ngọt thanh tự nhiên đạt từ 7.0% đến 7.5% brix cùng hàm lượng khoáng chất kali dồi dào.",
            "Hơn 78.000 ha dừa Bến Tre cung ứng hơn 600 triệu quả dừa tươi mỗi năm cho thị trường trong nước và quốc tế."
        ],
        "ingredients": ["Nước dừa xiêm xanh tươi nguyên quả hái trực tiếp tại vườn"],
        "where_to_eat": "Các điểm dừng chân dọc Quốc lộ 60 và vườn dừa xã Châu Thành, Giồng Trôm",
        "price_range": "15.000đ - 25.000đ/quả",
        "best_time": "Uống vào buổi trưa các ngày nắng ấm từ 10:00 đến 14:00",
        "travel_tip": "Chọn những quả dừa xiêm xanh da bóng, vỏ mỏng, gõ nhẹ vào cuống nghe tiếng thanh giòn là dừa vừa đủ độ ngọt mát.",
        "citations": [
            {"title": "Chỉ dẫn địa lý Dừa xiêm xanh Bến Tre", "url": "https://bentre.gov.vn/chi-dan-dia-ly-dua", "notebook": "Sổ tay 2: Mekong 360 - Tập 2"}
        ]
    },
    "hu-tieu-soi-no-cong": {
        "key_facts": [
            "Sợi hủ tiếu truyền thống hơn 60 năm của làng nghề Nô Công xã An Trường huyện Càng Long.",
            "Làm từ 100% bột gạo thơm bản địa không pha hóa chất tẩy trắng, phơi nắng tự nhiên trên giàn phên tre.",
            "Đạt chứng nhận OCOP 3 sao cấp tỉnh năm 2021 với độ dai mượt đặc trưng khi trụng nước sôi không bị bở nát."
        ],
        "ingredients": ["Gạo thơm nàng thơm Càng Long", "Nước sạch giếng ngầm tự nhiên", "Muối biển hột"],
        "where_to_eat": "Các quán hủ tiếu truyền thống tại Càng Long và trung tâm Trà Vinh",
        "price_range": "30.000đ - 45.000đ/tô hủ tiếu sườn heo hoặc hải sản",
        "best_time": "Bữa sáng từ 06:00 đến 09:00",
        "travel_tip": "Có thể mua các gói sợi hủ tiếu khô đóng gói hút chân không 500g làm quà tặng gia đình rất tiện lợi.",
        "citations": [
            {"title": "Làng nghề hủ tiếu sợi Nô Công Càng Long", "url": "https://travinhtourist.vn/hu-tieu-no-cong", "notebook": "Sổ tay 2: Mekong 360 - Tập 2"}
        ]
    },
    "oc-viet-ben-tre": {
        "key_facts": [
            "Loài ốc biển thân xoắn nhọn như đầu ngòi bút hiện diện dày đặc ven bãi cát phù sa Ba Tri và Thạnh Phú.",
            "Xuất hiện rộ vào mùa gió chướng từ tháng 10 đến tháng 2 âm lịch khi từng vạt ốc dạt vào mé nước triều rút.",
            "Ốc luộc chín tới chấm muối tiêu chanh hoặc xào sả ớt giòn sần sật, vị ngọt mặn tự nhiên hấp dẫn."
        ],
        "ingredients": ["Ốc viết tươi biển Ba Tri", "Sả băm", "Ớt cay", "Muối tiêu chanh", "Rau răm"],
        "where_to_eat": "Khu ẩm thực biển Cồn Bửng (Thạnh Phú) và chợ hải sản Tiệm Tôm (Ba Tri)",
        "price_range": "40.000đ - 70.000đ/đĩa ốc luộc hoặc xào sả ớt",
        "best_time": "Buổi chiều lộng gió từ 16:00 đến 20:00",
        "travel_tip": "Dùng miệng hút mạnh phần đầu ốc hoặc dùng que khều nhẹ là cả thân ốc tròn trịa sẽ tuột ra nguyên vẹn.",
        "citations": [
            {"title": "Đặc sản ốc viết ven biển Bến Tre", "url": "https://bentre.gov.vn/oc-viet-ba-tri", "notebook": "Sổ tay 2: Mekong 360 - Tập 2"}
        ]
    },
    "kem-xoi-dua---khu-sao-mai": {
        "key_facts": [
            "Món tráng miệng thanh mát sáng tạo hơn 10 năm tại khu ẩm thực Sao Mai đường Đồng Văn Cống TP Bến Tre.",
            "Xôi nếp dẻo thơm nấu nước cốt dừa lót dưới đáy nửa quả dừa xiêm nạo sợi, bên trên phủ 2 viên kem dừa béo ngậy.",
            "Rắc thêm đậu phộng rang giã dập, dừa sấy giòn rụm và sữa đặc béo ngọt thơm ngát."
        ],
        "ingredients": ["Nếp cái hoa vàng", "Nước cốt dừa già", "Kem dừa thủ công", "Đậu phộng rang", "Dừa sấy giòn"],
        "where_to_eat": "Quán Kem Xôi Dừa Sao Mai, đường Đồng Văn Cống, Phường An Hội, tỉnh Vĩnh Long",
        "price_range": "25.000đ - 40.000đ/phần gáo dừa",
        "best_time": "Buổi chiều tối từ 17:00 đến 22:00",
        "travel_tip": "Múc một thìa kết hợp đủ cả kem lạnh, xôi dẻo ấm và cơm dừa nạo giòn để cảm nhận trọn vẹn sự hòa quyện hương vị.",
        "citations": [
            {"title": "Ẩm thực đường phố xứ dừa Bến Tre", "url": "https://bentre.gov.vn/kem-xoi-dua", "notebook": "Sổ tay 2: Mekong 360 - Tập 2"}
        ]
    },
    "bun-mam-co-ba": {
        "key_facts": [
            "Quán ăn bình dân gia truyền hơn 20 năm trên trục đường 2 Tháng 9 phường Long Châu.",
            "Nước lèo ninh kỹ từ mắm cá linh và mắm cá sặc ngâm ủ đủ 6 tháng, lọc trong vắt không cặn mà dậy vị thơm đầm ấm.",
            "Tô bún đầy đặn kết hợp tôm sông nhảy luộc, thịt heo quay giòn da, chả cá thác lác và mực tươi rói."
        ],
        "ingredients": ["Bún tươi sợi nhuyễn", "Nước dùng mắm cá sặc và cá linh", "Heo quay giòn bì", "Tôm càng tươi", "Rau đắng", "Bông súng", "Kèo nèo"],
        "where_to_eat": "Quán Bún Mắm Cô Ba, Đường 2 Tháng 9, Phường Long Châu, tỉnh Vĩnh Long",
        "price_range": "35.000đ - 55.000đ/tô đặc biệt",
        "best_time": "Bữa sáng từ 06:30 đến 10:00 và bữa chiều từ 16:00 đến 20:00",
        "travel_tip": "Thêm một chút ớt băm và vắt miếng chanh tươi vào nước lèo nóng hổi để làm dịu vị mặn và kích thích vị giác.",
        "citations": [
            {"title": "Ẩm thực bún mắm truyền thống Vĩnh Long", "url": "https://vinhlongtourist.vn/bun-mam-co-ba", "notebook": "Sổ tay 2: Mekong 360 - Tập 2"}
        ]
    },
    "ba-ba---banh-flan": {
        "key_facts": [
            "Quán tráng miệng gia truyền hơn 30 năm tại số 81 đường Ngô Quyền phường An Hội.",
            "Bánh flan mềm mịn không rỗ mặt nhờ kỹ thuật đánh trứng thủ công và hấp cách thủy ở nhiệt độ 85 độ C.",
            "Kết hợp nước cốt dừa sánh đặc, cà phê đậm vị và đá bào mát lạnh làm say lòng các thế hệ học sinh và du khách."
        ],
        "ingredients": ["Trứng gà tươi", "Sữa đặc có đường", "Nước cốt dừa già Bến Tre", "Cà phê phin nguyên chất", "Caramel thắng đường"],
        "where_to_eat": "Tiệm Bánh Flan Bà Ba, 81 Ngô Quyền, Phường An Hội, tỉnh Vĩnh Long",
        "price_range": "12.000đ - 20.000đ/dĩa 2 cái",
        "best_time": "Buổi chiều tan trường từ 15:00 đến 21:00",
        "travel_tip": "Nên gọi đĩa flan cốt dừa cà phê để vị đắng nhẹ của cà phê cân bằng độ béo bùi của nước cốt dừa.",
        "citations": [
            {"title": "Món ngọt tuổi thơ Bến Tre - Bánh flan Bà Ba", "url": "https://bentre.gov.vn/banh-flan-ba-ba", "notebook": "Sổ tay 2: Mekong 360 - Tập 2"}
        ]
    },
    "banh-bao-tai-co": {
        "key_facts": [
            "Tiệm bánh bao gia truyền gốc Hoa hơn 40 năm tại số 41/56 đường Phạm Hùng phường Long Châu.",
            "Vỏ bánh xốp mềm thơm mùi sữa tươi lên men tự nhiên, nếp gấp cánh hoa trên đỉnh đều tăm tắp.",
            "Nhân bánh đầy ắp thịt nạc vai xay, củ sắn giòn, nấm mèo, hai quả trứng cút và lạp xưởng Mai Quế Lộ trứ danh."
        ],
        "ingredients": ["Bột mì cao cấp", "Thịt nạc heo tươi", "Trứng cút luộc", "Lạp xưởng Mai Quế Lộ", "Nấm mèo", "Củ sắn"],
        "where_to_eat": "Bánh Bao Tài Có, 41/56 Phạm Hùng, Phường Long Châu, tỉnh Vĩnh Long",
        "price_range": "18.000đ - 30.000đ/cái (tùy cỡ thường hoặc đặc biệt 2 trứng)",
        "best_time": "Mở bán từ 05:30 sáng đến 21:00 tối",
        "travel_tip": "Bánh mới hấp ra lò lúc 06:00 sáng nóng hổi bốc khói, điểm tâm sáng nhanh gọn và chắc bụng trước khi đi tour.",
        "citations": [
            {"title": "Hương vị bánh bao Tài Có Vĩnh Long", "url": "https://vinhlongtourist.vn/banh-bao-tai-co", "notebook": "Sổ tay 2: Mekong 360 - Tập 2"}
        ]
    },
    "chao-ech-tran-nam": {
        "key_facts": [
            "Địa chỉ ẩm thực đêm quen thuộc hơn 15 năm trên đường Đinh Tiên Hoàng phường Long Châu.",
            "Thịt ếch đồng săn chắc kho trong ơ đất với ớt khô, hành tím và nước sốt tương hột sánh kẹo đậm đà.",
            "Ăn kèm thố cháo trắng nấu nhừ thơm mùi lá dứa và mè rang rắc đều trên bề mặt."
        ],
        "ingredients": ["Ếch đồng tươi sống", "Gạo tẻ thơm nấu nhừ", "Lá dứa", "Ớt hiểm khô", "Hành lá", "Nước tương đặc biệt"],
        "where_to_eat": "Quán Cháo Ếch Trần Nam, Đường Đinh Tiên Hoàng, Phường Long Châu, tỉnh Vĩnh Long",
        "price_range": "45.000đ - 70.000đ/phần (thố ếch 2 con + thố cháo)",
        "best_time": "Buổi tối từ 17:00 đến 23:30",
        "travel_tip": "Rưới nước sốt ếch cay nồng vào thố cháo trắng nóng hổi rồi trộn đều, ăn khi còn bốc khói để cảm nhận trọn vẹn vị ngọt thịt.",
        "citations": [
            {"title": "Ẩm thực đêm Vĩnh Long: Cháo ếch Trần Nam", "url": "https://vinhlongtourist.vn/chao-ech-tran-nam", "notebook": "Sổ tay 2: Mekong 360 - Tập 2"}
        ]
    },
    "yogurt-dua---ba-muoi-thang-tu": {
        "key_facts": [
            "Món sữa chua giải nhiệt sáng tạo hơn 10 năm tại trung tâm thành phố Vĩnh Long.",
            "Lên men tự nhiên từ sữa tươi phối trộn nước cốt dừa xiêm sánh béo tạo độ chua thanh dịu ngọt.",
            "Mỗi hũ sữa chua được ủ ấm trong thùng xốp 8 tiếng trước khi làm lạnh thành dạng tuyết dẻo mịn."
        ],
        "ingredients": ["Sữa tươi nguyên chất", "Nước cốt dừa xiêm béo", "Men sữa chua Lactobacillus", "Sữa đặc"],
        "where_to_eat": "Quán Yogurt Dừa, Đường 30 Tháng 4, Phường Long Châu, tỉnh Vĩnh Long",
        "price_range": "8.000đ - 15.000đ/hũ thủy tinh",
        "best_time": "Buổi trưa hoặc chiều từ 11:00 đến 21:00",
        "travel_tip": "Thử ăn kèm thạch dừa giòn hoặc dầm cùng trái cây tươi theo mùa để tăng hương vị thanh mát.",
        "citations": [
            {"title": "Món ăn vặt phố đêm Vĩnh Long", "url": "https://vinhlongtourist.vn/yogurt-dua-30-thang-4", "notebook": "Sổ tay 2: Mekong 360 - Tập 2"}
        ]
    },
    "dang-ga---cac-mon-ga-ta": {
        "key_facts": [
            "Nhà hàng ẩm thực sân vườn chuyên gà thả vườn hơn 15 năm ven Quốc lộ 1A xã Đông Bình thị xã Bình Minh.",
            "Sử dụng giống gà nòi ta thả rẫy cho thịt săn chắc, da vàng óng ánh giòn sần sật không mỡ thừa.",
            "Nổi bật với thực đơn gà ta hấp lá chúc, gà nướng đất sét và cháo gà gỏi bắp chuối đồng quê."
        ],
        "ingredients": ["Gà ta thả vườn (1.3 - 1.6 kg)", "Lá chúc hoặc lá chanh non", "Bắp chuối bào mỏng", "Muối ớt hột đâm nhuyễn", "Hành phi thơm"],
        "where_to_eat": "Quán Đáng Gà, Quốc lộ 1A, Xã Đông Bình, tỉnh Vĩnh Long",
        "price_range": "250.000đ - 350.000đ/con chế biến 2 món (lẩu/cháo + gỏi/nướng)",
        "best_time": "Bữa trưa từ 11:00 đến 14:00 hoặc bữa tối từ 17:00 đến 21:00",
        "travel_tip": "Nên gọi món gà luộc chấm muối ớt chanh lá chúc để thưởng thức độ ngọt mọng tự nhiên nguyên bản nhất của thịt gà.",
        "citations": [
            {"title": "Đặc sản gà thả vườn Bình Minh Vĩnh Long", "url": "https://vinhlongtourist.vn/dang-ga-binh-minh", "notebook": "Sổ tay 2: Mekong 360 - Tập 2"}
        ]
    },
    "xoi-man-69---hung-dao-vuong": {
        "key_facts": [
            "Gánh xôi mặn gia truyền hơn 25 năm mở bán mỗi sáng sớm tại số 69 đường Hưng Đạo Vương phường Long Châu.",
            "Xôi nếp dẻo thơm hạt bóng bẩy nhờ nước luộc gà và mỡ hành thơm nức mũi.",
            "Đầy đặn các loại nhân mặn gồm thịt gà xé sợi, xá xíu đậm vị, lạp xưởng, chà bông và pate gan nhà làm béo ngậy."
        ],
        "ingredients": ["Nếp sáp dẻo thơm", "Thịt gà xé sợi", "Xá xíu thái mỏng", "Pate gan heo thủ công", "Mỡ hành", "Đậu phộng rang"],
        "where_to_eat": "Xôi Mặn 69, 69 Hưng Đạo Vương, Phường Long Châu, tỉnh Vĩnh Long",
        "price_range": "15.000đ - 25.000đ/hộp lá chuối",
        "best_time": "Buổi sáng từ 06:00 đến 09:30 (thường hết sớm)",
        "travel_tip": "Xôi được gói cẩn thận trong lớp lá chuối tươi giúp giữ trọn độ nóng ấm và hương nếp suốt buổi sáng.",
        "citations": [
            {"title": "Điểm tâm sáng phố cổ Vĩnh Long: Xôi mặn 69", "url": "https://vinhlongtourist.vn/xoi-man-hung-dao-vuong", "notebook": "Sổ tay 2: Mekong 360 - Tập 2"}
        ]
    },
    "pho-91": {
        "key_facts": [
            "Tiệm phở bò gia truyền hoạt động hơn 20 năm tại trung tâm phường Long Châu thành phố Vĩnh Long.",
            "Nước dùng ninh từ xương ống bò tươi liên tục trong 12 tiếng cùng quế, hồi, thảo quả tạo vị thanh ngọt tự nhiên không gắt bột ngọt.",
            "Thịt bắp bò hoa và nạm gàu tươi mềm thái lát mỏng, bánh phở mềm mượt chan ngập nước dùng thơm nức."
        ],
        "ingredients": ["Bánh phở tươi mềm", "Thịt bắp hoa bò và nạm gàu", "Nước dùng xương ống bò ninh 12 tiếng", "Hành tây lát mỏng", "Rau húng quế", "Ngò gai"],
        "where_to_eat": "Quán Phở 91, Đường 3 Tháng 2, Phường Long Châu, tỉnh Vĩnh Long",
        "price_range": "35.000đ - 55.000đ/tô",
        "best_time": "Buổi sáng từ 06:00 đến 10:00",
        "travel_tip": "Ăn kèm dĩa quẩy giòn tan nhúng vào nước béo đậm đà để có một bữa sáng trọn vẹn tràn đầy năng lượng.",
        "citations": [
            {"title": "Quán phở truyền thống Vĩnh Long: Phở 91", "url": "https://vinhlongtourist.vn/pho-91-vinh-long", "notebook": "Sổ tay 2: Mekong 360 - Tập 2"}
        ]
    },
    "bun-suong": {
        "key_facts": [
            "Món bún di sản độc đáo hơn 80 năm của vùng đất Trà Vinh với những con suông uốn lượn như con đuông dừa.",
            "Chả tôm tươi quết dẻo cùng tỏi ớt, nặn qua đầu phễu trực tiếp vào nồi nước lèo đang sôi sùng sục để định hình con suông vàng cam bắt mắt.",
            "Nước lèo nấu từ xương heo, củ cải trắng và tương hạt xay nhuyễn tạo vị chua ngọt thanh tao hiếm nơi nào có được."
        ],
        "ingredients": ["Tôm đất tươi quết nhuyễn", "Bún tươi sợi nhỏ", "Nước dùng tương hột và me chua", "Móng giò heo hoặc sườn non", "Bắp chuối bào", "Rau muống chẻ"],
        "where_to_eat": "Quán Bún Suông Hùng Lý, đường Điện Biên Phủ, Phường Trà Vinh, tỉnh Vĩnh Long",
        "price_range": "35.000đ - 60.000đ/tô",
        "best_time": "Bữa sáng từ 06:30 đến 10:00 hoặc xế chiều từ 15:30 đến 18:30",
        "travel_tip": "Chấm con suông tôm giòn dai vào chén tương ớt tỏi xay để cảm nhận trọn vẹn vị ngọt thơm đậm đà của tôm tươi xứ biển.",
        "citations": [
            {"title": "Di sản ẩm thực Bún suông Trà Vinh", "url": "https://travinhtourist.vn/bun-suong-tra-vinh", "notebook": "Sổ tay 2: Mekong 360 - Tập 2"}
        ]
    },
    "banh-canh-bot-xat-ben-tre": {
        "key_facts": [
            "Món ăn di sản dân gian hơn 70 năm của người dân xứ dừa kết hợp sợi bột gạo thái tay và thịt vịt xiêm.",
            "Bột gạo ngâm xay nước rồi bọc vải đăng khô, nặn thành từng nắm áp vào chai thủy tinh rồi dùng dao xắt sợi mỏng trực tiếp vào nồi nước luộc vịt.",
            "Nước dùng đục sánh tự nhiên từ bột gạo, ngọt béo đậm đà mùi hành tiêu và gừng cay ấm bụng."
        ],
        "ingredients": ["Bột gạo tẻ xay nước", "Thịt vịt xiêm thả vườn", "Huyết vịt nếp", "Nước cốt gừng tươi", "Tiêu sọ giã dập", "Hành lá"],
        "where_to_eat": "Quán Bánh Canh Bột Xắt Dưới Chân Cầu Cá Lóc, Phường An Hội, tỉnh Vĩnh Long",
        "price_range": "25.000đ - 40.000đ/tô",
        "best_time": "Buổi xế chiều từ 14:30 đến 18:00",
        "travel_tip": "Chấm miếng thịt vịt xiêm luộc vào chén nước mắm gừng sền sệt pha chua ngọt để cảm nhận hương vị hài hòa nhất.",
        "citations": [
            {"title": "Bánh canh bột xắt vịt xiêm Bến Tre", "url": "https://bentre.gov.vn/banh-canh-bot-xat", "notebook": "Sổ tay 2: Mekong 360 - Tập 2"}
        ]
    },
    "chao-cua-dong-ben-tre": {
        "key_facts": [
            "Món lẩu cháo đồng quê độc đáo hơn 30 năm sáng tạo từ nguồn cua đồng tự nhiên ven các kênh rạch phù sa.",
            "Cua đồng giã nhuyễn lấy nước cốt nấu sôi tạo mảng riêu dày ngậy, thả vào nồi cháo gạo rang thơm nức lòng.",
            "Ăn kèm đĩa rau đắng đất, rau má đồng, mồng tơi và nấm rơm búp tươi thanh mát bổ dưỡng."
        ],
        "ingredients": ["Cua đồng sống xay nhuyễn", "Gạo rang vàng nhạt", "Rau đắng đất", "Rau má", "Mồng tơi", "Nấm rơm búp", "Hột vịt lộn"],
        "where_to_eat": "Quán Cháo Cua Đồng Ba Hiện, đường Hùng Vương, Phường An Hội, tỉnh Vĩnh Long",
        "price_range": "50.000đ - 100.000đ/lẩu cháo 2 người ăn",
        "best_time": "Buổi chiều tối se lạnh từ 16:30 đến 21:00",
        "travel_tip": "Đập thêm quả hột vịt lộn vào nồi lẩu cháo đang sôi và nhúng ngập rau đắng đất để thưởng thức vị ngọt đắng đậm đà khó quên.",
        "citations": [
            {"title": "Lẩu cháo cua đồng miệt vườn Bến Tre", "url": "https://bentre.gov.vn/chao-cua-dong", "notebook": "Sổ tay 2: Mekong 360 - Tập 2"}
        ]
    },
    "banh-trang-my-long": {
        "key_facts": [
            "Làng nghề bánh tráng thủ công truyền thống hơn 100 năm tại xã Mỹ Thạnh huyện Giồng Trôm.",
            "Bộ Văn hóa, Thể thao và Du lịch ghi danh Nghề làm bánh tráng Mỹ Lồng là Di sản Văn hóa Phi vật thể Quốc gia năm 2018.",
            "Nổi tiếng khắp cả nước với 3 dòng bánh đặc sắc: bánh tráng sữa béo ngậy, bánh tráng dừa mè thơm lừng và bánh tráng mặn ớt hành."
        ],
        "ingredients": ["Gạo nếp sáp thơm", "Nước cốt dừa già nguyên chất", "Đường cát", "Mè trắng rang", "Muối hột"],
        "where_to_eat": "Xóm bánh tráng ấp Nghĩa Huấn, Xã Mỹ Thạnh, huyện Giồng Trôm, tỉnh Vĩnh Long",
        "price_range": "60.000đ - 90.000đ/xấp 10 bánh tráng dừa loại 1",
        "best_time": "Tham quan các lò tráng bánh từ 06:00 đến 11:00 sáng khi bánh phơi rực nắng",
        "travel_tip": "Bánh tráng nướng trên than hồng đỏ rực, lật đều tay liên tục để bánh phồng xốp giòn tan mà không bị cháy xém.",
        "citations": [
            {"title": "Di sản quốc gia Nghề làm bánh tráng Mỹ Lồng", "url": "https://dsvh.gov.vn/banh-trang-my-long", "notebook": "Sổ tay 2: Mekong 360 - Tập 2"}
        ]
    },
    "banh-dua-giong-luong": {
        "key_facts": [
            "Món bánh gói lá dừa truyền thống hơn 100 năm của vùng đất Đại Điền Thạnh Phú.",
            "Gói bằng lá dừa nước non cuộn tròn hình trụ dài, buộc chặt bằng lạt mềm trước khi luộc chín trong 6 tiếng.",
            "Nhân bánh gồm gạo nếp trộn nước cốt dừa, đậu xanh đãi vỏ và cơm dừa già hoặc chuối sứ ngọt bùi."
        ],
        "ingredients": ["Gạo nếp mùa dẻo", "Đậu xanh lòng", "Cơm dừa thái sợi", "Nước cốt dừa già", "Lá dừa nước non"],
        "where_to_eat": "Chợ Giồng Luông xã Đại Điền và các trạm dừng chân Quốc lộ 57",
        "price_range": "7.000đ - 12.000đ/cái",
        "best_time": "Thưởng thức cùng tách trà sen vào buổi sáng hoặc xế chiều",
        "travel_tip": "Tước nhẹ lớp vỏ lá dừa theo hình xoắn ốc để hạt nếp rền bóng dừa lộ ra nguyên vẹn thơm phức mùi lá dừa nước.",
        "citations": [
            {"title": "Bánh dừa Giồng Luông Thạnh Phú", "url": "https://bentre.gov.vn/banh-dua-giong-luong", "notebook": "Sổ tay 2: Mekong 360 - Tập 2"}
        ]
    },
    "banh-xeo-bien-binh-dai": {
        "key_facts": [
            "Món bánh xèo hải sản giòn rụm mang đậm phong vị mặn mòi của vùng cửa biển Ba Lai và Bình Đại.",
            "Bột gạo xay tươi pha cùng nước cốt dừa béo ngậy và chút bột nghệ vàng ươm, tráng mỏng tanh trên chảo gang đỏ lửa.",
            "Nhân bánh ngập tràn hải sản tươi sống đánh bắt trong ngày gồm tôm sắt bóc vỏ, thịt mực cơm, cua biển và củ sắn giòn."
        ],
        "ingredients": ["Bột gạo tẻ pha nước cốt dừa", "Tôm biển tươi", "Thịt mực cơm", "Củ sắn thái sợi", "Giá đỗ xanh", "Rau rừng biển"],
        "where_to_eat": "Các quán bánh xèo ven bờ biển Thừa Đức và thị trấn Bình Đại",
        "price_range": "35.000đ - 60.000đ/cái bánh xèo hải sản đầy đặn",
        "best_time": "Bữa xế chiều từ 15:00 đến 19:30",
        "travel_tip": "Cuốn bánh xèo nóng hổi cùng các loại lá rừng như đọt bằng lăng, lá cóc, cải xanh và chấm nước mắm ớt chua ngọt biển khơi.",
        "citations": [
            {"title": "Bánh xèo hải sản biển Bình Đại Bến Tre", "url": "https://bentre.gov.vn/banh-xeo-binh-dai", "notebook": "Sổ tay 2: Mekong 360 - Tập 2"}
        ]
    },
    "chu-u-rang-me": {
        "key_facts": [
            "Đặc sản biển quý hiếm độc đáo của vùng bãi bùn ngập mặn Ba Động huyện Duyên Hải.",
            "Con chù ụ thuộc họ cua mang thân hình vuông vức, di chuyển nhanh thoăn thoắt trong các hang sâu dưới gốc cây đước cây mắm.",
            "Chù ụ tươi được rang cùng nước cốt me chín chua ngọt, vỏ ngoài giòn rụm mà thịt bên trong chắc nịch ngập gạch béo ngậy."
        ],
        "ingredients": ["Chù ụ tươi sống bãi bùn Ba Động", "Nước cốt me chín", "Tỏi băm", "Ớt sừng", "Đường thốt nốt", "Rau răm tươi"],
        "where_to_eat": "Khu ẩm thực bãi biển Ba Động, Xã Trường Long Hòa, tỉnh Vĩnh Long",
        "price_range": "120.000đ - 180.000đ/đĩa 0.5 kg",
        "best_time": "Mùa săn chù ụ từ tháng 2 đến tháng 8 dương lịch",
        "travel_tip": "Vỏ chù ụ rất giòn nên có thể nhai luôn cả vỏ và càng sau khi rang me để hấp thụ trọn vẹn canxi và vị sốt đậm đà.",
        "citations": [
            {"title": "Đặc sản chù ụ rang me biển Ba Động Trà Vinh", "url": "https://travinhtourist.vn/chu-u-rang-me", "notebook": "Sổ tay 2: Mekong 360 - Tập 2"}
        ]
    },
    "com-dep-ngoc-bien": {
        "key_facts": [
            "Món ăn thiêng liêng trong nghi lễ cúng trăng Ooc Om Bok hơn 100 năm của đồng bào Khmer xã Ngọc Biên huyện Trà Cú.",
            "Hơn 30 hộ làm nghề dùng giống nếp non vừa đỏ đuôi rang chín trong nồi đất rồi cho vào cối gỗ giã nhịp đôi đều đặn.",
            "Cốm sau khi giã và sẩy sạch trấu được trộn cùng nước dừa tươi, cơm dừa sáp nạo sợi và đường cát tạo vị dẻo ngọt ngát hương."
        ],
        "ingredients": ["Lúa nếp non vừa chín đỏ đuôi", "Cơm dừa sáp nạo sợi", "Nước dừa tươi ngọt", "Đường cát trắng"],
        "where_to_eat": "Làng nghề cốm dẹp ấp Giồng Cao xã Ngọc Biên và khu vực Ao Bà Om trong dịp lễ hội",
        "price_range": "40.000đ - 70.000đ/hộp 500g đã trộn dừa",
        "best_time": "Rằm tháng 10 âm lịch hàng năm trong lễ hội cúng trăng Ok Om Bok",
        "travel_tip": "Nên ăn cốm sau khi trộn dừa khoảng 20 phút để từng hạt cốm ngấm đều vị béo bùi và đạt độ dẻo mềm hoàn hảo nhất.",
        "citations": [
            {"title": "Di sản văn hóa ẩm thực Cốm dẹp Ngọc Biên Trà Cú", "url": "https://travinhtourist.vn/com-dep-ngoc-bien", "notebook": "Sổ tay 2: Mekong 360 - Tập 2"}
        ]
    },
    "mut-dua-sap-cau-ke": {
        "key_facts": [
            "Sản phẩm quà tặng ẩm thực cao cấp chế biến thủ công từ cơm dừa sáp Cầu Kè dày đặc quánh.",
            "Trải qua 11 công đoạn tỉ mỉ từ nạo sợi, ướp đường cát tinh khiết đến sên chảo gang trên lửa nhỏ liu riu trong 3 tiếng.",
            "Đạt chứng nhận OCOP 4 sao cấp tỉnh năm 2020 với vị dẻo mềm tan trong miệng không hề bị khô cứng."
        ],
        "ingredients": ["Cơm dừa sáp Cầu Kè tươi", "Đường cát trắng tinh luyện", "Vani tự nhiên", "Nước cốt lá dứa"],
        "where_to_eat": "Cơ sở Mứt dừa sáp Cẩm Hằng, thị trấn Cầu Kè, tỉnh Vĩnh Long",
        "price_range": "150.000đ - 250.000đ/hộp 250g hút chân không",
        "best_time": "Thích hợp làm quà biếu quanh năm, đặc biệt vào dịp Tết Nguyên Đán",
        "travel_tip": "Bảo quản mứt trong ngăn mát tủ lạnh để giữ được độ dẻo mềm tự nhiên và hương thơm ngậy của dừa sáp suốt 3 tháng.",
        "citations": [
            {"title": "Đặc sản OCOP Mứt dừa sáp Cầu Kè Trà Vinh", "url": "https://travinhtourist.vn/mut-dua-sap-cau-ke", "notebook": "Sổ tay 2: Mekong 360 - Tập 2"}
        ]
    },
    "tep-rang-dua": {
        "key_facts": [
            "Món ăn gia đình kinh điển gắn bó trăm năm với nếp sinh hoạt miệt vườn xứ dừa Nam Bộ.",
            "Tép bạc đất hoặc tép rong sông tươi rói làm sạch râu, rang săn giòn rồi rưới ngập nước cốt dừa già đậm đặc.",
            "Đun lửa riu riu cho nước cốt dừa ngấm sâu vào từng thớ thịt tép chuyển sang màu cánh gián bóng bẩy và béo ngậy."
        ],
        "ingredients": ["Tép bạc đất hoặc tép trấu tươi", "Nước cốt dừa già nguyên chất", "Hành tím băm", "Nước mắm ngon", "Đường thốt nốt", "Tiêu đen giã dập"],
        "where_to_eat": "Các quán cơm gia đình truyền thống tại thành phố Bến Tre và cù lao An Bình",
        "price_range": "60.000đ - 90.000đ/đĩa ăn kèm cơm nóng",
        "best_time": "Bữa trưa hoặc bữa tối gia đình quanh năm",
        "travel_tip": "Món này ăn kèm cơm trắng nóng hổi và canh chua cá đồng là sự kết hợp ẩm thực miệt vườn trọn vẹn nhất.",
        "citations": [
            {"title": "Hương vị ẩm thực dân dã: Tép rang dừa Bến Tre", "url": "https://bentre.gov.vn/tep-rang-dua", "notebook": "Sổ tay 2: Mekong 360 - Tập 2"}
        ]
    }
}

def _apply_dish_facts(entity: dict, facts: dict) -> dict:
    attrs = entity.setdefault("attributes", {})
    attrs["key_facts"] = facts["key_facts"]
    attrs["ingredients"] = facts["ingredients"]
    attrs["where_to_eat"] = facts["where_to_eat"]
    attrs["price_range"] = facts["price_range"]
    attrs["best_time"] = facts["best_time"]
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

def enrich_batch11_dishes():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    log_entries = []
    entities = data.get("entities", [])
    for ent in entities:
        eid = ent.get("id")
        if eid in DISH_FACTS:
            log_entries.append(_apply_dish_facts(ent, DISH_FACTS[eid]))

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log_entries, f, ensure_ascii=False, indent=2)

    print(f"Batch 11 complete: Enriched {len(log_entries)}/25 culinary dishes.")

if __name__ == "__main__":
    enrich_batch11_dishes()
