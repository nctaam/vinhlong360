from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN = ("capability", "receipt_secret", "access_token", "csrf_binding")
SINKS = ("logger.", "logging.", "analytics.", "parse_qs", "localStorage", "sessionStorage")


def test_case_security_production_sources_do_not_handle_bearers_at_unsafe_sinks():
    violations = []
    for path in (ROOT / "agent").rglob("*.py"):
        if "tests" in path.parts:
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            lowered = line.lower()
            if any(token in lowered for token in FORBIDDEN) and any(sink.lower() in lowered for sink in SINKS):
                violations.append(f"{path.relative_to(ROOT)}:{number}")
    assert violations == []
