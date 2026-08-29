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


def test_enforce_apply_policy_confidence_reject_wins_over_demotion() -> None:
    # Ghim thứ tự elif (lát 10 R20.8): reject-vì-confidence thắng mọi nhánh
    # hạ-cấp; auto_apply với field thường và đủ tin cậy thì GIỮ NGUYÊN.
    low_conf_source = q.enforce_apply_policy({
        "entity_id": "e1",
        "field": "source",
        "confidence": 0.5,
        "evidence_urls": ["https://example.com"],
        "url_verified": False,
        "apply_policy": "auto_apply",
    })
    assert low_conf_source["apply_policy"] == "reject"

    ordinary_field = q.enforce_apply_policy({
        "entity_id": "e1",
        "field": "summary",
        "confidence": 0.95,
        "apply_policy": "auto_apply",
    })
    assert ordinary_field["apply_policy"] == "auto_apply"

    verified_source = q.enforce_apply_policy({
        "entity_id": "e1",
        "field": "source",
        "confidence": 0.95,
        "evidence_urls": ["https://example.com"],
        "url_verified": True,
        "apply_policy": "auto_apply",
    })
    assert verified_source["apply_policy"] == "auto_apply"


def test_validate_candidate_record_error_order_is_stable() -> None:
    errors = q.validate_candidate_record({
        "entity_id": "",
        "field": "",
        "confidence": "khong-phai-so",
        "evidence_urls": "khong-phai-list",
        "apply_policy": "sai",
    })
    joined = " | ".join(errors)
    assert joined.index("entity_id") < joined.index("confidence must be numeric")
    assert joined.index("confidence must be numeric") < joined.index("evidence_urls must be a list")
    assert joined.index("evidence_urls must be a list") < joined.index("apply_policy")


# ── Lát 17 (B3, test-only): đặc-tả 4 hàm trước khi mổ ở lát 18-19 ──


def _place_entity(**overrides):
    base = {
        "id": "e-1", "name": "Chua Vinh Trang", "type": "place",
        "summary": "mot ngoi chua", "source": "https://example.com",
        "coordinates": [10.1, 106.1],
    }
    base.update(overrides)
    return base


def test_relationship_targets_include_table() -> None:
    ent_a = _place_entity(id="a", coordinates=[10.0, 106.0])
    ent_b = _place_entity(id="b", name="Cho Noi", coordinates=[10.001, 106.001])
    ent_far = _place_entity(id="far", coordinates=[12.0, 108.0])
    data = {
        "entities": [ent_a, ent_b, ent_far],
        "relationships": [
            {"source_id": "a", "target_id": "b", "type": "near"},      # gần thật → LOẠI
            {"source_id": "a", "target_id": "far", "type": "near"},    # quá xa → GIỮ
            {"source_id": "a", "target_id": "b", "type": "related"},   # non-near → GIỮ
            {"source_id": "a", "target_id": "ma", "type": "related"},  # đích không tồn tại
            {"source_id": "a", "type": "near"},                        # thiếu đích
            "khong-phai-dict",                                          # bỏ qua
        ],
    }

    targets = q.relationship_targets(data)
    by_index = {t["index"]: t for t in targets}

    assert 0 not in by_index
    assert by_index[1]["heuristic_reasons"][0].startswith("near edge distance is ")
    assert by_index[2]["heuristic_reasons"] == []
    assert by_index[3]["heuristic_reasons"] == ["missing target entity"]
    assert (
        by_index[4]["heuristic_reasons"][0]
        == "missing relationship source, target, or type"
    )
    assert set(by_index) == {1, 2, 3, 4}


def test_candidate_places_scoring_order_and_fallback() -> None:
    entity = _place_entity(name="Gan Cho Noi Cai Be", area="phuong-1", type="food")
    places = [
        {"id": "p-match", "name": "Cho Noi Cai Be", "area": "phuong-1"},
        {"id": "p-cross", "name": "Cho Noi Cai Be", "area": "phuong-2"},
        {"id": "p-area", "name": "Khong Lien Quan Xyz", "area": "phuong-1"},
    ]

    ranked = q.candidate_places_for_entity(entity, places)
    assert [p["id"] for p in ranked][:2] == ["p-match", "p-cross"]
    assert set(ranked[0]) == {"id", "name", "area", "legacyArea"}

    # Không ai có điểm dương → fallback: mọi place cùng area, điểm 1.0
    fallback = q.candidate_places_for_entity(
        _place_entity(name="Zzz", summary="zzz", area="phuong-1", type="food"),
        [{"id": "p-area", "name": "Khong Lien Quan Xyz", "area": "phuong-1"}],
    )
    assert [p["id"] for p in fallback] == ["p-area"]


