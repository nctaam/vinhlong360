import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MIGRATION_TOOL = ROOT / "scripts" / "migrate_entity_status.py"
RUNBOOK = ROOT / "docs" / "runbooks" / "entity-published-status-migration.md"
WEB_NUXT = ROOT / "web-nuxt"
NOINDEX_AST_GUARD = ROOT / "tests" / "helpers" / "noindex_ast_guard.cjs"


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


def _assert_typescript_noindex_guard(source: str, mode: str) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        source_path = Path(temp_dir) / "source.ts"
        source_path.write_text(source, encoding="utf-8")
        result = subprocess.run(
            ["node", str(NOINDEX_AST_GUARD), mode, str(source_path)],
            cwd=WEB_NUXT,
            check=False,
            capture_output=True,
            text=True,
        )

    assert result.returncode == 0, result.stderr


def _assert_runtime_config_uses_site_noindex_shorthand(config: str) -> None:
    _assert_typescript_noindex_guard(config, "runtime")


def _assert_nitro_catch_all_noindex_header(config: str) -> None:
    _assert_typescript_noindex_guard(config, "nitro")


def test_runtime_config_guard_does_not_match_site_noindex_outside_public():
    config = """
const siteNoindex = process.env.NUXT_PUBLIC_SITE_NOINDEX !== 'false'
export default defineNuxtConfig({
  runtimeConfig: {
    public: {
      apiBase,
    },
    private: {
      siteNoindex,
    },
  },
})
"""

    with pytest.raises(AssertionError):
        _assert_runtime_config_uses_site_noindex_shorthand(config)


def test_runtime_config_guard_rejects_extended_site_noindex_initializer():
    config = """
const siteNoindex = process.env.NUXT_PUBLIC_SITE_NOINDEX !== 'false' && false
export default defineNuxtConfig({
  runtimeConfig: {
    public: {
      siteNoindex,
    },
  },
})
"""

    with pytest.raises(AssertionError):
        _assert_runtime_config_uses_site_noindex_shorthand(config)


def test_runtime_config_guard_ignores_markers_in_doc_string_before_real_config():
    config = """
const documentation = `
const siteNoindex = process.env.NUXT_PUBLIC_SITE_NOINDEX !== 'false'
runtimeConfig: {
  public: {
    siteNoindex,
  },
}
`
export default defineNuxtConfig({
  runtimeConfig: {
    public: {
      apiBase,
    },
  },
})
"""

    with pytest.raises(AssertionError):
        _assert_runtime_config_uses_site_noindex_shorthand(config)


def test_nitro_guard_rejects_later_x_robots_tag_override():
    config = """
export default defineNuxtConfig({
  nitro: {
    routeRules: {
      '/**': {
        headers: {
          ...(siteNoindex ? { 'X-Robots-Tag': 'noindex, follow' } : {}),
          'X-Robots-Tag': 'index, follow',
        },
      },
    },
  },
})
"""

    with pytest.raises(AssertionError):
        _assert_nitro_catch_all_noindex_header(config)


def test_nitro_guard_rejects_unknown_spread_after_noindex_header():
    config = """
export default defineNuxtConfig({
  nitro: {
    routeRules: {
      '/**': {
        headers: {
          ...(siteNoindex ? { 'X-Robots-Tag': 'noindex, follow' } : {}),
          ...runtimeHeaders,
          'X-Content-Type-Options': 'nosniff',
        },
      },
    },
  },
})
"""

    with pytest.raises(AssertionError):
        _assert_nitro_catch_all_noindex_header(config)


def test_middleware_guard_rejects_header_call_inside_unused_arrow():
    middleware = """
export default defineEventHandler((event) => {
  if (useRuntimeConfig(event).public.siteNoindex) {
    const setNoindex = () => {
      setResponseHeader(event, 'X-Robots-Tag', 'noindex, follow')
    }
  }
})
"""

    with pytest.raises(AssertionError):
        _assert_typescript_noindex_guard(middleware, "middleware")


def test_global_noindex_default_and_authoritative_header_are_executable_code():
    config = (WEB_NUXT / "nuxt.config.ts").read_text(encoding="utf-8")
    middleware = (
        WEB_NUXT / "server" / "middleware" / "noindex.ts"
    ).read_text(
        encoding="utf-8"
    )

    _assert_typescript_noindex_guard(config, "config")
    _assert_typescript_noindex_guard(middleware, "middleware")


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
