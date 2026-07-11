"""Use case: a treasurer corrects a mistaken entry."""
from __future__ import annotations

from ehson_bot.domain.exceptions import DonationNotFound
from ehson_bot.domain.repositories import DonationRepository


class RemoveDonationUseCase:
    def __init__(self, repository: DonationRepository) -> None:
        self._repository = repository

    async def execute(self, donation_id: int) -> None:
        removed = await self._repository.remove(donation_id)
        if not removed:
            raise DonationNotFound(f"Donation #{donation_id} does not exist")
