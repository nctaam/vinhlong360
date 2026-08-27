"""JSON-LD KHÔNG được phát `attributes.ocop` thô ra structured data.

Đo trên trang đang chạy 2026-08-27, `/dia-diem/dua-sap-cau-ke`:
    brand.name = "OCOP VICOSAP: 4 SP OCOP 5 sao quốc gia + 7 SP OCOP 4 sao"
Tức khai với máy tìm kiếm rằng thương hiệu của TRÁI DỪA là danh mục chứng nhận
của một CÔNG TY KHÁC. Cùng chuỗi đó còn nằm ở `identifier.value`.

Bộ test này soi CÙNG MỘT bộ chuỗi thật với `web-nuxt/tests/ocop-stars.test.ts`.
Đó là chủ đích: luật rút hạng có hai bản (Python cho JSON-LD, TypeScript cho huy
hiệu) vì backend và frontend dựng ở hai nơi. Hai bản lệch nhau thì hai bộ test
cùng đỏ.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import ocop  # noqa: E402
import seo  # noqa: E402


def E(attrs: dict, **kw) -> dict:
    return {"id": "x", "name": "X", "attributes": attrs, **kw}


class TestOcopDisplayLabel:
    def test_rut_dung_hang_tu_khoa_so(self):
        assert ocop.ocop_display_label(E({"ocop_star": 5})) == "OCOP 5 sao"
        assert ocop.ocop_display_label(E({"ocop_stars": 3})) == "OCOP 3 sao"
        assert ocop.ocop_display_label(E({"ocop_rating": "4"})) == "OCOP 4 sao"

    def test_rut_dung_hang_tu_van_xuoi_neo_dau(self):
        assert ocop.ocop_display_label(E({"ocop": "OCOP 3 sao"})) == "OCOP 3 sao"
        assert ocop.ocop_display_label(E({"ocop": "4 sao"})) == "OCOP 4 sao"

    def test_khong_in_so_quyet_dinh(self):
        lb = ocop.ocop_display_label(E({"ocop": "OCOP 4 sao (QĐ 114/QĐ-UBND, 15/1/2020)"}))
        assert lb == "OCOP 4 sao"
        assert "QĐ" not in lb

    def test_khong_gan_danh_muc_cua_cong_ty_khac(self):
        """Ca then chốt — chính nó là lỗi đo được trên trang thật."""
        dua_sap = E({"ocop": "VICOSAP: 4 SP OCOP 5 sao quốc gia + 7 SP OCOP 4 sao"})
        lb = ocop.ocop_display_label(dua_sap)
        assert lb == "OCOP", "neo đầu chuỗi bị nới → tự phong 5 sao cho trái dừa"
        assert "VICOSAP" not in lb

    def test_co_chung_nhan_chua_ro_hang_thi_chi_ghi_OCOP(self):
        assert ocop.ocop_display_label(E({"ocop": "OCOP"})) == "OCOP"
        assert ocop.ocop_display_label(E({"ocop_certified": True})) == "OCOP"

    def test_khong_co_dau_hieu_thi_khong_co_nhan(self):
        assert ocop.ocop_display_label(E({"rating": 4.5})) == ""
        assert ocop.ocop_display_label(E({})) == ""

    def test_bool_khong_bi_doc_thanh_hang(self):
        """`ocop_star: True` là 1 trong Python nếu không chặn — thành 'OCOP 1 sao'."""
        assert ocop.ocop_display_label(E({"ocop_star": True})) == "OCOP"

    def test_hang_ngoai_thang_1_5_khong_duoc_khai(self):
        assert ocop.ocop_display_label(E({"ocop_star": 9})) == "OCOP"
        assert ocop.ocop_display_label(E({"ocop_star": 0})) == "OCOP"


class TestBoLocDeNghi17:
    """§1.7 — hạng mới ĐƯỢC ĐỀ NGHỊ không phải hạng ĐÃ ĐẠT."""

    def test_de_xuat_thi_tut_ve_OCOP_tran(self):
        binh_tan = E(
            {"ocop_star": 5},
            summary="Sản phẩm được ĐỀ XUẤT lên Trung ương đánh giá 5 sao OCOP.",
        )
        assert ocop.ocop_display_label(binh_tan) == "OCOP"

    def test_da_dat_thi_giu_hang_du_co_de_xuat_hang_cao_hon(self):
        """Luật một chiều đánh oan ngay ca này — nó ĐẠT 4 sao thật."""
        dong_phat = E(
            {"ocop_star": 4},
            summary="ĐẠT OCOP 4 sao và được đề xuất công nhận 5 sao.",
        )
        assert ocop.ocop_display_label(dong_phat) == "OCOP 4 sao"

    def test_xet_toan_van_khong_xet_tung_lan_nhac(self):
        """Văn xuôi tự mâu thuẫn là chuyện THẬT: nói 'đề xuất … 5 sao' rồi kết
        bằng câu trần 'Sản phẩm OCOP 5 sao.' Luật xét-từng-lần sẽ để câu trần
        lật ngược cả phán quyết."""
        e = E(
            {"ocop_star": 5},
            summary="Được đề xuất lên Trung ương đánh giá 5 sao OCOP.",
            description="Sản phẩm OCOP 5 sao.",
        )
        assert ocop.ocop_display_label(e) == "OCOP"


class TestJsonLdKhongPhatVanXuoiTho:
    def test_brand_va_identifier_deu_da_chuan_hoa(self):
        ld: dict = {}
        e = E({"ocop": "VICOSAP: 4 SP OCOP 5 sao quốc gia + 7 SP OCOP 4 sao"})
        seo._jsonld_product(ld, e["attributes"], "dua-sap-cau-ke", e)
        assert ld.get("brand", {}).get("name") == "OCOP"
        assert "VICOSAP" not in str(ld)

    def test_khong_co_OCOP_thi_khong_phat_brand(self):
        ld: dict = {}
        e = E({"price": "50000"})
        seo._jsonld_product(ld, e["attributes"], "x", e)
        assert "brand" not in ld
