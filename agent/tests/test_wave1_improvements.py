"""Audit Đợt 1 — quick wins (perf/bug). Test hành vi các fix độc lập không-schema."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import public_api  # noqa: E402
import social  # noqa: E402


def test_score_one_itinerary_uses_dict_index():
    # public_api: đổi từ quét tuyến tính public sang dict O(1). Vẫn phải chấm điểm đúng.
    ent = {"id": "ent1", "season": {"months": [6]}, "images": ["a.webp"]}
    idx = {"ent1": ent}
    it = {"stops": [{"entityId": "ent1"}], "duration": "2 ngày"}
    score = public_api._score_one_itinerary(it, idx, 6)
    assert score >= 2.5  # in-season (+2.0) + có ảnh (+0.5)


def test_score_one_itinerary_missing_entity_no_crash():
    # entity không có trong index → bỏ qua, không cộng điểm, không lỗi.
    it = {"stops": [{"entityId": "khong-ton-tai"}]}
    assert public_api._score_one_itinerary(it, {}, 6) == 0.0


def test_extract_hashtags_vietnamese():
    # Backend trích hashtag Unicode (tiếng Việt OK). FE safe.ts đã sửa \\w→\\p{L} cho khớp
    # (JS \\w chỉ [A-Za-z0-9_] kể cả cờ u). Test này khoá parity nguồn dữ liệu.
    tags = social._extract_hashtags("Ghé #đặcsản và #OCOP2024 nhé")
    assert "đặcsản" in tags
    assert "ocop2024" in tags
