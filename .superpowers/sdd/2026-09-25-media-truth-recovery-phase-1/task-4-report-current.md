# Task 4 Report

## RED

Added manifest, generator, and R10.6 regression tests before implementation. The first focused run failed during collection with `ModuleNotFoundError: No module named 'agent.media_truth_manifest'`, confirming the production loader was absent.

## Implementation

- Added frozen `Batch21Truth` and public loaders in `agent/media_truth_manifest.py`.
- Added the authoritative 40-ID manifest and revision-bound subtractive revocation inventory.
- Reworked the Batch 21 generator to consume the manifest and emit 39 rows: 37 generated placeholders and 2 AI-generated rows with the required model/reference fields.
- Hardened all three R10.6 legacy compatibility inventories by subtracting the revocation set, including URL debt.
- Added focused manifest, generator determinism, and revocation tests.

## GREEN

Command:

```text
python -m pytest -q --basetemp=.tmp/media-task4-green agent/tests/test_media_truth_manifest.py tests/ops/test_generate_batch_21.py tests/checks/test_r10_6_legacy_inventory.py tests/checks/test_hard_checks.py
```

Result: `79 passed`.

Additional checks: `python -m ruff check` on all changed Python files passed; `python -m py_compile` passed for the changed modules; `git diff --check` passed for the task files.

## Determinism and Protected Stores

Running `python scripts/ops/generate_batch_21.py` twice produced byte-identical output SHA-256 `27040F86C2FA7F57CAAB9830CA622B7D329C60B686AA76C799B720F0DB188900`.

Protected-store checks observed: `agent/data/vinhlong360.db` SHA-256 `ea83864990cf8455061b2436f072c097bc7011f56428c5ba3ba43bcd66fb78a4`, `web/data.json` SHA-256 `8ac327de6c4f273c96efe99004f6a1858ba41af43799ebcdae5cd7f31316d92f`; no apply or write operation targeted either file. SQLite sidecar was not invoked or modified by the generator/tests.

## Concerns

- The standalone `ruff` command is not installed; the bundled `python -m ruff` module was used successfully.
- `prov-1` remains an external owner-evidence blocker and is intentionally not given provenance.
- Existing unrelated dirty changes remain in overlapping check/test files and were preserved.

## Determinism Correction (Controller Verification)

On 2026-09-29, the controller reran `python scripts/ops/generate_batch_21.py` twice and observed byte-identical SHA-256 `B2B3B2E7EEC419BD631F61481BA0BEA1C6C5CCC9A51C5E57F6A343C788CB5DC4`. This supersedes the earlier local hash recorded above; both runs remain deterministic.

## Round 1 Fix

Added strict manifest validation for exact keys, frozen metadata, list/string types, 1/2/37 partition counts, sorted uniqueness, disjointness, and total cardinality. RED coverage demonstrated that an extra-key manifest was previously accepted. Corrected the authoritative placeholder ID to the required `ba-nhi-bun-bo-hue-vinh-long-vinh-long` spelling in the manifest, revocation inventory, and regenerated ledger.

Round 1 focused GREEN: `17 passed`; `python -m ruff check`, `py_compile`, and `git diff --check` passed for the changed validation/test files.
