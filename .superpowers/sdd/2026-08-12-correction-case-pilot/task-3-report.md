# Task 3 Report: Correction Case Pure Policy

## Status
DONE_WITH_CONCERNS. The pure, deterministic correction-case policy layer is committed as `26c99baf` and verified.

## Files
- Modified: `agent/cases/domain.py`
- Added: `agent/cases/transitions.py`, `agent/cases/queue_policy.py`
- Added tests: `agent/tests/test_case_transitions.py`, `agent/tests/test_case_properties.py`, `agent/tests/test_case_queue_policy.py`, `agent/tests/test_case_domain.py`

## RED Evidence
Command:
```powershell
python -m pytest -q agent/tests/test_case_transitions.py agent/tests/test_case_properties.py agent/tests/test_case_queue_policy.py
```
Output: collection failed with three `ImportError`s for absent Task 3 contracts (`CorrectionItem`, `PromiseClock`) and absent policy modules. This demonstrated the expected missing behavior before implementation.

## GREEN Evidence
- `python -m pytest -q agent/tests/test_case_transitions.py agent/tests/test_case_properties.py agent/tests/test_case_queue_policy.py agent/tests/test_case_domain.py agent/tests/test_domain.py agent/tests/test_case_policy.py agent/tests/test_case_schema_postgres.py` -> `44 passed, 8 skipped`.
- `python -m ruff check ...touched Task 3 Python files...` -> `All checks passed!`.
- `git diff --check` -> exit 0.
- `python scripts/checks/run_hard.py --staged` -> `hard=0, ratchet kh?ng t?ng`.
- `python scripts/checks/run_hard.py --all` was attempted before staging and failed on pre-existing/full-repository counters: R20.8 complexity `41 > 36` (the new transitions validation initially contributed one and was refactored out), and R20.4 coverage artifact missing `1 > 0`. The final touched module is absent from complexity violations; no claim of a full-repository gate pass is made.

## Design Decisions
- Frozen domain drafts model correction items, promise clocks, and linked review statuses without I/O, wall-clock reads, mutation, or generated identifiers.
- All accepted transitions return a replacement snapshot with exactly one revision increment plus immutable audit-transition metadata from the actor context.
- Closed snapshots reject every command. Review relation is derived solely from links, never written as a terminal disposition.
- Waiting-on-requester requires a concrete request, safe requester-facing message, requester actor, evidence reference, and next review timestamp. Promise health evaluates original timestamps; no waiting branch changes due lineage.
- Corrected closure requires fulfillment plus verified publication for every accepted public-change item. Publication/rollback errors derive recovery/escalation work rather than a terminal case outcome.
- Queue priority uses ascending `(emergency, promise health, risk, ready_at, received_at)`, precisely implementing the specified precedence. R2 accepts E3/E4 authoritative evidence or derives independent review; R3 derives separate maker, truth-review, and publication-review work. Evidence suppliers are recused from independent review work.

## Spec Self-Review
- Section 6: closed immutability, state dimensions, waiting requirements, promise lineage, and derived review relation checked.
- Section 9: field-level correction data, evidence/risk escalation, and corrected-only-after-publication guard checked.
- Section 11: deterministic priority, R0/R1/R2/R3 derivation, maker-checker, and evidence-supplier recusal checked.
- Section 12: missing owner, promise risk/breach, R2/R3 conflict, publication/rollback, and privacy/security/safety escalation coverage checked.

## Commit
`26c99baf feat: enforce correction case policy`.

## Concerns
- `run_hard --all` cannot pass in this worktree without a fresh coverage artifact and baseline-wide complexity remediation. This Task 3 scope does not alter coverage infrastructure or unrelated legacy complexity. The staged R20.7 gate passes.

## Fix round 1

### Review Verification and RED
- Verified every Critical/Important review finding against sections 6, 9, 11, and 12 plus the Task 3 brief. The initial pure layer did not persist waiting context, guarded only `corrected` closure, used enum identity without boundary validation, had no phase graph, ignored clock lineage/`now` and R1 policy, and represented R3 independence only as a supplier recusal.
- Added focused tests first. `python -m pytest -q agent/tests/test_case_transitions.py agent/tests/test_case_properties.py agent/tests/test_case_queue_policy.py` produced 14 expected failures: missing waiting state, terminal-publication bypasses, deserialized string acceptance, illegal phase acceptance, absent clock lineage, ignored R1 policy, and missing R3 work relationship metadata. Hypothesis import then failed because it is not installed; deterministic Cartesian generation replaces it without adding a dependency.

