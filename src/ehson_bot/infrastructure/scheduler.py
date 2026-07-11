"""Daily 23:59 broadcast: today's donations, today's usage, and the balance.

Every registered bot user gets this report (not just Treasurers/Super
Admin) — the spec calls for it to reach "every user".
"""
from __future__ import annotations

import logging
from decimal import Decimal

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from ehson_bot.application.use_cases.get_period_report import GetPeriodReportUseCase, Period
from ehson_bot.domain.value_objects import PoolSnapshot
from ehson_bot.infrastructure.config import settings
from ehson_bot.infrastructure.db.repositories import (
    SqlAlchemyBotUserRepository,
    SqlAlchemyDonationRepository,
    SqlAlchemyExpenseRepository,
)
from ehson_bot.infrastructure.db.session import get_session
from ehson_bot.infrastructure.timeutil import start_of_today

logger = logging.getLogger("ehson_bot.scheduler")


def format_daily_report(
    today: PoolSnapshot, current_balance: Decimal, expense_descriptions: list[str]
) -> str:
    """``today`` is the day's donations/expenses; ``current_balance`` is the
    all-time running balance — these are deliberately different periods
    (the daily total is not the running balance).
    """
    usage_lines = (
        "\n".join(f"• {description}" for description in expense_descriptions)
        if expense_descriptions
        else "— bugun sarf bo'lmagan"
    )
    return (
        "<b>Kunlik hisobot</b>\n\n"
        f"Bugungi ehsonlar: {today.donations_total:,.0f} so'm\n"
        f"Bugungi xarajat: {today.expenses_total:,.0f} so'm\n"
        f"Joriy balans: {current_balance:,.0f} so'm\n\n"
        f"Bugungi sarf:\n{usage_lines}"
    )


async def _build_daily_report_text() -> str:
    async with get_session() as session:
        donation_repo = SqlAlchemyDonationRepository(session)
        expense_repo = SqlAlchemyExpenseRepository(session)
        use_case = GetPeriodReportUseCase(donation_repo, expense_repo)

        today_snapshot = await use_case.execute(Period.TODAY)
        # The running balance must be all-time, not today's net change.
        all_time_snapshot = await use_case.execute(Period.ALL)
        today_expenses = await expense_repo.list_since(start_of_today())

    return format_daily_report(
        today_snapshot,
        all_time_snapshot.balance,
        [expense.description for expense in today_expenses],
    )


async def broadcast(bot: Bot, telegram_ids: list[int], text: str) -> None:
    """Send ``text`` to each id, skipping (not failing the job on) blocked users."""
    for telegram_id in telegram_ids:
        try:
            await bot.send_message(telegram_id, text)
        except TelegramForbiddenError:
            logger.info("Skipping daily report for %s: bot was blocked", telegram_id)


async def send_daily_report(bot: Bot) -> None:
    text = await _build_daily_report_text()

    async with get_session() as session:
        # Not list_all(): a PENDING (not-yet-approved) user gets no reports.
        users = await SqlAlchemyBotUserRepository(session).list_approved()

    await broadcast(bot, [user.telegram_id for user in users], text)


def build_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=settings.timezone)
    scheduler.add_job(
        send_daily_report,
        trigger=CronTrigger(hour=23, minute=59),
        args=[bot],
        id="daily_report",
    )
    return scheduler
