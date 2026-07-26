> STATUS: active - design approved on 2026-07-26; implements Workstream 7 of the security remediation plan without expanding the mapped outbound-fetch scope.

# Shared Pinned Outbound HTTP Client Design

## 1. Context and goal

The three mapped remote-fetch paths currently delegate DNS resolution and redirects to general-purpose HTTP libraries:

- `agent/admin.py` resolves a candidate image URL in `_assert_public_url()`, then `httpx.get()` resolves it again when connecting.
- `agent/auto_learn.py` calls `httpx.get(..., follow_redirects=True)` on search-result URLs.
- `agent/gpt55_quality_burst.py` calls `requests.get()` on source URLs that may originate from search results or LLM output.

The admin preflight blocks obvious internal addresses, but the separate validation and connection resolutions leave a DNS-rebinding/TOCTOU window. The other two consumers do not apply a destination-address policy at all. Automatic redirects can also move a request to a destination that was never approved by the caller.

The goal is one synchronous, reusable outbound GET boundary that resolves each redirect hop once, rejects any non-public answer, connects only to that approved address set, verifies the actual peer before HTTP bytes are sent, and preserves normal HTTPS hostname verification. All three mapped fetches must use that boundary while retaining their consumer-specific status, logging, text-cleaning, and return-value behavior.

## 2. Decisions

1. Add `agent/pinned_http.py` as the single implementation authority for mapped public outbound GET requests.
2. Keep the API synchronous. Admin already offloads its network work to a thread pool, auto-learn is synchronous, and quality-burst performs synchronous fetches inside worker threads.
3. Use a small `httpx.BaseTransport` adapter backed by `httpcore.ConnectionPool(network_backend=...)`. Declare `httpx>=0.28,<1` and `httpcore>=1.0.9,<2` as direct runtime compatibility ranges because the project will intentionally depend on both transport contracts.
4. Parse, resolve, classify, pin, connect, and verify a fresh address set for every redirect hop. Never reuse a connection pool between hops, including redirects back to the same hostname.
5. Keep the original hostname in the request origin. The pinned backend substitutes only the TCP destination address, so the HTTP `Host` header, TLS SNI, and certificate hostname validation continue to use the original hostname.
6. Disable automatic redirects, ambient proxies, ambient `NO_PROXY` decisions, and HTTP-layer retries. The shared client owns the redirect loop and uses `trust_env=False`.
7. Default to at most five followed redirects after the initial request. This matches the existing admin contract and deliberately tightens the much larger library defaults in the two batch consumers.
8. Return an immutable buffered response containing status, final URL, headers, HTTP-decoded entity-body bytes, and redirect metadata. Status acceptance and character-set decoding remain consumer responsibilities.
9. Preserve current response buffering and consumer-side truncation/size checks. Moving body limits into streaming resource enforcement belongs to Workstream 10 and is not mixed into the P1 destination-authority change.
10. Use typed shared exceptions. The shared module does not log, translate errors to FastAPI responses, or silently swallow failures.

## 3. Public contract

The focused public surface is:

```python
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
    def __call__(self, host: str, port: int) -> tuple[ResolvedAddress, ...]: ...


class TransportFactory(Protocol):
    def __call__(self, hop: ResolvedHop) -> httpx.BaseTransport: ...


class PinnedHTTPClient:
    def __init__(
        self,
        *,
        resolver: Resolver = resolve_public_addresses,
        transport_factory: TransportFactory = build_pinned_transport,
    ) -> None: ...

    def get(
        self,
        url: str,
        *,
        user_agent: str,
        timeout: float | httpx.Timeout = 15.0,
        max_redirects: int = 5,
    ) -> PinnedResponse: ...


def validate_public_url(
    url: str,
    *,
    resolver: Resolver = resolve_public_addresses,
) -> None: ...
```

