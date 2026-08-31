"""Fail-closed parsing and verification for release evidence bundles."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Literal


Verdict = Literal["PASS", "BLOCKED", "UNCLASSIFIED"]
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_HEAD_SHA = re.compile(r"^[0-9a-f]{40}$")
_SUMMARY_TOKEN = re.compile(
    r"(?P<count>\d+)\s+(?P<label>failed|passed|errors?|skipped|xfailed|xpassed)\b",
    re.IGNORECASE,
)
_FAILED_LINE = re.compile(r"^\s*FAILED\s+(?P<nodeid>\S+)", re.IGNORECASE)
_FAILED_STATUS_LINE = re.compile(r"^\s*(?P<nodeid>\S+)\s+FAILED(?:\s|$)", re.IGNORECASE)
_ERROR_LINE = re.compile(r"^\s*ERROR\s+(?P<nodeid>\S+?)(?:\s+-|\s*$)", re.IGNORECASE)
_ERROR_AT_LINE = re.compile(r"^\s*ERROR\s+at\s+setup\s+of\s+(?P<nodeid>\S+)", re.IGNORECASE)
_COLLECTION_LINE = re.compile(r"^\s*(?:ERROR\s+)?collecting\s+(?P<nodeid>\S+)", re.IGNORECASE)


@dataclass(frozen=True)
class ParsedOutcome:
    passed: int
    failed: int
    errors: int
    skipped: int
    xfailed: int
    collection_errors: int
    interrupted: bool
    return_code: int
    failed_nodeids: tuple[str, ...] = ()
    error_nodeids: tuple[str, ...] = ()
    summary_present: bool = False


@dataclass(frozen=True)
class VerificationResult:
    verdict: Verdict
    reasons: tuple[str, ...]
    checked_sha256: str


def _ordered_unique(values: list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if value))


def _parse_summary(text: str) -> tuple[dict[str, int], bool]:
    """Parse pytest's terminal output without treating absent values as zero.

    Pytest emits one final comma-separated summary.  We intentionally use the
    last summary line so output from a nested invocation cannot be double-counted.
    """

    summary_counts: dict[str, int] = {}
    summary_present = False
    for line in text.splitlines():
        matches = list(_SUMMARY_TOKEN.finditer(line))
        if matches and (" in " in line.lower() or line.lstrip().startswith(tuple(str(i) for i in range(10)))):
            summary_counts = {}
            for match in matches:
                label = match.group("label").lower()
                key = {
                    "passed": "passed",
                    "failed": "failed",
                    "error": "errors",
                    "errors": "errors",
                    "skipped": "skipped",
                    "xfailed": "xfailed",
                    "xpassed": "xpassed",
                }[label]
                summary_counts[key] = int(match.group("count"))
            summary_present = True

    return summary_counts, summary_present


def _parse_nodes(text: str) -> tuple[tuple[str, ...], tuple[str, ...], int]:
    failed_nodeids: list[str] = []
    error_nodeids: list[str] = []
    collection_errors = 0
    for line in text.splitlines():
        failed_match = _FAILED_LINE.match(line)
        if failed_match is None:
            failed_match = _FAILED_STATUS_LINE.match(line)
        if failed_match:
            failed_nodeids.append(failed_match.group("nodeid").rstrip(":,"))
            continue
        error_match = _ERROR_LINE.match(line) or _ERROR_AT_LINE.match(line)
        if error_match:
            error_nodeids.append(error_match.group("nodeid").rstrip(":,"))
            continue
        collection_match = _COLLECTION_LINE.match(line)
        if collection_match:
            collection_errors += 1

    return _ordered_unique(failed_nodeids), _ordered_unique(error_nodeids), collection_errors


def parse_pytest_output(text: str, return_code: int) -> ParsedOutcome:
    """Parse pytest's terminal output without treating absent values as zero."""

    if not isinstance(text, str):
        raise TypeError("pytest output must be text")
    try:
        native_return_code = int(return_code)
    except (TypeError, ValueError) as exc:
        raise TypeError("return_code must be an integer") from exc
    summary_counts, summary_present = _parse_summary(text)
    failed_nodeids, error_nodeids, collection_errors = _parse_nodes(text)
    interrupted = bool(re.search(
        r"keyboardinterrupt|keyboard interrupt|interrupted|^!.*interrupt",
        text, re.IGNORECASE | re.MULTILINE,
    ))
    errors = summary_counts.get("errors", len(error_nodeids))
    # Collection errors are a subset of pytest's error count but are kept as a
    # separate blocker for callers that need to distinguish import failures.
    collection_errors = max(collection_errors, 0)
    return ParsedOutcome(
        passed=summary_counts.get("passed", 0),
        failed=summary_counts.get("failed", 0),
        errors=errors,
        skipped=summary_counts.get("skipped", 0),
        xfailed=summary_counts.get("xfailed", 0),
        collection_errors=collection_errors,
        interrupted=interrupted,
        return_code=native_return_code,
        failed_nodeids=failed_nodeids,
        error_nodeids=error_nodeids,
        summary_present=summary_present,
    )


