# Bounded Backend Regression Implementation Plan

> STATUS: implementation and verification complete - approved design is `docs/superpowers/specs/2026-07-24-bounded-backend-regression-design.md`; no deploy, production mutation, secret change, or live indexing authorization.

> **Completion truth:** Candidate `c1875b37f643ac6ca06a4db25ccce4902b04d717` passed the official matrix and the single `backend-full-regression` evidence row with exit `0`; Phase A was serial and excluded `tests/launch_safety/test_closed_installer.py`, while Phase B ran only that module with `-n 2 --dist=load --max-worker-restart=0`. Serial/xdist equivalence is authoritative at `a79b094` only: 303/303 node IDs and JUnit cases matched, outcomes were identical, and each run recorded 284 passed/19 skipped. From `a79b094` to `c1875b3` only the two route-guard files changed. Evidence B is `580b9b8`; final section truth is in `docs/superpowers/results/2026-07-20-launch-safety-gate-evidence.md`. The exact approved known-resource skip and blocked external gates remain unchanged; global `noindex` remains active and no push, merge, deploy, production mutation, secret change, or indexing authorization occurred.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the unbounded monolithic backend regression with a bounded two-phase runner that keeps non-installer tests serial, runs only the isolated closed-installer module with two xdist workers, and preserves one fail-closed `backend-full-regression` evidence section.

**Architecture:** A standard-library Python runner owns one 7,000-second monotonic deadline and the child-process tree. Phase A runs the full pytest suite excluding `test_closed_installer.py`; Phase B runs only that module with fixed `-n 2 --dist=load --max-worker-restart=0`. PowerShell continues to record the runner as one functional evidence section, while contracts enforce dependency, CI, timeout, cleanup, and serial-authority rules.

**Tech Stack:** Python 3.10+, pytest 8, pytest-xdist 3.x, PowerShell, GitHub Actions, Markdown authority documents.

---

## Locked file structure

- Create `scripts/ops/run_backend_regression.py`: fixed phase construction, shared deadline, subprocess execution, bounded process-tree cleanup, and CLI.
- Create `tests/launch_safety/test_backend_regression_runner.py`: direct contracts for phase commands, deadline reuse, fail-fast behavior, timeout `124`, output inheritance, and Windows/POSIX cleanup.
- Modify `scripts/release_gate.ps1`: call the runner inside the existing `backend-full-regression` evidence section and include its contracts in `backend-focused`.
- Modify `tests/launch_safety/test_launch_matrix_contract.py`: require runner/CI wiring and reject the old direct full-suite invocation.
- Modify `tests/launch_safety/powershell/test_release_gate_harness.ps1`: simulate runner timeout `124`, assert exact evidence, and prove later required sections still run.
- Modify `requirements-dev.txt` and `.github/workflows/ci.yml`: install `pytest-xdist>=3.6,<4` only in test/tooling environments and execute the new contracts.
- Modify `tests/launch_safety/test_closed_installer.py` only when a focused RED run proves an undrained-pipe deadlock in a background installer fixture; use per-case file-backed output without changing production installer behavior or test assertions.
- Modify the approved launch plans/specs only where their serial-matrix wording or command is superseded by this narrow two-worker exception.

## Task 1: Implement the bounded backend runner with TDD

**Files:**
- Create: `tests/launch_safety/test_backend_regression_runner.py`
- Create: `scripts/ops/run_backend_regression.py`

- [ ] **Step 1: Write RED runner contracts**

Create `tests/launch_safety/test_backend_regression_runner.py` with these contracts and fakes:

