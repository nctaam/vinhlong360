#!/usr/bin/env python3
"""Run the local, proof-first closed-pilot acceptance gate.

The runner is deliberately conservative: unavailable PostgreSQL, browser, and
provider integrations are recorded as explicit evidence gaps and therefore
cannot accidentally turn into a launch approval.  No command in this module
contacts a production service or a third-party provider.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Literal
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.control_plane.attestation import (  # noqa: E402
    build_attestation,
    evaluate_attestations,
    load_key_references,
    payload_digest,
    resolve_key,
)
from agent.control_plane.evidence import classify_verdict, parse_test_output, verify_probe_receipt


ACCEPTANCE_LAYERS = (
    "unit",
    "postgres",
    "multi_process",
    "browser",
    "external_side_effect",
)
DECISION_REQUIRED_ITEMS = ("legal", "provider", "residency", "public_indexing")
PUBLIC_LAUNCH_VERDICT = "NO_GO"
_PROBE_RECEIPT_FILES = {
    "multiprocess-scheduler": "multiprocess-scheduler-receipt.json",
    "provider-sandbox": "provider-sandbox-receipt.json",
    "proxy-contract": "proxy-contract-receipt.json",
    "backup-restore-checksum": "backup-restore-receipt.json",
    "rollback-local-rehearsal": "rollback-rehearsal-receipt.json",
}
_PROBE_ENVIRONMENTS = {
    "multiprocess-scheduler": "local-disposable-postgres",
    "provider-sandbox": "local-deterministic-provider-sandbox",
    "proxy-contract": "local-loopback-proxy",
    "backup-restore-checksum": "local-disposable-postgres",
    "rollback-local-rehearsal": "local-rollback-rehearsal",
}
_PROBE_COMMAND_MARKERS = {
    "multiprocess-scheduler": ("probe_multiprocess_scheduler.py", "--workers", "--slots"),
    "provider-sandbox": ("probe_provider_sandbox.py", "--mode", "deterministic"),
    "proxy-contract": ("probe_proxy_contract.py", "--base-url"),
    "backup-restore-checksum": ("scripts/ops/restore_drill.py", "--backup"),
    "rollback-local-rehearsal": ("probe_rollback.py",),
}
_HEAD_SHA = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_PYTEST_SUCCESS_LINE = re.compile(
    r"^\s*(?P<nodeid>.+?)\s+(?:PASSED|SKIPPED|XFAIL|XPASS)(?:\s|$)",
    re.IGNORECASE,
)
# A layer accepts only kinds that can actually cross its boundary: an in-process
# pytest capture is not browser, provider, or database proof, so "pytest" is
# confined to the unit layer.
_EVIDENCE_KINDS = {
    "unit": {"pytest", "cross-boundary-proof"},
    "postgres": {"postgresql-drill"},
    "multi_process": {"multi-process-drill"},
    "browser": {"browser-drill"},
    "external_side_effect": {"external-drill", "sandbox-receipt"},
}
_PROVENANCE_FIELDS = ("capture_id", "source", "finding_id", "layer")
_CANONICAL_EVIDENCE_FIELDS = (
    "finding_id",
    "layer",
    "command",
    "environment",
    "nodeids",
    "return_code",
    "outcome",
    "evidence_kind",
    "summary",
    "proof_id",
    "observed_at",
    "rollback_note",
    "provenance",
    "captured_output",
    "owner",
    "output_sha256",
    "checksum_verified",
    "stale",
    "availability_gap",
    "drill_steps",
    "execution_receipt",
)


def load_probe_receipts(
    evidence_dir: Path | None,
    *,
    expected_head_sha: str | None = None,
) -> dict[str, dict[str, Any]]:
    """Load only the fixed probe receipt set, treating absence as unavailable."""

    directory = Path(evidence_dir).resolve() if evidence_dir is not None else None
    statuses: dict[str, dict[str, Any]] = {}
    for probe_id, filename in _PROBE_RECEIPT_FILES.items():
        path = directory / filename if directory is not None else None
        if path is None or not path.is_file():
            statuses[probe_id] = _missing_probe_status()
            continue
        payload, read_status = _read_probe_receipt(path)
        if read_status is not None:
            statuses[probe_id] = read_status
            continue
        verification = verify_probe_receipt(payload)
        reasons = [*verification.reasons, *_probe_slot_reasons(probe_id, payload, expected_head_sha)]
        statuses[probe_id] = {
            "verdict": "BLOCKED" if reasons else verification.verdict,
            "reasons": reasons,
            "receipt": payload,
        }
    return statuses


def _missing_probe_status() -> dict[str, Any]:
    return {"verdict": "UNAVAILABLE", "reasons": ["probe receipt missing"]}


def _read_probe_receipt(path: Path) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, {
            "verdict": "BLOCKED",
            "reasons": [f"unable to read probe receipt: {type(exc).__name__}"],
        }
    if not isinstance(payload, dict):
        return None, {"verdict": "BLOCKED", "reasons": ["probe receipt must be a JSON object"]}
    return payload, None


def _probe_slot_reasons(probe_id: str, payload: dict[str, Any], expected_head_sha: str | None) -> list[str]:
    reasons: list[str] = []
    if payload.get("probe_id") != probe_id:
        reasons.append("probe_id does not match expected slot")
    if payload.get("environment_id") != _PROBE_ENVIRONMENTS[probe_id]:
        reasons.append("environment_id does not match expected probe environment")
    command = payload.get("command")
    markers = _PROBE_COMMAND_MARKERS[probe_id]
    normalized_command = command.replace("\\", "/").lower() if isinstance(command, str) else ""
    if not normalized_command or not all(marker.lower() in normalized_command for marker in markers):
        reasons.append("command does not match expected probe identity")
    if probe_id == "backup-restore-checksum" and "--target-dsn" in str(command):
        reasons.append("restore probe must not carry DSN in command arguments")
    if expected_head_sha and payload.get("head_sha") != expected_head_sha:
        reasons.append("head_sha does not match checked-out HEAD")
    return reasons


def _load_checkout_probe_receipts(root: Path, evidence_dir: Path | None) -> dict[str, dict[str, Any]]:
    if evidence_dir is None:
        return load_probe_receipts(None, expected_head_sha=_head_sha(root))
    resolved = evidence_dir if evidence_dir.is_absolute() else root / evidence_dir
    return load_probe_receipts(resolved, expected_head_sha=_head_sha(root))


def _receipt_fields(receipt: Any) -> set[str] | None:
    """Return the exact receipt schema when the value is a mapping."""

    required = {
        "version", "issuer", "finding_id", "layer", "command_sha256",
        "output_sha256", "return_code", "head_sha", "working_tree_digest",
    }
    if not isinstance(receipt, dict) or set(receipt) != required:
        return None
    return required


def _receipt_binding_matches(receipt: dict[str, Any], evidence: dict[str, Any]) -> bool:
    """Check receipt version, issuer, and finding/layer binding."""

    if type(receipt.get("version")) is not int or receipt["version"] != 1 or receipt.get("issuer") != "run_pilot_acceptance":
        return False
    return receipt.get("finding_id") == evidence.get("finding_id") and receipt.get("layer") == evidence.get("layer")


def _receipt_capture_matches(receipt: dict[str, Any], evidence: dict[str, Any]) -> bool:
    """Check receipt hashes and return code against the captured evidence."""

    command = evidence.get("command")
    if not isinstance(command, str) or sha256(command.encode("utf-8")).hexdigest() != receipt.get("command_sha256"):
        return False
    return receipt.get("output_sha256") == evidence.get("output_sha256") and receipt.get("return_code") == evidence.get("return_code")


def _receipt_environment_matches(receipt: dict[str, Any], evidence: dict[str, Any]) -> bool:
    """Check receipt checkout identity against the evidence environment."""

    environment = evidence.get("environment")
    if not isinstance(environment, dict):
        return False
    return receipt.get("head_sha") == environment.get("head_sha") and receipt.get("working_tree_digest") == environment.get("working_tree_digest")


def _receipt_hashes_are_valid(receipt: dict[str, Any]) -> bool:
    """Check the two digest fields carried by a receipt."""

    for field_name in ("command_sha256", "output_sha256"):
        value = receipt.get(field_name)
        if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
            return False
    return True


def _receipt_identity_is_valid(receipt: dict[str, Any], evidence: dict[str, Any]) -> bool:
    """Validate receipt identity format for the declared outcome."""

    head_value = receipt.get("head_sha")
    tree_value = receipt.get("working_tree_digest")
    if evidence.get("outcome") == "PASS":
        return isinstance(head_value, str) and _HEAD_SHA.fullmatch(head_value) is not None and isinstance(tree_value, str) and _SHA256.fullmatch(tree_value) is not None
    return isinstance(head_value, str) and bool(head_value.strip()) and isinstance(tree_value, str) and bool(tree_value.strip())


def _execution_receipt(evidence: dict[str, Any]) -> dict[str, Any] | None:
    """Validate the runner receipt binding one capture to its execution context."""

    receipt = evidence.get("execution_receipt")
    required = _receipt_fields(receipt)
    if required is None:
        return None
    if not _receipt_binding_matches(receipt, evidence) or not _receipt_capture_matches(receipt, evidence):
        return None
    if not _receipt_environment_matches(receipt, evidence) or not _receipt_hashes_are_valid(receipt):
        return None
    if not _receipt_identity_is_valid(receipt, evidence) or type(receipt.get("return_code")) is not int:
        return None
    return {key: receipt[key] for key in sorted(required)}


_PARSED_EVIDENCE_KINDS = frozenset({"pytest", "postgresql-drill", "multi-process-drill", "cross-boundary-proof"})


def _captured_output_supports_outcome(evidence: dict[str, Any]) -> bool:
    """Check that a record's captured text actually supports its declared verdict.

    A test-shaped capture must contain a real summary, must classify to the
    outcome the record declares, and must mention every node id it claims to
    have exercised.  This is what stops a hand-written string from being
    accepted as a passing run.
    """

    captured_output = evidence.get("captured_output")
    if not _transcript_names_its_own_work(evidence, captured_output):
        return False
    if evidence.get("evidence_kind") not in _PARSED_EVIDENCE_KINDS:
        # Browser and external drills do not emit a pytest tally, so the
        # transcript/nodeid binding above is the whole check available here.
        return True
    try:
        parsed = parse_test_output(captured_output, evidence["return_code"])
    except (TypeError, ValueError):
        return False
    return parsed.summary_present and classify_verdict(parsed, frozenset()) == evidence.get("outcome")


def _transcript_names_its_own_work(evidence: dict[str, Any], captured_output: Any) -> bool:
    """Check that a record's transcript exists and names every node id it claims."""

    if not isinstance(captured_output, str) or not captured_output.strip():
        return False
    if type(evidence.get("return_code")) is not int:
        return False
    nodeids = evidence.get("nodeids")
    if not isinstance(nodeids, list) or not nodeids:
        return False
    return all(isinstance(nodeid, str) and nodeid and nodeid in captured_output for nodeid in nodeids)


