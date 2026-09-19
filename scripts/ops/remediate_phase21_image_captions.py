# -*- coding: utf-8 -*-
"""Remediate 69 flawed image captions in web/data.json (Phase 21).

Removes all old district-level administrative terms (huyện, thị xã, thị trấn)
and filler clichés (miền Tây, thiên đường, điểm đến lý tưởng) from
attributes.image_caption across all entities.
"""
from __future__ import annotations

import json
from pathlib import Path

DATA_FILE = Path("web/data.json")
LOG_FILE = Path("outputs/remediation_phase21_image_log.json")

# Map of 69 entity IDs to remediated image captions
CAPTIONS_MAP: dict[str, str] = {
    "lang-nghe-det-chieu-ca-hom-ben-ba": (
        "Khung dệt chiếu thủ công Cà Hom rộn rã nhịp thoi đưa, nơi đồng bào Khmer xã Hàm Tân "
        "khéo léo dệt nên những tấm chiếu hoa Cà Hom bền đẹp qua hơn 100 năm gìn giữ."
    ),
    "lang-nghe-dan-non-la-tt-long-ho": (
        "Những vành nón lá trắng muốt được các mẹ các chị chăm chút từng mũi kim tỉ mỉ tại "
        "làng nghề đan nón lá truyền thống phường Long Hồ ven dòng sông Long Hồ."
    ),
    "bai-bien-con-bung-thanh-hai": (
        "Bãi biển phù sa hoang sơ trải dài với hàng phi lao chắn sóng lộng gió tại xã Thạnh Hải, "
        "nguồn hải sản tươi sống dồi dào và ốc viết mùa gió chướng."
    ),
    "bia-chien-thang-loc-thuan": (
        "Bia chiến thắng Lộc Thuận trang trọng ghi danh chiến công năm 1960 của quân và dân xã Lộc Thuận "
        "trong phong trào Đồng Khởi đánh phá cứ điểm đối phương."
    ),
    "chua-giac-linh-chua-doi": (
        "Chùa Giác Linh rợp bóng vườn cây cổ thụ mát lành, nơi cư ngụ tự nhiên của hàng ngàn cá thể "
        "dơi ngựa quý hiếm tại xã Cầu Ngang."
    ),
    "chua-vam-ray-chua-phat-nam": (
        "Chùa Vàm Ray rực rỡ sắc vàng phong cách Angkor với đại tượng Phật Thích Ca nhập niết bàn ngoài "
        "trời dài 54m uy nghiêm tại xã Hàm Giang."
    ),
    "keo-dua-mo-cay-co-so-tuyet-phung": (
        "Hộp kẹo dừa dẻo sầu riêng lá dứa Tuyết Phụng tại phường Mỏ Cày, đặc sản truyền thống béo ngậy "
        "được chế biến từ cốt dừa nguyên chất."
    ),
    "kho-ca-bien-thanh-phu": (
        "Các loại khô cá lưỡi trâu, cá mối, cá chỉ vàng phơi khô tự nhiên thơm phức mùi nắng biển "
        "tại làng hải sản xã Thạnh Hải ven bờ Biển Đông."
    ),
    "nha-tho-mac-bac-tieu-can": (
        "Thánh đường Mặc Bắc tráng lệ mang phong cách Roman Gothic xây dựng năm 1886, công trình "
        "Công giáo cổ kính hơn 130 năm tuổi tại xã Long Hiệp."
    ),
    "xa-binh-phu": (
        "Các xưởng thủ công mỹ nghệ chạm khắc gỗ và đan lục bình xuất khẩu tại xã Bình Phú "
        "ven trục quốc lộ 53."
    ),
    "xa-hoa-binh": (
        "Những luống cam sành hữu cơ chuẩn GlobalGAP mọng nước ven các kênh rạch tại xã Hòa Bình "
        "trù phú phù sa."
    ),
    "hu-tieu-chay": (
        "Tô hủ tiếu chay thanh tịnh tại phường Mỏ Cày với nước lèo hầm củ quả ngọt lành, "
        "tàu hũ ky chiên giòn rụm và nấm rơm búp thanh đạm."
    ),
    "xa-my-thuan": (
        "Cánh đồng lúa chất lượng cao kết hợp trồng luân canh khoai lang tím và bắp ngọt tại "
        "xã Mỹ Thuận ven sông Hậu."
    ),
    "xa-phong-thanh": (
        "Những rặng dừa sáp trĩu cành bên cánh đồng lúa hai vụ trù phú tại xã Phong Thạnh "
        "bên bờ rạch Bông Bót."
    ),
    "nha-hang-am-thuc-pho": (
        "Nhà hàng Ẩm Thực Phố trên trục đường Phạm Thái Bường thuộc phường Phước Hậu, "
        "phục vụ đa dạng phong vị ẩm thực sông nước trong không gian thoáng mát."
    ),
    "sokfarm-tieu-can": (
        "Kỹ thuật thu mật hoa dừa truyền thống và vườn dừa sinh thái đạt chuẩn hữu cơ quốc tế "
        "tại Sokfarm ấp Cây Hẹ, xã Cầu Quan."
    ),
    "mua-nuoc-noi-dbscl": (
        "Mùa nước nổi đem nguồn cá tôm dồi dào và sắc vàng bông điên điển tràn ngập các cánh đồng "
        "châu thổ đồng bằng sông Cửu Long từ tháng 8 đến tháng 11 âm lịch."
    ),
    "cho-giong-trom": (
        "Khu chợ truyền thống sầm uất tại xã Lương Hòa với đầy ắp các loại bánh phồng Sơn Đốc, "
        "kẹo dừa và rau củ quả tươi miệt vườn."
    ),
    "khu-du-lich-s-mo-farm-cuu-long": (
        "Không gian kiến trúc đất nung lấy cảm hứng từ vòm lò gạch gốm đỏ Mang Thít giữa vườn "
        "cây trái tại Khu du lịch Somo Farm Cửu Long, xã Cái Nhum."
    ),
    "dua-sap-cau-ke": (
        "Trái dừa sáp Cầu Kè bổ đôi với lớp cơm dừa trắng dẻo quánh, giống dừa đặc sản có từ "
        "thập niên 1960 tại xã Cầu Kè."
    ),
    "cau-lac-bo-don-ca-tai-tu-huyen-tra-on": (
        "Các tài tử miệt vườn hội tụ về xã Trà Côn so dây nắn phím những điệu Nam xuân, "
        "Nam ai mộc mạc bên dòng kinh Trà Ôn."
    ),
    "bien-con-bung-thanh-phu": (
        "Sóng biển vỗ rì rào lên bãi bồi Cồn Bửng thuộc xã Thạnh Hải, bãi biển cát phù sa "
        "mịn trải dài hơn 15km đón gió Đông."
    ),
    "thanh-duong-giao-xu-mac-bac": (
        "Tháp chuông gothic vút cao và vòm thánh đường gạch đỏ cổ kính soi bóng bên bờ sông Hậu "
        "tại giáo xứ Mặc Bắc, xã Long Hiệp."
    ),
    "cu-lao-dai-vung-liem": (
        "Cù Lao Dài trên sông Cổ Chiên thuộc xã Quới Thiện với những rặng bần cổ thụ chắn sóng "
        "và các vườn bưởi da xanh trĩu quả."
    ),
    "buoi-nam-roi-binh-minh": (
        "Những trái bưởi Năm Roi trĩu cành vỏ vàng óng tép ráo ngọt thanh đạt chứng nhận "
        "Chỉ dẫn địa lý tại phường Bình Minh."
    ),
    "khu-di-tich-dong-khoi": (
        "Khu di tích Quốc gia đặc biệt Đồng Khởi tại Định Thủy, nơi lưu giữ súng ngựa trời, "
        "mõ dừa và bia chiến thắng khắc ghi phong trào nổi dậy năm 1960."
    ),
    "monkey-tea---tra-sua-coffee": (
        "Monkey Tea trên trục đường Lý Tự Trọng thuộc phường Duyên Hải, không gian thưởng thức "
        "trà sữa ngắm phố biển râm ran gió mát."
    ),
    "somo-farm-cuu-long-mang-thit": (
        "Du khách trải nghiệm gặt lúa, hái nấm hữu cơ và đạp xe quanh các rặng cây ăn trái "
        "xanh tươi tại Somo Farm Cửu Long, xã Cái Nhum."
    ),
    "cho-cai-von": (
        "Khung cảnh buôn bán nông sản và rau củ miệt vườn tấp nập từ sớm mai tại Chợ Cái Vồn "
        "bên bờ sông Hậu thuộc phường Bình Minh."
    ),
    "kenh-tra-on-vinh-long": (
        "Tuyến thủy lộ kênh Trà Ôn tấp nập sà lan chở cát phù sa và ghe chở cam sành kết nối "
        "giao thương giữa sông Tiền và sông Hậu."
    ),
    "rach-tra-ngoa-vinh-long": (
        "Rạch Trà Ngoa đưa nguồn nước ngọt phù sa tưới tiêu cho những cánh đồng lúa và vườn "
        "dừa bạt ngàn tại vùng đất Trà Côn."
    ),
    "song-thom-rach-thom-ben-tre": (
        "Tấp nập cảnh ghe thuyền buôn bán chỉ xơ dừa và mụn dừa xuất khẩu dọc hai bên bờ sông "
        "Thom thuộc phường Mỏ Cày."
    ),
    "kenh-bong-bot-tra-vinh": (
        "Kênh Bông Bót nối dòng sông Hậu với các vùng trồng lúa phì nhiêu, nguồn cung cấp "
        "nước ngọt quan trọng cho các xã vùng Cầu Kè."
    ),
    "quan-lau-ca-keo-chu-tam-huyen-vung-liem-vinh-long": (
        "Quán Chú Tám tại phường Vũng Liêm, thố lẩu cá kèo lá giang sôi sùng sục ăn kèm "
        "rau đắng đất, bắp chuối bào và bún tươi trắng muốt."
    ),
    "goi-cuon-tom-thit-ba-hai-chau-thanh-ben-tre": (
        "Món gỏi cuốn tôm thịt rau sống xanh tươi chấm tương đen đậu phộng béo bùi tại quán "
        "Bà Hai ở phường Phú Khương."
    ),
    "hu-tieu-ba-tam-cau-ke-tra-vinh": (
        "Tiệm hủ tiếu Bà Tám tại xã Cầu Kè, nước lèo ninh từ xương ống heo ngọt thanh tự nhiên, "
        "sợi bánh hủ tiếu gạo Cầu Kè mềm dai đặc trưng."
    ),
    "cong-vien-29": (
        "Thảm cỏ xanh mướt và những bồn hoa rực rỡ tại Công viên Hai Tháng Chín trung tâm "
        "phường Tân Quới, không gian sinh hoạt cộng đồng thoáng đãng."
    ),
    "vuon-chim-hai-chia-tan-my-tra-on": (
        "Hàng ngàn cá thể cò ốc và cò trắng làm tổ trên ngọn tràm ngọn tre tại Vườn Chim Hai Chìa "
        "thuộc xã Trà Côn."
    ),
    "khu-du-lich-truong-huy-long-ho": (
        "Không gian vui chơi giải trí và hồ bơi nhân tạo hiện đại giữa mảng xanh rộng 10ha "
        "tại Khu Du Lịch Trường Huy, phường Thanh Đức."
    ),
    "khu-du-lich-sinh-thai-hoang-quan": (
        "Những chòi lá mộc mạc bên hồ sen nở hoa thanh khiết tại Khu Du Lịch Sinh Thái Hoàng Quân, "
        "phường Cái Vồn."
    ),
    "vuon-thanh-tra-dong-thanh": (
        "Những chùm thanh trà vàng ươm chua ngọt rực rỡ dưới nắng xuân tại các liếp vườn "
        "thuộc phường Đông Thành."
    ),
    "cho-tan-quoi": (
        "Các sạp hàng bày bán khoai lang tím giống Nhật và rau củ tươi sạch tại Chợ Tân Quới, "
        "trung tâm giao thương nông sản phường Tân Quới."
    ),
    "vuon-cay-an-trai-miet-vuon-long-ho": (
        "Liếp vườn chôm chôm, măng cụt và bưởi da xanh rợp bóng mát dọc các con rạch phù sa "
        "thuộc phường Long Châu."
    ),
    "song-co-chien-doan-mang-thit": (
        "Mặt nước sông Cổ Chiên mênh mông đoạn qua vùng gốm Mang Thít với những bè nuôi cá điêu "
        "hồng san sát và ghe chở đất sét đỏ."
    ),
    "rung-ngap-man-long-vinh-duyen-hai": (
        "Rừng đước nguyên sinh vươn rễ chằng chịt giữ đất ven biển tại xã Long Vĩnh thuộc "
        "khu vực Duyên Hải, tạo vành đai chắn sóng tự nhiên."
    ),
    "lang-nghe-dan-chapay-phu-can": (
        "Nghệ nhân Khmer miệt mài đục đẽo thân gỗ mít, so từng phím đàn Chà-pây Đơng-veng "
        "cổ truyền tại sóc Phú Cần thuộc phường Tiểu Cần."
    ),
    "mut-me-cai-von": (
        "Từng trái me chín dốt lột vỏ sên đường cát óng ả dẻo quánh, vị chua thanh ngọt ngào "
        "của thức quà gia truyền tại phường Cái Vồn."
    ),
    "truong-xuan": (
        "Nghệ sĩ hài Trường Xuân, gương mặt gạo cội của nghệ thuật sân khấu cải lương Nam Bộ "
        "thập niên 1960 với lối diễn hóm hỉnh và giàu tính nhân văn."
    ),
    "thanh-tra-binh-minh": (
        "Chùm trái thanh trà ngọt vỏ mỏng vàng ươm mọng nước tại phường Bình Minh, quả đặc sản "
        "quý hiếm tỏa hương thơm thảo mộc khó quên."
    ),
    "tom-duyen-hai": (
        "Thu hoạch tôm sú nước lợ sinh thái tại vùng cửa biển phường Duyên Hải, tôm đạt kích cỡ "
        "lớn vỏ bóng xanh đen cung cấp cho chế biến xuất khẩu."
    ),
    "cau-lac-bo-don-ca-tai-tu-truong-xay-dung-mien-tay": (
        "Buổi hòa tấu khúc Nam ai sâu lắng của các thành viên câu lạc bộ đờn ca tài tử tại "
        "khuôn viên trường đại học thuộc phường Long Châu."
    ),
    "chua-phuoc-son": (
        "Chánh điện chùa Phước Sơn thanh tịnh bên dòng sông Hậu tại phường Bình Minh, ngôi chùa "
        "Phật giáo Bắc tông duy trì nếp tu học trang nghiêm qua nhiều thế hệ."
    ),
    "chua-bo-de": (
        "Cổ tự Bồ Đề với cổng tam quan cổ kính và hàng bồ đề tỏa bóng mát, lưu giữ không gian "
        "thanh tịnh giữa xóm làng trù phú phường Bình Minh ven sông Hậu."
    ),
    "ben-pha-tran-phu-can-tho-vinh-long-vinh-long": (
        "Bến đò khách dân sinh Trần Phú vận chuyển người dân vượt sông Hậu kết nối phường Cái Vồn "
        "với bến Ninh Kiều."
    ),
    "ben-xe-duyen-hai-tx-duyen-hai-tra-vinh": (
        "Các chuyến xe khách đường dài chuẩn bị khởi hành từ Bến xe khách Duyên Hải trên trục đường "
        "19 Tháng 5 thuộc phường Duyên Hải."
    ),
    "htx-cam-sanh-tra-on": (
        "Những chùm cam sành vỏ mỏng mọng nước, tép vàng cam ngọt đậm đà được thu hoạch tại vườn "
        "chuyên canh trù phú xã Trà Côn ven sông Hậu."
    ),
    "ben-xe-vung-liem-vinh-long": (
        "Bến xe khách Vũng Liêm trên trục Tỉnh lộ 902 thuộc phường Vũng Liêm, phục vụ các tuyến xe "
        "liên tỉnh kết nối Thành phố Hồ Chí Minh."
    ),
    "nha-thuoc-fpt-long-chau-1237-quoc-lo-54-vinh-long": (
        "Điểm bán dược phẩm và thiết bị y tế gia đình tại Nhà thuốc FPT Long Châu số 1237 trên "
        "trục Quốc lộ 54 thuộc phường Tân Quới."
    ),
    "coco-riverside-lodge-trung-nghia": (
        "Khu nghỉ dưỡng Coco Riverside Lodge với dãy nhà sàn gỗ mộc mạc soi bóng ven kênh rạch "
        "xã Trung Nghĩa, nơi lưu trú sinh thái miệt vườn đón khách từ năm 2012."
    ),
    "khach-san-chieu-hung": (
        "Khách sạn Chiêu Hùng trên đường Gia Long thuộc xã Trà Côn, vị trí thuận tiện trải nghiệm "
        "nhịp sống sông nước ven kinh Trà Ôn vào sáng sớm."
    ),
    "khach-san-minh-khue": (
        "Khách sạn Minh Khuê tại khóm 2 xã Cái Nhum, địa chỉ lưu trú yên tĩnh giúp du khách "
        "thong thả khám phá làng nghề gạch gốm Mang Thít."
    ),
    "khu-di-san-lo-gach-mang-thit": (
        "Hàng trăm vòm lò nung gạch gốm san sát soi bóng xuống dòng kinh Thầy Kay, quần thể di sản "
        "làng nghề thủ công trăm năm tại xã Nhơn Phú."
    ),
    "lang-nghe-che-bien-hai-san-kho-thanh-phong": (
        "Những giàn phơi cá khô đù, cá khoai tươi rói ướp muối biển phơi dưới nắng giòn cửa biển "
        "Thạnh Phong thuộc xã An Qui."
    ),
    "lang-hoa-kieng-va-cay-giong-cho-lach": (
        "Bạt ngàn gốc mai vàng, cúc mâm xôi và cây giống sầu riêng măng cụt Cái Mơn khoe sắc rực rỡ "
        "dọc tuyến quốc lộ 57 qua xã Chợ Lách."
    ),
    "hai-san-ngoc-hiep-binh-dai-ben-tre": (
        "Quán Hải Sản Ngọc Hiệp trên đường Lê Hoàng Chiếu thuộc khu vực Bình Đại, đặc sản cua biển "
        "gạch son luộc sả và sò huyết rang muối ớt đậm đà vị biển."
    ),
    "nha-tho-giao-xu-cai-nhum": (
        "Tháp chuông cao 33 mét mang phong cách kiến trúc La Mã cổ kính của Nhà thờ Giáo xứ "
        "Cái Nhum xã Long Thới, một trong những họ đạo thành lập từ năm 1731."
    ),
    "tuan-le-van-hoa-am-thuc-an-hoi-2026": (
        "Không gian ẩm thực ven sông lung linh ánh đèn tại Công viên An Hội thuộc phường An Hội, "
        "chào đón du khách thưởng thức những món ngon dân dã của cư dân sông nước."
    ),
    "le-hoi-cung-bien-my-long": (
        "Nghi thức đóng tàu và tống tàu ra khơi cửa sông Cổ Chiên trong tiếng trống chiêng rộn rã "
        "tại miếu Bà Chúa Xứ xã Mỹ Long."
    ),
    "dinh-lang-hieu-phung": (
        "Kiến trúc gian võ ca và chính điện lợp ngói âm dương cổ kính của Đình làng Hiếu Phụng "
        "tại ấp Quang Trạch, trung tâm tín ngưỡng nông nghiệp lâu đời của xã Hiếu Phụng."
    ),
}


def load_dataset() -> dict:
    """Load JSON database."""
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_dataset(data: dict) -> None:
    """Save JSON database."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def apply_caption_remediation(entities: list[dict]) -> tuple[int, list[dict]]:
    """Apply remediated captions to entities."""
    logs = []
    count = 0
    for entity in entities:
        eid = entity.get("id")
        if eid in CAPTIONS_MAP:
            attrs = entity.setdefault("attributes", {})
            old_cap = attrs.get("image_caption", "")
            new_cap = CAPTIONS_MAP[eid]
            attrs["image_caption"] = new_cap
            count += 1
            logs.append({
                "id": eid,
                "name": entity.get("name"),
                "old_caption": old_cap,
                "new_caption": new_cap,
            })
    return count, logs


def main() -> None:
    """Execute remediation script."""
    data = load_dataset()
    entities = data.get("entities", [])
    count, logs = apply_caption_remediation(entities)
    save_dataset(data)

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump({"updated_count": count, "remediated": logs}, f, ensure_ascii=False, indent=2)

    print(f"Successfully remediated {count} / {len(CAPTIONS_MAP)} image captions.")


if __name__ == "__main__":
    main()