def _unexpected_failures(outcome: ParsedOutcome, allowlist: frozenset[str]) -> set[str]:
    allowed = frozenset(str(item) for item in allowlist)
    return {
        nodeid for nodeid in outcome.failed_nodeids
        if not any(nodeid == entry or nodeid.startswith(entry + "::") for entry in allowed)
    }


def classify_verdict(outcome: ParsedOutcome, allowlist: frozenset[str]) -> Verdict:
    """Classify one parsed run, failing closed for every ambiguous condition."""

    if not isinstance(outcome, ParsedOutcome):
        raise TypeError("outcome must be ParsedOutcome")
    unexpected = _unexpected_failures(outcome, allowlist)
    if (
        not outcome.summary_present
        or outcome.return_code != 0
        or outcome.errors
        or outcome.collection_errors
        or outcome.interrupted
        or unexpected
    ):
        return "BLOCKED" if outcome.summary_present else "UNCLASSIFIED"
    if not outcome.failed and not outcome.errors and not outcome.collection_errors:
        return "PASS"
    return "UNCLASSIFIED"


def _reason_for_field(name: str) -> str:
    return f"missing or invalid field: {name}"


def _load_bundle(path: Path) -> dict[str, object] | VerificationResult:
    """Verify a JSON evidence bundle and return a machine-readable verdict."""

    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return VerificationResult("BLOCKED", (f"unable to read bundle: {type(exc).__name__}",), "")
    return payload


def _validate_bundle(payload: dict[str, object]) -> list[str]:
    required = (
        "schema_version",
        "artifact_id",
        "head_sha",
        "branch",
        "started_at",
        "finished_at",
        "command",
        "environment",
        "outcomes",
        "allowlist",
        "verdict",
        "artifacts",
        "output_sha256",
    )
    reasons = [_reason_for_field(field) for field in required if field not in payload]
    if reasons:
        return reasons

    reasons.extend(_validate_scalars(payload))
    reasons.extend(_validate_collections(payload))
    declared_digest = payload.get("output_sha256")
    if not isinstance(declared_digest, str) or not _SHA256.fullmatch(declared_digest):
        reasons.append(_reason_for_field("output_sha256"))

    return reasons


def _validate_scalars(payload: dict[str, object]) -> list[str]:
    reasons: list[str] = []
    if payload.get("schema_version") != "1": reasons.append("unsupported schema_version")
    if not isinstance(payload.get("artifact_id"), str) or not payload["artifact_id"].strip(): reasons.append(_reason_for_field("artifact_id"))
    if not isinstance(payload.get("head_sha"), str) or not _HEAD_SHA.fullmatch(payload["head_sha"]): reasons.append(_reason_for_field("head_sha"))
    if not isinstance(payload.get("branch"), str) or not payload["branch"].strip(): reasons.append(_reason_for_field("branch"))
    if not isinstance(payload.get("command"), str) or not payload["command"].strip(): reasons.append(_reason_for_field("command"))
    if payload.get("verdict") not in {"PASS", "BLOCKED", "UNCLASSIFIED"}: reasons.append(_reason_for_field("verdict"))
    return reasons


