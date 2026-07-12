"""
Tests for kb_curation.py — quarantine review queue + auto-promotion.
"""

import json
import re
import sys
import threading
from copy import deepcopy
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import kb_curation


@pytest.fixture
def kb_with_provisional(tmp_path, monkeypatch):
    long_summary = "Chi tiết biên tập cần được đọc đầy đủ trước khi duyệt. " * 4
    data = {
        "entities": [
            {"id": "verified-1", "name": "Cam sành", "type": "product", "confidence": 0.9, "verified": True},
            {
                "id": "prov-1",
                "name": "Quán mới X",
                "type": "dish",
                "confidence": 0.4,
                "status": "provisional",
                "verified": False,
                "summary": long_summary,
                "source": {"name": "Danh bạ đối tác", "url": "https://example.test/source"},
                "coordinates": {"lat": 10.253, "lng": 106.012},
                "coords": [10.253, 106.012],
                "images": ["https://example.test/image-1.webp", "https://example.test/image-2.webp"],
                "attributes": {
                    "phone": "0900000000",
                    "address": "12 đường Thử Nghiệm",
                    "contact": {"zalo": "0900000000"},
                },
                "address": "12 đường Thử Nghiệm, Vĩnh Long",
                "area": "vinh-long",
                "placeId": "phuong-thanh-duc",
                "provider_trace_id": "partner-feed:uncommon:42",
            },
            {"id": "prov-2", "name": "Điểm Y", "type": "attraction", "confidence": 0.4,
             "status": "provisional", "verified": False, "summary": "auto-learned",
             "source": {"provider": "crawler", "fetched_at": "2026-07-12"}},
        ],
        "relationships": [{"from": "prov-1", "to": "verified-1", "type": "near"}],
        "itineraries": [],
    }
    data_json = tmp_path / "data.json"
    data_json.write_text(json.dumps(data), encoding="utf-8")
    analytics = tmp_path / "analytics.json"
    analytics.write_text(json.dumps({"entity_hits": {"prov-1": 5, "prov-2": 1}}), encoding="utf-8")

    monkeypatch.setattr(kb_curation, "DATA_JSON", data_json)
    monkeypatch.setattr(kb_curation, "ANALYTICS_FILE", analytics)
    monkeypatch.setattr(kb_curation, "_reload", lambda: None)
    return data_json


class TestDbWriteThrough:
    """GĐ-audit B1: promote/reject phải ghi DB (chat đọc DB) — không chỉ data.json."""

    def test_promote_and_reject_hit_db(self, kb_with_provisional):
        from database import db
        db.initialize()
        ids = ["prov-1", "prov-2"]
        try:
            db.upsert_entity({"id": "prov-1", "name": "Quán mới X", "type": "dish",
                              "status": "provisional", "verified": False})
            db.upsert_entity({"id": "prov-2", "name": "Điểm Y", "type": "attraction",
                              "status": "provisional", "verified": False})

            review = next(x for x in kb_curation.list_provisional() if x["id"] == "prov-1")
            r = kb_curation.promote("prov-1", review["review_token"])
            assert r["ok"] is True
            got = db.get_entity("prov-1")
            assert got is not None

            # reject: entity bị xoá khỏi DB (trước fix B1, reject chỉ sửa data.json → chat vẫn thấy)
            r2 = kb_curation.reject("prov-2")
            assert r2["ok"] is True
            assert db.get_entity("prov-2") is None
        finally:
            for i in ids:
                db.delete_entity(i)


class TestListProvisional:
    def test_lists_complete_review_snapshots(self, kb_with_provisional):
        source = json.loads(kb_with_provisional.read_text(encoding="utf-8"))
        prov = kb_curation.list_provisional()
        ids = {p["id"] for p in prov}
        assert ids == {"prov-1", "prov-2"}

        for item in prov:
            original = next(e for e in source["entities"] if e["id"] == item["id"])
            expected_snapshot = {k: deepcopy(v) for k, v in original.items() if k not in {"status", "verified"}}
            assert set(item) == {"id", "review_token", "entity"}
            assert re.fullmatch(r"[0-9a-f]{64}", item["review_token"])
            assert item["entity"] == expected_snapshot

        complete = next(item["entity"] for item in prov if item["id"] == "prov-1")
        assert len(complete["summary"]) > 160
        assert complete["provider_trace_id"] == "partner-feed:uncommon:42"


