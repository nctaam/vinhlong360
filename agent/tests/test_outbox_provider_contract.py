"""Static contract checks for the provider/outbox ambiguity boundary."""

from pathlib import Path

import database as _database_module  # noqa: F401,E402
from cases import outbox as _outbox_module  # noqa: F401,E402
import sms_provider as _sms_provider_module  # noqa: F401,E402


ROOT = Path(__file__).resolve().parents[2]


def test_provider_capabilities_declare_no_idempotency_until_proven():
    from sms_provider import EsmsProvider

    capabilities = EsmsProvider(api_key="", secret="", brandname="").capabilities
    assert capabilities["idempotency"] is False
    assert capabilities["reconciliation"] is False


def test_outbox_handles_ambiguous_without_retry():
    source = (ROOT / "agent" / "cases" / "outbox.py").read_text(encoding="utf-8")
    assert 'settle("ambiguous"' in source
    assert '"ambiguous"' in source
    assert "provider_receipt" in source


def test_migration_adds_ambiguous_provider_receipt_state():
    migration = (ROOT / "agent" / "migrations" / "089_provider_delivery_receipts.sql").read_text(encoding="utf-8")
    assert "provider_receipt" in migration
    assert "ambiguous" in migration
