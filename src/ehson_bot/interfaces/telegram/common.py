"""Small helpers shared across handler modules."""
from __future__ import annotations

from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from ehson_bot.interfaces.telegram.handlers.start import role_of
from ehson_bot.interfaces.telegram.keyboards import main_menu


async def show_main_menu(message: Message, session: AsyncSession) -> None:
    if message.from_user is None:
        return
    role = await role_of(session, message.from_user.id)
    await message.answer("Bosh menyu:", reply_markup=main_menu(role))
