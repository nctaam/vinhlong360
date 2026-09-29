# Task 9 Report

## Implemented

- Parameterized `generate_llms` and `export_frontend_data` to require explicit candidate inputs and write only to explicit output directories.
- Removed invented image credits and added image-type-aware media text.
- Added deterministic candidate bundle orchestration with byte-addressed SHA-256 manifest, review packets, ledger, and renderer registry copies.
- Replaced the hard-coded documentary assertion loop with a type-aware truth contract while preserving the existing governance test inventory and read-only database helper change.

## Verification

`$env:PYTEST_DEBUG_TEMPROOT='C:\vlt'; python -m pytest -q tests/test_generate_llms_media_truth.py tests/test_export_fe_data.py tests/checks/test_build_media_truth_artifacts.py`

```text
...............                                                          [100%]
15 passed in 2.22s
```

`python -m ruff check scripts/generate_llms_txt.py scripts/export_fe_data.py scripts/checks/build_media_truth_artifacts.py tests/test_generate_llms_media_truth.py tests/test_export_fe_data.py tests/checks/test_build_media_truth_artifacts.py`

```text
All checks passed!
```

`python -m py_compile scripts/generate_llms_txt.py scripts/export_fe_data.py scripts/checks/build_media_truth_artifacts.py scripts/checks/build_data_review_manifest.py scripts/checks/build_image_provenance_review.py`

```text
exit 0
```

`python -m scripts.checks.check_complexity`

```text
exit 0
```

`git diff --check -- scripts/generate_llms_txt.py scripts/export_fe_data.py scripts/checks/build_media_truth_artifacts.py tests/test_generate_llms_media_truth.py tests/test_export_fe_data.py tests/checks/test_build_media_truth_artifacts.py tests/llms-specification.test.ts tests/image-governance.test.ts`

```text
exit 0
```

Bundle generation was run twice against `.tmp/media-truth-stage-test-4/candidate` into `.tmp/task9-artifacts-fresh/first` and `.tmp/task9-artifacts-fresh/second`. Both manifests and all seven addressed artifact members compared byte-for-byte. The image provenance review contains the exact 40-record truth scope, including the controlled `prov-1` tombstone packet. The bundle includes the entity index, both LLM outputs, image provenance review, data review manifest, Batch 21 ledger, and renderer registry.

`npm --prefix web-nuxt run test:data -- tests/llms-specification.test.ts tests/image-governance.test.ts`

```text
1 file failed, 2 tests failed, 8 passed.
```

The failures are pre-existing live-fixture truth debt: an `https://example.test/...` image remains in the protected SQLite fixture, and `lang-nghe-san-xuat-chi-xo-dua-an-thanh` lacks complete rights evidence. No protected source or live output was modified.

Protected SHA-256 checks after generation:

- `agent/data/vinhlong360.db`: `EA83864990CF8455061B2436F072C097BC7011F56428C5BA3BA43BCD66FB78A4`
- `web/data.json`: `8AC327DE6C4F273C96EFE99004F6A1858BA41AF43799EBCDAE5CD7F31316D92F`

No SQLite `-wal`, `-shm`, or `-journal` sidecar was present after verification. No protected source, live public output, apply path, or publication path was modified.

## Fix Round 1

- Removed blanket Google Images/license claims and made summary counts include only records where `sourced_photo_evidence` returns a complete rights bundle.
- Made generator CLI inputs and outputs explicit; verified no-argument refusal and side-effect-free `--help` for both generators.
- Made candidate bundle review-manifest generation fail closed instead of emitting an empty findings manifest.
- Strengthened both LLM output tests for incomplete documentary fallback and removed the obsolete documentary ID inventory from governance tests.

Fix-round focused suite: `18 passed`. Ruff, `py_compile`, R20.8, and scoped diff checks passed. The relevant Vitest command still reports the two protected-fixture truth-debt failures (example.test media URL and one incomplete rights record); protected data was not changed. The generalized review-builder APIs required no edits because this round only closes the bundle orchestrator's fallback path.
