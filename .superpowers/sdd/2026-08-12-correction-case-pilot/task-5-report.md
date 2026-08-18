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

## Breaker remediation after the five-round ceiling — finding 2 (source-guard bypasses)

This is not fix round 6. Task 5 hit the five-round ceiling at `9b265f45` with two
Important findings retained by the final independent review. This entry records
remediation of the second finding only; finding 1 (catalog readiness) is still
open, and a fresh independent review of both is still owed before Task 5 may be
marked complete.

Both bypasses were reproduced before any code changed, by driving the committed
scanner directly rather than trusting the review text. `console.log` with a
bearer inside an executable template expression returned no violation, and
`localStorage.setItem('case', ...)` returned no violation once its argument was
wrapped in a template literal — so the bypass also defeated a sink the guard
already claimed to cover. Five browser property-assignment sinks
(`location.href`, `document.body.textContent`, a `localStorage` property, a
computed `sessionStorage` key, and `innerHTML`) likewise returned nothing,
because the frontend scanner only walked call spans.

RED: three tests were added first. Template-expression and property-assignment
coverage failed with an empty violation list against the expected two and six
entries; the accompanying negative test passed immediately, confirming the new
expectations did not simply widen the guard.

GREEN: `_strip_literals` was replaced with a linear scanner that drops literal
text but preserves `${...}` expressions and the source line count, so bearers
interpolated into templates stay visible to identifier analysis without
reintroducing file-wide false positives. A separate assignment pass matches a
member or computed target whose root is a browser sink object or whose final
property is a persisting sink, rejects comparison operators, and reads only the
bounded right-hand expression. Alias resolution was extracted so call and
assignment passes share one alias set, and results are now deduplicated and
ordered. The scanner remains a bounded Python analyser: adding a Node parser
would have introduced an npm dependency and a subprocess boundary into a Python
test, which is the Windows-versus-Linux class of defect recorded in CLAUDE.md
section 5b.

Verification: the source-guard suite returned `10 passed`. Ten hostile variants
were then confirmed caught, including three not covered by the new tests
(`document.cookie`, `window.name`, and a templated `srcdoc`), while a strict
comparison, a string literal naming a bearer, and a non-bearer assignment to a
sink stayed unflagged. The whole-repository scan over 448 production sources
returned no violations in 4.88 seconds, so the broadened guard added no false
positive to real code. Regression suites were unchanged: receipts, access
security and privacy logging `22 passed`; case store `15 passed`; PostgreSQL
transaction `8 passed`; database `198 passed, 1 xfailed`. Ruff passed,
`git diff --check` exited 0, and the staged repository hard gate reported
`hard=0` with no ratchet increase.

Watch item for any future sink expansion: `capability` is a live frontend domain
term in `web-nuxt/composables/useFeature.ts` and `web-nuxt/utils/featureFlags.ts`
that is unrelated to case bearers. It reaches no sink today, and the negative
test pins that pattern, but those two files must be re-measured before the sink
lists grow again.

## Breaker remediation after the five-round ceiling — finding 1 (catalog readiness)

Still not a fix round. This entry closes the first retained Important finding.

Both bypasses were reproduced on live PostgreSQL 16.15 before any code changed.
Repointing `case_access_sessions_case_receipt_fkey` at a same-named table in a
`shadow` namespace left `target_table`, ordered source and target columns, the
delete action and `convalidated` all identical, and readiness reported no issue
at all. Adding `WHEN (false)` to `case_receipts_case_immutable`, and separately
replacing `public.reject_case_receipt_case_move` and
`public.enforce_case_access_same_case` with `BEGIN RETURN NEW; END;` bodies,
each left every compared trigger field intact while disabling the guard.

RED: five pure catalog-drift cases and one schema-parity test were added first
and failed, and the live drift probe failed on the shadow-namespace foreign key.

GREEN: the constraint query now selects the target namespace and the update
action, joined through `pg_namespace` on the referenced relation, and the
foreign-key expectations pin `public` and `NO ACTION`. The trigger query now
selects the trigger predicate and the function body, and the trigger
expectations pin no predicate plus the exact body of each guard. Bodies are
compared after whitespace normalisation, which lets migration 080 and
`init.sql` keep their own formatting; a new test re-extracts both files and
asserts they still agree with the readiness constants, so a future edit to
either schema source cannot silently diverge from what readiness accepts.

