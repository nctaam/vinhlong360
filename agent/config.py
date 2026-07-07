"""Centralized configuration with validation.

Usage:
    from config import settings
    settings.LLM_API_KEY      # str (required in production)
    settings.LLM_MODEL        # str with default
    settings.is_production     # bool
"""

from pathlib import Path

from dotenv import load_dotenv
from pydantic import model_validator
from pydantic_settings import BaseSettings

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class Settings(BaseSettings):
    # ── LLM ──
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = ""
    LLM_MODEL: str = "cx/gpt-5.4"
    LLM_MODEL_MINI: str = "cx/gpt-5.4-mini"
    LLM_TIMEOUT: int = 30

    # ── Database ──
    DATABASE_URL: str = ""
    REDIS_URL: str = ""

    # ── Security ──
    ADMIN_API_KEY: str = ""
    CORS_ORIGINS: str = "http://localhost:8360,http://localhost:3000,https://vinhlong360.vn"
    JWT_SECRET: str = ""

    # ── SMS (eSMS) ──
    ESMS_API_KEY: str = ""
    ESMS_SECRET: str = ""
    ESMS_BRANDNAME: str = "VinhLong360"

    # ── Bots ──
    TELEGRAM_BOT_TOKEN: str = ""
    ZALO_OA_ACCESS_TOKEN: str = ""
    ZALO_OA_SECRET: str = ""
    ADMIN_TELEGRAM_IDS: str = ""

    # ── Storage ──
    S3_ENDPOINT: str = ""
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_BUCKET: str = ""
    S3_PUBLIC_URL: str = ""

    # ── Server behavior ──
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    BUILD_SEARCH_INDEXES: bool = True
    BACKGROUND_INDEX_BUILD: bool = True
    SCHEDULER_ENABLED: bool = True
    LLM_JUDGE_ENABLED: bool = False
    DESTRUCTIVE_OPS_LOCKED: str = "1"

    # ── Autonomous agent ──
    AUTONOMOUS_AGENT_ENABLED: bool = False
    AUTONOMOUS_AGENT_MAX_CALLS_PER_DAY: int = 20
    SCHEDULER_ENABLE_AUTONOMOUS_TASKS: bool = False

    # ── 2FA (Wave 4) ── kill-switch: OFF until TOTP_ENC_KEY is set by the owner
    TWO_FACTOR_ENABLED: bool = False

    # ── Cost limits ──
    COST_DAILY_LIMIT: float = 10.0
    COST_MONTHLY_LIMIT: float = 200.0

    # ── Rate limits ──
    OTP_IP_LIMIT: int = 5
    OTP_IP_WINDOW: int = 600
    LOGIN_IP_LIMIT: int = 10
    LOGIN_IP_WINDOW: int = 300
    LOGIN_PHONE_LIMIT: int = 5
    LOGIN_PHONE_WINDOW: int = 900
    CHECK_PHONE_IP_LIMIT: int = 10
    CHECK_PHONE_IP_WINDOW: int = 300
    RL_POST_LIMIT: int = 10
    RL_POST_WINDOW: int = 600
    RL_COMMENT_LIMIT: int = 20
    RL_COMMENT_WINDOW: int = 300
    RL_LIKE_LIMIT: int = 60
    RL_LIKE_WINDOW: int = 60
    AUDIT_MAX_LINES: int = 5000

    # ── Business rules ──
    MAX_COMMENTS_PER_POST: int = 500
    MAX_CONCURRENT_SESSIONS: int = 5
    COMMENT_EDIT_WINDOW_HOURS: int = 24
    RL_POST_DAILY_LIMIT: int = 50
    RL_POST_DAILY_WINDOW: int = 86400
    TRENDING_CACHE_TTL: int = 120
    BACKUP_COOLDOWN: int = 300
    ACCOUNT_DELETE_GRACE_DAYS: int = 30
    PBKDF2_ITERATIONS: int = 310_000
    SESSION_EXPIRE_DAYS: int = 30
    OTP_EXPIRE_MINUTES: int = 5

    # ── Misc ──
    DYNAMIC_AGENT_MAX: int = 10
    KB_CONTEXT_MODE: str = "index"
    GUARDRAIL_SESSION_BUDGET: str = ""

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.strip().lower() == "production"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def admin_telegram_ids_set(self) -> set[str]:
        return {x.strip() for x in self.ADMIN_TELEGRAM_IDS.split(",") if x.strip()}

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @model_validator(mode="after")
    def validate_production_keys(self):
        if self.is_production:
            missing = []
            if not self.LLM_API_KEY:
                missing.append("LLM_API_KEY")
            if not self.LLM_BASE_URL:
                missing.append("LLM_BASE_URL")
            if not self.ADMIN_API_KEY:
                missing.append("ADMIN_API_KEY")
            # JWT_SECRET: not yet used by any endpoint — skip until auth JWT is implemented
            if not self.DATABASE_URL:
                missing.append("DATABASE_URL")
            if missing:
                raise ValueError(f"Production requires: {', '.join(missing)}")
        return self


settings = Settings()
