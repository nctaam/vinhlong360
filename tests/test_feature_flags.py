"""Tests for feature flag registry."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

from feature_flags import FeatureRegistry


class TestFeatureRegistry:
    def test_register_and_available(self):
        r = FeatureRegistry()
        r.register("vector", True)
        assert r.available("vector") is True

    def test_unavailable_default(self):
        r = FeatureRegistry()
        assert r.available("nonexistent") is False

    def test_register_disabled(self):
        r = FeatureRegistry()
        r.register("redis", False)
        assert r.available("redis") is False

    def test_all(self):
        r = FeatureRegistry()
        r.register("a", True)
        r.register("b", False)
        assert r.all() == {"a": True, "b": False}

    def test_enabled_list(self):
        r = FeatureRegistry()
        r.register("a", True)
        r.register("b", False)
        r.register("c", True)
        assert sorted(r.enabled()) == ["a", "c"]

    def test_disabled_list(self):
        r = FeatureRegistry()
        r.register("a", True)
        r.register("b", False)
        assert r.disabled() == ["b"]

    def test_overwrite_flag(self):
        r = FeatureRegistry()
        r.register("flag", True)
        r.register("flag", False)
        assert r.available("flag") is False

    def test_empty_registry(self):
        r = FeatureRegistry()
        assert r.all() == {}
        assert r.enabled() == []
        assert r.disabled() == []
