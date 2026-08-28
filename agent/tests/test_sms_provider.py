"""SMS transport contract.

The first half characterises `auth._send_sms` exactly as it behaves today. It is
a safety net for extracting that code, so these assertions must keep passing
before and after the move — authentication OTP semantics do not change.
"""
from __future__ import annotations
from identity import api as identity_api  # mien dinh danh sang day 2026-08-28

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agent"))

import auth  # noqa: E402


class _Response:
    def __init__(self, payload) -> None:
        self._payload = payload

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class _FakeAsyncClient:
    """Stands in for httpx.AsyncClient so no test ever reaches the network."""

    calls: list[tuple[str, dict]] = []
    script: list = []

    def __init__(self, *args, **kwargs) -> None:
        type(self).init_kwargs = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, url, json=None):
        type(self).calls.append((url, json))
        outcome = type(self).script.pop(0) if type(self).script else {"CodeResult": "100"}
        if isinstance(outcome, Exception):
            raise outcome
        return _Response(outcome)


async def _no_sleep(_seconds):
    return None


@pytest.fixture
def fake_sms(monkeypatch):
    _FakeAsyncClient.calls = []
    _FakeAsyncClient.script = []
    _FakeAsyncClient.init_kwargs = {}
    import sms_provider

    # The transport is the pinned client now, so the fake sits at the injected
    # poster seam instead of at httpx. The assertions below are unchanged.
    def _fake_post(url, payload):
        _FakeAsyncClient.calls.append((url, payload))
        outcome = _FakeAsyncClient.script.pop(0) if _FakeAsyncClient.script else {"CodeResult": "100"}
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(sms_provider, "_pinned_post", _fake_post)
    monkeypatch.setattr(sms_provider.time, "sleep", lambda _s: None)
    monkeypatch.setattr(identity_api, "ESMS_API_KEY", "test-key")
    monkeypatch.setattr(identity_api, "ESMS_SECRET", "test-secret")
    monkeypatch.setattr(identity_api, "ESMS_BRANDNAME", "VL360")
    # A local shim, not a patch of the real asyncio module: patching the module
    # attribute in place makes the replacement call itself.
    monkeypatch.setattr(identity_api, "asyncio", SimpleNamespace(sleep=_no_sleep))
    return _FakeAsyncClient


# ── Characterisation: today's behaviour, which the extraction must preserve ──

def test_without_a_provider_key_the_send_is_a_dev_no_op(monkeypatch):
    monkeypatch.setattr(identity_api, "ESMS_API_KEY", "")

    assert asyncio.run(auth._send_sms("0901234567", "ma 123456")) is True


def test_a_success_code_reports_delivered_and_posts_once(fake_sms):
    fake_sms.script = [{"CodeResult": "100"}]

    assert asyncio.run(auth._send_sms("0901234567", "ma 123456")) is True
    assert len(fake_sms.calls) == 1


def test_the_national_number_is_sent_in_international_form(fake_sms):
    asyncio.run(auth._send_sms("0901234567", "ma 123456"))

    _url, payload = fake_sms.calls[0]
    assert payload["Phone"] == "84901234567"
    assert payload["Content"] == "ma 123456"
    assert payload["SmsType"] == "2"


def test_the_request_goes_to_the_exact_provider_endpoint(fake_sms):
    asyncio.run(auth._send_sms("0901234567", "ma 123456"))

    url, _payload = fake_sms.calls[0]
    assert url == (
        "https://rest.esms.vn/MainService.svc/json/SendMultipleMessage_V4_post_json/"
    )


def test_a_rejected_code_retries_up_to_the_bound_then_reports_failure(fake_sms):
    fake_sms.script = [{"CodeResult": "99"}, {"CodeResult": "99"}, {"CodeResult": "99"}]

    assert asyncio.run(auth._send_sms("0901234567", "ma 123456")) is False
    assert len(fake_sms.calls) == 3


