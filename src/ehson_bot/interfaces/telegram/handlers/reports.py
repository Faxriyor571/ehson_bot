"""Reports available to every *approved* bot user: statistics, balance,
usage history, and a read-only view of recent donation/expense entries.

Gated by ``IsTreasurerOrAbove`` — a PENDING (not-yet-approved) caller must
not see any of this, per the bot's private-by-default access model. There is
no separate donor-only tier: TREASURER is the lowest approved rank, and
today it means exactly "approved member" — view and donate, nothing more.
Recording/editing/deleting entries and everything else administrative is
Super-Admin-only (``handlers/donations.py``, ``handlers/admin.py``).
"""
from __future__ import annotations

from decimal import Decimal

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from ehson_bot.application.use_cases.get_period_report import GetPeriodReportUseCase, Period
from ehson_bot.application.use_cases.list_recent_entries import ListRecentEntriesUseCase
from ehson_bot.domain.entities import Role
from ehson_bot.domain.value_objects import PoolSnapshot
from ehson_bot.infrastructure.db.repositories import (
    SqlAlchemyDonationRepository,
    SqlAlchemyExpenseRepository,
)
from ehson_bot.interfaces.telegram.common import esc, show_main_menu
from ehson_bot.interfaces.telegram.filters import IsTreasurerOrAbove
from ehson_bot.interfaces.telegram.handlers.start import help_text, role_of
from ehson_bot.interfaces.telegram.keyboards import (
    BTN_BACK,
    BTN_BALANCE,
    BTN_HELP,
    BTN_PERIOD_ALL,
    BTN_PERIOD_MONTH,
    BTN_PERIOD_TODAY,
    BTN_PERIOD_YEAR,
    BTN_RECENT,
    BTN_STATS,
    BTN_USAGE_HISTORY,
    recent_entries_menu,
    stats_menu,
)

USAGE_HISTORY_LIMIT = 20

router = Router(name="reports")
router.message.filter(IsTreasurerOrAbove())

_PERIOD_LABELS = {
    Period.TODAY: "Bugungi",
    Period.MONTH: "Shu oylik",
    Period.YEAR: "Shu yillik",
    Period.ALL: "Umumiy",
}


def _format_snapshot(label: str, snapshot: PoolSnapshot, current_balance: Decimal) -> str:
    """``current_balance`` is always the true all-time balance — never the
    period's own net — so this never repeats the bug where a period's net
    change got shown to users labeled as "the balance".
    """
    return (
        f"<b>{label} hisobot</b>\n\n"
        f"Ehsonlar: {snapshot.donations_total:,.0f} so'm ({snapshot.donations_count} ta)\n"
        f"Xarajatlar: {snapshot.expenses_total:,.0f} so'm ({snapshot.expenses_count} ta)\n\n"
        f"💰 Joriy balans: {current_balance:,.0f} so'm"
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
    if period is Period.ALL:
        current_balance = snapshot.balance
    else:
        current_balance = (await _snapshot(session, Period.ALL)).balance
    await message.answer(_format_snapshot(_PERIOD_LABELS[period], snapshot, current_balance))


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
    all_time = await _snapshot(session, Period.ALL)
    today = await _snapshot(session, Period.TODAY)
    await message.answer(
        "<b>💰 Balans</b>\n\n"
        f"Joriy balans: {all_time.balance:,.0f} so'm\n\n"
        f"📆 Bugungi ehsonlar: {today.donations_total:,.0f} so'm\n"
        f"📆 Bugungi xarajat: {today.expenses_total:,.0f} so'm\n"
        f"📆 Bugungi qoldiq: {today.balance:,.0f} so'm"
    )


@router.message(F.text == BTN_USAGE_HISTORY)
async def show_usage_history(message: Message, session: AsyncSession) -> None:
    """Read-only: what the money was used for."""
    expenses = await SqlAlchemyExpenseRepository(session).list_recent(USAGE_HISTORY_LIMIT)
    if not expenses:
        await message.answer("Hozircha xarajatlar yo'q.")
        return

    lines = [
        f"{e.amount} so'm — {esc(e.description)} — {e.created_at:%Y-%m-%d}"
        for e in expenses
        if e.created_at is not None
    ]
    await message.answer("<b>Foydalanish tarixi:</b>\n" + "\n".join(lines))


@router.message(F.text == BTN_RECENT)
async def show_recent_entries(message: Message, session: AsyncSession) -> None:
    """Read-only for everyone here. The delete affordance (and the ability
    to act on it) only appears for Super Admin — recording/editing/deleting
    financial entries is administrative, not something an ordinary approved
    member does, even though they can see the same list.
    """
    if message.from_user is None:
        return
    use_case = ListRecentEntriesUseCase(
        SqlAlchemyDonationRepository(session), SqlAlchemyExpenseRepository(session)
    )
    entries = await use_case.execute()

    if not entries:
        text = "Hozircha yozuvlar yo'q."
    else:
        lines = []
        for entry in entries:
            tag = "D" if entry.kind == "donation" else "X"
            sign = "+" if entry.kind == "donation" else "-"
            when = entry.created_at.strftime("%Y-%m-%d %H:%M")
            label = f" ({esc(entry.label)})" if entry.label else ""
            lines.append(f"{tag}{entry.id} — {sign}{entry.amount:,.0f} so'm — {when}{label}")
        text = "<b>Oxirgi yozuvlar:</b>\n" + "\n".join(lines)

    role = await role_of(session, message.from_user.id)
    await message.answer(
        text, reply_markup=recent_entries_menu(can_delete=role is Role.SUPER_ADMIN)
    )


@router.message(F.text == BTN_HELP)
async def show_help(message: Message, session: AsyncSession) -> None:
    if message.from_user is None:
        return
    role = await role_of(session, message.from_user.id)
    await message.answer(help_text(role))


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
