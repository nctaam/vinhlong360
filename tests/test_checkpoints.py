"""Tests for agent/checkpoints.py -- Checkpoint & Confirmation managers."""

import json
import sys
import time
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agent"))

from checkpoints import (
    CheckpointManager,
    ConfirmationManager,
    ConversationCheckpoint,
    PendingConfirmation,
    needs_confirmation,
    format_confirmation_prompt,
    CONFIRMATION_EXPIRY_SECONDS,
)


# ---- Fixtures ----


@pytest.fixture()
def cp_manager(tmp_path):
    """CheckpointManager backed by a temp directory."""
    return CheckpointManager(directory=tmp_path / "checkpoints")


@pytest.fixture()
def cf_manager(tmp_path):
    """ConfirmationManager backed by a temp directory."""
    return ConfirmationManager(directory=tmp_path / "confirmations")


# ---- CheckpointManager ----


class TestSaveAndLoad:
    def test_save_returns_checkpoint_id(self, cp_manager):
        cp_id = cp_manager.save_checkpoint(
            session_id="s1",
            messages=[{"role": "user", "content": "hello"}],
            tools_used=["search"],
            agent_state={"round": 1},
        )
        assert cp_id.startswith("cp_")

    def test_load_restores_data(self, cp_manager):
        messages = [
            {"role": "user", "content": "Cho toi lich trinh"},
            {"role": "assistant", "content": "Day la lich trinh..."},
        ]
        tools = ["search", "generate_itinerary"]
        state = {"round_num": 3, "status": "active"}
        metadata = {"query_type": "itinerary"}

        cp_id = cp_manager.save_checkpoint("s1", messages, tools, state, metadata)
        loaded = cp_manager.load_checkpoint(cp_id)

        assert loaded is not None
        assert loaded.session_id == "s1"
        assert loaded.messages == messages
        assert loaded.tools_used == tools
        assert loaded.agent_state == state
        assert loaded.metadata == metadata

    def test_load_nonexistent_returns_none(self, cp_manager):
        assert cp_manager.load_checkpoint("cp_nonexistent") is None


class TestListCheckpoints:
    def test_returns_correct_session(self, cp_manager):
        cp_manager.save_checkpoint("s1", [{"role": "user", "content": "a"}], [], {})
        cp_manager.save_checkpoint("s1", [{"role": "user", "content": "b"}], [], {})
        cp_manager.save_checkpoint("s2", [{"role": "user", "content": "c"}], [], {})

        listing = cp_manager.list_checkpoints("s1")
        assert len(listing) == 2
        for item in listing:
            assert item["session_id"] == "s1"

    def test_includes_summary_fields(self, cp_manager):
        cp_manager.save_checkpoint(
            "s1",
            [{"role": "user", "content": "x"}],
            ["search", "weather"],
            {"r": 1},
        )
        listing = cp_manager.list_checkpoints("s1")
        assert len(listing) == 1
        item = listing[0]
        assert "checkpoint_id" in item
        assert item["message_count"] == 1
        assert item["tools_count"] == 2

    def test_sorted_newest_first(self, cp_manager):
        cp_manager.save_checkpoint("s1", [], [], {})
        time.sleep(0.05)
        cp_manager.save_checkpoint("s1", [], [], {})
        listing = cp_manager.list_checkpoints("s1")
        assert listing[0]["timestamp"] >= listing[1]["timestamp"]


class TestResumeFrom:
    def test_returns_messages_and_state(self, cp_manager):
        messages = [{"role": "user", "content": "resume me"}]
        state = {"round": 5, "pending": []}
        cp_id = cp_manager.save_checkpoint("s1", messages, [], state)

        result = cp_manager.resume_from(cp_id)
        assert result is not None
        msgs, st = result
        assert msgs == messages
        assert st == state

    def test_returns_none_for_missing(self, cp_manager):
        assert cp_manager.resume_from("cp_missing") is None


class TestDeleteCheckpoint:
    def test_removes_checkpoint(self, cp_manager):
        cp_id = cp_manager.save_checkpoint("s1", [], [], {})
        assert cp_manager.delete_checkpoint(cp_id) is True
        assert cp_manager.load_checkpoint(cp_id) is None

    def test_returns_false_for_missing(self, cp_manager):
        assert cp_manager.delete_checkpoint("cp_nope") is False


