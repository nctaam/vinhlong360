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

## Fix round 2 (persistence and readiness gaps)

This continuation adds the missing PostgreSQL guard on rotation, canonical
unpadded key re-encoding checks, Python constant-time digest comparison after
candidate lookup, and a replay-safe same-case access-session trigger in both
080 and `init.sql`. A focused RED test first reached the unguarded rotation
crypto call; it now fails closed with `case_postgresql_required`. The guarded
PostgreSQL rotation race remains one successor plus one credential failure, and
the focused suite is green. The disposable `vl360_case_task5_fix2_test` is
dropped after the final gate.

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

## Fix round 2 (continued)

The follow-up review found a missing PostgreSQL guard on rotation, noncanonical
key acceptance, SQL-only digest comparison, and missing same-case ownership
enforcement. Rotation now fails closed before touching crypto when PostgreSQL
is unavailable. The shared key validator requires canonical unpadded URL-safe
Base64 re-encoding. Exchange/validation perform a Python constant-time digest
comparison after candidate lookup, and migration/init install an idempotent
same-case access-session trigger. The focused guard RED was reproduced first
and then passed after the fix; final focused verification is attached to the
new commit.

## Fix round 3 (receipt authority and readiness)

The final continuation closes deterministic bearer lookup, same-case receipt
ownership, expired idempotency reuse, collision retry classification, and
schema readiness drift. Access validation now narrows by session digest and
asserts the joined receipt has the same case before the Python constant-time
comparison. Receipts have a composite `(case_id, receipt_id)` key, access
sessions have the matching composite foreign key, and receipt case moves are
rejected by idempotent triggers in migration 080 and `init.sql`.

Idempotency keys are serialized with a transaction advisory lock; expired
rows are removed before reuse, preventing raw unique violations under same-
actor concurrency. Receipt collision retries now require SQLSTATE `23505` and
one of the expected public-reference/capability constraints. Transaction-
bound receipt issuance is available on `CaseTransaction`, and rotation replay
is supported when an explicit idempotency key is supplied. Configuration and
readiness no longer strip key or owner inputs before shared validation.

Readiness now checks case column types/nullability/defaults, owners,
constraint definitions, indexes, foreign keys, and triggers while preserving
the dormant schema-79 behavior and stable `case_schema_not_ready` code.

Verification: database readiness `191 passed, 1 xfailed`; guarded migration,
readiness, and schema contracts `50 passed`; case store/transaction contracts
`23 passed`; access/receipt/source guards `17 passed`; Ruff and `git diff
--check` passed. The disposable `vl360_case_task5_fix2_test` database was
dropped after verification.

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

## Fix round 4 (replay authority and exact readiness)

Rotation replay now resolves the presented bearer before reading encrypted
idempotency output and binds the request digest to the operation key, actor,
case, and session digest. Invalid tokens and valid tokens from another case
receive the same public credential error. Revoke and rotate explicitly acquire
PostgreSQL row locks in the shared case, ordered-receipts, ordered-sessions
sequence, including the real concurrent rotation regression.

Readiness now verifies the owning table and catalog definition for the required
receipt/session constraints, indexes, foreign keys, and triggers; checks the
foreign-key target and delete action; requires unique public references,
capability digests, and session digests; and checks every Case Kernel table
owner while retaining the dormant schema-79 projection. CSRF validation uses
strict canonical unpadded URL-safe base64 decoding for both nonce and signature.
The source guard tracks exact bearer identifiers and direct aliases only inside
Python/Nuxt logger, query, route, notification, persistence, DOM, local-storage,
and session-storage call arguments rather than treating the whole file as a
single sink.

RED evidence: the CSRF suffix regression failed because an extra `=` was
accepted; the exact-capability alias regression failed with `0` detected sinks
instead of `2`. GREEN evidence: combined focused verification returned
`221 passed, 13 skipped, 1 xfailed`; the freshly migrated disposable PostgreSQL
suite returned `45 passed`; Ruff and `git diff --check` passed. The disposable
`vl360_case_task5_fix4_test` database was dropped after verification.

## Fix round 5 (catalog identity and bearer sink coverage)

Readiness now consumes structured PostgreSQL catalog identity instead of
owner/name checks or definition substrings. Required CHECK and UNIQUE
constraints are matched by exact normalized expression or ordered columns;
foreign keys include ordered source and target columns plus cascade action;
indexes include ordered keys, predicate, uniqueness, btree method, and
valid/ready/live state; triggers include table, function schema/name, exact
event bitmask, enabled state, and `UPDATE OF` columns. Constraint validation and
deferrability are also fail-closed. Dormant schema-79 behavior and migration
080/`init.sql` remain unchanged.

The source guard now detects Python `parse_qs`/`parse_qsl` bearer use and
annotated direct aliases, and detects Nuxt/TypeScript typed aliases at
`console`, `URLSearchParams`, route/query, notification, persistence, DOM,
local-storage, and session-storage call spans. It reports the exact call line
and remains argument/dataflow scoped, so unrelated field names and string
literals in the same file do not create file-wide false positives.

RED evidence: the focused regression run returned `8 failed, 1 passed` for a
renamed/weakened CHECK, wrong composite FK target/action, wrong ordered or
non-unique/predicate index, wrong trigger function/events, query parsing,
typed logger/console aliases, URL construction, and browser sinks. GREEN
evidence: source guard `7 passed`; access security with PostgreSQL `11 passed`;
case store `15 passed`; PostgreSQL transaction `8 passed`; PostgreSQL schema
`13 passed`; migration/readiness including live catalog drift probes `14
passed`; database `198 passed, 1 xfailed`. Ruff passed on all touched Python
files, and final staged hard-gate evidence is recorded with the commit.
