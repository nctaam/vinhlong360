# Shared Pinned Outbound HTTP Client Implementation Plan

> STATUS: done - implementation, adversarial correction, bounded follow-up, and final local verification are complete.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route the three mapped outbound GET paths through one DNS-pinned, redirect-safe synchronous client that preserves TLS hostname verification and each consumer's existing response behavior.

**Architecture:** `agent/pinned_http.py` owns URL parsing, public-address policy, exact-sockaddr dialing, peer verification, HTTPX/httpcore transport adaptation, and the manual redirect loop. The existing admin, auto-learn, and quality-burst modules remain thin adapters responsible for HTTP status policy, text decoding, logging, and return values.

**Tech Stack:** Python 3.10+ syntax, `httpx>=0.28,<1`, `httpcore>=1.0.9,<2`, stdlib `socket`/`ssl`/`ipaddress`, FastAPI `HTTPException`, pytest, Ruff, repository hard checks, bounded backend regression runner.

## Global Constraints

- Baseline authority is design commit `0f210a87` on `main`; re-read the approved spec before implementation.
- Add only `agent/pinned_http.py` as the shared egress module. Do not migrate crawler, geocode, realtime, bot, moderation, DDGS internals, OpenAI clients, or other outbound callers.
- Support synchronous GET only. Do not add an async client, generic method/body support, cookie jar, arbitrary request headers, proxy support, or HTTP authentication.
- Accept only absolute `http`/`https` URLs without credentials or zone identifiers.
- Resolve each hop once, reject an empty or mixed public/non-public answer set, and connect only to the exact approved socket addresses.
- Reject non-global IPs and IPv4-mapped, IPv4-compatible, NAT64, 6to4, Teredo, and ISATAP transition forms. The deployment must not route unlisted custom IPv6 translation prefixes.
- Verify the actual peer IP and port before returning the stream to httpcore. Preserve the original hostname for HTTP `Host`, TLS SNI, and certificate validation.
- Use a fresh one-connection HTTP/1.1 pool per hop, `trust_env=False`, no proxy, no keep-alive retention, no HTTP retry, and a maximum of five followed redirects after the initial request.
- Use standard GET redirect statuses `301`, `302`, `303`, `307`, and `308`. Blank `Location` is final; HTTPS-to-HTTP remains allowed but is fully revalidated.
- Preserve eager response buffering. Do not implement streaming body caps, global DNS/request deadlines, content-type enforcement, or bounded decompression in this tranche; those remain Workstream 10.
- Preserve admin's current post-buffer 12 MiB check, auto-learn's exact-200/6,000-character behavior, and quality-burst's `<400`/5,000-character behavior.
- Keep `requests>=2.32`; quality-burst still uses an offline `requests.Response` for legacy charset behavior and keeps the `requests is None` short circuit.
- Every production-file commit must stage a paired test file for R20.7. Keep new functions at cyclomatic complexity 12 or lower by extracting focused helpers.
- No test may perform live DNS, open a real network connection, mutate production data, read secrets, deploy, push, or change a route contract.
- Commit each task separately. Tasks 1-3 are sequential; Tasks 4-6 may run in parallel only in isolated worktrees based on the Task 3 commit, then merge/cherry-pick one at a time.

## File Structure

- Create `agent/pinned_http.py`: immutable contracts, exception hierarchy, resolver/address policy, pinned socket stream/backend, HTTPX transport, manual redirect client, validation-only helper.
- Create `tests/test_pinned_http.py`: offline unit and contract tests for policy, dialing, peer verification, TLS/SNI, redirects, decoding, environment isolation, and thread safety.
- Create `tests/test_admin_pinned_http.py`: admin adapter error/status/size/offload tests.
- Create `tests/test_auto_learn_fetch.py`: auto-learn status, charset, cleanup, logging, and caller-threshold tests.
- Modify `tests/test_gpt55_quality_burst.py`: quality-burst fetch, optional Requests, charset, cleanup, and status tests.
- Create `tests/test_pinned_http_consumers.py`: exact mapped-consumer registry and direct-network-call guard.
- Modify `agent/admin.py`: replace split SSRF preflight/fetch with pinned client and preserve non-fetch URL validation.
- Modify `agent/auto_learn.py`: replace `httpx.get()` and preserve HTTPX text semantics.
- Modify `agent/gpt55_quality_burst.py`: replace `requests.get()` and preserve Requests text semantics.
- Modify `agent/tests/test_p0_security.py`, `agent/tests/test_admin_mutations.py`, `agent/tests/test_gap_fixes.py`, `agent/tests/test_phase16_coverage.py`, and `tests/test_admin_p0_regressions.py`: remove stale `_assert_public_url`/`_fetch_public_url` assumptions and assert the new boundary.
- Modify `requirements.txt`: set `httpx>=0.28,<1`, add `httpcore>=1.0.9,<2`, retain `requests>=2.32`.
- Modify `docs/ROADMAP.md` and `docs/HANDOFF.md` only after all required verification succeeds.

## Execution Waves

1. **Wave A, sequential:** Tasks 1-3 build and verify the shared core.
2. **Wave B, parallel worktrees:** Tasks 4, 5, and 6 consume the frozen Task 3 interface without editing shared files.
3. **Wave C, sequential integration:** Task 7 adds the cross-consumer guard and runs focused integration. Task 8 runs repository gates and truth-syncs docs.

---

### Task 1: Destination Policy, Contracts, and Dependency Bounds

**Files:**
- Create: `agent/pinned_http.py`
- Create: `tests/test_pinned_http.py`
- Modify: `requirements.txt:9-10`

**Interfaces:**
- Consumes: `httpx.URL`, `socket.getaddrinfo`, `ipaddress.ip_address`.
- Produces: `ResolvedAddress`, `ResolvedHop`, `RedirectHop`, `PinnedResponse`, `Resolver`, `TransportFactory`, `PinnedHTTPError`, `DestinationPolicyError`, `InvalidDestinationError`, `ResolutionError`, `BlockedAddressError`, `PeerMismatchError`, `RedirectPolicyError`, `PinnedTransportError`, `resolve_public_addresses()`, `validate_public_url()`, `_ascii_host()`, and `_canonical_url_key()`.

- [ ] **Step 1: Add the failing URL and address-policy tests**

Add these helpers and test groups to `tests/test_pinned_http.py`:

```python
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
```

- [ ] **Step 2: Run the new tests and confirm RED**

Run:

```powershell
python -m pytest tests/test_pinned_http.py -q
```

Expected: collection fails because `pinned_http` does not exist.

- [ ] **Step 3: Add dependency bounds and implement the immutable contracts**

Change `requirements.txt` to:

```text
httpx>=0.28,<1
httpcore>=1.0.9,<2
requests>=2.32
```

In `agent/pinned_http.py`, define the exact public contracts and hierarchy:

```python
from __future__ import annotations

import ipaddress
import select
import socket
import ssl
import time
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Callable, Protocol

import httpcore
import httpx


class PinnedHTTPError(Exception):
    """Base error for the public pinned egress boundary."""


class DestinationPolicyError(PinnedHTTPError):
    """The requested destination cannot be authorized."""


class InvalidDestinationError(DestinationPolicyError):
    pass


class ResolutionError(DestinationPolicyError):
    pass


class BlockedAddressError(DestinationPolicyError):
    pass


class PeerMismatchError(DestinationPolicyError):
    pass


class RedirectPolicyError(PinnedHTTPError):
    pass


class PinnedTransportError(PinnedHTTPError):
    pass


@dataclass(frozen=True)
class ResolvedAddress:
    ip: ipaddress.IPv4Address | ipaddress.IPv6Address
    port: int
    family: int
    socktype: int
    protocol: int
    sockaddr: tuple


@dataclass(frozen=True)
class ResolvedHop:
    url: httpx.URL
    host: str
    port: int
    addresses: tuple[ResolvedAddress, ...]


@dataclass(frozen=True)
class RedirectHop:
    request_url: str
    status_code: int
    location: str
    next_url: str


@dataclass(frozen=True)
class PinnedResponse:
    status_code: int
    url: str
    headers: tuple[tuple[str, str], ...]
    content: bytes
    redirects: tuple[RedirectHop, ...]


class Resolver(Protocol):
    def __call__(self, host: str, port: int) -> tuple[ResolvedAddress, ...]:
        raise NotImplementedError


class TransportFactory(Protocol):
    def __call__(self, hop: ResolvedHop) -> httpx.BaseTransport:
        raise NotImplementedError
```

- [ ] **Step 4: Implement URL parsing, transition-address rejection, resolution, and canonical keys**

Use small helpers with this logic:

