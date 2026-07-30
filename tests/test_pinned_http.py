from __future__ import annotations

import gzip
import inspect
import logging
import math
import socket
import ssl
import threading
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
    # RFC 7526 6to4 relay anycast: the IPv4 peer of the 2002::/16 form below.
    # IPv6Address.sixtofour only catches the IPv6 side of the same mechanism.
    "192.88.99.1",
    "192.88.99.255",
    "::",
    "::1",
    "::127.0.0.1",
    "::ffff:127.0.0.1",
    # RFC 2765 IPv4-translated (::ffff:0:0:0/96). This is a DIFFERENT network
    # from the IPv4-mapped ::ffff:0:0/96 entry above and .ipv4_mapped is None
    # here, so the mapped check does not cover it.
    "::ffff:0:7f00:1",
    "::ffff:0:a00:1",
    "64:ff9b::7f00:1",
    "64:ff9b:1::7f00:1",
    "2002:7f00:1::",
    "2001:0000:4136:e378:8000:63bf:3fff:fdd2",
    "2001:db8:1:2:0:5efe:7f00:1",
    # IPv6 internal scopes. is_global already rejects ULA and link-local, but
    # CPython 3.14 dropped the RFC 3879 site-local fec0::/10 from
    # _private_networks, so is_global returns True across that whole range.
    "fc00::1",
    "fd12:3456:789a::1",
    "fe80::1",
    "fec0::1",
    "fec0:0:0:ffff::1",
    "feff:ffff:ffff:ffff:ffff:ffff:ffff:ffff",
)

# Additive-denial guard: every tightening of the address policy must leave
# these genuinely public destinations reachable.
_ALLOWED_IPS = (
    "1.1.1.1",
    "8.8.8.8",
    "93.184.216.34",
    # Immediately either side of the 6to4 relay anycast /24 that is denied.
    "192.88.98.255",
    "192.88.100.0",
    "2606:2800:220:1:248:1893:25c8:1946",
    "2001:4860:4860::8888",
)


@pytest.mark.parametrize("ip", _ALLOWED_IPS)
def test_public_addresses_stay_allowed(ip: str) -> None:
    ph._require_allowed_ip(ph.ipaddress.ip_address(ip))


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
        ph.validate_public_url(url, resolver=lambda _host, _port, _budget: ())


def test_resolver_allows_and_deduplicates_public_answers(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_dns(monkeypatch, "93.184.216.34", "2606:2800:220:1:248:1893:25c8:1946", "93.184.216.34")
    result = ph.resolve_public_addresses("example.com", 443, ph.DeadlineBudget.start(1.0))
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
        ph.resolve_public_addresses("example.com", 443, ph.DeadlineBudget.start(1.0))


def test_resolver_rejects_mixed_answer_set(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_dns(monkeypatch, "93.184.216.34", "127.0.0.1")
    with pytest.raises(ph.BlockedAddressError):
        ph.resolve_public_addresses("example.com", 443, ph.DeadlineBudget.start(1.0))


def test_resolver_translates_malformed_answers(monkeypatch: pytest.MonkeyPatch) -> None:
    malformed = [
        (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("not-an-ip", 443)),
    ]
    monkeypatch.setattr(ph.socket, "getaddrinfo", lambda *_args, **_kwargs: malformed)
    with pytest.raises(ph.ResolutionError):
        ph.resolve_public_addresses("example.com", 443, ph.DeadlineBudget.start(1.0))


def test_resolver_translates_dns_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*_args, **_kwargs):
        raise socket.gaierror("dns failed")

    monkeypatch.setattr(ph.socket, "getaddrinfo", fail)
    with pytest.raises(ph.ResolutionError):
        ph.resolve_public_addresses("example.com", 443, ph.DeadlineBudget.start(1.0))


def test_dns_gate_limits_active_resolvers_to_four(monkeypatch: pytest.MonkeyPatch) -> None:
    entered = threading.Barrier(5)
    release = threading.Event()
    active = 0
    peak = 0
    lock = threading.Lock()

    def blocked_getaddrinfo(*_args, **_kwargs):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        entered.wait(timeout=2.0)
        release.wait(timeout=2.0)
        with lock:
            active -= 1
        return [_answer("93.184.216.34")]

    monkeypatch.setattr(ph.socket, "getaddrinfo", blocked_getaddrinfo)
    budgets = [ph.DeadlineBudget.start(10.0) for _ in range(4)]
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(ph.resolve_public_addresses, "example.com", 443, budget)
            for budget in budgets
        ]
        try:
            entered.wait(timeout=2.0)
            with pytest.raises(ph.ResolverSaturatedError):
                ph.resolve_public_addresses(
                    "fifth.example",
                    443,
                    ph.DeadlineBudget.start(0.01),
                )
            assert peak == 4
        finally:
            release.set()
        assert all(future.result() for future in futures)


def test_timed_out_dns_threads_hold_slots_until_os_returns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entered = threading.Barrier(5)
    release = threading.Event()
    call_count = 0
    resolved_hosts: list[str] = []
    resolver_threads: list[threading.Thread] = []
    lock = threading.Lock()

    def blocked_getaddrinfo(host: str, *_args, **_kwargs):
        nonlocal call_count
        with lock:
            call_count += 1
            current = call_count
            resolved_hosts.append(host)
        if current <= 4:
            entered.wait(timeout=2.0)
            release.wait(timeout=2.0)
        return [_answer("93.184.216.34")]

    monkeypatch.setattr(ph.socket, "getaddrinfo", blocked_getaddrinfo)

    original_thread = ph.threading.Thread

    def capture_resolver_thread(*args, **kwargs):
        thread = original_thread(*args, **kwargs)
        if kwargs.get("name") == "vinhlong360-pinned-dns":
            with lock:
                resolver_threads.append(thread)
        return thread

    monkeypatch.setattr(ph.threading, "Thread", capture_resolver_thread)
    try:
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(
                    ph.resolve_public_addresses,
                    f"blocked-{index}.example",
                    443,
                    ph.DeadlineBudget.start(0.05),
                )
                for index in range(4)
            ]
            entered.wait(timeout=2.0)
            for future in futures:
                with pytest.raises(ph.PinnedDeadlineExceeded):
                    future.result(timeout=1.0)
            with pytest.raises(ph.ResolverSaturatedError):
                ph.resolve_public_addresses(
                    "fifth.example",
                    443,
                    ph.DeadlineBudget.start(0.01),
                )
        release.set()
        for thread in resolver_threads:
            thread.join(timeout=2.0)
        assert len(resolver_threads) == 4
        assert all(not thread.is_alive() for thread in resolver_threads)
        recovered = ph.resolve_public_addresses(
            "recovered.example",
            443,
            ph.DeadlineBudget.start(1.0),
        )
        assert str(recovered[0].ip) == "93.184.216.34"
        assert "fifth.example" not in resolved_hosts
    finally:
        release.set()
        for thread in resolver_threads:
            thread.join(timeout=2.0)


@pytest.mark.parametrize("ip", _ALLOWED_IPS)
def test_public_literal_ip_never_calls_dns(
    monkeypatch: pytest.MonkeyPatch,
    ip: str,
) -> None:
    monkeypatch.setattr(ph.socket, "getaddrinfo", lambda *_args, **_kwargs: pytest.fail("DNS called"))
    addresses = ph.resolve_public_addresses(ip, 443, ph.DeadlineBudget.start(1.0))
    assert addresses[0].ip == ph.ipaddress.ip_address(ip)


@pytest.mark.parametrize("ip", _BLOCKED_IPS)
def test_blocked_literal_ip_never_calls_dns(
    monkeypatch: pytest.MonkeyPatch,
    ip: str,
) -> None:
    monkeypatch.setattr(ph.socket, "getaddrinfo", lambda *_args, **_kwargs: pytest.fail("DNS called"))
    with pytest.raises(ph.BlockedAddressError):
        ph.resolve_public_addresses(ip, 443, ph.DeadlineBudget.start(1.0))


def test_validate_public_url_uses_injected_resolver() -> None:
    calls: list[tuple[str, int, ph.DeadlineBudget]] = []
    budget = ph.DeadlineBudget.start(1.0)

    def resolver(
        host: str,
        port: int,
        received_budget: ph.DeadlineBudget,
    ) -> tuple[ph.ResolvedAddress, ...]:
        calls.append((host, port, received_budget))
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

    ph.validate_public_url(
        "https://Example.COM/path#fragment",
        resolver=resolver,
        budget=budget,
    )
    assert calls == [("example.com", 443, budget)]


def test_validate_public_url_uses_ascii_idna_host() -> None:
    calls: list[tuple[str, int]] = []

    def resolver(
        host: str,
        port: int,
        _budget: ph.DeadlineBudget,
    ) -> tuple[ph.ResolvedAddress, ...]:
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


def test_validate_public_url_default_budget_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    start = 123.0
    received: list[ph.DeadlineBudget] = []
    monkeypatch.setattr(ph.time, "monotonic", lambda: start)

    def resolver(
        _host: str,
        _port: int,
        budget: ph.DeadlineBudget,
    ) -> tuple[ph.ResolvedAddress, ...]:
        received.append(budget)
        return _public_resolver("example.com", 443, budget)

    monkeypatch.setattr(ph, "resolve_public_addresses", resolver)
    ph.validate_public_url("https://example.com", resolver=ph.resolve_public_addresses)

    assert received[0].expires_at - start == pytest.approx(15.0)


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


class PartialSendSocket(FakeSocket):
    def __init__(self, peer: tuple, send_sizes: list[int]) -> None:
        super().__init__(peer)
        self.send_sizes = iter(send_sizes)

    def send(self, _buffer: bytes) -> int:
        return next(self.send_sizes)