def _validate_collections(payload: dict[str, object]) -> list[str]:
    reasons: list[str] = []
    if not isinstance(payload.get("environment"), dict): reasons.append(_reason_for_field("environment"))
    if not isinstance(payload.get("allowlist"), list) or not all(isinstance(v, str) for v in payload["allowlist"]): reasons.append(_reason_for_field("allowlist"))
    if not isinstance(payload.get("artifacts"), list): reasons.append(_reason_for_field("artifacts"))
    declared_digest = payload.get("output_sha256")
    if not isinstance(declared_digest, str) or not _SHA256.fullmatch(declared_digest): reasons.append(_reason_for_field("output_sha256"))
    return reasons


def _parse_bundle_outcome(payload: dict[str, object], reasons: list[str]) -> ParsedOutcome | None:
    outcomes_payload = payload.get("outcomes")
    outcome: ParsedOutcome | None = None
    if not isinstance(outcomes_payload, dict):
        reasons.append(_reason_for_field("outcomes"))
    else:
        outcome_fields = (
            "passed",
            "failed",
            "errors",
            "skipped",
            "xfailed",
            "collection_errors",
            "interrupted",
            "return_code",
        )
        if any(field not in outcomes_payload for field in outcome_fields):
            reasons.append("outcomes are incomplete")
        else:
            try:
                counts = {
                    field: outcomes_payload[field] for field in outcome_fields
                }
                if any(
                    type(counts[field]) is not int
                    for field in outcome_fields
                    if field != "interrupted"
                ) or type(counts["interrupted"]) is not bool:
                    raise ValueError("outcome counts have invalid types")
                if any(
                    counts[field] < 0
                    for field in outcome_fields
                    if field != "interrupted"
                ):
                    raise ValueError("outcome counts cannot be negative")
                outcome = ParsedOutcome(
                    **counts,
                    failed_nodeids=tuple(outcomes_payload.get("failed_nodeids", ())),
                    error_nodeids=tuple(outcomes_payload.get("error_nodeids", ())),
                    summary_present=True,
                )
            except (TypeError, ValueError) as exc:
                reasons.append(f"invalid outcomes: {exc}")

    return outcome


def _check_bundle_output(path: Path, payload: dict[str, object], reasons: list[str]) -> str:
    declared_digest = payload.get("output_sha256")
    output = payload.get("output")
    if output is None:
        output = payload.get("output_text")
    if output is None and isinstance(payload.get("output_path"), str):
        output_path = Path(path).parent / payload["output_path"]
        try:
            output = output_path.read_bytes()
        except OSError as exc:
            reasons.append(f"unable to read output: {type(exc).__name__}")
    if output is not None:
        if not isinstance(output, (str, bytes)):
            reasons.append("output must be text")
        else:
            output_bytes = output.encode("utf-8") if isinstance(output, str) else output
            checked_sha256 = sha256(output_bytes).hexdigest()
            if checked_sha256 != declared_digest:
                reasons.append("output_sha256 mismatch")
            return checked_sha256
    else:
        # Bundles may store output separately; an absent output is unverifiable.
        reasons.append("missing output for checksum verification")
    return ""


def verify_bundle(path: Path) -> VerificationResult:
    """Verify a JSON evidence bundle and return a machine-readable verdict."""

    payload_or_result = _load_bundle(Path(path))
    if isinstance(payload_or_result, VerificationResult):
        return payload_or_result
    payload = payload_or_result
    reasons = _validate_bundle(payload)
    if reasons:
        return VerificationResult("BLOCKED", tuple(reasons), "")
    outcome = _parse_bundle_outcome(payload, reasons)
    checked_sha256 = _check_bundle_output(Path(path), payload, reasons)

    computed: Verdict | None = None
    if outcome is not None and not reasons:
        computed = classify_verdict(outcome, frozenset(payload["allowlist"]))
        if payload["verdict"] != computed:
            reasons.append(f"verdict mismatch: declared {payload['verdict']!r}, computed {computed!r}")

    if reasons:
        # A structurally valid but incomplete run is unclassified; malformed or
        # tampered bundles are blocked so callers never mistake them for PASS.
        return VerificationResult("BLOCKED", tuple(reasons), checked_sha256)
    assert computed is not None
    return VerificationResult(computed, (), checked_sha256)
