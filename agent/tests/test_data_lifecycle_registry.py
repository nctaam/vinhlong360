"""Lifecycle registry completeness and safe diagnostics contracts."""

from __future__ import annotations

import asyncio
import json
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path

import data_lifecycle


EXPECTED_SUBJECT_STORES = {
    "hot_memory",
    "cold_memory",
    "memory_graph",
    "exact_cache",
    "semantic_cache",
    "semantic_leases",
    "pending_feedback_receipts",
    "feedback_receipts",
    "owner_analytics",
    "conversation_history",
    "guardrail_budget",
    "cost_attribution",
    "optimizer_records",
    "experience_memory",
    "prompt_demonstrations",
    "ab_outcomes",
}

IMMEDIATE_STORES = {
    "hot_memory",
    "exact_cache",
    "semantic_cache",
    "semantic_leases",
    "pending_feedback_receipts",
}


def test_registry_declares_every_subject_linked_store_once():
    policies = data_lifecycle.lifecycle_registry.policies
    names = [policy.name for policy in policies]

    assert len(names) == len(set(names))
    assert {
        policy.name for policy in policies if policy.subject_linked
    } == EXPECTED_SUBJECT_STORES
    assert data_lifecycle.validate_lifecycle_registry() == ()


def test_registry_rejects_a_missing_personal_adapter():
    incomplete = tuple(
        policy
        for policy in data_lifecycle.lifecycle_registry.policies
        if policy.name != "cold_memory"
    )

    errors = data_lifecycle.validate_lifecycle_registry(incomplete)

    assert errors == ("MISSING_SUBJECT_STORE:cold_memory",)


def test_registry_honors_an_explicit_empty_policy_set():
    errors = data_lifecycle.validate_lifecycle_registry(())

    assert "MISSING_SUBJECT_STORE:cold_memory" in errors
    assert "MISSING_QUARANTINE_STORE:hot_memory" in errors


def test_quarantine_phase_contains_only_ephemeral_personal_stores():
    policies = data_lifecycle.lifecycle_registry.policies
    immediate = {
        policy.name for policy in policies if policy.quarantine_on_request
    }

    assert immediate == IMMEDIATE_STORES
    assert not {
        "cold_memory",
        "memory_graph",
        "owner_analytics",
        "conversation_history",
        "guardrail_budget",
        "cost_attribution",
        "optimizer_records",
        "experience_memory",
        "prompt_demonstrations",
        "ab_outcomes",
    } & immediate


def test_subject_stores_have_purge_and_verify_adapters():
    for policy in data_lifecycle.lifecycle_registry.policies:
        if not policy.subject_linked:
            continue
        assert callable(policy.purge), policy.name
        assert callable(policy.verify), policy.name


def test_retained_aggregate_and_operational_policies_are_non_subject():
    policies = {
        policy.name: policy for policy in data_lifecycle.lifecycle_registry.policies
    }

    for name in (
        "deidentified_daily_rollups",
        "public_entity_popularity",
        "post_boundary_operational_logs",
    ):
        policy = policies[name]
        assert policy.classification in {"aggregate", "operational"}
        assert policy.subject_linked is False
        assert policy.retained_fields

    forbidden = {
        "owner_key",
        "user_id",
        "session_id",
        "query",
        "response",
        "receipt",
    }
    for name in ("deidentified_daily_rollups", "post_boundary_operational_logs"):
        assert forbidden.isdisjoint(policies[name].retained_fields)


def test_registry_rejects_subject_fields_in_retained_operational_data():
    policies = tuple(
        replace(policy, retained_fields=("event_code", "entity_id"))
        if policy.name == "post_boundary_operational_logs"
        else policy
        for policy in data_lifecycle.lifecycle_registry.policies
    )

    assert data_lifecycle.validate_lifecycle_registry(policies) == (
        "SUBJECT_FIELD_IN_RETAINED_STORE:post_boundary_operational_logs",
    )


def test_residual_verification_is_not_safe_for_hard_erasure():
    result = data_lifecycle.VerificationResult(
        store_name="cold_memory",
        absent=False,
        residual_count=1,
    )

    assert result.verified is False


def test_readiness_exposes_only_stable_registry_metadata():
    readiness = data_lifecycle.lifecycle_registry_readiness()
    encoded = json.dumps(readiness, sort_keys=True)

    assert readiness["ok"] is True
    assert readiness["store_count"] == len(
        data_lifecycle.lifecycle_registry.policies
    )
    assert set(readiness["stores"][0]) == {
        "name",
        "classification",
        "status",
    }
    assert "user:" not in encoded
    assert str(Path.cwd()) not in encoded


def test_server_readiness_wires_registry_check():
    source = Path(data_lifecycle.__file__).with_name("server.py").read_text(
        encoding="utf-8"
    )

    assert 'checks["lifecycle_registry"] = lifecycle_registry_readiness()' in source


def test_server_readiness_fails_when_lifecycle_registry_is_invalid(monkeypatch):
    import database
    import server

    @contextmanager
    def fake_conn():
        yield object()

    monkeypatch.setattr(server.knowledge, "_entities", {"sentinel": {}})
    monkeypatch.setattr(server.knowledge, "_data_source", "json")
    monkeypatch.setattr(server, "privacy_boundary_readiness", lambda: True)
    monkeypatch.setattr(database.db, "_conn", fake_conn)
    monkeypatch.setattr(database.db, "_fetchone", lambda *_args, **_kwargs: (1,))
    monkeypatch.setattr(database.db, "pg_schema_status", lambda: {"ok": True})
    monkeypatch.setattr(
        data_lifecycle,
        "lifecycle_registry_readiness",
        lambda: {"ok": False, "errors": ["MISSING_ADAPTER:cold_memory"]},
    )

    response = asyncio.run(server.readiness_probe())
    payload = json.loads(response.body)

    assert response.status_code == 503
    assert payload["ready"] is False
    assert payload["checks"]["lifecycle_registry"]["ok"] is False
