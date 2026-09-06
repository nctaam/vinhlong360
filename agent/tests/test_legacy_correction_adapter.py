"""Compatibility checks for retired legacy correction endpoints."""

from __future__ import annotations

import inspect
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agent"))

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import middleware  # noqa: E402
import public_api  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(public_api, "REPORTS_FILE", tmp_path / "reports.jsonl")
    middleware.report_limiter._requests.clear()
    app = FastAPI()
    app.include_router(public_api.router)
    return TestClient(app)


def _jsonl_lines(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_stale_endpoint_uses_canonical_report_service(client):
    source = inspect.getsource(public_api.report_stale_field)
    assert "ReportService" in source
    assert "ReportCreate" in source
    assert 'target_type="stale_field"' in source

    response = client.post(
        "/api/entities/p-quan-com/report-stale",
        json={"field": "phone", "detail": "0270 333 4444"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "target_not_found"
    assert _jsonl_lines(public_api.REPORTS_FILE) == []


def test_generic_report_rejects_unknown_target_type_without_legacy_coercion(client):
    response = client.post(
        "/api/report",
        json={"target_id": "x", "target_type": "weird", "reason": "spam"},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "invalid_target_type"
    assert _jsonl_lines(public_api.REPORTS_FILE) == []


def test_generic_report_requires_an_existing_target(client):
    response = client.post(
        "/api/report",
        json={
            "target_id": "missing-entity",
            "target_type": "entity",
            "reason": "Thông tin sai",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "target_not_found"
    assert _jsonl_lines(public_api.REPORTS_FILE) == []


def test_cutover_marker_helper_remains_derived_from_report_path(client):
    assert public_api._correction_cutover_marker() == public_api.REPORTS_FILE.with_name(
        "corrections-cutover.marker"
    )
