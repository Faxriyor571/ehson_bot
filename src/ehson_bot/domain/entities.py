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
    directly, since donation-taking no longer depends on role (the payment
    provider's confirmation is what protects it) and every approved member
    of this small, trusted group is also trusted to record expenses.
    """

    PENDING = "pending"
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
    """The single, Super-Admin-managed donation account, shown to everyone.

    Structured fields (not one free-text blob) so the display screen can
    format each one consistently — e.g. the card number rendered as
    tap-to-copy — instead of showing back whatever an admin once typed.
    """

    card_number: str
    card_holder: str
    bank_name: str
    updated_at: datetime | None = None


class PaymentStatus(str, Enum):
    """Lifecycle of one payment attempt, tracked independently of whether
    it ever becomes a ``Donation``."""

    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class PaymentSession:
    """One donor's attempt to pay through a provider (mock today, a real
    gateway later) — the operational record of a payment, not the donation
    itself.

    ``donor_telegram_id`` exists only to know who to thank and to route the
    confirmation message. It is a *transient* correlation: the moment this
    session leaves PENDING, the caller must clear it — this row is the
    audit trail of "a payment happened and what it became", not a permanent
    donor-to-donation link. The resulting ``Donation`` never carries it.
    """

    provider_session_id: str
    amount: Money
    provider: str
    id: int | None = None
    donor_telegram_id: int | None = None
    status: PaymentStatus = PaymentStatus.PENDING
    donation_id: int | None = None
    created_at: datetime | None = None
    confirmed_at: datetime | None = None
    # Never persisted (no DB column): a checkout link only makes sense in the
    # moment a provider issues it. Round-tripping through the repository
    # (add/get/mark_paid/mark_cancelled) always yields None here.
    pay_url: str | None = None
