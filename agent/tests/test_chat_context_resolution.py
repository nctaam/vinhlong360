# -*- coding: utf-8 -*-
"""Đặc tả hành vi HIỆN TẠI cụm giải-nghĩa-ngữ-cảnh + tool còn lại của chat (agent/chat/api.py).

Phạm vi: _resolve_anaphors / _resolve_pronouns / _extract_reply_entities /
_resolve_contextual_query / _fold_lazy_prompt / _fold_experience_fewshot /
_rerank_resolve_entities / _backfill_from_keyword / _hybrid_rerank_search /
call_tool / _tool_ocop_products / _tool_nearby_entities / _tool_accommodation_search /
_tool_community_reviews / _tool_trending_posts / _tool_directory_lookup /
_tool_web_search / web_search (+_do_search qua fake module ddgs).

Nguyên tắc harness (học từ test_chat_tools.py + test_chat_history_continuity.py):
- KHÔNG lifespan, KHÔNG TestClient: mọi hàm đích là hàm thuần gọi trực tiếp.
- KHÔNG network/LLM thật: ddgs được thay bằng module giả trong sys.modules,
  social cũng vậy; mọi hàm knowledge.* đụng tới đều monkeypatch vào ĐÚNG module
  knowledge (module thực thi), không đụng DB thật.
- knowledge._entities được setattr = dict giả → _ensure() thấy khác-None nên
  KHÔNG nạp data thật.
"""
import json
import os
import sys
import types
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:9999/v1")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key")
os.environ["BUILD_SEARCH_INDEXES"] = "false"
os.environ["BACKGROUND_INDEX_BUILD"] = "false"
os.environ["SCHEDULER_ENABLED"] = "false"
os.environ.setdefault("DESTRUCTIVE_OPS_LOCKED", "1")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chat import api as chat_api  # noqa: E402


# ══════════════════ helpers ══════════════════


def _install_fake_ddgs(monkeypatch, rows=None, exc=None):
    """Thay module `ddgs` trong sys.modules — _do_search import lúc CHẠY nên bắt được."""
    calls = []
    mod = types.ModuleType("ddgs")

    class DDGS:
        def __init__(self, timeout=None):
            calls.append({"timeout": timeout})

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def text(self, query, region=None, max_results=None):
            calls[-1].update({"query": query, "region": region, "max_results": max_results})
            if exc is not None:
                raise exc
            return list(rows or [])

    mod.DDGS = DDGS
    monkeypatch.setitem(sys.modules, "ddgs", mod)
    return calls


def _install_fake_social(monkeypatch, reviews=None, posts=None, exc=None):
    """Thay module `community.api` (nhà thật sau gỡ shim 2026-08-29) — hai tool
    UGC import nó bên trong try lúc GỌI nên fake trong sys.modules ăn trọn."""
    seen = {}
    mod = types.ModuleType("community.api")

    def get_community_reviews(entity_id, limit):
        seen["reviews_args"] = (entity_id, limit)
        if exc is not None:
            raise exc
        return list(reviews or [])

    def get_trending_posts(limit, entity_type=None):
        seen["posts_args"] = (limit, entity_type)
        if exc is not None:
            raise exc
        return list(posts or [])

    mod.get_community_reviews = get_community_reviews
    mod.get_trending_posts = get_trending_posts
    monkeypatch.setitem(sys.modules, "community.api", mod)
    return seen


# ══════════════════ web_search + _do_search ══════════════════


def test_web_search_maps_ddgs_rows_and_params(monkeypatch):
    """Nhánh chính: _do_search ánh xạ title/href/body → title/url/snippet, region vn-vi."""
    calls = _install_fake_ddgs(monkeypatch, rows=[
        {"title": "Chợ nổi Trà Ôn", "href": "https://vd.example/cho-noi", "body": "họp lúc sáng sớm"},
        {"title": "Thiếu href"},
    ])
    monkeypatch.setattr(chat_api, "HAS_CIRCUIT_BREAKER", False)
    out = chat_api.web_search("chợ nổi", max_results=2)
    assert out == [
        {"title": "Chợ nổi Trà Ôn", "url": "https://vd.example/cho-noi", "snippet": "họp lúc sáng sớm"},
        {"title": "Thiếu href", "url": "", "snippet": ""},
    ]
    assert calls == [{"timeout": 10, "query": "chợ nổi", "region": "vn-vi", "max_results": 2}]


