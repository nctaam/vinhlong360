# Bound-Complete Pinned Egress Implementation Plan

> STATUS: done - Plan A dependency, implementation, review corrections, and final local verification are complete; approved umbrella design is `docs/superpowers/specs/2026-07-27-hardening-closure-design.md`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every shared pinned GET an explicit encoded-body cap, decoded-body cap, bounded DNS slot, one absolute whole-chain deadline, and production-composition transport coverage.

**Architecture:** `agent/pinned_http.py` remains the sole synchronous GET boundary, but callers now supply one immutable `EgressPolicy`; each call creates one `DeadlineBudget` that flows through DNS, redirects, httpcore transport, socket operations, and raw-body decoding. DNS uses a process-wide four-slot semaphore with one daemon thread per accepted lookup, while deterministic `socket.socketpair()` tests exercise the actual `_PinnedHTTPTransport` and `httpcore.ConnectionPool` without live DNS or external network access.

**Tech Stack:** Python 3.10+, `httpx>=0.28,<1`, `httpcore>=1.0.9,<2`, stdlib `threading`/`socket`/`ssl`/`select`/`zlib`/`tracemalloc`, pytest, Nuxt 4 verification, Ruff, repository hard checks, bounded backend regression runner.

## Global Constraints

- Start from the verified Plan A result commit; do not execute this plan while Plan A is active or has uncommitted owned changes.
- Preserve destination parsing, public-address rejection, exact-sockaddr dialing, peer verification, TLS hostname/SNI/certificate validation, GET-only behavior, no proxies, no retries, HTTP/1.1, and per-hop redirect revalidation.
- The public call is exactly `PinnedHTTPClient.get(url, *, user_agent, policy)`. Remove separate `timeout` and `max_redirects` arguments.
- To keep each intermediate commit green while consumers are migrated, Task 1 may retain a private compatibility bridge that converts old `timeout`/`max_redirects` calls into a bounded policy; Task 5 must remove that bridge and the old keywords before final verification.
- Every policy has positive encoded/decoded byte limits, positive inactivity/total durations, a non-negative redirect limit, and only unique `identity`/`gzip` encoding tokens.
- `PinnedResponse.headers` preserves original response headers; `PinnedResponse.content` contains decoded bytes.
- Read final bodies with `iter_raw()`. Never call `Response.read()` on a final response and never buffer redirect bodies.
- Support identity and gzip only. Reject Brotli, deflate, stacked, unknown, blank-token, malformed, truncated, trailing-byte, and concatenated-member encodings.
- DNS uses one process-wide four-slot semaphore, at most four daemon resolver threads, no executor, and no queued work that may start after a request expires.
- Waiting for DNS capacity, resolution, redirects, connect attempts, TLS, partial writes, reads, and decode all consume one absolute monotonic deadline.
- The gzip allocation regression uses a 32 MiB decoded bomb, a 1 MiB decoded policy, creates compressed input before `tracemalloc.start()`, and requires peak traced allocation `<= 8 * max_decoded_bytes`.
- Use uncommitted RED tests followed by minimal GREEN implementation. Do not create a commit whose test suite is known to fail.
- Do not migrate crawler, geocode, realtime, scheduler, moderation, bot, DDGS, OpenAI, or any caller outside the three mapped consumers.
- Do not add cookie-jar support, async I/O, POST, authentication, arbitrary headers, proxy support, HTTP/2, retries, Brotli, deflate, a DNS service, paid telemetry, or external network tests.
- Do not push, deploy, rotate secrets, enable indexing, mutate data, or touch `agent/knowledge.db-shm` and `agent/knowledge.db-wal`.

---

## File Structure

- Modify `agent/pinned_http.py`: policy/budget contracts, exception hierarchy, raw bounded reader, bounded gzip decoder, DNS semaphore gate, deadline-aware resolver/backend/stream/transport/client, and closed-stream behavior.
- Modify `tests/test_pinned_http.py`: policy validation, body/encoding boundaries, allocation ceiling, DNS saturation, deadline reuse, transport edges, and real-httpcore socket-pair harness.
- Modify `agent/admin.py`: construct an identity-only image policy from the existing image-size limit and preserve HTTP error semantics.
- Modify `agent/auto_learn.py`: use a reusable 2 MiB gzip/identity text policy with 15-second inactivity and total limits.
- Modify `agent/gpt55_quality_burst.py`: construct a 2 MiB gzip/identity policy whose inactivity and total limits equal the existing `timeout` argument.
- Modify `tests/test_admin_pinned_http.py`: lock the dynamic image profile and new exception mappings.
- Modify `tests/test_auto_learn_fetch.py`: lock the auto-learn profile and preserved decode/cleanup behavior.
- Modify `tests/test_gpt55_quality_burst.py`: lock the quality-burst profile and preserved optional-Requests/status/silent-failure behavior.
- Modify `tests/test_pinned_http_consumers.py`: require `EgressPolicy` usage in all three mapped modules without widening the registry.
- Modify `docs/superpowers/plans/2026-07-26-shared-pinned-outbound-http-client.md`: mark the completed historical plan done and add its actual result record.
- Modify `docs/ROADMAP.md`: replace provisional scanner/egress evidence with final revision-bound baseline truth.
- Modify `docs/HANDOFF.md`: remove resolved body/deadline, real-transport, verifiedAt, and scanner lines while retaining observability and cookie-gate residuals.
- Modify both 2026-07-27 plan files after final verification: record exact result status without retroactively checking all task boxes.

---

### Task 1: Add Policy Contracts and Bounded Raw-Body Decoding

**Files:**
- Modify: `agent/pinned_http.py:35-120,512-555,563-606`
- Modify: `tests/test_pinned_http.py:1-15,532-869`

**Interfaces:**
- Consumes: final-hop `httpx.Response.iter_raw()`, original response headers, `zlib.decompressobj(16 + zlib.MAX_WBITS)`, and a call-scoped `DeadlineBudget`.
- Produces: `EgressPolicy`, `DeadlineBudget`, `PinnedBodyLimitError`, `PinnedContentEncodingError`, `PinnedDeadlineExceeded`, `_read_bounded_body()`, and a policy-first `PinnedHTTPClient.get()` with a temporary bounded compatibility bridge for the three unmigrated consumers.

