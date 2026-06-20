"""
Unit tests for saved entities (favorites) — P1.

Fast (no full server import, no network). Verifies the router mounts, the
Postgres guard behaves, and the snapshot model trims correctly.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from database import db  # noqa: E402
import saved  # noqa: E402


def _client():
    app = FastAPI()
    app.include_router(saved.router)
    return TestClient(app)


def _route_pairs(app) -> set:
    pairs = set()
    for r in app.routes:
        for m in (getattr(r, "methods", None) or set()):
            pairs.add((m, r.path))
    return pairs


def test_saved_router_mounted():
    client = _client()
    pairs = _route_pairs(client.app)
    assert ("GET", "/api/saved") in pairs
    assert ("POST", "/api/saved") in pairs
    assert ("DELETE", "/api/saved/{entity_id}") in pairs
    assert ("POST", "/api/saved/merge") in pairs


def test_saved_pg_guard():
    client = _client()
    if not db._use_pg:
        # SQLite dev/CI: the PG guard short-circuits before auth → 503.
        assert client.get("/api/saved").status_code == 503
        assert client.post("/api/saved", json={"id": "x"}).status_code == 503
        assert client.delete("/api/saved/x").status_code == 503
        assert client.post("/api/saved/merge", json={"items": []}).status_code == 503
    else:
        # Postgres: endpoint exists and requires auth (not 404).
        assert client.get("/api/saved").status_code in (401, 403)


def test_saved_item_snapshot_trims_id_and_nones():
    item = saved.SavedItem(id="homestay-x", name="Homestay X", type="accommodation")
    snap = item.model_dump(exclude={"id"}, exclude_none=True)
    assert snap == {"name": "Homestay X", "type": "accommodation"}
    assert "id" not in snap