def test_web_search_error_returns_empty_list(monkeypatch):
    """Nhánh lỗi: DDGS nổ → trả [] chứ không propagate."""
    _install_fake_ddgs(monkeypatch, exc=RuntimeError("mạng rớt"))
    monkeypatch.setattr(chat_api, "HAS_CIRCUIT_BREAKER", False)
    assert chat_api.web_search("bất kỳ") == []


def test_web_search_routes_through_circuit_breaker(monkeypatch):
    """Có breaker: gọi qua web_search_breaker.call(fn); max_results mặc định 5."""
    calls = _install_fake_ddgs(monkeypatch, rows=[{"title": "T", "href": "u", "body": "s"}])
    routed = {}

    class _FakeBreaker:
        def call(self, fn):
            routed["fn"] = fn
            return fn()

    monkeypatch.setattr(chat_api, "HAS_CIRCUIT_BREAKER", True)
    monkeypatch.setattr(chat_api, "web_search_breaker", _FakeBreaker())
    out = chat_api.web_search("chùa")
    assert out == [{"title": "T", "url": "u", "snippet": "s"}]
    assert callable(routed["fn"])          # đi qua breaker thật sự
    assert calls[0]["max_results"] == 5    # default giữ nguyên


# ══════════════════ _tool_web_search ══════════════════


def test_tool_web_search_wraps_results(monkeypatch):
    seen = {}
    rows = [{"title": "A", "url": "u", "snippet": "s"}]
    monkeypatch.setattr(chat_api, "web_search", lambda q: seen.setdefault("q", q) and rows or rows)
    out = json.loads(chat_api._tool_web_search({"query": "đặc sản"}))
    assert out == {"results": rows}
    assert seen["q"] == "đặc sản"


def test_tool_web_search_empty_returns_note(monkeypatch):
    monkeypatch.setattr(chat_api, "web_search", lambda q: [])
    out = json.loads(chat_api._tool_web_search({"query": "x"}))
    assert out == {"results": [], "note": "Không tìm thấy kết quả"}


# ══════════════════ call_tool ══════════════════


def test_call_tool_unknown_tool_error_shape():
    out = json.loads(chat_api.call_tool("khong-ton-tai", {}))
    assert out == {"error": "Unknown tool: khong-ton-tai"}


def test_call_tool_missing_required_arg_returns_structured_error():
    """P1: KeyError trong handler (web_search thiếu 'query') → lỗi có cấu trúc, không crash."""
    out = json.loads(chat_api.call_tool("web_search", {}))
    assert out == {"error": "Không thực hiện được công cụ (thiếu hoặc sai tham số)."}


def test_call_tool_none_args_treated_as_empty(monkeypatch):
    monkeypatch.setattr(chat_api.knowledge, "stats", lambda: {"entities": 2, "places": 1})
    out = json.loads(chat_api.call_tool("stats", None))
    assert out == {"entities": 2, "places": 1}


def test_call_tool_suggest_followups_forwards_accumulator(monkeypatch):
    """suggest_followups là handler DUY NHẤT nhận usage_accumulator từ call_tool."""
    seen = {}

    def fake_followups(context, acc=None):
        seen["context"], seen["acc"] = context, acc
        return ["Câu 1", "Câu 2"]

    sentinel = object()
    monkeypatch.setattr(chat_api, "generate_followups", fake_followups)
    out = json.loads(chat_api.call_tool("suggest_followups", {"context": "về chùa"}, sentinel))
    assert out == {"suggestions": ["Câu 1", "Câu 2"]}
    assert seen == {"context": "về chùa", "acc": sentinel}


# ══════════════════ _rerank_resolve_entities ══════════════════


def _ents3():
    return {
        "e1": {"id": "e1", "name": "E1"},
        "e2": {"id": "e2", "name": "E2"},
        "e3": {"id": "e3", "name": "E3"},
    }


def test_rerank_resolve_entities_resolves_both_id_keys(monkeypatch):
    ents = _ents3()
    monkeypatch.setattr(chat_api.knowledge, "get_entity", lambda eid: ents.get(eid))
    reranked = [{"id": "e1"}, {"entity_id": "e2"}, {"id": "khong-co"}, {}]
    out = chat_api._rerank_resolve_entities(reranked, set(), has_filters=False)
    # id lẫn entity_id đều resolve; id lạ và hit không-id bị bỏ qua êm.
    assert out == [ents["e1"], ents["e2"]]


