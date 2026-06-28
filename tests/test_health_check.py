from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("health_check", ROOT / "scripts" / "health_check.py")
health_check = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = health_check
SPEC.loader.exec_module(health_check)


def test_main_returns_1_on_connection_error(monkeypatch) -> None:
    monkeypatch.setattr("sys.argv", ["health_check"])

    with patch.object(health_check, "_fetch", return_value=(None, "connection error: refused")):
        rc = health_check.main()

    assert rc == 1


def test_main_returns_0_on_healthy(monkeypatch) -> None:
    monkeypatch.setattr("sys.argv", ["health_check"])

    with patch.object(health_check, "_fetch", return_value=({"status": "ok"}, None)):
        rc = health_check.main()

    assert rc == 0


def test_main_returns_1_on_unhealthy_status(monkeypatch) -> None:
    monkeypatch.setattr("sys.argv", ["health_check"])

    with patch.object(health_check, "_fetch", return_value=({"status": "degraded"}, None)):
        rc = health_check.main()

    assert rc == 1


def test_main_deep_check(monkeypatch) -> None:
    monkeypatch.setattr("sys.argv", ["health_check", "--deep"])

    responses = {
        "health": ({"status": "ok"}, None),
        "health/deep": ({"status": "ok", "llm": "connected"}, None),
    }

    def mock_fetch(url, timeout):
        if "health/deep" in url:
            return responses["health/deep"]
        return responses["health"]

    with patch.object(health_check, "_fetch", side_effect=mock_fetch):
        rc = health_check.main()

    assert rc == 0


def test_main_deep_check_warns_on_llm_fail(monkeypatch) -> None:
    monkeypatch.setattr("sys.argv", ["health_check", "--deep"])

    def mock_fetch(url, timeout):
        if "health/deep" in url:
            return ({"status": "degraded"}, None)
        return ({"status": "ok"}, None)

    with patch.object(health_check, "_fetch", side_effect=mock_fetch):
        rc = health_check.main()

    assert rc == 0


def test_main_json_output(monkeypatch, capsys) -> None:
    monkeypatch.setattr("sys.argv", ["health_check", "--json"])

    with patch.object(health_check, "_fetch", return_value=({"status": "ok"}, None)):
        health_check.main()

    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["overall"] == "OK"
    assert "health" in parsed["checks"]
    assert parsed["checks"]["health"]["status"] == "OK"


def test_main_custom_base_url(monkeypatch) -> None:
    monkeypatch.setattr("sys.argv", ["health_check", "--base-url", "http://prod:9000"])

    calls = []

    def mock_fetch(url, timeout):
        calls.append(url)
        return ({"status": "ok"}, None)

    with patch.object(health_check, "_fetch", side_effect=mock_fetch):
        health_check.main()

    assert calls[0].startswith("http://prod:9000/")


def test_main_text_output(monkeypatch, capsys) -> None:
    monkeypatch.setattr("sys.argv", ["health_check"])

    with patch.object(health_check, "_fetch", return_value=({"status": "ok"}, None)):
        health_check.main()

    out = capsys.readouterr().out
    assert "[health]" in out
    assert "overall: OK" in out
