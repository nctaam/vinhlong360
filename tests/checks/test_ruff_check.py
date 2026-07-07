# -*- coding: utf-8 -*-
"""Test check_ruff (R20.1) — graceful-skip khi vắng ruff + filter non-py + parse."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from checks import check_ruff  # noqa: E402
from checks.check_ruff import RuffCheck  # noqa: E402


def test_level_rule():
    c = RuffCheck()
    assert c.level == "hard-ratchet" and c.rule == "R20.1" and c.name == "ruff_lint"


def test_graceful_skip_when_ruff_absent(monkeypatch):
    # Máy không có ruff → count 0, KHÔNG chặn.
    monkeypatch.setattr(check_ruff, "find_ruff", lambda: None)
    assert RuffCheck().run()["count"] == 0


def test_non_py_staged_returns_zero(monkeypatch):
    # File staged không phải .py trong agent/scripts → không gọi ruff, count 0.
    called = {"n": 0}
    monkeypatch.setattr(check_ruff, "find_ruff", lambda: (called.__setitem__("n", called["n"] + 1) or ["ruff"]))
    r = RuffCheck().run(files=["docs/x.md", "web-nuxt/app.vue"])
    assert r["count"] == 0
    assert called["n"] == 0  # không target → không định vị/chạy ruff


def test_parses_ruff_json(monkeypatch):
    monkeypatch.setattr(check_ruff, "find_ruff", lambda: ["ruff"])
    fake = [
        {"filename": "agent/x.py", "code": "F401", "message": "unused import",
         "location": {"row": 3, "column": 1}},
        {"filename": "agent/y.py", "code": "F841", "message": "unused var",
         "location": {"row": 9, "column": 1}},
    ]

    class _P:
        stdout = __import__("json").dumps(fake)
    monkeypatch.setattr(check_ruff.subprocess, "run", lambda *a, **k: _P())
    r = RuffCheck().run(files=["agent/x.py"])
    assert r["count"] == 2
    assert r["violations"][0]["rule"] == "R20.1"
    assert "F401" in r["violations"][0]["msg"]