def test_rerank_resolve_entities_drops_outside_filter(monkeypatch):
    ents = _ents3()
    monkeypatch.setattr(chat_api.knowledge, "get_entity", lambda eid: ents.get(eid))
    reranked = [{"id": "e3"}, {"id": "e1"}]
    out = chat_api._rerank_resolve_entities(reranked, {"e1"}, has_filters=True)
    assert out == [ents["e1"]]  # e3 resolve được nhưng ngoài allowed_ids → loại


# ══════════════════ _backfill_from_keyword ══════════════════


def test_backfill_dedupes_and_stops_at_limit():
    out = [{"id": "a"}]
    kw = [{"id": "a"}, {"id": "b"}, {"id": "c"}, {"id": "d"}]
    chat_api._backfill_from_keyword(out, kw, limit=3)
    assert [e["id"] for e in out] == ["a", "b", "c"]  # a không lặp, dừng đúng limit


def test_backfill_noop_when_all_ids_already_present():
    out = [{"id": "a"}, {"id": "b"}]
    chat_api._backfill_from_keyword(out, [{"id": "b"}, {"id": "a"}], limit=5)
    assert [e["id"] for e in out] == ["a", "b"]


# ══════════════════ _hybrid_rerank_search ══════════════════


def test_hybrid_search_plain_path_without_query(monkeypatch):
    """q rỗng → trả thẳng keyword_results[:limit]; pool xin max(limit*3, 30)."""
    ents = _ents3()
    seen = {}

    def fake_search(**kwargs):
        seen.update(kwargs)
        return [ents["e1"], ents["e2"], ents["e3"]]

    monkeypatch.setattr(chat_api.knowledge, "search_entities", fake_search)
    out = chat_api._hybrid_rerank_search({"limit": 2})
    assert out == [ents["e1"], ents["e2"]]
    assert seen["q"] is None
    assert seen["limit"] == 30  # max(2*3, 30)


def test_hybrid_search_plain_path_when_contextual_off(monkeypatch):
    ents = _ents3()
    monkeypatch.setattr(chat_api.knowledge, "search_entities",
                        lambda **k: [ents["e1"], ents["e2"]])
    monkeypatch.setattr(chat_api, "HAS_CONTEXTUAL", False)
    monkeypatch.setattr(chat_api, "enhanced_hybrid_search",
                        lambda **k: (_ for _ in ()).throw(AssertionError("không được gọi")))
    out = chat_api._hybrid_rerank_search({"q": "chùa", "limit": 1})
    assert out == [ents["e1"]]


def test_hybrid_search_empty_pool_short_circuits(monkeypatch):
    monkeypatch.setattr(chat_api.knowledge, "search_entities", lambda **k: [])
    monkeypatch.setattr(chat_api, "HAS_CONTEXTUAL", True)
    assert chat_api._hybrid_rerank_search({"q": "chùa"}) == []


def test_hybrid_search_reranks_then_backfills(monkeypatch):
    """Hybrid xếp lại thứ tự, thiếu thì bù từ keyword pool (không trùng id)."""
    ents = _ents3()
    kw = [ents["e1"], ents["e2"], ents["e3"]]
    captured = {}

    def fake_enhanced(query, keyword_results, entities, relationships, top_k):
        captured.update(query=query, keyword_results=keyword_results,
                        entities=entities, relationships=relationships, top_k=top_k)
        return [{"id": "e3"}, {"id": "e1"}]

    monkeypatch.setattr(chat_api.knowledge, "search_entities", lambda **k: list(kw))
    monkeypatch.setattr(chat_api.knowledge, "_entities", ents)
    monkeypatch.setattr(chat_api.knowledge, "get_entity", lambda eid: ents.get(eid))
    monkeypatch.setattr(chat_api, "HAS_CONTEXTUAL", True)
    monkeypatch.setattr(chat_api, "enhanced_hybrid_search", fake_enhanced)
    out = chat_api._hybrid_rerank_search({"q": "chùa", "limit": 3})
    assert out == [ents["e3"], ents["e1"], ents["e2"]]  # rerank trước, e2 bù sau
    assert captured["query"] == "chùa"
    assert captured["top_k"] == 30
    assert captured["entities"] is ents


