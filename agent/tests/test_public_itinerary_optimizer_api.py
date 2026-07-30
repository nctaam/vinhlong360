import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import public_api
from public_api import router


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture
def non_raising_client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app, raise_server_exceptions=False)


def payload():
    return {
        "stops": [
            {"id": "start", "coordinates": [10.0, 106.0]},
            {"id": "late", "coordinates": [10.0, 106.7]},
            {"id": "early", "coordinates": [10.0, 106.3]},
            {"id": "end", "coordinates": [10.0, 107.0]},
        ],
        "strict_direction": True,
        "blocked_edges": [],
    }


def schedule_payload():
    body = payload()
    body["schedule"] = {
        "day_start_minute": 480,
        "day_end_minute": 1080,
        "mode": "driving",
        "stops": [
            {"id": "start", "visit_minutes": 0, "required": True},
            {
                "id": "late",
                "visit_minutes": 30,
                "opening_hours": "10:00-17:00",
                "required": True,
            },
            {
                "id": "early",
                "visit_minutes": 30,
                "opening_hours": "08:00-09:30",
                "required": True,
            },
            {"id": "end", "visit_minutes": 0, "required": True},
        ],
        "duration_matrix_minutes": [
            [0, 20, 10, 40],
            [20, 0, 20, 20],
            [10, 20, 0, 30],
            [40, 20, 30, 0],
        ],
    }
    return body


def basic_schedule(**overrides):
    schedule = {
        "day_start_minute": 480,
        "day_end_minute": 1080,
        "stops": [
            {"id": "start"},
            {"id": "late"},
            {"id": "early"},
            {"id": "end"},
        ],
    }
    schedule.update(overrides)
    return schedule


def matrix_with_cell(row_index, column_index, value):
    matrix = [
        [0 if row == column else 1 for column in range(4)]
        for row in range(4)
    ]
    matrix[row_index][column_index] = value
    return matrix


def capture_route_optimizer_calls(monkeypatch):
    calls = []
    original_optimize = public_api.optimize_stop_order

    def track_optimize(stops, options):
        calls.append((stops, options))
        return original_optimize(stops, options)

    monkeypatch.setattr(public_api, "optimize_stop_order", track_optimize)
    return calls


def assert_order_only_fallback(response, route_calls):
    assert response.status_code == 200
    assert len(route_calls) == 1
    body = response.json()
    assert "schedule" not in body
    assert set(body) == {
        "ordered_ids",
        "distance_before_km",
        "distance_after_km",
        "saved_distance_km",
        "backtrack_ratio",
        "solver",
        "warnings",
    }
    assert body["ordered_ids"] == ["start", "early", "late", "end"]
    assert body["solver"] == "exact-dp"
    assert body["saved_distance_km"] > 0
    assert body["warnings"] == ["schedule-fallback-order-only"]


def test_optimize_order_returns_forward_order_and_diagnostics(client):
    response = client.post("/api/itineraries/optimize-order", json=payload())

    assert response.status_code == 200
    body = response.json()
    assert body["ordered_ids"] == ["start", "early", "late", "end"]
    assert body["solver"] == "exact-dp"
    assert body["backtrack_ratio"] == pytest.approx(0.0, abs=1e-9)
    assert body["saved_distance_km"] > 0
    assert body["warnings"] == []


@pytest.mark.parametrize(
    "stops",
    [
        [{"id": "only", "coordinates": [10.0, 106.0]}],
        [
            {"id": f"stop-{index}", "coordinates": [10.0, 106.0 + index * 0.01]}
            for index in range(21)
        ],
    ],
)
def test_optimize_order_rejects_stop_count_outside_bounds(client, stops):
    body = payload()
    body["stops"] = stops

    response = client.post("/api/itineraries/optimize-order", json=body)

    assert response.status_code == 422


def test_optimize_order_rejects_duplicate_ids(client):
    body = payload()
    body["stops"].append(body["stops"][0])

    response = client.post("/api/itineraries/optimize-order", json=body)

    assert response.status_code == 422


