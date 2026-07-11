"""Use case: a treasurer corrects a mistaken expense entry."""
from __future__ import annotations

from ehson_bot.domain.exceptions import ExpenseNotFound
from ehson_bot.domain.repositories import ExpenseRepository


class RemoveExpenseUseCase:
    def __init__(self, repository: ExpenseRepository) -> None:
        self._repository = repository

    async def execute(self, expense_id: int) -> None:
        removed = await self._repository.remove(expense_id)
        if not removed:
            raise ExpenseNotFound(f"Expense #{expense_id} does not exist")
