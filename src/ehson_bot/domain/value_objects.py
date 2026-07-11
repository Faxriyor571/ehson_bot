"""Immutable value objects shared by domain entities."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal

from ehson_bot.domain.exceptions import InvalidDonationAmount


@dataclass(frozen=True, slots=True)
class Money:
    """A positive monetary amount. Currency is implicitly UZS (so'm) for v1."""

    amount: Decimal

    def __post_init__(self) -> None:
        if self.amount <= 0:
            raise InvalidDonationAmount(f"Amount must be positive, got {self.amount}")

    def __add__(self, other: Money) -> Money:
        return Money(self.amount + other.amount)

    def __str__(self) -> str:
        return f"{self.amount:,.0f}"


@dataclass(frozen=True, slots=True)
class PoolSnapshot:
    """Donations vs. usage over some period, and the resulting balance."""

    donations_total: Decimal
    expenses_total: Decimal

    @property
    def balance(self) -> Decimal:
        return self.donations_total - self.expenses_total


@dataclass(frozen=True, slots=True)
class LedgerEntry:
    """A merged, display-only view of one donation or expense row.

    Exists only so the "recent entries" screen can show a single
    chronological list without either ledger knowing about the other.
    """

    kind: Literal["donation", "expense"]
    id: int
    amount: Decimal
    label: str | None
    created_at: datetime
