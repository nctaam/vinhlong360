"""One SMS transport, shared by authentication OTP and case notifications.

The payload shape, the endpoint, the retry policy and the success/failure
classification live here exactly once. Two entry points call them: `send_async`
for request handlers already running on the event loop, and `send` for the
outbox dispatcher, which runs in a worker. Forcing either onto the other's
concurrency model would be a behaviour change, and authentication OTP semantics
must not change.

Nothing here logs a full phone number, a message body, or a provider credential.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

ESMS_ENDPOINT = "https://rest.esms.vn/MainService.svc/json/SendMultipleMessage_V4_post_json/"
ESMS_SUCCESS_CODE = "100"
MAX_RETRIES = 3
REQUEST_TIMEOUT_SECONDS = 10


@dataclass(frozen=True)
class SmsDeliveryResult:
    delivered: bool
    error_code: str | None = None
    retryable: bool = False


def mask_phone(phone: str) -> str:
    """Enough to correlate a report, not enough to identify a person."""
    if type(phone) is not str or len(phone) < 7:
        return "***"
    return f"{phone[:3]}***{phone[-3:]}"


def international_phone(phone: str) -> str:
    return "84" + phone[1:] if phone.startswith("0") else phone


def build_payload(phone: str, message: str, *, api_key: str, secret: str, brandname: str) -> dict:
    return {
        "ApiKey": api_key,
        "Content": message,
        "Phone": international_phone(phone),
        "SecretKey": secret,
        "SmsType": "2",
        "Brandname": brandname,
    }


def classify_provider_result(payload: object) -> SmsDeliveryResult:
    """No answer is worth another attempt; a stated rejection is not."""
    if not isinstance(payload, dict):
        return SmsDeliveryResult(False, "provider_unavailable", True)
    code = payload.get("CodeResult")
    if code == ESMS_SUCCESS_CODE:
        return SmsDeliveryResult(True, None, False)
    return SmsDeliveryResult(False, f"provider_code_{code}", False)


def backoff_seconds(attempt: int) -> float:
    return 0.5 * (2 ** attempt)


class EsmsProvider:
    def __init__(self, *, api_key: str, secret: str, brandname: str) -> None:
        self._api_key = api_key or ""
        self._secret = secret or ""
        self._brandname = brandname or ""

    @property
    def configured(self) -> bool:
        return bool(self._api_key)

    def _payload(self, phone: str, message: str) -> dict:
        return build_payload(
            phone, message,
            api_key=self._api_key, secret=self._secret, brandname=self._brandname,
        )

    def _dev_result(self, phone: str) -> SmsDeliveryResult:
        logger.debug("DEV MODE — SMS to %s suppressed (no provider key)", mask_phone(phone))
        return SmsDeliveryResult(True, "dev_no_provider", False)

    def _record(self, attempt: int, phone: str, outcome: SmsDeliveryResult) -> None:
        logger.warning(
            "SMS attempt %d failed for %s: %s",
            attempt + 1, mask_phone(phone), outcome.error_code,
        )

    def send(self, phone: str, message: str, *, delivery_key: str) -> SmsDeliveryResult:
        """Blocking send for the outbox dispatcher."""
        if not self.configured:
            return self._dev_result(phone)
        outcome = SmsDeliveryResult(False, "provider_unavailable", True)
        for attempt in range(MAX_RETRIES):
            try:
                with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as client:
                    response = client.post(ESMS_ENDPOINT, json=self._payload(phone, message))
                    outcome = classify_provider_result(response.json())
            except Exception:  # noqa: BLE001 - provider outage, never a credential leak
                logger.warning(
                    "SMS attempt %d exception for %s", attempt + 1, mask_phone(phone)
                )
                outcome = SmsDeliveryResult(False, "provider_unavailable", True)
            if outcome.delivered:
                return outcome
            self._record(attempt, phone, outcome)
            if attempt < MAX_RETRIES - 1:
                time.sleep(backoff_seconds(attempt))
        return outcome

    async def send_async(self, phone: str, message: str, *, delivery_key: str = "") -> SmsDeliveryResult:
        """Non-blocking send for handlers already on the event loop."""
        if not self.configured:
            return self._dev_result(phone)
        outcome = SmsDeliveryResult(False, "provider_unavailable", True)
        for attempt in range(MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
                    response = await client.post(
                        ESMS_ENDPOINT, json=self._payload(phone, message)
                    )
                    outcome = classify_provider_result(response.json())
            except Exception:  # noqa: BLE001
                logger.warning(
                    "SMS attempt %d exception for %s", attempt + 1, mask_phone(phone)
                )
                outcome = SmsDeliveryResult(False, "provider_unavailable", True)
            if outcome.delivered:
                return outcome
            self._record(attempt, phone, outcome)
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(backoff_seconds(attempt))
        return outcome
