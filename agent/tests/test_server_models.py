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
import importlib
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

    def setup_method(self):
        try:
            from server import FeedbackRequest
            self.FeedbackRequest = FeedbackRequest
        except Exception:
            pytest.skip("Cannot import FeedbackRequest")

    def test_valid_feedback(self):
        req = self.FeedbackRequest(rating=1)
        assert req.rating == 1
        assert req.user_id == "anonymous"

    def test_rating_0(self):
        req = self.FeedbackRequest(rating=0)
        assert req.rating == 0

    def test_invalid_rating_high(self):
        with pytest.raises(ValidationError):
            self.FeedbackRequest(rating=5)

    def test_invalid_rating_negative(self):
        with pytest.raises(ValidationError):
            self.FeedbackRequest(rating=-1)

    def test_query_too_long(self):
        with pytest.raises(ValidationError):
            self.FeedbackRequest(rating=1, query="x" * 2001)

    def test_entity_id(self):
        req = self.FeedbackRequest(rating=1, entity_id="cam-sanh-vinh-long")
        assert req.entity_id == "cam-sanh-vinh-long"


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
