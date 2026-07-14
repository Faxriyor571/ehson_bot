"""``PaymentProvider`` stand-in that confirms itself on a timer instead of
waiting for a real gateway's webhook.

This proves the automated-confirmation pipeline end to end -- payment ->
donation -> balance/statistics update -> thank-you message -- through
Telegram alone. Swapping in a real provider (Click/Payme) later only
replaces this adapter and adds a real inbound HTTP webhook; the domain
``PaymentProvider`` Protocol, the Telegram flow, and ``ConfirmPaymentUseCase``
do not change.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import replace
from decimal import Decimal

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError

from ehson_bot.application.use_cases.confirm_payment import (
    ConfirmPaymentResult,
    ConfirmPaymentUseCase,
)
from ehson_bot.domain.entities import PaymentSession, Role
from ehson_bot.domain.value_objects import Money
from ehson_bot.infrastructure.config import settings
from ehson_bot.infrastructure.db.repositories import (
    SqlAlchemyBotUserRepository,
    SqlAlchemyDonationRepository,
    SqlAlchemyPaymentSessionRepository,
)
from ehson_bot.infrastructure.db.session import get_session

logger = logging.getLogger("ehson_bot.payments.mock")

_PROVIDER_NAME = "mock"


def donor_thank_you_text(amount: Money) -> str:
    return (
        "✅ Ehson qilganingiz uchun rahmat!\n\n"
        f"Ehsoningiz ({amount} so'm) muvaffaqiyatli qabul qilindi.\n\n"
        "Alloh saxovatingiz uchun sizga ajr-savob ato etsin! 🤲"
    )


def admin_notification_text(amount: Money) -> str:
    return f"💰 Yangi ehson qabul qilindi: {amount} so'm."


class MockPaymentProvider:
    # Shown on the donor-facing confirmation screen. Deliberately generic
    # (not a fabricated brand name) since no real gateway is wired up yet --
    # swapping in Click/Payme later means swapping this string too.
    display_name = "Onlayn to'lov"

    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def create_payment(self, amount: Decimal, donor_telegram_id: int) -> PaymentSession:
        provider_session_id = uuid.uuid4().hex

        async with get_session() as session:
            created = await SqlAlchemyPaymentSessionRepository(session).add(
                PaymentSession(
                    provider_session_id=provider_session_id,
                    amount=Money(amount),
                    provider=_PROVIDER_NAME,
                    donor_telegram_id=donor_telegram_id,
                )
            )

        pay_url = f"{settings.mock_payment_base_url}/{provider_session_id}"

        # Fire-and-forget: proves the pipeline without a real webhook.
        # ConfirmPaymentUseCase's PENDING check makes this safe even if the
        # donor cancels before the delay elapses.
        asyncio.create_task(self._confirm_after_delay(provider_session_id))

        return replace(created, pay_url=pay_url)

    async def _confirm_after_delay(self, provider_session_id: str) -> None:
        await asyncio.sleep(settings.mock_payment_confirm_delay_seconds)

        async with get_session() as session:
            use_case = ConfirmPaymentUseCase(
                SqlAlchemyPaymentSessionRepository(session),
                SqlAlchemyDonationRepository(session),
            )
            result = await use_case.execute(provider_session_id)

        if result is None:
            logger.info("Mock confirmation for %s was a no-op (cancelled?)", provider_session_id)
            return

        await self._notify(result)

    async def _notify(self, result: ConfirmPaymentResult) -> None:
        if result.donor_telegram_id is not None:
            try:
                await self._bot.send_message(
                    result.donor_telegram_id, donor_thank_you_text(result.donation.amount)
                )
            except TelegramForbiddenError:
                logger.info(
                    "Could not thank donor %s: bot was blocked", result.donor_telegram_id
                )

        async with get_session() as session:
            admins = await SqlAlchemyBotUserRepository(session).list_by_role(Role.SUPER_ADMIN)

        for admin in admins:
            try:
                await self._bot.send_message(
                    admin.telegram_id, admin_notification_text(result.donation.amount)
                )
            except TelegramForbiddenError:
                logger.info("Could not notify admin %s: bot was blocked", admin.telegram_id)
