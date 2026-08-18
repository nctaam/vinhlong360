# Task 8 Report: Optional Phone Verification And At-Least-Once Notification Outbox

## Status: COMPLETE

Two of the three moving parts are complete, tested and wired. The third, Step 3's
extraction of the live eSMS transport out of `agent/auth.py` into
`agent/sms_provider.py` with a new `PinnedHTTPClient.post_json`, is deliberately
**not attempted here**. Reasons are given below rather than left implied.

## Delivered

**Optional phone verification** (`agent/cases/contact.py`). A verified phone is a
reply address and nothing else: the verification test asserts that no
`case_party_authority` row is created, so it never becomes account or listing
authority. Authority for the flow comes from the case access session the caller
already holds — the adapters accept `access_token`, never a `case_id`, so a
verified number cannot be attached to somebody else's case, and a test pins that
signature.

Codes are stored only as a keyed digest bound to the case, so the same code for a
different case is a different digest. The phone is stored as a keyed digest for
deduplication and separately as ciphertext on a case interaction; the plaintext
number is never written to `case_contact_challenges`. Challenges expire after ten
minutes, a wrong code and an unknown case both raise the same public
`invalid_case_credential`, and attempts are bounded by the durable `contact_otp`
bucket. Request and verify deliberately get **separate** budgets: one stops
flooding a phone with codes, the other stops guessing a code, and sharing them
would let either attack spend the other's allowance.

Withdrawing consent deletes the live challenge, so `verified_contact_for` returns
nothing and the dispatcher has nobody to notify.

**At-least-once dispatch** (`agent/cases/outbox.py`). `dispatch_case_outbox`
claims due items with `FOR UPDATE SKIP LOCKED`, so two workers never double-send.
Authority is re-read immediately before every side effect: no deliverable contact
or no live receipt means the item is suppressed rather than delivered. A
retryable failure backs off on a bounded schedule (1m, 5m, 30m, 2h) up to five
attempts; a permanent failure dead-letters. Neither ever touches the case — a
notification outage cannot invalidate a committed receipt, and a test asserts the
case row survives a dead-letter.

The delivery key is derived from the outbox id alone, so a provider that
deduplicates sees one logical send across retries; a test asserts the key is
identical on both attempts.

Messages come from a closed per-topic catalog. An unknown topic raises rather
than improvising copy at a reporter. The message carries the public reference and
generic instructions only — a test pins the absence of phone fragments, the word
capability, evidence, proposed values, the internal owner and backstage phase
names.

