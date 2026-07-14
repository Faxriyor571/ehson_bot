"""Unit tests for RejectPendingPaymentUseCase against a fake repository."""
from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from ehson_bot.application.use_cases.reject_pending_payment import RejectPendingPaymentUseCase
from ehson_bot.domain.entities import PendingPayment, PendingPaymentStatus
from ehson_bot.domain.value_objects import Money


class FakePendingPaymentRepository:
    def __init__(self, payments: list[PendingPayment]) -> None:
        self._payments = {p.reference_code: p for p in payments}
        self.try_claim_calls: list[tuple[str, PendingPaymentStatus]] = []

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
        raise NotImplementedError


def _pending(reference_code: str = "EH-8F42K") -> PendingPayment:
    return PendingPayment(
        reference_code=reference_code, amount=Money(Decimal(50000)), donor_telegram_id=42
    )


async def test_reject_marks_claim_rejected_and_returns_donor_id() -> None:
    repo = FakePendingPaymentRepository([_pending()])
    use_case = RejectPendingPaymentUseCase(repo)

    result = await use_case.execute("EH-8F42K")

    assert result is not None
    assert result.donor_telegram_id == 42
    assert repo.try_claim_calls == [("EH-8F42K", PendingPaymentStatus.REJECTED)]


async def test_reject_is_a_noop_for_unknown_reference_code() -> None:
    repo = FakePendingPaymentRepository([])
    use_case = RejectPendingPaymentUseCase(repo)

    result = await use_case.execute("EH-NOPE1")

    assert result is None


async def test_reject_is_a_noop_for_already_confirmed_claim() -> None:
    already = replace(_pending(), status=PendingPaymentStatus.CONFIRMED, donation_id=1)
    repo = FakePendingPaymentRepository([already])
    use_case = RejectPendingPaymentUseCase(repo)

    result = await use_case.execute("EH-8F42K")

    assert result is None


async def test_two_admins_deciding_the_same_code_only_one_wins() -> None:
    """Race safety also holds for confirm-vs-reject and reject-vs-reject:
    once one Super Admin decides, a second decision is always a no-op.
    """
    repo = FakePendingPaymentRepository([_pending()])
    use_case = RejectPendingPaymentUseCase(repo)

    first = await use_case.execute("EH-8F42K")
    second = await use_case.execute("EH-8F42K")

    assert first is not None
    assert second is None
