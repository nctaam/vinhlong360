from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess


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
