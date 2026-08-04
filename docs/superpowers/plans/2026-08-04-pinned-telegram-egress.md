# Pinned Telegram Egress Implementation Plan

> STATUS: active - design and implementation order approved; execute task-by-task with fresh subagents and two-stage review; no deploy, live Telegram call, production secret access, or production mutation is authorized.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route every scheduler and `python-telegram-bot` Telegram request through a bounded DNS-pinned JSON POST boundary, with safe error handling, bounded async execution, and working per-recipient retry delivery.

**Architecture:** `agent/pinned_http.py` gains a separate single-hop `post_json()` entry point while preserving `get()` exactly. `agent/telegram_pinned.py` owns the Telegram origin/method/payload contract and synchronous scheduler client; `agent/telegram_ptb.py` adapts that contract to PTB's async `BaseRequest` with dedicated bounded executors. Scheduler fan-out becomes round-based with an in-memory per-recipient outbox, and `bot_gateway.py` wires separate command and polling request instances with no unpinned fallback.

**Tech Stack:** Python 3.10+, `httpx>=0.28,<1`, `httpcore>=1.0.9,<2`, `python-telegram-bot>=22.7,<23`, stdlib `asyncio`/`concurrent.futures`/`dataclasses`/`json`/`threading`, pytest, Ruff, repository hard checks.

## Global Constraints

- Execute in `C:\Code\worktrees\vinhlong360-main-merge`; do not use or modify the dirty session worktree `C:\Code\vinhlong360`.
- Use a fresh implementation subagent for each task and perform specification-compliance review followed by code-quality review before dispatching the next task.
- Use TDD for every behavior change: add uncommitted RED tests, run and observe the intended failure, implement the smallest GREEN change, rerun the focused suite, then commit.
- Preserve the public signature and behavior of `PinnedHTTPClient.get()` exactly.
- `post_json()` is synchronous, JSON-only, single-hop, redirect-denying, proxy-free, cookie-free, and accepts no caller-defined headers.
- Telegram origin is exactly `https://api.telegram.org:443`; token-bearing paths, request/response bodies, chat IDs, message text, callback data, raw Telegram descriptions, and raw exception representations must never reach logs or exception strings.
- Command profile: methods `getMe`, `deleteWebhook`, `sendMessage`, `answerCallbackQuery`; request cap 64 KiB; encoded and decoded response caps 512 KiB; inactivity and total deadline 15 seconds; three executor workers.
- Polling profile: method `getUpdates` only; request cap 64 KiB; encoded and decoded response caps 2 MiB; long-poll timeout 20 seconds; inactivity 25 seconds; total deadline 30 seconds; one executor worker.
- Polling startup uses `bootstrap_retries=0`, `drop_pending_updates=True`, exactly `("message", "callback_query")`, and `stop_signals=None`.
- Both profiles accept only `identity` and `gzip`, disallow redirects, and use fixed audit-context literals.
- PTB must use distinct command and polling `BaseRequest` instances. Never fall back to `HTTPXRequest`, `httpx.post()`, or another unpinned transport.
- Reject GET/retrieve, multipart/file upload, unknown methods, unknown payload fields, query, fragment, encoded/alternate token paths, and off-origin destinations.
- Scheduler delivery is at-least-once. Retry transient failures at most three inline attempts with 0.5 and 1 second delays; defer 429 by bounded `retry_after`; never retry terminal/security failures.
- Retry outbox is memory-only, per recipient, maximum 50 items, maximum age 24 hours, drains at most ten due items every 60 seconds, and rechecks the current admin list before sending.
- No live Telegram/DNS/public-network calls in tests. The transport proof must use deterministic local socket pairs through the real `httpcore.ConnectionPool` and pinned network backend.
- Do not push, deploy, send a real Telegram message, rotate/read production secrets, mutate production state, run Codex Security, or touch unrelated files.

---

## File Structure

- Modify `agent/pinned_http.py`: add request-body validation, shared GET/POST hop dispatch, and public `post_json()` without changing `get()`.
- Modify `tests/test_pinned_http.py`: add JSON POST unit tests and extend the real socket-pair harness to read and assert request bodies.
- Create `agent/telegram_pinned.py`: Telegram profiles, exact endpoint/payload validation, pinned synchronous transport, response classification, and scheduler `send_message()` adapter.
- Create `tests/test_telegram_pinned.py`: endpoint, payload, response, redaction, and synchronous adapter tests.
- Modify `agent/scheduler.py`: replace direct Telegram HTTP, add round-based delivery, per-recipient outbox, retry task, and subject-free status.
- Create `agent/tests/test_scheduler_telegram.py`: scheduler fan-out, retry, queue, concurrency, authorization, and telemetry tests.
- Modify `agent/tests/test_gap_fixes.py`: replace raw-traceback source guards with safe-log behavioral coverage.
- Modify `tests/test_pinned_http_consumers.py`: make `KNOWN_UNPINNED_FETCHERS` empty after scheduler migration.
- Create `agent/telegram_ptb.py`: PTB `BaseRequest` adapter, safe response mapping, executor admission, cancellation, and lifecycle.
- Create `tests/test_telegram_ptb.py`: real PTB request-data integration and executor/lifecycle tests.
- Modify `requirements.txt`: pin `python-telegram-bot>=22.7,<23`.
- Modify `agent/bot_gateway.py`: wire command/polling requests, narrow updates, and restrict Markdown fallback.
- Create `agent/tests/test_bot_gateway_telegram.py`: builder wiring, polling arguments, fallback, and safe startup-log tests.
- Modify `docs/ROADMAP.md`: replace the residual Telegram egress line with revision-bound verified local evidence.
- Modify `docs/HANDOFF.md`: replace the out-of-scope Telegram line with the implemented contract, verification, and remaining production-observation note.

---

### Task 1: Add Bounded Pinned JSON POST

**Files:**
- Modify: `agent/pinned_http.py:28-45,51-96,1114-1249`
- Modify: `tests/test_pinned_http.py:1-16,1045-1283,1923-1948,2680-2885`

**Interfaces:**
- Consumes: existing `EgressPolicy`, `DeadlineBudget`, `_resolve_hop()`, `_PinnedHTTPTransport`, `_read_bounded_body()`, `_origin_is_allowed()`, `_log_security_denial()`, and `PinnedResponse`.
- Produces: `PinnedRequestBodyError` and `PinnedHTTPClient.post_json(url, *, json_body, max_request_bytes, user_agent, policy, audit_context) -> PinnedResponse`; a generalized private `_fetch_hop()` that still preserves the GET call path.

- [ ] **Step 1: Add RED request-body and public-contract tests**

Use the existing `inspect`, `math`, and pytest imports in `tests/test_pinned_http.py` and add:

```python
def test_post_json_rejects_oversize_before_resolution() -> None:
    calls = []

    def resolver(*args):
        calls.append(args)
        return _public_resolver(*args)

    client = ph.PinnedHTTPClient(resolver=resolver)
    with pytest.raises(ph.PinnedBodyLimitError):
        client.post_json(
            "https://example.com/bot",
            json_body={"text": "x" * 64},
            max_request_bytes=16,
            user_agent="telegram-test",
            policy=_policy(max_redirects=0),
            audit_context="telegram_test",
        )

    assert calls == []


@pytest.mark.parametrize(
    "payload",
    [["not", "a", "mapping"], {"bad": object()}, {"bad": math.nan}, {1: "bad-key"}],
)
def test_post_json_rejects_invalid_json_mapping(payload) -> None:
    client = ph.PinnedHTTPClient(resolver=lambda *_args: pytest.fail("DNS must not run"))
    with pytest.raises(ph.PinnedRequestBodyError):
        client.post_json(
            "https://example.com/bot",
            json_body=payload,
            max_request_bytes=1024,
            user_agent="telegram-test",
            policy=_policy(max_redirects=0),
            audit_context="telegram_test",
        )


def test_get_public_signature_is_unchanged() -> None:
    signature = inspect.signature(ph.PinnedHTTPClient.get)
    assert list(signature.parameters) == [
        "self", "url", "user_agent", "policy", "audit_context"
    ]
    assert signature.parameters["user_agent"].kind is inspect.Parameter.KEYWORD_ONLY


def test_post_json_public_signature_has_no_headers_cookies_or_redirect_controls() -> None:
    signature = inspect.signature(ph.PinnedHTTPClient.post_json)
    assert list(signature.parameters) == [
        "self", "url", "json_body", "max_request_bytes", "user_agent", "policy",
        "audit_context",
    ]
    assert all(
        signature.parameters[name].kind is inspect.Parameter.KEYWORD_ONLY
        for name in (
            "json_body", "max_request_bytes", "user_agent", "policy", "audit_context"
        )
    )
```

- [ ] **Step 2: Extend the real transport harness and add RED POST-wire tests**

Change `_serve_http()` so it records the complete request body rather than stopping at the header delimiter:

```python
def _serve_http(peer, response_chunks, received, response_gate) -> None:
    request = bytearray()
    request_recorded = False
    try:
        peer.settimeout(2.0)
        while b"\r\n\r\n" not in request:
            chunk = peer.recv(4096)
            if not chunk:
                break
            request.extend(chunk)
        header_end = request.find(b"\r\n\r\n")
        content_length = 0
        if header_end >= 0:
            for line in request[:header_end].split(b"\r\n")[1:]:
                name, separator, value = line.partition(b":")
                if separator and name.strip().lower() == b"content-length":
                    content_length = int(value.strip())
            expected = header_end + 4 + content_length
            while len(request) < expected:
                chunk = peer.recv(expected - len(request))
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
```

Add the real composition test:

```python
def test_real_httpcore_post_json_emits_exact_headers_and_body() -> None:
    harness = _real_transport_client(_fixed_http_response(b'{"ok":true}'))
    try:
        result = harness.client.post_json(
            "http://example.com/bot123/sendMessage",
            json_body={"chat_id": 42, "text": "Vinh Long"},
            max_request_bytes=1024,
            user_agent="telegram-test",
            policy=_policy(accepted_encodings=("identity",), max_redirects=0),
            audit_context="telegram_test",
        )
    finally:
        transport_closed = harness.cleanup()

    head, body = harness.received[0].split(b"\r\n\r\n", 1)
    assert head.startswith(b"POST /bot123/sendMessage HTTP/1.1\r\n")
    assert b"\r\nHost: example.com\r\n" in head
    assert b"\r\nUser-Agent: telegram-test\r\n" in head
    assert b"\r\nAccept: application/json\r\n" in head
    assert b"\r\nContent-Type: application/json\r\n" in head
    names = {
        line.partition(b":")[0].lower()
        for line in head.split(b"\r\n")[1:]
        if b":" in line
    }
    assert names == {
        b"host", b"user-agent", b"accept-encoding", b"accept",
        b"content-type", b"content-length",
    }
    assert body == b'{"chat_id":42,"text":"Vinh Long"}'
    assert result.content == b'{"ok":true}'
    assert transport_closed is True
```

Add the following POST-specific tests:

```python
@pytest.mark.parametrize("status", [300, 301, 302, 303, 307, 308, 399])
def test_post_json_rejects_every_redirect_status(status: int) -> None:
    calls = []

    def factory(_hop, _policy, _budget):
        calls.append(status)
        return httpx.MockTransport(
            lambda request: httpx.Response(
                status,
                headers={"location": "https://example.com/other"},
                request=request,
            )
        )

    client = ph.PinnedHTTPClient(
        resolver=_public_resolver,
        transport_factory=factory,
    )
    with pytest.raises(ph.RedirectPolicyError):
        client.post_json(
            "https://example.com/bot",
            json_body={"ok": True},
            max_request_bytes=1024,
            user_agent="telegram-test",
            policy=_policy(max_redirects=0),
            audit_context="telegram_test",
        )
    assert calls == [status]


def test_post_json_has_no_cookie_and_ignores_ambient_proxy(monkeypatch) -> None:
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:9")
    seen = []

    def factory(_hop, _policy, _budget):
        def handler(request):
            seen.append(request)
            return httpx.Response(200, content=b'{"ok":true}', request=request)
        return httpx.MockTransport(handler)

    ph.PinnedHTTPClient(
        resolver=_public_resolver,
        transport_factory=factory,
    ).post_json(
        "https://example.com/bot",
        json_body={"ok": True},
        max_request_bytes=1024,
        user_agent="telegram-test",
        policy=_policy(max_redirects=0),
        audit_context="telegram_test",
    )
    assert seen[0].headers.get("cookie") is None


def test_post_json_uses_a_fresh_transport_for_each_call() -> None:
    created = []

    def factory(_hop, _policy, _budget):
        created.append(object())
        return httpx.MockTransport(
            lambda request: httpx.Response(200, content=b'{"ok":true}', request=request)
        )

    client = ph.PinnedHTTPClient(resolver=_public_resolver, transport_factory=factory)
    for _ in range(2):
        client.post_json(
            "https://example.com/bot",
            json_body={"ok": True},
            max_request_bytes=1024,
            user_agent="telegram-test",
            policy=_policy(max_redirects=0),
            audit_context="telegram_test",
        )
    assert len(created) == 2


def test_post_json_reuses_bounded_gzip_decoder() -> None:
    encoded = gzip.compress(b'{"ok":true}')

    def factory(_hop, _policy, _budget):
        return httpx.MockTransport(lambda request: httpx.Response(
            200,
            headers={"content-encoding": "gzip"},
            stream=_OneChunkStream(encoded),
            request=request,
        ))

    result = ph.PinnedHTTPClient(
        resolver=_public_resolver,
        transport_factory=factory,
    ).post_json(
        "https://example.com/bot",
        json_body={"ok": True},
        max_request_bytes=1024,
        user_agent="telegram-test",
        policy=_policy(max_redirects=0),
        audit_context="telegram_test",
    )
    assert result.content == b'{"ok":true}'


@pytest.mark.parametrize(
    ("headers", "content", "error_type"),
    [
        ({"content-encoding": "br"}, b"x", ph.PinnedContentEncodingError),
        ({}, b"x" * 17, ph.PinnedBodyLimitError),
        ({"content-encoding": "gzip"}, gzip.compress(b"x" * 33), ph.PinnedBodyLimitError),
    ],
)
def test_post_json_reuses_response_encoding_and_body_limits(headers, content, error_type) -> None:
    def factory(_hop, _policy, _budget):
        return httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                headers=headers,
                stream=_OneChunkStream(content),
                request=request,
            )
        )

    client = ph.PinnedHTTPClient(resolver=_public_resolver, transport_factory=factory)
    with pytest.raises(error_type):
        client.post_json(
            "https://example.com/bot",
            json_body={"ok": True},
            max_request_bytes=1024,
            user_agent="telegram-test",
            policy=_policy(
                max_encoded_bytes=16,
                max_decoded_bytes=32,
                max_redirects=0,
            ),
            audit_context="telegram_test",
        )


def test_post_json_deadline_starts_before_resolution() -> None:
    times = iter([0.0, 2.0])
    calls = []
    client = ph.PinnedHTTPClient(
        resolver=lambda *args: calls.append(args) or _public_resolver(*args),
        monotonic=lambda: next(times),
    )
    with pytest.raises(ph.PinnedDeadlineExceeded):
        client.post_json(
            "https://example.com/bot",
            json_body={"ok": True},
            max_request_bytes=1024,
            user_agent="telegram-test",
            policy=_policy(total_timeout_seconds=1.0, max_redirects=0),
            audit_context="telegram_test",
        )
    assert calls == []


def test_post_json_security_denial_logs_safe_origin_only(caplog) -> None:
    token = "123456:SECRET_TOKEN_SENTINEL"

    def resolver(_host, _port, _budget):
        raise ph.BlockedAddressError("MESSAGE_SENTINEL")

    client = ph.PinnedHTTPClient(resolver=resolver)
    with caplog.at_level("WARNING", logger="security.egress"):
        with pytest.raises(ph.BlockedAddressError):
            client.post_json(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json_body={"text": "BODY_SENTINEL"},
                max_request_bytes=1024,
                user_agent="telegram-test",
                policy=_policy(
                    allowed_origins=("https://api.telegram.org",),
                    max_redirects=0,
                ),
                audit_context="telegram_sdk_command",
            )
    output = "\n".join(record.getMessage() for record in caplog.records)
    assert "target=https://api.telegram.org" in output
    for secret in (token, "sendMessage", "MESSAGE_SENTINEL", "BODY_SENTINEL"):
        assert secret not in output
```

- [ ] **Step 3: Run the focused tests and verify RED**

```powershell
python -m pytest tests/test_pinned_http.py -q -k "post_json or get_public_signature"
```

Expected: FAIL because `PinnedRequestBodyError` and `post_json()` do not exist and the real harness does not yet observe a POST body.

- [ ] **Step 4: Implement the request-body error and shared hop dispatcher**

In `agent/pinned_http.py`, import `json` and `Mapping`, then add:

```python
class PinnedRequestBodyError(PinnedHTTPError):
    pass
```

Generalize `_fetch_hop()` with private fixed request inputs while preserving all existing GET behavior:

```python
def _fetch_hop(
    hop: ResolvedHop,
    *,
    method: str,
    request_body: bytes | None,
    user_agent: str,
    cookie_header: str | None,
    policy: EgressPolicy,
    budget: DeadlineBudget,
    transport_factory: TransportFactory,
    monotonic: MonotonicClock = time.monotonic,
) -> tuple[int, tuple[tuple[str, str], ...], bytes, str | None]:
    try:
        budget.remaining(monotonic=monotonic)
        transport = transport_factory(hop, policy, budget)
        client_headers = {
            "User-Agent": user_agent,
            "Accept-Encoding": ", ".join(policy.accepted_encodings),
        }
        if method == "POST":
            client_headers["Accept"] = "application/json"
            client_headers["Content-Type"] = "application/json"
        if cookie_header:
            client_headers["Cookie"] = cookie_header
        with httpx.Client(
            transport=transport,
            follow_redirects=False,
            trust_env=False,
            headers=client_headers,
        ) as client:
            request = client.build_request(
                method,
                str(hop.url),
                content=request_body,
                timeout=httpx.Timeout(policy.inactivity_timeout_seconds),
            )
            if method == "POST":
                allowed = {
                    "host", "user-agent", "accept-encoding", "accept",
                    "content-type", "content-length",
                }
                for name in tuple(request.headers):
                    if name.lower() not in allowed:
                        del request.headers[name]
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
```