class ZeroSendSocket(FakeSocket):
    def send(self, _buffer: bytes) -> int:
        return 0


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
    backend = ph._PinnedNetworkBackend(
        hop,
        policy=_policy(),
        budget=ph.DeadlineBudget.start(5.0),
        socket_factory=lambda *_args: fake,
    )
    stream = backend.connect_tcp("example.com", 443, timeout=5.0)
    assert fake.connected_to == ("93.184.216.34", 443)
    assert stream.get_extra_info("server_addr") == ("93.184.216.34", 443)


def test_backend_closes_and_rejects_peer_mismatch() -> None:
    hop = _resolved_hop("https://example.com/x", "93.184.216.34")
    fake = FakeSocket(("127.0.0.1", 443))
    backend = ph._PinnedNetworkBackend(
        hop,
        policy=_policy(),
        budget=ph.DeadlineBudget.start(5.0),
        socket_factory=lambda *_args: fake,
    )
    with pytest.raises(ph.PeerMismatchError):
        backend.connect_tcp("example.com", 443, timeout=5.0)
    assert fake.closed is True


def test_backend_fallback_uses_one_connect_budget() -> None:
    hop = _resolved_hop("https://example.com/x", "93.184.216.34", "93.184.216.35")
    first = FakeSocket(("93.184.216.34", 443), connect_error=OSError("refused"))
    second = FakeSocket(("93.184.216.35", 443))
    sockets = iter([first, second])
    times = iter([11.0, 11.0, 12.0, 12.0])
    backend = ph._PinnedNetworkBackend(
        hop,
        policy=_policy(inactivity_timeout_seconds=5.0),
        budget=ph.DeadlineBudget(expires_at=15.0),
        socket_factory=lambda *_args: next(sockets),
        monotonic=lambda: next(times),
    )
    stream = backend.connect_tcp("example.com", 443, timeout=5.0)
    assert stream.get_extra_info("server_addr") == ("93.184.216.35", 443)
    # The attempt at t=11.0 may spend 4.0s and the fallback at t=12.0 only the
    # REMAINING 3.0s. A per-address timeout reset would hand 5.0s to each
    # address and let N addresses stretch the caller's 5s budget to N*5s, so
    # assert the exact remaining budget, not just reach.
    assert first.timeouts == [4.0]
    assert second.timeouts == [3.0]
    assert second.timeouts[0] < first.timeouts[0] < 5.0


def test_backend_skips_socket_factory_when_deadline_is_expired() -> None:
    hop = _resolved_hop("https://example.com/x", "93.184.216.34")
    calls = 0

    def socket_factory(*_args):
        nonlocal calls
        calls += 1
        return FakeSocket(("93.184.216.34", 443))

    backend = ph._PinnedNetworkBackend(
        hop,
        policy=_policy(inactivity_timeout_seconds=5.0),
        budget=ph.DeadlineBudget(expires_at=5.0),
        socket_factory=socket_factory,
        monotonic=lambda: 5.0,
    )

    with pytest.raises(ph.PinnedDeadlineExceeded):
        backend.connect_tcp("example.com", 443, timeout=5.0)

    assert calls == 0


def test_backend_recomputes_socket_timeout_before_and_after_factory() -> None:
    hop = _resolved_hop("https://example.com/x", "93.184.216.34")
    fake = FakeSocket(("93.184.216.34", 443))

    class RecordingBudget:
        def __init__(self) -> None:
            self.calls: list[tuple[float | None, float]] = []

        def socket_timeout(
            self,
            requested_timeout: float | None,
            inactivity_timeout_seconds: float,
            *,
            monotonic,
        ) -> float:
            self.calls.append((requested_timeout, inactivity_timeout_seconds))
            return min(requested_timeout or inactivity_timeout_seconds, inactivity_timeout_seconds)

        def remaining(self, *, monotonic):
            raise AssertionError("pre-address check must use socket_timeout")

    budget = RecordingBudget()
    backend = ph._PinnedNetworkBackend(
        hop,
        policy=_policy(inactivity_timeout_seconds=5.0),
        budget=budget,
        socket_factory=lambda *_args: fake,
        monotonic=lambda: 1.0,
    )

    backend.connect_tcp("example.com", 443, timeout=5.0)

    assert budget.calls == [(5.0, 5.0), (5.0, 5.0)]


def test_backend_closes_socket_when_deadline_expires_after_factory() -> None:
    hop = _resolved_hop("https://example.com/x", "93.184.216.34")
    fake = FakeSocket(("93.184.216.34", 443))
    times = iter([1.0, 6.0])

    backend = ph._PinnedNetworkBackend(
        hop,
        policy=_policy(inactivity_timeout_seconds=5.0),
        budget=ph.DeadlineBudget(expires_at=5.0),
        socket_factory=lambda *_args: fake,
        monotonic=lambda: next(times),
    )

    with pytest.raises(ph.PinnedDeadlineExceeded):
        backend.connect_tcp("example.com", 443, timeout=5.0)

    assert fake.closed is True
    assert fake.connected_to is None


def test_transport_wires_the_pinned_network_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class FakePool:
        def close(self) -> None:
            pass

    def pool_factory(**kwargs: object) -> FakePool:
        captured.update(kwargs)
        return FakePool()

    monkeypatch.setattr(ph.httpcore, "ConnectionPool", pool_factory)
    hop = _resolved_hop("https://example.com/x", "93.184.216.34")
    ph._PinnedHTTPTransport(
        hop,
        policy=_policy(),
        budget=ph.DeadlineBudget.start(5.0),
    )

    backend = captured.get("network_backend")
    # Without this kwarg httpcore falls back to SyncBackend, which dials via
    # socket.create_connection() and performs its own unpoliced DNS resolution
    # at connect time — every pinning guarantee in this module would vanish.
    assert isinstance(backend, ph._PinnedNetworkBackend)

    # ...and it must carry THIS hop: only the hop's origin is dialable, and it
    # is dialed at the exact pre-approved sockaddr rather than by name.
    fake = FakeSocket(("93.184.216.34", 443))
    backend._socket_factory = lambda *_args: fake
    stream = backend.connect_tcp("example.com", 443, timeout=5.0)
    assert fake.connected_to == ("93.184.216.34", 443)
    assert stream.get_extra_info("server_addr") == ("93.184.216.34", 443)
    with pytest.raises(ph.PeerMismatchError):
        backend.connect_tcp("other.example", 443, timeout=5.0)


def test_stream_tls_uses_original_hostname() -> None:
    fake = FakeSocket(("93.184.216.34", 443))
    seen: list[str | None] = []

    class FakeSSLContext:
        def wrap_socket(self, sock: FakeSocket, *, server_hostname: str | None) -> FakeSocket:
            assert sock is fake
            seen.append(server_hostname)
            return fake

    stream = ph._PinnedNetworkStream(
        fake,
        policy=_policy(),
        budget=ph.DeadlineBudget.start(5.0),
    )
    stream.start_tls(FakeSSLContext(), server_hostname="example.com", timeout=5.0)
    assert seen == ["example.com"]
    assert fake.timeouts[-1] == 2.0


@pytest.mark.parametrize(
    ("requested", "inactivity", "expires_at", "now", "expected"),
    [
        (3.0, 8.0, 10.0, 1.0, 3.0),
        (9.0, 4.0, 10.0, 1.0, 4.0),
        (9.0, 8.0, 10.0, 3.0, 7.0),
    ],
)
def test_tls_uses_minimum_requested_inactivity_and_remaining_deadline(
    requested: float,
    inactivity: float,
    expires_at: float,
    now: float,
    expected: float,
) -> None:
    fake = FakeSocket(("93.184.216.34", 443))

    class FakeSSLContext:
        def wrap_socket(self, sock: FakeSocket, *, server_hostname: str | None) -> FakeSocket:
            return sock

    stream = ph._PinnedNetworkStream(
        fake,
        policy=_policy(inactivity_timeout_seconds=inactivity),
        budget=ph.DeadlineBudget(expires_at=expires_at),
        monotonic=lambda: now,
    )

    stream.start_tls(FakeSSLContext(), server_hostname="example.com", timeout=requested)

    assert fake.timeouts == [expected]


@pytest.mark.parametrize(
    ("host", "port"),
    [("other.example", 443), ("example.com", 80)],
)
def test_backend_rejects_httpcore_origin_mismatch(host: str, port: int) -> None:
    hop = _resolved_hop("https://example.com/x", "93.184.216.34")
    fake = FakeSocket(("93.184.216.34", 443))
    backend = ph._PinnedNetworkBackend(
        hop,
        policy=_policy(),
        budget=ph.DeadlineBudget.start(5.0),
        socket_factory=lambda *_args: fake,
    )
    with pytest.raises(ph.PeerMismatchError):
        backend.connect_tcp(host, port, timeout=5.0)
    assert fake.connected_to is None


def test_backend_translates_connect_timeout() -> None:
    hop = _resolved_hop("https://example.com/x", "93.184.216.34")
    fake = FakeSocket(("93.184.216.34", 443), connect_error=socket.timeout("timed out"))
    backend = ph._PinnedNetworkBackend(
        hop,
        policy=_policy(),
        budget=ph.DeadlineBudget.start(5.0),
        socket_factory=lambda *_args: fake,
    )
    with pytest.raises(httpcore.ConnectTimeout):
        backend.connect_tcp("example.com", 443, timeout=5.0)
    assert fake.closed is True


def test_backend_translates_socket_creation_failure() -> None:
    hop = _resolved_hop("https://example.com/x", "93.184.216.34")

    def fail_socket(*_args):
        raise OSError("socket creation failed")

    backend = ph._PinnedNetworkBackend(
        hop,
        policy=_policy(),
        budget=ph.DeadlineBudget.start(5.0),
        socket_factory=fail_socket,
    )
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
    stream = ph._PinnedNetworkStream(
        fake,
        policy=_policy(),
        budget=ph.DeadlineBudget.start(5.0),
    )
    with pytest.raises(expected):
        if operation == "read":
            stream.read(16, timeout=2.0)
        else:
            stream.write(b"x", timeout=2.0)


