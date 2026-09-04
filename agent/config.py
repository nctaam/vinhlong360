"""Centralized configuration with validation.

Usage:
    from config import settings
    settings.LLM_API_KEY      # str (required in production)
    settings.LLM_MODEL        # str with default
    settings.is_production     # bool
"""

from pathlib import Path
import re
from urllib.parse import unquote, urlparse

from dotenv import load_dotenv
from pydantic import model_validator
from pydantic_settings import BaseSettings
from secret_policy import is_strong_production_secret

POSTGRES_URL_PREFIXES = ("postgres://", "postgresql://")


def is_postgresql_url(value: str) -> bool:
    return value.strip().lower().startswith(POSTGRES_URL_PREFIXES)


def _origin_text_is_valid(value: object) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and not any(ch.isspace() for ch in value)
        and "*" not in value
        and not any(ch in value for ch in "?#")
    )


def _origin_scheme_is_allowed(parsed, *, require_https: bool) -> bool:
    allowed_schemes = {"https"} if require_https else {"http", "https"}
    return parsed.scheme.lower() in allowed_schemes


def _origin_has_authority_only(parsed) -> bool:
    return (
        not parsed.netloc
        or parsed.username
        or parsed.password
        or bool(parsed.path)
        or parsed.netloc.endswith(":")
    )


def _origin_has_valid_port(parsed) -> bool:
    try:
        parsed.port
    except ValueError:
        return False
    return True


def _origin_hostname_is_valid(parsed) -> bool:
    hostname = parsed.hostname or ""
    pattern = r"(?:[A-Za-z0-9-]+\.)*[A-Za-z0-9-]+|\[[0-9A-Fa-f:.]+\]"
    return bool(re.fullmatch(pattern, hostname))


def is_exact_origin(value: object, *, require_https: bool = True) -> bool:
    """Validate a CORS origin (scheme + authority only, never a URL)."""
    if not _origin_text_is_valid(value):
        return False
    parsed = urlparse(value)
    if not _origin_scheme_is_allowed(parsed, require_https=require_https):
        return False
    if _origin_has_authority_only(parsed):
        return False
    if not _origin_has_valid_port(parsed):
        return False
    return _origin_hostname_is_valid(parsed)


def _is_individual_actor_ref(value: str) -> bool:
    """Validate the reference shape; a later resolver verifies actor existence."""
    if any(token in value.lower() for token in ("@", "mailbox", "team", "group", "alias")):
        return False
    return value.startswith("person:") and len(value) > len("person:") and value[7:].replace("-", "").replace("_", "").isalnum()

from privacy_policy import load_privacy_policy

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

_PRIVACY_POLICY = load_privacy_policy()


