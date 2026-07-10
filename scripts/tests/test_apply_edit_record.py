# -*- coding: utf-8 -*-
"""Test apply_edit_record: field-set tin cậy + string-replace reference-validated (chống over-match)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apply_edit_record import (  # noqa: E402
    _reconcile, _walk_replace, apply_record,
)


class FakeDB:
    """DB giả dict-backed cho test (entities + itineraries)."""

    def __init__(self, entities, itineraries=None):
        self._e = {e["id"]: dict(e) for e in entities}
        self._i = {i["id"]: dict(i) for i in (itineraries or [])}

    def get_entity(self, eid):
        return dict(self._e[eid]) if eid in self._e else None

    def upsert_entity(self, e):
        self._e[e["id"]] = dict(e)

    def get_itinerary(self, iid):
        return dict(self._i[iid]) if iid in self._i else None

    def upsert_itinerary(self, i):
        self._i[i["id"]] = dict(i)

    def delete_entity(self, eid):
        return self._e.pop(eid, None) is not None

    def all_entities(self):
        return [dict(v) for v in self._e.values()]

    def all_itineraries(self):
        return [dict(v) for v in self._i.values()]


def test_walk_replace_recursive():
    obj = {"a": "miền Tây", "b": ["nắng gắt miền Tây", 3], "c": {"d": "khác"}}
    out, changed = _walk_replace(obj, [("miền Tây", "Vĩnh Long")])
    assert changed is True
    assert out["a"] == "Vĩnh Long"
    assert out["b"][0] == "nắng gắt Vĩnh Long" and out["b"][1] == 3
    assert out["c"]["d"] == "khác"


def test_reconcile_blocks_overmatch():
    """Bare 'miền Tây'→'Vĩnh Long' làm hỏng 'miền Tây Nam Bộ' → phải BỎ (giữ original)."""
    original = {"summary": "đặc trưng miền Tây Nam Bộ."}
    replaced = {"summary": "đặc trưng Vĩnh Long Nam Bộ."}
    ref = {"summary": "đặc trưng miền Tây Nam Bộ."}  # data.json GIỮ
    stats = {"str_skip_overmatch": 0}
    final, kept = _reconcile(original, replaced, ref, stats)
    assert kept == 0
    assert final["summary"] == "đặc trưng miền Tây Nam Bộ."  # giữ nguyên
    assert stats["str_skip_overmatch"] == 1


def test_reconcile_applies_when_matches_ref():
    original = {"summary": "nấu cơm miền Tây ngon"}
    replaced = {"summary": "nấu cơm Vĩnh Long ngon"}
    ref = {"summary": "nấu cơm Vĩnh Long ngon"}  # data.json đã đổi
    stats = {"str_skip_overmatch": 0}
    final, kept = _reconcile(original, replaced, ref, stats)
    assert kept == 1
    assert final["summary"] == "nấu cơm Vĩnh Long ngon"
    assert stats["str_skip_overmatch"] == 0


def test_apply_record_end_to_end():
    entities = [
        {"id": "e1", "summary": "cũ", "attributes": {}},                      # field-set
        {"id": "e2", "summary": "đặc trưng miền Tây Nam Bộ."},                 # over-match → giữ
        {"id": "e3", "summary": "nấu cơm miền Tây"},                          # string-replace hợp lệ
        {"id": "dup-x", "name": "dup"},                                       # coord delete
        {"id": "e4", "coordinates": None, "attributes": {}},                  # add_coords
    ]
    db = FakeDB(entities)
    record = {
        "top_level": [{"entity_id": "e1", "field": "summary", "new_text": "MỚI"}],
        "formula_R50.3": [],
        "nested": [{"old_string": "miền Tây", "new_string": "Vĩnh Long"}],  # bare (rủi ro)
        "content_surgical": [],
        "coord_fixes_R_deploygate": {
            "delete_entity": ["dup-x (duplicate)"],
            "set_coords_approximate_true": [],
            "add_coords": {"e4": [10.1, 106.0], "_note": "skip"},
        },
    }
    ref = {
        "e1": {"summary": "MỚI"},
        "e2": {"summary": "đặc trưng miền Tây Nam Bộ."},   # data.json GIỮ miền Tây
        "e3": {"summary": "nấu cơm Vĩnh Long"},            # data.json ĐÃ đổi
    }
    stats = apply_record(db, record, ref, execute=True)
    assert db.get_entity("e1")["summary"] == "MỚI"                              # field-set
    assert db.get_entity("e2")["summary"] == "đặc trưng miền Tây Nam Bộ."       # over-match chặn
    assert db.get_entity("e3")["summary"] == "nấu cơm Vĩnh Long"                # string-replace hợp lệ
    assert db.get_entity("dup-x") is None                                      # deleted
    assert db.get_entity("e4")["coordinates"] == [10.1, 106.0]                 # add_coords
    assert db.get_entity("e4")["attributes"]["coords_approximate"] is True
    assert stats["field_set"] == 1 and stats["coord"] == 2 and stats["str_skip_overmatch"] == 1
