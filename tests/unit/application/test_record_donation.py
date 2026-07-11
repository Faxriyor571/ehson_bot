"""Unit test for RecordDonationUseCase against a fake, in-memory repository."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from decimal import Decimal

from ehson_bot.application.use_cases.record_donation import (
    RecordDonationInput,
    RecordDonationUseCase,
)
from ehson_bot.domain.entities import Donation


class FakeDonationRepository:
    """Minimal in-memory stand-in — satisfies ``DonationRepository`` structurally."""

    def __init__(self) -> None:
        self._next_id = 1
        self.saved: list[Donation] = []

    async def add(self, donation: Donation) -> Donation:
        saved = replace(donation, id=self._next_id, created_at=datetime(2026, 1, 1))
        self._next_id += 1
        self.saved.append(saved)
        return saved

    async def get(self, donation_id: int) -> Donation | None:
        return next((d for d in self.saved if d.id == donation_id), None)

    async def remove(self, donation_id: int) -> bool:
        raise NotImplementedError

    async def list_recent(self, limit: int) -> list[Donation]:
        raise NotImplementedError

    async def sum_since(self, start: datetime | None) -> Decimal:
        raise NotImplementedError


async def test_record_donation_persists_amount_and_note() -> None:
    repo = FakeDonationRepository()
    use_case = RecordDonationUseCase(repo)

    donation = await use_case.execute(
        RecordDonationInput(amount=Decimal(75000), recorded_by_id=42, note="fitr")
    )

    assert donation.id == 1
    assert donation.amount.amount == Decimal(75000)
    assert donation.note == "fitr"
    assert donation.recorded_by.value == 42
    assert repo.saved == [donation]
