"""Guard: toạ độ geocode NGOÀI bbox vùng phục vụ bị loại khi upsert (chống pin sai tỉnh).

Bbox mặc định = tỉnh Vĩnh Long mới; bản clone tỉnh khác đổi qua env REGION_BBOX.
Việc loại phải để lại WARNING (im lặng là lý do bug `ben-xe-mien-tay-hcm` sống lâu).
"""
import logging
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agent"))

import database
from database import Database, _coords_in_region, _parse_region_bbox, region_bbox

# Toạ độ thật của `ben-xe-mien-tay-hcm` trong web/data.json — ở TP.HCM, ngoài bbox VL.
HCM_COORDS = [10.7407, 106.6186]
# Bbox rộng đủ phủ cả VL lẫn TP.HCM (đại diện cho một bản clone tỉnh khác).
WIDE_BBOX = "9.2,11.5,105.6,107.2"


@pytest.fixture(autouse=True)
def _clean_region_env(monkeypatch):
    """Mỗi test bắt đầu từ trạng thái "không set env" + cache bbox rỗng."""
    monkeypatch.delenv("REGION_BBOX", raising=False)
    monkeypatch.setattr(database, "_REGION_BBOX_CACHE", None)


def _sqlite_db(tmp_path, monkeypatch, name="guard.db"):
    # `USE_PG`/`DATABASE_URL` là hằng module tính lúc import (database.py:37-38) và
    # __init__ đọc chúng → không ép thì tham số path bị bỏ qua và entity test được
    # GHI vào Postgres dùng chung của CI.
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(database, "USE_PG", False)
    monkeypatch.setattr(database, "DATABASE_URL", "")
    db = Database(str(tmp_path / name))
    assert db._use_pg is False and db._dsn is None
    return db


def test_region_predicate():
    assert _coords_in_region([10.0, 106.3]) is True    # Vĩnh Long
    assert _coords_in_region([9.8, 106.5]) is True      # Trà Vinh
    assert _coords_in_region([11.27, 106.51]) is False  # Bình Dương (bug gốc)
    assert _coords_in_region([10.4, 107.19]) is False   # Bà Rịa
    assert _coords_in_region(None) is False
    assert _coords_in_region([]) is False


def test_upsert_drops_out_of_region_coords(tmp_path, monkeypatch):
    db = _sqlite_db(tmp_path, monkeypatch)
    db.upsert_entity({"id": "bad", "type": "dish", "name": "X", "coordinates": [11.27, 106.51]})
    db.upsert_entity({"id": "good", "type": "dish", "name": "Y", "coordinates": [10.0, 106.3]})
    assert not db.get_entity("bad").get("coordinates")        # ngoài vùng -> loại
    assert db.get_entity("good").get("coordinates") == [10.0, 106.3]  # trong vùng -> giữ


# ── Mặc định (không set env) = hành vi cũ, không đổi ────────────────────────────

def test_default_bbox_unchanged_without_env():
    assert region_bbox() == (9.2, 10.65, 105.6, 106.95)


def test_default_bbox_drops_hcm_coords():
    """Bằng chứng gốc: entity `ben-xe-mien-tay-hcm` mất toạ độ vì ở TP.HCM."""
    assert _coords_in_region(HCM_COORDS) is False


# ── Cảnh báo: việc loại toạ độ KHÔNG còn im lặng ───────────────────────────────

def test_dropping_coords_logs_warning(tmp_path, monkeypatch, caplog):
    db = _sqlite_db(tmp_path, monkeypatch, "warn.db")
    with caplog.at_level(logging.WARNING, logger="database"):
        db.upsert_entity({
            "id": "ben-xe-mien-tay-hcm", "type": "place", "name": "Bến xe Miền Tây",
            "coordinates": HCM_COORDS,
        })
    warnings = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
    assert any("ben-xe-mien-tay-hcm" in m and "10.7407" in m for m in warnings), warnings
    assert any("REGION_BBOX" in m for m in warnings), warnings
    assert not db.get_entity("ben-xe-mien-tay-hcm").get("coordinates")


