"""Shared fixtures for vinhlong360 tests."""
import os
import sys
import pytest

# Add agent/ to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

# Set test environment
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:9999/v1")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:8360")
# Scheduler nền PHẢI tắt trong test: task "data-sync" ghi đè file tracked
# web/data.js. scheduler.py đọc env lúc import → phải đặt ở conftest (chạy trước
# mọi test module) mới kịp. Chi tiết: agent/tests/test_scheduler_repo_isolation.py
os.environ.setdefault("SCHEDULER_ENABLED", "false")

@pytest.fixture
def admin_headers():
    return {"X-Admin-Key": "test-admin-key"}
