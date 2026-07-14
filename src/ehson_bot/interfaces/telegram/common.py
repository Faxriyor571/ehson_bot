"""Small helpers shared across handler modules."""
from __future__ import annotations

from html import escape as _html_escape

from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from ehson_bot.interfaces.telegram.handlers.start import role_of
from ehson_bot.interfaces.telegram.keyboards import main_menu


async def show_main_menu(message: Message, session: AsyncSession) -> None:
    if message.from_user is None:
        return
    role = await role_of(session, message.from_user.id)
    await message.answer("Bosh menyu:", reply_markup=main_menu(role))


def esc(text: str) -> str:
    """Escape free text before interpolating it into an HTML-parsed message.

    The bot defaults to ``ParseMode.HTML`` for every ``message.answer`` call,
    so any unescaped ``<``/``&`` in a Telegram display name, expense
    description, or donation note (all attacker/user-controlled) would break
    Telegram's HTML parser and fail the send. Quotes are left alone —
    Telegram's HTML subset doesn't need them escaped, unlike full HTML.
    """
    return _html_escape(text, quote=False)
