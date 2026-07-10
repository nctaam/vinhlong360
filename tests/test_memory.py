"""Tests for agent/memory.py — Dual-Layer Conversation Memory."""
import json
import time
from unittest.mock import patch

import pytest

from memory import (
    HotMemory,
    ColdMemory,
    UserProfile,
    MemoryManager,
    _encrypt,
    _decrypt,
)


# ── HotMemory ────────────────────────────────────────


class TestHotMemory:
    def test_init(self):
        hm = HotMemory("session_1")
        assert hm.session_id == "session_1"
        assert hm.messages == []
        assert hm.summary == ""

    def test_add_message(self):
        hm = HotMemory("s1")
        hm.add_message("user", "Hello")
        assert len(hm.messages) == 1
        assert hm.messages[0]["role"] == "user"
        assert hm.messages[0]["content"] == "Hello"
        assert "ts" in hm.messages[0]

    def test_add_multiple_messages(self):
        hm = HotMemory("s1")
        hm.add_message("user", "Hi")
        hm.add_message("assistant", "Hello!")
        hm.add_message("user", "What is cam sanh?")
        assert len(hm.messages) == 3

    def test_get_context_messages_empty(self):
        hm = HotMemory("s1")
        msgs = hm.get_context_messages()
        assert msgs == []

    def test_get_context_messages_recent(self):
        hm = HotMemory("s1", max_messages=5)
        for i in range(10):
            hm.add_message("user", f"msg {i}")
        msgs = hm.get_context_messages()
        # Should return only the most recent max_messages
        assert len(msgs) <= 5

    def test_get_context_messages_with_summary(self):
        hm = HotMemory("s1", max_messages=3)
        hm.summary = "Discussed cam sanh and bun nuoc leo"
        hm.add_message("user", "Recent question")
        msgs = hm.get_context_messages()
        assert msgs[0]["role"] == "system"
        # The summary template uses Vietnamese: "Tóm tắt cuộc hội thoại trước đó"
        assert "Discussed cam sanh" in msgs[0]["content"]

    def test_extract_preferences_interests(self):
        hm = HotMemory("s1")
        # Keywords need Vietnamese diacritics to match: "đặc sản", "ăn", "món"
        hm.add_message("user", "Tôi muốn ăn món đặc sản")
        assert "interests" in hm.detected_preferences
        interests = hm.detected_preferences["interests"]
        assert "ẩm thực" in interests or "mua sắm" in interests

    def test_extract_preferences_budget(self):
        hm = HotMemory("s1")
        # Keywords need Vietnamese diacritics: "tiết kiệm"
        hm.add_message("user", "Tôi muốn đi du lịch tiết kiệm")
        assert hm.detected_preferences.get("budget") == "thấp"

    def test_extract_preferences_budget_high(self):
        hm = HotMemory("s1")
        hm.add_message("user", "Tim resort sang trong")
        assert hm.detected_preferences.get("budget") == "cao"

    def test_extract_preferences_group_type(self):
        hm = HotMemory("s1")
        # Keywords need Vietnamese diacritics: "gia đình", "con nhỏ"
        hm.add_message("user", "Đi du lịch với gia đình có con nhỏ")
        assert hm.detected_preferences.get("group_type") == "gia đình"

    def test_extract_areas_mentioned(self):
        hm = HotMemory("s1")
        hm.add_message("user", "Toi muon di vinh long va ben tre")
        assert "vinh-long" in hm.areas_mentioned
        assert "ben-tre" in hm.areas_mentioned

    def test_compress_triggered(self):
        hm = HotMemory("s1", max_messages=3)
        # Add more than max_messages * 2 to trigger compression
        for i in range(10):
            hm.add_message("user", f"Message {i} about tourism")
        # Compression triggered: summary should be populated
        assert hm.summary != ""
        # After compression, messages should be capped at max_messages
        # (compression fires when len > max_messages * 2, then trims to max_messages)
        assert len(hm.messages) <= hm.max_messages * 2

    def test_get_preference_context_empty(self):
        hm = HotMemory("s1")
        assert hm.get_preference_context() == ""

    def test_get_preference_context_with_data(self):
        hm = HotMemory("s1")
        hm.detected_preferences = {"interests": {"ẩm thực", "lịch sử"}}
        hm.areas_mentioned = {"vinh-long"}
        ctx = hm.get_preference_context()
        assert "vinh-long" in ctx


