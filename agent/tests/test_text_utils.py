"""Tests for text_utils.py — shared Vietnamese text utilities."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from text_utils import slugify, strip_diacritics, normalize_name


class TestSlugify:
    def test_basic(self):
        assert slugify("Vĩnh Long") == "vinh-long"

    def test_removes_diacritics(self):
        assert slugify("Chợ nổi Cái Bè") == "cho-noi-cai-be"

    def test_handles_d_stroke(self):
        assert slugify("Đình Tân Giai") == "dinh-tan-giai"

    def test_collapses_spaces(self):
        assert slugify("a   b   c") == "a-b-c"

    def test_strips_special_chars(self):
        assert slugify("hello! @world#") == "hello-world"

    def test_truncates_at_max_len(self):
        result = slugify("a" * 100)
        assert len(result) == 80

    def test_custom_max_len(self):
        result = slugify("abcdef", max_len=3)
        assert result == "abc"

    def test_empty(self):
        assert slugify("") == ""


class TestStripDiacritics:
    def test_basic(self):
        assert strip_diacritics("Vĩnh Long") == "Vinh Long"

    def test_d_stroke(self):
        assert strip_diacritics("đặc sản Đồng Tháp") == "dac san dong Thap"

    def test_no_diacritics(self):
        assert strip_diacritics("hello") == "hello"


class TestNormalizeName:
    def test_basic(self):
        assert normalize_name("Vĩnh Long") == "vinh long"

    def test_strips_whitespace(self):
        assert normalize_name("  Bến Tre  ") == "ben tre"

    def test_none_input(self):
        assert normalize_name(None) == ""

    def test_empty(self):
        assert normalize_name("") == ""
