# -*- coding: utf-8 -*-
"""Shape-contract cho response_model của visits.py (UGC PG-only → 503 ở SQLite).

Không gọi được endpoint thật (503 vì không có Postgres local) → thay bằng:
  1. model_validate mỗi payload KHỚP return-statement → no-strip + no-500.
  2. TestClient(router) gọi GET → 503 (SQLite) HOẶC 200, KHÔNG 500
     (response_model không phá path).
"""
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import visits  # noqa: E402
from api_schemas import ApiModel  # noqa: E402
from api_schemas_visits import (  # noqa: E402
    ReviewPromptsResponse,
    VisitCheckResponse,
    VisitListResponse,
    VisitStatsResponse,
)
from database import db  # noqa: E402


def _client():
    app = FastAPI()
    app.include_router(visits.router)
    return TestClient(app)


# ── 1. Mỗi GET endpoint có response_model kế ApiModel (extra=allow) ──────

def test_get_endpoints_have_apimodel_response_model():
    want = {
        "/api/me/visits": VisitListResponse,
        "/api/me/visits/check/{entity_id}": VisitCheckResponse,
        "/api/me/visits/review-prompts": ReviewPromptsResponse,
        "/api/me/visits/stats": VisitStatsResponse,
    }
    got = {}
    for r in visits.router.routes:
        methods = getattr(r, "methods", None) or set()
        if "GET" in methods:
            got[r.path] = getattr(r, "response_model", None)
    for path, model in want.items():
        rm = got.get(path)
        assert rm is not None, f"{path} thiếu response_model"
        assert rm is model, f"{path} sai model: {rm}"
        assert issubclass(rm, ApiModel), f"{path} phải kế ApiModel (extra=allow)"


# ── 2. Shape-contract: validate KHỚP return-statement, no-strip + no-500 ─

def test_visit_list_no_strip():
    # Return: {"visits": [{"entity_id","status"}, ...]}. Thêm field lạ trong
    # item + top-level để chứng minh pass-through (extra="allow").
    payload = {
        "visits": [
            {"entity_id": "cam-sanh", "status": "want", "surprise": 1},
            {"entity_id": "e2", "status": "visited"},
        ],
        "extra_top": "keep-me",
    }
    m = VisitListResponse.model_validate(payload)
    d = m.model_dump()
    assert d["visits"] == payload["visits"]  # item field không strip
    assert d["extra_top"] == "keep-me"       # top-level không khai vẫn còn


def test_visit_check_no_strip_both_branches():
    # Return: {"status": "want"|"visited"|None}.
    for val in ("want", "visited", None):
        m = VisitCheckResponse.model_validate({"status": val, "x": "keep"})
        d = m.model_dump()
        assert d["status"] == val
        assert d["x"] == "keep"


def test_review_prompts_no_strip():
    # Return: {"prompts": [row, ...]} — row = db._row_to_dict (shape tự do).
    payload = {
        "prompts": [
            {"entity_id": "e1", "visited_at": "t1", "extra": True},
            {"entity_id": "e2", "visited_at": "t2"},
        ],
    }
    m = ReviewPromptsResponse.model_validate(payload)
    d = m.model_dump()
    assert d["prompts"] == payload["prompts"]  # nested row không strip


def test_visit_stats_no_strip():
    # Return: {"total","visited","want": int, "by_type": dict}.
    payload = {
        "total": 5,
        "visited": 3,
        "want": 2,
        "by_type": {
            "attraction": {"visited": 2, "want": 1},
            "food": {"visited": 1, "want": 0},
        },
        "extra": "keep",
    }
    m = VisitStatsResponse.model_validate(payload)
    d = m.model_dump()
    assert d["total"] == 5
    assert d["visited"] == 3
    assert d["want"] == 2
    assert d["by_type"] == payload["by_type"]  # nested dict pass-through nguyên
    assert d["extra"] == "keep"


def test_visit_stats_defaults_row_missing():
    # td == {} → .get fallback 0 cho mọi count (khớp handler).
    m = VisitStatsResponse.model_validate({"total": 0, "visited": 0, "want": 0, "by_type": {}})
    d = m.model_dump()
    assert d == {"total": 0, "visited": 0, "want": 0, "by_type": {}}


# ── 3. 503-still-works: response_model không phá path 503 ────────────────

def test_get_endpoints_503_or_200_never_500():
    client = _client()
    paths = [
        "/api/me/visits",
        "/api/me/visits/check/cam-sanh",
        "/api/me/visits/review-prompts",
        "/api/me/visits/stats",
    ]
    for p in paths:
        code = client.get(p).status_code
        assert code != 500, f"{p} trả 500 — response_model phá path"
        if not db._use_pg:
            assert code == 503, f"{p} nên 503 ở SQLite (require_pg), got {code}"
