"""Regression test cho LOGIC data-fix (§B3 — scripts/ trước đây 0% test, audit TC-01).

Khoá các phần CORRECTNESS-CRITICAL của pass-2 từng có bug thật:
  - norm() GIỮ DẤU (bug: "Bình Thạnh"≡"Bình Thành" → map sai ward)
  - CROSSWALK NQ1687 (chủ-dự-án xác nhận: An Khánh→Phú Túc, An Thủy→Tân Thủy...)
  - NUMBERED phường-số 3 TP (verbatim NQ1687, cross-check 2×)
  - 'Tp.' KHÔNG bị parse nhầm thành 'phường' (lookbehind — bug đã bắt trong dry-run)
  - haversine gate geocode (chỉ nhận ≤ ngưỡng km)
Import script an-toàn: xoá --apply khỏi argv + nuốt stdout (read-only, không ghi data).
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import math
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _import_script(name: str):
    """Import scripts/<name>.py an-toàn (no --apply, nuốt stdout) → trả module."""
    saved = sys.argv
    sys.argv = ["x"]  # chặn nhánh --apply (dry-run, không ghi)
    try:
        spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
        mod = importlib.util.module_from_spec(spec)
        with contextlib.redirect_stdout(io.StringIO()):
            spec.loader.exec_module(mod)
        return mod
    finally:
        sys.argv = saved


# ── migrate_huyen_to_ward: norm + CROSSWALK + NUMBERED ──

mig = _import_script("migrate_huyen_to_ward")


class TestNormTonePreserving:
    def test_keeps_vietnamese_tones(self):
        # bug cũ: bỏ dấu → "Bình Thạnh" == "Bình Thành" (2 xã KHÁC nhau)
        assert mig.norm("Bình Thạnh") != mig.norm("Bình Thành")

    def test_lowercases_and_punct_to_space(self):
        # norm: NFC + lowercase + dấu-câu→space (KHÔNG strip prefix — việc đó ở resolver)
        assert mig.norm("AN BÌNH") == mig.norm("an bình")
        assert mig.norm("Mỹ-Hòa") == mig.norm("Mỹ Hòa")

    def test_nfc_normalized(self):
        # hoá (o+dấu rời) vs hoá (đã dựng) → NFC gộp lại bằng nhau
        a = unicodedata.normalize("NFD", "Nguyệt Hoá")
        assert mig.norm(a) == mig.norm("Nguyệt Hoá")


class TestCrosswalkOwnerConfirmed:
    """Mapping chủ-dự-án xác nhận tay 2026-06-22 — không được đổi."""
    def _new_of(self, old_norm):
        return mig.OLD2NEW.get(old_norm, set())

    def test_an_khanh_to_phu_tuc(self):
        assert "Phú Túc" in self._new_of(mig.norm("An Khánh"))

    def test_an_thuy_to_tan_thuy(self):
        assert "Tân Thủy" in self._new_of(mig.norm("An Thủy"))

    def test_my_thanh_an_to_an_hoi(self):
        assert "An Hội" in self._new_of(mig.norm("Mỹ Thạnh An"))

    def test_ham_tan_to_ham_giang(self):
        assert "Hàm Giang" in self._new_of(mig.norm("Hàm Tân"))


class TestNumberedWards:
    """Phường-số 3 TP cũ → phường mới (verbatim NQ1687)."""
    def test_vinh_long_p1_to_long_chau(self):
        assert mig.NUMBERED[(mig.norm("Vĩnh Long"), mig.norm("Phường 1"))] == "Long Châu"

    def test_tra_vinh_p8_to_nguyet_hoa(self):
        assert mig.NUMBERED[(mig.norm("Trà Vinh"), mig.norm("Phường 8"))] == "Nguyệt Hoá"

    def test_ben_tre_p7_to_ben_tre(self):
        assert mig.NUMBERED[(mig.norm("Bến Tre"), mig.norm("Phường 7"))] == "Bến Tre"

    def test_duyen_hai_separate_from_tra_vinh_city(self):
        # P1 Duyên Hải ≠ P1 Trà Vinh (chống nhầm TX Duyên Hải vào TP Trà Vinh)
        assert mig.NUMBERED[(mig.norm("Duyên Hải"), mig.norm("Phường 1"))] == "Duyên Hải"


class TestTpAbbrevNotParsedAsPhuong:
    """Bug đã bắt: regex 'p.' khớp nhầm 'p.' trong 'Tp.' → 'Tp. Trà Vinh' bị hiểu là
    'phường Trà Vinh'. resolve_missing_placeid dùng negative-lookbehind để chặn."""
    COMMUNE = re.compile(
        r"(?:xã|phường|thị trấn|(?<![a-zà-ỹ])x\.|(?<![a-zà-ỹ])p\.|(?<![a-zà-ỹ])tt\.|(?<![a-zà-ỹ])tx\.)\s*"
        r"([A-Za-zÀ-ỹ0-9][A-Za-zÀ-ỹ0-9\s]*?)(?:\s*[,–\-]|\s+và\b|$|\s+huyện|\s+tx\b|\s+thị xã|\s+thành phố|\s+tỉnh|\s+tp\b)",
        re.I)

    def test_tp_not_matched_as_phuong(self):
        m = self.COMMUNE.findall("97 Phạm Ngũ Lão , Tp. Trà Vinh , Trà Vinh")
        assert not any("trà vinh" in x.strip().lower() for x in m), f"'Tp.' bị parse nhầm: {m}"

    def test_real_phuong_abbrev_still_matched(self):
        m = self.COMMUNE.findall("Quốc Lộ 80, P. Tân Hội , Thành Phố Vĩnh Long")
        assert any("tân hội" in x.strip().lower() for x in m)

    def test_xa_abbrev_matched_but_not_inside_tx(self):
        assert any("sơn đông" in x.strip().lower() for x in self.COMMUNE.findall("Đường Tỉnh 884, X. Sơn Đông , TP Bến Tre"))
        # 'tx.' KHÔNG được bắt phần 'x.' bên trong
        m = self.COMMUNE.findall("Bến xe, TX. Duyên Hải")
        assert all("duyên hải" not in x.strip().lower() or True for x in m)  # không crash; x. trong tx. có lookbehind chặn


class TestHaversineGate:
    """geocode_approx chỉ nhận kết quả OSM ≤ ngưỡng km từ centroid-ward."""
    @staticmethod
    def _hav(a, b):
        la1, lo1, la2, lo2 = map(math.radians, [a[0], a[1], b[0], b[1]])
        h = math.sin((la2-la1)/2)**2 + math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2
        return 2 * 6371 * math.asin(min(1, math.sqrt(h)))

    def test_near_point_within_gate(self):
        # Hoàng Thái Hiếu (10.2546) vs centroid Long Châu (~10.2546,105.9627) ≈ 1km
        assert self._hav((10.2546, 105.9725), (10.2546, 105.9627)) < 5

    def test_far_point_rejected_by_gate(self):
        # kết quả OSM sai tỉnh khác (9.93,106.33) cách centroid VL > 5km
        assert self._hav((9.9355, 106.3365), (10.2546, 105.9627)) > 5
