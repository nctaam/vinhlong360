"""Regression tests for owner-scoped guardrail and cost settlement."""

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:9999/v1")
os.environ["BUILD_SEARCH_INDEXES"] = "false"
os.environ["BACKGROUND_INDEX_BUILD"] = "false"
os.environ["SCHEDULER_ENABLED"] = "false"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402
import server  # noqa: E402


pytestmark = pytest.mark.integration


def _completion():
    message = SimpleNamespace(content="Owner-scoped answer", tool_calls=None, role="assistant", function_call=None)
    choice = SimpleNamespace(message=message, finish_reason="stop", index=0)
    usage = SimpleNamespace(prompt_tokens=12, completion_tokens=4, total_tokens=16)
    return SimpleNamespace(choices=[choice], usage=usage, model="test-model", id="cmpl-owner")


def _provider_create(*_args, **kwargs):
    if kwargs.get("stream"):
        content = SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="Owner stream"))])
        done = SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=None))])
        return iter([content, done])
    return _completion()


@pytest.fixture
def client_mocked():
    provider = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=_provider_create)))
    with patch.object(server, "get_client", lambda: provider):
        with TestClient(server.app) as client:
            yield client


def _stream_session_id(response) -> str:
    for line in response.text.splitlines():
        if line.startswith("data: "):
            data = json.loads(line[6:])
            if data.get("type") == "done":
                return data.get("session_id", "")
    return ""


def test_post_admission_and_settlement_share_owner_across_conversation_rotation(client_mocked):
    admitted = []
    settled = []
    attributed = []

    with patch.object(server, "HAS_GUARDRAILS", True), \
         patch.object(server, "HAS_COST_TRACKER", True), \
         patch.object(server, "check_input", side_effect=lambda _message, key: admitted.append(key) or {"allowed": True}), \
         patch.object(server.guardrail_budget, "record_usage", side_effect=lambda key, _tokens: settled.append(key)), \
         patch.object(server.cost_attribution, "record", side_effect=lambda key, *_args, **_kwargs: attributed.append(key)):
        first = client_mocked.post("/chat", json={"message": "owner post one", "history": [{"role": "user", "content": "x"}]})
        second = client_mocked.post("/chat", json={"message": "owner post two", "history": [{"role": "user", "content": "y"}]})

    assert first.status_code == second.status_code == 200
    assert first.json()["session_id"] != second.json()["session_id"]
    assert len(admitted) == len(settled) == len(attributed) == 2
    assert admitted[0] == admitted[1]
    assert settled == admitted
    assert attributed == admitted


def test_stream_admission_and_settlement_share_owner_across_conversation_rotation(client_mocked):
    admitted = []
    settled = []
    attributed = []
    history = json.dumps([{"role": "user", "content": "prior"}])

    with patch.object(server, "HAS_GUARDRAILS", True), \
         patch.object(server, "HAS_COST_TRACKER", True), \
         patch.object(server, "check_input", side_effect=lambda _message, key: admitted.append(key) or {"allowed": True}), \
         patch.object(server, "check_output", return_value={}), \
         patch.object(server.guardrail_budget, "record_usage", side_effect=lambda key, _tokens: settled.append(key)), \
         patch.object(server.cost_attribution, "record", side_effect=lambda key, *_args, **_kwargs: attributed.append(key)):
        first = client_mocked.get("/chat/stream", params={"message": "owner stream one", "history": history})
        second = client_mocked.get("/chat/stream", params={"message": "owner stream two", "history": history})

    assert first.status_code == second.status_code == 200
    assert _stream_session_id(first) != _stream_session_id(second)
    assert len(admitted) == len(settled) == len(attributed) == 2
    assert admitted[0] == admitted[1]
    assert settled == admitted
    assert attributed == admitted
