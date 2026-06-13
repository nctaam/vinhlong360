"""Tests for agent/streaming_tools.py -- Streaming tools and adaptive selection."""

import sys
import os
import json
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

from streaming_tools import (
    AdaptiveToolSelector,
    ToolPipeline,
    ToolStep,
    ProgressTracker,
    StreamingToolExecutor,
    ToolResultStream,
    _extract_search_results,
    _extract_entity_detail,
    _is_entity_complete,
)


# ---- AdaptiveToolSelector ----


class TestAdaptiveToolSelector(unittest.TestCase):
    def setUp(self):
        self.selector = AdaptiveToolSelector()

    def test_should_continue_no_tools_used(self):
        result = self.selector.should_continue([], [], "test query")
        self.assertTrue(result)

    def test_should_continue_suggest_followups_done_no_remaining(self):
        tools_used = ["search", "entity_detail", "nearby_entities",
                      "web_search", "suggest_followups"]
        result = self.selector.should_continue(tools_used, [], "test")
        self.assertFalse(result)

    def test_should_continue_abundant_search_results(self):
        tools_used = ["search", "entity_detail", "nearby_entities", "web_search"]
        # 10+ high-confidence results
        results = [{
            "tool": "search",
            "data": json.dumps([
                {"name": f"place{i}", "score": 0.9} for i in range(12)
            ]),
        }]
        result = self.selector.should_continue(tools_used, results, "test")
        # suggest_followups still not called, so might still continue
        self.assertIsInstance(result, bool)

    def test_should_continue_complete_entity_detail(self):
        tools_used = ["search", "entity_detail", "web_search"]
        results = [
            {"tool": "search", "data": json.dumps([{"name": "test"}])},
            {"tool": "entity_detail", "data": json.dumps({
                "name": "Test Place",
                "description": "A nice place",
                "location": "Vinh Long",
                "season": "all year",
            })},
        ]
        result = self.selector.should_continue(tools_used, results, "test")
        # entity_detail complete + nearby_entities skippable
        self.assertIsInstance(result, bool)

    def test_suggest_next_tool_first_is_search(self):
        result = self.selector.suggest_next_tool("query", [], [])
        self.assertEqual(result, "search")

    def test_suggest_next_tool_after_search(self):
        results = [{"tool": "search", "data": json.dumps([{"name": "test"}])}]
        result = self.selector.suggest_next_tool("query", ["search"], results)
        self.assertEqual(result, "entity_detail")

    def test_suggest_next_tool_all_done(self):
        all_tools = ["search", "entity_detail", "web_search",
                     "nearby_entities", "suggest_followups"]
        result = self.selector.suggest_next_tool("query", all_tools, [])
        self.assertIsNone(result)

    def test_suggest_next_tool_web_search_when_insufficient(self):
        # search used but few results -> suggest web_search
        results = [{"tool": "search", "data": json.dumps([{"name": "a", "score": 0.5}])}]
        result = self.selector.suggest_next_tool("query", ["search", "entity_detail"], results)
        self.assertEqual(result, "web_search")

    def test_suggest_next_tool_skip_web_search_when_abundant(self):
        results = [{
            "tool": "search",
            "data": json.dumps([
                {"name": f"p{i}", "score": 0.9} for i in range(12)
            ]),
        }]
        result = self.selector.suggest_next_tool("query", ["search", "entity_detail"], results)
        # Should skip web_search and suggest nearby_entities or suggest_followups
        self.assertNotEqual(result, "web_search")


# ---- ToolPipeline ----