@pytest.mark.parametrize(
    ("overrides", "expected_status", "expected_conf"),
    [
        ({}, "verified", 0.80),
        ({"name": ""}, "needs_fix", 0.85),
        ({"source": ""}, "needs_source", 0.82),
        ({"type": "food", "area": "phuong-1", "placeId": ""}, "unverified", 0.74),
    ],
)
def test_heuristic_quality_status_truth_table(
    overrides, expected_status, expected_conf
) -> None:
    status, confidence, flags = q.heuristic_quality_status(_place_entity(**overrides))
    assert (status, confidence) == (expected_status, expected_conf)
    assert bool(flags) == (expected_status != "verified")


def test_placeid_decision_conflicts_pin_reason_bytes() -> None:
    entity = _place_entity(area="phuong-1")
    place_by_id = {"p-2": {"id": "p-2", "name": "P2", "area": "phuong-2"}}

    ghost = q.placeid_candidate_from_decision(
        entity, {"candidate_place_id": "ma", "confidence": 0.9}, place_by_id
    )
    assert ghost["status"] == "conflicting"
    assert "candidate placeId does not exist" in ghost["reason"]

    crossed = q.placeid_candidate_from_decision(
        entity, {"candidate_place_id": "p-2", "confidence": 0.9}, place_by_id
    )
    assert crossed["status"] == "conflicting"
    assert "area conflict: entity=phuong-1, place=phuong-2" in crossed["reason"]

    empty_low = q.placeid_candidate_from_decision(
        entity, {"candidate_place_id": "", "confidence": 0.2}, place_by_id
    )
    assert empty_low["apply_policy"] == "reject"
    assert empty_low["suggested_value"] is None


def test_entity_shard_seq_continues_across_calls_same_stream() -> None:
    # Mìn lát 18: seq shard phải NỐI theo len(shards[stream]) hiện có —
    # hai đợt add cùng stream không được đánh số lại từ 0.
    shards = {"source": []}
    q._add_entity_shards(shards, "source", [_place_entity(id="x1", type="food")], 25, priority="non_place_first")
    q._add_entity_shards(shards, "source", [_place_entity(id="x2")], 25, priority="place_second")

    assert [s["id"] for s in shards["source"]] == [
        "source-non_place_first-0000",
        "source-place_second-0001",
    ]


def test_placeid_policy_matrix_after_split() -> None:
    # Lát 19: auto_apply luôn bị hạ needs_review; không candidate thì
    # ngưỡng 0.70 quyết reject/needs_review.
    assert q._placeid_policy("p-1", 0.96, False) == "needs_review"
    assert q._placeid_policy("", 0.69, False) == "reject"
    assert q._placeid_policy("", 0.71, False) == "needs_review"


def test_eval_case_sections_share_one_picked_set() -> None:
    # Lát 20: `picked` dùng chung xuyên các đoạn — entity đã vào lịch trình
    # khu vực thì KHÔNG được xuất hiện lại ở đoạn dish phía sau.
    cases = q.generate_heuristic_eval_cases(sample_data(), case_target=30)
    seen: set[str] = set()
    for case in cases:
        for entity_id in case.get("expected_entities", []):
            assert entity_id not in seen or case["category"] == "itinerary"
        if case["category"] != "itinerary":
            seen.update(case.get("expected_entities", []))


# ── Lát 23 (B3, test-only): đặc-tả 3 hàm cao-rủi-ro trước khi mổ lát 24 ──


class _FakeLLM:
    def __init__(self, available=True, result=None):
        self.available = available
        self._result = result

    def complete_json(self, **_kwargs):
        return self._result


def _burst_config(**overrides):
    base = dict(data_path=Path("x"), output_dir=Path("y"), no_web=True)
    base.update(overrides)
    return q.BurstConfig(**base)


