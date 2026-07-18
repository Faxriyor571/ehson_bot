"""Adapter: implements ``domain.repositories.DonationRepository`` with SQLAlchemy."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ehson_bot.domain.entities import (
    BankAccountInfo,
    BotUser,
    Donation,
    Expense,
    Role,
    TreasurerId,
)
from ehson_bot.domain.value_objects import Money
from ehson_bot.infrastructure.db.models import (
    BankAccountSettingsRow,
    BotUserRow,
    DonationRow,
    ExpenseRow,
)

_BANK_ACCOUNT_ROW_ID = 1


def _to_domain(row: DonationRow) -> Donation:
    return Donation(
        id=row.id,
        amount=Money(row.amount),
        recorded_by=TreasurerId(row.recorded_by_id),
        note=row.note,
        receipt_file_id=row.receipt_file_id,
        created_at=row.created_at,
    )


def _expense_to_domain(row: ExpenseRow) -> Expense:
    return Expense(
        id=row.id,
        amount=Money(row.amount),
        description=row.description,
        recorded_by=TreasurerId(row.recorded_by_id),
        receipt_file_id=row.receipt_file_id,
        created_at=row.created_at,
    )


def _user_to_domain(row: BotUserRow) -> BotUser:
    return BotUser(
        telegram_id=row.telegram_id,
        role=Role(row.role),
        display_name=row.display_name,
        anonymous_name=row.anonymous_name,
        joined_at=row.joined_at,
    )


class SqlAlchemyDonationRepository:
    """Satisfies ``DonationRepository`` structurally (via ``Protocol``)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, donation: Donation) -> Donation:
        row = DonationRow(
            amount=donation.amount.amount,
            note=donation.note,
            receipt_file_id=donation.receipt_file_id,
            recorded_by_id=donation.recorded_by.value,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return _to_domain(row)

    async def get(self, donation_id: int) -> Donation | None:
        row = await self._session.get(DonationRow, donation_id)
        return _to_domain(row) if row is not None else None

    async def remove(self, donation_id: int) -> bool:
        row = await self._session.get(DonationRow, donation_id)
        if row is None:
            return False
        await self._session.delete(row)
        await self._session.commit()
        return True

    async def list_recent(self, limit: int) -> list[Donation]:
        stmt = select(DonationRow).order_by(DonationRow.created_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return [_to_domain(row) for row in result.scalars().all()]

    async def sum_since(self, start: datetime | None) -> Decimal:
        stmt = select(func.coalesce(func.sum(DonationRow.amount), 0))
        if start is not None:
            stmt = stmt.where(DonationRow.created_at >= start)
        return (await self._session.execute(stmt)).scalar_one()

    async def count_since(self, start: datetime | None) -> int:
        stmt = select(func.count(DonationRow.id))
        if start is not None:
            stmt = stmt.where(DonationRow.created_at >= start)
        return (await self._session.execute(stmt)).scalar_one()


class SqlAlchemyExpenseRepository:
    """Satisfies ``ExpenseRepository`` structurally (via ``Protocol``)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, expense: Expense) -> Expense:
        row = ExpenseRow(
            amount=expense.amount.amount,
            description=expense.description,
            recorded_by_id=expense.recorded_by.value,
            receipt_file_id=expense.receipt_file_id,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return _expense_to_domain(row)

    async def get(self, expense_id: int) -> Expense | None:
        row = await self._session.get(ExpenseRow, expense_id)
        return _expense_to_domain(row) if row is not None else None

    async def remove(self, expense_id: int) -> bool:
        row = await self._session.get(ExpenseRow, expense_id)
        if row is None:
            return False
        await self._session.delete(row)
        await self._session.commit()
        return True

    async def list_recent(self, limit: int) -> list[Expense]:
        stmt = select(ExpenseRow).order_by(ExpenseRow.created_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return [_expense_to_domain(row) for row in result.scalars().all()]

    async def list_since(self, start: datetime) -> list[Expense]:
        stmt = (
            select(ExpenseRow)
            .where(ExpenseRow.created_at >= start)
            .order_by(ExpenseRow.created_at)
        )
        result = await self._session.execute(stmt)
        return [_expense_to_domain(row) for row in result.scalars().all()]

    async def sum_since(self, start: datetime | None) -> Decimal:
        stmt = select(func.coalesce(func.sum(ExpenseRow.amount), 0))
        if start is not None:
            stmt = stmt.where(ExpenseRow.created_at >= start)
        return (await self._session.execute(stmt)).scalar_one()

    async def count_since(self, start: datetime | None) -> int:
        stmt = select(func.count(ExpenseRow.id))
        if start is not None:
            stmt = stmt.where(ExpenseRow.created_at >= start)
        return (await self._session.execute(stmt)).scalar_one()


class SqlAlchemyBotUserRepository:
    """Satisfies ``BotUserRepository`` structurally (via ``Protocol``)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, telegram_id: int) -> BotUser | None:
        row = await self._session.get(BotUserRow, telegram_id)
        return _user_to_domain(row) if row is not None else None

    async def upsert(self, telegram_id: int, display_name: str | None) -> BotUser:
        row = await self._session.get(BotUserRow, telegram_id)
        if row is None:
            row = BotUserRow(
                telegram_id=telegram_id, role=Role.PENDING, display_name=display_name
            )
            self._session.add(row)
        else:
            row.display_name = display_name
        await self._session.commit()
        await self._session.refresh(row)
        return _user_to_domain(row)

    async def set_role(self, telegram_id: int, role: Role) -> BotUser | None:
        row = await self._session.get(BotUserRow, telegram_id)
        if row is None:
            return None
        row.role = role
        await self._session.commit()
        await self._session.refresh(row)
        return _user_to_domain(row)

    async def set_anonymous_name(self, telegram_id: int, anonymous_name: str) -> BotUser | None:
        row = await self._session.get(BotUserRow, telegram_id)
        if row is None:
            return None
        row.anonymous_name = anonymous_name
        await self._session.commit()
        await self._session.refresh(row)
        return _user_to_domain(row)

    async def list_by_role(self, role: Role) -> list[BotUser]:
        stmt = (
            select(BotUserRow)
            .where(BotUserRow.role == role)
            .order_by(BotUserRow.joined_at)
        )
        result = await self._session.execute(stmt)
        return [_user_to_domain(row) for row in result.scalars().all()]

    async def list_approved(self) -> list[BotUser]:
        stmt = (
            select(BotUserRow)
            .where(BotUserRow.role != Role.PENDING)
            .order_by(BotUserRow.joined_at)
        )
        result = await self._session.execute(stmt)
        return [_user_to_domain(row) for row in result.scalars().all()]


class SqlAlchemyBankAccountRepository:
    """Satisfies ``BankAccountRepository`` structurally (via ``Protocol``)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self) -> BankAccountInfo | None:
        row = await self._session.get(BankAccountSettingsRow, _BANK_ACCOUNT_ROW_ID)
        if row is None:
            return None
        return BankAccountInfo(
            card_number=row.card_number,
            card_holder=row.card_holder,
            bank_name=row.bank_name,
            updated_at=row.updated_at,
        )

    async def set(self, card_number: str, card_holder: str, bank_name: str) -> BankAccountInfo:
        row = await self._session.get(BankAccountSettingsRow, _BANK_ACCOUNT_ROW_ID)
        if row is None:
            row = BankAccountSettingsRow(
                id=_BANK_ACCOUNT_ROW_ID,
                card_number=card_number,
                card_holder=card_holder,
                bank_name=bank_name,
            )
            self._session.add(row)
        else:
            row.card_number = card_number
            row.card_holder = card_holder
            row.bank_name = bank_name
        await self._session.commit()
        await self._session.refresh(row)
        return BankAccountInfo(
            card_number=row.card_number,
            card_holder=row.card_holder,
            bank_name=row.bank_name,
            updated_at=row.updated_at,
        )
