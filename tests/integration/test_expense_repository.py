"""Integration tests for SqlAlchemyExpenseRepository against in-memory SQLite."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from ehson_bot.domain.entities import Expense, TreasurerId
from ehson_bot.domain.value_objects import Money
from ehson_bot.infrastructure.db.models import ExpenseRow
from ehson_bot.infrastructure.db.repositories import SqlAlchemyExpenseRepository


async def test_add_persists_description_and_receipt(session: AsyncSession) -> None:
    repo = SqlAlchemyExpenseRepository(session)

    expense = await repo.add(
        Expense(
            amount=Money(Decimal(200000)),
            description="Tibbiy yordam",
            recorded_by=TreasurerId(1),
            receipt_file_id="file123",
        )
    )

    assert expense.id is not None
    assert expense.description == "Tibbiy yordam"
    assert expense.receipt_file_id == "file123"


async def test_remove_deletes_existing_and_reports_missing(session: AsyncSession) -> None:
    repo = SqlAlchemyExpenseRepository(session)
    expense = await repo.add(
        Expense(amount=Money(Decimal(1000)), description="Ovqat", recorded_by=TreasurerId(1))
    )

    assert await repo.remove(expense.id) is True
    assert await repo.get(expense.id) is None
    assert await repo.remove(expense.id) is False


async def test_sum_since_none_returns_all_time_total(session: AsyncSession) -> None:
    repo = SqlAlchemyExpenseRepository(session)
    await repo.add(
        Expense(amount=Money(Decimal(1000)), description="A", recorded_by=TreasurerId(1))
    )
    await repo.add(
        Expense(amount=Money(Decimal(2000)), description="B", recorded_by=TreasurerId(1))
    )

    assert await repo.sum_since(None) == Decimal(3000)


async def test_sum_since_start_excludes_older_rows(session: AsyncSession) -> None:
    old = ExpenseRow(
        amount=Decimal(1000),
        description="Old",
        recorded_by_id=1,
        created_at=datetime(2020, 1, 1),
    )
    recent = ExpenseRow(
        amount=Decimal(2000),
        description="Recent",
        recorded_by_id=1,
        created_at=datetime(2026, 1, 1),
    )
    session.add_all([old, recent])
    await session.commit()

    repo = SqlAlchemyExpenseRepository(session)
    total = await repo.sum_since(datetime(2025, 1, 1))

    assert total == Decimal(2000)


async def test_sum_since_on_empty_ledger_is_zero(session: AsyncSession) -> None:
    repo = SqlAlchemyExpenseRepository(session)

    assert await repo.sum_since(None) == 0


async def test_count_since_counts_entries(session: AsyncSession) -> None:
    repo = SqlAlchemyExpenseRepository(session)
    await repo.add(
        Expense(amount=Money(Decimal(1000)), description="A", recorded_by=TreasurerId(1))
    )
    await repo.add(
        Expense(amount=Money(Decimal(2000)), description="B", recorded_by=TreasurerId(1))
    )

    assert await repo.count_since(None) == 2


async def test_count_since_start_excludes_older_rows(session: AsyncSession) -> None:
    old = ExpenseRow(
        amount=Decimal(1000),
        description="Old",
        recorded_by_id=1,
        created_at=datetime(2020, 1, 1),
    )
    recent = ExpenseRow(
        amount=Decimal(2000),
        description="Recent",
        recorded_by_id=1,
        created_at=datetime(2026, 1, 1),
    )
    session.add_all([old, recent])
    await session.commit()

    repo = SqlAlchemyExpenseRepository(session)

    assert await repo.count_since(datetime(2025, 1, 1)) == 1
