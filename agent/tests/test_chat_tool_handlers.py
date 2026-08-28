# -*- coding: utf-8 -*-
"""Đặc tả hành vi HIỆN TẠI của tầng TOOL trong agent/chat/api.py (characterization).

Các handler dưới đây chỉ ĐỌC tầng tri thức in-memory (`knowledge._entities` /
`_itineraries`) — test bơm thẳng một KB nhỏ vào globals của module `knowledge`
(đúng module thực thi truy vấn), KHÔNG đụng DB thật, KHÔNG mạng, KHÔNG LLM:
  - `analytics.track_entity_hit` được patch (bản thật ghi agent/data/analytics.json);
  - `HAS_CONTEXTUAL` patch False → `_hybrid_rerank_search` đi đường keyword thuần;
  - `generate_itinerary` được patch để soi tham số handler truyền xuống.

Chạy một mình:
  PYTEST_DEBUG_TEMPROOT='C:\\vlt' python -m pytest -q agent/tests/test_chat_tool_handlers.py
"""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import knowledge  # noqa: E402
from chat import api as chat_api  # noqa: E402


CHO_NOI_SUMMARY = "Chợ nổi họp trên sông Trà Ôn từ tờ mờ sáng, ghe trái cây treo bẹo hàng."

# Cố ý dài hơn 120 ký tự để soi luật cắt summary[:120] của thẻ lưu trú.
HOMESTAY_SUMMARY = (
    "Homestay giữa vườn dừa xanh mát bên bờ sông Cổ Chiên, có võng nằm nghỉ trưa, "
    "xe đạp dạo quanh ấp, bữa cơm quê ba món và lớp làm bánh dân gian cho khách ở lại qua đêm."
)


def _seed_entities():
    """KB nhỏ, dựng mới mỗi test (tránh test này mutate lây sang test kia)."""
    return {e["id"]: e for e in [
        # tỉnh KHÔNG có parentId → knowledge.places() phải loại nó ra
        {"id": "tinh-vinh-long", "type": "place", "name": "Tỉnh Vĩnh Long",
         "level": "tinh", "area": "vinh-long"},
        {"id": "xa-an-binh", "type": "place", "name": "Xã An Bình", "level": "xa",
         "area": "vinh-long", "parentId": "tinh-vinh-long", "legacyArea": "Trà Ôn"},
        {"id": "phuong-1", "type": "place", "name": "Phường 1", "level": "phuong",
         "area": "ben-tre", "parentId": "tinh-vinh-long"},
        {"id": "cho-noi", "type": "attraction", "name": "Chợ nổi Trà Ôn",
         "summary": CHO_NOI_SUMMARY, "placeId": "xa-an-binh",
         "confidence": 0.9, "verified": True, "coords": [9.96, 105.94],
         "season": {"months": [6, 7, 8], "peak": [7]},
         "attributes": {"hours": "05:00-09:00", "admission_fee": "miễn phí",
                        "best_time": "sáng sớm", "address": "Sông Trà Ôn",
                        "phone": "0270 000 111"}},
        {"id": "van-thanh", "type": "attraction", "name": "Văn Thánh Miếu",
         "summary": "Di tích quốc gia bên rạch Long Hồ.", "placeId": "xa-an-binh",
         "confidence": 0.5, "attributes": {}},
        {"id": "keo-dua", "type": "product", "name": "Kẹo dừa Mỏ Cày",
         "summary": "Kẹo dẻo vị dừa xiêm, đặc sản Mỏ Cày.", "placeId": "phuong-1",
         "coords": [10.1, 106.3],
         "season": {"months": [11, 12, 1], "peak": [12]},
         "attributes": {"ocop_star": 4, "province_old": "Bến Tre",
                        "address": "Ấp Phú Lợi", "phone": "0275 111 222",
                        "admission_fee": "60.000đ/hộp", "best_time": "cuối năm"}},
        {"id": "mua-trai-cay", "type": "experience", "name": "Mùa trái cây Bình Hòa Phước",
         "summary": "Hái chôm chôm tại chỗ.", "season": {"months": [5, 6], "peak": [6]}},
        # peak phủ đủ 12 tháng → luôn có mặt bất kể tháng hiện tại (cho test fallback)
        {"id": "trai-cay-quanh-nam", "type": "experience", "name": "Đi miệt cây trái quanh năm",
         "summary": "", "season": {"months": list(range(1, 13)), "peak": list(range(1, 13))}},
        {"id": "homestay-vuon", "type": "accommodation", "name": "Homestay Vườn Dừa",
         "summary": HOMESTAY_SUMMARY, "coords": [10.27, 105.99],
         "attributes": {"price_range": "500k-800k", "open_hours": "check-in 14:00",
                        "booking_note": "Phù hợp gia đình có trẻ em",
                        "phone": "0270 333 444", "province_old": "Vĩnh Long",
                        "address": "Cù lao An Bình"}},
        # facility KHÔNG thuộc CARD_TYPES → không được đếm là "content"
        {"id": "ubnd-x", "type": "facility", "name": "UBND xã An Bình",
         "placeId": "xa-an-binh", "attributes": {"office_kind": "ubnd"}},
    ]}


