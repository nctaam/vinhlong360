"""
Tests for server.py Pydantic models — input validation.
"""

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# We need to import just the models without starting the server.
# The models are defined in server.py after FastAPI setup, so we import them
# by importing the module carefully.

# Import models via exec to avoid full server init
import os

os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:9999/v1")


class TestChatRequest:
    """Test ChatRequest validation."""

    def setup_method(self):
        # Lazy import to avoid server startup side effects
        try:
            from server import ChatRequest
            self.ChatRequest = ChatRequest
        except Exception:
            pytest.skip("Cannot import ChatRequest (server dependencies missing)")

    def test_valid_message(self):
        req = self.ChatRequest(message="Hello")
        assert req.message == "Hello"

    def test_empty_message(self):
        with pytest.raises(ValidationError):
            self.ChatRequest(message="")

    def test_message_too_long(self):
        with pytest.raises(ValidationError):
            self.ChatRequest(message="x" * 2001)

    def test_html_stripped(self):
        req = self.ChatRequest(message="<script>alert(1)</script>Hello")
        assert "<script>" not in req.message
        assert "Hello" in req.message

    def test_default_history(self):
        req = self.ChatRequest(message="test")
        assert req.history == []

    def test_session_id_optional(self):
        req = self.ChatRequest(message="test")
        assert req.session_id is None


class TestFeedbackRequest:
    """Test FeedbackRequest validation."""

    RECEIPT = "A" * 43

    def setup_method(self):
        try:
            from server import FeedbackRequest
            self.FeedbackRequest = FeedbackRequest
        except Exception:
            pytest.skip("Cannot import FeedbackRequest")

    def test_valid_feedback(self):
        req = self.FeedbackRequest(receipt=self.RECEIPT, rating=1)
        assert req.receipt == self.RECEIPT
        assert req.rating == 1

    def test_rating_0(self):
        req = self.FeedbackRequest(receipt=self.RECEIPT, rating=0)
        assert req.rating == 0

    def test_invalid_rating_high(self):
        with pytest.raises(ValidationError):
            self.FeedbackRequest(receipt=self.RECEIPT, rating=5)

    def test_invalid_rating_negative(self):
        with pytest.raises(ValidationError):
            self.FeedbackRequest(receipt=self.RECEIPT, rating=-1)

    def test_query_is_forbidden(self):
        with pytest.raises(ValidationError):
            self.FeedbackRequest(receipt=self.RECEIPT, rating=1, query="private")

    def test_entity_id_is_forbidden(self):
        with pytest.raises(ValidationError):
            self.FeedbackRequest(
                receipt=self.RECEIPT,
                rating=1,
                entity_id="cam-sanh-vinh-long",
            )


class TestGuardrailCheckRequest:
    """Test GuardrailCheckRequest validation."""

    def setup_method(self):
        try:
            from server import GuardrailCheckRequest
            self.GuardrailCheckRequest = GuardrailCheckRequest
        except Exception:
            pytest.skip("Cannot import GuardrailCheckRequest")

    def test_valid(self):
        req = self.GuardrailCheckRequest(message="test input")
        assert req.message == "test input"
        assert req.session_id == "test"

    def test_empty_message(self):
        with pytest.raises(ValidationError):
            self.GuardrailCheckRequest(message="")

    def test_too_long(self):
        with pytest.raises(ValidationError):
            self.GuardrailCheckRequest(message="x" * 5001)


class TestDynamicAgentCreateRequest:
    """Test DynamicAgentCreateRequest validation."""

    def setup_method(self):
        try:
            from server import DynamicAgentCreateRequest
            self.DynamicAgentCreateRequest = DynamicAgentCreateRequest
        except Exception:
            pytest.skip("Cannot import DynamicAgentCreateRequest")

    def test_valid(self):
        req = self.DynamicAgentCreateRequest(name="test-agent")
        assert req.name == "test-agent"

    def test_empty_name(self):
        with pytest.raises(ValidationError):
            self.DynamicAgentCreateRequest(name="")

    def test_name_too_long(self):
        with pytest.raises(ValidationError):
            self.DynamicAgentCreateRequest(name="x" * 101)

    def test_with_all_fields(self):
        req = self.DynamicAgentCreateRequest(
            name="test",
            description="A test agent",
            trigger_patterns=["hello", "hi"],
            system_prompt_addon="Be friendly",
            tool_whitelist=["search"],
        )
        assert len(req.trigger_patterns) == 2

# GĐ6/11: TestMultimodalAnalyzeRequest đã gỡ — model thuộc module multimodal_engine (đã xoá).


# ── Task 7: the case router must be mounted inert and classified no-store ──

def _server_source() -> str:
    return (Path(__file__).resolve().parents[1] / "server.py").read_text(encoding="utf-8")


def test_the_case_router_is_mounted_after_the_public_router():
    source = _server_source()
    assert "from cases.public_api import case_public_router" in source
    assert source.index("app.include_router(public_router)") < source.index(
        "app.include_router(case_public_router)"
    )


def test_case_credential_headers_are_allowed_by_cors():
    source = _server_source()
    allow_headers = source.split("allow_headers=[", 1)[1].split("]", 1)[0]
    assert "Idempotency-Key" in allow_headers
    assert "X-Case-CSRF" in allow_headers


def test_case_responses_are_classified_no_store():
    source = _server_source()
    no_store_block = source.split('"/api/notification-preferences",', 1)[1].split("))", 1)[0]
    assert '"/api/cases"' in no_store_block


def test_the_chat_khong_mang_van_xuoi_ocop_tho():
    """Thẻ chat từng gán `card["ocop"] = attrs["ocop"]` ở BỐN nơi, và bộ lọc
    tìm kiếm rút hạng bằng chữ số đầu tiên gặp ở bất kỳ đâu."""
    import server

    card: dict = {}
    e = {
        "id": "dua-sap-cau-ke", "name": "Dua sap Cau Ke",
        "attributes": {"ocop": "VICOSAP: 4 SP OCOP 5 sao quoc gia + 7 SP OCOP 4 sao"},
    }
    server._search_card_practical(card, e["attributes"], e)
    assert card.get("ocop") == "OCOP"
    assert "VICOSAP" not in str(card)


def test_the_chat_neu_hang_khi_co_that():
    import server

    card: dict = {}
    e = {"id": "x", "name": "X", "attributes": {"ocop_star": 4}}
    server._search_card_practical(card, e["attributes"], e)
    assert card.get("ocop") == "OCOP 4 sao"
