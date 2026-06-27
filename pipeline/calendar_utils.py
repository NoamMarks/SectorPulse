"""US (NYSE) trading-calendar helpers (PRD §8.1, §8.3).

Self-contained — no heavy external calendar dependency. Resolves the latest
*completed* trading date in ET, which is what the idempotency guard keys on
(NOT the wall-clock calendar date, which was the v2.0 bug).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from functools import lru_cache
from zoneinfo import ZoneInfo

import pandas as pd

ET = ZoneInfo("America/New_York")
# Regular session close; we treat data as final only comfortably after this.
SETTLE_HOUR_ET = 17  # 17:00 ET — safe in both EST and EDT (PRD §8.1)


def _easter(year: int) -> date:
    # Anonymous Gregorian algorithm
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return date(year, month, day + 1)


def _observed(d: date) -> date:
    if d.weekday() == 5:        # Saturday -> Friday
        return d - timedelta(days=1)
    if d.weekday() == 6:        # Sunday -> Monday
        return d + timedelta(days=1)
    return d


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    d = date(year, month, 1)
    offset = (weekday - d.weekday()) % 7
    return d + timedelta(days=offset + 7 * (n - 1))


def _last_weekday(year: int, month: int, weekday: int) -> date:
    if month == 12:
        d = date(year, 12, 31)
    else:
        d = date(year, month + 1, 1) - timedelta(days=1)
    while d.weekday() != weekday:
        d -= timedelta(days=1)
    return d


@lru_cache(maxsize=64)
def holidays(year: int) -> frozenset[date]:
    h = {
        _observed(date(year, 1, 1)),                       # New Year's
        _nth_weekday(year, 1, 0, 3),                        # MLK (3rd Mon Jan)
        _nth_weekday(year, 2, 0, 3),                        # Washington (3rd Mon Feb)
        _easter(year) - timedelta(days=2),                 # Good Friday
        _last_weekday(year, 5, 0),                          # Memorial (last Mon May)
        _observed(date(year, 6, 19)),                       # Juneteenth
        _observed(date(year, 7, 4)),                        # Independence
        _nth_weekday(year, 9, 0, 1),                        # Labor (1st Mon Sep)
        _nth_weekday(year, 11, 3, 4),                       # Thanksgiving (4th Thu Nov)
        _observed(date(year, 12, 25)),                      # Christmas
    }
    return frozenset(h)


def is_trading_day(d: date) -> bool:
    return d.weekday() < 5 and d not in holidays(d.year)


def previous_trading_day(d: date) -> date:
    d -= timedelta(days=1)
    while not is_trading_day(d):
        d -= timedelta(days=1)
    return d


def latest_trading_date(now_utc: datetime | None = None) -> date:
    """Most recent *completed* NYSE session as of ``now`` (ET-aware)."""
    now_et = (now_utc or datetime.now(tz=ZoneInfo("UTC"))).astimezone(ET)
    d = now_et.date()
    completed_today = is_trading_day(d) and now_et.hour >= SETTLE_HOUR_ET
    if is_trading_day(d) and completed_today:
        return d
    return previous_trading_day(d)


def is_market_open(now_utc: datetime | None = None) -> bool:
    """True during the 9:30–16:00 ET regular session on a trading day (PRD §8.1).
    Used by the intraday job to no-op outside market hours."""
    now_et = (now_utc or datetime.now(tz=ZoneInfo("UTC"))).astimezone(ET)
    if not is_trading_day(now_et.date()):
        return False
    minutes = now_et.hour * 60 + now_et.minute
    return 9 * 60 + 30 <= minutes < 16 * 60


def current_session_date(now_utc: datetime | None = None) -> date:
    """Today's date if it is a trading day (the in-progress session), else the
    most recent completed session. Intraday bars are stamped with this date."""
    now_et = (now_utc or datetime.now(tz=ZoneInfo("UTC"))).astimezone(ET)
    d = now_et.date()
    return d if is_trading_day(d) else previous_trading_day(d)


def to_timestamp(d: date) -> pd.Timestamp:
    return pd.Timestamp(d)
