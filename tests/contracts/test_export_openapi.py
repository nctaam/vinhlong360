from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import scripts.export_openapi as exporter


ROOT = Path(__file__).resolve().parents[2]
EXPORTER = ROOT / "scripts" / "export_openapi.py"


def run_export(path: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "ENVIRONMENT": "development",
            "DATABASE_URL": "",
            "LLM_API_KEY": "",
            "PILOT_ATTEST_RUNNER_KEY": "",
        }
    )
    return subprocess.run(
        [sys.executable, str(EXPORTER), "--output", str(path)],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )


def test_export_openapi_writes_live_route_document(tmp_path: Path) -> None:
    output = tmp_path / "openapi.json"
    result = run_export(output)

    assert result.returncode == 0, result.stderr
    document = json.loads(output.read_text(encoding="utf-8"))
    assert document["openapi"].startswith("3.")
    assert "/api/entities" in document["paths"]
    assert document["info"]["title"]


def test_export_openapi_describes_streaming_chat_response(tmp_path: Path) -> None:
    output = tmp_path / "openapi.json"
    result = run_export(output)

    assert result.returncode == 0, result.stderr
    document = json.loads(output.read_text(encoding="utf-8"))
    response = document["paths"]["/chat/stream"]["post"]["responses"]["200"]
    assert "text/event-stream" in response["content"]
    assert "application/json" not in response["content"]


def test_export_openapi_describes_streaming_notifications_response(tmp_path: Path) -> None:
    output = tmp_path / "openapi.json"
    result = run_export(output)

    assert result.returncode == 0, result.stderr
    document = json.loads(output.read_text(encoding="utf-8"))
    response = document["paths"]["/api/notifications/stream"]["get"]["responses"]["200"]
    assert response["content"] == {"text/event-stream": {"schema": {"type": "string"}}}


def test_export_openapi_describes_case_status_response_contract(tmp_path: Path) -> None:
    output = tmp_path / "openapi.json"
    result = run_export(output)

    assert result.returncode == 0, result.stderr
    document = json.loads(output.read_text(encoding="utf-8"))
    response = document["paths"]["/api/cases/status"]["get"]["responses"]["200"]
    schema = response["content"]["application/json"]["schema"]
    assert schema == {"$ref": "#/components/schemas/CaseStatusResponse"}

    required = set(document["components"]["schemas"]["CaseStatusResponse"]["required"])
    assert required == {
        "publicReference", "receivedAt", "currentStep", "waitingFor",
        "nextAction", "nextUpdateAt", "promiseHealth", "itemDecisions",
        "itemPublicationStates", "reviewPath", "currentRevision",
    }
    status_schema = document["components"]["schemas"]["CaseStatusResponse"]
    assert status_schema["additionalProperties"] is False
    assert status_schema["properties"]["promiseHealth"]["enum"] == [
        "on_track", "at_risk", "breached", "recovery",
    ]
    assert status_schema["properties"]["currentRevision"]["minimum"] == 1.0
    assert status_schema["properties"]["waitingFor"]["anyOf"] == [
        {"type": "string"}, {"type": "null"},
    ]


def test_response_media_registry_rejects_empty_or_duplicate_entries(tmp_path: Path, monkeypatch) -> None:
    registry = tmp_path / "response-media-types.json"
    monkeypatch.setattr(exporter, "RESPONSE_MEDIA_TYPES", registry)
    document = {"paths": {"/stream": {"get": {"responses": {"200": {}}}}}}

    registry.write_text('{"schema_version":"1","responses":[]}', encoding="utf-8")
    with pytest.raises(RuntimeError, match="at least one"):
        exporter._apply_response_media_types(document)

    registry.write_text(json.dumps({
        "schema_version": "1",
        "responses": [
            {"method": "get", "path": "/stream", "status": "200", "media_type": "text/plain", "schema": {"type": "string"}},
            {"method": "GET", "path": "/stream", "status": "200", "media_type": "text/event-stream", "schema": {"type": "string"}},
        ],
    }), encoding="utf-8")
    with pytest.raises(RuntimeError, match="duplicate"):
        exporter._apply_response_media_types(document)


def test_export_openapi_is_byte_deterministic_and_credential_free(tmp_path: Path) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"

    assert run_export(first).returncode == 0
    assert run_export(second).returncode == 0
    first_bytes = first.read_bytes()
    second_bytes = second.read_bytes()

    assert first_bytes == second_bytes
    text = first_bytes.decode("utf-8")
    for marker in ("DATABASE_URL", "PILOT_ATTEST", "LLM_API_KEY"):
        assert marker not in text
