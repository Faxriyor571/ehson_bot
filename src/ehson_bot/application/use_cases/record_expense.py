"""Use case: a treasurer records a confirmed use of pooled funds."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ehson_bot.domain.entities import Expense, TreasurerId
from ehson_bot.domain.repositories import ExpenseRepository
from ehson_bot.domain.value_objects import Money


@dataclass(frozen=True, slots=True)
class RecordExpenseInput:
    amount: Decimal
    description: str
    recorded_by_id: int
    receipt_file_id: str | None = None


class RecordExpenseUseCase:
    def __init__(self, repository: ExpenseRepository) -> None:
        self._repository = repository

    async def execute(self, data: RecordExpenseInput) -> Expense:
        expense = Expense(
            amount=Money(data.amount),
            description=data.description,
            recorded_by=TreasurerId(data.recorded_by_id),
            receipt_file_id=data.receipt_file_id,
        )
        return await self._repository.add(expense)
