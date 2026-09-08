from __future__ import annotations

import json
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "agent"))

from control_plane.snapshot import current_generation
from database import Database

import scripts.ops.run_pilot_acceptance as runner
from agent.control_plane.attestation import (
    KeyReference,
    build_attestation,
    payload_digest,
    resolve_key,
)
from scripts.ops.run_pilot_acceptance import (
    ACCEPTANCE_LAYERS,
    P1_FINDINGS,
    AcceptanceBundle,
    EvidenceSection,
    evaluate_pilot_gate,
    verify_pilot_bundle,
    run_pilot_acceptance,
    _head_sha,
    _working_tree_digest,
    _bundle_digest,
    _evidence_digest,
)

ROOT = Path(__file__).resolve().parents[2]

# The gate re-reads the checkout fingerprint at assertion time.  Freezing these
# at import made every bundle built later in the session stale the moment
# anything wrote to the tree, so each bundle now takes one fresh reading and
# threads it through its own sections.
_FIXTURE_EVIDENCE_KINDS = {
    "unit": "pytest",
    "postgres": "postgresql-drill",
    "multi_process": "multi-process-drill",
    "browser": "browser-drill",
    "external_side_effect": "external-drill",
}


@pytest.fixture(autouse=True)
def pilot_attestation_keys(monkeypatch, tmp_path_factory, request):
    """Give the gate a complete set of signing identities held outside the repo.

    Production custody deliberately resolves to nothing on a developer machine,
    which is what keeps the real gate at NO_GO.  Tests therefore supply their
    own key references so the signed path itself stays exercised.
    """

    # The production custody rule intentionally rejects keys inside the
    # editable checkout.  Keep this fixture outside ROOT even when callers use
    # a workspace-local --basetemp to avoid Windows pytest temp permissions.
    base_parent = tmp_path_factory.getbasetemp().resolve().parent
    try:
        base_parent.relative_to(ROOT)
    except ValueError:
        key_parent = base_parent
    else:
        key_parent = ROOT.parent
    key_dir = key_parent / f"pilot-attestation-keys-{uuid.uuid4().hex}"
    key_dir.mkdir(parents=True, exist_ok=False)
    request.addfinalizer(lambda: shutil.rmtree(key_dir, ignore_errors=True))
    owner_key = key_dir / "owner-signing.key"
    owner_key.write_bytes(b"owner-test-key-material-0123456789abcdef")
    # Một runner Actions thật công bố CẢ MỘT BỘ định danh mạch lạc. Chỉ
    # `GITHUB_ACTIONS=true` thì shell nào cũng export được, nên nó không bao giờ
    # phân biệt được custody CI với một tiến trình local — đúng thứ mà
    # `ci-secret` sinh ra để khẳng định.
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_REPOSITORY", "vinhlong360/vinhlong360")
    monkeypatch.setenv("GITHUB_RUN_ID", "1234567890")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    monkeypatch.setenv("GITHUB_SHA", "a" * 40)
    monkeypatch.setenv(
        "GITHUB_WORKFLOW_REF",
        "vinhlong360/vinhlong360/.github/workflows/ci.yml@refs/heads/main",
    )
    monkeypatch.setenv("PILOT_TEST_RUNNER_KEY", "runner-test-key-material-0123456789abcdef")
    monkeypatch.setenv("PILOT_TEST_COUNTERSIGN_KEY", "countersign-test-key-material-0123456789")
    monkeypatch.setenv("PILOT_TEST_CI_KEY", "ci-test-key-material-0123456789abcdefghij")
    references = {
        "runner-test": KeyReference("runner-test", "runner", "environment:PILOT_TEST_RUNNER_KEY"),
        "owner-test": KeyReference("owner-test", "owner", f"offline-owner:{owner_key}"),
        "countersign-test": KeyReference("countersign-test", "countersign", "environment:PILOT_TEST_COUNTERSIGN_KEY"),
        "ci-test": KeyReference("ci-test", "ci", "ci-secret:PILOT_TEST_CI_KEY"),
    }
    monkeypatch.setattr(runner, "_attestation_references", lambda _root=None: references)
    return references


def _sign_bundle(bundle: AcceptanceBundle) -> AcceptanceBundle:
    """Attach a complete, verifying attestation set to one fixture bundle."""

    references = runner._attestation_references()
    digest = payload_digest(bundle.unsigned_payload())
    covers = [
        f"{finding}/{layer}"
        for finding, section in bundle.sections.items()
        for layer in section.layers
    ]
    bundle.attestations = [
        build_attestation(
            role=reference.role,
            key_id=reference.key_id,
            custody=reference.custody,
            digest=digest,
            signed_at=datetime.now(timezone.utc).isoformat(),
            key=resolve_key(reference.custody),
            covers=covers if reference.role == "countersign" else None,
        )
        for reference in references.values()
    ]
    bundle.output_sha256 = _bundle_digest(bundle)
    return bundle


def test_entity_mutation_exposes_one_shared_generation_to_read_consumers(tmp_path, monkeypatch):
    # Pin the backend: without this the constructor honours a CI DATABASE_URL,
    # ignores db_path, and writes this fixture straight into a shared Postgres.
    import database

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(database, "USE_PG", False)
    monkeypatch.setattr(database, "DATABASE_URL", "")
    db = Database(db_path=str(tmp_path / "proof.db"))
    assert db._use_pg is False and db._dsn is None
    entity_id = "proof-entity"
    db.upsert_entity({"id": entity_id, "type": "dish", "name": "Before"})
    first = current_generation(entity_id)
    assert first == 1

    db.upsert_entity({"id": entity_id, "type": "dish", "name": "After"})
    second = current_generation(entity_id)
    assert second == first + 1
    assert db.get_entity(entity_id)["name"] == "After"


