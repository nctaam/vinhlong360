"""Shared DNS-pinned, redirect-safe synchronous HTTP GET client — destination policy.

This module implements a complete shared outbound HTTP egress boundary:
immutable dataclass contracts, the exception hierarchy, URL parsing/authority
policy, the public-address resolver (rejecting IPv6 transition forms and
reserved/deprecated ranges that ipaddress.is_global still reports as global),
a pinned-socket httpx transport that dials only pre-approved
addresses and verifies the connected peer, and `PinnedHTTPClient` — the
public synchronous GET entry point with a manual, per-hop-revalidating
redirect loop. Every redirect hop is re-resolved and re-checked against the
same public-address policy before it is followed.

Consumers wired to this boundary (see tests/test_pinned_http_consumers.py,
which locks the mapping):

- ``admin._approve_fetch_image_data`` — admin image-suggestion review
- ``auto_learn.fetch_url`` — auto-learn source ingestion
- ``gpt55_quality_burst.fetch_url_text`` — quality-burst source verification

Other outbound callers (crawler, geocode, realtime, bot, moderation, DDGS,
OpenAI clients) are deliberately NOT routed through here yet; that migration
is tracked as residual egress debt, not an oversight.
"""

from __future__ import annotations

import ipaddress
import select
import socket
import ssl
import threading
import time
import zlib
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Protocol

import httpcore
import httpx


MonotonicClock = Callable[[], float]


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


class PinnedBodyLimitError(PinnedHTTPError):
    pass


class PinnedContentEncodingError(PinnedHTTPError):
    pass


class PinnedDeadlineExceeded(PinnedTransportError):
    pass


class ResolverSaturatedError(PinnedTransportError):
    pass


@dataclass(frozen=True)
class EgressPolicy:
    max_encoded_bytes: int
    max_decoded_bytes: int
    accepted_encodings: tuple[str, ...]
    inactivity_timeout_seconds: float
    total_timeout_seconds: float
    max_redirects: int

    def __post_init__(self) -> None:
        if self.max_encoded_bytes <= 0 or self.max_decoded_bytes <= 0:
            raise ValueError("egress byte limits must be positive")
        if self.inactivity_timeout_seconds <= 0 or self.total_timeout_seconds <= 0:
            raise ValueError("egress timeouts must be positive")
        if self.max_redirects < 0:
            raise ValueError("max_redirects cannot be negative")
        if not self.accepted_encodings:
            raise ValueError("at least one content encoding is required")
        if len(set(self.accepted_encodings)) != len(self.accepted_encodings):
            raise ValueError("content encodings must be unique")
        if any(token not in {"identity", "gzip"} for token in self.accepted_encodings):
            raise ValueError("unsupported content encoding policy")


@dataclass(frozen=True)
class DeadlineBudget:
    expires_at: float

    @classmethod
    def start(
        cls,
        total_timeout_seconds: float,
        *,
        monotonic: MonotonicClock | None = None,
    ) -> "DeadlineBudget":
        clock = monotonic or time.monotonic
        return cls(clock() + total_timeout_seconds)

    def remaining(
        self,
        *,
        monotonic: MonotonicClock | None = None,
    ) -> float:
        clock = monotonic or time.monotonic
        remaining = self.expires_at - clock()
        if remaining <= 0:
            raise PinnedDeadlineExceeded("pinned egress deadline exceeded")
        return remaining

    def socket_timeout(
        self,
        requested_timeout: float | None,
        inactivity_timeout_seconds: float,
        *,
        monotonic: MonotonicClock | None = None,
    ) -> float:
        values = [inactivity_timeout_seconds, self.remaining(monotonic=monotonic)]
        if requested_timeout is not None:
            values.append(requested_timeout)
        return min(values)


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
    def __call__(
        self,
        host: str,
        port: int,
        budget: DeadlineBudget,
    ) -> tuple[ResolvedAddress, ...]:
        raise NotImplementedError


class TransportFactory(Protocol):
    def __call__(
        self,
        hop: ResolvedHop,
        policy: EgressPolicy,
        budget: DeadlineBudget,
    ) -> httpx.BaseTransport:
        raise NotImplementedError


