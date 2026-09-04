#!/usr/bin/env python3
"""Re-execute a pilot acceptance bundle's claims and countersign what matches.

Every other control in the bundle checks the bundle against itself.  This one
checks it against the world: for each record the bundle calls ``PASS`` it runs
the tests that record names and compares the outcome it observes with the
outcome the record claims.  A signature says who wrote something; only
re-execution says that it happened.

Two deliberate design choices:

* The command string recorded in the bundle is never executed.  This tool
  rebuilds its own invocation from the record's ``nodeids``, so a bundle cannot
  steer the countersigner at a command of its choosing.
* Byte equality is not required and would be wrong: pytest prints durations, so
  two honest runs of the same tests never produce identical text.  What must
  match is the parsed outcome — verdict, counts, and node ids.

The countersignature is written to its own artifact rather than back into the
bundle, because a bundle is never edited in place once issued.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.control_plane.attestation import (  # noqa: E402
    build_attestation,
    canonical_json,
    payload_digest,
    resolve_key,
)
from agent.control_plane.evidence import classify_verdict, parse_test_output  # noqa: E402
from scripts.ops.run_pilot_acceptance import (  # noqa: E402
    AcceptanceBundle,
    _attestation_references,
    _coverage_key,
    _PARSED_EVIDENCE_KINDS,
)

COUNTERSIGNATURE_VERSION = 1
DEFAULT_TIMEOUT_SECONDS = 900


_COUNTED_OUTCOMES = ("passed", "skipped", "failed", "errors", "collection_errors")


def _counts(summary: Any) -> dict[str, int]:
    """Normalise a parsed-outcome summary to the counts that enter the digest."""

    source = summary if isinstance(summary, dict) else {}
    return {name: int(source.get(name) or 0) for name in _COUNTED_OUTCOMES}


def _outcome_fingerprint(
    verdict: str, nodeids: list[str], return_code: int, counts: dict[str, int]
) -> str:
    """Digest the deterministic part of one run, excluding timings and paths.

    COUNTS ARE PART OF THE DIGEST, and must stay that way.  Without them an
    ALL-SKIPPED run is byte-identical to a real drill: ``classify_verdict``
    returns "PASS" when nothing failed, pytest exits 0, and ``pytest -v`` still
    prints every node id.  So on a machine with no database the three @pg_only
    postgres drills SKIP and reproduce the exact fingerprint of a genuine run —
    measured 2026-09-03 as
    57953d7e579821eaf43668cb6379df46b19c532dc035574f7ee9967557782db6 for
    F-42/postgres, identical to the value in the live countersignature receipt.

    The runner already guards this hazard per capture
    (``run_pilot_acceptance.py``: "an all-skipped run has a clean summary and
    would otherwise be indistinguishable from proof").  The countersigner is
    supposed to be STRONGER than the bundle's self-checks; without counts it was
    strictly weaker.  The module docstring always promised "verdict, counts, and
    node ids" — this makes the code keep that promise.
    """

    return payload_digest(
        {
            "verdict": verdict,
            "nodeids": sorted(nodeids),
            "return_code": return_code,
            "counts": {name: counts.get(name, 0) for name in _COUNTED_OUTCOMES},
        }
    )


def _rerun(nodeids: list[str], root: Path, temp_root: Path, label: str, timeout: int) -> tuple[str, int, list[str], dict[str, int]]:
    """Run the named node ids and return the observed verdict, code and output."""

    command = [
        # ``-v`` makes pytest name each test it ran, which is what lets this
        # tool confirm the node ids rather than only the aggregate tally.
        sys.executable, "-m", "pytest", "-v", "--tb=line", "-p", "no:randomly",
        "--basetemp", str(temp_root / label), *nodeids,
    ]
    try:
        result = subprocess.run(command, cwd=root, text=True, capture_output=True, timeout=timeout, check=False)
        output = (result.stdout or "") + (result.stderr or "")
        return_code = result.returncode
    except subprocess.TimeoutExpired:
        return "BLOCKED", 124, [], _counts(None)
    except OSError:
        return "UNCLASSIFIED", 127, [], _counts(None)
    parsed = parse_test_output(output, return_code)
    verdict = classify_verdict(parsed, frozenset())
    observed = [nodeid for nodeid in nodeids if nodeid in output]
    # The counts were already computed here and then discarded; they are the
    # difference between "nothing failed" and "something actually ran".
    return verdict, return_code, observed, _counts(parsed)


def _replay_record(key: str, evidence: dict[str, Any], root: Path, temp_root: Path, timeout: int) -> dict[str, Any]:
    """Re-execute one passing record and compare what happened with what it claims."""

    if evidence.get("evidence_kind") not in _PARSED_EVIDENCE_KINDS:
        # A browser or provider drill cannot be replayed by this tool; saying so
        # is the honest result, not silently counting it as confirmed.
        return {"record": key, "verdict": "NOT_REPLAYABLE", "reason": "evidence-kind-not-re-executable"}
    nodeids = evidence.get("nodeids")
    if not isinstance(nodeids, list) or not all(isinstance(item, str) and item for item in nodeids):
        return {"record": key, "verdict": "NOT_REPLAYABLE", "reason": "nodeids-missing"}
    claimed_return_code = evidence.get("return_code")
    if not isinstance(claimed_return_code, int) or isinstance(claimed_return_code, bool):
        # Substituting 0 would countersign a record that never stated its exit
        # status as though it had stated success.
        return {"record": key, "verdict": "NOT_REPLAYABLE", "reason": "return-code-missing"}
    claimed_counts = evidence.get("summary")
    if not isinstance(claimed_counts, dict):
        return {"record": key, "verdict": "NOT_REPLAYABLE", "reason": "summary-missing"}
    verdict, return_code, observed, observed_counts = _rerun(
        nodeids, root, temp_root, key.replace("/", "-"), timeout
    )
    claimed = _outcome_fingerprint("PASS", nodeids, claimed_return_code, _counts(claimed_counts))
    observed_fingerprint = _outcome_fingerprint(verdict, observed, return_code, observed_counts)
    return {
        "record": key,
        "verdict": "MATCH" if claimed == observed_fingerprint else "MISMATCH",
        "observed_verdict": verdict,
        "observed_return_code": return_code,
        "claimed_fingerprint": claimed,
        "observed_fingerprint": observed_fingerprint,
    }


def countersign(bundle_path: Path, *, root: Path, temp_root: Path, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> dict[str, Any]:
    """Re-execute every passing record and report what could be confirmed."""

    raw = json.loads(Path(bundle_path).read_text(encoding="utf-8"))
    bundle = AcceptanceBundle.from_dict(raw)
    results: list[dict[str, Any]] = []
    confirmed: list[str] = []
    for finding, section in sorted(bundle.sections.items()):
        for layer, evidence in sorted(section.layers.items()):
            if not isinstance(evidence, dict) or evidence.get("outcome") != "PASS":
                continue
            key = _coverage_key(finding, layer)
            record = _replay_record(key, evidence, root, temp_root, timeout)
            results.append(record)
            if record["verdict"] == "MATCH":
                confirmed.append(key)
    expected = {
        _coverage_key(finding, layer)
        for finding, section in bundle.sections.items()
        for layer, evidence in section.layers.items()
        if isinstance(evidence, dict) and evidence.get("outcome") == "PASS"
    }
    complete = bool(expected) and set(confirmed) == expected
    return {
        "version": COUNTERSIGNATURE_VERSION,
        "bundle_output_sha256": bundle.output_sha256,
        "bundle_artifact_id": bundle.artifact_id,
        "head_sha": bundle.head_sha,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "results": results,
        "confirmed": sorted(confirmed),
        "expected": sorted(expected),
        "complete": complete,
        "attestation": _countersignature_attestation(bundle, confirmed, root=root) if complete else None,
    }


def _countersignature_attestation(
    bundle: AcceptanceBundle, confirmed: list[str], *, root: Path | None = None
) -> dict[str, Any] | None:
    """Sign the re-execution result, or return ``None`` when no key is available."""

    checked_root = Path(root).resolve() if root is not None else ROOT
    references = _attestation_references(checked_root)
    if references is None:
        return None
    reference = next((item for item in references.values() if item.role == "countersign"), None)
    if reference is None:
        return None
    key = resolve_key(reference.custody, root=checked_root)
    return build_attestation(
        role="countersign",
        key_id=reference.key_id,
        custody=reference.custody,
        digest=payload_digest(bundle.unsigned_payload()),
        signed_at=datetime.now(timezone.utc).isoformat(),
        key=key,
        covers=sorted(confirmed),
        provenance={"issuer": "countersign_pilot_acceptance", "method": "independent-re-execution"},
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    bundle_path = args.bundle if args.bundle.is_absolute() else root / args.bundle
    output = args.output or (root / "artifacts" / "pilot-countersignature.json")
    temp_root = root / ".tmp-pilot-countersign"
    temp_root.mkdir(parents=True, exist_ok=True)
    try:
        receipt = countersign(bundle_path, root=root, temp_root=temp_root, timeout=args.timeout_seconds)
    finally:
        import shutil

        shutil.rmtree(temp_root, ignore_errors=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(canonical_json(receipt) + "\n", encoding="utf-8")
    print(json.dumps({
        "artifact": str(output),
        "complete": receipt["complete"],
        "confirmed": len(receipt["confirmed"]),
        "expected": len(receipt["expected"]),
        "signed": bool(receipt["attestation"] and receipt["attestation"].get("signature")),
    }, ensure_ascii=True, sort_keys=True))
    return 0 if receipt["complete"] and receipt["attestation"] and receipt["attestation"].get("signature") else 2


if __name__ == "__main__":
    raise SystemExit(main())
