from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from checks.check_complexity import ComplexityCheck  # noqa: E402


TARGETS = (
    ("agent/guardrails.py", "detect_spans"),
    ("agent/privacy_boundary.py", "feed"),
    ("agent/server.py", "_verified_public_contacts_from_payload"),
    ("agent/server.py", "_protect_public_contacts"),
    ("agent/server.py", "protect"),
)


def test_privacy_helpers_do_not_add_complexity_debt():
    for file_name, function_name in TARGETS:
        result = ComplexityCheck(root=ROOT).run(files=[file_name])
        offenders = [
            violation
            for violation in result["violations"]
            if f"{function_name}()" in violation["msg"]
        ]
        assert offenders == [], (file_name, function_name, offenders)
