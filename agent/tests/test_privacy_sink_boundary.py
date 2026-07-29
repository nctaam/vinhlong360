"""Privacy-boundary coverage for tool output and personal sink persistence."""

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient
import pytest

os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:9999/v1")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key")
os.environ["BUILD_SEARCH_INDEXES"] = "false"
os.environ["BACKGROUND_INDEX_BUILD"] = "false"
os.environ["SCHEDULER_ENABLED"] = "false"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ab_testing  # noqa: E402
import analytics  # noqa: E402
import cost_tracker  # noqa: E402
import experience_memory  # noqa: E402
import prompt_compiler  # noqa: E402
import self_optimizer  # noqa: E402
import server  # noqa: E402
from memory import MemoryManager  # noqa: E402
from privacy_boundary import PrivacyBoundaryUnavailable  # noqa: E402


PROVIDER_PHONE = "0901234567"
PROVIDER_EMAIL = "provider-secret@example.com"
PUBLIC_PHONE = "02703822000"
DRAFT_EMAIL = "draft-contact@example.com"
SAFE_FAILURE = "Xin loi, he thong khong the xac minh an toan cau tra loi. Vui long thu lai."


@pytest.fixture(autouse=True)
def _reset_server_drain_flag():
    server._draining = False
    yield
    server._draining = False


def _memory_manager(tmp_path):
    with patch("memory.MEMORY_DIR", tmp_path):
        return MemoryManager()


def _capture(writes, name):
    def record(*args, **kwargs):
        writes.append((name, args, kwargs))

    return record


