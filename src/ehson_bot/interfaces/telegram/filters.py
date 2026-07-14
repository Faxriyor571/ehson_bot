"""Access-control filters, backed by the ``bot_users`` table."""
from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from ehson_bot.domain.entities import Role
from ehson_bot.infrastructure.db.repositories import SqlAlchemyBotUserRepository

_RANK = {Role.PENDING: 0, Role.TREASURER: 1, Role.SUPER_ADMIN: 2}


class HasRole(BaseFilter):
    """True if the caller is a known bot user whose role is at least ``minimum``."""

    def __init__(self, minimum: Role) -> None:
        self.minimum = minimum

    async def __call__(self, message: Message, session: AsyncSession) -> bool:
        if message.from_user is None:
            return False
        user = await SqlAlchemyBotUserRepository(session).get(message.from_user.id)
        if user is None:
            return False
        return _RANK[user.role] >= _RANK[self.minimum]


class IsTreasurerOrAbove(HasRole):
    """TREASURER is the lowest non-PENDING rank, so this doubles as "is this
    caller an approved member at all" — there is no separate donor-only tier.
    """

    def __init__(self) -> None:
        super().__init__(Role.TREASURER)


class IsSuperAdmin(HasRole):
    def __init__(self) -> None:
        super().__init__(Role.SUPER_ADMIN)
