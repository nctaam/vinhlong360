"""Không route nào được đăng ký hai lần trên app đã mount.

Bug thật đã ship: GET /api/me/activity được khai báo ở cả public_api.py và
social.py, cả hai cùng prefix "/api". FastAPI giữ bản đăng ký trước, bản sau
thành code chết — nhưng hai bản trả payload khác nhau, nên phía frontend đọc
một key mà không bản nào trả. Mọi test cũ đều xanh vì chúng import router của
từng module riêng lẻ, không bao giờ soi app đã merge.
"""
import os
import sys
from collections import Counter
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agent"))


@pytest.fixture(scope="module")
def app_routes():
    os.environ.setdefault("BUILD_SEARCH_INDEXES", "false")
    os.environ.setdefault("BACKGROUND_INDEX_BUILD", "false")
    os.environ.setdefault("SCHEDULER_ENABLED", "false")
    with patch("server.start_scheduler", MagicMock()), \
         patch("server.sync_data_json_to_js", MagicMock()):
        from server import app
    return list(app.routes)


def _method_path_pairs(routes):
    pairs = []
    for route in routes:
        methods = getattr(route, "methods", None)
        path = getattr(route, "path", None)
        if not methods or not path:
            continue
        for method in methods:
            if method in ("HEAD", "OPTIONS"):
                continue
            pairs.append((method, path))
    return pairs


def test_no_duplicate_method_path_on_mounted_app(app_routes):
    duplicates = {
        pair: count
        for pair, count in Counter(_method_path_pairs(app_routes)).items()
        if count > 1
    }
    assert duplicates == {}, (
        "Route bị đăng ký trùng trên app đã mount; bản đăng ký sau là code chết "
        f"và OpenAPI sẽ mơ hồ: {sorted(duplicates)}"
    )


def test_me_activity_is_served_by_the_ugc_router(app_routes):
    """/api/me/activity phải nằm sau guard Postgres, không phải router public.

    Router UGC khai báo dependencies=[Depends(require_pg)] nên chế độ SQLite
    trả 503 có thông điệp rõ ràng. Nếu route này rơi vào router public không
    guard, cùng truy vấn đó ném 500 không kiểm soát.
    """
    activity = [r for r in app_routes if getattr(r, "path", None) == "/api/me/activity"]
    assert len(activity) == 1, f"kỳ vọng đúng 1 handler, có {len(activity)}"

    dependency_calls = [
        getattr(dep.call, "__name__", "")
        for dep in getattr(activity[0], "dependant", None).dependencies
    ] if getattr(activity[0], "dependant", None) else []
    assert any("require_pg" in name for name in dependency_calls), (
        "/api/me/activity phải chịu guard require_pg để trả 503 thay vì 500 khi chạy SQLite; "
        f"dependencies hiện tại: {dependency_calls}"
    )
