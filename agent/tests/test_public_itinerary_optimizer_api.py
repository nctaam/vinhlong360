import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from public_api import router


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


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
