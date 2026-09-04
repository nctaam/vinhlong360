from __future__ import annotations

import json
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest

import scripts.ops.countersign_pilot_acceptance as countersigner
import scripts.ops.run_pilot_acceptance as runner
from scripts.ops.run_pilot_acceptance import (
    ACCEPTANCE_LAYERS,
    AcceptanceBundle,
    EvidenceSection,
    _bundle_digest,
    _evidence_digest,
)

_KINDS = {
    "unit": "pytest",
    "postgres": "postgresql-drill",
    "multi_process": "multi-process-drill",
    "browser": "browser-drill",
    "external_side_effect": "external-drill",
}


def _bundle_with_one_passing_record(tmp_path: Path, *, layer: str = "postgres") -> Path:
    """Write a minimal bundle whose single passing record can be re-executed."""

    layers = {}
    for name in ACCEPTANCE_LAYERS:
        nodeid = f"agent/tests/test_x.py::test_{name}"
        captured = f"{nodeid} PASSED                       [100%]\n1 passed in 0.10s\n"
        evidence = {
            "command": f"pytest -v {nodeid}",
            "environment": {"head_sha": "0" * 40, "working_tree_digest": "1" * 64,
                            "production_calls": False, "secrets_collected": False, "raw_personal_data": False},
            "nodeids": [nodeid],
            "return_code": 0,
            # Counts are part of the fingerprint: without them an ALL-SKIPPED
            # run is indistinguishable from a real one.
            "summary": {"passed": 1, "skipped": 0, "failed": 0, "errors": 0,
                        "collection_errors": 0, "summary_present": True},
            "captured_output": captured,
            "output_sha256": sha256(captured.encode("utf-8")).hexdigest(),
            "owner": "service-owner",
            "rollback_note": "fixture",
            "outcome": "PASS" if name == layer else "UNCLASSIFIED",
            "finding_id": "F-01",
            "layer": name,
            "evidence_kind": _KINDS[name],
            "checksum_verified": True,
            "stale": False,
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "proof_id": f"fixture-{name}",
            "provenance": {"finding_id": "F-01", "layer": name, "capture_id": f"c-{name}", "source": "fixture"},
        }
        evidence["checksum"] = _evidence_digest(evidence)
        layers[name] = evidence
    bundle = AcceptanceBundle(
        sections={"F-01": EvidenceSection(outcome="UNCLASSIFIED", layers=layers, finding_id="F-01")},
        artifact_id="pilot-acceptance-countersign-fixture",
        head_sha="0" * 40,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
    bundle.output_sha256 = _bundle_digest(bundle)
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(bundle.to_dict(), ensure_ascii=True, indent=2, sort_keys=True), encoding="utf-8")
    return path


def test_a_confirmed_rerun_covers_every_passing_record(tmp_path, monkeypatch):
    """When re-execution agrees, the record is confirmed and coverage is complete."""

    path = _bundle_with_one_passing_record(tmp_path)
    monkeypatch.setattr(
        countersigner, "_rerun",
        lambda nodeids, root, temp_root, label, timeout: ("PASS", 0, list(nodeids), {"passed": 1, "skipped": 0, "failed": 0, "errors": 0, "collection_errors": 0}),
    )

    receipt = countersigner.countersign(path, root=tmp_path, temp_root=tmp_path / "scratch")

    assert receipt["confirmed"] == ["F-01/postgres"]
    assert receipt["expected"] == ["F-01/postgres"]
    assert receipt["complete"] is True


def test_a_rerun_that_disagrees_is_reported_as_a_mismatch(tmp_path, monkeypatch):
    """A bundle claiming PASS over a run that fails must not be countersigned."""

    path = _bundle_with_one_passing_record(tmp_path)
    monkeypatch.setattr(
        countersigner, "_rerun",
        lambda nodeids, root, temp_root, label, timeout: ("BLOCKED", 1, list(nodeids), {"passed": 0, "skipped": 0, "failed": 1, "errors": 0, "collection_errors": 0}),
    )

    receipt = countersigner.countersign(path, root=tmp_path, temp_root=tmp_path / "scratch")

    assert receipt["complete"] is False
    assert receipt["confirmed"] == []
    assert [item["verdict"] for item in receipt["results"]] == ["MISMATCH"]