### Changes
- `WaitingContext` is immutable and carried by both the replacement snapshot and immutable transition draft. It records requester-safe request copy, concrete requester actor/reference, evidence reference, next review, and wait start.
- `CaseSnapshot` carries immutable original `PromiseClock` tuples. Queue derivation evaluates all clocks with explicit `now`, retains due timestamps, and escalates the most severe health without changing wait lineage.
- Transition boundaries fail closed for deserialized/invalid enum values and invalid correction item values. An explicit, monotonic phase graph permits same-phase orthogonal updates and rejects skips/backward moves; closed snapshots remain immutable.
- Every terminal transition rejects unresolved accepted public changes (unverified, publication failed, or rollback failed), preventing alternate outcomes from bypassing fulfillment/recovery. A non-public/no-action terminal result remains valid when no such unresolved accepted change exists.
- R1 now derives from the validated `risk_registry.R1.independent_review` field; the default policy yields a decision maker and an injected validated policy view yields independent review. E3/E4 remains the narrow authoritative-evidence inference for R2 based on the existing evidence ladder; the Task 1 policy does not define a broader evidence authority field.
- R3 drafts include deterministic work identities and `independent_of_work_refs`; independent reviewers also carry evidence-supplier recusal and explicit independent-review requirement. Lease-expiry/abandonment has no Task 3 immutable input, so is deferred to a later work/lease state layer. Package exports remain deferred because Task 4 imports domain modules directly and no current downstream import needs the extra package surface.

### GREEN and Self-Review
- `python -m pytest -q agent/tests/test_case_transitions.py agent/tests/test_case_properties.py agent/tests/test_case_queue_policy.py agent/tests/test_case_domain.py agent/tests/test_domain.py agent/tests/test_case_policy.py agent/tests/test_case_schema_postgres.py` -> `202 passed, 8 skipped`.
- Touched-file Ruff, `git diff --check`, and focused R20.8 complexity check pass; no touched policy function exceeds the complexity ratchet.
- Rechecked all terminal paths, waiting persistence/clock lineage, public-change recovery, runtime validation, phase moves, R1/R2/R3 work derivation, and deterministic property coverage against sections 6, 9, 11, and 12.

### Commit and Remaining Concern
- This round's scoped commit follows this report update.
- The original repository-wide `run_hard --all` concern remains: it needs a fresh coverage artifact and has unrelated legacy complexity baseline debt. The staged R20.7 gate is run after staging this round.

## Fix round 2

### RED and Decisions
- Focused RED tests exposed terminal snapshots retaining requester-waiting state, unchecked nested channel/clock/time values, blank work identities across R0-R2, and duplicate item ID collisions. The focused RED command reported 18 failures after correcting a missing test import.
- The R3 reviewer premise was narrowed to the written rule: section 11.3 excludes an evidence supplier from an independence-required review; it does not exclude that actor from decision making. The policy retains supplier eligibility for maker work while review drafts explicitly forbid the supplier and require independence from the maker identity.

### Changes and GREEN
- Closed transitions normalize activity to locked-vocabulary `active` and clear wait context; leaving waiting does likewise.
- Nested actor channel, promise health/timestamps, explicit `now`, snapshot timestamp ordering, item revision values, and requester next-review ordering fail closed. Clock comparisons only run after timezone-aware validation.
- All work drafts gain a deterministic nonblank identity; duplicate item IDs fail closed before derivation. Maker-review references point to real identities.
- Deterministic Cartesian tests cover all risk/evidence combinations, identity uniqueness, duplicate IDs, nested malformed values, terminal/wait activity normalization, and separation metadata.
- Focused Task 3 queue/transition tests -> `51 passed` after implementation. Final regression/gate evidence is recorded by the fix commit workflow.

### Remaining Concern
- As in earlier rounds, `run_hard --all` depends on a fresh repository coverage artifact and unrelated legacy complexity baseline. The staged R20.7 gate is required and run for this round.

## Fix round 3

### RED and Scope
- Focused queue/transition RED confirmed raw malformed inputs could reach queue dereferences, while special/duplicate IDs could make work identities ambiguous. The correction stays limited to shared pure boundary and temporal validation.
- The earlier concern is corrected: `PromiseClock.observed_at` after `due_at` is valid; it represents a breached promise. Validation requires `started_at <= observed_at <= now`, not `observed_at <= due_at`.

### Changes
- Added a small shared `cases.validation` layer for stable input rejection in both transition and queue entry points. It validates object/container types before dereference, exact consumed enum/bool/int fields, identifier safety, policy fields used for R1, and aware time lineage.
- Snapshot validation now enforces create/update/close phase coherence; clock validation permits post-due observations while preserving original due time. Queue converts malformed entry inputs into `QueuePolicyRejected` code strings rather than raw Python errors.
- Added deterministic malformed queue matrices, policy/clock/now variants, safe identifier checks, and an explicit post-due observation regression. R3 supplier/maker eligibility remains unchanged: the spec restricts suppliers from independent reviews, which the current metadata and tests enforce.

### GREEN and Concern
- Task 3 plus Task 1 regression suite -> `238 passed, 8 skipped`; touched-file Ruff and `git diff --check` pass. The staged R20.7 gate follows staging this report.
- `run_hard --all` remains outside this fix scope because it needs a fresh coverage artifact and unrelated legacy complexity remediation.
