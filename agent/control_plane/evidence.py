"""Fail-closed parsing and verification for release evidence bundles."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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
_VITEST_SUMMARY = re.compile(
    r"^\s*(?P<label>Test\s+Files|Tests)\s+(?P<counts>.+?)\s*\((?P<total>\d+)\)\s*$",
    re.IGNORECASE,
)
_VITEST_COUNT = re.compile(
    r"(?P<count>\d+)\s+(?P<label>passed|failed|skipped|todo|pending)", re.IGNORECASE
)
_FAILED_LINE = re.compile(r"^\s*FAILED\s+(?P<nodeid>\S+)", re.IGNORECASE)
_FAILED_STATUS_LINE = re.compile(r"^\s*(?P<nodeid>\S+)\s+FAILED(?:\s|$)", re.IGNORECASE)
# Verbose (``-v``) runs report per-test outcomes as ``<nodeid> ERROR``.  Without
# this counterpart to ``_FAILED_STATUS_LINE`` an errored run keeps its aggregate
# count but loses every node id, so the errors cannot be triaged individually.
_ERROR_STATUS_LINE = re.compile(r"^\s*(?P<nodeid>\S+)\s+ERROR(?:\s|$)", re.IGNORECASE)
_ERROR_LINE = re.compile(r"^\s*ERROR\s+(?P<nodeid>\S+?)(?:\s+-|\s*$)", re.IGNORECASE)
# pytest pads its section headers with underscores/equals signs, so these two
# patterns must tolerate that run-in prefix; anchoring on ``\s*`` alone never
# matched real output and left ``collection_errors`` structurally zero.
_ERROR_AT_LINE = re.compile(r"^[\s_=]*ERROR\s+at\s+setup\s+of\s+(?P<nodeid>\S+)", re.IGNORECASE)
# Normal pytest progress starts with ``collecting ...``; only the explicit
# ``ERROR collecting`` form denotes a collection failure.
_COLLECTION_LINE = re.compile(r"^[\s_=]*ERROR\s+collecting\s+(?P<nodeid>\S+)", re.IGNORECASE)
# The ``ERRORS`` banner proves at least one error even when a malformed or
# absent tally would otherwise report none.
_ERRORS_SECTION = re.compile(r"^[\s=_]*ERRORS[\s=_]*$", re.IGNORECASE)
# A pytest tally always states its duration; requiring that shape stops an
# arbitrary line of captured text from being read as the run summary.
_SUMMARY_DURATION = re.compile(r"\bin\s+\d+(?:\.\d+)?\s*s\b", re.IGNORECASE)
# Counts that must never be lowered by a later line: under-reporting a failure
# or an error is the one direction that could turn a red run green.
_MONOTONIC_SUMMARY_KEYS = ("failed", "errors")
_REQUIRED_STATE_SECTIONS = (
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
)
_FUNCTIONAL_STATE_SECTIONS = frozenset({
    "artifacts",
    "backend-focused",
    "frontend-focused",
    "rollback-local-rehearsal",
    "backend-full-regression",
    "frontend-serial-regression",
    "source-scans",
})
_DEFAULT_EXTERNAL_GATES = {"H1": "blocked", "H2": "blocked", "owner": "not-authorized"}


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


ProbeVerdict = Literal["PASS", "BLOCKED", "UNAVAILABLE"]


@dataclass(frozen=True)
class ProbeReceiptVerification:
    """Fail-closed verification result for an operational probe receipt."""

    verdict: ProbeVerdict
    reasons: tuple[str, ...] = ()


def _probe_timestamp(value: object, field: str, reasons: list[str]) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        reasons.append(f"missing or invalid field: {field}")
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        reasons.append(f"invalid timestamp: {field}")
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        reasons.append("timestamps must be timezone-aware")
        return None
    return parsed


def _probe_required_fields(receipt: dict[str, object]) -> list[str]:
    required = (
        "probe_id", "head_sha", "environment_id", "started_at", "finished_at",
        "command", "exit_code", "output_sha256", "test_nodeids", "verdict",
    )
    return [f"missing or invalid field: {field}" for field in required if field not in receipt]


def _probe_identity_reasons(receipt: dict[str, object]) -> list[str]:
    reasons: list[str] = []
    for field in ("probe_id", "environment_id", "command"):
        value = receipt.get(field)
        if not isinstance(value, str) or not value.strip():
            reasons.append(f"missing or invalid field: {field}")
    head_sha = receipt.get("head_sha")
    if not isinstance(head_sha, str) or not _HEAD_SHA.fullmatch(head_sha):
        reasons.append("missing or invalid field: head_sha")
    return reasons


def _probe_output_reasons(receipt: dict[str, object]) -> list[str]:
    reasons: list[str] = []
    output_sha256 = receipt.get("output_sha256")
    if not isinstance(output_sha256, str) or not _SHA256.fullmatch(output_sha256):
        reasons.append("missing or invalid field: output_sha256")
    captured_output = receipt.get("captured_output")
    # A PASS receipt without the transcript it hashes is only a self-attested
    # claim: the digest format alone cannot prove what was executed.  Block it
    # until a signed external custody format exists.
    if receipt.get("verdict") == "PASS" and not isinstance(captured_output, str):
        reasons.append("PASS receipt requires captured_output")
    if captured_output is not None:
        if not isinstance(captured_output, str):
            reasons.append("captured_output must be text")
        elif isinstance(output_sha256, str) and _SHA256.fullmatch(output_sha256):
            if sha256(captured_output.encode("utf-8")).hexdigest() != output_sha256:
                reasons.append("output_sha256 does not match captured_output")
    return reasons


def _probe_clock_reasons(receipt: dict[str, object]) -> list[str]:
    reasons: list[str] = []
    started_at = _probe_timestamp(receipt.get("started_at"), "started_at", reasons)
    finished_at = _probe_timestamp(receipt.get("finished_at"), "finished_at", reasons)
    if started_at is not None and finished_at is not None and finished_at < started_at:
        reasons.append("finished_at must not precede started_at")
    return reasons


def _probe_capture_reasons(receipt: dict[str, object]) -> list[str]:
    reasons: list[str] = []
    exit_code = receipt.get("exit_code")
    if type(exit_code) is not int:
        reasons.append("missing or invalid field: exit_code")
    nodeids = receipt.get("test_nodeids")
    if not isinstance(nodeids, list) or not all(isinstance(nodeid, str) and nodeid.strip() for nodeid in nodeids):
        reasons.append("missing or invalid field: test_nodeids")
    return reasons


def _probe_verdict_reasons(receipt: dict[str, object]) -> list[str]:
    reasons: list[str] = []
    declared_verdict = receipt.get("verdict")
    if declared_verdict not in {"PASS", "BLOCKED", "UNAVAILABLE"}:
        reasons.append("missing or invalid field: verdict")
    return reasons


def _probe_status_exit_reasons(receipt: dict[str, object]) -> list[str]:
    reasons: list[str] = []
    exit_code = receipt.get("exit_code")
    declared_verdict = receipt.get("verdict")
    if declared_verdict == "UNAVAILABLE" and type(exit_code) is int and exit_code == 0:
        reasons.append("UNAVAILABLE receipt must have nonzero exit_code")
    if declared_verdict == "BLOCKED" and type(exit_code) is int and exit_code == 0:
        reasons.append("BLOCKED receipt must have nonzero exit_code")
    return reasons


def _probe_pass_reasons(receipt: dict[str, object]) -> list[str]:
    reasons: list[str] = []
    if receipt.get("verdict") == "PASS" and type(receipt.get("exit_code")) is int and receipt["exit_code"] != 0:
        reasons.append("PASS receipt must have exit_code 0")
    if receipt.get("verdict") == "PASS" and isinstance(receipt.get("test_nodeids"), list) and not receipt["test_nodeids"]:
        reasons.append("PASS receipt must list executed test_nodeids")
    return reasons


def _probe_execution_reasons(receipt: dict[str, object]) -> list[str]:
    return [
        *_probe_clock_reasons(receipt),
        *_probe_capture_reasons(receipt),
        *_probe_verdict_reasons(receipt),
        *_probe_status_exit_reasons(receipt),
        *_probe_pass_reasons(receipt),
    ]


def verify_probe_receipt(receipt: object) -> ProbeReceiptVerification:
    """Validate the portable receipt contract emitted by staging probes."""

    if not isinstance(receipt, dict):
        return ProbeReceiptVerification("BLOCKED", ("receipt must be a JSON object",))

    reasons = [
        *_probe_required_fields(receipt),
        *_probe_identity_reasons(receipt),
        *_probe_output_reasons(receipt),
        *_probe_execution_reasons(receipt),
    ]
    if reasons:
        return ProbeReceiptVerification("BLOCKED", tuple(dict.fromkeys(reasons)))
    return ProbeReceiptVerification(receipt["verdict"], ())


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
        if matches and _SUMMARY_DURATION.search(line):
            # Keep the last summary so a nested invocation cannot double-count,
            # but never let it lower an already-observed failure/error count.
            carried = {key: summary_counts[key] for key in _MONOTONIC_SUMMARY_KEYS if key in summary_counts}
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
            for key, value in carried.items():
                summary_counts[key] = max(summary_counts.get(key, 0), value)
            summary_present = True

    return summary_counts, summary_present


def _parse_nodes(text: str) -> tuple[tuple[str, ...], tuple[str, ...], int, bool]:
    failed_nodeids: list[str] = []
    error_nodeids: list[str] = []
    collection_errors = 0
    errors_section = False
    for line in text.splitlines():
        if _ERRORS_SECTION.match(line):
            errors_section = True
            continue
        failed_match = _FAILED_LINE.match(line)
        if failed_match is None:
            failed_match = _FAILED_STATUS_LINE.match(line)
        if failed_match:
            nodeid = failed_match.group("nodeid").rstrip(":,")
            # A summary such as ``1 failed in 0.1s`` is not a node-level line.
            if not nodeid.isdigit():
                failed_nodeids.append(nodeid)
            continue
        # ``ERROR collecting`` is a strict subset of the at-setup/short forms, so
        # it must be tested before them or a collection failure reads as a plain
        # node error and stops being counted separately.
        collection_match = _COLLECTION_LINE.match(line)
        if collection_match:
            collection_errors += 1
            error_nodeids.append(collection_match.group("nodeid").rstrip(":,"))
            continue
        error_match = _ERROR_AT_LINE.match(line) or _ERROR_LINE.match(line) or _ERROR_STATUS_LINE.match(line)
        if error_match:
            nodeid = error_match.group("nodeid").rstrip(":,")
            # ``1 error in 0.1s`` is a tally, not a node id.
            if not nodeid.isdigit():
                error_nodeids.append(nodeid)
            continue

    return _ordered_unique(failed_nodeids), _ordered_unique(error_nodeids), collection_errors, errors_section


def parse_pytest_output(text: str, return_code: int) -> ParsedOutcome:
    """Parse pytest's terminal output without treating absent values as zero."""

    if not isinstance(text, str):
        raise TypeError("pytest output must be text")
    try:
        native_return_code = int(return_code)
    except (TypeError, ValueError) as exc:
        raise TypeError("return_code must be an integer") from exc
    summary_counts, summary_present = _parse_summary(text)
    failed_nodeids, error_nodeids, collection_errors, errors_section = _parse_nodes(text)
    interrupted = bool(re.search(
        r"keyboardinterrupt|keyboard interrupt|interrupted|^!.*interrupt",
        text, re.IGNORECASE | re.MULTILINE,
    ))
    # Node-level errors remain blockers even when a malformed/native summary
    # under-reports the aggregate error count.  An ``ERRORS`` banner proves at
    # least one error even when no node id survived the report format.
    errors = max(summary_counts.get("errors", 0), len(error_nodeids), 1 if errors_section else 0)
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