def test_partial_write_recomputes_remaining_deadline() -> None:
    sock = PartialSendSocket(("93.184.216.34", 443), [2, 2])
    times = iter([1.0, 3.0])
    stream = ph._PinnedNetworkStream(
        sock,
        policy=_policy(inactivity_timeout_seconds=8.0),
        budget=ph.DeadlineBudget(expires_at=10.0),
        monotonic=lambda: next(times),
    )

    stream.write(b"abcd", timeout=9.0)

    assert sock.timeouts == [8.0, 7.0]


def test_read_uses_smaller_remaining_deadline_than_inactivity_timeout() -> None:
    sock = FakeSocket(("93.184.216.34", 443))
    stream = ph._PinnedNetworkStream(
        sock,
        policy=_policy(inactivity_timeout_seconds=8.0),
        budget=ph.DeadlineBudget(expires_at=10.0),
        monotonic=lambda: 3.0,
    )

    assert stream.read(16, timeout=9.0) == b"data"
    assert sock.timeouts == [7.0]


def test_zero_send_raises_write_error() -> None:
    stream = ph._PinnedNetworkStream(
        ZeroSendSocket(("93.184.216.34", 443)),
        policy=_policy(),
        budget=ph.DeadlineBudget(expires_at=10.0),
        monotonic=lambda: 1.0,
    )

    with pytest.raises(httpcore.WriteError, match="socket connection broken"):
        stream.write(b"x", timeout=2.0)


@pytest.mark.parametrize("operation", ["read", "write"])
def test_stream_socket_timeout_reports_total_deadline_exhaustion(operation: str) -> None:
    times = iter([1.0, 6.0])
    fake = FakeSocket(
        ("93.184.216.34", 443),
        recv_error=socket.timeout("read timeout") if operation == "read" else None,
        send_error=socket.timeout("write timeout") if operation == "write" else None,
    )
    stream = ph._PinnedNetworkStream(
        fake,
        policy=_policy(inactivity_timeout_seconds=8.0),
        budget=ph.DeadlineBudget(expires_at=5.0),
        monotonic=lambda: next(times),
    )

    with pytest.raises(ph.PinnedDeadlineExceeded):
        if operation == "read":
            stream.read(16, timeout=9.0)
        else:
            stream.write(b"x", timeout=9.0)


@pytest.mark.parametrize(
    ("inactivity_timeout", "requested_timeout"),
    [(4.0, 8.0), (8.0, 4.0), (4.0, 4.0)],
    ids=["ties-inactivity", "ties-requested", "ties-both"],
)
def test_stream_read_timeout_maps_exact_deadline_ties_to_deadline(
    inactivity_timeout: float,
    requested_timeout: float,
) -> None:
    times = iter([0.0, 3.999])
    stream = ph._PinnedNetworkStream(
        FakeSocket(
            ("93.184.216.34", 443),
            recv_error=socket.timeout("deadline-tied read timeout"),
        ),
        policy=_policy(inactivity_timeout_seconds=inactivity_timeout),
        budget=ph.DeadlineBudget(expires_at=4.0),
        monotonic=lambda: next(times),
    )

    with pytest.raises(ph.PinnedDeadlineExceeded):
        stream.read(16, timeout=requested_timeout)


@pytest.mark.parametrize(
    ("total_remaining", "expected_error"),
    [
        (math.nextafter(4.0, 0.0), ph.PinnedDeadlineExceeded),
        (math.nextafter(4.0, math.inf), httpcore.ReadTimeout),
    ],
    ids=["total-one-ulp-shorter", "inactivity-one-ulp-shorter"],
)
def test_stream_read_timeout_respects_float_boundary_precision(
    total_remaining: float,
    expected_error: type[Exception],
) -> None:
    times = iter([0.0, total_remaining - 0.001])
    stream = ph._PinnedNetworkStream(
        FakeSocket(
            ("93.184.216.34", 443),
            recv_error=socket.timeout("near-boundary read timeout"),
        ),
        policy=_policy(inactivity_timeout_seconds=4.0),
        budget=ph.DeadlineBudget(expires_at=total_remaining),
        monotonic=lambda: next(times),
    )

    with pytest.raises(expected_error) as exc_info:
        stream.read(16, timeout=4.0)

    assert type(exc_info.value) is expected_error


@pytest.mark.parametrize(
    ("inactivity_timeout", "requested_timeout"),
    [(3.0, 8.0), (8.0, 3.0)],
    ids=["shorter-inactivity", "shorter-requested"],
)
def test_stream_shorter_non_deadline_read_timeout_stays_read_timeout(
    inactivity_timeout: float,
    requested_timeout: float,
) -> None:
    times = iter([0.0, 3.999])
    stream = ph._PinnedNetworkStream(
        FakeSocket(
            ("93.184.216.34", 443),
            recv_error=socket.timeout("non-deadline read timeout"),
        ),
        policy=_policy(inactivity_timeout_seconds=inactivity_timeout),
        budget=ph.DeadlineBudget(expires_at=4.0),
        monotonic=lambda: next(times),
    )

    with pytest.raises(httpcore.ReadTimeout):
        stream.read(16, timeout=requested_timeout)


