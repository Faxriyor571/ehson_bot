"""/start and /help — every caller is registered, but starts PENDING (no access).

A Super Admin must approve a PENDING user (promoting them to TREASURER, the
only non-admin approved role) before they can see anything at all — no
statistics, no balance, no menu. The first time an approved member reaches
this far, they're routed into the anonymous-display-name flow
(``start_anonymous_name_flow``) instead of the welcome screen — see
``handlers/anonymous_name.py`` for why and how that's enforced.
"""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from ehson_bot.domain.entities import BotUser, Role
from ehson_bot.infrastructure.db.repositories import SqlAlchemyBotUserRepository
from ehson_bot.interfaces.telegram.keyboards import anonymous_name_choice_menu, main_menu
from ehson_bot.interfaces.telegram.states import AnonymousNameStates

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


def welcome_text() -> str:
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
        "🤲 Ehson qilish — ehson yuborish",
        "💰 Balans — joriy balans va bugungi harakat",
        "📊 Statistika — bugungi/oylik/yillik/umumiy hisobot",
    ]

    if role is Role.SUPER_ADMIN:
        lines += [
            "\n<b>Boshqaruv</b>",
            "➖ Xarajat qo'shish — yangi xarajatni qayd etish",
            "📋 Oxirgi yozuvlar — so'nggi ehson va xarajatlarni ko'rish/o'chirish",
            "👥 A'zolarni boshqarish — a'zolarni tasdiqlash yoki kirishini bekor qilish",
            "⚙️ Sozlamalar — ehson hisob raqamini sozlash",
        ]

    lines.append(
        "\nHar qanday amalni istalgan vaqtda “❌ Bekor qilish” bilan bekor "
        "qilishingiz mumkin."
    )
    return "\n".join(lines)


async def start_anonymous_name_flow(message: Message, state: FSMContext) -> None:
    """The first thing any approved member sees before their actual welcome
    screen or first menu render — enforced at every entry point that would
    otherwise hand them the persistent keyboard (``cmd_start``, ``cmd_help``,
    ``fallback.catch_all``): with no keyboard shown yet, there is nothing
    else for them to press, so gating just these three places is sufficient.
    """
    await state.set_state(AnonymousNameStates.choosing)
    await message.answer(
        "🤲 Xush kelibsiz!\n\n"
        "Ehsoningiz har doim maxfiy qoladi. Xohlasangiz, o'zingiz uchun "
        "maxfiy taxallus tanlang — bu sizning haqiqiy ismingiz yoki Telegram "
        "foydalanuvchi nomingiz emas, faqat siz bilan muloqot qilishda "
        "ishlatiladi.\n\n"
        "Ro'yxatdan birini tanlang, o'zingiz nom yozing yoki o'tkazib yuboring "
        "— bu holda sizga tasodifiy taxallus tayinlanadi.",
        reply_markup=anonymous_name_choice_menu(),
    )


async def _register_caller(message: Message, session: AsyncSession) -> BotUser | None:
    if message.from_user is None:
        return None
    return await SqlAlchemyBotUserRepository(session).upsert(
        telegram_id=message.from_user.id,
        display_name=message.from_user.full_name,
    )


@router.message(Command("start"))
async def cmd_start(message: Message, session: AsyncSession, state: FSMContext) -> None:
    user = await _register_caller(message, session)
    if user is None:
        return
    if user.role is Role.PENDING:
        await message.answer(lockout_text(user.telegram_id), reply_markup=ReplyKeyboardRemove())
        return
    if user.anonymous_name is None:
        await start_anonymous_name_flow(message, state)
        return
    await message.answer(welcome_text(), reply_markup=main_menu(user.role))


@router.message(Command("help"))
async def cmd_help(message: Message, session: AsyncSession, state: FSMContext) -> None:
    user = await _register_caller(message, session)
    if user is None:
        return
    if user.role is Role.PENDING:
        await message.answer(lockout_text(user.telegram_id), reply_markup=ReplyKeyboardRemove())
        return
    if user.anonymous_name is None:
        await start_anonymous_name_flow(message, state)
        return
    await message.answer(help_text(user.role), reply_markup=main_menu(user.role))


async def role_of(session: AsyncSession, telegram_id: int) -> Role:
    """Shared helper: other handlers need the caller's role to redraw the main menu."""
    user = await SqlAlchemyBotUserRepository(session).get(telegram_id)
    return user.role if user is not None else Role.PENDING
