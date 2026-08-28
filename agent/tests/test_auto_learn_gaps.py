"""
Characterization tests cho agent/auto_learn.py — đặc tả HÀNH VI HIỆN TẠI.

Phủ các hàm chưa có test: make_slug, content_hash, _has_vietnamese_diacritics,
_is_english_name, _normalize, is_near_duplicate, _reject_too_generic,
_reject_outside_vl, _reject_legal, filter_entity, to_entity, _accept_raw,
load_knowledge, existing_names, web_search, analyze_gaps,
extract_entities_from_text, learn_from_query, _select_queries, _save_round,
learn_round, apply_learned, main.

Mọi đường ra ngoài (DDGS, HTTP pinned, LLM, geocode/Nominatim) đều bị mock —
không network, không chạm DB thật, không ghi vào agent/learned/ của repo.
"""

import json
import os
import re
import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# auto_learn tạo OpenAI client LÚC IMPORT từ env bắt buộc → phải đặt trước import.
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:9999/v1")

import auto_learn
import geocode


class _FakeLLM:
    """Stub client OpenAI: ghi lại kwargs từng lời gọi, trả content cố định hoặc ném lỗi."""

    def __init__(self, content="", error=None):
        self.calls = []
        self._content = content
        self._error = error
        self.chat = types.SimpleNamespace(
            completions=types.SimpleNamespace(create=self._create)
        )

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        if self._error is not None:
            raise self._error
        message = types.SimpleNamespace(content=self._content)
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=message)])


@pytest.fixture(autouse=True)
def _chan_outbound(monkeypatch):
    """Chặn mặc định mọi đường ra ngoài; test nào cần thì monkeypatch đè lên."""
    monkeypatch.setattr(geocode, "geocode", lambda *a, **k: None)

    def _no_http(*_a, **_k):
        raise AssertionError("HTTP outbound phai duoc mock trong test")

    monkeypatch.setattr(auto_learn._PINNED_HTTP, "get", _no_http)

    class _NoDDGS:
        def __enter__(self):
            raise AssertionError("DDGS phai duoc mock trong test")

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(auto_learn, "DDGS", _NoDDGS)
    monkeypatch.setattr(
        auto_learn, "client", _FakeLLM(error=AssertionError("LLM phai duoc mock"))
    )


# ── make_slug / content_hash ──


def test_make_slug_bo_dau_va_thay_d():
    assert auto_learn.make_slug("Chùa Âng Trà Vinh") == "chua-ang-tra-vinh"
    # Chữ "đ" không tách được bằng NFD — module thay tường minh đ→d.
    assert auto_learn.make_slug("Đình Long Thanh") == "dinh-long-thanh"


def test_make_slug_bien_cat_60_va_rong():
    assert auto_learn.make_slug("A" * 100) == "a" * 60
    assert auto_learn.make_slug("!!!!") == ""


def test_content_hash_md5_cat_12():
    assert auto_learn.content_hash("abc") == "900150983cd2"
    assert auto_learn.content_hash("") == "d41d8cd98f00"
    assert len(auto_learn.content_hash("Vĩnh Long")) == 12


# ── _has_vietnamese_diacritics / _is_english_name / _normalize ──


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Chùa Âng", True),
        ("Cho Lach", False),
        ("ĐINH", True),  # lower() trước khi so → chữ hoa vẫn bắt được
        ("", False),
    ],
)
def test_has_vietnamese_diacritics(text, expected):
    assert auto_learn._has_vietnamese_diacritics(text) is expected


@pytest.mark.parametrize(
    "name,expected",
    [
        ("Mekong Riverside Resort", True),  # có marker "resort", không dấu
        ("Homestay Út Trinh", False),  # có marker nhưng có dấu tiếng Việt
        ("Coconut Candy Factory", True),  # không marker: ASCII, >= 3 từ
        ("An Binh", False),  # chỉ 2 từ
        ("Abc", False),  # < 6 ký tự chữ
        ("Chùa Âng", False),  # tên Việt có dấu
    ],
)
def test_is_english_name(name, expected):
    assert auto_learn._is_english_name(name) is expected