def _section(
    outcome: str = "PASS",
    *,
    stale: bool = False,
    finding: str = "F-01",
    head: str | None = None,
    tree: str | None = None,
) -> EvidenceSection:
    layers = {}
    current_head = head if head is not None else _head_sha(ROOT)
    current_tree = tree if tree is not None else _working_tree_digest(ROOT)
    for layer in ACCEPTANCE_LAYERS:
        nodeid = f"tests/{finding}/{layer}.py::proof"
        # The gate re-parses this text, so a fixture capture has to be shaped
        # like real pytest output: the node id it claims plus a matching tally.
        captured_output = f"{nodeid} PASSED                                   [100%]\n1 passed in 0.12s\n"
        evidence = {
            "command": f"pytest -q tests/{finding}/{layer}",
            "environment": {"runner": "pytest", "target": "disposable", "head_sha": current_head, "working_tree_digest": current_tree, "production_calls": False, "secrets_collected": False, "raw_personal_data": False},
            "nodeids": [nodeid],
            "return_code": 0,
            "checksum": "",
            "captured_output": captured_output,
            "output_sha256": sha256(captured_output.encode("utf-8")).hexdigest(),
            "owner": "service-owner",
            "rollback_note": "No mutation; local disposable fixture only.",
            "outcome": "PASS",
            "finding_id": finding,
            "layer": layer,
            "evidence_kind": _FIXTURE_EVIDENCE_KINDS[layer],
            "checksum_verified": True,
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "stale": False,
            "proof_id": f"fixture-{finding}-{layer}",
            "provenance": {
                "finding_id": finding,
                "layer": layer,
                "capture_id": f"capture-{finding}-{layer}",
                "source": "fixture",
            },
        }
        evidence["execution_receipt"] = {
            "version": 1,
            "issuer": "run_pilot_acceptance",
            "finding_id": finding,
            "layer": layer,
            "command_sha256": sha256(evidence["command"].encode("utf-8")).hexdigest(),
            "output_sha256": evidence["output_sha256"],
            "return_code": 0,
            "head_sha": current_head,
            "working_tree_digest": current_tree,
        }
        evidence["checksum"] = _evidence_digest(evidence)
        layers[layer] = evidence
    return EvidenceSection(
        outcome=outcome,
        stale=stale,
        cross_boundary_proof=True,
        layers=layers,
        finding_id=finding,
    )


def complete_fixture_bundle_for_p1() -> AcceptanceBundle:
    # One reading per bundle: recomputing per section would let the tree move
    # mid-build and produce layers that disagree with each other, which the
    # gate rejects outright.
    head = _head_sha(ROOT)
    tree = _working_tree_digest(ROOT)
    bundle = AcceptanceBundle(
        sections={finding: _section(finding=finding, head=head, tree=tree) for finding in P1_FINDINGS},
        artifact_id="pilot-acceptance-test",
        head_sha=head,
        generated_at=datetime.now(timezone.utc).isoformat(),
        owner_signoff=True,
        rollback_note="No mutation; local disposable fixture only.",
        owner="service-owner",
        environment={
            "runner": "pytest", "target": "disposable", "head_sha": head,
            "working_tree_digest": tree, "production_calls": False,
            "secrets_collected": False, "raw_personal_data": False,
            "probe_receipts": _valid_probe_receipts(head),
        },
        decision_required={"legal": True, "provider": True, "residency": True, "public_indexing": True},
        cross_boundary_proof=True,
        gate="GO_CONDITIONAL",
    )
    return _sign_bundle(bundle)


def _valid_probe_receipts(head: str) -> dict[str, dict[str, object]]:
    environments = {
        "multiprocess-scheduler": "local-disposable-postgres",
        "provider-sandbox": "local-deterministic-provider-sandbox",
        "proxy-contract": "local-loopback-proxy",
        "backup-restore-checksum": "local-disposable-postgres",
    }
    commands = {
        "multiprocess-scheduler": "python scripts/ops/probe_multiprocess_scheduler.py --workers 2 --slots 1",
        "provider-sandbox": "python scripts/ops/probe_provider_sandbox.py --mode deterministic",
        "proxy-contract": "python scripts/ops/probe_proxy_contract.py --base-url http://127.0.0.1:8360",
        "backup-restore-checksum": "python scripts/ops/restore_drill.py --backup fixture.dump --execute",
    }
    output = '{"status":"pass"}\n'
    started = datetime.now(timezone.utc)
    return {
        probe_id: {
            "verdict": "PASS",
            "reasons": [],
            "receipt": {
                "probe_id": probe_id,
                "head_sha": head,
                "environment_id": environment,
                "started_at": started.isoformat(),
                "finished_at": (started + timedelta(seconds=1)).isoformat(),
                "command": commands[probe_id],
                "exit_code": 0,
                "output_sha256": sha256(output.encode("utf-8")).hexdigest(),
                "captured_output": output,
                "test_nodeids": [f"{probe_id}::proof"],
                "verdict": "PASS",
            },
        }
        for probe_id, environment in environments.items()
    }


def test_gate_rejects_missing_p1_and_unclassified_evidence():
    bundle = AcceptanceBundle(
        sections={"F-69": _section(), "F-01": _section("UNCLASSIFIED")}
    )
    assert evaluate_pilot_gate(bundle) == "NO_GO"

def test_gate_allows_closed_pilot_only_when_all_p1_have_layered_proof():
    assert evaluate_pilot_gate(complete_fixture_bundle_for_p1()) == "GO_CONDITIONAL"


@pytest.mark.parametrize(
    "mutator",
    [
        lambda bundle: setattr(bundle, "cross_boundary_proof", False),
        lambda bundle: bundle.sections.__setitem__("F-01", _section(stale=True)),
        lambda bundle: bundle.sections["F-01"].layers.pop("browser"),
        lambda bundle: bundle.decision_required.__setitem__("legal", False),
    ],
)
def test_gate_is_fail_closed_for_boundary_staleness_layers_and_decisions(mutator):
    bundle = complete_fixture_bundle_for_p1()
    mutator(bundle)
    assert evaluate_pilot_gate(bundle) == "NO_GO"


