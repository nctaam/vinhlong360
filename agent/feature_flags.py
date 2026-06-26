"""Centralized feature flag registry.

Collects all HAS_* flags into a single queryable registry.
Supports env-var overrides: FEATURE_<NAME>=true/false overrides code registration.

Usage in server.py:
    from feature_flags import features
    features.register("vector", HAS_VECTOR)
    features.available("vector")  # -> bool (checks env FEATURE_VECTOR first)
    features.all()                # -> dict[str, bool]
"""

import os
from threading import Lock


class FeatureRegistry:
    def __init__(self):
        self._flags: dict[str, bool] = {}
        self._lock = Lock()

    def register(self, name: str, enabled: bool):
        with self._lock:
            self._flags[name] = enabled

    def available(self, name: str) -> bool:
        env_val = os.environ.get(f"FEATURE_{name.upper()}")
        if env_val is not None:
            return env_val.strip().lower() in ("1", "true", "yes", "on")
        with self._lock:
            return self._flags.get(name, False)

    def all(self) -> dict[str, bool]:
        with self._lock:
            base = dict(self._flags)
        for name in base:
            env_val = os.environ.get(f"FEATURE_{name.upper()}")
            if env_val is not None:
                base[name] = env_val.strip().lower() in ("1", "true", "yes", "on")
        return base

    def enabled(self) -> list[str]:
        return [k for k, v in self.all().items() if v]

    def disabled(self) -> list[str]:
        return [k for k, v in self.all().items() if not v]


features = FeatureRegistry()