class Settings(BaseSettings):
    CASE_KERNEL_ENABLED: bool = False
    CORRECTION_INTAKE_ENABLED: bool = False
    CORRECTION_ADMIN_ENABLED: bool = False
    CORRECTION_ASSISTED_ENABLED: bool = False
    CORRECTION_PUBLICATION_ENABLED: bool = False
    CASE_KERNEL_ENCRYPTION_KEY: str = ""
    CASE_SERVICE_OWNER_REF: str = ""
    # ── LLM ──
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = ""
    LLM_MODEL: str = "cx/gpt-5.4"
    LLM_MODEL_MINI: str = "cx/gpt-5.4-mini"
    LLM_TIMEOUT: int = 30

    # ── Database ──
    DATABASE_URL: str = ""
    ENTITY_DETAILS_TABLES: bool = False
    REDIS_URL: str = ""

    # ── Security ──
    ADMIN_API_KEY: str = ""
    CORS_ORIGINS: str = "http://localhost:8360,http://localhost:3000,https://vinhlong360.vn"
    JWT_SECRET: str = ""
    CSRF_SECRET: str = ""
    CHAT_OWNER_SECRET: str = ""
    EXPORT_CURSOR_SECRET: str = ""

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
    # ĐẢO MẶC ĐỊNH 2026-08-30 theo chỉ đạo chủ dự án ("thực hiện theo Luật
    # 91/2025"). Trước đó mặc định là chỉ-đếm, và mặc định đó ĐANG NÓI DỐI:
    # `identity/api.py` trả lời người dùng «Tài khoản sẽ bị xoá vĩnh viễn sau N
    # ngày» bất kể cấu hình, còn tác vụ nền thì đếm hồ sơ quá hạn rồi thoát,
    # 288 lần/ngày. Luật 91/2025 cho người dùng QUYỀN được xoá; một mặc định
    # "an toàn" bằng cách không xoá là an toàn cho hệ thống, không phải cho họ.
    #
    # Foot-gun được chặn ở tầng dưới, không phải ở đây: `erase_due_accounts`
    # đòi PostgreSQL (`db._use_pg`) và trả DB_ERROR nếu không có — nên mọi máy
    # dev chạy SQLite KHÔNG thể xoá gì, dù mặc định nay là bật.
    #
    # `ERASURE_ACTIVATION_ENABLED` giữ nguyên vai CẦU DAO: đặt False là dừng xoá
    # ngay lập tức, không cần deploy lại.
    ERASURE_AUDIT_ONLY: bool = False
    ERASURE_ACTIVATION_ENABLED: bool = True
    LLM_JUDGE_ENABLED: bool = False
    DESTRUCTIVE_OPS_LOCKED: str = "1"

    # ── Identity/location/personalization rollout ──
    # Kill-switches stay off until each bounded surface has an owner-approved
    # rollout. Legacy JSONL is read only through the configured ISO deadline.
    PREFERENCE_PROFILE_V1: bool = False
    PERSONALIZATION_EVENTS_PG: bool = False
    LOCATION_RESOLVER_V1: bool = False
    RECOMMENDATION_EXPLANATIONS_V1: bool = False
    TRUST_DRAWER_V1: bool = False
    LEGACY_EVENT_READ_UNTIL: str = ""

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
    ACCOUNT_ERASURE_DEADLINE_DAYS: int = _PRIVACY_POLICY.account_erasure_deadline_days
    RECOVERY_ENABLED_DURING_GRACE_PERIOD: bool = _PRIVACY_POLICY.recovery_enabled_during_grace_period
    FEEDBACK_MODE: str = _PRIVACY_POLICY.feedback_mode
    FEEDBACK_RECEIPT_TTL_HOURS: int = _PRIVACY_POLICY.feedback_receipt_ttl_hours
    RETAIN_DEIDENTIFIED_AGGREGATES: bool = _PRIVACY_POLICY.retain_deidentified_aggregates
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

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        "hide_input_in_errors": True,
    }

    @property
    def ACCOUNT_DELETE_GRACE_DAYS(self) -> int:
        return self.ACCOUNT_ERASURE_DEADLINE_DAYS

    def _validate_case_flags(self) -> None:
        case_flags = (
            self.CASE_KERNEL_ENABLED, self.CORRECTION_INTAKE_ENABLED,
            self.CORRECTION_ADMIN_ENABLED, self.CORRECTION_ASSISTED_ENABLED,
            self.CORRECTION_PUBLICATION_ENABLED,
        )
        if any(case_flags) and not is_postgresql_url(self.DATABASE_URL):
            raise ValueError("case_postgresql_required")
        if any(case_flags):
            owner = self.CASE_SERVICE_OWNER_REF
            try:
                from cases.security import validate_case_encryption_key
                validate_case_encryption_key(self.CASE_KERNEL_ENCRYPTION_KEY)
            except Exception:
                raise ValueError("case_encryption_key_required")
            if not _is_individual_actor_ref(owner):
                raise ValueError("case_owner_individual_required")

    def _missing_production_settings(self) -> list[str]:
        missing = []
        if not self.LLM_API_KEY:
            missing.append("LLM_API_KEY")
        if not self.LLM_BASE_URL:
            missing.append("LLM_BASE_URL")
        if not self.ADMIN_API_KEY:
            missing.append("ADMIN_API_KEY")
        if not self.CSRF_SECRET:
            missing.append("CSRF_SECRET")
        # JWT_SECRET: not yet used by any endpoint — skip until auth JWT is implemented
        if not self.DATABASE_URL:
            missing.append("DATABASE_URL")
        elif not is_postgresql_url(self.DATABASE_URL):
            missing.append("DATABASE_URL (PostgreSQL required)")
        if not self.ENTITY_DETAILS_TABLES:
            missing.append("ENTITY_DETAILS_TABLES=true")
        return missing

    def _mismatched_privacy_policy(self) -> list[str]:
        policy_values = {
            "ACCOUNT_ERASURE_DEADLINE_DAYS": (
                self.ACCOUNT_ERASURE_DEADLINE_DAYS,
                _PRIVACY_POLICY.account_erasure_deadline_days,
            ),
            "RECOVERY_ENABLED_DURING_GRACE_PERIOD": (
                self.RECOVERY_ENABLED_DURING_GRACE_PERIOD,
                _PRIVACY_POLICY.recovery_enabled_during_grace_period,
            ),
            "FEEDBACK_MODE": (self.FEEDBACK_MODE, _PRIVACY_POLICY.feedback_mode),
            "FEEDBACK_RECEIPT_TTL_HOURS": (
                self.FEEDBACK_RECEIPT_TTL_HOURS,
                _PRIVACY_POLICY.feedback_receipt_ttl_hours,
            ),
            "RETAIN_DEIDENTIFIED_AGGREGATES": (
                self.RETAIN_DEIDENTIFIED_AGGREGATES,
                _PRIVACY_POLICY.retain_deidentified_aggregates,
            ),
        }
        return [
            name for name, (actual, expected) in policy_values.items()
            if actual != expected
        ]

    @model_validator(mode="after")
    def validate_production_keys(self):
        self._validate_case_flags()
        if self.is_production:
            missing = self._missing_production_settings()
            if missing:
                raise ValueError(f"Production requires: {', '.join(missing)}")
            mismatched = self._mismatched_privacy_policy()
            if mismatched:
                raise ValueError(
                    "Production privacy policy mismatch: " + ", ".join(mismatched)
                )
        return self