```python
from __future__ import annotations

import importlib.util
import signal
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest


ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "scripts" / "ops" / "run_backend_regression.py"
INSTALLER_TEST = "tests/launch_safety/test_closed_installer.py"


def _load_runner() -> ModuleType:
    spec = importlib.util.spec_from_file_location("run_backend_regression", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FakeProcess:
    def __init__(self, *wait_effects: object, pid: int = 4242) -> None:
        self.pid = pid
        self.wait_effects = list(wait_effects)
        self.wait_timeouts: list[float] = []
        self.returncode: int | None = None
        self.kill_calls = 0

    def poll(self) -> int | None:
        return self.returncode

    def wait(self, timeout: float | None = None) -> int:
        assert timeout is not None
        self.wait_timeouts.append(timeout)
        effect = self.wait_effects.pop(0) if self.wait_effects else 0
        if isinstance(effect, BaseException):
            raise effect
        self.returncode = int(effect)
        return self.returncode

    def kill(self) -> None:
        self.kill_calls += 1
        self.returncode = -9


def test_build_phases_keeps_only_the_installer_module_parallel() -> None:
    runner = _load_runner()

    phases = runner.build_phases("python")

    assert phases == (
        runner.Phase(
            "backend-serial",
            (
                "python", "-m", "pytest", "-q",
                f"--ignore={INSTALLER_TEST}",
            ),
        ),
        runner.Phase(
            "closed-installer-xdist",
            (
                "python", "-m", "pytest", "-q", INSTALLER_TEST,
                "-n", "2", "--dist=load", "--max-worker-restart=0",
            ),
        ),
    )


def test_run_backend_regression_reuses_one_absolute_deadline() -> None:
    runner = _load_runner()
    observed: list[tuple[str, float]] = []

    def fake_run_phase(phase, **kwargs) -> int:
        observed.append((phase.name, kwargs["deadline"]))
        return 0

    result = runner.run_backend_regression(
        python="python",
        deadline_seconds=7000,
        root=ROOT,
        clock=lambda: 100.0,
        run_phase_fn=fake_run_phase,
    )

    assert result == 0
    assert observed == [
        ("backend-serial", 7100.0),
        ("closed-installer-xdist", 7100.0),
    ]


def test_shared_deadline_reduces_the_second_phase_wait_budget() -> None:
    runner = _load_runner()
    first = FakeProcess(0)
    second = FakeProcess(0)
    processes = iter((first, second))
    clock_values = iter((100.0, 100.0, 104.0))

    def clock() -> float:
        return next(clock_values)

    def real_phase_with_fake_process(phase, **kwargs) -> int:
        return runner.run_phase(
            phase,
            popen_factory=lambda *_args, **_kwargs: next(processes),
            **kwargs,
        )

    result = runner.run_backend_regression(
        python="python",
        deadline_seconds=10,
        root=ROOT,
        clock=clock,
        run_phase_fn=real_phase_with_fake_process,
    )

    assert result == 0
    assert first.wait_timeouts == [10.0]
    assert second.wait_timeouts == [6.0]


def test_phase_a_failure_stops_before_xdist() -> None:
    runner = _load_runner()
    observed: list[str] = []

    def fake_run_phase(phase, **_kwargs) -> int:
        observed.append(phase.name)
        return 17

    result = runner.run_backend_regression(
        python="python",
        deadline_seconds=7000,
        root=ROOT,
        clock=lambda: 10.0,
        run_phase_fn=fake_run_phase,
    )

    assert result == 17
    assert observed == ["backend-serial"]


def test_run_phase_timeout_cleans_the_owned_tree_and_returns_124() -> None:
    runner = _load_runner()
    process = FakeProcess(subprocess.TimeoutExpired(["python"], 5))
    popen_calls: list[tuple[tuple[str, ...], dict[str, object]]] = []
    cleaned: list[int] = []

    def fake_popen(command, **kwargs):
        popen_calls.append((tuple(command), kwargs))
        return process

    def fake_cleanup(owned_process, **_kwargs):
        cleaned.append(owned_process.pid)
        return ()

    result = runner.run_phase(
        runner.Phase("phase", ("python", "-V")),
        root=ROOT,
        deadline=105.0,
        clock=lambda: 100.0,
        popen_factory=fake_popen,
        terminate_tree=fake_cleanup,
        platform_name="nt",
    )

    assert result == 124
    assert cleaned == [4242]
    assert process.wait_timeouts == [5.0]
    assert popen_calls[0][0] == ("python", "-V")
    assert popen_calls[0][1]["cwd"] == ROOT
    assert "stdout" not in popen_calls[0][1]
    assert "stderr" not in popen_calls[0][1]


def test_timeout_remains_124_when_cleanup_raises(capsys) -> None:
    runner = _load_runner()
    process = FakeProcess(subprocess.TimeoutExpired(["python"], 5))

    def exploding_cleanup(*_args, **_kwargs):
        raise OSError("cleanup failed")

    result = runner.run_phase(
        runner.Phase("phase", ("python", "-V")),
        root=ROOT,
        deadline=105.0,
        clock=lambda: 100.0,
        popen_factory=lambda *_args, **_kwargs: process,
        terminate_tree=exploding_cleanup,
    )

    assert result == 124
    assert "cleanup warning: OSError" in capsys.readouterr().err


def test_run_phase_returns_124_without_spawning_after_deadline() -> None:
    runner = _load_runner()

    def forbidden_popen(*_args, **_kwargs):
        raise AssertionError("expired phase must not spawn")

    result = runner.run_phase(
        runner.Phase("phase", ("python", "-V")),
        root=ROOT,
        deadline=100.0,
        clock=lambda: 100.0,
        popen_factory=forbidden_popen,
    )

    assert result == 124


def test_run_phase_preserves_a_native_nonzero_exit() -> None:
    runner = _load_runner()
    process = FakeProcess(23)

    result = runner.run_phase(
        runner.Phase("phase", ("python", "-V")),
        root=ROOT,
        deadline=110.0,
        clock=lambda: 100.0,
        popen_factory=lambda *_args, **_kwargs: process,
    )

    assert result == 23


def test_windows_cleanup_targets_only_the_live_owned_process_tree() -> None:
    runner = _load_runner()
    process = FakeProcess(0, pid=31337)
    calls: list[tuple[list[str], dict[str, object]]] = []

    def fake_run(command, **kwargs):
        calls.append((list(command), kwargs))
        return subprocess.CompletedProcess(command, 0)

    errors = runner.terminate_process_tree(
        process,
        platform_name="nt",
        run_command=fake_run,
        taskkill_path="taskkill.exe",
        cleanup_timeout=3.0,
    )

    assert errors == ()
    assert calls == [(
        ["taskkill.exe", "/PID", "31337", "/T", "/F"],
        {"check": False, "timeout": 3.0},
    )]
    assert process.wait_timeouts == [3.0]


def test_cleanup_never_uses_a_pid_after_the_owned_process_exits() -> None:
    runner = _load_runner()
    process = FakeProcess(pid=31337)
    process.returncode = 0

    def forbidden_run(*_args, **_kwargs):
        raise AssertionError("exited process must not be targeted")

    assert runner.terminate_process_tree(
        process,
        platform_name="nt",
        run_command=forbidden_run,
    ) == ()


def test_posix_cleanup_escalates_from_term_to_kill() -> None:
    runner = _load_runner()
    process = FakeProcess(
        subprocess.TimeoutExpired(["python"], 2),
        0,
        pid=8080,
    )
    signals: list[tuple[int, int]] = []

    errors = runner.terminate_process_tree(
        process,
        platform_name="posix",
        kill_group=lambda pid, sig: signals.append((pid, sig)),
        cleanup_timeout=2.0,
    )

    assert errors == ()
    assert signals == [(8080, signal.SIGTERM), (8080, signal.SIGKILL)]
```