class TestPromote:
    def test_promote_with_current_token_preserves_snapshot(self, kb_with_provisional, monkeypatch):
        before = json.loads(kb_with_provisional.read_text(encoding="utf-8"))
        original = next(x for x in before["entities"] if x["id"] == "prov-1")
        review = next(x for x in kb_curation.list_provisional() if x["id"] == "prov-1")
        upserted = []
        monkeypatch.setattr(kb_curation, "_db_upsert", lambda entity: upserted.append(deepcopy(entity)))

        result = kb_curation.promote("prov-1", review["review_token"])
        assert result["ok"] is True
        data = json.loads(kb_with_provisional.read_text(encoding="utf-8"))
        e = next(x for x in data["entities"] if x["id"] == "prov-1")
        assert e["verified"] is True
        assert e["status"] == "verified"
        assert {k: v for k, v in e.items() if k not in {"status", "verified"}} == {
            k: v for k, v in original.items() if k not in {"status", "verified"}
        }
        assert upserted == [e]

    def test_stale_review_token_fails_before_mutation(self, kb_with_provisional, monkeypatch):
        review = next(x for x in kb_curation.list_provisional() if x["id"] == "prov-1")
        changed = json.loads(kb_with_provisional.read_text(encoding="utf-8"))
        entity = next(x for x in changed["entities"] if x["id"] == "prov-1")
        entity["attributes"]["phone"] = "0911111111"
        kb_with_provisional.write_text(json.dumps(changed, ensure_ascii=False), encoding="utf-8")

        def fail_mutation(*_args, **_kwargs):
            pytest.fail("stale approval attempted a mutation")

        monkeypatch.setattr(kb_curation, "compare_and_swap_json", fail_mutation)
        monkeypatch.setattr(kb_curation, "_db_upsert", fail_mutation)
        monkeypatch.setattr(kb_curation, "_reload", fail_mutation)

        result = kb_curation.promote("prov-1", review["review_token"])

        assert result == {"ok": False, "error": "stale_review"}
        persisted = json.loads(kb_with_provisional.read_text(encoding="utf-8"))
        persisted_entity = next(x for x in persisted["entities"] if x["id"] == "prov-1")
        assert persisted_entity["status"] == "provisional"
        assert persisted_entity["verified"] is False

    def test_hidden_update_after_token_check_is_not_overwritten(self, kb_with_provisional, monkeypatch):
        review = next(x for x in kb_curation.list_provisional() if x["id"] == "prov-1")
        token_checked = threading.Event()
        writer_done = threading.Event()
        original_review_token = kb_curation._review_token
        result = {}

        def pause_after_token_check(snapshot):
            token = original_review_token(snapshot)
            if threading.current_thread().name == "manual-promote":
                token_checked.set()
                assert writer_done.wait(timeout=5)
            return token

        monkeypatch.setattr(kb_curation, "_review_token", pause_after_token_check)

        def run_promote():
            result.update(kb_curation.promote("prov-1", review["review_token"]))

        promote_thread = threading.Thread(target=run_promote, name="manual-promote")
        promote_thread.start()
        assert token_checked.wait(timeout=5)

        changed = json.loads(kb_with_provisional.read_text(encoding="utf-8"))
        entity = next(x for x in changed["entities"] if x["id"] == "prov-1")
        entity["attributes"]["phone"] = "0922222222"
        kb_with_provisional.write_text(json.dumps(changed, ensure_ascii=False), encoding="utf-8")
        writer_done.set()
        promote_thread.join(timeout=5)

        assert not promote_thread.is_alive()
        assert result == {"ok": False, "error": "stale_review"}
        persisted = json.loads(kb_with_provisional.read_text(encoding="utf-8"))
        persisted_entity = next(x for x in persisted["entities"] if x["id"] == "prov-1")
        assert persisted_entity["attributes"]["phone"] == "0922222222"
        assert persisted_entity["status"] == "provisional"
        assert persisted_entity["verified"] is False

    def test_promote_already_verified(self, kb_with_provisional):
        result = kb_curation.promote("verified-1", "0" * 64)
        assert result["ok"] is False

    def test_promote_not_found(self, kb_with_provisional):
        result = kb_curation.promote("nope", "0" * 64)
        assert result["ok"] is False


