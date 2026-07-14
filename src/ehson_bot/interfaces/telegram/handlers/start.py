"""/start and /help — every caller is registered, but starts PENDING (no access).

A Super Admin must approve a PENDING user (promoting them to TREASURER, the
only non-admin approved role) before they can see anything at all — no
statistics, no balance, no menu.
"""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from ehson_bot.domain.entities import BotUser, Role
from ehson_bot.infrastructure.db.repositories import SqlAlchemyBotUserRepository
from ehson_bot.interfaces.telegram.keyboards import main_menu

router = Router(name="start")


def lockout_text(telegram_id: int) -> str:
    return (
        "🔒 Siz hali ushbu botdan foydalanish uchun ruxsat olmagansiz.\n\n"
        "Iltimos, administratorga murojaat qiling va unga quyidagi Telegram ID "
        "raqamingizni yuboring, u orqali sizni tasdiqlaydi:\n"
        f"<code>{telegram_id}</code>"
    )


def _daily_reflection() -> str:
    """A single static line for now — swap this body for real rotation
    (Qur'an verse / hadith of the day) later; nothing else needs to change.
    """
    return "\"Sadaqa gunohni o'chiradi, xuddi suv olovni o'chirgani kabi.\" (Termiziy)"


def _welcome_text() -> str:
    return (
        "<b>Assalomu alaykum va rohmatulloh!</b>\n\n"
        "<b>Mahfiy Ehson</b> botiga xush kelibsiz.\n\n"
        "Bu yerda ehson-xayriya mablag'lari to'planadi va ishlatilishi to'liq "
        "shaffof tarzda ko'rsatiladi. Kim qancha xayr qilgani hech qachon "
        "e'lon qilinmaydi — faqat mablag' qayerga sarflangani ko'rinadi.\n\n"
        f"<i>{_daily_reflection()}</i>\n\n"
        "Quyidagi menyudan foydalaning."
    )


def help_text(role: Role) -> str:
    """Mirrors ``keyboards.main_menu`` exactly — never mentions a button the
    caller's role doesn't actually see.
    """
    lines = [
        "<b>Mahfiy Ehson boti — yordam</b>\n",
        "📊 Statistika — bugungi/oylik/yillik/umumiy hisobot",
        "💰 Balans — joriy balans va bugungi harakat",
        "🤲 Ehson qilish — ehson yuborish",
        "📜 Foydalanish tarixi — mablag' qayerga sarflanganini ko'rish",
        "📋 Oxirgi yozuvlar — so'nggi ehson va xarajatlar ro'yxati",
    ]

    if role is Role.SUPER_ADMIN:
        lines += [
            "\n<b>Boshqaruv</b>",
            "➖ Xarajat qo'shish — yangi xarajatni qayd etish",
            "👥 A'zolarni boshqarish — a'zolarni tasdiqlash yoki kirishini bekor qilish",
            "⚙️ Sozlamalar — ehson hisob raqamini sozlash",
        ]

    lines.append(
        "\nHar qanday amalni istalgan vaqtda “❌ Bekor qilish” bilan bekor "
        "qilishingiz mumkin."
    )
    return "\n".join(lines)


async def _register_caller(message: Message, session: AsyncSession) -> BotUser | None:
    if message.from_user is None:
        return None
    return await SqlAlchemyBotUserRepository(session).upsert(
        telegram_id=message.from_user.id,
        display_name=message.from_user.full_name,
    )


@router.message(Command("start"))
async def cmd_start(message: Message, session: AsyncSession) -> None:
    user = await _register_caller(message, session)
    if user is None:
        return
    if user.role is Role.PENDING:
        await message.answer(lockout_text(user.telegram_id), reply_markup=ReplyKeyboardRemove())
        return
    await message.answer(_welcome_text(), reply_markup=main_menu(user.role))


@router.message(Command("help"))
async def cmd_help(message: Message, session: AsyncSession) -> None:
    user = await _register_caller(message, session)
    if user is None:
        return
    if user.role is Role.PENDING:
        await message.answer(lockout_text(user.telegram_id), reply_markup=ReplyKeyboardRemove())
        return
    await message.answer(help_text(user.role), reply_markup=main_menu(user.role))


async def role_of(session: AsyncSession, telegram_id: int) -> Role:
    """Shared helper: other handlers need the caller's role to redraw the main menu."""
    user = await SqlAlchemyBotUserRepository(session).get(telegram_id)
    return user.role if user is not None else Role.PENDING
