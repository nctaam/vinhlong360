"""One loopback-only rule for the disposable test database.

Fifteen suites had each grown their own copy of this validator. Nothing had
drifted apart semantically yet — but the guard decides whether a test suite is
allowed to open a connection, and a rule that exists in fifteen places is a rule
that will eventually mean fifteen things. The copy that drifts is the one that
lets a run point at something that is not a throwaway database.

The rule: a disposable PostgreSQL on the loopback interface, named by
VL360_TEST_DATABASE_URL, or no database tests at all.
"""
from __future__ import annotations

import os
from urllib.parse import parse_qs, urlparse

import pytest

LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
SKIP_REASON = "set VL360_TEST_DATABASE_URL to a disposable loopback PostgreSQL database"


def pg_url() -> str | None:
    """The configured test database, or None when it is not one we may touch."""
    raw = os.environ.get("VL360_TEST_DATABASE_URL", "").strip()
    if not raw:
        return None
    parsed = urlparse(raw)
    if parsed.scheme not in {"postgres", "postgresql"} or parsed.hostname not in LOOPBACK_HOSTS:
        return None
    # libpq lets `host`/`hostaddr` in the query string override the hostname we
    # just checked, so a loopback-looking URL could still dial elsewhere.
    if {"host", "hostaddr"} & parse_qs(parsed.query, keep_blank_values=True).keys():
        return None
    return raw


TEST_DATABASE_URL = pg_url()

pg_only = pytest.mark.skipif(TEST_DATABASE_URL is None, reason=SKIP_REASON)