def test_backend_applies_requested_options_and_tcp_nodelay() -> None:
    hop = _resolved_hop("https://example.com/x", "93.184.216.34")
    fake = FakeSocket(("93.184.216.34", 443))
    backend = ph._PinnedNetworkBackend(
        hop,
        policy=_policy(),
        budget=ph.DeadlineBudget.start(5.0),
        socket_factory=lambda *_args: fake,
    )
    keepalive = (socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    backend.connect_tcp("example.com", 443, timeout=5.0, socket_options=(keepalive,))
    assert keepalive in fake.options
    assert (socket.IPPROTO_TCP, socket.TCP_NODELAY, 1) in fake.options


def test_backend_rejects_unix_sockets() -> None:
    hop = _resolved_hop("https://example.com/x", "93.184.216.34")
    backend = ph._PinnedNetworkBackend(
        hop,
        policy=_policy(),
        budget=ph.DeadlineBudget.start(5.0),
    )
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
        ph._PinnedNetworkStream(
            fake,
            policy=_policy(),
            budget=ph.DeadlineBudget.start(5.0),
        ).start_tls(
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
    ph._PinnedHTTPTransport(
        hop,
        policy=_policy(),
        budget=ph.DeadlineBudget.start(5.0),
    )

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
    transport = ph._PinnedHTTPTransport(
        hop,
        policy=_policy(),
        budget=ph.DeadlineBudget.start(5.0),
    )
    with httpx.Client(transport=transport, trust_env=False) as client:
        response = client.get("https://BÜCHER.example/x")
        assert response.content == b"ok"
        assert response.headers.get_list("set-cookie") == ["a=1", "b=2"]

    assert captured[0].url.host == b"xn--bcher-kva.example"
    assert (b"Host", b"xn--bcher-kva.example") in captured[0].headers
    assert closed == [True]


def _public_resolver(
    host: str,
    port: int,
    _budget: ph.DeadlineBudget,
) -> tuple[ph.ResolvedAddress, ...]:
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


def _policy(
    *,
    max_encoded_bytes: int = 1024,
    max_decoded_bytes: int = 2048,
    accepted_encodings: tuple[str, ...] = ("gzip", "identity"),
    inactivity_timeout_seconds: float = 2.0,
    total_timeout_seconds: float = 5.0,
    max_redirects: int = 5,
) -> ph.EgressPolicy:
    return ph.EgressPolicy(
        max_encoded_bytes=max_encoded_bytes,
        max_decoded_bytes=max_decoded_bytes,
        accepted_encodings=accepted_encodings,
        inactivity_timeout_seconds=inactivity_timeout_seconds,
        total_timeout_seconds=total_timeout_seconds,
        max_redirects=max_redirects,
    )


class SocketPairClient:
    def __init__(
        self,
        sock: socket.socket,
        *,
        peer: tuple[str, int] = ("93.184.216.34", 80),
        max_send: int | None = None,
        zero_send: bool = False,
    ) -> None:
        self.sock = sock
        self.peer = peer
        self.max_send = max_send
        self.zero_send = zero_send
        self.closed = False

    def connect(self, _sockaddr: tuple) -> None:
        return None

    def send(self, buffer: bytes) -> int:
        if self.zero_send:
            self.zero_send = False
            return 0
        payload = buffer if self.max_send is None else buffer[: self.max_send]
        return self.sock.send(payload)

    def recv(self, max_bytes: int) -> bytes:
        return self.sock.recv(max_bytes)

    def settimeout(self, value: float | None) -> None:
        self.sock.settimeout(value)

    def setsockopt(self, *_args) -> None:
        return None

    def bind(self, address: tuple) -> None:
        self.sock.bind(address)

    def getpeername(self) -> tuple[str, int]:
        return self.peer

    def getsockname(self) -> tuple[str, int]:
        return ("192.0.2.10", 49152)

    def fileno(self) -> int:
        return self.sock.fileno()

    def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        self.sock.close()


class RealTransportHarness:
    def __init__(
        self,
        client: ph.PinnedHTTPClient,
        received: list[bytes],
        wrapped: SocketPairClient,
        server: threading.Thread,
        response_gate: threading.Event | None,
        transports: list[ph._PinnedHTTPTransport],
        transport_close_calls: list[ph._PinnedHTTPTransport],
    ) -> None:
        self.client = client
        self.received = received
        self.wrapped = wrapped
        self.server = server
        self.response_gate = response_gate
        self.transports = transports
        self.transport_close_calls = transport_close_calls
        self._cleaned = False
        self._transport_closed_before_cleanup = False

    def cleanup(self) -> bool:
        if self._cleaned:
            return self._transport_closed_before_cleanup
        if self.response_gate is not None:
            self.response_gate.set()
        self._transport_closed_before_cleanup = bool(self.transport_close_calls)
        try:
            for transport in self.transports:
                transport.close()
        finally:
            self.wrapped.close()
            self.server.join(timeout=2.0)
            assert not self.server.is_alive()
            self._cleaned = True
        return self._transport_closed_before_cleanup


def _serve_http(
    peer: socket.socket,
    response_chunks: tuple[bytes, ...],
    received: list[bytes],
    response_gate: threading.Event | None,
) -> None:
    request = bytearray()
    request_recorded = False
    try:
        peer.settimeout(2.0)
        while b"\r\n\r\n" not in request:
            chunk = peer.recv(4096)
            if not chunk:
                break
            request.extend(chunk)
        received.append(bytes(request))
        request_recorded = True
        if response_gate is not None:
            response_gate.wait(timeout=2.0)
        for chunk in response_chunks:
            peer.sendall(chunk)
    except OSError:
        pass
    finally:
        if not request_recorded:
            received.append(bytes(request))
        peer.close()


def _real_transport_client(
    response_chunks: tuple[bytes, ...],
    *,
    peer: tuple[str, int] = ("93.184.216.34", 80),
    max_send: int | None = None,
    zero_send: bool = False,
    response_gate: threading.Event | None = None,
) -> RealTransportHarness:
    client_socket, server_socket = socket.socketpair()
    wrapped = SocketPairClient(
        client_socket,
        peer=peer,
        max_send=max_send,
        zero_send=zero_send,
    )
    received: list[bytes] = []
    transports: list[ph._PinnedHTTPTransport] = []
    transport_close_calls: list[ph._PinnedHTTPTransport] = []
    server = threading.Thread(
        target=_serve_http,
        args=(server_socket, response_chunks, received, response_gate),
        daemon=True,
    )
    server.start()

    def resolver(
        _host: str,
        port: int,
        _budget: ph.DeadlineBudget,
    ) -> tuple[ph.ResolvedAddress, ...]:
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

    def factory(
        hop: ph.ResolvedHop,
        policy: ph.EgressPolicy,
        budget: ph.DeadlineBudget,
    ) -> ph._PinnedHTTPTransport:
        transport = ph._PinnedHTTPTransport(
            hop,
            policy=policy,
            budget=budget,
            socket_factory=lambda *_args: wrapped,
        )
        original_close = transport.close

        def close_transport() -> None:
            transport_close_calls.append(transport)
            original_close()

        transport.close = close_transport
        transports.append(transport)
        return transport

    client = ph.PinnedHTTPClient(
        resolver=resolver,
        transport_factory=factory,
    )
    return RealTransportHarness(
        client,
        received,
        wrapped,
        server,
        response_gate,
        transports,
        transport_close_calls,
    )


def _fixed_http_response(
    body: bytes,
    *,
    headers: tuple[bytes, ...] = (),
) -> tuple[bytes, ...]:
    head = b"\r\n".join(
        (
            b"HTTP/1.1 200 OK",
            f"Content-Length: {len(body)}".encode("ascii"),
            *headers,
            b"",
            b"",
        )
    )
    return (head + body,)


def test_real_httpcore_emits_request_line_host_and_reads_fixed_length() -> None:
    harness = _real_transport_client(
        (b"HTTP/1.1 200 OK\r\nContent-Length: 5\r\n\r\nhello",)
    )
    try:
        result = harness.client.get(
            "http://example.com/path?q=1",
            user_agent="test-agent",
            policy=_policy(
                accepted_encodings=("identity",),
                inactivity_timeout_seconds=1.0,
                total_timeout_seconds=2.0,
            ),
            audit_context="test",
        )
    finally:
        transport_closed = harness.cleanup()

    assert transport_closed is True
    assert harness.received[0].startswith(b"GET /path?q=1 HTTP/1.1\r\n")
    assert b"\r\nHost: example.com\r\n" in harness.received[0]
    assert b"\r\nUser-Agent: test-agent\r\n" in harness.received[0]
    assert harness.received[0].endswith(b"\r\n\r\n")
    assert result.content == b"hello"
    assert harness.wrapped.closed is True


def test_real_httpcore_reads_chunked_body() -> None:
    harness = _real_transport_client(
        (
            b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n5\r\nhel",
            b"lo\r\n0\r\n\r\n",
        )
    )
    try:
        result = harness.client.get(
            "http://example.com/path?q=1",
            user_agent="test-agent",
            policy=_policy(accepted_encodings=("identity",)),
            audit_context="test",
        )
    finally:
        transport_closed = harness.cleanup()

    assert transport_closed is True
    assert harness.received[0].startswith(b"GET /path?q=1 HTTP/1.1\r\n")
    assert b"\r\nHost: example.com\r\n" in harness.received[0]
    assert result.content == b"hello"
    assert harness.wrapped.closed is True


def test_real_httpcore_partial_send_completes_request() -> None:
    harness = _real_transport_client(
        _fixed_http_response(b"ok"),
        max_send=3,
    )
    try:
        result = harness.client.get(
            "http://example.com/path?q=1",
            user_agent="test-agent",
            policy=_policy(accepted_encodings=("identity",)),
            audit_context="test",
        )
    finally:
        transport_closed = harness.cleanup()

    assert transport_closed is True
    assert harness.received[0].startswith(b"GET /path?q=1 HTTP/1.1\r\n")
    assert b"\r\nHost: example.com\r\n" in harness.received[0]
    assert harness.received[0].endswith(b"\r\n\r\n")
    assert result.content == b"ok"
    assert harness.wrapped.closed is True


def test_real_httpcore_zero_send_raises_pinned_transport_error() -> None:
    harness = _real_transport_client(
        _fixed_http_response(b"unused"),
        zero_send=True,
    )
    try:
        with pytest.raises(ph.PinnedTransportError) as exc_info:
            harness.client.get(
                "http://example.com/path?q=1",
                user_agent="test-agent",
                policy=_policy(accepted_encodings=("identity",)),
                audit_context="test",
            )
    finally:
        transport_closed = harness.cleanup()

    assert transport_closed is True
    assert type(exc_info.value) is ph.PinnedTransportError
    assert harness.received == [b""]
    assert harness.wrapped.closed is True


def test_real_httpcore_peer_mismatch_prevents_request_bytes() -> None:
    harness = _real_transport_client(
        _fixed_http_response(b"unused"),
        peer=("127.0.0.1", 80),
    )
    try:
        with pytest.raises(ph.PeerMismatchError) as exc_info:
            harness.client.get(
                "http://example.com/path?q=1",
                user_agent="test-agent",
                policy=_policy(accepted_encodings=("identity",)),
                audit_context="test",
            )
    finally:
        transport_closed = harness.cleanup()

    assert transport_closed is True
    assert type(exc_info.value) is ph.PeerMismatchError
    assert harness.received == [b""]
    assert harness.wrapped.closed is True


def test_real_httpcore_harness_cleanup_is_idempotent() -> None:
    harness = _real_transport_client(_fixed_http_response(b"unused"))

    try:
        assert harness.cleanup() is False
        assert harness.cleanup() is False
    finally:
        harness.cleanup()
    assert harness.wrapped.closed is True


def test_closed_readability_is_terminal() -> None:
    client_socket, server_socket = socket.socketpair()
    wrapped = SocketPairClient(client_socket)
    wrapped.close()
    try:
        stream = ph._PinnedNetworkStream(
            wrapped,
            policy=_policy(),
            budget=ph.DeadlineBudget.start(1.0),
        )
        assert stream.get_extra_info("is_readable") is True
    finally:
        server_socket.close()


@pytest.mark.parametrize(
    "fileno_value",
    [ValueError("closed descriptor"), -1],
    ids=["raises-value-error", "returns-negative-one"],
)
def test_closed_readability_is_terminal_for_invalid_fileno(
    fileno_value: ValueError | int,
) -> None:
    class InvalidFilenoSocket:
        def fileno(self) -> int:
            if isinstance(fileno_value, ValueError):
                raise fileno_value
            return fileno_value

    stream = ph._PinnedNetworkStream(
        InvalidFilenoSocket(),
        policy=_policy(),
        budget=ph.DeadlineBudget.start(1.0),
    )

    assert stream.get_extra_info("is_readable") is True


@pytest.mark.parametrize(
    ("response_chunks", "policy", "expected_content", "expected_error"),
    [
        (
            _fixed_http_response(b"x" * 16),
            _policy(
                max_encoded_bytes=16,
                max_decoded_bytes=16,
                accepted_encodings=("identity",),
            ),
            b"x" * 16,
            None,
        ),
        (
            _fixed_http_response(b"x" * 17),
            _policy(
                max_encoded_bytes=16,
                max_decoded_bytes=32,
                accepted_encodings=("identity",),
            ),
            None,
            ph.PinnedBodyLimitError,
        ),
        (
            _fixed_http_response(
                gzip.compress(b"x" * 16),
                headers=(b"Content-Encoding: gzip",),
            ),
            _policy(
                max_encoded_bytes=64,
                max_decoded_bytes=16,
                accepted_encodings=("gzip",),
            ),
            b"x" * 16,
            None,
        ),
        (
            _fixed_http_response(
                gzip.compress(b"x" * 17),
                headers=(b"Content-Encoding: gzip",),
            ),
            _policy(
                max_encoded_bytes=64,
                max_decoded_bytes=16,
                accepted_encodings=("gzip",),
            ),
            None,
            ph.PinnedBodyLimitError,
        ),
        (
            _fixed_http_response(
                b"not gzip",
                headers=(b"Content-Encoding: gzip",),
            ),
            _policy(accepted_encodings=("gzip",)),
            None,
            ph.PinnedContentEncodingError,
        ),
        (
            _fixed_http_response(
                gzip.compress(b"truncated")[:-1],
                headers=(b"Content-Encoding: gzip",),
            ),
            _policy(accepted_encodings=("gzip",)),
            None,
            ph.PinnedContentEncodingError,
        ),
        (
            _fixed_http_response(
                b"body",
                headers=(b"Content-Encoding: br",),
            ),
            _policy(accepted_encodings=("identity",)),
            None,
            ph.PinnedContentEncodingError,
        ),
        (
            _fixed_http_response(
                gzip.compress(b"body"),
                headers=(b"Content-Encoding: gzip, identity",),
            ),
            _policy(accepted_encodings=("gzip", "identity")),
            None,
            ph.PinnedContentEncodingError,
        ),
        (
            (
                b"HTTP/1.1 200 OK\r\n"
                b"Content-Length: 1\r\n"
                b"Transfer-Encoding: chunked\r\n\r\n"
                b"11\r\n"
                + b"x" * 17
                + b"\r\n0\r\n\r\n",
            ),
            _policy(
                max_encoded_bytes=16,
                max_decoded_bytes=32,
                accepted_encodings=("identity",),
            ),
            None,
            ph.PinnedBodyLimitError,
        ),
    ],
    ids=[
        "identity-exact-cap",
        "identity-cap-plus-one",
        "gzip-exact-decoded-cap",
        "gzip-decoded-cap-plus-one",
        "malformed-gzip",
        "truncated-gzip",
        "unsupported-br",
        "stacked-gzip-identity",
        "false-small-content-length",
    ],
)
def test_real_httpcore_body_and_encoding_boundaries(
    response_chunks: tuple[bytes, ...],
    policy: ph.EgressPolicy,
    expected_content: bytes | None,
    expected_error: type[ph.PinnedHTTPError] | None,
) -> None:
    harness = _real_transport_client(response_chunks)
    result: ph.PinnedResponse | None = None
    try:
        if expected_error is None:
            result = harness.client.get(
                "http://example.com/body",
                user_agent="test-agent",
                policy=policy,
                audit_context="test",
            )
        else:
            with pytest.raises(expected_error) as exc_info:
                harness.client.get(
                    "http://example.com/body",
                    user_agent="test-agent",
                    policy=policy,
                    audit_context="test",
                )
    finally:
        transport_closed = harness.cleanup()

    assert transport_closed is True
    if expected_error is None:
        assert result is not None
        assert result.content == expected_content
    else:
        assert type(exc_info.value) is expected_error
    assert harness.wrapped.closed is True


def test_real_httpcore_total_deadline_expires_while_response_is_withheld() -> None:
    response_gate = threading.Event()
    harness = _real_transport_client(
        _fixed_http_response(b"late"),
        response_gate=response_gate,
    )
    try:
        with pytest.raises(ph.PinnedDeadlineExceeded) as exc_info:
            harness.client.get(
                "http://example.com/slow",
                user_agent="test-agent",
                policy=_policy(
                    accepted_encodings=("identity",),
                    inactivity_timeout_seconds=2.0,
                    total_timeout_seconds=1.0,
                ),
                audit_context="test",
            )
    finally:
        transport_closed = harness.cleanup()

    assert transport_closed is True
    assert type(exc_info.value) is ph.PinnedDeadlineExceeded
    assert harness.received[0].startswith(b"GET /slow HTTP/1.1\r\n")
    assert harness.wrapped.closed is True


class _ChunkStream(httpx.SyncByteStream):
    def __init__(self, chunks: list[bytes]) -> None:
        self.chunks = chunks
        self.iterated = False
        self.closed = False

    def __iter__(self):
        self.iterated = True
        yield from self.chunks

    def close(self) -> None:
        self.closed = True


def _client_for_raw_response(
    body: bytes,
    *,
    headers: tuple[tuple[str, str], ...] = (),
    chunks: list[bytes] | None = None,
) -> ph.PinnedHTTPClient:
    def resolver(host: str, port: int, budget: ph.DeadlineBudget):
        return _public_resolver(host, port, budget)

    def factory(_hop, _policy, _budget):
        raw_stream = _ChunkStream(chunks if chunks is not None else [body])

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                headers=headers,
                stream=raw_stream,
                request=request,
            )

        return httpx.MockTransport(handler)

    return ph.PinnedHTTPClient(resolver=resolver, transport_factory=factory)


def _client_for_redirect_stream(stream: _ChunkStream) -> ph.PinnedHTTPClient:
    def resolver(host: str, port: int, budget: ph.DeadlineBudget):
        return _public_resolver(host, port, budget)

    calls = 0

    def factory(_hop, _policy, _budget):
        nonlocal calls
        calls += 1

        def handler(request: httpx.Request) -> httpx.Response:
            if calls == 1:
                return httpx.Response(
                    302,
                    headers=(("location", "https://example.com/final"),),
                    stream=stream,
                    request=request,
                )
            return httpx.Response(
                200,
                stream=_ChunkStream([b"final"]),
                request=request,
            )

        return httpx.MockTransport(handler)

    return ph.PinnedHTTPClient(resolver=resolver, transport_factory=factory)


@pytest.mark.parametrize(
    "overrides",
    [
        {"max_encoded_bytes": 0},
        {"max_decoded_bytes": 0},
        {"inactivity_timeout_seconds": 0},
        {"total_timeout_seconds": 0},
        {"max_redirects": -1},
        {"accepted_encodings": ()},
        {"accepted_encodings": ("gzip", "gzip")},
        {"accepted_encodings": ("br",)},
        {"accepted_encodings": ("GZIP",)},
    ],
)
def test_egress_policy_rejects_invalid_limits(overrides: dict) -> None:
    values = {
        "max_encoded_bytes": 1024,
        "max_decoded_bytes": 2048,
        "accepted_encodings": ("gzip", "identity"),
        "inactivity_timeout_seconds": 2.0,
        "total_timeout_seconds": 5.0,
        "max_redirects": 5,
    }
    values.update(overrides)
    with pytest.raises(ValueError):
        ph.EgressPolicy(**values)


def test_pinned_client_public_get_requires_audit_context() -> None:
    parameters = inspect.signature(ph.PinnedHTTPClient.get).parameters
    assert list(parameters) == ["self", "url", "user_agent", "policy", "audit_context"]
    assert parameters["user_agent"].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters["policy"].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters["policy"].default is inspect.Parameter.empty
    assert parameters["audit_context"].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters["audit_context"].default is inspect.Parameter.empty


def test_security_denial_logs_sanitized_blocked_address_once(
    caplog: pytest.LogCaptureFixture,
) -> None:
    def resolver(_host: str, _port: int, _budget: ph.DeadlineBudget):
        raise ph.BlockedAddressError("private address: 127.0.0.1")

    client = ph.PinnedHTTPClient(resolver=resolver)
    with caplog.at_level(logging.WARNING, logger="security.egress"):
        with pytest.raises(ph.BlockedAddressError):
            client.get(
                "https://public.example/private?token=secret#fragment",
                user_agent="test-agent",
                policy=_policy(),
                audit_context="Quality / Burst",
            )

    records = [record for record in caplog.records if record.name == "security.egress"]
    assert len(records) == 1
    record = records[0]
    assert record.name == "security.egress"
    assert record.levelno == logging.WARNING
    message = record.getMessage()
    assert message == (
        "Pinned egress denied consumer=quality_burst reason=blocked_address "
        "target=https://public.example:443 hop=0"
    )
    assert "/private" not in message
    assert "token" not in message
    assert "fragment" not in message
    assert "private address" not in message


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Admin Image/Review", "admin_image_review"),
        ("x" * 100, "x" * 64),
        ("!!!", "unknown"),
    ],
)
def test_audit_context_sanitization(raw: str, expected: str) -> None:
    assert ph._sanitize_audit_context(raw) == expected


