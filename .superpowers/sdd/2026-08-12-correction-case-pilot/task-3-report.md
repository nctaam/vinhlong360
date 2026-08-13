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
