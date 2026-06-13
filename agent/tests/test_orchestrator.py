"""
Tests for orchestrator.py — routing, agent loop, and the round-exhaustion fix.
"""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator import QueryRouter, QueryCategory, Orchestrator, GENERAL_AGENT


# ── Mock LLM response helpers ──

def _msg(content=None, tool_calls=None):
    return SimpleNamespace(content=content, tool_calls=tool_calls)

def _resp(content=None, tool_calls=None):
    return SimpleNamespace(choices=[SimpleNamespace(message=_msg(content, tool_calls))])

def _tool_call(call_id, name, args):
    return SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(name=name, arguments=json.dumps(args)),
    )


class TestQueryRouter:
    """Test query classification."""

    def test_itinerary(self):
        assert QueryRouter.classify("Lập lịch trình 2 ngày ở Vĩnh Long") == QueryCategory.ITINERARY

    def test_comparison(self):
        assert QueryRouter.classify("So sánh Vĩnh Long và Bến Tre") == QueryCategory.COMPARISON

    def test_recommendation(self):
        assert QueryRouter.classify("Gợi ý đặc sản nên thử") == QueryCategory.RECOMMENDATION

    def test_search(self):
        assert QueryRouter.classify("Tìm thông tin về cam sành") == QueryCategory.SEARCH

    def test_general_fallback(self):
        assert QueryRouter.classify("Xin chào") == QueryCategory.GENERAL

    def test_empty(self):
        assert QueryRouter.classify("") == QueryCategory.GENERAL

    def test_ascii_fallback(self):
        # No diacritics — should still route via the ASCII pass
        assert QueryRouter.classify("lich trinh di choi 3 ngay") == QueryCategory.ITINERARY


class TestAgentLoopNormalExit:
    """Test the agent loop's normal (no-tool) exit."""

    def test_immediate_answer(self):
        """LLM returns content with no tool calls → that's the answer."""
        def llm_fn(messages, tools, temperature):
            return _resp(content="Đây là câu trả lời.")

        def tool_fn(name, args):
            return "{}"

        result = Orchestrator._agent_loop(
            messages=[{"role": "user", "content": "test"}],
            tools=[], temperature=0.5, max_rounds=6, max_tool_calls=15,
            call_tool_fn=tool_fn, llm_call_fn=llm_fn,
        )
        assert result["reply"] == "Đây là câu trả lời."

    def test_tool_then_answer(self):
        """LLM calls a tool, then answers."""
        calls = {"n": 0}
        def llm_fn(messages, tools, temperature):
            calls["n"] += 1
            if calls["n"] == 1:
                return _resp(tool_calls=[_tool_call("c1", "search", {"q": "cam"})])
            return _resp(content="Cam sành rất ngọt.")

        def tool_fn(name, args):
            return json.dumps([{"id": "cam", "name": "Cam sành"}])

        result = Orchestrator._agent_loop(
            messages=[{"role": "user", "content": "cam sành?"}],
            tools=[], temperature=0.5, max_rounds=6, max_tool_calls=15,
            call_tool_fn=tool_fn, llm_call_fn=llm_fn,
        )
        assert result["reply"] == "Cam sành rất ngọt."
        assert any("search" in t for t in result["tools_used"])


class TestRoundExhaustionFix:
    """Test the fix: when rounds exhaust while still calling tools,
    force a final synthesis turn instead of returning a canned apology."""

    def test_synthesis_on_exhaustion(self):
        """Every round calls a tool → loop exhausts → synthesis turn fires."""
        synthesis_called = {"with_empty_tools": False}

        def llm_fn(messages, tools, temperature):
            # The final synthesis call passes tools=[] (empty)
            if not tools:
                synthesis_called["with_empty_tools"] = True
                return _resp(content="Tổng hợp từ dữ liệu đã thu thập.")
            # Otherwise always call a tool (never produce final content)
            return _resp(tool_calls=[_tool_call("c", "search", {"q": "x"})])

        def tool_fn(name, args):
            return json.dumps([{"id": "x", "name": "X"}])

        result = Orchestrator._agent_loop(
            messages=[{"role": "user", "content": "test"}],
            tools=[{"type": "function", "function": {"name": "search"}}],
            temperature=0.5, max_rounds=3, max_tool_calls=15,
            call_tool_fn=tool_fn, llm_call_fn=llm_fn,
        )
        # The fix should have triggered a no-tools synthesis call
        assert synthesis_called["with_empty_tools"] is True
        assert result["reply"] == "Tổng hợp từ dữ liệu đã thu thập."
        # Should NOT be the canned apology
        assert "không thể trả lời" not in result["reply"]

    def test_apology_only_if_synthesis_empty(self):
        """If the synthesis turn also returns nothing, fall back to apology."""
        def llm_fn(messages, tools, temperature):
            if not tools:
                return _resp(content="")  # synthesis fails too
            return _resp(tool_calls=[_tool_call("c", "search", {"q": "x"})])

        def tool_fn(name, args):
            return json.dumps([])

        result = Orchestrator._agent_loop(
            messages=[{"role": "user", "content": "test"}],
            tools=[{"type": "function", "function": {"name": "search"}}],
            temperature=0.5, max_rounds=2, max_tool_calls=15,
            call_tool_fn=tool_fn, llm_call_fn=llm_fn,
        )
        assert "Xin lỗi" in result["reply"]