def _configure_post_chat(
    monkeypatch,
    tmp_path,
    provider_reply,
    provider_suggestions=None,
):
    manager = _memory_manager(tmp_path)
    writes = []

    async def resolve_owner(_request):
        return SimpleNamespace(owner_key="user:alice", cookie_value=None)

    monkeypatch.setattr(server, "memory_manager", manager)
    monkeypatch.setattr(server, "resolve_chat_owner", resolve_owner, raising=False)
    monkeypatch.setattr(server.chat_limiter, "is_allowed", lambda _ip: (True, {}))
    monkeypatch.setattr(server, "HAS_SEMANTIC_CACHE", False)
    monkeypatch.setattr(server, "HAS_AUTOCORRECT", False)
    monkeypatch.setattr(server, "HAS_TRACING", False)
    monkeypatch.setattr(server, "HAS_DYNAMIC_AGENTS", False)
    monkeypatch.setattr(server, "HAS_ORCHESTRATOR", True)
    monkeypatch.setattr(server, "HAS_OPTIMIZER", True)
    monkeypatch.setattr(server, "HAS_MEMORY_GRAPH", True)
    monkeypatch.setattr(server, "HAS_EXPERIENCE", True)
    monkeypatch.setattr(server, "HAS_FEWSHOT", True)
    monkeypatch.setattr(server, "HAS_LLM_JUDGE", False)
    monkeypatch.setattr(server, "HAS_AB_TESTING", True)
    monkeypatch.setattr(server, "HAS_METRICS", False)
    monkeypatch.setattr(server, "HAS_COST_TRACKER", False)
    monkeypatch.setattr(server, "HAS_GUARDRAILS", False)
    monkeypatch.setattr(server.cache, "get", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(server.cache, "put", _capture(writes, "cache"))
    monkeypatch.setattr(
        server,
        "_build_messages",
        lambda message, *_args: (
            [
                {"role": "system", "content": "system"},
                {"role": "user", "content": message},
            ],
            {},
        ),
    )
    monkeypatch.setattr(
        server,
        "_run_agent_orchestrated",
        lambda *_args, **_kwargs: (
            provider_reply,
            ["search"],
            provider_suggestions or [],
        ),
    )
    monkeypatch.setattr(server.prompt_optimizer, "get_current_variant", lambda: {})
    monkeypatch.setattr(
        server.reflexion_engine,
        "evaluate_answer",
        lambda *_args: {"score": 9, "issues": [], "good_points": ["safe"]},
    )
    monkeypatch.setattr(server.quality_tracker, "record", lambda *_args: None)
    monkeypatch.setattr(server.memory_manager, "on_message", _capture(writes, "memory_message"))
    monkeypatch.setattr(server.memory_manager, "on_chat_complete", _capture(writes, "memory_extract"))
    monkeypatch.setattr(server.memory_manager, "on_good_answer", _capture(writes, "memory_good"))
    monkeypatch.setattr(server.memory_graph, "on_chat_complete", _capture(writes, "graph"))
    monkeypatch.setattr(server.analytics, "track_query", _capture(writes, "analytics"))
    monkeypatch.setattr(server, "record_outcome", _capture(writes, "optimizer"))
    monkeypatch.setattr(server.experience_memory, "record", _capture(writes, "experience"))
    monkeypatch.setattr(server.prompt_compiler, "record_demo", _capture(writes, "prompt_demo"))
    monkeypatch.setattr(server.ab_manager, "record_outcome", _capture(writes, "ab"))
    return writes


def test_tool_result_keeps_only_exact_contact_from_public_current_payload(monkeypatch):
    monkeypatch.setattr(
        server.knowledge,
        "_entities",
        {
            "public-office": {
                "id": "public-office",
                "status": "published",
                "verified": True,
                "attributes": {"phone": PUBLIC_PHONE},
            },
            "draft-office": {
                "id": "draft-office",
                "status": "draft",
                "verified": True,
                "attributes": {"email": DRAFT_EMAIL},
            },
        },
    )
    contacts = set()
    raw = json.dumps(
        [
            {"id": "public-office", "phone": PUBLIC_PHONE, "note": PROVIDER_EMAIL},
            {"id": "draft-office", "email": DRAFT_EMAIL},
        ]
    )

    safe = server._safe_tool_result(raw, contacts)

    assert PUBLIC_PHONE in safe
    assert contacts == {PUBLIC_PHONE}
    assert PROVIDER_EMAIL not in safe
    assert DRAFT_EMAIL not in safe
    assert "[EMAIL]" in safe


def test_tool_result_does_not_trust_contact_without_selected_public_entity(monkeypatch):
    monkeypatch.setattr(
        server.knowledge,
        "_entities",
        {
            "public-office": {
                "id": "public-office",
                "status": "published",
                "verified": True,
                "attributes": {"phone": PUBLIC_PHONE},
            },
        },
    )

    safe = server._safe_tool_result(
        json.dumps({"id": "external-result", "note": PUBLIC_PHONE}),
        set(),
    )

    assert PUBLIC_PHONE not in safe
    assert "[PHONE]" in safe


def test_tool_result_restoration_marker_cannot_be_injected(monkeypatch):
    marker = "[PUBLIC_CONTACT_0]"
    monkeypatch.setattr(
        server.knowledge,
        "_entities",
        {
            "public-office": {
                "id": "public-office",
                "status": "published",
                "verified": True,
                "attributes": {"phone": PUBLIC_PHONE},
            },
        },
    )

    safe = server._safe_tool_result(
        json.dumps({
            "id": "public-office",
            "phone": PUBLIC_PHONE,
            "note": marker,
        }),
        set(),
    )

    assert safe.count(PUBLIC_PHONE) == 1
    assert marker in safe


def test_post_provider_output_is_safe_before_every_personal_sink(monkeypatch, tmp_path):
    reply = f"Call {PROVIDER_PHONE} or email {PROVIDER_EMAIL} for private details."
    writes = _configure_post_chat(monkeypatch, tmp_path, reply)

    with TestClient(server.app) as client:
        response = client.post("/chat", json={"message": "hello"})

    assert response.status_code == 200
    serialized = repr(writes)
    assert PROVIDER_PHONE not in response.json()["reply"]
    assert PROVIDER_EMAIL not in response.json()["reply"]
    assert PROVIDER_PHONE not in serialized
    assert PROVIDER_EMAIL not in serialized
    assert "user:alice" in serialized


def test_post_provider_suggestions_are_safe_before_response_and_cache(monkeypatch, tmp_path):
    suggestions = [f"Email {PROVIDER_EMAIL} for the next step"]
    writes = _configure_post_chat(
        monkeypatch,
        tmp_path,
        "Provider reply long enough to be cached safely.",
        provider_suggestions=suggestions,
    )

    with TestClient(server.app) as client:
        response = client.post("/chat", json={"message": "hello"})

    assert response.status_code == 200
    assert PROVIDER_EMAIL not in repr(response.json()["suggestions"])
    assert PROVIDER_EMAIL not in repr(writes)


def test_output_boundary_failure_writes_nothing(monkeypatch, tmp_path):
    writes = _configure_post_chat(monkeypatch, tmp_path, "Provider reply long enough for processing.")
    monkeypatch.setattr(server, "HAS_GUARDRAILS", True)
    monkeypatch.setattr(server, "HAS_COST_TRACKER", True)
    monkeypatch.setattr(
        server,
        "guardrail_budget",
        SimpleNamespace(record_usage=_capture(writes, "guardrail_budget")),
    )
    monkeypatch.setattr(
        server,
        "cost_attribution",
        SimpleNamespace(record=_capture(writes, "cost")),
    )

    def provider_with_usage(
        _message,
        _history,
        _session_id,
        _prompt,
        usage_accumulator,
        _verified_public_contacts,
    ):
        usage_accumulator.add_response(
            SimpleNamespace(
                usage=SimpleNamespace(
                    prompt_tokens=2,
                    completion_tokens=3,
                    total_tokens=5,
                ),
                choices=[SimpleNamespace(message=SimpleNamespace(content="safe"))],
            ),
            model="test-model",
            messages=[{"role": "user", "content": "safe"}],
        )
        return "Provider reply long enough for processing.", [], []

    monkeypatch.setattr(server, "_run_agent_orchestrated", provider_with_usage)
    monkeypatch.setattr(
        server,
        "prepare_chat_output",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            PrivacyBoundaryUnavailable("OUTPUT_REDACTION_FAILED")
        ),
        raising=False,
    )

    with TestClient(server.app) as client:
        response = client.post("/chat", json={"message": "hello"})

    assert response.status_code == 200
    assert response.json()["reply"] == getattr(server, "SAFE_PRIVACY_FAILURE_REPLY", SAFE_FAILURE)
    assert writes == []


