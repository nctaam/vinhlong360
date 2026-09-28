# Task 6 Report

Status: complete.

Implemented no-overwrite JSON publication and recoverable capture/rollback artifacts. Candidate JSON is staged beside the JSON target, journal state records candidate/capture/published identities and hashes, and recovery preserves foreign target or capture bytes before restoring the verified backup. Recovery now refuses SQLite sidecars before consuming JSON artifacts, including late sidecars after the completion journal boundary.

Validation:

- `PYTEST_DEBUG_TEMPROOT=C:\\vlt python -m pytest -q tests/checks/test_apply_data_reconciliation.py tests/checks/test_reconciliation_journal.py` — 48 passed, 1 skipped.
- `python -m ruff check scripts/checks/apply_data_reconciliation.py scripts/checks/reconciliation_journal.py tests/checks/test_apply_data_reconciliation.py tests/checks/test_reconciliation_journal.py` — passed.
- `python -m py_compile scripts/checks/apply_data_reconciliation.py scripts/checks/reconciliation_journal.py` — passed.

Note: repository-wide `git diff --check` remains noisy because unrelated pre-existing dirty files contain trailing whitespace; no unrelated files were staged.

## Round 1 Fixes

- Replaced capture hard-link/unlink with atomic rename ownership transfer; foreign replacement bytes are never destructively unlinked.
- Added and exercised hooks for `before_capture`, `after_capture`, `before_publish`, `after_publish`, and `before_rollback_capture`.
- Allowed legacy v1 `stagedPath` artifacts in the journal directory while retaining scope escape rejection for all other artifacts.
- Reduced all changed functions to R20.8 complexity <=12; direct checker reports zero violations.
- Added journal regressions for legacy staged paths, captured foreign bytes, sidecar refusal, and candidate cleanup after recovery.

Round 1 validation outputs:

```text
PYTEST_DEBUG_TEMPROOT=C:\\vlt python -m pytest -q tests/checks/test_apply_data_reconciliation.py tests/checks/test_reconciliation_journal.py
55 passed, 1 skipped in 4.82s

python -m ruff check scripts/checks/apply_data_reconciliation.py scripts/checks/reconciliation_journal.py tests/checks/test_apply_data_reconciliation.py tests/checks/test_reconciliation_journal.py
All checks passed!

R20.8 direct ComplexityCheck on both changed modules
count: 0
violations: []

python -m py_compile scripts/checks/apply_data_reconciliation.py scripts/checks/reconciliation_journal.py
passed

git diff --check -- <four scoped files>
passed
```
