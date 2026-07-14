"""Unit test for ConfirmPaymentUseCase against fake, in-memory repositories."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from decimal import Decimal

from ehson_bot.application.use_cases.confirm_payment import (
    SYSTEM_TREASURER_ID,
    ConfirmPaymentUseCase,
)
from ehson_bot.domain.entities import Donation, PaymentSession, PaymentStatus
from ehson_bot.domain.value_objects import Money


class FakePaymentSessionRepository:
    def __init__(self, sessions: list[PaymentSession]) -> None:
        self._sessions = {s.provider_session_id: s for s in sessions}
        self.mark_paid_calls: list[tuple[str, int]] = []

    async def add(self, session: PaymentSession) -> PaymentSession:
        raise NotImplementedError

    async def get(self, provider_session_id: str) -> PaymentSession | None:
        return self._sessions.get(provider_session_id)

    async def mark_paid(self, provider_session_id: str, donation_id: int) -> PaymentSession | None:
        session = self._sessions.get(provider_session_id)
        if session is None:
            return None
        self.mark_paid_calls.append((provider_session_id, donation_id))
        updated = replace(
            session,
            status=PaymentStatus.PAID,
            donation_id=donation_id,
            donor_telegram_id=None,
        )
        self._sessions[provider_session_id] = updated
        return updated

    async def mark_cancelled(self, provider_session_id: str) -> PaymentSession | None:
        raise NotImplementedError


class FakeDonationRepository:
    def __init__(self) -> None:
        self._next_id = 1
        self.saved: list[Donation] = []

    async def add(self, donation: Donation) -> Donation:
        saved = replace(donation, id=self._next_id, created_at=datetime(2026, 1, 1))
        self._next_id += 1
        self.saved.append(saved)
        return saved

    async def get(self, donation_id: int) -> Donation | None:
        raise NotImplementedError

    async def remove(self, donation_id: int) -> bool:
        raise NotImplementedError

    async def list_recent(self, limit: int) -> list[Donation]:
        raise NotImplementedError

    async def sum_since(self, start: datetime | None) -> Decimal:
        raise NotImplementedError

    async def count_since(self, start: datetime | None) -> int:
        raise NotImplementedError


def _pending_session(provider_session_id: str = "sess-1") -> PaymentSession:
    return PaymentSession(
        provider_session_id=provider_session_id,
        amount=Money(Decimal(50000)),
        provider="mock",
        donor_telegram_id=42,
    )


async def test_confirm_creates_donation_and_marks_session_paid() -> None:
    sessions = FakePaymentSessionRepository([_pending_session()])
    donations = FakeDonationRepository()
    use_case = ConfirmPaymentUseCase(sessions, donations)

    result = await use_case.execute("sess-1")

    assert result is not None
    assert result.donor_telegram_id == 42
    assert result.donation.amount.amount == Decimal(50000)
    assert result.donation.recorded_by.value == SYSTEM_TREASURER_ID
    assert donations.saved == [result.donation]
    assert sessions.mark_paid_calls == [("sess-1", result.donation.id)]


async def test_confirm_is_a_noop_for_unknown_session() -> None:
    sessions = FakePaymentSessionRepository([])
    donations = FakeDonationRepository()
    use_case = ConfirmPaymentUseCase(sessions, donations)

    result = await use_case.execute("nope")

    assert result is None
    assert donations.saved == []


async def test_confirm_is_a_noop_for_already_paid_session() -> None:
    already_paid = replace(_pending_session(), status=PaymentStatus.PAID, donation_id=1)
    sessions = FakePaymentSessionRepository([already_paid])
    donations = FakeDonationRepository()
    use_case = ConfirmPaymentUseCase(sessions, donations)

    result = await use_case.execute("sess-1")

    assert result is None
    assert donations.saved == []


async def test_confirm_is_a_noop_for_cancelled_session() -> None:
    cancelled = replace(_pending_session(), status=PaymentStatus.CANCELLED)
    sessions = FakePaymentSessionRepository([cancelled])
    donations = FakeDonationRepository()
    use_case = ConfirmPaymentUseCase(sessions, donations)

    result = await use_case.execute("sess-1")

    assert result is None
    assert donations.saved == []
