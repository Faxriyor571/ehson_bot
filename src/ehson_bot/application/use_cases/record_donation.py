"""Use case: record a confirmed donation.

Donations are now self-service: the donor's own "✅ Pulni o'tkazdim" press
*is* the confirmation (this is a small, trusted group of a handful of
people, so a second manual review step was decided unnecessary). No human
treasurer records it, so ``recorded_by`` uses ``SYSTEM_TREASURER_ID`` — a
fixed, documented sentinel, never a real Telegram id, since ``Donation``
must never carry the donor's own identity.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ehson_bot.domain.entities import Donation, TreasurerId
from ehson_bot.domain.repositories import DonationRepository
from ehson_bot.domain.value_objects import Money

SYSTEM_TREASURER_ID = 0


@dataclass(frozen=True, slots=True)
class RecordDonationInput:
    amount: Decimal
    recorded_by_id: int
    note: str | None = None
    receipt_file_id: str | None = None


class RecordDonationUseCase:
    def __init__(self, repository: DonationRepository) -> None:
        self._repository = repository

    async def execute(self, data: RecordDonationInput) -> Donation:
        donation = Donation(
            amount=Money(data.amount),
            recorded_by=TreasurerId(data.recorded_by_id),
            note=data.note,
            receipt_file_id=data.receipt_file_id,
        )
        return await self._repository.add(donation)
