"""
Tests for geocode.py — OSM geocoding scoped to the province (mocked, no network).
"""

import ipaddress
import socket
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import geocode
import pinned_http as ph


PUBLIC_IP = "93.184.216.34"


def _public_address(port: int) -> ph.ResolvedAddress:
    return ph.ResolvedAddress(
        ip=ipaddress.ip_address(PUBLIC_IP),
        port=port,
        family=socket.AF_INET,
        socktype=socket.SOCK_STREAM,
        protocol=socket.IPPROTO_TCP,
        sockaddr=(PUBLIC_IP, port),
    )


def _pinned_response(content: bytes) -> ph.PinnedResponse:
    return ph.PinnedResponse(
        200,
        "https://nominatim.openstreetmap.org/search",
        (("content-type", "application/json; charset=utf-8"),),
        content,
        (),
    )


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
        monkeypatch.setattr(
            geocode._PINNED_HTTP,
            "get",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                ph.PinnedTransportError("offline")
            ),
        )
        assert geocode._query_nominatim("anything") is None


class TestQueryValidation:
    def test_rejects_out_of_box_result(self, monkeypatch):
        """A Nominatim result outside the province box must be rejected."""
        monkeypatch.setattr(
            geocode._PINNED_HTTP,
            "get",
            lambda *_args, **_kwargs: _pinned_response(
                b'[{"lat":"21.0285","lon":"105.8542"}]'
            ),
        )
        assert geocode._query_nominatim("somewhere") is None

    def test_accepts_in_box_result(self, monkeypatch):
        monkeypatch.setattr(
            geocode._PINNED_HTTP,
            "get",
            lambda *_args, **_kwargs: _pinned_response(
                b'[{"lat":"10.2360","lon":"106.3870"}]'
            ),
        )
        assert geocode._query_nominatim("Bảo tàng Bến Tre") == [10.236, 106.387]


class TestPinnedNominatimEgress:
    def test_query_uses_bounded_exact_origin_policy_and_encodes_parameters(
        self,
        monkeypatch,
    ):
        resolved = []
        requested = []
        policies = []

        def resolver(host, port, _budget):
            resolved.append((host, port))
            return (_public_address(port),)

        def handler(request):
            requested.append(request)
            return httpx.Response(
                200,
                headers={"content-type": "application/json; charset=utf-8"},
                content=b'[{"lat":"10.2360","lon":"106.3870"}]',
                request=request,
            )

        def transport_factory(_hop, policy, _budget):
            policies.append(policy)
            return httpx.MockTransport(handler)

        monkeypatch.setattr(
            geocode,
            "_PINNED_HTTP",
            ph.PinnedHTTPClient(
                resolver=resolver,
                transport_factory=transport_factory,
            ),
            raising=False,
        )

        assert geocode._query_nominatim("Bảo tàng Bến Tre") == [10.236, 106.387]
        assert resolved == [("nominatim.openstreetmap.org", 443)]
        assert len(requested) == 1
        assert str(requested[0].url) == (
            "https://nominatim.openstreetmap.org/search?format=jsonv2&"
            "q=B%E1%BA%A3o+t%C3%A0ng+B%E1%BA%BFn+Tre&limit=1&"
            "viewbox=105.7%2C10.55%2C106.85%2C9.4&bounded=1"
        )
        assert requested[0].headers["user-agent"] == geocode.USER_AGENT
        assert requested[0].headers["accept-encoding"] == "gzip, identity"
        assert policies == [
            ph.EgressPolicy(
                max_encoded_bytes=64 * 1024,
                max_decoded_bytes=256 * 1024,
                accepted_encodings=("gzip", "identity"),
                inactivity_timeout_seconds=15.0,
                total_timeout_seconds=15.0,
                max_redirects=2,
                allowed_origins=("https://nominatim.openstreetmap.org",),
            )
        ]

    def test_off_origin_redirect_is_blocked_before_second_resolution_or_dial(
        self,
        monkeypatch,
        caplog,
    ):
        resolved = []
        requested = []

        def resolver(host, port, _budget):
            resolved.append((host, port))
            return (_public_address(port),)

        def handler(request):
            requested.append(request.url)
            return httpx.Response(
                302,
                headers={"location": "https://evil.example/collect"},
                request=request,
            )

        monkeypatch.setattr(
            geocode,
            "_PINNED_HTTP",
            ph.PinnedHTTPClient(
                resolver=resolver,
                transport_factory=lambda _hop, _policy, _budget: httpx.MockTransport(handler),
            ),
            raising=False,
        )

        with caplog.at_level("WARNING", logger="security.egress"):
            assert geocode._query_nominatim("somewhere") is None

        assert resolved == [("nominatim.openstreetmap.org", 443)]
        assert [url.host for url in requested] == ["nominatim.openstreetmap.org"]
        records = [record for record in caplog.records if record.name == "security.egress"]
        assert len(records) == 1
        assert records[0].getMessage() == (
            "Pinned egress denied consumer=geocode reason=redirect_policy "
            "target=https://nominatim.openstreetmap.org:443 hop=0"
        )
