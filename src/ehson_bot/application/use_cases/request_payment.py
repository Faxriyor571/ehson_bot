"""Use case: a donor starts a payment attempt."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ehson_bot.domain.entities import PaymentSession
from ehson_bot.domain.repositories import PaymentProvider


@dataclass(frozen=True, slots=True)
class RequestPaymentInput:
    amount: Decimal
    donor_telegram_id: int


class RequestPaymentUseCase:
    def __init__(self, provider: PaymentProvider) -> None:
        self._provider = provider

    async def execute(self, data: RequestPaymentInput) -> PaymentSession:
        return await self._provider.create_payment(data.amount, data.donor_telegram_id)