- [ ] **Step 1: Add RED policy validation tests**

Add a reusable test policy helper to `tests/test_pinned_http.py`:

```python
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
```

Add the raw-response fixtures used by the body tests; these are unit seams only and do not replace the real-httpcore harness in Task 4:

```python
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
    def resolver(host: str, port: int):
        return _public_resolver(host, port)

    def factory(_hop):
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
    def resolver(host: str, port: int):
        return _public_resolver(host, port)

    calls = 0

    def factory(_hop):
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
            return httpx.Response(200, content=b"final", request=request)

        return httpx.MockTransport(handler)

    return ph.PinnedHTTPClient(resolver=resolver, transport_factory=factory)
```

Add exact validation cases:

```python
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
```

Add a policy-forwarding test using `inspect.signature()` that requires keyword-only `policy` on the new path. Defer the final absence of `timeout` and `max_redirects` to Task 5 because the three production adapters still use those keywords until their profile migration.

- [ ] **Step 2: Add RED identity, gzip, header, and redirect-body tests**

Extend `_OneChunkStream` so it records closure, and add `_ChunkStream` for multiple raw chunks. Add tests with these exact contracts:

```python
def test_identity_body_accepts_exact_encoded_and_decoded_boundaries() -> None:
    body = b"x" * 1024
    result = _client_for_raw_response(body).get(
        "https://example.com/a",
        user_agent="test",
        policy=_policy(max_encoded_bytes=1024, max_decoded_bytes=1024),
    )
    assert result.content == body


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
        )


def test_redirect_body_is_closed_without_iteration() -> None:
    stream = _ChunkStream([b"redirect body must not be read"])
    client = _client_for_redirect_stream(stream)
    result = client.get(
        "https://example.com/a",
        user_agent="test",
        policy=_policy(max_redirects=1),
    )
    assert result.url == "https://example.com/final"
    assert stream.closed is True
    assert stream.iterated is False
```

Also cover parseable `Content-Length > max_encoded_bytes` early rejection, identity boundary plus one, decoded boundary plus one, preserved original headers, and explicit `Accept-Encoding` equal to `", ".join(policy.accepted_encodings)`.

- [ ] **Step 3: Add RED strict-gzip and allocation tests**

Add tests for a valid gzip body split across chunks, malformed bytes, a stream missing the trailer, valid gzip plus trailing bytes, concatenated gzip members, and decoded boundary plus one. Add the allocation regression exactly as follows:

```python
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
            )
        _current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    assert peak <= 8 * decoded_cap
```

The compressed fixture must remain outside the traced region. Do not weaken the 32 MiB source size, 1 MiB decoded cap, or eight-times ceiling.

- [ ] **Step 4: Run body tests and confirm RED**

```powershell
python -m pytest tests/test_pinned_http.py -q -k "policy or body or encoding or gzip or redirect_body or allocation or call_shape"
```

Expected: failures show missing policy/budget classes, the incomplete policy path, use of `response.read()`, unsupported encodings being decoded by HTTPX, and allocation scaling with decoded output. Existing consumers may continue through the bounded bridge until Task 5.

- [ ] **Step 5: Implement immutable policy, budget, and exception contracts**

Add these types near the existing exception and response dataclasses:

```python
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
```

Move `MonotonicClock = Callable[[], float]` above `DeadlineBudget` so annotations resolve consistently.

- [ ] **Step 6: Implement raw counting and bounded identity/gzip decoding**

Add focused helpers rather than one high-complexity reader:

```python
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
```

Implement identity and gzip decoding with bounded appends:

```python
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
```

`max_length=remaining + 1` prevents the decoder from allocating the full expanded member. `unconsumed_tail`, `unused_data`, and `decoder.eof` respectively prevent hidden extra output, trailing/concatenated members, and truncated streams.

Use this orchestration:

```python
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
    chunks = _bounded_raw_chunks(response, policy)
    if encoding == "identity":
        return _decode_identity(chunks, policy, budget, monotonic)
    return _decode_gzip(chunks, policy, budget, monotonic)
```

Call `budget.remaining(monotonic=monotonic)` before processing every raw chunk and before decoder flush.

- [ ] **Step 7: Replace final buffering and the public call signature**

Change `_fetch_hop()` to accept `policy` and `budget`, set `Accept-Encoding` explicitly, return redirects without iterating their body, and use `_read_bounded_body()` for final responses. Preserve `tuple(response.headers.multi_items())` before closing the response.

Change `PinnedHTTPClient.get()` to accept `policy` and use it for all new callers. During this task only, retain a bounded bridge for old callers:

```python
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
    budget = DeadlineBudget.start(policy.total_timeout_seconds)
    # The existing redirect loop follows here and reuses this exact budget.
```

Implement the temporary bridge with finite values so old callers remain bounded while the consumer task is pending:

```python
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
```

Use `policy.max_redirects` in the redirect check. Task 5 removes both old keyword parameters and the bridge after all three adapters pass explicit profiles.

- [ ] **Step 8: Run body verification and commit**

```powershell
python -m pytest tests/test_pinned_http.py -q -k "policy or body or encoding or gzip or redirect_body or allocation or call_shape"
python -m ruff check agent/pinned_http.py tests/test_pinned_http.py
git diff --check
git add agent/pinned_http.py tests/test_pinned_http.py
git commit -m "fix: bound pinned response bodies and decompression"
```

Expected: all selected tests pass, allocation peak is at most 8 MiB for the 1 MiB policy, and the commit contains no consumer migration yet.

---

### Task 2: Bound DNS Resolution with a Four-Slot Gate

**Files:**
- Modify: `agent/pinned_http.py:107-115,223-267,502-510`
- Modify: `tests/test_pinned_http.py:15-206,870-895`