def test_a_transport_exception_retries_and_can_still_succeed(fake_sms):
    fake_sms.script = [RuntimeError("boom"), {"CodeResult": "100"}]

    assert asyncio.run(auth._send_sms("0901234567", "ma 123456")) is True
    assert len(fake_sms.calls) == 2


def test_the_provider_credentials_never_reach_the_log(fake_sms, caplog):
    fake_sms.script = [{"CodeResult": "99"}, {"CodeResult": "99"}, {"CodeResult": "99"}]

    with caplog.at_level("WARNING"):
        asyncio.run(auth._send_sms("0901234567", "ma 123456"))

    rendered = caplog.text
    assert "test-key" not in rendered
    assert "test-secret" not in rendered
    assert "ma 123456" not in rendered
    assert "0901234567" not in rendered


# ── The extracted provider ──

def test_the_provider_exposes_one_send_operation():
    from sms_provider import EsmsProvider, SmsDeliveryResult

    provider = EsmsProvider(api_key="k", secret="s", brandname="b")

    assert hasattr(provider, "send")
    assert SmsDeliveryResult(True, None, False).delivered is True


def test_a_provider_without_credentials_reports_a_dev_delivery():
    from sms_provider import EsmsProvider

    provider = EsmsProvider(api_key="", secret="", brandname="")

    result = provider.send("0901234567", "ma 123456", delivery_key="k1")

    assert result.delivered is True
    assert result.error_code == "dev_no_provider"


def test_the_provider_classifies_a_rejection_as_not_retryable():
    from sms_provider import classify_provider_result

    assert classify_provider_result({"CodeResult": "100"}).delivered is True
    rejected = classify_provider_result({"CodeResult": "99"})
    assert rejected.delivered is False
    assert rejected.retryable is False
    assert rejected.error_code == "provider_code_99"


def test_the_provider_classifies_a_missing_answer_as_retryable():
    from sms_provider import classify_provider_result

    unknown = classify_provider_result(None)

    assert unknown.delivered is False
    assert unknown.retryable is True
    assert unknown.error_code == "provider_unavailable"


def test_a_missing_key_in_production_is_a_refusal_not_a_delivery(monkeypatch):
    from config import settings
    from sms_provider import EsmsProvider

    monkeypatch.setattr(type(settings), "is_production", property(lambda self: True))
    provider = EsmsProvider(api_key="", secret="", brandname="")

    outcome = provider.send("0901234567", "tin nhắn")

    # "Sent" while nothing left the building would settle the outbox as done and
    # leave the reporter waiting on a message that never existed.
    assert outcome.delivered is False
    assert outcome.error_code == "provider_unconfigured"
    assert outcome.retryable is False


def test_dev_without_a_key_still_suppresses_quietly(monkeypatch):
    from config import settings
    from sms_provider import EsmsProvider

    monkeypatch.setattr(type(settings), "is_production", property(lambda self: False))
    provider = EsmsProvider(api_key="", secret="", brandname="")

    outcome = provider.send("0901234567", "tin nhắn")

    assert outcome.delivered is True
    assert outcome.error_code == "dev_no_provider"


def test_a_failed_attempt_names_the_delivery_it_belongs_to(caplog):
    import logging

    from sms_provider import EsmsProvider

    provider = EsmsProvider(api_key="k", secret="s", brandname="b",
                            poster=lambda url, payload: {"CodeResult": "99"})

    with caplog.at_level(logging.WARNING):
        provider.send("0901234567", "tin nhắn", delivery_key="abc123")

    # The eSMS payload has no idempotency field, so the key never leaves the
    # process; logging it is the only way a complaint about a message gets
    # traced back to the row that sent it.
    assert any("abc123" in record.getMessage() for record in caplog.records)
    # And the phone number is still masked in that same line.
    assert not any("0901234567" in record.getMessage() for record in caplog.records)
