from __future__ import annotations

import gzip
import socket
import ssl
from concurrent.futures import ThreadPoolExecutor

import httpcore
import httpx
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


class FakeSocket:
    def __init__(
        self,
        peer: tuple,
        *,
        connect_error: BaseException | None = None,
        recv_error: BaseException | None = None,
        send_error: BaseException | None = None,
    ) -> None:
        self.peer = peer
        self.connect_error = connect_error
        self.recv_error = recv_error
        self.send_error = send_error
        self.connected_to: tuple | None = None
        self.closed = False
        self.timeouts: list[float | None] = []
        self.options: list[tuple[object, ...]] = []

    def settimeout(self, value: float | None) -> None:
        self.timeouts.append(value)

    def setsockopt(self, *option: object) -> None:
        self.options.append(option)

    def connect(self, sockaddr: tuple) -> None:
        self.connected_to = sockaddr
        if self.connect_error is not None:
            raise self.connect_error

    def getpeername(self) -> tuple:
        return self.peer

    def getsockname(self) -> tuple[str, int]:
        return ("0.0.0.0", 50000)

    def recv(self, _max_bytes: int) -> bytes:
        if self.recv_error is not None:
            raise self.recv_error
        return b"data"

    def send(self, buffer: bytes) -> int:
        if self.send_error is not None:
            raise self.send_error
        return len(buffer)

    def close(self) -> None:
        self.closed = True


def _resolved_hop(url: str, *ips: str) -> ph.ResolvedHop:
    parsed = ph._parse_url(url)
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    addresses = tuple(
        ph.ResolvedAddress(
            ip=ph.ipaddress.ip_address(ip),
            port=port,
            family=socket.AF_INET6 if ":" in ip else socket.AF_INET,
            socktype=socket.SOCK_STREAM,
            protocol=socket.IPPROTO_TCP,
            sockaddr=(ip, port, 0, 0) if ":" in ip else (ip, port),
        )
        for ip in ips
    )
    return ph.ResolvedHop(
        url=parsed,
        host=ph._ascii_host(parsed),
        port=port,
        addresses=addresses,
    )


def test_backend_connects_exact_sockaddr_without_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    hop = _resolved_hop("https://example.com/x", "93.184.216.34")
    fake = FakeSocket(("93.184.216.34", 443))
    monkeypatch.setattr(ph.socket, "getaddrinfo", lambda *_args, **_kwargs: pytest.fail("DNS called"))
    backend = ph._PinnedNetworkBackend(hop, socket_factory=lambda *_args: fake)
    stream = backend.connect_tcp("example.com", 443, timeout=5.0)
    assert fake.connected_to == ("93.184.216.34", 443)
    assert stream.get_extra_info("server_addr") == ("93.184.216.34", 443)


def test_backend_closes_and_rejects_peer_mismatch() -> None:
    hop = _resolved_hop("https://example.com/x", "93.184.216.34")
    fake = FakeSocket(("127.0.0.1", 443))
    backend = ph._PinnedNetworkBackend(hop, socket_factory=lambda *_args: fake)
    with pytest.raises(ph.PeerMismatchError):
        backend.connect_tcp("example.com", 443, timeout=5.0)
    assert fake.closed is True


def test_backend_fallback_uses_one_connect_budget() -> None:
    hop = _resolved_hop("https://example.com/x", "93.184.216.34", "93.184.216.35")
    sockets = iter(
        [
            FakeSocket(("93.184.216.34", 443), connect_error=OSError("refused")),
            FakeSocket(("93.184.216.35", 443)),
        ]
    )
    times = iter([10.0, 11.0, 12.0])
    backend = ph._PinnedNetworkBackend(
        hop,
        socket_factory=lambda *_args: next(sockets),
        monotonic=lambda: next(times),
    )
    stream = backend.connect_tcp("example.com", 443, timeout=5.0)
    assert stream.get_extra_info("server_addr") == ("93.184.216.35", 443)