@pytest.mark.parametrize(
    "coordinates",
    [
        [91.0, 106.0],
        [10.0, 181.0],
    ],
)
def test_optimize_order_rejects_out_of_range_coordinates(client, coordinates):
    body = payload()
    body["stops"][1]["coordinates"] = coordinates

    response = client.post("/api/itineraries/optimize-order", json=body)

    assert response.status_code == 422


def test_optimize_order_rejects_unknown_blocked_edge(client):
    body = payload()
    body["blocked_edges"] = [["missing", "end"]]

    response = client.post("/api/itineraries/optimize-order", json=body)

    assert response.status_code == 422


def test_optimize_order_maps_no_route_to_409(client):
    body = payload()
    body["blocked_edges"] = [["start", "early"]]

    response = client.post("/api/itineraries/optimize-order", json=body)

    assert response.status_code == 409
    assert "Không tìm thấy thứ tự" in response.json()["detail"]


def test_schedule_envelope_returns_placements_and_uses_request_matrix(client):
    response = client.post("/api/itineraries/optimize-order", json=schedule_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["ordered_ids"] == ["start", "early", "late", "end"]
    assert body["solver"] == "schedule-exact"
    assert body["distance_after_km"] < body["distance_before_km"]
    assert body["schedule"]["matrix_source"] == "request"
    assert body["schedule"]["placements"][1] == {
        "stop_id": "early",
        "arrival_minute": 490.0,
        "start_visit_minute": 490.0,
        "end_visit_minute": 520.0,
    }
    assert "finish_visit_minute" not in body["schedule"]["placements"][1]
    assert body["schedule"]["total_travel_minutes"] == 50.0
    assert body["schedule"]["waiting_minutes"] == 60.0
    assert body["schedule"]["overtime_minutes"] == 0.0


def test_without_schedule_keeps_existing_response_and_call_path(client, monkeypatch):
    optimize_calls = []
    original_optimize = public_api.optimize_stop_order

    def track_optimize(stops, options):
        optimize_calls.append((stops, options))
        return original_optimize(stops, options)

    def fail_schedule_path(*args, **kwargs):
        raise AssertionError("order-only request entered the scheduling path")

    monkeypatch.setattr(public_api, "optimize_stop_order", track_optimize)
    monkeypatch.setattr(
        public_api,
        "schedule_stop_order",
        fail_schedule_path,
        raising=False,
    )
    monkeypatch.setattr(
        public_api,
        "build_fallback_matrix",
        fail_schedule_path,
        raising=False,
    )

    response = client.post("/api/itineraries/optimize-order", json=payload())

    assert response.status_code == 200
    assert len(optimize_calls) == 1
    assert set(response.json()) == {
        "ordered_ids",
        "distance_before_km",
        "distance_after_km",
        "saved_distance_km",
        "backtrack_ratio",
        "solver",
        "warnings",
    }


@pytest.mark.parametrize(
    "bad_schedule",
    [
        basic_schedule(day_start_minute=900, day_end_minute=480),
        basic_schedule(stops=basic_schedule()["stops"][:-1]),
        basic_schedule(
            stops=[
                {"id": "start"},
                {"id": "missing"},
                {"id": "early"},
                {"id": "end"},
            ]
        ),
        basic_schedule(
            stops=[
                {"id": "start", "required": False},
                {"id": "late"},
                {"id": "early"},
                {"id": "end"},
            ]
        ),
        basic_schedule(
            stops=[
                {"id": "start"},
                {"id": "late"},
                {"id": "early"},
                {"id": "end", "required": False},
            ]
        ),
        basic_schedule(duration_matrix_minutes=[[0, 1]]),
        basic_schedule(duration_matrix_minutes=matrix_with_cell(0, 1, -1)),
        basic_schedule(duration_matrix_minutes=matrix_with_cell(0, 0, None)),
    ],
)
def test_schedule_validation_returns_422(client, bad_schedule):
    body = payload()
    body["schedule"] = bad_schedule

    response = client.post("/api/itineraries/optimize-order", json=body)

    assert response.status_code == 422


@pytest.mark.parametrize(
    "swap_indices",
    [(0, 1), (-1, -2)],
    ids=["swapped-start", "swapped-end"],
)
def test_schedule_rejects_endpoint_ids_that_differ_from_outer_stops(
    client,
    swap_indices,
):
    body = schedule_payload()
    source, target = swap_indices
    schedule_stops = body["schedule"]["stops"]
    schedule_stops[source], schedule_stops[target] = (
        schedule_stops[target],
        schedule_stops[source],
    )

    response = client.post("/api/itineraries/optimize-order", json=body)

    assert response.status_code == 422


def test_schedule_matrix_allows_null_for_an_unavailable_edge(client):
    body = schedule_payload()
    body["schedule"]["duration_matrix_minutes"][0][2] = None

    response = client.post("/api/itineraries/optimize-order", json=body)

    assert response.status_code == 409
    assert "early" in response.json()["detail"]


def test_invalid_requested_time_returns_422(client):
    body = schedule_payload()
    body["schedule"]["stops"][2]["requested_time"] = "khoảng chín giờ"

    response = client.post("/api/itineraries/optimize-order", json=body)

    assert response.status_code == 422


def test_requested_time_without_opening_hours_is_a_hard_window(client):
    body = schedule_payload()
    early = body["schedule"]["stops"][2]
    early.pop("opening_hours")
    early["requested_time"] = "09:00-09:30"

    response = client.post("/api/itineraries/optimize-order", json=body)

    assert response.status_code == 200
    early_placement = response.json()["schedule"]["placements"][1]
    assert early_placement["start_visit_minute"] == 540.0
    assert early_placement["end_visit_minute"] == 570.0


def test_requested_time_intersects_opening_hours_windows(client):
    body = schedule_payload()
    early = body["schedule"]["stops"][2]
    early["visit_minutes"] = 45
    early["opening_hours"] = "08:00-09:30"
    early["requested_time"] = "09:00-10:00"

    response = client.post("/api/itineraries/optimize-order", json=body)

    assert response.status_code == 409
    assert "early" in response.json()["detail"]
    assert "schedule" not in response.json()


def test_schedule_maps_outer_coordinates_and_uses_schedule_id_matrix_order(
    client,
    monkeypatch,
):
    body = schedule_payload()
    body["schedule"]["stops"] = [
        body["schedule"]["stops"][0],
        body["schedule"]["stops"][2],
        body["schedule"]["stops"][1],
        body["schedule"]["stops"][3],
    ]
    body["schedule"]["duration_matrix_minutes"] = [
        [0, 10, 20, 40],
        [10, 0, 20, 30],
        [20, 20, 0, 20],
        [40, 30, 20, 0],
    ]
    captured = {}
    original_schedule = getattr(public_api, "schedule_stop_order", None)

    def track_schedule(stops, matrix, options):
        captured["stops"] = stops
        captured["matrix"] = matrix
        return original_schedule(stops, matrix, options)

    monkeypatch.setattr(
        public_api,
        "schedule_stop_order",
        track_schedule,
        raising=False,
    )

    response = client.post("/api/itineraries/optimize-order", json=body)

    assert response.status_code == 200
    assert captured["matrix"].stop_ids == ("start", "early", "late", "end")
    assert {
        stop.id: stop.coordinates for stop in captured["stops"]
    } == {
        "start": (10.0, 106.0),
        "late": (10.0, 106.7),
        "early": (10.0, 106.3),
        "end": (10.0, 107.0),
    }


def test_schedule_without_matrix_uses_local_fallback_for_selected_mode(
    client,
    monkeypatch,
):
    body = schedule_payload()
    body["schedule"].pop("duration_matrix_minutes")
    body["schedule"]["mode"] = "cycling"
    body["schedule"]["day_end_minute"] = 1440
    for stop in body["schedule"]["stops"]:
        stop.pop("opening_hours", None)
        stop["visit_minutes"] = 0
    captured_modes = []
    original_builder = getattr(public_api, "build_fallback_matrix", None)

    def track_fallback(stops, mode):
        captured_modes.append(mode)
        return original_builder(stops, mode)

    monkeypatch.setattr(
        public_api,
        "build_fallback_matrix",
        track_fallback,
        raising=False,
    )

    response = client.post("/api/itineraries/optimize-order", json=body)

    assert response.status_code == 200
    assert captured_modes == ["cycling"]
    assert response.json()["schedule"]["matrix_source"] == "haversine-fallback"


def test_no_feasible_schedule_maps_to_409_without_partial_placements(client):
    body = schedule_payload()
    early = body["schedule"]["stops"][2]
    early["visit_minutes"] = 90
    early["opening_hours"] = "08:00-08:30"

    response = client.post("/api/itineraries/optimize-order", json=body)

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Không tìm thấy lịch trình khả thi; điểm chặn đầu tiên: early"
    }


