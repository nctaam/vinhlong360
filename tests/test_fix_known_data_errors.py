"""Đổi thang điểm phải chỉ đụng vào điểm bất khả, không đụng điểm hợp lệ."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from fix_known_data_errors import fix_rating_scale  # noqa: E402


@pytest.mark.parametrize("text,expected", [
    ("Đánh giá: 8.9/5 (11 đánh giá).", "Đánh giá: 8.9/10 (11 đánh giá)."),
    ("Đánh giá: 10.0/5", "Đánh giá: 10.0/10"),
    ("Đánh giá: 7,3/5", "Đánh giá: 7,3/10"),
])
def test_diem_bat_kha_tren_thang_5_duoc_doi_sang_thang_10(text, expected):
    assert fix_rating_scale(text) == expected


@pytest.mark.parametrize("text", [
    "Đánh giá: 4.5/5 (20 đánh giá).",
    "Đánh giá: 5.0/5",
    "Đánh giá: 3,8/5",
])
def test_diem_hop_le_tren_thang_5_giu_nguyen(text):
    assert fix_rating_scale(text) == text


def test_khong_dung_toi_con_so_khong_phai_danh_gia():
    text = "Quán mở 5:00 - 19:00, cách bến 2/5 km theo đường tắt."
    assert fix_rating_scale(text) == text


def test_chay_lai_khong_doi_them():
    once = fix_rating_scale("Đánh giá: 8.9/5")
    assert fix_rating_scale(once) == once