def test_stream_tls_uses_original_hostname() -> None:
    fake = FakeSocket(("93.184.216.34", 443))
    seen: list[str | None] = []

    class FakeSSLContext:
        def wrap_socket(self, sock: FakeSocket, *, server_hostname: str | None) -> FakeSocket:
            assert sock is fake
            seen.append(server_hostname)
            return fake

    stream = ph._PinnedNetworkStream(fake)
    stream.start_tls(FakeSSLContext(), server_hostname="example.com", timeout=5.0)
    assert seen == ["example.com"]
    assert fake.timeouts[-1] == 5.0


@pytest.mark.parametrize(
    ("host", "port"),
    [("other.example", 443), ("example.com", 80)],
)
def test_backend_rejects_httpcore_origin_mismatch(host: str, port: int) -> None:
    hop = _resolved_hop("https://example.com/x", "93.184.216.34")
    fake = FakeSocket(("93.184.216.34", 443))
    backend = ph._PinnedNetworkBackend(hop, socket_factory=lambda *_args: fake)
    with pytest.raises(ph.PeerMismatchError):
        backend.connect_tcp(host, port, timeout=5.0)
    assert fake.connected_to is None


def test_backend_translates_connect_timeout() -> None:
    hop = _resolved_hop("https://example.com/x", "93.184.216.34")
    fake = FakeSocket(("93.184.216.34", 443), connect_error=socket.timeout("timed out"))
    backend = ph._PinnedNetworkBackend(hop, socket_factory=lambda *_args: fake)
    with pytest.raises(httpcore.ConnectTimeout):
        backend.connect_tcp("example.com", 443, timeout=5.0)
    assert fake.closed is True


def test_backend_translates_socket_creation_failure() -> None:
    hop = _resolved_hop("https://example.com/x", "93.184.216.34")

    def fail_socket(*_args):
        raise OSError("socket creation failed")

    backend = ph._PinnedNetworkBackend(hop, socket_factory=fail_socket)
    with pytest.raises(httpcore.ConnectError):
        backend.connect_tcp("example.com", 443, timeout=5.0)


@pytest.mark.parametrize(
    ("operation", "error", "expected"),
    [
        ("read", socket.timeout("read timeout"), httpcore.ReadTimeout),
        ("read", OSError("read failed"), httpcore.ReadError),
        ("write", socket.timeout("write timeout"), httpcore.WriteTimeout),
        ("write", OSError("write failed"), httpcore.WriteError),
    ],
)
def test_stream_translates_io_errors(
    operation: str,
    error: BaseException,
    expected: type[Exception],
) -> None:
    fake = FakeSocket(
        ("93.184.216.34", 443),
        recv_error=error if operation == "read" else None,
        send_error=error if operation == "write" else None,
    )
    stream = ph._PinnedNetworkStream(fake)
    with pytest.raises(expected):
        if operation == "read":
            stream.read(16, timeout=2.0)
        else:
            stream.write(b"x", timeout=2.0)


