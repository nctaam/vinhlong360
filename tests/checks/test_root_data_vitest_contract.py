from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web-nuxt"
CONFIG = WEB / "vitest.data.config.ts"
VITEST = WEB / "node_modules" / ".bin" / (
    "vitest.cmd" if os.name == "nt" else "vitest"
)


def test_root_data_vitest_config_discovers_exact_suite_set() -> None:
    completed = subprocess.run(
        [str(VITEST), "list", "--config", str(CONFIG), "--filesOnly", "--json"],
        cwd=WEB,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    discovered = {
        Path(item["file"]).resolve() for item in json.loads(completed.stdout)
    }
    expected = {path.resolve() for path in (ROOT / "tests").glob("*.test.ts")}

    assert len(expected) == 18
    assert discovered == expected
    assert not any("web-nuxt/tests" in path.as_posix() for path in discovered)


def test_root_data_suites_use_shared_immutable_database_helper() -> None:
    direct_constructor = re.compile(r"\bnew\s+DatabaseSync\s*\(")
    offenders = [
        path.name
        for path in (ROOT / "tests").glob("*.test.ts")
        if direct_constructor.search(path.read_text(encoding="utf-8"))
    ]

    assert offenders == []

    helper = (ROOT / "tests/helpers/data-contract.ts").read_text(encoding="utf-8")
    assert "pathToFileURL" in helper
    assert "dbUri.searchParams.set('mode', 'ro')" in helper
    assert "dbUri.searchParams.set('immutable', '1')" in helper