```python
_HTTP_PORTS = {"http": 80, "https": 443}
_NAT64_NETWORKS = (
    ipaddress.ip_network("64:ff9b::/96"),
    ipaddress.ip_network("64:ff9b:1::/48"),
)


def _parse_url(url: str) -> httpx.URL:
    try:
        parsed = httpx.URL(url)
    except (TypeError, ValueError, httpx.InvalidURL) as exc:
        raise InvalidDestinationError("invalid URL") from exc
    if parsed.scheme not in _HTTP_PORTS or not parsed.host or not parsed.is_absolute_url:
        raise InvalidDestinationError("only absolute http/https URLs are allowed")
    if parsed.username or parsed.password or "%" in parsed.host:
        raise InvalidDestinationError("credentials and zone identifiers are forbidden")
    try:
        port = parsed.port
    except ValueError as exc:
        raise InvalidDestinationError("invalid port") from exc
    if port is not None and not 1 <= port <= 65535:
        raise InvalidDestinationError("invalid port")
    return parsed.copy_with(fragment=None)


def _is_isatap(address: ipaddress.IPv6Address) -> bool:
    interface_id = int(address) & ((1 << 64) - 1)
    marker = (interface_id >> 32) & 0xFFFFFFFF
    return marker in {0x00005EFE, 0x02005EFE}


def _is_transition_address(address: ipaddress.IPv6Address) -> bool:
    return (
        address.ipv4_mapped is not None
        or address in ipaddress.ip_network("::/96")
        or any(address in network for network in _NAT64_NETWORKS)
        or address.sixtofour is not None
        or address.teredo is not None
        or _is_isatap(address)
    )


def _require_allowed_ip(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> None:
    if isinstance(address, ipaddress.IPv6Address) and _is_transition_address(address):
        raise BlockedAddressError(f"IPv6 transition address denied: {address}")
    if address.is_multicast or address.is_unspecified or not address.is_global:
        raise BlockedAddressError(f"non-global address denied: {address}")


def _ascii_host(url: httpx.URL) -> str:
    return url.raw_host.decode("ascii").lower()


def _canonical_url_key(url: httpx.URL) -> tuple[str, str, int, bytes]:
    port = url.port or _HTTP_PORTS[url.scheme]
    return (url.scheme.lower(), _ascii_host(url), port, url.raw_path)


def _resolved_address(
    family: int,
    socktype: int,
    protocol: int,
    sockaddr: tuple,
) -> ResolvedAddress:
    try:
        address = ipaddress.ip_address(sockaddr[0])
        resolved_port = int(sockaddr[1])
    except (IndexError, TypeError, ValueError) as exc:
        raise ResolutionError("resolver returned a malformed address") from exc
    _require_allowed_ip(address)
    return ResolvedAddress(
        ip=address,
        port=resolved_port,
        family=family,
        socktype=socktype,
        protocol=protocol,
        sockaddr=sockaddr,
    )


def resolve_public_addresses(host: str, port: int) -> tuple[ResolvedAddress, ...]:
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None

    if literal is not None:
        _require_allowed_ip(literal)
        family = socket.AF_INET6 if literal.version == 6 else socket.AF_INET
        sockaddr = (str(literal), port, 0, 0) if family == socket.AF_INET6 else (str(literal), port)
        return (_resolved_address(family, socket.SOCK_STREAM, socket.IPPROTO_TCP, sockaddr),)

    try:
        answers = socket.getaddrinfo(
            host,
            port,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
        )
    except OSError as exc:
        raise ResolutionError(f"failed to resolve {host}") from exc

    resolved: list[ResolvedAddress] = []
    seen: set[tuple[int, tuple]] = set()
    for family, socktype, protocol, _canonname, sockaddr in answers:
        key = (family, sockaddr)
        if key in seen:
            continue
        seen.add(key)
        resolved.append(_resolved_address(family, socktype, protocol, sockaddr))
    if not resolved:
        raise ResolutionError("resolver returned no usable addresses")
    return tuple(resolved)


def validate_public_url(
    url: str,
    *,
    resolver: Resolver = resolve_public_addresses,
) -> None:
    parsed = _parse_url(url)
    port = parsed.port or _HTTP_PORTS[parsed.scheme]
    if not resolver(_ascii_host(parsed), port):
        raise ResolutionError("resolver returned no usable addresses")
```

- [ ] **Step 5: Run policy tests and Ruff**

Run:

```powershell
python -m pytest tests/test_pinned_http.py -q
python -m ruff check agent/pinned_http.py tests/test_pinned_http.py
```

Expected: all Task 1 tests pass; Ruff exits 0 or does not increase the committed ratchet.

- [ ] **Step 6: Commit Task 1**

```powershell
git add requirements.txt agent/pinned_http.py tests/test_pinned_http.py
git commit -m "security: add pinned egress destination policy"
```

---

### Task 2: Exact-Sockaddr Backend, Peer Verification, and TLS/SNI

**Files:**
- Modify: `agent/pinned_http.py`
- Modify: `tests/test_pinned_http.py`

**Interfaces:**
- Consumes: `ResolvedHop`, `ResolvedAddress`, `PeerMismatchError` from Task 1.
- Produces: `_PinnedNetworkStream`, `_PinnedNetworkBackend`, `_PinnedHTTPTransport`, and `build_pinned_transport(hop: ResolvedHop) -> httpx.BaseTransport`.

- [ ] **Step 1: Add failing backend and stream tests**

Add deterministic fake socket/SSL objects and these tests:

```python
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
```

- [ ] **Step 2: Run the backend subset and confirm RED**

```powershell
python -m pytest tests/test_pinned_http.py -q -k "backend or stream or peer or tls or transport"
```

Expected: failures report missing `_PinnedNetworkBackend` and `_PinnedNetworkStream`.

- [ ] **Step 3: Implement the focused `httpcore.NetworkStream` wrapper**

```python
class _PinnedNetworkStream(httpcore.NetworkStream):
    def __init__(self, sock: socket.socket) -> None:
        self._socket = sock

    def read(self, max_bytes: int, timeout: float | None = None) -> bytes:
        try:
            self._socket.settimeout(timeout)
            return self._socket.recv(max_bytes)
        except socket.timeout as exc:
            raise httpcore.ReadTimeout(str(exc)) from exc
        except OSError as exc:
            raise httpcore.ReadError(str(exc)) from exc

    def write(self, buffer: bytes, timeout: float | None = None) -> None:
        try:
            while buffer:
                self._socket.settimeout(timeout)
                written = self._socket.send(buffer)
                if written == 0:
                    raise OSError("socket connection broken")
                buffer = buffer[written:]
        except socket.timeout as exc:
            raise httpcore.WriteTimeout(str(exc)) from exc
        except OSError as exc:
            raise httpcore.WriteError(str(exc)) from exc

    def close(self) -> None:
        self._socket.close()

    def start_tls(
        self,
        ssl_context: ssl.SSLContext,
        server_hostname: str | None = None,
        timeout: float | None = None,
    ) -> httpcore.NetworkStream:
        try:
            self._socket.settimeout(timeout)
            wrapped = ssl_context.wrap_socket(
                self._socket,
                server_hostname=server_hostname,
            )
        except socket.timeout as exc:
            self.close()
            raise httpcore.ConnectTimeout(str(exc)) from exc
        except (ssl.SSLError, OSError) as exc:
            self.close()
            raise httpcore.ConnectError(str(exc)) from exc
        return _PinnedNetworkStream(wrapped)

    def get_extra_info(self, info: str) -> object:
        if info == "server_addr":
            return self._socket.getpeername()
        if info == "client_addr":
            return self._socket.getsockname()
        if info == "socket":
            return self._socket
        if info == "ssl_object" and isinstance(self._socket, ssl.SSLSocket):
            return self._socket._sslobj
        if info == "is_readable":
            readable, _, _ = select.select([self._socket], [], [], 0)
            return bool(readable)
        return None
```

- [ ] **Step 4: Implement exact-sockaddr dialing and peer checks**

Define the injected dependencies explicitly, then implement `_PinnedNetworkBackend.connect_tcp()`:

```python
SocketOption = (
    tuple[int, int, int]
    | tuple[int, int, bytes | bytearray]
    | tuple[int, int, None, int]
)
SocketFactory = Callable[[int, int, int], socket.socket]
MonotonicClock = Callable[[], float]


class _PinnedNetworkBackend(httpcore.NetworkBackend):
    def __init__(
        self,
        hop: ResolvedHop,
        *,
        socket_factory: SocketFactory = socket.socket,
        monotonic: MonotonicClock = time.monotonic,
    ) -> None:
        self._hop = hop
        self._socket_factory = socket_factory
        self._monotonic = monotonic

    def connect_unix_socket(
        self,
        path: str,
        timeout: float | None = None,
        socket_options: Iterable[SocketOption] | None = None,
    ) -> httpcore.NetworkStream:
        raise httpcore.UnsupportedProtocol("pinned HTTP supports TCP only")
```