def test_normalize_bo_dau_bo_ky_hieu_giu_so():
    assert auto_learn._normalize("Chợ Lách") == "cholach"
    assert auto_learn._normalize("Đình Long Thanh 2") == "dinhlongthanh2"


# ── is_near_duplicate ──


def test_is_near_duplicate_ten_qua_ngan_khong_so():
    # norm < 4 ký tự → bỏ qua luôn cả khi trùng hệt
    assert auto_learn.is_near_duplicate("Chợ", {"Chợ"}) is None


def test_is_near_duplicate_khop_chuan_hoa():
    assert auto_learn.is_near_duplicate("chợ lách", {"Chợ Lách"}) == "Chợ Lách"


def test_is_near_duplicate_bao_ham_tren_60_phan_tram():
    assert (
        auto_learn.is_near_duplicate("Chùa Vĩnh Tràng An", {"Chùa Vĩnh Tràng"})
        == "Chùa Vĩnh Tràng"
    )


def test_is_near_duplicate_bao_ham_duoi_nguong_thi_qua():
    known = {"Khu du lịch sinh thái Cồn Phụng Bến Tre"}
    assert auto_learn.is_near_duplicate("Cồn Phụng", known) is None


def test_is_near_duplicate_bo_qua_ten_rong_trong_known():
    assert auto_learn.is_near_duplicate("Chùa Âng", {"", "Chùa Hang"}) is None


# ── các reject-helper ──


def test_reject_too_generic():
    assert auto_learn._reject_too_generic("vĩnh long") == (False, "quá chung")
    # < 15 ký tự và bắt đầu bằng từ generic → loại kèm tên rule
    assert auto_learn._reject_too_generic("du lịch xanh") == (
        False,
        "quá chung (du lịch)",
    )
    # >= 15 ký tự thì startswith không còn tính
    assert auto_learn._reject_too_generic("du lịch sinh thái abc x") is None
    assert auto_learn._reject_too_generic("chùa âng") is None


def test_reject_outside_vl():
    assert auto_learn._reject_outside_vl("chợ nổi cái răng", "cần thơ") == (
        False,
        "ngoài VL (cần thơ)",
    )
    assert auto_learn._reject_outside_vl("bánh xèo cần thơ", "") == (
        False,
        "ngoài VL (cần thơ)",
    )
    # location nhắc tỉnh ngoài NHƯNG có "vĩnh long" → không loại
    assert (
        auto_learn._reject_outside_vl("kèo nèo", "cái bè, tiền giang và vĩnh long")
        is None
    )
    assert auto_learn._reject_outside_vl("chùa âng", "trà vinh") is None


def test_reject_legal():
    assert auto_learn._reject_legal("nghị quyết 120 về đbscl") == (
        False,
        "văn bản/thương mại (nghị quyết)",
    )
    assert auto_learn._reject_legal("vincom plaza vĩnh long") == (
        False,
        "văn bản/thương mại (vincom)",
    )
    # pattern regex giữ nguyên escape trong reason
    assert auto_learn._reject_legal("khu số 5 chợ đêm") == (
        False,
        "văn bản/thương mại (số\\s+\\d+)",
    )
    assert auto_learn._reject_legal("chùa hạnh phúc") is None


# ── filter_entity ──


