"""Any approved member's flow: pick an amount, see the donation card,
confirm the transfer, done.

Gated by ``IsTreasurerOrAbove`` (the lowest approved rank — there is no
separate donor-only tier) rather than anything donation-specific: this is a
small, trusted group of a handful of people, so the donor's own
"✅ Pulni o'tkazdim" press *is* the final confirmation — there is no second,
manual Super-Admin review step. Pressing it immediately records the
``Donation`` (balance and statistics update automatically, since they
already compute live from that table), notifies every Super Admin, and
posts the anonymous donation announcement.

Flow: preset amount (or "Boshqa summa" for a custom one) -> the donation
card -> an optional receipt photo -> "✅ Pulni o'tkazdim" -> recorded.
"""
from __future__ import annotations

from contextlib import suppress
from decimal import Decimal, InvalidOperation

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramForbiddenError
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from ehson_bot.application.use_cases.get_period_report import GetPeriodReportUseCase, Period
from ehson_bot.application.use_cases.record_donation import (
    SYSTEM_TREASURER_ID,
    RecordDonationInput,
    RecordDonationUseCase,
)
from ehson_bot.domain.entities import Donation, Role
from ehson_bot.infrastructure.db.repositories import (
    SqlAlchemyBankAccountRepository,
    SqlAlchemyBotUserRepository,
    SqlAlchemyDonationRepository,
    SqlAlchemyExpenseRepository,
)
from ehson_bot.interfaces.telegram.common import esc, show_main_menu
from ehson_bot.interfaces.telegram.filters import IsTreasurerOrAbove
from ehson_bot.interfaces.telegram.keyboards import (
    BTN_ACCOUNT,
    BTN_AMOUNT_50K,
    BTN_AMOUNT_100K,
    BTN_AMOUNT_200K,
    BTN_AMOUNT_500K,
    BTN_CANCEL,
    BTN_OTHER_AMOUNT,
    BTN_SKIP,
    BTN_TRANSFERRED,
    amount_choice_menu,
    cancel_only,
    skip_or_cancel,
    transferred_cancel,
)
from ehson_bot.interfaces.telegram.states import PaymentStates

router = Router(name="payments")
router.message.filter(IsTreasurerOrAbove())

_PRESET_AMOUNTS: dict[str, Decimal] = {
    BTN_AMOUNT_50K: Decimal(50000),
    BTN_AMOUNT_100K: Decimal(100000),
    BTN_AMOUNT_200K: Decimal(200000),
    BTN_AMOUNT_500K: Decimal(500000),
}


def _parse_amount(text: str) -> Decimal | None:
    raw = text.replace(",", "").replace(" ", "").strip()
    try:
        value = Decimal(raw)
    except InvalidOperation:
        return None
    return value if value > 0 else None


@router.message(F.text == BTN_ACCOUNT)
async def start_payment(message: Message, state: FSMContext) -> None:
    await state.set_state(PaymentStates.choosing_amount)
    await message.answer("🤲 Ehson summasini tanlang:", reply_markup=amount_choice_menu())