def test_backend_applies_requested_options_and_tcp_nodelay() -> None:
    hop = _resolved_hop("https://example.com/x", "93.184.216.34")
    fake = FakeSocket(("93.184.216.34", 443))
    backend = ph._PinnedNetworkBackend(hop, socket_factory=lambda *_args: fake)
    keepalive = (socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    backend.connect_tcp("example.com", 443, timeout=5.0, socket_options=(keepalive,))
    assert keepalive in fake.options
    assert (socket.IPPROTO_TCP, socket.TCP_NODELAY, 1) in fake.options


def test_backend_rejects_unix_sockets() -> None:
    hop = _resolved_hop("https://example.com/x", "93.184.216.34")
    backend = ph._PinnedNetworkBackend(hop)
    with pytest.raises(httpcore.UnsupportedProtocol):
        backend.connect_unix_socket("/tmp/pinned.sock")


def test_stream_tls_failure_closes_without_insecure_retry() -> None:
    fake = FakeSocket(("93.184.216.34", 443))
    calls = 0

    class FailingSSLContext:
        def wrap_socket(self, _sock: FakeSocket, *, server_hostname: str | None) -> FakeSocket:
            nonlocal calls
            calls += 1
            assert server_hostname == "example.com"
            raise ssl.SSLError("certificate verify failed")

    with pytest.raises(httpcore.ConnectError):
        ph._PinnedNetworkStream(fake).start_tls(
            FailingSSLContext(),
            server_hostname="example.com",
            timeout=2.5,
        )
    assert calls == 1
    assert fake.closed is True


def test_transport_builds_verified_non_proxy_http1_pool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class FakePool:
        def close(self) -> None:
            pass

    def pool_factory(**kwargs: object) -> FakePool:
        captured.update(kwargs)
        return FakePool()

    monkeypatch.setattr(ph.httpcore, "ConnectionPool", pool_factory)
    hop = _resolved_hop("https://example.com/x", "93.184.216.34")
    ph._PinnedHTTPTransport(hop)

    context = captured["ssl_context"]
    assert isinstance(context, ssl.SSLContext)
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True
    assert captured["http1"] is True
    assert captured["http2"] is False
    assert captured["retries"] == 0
    assert captured["max_connections"] == 1
    assert captured["max_keepalive_connections"] == 0
    assert captured.get("proxy") is None


def test_transport_preserves_ascii_host_duplicate_headers_and_stream_close(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[httpcore.Request] = []
    closed: list[bool] = []

    class CoreStream:
        def __iter__(self):
            yield b"ok"

        def close(self) -> None:
            closed.append(True)

    class FakePool:
        def handle_request(self, request: httpcore.Request) -> httpcore.Response:
            captured.append(request)
            return httpcore.Response(
                200,
                headers=[(b"set-cookie", b"a=1"), (b"set-cookie", b"b=2")],
                content=CoreStream(),
            )

        def close(self) -> None:
            pass

    monkeypatch.setattr(ph.httpcore, "ConnectionPool", lambda **_kwargs: FakePool())
    hop = _resolved_hop("https://BÜCHER.example/x", "93.184.216.34")
    with httpx.Client(transport=ph._PinnedHTTPTransport(hop), trust_env=False) as client:
        response = client.get("https://BÜCHER.example/x")
        assert response.content == b"ok"
        assert response.headers.get_list("set-cookie") == ["a=1", "b=2"]

    assert captured[0].url.host == b"xn--bcher-kva.example"
    assert (b"Host", b"xn--bcher-kva.example") in captured[0].headers
    assert closed == [True]


def _public_resolver(host: str, port: int) -> tuple[ph.ResolvedAddress, ...]:
    octet = 34 + (sum(host.encode("ascii")) % 20)
    ip = ph.ipaddress.ip_address(f"93.184.216.{octet}")
    return (
        ph.ResolvedAddress(
            ip=ip,
            port=port,
            family=socket.AF_INET,
            socktype=socket.SOCK_STREAM,
            protocol=socket.IPPROTO_TCP,
            sockaddr=(str(ip), port),
        ),
    )


def test_client_returns_immutable_decoded_response_and_user_agent() -> None:
    seen: list[tuple[str, str]] = []

    def factory(hop: ph.ResolvedHop) -> httpx.BaseTransport:
        def handler(request: httpx.Request) -> httpx.Response:
            seen.append((request.headers["host"], request.headers["user-agent"]))
            return httpx.Response(200, headers={"content-type": "text/plain; charset=utf-8"}, content="xin chao".encode())
        return httpx.MockTransport(handler)

    client = ph.PinnedHTTPClient(resolver=_public_resolver, transport_factory=factory)
    result = client.get("https://example.com/a", user_agent="ua/1", timeout=3, max_redirects=5)
    assert result.status_code == 200
    assert result.content == b"xin chao"
    assert seen == [("example.com", "ua/1")]


def test_redirect_re_resolves_every_hop_and_blocks_private_target() -> None:
    calls: list[tuple[str, int]] = []

    def resolver(host: str, port: int) -> tuple[ph.ResolvedAddress, ...]:
        calls.append((host, port))
        if host == "internal.example":
            raise ph.BlockedAddressError("mixed or private destination")
        return _public_resolver(host, port)

    def factory(hop: ph.ResolvedHop) -> httpx.BaseTransport:
        return httpx.MockTransport(
            lambda _request: httpx.Response(302, headers={"location": "https://internal.example/secret"})
        )

    client = ph.PinnedHTTPClient(resolver=resolver, transport_factory=factory)
    with pytest.raises(ph.BlockedAddressError):
        client.get("https://public.example/start", user_agent="ua/1")
    assert calls == [("public.example", 443), ("internal.example", 443)]


@pytest.mark.parametrize("ip", _BLOCKED_IPS)
def test_redirect_to_blocked_literal_is_rejected(ip: str) -> None:
    target = f"https://[{ip}]/secret" if ":" in ip else f"https://{ip}/secret"

    def factory(hop: ph.ResolvedHop) -> httpx.BaseTransport:
        return httpx.MockTransport(
            lambda _request: httpx.Response(302, headers={"location": target})
        )

    client = ph.PinnedHTTPClient(
        resolver=ph.resolve_public_addresses,
        transport_factory=factory,
    )
    with pytest.raises(ph.BlockedAddressError):
        client.get("https://93.184.216.34/start", user_agent="ua/1")


def test_redirect_to_mixed_dns_answer_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def getaddrinfo(host: str, *_args, **_kwargs):
        calls.append(host)
        if host == "mixed.example":
            return [_answer("93.184.216.34"), _answer("127.0.0.1")]
        return [_answer("93.184.216.34")]

    monkeypatch.setattr(ph.socket, "getaddrinfo", getaddrinfo)

    def factory(_hop: ph.ResolvedHop) -> httpx.BaseTransport:
        return httpx.MockTransport(
            lambda _request: httpx.Response(
                302,
                headers={"location": "https://mixed.example/secret"},
            )
        )

    client = ph.PinnedHTTPClient(
        resolver=ph.resolve_public_addresses,
        transport_factory=factory,
    )
    with pytest.raises(ph.BlockedAddressError):
        client.get("https://public.example/start", user_agent="ua/1")
    assert calls == ["public.example", "mixed.example"]


def test_five_redirects_allowed_sixth_rejected() -> None:
    visited: list[str] = []

    def factory(hop: ph.ResolvedHop) -> httpx.BaseTransport:
        def handler(_request: httpx.Request) -> httpx.Response:
            visited.append(str(hop.url))
            index = int(hop.url.path.rsplit("/", 1)[-1])
            if index < 6:
                return httpx.Response(302, headers={"location": f"/{index + 1}"})
            return httpx.Response(200, content=b"done")
        return httpx.MockTransport(handler)

    client = ph.PinnedHTTPClient(resolver=_public_resolver, transport_factory=factory)
    with pytest.raises(ph.RedirectPolicyError):
        client.get("https://example.com/0", user_agent="ua/1", max_redirects=5)
    assert len(visited) == 6


@pytest.mark.parametrize(
    ("start", "location", "expected"),
    [
        ("https://a.example/start", "/next", "https://a.example/next"),
        ("https://a.example/start", "next", "https://a.example/next"),
        ("https://a.example/start", "https://b.example/next", "https://b.example/next"),
        ("https://a.example/start", "//b.example/next", "https://b.example/next"),
        ("http://a.example/start", "https://a.example/next", "https://a.example/next"),
        ("https://a.example/start", "http://a.example/next", "http://a.example/next"),
    ],
)
def test_client_supports_all_approved_redirect_forms(
    start: str,
    location: str,
    expected: str,
) -> None:
    def factory(hop: ph.ResolvedHop) -> httpx.BaseTransport:
        def handler(_request: httpx.Request) -> httpx.Response:
            if hop.url.path == "/start":
                return httpx.Response(302, headers={"location": location})
            return httpx.Response(200, content=b"done")

        return httpx.MockTransport(handler)

    result = ph.PinnedHTTPClient(
        resolver=_public_resolver,
        transport_factory=factory,
    ).get(start, user_agent="ua/1")
    assert result.url == expected
    assert len(result.redirects) == 1


@pytest.mark.parametrize(
    ("status", "location"),
    [(302, ""), (302, "   "), (300, "/next"), (304, "/next")],
)
def test_blank_or_nonstandard_redirect_is_final(status: int, location: str) -> None:
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(status, headers={"location": location})
    )
    client = ph.PinnedHTTPClient(
        resolver=_public_resolver,
        transport_factory=lambda _hop: transport,
    )
    result = client.get("https://example.com/a", user_agent="ua/1")
    assert result.status_code == status
    assert result.redirects == ()


@pytest.mark.parametrize(
    "location",
    ["#different-fragment", "https://example.com:443/a"],
)
def test_fragment_and_default_port_redirect_loops_are_rejected(location: str) -> None:
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(302, headers={"location": location})
    )
    client = ph.PinnedHTTPClient(
        resolver=_public_resolver,
        transport_factory=lambda _hop: transport,
    )
    with pytest.raises(ph.RedirectPolicyError):
        client.get("https://example.com/a#initial", user_agent="ua/1")


