"""Opens one DB session per update and injects it into handler data.

This is where the composition happens: handlers receive a ready-to-use
``AsyncSession`` and build the repository/use case themselves, keeping the
handler bodies free of engine/session lifecycle concerns.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from ehson_bot.infrastructure.db.session import get_session


class DbSessionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with get_session() as session:
            data["session"] = session
            return await handler(event, data)