class TestToolPipeline(unittest.TestCase):
    def test_create_pipeline_search(self):
        pipeline = ToolPipeline.create_pipeline("test query", "search")
        self.assertIsInstance(pipeline, list)
        self.assertGreater(len(pipeline), 0)
        tool_names = [s.tool_name for s in pipeline]
        self.assertIn("search", tool_names)

    def test_create_pipeline_comparison(self):
        pipeline = ToolPipeline.create_pipeline("compare areas", "comparison")
        tool_names = [s.tool_name for s in pipeline]
        self.assertIn("compare_areas", tool_names)

    def test_create_pipeline_itinerary(self):
        pipeline = ToolPipeline.create_pipeline("lich trinh 3 ngay", "itinerary")
        tool_names = [s.tool_name for s in pipeline]
        self.assertIn("generate_itinerary", tool_names)

    def test_create_pipeline_recommendation(self):
        pipeline = ToolPipeline.create_pipeline("goi y dia diem", "recommendation")
        tool_names = [s.tool_name for s in pipeline]
        self.assertIn("seasonal_now", tool_names)

    def test_create_pipeline_unknown_category(self):
        pipeline = ToolPipeline.create_pipeline("hello", "unknown_category")
        tool_names = [s.tool_name for s in pipeline]
        # Should fallback to search pipeline
        self.assertIn("search", tool_names)

    def test_execute_pipeline_basic(self):
        def mock_call_fn(tool_name, args):
            return json.dumps({"tool": tool_name, "status": "ok"})

        pipeline = [
            ToolStep(
                tool_name="search",
                args_template={"q": "test"},
                condition=lambda r: True,
                priority=0,
            ),
        ]
        results = ToolPipeline.execute_pipeline(pipeline, mock_call_fn)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["tool"], "search")

    def test_execute_pipeline_skips_failed_condition(self):
        def mock_call_fn(tool_name, args):
            return json.dumps({"tool": tool_name})

        pipeline = [
            ToolStep(
                tool_name="search",
                args_template={"q": "test"},
                condition=lambda r: True,
                priority=0,
            ),
            ToolStep(
                tool_name="entity_detail",
                args_template={"entity_id": ""},
                condition=lambda r: False,  # always skip
                priority=1,
            ),
        ]
        results = ToolPipeline.execute_pipeline(pipeline, mock_call_fn)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["tool"], "search")

    def test_execute_pipeline_handles_tool_error(self):
        def failing_call_fn(tool_name, args):
            raise RuntimeError("tool failed")

        pipeline = [
            ToolStep(
                tool_name="search",
                args_template={"q": "test"},
                condition=lambda r: True,
                priority=0,
            ),
        ]
        results = ToolPipeline.execute_pipeline(pipeline, failing_call_fn)
        self.assertEqual(len(results), 1)
        data = json.loads(results[0]["data"])
        self.assertIn("error", data)


# ---- ProgressTracker ----


class TestProgressTracker(unittest.TestCase):
    def setUp(self):
        self.tracker = ProgressTracker()

    def test_start_and_get_progress(self):
        self.tracker.start_tracking("sess-1", total_steps=5)
        progress = self.tracker.get_progress("sess-1")
        self.assertEqual(progress["total"], 5)
        self.assertEqual(progress["completed"], 0)
        self.assertEqual(progress["pct"], 0.0)

    def test_update_progress(self):
        self.tracker.start_tracking("sess-1", total_steps=4)
        self.tracker.update("sess-1", step=2, tool_name="search", status="running")
        progress = self.tracker.get_progress("sess-1")
        self.assertEqual(progress["completed"], 2)
        self.assertEqual(progress["current_tool"], "search")
        self.assertEqual(progress["pct"], 50.0)

    def test_complete(self):
        self.tracker.start_tracking("sess-1", total_steps=3)
        self.tracker.complete("sess-1")
        progress = self.tracker.get_progress("sess-1")
        self.assertEqual(progress["completed"], 3)
        self.assertEqual(progress["pct"], 100.0)

    def test_get_progress_unknown_session(self):
        progress = self.tracker.get_progress("nonexistent")
        self.assertEqual(progress, {})

    def test_update_unknown_session_does_not_crash(self):
        self.tracker.update("nonexistent", step=1, tool_name="x", status="ok")
        # Should not raise

    def test_complete_unknown_session_does_not_crash(self):
        self.tracker.complete("nonexistent")
        # Should not raise


# ---- StreamingToolExecutor ----


