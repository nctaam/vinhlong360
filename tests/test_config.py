"""Tests for centralized config module."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:9999/v1")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:8360")


def _production_settings(**overrides):
    from config import Settings

    values = {
        "ENVIRONMENT": "production",
        "LLM_API_KEY": "k",
        "LLM_BASE_URL": "https://api.example.com",
        "ADMIN_API_KEY": "a",
        "DATABASE_URL": "postgresql://user:pass@localhost/db",
        "ENTITY_DETAILS_TABLES": True,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


@pytest.mark.parametrize("database_url", [
    "postgres://user:pass@localhost/db",
    "postgresql://user:pass@localhost/db",
])
def test_production_accepts_postgresql_urls(database_url):
    assert _production_settings(DATABASE_URL=database_url).is_production is True


def test_database_backend_accepts_postgres_url():
    agent_dir = Path(__file__).resolve().parents[1] / "agent"
    env = os.environ.copy()
    env["DATABASE_URL"] = "postgres://user:pass@localhost/db"
    env["ENVIRONMENT"] = "test"

    result = subprocess.run(
        [sys.executable, "-c", "import database; print(database.USE_PG)"],
        cwd=agent_dir,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "True"


def test_production_rejects_sqlite_database_url():
    with pytest.raises(ValueError, match="DATABASE_URL.*PostgreSQL"):
        _production_settings(DATABASE_URL="sqlite:///knowledge.db")


def test_production_requires_entity_detail_tables():
    with pytest.raises(ValueError, match="ENTITY_DETAILS_TABLES"):
        _production_settings(ENTITY_DETAILS_TABLES=False)


def test_production_validation_error_rendering_hides_sensitive_inputs():
    from config import Settings

    secret = "key-canary"
    dsn = "sqlite://dsn-canary"

    with pytest.raises(ValueError, match="PostgreSQL") as caught:
        Settings.model_validate(
            {
                "ENVIRONMENT": "production",
                "LLM_API_KEY": secret,
                "DATABASE_URL": dsn,
            }
        )

    rendered = str(caught.value)
    assert "input_value" not in rendered
    assert secret not in rendered
    assert dsn not in rendered


def test_development_still_allows_sqlite_and_disabled_detail_tables():
    from config import Settings

    settings = Settings(
        _env_file=None,
        ENVIRONMENT="development",
        DATABASE_URL="sqlite:///knowledge.db",
        ENTITY_DETAILS_TABLES=False,
    )
    assert settings.is_production is False


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
        assert s.ACCOUNT_ERASURE_DEADLINE_DAYS == 30
        assert s.RECOVERY_ENABLED_DURING_GRACE_PERIOD is True
        assert s.FEEDBACK_MODE == "telemetry_only"
        assert s.FEEDBACK_RECEIPT_TTL_HOURS == 24
        assert s.RETAIN_DEIDENTIFIED_AGGREGATES is True
        assert s.ACCOUNT_DELETE_GRACE_DAYS == 30

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
        s = _production_settings(
            LLM_API_KEY="real-key",
            LLM_BASE_URL="https://api.example.com",
            ADMIN_API_KEY="admin-key",
            JWT_SECRET="jwt-secret",
        )
        assert s.is_production is True

    def test_production_missing_key_fails(self):
        from config import Settings
        with pytest.raises(ValueError, match="LLM_API_KEY"):
            Settings(ENVIRONMENT="production", LLM_API_KEY="", LLM_BASE_URL="u",
                     ADMIN_API_KEY="a", JWT_SECRET="j", DATABASE_URL="postgresql://x")

    def test_production_missing_jwt_secret_is_allowed(self):
        # JWT_SECRET is intentionally OPTIONAL in production. Sessions are cookie-based
        # (not JWT-signed), and twofactor.py reads JWT_SECRET only as an optional
        # fallback for the TOTP encryption key (TOTP_ENC_KEY > JWT_SECRET > ADMIN_API_KEY),
        # so the app boots fine without it. Requiring it would gate deploys on a key the
        # app does not need. An empty JWT_SECRET in production must therefore NOT raise.
        s = _production_settings(LLM_BASE_URL="u", JWT_SECRET="",
                                 DATABASE_URL="postgresql://x")
        assert s.JWT_SECRET == ""
        assert s.is_production is True

    def test_production_missing_database_url_fails(self):
        from config import Settings
        with pytest.raises(ValueError, match="DATABASE_URL"):
            Settings(ENVIRONMENT="production", LLM_API_KEY="k", LLM_BASE_URL="u",
                     ADMIN_API_KEY="a", JWT_SECRET="j", DATABASE_URL="")

    def test_production_rejects_privacy_policy_override(self):
        from config import Settings
        with pytest.raises(ValueError, match="ACCOUNT_ERASURE_DEADLINE_DAYS"):
            Settings(
                _env_file=None,
                ENVIRONMENT="production",
                LLM_API_KEY="k",
                LLM_BASE_URL="u",
                ADMIN_API_KEY="a",
                DATABASE_URL="postgresql://x",
                ENTITY_DETAILS_TABLES=True,
                ACCOUNT_ERASURE_DEADLINE_DAYS=20,
            )

    def test_bool_env_parsing(self):
        from config import Settings
        s = Settings(BUILD_SEARCH_INDEXES=False, AUTONOMOUS_AGENT_ENABLED=True)
        assert s.BUILD_SEARCH_INDEXES is False
        assert s.AUTONOMOUS_AGENT_ENABLED is True

    def test_singleton_import(self):
        from config import settings
        assert settings is not None
        assert hasattr(settings, "LLM_MODEL")
