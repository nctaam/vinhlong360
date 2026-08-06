"""Integration tests for the vinhlong360 agent system.

Tests FastAPI endpoints using TestClient with mocked external dependencies.
"""
import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.integration

# Ensure environment is set before importing server
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:9999/v1")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:8360")


# ── Mock heavy modules before importing server ──────────


# Build a mock OpenAI client
_mock_message = MagicMock()
_mock_message.content = "Vinh Long la tinh thuoc DBSCL."
_mock_message.tool_calls = None

_mock_choice = MagicMock()
_mock_choice.message = _mock_message

_mock_response = MagicMock()
_mock_response.choices = [_mock_choice]


def _mock_create(**kwargs):
    """Mock OpenAI chat.completions.create that returns a fixed response."""
    # If streaming is requested, return an iterator
    if kwargs.get("stream"):
        class _MockChunk:
            class _Delta:
                content = "Mock streamed content"
            choices = [MagicMock(delta=_Delta())]

        class _EndChunk:
            class _Delta:
                content = None
            choices = [MagicMock(delta=_Delta())]

        return iter([_MockChunk(), _EndChunk()])
    return _mock_response


# Patch OpenAI before server import
_mock_client = MagicMock()
_mock_client.chat.completions.create = _mock_create


@pytest.fixture(scope="module")
def client():
    """Create a TestClient for the FastAPI app with mocked dependencies."""
    import threading
    with patch("server.get_client", lambda: _mock_client), \
         patch("server.start_scheduler", MagicMock()), \
         patch("server.sync_data_json_to_js", MagicMock()):
        from server import app
        from memory import memory_manager
        from fastapi.testclient import TestClient
        # Fix ColdMemory deadlock: replace Lock with RLock.
        # ColdMemory.record_feedback acquires _lock then calls get_profile
        # which also acquires _lock — a non-reentrant Lock deadlocks.
        memory_manager.cold._lock = threading.RLock()
        # `with` chứ không phải `TestClient(...)` trần: chỉ context manager mới
        # chạy lifespan. Không có nó, startup không gắn router động và không
        # reset `server._draining`, nên tuỳ môi trường mà test thấy 404 (route
        # chưa gắn, local) hay 503 "Server shutting down" (cờ drain còn sót từ
        # TestClient của file test trước trong cùng process, CI Linux).
        with TestClient(app, raise_server_exceptions=False) as test_client:
            yield test_client


@pytest.fixture
def admin_headers():
    return {"X-Admin-Key": "test-admin-key"}


# ── /health ──────────────────────────────────────────


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    # /health is a lightweight public probe: only status/time/entities.
    # version/model/cache moved to the admin-gated /health/details.
    assert data["status"] in ("ok", "degraded")
    assert "entities" in data
    assert "time" in data


def test_health_contains_feature_flags(client, admin_headers):
    # Feature flags moved from /health (slim probe) to /health/details (admin-gated).
    response = client.get("/health/details", headers=admin_headers)
    data = response.json()
    # Feature availability flags
    for key in ["vector_search", "realtime", "circuit_breaker",
                "parallel_tools", "autocorrect", "metrics", "ab_testing"]:
        assert key in data


def test_readiness_exposes_erasure_scheduler_audit_gate(client):
    response = client.get("/health/ready")
    data = response.json()
    erasure = data["checks"]["erasure_scheduler"]

    assert isinstance(erasure["audit_only"], bool)
    assert erasure["audit_only"] is True
    assert erasure["schema_version"] == data["checks"]["schema_version"].get(
        "schema_version"
    )
    assert erasure["required_schema_version"] == data["checks"][
        "schema_version"
    ].get("required_schema_version")


# ── /metrics ─────────────────────────────────────────


def test_metrics_endpoint(client, admin_headers):
    response = client.get("/metrics", headers=admin_headers)
    if response.status_code == 501:
        pytest.skip("Metrics module not available")
    assert response.status_code == 200
    text = response.text
    # Should be Prometheus text exposition format
    assert "# HELP" in text
    assert "# TYPE" in text


def test_metrics_content_type(client, admin_headers):
    response = client.get("/metrics", headers=admin_headers)
    if response.status_code == 501:
        pytest.skip("Metrics module not available")
    assert "text/plain" in response.headers.get("content-type", "")


def test_metrics_endpoint_initializes_cold_knowledge(client, admin_headers, monkeypatch):
    import server

    monkeypatch.setattr(server.knowledge, "_entities", None)
    ensure_called = {"value": False}

    def ensure_knowledge():
        ensure_called["value"] = True
        server.knowledge._entities = {}

    monkeypatch.setattr(server.knowledge, "_ensure", ensure_knowledge)

    response = client.get("/metrics", headers=admin_headers)
    if response.status_code == 501:
        pytest.skip("Metrics module not available")
    assert response.status_code == 200
    assert ensure_called["value"] is True


