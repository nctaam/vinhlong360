"""Committed privacy-policy authority shared by runtime and legal copy."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class PrivacyPolicyError(RuntimeError):
    pass


@dataclass(frozen=True)
class PrivacyPolicy:
    account_erasure_deadline_days: int
    recovery_enabled_during_grace_period: bool
    feedback_mode: str
    feedback_receipt_ttl_hours: int
    retain_deidentified_aggregates: bool


_POLICY_KEYS = {
    "accountErasureDeadlineDays",
    "recoveryEnabledDuringGracePeriod",
    "feedbackMode",
    "feedbackReceiptTtlHours",
    "retainDeidentifiedAggregates",
}


def _require_int(value: Any, *, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise PrivacyPolicyError(f"{name} must be an integer")
    if not minimum <= value <= maximum:
        raise PrivacyPolicyError(f"{name} must be in {minimum}..{maximum}")
    return value


def _require_bool(value: Any, *, name: str) -> bool:
    if not isinstance(value, bool):
        raise PrivacyPolicyError(f"{name} must be a boolean")
    return value


def load_privacy_policy(path: Path | None = None) -> PrivacyPolicy:
    policy_path = path or (
        Path(__file__).resolve().parents[1] / "config" / "privacy-policy.json"
    )
    try:
        payload = json.loads(policy_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PrivacyPolicyError("privacy policy is unavailable or invalid") from exc

    if not isinstance(payload, dict) or set(payload) != _POLICY_KEYS:
        raise PrivacyPolicyError("privacy policy keys do not match the contract")

    feedback_mode = payload["feedbackMode"]
    if feedback_mode != "telemetry_only":
        raise PrivacyPolicyError("feedbackMode must be telemetry_only")

    return PrivacyPolicy(
        account_erasure_deadline_days=_require_int(
            payload["accountErasureDeadlineDays"],
            name="accountErasureDeadlineDays",
            minimum=1,
            maximum=365,
        ),
        recovery_enabled_during_grace_period=_require_bool(
            payload["recoveryEnabledDuringGracePeriod"],
            name="recoveryEnabledDuringGracePeriod",
        ),
        feedback_mode=feedback_mode,
        feedback_receipt_ttl_hours=_require_int(
            payload["feedbackReceiptTtlHours"],
            name="feedbackReceiptTtlHours",
            minimum=1,
            maximum=168,
        ),
        retain_deidentified_aggregates=_require_bool(
            payload["retainDeidentifiedAggregates"],
            name="retainDeidentifiedAggregates",
        ),
    )


def privacy_policy_readiness(settings: Any) -> bool:
    try:
        policy = load_privacy_policy()
        return (
            settings.ACCOUNT_ERASURE_DEADLINE_DAYS
            == policy.account_erasure_deadline_days
            and settings.RECOVERY_ENABLED_DURING_GRACE_PERIOD
            is policy.recovery_enabled_during_grace_period
            and settings.FEEDBACK_MODE == policy.feedback_mode
            and settings.FEEDBACK_RECEIPT_TTL_HOURS
            == policy.feedback_receipt_ttl_hours
            and settings.RETAIN_DEIDENTIFIED_AGGREGATES
            is policy.retain_deidentified_aggregates
        )
    except (AttributeError, PrivacyPolicyError):
        return False