def test_safe_origin_formats_ascii_ipv6_and_effective_port() -> None:
    assert ph._safe_origin("https://[2001:db8::1]/path?secret=1") == "https://[2001:db8::1]:443"
    assert ph._safe_origin("https://user:pass@example.com/private") == "https://example.com:443"
    assert ph._safe_origin("not a url") == "<invalid>"


def test_peer_mismatch_logs_one_security_denial(
    caplog: pytest.LogCaptureFixture,
) -> None:
    def factory(_hop, _policy, _budget):
        raise ph.PeerMismatchError("peer secret text")

    client = ph.PinnedHTTPClient(resolver=_public_resolver, transport_factory=factory)
    with caplog.at_level(logging.WARNING, logger="security.egress"):
        with pytest.raises(ph.PeerMismatchError):
            client.get(
                "https://peer.example/path?token=secret",
                user_agent="test-agent",
                policy=_policy(),
                audit_context="test",
            )
    records = [record for record in caplog.records if record.name == "security.egress"]
    assert len(records) == 1
    assert records[0].getMessage() == (
        "Pinned egress denied consumer=test reason=peer_mismatch "
        "target=https://peer.example:443 hop=0"
    )


def test_redirect_policy_logs_accepted_redirect_hop(
    caplog: pytest.LogCaptureFixture,
) -> None:
    def factory(hop, _policy, _budget):
        def handler(request: httpx.Request) -> httpx.Response:
            if hop.url.host == "one.example":
                return httpx.Response(302, headers={"location": "https://two.example/next"}, request=request)
            return httpx.Response(302, headers={"location": "https://three.example/final"}, request=request)

        return httpx.MockTransport(handler)

    client = ph.PinnedHTTPClient(resolver=_public_resolver, transport_factory=factory)
    with caplog.at_level(logging.WARNING, logger="security.egress"):
        with pytest.raises(ph.RedirectPolicyError):
            client.get(
                "https://one.example/start",
                user_agent="test-agent",
                policy=_policy(max_redirects=1),
                audit_context="test",
            )
    records = [record for record in caplog.records if record.name == "security.egress"]
    assert len(records) == 1
    assert records[0].getMessage() == (
        "Pinned egress denied consumer=test reason=redirect_policy "
        "target=https://two.example:443 hop=1"
    )