**Interfaces:**
- Consumes: one `DeadlineBudget` per call and stdlib `threading.BoundedSemaphore`, `threading.Event`, and `threading.Thread`.
- Produces: `resolve_public_addresses(host: str, port: int, budget: DeadlineBudget) -> tuple[ResolvedAddress, ...]`, a process-wide `_RESOLVER_SLOTS` with capacity four, and bounded default `validate_public_url()` behavior.

- [ ] **Step 1: Change resolver test doubles to the budget-aware signature**

Update `Resolver` test functions throughout `tests/test_pinned_http.py` from `(host, port)` to `(host, port, budget)`. Assert that the same `DeadlineBudget` instance reaches each redirect resolution.

Add a standalone validation test that monkeypatches `resolve_public_addresses`, calls `validate_public_url("https://example.com")`, and asserts the received budget expires no more than 15 seconds after the captured monotonic start.

- [ ] **Step 2: Add RED gate saturation and no-queue tests**

Add `import threading` to `tests/test_pinned_http.py`. Use controlled events so tests never leave stuck daemon threads:

```python
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
        entered.wait(timeout=2)
        release.wait(timeout=2)
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
        entered.wait(timeout=2)
        with pytest.raises(ph.ResolverSaturatedError):
            ph.resolve_public_addresses(
                "fifth.example",
                443,
                ph.DeadlineBudget.start(0.01),
            )
        assert peak == 4
        release.set()
        assert all(future.result() for future in futures)
```

Add the timed-out-resolution retention test:

```python
def test_timed_out_dns_threads_hold_slots_until_os_returns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entered = threading.Barrier(5)
    release = threading.Event()
    call_count = 0
    lock = threading.Lock()

    def blocked_getaddrinfo(*_args, **_kwargs):
        nonlocal call_count
        with lock:
            call_count += 1
            current = call_count
        if current <= 4:
            entered.wait(timeout=2.0)
            release.wait(timeout=2.0)
        return [_answer("93.184.216.34")]

    monkeypatch.setattr(ph.socket, "getaddrinfo", blocked_getaddrinfo)
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
        recovered = ph.resolve_public_addresses(
            "recovered.example",
            443,
            ph.DeadlineBudget.start(1.0),
        )
        assert str(recovered[0].ip) == "93.184.216.34"
    finally:
        release.set()
```

This proves timed-out resolver threads retain slots until their OS calls return and no queued fifth job starts later.

- [ ] **Step 3: Run resolver tests and confirm RED**

```powershell
python -m pytest tests/test_pinned_http.py -q -k "resolver or dns or validate_public_url or redirect_re_resolves"
```

Expected: failures show the old two-argument resolver, direct synchronous `getaddrinfo()`, and absence of the four-slot saturation error.

- [ ] **Step 4: Implement the semaphore gate without an executor or queue**

Add module state:

```python
_MAX_RESOLVER_THREADS = 4
_RESOLVER_SLOTS = threading.BoundedSemaphore(_MAX_RESOLVER_THREADS)
```

Keep literal-IP validation synchronous because it does not call system DNS. Move hostname lookup into:

```python
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
```

Do not release the slot on caller timeout; only the daemon worker's `finally` releases it. Do not store timed-out jobs for later execution.

- [ ] **Step 5: Thread the budget through resolution and standalone validation**

Change the protocol and helpers to:

```python
class Resolver(Protocol):
    def __call__(
        self,
        host: str,
        port: int,
        budget: DeadlineBudget,
    ) -> tuple[ResolvedAddress, ...]: ...


def validate_public_url(
    url: str,
    *,
    resolver: Resolver = resolve_public_addresses,
    budget: DeadlineBudget | None = None,
) -> None:
    active_budget = budget or DeadlineBudget.start(15.0)
    # Parse and invoke resolver(host, port, active_budget).
```

Change `_resolve_hop()` and the redirect loop to pass the same call-scoped budget to every resolver invocation.

- [ ] **Step 6: Run DNS verification and commit**

```powershell
python -m pytest tests/test_pinned_http.py -q -k "resolver or dns or validate_public_url or redirect_re_resolves or concurrent"
python -m ruff check agent/pinned_http.py tests/test_pinned_http.py
git diff --check
git add agent/pinned_http.py tests/test_pinned_http.py
git commit -m "fix: bound pinned DNS resolution"
```

Expected: tests prove a maximum of four active daemon resolver threads, deadline-bounded gate waiting, retained slots for stuck OS calls, and recovery after workers finish.

---

### Task 3: Enforce One Deadline Through Backend, Stream, Redirects, and Decode

**Files:**
- Modify: `agent/pinned_http.py:269-445,459-510,512-606`
- Modify: `tests/test_pinned_http.py:207-445,547-840`

**Interfaces:**
- Consumes: the call-scoped `DeadlineBudget`, `EgressPolicy.inactivity_timeout_seconds`, httpcore's requested per-operation timeout, and the existing socket-factory/monotonic seams.
- Produces: budget-aware `_PinnedNetworkStream`, `_PinnedNetworkBackend`, `_PinnedHTTPTransport`, `build_pinned_transport`, `TransportFactory`, `_resolve_hop`, `_fetch_hop`, and redirect loop.

- [ ] **Step 1: Add RED one-budget and per-operation timeout tests**

Add tests that capture object identity at resolver and transport seams:

```python
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
    )

    assert len({id(item) for item in budgets}) == 1
```

Add fake-clock tests proving:

- a second address attempt receives a smaller connect timeout;
- TLS receives `min(requested, inactivity, remaining)`;
- every partial `send()` recomputes a smaller timeout;
- `recv()` receives the smaller of inactivity and remaining total time;
- redirect processing never creates a fresh expiry;
- raw decode raises `PinnedDeadlineExceeded` after the clock passes expiry;
- a socket `send()` returning zero raises `httpcore.WriteError`.

Use these concrete partial-write and decode-deadline contracts:

