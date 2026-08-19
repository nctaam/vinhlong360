"""The one rule that decides whether a test run may open a database.

It used to live in fifteen copies, so nothing held it to anything. Now that it
is one function, it is a single point of failure worth its own tests: every
branch here is the difference between a suite writing to a throwaway container
and a suite writing to something somebody cares about.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _pg_test_database import SKIP_REASON, pg_url  # noqa: E402


def _env(monkeypatch, value):
    monkeypatch.setenv("VL360_TEST_DATABASE_URL", value)
    return pg_url()


def test_no_setting_means_no_database_tests(monkeypatch):
    monkeypatch.delenv("VL360_TEST_DATABASE_URL", raising=False)

    assert pg_url() is None


@pytest.mark.parametrize("value", ["", "   ", "\t\n"])
def test_a_blank_setting_is_not_a_database(monkeypatch, value):
    assert _env(monkeypatch, value) is None


def test_a_loopback_postgres_is_accepted(monkeypatch):
    for host in ("localhost", "127.0.0.1"):
        url = f"postgresql://vl360:vl360@{host}:5433/vl360_case_breaker_test"
        assert _env(monkeypatch, url) == url


@pytest.mark.parametrize("host", ["db.example.com", "10.0.0.5", "192.168.1.20", "::2"])
def test_anything_off_the_loopback_is_refused(monkeypatch, host):
    # A remote database in a test run is somebody's real data being written to
    # by a suite that truncates tables between cases.
    assert _env(monkeypatch, f"postgresql://u:p@{host}:5432/db") is None


@pytest.mark.parametrize("scheme", ["mysql", "sqlite", "http", "postgresqlx"])
def test_only_postgres_schemes_pass(monkeypatch, scheme):
    assert _env(monkeypatch, f"{scheme}://localhost:5432/db") is None


@pytest.mark.parametrize("param", ["host", "hostaddr"])
def test_a_libpq_override_in_the_query_string_is_refused(monkeypatch, param):
    # libpq honours host/hostaddr from the query string over the hostname, so a
    # loopback-looking URL can still dial somewhere else entirely. This is the
    # branch a hand-rolled copy of the rule is most likely to forget.
    url = f"postgresql://u:p@127.0.0.1:5432/db?{param}=db.example.com"

    assert _env(monkeypatch, url) is None


def test_the_skip_reason_tells_an_operator_what_to_do():
    assert "VL360_TEST_DATABASE_URL" in SKIP_REASON
    assert "disposable" in SKIP_REASON
