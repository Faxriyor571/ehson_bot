"""Any approved member's flow: pick an amount, confirm, pay.

Gated by ``IsTreasurerOrAbove`` (the lowest approved rank — there is no
separate donor-only tier) rather than anything donation-specific: what
actually protects the donation from being fabricated is the payment
provider's confirmation, not a role check on who's allowed to ask for one.

Flow: preset amount (or "Boshqa summa" for a custom one) -> a confirmation
screen showing the amount and payment method -> "Pay Now" -> wait. No
``PaymentSession`` is created until the donor confirms the amount, so a typo
caught at the confirmation step never leaves an abandoned session behind.

Confirmation of the payment itself never arrives through this router — it
happens out-of-band (the mock provider's delayed self-trigger today, a real
provider's webhook handler later) and pushes the thank-you message directly
via ``bot.send_message``, the same "outside the request/response cycle"
pattern ``infrastructure/scheduler.py::send_daily_report`` already uses.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from ehson_bot.application.use_cases.request_payment import (
    RequestPaymentInput,
    RequestPaymentUseCase,
)
from ehson_bot.domain.repositories import PaymentProvider
from ehson_bot.infrastructure.db.repositories import (
    SqlAlchemyBankAccountRepository,
    SqlAlchemyPaymentSessionRepository,
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
    amount_choice_menu,
    cancel_only,
    confirm_cancel,
    pay_now_keyboard,
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
@router.message(PaymentStates.confirming, F.text == BTN_CANCEL)
async def cancel_before_payment(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    await state.clear()
    await message.answer("Bekor qilindi.")
    await show_main_menu(message, session)


@router.message(PaymentStates.choosing_amount, F.text == BTN_OTHER_AMOUNT)
async def ask_custom_amount(message: Message, state: FSMContext) -> None:
    await state.set_state(PaymentStates.awaiting_amount)
    await message.answer(
        "Ehson summasini kiriting (so'm). Masalan: 150000", reply_markup=cancel_only()
    )


async def _ask_payment_confirm(
    message: Message, state: FSMContext, amount: Decimal, payment_provider: PaymentProvider
) -> None:
    await state.update_data(amount=str(amount))
    await state.set_state(PaymentStates.confirming)
    await message.answer(
        "<b>🤲 Ehsonni tasdiqlang</b>\n\n"
        f"💰 Summa: {amount:,.0f} so'm\n"
        f"💳 Usul: {payment_provider.display_name}\n\n"
        "Ehsoningiz uchun oldindan rahmat — tasdiqlab, to'lovga o'ting.",
        reply_markup=confirm_cancel(),
    )


@router.message(PaymentStates.choosing_amount, F.text.in_(_PRESET_AMOUNTS))
async def preset_amount_chosen(
    message: Message, state: FSMContext, payment_provider: PaymentProvider
) -> None:
    if message.text is None:
        return
    await _ask_payment_confirm(message, state, _PRESET_AMOUNTS[message.text], payment_provider)


@router.message(PaymentStates.awaiting_amount)
async def custom_amount_entered(
    message: Message, state: FSMContext, payment_provider: PaymentProvider
) -> None:
    amount = _parse_amount(message.text or "")
    if amount is None:
        await message.answer("Summa noto'g'ri. Masalan: 150000")
        return
    await _ask_payment_confirm(message, state, amount, payment_provider)


@router.message(PaymentStates.confirming, F.text == BTN_CONFIRM)
async def confirm_amount(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    payment_provider: PaymentProvider,
) -> None:
    if message.from_user is None:
        return
    data = await state.get_data()
    amount = Decimal(data["amount"])

    payment_session = await RequestPaymentUseCase(payment_provider).execute(
        RequestPaymentInput(amount=amount, donor_telegram_id=message.from_user.id)
    )

    await state.update_data(provider_session_id=payment_session.provider_session_id)
    await state.set_state(PaymentStates.awaiting_payment)

    text = f"To'lovni yakunlash uchun quyidagi tugmani bosing:\nSumma: {amount:,.0f} so'm"

    account = await SqlAlchemyBankAccountRepository(session).get()
    if account is not None:
        text += (
            "\n\nYoki quyidagi hisob raqamiga to'g'ridan-to'g'ri o'tkazishingiz mumkin:\n"
            f"💳 Karta raqami: <code>{esc(account.card_number)}</code>\n"
            f"👤 Karta egasi: {esc(account.card_holder)}\n"
            f"🏦 Bank: {esc(account.bank_name)}"
        )

    await message.answer(text, reply_markup=pay_now_keyboard(payment_session.pay_url or ""))
    await message.answer(
        "To'lov tugagach xabar beramiz. Bekor qilish uchun:", reply_markup=cancel_only()
    )


@router.message(PaymentStates.awaiting_payment, F.text == BTN_CANCEL)
async def cancel_payment(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    provider_session_id = data.get("provider_session_id")
    if provider_session_id:
        await SqlAlchemyPaymentSessionRepository(session).mark_cancelled(provider_session_id)
    await state.clear()
    await message.answer("Bekor qilindi.")
    await show_main_menu(message, session)
