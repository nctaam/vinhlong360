# Task 5 Fix Report

## Scope

Closed the remaining lifecycle review blockers across export, erasure, browser,
media, and scheduled cleanup. The final follow-up in this patch addresses the
legacy `/auth/export-data` compatibility payload:

- Page manifests now report the number of rows actually returned, excluding
  the `limit + 1` probe row used to detect continuation.
- Manifest continuation cursors are signed for the authenticated subject, so
  a cursor copied from `lifecycle_manifest["legacy"]` can be passed back to the
  endpoint and verified by the existing cursor provenance checks.
- Legacy payload slices and manifest metadata are built from the same bounded
  page contract.

The supporting P1 controls in the lifecycle modules are also covered by the
focused suite:

- External erasure adapters return explicit `unavailable`/`retained` outcomes;
  these outcomes are excluded from `ErasureReport.verified` instead of being
  treated as successful deletion.
- Browser deletion issues the complete shipped-key inventory (including the
  journey-thread key), and the Nuxt consumer removes each key once.
- Media deletion records an idempotent `(subject, object, generation)` receipt,
  serializes provider calls, runs object and CDN attempts independently, and
  keeps failed or unavailable receipts retryable/unverified.
- Scheduler expiry cleanup invokes the bounded `limit=500` worker under its
  process lease rather than issuing an unbounded delete.

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

## Final durability and inventory wave

- Added explicit export/erasure coverage for `event_rsvp`,
  `notification_preferences`, `comment_likes`, `user_hidden_posts`,
  `user_achievements`, `profile_views`, and the complete preferences and
  personalization family. Profile views are attributed to either participant.
- Analytics export and erase now normalize owners to the canonical
  `user:<id>` namespace.
- Browser clear proofs carry a unique `issuance_id` per request and are
  persisted in `browser_clear_instructions`; `get_browser_clear_instruction`
  retrieves proof after an in-process cache loss.
- Media deletion receipts persist the
  `(subject_id, object_key, generation)` tuple in SQLite and PostgreSQL,
  preserving terminal provider statuses across retries and workers. PostgreSQL
  deployments receive this through migration `085_lifecycle_durable_receipts.sql`.
- RED: the four focused durability/inventory tests failed before these changes;
  GREEN: `python -m pytest agent/tests/test_lifecycle_registry.py -q
  --basetemp=.tmp-task5-final-green2` -> `21 passed`.
