from __future__ import annotations

from pathlib import Path
import tempfile

import pytest

from tests.launch_safety.integration import conftest as harness


@pytest.mark.parametrize(
    ("endpoint", "unsafe"),
    [
        ("", False),
        ("unix:///var/run/docker.sock", False),
        (r"npipe:////./pipe/docker_engine", False),
        ("remote.example:2376", True),
        ("127.0.0.1:2375", True),
        ("localhost:2375", True),
        ("tcp://127.0.0.1:2375", True),
        ("ssh://remote.example", True),
    ],
)
def test_remote_endpoint_safety_is_fail_closed(endpoint: str, unsafe: bool):
    assert harness.remote_endpoint_is_unsafe(endpoint) is unsafe


def test_remote_docker_host_is_rejected_before_cli_calls(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DOCKER_HOST", "remote.example:2376")
    monkeypatch.setattr(harness.shutil, "which", lambda _name: "docker")
    calls: list[list[str]] = []
    monkeypatch.setattr(
        harness,
        "_preflight_command",
        lambda args: calls.append(args) or harness.subprocess.CompletedProcess(args, 0, "", ""),
    )

    with pytest.raises(BaseException, match="remote tcp/ssh Docker context is not allowed"):
        harness.preflight_docker_runtime()
    assert calls == []


def test_head_snapshot_parser_allows_rename_and_copy_targets():
    harness.assert_head_snapshot_safe(
        "R  tests/launch_safety/integration/old.py\0"
        "tests/launch_safety/integration/new.py\0"
        "C  web/data.js\0"
        "web-nuxt/pnpm-lock.yaml\0"
    )


def test_head_snapshot_parser_rejects_runtime_paths_without_leaking_path():
    with pytest.raises(
        AssertionError,
        match="runtime snapshot differs from HEAD",
    ) as failure:
        harness.assert_head_snapshot_safe(" M docker-compose.yml\0")
    assert "docker-compose.yml" not in str(failure.value)


def _project_with_temp_root() -> tuple[harness.ComposeProject, tempfile.TemporaryDirectory[str]]:
    temporary = tempfile.TemporaryDirectory(prefix="vl360-cleanup-test-")
    project = harness.ComposeProject(harness.DockerRuntime("docker", "a" * 40))
    project._temporary = temporary
    project.root = Path(temporary.name)
    project.compose_files = (Path("docker-compose.yml"),)
    project._assert_no_project_residue = lambda: None
    return project, temporary


def test_cleanup_retries_transient_down_failure_and_then_removes_temp_project():
    project, temporary = _project_with_temp_root()
    calls: list[int] = []

    def transient_down(*_args, **_kwargs):
        calls.append(1)
        return harness.subprocess.CompletedProcess([], 1 if len(calls) == 1 else 0, "", "")

    project._raw = transient_down
    with pytest.raises(AssertionError, match="cleanup failed"):
        project.close()
    assert Path(temporary.name).exists()

    project.close()
    assert not Path(temporary.name).exists()
    assert project._closed is True


def test_cleanup_terminal_failure_removes_temp_project_after_two_down_failures():
    project, temporary = _project_with_temp_root()
    project._raw = lambda *_args, **_kwargs: harness.subprocess.CompletedProcess([], 1, "", "")

    with pytest.raises(AssertionError, match="cleanup failed"):
        project.close()
    with pytest.raises(AssertionError, match="cleanup failed"):
        project.close()
    assert not Path(temporary.name).exists()
    assert project._closed is True


def test_config_enter_preserves_primary_failure_and_allows_cleanup_retry(
    monkeypatch: pytest.MonkeyPatch,
):
    project = harness.ComposeProject(harness.DockerRuntime("docker", "a" * 40))
    temporary = tempfile.TemporaryDirectory(prefix="vl360-config-enter-")

    def failed_prepare():
        project._temporary = temporary
        project.root = Path(temporary.name)
        project.compose_files = (Path("docker-compose.yml"),)
        raise AssertionError("config-failed")

    monkeypatch.setattr(project, "_prepare", failed_prepare)
    project._raw = lambda *_args, **_kwargs: harness.subprocess.CompletedProcess([], 1, "", "")

    with pytest.raises(AssertionError, match="config-failed"):
        project.__enter__()
    assert Path(temporary.name).exists()

    with pytest.raises(AssertionError, match="cleanup failed"):
        project.close()
    assert not Path(temporary.name).exists()