The predicate is read through `pg_get_triggerdef` rather than
`pg_get_expr(tgqual, ...)`: the pre-existing `trg_entity_ratings` triggers on
`posts` carry a qualification spanning both OLD and NEW, which makes
`pg_get_expr` fail with `expression contains variables of more than one
relation` across the whole-catalog scan. Readiness now records no predicate as
NULL and any predicate as the rendered trigger definition, so it stays
fail-closed without depending on single-relation rendering.

Verification: `test_database.py` `204 passed, 1 xfailed`, up from 198 by the
five drift cases and the schema-parity test. Migration and readiness including
the live drift probes `14 passed`. Case schema `13 passed`; receipts, access
security and privacy logging `22 passed`; case store `15 passed`; PostgreSQL
transaction `8 passed`; source guard `10 passed`. Five hostile mutations were
then confirmed detected live, including a foreign key switched to
`ON UPDATE CASCADE`, which is the same class as the reported target-namespace
gap. Comparing the readiness output of `909dd42c` and this change against the
same healthy schema produced an identical issue set, so the broadened checks
introduced no false positive. Ruff passed and `git diff --check` exited 0.

### Blocking defect found during verification, NOT fixed here

On PostgreSQL 16.15 a freshly migrated database reports six Case Kernel issues
before any tampering: the five expiry, revision and digest-shape CHECK
constraints and the partial access-session index. `pg_get_expr(..., pretty)`
renders `receipt_revision >= 1`, while the pinned expectation is
`(receipt_revision>=1)`; the outer parentheses are not emitted by this server
version. `case_kernel_schema_status` therefore returns `case_schema_not_ready`
for a correct schema, so the Case Kernel cannot report ready once its flag is
enabled. This is a third defect, pre-existing at `909dd42c`, outside both
reported findings, and it is left untouched pending an owner decision because
the fix changes production readiness semantics in a locked area. The existing
drift tests never caught it because they assert only that an expected issue is
present, never that a healthy schema yields an empty issue set.

## Breaker remediation — blocking readiness defect (PostgreSQL 16 rendering)

The defect recorded in the previous section is now fixed on owner instruction.

Root cause, measured rather than inferred: the constraint and partial-index
queries asked `pg_get_expr` for pretty output. Pretty rendering is a
presentation format and PostgreSQL 16 omits the outer parentheses, so
`receipt_revision >= 1` was compared against the pinned
`(receipt_revision>=1)` and five CHECK constraints plus the access-session
partial index reported drift on a schema that was entirely correct.
Non-pretty rendering is the canonical form and reproduces the pinned
expectations exactly for all six.

The fix asks for canonical output instead of loosening the expectations, so
drift detection is not weakened: no pinned constant changed. Index key columns
are unaffected because `pg_get_indexdef` returns identical text in both modes.
Trigger predicates continue to render through `pg_get_triggerdef`, which is
only consulted when a predicate exists and therefore only ever appears on the
drift path.

The real test gap was that no test asserted the healthy direction. Every drift
case asserted that an expected issue was present, which remains true when the
entire catalog is reported as drifted, so a permanently blocked readiness was
indistinguishable from a working one. Two tests now close that gap: a live
assertion that a freshly migrated database yields no Case Kernel issues and
reports `case_kernel_ready`, and a pure assertion that the untampered catalog
doubles produce no issues.

RED: the live healthy-schema test failed with the six pre-existing issues while
the pure test passed, which localised the defect to SQL rendering rather than
to the expectations or the doubles.

GREEN: migration and readiness `15 passed`; `test_database.py`
`205 passed, 1 xfailed`; case schema `13 passed`; receipts, access security and
privacy logging `22 passed`; case store, PostgreSQL transaction and source
guard `33 passed`. A freshly created and migrated disposable database now
reports `{'ok': True, 'state': 'ready', 'code': 'case_kernel_ready'}` with an
empty issue set, and ten hostile mutations were confirmed still detected
against that clean baseline: a weakened CHECK bound, a renamed CHECK, a
loosened digest-shape regex, a dropped index predicate, a foreign key moved to
another namespace, a foreign key switched to `ON UPDATE CASCADE`, a restrictive
trigger predicate, two no-op guard bodies, and a disabled trigger. Ruff passed
and `git diff --check` exited 0. The disposable databases created for this
verification were dropped afterwards.
