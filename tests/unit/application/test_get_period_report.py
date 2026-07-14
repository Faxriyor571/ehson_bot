"""Unit test for GetPeriodReportUseCase against fake repositories."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from ehson_bot.application.use_cases.get_period_report import GetPeriodReportUseCase, Period


class FakeSumRepository:
    def __init__(
        self, all_time: Decimal, since_today: Decimal, all_time_count: int = 0, today_count: int = 0
    ) -> None:
        self._all_time = all_time
        self._since_today = since_today
        self._all_time_count = all_time_count
        self._today_count = today_count
        self.requested_starts: list[datetime | None] = []

    async def sum_since(self, start: datetime | None) -> Decimal:
        self.requested_starts.append(start)
        return self._all_time if start is None else self._since_today

    async def count_since(self, start: datetime | None) -> int:
        return self._all_time_count if start is None else self._today_count


async def test_all_period_queries_with_no_start_bound() -> None:
    donations = FakeSumRepository(
        all_time=Decimal(5000), since_today=Decimal(500), all_time_count=7, today_count=1
    )
    expenses = FakeSumRepository(
        all_time=Decimal(2000), since_today=Decimal(200), all_time_count=3, today_count=1
    )
    use_case = GetPeriodReportUseCase(donations, expenses)  # type: ignore[arg-type]

    snapshot = await use_case.execute(Period.ALL)

    assert snapshot.donations_total == Decimal(5000)
    assert snapshot.expenses_total == Decimal(2000)
    assert snapshot.balance == Decimal(3000)
    assert snapshot.donations_count == 7
    assert snapshot.expenses_count == 3
    assert donations.requested_starts == [None]


async def test_today_period_queries_with_a_start_bound() -> None:
    donations = FakeSumRepository(
        all_time=Decimal(5000), since_today=Decimal(500), all_time_count=7, today_count=1
    )
    expenses = FakeSumRepository(
        all_time=Decimal(2000), since_today=Decimal(200), all_time_count=3, today_count=1
    )
    use_case = GetPeriodReportUseCase(donations, expenses)  # type: ignore[arg-type]

    snapshot = await use_case.execute(Period.TODAY)

    assert snapshot.donations_total == Decimal(500)
    assert snapshot.expenses_total == Decimal(200)
    assert snapshot.balance == Decimal(300)
    assert snapshot.donations_count == 1
    assert snapshot.expenses_count == 1
    assert donations.requested_starts[0] is not None