def _seed_itineraries():
    return {it["id"]: it for it in [
        {"id": "it-1", "title": "Một ngày cù lao An Bình", "area": "vinh-long",
         "areas": ["vinh-long", "lien-vung"], "duration": "1 ngày",
         "summary": "Chợ nổi rồi về nhà cổ.",
         "stops": [
             {"time": "08:00", "id": "cho-noi", "note": "đi sớm"},
             {"time": "10:00", "id": "khong-ton-tai", "note": ""},
         ]},
        {"id": "it-2", "title": "Một vòng xứ dừa", "area": "ben-tre", "stops": []},
    ]}


@pytest.fixture
def kb(monkeypatch):
    """Bơm KB nhỏ vào ĐÚNG module `knowledge` (nơi thực thi truy vấn) + cắt outbound."""
    entities = _seed_entities()
    monkeypatch.setattr(knowledge, "_entities", entities)
    monkeypatch.setattr(knowledge, "_relationships", [])
    monkeypatch.setattr(knowledge, "_itineraries", _seed_itineraries())
    monkeypatch.setattr(knowledge, "_adjacency", None)
    monkeypatch.setattr(knowledge, "_adj_src", None)
    # Đường hybrid-rerank cần index nặng → ép plain-keyword cho tất định.
    monkeypatch.setattr(chat_api, "HAS_CONTEXTUAL", False)
    hits = []
    monkeypatch.setattr(chat_api.analytics, "track_entity_hit", lambda eid: hits.append(eid))
    return SimpleNamespace(entities=entities, hits=hits)


# ── _area_matches ─────────────────────────────────────────────────────────────

def test_area_matches_khong_loc_khi_area_rong(kb):
    e = kb.entities["cho-noi"]
    assert chat_api._area_matches(e, e["attributes"], None) is True
    assert chat_api._area_matches(e, e["attributes"], "") is True


def test_area_matches_theo_place(kb):
    e = kb.entities["cho-noi"]  # placeId=xa-an-binh, area=vinh-long
    assert chat_api._area_matches(e, e["attributes"], "vinh-long") is True
    assert chat_api._area_matches(e, e["attributes"], "ben-tre") is False


def test_area_matches_fallback_province_old(kb):
    e = kb.entities["homestay-vuon"]  # không placeId, chỉ có province_old
    assert chat_api._area_matches(e, e["attributes"], "vinh-long") is True
    assert chat_api._area_matches(e, e["attributes"], "ben-tre") is False


# ── _ocop_category_ok ─────────────────────────────────────────────────────────

def test_ocop_category_all_va_category_la(kb):
    e = {"id": "x", "name": "Bất kỳ", "summary": ""}
    assert chat_api._ocop_category_ok(e, "all") is True
    # category không nằm trong craft/drink/food → nhánh cuối trả True
    assert chat_api._ocop_category_ok(e, "khong-co-loai-nay") is True


