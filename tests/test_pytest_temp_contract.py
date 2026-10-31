from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
PROBE_ROOT = ROOT / ".tmp" / "pytest-contract-probe"
EXPECTED_BASETEMP = (ROOT / ".tmp" / "pytest").resolve()


def test_repository_config_places_tmp_path_under_local_basetemp():
    """Removing the repository basetemp must make this subprocess contract fail."""
    if PROBE_ROOT.exists():
        shutil.rmtree(PROBE_ROOT)
    PROBE_ROOT.mkdir(parents=True)
    probe = PROBE_ROOT / "test_probe.py"
    probe.write_text(
        "def test_emit_tmp_path(tmp_path):\n"
        "    print('VL360_TMP_PATH=' + str(tmp_path.resolve()))\n",
        encoding="ascii",
    )
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-c", "pytest.ini", "-q", "-s", str(probe)],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
    finally:
        shutil.rmtree(PROBE_ROOT, ignore_errors=True)

    assert result.returncode == 0, result.stdout + result.stderr
    marker = next(
        line.removeprefix("VL360_TMP_PATH=")
        for line in result.stdout.splitlines()
        if line.startswith("VL360_TMP_PATH=")
    )
    assert Path(marker).is_relative_to(EXPECTED_BASETEMP)
