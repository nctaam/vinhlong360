from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from checks.check_complexity import ComplexityCheck  # noqa: E402


TARGET_FILES = (
    "agent/index_policy.py",
    "agent/launch_policy_api.py",
    "agent/publication_status.py",
    "agent/route_manifest.py",
    "agent/sitemap_bundle.py",
    "agent/sitemap_store.py",
)


def test_task8_backend_functions_stay_below_the_complexity_limit():
    result = ComplexityCheck(root=ROOT).run(files=list(TARGET_FILES))

    assert result["violations"] == []


def test_database_connection_manager_stays_below_the_complexity_limit():
    result = ComplexityCheck(root=ROOT).run(files=["agent/database.py"])

    conn_violations = [
        violation
        for violation in result["violations"]
        if "_conn()" in violation["msg"]
    ]
    assert conn_violations == []
