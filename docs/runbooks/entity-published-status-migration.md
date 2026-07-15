# Entity Published-Status Migration Runbook

> STATUS: active safety runbook; Stage B, Stage C, rollback, deployment, export reconciliation, and indexing changes each require separately scoped authorization.

All executable blocks in this runbook target PowerShell 7+ on Windows. Assign every owner-supplied placeholder to a quoted variable before invoking a command. Do not paste angle-bracket placeholders directly into command arguments.

## Safety boundary

- `scripts/migrate_entity_status.py` is PostgreSQL-only. It must refuse every target except `pg` and every connection environment named `DATABASE_URL` before artifact access or database connection.
- Stage A changes and verifies repository code, tests, and documentation only. It must not connect to a project database, create a production backup or plan, mutate data, deploy, start a server, or change indexing.
- Stage B creates a PostgreSQL backup plus an immutable migration plan only. It requires separate target context and stops before apply.
- Stage C performs the logical apply only after separate Stage C authorization tied to exact reviewed artifacts.
- Rollback is a separate incident action. It is not automatically authorized by Stage C.
- Do not import web/data.json, write local SQLite first, deploy, infer launch completion, or change Nuxt noindex settings.
- Do not mutate local data, tracked `web/data.json`, or `agent/data/vinhlong360.db` in Stage A or as migration inputs.
- Global noindex remains enabled by executable source and must also be verified against an explicit live URL as `X-Robots-Tag: noindex, follow`.

## Stage A evidence

Stage A is repository-only. The owner must provide the exact authorized base commit for the review range. A bare post-commit diff is not evidence for the complete Stage A range.

```powershell
$ErrorActionPreference = 'Stop'
$StageABase = '<AUTHORIZED_STAGE_A_BASE_SHA>'

if ($StageABase -notmatch '^[0-9a-fA-F]{40,64}$') {
    throw 'Stage A base must be an explicit full commit SHA.'
}

& git cat-file -e "$StageABase`^{commit}"
if ($LASTEXITCODE -ne 0) { throw 'Authorized Stage A base is not a commit.' }

$DataJsonPath = [System.IO.Path]::GetFullPath('web/data.json')
$RepositoryDbPath = [System.IO.Path]::GetFullPath('agent/data/vinhlong360.db')
$DataJsonBefore = (Get-FileHash -LiteralPath $DataJsonPath -Algorithm SHA256).Hash
$RepositoryDbBefore = (Get-FileHash -LiteralPath $RepositoryDbPath -Algorithm SHA256).Hash

& python -m pytest agent/tests/test_index_policy.py agent/tests/test_publication_status.py agent/tests/test_database.py agent/tests/test_admin_mutations.py agent/tests/test_kb_curation.py agent/tests/test_seo.py agent/tests/test_seo_structured.py tests/checks/test_hard_checks.py tests/test_export_data.py tests/test_postgres_target.py tests/test_backup_data.py tests/test_migrate_entity_status.py tests/test_migrate_entity_status_postgres.py tests/test_entity_status_migration_guardrails.py -q
if ($LASTEXITCODE -ne 0) { throw 'Focused Stage A suite failed.' }

& python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'Default pytest suite failed.' }

& python -m ruff check agent/public_entity_types.py agent/publication_status.py agent/index_policy.py agent/launch_evidence.py agent/database.py scripts/postgres_target.py scripts/backup_data.py scripts/migrate_entity_status.py scripts/checks/check_data_schema.py tests/test_postgres_target.py tests/test_backup_data.py tests/test_migrate_entity_status.py tests/test_migrate_entity_status_postgres.py tests/test_entity_status_migration_guardrails.py
if ($LASTEXITCODE -ne 0) { throw 'Ruff failed.' }

& python -m ruff check agent/public_entity_types.py agent/publication_status.py agent/index_policy.py agent/launch_evidence.py agent/database.py scripts/postgres_target.py scripts/backup_data.py scripts/migrate_entity_status.py scripts/checks/check_data_schema.py tests/test_postgres_target.py tests/test_backup_data.py tests/test_migrate_entity_status.py tests/test_migrate_entity_status_postgres.py tests/test_entity_status_migration_guardrails.py --select C901 --config lint.mccabe.max-complexity=12
if ($LASTEXITCODE -ne 0) { throw 'Ruff C901 failed.' }

