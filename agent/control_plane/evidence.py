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
        if nodeid not in allowed
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
    output = payload.get("output")
    if output is None:
        output = payload.get("output_text")
    if output is None and isinstance(payload.get("output_path"), str):
        raw_output_path = payload["output_path"]
        try:
            if Path(raw_output_path).is_absolute():
                reasons.append("output_path must be relative")
                return None, ""
            bundle_dir = Path(path).parent.resolve()
            output_path = (bundle_dir / raw_output_path).resolve()
            try:
                output_path.relative_to(bundle_dir)
            except ValueError:
                reasons.append("output_path escapes bundle directory")
                return None, ""
            output = output_path.read_bytes()
        except ValueError:
            reasons.append("invalid output_path")
            return None, ""
        except (OSError, RuntimeError) as exc:
            reasons.append(f"unable to read output: {type(exc).__name__}")
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
    parsed = parse_pytest_output(text, outcome.return_code)
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


def _validate_state_outcomes(name: str, outcomes: object, verdict: object) -> list[str]:
    if not isinstance(outcomes, dict):
        return [f"invalid section outcomes: {name}"]
    fields = ("passed", "failed", "errors", "skipped", "xfailed", "collection_errors", "interrupted", "return_code")
    if any(field not in outcomes for field in fields):
        return [f"incomplete section outcomes: {name}"]
    try:
        counts = {field: outcomes[field] for field in fields}
        if any(type(counts[field]) is not int for field in fields if field != "interrupted"):
            raise ValueError("outcome counts have invalid types")
        if type(counts["interrupted"]) is not bool:
            raise ValueError("interrupted must be boolean")
        if any(counts[field] < 0 for field in fields if field != "interrupted"):
            raise ValueError("outcome counts cannot be negative")
        parsed = ParsedOutcome(
            **counts,
            failed_nodeids=_validated_nodeids(outcomes.get("failed_nodeids", ()), "failed_nodeids"),
            error_nodeids=_validated_nodeids(outcomes.get("error_nodeids", ()), "error_nodeids"),
            summary_present=True,
        )
    except (KeyError, TypeError, ValueError) as exc:
        return [f"invalid section outcomes: {name}: {exc}"]
    if classify_verdict(parsed, frozenset()) != verdict:
        return [f"section outcomes/verdict mismatch: {name}"]
    return []


def _validate_state_section(name: str, section: object, revision: str) -> list[str]:
    if not isinstance(section, dict):
        return [f"invalid section: {name}"]
    reasons: list[str] = []
    status = section.get("status")
    verdict = section.get("verdict")
    if status not in {"pass", "fail", "skip"}:
        reasons.append(f"invalid section status: {name}")
    if verdict not in {"PASS", "BLOCKED", "UNCLASSIFIED"}:
        reasons.append(f"invalid section verdict: {name}")
    expected = {"pass": "PASS", "fail": "BLOCKED", "skip": "UNCLASSIFIED"}.get(status)
    if expected is not None and verdict != expected:
        reasons.append(f"section status/verdict mismatch: {name}")
    reasons.extend(_validate_state_section_metadata(name, section, revision))
    outcomes = section.get("outcomes")
    if outcomes is not None and outcomes != {}:
        reasons.extend(_validate_state_outcomes(name, outcomes, verdict))
        reasons.extend(_validate_state_output_checksum(name, section))
    if status == "fail" or verdict == "BLOCKED":
        reasons.append(f"blocked section: {name}")
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