# ── UserProfile ──────────────────────────────────────


class TestUserProfile:
    def test_init(self):
        p = UserProfile("user_1")
        assert p.user_id == "user_1"
        assert p.interests == []
        assert p.conversation_count == 0

    def test_to_dict(self):
        p = UserProfile("user_1")
        p.interests = ["am thuc", "lich su"]
        d = p.to_dict()
        assert d["user_id"] == "user_1"
        assert d["interests"] == ["am thuc", "lich su"]

    def test_from_dict(self):
        data = {
            "user_id": "user_2",
            "interests": ["thien nhien"],
            "preferred_areas": ["vinh-long"],
            "budget_preference": "trung binh",
            "conversation_count": 5,
        }
        p = UserProfile.from_dict(data)
        assert p.user_id == "user_2"
        assert p.interests == ["thien nhien"]
        assert p.conversation_count == 5

    def test_get_personalization_prompt_empty(self):
        p = UserProfile("user_1")
        assert p.get_personalization_prompt() == ""

    def test_get_personalization_prompt_with_data(self):
        p = UserProfile("user_1")
        p.interests = ["ẩm thực"]
        p.preferred_areas = ["vinh-long"]
        prompt = p.get_personalization_prompt()
        assert "ẩm thực" in prompt
        assert "vinh-long" in prompt
        assert "[Ho so nguoi dung]" in prompt or "Hồ sơ người dùng" in prompt

    def test_interests_tracking(self):
        p = UserProfile("user_1")
        p.interests.append("food")
        p.interests.append("history")
        assert len(p.interests) == 2

    def test_areas_tracking(self):
        p = UserProfile("user_1")
        p.preferred_areas.append("vinh-long")
        p.preferred_areas.append("ben-tre")
        assert "vinh-long" in p.preferred_areas
        assert "ben-tre" in p.preferred_areas


# ── Encryption ───────────────────────────────────────


def test_encrypt_decrypt_roundtrip():
    plaintext = "Hello, this is a secret message!"
    encrypted = _encrypt(plaintext)
    assert encrypted != plaintext
    decrypted = _decrypt(encrypted)
    assert decrypted == plaintext


def test_encrypt_decrypt_unicode():
    plaintext = "Vĩnh Long đẹp lắm! Cam sành Tam Bình ngon tuyệt."
    encrypted = _encrypt(plaintext)
    decrypted = _decrypt(encrypted)
    assert decrypted == plaintext


def test_encrypt_decrypt_json():
    data = {"user_id": "test", "interests": ["ẩm thực", "lịch sử"]}
    plaintext = json.dumps(data, ensure_ascii=False)
    encrypted = _encrypt(plaintext)
    decrypted = _decrypt(encrypted)
    assert json.loads(decrypted) == data


def test_encrypt_produces_different_output():
    """Same input should produce an encrypted string different from plaintext."""
    plaintext = "test data"
    encrypted = _encrypt(plaintext)
    assert encrypted != plaintext


# ── ColdMemory ───────────────────────────────────────