def _unsafe_production_secret(value: object) -> bool:
    return not is_strong_production_secret(value)


def _production_secret_failures(settings: Settings) -> list[str]:
    return [
        f"{field} must be a strong non-default secret"
        for field in ("LLM_API_KEY", "ADMIN_API_KEY", "JWT_SECRET", "CSRF_SECRET")
        if _unsafe_production_secret(getattr(settings, field, ""))
    ]


def _production_database_failures(settings: Settings) -> list[str]:
    database_url = str(getattr(settings, "DATABASE_URL", "") or "").strip()
    if not is_postgresql_url(database_url):
        return ["DATABASE_URL must use PostgreSQL"]
    parsed = urlparse(database_url)
    if not parsed.hostname or not parsed.username or not parsed.password:
        return ["DATABASE_URL must include explicit PostgreSQL credentials"]
    if _unsafe_production_secret(unquote(parsed.password)):
        return ["DATABASE_URL password must be a strong non-default secret"]
    return []


def _production_cors_failures(settings: Settings) -> list[str]:
    origins = getattr(settings, "cors_origins_list", [])
    raw_origins = str(getattr(settings, "CORS_ORIGINS", "") or "").strip()
    if not raw_origins or not origins:
        return ["CORS_ORIGINS must be explicitly configured"]
    if any("localhost" in origin.lower() or "127.0.0.1" in origin for origin in origins):
        return ["CORS_ORIGINS must not include local origins in production"]
    if any(not is_exact_origin(origin, require_https=True) for origin in origins):
        return ["CORS_ORIGINS must use HTTPS in production"]
    return []


def assert_production_config(settings: Settings) -> None:
    """Fail closed before startup when a production contract is unsafe."""
    if not isinstance(settings, Settings):
        raise ValueError("production_settings_required")
    if not settings.is_production:
        raise ValueError("ENVIRONMENT=production is required")

    failures: list[str] = _production_secret_failures(settings)
    failures.extend(_production_database_failures(settings))
    if getattr(settings, "ENTITY_DETAILS_TABLES", False) is not True:
        failures.append("ENTITY_DETAILS_TABLES=true is required")
    failures.extend(_production_cors_failures(settings))

    if failures:
        raise ValueError("Unsafe production configuration: " + "; ".join(failures))


settings = Settings()


def erasure_is_audit_only() -> bool:
    """Vòng xoá tài khoản đang CHỈ ĐẾM, hay xoá thật?

    MỘT nguồn sự thật cho câu hỏi này. Trước 2026-08-30 nó chỉ nằm trong
    `scheduler._effective_erasure_audit_only`, nên chỗ TRẢ LỜI NGƯỜI DÙNG
    (`identity/api.py`) không hỏi được và cứ hứa "xoá vĩnh viễn" bất kể cấu hình.
    Đó chính là lỗ hổng P0: hứa một đằng làm một nẻo.

    Vẫn là "hoặc": thiếu BẤT KỲ cờ nào cũng là chỉ-đếm. Cờ activation giữ vai
    cầu dao — tắt nó là dừng xoá ngay, không cần deploy lại.
    """
    return bool(settings.ERASURE_AUDIT_ONLY) or not bool(
        settings.ERASURE_ACTIVATION_ENABLED
    )