```python
class PartialSendSocket(FakeSocket):
    def __init__(self, peer: tuple, send_sizes: list[int]) -> None:
        super().__init__(peer)
        self.send_sizes = iter(send_sizes)

    def send(self, _buffer: bytes) -> int:
        return next(self.send_sizes)


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
```

Adapt the existing two-address connect-budget test to construct `_PinnedNetworkBackend` with `policy=_policy(inactivity_timeout_seconds=5.0)`, `budget=DeadlineBudget(expires_at=15.0)`, and clock readings `11.0`, then `12.0`; retain the exact timeout assertions `[4.0]` and `[3.0]`. Add a `ZeroSendSocket` subclass returning `0` and assert `stream.write()` raises `httpcore.WriteError`.

- [ ] **Step 2: Run deadline tests and confirm RED**

```powershell
python -m pytest tests/test_pinned_http.py -q -k "deadline or budget or partial or zero_send or connect_budget or tls"
```

Expected: failures show transport factories receiving only a hop, streams retaining only a socket, redirects resetting HTTPX timeout state, and partial operations reusing stale timeouts.

- [ ] **Step 3: Make transport interfaces budget-aware**

Use these exact signatures:

```python
class TransportFactory(Protocol):
    def __call__(
        self,
        hop: ResolvedHop,
        policy: EgressPolicy,
        budget: DeadlineBudget,
    ) -> httpx.BaseTransport: ...


class _PinnedNetworkStream(httpcore.NetworkStream):
    def __init__(
        self,
        sock: socket.socket,
        *,
        policy: EgressPolicy,
        budget: DeadlineBudget,
        monotonic: MonotonicClock = time.monotonic,
    ) -> None: ...


class _PinnedNetworkBackend(httpcore.NetworkBackend):
    def __init__(
        self,
        hop: ResolvedHop,
        *,
        policy: EgressPolicy,
        budget: DeadlineBudget,
        socket_factory: SocketFactory = socket.socket,
        monotonic: MonotonicClock = time.monotonic,
    ) -> None: ...


class _PinnedHTTPTransport(httpx.BaseTransport):
    def __init__(
        self,
        hop: ResolvedHop,
        *,
        policy: EgressPolicy,
        budget: DeadlineBudget,
        socket_factory: SocketFactory = socket.socket,
        monotonic: MonotonicClock = time.monotonic,
    ) -> None: ...


def build_pinned_transport(
    hop: ResolvedHop,
    policy: EgressPolicy,
    budget: DeadlineBudget,
) -> httpx.BaseTransport:
    return _PinnedHTTPTransport(hop, policy=policy, budget=budget)
```

Use this client constructor and budget creation:

```python
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
```

In the transitional `get()` from Task 1, create the budget with:

```python
budget = DeadlineBudget.start(
    policy.total_timeout_seconds,
    monotonic=self._monotonic,
)
```

During Tasks 3-4, retain the bounded compatibility parameters introduced in Task 1. Task 5 installs the final exact signature. Pass `self._monotonic` to `_fetch_hop()` and bounded decoding. This keeps fake-clock deadline tests deterministic while the production default remains `time.monotonic`.

Update every injected factory in `tests/test_pinned_http.py` to accept all three arguments even when it ignores policy or budget. Update the three direct `_PinnedNetworkStream(fake)` constructions in the existing stream/TLS tests to pass `_policy()` and `ph.DeadlineBudget.start(5.0)`; do not make production constructors optional just to preserve stale test calls.

- [ ] **Step 4: Recompute timeout for every socket operation**

In stream `read()`, every loop iteration in `write()`, and `start_tls()`, compute:

```python
operation_timeout = self._budget.socket_timeout(
    timeout,
    self._policy.inactivity_timeout_seconds,
    monotonic=self._monotonic,
)
self._socket.settimeout(operation_timeout)
```

When `send()` returns zero, raise `httpcore.WriteError("socket connection broken")` directly. On `socket.timeout`, call `budget.remaining()` first: if it raises, let `PinnedDeadlineExceeded` propagate; otherwise translate to the matching httpcore inactivity timeout.

In `connect_tcp()`, remove the per-connect deadline created from httpcore's timeout. Before each address and after socket creation, use `budget.socket_timeout(timeout, policy.inactivity_timeout_seconds, monotonic=...)`. Return a `_PinnedNetworkStream` carrying the same policy, budget, and clock.

In `start_tls()`, return a new `_PinnedNetworkStream` with those same three objects.

- [ ] **Step 5: Propagate the same budget through redirects and decode**

Call the transport factory as `transport_factory(hop, policy, budget)`. Build the HTTPX request with `httpx.Timeout(policy.inactivity_timeout_seconds)` so httpcore still receives an inactivity request, but treat `DeadlineBudget` as the authoritative outer ceiling.

Before each redirect-loop iteration, redirect-target parse, and final response creation, call `budget.remaining()`. Keep the one budget created at the start of `PinnedHTTPClient.get()`; do not call `DeadlineBudget.start()` elsewhere in the request path.

- [ ] **Step 6: Run deadline verification and commit**

```powershell
python -m pytest tests/test_pinned_http.py -q -k "deadline or budget or partial or zero_send or connect_budget or tls or redirect"
python -m ruff check agent/pinned_http.py tests/test_pinned_http.py
git diff --check
git add agent/pinned_http.py tests/test_pinned_http.py
git commit -m "fix: enforce one pinned egress deadline"
```

Expected: all selected tests pass and every captured resolver, transport, backend, stream, redirect, and decode path observes the same `DeadlineBudget` instance.

---

### Task 4: Exercise the Real httpcore Composition and Edge Behavior

**Files:**
- Modify: `agent/pinned_http.py:273-340,459-498`
- Modify: `tests/test_pinned_http.py:207-531`

**Interfaces:**
- Consumes: actual `_PinnedHTTPTransport`, actual `httpcore.ConnectionPool`, a local `socket.socketpair()`, and the existing `socket_factory` seam.
- Produces: deterministic end-to-end HTTP/1.1 tests for request bytes, fixed/chunked bodies, partial/zero writes, peer rejection, closure, deadlines, and encoding boundaries.

