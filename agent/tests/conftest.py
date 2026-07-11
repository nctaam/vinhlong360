"""
Shared fixtures for vinhlong360 agent tests.
"""

import json
import os
import sys
from pathlib import Path

import pytest

# Ensure agent/ is on sys.path
AGENT_DIR = Path(__file__).resolve().parent.parent
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

# Set test environment
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key-12345")


# ── Router route-list guard (test-isolation) ──────────────────────────────
# Các test *_route_mounted dựng bare-app từ X.router và assert route đã register.
# Trên CI-Linux (order-dependent, KHÔNG reproduce local/Windows), một test nào đó làm
# RỖNG X.router → ~40 test route-mounted fail. Chưa truy được thủ phạm; prod KHÔNG ảnh
# hưởng (dùng server.app đã copy route lúc mount). Snapshot route-list lúc session-start
# (populated) rồi restore TRƯỚC mỗi test → route-mounted luôn thấy router đầy đủ.
@pytest.fixture(scope="session", autouse=True)
def _snapshot_routers():
    snaps = {}
    for name in ("admin", "social", "auth", "notifications", "public_api"):
        try:
            mod = __import__(name)
            if hasattr(mod, "router") and len(mod.router.routes) > 5:
                snaps[name] = (mod, list(mod.router.routes))
        except Exception:
            pass
    return snaps


@pytest.fixture(autouse=True)
def _restore_routers(_snapshot_routers):
    for _name, (mod, routes) in _snapshot_routers.items():
        if len(mod.router.routes) < len(routes):
            mod.router.routes[:] = list(routes)
    yield


@pytest.fixture
def sample_entities():
    """Minimal entity list for testing."""
    return [
        {
            "id": "cam-sanh-vinh-long",
            "name": "Cam sành Vĩnh Long",
            "type": "product",
            "summary": "Cam sành Vĩnh Long nổi tiếng ngọt mát, vỏ xanh.",
            "placeId": "xa-binh-hoa-phuoc",
            "confidence": 0.95,
            "images": ["https://example.com/cam.jpg"],
            "attributes": {"ocop": True, "ocopStars": 4},
            "season": {"months": [10, 11, 12, 1, 2], "peak": [11, 12]},
            "source": "manual",
            "updatedAt": "2026-06-01",
        },
        {
            "id": "bun-mam",
            "name": "Bún mắm",
            "type": "dish",
            "summary": "Bún mắm đặc sản Trà Vinh.",
            "placeId": "tp-tra-vinh",
            "confidence": 0.8,
            "images": [],
            "attributes": {},
            "source": "crawled",
            "updatedAt": "2026-06-05",
        },
        {
            "id": "xa-binh-hoa-phuoc",
            "name": "Bình Hòa Phước",
            "type": "place",
            "area": "vinh-long",
            "level": "xa",
            "parentId": "h-long-ho",
        },
        {
            "id": "tp-tra-vinh",
            "name": "TP Trà Vinh",
            "type": "place",
            "area": "tra-vinh",
            "level": "phuong",
        },
    ]


@pytest.fixture
def sample_data(sample_entities):
    """Full data structure matching data.json format."""
    return {
        "entities": sample_entities,
        "relationships": [
            {"from": "cam-sanh-vinh-long", "to": "xa-binh-hoa-phuoc", "type": "produced_in"},
        ],
        "itineraries": [
            {
                "id": "1-ngay-vinh-long",
                "name": "1 ngày Vĩnh Long",
                "area": "vinh-long",
                "days": 1,
                "stops": ["cam-sanh-vinh-long"],
            }
        ],
    }


@pytest.fixture
def tmp_data_json(sample_data, tmp_path):
    """Write sample data to a temp data.json and return the path."""
    data_path = tmp_path / "data.json"
    data_path.write_text(json.dumps(sample_data, ensure_ascii=False), encoding="utf-8")
    return data_path


@pytest.fixture
def tmp_analytics(tmp_path):
    """Create a temp analytics.json with sample data."""
    analytics_path = tmp_path / "analytics.json"
    data = {
        "queries": [
            {"text": "Cam sanh la gi?", "timestamp": "2026-06-10T01:00:00", "tools": [], "has_answer": True},
            {"text": "Bun mam o dau?", "timestamp": "2026-06-10T01:01:00", "tools": [], "has_answer": False},
        ],
        "entity_hits": {"cam-sanh-vinh-long": 5},
        "daily_stats": {"2026-06-10": {"queries": 10, "sessions": 2}},
        "gap_queries": ["bun mam o dau"],
        "unanswered": [{"text": "Bun mam o dau?", "timestamp": "2026-06-10T01:01:00"}],
        "tool_usage": {"search": 8, "entity_detail": 3},
        "sessions": 2,
    }
    analytics_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return analytics_path
