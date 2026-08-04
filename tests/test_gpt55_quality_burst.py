from __future__ import annotations

import ast
import logging
import re
from pathlib import Path

import pytest

import gpt55_quality_burst as q
import pinned_http as ph


def sample_data() -> dict:
    return {
        "entities": [
            {"id": "p-vl", "type": "place", "name": "Phuong Vinh Long", "area": "vinh-long", "coordinates": [10.1, 106.0]},
            {"id": "p-bt", "type": "place", "name": "Phuong Ben Tre", "area": "ben-tre", "coordinates": [10.2, 106.3]},
            {"id": "e-source", "type": "product", "name": "Dac san A", "area": "vinh-long", "summary": "Summary", "placeId": "p-vl", "coordinates": [10.1, 106.0]},
            {"id": "e-placeid", "type": "dish", "name": "Mon B", "area": "vinh-long", "summary": "Gan Phuong Vinh Long", "source": {"title": "s", "url": "https://example.com"}, "coordinates": [10.1, 106.0]},
            {"id": "e-location", "type": "attraction", "name": "Diem C", "area": "tra-vinh", "summary": "Summary", "source": {"title": "s", "url": "https://example.com"}, "placeId": "p-vl"},
            {"id": "e-eval", "type": "attraction", "name": "Diem D", "area": "vinh-long", "summary": "Summary", "source": {"title": "s", "url": "https://example.com"}, "placeId": "p-vl", "coordinates": [10.12, 106.01]},
            {"id": "e-prod", "type": "product", "name": "San pham E", "area": "ben-tre", "summary": "OCOP", "source": {"title": "s", "url": "https://example.com"}, "placeId": "p-bt", "coordinates": [10.2, 106.3]},
            {"id": "e-acc", "type": "accommodation", "name": "Luu tru F", "area": "tra-vinh", "summary": "Hotel", "source": {"title": "s", "url": "https://example.com"}, "placeId": "p-bt", "coordinates": [9.9, 106.2]},
            {"id": "e-dish", "type": "dish", "name": "Mon G", "area": "tra-vinh", "summary": "Khmer food", "source": {"title": "s", "url": "https://example.com"}, "placeId": "p-bt", "coordinates": [9.92, 106.22]},
        ],
        "relationships": [
            {"from": "e-eval", "to": "e-prod", "type": "related_to"},
            {"from": "e-location", "to": "e-dish", "type": "near"},
        ],
        "itineraries": [],
    }


def test_candidate_schema_and_policy_require_source_url() -> None:
    assert q.classify_apply_policy(0.95, [], verified=True, requires_url=True) == "needs_review"
    assert q.classify_apply_policy(0.95, ["https://example.com"], verified=True, requires_url=True) == "auto_apply"

    record = q.make_candidate_record(
        entity_id="",
        field="source",
        current_value=None,
        suggested_value=None,
        confidence=1.2,
        evidence_urls=["not-a-url"],
        reason="bad",
        apply_policy="auto_apply",
        stream="source",
    )
    assert record["apply_policy"] == "reject"
    assert "schema_errors" in record


def test_enforce_apply_policy_requires_verified_source_and_geocoder() -> None:
    source = q.enforce_apply_policy({
        "entity_id": "e1",
        "field": "source",
        "confidence": 0.95,
        "evidence_urls": ["https://example.com"],
        "url_verified": False,
        "apply_policy": "auto_apply",
    })
    assert source["apply_policy"] == "needs_review"

    location = q.enforce_apply_policy({
        "entity_id": "e1",
        "field": "coordinates",
        "confidence": 0.95,
        "suggested_value": [10.1, 106.1],
        "geocode_verified": False,
        "apply_policy": "auto_apply",
    })
    assert location["apply_policy"] == "needs_review"

    place_id = q.enforce_apply_policy({
        "entity_id": "e1",
        "field": "placeId",
        "confidence": 0.95,
        "suggested_value": "xa-an-binh",
        "apply_policy": "auto_apply",
    })
    assert place_id["apply_policy"] == "needs_review"