`ResolvedAddress` is an internal frozen record containing the normalized IP, port, address family, socket type, protocol, and exact resolver-provided socket address. `ResolvedHop` is an internal frozen record containing the normalized request URL, canonical ASCII hostname, effective port, and ordered `ResolvedAddress` tuple. The production transport factory builds the pinned backend for that exact record; tests may replace it with a deterministic one-hop transport.

`PinnedHTTPClient` is stateless across calls. Resolver and transport factories are constructor dependencies with production defaults so unit tests can inject deterministic fakes without opening sockets. Per-call redirect state, pinned addresses, response data, and clients remain local variables, making one client instance safe for concurrent calls from thread pools.

The mapped consumers require only a User-Agent override, so the public API does not accept arbitrary request headers. This prevents callers from overriding `Host` or forwarding cookies, authorization, proxy credentials, and other authority-bearing headers across redirects. The transport creates the `Host` header from the validated original URL.

`validate_public_url()` exists only for the admin endpoint that validates and stores an external image URL without fetching it. It applies the same parsing, DNS, and address policy, but its result is explicitly not reusable as authorization for a later network request. Any later server-side fetch must call `get()` and perform a new atomic resolve-and-connect flow.

The response's `content` is the HTTPX-decoded entity body after HTTP `Content-Encoding` decompression but before character-set decoding. Its headers are an immutable ordered tuple that preserves duplicates. The response carries bytes and headers instead of a shared `.text` decision because current httpx and Requests charset fallbacks differ. Each consumer keeps its current decoding behavior, backed by fixtures for declared UTF-8, declared legacy charset, and missing charset.

## 4. URL, DNS, and address policy

Every initial URL and redirect target is parsed with `httpx.URL` and normalized before resolution.

- Allow only absolute `http` and `https` URLs with a non-empty hostname and a valid port.
- Reject usernames, passwords, zone identifiers, malformed authorities, unsupported schemes, and invalid ports.
- Remove fragments before comparison and transmission because fragments are not part of an HTTP request target.
- Resolve with `socket.getaddrinfo(host, port, type=SOCK_STREAM, proto=IPPROTO_TCP)` and preserve the first-seen address order after deduplication.
- Normalize IPv4 and IPv6 addresses before classification and peer comparison. Reject IPv4-mapped, IPv4-compatible (`::/96`), well-known/local NAT64 (`64:ff9b::/96`, `64:ff9b:1::/48`), 6to4, Teredo, and ISATAP forms rather than trusting the translated IPv6 peer as proof of the embedded IPv4 destination.
- Require every remaining resolved address to be globally routable according to `ipaddress.ip_address(...).is_global`. This fails closed for private, loopback, link-local, reserved/documentation, multicast, unspecified, carrier-grade NAT, and other non-global ranges.
- Reject the entire hop when resolution returns no usable addresses or a mixed public/non-public set. The client never selects only the public subset from a mixed answer.
- Accept a literal IP only when that literal itself passes the same global-address policy.

DNS is performed exactly once per hop. Connection failures may advance to another address from that same pinned set, preserving resolver order, but must never trigger an implicit or explicit re-resolution.

The deployment egress contract must not route additional private/custom IPv6 translation prefixes. Introducing such a prefix requires adding it to the denied transition-prefix policy and its tests before rollout; the application cannot infer an arbitrary operator-defined translator from the destination address alone.

## 5. Pinned transport and TLS flow

For each hop, the client constructs a fresh `PinnedNetworkBackend` and a one-hop HTTP transport:

