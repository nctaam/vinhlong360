# Task 6 Report: Correction Create Command And Idempotency

## Status

Implemented the canonical correction intake: `CreateCorrectionCommand` and
`CreateCorrectionResult`, `CaseService.create_correction`, a PostgreSQL-backed
rate bucket, and encrypted lost-response replay. One public request becomes
exactly one case or nothing at all.

## TDD Evidence

The plan's RED command was run after creating the two test files:

`python -m pytest -q agent/tests/test_correction_create.py agent/tests/test_case_idempotency_postgres.py`

It failed at collection with `ModuleNotFoundError: No module named 'cases.service'`,
exactly the expected initial RED. Implementation then proceeded against the
failing tests.

Three RED rounds were driven by the real schema rather than by guesswork.
`correction_items.entity_id` carries a foreign key to `entities`, so an unknown
target produced a raw `ForeignKeyViolation`; the service now checks the target
inside the transaction and returns `correction_entity_unknown` (404).
`case_promise_clocks.observed_at` is `NOT NULL`, so the four clocks record an
observation at creation. Finally the durable rate bucket and the durable replay
row are by design not reset by a process restart, so a second run of the suite
at the same fixed clock saw its own earlier state; both module fixtures now
clear the buckets and `create:` replay keys they assert on, and the suite is
green twice in a row.

## Behaviour

- Validation and safety routing run before any transaction opens, so a rejected
  request never touches the database.
- A public command carrying an operator scope is rejected with
  `operator_actor_not_allowed` (403). Assisted intake is a separate lane.
- Account linkage comes only from the server-side session. A submitted
  `authenticated_user_ref` that is absent from, or contradicts, the session is
  rejected with `authenticated_ref_not_server_derived` (403).
- An optional phone is a reply address, never identity: identity assurance stays
  `none`, reporter privacy stays `anonymous`, and no party authority is created.
- Items are bounded: at most ten, an allowlist of correctable field paths, a
  2000-character value ceiling, no unchanged value, a positive base revision,
  and no duplicate entity/field pair.
- A bounded pre-intake classifier routes explicit imminent-harm language to the
  urgent lane with `correction_safety_routing` (409) and copy that names 113,
  114 and 115. It creates no case and never presents this service as an
  emergency authority.
- A Zalo handoff requires explicit user confirmation, accepts a 64-character
  conversation digest, and rejects construction outright when a transcript is
  attached.
- Case, interaction, optional party authority, E0 evidence, items, four clocks,
  the first work item, transition, audit, receipt and notification intent commit
  in one transaction. Receipt failure rolls the whole case back, verified by
  forcing the capability generator to raise and asserting the case count is
  unchanged.
- Reported and proposed values, and the optional contact, are persisted only as
  ciphertext; the outbox payload carries neither the value nor the capability.
- An exact retry replays the original case, reference and capability with
  `replayed=True`; the same key with a different body returns
  `idempotency_conflict` (409); after 24 hours it returns `idempotency_expired`
  (409) without creating a second case and without handing the capability back;
  a different actor under the same key conflicts.

## Deviations From The Plan, For Review

1. The plan's file list for this task did not include `agent/cases/security.py`,
   but correction values need a durable private envelope and the only existing
   payload cipher enforces the 24-hour replay window. Two methods,
   `encrypt_private_payload` and `decrypt_private_payload`, were added. They
   reuse the existing replay Fernet deliberately, so **no third HKDF salt is
   introduced** and the locked salt list is unchanged.
2. "Normalize only bounded field paths from policy" could not be satisfied from
   policy: `config/case-service-policy.json` defines no field paths and
   `cases/policy.py` rejects any unexpected top-level key, so adding one would
   change a locked policy structure and require a revision bump. The allowlist
   lives in `service.py` as `CORRECTABLE_FIELD_PATHS` with a comment recording
   that promotion into policy is an owner decision.
3. `correction_entity_unknown` and the `require_entities` guard are not named in
   the plan; they were added because the real foreign key would otherwise leak a
   driver error to the transport layer.

## Verification

`python -m pytest -q agent/tests/test_correction_create.py agent/tests/test_case_idempotency_postgres.py agent/tests/test_case_transaction_postgres.py`

Result: `34 passed`, and `26 passed` twice in a row for the two new files alone,
confirming the suite is repeatable against a durable store.

Regression: receipts, access security, case store, privacy logging and the
source guard `51 passed`; case schema, migration readiness and database
`233 passed, 1 xfailed`. Ruff passed on every touched file and `git diff --check`
exited 0.

## Not Done Here

No transport layer, no public API, no rate-limit wiring for receipt exchange,
contact OTP, review or rotation beyond the shared helper. Those belong to Task 7
and later. The task has not been reviewed independently yet.

## Pairing tests, and two defects they caught

The staged hard gate blocked the first commit on R20.7: the rule pairs a changed
`agent/**.py` to a staged test by filename token or AST import, and the plan's
mandated test names (`test_correction_create.py`,
`test_case_idempotency_postgres.py`) carry no `service`, `rate_limit`, `store`
or `security` token. An `agent/cases/*` module cannot be paired by import either,
because the rule matches `security`/`agent.security`, never `cases.security`.
Rather than take the soft-skip escape hatch, direct tests were added for the
modules actually changed, which invariant B3 wants anyway:
`agent/tests/test_case_service.py`, `agent/tests/test_case_rate_limit.py`, plus
new sections in `test_case_store.py` and `test_case_access_security.py`.

Those tests immediately found two real defects in this task's own code:

1. The urgent-language classifier folded text with NFD only. Vietnamese `đ`
   (U+0111) does not decompose, so a marker such as `đánh đập` could never match
   and a report of a beating would have been filed as an ordinary correction.
   `_fold` now maps that letter before normalising.
2. `decrypt_private_payload` accepted a replay envelope, because both are the
   same Fernet and it only looked for a `payload` key. A replay token carries a
   raw capability, so the two envelopes must not be interchangeable. Private
   payloads are now tagged and the tag is required on the way back.

Final verification after those fixes: the plan's GREEN command `34 passed`; the
six Task 6 files together `93 passed`; receipts, privacy logging, source guard,
case schema, migration readiness and database `258 passed, 1 xfailed`; Ruff
clean across `agent/cases/` and every touched test; staged hard gate reports
`hard=0` with no ratchet increase.
