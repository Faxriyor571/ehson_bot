"""Use case: a merged, chronological view of recent donations + expenses.

Exists purely for display (the "recent entries" screen) — the two ledgers
stay structurally separate everywhere else.
"""
from __future__ import annotations

from ehson_bot.domain.repositories import DonationRepository, ExpenseRepository
from ehson_bot.domain.value_objects import LedgerEntry

DEFAULT_LIMIT = 20


class ListRecentEntriesUseCase:
    def __init__(self, donation_repo: DonationRepository, expense_repo: ExpenseRepository) -> None:
        self._donations = donation_repo
        self._expenses = expense_repo

    async def execute(self, limit: int = DEFAULT_LIMIT) -> list[LedgerEntry]:
        donations = await self._donations.list_recent(limit)
        expenses = await self._expenses.list_recent(limit)

        entries = [
            LedgerEntry(
                kind="donation",
                id=d.id,  # type: ignore[arg-type]  # persisted rows always have an id
                amount=d.amount.amount,
                label=d.note,
                created_at=d.created_at,  # type: ignore[arg-type]
            )
            for d in donations
        ] + [
            LedgerEntry(
                kind="expense",
                id=e.id,  # type: ignore[arg-type]
                amount=e.amount.amount,
                label=e.description,
                created_at=e.created_at,  # type: ignore[arg-type]
            )
            for e in expenses
        ]
        entries.sort(key=lambda entry: entry.created_at, reverse=True)
        return entries[:limit]