& python -c "from scripts.checks import common; from scripts.checks.check_complexity import ComplexityCheck; files=['agent/public_entity_types.py','agent/publication_status.py','agent/index_policy.py','agent/launch_evidence.py','agent/database.py','scripts/postgres_target.py','scripts/backup_data.py','scripts/migrate_entity_status.py','scripts/checks/check_data_schema.py']; result=ComplexityCheck().run(files=files); baseline=common.load_baseline(); print({'count': result['count'], 'baseline': baseline.get(result['rule'], 0), 'violations': result['violations']}); raise SystemExit(1 if result['count'] > baseline.get(result['rule'], 0) else 0)"
if ($LASTEXITCODE -ne 0) { throw 'Custom complexity ratchet increased.' }

& python -m pytest tests/test_migrate_entity_status_postgres.py -q -m entity_status_postgres
if ($LASTEXITCODE -ne 0) { throw 'Disposable PostgreSQL integration failed.' }

$DataJsonAfter = (Get-FileHash -LiteralPath $DataJsonPath -Algorithm SHA256).Hash
$RepositoryDbAfter = (Get-FileHash -LiteralPath $RepositoryDbPath -Algorithm SHA256).Hash
if ($DataJsonAfter -ne $DataJsonBefore) { throw 'Tracked web/data.json changed during Stage A.' }
if ($RepositoryDbAfter -ne $RepositoryDbBefore) { throw 'Repository SQLite changed during Stage A.' }

& git diff --check "$StageABase..HEAD"
if ($LASTEXITCODE -ne 0) { throw 'Stage A range has whitespace errors.' }

& git diff --name-only "$StageABase..HEAD"
if ($LASTEXITCODE -ne 0) { throw 'Unable to enumerate the Stage A range.' }

& git status --short
if ($LASTEXITCODE -ne 0) { throw 'Unable to read worktree status.' }
```

Record exact command output, test counts, the authorized range file list, both before/after hashes, and worktree status in the review evidence. The PostgreSQL integration may safely skip only when `ENTITY_STATUS_TEST_DATABASE_URL` is absent. Docker executable: unavailable. Nginx executable: unavailable. No installation was attempted.

Verify noindex from executable source through the guard test, then verify the already-running authorized environment over HTTP. Do not start or deploy a server for this check.

```powershell
$ErrorActionPreference = 'Stop'
$OwnerBaseUrl = '<OWNER_SUPPLIED_BASE_URL>'

& python -m pytest tests/test_entity_status_migration_guardrails.py::test_global_noindex_default_and_authoritative_header_are_executable_code -q
if ($LASTEXITCODE -ne 0) { throw 'Noindex source guard failed.' }

$BaseUri = [Uri]$OwnerBaseUrl
if ($BaseUri.Scheme -notin @('http', 'https')) { throw 'Owner base URL must be HTTP(S).' }
$NoindexResponse = Invoke-WebRequest -Uri $BaseUri -Method Get -MaximumRedirection 0 -SkipHttpErrorCheck
$NoindexHeader = [string]$NoindexResponse.Headers['X-Robots-Tag']
if ($NoindexHeader -ne 'noindex, follow') {
    throw "Live X-Robots-Tag mismatch: '$NoindexHeader'"
}
```

Stop after the Stage A commit. Stage A completion is not authorization for Stage B or Stage C.

## Stage B: backup and plan

The owner supplies a named PostgreSQL connection environment other than `DATABASE_URL`. Use new paths and refuse repository defaults.

```powershell
$ErrorActionPreference = 'Stop'
$OwnerEnvName = '<OWNER_SUPPLIED_ENV>'
$BackupRoot = [System.IO.Path]::GetFullPath('<NEW_BACKUP_ROOT>')
$PlanPath = [System.IO.Path]::GetFullPath('<NEW_PLAN_PATH>')

