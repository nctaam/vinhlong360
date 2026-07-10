"""Tests for agent/orchestrator.py -- Multi-agent query routing & orchestration."""

import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agent"))

from orchestrator import (
    QueryRouter,
    QueryCategory,
    Orchestrator,
    HandoffLog,
    handoff_log,
    SEARCH_AGENT,
    RECOMMEND_AGENT,
    ITINERARY_AGENT,
    GENERAL_AGENT,
    _CATEGORY_AGENTS,
)


# ---- QueryRouter: classification with Vietnamese diacritics ----


class TestQueryRouterDiacritics:
    """Routing works with diacritics -- this is by design since autocorrect adds them."""

    def test_search_where(self):
        assert QueryRouter.classify("Chua Vinh Trang o dau?") == QueryCategory.GENERAL
        assert QueryRouter.classify("Chùa Vĩnh Tràng ở đâu?") == QueryCategory.SEARCH

    def test_search_info_about(self):
        assert QueryRouter.classify("Thông tin về cam sành Tam Bình") == QueryCategory.SEARCH

    def test_search_price(self):
        assert QueryRouter.classify("Giá vé vào cồn An Bình bao nhiêu?") == QueryCategory.SEARCH

    def test_search_nearby(self):
        assert QueryRouter.classify("Gần chùa Vam Ray có gì?") == QueryCategory.SEARCH

    def test_search_weather(self):
        assert QueryRouter.classify("Thời tiết Vĩnh Long hôm nay") == QueryCategory.SEARCH

    def test_search_who(self):
        assert QueryRouter.classify("Ai là người sáng lập làng nghề gốm?") == QueryCategory.SEARCH

    def test_recommendation_where_to_go(self):
        assert QueryRouter.classify("Nên đi đâu ở Vĩnh Long?") == QueryCategory.RECOMMENDATION

    def test_recommendation_suggest(self):
        assert QueryRouter.classify("Gợi ý món ngon Bến Tre") == QueryCategory.RECOMMENDATION

    def test_recommendation_top(self):
        assert QueryRouter.classify("Top 5 điểm tham quan nổi bật") == QueryCategory.RECOMMENDATION

    def test_recommendation_whats_interesting(self):
        assert QueryRouter.classify("Có gì hay ở Trà Vinh?") == QueryCategory.RECOMMENDATION

    def test_recommendation_specialty(self):
        assert QueryRouter.classify("Đặc sản nào ngon nhất?") == QueryCategory.RECOMMENDATION

    def test_itinerary_schedule(self):
        assert QueryRouter.classify("Lịch trình 2 ngày Vĩnh Long") == QueryCategory.ITINERARY

    def test_itinerary_plan(self):
        assert QueryRouter.classify("Lên kế hoạch đi chơi 3 ngày") == QueryCategory.ITINERARY

    def test_itinerary_english(self):
        assert QueryRouter.classify("Plan a 1-day tour") == QueryCategory.ITINERARY

    def test_itinerary_arrange_trip(self):
        assert QueryRouter.classify("Sắp xếp chuyến đi cuối tuần") == QueryCategory.ITINERARY

    def test_comparison_compare(self):
        assert QueryRouter.classify("So sánh Vĩnh Long và Bến Tre") == QueryCategory.COMPARISON

    def test_comparison_which_better(self):
        assert QueryRouter.classify("Bến Tre hay Trà Vinh hay hơn?") == QueryCategory.COMPARISON

    def test_comparison_difference(self):
        assert QueryRouter.classify("Khác nhau giữa 3 khu vực") == QueryCategory.COMPARISON

    def test_comparison_should_choose(self):
        assert QueryRouter.classify("Nên chọn Vĩnh Long hay Bến Tre?") == QueryCategory.COMPARISON


class TestQueryRouterGeneral:
    """Non-diacritic and generic queries route to general -- expected behavior."""

    def test_empty_string(self):
        assert QueryRouter.classify("") == QueryCategory.GENERAL

    def test_greeting(self):
        assert QueryRouter.classify("Xin chào") == QueryCategory.GENERAL

    def test_thanks(self):
        assert QueryRouter.classify("Cảm ơn bạn") == QueryCategory.GENERAL

    def test_who_are_you(self):
        assert QueryRouter.classify("Bạn là ai?") == QueryCategory.GENERAL

    def test_non_diacritic_fallback(self):
        # Without diacritics, pattern won't match Vietnamese keywords
        assert QueryRouter.classify("cam on ban") == QueryCategory.GENERAL


# ---- AgentSpec ----


class TestAgentSpec:
    def test_frozen(self):
        with pytest.raises(AttributeError):
            SEARCH_AGENT.name = "changed"

    def test_allowed_tools(self):
        assert "search" in SEARCH_AGENT.allowed_tools
        assert "web_search" in SEARCH_AGENT.allowed_tools
        assert "generate_itinerary" not in SEARCH_AGENT.allowed_tools

    def test_itinerary_agent_has_weather(self):
        assert "weather" in ITINERARY_AGENT.allowed_tools
        assert "generate_itinerary" in ITINERARY_AGENT.allowed_tools

    def test_general_agent_has_all_tools(self):
        # General agent should have the broadest tool set
        assert len(GENERAL_AGENT.allowed_tools) >= len(SEARCH_AGENT.allowed_tools)


