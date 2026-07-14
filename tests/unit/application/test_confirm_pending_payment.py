"""Unit tests for ConfirmPendingPaymentUseCase against fake, in-memory repositories."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from decimal import Decimal

from ehson_bot.application.use_cases.confirm_pending_payment import ConfirmPendingPaymentUseCase
from ehson_bot.domain.entities import Donation, PendingPayment, PendingPaymentStatus
from ehson_bot.domain.value_objects import Money


class FakePendingPaymentRepository:
    """Mirrors the atomic-conditional-write contract of the real adapter:
    ``try_claim`` only succeeds while the row is still PENDING, so calling
    it twice on the same code (simulating two Super Admins racing) always
    lets exactly one caller win.
    """

    def __init__(self, payments: list[PendingPayment]) -> None:
        self._payments = {p.reference_code: p for p in payments}
        self.try_claim_calls: list[tuple[str, PendingPaymentStatus]] = []
        self.attach_donation_calls: list[tuple[str, int]] = []

    async def add(self, payment: PendingPayment) -> PendingPayment:
        raise NotImplementedError

    async def get_by_reference(self, reference_code: str) -> PendingPayment | None:
        return self._payments.get(reference_code)

    async def list_pending(self) -> list[PendingPayment]:
        raise NotImplementedError

    async def try_claim(
        self, reference_code: str, decision: PendingPaymentStatus
    ) -> PendingPayment | None:
        self.try_claim_calls.append((reference_code, decision))
        payment = self._payments.get(reference_code)
        if payment is None or payment.status != PendingPaymentStatus.PENDING:
            return None
        self._payments[reference_code] = replace(payment, status=decision, donor_telegram_id=None)
        # Only the persisted copy is scrubbed -- the returned object keeps
        # the pre-scrub donor_telegram_id, matching the real adapter.
        return replace(payment, status=decision)

    async def attach_donation(self, reference_code: str, donation_id: int) -> None:
        self.attach_donation_calls.append((reference_code, donation_id))
        payment = self._payments[reference_code]
        self._payments[reference_code] = replace(payment, donation_id=donation_id)


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


def _pending(reference_code: str = "EH-8F42K") -> PendingPayment:
    return PendingPayment(
        reference_code=reference_code, amount=Money(Decimal(50000)), donor_telegram_id=42
    )


async def test_confirm_creates_donation_credited_to_confirming_admin() -> None:
    payments = FakePendingPaymentRepository([_pending()])
    donations = FakeDonationRepository()
    use_case = ConfirmPendingPaymentUseCase(payments, donations)

    result = await use_case.execute("EH-8F42K", confirmed_by_telegram_id=999)

    assert result is not None
    assert result.donor_telegram_id == 42
    assert result.donation.amount.amount == Decimal(50000)
    assert result.donation.recorded_by.value == 999
    assert donations.saved == [result.donation]
    assert payments.attach_donation_calls == [("EH-8F42K", result.donation.id)]


async def test_confirm_is_a_noop_for_unknown_reference_code() -> None:
    payments = FakePendingPaymentRepository([])
    donations = FakeDonationRepository()
    use_case = ConfirmPendingPaymentUseCase(payments, donations)

    result = await use_case.execute("EH-NOPE1", confirmed_by_telegram_id=999)

    assert result is None
    assert donations.saved == []


async def test_confirm_is_a_noop_for_already_confirmed_claim() -> None:
    already = replace(_pending(), status=PendingPaymentStatus.CONFIRMED, donation_id=1)
    payments = FakePendingPaymentRepository([already])
    donations = FakeDonationRepository()
    use_case = ConfirmPendingPaymentUseCase(payments, donations)

    result = await use_case.execute("EH-8F42K", confirmed_by_telegram_id=999)

    assert result is None
    assert donations.saved == []


async def test_confirm_is_a_noop_for_rejected_claim() -> None:
    rejected = replace(_pending(), status=PendingPaymentStatus.REJECTED)
    payments = FakePendingPaymentRepository([rejected])
    donations = FakeDonationRepository()
    use_case = ConfirmPendingPaymentUseCase(payments, donations)

    result = await use_case.execute("EH-8F42K", confirmed_by_telegram_id=999)

    assert result is None
    assert donations.saved == []


async def test_two_admins_confirming_the_same_code_only_one_wins() -> None:
    """The core race-safety guarantee: two Super Admins pressing confirm on
    the same reference code must never both succeed in creating a donation.
    """
    payments = FakePendingPaymentRepository([_pending()])
    donations = FakeDonationRepository()
    use_case = ConfirmPendingPaymentUseCase(payments, donations)

    first = await use_case.execute("EH-8F42K", confirmed_by_telegram_id=111)
    second = await use_case.execute("EH-8F42K", confirmed_by_telegram_id=222)

    assert first is not None
    assert second is None
    assert len(donations.saved) == 1
    assert donations.saved[0].recorded_by.value == 111
