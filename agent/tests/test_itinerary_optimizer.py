import math

import pytest

from itinerary_optimizer import (
    NoFeasibleRouteError,
    RouteStop,
    haversine_km,
    optimize_stop_order,
    project_onto_corridor,
)


def stop(stop_id: str, lat: float, lng: float) -> RouteStop:
    return RouteStop(stop_id, (lat, lng))


def test_projection_reports_station_and_lateral_distance():
    projection = project_onto_corridor(
        (10.0, 106.0),
        (10.0, 107.0),
        (10.1, 106.25),
    )

    assert projection.station == pytest.approx(0.25, abs=0.002)
    assert 11.0 < projection.lateral_km < 11.2


def test_haversine_is_zero_for_identical_coordinates():
    assert haversine_km((10.25, 105.97), (10.25, 105.97)) == 0.0


def test_optimizer_rejects_duplicate_ids():
    with pytest.raises(ValueError, match="không được trùng"):
        optimize_stop_order([
            stop("same", 10.0, 106.0),
            stop("same", 10.0, 106.5),
        ])


def test_optimizer_rejects_degenerate_corridor():
    with pytest.raises(NoFeasibleRouteError, match="không xác định được hướng"):
        optimize_stop_order([
            stop("start", 10.0, 106.0),
            stop("end", 10.00001, 106.00001),
        ])


@pytest.mark.parametrize(
    ("coordinates", "message"),
    [
        ((math.nan, 106.0), "hữu hạn"),
        ((91.0, 106.0), "Vĩ độ"),
        ((10.0, 181.0), "Kinh độ"),
    ],
)
def test_route_stop_rejects_invalid_coordinates(coordinates, message):
    with pytest.raises(ValueError, match=message):
        RouteStop("bad", coordinates)


def test_two_stop_route_returns_direct_diagnostics():
    result = optimize_stop_order([
        stop("start", 10.0, 106.0),
        stop("end", 10.0, 106.5),
    ])

    assert result.ordered_ids == ("start", "end")
    assert result.solver == "exact-dp"
    assert result.distance_before_km == pytest.approx(result.distance_after_km)
    assert result.backtrack_ratio == 0.0
