from __future__ import annotations

import json
from hashlib import sha256
import importlib.util
from pathlib import Path

import pytest

from agent import launch_evidence
from agent.control_plane.evidence import (
    classify_verdict,
    parse_pytest_output,
    parse_test_output,
    verify_bundle,
)
from scripts.ops.record_launch_evidence import CommandEvidence, EvidenceDocument, REQUIRED_SECTIONS


def test_launch_evidence_exposes_versioned_hash_helpers() -> None:
    assert launch_evidence.EVIDENCE_SCHEMA_VERSION == "1"
    assert len(launch_evidence.evidence_output_sha256("ok")) == 64


def _load_verifier():
    path = Path(__file__).resolve().parents[2] / "scripts" / "ops" / "verify_release_bundle.py"
    spec = importlib.util.spec_from_file_location("verify_release_bundle_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_error_and_nonzero_return_code_block_even_without_failed_lines() -> None:
    outcome = parse_pytest_output(
        "collected 2 items\nERROR tests/a.py - ImportError\n1 passed, 1 error in 0.2s\n",
        return_code=1,
    )
    assert outcome.errors == 1
    assert outcome.error_nodeids == ("tests/a.py",)
    assert classify_verdict(outcome, frozenset()) == "BLOCKED"


def test_error_nodeid_blocks_when_summary_under_reports_zero_errors() -> None:
    outcome = parse_pytest_output(
        "ERROR at setup of tests/a.py\n1 passed, 0 errors in 0.1s\n",
        return_code=0,
    )
    assert outcome.error_nodeids == ("tests/a.py",)
    assert outcome.errors == 1
    assert classify_verdict(outcome, frozenset()) == "BLOCKED"


def test_normal_collecting_progress_is_not_a_collection_error() -> None:
    outcome = parse_pytest_output(
        "collecting ... collected 2 items\n2 passed in 0.1s\n",
        return_code=0,
    )
    assert outcome.collection_errors == 0
    assert classify_verdict(outcome, frozenset()) == "PASS"


def test_vitest_summary_is_parsed_as_clean_test_evidence() -> None:
    outcome = parse_test_output(
        "Test Files  1 passed (1)\n     Tests  91 passed (91)\n",
        return_code=0,
    )
    assert outcome.summary_present is True
    assert outcome.passed == 91
    assert outcome.failed == 0
    assert classify_verdict(outcome, frozenset()) == "PASS"


def test_error_collecting_line_is_a_collection_error() -> None:
    outcome = parse_pytest_output(
        "ERROR collecting tests/a.py\n0 passed, 1 error in 0.1s\n",
        return_code=1,
    )
    assert outcome.collection_errors == 1
    assert classify_verdict(outcome, frozenset()) == "BLOCKED"


def test_clean_allowlisted_failure_is_pass_but_collection_error_is_not() -> None:
    clean = parse_pytest_output("1 failed, 4 passed in 0.1s\n", return_code=1)
    assert classify_verdict(clean, frozenset({"tests/known.py::test_old"})) == "BLOCKED"
    assert classify_verdict(clean, frozenset()) == "BLOCKED"
    assert classify_verdict(parse_pytest_output("5 passed in 0.1s\n", return_code=0), frozenset()) == "PASS"


def test_parser_collects_counts_nodeids_and_interrupted_marker() -> None:
    output = """collected 4 items
tests/a.py::test_ok PASSED
tests/b.py::test_bad FAILED
FAILED tests/b.py::test_bad
ERROR tests/c.py - SyntaxError
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! KeyboardInterrupt !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
1 failed, 1 passed, 1 skipped, 1 xfailed, 1 error in 0.2s
"""
    outcome = parse_pytest_output(output, return_code=2)
    assert outcome.passed == 1
    assert outcome.failed == 1
    assert outcome.errors == 1
    assert outcome.skipped == 1
    assert outcome.xfailed == 1
    assert outcome.interrupted is True
    assert outcome.failed_nodeids == ("tests/b.py::test_bad",)
    assert outcome.error_nodeids == ("tests/c.py",)


def test_missing_summary_is_unclassified() -> None:
    outcome = parse_pytest_output("tests/a.py::test_ok PASSED\n", return_code=0)
    assert classify_verdict(outcome, frozenset()) == "UNCLASSIFIED"


def test_verify_bundle_checks_schema_and_output_digest(tmp_path: Path) -> None:
    output = "5 passed in 0.1s\n"
    bundle = {
        "schema_version": "1",
        "artifact_id": "run-1",
        "head_sha": "a" * 40,
        "branch": "codex/test",
        "started_at": "2026-08-31T00:00:00Z",
        "finished_at": "2026-08-31T00:00:01Z",
        "command": "python -m pytest",
        "environment": {"os": "Windows", "python": "3.12", "pytest": "8"},
        "outcomes": {
            "passed": 5,
            "failed": 0,
            "errors": 0,
            "skipped": 0,
            "xfailed": 0,
            "collection_errors": 0,
            "interrupted": False,
            "return_code": 0,
        },
        "allowlist": [],
        "verdict": "PASS",
        "artifacts": [],
        "output": output,
        "output_sha256": sha256(output.encode()).hexdigest(),
    }
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(bundle), encoding="utf-8")
    result = verify_bundle(path)
    assert result.verdict == "PASS"
    assert result.checked_sha256 == bundle["output_sha256"]
    assert result.reasons == ()


