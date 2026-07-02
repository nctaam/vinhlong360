"""Tests audit vòng 2 — 8 fix (2026-07-02 tối).

Phủ: #1 filter key nhạy cảm site-settings; #2 4 task scheduler import instance;
#3 retry hot-loop + cột moderation_status; #7 SEO DB snapshot TTL.
(#4 executor / #5 to_thread / #8 record_usage wiring: thay đổi 1-2 dòng đã
review, hành vi cần chat/PG thật — verify trên prod sau deploy.)
"""
import os
import sys
import pathlib
import time

os.environ.setdefault("BUILD_SEARCH_INDEXES", "false")
os.environ.setdefault("SCHEDULER_ENABLED", "false")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import scheduler as sched_mod  # noqa: E402
from site_settings import is_public_key  # noqa: E402


# ── Fix #1: filter key nhạy cảm khỏi public site-settings ──
def test_sensitive_keys_blocked():
    for k in ("llm.api_key", "llm.base_url", "LLM.model", "payment_secret",
              "zalo_token", "smtp_password", "some.api_key"):
        assert not is_public_key(k), k


def test_normal_keys_allowed():
    for k in ("branding.site_name", "footer.tagline", "homepage.hero_title",
              "contact.email"):
        assert is_public_key(k), k


# ── Fix #2: 4 task bảo trì dùng instance db (trên SQLite phải return sạch,
#    KHÔNG AttributeError như trước — module database không có _use_pg) ──
def test_broken_maintenance_tasks_run_clean_on_sqlite():
    for fn_name in ("task_notification_cleanup", "task_event_reminders",
                    "task_session_cleanup", "task_moderation_auto_escalation"):
        fn = getattr(sched_mod, fn_name)
        fn()  # trước fix: AttributeError 'module database has no _use_pg' bị nuốt


# ── Fix #3: task fail bền vững phải CHỜ interval, không hot-loop mỗi tick ──
def test_persistent_failure_waits_interval_no_hot_loop():
    calls = {"n": 0}

    def always_fail():
        calls["n"] += 1
        raise RuntimeError("boom")

    t = sched_mod.ScheduledTask("test-fail", always_fail, interval_seconds=3600, timeout=10)
    # Chạy tới quá số retry (MAX_RETRIES=2 → lần 3 là hết retry)
    for _ in range(sched_mod._MAX_RETRIES + 1):
        t.next_run_after = 0  # cho phép chạy ngay (mô phỏng backoff đã qua)
        t.run()
    assert t.next_run_after > time.time() + 3000, \
        "hết retry phải đặt next_run_after = now + interval (chống hot-loop 60s)"
    n_before = calls["n"]
    assert not t.should_run(), "should_run phải False khi đang trong khoảng chờ"
    assert calls["n"] == n_before


def test_admin_digest_uses_moderation_status_column():
    import inspect
    src = inspect.getsource(sched_mod)
    assert "FROM posts WHERE moderation_status =" in src
    assert "FROM posts WHERE status =" not in src, "posts không có cột status"


# ── Fix #7: SEO DB snapshot TTL — không query cả DB mỗi request ──
def test_seo_db_snapshot_cached_within_ttl(monkeypatch):
    import seo
    calls = {"n": 0}

    class FakeDB:
        def all_entities(self):
            calls["n"] += 1
            return [{"id": "x", "type": "product", "name": "X"}]

        def all_relationships(self):
            return []

        def all_itineraries(self):
            return []

    import database
    monkeypatch.setattr(database, "db", FakeDB())
    seo._db_snapshot = None
    seo._db_snapshot_ts = 0.0
    first = seo._load_db_data()
    second = seo._load_db_data()
    assert first is second and calls["n"] == 1, "trong TTL phải trả snapshot cache"
    seo._db_snapshot_ts = 0.0  # hết hạn
    seo._load_db_data()
    assert calls["n"] == 2
    seo._db_snapshot = None
    seo._db_snapshot_ts = 0.0