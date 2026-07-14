"""Unit tests for MockPaymentProvider's message formatting.

Mirrors the approach in ``test_scheduler.py``: the text-building logic is
pure and tested directly, without touching the DB or the Bot API.
"""
from __future__ import annotations

from decimal import Decimal

from ehson_bot.domain.value_objects import Money
from ehson_bot.infrastructure.payments.mock_provider import (
    admin_notification_text,
    donor_thank_you_text,
)


def test_donor_thank_you_text_includes_amount_and_blessing() -> None:
    text = donor_thank_you_text(Money(Decimal(75000)))

    assert "75,000" in text
    assert text.startswith("✅ Ehson qilganingiz uchun rahmat!")
    assert "Alloh" in text


def test_admin_notification_text_includes_amount() -> None:
    text = admin_notification_text(Money(Decimal(200000)))

    assert "200,000" in text
