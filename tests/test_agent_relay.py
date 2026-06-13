"""Tests for agent/agent_relay.py -- Inter-agent communication and task decomposition."""

import sys
import os
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

from agent_relay import (
    MessageBus,
    SharedScratchpad,
    TaskDecomposer,
    RelayLog,
    AgentMessage,
    MessageType,
    SubTask,
    SubTaskStatus,
    AGENT_NAMES,
    _MAX_QUEUE_SIZE,
    _SESSION_TTL,
    _MAX_SESSIONS,
)


# ---- AgentMessage ----


class TestAgentMessage(unittest.TestCase):
    def test_to_dict_round_trip(self):
        msg = AgentMessage(
            sender="SearchAgent",
            receiver="CompareAgent",
            message_type=MessageType.REQUEST,
            payload={"query": "test"},
            session_id="sess-1",
            priority=2,
        )
        d = msg.to_dict()
        msg2 = AgentMessage.from_dict(d)
        self.assertEqual(msg.id, msg2.id)
        self.assertEqual(msg.sender, msg2.sender)
        self.assertEqual(msg.receiver, msg2.receiver)
        self.assertEqual(msg.message_type, msg2.message_type)

    def test_priority_validation(self):
        with self.assertRaises(ValueError):
            AgentMessage(
                sender="A",
                receiver="B",
                message_type=MessageType.INFORM,
                payload={},
                session_id="s",
                priority=0,
            )
        with self.assertRaises(ValueError):
            AgentMessage(
                sender="A",
                receiver="B",
                message_type=MessageType.INFORM,
                payload={},
                session_id="s",
                priority=6,
            )


# ---- MessageBus ----


class TestMessageBus(unittest.TestCase):
    def setUp(self):
        self.bus = MessageBus()

    def _make_msg(self, sender="A", receiver="B", priority=3, payload=None):
        return AgentMessage(
            sender=sender,
            receiver=receiver,
            message_type=MessageType.INFORM,
            payload=payload or {},
            session_id="s1",
            priority=priority,
        )

    def test_send_and_receive(self):
        msg = self._make_msg()
        self.bus.send(msg)
        received = self.bus.receive("B")
        self.assertIsNotNone(received)
        self.assertEqual(received.id, msg.id)

    def test_receive_empty_returns_none(self):
        result = self.bus.receive("NoSuchAgent", timeout=0)
        self.assertIsNone(result)

    def test_receive_all_drains_queue(self):
        for i in range(3):
            self.bus.send(self._make_msg(payload={"i": i}))
        msgs = self.bus.receive_all("B")
        self.assertEqual(len(msgs), 3)
        # Queue should be empty now
        self.assertIsNone(self.bus.receive("B", timeout=0))

    def test_broadcast_sends_to_all_except_sender(self):
        self.bus.broadcast("SearchAgent", {"alert": "test"}, "sess-1")
        for name in AGENT_NAMES:
            msgs = self.bus.receive_all(name)
            if name == "SearchAgent":
                self.assertEqual(len(msgs), 0)
            else:
                self.assertEqual(len(msgs), 1)
                self.assertEqual(msgs[0].message_type, MessageType.INFORM)

    def test_queue_overflow_eviction(self):
        # Fill queue to capacity with low-priority messages
        for i in range(_MAX_QUEUE_SIZE):
            self.bus.send(self._make_msg(priority=5, payload={"i": i}))
        # Now send a high-priority message -- should evict one low-priority msg
        high_msg = self._make_msg(priority=1, payload={"important": True})
        self.bus.send(high_msg)
        msgs = self.bus.receive_all("B")
        self.assertEqual(len(msgs), _MAX_QUEUE_SIZE)
        # High-priority message should be present
        ids = [m.id for m in msgs]
        self.assertIn(high_msg.id, ids)

    def test_fifo_ordering(self):
        for i in range(5):
            self.bus.send(self._make_msg(payload={"i": i}))
        msg = self.bus.receive("B")
        self.assertEqual(msg.payload["i"], 0)


# ---- SharedScratchpad ----


class TestSharedScratchpad(unittest.TestCase):
    def setUp(self):
        self.pad = SharedScratchpad()

    def test_write_and_read(self):
        self.pad.write("sess-1", "key1", "value1", "SearchAgent")
        result = self.pad.read("sess-1", "key1")
        self.assertEqual(result, "value1")

    def test_read_nonexistent_returns_none(self):
        result = self.pad.read("no-session", "key")
        self.assertIsNone(result)
        self.pad.write("sess-1", "key1", "val", "A")
        result = self.pad.read("sess-1", "no-key")
        self.assertIsNone(result)

    def test_read_all(self):
        self.pad.write("sess-1", "k1", "v1", "A")
        self.pad.write("sess-1", "k2", {"nested": True}, "B")
        all_data = self.pad.read_all("sess-1")
        self.assertEqual(all_data["k1"], "v1")
        self.assertEqual(all_data["k2"], {"nested": True})

    def test_read_all_empty_session(self):
        result = self.pad.read_all("nonexistent")
        self.assertEqual(result, {})

    def test_cleanup(self):
        self.pad.write("sess-1", "k1", "v1", "A")
        self.pad.cleanup("sess-1")
        result = self.pad.read("sess-1", "k1")
        self.assertIsNone(result)
        self.assertEqual(self.pad.read_all("sess-1"), {})

    def test_lru_eviction(self):
        # Write more sessions than the cap
        for i in range(_MAX_SESSIONS + 5):
            self.pad.write(f"sess-{i}", "key", f"val-{i}", "A")
        # _auto_cleanup runs at the START of write, so after the last write
        # the count may be _MAX_SESSIONS + 1.  One more write triggers cleanup.
        self.pad.write("trigger-cleanup", "key", "val", "A")
        with self.pad._lock:
            session_count = len(self.pad._data)
        self.assertLessEqual(session_count, _MAX_SESSIONS + 1)
        # Earliest sessions should have been evicted
        self.assertIsNone(self.pad.read("sess-0", "key"))

    def test_overwrite_value(self):
        self.pad.write("sess-1", "key", "old", "A")
        self.pad.write("sess-1", "key", "new", "B")
        self.assertEqual(self.pad.read("sess-1", "key"), "new")