def test_verify_bundle_treats_tampering_as_blocked(tmp_path: Path) -> None:
    path = tmp_path / "bundle.json"
    path.write_text("{}", encoding="utf-8")
    result = verify_bundle(path)
    assert result.verdict == "BLOCKED"
    assert result.reasons


def test_verify_bundle_rejects_declared_pass_when_stored_output_is_failed(tmp_path: Path) -> None:
    output = "1 failed in 0.1s\n"
    bundle = {
        "schema_version": "1", "artifact_id": "run", "head_sha": "a" * 40,
        "branch": "main", "started_at": "2026-08-31T00:00:00Z", "finished_at": "2026-08-31T00:00:01Z",
        "command": "pytest", "environment": {"os": "test"},
        "outcomes": {"passed": 0, "failed": 0, "errors": 0, "skipped": 0, "xfailed": 0,
                     "collection_errors": 0, "interrupted": False, "return_code": 0},
        "allowlist": [], "verdict": "PASS", "artifacts": [], "output": output,
        "output_sha256": sha256(output.encode()).hexdigest(),
    }
    path = tmp_path / "tampered.json"
    path.write_text(json.dumps(bundle), encoding="utf-8")
    result = verify_bundle(path)
    assert result.verdict == "BLOCKED"
    assert any("outcomes" in reason for reason in result.reasons)


def test_verifier_cli_maps_verdict_to_exit_code_and_prints_reasons(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    verifier = _load_verifier()
    path = tmp_path / "bundle.json"
    path.write_text("{}", encoding="utf-8")
    assert verifier.main(["--bundle", str(path)]) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["verdict"] == "BLOCKED"
    assert payload["reasons"]


@pytest.mark.parametrize("raw", ["null", "1", "[]"])
def test_non_object_json_bundle_is_blocked_without_traceback(tmp_path: Path, raw: str) -> None:
    path = tmp_path / "invalid.json"
    path.write_text(raw, encoding="utf-8")
    result = verify_bundle(path)
    assert result.verdict == "BLOCKED"
    assert result.reasons


def test_allowlist_requires_exact_nodeid_not_parent_prefix() -> None:
    outcome = parse_pytest_output(
        "tests/known.py::test_oldish FAILED\n1 failed in 0.1s\n", return_code=1
    )
    assert classify_verdict(outcome, frozenset({"tests/known.py::test_old"})) == "BLOCKED"


def test_bundle_requires_nonempty_timestamps_and_metadata_types(tmp_path: Path) -> None:
    output = "1 passed in 0.1s\n"
    bundle = {
        "schema_version": "1", "artifact_id": "run", "head_sha": "a" * 40,
        "branch": "main", "started_at": "", "finished_at": "",
        "command": "pytest", "environment": {}, "outcomes": {
            "passed": 1, "failed": 0, "errors": 0, "skipped": 0,
            "xfailed": 0, "collection_errors": 0, "interrupted": False, "return_code": 0,
        }, "allowlist": [], "verdict": "PASS", "artifacts": [],
        "output": output, "output_sha256": sha256(output.encode()).hexdigest(),
    }
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(bundle), encoding="utf-8")
    result = verify_bundle(path)
    assert result.verdict == "BLOCKED"