```python
    def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[SocketOption] | None = None,
    ) -> httpcore.NetworkStream:
        if host != self._hop.host or port != self._hop.port:
            raise PeerMismatchError("httpcore requested an origin outside the pinned hop")

        deadline = None if timeout is None else self._monotonic() + timeout
        last_error: Exception | None = None
        for address in self._hop.addresses:
            remaining = None if deadline is None else max(0.0, deadline - self._monotonic())
            if remaining == 0.0:
                raise httpcore.ConnectTimeout("pinned connect budget exhausted")
            sock: socket.socket | None = None
            try:
                sock = self._socket_factory(address.family, address.socktype, address.protocol)
                sock.settimeout(remaining)
                if local_address is not None:
                    sock.bind((local_address, 0))
                for option in socket_options or ():
                    sock.setsockopt(*option)
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                sock.connect(address.sockaddr)
                peer_ip, peer_port = _normalize_peer(sock.getpeername())
                approved = {(item.ip, item.port) for item in self._hop.addresses}
                if (peer_ip, peer_port) not in approved:
                    raise PeerMismatchError(f"peer {peer_ip}:{peer_port} is outside the pinned set")
                return _PinnedNetworkStream(sock)
            except PeerMismatchError:
                if sock is not None:
                    sock.close()
                raise
            except socket.timeout as exc:
                last_error = httpcore.ConnectTimeout(str(exc))
                if sock is not None:
                    sock.close()
            except OSError as exc:
                last_error = httpcore.ConnectError(str(exc))
                if sock is not None:
                    sock.close()
        if isinstance(last_error, httpcore.TimeoutException):
            raise last_error
        if isinstance(last_error, httpcore.NetworkError):
            raise last_error
        raise httpcore.ConnectError("all pinned addresses failed")
```

Use this peer normalizer so IPv4 and IPv6 socket tuples compare consistently:

```python
def _normalize_peer(
    peer: tuple,
) -> tuple[ipaddress.IPv4Address | ipaddress.IPv6Address, int]:
    return ipaddress.ip_address(peer[0].split("%", 1)[0]), int(peer[1])
```

Do not call `socket.create_connection()` or `getaddrinfo()` in the backend.

- [ ] **Step 5: Implement the HTTPX/httpcore transport adapter**

```python
class _CoreResponseStream(httpx.SyncByteStream):
    def __init__(self, stream: Iterable[bytes]) -> None:
        self._stream = stream

    def __iter__(self):
        yield from self._stream

    def close(self) -> None:
        close = getattr(self._stream, "close", None)
        if close is not None:
            close()


class _PinnedHTTPTransport(httpx.BaseTransport):
    def __init__(self, hop: ResolvedHop) -> None:
        self._pool = httpcore.ConnectionPool(
            ssl_context=httpx.create_ssl_context(verify=True, trust_env=False),
            max_connections=1,
            max_keepalive_connections=0,
            http1=True,
            http2=False,
            retries=0,
            network_backend=_PinnedNetworkBackend(hop),
        )

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        if not isinstance(request.stream, httpx.SyncByteStream):
            raise TypeError("pinned HTTP requires a synchronous request stream")
        core_request = httpcore.Request(
            method=request.method,
            url=httpcore.URL(
                scheme=request.url.raw_scheme,
                host=request.url.raw_host,
                port=request.url.port,
                target=request.url.raw_path,
            ),
            headers=request.headers.raw,
            content=request.stream,
            extensions=request.extensions,
        )
        response = self._pool.handle_request(core_request)
        return httpx.Response(
            status_code=response.status,
            headers=response.headers,
            stream=_CoreResponseStream(response.stream),
            extensions=response.extensions,
        )

    def close(self) -> None:
        self._pool.close()


def build_pinned_transport(hop: ResolvedHop) -> httpx.BaseTransport:
    return _PinnedHTTPTransport(hop)
```

- [ ] **Step 6: Run backend tests, full pinned tests, and Ruff**

```powershell
python -m pytest tests/test_pinned_http.py -q -k "backend or stream or peer or tls or transport"
python -m pytest tests/test_pinned_http.py -q
python -m ruff check agent/pinned_http.py tests/test_pinned_http.py
```

Expected: all Task 1-2 tests pass.

- [ ] **Step 7: Commit Task 2**

```powershell
git add agent/pinned_http.py tests/test_pinned_http.py
git commit -m "security: pin outbound sockets and verify peers"
```

---

### Task 3: Manual Redirect Client and Buffered Response Contract

**Files:**
- Modify: `agent/pinned_http.py`
- Modify: `tests/test_pinned_http.py`

**Interfaces:**
- Consumes: `resolve_public_addresses`, `build_pinned_transport`, immutable response/error types from Tasks 1-2.
- Produces: `PinnedHTTPClient.__init__()`, `PinnedHTTPClient.get()`, `_resolve_hop()`, `_redirect_target()`, `_fetch_hop()`, and the final five-redirect public behavior used by all consumers.

- [ ] **Step 1: Add failing final-response and redirect tests**

Use an injected resolver and per-hop `httpx.MockTransport` factory:

```python
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
```

Add the remaining redirect, transport, decoding, and concurrency tests:

```python
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
```

- [ ] **Step 2: Run redirect tests and confirm RED**

```powershell
python -m pytest tests/test_pinned_http.py -q -k "client or redirect or proxy or concurrent or decoded"
```

Expected: failures report missing `PinnedHTTPClient` behavior.

- [ ] **Step 3: Implement hop resolution and one-hop fetch helpers**

Use exact focused helpers:

```python
def _resolve_hop(url: str | httpx.URL, resolver: Resolver) -> ResolvedHop:
    parsed = _parse_url(str(url))
    port = parsed.port or _HTTP_PORTS[parsed.scheme]
    host = _ascii_host(parsed)
    addresses = resolver(host, port)
    if not addresses:
        raise ResolutionError("resolver returned no usable addresses")
    return ResolvedHop(url=parsed, host=host, port=port, addresses=addresses)


def _fetch_hop(
    hop: ResolvedHop,
    *,
    user_agent: str,
    timeout: float | httpx.Timeout,
    transport_factory: TransportFactory,
) -> tuple[int, tuple[tuple[str, str], ...], bytes, str | None]:
    try:
        transport = transport_factory(hop)
        with httpx.Client(
            transport=transport,
            follow_redirects=False,
            trust_env=False,
            headers={"User-Agent": user_agent},
        ) as client:
            with client.stream("GET", str(hop.url), timeout=timeout) as response:
                location = response.headers.get("location")
                if response.status_code in {301, 302, 303, 307, 308} and location and location.strip():
                    return response.status_code, tuple(response.headers.multi_items()), b"", location.strip()
                content = response.read()
                return response.status_code, tuple(response.headers.multi_items()), content, None
    except PinnedHTTPError:
        raise
    except (
        OSError,
        httpx.HTTPError,
        httpcore.NetworkError,
        httpcore.TimeoutException,
        httpcore.ProtocolError,
    ) as exc:
        raise PinnedTransportError(str(exc)) from exc


def _redirect_target(current: httpx.URL, location: str) -> httpx.URL:
    try:
        return _parse_url(str(current.join(location)))
    except (InvalidDestinationError, ValueError, httpx.InvalidURL) as exc:
        raise RedirectPolicyError("redirect target is invalid") from exc
```

- [ ] **Step 4: Implement the manual redirect loop below complexity 12**

`PinnedHTTPClient.get()` must delegate target calculation and loop checks:

```python
class PinnedHTTPClient:
    def __init__(
        self,
        *,
        resolver: Resolver = resolve_public_addresses,
        transport_factory: TransportFactory = build_pinned_transport,
    ) -> None:
        self._resolver = resolver
        self._transport_factory = transport_factory

    def get(
        self,
        url: str,
        *,
        user_agent: str,
        timeout: float | httpx.Timeout = 15.0,
        max_redirects: int = 5,
    ) -> PinnedResponse:
        current = _parse_url(url)
        visited: set[tuple[str, str, int, bytes]] = set()
        redirects: list[RedirectHop] = []
        while True:
            key = _canonical_url_key(current)
            if key in visited:
                raise RedirectPolicyError("redirect loop detected")
            visited.add(key)
            hop = _resolve_hop(current, self._resolver)
            status, headers, content, location = _fetch_hop(
                hop,
                user_agent=user_agent,
                timeout=timeout,
                transport_factory=self._transport_factory,
            )
            if location is None:
                return PinnedResponse(status, str(hop.url), headers, content, tuple(redirects))
            if len(redirects) >= max_redirects:
                raise RedirectPolicyError("redirect limit exceeded")
            next_url = _redirect_target(hop.url, location)
            redirects.append(RedirectHop(str(hop.url), status, location, str(next_url)))
            current = next_url
```

If the loop function exceeds the complexity ratchet, extract `_require_unvisited()` and `_append_redirect()` without changing behavior.

- [ ] **Step 5: Run the complete shared-client suite and hard checks for the new module**

```powershell
python -m pytest tests/test_pinned_http.py -q
python -m ruff check agent/pinned_http.py tests/test_pinned_http.py
python -m pytest tests agent/tests -m "not slow and not integration and not entity_status_postgres" --ignore=tests/launch_safety/test_closed_installer.py --cov=agent --cov-report=json:coverage.json --cov-report= -q
python scripts/checks/run_hard.py --all
```

Expected: pinned suite passes, coverage generation refreshes `coverage.json`, and `run_hard` reports `hard=0` with no ratchet increase.

- [ ] **Step 6: Commit Task 3**

```powershell
git add agent/pinned_http.py tests/test_pinned_http.py
git commit -m "security: add redirect-safe pinned HTTP client"
```

---

### Task 4: Migrate Admin Image Validation and Fetching

