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
    result: list[str] = []
    index = 0
    quote: str | None = None

    while index < len(source):
        char = source[index]

        if quote is not None:
            result.append(char)
            if char == "\\" and index + 1 < len(source):
                result.append(source[index + 1])
                index += 2
                continue
            if char == quote:
                quote = None
            index += 1
            continue

        if char in ("'", '"', "`"):
            quote = char
            result.append(char)
            index += 1
            continue

        if source.startswith("//", index):
            result.append(" ")
            index += 2
            while index < len(source) and source[index] not in "\r\n":
                index += 1
            continue

        if source.startswith("/*", index):
            result.append(" ")
            index += 2
            while index < len(source) and not source.startswith("*/", index):
                if source[index] in "\r\n":
                    result.append(source[index])
                index += 1
            index += 2 if source.startswith("*/", index) else 0
            continue

        result.append(char)
        index += 1

    return "".join(result)


def test_javascript_comment_stripper_preserves_markers_inside_strings():
    source = """
const httpUrl = 'http://localhost:8360/path//segment'
const httpsUrl = "https://example.com/a/*literal*/b"
const slashMarker = '// keep'
const blockMarker = '/* keep */'
// remove this line comment
const afterLine = true
/* remove this block comment */
const afterBlock = true
"""

    stripped = _without_javascript_comments(source)

    for literal in (
        "'http://localhost:8360/path//segment'",
        '"https://example.com/a/*literal*/b"',
        "'// keep'",
        "'/* keep */'",
    ):
        assert literal in stripped
    assert "remove this line comment" not in stripped
    assert "remove this block comment" not in stripped
    assert "const afterLine = true" in stripped
    assert "const afterBlock = true" in stripped


def _javascript_object_property(source: str, property_pattern: str) -> str:
    match = re.search(rf"(?:{property_pattern})\s*:\s*\{{", source)
    assert match is not None

    object_start = match.end() - 1
    depth = 0
    quote: str | None = None
    index = object_start

    while index < len(source):
        char = source[index]

        if quote is not None:
            if char == "\\" and index + 1 < len(source):
                index += 2
                continue
            if char == quote:
                quote = None
            index += 1
            continue

        if char in ("'", '"', "`"):
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[object_start + 1 : index]
        index += 1

    raise AssertionError(f"unclosed JavaScript object for {property_pattern!r}")


def _assert_runtime_config_uses_site_noindex_shorthand(config: str) -> None:
    assert re.search(
        r"\bconst\s+siteNoindex\s*=\s*process\.env\.NUXT_PUBLIC_SITE_NOINDEX\s*!==\s*"
        r"(?P<quote>['\"])false(?P=quote)",
        config,
    )
    runtime_config = _javascript_object_property(config, r"\bruntimeConfig\b")
    public_config = _javascript_object_property(runtime_config, r"\bpublic\b")
    assert "{" not in public_config and "}" not in public_config
    assert re.search(
        r"(?:^|,)\s*siteNoindex\s*(?=,|$)",
        public_config,
        flags=re.DOTALL,
    )


def _assert_nitro_catch_all_noindex_header(config: str) -> None:
    nitro = _javascript_object_property(config, r"\bnitro\b")
    route_rules = _javascript_object_property(nitro, r"\brouteRules\b")
    catch_all = _javascript_object_property(route_rules, r"['\"]/\*\*['\"]")
    headers = _javascript_object_property(catch_all, r"\bheaders\b")

    header_properties = re.findall(
        r"(?:['\"]X-Robots-Tag['\"]|\[\s*['\"]X-Robots-Tag['\"]\s*\])\s*:",
        headers,
    )
    assert len(header_properties) == 1
    assert re.search(
        r"\.\.\.\(\s*siteNoindex\s*\?\s*\{\s*"
        r"['\"]X-Robots-Tag['\"]\s*:\s*['\"]noindex,\s*follow['\"]\s*,?\s*"
        r"\}\s*:\s*\{\s*\}\s*\)",
        headers,
        flags=re.DOTALL,
    )


def test_runtime_config_guard_does_not_match_site_noindex_outside_public():
    config = _without_javascript_comments(
        """
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
    )

    with pytest.raises(AssertionError):
        _assert_runtime_config_uses_site_noindex_shorthand(config)


def test_nitro_guard_rejects_later_x_robots_tag_override():
    config = _without_javascript_comments(
        """
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
    )

    with pytest.raises(AssertionError):
        _assert_nitro_catch_all_noindex_header(config)


def test_global_noindex_default_and_authoritative_header_are_executable_code():
    config = _without_javascript_comments(
        (ROOT / "web-nuxt" / "nuxt.config.ts").read_text(encoding="utf-8")
    )
    middleware = _without_javascript_comments(
        (ROOT / "web-nuxt" / "server" / "middleware" / "noindex.ts").read_text(
            encoding="utf-8"
        )
    )

    _assert_runtime_config_uses_site_noindex_shorthand(config)
    assert re.search(
        r"\{\s*name\s*:\s*['\"]robots['\"]\s*,\s*"
        r"content\s*:\s*siteNoindex\s*\?\s*['\"]noindex,\s*follow['\"]\s*:\s*"
        r"['\"]index,\s*follow,\s*max-image-preview:large,\s*max-snippet:-1['\"]\s*,\s*\}",
        config,
        flags=re.DOTALL,
    )
    _assert_nitro_catch_all_noindex_header(config)
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
