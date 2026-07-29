import math

import pytest

from itinerary_optimizer import (
    NoFeasibleRouteError,
    OptimizeOptions,
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


def test_exact_solver_restores_forward_order_and_preserves_endpoints():
    stops = [
        stop("start", 10.0, 106.0),
        stop("late", 10.0, 106.7),
        stop("early", 10.0, 106.3),
        stop("end", 10.0, 107.0),
    ]

    result = optimize_stop_order(stops)

    assert result.ordered_ids == ("start", "early", "late", "end")
    assert result.solver == "exact-dp"
    assert result.backtrack_ratio == pytest.approx(0.0, abs=1e-9)
    assert result.distance_after_km < result.distance_before_km


def test_blocked_edge_is_never_used():
    stops = [
        stop("start", 10.0, 106.0),
        stop("north", 10.03, 106.5),
        stop("south", 9.97, 106.5),
        stop("end", 10.0, 107.0),
    ]
    options = OptimizeOptions(
        blocked_edges=frozenset({("start", "north")}),
    )

    result = optimize_stop_order(stops, options)

    edges = set(zip(result.ordered_ids, result.ordered_ids[1:]))
    assert ("start", "north") not in edges
    assert result.ordered_ids[0] == "start"
    assert result.ordered_ids[-1] == "end"


def test_strict_solver_reports_no_route_instead_of_backtracking():
    stops = [
        stop("start", 10.0, 106.0),
        stop("middle", 10.0, 106.5),
        stop("end", 10.0, 107.0),
    ]
    options = OptimizeOptions(
        blocked_edges=frozenset({("start", "middle")}),
    )

    with pytest.raises(NoFeasibleRouteError, match="Không tìm thấy thứ tự"):
        optimize_stop_order(stops, options)


def test_duplicate_coordinates_keep_input_order():
    stops = [
        stop("start", 10.0, 106.0),
        stop("first", 10.0, 106.5),
        stop("second", 10.0, 106.5),
        stop("end", 10.0, 107.0),
    ]

    result = optimize_stop_order(stops)

    assert result.ordered_ids == ("start", "first", "second", "end")


def test_beam_solver_is_deterministic_for_twenty_stops():
    middle = [
        stop(
            f"p{i:02d}",
            10.0 + ((i % 3) - 1) * 0.002,
            106.0 + i * 0.04,
        )
        for i in range(1, 19)
    ]
    stops = [
        stop("start", 10.0, 106.0),
        *reversed(middle),
        stop("end", 10.0, 106.8),
    ]

    first = optimize_stop_order(stops)
    second = optimize_stop_order(stops)

    assert first.ordered_ids == second.ordered_ids
    assert first.solver == "beam-search"
    assert first.ordered_ids[0] == "start"
    assert first.ordered_ids[-1] == "end"
    assert first.backtrack_ratio == pytest.approx(0.0, abs=1e-9)