- [ ] **Step 2: Run the runner contracts and verify RED**

Run:

```powershell
python -m pytest tests/launch_safety/test_backend_regression_runner.py -q
```

Expected: FAIL while importing `scripts/ops/run_backend_regression.py` because the runner does not exist. The failure must be about the missing implementation, not a syntax error in the test.

- [ ] **Step 3: Implement the minimal runner**

Create `scripts/ops/run_backend_regression.py` with this interface and behavior:

```python
from __future__ import annotations

import argparse
import math
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence


ROOT = Path(__file__).resolve().parents[2]
INSTALLER_TEST = "tests/launch_safety/test_closed_installer.py"
DEFAULT_DEADLINE_SECONDS = 7000.0
TIMEOUT_EXIT_CODE = 124
DEFAULT_CLEANUP_TIMEOUT = 15.0


@dataclass(frozen=True)
class Phase:
    name: str
    command: tuple[str, ...]


def build_phases(python: str) -> tuple[Phase, Phase]:
    base = (python, "-m", "pytest", "-q")
    return (
        Phase("backend-serial", base + (f"--ignore={INSTALLER_TEST}",)),
        Phase(
            "closed-installer-xdist",
            base + (
                INSTALLER_TEST,
                "-n", "2",
                "--dist=load",
                "--max-worker-restart=0",
            ),
        ),
    )


def _taskkill_path() -> str:
    system_root = os.environ.get("SystemRoot")
    if system_root:
        return str(Path(system_root) / "System32" / "taskkill.exe")
    return "taskkill.exe"


def terminate_process_tree(
    process,
    *,
    platform_name: str = os.name,
    run_command: Callable[..., subprocess.CompletedProcess] = subprocess.run,
    kill_group: Callable[[int, int], None] | None = None,
    taskkill_path: str | None = None,
    cleanup_timeout: float = DEFAULT_CLEANUP_TIMEOUT,
) -> tuple[str, ...]:
    if process.poll() is not None:
        return ()

    errors: list[str] = []
    if platform_name == "nt":
        try:
            run_command(
                [taskkill_path or _taskkill_path(), "/PID", str(process.pid), "/T", "/F"],
                check=False,
                timeout=cleanup_timeout,
            )
        except (OSError, subprocess.SubprocessError) as error:
            errors.append(f"taskkill: {error}")
        try:
            process.wait(timeout=cleanup_timeout)
        except subprocess.TimeoutExpired:
            try:
                process.kill()
                process.wait(timeout=cleanup_timeout)
            except (OSError, subprocess.SubprocessError) as error:
                errors.append(f"root-kill: {error}")
        return tuple(errors)

    group_killer = kill_group or os.killpg
    try:
        group_killer(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return ()
    except OSError as error:
        errors.append(f"sigterm: {error}")
    try:
        process.wait(timeout=cleanup_timeout)
    except subprocess.TimeoutExpired:
        try:
            group_killer(process.pid, signal.SIGKILL)
            process.wait(timeout=cleanup_timeout)
        except (OSError, subprocess.SubprocessError) as error:
            errors.append(f"sigkill: {error}")
    return tuple(errors)


def run_phase(
    phase: Phase,
    *,
    root: Path,
    deadline: float,
    clock: Callable[[], float] = time.monotonic,
    popen_factory: Callable[..., object] = subprocess.Popen,
    terminate_tree: Callable[..., tuple[str, ...]] = terminate_process_tree,
    platform_name: str = os.name,
) -> int:
    remaining = deadline - clock()
    if remaining <= 0:
        print(f"[backend-regression] {phase.name}: deadline exhausted before start", file=sys.stderr)
        return TIMEOUT_EXIT_CODE

    options: dict[str, object] = {"cwd": root}
    if platform_name == "nt":
        options["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        options["start_new_session"] = True

    print(f"[backend-regression] {phase.name}: start")
    process = popen_factory(list(phase.command), **options)
    try:
        exit_code = int(process.wait(timeout=remaining))
    except subprocess.TimeoutExpired:
        try:
            cleanup_errors = terminate_tree(process, platform_name=platform_name)
        except Exception as error:
            cleanup_errors = ()
            print(
                f"[backend-regression] {phase.name}: cleanup warning: {type(error).__name__}",
                file=sys.stderr,
            )
        for error in cleanup_errors:
            print(f"[backend-regression] {phase.name}: cleanup warning: {error}", file=sys.stderr)
        print(f"[backend-regression] {phase.name}: deadline exceeded", file=sys.stderr)
        return TIMEOUT_EXIT_CODE

    print(f"[backend-regression] {phase.name}: exit {exit_code}")
    return exit_code


def run_backend_regression(
    *,
    python: str,
    deadline_seconds: float,
    root: Path = ROOT,
    clock: Callable[[], float] = time.monotonic,
    run_phase_fn: Callable[..., int] = run_phase,
) -> int:
    deadline = clock() + deadline_seconds
    for phase in build_phases(python):
        exit_code = run_phase_fn(phase, root=root, deadline=deadline, clock=clock)
        if exit_code != 0:
            return exit_code
    return 0


def _positive_seconds(raw: str) -> float:
    value = float(raw)
    if not math.isfinite(value) or value <= 0:
        raise argparse.ArgumentTypeError("deadline must be a positive finite number")
    return value


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--deadline-seconds",
        type=_positive_seconds,
        default=DEFAULT_DEADLINE_SECONDS,
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    return run_backend_regression(
        python=sys.executable,
        deadline_seconds=args.deadline_seconds,
    )


if __name__ == "__main__":
    raise SystemExit(main())
```

