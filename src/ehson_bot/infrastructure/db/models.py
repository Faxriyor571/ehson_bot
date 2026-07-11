"""SQLAlchemy ORM models — the persistence schema.

Deliberately separate from ``ehson_bot.domain.entities.Donation``: the ORM
model is an infrastructure concern (table layout, column types) and must
never leak into the domain. ``DonationRow`` has, and can only ever have, the
columns declared below — there is no donor-identifying column to add by
accident.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, Numeric, String, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from ehson_bot.domain.entities import Role
from ehson_bot.infrastructure.db.base import Base

_RoleType = SQLEnum(
    Role,
    name="role",
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
    native_enum=False,
    length=20,
)


class DonationRow(Base):
    __tablename__ = "donations"

    id: Mapped[int] = mapped_column(primary_key=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # BigInteger: current Telegram user IDs already exceed Postgres's 32-bit
    # INTEGER range (~2.1B).
    recorded_by_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class BotUserRow(Base):
    __tablename__ = "bot_users"

    # autoincrement=False: this is the Telegram user's actual id, always
    # supplied explicitly on insert — never a generated sequence value.
    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    role: Mapped[Role] = mapped_column(_RoleType, nullable=False, default=Role.USER)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ExpenseRow(Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    recorded_by_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    receipt_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class BankAccountSettingsRow(Base):
    """A deliberate singleton: always exactly one row, ``id=1``."""

    __tablename__ = "bank_account_settings"

    # autoincrement=False: always inserted as id=1 explicitly, never generated.
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    text: Mapped[str] = mapped_column(String(1000), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
