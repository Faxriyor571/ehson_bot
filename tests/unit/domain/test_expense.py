"""Unit tests for Expense's business rule: description is mandatory."""
from __future__ import annotations

from decimal import Decimal

import pytest

from ehson_bot.domain.entities import Expense, TreasurerId
from ehson_bot.domain.exceptions import InvalidExpenseDescription
from ehson_bot.domain.value_objects import Money


def test_expense_rejects_empty_description() -> None:
    with pytest.raises(InvalidExpenseDescription):
        Expense(amount=Money(Decimal(1000)), description="   ", recorded_by=TreasurerId(1))


def test_expense_accepts_non_empty_description() -> None:
    expense = Expense(amount=Money(Decimal(1000)), description="Ovqat", recorded_by=TreasurerId(1))

    assert expense.description == "Ovqat"
