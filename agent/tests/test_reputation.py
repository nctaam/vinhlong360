"""Unit tests for the anti-inflation reputation system (_diminish, _calc_points, _level_for)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from social import _diminish, _calc_points, _level_for  # noqa: E402


class TestDiminish:
    def test_zero(self):
        assert _diminish(0, [(10, 5)]) == 0

    def test_within_first_tier(self):
        assert _diminish(5, [(10, 5), (20, 3)]) == 25

    def test_exactly_first_tier(self):
        assert _diminish(10, [(10, 5), (20, 3)]) == 50

    def test_spans_two_tiers(self):
        assert _diminish(15, [(10, 5), (20, 3)]) == 50 + 5 * 3

    def test_beyond_all_tiers_capped(self):
        assert _diminish(100, [(10, 5), (20, 3)]) == 50 + 60

    def test_single_tier(self):
        assert _diminish(30, [(20, 1)]) == 20


class TestCalcPoints:
    def test_zero_everything(self):
        assert _calc_points(0, 0, 0, 0, 0, 0) == 0

    def test_review_diminishing_max(self):
        # 10*5 + 20*3 + 20*1 = 130 max
        assert _calc_points(50, 50, 0, 0, 0, 0) == 130

    def test_post_diminishing_max(self):
        # posts - reviews = 100: 15*2 + 15*1 = 45 max
        assert _calc_points(0, 100, 0, 0, 0, 0) == 45

    def test_photo_diminishing_max(self):
        # 10*3 + 10*1 = 40 max
        assert _calc_points(0, 0, 100, 0, 0, 0) == 40

    def test_follower_cap(self):
        # 20*1 = 20 max
        assert _calc_points(0, 0, 0, 100, 0, 0) == 20

    def test_place_cap(self):
        # 10*2 + 10*1 = 30 max
        assert _calc_points(0, 0, 0, 0, 100, 0) == 30

    def test_like_cap(self):
        # 50*1 = 50 max
        assert _calc_points(0, 0, 0, 0, 0, 100) == 50

    def test_theoretical_max(self):
        assert _calc_points(50, 100, 100, 100, 100, 100) == 315

    def test_moderate_user(self):
        # 5 reviews (5*5=25), 3 extra posts (3*2=6), 2 photos (2*3=6),
        # 8 followers (8*1=8), 3 places (3*2=6), 10 likes (10*1=10)
        assert _calc_points(5, 8, 2, 8, 3, 10) == 25 + 6 + 6 + 8 + 6 + 10

    def test_spam_one_category_capped(self):
        only_reviews = _calc_points(500, 500, 0, 0, 0, 0)
        diverse = _calc_points(10, 15, 10, 15, 10, 30)
        assert diverse > only_reviews * 0.5


class TestLevelFor:
    def test_level_1(self):
        level, label = _level_for(0)
        assert level == 1
        assert label == "Người mới"

    def test_level_2_boundary(self):
        assert _level_for(19)[0] == 1
        assert _level_for(20)[0] == 2

    def test_level_3_boundary(self):
        assert _level_for(79)[0] == 2
        assert _level_for(80)[0] == 3

    def test_level_4_boundary(self):
        assert _level_for(199)[0] == 3
        assert _level_for(200)[0] == 4
        assert _level_for(200)[1] == "Đại sứ"

    def test_ambassador_needs_diversity(self):
        """Đại sứ (200+) không thể đạt chỉ bằng 1 loại đóng góp."""
        only_reviews = _calc_points(50, 50, 0, 0, 0, 0)
        assert only_reviews < 200
        only_posts = _calc_points(0, 100, 0, 0, 0, 0)
        assert only_posts < 200
        only_photos = _calc_points(0, 0, 100, 0, 0, 0)
        assert only_photos < 200
