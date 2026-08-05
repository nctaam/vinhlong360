"""Gác cổng chống bịa khi nâng mô tả mỏng.

Mô tả mỏng chỉ được làm giàu bằng dữ kiện đã nằm trong bản ghi (name, address,
attributes...). Mọi con số hay tên riêng không truy được về đó đều là bịa, và
bịa trên dữ liệu du lịch là dẫn người thật đi sai chỗ.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from thin_description_writer import check_no_invention  # noqa: E402

ENTITY = {
    "id": "bun-nuoc-leo-cho-ba-tri",
    "name": "Bún nước lèo chợ Ba Tri",
    "type": "dish",
    "area": "ben-tre",
    "description": "",
    "attributes": {
        "toppings": "Cá lóc phi lê, tôm, huyết, rau muống, bông chuối, giá",
        "must_order": "Bún nước lèo đầy đủ",
        "open_hours": "5:00-10:00",
    },
}


def test_chan_so_lieu_bia():
    new = ("Tô bún nước lèo ở chợ Ba Tri dọn ra với cá lóc phi lê, tôm, huyết, rau muống, "
           "bông chuối và giá. Quán mở từ 5:00 đến 10:00. Giá khoảng 35.000 đồng mỗi tô, "
           "bán suốt 40 năm nay tại khu chợ này cho khách quen.")
    problems = check_no_invention(ENTITY, new)
    assert any("số liệu không có" in p for p in problems)


def test_chan_ten_rieng_bia():
    new = ("Tô bún nước lèo ở chợ Ba Tri dọn ra với cá lóc phi lê, tôm, huyết, rau muống, "
           "bông chuối và giá — do bà Nguyễn Thị Hoa nấu. Quán mở từ 5:00 đến 10:00, "
           "khách quen gọi bún nước lèo đầy đủ ngay khi vừa ngồi xuống ghế.")
    problems = check_no_invention(ENTITY, new)
    assert any("tên riêng không có" in p for p in problems)


def test_chan_tu_sao_rong():
    new = ("Tô bún nước lèo nổi tiếng ở chợ Ba Tri dọn ra với cá lóc phi lê, tôm, huyết, "
           "rau muống, bông chuối và giá. Quán mở từ 5:00 đến 10:00 mỗi ngày, khách quen "
           "thường gọi bún nước lèo đầy đủ ngay khi ngồi xuống.")
    problems = check_no_invention(ENTITY, new)
    assert any("sáo rỗng" in p for p in problems)


def test_chan_neu_van_con_mong():
    problems = check_no_invention(ENTITY, "Bún nước lèo chợ Ba Tri, mở 5:00-10:00.")
    assert any("vẫn dưới ngưỡng mỏng" in p for p in problems)


def test_cho_qua_khi_moi_du_kien_deu_truy_duoc():
    new = ("Tô bún nước lèo ở chợ Ba Tri dọn ra với cá lóc phi lê, tôm, huyết, rau muống, "
           "bông chuối và giá — ăn kèm cho tô đầy đủ. Hàng bún dọn sớm, bán từ 5:00 đến "
           "10:00 rồi nghỉ, nên muốn ăn phải đi trong buổi sáng.")
    assert check_no_invention(ENTITY, new) == []


def test_chan_mo_ta_rong():
    assert check_no_invention(ENTITY, "  ") == ["mô tả mới rỗng"]
