> STATUS: design approved in conversation on 2026-08-04; written for final user review before implementation planning.

# Pinned Telegram Egress Design

## 1. Context

The shared pinned outbound HTTP client now protects the mapped GET consumers with single-resolution-per-hop DNS pinning, public-address enforcement, peer verification, bounded response/decompression handling, and one monotonic deadline. The remaining production egress debt is Telegram:

- `agent/scheduler.py::_digest_send()` sends directly with `httpx.post()`.
- `agent/scheduler.py::_send_telegram_admins()` sends directly with `httpx.post()`.
- `agent/bot_gateway.py::start_telegram()` lets `python-telegram-bot` create its default unpinned `HTTPXRequest` instances for command traffic and long polling.

The current scheduler behavior also has correctness and privacy defects:

- Any response below HTTP 500 is treated as success, including 400, 401, 403, and 429.
- A failure for one recipient stops the remaining fan-out.
- The retry queue stores only `(text, timestamp)`, so a retry can resend to recipients that already succeeded.
- `retry_pending_telegram()` is not registered as a scheduled task, so queued items are never drained automatically.
- Retry failures log raw chat IDs and `exc_info=True`.
- A Markdown fallback catches every exception, so an ambiguous network failure can trigger an unintended second send.

The goal is to close all Telegram egress paths without weakening the existing GET contract, without allowing a fallback to unpinned HTTP, and without introducing a new durable store for best-effort admin alerts.

## 2. Goals

1. Preserve `PinnedHTTPClient.get()` and all existing GET-consumer behavior.
2. Add one narrow, bounded, synchronous JSON POST operation to the pinned core.
3. Route scheduler Telegram POSTs and all `python-telegram-bot` command/polling traffic through that operation.
4. Enforce the exact Telegram origin, token path, method set, payload fields, request size, response size, decompression bounds, and end-to-end deadline.
5. Keep async polling responsive by bridging the synchronous pinned operation through dedicated bounded executors.
6. Correct Telegram success/error classification and retry only the recipients that failed.
7. Ensure logs, exceptions, and telemetry never expose the bot token, URL path, payload, message text, chat ID, or raw Telegram response.
8. Verify the real transport path deterministically without contacting Telegram in CI.

## 3. Non-goals

- Telegram webhook mode.
- File upload, multipart requests, media download, or `getFile`.
- Arbitrary Telegram Bot API methods or generic external JSON POST support for other consumers.
- A persistent database/file outbox or an external message broker.
- Exactly-once Telegram delivery. Telegram `sendMessage` has no idempotency key, so an accepted request whose response is lost can be delivered more than once.
- Deployment, production token validation, or a live Telegram test message. Those require separate operational authorization.

## 4. Alternatives considered

### 4.1 Recommended: bounded in-memory per-recipient outbox

Keep retry state in process memory, bounded to 50 delivery items and 24 hours. This closes the current retry defect without adding a new persistent collection containing chat IDs and message text. It remains best-effort across process restarts, matching the current admin-alert role.

### 4.2 Durable PostgreSQL or SQLite outbox

This survives a restart but adds schema/migration work, locking and multi-process semantics, privacy/lifecycle obligations, and a dependency on storage during the same outages for which alerts may be needed. It is not justified for the current small admin fan-out.

### 4.3 External broker

A broker gives strong backpressure and delivery control but adds deployment and operations infrastructure far beyond the current need. It is explicitly deferred.

## 5. Architecture

The design has five bounded units.

### 5.1 `PinnedHTTPClient.post_json()`

`agent/pinned_http.py` remains the sole DNS/address/peer/transport authority. `get()` remains unchanged. A separate `post_json()` method performs exactly one JSON POST and never follows redirects.