class TestParallelExecution:
    """Test that multi-tool rounds use the parallel executor when provided."""

    class _FakeExecutor:
        def __init__(self):
            self.smart_calls = 0
        def execute_smart(self, pending):
            self.smart_calls += 1
            return [
                {"id": c["id"], "name": c["name"], "result": json.dumps([{"id": "x"}])}
                for c in pending
            ]

    def test_multi_tool_round_uses_executor(self):
        execu = self._FakeExecutor()
        calls = {"n": 0}
        def llm_fn(messages, tools, temperature):
            calls["n"] += 1
            if calls["n"] == 1:
                # Two tool calls in one round → should go parallel
                return _resp(tool_calls=[
                    _tool_call("c1", "search", {"q": "a"}),
                    _tool_call("c2", "entity_detail", {"entity_id": "b"}),
                ])
            return _resp(content="Done.")

        def tool_fn(name, args):
            return json.dumps([{"id": "x"}])

        result = Orchestrator._agent_loop(
            messages=[{"role": "user", "content": "test"}],
            tools=[{"type": "function", "function": {"name": "search"}}],
            temperature=0.5, max_rounds=4, max_tool_calls=15,
            call_tool_fn=tool_fn, llm_call_fn=llm_fn, tool_executor=execu,
        )
        assert execu.smart_calls == 1  # executor used for the 2-call round
        assert result["reply"] == "Done."
        assert len(result["tools_used"]) == 2

    def test_single_tool_round_skips_executor(self):
        execu = self._FakeExecutor()
        calls = {"n": 0}
        def llm_fn(messages, tools, temperature):
            calls["n"] += 1
            if calls["n"] == 1:
                return _resp(tool_calls=[_tool_call("c1", "search", {"q": "a"})])
            return _resp(content="Done.")

        def tool_fn(name, args):
            return json.dumps([{"id": "x"}])

        Orchestrator._agent_loop(
            messages=[{"role": "user", "content": "test"}],
            tools=[{"type": "function", "function": {"name": "search"}}],
            temperature=0.5, max_rounds=4, max_tool_calls=15,
            call_tool_fn=tool_fn, llm_call_fn=llm_fn, tool_executor=execu,
        )
        assert execu.smart_calls == 0  # single call → sequential, no executor

    def test_executor_failure_falls_back_to_sequential(self):
        class _BrokenExecutor:
            def execute_smart(self, pending):
                raise RuntimeError("pool died")
        calls = {"n": 0}
        def llm_fn(messages, tools, temperature):
            calls["n"] += 1
            if calls["n"] == 1:
                return _resp(tool_calls=[
                    _tool_call("c1", "search", {"q": "a"}),
                    _tool_call("c2", "search", {"q": "b"}),
                ])
            return _resp(content="Recovered.")
        def tool_fn(name, args):
            return json.dumps([{"id": "x"}])

        result = Orchestrator._agent_loop(
            messages=[{"role": "user", "content": "test"}],
            tools=[{"type": "function", "function": {"name": "search"}}],
            temperature=0.5, max_rounds=4, max_tool_calls=15,
            call_tool_fn=tool_fn, llm_call_fn=llm_fn, tool_executor=_BrokenExecutor(),
        )
        assert result["reply"] == "Recovered."


class TestTunedParams:
    """Test that get_params_fn overrides the specialist's default params."""

    def test_params_override_applied(self):
        captured = {}
        def llm_fn(messages, tools, temperature):
            captured["temperature"] = temperature
            return _resp(content="OK")
        def tool_fn(name, args):
            return "{}"
        def params_fn(category):
            return {"temperature": 0.99, "max_rounds": 3, "max_tool_calls": 7}

        orch = Orchestrator([])
        orch.run(
            message="Tìm cam sành", history=[], session_id="s1",
            base_system_prompt="base", call_tool_fn=tool_fn, llm_call_fn=llm_fn,
            get_params_fn=params_fn,
        )
        assert captured["temperature"] == 0.99

    def test_no_params_fn_uses_defaults(self):
        captured = {}
        def llm_fn(messages, tools, temperature):
            captured["temperature"] = temperature
            return _resp(content="OK")
        def tool_fn(name, args):
            return "{}"

        orch = Orchestrator([])
        orch.run(
            message="Tìm cam sành", history=[], session_id="s1",
            base_system_prompt="base", call_tool_fn=tool_fn, llm_call_fn=llm_fn,
        )
        # SearchAgent default temperature (not overridden) — just assert it's a float in range
        assert 0.0 <= captured["temperature"] <= 1.0


class TestBuildSpecialistMessages:
    """Test that enriched system context flows into specialist messages."""

    def test_enriched_context_preserved(self):
        """The base_system_prompt (which now carries RAG/memory context)
        must appear in the specialist's system message."""
        orch = Orchestrator([])
        enriched = "BASE PROMPT\n[RAG]: cam sành ở Bình Hòa Phước\n[Memory]: user thích trái cây"
        messages = orch.build_specialist_messages(
            message="cam sành?",
            history=[],
            agent_spec=GENERAL_AGENT,
            base_system_prompt=enriched,
        )
        assert messages[0]["role"] == "system"
        assert "[RAG]: cam sành" in messages[0]["content"]
        assert "[Memory]: user thích" in messages[0]["content"]
        assert messages[-1]["content"] == "cam sành?"

    def test_history_bounded(self):
        """History should be bounded to last 20 messages."""
        orch = Orchestrator([])
        history = [{"role": "user", "content": f"msg{i}"} for i in range(30)]
        messages = orch.build_specialist_messages(
            message="now", history=history, agent_spec=GENERAL_AGENT,
            base_system_prompt="base",
        )
        # 1 system + 20 history + 1 user = 22
        assert len(messages) == 22
