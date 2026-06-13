"""Tests for a2a_protocol.py -- Level 7 Google A2A protocol."""

import sys
import os
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

from a2a_protocol import (
    AgentCard,
    AgentSkill,
    DEFAULT_SKILLS,
    TaskState,
    A2ATask,
    TaskManager,
    A2AServer,
    get_agent_card,
    get_a2a_status,
)


class TestAgentCard(unittest.TestCase):
    """Tests for AgentCard."""

    def test_to_dict_has_json_ld_fields(self):
        card = AgentCard()
        d = card.to_dict()
        self.assertEqual(d["@context"], "https://schema.org")
        self.assertEqual(d["@type"], "SoftwareAgent")
        self.assertIn("name", d)
        self.assertIn("skills", d)
        self.assertEqual(d["protocol"], "a2a")

    def test_to_well_known_has_correct_fields(self):
        card = AgentCard()
        wk = card.to_well_known()
        self.assertIn("name", wk)
        self.assertIn("description", wk)
        self.assertIn("url", wk)
        self.assertIn("version", wk)
        self.assertIn("capabilities", wk)
        self.assertIn("skills", wk)
        self.assertIn("inputModes", wk)
        self.assertIn("outputModes", wk)
        self.assertIn("protocol", wk)
        self.assertIn("protocolVersion", wk)
        self.assertIn("endpoints", wk)

    def test_to_well_known_endpoints(self):
        card = AgentCard()
        wk = card.to_well_known()
        endpoints = wk["endpoints"]
        self.assertIn("agentCard", endpoints)
        self.assertIn("tasksSend", endpoints)
        self.assertIn("tasksGet", endpoints)
        self.assertIn("tasksCancel", endpoints)

    def test_default_card_name(self):
        card = AgentCard()
        self.assertEqual(card.name, "vinhlong360-knowledge-agent")


class TestDefaultSkills(unittest.TestCase):
    """Tests for DEFAULT_SKILLS list."""

    def test_skills_count(self):
        self.assertEqual(len(DEFAULT_SKILLS), 5)

    def test_each_skill_has_required_fields(self):
        for skill in DEFAULT_SKILLS:
            self.assertIsInstance(skill, AgentSkill)
            self.assertTrue(skill.id)
            self.assertTrue(skill.name)
            self.assertTrue(skill.description)

    def test_skill_to_dict_from_dict_roundtrip(self):
        skill = DEFAULT_SKILLS[0]
        d = skill.to_dict()
        restored = AgentSkill.from_dict(d)
        self.assertEqual(restored.id, skill.id)
        self.assertEqual(restored.name, skill.name)


class TestTaskManager(unittest.TestCase):
    """Tests for TaskManager."""

    def setUp(self):
        self.tm = TaskManager(max_tasks=5)

    def test_create_task(self):
        task = self.tm.create_task(
            input_message={"role": "user", "content": "Hello"},
        )
        self.assertIsInstance(task, A2ATask)
        self.assertEqual(task.state, TaskState.SUBMITTED)

    def test_get_task(self):
        task = self.tm.create_task(
            input_message={"role": "user", "content": "Test"},
        )
        fetched = self.tm.get_task(task.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.id, task.id)

    def test_get_task_not_found(self):
        self.assertIsNone(self.tm.get_task("nonexistent-id"))

    def test_update_task(self):
        task = self.tm.create_task(
            input_message={"role": "user", "content": "Test"},
        )
        self.tm.update_task(task.id, TaskState.WORKING)
        fetched = self.tm.get_task(task.id)
        self.assertEqual(fetched.state, TaskState.WORKING)

    def test_update_task_with_output(self):
        task = self.tm.create_task(
            input_message={"role": "user", "content": "Test"},
        )
        output = {"role": "agent", "content": "Done"}
        self.tm.update_task(task.id, TaskState.COMPLETED, output)
        fetched = self.tm.get_task(task.id)
        self.assertEqual(len(fetched.output_messages), 1)
        self.assertEqual(fetched.output_messages[0]["content"], "Done")

    def test_update_task_not_found_raises(self):
        with self.assertRaises(KeyError):
            self.tm.update_task("nonexistent", TaskState.WORKING)

    def test_cancel_task(self):
        task = self.tm.create_task(
            input_message={"role": "user", "content": "Cancel me"},
        )
        result = self.tm.cancel_task(task.id)
        self.assertTrue(result)
        fetched = self.tm.get_task(task.id)
        self.assertEqual(fetched.state, TaskState.CANCELED)

    def test_cancel_completed_task_returns_false(self):
        task = self.tm.create_task(
            input_message={"role": "user", "content": "Done"},
        )
        self.tm.update_task(task.id, TaskState.COMPLETED)
        result = self.tm.cancel_task(task.id)
        self.assertFalse(result)

    def test_cancel_nonexistent_returns_false(self):
        self.assertFalse(self.tm.cancel_task("does-not-exist"))

    def test_list_tasks(self):
        self.tm.create_task(input_message={"role": "user", "content": "1"}, session_id="s1")
        self.tm.create_task(input_message={"role": "user", "content": "2"}, session_id="s2")
        all_tasks = self.tm.list_tasks()
        self.assertEqual(len(all_tasks), 2)

    def test_list_tasks_filter_by_session(self):
        self.tm.create_task(input_message={"role": "user", "content": "1"}, session_id="s1")
        self.tm.create_task(input_message={"role": "user", "content": "2"}, session_id="s2")
        s1_tasks = self.tm.list_tasks(session_id="s1")
        self.assertEqual(len(s1_tasks), 1)

    def test_fifo_eviction(self):
        """When max_tasks is reached, oldest tasks should be evicted."""
        tm = TaskManager(max_tasks=3)
        ids = []
        for i in range(5):
            t = tm.create_task(input_message={"role": "user", "content": f"msg {i}"})
            ids.append(t.id)
        stats = tm.stats()
        self.assertLessEqual(stats["total"], 3)
        # The first two should have been evicted
        self.assertIsNone(tm.get_task(ids[0]))
        self.assertIsNone(tm.get_task(ids[1]))
        # The last ones should still exist
        self.assertIsNotNone(tm.get_task(ids[-1]))


