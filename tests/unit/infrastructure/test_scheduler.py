"""Unit tests for the daily-report formatting and broadcast logic.

These avoid touching the DB or Telegram — ``_build_daily_report_text`` and
``send_daily_report`` (which open a real session / call the Bot API) are
exercised instead via a manual run, per the project's verification plan.
"""
from __future__ import annotations

from decimal import Decimal

from aiogram.exceptions import TelegramForbiddenError

from ehson_bot.domain.value_objects import PoolSnapshot
from ehson_bot.infrastructure.scheduler import broadcast, format_daily_report


def test_format_daily_report_lists_each_expense() -> None:
    snapshot = PoolSnapshot(donations_total=Decimal(500000), expenses_total=Decimal(200000))

    text = format_daily_report(snapshot, ["Tibbiy yordam", "Oziq-ovqat"])

    assert "500,000" in text
    assert "200,000" in text
    assert "300,000" in text  # balance
    assert "• Tibbiy yordam" in text
    assert "• Oziq-ovqat" in text


def test_format_daily_report_handles_no_expenses() -> None:
    snapshot = PoolSnapshot(donations_total=Decimal(0), expenses_total=Decimal(0))

    text = format_daily_report(snapshot, [])

    assert "bugun sarf bo'lmagan" in text


class FakeBot:
    def __init__(self, blocked_ids: set[int]) -> None:
        self.blocked_ids = blocked_ids
        self.sent_to: list[int] = []

    async def send_message(self, chat_id: int, text: str) -> None:
        if chat_id in self.blocked_ids:
            raise TelegramForbiddenError(method=None, message="bot was blocked by the user")  # type: ignore[arg-type]
        self.sent_to.append(chat_id)


async def test_broadcast_skips_users_who_blocked_the_bot() -> None:
    bot = FakeBot(blocked_ids={2})

    await broadcast(bot, [1, 2, 3], "hisobot")  # type: ignore[arg-type]

    assert bot.sent_to == [1, 3]
