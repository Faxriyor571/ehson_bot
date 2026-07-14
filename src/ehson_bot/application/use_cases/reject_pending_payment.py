"""Use case: a Super Admin rejects a payment claim (the money never arrived).

Keeps the pending-payments queue from accumulating claims nobody ever
resolves, and lets the donor find out rather than being left wondering.

Race safety: ``try_claim`` is a single atomic conditional write, so if
another Super Admin already confirmed or rejected this same reference code
moments earlier, this call simply loses the race and returns None -- never
overwrites a decision someone else already made.
"""
from __future__ import annotations

from dataclasses import dataclass

from ehson_bot.domain.entities import PendingPaymentStatus
from ehson_bot.domain.repositories import PendingPaymentRepository


@dataclass(frozen=True, slots=True)
class RejectPendingPaymentResult:
    donor_telegram_id: int | None


class RejectPendingPaymentUseCase:
    def __init__(self, payments: PendingPaymentRepository) -> None:
        self._payments = payments

    async def execute(self, reference_code: str) -> RejectPendingPaymentResult | None:
        """Returns None if the claim doesn't exist, or someone (possibly a
        different Super Admin) already decided it.
        """
        claimed = await self._payments.try_claim(reference_code, PendingPaymentStatus.REJECTED)
        if claimed is None:
            return None
        return RejectPendingPaymentResult(donor_telegram_id=claimed.donor_telegram_id)