Its focused contract is:

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
) -> PinnedResponse: ...
```

The method:

- Requires a mapping payload.
- Serializes once as compact UTF-8 JSON with `ensure_ascii=False`, `allow_nan=False`, and no custom encoder.
- Rejects a non-serializable value or a body over `max_request_bytes` before DNS or socket work.
- Sends only `User-Agent`, `Accept: application/json`, `Content-Type: application/json`, `Content-Length`, and the existing policy-derived `Accept-Encoding` header.
- Accepts no caller-defined headers, cookies, authorization header, proxy, or redirect behavior.
- Starts its `DeadlineBudget` at method entry, before serialization, URL parsing, DNS, connect, write, response read, and decompression.
- Reuses the existing per-hop resolve, public-address policy, pinned network backend, peer verification, TLS hostname verification, response streaming, encoded/decoded body bounds, and safe-origin security logging.
- Rejects every 3xx response as `RedirectPolicyError`; a JSON POST is never replayed to a redirect target.
- Returns the same immutable `PinnedResponse` type as `get()`.

The internal fetch helper may be generalized to accept the fixed method/body selected by the public entry point, but `get()` must retain its current request headers, redirect semantics, cookies, return values, and exception behavior.

### 5.2 Telegram endpoint and payload contract

Add `agent/telegram_pinned.py` as the Telegram-specific authority above the pinned core. It validates every SDK- or scheduler-generated call before invoking `post_json()`.

The only allowed origin is `https://api.telegram.org:443`. A request URL is accepted only when all of these are true:

- Scheme is `https`, raw host is exactly `api.telegram.org`, and effective port is 443.
- There are no credentials, query, or fragment.
- The raw path is exactly `/bot<configured-token>/<allowed-method>` with no percent-encoded or alternate representation.
- The configured token is non-empty ASCII, contains no URL delimiter, and matches the token embedded in the path exactly.
- Error text and object representations never include the token or full URL.

There are two independent profiles:

| Profile | Allowed methods | Request | Encoded/decoded response | Inactivity | Total deadline |
| --- | --- | ---: | ---: | ---: | ---: |
| Command | `getMe`, `deleteWebhook`, `sendMessage`, `answerCallbackQuery` | 64 KiB | 512 KiB | 15 s | 15 s |
| Polling | `getUpdates` only | 64 KiB | 2 MiB | 25 s | 30 s |

Both profiles accept only `identity` and `gzip`, disallow redirects, and use the exact Telegram origin allowlist.

Method payloads are also closed:

- `getMe`: no fields.
- `deleteWebhook`: `drop_pending_updates` only.
- `getUpdates`: `offset`, `limit`, `timeout`, and `allowed_updates` only.
- `sendMessage`: `chat_id`, `text`, `parse_mode`, `reply_markup`, `link_preview_options`, `message_thread_id`, `direct_messages_topic_id`, `business_connection_id`, and `reply_parameters` only.
- `answerCallbackQuery`: `callback_query_id` only.

Unknown fields fail closed. `api_kwargs` cannot widen the contract. Additional method or field support requires an explicit design change and tests.

Value validation is method-aware:

- `getUpdates.timeout` is an integer from 0 through 20 seconds.
- `getUpdates.allowed_updates` contains exactly `message` and `callback_query`, with no duplicates.
- `sendMessage.chat_id` is an integer or signed decimal string.
- `sendMessage.text` is a string of at most 4,096 Unicode code points.
- `sendMessage.parse_mode`, when present, is exactly `Markdown`.
- `answerCallbackQuery.callback_query_id` is a non-empty bounded string.

The adapter uses native `RequestData.parameters`, not form encoding or `RequestData.json_parameters`, and rejects `RequestData.contains_files` before serialization.

### 5.3 Synchronous Telegram API adapter

`TelegramBotAPI` wraps the Telegram endpoint contract and `PinnedHTTPClient` for scheduler calls. It exposes only the operations needed by this project, principally `send_message()`.

It parses the bounded response internally. Delivery is successful only when:

- HTTP status is 2xx;
- the body is valid UTF-8 JSON;
- the top-level value is an object; and
- `ok` is exactly `true`.

The adapter never logs or returns the raw response body or Telegram `description`. It returns a small typed result containing only a stable outcome code, retry classification, and a bounded `retry_after` when present.

Classification is:

- Success: HTTP 2xx plus `ok: true`.
- Deferred: HTTP/error code 429. A valid positive `retry_after` is clamped to at most one hour; a missing/invalid value uses 60 seconds.
- Transient: DNS/connect/read/write failure, pinned total deadline, HTTP 5xx, or valid-size malformed JSON/schema.
- Terminal protocol/security: redirect, blocked address, peer mismatch, unsupported encoding, response body-limit violation, or request-contract denial.
- Terminal Telegram response: 400, 401, 403, 404, 409, and other non-429 4xx responses.

