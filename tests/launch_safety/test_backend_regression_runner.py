from __future__ import annotations

from dataclasses import FrozenInstanceError
import importlib.util
from pathlib import Path
import subprocess
import sys
from types import ModuleType
import uuid

import pytest


ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = ROOT / "scripts" / "ops" / "run_backend_regression.py"


@pytest.fixture
def runner(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    assert RUNNER_PATH.is_file(), f"backend regression runner is missing: {RUNNER_PATH}"
    name = f"backend_regression_runner_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(name, RUNNER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    return module


class FakeProcess:
    def __init__(
        self,
        returncode: int = 0,
        *,
        pid: int = 4321,
        times_out: bool = False,
        poll_results: list[int | None] | None = None,
    ) -> None:
        self.returncode = returncode
        self.pid = pid
        self.times_out = times_out
        self.wait_timeouts: list[float] = []
        self.kill_calls = 0
        self._poll_results = iter(poll_results or [None])

    def wait(self, timeout: float) -> int:
        self.wait_timeouts.append(timeout)
        if self.times_out:
            raise subprocess.TimeoutExpired(["pytest"], timeout)
        return self.returncode

    def poll(self) -> int | None:
        return next(self._poll_results)

    def kill(self) -> None:
        self.kill_calls += 1


def _install_processes(
    runner: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    processes: list[FakeProcess],
) -> list[tuple[tuple[str, ...], dict[str, object]]]:
    calls: list[tuple[tuple[str, ...], dict[str, object]]] = []
    remaining = iter(processes)

    def fake_popen(
        command: tuple[str, ...], **kwargs: object
    ) -> FakeProcess:
        calls.append((command, kwargs))
        return next(remaining)

    monkeypatch.setattr(runner.subprocess, "Popen", fake_popen)
    return calls


def test_build_phases_returns_exact_immutable_commands(runner: ModuleType) -> None:
    phases = runner.build_phases("python-under-test")

    assert phases == (
        runner.Phase(
            "A",
            (
                "python-under-test",
                "-m",
                "pytest",
                "-q",
                "--ignore=tests/launch_safety/test_closed_installer.py",
            ),
        ),
        runner.Phase(
            "B",
            (
                "python-under-test",
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
    assert "-n" not in phases[0].command
    assert not any(argument.startswith("--dist") for argument in phases[0].command)
    assert not any(
        argument.startswith("--max-worker-restart")
        for argument in phases[0].command
    )
    with pytest.raises(FrozenInstanceError):
        phases[0].name = "changed"


def test_run_reuses_one_absolute_deadline_and_shrinks_wait_budget(
    runner: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    processes = [FakeProcess(), FakeProcess()]
    calls = _install_processes(runner, monkeypatch, processes)
    clock = iter([100.0, 100.0, 100.0, 104.0, 104.0])
    monkeypatch.setattr(runner.time, "monotonic", lambda: next(clock))

    result = runner.run_backend_regression(
        "python-under-test", deadline_seconds=10.0
    )

    assert result == 0
    assert processes[0].wait_timeouts == [10.0]
    assert processes[1].wait_timeouts == [6.0]
    assert len(calls) == 2
    diagnostics = capsys.readouterr().err
    assert "phase A start" in diagnostics
    assert "phase A complete: exit 0" in diagnostics
    assert "phase B start" in diagnostics
    assert "phase B complete: exit 0" in diagnostics


def test_phase_a_failure_prevents_phase_b(
    runner: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _install_processes(runner, monkeypatch, [FakeProcess(returncode=9)])
    clock = iter([20.0, 20.0, 20.0])
    monkeypatch.setattr(runner.time, "monotonic", lambda: next(clock))

    result = runner.run_backend_regression("python-under-test", deadline_seconds=5.0)

    assert result == 9
    assert len(calls) == 1


def test_phase_b_nonzero_is_returned_after_phase_a_passes(
    runner: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _install_processes(
        runner,
        monkeypatch,
        [FakeProcess(returncode=0), FakeProcess(returncode=17)],
    )
    clock = iter([30.0, 30.0, 30.0, 31.0, 31.0])
    monkeypatch.setattr(runner.time, "monotonic", lambda: next(clock))

    result = runner.run_backend_regression("python-under-test", deadline_seconds=5.0)

    assert result == 17
    assert len(calls) == 2


def test_timeout_cleans_exact_owned_process_and_returns_124(
    runner: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    process = FakeProcess(times_out=True)
    _install_processes(runner, monkeypatch, [process])
    clock = iter([40.0, 40.0, 40.0])
    monkeypatch.setattr(runner.time, "monotonic", lambda: next(clock))
    cleaned: list[FakeProcess] = []
    monkeypatch.setattr(runner, "_cleanup_process", cleaned.append)

    result = runner.run_backend_regression("python-under-test", deadline_seconds=2.0)

    assert result == runner.TIMEOUT_EXIT_CODE == 124
    assert cleaned == [process]
    diagnostics = capsys.readouterr().err
    assert "deadline exceeded during phase A" in diagnostics
    assert "phase A cleanup complete" in diagnostics


def test_cleanup_failure_is_bounded_warning_and_timeout_stays_124(
    runner: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _install_processes(runner, monkeypatch, [FakeProcess(times_out=True)])
    clock = iter([50.0, 50.0, 50.0])
    monkeypatch.setattr(runner.time, "monotonic", lambda: next(clock))

    def fail_cleanup(_process: FakeProcess) -> None:
        raise RuntimeError("x" * (runner.MAX_DIAGNOSTIC_CHARS * 4))

    monkeypatch.setattr(runner, "_cleanup_process", fail_cleanup)

    result = runner.run_backend_regression("python-under-test", deadline_seconds=2.0)

    assert result == 124
    warning = next(
        line for line in capsys.readouterr().err.splitlines() if "cleanup warning" in line
    )
    assert len(warning) <= runner.MAX_DIAGNOSTIC_CHARS


def test_expired_deadline_before_phase_start_does_not_spawn(
    runner: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def unexpected_popen(*_args: object, **_kwargs: object) -> None:
        pytest.fail("expired deadline must not spawn a child")

    monkeypatch.setattr(runner.subprocess, "Popen", unexpected_popen)
    clock = iter([60.0, 61.0])
    monkeypatch.setattr(runner.time, "monotonic", lambda: next(clock))

    result = runner.run_backend_regression("python-under-test", deadline_seconds=1.0)

    assert result == 124
    assert "deadline exhausted before phase A" in capsys.readouterr().err


def test_deadline_exhausted_during_spawn_cleans_child_without_waiting(
    runner: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    process = FakeProcess()
    _install_processes(runner, monkeypatch, [process])
    clock = iter([80.0, 80.0, 82.0])
    monkeypatch.setattr(runner.time, "monotonic", lambda: next(clock))
    cleaned: list[FakeProcess] = []
    monkeypatch.setattr(runner, "_cleanup_process", cleaned.append)

    result = runner.run_backend_regression("python-under-test", deadline_seconds=1.0)

    assert result == 124
    assert process.wait_timeouts == []
    assert cleaned == [process]
    diagnostics = capsys.readouterr().err
    assert "deadline exceeded during phase A startup" in diagnostics
    assert "phase A cleanup complete" in diagnostics


@pytest.mark.parametrize("is_windows", [False, True])
def test_popen_uses_root_inherited_output_and_process_group(
    runner: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    is_windows: bool,
) -> None:
    calls: list[tuple[tuple[str, ...], dict[str, object]]] = []

    def fake_popen(
        command: tuple[str, ...], **kwargs: object
    ) -> FakeProcess:
        calls.append((command, kwargs))
        return FakeProcess()

    monkeypatch.setattr(runner, "IS_WINDOWS", is_windows)
    monkeypatch.setattr(runner.subprocess, "Popen", fake_popen)
    phase = runner.build_phases("python-under-test")[0]

    runner._start_phase(phase)

    assert len(calls) == 1
    command, kwargs = calls[0]
    assert kwargs["cwd"] == runner.ROOT == ROOT
    assert kwargs["stdout"] is None
    assert kwargs["stderr"] is None
    if is_windows:
        assert command == runner._windows_job_supervisor_command(phase.command)
        assert kwargs["creationflags"] == runner.CREATE_NEW_PROCESS_GROUP
        assert "start_new_session" not in kwargs
    else:
        assert command == phase.command
        assert kwargs["start_new_session"] is True
        assert "creationflags" not in kwargs


def test_windows_job_supervisor_assigns_job_before_spawning_child(
    runner: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    events: list[object] = []

    class SupervisorChild:
        def wait(self) -> int:
            events.append("wait")
            return 17

    def fake_create_job() -> int:
        events.append("assign-job")
        return 9753

    def fake_popen(command: tuple[str, ...]) -> SupervisorChild:
        events.append(("spawn", command))
        return SupervisorChild()

    monkeypatch.setattr(runner, "_create_windows_kill_on_close_job", fake_create_job)
    monkeypatch.setattr(runner.subprocess, "Popen", fake_popen)

    result = runner._run_windows_job_supervisor(("child", "argument"))

    assert result == 17
    assert events == [
        "assign-job",
        ("spawn", ("child", "argument")),
        "wait",
    ]


def test_cli_routes_private_windows_job_supervisor_mode(
    runner: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str, ...]] = []
    monkeypatch.setattr(
        runner,
        "_run_windows_job_supervisor",
        lambda command: calls.append(command) or 23,
        raising=False,
    )

    assert runner.main(
        ["--windows-job-supervisor", "--", "child", "argument"]
    ) == 23
    assert calls == [("child", "argument")]


def test_windows_cleanup_targets_live_child_with_exact_taskkill(
    runner: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    process = FakeProcess(pid=2468, poll_results=[None, None])
    calls: list[tuple[list[str], dict[str, object]]] = []

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(runner, "IS_WINDOWS", True)
    monkeypatch.setattr(runner.subprocess, "run", fake_run)

    runner._cleanup_process(process)

    assert len(calls) == 1
    command, kwargs = calls[0]
    assert command == ["taskkill", "/PID", "2468", "/T", "/F"]
    assert kwargs["timeout"] == runner.CLEANUP_TIMEOUT_SECONDS
    assert kwargs["check"] is False
    assert kwargs["stdout"] is subprocess.DEVNULL
    assert kwargs["stderr"] is subprocess.DEVNULL
    assert process.wait_timeouts == [runner.CLEANUP_TIMEOUT_SECONDS]


def test_windows_cleanup_does_not_wait_after_taskkill_if_child_exited(
    runner: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    process = FakeProcess(pid=2469, poll_results=[None, 0])

    monkeypatch.setattr(runner, "IS_WINDOWS", True)
    monkeypatch.setattr(
        runner.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0),
    )

    runner._cleanup_process(process)

    assert process.wait_timeouts == []


def test_windows_cleanup_never_targets_exited_child(
    runner: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    process = FakeProcess(pid=1357, poll_results=[0])

    def unexpected_run(*_args: object, **_kwargs: object) -> None:
        pytest.fail("taskkill must not target an exited child")

    monkeypatch.setattr(runner, "IS_WINDOWS", True)
    monkeypatch.setattr(runner.subprocess, "run", unexpected_run)

    runner._cleanup_process(process)


def test_windows_taskkill_nonzero_falls_back_to_owned_handle_and_warns(
    runner: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class TimeoutThenExitProcess(FakeProcess):
        def __init__(self) -> None:
            super().__init__(pid=8642)
            self.wait_calls = 0

        def poll(self) -> None:
            return None

        def wait(self, timeout: float) -> int:
            self.wait_timeouts.append(timeout)
            self.wait_calls += 1
            if self.wait_calls == 1:
                raise subprocess.TimeoutExpired(["pytest"], timeout)
            return 0

    process = TimeoutThenExitProcess()
    _install_processes(runner, monkeypatch, [process])
    clock = iter([90.0, 90.0, 90.0])
    monkeypatch.setattr(runner.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(runner, "IS_WINDOWS", True)
    monkeypatch.setattr(
        runner.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 7),
    )

    result = runner.run_backend_regression("python-under-test", deadline_seconds=2.0)

    assert result == 124
    assert process.kill_calls == 1
    assert process.wait_timeouts == [2.0, runner.CLEANUP_TIMEOUT_SECONDS]
    diagnostics = capsys.readouterr().err
    assert "taskkill exited 7" in diagnostics
    assert "cleanup complete" not in diagnostics


@pytest.mark.parametrize(
    "taskkill_error",
    [
        OSError("taskkill unavailable"),
        subprocess.TimeoutExpired(["taskkill"], 5.0),
    ],
)
def test_windows_taskkill_exception_falls_back_and_timeout_stays_124(
    runner: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    taskkill_error: Exception,
) -> None:
    class TimeoutThenExitProcess(FakeProcess):
        def __init__(self) -> None:
            super().__init__(pid=8643)
            self.wait_calls = 0

        def poll(self) -> None:
            return None

        def wait(self, timeout: float) -> int:
            self.wait_timeouts.append(timeout)
            self.wait_calls += 1
            if self.wait_calls == 1:
                raise subprocess.TimeoutExpired(["pytest"], timeout)
            return 0

    process = TimeoutThenExitProcess()
    _install_processes(runner, monkeypatch, [process])
    clock = iter([100.0, 100.0, 100.0])
    monkeypatch.setattr(runner.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(runner, "IS_WINDOWS", True)

    def fail_taskkill(*_args: object, **_kwargs: object) -> None:
        raise taskkill_error

    monkeypatch.setattr(runner.subprocess, "run", fail_taskkill)

    result = runner.run_backend_regression("python-under-test", deadline_seconds=2.0)

    assert result == 124
    assert process.kill_calls == 1
    assert process.wait_timeouts == [2.0, runner.CLEANUP_TIMEOUT_SECONDS]
    diagnostics = capsys.readouterr().err
    assert "taskkill" in diagnostics
    assert "cleanup complete" not in diagnostics


def test_windows_wait_timeout_uses_owned_handle_fallback(
    runner: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    class WaitTimeoutProcess(FakeProcess):
        def __init__(self) -> None:
            super().__init__(pid=8644)
            self.wait_calls = 0

        def poll(self) -> None:
            return None

        def wait(self, timeout: float) -> int:
            self.wait_timeouts.append(timeout)
            self.wait_calls += 1
            if self.wait_calls == 1:
                raise subprocess.TimeoutExpired(["taskkill"], timeout)
            return 0

    process = WaitTimeoutProcess()
    monkeypatch.setattr(runner, "IS_WINDOWS", True)
    monkeypatch.setattr(
        runner.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0),
    )

    runner._cleanup_process(process)

    assert process.kill_calls == 1
    assert process.wait_timeouts == [
        runner.CLEANUP_TIMEOUT_SECONDS,
        runner.CLEANUP_TIMEOUT_SECONDS,
    ]


def test_posix_cleanup_is_bounded_and_escalates_to_kill(
    runner: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    process = FakeProcess(pid=9753, poll_results=[0])
    signals: list[tuple[int, object]] = []
    group_states = iter([True, True])
    waits: list[tuple[FakeProcess, int]] = []
    monkeypatch.setattr(runner, "IS_WINDOWS", False)
    monkeypatch.setattr(
        runner,
        "_process_group_exists",
        lambda _pgid: next(group_states),
    )
    wait_results = iter([False, True])
    monkeypatch.setattr(
        runner,
        "_wait_for_process_group_exit",
        lambda owned_process, pgid: waits.append((owned_process, pgid))
        or next(wait_results),
    )
    monkeypatch.setattr(
        runner.os,
        "killpg",
        lambda pgid, sig: signals.append((pgid, sig)),
        raising=False,
    )

    runner._cleanup_process(process)

    assert signals == [
        (process.pid, runner.signal.SIGTERM),
        (process.pid, runner.SIGKILL),
    ]
    assert waits == [(process, process.pid), (process, process.pid)]
    assert process.wait_timeouts == []


def test_posix_cleanup_kills_owned_group_when_leader_already_exited(
    runner: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    process = FakeProcess(pid=9754, poll_results=[0])
    signals: list[tuple[int, object]] = []
    group_states = iter([True, True])
    monkeypatch.setattr(runner, "IS_WINDOWS", False)
    monkeypatch.setattr(
        runner,
        "_process_group_exists",
        lambda _pgid: next(group_states),
    )
    wait_results = iter([False, True])
    monkeypatch.setattr(
        runner,
        "_wait_for_process_group_exit",
        lambda _process, _pgid: next(wait_results),
    )
    monkeypatch.setattr(
        runner.os,
        "killpg",
        lambda pgid, sig: signals.append((pgid, sig)),
        raising=False,
    )

    runner._cleanup_process(process)

    assert signals == [
        (process.pid, runner.signal.SIGTERM),
        (process.pid, runner.SIGKILL),
    ]


def test_native_exit_code_is_preserved(
    runner: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_processes(runner, monkeypatch, [FakeProcess(returncode=-15)])
    clock = iter([70.0, 70.0, 70.0])
    monkeypatch.setattr(runner.time, "monotonic", lambda: next(clock))

    assert (
        runner.run_backend_regression("python-under-test", deadline_seconds=4.0)
        == -15
    )


def test_cli_defaults_to_current_python_and_7000_seconds(
    runner: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str, float]] = []
    monkeypatch.setattr(
        runner,
        "run_backend_regression",
        lambda python, deadline_seconds: calls.append((python, deadline_seconds)) or 23,
    )

    assert runner.main([]) == 23
    assert calls == [(sys.executable, runner.DEFAULT_DEADLINE_SECONDS)]
    assert runner.DEFAULT_DEADLINE_SECONDS == 7000.0


def test_cli_accepts_positive_finite_deadline(
    runner: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str, float]] = []
    monkeypatch.setattr(
        runner,
        "run_backend_regression",
        lambda python, deadline_seconds: calls.append((python, deadline_seconds)) or 0,
    )

    assert runner.main(["--deadline-seconds", "12.5"]) == 0
    assert calls == [(sys.executable, 12.5)]


@pytest.mark.parametrize("value", ["0", "-1", "nan", "inf", "-inf"])
def test_cli_rejects_nonpositive_or_nonfinite_deadline(
    runner: ModuleType, value: str
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        runner.main(["--deadline-seconds", value])

    assert exc_info.value.code == 2
