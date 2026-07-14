"""Use case: turn a confirmed payment session into an anonymous donation.

Called by a provider's confirmation path (the mock's delayed self-trigger
today, a real webhook handler later) -- never by the Telegram flow directly.
"""
from __future__ import annotations

from dataclasses import dataclass

from ehson_bot.application.use_cases.record_donation import (
    RecordDonationInput,
    RecordDonationUseCase,
)
from ehson_bot.domain.entities import Donation, PaymentStatus
from ehson_bot.domain.repositories import DonationRepository, PaymentSessionRepository

# Payment-originated donations have no human treasurer to credit -- crediting
# an arbitrary Super Admin would misrepresent who did the work. 0 is never a
# real Telegram user id, so it's a safe, documented sentinel; no schema
# change needed since recorded_by_id just stays an integer column.
SYSTEM_TREASURER_ID = 0


@dataclass(frozen=True, slots=True)
class ConfirmPaymentResult:
    donation: Donation
    donor_telegram_id: int | None


class ConfirmPaymentUseCase:
    def __init__(
        self,
        payment_sessions: PaymentSessionRepository,
        donations: DonationRepository,
    ) -> None:
        self._payment_sessions = payment_sessions
        self._donations = donations

    async def execute(self, provider_session_id: str) -> ConfirmPaymentResult | None:
        """Returns None if the session doesn't exist or already left PENDING
        (already confirmed, already cancelled) -- a safe no-op so a
        confirmation firing twice (or after a cancel) never double-records.
        """
        session = await self._payment_sessions.get(provider_session_id)
        if session is None or session.status != PaymentStatus.PENDING:
            return None

        donor_telegram_id = session.donor_telegram_id

        donation = await RecordDonationUseCase(self._donations).execute(
            RecordDonationInput(amount=session.amount.amount, recorded_by_id=SYSTEM_TREASURER_ID)
        )
        assert donation.id is not None  # DonationRepository.add() always populates it
        await self._payment_sessions.mark_paid(provider_session_id, donation.id)

        return ConfirmPaymentResult(donation=donation, donor_telegram_id=donor_telegram_id)