if ([string]::IsNullOrWhiteSpace($OwnerEnvName) -or $OwnerEnvName -eq 'DATABASE_URL') {
    throw 'A named PostgreSQL environment other than DATABASE_URL is required.'
}
$OwnerEnvItem = Get-Item -LiteralPath "Env:$OwnerEnvName" -ErrorAction Stop
$OwnerDatabaseUrl = [string]$OwnerEnvItem.Value
if ([string]::IsNullOrWhiteSpace($OwnerDatabaseUrl) -or -not $OwnerDatabaseUrl.StartsWith('postgresql://', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Owner environment must contain a nonempty postgresql:// URL.'
}
if (Test-Path -LiteralPath $BackupRoot) { throw 'Backup root must be new.' }
if (Test-Path -LiteralPath $PlanPath) { throw 'Plan path must be new.' }

& python scripts/backup_data.py --target pg --database-url-env "$OwnerEnvName" --out-dir "$BackupRoot"
if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL backup failed.' }

& python scripts/migrate_entity_status.py plan --target pg --database-url-env "$OwnerEnvName" --policy published-v1 --report-out "$PlanPath"
if ($LASTEXITCODE -ne 0) { throw 'Publication plan failed.' }
```

Review the exact target/database identity, schema fingerprint and columns, candidate IDs/count/hash, every exclusion count and rule, status groups, expected counts, backup manifest/artifact hashes and age, restore listing, tool versions, plan hash/canonical bytes/source revision/freshness, and source plus live noindex evidence. Stop if any value is missing, unexplained, stale, inconsistent, or points at an unexpected target. Stage B authorization permits backup and plan only.

## Stage C: apply after separate authorization

The owner authorization record must name the exact target fingerprint, plan SHA-256, backup manifest SHA-256, candidate count, and candidate ID hash. Keep those values fixed for both calls below. The second call changes only the new report path.

```powershell
$ErrorActionPreference = 'Stop'
$OwnerEnvName = '<OWNER_SUPPLIED_ENV>'
$PlanPath = [System.IO.Path]::GetFullPath('<PLAN_PATH>')
$BackupManifestPath = [System.IO.Path]::GetFullPath('<BACKUP_MANIFEST>')
$ApplyReportPath = [System.IO.Path]::GetFullPath('<NEW_APPLY_REPORT>')
$ApplyRecoveryReportPath = [System.IO.Path]::GetFullPath('<NEW_APPLY_RECOVERY_REPORT>')
$AuthorizedTargetFingerprint = '<AUTHORIZED_TARGET_FINGERPRINT>'
$AuthorizedPlanSha256 = '<AUTHORIZED_PLAN_SHA256>'
$AuthorizedBackupManifestSha256 = '<AUTHORIZED_BACKUP_MANIFEST_SHA256>'
$AuthorizedCandidateCount = [int]::Parse('<AUTHORIZED_CANDIDATE_COUNT>')
$AuthorizedCandidateIdHash = '<AUTHORIZED_CANDIDATE_ID_HASH>'

if ($ApplyReportPath -eq $ApplyRecoveryReportPath) { throw 'Apply report paths must differ.' }
if (Test-Path -LiteralPath $ApplyReportPath) { throw 'Apply report path must be new.' }
if (Test-Path -LiteralPath $ApplyRecoveryReportPath) { throw 'Apply recovery path must be new.' }

& python scripts/migrate_entity_status.py apply --target pg --database-url-env "$OwnerEnvName" --plan "$PlanPath" --backup-manifest "$BackupManifestPath" --confirm-target "$AuthorizedTargetFingerprint" --confirm-plan-sha256 "$AuthorizedPlanSha256" --confirm-backup-manifest-sha256 "$AuthorizedBackupManifestSha256" --report-out "$ApplyReportPath"
$FirstApplyExit = $LASTEXITCODE

if ($FirstApplyExit -eq 0 -and (Test-Path -LiteralPath $ApplyReportPath)) {
    $FirstApply = Get-Content -Raw -LiteralPath $ApplyReportPath | ConvertFrom-Json
    if ($FirstApply.result -ne 'applied') { throw 'First apply report is not exact applied evidence.' }
}
elseif ($FirstApplyExit -ne 0 -and -not (Test-Path -LiteralPath $ApplyReportPath)) {
    Write-Warning 'Apply returned nonzero with no report: this may be a commit-success/report-write failure.'
}
else {
    throw 'Apply exit/report combination is ambiguous; preserve evidence and STOP.'
}

# Retry the EXACT same target, plan, backup, and confirmation values. Change only report-out.
& python scripts/migrate_entity_status.py apply --target pg --database-url-env "$OwnerEnvName" --plan "$PlanPath" --backup-manifest "$BackupManifestPath" --confirm-target "$AuthorizedTargetFingerprint" --confirm-plan-sha256 "$AuthorizedPlanSha256" --confirm-backup-manifest-sha256 "$AuthorizedBackupManifestSha256" --report-out "$ApplyRecoveryReportPath"
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $ApplyRecoveryReportPath)) {
    throw 'Apply recovery retry did not produce exact evidence; STOP.'
}

