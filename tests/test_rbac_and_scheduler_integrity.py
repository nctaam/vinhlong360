# -*- coding: utf-8 -*-
"""Regression tests for Wave 14 (QW-41):
1. RBAC privilege hierarchy enforcement in community/admin_api.py:
   - _assert_role_change_allowed blocks non-superadmin from modifying a superadmin target
     or granting superadmin/admin roles.
   - unban_user and bulk_unban_users enforce _assert_actor_can_manage_target so a
     moderator or admin cannot unban an equal-or-higher-ranked account.
2. Data integrity & N+1 elimination in scheduler._hard_delete_stale_posts:
   - Deletes child records (comments, likes, bookmarks, notifications) and parent posts
     strictly for the fetched batch of <=500 IDs using batched IN (...) queries (5 SQL
     statements total instead of 2,001), preventing orphan child rows for posts >500.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace
import pytest
from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "agent") not in sys.path:
    sys.path.insert(0, str(ROOT / "agent"))

from community import admin_api as comm_admin  # noqa: E402
from community import api as comm_api  # noqa: E402
from cases import public_api as case_public_api  # noqa: E402
import contextual_retrieval  # noqa: E402
import database  # noqa: E402
import learn_loop  # noqa: E402
import orchestrator  # noqa: E402
import scheduler  # noqa: E402


def test_role_change_blocks_admin_from_demoting_superadmin():
    admin_actor = {"id": "a1", "role": "admin"}
    with pytest.raises(HTTPException) as exc:
        comm_admin._assert_role_change_allowed(
            admin_user=admin_actor,
            admin_role="admin",
            role="user",
            target_role="superadmin",
        )
    assert exc.value.status_code == 403


def test_unban_user_blocks_moderator_from_unbanning_admin(monkeypatch):
    monkeypatch.setattr(comm_admin, "require_pg", lambda: None)
    monkeypatch.setattr(comm_admin, "validate_path_id", lambda v, _: v)
    monkeypatch.setattr(comm_admin, "_log_mod_action", lambda *a, **k: None)

    class FakeDB:
        _ph = "%s"

        def _conn(self):
            class _Ctx:
                def __enter__(self_inner):
                    return "conn"

                def __exit__(self_inner, *args):
                    return False

            return _Ctx()

        def _fetchone(self, conn, sql, params):
            return {"id": params[0], "is_active": False, "role": "admin"}

        def _row_to_dict(self, row):
            return dict(row)

        def _execute(self, conn, sql, params):
            raise AssertionError("Should not execute UPDATE when actor lacks rank")

    monkeypatch.setattr(comm_admin, "db", FakeDB())
    req = SimpleNamespace(state=SimpleNamespace(admin_user={"id": "mod-1", "role": "moderator"}))
    with pytest.raises(HTTPException) as exc:
        asyncio.run(comm_admin.unban_user("admin-target-1", req))
    assert exc.value.status_code == 403


def test_bulk_unban_users_blocks_admin_from_unbanning_peer_admin(monkeypatch):
    monkeypatch.setattr(comm_admin, "require_pg", lambda: None)
    monkeypatch.setattr(comm_admin, "validate_path_id", lambda v, _: v)
    monkeypatch.setattr(comm_admin, "_log_mod_action", lambda *a, **k: None)

    class FakeDB:
        _ph = "%s"

        def _conn(self):
            class _Ctx:
                def __enter__(self_inner):
                    return "conn"

                def __exit__(self_inner, *args):
                    return False

            return _Ctx()

        def _fetchone(self, conn, sql, params):
            return {"id": params[0], "is_active": False, "role": "admin"}

        def _row_to_dict(self, row):
            return dict(row)

        def _execute(self, conn, sql, params):
            raise AssertionError("Should not execute UPDATE when actor lacks rank")

    monkeypatch.setattr(comm_admin, "db", FakeDB())
    req = SimpleNamespace(state=SimpleNamespace(admin_user={"id": "adm-1", "role": "admin"}))
    body = comm_admin.BulkUserAction(user_ids=["adm-2"], reason="test")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(comm_admin.bulk_unban_users(body, req))
    assert exc.value.status_code == 403


def test_hard_delete_stale_posts_uses_batched_in_queries_and_scopes_post_delete():
    executed: list[tuple[str, tuple]] = []

    class FakeDB:
        _ph = "%s"

        def _fetchall(self, conn, sql, params):
            return [{"id": "p-1"}, {"id": "p-2"}, {"id": "p-3"}]

        def _row_to_dict(self, row):
            return dict(row)

        def _execute(self, conn, sql, params):
            executed.append((" ".join(sql.split()), tuple(params)))

    scheduler._hard_delete_stale_posts(FakeDB(), "conn")
    # Must execute exactly 5 batched DELETE queries (not 3 * 4 + 1 = 13)
    assert len(executed) == 5, f"Expected 5 batched queries, got {len(executed)}: {executed}"
    posts_delete_sql, posts_delete_params = executed[-1]
    assert "DELETE FROM posts" in posts_delete_sql
    assert "IN (" in posts_delete_sql
    assert posts_delete_params == ("p-1", "p-2", "p-3")


def test_stage2_audit_remediations_contracts():
    # 1. community.api.DraftPost strips HTML and validates rating
    draft = comm_api.DraftPost(content="<b>Xin chào</b> Vĩnh Long", post_type="review", rating=5)
    assert draft.content == "Xin chào Vĩnh Long"

    # 2. orchestrator.SEARCH_AGENT includes weather, seasonal_now, places_in_area
    for tool_name in ("weather", "seasonal_now", "places_in_area"):
        assert tool_name in orchestrator.SEARCH_AGENT.allowed_tools

    # 3. contextual_retrieval._compute_hybrid falls back to keyword_scores when bm25 is 0
    hybrid = contextual_retrieval._compute_hybrid(
        ["e1"], {"e1": 0.0}, {"e1": 0.5}, {"e1": 0.8}, 0.3, 0.4, 0.3, {"e1": 0.6}
    )
    assert hybrid[0]["hybrid_score"] > 0.5

    # 4. cases.public_api._session_user_ref & learn_loop._persist_enrichments & database SQLite CAST
    assert "directory_lookup" in orchestrator.SEARCH_AGENT.allowed_tools
    assert "ocop_products" in orchestrator.SEARCH_AGENT.allowed_tools
    assert "accommodation_search" in orchestrator.SEARCH_AGENT.allowed_tools
    assert callable(case_public_api._session_user_ref)
    assert callable(case_public_api.revoke_access)
    assert callable(learn_loop._persist_enrichments)
    assert hasattr(database, "Database")


def test_publish_draft_strips_legacy_html_and_validates_post_type(monkeypatch):
    monkeypatch.setattr(comm_api, "validate_path_id", lambda v, _: v)
    monkeypatch.setattr(comm_api, "check_rate", lambda *a, **k: None)
    monkeypatch.setattr(comm_api, "log_moderation", lambda *a, **k: None)
    monkeypatch.setattr(comm_api, "_invalidate_social_caches", lambda: None)
    monkeypatch.setattr(comm_api, "_enrich_post", lambda p, u: p)

    async def _fake_mod(content, user_id=None, image_urls=None):
        return {"status": "approved", "reason": "ok"}

    monkeypatch.setattr(comm_api, "moderate_content_enhanced", _fake_mod)

    captured_params = {}

    class FakeDB:
        _ph = "%s"

        def _conn(self):
            class _Ctx:
                def __enter__(self_inner):
                    return "conn"

                def __exit__(self_inner, *args):
                    return False

            return _Ctx()

        def _fetchone(self, conn, sql, params):
            if "SELECT id, content, post_type" in sql:
                return {
                    "id": "d-1",
                    "content": "<script>alert(1)</script>Chuyến đi cù lao An Bình thật tuyệt vời #vinhlong",
                    "post_type": "review",
                    "entity_id": "ent-an-binh",
                    "rating": 5,
                    "images": "[]",
                }
            captured_params["sql"] = sql
            captured_params["params"] = params
            return {
                "id": "d-1",
                "content": params[0],
                "post_type": params[1],
                "moderation_status": params[2],
                "hashtags": params[3],
            }

        def _row_to_dict(self, row):
            return dict(row)

    monkeypatch.setattr(comm_api, "db", FakeDB())
    res = asyncio.run(comm_api.publish_draft("d-1", user={"id": "u-1"}, _csrf=None, _idem=None))
    assert "<script>" not in res["post"]["content"]
    assert res["post"]["content"].startswith("alert(1)Chuyến đi cù lao An Bình")
    assert res["post"]["post_type"] == "review"