**Files:**
- Modify: `agent/admin.py:1045-1060,2179-2235,2261-2290`
- Create: `tests/test_admin_pinned_http.py`
- Modify: `agent/tests/test_p0_security.py`
- Modify: `agent/tests/test_admin_mutations.py`
- Modify: `agent/tests/test_gap_fixes.py`
- Modify: `agent/tests/test_phase16_coverage.py`
- Modify: `tests/test_admin_p0_regressions.py`

**Interfaces:**
- Consumes: `PinnedHTTPClient`, `PinnedResponse`, `InvalidDestinationError`, `ResolutionError`, `BlockedAddressError`, `PeerMismatchError`, `RedirectPolicyError`, `PinnedTransportError`, and `validate_public_url` from Task 3.
- Produces: admin module singleton `_PINNED_HTTP`, `_validate_public_image_url()`, `_image_policy_http_error()`, and a pinned implementation of `_approve_fetch_image_data()`.

- [ ] **Step 1: Add failing behavioral adapter tests**

Create `tests/test_admin_pinned_http.py`:

```python
from __future__ import annotations

import asyncio
import copy

import httpx
import pytest
from fastapi import HTTPException

import admin
import pinned_http as ph
import storage


async def _inline_threadpool(fn):
    return fn()


def _response(
    status: int = 200,
    content: bytes = b"image",
    headers: tuple[tuple[str, str], ...] = (("content-type", "image/webp"),),
) -> ph.PinnedResponse:
    return ph.PinnedResponse(
        status_code=status,
        url="https://cdn.example/final.webp",
        headers=headers,
        content=content,
        redirects=(),
    )


def test_admin_fetch_passes_fixed_pinned_options(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict]] = []
    monkeypatch.setattr(
        admin._PINNED_HTTP,
        "get",
        lambda url, **kwargs: calls.append((url, kwargs)) or _response(),
    )
    data = asyncio.run(admin._approve_fetch_image_data("https://cdn.example/a", _inline_threadpool, 12 * 1024 * 1024))
    assert data == b"image"
    assert calls == [(
        "https://cdn.example/a",
        {
            "user_agent": "vinhlong360-image-review/1.0 (+https://vinhlong360.vn)",
            "timeout": 25,
            "max_redirects": 5,
        },
    )]


def test_admin_fetch_does_not_redecode_http_decoded_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    decoded = b"already-decoded-image"
    monkeypatch.setattr(
        admin._PINNED_HTTP,
        "get",
        lambda *_args, **_kwargs: _response(
            content=decoded,
            headers=(
                ("content-type", "image/webp"),
                ("content-encoding", "gzip"),
                ("content-length", "9"),
            ),
        ),
    )
    result = asyncio.run(
        admin._approve_fetch_image_data(
            "https://cdn.example/a",
            _inline_threadpool,
            1024,
        )
    )
    assert result == decoded


@pytest.mark.parametrize(
    "error",
    [
        ph.InvalidDestinationError("invalid"),
        ph.ResolutionError("dns"),
        ph.BlockedAddressError("blocked"),
        ph.PeerMismatchError("peer"),
        ph.RedirectPolicyError("redirect"),
    ],
)
def test_admin_fetch_maps_policy_failures_to_400(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
) -> None:
    monkeypatch.setattr(admin._PINNED_HTTP, "get", lambda *_args, **_kwargs: (_ for _ in ()).throw(error))
    with pytest.raises(HTTPException) as caught:
        asyncio.run(admin._approve_fetch_image_data("https://cdn.example/a", _inline_threadpool, 1024))
    assert caught.value.status_code == 400


def test_admin_fetch_maps_transport_and_status_failures_to_502(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(admin._PINNED_HTTP, "get", lambda *_args, **_kwargs: _response(status=404))
    with pytest.raises(HTTPException) as caught:
        asyncio.run(admin._approve_fetch_image_data("https://cdn.example/a", _inline_threadpool, 1024))
    assert caught.value.status_code == 502


@pytest.mark.parametrize("content", [b"", b"x" * 1025])
def test_admin_fetch_preserves_empty_and_size_rejection(
    monkeypatch: pytest.MonkeyPatch,
    content: bytes,
) -> None:
    monkeypatch.setattr(admin._PINNED_HTTP, "get", lambda *_args, **_kwargs: _response(content=content))
    with pytest.raises(HTTPException) as caught:
        asyncio.run(admin._approve_fetch_image_data("https://cdn.example/a", _inline_threadpool, 1024))
    assert caught.value.status_code == 400
```

Add the validation, offload, endpoint-state, and credit tests:

```python
class RecordingDB:
    def __init__(self, entity: dict) -> None:
        self.entity = copy.deepcopy(entity)
        self.upserts: list[dict] = []

    def get_entity(self, entity_id: str) -> dict:
        assert entity_id == self.entity["id"]
        return copy.deepcopy(self.entity)

    def upsert_entity(self, entity: dict) -> None:
        saved = copy.deepcopy(entity)
        self.upserts.append(saved)
        self.entity = saved


@pytest.mark.parametrize(
    ("error", "detail"),
    [
        (ph.InvalidDestinationError("invalid"), "URL ảnh không hợp lệ (chỉ http/https)"),
        (ph.ResolutionError("dns"), "Không phân giải được host ảnh"),
        (ph.BlockedAddressError("blocked"), "Host ảnh trỏ địa chỉ nội bộ — từ chối (SSRF)"),
        (ph.PeerMismatchError("peer"), "Host ảnh trỏ địa chỉ nội bộ — từ chối (SSRF)"),
    ],
)
def test_validate_public_image_url_preserves_localized_400(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    detail: str,
) -> None:
    def fail(_url: str) -> None:
        raise error

    monkeypatch.setattr(admin, "validate_public_url", fail)
    with pytest.raises(HTTPException) as caught:
        admin._validate_public_image_url("https://example.com/image.webp")
    assert caught.value.status_code == 400
    assert caught.value.detail == detail


def test_add_entity_image_url_validates_without_fetching(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    url = "https://licensed.example/original.webp"
    database = RecordingDB({
        "id": "entity-1",
        "name": "Entity",
        "type": "attraction",
        "images": [],
    })
    validations: list[str] = []
    monkeypatch.setattr(admin, "is_canonical_legacy_entity_image", lambda _url: True)
    monkeypatch.setattr(admin, "_validate_public_image_url", validations.append)
    monkeypatch.setattr(
        admin._PINNED_HTTP,
        "get",
        lambda *_args, **_kwargs: pytest.fail("validation-only route fetched content"),
    )
    monkeypatch.setattr(admin, "db", database)
    monkeypatch.setattr(admin, "_sync_kb", lambda: None)

    result = asyncio.run(
        admin.add_entity_image_url(
            "entity-1",
            admin._EntityImageURL(url=url),
        )
    )
    assert validations == [url]
    assert result == {"status": "added", "images": [url]}
    assert database.upserts[0]["images"] == [url]


def test_admin_fetch_executes_pinned_get_inside_threadpool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inside_threadpool = False

    def get(_url: str, **_kwargs) -> ph.PinnedResponse:
        assert inside_threadpool is True
        return _response(content=b"image")

    async def guarded_threadpool(fn):
        nonlocal inside_threadpool
        inside_threadpool = True
        try:
            return fn()
        finally:
            inside_threadpool = False

    monkeypatch.setattr(admin._PINNED_HTTP, "get", get)
    assert asyncio.run(
        admin._approve_fetch_image_data(
            "https://example.com/image.webp",
            guarded_threadpool,
            1024,
        )
    ) == b"image"


@pytest.mark.parametrize(
    ("outcome", "expected_status"),
    [
        (ph.BlockedAddressError("blocked"), 400),
        (ph.RedirectPolicyError("loop"), 400),
        (ph.PinnedTransportError("connect"), 502),
        (_response(status=404), 502),
        (_response(content=b""), 400),
        (_response(content=b"12345"), 400),
    ],
    ids=["blocked", "redirect", "transport", "http-status", "empty", "oversize"],
)
def test_approval_fetch_failures_leave_all_state_untouched(
    monkeypatch: pytest.MonkeyPatch,
    outcome: Exception | ph.PinnedResponse,
    expected_status: int,
) -> None:
    suggestion = {
        "id": "suggestion-1",
        "entity_id": "entity-1",
        "candidate_url": "https://licensed.example/original.webp",
        "status": "pending",
        "license": "CC BY-SA 4.0",
        "author": "Author",
        "source": "wikipedia-vi",
    }
    original_entity = {
        "id": "entity-1",
        "name": "Entity",
        "type": "attraction",
        "images": [],
        "attributes": {},
    }
    database = RecordingDB(original_entity)
    uploads: list[bytes] = []
    status_changes: list[tuple] = []
    syncs: list[bool] = []

    def get(*_args, **_kwargs):
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(admin, "_reject_non_ai_media", lambda: None)
    monkeypatch.setattr(admin, "db", database)
    monkeypatch.setattr(admin._imgq, "get_suggestion", lambda _id: copy.deepcopy(suggestion))
    monkeypatch.setattr(
        admin._imgq,
        "mark_status",
        lambda *args, **kwargs: status_changes.append((args, kwargs)),
    )
    monkeypatch.setattr(admin, "_sync_kb", lambda: syncs.append(True))
    monkeypatch.setattr(admin._PINNED_HTTP, "get", get)
    monkeypatch.setattr(storage, "MAX_IMAGE_SIZE", 4)
    monkeypatch.setattr(
        storage.storage,
        "upload_image_set",
        lambda data, *_args: uploads.append(data) or {"md": "/img/entities/entity-1.webp"},
    )

    with pytest.raises(HTTPException) as caught:
        asyncio.run(admin.approve_image_suggestion("suggestion-1"))
    assert caught.value.status_code == expected_status
    assert database.entity == original_entity
    assert database.upserts == []
    assert uploads == []
    assert status_changes == []
    assert syncs == []
    assert suggestion["status"] == "pending"


def test_approval_keeps_original_candidate_url_in_redirected_credit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate_url = "https://licensed.example/original.webp"
    suggestion = {
        "id": "suggestion-1",
        "entity_id": "entity-1",
        "candidate_url": candidate_url,
        "status": "pending",
        "license": "CC BY-SA 4.0",
        "author": "Author",
        "source": "wikipedia-vi",
        "wp_title": "File:Original.webp",
    }
    database = RecordingDB({
        "id": "entity-1",
        "name": "Entity",
        "type": "attraction",
        "images": [],
        "attributes": {},
    })
    status_changes: list[tuple] = []

    monkeypatch.setattr(admin, "_reject_non_ai_media", lambda: None)
    monkeypatch.setattr(
        admin,
        "_validate_public_image_url",
        lambda _url: pytest.fail("separate validation called before pinned fetch"),
    )
    monkeypatch.setattr(admin, "db", database)
    monkeypatch.setattr(admin._imgq, "get_suggestion", lambda _id: copy.deepcopy(suggestion))
    monkeypatch.setattr(
        admin._imgq,
        "mark_status",
        lambda *args, **kwargs: status_changes.append((args, kwargs)),
    )
    monkeypatch.setattr(admin, "_sync_kb", lambda: None)
    monkeypatch.setattr(
        admin._PINNED_HTTP,
        "get",
        lambda *_args, **_kwargs: _response(content=b"image"),
    )
    monkeypatch.setattr(storage, "MAX_IMAGE_SIZE", 1024)
    monkeypatch.setattr(
        storage.storage,
        "upload_image_set",
        lambda *_args: {"md": "/img/entities/entity-1.webp"},
    )

    result = asyncio.run(admin.approve_image_suggestion("suggestion-1"))
    saved_credit = database.upserts[0]["attributes"]["image_credits"][-1]
    assert result["credits"]["source_url"] == candidate_url
    assert saved_credit["source_url"] == candidate_url
    assert status_changes == [
        (("suggestion-1", "approved"), {"approved_by": "admin"}),
    ]
```

