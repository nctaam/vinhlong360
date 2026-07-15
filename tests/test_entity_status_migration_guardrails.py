from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATION_TOOL = ROOT / "scripts" / "migrate_entity_status.py"
RUNBOOK = ROOT / "docs" / "runbooks" / "entity-published-status-migration.md"


def test_migration_tool_is_postgresql_only_and_avoids_project_data_sources():
    source = MIGRATION_TOOL.read_text(encoding="utf-8")

    assert source.count('if args.target != "pg":') >= 3
    for command in ("plan", "apply", "rollback"):
        assert f'{command} target must be pg' in source
        assert (
            f'{command} requires a named database URL environment other than DATABASE_URL'
            in source
        )

    for forbidden in (
        "from database import",
        "import database",
        "from agent.database import",
        "import agent.database",
        "web/data.json",
        "web\\data.json",
        "vinhlong360.db",
    ):
        assert forbidden not in source


def test_global_noindex_default_and_authoritative_header_remain_enabled():
    config = (ROOT / "web-nuxt" / "nuxt.config.ts").read_text(encoding="utf-8")
    middleware = (
        ROOT / "web-nuxt" / "server" / "middleware" / "noindex.ts"
    ).read_text(encoding="utf-8")

    assert "process.env.NUXT_PUBLIC_SITE_NOINDEX !== 'false'" in config
    assert "setResponseHeader(event, 'X-Robots-Tag', 'noindex, follow')" in middleware


def test_runbook_preserves_stage_boundaries_and_exact_authorization_contract():
    assert RUNBOOK.is_file(), "the publication-status migration runbook must exist"
    runbook = RUNBOOK.read_text(encoding="utf-8")

    for heading in (
        "## Safety boundary",
        "## Stage A evidence",
        "## Stage B: backup and plan",
        "## Stage C: apply after separate authorization",
        "## Post-apply DB export artifact",
        "## Rollback",
        "## Safe integration skip",
        "## STOP",
    ):
        assert heading in runbook

    for phrase in (
        "Stage A completion is not authorization for Stage B or Stage C",
        "separate Stage C authorization",
        "exact target fingerprint",
        "plan SHA-256",
        "backup manifest SHA-256",
        "candidate count",
        "candidate ID hash",
        "schema fingerprint",
        "every exclusion count",
        "status groups",
        "X-Robots-Tag: noindex, follow",
        "Do not import web/data.json",
        "Do not mutate local data",
        "recovery_ready=true",
        "recovery_contract=apply-audit-exact-v1",
        "zero status writes and zero audit writes",
        "Reconciliation into tracked web/data.json or local SQLite is a separate reviewed task",
        "Docker executable: unavailable",
        "Nginx executable: unavailable",
        "No installation was attempted",
        "802 passed, 8 skipped, 2 deselected, 1 xfailed",
        "6871 passed, 48 skipped, 80 deselected, 1 xfailed",
        "2 skipped because no disposable PostgreSQL target was supplied",
        "7d20a0442129ae650c168225d3a6d4e0c7a96797ba8e3b003f3b61b76f493418",
        "3c9c1235e2c32409df52bcf60d115515e292fbaf18d0b1aaf912a9e843847c1f",
    ):
        assert phrase in runbook

    assert (
        "python scripts/backup_data.py --target pg --database-url-env "
        "<OWNER_SUPPLIED_ENV> --out-dir <NEW_BACKUP_ROOT>"
    ) in runbook
    assert (
        "python scripts/migrate_entity_status.py plan --target pg "
        "--database-url-env <OWNER_SUPPLIED_ENV> --policy published-v1 "
        "--report-out <NEW_PLAN_PATH>"
    ) in runbook
    assert (
        "python scripts/migrate_entity_status.py apply --target pg "
        "--database-url-env <OWNER_SUPPLIED_ENV> --plan <PLAN_PATH> "
        "--backup-manifest <BACKUP_MANIFEST> --confirm-target "
        "<AUTHORIZED_TARGET_FINGERPRINT> --confirm-plan-sha256 "
        "<AUTHORIZED_PLAN_SHA256> --confirm-backup-manifest-sha256 "
        "<AUTHORIZED_BACKUP_MANIFEST_SHA256> --report-out <NEW_APPLY_REPORT>"
    ) in runbook
    assert (
        "python scripts/migrate_entity_status.py rollback --target pg "
        "--database-url-env <OWNER_SUPPLIED_ENV> --apply-report <APPLY_REPORT> "
        "--backup-manifest <BACKUP_MANIFEST> --confirm-target "
        "<AUTHORIZED_TARGET_FINGERPRINT> --confirm-apply-report-sha256 "
        "<AUTHORIZED_APPLY_REPORT_SHA256> "
        "--confirm-backup-manifest-sha256 "
        "<AUTHORIZED_BACKUP_MANIFEST_SHA256> --report-out "
        "<NEW_ROLLBACK_REPORT>"
    ) in runbook

    assert "python scripts/export_data.py --dry-run --out " in runbook
    assert "python scripts/export_data.py --out " in runbook
    assert "scripts/export_data.py --database-url-env" not in runbook
    assert "python scripts/check_complexity.py" not in runbook
    assert "from scripts.checks.check_complexity import ComplexityCheck" in runbook