@pytest.mark.parametrize(
    "raw,known,expected",
    [
        ({"name": "Áng"}, set(), (False, "tên quá ngắn")),
        (
            {"name": "Mekong Riverside Resort", "summary": "x" * 20},
            set(),
            (False, "tên tiếng Anh"),
        ),
        ({"name": "Vĩnh Long", "summary": "x" * 20}, set(), (False, "quá chung")),
        (
            {"name": "Chợ nổi Cái Răng", "location": "Cần Thơ", "summary": "x" * 20},
            set(),
            (False, "ngoài VL (cần thơ)"),
        ),
        (
            {"name": "Nghị quyết 120 về ĐBSCL", "summary": "x" * 20},
            set(),
            (False, "văn bản/thương mại (nghị quyết)"),
        ),
        (
            {"name": "Chùa Âng", "summary": "x" * 20},
            {"Chùa Âng"},
            (False, "trùng gần: Chùa Âng"),
        ),
        (
            {"name": "bánh tráng Mỹ Lồng", "type": "dish", "summary": "x" * 20},
            set(),
            (False, "không phải danh từ riêng"),
        ),
        (
            {"name": "Chùa Hạnh Phúc", "summary": "ngắn"},
            set(),
            (False, "thiếu mô tả"),
        ),
    ],
)
def test_filter_entity_cac_nhanh_loai(raw, known, expected):
    assert auto_learn.filter_entity(raw, known) == expected


def test_filter_entity_giu_ten_thuong_khi_type_nature():
    keep, reason = auto_learn.filter_entity(
        {"name": "sông rạch miệt vườn", "type": "nature", "summary": "x" * 20}, set()
    )
    assert (keep, reason) == (True, "ok")


def test_filter_entity_giu_entity_hop_le():
    raw = {
        "name": "Chùa Âng",
        "location": "phường Trà Vinh",
        "summary": "Ngôi chùa Khmer cổ nhất Trà Vinh.",
    }
    assert auto_learn.filter_entity(raw, set()) == (True, "ok")


# ── to_entity ──


def test_to_entity_du_truong_va_gan_coords(monkeypatch):
    goi = []

    def fake_geocode(name, region="Vĩnh Long", use_cache=True):
        goi.append((name, region))
        return [10.25, 106.0]

    monkeypatch.setattr(geocode, "geocode", fake_geocode)
    raw = {
        "name": "Chùa Âng",
        "type": "attraction",
        "summary": "Ngôi chùa Khmer cổ.",
        "location": "phường Trà Vinh",
        "confidence": 0.95,
    }
    e = auto_learn.to_entity(raw, "https://vd.example.com/bai-viet")
    assert e["id"] == "chua-ang"
    assert e["type"] == "attraction"
    assert e["placeId"] == "p-tra-vinh"
    assert e["summary"] == "Ngôi chùa Khmer cổ."
    assert e["season"] is None
    assert e["attributes"] == {}
    assert e["source"] == {
        "title": "vd.example.com",
        "url": "https://vd.example.com/bai-viet",
    }
    assert e["confidence"] == 0.9  # kẹp trần 0.9
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", e["updatedAt"])
    assert e["coords"] == [10.25, 106.0]
    assert goi == [("Chùa Âng", "phường Trà Vinh")]


def test_to_entity_type_la_fallback_ve_attraction_va_kep_san():
    raw = {
        "name": "Bánh Tráng Mỹ Lồng",
        "type": "unknown-type",
        "summary": "s",
        "location": None,
        "confidence": 0.1,
    }
    e = auto_learn.to_entity(raw, "no-slash-url")
    assert e["type"] == "attraction"
    assert e["id"] == "banh-trang-my-long"
    assert e["placeId"] is None  # location None → đoán theo tên, không khớp
    assert e["source"] == {"title": "no-slash-url", "url": "no-slash-url"}
    assert e["confidence"] == 0.3  # kẹp sàn 0.3
    assert "coords" not in e  # geocode trả None → không có coords


def test_to_entity_geocode_no_van_tra_entity(monkeypatch):
    def boom(*_a, **_k):
        raise RuntimeError("geo down")

    monkeypatch.setattr(geocode, "geocode", boom)
    e = auto_learn.to_entity({"name": "Cồn Chim"}, "https://x.y/z")
    assert e["id"] == "con-chim"
    assert e["confidence"] == 0.6  # thiếu confidence → mặc định 0.6
    assert "coords" not in e