def test_hybrid_search_filters_confine_rerank_to_allowed_pool(monkeypatch):
    """Có filter cấu trúc: hit ngoài pool đã lọc bị loại, dù resolve được entity."""
    ents = {**_ents3(), "e9": {"id": "e9", "name": "Ngoài pool"}}
    kw = [ents["e1"], ents["e2"]]  # pool đã qua filter entity_type
    monkeypatch.setattr(chat_api.knowledge, "search_entities", lambda **k: list(kw))
    monkeypatch.setattr(chat_api.knowledge, "_entities", ents)
    monkeypatch.setattr(chat_api.knowledge, "get_entity", lambda eid: ents.get(eid))
    monkeypatch.setattr(chat_api, "HAS_CONTEXTUAL", True)
    monkeypatch.setattr(chat_api, "enhanced_hybrid_search",
                        lambda **k: [{"id": "e9"}, {"id": "e2"}])
    out = chat_api._hybrid_rerank_search({"q": "x", "entity_type": "dish", "limit": 2})
    assert out == [ents["e2"], ents["e1"]]
    assert ents["e9"] not in out


def test_hybrid_search_falls_back_on_rerank_exception(monkeypatch):
    ents = _ents3()
    kw = [ents["e1"], ents["e2"], ents["e3"]]
    monkeypatch.setattr(chat_api.knowledge, "search_entities", lambda **k: list(kw))
    monkeypatch.setattr(chat_api.knowledge, "_entities", ents)
    monkeypatch.setattr(chat_api, "HAS_CONTEXTUAL", True)
    monkeypatch.setattr(chat_api, "enhanced_hybrid_search",
                        lambda **k: (_ for _ in ()).throw(ValueError("index hỏng")))
    out = chat_api._hybrid_rerank_search({"q": "chùa", "limit": 2})
    assert out == [ents["e1"], ents["e2"]]  # keyword fallback nguyên thứ tự


# ══════════════════ _extract_reply_entities ══════════════════


def test_extract_reply_entities_bold_then_headers():
    history = [
        {"role": "user", "content": "Trà Vinh có gì?"},
        {"role": "assistant",
         "content": "Bạn nên ghé **Ao Bà Om**.\n## Chùa Hang Trà Vinh\nRất đẹp."},
    ]
    out = chat_api._extract_reply_entities(history)
    assert out == ["Ao Bà Om", "Chùa Hang Trà Vinh"]  # bold đứng trước header


def test_extract_reply_entities_uses_nearest_assistant_turn():
    history = [
        {"role": "assistant", "content": "**Cũ Hơn Nhiều**"},
        {"role": "user", "content": "còn gì nữa?"},
        {"role": "assistant", "content": "**Mới Nhất Đây**"},
    ]
    assert chat_api._extract_reply_entities(history) == ["Mới Nhất Đây"]


def test_extract_reply_entities_window_only_last_six_turns():
    history = [{"role": "assistant", "content": "**Chùa Cổ Xưa**"}]
    history += [{"role": "user", "content": f"hỏi {i}"} for i in range(6)]
    assert chat_api._extract_reply_entities(history) == []


def test_extract_reply_entities_plain_reply_yields_empty():
    history = [{"role": "assistant", "content": "Không có định dạng gì đặc biệt."}]
    assert chat_api._extract_reply_entities(history) == []


# ══════════════════ _resolve_anaphors ══════════════════


def test_resolve_anaphors_substitutes_matching_entity():
    out = chat_api._resolve_anaphors(
        "từ chợ đến bảo tàng",
        "từ chợ đến bảo tàng",
        ["Bảo tàng Văn hóa Khmer"],
    )
    assert out == "từ chợ đến Bảo tàng Văn hóa Khmer"


def test_resolve_anaphors_skips_entity_not_longer_enough():
    """Entity phải dài hơn anaphor + 3 ký tự mới được thế."""
    msg = "tới bảo tàng"
    out = chat_api._resolve_anaphors(msg, msg, ["Bảo tàng X"])
    assert out == msg


def test_resolve_anaphors_requires_type_keyword_match():
    msg = "khách sạn nào tốt"
    out = chat_api._resolve_anaphors(msg, msg, ["Bảo tàng Văn hóa Khmer"])
    assert out == msg  # entity không mang keyword nhóm "khách sạn"


# ══════════════════ _resolve_pronouns ══════════════════