_HTTP_PORTS = {"http": 80, "https": 443}
_MAX_RESOLVER_THREADS = 4
_RESOLVER_SLOTS = threading.BoundedSemaphore(_MAX_RESOLVER_THREADS)
_NAT64_NETWORKS = (
    ipaddress.ip_network("64:ff9b::/96"),
    ipaddress.ip_network("64:ff9b:1::/48"),
)
# RFC 2765 IPv4-translated. Deliberately distinct from the IPv4-mapped
# ::ffff:0:0/96 that IPv6Address.ipv4_mapped reports: these are two different
# networks, and .ipv4_mapped is None throughout this one, so the mapped check
# below does not cover it even though it also embeds an IPv4 address.
_IPV4_TRANSLATED_NETWORK = ipaddress.ip_network("::ffff:0:0:0/96")
# Ranges that reach somewhere internal or unexpected but that
# ipaddress.is_global reports as global, so the is_global test cannot catch
# them. Mixing address families is safe: ip_network.__contains__ returns False
# for an address of the other version rather than raising.
_DENIED_NETWORKS = (
    # RFC 3879 deprecated IPv6 site-local. CPython 3.14 dropped this from
    # ipaddress._private_networks, so is_global became True for the whole /10 —
    # including fec0:0:0:ffff::/64, the historical Windows default resolvers.
    ipaddress.ip_network("fec0::/10"),
    # RFC 7526 deprecated 6to4 relay anycast: the IPv4 peer of the 2002::/16
    # form that IPv6Address.sixtofour already rejects. sixtofour only ever sees
    # the IPv6 side, so denying it alone left the mechanism half-open.
    ipaddress.ip_network("192.88.99.0/24"),
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
        or address in _IPV4_TRANSLATED_NETWORK
        or address in ipaddress.ip_network("::/96")
        or any(address in network for network in _NAT64_NETWORKS)
        or address.sixtofour is not None
        or address.teredo is not None
        or _is_isatap(address)
    )