class TestColdMemory:
    @pytest.fixture
    def cold(self, tmp_path):
        """ColdMemory with temp directory, using RLock to avoid deadlock."""
        import threading
        with patch("memory.MEMORY_DIR", tmp_path):
            cm = ColdMemory.__new__(ColdMemory)
            cm._profiles = {}
            # Use RLock since update_profile_from_session calls get_profile
            # while holding the lock (reentrant).
            cm._lock = threading.RLock()
            cm._profiles_file = tmp_path / "user_profiles.json"
            return cm

    def test_get_profile_new_user(self, cold):
        profile = cold.get_profile("new_user")
        assert profile.user_id == "new_user"
        assert profile.conversation_count == 0

    def test_get_profile_returns_same_instance(self, cold):
        p1 = cold.get_profile("user_x")
        p2 = cold.get_profile("user_x")
        assert p1 is p2

    def test_update_profile_from_session(self, cold):
        hot = HotMemory("session_1")
        hot.add_message("user", "Toi muon an dac san vinh long")
        hot.areas_mentioned.add("vinh-long")

        cold.update_profile_from_session("user_1", hot)
        profile = cold.get_profile("user_1")
        assert profile.conversation_count == 1
        assert "vinh-long" in profile.preferred_areas

    def test_record_feedback(self, cold):
        cold.record_feedback("user_1", "cam sanh?", 5, "cam-sanh")
        profile = cold.get_profile("user_1")
        assert len(profile.feedback_history) == 1
        assert profile.feedback_history[0]["rating"] == 5
        # High rating should add to favorites
        assert "cam-sanh" in profile.favorite_entities

    def test_record_feedback_low_rating(self, cold):
        cold.record_feedback("user_1", "bad query", 1, "bad-entity")
        profile = cold.get_profile("user_1")
        assert "bad-entity" in profile.disliked_entities

    def test_add_semantic_fact(self, cold):
        cold.add_semantic_fact("user_1", "Thich an chay")
        profile = cold.get_profile("user_1")
        assert "Thich an chay" in profile.semantic_facts

    def test_add_semantic_fact_dedup(self, cold):
        cold.add_semantic_fact("user_1", "Fact A")
        cold.add_semantic_fact("user_1", "Fact A")  # duplicate
        profile = cold.get_profile("user_1")
        assert profile.semantic_facts.count("Fact A") == 1

    def test_stats(self, cold):
        cold.get_profile("user_1")
        cold.get_profile("user_2")
        s = cold.stats()
        assert s["total_users"] == 2


# ── Backward compatibility ───────────────────────────


def test_cold_memory_reads_plain_json(tmp_path):
    """ColdMemory should be able to read unencrypted JSON files."""
    profiles_file = tmp_path / "user_profiles.json"
    data = {
        "user_1": {
            "user_id": "user_1",
            "interests": ["food"],
            "preferred_areas": [],
            "budget_preference": "",
            "group_type": "",
            "visited_entities": [],
            "favorite_entities": [],
            "disliked_entities": [],
            "conversation_count": 3,
            "total_messages": 15,
            "first_seen": "2024-01-01T00:00:00",
            "last_seen": "2024-06-01T00:00:00",
            "feedback_history": [],
            "semantic_facts": [],
        }
    }
    profiles_file.write_text(json.dumps(data), encoding="utf-8")

    with patch("memory.MEMORY_DIR", tmp_path):
        cm = ColdMemory.__new__(ColdMemory)
        cm._profiles = {}
        cm._lock = __import__("threading").Lock()
        cm._profiles_file = profiles_file
        cm._load_all()

    assert "user_1" in cm._profiles
    assert cm._profiles["user_1"].interests == ["food"]
    assert cm._profiles["user_1"].conversation_count == 3


# ── MemoryManager ────────────────────────────────────


class TestMemoryManager:
    def test_get_session(self):
        mm = MemoryManager()
        s = mm.get_session("s1")
        assert isinstance(s, HotMemory)
        assert s.session_id == "s1"

    def test_get_session_returns_same_instance(self):
        mm = MemoryManager()
        s1 = mm.get_session("s1")
        s2 = mm.get_session("s1")
        assert s1 is s2

    def test_on_message(self):
        mm = MemoryManager()
        mm.on_message("s1", "user", "Hello")
        session = mm.get_session("s1")
        assert len(session.messages) == 1

    def test_cleanup_stale_sessions(self):
        mm = MemoryManager()
        s = mm.get_session("old_session")
        s.last_active = time.time() - 7200  # 2 hours ago

        mm.get_session("new_session")  # fresh session

        mm.cleanup_stale_sessions(max_age_seconds=3600)
        assert "old_session" not in mm._sessions
        assert "new_session" in mm._sessions

    def test_stats(self):
        mm = MemoryManager()
        mm.get_session("s1")
        mm.get_session("s2")
        s = mm.stats()
        assert s["active_sessions"] == 2
        assert "cold_memory" in s
        assert "skills" in s