Update the existing GET call to pass `method="GET"` and `request_body=None`; do not otherwise change its loop, cookies, redirects, logging, or return value.

- [ ] **Step 5: Implement `PinnedHTTPClient.post_json()`**

Add the public method after `get()`:

```python
def post_json(
    self,
    url: str,
    *,
    json_body: Mapping[str, object],
    max_request_bytes: int,
    user_agent: str,
    policy: EgressPolicy,
    audit_context: str,
) -> PinnedResponse:
    budget = DeadlineBudget.start(
        policy.total_timeout_seconds,
        monotonic=self._monotonic,
    )
    if max_request_bytes <= 0:
        raise ValueError("max_request_bytes must be positive")
    if not isinstance(json_body, Mapping) or any(
        not isinstance(key, str) for key in json_body
    ):
        raise PinnedRequestBodyError("JSON request body must be a string-keyed mapping")
    try:
        request_body = json.dumps(
            dict(json_body),
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise PinnedRequestBodyError("JSON request body is not serializable") from exc
    if len(request_body) > max_request_bytes:
        raise PinnedBodyLimitError("request body exceeds policy")

    current = _parse_url(url)
    if not _origin_is_allowed(current, policy):
        raise InvalidDestinationError("destination origin is not allowed")
    try:
        budget.remaining(monotonic=self._monotonic)
        hop = _resolve_hop(current, self._resolver, budget)
        status, headers, content, location = _fetch_hop(
            hop,
            method="POST",
            request_body=request_body,
            user_agent=user_agent,
            cookie_header=None,
            policy=policy,
            budget=budget,
            transport_factory=self._transport_factory,
            monotonic=self._monotonic,
        )
        if 300 <= status < 400 or location is not None:
            raise RedirectPolicyError("JSON POST redirects are not allowed")
        budget.remaining(monotonic=self._monotonic)
        return PinnedResponse(status, str(hop.url), headers, content, ())
    except (BlockedAddressError, PeerMismatchError, RedirectPolicyError) as exc:
        _log_security_denial(audit_context, current, 0, exc)
        raise
```

- [ ] **Step 6: Run focused and GET-regression suites**

```powershell
python -m pytest tests/test_pinned_http.py -q
python -m pytest tests/test_admin_pinned_http.py tests/test_auto_learn_fetch.py tests/test_crawler_ssrf.py tests/test_geocode_pinned.py tests/test_gpt55_quality_burst.py tests/test_realtime_pinned.py tests/test_pinned_http_consumers.py -q
python -m ruff check agent/pinned_http.py tests/test_pinned_http.py
git diff --check
```

Expected: all commands exit 0; existing GET and mapped-consumer assertions remain green.

- [ ] **Step 7: Commit Task 1**

```powershell
git add -- agent/pinned_http.py tests/test_pinned_http.py
git commit -m "feat: add bounded pinned JSON POST"
```

---

### Task 2: Add the Telegram Contract and Synchronous Adapter

**Files:**
- Create: `agent/telegram_pinned.py`
- Create: `tests/test_telegram_pinned.py`

**Interfaces:**
- Consumes: `PinnedHTTPClient.post_json()`, `EgressPolicy`, `PinnedResponse`, and typed pinned exceptions from Task 1.
- Produces: `COMMAND_PROFILE`, `POLLING_PROFILE`, `TelegramPinnedTransport.request_url()`, `TelegramDeliveryState`, `TelegramDeliveryResult`, `TelegramBotAPI.send_message()`, and `sanitize_ptb_response()` for Task 4.

- [ ] **Step 1: Add RED profile, endpoint, and payload tests**

Create `tests/test_telegram_pinned.py` with an injected pinned client:

```python
from __future__ import annotations

import json
from dataclasses import replace

import pytest

import pinned_http as ph
import telegram_pinned as tp


TOKEN = "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghi"


class RecordingPinnedClient:
    def __init__(self, response=None, error=None) -> None:
        self.response = response or ph.PinnedResponse(
            200,
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            (("content-type", "application/json"),),
            b'{"ok":true,"result":true}',
            (),
        )
        self.error = error
        self.calls = []

    def post_json(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self.error:
            raise self.error
        return self.response


@pytest.mark.parametrize(
    "url",
    [
        f"http://api.telegram.org/bot{TOKEN}/sendMessage",
        f"https://API.TELEGRAM.ORG/bot{TOKEN}/sendMessage",
        f"https://api.telegram.org:444/bot{TOKEN}/sendMessage",
        f"https://user@api.telegram.org/bot{TOKEN}/sendMessage",
        f"https://evil.example/bot{TOKEN}/sendMessage",
        f"https://api.telegram.org/bot{TOKEN}/sendMessage?x=1",
        f"https://api.telegram.org/bot{TOKEN}/sendMessage#x",
        f"https://api.telegram.org/bot{TOKEN}%2FsendMessage",
        "https://api.telegram.org/botwrong/sendMessage",
    ],
)
def test_exact_telegram_url_contract_rejects_alternates(url: str) -> None:
    transport = tp.TelegramPinnedTransport(
        TOKEN,
        tp.COMMAND_PROFILE,
        client=RecordingPinnedClient(),
        audit_context="telegram_sdk_command",
    )
    with pytest.raises(tp.TelegramContractError):
        transport.request_url(url, {})


@pytest.mark.parametrize("token", ["", "non-ascii-đ", "bad/token", "bad%token", "bad\\token"])
def test_configured_token_contract_rejects_unsafe_values(token: str) -> None:
    with pytest.raises(tp.TelegramContractError, match="telegram_token_invalid") as exc_info:
        tp.TelegramPinnedTransport(
            token,
            tp.COMMAND_PROFILE,
            client=RecordingPinnedClient(),
            audit_context="telegram_sdk_command",
        )
    assert token not in str(exc_info.value)


def test_explicit_default_port_is_accepted() -> None:
    pinned = RecordingPinnedClient()
    transport = tp.TelegramPinnedTransport(
        TOKEN,
        tp.COMMAND_PROFILE,
        client=pinned,
        audit_context="telegram_sdk_command",
    )
    transport.request_url(
        f"https://api.telegram.org:443/bot{TOKEN}/getMe",
        {},
    )
    assert len(pinned.calls) == 1


@pytest.mark.parametrize(
    ("method", "parameters"),
    [
        ("getUpdates", {}),
        ("sendPhoto", {"chat_id": 1}),
        ("sendMessage", {"chat_id": 1, "text": "ok", "unknown": True}),
        ("answerCallbackQuery", {"callback_query_id": "x", "text": "not allowed"}),
    ],
)
def test_command_contract_rejects_unknown_method_or_field(method, parameters) -> None:
    transport = tp.TelegramPinnedTransport(
        TOKEN,
        tp.COMMAND_PROFILE,
        client=RecordingPinnedClient(),
        audit_context="telegram_sdk_command",
    )
    with pytest.raises(tp.TelegramContractError):
        transport.request_url(
            f"https://api.telegram.org/bot{TOKEN}/{method}",
            parameters,
        )
```

Add positive and negative value tests with exact cases:

```python
@pytest.mark.parametrize(
    ("profile", "method", "parameters"),
    [
        (tp.COMMAND_PROFILE, "getMe", {}),
        (tp.COMMAND_PROFILE, "deleteWebhook", {"drop_pending_updates": True}),
        (tp.COMMAND_PROFILE, "sendMessage", {"chat_id": -42, "text": "ok", "parse_mode": "Markdown"}),
        (tp.COMMAND_PROFILE, "answerCallbackQuery", {"callback_query_id": "callback-id"}),
        (tp.POLLING_PROFILE, "getUpdates", {"timeout": 20, "allowed_updates": ["message", "callback_query"]}),
    ],
)
def test_allowed_telegram_calls_reach_pinned_post(profile, method, parameters) -> None:
    pinned = RecordingPinnedClient()
    transport = tp.TelegramPinnedTransport(
        TOKEN,
        profile,
        client=pinned,
        audit_context=(
            "telegram_sdk_polling" if profile is tp.POLLING_PROFILE
            else "telegram_sdk_command"
        ),
    )
    transport.request_url(
        f"https://api.telegram.org/bot{TOKEN}/{method}",
        parameters,
    )
    assert pinned.calls[0][1]["max_request_bytes"] == 64 * 1024


@pytest.mark.parametrize(
    ("profile", "method", "parameters"),
    [
        (tp.POLLING_PROFILE, "getUpdates", {"timeout": 21, "allowed_updates": ["message", "callback_query"]}),
        (tp.POLLING_PROFILE, "getUpdates", {"timeout": 20, "allowed_updates": ["message", "message"]}),
        (tp.POLLING_PROFILE, "getUpdates", {"timeout": 20, "allowed_updates": ["message", "channel_post"]}),
        (tp.COMMAND_PROFILE, "sendMessage", {"chat_id": "@channel", "text": "ok"}),
        (tp.COMMAND_PROFILE, "sendMessage", {"chat_id": 1, "text": "x" * 4097}),
        (tp.COMMAND_PROFILE, "sendMessage", {"chat_id": 1, "text": "ok", "parse_mode": "HTML"}),
        (tp.COMMAND_PROFILE, "answerCallbackQuery", {"callback_query_id": ""}),
    ],
)
def test_telegram_value_contract_rejects_out_of_scope_values(profile, method, parameters) -> None:
    transport = tp.TelegramPinnedTransport(
        TOKEN,
        profile,
        client=RecordingPinnedClient(),
        audit_context=(
            "telegram_sdk_polling" if profile is tp.POLLING_PROFILE
            else "telegram_sdk_command"
        ),
    )
    with pytest.raises(tp.TelegramContractError):
        transport.request_url(
            f"https://api.telegram.org/bot{TOKEN}/{method}",
            parameters,
        )
```

- [ ] **Step 2: Add RED response-classification and redaction tests**

Add exact classification cases:

```python
@pytest.mark.parametrize(
    ("status", "body", "state", "code", "retry_after"),
    [
        (200, b'{"ok":true,"result":true}', tp.TelegramDeliveryState.SUCCESS, "telegram_ok", None),
        (429, b'{"ok":false,"error_code":429,"parameters":{"retry_after":17}}', tp.TelegramDeliveryState.DEFERRED, "telegram_rate_limited", 17),
        (503, b'{"ok":false}', tp.TelegramDeliveryState.TRANSIENT, "telegram_http_5xx", None),
        (400, b'{"ok":false,"error_code":400}', tp.TelegramDeliveryState.TERMINAL, "telegram_bad_request", None),
        (401, b'{"ok":false,"error_code":401}', tp.TelegramDeliveryState.TERMINAL, "telegram_invalid_token", None),
        (409, b'{"ok":false,"error_code":409}', tp.TelegramDeliveryState.TERMINAL, "telegram_conflict", None),
        (200, b"not-json", tp.TelegramDeliveryState.TRANSIENT, "telegram_invalid_json", None),
        (200, b'{"result":true}', tp.TelegramDeliveryState.TRANSIENT, "telegram_invalid_schema", None),
        (200, b'{"ok":false}', tp.TelegramDeliveryState.TRANSIENT, "telegram_invalid_schema", None),
    ],
)
def test_send_message_classifies_response(status, body, state, code, retry_after) -> None:
    pinned = RecordingPinnedClient(
        response=ph.PinnedResponse(status, "https://api.telegram.org", (), body, ())
    )
    result = tp.TelegramBotAPI(TOKEN, client=pinned).send_message(42, "hello")
    assert result == tp.TelegramDeliveryResult(state, code, retry_after)


def test_contract_errors_never_expose_sensitive_sentinels(caplog) -> None:
    token = "987654:SECRET_TOKEN_SENTINEL_abcdefghijklmnopqrstuvwxyz"
    chat_id = "-1001234567890"
    text = "MESSAGE_SENTINEL"
    api = tp.TelegramBotAPI(token, client=RecordingPinnedClient(error=ph.PinnedTransportError(text)))

    with caplog.at_level("DEBUG"):
        result = api.send_message(chat_id, text)

    output = "\n".join(record.getMessage() for record in caplog.records)
    assert result.code == "telegram_transport_error"
    for secret in (token, chat_id, text, "SECRET_TOKEN_SENTINEL"):
        assert secret not in output
        assert secret not in repr(result)
```

Add exact exception and rate-limit mapping tests:

```python
@pytest.mark.parametrize(
    ("error", "state", "code"),
    [
        (ph.PinnedBodyLimitError("SECRET"), tp.TelegramDeliveryState.TERMINAL, "telegram_protocol_limit"),
        (ph.PinnedContentEncodingError("SECRET"), tp.TelegramDeliveryState.TERMINAL, "telegram_protocol_limit"),
        (ph.RedirectPolicyError("SECRET"), tp.TelegramDeliveryState.TERMINAL, "telegram_security_denied"),
        (ph.BlockedAddressError("SECRET"), tp.TelegramDeliveryState.TERMINAL, "telegram_security_denied"),
        (ph.PeerMismatchError("SECRET"), tp.TelegramDeliveryState.TERMINAL, "telegram_security_denied"),
        (ph.PinnedTransportError("SECRET"), tp.TelegramDeliveryState.TRANSIENT, "telegram_transport_error"),
        (ph.ResolutionError("SECRET"), tp.TelegramDeliveryState.TRANSIENT, "telegram_resolution_error"),
        (ph.PinnedDeadlineExceeded("SECRET"), tp.TelegramDeliveryState.TRANSIENT, "telegram_timeout"),
        (RuntimeError("SECRET"), tp.TelegramDeliveryState.TERMINAL, "telegram_internal_error"),
    ],
)
def test_send_message_maps_typed_pinned_failures_without_message(error, state, code) -> None:
    result = tp.TelegramBotAPI(TOKEN, client=RecordingPinnedClient(error=error)).send_message(42, "hello")
    assert result == tp.TelegramDeliveryResult(state, code)
    assert "SECRET" not in repr(result)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [(0, 60), (-1, 60), ("17", 60), (17, 17), (7200, 3600)],
)
def test_retry_after_is_positive_and_capped(raw, expected) -> None:
    body = json.dumps({
        "ok": False,
        "error_code": 429,
        "parameters": {"retry_after": raw},
    }).encode("utf-8")
    pinned = RecordingPinnedClient(
        response=ph.PinnedResponse(429, "https://api.telegram.org", (), body, ())
    )
    assert tp.TelegramBotAPI(TOKEN, client=pinned).send_message(42, "hello").retry_after == expected


def test_transport_redacts_token_from_returned_response_and_repr() -> None:
    pinned = RecordingPinnedClient()
    transport = tp.TelegramPinnedTransport(
        TOKEN,
        tp.COMMAND_PROFILE,
        client=pinned,
        audit_context="telegram_sdk_command",
    )
    response = transport.request_url(
        f"https://api.telegram.org/bot{TOKEN}/getMe",
        {},
    )
    assert response.url == tp.TELEGRAM_ORIGIN
    assert TOKEN not in repr(response)
    assert TOKEN not in repr(transport)


def test_unknown_profile_and_audit_context_fail_closed() -> None:
    widened = replace(
        tp.COMMAND_PROFILE,
        methods=tp.COMMAND_PROFILE.methods | {"sendPhoto"},
    )
    with pytest.raises(tp.TelegramContractError, match="telegram_profile_denied"):
        tp.TelegramPinnedTransport(
            TOKEN,
            widened,
            client=RecordingPinnedClient(),
            audit_context="telegram_sdk_command",
        )
    with pytest.raises(tp.TelegramContractError, match="telegram_audit_context_denied"):
        tp.TelegramPinnedTransport(
            TOKEN,
            tp.COMMAND_PROFILE,
            client=RecordingPinnedClient(),
            audit_context="caller_supplied_value",
        )


def test_profile_field_maps_cannot_be_widened_at_runtime() -> None:
    with pytest.raises(TypeError):
        tp.COMMAND_PROFILE.fields["sendPhoto"] = frozenset({"chat_id"})
```

- [ ] **Step 3: Run tests and verify RED**

```powershell
python -m pytest tests/test_telegram_pinned.py -q
```

Expected: collection fails because `telegram_pinned` and its contracts do not exist.

- [ ] **Step 4: Implement profiles and exact request validation**

Create `agent/telegram_pinned.py` with these public contracts:

```python
from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, replace
from enum import Enum
from types import MappingProxyType
from urllib.parse import urlsplit

from pinned_http import (
    BlockedAddressError,
    EgressPolicy,
    InvalidDestinationError,
    PeerMismatchError,
    PinnedBodyLimitError,
    PinnedContentEncodingError,
    PinnedDeadlineExceeded,
    PinnedHTTPClient,
    PinnedRequestBodyError,
    PinnedResponse,
    PinnedTransportError,
    RedirectPolicyError,
    ResolutionError,
)


TELEGRAM_ORIGIN = "https://api.telegram.org"
TELEGRAM_USER_AGENT = "vinhlong360-telegram/1"
_PROFILE_AUDIT_CONTEXTS = {
    "command": frozenset({"telegram_scheduler", "telegram_sdk_command"}),
    "polling": frozenset({"telegram_sdk_polling"}),
}


class TelegramContractError(Exception):
    pass


class TelegramProtocolError(Exception):
    pass


@dataclass(frozen=True)
class TelegramEgressProfile:
    name: str
    methods: frozenset[str]
    fields: Mapping[str, frozenset[str]]
    policy: EgressPolicy
    max_request_bytes: int
    default_read_timeout: float
    workers: int


COMMAND_PROFILE = TelegramEgressProfile(
    name="command",
    methods=frozenset({"getMe", "deleteWebhook", "sendMessage", "answerCallbackQuery"}),
    fields=MappingProxyType({
        "getMe": frozenset(),
        "deleteWebhook": frozenset({"drop_pending_updates"}),
        "sendMessage": frozenset({
            "chat_id", "text", "parse_mode", "reply_markup",
            "link_preview_options", "message_thread_id",
            "direct_messages_topic_id", "business_connection_id",
            "reply_parameters",
        }),
        "answerCallbackQuery": frozenset({"callback_query_id"}),
    }),
    policy=EgressPolicy(
        max_encoded_bytes=512 * 1024,
        max_decoded_bytes=512 * 1024,
        accepted_encodings=("gzip", "identity"),
        inactivity_timeout_seconds=15.0,
        total_timeout_seconds=15.0,
        max_redirects=0,
        allowed_origins=(TELEGRAM_ORIGIN,),
    ),
    max_request_bytes=64 * 1024,
    default_read_timeout=15.0,
    workers=3,
)


POLLING_PROFILE = TelegramEgressProfile(
    name="polling",
    methods=frozenset({"getUpdates"}),
    fields=MappingProxyType({
        "getUpdates": frozenset({"offset", "limit", "timeout", "allowed_updates"})
    }),
    policy=EgressPolicy(
        max_encoded_bytes=2 * 1024 * 1024,
        max_decoded_bytes=2 * 1024 * 1024,
        accepted_encodings=("gzip", "identity"),
        inactivity_timeout_seconds=25.0,
        total_timeout_seconds=30.0,
        max_redirects=0,
        allowed_origins=(TELEGRAM_ORIGIN,),
    ),
    max_request_bytes=64 * 1024,
    default_read_timeout=5.0,
    workers=1,
)
```

Implement token, URL, and payload validation exactly:

```python
def _validate_token(token: str) -> str:
    if not isinstance(token, str) or not token or len(token) > 256:
        raise TelegramContractError("telegram_token_invalid")
    try:
        token.encode("ascii")
    except UnicodeEncodeError:
        raise TelegramContractError("telegram_token_invalid") from None
    if any(char in token for char in "/?#%\\") or any(
        ord(char) < 33 or ord(char) > 126 for char in token
    ):
        raise TelegramContractError("telegram_token_invalid")
    return token


def _method_from_url(url: str, token: str, profile: TelegramEgressProfile) -> str:
    try:
        parsed = urlsplit(url)
    except (TypeError, ValueError):
        raise TelegramContractError("telegram_url_denied") from None
    if (
        parsed.scheme != "https"
        or parsed.netloc not in {"api.telegram.org", "api.telegram.org:443"}
        or parsed.query
        or parsed.fragment
    ):
        raise TelegramContractError("telegram_url_denied")
    prefix = f"/bot{token}/"
    raw_path = parsed.path
    if not raw_path.startswith(prefix):
        raise TelegramContractError("telegram_url_denied")
    method = raw_path[len(prefix):]
    if "/" in method or method not in profile.methods:
        raise TelegramContractError("telegram_method_denied")
    if raw_path != f"{prefix}{method}":
        raise TelegramContractError("telegram_url_denied")
    return method


def _validate_parameters(
    method: str,
    parameters: Mapping[str, object],
    profile: TelegramEgressProfile,
) -> dict[str, object]:
    if not isinstance(parameters, Mapping) or any(not isinstance(key, str) for key in parameters):
        raise TelegramContractError("telegram_payload_denied")
    allowed = profile.fields.get(method)
    if allowed is None or not set(parameters).issubset(allowed):
        raise TelegramContractError("telegram_payload_denied")
    normalized = dict(parameters)
    if method == "deleteWebhook" and "drop_pending_updates" in normalized:
        if not isinstance(normalized["drop_pending_updates"], bool):
            raise TelegramContractError("telegram_payload_denied")
    if method == "getUpdates":
        timeout = normalized.get("timeout", 0)
        updates = normalized.get("allowed_updates")
        if isinstance(timeout, bool) or not isinstance(timeout, int) or not 0 <= timeout <= 20:
            raise TelegramContractError("telegram_payload_denied")
        if not isinstance(updates, (list, tuple)) or list(updates) not in (
            ["message", "callback_query"],
            ["callback_query", "message"],
        ):
            raise TelegramContractError("telegram_payload_denied")
        normalized["allowed_updates"] = list(updates)
    if method == "sendMessage":
        chat_id = normalized.get("chat_id")
        text = normalized.get("text")
        if not (
            isinstance(chat_id, int) and not isinstance(chat_id, bool)
            or isinstance(chat_id, str) and re.fullmatch(r"[+-]?\d+", chat_id)
        ):
            raise TelegramContractError("telegram_payload_denied")
        if not isinstance(text, str) or len(text) > 4096:
            raise TelegramContractError("telegram_payload_denied")
        if normalized.get("parse_mode", "Markdown") != "Markdown":
            raise TelegramContractError("telegram_payload_denied")
    if method == "answerCallbackQuery":
        callback_id = normalized.get("callback_query_id")
        if not isinstance(callback_id, str) or not 1 <= len(callback_id) <= 256:
            raise TelegramContractError("telegram_payload_denied")
    return normalized
```

Implement the transport interface:

```python
class TelegramPinnedTransport:
    def __init__(
        self,
        token: str,
        profile: TelegramEgressProfile,
        *,
        client: PinnedHTTPClient | None = None,
        audit_context: str,
    ) -> None:
        self._token = _validate_token(token)
        if profile is not COMMAND_PROFILE and profile is not POLLING_PROFILE:
            raise TelegramContractError("telegram_profile_denied")
        if audit_context not in _PROFILE_AUDIT_CONTEXTS[profile.name]:
            raise TelegramContractError("telegram_audit_context_denied")
        self.profile = profile
        self._client = client or PinnedHTTPClient()
        self._audit_context = audit_context

    def request_url(
        self,
        url: str,
        parameters: Mapping[str, object],
        *,
        total_timeout_seconds: float | None = None,
        inactivity_timeout_seconds: float | None = None,
    ) -> PinnedResponse:
        method = _method_from_url(url, self._token, self.profile)
        normalized = _validate_parameters(method, parameters, self.profile)
        policy = self.profile.policy
        if total_timeout_seconds is not None and total_timeout_seconds <= 0:
            raise PinnedDeadlineExceeded("telegram request deadline exceeded")
        if inactivity_timeout_seconds is not None and inactivity_timeout_seconds <= 0:
            raise PinnedDeadlineExceeded("telegram request deadline exceeded")
        if total_timeout_seconds is not None or inactivity_timeout_seconds is not None:
            policy = replace(
                policy,
                total_timeout_seconds=min(
                    policy.total_timeout_seconds,
                    total_timeout_seconds
                    if total_timeout_seconds is not None
                    else policy.total_timeout_seconds,
                ),
                inactivity_timeout_seconds=min(
                    policy.inactivity_timeout_seconds,
                    inactivity_timeout_seconds
                    if inactivity_timeout_seconds is not None
                    else policy.inactivity_timeout_seconds,
                ),
            )
        response = self._client.post_json(
            url,
            json_body=normalized,
            max_request_bytes=self.profile.max_request_bytes,
            user_agent=TELEGRAM_USER_AGENT,
            policy=policy,
            audit_context=self._audit_context,
        )
        return replace(response, url=TELEGRAM_ORIGIN, redirects=())
```

- [ ] **Step 5: Implement safe classification and scheduler API**

Add:

```python
class TelegramDeliveryState(str, Enum):
    SUCCESS = "success"
    DEFERRED = "deferred"
    TRANSIENT = "transient"
    TERMINAL = "terminal"


@dataclass(frozen=True)
class TelegramDeliveryResult:
    state: TelegramDeliveryState
    code: str
    retry_after: int | None = None

    @property
    def succeeded(self) -> bool:
        return self.state is TelegramDeliveryState.SUCCESS
```

Implement strict UTF-8/JSON object parsing and classification without logging raw content. Map pinned exceptions by exact type, not by their message. `TelegramBotAPI.send_message()` must use the command transport with audit context `telegram_scheduler` and return only `TelegramDeliveryResult`:

```python
def classify_delivery_response(response: PinnedResponse) -> TelegramDeliveryResult:
    try:
        data = _decode_telegram_object(response.content)
    except TelegramProtocolError:
        return TelegramDeliveryResult(
            TelegramDeliveryState.TRANSIENT,
            "telegram_invalid_json",
        )
    if 200 <= response.status_code < 300 and data.get("ok") is True:
        return TelegramDeliveryResult(TelegramDeliveryState.SUCCESS, "telegram_ok")

    if data.get("ok") is not False:
        return TelegramDeliveryResult(
            TelegramDeliveryState.TRANSIENT,
            "telegram_invalid_schema",
        )

    raw_code = data.get("error_code")
    code = raw_code if isinstance(raw_code, int) and not isinstance(raw_code, bool) else response.status_code
    if code == 429:
        parameters = data.get("parameters")
        retry_after = _retry_after(parameters.get("retry_after")) if isinstance(parameters, dict) else None
        return TelegramDeliveryResult(
            TelegramDeliveryState.DEFERRED,
            "telegram_rate_limited",
            retry_after or 60,
        )
    if response.status_code >= 500 or code >= 500:
        return TelegramDeliveryResult(
            TelegramDeliveryState.TRANSIENT,
            "telegram_http_5xx",
        )
    if not 400 <= code < 500:
        return TelegramDeliveryResult(
            TelegramDeliveryState.TRANSIENT,
            "telegram_invalid_schema",
        )
    terminal_code = {
        400: "telegram_bad_request",
        401: "telegram_invalid_token",
        403: "telegram_forbidden",
        404: "telegram_invalid_token",
        409: "telegram_conflict",
    }.get(code, "telegram_http_4xx")
    return TelegramDeliveryResult(TelegramDeliveryState.TERMINAL, terminal_code)


class TelegramBotAPI:
    def __init__(self, token: str, *, client: PinnedHTTPClient | None = None) -> None:
        self._token = _validate_token(token)
        self._transport = TelegramPinnedTransport(
            self._token,
            COMMAND_PROFILE,
            client=client,
            audit_context="telegram_scheduler",
        )

    def send_message(
        self,
        chat_id: int | str,
        text: str,
        *,
        parse_mode: str = "Markdown",
    ) -> TelegramDeliveryResult:
        url = f"{TELEGRAM_ORIGIN}/bot{self._token}/sendMessage"
        try:
            response = self._transport.request_url(
                url,
                {"chat_id": chat_id, "text": text, "parse_mode": parse_mode},
            )
        except PinnedDeadlineExceeded:
            return TelegramDeliveryResult(TelegramDeliveryState.TRANSIENT, "telegram_timeout")
        except ResolutionError:
            return TelegramDeliveryResult(TelegramDeliveryState.TRANSIENT, "telegram_resolution_error")
        except PinnedTransportError:
            return TelegramDeliveryResult(TelegramDeliveryState.TRANSIENT, "telegram_transport_error")
        except (TelegramContractError, PinnedRequestBodyError):
            return TelegramDeliveryResult(TelegramDeliveryState.TERMINAL, "telegram_contract_denied")
        except (InvalidDestinationError, BlockedAddressError, PeerMismatchError, RedirectPolicyError):
            return TelegramDeliveryResult(TelegramDeliveryState.TERMINAL, "telegram_security_denied")
        except (PinnedBodyLimitError, PinnedContentEncodingError):
            return TelegramDeliveryResult(TelegramDeliveryState.TERMINAL, "telegram_protocol_limit")
        except Exception:
            return TelegramDeliveryResult(TelegramDeliveryState.TERMINAL, "telegram_internal_error")
        return classify_delivery_response(response)
```

Add `sanitize_ptb_response(response) -> tuple[int, bytes]` now, even though Task 4 is its first consumer. It returns the original success body only after validating a JSON object with `ok is True`; for errors it returns compact safe JSON and preserves only bounded numeric `parameters.retry_after`:

```python
def _decode_telegram_object(content: bytes) -> dict:
    try:
        value = json.loads(content.decode("utf-8", "strict"))
    except (UnicodeDecodeError, ValueError):
        raise TelegramProtocolError("telegram_invalid_json") from None
    if not isinstance(value, dict):
        raise TelegramProtocolError("telegram_invalid_json")
    return value


def _retry_after(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return None
    return min(value, 3600)


def sanitize_ptb_response(response: PinnedResponse) -> tuple[int, bytes]:
    data = _decode_telegram_object(response.content)
    if 200 <= response.status_code < 300 and data.get("ok") is True:
        return response.status_code, response.content

    if data.get("ok") is not False:
        raise TelegramProtocolError("telegram_invalid_schema")

    raw_code = data.get("error_code")
    error_code = raw_code if isinstance(raw_code, int) and not isinstance(raw_code, bool) else response.status_code
    if not 400 <= error_code <= 599:
        raise TelegramProtocolError("telegram_invalid_schema")
    status = error_code if 400 <= error_code <= 599 else 502
    raw_description = data.get("description")
    description_text = raw_description.lower() if isinstance(raw_description, str) else ""
    if status == 400 and (
        "can't parse entities" in description_text
        or "can't find end of the entity" in description_text
    ):
        description = "telegram_bad_markup"
    else:
        description = {
            400: "telegram_bad_request",
            401: "telegram_invalid_token",
            403: "telegram_forbidden",
            404: "telegram_invalid_token",
            409: "telegram_conflict",
            429: "telegram_rate_limited",
        }.get(status, "telegram_network_error")

    safe = {"ok": False, "description": description}
    parameters = data.get("parameters")
    retry_after = _retry_after(parameters.get("retry_after")) if isinstance(parameters, dict) else None
    if status == 429:
        safe["parameters"] = {"retry_after": retry_after or 60}
    return status, json.dumps(safe, separators=(",", ":")).encode("utf-8")
```

Detect Telegram entity-parse descriptions only inside this helper and never return or log the raw description. `classify_delivery_response()` may share `_decode_telegram_object()` but must translate `TelegramProtocolError` to the transient `telegram_invalid_json` result rather than exposing the exception.

- [ ] **Step 6: Run focused tests and lint**

```powershell
python -m pytest tests/test_telegram_pinned.py tests/test_pinned_http.py -q
python -m ruff check agent/telegram_pinned.py tests/test_telegram_pinned.py
git diff --check
```

Expected: all commands exit 0; no sentinel appears in captured logs or exception/result representations.

- [ ] **Step 7: Commit Task 2**

```powershell
git add -- agent/telegram_pinned.py tests/test_telegram_pinned.py
git commit -m "feat: add pinned Telegram API contract"
```

---

### Task 3: Migrate Scheduler Delivery and Add the Retry Outbox

**Files:**
- Modify: `agent/scheduler.py:15-24,560-649,652-701,1104-1131,1182-1206`
- Create: `agent/tests/test_scheduler_telegram.py`
- Modify: `agent/tests/test_gap_fixes.py:2617-2641`
- Modify: `tests/test_pinned_http_consumers.py:107-116`

**Interfaces:**
- Consumes: `TelegramBotAPI.send_message() -> TelegramDeliveryResult`, `TelegramDeliveryState`, and stable result codes from Task 2.
- Produces: `TelegramRetryItem`, `TelegramDeliverySummary`, `_deliver_telegram_admins()`, `_send_telegram_admins() -> bool`, `retry_pending_telegram() -> int`, a 60-second `telegram-retry` task, and `scheduler_status()["telegram"]`.

- [ ] **Step 1: Add RED round-based fan-out tests**

Create `agent/tests/test_scheduler_telegram.py`:

```python
from __future__ import annotations

import pytest
import scheduler
from telegram_pinned import TelegramDeliveryResult, TelegramDeliveryState


def result(state, code="test", retry_after=None):
    return TelegramDeliveryResult(state, code, retry_after)


class ScriptedAPI:
    def __init__(self, scripts, calls):
        self.scripts = scripts
        self.calls = calls

    def send_message(self, chat_id, text, *, parse_mode="Markdown"):
        recipient = str(chat_id)
        self.calls.append((recipient, text, parse_mode))
        return self.scripts[recipient].pop(0)


def reset_telegram_state(monkeypatch):
    monkeypatch.setattr(scheduler, "_TELEGRAM_RETRY_QUEUE", [])
    monkeypatch.setattr(scheduler, "_TELEGRAM_EXPIRED_TOTAL", 0)
    monkeypatch.setattr(scheduler, "_TELEGRAM_DROPPED_TOTAL", 0)
    monkeypatch.setattr(scheduler, "_TELEGRAM_LAST_DRAIN", {})


def test_partial_success_retries_only_failed_recipient_in_round_order(monkeypatch):
    reset_telegram_state(monkeypatch)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghi")
    monkeypatch.setenv("ADMIN_TELEGRAM_IDS", "101,202")
    calls = []
    scripts = {
        "101": [result(TelegramDeliveryState.SUCCESS)],
        "202": [
            result(TelegramDeliveryState.TRANSIENT),
            result(TelegramDeliveryState.SUCCESS),
        ],
    }
    monkeypatch.setattr(scheduler, "_telegram_api_factory", lambda _token: ScriptedAPI(scripts, calls))
    sleeps = []
    monkeypatch.setattr(scheduler, "_telegram_sleep", sleeps.append)

    assert scheduler._send_telegram_admins("hello") is True

    assert [call[0] for call in calls] == ["101", "202", "202"]
    assert sleeps == [0.5]
    assert scheduler._TELEGRAM_RETRY_QUEUE == []


def test_rate_limited_recipient_is_queued_without_inline_retry(monkeypatch):
    reset_telegram_state(monkeypatch)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghi")
    monkeypatch.setenv("ADMIN_TELEGRAM_IDS", "101")
    monkeypatch.setattr(scheduler, "_telegram_now", lambda: 1_000.0)
    monkeypatch.setattr(
        scheduler,
        "_telegram_api_factory",
        lambda _token: ScriptedAPI(
            {"101": [result(TelegramDeliveryState.DEFERRED, retry_after=17)]},
            [],
        ),
    )

    assert scheduler._send_telegram_admins("hello") is False
    assert len(scheduler._TELEGRAM_RETRY_QUEUE) == 1
    assert scheduler._TELEGRAM_RETRY_QUEUE[0].recipient == "101"
    assert scheduler._TELEGRAM_RETRY_QUEUE[0].not_before == 1_017.0
```

