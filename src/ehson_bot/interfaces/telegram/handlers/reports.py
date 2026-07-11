"""Reports available to every bot user: statistics, balance, donation account.

Unlike ``admin``/``donations``, this router has no role filter — Users are
explicitly allowed to view reports, statistics, balance, and the donation
account per the spec.
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from ehson_bot.application.use_cases.get_period_report import GetPeriodReportUseCase, Period
from ehson_bot.domain.value_objects import PoolSnapshot
from ehson_bot.infrastructure.db.repositories import (
    SqlAlchemyBankAccountRepository,
    SqlAlchemyDonationRepository,
    SqlAlchemyExpenseRepository,
)
from ehson_bot.interfaces.telegram.common import show_main_menu
from ehson_bot.interfaces.telegram.keyboards import (
    BTN_ACCOUNT,
    BTN_BACK,
    BTN_BALANCE,
    BTN_PERIOD_ALL,
    BTN_PERIOD_MONTH,
    BTN_PERIOD_TODAY,
    BTN_PERIOD_YEAR,
    BTN_STATS,
    stats_menu,
)

router = Router(name="reports")

_PERIOD_LABELS = {
    Period.TODAY: "Bugungi",
    Period.MONTH: "Shu oylik",
    Period.YEAR: "Shu yillik",
    Period.ALL: "Umumiy",
}


def _format_snapshot(label: str, snapshot: PoolSnapshot) -> str:
    return (
        f"<b>{label} hisobot</b>\n\n"
        f"Ehsonlar: {snapshot.donations_total:,.0f} so'm\n"
        f"Xarajatlar: {snapshot.expenses_total:,.0f} so'm\n"
        f"Balans: {snapshot.balance:,.0f} so'm"
    )


async def _snapshot(session: AsyncSession, period: Period) -> PoolSnapshot:
    use_case = GetPeriodReportUseCase(
        SqlAlchemyDonationRepository(session), SqlAlchemyExpenseRepository(session)
    )
    return await use_case.execute(period)


@router.message(F.text == BTN_STATS)
async def open_stats(message: Message) -> None:
    await message.answer("Qaysi davr uchun ko'rsataman?", reply_markup=stats_menu())


async def _reply_with_period(message: Message, session: AsyncSession, period: Period) -> None:
    snapshot = await _snapshot(session, period)
    await message.answer(_format_snapshot(_PERIOD_LABELS[period], snapshot))


@router.message(F.text == BTN_PERIOD_TODAY)
async def stats_today(message: Message, session: AsyncSession) -> None:
    await _reply_with_period(message, session, Period.TODAY)


@router.message(F.text == BTN_PERIOD_MONTH)
async def stats_month(message: Message, session: AsyncSession) -> None:
    await _reply_with_period(message, session, Period.MONTH)


@router.message(F.text == BTN_PERIOD_YEAR)
async def stats_year(message: Message, session: AsyncSession) -> None:
    await _reply_with_period(message, session, Period.YEAR)


@router.message(F.text == BTN_PERIOD_ALL)
async def stats_all(message: Message, session: AsyncSession) -> None:
    await _reply_with_period(message, session, Period.ALL)


@router.message(F.text == BTN_BALANCE)
async def show_balance(message: Message, session: AsyncSession) -> None:
    snapshot = await _snapshot(session, Period.ALL)
    await message.answer(f"<b>Joriy balans:</b> {snapshot.balance:,.0f} so'm")


@router.message(F.text == BTN_ACCOUNT)
async def show_account(message: Message, session: AsyncSession) -> None:
    account = await SqlAlchemyBankAccountRepository(session).get()
    text = account.text if account else "Hisob raqami hali sozlanmagan."
    await message.answer(f"<b>Hisob raqami:</b>\n{text}")


@router.message(StateFilter(None), F.text == BTN_BACK)
async def back_to_main(message: Message, session: AsyncSession) -> None:
    """The one generic "back to main menu" handler, shared by every submenu.

    Scoped to "no active FSM state" so it never intercepts a Back keypress
    that a role-specific flow (donation/expense entry, treasurer management)
    needs to handle itself for its own state cleanup — those flows don't
    offer a Back button anyway, only Cancel, but this keeps a stray manual
    keypress from leaving a flow's state dangling.
    """
    await show_main_menu(message, session)
