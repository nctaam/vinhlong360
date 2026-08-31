#!/usr/bin/env python3
"""Record deterministic, bounded evidence for the Launch Safety release gate.

The recorder writes a small JSON state file outside the repository by default.
Only a final ``render`` produces the canonical Markdown result document.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Any, Literal

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.control_plane.evidence import ParsedOutcome, classify_verdict, parse_pytest_output


Status = Literal["pass", "fail", "skip"]

REQUIRED_SECTIONS = (
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
FUNCTIONAL_SECTIONS = {
    "artifacts",
    "backend-focused",
    "frontend-focused",
    "rollback-local-rehearsal",
    "backend-full-regression",
    "frontend-serial-regression",
    "source-scans",
}
OPT_IN_SECTIONS = {"postgres-opt-in", "compose-nginx-opt-in", "browser-opt-in"}
OPT_IN_SKIP_REASONS = {
    "postgres-opt-in": {"docker-cli-unavailable", "docker-daemon-unavailable"},
    "compose-nginx-opt-in": {"docker-cli-unavailable", "docker-daemon-unavailable"},
    "browser-opt-in": {"chrome-unavailable"},
}
DEFAULT_EXTERNAL_GATES = {
    "H1": "blocked",
    "H2": "blocked",
    "owner": "not-authorized",
}
EXTERNAL_GATE_SUMMARY = "H1=blocked; H2=blocked; owner=not-authorized"
STATE_VERSION = 1
MAX_TEXT = 500
_NEWLINES = re.compile(r"\r\n?|\n")
_URL_USERINFO = re.compile(
    r"(?P<scheme>\b[a-z][a-z0-9+.-]*://)(?P<userinfo>[^/@\s]+)@",
    re.IGNORECASE,
)
_SECRET_QUERY = re.compile(
    r"([?&](?:password|passwd|secret|token|access[_-]?token|refresh[_-]?token|"
    r"auth|authorization|session|session_token|vl360_token|api[_-]?key|code)=)[^&#\s]+",
    re.IGNORECASE,
)
_SECRET_ARG = re.compile(
    r"(?P<prefix>(?<!\S)--(?:password|passwd|secret|token|access[-_]?token|"
    r"refresh[-_]?token|auth|authorization|api[-_]?key|client[-_]?secret|"
    r"database[-_]?(?:url|dsn))(?:=|\s+))"
    r"(?P<value>\"[^\"]*\"|'[^']*'|[^\s]+)",
    re.IGNORECASE,
)
_SECRET_ASSIGNMENT = re.compile(
    r"((?:password|passwd|secret|token|access[-_]?token|refresh[-_]?token|"
    r"authorization|api[-_]?key|client[-_]?secret)\s*[=:]\s*)[^\s,;]+",
    re.IGNORECASE,
)
_HEAD_SHA = re.compile(r"^[0-9a-f]{40}$")


def _validate_command_evidence(status: str, exit_code: int, command: str) -> None:
    if status not in {"pass", "fail", "skip"}:
        raise ValueError(f"invalid evidence status: {status}")
    if not isinstance(exit_code, int):
        raise TypeError("exit_code must be an integer")
    if len(str(command)) > MAX_TEXT:
        raise ValueError("command exceeds maximum evidence length")
    if status in {"pass", "skip"} and exit_code != 0:
        raise ValueError(f"{status} evidence exit_code must be 0")


def _validate_digests(head_sha: str, output_sha256: str) -> None:
    if head_sha and _HEAD_SHA.fullmatch(head_sha) is None:
        raise ValueError("head_sha must be a lowercase 40-hex revision")
    if output_sha256 and re.fullmatch(r"[0-9a-f]{64}", output_sha256) is None:
        raise ValueError("output_sha256 must be a lowercase SHA-256 digest")


def _resolved_verdict(status: str, verdict: str | None) -> str:
    expected = {"pass": "PASS", "fail": "BLOCKED", "skip": "UNCLASSIFIED"}[status]
    if verdict is not None and verdict != expected:
        raise ValueError("status and verdict contradict each other")
    return verdict or expected


def _redact(value: str) -> str:
    value = str(value)
    value = _URL_USERINFO.sub(r"\g<scheme>[redacted]@", value)
    value = _SECRET_QUERY.sub(r"\1[redacted]", value)
    value = _SECRET_ARG.sub(r"\g<prefix>[redacted]", value)
    value = _SECRET_ASSIGNMENT.sub(r"\1[redacted]", value)
    return _NEWLINES.sub(r"\\n", value)


def _markdown_escape(value: str) -> str:
    escaped: list[str] = []
    length = 0
    for character in _redact(value):
        fragment = "\\" + character if character in {"|", "`"} else character
        if length + len(fragment) > MAX_TEXT:
            break
        escaped.append(fragment)
        length += len(fragment)
    return "".join(escaped)


def _default_state_path() -> Path:
    configured = os.environ.get("LAUNCH_SAFETY_EVIDENCE_STATE")
    if configured:
        return Path(configured)
    return Path(tempfile.gettempdir()) / "vinhlong360-launch-safety-evidence.json"


@dataclass(frozen=True)
class CommandEvidence:
    command: str
    exit_code: int
    summary: str
    status: Status
    outcomes: dict[str, Any] | None = None
    environment: dict[str, Any] | None = None
    head_sha: str = ""
    output_sha256: str = ""
    verdict: str | None = None

    def __post_init__(self) -> None:
        _validate_command_evidence(self.status, self.exit_code, self.command)
        object.__setattr__(self, "command", _redact(self.command))
        object.__setattr__(self, "summary", _redact(self.summary))
        object.__setattr__(self, "outcomes", dict(self.outcomes or {}))
        object.__setattr__(self, "environment", dict(self.environment or {}))
        _validate_digests(self.head_sha, self.output_sha256)
        object.__setattr__(self, "verdict", _resolved_verdict(self.status, self.verdict))

    @classmethod
    def from_mapping(cls, value: object) -> "CommandEvidence":
        if not isinstance(value, dict):
            raise ValueError("evidence entry must be an object")
        return cls(
            command=str(value.get("command", "")),
            exit_code=int(value.get("exit_code", 1)),
            summary=str(value.get("summary", "")),
            status=value.get("status", "fail"),  # type: ignore[arg-type]
            outcomes=value.get("outcomes"),
            environment=value.get("environment"),
            head_sha=str(value.get("head_sha", "")),
            output_sha256=str(value.get("output_sha256", "")),
            verdict=value.get("verdict"),
        )


@dataclass(frozen=True)
class HarnessResult:
    exit_code: int
    primary_status: Literal["pass", "fail"]
    cleanup_status: Literal["pass", "fail"]


def _with_metadata(
    evidence: CommandEvidence,
    *,
    outcomes: dict[str, Any] | None,
    command: str | None,
    environment: dict[str, Any] | None,
    head_sha: str | None,
    output: str | bytes | None,
    output_sha256: str | None,
    verdict: str | None,
) -> CommandEvidence:
    if not any(value is not None for value in (outcomes, command, environment, head_sha, output, output_sha256, verdict)):
        return evidence
    digest = _output_digest(output, output_sha256)
    return CommandEvidence(
        command=evidence.command if command is None else command,
        exit_code=evidence.exit_code,
        summary=evidence.summary,
        status=evidence.status,
        outcomes=evidence.outcomes if outcomes is None else outcomes,
        environment=evidence.environment if environment is None else environment,
        head_sha=evidence.head_sha if head_sha is None else head_sha,
        output_sha256=evidence.output_sha256 if digest is None else digest,
        verdict=evidence.verdict if verdict is None else verdict,
    )


def _output_digest(output: str | bytes | None, declared: str | None) -> str | None:
    if output is None:
        return declared
    output_bytes = output.encode("utf-8") if isinstance(output, str) else output
    computed = sha256(output_bytes).hexdigest()
    if declared and declared != computed:
        raise ValueError("output_sha256 does not match output")
    return computed


def resolve_harness_result(*, primary_exit: int, cleanup_exit: int) -> HarnessResult:
    """Preserve the primary failure, otherwise surface cleanup failure."""

    primary = int(primary_exit)
    cleanup = int(cleanup_exit)
    return HarnessResult(
        exit_code=primary if primary != 0 else cleanup,
        primary_status="pass" if primary == 0 else "fail",
        cleanup_status="pass" if cleanup == 0 else "fail",
    )


class EvidenceDocument:
    """Versioned state plus validation/rendering for one gate run."""

    def __init__(
        self,
        path: Path,
        sections: dict[str, CommandEvidence] | None = None,
        external_gates: dict[str, str] | None = None,
        revision: str = "unknown",
    ) -> None:
        self.path = Path(path)
        self.sections = sections or {}
        selected_gates = DEFAULT_EXTERNAL_GATES if external_gates is None else external_gates
        self.external_gates = dict(selected_gates)
        self.revision = _redact(revision).strip()

    @classmethod
    def empty(cls, path: Path) -> "EvidenceDocument":
        return cls(Path(path))

    @classmethod
    def load(cls, path: Path) -> "EvidenceDocument":
        path = Path(path)
        if not path.exists():
            return cls.empty(path)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid evidence state: {path}") from exc
        if payload.get("version") != STATE_VERSION:
            raise ValueError("unsupported evidence state version")
        raw_sections = payload.get("sections", {})
        if not isinstance(raw_sections, dict):
            raise ValueError("evidence sections must be an object")
        sections = {
            name: CommandEvidence.from_mapping(entry)
            for name, entry in raw_sections.items()
        }
        external = payload.get("external_gates", DEFAULT_EXTERNAL_GATES)
        if not isinstance(external, dict):
            raise ValueError("external_gates must be an object")
        return cls(
            path,
            sections,
            {str(k): str(v) for k, v in external.items()},
            str(payload.get("revision", "unknown")),
        )

    def record(
        self,
        name: str,
        evidence: CommandEvidence,
        *,
        outcomes: dict[str, Any] | None = None,
        command: str | None = None,
        environment: dict[str, Any] | None = None,
        head_sha: str | None = None,
        output: str | bytes | None = None,
        output_sha256: str | None = None,
        verdict: str | None = None,
    ) -> None:
        if name not in REQUIRED_SECTIONS:
            raise ValueError(f"unknown evidence section: {name}")
        if name == "external-gates" and self.external_gates != DEFAULT_EXTERNAL_GATES:
            raise ValueError("external gates do not match the approved blocked state")
        evidence = _with_metadata(
            evidence, outcomes=outcomes, command=command, environment=environment,
            head_sha=head_sha, output=output, output_sha256=output_sha256, verdict=verdict,
        )
        self.sections[name] = evidence

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = self._state_payload()
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, self.path)

    def _state_payload(self) -> dict[str, Any]:
        return {
            "version": STATE_VERSION,
            "revision": self.revision,
            "external_gates": self.external_gates,
            "sections": {
                name: asdict(self.sections[name])
                for name in sorted(self.sections)
            },
        }

    def write_bundle(self, output_path: Path) -> None:
        self.validate_final()
        state = self._state_payload()
        canonical = json.dumps(state, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        now = datetime.now(timezone.utc).isoformat()
        digest = sha256(canonical.encode()).hexdigest()
        bundle = {
            "bundle_kind": "launch-safety-state-v1",
            "schema_version": "1",
            "artifact_id": f"launch-safety-{self.revision}",
            "head_sha": self.revision,
            "branch": "release-gate",
            "started_at": now,
            "finished_at": now,
            "command": "scripts/release_gate.ps1",
            "environment": {"recorder": "record_launch_evidence.py", "database_target": "redacted"},
            "allowlist": [], "verdict": "PASS", "artifacts": sorted(self.sections),
            "state": state, "output": canonical, "output_sha256": digest,
            "state_sha256": digest,
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(bundle, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _validate_opt_in_sections(self) -> None:
        for name in OPT_IN_SECTIONS:
            evidence = self.sections[name]
            if evidence.status == "skip" and evidence.summary not in OPT_IN_SKIP_REASONS[name]:
                raise ValueError(
                    f"opt-in section has invalid skip reason: {name}/{evidence.summary}"
                )
            if name == "compose-nginx-opt-in" and evidence.status == "pass":
                if (
                    not evidence.outcomes
                    or not evidence.environment
                    or not evidence.head_sha
                    or not evidence.output_sha256
                    or evidence.verdict != "PASS"
                ):
                    raise ValueError(
                        "compose-nginx-opt-in pass evidence requires capture metadata"
                    )

    def _validate_external_section(self) -> None:
        external = self.sections["external-gates"]
        if external.status != "skip" or external.summary != EXTERNAL_GATE_SUMMARY:
            raise ValueError("external gates must be exact informational evidence")

    def validate_final(self) -> None:
        missing = set(REQUIRED_SECTIONS) - set(self.sections)
        if missing:
            raise ValueError(
                "missing evidence sections: " + ", ".join(sorted(missing))
            )
        if not self.revision.strip() or self.revision.strip().lower() == "unknown":
            raise ValueError("final evidence revision is empty or unknown")
        if self.external_gates != DEFAULT_EXTERNAL_GATES:
            raise ValueError("external gates do not match the approved blocked state")
        _validate_functional_sections(self.sections)
        failed = sorted(
            name for name, evidence in self.sections.items() if evidence.status == "fail"
        )
        if failed:
            raise ValueError("failed evidence section: " + ", ".join(failed))
        self._validate_opt_in_sections()
        self._validate_external_section()

    def render(self, *, final: bool = False) -> str:
        if final:
            self.validate_final()
        status = "pass" if final else "in-progress"
        generated = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        lines = [
            "> STATUS: " + status,
            f"> Revision: {_markdown_escape(self.revision)}",
            f"> Generated: {generated} UTC",
            "> Scope: reproducible local gate evidence only; no live SLA claim.",
            "",
            "| Section | Command | Exit | Status | Summary |",
            "| --- | --- | ---: | --- | --- |",
        ]
        for name in REQUIRED_SECTIONS:
            evidence = self.sections.get(name)
            if evidence is None:
                lines.append(f"| `{name}` | — | — | missing | — |")
                continue
            lines.append(
                f"| `{name}` | `{_markdown_escape(evidence.command)}` | {evidence.exit_code} | "
                f"{evidence.status} | {_markdown_escape(evidence.summary)} |"
            )
        lines.extend(
            [
                "",
                "External gates: `H1=blocked`, `H2=blocked`, `owner=not-authorized`.",
                "",
            ]
        )
        return "\n".join(lines)


def record_section(
    name: str,
    evidence: CommandEvidence,
    evidence_path: Path | None = None,
    *,
    revision: str | None = None,
    outcomes: dict[str, Any] | None = None,
    command: str | None = None,
    environment: dict[str, Any] | None = None,
    head_sha: str | None = None,
    output: str | bytes | None = None,
    output_sha256: str | None = None,
    verdict: str | None = None,
) -> None:
    """Load, upsert, and persist a single evidence section."""

    document = EvidenceDocument.load(evidence_path or _default_state_path())
    if revision is not None:
        normalized_revision = _redact(revision).strip()
        if not normalized_revision or normalized_revision.lower() == "unknown":
            raise ValueError("evidence revision is empty or unknown")
        if document.revision.lower() != "unknown" and document.revision != normalized_revision:
            raise ValueError(
                f"evidence revision mismatch: {document.revision} != {normalized_revision}"
            )
        document.revision = normalized_revision
    document.record(
        name,
        evidence,
        outcomes=outcomes,
        command=command,
        environment=environment,
        head_sha=head_sha,
        output=output,
        output_sha256=output_sha256,
        verdict=verdict,
    )
    document.save()


def _validate_functional_sections(sections: dict[str, CommandEvidence]) -> None:
    for name in FUNCTIONAL_SECTIONS:
        evidence = sections[name]
        if evidence.status != "pass" or evidence.verdict != "PASS":
            raise ValueError(f"functional section is not pass: {name}")
        outcomes = evidence.outcomes
        if not outcomes:
            continue
        if _outcomes_verdict(outcomes) != "PASS":
            raise ValueError(f"functional section verdict is blocked: {name}")
        if not evidence.output_sha256:
            raise ValueError(f"functional section is missing output checksum: {name}")


def _outcomes_verdict(outcomes: dict[str, Any]) -> str:
    try:
        outcome = ParsedOutcome(
            passed=outcomes["passed"], failed=outcomes["failed"],
            errors=outcomes["errors"], skipped=outcomes["skipped"],
            xfailed=outcomes["xfailed"], collection_errors=outcomes["collection_errors"],
            interrupted=outcomes["interrupted"], return_code=outcomes["return_code"],
            failed_nodeids=tuple(outcomes.get("failed_nodeids", ())),
            error_nodeids=tuple(outcomes.get("error_nodeids", ())), summary_present=True,
        )
    except (KeyError, TypeError, ValueError):
        return "BLOCKED"
    return classify_verdict(outcome, frozenset())


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)

    record = subparsers.add_parser("record", help="upsert one section")
    record.add_argument("--section", required=True, choices=REQUIRED_SECTIONS)
    record.add_argument("--status", required=True, choices=("pass", "fail", "skip"))
    record.add_argument("--exit-code", type=int, required=True)
    record.add_argument("--summary", required=True)
    record.add_argument("--command", default="")
    record.add_argument("--revision")
    record.add_argument("--head-sha", default="")
    record.add_argument("--outcomes-json", default="")
    record.add_argument("--environment-json", default="")
    output = record.add_mutually_exclusive_group()
    output.add_argument("--output-text", default=None)
    output.add_argument("--output-file", type=Path)
    record.add_argument("--output-sha256", default="")
    record.add_argument("--verdict", choices=("PASS", "BLOCKED", "UNCLASSIFIED"))
    record.add_argument("--state", type=Path, default=_default_state_path())

    harness = subparsers.add_parser("harness-result", help="record compose result")
    harness.add_argument("--section", required=True, choices=REQUIRED_SECTIONS)
    harness.add_argument("--primary-exit", type=int, required=True)
    harness.add_argument("--cleanup-exit", type=int, required=True)
    harness.add_argument("--command", default="docker compose harness")
    harness.add_argument("--head-sha", default="")
    harness.add_argument("--environment-json", default="")
    output = harness.add_mutually_exclusive_group()
    output.add_argument("--output-text", default=None)
    output.add_argument("--output-file", type=Path)
    harness.add_argument("--state", type=Path, default=_default_state_path())

    render = subparsers.add_parser("render", help="render state as Markdown")
    render.add_argument("--state", type=Path, default=_default_state_path())
    render.add_argument("--output", type=Path)
    render.add_argument("--final", action="store_true")
    bundle = subparsers.add_parser("bundle", help="write canonical verification bundle")
    bundle.add_argument("--state", type=Path, default=_default_state_path())
    bundle.add_argument("--output", type=Path, required=True)
    return parser


def _metadata_from_args(args: argparse.Namespace) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    try:
        outcomes = json.loads(args.outcomes_json) if args.outcomes_json else None
        environment = json.loads(args.environment_json) if args.environment_json else None
    except json.JSONDecodeError as exc:
        raise ValueError(f"metadata must be valid JSON: {exc}") from exc
    if outcomes is not None and not isinstance(outcomes, dict):
        raise ValueError("outcomes metadata must be an object")
    if environment is not None and not isinstance(environment, dict):
        raise ValueError("environment metadata must be an object")
    return outcomes, environment


def _record_payload(args: argparse.Namespace, outcomes: dict[str, Any] | None) -> tuple[dict[str, Any] | None, str | bytes | None, str, str | None]:
    effective_status = args.status
    effective_verdict = args.verdict
    output: str | bytes | None = args.output_text
    if args.output_file is not None:
        try:
            output = args.output_file.read_bytes()
        except OSError as exc:
            raise ValueError(f"unable to read output file: {exc}") from exc
    output_text: str | None
    if isinstance(output, bytes):
        try:
            output_text = output.decode("utf-8")
        except UnicodeDecodeError:
            output_text = None
    else:
        output_text = output
    if outcomes is None and output is not None:
        if output_text is None:
            parsed = None
        else:
            parsed = parse_pytest_output(output_text, args.exit_code)
        if parsed is not None and parsed.summary_present:
            outcomes = asdict(parsed)
            effective_verdict = classify_verdict(parsed, frozenset())
            effective_status = {"PASS": "pass", "BLOCKED": "fail", "UNCLASSIFIED": "skip"}[effective_verdict]
        elif parsed is None or not parsed.summary_present:
            # A captured command without a parseable pytest summary is not a
            # passing test run; preserve the output and classify it explicitly.
            effective_verdict = "UNCLASSIFIED"
            effective_status = "skip"
    return outcomes, output, effective_status, effective_verdict


def _handle_record(args: argparse.Namespace) -> int:
    outcomes, environment = _metadata_from_args(args)
    outcomes, output, effective_status, effective_verdict = _record_payload(args, outcomes)
    record_section(
        args.section,
        CommandEvidence(args.command or args.section, args.exit_code, args.summary, effective_status),
        args.state,
        revision=args.revision,
        outcomes=outcomes,
        environment=environment,
        head_sha=args.head_sha or None,
        output=output,
        output_sha256=args.output_sha256 or None,
        verdict=effective_verdict,
    )
    return 0


def _handle_harness(args: argparse.Namespace) -> int:
        result = resolve_harness_result(
            primary_exit=args.primary_exit, cleanup_exit=args.cleanup_exit
        )
        output: bytes
        if args.output_file is not None:
            try:
                output = args.output_file.read_bytes()
            except OSError as exc:
                raise ValueError(f"unable to read output file: {exc}") from exc
        elif args.output_text is not None:
            output = args.output_text.encode("utf-8")
        else:
            output = b""
        from agent.control_plane.evidence import parse_pytest_output

        try:
            parsed = parse_pytest_output(output.decode("utf-8"), result.exit_code)
        except UnicodeDecodeError as exc:
            raise ValueError("captured harness output is not valid UTF-8") from exc
        _outcomes = asdict(parsed) if parsed.summary_present else None
        effective_verdict = classify_verdict(parsed, frozenset())
        status: Status = {
            "PASS": "pass", "BLOCKED": "fail", "UNCLASSIFIED": "skip",
        }[effective_verdict]
        _environment = {"database_target": "redacted"}
        if args.environment_json:
            try:
                _environment = json.loads(args.environment_json)
            except json.JSONDecodeError as exc:
                raise ValueError(f"metadata must be valid JSON: {exc}") from exc
            if not isinstance(_environment, dict):
                raise ValueError("environment metadata must be an object")
        record_section(
            args.section,
            CommandEvidence(
                args.command,
                result.exit_code,
                f"primary_exit={args.primary_exit}; cleanup_exit={args.cleanup_exit}",
                status,
            ),
            args.state,
            outcomes=_outcomes,
            environment=_environment,
            head_sha=args.head_sha or None,
            output=output,
            verdict=effective_verdict,
        )
        return result.exit_code


def _handle_render_or_bundle(args: argparse.Namespace) -> int:
    document = EvidenceDocument.load(args.state)
    if args.action == "bundle":
        document.write_bundle(args.output)
        return 0
    rendered = document.render(final=args.final)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.action == "record":
        return _handle_record(args)
    if args.action == "harness-result":
        return _handle_harness(args)
    return _handle_render_or_bundle(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as exc:
        print(f"evidence error: {exc}", file=os.sys.stderr)
        raise SystemExit(2)