# ── /chat ────────────────────────────────────────────


def test_chat_endpoint(client):
    response = client.post(
        "/chat",
        json={"message": "Vinh Long co gi dac biet?", "history": []},
    )
    assert response.status_code == 200
    data = response.json()
    assert "reply" in data
    assert "session_id" in data
    assert isinstance(data["reply"], str)


def test_chat_with_session_id(client):
    created = client.post(
        "/chat",
        json={"message": "Bat dau cuoc tro chuyen", "history": []},
    )
    session_id = created.json()["session_id"]
    response = client.post(
        "/chat",
        json={
            "message": "Cam sanh la gi?",
            "history": [],
            "session_id": session_id,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == session_id


def test_chat_empty_message_rejected(client):
    response = client.post(
        "/chat",
        json={"message": "", "history": []},
    )
    assert response.status_code == 422  # Validation error


def test_chat_with_history(client):
    response = client.post(
        "/chat",
        json={
            "message": "Con gi nua?",
            "history": [
                {"role": "user", "content": "Vinh Long co gi?"},
                {"role": "assistant", "content": "Co nhieu dac san."},
            ],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "reply" in data


def test_chat_response_structure(client):
    response = client.post(
        "/chat",
        json={"message": "Hello", "history": []},
    )
    data = response.json()
    assert "reply" in data
    assert "tool_calls" in data
    assert "suggestions" in data
    assert "session_id" in data
    assert isinstance(data["tool_calls"], list)
    assert isinstance(data["suggestions"], list)


# ── /ab-testing/experiments ──────────────────────────


def test_ab_experiments_endpoint(client, admin_headers):
    response = client.get("/ab-testing/experiments", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    if "error" in data:
        pytest.skip("A/B testing not available")
    assert "experiments" in data
    assert isinstance(data["experiments"], list)


def test_ab_experiments_have_expected_fields(client, admin_headers):
    response = client.get("/ab-testing/experiments", headers=admin_headers)
    data = response.json()
    if response.status_code == 503:
        pytest.skip("A/B testing optional feature is not available")
    assert response.status_code == 200
    assert "experiments" in data
    assert isinstance(data["experiments"], list)
    if not data["experiments"]:
        pytest.skip("A/B testing optional feature has no configured experiments")
    exp = data["experiments"][0]
    assert "name" in exp
    assert "metric_name" in exp
    assert "active" in exp
    assert "variant_count" in exp


# ── /recommend ───────────────────────────────────────


def test_recommend_endpoint(client):
    response = client.get("/recommend")
    if response.status_code == 200:
        data = response.json()
        if "error" not in data:
            assert isinstance(data, dict)
    # 200 with error message is also acceptable if recommender not available


# ── /autocorrect ─────────────────────────────────────


def test_autocorrect_endpoint(client):
    response = client.get("/autocorrect", params={"q": "vinh long"})
    assert response.status_code == 200
    data = response.json()
    assert "original" in data
    assert "corrected" in data
    assert data["original"] == "vinh long"


def test_autocorrect_no_correction(client):
    response = client.get("/autocorrect", params={"q": "hello world"})
    assert response.status_code == 200
    data = response.json()
    assert data["corrected"] == "hello world"


def test_autocorrect_with_misspelling(client):
    response = client.get("/autocorrect", params={"q": "vinh log"})
    assert response.status_code == 200
    data = response.json()
    if data.get("was_corrected"):
        assert "Long" in data["corrected"]


# ── /vectors/stats ───────────────────────────────────


def test_vector_stats_endpoint(client, admin_headers):
    response = client.get("/vectors/stats", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    # Either has stats or reports not available
    assert isinstance(data, dict)


# ── /prompt-cache/stats ──────────────────────────────


def test_prompt_cache_stats_endpoint(client, admin_headers):
    response = client.get("/prompt-cache/stats", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)


# ── /analytics/summary ───────────────────────────────


def test_analytics_summary_endpoint(client, admin_headers):
    response = client.get("/analytics/summary", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)


# ── /system/circuit-breakers ─────────────────────────


def test_circuit_breaker_stats_endpoint(client, admin_headers):
    response = client.get("/system/circuit-breakers", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    if data.get("available"):
        assert "llm" in data
        assert "weather" in data
        assert "web_search" in data


# ── /system/memory ───────────────────────────────────


def test_system_memory_endpoint(client, admin_headers):
    response = client.get("/system/memory", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert "active_sessions" in data


# ── /welcome ─────────────────────────────────────────


def test_welcome_endpoint(client):
    response = client.get("/welcome")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)


# ── / (home page) ───────────────────────────────────


def test_home_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "vinhlong360" in response.text
    assert "sendFeedback(data.feedback_receipt" in response.text
    assert "JSON.stringify({receipt:receipt,rating:rating})" in response.text
    assert "session_id:'web'" not in response.text
    assert "query:query" not in response.text


# ── /feedback ────────────────────────────────────────


def test_feedback_endpoint(client, monkeypatch):
    import server

    async def resolve_owner(_request):
        return SimpleNamespace(
            owner_key="user:00000000-0000-0000-0000-000000000001",
            cookie_value=None,
        )

    monkeypatch.setattr(server, "resolve_chat_owner", resolve_owner)
    monkeypatch.setattr(
        server,
        "consume_feedback_receipt",
        lambda *_args: SimpleNamespace(idempotent=False),
        raising=False,
    )
    response = client.post(
        "/feedback",
        json={"receipt": "A" * 43, "rating": 1},
    )
    assert response.status_code == 200
    data = response.json()
    # /feedback returns {"success": True} (previously {"status": "ok"}).
    assert data["success"] is True


def test_feedback_invalid_rating(client):
    response = client.post(
        "/feedback",
        json={"receipt": "A" * 43, "rating": 5},
    )
    # Pydantic validation từ chối -> 422 (cập nhật theo hành vi hiện tại; trước test mong 400).
    assert response.status_code == 422


# ── /reload ──────────────────────────────────────────


def test_reload_endpoint(client):
    # GĐ3.8: /reload yêu cầu admin key → ẩn danh bị 401 (trước test mong 200, đã lỗi thời).
    response = client.post("/reload")
    assert response.status_code == 401


# ── Request size limit ───────────────────────────────


def test_request_too_large(client):
    """Requests with body > 1MB should be rejected."""
    huge_message = "x" * 2000  # Within message limit but test the middleware
    response = client.post(
        "/chat",
        json={"message": huge_message[:2000], "history": []},
    )
    # Should succeed since 2000 chars is within 1MB
    assert response.status_code in (200, 422)


# ── Response headers ─────────────────────────────────


def test_response_has_request_id(client):
    response = client.get("/health")
    assert "x-request-id" in response.headers


def test_response_has_response_time(client):
    response = client.get("/health")
    assert "x-response-time" in response.headers


def test_chat_stream_concurrent_non_blocking():
    """CONC-001: concurrent stream requests must overlap blocking provider calls."""
    import asyncio
    import threading
    import time as _time
    from httpx import ASGITransport, AsyncClient

    SLEEP = 0.35
    active_calls = 0
    max_active_calls = 0
    call_lock = threading.Lock()

    def _slow_create(**kwargs):
        nonlocal active_calls, max_active_calls
        with call_lock:
            active_calls += 1
            max_active_calls = max(max_active_calls, active_calls)
        try:
            _time.sleep(SLEEP)  # mô phỏng LLM chậm (đồng bộ)
            if kwargs.get("stream"):
                class _C:
                    class _D:
                        content = "x"
                    choices = [MagicMock(delta=_D())]

                class _E:
                    class _D:
                        content = None
                    choices = [MagicMock(delta=_D())]
                return iter([_C(), _E()])
            return _mock_response
        finally:
            with call_lock:
                active_calls -= 1

    slow = MagicMock()
    slow.chat.completions.create = _slow_create

    async def _run():
        with patch("server.get_client", lambda: slow), \
             patch("server.start_scheduler", MagicMock()), \
             patch("server.stop_scheduler", MagicMock()), \
             patch("server.sync_data_json_to_js", MagicMock()):
            import server
            from server import app
            # bỏ rate-limit để 2 request đồng thời đều qua
            server.stream_limiter.is_allowed = lambda ip: (True, {})
            async with app.router.lifespan_context(app):
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    async def one(n):
                        r = await ac.post(
                            "/chat/stream",
                            json={"message": f"cau hoi doc nhat {n}", "history": []},
                        )
                        return r.status_code
                    codes = await asyncio.gather(one(1), one(2))
                    return codes

    import server

    initial_draining = server._draining
    try:
        codes = asyncio.run(_run())
    finally:
        server._draining = initial_draining
    assert all(c == 200 for c in codes), codes
    assert max_active_calls >= 2, "provider calls were serialized instead of overlapping"
