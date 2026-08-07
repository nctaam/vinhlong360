from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import subprocess
import threading

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "launch_safety_browser_e2e.mjs"


def test_probe_browser_returns_three_without_creating_profile_or_network(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["CHROME_PATH"] = str(tmp_path / "missing-browser.exe")
    result = subprocess.run(
        ["node", str(SCRIPT), "--probe-browser"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 3
    assert not list(tmp_path.iterdir())


def test_probe_browser_uses_the_same_explicit_candidate_without_starting_it(tmp_path: Path) -> None:
    candidate = tmp_path / "browser.exe"
    candidate.write_text("stub", encoding="utf-8")
    env = os.environ.copy()
    env["CHROME_PATH"] = str(candidate)

    result = subprocess.run(
        ["node", str(SCRIPT), "--probe-browser"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == ""
    assert result.stderr.strip() == ""


def test_browser_smoke_keeps_the_reviewed_service_worker_and_cache_assertions() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    package = json.loads((ROOT / "web-nuxt" / "package.json").read_text(encoding="utf-8"))

    assert "POLICY_CACHE_NAMES" in source
    assert "installLegacyWorker" in source
    assert "activateCurrentWorker" in source
    assert "assertOfflineReplay" in source
    assert package["scripts"]["smoke:launch-safety"] == (
        "node ../scripts/launch_safety_browser_e2e.mjs "
        "--install-legacy-worker-first --activate-current-worker "
        "--assert-policy-cache-storage-empty --assert-offline-policy-replay-denied"
    )


def test_default_release_gate_does_not_invoke_browser_or_preview(tmp_path: Path) -> None:
    marker = tmp_path / "node-invoked.txt"
    node_stub = tmp_path / "node.cmd"
    node_stub.write_text(f'@echo off\r\necho invoked>"{marker}"\r\nexit /b 91\r\n', encoding="ascii")
    # "Cổng mặc định" = cổng chạy trên máy KHÔNG khai DATABASE_URL. release_gate.ps1:545
    # tự bật "local dev auth check" ngay khi thấy biến đó, và Postgres dùng-một-lần của
    # job test-pg không có tài khoản dev 0909090909 → WARN → gate exit 2. Đấy là hành vi
    # ĐÚNG của cổng, nên siết assertion là sai chỗ; cái sai là bài test đọc env của runner.
    # Ghim env để phép đo "không đụng browser/preview" cho cùng kết quả ở cả hai job CI.
    env = os.environ.copy()
    env.pop("DATABASE_URL", None)
    powershell = next(
        (candidate for candidate in ("pwsh", "powershell") if subprocess.run(
            [candidate, "-NoProfile", "-Command", "exit 0"],
            capture_output=True,
            check=False,
        ).returncode == 0),
        None,
    )
    assert powershell is not None

    result = subprocess.run(
        [
            powershell,
            "-NoProfile",
            "-File",
            str(ROOT / "scripts" / "release_gate.ps1"),
            "-SkipBackend",
            "-SkipFrontend",
            "-SkipData",
            "-Node",
            str(node_stub),
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert not marker.exists()


def test_browser_release_harness_contract_is_bounded_and_targets_real_nuxt_output() -> None:
    harness = ROOT / "scripts" / "ops" / "release_gate_browser_harness.ps1"
    source = harness.read_text(encoding="utf-8")

    assert ".output/server/index.mjs" in source
    assert "HOST" in source and "NITRO_HOST" in source
    assert "PORT" in source and "NITRO_PORT" in source
    assert "SMOKE_BASE_URL" in source
    assert "npm" in source and "smoke:launch-safety" in source
    assert "MAX_LAUNCH_SAFETY_OUTPUT" in source


def _run_assert_server(root_status: int, worker_status: int, worker_body: str = "worker") -> subprocess.CompletedProcess[str]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/sw.js":
                body = worker_body.encode("utf-8")
                status = worker_status
            else:
                body = b"home"
                status = root_status
            self.send_response(status)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        module = (ROOT / "scripts" / "launch_safety_browser_e2e.mjs").as_uri()
        command = (
            f"import {{ assertServer }} from {json.dumps(module)}; "
            f"await assertServer({json.dumps(base_url)});"
        )
        return subprocess.run(
            ["node", "--input-type=module", "-e", command],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.mark.parametrize("root_status", [199, 404, 500])
def test_assert_server_rejects_unsuccessful_root_status(root_status: int) -> None:
    result = _run_assert_server(root_status, 200)

    assert result.returncode != 0, result.stdout + result.stderr


@pytest.mark.parametrize("root_status", [200, 302])
def test_assert_server_accepts_successful_root_status(root_status: int) -> None:
    result = _run_assert_server(root_status, 200)

    assert result.returncode == 0, result.stdout + result.stderr


def test_stop_chrome_process_terminates_the_spawned_process_tree() -> None:
    module = (ROOT / "scripts" / "launch_safety_browser_e2e.mjs").as_uri()
    command = (
        f"import {{ spawn }} from 'node:child_process'; "
        f"import {{ stopChromeProcess }} from {json.dumps(module)}; "
        "const child = spawn(process.execPath, ['-e', 'setInterval(() => {}, 100000)'], "
        "{ stdio: 'ignore', detached: process.platform !== 'win32' }); "
        "await stopChromeProcess(child); "
        "if (child.exitCode === null && child.signalCode === null) process.exit(1);"
    )
    result = subprocess.run(
        ["node", "--input-type=module", "-e", command],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_stop_chrome_process_accepts_a_process_already_exited_by_signal() -> None:
    module = (ROOT / "scripts" / "launch_safety_browser_e2e.mjs").as_uri()
    command = (
        f"import {{ spawn }} from 'node:child_process'; "
        f"import {{ stopChromeProcess }} from {json.dumps(module)}; "
        "const child = spawn(process.execPath, ['-e', 'setInterval(() => {}, 100000)'], { stdio: 'ignore' }); "
        "await new Promise(resolve => child.once('spawn', resolve)); "
        "child.kill('SIGTERM'); "
        "await new Promise(resolve => child.once('exit', resolve)); "
        "await stopChromeProcess(child, { timeoutMs: 50 });"
    )
    result = subprocess.run(
        ["node", "--input-type=module", "-e", command],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_profile_cleanup_errors_are_returned_for_evidence() -> None:
    module = (ROOT / "scripts" / "launch_safety_browser_e2e.mjs").as_uri()
    command = (
        f"import {{ cleanupBrowserResources }} from {json.dumps(module)}; "
        "const errors = await cleanupBrowserResources({ temporaryProfile: true, profile: 'x', "
        "removeProfile: async () => { throw new Error('denied'); } }); "
        "console.log(JSON.stringify(errors));"
    )
    result = subprocess.run(
        ["node", "--input-type=module", "-e", command],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "profile-cleanup-failed" in result.stdout