### 5.4 `python-telegram-bot` `BaseRequest` adapter

`PinnedTelegramRequest(BaseRequest)` is constructed separately for command and polling profiles and passed through both builder hooks:

```python
app = (
    Application.builder()
    .token(token)
    .request(command_request)
    .get_updates_request(polling_request)
    .build()
)
```

`run_polling()` uses:

- `timeout=20`;
- `allowed_updates=("message", "callback_query")`;
- `drop_pending_updates=True`; and
- the existing `stop_signals=None` behavior.

The command request owns a three-worker `ThreadPoolExecutor`; the polling request owns a one-worker executor. Each has a matching semaphore, so no executor work queue can grow beyond the number of workers.

`asyncio.to_thread()` is not used because it always targets the loop's default executor. `do_request()` uses `loop.run_in_executor()` with its dedicated executor.

The end-to-end deadline begins before semaphore acquisition. Executor admission uses the smaller of the remaining total deadline and a one-second pool wait. The worker receives only the remaining deadline, so executor wait cannot extend the 15/30-second profile.

The underlying executor future is tracked and awaited through `asyncio.shield()`. If the calling coroutine is cancelled, the worker continues under its bounded pinned deadline and retains its semaphore lease until the actual thread completes. Cancellation therefore cannot create hidden over-capacity.

The adapter:

- Rejects every method other than POST; `BaseRequest.retrieve()` and file downloads fail closed.
- Rejects use before initialization, during shutdown, or after shutdown with a stable safe exception.
- Maps transport/deadline failures to safe `NetworkError` or `TimedOut` codes with `from None`.
- Sanitizes non-2xx Telegram bodies into a minimal safe JSON error before PTB classifies them as `BadRequest`, `InvalidToken`, `Forbidden`, `Conflict`, `RetryAfter`, or `NetworkError`.
- Preserves only bounded numeric `retry_after` metadata.
- Maps a Telegram entity-parsing 400 internally to the safe description `telegram_bad_markup`; all other raw descriptions are discarded.
- Overrides `parse_json_payload()` so invalid JSON produces a stable `TelegramError` without PTB logging the raw payload.

The Markdown fallback in `bot_gateway.py` runs only for `BadRequest("telegram_bad_markup")`. Network, timeout, authorization, and other bad-request failures are not converted into a second plain-text send.

### 5.5 Scheduler delivery and retry outbox

The duplicate scheduler send paths delegate to one delivery engine. Existing wrappers may retain their current boolean return contract, but the engine produces an internal `DeliverySummary` with success, terminal, deferred, and queued counts.

Admin fan-out is recipient-independent and round-based:

1. Resolve the current token and normalized unique admin ID list.
2. Attempt every pending recipient once before retrying any recipient.
3. Remove successes and terminal failures from the pending set.
4. Queue 429 recipients immediately at their `not_before`; do not sleep and retry them inline.
5. For other transient failures, sleep 0.5 seconds before round two and 1 second before round three.
6. After three total attempts, enqueue only the recipients still transiently failed, with their first queued attempt eligible after 60 seconds.

This is intentionally at-least-once. A timeout after Telegram accepted a message but before the response arrived can produce a duplicate on retry. Internal queue deduplication prevents application-generated duplicate retry items but cannot remove this transport ambiguity.

Each retry item contains:

- message text;
- parse mode;
- one recipient;
- creation time;
- next eligible time;
- retry count; and
- a non-reversible in-memory fingerprint for deduplication only.

It never contains the token. The queue is protected by its existing state lock plus a separate non-blocking drain lock so two drains cannot process the same snapshot.

Queue policy:

- Maximum 50 per-recipient items.
- Expiry after 24 hours.
- Prune expired items and deduplicate before applying capacity.
- If still full, evict the oldest queued item so the newest operational alert is retained; increment a subject-free dropped counter.
- Never persist queue contents to disk, database, logs, metrics, or health output.

Register a `telegram-retry` `ScheduledTask` every 60 seconds. One pass processes at most ten due items and skips future items without head-of-line blocking. A queued attempt performs one network call, not another three-attempt inline loop:

- Success or terminal result removes the item.
- 429 updates `not_before` from the bounded `retry_after`.
- Other transient failure increments the count of completed queued attempts and applies `min(60 * 2**max(retry_count - 1, 0), 3600)` seconds before the next attempt: 60, 120, 240 seconds, then up to one hour.
- Retry sends use an internal `enqueue=False` path and can never recursively add a second item.
- Before each retry, the recipient must still be present in the current normalized `ADMIN_TELEGRAM_IDS`; removed recipients are discarded.
- If the Telegram token is now absent, the due item remains queued and is deferred for 60 seconds until expiry. A fresh initial send while Telegram is intentionally unconfigured remains a no-op and is not queued.

## 6. Logging, privacy, and observability

Telegram egress logs use stable event codes and aggregate counts only. They may include profile, method name, outcome class, attempt number, queue depth, expired count, dropped count, and oldest queued age.

They must never include:

- bot token or token-derived URL path;
- request/response body;
- Telegram error description;
- message text, callback data, username, or chat ID;
- exception `repr` or `exc_info=True` from Telegram transport failures.

The existing pinned-core security logger continues to record only sanitized consumer, reason, safe origin, and hop number. The Telegram audit contexts are fixed literals, one for scheduler command traffic, one for SDK command traffic, and one for SDK polling traffic.

Scheduler status may expose only subject-free queue telemetry: depth, oldest age, expired total, dropped total, and last drain outcome counts. Retry text and recipients exist in memory for at most 24 hours and are not part of persistent telemetry.

## 7. Lifecycle and compatibility

Pin `python-telegram-bot>=22.7,<23` in `requirements.txt`. CI installs the newest version in this range, so the integration contract fails before an incompatible 22.x release is accepted.

Runtime compatibility checks require the `BaseRequest` lifecycle/read-timeout contract, both `ApplicationBuilder` request hooks, and `RequestData.parameters`/`contains_files`. A missing capability disables Telegram safely; it never selects `HTTPXRequest`.

The command request reports a default `read_timeout` of 15 seconds. The polling request reports 5 seconds, which PTB adds to the 20-second `getUpdates.timeout`, producing the approved 25-second inactivity window. Explicit SDK timeout arguments may tighten but never relax the profile maximums; `None` never creates an unlimited operation.

Executors and semaphores are created in `initialize()`, not at import or construction. Initialization and shutdown are idempotent and concurrency-safe. Shutdown:

1. Marks the adapter closing and rejects new work.
2. Cancels executor work that has not started.
3. Awaits tracked workers for the maximum profile deadline plus a small one-second cleanup allowance.
4. Calls executor shutdown after active workers exit.
5. If the invariant is exceeded, records a stable lifecycle failure and uses non-waiting executor shutdown; Python cannot safely kill an in-flight thread.

Partial application initialization invokes cleanup for both request instances. The polling retry loop remains PTB-owned and can recover from transient failures, but every individual attempt remains bounded and pinned. Startup/bootstrap keeps PTB's zero bootstrap-retry default so invalid configuration fails promptly.

## 8. Testing strategy

### 8.1 Pinned core

Extend `tests/test_pinned_http.py` with:

- request serialization and 64 KiB pre-DNS rejection;
- non-serializable/NaN rejection;
- POST headers and exact JSON bytes;
- no cookies, ambient proxies, custom headers, redirect replay, or connection reuse;
- request write, encoded/decoded response, gzip bomb, unsupported encoding, and total-deadline bounds;
- security-denial safe-origin logging; and
- explicit regression tests proving `get()` behavior is unchanged.

At least one test must traverse the actual `httpcore.ConnectionPool`, pinned network backend, socket stream, peer verification, HTTP request writer, and bounded response reader using deterministic injected sockets. A mocked `PinnedHTTPClient.post_json()` alone does not satisfy the transport requirement. CI does not contact Telegram or public DNS.

### 8.2 Telegram contract and SDK

Add focused tests for:

- exact origin/token/path validation and token redaction;
- command versus polling method allowlists;
- method field/value allowlists;
- multipart, file, GET/retrieve, query, fragment, redirect, encoded path, and unknown method denial;
- success, 429, every terminal 4xx class, 5xx, malformed JSON, oversized body, and security denial;
- safe PTB exception mapping and `telegram_bad_markup` fallback;
- actual `RequestData` produced by the installed compatible PTB version for `getMe`, `deleteWebhook`, `getUpdates`, `sendMessage`, and `answerCallbackQuery`, with 22.7 as the initial reference version;
- builder wiring that proves both request slots use `PinnedTelegramRequest`, never `HTTPXRequest`;
- executor saturation, full-chain deadline, cancellation lease retention, idempotent lifecycle, and partial-initialize cleanup; and
- sentinel assertions proving token, path, chat ID, message text, callback data, and raw payload never reach logs or exception strings.

