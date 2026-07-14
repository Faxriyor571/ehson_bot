"""Unit tests for SubmitPendingPaymentUseCase and reference code generation."""
from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from ehson_bot.application.use_cases.submit_pending_payment import (
    SubmitPendingPaymentInput,
    SubmitPendingPaymentUseCase,
    generate_reference_code,
)
from ehson_bot.domain.entities import PendingPayment, PendingPaymentStatus
from ehson_bot.domain.exceptions import ReferenceCodeGenerationError
from ehson_bot.domain.value_objects import Money


class FakePendingPaymentRepository:
    """``collisions_remaining`` forces the first N reference-code checks to
    report "already taken" regardless of the code, so the retry loop is
    exercised deterministically rather than depending on real random luck.
    """

    def __init__(self, collisions_remaining: int = 0) -> None:
        self._next_id = 1
        self._collisions_remaining = collisions_remaining
        self.lookup_count = 0
        self.saved: list[PendingPayment] = []

    async def add(self, payment: PendingPayment) -> PendingPayment:
        saved = replace(payment, id=self._next_id)
        self._next_id += 1
        self.saved.append(saved)
        return saved

    async def get_by_reference(self, reference_code: str) -> PendingPayment | None:
        self.lookup_count += 1
        if self._collisions_remaining > 0:
            self._collisions_remaining -= 1
            return PendingPayment(reference_code=reference_code, amount=Money(Decimal(1)))
        return None

    async def list_pending(self) -> list[PendingPayment]:
        raise NotImplementedError

    async def try_claim(
        self, reference_code: str, decision: PendingPaymentStatus
    ) -> PendingPayment | None:
        raise NotImplementedError

    async def attach_donation(self, reference_code: str, donation_id: int) -> None:
        raise NotImplementedError


def test_generate_reference_code_matches_expected_format() -> None:
    code = generate_reference_code()

    assert code.startswith("EH-")
    suffix = code.removeprefix("EH-")
    assert len(suffix) == 5
    assert all(c not in "01OIL" for c in suffix)


async def test_submit_persists_claim_with_donor_id_and_receipt() -> None:
    repo = FakePendingPaymentRepository()
    use_case = SubmitPendingPaymentUseCase(repo)

    payment = await use_case.execute(
        SubmitPendingPaymentInput(
            amount=Decimal(75000), donor_telegram_id=42, receipt_file_id="file123"
        )
    )

    assert payment.id == 1
    assert payment.amount.amount == Decimal(75000)
    assert payment.donor_telegram_id == 42
    assert payment.receipt_file_id == "file123"
    assert payment.reference_code.startswith("EH-")
    assert repo.saved == [payment]


async def test_submit_retries_on_reference_code_collision() -> None:
    repo = FakePendingPaymentRepository(collisions_remaining=2)
    use_case = SubmitPendingPaymentUseCase(repo)

    payment = await use_case.execute(
        SubmitPendingPaymentInput(amount=Decimal(1000), donor_telegram_id=1)
    )

    assert payment.reference_code.startswith("EH-")
    assert repo.lookup_count == 3  # two forced collisions, then the winning attempt


async def test_submit_gives_up_after_exhausting_retry_budget() -> None:
    repo = FakePendingPaymentRepository(collisions_remaining=5)
    use_case = SubmitPendingPaymentUseCase(repo)

    with pytest.raises(ReferenceCodeGenerationError):
        await use_case.execute(SubmitPendingPaymentInput(amount=Decimal(1000), donor_telegram_id=1))