# ── _accept_raw ──


def test_accept_raw_ten_qua_ngan_khong_them():
    known, acc = set(), []
    auto_learn._accept_raw({"name": "Ab"}, "https://u.v/w", known, acc)
    assert acc == [] and known == set()


def test_accept_raw_them_entity_va_cap_nhat_known():
    known, acc = set(), []
    auto_learn._accept_raw(
        {"name": "Chùa Âng", "summary": "Ngôi chùa Khmer cổ nhất."},
        "https://u.v/w",
        known,
        acc,
    )
    assert [e["id"] for e in acc] == ["chua-ang"]
    assert known == {"chùa âng"}


def test_accept_raw_bo_qua_ten_da_co_trong_known():
    known, acc = {"chùa âng"}, []
    auto_learn._accept_raw(
        {"name": "CHÙA ÂNG", "summary": "Trùng known theo lower()."},
        "https://u.v/w",
        known,
        acc,
    )
    assert acc == []


def test_accept_raw_bo_qua_khi_filter_loai():
    known, acc = set(), []
    auto_learn._accept_raw(
        {"name": "Vĩnh Long", "summary": "x" * 20}, "https://u.v/w", known, acc
    )
    assert acc == [] and known == set()


def test_accept_raw_khu_trung_slug_trong_cung_batch():
    # "Đò 9" và "Đò-9": norm < 4 nên thoát near-duplicate, nhưng trùng slug "do-9"
    known, acc = set(), []
    auto_learn._accept_raw(
        {"name": "Đò 9", "summary": "Bến đò nhỏ ở cù lao."}, "https://u.v/w", known, acc
    )
    auto_learn._accept_raw(
        {"name": "Đò-9", "summary": "Bến đò nhỏ ở cù lao (trùng slug)."},
        "https://u.v/w",
        known,
        acc,
    )
    assert [e["id"] for e in acc] == ["do-9"]
    assert known == {"đò 9"}  # tên thứ hai không được add vào known


def test_accept_raw_slug_rong_khong_them():
    known, acc = set(), []
    auto_learn._accept_raw(
        {"name": "!!!!", "summary": "Toàn ký hiệu nhưng dài đủ."},
        "https://u.v/w",
        known,
        acc,
    )
    assert acc == [] and known == set()


# ── load_knowledge / existing_names ──