class TestCleanupOld:
    def test_removes_old_checkpoints(self, cp_manager):
        # Save a checkpoint and backdate its timestamp
        cp_id = cp_manager.save_checkpoint("s1", [], [], {})
        # Manually backdate the file
        path = cp_manager._path(cp_id)
        data = json.loads(path.read_text(encoding="utf-8"))
        data["timestamp"] = time.time() - 100_000  # way older than 24h
        path.write_text(json.dumps(data), encoding="utf-8")

        removed = cp_manager.cleanup_old(max_age_hours=24)
        assert removed == 1


# ---- ConfirmationManager ----


class TestCreateAndConfirm:
    def test_create_returns_pending(self, cf_manager):
        cf = cf_manager.create_confirmation(
            session_id="s1",
            action_type="itinerary",
            description="Test itinerary",
            params={"days": 2, "budget": "cao"},
        )
        assert cf.status == "pending"
        assert cf.confirmation_id.startswith("cf_")
        assert cf.action_type == "itinerary"

    def test_confirm_returns_params(self, cf_manager):
        cf = cf_manager.create_confirmation("s1", "itinerary", "test", {"days": 2})
        params = cf_manager.confirm(cf.confirmation_id)
        assert params is not None
        assert params["days"] == 2

    def test_confirm_sets_status(self, cf_manager):
        cf = cf_manager.create_confirmation("s1", "itinerary", "test", {"days": 1})
        cf_manager.confirm(cf.confirmation_id)
        assert cf_manager.is_confirmed(cf.confirmation_id) is True

    def test_double_confirm_returns_none(self, cf_manager):
        cf = cf_manager.create_confirmation("s1", "itinerary", "test", {})
        cf_manager.confirm(cf.confirmation_id)
        assert cf_manager.confirm(cf.confirmation_id) is None


class TestCreateAndReject:
    def test_reject_returns_true(self, cf_manager):
        cf = cf_manager.create_confirmation("s1", "rec", "test", {})
        assert cf_manager.reject(cf.confirmation_id, reason="Too many") is True

    def test_rejected_not_confirmed(self, cf_manager):
        cf = cf_manager.create_confirmation("s1", "rec", "test", {})
        cf_manager.reject(cf.confirmation_id)
        assert cf_manager.is_confirmed(cf.confirmation_id) is False

    def test_reject_missing_returns_false(self, cf_manager):
        assert cf_manager.reject("cf_missing") is False

    def test_reject_already_confirmed_returns_false(self, cf_manager):
        cf = cf_manager.create_confirmation("s1", "rec", "test", {})
        cf_manager.confirm(cf.confirmation_id)
        assert cf_manager.reject(cf.confirmation_id) is False


class TestGetPending:
    def test_returns_only_active_confirmations(self, cf_manager):
        cf1 = cf_manager.create_confirmation("s1", "a", "desc1", {})
        cf2 = cf_manager.create_confirmation("s1", "b", "desc2", {})
        cf_manager.confirm(cf1.confirmation_id)  # no longer pending

        pending = cf_manager.get_pending("s1")
        ids = [p.confirmation_id for p in pending]
        assert cf1.confirmation_id not in ids
        assert cf2.confirmation_id in ids

    def test_filters_by_session(self, cf_manager):
        cf_manager.create_confirmation("s1", "a", "desc", {})
        cf_manager.create_confirmation("s2", "b", "desc", {})
        pending = cf_manager.get_pending("s1")
        assert all(p.session_id == "s1" for p in pending)


class TestExpiredConfirmation:
    def test_expired_confirmation_returns_none_on_confirm(self, cf_manager):
        cf = cf_manager.create_confirmation("s1", "itinerary", "test", {"days": 1})
        # Manually backdate the expiry
        path = cf_manager._path(cf.confirmation_id)
        data = json.loads(path.read_text(encoding="utf-8"))
        data["expires_at"] = time.time() - 10  # already expired
        path.write_text(json.dumps(data), encoding="utf-8")

        result = cf_manager.confirm(cf.confirmation_id)
        assert result is None

    def test_pending_confirmation_is_expired_property(self):
        cf = PendingConfirmation(
            confirmation_id="cf_test",
            session_id="s1",
            action_type="test",
            description="test",
            params={},
            created_at=time.time() - 600,
            expires_at=time.time() - 100,
        )
        assert cf.is_expired is True

    def test_fresh_confirmation_not_expired(self):
        cf = PendingConfirmation(
            confirmation_id="cf_fresh",
            session_id="s1",
            action_type="test",
            description="test",
            params={},
            created_at=time.time(),
        )
        assert cf.is_expired is False