def test_resolve_pronouns_replaces_with_top_entity():
    out = chat_api._resolve_pronouns("ăn gì ở đó", ["Cồn Chim", "Ao Bà Om"])
    assert out == "ăn gì tại Cồn Chim"  # luôn dùng entity ĐẦU danh sách


def test_resolve_pronouns_no_pronoun_no_change():
    assert chat_api._resolve_pronouns("ăn gì ngon", ["Cồn Chim"]) == "ăn gì ngon"


# ══════════════════ _resolve_contextual_query ══════════════════


def _history_with_museum():
    return [
        {"role": "user", "content": "Có bảo tàng nào ở Trà Vinh?"},
        {"role": "assistant", "content": "Bạn nên ghé **Bảo tàng Văn hóa Khmer** nhé."},
    ]


def test_resolve_contextual_query_no_history_passthrough():
    assert chat_api._resolve_contextual_query("tới bảo tàng", []) == "tới bảo tàng"


def test_resolve_contextual_query_no_anaphor_passthrough():
    msg = "cho mình lịch mở cửa"
    assert chat_api._resolve_contextual_query(msg, _history_with_museum()) == msg


def test_resolve_contextual_query_resolves_anaphor_from_history():
    out = chat_api._resolve_contextual_query("đường đi tới bảo tàng", _history_with_museum())
    assert out == "đường đi tới Bảo tàng Văn hóa Khmer"


def test_resolve_contextual_query_resolves_pronoun_from_history():
    history = [
        {"role": "user", "content": "chỗ nào ngắm chim?"},
        {"role": "assistant", "content": "**Cồn Chim** là lựa chọn hay."},
    ]
    out = chat_api._resolve_contextual_query("cách đi đến đó thế nào", history)
    assert out == "cách đi tại Cồn Chim thế nào"


def test_resolve_contextual_query_no_entities_in_reply_passthrough():
    history = [
        {"role": "user", "content": "hỏi chơi"},
        {"role": "assistant", "content": "Trả lời trơn, không bold không header."},
    ]
    msg = "đường đi tới bảo tàng"
    assert chat_api._resolve_contextual_query(msg, history) == msg


# ══════════════════ _fold_lazy_prompt ══════════════════


def test_fold_lazy_prompt_appends_builder_output():
    out = chat_api._fold_lazy_prompt(lambda m: f"EXTRA({m})", "tin nhắn", "GỐC", "nhãn")
    assert out == "GỐC\nEXTRA(tin nhắn)"


def test_fold_lazy_prompt_none_ctx_becomes_newline_extra():
    out = chat_api._fold_lazy_prompt(lambda m: "EXTRA", "m", None, "nhãn")
    assert out == "\nEXTRA"


def test_fold_lazy_prompt_empty_output_keeps_ctx():
    assert chat_api._fold_lazy_prompt(lambda m: "", "m", "GỐC", "nhãn") == "GỐC"
    assert chat_api._fold_lazy_prompt(lambda m: None, "m", "GỐC", "nhãn") == "GỐC"


def test_fold_lazy_prompt_swallows_builder_exception():
    out = chat_api._fold_lazy_prompt(lambda m: 1 / 0, "m", "GỐC", "nhãn")
    assert out == "GỐC"


# ══════════════════ _fold_experience_fewshot ══════════════════


def test_fold_experience_fewshot_simple_query_skips_heavy_modules(monkeypatch):
    called = []
    monkeypatch.setattr(chat_api, "HAS_EXPERIENCE", True)
    monkeypatch.setattr(chat_api, "HAS_FEWSHOT", True)
    monkeypatch.setattr(chat_api, "experience_memory",
                        SimpleNamespace(build_prompt=lambda m: called.append("exp")))
    monkeypatch.setattr(chat_api, "prompt_compiler",
                        SimpleNamespace(build_prompt=lambda m: called.append("few")))
    out = chat_api._fold_experience_fewshot("chùa nào đẹp nhất", "GỐC")
    assert out == "GỐC"
    assert called == []  # query đơn giản → module nặng không được đụng


