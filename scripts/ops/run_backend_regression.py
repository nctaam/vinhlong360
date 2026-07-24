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
CLEANUP_POLL_INTERVAL_SECONDS = 0.05
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
    # Explicit None preserves the parent's stdout/stderr streams.
    return subprocess.Popen(phase.command, **kwargs)


def _wait_for_owned_process(process: subprocess.Popen) -> bool:
    try:
        process.wait(timeout=CLEANUP_TIMEOUT_SECONDS)
        return True
    except subprocess.TimeoutExpired:
        return False


def _cleanup_windows_process(process: subprocess.Popen) -> None:
    errors: list[str] = []
    taskkill_succeeded = False
    try:
        completed = subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            check=False,
            timeout=CLEANUP_TIMEOUT_SECONDS,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as exc:
        errors.append(f"taskkill failed: {type(exc).__name__}: {exc}")
    else:
        if completed.returncode == 0:
            taskkill_succeeded = True
        else:
            errors.append(f"taskkill exited {completed.returncode}")

    needs_handle_fallback = not taskkill_succeeded
    if taskkill_succeeded and process.poll() is None:
        needs_handle_fallback = not _wait_for_owned_process(process)

    if needs_handle_fallback and process.poll() is None:
        try:
            process.kill()
        except Exception as exc:
            errors.append(f"owned-handle kill failed: {type(exc).__name__}: {exc}")
        else:
            try:
                if not _wait_for_owned_process(process):
                    errors.append("owned-handle wait timed out")
            except Exception as exc:
                errors.append(
                    f"owned-handle wait failed: {type(exc).__name__}: {exc}"
                )

    if errors:
        raise RuntimeError("; ".join(errors))


def _process_group_exists(process_group_id: int) -> bool:
    try:
        os.killpg(process_group_id, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _wait_for_process_group_exit(
    process: subprocess.Popen, process_group_id: int
) -> bool:
    deadline = time.monotonic() + CLEANUP_TIMEOUT_SECONDS
    while True:
        process.poll()
        if not _process_group_exists(process_group_id):
            return True
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False
        time.sleep(min(CLEANUP_POLL_INTERVAL_SECONDS, remaining))


def _cleanup_posix_process(process: subprocess.Popen) -> None:
    process_group_id = process.pid
    if not _process_group_exists(process_group_id):
        return

    try:
        os.killpg(process_group_id, signal.SIGTERM)
    except ProcessLookupError:
        return

    if not _wait_for_process_group_exit(process, process_group_id):
        if _process_group_exists(process_group_id):
            try:
                os.killpg(process_group_id, SIGKILL)
            except ProcessLookupError:
                pass
            else:
                if not _wait_for_process_group_exit(process, process_group_id):
                    raise RuntimeError("owned process group survived SIGKILL grace")

    if process.poll() is None and not _wait_for_owned_process(process):
        raise RuntimeError("owned process leader did not exit after group cleanup")


def _cleanup_process(process: subprocess.Popen) -> None:
    """Terminate one owned process tree with bounded waits."""
    if IS_WINDOWS:
        if process.poll() is None:
            _cleanup_windows_process(process)
        return
    _cleanup_posix_process(process)


def _deadline_timeout(phase: Phase, process: subprocess.Popen, context: str) -> int:
    _diagnose(f"deadline exceeded during phase {phase.name}{context}")
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
            f"phase {phase.name} start ({'serial suite' if phase.name == 'A' else 'closed-installer xdist suite'}); "
            f"deadline={deadline:.6f}; "
            f"remaining={remaining:.3f}s"
        )
        process = _start_phase(phase)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return _deadline_timeout(phase, process, " startup")
        try:
            status = process.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            return _deadline_timeout(phase, process, "")

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