def test_ocop_category_craft_drink_food(kb):
    craft = {"name": "Giỏ đan lục bình", "summary": ""}
    drink = {"name": "Rượu nếp Phú Lễ", "summary": ""}
    food = {"name": "Kẹo dừa", "summary": "ngọt béo"}
    assert chat_api._ocop_category_ok(craft, "craft") is True
    assert chat_api._ocop_category_ok(craft, "food") is False
    assert chat_api._ocop_category_ok(drink, "drink") is True
    assert chat_api._ocop_category_ok(drink, "food") is False
    assert chat_api._ocop_category_ok(food, "craft") is False
    assert chat_api._ocop_category_ok(food, "drink") is False
    assert chat_api._ocop_category_ok(food, "food") is True


# ── _accom_filters_ok ─────────────────────────────────────────────────────────

def test_accom_filters_theo_type(kb):
    e = kb.entities["homestay-vuon"]
    assert chat_api._accom_filters_ok(e, e["attributes"], "all", False) is True
    assert chat_api._accom_filters_ok(e, e["attributes"], "homestay", False) is True
    assert chat_api._accom_filters_ok(e, e["attributes"], "resort", False) is False


def test_accom_filters_family(kb):
    # tên chứa "vườn" (từ khoá family) → qua
    e = kb.entities["homestay-vuon"]
    assert chat_api._accom_filters_ok(e, e["attributes"], "all", True) is True
    # khách sạn trung tâm không có từ khoá nào → rớt
    hotel = {"name": "Khách sạn Trung tâm", "summary": "ngay trung tâm thành phố"}
    assert chat_api._accom_filters_ok(hotel, {}, "hotel", True) is False
    # nhưng booking_note có "gia đình" → qua
    assert chat_api._accom_filters_ok(hotel, {"booking_note": "ưu đãi gia đình"}, "hotel", True) is True


# ── Card builders ─────────────────────────────────────────────────────────────

def test_ocop_card_day_du(kb):
    e = kb.entities["keo-dua"]
    card = chat_api._ocop_card(e, e["attributes"], 4)
    assert card == {
        "id": "keo-dua", "name": "Kẹo dừa Mỏ Cày", "ocop": "OCOP 4 sao",
        "summary": "Kẹo dẻo vị dừa xiêm, đặc sản Mỏ Cày.",
        "province": "Bến Tre", "address": "Ấp Phú Lợi",
        "price": "60.000đ/hộp", "phone": "0275 111 222",
        "coords": [10.1, 106.3], "_star": 4,
    }


def test_accom_card_day_du_va_cat_summary(kb):
    e = kb.entities["homestay-vuon"]
    card = chat_api._accom_card(e, e["attributes"])
    assert card == {
        "id": "homestay-vuon", "name": "Homestay Vườn Dừa",
        "summary": HOMESTAY_SUMMARY[:120],
        "province": "Vĩnh Long", "address": "Cù lao An Bình",
        "price": "500k-800k",              # admission_fee/admission vắng → rơi về price_range
        "phone": "0270 333 444",
        "check_in": "check-in 14:00",      # hours vắng → lấy open_hours
        "booking_note": "Phù hợp gia đình có trẻ em",
        "coords": [10.27, 105.99],
    }
    assert len(card["summary"]) == 120     # summary gốc dài hơn → bị cắt thật


def test_accom_card_toi_thieu():
    card = chat_api._accom_card({"id": "a1", "name": "Nhà nghỉ X"}, {})
    assert card == {"id": "a1", "name": "Nhà nghỉ X", "summary": "", "province": "", "address": ""}


