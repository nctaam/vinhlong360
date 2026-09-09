from __future__ import annotations

import subprocess
import sys
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_server_entrypoint_path_resolves_repo_level_script_packages() -> None:
    code = (
        "import sys; "
        f"sys.path = [{str(ROOT / 'agent')!r}] + sys.path[1:]; "
        "import server"
    )
    env = {
        "BUILD_SEARCH_INDEXES": "false",
        "BACKGROUND_INDEX_BUILD": "false",
        "SCHEDULER_ENABLED": "false",
    }
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={**os.environ, **env},
        check=False,
    )

    assert result.returncode == 0, result.stderr