def _is_denied_network(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return any(address in network for network in _DENIED_NETWORKS)


def _require_allowed_ip(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> None:
    if isinstance(address, ipaddress.IPv6Address) and _is_transition_address(address):
        raise BlockedAddressError(f"IPv6 transition address denied: {address}")
    if _is_denied_network(address):
        raise BlockedAddressError(f"reserved or deprecated address denied: {address}")
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


def _gated_getaddrinfo(
    host: str,
    port: int,
    budget: DeadlineBudget,
) -> list[tuple]:
    try:
        acquired = _RESOLVER_SLOTS.acquire(timeout=budget.remaining())
    except PinnedDeadlineExceeded as exc:
        raise ResolverSaturatedError("resolver gate deadline exceeded") from exc
    if not acquired:
        raise ResolverSaturatedError("resolver capacity exhausted")

    completed = threading.Event()
    state: dict[str, object] = {}

    def resolve() -> None:
        try:
            state["answers"] = socket.getaddrinfo(
                host,
                port,
                type=socket.SOCK_STREAM,
                proto=socket.IPPROTO_TCP,
            )
        except BaseException as exc:
            state["error"] = exc
        finally:
            _RESOLVER_SLOTS.release()
            completed.set()

    try:
        threading.Thread(
            target=resolve,
            name="vinhlong360-pinned-dns",
            daemon=True,
        ).start()
    except BaseException:
        _RESOLVER_SLOTS.release()
        raise

    if not completed.wait(timeout=budget.remaining()):
        raise PinnedDeadlineExceeded("DNS resolution deadline exceeded")
    error = state.get("error")
    if error is not None:
        raise ResolutionError(f"failed to resolve {host}") from error
    return list(state["answers"])


def resolve_public_addresses(
    host: str,
    port: int,
    budget: DeadlineBudget,
) -> tuple[ResolvedAddress, ...]:
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None

    if literal is not None:
        _require_allowed_ip(literal)
        family = socket.AF_INET6 if literal.version == 6 else socket.AF_INET
        sockaddr = (str(literal), port, 0, 0) if family == socket.AF_INET6 else (str(literal), port)
        return (_resolved_address(family, socket.SOCK_STREAM, socket.IPPROTO_TCP, sockaddr),)

    answers = _gated_getaddrinfo(host, port, budget)

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
    budget: DeadlineBudget | None = None,
) -> None:
    active_budget = budget or DeadlineBudget.start(15.0)
    parsed = _parse_url(url)
    port = parsed.port or _HTTP_PORTS[parsed.scheme]
    if not resolver(_ascii_host(parsed), port, active_budget):
        raise ResolutionError("resolver returned no usable addresses")


class _PinnedNetworkStream(httpcore.NetworkStream):
    def __init__(
        self,
        sock: socket.socket,
        *,
        policy: EgressPolicy,
        budget: DeadlineBudget,
        monotonic: MonotonicClock = time.monotonic,
    ) -> None:
        self._socket = sock
        self._policy = policy
        self._budget = budget
        self._monotonic = monotonic

    def read(self, max_bytes: int, timeout: float | None = None) -> bytes:
        try:
            operation_timeout = self._budget.socket_timeout(
                timeout,
                self._policy.inactivity_timeout_seconds,
                monotonic=self._monotonic,
            )
            self._socket.settimeout(operation_timeout)
            return self._socket.recv(max_bytes)
        except socket.timeout as exc:
            self._budget.remaining(monotonic=self._monotonic)
            raise httpcore.ReadTimeout(str(exc)) from exc
        except OSError as exc:
            raise httpcore.ReadError(str(exc)) from exc

    def write(self, buffer: bytes, timeout: float | None = None) -> None:
        try:
            while buffer:
                operation_timeout = self._budget.socket_timeout(
                    timeout,
                    self._policy.inactivity_timeout_seconds,
                    monotonic=self._monotonic,
                )
                self._socket.settimeout(operation_timeout)
                written = self._socket.send(buffer)
                if written == 0:
                    raise httpcore.WriteError("socket connection broken")
                buffer = buffer[written:]
        except socket.timeout as exc:
            self._budget.remaining(monotonic=self._monotonic)
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
            operation_timeout = self._budget.socket_timeout(
                timeout,
                self._policy.inactivity_timeout_seconds,
                monotonic=self._monotonic,
            )
            self._socket.settimeout(operation_timeout)
            wrapped = ssl_context.wrap_socket(
                self._socket,
                server_hostname=server_hostname,
            )
        except socket.timeout as exc:
            self.close()
            self._budget.remaining(monotonic=self._monotonic)
            raise httpcore.ConnectTimeout(str(exc)) from exc
        except (ssl.SSLError, OSError) as exc:
            self.close()
            raise httpcore.ConnectError(str(exc)) from exc
        return _PinnedNetworkStream(
            wrapped,
            policy=self._policy,
            budget=self._budget,
            monotonic=self._monotonic,
        )

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


SocketOption = (
    tuple[int, int, int]
    | tuple[int, int, bytes | bytearray]
    | tuple[int, int, None, int]
)
SocketFactory = Callable[[int, int, int], socket.socket]


def _normalize_peer(
    peer: tuple,
) -> tuple[ipaddress.IPv4Address | ipaddress.IPv6Address, int]:
    return ipaddress.ip_address(peer[0].split("%", 1)[0]), int(peer[1])


def _check_requested_origin(host: str, port: int, hop: ResolvedHop) -> None:
    if host != hop.host or port != hop.port:
        raise PeerMismatchError("httpcore requested an origin outside the pinned hop")


def _remaining_timeout(deadline: float | None, monotonic: MonotonicClock) -> float | None:
    return None if deadline is None else max(0.0, deadline - monotonic())


def _configure_connecting_socket(
    sock: socket.socket,
    remaining: float | None,
    local_address: str | None,
    socket_options: Iterable[SocketOption] | None,
) -> None:
    sock.settimeout(remaining)
    if local_address is not None:
        sock.bind((local_address, 0))
    for option in socket_options or ():
        sock.setsockopt(*option)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)


def _check_peer_matches_approved(
    sock: socket.socket,
    approved: set[tuple[ipaddress.IPv4Address | ipaddress.IPv6Address, int]],
) -> None:
    peer_ip, peer_port = _normalize_peer(sock.getpeername())
    if (peer_ip, peer_port) not in approved:
        raise PeerMismatchError(f"peer {peer_ip}:{peer_port} is outside the pinned set")