### 8.3 Scheduler

Add behavior tests for:

- independent recipients and round-based fairness;
- retry backoff and maximum attempts;
- partial success without resending successful recipients;
- 429 scheduling;
- terminal failures not queued;
- per-recipient dedupe, capacity eviction, expiry, and no head-of-line blocking;
- current-admin filtering and token rotation/removal behavior;
- one-attempt drain and non-recursive requeue;
- drain-lock concurrency; and
- registration of the 60-second `telegram-retry` task.

Replace the current source guard requiring `exc_info=True` with secret-safe behavioral assertions. Update `tests/test_pinned_http_consumers.py` so the known-unpinned Telegram fetcher set becomes empty and cannot grow silently.

### 8.4 Verification baseline

Implementation is not complete until all of these pass:

1. Focused pinned-core and Telegram suites.
2. Existing mapped-consumer, geocode, realtime, and resilience suites.
3. `python -m pytest tests/ agent/tests/ -m "not slow"` using the repository's normal CI environment.
4. `python -m ruff check .`.
5. `python scripts/checks/run_hard.py --all`.

No live Telegram call is part of automated verification.

## 9. Rollout and rollback

There is no feature flag that restores unpinned Telegram HTTP. When a token is configured but the pinned adapter cannot initialize, Telegram fails closed while unrelated API/Zalo capabilities remain available.

The implementation rollout order is:

1. Add and verify `post_json()` while keeping every existing GET consumer unchanged.
2. Add the Telegram contract and synchronous adapter.
3. Migrate and test scheduler delivery/outbox behavior.
4. Add the PTB `BaseRequest` adapter and wire command/polling instances.
5. Remove the two known-unpinned scheduler exceptions and run the full baseline.
6. Synchronize `docs/ROADMAP.md` and `docs/HANDOFF.md` with the verified local state.

Production validation is a separate authorized operation. Its runbook will verify startup `getMe`/`deleteWebhook`, active bounded long polling, one harmless command response, queue telemetry, and absence of token/path/body data in logs. It will not be executed as part of local implementation.

Rollback uses a code commit rollback. Runtime fallback to `HTTPXRequest`, `httpx.post()`, or any unpinned transport is prohibited.

## 10. Success criteria

- `PinnedHTTPClient.get()` has no behavioral or public-signature regression.
- All Telegram scheduler and SDK traffic uses the pinned JSON POST boundary.
- Telegram origin, path, method, fields, sizes, decompression, and deadlines are enforced before or during the real transport path.
- SDK polling remains async-responsive with dedicated bounded executor capacity.
- Scheduler correctly distinguishes success, deferred, transient, terminal, and security outcomes.
- Successful recipients are not resent by the application retry queue.
- The retry task is registered, bounded, non-recursive, subject to current admin authorization, and observable without exposing identifiers or content.
- Logs and exceptions contain no token, URL path, chat ID, message text, callback data, or raw Telegram payload.
- `KNOWN_UNPINNED_FETCHERS` is empty.
- Focused tests, the full baseline, Ruff, and the hard gate pass.

## 11. Accepted residual risks

- At-least-once scheduler delivery can create a duplicate after an ambiguous timeout; Telegram offers no idempotency key to remove this risk.
- The in-memory outbox is lost on process restart. This is accepted for best-effort admin alerts to avoid adding a sensitive persistent store.
- A future PTB 22.x release may change `RequestData` behavior despite the major-version bound. CI contract tests and fail-closed runtime capability checks contain this risk.
- A legitimate polling response over 2 MiB is rejected and retried. Narrow update types and Telegram's normal update limits make this unlikely; raising the limit requires evidence and a design update.
- Python cannot forcibly terminate a worker thread stuck below the pinned transport. The existing resolver, socket inactivity, decompression, and total deadlines are therefore mandatory lifecycle invariants.
