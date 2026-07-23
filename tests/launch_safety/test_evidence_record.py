from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.ops.record_launch_evidence import (
    MAX_TEXT,
    REQUIRED_SECTIONS,
    CommandEvidence,
    EvidenceDocument,
    _markdown_escape,
    record_section,
    resolve_harness_result,
)


def _complete_document(tmp_path: Path, *, revision: str = "a" * 40) -> EvidenceDocument:
    document = EvidenceDocument.empty(tmp_path / "state.json")
    document.revision = revision
    for section in REQUIRED_SECTIONS:
        if section == "external-gates":
            evidence = CommandEvidence(
                "external authorization",
                0,
                "H1=blocked; H2=blocked; owner=not-authorized",
                "skip",
            )
        elif section in {"postgres-opt-in", "compose-nginx-opt-in"}:
            evidence = CommandEvidence(section, 0, "docker-cli-unavailable", "skip")
        elif section == "browser-opt-in":
            evidence = CommandEvidence(section, 0, "chrome-unavailable", "skip")
        elif section == "known-resource-timeout":
            evidence = CommandEvidence(section, 0, "not observed", "skip")
        else:
            evidence = CommandEvidence(section, 0, "passed", "pass")
        document.record(section, evidence)
    return document


def test_evidence_document_requires_all_gate_sections(tmp_path: Path) -> None:
    document = EvidenceDocument.empty(tmp_path / "state.json")

    assert set(REQUIRED_SECTIONS) == {
        "artifacts",
        "backend-focused",
        "frontend-focused",
        "postgres-opt-in",
        "compose-nginx-opt-in",
        "browser-opt-in",
        "rollback-local-rehearsal",
        "backend-full-regression",
        "frontend-serial-regression",
        "source-scans",
        "known-resource-timeout",
        "external-gates",
    }
    assert document.external_gates == {
        "H1": "blocked",
        "H2": "blocked",
        "owner": "not-authorized",
    }


@pytest.mark.parametrize(
    ("primary_exit", "cleanup_exit", "expected_exit"),
    [(0, 0, 0), (0, 9, 9), (37, 0, 37), (37, 9, 37)],
)
def test_harness_exit_preserves_primary_failure_and_surfaces_cleanup_failure(
    primary_exit: int, cleanup_exit: int, expected_exit: int
) -> None:
    result = resolve_harness_result(
        primary_exit=primary_exit, cleanup_exit=cleanup_exit
    )

    assert result.exit_code == expected_exit
    assert result.primary_status == ("pass" if primary_exit == 0 else "fail")
    assert result.cleanup_status == ("pass" if cleanup_exit == 0 else "fail")