def test_manifest_shards_prioritize_non_place_sources() -> None:
    manifest = q.build_manifest(sample_data(), chunk_size=1, relationship_chunk_size=1)
    counts = manifest["counts"]
    assert counts["missing_source"] == 3
    assert counts["missing_source_non_place"] == 1
    assert counts["missing_source_place"] == 2
    assert counts["missing_place_id"] == 1
    source_shards = manifest["streams"]["source"]
    assert source_shards[0]["priority"] == "non_place_first"
    assert source_shards[-1]["priority"] == "place_second"
    assert manifest["streams"]["relationship"]


def test_placeid_area_conflict_rejects_candidate() -> None:
    data = sample_data()
    place_by_id = {e["id"]: e for e in data["entities"] if e["type"] == "place"}
    entity = next(e for e in data["entities"] if e["id"] == "e-placeid")
    record = q.placeid_candidate_from_decision(entity, {"candidate_place_id": "p-bt", "confidence": 0.96, "evidence": "looks close"}, place_by_id)
    assert record["apply_policy"] == "reject"
    assert record["area_conflict"] is True


def test_location_ignores_llm_coordinates_and_uses_geocoder() -> None:
    entity = {"id": "e-location", "type": "attraction", "name": "Diem C", "area": "tra-vinh"}
    decision = {"geocode_query": "Diem C, Tra Vinh", "coordinates": [1, 2], "confidence": 0.95, "reason": "query"}

    no_hit = q.location_candidate_from_decision(entity, decision, geocode_fn=lambda *_args: None)
    assert no_hit["suggested_value"] is None
    assert no_hit["apply_policy"] == "reject"
    assert no_hit["llm_supplied_coordinates_ignored"] is True

    hit = q.location_candidate_from_decision(entity, decision, geocode_fn=lambda *_args: [9.9, 106.2])
    assert hit["suggested_value"] == [9.9, 106.2]
    assert hit["apply_policy"] == "auto_apply"


def test_merge_outputs_dedupes_highest_confidence(tmp_path: Path) -> None:
    low = q.make_candidate_record(
        entity_id="e1", field="source", current_value=None, suggested_value={"url": "https://example.com/a"},
        confidence=0.72, evidence_urls=["https://example.com/a"], reason="low", apply_policy="needs_review", stream="source",
    )
    high = q.make_candidate_record(
        entity_id="e1", field="source", current_value=None, suggested_value={"url": "https://example.com/a"},
        confidence=0.91, evidence_urls=["https://example.com/a"], reason="high", apply_policy="auto_apply", stream="source",
        extra={"url_verified": True},
    )
    q.write_jsonl(tmp_path / q.STREAM_FILES["source"], [low, high])
    queue = q.merge_outputs(tmp_path)
    assert queue["counts"]["raw_records"] == 2
    assert queue["counts"]["deduped_records"] == 1
    assert queue["auto_apply"][0]["reason"] == "high"
    assert (tmp_path / q.REVIEW_QUEUE_FILE).exists()
    assert (tmp_path / q.SUMMARY_FILE).exists()


def test_generated_eval_cases_have_valid_shape() -> None:
    data = sample_data()
    cases = q.generate_heuristic_eval_cases(data, case_target=5)
    entity_ids = {e["id"] for e in data["entities"]}
    assert cases
    assert all(q.valid_eval_case(case, entity_ids) for case in cases)


def test_relationship_low_confidence_rejects_even_with_risk() -> None:
    item = {"index": 1, "source_id": "a", "target_id": "b", "rel_type": "hosts", "heuristic_reasons": ["missing proof"]}
    record = q.relationship_record_from_status(item, "needs_review", 0.35, "missing proof")
    assert record["risk"] == "high"
    assert record["apply_policy"] == "reject"


def test_merge_enforces_low_confidence_reject(tmp_path: Path) -> None:
    bad_policy = q.make_candidate_record(
        entity_id="e2", field="relationship", current_value={}, suggested_value={"risk": "medium"},
        confidence=0.35, evidence_urls=[], reason="weak", apply_policy="needs_review", stream="relationship",
    )
    q.write_jsonl(tmp_path / q.STREAM_FILES["relationship"], [bad_policy])
    queue = q.merge_outputs(tmp_path)
    assert queue["counts"]["needs_review"] == 0
    assert queue["counts"]["reject"] == 1