def test_search_result_card_day_du(kb):
    card = chat_api._search_result_card(kb.entities["cho-noi"])
    assert card == {
        "id": "cho-noi", "type": "attraction", "name": "Chợ nổi Trà Ôn",
        "summary": CHO_NOI_SUMMARY,
        "place": "Xã An Bình",
        "season": "mùa cao điểm tháng 7; mùa: tháng 6, tháng 7, tháng 8",
        "needs_verification": False,       # confidence 0.9 ≥ 0.7
        "coords": [9.96, 105.94],
        "hours": "05:00-09:00", "admission_fee": "miễn phí",
        "best_time": "sáng sớm", "address": "Sông Trà Ôn",
    }
    # §1.7: cờ publish của entity không được lọt vào payload cho LLM
    assert "verified" not in card


def test_search_result_card_fallback_district_location():
    # entity KHÔNG có trong KB → place label rơi về attributes; không address → "location"
    card = chat_api._search_result_card({
        "id": "tam", "type": "dish", "name": "Bánh xèo hến",
        "attributes": {"district": "Càng Long", "province_old": "Trà Vinh"},
    })
    assert card == {
        "id": "tam", "type": "dish", "name": "Bánh xèo hến", "summary": "",
        "place": "Càng Long", "season": "quanh năm", "needs_verification": False,
        "location": "Càng Long, Trà Vinh",
    }


def test_search_result_card_confidence_thap(kb):
    card = chat_api._search_result_card(kb.entities["van-thanh"])
    assert card["needs_verification"] is True   # confidence 0.5 < 0.7


# ── _tool_search ──────────────────────────────────────────────────────────────

def test_tool_search_tra_card_va_track_hit(kb):
    out = json.loads(chat_api._tool_search({"q": "chợ nổi", "limit": 5}))
    assert [c["id"] for c in out] == ["cho-noi"]
    assert out[0]["place"] == "Xã An Bình"
    assert out[0]["season"] == "mùa cao điểm tháng 7; mùa: tháng 6, tháng 7, tháng 8"
    assert out[0]["needs_verification"] is False
    assert "verified" not in out[0]
    assert kb.hits == ["cho-noi"]          # top-3 kết quả được ghi nhận analytics


def test_tool_search_loc_theo_type_khong_can_q(kb):
    out = json.loads(chat_api._tool_search({"entity_type": "accommodation"}))
    assert [c["id"] for c in out] == ["homestay-vuon"]
    card = out[0]
    assert card["place"] == "Vĩnh Long"        # không placeId/ward/district → province_old
    assert card["hours"] == "check-in 14:00"   # hours vắng → open_hours
    assert card["season"] == "quanh năm"


def test_tool_search_rong(kb):
    out = json.loads(chat_api._tool_search({"q": "hoàn toàn không khớp zzz"}))
    assert out == []
    assert kb.hits == []


def test_tool_search_song_sot_khi_analytics_hong(kb, monkeypatch):
    def _boom(_eid):
        raise RuntimeError("analytics hỏng")
    monkeypatch.setattr(chat_api.analytics, "track_entity_hit", _boom)
    out = json.loads(chat_api._tool_search({"q": "chợ nổi"}))
    assert [c["id"] for c in out] == ["cho-noi"]   # lỗi analytics không lây sang kết quả


# ── _tool_entity_detail ───────────────────────────────────────────────────────

def test_tool_entity_detail_tim_thay(kb):
    out = json.loads(chat_api._tool_entity_detail({"entity_id": "cho-noi"}))
    assert out["place_name"] == "Xã An Bình"
    assert out["legacy_area"] == "Trà Ôn"
    assert out["area"] == "vinh-long"
    assert out["area_name"] == "Vĩnh Long"
    assert out["related"] == []
    assert out["needs_verification"] is False
    assert "confidence" not in out             # bị pop, thay bằng needs_verification
    assert "verified" not in out               # §1.7: cờ publish bị gỡ khỏi payload LLM
    assert kb.hits == ["cho-noi"]


def test_tool_entity_detail_confidence_thap(kb):
    out = json.loads(chat_api._tool_entity_detail({"entity_id": "van-thanh"}))
    assert out["needs_verification"] is True


