"""
Real unit tests for agent/freshness.py — Content Freshness Checker.

Covers pure helpers (date/location/source extraction, parsing, knowledge
classification), the core check_freshness tally logic, refresh-candidate
prioritization/sorting, human-readable report generation, the queue-writing
scheduler, and the CLI dispatch. I/O boundaries (data.json / analytics.json /
refresh_queue.json) are redirected to tmp paths via monkeypatch so the logic
around them is exercised without touching real project data.
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import freshness


# ══════════════════════════════════════════════════
#  Helpers: date/location/source extraction
# ══════════════════════════════════════════════════

class TestGetDateField:
    def test_prefers_learned_at(self):
        e = {"learned_at": "2026-01-01", "updatedAt": "2025-01-01"}
        assert freshness._get_date_field(e) == "2026-01-01"

    def test_falls_back_to_updated_at(self):
        e = {"updatedAt": "2025-05-05"}
        assert freshness._get_date_field(e) == "2025-05-05"

    def test_none_when_missing(self):
        assert freshness._get_date_field({}) is None


class TestGetLocationField:
    def test_prefers_ward_id(self):
        e = {"ward_id": "w1", "placeId": "p1", "area": "a1"}
        assert freshness._get_location_field(e) == "w1"

    def test_falls_back_to_place_id(self):
        e = {"placeId": "p1", "area": "a1"}
        assert freshness._get_location_field(e) == "p1"

    def test_falls_back_to_area(self):
        assert freshness._get_location_field({"area": "a1"}) == "a1"

    def test_none_when_all_missing(self):
        assert freshness._get_location_field({}) is None


class TestGetSourceValue:
    def test_none_when_absent(self):
        assert freshness._get_source_value({}) is None

    def test_string_source(self):
        assert freshness._get_source_value({"source": "manual"}) == "manual"

    def test_blank_string_source_is_none(self):
        # whitespace-only string must collapse to None, not "   "
        assert freshness._get_source_value({"source": "   "}) is None

    def test_dict_source_prefers_title(self):
        src = {"title": "Báo VL", "url": "http://x"}
        assert freshness._get_source_value({"source": src}) == "Báo VL"

    def test_dict_source_url_when_no_title(self):
        src = {"url": "http://x"}
        assert freshness._get_source_value({"source": src}) == "http://x"

    def test_dict_source_empty_is_none(self):
        assert freshness._get_source_value({"source": {}}) is None

    def test_non_str_non_dict_source_is_none(self):
        # e.g. a list — hits the final `return None`
        assert freshness._get_source_value({"source": [1, 2]}) is None


class TestParseDate:
    # _parse_date trả tz-aware (UTC) sau fix bug naive-vs-aware (SP3-W5).
    def test_date_only_format(self):
        assert freshness._parse_date("2026-03-15") == datetime(2026, 3, 15, tzinfo=timezone.utc)

    def test_datetime_format(self):
        assert freshness._parse_date("2026-03-15T10:20:30") == datetime(2026, 3, 15, 10, 20, 30, tzinfo=timezone.utc)

    def test_datetime_microseconds_format(self):
        got = freshness._parse_date("2026-03-15T10:20:30.500000")
        assert got == datetime(2026, 3, 15, 10, 20, 30, 500000, tzinfo=timezone.utc)

    def test_returns_timezone_aware(self):
        # Regression: phải aware để so với cutoff aware, tránh TypeError crash.
        assert freshness._parse_date("2026-03-15").tzinfo is not None

    def test_iso_offset_z_format(self):
        # Format CHÍNH trong data.json (1694/1749): '...Z'. Trước strptime không
        # nuốt → None → staleness câm lặng. Nay parse đúng thành aware UTC.
        got = freshness._parse_date("2026-07-05T00:00:00Z")
        assert got == datetime(2026, 7, 5, tzinfo=timezone.utc)
        assert got.tzinfo is not None

    def test_unparseable_returns_none(self):
        assert freshness._parse_date("not-a-date") is None

    def test_empty_string_returns_none(self):
        assert freshness._parse_date("") is None


class TestIsKnowledgeEntity:
    def test_place_without_summary_is_structural(self):
        assert freshness._is_knowledge_entity({"type": "place"}) is False

    def test_place_with_summary_is_knowledge(self):
        assert freshness._is_knowledge_entity({"type": "place", "summary": "x"}) is True

    def test_non_place_is_knowledge(self):
        assert freshness._is_knowledge_entity({"type": "dish"}) is True

    def test_missing_type_is_knowledge(self):
        # empty type != "place", so treated as knowledge
        assert freshness._is_knowledge_entity({}) is True


# ══════════════════════════════════════════════════
#  _load_data / _load_analytics (I/O with branches)
# ══════════════════════════════════════════════════

class TestLoadData:
    def test_missing_file_returns_default(self, tmp_path, monkeypatch):
        monkeypatch.setattr(freshness, "DATA_JSON", tmp_path / "nope.json")
        assert freshness._load_data() == {"entities": []}

    def test_existing_file_is_parsed(self, tmp_path, monkeypatch):
        f = tmp_path / "data.json"
        payload = {"entities": [{"id": "a"}]}
        f.write_text(json.dumps(payload), encoding="utf-8")
        monkeypatch.setattr(freshness, "DATA_JSON", f)
        assert freshness._load_data() == payload


class TestLoadAnalytics:
    def test_missing_file_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr(freshness, "ANALYTICS_FILE", tmp_path / "nope.json")
        assert freshness._load_analytics() == {}

    def test_existing_file_is_parsed(self, tmp_path, monkeypatch):
        f = tmp_path / "analytics.json"
        payload = {"entity_hits": {"a": 3}}
        f.write_text(json.dumps(payload), encoding="utf-8")
        monkeypatch.setattr(freshness, "ANALYTICS_FILE", f)
        assert freshness._load_analytics() == payload


# ══════════════════════════════════════════════════
#  check_freshness — core tally logic
# ══════════════════════════════════════════════════

# NOTE on dates: _parse_date() produces *naive* datetimes while check_freshness
# builds a timezone-aware `cutoff`. Comparing them raises TypeError, so any
# entity with a PARSEABLE date currently crashes check_freshness (see
# test_parseable_old_date_currently_raises, which pins that real behavior).
# To exercise the confidence/missing-field/summary/priority/report/CLI logic we
# therefore feed entities with an UNPARSEABLE date sentinel: _parse_date returns
# None, no stale reason is added, and the rest of the pipeline runs normally.
UNPARSEABLE = "no-date-sentinel"


def _recent_date():
    # kept for the staleness-specific asserts; unparseable so it never crashes
    return UNPARSEABLE


def _old_date(days=400):
    return UNPARSEABLE


class TestStalenessDateComparison:
    """Staleness branch: date parseable so với cutoff (aware) sau fix SP3-W5."""

    def test_parseable_old_date_flags_stale(self):
        # Sau fix _parse_date (tz-aware): date parseable cũ hơn cutoff → stale,
        # KHÔNG còn TypeError crash (bug /freshness/check 500 trước đây).
        old = (datetime.now(timezone.utc) - timedelta(days=400)).strftime("%Y-%m-%d")
        data = {"entities": [{
            "id": "e1", "name": "Old", "type": "dish",
            "summary": "x" * 50, "placeId": "w", "source": "m", "confidence": 0.9,
            "updatedAt": old,
        }]}
        res = freshness.check_freshness(data)  # default max_age_days=180
        assert res["stale"] == 1
        assert any("Stale: last updated" in r for r in res["issues"][0]["reasons"])

    def test_iso_offset_old_date_flags_stale(self):
        # Date '...Z' cũ (format chính data.json) nay được tính staleness đúng,
        # không còn câm lặng (fix 1694 entity).
        old = (datetime.now(timezone.utc) - timedelta(days=400)).strftime("%Y-%m-%dT%H:%M:%SZ")
        data = {"entities": [{
            "id": "e1", "name": "OldZ", "type": "dish",
            "summary": "x" * 50, "placeId": "w", "source": "m", "confidence": 0.9,
            "updatedAt": old,
        }]}
        assert freshness.check_freshness(data)["stale"] == 1

    def test_missing_date_flags_stale_without_crash(self):
        data = {"entities": [{
            "id": "e1", "name": "NoDate", "type": "dish",
            "summary": "x" * 50, "placeId": "w", "source": "m", "confidence": 0.9,
        }]}
        res = freshness.check_freshness(data)
        assert res["stale"] == 1
        assert any("no update date recorded" in r for r in res["issues"][0]["reasons"])

    def test_unparseable_date_not_stale(self):
        data = {"entities": [{
            "id": "e1", "name": "Bad", "type": "dish",
            "summary": "x" * 50, "placeId": "w", "source": "m", "confidence": 0.9,
            "updatedAt": "garbage-date",
        }]}
        res = freshness.check_freshness(data)
        assert res["stale"] == 0
        assert res["fresh"] == 1


class TestCheckFreshness:
    def test_empty_input(self):
        res = freshness.check_freshness({})
        assert res["total"] == 0
        assert res["fresh"] == 0
        assert res["issues"] == []

    def test_structural_places_excluded_from_total(self):
        data = {"entities": [
            {"id": "p1", "type": "place"},          # structural, filtered out
            {"id": "p2", "type": "place", "summary": "has summary"},  # knowledge
        ]}
        res = freshness.check_freshness(data)
        assert res["total"] == 1  # only the place-with-summary counts

    def test_fully_fresh_entity_has_no_issues(self):
        data = {"entities": [{
            "id": "e1",
            "name": "Entity One",
            "type": "dish",
            "summary": "A sufficiently long summary that exceeds the min length.",
            "placeId": "ward-1",
            "source": "manual",
            "confidence": 0.9,
            "updatedAt": _recent_date(),
        }]}
        res = freshness.check_freshness(data)
        assert res["total"] == 1
        assert res["fresh"] == 1
        assert res["stale"] == 0
        assert res["low_confidence"] == 0
        assert res["incomplete"] == 0
        assert res["issues"] == []

    def test_low_confidence(self):
        data = {"entities": [{
            "id": "e1", "name": "LowConf", "type": "dish",
            "summary": "A sufficiently long summary that exceeds the min length.",
            "placeId": "w", "source": "manual", "confidence": 0.3,
            "updatedAt": _recent_date(),
        }]}
        res = freshness.check_freshness(data)
        assert res["low_confidence"] == 1
        assert any("Low confidence: 0.3" in r for r in res["issues"][0]["reasons"])

    def test_confidence_none_not_flagged(self):
        # confidence missing entirely -> no low-confidence reason
        data = {"entities": [{
            "id": "e1", "name": "NoConf", "type": "dish",
            "summary": "A sufficiently long summary that exceeds the min length.",
            "placeId": "w", "source": "manual",
            "updatedAt": _recent_date(),
        }]}
        res = freshness.check_freshness(data)
        assert res["low_confidence"] == 0

    def test_confidence_at_threshold_not_flagged(self):
        # exactly DEFAULT_MIN_CONFIDENCE (0.6) is NOT < threshold
        data = {"entities": [{
            "id": "e1", "name": "Edge", "type": "dish",
            "summary": "A sufficiently long summary that exceeds the min length.",
            "placeId": "w", "source": "manual",
            "confidence": freshness.DEFAULT_MIN_CONFIDENCE,
            "updatedAt": _recent_date(),
        }]}
        res = freshness.check_freshness(data)
        assert res["low_confidence"] == 0

    def test_missing_fields_reported(self):
        data = {"entities": [{
            "id": "e1", "name": "Bare", "type": "dish",
            "confidence": 0.9,
            "updatedAt": _recent_date(),
            # no summary, no location, no source
        }]}
        res = freshness.check_freshness(data)
        assert res["incomplete"] == 1
        reason = next(r for r in res["issues"][0]["reasons"] if r.startswith("Missing"))
        assert "summary" in reason
        assert "location" in reason
        assert "source" in reason

    def test_short_summary_reported(self):
        data = {"entities": [{
            "id": "e1", "name": "Short", "type": "dish",
            "summary": "tiny",  # < DEFAULT_MIN_SUMMARY_LEN (30)
            "placeId": "w", "source": "manual", "confidence": 0.9,
            "updatedAt": _recent_date(),
        }]}
        res = freshness.check_freshness(data)
        assert res["incomplete"] == 1
        assert any("Short summary: only 4 chars" in r for r in res["issues"][0]["reasons"])

    def test_summary_at_threshold_not_short(self):
        # exactly DEFAULT_MIN_SUMMARY_LEN chars -> not < threshold -> not short
        summary = "x" * freshness.DEFAULT_MIN_SUMMARY_LEN
        data = {"entities": [{
            "id": "e1", "name": "Exact", "type": "dish",
            "summary": summary,
            "placeId": "w", "source": "manual", "confidence": 0.9,
            "updatedAt": _recent_date(),
        }]}
        res = freshness.check_freshness(data)
        assert not any("Short summary" in r for r in
                       (res["issues"][0]["reasons"] if res["issues"] else []))

    def test_id_and_name_fallbacks(self):
        # no name -> name falls back to id; no id -> "unknown"
        data = {"entities": [{
            "type": "dish",
            # nothing else -> triggers missing fields + no-date stale
        }]}
        res = freshness.check_freshness(data)
        assert res["issues"][0]["id"] == "unknown"
        assert res["issues"][0]["name"] == "unknown"

    def test_custom_max_age_days_changes_verdict(self):
        # max_age_days PHẢI tác động verdict: cùng 1 entity date ~100 ngày,
        # cửa sổ hẹp → stale, cửa sổ rộng → không stale. (Bắt regression nếu
        # tham số bị bỏ qua — trước là test-rỗng vì entity không có date.)
        old = (datetime.now(timezone.utc) - timedelta(days=100)).strftime("%Y-%m-%d")
        entity = {
            "id": "e1", "name": "Mid", "type": "dish",
            "summary": "A sufficiently long summary that exceeds the min length.",
            "placeId": "w", "source": "manual", "confidence": 0.9, "updatedAt": old,
        }
        assert freshness.check_freshness({"entities": [entity]}, max_age_days=30)["stale"] == 1
        assert freshness.check_freshness({"entities": [entity]}, max_age_days=100000)["stale"] == 0

    def test_fresh_count_is_total_minus_issues(self):
        data = {"entities": [
            {  # fresh
                "id": "ok", "name": "OK", "type": "dish",
                "summary": "A sufficiently long summary that exceeds the min length.",
                "placeId": "w", "source": "manual", "confidence": 0.9,
                "updatedAt": _recent_date(),
            },
            {  # has issue
                "id": "bad", "name": "Bad", "type": "dish",
                "confidence": 0.9, "updatedAt": _recent_date(),
            },
        ]}
        res = freshness.check_freshness(data)
        assert res["total"] == 2
        assert len(res["issues"]) == 1
        assert res["fresh"] == 1


# ══════════════════════════════════════════════════
#  auto_refresh_candidates — priority + sort
# ══════════════════════════════════════════════════

class TestAutoRefreshCandidates:
    def _patch_hits(self, monkeypatch, hits):
        monkeypatch.setattr(freshness, "_load_analytics", lambda: {"entity_hits": hits})

    def test_empty_when_no_issues(self, monkeypatch):
        self._patch_hits(monkeypatch, {})
        data = {"entities": [{
            "id": "ok", "name": "OK", "type": "dish",
            "summary": "A sufficiently long summary that exceeds the min length.",
            "placeId": "w", "source": "manual", "confidence": 0.9,
            "updatedAt": _recent_date(),
        }]}
        assert freshness.auto_refresh_candidates(data) == []

    def test_priority_stale_popular_beats_stale_unpopular(self, monkeypatch):
        self._patch_hits(monkeypatch, {"pop": 50})
        # stale via missing-date (no crash); complete otherwise so only stale fires
        data = {"entities": [
            {"id": "pop", "name": "Popular Stale", "type": "dish",
             "summary": "A sufficiently long summary that exceeds the min length.",
             "placeId": "w", "source": "manual", "confidence": 0.9},
            {"id": "unpop", "name": "Unpopular Stale", "type": "dish",
             "summary": "A sufficiently long summary that exceeds the min length.",
             "placeId": "w", "source": "manual", "confidence": 0.9},
        ]}
        cands = freshness.auto_refresh_candidates(data)
        assert cands[0]["id"] == "pop"
        assert cands[0]["priority"] == 1
        assert cands[0]["hits"] == 50
        assert cands[1]["id"] == "unpop"
        assert cands[1]["priority"] == 2

    def test_incomplete_priority_3(self, monkeypatch):
        self._patch_hits(monkeypatch, {})
        # recent date + missing fields => incomplete only, not stale
        data = {"entities": [{
            "id": "inc", "name": "Incomplete", "type": "dish",
            "confidence": 0.9, "updatedAt": _recent_date(),
            # no summary/location/source
        }]}
        cands = freshness.auto_refresh_candidates(data)
        assert cands[0]["priority"] == 3

    def test_low_confidence_only_priority_4(self, monkeypatch):
        self._patch_hits(monkeypatch, {})
        # fresh date, complete fields, only low confidence => priority 4
        data = {"entities": [{
            "id": "lc", "name": "LowConf", "type": "dish",
            "summary": "A sufficiently long summary that exceeds the min length.",
            "placeId": "w", "source": "manual", "confidence": 0.2,
            "updatedAt": _recent_date(),
        }]}
        cands = freshness.auto_refresh_candidates(data)
        assert cands[0]["priority"] == 4

    def test_sort_within_tier_by_hits_desc(self, monkeypatch):
        # two stale+popular entities (stale via missing-date), higher hits first
        self._patch_hits(monkeypatch, {"a": 3, "b": 99})
        data = {"entities": [
            {"id": "a", "name": "A", "type": "dish",
             "summary": "A sufficiently long summary that exceeds the min length.",
             "placeId": "w", "source": "manual", "confidence": 0.9},
            {"id": "b", "name": "B", "type": "dish",
             "summary": "A sufficiently long summary that exceeds the min length.",
             "placeId": "w", "source": "manual", "confidence": 0.9},
        ]}
        cands = freshness.auto_refresh_candidates(data)
        assert [c["id"] for c in cands] == ["b", "a"]

    def test_limit_truncates(self, monkeypatch):
        self._patch_hits(monkeypatch, {})
        entities = []
        for i in range(5):
            entities.append({
                "id": f"e{i}", "name": f"E{i}", "type": "dish",
                "confidence": 0.9, "updatedAt": _recent_date(),
            })
        cands = freshness.auto_refresh_candidates({"entities": entities}, limit=2)
        assert len(cands) == 2


# ══════════════════════════════════════════════════
#  freshness_report — string builder
# ══════════════════════════════════════════════════

class TestFreshnessReport:
    def test_no_entities_message(self):
        assert freshness.freshness_report({}) == "No knowledge entities found."

    def test_all_fresh_message(self, monkeypatch):
        monkeypatch.setattr(freshness, "_load_analytics", lambda: {"entity_hits": {}})
        data = {"entities": [{
            "id": "e1", "name": "OK", "type": "dish",
            "summary": "A sufficiently long summary that exceeds the min length.",
            "placeId": "w", "source": "manual", "confidence": 0.9,
            "updatedAt": _recent_date(),
        }]}
        report = freshness.freshness_report(data)
        assert "All entities are fresh and complete!" in report
        assert "Total entities:    1" in report
        # no issue sections rendered
        assert "STALE ENTITIES" not in report

    def test_report_contains_all_issue_sections(self, monkeypatch):
        monkeypatch.setattr(freshness, "_load_analytics", lambda: {"entity_hits": {"stale1": 7}})
        data = {"entities": [
            # stale via missing-date, complete otherwise -> STALE section only
            {"id": "stale1", "name": "StaleOne", "type": "dish",
             "summary": "A sufficiently long summary that exceeds the min length.",
             "placeId": "w", "source": "manual", "confidence": 0.9},
            # unparseable date (not stale) + low confidence -> LOW CONFIDENCE
            {"id": "lc1", "name": "LowConfOne", "type": "dish",
             "summary": "A sufficiently long summary that exceeds the min length.",
             "placeId": "w", "source": "manual", "confidence": 0.1,
             "updatedAt": _recent_date()},
            # unparseable date (not stale) + missing fields -> INCOMPLETE
            {"id": "inc1", "name": "IncompleteOne", "type": "dish",
             "confidence": 0.9, "updatedAt": _recent_date()},
        ]}
        report = freshness.freshness_report(data)
        assert "CONTENT FRESHNESS REPORT" in report
        assert "STALE ENTITIES (" in report
        assert "LOW CONFIDENCE (" in report
        assert "INCOMPLETE ENTITIES (" in report
        assert "TOP REFRESH CANDIDATES" in report
        # popular stale entity shows its query count
        assert "(7 queries)" in report
        assert "[stale1] StaleOne" in report

    def test_report_truncates_long_stale_list(self, monkeypatch):
        monkeypatch.setattr(freshness, "_load_analytics", lambda: {"entity_hits": {}})
        entities = []
        for i in range(35):  # > 30 -> triggers "... and N more"
            entities.append({
                "id": f"s{i}", "name": f"S{i}", "type": "dish",
                "summary": "A sufficiently long summary that exceeds the min length.",
                "placeId": "w", "source": "manual", "confidence": 0.9,
                # no updatedAt -> stale via missing-date (no crash)
            })
        report = freshness.freshness_report({"entities": entities})
        assert "... and 5 more" in report  # 35 - 30

    def test_report_truncates_long_low_confidence_list(self, monkeypatch):
        monkeypatch.setattr(freshness, "_load_analytics", lambda: {"entity_hits": {}})
        entities = []
        for i in range(25):  # > 20 low-conf cap -> "... and 5 more"
            entities.append({
                "id": f"lc{i}", "name": f"LC{i}", "type": "dish",
                "summary": "A sufficiently long summary that exceeds the min length.",
                "placeId": "w", "source": "manual", "confidence": 0.1,
                "updatedAt": _recent_date(),  # unparseable -> not stale
            })
        report = freshness.freshness_report({"entities": entities})
        assert "LOW CONFIDENCE (25)" in report
        assert "... and 5 more" in report  # 25 - 20

    def test_report_truncates_long_incomplete_list(self, monkeypatch):
        monkeypatch.setattr(freshness, "_load_analytics", lambda: {"entity_hits": {}})
        entities = []
        for i in range(25):  # > 20 incomplete cap -> "... and 5 more"
            # complete except a short summary -> incomplete only, not stale
            entities.append({
                "id": f"inc{i}", "name": f"INC{i}", "type": "dish",
                "summary": "short",  # < 30 chars
                "placeId": "w", "source": "manual", "confidence": 0.9,
                "updatedAt": _recent_date(),  # unparseable -> not stale
            })
        report = freshness.freshness_report({"entities": entities})
        assert "INCOMPLETE ENTITIES (25)" in report
        assert "... and 5 more" in report  # 25 - 20

    def test_report_percentages_present(self, monkeypatch):
        monkeypatch.setattr(freshness, "_load_analytics", lambda: {"entity_hits": {}})
        data = {"entities": [
            {  # fresh: đầy đủ field + date mới (recipe từ test_fresh_count)
                "id": "ok", "name": "OK", "type": "dish",
                "summary": "A sufficiently long summary that exceeds the min length.",
                "placeId": "w", "source": "manual", "confidence": 0.9,
                "updatedAt": _recent_date(),
            },
            {  # có issue (thiếu field) → không fresh
                "id": "bad", "name": "Bad", "type": "dish",
                "confidence": 0.9, "updatedAt": _recent_date(),
            },
        ]}
        report = freshness.freshness_report(data)
        # fresh=1/total=2 → 50.0% — assert ĐÚNG con số, không chỉ literal "%".
        assert "Fresh:" in report
        assert "50.0%" in report


# ══════════════════════════════════════════════════
#  schedule_refresh — queue writer
# ══════════════════════════════════════════════════

class TestScheduleRefresh:
    @pytest.fixture(autouse=True)
    def _redirect_queue(self, tmp_path, monkeypatch):
        self.dir = tmp_path / "data"
        self.queue = self.dir / "refresh_queue.json"
        monkeypatch.setattr(freshness, "DATA_DIR", self.dir)
        monkeypatch.setattr(freshness, "REFRESH_QUEUE_FILE", self.queue)

    def test_writes_queue_file_and_counts(self):
        res = freshness.schedule_refresh(["a", "b", "c"])
        assert res["scheduled"] == 3
        assert res["queue_file"] == str(self.queue)
        assert self.queue.exists()
        data = json.loads(self.queue.read_text(encoding="utf-8"))
        assert {item["id"] for item in data["pending"]} == {"a", "b", "c"}
        assert all(item["status"] == "pending" for item in data["pending"])

    def test_dedup_against_existing_queue(self):
        freshness.schedule_refresh(["a", "b"])
        res = freshness.schedule_refresh(["b", "c", "d"])
        # only c and d are new
        assert res["scheduled"] == 2
        data = json.loads(self.queue.read_text(encoding="utf-8"))
        assert {item["id"] for item in data["pending"]} == {"a", "b", "c", "d"}

    def test_empty_list_schedules_nothing(self):
        res = freshness.schedule_refresh([])
        assert res["scheduled"] == 0
        # file is still created (queue seeded), with empty pending
        data = json.loads(self.queue.read_text(encoding="utf-8"))
        assert data["pending"] == []

    def test_timestamp_recorded(self):
        res = freshness.schedule_refresh(["a"])
        # timestamp parses as an ISO-ish datetime
        parsed = datetime.strptime(res["timestamp"], "%Y-%m-%dT%H:%M:%S")
        assert isinstance(parsed, datetime)
        data = json.loads(self.queue.read_text(encoding="utf-8"))
        assert data["last_updated"] == res["timestamp"]


# ══════════════════════════════════════════════════
#  main() — CLI dispatch
# ══════════════════════════════════════════════════

class TestMainCLI:
    @pytest.fixture
    def sample_stale_data(self):
        # stale via missing-date so check_freshness doesn't hit the naive/aware crash
        return {"entities": [{
            "id": "stale1", "name": "StaleOne", "type": "dish",
            "summary": "A sufficiently long summary that exceeds the min length.",
            "placeId": "w", "source": "manual", "confidence": 0.9,
        }]}

    def test_json_mode_prints_result(self, monkeypatch, capsys, sample_stale_data):
        monkeypatch.setattr(freshness, "_load_data", lambda: sample_stale_data)
        monkeypatch.setattr(sys, "argv", ["freshness.py", "--json"])
        freshness.main()
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert parsed["total"] == 1
        assert parsed["stale"] == 1
        assert "issues" in parsed

    def test_json_mode_respects_max_age(self, monkeypatch, capsys):
        # --max-age is parsed and threaded through to check_freshness. Use an
        # unparseable date so no stale reason fires and total/stale reflect that.
        data = {"entities": [{
            "id": "e", "name": "E", "type": "dish",
            "summary": "A sufficiently long summary that exceeds the min length.",
            "placeId": "w", "source": "manual", "confidence": 0.9,
            "updatedAt": "garbage",
        }]}
        captured = {}
        real = freshness.check_freshness

        def spy(entities, max_age_days=freshness.DEFAULT_MAX_AGE_DAYS):
            captured["max_age"] = max_age_days
            return real(entities, max_age_days=max_age_days)

        monkeypatch.setattr(freshness, "check_freshness", spy)
        monkeypatch.setattr(freshness, "_load_data", lambda: data)
        monkeypatch.setattr(sys, "argv", ["freshness.py", "--json", "--max-age", "365"])
        freshness.main()
        parsed = json.loads(capsys.readouterr().out)
        assert captured["max_age"] == 365  # CLI value reached the function
        assert parsed["stale"] == 0

    def test_report_mode_prints_report(self, monkeypatch, capsys, sample_stale_data):
        monkeypatch.setattr(freshness, "_load_data", lambda: sample_stale_data)
        monkeypatch.setattr(freshness, "_load_analytics", lambda: {"entity_hits": {}})
        monkeypatch.setattr(sys, "argv", ["freshness.py"])
        freshness.main()
        out = capsys.readouterr().out
        assert "CONTENT FRESHNESS REPORT" in out
        assert "STALE ENTITIES" in out

    def test_schedule_mode_calls_scheduler(self, monkeypatch, capsys, sample_stale_data):
        monkeypatch.setattr(freshness, "_load_data", lambda: sample_stale_data)
        monkeypatch.setattr(freshness, "_load_analytics", lambda: {"entity_hits": {}})
        captured = {}

        def fake_schedule(ids):
            captured["ids"] = ids
            return {"scheduled": len(ids), "queue_file": "Q", "timestamp": "T"}

        monkeypatch.setattr(freshness, "schedule_refresh", fake_schedule)
        monkeypatch.setattr(sys, "argv", ["freshness.py", "--schedule", "5"])
        freshness.main()
        out = capsys.readouterr().out
        # the stale entity's id must have flowed into the scheduler
        assert captured["ids"] == ["stale1"]
        assert "Scheduled 1 entities for refresh." in out
        assert "Queue file: Q" in out

    def test_schedule_mode_no_candidates(self, monkeypatch, capsys):
        # all fresh -> no candidates -> "No candidates to schedule."
        fresh_data = {"entities": [{
            "id": "ok", "name": "OK", "type": "dish",
            "summary": "A sufficiently long summary that exceeds the min length.",
            "placeId": "w", "source": "manual", "confidence": 0.9,
            "updatedAt": _recent_date(),
        }]}
        monkeypatch.setattr(freshness, "_load_data", lambda: fresh_data)
        monkeypatch.setattr(freshness, "_load_analytics", lambda: {"entity_hits": {}})

        def fail_schedule(ids):  # must never be called
            raise AssertionError("schedule_refresh should not run with no candidates")

        monkeypatch.setattr(freshness, "schedule_refresh", fail_schedule)
        monkeypatch.setattr(sys, "argv", ["freshness.py", "--schedule", "5"])
        freshness.main()
        out = capsys.readouterr().out
        assert "No candidates to schedule." in out
