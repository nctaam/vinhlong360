# Final Review Fix Wave Report

Date: 2026-09-30
Base review: `15d770f3`

## Changes

- Hardened evidence command validation with a finite classification vocabulary:
  `passed`, `passed_baseline`, and `passed_copy_only_rehearsal`.
- Bound every accepted classification to exit code `0` and require every
  `outputSha256` to be exactly 64 lowercase hexadecimal characters.
- Added negative coverage for non-zero exits with positive classifications,
  unknown classifications, and malformed output hashes, plus positive coverage
  for all documented passing classifications.
- Exact SQLite backup mode now stages JSON, SQLite, and the manifest in an
  owned temporary directory and publishes only after all work succeeds. Failed
  staging verifies the temporary directory identity before removal, so it
  removes only the owned temporary directory and leaves foreign output paths
  untouched.
- Added regression coverage for a byte-exact failure after JSON staging and a
  pre-existing foreign backup directory.

## Validation

All commands ran from the repository root. Exit codes are shown explicitly.

1. `python -m pytest -q tests/checks/test_build_media_truth_review.py tests/test_backup_data.py`
   - Exit code: `0`
   - Output: `73 passed, 2 skipped in 20.01s`
2. `python -m ruff check scripts/checks/build_media_truth_review.py tests/checks/test_build_media_truth_review.py scripts/backup_data.py tests/test_backup_data.py`
   - Exit code: `0`
   - Output: `All checks passed!`
3. `python -m py_compile scripts/checks/build_media_truth_review.py tests/checks/test_build_media_truth_review.py scripts/backup_data.py tests/test_backup_data.py`
   - Exit code: `0`
   - Output: none
4. Direct R20.8:
   `python -c "... ComplexityCheck(...).run(files=['scripts/checks/build_media_truth_review.py','scripts/backup_data.py']) ..."`
   - Exit code: `0`
   - Output: `{"check": "complexity", "count": 0, "level": "soft-ratchet", "rule": "R20.8", "violations": []}`
5. `git diff --check -- scripts/checks/build_media_truth_review.py tests/checks/test_build_media_truth_review.py scripts/backup_data.py tests/test_backup_data.py`
   - Exit code: `0`
   - Output: none
6. Protected hash and sidecar check:
   - Exit code: `0`
   - `agent/data/vinhlong360.db`: `ea83864990cf8455061b2436f072c097bc7011f56428c5ba3ba43bcd66fb78a4`
   - `web/data.json`: `8ac327de6c4f273c96efe99004f6a1858ba41af43799ebcdae5cd7f31316d92f`
   - Protected SQLite sidecars found: `0`

## Scoped diff

Only these four task files were changed by this fix wave:

- `scripts/checks/build_media_truth_review.py`
- `scripts/backup_data.py`
- `tests/checks/test_build_media_truth_review.py`
- `tests/test_backup_data.py`

Protected stores were not opened or mutated.