- [ ] **Step 2: Run the admin tests and confirm RED**

```powershell
python -m pytest tests/test_admin_pinned_http.py -q
```

Expected: failures report missing `_PINNED_HTTP` and `_validate_public_image_url`.

- [ ] **Step 3: Replace the old admin SSRF helpers with the pinned adapter**

Move `httpx` to the module-scope imports, import the shared symbols, and create one client:

```python
from pinned_http import (
    DestinationPolicyError,
    InvalidDestinationError,
    PinnedHTTPClient,
    PinnedTransportError,
    RedirectPolicyError,
    ResolutionError,
    validate_public_url,
)

_PINNED_HTTP = PinnedHTTPClient()
```

Delete `_is_blocked_ip()`, `_assert_public_url()`, and `_fetch_public_url()`. Add:

```python
def _image_policy_http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, InvalidDestinationError):
        return HTTPException(400, "URL ảnh không hợp lệ (chỉ http/https)")
    if isinstance(exc, ResolutionError):
        return HTTPException(400, "Không phân giải được host ảnh")
    if isinstance(exc, RedirectPolicyError):
        return HTTPException(400, "URL ảnh chuyển hướng quá nhiều lần")
    return HTTPException(400, "Host ảnh trỏ địa chỉ nội bộ — từ chối (SSRF)")


def _validate_public_image_url(url: str) -> None:
    try:
        validate_public_url(url)
    except DestinationPolicyError as exc:
        raise _image_policy_http_error(exc) from exc
```

- [ ] **Step 4: Implement pinned fetch and preserve status/body behavior**

```python
async def _approve_fetch_image_data(candidate_url, run_in_threadpool, max_image_size):
    try:
        result = await run_in_threadpool(
            lambda: _PINNED_HTTP.get(
                candidate_url,
                user_agent="vinhlong360-image-review/1.0 (+https://vinhlong360.vn)",
                timeout=25,
                max_redirects=5,
            )
        )
        status_response = httpx.Response(
            result.status_code,
            headers=result.headers,
            request=httpx.Request("GET", result.url),
        )
        status_response.raise_for_status()
        data = result.content
    except (DestinationPolicyError, RedirectPolicyError) as exc:
        raise _image_policy_http_error(exc) from exc
    except (PinnedTransportError, httpx.HTTPStatusError) as exc:
        logger.warning("Suggestion image fetch failed for %s: %s", candidate_url, exc)
        raise HTTPException(502, "Không tải được ảnh nguồn, vui lòng thử lại sau") from exc

    if not data or len(data) > max_image_size:
        raise HTTPException(
            400,
            f"Ảnh nguồn rỗng hoặc quá lớn (tối đa {max_image_size // 1024 // 1024}MB)",
        )
    return data
```

Remove the separate preflight from `approve_image_suggestion()` so the endpoint goes directly from:

```python
candidate_url = s["candidate_url"]
data = await _approve_fetch_image_data(
    candidate_url,
    run_in_threadpool,
    MAX_IMAGE_SIZE,
)
```

For validation-only external URLs, `add_entity_image_url()` uses:

```python
if url.startswith("/"):
    pass
else:
    await asyncio.to_thread(_validate_public_image_url, url)
```

- [ ] **Step 5: Update stale admin tests**

Apply these exact replacements:

```python
# agent/tests/test_p0_security.py
def test_validate_public_image_url_rejects_internal_and_bad(bad_url):
    from admin import _validate_public_image_url

    with pytest.raises(HTTPException):
        _validate_public_image_url(bad_url)


# agent/tests/test_admin_mutations.py, image-URL early rejection
network_calls: list[str] = []
monkeypatch.setattr(admin, "_validate_public_image_url", network_calls.append)


# agent/tests/test_admin_mutations.py, suggestion early rejection
monkeypatch.setattr(
    admin._PINNED_HTTP,
    "get",
    lambda *_args, **_kwargs: side_effects.append("network"),
)


# agent/tests/test_gap_fixes.py
def test_image_url_validation_and_fetch_are_offloaded(self):
    import admin

    validation_src = inspect.getsource(admin.add_entity_image_url)
    fetch_src = inspect.getsource(admin._approve_fetch_image_data)
    assert "await asyncio.to_thread(_validate_public_image_url" in validation_src
    assert "await run_in_threadpool(" in fetch_src
    assert "_PINNED_HTTP.get(" in fetch_src


# agent/tests/test_phase16_coverage.py
def test_ssrf_protection_on_entity_image_url(self):
    src = (Path(__file__).resolve().parent.parent / "admin.py").read_text(encoding="utf-8")
    idx = src.find("def add_entity_image_url")
    assert idx > 0
    block = src[idx:idx + 700]
    assert "_validate_public_image_url" in block
    assert "asyncio.to_thread" in block
```

Delete `test_image_suggestion_fetch_revalidates_redirect_targets()` from `tests/test_admin_p0_regressions.py`; its source-only contract is replaced by the redirect, localized-error, and endpoint-state tests in `tests/test_pinned_http.py` and `tests/test_admin_pinned_http.py`.

- [ ] **Step 6: Run all owning admin tests and Ruff**

```powershell
python -m pytest tests/test_admin_pinned_http.py tests/test_admin_p0_regressions.py agent/tests/test_p0_security.py agent/tests/test_admin_mutations.py agent/tests/test_gap_fixes.py agent/tests/test_phase16_coverage.py -q
python -m ruff check agent/admin.py tests/test_admin_pinned_http.py agent/tests/test_p0_security.py agent/tests/test_admin_mutations.py agent/tests/test_gap_fixes.py agent/tests/test_phase16_coverage.py tests/test_admin_p0_regressions.py
```

Expected: all selected tests pass; no new Ruff or complexity debt.

- [ ] **Step 7: Commit Task 4**

```powershell
git add agent/admin.py tests/test_admin_pinned_http.py tests/test_admin_p0_regressions.py agent/tests/test_p0_security.py agent/tests/test_admin_mutations.py agent/tests/test_gap_fixes.py agent/tests/test_phase16_coverage.py
git commit -m "security: route admin image fetch through pinned HTTP"
```

---

### Task 5: Migrate Auto-Learn Fetching and Preserve HTTPX Text Semantics

**Files:**
- Modify: `agent/auto_learn.py:39,241-254`
- Create: `tests/test_auto_learn_fetch.py`

**Interfaces:**
- Consumes: `PinnedHTTPClient`, `PinnedResponse` from Task 3.
- Produces: `_PINNED_HTTP`, `_decode_pinned_httpx_text(response: PinnedResponse) -> str`, and the migrated `fetch_url(url: str) -> str | None`.

