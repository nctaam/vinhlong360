# NP-1.1 location remediation verification

> STATUS: focused verification complete; whole-branch review pending

Base: 2bca1dd7f3afce9ad47f70b51b815da62305e559

Head source: 5e1f74c7d4556ad5555706e59785da11fb825776 (captured with `git rev-parse HEAD`)

## Migration and PostgreSQL

- `python -m pytest -q agent/tests/test_database.py agent/tests/test_migration_chain.py agent/tests/test_migration_apply.py agent/tests/test_user_preferences.py agent/tests/test_location_resolver.py agent/tests/test_public_api.py agent/tests/test_auth_security_hardening.py` — PASS: 426 passed, 7 skipped, 1 xfailed, 1 warning; pytest 31.43s, wrapper elapsed 33.947s.
- `if ($env:PERSONALIZATION_EVENTS_TEST_DATABASE_URL) { python -m pytest -q agent/tests/test_personalization_events.py } else { Write-Output 'NOT RUN: PERSONALIZATION_EVENTS_TEST_DATABASE_URL is not configured' }` — NOT RUN: `PERSONALIZATION_EVENTS_TEST_DATABASE_URL` is not configured; no pass is claimed.
- `$env:LOCATION_REMEDIATION_TEST_DATABASE_URL = $env:MIGRATION_APPLY_TEST_DATABASE_URL; python -m pytest -q agent/tests/test_location_remediation_postgres.py agent/tests/test_migration_readiness_postgres.py` — PASS: 24 passed, 5 skipped; pytest 1.78s, wrapper elapsed 3.959s. The configured migration DSN was absent, so PostgreSQL-only cases skipped.

## Backend

- Focused backend command above completed with exit code 0: 426 passed, 7 skipped, 1 xfailed, 1 warning (33.947s wrapper).
- `python -m py_compile agent/user_preferences.py agent/location_resolver.py agent/public_api.py agent/personalization_events.py agent/scheduler.py` — PASS, exit 0, 0.396s.

## Frontend

- From `web-nuxt`, `npm test` (`vitest run`) — PASS: 42 test files, 1005 tests; Vitest duration 52.24s, wrapper elapsed 65.589s.
- From `web-nuxt`, `npm run typecheck` — PASS, exit 0, wrapper elapsed 56.491s.
- From `web-nuxt`, `npm run build` — PASS, exit 0, wrapper elapsed 219.491s; Nuxt/Nitro production build completed and launch-readiness manifest was generated for `5e1f74c7d4556ad5555706e59785da11fb825776`.
- Build warnings (non-fatal, no build errors): Nuxt module-preload sourcemap warning; Rollup chunks larger than 500 kB warning; Node `DEP0155` deprecated trailing-slash package export mapping warning.

## Privacy and scope

- Raw GPS/IP/token persistence gate: `rg -n "latitude|longitude|confirmation_token|location_confirmation_token|nonce" agent/migrations/073_location_preference_remediation.sql agent/user_preferences.py agent/scheduler.py` returned no matches (exit 1). Transient route/token handling remains confined to resolver/API paths and is not persisted or logged.
- Frontend behavior-test source inspection gate: `rg -n "readFileSync\\(|toContain\\(.*\\.vue|toContain\\(.*\\.ts" web-nuxt/tests/personalization-preferences.test.ts web-nuxt/tests/location-consent.test.ts` returned no matches (exit 1); tests are behavior-level.
- Manual precedence evidence is covered by passing tests including `test_manual_all_region_wins_over_valid_gps_confirmation`, `test_region_source_precedence_is_manual_gps_ip_default`, `test_manual_all_region_route_wins_over_resolver_confirmation`, and PostgreSQL migration cases for `canonical-manual` and `manual-all`.
- Interests/consent/workspace preservation evidence is covered by passing `test_quarantine_location_snapshot_drops_location_and_preserves_preferences`, `test_073_quarantines_legacy_location_without_erasing_personal_data`, and worker idempotence/non-location preservation tests. The migration matrix asserts explicit interests, consent history, reset timestamp, and saved workspace survive quarantine.
- Resolver token v2 evidence is covered by passing revision/user/TTL/one-use and no-nonce/raw-coordinate tests; no one-time token/nonce table, cache, column, or cleanup job is introduced.
- `git diff --check` — PASS, exit 0, 0.232s. Initial `git status --short --untracked-files=all` was clean.

## Limitations

- Official backend runner: not run; no fresh official-runner evidence is available in this environment.
- Real PostgreSQL personalization matrix: not run because `PERSONALIZATION_EVENTS_TEST_DATABASE_URL` is not configured.
- Migration/remediation PostgreSQL execution: the suite ran with 24 pass / 5 skip; configured DSN was absent, so live database cases were skipped.
- Browser/Stitch rendered verification: not in scope/not run for this final gate (Task 7 had a prior preview smoke pass, but authenticated reconfirm was not exercised).
- Whole-branch reviewer approval for `2bca1dd7f3afce9ad47f70b51b815da62305e559..HEAD`: not dispatched per instruction; branch is therefore not declared merge-ready. Known whole-tree hard-gate limitations remain R20.8 = 27 (baseline 14) and R20.4 missing/unreadable `coverage.json`; no baseline was changed.

## Rollout runbook

1. Disable `preference_ui_v1`, `PREFERENCE_PROFILE_V1` and `LOCATION_RESOLVER_V1`.
2. Drain in-flight preference/resolver mutations.
3. Apply migration 073 and verify readiness 73.
4. Deploy runtime guard, worker, token v2 and frontend state.
5. Enable `PREFERENCE_PROFILE_V1`, then `preference_ui_v1`.
6. Enable `LOCATION_RESOLVER_V1` last and monitor aggregate quarantine/stale counts.
7. On rollback, keep mutation flags off; never remove constraints, restore quarantined location or re-enable token v1.

## Staged gate

- Intended NP-1.1 verification path staged: `docs/superpowers/reports/2026-07-29-np1-1-location-remediation-verification.md` only; no package manifest/lock, homepage, public catalog, or unrelated migration staged.
- `git diff --cached --check` — PASS, exit 0.
- `python scripts/checks/run_hard.py --staged` — PASS: `hard=0`, ratchet did not increase; exit 0. The first attempt was correctly blocked by R60.1 until this report received its required `> STATUS` header; no production files were changed.
