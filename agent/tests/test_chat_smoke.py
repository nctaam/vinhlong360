"""
Smoke test integration cho /chat (GĐ1.3).

Mock LLM (không gọi mạng) để bọc luồng chat handler end-to-end:
request -> _build_messages -> agent loop -> ChatResponse. Đây là lưới an toàn
cho các refactor GĐ3 (DB-as-SoT) và GĐ4 (concurrency).

Marked `integration` -> không chạy trong unit baseline mặc định, có chạy ở CI.
"""

import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

# Env phải set TRƯỚC khi import server (đọc lúc import + lifespan startup).
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:9999/v1")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key")
os.environ["BUILD_SEARCH_INDEXES"] = "false"
os.environ["BACKGROUND_INDEX_BUILD"] = "false"
os.environ["SCHEDULER_ENABLED"] = "false"
os.environ.setdefault("DESTRUCTIVE_OPS_LOCKED", "1")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

pytestmark = pytest.mark.integration

from fastapi.testclient import TestClient  # noqa: E402
import server  # noqa: E402


def _fake_completion(content="Vĩnh Long có Văn Thánh Miếu và làng gốm Mang Thít để tham quan."):
    """Giả lập completion KHÔNG gọi tool -> agent loop trả lời thẳng."""
    msg = SimpleNamespace(content=content, tool_calls=None, role="assistant", function_call=None)
    choice = SimpleNamespace(message=msg, finish_reason="stop", index=0)
    usage = SimpleNamespace(prompt_tokens=120, completion_tokens=25, total_tokens=145)
    return SimpleNamespace(choices=[choice], usage=usage, model="test-model", id="cmpl-test")


@pytest.fixture
def client_mocked():
    # Patch tại client module-global của server: cả circuit-breaker và orchestrated
    # đều gọi server.client.chat.completions.create.
    with patch.object(server.client.chat.completions, "create",
                      side_effect=lambda *a, **k: _fake_completion()):
        with TestClient(server.app) as c:
            yield c


def test_chat_returns_200_and_reply(client_mocked):
    r = client_mocked.post("/chat", json={"message": "Vĩnh Long có gì chơi?", "session_id": "smoke1"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body.get("reply"), str)
    assert body["reply"].strip(), "reply không được rỗng"


def test_chat_rejects_empty_message(client_mocked):
    r = client_mocked.post("/chat", json={"message": ""})
    assert r.status_code == 422  # pydantic min_length=1


def test_health_is_ok(client_mocked):
    r = client_mocked.get("/health")
    assert r.status_code == 200
    assert r.json().get("status") in ("ok", "degraded")
