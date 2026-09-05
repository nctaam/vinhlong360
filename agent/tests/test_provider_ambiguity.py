"""Provider ambiguity contract tests."""

from sms_provider import EsmsProvider


def test_timeout_after_provider_accept_is_ambiguous_and_not_retried():
    calls = []

    def send_then_timeout(_url, _payload):
        calls.append(True)
        raise TimeoutError("provider accepted request before timeout")

    provider = EsmsProvider(api_key="key", secret="secret", brandname="VL360", poster=send_then_timeout)
    result = provider.send("0901234567", "message", delivery_key="delivery-1")

    assert result.delivered is False
    assert result.state == "ambiguous"
    assert result.error_code == "provider_ambiguous"
    assert result.retryable is False
    assert len(calls) == 1

