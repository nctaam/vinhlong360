"""
Unit tests THẬT cho agent/itinerary_gen.py — nâng coverage.

Chiến lược:
- Các hàm thuần (helper) được gọi trực tiếp với input thật, assert output thật.
- generate_itinerary chạm knowledge (_entities/_relationships/_itineraries + AREA_META);
  ta patch state của knowledge bằng entities mẫu (không PG, không network) rồi assert
  LOGIC lịch trình: clamp ngày, lọc khu vực, phân bổ stops/ngày, chèn bữa ăn, tips, title.

Không có Postgres/network nào bị chạm: knowledge._entities được set sẵn nên _ensure()
là no-op (không đọc DB).
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import itinerary_gen as ig
import knowledge


# ─────────────────────────── helpers thuần ───────────────────────────

class TestFmtTime:
    def test_on_the_hour(self):
        assert ig._fmt_time(8 * 60) == "08:00"

    def test_with_minutes(self):
        assert ig._fmt_time(9 * 60 + 5) == "09:05"

    def test_afternoon_two_digit_hour(self):
        assert ig._fmt_time(13 * 60 + 30) == "13:30"

    def test_zero(self):
        assert ig._fmt_time(0) == "00:00"

    def test_minute_padding(self):
        # 12:07 — phút phải zero-pad
        assert ig._fmt_time(12 * 60 + 7) == "12:07"


class TestDayArea:
    def test_empty(self):
        assert ig._day_area([]) == ""

    def test_no_area_key(self):
        assert ig._day_area([{"foo": 1}, {"bar": 2}]) == ""

    def test_majority_area(self):
        ents = [{"area": "vinh-long"}, {"area": "vinh-long"}, {"area": "ben-tre"}]
        assert ig._day_area(ents) == "vinh-long"

    def test_single(self):
        assert ig._day_area([{"area": "tra-vinh"}]) == "tra-vinh"

    def test_mixed_with_missing_keys(self):
        # phần tử thiếu 'area' bị bỏ qua, không tính vào Counter
        ents = [{"area": "ben-tre"}, {"noarea": 1}, {"area": "ben-tre"}]
        assert ig._day_area(ents) == "ben-tre"


class TestEntitySummary:
    def test_basic_fields(self):
        e = {"id": "x", "name": "X", "type": "dish", "summary": "abc"}
        out = ig._entity_summary(e)
        assert out == {"id": "x", "name": "X", "type": "dish", "summary": "abc"}

    def test_summary_truncated_to_120(self):
        long = "a" * 200
        out = ig._entity_summary({"id": "x", "name": "X", "type": "dish", "summary": long})
        assert len(out["summary"]) == 120

    def test_missing_summary_defaults_empty(self):
        out = ig._entity_summary({"id": "x", "name": "X", "type": "dish"})
        assert out["summary"] == ""

    def test_hours_from_hours_attr(self):
        e = {"id": "x", "name": "X", "type": "attraction",
             "attributes": {"hours": "7:00-17:00"}}
        assert ig._entity_summary(e)["hours"] == "7:00-17:00"

    def test_hours_fallback_open_hours(self):
        e = {"id": "x", "name": "X", "type": "attraction",
             "attributes": {"open_hours": "8:00-18:00"}}
        assert ig._entity_summary(e)["hours"] == "8:00-18:00"

    def test_hours_prefers_hours_over_open_hours(self):
        e = {"id": "x", "name": "X", "type": "attraction",
             "attributes": {"hours": "A", "open_hours": "B"}}
        assert ig._entity_summary(e)["hours"] == "A"

    def test_admission_fee_and_address(self):
        e = {"id": "x", "name": "X", "type": "attraction",
             "attributes": {"admission_fee": "20k", "address": "Đường số 1"}}
        out = ig._entity_summary(e)
        assert out["admission_fee"] == "20k"
        assert out["address"] == "Đường số 1"

    def test_no_optional_keys_when_absent(self):
        out = ig._entity_summary({"id": "x", "name": "X", "type": "dish"})
        assert "hours" not in out
        assert "admission_fee" not in out
        assert "address" not in out

    def test_attributes_none_safe(self):
        # attributes=None phải được coi như {} (không nổ)
        out = ig._entity_summary({"id": "x", "name": "X", "type": "dish", "attributes": None})
        assert "hours" not in out


class TestFindMeal:
    def _c(self, eid, etype, area):
        return {"entity": {"id": eid, "type": etype, "name": eid}, "area": area}

    def test_finds_dish_in_area(self):
        cands = [self._c("d1", "dish", "vinh-long")]
        meal = ig._find_meal(cands, "vinh-long", [])
        assert meal is not None
        assert meal["entity"]["id"] == "d1"

    def test_finds_product_in_area(self):
        cands = [self._c("p1", "product", "ben-tre")]
        assert ig._find_meal(cands, "ben-tre", [])["entity"]["id"] == "p1"

    def test_wrong_area_returns_none(self):
        cands = [self._c("d1", "dish", "tra-vinh")]
        assert ig._find_meal(cands, "vinh-long", []) is None

    def test_wrong_type_returns_none(self):
        cands = [self._c("a1", "attraction", "vinh-long")]
        assert ig._find_meal(cands, "vinh-long", []) is None

    def test_excluded_id_skipped(self):
        cands = [self._c("d1", "dish", "vinh-long"), self._c("d2", "dish", "vinh-long")]
        meal = ig._find_meal(cands, "vinh-long", ["d1"])
        assert meal["entity"]["id"] == "d2"

    def test_all_excluded_returns_none(self):
        cands = [self._c("d1", "dish", "vinh-long")]
        assert ig._find_meal(cands, "vinh-long", ["d1"]) is None

    def test_empty_candidates(self):
        assert ig._find_meal([], "vinh-long", []) is None


# ─────────────────────────── _score_entity ───────────────────────────

class TestScoreEntity:
    def test_base_confidence_scaled(self):
        e = {"type": "unknown_type", "confidence": 0.5}
        # 0.5*10 = 5; area 'x' KHÁC preferred[0] 'y' nên không +2 → đúng 5.0
        assert ig._score_entity(e, None, "trung_binh", "x", ["y"]) == 5.0

    def test_missing_confidence_defaults_half(self):
        e = {"type": "unknown_type"}
        # default confidence 0.5 → 5.0; area không nằm trong preferred[0]
        assert ig._score_entity(e, None, "trung_binh", "x", ["y"]) == 5.0

    def test_type_bonus_attraction(self):
        e = {"type": "attraction", "confidence": 0.0}
        # 0 + type_bonus 3 = 3
        assert ig._score_entity(e, None, "trung_binh", "x", ["y"]) == 3.0

    def test_season_peak_bonus(self):
        e = {"type": "unknown", "confidence": 0.0,
             "season": {"peak": [11], "months": [10, 11, 12]}}
        # month=11 in peak → +5
        assert ig._score_entity(e, 11, "trung_binh", "x", ["y"]) == 5.0

    def test_season_month_not_peak(self):
        e = {"type": "unknown", "confidence": 0.0,
             "season": {"peak": [11], "months": [10, 11, 12]}}
        # month=10 in months but not peak → +2
        assert ig._score_entity(e, 10, "trung_binh", "x", ["y"]) == 2.0

    def test_season_month_outside(self):
        e = {"type": "unknown", "confidence": 0.0,
             "season": {"peak": [11], "months": [10, 11, 12]}}
        # month=5 không có → 0
        assert ig._score_entity(e, 5, "trung_binh", "x", ["y"]) == 0.0

    def test_season_none_peak_uses_empty(self):
        # peak=None phải được coi là [] (nhánh `or []`)
        e = {"type": "unknown", "confidence": 0.0,
             "season": {"peak": None, "months": [3]}}
        # month=3 trong months → +2 (không crash vì peak None)
        assert ig._score_entity(e, 3, "trung_binh", "x", ["y"]) == 2.0

    def test_no_month_skips_season(self):
        e = {"type": "unknown", "confidence": 0.0,
             "season": {"peak": [11], "months": [11]}}
        # month=None → nhánh mùa vụ bị bỏ qua hoàn toàn
        assert ig._score_entity(e, None, "trung_binh", "x", ["y"]) == 0.0

    def test_preferred_area_bonus(self):
        e = {"type": "unknown", "confidence": 0.0}
        # area == preferred_areas[0] → +2
        assert ig._score_entity(e, None, "trung_binh", "vinh-long",
                                ["vinh-long", "ben-tre"]) == 2.0

    def test_not_first_preferred_area_no_bonus(self):
        e = {"type": "unknown", "confidence": 0.0}
        # area là preferred[1], không phải [0] → không +2
        assert ig._score_entity(e, None, "trung_binh", "ben-tre",
                                ["vinh-long", "ben-tre"]) == 0.0

    def test_ocop_bonus(self):
        e = {"type": "unknown", "confidence": 0.0, "attributes": {"ocop": "4 sao"}}
        assert ig._score_entity(e, None, "trung_binh", "x", ["y"]) == 2.0

    def test_summary_length_bonuses(self):
        short = {"type": "unknown", "confidence": 0.0, "summary": "a" * 30}
        mid = {"type": "unknown", "confidence": 0.0, "summary": "a" * 60}
        rich = {"type": "unknown", "confidence": 0.0, "summary": "a" * 150}
        assert ig._score_entity(short, None, "x", "z", ["w"]) == 0.0   # <=50: 0
        assert ig._score_entity(mid, None, "x", "z", ["w"]) == 1.0     # >50: +1
        assert ig._score_entity(rich, None, "x", "z", ["w"]) == 2.0    # >100: +1+1

    def test_combined_score(self):
        e = {
            "type": "attraction",       # +3
            "confidence": 1.0,          # +10
            "season": {"peak": [6], "months": [6]},  # month 6 peak → +5
            "attributes": {"ocop": "3 sao"},          # +2
            "summary": "a" * 120,       # >50 +1, >100 +1 = +2
        }
        # area == preferred[0] → +2
        total = ig._score_entity(e, 6, "trung_binh", "vinh-long", ["vinh-long"])
        assert total == 10 + 5 + 2 + 3 + 2 + 2  # = 24


# ─────────────────────────── _gen_note ───────────────────────────

class TestGenNote:
    def test_empty_when_nothing(self):
        assert ig._gen_note({"type": "dish"}, None) == ""

    def test_peak_season_note(self):
        e = {"season": {"peak": [11]}}
        note = ig._gen_note(e, 11)
        assert "cao điểm" in note

    def test_season_not_peak_no_note(self):
        e = {"season": {"peak": [11]}}
        assert ig._gen_note(e, 5) == ""

    def test_season_without_month_no_note(self):
        e = {"season": {"peak": [11]}}
        assert ig._gen_note(e, None) == ""

    def test_ocop_note(self):
        note = ig._gen_note({"attributes": {"ocop": "4 sao"}}, None)
        assert "OCOP 4 sao" in note

    def test_fee_from_admission(self):
        note = ig._gen_note({"attributes": {"admission_fee": "30k"}}, None)
        assert "30k" in note

    def test_fee_fallback_gia(self):
        note = ig._gen_note({"attributes": {"gia": "50k"}}, None)
        assert "50k" in note

    def test_hours_note(self):
        note = ig._gen_note({"attributes": {"hours": "7-17"}}, None)
        assert "7-17" in note

    def test_hours_fallback_open_hours(self):
        note = ig._gen_note({"attributes": {"open_hours": "8-18"}}, None)
        assert "8-18" in note

    def test_multiple_parts_joined(self):
        e = {
            "season": {"peak": [7]},
            "attributes": {"ocop": "3 sao", "admission_fee": "20k", "hours": "8-17"},
        }
        note = ig._gen_note(e, 7)
        assert " | " in note
        assert "cao điểm" in note
        assert "OCOP 3 sao" in note
        assert "20k" in note
        assert "8-17" in note


# ─────────────────────────── _gen_tips ───────────────────────────

class TestGenTips:
    def test_always_has_hotline(self):
        tips = ig._gen_tips([], [], None, "trung_binh")
        assert any("hotline" in t.lower() for t in tips)

    def test_rainy_month(self):
        tips = ig._gen_tips([], [], 7, "trung_binh")
        assert any("mùa mưa" in t for t in tips)

    def test_dry_month(self):
        tips = ig._gen_tips([], [], 1, "trung_binh")
        assert any("Mùa khô" in t for t in tips)

    def test_month_outside_both_ranges(self):
        # tháng 4, 5, 11 không nằm trong dải mưa (6-10) hay khô (12-3)
        tips = ig._gen_tips([], [], 4, "trung_binh")
        assert not any("mùa mưa" in t for t in tips)
        assert not any("Mùa khô" in t for t in tips)

    def test_ben_tre_tip(self):
        tips = ig._gen_tips([], ["ben-tre"], None, "trung_binh")
        assert any("Bến Tre" in t for t in tips)

    def test_tra_vinh_tip(self):
        tips = ig._gen_tips([], ["tra-vinh"], None, "trung_binh")
        assert any("Khmer" in t for t in tips)

    def test_budget_thap(self):
        tips = ig._gen_tips([], [], None, "thap")
        assert any("tiết kiệm" in t for t in tips)

    def test_budget_cao(self):
        tips = ig._gen_tips([], [], None, "cao")
        assert any("resort" in t or "cao cấp" in t for t in tips)

    def test_budget_trung_binh_no_budget_tip(self):
        tips = ig._gen_tips([], [], None, "trung_binh")
        assert not any("tiết kiệm" in t for t in tips)
        assert not any("resort" in t for t in tips)

    def test_am_thuc_interest(self):
        tips = ig._gen_tips(["am_thuc"], [], None, "trung_binh")
        assert any("địa phương" in t for t in tips)

    def test_full_combo(self):
        tips = ig._gen_tips(["am_thuc"], ["ben-tre", "tra-vinh"], 7, "thap")
        joined = " ".join(tips)
        assert "mùa mưa" in joined
        assert "Bến Tre" in joined
        assert "Khmer" in joined
        assert "tiết kiệm" in joined
        assert "địa phương" in joined


# ─────────────────────────── _select_diverse ───────────────────────────

class TestSelectDiverse:
    def _cand(self, eid, etype, area, score):
        return {"entity": {"id": eid, "type": etype, "name": eid},
                "area": area, "score": score}

    def test_picks_highest_score(self):
        cands = [
            self._cand("a", "attraction", "vinh-long", 5),
            self._cand("b", "attraction", "vinh-long", 9),
        ]
        out = ig._select_diverse(cands, 1, ["vinh-long"], 1)
        assert out[0]["entity"]["id"] == "b"

    def test_no_duplicates(self):
        cands = [
            self._cand("a", "dish", "vinh-long", 5),
            self._cand("b", "attraction", "vinh-long", 4),
        ]
        out = ig._select_diverse(cands, 5, ["vinh-long"], 1)
        ids = [c["entity"]["id"] for c in out]
        assert len(ids) == len(set(ids))
        # chỉ có 2 candidate nên tối đa 2 dù total=5
        assert len(out) == 2

    def test_type_diversity_within_day(self):
        # cùng ngày: sau khi chọn 1 attraction, attraction thứ 2 bị phạt -3
        # nên dish điểm thấp hơn vẫn có thể được ưu tiên nếu chênh <3
        cands = [
            self._cand("a1", "attraction", "vinh-long", 10),
            self._cand("a2", "attraction", "vinh-long", 9),   # 9-3=6 sau phạt
            self._cand("d1", "dish", "vinh-long", 8),          # 8, không phạt
        ]
        out = ig._select_diverse(cands, 2, ["vinh-long"], 1)
        ids = [c["entity"]["id"] for c in out]
        assert ids[0] == "a1"          # cao nhất, chọn trước
        assert ids[1] == "d1"          # dish (8) thắng a2 (9-3=6) nhờ đa dạng loại

    def test_empty_candidates_returns_empty(self):
        assert ig._select_diverse([], 5, ["vinh-long"], 1) == []

    def test_multi_day_partitions_days(self):
        cands = [self._cand(f"e{i}", "dish", "vinh-long", 10 - i) for i in range(8)]
        out = ig._select_diverse(cands, 8, ["vinh-long"], 2)
        assert len(out) == 8
        ids = [c["entity"]["id"] for c in out]
        assert len(set(ids)) == 8   # không trùng qua các ngày


# ─────────────────────── generate_itinerary (integration) ───────────────────────

def _place(pid, area):
    return {"id": pid, "name": pid, "type": "place", "area": area, "level": "xa"}


def _entity(eid, etype, place_id, **kw):
    e = {"id": eid, "name": eid.upper(), "type": etype, "placeId": place_id,
         "confidence": kw.pop("confidence", 0.8), "summary": kw.pop("summary", "x" * 60)}
    e.update(kw)
    return e


@pytest.fixture
def kb_itinerary():
    """Nạp entities mẫu vào knowledge để generate_itinerary chạy không cần DB.

    Bố cục: mỗi khu vực có 1 place + vài entity (attraction/dish/craft_village...)
    trỏ placeId về place đó.
    """
    entities = {}
    # places
    entities["p-vl"] = _place("p-vl", "vinh-long")
    entities["p-bt"] = _place("p-bt", "ben-tre")
    entities["p-tv"] = _place("p-tv", "tra-vinh")

    # vinh-long content
    entities["vl-att1"] = _entity("vl-att1", "attraction", "p-vl", confidence=0.9)
    entities["vl-att2"] = _entity("vl-att2", "attraction", "p-vl", confidence=0.85)
    entities["vl-dish1"] = _entity("vl-dish1", "dish", "p-vl", confidence=0.8)
    entities["vl-craft1"] = _entity("vl-craft1", "craft_village", "p-vl", confidence=0.7)
    entities["vl-exp1"] = _entity("vl-exp1", "experience", "p-vl", confidence=0.75)
    entities["vl-prod1"] = _entity("vl-prod1", "product", "p-vl", confidence=0.6,
                                   attributes={"ocop": "4 sao"})
    # ben-tre content
    entities["bt-att1"] = _entity("bt-att1", "attraction", "p-bt", confidence=0.9)
    entities["bt-dish1"] = _entity("bt-dish1", "dish", "p-bt", confidence=0.8)
    entities["bt-exp1"] = _entity("bt-exp1", "experience", "p-bt", confidence=0.7)
    # tra-vinh content
    entities["tv-att1"] = _entity("tv-att1", "attraction", "p-tv", confidence=0.9)
    entities["tv-dish1"] = _entity("tv-dish1", "dish", "p-tv", confidence=0.8)
    # 1 entity KHÔNG có place (get_place trả None → bị loại)
    entities["orphan"] = {"id": "orphan", "name": "ORPHAN", "type": "attraction",
                          "confidence": 0.99, "summary": "z" * 60}

    with patch.object(knowledge, "_entities", entities), \
         patch.object(knowledge, "_relationships", []), \
         patch.object(knowledge, "_itineraries", {}):
        yield entities


class TestGenerateItinerary:
    def test_returns_expected_shape(self, kb_itinerary):
        out = ig.generate_itinerary(days=1, interests=["tham_quan"], areas=["vinh-long"])
        for key in ("title", "days", "areas", "interests", "month", "budget",
                    "day_plans", "tips", "total_stops"):
            assert key in out
        assert isinstance(out["day_plans"], list)
        assert isinstance(out["tips"], list)

    def test_days_clamped_upper(self, kb_itinerary):
        out = ig.generate_itinerary(days=99, interests=["tong_hop"], areas=["vinh-long"])
        assert out["days"] == 5

    def test_days_clamped_lower(self, kb_itinerary):
        out = ig.generate_itinerary(days=0, interests=["tong_hop"], areas=["vinh-long"])
        assert out["days"] == 1

    def test_days_negative_clamped(self, kb_itinerary):
        out = ig.generate_itinerary(days=-5, interests=["tong_hop"], areas=["vinh-long"])
        assert out["days"] == 1

    def test_default_interests_and_areas(self, kb_itinerary):
        # interests=None → ["tong_hop"]; areas=None → cả 3 vùng
        out = ig.generate_itinerary(days=1)
        assert out["interests"] == ["tong_hop"]
        assert out["areas"] == ["vinh-long", "ben-tre", "tra-vinh"]

    def test_one_day_five_stops(self, kb_itinerary):
        # 1 ngày → stops_per_day=5; vinh-long có đủ >=5 content entity
        out = ig.generate_itinerary(days=1, interests=["tong_hop"], areas=["vinh-long"])
        assert len(out["day_plans"]) == 1
        # 5 stops thường + có thể +1 bữa ăn được chèn
        n = len(out["day_plans"][0]["stops"])
        assert n >= 5

    def test_multi_day_four_stops_each(self, kb_itinerary):
        out = ig.generate_itinerary(days=2, interests=["tong_hop"],
                                    areas=["vinh-long", "ben-tre"])
        assert len(out["day_plans"]) == 2
        for dp in out["day_plans"]:
            base_stops = [s for s in dp["stops"] if not s.get("is_meal")]
            # mỗi ngày tối đa 4 stop thường (có thể ít hơn nếu thiếu candidate)
            assert len(base_stops) <= 4

    def test_area_filter_excludes_other_areas(self, kb_itinerary):
        # chỉ chọn vinh-long → không có entity ben-tre/tra-vinh lọt vào
        out = ig.generate_itinerary(days=1, interests=["tong_hop"], areas=["vinh-long"])
        all_ids = [s["entity"]["id"] for dp in out["day_plans"] for s in dp["stops"]]
        assert all(not i.startswith("bt-") and not i.startswith("tv-") for i in all_ids)

    def test_orphan_without_place_excluded(self, kb_itinerary):
        # entity 'orphan' confidence rất cao nhưng không có placeId → phải bị loại
        out = ig.generate_itinerary(days=1, interests=["tham_quan"], areas=["vinh-long"])
        all_ids = [s["entity"]["id"] for dp in out["day_plans"] for s in dp["stops"]]
        assert "orphan" not in all_ids

    def test_stops_have_time_and_no_time_min(self, kb_itinerary):
        # time_min là field nội bộ, phải bị strip khỏi output
        out = ig.generate_itinerary(days=1, interests=["tong_hop"], areas=["vinh-long"])
        for dp in out["day_plans"]:
            for s in dp["stops"]:
                assert "time" in s
                assert "time_min" not in s
                # time đúng định dạng HH:MM
                assert len(s["time"]) == 5 and s["time"][2] == ":"

    def test_meal_inserted_for_dish_area(self, kb_itinerary):
        # ngày 1 có 5 stops kéo dài qua trưa → nên có 1 stop is_meal
        out = ig.generate_itinerary(days=1, interests=["tong_hop"], areas=["vinh-long"])
        stops = out["day_plans"][0]["stops"]
        meals = [s for s in stops if s.get("is_meal")]
        assert len(meals) >= 1
        assert "Nghỉ trưa" in meals[0]["note"]

    def test_total_stops_matches_sum(self, kb_itinerary):
        out = ig.generate_itinerary(days=2, interests=["tong_hop"],
                                    areas=["vinh-long", "ben-tre"])
        assert out["total_stops"] == sum(len(dp["stops"]) for dp in out["day_plans"])

    def test_title_contains_area_name_and_interest(self, kb_itinerary):
        out = ig.generate_itinerary(days=2, interests=["am_thuc"], areas=["vinh-long"])
        assert "2 ngày" in out["title"]
        assert "ẩm thực" in out["title"]
        assert "Vĩnh Long" in out["title"]   # AREA_META name

    def test_title_unknown_interest_uses_raw_key(self, kb_itinerary):
        # interest lạ không có label → dùng nguyên key (nhánh fallback trong labels.get)
        out = ig.generate_itinerary(days=1, interests=["xyz_unknown"], areas=["vinh-long"])
        assert "xyz_unknown" in out["title"]

    def test_unknown_interest_maps_to_tong_hop_types(self, kb_itinerary):
        # INTEREST_MAP.get(interest, tong_hop) → interest lạ vẫn thu được candidates
        out = ig.generate_itinerary(days=1, interests=["xyz_unknown"], areas=["vinh-long"])
        total = sum(len(dp["stops"]) for dp in out["day_plans"])
        assert total >= 1   # có candidate nhờ fallback tong_hop

    def test_month_influences_tips(self, kb_itinerary):
        out = ig.generate_itinerary(days=1, interests=["tong_hop"],
                                    areas=["vinh-long"], month=7)
        assert out["month"] == 7
        assert any("mùa mưa" in t for t in out["tips"])

    def test_budget_passed_through(self, kb_itinerary):
        out = ig.generate_itinerary(days=1, interests=["tong_hop"],
                                    areas=["vinh-long"], budget="cao")
        assert out["budget"] == "cao"
        assert any("resort" in t or "cao cấp" in t for t in out["tips"])

    def test_empty_matching_area_yields_no_stops(self, kb_itinerary):
        # area 'lien-vung' không có entity nào → day_plans có stops rỗng
        out = ig.generate_itinerary(days=1, interests=["tong_hop"], areas=["lien-vung"])
        assert out["total_stops"] == 0
        assert out["day_plans"][0]["stops"] == []

    def test_am_thuc_only_selects_food_types(self, kb_itinerary):
        # interest am_thuc → target types dish/product; không có attraction
        out = ig.generate_itinerary(days=1, interests=["am_thuc"], areas=["vinh-long"])
        types = {s["entity"]["type"] for dp in out["day_plans"]
                 for s in dp["stops"] if not s.get("is_meal")}
        assert types <= {"dish", "product"}

    def test_area_focus_present(self, kb_itinerary):
        out = ig.generate_itinerary(days=1, interests=["tong_hop"], areas=["vinh-long"])
        assert out["day_plans"][0]["area_focus"] == "vinh-long"