Do not capture child stdout/stderr. Do not add a fallback that targets a PID after the owned `Popen` has exited.

- [ ] **Step 4: Run runner contracts and verify GREEN**

Run:

```powershell
python -m pytest tests/launch_safety/test_backend_regression_runner.py -q
python -m py_compile scripts/ops/run_backend_regression.py
```

Expected: all runner contracts pass and `py_compile` exits `0`.

- [ ] **Step 5: Self-review and commit Task 1**

Run:

```powershell
git diff --check
git status --short
git add scripts/ops/run_backend_regression.py tests/launch_safety/test_backend_regression_runner.py
git commit -m "test: add bounded backend regression runner"
```

Expected: the commit contains only the runner and its Python contracts.

## Task 2: Wire the runner into release evidence, CI, and dev dependencies

**Files:**
- Modify: `requirements-dev.txt`
- Modify: `.github/workflows/ci.yml`
- Modify: `scripts/release_gate.ps1`
- Modify: `tests/launch_safety/test_launch_matrix_contract.py`
- Modify: `tests/launch_safety/powershell/test_release_gate_harness.ps1`

- [ ] **Step 1: Write RED source/CI contracts**

In `tests/launch_safety/test_launch_matrix_contract.py`:

1. Add `BACKEND_RUNNER = ROOT / "scripts" / "ops" / "run_backend_regression.py"` beside `RELEASE_GATE`.
2. Extend the exact CI command to include `tests/launch_safety/test_backend_regression_runner.py`.
3. Require `python -m pip install pytest -r requirements-dev.txt` in the `launch-safety-contracts` job.
4. Add `tests/launch_safety/test_backend_regression_runner.py` to the curated `backend-focused` contract tuple.
5. Add `REQUIREMENTS_DEV = ROOT / "requirements-dev.txt"` and assert its lines contain exactly `pytest-xdist>=3.6,<4  # bounded two-worker closed-installer regression`.
6. Add this contract:

```python
def test_release_gate_backend_full_uses_the_bounded_two_phase_runner() -> None:
    source = RELEASE_GATE.read_text(encoding="utf-8")
    backend_full = source.split(
        'Invoke-RecordedLaunchSafetySection "backend-full-regression"', 1
    )[1].split(
        'Invoke-RecordedLaunchSafetySection "frontend-serial-regression"', 1
    )[0]

    assert '"scripts/ops/run_backend_regression.py"' in backend_full
    assert '"--deadline-seconds", "7000"' in backend_full
    assert 'Invoke-Native $Python' in backend_full
    assert '@("-m", "pytest", "-q")' not in backend_full

    runner_source = BACKEND_RUNNER.read_text(encoding="utf-8")
    assert '"-n", "2"' in runner_source
    assert '"--dist=load"' in runner_source
    assert '"--max-worker-restart=0"' in runner_source
```

- [ ] **Step 2: Update the PowerShell harness to create a RED timeout contract**

In `tests/launch_safety/powershell/test_release_gate_harness.ps1`, rename the `$exit120*` fixture variables to `$timeout124*`, then change the Python stub branch to:

```bat
if "%*"=="scripts/ops/run_backend_regression.py --deadline-seconds 7000" exit /b 124
```

Change assertions to require:

```powershell
Assert-Equal $timeout124GateExit 1 'runner timeout 124 must fail the release gate'
$timeout124Evidence = Get-Content -LiteralPath $timeout124State -Raw | ConvertFrom-Json
$backendFullEvidence = $timeout124Evidence.sections.'backend-full-regression'
Assert-Equal $backendFullEvidence.status 'fail' 'backend full timeout evidence status'
Assert-Equal ([int]$backendFullEvidence.exit_code) 124 'backend full timeout evidence code'
Assert-Equal $backendFullEvidence.command `
  'python scripts/ops/run_backend_regression.py --deadline-seconds 7000' `
  'backend full timeout evidence command'
Assert-Equal $timeout124Evidence.sections.'frontend-serial-regression'.status 'pass' `
  'frontend serial regression must still run after backend timeout'