def parse_test_output(text: str, return_code: int) -> ParsedOutcome:
    """Parse pytest or Vitest terminal summaries into one evidence shape."""

    pytest_outcome = parse_pytest_output(text, return_code)
    if pytest_outcome.summary_present:
        return pytest_outcome
    counts, saw_vitest, inconsistent = _parse_vitest_summaries(text)
    if not saw_vitest:
        return pytest_outcome
    failed_nodeids, error_nodeids, collection_errors, errors_section = _parse_nodes(text)
    return ParsedOutcome(
        passed=counts.get("passed", 0),
        failed=counts.get("failed", 0),
        errors=max(
            pytest_outcome.errors,
            len(error_nodeids),
            1 if inconsistent else 0,
            1 if errors_section else 0,
        ),
        skipped=counts.get("skipped", 0) + counts.get("todo", 0) + counts.get("pending", 0),
        xfailed=0,
        collection_errors=collection_errors,
        interrupted=pytest_outcome.interrupted,
        return_code=int(return_code),
        failed_nodeids=failed_nodeids,
        error_nodeids=error_nodeids,
        summary_present=True,
    )


def _parse_vitest_summaries(text: str) -> tuple[dict[str, int], bool, bool]:
    counts: dict[str, int] = {}
    totals: dict[str, int] = {}
    inconsistent = False
    for line in text.splitlines():
        match = _VITEST_SUMMARY.match(line)
        if not match:
            continue
        label = match.group("label").lower()
        parsed = {item.group("label").lower(): int(item.group("count")) for item in _VITEST_COUNT.finditer(match.group("counts"))}
        total = int(match.group("total"))
        totals[label] = total
        inconsistent = inconsistent or total == 0 or sum(parsed.values()) != total
        if label.startswith("tests") or not counts:
            counts = parsed
    saw = bool(totals)
    return counts, saw, inconsistent or set(totals) != {"test files", "tests"}


