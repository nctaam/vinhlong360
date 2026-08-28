"""
Characterization tests cho các hàm chưa phủ của learn_loop.py.

Đặc tả HÀNH VI HIỆN TẠI. Đợt fix 2026-08-28 sửa 2 bug trong module đích
(keyword 'OCOP' hạ chữ thường; _find_best_snippet bỏ qua body rỗng) — các test
tương ứng khoá hành vi ĐÚNG sau fix:
  - Nhóm heuristics thuần: _clean_entity_name, _slugify_entity_name,
    _detect_area, _detect_entity_type, _truncate_summary, _find_best_snippet.
  - Nhóm có I/O ngoài: _web_search_light (mock ddgs), _geocode_candidate /
    _geocode_entity_inline (mock geocode), _collect_existing_keys (mock database).
  - Nhóm pipeline gap: _extract_entity_from_snippet, _accept_gap_candidate,
    _process_gap_results.
  - Nhóm feedback/log: _adjust_entity_confidence, process_feedback_batch,
    _log_event, _status_recent_events.

Mọi đường ghi đều trỏ vào tmp_path (DATA_JSON / FEEDBACK_FILE / LEARN_LOG được
monkeypatch), module `database` / `knowledge` / `kb_curation` / `geocode` /
`ddgs` được thay bằng fake trong sys.modules — không chạm DB thật, không network.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import learn_loop


def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ══════════════════════════════════════════════════
#  Heuristics thuần
# ══════════════════════════════════════════════════

class TestCleanEntityName:
    def test_removes_sitename_suffix_after_dash(self):
        assert learn_loop._clean_entity_name("Chùa Tiên Châu - VnExpress") == "Chùa Tiên Châu"

    def test_removes_em_dash_suffix_and_trailing_parens(self):
        # Cả hai lớp: bỏ " – SiteName" rồi bỏ "(...)" cuối chuỗi.
        assert learn_loop._clean_entity_name("Cầu Mỹ Thuận (mới) – Báo Vĩnh Long") == "Cầu Mỹ Thuận"

    def test_keeps_long_suffix_beyond_30_chars(self):
        # Đuôi sau dấu gạch dài hơn 30 ký tự thì regex không khớp → giữ nguyên.
        title = "Chùa Tiên Châu - " + "x" * 40
        assert learn_loop._clean_entity_name(title) == title

    def test_too_short_name_returns_none(self):
        assert learn_loop._clean_entity_name("Abc") is None

    def test_too_long_name_returns_none(self):
        assert learn_loop._clean_entity_name("A" * 101) is None


class TestSlugifyEntityName:
    def test_strips_diacritics_and_joins_with_hyphen(self):
        assert learn_loop._slugify_entity_name("Chùa Phước Hậu") == "chua-phuoc-hau"

    def test_d_stroke_becomes_d(self):
        # "đ" không phân rã qua NFD nên có nhánh replace riêng.
        assert learn_loop._slugify_entity_name("Đình Bình Đông") == "dinh-binh-dong"

    def test_slug_truncated_to_60_chars(self):
        slug = learn_loop._slugify_entity_name("a" * 80)
        assert slug == "a" * 60

    def test_slug_shorter_than_3_returns_none(self):
        assert learn_loop._slugify_entity_name("Đà!") is None

    def test_only_symbols_returns_none(self):
        assert learn_loop._slugify_entity_name("!!!") is None


class TestDetectArea:
    def test_vinh_long(self):
        assert learn_loop._detect_area("Chợ nổi ở Vĩnh Long") == "vinh-long"

    def test_ben_tre_lowercase(self):
        assert learn_loop._detect_area("dừa bến tre ngon") == "ben-tre"

    def test_tra_vinh(self):
        assert learn_loop._detect_area("Ao Bà Om Trà Vinh") == "tra-vinh"

    def test_vinh_long_wins_when_multiple_areas_present(self):
        # Thứ tự dict quyết định: vinh-long được thử trước.
        assert learn_loop._detect_area("Từ Vĩnh Long qua Bến Tre") == "vinh-long"

    def test_unrelated_text_returns_none(self):
        assert learn_loop._detect_area("Chùa Bái Đính ở Ninh Bình") is None


class TestDetectEntityType:
    def test_dish_keyword(self):
        assert learn_loop._detect_entity_type("Món bún riêu nổi tiếng") == "dish"

    def test_product_keyword(self):
        assert learn_loop._detect_entity_type("đặc sản OCOP nổi bật") == "product"

    def test_attraction_wins_over_nature_by_dict_order(self):
        # "chùa" (attraction) được duyệt trước "sông" (nature).
        assert learn_loop._detect_entity_type("ngôi chùa cổ ven sông") == "attraction"

    def test_nature_keyword(self):
        assert learn_loop._detect_entity_type("cù lao xanh giữa dòng") == "nature"

    def test_event_keyword(self):
        assert learn_loop._detect_entity_type("lễ hội Ok Om Bok") == "event"

    def test_dish_wins_over_attraction_by_dict_order(self):
        # "món" (dish) đứng trước "chùa" (attraction) trong bảng keyword.
        assert learn_loop._detect_entity_type("món chay gần chùa") == "dish"

    def test_default_is_attraction(self):
        assert learn_loop._detect_entity_type("một nơi bình thường") == "attraction"

    def test_keyword_match_is_case_insensitive(self):
        assert learn_loop._detect_entity_type("BÁNH xèo giòn rụm") == "dish"

    def test_ocop_keyword_matches_after_lowercase_fix(self):
        # Fix 2026-08-28: keyword 'OCOP' đã hạ thành 'ocop' — text bị .lower()
        # trước khi so nên bản viết HOA trong bảng không bao giờ khớp được.
        assert learn_loop._detect_entity_type("OCOP 4 sao tiêu biểu") == "product"


class TestTruncateSummary:
    def test_short_snippet_only_stripped(self):
        assert learn_loop._truncate_summary("  ngắn gọn  ") == "ngắn gọn"

    def test_cuts_at_sentence_boundary_when_period_after_100(self):
        s = "A" * 150 + "." + "B" * 200
        assert learn_loop._truncate_summary(s) == "A" * 150 + "."

    def test_hard_cut_with_ellipsis_when_no_late_period(self):
        s = "B" * 50 + "." + "C" * 300
        out = learn_loop._truncate_summary(s)
        assert out == s[:300] + "..."
        assert len(out) == 303

    def test_exactly_300_chars_untouched(self):
        s = "D" * 300
        assert learn_loop._truncate_summary(s) == s


class TestFindBestSnippet:
    def test_returns_body_of_first_matching_result(self):
        results = [
            {"title": "Khách sạn ABC", "body": "không liên quan"},
            {"title": "Giới thiệu chùa Tiên Châu", "body": "Ngôi chùa cổ ven sông."},
            {"title": "chùa Tiên Châu khác", "body": "kết quả sau bị bỏ qua"},
        ]
        assert learn_loop._find_best_snippet(results, "Chùa Tiên Châu") == "Ngôi chùa cổ ven sông."

    def test_match_uses_5_char_prefix_over_title_plus_body(self):
        # Khớp theo 5 ký tự đầu của tên (lowercase), tìm trong body+title.
        results = [{"title": "bài về CHÙA Tiên Châu", "body": "thân bài"}]
        assert learn_loop._find_best_snippet(results, "Chùa Khác Hẳn") == "thân bài"

    def test_no_match_returns_empty_string(self):
        results = [{"title": "Khách sạn", "body": "phòng đẹp"}]
        assert learn_loop._find_best_snippet(results, "Chùa Tiên Châu") == ""

    def test_empty_body_match_skipped_tries_next_result(self):
        # Fix 2026-08-28: title khớp nhưng body rỗng không còn return "" ngay —
        # duyệt tiếp để lấy body có chữ của result kế; fallback cuối vẫn là "".
        results = [
            {"title": "Chùa Tiên Châu", "body": ""},
            {"title": "Giới thiệu chùa Tiên Châu", "body": "Ngôi chùa cổ."},
        ]
        assert learn_loop._find_best_snippet(results, "Chùa Tiên Châu") == "Ngôi chùa cổ."

    def test_empty_results_returns_empty_string(self):
        assert learn_loop._find_best_snippet([], "Chùa Tiên Châu") == ""


# ══════════════════════════════════════════════════
#  _web_search_light — mock ddgs, không network
# ══════════════════════════════════════════════════

def _fake_ddgs_module(results, calls):
    class FakeDDGS:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def text(self, query, region=None, max_results=None):
            calls.append({"query": query, "region": region, "max_results": max_results})
            return list(results)

    return SimpleNamespace(DDGS=FakeDDGS)


class TestWebSearchLight:
    def test_appends_province_names_and_uses_vn_region(self, monkeypatch):
        calls = []
        fake_results = [{"title": "t", "body": "b", "href": "https://x.vn/a"}]
        monkeypatch.setitem(sys.modules, "ddgs", _fake_ddgs_module(fake_results, calls))

        out = learn_loop._web_search_light("chợ nổi", max_results=2)

        assert out == fake_results
        assert len(calls) == 1
        assert calls[0]["query"] == "chợ nổi Vĩnh Long Bến Tre Trà Vinh"
        assert calls[0]["region"] == "vn-vi"
        assert calls[0]["max_results"] == 2

    def test_search_failure_returns_empty_list(self, monkeypatch):
        class BoomDDGS:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def text(self, *a, **kw):
                raise RuntimeError("network down")

        monkeypatch.setitem(sys.modules, "ddgs", SimpleNamespace(DDGS=BoomDDGS))
        assert learn_loop._web_search_light("bất kỳ") == []


# ══════════════════════════════════════════════════
#  _collect_existing_keys — mock database
# ══════════════════════════════════════════════════

class TestCollectExistingKeys:
    KB = {"entities": [
        {"id": "a", "name": "Chùa Á"},
        {"id": "b", "name": "Bến Xe"},
    ]}

    def test_merges_kb_and_db_keys(self, monkeypatch):
        seen = {}

        def fake_search(query, limit=None):
            seen["args"] = (query, limit)
            return [
                {"id": "db-1", "name": "Đình Đỏ"},
                {"id": "", "name": ""},  # hàng rỗng bị bỏ qua
            ]

        monkeypatch.setitem(
            sys.modules, "database",
            SimpleNamespace(db=SimpleNamespace(search_entities=fake_search)),
        )
        ids, names = learn_loop._collect_existing_keys(self.KB)

        assert ids == {"a", "b", "db-1"}
        # Tên đã chuẩn hoá: bỏ dấu, lower, đ→d.
        assert names == {"chua a", "ben xe", "dinh do"}
        assert seen["args"] == ("", 5000)

    def test_db_failure_falls_back_to_kb_only(self, monkeypatch):
        def boom(query, limit=None):
            raise RuntimeError("no db")

        monkeypatch.setitem(
            sys.modules, "database",
            SimpleNamespace(db=SimpleNamespace(search_entities=boom)),
        )
        ids, names = learn_loop._collect_existing_keys(self.KB)
        assert ids == {"a", "b"}
        assert names == {"chua a", "ben xe"}


# ══════════════════════════════════════════════════
#  _extract_entity_from_snippet
# ══════════════════════════════════════════════════

class TestExtractEntityFromSnippet:
    TITLE = "Chùa Tiên Châu - Báo ABC"
    SNIPPET = "Chùa Tiên Châu là ngôi chùa cổ nằm bên bờ sông Cổ Chiên, tỉnh Vĩnh Long."
    URL = "https://example.com/chua-tien-chau"

    def test_happy_path_shape(self):
        entity = learn_loop._extract_entity_from_snippet(
            self.SNIPPET, self.TITLE, self.URL, "chùa tiên châu")

        assert entity["id"] == "chua-tien-chau"
        assert entity["name"] == "Chùa Tiên Châu"
        # "chùa" (attraction) đứng trước "sông" (nature) trong bảng keyword.
        assert entity["type"] == "attraction"
        assert entity["summary"] == self.SNIPPET[:300]
        assert entity["confidence"] == 0.4
        assert entity["status"] == "provisional"
        assert entity["verified"] is False
        assert entity["source"] == {"title": "example.com", "url": self.URL}
        assert entity["learned_at"] == _today_utc()
        assert entity["updatedAt"] == _today_utc()
        assert entity["placeId"] is None
        assert entity["attributes"] == {}
        assert entity["images"] == []

    def test_short_text_returns_none(self):
        assert learn_loop._extract_entity_from_snippet("", "Chùa A", "https://x.vn/a", "q") is None

    def test_no_area_returns_none(self):
        out = learn_loop._extract_entity_from_snippet(
            "Ngôi chùa nổi tiếng với kiến trúc độc đáo ở Ninh Bình.",
            "Chùa Bái Đính", "https://x.vn/a", "q")
        assert out is None

    def test_invalid_cleaned_name_returns_none(self):
        out = learn_loop._extract_entity_from_snippet(
            "Địa điểm ở Vĩnh Long rất đẹp và nổi tiếng khắp vùng.",
            "Abc", "https://x.vn/a", "q")
        assert out is None

    def test_url_without_slash_gets_web_source_title(self):
        entity = learn_loop._extract_entity_from_snippet(
            self.SNIPPET, self.TITLE, "nourl", "q")
        assert entity["source"] == {"title": "web", "url": "nourl"}


# ══════════════════════════════════════════════════
#  _accept_gap_candidate — mock kb_curation
# ══════════════════════════════════════════════════

def _candidate(name="Chợ Nổi Trà Ôn", eid="cho-noi-tra-on", etype="attraction"):
    return {"id": eid, "name": name, "type": etype}


class TestAcceptGapCandidate:
    KB = {"entities": []}

    def _patch_curation(self, monkeypatch, dup=None, boom=False):
        def find_near_duplicate(name, etype, entities):
            if boom:
                raise RuntimeError("curation down")
            return dup

        monkeypatch.setitem(
            sys.modules, "kb_curation",
            SimpleNamespace(find_near_duplicate=find_near_duplicate),
        )

    def test_passes_all_gates(self, monkeypatch):
        self._patch_curation(monkeypatch, dup=None)
        assert learn_loop._accept_gap_candidate(_candidate(), self.KB, set(), set()) is True

    def test_duplicate_id_rejected(self, monkeypatch):
        self._patch_curation(monkeypatch, dup=None)
        ok = learn_loop._accept_gap_candidate(
            _candidate(), self.KB, {"cho-noi-tra-on"}, set())
        assert ok is False

    def test_duplicate_name_diacritic_insensitive(self, monkeypatch):
        self._patch_curation(monkeypatch, dup=None)
        # Tên tồn tại dưới dạng đã chuẩn hoá "cho noi tra on" chặn cả bản viết hoa/có dấu.
        ok = learn_loop._accept_gap_candidate(
            _candidate(name="CHỢ NỔI TRÀ ÔN"), self.KB, set(), {"cho noi tra on"})
        assert ok is False

    def test_near_duplicate_rejected(self, monkeypatch):
        self._patch_curation(monkeypatch, dup="cho-noi-tra-on-cu")
        assert learn_loop._accept_gap_candidate(_candidate(), self.KB, set(), set()) is False

    def test_curation_failure_lets_candidate_through(self, monkeypatch):
        self._patch_curation(monkeypatch, boom=True)
        assert learn_loop._accept_gap_candidate(_candidate(), self.KB, set(), set()) is True


# ══════════════════════════════════════════════════
#  _process_gap_results
# ══════════════════════════════════════════════════

class TestProcessGapResults:
    RESULTS = [
        {  # hợp lệ: có vùng, tên sạch, đủ dài
            "title": "Chùa Tiên Châu - Báo ABC",
            "body": "Chùa Tiên Châu là ngôi chùa cổ nằm bên bờ sông Cổ Chiên, tỉnh Vĩnh Long.",
            "href": "https://example.com/chua-tien-chau",
        },
        {  # không nhắc vùng nào → extract trả None
            "title": "Một bài viết khác",
            "body": "Bài viết nói về nơi hoàn toàn khác, không nhắc địa phương nào cả.",
            "href": "https://example.com/khac",
        },
    ]

    def _run(self, monkeypatch, existing_ids, existing_names, new_entities):
        monkeypatch.setitem(
            sys.modules, "kb_curation",
            SimpleNamespace(find_near_duplicate=lambda name, etype, entities: None),
        )
        geocoded = []

        def fake_inline(entity):
            geocoded.append(entity["id"])
            entity["coords"] = [10.25, 105.97]

        monkeypatch.setattr(learn_loop, "_geocode_entity_inline", fake_inline)
        learn_loop._process_gap_results(
            self.RESULTS, "chùa tiên châu", {"entities": []},
            existing_ids, existing_names, new_entities)
        return geocoded

    def test_valid_result_appended_and_keys_updated(self, monkeypatch):
        new_entities, ids, names = [], set(), set()
        geocoded = self._run(monkeypatch, ids, names, new_entities)

        assert [e["id"] for e in new_entities] == ["chua-tien-chau"]
        assert new_entities[0]["coords"] == [10.25, 105.97]
        assert geocoded == ["chua-tien-chau"]
        assert "chua-tien-chau" in ids
        assert "chua tien chau" in names

    def test_second_pass_dedups_via_updated_keys(self, monkeypatch):
        new_entities, ids, names = [], set(), set()
        self._run(monkeypatch, ids, names, new_entities)
        # Lần hai với cùng results: id đã nằm trong existing_ids → không thêm nữa.
        self._run(monkeypatch, ids, names, new_entities)
        assert len(new_entities) == 1


# ══════════════════════════════════════════════════
#  _geocode_entity_inline / _geocode_candidate — mock geocode
# ══════════════════════════════════════════════════

class TestGeocodeEntityInline:
    def test_sets_coords_on_success(self, monkeypatch):
        monkeypatch.setitem(
            sys.modules, "geocode",
            SimpleNamespace(geocode=lambda name: [10.0, 106.0]),
        )
        entity = {"id": "x", "name": "Chùa Tiên Châu"}
        learn_loop._geocode_entity_inline(entity)
        assert entity["coords"] == [10.0, 106.0]

    def test_no_result_leaves_entity_untouched(self, monkeypatch):
        monkeypatch.setitem(
            sys.modules, "geocode", SimpleNamespace(geocode=lambda name: None))
        entity = {"id": "x", "name": "Chùa Tiên Châu"}
        learn_loop._geocode_entity_inline(entity)
        assert "coords" not in entity

    def test_geocode_error_swallowed(self, monkeypatch):
        def boom(name):
            raise RuntimeError("osm down")

        monkeypatch.setitem(sys.modules, "geocode", SimpleNamespace(geocode=boom))
        entity = {"id": "x", "name": "Chùa Tiên Châu"}
        learn_loop._geocode_entity_inline(entity)  # không được nổ
        assert "coords" not in entity


class _FakeGeo:
    """geocode giả: trả coords theo bảng (name, region) hoặc name trần."""

    def __init__(self, mapping):
        self.mapping = mapping
        self.calls = []

    def geocode(self, name, region=None):
        self.calls.append((name, region))
        if (name, region) in self.mapping:
            return self.mapping[(name, region)]
        return self.mapping.get(name)


class TestGeocodeCandidate:
    def test_variant1_plain_name(self):
        geo = _FakeGeo({"Chùa Tiên Châu": [10.1, 105.9]})
        c = learn_loop._geocode_candidate(geo, {"name": "Chùa Tiên Châu"}, {})
        assert c == [10.1, 105.9]
        assert geo.calls == [("Chùa Tiên Châu", None)]

    def test_variant2_scoped_by_place_name(self):
        geo = _FakeGeo({("Đình Long Thanh", "Phường 5"): [10.2, 105.9]})
        places = {"phuong-5": {"id": "phuong-5", "name": "Phường 5"}}
        e = {"name": "Đình Long Thanh", "placeId": "phuong-5"}
        c = learn_loop._geocode_candidate(geo, e, places)
        assert c == [10.2, 105.9]
        assert geo.calls == [("Đình Long Thanh", None), ("Đình Long Thanh", "Phường 5")]

    def test_variant3_strips_category_prefix(self):
        geo = _FakeGeo({"Cái Ngang": [10.05, 105.95]})
        e = {"name": "Khu di tích Cái Ngang"}
        c = learn_loop._geocode_candidate(geo, e, {})
        assert c == [10.05, 105.95]
        assert geo.calls == [("Khu di tích Cái Ngang", None), ("Cái Ngang", None)]

    def test_all_variants_fail_returns_none(self):
        geo = _FakeGeo({})
        # Không có prefix bóc được → chỉ thử đúng 1 biến thể rồi chịu.
        c = learn_loop._geocode_candidate(geo, {"name": "Cồn Phụng"}, {})
        assert c is None
        assert geo.calls == [("Cồn Phụng", None)]


# ══════════════════════════════════════════════════
#  _adjust_entity_confidence — DATA_JSON tạm + database giả
# ══════════════════════════════════════════════════

def _write_kb(tmp_path, entities):
    data_path = tmp_path / "data.json"
    data_path.write_text(
        json.dumps({"entities": entities, "relationships": [], "itineraries": []},
                   ensure_ascii=False),
        encoding="utf-8",
    )
    return data_path


def _patch_db(monkeypatch, known_ids, upserts):
    monkeypatch.setitem(
        sys.modules, "database",
        SimpleNamespace(db=SimpleNamespace(
            get_entity=lambda eid: {"id": eid} if eid in known_ids else None,
            upsert_entity=lambda entity: upserts.append(entity),
        )),
    )


class TestAdjustEntityConfidence:
    def test_negative_delta_lowers_and_stamps_updated_at(self, tmp_path, monkeypatch):
        data_path = _write_kb(tmp_path, [{"id": "e1", "name": "E1", "confidence": 0.5}])
        monkeypatch.setattr(learn_loop, "DATA_JSON", data_path)
        upserts = []
        _patch_db(monkeypatch, {"e1"}, upserts)

        learn_loop._adjust_entity_confidence("e1", delta=-0.05)

        saved = json.loads(data_path.read_text(encoding="utf-8"))
        assert saved["entities"][0]["confidence"] == 0.45
        assert saved["entities"][0]["updatedAt"] == _today_utc()
        assert [u["id"] for u in upserts] == ["e1"]
        assert upserts[0]["confidence"] == 0.45

    def test_clamped_to_floor_0_1(self, tmp_path, monkeypatch):
        data_path = _write_kb(tmp_path, [{"id": "e1", "name": "E1", "confidence": 0.12}])
        monkeypatch.setattr(learn_loop, "DATA_JSON", data_path)
        _patch_db(monkeypatch, set(), [])

        learn_loop._adjust_entity_confidence("e1", delta=-0.1)

        saved = json.loads(data_path.read_text(encoding="utf-8"))
        assert saved["entities"][0]["confidence"] == 0.1

    def test_clamped_to_ceiling_1_0(self, tmp_path, monkeypatch):
        data_path = _write_kb(tmp_path, [{"id": "e1", "name": "E1", "confidence": 0.99}])
        monkeypatch.setattr(learn_loop, "DATA_JSON", data_path)
        _patch_db(monkeypatch, set(), [])

        learn_loop._adjust_entity_confidence("e1", delta=+0.02)

        saved = json.loads(data_path.read_text(encoding="utf-8"))
        assert saved["entities"][0]["confidence"] == 1.0

    def test_missing_confidence_defaults_to_0_7(self, tmp_path, monkeypatch):
        data_path = _write_kb(tmp_path, [{"id": "e1", "name": "E1"}])
        monkeypatch.setattr(learn_loop, "DATA_JSON", data_path)
        _patch_db(monkeypatch, set(), [])

        learn_loop._adjust_entity_confidence("e1", delta=+0.02)

        saved = json.loads(data_path.read_text(encoding="utf-8"))
        assert saved["entities"][0]["confidence"] == 0.72

    def test_unknown_entity_leaves_file_and_db_alone(self, tmp_path, monkeypatch):
        data_path = _write_kb(tmp_path, [{"id": "e1", "name": "E1", "confidence": 0.5}])
        before = data_path.read_text(encoding="utf-8")
        monkeypatch.setattr(learn_loop, "DATA_JSON", data_path)
        upserts = []
        _patch_db(monkeypatch, {"e1"}, upserts)

        learn_loop._adjust_entity_confidence("khong-ton-tai", delta=-0.05)

        assert data_path.read_text(encoding="utf-8") == before
        assert upserts == []

    def test_entity_absent_from_db_still_updates_json(self, tmp_path, monkeypatch):
        data_path = _write_kb(tmp_path, [{"id": "e1", "name": "E1", "confidence": 0.5}])
        monkeypatch.setattr(learn_loop, "DATA_JSON", data_path)
        upserts = []
        _patch_db(monkeypatch, set(), upserts)  # DB không biết e1

        learn_loop._adjust_entity_confidence("e1", delta=+0.02)

        saved = json.loads(data_path.read_text(encoding="utf-8"))
        assert saved["entities"][0]["confidence"] == 0.52
        assert upserts == []

    def test_missing_data_json_is_swallowed(self, tmp_path, monkeypatch):
        monkeypatch.setattr(learn_loop, "DATA_JSON", tmp_path / "khong-co.json")
        _patch_db(monkeypatch, set(), [])
        # Toàn thân hàm bọc try/except → không được nổ ra ngoài.
        learn_loop._adjust_entity_confidence("e1", delta=-0.05)


# ══════════════════════════════════════════════════
#  process_feedback_batch
# ══════════════════════════════════════════════════

class TestProcessFeedbackBatchGaps:
    def _feedback(self):
        neg_q = "Món bún nào ngon ở Vĩnh Long?"
        return (
            [{"query": neg_q, "rating": 0, "entity_id": "bun-xeo"}] * 3
            + [{"query": neg_q, "rating": 0, "entity_id": "hu-tieu"}] * 2
            + [{"query": "ok", "rating": 0, "entity_id": None}]  # query ngắn ≤5 → bỏ đếm
            + [{"query": "tốt lắm", "rating": 1, "entity_id": "e2"}] * 2
        )

    def _run(self, tmp_path, monkeypatch):
        feedback_file = tmp_path / "feedback_history.json"
        feedback_file.write_text(
            json.dumps(self._feedback(), ensure_ascii=False), encoding="utf-8")
        log_file = tmp_path / "learn_log.jsonl"
        monkeypatch.setattr(learn_loop, "FEEDBACK_FILE", feedback_file)
        monkeypatch.setattr(learn_loop, "LEARN_LOG", log_file)
        adjustments = []
        monkeypatch.setattr(
            learn_loop, "_adjust_entity_confidence",
            lambda entity_id, delta: adjustments.append((entity_id, delta)))
        result = learn_loop.process_feedback_batch()
        return result, adjustments, log_file

    def test_counts_and_threshold(self, tmp_path, monkeypatch):
        result, adjustments, _ = self._run(tmp_path, monkeypatch)

        assert result == {
            "total_feedback": 8,
            "negative_count": 6,
            "entities_adjusted": 1,
        }
        # Chỉ entity đủ 3 vote negative bị giảm mạnh; 2 vote chưa tới ngưỡng.
        assert adjustments == [("bun-xeo", -0.1)]

    def test_logs_feedback_processing_event(self, tmp_path, monkeypatch):
        _, _, log_file = self._run(tmp_path, monkeypatch)

        events = [json.loads(line) for line in
                  log_file.read_text(encoding="utf-8").strip().split("\n")]
        assert len(events) == 1
        event = events[0]
        assert event["type"] == "feedback_processing"
        assert event["negative_count"] == 6
        assert event["positive_count"] == 2
        assert event["entities_adjusted"] == 1
        # Query đã chuẩn hoá: lower + bỏ "?" cuối.
        top = {item["query"]: item["count"] for item in event["top_negative_queries"]}
        assert top == {"món bún nào ngon ở vĩnh long": 5}


# ══════════════════════════════════════════════════
#  _log_event / _status_recent_events
# ══════════════════════════════════════════════════

class TestLogEvent:
    def test_appends_jsonl_line_with_type_and_timestamp(self, tmp_path, monkeypatch):
        log_file = tmp_path / "learn_log.jsonl"
        monkeypatch.setattr(learn_loop, "LEARN_LOG", log_file)

        learn_loop._log_event("thu_nghiem", {"a": 1})
        learn_loop._log_event("thu_nghiem", {"a": 2})

        lines = log_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2
        first = json.loads(lines[0])
        assert first["type"] == "thu_nghiem"
        assert first["a"] == 1
        assert "timestamp" in first
        assert json.loads(lines[1])["a"] == 2

    def test_trims_to_5000_lines_when_over_2mb(self, tmp_path, monkeypatch):
        log_file = tmp_path / "learn_log.jsonl"
        pad = "x" * 420
        old_lines = [json.dumps({"i": n, "pad": pad}) for n in range(5100)]
        log_file.write_text("\n".join(old_lines) + "\n", encoding="utf-8")
        assert log_file.stat().st_size > 2 * 1024 * 1024
        monkeypatch.setattr(learn_loop, "LEARN_LOG", log_file)

        learn_loop._log_event("moi_nhat", {"marker": True})

        lines = log_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 5000
        # 5101 dòng sau append → giữ 5000 dòng cuối: mở đầu là dòng cũ i=101.
        assert json.loads(lines[0])["i"] == 101
        last = json.loads(lines[-1])
        assert last["type"] == "moi_nhat"
        assert last["marker"] is True

    def test_write_failure_swallowed(self, tmp_path, monkeypatch):
        # LEARN_LOG trỏ vào thư mục → open() nổ → hàm nuốt lỗi, không raise.
        monkeypatch.setattr(learn_loop, "LEARN_LOG", tmp_path)
        learn_loop._log_event("bat_ky", {"a": 1})


class TestStatusRecentEvents:
    def test_missing_log_returns_empty_list(self, tmp_path, monkeypatch):
        monkeypatch.setattr(learn_loop, "LEARN_LOG", tmp_path / "khong-co.jsonl")
        assert learn_loop._status_recent_events() == []

    def test_returns_last_10_events(self, tmp_path, monkeypatch):
        log_file = tmp_path / "learn_log.jsonl"
        log_file.write_text(
            "\n".join(json.dumps({"i": n}) for n in range(12)) + "\n",
            encoding="utf-8")
        monkeypatch.setattr(learn_loop, "LEARN_LOG", log_file)

        events = learn_loop._status_recent_events()

        assert [e["i"] for e in events] == list(range(2, 12))

    def test_malformed_line_skipped(self, tmp_path, monkeypatch):
        log_file = tmp_path / "learn_log.jsonl"
        lines = [json.dumps({"i": 0}), json.dumps({"i": 1}),
                 "khong phai json", json.dumps({"i": 3})]
        log_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        monkeypatch.setattr(learn_loop, "LEARN_LOG", log_file)

        events = learn_loop._status_recent_events()

        assert [e["i"] for e in events] == [0, 1, 3]