def test_fold_experience_fewshot_complex_query_folds_both(monkeypatch):
    monkeypatch.setattr(chat_api, "HAS_EXPERIENCE", True)
    monkeypatch.setattr(chat_api, "HAS_FEWSHOT", True)
    monkeypatch.setattr(chat_api, "experience_memory",
                        SimpleNamespace(build_prompt=lambda m: "KINH NGHIỆM"))
    monkeypatch.setattr(chat_api, "prompt_compiler",
                        SimpleNamespace(build_prompt=lambda m: "VÍ DỤ MẪU"))
    out = chat_api._fold_experience_fewshot("lên lịch trình 2 hôm ở Vĩnh Long", "GỐC")
    assert out == "GỐC\nKINH NGHIỆM\nVÍ DỤ MẪU"


def test_fold_experience_fewshot_flags_off_no_change(monkeypatch):
    monkeypatch.setattr(chat_api, "HAS_EXPERIENCE", False)
    monkeypatch.setattr(chat_api, "HAS_FEWSHOT", False)
    out = chat_api._fold_experience_fewshot("so sánh hai cồn", "GỐC")
    assert out == "GỐC"


# ══════════════════ _tool_ocop_products ══════════════════


def _install_ocop_entities(monkeypatch, extra=None):
    ents = {
        "keo-dua": {
            "id": "keo-dua", "name": "Kẹo dừa Bến Tre", "type": "product",
            "summary": "Đặc sản truyền thống của xứ dừa.",
            "coords": [10.1, 106.2],
            "attributes": {"ocop_star": 5, "province_old": "Bến Tre",
                           "address": "ấp An Thuận", "phone": "0270 000 000"},
        },
        "mat-hoa-dua": {
            "id": "mat-hoa-dua", "name": "Mật hoa dừa", "type": "product",
            "summary": "Thức uống thiên nhiên.",
            "attributes": {"ocop_star": 3, "province_old": "Trà Vinh"},
        },
        "khong-ocop": {
            "id": "khong-ocop", "name": "Bánh tét", "type": "dish",
            "summary": "Món quen.", "attributes": {},
        },
    }
    ents.update(extra or {})
    monkeypatch.setattr(chat_api.knowledge, "_entities", ents)
    monkeypatch.setattr(chat_api.knowledge, "get_place", lambda eid: None)
    return ents


def test_tool_ocop_products_cards_sorted_by_star_desc(monkeypatch):
    _install_ocop_entities(monkeypatch)
    out = json.loads(chat_api._tool_ocop_products({}))
    assert [c["id"] for c in out] == ["keo-dua", "mat-hoa-dua"]  # 5 sao trước 3 sao
    assert out[0] == {
        "id": "keo-dua", "name": "Kẹo dừa Bến Tre", "ocop": "OCOP 5 sao",
        "summary": "Đặc sản truyền thống của xứ dừa.", "province": "Bến Tre",
        "address": "ấp An Thuận", "phone": "0270 000 000", "coords": [10.1, 106.2],
    }
    assert "_star" not in out[0] and "_star" not in out[1]  # khoá sort nội bộ đã pop
    assert out[1]["ocop"] == "OCOP 3 sao" and out[1]["address"] == ""


def test_tool_ocop_products_min_stars_keeps_unknown_tier(monkeypatch):
    """star=0 (có dấu hiệu OCOP nhưng chưa rõ hạng) KHÔNG bị chặn bởi min_stars."""
    _install_ocop_entities(monkeypatch, extra={
        "tieu-bieu": {
            "id": "tieu-bieu", "name": "Sản phẩm làng nghề", "type": "product",
            "summary": "Hàng thủ công.", "attributes": {"ocop": "Sản phẩm OCOP tiêu biểu"},
        },
    })
    out = json.loads(chat_api._tool_ocop_products({"min_stars": 4}))
    assert [c["id"] for c in out] == ["keo-dua", "tieu-bieu"]  # 3 sao rớt, hạng-0 vẫn qua
    assert out[1]["ocop"] == "OCOP"


def test_tool_ocop_products_area_filter_via_province_old(monkeypatch):
    _install_ocop_entities(monkeypatch)
    out = json.loads(chat_api._tool_ocop_products({"area": "ben-tre"}))
    assert [c["id"] for c in out] == ["keo-dua"]


def test_tool_ocop_products_category_drink(monkeypatch):
    _install_ocop_entities(monkeypatch)
    out = json.loads(chat_api._tool_ocop_products({"category": "drink"}))
    assert [c["id"] for c in out] == ["mat-hoa-dua"]  # "mật" nằm trong nhóm đồ uống


# ══════════════════ _tool_accommodation_search ══════════════════