def test_tool_entity_detail_khong_thay(kb):
    out = json.loads(chat_api._tool_entity_detail({"entity_id": "khong-co"}))
    assert out == {"error": "Không tìm thấy: khong-co"}
    # hành vi hiện tại: analytics ghi nhận TRƯỚC khi kiểm tra tồn tại
    assert kb.hits == ["khong-co"]


# ── _tool_seasonal_now (+ _seasonal_card) ─────────────────────────────────────

def test_tool_seasonal_dung_thang_va_loc_type(kb):
    ids_12 = {c["id"] for c in json.loads(chat_api._tool_seasonal_now({"month": 12}))}
    assert ids_12 == {"keo-dua", "trai-cay-quanh-nam"}
    # cho-noi peak tháng 7 nhưng type=attraction → seasonal_now loại (chỉ product/experience)
    ids_7 = {c["id"] for c in json.loads(chat_api._tool_seasonal_now({"month": 7}))}
    assert ids_7 == {"trai-cay-quanh-nam"}


def test_tool_seasonal_card_shape(kb):
    out = json.loads(chat_api._tool_seasonal_now({"month": 12}))
    card = next(c for c in out if c["id"] == "keo-dua")
    assert card == {
        "id": "keo-dua", "type": "product", "name": "Kẹo dừa Mỏ Cày",
        "summary": "Kẹo dẻo vị dừa xiêm, đặc sản Mỏ Cày.",
        "season": "mùa cao điểm tháng 12; mùa: tháng 11, tháng 12, tháng 1",
        "admission_fee": "60.000đ/hộp", "best_time": "cuối năm",
        "ocop": "OCOP 4 sao", "coords": [10.1, 106.3],
    }
    bare = next(c for c in out if c["id"] == "trai-cay-quanh-nam")
    assert set(bare) == {"id", "type", "name", "summary", "season"}  # không attrs → card tối giản


def test_tool_seasonal_clamp_thang_ngoai_bien(kb):
    # "15" (chuỗi) → int → clamp về 12 → vẫn ra entity peak tháng 12
    ids = {c["id"] for c in json.loads(chat_api._tool_seasonal_now({"month": "15"}))}
    assert "keo-dua" in ids


def test_tool_seasonal_thang_khong_parse_duoc_rot_ve_thang_hien_tai(kb):
    # month=None → int(None) nổ TypeError → dùng tháng UTC hiện tại;
    # entity peak phủ đủ 12 tháng nên luôn có mặt, test tất định quanh năm.
    ids = {c["id"] for c in json.loads(chat_api._tool_seasonal_now({"month": None}))}
    assert "trai-cay-quanh-nam" in ids


# ── _tool_list_itineraries ────────────────────────────────────────────────────

def test_tool_list_itineraries_tat_ca(kb):
    out = json.loads(chat_api._tool_list_itineraries({}))
    assert {it["id"] for it in out} == {"it-1", "it-2"}
    it2 = next(it for it in out if it["id"] == "it-2")
    assert it2 == {"id": "it-2", "title": "Một vòng xứ dừa", "area": "ben-tre",
                   "duration": None, "summary": "", "stops": 0}
    it1 = next(it for it in out if it["id"] == "it-1")
    assert it1["stops"] == 2 and it1["duration"] == "1 ngày"


def test_tool_list_itineraries_loc_area(kb):
    out = json.loads(chat_api._tool_list_itineraries({"area": "ben-tre"}))
    assert [it["id"] for it in out] == ["it-2"]
    # khớp qua danh sách `areas` (không chỉ trường `area` đơn)
    out2 = json.loads(chat_api._tool_list_itineraries({"area": "lien-vung"}))
    assert [it["id"] for it in out2] == ["it-1"]


# ── _tool_itinerary_detail ────────────────────────────────────────────────────

