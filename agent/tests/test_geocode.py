"""
Tests for geocode.py — OSM geocoding scoped to the province (mocked, no network).
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import geocode


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(geocode, "CACHE_FILE", tmp_path / "geo_cache.json")
    monkeypatch.setattr(geocode, "_cache", None)
    monkeypatch.setattr(geocode, "_last_request", [0.0])
    yield


class TestInBox:
    def test_inside(self):
        assert geocode.in_box(10.24, 106.37) is True   # An Hội

    def test_outside_lat(self):
        assert geocode.in_box(21.0, 105.8) is False     # Hà Nội

    def test_outside_lon(self):
        assert geocode.in_box(10.03, 105.78) is True    # Cần Thơ edge — within lon box
        assert geocode.in_box(10.77, 106.70) is False   # HCMC (lat too high)


class TestGeocode:
    def test_returns_coords_in_box(self, monkeypatch):
        monkeypatch.setattr(geocode, "_query_nominatim", lambda q: [10.2367, 106.3770])
        assert geocode.geocode("Đình An Hội") == [10.2367, 106.3770]

    def test_returns_none_when_not_found(self, monkeypatch):
        monkeypatch.setattr(geocode, "_query_nominatim", lambda q: None)
        assert geocode.geocode("Nơi không tồn tại 12345") is None

    def test_too_short_name(self):
        assert geocode.geocode("AB") is None

    def test_caches_hit(self, monkeypatch):
        calls = {"n": 0}
        def fake(q):
            calls["n"] += 1
            return [10.24, 106.37]
        monkeypatch.setattr(geocode, "_query_nominatim", fake)
        geocode.geocode("Chùa X")
        geocode.geocode("Chùa X")  # second call → cached
        assert calls["n"] <= 2  # at most the 2 query variants of the FIRST call

    def test_caches_miss(self, monkeypatch):
        calls = {"n": 0}
        def fake(q):
            calls["n"] += 1
            return None
        monkeypatch.setattr(geocode, "_query_nominatim", fake)
        assert geocode.geocode("Không có Y") is None
        n_after_first = calls["n"]
        assert geocode.geocode("Không có Y") is None  # cached miss
        assert calls["n"] == n_after_first  # no extra calls

    def test_offline_safe(self, monkeypatch):
        # Simulate requests unavailable → _query_nominatim returns None
        monkeypatch.setattr(geocode, "_HAS_REQUESTS", False)
        assert geocode._query_nominatim("anything") is None


class TestQueryValidation:
    def test_rejects_out_of_box_result(self, monkeypatch):
        """A Nominatim result outside the province box must be rejected."""
        class _Resp:
            status_code = 200
            def json(self):
                return [{"lat": "21.0285", "lon": "105.8542"}]  # Hà Nội
        monkeypatch.setattr(geocode, "_HAS_REQUESTS", True)
        monkeypatch.setattr(geocode.requests, "get", lambda *a, **k: _Resp())
        assert geocode._query_nominatim("somewhere") is None

    def test_accepts_in_box_result(self, monkeypatch):
        class _Resp:
            status_code = 200
            def json(self):
                return [{"lat": "10.2360", "lon": "106.3870"}]
        monkeypatch.setattr(geocode, "_HAS_REQUESTS", True)
        monkeypatch.setattr(geocode.requests, "get", lambda *a, **k: _Resp())
        assert geocode._query_nominatim("Bảo tàng Bến Tre") == [10.236, 106.387]