- [ ] **Step 1: Add the socket-pair harness**

Add these helpers to `tests/test_pinned_http.py`:

```python
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
        self.closed = True
        self.sock.close()
```

Add the server and client builders:

```python
def _serve_http(
    peer: socket.socket,
    response_chunks: tuple[bytes, ...],
    received: list[bytes],
    response_gate: threading.Event | None,
) -> None:
    request = bytearray()
    try:
        peer.settimeout(2.0)
        while b"\r\n\r\n" not in request:
            chunk = peer.recv(4096)
            if not chunk:
                break
            request.extend(chunk)
        received.append(bytes(request))
        if response_gate is not None:
            response_gate.wait(timeout=2.0)
        for chunk in response_chunks:
            peer.sendall(chunk)
    except OSError:
        pass
    finally:
        peer.close()


def _real_transport_client(
    response_chunks: tuple[bytes, ...],
    *,
    peer: tuple[str, int] = ("93.184.216.34", 80),
    max_send: int | None = None,
    zero_send: bool = False,
    response_gate: threading.Event | None = None,
):
    client_socket, server_socket = socket.socketpair()
    wrapped = SocketPairClient(
        client_socket,
        peer=peer,
        max_send=max_send,
        zero_send=zero_send,
    )
    received: list[bytes] = []
    server = threading.Thread(
        target=_serve_http,
        args=(server_socket, response_chunks, received, response_gate),
        daemon=True,
    )
    server.start()

    def resolver(host: str, port: int, _budget: ph.DeadlineBudget):
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

    def factory(hop, policy, budget):
        return ph._PinnedHTTPTransport(
            hop,
            policy=policy,
            budget=budget,
            socket_factory=lambda *_args: wrapped,
        )

    client = ph.PinnedHTTPClient(
        resolver=resolver,
        transport_factory=factory,
    )
    return client, received, wrapped, server
```

Every harness test must set `response_gate` when one was supplied, call `server.join(timeout=2.0)` in `finally`, and assert `not server.is_alive()` so a protocol failure cannot leak a blocked test thread.

- [ ] **Step 2: Add RED request, fixed-length, chunked, and close tests**

Use the harness with an `http://example.com/path?q=1` hop:

```python
def test_real_httpcore_emits_request_and_reads_fixed_length() -> None:
    client, received, wrapped, server = _real_transport_client(
        (b"HTTP/1.1 200 OK\r\nContent-Length: 5\r\n\r\nhello",)
    )
    try:
        result = client.get(
            "http://example.com/path?q=1",
            user_agent="test-agent",
            policy=_policy(
                accepted_encodings=("identity",),
                inactivity_timeout_seconds=1.0,
                total_timeout_seconds=2.0,
            ),
        )
    finally:
        server.join(timeout=2.0)

    assert not server.is_alive()
    assert received[0].startswith(b"GET /path?q=1 HTTP/1.1\r\n")
    assert b"\r\nHost: example.com\r\n" in received[0]
    assert result.content == b"hello"
    assert wrapped.closed is True
```

Run once with `Content-Length: 5` and once with:

```text
Transfer-Encoding: chunked

5\r\nhello\r\n0\r\n\r\n
```

The tests must instantiate the real `_PinnedHTTPTransport`; do not monkeypatch `httpcore.ConnectionPool`, use `httpx.MockTransport`, perform live DNS, or connect externally.

- [ ] **Step 3: Add RED partial-send, zero-send, peer, and readability tests**

Add one request with `max_send=3` and assert the server still receives a complete request. Add one with `zero_send=True` and assert `PinnedTransportError` is raised and no complete request reaches the server.

Set `peer=("127.0.0.1", 80)` while the approved address remains `93.184.216.34`; assert `PeerMismatchError` and assert the server observes zero request bytes.

For closed readability:

```python
wrapped.close()
stream = ph._PinnedNetworkStream(
    wrapped,
    policy=_policy(),
    budget=ph.DeadlineBudget.start(1.0),
)
assert stream.get_extra_info("is_readable") is True
```

Also cover a wrapper whose `fileno()` raises `ValueError` and one returning `-1`; both must return `True` rather than leaking.

- [ ] **Step 4: Add real-transport boundary and encoding tests**

Parameterize scripted responses over:

- identity at exact cap and cap plus one;
- gzip at exact decoded cap and cap plus one;
- malformed gzip;
- truncated gzip;
- unsupported `br`;
- stacked `gzip, identity`;
- false small `Content-Length` with an over-cap body;
- a server that withholds the body until the total deadline expires.

Assert the exact typed error for each case: `PinnedBodyLimitError`, `PinnedContentEncodingError`, or `PinnedDeadlineExceeded`. Keep unit allocation tracing in Task 1; this task verifies the production composition seam rather than duplicating the 32 MiB allocation test.

- [ ] **Step 5: Run real-httpcore tests and confirm RED**

```powershell
python -m pytest tests/test_pinned_http.py -q -k "real_httpcore or socketpair or request_line or chunked or partial_send or zero_send or peer_mismatch or closed_readability"
```

Expected: the harness exposes the current closed-`select.select()` `ValueError` and any composition mismatch in actual request/response handling.

- [ ] **Step 6: Harden closed readability without weakening terminal detection**

Replace the `is_readable` branch with:

```python
if info == "is_readable":
    try:
        if self._socket.fileno() < 0:
            return True
        readable, _, _ = select.select([self._socket], [], [], 0)
    except (OSError, ValueError):
        return True
    return bool(readable)
```

Do not return `False` for closed or invalid descriptors; httpcore treats readable as terminal and can then retire the connection.

- [ ] **Step 7: Run the full core suite and commit transport edges**

```powershell
python -m pytest tests/test_pinned_http.py -q
python -m ruff check agent/pinned_http.py tests/test_pinned_http.py
git diff --check
git add agent/pinned_http.py tests/test_pinned_http.py
git commit -m "fix: harden real pinned transport edges"
```