def test_gate_rejects_an_artifact_older_than_its_freshness_window():
    bundle = complete_fixture_bundle_for_p1()
    bundle.generated_at = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
    bundle.max_age_hours = 24

    assert evaluate_pilot_gate(bundle) == "NO_GO"


def test_gate_rejects_a_stale_layer_even_when_other_layers_pass():
    bundle = complete_fixture_bundle_for_p1()
    bundle.sections["F-01"].layers["unit"]["stale"] = True

    assert evaluate_pilot_gate(bundle) == "NO_GO"


def test_gate_rejects_missing_artifact_identity():
    bundle = complete_fixture_bundle_for_p1()
    bundle.artifact_id = ""

    assert evaluate_pilot_gate(bundle) == "NO_GO"


def test_gate_rejects_availability_probe_as_postgres_proof():
    bundle = complete_fixture_bundle_for_p1()
    bundle.sections["F-01"].layers["postgres"]["outcome"] = "PASS"
    bundle.sections["F-01"].layers["postgres"]["evidence_kind"] = "availability"

    assert evaluate_pilot_gate(bundle) == "NO_GO"


@pytest.mark.parametrize(
    "field,value",
    [
        ("generated_at", ""),
        ("generated_at", "not-a-timestamp"),
        ("generated_at", (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()),
        ("head_sha", "g" * 40),
        ("head_sha", "unknown"),
    ],
)
def test_gate_rejects_missing_malformed_or_future_identity_metadata(field, value):
    bundle = complete_fixture_bundle_for_p1()
    setattr(bundle, field, value)
    assert evaluate_pilot_gate(bundle) == "NO_GO"


def test_gate_binds_decision_keys_to_authority_contract_and_public_no_go():
    bundle = complete_fixture_bundle_for_p1()
    bundle.decision_required = {
        "legal": True,
        "provider": True,
        "residency": True,
        "public_indexing": True,
    }
    assert bundle.public_launch_gate == "NO_GO"
    assert evaluate_pilot_gate(bundle) == "GO_CONDITIONAL"

    bundle.decision_required["extra"] = True
    assert evaluate_pilot_gate(bundle) == "NO_GO"


def test_gate_requires_finding_and_layer_bound_evidence_with_explicit_kind():
    bundle = complete_fixture_bundle_for_p1()
    evidence = bundle.sections["F-01"].layers["unit"]
    evidence["finding_id"] = "F-02"
    assert evaluate_pilot_gate(bundle) == "NO_GO"

    evidence["finding_id"] = "F-01"
    evidence["layer"] = "postgres"
    assert evaluate_pilot_gate(bundle) == "NO_GO"

    evidence["layer"] = "unit"
    evidence["evidence_kind"] = ""
    assert evaluate_pilot_gate(bundle) == "NO_GO"


def test_gate_rejects_unverifiable_checksum_and_invalid_outcome():
    bundle = complete_fixture_bundle_for_p1()
    evidence = bundle.sections["F-01"].layers["unit"]
    evidence["checksum"] = "not-hex"
    assert evaluate_pilot_gate(bundle) == "NO_GO"

    evidence["checksum"] = "a" * 64
    evidence.pop("outcome", None)
    assert evaluate_pilot_gate(bundle) == "NO_GO"


def test_verifier_returns_blocked_for_malformed_sections(tmp_path):
    path = tmp_path / "malformed.json"
    path.write_text(
        '{"bundle_kind":"pilot-acceptance-v1","output_sha256":"' + "0" * 64 + '","sections":{"F-01":[]}}',
        encoding="utf-8",
    )
    verdict, reasons, _ = verify_pilot_bundle(path)
    assert verdict == "BLOCKED"
    assert reasons


def test_runner_uses_workspace_local_pytest_temp_and_binds_unique_provenance(monkeypatch, tmp_path):
    import scripts.ops.run_pilot_acceptance as runner

    commands = []

    def fake_run(command, root, *, timeout=120):
        commands.append(command)
        return " ".join(command), 0, {
            "outcome": "PASS",
            "nodeids": ["tests/integration/test_cross_boundary_proof.py::proof"],
            "parsed": {"summary_present": True},
            "output": "1 passed\n",
        }

    monkeypatch.setattr(runner, "_run", fake_run)
    monkeypatch.setattr(runner.shutil, "which", lambda _name: None)
    bundle = run_pilot_acceptance(
        tmp_path,
        database_target="none",
        browser_base_url=None,
        external_sandbox=False,
    )

    assert commands
    assert all("--basetemp" in command and str(tmp_path) in " ".join(command) for command in commands)
    unit_checksums = {
        bundle.sections[finding].layers[layer]["checksum"]
        for finding in P1_FINDINGS
        for layer in ACCEPTANCE_LAYERS
    }
    assert len(unit_checksums) == len(P1_FINDINGS) * len(ACCEPTANCE_LAYERS)
    assert all(
        bundle.sections[finding].layers["unit"]["outcome"] == "UNCLASSIFIED"
        for finding in P1_FINDINGS
    )


def test_gate_rejects_one_shared_placeholder_result_cloned_to_every_p1_layer():
    bundle = complete_fixture_bundle_for_p1()
    placeholder = dict(bundle.sections["F-01"].layers["unit"])
    for finding in P1_FINDINGS:
        for layer in ACCEPTANCE_LAYERS:
            evidence = dict(placeholder)
            evidence["finding_id"] = finding
            evidence["layer"] = layer
            bundle.sections[finding].layers[layer] = evidence

    assert evaluate_pilot_gate(bundle) == "NO_GO"


@pytest.mark.parametrize(
    "field,value",
    [
        ("command", ["pytest"]),
        ("owner", 42),
        ("rollback_note", {"note": "local"}),
        ("environment", "pytest"),
        ("nodeids", "tests::proof"),
        ("return_code", "0"),
        ("checksum", 42),
        ("outcome", ["PASS"]),
        ("evidence_kind", ["pytest"]),
        ("observed_at", None),
        ("checksum_verified", 1),
        ("stale", "false"),
    ],
)
def test_gate_rejects_malformed_layer_metadata_types(field, value):
    bundle = complete_fixture_bundle_for_p1()
    bundle.sections["F-01"].layers["unit"][field] = value
    assert evaluate_pilot_gate(bundle) == "NO_GO"


def test_verifier_rejects_declared_gate_that_disagrees_with_computed_verdict(tmp_path):
    bundle = complete_fixture_bundle_for_p1()
    bundle.gate = "NO_GO"
    path = tmp_path / "forged-gate.json"
    bundle.write(path)

    verdict, reasons, _ = verify_pilot_bundle(path)

    assert verdict == "BLOCKED"
    assert reasons


def test_head_sha_returns_unknown_when_git_fails(monkeypatch, tmp_path):
    import scripts.ops.run_pilot_acceptance as runner

    class FailedGit:
        returncode = 1
        stdout = "a" * 40

    monkeypatch.setattr(runner.subprocess, "run", lambda *args, **kwargs: FailedGit())

    assert runner._head_sha(tmp_path) == "unknown"


def test_gate_recomputes_layer_checksum_from_canonical_evidence_payload():
    bundle = complete_fixture_bundle_for_p1()
    evidence = bundle.sections["F-01"].layers["unit"]
    evidence["summary"] = {"proof_id": "tampered-after-capture"}
    assert evaluate_pilot_gate(bundle) == "NO_GO"


@pytest.mark.parametrize(
    "field,value",
    [
        ("capture_id", "capture-F-01-unit-forged"),
        ("source", "forged-source"),
    ],
)
def test_gate_requires_full_attestation_regeneration_after_provenance_mutation(field, value):
    bundle = complete_fixture_bundle_for_p1()
    evidence = bundle.sections["F-01"].layers["unit"]
    evidence["provenance"][field] = value

    # Re-signing only the envelope must not authorize a changed provenance claim.
    bundle.output_sha256 = _bundle_digest(bundle)
    assert evaluate_pilot_gate(bundle) == "NO_GO"

    # Regenerating the layer checksum and the envelope is still not enough:
    # provenance is inside the signed payload, so the attestations no longer
    # match the bundle they claim to cover.
    evidence["checksum"] = _evidence_digest(evidence)
    bundle.output_sha256 = _bundle_digest(bundle)
    assert evaluate_pilot_gate(bundle) == "NO_GO"

    # A legitimate change re-signs every layer, then the attestations, then the
    # envelope, in that order.
    assert evaluate_pilot_gate(_sign_bundle(bundle)) == "GO_CONDITIONAL"


def test_gate_requires_mandatory_unique_source_capture_provenance():
    bundle = complete_fixture_bundle_for_p1()
    evidence = bundle.sections["F-01"].layers["unit"]
    evidence.pop("provenance", None)
    assert evaluate_pilot_gate(bundle) == "NO_GO"


def test_canonical_digest_rejects_missing_provenance_mapping():
    bundle = complete_fixture_bundle_for_p1()
    evidence = bundle.sections["F-01"].layers["unit"]
    evidence.pop("provenance", None)
    assert _evidence_digest(evidence) == ""


def test_gate_rejects_unbound_provenance_fields():
    bundle = complete_fixture_bundle_for_p1()
    evidence = bundle.sections["F-01"].layers["unit"]
    evidence["provenance"]["unexpected"] = "tampered"
    bundle.output_sha256 = _bundle_digest(bundle)
    assert evaluate_pilot_gate(bundle) == "NO_GO"


def test_gate_rejects_copied_capture_with_unique_summaries():
    bundle = complete_fixture_bundle_for_p1()
    source = dict(bundle.sections["F-01"].layers["unit"])
    for finding in P1_FINDINGS:
        for layer in ACCEPTANCE_LAYERS:
            copied = dict(source)
            copied["finding_id"] = finding
            copied["layer"] = layer
            copied["summary"] = {"proof_id": f"copied-{finding}-{layer}"}
            bundle.sections[finding].layers[layer] = copied
    assert evaluate_pilot_gate(bundle) == "NO_GO"


def test_gate_rejects_synthetic_evidence_without_runner_execution_receipt():
    bundle = complete_fixture_bundle_for_p1()
    evidence = bundle.sections["F-01"].layers["unit"]
    evidence.pop("execution_receipt")
    evidence["checksum"] = _evidence_digest(evidence)
    bundle.output_sha256 = _bundle_digest(bundle)

    assert evaluate_pilot_gate(bundle) == "NO_GO"


def test_gate_rejects_copied_capture_with_forged_unique_provenance_and_summary():
    bundle = complete_fixture_bundle_for_p1()
    source = dict(bundle.sections["F-01"].layers["unit"])
    for finding in P1_FINDINGS:
        for layer in ACCEPTANCE_LAYERS:
            copied = dict(source)
            copied["finding_id"] = finding
            copied["layer"] = layer
            copied["summary"] = {"proof_id": f"copied-{finding}-{layer}"}
            copied["provenance"] = {
                "finding_id": finding,
                "layer": layer,
                "capture_id": f"forged-{finding}-{layer}",
                "source": "forged-copy",
            }
            copied["checksum"] = _evidence_digest(copied)
            bundle.sections[finding].layers[layer] = copied
    bundle.output_sha256 = _bundle_digest(bundle)
    assert evaluate_pilot_gate(bundle) == "NO_GO"


def test_gate_binds_head_sha_to_current_checkout():
    bundle = complete_fixture_bundle_for_p1()
    bundle.head_sha = "b" * 40
    bundle.output_sha256 = _bundle_digest(bundle)
    assert evaluate_pilot_gate(bundle) == "NO_GO"


def test_gate_binds_evidence_to_current_working_tree_contents():
    bundle = complete_fixture_bundle_for_p1()
    bundle.environment["working_tree_digest"] = "0" * 64
    assert evaluate_pilot_gate(bundle) == "NO_GO"


def test_gate_rejects_layer_from_a_different_working_tree():
    bundle = complete_fixture_bundle_for_p1()
    bundle.sections["F-01"].layers["unit"]["environment"]["working_tree_digest"] = "f" * 64
    assert evaluate_pilot_gate(bundle) == "NO_GO"


def test_gate_rejects_forged_checkout_head_even_when_every_environment_agrees():
    bundle = complete_fixture_bundle_for_p1()
    forged_head = "f" * 40 if bundle.head_sha != "f" * 40 else "e" * 40
    bundle.head_sha = forged_head
    bundle.environment["head_sha"] = forged_head
    for section in bundle.sections.values():
        for evidence in section.layers.values():
            evidence["environment"]["head_sha"] = forged_head
            evidence["checksum"] = _evidence_digest(evidence)
    bundle.output_sha256 = _bundle_digest(bundle)

    assert evaluate_pilot_gate(bundle) == "NO_GO"


def test_gate_uses_authority_freshness_not_a_mutable_bundle_extension():
    bundle = complete_fixture_bundle_for_p1()
    bundle.generated_at = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
    bundle.max_age_hours = 48
    bundle.output_sha256 = _bundle_digest(bundle)

    assert evaluate_pilot_gate(bundle) == "NO_GO"


@pytest.mark.parametrize("constant", [float("nan"), float("inf"), float("-inf")])
def test_direct_gate_rejects_non_finite_canonical_evidence_values(constant):
    bundle = complete_fixture_bundle_for_p1()
    evidence = bundle.sections["F-01"].layers["unit"]
    evidence["summary"] = {"duration": constant}

    assert _evidence_digest(evidence) == ""
    assert evaluate_pilot_gate(bundle) == "NO_GO"


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_file_verifier_rejects_non_finite_json_constants(tmp_path, constant):
    bundle = complete_fixture_bundle_for_p1()
    path = tmp_path / "non-finite.json"
    bundle.write(path)
    path.write_text(
        path.read_text(encoding="utf-8").replace('"max_age_hours": 24', f'"max_age_hours": {constant}'),
        encoding="utf-8",
    )

    verdict, reasons, _ = verify_pilot_bundle(path)

    assert verdict == "BLOCKED"
    assert reasons


def test_gate_rejects_malformed_layer_output_digest():
    bundle = complete_fixture_bundle_for_p1()
    evidence = bundle.sections["F-01"].layers["unit"]
    evidence["output_sha256"] = "not-a-sha256"

    assert _evidence_digest(evidence) == ""
    assert evaluate_pilot_gate(bundle) == "NO_GO"


def test_gate_rejects_output_digest_not_bound_to_captured_bytes():
    bundle = complete_fixture_bundle_for_p1()
    evidence = bundle.sections["F-01"].layers["unit"]
    evidence["captured_output"] = "different captured bytes\n"
    evidence["checksum"] = _evidence_digest(evidence)
    bundle.output_sha256 = _bundle_digest(bundle)

    assert evaluate_pilot_gate(bundle) == "NO_GO"


def test_gate_rejects_unsafe_environment_claim():
    bundle = complete_fixture_bundle_for_p1()
    bundle.environment["production_calls"] = True
    bundle.output_sha256 = _bundle_digest(bundle)
    assert evaluate_pilot_gate(bundle) == "NO_GO"


def test_gate_rejects_non_authority_owner():
    bundle = complete_fixture_bundle_for_p1()
    bundle.owner = "qa/release"
    bundle.output_sha256 = _bundle_digest(bundle)
    assert evaluate_pilot_gate(bundle) == "NO_GO"


def test_gate_rejects_layer_owner_mismatch():
    bundle = complete_fixture_bundle_for_p1()
    bundle.sections["F-01"].layers["unit"]["owner"] = "qa/release"
    bundle.sections["F-01"].layers["unit"]["checksum"] = _evidence_digest(bundle.sections["F-01"].layers["unit"])
    bundle.output_sha256 = _bundle_digest(bundle)
    assert evaluate_pilot_gate(bundle) == "NO_GO"


def test_gate_rejects_missing_owner_signoff():
    bundle = complete_fixture_bundle_for_p1()
    bundle.owner_signoff = False
    bundle.output_sha256 = _bundle_digest(bundle)
    assert evaluate_pilot_gate(bundle) == "NO_GO"


def test_gate_rejects_authority_contract_drift(monkeypatch):
    import scripts.ops.run_pilot_acceptance as runner

    bundle = complete_fixture_bundle_for_p1()
    monkeypatch.setattr(runner, "_authority_contract", lambda _root=None: ({"legal"}, "NO_GO", 24, "service-owner"))
    assert evaluate_pilot_gate(bundle) == "NO_GO"


def test_gate_rejects_cloned_capture_with_unique_user_editable_metadata():
    bundle = complete_fixture_bundle_for_p1()
    source = dict(bundle.sections["F-01"].layers["unit"])
    for finding in P1_FINDINGS:
        for layer in ACCEPTANCE_LAYERS:
            copied = dict(source)
            copied["finding_id"] = finding
            copied["layer"] = layer
            copied["command"] = f"pytest -q tests/{finding}/{layer}/unique"
            copied["nodeids"] = [f"tests/{finding}/{layer}::unique"]
            copied["summary"] = {"proof_id": f"unique-summary-{finding}-{layer}"}
            copied["proof_id"] = f"unique-proof-{finding}-{layer}"
            copied["provenance"] = {
                "finding_id": finding,
                "layer": layer,
                "capture_id": f"unique-capture-{finding}-{layer}",
                "source": f"unique-source-{finding}-{layer}",
            }
            copied["checksum"] = _evidence_digest(copied)
            bundle.sections[finding].layers[layer] = copied
    bundle.output_sha256 = _bundle_digest(bundle)

    assert evaluate_pilot_gate(bundle) == "NO_GO"


def test_gate_binds_evidence_owner_into_layer_attestation():
    bundle = complete_fixture_bundle_for_p1()
    evidence = bundle.sections["F-01"].layers["unit"]
    evidence["owner"] = "attacker"
    bundle.output_sha256 = _bundle_digest(bundle)
    assert evaluate_pilot_gate(bundle) == "NO_GO"


@pytest.mark.parametrize("declared", ["", "0" * 64, "f" * 64])
def test_gate_requires_valid_top_level_envelope_digest(declared):
    bundle = complete_fixture_bundle_for_p1()
    bundle.output_sha256 = declared
    assert evaluate_pilot_gate(bundle) == "NO_GO"


def test_gate_rejects_a_capture_whose_text_contradicts_its_declared_outcome():
    """A record may not claim PASS over output that reports a failure."""

    bundle = complete_fixture_bundle_for_p1()
    evidence = bundle.sections["F-01"].layers["unit"]
    nodeid = evidence["nodeids"][0]
    captured = f"{nodeid} FAILED                                   [100%]\n1 failed in 0.12s\n"
    evidence["captured_output"] = captured
    evidence["output_sha256"] = sha256(captured.encode("utf-8")).hexdigest()
    evidence["execution_receipt"]["output_sha256"] = evidence["output_sha256"]
    evidence["checksum"] = _evidence_digest(evidence)

    assert evaluate_pilot_gate(_sign_bundle(bundle)) == "NO_GO"


def test_gate_rejects_a_capture_with_no_test_summary_at_all():
    """Free text is not a run: a pytest-shaped record needs a real tally."""

    bundle = complete_fixture_bundle_for_p1()
    evidence = bundle.sections["F-01"].layers["unit"]
    captured = evidence["nodeids"][0] + " looks fine to me\n"
    evidence["captured_output"] = captured
    evidence["output_sha256"] = sha256(captured.encode("utf-8")).hexdigest()
    evidence["execution_receipt"]["output_sha256"] = evidence["output_sha256"]
    evidence["checksum"] = _evidence_digest(evidence)

    assert evaluate_pilot_gate(_sign_bundle(bundle)) == "NO_GO"


def test_gate_rejects_nodeids_absent_from_the_captured_transcript():
    """A record may not claim to have exercised work its transcript never names."""

    bundle = complete_fixture_bundle_for_p1()
    evidence = bundle.sections["F-01"].layers["unit"]
    evidence["nodeids"] = ["tests/never_ran.py::phantom"]
    evidence["checksum"] = _evidence_digest(evidence)

    assert evaluate_pilot_gate(_sign_bundle(bundle)) == "NO_GO"


@pytest.mark.parametrize("layer", ["browser", "external_side_effect", "postgres", "multi_process"])
def test_gate_rejects_a_pytest_capture_offered_as_another_boundary(layer):
    """An in-process pytest run does not cross the browser or provider boundary."""

    bundle = complete_fixture_bundle_for_p1()
    evidence = bundle.sections["F-01"].layers[layer]
    evidence["evidence_kind"] = "pytest"
    evidence["checksum"] = _evidence_digest(evidence)

    assert evaluate_pilot_gate(_sign_bundle(bundle)) == "NO_GO"


def test_gate_rejects_a_bundle_with_no_attestations_at_all():
    """An unsigned bundle is never a closed-pilot approval."""

    bundle = complete_fixture_bundle_for_p1()
    bundle.attestations = []
    bundle.output_sha256 = _bundle_digest(bundle)

    assert evaluate_pilot_gate(bundle) == "NO_GO"


@pytest.mark.parametrize("role", ["runner", "owner", "countersign", "ci"])
def test_gate_requires_every_attestation_role(role):
    """Dropping any single role leaves the bundle unattested."""

    bundle = complete_fixture_bundle_for_p1()
    bundle.attestations = [item for item in bundle.attestations if item["role"] != role]
    bundle.output_sha256 = _bundle_digest(bundle)

    assert evaluate_pilot_gate(bundle) == "NO_GO"


def test_gate_rejects_an_unsigned_scheme_even_when_every_role_is_present():
    """An unsigned scheme is refused by name, never read as legacy-and-allowed."""

    bundle = complete_fixture_bundle_for_p1()
    for attestation in bundle.attestations:
        attestation["scheme"] = "unsigned"
        attestation["signature"] = ""
    bundle.output_sha256 = _bundle_digest(bundle)

    assert evaluate_pilot_gate(bundle) == "NO_GO"


def test_gate_rejects_a_signature_over_a_different_payload():
    """Editing any signed field after signing invalidates the attestation set."""

    bundle = complete_fixture_bundle_for_p1()
    bundle.rollback_note = "rewritten after signing"
    bundle.output_sha256 = _bundle_digest(bundle)

    assert evaluate_pilot_gate(bundle) == "NO_GO"


def test_gate_rejects_a_countersignature_that_covers_less_than_it_claims():
    """One re-executed record must not stand in for the whole bundle."""

    bundle = complete_fixture_bundle_for_p1()
    rebuilt = []
    for item in bundle.attestations:
        covers = ["F-01/unit"] if item["role"] == "countersign" else (item["covers"] or None)
        rebuilt.append(
            build_attestation(
                role=item["role"],
                key_id=item["key_id"],
                custody=item["custody"],
                digest=item["payload_sha256"],
                signed_at=item["signed_at"],
                key=resolve_key(item["custody"]),
                covers=covers,
            )
        )
    bundle.attestations = rebuilt
    bundle.output_sha256 = _bundle_digest(bundle)

    assert evaluate_pilot_gate(bundle) == "NO_GO"


def test_gate_rejects_an_attestation_key_the_authority_never_authorised():
    """A bundle cannot introduce its own signing identity."""

    bundle = complete_fixture_bundle_for_p1()
    for attestation in bundle.attestations:
        if attestation["role"] == "owner":
            attestation["key_id"] = "owner-invented-by-the-bundle"
    bundle.output_sha256 = _bundle_digest(bundle)

    assert evaluate_pilot_gate(bundle) == "NO_GO"


def test_gate_is_no_go_when_the_working_tree_digest_cannot_be_established(monkeypatch):
    """An unknowable checkout fingerprint fails closed rather than being skipped."""

    bundle = complete_fixture_bundle_for_p1()
    monkeypatch.setattr(runner, "_working_tree_digest", lambda _root: "unknown")

    assert evaluate_pilot_gate(bundle) == "NO_GO"


def _seed_repo(path):
    """Create a throwaway git repository for working-tree digest checks."""

    import subprocess

    path.mkdir()

    def run(*args):
        subprocess.run(["git", *args], cwd=path, capture_output=True, check=True)

    run("init", "-q")
    run("config", "user.email", "t@example.com")
    run("config", "user.name", "t")
    return run


def test_working_tree_digest_survives_renames_and_deletions(tmp_path):
    """A rename or deletion must not collapse the fingerprint to unknown."""

    repo = tmp_path / "repo"
    run = _seed_repo(repo)
    (repo / "kept.txt").write_text("kept\n", encoding="utf-8")
    (repo / "renamed.txt").write_text("payload\n", encoding="utf-8")
    (repo / "removed.txt").write_text("gone\n", encoding="utf-8")
    run("add", "-A")
    run("commit", "-qm", "seed")

    baseline = _working_tree_digest(repo)
    assert baseline != "unknown"

    run("mv", "renamed.txt", "moved.txt")
    run("rm", "-q", "removed.txt")

    after = _working_tree_digest(repo)
    assert after != "unknown"
    assert after != baseline


def test_working_tree_digest_ignores_the_acceptance_artifact_but_not_source(tmp_path):
    """The bundle sits outside its own fingerprint; source files do not."""

    repo = tmp_path / "repo"
    run = _seed_repo(repo)
    (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
    run("add", "-A")
    run("commit", "-qm", "seed")

    baseline = _working_tree_digest(repo)
    (repo / "artifacts").mkdir()
    (repo / "artifacts" / "pilot-acceptance.json").write_text("{}", encoding="utf-8")
    assert _working_tree_digest(repo) == baseline

    (repo / "agent").mkdir()
    (repo / "agent" / "new_source.py").write_text("x = 1\n", encoding="utf-8")
    assert _working_tree_digest(repo) != baseline


def test_working_tree_digest_ignores_generated_pytest_nested_worktrees(tmp_path):
    """Generated pytest nested repos must not collapse the checkout digest."""

    repo = tmp_path / "repo"
    run = _seed_repo(repo)
    (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
    run("add", "-A")
    run("commit", "-qm", "seed")

    baseline = _working_tree_digest(repo)
    assert baseline != "unknown"
    generated = repo / "agent" / ".pytest-generated" / "test-case"
    generated.mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=generated, check=True, capture_output=True)

    assert _working_tree_digest(repo) == baseline

    (repo / "agent" / "source.py").write_text("value = 1\n", encoding="utf-8")
    assert _working_tree_digest(repo) != baseline


def test_runner_leaves_no_scratch_directory_behind(monkeypatch, tmp_path):
    """Repeated runs must not accumulate scratch trees and exhaust the disk."""

    def fake_run(command, root, *, timeout=120):
        return " ".join(command), 0, {
            "outcome": "PASS",
            "nodeids": ["tests/x.py::proof"],
            "parsed": {"summary_present": True, "passed": 1},
            "output": "tests/x.py::proof PASSED\n1 passed in 0.10s\n",
        }

    monkeypatch.setattr(runner, "_run", fake_run)
    run_pilot_acceptance(tmp_path, database_target="none", browser_base_url=None, external_sandbox=True)

    assert not list(tmp_path.glob(".tmp-pilot-acceptance-*"))
    assert not list(tmp_path.glob("pilot-receipt-*.json"))


def test_runner_records_a_named_gap_for_every_unmapped_postgres_finding(monkeypatch, tmp_path):
    """A finding with no PostgreSQL test says so, instead of borrowing one."""

    monkeypatch.delenv("VL360_TEST_DATABASE_URL", raising=False)
    bundle = run_pilot_acceptance(tmp_path, database_target="none", browser_base_url=None, external_sandbox=False)

    for finding in P1_FINDINGS:
        evidence = bundle.sections[finding].layers["postgres"]
        assert evidence["outcome"] != "PASS"
        assert evidence["availability_gap"]


def test_loopback_only_postgres_dsn_is_required(monkeypatch):
    """A non-loopback DSN is refused so the runner cannot touch a shared database."""

    monkeypatch.setenv("VL360_TEST_DATABASE_URL", "postgresql://u:p@db.example.com:5432/prod")
    assert runner._loopback_pg_dsn() is None

    monkeypatch.setenv("VL360_TEST_DATABASE_URL", "postgresql://u:p@127.0.0.1:55432/disposable")
    monkeypatch.setenv("VL360_TEST_DATABASE_CONFIRM", "disposable")
    assert runner._loopback_pg_dsn() is not None


def test_loopback_postgres_requires_explicit_disposable_marker(monkeypatch):
    """Loopback reachability alone must never authorize database mutation."""

    monkeypatch.setenv("VL360_TEST_DATABASE_URL", "postgresql://u:p@127.0.0.1:55432/disposable")
    monkeypatch.delenv("VL360_TEST_DATABASE_CONFIRM", raising=False)
    monkeypatch.delenv("VL360_TEST_DATABASE_DISPOSABLE", raising=False)

    assert runner._loopback_pg_dsn() is None

    monkeypatch.setenv("VL360_TEST_DATABASE_DISPOSABLE", "true")
    assert runner._loopback_pg_dsn() is not None


def test_acceptance_helpers_read_the_explicit_alternate_root(monkeypatch, tmp_path):
    """Authority and attestation helpers must not fall back to module ROOT."""

    alternate = tmp_path / "alternate-checkout"
    (alternate / "config").mkdir(parents=True)
    authority = ROOT / "config" / "release-authority.json"
    (alternate / "config" / "release-authority.json").write_text(
        authority.read_text(encoding="utf-8"), encoding="utf-8"
    )
    monkeypatch.setattr(runner, "ROOT", tmp_path / "wrong-root")

    contract = runner._authority_contract(alternate)
    references = runner._attestation_references(alternate)

    assert contract is not None
    assert references is not None
    assert set(references) == {"runner-test", "owner-test", "countersign-test", "ci-test"}


def test_postgres_credentials_never_reach_the_bundle(monkeypatch, tmp_path):
    """The DSN is read from the environment and must not appear in the artifact."""

    secret = "postgresql://vl360:sup3rsecret@127.0.0.1:55432/disposable"
    monkeypatch.setenv("VL360_TEST_DATABASE_URL", secret)

    def fake_run(command, root, *, timeout=120):
        return " ".join(command), 0, {
            "outcome": "PASS",
            "nodeids": ["agent/tests/x.py::proof"],
            "parsed": {"summary_present": True, "passed": 1},
            "output": "agent/tests/x.py::proof PASSED\n1 passed in 0.10s\n",
        }

    monkeypatch.setattr(runner, "_run", fake_run)
    bundle = run_pilot_acceptance(
        tmp_path,
        database_target="disposable-postgres",
        browser_base_url=None,
        external_sandbox=False,
        postgres_proof=True,
    )

    serialised = json.dumps(bundle.to_dict())
    assert "sup3rsecret" not in serialised
    assert secret not in serialised


def test_runner_signature_covers_the_final_gate(pilot_attestation_keys):
    """Runner phải QUYẾT rồi mới KÝ, không được ký rồi mới quyết.

    `gate` NẰM TRONG payload được ký: `unsigned_payload()` chỉ bỏ ra
    `output_sha256` và `attestations`, mọi trường khác — kể cả `gate` — đều được
    phủ. Thứ tự cũ ở `run_pilot_acceptance()` là:

        bundle.attestations = _runner_attestations(bundle)   # ký
        bundle.gate = _evaluate_pilot_gate_contents(bundle)  # rồi mới quyết

    nên chữ ký cam kết vào giá trị MẶC ĐỊNH của dataclass ("NO_GO"), không phải
    vào phán quyết vừa ghi. Hệ quả là fail-CLOSED (chỉ biến một GO_CONDITIONAL
    hợp lệ thành NO_GO, không bao giờ tạo ra cổng xanh), và hiện đang bị che vì
    gate luôn ra đúng giá trị mặc định — nhưng runner vẫn đang bất đồng với mọi
    verifier về sau, và với chính countersigner (ký trên bundle ĐỌC TỪ ĐĨA, tức
    trên gate cuối).

    Bộ test cũ không bắt được vì fixture dùng thứ tự NGƯỢC LẠI (đúng):
    `complete_fixture_bundle_for_p1()` đặt `gate=` trong constructor rồi mới ký.
    """
    bundle = complete_fixture_bundle_for_p1()

    # Dựng lại đúng trình tự sản xuất, với gate KHÁC giá trị mặc định.
    bundle.gate = runner._evaluate_pilot_gate_contents(bundle)
    bundle.attestations = runner._runner_attestations(bundle)
    bundle.output_sha256 = runner._bundle_digest(bundle)

    assert bundle.gate == "GO_CONDITIONAL", (
        "fixture phải cho ra một gate KHÁC mặc định, nếu không test thành rỗng"
    )
    recomputed = payload_digest(bundle.unsigned_payload())
    runner_attestation = next(a for a in bundle.attestations if a["role"] == "runner")
    assert runner_attestation["payload_sha256"] == recomputed, (
        "chữ ký của runner không phủ gate cuối cùng — digest cũ (stale)"
    )


def test_signing_before_deciding_would_produce_a_stale_digest(pilot_attestation_keys):
    """Chứng minh bất biến trên KHÔNG tầm thường: `gate` NẰM TRONG payload ký.

    Nếu `gate` không được phủ, ký trước hay ký sau đều ra cùng digest và test
    bất biến ở trên sẽ luôn xanh một cách vô nghĩa. Ở đây ta ký trên một gate
    rồi đổi gate, và digest PHẢI lệch.
    """
    bundle = complete_fixture_bundle_for_p1()

    bundle.gate = "NO_GO"                       # giá trị mặc định của dataclass
    signed_over = payload_digest(bundle.unsigned_payload())

    bundle.gate = "GO_CONDITIONAL"              # phán quyết ghi SAU khi đã ký
    assert signed_over != payload_digest(bundle.unsigned_payload()), (
        "gate không nằm trong payload được ký — test bất biến ở trên vô nghĩa"
    )
