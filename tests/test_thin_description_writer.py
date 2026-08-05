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


def test_chan_khi_khong_dai_hon_ban_cu():
    entity = dict(ENTITY, description="Bún nước lèo ở chợ Ba Tri, bán buổi sáng với cá lóc và tôm.")
    problems = check_no_invention(entity, "Bún nước lèo chợ Ba Tri.")
    assert any("không dài hơn mô tả cũ" in p for p in problems)


class TestLoiThatTuDotViet765MoTa:
    """Ba loại lỗi mà gác cổng bản đầu hoàn toàn mù, đều đã xuất hiện thật."""

    def test_chan_khi_lo_ten_truong_noi_bo(self):
        """responsible_tips là đề xuất nội bộ; đưa ra ngoài thành dịch vụ đang bán."""
        new = ("Bãi biển Ba Động với responsible_tips cho khách tham gia workshop làm muối "
               "cùng diêm dân, kèm tour tìm hiểu nghề biển và các hoạt động trải nghiệm khác "
               "trong khu du lịch ven biển này.")
        problems = check_no_invention(ENTITY, new)
        assert any("trường nội bộ" in p for p in problems)

    def test_chan_khai_khong_do_chinh_xac_toa_do(self):
        """coords_approximate=false không đủ để hứa 'bấm bản đồ là ra tới cửa' (§1.7)."""
        new = ("Tô bún nước lèo ở chợ Ba Tri dọn ra với cá lóc phi lê, tôm, huyết và rau muống. "
               "Toạ độ chính xác nên bấm bản đồ là ra tới cửa, khỏi phải hỏi đường ai.")
        problems = check_no_invention(ENTITY, new)
        assert any("khai khống độ chính xác" in p for p in problems)

    def test_chan_loi_khuyen_an_toan_bia(self):
        """Bản thật đã khuyên bơi tự do giữa sông Cổ Chiên — sông sâu nhất ĐBSCL."""
        new = ("Chiều mát, nước sông Cổ Chiên quanh cù lao là chỗ tắm. Bơi tự do giữa dòng, "
               "không phao không hàng rào. Đi theo nhóm thì an toàn hơn, đừng xuống nước giữa trưa.")
        problems = check_no_invention(ENTITY, new)
        assert any("lời khuyên an toàn" in p for p in problems)

    def test_chan_tu_suy_ra_luat_hanh_chinh(self):
        new = ("Thị trấn Cầu Quan cũ cộng thêm hai xã thành phường Tân Hoà. "
               "Có thị trấn cũ nằm bên trong nên đơn vị mới xếp là phường, không phải xã.")
        problems = check_no_invention(ENTITY, new)
        assert any("luật phân loại hành chính" in p for p in problems)

    def test_chan_nhom_khach_muc_tieu(self):
        new = ("Bãi Ba Động là biển phù sa chứ không phải cát trắng. Phòng nghỉ hợp nghỉ ngắn ngày. "
               "Nhóm khách được nhắm tới là dân nhiếp ảnh và người làm nội dung.")
        problems = check_no_invention(ENTITY, new)
        assert any("nhóm khách mục tiêu" in p for p in problems)

    def test_chan_don_chu_bang_thu_ho_so_khong_co(self):
        """148 bản ở đợt đầu đủ 200 ký tự nhờ liệt kê thứ không có."""
        new = ("Tô bún nước lèo ở chợ Ba Tri dọn ra với cá lóc phi lê, tôm, huyết, rau muống, "
               "bông chuối và giá. Hàng bán từ 5:00 đến 10:00. Giá thì chưa có thông tin, "
               "khách hỏi tại chỗ để biết thêm.")
        problems = check_no_invention(ENTITY, new)
        assert any("độn chữ" in p for p in problems)


def test_cho_qua_khi_moi_du_kien_deu_truy_duoc():
    new = ("Tô bún nước lèo ở chợ Ba Tri dọn ra với cá lóc phi lê, tôm, huyết, rau muống, "
           "bông chuối và giá — ăn kèm cho tô đầy đủ. Hàng bún dọn sớm, bán từ 5:00 đến "
           "10:00 rồi nghỉ, nên muốn ăn phải đi trong buổi sáng.")
    assert check_no_invention(ENTITY, new) == []


def test_chan_mo_ta_rong():
    assert check_no_invention(ENTITY, "  ") == ["mô tả mới rỗng"]
