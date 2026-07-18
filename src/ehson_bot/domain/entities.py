"""Aggregate root(s) of the donation ledger."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from ehson_bot.domain.exceptions import InvalidExpenseDescription
from ehson_bot.domain.value_objects import Money


class Role(str, Enum):
    """A bot user's permission level. Ordered lowest to highest trust.

    PENDING is the default for anyone who has never been approved by a
    Super Admin — they have no access at all until approved. There is no
    separate "regular member" tier: approving someone grants TREASURER
    directly, since every approved member of this small, trusted group
    (only a handful of people) is trusted both to donate on their own
    say-so and to record expenses.
    """

    PENDING = "pending"
    TREASURER = "treasurer"
    SUPER_ADMIN = "super_admin"


@dataclass(slots=True)
class BotUser:
    """Anyone who has ever pressed /start. Identity here is fine — this is
    about *who operates the bot*, never about who donated.

    ``anonymous_name`` is a self-chosen (or randomly assigned) nickname used
    only to personalize messages sent directly back to this person and in
    the anonymous donation announcement — never their real Telegram name or
    username, and never shown alongside any identifying information.
    """

    telegram_id: int
    role: Role
    display_name: str | None = None
    anonymous_name: str | None = None
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
    ``receipt_file_id`` is an optional transfer screenshot the donor
    attached — visible only to Super Admins, never in a group/channel or on
    any statistics screen.
    """

    amount: Money
    recorded_by: TreasurerId
    id: int | None = None
    note: str | None = None
    receipt_file_id: str | None = None
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
    """The single, Super-Admin-managed donation account, shown to everyone.

    Structured fields (not one free-text blob) so the display screen can
    format each one consistently — e.g. the card number rendered as
    tap-to-copy — instead of showing back whatever an admin once typed.
    """

    card_number: str
    card_holder: str
    bank_name: str
    updated_at: datetime | None = None