@pytest.mark.parametrize("raw_output_path", ["\x00pytest-output.txt", "../outside.txt", "missing.txt"])
def test_bundle_malformed_output_path_is_blocked_without_traceback(
    tmp_path: Path, raw_output_path: str
) -> None:
    bundle = {
        "schema_version": "1", "artifact_id": "run", "head_sha": "a" * 40,
        "branch": "main", "started_at": "2026-08-31T00:00:00Z",
        "finished_at": "2026-08-31T00:00:01Z", "command": "pytest",
        "environment": {"os": "test"},
        "outcomes": {
            "passed": 1, "failed": 0, "errors": 0, "skipped": 0,
            "xfailed": 0, "collection_errors": 0, "interrupted": False,
            "return_code": 0,
        },
        "allowlist": [], "verdict": "PASS", "artifacts": [],
        "output_path": raw_output_path, "output_sha256": "0" * 64,
    }
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(bundle), encoding="utf-8")
    result = verify_bundle(path)
    assert result.verdict == "BLOCKED"
    assert result.reasons


def test_bundle_rejects_inline_output_with_secondary_output_path(tmp_path: Path) -> None:
    output = "1 passed in 0.1s\n"
    bundle = {
        "schema_version": "1", "artifact_id": "run", "head_sha": "a" * 40,
        "branch": "main", "started_at": "2026-08-31T00:00:00Z",
        "finished_at": "2026-08-31T00:00:01Z", "command": "pytest",
        "environment": {"os": "test"},
        "outcomes": {
            "passed": 1, "failed": 0, "errors": 0, "skipped": 0,
            "xfailed": 0, "collection_errors": 0, "interrupted": False,
            "return_code": 0,
        },
        "allowlist": [], "verdict": "PASS", "artifacts": [],
        "output": output, "output_path": "../outside.txt",
        "output_sha256": sha256(output.encode()).hexdigest(),
    }
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(bundle), encoding="utf-8")
    result = verify_bundle(path)
    assert result.verdict == "BLOCKED"
    assert any("both inline output" in reason for reason in result.reasons)


def test_verify_bundle_reparses_stored_output_and_nodeids(tmp_path: Path) -> None:
    output = "tests/a.py::test_bad FAILED\n1 failed in 0.1s\n"
    bundle = {
        "schema_version": "1", "artifact_id": "run", "head_sha": "a" * 40,
        "branch": "main", "started_at": "2026-08-31T00:00:00Z", "finished_at": "2026-08-31T00:00:01Z",
        "command": "pytest", "environment": {"os": "test"},
        "outcomes": {"passed": 0, "failed": 1, "errors": 0, "skipped": 0, "xfailed": 0,
                     "collection_errors": 0, "interrupted": False, "return_code": 1,
                     "failed_nodeids": ["tests/other.py::test_bad"], "error_nodeids": []},
        "allowlist": [], "verdict": "BLOCKED", "artifacts": [], "output": output,
        "output_sha256": sha256(output.encode()).hexdigest(),
    }
    path = tmp_path / "nodeid-tampered.json"
    path.write_text(json.dumps(bundle), encoding="utf-8")
    result = verify_bundle(path)
    assert result.verdict == "BLOCKED"
    assert any("outcomes" in reason or "nodeid" in reason for reason in result.reasons)