def test_unicode_and_ascii_idna_redirect_loop_is_rejected() -> None:
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(
            302,
            headers={"location": "https://xn--bcher-kva.example/a"},
        )
    )
    client = ph.PinnedHTTPClient(
        resolver=_public_resolver,
        transport_factory=lambda _hop: transport,
    )
    with pytest.raises(ph.RedirectPolicyError):
        client.get("https://BÜCHER.example/a", user_agent="ua/1")


def test_malformed_redirect_target_is_translated() -> None:
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(302, headers={"location": "http://[::1"})
    )
    client = ph.PinnedHTTPClient(
        resolver=_public_resolver,
        transport_factory=lambda _hop: transport,
    )
    with pytest.raises(ph.RedirectPolicyError):
        client.get("https://example.com/a", user_agent="ua/1")


def test_percent_encoded_and_literal_paths_are_distinct() -> None:
    def factory(hop: ph.ResolvedHop) -> httpx.BaseTransport:
        if hop.url.raw_path == b"/a%2Fb":
            response = httpx.Response(302, headers={"location": "/a/b"})
        else:
            response = httpx.Response(200, content=b"done")
        return httpx.MockTransport(lambda _request: response)

    result = ph.PinnedHTTPClient(
        resolver=_public_resolver,
        transport_factory=factory,
    ).get("https://example.com/a%2Fb", user_agent="ua/1")
    assert result.url == "https://example.com/a/b"
    assert len(result.redirects) == 1


