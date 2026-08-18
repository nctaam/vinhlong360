# Task 8 Report: Optional Phone Verification And At-Least-Once Notification Outbox

## Status: PARTIAL — contact and outbox landed, the eSMS extraction is deferred

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