@pytest.mark.parametrize(
    "error",
    [
        ph.PinnedBodyLimitError("body secret"),
        ph.PinnedContentEncodingError("encoding secret"),
        ph.PinnedDeadlineExceeded("deadline secret"),
        ph.ResolverSaturatedError("saturation secret"),
        ph.PinnedTransportError("transport secret"),
    ],
)
def test_non_security_failures_do_not_emit_security_denial(
    caplog: pytest.LogCaptureFixture,
    error: Exception,
) -> None:
    def resolver(_host: str, _port: int, _budget: ph.DeadlineBudget):
        raise error

    client = ph.PinnedHTTPClient(resolver=resolver)
    with caplog.at_level(logging.WARNING, logger="security.egress"):
        with pytest.raises(type(error)):
            client.get(
                "https://example.com/a",
                user_agent="test-agent",
                policy=_policy(),
                audit_context="test",
            )
    assert caplog.records == []


def test_identity_body_accepts_exact_encoded_and_decoded_boundaries() -> None:
    body = b"x" * 1024
    result = _client_for_raw_response(body).get(
        "https://example.com/a",
        user_agent="test",
        policy=_policy(max_encoded_bytes=1024, max_decoded_bytes=1024),
        audit_context="test",
    )
    assert result.content == body


def test_identity_body_rejects_encoded_boundary_plus_one() -> None:
    with pytest.raises(ph.PinnedBodyLimitError):
        _client_for_raw_response(b"x" * 1025).get(
            "https://example.com/a",
            user_agent="test",
            policy=_policy(max_encoded_bytes=1024),
            audit_context="test",
        )


@pytest.mark.parametrize(
    "headers",
    [
        (("content-encoding", "br"),),
        (("content-encoding", "deflate"),),
        (("content-encoding", "gzip, identity"),),
        (("content-encoding", "gzip,,identity"),),
    ],
)
def test_unsupported_or_stacked_content_encoding_is_rejected(headers) -> None:
    with pytest.raises(ph.PinnedContentEncodingError):
        _client_for_raw_response(b"body", headers=headers).get(
            "https://example.com/a",
            user_agent="test",
            policy=_policy(),
            audit_context="test",
        )


def test_false_small_content_length_cannot_bypass_actual_encoded_limit() -> None:
    with pytest.raises(ph.PinnedBodyLimitError):
        _client_for_raw_response(
            b"x" * 1025,
            headers=(("content-length", "1"),),
        ).get(
            "https://example.com/a",
            user_agent="test",
            policy=_policy(max_encoded_bytes=1024),
            audit_context="test",
        )


def test_content_length_over_encoded_limit_is_rejected_early() -> None:
    with pytest.raises(ph.PinnedBodyLimitError):
        _client_for_raw_response(
            b"x",
            headers=(("content-length", "1025"),),
        ).get(
            "https://example.com/a",
            user_agent="test",
            policy=_policy(max_encoded_bytes=1024),
            audit_context="test",
        )


def test_buffered_response_still_enforces_encoded_limit() -> None:
    response = httpx.Response(
        200,
        stream=httpx.ByteStream(b"x" * 1025),
        request=httpx.Request("GET", "https://example.com/a"),
    )
    response.read()

    with pytest.raises(ph.PinnedBodyLimitError):
        ph._read_bounded_body(
            response,
            policy=_policy(max_encoded_bytes=1024),
            budget=ph.DeadlineBudget(expires_at=10.0),
            monotonic=lambda: 1.0,
        )


def test_final_response_headers_and_accept_encoding_are_preserved() -> None:
    seen: list[str] = []

    def factory(_hop, _policy, _budget):
        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request.headers["accept-encoding"])
            return httpx.Response(
                200,
                headers=(("x-original", "kept"), ("x-original", "duplicate")),
                stream=_ChunkStream([b"body"]),
                request=request,
            )

        return httpx.MockTransport(handler)

    result = ph.PinnedHTTPClient(
        resolver=_public_resolver,
        transport_factory=factory,
    ).get(
        "https://example.com/a",
        user_agent="test",
        policy=_policy(accepted_encodings=("gzip", "identity")),
        audit_context="test",
    )
    assert result.headers == (("x-original", "kept"), ("x-original", "duplicate"))
    assert seen == ["gzip, identity"]


def test_redirect_body_is_closed_without_iteration() -> None:
    stream = _ChunkStream([b"redirect body must not be read"])
    client = _client_for_redirect_stream(stream)
    result = client.get(
        "https://example.com/a",
        user_agent="test",
        policy=_policy(max_redirects=1),
        audit_context="test",
    )
    assert result.url == "https://example.com/final"
    assert stream.closed is True
    assert stream.iterated is False


def test_same_url_redirect_with_set_cookie_replays_cookie() -> None:
    seen: list[tuple[str, str | None]] = []

    def factory(
        _hop: ph.ResolvedHop,
        _policy: ph.EgressPolicy,
        _budget: ph.DeadlineBudget,
    ) -> httpx.BaseTransport:
        def handler(request: httpx.Request) -> httpx.Response:
            seen.append((str(request.url), request.headers.get("cookie")))
            if len(seen) == 1:
                return httpx.Response(
                    302,
                    headers=(
                        ("location", "/p"),
                        ("set-cookie", "consent=yes; Path=/"),
                    ),
                    request=request,
                )
            return httpx.Response(
                200,
                stream=_ChunkStream([b"ok"]),
                request=request,
            )

        return httpx.MockTransport(handler)

    result = ph.PinnedHTTPClient(
        resolver=_public_resolver,
        transport_factory=factory,
    ).get(
        "https://example.com/p",
        user_agent="ua/1",
        policy=_policy(),
        audit_context="test",
    )

    assert result.content == b"ok"
    assert seen == [
        ("https://example.com/p", None),
        ("https://example.com/p", "consent=yes"),
    ]


def test_same_url_redirect_without_cookie_is_rejected() -> None:
    seen: list[str] = []

    def factory(
        _hop: ph.ResolvedHop,
        _policy: ph.EgressPolicy,
        _budget: ph.DeadlineBudget,
    ) -> httpx.BaseTransport:
        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(str(request.url))
            return httpx.Response(
                302,
                headers={"location": "/p"},
                request=request,
            )

        return httpx.MockTransport(handler)

    with pytest.raises(ph.RedirectPolicyError):
        ph.PinnedHTTPClient(
            resolver=_public_resolver,
            transport_factory=factory,
        ).get(
            "https://example.com/p",
            user_agent="ua/1",
            policy=_policy(),
            audit_context="test",
        )

    assert seen == ["https://example.com/p"]


def test_cookie_is_not_sent_to_incompatible_origin_or_scheme() -> None:
    seen: list[tuple[str, str | None]] = []

    def factory(
        _hop: ph.ResolvedHop,
        _policy: ph.EgressPolicy,
        _budget: ph.DeadlineBudget,
    ) -> httpx.BaseTransport:
        def handler(request: httpx.Request) -> httpx.Response:
            seen.append((str(request.url), request.headers.get("cookie")))
            if len(seen) == 1:
                return httpx.Response(
                    302,
                    headers=(
                        ("location", "http://example.com/p"),
                        ("set-cookie", "consent=yes; Secure; Path=/"),
                    ),
                    request=request,
                )
            return httpx.Response(
                200,
                stream=_ChunkStream([b"ok"]),
                request=request,
            )

        return httpx.MockTransport(handler)

    result = ph.PinnedHTTPClient(
        resolver=_public_resolver,
        transport_factory=factory,
    ).get(
        "https://example.com/p",
        user_agent="ua/1",
        policy=_policy(),
        audit_context="test",
    )

    assert result.content == b"ok"
    assert seen == [
        ("https://example.com/p", None),
        ("http://example.com/p", None),
    ]


def test_pinned_cookie_jar_enforces_domain_path_and_count_bounds() -> None:
    jar = ph._PinnedCookieJar()
    source = httpx.URL("https://sub.example.com/section/page")
    jar.update(
        source,
        (
            ("set-cookie", "scoped=yes; Domain=example.com; Path=/section"),
            ("set-cookie", "too-large=" + ("x" * 1025)),
        ),
    )
    for index in range(17):
        jar.update(source, (("set-cookie", f"c{index}=v; Path=/"),))

    path_cookies = "; ".join(
        f"c{index}=v" for index in sorted(range(15), key=lambda item: f"c{item}")
    )
    assert jar.header_for(httpx.URL("https://sub.example.com/section/next")) == (
        "scoped=yes; " + path_cookies
    )
    assert jar.header_for(httpx.URL("https://sub.example.com/other")) == path_cookies
    assert jar.header_for(httpx.URL("https://other.test/section/next")) is None


def test_pinned_cookie_jar_honors_max_age_deletion() -> None:
    jar = ph._PinnedCookieJar()
    url = httpx.URL("https://example.com/p")
    jar.update(url, (("set-cookie", "consent=yes; Path=/"),))
    jar.update(url, (("set-cookie", "consent=; Max-Age=0; Path=/"),))

    assert jar.header_for(url) is None