Assert-Equal $timeout124Evidence.sections.'source-scans'.status 'pass' `
  'later required sections must still run after backend timeout'
```

- [ ] **Step 3: Run focused contracts and verify RED**

Run:

```powershell
python -m pytest tests/launch_safety/test_backend_regression_runner.py tests/launch_safety/test_launch_matrix_contract.py -q
$powershell = (Get-Command pwsh,powershell -ErrorAction Stop | Select-Object -First 1).Source
& $powershell -NoProfile -File tests/launch_safety/powershell/test_release_gate_harness.ps1
if ($LASTEXITCODE -eq 0) { throw 'PowerShell runner wiring contract unexpectedly passed' }
```

Expected: Python source/CI assertions and the PowerShell timeout contract fail because release-gate/CI wiring still uses the old command.

- [ ] **Step 4: Implement minimal dependency, CI, and release-gate wiring**

Make these exact changes:

`requirements-dev.txt`:

```text
pytest-xdist>=3.6,<4  # bounded two-worker closed-installer regression
```

`.github/workflows/ci.yml`:

```yaml
      - name: Install contract test dependencies
        run: python -m pip install pytest -r requirements-dev.txt

      - name: Run Task 45 Python contracts
        run: python -m pytest tests/launch_safety/test_backend_regression_runner.py tests/launch_safety/test_evidence_record.py tests/launch_safety/test_browser_probe_contract.py tests/launch_safety/test_launch_matrix_contract.py -q
```

Add `"tests/launch_safety/test_backend_regression_runner.py"` to the `backend-focused` pytest argument list in `scripts/release_gate.ps1`, then replace the old backend-full block with:

```powershell
  Invoke-RecordedLaunchSafetySection "backend-full-regression" `
    "python scripts/ops/run_backend_regression.py --deadline-seconds 7000" {
      Invoke-Native $Python @(
        "scripts/ops/run_backend_regression.py",
        "--deadline-seconds", "7000"
      )
    }
```

- [ ] **Step 5: Run focused contracts and verify GREEN**

Run:

```powershell
python -m pytest tests/launch_safety/test_backend_regression_runner.py tests/launch_safety/test_evidence_record.py tests/launch_safety/test_browser_probe_contract.py tests/launch_safety/test_launch_matrix_contract.py -q
$powershell = (Get-Command pwsh,powershell -ErrorAction Stop | Select-Object -First 1).Source
& $powershell -NoProfile -File tests/launch_safety/powershell/test_release_gate_harness.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
```

Expected: all Python contracts and the PowerShell harness pass; the harness records one failed backend row with exit `124` and a passing later `source-scans` row.

- [ ] **Step 6: Self-review and commit Task 2**

Run:

```powershell
git diff --check
python scripts/checks/run_hard.py --all
git add requirements-dev.txt .github/workflows/ci.yml scripts/release_gate.ps1 tests/launch_safety/test_launch_matrix_contract.py tests/launch_safety/powershell/test_release_gate_harness.ps1
git commit -m "fix: bound launch safety backend regression"
```

Expected: hard checks report `hard=0`; the commit does not include evidence Markdown or unrelated files.

## Task 3: Synchronize launch authority documents

**Files:**
- Modify: `docs/superpowers/plans/2026-07-13-launch-safety-gate.md`
- Modify: `docs/superpowers/plans/2026-07-20-launch-safety-remediation.md`
- Modify: `docs/superpowers/specs/2026-07-20-launch-safety-task45-correction-design.md`

- [ ] **Step 1: Update the serial-only authority with the narrow exception**

At the execution rules in `2026-07-13-launch-safety-gate.md`, replace the serial rule with:

```markdown
- Backend and frontend phases run sequentially. Backend tests remain serial except the approved bounded Phase B for `tests/launch_safety/test_closed_installer.py`, which uses exactly two xdist workers under `docs/superpowers/specs/2026-07-24-bounded-backend-regression-design.md`. No other suite gains parallel permission.
```

Replace the historical full-backend command with:

```powershell
python scripts/ops/run_backend_regression.py --deadline-seconds 7000
```

- [ ] **Step 2: Update active Task 45 authority**

In `2026-07-20-launch-safety-remediation.md`:

- add `scripts/ops/run_backend_regression.py`, `tests/launch_safety/test_backend_regression_runner.py`, `requirements-dev.txt`, `.github/workflows/ci.yml`, and the bounded-backend spec to Task 9 files/references;
- state that the 2026-07-24 matrix reached the external two-hour bound during the old monolithic backend command and produced only partial diagnostic state;
- change Step 6 wording from a wholly serial backend matrix to phase-sequential execution with the sole two-worker installer exception;
- keep Step 6 and Step 7 unchecked until a fresh clean-HEAD matrix and final rendering pass.

In `2026-07-20-launch-safety-task45-correction-design.md`, replace the sentence at the old sequential-matrix clause with:

```markdown
4. Từ clean Commit A chạy ma trận theo phase tuần tự: backend focused, backend full qua bounded runner (Phase A serial; chỉ `test_closed_installer.py` dùng đúng hai xdist workers), frontend focused/full serial, typecheck, build, source/config gates, rồi gọi release gate với cả hai opt-in switch. Docker/browser unavailable được ghi skip chính xác; `not-requested` không được chấp nhận.
```

- [ ] **Step 3: Verify and commit Task 3**

Run:

```powershell
git diff --check
python scripts/checks/run_hard.py --all
git add docs/superpowers/plans/2026-07-13-launch-safety-gate.md docs/superpowers/plans/2026-07-20-launch-safety-remediation.md docs/superpowers/specs/2026-07-20-launch-safety-task45-correction-design.md
git commit -m "docs: authorize bounded backend regression"
```

Expected: hard checks report `hard=0`; neither Task 9 Step 6 nor Step 7 is marked complete.

## Task 4: Prove serial/two-worker equivalence

**Files:**
- Modify only for a proven comparison blocker: `tests/launch_safety/test_closed_installer.py`.
- Comparison outputs go under `%TEMP%`.

- [ ] **Step 0: Remove proven background-output deadlocks without weakening tests**

If a focused installer node times out waiting for a marker and the marker appears only after `communicate()` starts draining `stdout`/`stderr`, preserve that RED evidence and replace only the affected background installer `PIPE` captures with per-case file-backed streams. Keep the same marker wait, exit-code assertions, authority snapshots, and process ownership. Run every affected node serially under the Windows Job supervisor or POSIX process-group owner before continuing.

- [ ] **Step 1: Install the approved test-only dependency**

Task 4's watchdog requires PowerShell 7+ for `ProcessStartInfo.ArgumentList` and owned-tree `Process.Kill($true)`. Run:

```powershell
$pwsh = (Get-Command pwsh -CommandType Application -ErrorAction Stop).Source
if ($PSVersionTable.PSVersion.Major -lt 7) {
  throw "rerun Task 4 with PowerShell 7+: $pwsh"
}
python -m pip install -r requirements-dev.txt
python -c "import xdist; print(xdist.__version__)"
```

Expected: xdist imports successfully with a `3.x` version. Do not add it to `requirements.txt`.

- [ ] **Step 2: Compare collected node IDs**

Run:

```powershell
$eq = Join-Path $env:TEMP ('vl360-backend-equivalence-' + (git rev-parse --short HEAD))
New-Item -ItemType Directory -Path $eq -Force | Out-Null
$serialNodes = Join-Path $eq 'serial-nodes.txt'
$parallelNodes = Join-Path $eq 'parallel-nodes.txt'

