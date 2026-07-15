# Entity Published-Status Migration Runbook

> STATUS: active safety runbook; Stage A only is complete when its verification gate passes; Stage B, Stage C, rollback, deployment, and indexing changes require their own authorization.

## Safety boundary

- This runbook is PostgreSQL-only. `scripts/migrate_entity_status.py` must refuse every target except `pg` and must use an explicitly named connection environment other than `DATABASE_URL`.
- Stage A changes code, tests, and this documentation only. It does not connect to a project database, create a production backup or plan, mutate data, deploy, or change indexing.
- Stage B is backup plus immutable plan generation only. It requires separately supplied PostgreSQL target context and stops before apply.
- Stage C is the only logical apply stage. It requires separate Stage C authorization tied to reviewed immutable evidence.
- Rollback is a separate incident action with separate authorization. It is not an automatic continuation of Stage C.
- Do not import web/data.json, write local SQLite first, reconcile exports, deploy, or infer launch completion from this migration.
- Do not mutate local data, `web/data.json`, `agent/data/vinhlong360.db`, noindex configuration, or deployment state in any Stage A command.
- Global noindex remains enabled by default in `web-nuxt/nuxt.config.ts`. The authoritative middleware response remains `X-Robots-Tag: noindex, follow` in `web-nuxt/server/middleware/noindex.ts`.

## Stage A evidence

Stage A is repository-only evidence. Run the focused suite serially, then the default suite, static checks, the optional disposable PostgreSQL integration, and repository checks. Never substitute a production URL for the integration-test variable.

```powershell
python -m pytest agent/tests/test_index_policy.py agent/tests/test_publication_status.py agent/tests/test_database.py agent/tests/test_admin_mutations.py agent/tests/test_kb_curation.py agent/tests/test_seo.py agent/tests/test_seo_structured.py tests/checks/test_hard_checks.py tests/test_export_data.py tests/test_postgres_target.py tests/test_backup_data.py tests/test_migrate_entity_status.py tests/test_migrate_entity_status_postgres.py tests/test_entity_status_migration_guardrails.py -q
python -m pytest -q
python -m ruff check agent/public_entity_types.py agent/publication_status.py agent/index_policy.py agent/launch_evidence.py agent/database.py scripts/postgres_target.py scripts/backup_data.py scripts/migrate_entity_status.py scripts/checks/check_data_schema.py tests/test_postgres_target.py tests/test_backup_data.py tests/test_migrate_entity_status.py tests/test_migrate_entity_status_postgres.py tests/test_entity_status_migration_guardrails.py
python -m pytest tests/test_migrate_entity_status_postgres.py -q -m entity_status_postgres
python -m ruff check agent/public_entity_types.py agent/publication_status.py agent/index_policy.py agent/launch_evidence.py agent/database.py scripts/postgres_target.py scripts/backup_data.py scripts/migrate_entity_status.py scripts/checks/check_data_schema.py tests/test_postgres_target.py tests/test_backup_data.py tests/test_migrate_entity_status.py tests/test_migrate_entity_status_postgres.py tests/test_entity_status_migration_guardrails.py --select C901 --config lint.mccabe.max-complexity=12
python -c "from scripts.checks import common; from scripts.checks.check_complexity import ComplexityCheck; files=['agent/public_entity_types.py','agent/publication_status.py','agent/index_policy.py','agent/launch_evidence.py','agent/database.py','scripts/postgres_target.py','scripts/backup_data.py','scripts/migrate_entity_status.py','scripts/checks/check_data_schema.py']; result=ComplexityCheck().run(files=files); baseline=common.load_baseline(); print({'count': result['count'], 'baseline': baseline.get(result['rule'], 0), 'violations': result['violations']}); raise SystemExit(1 if result['count'] > baseline.get(result['rule'], 0) else 0)"
git diff --check
git status --short
```

Stage A acceptance requires all non-optional commands to exit zero. The PostgreSQL integration must pass against its disposable target or safely skip when `ENTITY_STATUS_TEST_DATABASE_URL` is absent. Confirm that the repository diff contains only this runbook and its guard test before commit. Record any unavailable executable without attempting installation.

Stage A workstation capability record for 2026-07-15:

- Docker executable: unavailable.
- Nginx executable: unavailable.
- No installation was attempted.

Recorded Task 10 Stage A verification on 2026-07-15:

- The guard test first failed with `1 failed, 2 passed` because this runbook did not exist, then passed with `3 passed` after the runbook was added.
- The focused serial suite completed with `802 passed, 8 skipped, 2 deselected, 1 xfailed`.
- The default suite completed with `6871 passed, 48 skipped, 80 deselected, 1 xfailed`.
- The explicit integration command completed with `2 skipped because no disposable PostgreSQL target was supplied` through `ENTITY_STATUS_TEST_DATABASE_URL`.
- Ruff and Ruff C901 at the repository complexity threshold of 12 both exited zero. The scoped custom complexity result remained `3` against baseline `3`, so the ratchet did not increase.
- `web/data.json` SHA-256 was `7d20a0442129ae650c168225d3a6d4e0c7a96797ba8e3b003f3b61b76f493418` before and after the focused suite.
- `agent/data/vinhlong360.db` SHA-256 was `3c9c1235e2c32409df52bcf60d115515e292fbaf18d0b1aaf912a9e843847c1f` before and after the focused suite.
- No production database, plan, backup, export, deploy, or local data mutation command was run during Stage A.

Stop after the Stage A commit. Stage A completion is not authorization for Stage B or Stage C.

## Stage B: backup and plan

Prerequisite: the owner supplies the exact name of a PostgreSQL connection environment for the intended target. The environment name must not be `DATABASE_URL`. Use new, empty evidence paths. Do not use repository defaults or infer a target from local files.