def test_personal_file_stores_persist_owner_attribution(monkeypatch, tmp_path):
    analytics_path = tmp_path / "analytics.json"
    monkeypatch.setattr(analytics, "ANALYTICS_FILE", analytics_path)
    analytics.track_query(
        "safe q",
        ["search"],
        "safe answer with enough content",
        "sid",
        owner_key="user:alice",
    )
    assert analytics._load()["queries"][0]["owner_key"] == "user:alice"

    bank_path = tmp_path / "experience.json"
    monkeypatch.setattr(experience_memory, "BANK_FILE", bank_path)
    experience_memory.record(
        "safe q",
        ["search"],
        9,
        "safe a",
        owner_key="user:alice",
    )
    assert json.loads(bank_path.read_text(encoding="utf-8"))[0]["owner_key"] == "user:alice"

    pool_path = tmp_path / "prompt-pool.json"
    monkeypatch.setattr(prompt_compiler, "RAW_FILE", pool_path)
    prompt_compiler.record_demo(
        "safe q",
        "safe answer " * 20,
        9,
        owner_key="user:alice",
    )
    assert json.loads(pool_path.read_text(encoding="utf-8"))[0]["owner_key"] == "user:alice"

    performance_path = tmp_path / "performance.json"
    monkeypatch.setattr(self_optimizer, "PERFORMANCE_FILE", performance_path)
    collector = self_optimizer.PerformanceCollector()
    monkeypatch.setattr(self_optimizer, "performance_collector", collector)
    monkeypatch.setattr(self_optimizer.parameter_tuner, "increment_query_count", lambda: False)
    self_optimizer.record_outcome(
        "sid",
        "safe q",
        "direct",
        [],
        8,
        1.0,
        10,
        owner_key="user:alice",
    )
    assert collector._records[0]["owner_key"] == "user:alice"

    ab_path = tmp_path / "ab.json"
    manager = ab_testing.ABTestManager(filepath=ab_path)
    monkeypatch.setattr(ab_testing, "ab_manager", manager)
    ab_testing.create_default_experiments(manager)
    manager.assign_variant("prompt_style", "sid")
    manager.record_outcome("prompt_style", "sid", 9, owner_key="user:alice")
    assert manager._outcome_owners["prompt_style"]["sid"] == "user:alice"
    assert "user:alice" in ab_path.read_text(encoding="utf-8")


def test_cost_records_use_owner_key_and_legacy_sessions_load_unattributed(monkeypatch, tmp_path):
    costs_path = tmp_path / "costs.json"
    monkeypatch.setattr(cost_tracker, "COSTS_FILE", costs_path)
    attribution = cost_tracker.CostAttribution()
    attribution.record(
        "user:alice",
        "safe q",
        "chat",
        None,
        "test-model",
        {"total_tokens": 3},
        0.1,
    )
    current = list(attribution._records)[0]
    assert current["owner_key"] == "user:alice"
    assert "session_id" not in current

    legacy = dict(current)
    legacy.pop("owner_key")
    legacy["session_id"] = "legacy-session"
    costs_path.write_text(json.dumps({"records": [legacy]}), encoding="utf-8")
    loaded = cost_tracker.CostAttribution()
    restored = list(loaded._records)[0]
    assert restored["owner_key"] == ""
    assert "session_id" not in restored
