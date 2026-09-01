"""Canonical UTC and Vietnam clocks used by cache and presentation code."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

try:
    VIETNAM_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
except Exception:  # Windows test/runtime images may not bundle tzdata.
    VIETNAM_TZ = timezone(timedelta(hours=7), name="Asia/Ho_Chi_Minh")


class Clock:
    """Clock interface. All persisted values originate from UTC."""

    def now_utc(self) -> datetime:
        raise NotImplementedError

    def now_vietnam(self) -> datetime:
        return self.now_utc().astimezone(VIETNAM_TZ)


class SystemClock(Clock):
    def now_utc(self) -> datetime:
        return datetime.now(timezone.utc)


class FrozenClock(Clock):
    def __init__(self, value: datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("FrozenClock requires an aware datetime")
        self._value = value.astimezone(timezone.utc)

    def now_utc(self) -> datetime:
        return self._value


system_clock = SystemClock()


def utc_now() -> datetime:
    """Compatibility helper for callers that need the process clock."""
    return system_clock.now_utc()


def vietnam_now() -> datetime:
    return system_clock.now_vietnam()
