"""Integration tests for SqlAlchemyDonationRepository against in-memory SQLite."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from ehson_bot.domain.entities import Donation, TreasurerId
from ehson_bot.domain.value_objects import Money
from ehson_bot.infrastructure.db.models import DonationRow
from ehson_bot.infrastructure.db.repositories import SqlAlchemyDonationRepository


async def test_add_persists_and_returns_id_and_created_at(session: AsyncSession) -> None:
    repo = SqlAlchemyDonationRepository(session)

    donation = await repo.add(
        Donation(amount=Money(Decimal(50000)), recorded_by=TreasurerId(1), note="fitr")
    )

    assert donation.id is not None
    assert donation.created_at is not None
    assert donation.note == "fitr"


async def test_sum_since_none_sums_all_time(session: AsyncSession) -> None:
    repo = SqlAlchemyDonationRepository(session)
    await repo.add(Donation(amount=Money(Decimal(1000)), recorded_by=TreasurerId(1)))
    await repo.add(Donation(amount=Money(Decimal(2000)), recorded_by=TreasurerId(1)))

    assert await repo.sum_since(None) == Decimal(3000)


async def test_sum_since_on_empty_ledger_is_zero(session: AsyncSession) -> None:
    repo = SqlAlchemyDonationRepository(session)

    assert await repo.sum_since(None) == 0


async def test_remove_deletes_existing_and_reports_missing(session: AsyncSession) -> None:
    repo = SqlAlchemyDonationRepository(session)
    donation = await repo.add(Donation(amount=Money(Decimal(500)), recorded_by=TreasurerId(1)))

    assert await repo.remove(donation.id) is True
    assert await repo.get(donation.id) is None
    assert await repo.remove(donation.id) is False


async def test_list_recent_orders_newest_first(session: AsyncSession) -> None:
    # created_at is set explicitly (bypassing the server default) so ordering
    # is deterministic regardless of the test DB's timestamp resolution.
    early = DonationRow(amount=Decimal(100), recorded_by_id=1, created_at=datetime(2026, 1, 1))
    late = DonationRow(amount=Decimal(200), recorded_by_id=1, created_at=datetime(2026, 1, 2))
    session.add_all([early, late])
    await session.commit()

    repo = SqlAlchemyDonationRepository(session)
    recent = await repo.list_recent(limit=10)

    assert [d.amount.amount for d in recent] == [Decimal(200), Decimal(100)]
