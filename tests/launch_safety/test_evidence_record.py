from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.ops.record_launch_evidence import (
    REQUIRED_SECTIONS,
    CommandEvidence,
    EvidenceDocument,
    record_section,
    resolve_harness_result,
)


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

    for section in {"postgres-opt-in", "compose-nginx-opt-in", "browser-opt-in"}:
        document.record(
            section,
            CommandEvidence(section, 0, "docker-cli-unavailable", "skip"),
        )
    rendered = document.render(final=True)
    assert "> STATUS: pass" in rendered
    assert "five-minute SLA" not in rendered
    assert "deploy" not in rendered.lower()


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


def test_release_gate_requires_clean_head_before_docker_prerequisites() -> None:
    gate = Path(__file__).resolve().parents[2] / "scripts" / "release_gate.ps1"
    source = gate.read_text(encoding="utf-8")

    clean_head = source.index("git status --porcelain --untracked-files=all")
    docker_lookup = source.index("Get-Command docker")
    compose_start = source.index("Invoke-RecordedComposeHarness")

    assert clean_head < docker_lookup < compose_start