class TestReject:
    def test_reject_removes_entity(self, kb_with_provisional):
        result = kb_curation.reject("prov-1")
        assert result["ok"] is True
        data = json.loads(kb_with_provisional.read_text(encoding="utf-8"))
        ids = {e["id"] for e in data["entities"]}
        assert "prov-1" not in ids
        # Relationship referencing it also dropped
        assert all(r["from"] != "prov-1" and r["to"] != "prov-1" for r in data["relationships"])

    def test_reject_refuses_verified(self, kb_with_provisional):
        result = kb_curation.reject("verified-1")
        assert result["ok"] is False


class TestNearDuplicate:
    """Contradiction / near-duplicate detection before KB write."""

    ENTITIES = [
        {"id": "cho-noi-tra-on", "name": "Khu du lịch Chợ nổi Trà Ôn", "type": "attraction"},
        {"id": "cam-sanh-tra-on", "name": "Cam sành Trà Ôn", "type": "product"},
    ]

    def test_detects_near_duplicate_same_type(self):
        # "Chợ nổi Trà Ôn" shares significant tokens with existing attraction
        dup = kb_curation.find_near_duplicate("Chợ nổi Trà Ôn", "attraction", self.ENTITIES)
        assert dup == "cho-noi-tra-on"

    def test_novel_entity_not_flagged(self):
        dup = kb_curation.find_near_duplicate("Bún nước lèo Cầu Kè", "dish", self.ENTITIES)
        assert dup is None

    def test_different_type_not_flagged(self):
        # Same name tokens but different type → not a duplicate
        dup = kb_curation.find_near_duplicate("Chợ nổi Trà Ôn", "dish", self.ENTITIES)
        assert dup is None

    def test_cross_site_type_containment_flagged(self):
        """Same physical place filed under a different site-type must be caught
        (the Văn Thánh Miếu attraction-vs-history case)."""
        entities = [{"id": "van-thanh-mieu", "name": "Văn Thánh Miếu", "type": "attraction"}]
        dup = kb_curation.find_near_duplicate("Văn Thánh Miếu Vĩnh Long", "history", entities)
        assert dup == "van-thanh-mieu"

    def test_cross_site_type_distinct_places_not_flagged(self):
        """Distinct places sharing words must NOT be cross-flagged."""
        entities = [{"id": "chua-ba-thien-hau-tra-vinh", "name": "Chùa Bà Thiên Hậu Trà Vinh", "type": "attraction"}]
        dup = kb_curation.find_near_duplicate("Thiên Hậu Cung", "history", entities)
        assert dup is None

    def test_cross_type_person_vs_site_not_flagged(self):
        """A memorial SITE named after a person is distinct from the person."""
        entities = [{"id": "nguyen-dinh-chieu", "name": "Nguyễn Đình Chiểu", "type": "person"}]
        dup = kb_curation.find_near_duplicate("Khu di tích Nguyễn Đình Chiểu", "history", entities)
        assert dup is None  # person is not a site-type → no cross check


class TestAutoPromote:
    def test_promotes_useful_entities(self, kb_with_provisional):
        # prov-1 has 5 hits (>= 3), prov-2 has 1 (< 3)
        result = kb_curation.auto_promote_pass(min_hits=3)
        assert "prov-1" in result["promoted"]
        assert "prov-2" not in result["promoted"]

    def test_dry_run_no_changes(self, kb_with_provisional):
        result = kb_curation.auto_promote_pass(min_hits=3, dry_run=True)
        assert "prov-1" in result["promoted"]
        # But not persisted
        data = json.loads(kb_with_provisional.read_text(encoding="utf-8"))
        e = next(x for x in data["entities"] if x["id"] == "prov-1")
        assert e["verified"] is False  # unchanged
