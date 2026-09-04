"""Characterization coverage for pure helpers selected for R20.8 refactoring."""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


AGENT_DIR = Path(__file__).resolve().parents[1] / "agent"
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))


def test_is_exact_origin_accepts_only_origin_authority_shapes():
    from bot_gateway import _is_exact_origin
    from config import is_exact_origin

    assert is_exact_origin("https://vinhlong360.vn") is True
    assert _is_exact_origin("https://vinhlong360.vn") is True
    # Preserve the pre-refactor parser's treatment of an empty userinfo field.
    assert is_exact_origin("https://@vinhlong360.vn") is True
    assert is_exact_origin("http://localhost:3000", require_https=False) is True
    for value in (
        "",
        "https://vinhlong360.vn/path",
        "https://vinhlong360.vn/?next=/",
        "https://user:pass@vinhlong360.vn",
        "https://vinhlong360.vn:",
        "https://bad host.example",
        "ftp://vinhlong360.vn",
        "http://vinhlong360.vn",
    ):
        assert is_exact_origin(value) is False


def test_production_secret_policy_rejects_placeholders_cycles_and_low_entropy():
    from secret_policy import is_strong_production_secret

    assert is_strong_production_secret("short") is False
    assert is_strong_production_secret("replace-me-123456789012345") is False
    assert is_strong_production_secret("0123456789" * 4) is False
    assert is_strong_production_secret("aaaaaaaaaaaaaaaaaaaa") is False
    assert is_strong_production_secret("mixed-production-secret-123456") is True


def test_redact_log_value_preserves_scalars_and_container_shapes():
    import privacy_boundary

    value = {
        "message": "contact a@example.com",
        "items": ["call 0901234567", None, 2],
        "tuple": ("mail b@example.com",),
    }

    result = privacy_boundary.redact_log_value(value)

    assert result["message"] == "contact [EMAIL]"
    assert result["items"] == ["call [PHONE]", None, 2]
    assert result["tuple"] == ("mail [EMAIL]",)


def test_search_rank_reason_order_is_stable():
    from search_contract import _rank

    entity = {
        "name": "Dừa Sáp",
        "summary": "Đặc sản miền Tây",
        "source": [{"title": "Nguồn Dừa Sáp"}],
        "confidence": 0.8,
    }

    assert _rank(entity, "dua sap") == (1000.0, "exact_name")
    assert _rank(entity, "dac san") == (500.0, "summary")
    assert _rank(entity, "nguon") == (300.0, "source")
    assert _rank(entity, "khong co") is None


def test_search_catalog_preserves_none_query_for_count_contract():
    from search_contract import SearchFilters, search_public_entities

    class Catalog:
        def count_entities_filtered(self, **kwargs):
            self.count_kwargs = kwargs
            return 0

        def list_entities(self, **kwargs):
            return []

    catalog = Catalog()
    search_public_entities("", offset=0, limit=10, filters=SearchFilters(), database=catalog)
    assert catalog.count_kwargs["q"] is None


def test_entities_page_helper_preserves_search_query_contract(monkeypatch):
    """The public entities route keeps search and list pagination semantics in one helper."""
    from entities import api as entities_api

    class Page:
        items = [{"id": "search-1"}]
        total = 1
        truncated = True
        ranking_version = "search-v1"

    seen = {}

    def fake_search(query, **kwargs):
        seen["query"] = query
        seen["filters"] = kwargs["filters"]
        return Page()

    monkeypatch.setattr(entities_api, "search_public_entities", fake_search)
    results, total, page = asyncio.run(
        entities_api._fetch_entities_page(
            "dua sap",
            single_type="dish",
            area="vinh-long",
            entity_types=["dish", "attraction"],
            month=7,
            sort="rating",
            limit=5,
            offset=10,
        )
    )

    assert results == Page.items
    assert total == 1
    assert page is not None
    assert seen["query"] == "dua sap"
    assert seen["filters"].entity_type == "dish"
    assert seen["filters"].entity_types == ("dish", "attraction")
    assert seen["filters"].month == 7
    assert seen["filters"].public_only is True