def _pinned_response(
    *,
    status: int = 200,
    content: bytes = b"",
    headers: tuple[tuple[str, str], ...] = (("content-type", "text/html; charset=utf-8"),),
) -> ph.PinnedResponse:
    return ph.PinnedResponse(status, "https://example.com/final", headers, content, ())


def test_fetch_url_text_uses_pinned_options_and_tag_only_cleanup(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict]] = []
    body = b"<script>keep_me()</script><style>.keep{}</style><h1>Vinh Long</h1>"
    monkeypatch.setattr(
        q._PINNED_HTTP,
        "get",
        lambda url, **kwargs: calls.append((url, kwargs)) or _pinned_response(content=body),
    )
    text = q.fetch_url_text("https://example.com/a", timeout=12)
    assert "keep_me()" in text
    assert ".keep{}" in text
    assert "Vinh Long" in text
    assert calls == [(
        "https://example.com/a",
        {
            "user_agent": "vinhlong360-quality-burst/1.0",
            "policy": ph.EgressPolicy(
                max_encoded_bytes=2 * 1024 * 1024,
                max_decoded_bytes=2 * 1024 * 1024,
                accepted_encodings=("gzip", "identity"),
                inactivity_timeout_seconds=12.0,
                total_timeout_seconds=12.0,
                max_redirects=5,
            ),
            "audit_context": "quality_burst",
        },
    )]


def test_fetch_url_text_real_blocked_literal_returns_empty_and_logs_once(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING, logger="security.egress"):
        assert q.fetch_url_text("https://127.0.0.1/private?token=secret") == ""

    records = [record for record in caplog.records if record.name == "security.egress"]
    assert len(records) == 1
    assert records[0].getMessage() == (
        "Pinned egress denied consumer=quality_burst reason=blocked_address "
        "target=https://127.0.0.1:443 hop=0"
    )
    assert "token" not in records[0].getMessage()


@pytest.mark.parametrize("status, expected", [(200, True), (399, True), (400, False), (500, False)])
def test_fetch_url_text_preserves_status_contract(
    monkeypatch: pytest.MonkeyPatch,
    status: int,
    expected: bool,
) -> None:
    monkeypatch.setattr(
        q._PINNED_HTTP,
        "get",
        lambda *_args, **_kwargs: _pinned_response(status=status, content=b"body"),
    )
    assert bool(q.fetch_url_text("https://example.com/a")) is expected


def test_fetch_url_text_skips_client_when_requests_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(q, "requests", None)
    monkeypatch.setattr(
        q._PINNED_HTTP,
        "get",
        lambda *_args, **_kwargs: pytest.fail("pinned client called"),
    )
    assert q.fetch_url_text("https://example.com/a") == ""


def test_fetch_url_text_keeps_requests_charset_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    content = "café".encode("iso-8859-1")
    monkeypatch.setattr(
        q._PINNED_HTTP,
        "get",
        lambda *_args, **_kwargs: _pinned_response(
            content=content,
            headers=(("content-type", "text/html; charset=iso-8859-1"),),
        ),
    )
    assert q.fetch_url_text("https://example.com/a") == "café"


def test_fetch_url_text_does_not_redecode_http_decoded_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    decoded = "Nội dung đã giải nén".encode("utf-8")
    monkeypatch.setattr(
        q._PINNED_HTTP,
        "get",
        lambda *_args, **_kwargs: _pinned_response(
            content=decoded,
            headers=(
                ("content-type", "text/html; charset=utf-8"),
                ("content-encoding", "gzip"),
                ("content-length", "12"),
            ),
        ),
    )
    assert q.fetch_url_text("https://example.com/a") == "Nội dung đã giải nén"


@pytest.mark.parametrize(
    ("url", "disabled"),
    [
        ("https://example.com/a", True),
        ("not-a-url", False),
    ],
)
def test_fetch_url_text_guards_skip_pinned_client(
    monkeypatch: pytest.MonkeyPatch,
    url: str,
    disabled: bool,
) -> None:
    monkeypatch.setattr(
        q._PINNED_HTTP,
        "get",
        lambda *_args, **_kwargs: pytest.fail("pinned client called"),
    )
    assert q.fetch_url_text(url, disabled=disabled) == ""


