"""Characterization coverage for pure helpers selected for R20.8 refactoring."""

from __future__ import annotations

import sys
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