def test_matrix_builder_runtime_failure_falls_back_to_order_only(
    non_raising_client,
    monkeypatch,
    caplog,
):
    body = schedule_payload()
    body["schedule"].pop("duration_matrix_minutes")
    route_calls = capture_route_optimizer_calls(monkeypatch)

    def fail_matrix(*args, **kwargs):
        raise RuntimeError("matrix builder exploded")

    monkeypatch.setattr(
        public_api,
        "build_fallback_matrix",
        fail_matrix,
    )

    with caplog.at_level("ERROR", logger=public_api.logger.name):
        response = non_raising_client.post(
            "/api/itineraries/optimize-order",
            json=body,
        )

    assert_order_only_fallback(response, route_calls)
    assert any(
        record.name == public_api.logger.name and record.exc_info
        for record in caplog.records
    )


def test_scheduler_runtime_failure_falls_back_to_order_only(
    non_raising_client,
    monkeypatch,
    caplog,
):
    route_calls = capture_route_optimizer_calls(monkeypatch)

    def fail_schedule(*args, **kwargs):
        raise RuntimeError("scheduler exploded")

    monkeypatch.setattr(public_api, "schedule_stop_order", fail_schedule)

    with caplog.at_level("ERROR", logger=public_api.logger.name):
        response = non_raising_client.post(
            "/api/itineraries/optimize-order",
            json=schedule_payload(),
        )

    assert_order_only_fallback(response, route_calls)
    assert any(
        record.name == public_api.logger.name and record.exc_info
        for record in caplog.records
    )