- [ ] **Step 1: Add failing auto-learn fetch tests**

Create `tests/test_auto_learn_fetch.py` with a fake pinned client:

```python
from __future__ import annotations

import logging

import pytest

import auto_learn
import pinned_http as ph


def _response(
    *,
    status: int = 200,
    content: bytes = b"",
    content_type: str | None = "text/html; charset=utf-8",
    extra_headers: tuple[tuple[str, str], ...] = (),
) -> ph.PinnedResponse:
    headers = extra_headers
    if content_type is not None:
        headers = (("content-type", content_type),) + headers
    return ph.PinnedResponse(status, "https://example.com/final", headers, content, ())


def test_fetch_url_uses_pinned_options_and_preserves_cleanup(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict]] = []
    body = b"<script>drop()</script><style>.x{}</style><h1>Vinh Long</h1> noi dung"
    monkeypatch.setattr(
        auto_learn._PINNED_HTTP,
        "get",
        lambda url, **kwargs: calls.append((url, kwargs)) or _response(content=body),
    )
    assert auto_learn.fetch_url("https://example.com/a") == "Vinh Long noi dung"
    assert calls == [(
        "https://example.com/a",
        {
            "user_agent": "vinhlong360-learner/1.0",
            "timeout": 15,
            "max_redirects": 5,
        },
    )]


@pytest.mark.parametrize("status", [199, 204, 302, 399, 400, 500])
def test_fetch_url_requires_exact_200(monkeypatch: pytest.MonkeyPatch, status: int) -> None:
    monkeypatch.setattr(
        auto_learn._PINNED_HTTP,
        "get",
        lambda *_args, **_kwargs: _response(status=status, content=b"ignored"),
    )
    assert auto_learn.fetch_url("https://example.com/a") is None


def test_fetch_url_keeps_httpx_charset_behavior(monkeypatch: pytest.MonkeyPatch) -> None:
    content = "café Vĩnh Long".encode("iso-8859-1", errors="replace")
    monkeypatch.setattr(
        auto_learn._PINNED_HTTP,
        "get",
        lambda *_args, **_kwargs: _response(
            content=content,
            content_type="text/html; charset=iso-8859-1",
            extra_headers=(("content-encoding", "gzip"), ("content-length", "10")),
        ),
    )
    assert "café" in auto_learn.fetch_url("https://example.com/a")


def test_fetch_url_logs_and_returns_none_on_failure(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(
        auto_learn._PINNED_HTTP,
        "get",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ph.PinnedTransportError("boom")),
    )
    with caplog.at_level(logging.WARNING):
        assert auto_learn.fetch_url("https://example.com/a") is None
    assert "https://example.com/a" in caplog.text
```

Add the remaining HTTPX compatibility and caller-threshold tests:

```python
def test_fetch_url_missing_charset_uses_httpx_utf8_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = "Vĩnh Long miền sông nước".encode("utf-8")
    monkeypatch.setattr(
        auto_learn._PINNED_HTTP,
        "get",
        lambda *_args, **_kwargs: _response(content=body, content_type="text/html"),
    )
    assert auto_learn.fetch_url("https://example.com/a") == "Vĩnh Long miền sông nước"


def test_fetch_url_does_not_redecode_http_decoded_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    decoded_body = "Nội dung đã giải nén".encode("utf-8")
    monkeypatch.setattr(
        auto_learn._PINNED_HTTP,
        "get",
        lambda *_args, **_kwargs: _response(
            content=decoded_body,
            extra_headers=(
                ("content-encoding", "gzip"),
                ("content-length", "12"),
                ("transfer-encoding", "chunked"),
            ),
        ),
    )
    assert auto_learn.fetch_url("https://example.com/a") == "Nội dung đã giải nén"


def test_fetch_url_truncates_cleaned_text_to_exactly_6000_characters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        auto_learn._PINNED_HTTP,
        "get",
        lambda *_args, **_kwargs: _response(
            content=("<p>" + ("x" * 6005) + "</p>").encode(),
        ),
    )
    result = auto_learn.fetch_url("https://example.com/a")
    assert result == "x" * 6000
    assert len(result) == 6000


def test_process_result_skips_text_shorter_than_200_without_extraction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(auto_learn, "fetch_url", lambda _url: "x" * 199)
    monkeypatch.setattr(
        auto_learn,
        "extract_entities_from_text",
        lambda *_args, **_kwargs: pytest.fail("extraction called for short text"),
    )
    known: set[str] = set()
    new_entities: list[dict] = []
    auto_learn._process_result(
        {"href": "https://example.com/a"},
        "query",
        known,
        new_entities,
    )
    assert known == set()
    assert new_entities == []
```

- [ ] **Step 2: Run the auto-learn tests and confirm RED**

```powershell
python -m pytest tests/test_auto_learn_fetch.py -q
```

Expected: failures report missing `_PINNED_HTTP` and direct `httpx.get()` behavior.

- [ ] **Step 3: Add the pinned client and offline HTTPX decoder**

```python
import httpx

from pinned_http import PinnedHTTPClient, PinnedResponse


_PINNED_HTTP = PinnedHTTPClient()
_HTTP_ENTITY_HEADERS = {"content-encoding", "content-length", "transfer-encoding"}


def _decode_pinned_httpx_text(response: PinnedResponse) -> str:
    headers = [
        (name, value)
        for name, value in response.headers
        if name.lower() not in _HTTP_ENTITY_HEADERS
    ]
    offline = httpx.Response(
        status_code=response.status_code,
        headers=headers,
        content=response.content,
        request=httpx.Request("GET", response.url),
    )
    return offline.text
```

- [ ] **Step 4: Replace only the network operation in `fetch_url()`**

```python
def fetch_url(url: str) -> str | None:
    try:
        response = _PINNED_HTTP.get(
            url,
            user_agent="vinhlong360-learner/1.0",
            timeout=15,
            max_redirects=5,
        )
        if response.status_code != 200:
            return None
        text = _decode_pinned_httpx_text(response)
        text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.S)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.S)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:6000]
    except Exception as exc:
        logger.warning("Failed to fetch %s: %s", url, exc)
        return None
```

- [ ] **Step 5: Run owning tests and Ruff**

```powershell
python -m pytest tests/test_auto_learn_fetch.py tests/test_runtime_place_mappings.py -q
python -m ruff check agent/auto_learn.py tests/test_auto_learn_fetch.py tests/test_runtime_place_mappings.py
```

Expected: both suites pass.

- [ ] **Step 6: Commit Task 5**

```powershell
git add agent/auto_learn.py tests/test_auto_learn_fetch.py
git commit -m "security: pin auto-learn source fetches"
```

---

### Task 6: Migrate Quality-Burst Fetching and Preserve Requests Text Semantics

**Files:**
- Modify: `agent/gpt55_quality_burst.py:48-51,645-655`
- Modify: `tests/test_gpt55_quality_burst.py`

**Interfaces:**
- Consumes: `PinnedHTTPClient`, `PinnedResponse` from Task 3 and the existing optional `requests` import.
- Produces: `_PINNED_HTTP`, `_decode_pinned_requests_text(response: PinnedResponse) -> str`, and the migrated `fetch_url_text()`.

- [ ] **Step 1: Add failing quality-burst fetch tests**

Append:

```python
import logging
import re

import pytest

import pinned_http as ph


def _pinned_response(
    *,
    status: int = 200,
    content: bytes = b"",
    headers: tuple[tuple[str, str], ...] = (("content-type", "text/html; charset=utf-8"),),
) -> ph.PinnedResponse:
    return ph.PinnedResponse(status, "https://example.com/final", headers, content, ())


def test_fetch_url_text_uses_pinned_options_and_tag_only_cleanup(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict]] = []
    body = b"<script>keep_me()</script><style>.keep{}</style><h1>Vinh Long</h1>"
    monkeypatch.setattr(
        q._PINNED_HTTP,
        "get",
        lambda url, **kwargs: calls.append((url, kwargs)) or _pinned_response(content=body),
    )
    text = q.fetch_url_text("https://example.com/a", timeout=12)
    assert "keep_me()" in text
    assert ".keep{}" in text
    assert "Vinh Long" in text
    assert calls == [(
        "https://example.com/a",
        {
            "user_agent": "vinhlong360-quality-burst/1.0",
            "timeout": 12,
            "max_redirects": 5,
        },
    )]


@pytest.mark.parametrize("status, expected", [(200, True), (399, True), (400, False), (500, False)])
def test_fetch_url_text_preserves_status_contract(
    monkeypatch: pytest.MonkeyPatch,
    status: int,
    expected: bool,
) -> None:
    monkeypatch.setattr(
        q._PINNED_HTTP,
        "get",
        lambda *_args, **_kwargs: _pinned_response(status=status, content=b"body"),
    )
    assert bool(q.fetch_url_text("https://example.com/a")) is expected


def test_fetch_url_text_skips_client_when_requests_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(q, "requests", None)
    monkeypatch.setattr(
        q._PINNED_HTTP,
        "get",
        lambda *_args, **_kwargs: pytest.fail("pinned client called"),
    )
    assert q.fetch_url_text("https://example.com/a") == ""


def test_fetch_url_text_keeps_requests_charset_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    content = "café".encode("iso-8859-1")
    monkeypatch.setattr(
        q._PINNED_HTTP,
        "get",
        lambda *_args, **_kwargs: _pinned_response(
            content=content,
            headers=(("content-type", "text/html; charset=iso-8859-1"),),
        ),
    )
    assert q.fetch_url_text("https://example.com/a") == "café"


def test_fetch_url_text_does_not_redecode_http_decoded_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    decoded = "Nội dung đã giải nén".encode("utf-8")
    monkeypatch.setattr(
        q._PINNED_HTTP,
        "get",
        lambda *_args, **_kwargs: _pinned_response(
            content=decoded,
            headers=(
                ("content-type", "text/html; charset=utf-8"),
                ("content-encoding", "gzip"),
                ("content-length", "12"),
            ),
        ),
    )
    assert q.fetch_url_text("https://example.com/a") == "Nội dung đã giải nén"
```

