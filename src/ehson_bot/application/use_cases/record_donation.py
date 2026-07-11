"""Use case: a treasurer records a confirmed donation."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ehson_bot.domain.entities import Donation, TreasurerId
from ehson_bot.domain.repositories import DonationRepository
from ehson_bot.domain.value_objects import Money


@dataclass(frozen=True, slots=True)
class RecordDonationInput:
    amount: Decimal
    recorded_by_id: int
    note: str | None = None


class RecordDonationUseCase:
    def __init__(self, repository: DonationRepository) -> None:
        self._repository = repository

    async def execute(self, data: RecordDonationInput) -> Donation:
        donation = Donation(
            amount=Money(data.amount),
            recorded_by=TreasurerId(data.recorded_by_id),
            note=data.note,
        )
        return await self._repository.add(donation)
