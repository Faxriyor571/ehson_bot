"""Super-Admin-only financial management: record expenses, view recent
donation/expense entries, correct a mistaken one by deleting it.

Donations are no longer recorded here — a member submits a claim through
``handlers/payments.py`` and a Super Admin manually verifies and confirms
it via ``handlers/admin.py``'s pending-payments review screen. Everything
in this module — recording, viewing itemized entries, editing, deleting —
is administrative and restricted to Super Admin; the persistent menu for
an ordinary approved member stays minimal (donate/balance/statistics only).

All multi-step input uses ReplyKeyboardMarkup + FSM (no slash commands) so
every step offers Cancel (and Skip where the field is optional), per the
bot's UX rules.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from ehson_bot.application.use_cases.list_recent_entries import ListRecentEntriesUseCase
from ehson_bot.application.use_cases.record_expense import RecordExpenseInput, RecordExpenseUseCase
from ehson_bot.application.use_cases.remove_donation import RemoveDonationUseCase
from ehson_bot.application.use_cases.remove_expense import RemoveExpenseUseCase
from ehson_bot.domain.exceptions import DomainError, DonationNotFound, ExpenseNotFound
from ehson_bot.infrastructure.db.repositories import (
    SqlAlchemyDonationRepository,
    SqlAlchemyExpenseRepository,
)
from ehson_bot.interfaces.telegram.common import esc, show_main_menu
from ehson_bot.interfaces.telegram.filters import IsSuperAdmin
from ehson_bot.interfaces.telegram.keyboards import (
    BTN_ADD_EXPENSE,
    BTN_CANCEL,
    BTN_CONFIRM,
    BTN_DELETE_ENTRY,
    BTN_RECENT,
    BTN_SKIP,
    cancel_only,
    confirm_cancel,
    recent_entries_menu,
    skip_or_cancel,
)
from ehson_bot.interfaces.telegram.states import ExpenseEntryStates, RemoveEntryStates

router = Router(name="donations")
router.message.filter(IsSuperAdmin())


def _parse_amount(text: str) -> Decimal | None:
    raw = text.replace(",", "").replace(" ", "").strip()
    try:
        value = Decimal(raw)
    except InvalidOperation:
        return None
    return value if value > 0 else None


# --------------------------------------------------------------------------
# Record an expense: amount -> required description -> optional receipt -> confirm
# --------------------------------------------------------------------------


@router.message(F.text == BTN_ADD_EXPENSE)
async def start_add_expense(message: Message, state: FSMContext) -> None:
    await state.set_state(ExpenseEntryStates.awaiting_amount)
    await message.answer(
        "Xarajat summasini kiriting (so'm). Masalan: 200000", reply_markup=cancel_only()
    )


@router.message(ExpenseEntryStates.awaiting_amount, F.text == BTN_CANCEL)
@router.message(ExpenseEntryStates.awaiting_description, F.text == BTN_CANCEL)
@router.message(ExpenseEntryStates.awaiting_receipt, F.text == BTN_CANCEL)
@router.message(ExpenseEntryStates.awaiting_confirm, F.text == BTN_CANCEL)
async def cancel_add_expense(message: Message, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    await message.answer("Bekor qilindi.")
    await show_main_menu(message, session)


@router.message(ExpenseEntryStates.awaiting_amount)
async def expense_amount_entered(message: Message, state: FSMContext) -> None:
    amount = _parse_amount(message.text or "")
    if amount is None:
        await message.answer("Summa noto'g'ri. Masalan: 200000")
        return
    await state.update_data(amount=str(amount))
    await state.set_state(ExpenseEntryStates.awaiting_description)
    await message.answer(
        "Xarajat nimaga ishlatilganini yozing (majburiy). Masalan: Tibbiy yordam",
        reply_markup=cancel_only(),
    )


@router.message(ExpenseEntryStates.awaiting_description)
async def expense_description_entered(message: Message, state: FSMContext) -> None:
    description = (message.text or "").strip()
    if not description:
        await message.answer("Izoh bo'sh bo'lishi mumkin emas. Iltimos, qayta yozing.")
        return
    await state.update_data(description=description)
    await state.set_state(ExpenseEntryStates.awaiting_receipt)
    await message.answer("Chek rasmini yuborasizmi? (ixtiyoriy)", reply_markup=skip_or_cancel())


async def _ask_expense_confirm(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await state.set_state(ExpenseEntryStates.awaiting_confirm)
    receipt_line = "\nChek: biriktirildi" if data.get("receipt_file_id") else ""
    await message.answer(
        "Tasdiqlaysizmi?\n"
        f"Summa: {Decimal(data['amount']):,.0f} so'm\n"
        f"Izoh: {esc(data['description'])}{receipt_line}",
        reply_markup=confirm_cancel(),
    )


@router.message(ExpenseEntryStates.awaiting_receipt, F.text == BTN_SKIP)
async def expense_receipt_skipped(message: Message, state: FSMContext) -> None:
    await state.update_data(receipt_file_id=None)
    await _ask_expense_confirm(message, state)


@router.message(ExpenseEntryStates.awaiting_receipt, F.photo)
async def expense_receipt_uploaded(message: Message, state: FSMContext) -> None:
    if not message.photo:
        return
    await state.update_data(receipt_file_id=message.photo[-1].file_id)
    await _ask_expense_confirm(message, state)


@router.message(ExpenseEntryStates.awaiting_receipt)
async def expense_receipt_invalid(message: Message) -> None:
    await message.answer("Iltimos, chek rasmini yuboring yoki “O'tkazib yuborish”ni bosing.")


@router.message(ExpenseEntryStates.awaiting_confirm, F.text == BTN_CONFIRM)
async def expense_confirmed(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if message.from_user is None:
        return
    data = await state.get_data()
    use_case = RecordExpenseUseCase(SqlAlchemyExpenseRepository(session))
    try:
        expense = await use_case.execute(
            RecordExpenseInput(
                amount=Decimal(data["amount"]),
                description=data["description"],
                recorded_by_id=message.from_user.id,
                receipt_file_id=data.get("receipt_file_id"),
            )
        )
    except DomainError as exc:
        await state.clear()
        await message.answer(str(exc))
        await show_main_menu(message, session)
        return

    await state.clear()
    await message.answer(f"✅ Qayd etildi: {expense.amount} so'm\nKod: X{expense.id}")
    await show_main_menu(message, session)


# --------------------------------------------------------------------------
# Recent entries: browse + correct (remove) a mistaken entry. Super-Admin
# only — the persistent menu is kept minimal for ordinary approved members,
# who no longer have a button for this at all.
# --------------------------------------------------------------------------


@router.message(F.text == BTN_RECENT)
async def show_recent_entries(message: Message, session: AsyncSession) -> None:
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

    await message.answer(text, reply_markup=recent_entries_menu())


@router.message(F.text == BTN_DELETE_ENTRY)
async def ask_removal_code(message: Message, state: FSMContext) -> None:
    await state.set_state(RemoveEntryStates.awaiting_code)
    await message.answer(
        "O'chiriladigan yozuv kodini yuboring (masalan: D12 yoki X7).",
        reply_markup=cancel_only(),
    )


@router.message(RemoveEntryStates.awaiting_code, F.text == BTN_CANCEL)
@router.message(RemoveEntryStates.confirming, F.text == BTN_CANCEL)
async def cancel_removal(message: Message, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    await message.answer("Bekor qilindi.")
    await show_main_menu(message, session)


@router.message(RemoveEntryStates.awaiting_code)
async def ask_confirm_removal(message: Message, state: FSMContext, session: AsyncSession) -> None:
    code = (message.text or "").strip().upper()
    if len(code) < 2 or code[0] not in ("D", "X") or not code[1:].isdigit():
        await message.answer("Noto'g'ri kod. Masalan: D12 yoki X7.")
        return

    kind, entry_id = code[0], int(code[1:])
    if kind == "D":
        donation = await SqlAlchemyDonationRepository(session).get(entry_id)
        if donation is None:
            await message.answer(f"{code} topilmadi.")
            return
        note_suffix = f" ({esc(donation.note)})" if donation.note else ""
        summary = f"{donation.amount} so'm{note_suffix}"
    else:
        expense = await SqlAlchemyExpenseRepository(session).get(entry_id)
        if expense is None:
            await message.answer(f"{code} topilmadi.")
            return
        summary = f"{expense.amount} so'm ({esc(expense.description)})"

    await state.update_data(code=code)
    await state.set_state(RemoveEntryStates.confirming)
    await message.answer(
        f"Tasdiqlaysizmi? {code} o'chiriladi:\n{summary}", reply_markup=confirm_cancel()
    )


@router.message(RemoveEntryStates.confirming, F.text == BTN_CONFIRM)
async def confirm_removal(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    code = data["code"]
    kind, entry_id = code[0], int(code[1:])
    try:
        if kind == "D":
            await RemoveDonationUseCase(SqlAlchemyDonationRepository(session)).execute(entry_id)
        else:
            await RemoveExpenseUseCase(SqlAlchemyExpenseRepository(session)).execute(entry_id)
    except (DonationNotFound, ExpenseNotFound):
        await state.clear()
        await message.answer(f"{code} topilmadi.")
        await show_main_menu(message, session)
        return

    await state.clear()
    await message.answer(f"✅ {code} o'chirildi.")
    await show_main_menu(message, session)
