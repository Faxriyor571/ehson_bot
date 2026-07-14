"""Any approved member's flow: pick an amount, see the donation card, submit
a receipt, and wait for a Super Admin to manually verify the bank account.

Gated by ``IsTreasurerOrAbove`` (the lowest approved rank — there is no
separate donor-only tier) rather than anything donation-specific: what
protects the donation from being fabricated is a Super Admin actually
checking the bank account, not a role check on who's allowed to submit one.

Flow: preset amount (or "Boshqa summa" for a custom one) -> the donation
card -> an optional receipt photo -> a confirmation screen -> submit. A
``PendingPayment`` is only created on that final submit, with a random
public ``reference_code`` (e.g. "EH-8F42K") — the *only* donor-facing
identifier a Super Admin ever sees. The donor's Telegram ID is stored
internally purely to route the private confirm/reject message later, and is
scrubbed by the repository the instant a Super Admin decides — see
``PendingPayment`` in the domain layer for the full rationale. Confirmation
itself happens entirely in ``handlers/admin.py``; this router never learns
what a Super Admin ultimately decides beyond what it can see (nothing).
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramForbiddenError
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from ehson_bot.application.use_cases.submit_pending_payment import (
    SubmitPendingPaymentInput,
    SubmitPendingPaymentUseCase,
)
from ehson_bot.domain.entities import PendingPayment, Role
from ehson_bot.infrastructure.db.repositories import (
    SqlAlchemyBankAccountRepository,
    SqlAlchemyBotUserRepository,
    SqlAlchemyPendingPaymentRepository,
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
    BTN_CONFIRM,
    BTN_OTHER_AMOUNT,
    BTN_SKIP,
    amount_choice_menu,
    cancel_only,
    confirm_cancel,
    skip_or_cancel,
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

# Shown to the Super Admin instead of any identifying information —
# "Allah's beloved servant", a deliberately generic, respectful stand-in.
_ANONYMOUS_DONOR_LABEL = "Allohning suygan bandasi"


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
        "<b>Tasdiqlaysizmi?</b>\n\n"
        f"💰 Summa: {amount:,.0f} so'm{receipt_line}\n\n"
        "Tasdiqlagach, administrator hisobingizni tekshirib chiqadi.",
        reply_markup=confirm_cancel(),
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


async def _notify_super_admins(bot: Bot, session: AsyncSession, payment: PendingPayment) -> None:
    """The only information a Super Admin ever receives about a donor: a
    reference code, a generic non-identifying label, the amount, the time,
    and the receipt if one was attached. Never the Telegram ID, username,
    display name, or anything else that could identify who paid.
    """
    text = (
        "🆔 Reference:\n"
        f"{payment.reference_code}\n\n"
        f"👤 {_ANONYMOUS_DONOR_LABEL}\n\n"
        f"💰 {payment.amount} so'm\n\n"
        f"🕒 {payment.created_at:%Y-%m-%d %H:%M}"
    )

    admins = await SqlAlchemyBotUserRepository(session).list_by_role(Role.SUPER_ADMIN)
    for admin in admins:
        try:
            if payment.receipt_file_id is not None:
                await bot.send_photo(admin.telegram_id, photo=payment.receipt_file_id, caption=text)
            else:
                await bot.send_message(admin.telegram_id, text)
        except TelegramForbiddenError:
            pass


@router.message(PaymentStates.confirming, F.text == BTN_CONFIRM)
async def confirm_payment(
    message: Message, state: FSMContext, session: AsyncSession, bot: Bot
) -> None:
    if message.from_user is None:
        return
    data = await state.get_data()

    use_case = SubmitPendingPaymentUseCase(SqlAlchemyPendingPaymentRepository(session))
    payment = await use_case.execute(
        SubmitPendingPaymentInput(
            amount=Decimal(data["amount"]),
            donor_telegram_id=message.from_user.id,
            receipt_file_id=data.get("receipt_file_id"),
        )
    )

    await state.clear()
    await message.answer(
        "✅ Ehsoningiz qabul qilindi va tekshiruv uchun yuborildi.\n\n"
        f"🆔 Murojaat kodi: <code>{payment.reference_code}</code>\n\n"
        "Administrator hisobingizni tasdiqlagach, sizga xabar beramiz."
    )
    await _notify_super_admins(bot, session, payment)
    await show_main_menu(message, session)
