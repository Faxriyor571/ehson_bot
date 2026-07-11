"""/start and /help — every caller is registered, but starts PENDING (no access).

A Super Admin must approve a PENDING user (promoting them to USER) before
they can see anything at all — no statistics, no balance, no menu.
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

LOCKOUT_TEXT = (
    "🔒 Siz hali ushbu botdan foydalanish uchun ruxsat olmagansiz.\n\n"
    "Iltimos, administrator bilan bog'laning."
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


HELP_TEXT = (
    "<b>Mahfiy Ehson boti — yordam</b>\n\n"
    "📊 Statistika — bugungi/oylik/yillik hisobot\n"
    "💰 Balans — joriy qoldiq\n"
    "🏦 Hisob raqami — xayriya uchun bank hisobi\n\n"
    "Har qanday amalni istalgan vaqtda “❌ Bekor qilish” bilan bekor "
    "qilishingiz mumkin."
)


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
        await message.answer(LOCKOUT_TEXT, reply_markup=ReplyKeyboardRemove())
        return
    await message.answer(_welcome_text(), reply_markup=main_menu(user.role))


@router.message(Command("help"))
async def cmd_help(message: Message, session: AsyncSession) -> None:
    user = await _register_caller(message, session)
    if user is None:
        return
    if user.role is Role.PENDING:
        await message.answer(LOCKOUT_TEXT, reply_markup=ReplyKeyboardRemove())
        return
    await message.answer(HELP_TEXT, reply_markup=main_menu(user.role))


async def role_of(session: AsyncSession, telegram_id: int) -> Role:
    """Shared helper: other handlers need the caller's role to redraw the main menu."""
    user = await SqlAlchemyBotUserRepository(session).get(telegram_id)
    return user.role if user is not None else Role.PENDING