def _raise_pinned_connect_error(last_error: Exception | None) -> None:
    if isinstance(last_error, httpcore.TimeoutException):
        raise last_error
    if isinstance(last_error, httpcore.NetworkError):
        raise last_error
    raise httpcore.ConnectError("all pinned addresses failed")


class _PinnedNetworkBackend(httpcore.NetworkBackend):
    def __init__(
        self,
        hop: ResolvedHop,
        *,
        policy: EgressPolicy,
        budget: DeadlineBudget,
        socket_factory: SocketFactory = socket.socket,
        monotonic: MonotonicClock = time.monotonic,
    ) -> None:
        self._hop = hop
        self._policy = policy
        self._budget = budget
        self._socket_factory = socket_factory
        self._monotonic = monotonic

    def connect_unix_socket(
        self,
        path: str,
        timeout: float | None = None,
        socket_options: Iterable[SocketOption] | None = None,
    ) -> httpcore.NetworkStream:
        raise httpcore.UnsupportedProtocol("pinned HTTP supports TCP only")

    def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[SocketOption] | None = None,
    ) -> httpcore.NetworkStream:
        _check_requested_origin(host, port, self._hop)
        approved = {(item.ip, item.port) for item in self._hop.addresses}
        last_error: Exception | None = None
        for address in self._hop.addresses:
            self._budget.socket_timeout(
                timeout,
                self._policy.inactivity_timeout_seconds,
                monotonic=self._monotonic,
            )
            sock: socket.socket | None = None
            try:
                sock = self._socket_factory(address.family, address.socktype, address.protocol)
                operation_timeout = self._budget.socket_timeout(
                    timeout,
                    self._policy.inactivity_timeout_seconds,
                    monotonic=self._monotonic,
                )
                _configure_connecting_socket(
                    sock,
                    operation_timeout,
                    local_address,
                    socket_options,
                )
                sock.connect(address.sockaddr)
                _check_peer_matches_approved(sock, approved)
                return _PinnedNetworkStream(
                    sock,
                    policy=self._policy,
                    budget=self._budget,
                    monotonic=self._monotonic,
                )
            except PinnedDeadlineExceeded:
                if sock is not None:
                    sock.close()
                raise
            except PeerMismatchError:
                if sock is not None:
                    sock.close()
                raise
            except socket.timeout as exc:
                self._budget.remaining(monotonic=self._monotonic)
                last_error = httpcore.ConnectTimeout(str(exc))
                if sock is not None:
                    sock.close()
            except OSError as exc:
                last_error = httpcore.ConnectError(str(exc))
                if sock is not None:
                    sock.close()
        _raise_pinned_connect_error(last_error)


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
    def __init__(
        self,
        hop: ResolvedHop,
        *,
        policy: EgressPolicy,
        budget: DeadlineBudget,
        socket_factory: SocketFactory = socket.socket,
        monotonic: MonotonicClock = time.monotonic,
    ) -> None:
        self._pool = httpcore.ConnectionPool(
            ssl_context=httpx.create_ssl_context(verify=True, trust_env=False),
            max_connections=1,
            max_keepalive_connections=0,
            http1=True,
            http2=False,
            retries=0,
            network_backend=_PinnedNetworkBackend(
                hop,
                policy=policy,
                budget=budget,
                socket_factory=socket_factory,
                monotonic=monotonic,
            ),
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


def build_pinned_transport(
    hop: ResolvedHop,
    policy: EgressPolicy,
    budget: DeadlineBudget,
) -> httpx.BaseTransport:
    return _PinnedHTTPTransport(hop, policy=policy, budget=budget)


def _resolve_hop(
    url: str | httpx.URL,
    resolver: Resolver,
    budget: DeadlineBudget,
) -> ResolvedHop:
    parsed = _parse_url(str(url))
    port = parsed.port or _HTTP_PORTS[parsed.scheme]
    host = _ascii_host(parsed)
    addresses = resolver(host, port, budget)
    if not addresses:
        raise ResolutionError("resolver returned no usable addresses")
    return ResolvedHop(url=parsed, host=host, port=port, addresses=addresses)


def _response_encoding(headers: httpx.Headers) -> str:
    values = headers.get_list("content-encoding")
    if not values:
        return "identity"
    tokens = [token.strip().lower() for value in values for token in value.split(",")]
    if len(tokens) != 1 or not tokens[0]:
        raise PinnedContentEncodingError("stacked or malformed content encoding")
    return tokens[0]


def _content_length_hint(headers: httpx.Headers) -> int | None:
    value = headers.get("content-length")
    if value is None:
        return None
    try:
        parsed = int(value, 10)
    except ValueError:
        return None
    return parsed if parsed >= 0 else None


def _bounded_raw_chunks(response: httpx.Response, policy: EgressPolicy):
    encoded = 0
    for chunk in response.iter_raw():
        encoded += len(chunk)
        if encoded > policy.max_encoded_bytes:
            raise PinnedBodyLimitError("encoded response body exceeds policy")
        yield chunk


def _append_decoded(output: bytearray, chunk: bytes, limit: int) -> None:
    if len(chunk) > limit - len(output):
        raise PinnedBodyLimitError("decoded response body exceeds policy")
    output.extend(chunk)


def _decode_identity(
    chunks: Iterable[bytes],
    policy: EgressPolicy,
    budget: DeadlineBudget,
    monotonic: MonotonicClock,
) -> bytes:
    output = bytearray()
    for chunk in chunks:
        budget.remaining(monotonic=monotonic)
        _append_decoded(output, chunk, policy.max_decoded_bytes)
    return bytes(output)


def _decode_gzip(
    chunks: Iterable[bytes],
    policy: EgressPolicy,
    budget: DeadlineBudget,
    monotonic: MonotonicClock,
) -> bytes:
    decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
    output = bytearray()
    try:
        for chunk in chunks:
            budget.remaining(monotonic=monotonic)
            remaining = policy.max_decoded_bytes - len(output)
            decoded = decoder.decompress(chunk, remaining + 1)
            if len(decoded) > remaining or decoder.unconsumed_tail:
                raise PinnedBodyLimitError("decoded response body exceeds policy")
            _append_decoded(output, decoded, policy.max_decoded_bytes)
            if decoder.unused_data:
                raise PinnedContentEncodingError("gzip has trailing or concatenated data")
        budget.remaining(monotonic=monotonic)
        remaining = policy.max_decoded_bytes - len(output)
        tail = decoder.flush(remaining + 1)
    except zlib.error as exc:
        raise PinnedContentEncodingError("malformed gzip response") from exc
    if len(tail) > remaining:
        raise PinnedBodyLimitError("decoded response body exceeds policy")
    _append_decoded(output, tail, policy.max_decoded_bytes)
    if not decoder.eof:
        raise PinnedContentEncodingError("truncated gzip response")
    if decoder.unused_data:
        raise PinnedContentEncodingError("gzip has trailing or concatenated data")
    return bytes(output)


def _read_bounded_body(
    response: httpx.Response,
    *,
    policy: EgressPolicy,
    budget: DeadlineBudget,
    monotonic: MonotonicClock = time.monotonic,
) -> bytes:
    hint = _content_length_hint(response.headers)
    if hint is not None and hint > policy.max_encoded_bytes:
        raise PinnedBodyLimitError("content-length exceeds encoded policy")
    encoding = _response_encoding(response.headers)
    if encoding not in policy.accepted_encodings:
        raise PinnedContentEncodingError("response content encoding is not accepted")
    # Mock transports may return an already-buffered response body.
    if response.is_stream_consumed:
        buffered = response.content
        if len(buffered) > policy.max_encoded_bytes:
            raise PinnedBodyLimitError("encoded response body exceeds policy")
        chunks = [buffered]
    else:
        chunks = _bounded_raw_chunks(response, policy)
    if encoding == "identity":
        return _decode_identity(chunks, policy, budget, monotonic)
    return _decode_gzip(chunks, policy, budget, monotonic)


def _fetch_hop(
    hop: ResolvedHop,
    *,
    user_agent: str,
    policy: EgressPolicy,
    budget: DeadlineBudget,
    timeout: float | httpx.Timeout | None = None,
    transport_factory: TransportFactory,
    monotonic: MonotonicClock = time.monotonic,
) -> tuple[int, tuple[tuple[str, str], ...], bytes, str | None]:
    try:
        budget.remaining(monotonic=monotonic)
        transport = transport_factory(hop, policy, budget)
        with httpx.Client(
            transport=transport,
            follow_redirects=False,
            trust_env=False,
            headers={
                "User-Agent": user_agent,
                "Accept-Encoding": ", ".join(policy.accepted_encodings),
            },
        ) as client:
            # Built via the client (for default-header merging and timeout-extension
            # conversion) but dispatched straight to the transport: httpx.Client.send()
            # unconditionally pre-builds the (unfollowed) redirect request whenever a
            # response carries a redirect status + Location header, even with
            # follow_redirects=False, and raises RemoteProtocolError for a malformed
            # Location before this function ever sees it. Calling the transport
            # directly keeps this module the sole arbiter of redirect-target validity.
            request = client.build_request(
                "GET",
                str(hop.url),
                timeout=httpx.Timeout(policy.inactivity_timeout_seconds),
            )
            response = transport.handle_request(request)
            try:
                location = response.headers.get("location")
                if response.status_code in {301, 302, 303, 307, 308} and location and location.strip():
                    budget.remaining(monotonic=monotonic)
                    return response.status_code, tuple(response.headers.multi_items()), b"", location.strip()
                budget.remaining(monotonic=monotonic)
                headers = tuple(response.headers.multi_items())
                content = _read_bounded_body(
                    response,
                    policy=policy,
                    budget=budget,
                    monotonic=monotonic,
                )
                return response.status_code, headers, content, None
            finally:
                response.close()
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


def _transitional_policy(
    *,
    timeout: float | httpx.Timeout | None,
    max_redirects: int | None,
) -> EgressPolicy:
    seconds = float(timeout) if isinstance(timeout, (int, float)) else 15.0
    return EgressPolicy(
        max_encoded_bytes=12 * 1024 * 1024,
        max_decoded_bytes=12 * 1024 * 1024,
        accepted_encodings=("gzip", "identity"),
        inactivity_timeout_seconds=max(seconds, 0.001),
        total_timeout_seconds=max(seconds, 0.001),
        max_redirects=max(0, max_redirects if max_redirects is not None else 5),
    )


class PinnedHTTPClient:
    def __init__(
        self,
        *,
        resolver: Resolver = resolve_public_addresses,
        transport_factory: TransportFactory = build_pinned_transport,
        monotonic: MonotonicClock = time.monotonic,
    ) -> None:
        self._resolver = resolver
        self._transport_factory = transport_factory
        self._monotonic = monotonic

    def get(
        self,
        url: str,
        *,
        user_agent: str,
        policy: EgressPolicy | None = None,
        timeout: float | httpx.Timeout | None = None,
        max_redirects: int | None = None,
    ) -> PinnedResponse:
        if policy is None:
            policy = _transitional_policy(timeout=timeout, max_redirects=max_redirects)
        budget = DeadlineBudget.start(
            policy.total_timeout_seconds,
            monotonic=self._monotonic,
        )
        current = _parse_url(url)
        visited: set[tuple[str, str, int, bytes]] = set()
        redirects: list[RedirectHop] = []
        while True:
            budget.remaining(monotonic=self._monotonic)
            key = _canonical_url_key(current)
            if key in visited:
                raise RedirectPolicyError("redirect loop detected")
            visited.add(key)
            hop = _resolve_hop(current, self._resolver, budget)
            status, headers, content, location = _fetch_hop(
                hop,
                user_agent=user_agent,
                policy=policy,
                budget=budget,
                timeout=timeout,
                transport_factory=self._transport_factory,
                monotonic=self._monotonic,
            )
            if location is None:
                budget.remaining(monotonic=self._monotonic)
                return PinnedResponse(status, str(hop.url), headers, content, tuple(redirects))
            if len(redirects) >= policy.max_redirects:
                raise RedirectPolicyError("redirect limit exceeded")
            budget.remaining(monotonic=self._monotonic)
            next_url = _redirect_target(hop.url, location)
            redirects.append(RedirectHop(str(hop.url), status, location, str(next_url)))
            current = next_url
