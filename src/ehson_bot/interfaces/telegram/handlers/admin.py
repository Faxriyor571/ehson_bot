"""Super Admin: approve pending members, grant/revoke access, and manage
the donation account. Donations themselves are entirely self-service (see
``handlers/payments.py``) — there is no admin approval step for them.

TREASURER is the only non-admin approved role (there is no separate
donor-only tier) — this is a small, trusted group where every approved
member is also trusted to record expenses. Approving and revoking access
are one merged "Manage Members" screen rather than two separate ones,
since both are really the same underlying action: is this Telegram ID
allowed to use the bot or not. Revoking access has no lower "approved but
view-only" tier to fall back to, so it fully locks the person out again
(back to PENDING), the same as if they'd never been approved.

Telegram's Bot API has no way to look a user up by @username unless that
user has messaged the bot, so role changes are keyed on the numeric
Telegram ID (same convention the old ``ADMIN_IDS`` env var used) — obtained
by the target user via @userinfobot, then handed to the Super Admin.
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from ehson_bot.domain.entities import BotUser, Role
from ehson_bot.infrastructure.db.repositories import (
    SqlAlchemyBankAccountRepository,
    SqlAlchemyBotUserRepository,
)
from ehson_bot.interfaces.telegram.common import esc, show_main_menu
from ehson_bot.interfaces.telegram.filters import IsSuperAdmin
from ehson_bot.interfaces.telegram.keyboards import (
    BTN_APPROVE_MEMBER,
    BTN_CANCEL,
    BTN_CONFIRM,
    BTN_EDIT_BANK_ACCOUNT,
    BTN_MANAGE_MEMBERS,
    BTN_REVOKE_ACCESS,
    BTN_SETTINGS,
    cancel_only,
    confirm_cancel,
    manage_members_menu,
    settings_menu,
)
from ehson_bot.interfaces.telegram.states import BankAccountStates, ManageMembersStates

router = Router(name="admin")
router.message.filter(IsSuperAdmin())


_UNKNOWN_NAME = "Noma'lum"


def _member_listing(users: list[BotUser]) -> str:
    if not users:
        return "— yo'q"
    return "\n".join(
        f"• {esc(u.display_name) if u.display_name else _UNKNOWN_NAME} — ID: {u.telegram_id}"
        for u in users
    )


@router.message(F.text == BTN_MANAGE_MEMBERS)
async def open_manage_members(message: Message, session: AsyncSession) -> None:
    repo = SqlAlchemyBotUserRepository(session)
    pending = await repo.list_by_role(Role.PENDING)
    approved = await repo.list_by_role(Role.TREASURER)
    await message.answer(
        "<b>A'zolarni boshqarish</b>\n\n"
        f"⏳ Tasdiq kutmoqda:\n{_member_listing(pending)}\n\n"
        f"✅ Tasdiqlangan a'zolar:\n{_member_listing(approved)}",
        reply_markup=manage_members_menu(),
    )


@router.message(F.text == BTN_APPROVE_MEMBER)
async def ask_id_to_approve(message: Message, state: FSMContext) -> None:
    await state.set_state(ManageMembersStates.awaiting_id_to_approve)
    await message.answer(
        "Tasdiqlanadigan a'zoning Telegram ID raqamini yuboring.",
        reply_markup=cancel_only(),
    )


@router.message(F.text == BTN_REVOKE_ACCESS)
async def ask_id_to_revoke(message: Message, state: FSMContext) -> None:
    await state.set_state(ManageMembersStates.awaiting_id_to_revoke)
    await message.answer(
        "Kirishi bekor qilinadigan a'zoning Telegram ID raqamini yuboring.",
        reply_markup=cancel_only(),
    )


@router.message(ManageMembersStates.awaiting_id_to_approve, F.text == BTN_CANCEL)
@router.message(ManageMembersStates.awaiting_id_to_revoke, F.text == BTN_CANCEL)
@router.message(ManageMembersStates.confirming_approve, F.text == BTN_CANCEL)
@router.message(ManageMembersStates.confirming_revoke, F.text == BTN_CANCEL)
async def cancel_member_management(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    await state.clear()
    await message.answer("Bekor qilindi.")
    await show_main_menu(message, session)


@router.message(ManageMembersStates.awaiting_id_to_approve)
async def ask_confirm_approve_member(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    if not message.text or not message.text.strip().isdigit():
        await message.answer("Iltimos, faqat raqamlardan iborat Telegram ID yuboring.")
        return

    telegram_id = int(message.text.strip())
    user = await SqlAlchemyBotUserRepository(session).get(telegram_id)
    if user is None or user.role is not Role.PENDING:
        await message.answer(
            "Bu ID tasdiq kutayotganlar ro'yxatida topilmadi. Eslatma: shaxs "
            "avval botda /start bosgan bo'lishi kerak."
        )
        return

    await state.update_data(telegram_id=telegram_id)
    await state.set_state(ManageMembersStates.confirming_approve)
    label = esc(user.display_name) if user.display_name else str(telegram_id)
    await message.answer(
        f"Tasdiqlaysizmi?\n{label} (ID: {telegram_id}) botdan foydalanishga ruxsat oladi.",
        reply_markup=confirm_cancel(),
    )


@router.message(ManageMembersStates.confirming_approve, F.text == BTN_CONFIRM)
async def confirm_approve_member(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    data = await state.get_data()
    telegram_id = data["telegram_id"]
    await SqlAlchemyBotUserRepository(session).set_role(telegram_id, Role.TREASURER)
    await state.clear()
    await message.answer(f"✅ {telegram_id} endi botdan foydalanishi mumkin.")
    await show_main_menu(message, session)


@router.message(ManageMembersStates.awaiting_id_to_revoke)
async def ask_confirm_revoke_access(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    if not message.text or not message.text.strip().isdigit():
        await message.answer("Iltimos, faqat raqamlardan iborat Telegram ID yuboring.")
        return

    telegram_id = int(message.text.strip())
    user = await SqlAlchemyBotUserRepository(session).get(telegram_id)
    if user is None or user.role is not Role.TREASURER:
        await message.answer("Bu ID tasdiqlangan a'zolar ro'yxatida topilmadi.")
        return

    await state.update_data(telegram_id=telegram_id)
    await state.set_state(ManageMembersStates.confirming_revoke)
    label = esc(user.display_name) if user.display_name else str(telegram_id)
    await message.answer(
        f"Tasdiqlaysizmi?\n{label} (ID: {telegram_id}) botdan foydalanish huquqidan butunlay "
        "mahrum qilinadi (qayta tasdiqlash kerak bo'ladi).",
        reply_markup=confirm_cancel(),
    )


@router.message(ManageMembersStates.confirming_revoke, F.text == BTN_CONFIRM)
async def confirm_revoke_access(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    telegram_id = data["telegram_id"]
    # No lower "approved but view-only" tier exists to fall back to, so this
    # is a full lockout, not a demotion.
    await SqlAlchemyBotUserRepository(session).set_role(telegram_id, Role.PENDING)
    await state.clear()
    await message.answer(f"✅ {telegram_id} botdan foydalanish huquqidan mahrum qilindi.")
    await show_main_menu(message, session)


# --------------------------------------------------------------------------
# Settings: view/edit the donation bank account (card number, holder, bank —
# a guided 3-step flow, each field stored separately, not one free-text blob)
# --------------------------------------------------------------------------


def _account_summary(card_number: str, card_holder: str, bank_name: str) -> str:
    return (
        f"💳 Karta raqami: <code>{esc(card_number)}</code>\n"
        f"👤 Karta egasi: {esc(card_holder)}\n"
        f"🏦 Bank: {esc(bank_name)}"
    )


@router.message(F.text == BTN_SETTINGS)
async def open_settings(message: Message, session: AsyncSession) -> None:
    account = await SqlAlchemyBankAccountRepository(session).get()
    current = (
        _account_summary(account.card_number, account.card_holder, account.bank_name)
        if account
        else "Hisob raqami hali sozlanmagan."
    )
    await message.answer(f"<b>Sozlamalar</b>\n\n{current}", reply_markup=settings_menu())


@router.message(F.text == BTN_EDIT_BANK_ACCOUNT)
async def ask_card_number(message: Message, state: FSMContext) -> None:
    await state.set_state(BankAccountStates.awaiting_card_number)
    await message.answer("1/3. Karta raqamini yuboring.", reply_markup=cancel_only())


@router.message(BankAccountStates.awaiting_card_number, F.text == BTN_CANCEL)
@router.message(BankAccountStates.awaiting_card_holder, F.text == BTN_CANCEL)
@router.message(BankAccountStates.awaiting_bank_name, F.text == BTN_CANCEL)
@router.message(BankAccountStates.confirming, F.text == BTN_CANCEL)
async def cancel_bank_account_edit(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    await state.clear()
    await message.answer("Bekor qilindi.")
    await show_main_menu(message, session)


@router.message(BankAccountStates.awaiting_card_number)
async def ask_card_holder(message: Message, state: FSMContext) -> None:
    card_number = (message.text or "").strip()
    if not card_number:
        await message.answer("Karta raqami bo'sh bo'lishi mumkin emas. Iltimos, qayta yuboring.")
        return

    await state.update_data(card_number=card_number)
    await state.set_state(BankAccountStates.awaiting_card_holder)
    await message.answer("2/3. Karta egasining F.I.Sh.ni yuboring.", reply_markup=cancel_only())


@router.message(BankAccountStates.awaiting_card_holder)
async def ask_bank_name(message: Message, state: FSMContext) -> None:
    card_holder = (message.text or "").strip()
    if not card_holder:
        await message.answer("Karta egasi bo'sh bo'lishi mumkin emas. Iltimos, qayta yuboring.")
        return

    await state.update_data(card_holder=card_holder)
    await state.set_state(BankAccountStates.awaiting_bank_name)
    await message.answer("3/3. Bank nomini yuboring.", reply_markup=cancel_only())


@router.message(BankAccountStates.awaiting_bank_name)
async def ask_confirm_bank_account(message: Message, state: FSMContext) -> None:
    bank_name = (message.text or "").strip()
    if not bank_name:
        await message.answer("Bank nomi bo'sh bo'lishi mumkin emas. Iltimos, qayta yuboring.")
        return

    await state.update_data(bank_name=bank_name)
    await state.set_state(BankAccountStates.confirming)
    data = await state.get_data()
    summary = _account_summary(data["card_number"], data["card_holder"], bank_name)
    await message.answer(
        f"Tasdiqlaysizmi?\n\n{summary}", reply_markup=confirm_cancel()
    )


@router.message(BankAccountStates.confirming, F.text == BTN_CONFIRM)
async def confirm_bank_account(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    await SqlAlchemyBankAccountRepository(session).set(
        card_number=data["card_number"],
        card_holder=data["card_holder"],
        bank_name=data["bank_name"],
    )
    await state.clear()
    await message.answer("✅ Hisob raqami yangilandi.")
    await show_main_menu(message, session)

