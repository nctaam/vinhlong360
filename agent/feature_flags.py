"""Centralized feature flag registry.

Collects all HAS_* flags into a single queryable registry.
Usage in server.py:
    from feature_flags import features
    features.register("vector", HAS_VECTOR)
    features.available("vector")  # -> bool
    features.all()                # -> dict[str, bool]
"""


class FeatureRegistry:
    def __init__(self):
        self._flags: dict[str, bool] = {}

    def register(self, name: str, enabled: bool):
        self._flags[name] = enabled

    def available(self, name: str) -> bool:
        return self._flags.get(name, False)

    def all(self) -> dict[str, bool]:
        return dict(self._flags)

    def enabled(self) -> list[str]:
        return [k for k, v in self._flags.items() if v]

    def disabled(self) -> list[str]:
        return [k for k, v in self._flags.items() if not v]


features = FeatureRegistry()