Expected: the full pinned core suite exits `0`; actual httpcore sends the expected request, parses fixed/chunked responses, closes response/pool/socket resources, and fails before request bytes on peer mismatch.

---

### Task 5: Migrate the Three Consumer Profiles

**Files:**
- Modify: `agent/admin.py:40-53,1040-1080`
- Modify: `agent/auto_learn.py:39-55,263-280`
- Modify: `agent/gpt55_quality_burst.py:48-56,649-676`
- Modify: `tests/test_admin_pinned_http.py:1-112,186-230`
- Modify: `tests/test_auto_learn_fetch.py:1-124`
- Modify: `tests/test_gpt55_quality_burst.py:165-305`
- Modify: `tests/test_pinned_http_consumers.py:40-63`

**Interfaces:**
- Consumes: `EgressPolicy`, the new `PinnedHTTPClient.get(..., policy=...)` call, and existing consumer return/status/charset contracts.
- Produces: identity-only dynamic admin image policy; reusable auto-learn text policy; timeout-derived quality-burst text policy.

- [ ] **Step 1: Add RED exact-profile tests**

Change the expected admin call to:

```python
assert calls == [(
    "https://cdn.example/a",
    {
        "user_agent": "vinhlong360-image-review/1.0 (+https://vinhlong360.vn)",
        "policy": ph.EgressPolicy(
            max_encoded_bytes=12 * 1024 * 1024,
            max_decoded_bytes=12 * 1024 * 1024,
            accepted_encodings=("identity",),
            inactivity_timeout_seconds=25.0,
            total_timeout_seconds=25.0,
            max_redirects=5,
        ),
    },
)]
```

Change the auto-learn expectation to a 2 MiB encoded/decoded cap, `("gzip", "identity")`, 15-second inactivity/total limits, and five redirects. Change quality-burst to the same 2 MiB/encoding profile with both durations equal to the function's `timeout` argument.

Extend `tests/test_pinned_http_consumers.py` so each mapped module must import both `PinnedHTTPClient` and `EgressPolicy`.

Add `import inspect` to `tests/test_pinned_http.py` and add the final signature assertion:

```python
def test_pinned_client_public_get_requires_policy_only() -> None:
    parameters = inspect.signature(ph.PinnedHTTPClient.get).parameters
    assert list(parameters) == ["self", "url", "user_agent", "policy"]
    assert parameters["user_agent"].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters["policy"].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters["policy"].default is inspect.Parameter.empty
```

- [ ] **Step 2: Add RED outward-error behavior tests**

For admin, parameterize:

```python
(
    (ph.PinnedBodyLimitError("large"), 400),
    (ph.PinnedContentEncodingError("encoding"), 400),
    (ph.PinnedDeadlineExceeded("deadline"), 502),
    (ph.ResolverSaturatedError("dns busy"), 502),
)
```

Assert image approval leaves DB, queue status, upload calls, and sync hooks untouched on every failure. For auto-learn, assert all four exceptions log one warning containing the URL and return `None`. For quality-burst, assert they return `""` and preserve the existing no-log contract.

- [ ] **Step 3: Run consumer tests and confirm RED**

```powershell
python -m pytest tests/test_admin_pinned_http.py tests/test_auto_learn_fetch.py tests/test_gpt55_quality_burst.py tests/test_pinned_http_consumers.py -q
```

Expected: failures show consumers still passing `timeout` and `max_redirects` and not importing `EgressPolicy`.

- [ ] **Step 4: Implement the exact consumer policies**

In `agent/admin.py`, import the new exception types and `EgressPolicy`, then add:

```python
def _admin_image_egress_policy(max_image_size: int) -> EgressPolicy:
    return EgressPolicy(
        max_encoded_bytes=max_image_size,
        max_decoded_bytes=max_image_size,
        accepted_encodings=("identity",),
        inactivity_timeout_seconds=25.0,
        total_timeout_seconds=25.0,
        max_redirects=5,
    )
```

Pass `policy=_admin_image_egress_policy(max_image_size)`. Map `PinnedBodyLimitError` and `PinnedContentEncodingError` to the existing 400 invalid/oversize source response; map `PinnedDeadlineExceeded`, `ResolverSaturatedError`, and `PinnedTransportError` to the existing 502 retry-later response. Retain the post-fetch empty/size check as defense in depth.

In `agent/auto_learn.py`, define once:

```python
_AUTO_LEARN_EGRESS_POLICY = EgressPolicy(
    max_encoded_bytes=2 * 1024 * 1024,
    max_decoded_bytes=2 * 1024 * 1024,
    accepted_encodings=("gzip", "identity"),
    inactivity_timeout_seconds=15.0,
    total_timeout_seconds=15.0,
    max_redirects=5,
)
```

Pass that object as `policy`. Preserve exact-200, HTTPX charset reconstruction, script/style removal, HTML stripping, whitespace collapse, 6,000-character limit, and warning behavior.

In `agent/gpt55_quality_burst.py`, add:

```python
def _quality_burst_egress_policy(timeout: int) -> EgressPolicy:
    return EgressPolicy(
        max_encoded_bytes=2 * 1024 * 1024,
        max_decoded_bytes=2 * 1024 * 1024,
        accepted_encodings=("gzip", "identity"),
        inactivity_timeout_seconds=float(timeout),
        total_timeout_seconds=float(timeout),
        max_redirects=5,
    )
```

Pass that object as `policy`. Preserve the `requests is None` short circuit, `<400` status rule, offline Requests charset behavior, tag-only cleanup, 5,000-character compaction, and silent failure.

After all three adapters pass explicit policies, delete `_transitional_policy()` and change the public method to the final contract:

```python
    def get(
    self,
    url: str,
    *,
    user_agent: str,
    policy: EgressPolicy,
) -> PinnedResponse:
```

Remove `timeout` and `max_redirects` from the method, tests, and all call sites. The final signature test must fail if the bridge survives.

- [ ] **Step 5: Run consumer and full pinned verification**

