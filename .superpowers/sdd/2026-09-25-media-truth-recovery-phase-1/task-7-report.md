# Task 7 Report

Status: complete; review-only candidate staging is implemented. The plan is
`review_required`, has `mutationAllowed=false`, and uses
`targeted-media-v1`. No protected store is mutated by the builder or stager.

Implemented:

- deterministic Batch 21 scope validation and before-value mutations for the
  JSON and immutable SQLite source stores;
- canonical SQLite logical digests, expected candidate hashes/counts, and
  affected asset hashes;
- owned candidate staging at `candidate/vinhlong360.db`,
  `candidate/data.json`, `candidate/public/img/entities`, and
  `candidate/stage-result.json`;
- complete candidate asset-tree inventory with only `prov-1.webp` removed;
- protected-path and SQLite-sidecar refusals; and
- exact write-guard registration for the `_update_sqlite_entity` offline
  reconciliation boundary (the scanner discovers the nested helper, not the
  dispatcher).

Validation commands and outputs:

```text
PYTEST_DEBUG_TEMPROOT=C:\vlt python -m pytest -q tests/checks/test_build_media_truth_plan.py tests/checks/test_stage_data_reconciliation.py tests/test_entity_write_guard.py
27 passed in 117.79s

python -m ruff check scripts/checks/build_media_truth_plan.py scripts/checks/stage_data_reconciliation.py scripts/check_entity_write_paths.py tests/checks/test_build_media_truth_plan.py tests/checks/test_stage_data_reconciliation.py tests/test_entity_write_guard.py
All checks passed!

python -m py_compile scripts/checks/build_media_truth_plan.py scripts/checks/stage_data_reconciliation.py scripts/check_entity_write_paths.py tests/checks/test_build_media_truth_plan.py tests/checks/test_stage_data_reconciliation.py tests/test_entity_write_guard.py
passed

git diff --check -- <six scoped source/test files>
passed
```

The checked-in plan was generated twice with:

```text
python scripts/checks/build_media_truth_plan.py --output outputs/media-truth-plan-2026-09-25.json
python scripts/checks/build_media_truth_plan.py --output outputs/media-truth-plan-2026-09-25.json
```

Both runs produced SHA-256
`0d027436c730a8753b99a5956afeeac3bd815a3219ac1c9025346e4cf78a6ff2`.
Protected `agent/data/vinhlong360.db` and `web/data.json` hashes and UTC
mtimes were unchanged, and no SQLite sidecar was present.

The required pre-apply snapshot command was run:

```text
python scripts/backup_data.py --target local --out-dir .tmp/media-truth-backups-phase-1 --label before-media-truth-review --keep 50 --max-age-days 3650
[backup] -> .tmp/media-truth-backups-phase-1/20260929-054438-before-media-truth-review
[backup] copied: web/data.json, agent/data/vinhlong360.db
[backup] counts: {'entities': 1772, 'relationships': 13463, 'itineraries': 33}
```

Snapshot evidence:

- directory: `.tmp/media-truth-backups-phase-1/20260929-054438-before-media-truth-review`;
- manifest SHA-256: `2e13d7c88d52ed19c4dd8c6626aa9ea6711785ff98989e00d68b0848b4fd50bb`;
- backup JSON SHA-256: `8ac327de6c4f273c96efe99004f6a1858ba41af43799ebcdae5cd7f31316d92f`;
- backup SQLite SHA-256: `f686bdc1e35675d5543720efd1d67359851b29b6a713154a2613d78977cfe7de`;
- backup SQLite logical digest: `800c2c39644f78c676d08b09d84484b7f94d65173e8847c9456a2067069974d1`;
- `PRAGMA integrity_check`: `ok`;
- SQLite row counts (source and backup): entities `1772`, relationships `13337`,
  itineraries `33`; and
- JSON row counts (source and backup): entities `1772`, relationships `13463`,
  itineraries `33`.

Concern/ruling: the backup manifest's `counts` are intentionally derived from
`web/data.json` by `scripts/backup_data.py`, so its relationship count is
`13463`. Direct SQLite queries correctly report `13337` for both the protected
source and its backup. This is the pre-existing JSON/SQLite relationship drift
preserved by the targeted plan, not a backup corruption or copy mismatch; both
stores match their respective protected sources byte-for-byte/logically.