Add the remaining round and wrapper contracts explicitly:

```python
def test_terminal_recipient_is_not_retried_or_queued(monkeypatch):
    reset_telegram_state(monkeypatch)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghi")
    monkeypatch.setenv("ADMIN_TELEGRAM_IDS", "101")
    calls = []
    monkeypatch.setattr(
        scheduler,
        "_telegram_api_factory",
        lambda _token: ScriptedAPI(
            {"101": [result(TelegramDeliveryState.TERMINAL)]}, calls
        ),
    )
    assert scheduler._send_telegram_admins("hello") is False
    assert [call[0] for call in calls] == ["101"]
    assert scheduler._TELEGRAM_RETRY_QUEUE == []


def test_transient_recipient_queues_after_three_total_attempts(monkeypatch):
    reset_telegram_state(monkeypatch)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghi")
    monkeypatch.setenv("ADMIN_TELEGRAM_IDS", "101")
    monkeypatch.setattr(scheduler, "_telegram_now", lambda: 1_000.0)
    calls = []
    monkeypatch.setattr(
        scheduler,
        "_telegram_api_factory",
        lambda _token: ScriptedAPI(
            {"101": [
                result(TelegramDeliveryState.TRANSIENT),
                result(TelegramDeliveryState.TRANSIENT),
                result(TelegramDeliveryState.TRANSIENT),
            ]},
            calls,
        ),
    )
    sleeps = []
    monkeypatch.setattr(scheduler, "_telegram_sleep", sleeps.append)
    assert scheduler._send_telegram_admins("hello") is False
    assert [call[0] for call in calls] == ["101", "101", "101"]
    assert sleeps == [0.5, 1.0]
    assert scheduler._TELEGRAM_RETRY_QUEUE[0].recipient == "101"
    assert scheduler._TELEGRAM_RETRY_QUEUE[0].not_before == 1_060.0


def test_inline_retries_are_round_based_across_recipients(monkeypatch):
    reset_telegram_state(monkeypatch)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghi")
    monkeypatch.setenv("ADMIN_TELEGRAM_IDS", "101,202")
    calls = []
    scripts = {
        recipient: [
            result(TelegramDeliveryState.TRANSIENT),
            result(TelegramDeliveryState.SUCCESS),
        ]
        for recipient in ("101", "202")
    }
    monkeypatch.setattr(
        scheduler,
        "_telegram_api_factory",
        lambda _token: ScriptedAPI(scripts, calls),
    )
    monkeypatch.setattr(scheduler, "_telegram_sleep", lambda _seconds: None)
    assert scheduler._send_telegram_admins("hello") is True
    assert [call[0] for call in calls] == ["101", "202", "101", "202"]


def test_admin_ids_are_stripped_filtered_and_deduplicated(monkeypatch):
    reset_telegram_state(monkeypatch)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", " 123456:ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghi ")
    monkeypatch.setenv("ADMIN_TELEGRAM_IDS", "101, 101,invalid,+202")
    calls = []
    monkeypatch.setattr(
        scheduler,
        "_telegram_api_factory",
        lambda token: (
            pytest.fail("token was not normalized")
            if token != "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghi"
            else ScriptedAPI({
                "101": [result(TelegramDeliveryState.SUCCESS)],
                "+202": [result(TelegramDeliveryState.SUCCESS)],
            }, calls)
        ),
    )
    assert scheduler._send_telegram_admins("hello") is True
    assert [call[0] for call in calls] == ["101", "+202"]


def test_unconfigured_initial_send_is_noop_and_never_queues(monkeypatch):
    reset_telegram_state(monkeypatch)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.setenv("ADMIN_TELEGRAM_IDS", "101")
    monkeypatch.setattr(
        scheduler,
        "_telegram_api_factory",
        lambda _token: pytest.fail("API must not be created"),
    )
    assert scheduler._send_telegram_admins("hello") is False
    assert scheduler._TELEGRAM_RETRY_QUEUE == []


def test_invalid_configured_token_fails_closed_without_queue_or_exception(monkeypatch):
    reset_telegram_state(monkeypatch)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "bad/token")
    monkeypatch.setenv("ADMIN_TELEGRAM_IDS", "101")

    def factory(_token):
        raise scheduler.TelegramContractError("telegram_token_invalid")

    monkeypatch.setattr(scheduler, "_telegram_api_factory", factory)
    assert scheduler._send_telegram_admins("MESSAGE_SENTINEL") is False
    assert scheduler._TELEGRAM_RETRY_QUEUE == []


def test_digest_delegates_to_shared_delivery_engine(monkeypatch):
    captured = {}

    def deliver(text, **kwargs):
        captured.update(text=text, **kwargs)
        return scheduler.TelegramDeliverySummary(attempted=2, succeeded=2)

    monkeypatch.setattr(scheduler, "_deliver_telegram_admins", deliver)
    scheduler._digest_send("token", [101, 202], "digest")
    assert captured == {
        "text": "digest",
        "token": "token",
        "recipients": ("101", "202"),
    }
```

- [ ] **Step 2: Add RED queue-drain, capacity, authorization, and telemetry tests**

Add these contracts:

```python
def test_retry_drain_skips_future_item_and_sends_due_item(monkeypatch):
    reset_telegram_state(monkeypatch)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghi")
    monkeypatch.setenv("ADMIN_TELEGRAM_IDS", "101,202")
    monkeypatch.setattr(scheduler, "_telegram_now", lambda: 2_000.0)
    scheduler._TELEGRAM_RETRY_QUEUE.extend([
        scheduler.TelegramRetryItem("future", "Markdown", "101", 1_900.0, 2_100.0, 0, "f1"),
        scheduler.TelegramRetryItem("due", "Markdown", "202", 1_900.0, 1_999.0, 0, "f2"),
    ])
    calls = []
    monkeypatch.setattr(
        scheduler,
        "_telegram_api_factory",
        lambda _token: ScriptedAPI(
            {"202": [result(TelegramDeliveryState.SUCCESS)]},
            calls,
        ),
    )

    assert scheduler.retry_pending_telegram() == 1
    assert [item.recipient for item in scheduler._TELEGRAM_RETRY_QUEUE] == ["101"]
    assert [call[0] for call in calls] == ["202"]


def test_retry_discards_recipient_removed_from_current_admins(monkeypatch):
    reset_telegram_state(monkeypatch)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghi")
    monkeypatch.setenv("ADMIN_TELEGRAM_IDS", "202")
    monkeypatch.setattr(scheduler, "_telegram_now", lambda: 2_000.0)
    scheduler._TELEGRAM_RETRY_QUEUE.append(
        scheduler.TelegramRetryItem("old", "Markdown", "101", 1_900.0, 1_999.0, 0, "f1")
    )

    assert scheduler.retry_pending_telegram() == 0
    assert scheduler._TELEGRAM_RETRY_QUEUE == []


def test_scheduler_status_exposes_subject_free_telegram_state(monkeypatch):
    reset_telegram_state(monkeypatch)
    monkeypatch.setattr(scheduler, "_telegram_now", lambda: 2_000.0)
    scheduler._TELEGRAM_RETRY_QUEUE.append(
        scheduler.TelegramRetryItem("SECRET_TEXT", "Markdown", "-100123", 1_900.0, 2_100.0, 0, "f1")
    )

    status = scheduler.scheduler_status()["telegram"]
    rendered = repr(status)
    assert status["queue_depth"] == 1
    assert status["oldest_age_seconds"] == 100
    assert "SECRET_TEXT" not in rendered
    assert "-100123" not in rendered


def test_retry_drain_log_is_aggregate_only(monkeypatch, caplog):
    reset_telegram_state(monkeypatch)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghi")
    monkeypatch.setenv("ADMIN_TELEGRAM_IDS", "-100123")
    monkeypatch.setattr(scheduler, "_telegram_now", lambda: 2_000.0)
    scheduler._TELEGRAM_RETRY_QUEUE.append(
        scheduler.TelegramRetryItem(
            "MESSAGE_SENTINEL", "Markdown", "-100123", 1_900.0, 1_999.0, 0, "fp"
        )
    )
    monkeypatch.setattr(
        scheduler,
        "_telegram_api_factory",
        lambda _token: ScriptedAPI(
            {"-100123": [result(TelegramDeliveryState.SUCCESS)]}, []
        ),
    )
    with caplog.at_level("INFO", logger="scheduler"):
        scheduler.retry_pending_telegram()
    output = "\n".join(record.getMessage() for record in caplog.records)
    assert "TELEGRAM_RETRY_DRAIN" in output
    assert "MESSAGE_SENTINEL" not in output
    assert "-100123" not in output
```

Add these queue-boundary tests:

```python
def test_enqueue_prunes_expired_dedupes_and_evicts_oldest(monkeypatch):
    reset_telegram_state(monkeypatch)
    monkeypatch.setattr(scheduler, "_telegram_now", lambda: 100_000.0)
    scheduler._TELEGRAM_RETRY_QUEUE.append(
        scheduler.TelegramRetryItem("expired", "Markdown", "1", 1.0, 1.0, 0, "expired")
    )
    for index in range(50):
        scheduler._TELEGRAM_RETRY_QUEUE.append(
            scheduler.TelegramRetryItem(
                f"text-{index}", "Markdown", str(index), 99_000.0 + index,
                100_100.0, 0, f"fp-{index}",
            )
        )

    assert scheduler._enqueue_telegram_retry("new", "Markdown", "999", delay=60) is True
    assert len(scheduler._TELEGRAM_RETRY_QUEUE) == 50
    assert scheduler._TELEGRAM_EXPIRED_TOTAL == 1
    assert scheduler._TELEGRAM_DROPPED_TOTAL == 1
    assert any(item.recipient == "999" for item in scheduler._TELEGRAM_RETRY_QUEUE)
    assert scheduler._enqueue_telegram_retry("new", "Markdown", "999", delay=60) is False


def test_retry_drain_processes_at_most_ten_due_items(monkeypatch):
    reset_telegram_state(monkeypatch)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghi")
    monkeypatch.setenv("ADMIN_TELEGRAM_IDS", ",".join(str(i) for i in range(12)))
    monkeypatch.setattr(scheduler, "_telegram_now", lambda: 2_000.0)
    for index in range(12):
        scheduler._TELEGRAM_RETRY_QUEUE.append(
            scheduler.TelegramRetryItem("x", "Markdown", str(index), 1_900.0, 1_999.0, 0, f"fp-{index}")
        )
    calls = []
    scripts = {str(i): [result(TelegramDeliveryState.SUCCESS)] for i in range(12)}
    monkeypatch.setattr(scheduler, "_telegram_api_factory", lambda _token: ScriptedAPI(scripts, calls))

    assert scheduler.retry_pending_telegram() == 10
    assert len(calls) == 10
    assert len(scheduler._TELEGRAM_RETRY_QUEUE) == 2


def test_retry_transient_backoff_is_60_then_120_seconds(monkeypatch):
    reset_telegram_state(monkeypatch)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghi")
    monkeypatch.setenv("ADMIN_TELEGRAM_IDS", "101")
    now = {"value": 2_000.0}
    monkeypatch.setattr(scheduler, "_telegram_now", lambda: now["value"])
    scripts = {"101": [
        result(TelegramDeliveryState.TRANSIENT),
        result(TelegramDeliveryState.TRANSIENT),
    ]}
    monkeypatch.setattr(scheduler, "_telegram_api_factory", lambda _token: ScriptedAPI(scripts, []))
    scheduler._TELEGRAM_RETRY_QUEUE.append(
        scheduler.TelegramRetryItem("x", "Markdown", "101", 1_900.0, 1_999.0, 0, "fp")
    )

    scheduler.retry_pending_telegram()
    assert scheduler._TELEGRAM_RETRY_QUEUE[0].not_before == 2_060.0
    now["value"] = 2_060.0
    scheduler.retry_pending_telegram()
    assert scheduler._TELEGRAM_RETRY_QUEUE[0].not_before == 2_180.0


def test_retry_drain_lock_prevents_duplicate_processing(monkeypatch):
    reset_telegram_state(monkeypatch)
    assert scheduler._telegram_drain_lock.acquire(blocking=False) is True
    try:
        assert scheduler.retry_pending_telegram() == 0
    finally:
        scheduler._telegram_drain_lock.release()
```

Add the missing-token/non-recursive case:

```python
def test_retry_missing_token_defers_without_recursive_delivery(monkeypatch):
    reset_telegram_state(monkeypatch)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.setenv("ADMIN_TELEGRAM_IDS", "101")
    monkeypatch.setattr(scheduler, "_telegram_now", lambda: 2_000.0)
    monkeypatch.setattr(
        scheduler,
        "_deliver_telegram_admins",
        lambda *_args, **_kwargs: pytest.fail("retry drain must not call inline delivery"),
    )
    monkeypatch.setattr(
        scheduler,
        "_telegram_api_factory",
        lambda _token: pytest.fail("missing token must not create API client"),
    )
    scheduler._TELEGRAM_RETRY_QUEUE.append(
        scheduler.TelegramRetryItem("x", "Markdown", "101", 1_900.0, 1_999.0, 0, "fp")
    )

    assert scheduler.retry_pending_telegram() == 0
    assert scheduler._TELEGRAM_RETRY_QUEUE[0].not_before == 2_060.0
    assert len(scheduler._TELEGRAM_RETRY_QUEUE) == 1


def test_retry_uses_rotated_token_without_storing_the_old_token(monkeypatch):
    reset_telegram_state(monkeypatch)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "654321:ROTATED_TOKEN_ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    monkeypatch.setenv("ADMIN_TELEGRAM_IDS", "101")
    monkeypatch.setattr(scheduler, "_telegram_now", lambda: 2_000.0)
    scheduler._TELEGRAM_RETRY_QUEUE.append(
        scheduler.TelegramRetryItem("x", "Markdown", "101", 1_900.0, 1_999.0, 0, "fp")
    )
    seen_tokens = []

    def factory(token):
        seen_tokens.append(token)
        return ScriptedAPI({"101": [result(TelegramDeliveryState.SUCCESS)]}, [])

    monkeypatch.setattr(scheduler, "_telegram_api_factory", factory)
    assert scheduler.retry_pending_telegram() == 1
    assert seen_tokens == ["654321:ROTATED_TOKEN_ABCDEFGHIJKLMNOPQRSTUVWXYZ"]
    assert "ROTATED_TOKEN" not in repr(scheduler._TELEGRAM_RETRY_QUEUE)


def test_retry_rate_limit_is_clamped_and_does_not_increment_retry_count(monkeypatch):
    reset_telegram_state(monkeypatch)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghi")
    monkeypatch.setenv("ADMIN_TELEGRAM_IDS", "101")
    monkeypatch.setattr(scheduler, "_telegram_now", lambda: 2_000.0)
    scheduler._TELEGRAM_RETRY_QUEUE.append(
        scheduler.TelegramRetryItem("x", "Markdown", "101", 1_900.0, 1_999.0, 2, "fp")
    )
    monkeypatch.setattr(
        scheduler,
        "_telegram_api_factory",
        lambda _token: ScriptedAPI(
            {"101": [result(TelegramDeliveryState.DEFERRED, retry_after=7_200)]}, []
        ),
    )
    assert scheduler.retry_pending_telegram() == 0
    item = scheduler._TELEGRAM_RETRY_QUEUE[0]
    assert item.not_before == 5_600.0
    assert item.retry_count == 2


def test_retry_transient_path_never_recursively_enqueues(monkeypatch):
    reset_telegram_state(monkeypatch)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghi")
    monkeypatch.setenv("ADMIN_TELEGRAM_IDS", "101")
    monkeypatch.setattr(scheduler, "_telegram_now", lambda: 2_000.0)
    scheduler._TELEGRAM_RETRY_QUEUE.append(
        scheduler.TelegramRetryItem("x", "Markdown", "101", 1_900.0, 1_999.0, 0, "fp")
    )
    monkeypatch.setattr(
        scheduler,
        "_telegram_api_factory",
        lambda _token: ScriptedAPI(
            {"101": [result(TelegramDeliveryState.TRANSIENT)]}, []
        ),
    )
    monkeypatch.setattr(
        scheduler,
        "_enqueue_telegram_retry",
        lambda *_args, **_kwargs: pytest.fail("drain must update the existing item"),
    )
    scheduler.retry_pending_telegram()
    assert len(scheduler._TELEGRAM_RETRY_QUEUE) == 1


def test_retry_task_is_registered_every_sixty_seconds() -> None:
    task = next(item for item in scheduler.TASKS if item.name == "telegram-retry")
    assert task.func is scheduler.retry_pending_telegram
    assert task.interval == 60
    assert task.next_run_after > 0
```

- [ ] **Step 3: Run scheduler tests and verify RED**

```powershell
python -m pytest agent/tests/test_scheduler_telegram.py tests/test_pinned_http_consumers.py agent/tests/test_gap_fixes.py -q
```

Expected: new scheduler contracts are missing; the egress registry still reports both direct Telegram POST functions.

- [ ] **Step 4: Implement scheduler data contracts and helpers**

