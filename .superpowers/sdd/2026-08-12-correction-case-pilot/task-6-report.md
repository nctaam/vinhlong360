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

## Independent review of Task 6, and its five findings

A multi-agent cloud review against `breaker-base` returned five findings, all in
this task's code, all confirmed by reproduction before being fixed. Three were
graded normal and two nit; every one was accepted.

**Vietnamese values crashed intake.** `_request_digest` serialised the canonical
body with `ensure_ascii=False` and fed it to `digest_capability`, which encodes
ASCII and converts the resulting `UnicodeEncodeError` into
`CaseSecurityError("invalid_case_credential")`. Reproduced directly: a routine
address correction reading `Ấp Phú Đông, xã Long Hồ` raised an auth-shaped error
before any transaction opened. On a Vietnamese-first product with `name`,
`summary`, `description` and `attributes.address` all correctable, this broke
essentially every real submission. Every fixture in this task used ASCII values,
which is exactly why the suite stayed green. Fixed by keeping the canonical form
ASCII, and covered by a create test that files a correction in Vietnamese.

**The safety classifier blocked ordinary wording.** Folding diacritics collapses
`từ từ` (slowly) onto `tự tử` (suicide) and `tủ sát` (cabinet against) onto
`tự sát`. Measured false positives included `cửa hàng mở từ từ 8h đến 22h`,
`tăng giá từ tuần sau` and `tủ sát tường`, each of which would have been rejected
with 409 and told to call the police over an opening-hours correction. Word
boundaries do not fix this, because the folded forms are identical; the markers
are now matched with their diacritics, and only the markers that stay
unambiguous when folded are also matched unaccented, so a reporter without
Vietnamese input still routes correctly.

**A lost-response retry could not collect its receipt.** The rate bucket was
consumed before the replay branch was reached, so each retry of a dropped
response spent a slot and the sixth attempt returned 429 instead of replaying,
stranding a capability that was already committed with a 24-hour TTL. The
service now recognises a clean replay on an unlocked peek and returns it without
touching the bucket; a conflicting body still pays for a slot, so the limiter
keeps gating new work. The peek runs on its own connection rather than nested
inside the case transaction, because the PostgreSQL pool is shared and nesting
could exhaust it.

**A corrected phone replayed silently.** The digest bound only whether a contact
was present, so retrying with a fixed typo returned the original grant and left
the dispatcher pointed at the old number. The keyed digest of the contact is now
bound, so an edited phone conflicts; the number itself never enters the digest
input.

**The entity guard could still leak a driver error.** `require_entities` took no
row lock, so a concurrent delete between the check and the insert produced the
`ForeignKeyViolation` the guard exists to convert. The read now takes
`FOR KEY SHARE`, the lock the foreign key would acquire anyway.

Verification after the fixes: the two new-file suites `29 passed` twice in a row;
the plan's GREEN command `37 passed`; the full case, schema, readiness and
database sweep `340 passed, 1 xfailed`; Ruff clean; `git diff --check` exit 0.

## Second independent review, and its three findings

A second cloud review over the same base returned three findings. Two were
accepted in full and one was accepted only in part.

**A signed-in reporter filing anonymously was locked out of their own receipt.**
`_commit_case` issued the receipt with `current_user_id=session_user_ref`, while
reporter privacy, identity assurance and party authority all read
`command.authenticated_user_ref`. A reporter who was signed in but deliberately
did not link the case therefore got a receipt bound to their account, and
`exchange_receipt` rejects a bound receipt presented without that account. After
logging out, from another device, or after clearing cookies, the capability was
unusable, and for an anonymous case the capability is the only way back in. The
receipt now follows the opt-in, and a regression test files while signed in with
no linkage and asserts the receipt subject is NULL, privacy stays anonymous and
no party authority is written.

**Reporter privacy fed the digest and nothing else.** The field was part of the
locked command signature but the stored value was re-derived from the session,
so two retries differing only in that field conflicted while producing identical
cases. Rather than drop a field the handoff pins, the service now uses the
reporter's stated choice, bounded to `anonymous` or `attributed`, and rejects
`attributed` without a session. Signing in still never forces attribution. One
earlier test asserted the old derivation and was updated to the corrected
contract.

**The English marker list repeated the substring mistake — partly.** `dying`
matched `studying` and `khan cap` matched `Khan Capital`, the same class of
defect the diacritic split had just fixed on the Vietnamese side. Folded markers
are now matched on word boundaries, which fixes both of those.

Accepted only in part: the review also listed `assault course training gym`,
`kidnap simulation drill` and `suicide squad film screening`. Word boundaries do
not help there, and neither does the fix the review proposed, because in those
strings the marker really is a standalone word. Removing the markers is the only
way to silence them, and that would trade a rare rejected venue-name correction
for a missed report of real harm. The markers stay, the deliberate choice is now
pinned by its own test, and the test expectations written from the review's
examples were corrected to what word boundaries can actually deliver rather than
left asserting a fix that does not exist.

Verification: the two create suites `30 passed` twice; the plan's GREEN command
`38 passed`; the full case, schema, readiness and database sweep
`353 passed, 1 xfailed`; Ruff clean; `git diff --check` exit 0.

## Owner disposition on the three deviations

The project owner reviewed and **approved all three deviations** recorded above
on 2026-08-18. They are no longer open questions:

1. `agent/cases/security.py` may carry `encrypt_private_payload` /
   `decrypt_private_payload` even though the task's file list did not name it.
   The envelope reuses the existing replay Fernet, so the locked HKDF salt list
   is unchanged, and the tagged envelope keeps a replay token from being read
   back through the private path.
2. `CORRECTABLE_FIELD_PATHS` stays in `agent/cases/service.py`. Promoting it into
   `config/case-service-policy.json` would change a locked policy structure and
   require a revision bump; that remains available as a later, deliberate change
   rather than a silent one.
3. The `require_entities` guard and the `correction_entity_unknown` (404) problem
   stay, so the real foreign key on `correction_items.entity_id` cannot leak a
   driver error to the transport layer.