def test_kept_coords_log_nothing(tmp_path, monkeypatch, caplog):
    db = _sqlite_db(tmp_path, monkeypatch, "quiet.db")
    with caplog.at_level(logging.WARNING, logger="database"):
        db.upsert_entity({"id": "ok", "type": "dish", "name": "Y", "coordinates": [10.0, 106.3]})
    assert [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING] == []


# ── Tham số hoá qua env REGION_BBOX ────────────────────────────────────────────

def test_env_bbox_overrides_default(monkeypatch):
    monkeypatch.setenv("REGION_BBOX", WIDE_BBOX)
    assert region_bbox() == (9.2, 11.5, 105.6, 107.2)
    assert _coords_in_region(HCM_COORDS) is True       # trước bị loại, nay trong vùng
    assert _coords_in_region([10.0, 106.3]) is True    # Vĩnh Long vẫn trong vùng
    assert _coords_in_region([21.0, 105.8]) is False   # Hà Nội vẫn ngoài vùng


def test_env_bbox_keeps_previously_dropped_coords(tmp_path, monkeypatch):
    """Kịch bản clone tỉnh khác: cùng entity, cùng toạ độ — đổi env là giữ được pin."""
    monkeypatch.setenv("REGION_BBOX", WIDE_BBOX)
    db = _sqlite_db(tmp_path, monkeypatch, "wide.db")
    db.upsert_entity({
        "id": "ben-xe-mien-tay-hcm", "type": "place", "name": "Bến xe Miền Tây",
        "coordinates": HCM_COORDS,
    })
    assert db.get_entity("ben-xe-mien-tay-hcm").get("coordinates") == HCM_COORDS


def test_env_bbox_can_narrow_region(monkeypatch):
    monkeypatch.setenv("REGION_BBOX", "10.5,11.0,106.0,106.5")
    assert _coords_in_region([10.0, 106.3]) is False   # VL nay NGOÀI vùng đã siết
    assert _coords_in_region([10.7, 106.2]) is True


# ── Env sai định dạng: cảnh báo + fallback mặc định, không vỡ ──────────────────

@pytest.mark.parametrize("raw", [
    "not-a-bbox",
    "9.2,10.65,105.6",            # thiếu 1 số
    "9.2,10.65,105.6,106.95,1",   # thừa
    "10.65,9.2,105.6,106.95",     # lat_min > lat_max
    "9.2,10.65,106.95,105.6",     # lng_min > lng_max
    "-95,95,105.6,106.95",        # ngoài dải lat hợp lệ
    "9.2,10.65,-200,106.95",      # ngoài dải lng hợp lệ
    "",
])
def test_parse_region_bbox_rejects_bad_input(raw):
    assert _parse_region_bbox(raw) is None


def test_invalid_env_bbox_falls_back_to_default_with_warning(monkeypatch, caplog):
    monkeypatch.setenv("REGION_BBOX", "9.2;10.65;105.6;106.95")  # dấu ; thay vì ,
    with caplog.at_level(logging.WARNING, logger="database"):
        assert region_bbox() == (9.2, 10.65, 105.6, 106.95)
    assert any("REGION_BBOX" in r.getMessage() for r in caplog.records)
    assert _coords_in_region([10.0, 106.3]) is True     # vẫn chạy theo mặc định
    assert _coords_in_region(HCM_COORDS) is False


def test_blank_env_bbox_uses_default(monkeypatch):
    monkeypatch.setenv("REGION_BBOX", "   ")
    assert region_bbox() == (9.2, 10.65, 105.6, 106.95)


def test_env_change_takes_effect_without_reload(monkeypatch):
    """Cache theo chuỗi thô, không được khoá chết giá trị đọc lần đầu."""
    monkeypatch.setenv("REGION_BBOX", WIDE_BBOX)
    assert _coords_in_region(HCM_COORDS) is True
    monkeypatch.setenv("REGION_BBOX", "9.2,10.65,105.6,106.95")
    assert _coords_in_region(HCM_COORDS) is False
    monkeypatch.delenv("REGION_BBOX")
    assert region_bbox() == (9.2, 10.65, 105.6, 106.95)
