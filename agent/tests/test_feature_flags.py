"""Tests cho feature_flags.py — FeatureRegistry + env-var override."""

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


class TestEnvVarOverride:
    def test_env_overrides_registered_false(self, monkeypatch):
        r = FeatureRegistry()
        r.register("vector", False)
        monkeypatch.setenv("FEATURE_VECTOR", "true")
        assert r.available("vector") is True

    def test_env_overrides_registered_true(self, monkeypatch):
        r = FeatureRegistry()
        r.register("vector", True)
        monkeypatch.setenv("FEATURE_VECTOR", "false")
        assert r.available("vector") is False

    def test_env_overrides_unregistered(self, monkeypatch):
        r = FeatureRegistry()
        monkeypatch.setenv("FEATURE_MAGIC", "1")
        assert r.available("magic") is True

    def test_env_case_insensitive_values(self, monkeypatch):
        r = FeatureRegistry()
        r.register("x", False)
        for val in ("TRUE", "True", "1", "yes", "on"):
            monkeypatch.setenv("FEATURE_X", val)
            assert r.available("x") is True, f"Failed for {val}"

    def test_env_false_values(self, monkeypatch):
        r = FeatureRegistry()
        r.register("x", True)
        for val in ("false", "0", "no", "off", "anything"):
            monkeypatch.setenv("FEATURE_X", val)
            assert r.available("x") is False, f"Failed for {val}"

    def test_all_reflects_env_override(self, monkeypatch):
        r = FeatureRegistry()
        r.register("a", True)
        r.register("b", False)
        monkeypatch.setenv("FEATURE_B", "true")
        result = r.all()
        assert result == {"a": True, "b": True}

    def test_enabled_with_env_override(self, monkeypatch):
        r = FeatureRegistry()
        r.register("a", True)
        r.register("b", False)
        monkeypatch.setenv("FEATURE_B", "1")
        assert sorted(r.enabled()) == ["a", "b"]


class TestThreadSafety:
    def test_concurrent_register(self):
        import threading
        r = FeatureRegistry()
        errors = []

        def register_batch(prefix, count):
            try:
                for i in range(count):
                    r.register(f"{prefix}_{i}", True)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=register_batch, args=(f"t{t}", 100)) for t in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert len(r.all()) == 400