def test_gzip_body_accepts_split_chunks() -> None:
    decoded = b"gzip body"
    encoded = gzip.compress(decoded)
    midpoint = len(encoded) // 2
    result = _client_for_raw_response(
        encoded,
        headers=(("content-encoding", "gzip"),),
        chunks=[encoded[:midpoint], encoded[midpoint:]],
    ).get("https://example.com/a", user_agent="test", policy=_policy(), audit_context="test")
    assert result.content == decoded


@pytest.mark.parametrize(
    "encoded",
    [
        b"not gzip",
        gzip.compress(b"truncated")[:-1],
        gzip.compress(b"trailing") + b"tail",
        gzip.compress(b"first") + gzip.compress(b"second"),
    ],
)
def test_gzip_rejects_malformed_truncated_trailing_or_concatenated(encoded: bytes) -> None:
    with pytest.raises(ph.PinnedContentEncodingError):
        _client_for_raw_response(
            encoded,
            headers=(("content-encoding", "gzip"),),
        ).get("https://example.com/a", user_agent="test", policy=_policy(), audit_context="test")


def test_gzip_body_rejects_decoded_boundary_plus_one() -> None:
    encoded = gzip.compress(b"x" * 1025)
    with pytest.raises(ph.PinnedBodyLimitError):
        _client_for_raw_response(
            encoded,
            headers=(("content-encoding", "gzip"),),
        ).get(
            "https://example.com/a",
            user_agent="test",
            policy=_policy(max_encoded_bytes=len(encoded), max_decoded_bytes=1024),
            audit_context="test",
        )


def test_gzip_bomb_allocation_is_policy_relative() -> None:
    import tracemalloc

    decoded_size = 32 * 1024 * 1024
    decoded_cap = 1024 * 1024
    encoded = gzip.compress(b"A" * decoded_size, compresslevel=9)
    client = _client_for_raw_response(
        encoded,
        headers=(("content-encoding", "gzip"),),
    )

    tracemalloc.start()
    try:
        with pytest.raises(ph.PinnedBodyLimitError):
            client.get(
                "https://example.com/bomb",
                user_agent="test",
                policy=_policy(
                    max_encoded_bytes=len(encoded),
                    max_decoded_bytes=decoded_cap,
                ),
                audit_context="test",
            )
        _current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    assert peak <= 8 * decoded_cap


def test_decode_stops_when_total_deadline_expires() -> None:
    response = httpx.Response(
        200,
        stream=_ChunkStream([b"a", b"b"]),
        request=httpx.Request("GET", "https://example.com/a"),
    )
    times = iter([1.0, 6.0])

    with pytest.raises(ph.PinnedDeadlineExceeded):
        ph._read_bounded_body(
            response,
            policy=_policy(),
            budget=ph.DeadlineBudget(expires_at=5.0),
            monotonic=lambda: next(times),
        )


def test_client_returns_immutable_decoded_response_and_user_agent() -> None:
    seen: list[tuple[str, str]] = []

    def factory(
        hop: ph.ResolvedHop,
        _policy: ph.EgressPolicy,
        _budget: ph.DeadlineBudget,
    ) -> httpx.BaseTransport:
        def handler(request: httpx.Request) -> httpx.Response:
            seen.append((request.headers["host"], request.headers["user-agent"]))
            return httpx.Response(
                200,
                headers={"content-type": "text/plain; charset=utf-8"},
                stream=_ChunkStream([b"xin chao"]),
            )
        return httpx.MockTransport(handler)

    client = ph.PinnedHTTPClient(resolver=_public_resolver, transport_factory=factory)
    result = client.get(
        "https://example.com/a",
        user_agent="ua/1",
        policy=_policy(inactivity_timeout_seconds=3.0, total_timeout_seconds=3.0),
        audit_context="test",
    )
    assert result.status_code == 200
    assert result.content == b"xin chao"
    assert seen == [("example.com", "ua/1")]


def test_redirect_re_resolves_every_hop_and_blocks_private_target() -> None:
    calls: list[tuple[str, int]] = []
    budgets: list[ph.DeadlineBudget] = []

    def resolver(
        host: str,
        port: int,
        budget: ph.DeadlineBudget,
    ) -> tuple[ph.ResolvedAddress, ...]:
        calls.append((host, port))
        budgets.append(budget)
        if host == "internal.example":
            raise ph.BlockedAddressError("mixed or private destination")
        return _public_resolver(host, port, budget)

    def factory(
        hop: ph.ResolvedHop,
        _policy: ph.EgressPolicy,
        _budget: ph.DeadlineBudget,
    ) -> httpx.BaseTransport:
        return httpx.MockTransport(
            lambda _request: httpx.Response(302, headers={"location": "https://internal.example/secret"})
        )

    client = ph.PinnedHTTPClient(resolver=resolver, transport_factory=factory)
    with pytest.raises(ph.BlockedAddressError):
        client.get(
            "https://public.example/start",
            user_agent="ua/1",
            policy=_policy(),
            audit_context="test",
        )
    assert calls == [("public.example", 443), ("internal.example", 443)]
    assert budgets[0] is budgets[1]


def test_redirects_reuse_one_deadline_budget() -> None:
    budgets: list[ph.DeadlineBudget] = []

    def resolver(host: str, port: int, budget: ph.DeadlineBudget):
        budgets.append(budget)
        return _public_resolver(host, port, budget)

    def factory(hop, policy, budget):
        budgets.append(budget)

        def handler(request: httpx.Request) -> httpx.Response:
            if hop.host == "one.example":
                return httpx.Response(
                    302,
                    headers=(("location", "https://two.example/final"),),
                    request=request,
                )
            return httpx.Response(200, content=b"done", request=request)

        return httpx.MockTransport(handler)

    ph.PinnedHTTPClient(resolver=resolver, transport_factory=factory).get(
        "https://one.example/start",
        user_agent="test",
        policy=_policy(max_redirects=2),
        audit_context="test",
    )

    assert len({id(item) for item in budgets}) == 1


def test_one_deadline_budget_reaches_transport_backend_stream_and_decode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    budgets: dict[str, ph.DeadlineBudget] = {}
    original_read = ph._read_bounded_body

    def read_bounded_body(
        response: httpx.Response,
        *,
        policy: ph.EgressPolicy,
        budget: ph.DeadlineBudget,
        monotonic=ph.time.monotonic,
    ) -> bytes:
        budgets["decode"] = budget
        return original_read(response, policy=policy, budget=budget, monotonic=monotonic)

    monkeypatch.setattr(ph, "_read_bounded_body", read_bounded_body)

    def resolver(host: str, port: int, budget: ph.DeadlineBudget):
        budgets["resolver"] = budget
        return _public_resolver(host, port, budget)

    def factory(
        hop: ph.ResolvedHop,
        policy: ph.EgressPolicy,
        budget: ph.DeadlineBudget,
    ) -> httpx.BaseTransport:
        budgets["factory"] = budget
        fake = FakeSocket(hop.addresses[0].sockaddr)
        transport = ph._PinnedHTTPTransport(
            hop,
            policy=policy,
            budget=budget,
            socket_factory=lambda *_args: fake,
            monotonic=lambda: 1.0,
        )
        backend = transport._pool._network_backend
        budgets["backend"] = backend._budget
        stream = backend.connect_tcp(hop.host, hop.port, timeout=5.0)
        budgets["stream"] = stream._budget
        stream.close()
        transport.close()

        return httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                stream=_ChunkStream([b"done"]),
                request=request,
            )
        )

    result = ph.PinnedHTTPClient(
        resolver=resolver,
        transport_factory=factory,
    ).get(
        "https://one.example/start",
        user_agent="test",
        policy=_policy(),
        audit_context="test",
    )

    assert result.content == b"done"
    assert {id(item) for item in budgets.values()} == {id(budgets["resolver"])}


def test_redirect_processing_stops_on_original_deadline() -> None:
    resolved: list[str] = []
    times = iter([0.0, 1.0, 2.0, 6.0])

    def resolver(host: str, port: int, budget: ph.DeadlineBudget):
        resolved.append(host)
        return _public_resolver(host, port, budget)

    def factory(_hop, _policy, _budget):
        return httpx.MockTransport(
            lambda request: httpx.Response(
                302,
                headers=(("location", "https://two.example/final"),),
                request=request,
            )
        )

    client = ph.PinnedHTTPClient(
        resolver=resolver,
        transport_factory=factory,
        monotonic=lambda: next(times),
    )

    with pytest.raises(ph.PinnedDeadlineExceeded):
        client.get(
            "https://one.example/start",
            user_agent="test",
            policy=_policy(total_timeout_seconds=5.0),
            audit_context="test",
        )

    assert resolved == ["one.example"]


@pytest.mark.parametrize("ip", _BLOCKED_IPS)
def test_redirect_to_blocked_literal_is_rejected(ip: str) -> None:
    target = f"https://[{ip}]/secret" if ":" in ip else f"https://{ip}/secret"

    def factory(
        hop: ph.ResolvedHop,
        _policy: ph.EgressPolicy,
        _budget: ph.DeadlineBudget,
    ) -> httpx.BaseTransport:
        return httpx.MockTransport(
            lambda _request: httpx.Response(302, headers={"location": target})
        )

    client = ph.PinnedHTTPClient(
        resolver=ph.resolve_public_addresses,
        transport_factory=factory,
    )
    with pytest.raises(ph.BlockedAddressError):
        client.get(
            "https://93.184.216.34/start",
            user_agent="ua/1",
            policy=_policy(),
            audit_context="test",
        )


