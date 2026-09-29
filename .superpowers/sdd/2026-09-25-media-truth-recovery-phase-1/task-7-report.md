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

## Fix Round 1

Review findings addressed in commit after `f834881b`:

- JSON mutation validation now scopes duplicate-location checks by
  `(recordType, index, recordId, field)`, allowing multiple exact fields on one
  entity while still rejecting duplicate writes to the same field/location.
  A regression calls the shared `_validated_mutations` validator on the
  generated 484-mutation plan.
- `affectedAssets[*].path` is now stable and repository-root-relative, for
  example `web-nuxt/public/img/entities/prov-1.webp`; no checkout-specific
  absolute path is serialized.
- SQLite logical digests sort relationship triples by `(from, to, type)` and a
  regression proves row insertion order does not change the digest.
- Staging captures source identity/hash snapshots and rechecks SQLite, JSON,
  and the complete asset-tree digest immediately before copying. It refuses
  symlink and non-empty output directories rather than reusing or overwriting
  an existing candidate tree.
- `image_caption` removal remains restricted to the reviewed false photographic
  shape (`image_type=documentary` and `is_verified_photo=true`); other caption
  fields are preserved. The current Batch 21 records match this reviewed shape.

The Task 5 shared attribute mutation helper supports strict absent-to-add
generation fields (`before=None`, exact `after`) for the two AI IDs; all other
before/after checks remain strict. The compatibility changes are committed in
`629929b1` together with the Task 7 fix-round code, and Task 7's regression and
staging run exercise them.

Fix-round validation:

```text
PYTEST_DEBUG_TEMPROOT=C:\vlt python -m pytest -q tests/checks/test_build_media_truth_plan.py tests/checks/test_stage_data_reconciliation.py tests/test_entity_write_guard.py tests/checks/test_apply_data_reconciliation.py
78 passed, 1 skipped in 146.58s (the symlink case is skipped when Windows privilege 1314 prevents creating a test symlink)

python -m ruff check scripts/checks/build_media_truth_plan.py scripts/checks/stage_data_reconciliation.py scripts/check_entity_write_paths.py tests/checks/test_build_media_truth_plan.py tests/checks/test_stage_data_reconciliation.py tests/test_entity_write_guard.py
All checks passed!

python -m py_compile scripts/checks/build_media_truth_plan.py scripts/checks/stage_data_reconciliation.py scripts/check_entity_write_paths.py tests/checks/test_build_media_truth_plan.py tests/checks/test_stage_data_reconciliation.py tests/test_entity_write_guard.py
passed
```

Fix-round post-checks:

```text
PYTEST_DEBUG_TEMPROOT=C:\vlt python -m pytest -q tests/checks/test_build_media_truth_plan.py tests/checks/test_stage_data_reconciliation.py tests/test_entity_write_guard.py tests/checks/test_apply_data_reconciliation.py
78 passed, 1 skipped in 146.07s

Direct R20.8 complexity check for the changed builder/stager modules
scripts/checks/build_media_truth_plan.py []
scripts/checks/stage_data_reconciliation.py []

python -m ruff check <Task 7 files plus scripts/checks/apply_data_reconciliation.py and Task 5 tests>
All checks passed!

python -m py_compile <same scoped Python files>
passed
```

The checked-in plan was regenerated after the fixes; its latest SHA-256 is
`aac5baec34c758e8b67f27ca943461c31d2d27bf661d4e8e013334892edcb37b`.
The generated plan contains 484 mutations and the shared validator returns
484 total / 245 JSON / 239 SQLite mutations. Source protected hashes and
mtimes remain unchanged; no source SQLite sidecar exists.
Post-commit HEAD verification (unique pytest temp root to avoid Windows cleanup races):

```text
PYTEST_DEBUG_TEMPROOT=C:\vlt_task7_final_full python -m pytest -q tests/checks/test_build_media_truth_plan.py tests/checks/test_stage_data_reconciliation.py tests/test_entity_write_guard.py tests/checks/test_apply_data_reconciliation.py
78 passed, 1 skipped in 156.03s
```

The isolated sidecar refusal test also passed with
`PYTEST_DEBUG_TEMPROOT=C:\vlt_task7_final` (`1 passed in 9.47s`). A prior run
using the shared `C:\vlt` temp root encountered Windows pytest cleanup races;
no product assertion failed, and the unique-root rerun is clean.

## Fix Round 2

Added a final `_ensure_no_sidecars(sqlite_input)` immediately before the
candidate DB copy. A deterministic `before_sqlite_copy` test hook creates a
late `-wal` sidecar after initial validation; staging refuses with
`StageError("SQLite sidecar present")` and removes the owned, unpublished
candidate directory. The report's Fix Round 1 wording now correctly states
that the shared apply-helper changes are committed in `629929b1`.

Fix-round checks:

```text
PYTEST_DEBUG_TEMPROOT=C:\vlt_task7_round2b python -m pytest -q tests/checks/test_stage_data_reconciliation.py::test_stage_refuses_late_sqlite_sidecar_before_copy tests/checks/test_stage_data_reconciliation.py::test_stage_creates_owned_candidate
2 passed in 43.90s

python -m ruff check <scoped Fix Round 2 files>
All checks passed!

python -m py_compile <scoped Fix Round 2 files>
passed

Direct R20.8: build_media_truth_plan.py [], stage_data_reconciliation.py []
git diff --check -- <scoped Fix Round 2 files>
passed
```
