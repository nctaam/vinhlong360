# Task 3 Race Hardening Report

## Scope

Fixture-only Phase B apply/recovery hardening. Protected live stores were not used
as apply inputs and were not modified.

## RED

Added `test_recovery_refuses_external_json_edit_after_publication_boundary` to
model publication succeeding, followed by a non-cooperating external JSON edit
before the apply failure is surfaced.

Command:

```text
python -m pytest -q tests/checks/test_apply_data_reconciliation.py::test_recovery_refuses_external_json_edit_after_publication_boundary --basetemp=.tmp/task3-red
```

Output (expected failure before the production change):

```text
F                                                                        [100%]
...
E       Failed: DID NOT RAISE ApplyError
1 failed in 1.99s
```

The failure demonstrated that recovery unconditionally restored the JSON target
and removed the journal after the external edit.

## Implementation

- Added `_verify_recovery_json_ownership` in `scripts/checks/apply_data_reconciliation.py`.
- Recovery now permits restoration only when the current JSON SHA-256 matches the
  journaled pre-apply hash or the staged hash representing the known published
  state.
- For the pre-apply branch, the current device/inode/size must also match the
  journaled `beforeIdentity`; the staged published branch intentionally uses its
  durable hash because its post-`os.replace` identity is not recorded at the
  crash boundary.
- A mismatch (or unreadable target) fails closed with
  `ApplyError("JSON target ownership cannot be verified")`; recovery does not call
  the unconditional restore path, so external bytes and the journal remain intact.
- The helper documents the guarantee boundary: the shared advisory lock protects
  cooperating writers, while a non-cooperating writer may still race after the
  check; this is not portable cross-process compare-and-swap.
- Updated the pre-publication external-edit fixture contract to expect refusal,
  preserved external bytes, and a retained journal.

## GREEN

Focused apply/recovery tests:

```text
python -m pytest -q tests/checks/test_apply_data_reconciliation.py --basetemp=.tmp/task3-focused-2
```

```text
.............................                                            [100%]
29 passed in 3.26s
```

Adjacent journal recovery tests:

```text
python -m pytest -q tests/checks/test_apply_data_reconciliation.py tests/checks/test_reconciliation_journal.py --basetemp=.tmp/task3-all-recovery
```

```text
....................................s...                                 [100%]
39 passed, 1 skipped in 4.31s
```

## Static validation

```text
python -m ruff check scripts/checks/apply_data_reconciliation.py tests/checks/test_apply_data_reconciliation.py
All checks passed!

python -m py_compile scripts/checks/apply_data_reconciliation.py tests/checks/test_apply_data_reconciliation.py
(no output; exit code 0)
```

## Protected-store verification

Before and after validation, the following remained identical:

```text
agent/data/vinhlong360.db|sha256=ea83864990cf8455061b2436f072c097bc7011f56428c5ba3ba43bcd66fb78a4|length=46522368|mtime=2026-09-23T08:49:08.6964714Z
agent/data/vinhlong360.db-wal|absent
agent/data/vinhlong360.db-shm|absent
agent/data/vinhlong360.db-journal|absent
web/data.json|sha256=8ac327de6c4f273c96efe99004f6a1858ba41af43799ebcdae5cd7f31316d92f|length=8236562|mtime=2026-09-20T11:27:40.3820928Z
web/data.json-wal|absent
web/data.json-shm|absent
web/data.json-journal|absent
```

No live apply command was run.

## Residual concern

The ownership check and restore are not an operating-system compare-and-swap.
An uncooperative writer can still modify the target after validation and before
restore; the portable behavior is therefore fail-closed validation under the
shared lock, not an impossible cross-process guarantee.