$ApplyRecovery = Get-Content -Raw -LiteralPath $ApplyRecoveryReportPath | ConvertFrom-Json
if ($ApplyRecovery.result -ne 'already-applied' -or $ApplyRecovery.recovery_ready -ne $true -or $ApplyRecovery.recovery_contract -ne 'apply-audit-exact-v1') {
    throw 'Apply recovery contract mismatch; STOP.'
}
```

Accept recovery only with exact `already-applied`, `recovery_ready=true`, and `recovery_contract=apply-audit-exact-v1` evidence, after independently captured before/after database evidence also shows the exact authorized candidate/status counts and exact owned audit set are unchanged across the retry: zero status writes and zero audit writes. The values represented by `$AuthorizedCandidateCount` and `$AuthorizedCandidateIdHash` must still match the plan and recovery evidence. Any mismatch requires STOP; do not change confirmations or create a new plan inside Stage C.

## Post-apply DB export artifact

Run this block only after exact apply recovery evidence. `scripts/export_data.py` supports only `--dry-run` and `--out`; it reads through `DATABASE_URL`. The block temporarily maps the already authorized named PostgreSQL URL and restores the prior process environment in `finally`.

```powershell
$ErrorActionPreference = 'Stop'
$OwnerEnvName = '<OWNER_SUPPLIED_ENV>'
$ExportPath = [System.IO.Path]::GetFullPath('<NEW_POST_APPLY_EXPORT_PATH>')
$TrackedDataPath = [System.IO.Path]::GetFullPath('web/data.json')
$RepositoryDbPath = [System.IO.Path]::GetFullPath('agent/data/vinhlong360.db')

$OwnerEnvItem = Get-Item -LiteralPath "Env:$OwnerEnvName" -ErrorAction Stop
$OwnerDatabaseUrl = [string]$OwnerEnvItem.Value
if ([string]::IsNullOrWhiteSpace($OwnerDatabaseUrl) -or -not $OwnerDatabaseUrl.StartsWith('postgresql://', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Owner environment must contain a nonempty postgresql:// URL.'
}
if ([StringComparer]::OrdinalIgnoreCase.Equals($ExportPath, $TrackedDataPath)) {
    throw 'Export path must not be tracked web/data.json.'
}
if ([StringComparer]::OrdinalIgnoreCase.Equals($ExportPath, $RepositoryDbPath)) {
    throw 'Export path must not be the repository database.'
}
if (Test-Path -LiteralPath $ExportPath) { throw 'Export path must be new and unique.' }
$ExportDirectory = Split-Path -Parent $ExportPath
if (-not (Test-Path -LiteralPath $ExportDirectory -PathType Container)) {
    throw 'Export parent directory must already exist and be operator-owned.'
}

$PreviousDatabaseUrlItem = Get-Item -LiteralPath 'Env:DATABASE_URL' -ErrorAction SilentlyContinue
$HadPreviousDatabaseUrl = $null -ne $PreviousDatabaseUrlItem
$PreviousDatabaseUrl = if ($HadPreviousDatabaseUrl) { [string]$PreviousDatabaseUrlItem.Value } else { $null }

try {
    $env:DATABASE_URL = $OwnerDatabaseUrl

    & python scripts/export_data.py --dry-run --out "$ExportPath"
    if ($LASTEXITCODE -ne 0) { throw 'Post-apply export dry-run failed.' }
    if (Test-Path -LiteralPath $ExportPath) { throw 'Dry-run unexpectedly created the export path.' }

    & python scripts/export_data.py --out "$ExportPath"
    if ($LASTEXITCODE -ne 0) { throw 'Post-apply export write failed.' }
    if (-not (Test-Path -LiteralPath $ExportPath -PathType Leaf)) { throw 'Export artifact is missing.' }
}
finally {
    if ($HadPreviousDatabaseUrl) {
        $env:DATABASE_URL = $PreviousDatabaseUrl
    }
    else {
        Remove-Item -LiteralPath 'Env:DATABASE_URL' -ErrorAction SilentlyContinue
    }
}
```

The new-path preflight is mandatory, but `export_data.py` ultimately uses `os.replace` and is not an immutable-artifact writer. A residual concurrent race remains between the preflight and replacement. Use a unique operator-owned directory with no concurrent writers; otherwise STOP. Record the export SHA-256, file size, counts, target fingerprint, apply report SHA-256, and path. Do not overwrite tracked `web/data.json`. Reconciliation into tracked web/data.json or local SQLite is a separate reviewed task.

## Rollback

Rollback requires a separate owner decision naming the exact target fingerprint, apply report SHA-256, backup manifest SHA-256, and two new report paths. Keep target, apply report, backup, and confirmation values fixed across the first call and recovery retry.

```powershell
$ErrorActionPreference = 'Stop'
$OwnerEnvName = '<OWNER_SUPPLIED_ENV>'
$ApplyReportPath = [System.IO.Path]::GetFullPath('<APPLY_REPORT>')
$BackupManifestPath = [System.IO.Path]::GetFullPath('<BACKUP_MANIFEST>')
$RollbackReportPath = [System.IO.Path]::GetFullPath('<NEW_ROLLBACK_REPORT>')
$RollbackRecoveryReportPath = [System.IO.Path]::GetFullPath('<NEW_ROLLBACK_RECOVERY_REPORT>')
$AuthorizedTargetFingerprint = '<AUTHORIZED_TARGET_FINGERPRINT>'
$AuthorizedApplyReportSha256 = '<AUTHORIZED_APPLY_REPORT_SHA256>'
$AuthorizedBackupManifestSha256 = '<AUTHORIZED_BACKUP_MANIFEST_SHA256>'

if ($RollbackReportPath -eq $RollbackRecoveryReportPath) { throw 'Rollback report paths must differ.' }
if (Test-Path -LiteralPath $RollbackReportPath) { throw 'Rollback report path must be new.' }
if (Test-Path -LiteralPath $RollbackRecoveryReportPath) { throw 'Rollback recovery path must be new.' }

& python scripts/migrate_entity_status.py rollback --target pg --database-url-env "$OwnerEnvName" --apply-report "$ApplyReportPath" --backup-manifest "$BackupManifestPath" --confirm-target "$AuthorizedTargetFingerprint" --confirm-apply-report-sha256 "$AuthorizedApplyReportSha256" --confirm-backup-manifest-sha256 "$AuthorizedBackupManifestSha256" --report-out "$RollbackReportPath"
$FirstRollbackExit = $LASTEXITCODE

if ($FirstRollbackExit -eq 0 -and (Test-Path -LiteralPath $RollbackReportPath)) {
    $FirstRollback = Get-Content -Raw -LiteralPath $RollbackReportPath | ConvertFrom-Json
    if ($FirstRollback.result -ne 'rolled-back') { throw 'First rollback report is not exact rolled-back evidence.' }
}
elseif ($FirstRollbackExit -ne 0 -and -not (Test-Path -LiteralPath $RollbackReportPath)) {
    Write-Warning 'Rollback returned nonzero with no report: this may be a commit-success/report-write failure.'
}
else {
    throw 'Rollback exit/report combination is ambiguous; preserve evidence and STOP.'
}

# Retry the exact same target, apply report, backup, and confirmation values. Change only report-out.
& python scripts/migrate_entity_status.py rollback --target pg --database-url-env "$OwnerEnvName" --apply-report "$ApplyReportPath" --backup-manifest "$BackupManifestPath" --confirm-target "$AuthorizedTargetFingerprint" --confirm-apply-report-sha256 "$AuthorizedApplyReportSha256" --confirm-backup-manifest-sha256 "$AuthorizedBackupManifestSha256" --report-out "$RollbackRecoveryReportPath"
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $RollbackRecoveryReportPath)) {
    throw 'Rollback recovery retry did not produce exact evidence; STOP.'
}