python -m pytest tests/launch_safety/test_closed_installer.py --collect-only -q |
  Where-Object { $_ -match '::' } | Sort-Object -Unique |
  Set-Content -LiteralPath $serialNodes -Encoding UTF8
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m pytest tests/launch_safety/test_closed_installer.py --collect-only -q -n 2 --dist=load --max-worker-restart=0 |
  Where-Object { $_ -match '::' } | Sort-Object -Unique |
  Set-Content -LiteralPath $parallelNodes -Encoding UTF8
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$nodeDiff = @(Compare-Object (Get-Content $serialNodes) (Get-Content $parallelNodes))
if ($nodeDiff.Count) { $nodeDiff | Format-Table; throw 'serial/xdist node IDs differ' }
```

Expected: both normalized files contain the same node IDs and `Compare-Object` is empty.

- [ ] **Step 3: Run full serial and two-worker installer outcomes**

Run both exact commands with separate JUnit outputs and independent finite process-tree watchdogs. The executable PowerShell harness below launches the Windows command through `scripts/ops/run_backend_regression.py --windows-job-supervisor --`; on POSIX it launches through `setsid`. It continuously drains both output streams, terminates only the owned tree/group on timeout, and returns exit `124`. Use a 21,000-second limit for the serial reference and a 7,000-second limit for xdist. These are validation limits, not the production runner's shared deadline.

```powershell
function Invoke-OwnedBoundedPython {
  param(
    [Parameter(Mandatory)][string[]]$Arguments,
    [Parameter(Mandatory)][int]$TimeoutSeconds,
    [Parameter(Mandatory)][string]$StdoutPath,
    [Parameter(Mandatory)][string]$StderrPath
  )

  $python = (Get-Command python -ErrorAction Stop).Source
  $onWindows = $env:OS -eq 'Windows_NT'
  $start = [System.Diagnostics.ProcessStartInfo]::new()
  $start.UseShellExecute = $false
  $start.RedirectStandardOutput = $true
  $start.RedirectStandardError = $true
  $start.WorkingDirectory = (Get-Location).Path
  if ($onWindows) {
    $start.FileName = $python
    $launchArguments = @(
      'scripts/ops/run_backend_regression.py',
      '--windows-job-supervisor', '--', $python
    ) + $Arguments
  } else {
    $start.FileName = (Get-Command setsid -CommandType Application -ErrorAction Stop).Source
    $launchArguments = @($python) + $Arguments
  }
  foreach ($argument in $launchArguments) { $null = $start.ArgumentList.Add($argument) }

  $process = [System.Diagnostics.Process]::new()
  $process.StartInfo = $start
  $timer = [System.Diagnostics.Stopwatch]::StartNew()
  if (-not $process.Start()) { throw 'failed to start bounded Python command' }
  $stdoutRead = $process.StandardOutput.ReadToEndAsync()
  $stderrRead = $process.StandardError.ReadToEndAsync()
  $completed = $process.WaitForExit([int]($TimeoutSeconds * 1000))
  if ($completed) {
    $process.WaitForExit()
    $exitCode = $process.ExitCode
  } else {
    if ($onWindows) {
      try { $process.Kill($true) } catch {
        if (-not $process.HasExited) { throw }
      }
    } else {
      $kill = (Get-Command kill -CommandType Application -ErrorAction Stop).Source
      $null = & $kill -TERM -- "-$($process.Id)" 2>&1
      $termDeadline = [DateTime]::UtcNow.AddSeconds(5)
      do {
        $null = $process.HasExited
        $null = & $kill -0 -- "-$($process.Id)" 2>&1
        $groupExists = $LASTEXITCODE -eq 0
        if ($groupExists) { Start-Sleep -Milliseconds 100 }
      } while ($groupExists -and [DateTime]::UtcNow -lt $termDeadline)
      if ($groupExists) {
        $null = & $kill -KILL -- "-$($process.Id)" 2>&1
        $killDeadline = [DateTime]::UtcNow.AddSeconds(15)
        do {
          $null = $process.HasExited
          $null = & $kill -0 -- "-$($process.Id)" 2>&1
          $groupExists = $LASTEXITCODE -eq 0
          if ($groupExists) { Start-Sleep -Milliseconds 100 }
        } while ($groupExists -and [DateTime]::UtcNow -lt $killDeadline)
        if ($groupExists) {
          throw 'owned comparison process group survived SIGKILL cleanup'
        }
      }
    }
    if (-not $process.WaitForExit(15000)) {
      try { $process.Kill($true) } catch {}
      if (-not $process.WaitForExit(15000)) {
        throw 'owned comparison process tree survived timeout cleanup'
      }
    }
    $exitCode = 124
  }
  $timer.Stop()

  $utf8 = [System.Text.UTF8Encoding]::new($false)
  [System.IO.File]::WriteAllText(
    $StdoutPath, $stdoutRead.GetAwaiter().GetResult(), $utf8
  )
  [System.IO.File]::WriteAllText(
    $StderrPath, $stderrRead.GetAwaiter().GetResult(), $utf8
  )
  [pscustomobject]@{
    ExitCode = $exitCode
    ElapsedSeconds = $timer.Elapsed.TotalSeconds
  }
}