def _unexpected_failures(outcome: ParsedOutcome, allowlist: frozenset[str]) -> set[str]:
    allowed = frozenset(str(item) for item in allowlist)
    return {
        nodeid for nodeid in outcome.failed_nodeids
        if nodeid not in allowed
    }


def classify_verdict(outcome: ParsedOutcome, allowlist: frozenset[str]) -> Verdict:
    """Classify one parsed run, failing closed for every ambiguous condition."""

    if not isinstance(outcome, ParsedOutcome):
        raise TypeError("outcome must be ParsedOutcome")
    unexpected = _unexpected_failures(outcome, allowlist)
    if _has_blocking_outcome(outcome, unexpected):
        return "BLOCKED" if outcome.summary_present else "UNCLASSIFIED"
    if not outcome.failed and not outcome.errors and not outcome.collection_errors:
        return "PASS"
    return "UNCLASSIFIED"


def _has_blocking_outcome(outcome: ParsedOutcome, unexpected: set[str]) -> bool:
    return any((
        not outcome.summary_present,
        outcome.return_code != 0,
        bool(outcome.errors),
        bool(outcome.error_nodeids),
        bool(outcome.collection_errors),
        outcome.interrupted,
        bool(unexpected),
    ))


def _reason_for_field(name: str) -> str:
    return f"missing or invalid field: {name}"


