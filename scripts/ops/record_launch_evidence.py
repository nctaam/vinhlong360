#!/usr/bin/env python3
"""Record deterministic, bounded evidence for the Launch Safety release gate.

The recorder writes a small JSON state file outside the repository by default.
Only a final ``render`` produces the canonical Markdown result document.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Literal


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


def _redact(value: str) -> str:
    value = str(value)
    value = _URL_USERINFO.sub(r"\g<scheme>[redacted]@", value)
    value = _SECRET_QUERY.sub(r"\1[redacted]", value)
    value = _SECRET_ARG.sub(r"\g<prefix>[redacted]", value)
    value = _SECRET_ASSIGNMENT.sub(r"\1[redacted]", value)
    return _NEWLINES.sub(r"\\n", value)[:MAX_TEXT]


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

    def __post_init__(self) -> None:
        if self.status not in {"pass", "fail", "skip"}:
            raise ValueError(f"invalid evidence status: {self.status}")
        if not isinstance(self.exit_code, int):
            raise TypeError("exit_code must be an integer")
        if self.status in {"pass", "skip"} and self.exit_code != 0:
            raise ValueError(f"{self.status} evidence exit_code must be 0")
        object.__setattr__(self, "command", _redact(self.command))
        object.__setattr__(self, "summary", _redact(self.summary))

    @classmethod
    def from_mapping(cls, value: object) -> "CommandEvidence":
        if not isinstance(value, dict):
            raise ValueError("evidence entry must be an object")
        return cls(
            command=str(value.get("command", "")),
            exit_code=int(value.get("exit_code", 1)),
            summary=str(value.get("summary", "")),
            status=value.get("status", "fail"),  # type: ignore[arg-type]
        )


@dataclass(frozen=True)
class HarnessResult:
    exit_code: int
    primary_status: Literal["pass", "fail"]
    cleanup_status: Literal["pass", "fail"]


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

    def record(self, name: str, evidence: CommandEvidence) -> None:
        if name not in REQUIRED_SECTIONS:
            raise ValueError(f"unknown evidence section: {name}")
        if name == "external-gates" and self.external_gates != DEFAULT_EXTERNAL_GATES:
            raise ValueError("external gates do not match the approved blocked state")
        self.sections[name] = evidence

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": STATE_VERSION,
            "revision": self.revision,
            "external_gates": self.external_gates,
            "sections": {
                name: asdict(self.sections[name])
                for name in sorted(self.sections)
            },
        }
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, self.path)

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
        for name in FUNCTIONAL_SECTIONS:
            if self.sections[name].status != "pass":
                raise ValueError(f"functional section is not pass: {name}")
        failed = sorted(
            name for name, evidence in self.sections.items() if evidence.status == "fail"
        )
        if failed:
            raise ValueError("failed evidence section: " + ", ".join(failed))
        for name in OPT_IN_SECTIONS:
            evidence = self.sections[name]
            if evidence.status == "skip" and evidence.summary not in OPT_IN_SKIP_REASONS[name]:
                raise ValueError(
                    f"opt-in section has invalid skip reason: {name}/{evidence.summary}"
                )
        external = self.sections["external-gates"]
        if external.status != "skip" or external.summary != EXTERNAL_GATE_SUMMARY:
            raise ValueError("external gates must be exact informational evidence")

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
    document.record(name, evidence)
    document.save()


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
    record.add_argument("--state", type=Path, default=_default_state_path())

    harness = subparsers.add_parser("harness-result", help="record compose result")
    harness.add_argument("--section", required=True, choices=REQUIRED_SECTIONS)
    harness.add_argument("--primary-exit", type=int, required=True)
    harness.add_argument("--cleanup-exit", type=int, required=True)
    harness.add_argument("--state", type=Path, default=_default_state_path())

    render = subparsers.add_parser("render", help="render state as Markdown")
    render.add_argument("--state", type=Path, default=_default_state_path())
    render.add_argument("--output", type=Path)
    render.add_argument("--final", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.action == "record":
        record_section(
            args.section,
            CommandEvidence(args.command or args.section, args.exit_code, args.summary, args.status),
            args.state,
            revision=args.revision,
        )
        return 0
    if args.action == "harness-result":
        result = resolve_harness_result(
            primary_exit=args.primary_exit, cleanup_exit=args.cleanup_exit
        )
        status: Status = "pass" if result.exit_code == 0 else "fail"
        record_section(
            args.section,
            CommandEvidence(
                "docker compose harness",
                result.exit_code,
                f"primary_exit={args.primary_exit}; cleanup_exit={args.cleanup_exit}",
                status,
            ),
            args.state,
        )
        return result.exit_code
    document = EvidenceDocument.load(args.state)
    rendered = document.render(final=args.final)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as exc:
        print(f"evidence error: {exc}", file=os.sys.stderr)
        raise SystemExit(2)
