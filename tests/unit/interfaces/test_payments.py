"""Unit tests for payments.py's pure donation-announcement formatting."""
from __future__ import annotations

from ehson_bot.interfaces.telegram.handlers.payments import _donation_announcement_text


def test_announcement_includes_named_donor_line_amount_and_totals() -> None:
    text = _donation_announcement_text(
        donor_line="🌙 QalbNuri ehson qildi!",
        amount="50,000 so'm",
        today_total="450,000 so'm",
        balance="3,820,000 so'm",
    )

    assert text.startswith("🌙 QalbNuri ehson qildi!")
    assert "💰 +50,000 so'm" in text
    assert "450,000 so'm" in text
    assert "3,820,000 so'm" in text
    assert "Alloh" in text


def test_announcement_supports_anonymous_fallback_donor_line() -> None:
    text = _donation_announcement_text(
        donor_line="🤲 Mahfiy inson ehson qildi!",
        amount="10,000 so'm",
        today_total="10,000 so'm",
        balance="10,000 so'm",
    )

    assert text.startswith("🤲 Mahfiy inson ehson qildi!")