def _load_bundle(path: Path) -> dict[str, object] | VerificationResult:
    """Verify a JSON evidence bundle and return a machine-readable verdict."""

    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return VerificationResult("BLOCKED", (f"unable to read bundle: {type(exc).__name__}",), "")
    if not isinstance(payload, dict):
        return VerificationResult("BLOCKED", ("bundle must be a JSON object",), "")
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
    if payload.get("schema_version") != "1":
        reasons.append("unsupported schema_version")
    for name in ("artifact_id", "branch", "command", "started_at", "finished_at"):
        value = payload.get(name)
        if not isinstance(value, str) or not value.strip():
            reasons.append(_reason_for_field(name))
    head_sha = payload.get("head_sha")
    if not isinstance(head_sha, str) or not _HEAD_SHA.fullmatch(head_sha):
        reasons.append(_reason_for_field("head_sha"))
    if payload.get("verdict") not in {"PASS", "BLOCKED", "UNCLASSIFIED"}:
        reasons.append(_reason_for_field("verdict"))
    return reasons


def _validate_collections(payload: dict[str, object]) -> list[str]:
    reasons: list[str] = []
    if not isinstance(payload.get("environment"), dict) or not payload["environment"]: reasons.append(_reason_for_field("environment"))
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
                    failed_nodeids=_validated_nodeids(outcomes_payload.get("failed_nodeids", ()), "failed_nodeids"),
                    error_nodeids=_validated_nodeids(outcomes_payload.get("error_nodeids", ()), "error_nodeids"),
                    summary_present=True,
                )
            except (TypeError, ValueError) as exc:
                reasons.append(f"invalid outcomes: {exc}")

    return outcome