def _canonical_metadata_is_valid(evidence: dict[str, Any]) -> bool:
    """Validate the non-digest metadata included in the canonical payload."""

    return isinstance(evidence.get("summary", {}), dict) and isinstance(evidence.get("proof_id", ""), str)


def _captured_output_digest_is_valid(evidence: dict[str, Any]) -> bool:
    """Validate the captured output type, digest format, and byte binding."""

    output_sha256 = evidence.get("output_sha256")
    captured_output = evidence.get("captured_output")
    if not isinstance(output_sha256, str) or _SHA256.fullmatch(output_sha256) is None:
        return False
    if not isinstance(captured_output, str):
        return False
    return sha256(captured_output.encode("utf-8")).hexdigest() == output_sha256


def _canonical_provenance(evidence: dict[str, Any]) -> dict[str, str] | None:
    """Return provenance fields in their deterministic order and types."""

    provenance = evidence.get("provenance")
    if not isinstance(provenance, dict) or set(provenance) != set(_PROVENANCE_FIELDS):
        return None
    canonical = {}
    for key in _PROVENANCE_FIELDS:
        value = provenance.get(key, "")
        if not isinstance(value, str):
            return None
        canonical[key] = value
    return canonical


def _canonical_evidence_payload(evidence: dict[str, Any]) -> dict[str, Any] | None:
    """Return only the signed, deterministic fields of one evidence record."""

    if not _canonical_metadata_is_valid(evidence) or not _captured_output_digest_is_valid(evidence):
        return None
    canonical_provenance = _canonical_provenance(evidence)
    if canonical_provenance is None:
        return None
    canonical_receipt = _execution_receipt(evidence)
    if canonical_receipt is None:
        return None
    payload = {key: evidence.get(key, "") for key in _CANONICAL_EVIDENCE_FIELDS}
    payload["provenance"] = canonical_provenance
    payload["execution_receipt"] = canonical_receipt
    return payload


def _evidence_digest(evidence: dict[str, Any]) -> str:
    payload = _canonical_evidence_payload(evidence)
    if payload is None:
        return ""
    try:
        canonical = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError):
        return ""
    return sha256(canonical.encode("utf-8")).hexdigest()


def _bundle_digest(bundle: "AcceptanceBundle") -> str:
    unsigned = bundle.to_dict()
    unsigned.pop("output_sha256", None)
    canonical = json.dumps(unsigned, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return sha256(canonical.encode("utf-8")).hexdigest()


def _is_digest_excluded(relative_path: str) -> bool:
    """Report whether one repository-relative path is outside the tree digest.

    Acceptance artifacts and temporary/build directories are excluded because
    the runner creates them while producing its own bundle.  Matching is done
    on whole path segments so a real file such as ``.tmpl`` is never mistaken
    for one of the runner's own ``.tmp-*`` scratch directories.
    """

    parts = [part for part in relative_path.split("/") if part]
    if not parts:
        return False
    if parts[0] == ".git" or parts[0] in {"artifacts", "graphify-out"}:
        return True
    if parts[0].startswith(".tmp-"):
        return True
    return parts[:2] in (["web-nuxt", ".nuxt"], ["web-nuxt", ".output"])


def _status_entries(status_bytes: bytes) -> list[tuple[bytes, bytes]]:
    """Split ``git status -z`` output into (status code, path) pairs.

    A rename or copy record is followed by a bare origin path carrying no
    status prefix.  Consuming that field here stops it being sliced as if it
    had one, which produced a nonexistent path and collapsed the whole digest.
    """

    entries = status_bytes.split(b"\0")
    pairs: list[tuple[bytes, bytes]] = []
    index = 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if len(entry) < 4:
            continue
        status_code = entry[:2]
        if b"R" in status_code or b"C" in status_code:
            index += 1
        pairs.append((status_code, entry[3:]))
    return pairs


def _untracked_bytes(root: Path, relative_path: str) -> bytes | None:
    """Read one untracked file, or ``None`` when it escapes the root or fails."""

    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root.resolve())
        return candidate.read_bytes()
    except (OSError, ValueError):
        return None


