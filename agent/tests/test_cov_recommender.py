"""Unit tests cho recommender.py — content-based, user-profile, trending,
contextual, unified merge/dedup. Module thuần logic (không PG/network).

Mỗi test gọi hàm THẬT với input thật và assert side-effect/output thật;
được thiết kế để bắt regression nếu công thức scoring/ranking/merge sai.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import recommender as rec  # noqa: E402


# ══════════════════════════════════════════════════
#  Fixtures / helpers
# ══════════════════════════════════════════════════

def _place(pid, area, **extra):
    return {"id": pid, "name": pid, "type": "place", "area": area, **extra}


def _content(eid, etype="attraction", **extra):
    base = {"id": eid, "name": eid.upper(), "type": etype}
    base.update(extra)
    return base


@pytest.fixture
def corpus():
    """Small entity corpus with 2 areas, tags, confidence, seasons."""
    return {
        "ward-a": _place("ward-a", "vinh-long"),
        "ward-b": _place("ward-b", "ben-tre"),
        "att-1": _content(
            "att-1", "attraction", placeId="ward-a",
            tags=["Song", "Xanh"], confidence=0.9,
            summary="x" * 150,
        ),
        "att-2": _content(
            "att-2", "attraction", placeId="ward-a",
            tags=["song", "co"], confidence=0.5,
        ),
        "dish-1": _content(
            "dish-1", "dish", placeId="ward-b",
            tags=["cay"], confidence=0.7,
        ),
        "nat-1": _content(
            "nat-1", "nature", placeId="ward-b",
            tags=["xanh"], confidence=0.3,
            season={"months": [1, 2, 3], "peak": [2]},
        ),
    }


# ══════════════════════════════════════════════════
#  Helper functions
# ══════════════════════════════════════════════════

def test_get_tags_normalizes_and_filters_non_strings():
    tags = rec._get_tags({"tags": ["  Sông ", "XANH", 42, None, "xanh"]})
    # lowercased, stripped, ints/None dropped, deduped as a set
    assert tags == {"sông", "xanh"}


def test_get_tags_non_list_returns_empty():
    assert rec._get_tags({"tags": "not-a-list"}) == set()
    assert rec._get_tags({}) == set()


def test_get_area_resolves_via_placeid():
    entities = {"w": {"id": "w", "type": "place", "area": "tra-vinh"}}
    assert rec._get_area({"placeId": "w"}, entities) == "tra-vinh"


def test_get_area_missing_placeid_or_place():
    assert rec._get_area({}, {}) is None
    # placeId points to a non-existent place
    assert rec._get_area({"placeId": "ghost"}, {}) is None


def test_get_ward_id_prefers_placeid_then_ward_id():
    assert rec._get_ward_id({"placeId": "p1", "ward_id": "w1"}) == "p1"
    assert rec._get_ward_id({"ward_id": "w1"}) == "w1"
    assert rec._get_ward_id({}) is None


def test_entity_in_season_no_season_always_true():
    assert rec._entity_in_season({}, 6) is True
    # season present but empty months list -> unrestricted
    assert rec._entity_in_season({"season": {"months": []}}, 6) is True


def test_entity_in_season_month_membership():
    e = {"season": {"months": [10, 11, 12]}}
    assert rec._entity_in_season(e, 11) is True
    assert rec._entity_in_season(e, 6) is False


def test_entity_in_peak():
    assert rec._entity_in_peak({}, 6) is False  # no season -> not peak
    e = {"season": {"months": [1, 2, 3], "peak": [2]}}
    assert rec._entity_in_peak(e, 2) is True
    assert rec._entity_in_peak(e, 1) is False
    # peak key missing -> falls back to empty list
    assert rec._entity_in_peak({"season": {"months": [1]}}, 1) is False


def test_is_content_entity():
    assert rec._is_content_entity({"type": "dish"}) is True
    assert rec._is_content_entity({"type": "place"}) is False
    assert rec._is_content_entity({}) is False


def test_build_relationship_index_bidirectional_and_skips_blank():
    rels = [
        {"from": "a", "to": "b"},
        {"from": "b", "to": "c"},
        {"from": "", "to": "z"},   # skipped: blank from
        {"from": "x", "to": ""},   # skipped: blank to
    ]
    idx = rec._build_relationship_index(rels)
    assert idx["a"] == {"b"}
    assert idx["b"] == {"a", "c"}
    assert idx["c"] == {"b"}
    assert "z" not in idx and "x" not in idx


# ══════════════════════════════════════════════════
#  1. recommend_by_entity
# ══════════════════════════════════════════════════

def test_recommend_by_entity_unknown_or_place_source_returns_empty(corpus):
    assert rec.recommend_by_entity("nope", corpus, []) == []
    # a place is not a content entity
    assert rec.recommend_by_entity("ward-a", corpus, []) == []


def test_recommend_by_entity_same_type_and_tags_beat_others(corpus):
    out = rec.recommend_by_entity("att-1", corpus, [])
    ids = [r["id"] for r in out]
    # source att-1 excluded; att-2 shares type(attraction)+area+a tag -> top
    assert "att-1" not in ids
    assert ids[0] == "att-2"
    top = out[0]
    assert "same_type" in top["reason"]
    assert "same_area" in top["reason"]
    assert "shared_tags" in top["reason"]


def test_recommend_by_entity_same_ward_bonus_present(corpus):
    out = rec.recommend_by_entity("att-1", corpus, [])
    att2 = next(r for r in out if r["id"] == "att-2")
    # att-1 and att-2 both placeId=ward-a -> same_ward bonus reason
    assert "same_ward" in att2["reason"]


def test_recommend_by_entity_relationship_adds_score_and_reason(corpus):
    # dish-1 shares no type/area/tags with att-1, so without a relationship it
    # scores 0 and is dropped entirely; the relationship is what surfaces it.
    rels = [{"from": "att-1", "to": "dish-1", "type": "near"}]
    with_rel = rec.recommend_by_entity("att-1", corpus, rels)
    without = rec.recommend_by_entity("att-1", corpus, [])
    d_with = next(r for r in with_rel if r["id"] == "dish-1")
    assert "related" in d_with["reason"]
    # relationship weight (0.2) is the sole contributor here
    assert d_with["score"] == pytest.approx(rec.W_RELATIONSHIP, abs=1e-9)
    # dish-1 absent when there is no relationship
    assert all(r["id"] != "dish-1" for r in without)


def test_recommend_by_entity_limit_respected(corpus):
    out = rec.recommend_by_entity("att-1", corpus, [], limit=1)
    assert len(out) == 1


def test_recommend_by_entity_confidence_tiebreak(corpus):
    # Two candidates with identical scoring signal but different confidence.
    ents = {
        "src": _content("src", "dish", tags=["a"], confidence=0.5),
        "hi": _content("hi", "dish", tags=["a"], confidence=0.95),
        "lo": _content("lo", "dish", tags=["a"], confidence=0.10),
    }
    out = rec.recommend_by_entity("src", ents, [])
    ids = [r["id"] for r in out]
    # same score (same_type+shared_tags), higher confidence ranks first
    assert ids.index("hi") < ids.index("lo")


def test_recommend_by_entity_no_tag_overlap_no_shared_reason():
    ents = {
        "src": _content("src", "dish", tags=["a"]),
        "cand": _content("cand", "dish", tags=["b"]),
    }
    out = rec.recommend_by_entity("src", ents, [])
    cand = next(r for r in out if r["id"] == "cand")
    # union>0 but intersection==0 -> tag_sim=0, no shared_tags reason
    assert "shared_tags" not in cand["reason"]
    assert "same_type" in cand["reason"]


# ══════════════════════════════════════════════════
#  2. recommend_for_user
# ══════════════════════════════════════════════════

def test_recommend_for_user_interest_maps_to_types(corpus):
    profile = {"interests": ["am_thuc"]}  # -> dish, product
    out = rec.recommend_for_user(profile, corpus)
    dish = next(r for r in out if r["id"] == "dish-1")
    assert "matches_interest" in dish["reason"]
    att = next((r for r in out if r["id"] == "att-1"), None)
    if att is not None:
        assert "matches_interest" not in att["reason"]


def test_recommend_for_user_preferred_area_and_visited(corpus):
    profile = {
        "interests": ["tham_quan"],       # attraction, experience
        "preferred_areas": ["vinh-long"],
        "visited_entities": ["att-1"],
    }
    out = rec.recommend_for_user(profile, corpus)
    att1 = next(r for r in out if r["id"] == "att-1")
    att2 = next(r for r in out if r["id"] == "att-2")
    # att-1 visited -> no not_visited reason; att-2 not visited -> has it
    assert "not_visited" not in att1["reason"]
    assert "not_visited" in att2["reason"]
    # both in vinh-long (preferred)
    assert "preferred_area" in att1["reason"]
    assert "preferred_area" in att2["reason"]


def test_recommend_for_user_high_confidence_reason(corpus):
    out = rec.recommend_for_user({"interests": ["tham_quan"]}, corpus)
    att1 = next(r for r in out if r["id"] == "att-1")  # confidence 0.9
    assert "high_confidence" in att1["reason"]


def test_recommend_for_user_diversity_caps_three_per_type():
    ents = {}
    for i in range(6):
        ents[f"d{i}"] = _content(f"d{i}", "dish", confidence=0.5)
    out = rec.recommend_for_user({"interests": ["am_thuc"]}, ents, limit=10)
    dish_count = sum(1 for r in out if r["type"] == "dish")
    assert dish_count == 3  # capped at 3 per type


def test_recommend_for_user_limit_respected():
    ents = {}
    for t in ["dish", "attraction", "nature", "product"]:
        for i in range(3):
            ents[f"{t}{i}"] = _content(f"{t}{i}", t, confidence=0.5)
    out = rec.recommend_for_user({"interests": ["tong_hop"]}, ents, limit=5)
    assert len(out) == 5


def test_recommend_for_user_empty_profile_still_scores_via_not_visited(corpus):
    # No interests/areas: only the not_visited(0.2) + popularity signals fire.
    out = rec.recommend_for_user({}, corpus)
    assert out, "should still return recommendations from not_visited/popularity"
    for r in out:
        assert r["score"] > 0


def test_recommend_for_user_zero_confidence_no_popularity_bump():
    ents = {"d": _content("d", "dish", confidence=0)}
    out = rec.recommend_for_user({"interests": ["am_thuc"]}, ents)
    d = next(r for r in out if r["id"] == "d")
    # interest(0.4)+not_visited(0.2) only, no popularity term
    assert d["score"] == pytest.approx(0.6, abs=1e-9)


# ══════════════════════════════════════════════════
#  3. recommend_trending
# ══════════════════════════════════════════════════

def test_recommend_trending_skips_missing_and_place_entities(corpus):
    analytics = {"entity_hits": {"att-1": 10, "ward-a": 99, "ghost": 5}}
    out = rec.recommend_trending(analytics, corpus)
    ids = {r["id"] for r in out}
    assert "att-1" in ids
    assert "ward-a" not in ids   # place skipped
    assert "ghost" not in ids    # not in corpus


def test_recommend_trending_fresh_discovery_bonus(corpus):
    # low-hit entity gets +1.5 fresh_discovery boost & reason
    analytics = {"entity_hits": {"dish-1": 2}}
    out = rec.recommend_trending(analytics, corpus)
    d = next(r for r in out if r["id"] == "dish-1")
    assert "fresh_discovery" in d["reason"]
    assert "hits(2)" in d["reason"]


def test_recommend_trending_popular_reason_for_high_relative_hits():
    ents = {
        "hot": _content("hot", "attraction", confidence=0.5),
        "mid": _content("mid", "attraction", confidence=0.5),
    }
    analytics = {"entity_hits": {"hot": 100, "mid": 80}}
    out = rec.recommend_trending(analytics, ents)
    hot = next(r for r in out if r["id"] == "hot")
    # relative_pop = 100/100 = 1.0 >= 0.7 -> "popular"
    assert "popular" in hot["reason"]


# (Đã bỏ test recency_boost_branch: khối `recent_boost` recommender.py:383-400 là
#  DEAD CODE — tính rồi không đọc lại vào scoring; output giống hệt khi có/không
#  queries. Test đó chỉ phủ nhánh chết + tautology. Dead-code flag riêng cho chủ.)


def test_recommend_trending_empty_hits_returns_empty(corpus):
    assert rec.recommend_trending({"entity_hits": {}}, corpus) == []
    assert rec.recommend_trending({}, corpus) == []


def test_recommend_trending_confidence_lifts_score():
    ents = {
        "a": _content("a", "attraction", confidence=1.0),
        "b": _content("b", "attraction", confidence=0.0),
    }
    analytics = {"entity_hits": {"a": 50, "b": 50}}
    out = rec.recommend_trending(analytics, ents)
    a = next(r for r in out if r["id"] == "a")
    b = next(r for r in out if r["id"] == "b")
    # same hits, confidence*0.5 makes a strictly higher
    assert a["score"] > b["score"]
    assert round(a["score"] - b["score"], 4) == 0.5


def test_recommend_trending_fills_and_limits():
    # More fresh entities than the 40% fresh budget -> fill loop must top up.
    ents = {f"f{i}": _content(f"f{i}", "attraction", confidence=0.5) for i in range(8)}
    analytics = {"entity_hits": {f"f{i}": 1 for i in range(8)}}
    out = rec.recommend_trending(analytics, ents, limit=5)
    assert len(out) == 5
    # no duplicate ids after merge/fill
    assert len({r["id"] for r in out}) == 5


# ══════════════════════════════════════════════════
#  4. recommend_contextual
# ══════════════════════════════════════════════════

def test_recommend_trending_fill_loop_tops_up_from_remaining():
    # Mix of mid-range hitters (neither fresh nor >=0.7 relative) so that the
    # popular/fresh split leaves a gap the fill loop must close from `scored`.
    ents = {f"m{i}": _content(f"m{i}", "attraction", confidence=0.5) for i in range(6)}
    # max hits 100; mid entities at 30 -> relative_pop 0.3 (<0.7) and hits>3
    hits = {"m0": 100}
    for i in range(1, 6):
        hits[f"m{i}"] = 30
    out = rec.recommend_trending({"entity_hits": hits}, ents, limit=6)
    # all six surface, no duplicates -> fill loop exercised
    assert len(out) == 6
    assert len({r["id"] for r in out}) == 6


def test_recommend_contextual_preferred_intersection_scores_highest(corpus):
    # rainy ∩ evening: dish, accommodation, ... ; dish-1 should fit strongly.
    out = rec.recommend_contextual(6, "evening", "rainy", corpus)
    dish = next((r for r in out if r["id"] == "dish-1"), None)
    assert dish is not None
    assert "fits_rainy_evening" in dish["reason"]


def test_recommend_contextual_skips_types_out_of_all_context():
    # weather=sunny types + time=evening types; 'history' fits neither -> skipped.
    ents = {
        "h": _content("h", "history"),
        "n": _content("n", "nature"),
    }
    out = rec.recommend_contextual(6, "evening", "sunny", ents)
    ids = {r["id"] for r in out}
    assert "n" in ids          # nature fits sunny
    assert "h" not in ids      # history fits neither sunny nor evening -> continue


def test_recommend_contextual_peak_season_beats_in_season(corpus):
    # nat-1 season months [1,2,3], peak [2].
    peak_out = rec.recommend_contextual(2, "morning", "sunny", corpus)
    in_out = rec.recommend_contextual(1, "morning", "sunny", corpus)
    nat_peak = next(r for r in peak_out if r["id"] == "nat-1")
    nat_in = next(r for r in in_out if r["id"] == "nat-1")
    assert "peak_season" in nat_peak["reason"]
    assert "in_season" in nat_in["reason"]
    assert nat_peak["score"] > nat_in["score"]


def test_recommend_contextual_out_of_season_penalty_can_drop_entity():
    # nature fits sunny (0.4) but out of season penalty is -0.1 -> still >0,
    # confidence 0 -> score 0.3. Compare to in-season variant being higher.
    ent_out = {"n": _content("n", "nature", season={"months": [7], "peak": []})}
    out = rec.recommend_contextual(1, "morning", "sunny", ent_out)  # month 1 not in season
    n = next(r for r in out if r["id"] == "n")
    # 0.4 (fits) - 0.1 (out of season) = 0.3
    assert n["score"] == pytest.approx(0.3, abs=1e-9)
    assert "in_season" not in n["reason"] and "peak_season" not in n["reason"]


def test_recommend_contextual_rich_content_bonus():
    ents = {
        "rich": _content("rich", "nature", summary="z" * 200),
        "thin": _content("thin", "nature", summary="short"),
    }
    out = rec.recommend_contextual(6, "morning", "sunny", ents)
    rich = next(r for r in out if r["id"] == "rich")
    thin = next(r for r in out if r["id"] == "thin")
    assert "rich_content" in rich["reason"]
    assert "rich_content" not in thin["reason"]
    assert rich["score"] > thin["score"]


def test_recommend_contextual_unknown_weather_time_fallback_union():
    # Unknown keys -> _WEATHER_TYPES/_TIME_TYPES default to CARD_TYPES,
    # intersection == all -> nothing skipped for a valid content type.
    ents = {"d": _content("d", "dish", confidence=0.5)}
    out = rec.recommend_contextual(6, "bogus_time", "bogus_weather", ents)
    assert any(r["id"] == "d" for r in out)


def test_recommend_contextual_fits_weather_only_branch():
    # product fits rainy (weather) but morning time_types doesn't include product?
    # morning types include product, so pick a type only in weather set.
    # 'accommodation' is in rainy weather but NOT in morning time set.
    ents = {"acc": _content("acc", "accommodation", confidence=0.5)}
    out = rec.recommend_contextual(6, "morning", "rainy", ents)
    acc = next(r for r in out if r["id"] == "acc")
    assert "fits_rainy" in acc["reason"]
    assert "fits_rainy_morning" not in acc["reason"]


def test_recommend_contextual_union_fallback_when_intersection_empty(monkeypatch):
    # Force disjoint weather/time type sets so the intersection is empty and
    # the code falls back to the union (line: preferred = weather | time).
    monkeypatch.setitem(rec._WEATHER_TYPES, "rainy", ["dish"])
    monkeypatch.setitem(rec._TIME_TYPES, "evening", ["nature"])
    ents = {
        "d": _content("d", "dish", confidence=0.5),
        "n": _content("n", "nature", confidence=0.5),
    }
    out = rec.recommend_contextual(6, "evening", "rainy", ents)
    ids = {r["id"] for r in out}
    # Union fallback means BOTH the dish (weather) and nature (time) qualify,
    # each via the top "fits_rainy_evening" branch since union == preferred.
    assert ids == {"d", "n"}
    for r in out:
        assert "fits_rainy_evening" in r["reason"]


def test_recommend_contextual_fits_time_only_branch():
    # 'event' is in evening time set but NOT in sunny... actually event IS in sunny.
    # Use 'history': in afternoon time set, not in sunny weather set.
    ents = {"his": _content("his", "history", confidence=0.5)}
    out = rec.recommend_contextual(6, "afternoon", "sunny", ents)
    his = next(r for r in out if r["id"] == "his")
    assert "fits_afternoon" in his["reason"]


# ══════════════════════════════════════════════════
#  5. recommend (unified) + _merge_results
# ══════════════════════════════════════════════════

def test_recommend_no_entities_returns_no_entities_strategy():
    assert rec.recommend({"entities": {}}) == {
        "recommendations": [], "strategy": "no_entities",
    }


def test_recommend_content_based_strategy(corpus):
    out = rec.recommend({"entities": corpus, "entity_id": "att-1", "relationships": []})
    assert out["strategy"] == "content_based"
    assert out["recommendations"]
    # internal fields cleaned
    for r in out["recommendations"]:
        assert "_source" not in r and "_sources" not in r


def test_recommend_ignores_unknown_entity_id_falls_back(corpus):
    # entity_id not in entities -> content_based skipped -> fallback contextual.
    out = rec.recommend({"entities": corpus, "entity_id": "ghost"})
    assert out["strategy"] == "contextual_fallback"


def test_recommend_user_profile_strategy(corpus):
    out = rec.recommend({
        "entities": corpus,
        "user_profile": {"interests": ["am_thuc"]},
    })
    assert out["strategy"] == "user_profile"


def test_recommend_trending_strategy(corpus):
    out = rec.recommend({
        "entities": corpus,
        "analytics_data": {"entity_hits": {"att-1": 10}},
    })
    assert out["strategy"] == "trending"


def test_recommend_contextual_needs_month_and_time_or_weather(corpus):
    # month alone (no time/weather) does NOT trigger contextual -> fallback.
    only_month = rec.recommend({"entities": corpus, "month": 6})
    assert only_month["strategy"] == "contextual_fallback"
    # month + weather triggers contextual
    with_weather = rec.recommend({"entities": corpus, "month": 6, "weather": "sunny"})
    assert with_weather["strategy"] == "contextual"


def test_recommend_combines_multiple_strategies(corpus):
    out = rec.recommend({
        "entities": corpus,
        "entity_id": "att-1",
        "user_profile": {"interests": ["tham_quan"]},
        "analytics_data": {"entity_hits": {"att-1": 10}},
        "month": 6, "weather": "rainy", "time_of_day": "evening",
    })
    parts = out["strategy"].split(" + ")
    assert parts == ["content_based", "user_profile", "trending", "contextual"]


def test_recommend_fallback_morning_bucket(corpus, monkeypatch):
    # hour < 12 -> morning branch of the contextual fallback.
    class _MorningDT(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 7, 8, 8, 0, 0, tzinfo=tz or timezone.utc)

    monkeypatch.setattr(rec, "datetime", _MorningDT)
    out = rec.recommend({"entities": corpus})
    assert out["strategy"] == "contextual_fallback"
    assert out["recommendations"]


def test_recommend_fallback_afternoon_bucket(corpus, monkeypatch):
    # 12 <= hour < 17 -> afternoon branch.
    class _NoonDT(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 7, 8, 14, 0, 0, tzinfo=tz or timezone.utc)

    monkeypatch.setattr(rec, "datetime", _NoonDT)
    out = rec.recommend({"entities": corpus})
    assert out["strategy"] == "contextual_fallback"


def test_recommend_fallback_uses_current_hour_bucket(corpus, monkeypatch):
    # Force a deterministic "now" so the morning/afternoon/evening branch is known.
    class _FixedDT(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 7, 8, 20, 0, 0, tzinfo=tz or timezone.utc)

    monkeypatch.setattr(rec, "datetime", _FixedDT)
    out = rec.recommend({"entities": corpus})
    assert out["strategy"] == "contextual_fallback"
    assert out["recommendations"]  # evening bucket produced results


def test_recommend_limit_caps_final_results():
    ents = {f"d{i}": _content(f"d{i}", "dish", confidence=0.5) for i in range(20)}
    out = rec.recommend({
        "entities": ents,
        "user_profile": {"interests": ["am_thuc"]},
        "limit": 3,
    })
    assert len(out["recommendations"]) <= 3


def test_merge_results_dedup_keeps_higher_score_and_unions_reasons():
    results = [
        {"id": "x", "name": "X", "type": "dish", "score": 0.5,
         "reason": "a, b", "_source": "content_based"},
        {"id": "x", "name": "X", "type": "dish", "score": 0.9,
         "reason": "b, c", "_source": "trending"},
    ]
    merged = rec._merge_results(results, limit=10)
    assert len(merged) == 1
    entry = merged[0]
    # higher score wins
    assert entry["score"] > 0.9  # 0.9 + multi_signal bonus 0.1
    # reasons unioned & sorted
    reason_parts = entry["reason"].split(", ")
    assert "a" in reason_parts and "b" in reason_parts and "c" in reason_parts
    # multi-source bonus reason appended
    assert any("multi_signal" in p for p in reason_parts)


def test_merge_results_multi_signal_bonus_only_for_multiple_sources():
    single = [
        {"id": "y", "name": "Y", "type": "dish", "score": 0.5,
         "reason": "a", "_source": "content_based"},
    ]
    merged = rec._merge_results(single, limit=10)
    # one source -> no bonus, score unchanged, no multi_signal reason
    assert merged[0]["score"] == 0.5
    assert "multi_signal" not in merged[0]["reason"]


def test_merge_results_sorts_and_limits():
    results = [
        {"id": f"e{i}", "name": f"E{i}", "type": "dish", "score": i / 10,
         "reason": "r", "_source": "content_based"}
        for i in range(6)
    ]
    merged = rec._merge_results(results, limit=3)
    assert len(merged) == 3
    scores = [m["score"] for m in merged]
    assert scores == sorted(scores, reverse=True)
    # top-3 by score
    assert merged[0]["id"] == "e5"


def test_recommend_is_locked_but_reentrant_via_impl(corpus):
    # recommend() acquires _lock then delegates to _recommend_impl.
    # Calling the impl directly must produce the same shape (no lock needed).
    ctx = {"entities": corpus, "entity_id": "att-1", "relationships": []}
    via_public = rec.recommend(ctx)
    via_impl = rec._recommend_impl(ctx)
    assert via_public["strategy"] == via_impl["strategy"] == "content_based"