def test_seo_coverage_parts_keep_required_type_and_safe_attributes():
    """SEO coverage ignores unknown shapes without changing recognized values."""
    from scripts import validate_data

    assert validate_data._seo_coverage_parts(None) is None
    assert validate_data._seo_coverage_parts({"type": "organization"}) is None

    etype, required, attrs = validate_data._seo_coverage_parts(
        {"type": "restaurant", "attributes": {"phone": "0909123456"}}
    )
    assert etype == "restaurant"
    assert "phone" in required
    assert attrs == {"phone": "0909123456"}

    etype, _required, attrs = validate_data._seo_coverage_parts(
        {"type": "restaurant", "attributes": []}
    )
    assert etype == "restaurant"
    assert attrs == {}


def test_verified_projection_replay_uses_persisted_revision():
    """A verified retry replays its immutable receipt without fetching the entity."""
    from cases.publication import (
        VerifyProjectionCommand,
        _replay_verified_projection,
    )

    event_id = "notify:change-1:verified"

    class Transaction:
        def load_outbox_by_idempotency_key(self, key):
            assert key == event_id
            return {
                "idempotency_key": event_id,
                "payload": {
                    "event_id": event_id,
                    "case_id": "case-1",
                    "generation": "8",
                    "correlation_id": "corr-1",
                    "revision": 9,
                },
            }

    result = _replay_verified_projection(
        Transaction(), VerifyProjectionCommand("case-1", "change-1", object())
    )

    assert result.verified is True
    assert result.revision == 9
    assert result.outbox_event_id == event_id


def test_verification_failure_loader_replays_before_deadline():
    """A persisted failure is replayed until its own recovery deadline."""
    from cases.publication import VerifyProjectionCommand, _load_verification_failure

    now = datetime(2026, 9, 4, tzinfo=timezone.utc)
    event_id = "notify:change-1:verification_failed"
    existing = {
        "idempotency_key": event_id,
        "payload": {
            "event_id": event_id,
            "case_id": "case-1",
            "generation": "8",
            "correlation_id": "corr-1",
            "revision": 9,
            "mismatched": ["revision"],
            "next_update_at": (now + timedelta(hours=1)).isoformat(),
        },
    }

    class Transaction:
        def load_outbox_by_idempotency_key(self, key):
            assert key == event_id
            return existing

    previous = _load_verification_failure(
        Transaction(), VerifyProjectionCommand("case-1", "change-1", object()),
        object(), now,
    )

    assert previous[0] is existing
    assert previous[1] is not None
    assert previous[2] == now + timedelta(hours=1)


def test_replay_mapping_copy_accepts_database_mapping_rows():
    """Replay validation can normalize mapping rows returned by a database adapter."""
    from collections import UserDict

    from cases.publication import _copy_replay_mapping

    assert _copy_replay_mapping(UserDict({"event_id": "e-1"}), "e-1") == {
        "event_id": "e-1"
    }


def test_case_service_validation_pipeline_accepts_a_valid_command():
    """Create validation remains callable as one ordered, side-effect-free stage."""
    from cases.domain import ActorContext, Channel, CommandEnvelope
    from cases.service import (
        CaseService,
        CorrectionItemInput,
        CreateCorrectionCommand,
    )

    service = CaseService(store=None, crypto=None, policy=None, owner_ref="person:owner")
    command = CreateCorrectionCommand(
        envelope=CommandEnvelope(
            idempotency_key="validation-1",
            expected_revision=None,
            actor=ActorContext(
                actor_ref="anonymous",
                channel=Channel.WEB,
                scopes=frozenset(),
                correlation_id="corr-1",
            ),
        ),
        reporter_privacy="anonymous",
        items=(CorrectionItemInput(
            entity_id="entity-1",
            field_path="attributes.phone",
            reported_value="old",
            proposed_value="new",
            base_entity_revision=1,
        ),),
    )
    assert service._validate_create_request(
        command, now=datetime(2026, 9, 4, tzinfo=timezone.utc), session_user_ref=None
    ) is None


def test_contact_receipt_requirement_requires_phone_consent_without_assisted_flow():
    """Self-service phone notifications require a verified receipt; assisted intake does not."""
    from types import SimpleNamespace

    from cases.service import _requires_contact_receipt

    assert _requires_contact_receipt(SimpleNamespace(
        optional_phone="0909123456", assisted=None,
        notification_consent=True, contact_receipt=None,
    )) is True
    assert _requires_contact_receipt(SimpleNamespace(
        optional_phone="0909123456", assisted=object(),
        notification_consent=True, contact_receipt=None,
    )) is False
