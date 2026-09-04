from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pytest

from scripts.ops.record_launch_evidence import (
    MAX_TEXT,
    REQUIRED_SECTIONS,
    CommandEvidence,
    EvidenceDocument,
    main,
    _markdown_escape,
    record_section,
    resolve_harness_result,
    _output_digest,
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
            output = "1 passed in 0.1s\n"
            evidence = CommandEvidence(
                section,
                0,
                "passed",
                "pass",
                outcomes={
                    "passed": 1,
                    "failed": 0,
                    "errors": 0,
                    "skipped": 0,
                    "xfailed": 0,
                    "collection_errors": 0,
                    "interrupted": False,
                    "return_code": 0,
                    "failed_nodeids": [],
                    "error_nodeids": [],
                    "summary_present": True,
                },
                environment={"os": "test"},
                head_sha=revision if len(revision) == 40 and revision == revision.lower() else "",
                output_sha256=sha256(output.encode()).hexdigest(),
            )
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


def test_record_stores_versioned_outcomes_environment_head_and_output_checksum(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "metadata-state.json"
    output = "5 passed in 0.1s\n"
    record_section(
        "backend-focused",
        CommandEvidence("pytest -q", 0, "passed", "pass"),
        state_path,
        outcomes={"passed": 5, "failed": 0, "return_code": 0},
        environment={"python": "3.14", "os": "Windows"},
        head_sha="a" * 40,
        output=output,
        verdict="PASS",
    )

    payload = json.loads(state_path.read_text(encoding="utf-8"))
    section = payload["sections"]["backend-focused"]
    assert section["outcomes"]["passed"] == 5
    assert section["environment"]["os"] == "Windows"
    assert section["head_sha"] == "a" * 40
    assert section["output_sha256"]
    assert section["verdict"] == "PASS"


def test_command_evidence_keeps_layered_pilot_provenance_without_raw_subject_data() -> None:
    evidence = CommandEvidence(
        "python -m pytest tests/integration/test_cross_boundary_proof.py -q",
        0,
        "local fixture passed",
        "pass",
        nodeids=("tests/integration/test_cross_boundary_proof.py::test_gate",),
        layer="multi_process",
        owner="qa/release",
        rollback_note="No production mutation; fixture is disposable.",
    )

    assert evidence.layer == "multi_process"
    assert evidence.owner == "qa/release"
    assert evidence.nodeids == ("tests/integration/test_cross_boundary_proof.py::test_gate",)


def test_record_metadata_round_trip_preserves_layered_pilot_provenance(tmp_path: Path) -> None:
    state_path = tmp_path / "pilot-provenance.json"
    evidence = CommandEvidence(
        "python -m pytest tests/integration/test_cross_boundary_proof.py -q",
        0,
        "local fixture passed",
        "pass",
        nodeids=("tests/integration/test_cross_boundary_proof.py::test_gate",),
        layer="multi_process",
        owner="qa/release",
        rollback_note="No production mutation; fixture is disposable.",
    )
    document = EvidenceDocument.empty(state_path)
    document.record(
        "backend-focused",
        evidence,
        outcomes={"passed": 1, "failed": 0, "return_code": 0},
        environment={"os": "Windows"},
        head_sha="a" * 40,
        output="1 passed in 0.1s\n",
        verdict="PASS",
    )
    document.save()

    restored = EvidenceDocument.load(state_path).sections["backend-focused"]
    assert restored.layer == "multi_process"
    assert restored.nodeids == ("tests/integration/test_cross_boundary_proof.py::test_gate",)
    assert restored.owner == "qa/release"
    assert restored.rollback_note == "No production mutation; fixture is disposable."


def test_record_rejects_status_verdict_contradiction(tmp_path: Path) -> None:
    document = EvidenceDocument.empty(tmp_path / "state.json")
    with pytest.raises(ValueError, match="status.*verdict|verdict.*status"):
        document.record(
            "artifacts",
            CommandEvidence("pytest", 0, "passed", "pass", verdict="BLOCKED"),
        )


def test_output_digest_rejects_declared_hash_without_captured_bytes() -> None:
    with pytest.raises(ValueError, match="captured output"):
        _output_digest(None, "a" * 64)


def test_final_render_rejects_pass_status_with_blocked_outcomes(tmp_path: Path) -> None:
    document = _complete_document(tmp_path)
    outcomes = {
        "passed": 1, "failed": 0, "errors": 1, "skipped": 0,
        "xfailed": 0, "collection_errors": 0, "interrupted": False,
        "return_code": 1,
        "failed_nodeids": [], "error_nodeids": [], "summary_present": True,
    }
    document.record(
        "backend-focused",
        CommandEvidence(
            "pytest", 0, "passed", "pass",
            outcomes=outcomes,
            environment={"os": "test"},
            head_sha=document.revision,
        ),
    )
    with pytest.raises(ValueError, match="verdict is blocked"):
        document.render(final=True)


def test_final_render_and_bundle_reject_functional_pass_without_parsed_outcomes(
    tmp_path: Path,
) -> None:
    document = _complete_document(tmp_path)
    document.record(
        "backend-focused",
        CommandEvidence(
            "pytest", 0, "passed", "pass",
            environment={"os": "test"}, head_sha=document.revision,
        ),
    )
    with pytest.raises(ValueError, match="missing parsed outcomes"):
        document.render(final=True)
    with pytest.raises(ValueError, match="missing parsed outcomes"):
        document.write_bundle(tmp_path / "bundle.json")


def test_final_document_writes_bundle_verified_by_control_plane(tmp_path: Path) -> None:
    from agent.control_plane.evidence import verify_bundle

    document = _complete_document(tmp_path)
    bundle_path = tmp_path / "bundle.json"
    document.write_bundle(bundle_path)
    result = verify_bundle(bundle_path)
    assert result.verdict == "PASS"
    assert result.checked_sha256
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    assert "outcomes" not in bundle


def test_cli_unparseable_captured_output_is_unclassified_not_fabricated_pass(tmp_path: Path) -> None:
    state_path = tmp_path / "cli-unclassified.json"
    assert main([
        "record", "--section", "backend-focused", "--status", "pass",
        "--exit-code", "0", "--summary", "native", "--command", "command",
        "--output-text", "command completed", "--environment-json", '{"os":"test"}',
        "--head-sha", "a" * 40, "--state", str(state_path),
    ]) == 0
    section = json.loads(state_path.read_text(encoding="utf-8"))["sections"]["backend-focused"]
    assert section["status"] == "skip"
    assert section["verdict"] == "UNCLASSIFIED"
    assert section["outcomes"] == {}


def test_cli_unparseable_output_with_nonzero_exit_persists_blocked_failure(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "cli-unparseable-failure.json"
    assert main([
        "record", "--section", "backend-focused", "--status", "fail",
        "--exit-code", "7", "--summary", "native failure", "--command", "pytest",
        "--output-text", "command failed before pytest summary", "--environment-json", '{"os":"test"}',
        "--head-sha", "a" * 40, "--revision", "a" * 40, "--state", str(state_path),
    ]) == 0
    section = json.loads(state_path.read_text(encoding="utf-8"))["sections"]["backend-focused"]
    assert section["status"] == "fail"
    assert section["verdict"] == "BLOCKED"
    assert section["exit_code"] == 7
    assert section["outcomes"] == {}


def test_cli_unparseable_output_overrides_fabricated_outcomes_and_blocks_final(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "cli-fabricated.json"
    document = _complete_document(tmp_path)
    document.path = state_path
    document.save()
    fabricated = {
        "passed": 1,
        "failed": 0,
        "errors": 0,
        "skipped": 0,
        "xfailed": 0,
        "collection_errors": 0,
        "interrupted": False,
        "return_code": 0,
    }
    assert main([
        "record", "--section", "backend-focused", "--status", "pass",
        "--exit-code", "0", "--summary", "native", "--command", "pytest",
        "--output-text", "command completed", "--outcomes-json", json.dumps(fabricated),
        "--environment-json", '{"os":"test"}', "--head-sha", "a" * 40,
        "--revision", "a" * 40, "--state", str(state_path),
    ]) == 0
    section = json.loads(state_path.read_text(encoding="utf-8"))["sections"]["backend-focused"]
    assert section["status"] == "skip"
    assert section["verdict"] == "UNCLASSIFIED"
    assert section["outcomes"] == {}
    with pytest.raises(ValueError, match="functional section"):
        EvidenceDocument.load(state_path).render(final=True)


def test_cli_parses_real_output_into_errors_and_blocked_verdict(tmp_path: Path) -> None:
    state_path = tmp_path / "cli-state.json"
    output = "ERROR tests/a.py - ImportError\n1 passed, 1 error in 0.1s\n"
    assert main([
        "record", "--section", "backend-focused", "--status", "pass",
        "--exit-code", "1", "--summary", "native", "--command", "pytest",
        "--output-text", output, "--environment-json", '{"os":"test"}',
        "--head-sha", "a" * 40, "--state", str(state_path),
    ]) == 0
    payload = json.loads(state_path.read_text(encoding="utf-8"))
    section = payload["sections"]["backend-focused"]
    assert section["outcomes"]["errors"] == 1
    assert section["verdict"] == "BLOCKED"
    assert section["status"] == "fail"


def test_cli_parses_vitest_output_as_pass(tmp_path: Path) -> None:
    state_path = tmp_path / "vitest-state.json"
    output = "Test Files  1 passed (1)\n     Tests  91 passed (91)\n"
    assert main([
        "record", "--section", "frontend-focused", "--status", "pass",
        "--exit-code", "0", "--summary", "vitest", "--command", "npm test",
        "--output-text", output, "--environment-json", '{"os":"test"}',
        "--head-sha", "a" * 40, "--revision", "a" * 40, "--state", str(state_path),
    ]) == 0
    section = json.loads(state_path.read_text(encoding="utf-8"))["sections"]["frontend-focused"]
    assert section["status"] == "pass"
    assert section["verdict"] == "PASS"
    assert section["outcomes"]["passed"] == 91


def test_cli_records_native_rollback_output_without_fabricating_counts(tmp_path: Path) -> None:
    state_path = tmp_path / "rollback-state.json"
    assert main([
        "record", "--section", "rollback-local-rehearsal", "--status", "pass",
        "--exit-code", "0", "--summary", "rollback ok", "--command", "bash rollback",
        "--native-command", "--output-text", "rollback completed", "--environment-json", '{"os":"test"}',
        "--head-sha", "a" * 40, "--revision", "a" * 40, "--state", str(state_path),
    ]) == 0
    section = json.loads(state_path.read_text(encoding="utf-8"))["sections"]["rollback-local-rehearsal"]
    assert section["verdict"] == "PASS"
    assert section["outcomes"] == {
        "evidence_kind": "native-command", "summary_present": True, "return_code": 0,
    }


def test_native_skip_preserves_unclassified_and_empty_native_pass_blocks(tmp_path: Path) -> None:
    skip_state = tmp_path / "skip.json"
    assert main([
        "record", "--section", "browser-opt-in", "--status", "skip", "--exit-code", "0",
        "--summary", "chrome-unavailable", "--command", "node probe", "--native-command",
        "--environment-json", '{"os":"test"}', "--head-sha", "a" * 40,
        "--revision", "a" * 40, "--state", str(skip_state),
    ]) == 0
    section = json.loads(skip_state.read_text(encoding="utf-8"))["sections"]["browser-opt-in"]
    assert section["status"] == "skip" and section["verdict"] == "UNCLASSIFIED"
    pass_state = tmp_path / "pass.json"
    assert main([
        "record", "--section", "browser-opt-in", "--status", "pass", "--exit-code", "0",
        "--summary", "ok", "--command", "node probe", "--native-command",
        "--environment-json", '{"os":"test"}', "--head-sha", "a" * 40,
        "--revision", "a" * 40, "--state", str(pass_state),
    ]) == 0
    section = json.loads(pass_state.read_text(encoding="utf-8"))["sections"]["browser-opt-in"]
    assert section["status"] == "fail" and section["verdict"] == "BLOCKED"


@pytest.mark.parametrize(
    ("requested_status", "requested_verdict"),
    [("skip", None), ("fail", None), ("skip", "PASS"), ("fail", "PASS")],
)
def test_native_nonempty_capture_preserves_requested_nonpass_semantics(
    tmp_path: Path, requested_status: str, requested_verdict: str | None,
) -> None:
    state_path = tmp_path / f"native-{requested_status}-{requested_verdict or 'none'}.json"
    argv = [
        "record", "--section", "browser-opt-in", "--status", requested_status,
        "--exit-code", "0", "--summary", "native", "--command", "node probe",
        "--native-command", "--output-text", "probe completed", "--environment-json", '{"os":"test"}',
        "--head-sha", "a" * 40, "--revision", "a" * 40, "--state", str(state_path),
    ]
    if requested_verdict is not None:
        argv.extend(["--verdict", requested_verdict])
    assert main(argv) == 0
    section = json.loads(state_path.read_text(encoding="utf-8"))["sections"]["browser-opt-in"]
    expected_status = "skip" if requested_status == "skip" else "fail"
    expected_verdict = "UNCLASSIFIED" if requested_status == "skip" else "BLOCKED"
    assert section["status"] == expected_status
    assert section["verdict"] == expected_verdict


def test_browser_native_skip_with_empty_capture_remains_verifiable(tmp_path: Path) -> None:
    document = _complete_document(tmp_path)
    document.record(
        "browser-opt-in",
        CommandEvidence(
            "node probe", 0, "chrome-unavailable", "skip",
            outcomes={"evidence_kind": "native-command", "summary_present": False, "return_code": 0},
            environment={"os": "test"},
        ),
    )
    bundle_path = tmp_path / "browser-skip-bundle.json"
    document.write_bundle(bundle_path)
    from agent.control_plane.evidence import verify_bundle
    assert verify_bundle(bundle_path).verdict == "PASS"


def test_cli_rejects_non_utf8_native_capture_as_blocked(tmp_path: Path) -> None:
    output_path = tmp_path / "native.bin"
    output_path.write_bytes(b"rollback\xff")
    state_path = tmp_path / "native-invalid.json"
    assert main([
        "record", "--section", "rollback-local-rehearsal", "--status", "pass",
        "--exit-code", "0", "--summary", "rollback", "--command", "bash rollback",
        "--native-command", "--output-file", str(output_path), "--environment-json", '{"os":"test"}',
        "--head-sha", "a" * 40, "--revision", "a" * 40, "--state", str(state_path),
    ]) == 0
    section = json.loads(state_path.read_text(encoding="utf-8"))["sections"]["rollback-local-rehearsal"]
    assert section["status"] == "fail"
    assert section["verdict"] == "BLOCKED"


def test_harness_result_parses_captured_output_instead_of_fabricating_counts(tmp_path: Path) -> None:
    state_path = tmp_path / "harness-state.json"
    output_path = tmp_path / "compose-output.txt"
    output_path.write_text("3 passed in 0.1s\n", encoding="utf-8")
    assert main([
        "harness-result", "--section", "compose-nginx-opt-in",
        "--primary-exit", "0", "--cleanup-exit", "0",
        "--head-sha", "a" * 40, "--environment-json", '{"os":"test"}',
        "--output-file", str(output_path), "--state", str(state_path),
    ]) == 0
    payload = json.loads(state_path.read_text(encoding="utf-8"))
    section = payload["sections"]["compose-nginx-opt-in"]
    assert section["outcomes"]["passed"] == 3
    assert section["verdict"] == "PASS"
    assert section["output_sha256"]


def test_harness_result_without_parseable_output_is_unclassified(tmp_path: Path) -> None:
    state_path = tmp_path / "harness-unclassified.json"
    output_path = tmp_path / "compose-output.txt"
    output_path.write_text("docker compose completed\n", encoding="utf-8")
    assert main([
        "harness-result", "--section", "compose-nginx-opt-in",
        "--primary-exit", "0", "--cleanup-exit", "0",
        "--head-sha", "a" * 40, "--environment-json", '{"os":"test"}',
        "--output-file", str(output_path), "--state", str(state_path),
    ]) == 0
    payload = json.loads(state_path.read_text(encoding="utf-8"))
    section = payload["sections"]["compose-nginx-opt-in"]
    assert section["verdict"] == "UNCLASSIFIED"
    assert section["status"] == "skip"


def test_harness_result_unparseable_nonzero_exit_persists_blocked_failure(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "harness-unparseable-failure.json"
    output_path = tmp_path / "compose-output.txt"
    output_path.write_text("docker compose failed\n", encoding="utf-8")
    assert main([
        "harness-result", "--section", "compose-nginx-opt-in",
        "--primary-exit", "7", "--cleanup-exit", "0",
        "--head-sha", "a" * 40, "--environment-json", '{"os":"test"}',
        "--output-file", str(output_path), "--state", str(state_path),
    ]) == 7
    section = json.loads(state_path.read_text(encoding="utf-8"))["sections"]["compose-nginx-opt-in"]
    assert section["status"] == "fail"
    assert section["verdict"] == "BLOCKED"
    assert section["exit_code"] == 7
    assert section["outcomes"] == {}


def test_final_render_blocks_compose_pass_without_capture_metadata(tmp_path: Path) -> None:
    document = _complete_document(tmp_path)
    document.record(
        "compose-nginx-opt-in",
        CommandEvidence("docker compose up", 0, "passed", "pass"),
    )
    with pytest.raises(ValueError, match="compose-nginx-opt-in.*metadata|metadata.*compose-nginx-opt-in"):
        document.render(final=True)


def test_final_render_blocks_browser_pass_without_capture_metadata(tmp_path: Path) -> None:
    document = _complete_document(tmp_path)
    document.record(
        "browser-opt-in",
        CommandEvidence("node probe", 0, "passed", "pass"),
    )
    with pytest.raises(ValueError, match="browser-opt-in.*metadata|metadata.*browser-opt-in"):
        document.render(final=True)


def test_final_render_blocks_browser_pass_with_blocked_parsed_outcomes(tmp_path: Path) -> None:
    document = _complete_document(tmp_path)
    output = "1 failed, 0 passed in 0.1s\n"
    document.record(
        "browser-opt-in",
        CommandEvidence(
            "node probe", 0, "failed", "pass",
            outcomes={
                "passed": 0, "failed": 1, "errors": 0, "skipped": 0,
                "xfailed": 0, "collection_errors": 0, "interrupted": False,
                "return_code": 0, "failed_nodeids": [], "error_nodeids": [],
                "summary_present": True,
            },
            environment={"os": "test"}, head_sha=document.revision,
            output_sha256=sha256(output.encode()).hexdigest(),
        ),
    )
    with pytest.raises(ValueError, match="browser-opt-in.*metadata|verdict|blocked"):
        document.render(final=True)


def test_final_render_blocks_parsed_outcomes_without_output_checksum(tmp_path: Path) -> None:
    document = _complete_document(tmp_path)
    document.record(
        "backend-focused",
        CommandEvidence(
            "pytest", 0, "passed", "pass",
            outcomes={
                "passed": 1, "failed": 0, "errors": 0, "skipped": 0,
                "xfailed": 0, "collection_errors": 0, "interrupted": False,
                "return_code": 0,
                "failed_nodeids": [], "error_nodeids": [], "summary_present": True,
            },
            environment={"os": "test"},
            head_sha=document.revision,
        ),
    )
    with pytest.raises(ValueError, match="checksum"):
        document.render(final=True)


def test_command_evidence_does_not_silently_truncate_exact_command() -> None:
    command = "pytest " + ("x" * 600)
    with pytest.raises(ValueError, match="command"):
        CommandEvidence(command, 0, "passed", "pass")


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
            output = "1 passed in 0.1s\n"
            evidence = CommandEvidence(
                section,
                0,
                "passed",
                "pass",
                outcomes={
                    "passed": 1, "failed": 0, "errors": 0, "skipped": 0,
                    "xfailed": 0, "collection_errors": 0, "interrupted": False,
                    "return_code": 0,
                    "failed_nodeids": [], "error_nodeids": [], "summary_present": True,
                },
                environment={"os": "test"},
                head_sha=document.revision,
                output_sha256=sha256(output.encode()).hexdigest(),
            )
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
