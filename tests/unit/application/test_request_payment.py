"""Unit test for RequestPaymentUseCase against a fake payment provider."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from ehson_bot.application.use_cases.request_payment import (
    RequestPaymentInput,
    RequestPaymentUseCase,
)
from ehson_bot.domain.entities import PaymentSession
from ehson_bot.domain.value_objects import Money


@dataclass
class FakePaymentProvider:
    """Minimal stand-in — satisfies ``PaymentProvider`` structurally."""

    display_name: str = "Fake"
    calls: list[tuple[Decimal, int]] = field(default_factory=list)

    async def create_payment(self, amount: Decimal, donor_telegram_id: int) -> PaymentSession:
        self.calls.append((amount, donor_telegram_id))
        return PaymentSession(
            provider_session_id="sess-1",
            amount=Money(amount),
            provider="mock",
            donor_telegram_id=donor_telegram_id,
            pay_url="https://mock-pay.example/sess-1",
        )


async def test_request_payment_delegates_to_provider_and_returns_its_session() -> None:
    provider = FakePaymentProvider()
    use_case = RequestPaymentUseCase(provider)

    session = await use_case.execute(
        RequestPaymentInput(amount=Decimal(50000), donor_telegram_id=7)
    )

    assert provider.calls == [(Decimal(50000), 7)]
    assert session.provider_session_id == "sess-1"
    assert session.pay_url == "https://mock-pay.example/sess-1"
