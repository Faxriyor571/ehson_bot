"""Integration tests for SqlAlchemyPendingPaymentRepository against in-memory SQLite."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from ehson_bot.domain.entities import PendingPayment, PendingPaymentStatus
from ehson_bot.domain.value_objects import Money
from ehson_bot.infrastructure.db.repositories import SqlAlchemyPendingPaymentRepository


async def test_add_persists_pending_claim_with_donor_id(session: AsyncSession) -> None:
    repo = SqlAlchemyPendingPaymentRepository(session)

    created = await repo.add(
        PendingPayment(
            reference_code="EH-8F42K",
            amount=Money(Decimal(50000)),
            donor_telegram_id=111,
        )
    )

    assert created.id is not None
    assert created.status == PendingPaymentStatus.PENDING
    assert created.donor_telegram_id == 111
    assert created.donation_id is None


async def test_get_by_reference_returns_none_for_unknown_code(session: AsyncSession) -> None:
    repo = SqlAlchemyPendingPaymentRepository(session)

    assert await repo.get_by_reference("EH-NOPE1") is None


async def test_get_by_reference_round_trips(session: AsyncSession) -> None:
    repo = SqlAlchemyPendingPaymentRepository(session)
    await repo.add(PendingPayment(reference_code="EH-3R91P", amount=Money(Decimal(1000))))

    fetched = await repo.get_by_reference("EH-3R91P")

    assert fetched is not None
    assert fetched.amount.amount == Decimal(1000)


async def test_list_pending_excludes_decided_claims(session: AsyncSession) -> None:
    repo = SqlAlchemyPendingPaymentRepository(session)
    await repo.add(PendingPayment(reference_code="EH-AAAAA", amount=Money(Decimal(1000))))
    await repo.add(PendingPayment(reference_code="EH-BBBBB", amount=Money(Decimal(2000))))
    await repo.try_claim("EH-BBBBB", PendingPaymentStatus.REJECTED)

    pending = await repo.list_pending()

    assert [p.reference_code for p in pending] == ["EH-AAAAA"]


async def test_try_claim_confirmed_scrubs_donor_id(session: AsyncSession) -> None:
    repo = SqlAlchemyPendingPaymentRepository(session)
    await repo.add(
        PendingPayment(
            reference_code="EH-CCCCC", amount=Money(Decimal(2000)), donor_telegram_id=222
        )
    )

    claimed = await repo.try_claim("EH-CCCCC", PendingPaymentStatus.CONFIRMED)

    assert claimed is not None
    assert claimed.status == PendingPaymentStatus.CONFIRMED
    # The claim result still carries the pre-scrub donor id for the caller
    # to route a private message, even though the persisted row is scrubbed.
    assert claimed.donor_telegram_id == 222

    persisted = await repo.get_by_reference("EH-CCCCC")
    assert persisted is not None
    assert persisted.donor_telegram_id is None
    assert persisted.decided_at is not None


async def test_attach_donation_links_the_donation_id(session: AsyncSession) -> None:
    repo = SqlAlchemyPendingPaymentRepository(session)
    await repo.add(PendingPayment(reference_code="EH-EEEEE", amount=Money(Decimal(4000))))
    await repo.try_claim("EH-EEEEE", PendingPaymentStatus.CONFIRMED)

    await repo.attach_donation("EH-EEEEE", donation_id=99)

    persisted = await repo.get_by_reference("EH-EEEEE")
    assert persisted is not None
    assert persisted.donation_id == 99


async def test_try_claim_on_unknown_code_returns_none(session: AsyncSession) -> None:
    repo = SqlAlchemyPendingPaymentRepository(session)

    assert await repo.try_claim("EH-NOPE1", PendingPaymentStatus.CONFIRMED) is None


async def test_try_claim_rejected_scrubs_donor_id(session: AsyncSession) -> None:
    repo = SqlAlchemyPendingPaymentRepository(session)
    await repo.add(
        PendingPayment(
            reference_code="EH-DDDDD", amount=Money(Decimal(3000)), donor_telegram_id=333
        )
    )

    claimed = await repo.try_claim("EH-DDDDD", PendingPaymentStatus.REJECTED)

    assert claimed is not None
    assert claimed.status == PendingPaymentStatus.REJECTED

    persisted = await repo.get_by_reference("EH-DDDDD")
    assert persisted is not None
    assert persisted.donor_telegram_id is None


async def test_try_claim_is_race_safe_against_a_second_decision(session: AsyncSession) -> None:
    """The core DB-level guarantee: once a reference code is claimed, a
    second ``try_claim`` call for the same code (simulating a second Super
    Admin) always loses, regardless of which decision it attempts.
    """
    repo = SqlAlchemyPendingPaymentRepository(session)
    await repo.add(PendingPayment(reference_code="EH-FFFFF", amount=Money(Decimal(5000))))

    first = await repo.try_claim("EH-FFFFF", PendingPaymentStatus.CONFIRMED)
    second = await repo.try_claim("EH-FFFFF", PendingPaymentStatus.REJECTED)

    assert first is not None
    assert second is None

    persisted = await repo.get_by_reference("EH-FFFFF")
    assert persisted is not None
    assert persisted.status == PendingPaymentStatus.CONFIRMED  # the second call never overwrote it
