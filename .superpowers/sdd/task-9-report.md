# Task 9 Report: Canonical Search, Truthful Pagination, Data Quality, and Cache Topology

## RED

- `python -m pytest tests/test_search_contract.py tests/test_pagination_truth.py -q`
- Initial collection failed as intended: `search_contract` and `database.normalize_entity`
  did not exist.
- After the contract skeleton, the only remaining red was the missing explicit
  zero-denominator quality status helper.

## GREEN

- Focused Task 9 suite: `122 passed` in 7.15s.
- Included canonical search/pagination tests, SQLite accent-insensitive filtering,
  knowledge regressions, LLM/semantic cache regressions, and geocode tests.
- Public API compatibility/integration suite: `128 passed, 1 warning`.
- Database regression suite: `206 passed, 1 xfailed`.
- Static verification: `py_compile`, `git diff --check`, and Ruff all passed.
- Data evidence: `scripts/validate_data.py --json` exited 0; `scripts/deep_audit.py --json`
  now exits 0 and emits a machine-readable report. The current catalog has 1,746
  entities, 12,060 relationships, 33 itineraries, and no relationship deletion
  candidates; five exact-normalized duplicate-name groups remain visible in the
  report for curation.

### Review remediation GREEN

- Review RED tests covered direct FastAPI `Query` defaults, the >500 full-catalog
  entity ranking path, zero-denominator quality metrics, semantic cache refresh,
  and concurrent cache manifest writes.
- Semantic-cache regression suite: `60 passed`.
- Search/pagination contract suite after remediation: `11 passed`.
- API/database compatibility slice: `21 passed, 1 warning`.
- The cache fix now separates genuine disk-loaded state from test/local-only state,
  merges concurrent puts, and carries explicit deletion tombstones through
  invalidation and TTL expiry so removed entries cannot be resurrected.

### Independent review findings (F-45, F-28, F-54, F-56, F-60, F-62)

- Added `tests/test_task9_review_fixes.py` with red/green regressions for zero-
  denominator completeness, bounded overall percentages, source-only SQLite
  search, missing-manifest semantic-cache refresh, geocode mtime refresh/metric,
  vector module identity, and stale-queue mutation.
- `python -m pytest -q tests/test_task9_review_fixes.py --basetemp=.tmp-task9-review-green2`
  -> `7 passed`.
- `python -m pytest -q agent/tests/test_geocode.py tests/test_semantic_cache.py tests/test_database_filters.py tests/test_search_contract.py tests/test_pagination_truth.py tests/test_task9_review_fixes.py --basetemp=.tmp-task9-review-suite1`
  -> `96 passed`.
- `python -m pytest -q agent/tests/test_admin_mutations.py -k 'stale or completeness' --basetemp=.tmp-task9-admin-suite1`
  -> `2 passed, 50 deselected, 1 warning`.
- `python scripts/validate_data.py --json` -> exit `0`; catalog `1746` entities,
  `12060` relationships, `33` itineraries.
- `python scripts/deep_audit.py --json` -> exit `0`; no relationship deletion
  candidates; five exact-normalized duplicate-name groups remain for curation.

## Changes

- Added `agent/search_contract.py` with NFKD accent folding, case/whitespace
  normalization, deterministic exact/prefix/name/summary/source ranking, complete
  filtered-relation pagination, and mandatory page truth fields.
- Routed public `/search`, entity-list search, and autocomplete ranking through the
  canonical scorer; public responses expose `offset`, `limit`, `truncated`, and
  `ranking_version`.
- Registered SQLite `f_unaccent` and normalized knowledge/cache/geocode text so
  SQLite and PostgreSQL search semantics agree.
- Added canonical `normalize_entity()` migration for legacy top-level `verifiedAt`
  values while preserving the nested field as the only public verification source.
- Added explicit quality metric status (`not_applicable` for 0/0) and JSON output to
  `deep_audit.py`.
- Fixed semantic-cache replacement document-frequency inflation and added a
  cross-process lock/merge path for semantic and geocode manifests with counters
  for replacements, duplicate writes, and prevented lost updates.

## Commit

- `0a2f8249 fix: make search data quality and pagination truthful`
- Review remediation commit: `fix: close search review findings`.

## Cross-worker re-review remediation

- PostgreSQL source search now casts JSONB to text before `lower()`/`f_unaccent()`;
  SQLite and PostgreSQL source-only search contracts are covered.
- Semantic cache manifests persist versioned tombstones, merge under the
  inter-process lock, reject stale same-key writes, and evict L1 entries when a
  worker observes an external invalidate or replacement.
- Geocode cache writes compare an immutable loaded snapshot with the locked
  manifest, preserve newer same-key worker values, and increment the existing
  lost-update metric when a conflict is prevented.
- RED/GREEN evidence: `python -m pytest -q tests/test_task9_review_fixes.py
  tests/test_database_filters_pg.py tests/test_semantic_cache.py
  agent/tests/test_geocode.py --basetemp=.tmp-task9-cross-final` -> `85 passed,
  8 skipped`; `py_compile`, Ruff, and `git diff --check` pass.

## PostgreSQL / remaining concerns

- The parent Task 8 disposable PostgreSQL proof owns the active local cluster; I did
  not attach to or mutate it. PostgreSQL-specific SQL filter coverage remains in
  `tests/test_database_filters_pg.py` and should be run by the parent once the
  disposable cluster is released or via its existing script.
- The full-catalog Python ranking intentionally materializes the filtered relation;
  for the current ~1.7k catalog this is bounded and truthful, but a much larger
  catalog should move ranking into a versioned SQL projection/search index.
- Public autocomplete keeps the established `db.search_entities` seam for backward
  compatibility and requests the catalog scan ceiling (`_FULL_SCAN_LIMIT`); it is
  still bounded if a future catalog exceeds that ceiling and should then expose a
  bounded-mode flag or move to the canonical relation API.