Add direct imports and subject-free records near the scheduler configuration:

```python
import hashlib
import re
import secrets
from dataclasses import dataclass, replace

from telegram_pinned import (
    TelegramBotAPI,
    TelegramContractError,
    TelegramDeliveryState,
)


@dataclass(frozen=True)
class TelegramRetryItem:
    text: str
    parse_mode: str
    recipient: str
    created_at: float
    not_before: float
    retry_count: int
    fingerprint: str


@dataclass(frozen=True)
class TelegramDeliverySummary:
    attempted: int = 0
    succeeded: int = 0
    terminal: int = 0
    deferred: int = 0
    queued: int = 0

    @property
    def all_succeeded(self) -> bool:
        return self.attempted > 0 and self.succeeded == self.attempted
```

Use concrete seams that tests can patch without replacing stdlib globals:

```python
def _telegram_now() -> float:
    return time.time()


def _telegram_sleep(seconds: float) -> None:
    time.sleep(seconds)


def _telegram_api_factory(token: str) -> TelegramBotAPI:
    return TelegramBotAPI(token)


def _telegram_config() -> tuple[str, tuple[str, ...]]:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    recipients = tuple(dict.fromkeys(
        value
        for raw in os.environ.get("ADMIN_TELEGRAM_IDS", "").split(",")
        if (value := raw.strip()) and re.fullmatch(r"[+-]?\d+", value)
    ))
    return token, recipients
```

Define queue state with explicit locks/counters:

```python
_TELEGRAM_RETRY_QUEUE: list[TelegramRetryItem] = []
_TELEGRAM_MAX_QUEUE = 50
_TELEGRAM_MAX_AGE_SECONDS = 24 * 3600
_TELEGRAM_DRAIN_LIMIT = 10
_telegram_queue_lock = threading.Lock()
_telegram_drain_lock = threading.Lock()
_TELEGRAM_EXPIRED_TOTAL = 0
_TELEGRAM_DROPPED_TOTAL = 0
_TELEGRAM_LAST_DRAIN: dict[str, int | float] = {}
_TELEGRAM_FINGERPRINT_KEY = secrets.token_bytes(32)
```

Fingerprint only for equality/deduplication; never log it:

```python
def _telegram_fingerprint(text: str, parse_mode: str, recipient: str) -> str:
    raw = "\0".join((recipient, parse_mode, text)).encode("utf-8")
    return hashlib.blake2b(
        raw,
        key=_TELEGRAM_FINGERPRINT_KEY,
        digest_size=32,
    ).hexdigest()
```

- [ ] **Step 5: Implement round-based delivery and bounded enqueue**

Implement `_deliver_telegram_admins()` with exact state transitions:

```python
def _deliver_telegram_admins(
    text: str,
    *,
    parse_mode: str = "Markdown",
    token: str | None = None,
    recipients: tuple[str, ...] | None = None,
    enqueue: bool = True,
    max_attempts: int = 3,
) -> TelegramDeliverySummary:
    configured_token, configured_recipients = _telegram_config()
    active_token = (token if token is not None else configured_token).strip()
    source_recipients = recipients if recipients is not None else configured_recipients
    pending = list(dict.fromkeys(
        value
        for raw in source_recipients
        if (value := str(raw).strip()) and re.fullmatch(r"[+-]?\d+", value)
    ))
    if not active_token or not pending:
        return TelegramDeliverySummary()

    attempted = len(pending)
    try:
        api = _telegram_api_factory(active_token)
    except TelegramContractError:
        return TelegramDeliverySummary(attempted=attempted, terminal=attempted)
    except Exception:
        return TelegramDeliverySummary(attempted=attempted, terminal=attempted)
    succeeded = terminal = deferred = queued = 0
    transient: list[str] = pending
    attempt_limit = min(max(int(max_attempts), 1), 3)
    for attempt in range(attempt_limit):
        next_transient = []
        for recipient in transient:
            result = api.send_message(recipient, text, parse_mode=parse_mode)
            if result.state is TelegramDeliveryState.SUCCESS:
                succeeded += 1
            elif result.state is TelegramDeliveryState.TERMINAL:
                terminal += 1
            elif result.state is TelegramDeliveryState.DEFERRED:
                deferred += 1
                if enqueue and _enqueue_telegram_retry(
                    text, parse_mode, recipient, delay=result.retry_after or 60
                ):
                    queued += 1
            else:
                next_transient.append(recipient)
        transient = next_transient
        if not transient:
            break
        if attempt < attempt_limit - 1:
            _telegram_sleep((0.5, 1.0)[attempt])

    if enqueue:
        for recipient in transient:
            if _enqueue_telegram_retry(text, parse_mode, recipient, delay=60):
                queued += 1
    return TelegramDeliverySummary(attempted, succeeded, terminal, deferred, queued)
```

Implement `_enqueue_telegram_retry()` under `_telegram_queue_lock`: prune expired entries, increment the expired counter, suppress an existing fingerprint, evict the oldest item if capacity remains full, increment dropped, and append one new item with `retry_count=0`.

Use this exact shape:

```python
def _prune_telegram_queue(now: float, max_age_seconds: int = _TELEGRAM_MAX_AGE_SECONDS) -> None:
    global _TELEGRAM_EXPIRED_TOTAL
    retained = [
        item for item in _TELEGRAM_RETRY_QUEUE
        if now - item.created_at <= max_age_seconds
    ]
    _TELEGRAM_EXPIRED_TOTAL += len(_TELEGRAM_RETRY_QUEUE) - len(retained)
    _TELEGRAM_RETRY_QUEUE[:] = retained


def _enqueue_telegram_retry(
    text: str,
    parse_mode: str,
    recipient: str,
    *,
    delay: int,
) -> bool:
    global _TELEGRAM_DROPPED_TOTAL
    now = _telegram_now()
    fingerprint = _telegram_fingerprint(text, parse_mode, recipient)
    with _telegram_queue_lock:
        _prune_telegram_queue(now)
        if any(item.fingerprint == fingerprint for item in _TELEGRAM_RETRY_QUEUE):
            return False
        if len(_TELEGRAM_RETRY_QUEUE) >= _TELEGRAM_MAX_QUEUE:
            oldest_index = min(
                range(len(_TELEGRAM_RETRY_QUEUE)),
                key=lambda index: _TELEGRAM_RETRY_QUEUE[index].created_at,
            )
            _TELEGRAM_RETRY_QUEUE.pop(oldest_index)
            _TELEGRAM_DROPPED_TOTAL += 1
        _TELEGRAM_RETRY_QUEUE.append(TelegramRetryItem(
            text=text,
            parse_mode=parse_mode,
            recipient=recipient,
            created_at=now,
            not_before=now + min(max(int(delay), 1), 3600),
            retry_count=0,
            fingerprint=fingerprint,
        ))
    return True
```

Keep wrappers small and compatible:

```python
def _send_telegram_admins(text: str) -> bool:
    return _deliver_telegram_admins(text).all_succeeded


def _digest_send(token: str, admin_ids: list, text: str):
    summary = _deliver_telegram_admins(
        text,
        token=token,
        recipients=tuple(str(item) for item in admin_ids),
    )
    _sched_logger.info(
        "TELEGRAM_DIGEST_RESULT attempted=%d succeeded=%d terminal=%d deferred=%d queued=%d",
        summary.attempted,
        summary.succeeded,
        summary.terminal,
        summary.deferred,
        summary.queued,
    )
```

Remove both local `httpx` imports and every chat-ID/raw-exception log.

- [ ] **Step 6: Implement one-attempt drain, task registration, and status**

Implement `retry_pending_telegram()` with a non-blocking drain lock. Snapshot at most ten due items under the queue lock, process outside the lock, then replace/remove the exact fingerprint under lock. Use current config on every item:

```python
def retry_pending_telegram(max_age_hours: int = 24) -> int:
    global _TELEGRAM_LAST_DRAIN
    if not _telegram_drain_lock.acquire(blocking=False):
        return 0
    now = _telegram_now()
    succeeded = terminal = deferred = transient = discarded = 0
    try:
        max_age_seconds = min(max(int(max_age_hours), 1) * 3600, _TELEGRAM_MAX_AGE_SECONDS)
        with _telegram_queue_lock:
            _prune_telegram_queue(now, max_age_seconds)
            due = sorted(
                (item for item in _TELEGRAM_RETRY_QUEUE if item.not_before <= now),
                key=lambda item: (item.not_before, item.created_at, item.fingerprint),
            )[:_TELEGRAM_DRAIN_LIMIT]

        token, current_recipients = _telegram_config()
        current_admins = set(current_recipients)
        api = None
        terminal_config = False
        if token:
            try:
                api = _telegram_api_factory(token)
            except TelegramContractError:
                terminal_config = True
            except Exception:
                terminal_config = True
        for item in due:
            if item.recipient not in current_admins:
                outcome = "discard"
                result = None
            elif terminal_config:
                outcome = "terminal"
                result = None
            elif api is None:
                outcome = "missing_token"
                result = None
            else:
                result = api.send_message(
                    item.recipient,
                    item.text,
                    parse_mode=item.parse_mode,
                )
                outcome = result.state.value

            with _telegram_queue_lock:
                index = next(
                    (i for i, queued in enumerate(_TELEGRAM_RETRY_QUEUE)
                     if queued.fingerprint == item.fingerprint),
                    None,
                )
                if index is None:
                    continue
                current = _TELEGRAM_RETRY_QUEUE[index]
                if outcome == "success":
                    _TELEGRAM_RETRY_QUEUE.pop(index)
                    succeeded += 1
                elif outcome == "terminal" or outcome == "discard":
                    _TELEGRAM_RETRY_QUEUE.pop(index)
                    terminal += outcome == "terminal"
                    discarded += outcome == "discard"
                elif outcome == "deferred":
                    _TELEGRAM_RETRY_QUEUE[index] = replace(
                        current,
                        not_before=now + min(max(result.retry_after or 60, 1), 3600),
                    )
                    deferred += 1
                elif outcome == "missing_token":
                    _TELEGRAM_RETRY_QUEUE[index] = replace(current, not_before=now + 60)
                    deferred += 1
                else:
                    retry_count = current.retry_count + 1
                    delay = min(60 * 2 ** max(retry_count - 1, 0), 3600)
                    _TELEGRAM_RETRY_QUEUE[index] = replace(
                        current,
                        retry_count=retry_count,
                        not_before=now + delay,
                    )
                    transient += 1

        with _telegram_queue_lock:
            _TELEGRAM_LAST_DRAIN = {
                "at": now,
                "succeeded": succeeded,
                "terminal": terminal,
                "deferred": deferred,
                "transient": transient,
                "discarded": discarded,
            }
            queue_depth = len(_TELEGRAM_RETRY_QUEUE)
        _sched_logger.info(
            "TELEGRAM_RETRY_DRAIN succeeded=%d terminal=%d deferred=%d "
            "transient=%d discarded=%d queue_depth=%d",
            succeeded,
            terminal,
            deferred,
            transient,
            discarded,
            queue_depth,
        )
        return succeeded
    finally:
        _telegram_drain_lock.release()
```

This one-attempt drain never calls `_deliver_telegram_admins()` and therefore cannot recursively enqueue.

Register:

```python
ScheduledTask(
    "telegram-retry",
    retry_pending_telegram,
    interval_seconds=60,
    run_immediately=False,
),
```

Add subject-free status:

```python
def _telegram_retry_status() -> dict:
    now = _telegram_now()
    with _telegram_queue_lock:
        _prune_telegram_queue(now)
        oldest = min((item.created_at for item in _TELEGRAM_RETRY_QUEUE), default=None)
        return {
            "queue_depth": len(_TELEGRAM_RETRY_QUEUE),
            "oldest_age_seconds": int(max(0, now - oldest)) if oldest is not None else 0,
            "expired_total": _TELEGRAM_EXPIRED_TOTAL,
            "dropped_total": _TELEGRAM_DROPPED_TOTAL,
            "last_drain": dict(_TELEGRAM_LAST_DRAIN),
        }
```

Expose it as `scheduler_status()["telegram"]`. Update autonomous-agent logging so success is logged only when `_send_telegram_admins()` returns true; otherwise log the stable aggregate code `TELEGRAM_ADMIN_DELIVERY_INCOMPLETE` without exception data.

Use the exact branch:

```python
if _send_telegram_admins(
    f"🤖 *Agent quản trị* (LLM dùng {st['used_today']}/{st['cap_per_day']} hôm nay)\n"
    f"{suggestion}"
):
    _sched_logger.info("TELEGRAM_ADMIN_DELIVERY_COMPLETE")
else:
    _sched_logger.warning("TELEGRAM_ADMIN_DELIVERY_INCOMPLETE")
```

- [ ] **Step 7: Replace hygiene guards and empty the unpinned registry**

In `agent/tests/test_gap_fixes.py`, replace the two legacy Telegram tests with:

```python
def test_telegram_queue_mutation_has_lock(self):
    src = (AGENT_DIR / "scheduler.py").read_text(encoding="utf-8")
    start = src.index("def _enqueue_telegram_retry")
    end = src.index("\ndef ", start + 4)
    chunk = src[start:end]
    assert "with _telegram_queue_lock" in chunk
    assert "_TELEGRAM_RETRY_QUEUE.append" in chunk


def test_telegram_transport_logs_never_include_subjects_or_tracebacks(self):
    src = (AGENT_DIR / "scheduler.py").read_text(encoding="utf-8")
    start = src.index("def _digest_send")
    end = src.index("def task_autonomous_agent", start)
    chunk = src[start:end]
    for banned in ("exc_info=True", "chat %s", "telegram attempt %d", "repr("):
        assert banned not in chunk
```

In `tests/test_pinned_http_consumers.py`, set:

```python
KNOWN_UNPINNED_FETCHERS: set[tuple[str, str]] = set()
```

Replace the adjacent comment with:

```python
# General-purpose outbound HTTP calls in agent/ must be absent. SDK-managed
# transports are verified separately by their integration contract tests.
```

- [ ] **Step 8: Run scheduler and scanner tests**

```powershell
python -m pytest agent/tests/test_scheduler_telegram.py agent/tests/test_scheduler.py agent/tests/test_autonomous_budget.py agent/tests/test_gap_fixes.py tests/test_pinned_http_consumers.py tests/test_telegram_pinned.py -q
python -m ruff check agent/scheduler.py agent/tests/test_scheduler_telegram.py agent/tests/test_gap_fixes.py tests/test_pinned_http_consumers.py
git diff --check
```

Expected: all commands exit 0; scanner found set and `KNOWN_UNPINNED_FETCHERS` are both empty.

- [ ] **Step 9: Commit Task 3**

```powershell
git add -- agent/scheduler.py agent/tests/test_scheduler_telegram.py agent/tests/test_gap_fixes.py tests/test_pinned_http_consumers.py
git commit -m "fix: harden Telegram scheduler delivery"
```

---

### Task 4: Add the PTB `BaseRequest` Adapter and Bounded Lifecycle

**Files:**
- Create: `agent/telegram_ptb.py`
- Create: `tests/test_telegram_ptb.py`
- Modify: `requirements.txt:14`

**Interfaces:**
- Consumes: `TelegramPinnedTransport`, `TelegramEgressProfile`, `COMMAND_PROFILE`, `POLLING_PROFILE`, and `sanitize_ptb_response()` from Task 2.
- Produces: `validate_ptb_runtime_contract()`, `build_pinned_telegram_requests()`, and `PinnedTelegramRequest(BaseRequest)` with `read_timeout`, grouped partial-init cleanup, `initialize()`, `shutdown()`, safe `parse_json_payload()`, and `do_request()`; no default-executor or HTTPX fallback.

- [ ] **Step 1: Pin the SDK range and add RED protocol tests**

Change `requirements.txt` to:

```text
python-telegram-bot>=22.7,<23
```

Create `tests/test_telegram_ptb.py` with a fake synchronous transport:

```python
from __future__ import annotations

import asyncio
import inspect
import json
import threading
from types import SimpleNamespace

import pytest
from telegram import Bot
from telegram.error import (
    BadRequest,
    Conflict,
    Forbidden,
    InvalidToken,
    NetworkError,
    RetryAfter,
    TelegramError,
    TimedOut,
)
from telegram.request import HTTPXRequest, RequestData
from telegram.request._requestparameter import RequestParameter

import pinned_http as ph
import telegram_pinned as tp
import telegram_ptb as tr
from telegram_ptb import PinnedTelegramRequest, build_pinned_telegram_requests


TOKEN = "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghi"


class FakeTelegramTransport:
    def __init__(self, responses=None, error=None) -> None:
        self.responses = list(responses or [])
        self.error = error
        self.calls = []

    def request_url(self, url, parameters, **kwargs):
        self.calls.append((url, dict(parameters), kwargs, threading.current_thread().name))
        if self.error:
            raise self.error
        return self.responses.pop(0)


class MethodScriptedTransport:
    def __init__(self, responses) -> None:
        self.responses = dict(responses)
        self.calls = []

    def request_url(self, url, parameters, **kwargs):
        method = url.rsplit("/", 1)[-1]
        self.calls.append((method, dict(parameters), kwargs))
        return self.responses[method]


class BlockingTransport:
    def __init__(self, gate: threading.Event) -> None:
        self.gate = gate
        self._lock = threading.Lock()
        self.started = 0
        self.finished = 0
        self.active = 0
        self.max_active = 0

    def request_url(self, url, parameters, **kwargs):
        with self._lock:
            self.started += 1
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        self.gate.wait(timeout=2.0)
        with self._lock:
            self.active -= 1
            self.finished += 1
        return response(200, {"ok": True, "result": True})

    async def wait_for_started(self, expected: int) -> None:
        for _ in range(200):
            with self._lock:
                if self.started >= expected:
                    return
            await asyncio.sleep(0.01)
        raise AssertionError(f"only {self.started} workers started")

    async def wait_for_finished(self, expected: int) -> None:
        for _ in range(200):
            with self._lock:
                if self.finished >= expected:
                    return
            await asyncio.sleep(0.01)
        raise AssertionError(f"only {self.finished} workers finished")


def response(status: int, payload: dict | bytes) -> ph.PinnedResponse:
    body = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
    return ph.PinnedResponse(status, "https://api.telegram.org", (), body, ())


def request_data(**values) -> RequestData:
    return RequestData([RequestParameter.from_input(key, value) for key, value in values.items()])


def test_runtime_contract_accepts_installed_ptb_and_rejects_missing_capability(monkeypatch) -> None:
    tr.validate_ptb_runtime_contract()
    monkeypatch.setattr(tr, "RequestData", object)
    with pytest.raises(RuntimeError, match="telegram_ptb_incompatible"):
        tr.validate_ptb_runtime_contract()


def test_adapter_never_uses_default_executor_or_httpx_fallback() -> None:
    source = inspect.getsource(tr)
    assert "asyncio.to_thread" not in source
    assert "HTTPXRequest" not in source
    assert "run_in_executor(self._executor" in source


def test_profile_read_timeouts_match_ptb_long_poll_contract() -> None:
    command = PinnedTelegramRequest(TOKEN, tp.COMMAND_PROFILE, transport=FakeTelegramTransport())
    polling = PinnedTelegramRequest(TOKEN, tp.POLLING_PROFILE, transport=FakeTelegramTransport())
    assert command.read_timeout == 15.0
    assert polling.read_timeout == 5.0


def test_command_request_returns_ptb_result_and_uses_dedicated_thread() -> None:
    async def exercise():
        fake = FakeTelegramTransport([response(200, {"ok": True, "result": True})])
        request = PinnedTelegramRequest(TOKEN, tp.COMMAND_PROFILE, transport=fake)
        await request.initialize()
        try:
            result = await request.post(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                request_data(chat_id=42, text="hello"),
            )
        finally:
            await request.shutdown()
        return result, fake.calls

    result, calls = asyncio.run(exercise())
    assert result is True
    assert calls[0][1] == {"chat_id": 42, "text": "hello"}
    assert calls[0][3].startswith("telegram-command-")


def test_request_rejects_get_before_worker_submission() -> None:
    async def exercise():
        fake = FakeTelegramTransport()
        request = PinnedTelegramRequest(TOKEN, tp.COMMAND_PROFILE, transport=fake)
        await request.initialize()
        try:
            with pytest.raises(NetworkError, match="telegram_method_denied"):
                await request.do_request("https://api.telegram.org/file", "GET")
        finally:
            await request.shutdown()
        return fake.calls

    assert asyncio.run(exercise()) == []


def test_request_rejects_files_before_worker_submission() -> None:
    async def exercise():
        fake = FakeTelegramTransport()
        request = PinnedTelegramRequest(TOKEN, tp.COMMAND_PROFILE, transport=fake)
        await request.initialize()
        try:
            file_data = SimpleNamespace(contains_files=True, parameters={})
            with pytest.raises(NetworkError, match="telegram_files_denied"):
                await request.do_request(
                    f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                    "POST",
                    file_data,
                )
        finally:
            await request.shutdown()
        return fake.calls

    assert asyncio.run(exercise()) == []


def test_parse_json_payload_is_strict_and_never_logs_raw_bytes(caplog) -> None:
    with caplog.at_level("DEBUG"):
        with pytest.raises(TelegramError, match="telegram_invalid_json"):
            PinnedTelegramRequest.parse_json_payload(b"RAW_PAYLOAD_SENTINEL")
    assert "RAW_PAYLOAD_SENTINEL" not in "\n".join(
        record.getMessage() for record in caplog.records
    )
```

Add safe response/error mapping tests:

```python
@pytest.mark.parametrize(
    ("status", "payload", "error_type", "message"),
    [
        (400, {"ok": False, "error_code": 400, "description": "Bad Request: can't parse entities"}, BadRequest, "telegram_bad_markup"),
        (401, {"ok": False, "error_code": 401, "description": "SECRET"}, InvalidToken, "telegram_invalid_token"),
        (403, {"ok": False, "error_code": 403, "description": "SECRET"}, Forbidden, "telegram_forbidden"),
        (409, {"ok": False, "error_code": 409, "description": "SECRET"}, Conflict, "telegram_conflict"),
        (429, {"ok": False, "error_code": 429, "description": "SECRET", "parameters": {"retry_after": 7}}, RetryAfter, None),
    ],
)
def test_ptb_errors_are_typed_and_sanitized(status, payload, error_type, message) -> None:
    async def exercise():
        fake = FakeTelegramTransport([response(status, payload)])
        request = PinnedTelegramRequest(TOKEN, tp.COMMAND_PROFILE, transport=fake)
        await request.initialize()
        try:
            with pytest.raises(error_type) as exc_info:
                await request.post(
                    f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                    request_data(chat_id=42, text="hello"),
                )
        finally:
            await request.shutdown()
        return exc_info.value

    error = asyncio.run(exercise())
    assert "SECRET" not in str(error)
    if message is not None:
        assert message in str(error)
    if error_type is RetryAfter:
        assert error.retry_after == 7


def test_invalid_json_never_reaches_ptb_raw_payload_logger(caplog) -> None:
    async def exercise():
        fake = FakeTelegramTransport([response(200, b"RAW_PAYLOAD_SENTINEL")])
        request = PinnedTelegramRequest(TOKEN, tp.COMMAND_PROFILE, transport=fake)
        await request.initialize()
        try:
            with pytest.raises(NetworkError, match="telegram_protocol_error"):
                await request.post(
                    f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                    request_data(chat_id=42, text="hello"),
                )
        finally:
            await request.shutdown()

    with caplog.at_level("DEBUG"):
        asyncio.run(exercise())
    assert "RAW_PAYLOAD_SENTINEL" not in "\n".join(record.getMessage() for record in caplog.records)
```

Add typed transport/protocol mapping:

```python
@pytest.mark.parametrize(
    ("error", "error_type", "message"),
    [
        (ph.PinnedDeadlineExceeded("SECRET"), TimedOut, "telegram_timeout"),
        (ph.PinnedTransportError("SECRET"), NetworkError, "telegram_transport_error"),
        (ph.ResolutionError("SECRET"), NetworkError, "telegram_resolution_error"),
        (ph.BlockedAddressError("SECRET"), NetworkError, "telegram_egress_denied"),
        (ph.PinnedBodyLimitError("SECRET"), NetworkError, "telegram_protocol_error"),
        (tp.TelegramProtocolError("SECRET"), NetworkError, "telegram_protocol_error"),
    ],
)
def test_typed_transport_failures_map_to_stable_ptb_errors(error, error_type, message) -> None:
    async def exercise():
        request = PinnedTelegramRequest(
            TOKEN,
            tp.COMMAND_PROFILE,
            transport=FakeTelegramTransport(error=error),
        )
        await request.initialize()
        try:
            with pytest.raises(error_type, match=message) as exc_info:
                await request.do_request(
                    f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                    "POST",
                    request_data(chat_id=42, text="hello"),
                )
        finally:
            await request.shutdown()
        return exc_info.value

    assert "SECRET" not in str(asyncio.run(exercise()))


def test_unexpected_worker_exception_is_sanitized() -> None:
    error = RuntimeError("SECRET_TOKEN_SENTINEL")

    async def exercise():
        request = PinnedTelegramRequest(
            TOKEN,
            tp.COMMAND_PROFILE,
            transport=FakeTelegramTransport(error=error),
        )
        await request.initialize()
        try:
            with pytest.raises(NetworkError, match="telegram_transport_error") as exc_info:
                await request.do_request(
                    f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                    "POST",
                    request_data(chat_id=42, text="hello"),
                )
        finally:
            await request.shutdown()
        return exc_info.value

    assert "SECRET_TOKEN_SENTINEL" not in str(asyncio.run(exercise()))
```

- [ ] **Step 2: Add RED real-PTB request-data integration tests**

Use `telegram.Bot` with command and polling `PinnedTelegramRequest` instances backed by method-scripted fake transports. Exercise:

```python
async def exercise_real_bot_contracts():
    command_transport = MethodScriptedTransport({
        "getMe": response(200, {"ok": True, "result": {"id": 1, "is_bot": True, "first_name": "bot", "username": "vl360bot"}}),
        "deleteWebhook": response(200, {"ok": True, "result": True}),
        "sendMessage": response(200, {"ok": True, "result": {"message_id": 9, "date": 0, "chat": {"id": 42, "type": "private"}, "text": "hello"}}),
        "answerCallbackQuery": response(200, {"ok": True, "result": True}),
    })
    polling_transport = MethodScriptedTransport({
        "getUpdates": response(200, {"ok": True, "result": []}),
    })
    command_request = PinnedTelegramRequest(TOKEN, tp.COMMAND_PROFILE, transport=command_transport)
    polling_request = PinnedTelegramRequest(TOKEN, tp.POLLING_PROFILE, transport=polling_transport)
    bot = Bot(TOKEN, request=command_request, get_updates_request=polling_request)
    await bot.initialize()
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await bot.get_updates(timeout=20, allowed_updates=("message", "callback_query"))
        await bot.send_message(42, "hello", parse_mode="Markdown")
        await bot.answer_callback_query("callback-id")
    finally:
        await bot.shutdown()
    return command_transport.calls, polling_transport.calls, bot._request
```

Add the concrete assertion:

```python
def test_real_ptb_request_data_stays_inside_closed_contract() -> None:
    command_calls, polling_calls, requests = asyncio.run(exercise_real_bot_contracts())
    command_by_method = {method: parameters for method, parameters, _kwargs in command_calls}
    assert command_by_method == {
        "getMe": {},
        "deleteWebhook": {"drop_pending_updates": True},
        "sendMessage": {"chat_id": 42, "text": "hello", "parse_mode": "Markdown"},
        "answerCallbackQuery": {"callback_query_id": "callback-id"},
    }
    assert [method for method, _parameters, _kwargs in polling_calls] == ["getUpdates"]
    assert polling_calls[0][1] == {
        "timeout": 20,
        "allowed_updates": ["message", "callback_query"],
    }
    assert all(isinstance(request, PinnedTelegramRequest) for request in requests)
    assert all(not isinstance(request, HTTPXRequest) for request in requests)
```

- [ ] **Step 3: Add RED admission, cancellation, and lifecycle tests**

Add these concurrency contracts:

```python
def test_command_capacity_never_exceeds_three_workers() -> None:
    async def exercise():
        gate = threading.Event()
        transport = BlockingTransport(gate)
        request = PinnedTelegramRequest(TOKEN, tp.COMMAND_PROFILE, transport=transport)
        await request.initialize()
        tasks = [
            asyncio.create_task(request.do_request(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                "POST",
                request_data(chat_id=index, text="x"),
            ))
            for index in range(4)
        ]
        await transport.wait_for_started(3)
        assert transport.max_active == 3
        with pytest.raises(TimedOut, match="telegram_executor_saturated"):
            await tasks[3]
        gate.set()
        await asyncio.gather(*tasks[:3])
        await request.shutdown()

    asyncio.run(exercise())


def test_cancelled_coroutine_keeps_slot_until_worker_finishes() -> None:
    async def exercise():
        gate = threading.Event()
        transport = BlockingTransport(gate)
        request = PinnedTelegramRequest(TOKEN, tp.POLLING_PROFILE, transport=transport)
        await request.initialize()
        first = asyncio.create_task(request.do_request(
            f"https://api.telegram.org/bot{TOKEN}/getUpdates",
            "POST",
            request_data(timeout=20, allowed_updates=["message", "callback_query"]),
        ))
        await transport.wait_for_started(1)
        first.cancel()
        with pytest.raises(asyncio.CancelledError):
            await first
        with pytest.raises(TimedOut, match="telegram_executor_saturated"):
            await request.do_request(
                f"https://api.telegram.org/bot{TOKEN}/getUpdates",
                "POST",
                request_data(timeout=20, allowed_updates=["message", "callback_query"]),
                pool_timeout=0.01,
            )
        gate.set()
        await transport.wait_for_finished(1)
        await request.shutdown()

    asyncio.run(exercise())
```

Add lifecycle and timeout tests:

```python
def test_initialize_and_shutdown_are_idempotent_and_closed_request_fails() -> None:
    async def exercise():
        request = PinnedTelegramRequest(TOKEN, tp.COMMAND_PROFILE, transport=FakeTelegramTransport())
        await request.initialize()
        await request.initialize()
        await request.shutdown()
        await request.shutdown()
        with pytest.raises(NetworkError, match="telegram_request_not_initialized"):
            await request.do_request(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                "POST",
                request_data(chat_id=1, text="x"),
            )

    asyncio.run(exercise())


def test_explicit_timeouts_tighten_but_none_never_relaxes_profile() -> None:
    async def exercise():
        fake = FakeTelegramTransport([
            response(200, {"ok": True, "result": True}),
            response(200, {"ok": True, "result": True}),
        ])
        request = PinnedTelegramRequest(TOKEN, tp.COMMAND_PROFILE, transport=fake)
        await request.initialize()
        try:
            await request.do_request(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                "POST",
                request_data(chat_id=1, text="x"),
                read_timeout=2.0,
            )
            await request.do_request(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                "POST",
                request_data(chat_id=1, text="x"),
                read_timeout=None,
            )
        finally:
            await request.shutdown()
        return fake.calls

    calls = asyncio.run(exercise())
    assert calls[0][2]["inactivity_timeout_seconds"] == 2.0
    assert calls[1][2]["inactivity_timeout_seconds"] == 15.0


def test_executor_admission_time_is_subtracted_from_worker_deadline() -> None:
    async def exercise():
        fake = FakeTelegramTransport([response(200, {"ok": True, "result": True})])
        request = PinnedTelegramRequest(TOKEN, tp.COMMAND_PROFILE, transport=fake)
        await request.initialize()
        semaphore = request._semaphore
        assert semaphore is not None
        for _ in range(tp.COMMAND_PROFILE.workers):
            await semaphore.acquire()
        task = asyncio.create_task(request.do_request(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            "POST",
            request_data(chat_id=1, text="x"),
        ))
        await asyncio.sleep(0.05)
        semaphore.release()
        await task
        for _ in range(tp.COMMAND_PROFILE.workers - 1):
            semaphore.release()
        await request.shutdown()
        return fake.calls[0][2]["total_timeout_seconds"]

    remaining = asyncio.run(exercise())
    assert 0 < remaining < tp.COMMAND_PROFILE.policy.total_timeout_seconds


def test_async_context_cleans_up_when_initialize_fails(monkeypatch) -> None:
    class BrokenExecutor:
        def __init__(self, **_kwargs):
            raise RuntimeError("executor failed")

    monkeypatch.setattr("telegram_ptb.ThreadPoolExecutor", BrokenExecutor)

    async def exercise():
        request = PinnedTelegramRequest(TOKEN, tp.COMMAND_PROFILE, transport=FakeTelegramTransport())
        with pytest.raises(RuntimeError, match="executor failed"):
            async with request:
                pass
        assert request._state == "closed"

    asyncio.run(exercise())


def test_request_pair_cleans_both_members_after_partial_initialize(monkeypatch) -> None:
    created = []

    class FailSecondExecutor:
        def __init__(self, **_kwargs):
            created.append(self)
            if len(created) == 2:
                raise RuntimeError("executor failed")
            self.closed = False

        def shutdown(self, *, wait, cancel_futures):
            self.closed = True

    monkeypatch.setattr("telegram_ptb.ThreadPoolExecutor", FailSecondExecutor)

    async def exercise():
        command, polling = build_pinned_telegram_requests(TOKEN)
        with pytest.raises(RuntimeError, match="executor failed"):
            await asyncio.gather(command.initialize(), polling.initialize())
        assert command._state == "closed"
        assert polling._state == "closed"
        assert created[0].closed is True

    asyncio.run(exercise())
```

The three-worker command capacity and one-worker polling capacity are locked by the two blocking tests above. Add the active-worker shutdown test:

```python
def test_shutdown_waits_for_active_bounded_worker() -> None:
    async def exercise():
        gate = threading.Event()
        transport = BlockingTransport(gate)
        request = PinnedTelegramRequest(TOKEN, tp.POLLING_PROFILE, transport=transport)
        await request.initialize()
        worker = asyncio.create_task(request.do_request(
            f"https://api.telegram.org/bot{TOKEN}/getUpdates",
            "POST",
            request_data(timeout=20, allowed_updates=["message", "callback_query"]),
        ))
        await transport.wait_for_started(1)
        shutdown = asyncio.create_task(request.shutdown())
        await asyncio.sleep(0)
        assert shutdown.done() is False
        gate.set()
        await worker
        await shutdown
        assert request._state == "closed"

    asyncio.run(exercise())


def test_shutdown_timeout_records_only_stable_lifecycle_failure(monkeypatch, caplog) -> None:
    async def exercise():
        gate = threading.Event()
        transport = BlockingTransport(gate)
        request = PinnedTelegramRequest(TOKEN, tp.POLLING_PROFILE, transport=transport)
        await request.initialize()
        worker = asyncio.create_task(request.do_request(
            f"https://api.telegram.org/bot{TOKEN}/getUpdates",
            "POST",
            request_data(timeout=20, allowed_updates=["message", "callback_query"]),
        ))
        await transport.wait_for_started(1)

        async def force_timeout(awaitable, *, timeout):
            awaitable.cancel()
            raise asyncio.TimeoutError

        monkeypatch.setattr(tr.asyncio, "wait_for", force_timeout)
        with caplog.at_level("ERROR", logger="telegram_ptb"):
            await request.shutdown()
        gate.set()
        await worker
        return "\n".join(record.getMessage() for record in caplog.records)

    output = asyncio.run(exercise())
    assert output == "TELEGRAM_REQUEST_SHUTDOWN_TIMEOUT profile=polling"
    assert TOKEN not in output
```

