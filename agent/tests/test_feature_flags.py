"""Tests cho feature_flags.py — FeatureRegistry."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from feature_flags import FeatureRegistry  # noqa: E402


class TestFeatureRegistry:
    def test_register_and_available(self):
        r = FeatureRegistry()
        r.register("vector", True)
        assert r.available("vector") is True

    def test_available_default_false(self):
        r = FeatureRegistry()
        assert r.available("nonexistent") is False

    def test_all_returns_dict(self):
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
        r.register("x", True)
        r.register("x", False)
        assert r.available("x") is False

    def test_empty_registry(self):
        r = FeatureRegistry()
        assert r.all() == {}
        assert r.enabled() == []
        assert r.disabled() == []

    def test_all_returns_copy(self):
        r = FeatureRegistry()
        r.register("a", True)
        d = r.all()
        d["a"] = False
        assert r.available("a") is True
