"""Timezone-aware period boundaries, anchored to ``settings.timezone``.

All "today/month/year" bucketing and the 23:59 daily job use this so date
math is consistent everywhere instead of accidentally using server-local or
UTC boundaries.
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from ehson_bot.infrastructure.config import settings


def local_tz() -> ZoneInfo:
    return ZoneInfo(settings.timezone)


def local_now() -> datetime:
    return datetime.now(local_tz())


def start_of_today(at: datetime | None = None) -> datetime:
    now = at or local_now()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def start_of_month(at: datetime | None = None) -> datetime:
    return start_of_today(at).replace(day=1)


def start_of_year(at: datetime | None = None) -> datetime:
    return start_of_month(at).replace(month=1)
