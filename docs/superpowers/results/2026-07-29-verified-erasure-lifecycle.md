# Verified Erasure Lifecycle Result Evidence

> STATUS: pending-final-gate - implementation and non-PostgreSQL evidence are complete locally, but the required disposable PostgreSQL target is not configured and the repository-wide baseline timed out.
> Revision under test: `59fdbe5750c7e25a96aa676ec3f8240a65cb8cb5`
> Date: 2026-07-30 (Asia/Bangkok)
> Scope: local implementation and verification only; no production deletion, deadline backfill, legacy scrub apply, deploy, push, secret change, or real-data mutation.

## Outcome

The Verified Erasure Lifecycle implementation is present through migration 073,
owner-write admission, external-store registry, quarantine/recovery, verified
hard-erasure orchestration, scheduler audit mode, guarded legacy scrub tooling,
and end-to-end evidence tests.

Focused lifecycle and scheduler gates are green. The final gate is not closed:
the PostgreSQL-only tests are skipped because both required connection settings
are unset, and the serial repository baseline exceeded the bounded 330-second
command limit. These are recorded as evidence debt, not as passing evidence.

The Runtime Trust Boundary result is already complete at
`docs/superpowers/results/2026-07-29-runtime-trust-boundary.md`; the shared
design therefore remains pending only on this Verified Erasure Lifecycle final
gate.

## Implementation Commits

| Area | Commits |
| --- | --- |
| Durable deadline and migration 072 | `aac58afc`, `ecd02919` |
| Owner write gate | `947e674e` |
| Lifecycle registry and bounded adapters | `0c353bc8`, `eb83ea62` |
| FK/reference policy and complexity hygiene | `9279ff30`, `fce74d6a` |
| Quarantine and recovery | `0a949544`, `29f5152b` |
| Verified hard-erasure orchestration | `5669aebd` |
| Scheduler audit mode and readiness | `5d142426` |
| Guarded legacy scrub tooling | `d8a7cfdf` |
| Subject-free lifecycle diagnostics | `61a118df` |
| Lifecycle integration evidence | `fe1645d4`, `59fdbe57` |

Branch range: `82241b9a..59fdbe57`.

## Verification Evidence

| Gate | Exact command | Result |
| --- | --- | --- |
| PostgreSQL/state/reference gate | `python -m pytest -q -rs agent/tests/test_erasure_state.py agent/tests/test_erasure_constraints_postgres.py agent/tests/test_structured_reference_cleanup.py agent/tests/test_quarantine.py agent/tests/test_recovery_deadline.py agent/tests/test_erasure_orchestrator_postgres.py agent/tests/test_erasure_lifecycle_postgres.py` | Exit `0`; `23 passed, 7 skipped` in `2.28s`. Every skip states `set TRUST_ERASURE_TEST_DATABASE_URL to a disposable PostgreSQL DB`; both `TRUST_ERASURE_TEST_DATABASE_URL` and `ACCOUNT_CONTROL_PLANE_TEST_DATABASE_URL` were empty. |
| Lifecycle integration gate | `python -m pytest -q agent/tests/test_erasure_lifecycle_integration.py agent/tests/test_erasure_lifecycle_postgres.py agent/tests/test_erasure_constraints_postgres.py agent/tests/test_structured_reference_cleanup.py agent/tests/test_quarantine.py agent/tests/test_recovery_deadline.py agent/tests/test_erasure_orchestrator.py agent/tests/test_erasure_scheduler.py agent/tests/test_legacy_scrub.py agent/tests/test_erasure_source_guards.py` | Exit `0`; `62 passed, 4 skipped` in `14.73s`. |
| Scheduler/registry/CLI gate | `python -m pytest -q agent/tests/test_owner_write_gate.py agent/tests/test_data_lifecycle_registry.py agent/tests/test_erasure_orchestrator.py agent/tests/test_erasure_scheduler.py agent/tests/test_erasure_deadline_backfill.py agent/tests/test_erasure_cli.py agent/tests/test_legacy_scrub.py agent/tests/test_erasure_lifecycle_integration.py` | Exit `0`; `65 passed` in `10.86s`. |
| Diff whitespace | `git diff --check` | Exit `0`. |
| Full hard gate | `python scripts/checks/run_hard.py --all` | Exit `0`; `hard=0`, ratchet did not increase. The tool reported only lower-than-baseline soft counters and requested no write. |
| Collection audit | `python -m pytest --collect-only -q` | Exit `0`; `9395/9508` tests collected, `113 deselected`, in `19.29s`. |
| Repository baseline | `python -m pytest -q` | Harness exit `124` after `334s` (configured `330000ms` command limit). `-q` emitted no case-level progress before timeout, so no last case is claimed; the orphaned timed-out pytest PID was stopped and no full-baseline pass is claimed. |