Add the remaining guard, Requests fallback, silence, truncation, and verification-message tests:

```python
@pytest.mark.parametrize(
    ("url", "disabled"),
    [
        ("https://example.com/a", True),
        ("not-a-url", False),
    ],
)
def test_fetch_url_text_guards_skip_pinned_client(
    monkeypatch: pytest.MonkeyPatch,
    url: str,
    disabled: bool,
) -> None:
    monkeypatch.setattr(
        q._PINNED_HTTP,
        "get",
        lambda *_args, **_kwargs: pytest.fail("pinned client called"),
    )
    assert q.fetch_url_text(url, disabled=disabled) == ""


def test_fetch_url_text_without_content_type_matches_requests_apparent_encoding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert q.requests is not None
    content = ("Café déjà vu, façade et élève. " * 20).encode("cp1252")
    monkeypatch.setattr(
        q._PINNED_HTTP,
        "get",
        lambda *_args, **_kwargs: _pinned_response(content=content, headers=()),
    )
    offline = q.requests.Response()
    offline.headers = q.requests.structures.CaseInsensitiveDict()
    offline._content = content
    offline._content_consumed = True
    offline.encoding = q.requests.utils.get_encoding_from_headers(offline.headers)
    expected = q.compact_text(re.sub(r"<[^>]+>", " ", offline.text or ""), 5000)
    assert q.fetch_url_text("https://example.com/a") == expected


def test_fetch_url_text_silently_returns_empty_on_transport_failure(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(
        q._PINNED_HTTP,
        "get",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            ph.PinnedTransportError("connect failed")
        ),
    )
    with caplog.at_level(logging.WARNING):
        assert q.fetch_url_text("https://example.com/a") == ""
    assert caplog.records == []


def test_fetch_url_text_truncates_to_exactly_5000_characters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        q._PINNED_HTTP,
        "get",
        lambda *_args, **_kwargs: _pinned_response(content=("x" * 5005).encode()),
    )
    result = q.fetch_url_text("https://example.com/a")
    assert result == "x" * 5000
    assert len(result) == 5000


def test_verify_source_url_preserves_all_messages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entity = {"name": "Vinh Long"}
    assert q.verify_source_url("not-a-url", entity) == (False, "invalid URL")

    monkeypatch.setattr(q, "fetch_url_text", lambda *_args, **_kwargs: "")
    assert q.verify_source_url("https://example.com/a", entity) == (
        False,
        "URL could not be fetched",
    )

    monkeypatch.setattr(
        q,
        "fetch_url_text",
        lambda *_args, **_kwargs: "Tourism information for Vinh Long",
    )
    assert q.verify_source_url("https://example.com/a", entity) == (
        True,
        "URL opens and page text matches entity name",
    )

    monkeypatch.setattr(
        q,
        "fetch_url_text",
        lambda *_args, **_kwargs: "Completely unrelated page",
    )
    assert q.verify_source_url("https://example.com/a", entity) == (
        False,
        "URL opens but page text does not clearly match entity",
    )


def test_verify_source_url_no_web_passes_disabled_without_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, bool]] = []

    def fetch(url: str, *, disabled: bool = False, **_kwargs) -> str:
        calls.append((url, disabled))
        return ""

    monkeypatch.setattr(q, "fetch_url_text", fetch)
    assert q.verify_source_url(
        "https://example.com/a",
        {"name": "Vinh Long"},
        no_web=True,
    ) == (False, "URL could not be fetched")
    assert calls == [("https://example.com/a", True)]
```

- [ ] **Step 2: Run the quality-burst tests and confirm RED**

```powershell
python -m pytest tests/test_gpt55_quality_burst.py -q -k "fetch_url_text or verify_source_url"
```

Expected: failures report missing `_PINNED_HTTP` and direct Requests networking.

- [ ] **Step 3: Add the pinned client and offline Requests decoder**

```python
from pinned_http import PinnedHTTPClient, PinnedResponse

_PINNED_HTTP = PinnedHTTPClient()


def _decode_pinned_requests_text(response: PinnedResponse) -> str:
    assert requests is not None
    offline = requests.Response()
    offline.status_code = response.status_code
    offline.url = response.url
    offline.headers = requests.structures.CaseInsensitiveDict(response.headers)
    offline._content = response.content
    offline._content_consumed = True
    offline.encoding = requests.utils.get_encoding_from_headers(offline.headers)
    return offline.text
```

- [ ] **Step 4: Replace `requests.get()` while preserving guards and silence**

```python
def fetch_url_text(url: str, *, timeout: int = 12, disabled: bool = False) -> str:
    if disabled or not is_valid_http_url(url) or requests is None:
        return ""
    try:
        response = _PINNED_HTTP.get(
            url,
            user_agent="vinhlong360-quality-burst/1.0",
            timeout=timeout,
            max_redirects=5,
        )
        if response.status_code >= 400:
            return ""
        text = _decode_pinned_requests_text(response)
        return compact_text(re.sub(r"<[^>]+>", " ", text or ""), 5000)
    except Exception:
        return ""
```

- [ ] **Step 5: Run owning tests and Ruff**

```powershell
python -m pytest tests/test_gpt55_quality_burst.py -q
python -m ruff check agent/gpt55_quality_burst.py tests/test_gpt55_quality_burst.py
```

Expected: the full quality-burst test file passes.

- [ ] **Step 6: Commit Task 6**

```powershell
git add agent/gpt55_quality_burst.py tests/test_gpt55_quality_burst.py
git commit -m "security: pin quality-burst source fetches"
```

---

### Task 7: Cross-Consumer Registry and Focused Integration

**Files:**
- Create: `tests/test_pinned_http_consumers.py`
- Modify only if integration exposes a real defect: files owned by Tasks 1-6, with the owning tests updated in the same commit.

**Interfaces:**
- Consumes: completed Task 3 core and Task 4-6 consumer adapters.
- Produces: exact mapped-consumer registry contract and integrated focused-test evidence.

- [ ] **Step 1: Add the direct-network-call registry test**

Create:

```python
from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAPPED_FETCHERS = {
    "agent/admin.py": {"_approve_fetch_image_data"},
    "agent/auto_learn.py": {"fetch_url"},
    "agent/gpt55_quality_burst.py": {"fetch_url_text"},
}


def _calls_in_function(path: Path, function_name: str) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    function = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name
    )
    calls: set[str] = set()
    for node in ast.walk(function):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if isinstance(node.func.value, ast.Name):
            calls.add(f"{node.func.value.id}.{node.func.attr}")
    return calls


def test_mapped_fetchers_have_no_direct_general_http_calls() -> None:
    for relative_path, functions in MAPPED_FETCHERS.items():
        path = ROOT / relative_path
        for function_name in functions:
            calls = _calls_in_function(path, function_name)
            assert "httpx.get" not in calls
            assert "requests.get" not in calls


def _module_pinned_http_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "pinned_http":
            imported.update(alias.name for alias in node.names)
    return imported


def test_mapped_fetcher_registry_scope_is_exact() -> None:
    assert MAPPED_FETCHERS == {
        "agent/admin.py": {"_approve_fetch_image_data"},
        "agent/auto_learn.py": {"fetch_url"},
        "agent/gpt55_quality_burst.py": {"fetch_url_text"},
    }


def test_every_mapped_module_imports_pinned_http_client() -> None:
    for relative_path in MAPPED_FETCHERS:
        imported = _module_pinned_http_imports(ROOT / relative_path)
        assert "PinnedHTTPClient" in imported, (
            f"{relative_path} does not import PinnedHTTPClient"
        )
```

- [ ] **Step 2: Run the registry test and confirm it passes only after all migrations are integrated**

```powershell
python -m pytest tests/test_pinned_http_consumers.py -q
```

Expected: pass. If it fails, fix the owning consumer; do not weaken the registry.

- [ ] **Step 3: Run the complete focused P1 suite**

```powershell
python -m pytest tests/test_pinned_http.py tests/test_admin_pinned_http.py tests/test_auto_learn_fetch.py tests/test_gpt55_quality_burst.py tests/test_runtime_place_mappings.py tests/test_admin_p0_regressions.py tests/test_pinned_http_consumers.py agent/tests/test_p0_security.py agent/tests/test_admin_mutations.py agent/tests/test_gap_fixes.py agent/tests/test_phase16_coverage.py -q
```

