"""Ports: contracts the domain/application need from persistence.

No implementation lives here — see ``infrastructure/db/repositories.py``
for the SQLAlchemy adapter that fulfils this contract.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Protocol

from ehson_bot.domain.entities import (
    BankAccountInfo,
    BotUser,
    Donation,
    Expense,
    Role,
)


class DonationRepository(Protocol):
    """Persistence port for the donation ledger."""

    async def add(self, donation: Donation) -> Donation:
        """Persist a new donation and return it with id/created_at populated."""
        ...

    async def get(self, donation_id: int) -> Donation | None: ...

    async def remove(self, donation_id: int) -> bool:
        """Delete a donation by id. Returns False if it did not exist."""
        ...

    async def list_recent(self, limit: int) -> list[Donation]: ...

    async def sum_since(self, start: datetime | None) -> Decimal:
        """Sum of amounts with ``created_at >= start``, or all-time if ``start`` is None."""
        ...

    async def count_since(self, start: datetime | None) -> int:
        """Count of entries with ``created_at >= start``, or all-time if ``start`` is None."""
        ...


class ExpenseRepository(Protocol):
    """Persistence port for the usage/expense ledger."""

    async def add(self, expense: Expense) -> Expense:
        """Persist a new expense and return it with id/created_at populated."""
        ...

    async def get(self, expense_id: int) -> Expense | None: ...

    async def remove(self, expense_id: int) -> bool:
        """Delete an expense by id. Returns False if it did not exist."""
        ...

    async def list_recent(self, limit: int) -> list[Expense]: ...

    async def list_since(self, start: datetime) -> list[Expense]:
        """All expenses with ``created_at >= start``, oldest first.

        Unlike ``list_recent``, this is unbounded by count — used where every
        entry in a period matters (e.g. the daily report's usage list).
        """
        ...

    async def sum_since(self, start: datetime | None) -> Decimal:
        """Sum of amounts with ``created_at >= start``, or all-time if ``start`` is None."""
        ...

    async def count_since(self, start: datetime | None) -> int:
        """Count of entries with ``created_at >= start``, or all-time if ``start`` is None."""
        ...


class BotUserRepository(Protocol):
    """Persistence port for bot operators (not donors — donors are never stored)."""

    async def get(self, telegram_id: int) -> BotUser | None: ...

    async def upsert(self, telegram_id: int, display_name: str | None) -> BotUser:
        """Register a user on first contact, or refresh their display name.

        A newly-registered user gets ``Role.PENDING`` — never changes an
        existing user's role, and never grants any role above PENDING by
        itself. Role changes only happen via ``set_role``.
        """
        ...

    async def set_role(self, telegram_id: int, role: Role) -> BotUser | None:
        """Change a known user's role. Returns None if the user doesn't exist."""
        ...

    async def set_anonymous_name(self, telegram_id: int, anonymous_name: str) -> BotUser | None:
        """Set this person's self-chosen (or randomly assigned) nickname.
        Returns None if the user doesn't exist.
        """
        ...

    async def list_by_role(self, role: Role) -> list[BotUser]: ...

    async def list_approved(self) -> list[BotUser]:
        """Every user whose role is not PENDING — who should receive reports."""
        ...


class BankAccountRepository(Protocol):
    """Persistence port for the single, Super-Admin-managed donation account."""

    async def get(self) -> BankAccountInfo | None:
        """Returns None if no Super Admin has configured it yet."""
        ...

    async def set(self, card_number: str, card_holder: str, bank_name: str) -> BankAccountInfo: ...