class TestCleanupExpired:
    def test_removes_old_confirmations(self, cf_manager):
        cf = cf_manager.create_confirmation("s1", "a", "desc", {})
        # Backdate expires_at so is_expired returns True (status stays "pending")
        path = cf_manager._path(cf.confirmation_id)
        data = json.loads(path.read_text(encoding="utf-8"))
        data["created_at"] = time.time() - 7200  # 2 hours ago
        data["expires_at"] = time.time() - 7000   # already past
        # status stays "pending" so is_expired property returns True
        path.write_text(json.dumps(data), encoding="utf-8")

        removed = cf_manager.cleanup_expired()
        assert removed >= 1


# ---- needs_confirmation ----


class TestNeedsConfirmation:
    def test_itinerary_with_budget_true(self):
        assert needs_confirmation("itinerary", {"budget": "cao"}) is True

    def test_itinerary_without_budget_false(self):
        assert needs_confirmation("itinerary", {}) is False

    def test_itinerary_empty_budget_false(self):
        assert needs_confirmation("itinerary", {"budget": ""}) is False

    def test_recommendation_all_areas_true(self):
        assert needs_confirmation("recommendation", {"areas": "all"}) is True

    def test_recommendation_specific_area_false(self):
        assert needs_confirmation("recommendation", {"areas": "vinh-long"}) is False

    def test_recommendation_tat_ca_true(self):
        assert needs_confirmation("recommendation", {"area": "tất cả"}) is True

    def test_search_results_over_10_true(self):
        assert needs_confirmation("search_results", {"result_count": 15}) is True

    def test_search_results_under_10_false(self):
        assert needs_confirmation("search_results", {"result_count": 5}) is False

    def test_weather_dependent_true(self):
        assert needs_confirmation("weather_dependent", {"weather_dependent": True}) is True

    def test_weather_dependent_false(self):
        assert needs_confirmation("weather_dependent", {"weather_dependent": False}) is False

    def test_unknown_action_false(self):
        assert needs_confirmation("totally_unknown", {"anything": True}) is False


# ---- format_confirmation_prompt ----


class TestFormatConfirmationPrompt:
    def _make_confirmation(self, action_type, description, params):
        return PendingConfirmation(
            confirmation_id="cf_test",
            session_id="s1",
            action_type=action_type,
            description=description,
            params=params,
            created_at=time.time(),
        )

    def test_itinerary_prompt(self):
        cf = self._make_confirmation("itinerary", "Tao lich trinh", {
            "days": 2, "areas": ["vinh-long"], "budget": "cao",
            "interests": ["am_thuc"], "month": 12,
        })
        prompt = format_confirmation_prompt(cf)
        assert isinstance(prompt, str)
        assert "lich trinh" in prompt.lower()
        assert "2" in prompt

    def test_recommendation_prompt(self):
        cf = self._make_confirmation("recommendation", "Goi y diem den", {
            "areas": "all", "limit": 20,
        })
        prompt = format_confirmation_prompt(cf)
        assert "goi y" in prompt.lower()

    def test_search_results_prompt(self):
        cf = self._make_confirmation("search_results", "Tim kiem chua", {
            "result_count": 25,
        })
        prompt = format_confirmation_prompt(cf)
        assert "25" in prompt

    def test_weather_prompt(self):
        cf = self._make_confirmation("weather_dependent", "Goi y ngoai troi", {
            "weather_dependent": True,
        })
        prompt = format_confirmation_prompt(cf)
        assert "thoi tiet" in prompt.lower()

    def test_unknown_type_fallback(self):
        cf = self._make_confirmation("custom", "Custom action", {"x": 1})
        prompt = format_confirmation_prompt(cf)
        assert "custom" in prompt.lower()

    def test_prompt_is_nonempty_string(self):
        cf = self._make_confirmation("itinerary", "test", {"days": 1})
        prompt = format_confirmation_prompt(cf)
        assert len(prompt) > 10


# ---- ConversationCheckpoint dataclass ----


class TestConversationCheckpoint:
    def test_to_dict_roundtrip(self):
        cp = ConversationCheckpoint(
            checkpoint_id="cp_abc",
            session_id="s1",
            timestamp=time.time(),
            messages=[{"role": "user", "content": "hi"}],
            tools_used=["search"],
            agent_state={"round": 1},
            metadata={"note": "test"},
        )
        d = cp.to_dict()
        restored = ConversationCheckpoint.from_dict(d)
        assert restored.checkpoint_id == "cp_abc"
        assert restored.messages == cp.messages
        assert restored.agent_state == cp.agent_state
        assert restored.metadata == {"note": "test"}