$serialXml = Join-Path $eq 'serial.xml'
$parallelXml = Join-Path $eq 'parallel.xml'
$serialStdout = Join-Path $eq 'serial.stdout.txt'
$serialStderr = Join-Path $eq 'serial.stderr.txt'
$parallelStdout = Join-Path $eq 'parallel.stdout.txt'
$parallelStderr = Join-Path $eq 'parallel.stderr.txt'
$serialCommand = @(
  '-m', 'pytest', 'tests/launch_safety/test_closed_installer.py', '-q',
  "--junitxml=$serialXml"
)
$parallelCommand = @(
  '-m', 'pytest', 'tests/launch_safety/test_closed_installer.py', '-q',
  '-n', '2', '--dist=load', '--max-worker-restart=0',
  "--junitxml=$parallelXml"
)

$serialResult = Invoke-OwnedBoundedPython $serialCommand -TimeoutSeconds 21000 `
  -StdoutPath $serialStdout -StderrPath $serialStderr
$parallelResult = Invoke-OwnedBoundedPython $parallelCommand -TimeoutSeconds 7000 `
  -StdoutPath $parallelStdout -StderrPath $parallelStderr
```

The harness runs both commands even if the first is nonzero. Do not shard, filter, rerun, add markers, use `--maxfail`, or change pytest timeout behavior.

Compare per-node outcomes:

```powershell
function Read-JUnitOutcomes([string]$Path) {
  try {
    [xml]$xml = Get-Content -LiteralPath $Path -Raw -ErrorAction Stop
  } catch {
    throw "equivalence inconclusive: unreadable JUnit $Path"
  }
  $outcomes = @{}
  foreach ($case in @($xml.SelectNodes('//testcase'))) {
    $module = ([string]$case.classname).Replace('.', '/') + '.py'
    $key = "$module::$($case.name)"
    if ($outcomes.ContainsKey($key)) { throw "duplicate JUnit case: $key" }
    $outcome = if ($case.failure) { 'failure' } elseif ($case.error) { 'error' } elseif ($case.skipped) { 'skipped' } else { 'passed' }
    $outcomes[$key] = $outcome
  }
  return $outcomes
}

$inconclusive = @()
if ($serialResult.ExitCode -eq 124) { $inconclusive += 'serial watchdog timeout' }
if ($parallelResult.ExitCode -eq 124) { $inconclusive += 'xdist watchdog timeout' }
if (-not (Test-Path -LiteralPath $serialXml)) { $inconclusive += 'serial JUnit missing' }
if (-not (Test-Path -LiteralPath $parallelXml)) { $inconclusive += 'xdist JUnit missing' }
if ($inconclusive.Count) {
  throw ('equivalence inconclusive: ' + ($inconclusive -join '; '))
}

