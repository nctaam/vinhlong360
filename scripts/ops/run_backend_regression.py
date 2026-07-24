"""Run the bounded backend regression suite in two ordered phases."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DEADLINE_SECONDS = 7000.0
TIMEOUT_EXIT_CODE = 124
CLEANUP_TIMEOUT_SECONDS = 5.0
MAX_DIAGNOSTIC_CHARS = 512
IS_WINDOWS = os.name == "nt"
CREATE_NEW_PROCESS_GROUP = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
SIGKILL = getattr(signal, "SIGKILL", 9)


@dataclass(frozen=True)
class Phase:
    name: str
    command: tuple[str, ...]


def build_phases(python: str) -> tuple[Phase, Phase]:
    """Build the two ordered pytest invocations for the backend suite."""
    return (
        Phase(
            "A",
            (
                python,
                "-m",
                "pytest",
                "-q",
                "--ignore=tests/launch_safety/test_closed_installer.py",
            ),
        ),
        Phase(
            "B",
            (
                python,
                "-m",
                "pytest",
                "-q",
                "tests/launch_safety/test_closed_installer.py",
                "-n",
                "2",
                "--dist=load",
                "--max-worker-restart=0",
            ),
        ),
    )


def _diagnose(message: str) -> None:
    line = f"[backend-regression] {message}"[:MAX_DIAGNOSTIC_CHARS]
    print(line, file=sys.stderr, flush=True)


def _start_phase(phase: Phase) -> subprocess.Popen:
    kwargs: dict[str, object] = {
        "cwd": ROOT,
        "stdout": None,
        "stderr": None,
    }
    if IS_WINDOWS:
        kwargs["creationflags"] = CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    # stdout/stderr are intentionally omitted so child output is inherited.
    return subprocess.Popen(phase.command, **kwargs)


def _cleanup_process(process: subprocess.Popen) -> None:
    """Terminate one still-live process tree with bounded waits."""
    if process.poll() is not None:
        return

    if IS_WINDOWS:
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            check=False,
            timeout=CLEANUP_TIMEOUT_SECONDS,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if process.poll() is None:
            process.wait(timeout=CLEANUP_TIMEOUT_SECONDS)
        return

    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=CLEANUP_TIMEOUT_SECONDS)
        return
    except subprocess.TimeoutExpired:
        if process.poll() is None:
            os.killpg(process.pid, SIGKILL)
            process.wait(timeout=CLEANUP_TIMEOUT_SECONDS)


def run_backend_regression(
    python: str = sys.executable,
    deadline_seconds: float = DEFAULT_DEADLINE_SECONDS,
) -> int:
    """Run both phases against one absolute monotonic deadline."""
    deadline = time.monotonic() + deadline_seconds

    for phase in build_phases(python):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            _diagnose(
                f"deadline exhausted before phase {phase.name}; deadline={deadline:.6f}"
            )
            return TIMEOUT_EXIT_CODE

        _diagnose(
            f"phase {phase.name} start; deadline={deadline:.6f}; "
            f"remaining={remaining:.3f}s"
        )
        process = _start_phase(phase)
        try:
            status = process.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            _diagnose(f"deadline exceeded during phase {phase.name}")
            try:
                _cleanup_process(process)
            except Exception as exc:  # cleanup is diagnostic-only on timeout
                _diagnose(
                    f"phase {phase.name} cleanup warning: "
                    f"{type(exc).__name__}: {exc}"
                )
            else:
                _diagnose(f"phase {phase.name} cleanup complete")
            return TIMEOUT_EXIT_CODE

        _diagnose(f"phase {phase.name} complete: exit {status}")
        if status != 0:
            return status

    return 0


def _positive_finite_seconds(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("deadline must be a finite positive number") from exc
    if not math.isfinite(parsed) or parsed <= 0:
        raise argparse.ArgumentTypeError("deadline must be a finite positive number")
    return parsed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--deadline-seconds",
        type=_positive_finite_seconds,
        default=DEFAULT_DEADLINE_SECONDS,
    )
    args = parser.parse_args(argv)
    return run_backend_regression(
        sys.executable, deadline_seconds=args.deadline_seconds
    )


if __name__ == "__main__":
    raise SystemExit(main())
