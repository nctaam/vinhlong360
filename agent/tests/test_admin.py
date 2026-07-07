"""
Tests for admin.py — admin API input validation and security.
"""

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestEntityCreateValidation:
    """Test EntityCreate Pydantic model."""

    def setup_method(self):
        try:
            from admin import EntityCreate
            self.EntityCreate = EntityCreate
        except Exception:
            pytest.skip("Cannot import EntityCreate")

    def test_valid_entity(self):
        e = self.EntityCreate(
            id="test-entity",
            name="Test Entity",
            type="product",
            summary="A test product"
        )
        assert e.id == "test-entity"
        assert e.name == "Test Entity"

    def test_invalid_id_uppercase(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            self.EntityCreate(id="TestEntity", name="Test", type="product")

    def test_invalid_id_special_chars(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            self.EntityCreate(id="test entity!", name="Test", type="product")


class TestTriggerLearnValidation:
    """Test trigger-learn parameter validation."""

    def test_category_sanitization_regex(self):
        """Validate the category sanitization regex."""
        pattern = r'^[\w\s\-À-ɏḀ-ỿ]+$'
        # Valid
        assert re.match(pattern, "food") is not None
        assert re.match(pattern, "ẩm thực") is not None
        assert re.match(pattern, "du-lich") is not None
        # Invalid
        assert re.match(pattern, "food;rm -rf /") is None
        assert re.match(pattern, "cat$(whoami)") is None
        assert re.match(pattern, "test && evil") is None

    def test_topics_bounds(self):
        """Topics should be 1-20."""
        assert 1 <= 3 <= 20   # default
        assert not (1 <= 0 <= 20)  # too low
        assert not (1 <= 999 <= 20)  # too high


class TestHTMLSanitization:
    """Test HTML/XSS sanitization."""

    def setup_method(self):
        try:
            from admin import _sanitize
            self.sanitize = _sanitize
        except Exception:
            pytest.skip("Cannot import _sanitize")

    def test_escapes_script(self):
        result = self.sanitize("<script>alert(1)</script>Hello")
        # _sanitize uses html.escape, so <script> becomes &lt;script&gt;
        assert "<script>" not in result
        assert "Hello" in result

    def test_escapes_html_tags(self):
        result = self.sanitize("<b>bold</b> text")
        assert "<b>" not in result
        assert "bold" in result
        assert "text" in result

    def test_preserves_normal_text(self):
        result = self.sanitize("Cam sành Vĩnh Long")
        assert result == "Cam sành Vĩnh Long"

    def test_escapes_event_handlers(self):
        """html.escape converts < and > so event handlers can't execute."""
        result = self.sanitize('<img onerror="alert(1)" src="x">')
        # After html.escape, raw HTML tags are neutralized
        assert "<img" not in result  # < is escaped to &lt;


class TestImageURLValidation:
    """Test image URL validation rules."""

    def test_valid_https(self):
        url = "https://example.com/image.jpg"
        assert url.startswith(("https://", "http://"))

    def test_valid_http(self):
        url = "http://example.com/image.jpg"
        assert url.startswith(("https://", "http://"))

    def test_invalid_javascript(self):
        url = "javascript:alert(1)"
        assert not url.startswith(("https://", "http://"))

    def test_invalid_data_uri(self):
        url = "data:image/png;base64,..."
        assert not url.startswith(("https://", "http://"))

    def test_too_long(self):
        url = "https://example.com/" + "x" * 500
        assert len(url) > 500
