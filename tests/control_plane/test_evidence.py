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
    verify_bundle,
)


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