def _install_accom_entities(monkeypatch):
    ents = {
        "hs-con-chim": {
            "id": "hs-con-chim", "name": "Homestay Cồn Chim", "type": "accommodation",
            "summary": "Nhà vườn giữa cù lao, hợp gia đình.",
            "coords": [9.9, 106.3],
            "attributes": {"province_old": "Trà Vinh", "address": "ấp Cồn Chim",
                           "phone": "0294 111 222", "price_range": "500k/đêm",
                           "hours": "nhận phòng 14:00", "booking_note": "Đặt trước 2 hôm"},
        },
        "ks-cuu-long": {
            "id": "ks-cuu-long", "name": "Khách sạn Cửu Long", "type": "accommodation",
            "summary": "Trung tâm thành phố.",
            "attributes": {"province_old": "Vĩnh Long"},
        },
        "cho-noi": {
            "id": "cho-noi", "name": "Chợ nổi", "type": "attraction",
            "summary": "Không phải chỗ ở.", "attributes": {},
        },
    }
    monkeypatch.setattr(chat_api.knowledge, "_entities", ents)
    monkeypatch.setattr(chat_api.knowledge, "get_place", lambda eid: None)
    return ents


def test_tool_accommodation_default_lists_only_accommodation(monkeypatch):
    _install_accom_entities(monkeypatch)
    out = json.loads(chat_api._tool_accommodation_search({}))
    assert [c["id"] for c in out] == ["hs-con-chim", "ks-cuu-long"]  # attraction bị loại
    assert out[0] == {
        "id": "hs-con-chim", "name": "Homestay Cồn Chim",
        "summary": "Nhà vườn giữa cù lao, hợp gia đình.", "province": "Trà Vinh",
        "address": "ấp Cồn Chim", "price": "500k/đêm", "phone": "0294 111 222",
        "check_in": "nhận phòng 14:00", "booking_note": "Đặt trước 2 hôm",
        "coords": [9.9, 106.3],
    }
    assert out[1] == {
        "id": "ks-cuu-long", "name": "Khách sạn Cửu Long",
        "summary": "Trung tâm thành phố.", "province": "Vĩnh Long", "address": "",
    }


def test_tool_accommodation_type_filter(monkeypatch):
    _install_accom_entities(monkeypatch)
    out = json.loads(chat_api._tool_accommodation_search({"type": "hotel"}))
    assert [c["id"] for c in out] == ["ks-cuu-long"]


def test_tool_accommodation_family_friendly_filter(monkeypatch):
    _install_accom_entities(monkeypatch)
    out = json.loads(chat_api._tool_accommodation_search({"family_friendly": True}))
    assert [c["id"] for c in out] == ["hs-con-chim"]  # "gia đình" trong summary


def test_tool_accommodation_respects_limit(monkeypatch):
    _install_accom_entities(monkeypatch)
    out = json.loads(chat_api._tool_accommodation_search({"limit": 1}))
    assert len(out) == 1


# ══════════════════ _tool_nearby_entities ══════════════════


def test_tool_nearby_enriches_from_entity_attributes(monkeypatch):
    seen = {}

    def fake_nearby(entity_id, limit):
        seen["args"] = (entity_id, limit)
        return [
            {"id": "n1", "name": "Nhà cổ", "distance_km": 1.2},
            {"id": "n2", "name": "Bến đò", "distance_km": 2.5},
        ]

    monkeypatch.setattr(chat_api.knowledge, "nearby_entities", fake_nearby)
    monkeypatch.setattr(chat_api.knowledge, "_entities", {
        "n1": {"id": "n1", "name": "Nhà cổ", "coords": [9.94, 106.34],
               "attributes": {"hours": "07:00-17:00", "admission_fee": "20.000đ"}},
        # n2 cố ý vắng mặt → card giữ nguyên như knowledge trả về
    })
    out = json.loads(chat_api._tool_nearby_entities({"entity_id": "goc-x"}))
    assert seen["args"] == ("goc-x", 8)  # limit mặc định 8
    assert out[0] == {"id": "n1", "name": "Nhà cổ", "distance_km": 1.2,
                      "hours": "07:00-17:00", "admission_fee": "20.000đ",
                      "coords": [9.94, 106.34]}
    assert out[1] == {"id": "n2", "name": "Bến đò", "distance_km": 2.5}


