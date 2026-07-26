from __future__ import annotations

import socket

import pytest

import pinned_http as ph


def _answer(ip: str, port: int = 443) -> tuple:
    family = socket.AF_INET6 if ":" in ip else socket.AF_INET
    sockaddr = (ip, port, 0, 0) if family == socket.AF_INET6 else (ip, port)
    return (family, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", sockaddr)


def _install_dns(monkeypatch: pytest.MonkeyPatch, *ips: str) -> None:
    answers = [_answer(ip) for ip in ips]
    monkeypatch.setattr(ph.socket, "getaddrinfo", lambda *_args, **_kwargs: answers)


_BLOCKED_IPS = (
    "0.0.0.0",
    "10.0.0.1",
    "100.64.0.1",
    "127.0.0.1",
    "169.254.169.254",
    "192.0.2.1",
    "224.0.0.1",
    "240.0.0.1",
    "::",
    "::1",
    "::127.0.0.1",
    "::ffff:127.0.0.1",
    "64:ff9b::7f00:1",
    "64:ff9b:1::7f00:1",
    "2002:7f00:1::",
    "2001:0000:4136:e378:8000:63bf:3fff:fdd2",
    "2001:db8:1:2:0:5efe:7f00:1",
)


@pytest.mark.parametrize(
    "url",
    [
        "",
        "notaurl",
        "ftp://example.com/x",
        "file:///etc/passwd",
        "https://user@example.com/x",
        "https://user:pass@example.com/x",
        "https://[fe80::1%25eth0]/x",
        "https://example.com:99999/x",
    ],
)
def test_validate_public_url_rejects_invalid_authority(url: str) -> None:
    with pytest.raises(ph.InvalidDestinationError):
        ph.validate_public_url(url, resolver=lambda _host, _port: ())


def test_resolver_allows_and_deduplicates_public_answers(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_dns(monkeypatch, "93.184.216.34", "2606:2800:220:1:248:1893:25c8:1946", "93.184.216.34")
    result = ph.resolve_public_addresses("example.com", 443)
    assert [str(item.ip) for item in result] == [
        "93.184.216.34",
        "2606:2800:220:1:248:1893:25c8:1946",
    ]


@pytest.mark.parametrize(
    "ip",
    _BLOCKED_IPS,
)
def test_resolver_rejects_blocked_and_transition_answers(
    monkeypatch: pytest.MonkeyPatch,
    ip: str,
) -> None:
    _install_dns(monkeypatch, ip)
    with pytest.raises(ph.BlockedAddressError):
        ph.resolve_public_addresses("example.com", 443)


def test_resolver_rejects_mixed_answer_set(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_dns(monkeypatch, "93.184.216.34", "127.0.0.1")
    with pytest.raises(ph.BlockedAddressError):
        ph.resolve_public_addresses("example.com", 443)


def test_resolver_translates_malformed_answers(monkeypatch: pytest.MonkeyPatch) -> None:
    malformed = [
        (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("not-an-ip", 443)),
    ]
    monkeypatch.setattr(ph.socket, "getaddrinfo", lambda *_args, **_kwargs: malformed)
    with pytest.raises(ph.ResolutionError):
        ph.resolve_public_addresses("example.com", 443)


def test_resolver_translates_dns_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*_args, **_kwargs):
        raise socket.gaierror("dns failed")

    monkeypatch.setattr(ph.socket, "getaddrinfo", fail)
    with pytest.raises(ph.ResolutionError):
        ph.resolve_public_addresses("example.com", 443)


@pytest.mark.parametrize(
    "ip",
    ["93.184.216.34", "2606:2800:220:1:248:1893:25c8:1946"],
)
def test_public_literal_ip_never_calls_dns(
    monkeypatch: pytest.MonkeyPatch,
    ip: str,
) -> None:
    monkeypatch.setattr(ph.socket, "getaddrinfo", lambda *_args, **_kwargs: pytest.fail("DNS called"))
    addresses = ph.resolve_public_addresses(ip, 443)
    assert addresses[0].ip == ph.ipaddress.ip_address(ip)


@pytest.mark.parametrize("ip", _BLOCKED_IPS)
def test_blocked_literal_ip_never_calls_dns(
    monkeypatch: pytest.MonkeyPatch,
    ip: str,
) -> None:
    monkeypatch.setattr(ph.socket, "getaddrinfo", lambda *_args, **_kwargs: pytest.fail("DNS called"))
    with pytest.raises(ph.BlockedAddressError):
        ph.resolve_public_addresses(ip, 443)


def test_validate_public_url_uses_injected_resolver() -> None:
    calls: list[tuple[str, int]] = []

    def resolver(host: str, port: int) -> tuple[ph.ResolvedAddress, ...]:
        calls.append((host, port))
        return (
            ph.ResolvedAddress(
                ip=ph.ipaddress.ip_address("93.184.216.34"),
                port=port,
                family=socket.AF_INET,
                socktype=socket.SOCK_STREAM,
                protocol=socket.IPPROTO_TCP,
                sockaddr=("93.184.216.34", port),
            ),
        )

    ph.validate_public_url("https://Example.COM/path#fragment", resolver=resolver)
    assert calls == [("example.com", 443)]


def test_validate_public_url_uses_ascii_idna_host() -> None:
    calls: list[tuple[str, int]] = []

    def resolver(host: str, port: int) -> tuple[ph.ResolvedAddress, ...]:
        calls.append((host, port))
        return (
            ph.ResolvedAddress(
                ip=ph.ipaddress.ip_address("93.184.216.34"),
                port=port,
                family=socket.AF_INET,
                socktype=socket.SOCK_STREAM,
                protocol=socket.IPPROTO_TCP,
                sockaddr=("93.184.216.34", port),
            ),
        )

    ph.validate_public_url("https://BÜCHER.example/path", resolver=resolver)
    assert calls == [("xn--bcher-kva.example", 443)]