# ---- TaskDecomposer ----


class TestTaskDecomposer(unittest.TestCase):
    def setUp(self):
        self.td = TaskDecomposer()

    def test_single_category_no_split(self):
        subtasks = self.td.decompose("Xin chao", "general")
        self.assertEqual(len(subtasks), 1)
        self.assertEqual(subtasks[0].assigned_agent, "GeneralAgent")

    def test_itinerary_only_no_split(self):
        subtasks = self.td.decompose("lich trinh 3 ngay Vinh Long", "itinerary")
        # Contains only itinerary keywords, no second category
        self.assertEqual(len(subtasks), 1)

    def test_multi_category_itinerary_compare(self):
        query = "Lịch trình 2 ngày và so sánh các khu vực"
        subtasks = self.td.decompose(query, "itinerary")
        self.assertGreaterEqual(len(subtasks), 2)
        agents = [st.assigned_agent for st in subtasks]
        self.assertIn("ItineraryAgent", agents)
        self.assertIn("CompareAgent", agents)

    def test_multi_category_search_recommend(self):
        query = "Tìm thông tin và gợi ý món ngon"
        subtasks = self.td.decompose(query, "search")
        self.assertGreaterEqual(len(subtasks), 2)

    def test_dependency_chain(self):
        query = "Lịch trình 2 ngày và so sánh các khu vực"
        subtasks = self.td.decompose(query, "itinerary")
        if len(subtasks) >= 2:
            self.assertEqual(subtasks[0].dependencies, [])
            self.assertIn(subtasks[0].id, subtasks[1].dependencies)

    def test_empty_query(self):
        subtasks = self.td.decompose("", "general")
        self.assertEqual(len(subtasks), 1)

    def test_merge_results_all_done(self):
        tasks = [
            SubTask(description="q", assigned_agent="SearchAgent",
                    status=SubTaskStatus.DONE, result="Result A"),
            SubTask(description="q", assigned_agent="RecommendAgent",
                    status=SubTaskStatus.DONE, result="Result B"),
        ]
        merged = self.td.merge_results(tasks)
        self.assertIn("Result A", merged)
        self.assertIn("Result B", merged)
        self.assertIn("---", merged)

    def test_merge_results_single(self):
        tasks = [
            SubTask(description="q", assigned_agent="SearchAgent",
                    status=SubTaskStatus.DONE, result="Only result"),
        ]
        merged = self.td.merge_results(tasks)
        self.assertEqual(merged, "Only result")

    def test_merge_results_with_failure(self):
        tasks = [
            SubTask(description="q", assigned_agent="SearchAgent",
                    status=SubTaskStatus.FAILED),
            SubTask(description="q", assigned_agent="RecommendAgent",
                    status=SubTaskStatus.DONE, result="Fallback result"),
        ]
        merged = self.td.merge_results(tasks)
        self.assertEqual(merged, "Fallback result")

    def test_merge_results_all_failed(self):
        tasks = [
            SubTask(description="q", assigned_agent="SearchAgent",
                    status=SubTaskStatus.FAILED),
        ]
        merged = self.td.merge_results(tasks)
        self.assertIn("không", merged.lower())


# ---- RelayLog ----


class TestRelayLog(unittest.TestCase):
    def setUp(self):
        self.log = RelayLog(maxlen=100)

    def _make_msg(self, sender="A", receiver="B", msg_type=MessageType.REQUEST):
        return AgentMessage(
            sender=sender,
            receiver=receiver,
            message_type=msg_type,
            payload={},
            session_id="s1",
        )

    def test_record_and_recent(self):
        for i in range(5):
            self.log.record(self._make_msg())
        recent = self.log.recent(3)
        self.assertEqual(len(recent), 3)

    def test_recent_returns_all_if_fewer_than_n(self):
        self.log.record(self._make_msg())
        recent = self.log.recent(50)
        self.assertEqual(len(recent), 1)

    def test_stats(self):
        self.log.record(self._make_msg(sender="SearchAgent", receiver="CompareAgent",
                                       msg_type=MessageType.REQUEST))
        self.log.record(self._make_msg(sender="SearchAgent", receiver="CompareAgent",
                                       msg_type=MessageType.REQUEST))
        self.log.record(self._make_msg(sender="CompareAgent", receiver="SearchAgent",
                                       msg_type=MessageType.RESPONSE))
        stats = self.log.stats()
        self.assertEqual(stats["total"], 3)
        self.assertEqual(stats["by_type"]["request"], 2)
        self.assertEqual(stats["by_type"]["response"], 1)
        self.assertIn("SearchAgent->CompareAgent", stats["by_agent_pair"])

    def test_bounded_eviction(self):
        small_log = RelayLog(maxlen=10)
        for i in range(20):
            small_log.record(self._make_msg())
        stats = small_log.stats()
        self.assertLessEqual(stats["total"], 10)

    def test_empty_stats(self):
        stats = self.log.stats()
        self.assertEqual(stats["total"], 0)
        self.assertEqual(stats["by_type"], {})
        self.assertEqual(stats["by_agent_pair"], {})


if __name__ == "__main__":
    unittest.main()