$RollbackRecovery = Get-Content -Raw -LiteralPath $RollbackRecoveryReportPath | ConvertFrom-Json
if ($RollbackRecovery.result -ne 'already-rolled-back' -or $RollbackRecovery.recovery_ready -ne $true -or $RollbackRecovery.recovery_contract -ne 'rollback-audit-exact-v1' -or $RollbackRecovery.restored_count -ne 0 -or $RollbackRecovery.restored_ids.Count -ne 0) {
    throw 'Rollback recovery contract mismatch; STOP.'
}
```

Accept rollback recovery only with exact `already-rolled-back`, `recovery_ready=true`, and `recovery_contract=rollback-audit-exact-v1` evidence, when expected before/after counts exactly match the authorized apply report and independently captured before/after evidence proves the retry added no rollback audit and changed no status. Logical rollback must refuse target/schema/status/count/audit ownership drift or changed evidence.

Do not jump to disaster recovery while the transaction outcome is ambiguous. A nonzero recovery retry means STOP, preserve all evidence, and establish actual database state with separately approved read-only investigation. Use the validated custom-format PostgreSQL backup only after a separate disaster-recovery decision establishes that logical rollback cannot safely pass; never use restore as a guess.

## Safe integration skip

`tests/test_migrate_entity_status_postgres.py` may use only a disposable target supplied through `ENTITY_STATUS_TEST_DATABASE_URL` plus its disposable confirmation. If absent, the suite must safely skip. Never point it at Stage B, Stage C, or production credentials. Docker and Nginx checks are observational only; absence does not authorize installation.

## STOP

After Stage A verification and commit, request separately scoped Stage B target context. Stage A is not target authorization. After Stage B, stop for separate exact-artifact Stage C authorization. After Stage C, stop before deployment, noindex changes, export reconciliation, or rollback unless each receives its own scope and authorization.