# ---- Orchestrator ----


class TestOrchestrator:
    @pytest.fixture()
    def orch(self):
        """Orchestrator with mock tool list."""
        tools = [
            {"type": "function", "function": {"name": name}}
            for name in [
                "search", "entity_detail", "nearby_entities", "web_search",
                "suggest_followups", "seasonal_now", "list_itineraries",
                "itinerary_detail", "generate_itinerary", "weather",
                "compare_areas", "places_in_area", "stats",
            ]
        ]
        return Orchestrator(tools_list=tools)

    def test_route_returns_category_and_agent(self, orch):
        cat, agent = orch.route("Gợi ý món ngon Bến Tre")
        assert cat == QueryCategory.RECOMMENDATION
        assert agent.name == "RecommendAgent"

    def test_filter_tools_search_agent(self, orch):
        tools = orch.filter_tools(SEARCH_AGENT)
        names = {t["function"]["name"] for t in tools}
        assert names == set(SEARCH_AGENT.allowed_tools)

    def test_filter_tools_excludes_non_allowed(self, orch):
        tools = orch.filter_tools(SEARCH_AGENT)
        names = {t["function"]["name"] for t in tools}
        assert "generate_itinerary" not in names

    def test_build_specialist_messages_structure(self, orch):
        cat, agent = orch.route("Lịch trình 2 ngày Vĩnh Long")
        msgs = orch.build_specialist_messages(
            message="Lịch trình 2 ngày Vĩnh Long",
            history=[
                {"role": "user", "content": "Xin chào"},
                {"role": "assistant", "content": "Chào bạn!"},
            ],
            agent_spec=agent,
            base_system_prompt="Base prompt.",
        )
        # system + 2 history + 1 user = 4 messages
        assert len(msgs) == 4
        assert msgs[0]["role"] == "system"
        assert msgs[-1]["role"] == "user"
        assert msgs[-1]["content"] == "Lịch trình 2 ngày Vĩnh Long"

    def test_build_specialist_messages_includes_handoff_note(self, orch):
        agent = RECOMMEND_AGENT
        msgs = orch.build_specialist_messages(
            message="test",
            history=[],
            agent_spec=agent,
            base_system_prompt="Base.",
        )
        system_content = msgs[0]["content"]
        assert "RecommendAgent" in system_content
        assert "gợi ý và đề xuất" in system_content

    def test_build_specialist_messages_truncates_history(self, orch):
        # 25 history messages -- should keep only last 20
        history = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"msg {i}"}
            for i in range(25)
        ]
        msgs = orch.build_specialist_messages(
            message="query",
            history=history,
            agent_spec=GENERAL_AGENT,
            base_system_prompt="Base.",
        )
        # system + 20 history + 1 user = 22
        assert len(msgs) == 22

    def test_category_agent_map_complete(self):
        for cat in QueryCategory:
            assert cat in _CATEGORY_AGENTS


# ---- HandoffLog ----


class TestHandoffLog:
    def test_record_and_recent(self):
        log = HandoffLog(maxlen=100)
        log.record("s1", "test query", QueryCategory.SEARCH, SEARCH_AGENT)
        recent = log.recent(10)
        assert len(recent) == 1
        assert recent[0].session_id == "s1"
        assert recent[0].category == "search"
        assert recent[0].agent_name == "SearchAgent"

    def test_recent_default(self):
        log = HandoffLog()
        for i in range(30):
            log.record(f"s{i}", f"q{i}", QueryCategory.GENERAL, GENERAL_AGENT)
        assert len(log.recent()) == 20  # default n=20

    def test_stats(self):
        log = HandoffLog()
        log.record("s1", "q1", QueryCategory.SEARCH, SEARCH_AGENT)
        log.record("s1", "q2", QueryCategory.SEARCH, SEARCH_AGENT)
        log.record("s2", "q3", QueryCategory.ITINERARY, ITINERARY_AGENT)
        stats = log.stats()
        assert stats["SearchAgent"] == 2
        assert stats["ItineraryAgent"] == 1

    def test_bounded_size(self):
        log = HandoffLog(maxlen=5)
        for i in range(10):
            log.record(f"s{i}", f"q{i}", QueryCategory.GENERAL, GENERAL_AGENT)
        assert len(log.recent(100)) == 5

    def test_query_snippet_truncated(self):
        log = HandoffLog()
        long_query = "x" * 200
        log.record("s1", long_query, QueryCategory.GENERAL, GENERAL_AGENT)
        assert len(log.recent(1)[0].query_snippet) == 120

    def test_thread_safety(self):
        log = HandoffLog(maxlen=1000)
        errors = []

        def worker(thread_id):
            try:
                for i in range(50):
                    log.record(f"s{thread_id}", f"q{i}", QueryCategory.GENERAL, GENERAL_AGENT)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(log.recent(1000)) == 500

    def test_handoff_log_module_singleton(self):
        assert isinstance(handoff_log, HandoffLog)
