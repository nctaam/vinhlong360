"""Readiness contract for the erasure scheduler capability."""

from __future__ import annotations

from pathlib import Path


def test_readiness_reports_erasure_scheduler_state():
    source = (Path(__file__).resolve().parents[1] / "server.py").read_text(
        encoding="utf-8"
    )

    assert 'checks["erasure_scheduler"]' in source
    assert '"required_schema_version"' in source
