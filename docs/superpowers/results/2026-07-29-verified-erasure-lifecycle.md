# Verified Erasure Lifecycle Result Evidence

> STATUS: complete - focused, real-PostgreSQL, lifecycle, scheduler, and hard gates pass; the repository-wide baseline remains incomplete under the documented outer timeout and is not reported as passing.
> Revision under test: `62c97fde7d796f30064c7599dea5547d245cceab`
> Date: 2026-07-30 (Asia/Bangkok)
> Scope: local implementation and verification only; no production deletion, deadline backfill, legacy scrub apply, deploy, push, secret change, or real-data mutation.

## Outcome

The Verified Erasure Lifecycle implementation is present through migration 073,
owner-write admission, external-store registry, quarantine/recovery, verified
hard-erasure orchestration, scheduler audit mode, guarded legacy scrub tooling,
and end-to-end evidence tests.

Focused lifecycle, scheduler, and real-PostgreSQL gates are green. The first
live PostgreSQL run exposed that completed-appeal erasure attempted to clear a
`NOT NULL` user-authored reason field. Migration 073 now makes that field
nullable, the regression test asserts the migrated catalog state, and the full
PostgreSQL matrix passes without skips.

The serial repository baseline still exceeds the bounded 330-second command
limit. That known closed-installer rehearsal debt is recorded exactly and is not
reported as passing.

The Runtime Trust Boundary result is already complete at
`docs/superpowers/results/2026-07-29-runtime-trust-boundary.md`; both approved
implementation plans are now locally complete. Production activation remains a
separate, explicitly unauthorized operation.

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
| Live PostgreSQL appeal-erasure correction | `3143ba7c` |
| Full live FK-catalog introspection | `62c97fde` |

Branch range: `82241b9a..62c97fde`.

## Verification Evidence

| Gate | Exact command | Result |
| --- | --- | --- |
| PostgreSQL/state/reference gate | `python -m pytest -q -rs agent/tests/test_erasure_state.py agent/tests/test_erasure_constraints_postgres.py agent/tests/test_structured_reference_cleanup.py agent/tests/test_quarantine.py agent/tests/test_recovery_deadline.py agent/tests/test_erasure_orchestrator_postgres.py agent/tests/test_erasure_lifecycle_postgres.py` | Exit `0`; `31 passed` in `10.88s`, no skips. Covers migration 073, all 45 live catalog actions, exact sentinel cleanup, final-transaction rollback, and row-lock lifecycle races. |
| Account control-plane PostgreSQL regression | `python -m pytest -q -rs agent/tests/test_account_control_plane_postgres.py` | Exit `0`; `9 passed` in `14.76s`, no skips. |
| Lifecycle integration gate | `python -m pytest -q -rs agent/tests/test_erasure_lifecycle_integration.py agent/tests/test_erasure_lifecycle_postgres.py agent/tests/test_erasure_constraints_postgres.py agent/tests/test_structured_reference_cleanup.py agent/tests/test_quarantine.py agent/tests/test_recovery_deadline.py agent/tests/test_erasure_orchestrator.py agent/tests/test_erasure_scheduler.py agent/tests/test_legacy_scrub.py agent/tests/test_erasure_source_guards.py` | Exit `0`; `67 passed` in `23.24s`, no skips. |
| Scheduler/registry/CLI gate | `python -m pytest -q -rs agent/tests/test_owner_write_gate.py agent/tests/test_data_lifecycle_registry.py agent/tests/test_erasure_orchestrator.py agent/tests/test_erasure_scheduler.py agent/tests/test_erasure_deadline_backfill.py agent/tests/test_erasure_cli.py agent/tests/test_legacy_scrub.py agent/tests/test_erasure_lifecycle_integration.py` | Exit `0`; `65 passed` in `15.66s`. |
| Diff whitespace | `git diff --check` | Exit `0`. |
| Full hard gate | `python scripts/checks/run_hard.py --all` | Exit `0`; `hard=0`, ratchet did not increase. The tool reported only lower-than-baseline soft counters and requested no write. |
| Collection audit | `python -m pytest --collect-only -q` | Exit `0`; `9396/9509` tests collected, `113 deselected`, in `17.58s`. |
| Repository baseline | `python -m pytest -q` with both disposable PostgreSQL URLs set | Harness exit `124` after `334.0s` (configured `330000ms` command limit) on revision `62c97fde`. `-q` emitted no case-level progress before timeout, so no last case is claimed; timed-out pytest PID `21316` was stopped and no full-baseline pass is claimed. |

## PostgreSQL Target Safety

The tests used only the purpose-named loopback database:

```text
postgresql://postgres@127.0.0.1:5432/vinhlong360_trust_erasure_test_20260730
```

PostgreSQL reported database `vinhlong360_trust_erasure_test_20260730`, role
`postgres`, and server `16.4`. Tests created random schema-isolated fixtures and
removed them after each run; the post-run matching schema count was `0`. No
production host, role, database, or data was contacted, and SQLite was not
substituted.

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

The live PostgreSQL migration test validated all 45 entries against
`pg_constraint`, recorded schema version 73, and passed exact sentinel cleanup.

## Acceptance Mapping

| Requirement | Evidence | Gate state |
| --- | --- | --- |
| Provider/log/sink privacy and feedback non-mutation | Runtime Trust Boundary result plus lifecycle source guards and owner-gate tests. | Green on focused evidence. |
| 30 days from committed deletion request | Policy authority, migration 072, transport tests, recovery deadline matrix. | Green. |
| Immediate quarantine and write blocking | `test_quarantine.py`, owner-write gate tests, and lifecycle integration matrix. | Green. |
| Verified hard erasure of registered personal/pseudonymous stores | Registry, orchestrator, residual-stop, retry, live rollback, and lifecycle tests. | Green. |
| Batch isolation | Orchestrator tests cover one failed user not poisoning later users. | Green. |
| Exact-deadline recovery/erasure linearization | Before/exact/after deadline tests, durable attempt marker, and real row-lock races. | Green. |
| PostgreSQL schema and structured references | Migration 073, live catalog introspection, and exact sentinel cleanup. | Green. |
| Aggregate retention | Registry, integration, and real PostgreSQL deletion assertions retain deidentified rollups. | Green. |
| Claim/appeal anonymization | Live migration and transaction tests cover pending delete, completed scrub, nullable actor fields, and nullable erased appeal reason. | Green. |
| Scrub safety and operational controls | Dry-run default, backup/digest gates, audit-only scheduler, and runbook tests. | Green; no apply performed. |
| No unauthorized mutation | No production URL, no `--apply`, no `--activate`, no deploy/push/secret operation. | Confirmed. |

## Activation State And Residual Debt

- `ERASURE_AUDIT_ONLY=True` and `ERASURE_ACTIVATION_ENABLED=False` remain the
  safe defaults; the scheduler and CLI cannot mutate without explicit gates.
- The legacy deadline backfill and legacy scrub remain dry-run/audit-only; no
  production or real-data invocation occurred.
- The full serial repository baseline remains incomplete under the 330-second
  outer limit because the existing closed-installer rehearsal dominates
  runtime. Focused and real-PostgreSQL evidence are green; the incomplete run is
  not relabeled as success.
- Completing this implementation plan does not approve production activation.
  Any scheduler activation, deadline backfill `--apply`, legacy scrub `--apply`,
  deployment, push, or real-data deletion still requires separate explicit
  authorization and the runbook backup gates.
