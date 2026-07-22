from __future__ import annotations

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