@router.message(PaymentStates.choosing_amount, F.text == BTN_CANCEL)
@router.message(PaymentStates.awaiting_amount, F.text == BTN_CANCEL)
@router.message(PaymentStates.awaiting_receipt, F.text == BTN_CANCEL)
@router.message(PaymentStates.confirming, F.text == BTN_CANCEL)
async def cancel_payment(message: Message, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    await message.answer("Bekor qilindi.")
    await show_main_menu(message, session)


@router.message(PaymentStates.choosing_amount, F.text == BTN_OTHER_AMOUNT)
async def ask_custom_amount(message: Message, state: FSMContext) -> None:
    await state.set_state(PaymentStates.awaiting_amount)
    await message.answer(
        "Ehson summasini kiriting (so'm). Masalan: 150000", reply_markup=cancel_only()
    )


async def _show_donation_card(message: Message, state: FSMContext, session: AsyncSession) -> None:
    account = await SqlAlchemyBankAccountRepository(session).get()
    if account is None:
        await state.clear()
        await message.answer(
            "🤲 Hisob raqami hali sozlanmagan.\nIltimos, administrator bilan bog'laning."
        )
        await show_main_menu(message, session)
        return

    await state.set_state(PaymentStates.awaiting_receipt)
    await message.answer(
        "Quyidagi hisob raqamiga ehson yuboring:\n\n"
        f"💳 Karta raqami: <code>{esc(account.card_number)}</code>\n"
        f"👤 Karta egasi: {esc(account.card_holder)}\n"
        f"🏦 Bank: {esc(account.bank_name)}\n\n"
        "To'lov chekini (skrinshot) yuborasizmi? (ixtiyoriy)",
        reply_markup=skip_or_cancel(),
    )


@router.message(PaymentStates.choosing_amount, F.text.in_(_PRESET_AMOUNTS))
async def preset_amount_chosen(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if message.text is None:
        return
    await state.update_data(amount=str(_PRESET_AMOUNTS[message.text]))
    await _show_donation_card(message, state, session)


@router.message(PaymentStates.awaiting_amount)
async def custom_amount_entered(message: Message, state: FSMContext, session: AsyncSession) -> None:
    amount = _parse_amount(message.text or "")
    if amount is None:
        await message.answer("Summa noto'g'ri. Masalan: 150000")
        return
    await state.update_data(amount=str(amount))
    await _show_donation_card(message, state, session)


async def _ask_payment_confirm(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await state.set_state(PaymentStates.confirming)
    amount = Decimal(data["amount"])
    receipt_line = "\nChek: biriktirildi" if data.get("receipt_file_id") else "\nChek: yuborilmadi"
    await message.answer(
        "<b>Pulni o'tkazdingizmi?</b>\n\n"
        f"💰 Summa: {amount:,.0f} so'm{receipt_line}\n\n"
        "Pastdagi tugmani bosgach, ehsoningiz darhol qayd etiladi.",
        reply_markup=transferred_cancel(),
    )


@router.message(PaymentStates.awaiting_receipt, F.text == BTN_SKIP)
async def receipt_skipped(message: Message, state: FSMContext) -> None:
    await state.update_data(receipt_file_id=None)
    await _ask_payment_confirm(message, state)


@router.message(PaymentStates.awaiting_receipt, F.photo)
async def receipt_uploaded(message: Message, state: FSMContext) -> None:
    if not message.photo:
        return
    await state.update_data(receipt_file_id=message.photo[-1].file_id)
    await _ask_payment_confirm(message, state)


@router.message(PaymentStates.awaiting_receipt)
async def receipt_invalid(message: Message) -> None:
    await message.answer("Iltimos, chek rasmini yuboring yoki “O'tkazib yuborish”ni bosing.")


async def _donor_confirmed_text(session: AsyncSession, telegram_id: int, amount: str) -> str:
    user = await SqlAlchemyBotUserRepository(session).get(telegram_id)
    name = user.anonymous_name if user is not None and user.anonymous_name is not None else None
    greeting = f"🤲 Rahmat, {esc(name)}!" if name is not None else "🤲 Rahmat!"
    return (
        f"{greeting}\n\n"
        "✅ Ehsoningiz muvaffaqiyatli qayd etildi.\n\n"
        f"💰 {amount}\n\n"
        "Alloh ehsoningizni qabul qilsin va ajringizni ziyoda qilsin. 🤲"
    )


async def _notify_super_admins(
    bot: Bot, session: AsyncSession, donation: Donation, receipt_file_id: str | None
) -> None:
    """Never the donor's Telegram ID, username, display name, or anything
    else that could identify who paid — just the amount and the record's
    own code (the same D#/X# convention already used for corrections).
    """
    text = f"✅ Yangi ehson qayd etildi\n\n💰 {donation.amount} so'm\n\nKod: D{donation.id}"

    admins = await SqlAlchemyBotUserRepository(session).list_by_role(Role.SUPER_ADMIN)
    for admin in admins:
        try:
            if receipt_file_id is not None:
                await bot.send_photo(admin.telegram_id, photo=receipt_file_id, caption=text)
            else:
                await bot.send_message(admin.telegram_id, text)
        except TelegramForbiddenError:
            pass


async def _donation_announcement_line(session: AsyncSession, donor_telegram_id: int) -> str:
    """Never the donor's real name or username — their own chosen (or
    randomly assigned) anonymous nickname if they have one, otherwise a
    generic, still-anonymous phrase.
    """
    user = await SqlAlchemyBotUserRepository(session).get(donor_telegram_id)
    if user is not None and user.anonymous_name is not None:
        return f"🌙 {esc(user.anonymous_name)} ehson qildi!"
    return "🤲 Mahfiy inson ehson qildi!"


def _donation_announcement_text(
    donor_line: str, amount: str, today_total: str, balance: str
) -> str:
    return (
        f"{donor_line}\n\n"
        f"💰 +{amount}\n\n"
        f"📊 Bugungi ehson:\n{today_total}\n\n"
        f"💰 Joriy balans:\n{balance}\n\n"
        "🤲 Alloh ehson qiluvchidan rozi bo'lsin."
    )


async def _announce_donation(
    bot: Bot, session: AsyncSession, donor_telegram_id: int, amount: str
) -> None:
    """Every Super Admin's own private chat — never a group or channel;
    this project has no Telegram group/channel dependency anywhere.
    """
    donor_line = await _donation_announcement_line(session, donor_telegram_id)

    snapshot_use_case = GetPeriodReportUseCase(
        SqlAlchemyDonationRepository(session), SqlAlchemyExpenseRepository(session)
    )
    today = await snapshot_use_case.execute(Period.TODAY)
    all_time = await snapshot_use_case.execute(Period.ALL)
    text = _donation_announcement_text(
        donor_line,
        amount,
        today_total=f"{today.donations_total:,.0f} so'm",
        balance=f"{all_time.balance:,.0f} so'm",
    )

    admins = await SqlAlchemyBotUserRepository(session).list_by_role(Role.SUPER_ADMIN)
    for admin in admins:
        with suppress(TelegramForbiddenError):
            await bot.send_message(admin.telegram_id, text)


@router.message(PaymentStates.confirming, F.text == BTN_TRANSFERRED)
async def confirm_payment(
    message: Message, state: FSMContext, session: AsyncSession, bot: Bot
) -> None:
    if message.from_user is None:
        return
    data = await state.get_data()
    amount = Decimal(data["amount"])
    receipt_file_id = data.get("receipt_file_id")

    donation = await RecordDonationUseCase(SqlAlchemyDonationRepository(session)).execute(
        RecordDonationInput(
            amount=amount,
            recorded_by_id=SYSTEM_TREASURER_ID,
            receipt_file_id=receipt_file_id,
        )
    )

    await state.clear()
    amount_text = f"{donation.amount} so'm"
    await message.answer(
        f"{await _donor_confirmed_text(session, message.from_user.id, amount_text)}\n\n"
        f"Kod: D{donation.id}"
    )

    await _notify_super_admins(bot, session, donation, receipt_file_id)
    await _announce_donation(bot, session, message.from_user.id, amount_text)

    await show_main_menu(message, session)
