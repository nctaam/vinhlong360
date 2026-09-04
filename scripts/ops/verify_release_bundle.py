#!/usr/bin/env python3
"""Verify a versioned release evidence bundle without mutating it.

Three controls that the release path was supposed to have were never reached
from here, and each failed OPEN:

``countersignature``
    ``countersign_pilot_acceptance.py`` writes its receipt to a SEPARATE
    artifact (``artifacts/pilot-countersignature.json``) on purpose — a bundle
    is never edited in place once issued.  But nothing ever read it back, so an
    independent re-execution could exist on disk, or be absent, or bind to a
    different bundle entirely, and the verifier said the same thing either way.

``authority staleness``
    ``check_authority`` returns ``STALE`` when the governing documents have
    expired, and it is exercised by its own unit test — but no release path
    called it.  A stale authority therefore could not block a release.

``decision records``
    The gate saw only four bare booleans inside the bundle.  Nothing connected
    them to ``config/decision-records.json`` or ``docs/decisions/QD-*.md``, so a
    record could be minted locally, bind to nothing, and name any signer.

All three are wired in below.  They can only ADD reasons and downgrade the
verdict to ``BLOCKED``; nothing here can raise a verdict, so the wiring cannot
turn a failing check green.  None of them can create an approval: choosing an
option on behalf of owner / legal / provider / residency is a human act, and
these checks can only refuse.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.control_plane.attestation import (  # noqa: E402
    load_key_references,
    payload_digest,
    verify_attestation,
)
from agent.control_plane.authority import check_authority  # noqa: E402
from agent.control_plane.evidence import verify_bundle  # noqa: E402
from scripts.ops.run_pilot_acceptance import (  # noqa: E402
    AcceptanceBundle,
    _bundle_digest,
    evaluate_pilot_gate,
    verify_pilot_bundle,
)

COUNTERSIGNATURE_NAME = "pilot-countersignature.json"


def _head_sha(root: Path) -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _countersignature_path(bundle_path: Path, receipt_path: Path | None = None) -> Path:
    return Path(receipt_path).resolve() if receipt_path is not None else Path(bundle_path).resolve().parent / COUNTERSIGNATURE_NAME


def _read_countersignature(receipt_path: Path) -> tuple[dict | None, list[str]]:
    if not receipt_path.is_file():
        return None, [f"countersignature artifact not found: {receipt_path.name}"]
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, [f"countersignature artifact unreadable: {type(exc).__name__}"]
    if not isinstance(receipt, dict):
        return None, ["countersignature artifact is not an object"]
    return receipt, []


def countersignature_reasons(
    bundle_path: Path,
    payload: dict,
    checked_sha256: str,
    receipt_path: Path | None = None,
) -> list[str]:
    """Report why the countersignature does not stand for this exact bundle.

    An empty list means a complete receipt was found AND it binds to this
    bundle's identity and digest.
    """

    receipt, reasons = _read_countersignature(_countersignature_path(bundle_path, receipt_path))
    if receipt is None:
        return reasons

    reasons = list(reasons)
    # Binding first: a receipt that does not name THIS bundle proves nothing
    # about it, however complete it looks on its own.
    declared_digest = receipt.get("bundle_output_sha256")
    if declared_digest != payload.get("output_sha256"):
        reasons.append("countersignature does not bind this bundle's output_sha256")
    if declared_digest != checked_sha256:
        reasons.append("countersignature digest does not match the recomputed bundle digest")
    if receipt.get("bundle_artifact_id") != payload.get("artifact_id"):
        reasons.append("countersignature does not bind this bundle's artifact_id")
    if receipt.get("head_sha") != payload.get("head_sha"):
        reasons.append("countersignature head_sha differs from the bundle head_sha")

    if receipt.get("complete") is not True:
        reasons.append("countersignature is incomplete")
    expected = receipt.get("expected")
    confirmed = receipt.get("confirmed")
    expected_keys: list[str] = []
    confirmed_keys: list[str] = []
    if not isinstance(expected, list) or not isinstance(confirmed, list):
        reasons.append("countersignature expected/confirmed sets are malformed")
    else:
        if any(not isinstance(item, str) or not item for item in expected + confirmed):
            reasons.append("countersignature expected/confirmed sets are malformed")
        expected_keys = [item for item in expected if isinstance(item, str) and item]
        confirmed_keys = [item for item in confirmed if isinstance(item, str) and item]
        if not expected_keys:
            reasons.append("countersignature expected set is empty")
        if len(set(expected_keys)) != len(expected_keys):
            reasons.append("countersignature expected set contains duplicate records")
        if len(set(confirmed_keys)) != len(confirmed_keys):
            reasons.append("countersignature confirmed set contains duplicate records")
    if sorted(confirmed_keys) != sorted(expected_keys):
        reasons.append("countersignature confirmed set does not equal its expected set")
    expected_set = set(expected_keys)
    results = receipt.get("results")
    if not isinstance(results, list):
        reasons.append("countersignature results are malformed")
        results = []
    result_keys: list[str] = []
    seen_result_keys: set[str] = set()
    for entry in results:
        if not isinstance(entry, dict):
            reasons.append("countersignature results contain a malformed record")
            continue
        record = entry.get("record")
        if not isinstance(record, str) or not record:
            reasons.append("countersignature results contain a malformed record key")
            continue
        result_keys.append(record)
        if record in seen_result_keys:
            reasons.append(f"countersignature results contain duplicate record: {record}")
        seen_result_keys.add(record)
        if record not in expected_set:
            reasons.append(f"countersignature results contain unknown record: {record}")
        if entry.get("verdict") != "MATCH":
            reasons.append(f"countersignature record did not match: {record}")
    if expected_set:
        missing = sorted(expected_set - seen_result_keys)
        if missing:
            reasons.append(
                "countersignature results are missing expected record(s): "
                + ", ".join(missing)
            )
        unknown = sorted(seen_result_keys - expected_set)
        if unknown and not any("unknown record" in reason for reason in reasons):
            reasons.append(
                "countersignature results contain unknown record(s): "
                + ", ".join(unknown)
            )

    attestation = receipt.get("attestation")
    if not isinstance(attestation, dict):
        reasons.append("countersignature carries no attestation")
    elif attestation.get("scheme") == "unsigned" or not attestation.get("signature"):
        # Deliberate on this machine: the key is absent by owner decision.
        # Recorded as a reason rather than ignored, so it stays visible.
        reasons.append("countersignature is unsigned (no countersign key in custody)")
    return reasons


def overlay_countersignature(payload: dict, receipt: dict) -> tuple[dict | None, list[str]]:
    """Return an in-memory finalized view with one validated sidecar attestation.

    The issued bundle remains immutable on disk.  The returned payload gets a
    fresh envelope checksum because adding an attestation changes the envelope;
    callers must still validate the sidecar's binding to the original checksum
    before using this view as a gate input.
    """

    if not isinstance(payload, dict) or not isinstance(receipt, dict):
        return None, ["countersignature overlay input is malformed"]
    attestations = payload.get("attestations", [])
    if not isinstance(attestations, list):
        return None, ["countersignature overlay attestation list is malformed"]
    if any(isinstance(item, dict) and item.get("role") == "countersign" for item in attestations):
        return None, ["countersignature role duplicated in bundle overlay"]
    attestation = receipt.get("attestation")
    if not isinstance(attestation, dict):
        return None, ["countersignature carries no attestation"]

    finalized = deepcopy(payload)
    finalized["attestations"] = [*attestations, deepcopy(attestation)]
    try:
        bundle = AcceptanceBundle.from_dict(finalized)
        finalized["output_sha256"] = _bundle_digest(bundle)
        return finalized, []
    except (TypeError, ValueError, KeyError, AttributeError, OverflowError):
        return None, ["countersignature overlay bundle is malformed"]


def _has_inline_countersignature(payload: dict) -> bool:
    attestations = payload.get("attestations") if isinstance(payload, dict) else None
    return isinstance(attestations, list) and any(
        isinstance(item, dict) and item.get("role") == "countersign" for item in attestations
    )


def countersignature_attestation_reasons(root: Path, payload: dict, receipt: dict) -> list[str]:
    """Verify the sidecar's HMAC and its exact re-execution coverage."""

    attestation = receipt.get("attestation")
    if not isinstance(attestation, dict):
        return ["countersignature carries no attestation"]
    expected = receipt.get("expected")
    if not isinstance(expected, list) or sorted(attestation.get("covers") or []) != sorted(expected):
        return ["countersignature attestation coverage differs from expected records"]
    try:
        authority = json.loads((root / "config" / "release-authority.json").read_text(encoding="utf-8"))
        pilot = authority["pilot_acceptance"]
        references = load_key_references(pilot.get("attestation_keys"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        references = None
    if references is None:
        return ["countersignature attestation authority is malformed"]
    try:
        bundle = AcceptanceBundle.from_dict(payload)
        digest = payload_digest(bundle.unsigned_payload())
    except (TypeError, ValueError, KeyError, AttributeError, OverflowError):
        return ["countersignature attestation payload is malformed"]
    ok, reason = verify_attestation(attestation, digest=digest, references=references, root=root)
    return [] if ok else [f"countersignature attestation rejected: {reason}"]


def _is_tracked(root: Path, rel: str) -> bool:
    try:
        result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", rel],
            cwd=root,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def decision_reasons(root: Path, payload: dict) -> list[str]:
    """Report why the four required decisions do not stand.

    The gate previously saw ONLY four bare booleans carried inside the bundle
    (``decision_required``).  Nothing connected them to
    ``config/decision-records.json`` or ``docs/decisions/QD-*.md``, so a record
    could be minted locally, hash nothing, and be signed by anyone — and the
    gate would not notice either way.  Measured 2026-09-03: the entire decision
    corpus is UNTRACKED.

    This never mints or selects a decision.  Choosing an option on behalf of
    owner / legal / provider / residency is a human act; the only thing this
    can do is refuse.
    """

    reasons: list[str] = []
    index_rel = "config/decision-records.json"
    index_path = root / index_rel
    if not index_path.is_file():
        return [f"decision record index missing: {index_rel}"]
    if not _is_tracked(root, index_rel):
        # An untracked index is one anybody could have written locally.
        reasons.append(f"decision record index is not git-tracked: {index_rel}")
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return reasons + [f"decision record index unreadable: {type(exc).__name__}"]

    decisions = {
        entry.get("decision_key"): entry
        for entry in (index.get("decisions") or [])
        if isinstance(entry, dict)
    }

    # An allowed-signer list does not exist in the authority.  Rather than
    # inventing one here — which would be this tool deciding who may approve a
    # release — a signed record is refused until the authority declares it.
    try:
        authority = json.loads((root / "config/release-authority.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        authority = {}
    pilot = authority.get("pilot_acceptance") or {}
    allowed_signers = pilot.get("decision_signers") or {}
    required = pilot.get("decision_required_items") or []

    for key in required:
        entry = decisions.get(key)
        if entry is None:
            reasons.append(f"decision record missing for required item: {key}")
            continue
        record_rel = entry.get("record")
        if not isinstance(record_rel, str) or not record_rel:
            reasons.append(f"decision {key}: names no record file")
            continue
        record_path = root / record_rel
        if not record_path.is_file():
            reasons.append(f"decision {key}: record file missing: {record_rel}")
            continue
        if not _is_tracked(root, record_rel):
            reasons.append(f"decision {key}: record is not git-tracked: {record_rel}")

        if entry.get("state") != "signed":
            reasons.append(f"decision {key}: state is {entry.get('state')!r}, not signed")
            continue

        # From here the record CLAIMS to be signed, so every binding must hold.
        declared = entry.get("record_sha256")
        actual = hashlib.sha256(record_path.read_bytes()).hexdigest()
        if declared != actual:
            reasons.append(
                f"decision {key}: record_sha256 does not match {record_rel} "
                "(the signature does not bind the text that was decided)"
            )
        if not entry.get("chosen_option"):
            reasons.append(f"decision {key}: signed with no chosen_option")
        if not entry.get("signature"):
            reasons.append(f"decision {key}: signed state carries no signature")
        signer = entry.get("signed_by")
        permitted = allowed_signers.get(key)
        if not permitted:
            reasons.append(
                f"decision {key}: authority declares no allowed signer, so a "
                "signature cannot be credited"
            )
        elif signer not in permitted:
            reasons.append(f"decision {key}: signer {signer!r} is not an allowed signer")

    # The bundle must not assert approval that the records do not carry.
    for key, claimed in (payload.get("decision_required") or {}).items():
        entry = decisions.get(key) or {}
        if claimed is True and entry.get("state") != "signed":
            reasons.append(
                f"decision {key}: bundle claims approval but the record is not signed"
            )
    return reasons


def authority_reasons(root: Path) -> list[str]:
    """Report why the release authority does not currently stand."""

    report = check_authority(root, datetime.now(timezone.utc), _head_sha(root))
    if report.status == "PASS":
        return []
    reasons = [f"release authority is {report.status}"]
    reasons.extend(f"authority mismatch: {item}" for item in report.mismatches)
    reasons.extend(f"authority document expired: {item}" for item in report.expired_documents)
    return reasons


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--countersignature",
        type=Path,
        default=None,
        help="explicit countersignature sidecar; required only when the bundle has no inline countersignature",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()
    bundle_path = args.bundle if args.bundle.is_absolute() else root / args.bundle
    try:
        payload = json.loads(bundle_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        payload = None
    if isinstance(payload, dict) and payload.get("bundle_kind") == "pilot-acceptance-v1":
        verdict, reasons, checked_sha256 = verify_pilot_bundle(bundle_path, root=root)
        reasons = list(reasons)
        receipt_path = _countersignature_path(bundle_path, args.countersignature)
        has_inline = _has_inline_countersignature(payload)
        # A finalized bundle carries its countersignature in the immutable
        # envelope.  Otherwise an explicit/adjacent sidecar is validated and
        # overlaid in memory; the issued source file is never rewritten.
        if not has_inline or args.countersignature is not None:
            receipt, countersign_reasons = _read_countersignature(receipt_path)
            sidecar_reasons = countersign_reasons
            if receipt is not None:
                sidecar_reasons.extend(countersignature_reasons(bundle_path, payload, checked_sha256, receipt_path))
            reasons.extend(sidecar_reasons)
            if receipt is not None and not sidecar_reasons and not has_inline:
                reasons.extend(countersignature_attestation_reasons(root, payload, receipt))
                if not reasons or reasons == ["pilot acceptance gate is NO_GO"]:
                    overlay, overlay_reasons = overlay_countersignature(payload, receipt)
                    reasons.extend(overlay_reasons)
                    if overlay is not None and not overlay_reasons:
                        try:
                            overlay_gate = evaluate_pilot_gate(AcceptanceBundle.from_dict(overlay), root=root)
                        except (TypeError, ValueError, KeyError, AttributeError, OverflowError):
                            overlay_gate = "NO_GO"
                        if overlay_gate == "GO_CONDITIONAL":
                            reasons = [reason for reason in reasons if reason != "pilot acceptance gate is NO_GO"]
                            verdict = "PASS"
                        else:
                            reasons.append("countersignature overlay does not satisfy pilot acceptance gate")
        reasons.extend(decision_reasons(root, payload))
        reasons.extend(authority_reasons(root))
        # Fail closed: any reason at all blocks, and no branch here can raise a
        # verdict that verify_pilot_bundle already lowered.
        if reasons:
            verdict = "BLOCKED"
        result = type(
            "PilotVerification",
            (),
            {"verdict": verdict, "reasons": tuple(reasons), "checked_sha256": checked_sha256},
        )()
    else:
        result = verify_bundle(bundle_path)
    print(
        json.dumps(
            {
                "verdict": result.verdict,
                "reasons": list(result.reasons),
                "checked_sha256": result.checked_sha256,
            },
            ensure_ascii=True,
            sort_keys=True,
        )
    )
    return {"PASS": 0, "BLOCKED": 2, "UNCLASSIFIED": 3}[result.verdict]


if __name__ == "__main__":
    raise SystemExit(main())