**Schema constraints honoured.** Migration 080 is locked, so no new columns were
invented: `case_outbox.status` only permits `pending/processing/sent/failed`, so
suppression and dead-lettering are expressed as `failed` with a distinguishing
`last_error_code` (`suppressed_at_delivery` versus the provider's code).
`case_contact_challenges` has no attempts column, so bounded attempts use the
durable rate bucket that was already reserved for exactly this in Task 6.

**Transport.** `POST /api/cases/contact/request` and `/contact/verify` no longer
answer `503`; they reach the service behind the same same-origin, CSRF-bound
session contract Task 7 established. Request answers `202` and never reveals
whether the number exists or was reachable; verify answers `204`. An unusable
phone number is `400 invalid_contact_phone`.

## Deferred, with the reason

Step 3 moves eSMS out of `agent/auth.py` and extends `agent/pinned_http.py`. That
is a refactor of live authentication code: CLAUDE.md records 2FA as a deploy gate
where a mistake locks users out, and invariant B3 requires test coverage of a
blind module *before* refactoring it. Doing that at the end of a long session,
immediately after five other tasks, is exactly the wrong moment. The case tests
use an injected fake provider throughout — the plan asks for that anyway — so
nothing here depends on the extraction, and `agent/sms_provider.py`,
`agent/auth.py`, `agent/pinned_http.py`, `agent/scheduler.py`,
`agent/tests/test_sms_provider.py` and `tests/test_pinned_http_consumers.py` are
untouched.

To finish Task 8 the remaining work is: cover the existing eSMS path in
`auth.py` first, then extract it behind a `SmsProvider.send` interface, extend
`PinnedHTTPClient` with the bounded `post_json`, register both consumers in
`tests/test_pinned_http_consumers.py`, and have the scheduler invoke
`dispatch_case_outbox` single-flight so a dispatcher failure cannot stop
unrelated jobs.

## Verification

Case suites, including the two new files: `235 passed`. Authentication hardening,
advanced security and database regression, none of which this change touches:
`382 passed, 1 xfailed`. The contact and outbox suites pass twice in a row, so the
durable state they exercise does not leak between runs. Ruff clean on
`agent/cases/` and both new test files; `git diff --check` exit 0.

## Step 3: the eSMS extraction, done under a characterisation net

The deferral above is closed except for one named piece.

**The net came first, as B3 requires.** `agent/auth.py._send_sms` had no
behavioural coverage at all — the only tests were two source-text assertions in
`test_qa_fixes.py` checking that the function body contained a retry loop and a
backoff expression. Seven characterisation tests were written first and passed
against the untouched function: a missing provider key is a dev no-op returning
True, a `CodeResult` of 100 posts once and reports delivered, the national number
is converted to international form, the endpoint is exact, a rejected code
retries to the bound of three and then reports failure, a transport exception
retries and can still succeed, and neither the API key, the secret, the message
nor the full phone number reaches the log.

**Then the move.** `agent/sms_provider.py` now owns the payload shape, the
endpoint, the retry bound, the backoff curve, the success/failure classification
and the phone masking, exactly once. It exposes two entry points over that one
implementation: `send_async` for handlers already on the event loop, and `send`
for the outbox dispatcher, which runs in a worker. Forcing authentication onto a
blocking client inside an async endpoint would have been a real behaviour change,
which is precisely the risk B3 warns about, so the concurrency model of each
caller is preserved. `auth._send_sms` is now a delegation that still returns a
plain bool. The same seven assertions pass unchanged after the move.

**A source-shape test had to follow its code.** `test_qa_fixes.py` asserted that
`auth._send_sms`'s body contained `asyncio.sleep` and `2 **`. The Finding-018
guarantee is retry plus exponential backoff, and that guarantee is intact — it
simply lives in `sms_provider` now, so those two assertions were repointed there.
The behavioural tests added here are the stronger guard; searching a function
body for text was always going to block a legitimate refactor.

**The dispatcher runs on a schedule.** `task_case_outbox` is registered at a one
minute interval and is inert while `CASE_KERNEL_ENABLED` is false — it returns
before touching the database. Failures are contained by the scheduler's existing
per-task handling, so an SMS outage cannot stop unrelated jobs, and the
dispatcher's `FOR UPDATE SKIP LOCKED` claim keeps a second worker from
double-sending.

### Still outstanding, and named honestly

`PinnedHTTPClient.post_json` was **not** written, so the eSMS call is not pinned.
`tests/test_pinned_http_consumers.py` caught this immediately: extracting the
transport surfaced `('agent/sms_provider.py', 'send')` as newly unpinned egress.
It is registered in `KNOWN_UNPINNED_FETCHERS` deliberately, alongside the two
Telegram POSTs that are there for exactly the same reason — the pinned client is
GET-only by design. The real egress posture is unchanged: this is the same call
that already ran unpinned inside `auth.py`. But the documented unpinned surface
did grow by one entry, and that is the honest cost of stopping here.

Adding a POST verb to the module whose entire purpose is egress safety — exact
origin resolution, approved-socket dialing, peer verification, deadlines, body
caps, zero cross-origin redirects — deserves its own focused pass with its own
adversarial tests. It is the last remaining item of Task 8.

Verification: the plan's Step 5 command `219 passed`; the wider sweep across
contact, outbox, provider, public API, service, store, create, idempotency, QA
fixes, auth hardening, advanced security and database `653 passed, 1 xfailed`.
Ruff clean on every touched file; `git diff --check` exit 0.

## Step 3 completed: the eSMS POST is pinned

`PinnedHTTPClient.post_json` now exists and the outstanding item above is closed.

**The verb.** `_fetch_hop` was parameterised with a method, body and content
type, defaulting to the previous GET behaviour so the existing path is
untouched; the whole pinned suite passes unchanged. `post_json` reuses exactly
the same machinery as `get` — exact-origin check, resolver, approved-socket
dial, peer verification, total and inactivity deadlines, bounded body read — and
is deliberately **stricter** in one respect: it makes a single hop and treats any
redirect as a policy error rather than following it. Following one would replay
the request body at a destination the caller never approved, which is the whole
reason this module exists. It also refuses a payload that is not a JSON object
and refuses a request body over the encoded cap before opening a socket.

**The consumer.** `agent/sms_provider.py` now posts through a module-level
`_PINNED_HTTP` with a literal `audit_context="sms_provider"`, matching the
convention the registry verifies statically, against a policy whose only allowed
origin is `https://rest.esms.vn` and whose `max_redirects` is zero. The
deliberate exemption added earlier is gone: `sms_provider` moved out of
`KNOWN_UNPINNED_FETCHERS` and into `MAPPED_FETCHERS`, so the documented unpinned
egress surface is back to what it was before this task started. The registry's
audit-context extractor was extended to recognise `post_json` alongside `get`.

**One transport, two entry points, still.** `send` runs the pinned client and
owns the retry loop and backoff; `send_async` offloads to it with
`asyncio.to_thread`, so an event loop is never blocked on the socket and both
callers share one implementation. The seven characterisation tests still hold —
dev no-op, international form, exact endpoint, retry to the bound, exception then
success, and no credential, message or full phone in the log — with the fake
moved from httpx to the injected poster seam, because the transport underneath
changed on purpose.

Two source-shape assertions in `test_qa_fixes.py` were repointed again, to
`EsmsProvider.send` and `time.sleep`, since the loop now lives on the blocking
entry point. The Finding-018 guarantee is unchanged; the behavioural tests added
in this task are the stronger guard.

Verification: the plan's Step 5 command `222 passed`; the pinned family
(`test_pinned_http.py`, `test_pinned_http_consumers.py`,
`test_admin_pinned_http.py`) `306 passed` including ten new `post_json` cases;
provider, QA fixes, auth hardening, scheduler and outbox together `509 passed`.
Ruff clean; `git diff --check` exit 0. Task 8 is complete.
