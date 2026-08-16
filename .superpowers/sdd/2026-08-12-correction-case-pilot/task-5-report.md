# Task 5 Report: Secure Correction Case Receipts

## Status

Implemented the Task 5 security boundary: dedicated HKDF-derived capability and
replay keys, Crockford receipt references, digest-only capability and access
tokens, encrypted/expiring replay payloads, CSRF/cookie/origin helpers, and
PostgreSQL-backed receipt/access lifecycle operations.

## TDD Evidence

The required initial RED command was run after creating the three Task 5 test
files:

`python -m pytest -q agent/tests/test_case_receipts.py agent/tests/test_case_access_security.py agent/tests/test_case_security_source_guard.py`

It failed at collection with two expected
`ModuleNotFoundError: No module named 'cases.security'` errors. The missing
security boundary was then implemented. A replay-expiry test initially exposed
that the test had not passed its fixed clock into encryption; the test was
corrected to exercise the explicit `now` seam before continuing.

## Security Properties

- `CaseCrypto` validates a 32-byte URL-safe base64 master key before deriving
  purpose-separated HKDF subkeys with exact salts
  `vl360-case-replay-v1` and `vl360-case-capability-v1`.
- Receipt references are `VL-COR-` plus twelve Crockford symbols and a
  checked symbol. Capabilities are URL-safe 32-byte values (43 characters).
- Database receipt and access rows receive only HMAC-SHA256 digests. Raw
  capabilities/access tokens return once from the service boundary.
- Fernet replay payloads carry an injected issue time and reject tampering or
  values more than 24 hours old using the same public credential error.
- Access sessions expire at 15 minutes. Receipt expiry is 365 days. Receipt
  revocation is joined into session validation, so it takes precedence over an
  otherwise unexpired session; rotation revokes the old receipt and sessions.
- CSRF values are readable short-lived cookies, HMAC-bound to the access
  session digest, and require matching Origin, `Sec-Fetch-Site`, and header/
  cookie values. The access cookie is HTTP-only, Lax, path-scoped, and 900 s.
- The source guard scans production Python sources only and fails on bearer
  material routed to query parsing, logging/analytics, or browser persistent
  storage patterns.

## Verification

`python -m pytest -q agent/tests/test_case_receipts.py agent/tests/test_case_access_security.py agent/tests/test_case_security_source_guard.py agent/tests/test_privacy_logging.py agent/tests/test_case_store.py agent/tests/test_case_transaction_postgres.py agent/tests/test_case_schema_postgres.py`

Result: `29 passed, 17 skipped`. The skips are guarded PostgreSQL tests; this
environment has no `VL360_TEST_DATABASE_URL`, and the new lifecycle test only
accepts a disposable loopback DSN with `test` in its database name.

`python -m ruff check agent/cases/security.py agent/cases/store.py agent/tests/test_case_receipts.py agent/tests/test_case_access_security.py agent/tests/test_case_security_source_guard.py`

Result: `All checks passed!`

`git diff --check`

Result: exit 0.

## Schema Reconciliation

The branch has not merged migration 080, so the same additive migration and
fresh `init.sql` were reconciled rather than introducing migration 081. Direct
080 replay assigns legacy receipt revisions deterministically by
`created_at, receipt_id`, preserves anonymous subjects as `NULL`, and marks
existing session/idempotency key versions `legacy-unusable`; runtime accepts
only `v1` access-session digests. The revision has a positive check and a
unique `(case_id, receipt_revision)` constraint. Direct issue and rotation
lock the case row; rotation revokes the old receipt/sessions and inserts
`MAX(receipt_revision) + 1` in that transaction.

Authenticated subjects persist on receipts and are constant-time checked at
exchange and validation. A copied bearer used by another authenticated user
or anonymously receives the same credential error. `case_access_sessions`
now records `session_key_version`; `case_idempotency` records
`response_key_version` for Task 6 replay ownership.

## PostgreSQL Verification

Created only the loopback disposable `vl360_case_task5_security_test` as the
local `postgres` role, applied the baseline plus all migrations through the
guarded `VL360_TEST_DATABASE_URL` and `MIGRATION_APPLY_TEST_DATABASE_URL`, and
ran the expanded Task 2/4/5 verification. It returned `97 passed`. Focused
authenticated lifecycle/rotation and direct old-080 replay reconciliation then
returned `2 passed`. The database is dropped after final gates.

## Fix round 2

Round 2 hardens revocation serialization and strict key/boundary handling.
`revoke_access` now locks the case row before invalidating every receipt and
session, sharing the lock order used by rotation. Key validation requires an
exact 43-character unpadded URL-safe Base64 value decoding to 32 bytes;
configuration, readiness, and `CaseCrypto` share the validator. Replay and
CSRF malformed inputs collapse to stable credential errors, and only
`same-origin` is accepted. Module lifecycle wrappers now resolve through an
explicit immutable ContextVar seam while still permitting test injection.

RED: strict-key/future-replay and boundary regressions initially produced
8 failures; the focused corrected suite is `10 passed, 3 skipped`. The real
PostgreSQL idempotency and concurrent-rotation checks remain green from the
preceding gate, and the final focused verification is recorded with the fix
commit.

## Fix round 1

The review identified a rotate time-of-check/time-of-use window, PostgreSQL
unique-violation retry aborts, absent lost-response replay, incomplete bearer
input checks, divergent key validation, and a Python-only source guard.

The receipt insertion path now brackets each collision-prone attempt in a
savepoint. Rotation validates the session digest, key version, expiry,
revocation, receipt subject, and case authority in one `FOR UPDATE` join
transaction before revoking and creating the successor. The real PostgreSQL
two-rotation race produced exactly one revision-2 successor and one
`invalid_case_credential` loser.

Issue operations accept an explicit idempotency key. The request digest and
actor are bound to a 24-hour Fernet-encrypted receipt replay in
`case_idempotency`; an exact retry returns the original raw capability without
inserting another receipt, and another actor receives the public credential
error. The guarded PostgreSQL replay test passed.

`CaseCrypto`, production configuration, and readiness now share strict
URL-safe-base64 32-byte key validation. CSRF accepts only `same-origin`,
normalizes no non-empty subject value, rejects malformed boundary values, and
replay rejects future issue timestamps beyond five minutes. The source guard
now scans production Python AST call spans and frontend sources for named case
bearers routed to logs, query parsing, notifications, or persistence.

Focused RED evidence included `3 failed, 7 passed, 1 skipped` for future
replay/same-site/subject helpers, followed by green `10 passed, 1 skipped`.
The idempotency delegation RED was one missing keyword-argument failure;
the guarded PostgreSQL replay test and concurrent rotation test subsequently
passed. Final verification is recorded with the fix commit.
