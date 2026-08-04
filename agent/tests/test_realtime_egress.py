from __future__ import annotations

import ipaddress
import json
import socket

import httpx
import pytest

import pinned_http as ph
import realtime


PUBLIC_IP = "93.184.216.34"
WEATHER_HOST = "api.openweathermap.org"


def _public_address(port: int) -> ph.ResolvedAddress:
    return ph.ResolvedAddress(
        ip=ipaddress.ip_address(PUBLIC_IP),
        port=port,
        family=socket.AF_INET,
        socktype=socket.SOCK_STREAM,
        protocol=socket.IPPROTO_TCP,
        sockaddr=(PUBLIC_IP, port),
    )


def _weather_body() -> bytes:
    return json.dumps({
        "main": {"temp": 30.56, "feels_like": 34.44, "humidity": 78},
        "weather": [{"id": 500, "description": "mưa nhẹ", "icon": "10d"}],
        "wind": {"speed": 2.34},
        "rain": {"1h": 1.2},
    }).encode()


@pytest.fixture(autouse=True)
def _isolate_weather(monkeypatch: pytest.MonkeyPatch):
    realtime._weather_cache.clear()
    monkeypatch.setattr(realtime, "WEATHER_API_KEY", "key +/?")

    def reject_legacy_get(*_args, **_kwargs):
        raise AssertionError("weather must not use unpinned httpx.get")

    monkeypatch.setattr(httpx, "get", reject_legacy_get)
    yield
    realtime._weather_cache.clear()


def test_get_weather_uses_bounded_exact_origin_policy_and_encoded_parameters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolved: list[tuple[str, int]] = []
    requested: list[httpx.Request] = []
    policies: list[ph.EgressPolicy] = []

    def resolver(
        host: str,
        port: int,
        _budget: ph.DeadlineBudget,
    ) -> tuple[ph.ResolvedAddress, ...]:
        resolved.append((host, port))
        return (_public_address(port),)

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(request)
        return httpx.Response(
            200,
            headers={"content-type": "application/json; charset=utf-8"},
            content=_weather_body(),
            request=request,
        )

    def transport_factory(
        _hop: ph.ResolvedHop,
        policy: ph.EgressPolicy,
        _budget: ph.DeadlineBudget,
    ) -> httpx.BaseTransport:
        policies.append(policy)
        return httpx.MockTransport(handler)

    monkeypatch.setattr(
        realtime,
        "_PINNED_HTTP",
        ph.PinnedHTTPClient(
            resolver=resolver,
            transport_factory=transport_factory,
        ),
        raising=False,
    )

    result = realtime.get_weather("vinh-long")

    assert result is not None
    assert result["area"] == "vinh-long"
    assert result["area_name"] == "Vĩnh Long"
    assert result["temp_c"] == 30.6
    assert result["feels_like_c"] == 34.4
    assert result["humidity"] == 78
    assert result["description"] == "mưa nhẹ"
    assert result["icon"] == "10d"
    assert result["wind_speed_ms"] == 2.3
    assert result["rain_mm"] == 1.2
    assert "fallback" not in result
    assert resolved == [(WEATHER_HOST, 443)]
    assert len(requested) == 1
    assert str(requested[0].url) == (
        "https://api.openweathermap.org/data/2.5/weather?"
        "lat=10.2537&lon=105.9722&appid=key+%2B%2F%3F&units=metric&lang=vi"
    )
    assert requested[0].headers["user-agent"] == "vinhlong360-weather/1.0"
    assert requested[0].headers["accept-encoding"] == "gzip, identity"
    assert policies == [
        ph.EgressPolicy(
            max_encoded_bytes=64 * 1024,
            max_decoded_bytes=256 * 1024,
            accepted_encodings=("gzip", "identity"),
            inactivity_timeout_seconds=10.0,
            total_timeout_seconds=10.0,
            max_redirects=2,
            allowed_origins=("https://api.openweathermap.org",),
        )
    ]


def test_get_weather_blocks_off_origin_redirect_without_logging_api_key(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    resolved: list[tuple[str, int]] = []
    requested: list[httpx.URL] = []

    def resolver(
        host: str,
        port: int,
        _budget: ph.DeadlineBudget,
    ) -> tuple[ph.ResolvedAddress, ...]:
        resolved.append((host, port))
        return (_public_address(port),)

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(request.url)
        return httpx.Response(
            302,
            headers={"location": "https://evil.example/collect"},
            request=request,
        )

    monkeypatch.setattr(
        realtime,
        "_PINNED_HTTP",
        ph.PinnedHTTPClient(
            resolver=resolver,
            transport_factory=lambda _hop, _policy, _budget: httpx.MockTransport(handler),
        ),
        raising=False,
    )

    with caplog.at_level("WARNING"):
        result = realtime.get_weather("vinh-long")

    assert result is not None and result["fallback"] is True
    assert resolved == [(WEATHER_HOST, 443)]
    assert [url.host for url in requested] == [WEATHER_HOST]
    security_records = [record for record in caplog.records if record.name == "security.egress"]
    realtime_records = [record for record in caplog.records if record.name == realtime.__name__]
    assert len(security_records) == 1
    assert realtime_records == []
    assert security_records[0].getMessage() == (
        "Pinned egress denied consumer=realtime_weather reason=redirect_policy "
        "target=https://api.openweathermap.org:443 hop=0"
    )
    assert all("key +/?" not in record.getMessage() for record in caplog.records)


def test_get_weather_reuses_cached_live_result_without_second_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requested: list[httpx.URL] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(request.url)
        return httpx.Response(200, content=_weather_body(), request=request)

    monkeypatch.setattr(
        realtime,
        "_PINNED_HTTP",
        ph.PinnedHTTPClient(
            resolver=lambda _host, port, _budget: (_public_address(port),),
            transport_factory=lambda _hop, _policy, _budget: httpx.MockTransport(handler),
        ),
        raising=False,
    )

    first = realtime.get_weather("tra-vinh")
    second = realtime.get_weather("tra-vinh")

    assert first is second
    assert len(requested) == 1


def test_get_weather_transport_failure_logs_safe_metadata_without_api_key(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret = "key +/?"
    monkeypatch.setattr(
        realtime,
        "_PINNED_HTTP",
        type(
            "FailingClient",
            (),
            {"get": lambda *_args, **_kwargs: (_ for _ in ()).throw(
                ph.PinnedTransportError(
                    f"GET https://api.openweathermap.org/weather?appid={secret} failed"
                )
            )},
        )(),
        raising=False,
    )

    with caplog.at_level("WARNING"):
        result = realtime.get_weather("vinh-long")

    assert result is not None and result["fallback"] is True
    records = [record for record in caplog.records if record.name == realtime.__name__]
    assert len(records) == 1
    assert records[0].getMessage() == (
        "Weather API failed for area vinh-long, using fallback (PinnedTransportError)"
    )
    assert all(secret not in record.getMessage() for record in caplog.records)


def test_get_weather_without_api_key_keeps_seasonal_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(realtime, "WEATHER_API_KEY", "")
    monkeypatch.setattr(
        realtime,
        "_PINNED_HTTP",
        type(
            "UnexpectedClient",
            (),
            {"get": lambda *_args, **_kwargs: pytest.fail("weather request was attempted")},
        )(),
        raising=False,
    )

    result = realtime.get_weather("ben-tre")

    assert result is not None and result["fallback"] is True
    assert result["area_name"] == "Bến Tre"