def _working_tree_digest(root: Path) -> str:
    """Hash tracked diffs plus source-like untracked files in this checkout.

    ``git diff --binary HEAD`` already binds every tracked addition, edit and
    deletion byte-for-byte, so only untracked content is read from disk here.
    Status entries are hashed as raw bytes together with their status code, and
    the rename/copy origin field is consumed rather than parsed as a path.
    """

    try:
        diff = subprocess.run(
            ["git", "diff", "--binary", "HEAD", "--"],
            cwd=root,
            capture_output=True,
            timeout=60,
            check=False,
        )
        status = subprocess.run(
            ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
            cwd=root,
            capture_output=True,
            timeout=60,
            check=False,
        )
        if diff.returncode != 0 or status.returncode != 0:
            return "unknown"
        digest = sha256()
        diff_bytes = diff.stdout if isinstance(diff.stdout, bytes) else str(diff.stdout).encode("utf-8")
        digest.update(b"tracked-diff\0")
        digest.update(diff_bytes)
        status_bytes = status.stdout if isinstance(status.stdout, bytes) else str(status.stdout).encode("utf-8")
        for status_code, path_bytes in _status_entries(status_bytes):
            relative_path = path_bytes.decode("utf-8", errors="surrogateescape").replace("\\", "/")
            if _is_digest_excluded(relative_path):
                continue
            digest.update(b"status\0")
            digest.update(status_code)
            digest.update(b"\0")
            digest.update(path_bytes)
            digest.update(b"\0")
            if status_code != b"??":
                # Tracked changes are already covered by the diff above.
                continue
            content = _untracked_bytes(root, relative_path)
            if content is None:
                # An untracked file whose bytes cannot be read cannot be bound
                # by this digest, so the gate must fail closed rather than
                # record a hash that covers only the path.
                return "unknown"
            digest.update(b"untracked\0")
            digest.update(content)
            digest.update(b"\0")
        return digest.hexdigest()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def _attestation_references(root: Path | None = None) -> dict[str, Any] | None:
    """Read the signing identities the release authority authorises.

    The bundle can never introduce its own key identity: an attestation whose
    ``key_id`` is absent from this contract is refused.
    """

    try:
        checked_root = Path(root).resolve() if root is not None else ROOT
        payload = json.loads((checked_root / "config" / "release-authority.json").read_text(encoding="utf-8"))
        pilot = payload["pilot_acceptance"]
        if pilot.get("attestation_schemes") != ["hmac-sha256"]:
            return None
        return load_key_references(pilot.get("attestation_keys"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None


def _authority_identity_is_valid(payload: dict[str, Any]) -> bool:
    """Check the release authority identity and checkout source contract."""

    if payload.get("authority_id") != "release-control" or payload.get("owner") != "service-owner":
        return False
    return payload.get("head_source") == "git:HEAD" and payload.get("max_age_hours") == 24


def _pilot_static_contract_is_valid(pilot: dict[str, Any]) -> bool:
    """Check static pilot fields that bind the runner to its authority."""

    expected = {
        "runner": "scripts/ops/run_pilot_acceptance.py",
        "bundle": "artifacts/pilot-acceptance.json",
        "owner": "service-owner",
        "owner_signoff_required": True,
        "required_layers": list(ACCEPTANCE_LAYERS),
        "closed_pilot_verdict": "GO_CONDITIONAL",
        "external_policy": "sandbox-only-no-provider-calls",
    }
    return all(pilot.get(key) == value for key, value in expected.items())


def _decision_items_are_valid(items: Any) -> bool:
    """Check the authority's required decision item names."""

    return (
        isinstance(items, list)
        and all(isinstance(item, str) and item for item in items)
        and set(items) == set(DECISION_REQUIRED_ITEMS)
    )


def _authority_limits_are_valid(public: Any, max_age_hours: Any) -> bool:
    """Check public verdict and freshness limit types."""

    return isinstance(public, str) and type(max_age_hours) is int and max_age_hours > 0


def _authority_contract(root: Path | None = None) -> tuple[set[str], str, int, str] | None:
    """Read the decision/public gate contract used by the release authority."""

    try:
        checked_root = Path(root).resolve() if root is not None else ROOT
        payload = json.loads((checked_root / "config" / "release-authority.json").read_text(encoding="utf-8"))
        pilot = payload["pilot_acceptance"]
        if not _authority_identity_is_valid(payload) or not _pilot_static_contract_is_valid(pilot):
            return None
        items = pilot["decision_required_items"]
        public = pilot["public_launch_verdict"]
        max_age_hours = pilot["max_age_hours"]
        if not _decision_items_are_valid(items) or not _authority_limits_are_valid(public, max_age_hours):
            return None
        return set(items), public, max_age_hours, "service-owner"
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None
P1_FINDINGS = (
    "F-01", "F-02", "F-03", "F-04", "F-05", "F-06", "F-07", "F-08",
    "F-09", "F-10", "F-11", "F-12", "F-13", "F-14", "F-15", "F-16",
    "F-17", "F-32", "F-34", "F-38", "F-40", "F-41", "F-42", "F-44",
    "F-47", "F-49", "F-53", "F-69",
)
POSTGRES_FINDING_NODEIDS: dict[str, tuple[str, ...]] = {
    # Only findings whose defect is actually exercised by a PostgreSQL test may
    # appear here.  Adding an entry requires naming the test that reproduces
    # that finding; a blanket bind would make one capture stand in for evidence
    # it does not contain.
    # F-42: scheduled community post needs a lease/CAS consumer (audit :246).
    "F-42": (
        "agent/tests/test_case_contention_postgres.py::test_community_cas_and_due_lease_have_one_winner",
    ),
    # F-49: moderation approve/reject must have exactly one winning transition
    # under two concurrent operators (audit :249).
    "F-49": (
        "agent/tests/test_case_contention_postgres.py::test_only_one_operator_can_hold_one_work_item",
        "agent/tests/test_case_contention_postgres.py::test_racing_applies_write_the_entry_once",
        "agent/tests/test_case_contention_postgres.py::test_racing_rollbacks_undo_the_entry_once",
    ),
    # F-53: outbox at-least-once must not send one notification twice between
    # live dispatchers (audit :250).  This does NOT prove provider-side
    # idempotency across a crash window; that remains a decision item.
    "F-53": (
        "agent/tests/test_case_contention_postgres.py::test_racing_dispatchers_never_send_one_notification_twice",
    ),
}
LOCAL_DRILL_NODEIDS = (
    "tests/integration/test_cross_boundary_proof.py",
    "agent/tests/test_case_proof_first.py::test_validate_decision_uses_only_evidence_in_required_scope_and_time_window",
    "agent/tests/test_lifecycle_registry.py::test_export_manifest_declares_cursor_and_checksums",
    "agent/tests/test_lifecycle_registry.py::test_failed_media_receipt_can_retry",
    "tests/test_cache.py::test_owner_scoped_put_and_get_isolate_identical_queries",
)
Outcome = Literal["PASS", "BLOCKED", "UNCLASSIFIED"]
GateVerdict = Literal["GO_CONDITIONAL", "NO_GO"]


@dataclass
class EvidenceSection:
    """One P1's layered evidence, kept mutable for fixture construction."""

    outcome: Outcome = "UNCLASSIFIED"
    layers: dict[str, dict[str, Any]] = field(default_factory=dict)
    stale: bool = False
    cross_boundary_proof: bool = False
    decision_required: bool = False
    owner_signoff: bool = False
    finding_id: str = ""

    @property
    def verdict(self) -> Outcome:
        return self.outcome

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AcceptanceBundle:
    """Serializable acceptance evidence for all P1 findings."""

    sections: dict[str, EvidenceSection] = field(default_factory=dict)
    artifact_id: str = ""
    head_sha: str = ""
    generated_at: str = ""
    owner: str = "service-owner"
    owner_signoff: bool = False
    rollback_note: str = ""
    cross_boundary_proof: bool = False
    stale: bool = False
    decision_required: dict[str, bool] = field(default_factory=dict)
    gate: GateVerdict = "NO_GO"
    environment: dict[str, Any] = field(default_factory=dict)
    output_sha256: str = ""
    max_age_hours: int = 24
    public_launch_gate: Literal["NO_GO"] = "NO_GO"
    attestations: list[dict[str, Any]] = field(default_factory=list)

    def unsigned_payload(self) -> dict[str, Any]:
        """Return the payload the attestation signatures cover.

        The envelope digest and the signatures themselves are excluded so that
        appending an attestation does not invalidate the ones already present,
        while ``output_sha256`` still covers the attestation list and therefore
        detects any later edit to it.
        """

        payload = self.to_dict()
        payload.pop("output_sha256", None)
        payload.pop("attestations", None)
        return payload

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["bundle_kind"] = "pilot-acceptance-v1"
        payload["sections"] = {
            name: section.to_dict() if isinstance(section, EvidenceSection) else section
            for name, section in self.sections.items()
        }
        payload["p1_findings"] = list(P1_FINDINGS)
        payload["acceptance_layers"] = list(ACCEPTANCE_LAYERS)
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AcceptanceBundle":
        raw_sections = payload.get("sections", {})
        if not isinstance(raw_sections, dict):
            raise ValueError("sections must be an object")
        sections: dict[str, EvidenceSection] = {}
        for name, value in raw_sections.items():
            if isinstance(value, EvidenceSection):
                sections[str(name)] = value
            elif isinstance(value, dict):
                sections[str(name)] = EvidenceSection(**value)
            else:
                raise ValueError("section must be an object")
        fields = {
            key: payload[key]
            for key in cls.__dataclass_fields__
            if key in payload and key != "sections"
        }
        return cls(sections=sections, **fields)

    def write(self, path: Path) -> str:
        digest = _bundle_digest(self)
        # Always regenerate the envelope attestation after serializable fields change.
        self.output_sha256 = digest
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return digest


def verify_pilot_bundle(path: Path, root: Path | None = None) -> tuple[Outcome, tuple[str, ...], str]:
    """Verify the custom pilot envelope without treating it as launch-safety state."""

    try:
        raw = json.loads(
            Path(path).read_text(encoding="utf-8"),
            parse_constant=lambda constant: (_ for _ in ()).throw(ValueError(f"non-finite JSON constant: {constant}")),
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        return "BLOCKED", (f"unable to read bundle: {type(exc).__name__}",), ""
    if not isinstance(raw, dict) or raw.get("bundle_kind") != "pilot-acceptance-v1":
        return "BLOCKED", ("unsupported pilot bundle kind",), ""
    declared = raw.get("output_sha256")
    if not isinstance(declared, str) or _SHA256.fullmatch(declared) is None:
        return "BLOCKED", ("pilot bundle checksum is missing or malformed",), ""
    unsigned = dict(raw)
    unsigned.pop("output_sha256", None)
    try:
        checked = sha256(json.dumps(unsigned, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()
    except (TypeError, ValueError):
        return "BLOCKED", ("pilot bundle contains non-canonical JSON values",), ""
    if declared != checked:
        return "BLOCKED", ("pilot bundle checksum mismatch",), checked
    try:
        checked_root = Path(root).resolve() if root is not None else ROOT
        gate = evaluate_pilot_gate(AcceptanceBundle.from_dict(raw), root=checked_root)
    except (TypeError, ValueError, KeyError, AttributeError, OverflowError):
        return "BLOCKED", ("pilot bundle is malformed",), checked
    return ("PASS", (), checked) if gate == "GO_CONDITIONAL" else ("BLOCKED", ("pilot acceptance gate is NO_GO",), checked)


def _section_outcome(value: object) -> Outcome:
    if isinstance(value, EvidenceSection):
        value = value.outcome
    if value in {"PASS", "BLOCKED", "UNCLASSIFIED"}:
        return value  # type: ignore[return-value]
    return "UNCLASSIFIED"


def _layer_values(section: EvidenceSection) -> dict[str, dict[str, Any]]:
    if not isinstance(section.layers, dict):
        return {}
    return section.layers


def _coverage_key(finding: str, layer: str) -> str:
    """Return the stable identifier a countersignature uses for one record."""

    return f"{finding}/{layer}"


def _countersignature_covers_every_passing_record(bundle: AcceptanceBundle) -> bool:
    """Check the countersignature re-executed every record the bundle calls PASS."""

    countersignature = next(
        (item for item in bundle.attestations if isinstance(item, dict) and item.get("role") == "countersign"),
        None,
    )
    if countersignature is None:
        return False
    covers = countersignature.get("covers")
    if not isinstance(covers, list):
        return False
    expected = {
        _coverage_key(finding, layer)
        for finding, section in bundle.sections.items()
        if isinstance(section, EvidenceSection)
        for layer, evidence in _layer_values(section).items()
        if isinstance(evidence, dict) and evidence.get("outcome") == "PASS"
    }
    return expected.issubset(set(covers)) and bool(expected)


def _validate_bundle_shape(bundle: Any) -> bool:
    """Validate top-level bundle type and identity fields."""

    if not isinstance(bundle, AcceptanceBundle) or set(bundle.sections) != set(P1_FINDINGS):
        return False
    if type(bundle.stale) is not bool or bundle.stale:
        return False
    if not isinstance(bundle.artifact_id, str) or not bundle.artifact_id.strip():
        return False
    return isinstance(bundle.head_sha, str) and _HEAD_SHA.fullmatch(bundle.head_sha) is not None


def _bundle_timestamp(bundle: AcceptanceBundle) -> datetime | None:
    """Validate envelope freshness and return the shared current time."""

    if not isinstance(bundle.generated_at, str) or not bundle.generated_at.strip():
        return None
    if type(bundle.max_age_hours) is not int or bundle.max_age_hours <= 0:
        return None
    now = datetime.now(timezone.utc)
    observed = datetime.fromisoformat(bundle.generated_at.replace("Z", "+00:00"))
    if observed.tzinfo is None or observed.astimezone(timezone.utc) > now:
        return None
    if (now - observed.astimezone(timezone.utc)).total_seconds() > bundle.max_age_hours * 3600:
        return None
    return now


def _validate_authority_fields(bundle: AcceptanceBundle, checked_root: Path) -> tuple[set[str], str, int, str] | None:
    """Validate public verdict, authority contract, owner, and rollback note."""

    if bundle.public_launch_gate != PUBLIC_LAUNCH_VERDICT:
        return None
    contract = _authority_contract(checked_root)
    if contract is None:
        return None
    required_decisions, public_verdict, authority_max_age_hours, authority_owner = contract
    if public_verdict != PUBLIC_LAUNCH_VERDICT or bundle.public_launch_gate != public_verdict:
        return None
    if bundle.max_age_hours != authority_max_age_hours:
        return None
    if type(bundle.owner) is not str or bundle.owner != authority_owner:
        return None
    if type(bundle.rollback_note) is not str or not bundle.rollback_note.strip():
        return None
    return contract


def _validate_bundle_environment(bundle: AcceptanceBundle, checked_root: Path) -> str | None:
    """Bind envelope environment and safety controls to the current checkout."""

    if not isinstance(bundle.environment, dict) or not bundle.environment:
        return None
    if bundle.environment.get("head_sha") != bundle.head_sha:
        return None
    working_tree_digest = bundle.environment.get("working_tree_digest")
    current_working_tree_digest = _working_tree_digest(checked_root)
    if not isinstance(working_tree_digest, str) or not _SHA256.fullmatch(working_tree_digest):
        return None
    if current_working_tree_digest == "unknown" or working_tree_digest != current_working_tree_digest:
        return None
    for safety_key in ("production_calls", "secrets_collected", "raw_personal_data"):
        if bundle.environment.get(safety_key) is not False:
            return None
    if bundle.owner_signoff is not True or bundle.cross_boundary_proof is not True:
        return None
    return working_tree_digest


def _gate_identity_valid(bundle: Any, checked_root: Path) -> tuple[datetime, str, tuple[set[str], str, int, str]] | None:
    """Run the ordered envelope, authority, and checkout identity checks."""

    if not _validate_bundle_shape(bundle):
        return None
    current_head = _head_sha(checked_root)
    if current_head == "unknown" or bundle.head_sha != current_head:
        return None
    now = _bundle_timestamp(bundle)
    if now is None:
        return None
    contract = _validate_authority_fields(bundle, checked_root)
    if contract is None:
        return None
    working_tree_digest = _validate_bundle_environment(bundle, checked_root)
    if working_tree_digest is None:
        return None
    return now, working_tree_digest, contract


def _section_flags_are_valid(section: EvidenceSection) -> bool:
    """Validate section field types and the passing control flags."""

    if type(section.outcome) is not str or type(section.stale) is not bool:
        return False
    if type(section.cross_boundary_proof) is not bool or type(section.decision_required) is not bool:
        return False
    if type(section.owner_signoff) is not bool or type(section.finding_id) is not str:
        return False
    return section.stale is False and section.outcome == "PASS" and section.cross_boundary_proof is True


def _validate_section_header(section: Any, finding: str) -> bool:
    """Validate one P1 section's outcome and control flags."""

    if not isinstance(section, EvidenceSection) or not _section_flags_are_valid(section):
        return False
    if section.finding_id != finding:
        return False
    return not section.decision_required or section.owner_signoff is True


def _validate_layer_identity(evidence: dict[str, Any], finding: str, layer: str) -> bool:
    """Validate a layer's finding, freshness flag, kind, and outcome."""

    if evidence.get("finding_id") != finding or evidence.get("layer") != layer:
        return False
    if evidence.get("stale") is not False or evidence.get("outcome") != "PASS":
        return False
    kind = evidence.get("evidence_kind")
    return isinstance(kind, str) and kind in _EVIDENCE_KINDS[layer]


def _validate_layer_metadata(evidence: dict[str, Any], bundle: AcceptanceBundle) -> bool:
    """Validate required command, owner, and rollback metadata."""

    required = ("command", "environment", "nodeids", "return_code", "checksum", "owner", "rollback_note")
    if any(key not in evidence or not evidence[key] for key in required if key != "return_code"):
        return False
    if type(evidence["command"]) is not str or not evidence["command"].strip():
        return False
    if type(evidence["owner"]) is not str or not evidence["owner"].strip() or evidence["owner"] != bundle.owner:
        return False
    if type(evidence["rollback_note"]) is not str or not evidence["rollback_note"].strip():
        return False
    return True


def _validate_layer_environment(evidence: dict[str, Any], bundle: AcceptanceBundle, working_tree_digest: str) -> bool:
    """Validate checkout identity and safety controls for one layer."""

    environment = evidence["environment"]
    if not isinstance(environment, dict) or not environment:
        return False
    if environment.get("head_sha") != bundle.head_sha or environment.get("working_tree_digest") != working_tree_digest:
        return False
    for safety_key in ("production_calls", "secrets_collected", "raw_personal_data"):
        if environment.get(safety_key) is not False:
            return False
    return True


def _validate_nodeids_and_return_code(evidence: dict[str, Any]) -> bool:
    """Validate node IDs and successful command completion."""

    nodeids = evidence["nodeids"]
    if not isinstance(nodeids, list) or not nodeids or any(not isinstance(item, str) or not item for item in nodeids):
        return False
    if type(evidence["return_code"]) is not int or evidence["return_code"] != 0:
        return False
    return True


def _validate_capture_hashes(evidence: dict[str, Any]) -> bool:
    """Validate checksum fields and bind the digest to captured bytes."""

    checksum = evidence.get("checksum")
    output_sha256 = evidence.get("output_sha256")
    if not isinstance(checksum, str) or _SHA256.fullmatch(checksum) is None:
        return False
    if not isinstance(output_sha256, str) or _SHA256.fullmatch(output_sha256) is None:
        return False
    captured_output = evidence.get("captured_output")
    return isinstance(captured_output, str) and sha256(captured_output.encode("utf-8")).hexdigest() == output_sha256


def _validate_layer_capture(evidence: dict[str, Any]) -> bool:
    """Validate node IDs, return code, and captured output digest."""

    return _validate_nodeids_and_return_code(evidence) and _validate_capture_hashes(evidence)


def _validate_layer_execution(evidence: dict[str, Any], bundle: AcceptanceBundle, working_tree_digest: str) -> bool:
    """Validate command, environment, node IDs, return code, and output hashes."""

    return (
        _validate_layer_metadata(evidence, bundle)
        and _validate_layer_environment(evidence, bundle, working_tree_digest)
        and _validate_layer_capture(evidence)
    )


def _validate_provenance_metadata(evidence: dict[str, Any], finding: str, layer: str) -> str | None:
    """Validate the provenance mapping and return its capture ID."""

    provenance = evidence.get("provenance")
    if not isinstance(provenance, dict):
        return None
    capture_id = provenance.get("capture_id")
    source = provenance.get("source")
    if not isinstance(capture_id, str) or not capture_id.strip() or not isinstance(source, str) or not source.strip():
        return None
    if provenance.get("finding_id") != finding or provenance.get("layer") != layer:
        return None
    return capture_id


def _validate_layer_provenance(evidence: dict[str, Any], finding: str, layer: str, seen_capture_ids: set[str]) -> bool:
    """Validate transcript support and reserve a unique capture identity."""

    if not _captured_output_supports_outcome(evidence) or evidence.get("checksum_verified") is not True:
        return False
    if "summary" in evidence and not isinstance(evidence["summary"], dict):
        return False
    capture_id = _validate_provenance_metadata(evidence, finding, layer)
    if capture_id is None or capture_id in seen_capture_ids:
        return False
    seen_capture_ids.add(capture_id)
    return True


def _fingerprint_evidence(evidence: dict[str, Any]) -> str:
    """Return the duplicate-detection fingerprint for one evidence record."""

    return json.dumps(
        {
            key: evidence.get(key)
            for key in (
                "command", "environment", "nodeids", "return_code", "owner",
                "rollback_note", "outcome", "evidence_kind",
                "availability_gap", "drill_steps", "checksum_verified", "stale",
                "output_sha256",
            )
        },
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _validate_layer_fingerprint(
    evidence: dict[str, Any],
    layer: str,
    seen_fingerprints: dict[str, set[str]],
    seen_capture_fingerprints: set[str],
) -> bool:
    """Validate canonical checksum and reject duplicate captured records."""

    proof_id = evidence.get("proof_id", "")
    summary = evidence.get("summary", {})
    if not isinstance(proof_id, str) or (not proof_id.strip() and not summary):
        return False
    if evidence.get("checksum") != _evidence_digest(evidence):
        return False
    capture_fingerprint = evidence["output_sha256"]
    if capture_fingerprint in seen_capture_fingerprints:
        return False
    seen_capture_fingerprints.add(capture_fingerprint)
    fingerprint = _fingerprint_evidence(evidence)
    prior = seen_fingerprints.setdefault(layer, set())
    if fingerprint in prior:
        return False
    prior.add(fingerprint)
    return True


def _validate_layer_evidence(
    bundle: AcceptanceBundle,
    finding: str,
    layer: str,
    evidence: Any,
    now: datetime,
    working_tree_digest: str,
    seen_fingerprints: dict[str, set[str]],
    seen_capture_fingerprints: set[str],
    seen_capture_ids: set[str],
) -> bool:
    """Validate one layer while preserving the original check ordering."""

    if not isinstance(evidence, dict) or not _validate_layer_identity(evidence, finding, layer):
        return False
    observed_at = evidence.get("observed_at")
    if not isinstance(observed_at, str) or not observed_at.strip():
        return False
    observed_layer = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
    if observed_layer.tzinfo is None or observed_layer.astimezone(timezone.utc) > now:
        return False
    if (now - observed_layer.astimezone(timezone.utc)).total_seconds() > bundle.max_age_hours * 3600:
        return False
    if not _validate_layer_execution(evidence, bundle, working_tree_digest):
        return False
    if not _validate_layer_provenance(evidence, finding, layer, seen_capture_ids):
        return False
    return _validate_layer_fingerprint(evidence, layer, seen_fingerprints, seen_capture_fingerprints)


def _validate_sections(
    bundle: AcceptanceBundle,
    now: datetime,
    working_tree_digest: str,
) -> bool:
    """Validate every P1 section and its distinct layered evidence records."""

    seen_fingerprints: dict[str, set[str]] = {}
    seen_capture_fingerprints: set[str] = set()
    seen_capture_ids: set[str] = set()
    for finding in P1_FINDINGS:
        section = bundle.sections.get(finding)
        if not _validate_section_header(section, finding):
            return False
        layers = _layer_values(section)
        if set(layers) != set(ACCEPTANCE_LAYERS):
            return False
        for layer in ACCEPTANCE_LAYERS:
            if not _validate_layer_evidence(
                bundle, finding, layer, layers.get(layer), now, working_tree_digest,
                seen_fingerprints, seen_capture_fingerprints, seen_capture_ids,
            ):
                return False
    return True


def _required_probe_receipts_pass(bundle: AcceptanceBundle) -> bool:
    probe_receipts = bundle.environment.get("probe_receipts")
    if probe_receipts is None:
        return False
    required = (
        "multiprocess-scheduler",
        "provider-sandbox",
        "proxy-contract",
        "backup-restore-checksum",
    )
    if not isinstance(probe_receipts, dict):
        return False
    for probe_id in required:
        status = probe_receipts.get(probe_id)
        if not isinstance(status, dict) or status.get("verdict") != "PASS":
            return False
        receipt = status.get("receipt")
        if not isinstance(receipt, dict) or verify_probe_receipt(receipt).verdict != "PASS":
            return False
        if _probe_slot_reasons(probe_id, receipt, bundle.head_sha):
            return False
    return True


def _pilot_attestation_checks(bundle: AcceptanceBundle, root: Path) -> bool:
    references = _attestation_references(root)
    if references is None:
        return False
    attested, _reasons = evaluate_attestations(
        bundle.attestations,
        digest=payload_digest(bundle.unsigned_payload()),
        references=references,
        root=root,
    )
    return attested and _countersignature_covers_every_passing_record(bundle)


def _evaluate_pilot_gate_contents(bundle: AcceptanceBundle, root: Path | None = None) -> GateVerdict:
    """Compute the closed-pilot decision from the evidence contents."""
    try:
        checked_root = Path(root).resolve() if root is not None else Path.cwd().resolve()
        identity = _gate_identity_valid(bundle, checked_root)
        if identity is None:
            return "NO_GO"
        now, working_tree_digest, contract = identity
        required_decisions, _public_verdict, authority_max_age_hours, authority_owner = contract
        if not _pilot_attestation_checks(bundle, checked_root):
            return "NO_GO"
        if not _required_probe_receipts_pass(bundle):
            return "NO_GO"
        if not isinstance(bundle.decision_required, dict) or set(bundle.decision_required) != required_decisions:
            return "NO_GO"
        if any(value is not True for value in bundle.decision_required.values()):
            return "NO_GO"
        return "GO_CONDITIONAL" if _validate_sections(bundle, now, working_tree_digest) else "NO_GO"
    except (TypeError, ValueError, KeyError, AttributeError, OverflowError):
        return "NO_GO"


def evaluate_pilot_gate(bundle: AcceptanceBundle, root: Path | None = None) -> GateVerdict:
    """Return a closed-pilot decision and reject forged declared gates."""

    try:
        if not isinstance(bundle, AcceptanceBundle) or bundle.gate not in {"GO_CONDITIONAL", "NO_GO"}:
            return "NO_GO"
        computed = _evaluate_pilot_gate_contents(bundle, root=root)
        if bundle.gate != computed:
            return "NO_GO"
        if not isinstance(bundle.output_sha256, str) or _SHA256.fullmatch(bundle.output_sha256) is None:
            return "NO_GO"
        return computed if bundle.output_sha256 == _bundle_digest(bundle) else "NO_GO"
    except (TypeError, ValueError, KeyError, AttributeError, OverflowError):
        return "NO_GO"


def _environment(root: Path, database_target: str, browser_base_url: str | None, external_sandbox: bool) -> dict[str, Any]:
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "head_sha": _head_sha(root),
        "working_tree_digest": _working_tree_digest(root),
        "database_target": database_target,
        "browser_base_url_supplied": bool(browser_base_url),
        "external_sandbox": bool(external_sandbox),
        "production_calls": False,
        "secrets_collected": False,
        "raw_personal_data": False,
    }


def _head_sha(root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD^{commit}"],
            cwd=root,
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )
        object_type = subprocess.run(
            ["git", "cat-file", "-t", "HEAD"],
            cwd=root,
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    if result.returncode != 0 or object_type.returncode != 0 or object_type.stdout.strip() != "commit":
        return "unknown"
    value = result.stdout.strip()
    return value if _HEAD_SHA.fullmatch(value) else "unknown"


def _disk_free(root: Path) -> int:
    try:
        return int(shutil.disk_usage(root).free)
    except OSError:
        return 0


def _successful_pytest_nodeids(output: str, command: list[str]) -> list[str]:
    """Extract node ids named by a verbose pytest run, including passing tests."""

    if not any(Path(str(token)).stem.lower() == "pytest" for token in command):
        return []
    nodeids: list[str] = []
    for line in output.splitlines():
        match = _PYTEST_SUCCESS_LINE.match(line)
        if not match:
            continue
        nodeid = match.group("nodeid").strip()
        # Pytest node ids identify an individual test with ``::``.  Requiring
        # it avoids treating arbitrary captured text ending in ``PASSED`` as
        # executable evidence.
        if "::" in nodeid and nodeid not in nodeids:
            nodeids.append(nodeid)
    return nodeids


def _run(command: list[str], root: Path, *, timeout: int = 120) -> tuple[str, int, dict[str, Any]]:
    rendered = " ".join(command)
    try:
        result = subprocess.run(command, cwd=root, text=True, capture_output=True, timeout=timeout, check=False)
        output = (result.stdout or "") + (result.stderr or "")
        outcome = parse_test_output(output, result.returncode)
        verdict = classify_verdict(outcome, frozenset())
        nodeids = list(outcome.failed_nodeids + outcome.error_nodeids)
        for nodeid in _successful_pytest_nodeids(output, command):
            if nodeid not in nodeids:
                nodeids.append(nodeid)
        return rendered, result.returncode, {
            "outcome": verdict,
            "nodeids": nodeids,
            "parsed": asdict(outcome),
            "output": output,
        }
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or "") + (exc.stderr or "") + "\nTIMEOUT\n"
        return rendered, 124, {
            "outcome": "BLOCKED",
            "nodeids": [],
            "parsed": {"return_code": 124, "summary_present": False},
            "output": output,
        }
    except OSError as exc:
        return rendered, 127, {
            "outcome": "UNCLASSIFIED",
            "nodeids": [],
            "parsed": {"return_code": 127, "summary_present": False},
            "output": f"{type(exc).__name__}: command unavailable",
        }


def _evidence(command: str, return_code: int, details: dict[str, Any], environment: dict[str, Any], owner: str, rollback_note: str) -> dict[str, Any]:
    output = str(details.get("output", ""))
    evidence = {
        "command": command,
        "environment": environment,
        "nodeids": details.get("nodeids", []),
        "return_code": int(return_code),
        "captured_output": output,
        "output_sha256": sha256(output.encode("utf-8")).hexdigest(),
        "owner": owner,
        "rollback_note": rollback_note,
        "outcome": details.get("outcome", "UNCLASSIFIED"),
        "summary": details.get("parsed", {}),
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "checksum_verified": True,
    }
    if "provenance" in details:
        evidence["provenance"] = details["provenance"]
    return evidence


def _skip_evidence(layer: str, reason: str, environment: dict[str, Any], owner: str, rollback_note: str) -> dict[str, Any]:
    output = f"UNAVAILABLE: {reason}\n"
    return {
        "command": f"availability probe: {layer}",
        "environment": environment,
        "nodeids": [],
        "return_code": 0,
        "captured_output": output,
        "output_sha256": sha256(output.encode("utf-8")).hexdigest(),
        "owner": owner,
        "rollback_note": rollback_note,
        "outcome": "UNCLASSIFIED",
        "summary": {"summary_present": False, "reason": reason},
        "availability_gap": reason,
        "evidence_kind": "availability",
        "checksum_verified": False,
        "observed_at": datetime.now(timezone.utc).isoformat(),
    }


def _disposable_pg_marker_present() -> bool:
    """Require an explicit operator confirmation before opening PostgreSQL.

    Loopback describes network reachability, not database ownership.  A local
    production database behind an SSH tunnel can look exactly like a disposable
    target, so the runner also requires a deliberate disposable-target marker.
    Both spellings are accepted to align with existing test-suite conventions.
    """

    confirmation = os.environ.get("VL360_TEST_DATABASE_CONFIRM", "").strip().lower()
    marker = os.environ.get("VL360_TEST_DATABASE_DISPOSABLE", "").strip().lower()
    return confirmation == "disposable" or marker in {"disposable", "true", "1", "yes"}


def _loopback_pg_dsn() -> str | None:
    """Return the PostgreSQL DSN only when loopback and disposable are explicit.

    The value is never returned to a caller that writes it into the bundle; it
    is read here solely to decide whether a real PostgreSQL capture is possible.
    A remote host is refused so this runner can never touch a shared database.
    """

    if not _disposable_pg_marker_present():
        return None
    raw = os.environ.get("VL360_TEST_DATABASE_URL", "").strip()
    if not raw:
        return None
    try:
        parsed = urlsplit(raw)
    except ValueError:
        return None
    if parsed.scheme not in {"postgres", "postgresql"}:
        return None
    hostname = (parsed.hostname or "").lower()
    if hostname not in {"127.0.0.1", "::1", "localhost"}:
        return None
    if "hostaddr" in parse_qs(parsed.query):
        return None
    return raw


def _postgres_capture(
    root: Path,
    node_ids: tuple[str, ...],
    temp_root: Path,
    env: dict[str, Any],
    owner: str,
    finding: str,
) -> dict[str, Any]:
    """Capture one finding's PostgreSQL result against the disposable target.

    A suite that skipped or collected nothing is downgraded to ``UNCLASSIFIED``
    with a named gap: an all-skipped run has a clean summary and would otherwise
    be indistinguishable from proof.
    """

    command, exit_code, details = _run(
        [
            # ``-v`` is required, not cosmetic: under ``-q`` pytest prints no
            # per-test lines, so the transcript could not evidence the node ids
            # this record claims to have exercised.
            sys.executable, "-m", "pytest", "-v", "--tb=line", "-p", "no:randomly",
            "--basetemp", str(temp_root / f"pg-{finding}"), *node_ids,
        ],
        root,
        timeout=900,
    )
    parsed = details.get("parsed", {})
    gap: str | None = None
    if not isinstance(parsed, dict) or not parsed.get("passed"):
        gap = "postgres-suite-collected-no-passing-test"
    elif parsed.get("skipped"):
        gap = "postgres-suite-partially-skipped-no-live-database"
    details["provenance"] = {
        "capture_id": f"pg-{finding}-{sha256(command.encode('utf-8')).hexdigest()[:16]}",
        "source": "pytest:VL360_TEST_DATABASE_URL",
        "finding_id": finding,
        "layer": "postgres",
    }
    evidence = _evidence(
        command, exit_code, details, env, owner,
        "Disposable PostgreSQL only; destroy target after run.",
    )
    evidence["evidence_kind"] = "postgresql-drill"
    evidence["nodeids"] = list(node_ids)
    if gap:
        evidence["outcome"] = "UNCLASSIFIED"
        evidence["availability_gap"] = gap
    return evidence


def _postgres_layers(
    root: Path,
    pytest_temp_root: Path,
    env: dict[str, Any],
    owner: str,
    database_target: str,
    postgres_proof: bool,
) -> dict[str, dict[str, Any]]:
    """Build one PostgreSQL evidence record per finding.

    A finding gets a real capture only when a PostgreSQL test names its defect;
    every other finding records an explicit, per-finding gap rather than
    borrowing a capture that proves something else.
    """

    available = postgres_proof and database_target == "disposable-postgres" and _loopback_pg_dsn() is not None
    if not postgres_proof:
        reason = "postgres-proof-not-requested"
    elif database_target != "disposable-postgres":
        reason = "database-target-not-disposable-postgres"
    else:
        reason = "postgres-dsn-not-explicitly-disposable-loopback"
    layers: dict[str, dict[str, Any]] = {}
    for finding in P1_FINDINGS:
        node_ids = POSTGRES_FINDING_NODEIDS.get(finding)
        if not node_ids:
            layers[finding] = _skip_evidence("postgres", "no-postgres-proof-mapped-for-finding", env, owner, "No database mutation performed.")
        elif available:
            layers[finding] = _postgres_capture(root, node_ids, pytest_temp_root, env, owner, finding)
        else:
            layers[finding] = _skip_evidence("postgres", reason, env, owner, "No database mutation performed.")
    return layers


def _has_bound_provenance(evidence: dict[str, Any], finding: str, layer: str) -> bool:
    """Return whether a capture names the exact finding and layer."""

    provenance = evidence.get("provenance")
    return (
        isinstance(provenance, dict)
        and provenance.get("finding_id") == finding
        and provenance.get("layer") == layer
        and isinstance(provenance.get("capture_id"), str)
        and bool(provenance.get("capture_id", "").strip())
        and isinstance(provenance.get("source"), str)
        and bool(provenance.get("source", "").strip())
    )


def _mark_unclassified(bound: dict[str, Any], finding: str, layer: str) -> None:
    """Prevent a shared aggregate capture from becoming passing evidence."""

    bound["provenance"] = {
        "capture_id": "",
        "source": "",
        "finding_id": finding,
        "layer": layer,
    }
    bound["outcome"] = "UNCLASSIFIED"
    bound["evidence_kind"] = "unclassified-shared-result"
    bound["checksum_verified"] = False
    bound["unclassified_reason"] = "capture lacks per-finding/per-layer provenance"


def _execution_receipt_for_bound_evidence(bound: dict[str, Any], finding: str, layer: str) -> dict[str, Any] | None:
    """Build the diagnostic receipt after finding/layer binding is known."""

    command = bound.get("command")
    output = bound.get("output_sha256")
    environment = bound.get("environment")
    if not isinstance(command, str) or not isinstance(output, str) or not isinstance(environment, dict):
        return None
    return {
        "version": 1,
        "issuer": "run_pilot_acceptance",
        "finding_id": finding,
        "layer": layer,
        "command_sha256": sha256(command.encode("utf-8")).hexdigest(),
        "output_sha256": output,
        "return_code": bound.get("return_code"),
        "head_sha": environment.get("head_sha"),
        "working_tree_digest": environment.get("working_tree_digest"),
    }


def _attach_execution_receipt(bound: dict[str, Any], finding: str, layer: str) -> None:
    """Attach a receipt when the captured fields are complete enough to bind."""

    receipt = _execution_receipt_for_bound_evidence(bound, finding, layer)
    if receipt is not None:
        bound["execution_receipt"] = receipt


def _bind_evidence(evidence: dict[str, Any], finding: str, layer: str) -> dict[str, Any]:
    """Bind one captured result to exactly one finding/layer pair."""

    bound = {**evidence, "finding_id": finding, "layer": layer}
    valid_provenance = _has_bound_provenance(evidence, finding, layer)
    if valid_provenance and not bound.get("proof_id"):
        bound["proof_id"] = evidence["provenance"]["capture_id"]
    if not valid_provenance:
        _mark_unclassified(bound, finding, layer)
    _attach_execution_receipt(bound, finding, layer)
    bound["checksum"] = _evidence_digest(bound)
    return bound


def run_pilot_acceptance(root: Path, *, database_target: str, browser_base_url: str | None, external_sandbox: bool, postgres_proof: bool = False, probe_evidence_dir: Path | None = None) -> AcceptanceBundle:
    """Run repository-local checks in a scratch directory that is always removed.

    The scratch tree is created inside the checkout so pytest never writes to a
    long Windows temp path, and it is deleted afterwards so repeated runs cannot
    exhaust the disk and corrupt later measurements.
    """

    root = Path(root).resolve()
    pytest_temp_root = Path(tempfile.mkdtemp(prefix=".tmp-pilot-acceptance-", dir=root))
    try:
        return _collect_pilot_evidence(
            root,
            pytest_temp_root=pytest_temp_root,
            database_target=database_target,
            browser_base_url=browser_base_url,
            external_sandbox=external_sandbox,
            postgres_proof=postgres_proof,
            probe_evidence_dir=probe_evidence_dir,
        )
    finally:
        shutil.rmtree(pytest_temp_root, ignore_errors=True)


def _collect_pilot_evidence(root: Path, *, pytest_temp_root: Path, database_target: str, browser_base_url: str | None, external_sandbox: bool, postgres_proof: bool, probe_evidence_dir: Path | None) -> AcceptanceBundle:
    """Run only repository-local checks and return a fail-closed bundle."""

    owner = "service-owner"
    env = _environment(root, database_target, browser_base_url, external_sandbox)
    probe_receipts = _load_checkout_probe_receipts(root, probe_evidence_dir)
    env["probe_receipts"] = probe_receipts
    before_free = _disk_free(root)
    # ``-v`` so the transcript names the tests it ran, and a drill-sized
    # timeout: the 120s default silently turned this layer into a TIMEOUT
    # record once the cross-boundary suite grew past two minutes.
    unit_command, unit_exit, unit_details = _run(
        [sys.executable, "-m", "pytest", "-v", "--tb=line", "-p", "no:randomly",
         "--basetemp", str(pytest_temp_root / "unit"), *LOCAL_DRILL_NODEIDS],
        root,
        timeout=1800,
    )
    multi_command, multi_exit, multi_details = _run(
        [sys.executable, "-m", "pytest", "tests/integration/test_cross_boundary_proof.py", "-v", "--tb=line",
         "-p", "no:randomly", "-k", "generation", "--basetemp", str(pytest_temp_root / "multi_process")],
        root,
        timeout=900,
    )

    layers: dict[str, dict[str, Any]] = {
        "unit": _evidence(unit_command, unit_exit, unit_details, env, owner, "No production mutation; rerun locally."),
        "multi_process": _evidence(multi_command, multi_exit, multi_details, env, owner, "No production mutation; rerun locally."),
    }
    layers["unit"]["drill_steps"] = [
        "fixture entity revision/generation",
        "stale and wrong-scope decision evidence rejection",
        "owner-keyed cache denial",
        "export manifest with checksum/excluded secrets",
        "local object deletion failure and retry receipt",
    ]
    layers["multi_process"]["outcome"] = "UNCLASSIFIED"
    layers["multi_process"]["evidence_kind"] = "partial-local-proof"
    layers["multi_process"]["availability_gap"] = "multi-process-contention-command-not-run"
    layers["multi_process"]["probe_receipt"] = probe_receipts["multiprocess-scheduler"]
    # `docker info` was never PostgreSQL proof, so it is not consulted here.
    # A finding gets a real capture only when a PostgreSQL test names its
    # defect; every other finding records an explicit, per-finding gap.
    postgres_layers = _postgres_layers(root, pytest_temp_root, env, owner, database_target, postgres_proof)
    layers["postgres"] = _skip_evidence("postgres", "per-finding-postgres-evidence", env, owner, "No database mutation performed.")
    if browser_base_url:
        layers["browser"] = _skip_evidence("browser", "browser-harness-not-invoked; local URL supplied but no browser binary was authorized", env, owner, "No browser state retained; rerun with disposable harness.")
    else:
        layers["browser"] = _skip_evidence("browser", "browser-base-url-not-supplied", env, owner, "No browser state retained.")
    layers["browser"]["proxy_probe_receipt"] = probe_receipts["proxy-contract"]
    if external_sandbox:
        # The receipt lives inside the runner's own excluded scratch directory:
        # a crashed run must never leave a repository-root file behind that
        # would perturb every later working-tree digest.
        receipt_fd, receipt_name = tempfile.mkstemp(prefix="pilot-receipt-", suffix=".json", dir=pytest_temp_root)
        os.close(receipt_fd)
        receipt_path = Path(receipt_name)
        try:
            receipt_output = '{"sandbox":true,"provider_call":false}\n'
            receipt_path.write_bytes(receipt_output.encode("utf-8"))
            receipt_hash = sha256(receipt_path.read_bytes()).hexdigest()
        finally:
            receipt_path.unlink(missing_ok=True)
        layers["external_side_effect"] = {
            "command": "local external-side-effect sandbox receipt",
            "environment": env,
            "nodeids": ["sandbox:no-provider-call"],
            "return_code": 0,
            "captured_output": receipt_output,
            "output_sha256": sha256(receipt_output.encode("utf-8")).hexdigest(),
            "checksum": receipt_hash,
            "owner": owner,
            "rollback_note": "Temporary receipt deleted; no provider or production call.",
            "outcome": "UNCLASSIFIED",
            "evidence_kind": "sandbox-receipt",
            "checksum_verified": True,
            "availability_gap": "provider/object failure retry drill not executed against external sandbox",
            "summary": {"summary_present": True, "provider_call": False},
            "observed_at": datetime.now(timezone.utc).isoformat(),
        }
    else:
        layers["external_side_effect"] = _skip_evidence("external_side_effect", "external-sandbox-not-enabled", env, owner, "No provider call performed.")
    layers["external_side_effect"]["provider_probe_receipt"] = probe_receipts["provider-sandbox"]
    layers["external_side_effect"]["backup_restore_probe_receipt"] = probe_receipts["backup-restore-checksum"]
    layers["external_side_effect"]["rollback_probe_receipt"] = probe_receipts["rollback-local-rehearsal"]

    all_layers = {name: value for name, value in layers.items()}

    def _finding_layers(finding: str) -> dict[str, dict[str, Any]]:
        """Bind every layer to one finding, using that finding's own PostgreSQL capture."""

        resolved = {**all_layers, "postgres": postgres_layers[finding]}
        return {layer: _bind_evidence(value, finding, layer) for layer, value in resolved.items()}

    sections = {}
    for finding in P1_FINDINGS:
        bound = _finding_layers(finding)
        # The section verdict is computed from the BOUND records, so a capture
        # that lost its outcome during binding can never be reported as proof.
        outcome: Outcome = "PASS" if all(item.get("outcome") == "PASS" for item in bound.values()) else "UNCLASSIFIED"
        sections[finding] = EvidenceSection(
            outcome=outcome,
            layers=bound,
            stale=False,
            cross_boundary_proof=(outcome == "PASS"),
            finding_id=finding,
        )
    section_outcome: Outcome = "PASS" if all(item.outcome == "PASS" for item in sections.values()) else "UNCLASSIFIED"
    bundle = AcceptanceBundle(
        sections=sections,
        artifact_id=f"pilot-acceptance-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        head_sha=env["head_sha"],
        generated_at=datetime.now(timezone.utc).isoformat(),
        owner=owner,
        owner_signoff=False,
        rollback_note="Closed pilot only; public launch remains NO_GO.",
        cross_boundary_proof=section_outcome == "PASS",
        decision_required={key: False for key in DECISION_REQUIRED_ITEMS},
        environment={**env, "disk_free_before": before_free, "disk_free_after": _disk_free(root), "pytest_temp_root": str(pytest_temp_root)},
        max_age_hours=(_authority_contract(root) or (set(), PUBLIC_LAUNCH_VERDICT, 0, ""))[2],
    )
    # Decide BEFORE signing.  `gate` is inside the signed payload
    # (`unsigned_payload` pops only `output_sha256` and `attestations`), so
    # signing first commits the runner to the dataclass default rather than to
    # the verdict it is about to write.  That is fail-closed — a stale digest
    # can only turn a legitimate GO_CONDITIONAL into NO_GO, never mint a green
    # gate — and today it is masked because the gate always evaluates to the
    # default anyway.  It is still the runner disagreeing with every later
    # verifier, and with the countersigner, which signs the bundle as read from
    # disk (i.e. over the final gate).
    bundle.gate = _evaluate_pilot_gate_contents(bundle, root=root)
    bundle.attestations = _runner_attestations(bundle, root=root)
    bundle.output_sha256 = _bundle_digest(bundle)
    return bundle


def _runner_attestations(bundle: AcceptanceBundle, root: Path | None = None) -> list[dict[str, Any]]:
    """Mint the runner's own attestation over the bundle it just produced.

    When no runner key is configured the attestation is still emitted with
    scheme ``unsigned``.  Recording the absence is the point: an omitted
    attestation is indistinguishable from one that was never attempted, while
    an explicit unsigned one names the gap the gate then refuses.
    """

    checked_root = Path(root).resolve() if root is not None else ROOT
    references = _attestation_references(checked_root)
    if references is None:
        return []
    reference = next((item for item in references.values() if item.role == "runner"), None)
    if reference is None:
        return []
    return [
        build_attestation(
            role="runner",
            key_id=reference.key_id,
            custody=reference.custody,
            digest=payload_digest(bundle.unsigned_payload()),
            signed_at=datetime.now(timezone.utc).isoformat(),
            key=resolve_key(reference.custody, root=checked_root),
            provenance={"issuer": "run_pilot_acceptance", "head_sha": bundle.head_sha},
        )
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--database-target", default="none")
    parser.add_argument("--browser-base-url")
    parser.add_argument("--external-sandbox", action="store_true")
    # Opt-in only, and deliberately a boolean: the DSN is read from the
    # environment so no credential can reach argv, the recorded command, or the
    # artifact that claims `secrets_collected: False`.
    parser.add_argument("--postgres-proof", action="store_true")
    parser.add_argument("--evidence-dir", type=Path, default=None, help="directory containing validated staging probe receipts")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)
    output = args.output or (args.root / "artifacts" / "pilot-acceptance.json")
    bundle = run_pilot_acceptance(args.root, database_target=args.database_target, browser_base_url=args.browser_base_url, external_sandbox=args.external_sandbox, postgres_proof=args.postgres_proof, probe_evidence_dir=args.evidence_dir)
    bundle.write(output)
    print(json.dumps({"artifact": str(output), "gate": bundle.gate, "p1_count": len(bundle.sections), "layers": list(ACCEPTANCE_LAYERS)}, ensure_ascii=True, sort_keys=True))
    return 0 if bundle.gate == "GO_CONDITIONAL" else 2


if __name__ == "__main__":
    raise SystemExit(main())