```powershell
python -m pytest tests/test_pinned_http.py tests/test_admin_pinned_http.py tests/test_auto_learn_fetch.py tests/test_gpt55_quality_burst.py tests/test_pinned_http_consumers.py -q
python -m ruff check agent/pinned_http.py agent/admin.py agent/auto_learn.py agent/gpt55_quality_burst.py tests/test_pinned_http.py tests/test_admin_pinned_http.py tests/test_auto_learn_fetch.py tests/test_gpt55_quality_burst.py tests/test_pinned_http_consumers.py
git diff --check
```

Expected: all commands exit `0`; the registry remains exactly three mapped fetchers and no direct general-purpose GET is introduced.

- [ ] **Step 6: Commit consumer migration**

```powershell
git add agent/admin.py agent/auto_learn.py agent/gpt55_quality_burst.py tests/test_admin_pinned_http.py tests/test_auto_learn_fetch.py tests/test_gpt55_quality_burst.py tests/test_pinned_http_consumers.py
git commit -m "refactor: migrate pinned egress consumer profiles"
```

Expected: the commit succeeds with paired tests and preserves all outward consumer behavior except the intentional bounded-failure cases.

---

### Task 6: Run Final Baselines and Truth-Sync Documentation

**Files:**
- Modify after gates: `docs/superpowers/plans/2026-07-26-shared-pinned-outbound-http-client.md`
- Modify after gates: `docs/superpowers/plans/2026-07-27-trust-scanner-correctness.md`
- Modify after gates: `docs/superpowers/plans/2026-07-27-bound-complete-pinned-egress.md`
- Modify after gates: `docs/ROADMAP.md:418-430`
- Modify after gates: `docs/HANDOFF.md:1-5,131-142`

**Interfaces:**
- Consumes: all green Plan A and Plan B commits, frontend gates, hard checks, and the official bounded backend runner.
- Produces: one final revision-bound evidence record, truthful plan statuses, resolved HANDOFF debt removal, and retained genuine residual risks.

- [ ] **Step 1: Run the final focused pinned suite**

```powershell
python -m pytest tests/test_pinned_http.py tests/test_admin_pinned_http.py tests/test_auto_learn_fetch.py tests/test_gpt55_quality_burst.py tests/test_pinned_http_consumers.py -q
```

Expected: exit `0`. Record exact pass/skip counts and duration from this run.

- [ ] **Step 2: Run the final frontend suite**

```powershell
Set-Location web-nuxt
npm test
npm run typecheck
npm run build
Set-Location ..
```

Expected: all three commands exit `0`. This is the final frontend proof for the combined trust/scanner/egress candidate.

- [ ] **Step 3: Run hard checks and diff hygiene**

```powershell
python scripts/checks/run_hard.py --all
git diff --check
```

Expected: hard checks exit `0` with `hard=0` and no ratchet increase; diff check exits `0`.

- [ ] **Step 4: Run the fresh official bounded backend baseline**

```powershell
python scripts/ops/run_backend_regression.py --deadline-seconds 7000
```

Run with an outer harness timeout greater than 7,000 seconds. Expected: Phase A and Phase B both exit `0`; exit `124` is a failed gate. Record exact revision, command, counts, skips, xfails, duration, exit code, and SHA-256 receipts emitted or captured for stdout/stderr. The earlier clean research baseline was Phase A `8534 passed, 58 skipped, 111 deselected, 1 xfailed` and Phase B `284 passed, 19 skipped`; report the new measured values rather than copying those historical counts.

- [ ] **Step 5: Mark the historical pinned-client plan truthful**

In `docs/superpowers/plans/2026-07-26-shared-pinned-outbound-http-client.md`, change the status to `done`. Add `## KẾT QUẢ` listing the actual implementation lineage already present in history:

- destination policy `660ec004`;
- pinned sockets/peer verification `073a50e6`;
- redirect-safe client `c46c936d`;
- admin adapter `21930353`;
- auto-learn adapter `e4f54a01`;
- quality-burst adapter `2e67ca0b`;
- adversarial address-policy fix `fabb156b`;
- consumer registry `9f314e32` and enforcement correction `59d0009b`;
- verification truth-sync `407c7a13`;
- the final body/deadline/transport commits created by Tasks 1-5 of this plan;
- exact final focused/hard/frontend/backend evidence from Steps 1-4;
- remaining observability and consent-cookie compatibility debt.

Do not check every historical checkbox. The result section is authoritative.

- [ ] **Step 6: Truth-sync HANDOFF and ROADMAP**

Remove the resolved HANDOFF entries currently at lines 135, 136, 139, and 140: body/deadline bounds, missing real transport test, false `verifiedAt`, and ambient-worktree scanner failure. Retain:

- egress observability gap: blocked destinations, peer mismatches, and redirect denials remain operationally silent;
- cookie/consent redirect-gate incompatibility;
- unmigrated outbound callers explicitly excluded by the spec;
- production behavior remains unobserved until a separately authorized deployment.

Update the ROADMAP security tranche so it states:

- Plan A made `attributes.verifiedAt` authoritative without data rewrites;
- repository checks use Git-index members and package checks use immutable snapshot members;
- every mapped pinned GET now has explicit encoded/decoded caps, bounded gzip, four-slot DNS gating, and one total deadline;
- actual httpcore composition passes deterministic local socket tests;
- exact final focused, frontend, hard, and backend results from Steps 1-4;
- no push, deploy, production mutation, secret change, or indexing change occurred.

Remove the obsolete statement that scanner failures should merely be rerun after worktrees disappear.

- [ ] **Step 7: Mark both 2026-07-27 plans done**

For each plan, change `STATUS: active` to `STATUS: done` and append a concise `## KẾT QUẢ` containing the verified revision, implementation commit hashes, exact commands/counts/exits, and operational non-actions. In Plan A, preserve its own focused evidence and reference the final baseline from this task. In this plan, record the new egress commits and final complete baseline. Do not replace execution history with checked boxes.

- [ ] **Step 8: Verify documentation and commit final truth-sync**

