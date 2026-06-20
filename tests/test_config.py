"""Tests for centralized config module."""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:9999/v1")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:8360")


class TestSettings:
    def test_defaults(self, monkeypatch):
        # Isolate from the runner's ENVIRONMENT var and any .env file so this
        # asserts the CODE default, not the ambient environment.
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        from config import Settings
        s = Settings(_env_file=None, LLM_API_KEY="k", LLM_BASE_URL="u", ADMIN_API_KEY="a")
        assert s.LLM_MODEL  # has a value (may come from .env or default)
        assert s.LLM_TIMEOUT == 30
        assert s.ENVIRONMENT == "development"
        assert s.is_production is False

    def test_cors_list(self):
        from config import Settings
        s = Settings(CORS_ORIGINS="http://a,http://b, http://c")
        assert s.cors_origins_list == ["http://a", "http://b", "http://c"]

    def test_admin_telegram_ids(self):
        from config import Settings
        s = Settings(ADMIN_TELEGRAM_IDS="123,456, 789")
        assert s.admin_telegram_ids_set == {"123", "456", "789"}

    def test_empty_telegram_ids(self):
        from config import Settings
        s = Settings(ADMIN_TELEGRAM_IDS="")
        assert s.admin_telegram_ids_set == set()

    def test_production_validation_passes(self):
        from config import Settings
        s = Settings(
            ENVIRONMENT="production",
            LLM_API_KEY="real-key",
            LLM_BASE_URL="https://api.example.com",
            ADMIN_API_KEY="admin-key",
        )
        assert s.is_production is True

    def test_production_missing_key_fails(self):
        from config import Settings
        with pytest.raises(ValueError, match="LLM_API_KEY"):
            Settings(ENVIRONMENT="production", LLM_API_KEY="", LLM_BASE_URL="u", ADMIN_API_KEY="a")

    def test_bool_env_parsing(self):
        from config import Settings
        s = Settings(BUILD_SEARCH_INDEXES=False, AUTONOMOUS_AGENT_ENABLED=True)
        assert s.BUILD_SEARCH_INDEXES is False
        assert s.AUTONOMOUS_AGENT_ENABLED is True

    def test_singleton_import(self):
        from config import settings
        assert settings is not None
        assert hasattr(settings, "LLM_MODEL")