def test_source_candidate_four_branches(monkeypatch) -> None:
    entity = _place_entity(source=None)
    cfg = _burst_config()

    # 1) LLM tắt + không có search → reject, needs_source
    monkeypatch.setattr(q, "search_web", lambda query, disabled=False: [])
    off_dry = q.source_candidate_for_entity(entity, _FakeLLM(available=False), cfg)
    assert (off_dry["apply_policy"], off_dry["status"]) == ("reject", "needs_source")

    # 2) LLM tắt + có search → giữ ứng viên 0.55 nhưng vẫn reject
    monkeypatch.setattr(
        q, "search_web",
        lambda query, disabled=False: [{"title": "T", "url": "https://ex.com"}],
    )
    off_hit = q.source_candidate_for_entity(entity, _FakeLLM(available=False), cfg)
    assert (off_hit["apply_policy"], off_hit["status"]) == ("reject", "candidate_unverified")
    assert off_hit["confidence"] == 0.55
    assert off_hit["suggested_value"] == {"title": "T", "url": "https://ex.com"}

    # 3) LLM lỗi → reject, llm_error
    err = q.source_candidate_for_entity(entity, _FakeLLM(result={"_error": "boom"}), cfg)
    assert (err["apply_policy"], err["status"]) == ("reject", "llm_error")
    assert "boom" in err["reason"]

    # 4) LLM tốt + URL verify được → url_verified, status verified
    monkeypatch.setattr(q, "verify_source_url", lambda url, entity, no_web=False: (True, "match"))
    good = q.source_candidate_for_entity(
        entity,
        _FakeLLM(result={"title": "Chinh chu", "url": "https://ex.com/a", "confidence": 0.95, "reason": "khop ten"}),
        cfg,
    )
    assert good["status"] == "verified"
    assert good["url_verified"] is True
    assert good["evidence_urls"] == ["https://ex.com/a"]
    assert "verification: match" in good["reason"]


def test_audit_accuracy_chunk_three_branches() -> None:
    complete = _place_entity()
    # 1) LLM tắt → dùng heuristic: entity đủ → status verified, policy reject
    off = q.audit_accuracy_chunk([complete], _FakeLLM(available=False))
    assert off[0]["status"] == "verified"
    assert off[0]["apply_policy"] == "reject"

    # 2) LLM trả không-phải-list → mọi entity thành llm_error/unverified
    err = q.audit_accuracy_chunk([complete], _FakeLLM(result={"_error": "hong"}))
    assert err[0]["status"] == "unverified"
    assert "hong" in err[0]["reason"]

    # 3) LLM trả list: status lạ bị ép về unverified, status hợp lệ giữ nguyên
    decisions = [
        {"entity_id": complete["id"], "status": "tu-che", "confidence": 0.9, "reason": "x"},
    ]
    coerced = q.audit_accuracy_chunk([complete], _FakeLLM(result=decisions))
    assert coerced[0]["status"] == "unverified"


def test_audit_relationship_chunk_three_branches() -> None:
    flagged = {"index": 1, "source_id": "a", "target_id": "b", "rel_type": "near",
               "heuristic_reasons": ["near edge distance is 99.0 km"]}
    clean = {"index": 2, "source_id": "a", "target_id": "c", "rel_type": "related",
             "heuristic_reasons": []}

    # 1) LLM tắt: near-có-lý-do → needs_review 0.86; sạch → verified 0.75
    off = q.audit_relationship_chunk([flagged, clean], _FakeLLM(available=False))
    assert (off[0]["status"], off[0]["confidence"]) == ("needs_review", 0.86)
    assert (off[1]["status"], off[1]["confidence"]) == ("verified", 0.75)

    # 2) LLM trả không-phải-list → unverified kèm lý do lỗi
    err = q.audit_relationship_chunk([flagged], _FakeLLM(result={"_error": "gay"}))
    assert err[0]["status"] == "unverified"
    assert "gay" in err[0]["reason"]

    # 3) LLM trả list: index khớp giữ status; index bị bỏ sót → unverified + lý do riêng
    decisions = [{"relationship_index": 1, "status": "conflicting", "confidence": 0.9, "reason": "trung"}]
    mixed = q.audit_relationship_chunk([flagged, clean], _FakeLLM(result=decisions))
    assert mixed[0]["status"] == "conflicting"
    assert mixed[1]["status"] == "unverified"
    assert "omitted" in mixed[1]["reason"]
