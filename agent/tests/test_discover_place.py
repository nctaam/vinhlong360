"""
Test discover_province._place_for — gán placeId cho entity phát hiện tự động.

Bảo vệ fix chống tái nhiễm lỗi "thùng chứa": KHÔNG dồn entity không khớp tên
vào ward đầu tiên của khu vực; trả None (chưa phân loại) thay vì gán sai xã.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from discover_province import _place_for

PLACES = [
    {"id": "xa-an-binh", "type": "place", "name": "Xã An Bình", "area": "vinh-long"},
    {"id": "p-long-chau", "type": "place", "name": "Phường Long Châu", "area": "vinh-long"},
    {"id": "xa-ba-tri", "type": "place", "name": "Xã Ba Tri", "area": "ben-tre"},
]


def test_matches_ward_by_name_in_location():
    assert _place_for("vinh-long", "Ấp Bình Thuận, Xã An Bình", PLACES) == "xa-an-binh"
    assert _place_for("ben-tre", "Chợ Ba Tri, huyện Ba Tri", PLACES) == "xa-ba-tri"


def test_no_match_returns_none_not_first_place():
    # Địa chỉ không nêu tên ward nào → KHÔNG được dồn vào ward đầu tiên (xa-an-binh).
    assert _place_for("vinh-long", "Một nơi nào đó không rõ xã", PLACES) is None


def test_empty_location_returns_none():
    assert _place_for("vinh-long", "", PLACES) is None


def test_respects_area_scope():
    # location nêu 'Ba Tri' nhưng tìm trong area vinh-long → không khớp (Ba Tri ở ben-tre).
    assert _place_for("vinh-long", "Chợ Ba Tri", PLACES) is None
