import re
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MIGRATION_TOOL = ROOT / "scripts" / "migrate_entity_status.py"
RUNBOOK = ROOT / "docs" / "runbooks" / "entity-published-status-migration.md"


def _cli_args(command: str, target: str, environment_name: str, report: Path) -> list[str]:
    common = [
        sys.executable,
        str(MIGRATION_TOOL),
        command,
        "--target",
        target,
        "--database-url-env",
        environment_name,
    ]
    if command == "plan":
        return [
            *common,
            "--policy",
            "published-v1",
            "--report-out",
            str(report),
        ]
    if command == "apply":
        return [
            *common,
            "--plan",
            str(report.parent / "missing-plan.json"),
            "--backup-manifest",
            str(report.parent / "missing-manifest.json"),
            "--confirm-target",
            "0" * 64,
            "--confirm-plan-sha256",
            "0" * 64,
            "--confirm-backup-manifest-sha256",
            "0" * 64,
            "--report-out",
            str(report),
        ]
    return [
        *common,
        "--apply-report",
        str(report.parent / "missing-apply.json"),
        "--backup-manifest",
        str(report.parent / "missing-manifest.json"),
        "--confirm-target",
        "0" * 64,
        "--confirm-apply-report-sha256",
        "0" * 64,
        "--confirm-backup-manifest-sha256",
        "0" * 64,
        "--report-out",
        str(report),
    ]


@pytest.mark.parametrize("command", ["plan", "apply", "rollback"])
@pytest.mark.parametrize(
    ("target", "environment_name"),
    [("sqlite", "ENTITY_STATUS_GUARD_DATABASE_URL"), ("pg", "DATABASE_URL")],
)
def test_migration_cli_refuses_unsafe_target_or_default_environment_without_report(
    tmp_path: Path,
    command: str,
    target: str,
    environment_name: str,
) -> None:
    report = tmp_path / f"{command}-report.json"

    result = subprocess.run(
        _cli_args(command, target, environment_name, report),
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert result.stdout == ""
    assert not report.exists()


def test_migration_tool_avoids_project_database_imports_and_local_data_literals():
    source = MIGRATION_TOOL.read_text(encoding="utf-8")

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


def _without_javascript_comments(source: str) -> str:
    without_blocks = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    return re.sub(r"//[^\r\n]*", "", without_blocks)


def test_global_noindex_default_and_authoritative_header_are_executable_code():
    config = _without_javascript_comments(
        (ROOT / "web-nuxt" / "nuxt.config.ts").read_text(encoding="utf-8")
    )
    middleware = _without_javascript_comments(
        (ROOT / "web-nuxt" / "server" / "middleware" / "noindex.ts").read_text(
            encoding="utf-8"
        )
    )

    assert re.search(
        r"\bsiteNoindex\s*:\s*process\.env\.NUXT_PUBLIC_SITE_NOINDEX\s*!==\s*"
        r"(?P<quote>['\"])false(?P=quote)",
        config,
    )
    assert re.search(
        r"if\s*\(\s*useRuntimeConfig\(event\)\.public\.siteNoindex\s*\)\s*\{"
        r"\s*setResponseHeader\(\s*event\s*,\s*(?P<header_quote>['\"])"
        r"X-Robots-Tag(?P=header_quote)\s*,\s*(?P<value_quote>['\"])"
        r"noindex, follow(?P=value_quote)\s*\)",
        middleware,
        flags=re.DOTALL,
    )


def test_runbook_is_fail_closed_and_reproducible():
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
        "PowerShell 7+ on Windows",
        "Stage A completion is not authorization for Stage B or Stage C",
        "separate Stage C authorization",
        "exact target fingerprint",
        "candidate ID hash",
        "X-Robots-Tag: noindex, follow",
        "Do not import web/data.json",
        "Do not mutate local data",
        "commit-success/report-write failure",
        "EXACT same target, plan, backup, and confirmation values",
        "recovery_ready=true",
        "recovery_contract=apply-audit-exact-v1",
        "zero status writes and zero audit writes",
        "already-rolled-back",
        "recovery_contract=rollback-audit-exact-v1",
        "Do not jump to disaster recovery while the transaction outcome is ambiguous",
        "residual concurrent race",
        "not an immutable-artifact writer",
        "Reconciliation into tracked web/data.json or local SQLite is a separate reviewed task",
        "Do not start or deploy a server",
    ):
        assert phrase in runbook

    for snippet in (
        "$ErrorActionPreference = 'Stop'",
        "$StageABase = '<AUTHORIZED_STAGE_A_BASE_SHA>'",
        'git diff --check "$StageABase..HEAD"',
        'git diff --name-only "$StageABase..HEAD"',
        "$OwnerBaseUrl = '<OWNER_SUPPLIED_BASE_URL>'",
        "Invoke-WebRequest",
        "-Method Get",
        "$NoindexResponse.Headers['X-Robots-Tag']",
        "-ne 'noindex, follow'",
        '$OwnerEnvItem = Get-Item -LiteralPath "Env:$OwnerEnvName" -ErrorAction Stop',
        "$ExportPath = [System.IO.Path]::GetFullPath",
        "$TrackedDataPath = [System.IO.Path]::GetFullPath",
        "$RepositoryDbPath = [System.IO.Path]::GetFullPath",
        "Test-Path -LiteralPath $ExportPath",
        "StartsWith('postgresql://'",
        '& python scripts/export_data.py --dry-run --out "$ExportPath"',
        '& python scripts/export_data.py --out "$ExportPath"',
        "if ($LASTEXITCODE -ne 0)",
    ):
        assert snippet in runbook

    assert "--database-url-env <OWNER_SUPPLIED_ENV>" not in runbook
    assert "scripts/export_data.py --database-url-env" not in runbook
