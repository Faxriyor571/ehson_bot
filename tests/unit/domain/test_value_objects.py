"""Unit tests for domain value objects (no DB, no I/O)."""
from __future__ import annotations

from decimal import Decimal

import pytest

from ehson_bot.domain.exceptions import InvalidDonationAmount
from ehson_bot.domain.value_objects import Money


def test_money_rejects_non_positive_amounts() -> None:
    with pytest.raises(InvalidDonationAmount):
        Money(Decimal(0))
    with pytest.raises(InvalidDonationAmount):
        Money(Decimal(-1))


def test_money_addition_combines_amounts() -> None:
    total = Money(Decimal(1000)) + Money(Decimal(500))

    assert total.amount == Decimal(1500)


def test_money_str_formats_with_thousands_separator() -> None:
    assert str(Money(Decimal(1500000))) == "1,500,000"