- [ ] **Step 4: Run PTB tests and verify RED**

```powershell
python -m pytest tests/test_telegram_ptb.py tests/test_telegram_pinned.py -q
```

Expected: collection fails because `telegram_ptb.PinnedTelegramRequest` does not exist.

- [ ] **Step 5: Implement safe PTB parsing and exception mapping**

Create `agent/telegram_ptb.py` with the complete imports and runtime gate:

```python
from __future__ import annotations

import asyncio
import functools
import json
import logging
import math
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from telegram import __version_info__
from telegram.error import NetworkError, TelegramError, TimedOut
from telegram.request import BaseRequest, RequestData

from pinned_http import (
    BlockedAddressError,
    InvalidDestinationError,
    PeerMismatchError,
    PinnedBodyLimitError,
    PinnedContentEncodingError,
    PinnedDeadlineExceeded,
    PinnedRequestBodyError,
    PinnedTransportError,
    RedirectPolicyError,
    ResolutionError,
)
from telegram_pinned import (
    COMMAND_PROFILE,
    POLLING_PROFILE,
    TelegramContractError,
    TelegramEgressProfile,
    TelegramPinnedTransport,
    TelegramProtocolError,
    sanitize_ptb_response,
)


_LOGGER = logging.getLogger("telegram_ptb")


def validate_ptb_runtime_contract() -> None:
    try:
        version = tuple(__version_info__[:3])
        probe = RequestData([])
        valid = (
            (22, 7, 0) <= version < (23, 0, 0)
            and all(callable(getattr(BaseRequest, name, None)) for name in (
                "initialize", "shutdown", "do_request", "parse_json_payload"
            ))
            and isinstance(getattr(BaseRequest, "read_timeout", None), property)
            and probe.parameters == {}
            and probe.contains_files is False
        )
    except Exception:
        valid = False
    if not valid:
        raise RuntimeError("telegram_ptb_incompatible") from None
```

Then add these stable helpers:

```python
def _safe_json(payload: bytes) -> dict:
    try:
        value = json.loads(payload.decode("utf-8", "strict"))
    except (UnicodeDecodeError, ValueError):
        raise TelegramError("telegram_invalid_json") from None
    if not isinstance(value, dict):
        raise TelegramError("telegram_invalid_json") from None
    return value


def _finite_timeout(value, default: float) -> float:
    if value is BaseRequest.DEFAULT_NONE or value is None:
        return default
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(parsed):
        return default
    return min(default, max(0.001, parsed))
```

`PinnedTelegramRequest.parse_json_payload()` is concrete and never delegates invalid bytes to PTB's logger:

```python
@staticmethod
def parse_json_payload(payload: bytes) -> dict[str, Any]:
    return _safe_json(payload)
```

Map typed pinned failures exactly:

```python
except PinnedDeadlineExceeded:
    raise TimedOut("telegram_timeout") from None
except PinnedTransportError:
    raise NetworkError("telegram_transport_error") from None
except ResolutionError:
    raise NetworkError("telegram_resolution_error") from None
except (TelegramContractError, PinnedRequestBodyError):
    raise NetworkError("telegram_contract_denied") from None
except TelegramProtocolError:
    raise NetworkError("telegram_protocol_error") from None
except (InvalidDestinationError, BlockedAddressError, PeerMismatchError, RedirectPolicyError):
    raise NetworkError("telegram_egress_denied") from None
except (PinnedBodyLimitError, PinnedContentEncodingError):
    raise NetworkError("telegram_protocol_error") from None
```

- [ ] **Step 6: Implement the dedicated executor, semaphore, shield, and lifecycle**

Use one small shared lifecycle group so PTB's concurrent two-request initialization cannot leak the request that initialized first:

```python
class _PinnedTelegramLifecycleGroup:
    def __init__(self) -> None:
        self.lock = asyncio.Lock()
        self.members: list[PinnedTelegramRequest] = []

    def register(self, request: "PinnedTelegramRequest") -> None:
        self.members.append(request)

    async def initialize(self, request: "PinnedTelegramRequest") -> None:
        async with self.lock:
            try:
                request._initialize_locked()
            except Exception:
                for member in self.members:
                    await member._shutdown_locked()
                raise

    async def shutdown(self, request: "PinnedTelegramRequest") -> None:
        async with self.lock:
            await request._shutdown_locked()


class PinnedTelegramRequest(BaseRequest):
    def __init__(
        self,
        token: str,
        profile: TelegramEgressProfile,
        *,
        transport: TelegramPinnedTransport | None = None,
        lifecycle_group: _PinnedTelegramLifecycleGroup | None = None,
    ) -> None:
        validate_ptb_runtime_contract()
        if profile is not COMMAND_PROFILE and profile is not POLLING_PROFILE:
            raise RuntimeError("telegram_profile_denied")
        self._profile = profile
        self._transport = transport or TelegramPinnedTransport(
            token,
            profile,
            audit_context=(
                "telegram_sdk_polling" if profile is POLLING_PROFILE
                else "telegram_sdk_command"
            ),
        )
        self._executor = None
        self._semaphore = None
        self._active = set()
        self._state = "new"
        self._lifecycle_group = lifecycle_group or _PinnedTelegramLifecycleGroup()
        self._lifecycle_group.register(self)

    @property
    def read_timeout(self) -> float:
        return self._profile.default_read_timeout

    async def initialize(self) -> None:
        await self._lifecycle_group.initialize(self)

    def _initialize_locked(self) -> None:
        if self._state == "active":
            return
        if self._state in {"closing", "closed"}:
            raise RuntimeError("telegram_request_closed")
        prefix = f"telegram-{self._profile.name}-"
        self._executor = ThreadPoolExecutor(
            max_workers=self._profile.workers,
            thread_name_prefix=prefix,
        )
        self._semaphore = asyncio.Semaphore(self._profile.workers)
        self._state = "active"


def build_pinned_telegram_requests(
    token: str,
) -> tuple[PinnedTelegramRequest, PinnedTelegramRequest]:
    group = _PinnedTelegramLifecycleGroup()
    return (
        PinnedTelegramRequest(token, COMMAND_PROFILE, lifecycle_group=group),
        PinnedTelegramRequest(token, POLLING_PROFILE, lifecycle_group=group),
    )
```

In `do_request()`:

1. Reject non-POST and files before admission.
2. Start `expires_at = loop.time() + profile.policy.total_timeout_seconds` before waiting.
3. Await semaphore with `min(1.0, explicit_pool_timeout, remaining_total)`; timeout raises `TimedOut("telegram_executor_saturated") from None`.
4. Compute the strictest finite inactivity timeout from read/write/connect arguments without allowing any argument, including `None`, to exceed the profile.
5. Submit `TelegramPinnedTransport.request_url()` to the dedicated executor with only the remaining total deadline.
6. Add the underlying executor future to `_active`; attach a done callback that removes it and releases the semaphore.
7. Await `asyncio.shield(worker_future)`. Cancellation propagates to the caller but does not cancel the underlying future or release capacity early.
8. Validate/sanitize the response through `sanitize_ptb_response()` and return `(status_code, payload)`.

Use this concrete implementation shape:

```python
async def do_request(
    self,
    url: str,
    method: str,
    request_data: RequestData | None = None,
    read_timeout=BaseRequest.DEFAULT_NONE,
    write_timeout=BaseRequest.DEFAULT_NONE,
    connect_timeout=BaseRequest.DEFAULT_NONE,
    pool_timeout=BaseRequest.DEFAULT_NONE,
) -> tuple[int, bytes]:
    if method != "POST":
        raise NetworkError("telegram_method_denied") from None
    try:
        if request_data is not None and request_data.contains_files:
            raise NetworkError("telegram_files_denied") from None
    except NetworkError:
        raise
    except Exception:
        raise NetworkError("telegram_contract_denied") from None
    if self._state != "active" or self._executor is None or self._semaphore is None:
        raise NetworkError("telegram_request_not_initialized") from None

    loop = asyncio.get_running_loop()
    expires_at = loop.time() + self._profile.policy.total_timeout_seconds
    try:
        parameters = dict(request_data.parameters) if request_data is not None else {}
    except Exception:
        raise NetworkError("telegram_contract_denied") from None
    semaphore = self._semaphore
    remaining_before_admission = expires_at - loop.time()
    if remaining_before_admission <= 0:
        raise TimedOut("telegram_timeout") from None
    admission_timeout = min(
        1.0,
        _finite_timeout(pool_timeout, 1.0),
        remaining_before_admission,
    )
    try:
        await asyncio.wait_for(semaphore.acquire(), timeout=admission_timeout)
    except asyncio.TimeoutError:
        raise TimedOut("telegram_executor_saturated") from None

    if self._state != "active" or self._executor is None:
        semaphore.release()
        raise NetworkError("telegram_request_not_initialized") from None
    remaining = expires_at - loop.time()
    if remaining <= 0:
        semaphore.release()
        raise TimedOut("telegram_timeout") from None
    inactivity = min(
        self._profile.policy.inactivity_timeout_seconds,
        _finite_timeout(read_timeout, self._profile.policy.inactivity_timeout_seconds),
        _finite_timeout(write_timeout, self._profile.policy.inactivity_timeout_seconds),
        _finite_timeout(connect_timeout, self._profile.policy.inactivity_timeout_seconds),
    )
    call = functools.partial(
        self._transport.request_url,
        url,
        parameters,
        total_timeout_seconds=remaining,
        inactivity_timeout_seconds=inactivity,
    )
    try:
        worker = loop.run_in_executor(self._executor, call)
    except Exception:
        semaphore.release()
        raise NetworkError("telegram_transport_error") from None
    self._active.add(worker)

    def completed(_future) -> None:
        self._active.discard(worker)
        semaphore.release()

    worker.add_done_callback(completed)
    try:
        response = await asyncio.shield(worker)
        return sanitize_ptb_response(response)
    except asyncio.CancelledError:
        raise
    except PinnedDeadlineExceeded:
        raise TimedOut("telegram_timeout") from None
    except ResolutionError:
        raise NetworkError("telegram_resolution_error") from None
    except PinnedTransportError:
        raise NetworkError("telegram_transport_error") from None
    except (TelegramContractError, PinnedRequestBodyError):
        raise NetworkError("telegram_contract_denied") from None
    except TelegramProtocolError:
        raise NetworkError("telegram_protocol_error") from None
    except (InvalidDestinationError, BlockedAddressError, PeerMismatchError, RedirectPolicyError):
        raise NetworkError("telegram_egress_denied") from None
    except (PinnedBodyLimitError, PinnedContentEncodingError):
        raise NetworkError("telegram_protocol_error") from None
    except Exception:
        raise NetworkError("telegram_transport_error") from None
```

Implement shutdown:

```python
async def shutdown(self) -> None:
    await self._lifecycle_group.shutdown(self)


async def _shutdown_locked(self) -> None:
    if self._state == "closed":
        return
    if self._state == "new":
        self._state = "closed"
        return
    self._state = "closing"
    executor = self._executor
    active = tuple(self._active)
    timed_out = False
    if active:
        try:
            await asyncio.wait_for(
                asyncio.gather(*(asyncio.shield(item) for item in active), return_exceptions=True),
                timeout=self._profile.policy.total_timeout_seconds + 1.0,
            )
        except asyncio.TimeoutError:
            timed_out = True
            _LOGGER.error("TELEGRAM_REQUEST_SHUTDOWN_TIMEOUT profile=%s", self._profile.name)
    if executor is not None:
        executor.shutdown(wait=not timed_out, cancel_futures=True)
    self._executor = None
    self._semaphore = None
    self._active.clear()
    self._state = "closed"
```

Do not call `asyncio.to_thread()` anywhere in this module.

- [ ] **Step 7: Run PTB, contract, and dependency tests**

```powershell
python -m pytest tests/test_telegram_ptb.py tests/test_telegram_pinned.py tests/test_pinned_http.py -q
python -m ruff check agent/telegram_ptb.py agent/telegram_pinned.py tests/test_telegram_ptb.py tests/test_telegram_pinned.py
python -m pip check
git diff --check
```

Expected: all commands exit 0; actual installed PTB in `>=22.7,<23` produces only payloads accepted by the contract.

- [ ] **Step 8: Commit Task 4**

```powershell
git add -- requirements.txt agent/telegram_ptb.py tests/test_telegram_ptb.py
git commit -m "feat: add pinned Telegram SDK request"
```

---

### Task 5: Wire Bot Gateway Polling and Restrict Markdown Fallback

**Files:**
- Modify: `agent/bot_gateway.py:61-82,421-465,643-660,697-712,1030-1037`
- Create: `agent/tests/test_bot_gateway_telegram.py`

**Interfaces:**
- Consumes: `COMMAND_PROFILE`, `POLLING_PROFILE`, and `PinnedTelegramRequest` from Task 4.
- Produces: `BotGateway.start_telegram()` with both pinned request slots, exact polling arguments, `_send_telegram_reply()` safe fallback behavior, and stable startup failure logging.

- [ ] **Step 1: Add RED builder-wiring and polling tests**

Create `agent/tests/test_bot_gateway_telegram.py` with a fake fluent builder/application:

```python
from __future__ import annotations

import asyncio
import inspect
from types import SimpleNamespace

import pytest
from telegram.error import BadRequest, NetworkError

import bot_gateway
from bot_gateway import BotGateway
from telegram_ptb import PinnedTelegramRequest


TOKEN = "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghi"


class FakeApplication:
    def __init__(self) -> None:
        self.handlers = []
        self.polling_kwargs = None

    def add_handler(self, handler) -> None:
        self.handlers.append(handler)

    def run_polling(self, **kwargs) -> None:
        self.polling_kwargs = kwargs


class FakeBuilder:
    def __init__(self) -> None:
        self.values = {}
        self.app = FakeApplication()

    def token(self, value):
        self.values["token"] = value
        return self

    def request(self, value):
        self.values["request"] = value
        return self

    def get_updates_request(self, value):
        self.values["get_updates_request"] = value
        return self

    def build(self):
        return self.app


def test_start_telegram_wires_distinct_pinned_requests(monkeypatch) -> None:
    builder = FakeBuilder()
    monkeypatch.setattr(bot_gateway.Application, "builder", lambda: builder)
    gateway = BotGateway()

    gateway.start_telegram(TOKEN)

    assert isinstance(builder.values["request"], PinnedTelegramRequest)
    assert isinstance(builder.values["get_updates_request"], PinnedTelegramRequest)
    assert builder.values["request"] is not builder.values["get_updates_request"]
    assert builder.app.polling_kwargs == {
        "timeout": 20,
        "bootstrap_retries": 0,
        "allowed_updates": ("message", "callback_query"),
        "drop_pending_updates": True,
        "stop_signals": None,
        "close_loop": False,
    }
```

Add the exact source assertion and missing-capability test:

```python
def test_start_telegram_source_has_no_default_builder_or_broad_updates() -> None:
    source = inspect.getsource(BotGateway.start_telegram)
    assert ".request(command_request)" in source
    assert ".get_updates_request(polling_request)" in source
    assert "Update.ALL_TYPES" not in source
    assert ".token(token).build()" not in source


def test_start_telegram_fails_closed_when_builder_hook_is_missing(monkeypatch) -> None:
    builder = FakeBuilder()
    builder.get_updates_request = None
    monkeypatch.setattr(bot_gateway.Application, "builder", lambda: builder)
    with pytest.raises(RuntimeError, match="telegram_pinned_request_unavailable"):
        BotGateway().start_telegram(TOKEN)
    assert "request" not in builder.values
    assert builder.app.polling_kwargs is None
```

- [ ] **Step 2: Add RED safe Markdown fallback tests**

Use a message fake with scripted exceptions:

```python
class ReplyMessage:
    def __init__(self, errors):
        self.errors = list(errors)
        self.calls = []

    async def reply_text(self, text, **kwargs):
        self.calls.append((text, kwargs))
        if self.errors:
            error = self.errors.pop(0)
            if error is not None:
                raise error


def test_bad_markup_retries_once_without_parse_mode() -> None:
    async def exercise():
        message = ReplyMessage([BadRequest("telegram_bad_markup"), None])
        await BotGateway()._send_telegram_reply(message, "*broken*", reply_markup=None)
        return message.calls

    calls = asyncio.run(exercise())
    assert len(calls) == 2
    assert calls[0][1]["parse_mode"] == "Markdown"
    assert "parse_mode" not in calls[1][1]


def test_network_error_is_not_converted_into_second_send() -> None:
    async def exercise():
        message = ReplyMessage([NetworkError("telegram_transport_error")])
        with pytest.raises(NetworkError, match="telegram_transport_error"):
            await BotGateway()._send_telegram_reply(message, "text", reply_markup=None)
        return message.calls

    assert len(asyncio.run(exercise())) == 1
```

Add exact helper-use and redaction coverage:

```python
def test_both_telegram_reply_paths_use_safe_helper() -> None:
    message_source = inspect.getsource(BotGateway._tg_message)
    callback_source = inspect.getsource(BotGateway._tg_callback)
    assert "_send_telegram_reply" in message_source
    assert "_send_telegram_reply" in callback_source
    assert "except Exception" not in message_source
    assert "except Exception" not in callback_source


def test_markup_fallback_log_contains_no_text_or_exception(caplog) -> None:
    async def exercise():
        message = ReplyMessage([BadRequest("telegram_bad_markup"), None])
        await BotGateway()._send_telegram_reply(
            message,
            "MESSAGE_SENTINEL",
            reply_markup=None,
        )

    with caplog.at_level("DEBUG", logger="bot_gateway"):
        asyncio.run(exercise())
    output = "\n".join(record.getMessage() for record in caplog.records)
    assert "TELEGRAM_MARKUP_FALLBACK" in output
    assert "MESSAGE_SENTINEL" not in output
    assert "telegram_bad_markup" not in output


def test_message_and_callback_logs_are_subject_free(monkeypatch, caplog) -> None:
    gateway = BotGateway()

    async def send_to_agent(_text, _user_key):
        return {"reply": "safe reply", "suggestions": []}

    gateway.send_to_agent = send_to_agent
    monkeypatch.setattr(bot_gateway, "_add_message", lambda *_args: None)
    message = ReplyMessage([])
    message.text = "MESSAGE_SENTINEL"
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=4242, first_name="USERNAME_SENTINEL"),
        message=message,
    )

    async def answer():
        return None

    callback_message = ReplyMessage([])
    query = SimpleNamespace(
        answer=answer,
        from_user=SimpleNamespace(id=4343, first_name="CALLBACK_USER_SENTINEL"),
        data="CALLBACK_DATA_SENTINEL",
        message=callback_message,
    )
    callback_update = SimpleNamespace(callback_query=query)

    async def exercise():
        await gateway._tg_message(update, None)
        await gateway._tg_callback(callback_update, None)

    with caplog.at_level("INFO", logger="bot_gateway"):
        asyncio.run(exercise())
    output = "\n".join(record.getMessage() for record in caplog.records)
    assert "TELEGRAM_MESSAGE_RECEIVED" in output
    assert "TELEGRAM_CALLBACK_RECEIVED" in output
    for secret in (
        "MESSAGE_SENTINEL", "USERNAME_SENTINEL", "4242",
        "CALLBACK_DATA_SENTINEL", "CALLBACK_USER_SENTINEL", "4343",
    ):
        assert secret not in output


def test_agent_error_log_omits_telegram_session_and_response_body(monkeypatch, caplog) -> None:
    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, *_args, **_kwargs):
            return SimpleNamespace(status_code=400, text="BODY_SENTINEL")

    monkeypatch.setattr(bot_gateway.httpx, "AsyncClient", lambda **_kwargs: FakeClient())
    with caplog.at_level("ERROR", logger="bot_gateway"):
        asyncio.run(BotGateway().send_to_agent(
            "MESSAGE_SENTINEL",
            "telegram:-1001234567890",
        ))
    output = "\n".join(record.getMessage() for record in caplog.records)
    assert output == "AGENT_RESPONSE_REJECTED status=400"
    for secret in ("BODY_SENTINEL", "MESSAGE_SENTINEL", "-1001234567890"):
        assert secret not in output


def test_unexpected_agent_exception_log_has_no_raw_exception(monkeypatch, caplog) -> None:
    class FailingClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, *_args, **_kwargs):
            raise RuntimeError("EXCEPTION_SENTINEL")

    monkeypatch.setattr(bot_gateway.httpx, "AsyncClient", lambda **_kwargs: FailingClient())
    with caplog.at_level("ERROR", logger="bot_gateway"):
        asyncio.run(BotGateway().send_to_agent("MESSAGE_SENTINEL", "telegram:-100123"))
    output = "\n".join(record.getMessage() for record in caplog.records)
    assert output == "AGENT_REQUEST_FAILED"
    assert "EXCEPTION_SENTINEL" not in output
    assert all(record.exc_info is None for record in caplog.records)
```

- [ ] **Step 3: Add RED startup-log redaction test**

Add this exact helper contract test:

```python
def test_background_gateway_logs_only_stable_failure_code(monkeypatch, caplog) -> None:
    gateway = BotGateway()

    def fail(_token):
        raise RuntimeError("SECRET_TOKEN_SENTINEL MESSAGE_SENTINEL")

    monkeypatch.setattr(gateway, "start_telegram", fail)
    with caplog.at_level("ERROR", logger="bot_gateway"):
        bot_gateway._run_telegram_gateway(gateway, TOKEN)

    output = "\n".join(record.getMessage() for record in caplog.records)
    assert output == "TELEGRAM_POLLING_STOPPED"
    assert "SECRET_TOKEN_SENTINEL" not in output
    assert "MESSAGE_SENTINEL" not in output
    assert all(record.exc_info is None for record in caplog.records)


def test_start_telegram_sanitizes_polling_exception(monkeypatch) -> None:
    class FailingApplication(FakeApplication):
        def run_polling(self, **kwargs) -> None:
            self.polling_kwargs = kwargs
            raise RuntimeError(f"{TOKEN} MESSAGE_SENTINEL")

    builder = FakeBuilder()
    builder.app = FailingApplication()
    monkeypatch.setattr(bot_gateway.Application, "builder", lambda: builder)
    with pytest.raises(RuntimeError, match="^telegram_polling_failed$") as exc_info:
        BotGateway().start_telegram(TOKEN)
    assert TOKEN not in str(exc_info.value)
    assert "MESSAGE_SENTINEL" not in str(exc_info.value)


def test_polling_failure_cleans_both_request_instances(monkeypatch) -> None:
    class PartialInitApplication(FakeApplication):
        def run_polling(self, **kwargs) -> None:
            self.polling_kwargs = kwargs
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            loop.run_until_complete(builder.values["request"].initialize())
            raise RuntimeError("startup failed")

    builder = FakeBuilder()
    builder.app = PartialInitApplication()
    monkeypatch.setattr(bot_gateway.Application, "builder", lambda: builder)
    with pytest.raises(RuntimeError, match="telegram_polling_failed"):
        BotGateway().start_telegram(TOKEN)
    assert builder.values["request"]._state == "closed"
    assert builder.values["get_updates_request"]._state == "closed"
```

- [ ] **Step 4: Run bot tests and verify RED**

```powershell
python -m pytest agent/tests/test_bot_gateway_telegram.py -q
```

Expected: failures show missing request hooks, broad `Update.ALL_TYPES`, catch-all Markdown fallback, and raw startup exception logging.

- [ ] **Step 5: Wire the pinned requests and narrow polling**

Within the existing optional Telegram import block, import `BadRequest` and the pinned factory/runtime gate. Treat failure of either the SDK or pinned adapter import as Telegram being unavailable; never import or construct `HTTPXRequest`:

```python
import asyncio

from telegram.error import BadRequest
from telegram_ptb import (
    PinnedTelegramRequest,
    build_pinned_telegram_requests,
    validate_ptb_runtime_contract,
)
```

In `start_telegram()`, replace the installation-specific exception with the stable fail-closed code, validate the builder hooks before chaining, and build exactly as follows:

```python
if not HAS_TELEGRAM:
    raise RuntimeError("telegram_pinned_request_unavailable")
try:
    validate_ptb_runtime_contract()
    command_request, polling_request = build_pinned_telegram_requests(token)
    builder = Application.builder()
    if not callable(getattr(builder, "request", None)) or not callable(
        getattr(builder, "get_updates_request", None)
    ):
        raise RuntimeError("telegram_ptb_incompatible")
    app = (
        builder
        .token(token)
        .request(command_request)
        .get_updates_request(polling_request)
        .build()
    )
except Exception:
    raise RuntimeError("telegram_pinned_request_unavailable") from None
```

Add a synchronous cleanup helper next to `start_telegram()`; `close_loop=False` leaves PTB's loop available long enough to close both request instances even when application initialization fails after only the requests initialized:

```python
def _shutdown_pinned_telegram_requests(*requests: PinnedTelegramRequest) -> None:
    loop = None
    try:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        if loop.is_running():
            _bot_logger.error("TELEGRAM_REQUEST_CLEANUP_UNAVAILABLE")
            return
        loop.run_until_complete(asyncio.gather(
            *(request.shutdown() for request in requests),
            return_exceptions=True,
        ))
    except Exception:
        _bot_logger.error("TELEGRAM_REQUEST_CLEANUP_FAILED")
    finally:
        if loop is not None and not loop.is_running() and not loop.is_closed():
            loop.close()
            asyncio.set_event_loop(None)
```

Import `PinnedTelegramRequest` for the annotation from `telegram_ptb`. Keep the existing handler registration, then wrap the blocking polling call so PTB cannot re-expose the token in an `InvalidToken` message:

```python
try:
    app.run_polling(
        timeout=20,
        bootstrap_retries=0,
        allowed_updates=("message", "callback_query"),
        drop_pending_updates=True,
        stop_signals=None,
        close_loop=False,
    )
except Exception:
    raise RuntimeError("telegram_polling_failed") from None
finally:
    _shutdown_pinned_telegram_requests(command_request, polling_request)
```

Do not call `run_polling()` a second time outside this wrapper. The lifecycle group closes both instances when one request initializer fails; the `finally` helper covers later `getMe`, updater, or application bootstrap failures.

- [ ] **Step 6: Centralize and restrict Telegram reply fallback**

Add:

```python
async def _send_telegram_reply(self, message, text: str, *, reply_markup=None) -> None:
    common = {
        "reply_markup": reply_markup,
        "disable_web_page_preview": True,
    }
    try:
        await message.reply_text(text, parse_mode="Markdown", **common)
    except BadRequest as exc:
        if str(exc) != "telegram_bad_markup":
            raise
        _bot_logger.debug("TELEGRAM_MARKUP_FALLBACK")
        await message.reply_text(text, **common)
```

Before changing the reply loops, sanitize the shared `send_to_agent()` failure logs because its `session_id` contains the Telegram chat ID and its response body may echo user content. Use only:

```python
_bot_logger.warning(
    "AGENT_RESPONSE_RETRY status=%d attempt=%d/%d",
    resp.status_code,
    attempt + 1,
    max_retries + 1,
)
_bot_logger.error("AGENT_RESPONSE_REJECTED status=%d", resp.status_code)
_bot_logger.error("AGENT_RESPONSE_INVALID_JSON")
_bot_logger.warning(
    "AGENT_REQUEST_TIMEOUT attempt=%d/%d",
    attempt + 1,
    max_retries + 1,
)
_bot_logger.error("AGENT_CONNECT_FAILED")
_bot_logger.error("AGENT_REQUEST_FAILED")
```

Apply each code to its existing branch and remove `session_id`, `resp.text`, exception formatting, and `exc_info=True` from those branches. Preserve retry counts, user-facing fallback replies, and retry delays.

Replace both duplicated reply try/except blocks in `_tg_message()` and `_tg_callback()` with this helper. Leave the existing 4,000-character chunking and final-chunk keyboard behavior unchanged.

Replace the two subject-bearing receipt logs and both reply loops with these exact forms:

```python
# In _tg_message():
_bot_logger.info("TELEGRAM_MESSAGE_RECEIVED")
# ...
for i, chunk in enumerate(chunks):
    await self._send_telegram_reply(
        update.message,
        chunk,
        reply_markup=keyboard if i == len(chunks) - 1 else None,
    )

# In _tg_callback():
_bot_logger.info("TELEGRAM_CALLBACK_RECEIVED")
# ...
for i, chunk in enumerate(chunks):
    await self._send_telegram_reply(
        query.message,
        chunk,
        reply_markup=keyboard if i == len(chunks) - 1 else None,
    )
```

Delete the existing `first_name`, message-prefix, callback-data, and caught-exception log arguments; do not replace them with hashed identifiers.

Replace the background-thread error log with a helper that catches exceptions and emits only:

```python
def _run_telegram_gateway(gateway: BotGateway, token: str) -> None:
    try:
        gateway.start_telegram(token=token)
    except Exception:
        _bot_logger.error("TELEGRAM_POLLING_STOPPED")
```

Use `threading.Thread(target=_run_telegram_gateway, args=(gw, TELEGRAM_TOKEN), daemon=True)` in `main()`. Do not include `%s`, `repr`, `traceback`, or `exc_info=True`.

- [ ] **Step 7: Run bot, PTB, scheduler, and resilience regressions**

```powershell
python -m pytest agent/tests/test_bot_gateway_telegram.py tests/test_telegram_ptb.py tests/test_telegram_pinned.py agent/tests/test_scheduler_telegram.py agent/tests/test_resilience.py -q
python -m ruff check agent/bot_gateway.py agent/tests/test_bot_gateway_telegram.py
git diff --check
```

Expected: all commands exit 0; PTB traffic is pinned and bot reply behavior preserves only the intended bad-markup retry.

- [ ] **Step 8: Commit Task 5**

```powershell
git add -- agent/bot_gateway.py agent/tests/test_bot_gateway_telegram.py
git commit -m "fix: pin Telegram bot polling traffic"
```

---

### Task 6: Close the Egress Registry, Documentation, and Full Baseline

**Files:**
- Verify only: `tests/test_pinned_http_consumers.py`, `agent/tests/test_gap_fixes.py`, `tests/test_telegram_pinned.py`, `tests/test_telegram_ptb.py`, `agent/tests/test_scheduler_telegram.py`, `agent/tests/test_bot_gateway_telegram.py`
- Modify: `docs/ROADMAP.md:422-439`
- Modify: `docs/HANDOFF.md:134-142`
- Modify: `docs/superpowers/plans/2026-08-04-pinned-telegram-egress.md`: append the actual result record after verification

**Interfaces:**
- Consumes: all Task 1-5 production and test contracts.
- Produces: an empty known-unpinned registry, green focused/full gates, and revision-bound local documentation without claiming deployment or live Telegram observation.

- [ ] **Step 1: Run the complete focused Telegram/pinned gate**

```powershell
python -m pytest tests/test_pinned_http.py tests/test_telegram_pinned.py tests/test_telegram_ptb.py agent/tests/test_scheduler_telegram.py agent/tests/test_bot_gateway_telegram.py tests/test_pinned_http_consumers.py agent/tests/test_gap_fixes.py -q
```

Expected: exit 0. If a failure appears, use `superpowers:systematic-debugging`, add or tighten the smallest regression test that reproduces the root cause, fix it, rerun this exact command, and commit the correction before continuing.

- [ ] **Step 2: Run mapped-consumer and resilience regressions**

```powershell
python -m pytest tests/test_admin_pinned_http.py tests/test_auto_learn_fetch.py tests/test_crawler_ssrf.py tests/test_geocode_pinned.py tests/test_gpt55_quality_burst.py tests/test_realtime_pinned.py agent/tests/test_resilience.py -q
```

Expected: exit 0; GET consumers and resilience logging remain unchanged.

- [ ] **Step 3: Run static and repository hard gates**

```powershell
python -m ruff check .
python scripts/checks/run_hard.py --all
git diff --check
```

Expected: Ruff exit 0, hard checks report `hard=0` with no ratchet increase, and diff check exit 0.

- [ ] **Step 4: Run the full non-slow baseline**

```powershell
python -m pytest tests/ agent/tests/ -m "not slow" --tb=short
```

Expected: exit 0. Do not normalize an infrastructure/timing/xdist failure into a pass: isolate it with the exact failing selector, rerun to determine reproducibility, fix a real regression, and document a genuine non-reproducible harness limitation precisely.

- [ ] **Step 5: Verify secret-safe source and dependency closure**

```powershell
rg -n "httpx\.post|chat %s|telegram attempt %d" agent/scheduler.py
rg -n "HTTPXRequest|Update\.ALL_TYPES|Telegram polling error|Markdown parse failed" agent/bot_gateway.py agent/telegram_pinned.py agent/telegram_ptb.py
python -m pip check
git status --short
```

Expected: both `rg` commands return no matches; there is no direct scheduler Telegram POST, `HTTPXRequest`, broad update constant, or legacy secret-bearing Telegram log format. `pip check` exits 0; only intended documentation/result edits remain.

- [ ] **Step 6: Update revision-bound documentation**

In `docs/ROADMAP.md`, replace the residual line that lists the two scheduler functions with a completed local Telegram egress entry. State:

- core `post_json()` is JSON-only, bounded, redirect-denying, and uses the existing pinned transport;
- scheduler and PTB command/polling paths are pinned;
- command/polling limits and worker counts;
- retry outbox limits and at-least-once duplicate residual;
- the exact implementation revision and exact observed focused/full/Ruff/hard results from Steps 1-4; and
- production remains unobserved because no deployment/live Telegram action was authorized.

In `docs/HANDOFF.md`, replace the out-of-scope Telegram line with the same concise operational truth and retain the no-push/no-deploy/no-secret-change statement.

Append a `## Result Record` section to this plan containing the implementation commit sequence, exact commands/results, accepted residuals, and operational non-actions. Do not retroactively mark task checkboxes if the repository convention is to preserve plans as execution instructions.

- [ ] **Step 7: Commit documentation and final result record**

```powershell
git add -- docs/ROADMAP.md docs/HANDOFF.md docs/superpowers/plans/2026-08-04-pinned-telegram-egress.md
git commit -m "docs: close pinned Telegram egress verification"
```

- [ ] **Step 8: Verify the final committed revision**

```powershell
git status --short --branch
git log -8 --oneline --decorate
python -m pytest tests/test_pinned_http.py tests/test_telegram_pinned.py tests/test_telegram_ptb.py agent/tests/test_scheduler_telegram.py agent/tests/test_bot_gateway_telegram.py tests/test_pinned_http_consumers.py -q
python -m ruff check .
python scripts/checks/run_hard.py --all
git diff --check HEAD^ HEAD
```

Expected: clean worktree, focused suite exit 0, Ruff exit 0, hard checks `hard=0`, and committed diff check exit 0.

---

## Execution Review Gates

After every task, the controller must run two reviews before dispatching the next fresh subagent:

1. **Specification compliance:** verify every produced interface and invariant against `docs/superpowers/specs/2026-08-04-pinned-telegram-egress-design.md`; reject missing tests, widened methods/fields, fallback transports, or secret-bearing diagnostics.
2. **Code quality:** inspect concurrency ownership, cancellation, lock boundaries, typed error mapping, test determinism, duplication, naming, and unnecessary scope. Require corrections in the same task before proceeding.

Task 6 final review must additionally inspect the full diff from `eaa043e2` to the implementation head and confirm no unrelated files, production mutations, or live-network behavior entered the tranche.