def test_a_rerun_that_never_names_the_claimed_tests_is_a_mismatch(tmp_path, monkeypatch):
    """Observing a green tally is not enough; the named tests must actually appear."""

    path = _bundle_with_one_passing_record(tmp_path)
    monkeypatch.setattr(
        countersigner, "_rerun",
        lambda nodeids, root, temp_root, label, timeout: ("PASS", 0, [], {"passed": 1, "skipped": 0, "failed": 0, "errors": 0, "collection_errors": 0}),
    )

    receipt = countersigner.countersign(path, root=tmp_path, temp_root=tmp_path / "scratch")

    assert receipt["complete"] is False
    assert receipt["results"][0]["verdict"] == "MISMATCH"


@pytest.mark.parametrize("layer", ["browser", "external_side_effect"])
def test_a_non_replayable_boundary_is_named_rather_than_counted(tmp_path, monkeypatch, layer):
    """A browser or provider drill cannot be replayed, and the receipt says so."""

    path = _bundle_with_one_passing_record(tmp_path, layer=layer)
    monkeypatch.setattr(
        countersigner, "_rerun",
        lambda nodeids, root, temp_root, label, timeout: ("PASS", 0, list(nodeids), {"passed": 1, "skipped": 0, "failed": 0, "errors": 0, "collection_errors": 0}),
    )

    receipt = countersigner.countersign(path, root=tmp_path, temp_root=tmp_path / "scratch")

    assert receipt["results"][0]["verdict"] == "NOT_REPLAYABLE"
    assert receipt["complete"] is False


def test_the_bundle_command_string_is_never_executed(tmp_path, monkeypatch):
    """The countersigner rebuilds its own invocation from node ids only."""

    path = _bundle_with_one_passing_record(tmp_path)
    seen: list[list[str]] = []

    def fake_rerun(nodeids, root, temp_root, label, timeout):
        seen.append(list(nodeids))
        return "PASS", 0, list(nodeids), {
            "passed": 1, "skipped": 0, "failed": 0, "errors": 0, "collection_errors": 0,
        }

    monkeypatch.setattr(countersigner, "_rerun", fake_rerun)
    countersigner.countersign(path, root=tmp_path, temp_root=tmp_path / "scratch")

    assert seen == [["agent/tests/test_x.py::test_postgres"]]


def test_no_countersignature_is_signed_without_key_material(tmp_path, monkeypatch):
    """Absent keys yield an unsigned attestation, never a silent pass."""

    path = _bundle_with_one_passing_record(tmp_path)
    monkeypatch.delenv("PILOT_ATTEST_COUNTERSIGN_KEY", raising=False)
    monkeypatch.setattr(
        countersigner, "_rerun",
        lambda nodeids, root, temp_root, label, timeout: ("PASS", 0, list(nodeids), {"passed": 1, "skipped": 0, "failed": 0, "errors": 0, "collection_errors": 0}),
    )

    receipt = countersigner.countersign(path, root=tmp_path, temp_root=tmp_path / "scratch")

    attestation = receipt["attestation"]
    assert attestation is None or attestation["signature"] == ""


def test_the_outcome_fingerprint_ignores_ordering_but_not_content():
    """Two honest runs differ in timing, never in verdict, node ids or code."""

    COUNTS = {"passed": 1, "skipped": 0, "failed": 0, "errors": 0, "collection_errors": 0}
    first = countersigner._outcome_fingerprint("PASS", ["b::t", "a::t"], 0, COUNTS)
    second = countersigner._outcome_fingerprint("PASS", ["a::t", "b::t"], 0, COUNTS)
    assert first == second
    assert first != countersigner._outcome_fingerprint("BLOCKED", ["a::t", "b::t"], 0, COUNTS)
    assert first != countersigner._outcome_fingerprint("PASS", ["a::t"], 0, COUNTS)
    # Cùng verdict, cùng node id, cùng return code — chỉ khác COUNTS.
    all_skipped = {"passed": 0, "skipped": 1, "failed": 0, "errors": 0, "collection_errors": 0}
    assert first != countersigner._outcome_fingerprint("PASS", ["b::t", "a::t"], 0, all_skipped)


def test_runner_and_countersigner_agree_on_the_replayable_kinds():
    """The two tools must not disagree about what can be re-executed."""

    assert countersigner._PARSED_EVIDENCE_KINDS is runner._PARSED_EVIDENCE_KINDS