```powershell
python scripts/backup_data.py --target pg --database-url-env <OWNER_SUPPLIED_ENV> --out-dir <NEW_BACKUP_ROOT>
python scripts/migrate_entity_status.py plan --target pg --database-url-env <OWNER_SUPPLIED_ENV> --policy published-v1 --report-out <NEW_PLAN_PATH>
```

These commands are the entire Stage B write boundary: they may create only the new PostgreSQL backup directory and new plan report. They must not apply entity changes.

Review and independently record all of the following before requesting Stage C:

- exact target fingerprint and database identity;
- schema fingerprint and required entity columns;
- every candidate ID, candidate count, and candidate ID hash;
- every exclusion count, reviewed exclusion rule, and status groups;
- expected before/after status counts;
- backup manifest SHA-256, artifact SHA-256, backup age, tool versions, restore listing validation, and target match;
- plan SHA-256, canonical bytes, policy revision, source revision, and freshness window;
- unchanged global noindex default and live/source evidence for `X-Robots-Tag: noindex, follow`.

Stop if any value is missing, unexplained, stale, inconsistent, or points at an unexpected target. Stage B authorization permits backup and plan only; it does not authorize Stage C.

## Stage C: apply after separate authorization

The owner authorization record must name the exact target fingerprint, plan SHA-256, backup manifest SHA-256, candidate count, and candidate ID hash reviewed in Stage B. Any changed byte, regenerated artifact, changed count/hash, stale plan/backup, or target/schema drift invalidates that authorization.

Run exactly one apply command with new report output:

```powershell
python scripts/migrate_entity_status.py apply --target pg --database-url-env <OWNER_SUPPLIED_ENV> --plan <PLAN_PATH> --backup-manifest <BACKUP_MANIFEST> --confirm-target <AUTHORIZED_TARGET_FINGERPRINT> --confirm-plan-sha256 <AUTHORIZED_PLAN_SHA256> --confirm-backup-manifest-sha256 <AUTHORIZED_BACKUP_MANIFEST_SHA256> --report-out <NEW_APPLY_REPORT>
```

Require result `applied`, exact candidate ownership, exact expected counts, and an immutable report SHA-256. Abort on any refusal; do not weaken checks or retry with changed evidence.

Re-run the same authorized apply inputs once with a different, new report path. The recovery report must say `already-applied`, `recovery_ready=true`, and `recovery_contract=apply-audit-exact-v1`. Verify zero status writes and zero audit writes on this rerun. Any other outcome is drift or an incomplete recovery contract and requires an immediate stop.

## Post-apply DB export artifact

Only after a successful Stage C apply and recovery rerun, create a post-apply DB export artifact at a new, untracked path. `scripts/export_data.py` supports only `--dry-run` and `--out`; it reads the backend through `DATABASE_URL`, so temporarily copy the already authorized named PostgreSQL URL into that variable for this isolated command block. Do not use the default output.

```powershell
$previousDatabaseUrl = $env:DATABASE_URL
try {
    $env:DATABASE_URL = (Get-Item "Env:<OWNER_SUPPLIED_ENV>").Value
    python scripts/export_data.py --dry-run --out <NEW_POST_APPLY_EXPORT_PATH>
    python scripts/export_data.py --out <NEW_POST_APPLY_EXPORT_PATH>
}
finally {
    if ($null -eq $previousDatabaseUrl) {
        Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
    }
    else {
        $env:DATABASE_URL = $previousDatabaseUrl
    }
}
```

Record the export SHA-256, file size, entity/relationship/itinerary counts, authorized target fingerprint, apply report SHA-256, and output path in Stage C evidence. Do not overwrite or edit tracked `web/data.json`. Reconciliation into tracked web/data.json or local SQLite is a separate reviewed task. The export artifact is evidence, not an instruction to import it anywhere.

## Rollback

Rollback requires a separate owner decision naming the exact target fingerprint, apply report SHA-256, backup manifest SHA-256, and new rollback report path. Use the immutable applied report that owns the exact candidate set; do not manufacture or edit it.

```powershell
python scripts/migrate_entity_status.py rollback --target pg --database-url-env <OWNER_SUPPLIED_ENV> --apply-report <APPLY_REPORT> --backup-manifest <BACKUP_MANIFEST> --confirm-target <AUTHORIZED_TARGET_FINGERPRINT> --confirm-apply-report-sha256 <AUTHORIZED_APPLY_REPORT_SHA256> --confirm-backup-manifest-sha256 <AUTHORIZED_BACKUP_MANIFEST_SHA256> --report-out <NEW_ROLLBACK_REPORT>
```

Logical rollback must abort on target drift, schema drift, status drift, count drift, missing or foreign audit ownership, changed report bytes, changed backup evidence, or any manual/later update to a candidate. Do not force rollback past a refusal. If logical rollback cannot pass its ownership checks, stop and use the validated custom-format PostgreSQL backup only through a separately approved disaster-recovery procedure.

## Safe integration skip

`tests/test_migrate_entity_status_postgres.py` is permitted to use only a disposable PostgreSQL target supplied through `ENTITY_STATUS_TEST_DATABASE_URL`. If that environment variable is absent, the integration suite must report a safe skip. Do not point it at Stage B/Stage C or production credentials. Docker and Nginx availability are observational checks only; absence does not authorize installation.

## STOP

After Stage A verification and commit, stop and request separately scoped Stage B target context from the owner. Stage A is not target authorization. After Stage B, stop again for separate exact-artifact Stage C authorization. After Stage C, stop before deployment, noindex changes, export reconciliation, or rollback unless each action receives its own scope and authorization.