1. The resolver produces an immutable ordered set of approved numeric addresses for the URL's original hostname and effective port.
2. `httpcore` builds the HTTP connection using the original URL origin.
3. When `httpcore` calls `connect_tcp(original_host, port, ...)`, the pinned backend verifies the requested host and port match the approved hop, ignores DNS for dialing, and attempts only the pre-resolved numeric addresses.
4. The backend opens a socket for the stored address family, applies the timeout and requested socket options, and calls `connect()` with the exact resolver-provided socket address; it must not call a hostname resolver or `socket.create_connection()`. A focused local `httpcore.NetworkStream` wrapper owns read, write, close, peer-info, and TLS-upgrade operations for that socket. Immediately after each successful TCP connect, the backend reads the peer address, normalizes the peer IP and port, and requires them to belong to the approved set. A mismatch closes the stream and raises `PeerMismatchError` before the backend returns, so no TLS or HTTP request bytes are sent through an unapproved peer.
5. For HTTPS, `httpcore` subsequently calls `start_tls(..., server_hostname=original_host)`. The standard verified SSL context remains enabled; certificate or hostname failures are never retried insecurely.
6. The HTTP request retains the original hostname in the URL and `Host` header. The numeric pinned address never leaks into application-visible URL semantics.

The transport uses HTTP/1.1, one connection, no keep-alive retention after the hop, no proxy, and zero transport retries. Low-level connect attempts may try the next address in the already-approved set, but no connection can leave that set. All address attempts within one hop share one monotonic connect-time budget; each next attempt receives only the remaining connect timeout rather than resetting the full timeout per address.

The implementation will keep its `httpcore` adapter small and isolated. Contract tests will pin the constructor and stream methods the adapter relies on, so an incompatible dependency upgrade fails in CI instead of silently disabling pinning.

## 6. Redirect and response flow

The client sends each request with automatic redirects disabled. Redirect handling recognizes the standard GET redirect statuses `301`, `302`, `303`, `307`, and `308` when a non-blank `Location` header is present. Restricting admin's previous broad `300 <= status < 400` condition to the standard redirect statuses is an intentional tightening; `300`, `304`, `305`, and unassigned 3xx responses become final responses.

1. Resolve, validate, pin, and fetch the current URL.
2. If the response is a recognized redirect with non-blank `Location`, close that hop without retaining its pool, resolve the target with `httpx.URL(current_url).join(location)`, and run the complete URL/DNS/address policy again.
3. Relative, absolute, scheme-relative, same-host, cross-host, HTTP-to-HTTPS, and HTTPS-to-HTTP redirects all follow the same path. Allowing HTTPS-to-HTTP preserves current library behavior; the target still receives the full public-destination policy. Redirects may not inherit an old DNS result, connection, cookie, authorization, or other authority-bearing header.
4. Canonicalize every visited URL with HTTPX, strip its fragment, lowercase and IDNA-normalize the host, replace an omitted port with the scheme default, and use `(scheme, canonical_host, effective_port, raw_path)` as the loop-comparison key. In HTTPX 0.28, `raw_path` includes the raw query string; percent-encoded request-target bytes remain byte-distinct unless HTTPX itself normalizes them. An absent or whitespace-only `Location` makes the response final; a fragment-only or otherwise repeated canonical target raises `RedirectPolicyError`.
5. Reject malformed targets, credentials introduced by a redirect, repeated canonical keys, and more than five followed redirects with `RedirectPolicyError`.
6. A 3xx response without a usable redirect location is a final response. The consumer's existing status policy decides whether it is useful or an error.
7. For a final response, read the decoded HTTPX body into a buffer, matching the current consumers' eager-response behavior.
8. Close the hop client and pool before returning the fully buffered immutable response. Callers may safely inspect content after closure.

The `timeout` argument keeps the consumers' current per-operation timeout model. It is applied to connect, TLS, read, and write operations for each hop. A single monotonic deadline spanning DNS and the whole redirect chain is intentionally deferred to Workstream 10; the five-redirect cap bounds the P1 chain.

## 7. Error model

The module defines this exact narrow hierarchy:

```text
PinnedHTTPError
|- DestinationPolicyError
|  |- InvalidDestinationError
|  |- ResolutionError
|  |- BlockedAddressError
|  `- PeerMismatchError
|- RedirectPolicyError
`- PinnedTransportError
```

