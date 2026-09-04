from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from scripts.check_contract_drift import _safe_export_environment


ROOT = Path(__file__).resolve().parents[2]
CHECKER = ROOT / "scripts" / "check_contract_drift.py"
SNAPSHOT = ROOT / "contracts" / "openapi" / "backend-openapi.json"


def run_checker(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    # Blank sensitive values prevent load_dotenv from importing a local .env.
    env.update(
        {
            "ENVIRONMENT": "development",
            "DATABASE_URL": "",
            "LLM_API_KEY": "",
            "LLM_BASE_URL": "",
            "ADMIN_API_KEY": "",
            "JWT_SECRET": "",
            "CSRF_SECRET": "",
            "CHAT_OWNER_SECRET": "",
            "PILOT_ATTEST_RUNNER_KEY": "",
        }
    )
    return subprocess.run(
        [sys.executable, str(CHECKER), *args],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )


def test_contract_drift_passes_for_canonical_snapshot() -> None:
    result = run_checker()

    assert result.returncode == 0, result.stderr or result.stdout
    assert "up to date" in result.stdout.lower()


def test_contract_drift_fails_with_regeneration_hint_for_changed_snapshot(
    tmp_path: Path,
) -> None:
    changed = tmp_path / "backend-openapi.json"
    shutil.copyfile(SNAPSHOT, changed)
    document = json.loads(changed.read_text(encoding="utf-8"))
    document["info"]["description"] = "intentional test drift"
    changed.write_text(
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_checker("--snapshot", str(changed))

    assert result.returncode != 0
    combined = (result.stdout + result.stderr).lower()
    assert "drift" in combined
    assert "python scripts/export_openapi.py" in combined


def test_contract_drift_rejects_missing_snapshot(tmp_path: Path) -> None:
    missing = tmp_path / "missing-openapi.json"

    result = run_checker("--snapshot", str(missing))

    assert result.returncode != 0
    combined = (result.stdout + result.stderr).lower()
    assert "snapshot" in combined
    assert "python scripts/export_openapi.py" in combined


def test_contract_export_environment_disables_dotenv_loading() -> None:
    environment = _safe_export_environment()

    assert environment["VL360_DISABLE_DOTENV"] == "1"
