"""Gác cổng khi ghi đè mô tả hàng loạt: không được mất dữ kiện, không sửa oan câu lịch sử."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from admin_naming_rewrite import check, stale_sentences  # noqa: E402


class TestNhanDienCauCanSua:
    def test_cau_mo_ta_vi_tri_hien_tai_bi_bat(self):
        text = "Nằm trên khu đất cao ở xã Quới Thiện, huyện Vũng Liêm, khu mộ là điểm dừng lặng lẽ."
        assert stale_sentences(text)

    def test_cau_tieu_su_khong_bi_bat(self):
        """'sinh tại huyện Giồng Trôm' năm 1918 — huyện là cách gọi đúng của thời đó."""
        text = "Trung tướng Quân đội Nhân dân Việt Nam (1918–2005), sinh tại huyện Giồng Trôm, Bến Tre."
        assert stale_sentences(text) == []

    def test_cau_co_chu_cu_khong_bi_bat(self):
        text = "Khu vực này thuộc tỉnh Bến Tre cũ, nay là một phần tỉnh Vĩnh Long."
        assert stale_sentences(text) == []

    def test_cau_sach_khong_bi_bat(self):
        text = "Vườn dừa trải dọc bờ sông, mùa nước nổi ghe vẫn cặp mé vườn."
        assert stale_sentences(text) == []


class TestGacCongKhiGhi:
    OLD = "Công viên An Hội rộng 2,5 ha nằm trên Đại lộ Đồng Khởi, giữa trung tâm thành phố Bến Tre."

    def test_chan_khi_mat_so_lieu(self):
        new = "Công viên An Hội nằm trên Đại lộ Đồng Khởi, giữa trung tâm Bến Tre."
        problems = check(self.OLD, new)
        assert any("mất số liệu" in p for p in problems)

    def test_chan_khi_mat_ten_rieng(self):
        new = "Công viên rộng 2,5 ha nằm giữa trung tâm Bến Tre."
        problems = check(self.OLD, new)
        assert any("mất tên riêng" in p for p in problems)

    def test_chan_khi_van_con_cach_goi_cu(self):
        new = "Công viên An Hội rộng 2,5 ha nằm trên Đại lộ Đồng Khởi, giữa trung tâm thành phố Bến Tre hôm nay."
        problems = check(self.OLD, new)
        assert any("vẫn còn cách gọi cũ" in p for p in problems)

    def test_chan_khi_cat_xen_qua_nhieu(self):
        new = "Công viên An Hội 2,5 ha, Đại lộ Đồng Khởi."
        problems = check(self.OLD, new)
        assert any("ngắn hơn" in p for p in problems)

    def test_chan_khi_rong(self):
        assert check(self.OLD, "   ") == ["mô tả mới rỗng"]

    def test_cho_qua_ban_sua_dung(self):
        new = ("Công viên An Hội rộng 2,5 ha trải dọc Đại lộ Đồng Khởi, ngay lõi phường An Hội — "
               "khu trung tâm của Bến Tre trước khi ba tỉnh hợp nhất.")
        assert check(self.OLD, new) == []