def test_tool_itinerary_detail_resolve_stops(kb):
    out = json.loads(chat_api._tool_itinerary_detail({"itinerary_id": "it-1"}))
    assert out["title"] == "Một ngày cù lao An Bình"
    assert out["stops"] == [
        {"time": "08:00", "id": "cho-noi", "name": "Chợ nổi Trà Ôn",
         "summary": CHO_NOI_SUMMARY, "note": "đi sớm"},
        # stop trỏ entity không tồn tại → name = id, summary rỗng (không nổ)
        {"time": "10:00", "id": "khong-ton-tai", "name": "khong-ton-tai",
         "summary": "", "note": ""},
    ]


def test_tool_itinerary_detail_khong_thay(kb):
    out = json.loads(chat_api._tool_itinerary_detail({"itinerary_id": "it-x"}))
    assert out == {"error": "Không tìm thấy: it-x"}


# ── _tool_places_in_area ──────────────────────────────────────────────────────

def test_tool_places_in_area_dem_noi_dung(kb):
    out = json.loads(chat_api._tool_places_in_area({"area": "vinh-long"}))
    # tinh-vinh-long không có parentId → bị loại; facility không tính vào content_count
    assert out == [{"id": "xa-an-binh", "name": "Xã An Bình", "level": "xa",
                    "legacyArea": "Trà Ôn", "content_count": 2}]


def test_tool_places_in_area_khu_vuc_khac(kb):
    out = json.loads(chat_api._tool_places_in_area({"area": "ben-tre"}))
    assert out == [{"id": "phuong-1", "name": "Phường 1", "level": "phuong",
                    "legacyArea": "", "content_count": 1}]


# ── _tool_stats ───────────────────────────────────────────────────────────────

def test_tool_stats_dem_theo_type(kb):
    out = json.loads(chat_api._tool_stats({}))
    assert out == {
        "total_content": 6,
        "by_type": {"attraction": 2, "product": 1, "experience": 2, "accommodation": 1},
        "places": 2, "phuong": 1, "xa": 1,
        "itineraries": 2,
    }


# ── _tool_compare_areas ───────────────────────────────────────────────────────

def test_tool_compare_areas(kb):
    res = json.loads(chat_api._tool_compare_areas({"area_1": "vinh-long", "area_2": "ben-tre"}))
    a1, a2 = res["area_1"], res["area_2"]
    assert a1["area_name"] == "Vĩnh Long"
    assert a1["total_content"] == 2 and a1["by_type"] == {"attraction": 2}
    assert a1["places_count"] == 1
    assert [h["id"] for h in a1["highlights"]] == ["cho-noi", "van-thanh"]  # sort theo tên
    assert a2["area_name"] == "Bến Tre"
    assert a2["total_content"] == 1 and a2["by_type"] == {"product": 1}
    assert [h["id"] for h in a2["highlights"]] == ["keo-dua"]


# ── _tool_generate_itinerary ──────────────────────────────────────────────────

def test_tool_generate_itinerary_mac_dinh(monkeypatch):
    captured = {}

    def _fake(**kwargs):
        captured.update(kwargs)
        return {"days": kwargs["days"], "title": "lịch trình test"}

    monkeypatch.setattr(chat_api, "generate_itinerary", _fake)
    out = json.loads(chat_api._tool_generate_itinerary({}))
    assert captured == {"days": 1, "interests": None, "areas": None,
                        "month": None, "budget": "trung_binh"}
    assert out == {"days": 1, "title": "lịch trình test"}


def test_tool_generate_itinerary_truyen_du_tham_so(monkeypatch):
    captured = {}

    def _fake(**kwargs):
        captured.update(kwargs)
        return {"ok": True}

    monkeypatch.setattr(chat_api, "generate_itinerary", _fake)
    out = json.loads(chat_api._tool_generate_itinerary({
        "days": 2, "interests": ["ẩm thực"], "areas": ["ben-tre"],
        "month": 7, "budget": "tiet_kiem",
    }))
    assert captured == {"days": 2, "interests": ["ẩm thực"], "areas": ["ben-tre"],
                        "month": 7, "budget": "tiet_kiem"}
    assert out == {"ok": True}
