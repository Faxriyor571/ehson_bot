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
    PaymentSession,
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


class PaymentSessionRepository(Protocol):
    """Persistence port for payment attempts — the operational record of a
    payment, kept separate from the anonymous ``Donation`` it may produce.
    """

    async def add(self, session: PaymentSession) -> PaymentSession:
        """Persist a new PENDING session and return it with id populated."""
        ...

    async def get(self, provider_session_id: str) -> PaymentSession | None: ...

    async def mark_paid(self, provider_session_id: str, donation_id: int) -> PaymentSession | None:
        """Transition PENDING -> PAID, link the resulting donation, and scrub
        ``donor_telegram_id`` — the correlation has served its purpose.
        Returns None if no such session exists.
        """
        ...

    async def mark_cancelled(self, provider_session_id: str) -> PaymentSession | None:
        """Transition PENDING -> CANCELLED. Returns None if no such session exists."""
        ...


class PaymentProvider(Protocol):
    """A payment gateway adapter. ``MockPaymentProvider`` is the only
    implementation for now; a real provider (Click/Payme) will also need
    webhook-signature verification, which is an HTTP-layer concern added
    alongside that real integration, not speculatively defined here first.
    """

    display_name: str
    """Human-readable label shown on the donor-facing confirmation screen
    before a session is created (e.g. "Click", "Payme") — never the raw
    provider identifier stored on ``PaymentSession.provider``.
    """

    async def create_payment(self, amount: Decimal, donor_telegram_id: int) -> PaymentSession:
        """Start a payment attempt and return the PENDING session, including
        wherever the caller should send the donor to pay.
        """
        ...
