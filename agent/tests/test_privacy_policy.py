import asyncio
import json
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

from privacy_policy import PrivacyPolicyError, load_privacy_policy, privacy_policy_readiness


POLICY = Path(__file__).resolve().parents[2] / "config" / "privacy-policy.json"


def test_committed_privacy_policy_has_approved_values():
    policy = load_privacy_policy(POLICY)
    assert policy.account_erasure_deadline_days == 30
    assert policy.recovery_enabled_during_grace_period is True
    assert policy.feedback_mode == "telemetry_only"
    assert policy.feedback_receipt_ttl_hours == 24
    assert policy.retain_deidentified_aggregates is True


@pytest.mark.parametrize(
    "payload",
    [
        '{"accountErasureDeadlineDays": 0, "extra": true}',
        (
            '{"accountErasureDeadlineDays": true,'
            '"recoveryEnabledDuringGracePeriod": true,'
            '"feedbackMode": "telemetry_only",'
            '"feedbackReceiptTtlHours": 24,'
            '"retainDeidentifiedAggregates": true}'
        ),
    ],
)
def test_policy_rejects_unknown_or_invalid_values(tmp_path, payload):
    path = tmp_path / "privacy-policy.json"
    path.write_text(payload, encoding="utf-8")
    with pytest.raises(PrivacyPolicyError):
        load_privacy_policy(path)


def test_readiness_rejects_runtime_policy_drift():
    matching = SimpleNamespace(
        ACCOUNT_ERASURE_DEADLINE_DAYS=30,
        RECOVERY_ENABLED_DURING_GRACE_PERIOD=True,
        FEEDBACK_MODE="telemetry_only",
        FEEDBACK_RECEIPT_TTL_HOURS=24,
        RETAIN_DEIDENTIFIED_AGGREGATES=True,
    )
    assert privacy_policy_readiness(matching) is True

    matching.ACCOUNT_ERASURE_DEADLINE_DAYS = 20
    assert privacy_policy_readiness(matching) is False


def test_backend_readiness_fails_when_runtime_policy_drifts(monkeypatch):
    import config
    import database
    import server

    @contextmanager
    def fake_conn():
        yield object()

    monkeypatch.setattr(server.knowledge, "_entities", {"sentinel": {}})
    monkeypatch.setattr(server.knowledge, "_data_source", "json")
    monkeypatch.setattr(database.db, "_conn", fake_conn)
    monkeypatch.setattr(database.db, "_fetchone", lambda *_args, **_kwargs: (1,))
    monkeypatch.setattr(database.db, "pg_schema_status", lambda: {"ok": True})
    monkeypatch.setattr(config.settings, "ACCOUNT_ERASURE_DEADLINE_DAYS", 20)

    response = asyncio.run(server.readiness_probe())
    payload = json.loads(response.body)

    assert response.status_code == 503
    assert payload["ready"] is False
    assert payload["checks"]["privacy_policy"] is False