## PostgreSQL Target Safety

No PostgreSQL target was contacted. The required disposable settings were
empty at verification time:

```text
TRUST_ERASURE_TEST_DATABASE_URL=
ACCOUNT_CONTROL_PLANE_TEST_DATABASE_URL=
```

Consequently, migration catalog introspection, real FK action checks, row-lock
linearization, transaction rollback, and final database-residue assertions
remain required before activation. SQLite was not substituted.

## Registry And FK Evidence

The static registry snapshot reports 19 stores: 8 `personal`, 8
`pseudonymous`, 2 `aggregate`, and 1 `operational`. Five subject-linked stores
are marked for immediate quarantine: `hot_memory`, `exact_cache`,
`semantic_cache`, `semantic_leases`, and `pending_feedback_receipts`. Aggregate
and operational entries are explicitly `subject_linked=False`.

Migration 073 and the source registry contain 45 user foreign-key policies:

| Action | Count | Policy |
| --- | ---: | --- |
| `cascade` | 34 | User-owned rows are deleted with the account. |
| `set_null` | 11 | Actor-only references are nullable; actor identity is removed. |
| Special scrub | 2 entries | `entity_claims.claimant_id` and `moderation_appeals.user_id` apply the approved completed-workflow anonymization. |

The 45-entry catalog must still be validated against a live PostgreSQL
`pg_constraint` snapshot before the final gate can close.

## Acceptance Mapping

| Requirement | Evidence | Gate state |
| --- | --- | --- |
| Provider/log/sink privacy and feedback non-mutation | Runtime Trust Boundary result plus lifecycle source guards and owner-gate tests. | Green on focused evidence. |
| 30 days from committed deletion request | Policy authority, migration 072, transport tests, recovery deadline matrix. | Green on non-PostgreSQL evidence. |
| Immediate quarantine and write blocking | `test_quarantine.py`, owner-write gate tests, and lifecycle integration matrix. | Green on non-PostgreSQL evidence. |
| Verified hard erasure of registered personal/pseudonymous stores | Registry, orchestrator, residual-stop, retry, and lifecycle tests. | PostgreSQL residue proof pending. |
| Batch isolation | Orchestrator tests cover one failed user not poisoning later users. | Green on non-PostgreSQL evidence. |
| Exact-deadline recovery/erasure linearization | Before/exact/after deadline tests and durable attempt marker regression. | Real row-lock race proof pending. |
| PostgreSQL schema and structured references | Migration 073 and sentinel tests exist. | Live catalog/sentinel run pending. |
| Aggregate retention | Registry and integration assertions retain only deidentified aggregates. | PostgreSQL confirmation pending. |
| Claim/appeal anonymization | Structured cleanup policy and lifecycle assertions cover pending delete/completed scrub. | Live transaction proof pending. |
| Scrub safety and operational controls | Dry-run default, backup/digest gates, audit-only scheduler, and runbook tests. | Green; no apply performed. |
| No unauthorized mutation | No production URL, no `--apply`, no `--activate`, no deploy/push/secret operation. | Confirmed. |

## Activation State And Residual Debt

- `ERASURE_AUDIT_ONLY=True` and `ERASURE_ACTIVATION_ENABLED=False` remain the
  safe defaults; the scheduler and CLI cannot mutate without explicit gates.
- The legacy deadline backfill and legacy scrub remain dry-run/audit-only; no
  production or real-data invocation occurred.
- To close this result, provide a purpose-named disposable PostgreSQL database
  through `TRUST_ERASURE_TEST_DATABASE_URL` (and the control-plane URL when
  required), rerun the PostgreSQL gate and full lifecycle matrix, capture
  schema version 73 plus live constraint introspection, then rerun the full
  repository baseline with a limit that allows the known slow module to finish.
- Until those steps succeed, the plan and shared design must remain pending and
  no erasure activation gate may be approved.