```powershell
python scripts/checks/run_hard.py --all
git diff --check
git status --short
git add docs/ROADMAP.md docs/HANDOFF.md docs/superpowers/plans/2026-07-26-shared-pinned-outbound-http-client.md docs/superpowers/plans/2026-07-27-trust-scanner-correctness.md docs/superpowers/plans/2026-07-27-bound-complete-pinned-egress.md
git commit -m "docs: close pinned hardening follow-ups"
```

Expected: hard checks and diff hygiene remain green after documentation edits; the commit succeeds; only the pre-existing untracked `agent/knowledge.db-shm` and `agent/knowledge.db-wal` remain outside Git; nothing is pushed or deployed.

- [ ] **Step 9: Confirm the final local state**

```powershell
git status --short --branch
git log --oneline -12
```

Expected: all implementation and truth-sync commits are visible on the local branch, no owned changes remain uncommitted, and Plan A precedes Plan B in history.

---

## Completion Criteria

- Every `PinnedHTTPClient.get()` call has an explicit `EgressPolicy` and a fresh absolute monotonic `DeadlineBudget`.
- Encoded and decoded byte counts are independently authoritative; `Content-Length` is only an early-rejection hint.
- Final responses use `iter_raw()`; redirect bodies are closed without buffering.
- Identity and gzip boundaries pass exactly at the cap and fail at cap plus one.
- Malformed, truncated, trailing, concatenated, unsupported, and stacked encodings fail closed with typed errors.
- The 32 MiB gzip bomb is rejected under a 1 MiB decoded policy with traced peak allocation at most 8 MiB.
- DNS has at most four active daemon lookup threads, no executor queue, deadline-bounded slot waiting, and retained slots for timed-out system calls.
- Redirects, DNS, connect attempts, TLS, partial writes, reads, and decode share one deadline and never reset expiry.
- Real `_PinnedHTTPTransport` plus real `httpcore.ConnectionPool` emits the expected request and handles fixed/chunked responses through local socket pairs.
- Peer mismatch occurs before HTTP/TLS bytes; zero send becomes a typed write failure; closed readability never leaks `ValueError`.
- Admin uses identity-only 12 MiB-by-current-limit semantics with 25-second bounds; auto-learn uses 2 MiB gzip/identity with 15 seconds; quality-burst uses 2 MiB gzip/identity with its existing timeout, default 12 seconds.
- Focused backend, frontend test/typecheck/build, hard checks, diff hygiene, and the official bounded backend regression all pass on the final candidate revision.
- The old pinned-client plan and both new plans report truthful completion; ROADMAP and HANDOFF retain only genuine residuals.
- No data file, database, secret, production service, indexing posture, remote branch, or deployment is changed.

## KẾT QUẢ

- Verified implementation revision: `de7efa3fbc26cb04430bc3e6f98afe50fef48724` (backend implementation remains `dab4877163280a6476180e0ad285280e405af1b4`; frontend test ownership/hook stability was corrected in `de7efa3f`); Plan A result commit `61a14003` precedes this plan.
- Implementation commits: `ea2822d1` body/decompression bounds; `8ae23153` bounded DNS; `271e2653` saturation-test hardening; `286c021a` whole-chain deadline; `a05d6784` deadline-boundary correction; `6d3e43fb` connect-timeout recomputation; `a83e48fd` real transport edge hardening; `6387a246` deadline-limited read mapping; `be94c629` timeout-tie and cleanup hardening; `dab48771` explicit admin/auto-learn/quality-burst profiles.
- Focused pinned gate: `python -m pytest tests/test_pinned_http.py tests/test_admin_pinned_http.py tests/test_auto_learn_fetch.py tests/test_gpt55_quality_burst.py tests/test_pinned_http_consumers.py -q` -> exit `0`; `303 passed in 22.36s`.
- Frontend gates from `web-nuxt` on `de7efa3f`: `npm test` -> exit `0`, `37` files and `912` tests passed in `30.49s`; pure composable tests own the Node environment and genuine Nuxt setup has `30_000ms` hook headroom. `npm run typecheck` -> exit `0`, no diagnostics; `npm run build` -> exit `0`, `746 modules transformed`, `Σ Total size: 6.45 MB (1.62 MB gzip)`, launch-readiness manifest generated for `de7efa3f`; existing sourcemap, chunk-size, and Node `DEP0155` warnings were non-fatal.
- Repository gates: `python scripts/checks/run_hard.py --all` -> exit `0`, `hard=0`, ratchet không tăng (R50.3 `7 < baseline 8`); `git diff --check` -> exit `0`.
- Official bounded backend gate: `python scripts/ops/run_backend_regression.py --deadline-seconds 7000` with a `7200s` outer timeout -> exit `0` in `6901.2s`; Phase A exit `0`, `8633 passed, 58 skipped, 111 deselected, 1 xfailed, 1 warning in 1152.25s`; Phase B exit `0`, `284 passed, 19 skipped in 5739.98s`. Captured UTF-8/CRLF receipts: stdout `10840` bytes, SHA-256 `f11b8db7d11fe8925c9ce582eff85e73ab546a8578d82f75628d8a80ac5e8b2a`; stderr `300` bytes, SHA-256 `adf1dff1272e2cc714b37a623c093f3234de49875a91888173ed88b6b1e48169`.
- Resulting contract: each mapped pinned GET has explicit encoded/decoded caps, bounded identity/gzip decoding, four-slot deadline-aware DNS admission, one absolute monotonic deadline, and deterministic local-socket coverage of the actual `_PinnedHTTPTransport` plus `httpcore.ConnectionPool` composition.
- Genuine residuals: egress denials remain operationally silent; cookie/consent redirect gates requiring a cookie jar remain incompatible; explicitly excluded outbound callers remain unmigrated; production behavior remains unobserved pending separately authorized deployment.
- Operational non-actions: no DB or `web/data.json` rewrite, no push, deploy, production mutation, secret change, or indexing change; pre-existing WAL/SHM files remained untouched.