def test_each_redirect_hop_resolves_once_and_gets_a_fresh_transport() -> None:
    resolutions: list[tuple[str, int]] = []
    transports: list[str] = []

    def resolver(host: str, port: int) -> tuple[ph.ResolvedAddress, ...]:
        resolutions.append((host, port))
        return _public_resolver(host, port)

    def factory(hop: ph.ResolvedHop) -> httpx.BaseTransport:
        transports.append(str(hop.url))
        if hop.host == "a.example":
            response = httpx.Response(
                302,
                headers={"location": "https://b.example/final"},
            )
        else:
            response = httpx.Response(200, content=b"done")
        return httpx.MockTransport(lambda _request: response)

    result = ph.PinnedHTTPClient(
        resolver=resolver,
        transport_factory=factory,
    ).get("https://a.example/start", user_agent="ua/1")
    assert result.content == b"done"
    assert resolutions == [("a.example", 443), ("b.example", 443)]
    assert transports == [
        "https://a.example/start",
        "https://b.example/final",
    ]


def test_environment_proxies_are_not_used(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:9")
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:9")
    monkeypatch.setenv("NO_PROXY", "")
    handled: list[str] = []

    def factory(_hop: ph.ResolvedHop) -> httpx.BaseTransport:
        def handler(request: httpx.Request) -> httpx.Response:
            handled.append(str(request.url))
            return httpx.Response(200, content=b"direct")

        return httpx.MockTransport(handler)

    result = ph.PinnedHTTPClient(
        resolver=_public_resolver,
        transport_factory=factory,
    ).get("https://example.com/a", user_agent="ua/1")
    assert result.content == b"direct"
    assert handled == ["https://example.com/a"]


def test_client_translates_transport_factory_failure() -> None:
    def factory(_hop: ph.ResolvedHop) -> httpx.BaseTransport:
        raise OSError("TLS context construction failed")

    client = ph.PinnedHTTPClient(
        resolver=_public_resolver,
        transport_factory=factory,
    )
    with pytest.raises(ph.PinnedTransportError):
        client.get("https://example.com/a", user_agent="ua/1")


@pytest.mark.parametrize(
    "error_factory",
    [
        lambda request: httpx.ConnectError("connect", request=request),
        lambda request: httpx.ReadError("read", request=request),
        lambda request: httpx.RemoteProtocolError("protocol", request=request),
        lambda _request: httpcore.ConnectError("tls"),
    ],
)
def test_client_translates_transport_failures(error_factory) -> None:
    def factory(_hop: ph.ResolvedHop) -> httpx.BaseTransport:
        def handler(request: httpx.Request) -> httpx.Response:
            raise error_factory(request)

        return httpx.MockTransport(handler)

    client = ph.PinnedHTTPClient(
        resolver=_public_resolver,
        transport_factory=factory,
    )
    with pytest.raises(ph.PinnedTransportError):
        client.get("https://example.com/a", user_agent="ua/1")


class _OneChunkStream(httpx.SyncByteStream):
    def __init__(self, content: bytes) -> None:
        self._content = content

    def __iter__(self):
        yield self._content


def test_shared_layer_decodes_gzip_exactly_once() -> None:
    encoded = gzip.compress("Vĩnh Long".encode("utf-8"))

    def factory(_hop: ph.ResolvedHop) -> httpx.BaseTransport:
        return httpx.MockTransport(
            lambda _request: httpx.Response(
                200,
                headers={"content-encoding": "gzip"},
                stream=_OneChunkStream(encoded),
            )
        )

    result = ph.PinnedHTTPClient(
        resolver=_public_resolver,
        transport_factory=factory,
    ).get("https://example.com/a", user_agent="ua/1")
    assert result.content == "Vĩnh Long".encode("utf-8")
    assert result.content != encoded


def test_concurrent_calls_do_not_leak_pinned_hops() -> None:
    observed: list[tuple[str, str]] = []

    def factory(hop: ph.ResolvedHop) -> httpx.BaseTransport:
        approved = str(hop.addresses[0].ip)

        def handler(_request: httpx.Request) -> httpx.Response:
            observed.append((hop.host, approved))
            return httpx.Response(200, content=hop.host.encode("ascii"))

        return httpx.MockTransport(handler)

    client = ph.PinnedHTTPClient(
        resolver=_public_resolver,
        transport_factory=factory,
    )
    hosts = [f"h{index}.example" for index in range(12)]
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(
            executor.map(
                lambda host: client.get(f"https://{host}/", user_agent="ua/1"),
                hosts,
            )
        )
    assert [result.content.decode("ascii") for result in results] == hosts
    assert {host for host, _approved in observed} == set(hosts)
    assert len(observed) == len(hosts)