def test_fetch_url_text_without_content_type_matches_requests_apparent_encoding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert q.requests is not None
    content = ("Café déjà vu, façade et élève. " * 20).encode("cp1252")
    monkeypatch.setattr(
        q._PINNED_HTTP,
        "get",
        lambda *_args, **_kwargs: _pinned_response(content=content, headers=()),
    )
    offline = q.requests.Response()
    offline.headers = q.requests.structures.CaseInsensitiveDict()
    offline._content = content
    offline._content_consumed = True
    offline.encoding = q.requests.utils.get_encoding_from_headers(offline.headers)
    expected = q.compact_text(re.sub(r"<[^>]+>", " ", offline.text or ""), 5000)
    assert q.fetch_url_text("https://example.com/a") == expected


@pytest.mark.parametrize(
    "error",
    [
        ph.PinnedBodyLimitError("large"),
        ph.PinnedContentEncodingError("encoding"),
        ph.PinnedDeadlineExceeded("deadline"),
        ph.ResolverSaturatedError("dns busy"),
    ],
)
def test_fetch_url_text_silently_returns_empty_on_bounded_failure(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    error: Exception,
) -> None:
    monkeypatch.setattr(
        q._PINNED_HTTP,
        "get",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(error),
    )
    with caplog.at_level(logging.WARNING):
        assert q.fetch_url_text("https://example.com/a") == ""
    assert caplog.records == []


def test_fetch_url_text_truncates_to_exactly_5000_characters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        q._PINNED_HTTP,
        "get",
        lambda *_args, **_kwargs: _pinned_response(content=("x" * 5005).encode()),
    )
    result = q.fetch_url_text("https://example.com/a")
    assert result == "x" * 5000
    assert len(result) == 5000


def test_verify_source_url_preserves_all_messages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entity = {"name": "Vinh Long"}
    assert q.verify_source_url("not-a-url", entity) == (False, "invalid URL")

    monkeypatch.setattr(q, "fetch_url_text", lambda *_args, **_kwargs: "")
    assert q.verify_source_url("https://example.com/a", entity) == (
        False,
        "URL could not be fetched",
    )

    monkeypatch.setattr(
        q,
        "fetch_url_text",
        lambda *_args, **_kwargs: "Tourism information for Vinh Long",
    )
    assert q.verify_source_url("https://example.com/a", entity) == (
        True,
        "URL opens and page text matches entity name",
    )

    monkeypatch.setattr(
        q,
        "fetch_url_text",
        lambda *_args, **_kwargs: "Completely unrelated page",
    )
    assert q.verify_source_url("https://example.com/a", entity) == (
        False,
        "URL opens but page text does not clearly match entity",
    )


def test_verify_source_url_no_web_passes_disabled_without_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, bool]] = []

    def fetch(url: str, *, disabled: bool = False, **_kwargs) -> str:
        calls.append((url, disabled))
        return ""

    monkeypatch.setattr(q, "fetch_url_text", fetch)
    assert q.verify_source_url(
        "https://example.com/a",
        {"name": "Vinh Long"},
        no_web=True,
    ) == (False, "URL could not be fetched")
    assert calls == [("https://example.com/a", True)]


def test_module_source_has_no_bom_and_is_parseable() -> None:
    """Regression guard: a UTF-8 BOM here is not cosmetic.

    This file previously began with a UTF-8 BOM sitting *before* the shebang.
    Two standards checkers (`scripts/checks/check_complexity.py` and
    `scripts/checks/check_test_pairing.py`) read sources with `encoding="utf-8"`
    and `ast.parse` them inside `except SyntaxError: continue`, so the BOM
    decoded to U+FEFF, parsing failed, and the module was skipped in silence --
    hiding 11 pre-existing R20.8 complexity violations from the ratchet. The BOM
    also defeated the shebang, since the kernel never saw `#!` in byte zero.
    """
    raw = Path(q.__file__).read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf"), "UTF-8 BOM re-introduced"
    assert raw.startswith(b"#!"), "shebang must occupy the first bytes"
    ast.parse(raw.decode("utf-8"))