def test_verify_bundle_reparses_output_file_with_declared_return_code(tmp_path: Path) -> None:
    output = "1 failed in 0.1s\n"
    output_path = tmp_path / "pytest-output.txt"
    output_path.write_bytes(output.encode())
    bundle = {
        "schema_version": "1", "artifact_id": "run", "head_sha": "a" * 40,
        "branch": "main", "started_at": "2026-08-31T00:00:00Z", "finished_at": "2026-08-31T00:00:01Z",
        "command": "pytest", "environment": {"os": "test"},
        "outcomes": {"passed": 1, "failed": 0, "errors": 0, "skipped": 0, "xfailed": 0,
                     "collection_errors": 0, "interrupted": False, "return_code": 0},
        "allowlist": [], "verdict": "PASS", "artifacts": [],
        "output_path": output_path.name,
        "output_sha256": sha256(output.encode()).hexdigest(),
    }
    path = tmp_path / "output-file-tampered.json"
    path.write_text(json.dumps(bundle), encoding="utf-8")
    result = verify_bundle(path)
    assert result.verdict == "BLOCKED"
    assert any("outcomes" in reason for reason in result.reasons)


def test_state_bundle_rejects_blocked_outcomes_even_when_state_checksum_matches(tmp_path: Path) -> None:
    state = {
        "version": 1,
        "revision": "a" * 40,
        "external_gates": {"H1": "blocked", "H2": "blocked", "owner": "not-authorized"},
        "sections": {
            "backend-focused": {
                "command": "pytest",
                "exit_code": 0,
                "summary": "passed",
                "status": "pass",
                "outcomes": {
                    "passed": 1, "failed": 0, "errors": 1, "skipped": 0,
                    "xfailed": 0, "collection_errors": 0, "interrupted": False,
                    "return_code": 1,
                },
                "environment": {"os": "test"},
                "head_sha": "a" * 40,
                "output_sha256": "b" * 64,
                "verdict": "PASS",
            }
        },
    }
    canonical = json.dumps(state, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    digest = sha256(canonical.encode()).hexdigest()
    bundle = {
        "bundle_kind": "launch-safety-state-v1",
        "state": state,
        "state_sha256": digest,
        "output_sha256": digest,
    }
    path = tmp_path / "state-tampered.json"
    path.write_text(json.dumps(bundle), encoding="utf-8")
    result = verify_bundle(path)
    assert result.verdict == "BLOCKED"


def test_state_bundle_binds_top_level_revision_and_artifacts_to_state(tmp_path: Path) -> None:
    document = EvidenceDocument.empty(tmp_path / "state.json")
    document.revision = "a" * 40
    for section in REQUIRED_SECTIONS:
        if section == "external-gates":
            evidence = CommandEvidence(
                section, 0, "H1=blocked; H2=blocked; owner=not-authorized", "skip"
            )
        elif section in {"postgres-opt-in", "compose-nginx-opt-in", "browser-opt-in"}:
            evidence = CommandEvidence(
                section, 0, "docker-cli-unavailable" if section != "browser-opt-in" else "chrome-unavailable", "skip"
            )
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
                    "failed_nodeids": [], "error_nodeids": [],
                    "summary_present": True,
                },
                environment={"os": "test"},
                head_sha="a" * 40,
                output_sha256=sha256(output.encode()).hexdigest(),
            )
        document.record(section, evidence)
    bundle_path = tmp_path / "bundle.json"
    document.write_bundle(bundle_path)
    payload = json.loads(bundle_path.read_text(encoding="utf-8"))
    payload["head_sha"] = "b" * 40
    bundle_path.write_text(json.dumps(payload), encoding="utf-8")
    result = verify_bundle(bundle_path)
    assert result.verdict == "BLOCKED"
    assert any("head_sha" in reason for reason in result.reasons)
