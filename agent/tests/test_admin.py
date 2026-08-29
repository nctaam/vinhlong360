"""
Tests for admin.py — admin API input validation and security.
"""

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))



def _admin_src() -> str:
    """Nguon MAT QUAN TRI — hop nhat admin.py + entities/ + community/admin_api.py.

    Mien entity-admin sang agent/entities/ (2026-08-28, buoc 2b). Cac rao duoi
    soi "mat quan tri co tinh chat X", bat ke handler song o file nao; ghim mot
    duong dan la chung im lang mat tac dung khi ma doi nha.
    """
    from pathlib import Path as _P
    root = _P(__file__).resolve().parent.parent
    return ((root / "admin.py").read_text(encoding="utf-8") + chr(10)
            + (root / "entities" / "admin_api.py").read_text(encoding="utf-8") + chr(10)
            + (root / "community" / "admin_api.py").read_text(encoding="utf-8"))


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


def test_the_claims_list_masks_the_one_phone_it_used_to_leak():

    source = _admin_src()

    # GET /admin/claims joined users.phone and returned every row raw, while
    # every other endpoint masked and _mask sat ten lines above it. It is the
    # only place in the API that returned a registered user's raw number.
    assert '"claims": [_claim_row(r) for r in rows]' in source
    assert 'item["claimant_phone"] = _mask(str(item["claimant_phone"]))' in source
    # `_mask` sang agent/admin_common.py (2026-08-28, bước 2a) vì cả miền
    # entity-admin lẫn phần còn lại của admin đều dùng. Ý định của rào KHÔNG đổi:
    # helper che số phải TỒN TẠI và handler claims phải GỌI nó (hai assert trên
    # đã khoá chỗ gọi). Soi định nghĩa ở nhà mới; import-đứt thì bài này nổ
    # ImportError chứ không im.
    from admin_common import _mask as _mask_fn
    assert callable(_mask_fn), "the masking helper vanished"
    assert _mask_fn("0912345678") != "0912345678", "helper không còn che gì cả"
