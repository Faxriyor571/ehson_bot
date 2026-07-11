"""Use case: donations vs. usage vs. balance for a given period."""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from ehson_bot.domain.repositories import DonationRepository, ExpenseRepository
from ehson_bot.domain.value_objects import PoolSnapshot
from ehson_bot.infrastructure.timeutil import start_of_month, start_of_today, start_of_year


class Period(str, Enum):
    TODAY = "today"
    MONTH = "month"
    YEAR = "year"
    ALL = "all"


def _period_start(period: Period) -> datetime | None:
    if period is Period.TODAY:
        return start_of_today()
    if period is Period.MONTH:
        return start_of_month()
    if period is Period.YEAR:
        return start_of_year()
    return None


class GetPeriodReportUseCase:
    def __init__(self, donation_repo: DonationRepository, expense_repo: ExpenseRepository) -> None:
        self._donations = donation_repo
        self._expenses = expense_repo

    async def execute(self, period: Period) -> PoolSnapshot:
        start = _period_start(period)
        donations_total = await self._donations.sum_since(start)
        expenses_total = await self._expenses.sum_since(start)
        return PoolSnapshot(donations_total=donations_total, expenses_total=expenses_total)