`InvalidDestinationError` covers malformed/unsupported URLs and credentials. `ResolutionError` covers resolver failure or no usable answer. `BlockedAddressError` covers non-global and mixed answer sets. `PeerMismatchError(DestinationPolicyError)` covers an actual peer outside the pinned set. `RedirectPolicyError` covers malformed targets, loops, and redirect-limit overflow. `PinnedTransportError` covers connect, TLS, protocol, read, and other upstream transport failures.

HTTP status codes are not shared-client exceptions. Consumers retain their existing status contracts. The shared module catches the underlying `httpx`/`httpcore` exception set and exposes stable typed failures without logging URL bodies, headers, or secrets.

## 8. Consumer migrations

### Admin image approval

- Remove the separate `_assert_public_url()` call before `_approve_fetch_image_data()` and replace `_fetch_public_url()` with one pinned `get()` call inside the existing thread-pool boundary.
- Pass the current fixed User-Agent, timeout `25`, and redirect limit `5`.
- Reconstruct a status-only offline `httpx.Response` from the pinned status, final URL, and headers, attach an equivalent GET request, and call `raise_for_status()` so final status acceptance remains identical to the current code. Do not feed the already HTTP-decoded body through HTTPX a second time. Preserve empty-body rejection, the 12 MiB error message, downstream PIL validation/re-encoding, and all state transitions.
- Apply the existing empty-body and `MAX_IMAGE_SIZE` checks after the buffered response. Map destination and redirect policy failures to HTTP 400. Map transport, TLS, protocol, and final HTTP-status failures to the existing HTTP 502 response.
- Keep the suggestion pending and perform no upload, entity mutation, credit write, or approval mark after any fetch failure.
- Continue recording the original licensed `candidate_url` in image credits rather than the final redirected URL.
- Replace the non-fetching `add_entity_image_url()` preflight with `validate_public_url()` for external URLs. Map every `DestinationPolicyError` to the current localized HTTP 400 URL/host-resolution/blocked-host responses; do not allow a shared exception to become HTTP 500. Do not make that endpoint download the URL.

### Auto-learn

- Replace `httpx.get(..., follow_redirects=True)` with pinned `get()` using the existing User-Agent and timeout `15`.
- Keep exact status acceptance at `200`; all other statuses return `None` without becoming shared transport policy.
- Reconstruct an offline `httpx.Response` with the already HTTP-decoded content and with `Content-Encoding`, `Content-Length`, and `Transfer-Encoding` removed from the copied headers, then use its `.text` property. This preserves HTTPX's declared-charset and UTF-8 fallback behavior without decompressing twice. Then remove script/style blocks and tags, normalize whitespace, and retain the 6,000-character output limit.
- Preserve warning logs containing the source URL for exceptions and preserve `None` on failure. The caller continues to discard empty or shorter-than-200-character content.

### GPT-5.5 quality burst

- Replace the network use of `requests.get()` with pinned `get()` using the existing User-Agent and timeout argument.
- Preserve `disabled`/`--no-web`, invalid-URL short-circuiting, acceptance of every status below 400, silent failure to an empty string, tag-only cleanup, and the 5,000-character output limit.
- Preserve Requests-compatible decoding by constructing an offline `requests.Response`, assigning the pinned headers and content, setting `encoding = requests.utils.get_encoding_from_headers(headers)`, and using its `.text` property so a missing charset retains Requests' apparent-encoding fallback. The shared transport does not choose a text encoding.
- Preserve the current optional-dependency guard: when `requests is None`, return an empty string without calling the pinned client. `requests.get()` disappears from this path, but the import remains for the legacy decoding contract and other repository consumers still require the package.
- URLs generated by search or an LLM still pass through the same pinned policy. Requiring an LLM URL to be a member of the preceding search result set is a separate provenance hardening task and is not part of P1.

## 9. Test strategy

Implementation follows TDD. Add focused shared-client tests before production code, using injected fake resolvers, backends/streams, and transport responses. No test in this tranche requires live DNS or network access.

Shared policy and transport tests must cover:

- allowed public IPv4, IPv6, multiple-address, and global literal-IP cases;
- blocked private, loopback, link-local, reserved/documentation, multicast, unspecified, carrier-grade NAT, mapped/compatible IPv4, NAT64, 6to4, Teredo, and ISATAP literals;
- embedded-internal translation forms in direct URLs, DNS answers, and redirect targets;
- all-public versus mixed public/non-public DNS answers;
- one DNS resolution per hop and dialing only addresses from that resolved set;
- fallback between approved addresses without re-resolution;
- actual peer match and mismatch, including stream closure before request handling;
- original HTTP `Host`, TLS `server_hostname`, and certificate verification behavior;
- absence of environment proxy routing and insecure TLS fallback;
- relative, same-host, cross-host, and scheme-relative redirects;
- redirect to blocked or mixed addresses, redirect loops, malformed locations, and the five-redirect boundary;
- blank, fragment-only, default-port-equivalent, percent-encoding-distinct, HTTP-to-HTTPS, and HTTPS-to-HTTP redirect cases;
- final 3xx without `Location`;
- DNS, connect, TLS, read, and protocol exception translation;
- concurrent calls sharing one `PinnedHTTPClient` without pinned-set leakage.

Consumer tests must replace source-inspection-only assertions with behavioral contracts where possible:

- Admin maps policy/redirect and existing body-size errors to 400, maps upstream/status errors to 502, preserves async offload, and leaves all persistent state untouched on failure.
- Auto-learn preserves status, logging, charset, cleanup, truncation, and `None` behavior.
- Quality-burst preserves disabled mode, status, silent failure, charset, cleanup, truncation, and verification messages.
- Compressed response fixtures prove the shared layer performs HTTP content decoding exactly once before each consumer's character-set decoding.
- A registry/source contract confirms the three mapped call sites no longer call `httpx.get()` or `requests.get()` directly.

Focused tests include the new pinned-client module and the three consumer suites. After they pass, run `python scripts/checks/run_hard.py --all`, then run `python scripts/ops/run_backend_regression.py --deadline-seconds 7000` with an outer timeout greater than the runner's internal deadline.

## 10. Alternatives considered

1. **Keep preflight validation and improve `_assert_public_url()`.** Rejected because any design where the HTTP library resolves again retains the DNS-rebinding window.
2. **Rewrite the request URL to a numeric IP and set `Host` manually.** Rejected because it complicates HTTPS SNI and certificate validation, mishandles IPv6 and redirects easily, and exposes numeric-origin semantics to HTTPX.
3. **Build a complete HTTP/TLS client directly on sockets.** Rejected because it would duplicate mature HTTP parsing, decompression, timeout, and TLS behavior. The narrow custom backend preserves the required connection authority while retaining HTTPX/httpcore behavior.

## 11. Scope, non-goals, and rollback

In scope are the new focused module and tests, the three mapped consumers, the admin non-fetch validation compatibility call, the `httpx`/`httpcore` compatibility declarations in `requirements.txt`, and truth updates to `docs/ROADMAP.md` and `docs/HANDOFF.md` after implementation and verification.

Crawler, geocode, realtime, bot, moderation, search-provider internals, OpenAI clients, and other outbound modules are not migrated in this P1 tranche. The work does not add an outbound proxy service, allowlist, DNS-over-HTTPS resolver, global request deadline, streaming body cap, general response-size policy, content-type enforcement, authentication/cookie forwarding, asynchronous client, or production deployment change. Admin's current post-buffer 12 MiB check remains in place; Workstream 10 owns stopping oversized or compressed responses before unbounded allocation.

Each consumer migration should be a separable commit after the shared core and tests. If a compatibility failure cannot be resolved safely, revert that consumer commit while keeping the shared module unused by that path; never restore the split validate-then-resolve pattern as a partial fix. The completed tranche is accepted only when all three mapped remote fetches use the shared pinned client and the mock DNS/redirect/peer matrix passes.