def test_schedule_fallback_preserves_legacy_no_route_409(
    non_raising_client,
    monkeypatch,
):
    body = schedule_payload()
    body["blocked_edges"] = [["start", "early"]]
    route_calls = capture_route_optimizer_calls(monkeypatch)

    def fail_schedule(*args, **kwargs):
        raise RuntimeError("scheduler exploded")

    monkeypatch.setattr(public_api, "schedule_stop_order", fail_schedule)

    response = non_raising_client.post(
        "/api/itineraries/optimize-order",
        json=body,
    )

    assert response.status_code == 409
    assert len(route_calls) == 1
    assert "Không tìm thấy thứ tự" in response.json()["detail"]
    assert "schedule" not in response.json()


def test_optional_schedule_stop_is_skipped_with_a_reason(client):
    body = payload()
    body["schedule"] = {
        "day_start_minute": 480,
        "day_end_minute": 780,
        "mode": "driving",
        "stops": [
            {"id": "start", "visit_minutes": 0},
            {"id": "late", "visit_minutes": 250},
            {"id": "early", "visit_minutes": 250, "required": False},
            {"id": "end", "visit_minutes": 0},
        ],
        "duration_matrix_minutes": [
            [0, 1, 1, 1],
            [1, 0, 1, 1],
            [1, 1, 0, 1],
            [1, 1, 1, 0],
        ],
    }

    response = client.post("/api/itineraries/optimize-order", json=body)

    assert response.status_code == 200
    assert response.json()["ordered_ids"] == ["start", "late", "end"]
    assert response.json()["schedule"]["skipped"] == [
        {"stop_id": "early", "reason": "day-window-overflow"}
    ]
