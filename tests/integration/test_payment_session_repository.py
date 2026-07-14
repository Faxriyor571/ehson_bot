"""Integration tests for SqlAlchemyPaymentSessionRepository against in-memory SQLite."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from ehson_bot.domain.entities import PaymentSession, PaymentStatus
from ehson_bot.domain.value_objects import Money
from ehson_bot.infrastructure.db.repositories import SqlAlchemyPaymentSessionRepository


async def test_add_persists_pending_session_with_donor_id(session: AsyncSession) -> None:
    repo = SqlAlchemyPaymentSessionRepository(session)

    created = await repo.add(
        PaymentSession(
            provider_session_id="sess-1",
            amount=Money(Decimal(50000)),
            provider="mock",
            donor_telegram_id=111,
        )
    )

    assert created.id is not None
    assert created.status == PaymentStatus.PENDING
    assert created.donor_telegram_id == 111
    assert created.donation_id is None


async def test_get_returns_none_for_unknown_session(session: AsyncSession) -> None:
    repo = SqlAlchemyPaymentSessionRepository(session)

    assert await repo.get("does-not-exist") is None


async def test_get_round_trips_by_provider_session_id(session: AsyncSession) -> None:
    repo = SqlAlchemyPaymentSessionRepository(session)
    await repo.add(
        PaymentSession(
            provider_session_id="sess-2", amount=Money(Decimal(1000)), provider="mock"
        )
    )

    fetched = await repo.get("sess-2")

    assert fetched is not None
    assert fetched.amount.amount == Decimal(1000)


async def test_mark_paid_links_donation_and_scrubs_donor_id(session: AsyncSession) -> None:
    repo = SqlAlchemyPaymentSessionRepository(session)
    await repo.add(
        PaymentSession(
            provider_session_id="sess-3",
            amount=Money(Decimal(2000)),
            provider="mock",
            donor_telegram_id=222,
        )
    )

    updated = await repo.mark_paid("sess-3", donation_id=99)

    assert updated is not None
    assert updated.status == PaymentStatus.PAID
    assert updated.donation_id == 99
    assert updated.donor_telegram_id is None
    assert updated.confirmed_at is not None


async def test_mark_paid_on_unknown_session_returns_none(session: AsyncSession) -> None:
    repo = SqlAlchemyPaymentSessionRepository(session)

    assert await repo.mark_paid("nope", donation_id=1) is None


async def test_mark_cancelled_transitions_status(session: AsyncSession) -> None:
    repo = SqlAlchemyPaymentSessionRepository(session)
    await repo.add(
        PaymentSession(provider_session_id="sess-4", amount=Money(Decimal(3000)), provider="mock")
    )

    updated = await repo.mark_cancelled("sess-4")

    assert updated is not None
    assert updated.status == PaymentStatus.CANCELLED


async def test_mark_cancelled_on_unknown_session_returns_none(session: AsyncSession) -> None:
    repo = SqlAlchemyPaymentSessionRepository(session)

    assert await repo.mark_cancelled("nope") is None
