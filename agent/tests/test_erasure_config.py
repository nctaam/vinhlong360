"""Configuration contracts for safe erasure scheduler activation."""

from __future__ import annotations

from config import Settings


def test_erasure_scheduler_defaults_are_audit_only_and_not_activated():
    fields = Settings.model_fields

    assert fields["ERASURE_AUDIT_ONLY"].default is True
    assert fields["ERASURE_ACTIVATION_ENABLED"].default is False