def test_record_upserts_section_and_final_render_rejects_missing_sections(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    document = EvidenceDocument.empty(state_path)
    document.record(
        "artifacts",
        CommandEvidence("python -m pytest", 0, "artifact checks", "pass"),
    )
    document.record(
        "artifacts",
        CommandEvidence("python -m pytest", 0, "artifact checks rerun", "pass"),
    )
    document.save()

    payload = json.loads(state_path.read_text(encoding="utf-8"))
    assert len(payload["sections"]) == 1
    assert payload["sections"]["artifacts"]["summary"] == "artifact checks rerun"
    with pytest.raises(ValueError, match="missing evidence sections"):
        document.render(final=True)


def test_record_section_persists_the_clean_head_revision(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"

    record_section(
        "artifacts",
        CommandEvidence("pytest artifacts", 0, "passed", "pass"),
        state_path,
        revision="09510487598f50488475a3f2d62d07a3fb337938",
    )

    document = EvidenceDocument.load(state_path)
    assert document.revision == "09510487598f50488475a3f2d62d07a3fb337938"
    assert "> Revision: 09510487598f50488475a3f2d62d07a3fb337938" in document.render()


def test_final_render_rejects_not_requested_opt_in_and_accepts_explicit_skip(tmp_path: Path) -> None:
    document = EvidenceDocument.empty(tmp_path / "state.json")
    document.revision = "a" * 40
    for section in REQUIRED_SECTIONS:
        if section == "external-gates":
            evidence = CommandEvidence(
                "external authorization", 0, "H1=blocked; H2=blocked; owner=not-authorized", "skip"
            )
        elif section in {"postgres-opt-in", "compose-nginx-opt-in", "browser-opt-in"}:
            evidence = CommandEvidence("not requested", 0, "not-requested", "skip")
        else:
            evidence = CommandEvidence(section, 0, "passed", "pass")
        document.record(section, evidence)

    with pytest.raises(ValueError, match="not-requested"):
        document.render(final=True)

    for section in {"postgres-opt-in", "compose-nginx-opt-in"}:
        document.record(
            section,
            CommandEvidence(section, 0, "docker-cli-unavailable", "skip"),
        )
    document.record(
        "browser-opt-in",
        CommandEvidence("browser-opt-in", 0, "chrome-unavailable", "skip"),
    )
    rendered = document.render(final=True)
    assert "> STATUS: pass" in rendered
    assert "five-minute SLA" not in rendered
    assert "deploy" not in rendered.lower()


@pytest.mark.parametrize("status", ["pass", "skip"])
def test_pass_and_skip_evidence_require_zero_exit(status: str) -> None:
    with pytest.raises(ValueError, match="exit_code must be 0"):
        CommandEvidence("pytest", 7, "bad", status)  # type: ignore[arg-type]


@pytest.mark.parametrize("revision", ["", "   ", "unknown", "UNKNOWN"])
def test_final_render_rejects_empty_or_unknown_revision(
    tmp_path: Path, revision: str
) -> None:
    document = _complete_document(tmp_path, revision=revision)
    with pytest.raises(ValueError, match="revision"):
        document.render(final=True)


def test_record_rejects_revision_mismatch(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "revision-state.json"
    record_section(
        "artifacts",
        CommandEvidence("pytest", 0, "passed", "pass"),
        state_path,
        revision="a" * 40,
    )
    with pytest.raises(ValueError, match="revision mismatch"):
        record_section(
            "backend-focused",
            CommandEvidence("pytest", 0, "passed", "pass"),
            state_path,
            revision="b" * 40,
        )


@pytest.mark.parametrize(
    ("section", "reason"),
    [
        ("postgres-opt-in", "chrome-unavailable"),
        ("compose-nginx-opt-in", "chrome-unavailable"),
        ("browser-opt-in", "docker-cli-unavailable"),
        ("browser-opt-in", "docker-daemon-unavailable"),
        ("browser-opt-in", "not-requested"),
    ],
)
def test_final_render_enforces_section_specific_opt_in_skip_reason(
    tmp_path: Path, section: str, reason: str
) -> None:
    document = _complete_document(tmp_path)
    document.record(section, CommandEvidence(section, 0, reason, "skip"))

    with pytest.raises(ValueError, match="invalid skip reason"):
        document.render(final=True)


def test_failed_timeout_row_cannot_render_final_pass(tmp_path: Path) -> None:
    document = _complete_document(tmp_path)
    document.record(
        "known-resource-timeout",
        CommandEvidence("parallel suite", 9, "resource timeout", "fail"),
    )

    with pytest.raises(ValueError, match="failed evidence section"):
        document.render(final=True)


@pytest.mark.parametrize(
    ("status", "summary"),
    [
        ("pass", "H1=blocked; H2=blocked; owner=not-authorized"),
        ("skip", "H1=open; H2=blocked; owner=not-authorized"),
        ("skip", "H1=blocked; H2=blocked; owner=authorized"),
    ],
)
def test_external_gates_are_exact_informational_evidence(
    tmp_path: Path, status: str, summary: str
) -> None:
    document = _complete_document(tmp_path)
    document.record(
        "external-gates",
        CommandEvidence("external gates", 0, summary, status),  # type: ignore[arg-type]
    )

    with pytest.raises(ValueError, match="external gates"):
        document.render(final=True)


def test_empty_external_gate_mapping_is_not_replaced_by_defaults(tmp_path: Path) -> None:
    complete = _complete_document(tmp_path)
    document = EvidenceDocument(
        tmp_path / "tampered.json",
        sections=complete.sections,
        external_gates={},
        revision="a" * 40,
    )

    with pytest.raises(ValueError, match="external gates"):
        document.render(final=True)


def test_reviewer_payload_cannot_render_final_pass(tmp_path: Path) -> None:
    document = _complete_document(tmp_path, revision="unknown")
    document.record(
        "postgres-opt-in",
        CommandEvidence("postgres", 0, "chrome-unavailable", "skip"),
    )
    document.record(
        "known-resource-timeout",
        CommandEvidence("parallel suite", 9, "resource timeout", "fail"),
    )
    document.external_gates = {"H1": "open", "H2": "blocked", "owner": "not-authorized"}
    document.sections["external-gates"] = CommandEvidence(
        "external gates", 0, "H1=open; H2=blocked; owner=not-authorized", "pass"
    )

    with pytest.raises(ValueError, match="revision|external|skip reason|timeout"):
        document.render(final=True)


def test_known_timeout_cannot_hide_functional_failure(tmp_path: Path) -> None:
    document = _complete_document(tmp_path)
    document.record(
        "backend-focused",
        CommandEvidence("pytest backend", 9, "functional failure", "fail"),
    )
    with pytest.raises(ValueError, match="functional section"):
        document.render(final=True)


def test_evidence_redacts_userinfo_secret_args_and_escapes_markdown(tmp_path: Path) -> None:
    evidence = CommandEvidence(
        "curl postgresql://alice:s3cr3t@example.test/db https://alice:s3cr3t@example.test/path "
        "--token=topsecret --password hunter2 --client-secret\nsplit-secret",
        0,
        "first|`second`\r\nthird; api-key=another-secret",
        "pass",
    )
    document = EvidenceDocument.empty(tmp_path / "state.json")
    document.record("artifacts", evidence)
    rendered = document.render()

    assert "s3cr3t" not in rendered
    assert "topsecret" not in rendered
    assert "hunter2" not in rendered
    assert "split-secret" not in rendered
    assert "another-secret" not in rendered
    assert "first\\|\\`second\\`\\nthird" in rendered
    assert "https://[redacted]@example.test/path" in rendered
    assert "postgresql://[redacted]@example.test/db" in rendered


def test_markdown_escaping_preserves_the_text_bound() -> None:
    escaped = _markdown_escape("`|" * MAX_TEXT)

    assert len(escaped) <= MAX_TEXT
    assert not escaped.endswith("\\")


def test_release_gate_exposes_independent_opt_in_switches_without_default_startup() -> None:
    gate = Path(__file__).resolve().parents[2] / "scripts" / "release_gate.ps1"
    source = gate.read_text(encoding="utf-8")

    assert "RunLaunchSafetyDockerOptIn" in source
    assert "RunLaunchSafetyBrowserOptIn" in source
    assert "Invoke-RecordedComposeHarness" in source
    assert "--probe-browser" in source
    assert "if ($RunLaunchSafetyDockerOptIn" in source
    assert "if ($RunLaunchSafetyBrowserOptIn" in source


def test_release_gate_records_default_sections_and_renders_canonical_result() -> None:
    gate = Path(__file__).resolve().parents[2] / "scripts" / "release_gate.ps1"
    source = gate.read_text(encoding="utf-8")

    assert "Invoke-LaunchSafetyRequiredEvidence" in source
    for section in {
        "artifacts",
        "backend-focused",
        "frontend-focused",
        "rollback-local-rehearsal",
        "backend-full-regression",
        "frontend-serial-regression",
        "source-scans",
        "known-resource-timeout",
        "external-gates",
    }:
        assert f'"{section}"' in source
    assert "RenderLaunchSafetyFinalEvidence" in source
    assert "docs/superpowers/results/2026-07-20-launch-safety-gate-evidence.md" in source
    assert '"render", "--final"' in source
    assert '"--output", $evidenceOutput' in source


def test_release_gate_uses_resolved_bash_and_fails_closed_when_unavailable() -> None:
    gate = Path(__file__).resolve().parents[2] / "scripts" / "release_gate.ps1"
    source = gate.read_text(encoding="utf-8")

    assert '. (Join-Path $Root "scripts/ops/release_gate_harness.ps1")' in source
    assert "$bashAuthority = Resolve-LaunchSafetyBash" in source
    assert '& "bash"' not in source
    assert '"bash-interpreter-unavailable"' in source
    assert '"rollback-local-rehearsal" "skip"' in source


def test_release_gate_requires_clean_head_before_docker_prerequisites() -> None:
    gate = Path(__file__).resolve().parents[2] / "scripts" / "release_gate.ps1"
    source = gate.read_text(encoding="utf-8")

    clean_head = source.index("git status --porcelain --untracked-files=all")
    docker_lookup = source.index("Get-Command docker")
    compose_start = source.index("Invoke-RecordedComposeHarness")

    assert clean_head < docker_lookup < compose_start


def test_release_gate_owns_a_fresh_default_state_and_records_each_omitted_opt_in() -> None:
    gate = Path(__file__).resolve().parents[2] / "scripts" / "release_gate.ps1"
    source = gate.read_text(encoding="utf-8")

    assert "LaunchSafetyEvidenceStateOwned" in source
    assert "[guid]::NewGuid()" in source
    assert 'if (-not $RunLaunchSafetyDockerOptIn -and' in source
    assert 'if (-not $RunLaunchSafetyBrowserOptIn -and' in source
    assert source.count('"not-requested"') >= 3


def test_release_gate_preserves_browser_primary_cleanup_recorder_exit_code() -> None:
    gate = Path(__file__).resolve().parents[2] / "scripts" / "release_gate.ps1"
    source = gate.read_text(encoding="utf-8")

    assert "Invoke-LaunchSafetyBrowserHarness" in source
    assert "$Script:LaunchSafetyOptInExit" in source
    assert "exit $Script:LaunchSafetyOptInExit" in source
    assert 'Data["ExitCode"] = [int]$LASTEXITCODE' in source
    render = source.index("function Invoke-LaunchSafetyFinalRender")
    render_opt_in_guard = source.index(
        "if ($Script:LaunchSafetyOptInExit -ne 0)", render
    )
    render_command = source.index('"render", "--final"', render)
    assert render_opt_in_guard < render_command


def test_release_gate_preserves_native_exit_codes_for_evidence_sections() -> None:
    gate = Path(__file__).resolve().parents[2] / "scripts" / "release_gate.ps1"
    source = gate.read_text(encoding="utf-8")

    assert 'Data["ExitCode"] = [int]$code' in source