class TestA2AServer(unittest.TestCase):
    """Tests for A2AServer."""

    def setUp(self):
        self.card = AgentCard()
        self.tm = TaskManager()
        self.server = A2AServer(card=self.card, manager=self.tm)

    def test_handle_well_known(self):
        resp = self.server.handle_request("GET", "/.well-known/agent.json", {})
        self.assertIn("name", resp)
        self.assertIn("endpoints", resp)

    def test_handle_tasks_send(self):
        resp = self.server.handle_request("POST", "/a2a", {
            "jsonrpc": "2.0",
            "method": "tasks/send",
            "params": {"message": {"role": "user", "content": "Hello agent"}},
            "id": "req-1",
        })
        self.assertEqual(resp["jsonrpc"], "2.0")
        self.assertEqual(resp["id"], "req-1")
        self.assertIn("result", resp)
        self.assertEqual(resp["result"]["state"], "completed")

    def test_handle_tasks_get(self):
        # Create a task first
        send_resp = self.server.handle_request("POST", "/a2a", {
            "jsonrpc": "2.0",
            "method": "tasks/send",
            "params": {"message": {"role": "user", "content": "Test"}},
            "id": "req-send",
        })
        task_id = send_resp["result"]["id"]

        # Now get it
        get_resp = self.server.handle_request("POST", "/a2a", {
            "jsonrpc": "2.0",
            "method": "tasks/get",
            "params": {"taskId": task_id},
            "id": "req-get",
        })
        self.assertEqual(get_resp["result"]["id"], task_id)

    def test_handle_invalid_method(self):
        resp = self.server.handle_request("POST", "/a2a", {
            "jsonrpc": "2.0",
            "method": "tasks/nonexistent",
            "params": {},
            "id": "req-err",
        })
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], -32601)

    def test_handle_missing_jsonrpc_version(self):
        resp = self.server.handle_request("POST", "/a2a", {
            "method": "tasks/send",
            "params": {},
            "id": "req-bad",
        })
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], -32600)

    def test_handle_tasks_send_missing_message(self):
        resp = self.server.handle_request("POST", "/a2a", {
            "jsonrpc": "2.0",
            "method": "tasks/send",
            "params": {},
            "id": "req-no-msg",
        })
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], -32602)


class TestConvenienceFunctions(unittest.TestCase):
    """Tests for module-level convenience functions."""

    def test_get_agent_card(self):
        card = get_agent_card()
        self.assertIsInstance(card, dict)
        self.assertEqual(card["@type"], "SoftwareAgent")
        self.assertIn("skills", card)

    def test_get_a2a_status(self):
        status = get_a2a_status()
        self.assertEqual(status["a2a_protocol"], "enabled")
        self.assertIn("agent", status)
        self.assertIn("version", status)
        self.assertIn("capabilities", status)
        self.assertIn("skills_count", status)
        self.assertIn("server", status)


class TestA2ATask(unittest.TestCase):
    """Tests for A2ATask dataclass."""

    def test_to_dict_from_dict_roundtrip(self):
        task = A2ATask(
            session_id="sess-1",
            input_message={"role": "user", "content": "Hello"},
        )
        d = task.to_dict()
        restored = A2ATask.from_dict(d)
        self.assertEqual(restored.id, task.id)
        self.assertEqual(restored.session_id, "sess-1")
        self.assertEqual(restored.state, TaskState.SUBMITTED)


if __name__ == "__main__":
    unittest.main()
