"""Use case: a Super Admin confirms a payment claim after manually checking
the bank account.

Called only from the Super-Admin-only "review by reference code" flow --
never anything donor-facing. The confirming admin's own Telegram ID becomes
``Donation.recorded_by``: a real person did verify this one, unlike an
automated flow, so crediting them for their own accountability is exactly
what that field is for.

Race safety: with multiple Super Admins, two people could open the same
reference code and both press confirm within moments of each other. The
claim itself (``try_claim``) is a single atomic conditional write -- only
one caller can ever win it -- so at most one ``Donation`` is ever created
per reference code, no matter how the two requests interleave.
"""
from __future__ import annotations

from dataclasses import dataclass

from ehson_bot.application.use_cases.record_donation import (
    RecordDonationInput,
    RecordDonationUseCase,
)
from ehson_bot.domain.entities import Donation, PendingPaymentStatus
from ehson_bot.domain.repositories import DonationRepository, PendingPaymentRepository


@dataclass(frozen=True, slots=True)
class ConfirmPendingPaymentResult:
    donation: Donation
    donor_telegram_id: int | None


class ConfirmPendingPaymentUseCase:
    def __init__(
        self,
        payments: PendingPaymentRepository,
        donations: DonationRepository,
    ) -> None:
        self._payments = payments
        self._donations = donations

    async def execute(
        self, reference_code: str, confirmed_by_telegram_id: int
    ) -> ConfirmPendingPaymentResult | None:
        """Returns None if the claim doesn't exist, or someone (possibly a
        different Super Admin) already decided it -- a safe, idempotent
        no-op either way, so pressing confirm twice (or racing another
        admin) never double-records.
        """
        claimed = await self._payments.try_claim(reference_code, PendingPaymentStatus.CONFIRMED)
        if claimed is None:
            return None

        donation = await RecordDonationUseCase(self._donations).execute(
            RecordDonationInput(
                amount=claimed.amount.amount, recorded_by_id=confirmed_by_telegram_id
            )
        )
        assert donation.id is not None  # DonationRepository.add() always populates it
        await self._payments.attach_donation(reference_code, donation.id)

        return ConfirmPendingPaymentResult(
            donation=donation, donor_telegram_id=claimed.donor_telegram_id
        )
