"""Aggregate root(s) of the donation ledger."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from ehson_bot.domain.exceptions import InvalidExpenseDescription
from ehson_bot.domain.value_objects import Money


class Role(str, Enum):
    """A bot user's permission level. Ordered lowest to highest trust."""

    USER = "user"
    TREASURER = "treasurer"
    SUPER_ADMIN = "super_admin"


@dataclass(slots=True)
class BotUser:
    """Anyone who has ever pressed /start. Identity here is fine — this is
    about *who operates the bot*, never about who donated.
    """

    telegram_id: int
    role: Role
    display_name: str | None = None
    joined_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class TreasurerId:
    """Identifies who *recorded* an entry — never the donor.

    Wrapping the raw int keeps the domain from caring that, today, this
    happens to be a Telegram user id; it is just "the operator's identity"
    as far as business rules are concerned.
    """

    value: int


@dataclass(slots=True)
class Donation:
    """A single anonymous contribution to the shared pool.

    Deliberately has no donor-identifying field: anonymity is a structural
    property of this entity, not something enforced by hiding a field later.
    """

    amount: Money
    recorded_by: TreasurerId
    id: int | None = None
    note: str | None = None
    created_at: datetime | None = None


@dataclass(slots=True)
class Expense:
    """A confirmed use of pooled funds — the counterpart to ``Donation``.

    ``description`` is mandatory (unlike a donation's optional note): the
    whole point of transparency here is that everyone can see where money
    went, so an expense with no description is not a valid expense.
    """

    amount: Money
    description: str
    recorded_by: TreasurerId
    id: int | None = None
    receipt_file_id: str | None = None
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.description.strip():
            raise InvalidExpenseDescription("An expense must have a non-empty description")


@dataclass(frozen=True, slots=True)
class BankAccountInfo:
    """The single, Super-Admin-managed donation account, shown to everyone."""

    text: str
    updated_at: datetime | None = None
