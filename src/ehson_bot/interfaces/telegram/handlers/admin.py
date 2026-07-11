"""Super Admin: grant/revoke the Treasurer role.

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

from ehson_bot.domain.entities import Role
from ehson_bot.infrastructure.db.repositories import (
    SqlAlchemyBankAccountRepository,
    SqlAlchemyBotUserRepository,
)
from ehson_bot.interfaces.telegram.common import show_main_menu
from ehson_bot.interfaces.telegram.filters import IsSuperAdmin
from ehson_bot.interfaces.telegram.keyboards import (
    BTN_ADD_TREASURER,
    BTN_APPROVE_BY_ID,
    BTN_APPROVE_USERS,
    BTN_CANCEL,
    BTN_CONFIRM,
    BTN_EDIT_BANK_ACCOUNT,
    BTN_MANAGE_TREASURERS,
    BTN_REMOVE_TREASURER,
    BTN_SETTINGS,
    approve_users_menu,
    cancel_only,
    confirm_cancel,
    manage_treasurers_menu,
    settings_menu,
)
from ehson_bot.interfaces.telegram.states import (
    ApproveUserStates,
    ManageTreasurerStates,
    SettingsStates,
)

router = Router(name="admin")
router.message.filter(IsSuperAdmin())


@router.message(F.text == BTN_MANAGE_TREASURERS)
async def open_manage_treasurers(message: Message, session: AsyncSession) -> None:
    treasurers = await SqlAlchemyBotUserRepository(session).list_by_role(Role.TREASURER)
    if treasurers:
        listing = "\n".join(
            f"• {t.display_name or 'Noma\'lum'} — ID: {t.telegram_id}" for t in treasurers
        )
    else:
        listing = "Hozircha xazinachilar yo'q."
    await message.answer(f"<b>Xazinachilar:</b>\n{listing}", reply_markup=manage_treasurers_menu())


@router.message(F.text == BTN_ADD_TREASURER)
async def ask_id_to_add(message: Message, state: FSMContext) -> None:
    await state.set_state(ManageTreasurerStates.awaiting_id_to_add)
    await message.answer(
        "Xazinachi etib tayinlanadigan foydalanuvchining Telegram ID raqamini yuboring "
        "(u avval botga /start bosgan bo'lishi kerak).",
        reply_markup=cancel_only(),
    )


@router.message(F.text == BTN_REMOVE_TREASURER)
async def ask_id_to_remove(message: Message, state: FSMContext) -> None:
    await state.set_state(ManageTreasurerStates.awaiting_id_to_remove)
    await message.answer(
        "Xazinachilikdan chetlatiladigan Telegram ID raqamini yuboring.",
        reply_markup=cancel_only(),
    )


@router.message(ManageTreasurerStates.awaiting_id_to_add, F.text == BTN_CANCEL)
@router.message(ManageTreasurerStates.awaiting_id_to_remove, F.text == BTN_CANCEL)
@router.message(ManageTreasurerStates.confirming_add, F.text == BTN_CANCEL)
@router.message(ManageTreasurerStates.confirming_remove, F.text == BTN_CANCEL)
async def cancel_role_change(message: Message, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    await message.answer("Bekor qilindi.")
    await show_main_menu(message, session)


@router.message(ManageTreasurerStates.awaiting_id_to_add)
async def ask_confirm_add_treasurer(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    if not message.text or not message.text.strip().isdigit():
        await message.answer("Iltimos, faqat raqamlardan iborat Telegram ID yuboring.")
        return

    telegram_id = int(message.text.strip())
    user = await SqlAlchemyBotUserRepository(session).get(telegram_id)
    if user is None:
        await message.answer(
            "Bu ID topilmadi. Avval o'sha shaxs botda /start bosishi kerak, "
            "so'ng qayta urinib ko'ring."
        )
        return

    await state.update_data(telegram_id=telegram_id)
    await state.set_state(ManageTreasurerStates.confirming_add)
    label = user.display_name or str(telegram_id)
    await message.answer(
        f"Tasdiqlaysizmi?\n{label} (ID: {telegram_id}) endi xazinachi bo'ladi.",
        reply_markup=confirm_cancel(),
    )


@router.message(ManageTreasurerStates.confirming_add, F.text == BTN_CONFIRM)
async def confirm_add_treasurer(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    telegram_id = data["telegram_id"]
    await SqlAlchemyBotUserRepository(session).set_role(telegram_id, Role.TREASURER)
    await state.clear()
    await message.answer(f"✅ {telegram_id} endi xazinachi.")
    await show_main_menu(message, session)


@router.message(ManageTreasurerStates.awaiting_id_to_remove)
async def ask_confirm_remove_treasurer(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    if not message.text or not message.text.strip().isdigit():
        await message.answer("Iltimos, faqat raqamlardan iborat Telegram ID yuboring.")
        return

    telegram_id = int(message.text.strip())
    user = await SqlAlchemyBotUserRepository(session).get(telegram_id)
    if user is None or user.role is not Role.TREASURER:
        await message.answer("Bu ID xazinachilar ro'yxatida topilmadi.")
        return

    await state.update_data(telegram_id=telegram_id)
    await state.set_state(ManageTreasurerStates.confirming_remove)
    label = user.display_name or str(telegram_id)
    await message.answer(
        f"Tasdiqlaysizmi?\n{label} (ID: {telegram_id}) xazinachilikdan chetlatiladi.",
        reply_markup=confirm_cancel(),
    )


@router.message(ManageTreasurerStates.confirming_remove, F.text == BTN_CONFIRM)
async def confirm_remove_treasurer(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    data = await state.get_data()
    telegram_id = data["telegram_id"]
    await SqlAlchemyBotUserRepository(session).set_role(telegram_id, Role.USER)
    await state.clear()
    await message.answer(f"✅ {telegram_id} xazinachilikdan chetlatildi.")
    await show_main_menu(message, session)


# --------------------------------------------------------------------------
# Settings: view/edit the donation bank account text
# --------------------------------------------------------------------------


@router.message(F.text == BTN_SETTINGS)
async def open_settings(message: Message, session: AsyncSession) -> None:
    account = await SqlAlchemyBankAccountRepository(session).get()
    current = f"Joriy matn:\n{account.text}" if account else "Hisob raqami hali sozlanmagan."
    await message.answer(f"<b>Sozlamalar</b>\n\n{current}", reply_markup=settings_menu())


@router.message(F.text == BTN_EDIT_BANK_ACCOUNT)
async def ask_bank_account_text(message: Message, state: FSMContext) -> None:
    await state.set_state(SettingsStates.awaiting_bank_account_text)
    await message.answer(
        "Hisob raqami uchun matnni yuboring (bank nomi, karta/hisob raqami, qabul qiluvchi).",
        reply_markup=cancel_only(),
    )


@router.message(SettingsStates.awaiting_bank_account_text, F.text == BTN_CANCEL)
@router.message(SettingsStates.confirming, F.text == BTN_CANCEL)
async def cancel_bank_account_edit(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    await state.clear()
    await message.answer("Bekor qilindi.")
    await show_main_menu(message, session)


@router.message(SettingsStates.awaiting_bank_account_text)
async def ask_confirm_bank_account_text(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not text:
        await message.answer("Matn bo'sh bo'lishi mumkin emas. Iltimos, qayta yuboring.")
        return

    await state.update_data(text=text)
    await state.set_state(SettingsStates.confirming)
    await message.answer(
        f"Tasdiqlaysizmi? Yangi matn:\n\n{text}", reply_markup=confirm_cancel()
    )


@router.message(SettingsStates.confirming, F.text == BTN_CONFIRM)
async def confirm_bank_account_text(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    data = await state.get_data()
    await SqlAlchemyBankAccountRepository(session).set(data["text"])
    await state.clear()
    await message.answer("✅ Hisob raqami yangilandi.")
    await show_main_menu(message, session)


# --------------------------------------------------------------------------
# Approve pending users: grant baseline (USER) access
# --------------------------------------------------------------------------


@router.message(F.text == BTN_APPROVE_USERS)
async def open_approve_users(message: Message, session: AsyncSession) -> None:
    pending = await SqlAlchemyBotUserRepository(session).list_by_role(Role.PENDING)
    if pending:
        listing = "\n".join(
            f"• {u.display_name or 'Noma\'lum'} — ID: {u.telegram_id}" for u in pending
        )
    else:
        listing = "Hozircha tasdiq kutayotgan foydalanuvchilar yo'q."
    await message.answer(
        f"<b>Tasdiq kutayotganlar:</b>\n{listing}", reply_markup=approve_users_menu()
    )


@router.message(F.text == BTN_APPROVE_BY_ID)
async def ask_id_to_approve(message: Message, state: FSMContext) -> None:
    await state.set_state(ApproveUserStates.awaiting_id)
    await message.answer(
        "Tasdiqlanadigan foydalanuvchining Telegram ID raqamini yuboring.",
        reply_markup=cancel_only(),
    )


@router.message(ApproveUserStates.awaiting_id, F.text == BTN_CANCEL)
@router.message(ApproveUserStates.confirming, F.text == BTN_CANCEL)
async def cancel_approve_user(message: Message, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    await message.answer("Bekor qilindi.")
    await show_main_menu(message, session)


@router.message(ApproveUserStates.awaiting_id)
async def ask_confirm_approve_user(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    if not message.text or not message.text.strip().isdigit():
        await message.answer("Iltimos, faqat raqamlardan iborat Telegram ID yuboring.")
        return

    telegram_id = int(message.text.strip())
    user = await SqlAlchemyBotUserRepository(session).get(telegram_id)
    if user is None or user.role is not Role.PENDING:
        await message.answer("Bu ID tasdiq kutayotganlar ro'yxatida topilmadi.")
        return

    await state.update_data(telegram_id=telegram_id)
    await state.set_state(ApproveUserStates.confirming)
    label = user.display_name or str(telegram_id)
    await message.answer(
        f"Tasdiqlaysizmi?\n{label} (ID: {telegram_id}) botdan foydalanishga ruxsat oladi.",
        reply_markup=confirm_cancel(),
    )


@router.message(ApproveUserStates.confirming, F.text == BTN_CONFIRM)
async def confirm_approve_user(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    telegram_id = data["telegram_id"]
    await SqlAlchemyBotUserRepository(session).set_role(telegram_id, Role.USER)
    await state.clear()
    await message.answer(f"✅ {telegram_id} endi botdan foydalanishi mumkin.")
    await show_main_menu(message, session)
