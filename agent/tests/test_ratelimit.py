"""
Chống spam UGC — rate-limit sliding-window (ratelimit.py) + wiring create_post.
Unit test offline; 1 endpoint test pg_only (hạ limit qua monkeypatch).
"""
import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import HTTPException, FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import ratelimit  # noqa: E402
from ratelimit import check_rate  # noqa: E402
from database import db  # noqa: E402

pg_only = pytest.mark.skipif(not db._use_pg, reason="UGC là Postgres-only (SQLite trả 503).")


# ── Unit: limiter ──────────────────────────────────────────────────────────
def test_allows_up_to_limit_then_blocks():
    ratelimit._reset()
    for _ in range(3):
        check_rate("k", limit=3, window=100)
    with pytest.raises(HTTPException) as ei:
        check_rate("k", limit=3, window=100)
    assert ei.value.status_code == 429


def test_keys_isolated():
    ratelimit._reset()
    check_rate("a", 1, 100)
    check_rate("b", 1, 100)  # key khác không bị ảnh hưởng
    with pytest.raises(HTTPException):
        check_rate("a", 1, 100)


def test_window_expiry(monkeypatch):
    ratelimit._reset()
    t = [1000.0]
    monkeypatch.setattr(ratelimit, "_now", lambda: t[0])
    check_rate("k", 1, 10)
    t[0] += 11  # quá cửa sổ → cho phép lại
    check_rate("k", 1, 10)  # không raise


# ── Endpoint: create_post bị chặn khi vượt limit ───────────────────────────
@pg_only
def test_create_post_rate_limited(monkeypatch):
    import social
    from auth_middleware import require_user, get_current_user

    ratelimit._reset()
    monkeypatch.setattr(social, "RL_POST_LIMIT", 2)  # hạ limit để test nhanh
    user = db.create_user("09" + uuid.uuid4().hex[:8])
    app = FastAPI()
    app.include_router(social.router)
    app.dependency_overrides[require_user] = lambda: user
    app.dependency_overrides[get_current_user] = lambda: user
    client = TestClient(app)
    created = []
    try:
        for _i in range(2):
            # Nội dung UNIQUE mỗi bài — tránh chặn-trùng-nội-dung (409) che mất path rate-limit (429).
            r = client.post("/api/posts", json={"content": f"Chia sẻ trải nghiệm hợp lệ số {_i}.", "post_type": "share"})
            assert r.status_code == 201, r.text
            created.append(r.json()["post"]["id"])
        # lần thứ 3 vượt limit → 429
        blocked = client.post("/api/posts", json={"content": "Bài thứ ba bị chặn nhé.", "post_type": "share"})
        assert blocked.status_code == 429
    finally:
        with db._conn() as conn:
            for pid in created:
                db._execute(conn, f"DELETE FROM posts WHERE id::text = {db._ph}", (pid,))
            db._execute(conn, f"DELETE FROM users WHERE id::text = {db._ph}", (str(user["id"]),))