Expected: exit 0 with no live network access.

- [ ] **Step 4: Run repository hard checks before the integration commit**

```powershell
python -m pytest tests agent/tests -m "not slow and not integration and not entity_status_postgres" --ignore=tests/launch_safety/test_closed_installer.py --cov=agent --cov-report=json:coverage.json --cov-report= -q
python scripts/checks/run_hard.py --all
git diff --check
```

Expected: coverage generation refreshes `coverage.json`, `hard=0`, no ratchet increase, and no whitespace errors.

- [ ] **Step 5: Commit the registry contract**

```powershell
git add tests/test_pinned_http_consumers.py
git commit -m "test: lock pinned HTTP consumer registry"
```

---

### Task 8: Full Regression, Truth Sync, and Final Review

**Files:**
- Modify: `docs/ROADMAP.md:418-421`
- Modify: `docs/HANDOFF.md:1-7,120-135`
- Verify: all files changed by Tasks 1-7

**Interfaces:**
- Consumes: integrated P1 commits and focused evidence from Task 7.
- Produces: full backend evidence, current operational documentation, and a clean locally committed branch ready for merge/push decision.

- [ ] **Step 1: Re-run focused tests from the integrated HEAD**

```powershell
python -m pytest tests/test_pinned_http.py tests/test_admin_pinned_http.py tests/test_auto_learn_fetch.py tests/test_gpt55_quality_burst.py tests/test_runtime_place_mappings.py tests/test_admin_p0_regressions.py tests/test_pinned_http_consumers.py agent/tests/test_p0_security.py agent/tests/test_admin_mutations.py agent/tests/test_gap_fixes.py agent/tests/test_phase16_coverage.py -q
```

Expected: exit 0. Any new failure stops truth-sync and must be triaged as a regression.

- [ ] **Step 2: Run hard checks and the bounded backend regression**

```powershell
python -m pytest tests agent/tests -m "not slow and not integration and not entity_status_postgres" --ignore=tests/launch_safety/test_closed_installer.py --cov=agent --cov-report=json:coverage.json --cov-report= -q
python scripts/checks/run_hard.py --all
python scripts/ops/run_backend_regression.py --deadline-seconds 7000
```

The coverage command must finish and write a fresh `coverage.json` before `run_hard`; do not reuse the artifact from a prior revision. Run the backend command with an outer process timeout greater than 7,000 seconds. Expected: coverage generation exits 0, `run_hard` reports `hard=0` with no ratchet increase, and the backend runner exits 0. Exit `124` is a failed regression gate, not a skip.

- [ ] **Step 3: Perform final two-stage code review before truth-sync**

Dispatch one spec-compliance reviewer against `0f210a87..HEAD`, then one code-quality reviewer after compliance passes. Resolve findings in the owning task's files and rerun that task's focused tests. If any production or test code changes after review, rerun the fresh coverage command, `run_hard.py --all`, and the bounded backend regression from Step 2 before editing truth documents.

- [ ] **Step 4: Update ROADMAP only after gates and reviews pass**

Under `### Security/CI remediation tranche (2026-07-26)`, append:

```markdown
- ✅ **P1 shared pinned outbound HTTP client:** `agent/pinned_http.py` now owns per-hop public DNS policy, exact-sockaddr dialing, peer verification, TLS hostname/SNI preservation, and manual redirect validation for admin image review, auto-learn, and GPT-5.5 quality-burst fetches. Mock DNS/redirect/peer/TLS suites, `run_hard.py --all`, and the bounded backend regression pass locally. No push/deploy.
- **Residual egress debt:** streaming body/decompression bounds and a whole-chain monotonic deadline remain Workstream 10; crawler/geocode/realtime/bot/moderation migrations remain outside this P1 tranche.
```

- [ ] **Step 5: Update HANDOFF with current authority and residual debt**

In the opening status paragraph, include P1 pinned egress in the completed local security tranche. In the backlog section add:

```markdown
- **[P1 follow-up / Workstream 10] Outbound body and deadline bounds:** the shared pinned client closes DNS/connect/redirect authority but intentionally preserves eager response buffering and per-hop timeout semantics. Add bounded decompression/body allocation and one monotonic whole-chain deadline in the dedicated bounded-work tranche; do not weaken peer pinning while doing so.
```

- [ ] **Step 6: Verify documentation and final diff**

```powershell
python scripts/checks/run_hard.py --all
git diff --check
git status --short
```

Expected: hard checks remain clean; only the two documentation files are uncommitted at this step.

- [ ] **Step 7: Commit truth-sync documentation**

```powershell
git add docs/ROADMAP.md docs/HANDOFF.md
git commit -m "docs: record pinned egress verification"
```

- [ ] **Step 8: Confirm final local state**

Run:

```powershell
git status --short --branch
git log --oneline -10
```

Expected: clean worktree on the implementation branch, all task commits visible, no push/deploy performed.

## Completion Criteria

- Every mapped fetch uses `PinnedHTTPClient`; no mapped function directly calls `httpx.get()` or `requests.get()`.
- Mock tests prove allowed, blocked, mixed-address, transition-address, redirect, peer-mismatch, TLS/SNI, proxy-isolation, and concurrency behavior.
- The admin adapter retains 400/502/body-size/state semantics and does not perform a separate preflight before fetching.
- Auto-learn retains exact-200, HTTPX charset, cleanup, warning, 6,000-character, and under-200 caller behavior.
- Quality-burst retains optional Requests, `<400`, Requests charset, silent failure, tag-only cleanup, 5,000-character, and `--no-web` behavior.
- `python scripts/checks/run_hard.py --all` exits 0 without ratchet increase.
- `python scripts/ops/run_backend_regression.py --deadline-seconds 7000` exits 0.
- `docs/ROADMAP.md` and `docs/HANDOFF.md` state the completed P1 scope and the explicit Workstream 10 residual debt.
- Worktree is clean; implementation is committed locally; nothing is pushed or deployed.

## KẾT QUẢ

- Historical implementation lineage: destination policy `660ec004`; pinned sockets and peer verification `073a50e6`; redirect-safe client `c46c936d`; admin adapter `21930353`; auto-learn adapter `e4f54a01`; quality-burst adapter `2e67ca0b`; adversarial address-policy correction `fabb156b`; consumer registry `9f314e32` plus enforcement correction `59d0009b`; verification truth-sync `407c7a13`.
- Bound-complete follow-up lineage: body/decompression bounds `ea2822d1`; bounded DNS `8ae23153` plus saturation coverage `271e2653`; whole-chain deadline `286c021a`, boundary correction `a05d6784`, and connect-timeout recomputation `6d3e43fb`; real transport edges `a83e48fd`, deadline-limited read mapping `6387a246`, and timeout/cleanup correction `be94c629`; explicit consumer profiles `dab48771`.
- Final verified implementation revision: `dab4877163280a6476180e0ad285280e405af1b4`.
- Focused pinned gate: `python -m pytest tests/test_pinned_http.py tests/test_admin_pinned_http.py tests/test_auto_learn_fetch.py tests/test_gpt55_quality_burst.py tests/test_pinned_http_consumers.py -q` -> exit `0`; `303 passed in 22.36s`.
- Frontend gates from `web-nuxt`: `npm test` -> exit `0`, `37` files and `912` tests passed in `28.66s`; `npm run typecheck` -> exit `0`, no diagnostics; `npm run build` -> exit `0`, `746 modules transformed`, `Σ Total size: 6.45 MB (1.62 MB gzip)`, launch-readiness manifest generated for `dab4877163280a6476180e0ad285280e405af1b4` (existing sourcemap, chunk-size, and Node `DEP0155` warnings remain non-fatal).
- Repository gates: `python scripts/checks/run_hard.py --all` -> exit `0`, `hard=0`, ratchet không tăng (R50.3 improved from baseline `8` to `7`); `git diff --check` -> exit `0`.
- Official bounded backend gate: `python scripts/ops/run_backend_regression.py --deadline-seconds 7000` -> exit `0` in `6901.2s`; Phase A exit `0`, `8633 passed, 58 skipped, 111 deselected, 1 xfailed, 1 warning in 1152.25s`; Phase B exit `0`, `284 passed, 19 skipped in 5739.98s`. Captured UTF-8/CRLF receipts: stdout `10840` bytes, SHA-256 `f11b8db7d11fe8925c9ce582eff85e73ab546a8578d82f75628d8a80ac5e8b2a`; stderr `300` bytes, SHA-256 `adf1dff1272e2cc714b37a623c093f3234de49875a91888173ed88b6b1e48169`.
- Genuine residuals: blocked destinations, peer mismatches, and redirect denials remain operationally silent; cookie/consent redirect gates that require a cookie jar remain incompatible; outbound callers excluded by this GET-only spec remain unmigrated; production behavior remains unobserved until a separately authorized deployment.
- Operational non-actions: no DB or `web/data.json` rewrite, no secret or indexing change, no push, no deploy, and no production mutation; pre-existing `agent/knowledge.db-shm` and `agent/knowledge.db-wal` remained untouched.
