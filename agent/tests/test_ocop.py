"""Luật rút hạng OCOP — bản backend.

SONG SINH với `web-nuxt/tests/ocop-stars.test.ts`. Hai bộ soi CÙNG MỘT bộ chuỗi
thật, vì luật có hai bản (Python dựng JSON-LD / văn bản nạp cho LLM / thẻ chat,
TypeScript dựng huy hiệu). Lệch nhau thì cả hai cùng đỏ.

Bộ chuỗi thật lấy từ `web/data.json`, không bịa:
  dua-sap-cau-ke            "VICOSAP: 4 SP OCOP 5 sao quốc gia + 7 SP OCOP 4 sao"
  (một entity khác)         "OCOP 4 sao (QĐ 114/QĐ-UBND, 15/1/2020)"
  khoai-lang-say-binh-tan   ocop_star=5, văn xuôi "được ĐỀ XUẤT … 5 sao"
  khoai-lang-say-dong-phat  ocop_star=4, văn xuôi "ĐẠT OCOP 4 sao và được đề xuất 5 sao"
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import ocop  # noqa: E402


def E(attrs, **kw) -> dict:
    return {"id": "x", "name": "X", "attributes": attrs, **kw}


class TestNhanHienThi:
    def test_khoa_so_uu_tien(self):
        assert ocop.ocop_display_label(E({"ocop_star": 5})) == "OCOP 5 sao"
        assert ocop.ocop_display_label(E({"ocop_stars": 3})) == "OCOP 3 sao"
        assert ocop.ocop_display_label(E({"ocop_rating": "4"})) == "OCOP 4 sao"

    def test_van_xuoi_neo_dau_chuoi(self):
        assert ocop.ocop_display_label(E({"ocop": "OCOP 3 sao"})) == "OCOP 3 sao"
        assert ocop.ocop_display_label(E({"ocop": "4 sao"})) == "OCOP 4 sao"

    def test_khong_gan_danh_muc_cua_cong_ty_khac(self):
        """Ca then chốt — đây chính là lỗi đo được trên trang đang chạy."""
        e = E({"ocop": "VICOSAP: 4 SP OCOP 5 sao quốc gia + 7 SP OCOP 4 sao"})
        assert ocop.ocop_display_label(e) == "OCOP"
        assert ocop.ocop_tier(e) == 0

    def test_khong_in_so_quyet_dinh(self):
        e = E({"ocop": "OCOP 4 sao (QĐ 114/QĐ-UBND, 15/1/2020)"})
        assert ocop.ocop_display_label(e) == "OCOP 4 sao"

    def test_bool_khong_thanh_hang_mot_sao(self):
        """`True` là `1` trong Python — không chặn thì thành 'OCOP 1 sao'."""
        assert ocop.ocop_display_label(E({"ocop_star": True})) == "OCOP"

    def test_hang_ngoai_thang_khong_duoc_khai(self):
        assert ocop.ocop_display_label(E({"ocop_star": 9})) == "OCOP"
        assert ocop.ocop_display_label(E({"ocop_star": 0})) == "OCOP"

    def test_khong_co_dau_hieu_thi_rong(self):
        assert ocop.ocop_display_label(E({"rating": 4.5})) == ""
        assert ocop.ocop_display_label(E({})) == ""

    def test_attributes_la_LIST_khong_lam_no(self):
        """Dữ liệu thật có entity mang `attributes` dị dạng. Một test cũ của seo
        bơm đúng ca này và đã bắt được bản đầu của hàm."""
        assert ocop.ocop_display_label({"id": "x", "attributes": ["a", "b"]}) == ""
        assert ocop.is_ocop_certified({"id": "x", "attributes": ["a"]}) is False


class TestBoLocDeNghi17:
    def test_moi_de_nghi_thi_khong_khai_hang(self):
        e = E({"ocop_star": 5},
              summary="Sản phẩm được ĐỀ XUẤT lên Trung ương đánh giá 5 sao OCOP.")
        assert ocop.ocop_display_label(e) == "OCOP"

    def test_da_dat_thi_giu_hang(self):
        """Luật một chiều đánh oan ngay ca này — nó ĐẠT 4 sao thật."""
        e = E({"ocop_star": 4},
              summary="ĐẠT OCOP 4 sao và được đề xuất công nhận 5 sao.")
        assert ocop.ocop_display_label(e) == "OCOP 4 sao"

    def test_xet_toan_van_khong_xet_tung_lan_nhac(self):
        e = E({"ocop_star": 5},
              summary="Được đề xuất lên Trung ương đánh giá 5 sao OCOP.",
              description="Sản phẩm OCOP 5 sao.")
        assert ocop.ocop_display_label(e) == "OCOP"


class TestCoChungNhan:
    def test_bat_ca_san_pham_chi_co_khoa_so(self):
        """Lọc bằng `attributes.ocop` truthy bỏ sót 73 sản phẩm — cùng lỗi đã vá
        ở trang /ocop, còn sống trong xếp hạng và bộ lọc tìm kiếm backend."""
        assert ocop.is_ocop_certified(E({"ocop_star": 3})) is True
        assert ocop.is_ocop_certified(E({"ocop": "OCOP"})) is True
        assert ocop.is_ocop_certified(E({"ocop_certified": True})) is True
        assert ocop.is_ocop_certified(E({"rating": 4})) is False

    def test_chuoi_rong_khong_tinh_la_co_chung_nhan(self):
        assert ocop.is_ocop_certified(E({"ocop_star": ""})) is False
        assert ocop.is_ocop_certified(E({"ocop": ""})) is False


class TestTier:
    def test_tier_khop_voi_nhan(self):
        assert ocop.ocop_tier(E({"ocop_star": 5})) == 5
        assert ocop.ocop_tier(E({"ocop": "OCOP"})) == 0

    def test_tier_khong_bat_chu_so_lac(self):
        """Bản cũ ở server.py dùng `re.search` chữ số đầu tiên ở bất kỳ đâu."""
        assert ocop.ocop_tier(E({"ocop": "Đạt chuẩn năm 2020"})) == 0
        assert ocop.ocop_tier(E({"ocop": "VICOSAP: 4 SP OCOP 5 sao"})) == 0


# ─────────────────────────────────────────────────────────────────────────
# BỘ CA DÙNG CHUNG với bản TypeScript
# ─────────────────────────────────────────────────────────────────────────
# `tests/fixtures/ocop-twin-cases.json` được CẢ HAI suite đọc. Viết test song
# song ở hai bên là chưa đủ: 2026-08-27 hai bản đã lệch ở việc kẹp thang 1..5
# mà cả hai bộ test vẫn xanh, vì mỗi bên chỉ soi ca của riêng mình.

import json  # noqa: E402

_TWIN = json.loads(
    (Path(__file__).resolve().parents[2] / "tests/fixtures/ocop-twin-cases.json")
    .read_text(encoding="utf-8")
)


def test_bo_ca_dung_chung_khong_rong():
    assert len(_TWIN["cases"]) >= 20, "bộ ca dùng chung bị teo — ai đó xoá bớt?"


def test_khop_bo_ca_dung_chung():
    sai = []
    for c in _TWIN["cases"]:
        e = c["entity"]
        got = (ocop.ocop_display_label(e), ocop.ocop_tier(e), ocop.is_ocop_certified(e))
        want = (c["label"], c["tier"], c["certified"])
        if got != want:
            sai.append(f"{c['ten']}: được {got}, cần {want}")
    assert not sai, "lệch bộ ca dùng chung:\n  " + "\n  ".join(sai)


class TestRanhGioiCacHamTach:
    """Khoá hợp đồng của các hàm con sau đợt tách (complexity 21 -> dưới 12).

    Điểm dễ hỏng nhất khi tách: đặt bộ lọc §1.7 nhầm tầng. `_claimed_tier` phải
    trả hạng GHI TRONG DỮ LIỆU, chưa lọc — nếu nó tự lọc thì `ocop_tier` và
    `ocop_display_label` sẽ lọc HAI LẦN, và một ngày nào đó ai đó gọi thẳng
    `_claimed_tier` sẽ nhận số khác với ý nghĩa cái tên.
    """

    def test_claimed_tier_KHONG_ap_bo_loc_17(self):
        e = E({"ocop_star": 5}, summary="Được ĐỀ XUẤT đánh giá 5 sao OCOP.")
        assert ocop._claimed_tier(e["attributes"]) == 5, "hạng ghi trong dữ liệu"
        assert ocop.ocop_display_label(e) == "OCOP", "nhãn mới là nơi lọc §1.7"

    def test_khoa_so_thang_van_xuoi(self):
        attrs = {"ocop_star": 3, "ocop": "OCOP 5 sao"}
        assert ocop._claimed_tier(attrs) == 3

    def test_attrs_chuan_hoa_ca_di_dang(self):
        assert ocop._attrs({"attributes": ["a"]}) == {}
        assert ocop._attrs({"attributes": None}) == {}
        assert ocop._attrs({}) == {}

    def test_tu_o_ocop_neo_dau_chuoi(self):
        assert ocop._tu_o_ocop({"ocop": "4 sao"}) == 4
        assert ocop._tu_o_ocop({"ocop": "VICOSAP: 4 SP OCOP 5 sao"}) == 0
        assert ocop._tu_o_ocop({"ocop": True}) == 0

    def test_dau_hieu_ocop_doc_lap_voi_hang(self):
        """Có chứng nhận mà không rút được hạng vẫn phải là True — nếu không,
        73 sản phẩm chỉ có `ocop_star` lại biến mất như lỗi cũ."""
        assert ocop._co_dau_hieu_ocop({"ocop_star": 9}) is True
        assert ocop._co_dau_hieu_ocop({"ocop": "OCOP"}) is True
        assert ocop._co_dau_hieu_ocop({"rating": 4}) is False