def test_tool_nearby_forwards_explicit_limit(monkeypatch):
    seen = {}
    monkeypatch.setattr(chat_api.knowledge, "nearby_entities",
                        lambda eid, limit: seen.setdefault("args", (eid, limit)) and [] or [])
    monkeypatch.setattr(chat_api.knowledge, "_entities", {})
    out = json.loads(chat_api._tool_nearby_entities({"entity_id": "e", "limit": 3}))
    assert out == []
    assert seen["args"] == ("e", 3)


# ══════════════════ _tool_community_reviews / _tool_trending_posts (UGC) ══════════════════


def test_tool_community_reviews_returns_reviews_and_count(monkeypatch):
    reviews = [{"author": "an", "rating": 5, "content": "tuyệt"}]
    seen = _install_fake_social(monkeypatch, reviews=reviews)
    out = json.loads(chat_api._tool_community_reviews({"entity_id": "con-chim", "limit": 2}))
    assert out == {"reviews": reviews, "count": 1}
    assert seen["reviews_args"] == ("con-chim", 2)


def test_tool_community_reviews_empty_returns_note(monkeypatch):
    _install_fake_social(monkeypatch, reviews=[])
    out = json.loads(chat_api._tool_community_reviews({"entity_id": "con-chim"}))
    assert out == {"reviews": [], "note": "Chưa có đánh giá cộng đồng cho 'con-chim'"}


# Nhánh except của 2 tool UGC: defect cũ (logger.warning %-style nổ TypeError
# trong chính câu log vì StructuredLogger.warning chỉ nhận **kw) ĐÃ SỬA — nay
# khoá hành vi ĐÚNG: social nổ → JSON degrade mềm, không propagate.


def test_tool_community_reviews_social_error_degrades_to_json(monkeypatch):
    _install_fake_social(monkeypatch, exc=RuntimeError("social hỏng"))
    out = json.loads(chat_api._tool_community_reviews({"entity_id": "con-chim"}))
    assert out == {"reviews": [], "error": "Không thể tải đánh giá"}


def test_tool_trending_posts_social_error_degrades_to_json(monkeypatch):
    _install_fake_social(monkeypatch, exc=RuntimeError("social hỏng"))
    out = json.loads(chat_api._tool_trending_posts({}))
    assert out == {"posts": [], "error": "Không thể tải bài viết"}


def test_tool_trending_posts_returns_posts_and_count(monkeypatch):
    posts = [{"id": 1, "title": "Đi Cồn Chim"}, {"id": 2, "title": "Ẩm thực"}]
    seen = _install_fake_social(monkeypatch, posts=posts)
    out = json.loads(chat_api._tool_trending_posts({"entity_type": "attraction", "limit": 4}))
    assert out == {"posts": posts, "count": 2}
    assert seen["posts_args"] == (4, "attraction")  # (limit, entity_type)


def test_tool_trending_posts_empty_returns_note(monkeypatch):
    seen = _install_fake_social(monkeypatch, posts=[])
    out = json.loads(chat_api._tool_trending_posts({}))
    assert out == {"posts": [], "note": "Chưa có bài viết nổi bật"}
    assert seen["posts_args"] == (10, None)  # limit mặc định 10, không lọc type


# ══════════════════ _tool_directory_lookup ══════════════════


def test_tool_directory_lookup_returns_results(monkeypatch):
    rows = [{"name": "UBND phường Long Châu", "phone": "0270"}]
    seen = {}
    monkeypatch.setattr(chat_api.knowledge, "directory_search",
                        lambda q: seen.setdefault("q", q) and rows or rows)
    out = json.loads(chat_api._tool_directory_lookup({"query": "long châu"}))
    assert out == {"results": rows}
    assert seen["q"] == "long châu"


def test_tool_directory_lookup_empty_returns_note_and_default_query(monkeypatch):
    seen = {}

    def fake_dir(q):
        seen["q"] = q
        return []

    monkeypatch.setattr(chat_api.knowledge, "directory_search", fake_dir)
    out = json.loads(chat_api._tool_directory_lookup({}))
    assert out == {
        "results": [],
        "note": "Chưa có dữ liệu danh bạ hành chính cho yêu cầu này (đang bổ sung từ nguồn chính thống).",
    }
    assert seen["q"] == ""  # thiếu 'query' → mặc định chuỗi rỗng, không lỗi
