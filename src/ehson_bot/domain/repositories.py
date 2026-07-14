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
    PendingPayment,
    PendingPaymentStatus,
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


class PendingPaymentRepository(Protocol):
    """Persistence port for donor-submitted payment claims — kept separate
    from the anonymous ``Donation`` a claim may produce. The Super Admin
    interface must only ever read a ``PendingPayment`` via
    ``reference_code`` or ``list_pending`` — never a method keyed on
    ``donor_telegram_id``, since that would make it possible to build a
    donor-facing lookup screen by accident.
    """

    async def add(self, payment: PendingPayment) -> PendingPayment:
        """Persist a new PENDING claim and return it with id populated."""
        ...

    async def get_by_reference(self, reference_code: str) -> PendingPayment | None: ...

    async def list_pending(self) -> list[PendingPayment]:
        """Every claim still awaiting a Super Admin decision, oldest first."""
        ...

    async def try_claim(
        self, reference_code: str, decision: PendingPaymentStatus
    ) -> PendingPayment | None:
        """Atomically transition PENDING -> ``decision`` (CONFIRMED or
        REJECTED) and scrub ``donor_telegram_id`` — a single conditional
        write (``WHERE status = 'pending'``), not a read-then-write, so two
        Super Admins racing to decide the same reference code can never both
        win. Returns the claim as it stood immediately before the scrub (so
        the caller can still route a private message) if this call won the
        race; returns None if the claim doesn't exist or someone else
        already decided it — a safe, idempotent no-op for the loser.
        """
        ...

    async def attach_donation(self, reference_code: str, donation_id: int) -> None:
        """Links the resulting donation to an already-CONFIRMED claim. Only
        ever called after ``try_claim`` has won the race for this code —
        by then no concurrent caller can interfere, so this step needs no
        guard of its own.
        """
        ...
