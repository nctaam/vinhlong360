"""Tests for scripts/generate_seo_meta.py."""

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.generate_seo_meta import _vietnamese_to_slug, _make_meta_description


class TestVietnameseToSlug:
    def test_basic_vietnamese(self):
        assert _vietnamese_to_slug("Chợ Nổi Cái Bè") == "cho-noi-cai-be"

    def test_dbar(self):
        assert _vietnamese_to_slug("Đền Thờ Đức Thánh") == "den-tho-duc-thanh"

    def test_special_chars(self):
        slug = _vietnamese_to_slug("Bánh xèo (Bến Tre)")
        assert slug == "banh-xeo-ben-tre"

    def test_multiple_spaces(self):
        slug = _vietnamese_to_slug("  Cầu   Mỹ   Thuận  ")
        assert slug == "cau-my-thuan"

    def test_empty_string(self):
        assert _vietnamese_to_slug("") == ""

    def test_numbers_preserved(self):
        slug = _vietnamese_to_slug("Khách sạn 360")
        assert "360" in slug


class TestMakeMetaDescription:
    def test_short_summary(self):
        desc = _make_meta_description("Ngắn gọn.", 155)
        assert desc == "Ngắn gọn."

    def test_truncate_long_summary(self):
        long_text = "A" * 200
        desc = _make_meta_description(long_text, 155)
        assert len(desc) <= 158  # 155 + "..."
        assert desc.endswith("...")

    def test_empty_summary(self):
        desc = _make_meta_description("", 155)
        assert desc == ""


class TestIntegration:
    def test_slug_and_desc_together(self):
        name = "Chợ Nổi Cái Bè"
        summary = "Chợ nổi nổi tiếng nhất ĐBSCL, nơi buôn bán trên sông."
        slug = _vietnamese_to_slug(name)
        desc = _make_meta_description(summary, 155)
        assert slug == "cho-noi-cai-be"
        assert desc == summary  # short enough, no truncation