class TestStreamingToolExecutor(unittest.TestCase):
    def setUp(self):
        self.executor = StreamingToolExecutor(max_workers=2)

    def test_execute_empty_list(self):
        results = self.executor.execute_with_streaming([], lambda n, a: "{}")
        self.assertEqual(results, [])

    def test_execute_single_tool(self):
        def mock_call(name, args):
            return json.dumps({"name": name, "result": "ok"})

        tool_calls = [{"id": "t1", "name": "search", "args": {"q": "test"}}]
        results = self.executor.execute_with_streaming(tool_calls, mock_call)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "t1")
        self.assertEqual(results[0]["name"], "search")
        self.assertIsNone(results[0]["error"])

    def test_execute_preserves_order(self):
        def mock_call(name, args):
            return json.dumps({"name": name})

        tool_calls = [
            {"id": "t1", "name": "search", "args": {}},
            {"id": "t2", "name": "entity_detail", "args": {}},
            {"id": "t3", "name": "web_search", "args": {}},
        ]
        results = self.executor.execute_with_streaming(tool_calls, mock_call)
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0]["id"], "t1")
        self.assertEqual(results[1]["id"], "t2")
        self.assertEqual(results[2]["id"], "t3")

    def test_execute_handles_tool_error(self):
        def failing_call(name, args):
            raise ValueError("boom")

        tool_calls = [{"id": "t1", "name": "search", "args": {}}]
        results = self.executor.execute_with_streaming(tool_calls, failing_call)
        self.assertEqual(len(results), 1)
        self.assertIsNotNone(results[0]["error"])
        self.assertIn("boom", results[0]["error"])

    def test_execute_with_partial_callback(self):
        partials = []

        def mock_call(name, args):
            return json.dumps([{"item": i} for i in range(6)])

        def on_partial(tool_id, tool_name, partial_json):
            partials.append(partial_json)

        tool_calls = [{"id": "t1", "name": "search", "args": {}}]
        results = self.executor.execute_with_streaming(
            tool_calls, mock_call, on_partial=on_partial
        )
        self.assertEqual(len(results), 1)
        self.assertGreater(len(partials), 0)

    def test_partition_independent_and_dependent(self):
        tool_calls = [
            {"id": "1", "name": "search", "args": {}},
            {"id": "2", "name": "entity_detail", "args": {}},
            {"id": "3", "name": "web_search", "args": {}},
            {"id": "4", "name": "suggest_followups", "args": {}},
        ]
        ind, dep = StreamingToolExecutor._partition(tool_calls)
        ind_names = [t["name"] for t in ind]
        dep_names = [t["name"] for t in dep]
        self.assertIn("search", ind_names)
        self.assertIn("web_search", ind_names)
        self.assertIn("entity_detail", dep_names)
        self.assertIn("suggest_followups", dep_names)


# ---- Helper functions ----


class TestHelpers(unittest.TestCase):
    def test_extract_search_results_parses_json(self):
        results = [
            {"tool": "search", "data": json.dumps([{"name": "a"}, {"name": "b"}])},
        ]
        items = _extract_search_results(results)
        self.assertEqual(len(items), 2)

    def test_extract_search_results_ignores_non_search(self):
        results = [
            {"tool": "web_search", "data": json.dumps([{"name": "a"}])},
        ]
        items = _extract_search_results(results)
        self.assertEqual(len(items), 0)

    def test_extract_entity_detail(self):
        results = [
            {"tool": "entity_detail", "data": json.dumps({"name": "Test", "description": "desc"})},
        ]
        detail = _extract_entity_detail(results)
        self.assertIsNotNone(detail)
        self.assertEqual(detail["name"], "Test")

    def test_extract_entity_detail_none(self):
        detail = _extract_entity_detail([])
        self.assertIsNone(detail)

    def test_is_entity_complete(self):
        self.assertTrue(_is_entity_complete({
            "name": "Test", "description": "Desc", "location": "VL",
        }))
        self.assertFalse(_is_entity_complete({
            "name": "Test",
        }))
        self.assertFalse(_is_entity_complete({}))


# ---- ToolResultStream ----


class TestToolResultStream(unittest.TestCase):
    def test_start_and_get_final(self):
        stream = ToolResultStream(max_workers=1)

        def mock_call(name, args):
            return json.dumps({"result": "done"})

        stream_id = stream.start("search", {"q": "test"}, mock_call)
        result = stream.get_final(stream_id, timeout=5)
        self.assertIn("done", result)

    def test_is_complete(self):
        stream = ToolResultStream(max_workers=1)

        def mock_call(name, args):
            return json.dumps({"ok": True})

        stream_id = stream.start("search", {}, mock_call)
        stream.get_final(stream_id, timeout=5)
        self.assertTrue(stream.is_complete(stream_id))

    def test_is_complete_unknown_id(self):
        stream = ToolResultStream(max_workers=1)
        self.assertTrue(stream.is_complete("nonexistent"))


if __name__ == "__main__":
    unittest.main()