def _validated_nodeids(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{label} must be a list of strings")
    return _ordered_unique(list(value))


def _check_bundle_output(
    path: Path, payload: dict[str, object], reasons: list[str]
) -> tuple[bytes | None, str]:
    declared_digest = payload.get("output_sha256")
    has_inline_output = payload.get("output") is not None or payload.get("output_text") is not None
    if has_inline_output and "output_path" in payload:
        reasons.append("bundle cannot contain both inline output and output_path")
        return None, ""
    output = payload.get("output")
    if output is None:
        output = payload.get("output_text")
    if output is None and isinstance(payload.get("output_path"), str):
        output = _read_output_path(path, payload["output_path"], reasons)
    if output is not None:
        if not isinstance(output, (str, bytes)):
            reasons.append("output must be text")
        else:
            output_bytes = output.encode("utf-8") if isinstance(output, str) else output
            checked_sha256 = sha256(output_bytes).hexdigest()
            if checked_sha256 != declared_digest:
                reasons.append("output_sha256 mismatch")
            return output_bytes, checked_sha256
    else:
        # Bundles may store output separately; an absent output is unverifiable.
        reasons.append("missing output for checksum verification")
    return None, ""


def _read_output_path(path: Path, raw_output_path: object, reasons: list[str]) -> bytes | None:
    try:
        if not isinstance(raw_output_path, str) or "\x00" in raw_output_path:
            raise ValueError("invalid output_path")
        if Path(raw_output_path).is_absolute():
            reasons.append("output_path must be relative")
            return None
        bundle_dir = Path(path).parent.resolve()
        output_path = (bundle_dir / raw_output_path).resolve()
        output_path.relative_to(bundle_dir)
        return output_path.read_bytes()
    except ValueError as exc:
        reasons.append(str(exc) or "invalid output_path")
    except (OSError, RuntimeError) as exc:
        reasons.append(f"unable to read output: {type(exc).__name__}")
    return None


def _compare_output_outcome(
    output: bytes,
    outcome: ParsedOutcome,
    allowlist: frozenset[str],
    declared_verdict: object,
    reasons: list[str],
) -> bool:
    try:
        text = output.decode("utf-8")
    except UnicodeDecodeError:
        reasons.append("stored output is not valid UTF-8")
        return False
    # The native return code is part of the stored declaration; parsing with it
    # prevents a clean-looking output from masking a failed process.
    parsed = parse_test_output(text, outcome.return_code)
    if not parsed.summary_present:
        reasons.append("stored output has no pytest summary")
        return False
    fields = (
        "passed", "failed", "errors", "skipped", "xfailed", "collection_errors",
        "interrupted", "return_code", "failed_nodeids", "error_nodeids",
    )
    if any(getattr(parsed, field) != getattr(outcome, field) for field in fields):
        reasons.append("stored output outcomes do not match declared outcomes")
    parsed_verdict = classify_verdict(parsed, allowlist)
    declared_outcome_verdict = classify_verdict(outcome, allowlist)
    if parsed_verdict != declared_outcome_verdict or parsed_verdict != declared_verdict:
        reasons.append("stored output verdict does not match declared verdict")
    return True


def _verify_standard_bundle(path: Path, payload: dict[str, object]) -> VerificationResult:
    reasons = _validate_bundle(payload)
    if reasons:
        return VerificationResult("BLOCKED", tuple(reasons), "")
    outcome = _parse_bundle_outcome(payload, reasons)
    output_bytes, checked_sha256 = _check_bundle_output(Path(path), payload, reasons)
    output_parseable = True
    if output_bytes is not None and outcome is not None and not reasons:
        output_parseable = _compare_output_outcome(
            output_bytes,
            outcome,
            frozenset(payload["allowlist"]),
            payload["verdict"],
            reasons,
        )

    computed: Verdict | None = None
    if outcome is not None and not reasons:
        computed = classify_verdict(outcome, frozenset(payload["allowlist"]))
        if payload["verdict"] != computed:
            reasons.append(f"verdict mismatch: declared {payload['verdict']!r}, computed {computed!r}")

    if reasons:
        # A structurally valid but incomplete run is unclassified; malformed or
        # tampered bundles are blocked so callers never mistake them for PASS.
        if output_parseable is False and reasons == ["stored output has no pytest summary"]:
            return VerificationResult("UNCLASSIFIED", tuple(reasons), checked_sha256)
        return VerificationResult("BLOCKED", tuple(reasons), checked_sha256)
    assert computed is not None
    return VerificationResult(computed, (), checked_sha256)


def verify_bundle(path: Path) -> VerificationResult:
    """Verify a JSON evidence bundle and return a machine-readable verdict."""

    payload_or_result = _load_bundle(Path(path))
    if isinstance(payload_or_result, VerificationResult):
        return payload_or_result
    if payload_or_result.get("bundle_kind") == "launch-safety-state-v1":
        return _verify_state_bundle(payload_or_result)
    return _verify_standard_bundle(Path(path), payload_or_result)


def _validate_state_outcomes(
    name: str, outcomes: object, verdict: object, status: object = None,
) -> list[str]:
    if not isinstance(outcomes, dict):
        return [f"invalid section outcomes: {name}"]
    if outcomes.get("evidence_kind") == "native-command":
        return _validate_native_state_outcomes(name, outcomes, verdict, status)
    try:
        parsed = _parse_state_outcomes(outcomes)
    except (KeyError, TypeError, ValueError) as exc:
        return [f"invalid section outcomes: {name}: {exc}"]
    if classify_verdict(parsed, frozenset()) != verdict:
        return [f"section outcomes/verdict mismatch: {name}"]
    return []


def _validate_native_state_outcomes(
    name: str, outcomes: dict[str, object], verdict: object, status: object = None,
) -> list[str]:
    if outcomes.get("summary_present") is not True or type(outcomes.get("return_code")) is not int:
        if (
            name == "browser-opt-in"
            and status == "skip"
            and outcomes.get("summary_present") is False
            and outcomes.get("return_code") == 0
            and verdict == "UNCLASSIFIED"
        ):
            return []
        return [f"invalid native section outcomes: {name}"]
    expected = "PASS" if outcomes["return_code"] == 0 else "BLOCKED"
    return [] if expected == verdict else [f"section outcomes/verdict mismatch: {name}"]


def _parse_state_outcomes(outcomes: dict[str, object]) -> ParsedOutcome:
    fields = (
        "passed", "failed", "errors", "skipped", "xfailed", "collection_errors",
        "interrupted", "return_code", "summary_present",
    )
    if any(field not in outcomes for field in fields):
        raise ValueError("outcomes are incomplete")
    counts = {field: outcomes[field] for field in fields}
    _validate_state_count_values(counts)
    return ParsedOutcome(
        **{field: value for field, value in counts.items() if field != "summary_present"},
        failed_nodeids=_validated_nodeids(outcomes.get("failed_nodeids", ()), "failed_nodeids"),
        error_nodeids=_validated_nodeids(outcomes.get("error_nodeids", ()), "error_nodeids"),
        summary_present=True,
    )


def _validate_state_count_values(counts: dict[str, object]) -> None:
    if counts["summary_present"] is not True:
        raise ValueError("summary_present must be true")
    numeric = [k for k in counts if k not in {"interrupted", "summary_present"}]
    if any(type(counts[k]) is not int for k in numeric):
        raise ValueError("outcome counts have invalid types")
    if type(counts["interrupted"]) is not bool:
        raise ValueError("interrupted must be boolean")
    if any(counts[k] < 0 for k in numeric):
        raise ValueError("outcome counts cannot be negative")


def _validate_state_section(name: str, section: object, revision: str) -> list[str]:
    if not isinstance(section, dict):
        return [f"invalid section: {name}"]
    reasons: list[str] = _validate_section_identity(name, section, revision)
    outcomes = section.get("outcomes")
    if outcomes is not None and outcomes != {}:
        reasons.extend(_validate_captured_state_outcomes(name, section, outcomes))
    if section.get("status") == "fail" or section.get("verdict") == "BLOCKED":
        reasons.append(f"blocked section: {name}")
    return reasons


def _validate_captured_state_outcomes(
    name: str, section: dict[str, object], outcomes: object,
) -> list[str]:
    reasons = _validate_state_outcomes(
        name, outcomes, section.get("verdict"), section.get("status")
    )
    if not _is_approved_native_skip(name, section, outcomes):
        reasons.extend(_validate_state_output_checksum(name, section))
    if (
        isinstance(outcomes, dict)
        and type(outcomes.get("return_code")) is int
        and outcomes.get("return_code") != section.get("exit_code")
    ):
        reasons.append(f"section exit code mismatch: {name}")
    return reasons


def _is_approved_native_skip(
    name: str, section: dict[str, object], outcomes: object,
) -> bool:
    return (
        name == "browser-opt-in"
        and section.get("status") == "skip"
        and isinstance(outcomes, dict)
        and outcomes.get("evidence_kind") == "native-command"
        and outcomes.get("summary_present") is False
        and outcomes.get("return_code") == 0
    )


def _validate_section_identity(name: str, section: dict[str, object], revision: str) -> list[str]:
    reasons: list[str] = []
    status = section.get("status")
    verdict = section.get("verdict")
    exit_code = section.get("exit_code")
    if type(exit_code) is not int:
        reasons.append(f"invalid section exit code: {name}")
    if status not in {"pass", "fail", "skip"}:
        reasons.append(f"invalid section status: {name}")
    if verdict not in {"PASS", "BLOCKED", "UNCLASSIFIED"}:
        reasons.append(f"invalid section verdict: {name}")
    expected = {"pass": "PASS", "fail": "BLOCKED", "skip": "UNCLASSIFIED"}.get(status)
    if expected is not None and verdict != expected:
        reasons.append(f"section status/verdict mismatch: {name}")
    reasons.extend(_validate_state_section_metadata(name, section, revision))
    if name in _FUNCTIONAL_STATE_SECTIONS:
        reasons.extend(_validate_functional_state_section(name, section, revision))
    elif name == "browser-opt-in" and section.get("status") == "pass":
        reasons.extend(_validate_functional_state_section(name, section, revision))
    return reasons


def _validate_functional_state_section(
    name: str, section: dict[str, object], revision: str
) -> list[str]:
    reasons: list[str] = []
    command = section.get("command")
    if not isinstance(command, str) or not command.strip():
        reasons.append(f"functional section command invalid: {name}")
    environment = section.get("environment")
    if not isinstance(environment, dict) or not environment:
        reasons.append(f"functional section environment invalid: {name}")
    if section.get("head_sha") != revision:
        reasons.append(f"functional section head revision mismatch: {name}")
    outcomes = section.get("outcomes")
    if not isinstance(outcomes, dict) or not outcomes:
        reasons.append(f"functional section outcomes missing: {name}")
    elif outcomes.get("summary_present") is not True:
        reasons.append(f"functional section summary missing: {name}")
    checksum = section.get("output_sha256")
    if not isinstance(checksum, str) or not _SHA256.fullmatch(checksum):
        reasons.append(f"functional section output checksum invalid: {name}")
    return reasons


def _validate_state_section_metadata(name: str, section: dict[str, object], revision: str) -> list[str]:
    reasons: list[str] = []
    section_head = section.get("head_sha", "")
    if section_head and (not isinstance(section_head, str) or section_head != revision):
        reasons.append(f"section head revision mismatch: {name}")
    if section.get("environment") is not None and not isinstance(section.get("environment"), dict):
        reasons.append(f"invalid section environment: {name}")
    return reasons


def _validate_state_output_checksum(name: str, section: dict[str, object]) -> list[str]:
    checksum = section.get("output_sha256")
    if not isinstance(checksum, str) or not _SHA256.fullmatch(checksum):
        return [f"section output checksum invalid: {name}"]
    return []


def _validate_state_envelope(payload: dict[str, object], state: dict[str, object]) -> list[str]:
    required = (
        "bundle_kind", "schema_version", "artifact_id", "head_sha", "branch",
        "started_at", "finished_at", "command", "environment", "artifacts",
        "state_sha256", "output_sha256", "output", "verdict",
    )
    reasons: list[str] = [
        f"missing or invalid field: {field}" for field in required if field not in payload
    ]
    reasons.extend(_validate_state_identity(payload, state))
    reasons.extend(_validate_state_metadata(payload))
    return reasons


def _validate_state_identity(payload: dict[str, object], state: dict[str, object]) -> list[str]:
    reasons: list[str] = []
    if payload.get("bundle_kind") != "launch-safety-state-v1":
        reasons.append("unsupported bundle_kind")
    if payload.get("schema_version") != "1":
        reasons.append("unsupported schema_version")
    revision = state.get("revision")
    if not isinstance(revision, str) or not _HEAD_SHA.fullmatch(revision):
        reasons.append("state revision is invalid")
        revision = ""
    if payload.get("head_sha") != revision:
        reasons.append("bundle head_sha does not match state revision")
    if payload.get("artifact_id") != f"launch-safety-{revision}":
        reasons.append("bundle artifact_id does not match state revision")
    if payload.get("branch") != "release-gate":
        reasons.append("bundle branch is invalid")
    return reasons


def _validate_state_metadata(payload: dict[str, object]) -> list[str]:
    reasons: list[str] = []
    for field in ("started_at", "finished_at", "command"):
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            reasons.append(f"bundle {field} is invalid")
    environment = payload.get("environment")
    if not isinstance(environment, dict) or not environment:
        reasons.append("bundle environment is invalid")
    if not isinstance(payload.get("artifacts"), list):
        reasons.append("bundle artifacts are invalid")
    return reasons


def _validate_state_sections(payload: dict[str, object], state: dict[str, object], revision: str) -> list[str]:
    sections = state.get("sections")
    if not isinstance(sections, dict):
        return ["state sections must be an object"]
    reasons: list[str] = []
    missing = sorted(set(_REQUIRED_STATE_SECTIONS) - set(sections))
    if missing:
        reasons.append("state sections missing: " + ", ".join(missing))
    artifacts = payload.get("artifacts")
    if isinstance(artifacts, list) and artifacts != sorted(sections):
        reasons.append("bundle artifacts do not match state sections")
    for name, section in sections.items():
        reasons.extend(_validate_state_section(name, section, revision))
    return reasons


def _verify_state_bundle(payload: dict[str, object]) -> VerificationResult:
    state = payload.get("state")
    if not isinstance(state, dict):
        return VerificationResult("BLOCKED", ("state must be a JSON object",), "")
    reasons = _validate_state_envelope(payload, state)
    revision = state.get("revision")
    if not isinstance(revision, str) or not _HEAD_SHA.fullmatch(revision):
        revision = ""
    canonical = json.dumps(state, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    checked = sha256(canonical.encode()).hexdigest()
    if payload.get("state_sha256") != checked or payload.get("output_sha256") != checked:
        reasons.append("state checksum mismatch")
    if payload.get("output") != canonical:
        reasons.append("canonical bundle output mismatch")
    if payload.get("verdict") != "PASS":
        reasons.append("canonical bundle verdict is not PASS")
    if state.get("version") != 1:
        reasons.append("unsupported state version")
    if state.get("external_gates") != _DEFAULT_EXTERNAL_GATES:
        reasons.append("state external gates are invalid")
    reasons.extend(_validate_state_sections(payload, state, revision))
    if reasons:
        return VerificationResult("BLOCKED", tuple(reasons), checked)
    return VerificationResult("PASS", (), checked)
