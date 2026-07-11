"""Unit test for ListRecentEntriesUseCase against fake repositories."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from ehson_bot.application.use_cases.list_recent_entries import ListRecentEntriesUseCase
from ehson_bot.domain.entities import Donation, Expense, TreasurerId
from ehson_bot.domain.value_objects import Money


class FakeDonationRepo:
    def __init__(self, donations: list[Donation]) -> None:
        self._donations = donations

    async def list_recent(self, limit: int) -> list[Donation]:
        # Mirrors the real repository's contract: newest first, then limited.
        return sorted(self._donations, key=lambda d: d.created_at, reverse=True)[:limit]


class FakeExpenseRepo:
    def __init__(self, expenses: list[Expense]) -> None:
        self._expenses = expenses

    async def list_recent(self, limit: int) -> list[Expense]:
        return self._expenses[:limit]


async def test_merges_and_sorts_newest_first() -> None:
    donation = Donation(
        id=1,
        amount=Money(Decimal(1000)),
        recorded_by=TreasurerId(1),
        note="fitr",
        created_at=datetime(2026, 1, 1),
    )
    expense = Expense(
        id=1,
        amount=Money(Decimal(500)),
        description="Ovqat",
        recorded_by=TreasurerId(1),
        created_at=datetime(2026, 1, 2),
    )
    use_case = ListRecentEntriesUseCase(
        FakeDonationRepo([donation]), FakeExpenseRepo([expense])  # type: ignore[arg-type]
    )

    entries = await use_case.execute()

    assert [(e.kind, e.id) for e in entries] == [("expense", 1), ("donation", 1)]
    assert entries[0].label == "Ovqat"
    assert entries[1].label == "fitr"


async def test_respects_limit_after_merging() -> None:
    donations = [
        Donation(
            id=i,
            amount=Money(Decimal(100)),
            recorded_by=TreasurerId(1),
            created_at=datetime(2026, 1, i),
        )
        for i in range(1, 4)
    ]
    use_case = ListRecentEntriesUseCase(
        FakeDonationRepo(donations), FakeExpenseRepo([])  # type: ignore[arg-type]
    )

    entries = await use_case.execute(limit=2)

    assert len(entries) == 2
    assert entries[0].id == 3