def test_load_knowledge_tra_dict_theo_id(tmp_path, monkeypatch):
    dj = tmp_path / "data.json"
    dj.write_text(
        json.dumps(
            {"entities": [{"id": "a", "name": "Chùa Âng"}, {"id": "b"}]},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(auto_learn, "DATA_JSON", dj)
    kb = auto_learn.load_knowledge()
    assert sorted(kb) == ["a", "b"]
    assert kb["a"]["name"] == "Chùa Âng"


def test_load_knowledge_thieu_entities_tra_rong(tmp_path, monkeypatch):
    dj = tmp_path / "data.json"
    dj.write_text(json.dumps({"x": 1}), encoding="utf-8")
    monkeypatch.setattr(auto_learn, "DATA_JSON", dj)
    assert auto_learn.load_knowledge() == {}


def test_existing_names_lower_va_chuoi_rong_cho_entity_khong_ten(
    tmp_path, monkeypatch
):
    dj = tmp_path / "data.json"
    dj.write_text(
        json.dumps(
            {"entities": [{"id": "a", "name": "Chùa Âng"}, {"id": "b"}]},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(auto_learn, "DATA_JSON", dj)
    assert auto_learn.existing_names() == {"chùa âng", ""}


# ── web_search ──


def test_web_search_truyen_region_vn_vi_va_tra_list(monkeypatch):
    thay = {}

    class FakeDDGS:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def text(self, query, region=None, max_results=None):
            thay["args"] = (query, region, max_results)
            return iter([{"title": "t", "href": "https://a.b/c", "body": "x"}])

    monkeypatch.setattr(auto_learn, "DDGS", FakeDDGS)
    out = auto_learn.web_search("chùa âng trà vinh")
    assert out == [{"title": "t", "href": "https://a.b/c", "body": "x"}]
    assert thay["args"] == ("chùa âng trà vinh", "vn-vi", 5)


def test_web_search_loi_tra_list_rong(monkeypatch):
    class BoomDDGS:
        def __enter__(self):
            raise RuntimeError("ddg down")

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(auto_learn, "DDGS", BoomDDGS)
    assert auto_learn.web_search("q") == []


# ── analyze_gaps ──


def test_analyze_gaps_boc_fence_json_va_dung_model_mini(monkeypatch):
    fake = _FakeLLM('```json\n["q1", "q2"]\n```')
    monkeypatch.setattr(auto_learn, "client", fake)
    out = auto_learn.analyze_gaps({"Chùa Âng", "Cồn Phụng"}, category="history")
    assert out == ["q1", "q2"]
    call = fake.calls[0]
    assert call["model"] == auto_learn.MODEL_MINI
    assert call["temperature"] == 0.8
    prompt = call["messages"][0]["content"]
    assert "Tập trung vào danh mục: Lịch sử" in prompt
    assert "Chùa Âng" in prompt  # sample tên hiện có được nhúng vào prompt


def test_analyze_gaps_loi_llm_tra_rong(monkeypatch):
    monkeypatch.setattr(
        auto_learn, "client", _FakeLLM(error=RuntimeError("llm down"))
    )
    assert auto_learn.analyze_gaps(set()) == []


def test_analyze_gaps_content_khong_phai_json_tra_rong(monkeypatch):
    monkeypatch.setattr(auto_learn, "client", _FakeLLM("not json"))
    assert auto_learn.analyze_gaps(set()) == []


# ── extract_entities_from_text ──


def test_extract_entities_tra_list_va_prompt_mang_url_query(monkeypatch):
    fake = _FakeLLM('```json\n[{"name": "Chùa Âng"}]\n```')
    monkeypatch.setattr(auto_learn, "client", fake)
    items = auto_learn.extract_entities_from_text(
        "nội dung " * 100, "https://s.t/u", "chùa khmer"
    )
    assert items == [{"name": "Chùa Âng"}]
    call = fake.calls[0]
    assert call["model"] == auto_learn.MODEL_MINI
    assert call["temperature"] == 0.1
    prompt = call["messages"][0]["content"]
    assert "https://s.t/u" in prompt
    assert "chùa khmer" in prompt


def test_extract_entities_json_khong_phai_list_tra_rong(monkeypatch):
    monkeypatch.setattr(auto_learn, "client", _FakeLLM('{"name": "khong phai list"}'))
    assert auto_learn.extract_entities_from_text("x", "u", "q") == []


def test_extract_entities_loi_llm_tra_rong(monkeypatch):
    monkeypatch.setattr(auto_learn, "client", _FakeLLM(error=RuntimeError("x")))
    assert auto_learn.extract_entities_from_text("x", "u", "q") == []


# ── learn_from_query ──


def test_learn_from_query_khong_ket_qua_tra_rong(monkeypatch):
    monkeypatch.setattr(auto_learn, "web_search", lambda q, max_results=3: [])
    assert auto_learn.learn_from_query("q", set()) == []


def test_learn_from_query_fetch_extract_va_khu_trung_qua_known(monkeypatch):
    monkeypatch.setattr(
        auto_learn,
        "web_search",
        lambda q, max_results=3: [
            {"href": "https://a.b/c"},
            {"url": "https://a.b/d"},
            {},  # không href/url → bỏ qua
        ],
    )
    monkeypatch.setattr(auto_learn, "fetch_url", lambda url: "nội dung dài " * 30)
    goi = []

    def fake_extract(text, url, query):
        goi.append((url, query))
        return [{"name": "Chùa Âng", "summary": "Ngôi chùa Khmer cổ nhất."}]

    monkeypatch.setattr(auto_learn, "extract_entities_from_text", fake_extract)
    known = set()
    ents = auto_learn.learn_from_query("chùa khmer", known)
    # URL thứ hai trích cùng tên → known chặn, chỉ còn 1 entity
    assert [e["id"] for e in ents] == ["chua-ang"]
    assert known == {"chùa âng"}
    assert goi == [("https://a.b/c", "chùa khmer"), ("https://a.b/d", "chùa khmer")]


# ── _select_queries ──


def test_select_queries_theo_category_lay_seed_dau():
    qs = auto_learn._select_queries("tourism", 2, set())
    assert qs == auto_learn.CATEGORIES["tourism"]["seed_queries"][:2]


def test_select_queries_khong_category_dung_llm_gaps(monkeypatch):
    monkeypatch.setattr(
        auto_learn,
        "analyze_gaps",
        lambda known, cat=None: ["g1", "g2", "g3", "g4", "g5", "g6"],
    )
    assert auto_learn._select_queries(None, 3, set()) == ["g1", "g2", "g3"]


def test_select_queries_fallback_seed_ngau_nhien_khi_llm_rong(monkeypatch):
    monkeypatch.setattr(auto_learn, "analyze_gaps", lambda known, cat=None: [])
    out = auto_learn._select_queries(None, 4, set())
    all_seeds = [q for c in auto_learn.CATEGORIES.values() for q in c["seed_queries"]]
    assert len(out) == 4
    assert all(q in all_seeds for q in out)


# ── _save_round ──


def test_save_round_ghi_file_learned_va_log_jsonl(tmp_path, monkeypatch):
    monkeypatch.setattr(auto_learn, "LEARN_DIR", tmp_path)
    monkeypatch.setattr(auto_learn, "LOG_FILE", tmp_path / "_learn_log.jsonl")
    unique = [
        {
            "id": "chua-ang",
            "type": "attraction",
            "name": "Chùa Âng",
            "placeId": "p-tra-vinh",
            "confidence": 0.8,
        },
        {
            "id": "con-chim",
            "type": "nature",
            "name": "Cồn Chim",
            "placeId": None,
            "confidence": 0.6,
        },
    ]
    auto_learn._save_round(unique, "culture", ["q1", "q2"])

    files = sorted(tmp_path.glob("learned_*.json"))
    assert len(files) == 1
    saved = json.loads(files[0].read_text(encoding="utf-8"))
    assert [e["id"] for e in saved] == ["chua-ang", "con-chim"]

    log_lines = (tmp_path / "_learn_log.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(log_lines) == 1
    entry = json.loads(log_lines[0])
    assert entry["category"] == "culture"
    assert entry["queries"] == ["q1", "q2"]
    assert entry["found"] == 2
    assert entry["types"] == {"attraction": 1, "nature": 1}


# ── learn_round ──


def test_learn_round_theo_category_khu_trung_id_va_save(monkeypatch):
    monkeypatch.setattr(auto_learn, "existing_names", lambda: set())
    monkeypatch.setattr(auto_learn.time, "sleep", lambda s: None)
    seen_q = []

    def fake_lfq(q, known):
        seen_q.append(q)
        if len(seen_q) == 1:
            return [
                {"id": "x1", "type": "dish", "name": "A"},
                {"id": "x2", "type": "dish", "name": "B"},
            ]
        return [{"id": "x1", "type": "dish", "name": "A dup"}]

    monkeypatch.setattr(auto_learn, "learn_from_query", fake_lfq)
    saved = []
    monkeypatch.setattr(
        auto_learn, "_save_round", lambda u, c, q: saved.append((u, c, q))
    )

    unique = auto_learn.learn_round(category="tourism", num_topics=2)
    assert [e["id"] for e in unique] == ["x1", "x2"]  # id trùng giữ bản đầu
    assert seen_q == auto_learn.CATEGORIES["tourism"]["seed_queries"][:2]
    assert len(saved) == 1
    assert saved[0][1] == "tourism" and saved[0][2] == seen_q


def test_learn_round_khong_tim_thay_gi_khong_save(monkeypatch):
    monkeypatch.setattr(auto_learn, "existing_names", lambda: set())
    monkeypatch.setattr(auto_learn.time, "sleep", lambda s: None)
    monkeypatch.setattr(auto_learn, "learn_from_query", lambda q, known: [])
    saved = []
    monkeypatch.setattr(
        auto_learn, "_save_round", lambda u, c, q: saved.append((u, c, q))
    )
    assert auto_learn.learn_round(category="tourism", num_topics=1) == []
    assert saved == []


# ── apply_learned (DB + knowledge đều là module giả trong sys.modules) ──


def _fake_db_modules(monkeypatch):
    store = {}
    ups = []

    fake_db = types.SimpleNamespace(
        get_entity=lambda eid: store.get(eid),
        upsert_entity=lambda e: (ups.append(e["id"]), store.__setitem__(e["id"], e)),
    )
    db_mod = types.ModuleType("database")
    db_mod.db = fake_db
    monkeypatch.setitem(sys.modules, "database", db_mod)

    reloads = []
    k_mod = types.ModuleType("knowledge")
    k_mod.reload = lambda: reloads.append(1)
    monkeypatch.setitem(sys.modules, "knowledge", k_mod)
    return store, ups, reloads


def test_apply_learned_them_moi_va_reload_knowledge(monkeypatch):
    store, ups, reloads = _fake_db_modules(monkeypatch)
    added = auto_learn.apply_learned([{"id": "e1"}, {"id": "e1"}, {"id": "e2"}])
    # bản e1 thứ hai đã có trong DB (vừa upsert) → bỏ qua
    assert [e["id"] for e in added] == ["e1", "e2"]
    assert ups == ["e1", "e2"]
    assert reloads == [1]


def test_apply_learned_toan_trung_khong_upsert_khong_reload(monkeypatch):
    store, ups, reloads = _fake_db_modules(monkeypatch)
    store["e1"] = {"id": "e1"}
    assert auto_learn.apply_learned([{"id": "e1"}]) == []
    assert ups == [] and reloads == []


def test_apply_learned_reload_loi_van_tra_added(monkeypatch):
    _, ups, _ = _fake_db_modules(monkeypatch)

    def boom():
        raise RuntimeError("reload down")

    sys.modules["knowledge"].reload = boom
    added = auto_learn.apply_learned([{"id": "e9"}])
    assert [e["id"] for e in added] == ["e9"]
    assert ups == ["e9"]


# ── main (CLI wrapper, mock trọn learn_round + apply_learned) ──


def test_main_truyen_args_va_apply(monkeypatch):
    ents = [{"id": "e1"}]
    seen = {}

    def fake_round(category=None, num_topics=5):
        seen["round"] = (category, num_topics)
        return ents

    monkeypatch.setattr(auto_learn, "learn_round", fake_round)
    applied = []
    monkeypatch.setattr(auto_learn, "apply_learned", lambda e: applied.append(e))
    monkeypatch.setattr(
        sys, "argv", ["auto_learn.py", "-c", "food", "-t", "2", "--apply"]
    )
    auto_learn.main()
    assert seen["round"] == ("food", 2)
    assert applied == [ents]


def test_main_khong_apply_chi_in_goi_y(monkeypatch, capsys):
    monkeypatch.setattr(
        auto_learn, "learn_round", lambda category=None, num_topics=5: [{"id": "e1"}]
    )
    monkeypatch.setattr(
        auto_learn,
        "apply_learned",
        lambda e: pytest.fail("apply_learned khong duoc goi khi thieu --apply"),
    )
    monkeypatch.setattr(sys, "argv", ["auto_learn.py"])
    auto_learn.main()
    assert "--apply" in capsys.readouterr().out
