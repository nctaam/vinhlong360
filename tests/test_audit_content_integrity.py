"""Cổng soi nội dung đang phục vụ người dùng — phải bắt đúng, và không báo oan."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from audit_content_integrity import audit, stale_admin_sentences  # noqa: E402


def _one(description: str, eid: str = "e1"):
    return audit([{"id": eid, "description": description}])


class TestBatDungSauNhom:
    def test_bat_lo_truong_noi_bo(self):
        found = _one("Nơi này có responsible_tips cho khách tham gia workshop làm muối.")
        assert found["truong_noi_bo"]

    def test_bat_khai_khong_vi_tri(self):
        found = _one("Toạ độ chính xác nên bấm bản đồ là ra tới cửa.")
        assert found["khai_khong_vi_tri"]

    def test_bat_khuyen_an_toan_cho_nguoi(self):
        found = _one("Khách có thể bơi tự do giữa dòng, đi theo nhóm thì an toàn hơn.")
        assert found["khuyen_an_toan"]

    def test_bat_tu_suy_luat_hanh_chinh(self):
        found = _one("Có thị trấn cũ bên trong nên đơn vị mới xếp là phường.")
        assert found["tu_suy_luat_hc"]

    def test_bat_don_chu(self):
        found = _one("Giá thì chưa có thông tin, khách hỏi tại chỗ để biết thêm.")
        assert found["don_chu"]

    def test_bat_don_vi_hanh_chinh_cu(self):
        found = _one("Quán nằm ở xã Kim Hòa, huyện Cầu Ngang, Trà Vinh.")
        assert found["don_vi_hanh_chinh_cu"]


class TestKhongBaoOan:
    def test_ta_dong_vat_boi_loi_khong_phai_khuyen_an_toan(self):
        """Ca thật: 'bạn sẽ chứng kiến cua, còng, vọp bơi lội tự do' — thứ đang bơi
        là con vật, dù câu có chữ 'bạn'."""
        found = _one("Đi bộ theo lối ván gỗ, bạn sẽ chứng kiến cua, còng, vọp bơi lội tự do dưới tán rừng.")
        assert not found["khuyen_an_toan"]

    def test_cau_lich_su_giu_ten_cu_khong_bi_bat(self):
        text = "Trung tướng sinh năm 1918 tại huyện Giồng Trôm, Bến Tre."
        assert stale_admin_sentences(text) == []

    def test_cau_co_chu_cu_khong_bi_bat(self):
        text = "UBND tỉnh Trà Vinh cũ công nhận làng nghề năm 2011."
        assert stale_admin_sentences(text) == []

    def test_mo_ta_sach_khong_bi_bat(self):
        found = _one("Nước lèo nấu từ mắm cá sặc với sả. Tô có cá lóc phi lê, tôm và huyết.")
        assert all(not items for items in found.values())
