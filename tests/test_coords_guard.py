"""Guard: toạ độ geocode NGOÀI vùng 3 tỉnh bị loại khi upsert (chống pin sai tỉnh)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agent"))

from database import Database, _coords_in_region


def test_region_predicate():
    assert _coords_in_region([10.0, 106.3]) is True    # Vĩnh Long
    assert _coords_in_region([9.8, 106.5]) is True      # Trà Vinh
    assert _coords_in_region([11.27, 106.51]) is False  # Bình Dương (bug gốc)
    assert _coords_in_region([10.4, 107.19]) is False   # Bà Rịa
    assert _coords_in_region(None) is False
    assert _coords_in_region([]) is False


def test_upsert_drops_out_of_region_coords(tmp_path):
    db = Database(str(tmp_path / "guard.db"))
    db.upsert_entity({"id": "bad", "type": "dish", "name": "X", "coordinates": [11.27, 106.51]})
    db.upsert_entity({"id": "good", "type": "dish", "name": "Y", "coordinates": [10.0, 106.3]})
    assert not db.get_entity("bad").get("coordinates")        # ngoài vùng -> loại
    assert db.get_entity("good").get("coordinates") == [10.0, 106.3]  # trong vùng -> giữ
