"""Catch-all: anything no other router matched.

A brand-new Telegram user's very first message doesn't have to be
literally ``/start`` — it can be any free text — and at that point they
have no ``bot_users`` row yet, so every role filter elsewhere returns
False and the update would otherwise be silently dropped instead of
showing the required lockout message. This router has no filter and must
be registered *last* in the dispatcher, so it only ever sees updates
nothing else handled.
"""
from __future__ import annotations

from aiogram import Router
from aiogram.types import Message, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from ehson_bot.domain.entities import Role
from ehson_bot.infrastructure.db.repositories import SqlAlchemyBotUserRepository
from ehson_bot.interfaces.telegram.common import show_main_menu
from ehson_bot.interfaces.telegram.handlers.start import LOCKOUT_TEXT

router = Router(name="fallback")


@router.message()
async def catch_all(message: Message, session: AsyncSession) -> None:
    if message.from_user is None:
        return
    user = await SqlAlchemyBotUserRepository(session).upsert(
        telegram_id=message.from_user.id,
        display_name=message.from_user.full_name,
    )
    if user.role is Role.PENDING:
        await message.answer(LOCKOUT_TEXT, reply_markup=ReplyKeyboardRemove())
        return
    # An approved user typed something no specific handler matched — just
    # redraw the main menu rather than staying silent.
    await show_main_menu(message, session)