def test_redirect_to_mixed_dns_answer_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def getaddrinfo(host: str, *_args, **_kwargs):
        calls.append(host)
        if host == "mixed.example":
            return [_answer("93.184.216.34"), _answer("127.0.0.1")]
        return [_answer("93.184.216.34")]

    monkeypatch.setattr(ph.socket, "getaddrinfo", getaddrinfo)

    def factory(
        _hop: ph.ResolvedHop,
        _policy: ph.EgressPolicy,
        _budget: ph.DeadlineBudget,
    ) -> httpx.BaseTransport:
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
        client.get(
            "https://public.example/start",
            user_agent="ua/1",
            policy=_policy(),
            audit_context="test",
        )
    assert calls == ["public.example", "mixed.example"]


def test_five_redirects_allowed_sixth_rejected() -> None:
    visited: list[str] = []

    def factory(
        hop: ph.ResolvedHop,
        _policy: ph.EgressPolicy,
        _budget: ph.DeadlineBudget,
    ) -> httpx.BaseTransport:
        def handler(_request: httpx.Request) -> httpx.Response:
            visited.append(str(hop.url))
            index = int(hop.url.path.rsplit("/", 1)[-1])
            if index < 6:
                return httpx.Response(302, headers={"location": f"/{index + 1}"})
            return httpx.Response(200, stream=_ChunkStream([b"done"]))
        return httpx.MockTransport(handler)

    client = ph.PinnedHTTPClient(resolver=_public_resolver, transport_factory=factory)
    with pytest.raises(ph.RedirectPolicyError):
        client.get(
            "https://example.com/0",
            user_agent="ua/1",
            policy=_policy(max_redirects=5),
            audit_context="test",
        )
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
    def factory(
        hop: ph.ResolvedHop,
        _policy: ph.EgressPolicy,
        _budget: ph.DeadlineBudget,
    ) -> httpx.BaseTransport:
        def handler(_request: httpx.Request) -> httpx.Response:
            if hop.url.path == "/start":
                return httpx.Response(302, headers={"location": location})
            return httpx.Response(200, stream=_ChunkStream([b"done"]))

        return httpx.MockTransport(handler)

    result = ph.PinnedHTTPClient(
        resolver=_public_resolver,
        transport_factory=factory,
    ).get(start, user_agent="ua/1", policy=_policy(), audit_context="test")
    assert result.url == expected
    assert len(result.redirects) == 1


@pytest.mark.parametrize(
    ("status", "location"),
    [(302, ""), (302, "   "), (300, "/next"), (304, "/next")],
)
def test_blank_or_nonstandard_redirect_is_final(status: int, location: str) -> None:
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(
            status,
            headers={"location": location},
            stream=_ChunkStream([b""]),
        )
    )
    client = ph.PinnedHTTPClient(
        resolver=_public_resolver,
        transport_factory=lambda _hop, _policy, _budget: transport,
    )
    result = client.get(
        "https://example.com/a",
        user_agent="ua/1",
        policy=_policy(),
        audit_context="test",
    )
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
        transport_factory=lambda _hop, _policy, _budget: transport,
    )
    with pytest.raises(ph.RedirectPolicyError):
        client.get(
            "https://example.com/a#initial",
            user_agent="ua/1",
            policy=_policy(),
            audit_context="test",
        )


def test_unicode_and_ascii_idna_redirect_loop_is_rejected() -> None:
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(
            302,
            headers={"location": "https://xn--bcher-kva.example/a"},
        )
    )
    client = ph.PinnedHTTPClient(
        resolver=_public_resolver,
        transport_factory=lambda _hop, _policy, _budget: transport,
    )
    with pytest.raises(ph.RedirectPolicyError):
        client.get(
            "https://BÜCHER.example/a",
            user_agent="ua/1",
            policy=_policy(),
            audit_context="test",
        )


def test_malformed_redirect_target_is_translated() -> None:
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(302, headers={"location": "http://[::1"})
    )
    client = ph.PinnedHTTPClient(
        resolver=_public_resolver,
        transport_factory=lambda _hop, _policy, _budget: transport,
    )
    with pytest.raises(ph.RedirectPolicyError):
        client.get(
            "https://example.com/a",
            user_agent="ua/1",
            policy=_policy(),
            audit_context="test",
        )


def test_percent_encoded_and_literal_paths_are_distinct() -> None:
    def factory(
        hop: ph.ResolvedHop,
        _policy: ph.EgressPolicy,
        _budget: ph.DeadlineBudget,
    ) -> httpx.BaseTransport:
        if hop.url.raw_path == b"/a%2Fb":
            response = httpx.Response(302, headers={"location": "/a/b"})
        else:
            response = httpx.Response(200, stream=_ChunkStream([b"done"]))
        return httpx.MockTransport(lambda _request: response)

    result = ph.PinnedHTTPClient(
        resolver=_public_resolver,
        transport_factory=factory,
    ).get(
        "https://example.com/a%2Fb",
        user_agent="ua/1",
        policy=_policy(),
        audit_context="test",
    )
    assert result.url == "https://example.com/a/b"
    assert len(result.redirects) == 1


def test_each_redirect_hop_resolves_once_and_gets_a_fresh_transport() -> None:
    resolutions: list[tuple[str, int]] = []
    transports: list[str] = []

    def resolver(
        host: str,
        port: int,
        budget: ph.DeadlineBudget,
    ) -> tuple[ph.ResolvedAddress, ...]:
        resolutions.append((host, port))
        return _public_resolver(host, port, budget)

    def factory(
        hop: ph.ResolvedHop,
        _policy: ph.EgressPolicy,
        _budget: ph.DeadlineBudget,
    ) -> httpx.BaseTransport:
        transports.append(str(hop.url))
        if hop.host == "a.example":
            response = httpx.Response(
                302,
                headers={"location": "https://b.example/final"},
            )
        else:
            response = httpx.Response(200, stream=_ChunkStream([b"done"]))
        return httpx.MockTransport(lambda _request: response)

    result = ph.PinnedHTTPClient(
        resolver=resolver,
        transport_factory=factory,
    ).get(
        "https://a.example/start",
        user_agent="ua/1",
        policy=_policy(),
        audit_context="test",
    )
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

    def factory(
        _hop: ph.ResolvedHop,
        _policy: ph.EgressPolicy,
        _budget: ph.DeadlineBudget,
    ) -> httpx.BaseTransport:
        def handler(request: httpx.Request) -> httpx.Response:
            handled.append(str(request.url))
            return httpx.Response(200, stream=_ChunkStream([b"direct"]))

        return httpx.MockTransport(handler)

    result = ph.PinnedHTTPClient(
        resolver=_public_resolver,
        transport_factory=factory,
    ).get(
        "https://example.com/a",
        user_agent="ua/1",
        policy=_policy(),
        audit_context="test",
    )
    assert result.content == b"direct"
    assert handled == ["https://example.com/a"]


def test_client_translates_transport_factory_failure() -> None:
    def factory(
        _hop: ph.ResolvedHop,
        _policy: ph.EgressPolicy,
        _budget: ph.DeadlineBudget,
    ) -> httpx.BaseTransport:
        raise OSError("TLS context construction failed")

    client = ph.PinnedHTTPClient(
        resolver=_public_resolver,
        transport_factory=factory,
    )
    with pytest.raises(ph.PinnedTransportError):
        client.get(
            "https://example.com/a",
            user_agent="ua/1",
            policy=_policy(),
            audit_context="test",
        )


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
    def factory(
        _hop: ph.ResolvedHop,
        _policy: ph.EgressPolicy,
        _budget: ph.DeadlineBudget,
    ) -> httpx.BaseTransport:
        def handler(request: httpx.Request) -> httpx.Response:
            raise error_factory(request)

        return httpx.MockTransport(handler)

    client = ph.PinnedHTTPClient(
        resolver=_public_resolver,
        transport_factory=factory,
    )
    with pytest.raises(ph.PinnedTransportError):
        client.get(
            "https://example.com/a",
            user_agent="ua/1",
            policy=_policy(),
            audit_context="test",
        )


class _OneChunkStream(httpx.SyncByteStream):
    def __init__(self, content: bytes) -> None:
        self._content = content
        self.closed = False

    def __iter__(self):
        yield self._content

    def close(self) -> None:
        self.closed = True


def test_shared_layer_decodes_gzip_exactly_once() -> None:
    encoded = gzip.compress("Vĩnh Long".encode("utf-8"))

    def factory(
        _hop: ph.ResolvedHop,
        _policy: ph.EgressPolicy,
        _budget: ph.DeadlineBudget,
    ) -> httpx.BaseTransport:
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
    ).get(
        "https://example.com/a",
        user_agent="ua/1",
        policy=_policy(),
        audit_context="test",
    )
    assert result.content == "Vĩnh Long".encode("utf-8")
    assert result.content != encoded


def test_concurrent_calls_do_not_leak_pinned_hops() -> None:
    observed: list[tuple[str, str]] = []

    def factory(
        hop: ph.ResolvedHop,
        _policy: ph.EgressPolicy,
        _budget: ph.DeadlineBudget,
    ) -> httpx.BaseTransport:
        approved = str(hop.addresses[0].ip)

        def handler(_request: httpx.Request) -> httpx.Response:
            observed.append((hop.host, approved))
            return httpx.Response(200, stream=_ChunkStream([hop.host.encode("ascii")]))

        return httpx.MockTransport(handler)

    client = ph.PinnedHTTPClient(
        resolver=_public_resolver,
        transport_factory=factory,
    )
    hosts = [f"h{index}.example" for index in range(12)]
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(
            executor.map(
                lambda host: client.get(
                    f"https://{host}/",
                    user_agent="ua/1",
                    policy=_policy(),
                    audit_context="test",
                ),
                hosts,
            )
        )
    assert [result.content.decode("ascii") for result in results] == hosts
    assert {host for host, _approved in observed} == set(hosts)
    assert len(observed) == len(hosts)
