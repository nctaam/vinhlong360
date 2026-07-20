#!/usr/bin/env python3
"""Append truthful local-only rollback phase evidence and summaries."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Mapping


STATUSES = {"passed", "failed", "skipped", "closed-verified"}
TRAFFIC_STATES = {"drained", "open", "unknown"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _validate_phase_inputs(
    *, phase: str, status: str, exit_code: int, traffic_state: str
) -> None:
    if not phase or any(character in phase for character in "\r\n\0"):
        raise ValueError("rollback phase must be a canonical non-empty string")
    if status not in STATUSES:
        raise ValueError("rollback phase status is invalid")
    if traffic_state not in TRAFFIC_STATES:
        raise ValueError("rollback traffic state is invalid")
    if type(exit_code) is not int or not 0 <= exit_code <= 255:
        raise ValueError("rollback exit code is invalid")


def _prepare_evidence_directory(evidence_dir: Path) -> Path:
    directory = Path(evidence_dir)
    directory.mkdir(parents=True, exist_ok=True)
    if directory.is_symlink():
        raise OSError("rollback evidence directory must not be a symlink")
    return directory


def _build_phase_record(
    *,
    phase: str,
    status: str,
    exit_code: int,
    traffic_state: str,
    fields: dict[str, Any],
) -> dict[str, Any]:
    observed_local_elapsed_seconds = fields.pop("observed_local_elapsed_seconds", 0.0)
    if observed_local_elapsed_seconds is None:
        observed_local_elapsed_seconds = 0.0
    record: dict[str, Any] = {
        "exit_code": exit_code,
        "live_sla_proven": False,
        "observed_at": _utc_now(),
        "observed_local_elapsed_seconds": observed_local_elapsed_seconds,
        "phase": phase,
        "schema_version": 1,
        "stage3_claim": False,
        "status": status,
        "traffic_state": traffic_state,
    }
    for key, value in fields.items():
        if key in {"stage3_claim", "live_sla_proven"}:
            continue
        if value is not None:
            record[key] = value
    return record


def _append_phase_record(directory: Path, record: Mapping[str, Any]) -> None:
    raw = (json.dumps(dict(record), ensure_ascii=True, sort_keys=True) + "\n").encode("utf-8")
    path = directory / "rollback-phases.jsonl"
    if path.is_symlink():
        raise OSError("rollback phase log must not be a symlink")
    descriptor = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
    try:
        os.write(descriptor, raw)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def append_phase(
    evidence_dir: Path,
    *,
    phase: str,
    status: str,
    exit_code: int = 0,
    traffic_state: str = "unknown",
    **fields: Any,
) -> dict[str, Any]:
    """Append one JSONL event. External launch claims are never caller-controlled."""
    _validate_phase_inputs(
        phase=phase,
        status=status,
        exit_code=exit_code,
        traffic_state=traffic_state,
    )
    directory = _prepare_evidence_directory(evidence_dir)
    record = _build_phase_record(
        phase=phase,
        status=status,
        exit_code=exit_code,
        traffic_state=traffic_state,
        fields=fields,
    )
    _append_phase_record(directory, record)
    return record


def write_summary(evidence_dir: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    summary = {
        **dict(payload),
        "schema_version": 1,
        "stage3_claim": False,
        "live_sla_proven": False,
    }
    directory = Path(evidence_dir)
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / "rollback-summary.json"
    if destination.is_symlink():
        raise OSError("rollback summary must not be a symlink")
    raw = (json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True) + "\n").encode("utf-8")
    descriptor, name = tempfile.mkstemp(prefix=".rollback-summary.", suffix=".tmp", dir=directory)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        if descriptor != -1:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)
    return summary


def read_traffic_state(path: Path) -> str:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("traffic classification evidence is invalid") from exc
    value = payload.get("traffic_state") if isinstance(payload, dict) else None
    if value not in TRAFFIC_STATES:
        raise ValueError("traffic classification state is invalid")
    return value


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", type=Path)
    parser.add_argument("--phase")
    parser.add_argument("--status")
    parser.add_argument("--exit-code", type=int, default=0)
    parser.add_argument("--traffic-state", choices=sorted(TRAFFIC_STATES), default="unknown")
    parser.add_argument("--operator")
    parser.add_argument("--candidate-id")
    parser.add_argument("--rollback-id")
    parser.add_argument("--recovery-action")
    parser.add_argument("--recovery-status")
    parser.add_argument("--closed-verified", choices=("true", "false"))
    parser.add_argument("--old-open-restored", choices=("true", "false"))
    parser.add_argument("--observed-local-elapsed-seconds", type=float)
    parser.add_argument("--read-traffic-state", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.read_traffic_state is not None:
            print(read_traffic_state(args.read_traffic_state))
            return 0
        if args.evidence_dir is None or args.phase is None or args.status is None:
            raise ValueError("evidence directory, phase, and status are required")
        record = append_phase(
            args.evidence_dir,
            phase=args.phase,
            status=args.status,
            exit_code=args.exit_code,
            traffic_state=args.traffic_state,
            operator=args.operator,
            candidate_id=args.candidate_id,
            rollback_id=args.rollback_id,
            recovery_action=args.recovery_action,
            recovery_status=args.recovery_status,
            closed_verified=(args.closed_verified == "true") if args.closed_verified else None,
            old_open_restored=(args.old_open_restored == "true") if args.old_open_restored else None,
            observed_local_elapsed_seconds=args.observed_local_elapsed_seconds,
        )
        if args.phase in {"recovery", "complete"}:
            write_summary(args.evidence_dir, record)
    except (OSError, ValueError) as exc:
        print(f"rollback evidence refused: {exc}", file=os.sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
