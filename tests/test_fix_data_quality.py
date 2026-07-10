"""Tests for scripts/fix_data_quality.py."""

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.fix_data_quality import (
    check_asymmetric_near,
    _rel_source,
    _rel_target,
    _rel_type,
)


class TestRelAccessors:
    def test_rel_source_from_field(self):
        assert _rel_source({"from": "e1"}) == "e1"

    def test_rel_source_source_id_field(self):
        assert _rel_source({"source_id": "e2"}) == "e2"

    def test_rel_source_missing(self):
        assert _rel_source({}) == ""

    def test_rel_target_to_field(self):
        assert _rel_target({"to": "e3"}) == "e3"

    def test_rel_target_target_id_field(self):
        assert _rel_target({"target_id": "e4"}) == "e4"

    def test_rel_type(self):
        assert _rel_type({"type": "near"}) == "near"

    def test_rel_type_missing(self):
        assert _rel_type({}) == ""


class TestCheckAsymmetricNear:
    def test_symmetric_pair_no_issues(self):
        entities = [{"id": "a"}, {"id": "b"}]
        rels = [
            {"from": "a", "to": "b", "type": "near"},
            {"from": "b", "to": "a", "type": "near"},
        ]
        issues, fixes = check_asymmetric_near(entities, rels)
        assert len(issues) == 0
        assert len(fixes) == 0

    def test_asymmetric_detected(self):
        entities = [{"id": "a"}, {"id": "b"}]
        rels = [
            {"from": "a", "to": "b", "type": "near"},
        ]
        issues, fixes = check_asymmetric_near(entities, rels)
        assert len(issues) == 1
        assert len(fixes) == 1

    def test_non_near_ignored(self):
        entities = [{"id": "a"}, {"id": "b"}]
        rels = [
            {"from": "a", "to": "b", "type": "located_in"},
        ]
        issues, fixes = check_asymmetric_near(entities, rels)
        assert len(issues) == 0

    def test_dangling_ref_skipped(self):
        entities = [{"id": "a"}]
        rels = [
            {"from": "a", "to": "nonexistent", "type": "near"},
        ]
        issues, fixes = check_asymmetric_near(entities, rels)
        assert len(fixes) == 0
