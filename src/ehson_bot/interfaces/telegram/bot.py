"""Composition root for the Telegram adapter: wires routers + middleware."""
from __future__ import annotations

import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from ehson_bot.domain.entities import Role
from ehson_bot.infrastructure.config import settings
from ehson_bot.infrastructure.db.repositories import SqlAlchemyBotUserRepository
from ehson_bot.infrastructure.db.session import get_session
from ehson_bot.infrastructure.scheduler import build_scheduler
from ehson_bot.interfaces.telegram.handlers import (
    admin,
    donations,
    fallback,
    payments,
    reports,
    start,
)
from ehson_bot.interfaces.telegram.middlewares import DbSessionMiddleware

logger = logging.getLogger("ehson_bot")


def build_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    # Outer, not inner: root-level router filters (IsTreasurerOrAbove,
    # IsSuperAdmin) need `session` too, and those are checked *before* inner
    # middleware ever runs — only outer middleware wraps that early enough.
    dp.message.outer_middleware(DbSessionMiddleware())
    dp.include_router(start.router)
    dp.include_router(reports.router)
    dp.include_router(admin.router)
    dp.include_router(donations.router)
    dp.include_router(payments.router)
    # Must stay last: catches anything no role-specific router matched.
    dp.include_router(fallback.router)
    return dp


def build_bot() -> Bot:
    return Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))


async def _bootstrap_super_admins() -> None:
    """Idempotently (re-)promote the configured bootstrap IDs to Super Admin.

    Safe to run on every startup: it only ever raises a user's role, never
    lowers one, so it never clobbers roles assigned later from within the bot.
    """
    if not settings.super_admin_id_list:
        return
    async with get_session() as session:
        repo = SqlAlchemyBotUserRepository(session)
        for telegram_id in settings.super_admin_id_list:
            await repo.upsert(telegram_id, display_name=None)
            await repo.set_role(telegram_id, Role.SUPER_ADMIN)


async def run() -> None:
    await _bootstrap_super_admins()
    bot = build_bot()
    dp = build_dispatcher()

    scheduler = build_scheduler(bot)
    scheduler.start()

    logger.info("Ehson bot ishga tushdi")
    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
