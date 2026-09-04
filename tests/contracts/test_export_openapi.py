from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


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