$serialOutcomes = Read-JUnitOutcomes $serialXml
$parallelOutcomes = Read-JUnitOutcomes $parallelXml
$serialExpected = @(Get-Content -LiteralPath $serialNodes | Sort-Object -Unique)
$parallelExpected = @(Get-Content -LiteralPath $parallelNodes | Sort-Object -Unique)
$serialCaseDiff = @(Compare-Object $serialExpected @($serialOutcomes.Keys | Sort-Object))
$parallelCaseDiff = @(Compare-Object $parallelExpected @($parallelOutcomes.Keys | Sort-Object))
if ($serialCaseDiff.Count -or $parallelCaseDiff.Count) {
  throw 'equivalence inconclusive: JUnit case IDs do not match collected node IDs'
}
$outcomeDiff = @(Compare-Object `
  @($serialOutcomes.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" } | Sort-Object) `
  @($parallelOutcomes.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" } | Sort-Object))
if ($outcomeDiff.Count) { $outcomeDiff | Format-Table; throw 'serial/xdist outcomes differ' }

[pscustomobject]@{
  Cases = $serialOutcomes.Count
  SerialSeconds = [math]::Round($serialResult.ElapsedSeconds, 3)
  ParallelSeconds = [math]::Round($parallelResult.ElapsedSeconds, 3)
  Speedup = [math]::Round($serialResult.ElapsedSeconds / $parallelResult.ElapsedSeconds, 3)
} | Format-List

if ($serialResult.ExitCode -ne 0 -or $parallelResult.ExitCode -ne 0) {
  throw "equivalence matched diagnostically but adoption requires both runs to pass: serial=$($serialResult.ExitCode) parallel=$($parallelResult.ExitCode)"
}
```

Expected: both commands exit `0` with identical complete case sets and outcomes. A completed mismatch blocks Task 5 and requires returning to Task 1. A timeout or incomplete JUnit file leaves equivalence unproven and also blocks Task 5; do not weaken or exclude tests.

- [ ] **Step 4: Prove the production runner meets its own deadline**

After the comparison passes, run:

```powershell
python scripts/ops/run_backend_regression.py --deadline-seconds 7000
if ($LASTEXITCODE -ne 0) { throw "bounded backend runner exited $LASTEXITCODE" }
```

Expected: Phase A and Phase B both pass within the runner's one shared 7,000-second deadline.

## Task 5: Final verification, reviews, and clean candidate commit

**Files:**
- Modify only if verification/review finds a real issue within this plan's scope.

- [ ] **Step 1: Run the fresh focused verification set**

Run:

```powershell
python -m pytest tests/launch_safety/test_backend_regression_runner.py tests/launch_safety/test_evidence_record.py tests/launch_safety/test_browser_probe_contract.py tests/launch_safety/test_launch_matrix_contract.py -q
$powershell = (Get-Command pwsh,powershell -ErrorAction Stop | Select-Object -First 1).Source
& $powershell -NoProfile -File tests/launch_safety/powershell/test_release_gate_harness.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python scripts/checks/run_hard.py --all
python -m ruff check scripts/ops/run_backend_regression.py tests/launch_safety/test_backend_regression_runner.py tests/launch_safety/test_launch_matrix_contract.py
git diff --check
git status --short
```

Expected: all focused tests pass, PowerShell harness exits `0`, hard checks report `hard=0`, and the worktree is clean after the planned commits.

- [ ] **Step 2: Run spec-compliance review**

Review the implementation against every decision and non-goal in `docs/superpowers/specs/2026-07-24-bounded-backend-regression-design.md`. Fix every Critical or Important finding, rerun Task 5 Step 1, and request re-review until approved.

- [ ] **Step 3: Run code-quality review**

Review only after spec compliance passes. Pay particular attention to PID ownership, bounded cleanup, timeout precedence, output inheritance, Windows quoting, xdist scope, and accidental production dependency changes. Fix and re-review every Critical or Important finding.

- [ ] **Step 4: Run the official launch matrix from clean HEAD**

Use the existing disposable rollback fixture procedure in `docs/runbooks/launch-safety-rollback.md`, a fresh external evidence-state path bound to the current full revision, explicit Docker/browser opt-ins, and an outer execution timeout greater than 7,000 seconds. Run:

```powershell
./scripts/release_gate.ps1 `
  -RunLaunchSafetyDockerOptIn `
  -RunLaunchSafetyBrowserOptIn `
  -LaunchSafetyEvidenceState $State
```

Expected: the state records all 12 sections. Docker/PostgreSQL/Nginx may use only exact prerequisite skips; browser runs when Chrome is available. If `backend-full-regression` exits `124` or any functional section fails, keep the state diagnostic-only and do not render final evidence.

- [ ] **Step 5: Return to active remediation Task 9 evidence flow**

Only after the official matrix passes, execute Task 9 Step 7 in `docs/superpowers/plans/2026-07-20-launch-safety-remediation.md`: validate revision/state integrity, render final evidence to a temporary path, copy the verified Markdown to `docs/superpowers/results/2026-07-20-launch-safety-gate-evidence.md`, update plan truth, run final reviews/checks, and commit evidence as a separate Commit B.
