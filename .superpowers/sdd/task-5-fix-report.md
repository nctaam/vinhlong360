# Task 5 Fix Report

## Scope

Closed the remaining lifecycle export pagination blockers in the legacy
`/auth/export-data` compatibility payload:

- Page manifests now report the number of rows actually returned, excluding
  the `limit + 1` probe row used to detect continuation.
- Manifest continuation cursors are signed for the authenticated subject, so
  a cursor copied from `lifecycle_manifest["legacy"]` can be passed back to the
  endpoint and verified by the existing cursor provenance checks.
- Legacy payload slices and manifest metadata are built from the same bounded
  page contract.

## TDD Evidence

RED: added `test_legacy_manifest_counts_page_rows_and_signs_next_cursor` to
`agent/tests/test_lifecycle_registry.py`; before the helper was implemented,
the test failed because `_build_legacy_manifest` did not exist.

GREEN:

```text
python -m pytest agent/tests/test_lifecycle_registry.py -q --basetemp=.tmp-task5-fix-final
17 passed in 5.31s
```

Focused lifecycle coverage:

```text
python -m pytest agent/tests/test_lifecycle_registry.py agent/tests/test_data_lifecycle_registry.py agent/tests/test_external_store_erasure.py agent/tests/test_account_deletion_transport.py -q --basetemp=.tmp-task5-fix-final-focused
44 passed, 1 failed
```

The single failure is the pre-existing semantic-cache owner purge assertion in
`agent/tests/test_external_store_erasure.py::test_semantic_cache_and_lease_purge_are_owner_scoped`;
it is outside Task 5's lifecycle export changes and was not modified.

Static checks passed for the touched lifecycle modules:

```text
python -m py_compile agent/identity/api.py agent/control_plane/lifecycle.py agent/storage.py agent/scheduler.py
python -m ruff check agent/identity/api.py agent/control_plane/lifecycle.py agent/storage.py
git diff --check -- agent/identity/api.py agent/tests/test_lifecycle_registry.py
```

The scheduler-wide Ruff check still reports an existing unused
`moderation.log_moderation` import; that unrelated warning was left unchanged.

## Safety

No production database, object store, CDN, or paid provider was contacted.