def test_runner_retains_successful_pytest_nodeids(monkeypatch, tmp_path: Path) -> None:
    """A clean verbose pytest run must carry its real passing node id forward."""

    nodeid = "tests/example.py::test_green"
    monkeypatch.setattr(
        runner.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            stdout=f"{nodeid} PASSED [100%]\n1 passed in 0.01s\n",
            stderr="",
            returncode=0,
        ),
    )

    _command, code, details = runner._run(["pytest", "-v", nodeid], tmp_path)

    assert code == 0
    assert details["outcome"] == "PASS"
    assert details["nodeids"] == [nodeid]


def test_countersign_cli_resolves_relative_bundle_against_root(tmp_path: Path, monkeypatch) -> None:
    """A relative bundle argument is rooted at the selected checkout."""

    root = tmp_path / "alternate-root"
    bundle_path = root / "artifacts" / "pilot-acceptance.json"
    bundle_path.parent.mkdir(parents=True)
    bundle_path.write_text("{}", encoding="utf-8")
    seen: list[Path] = []

    def fake_countersign(path: Path, **kwargs):
        seen.append(path)
        return {"complete": True, "confirmed": [], "expected": [], "attestation": {"signature": "x"}}

    monkeypatch.setattr(countersigner, "countersign", fake_countersign)
    output = root / "artifacts" / "receipt.json"

    assert countersigner.main([
        "--bundle", "artifacts/pilot-acceptance.json",
        "--root", str(root),
        "--output", str(output),
    ]) == 0

    assert seen == [bundle_path.resolve()]


def test_an_all_skipped_rerun_cannot_impersonate_a_real_drill(tmp_path, monkeypatch):
    """Chạy TOÀN SKIP không được trùng dấu vân tay với một drill thật.

    Đây là lỗ hổng nghiêm trọng nhất của bộ đối chứng, đo ngày 2026-09-03:
    `classify_verdict` trả "PASS" khi không có gì FAIL, pytest thoát 0, và
    `pytest -v` vẫn in ra node id. Nên trên một máy KHÔNG có database, ba drill
    postgres `@pg_only` sẽ SKIP và tái tạo đúng dấu vân tay của một lần chạy
    thật — nghĩa là cái control MẠNH NHẤT có thể được thoả mãn bằng cách không
    chạy gì cả.

    Runner đã tự canh mối nguy này ở từng capture ("an all-skipped run has a
    clean summary and would otherwise be indistinguishable from proof"); bộ đối
    chứng thì chưa, nên nó YẾU HƠN chính cái self-check mà nó phải vượt qua.
    """
    path = _bundle_with_one_passing_record(tmp_path)

    monkeypatch.setattr(
        countersigner,
        "_rerun",
        # Verdict, return code và node id GIỐNG HỆT một lần chạy thật.
        # Chỉ counts là khác: không có gì chạy cả.
        lambda nodeids, root, temp_root, label, timeout: (
            "PASS", 0, list(nodeids),
            {"passed": 0, "skipped": 1, "failed": 0, "errors": 0, "collection_errors": 0},
        ),
    )

    receipt = countersigner.countersign(path, root=tmp_path, temp_root=tmp_path / "scratch")

    assert receipt["results"][0]["verdict"] == "MISMATCH", (
        "một lần chạy toàn SKIP đã mạo danh được drill thật"
    )
    assert receipt["complete"] is False


def test_a_record_without_a_return_code_is_not_replayable(tmp_path, monkeypatch):
    """Thiếu return_code thì phải TỪ CHỐI, không được coi như đã thành công.

    Trước đây `int(evidence.get("return_code", 0))` bịa ra số 0, nên một bản ghi
    chưa từng khai trạng thái thoát vẫn được đối chứng như thể đã khai thành công.
    """
    path = _bundle_with_one_passing_record(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    del payload["sections"]["F-01"]["layers"]["postgres"]["return_code"]
    payload["output_sha256"] = _bundle_digest(runner.AcceptanceBundle.from_dict(payload))
    path.write_text(json.dumps(payload), encoding="utf-8")

    receipt = countersigner.countersign(path, root=tmp_path, temp_root=tmp_path / "scratch")

    assert receipt["results"][0]["verdict"] == "NOT_REPLAYABLE"
    assert receipt["results"][0]["reason"] == "return-code-missing"
