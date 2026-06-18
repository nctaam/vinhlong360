"""
Tests for kb_curation.py — quarantine review queue + auto-promotion.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import kb_curation


@pytest.fixture
def kb_with_provisional(tmp_path, monkeypatch):
    data = {
        "entities": [
            {"id": "verified-1", "name": "Cam sành", "type": "product", "confidence": 0.9, "verified": True},
            {"id": "prov-1", "name": "Quán mới X", "type": "dish", "confidence": 0.4,
             "status": "provisional", "verified": False, "summary": "auto-learned"},
            {"id": "prov-2", "name": "Điểm Y", "type": "attraction", "confidence": 0.4,
             "status": "provisional", "verified": False, "summary": "auto-learned"},
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

            r = kb_curation.promote("prov-1")
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
    def test_lists_only_provisional(self, kb_with_provisional):
        prov = kb_curation.list_provisional()
        ids = {p["id"] for p in prov}
        assert ids == {"prov-1", "prov-2"}


class TestPromote:
    def test_promote_sets_verified(self, kb_with_provisional):
        result = kb_curation.promote("prov-1")
        assert result["ok"] is True
        data = json.loads(kb_with_provisional.read_text(encoding="utf-8"))
        e = next(x for x in data["entities"] if x["id"] == "prov-1")
        assert e["verified"] is True
        assert e["status"] == "verified"

    def test_promote_already_verified(self, kb_with_provisional):
        result = kb_curation.promote("verified-1")
        assert result["ok"] is False

    def test_promote_not_found(self, kb_with_provisional):
        result = kb_curation.promote("nope")
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
